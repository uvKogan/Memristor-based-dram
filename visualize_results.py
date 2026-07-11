#!/usr/bin/env python3
"""
MBMM Visualization - Bar Chart Generation

Reads pre-calculated metrics from CSV and generates:
- Total Execution Cycles comparison (PDP latency component)
- Power breakdown (Dynamic vs. Static)
- PDP efficiency index

This is a 'dumb plotter' - zero math, zero stat parsing.
All calculations performed in process_metrics.py.
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
from pathlib import Path
from logging_config import setup_logging

logger = setup_logging("visualize_bar_charts")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Overridable via --output-dir/--metrics-file (see main()) for isolated dataset
# runs (e.g. the v2/module-sum repair validation) without touching the
# documented-ground-truth final_graphs/ and processed_bar_chart_metrics.csv.
# Defaults are unchanged from the original pipeline.
BASE_OUTPUT_DIR = "/home/yuvalk/MBMM/results/final_graphs"
LATENCY_DIR = os.path.join(BASE_OUTPUT_DIR, "latency")
POWER_DIR = os.path.join(BASE_OUTPUT_DIR, "power")
PDP_DIR = os.path.join(BASE_OUTPUT_DIR, "pdp")
METRICS_FILE = "/home/yuvalk/MBMM/results/processed_bar_chart_metrics.csv"

# Caveat footnote required on every power/PDP figure once static power reflects
# real, ungated, per-technology NVSim leakage (module-summed across all ranks)
# instead of the old fixed-ratio/single-rank-max approximation.
UNGATED_CAVEAT = ('Ungated static power (NVMain power-down disabled); module-sum '
                   'semantics; real per-technology leakage (see fidelity audit).')

# Gold Master color palette (exact hex codes)
TECHNOLOGY_COLORS = {
    'DDR5_4800': '#0044FF',              # Vibrant Blue
    'pcm_microsoft_2009': '#FF0000',     # Pure Red
    '1T1R_SLC': '#32CD32',               # Forest Green
    '1S1R_SLC': '#00FF00',               # Neon Green
    '1T1R_MLC': '#8A2BE2',               # Dark Violet
    '1S1R_MLC': '#FF00FF'                # Magenta
}

# Generic DRAM examples dropped — narrative focuses on literature-backed baselines only
EXCLUDED_TECHNOLOGIES = {'2D_DRAM_example', '3D_DRAM_example'}


# ============================================================================
# ARCHIVE FUNCTION
# ============================================================================

def archive_old_graphs():
    """Archive existing bar chart PNGs before generating new plots.

    Only touches the three subdirectories owned by this script
    (latency/, power/, pdp/).  The pareto/ and hero/ directories are
    intentionally ignored so peer visualizers can run independently.
    """
    import shutil
    from datetime import datetime

    own_dirs = [Path(LATENCY_DIR), Path(POWER_DIR), Path(PDP_DIR)]

    graph_files = []
    for subdir in own_dirs:
        if subdir.exists():
            for ext in ['*.png', '*.pdf']:
                graph_files.extend(subdir.glob(ext))

    if not graph_files:
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = Path(BASE_OUTPUT_DIR).parent / f"archive_{timestamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for graph_file in graph_files:
        relative_path = graph_file.relative_to(Path(BASE_OUTPUT_DIR))
        dest_file = archive_dir / relative_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(graph_file), str(dest_file))
        logger.info(f"[ARCHIVE] Moved: {relative_path} → archive_{timestamp}/")

    logger.info(f"[ARCHIVE] Created archive folder: {archive_dir.name}\n")


# ============================================================================
# DATA LOADING
# ============================================================================

def load_bar_chart_metrics():
    """Load pre-calculated metrics from CSV."""
    logger.info(f"Loading metrics from {METRICS_FILE}")
    
    if not Path(METRICS_FILE).exists():
        logger.error(f"Metrics file not found: {METRICS_FILE}")
        logger.error("Run process_metrics.py first")
        return None
    
    df = pd.read_csv(METRICS_FILE)
    df = df[~df['Technology'].isin(EXCLUDED_TECHNOLOGIES)]
    logger.info(f"Loaded {len(df)} data points (2D/3D DRAM examples excluded)")
    logger.info(f"Benchmarks: {sorted(df['Benchmark'].unique().tolist())}")
    logger.info(f"Technologies: {sorted(df['Technology'].unique().tolist())}\n")

    return df


def setup_output_directories():
    """Create organized subdirectories for bar charts."""
    logger.info("="*80)
    logger.info("SETUP PHASE: Creating output directories")
    logger.info("="*80)
    
    os.makedirs(LATENCY_DIR, exist_ok=True)
    logger.info(f"[OK] Latency output directory: {LATENCY_DIR}")
    
    os.makedirs(POWER_DIR, exist_ok=True)
    logger.info(f"[OK] Power output directory: {POWER_DIR}")
    
    os.makedirs(PDP_DIR, exist_ok=True)
    logger.info(f"[OK] PDP output directory: {PDP_DIR}\n")


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def format_benchmark_name(benchmark):
    """Format benchmark name for display."""
    BENCHMARK_TITLES = {
        'alexnet_layer1_ifmap': 'AlexNet Layer 1 (IFMAP)',
        'alexnet_layer1_ofmap': 'AlexNet Layer 1 (OFMAP)',
        'gpt2_ifmap': 'GPT-2 (IFMAP)',
        'gcc_spec2017': 'GCC (SPEC2017)',
        'lbm_spec2017': 'LBM (SPEC2017)',
        'stream': 'STREAM'
    }

    if benchmark in BENCHMARK_TITLES:
        return BENCHMARK_TITLES[benchmark]

    name = benchmark.replace('_spec2017', '').replace('_ifmap', '').replace('_ofmap', '')
    parts = name.split('_')
    return ' '.join(part.capitalize() for part in parts)


def format_tech_name(tech):
    """Convert internal technology key to a clean x-axis label."""
    TECH_LABELS = {
        'DDR5_4800':          'DDR5-4800',
        '2D_DRAM_example':    '2D DRAM',
        '3D_DRAM_example':    '3D DRAM',
        'pcm_microsoft_2009': 'PCM',
        '1T1R_SLC':           '1T1R SLC',
        '1T1R_MLC':           '1T1R MLC',
        '1S1R_SLC':           '1S1R SLC',
        '1S1R_MLC':           '1S1R MLC',
    }
    return TECH_LABELS.get(tech, tech.replace('_', ' '))


# ============================================================================
# BAR CHART GENERATION
# ============================================================================

def generate_bar_charts(df):
    """Generate 3 Gold Master bar charts per benchmark: Cycles, Power, PDP."""
    
    if df is None or df.empty:
        logger.error("No data to visualize")
        return
    
    plt.rcdefaults()
    sns.set_theme(style="whitegrid")
    
    benchmarks = sorted(df['Benchmark'].unique())
    
    logger.info("="*80)
    logger.info("GENERATING BAR CHARTS: Gold Master Presentation Quality")
    logger.info("="*80)
    
    for benchmark in benchmarks:
        bench_df = df[df['Benchmark'] == benchmark].copy()
        if bench_df.empty:
            continue

        # Keep only full_dimm for ReRAM; DRAM/PCM are already full_dimm only
        bench_df = bench_df[bench_df['Architecture'] == 'full_dimm'].copy()
        if bench_df.empty:
            logger.warning(f"  No full_dimm data for {benchmark}, skipping")
            continue

        # Enforce canonical technology order; discard any tech not in TECHNOLOGY_COLORS
        tech_order = list(TECHNOLOGY_COLORS.keys())
        bench_df = bench_df[bench_df['Technology'].isin(tech_order)].copy()
        bench_df['Technology'] = pd.Categorical(
            bench_df['Technology'],
            categories=tech_order,
            ordered=True
        )
        bench_df = bench_df.sort_values('Technology').reset_index(drop=True)

        logger.info(f"\n[PROCESSING] Benchmark: {benchmark}")
        logger.info(f"  Data points (full_dimm only): {len(bench_df)}")

        techs = bench_df['Technology'].astype(str).tolist()
        display_techs = [format_tech_name(t) for t in techs]
        bars_x = range(len(bench_df))
        colors = [TECHNOLOGY_COLORS.get(t, '#808080') for t in techs]
        
        # ====================================================================
        # 1. LATENCY BAR CHART (nanoseconds, clock-domain corrected)
        # ====================================================================
        fig, ax = plt.subplots(figsize=(12, 7))

        lat_vals = bench_df['Latency_ns'].values
        bars = ax.bar(bars_x, lat_vals, color=colors, edgecolor='black',
                     linewidth=1.5, alpha=0.85)

        # Add value labels
        for bar, val in zip(bars, lat_vals):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.1f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        # Determine if log scale; add 15% headroom on linear
        max_lat = lat_vals.max()
        min_lat = lat_vals.min()
        if max_lat > 0 and min_lat > 0 and max_lat / min_lat > 10:
            ax.set_yscale('log')
        else:
            ax.set_ylim(0, max_lat * 1.15)

        formatted_bench = format_benchmark_name(benchmark)
        ax.set_ylabel('Average Latency (ns)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Memory Technology', fontsize=12, fontweight='bold')
        ax.set_title(f'{formatted_bench} — Average Latency (ns)',
                    fontsize=14, fontweight='bold', pad=15)

        fig.text(0.99, 0.01,
                'Workload executed on 64-chip (16GB) Full DIMM configuration. '
                'DDR5 @ 2400 MHz; ReRAM/PCM @ 800 MHz.',
                ha='right', va='bottom', fontsize=9, style='italic', color='gray')
        ax.set_xticks(bars_x)
        ax.set_xticklabels(display_techs, rotation=45, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout(rect=[0, 0.02, 1, 1])
        latency_file = os.path.join(LATENCY_DIR, f"Bar_Latency_{benchmark}.png")
        plt.savefig(latency_file, dpi=300, bbox_inches='tight')
        logger.info(f"  ✓ Saved: {latency_file}")
        plt.close(fig)
        
        # ====================================================================
        # 2. POWER BAR CHART (stacked: Static / Dynamic / Refresh)
        # ====================================================================
        fig, ax = plt.subplots(figsize=(14, 7))

        x = list(range(len(bench_df)))

        stat_power_vals = bench_df['Static_Power'].values
        dyn_power_vals = bench_df['Dynamic_Power'].values
        refresh_power_vals = bench_df['Refresh_Power'].values
        colors_list = [TECHNOLOGY_COLORS.get(t, '#808080') for t in bench_df['Technology']]

        bars_static = ax.bar(x, stat_power_vals, color=colors_list,
                            edgecolor='black', linewidth=1.5, alpha=0.9,
                            label='Static / Leakage Power')
        bars_dynamic = ax.bar(x, dyn_power_vals, bottom=stat_power_vals,
                             color=colors_list, edgecolor='black', linewidth=1.5,
                             alpha=0.55, hatch='//', label='Dynamic Access Power')
        bars_refresh = ax.bar(x, refresh_power_vals,
                             bottom=stat_power_vals + dyn_power_vals,
                             color=colors_list, edgecolor='black', linewidth=1.5,
                             alpha=0.25, hatch='xx', label='Refresh Power')

        # Total-height label on top of each stack
        totals = stat_power_vals + dyn_power_vals + refresh_power_vals
        for xi, total in zip(x, totals):
            if total > 0.0001:
                ax.text(xi, total, f'{total:.3f}',
                       ha='center', va='bottom', fontsize=9, fontweight='bold')

        ax.set_yscale('linear')
        ax.set_ylim(0, max(totals) * 1.2 if max(totals) > 0 else 0.25)

        ax.set_ylabel('Power Consumption (Watts)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Memory Technology', fontsize=12, fontweight='bold')
        formatted_bench = format_benchmark_name(benchmark)
        ax.set_title(f'Power Breakdown (Static + Dynamic + Refresh): {formatted_bench}',
                    fontsize=14, fontweight='bold', pad=15)

        ax.set_xticks(x)
        ax.set_xticklabels(display_techs, rotation=45, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)

        # Legend uses neutral gray swatches so component shading (not technology
        # color) is what's being explained
        from matplotlib.patches import Patch
        legend_handles = [
            Patch(facecolor='gray', alpha=0.9, edgecolor='black', label='Static / Leakage Power'),
            Patch(facecolor='gray', alpha=0.55, hatch='//', edgecolor='black', label='Dynamic Access Power'),
            Patch(facecolor='gray', alpha=0.25, hatch='xx', edgecolor='black', label='Refresh Power'),
        ]
        ax.legend(handles=legend_handles, loc='upper right', fontsize=11, framealpha=0.95)

        fig.text(0.99, 0.01,
                'Workload executed on 64-chip (16GB) Full DIMM configuration. '
                'Static = backgroundPower, Dynamic = activatePower + burstPower, Refresh = '
                'refreshPower — module-summed NVMain rank counters, same formula every technology. '
                + UNGATED_CAVEAT,
                ha='right', va='bottom', fontsize=7, style='italic', color='gray')

        plt.tight_layout(rect=[0, 0.03, 1, 1])
        power_file = os.path.join(POWER_DIR, f"Bar_Power_Breakdown_{benchmark}.png")
        plt.savefig(power_file, dpi=300, bbox_inches='tight')
        logger.info(f"  ✓ Saved: {power_file}")
        plt.close(fig)
        
        # ====================================================================
        # 3. PDP BAR CHART
        # ====================================================================
        fig, ax = plt.subplots(figsize=(12, 7))
        
        edp_vals = bench_df['PDP'].values
        bars = ax.bar(bars_x, edp_vals, color=colors, edgecolor='black', linewidth=1.5, alpha=0.85)
        
        # Add value labels
        for i, (bar, val) in enumerate(zip(bars, edp_vals)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.1f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')

        max_edp = edp_vals.max()
        min_edp = edp_vals.min()
        # Axis choice: log when the spread exceeds 10x (same convention used
        # throughout this pipeline for latency/hero-PDP charts) -- ungated
        # leakage widens the PDP range enough that this now reliably triggers
        # (e.g. GCC full_dimm: ~38 to ~50,860 W*ns, a >1000x spread), which
        # is exactly the case log scale exists to handle: linear axes would
        # flatten every non-1T1R bar to an indistinguishable sliver near zero.
        use_log = max_edp > 0 and min_edp > 0 and max_edp / min_edp > 10
        if use_log:
            ax.set_yscale('log')
            logger.info(f"  [AXIS] {benchmark} PDP: log scale "
                       f"(range {min_edp:.1f}-{max_edp:.1f} W*ns, "
                       f"{max_edp/min_edp:.0f}x spread > 10x threshold)")
        else:
            ax.set_ylim(0, max_edp * 1.15)

        ax.set_ylabel('Average PDP (W·ns)' + (' — Log Scale' if use_log else ''),
                     fontsize=12, fontweight='bold')
        ax.set_xlabel('Memory Technology', fontsize=12, fontweight='bold')
        formatted_bench = format_benchmark_name(benchmark)
        ax.set_title(f'Workload Efficiency: {formatted_bench} (PDP)',
                    fontsize=14, fontweight='bold', pad=15)

        ax.text(0.98, 0.95, 'Lower is Better (Higher Efficiency)',
               transform=ax.transAxes, fontsize=9, style='italic',
               verticalalignment='top', horizontalalignment='right',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

        fig.text(0.99, 0.01,
                'Workload executed on 64-chip (16GB) Full DIMM configuration. ' + UNGATED_CAVEAT,
                ha='right', va='bottom', fontsize=7, style='italic', color='gray')
        ax.set_xticks(bars_x)
        ax.set_xticklabels(display_techs, rotation=45, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout(rect=[0, 0.02, 1, 1])
        edp_file = os.path.join(PDP_DIR, f"Bar_PDP_{benchmark}.png")
        plt.savefig(edp_file, dpi=300, bbox_inches='tight')
        logger.info(f"  ✓ Saved: {edp_file}")
        plt.close(fig)
    
    logger.info("\n" + "="*80)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Execute visualization pipeline."""

    global BASE_OUTPUT_DIR, LATENCY_DIR, POWER_DIR, PDP_DIR, METRICS_FILE

    parser = argparse.ArgumentParser(description="MBMM Step 7A: Bar Chart Visualization")
    parser.add_argument("--metrics-file", default=METRICS_FILE,
                        help="Path to processed_bar_chart_metrics.csv (default: results/).")
    parser.add_argument("--output-dir", default=BASE_OUTPUT_DIR,
                        help="Base output directory for latency/power/pdp subdirs (default: results/final_graphs).")
    args = parser.parse_args()
    METRICS_FILE = args.metrics_file
    BASE_OUTPUT_DIR = args.output_dir
    LATENCY_DIR = os.path.join(BASE_OUTPUT_DIR, "latency")
    POWER_DIR = os.path.join(BASE_OUTPUT_DIR, "power")
    PDP_DIR = os.path.join(BASE_OUTPUT_DIR, "pdp")

    logger.info("\n" + "="*80)
    logger.info("STAGE 7A: BAR CHART VISUALIZATION")
    logger.info("="*80 + "\n")

    # Archive old graphs
    archive_old_graphs()
    
    # Setup output directories
    setup_output_directories()
    
    # Load metrics
    df = load_bar_chart_metrics()
    
    # Generate charts
    if df is not None and not df.empty:
        generate_bar_charts(df)
        logger.info("✅ BAR CHART GENERATION COMPLETE\n")
        return True
    else:
        logger.error("✗ BAR CHART GENERATION FAILED\n")
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
