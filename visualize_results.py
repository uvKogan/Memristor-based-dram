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

# v3 standardized footnote: the old single-line ungated-leakage caveat measured wider
# than the axes on the power (1757px vs 1085px axes, starting off-canvas at x=-372)
# and hero-PDP (1299px vs 1085px) figures, and hung off the axes edge on PDP figures
# (right-aligned against the figure edge rather than the axes). This verbatim,
# pre-wrapped two-liner replaces it on every figure that carries a footnote except
# Pareto, whose existing single-line footnote was measured to already fit within
# its axes bounds (924px vs 1380px) and so was left untouched per the v3 scope.
STANDARD_FOOTNOTE = (
    'Full-DIMM module sums; ReRAM worst-case ungated (NVMain power-down disabled in source).\n'
    'DRAM/PCM baselines model standard idle behavior. MBMM pipeline: NVSim→NVMain, 200M cycles.'
)

# Technology order for the v3 two-panel power breakdown chart only (groups SLC/MLC
# pairs together rather than by cell topology); latency/PDP charts keep the
# original TECHNOLOGY_COLORS key order.
POWER_TECH_ORDER_V3 = ['DDR5_4800', 'pcm_microsoft_2009',
                       '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC']

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
        # 2. POWER BREAKDOWN (v3: two-panel — total power (log) | composition %)
        # ====================================================================
        # Redesigned from a single linear-stacked chart because the repaired
        # leakage model spans 0.073 W (PCM) to 51 W (1T1R) — a >600x range that
        # renders DDR5/PCM/1S1R as invisible slivers on a linear axis, and a log
        # axis is not valid on *stacked* bars (segment heights lose meaning).
        # Left panel isolates magnitude (log-scale, one bar per technology);
        # right panel isolates the static/dynamic/refresh mix as 100%-stacked
        # percentages, independent of the underlying magnitude.
        from matplotlib.patches import Patch

        power_order = [t for t in POWER_TECH_ORDER_V3
                       if t in bench_df['Technology'].astype(str).unique()]
        power_df = bench_df.set_index(bench_df['Technology'].astype(str)).loc[power_order]

        p_display = [format_tech_name(t) for t in power_order]
        p_colors = [TECHNOLOGY_COLORS.get(t, '#808080') for t in power_order]
        px = list(range(len(power_order)))

        p_totals = power_df['Power'].values
        p_stat = power_df['Static_Power'].values
        p_dyn = power_df['Dynamic_Power'].values
        p_ref = power_df['Refresh_Power'].values

        # figsize height tuned (6.9in) so the post-tight-crop canvas lands near
        # the ≈2.55:1 aspect of the legacy 5319x2085px power figures, keeping
        # the book's embed slot sized correctly.
        fig, (axL, axR) = plt.subplots(1, 2, figsize=(16, 6.9))

        # -- Left: total module power, log scale --
        bars = axL.bar(px, p_totals, color=p_colors, edgecolor='black',
                       linewidth=1.5, alpha=0.9)
        for bar, val in zip(bars, p_totals):
            label = f'{val:.4f} W' if val < 1 else f'{val:.2f} W'
            axL.text(bar.get_x() + bar.get_width() / 2., bar.get_height(), label,
                    ha='center', va='bottom', fontsize=9, fontweight='bold')
        axL.set_yscale('log')
        axL.set_ylim(p_totals.min() * 0.3, p_totals.max() * 3)
        axL.set_ylabel('Total Module Power (W), log scale', fontsize=11, fontweight='bold')
        axL.set_xlabel('Memory Technology', fontsize=11, fontweight='bold')
        axL.set_title('Total Module Power', fontsize=12, fontweight='bold')
        axL.set_xticks(px)
        axL.set_xticklabels(p_display, rotation=45, ha='right', fontsize=9)
        axL.grid(axis='y', which='both', alpha=0.3)

        # -- Right: 100%-stacked composition (Static / Dynamic / Refresh) --
        stat_pct = p_stat / p_totals * 100
        dyn_pct = p_dyn / p_totals * 100
        ref_pct = p_ref / p_totals * 100

        axR.bar(px, stat_pct, color=p_colors, edgecolor='black', linewidth=1.5, alpha=0.9)
        axR.bar(px, dyn_pct, bottom=stat_pct, color=p_colors, edgecolor='black',
               linewidth=1.5, alpha=0.55, hatch='//')
        axR.bar(px, ref_pct, bottom=stat_pct + dyn_pct, color=p_colors, edgecolor='black',
               linewidth=1.5, alpha=0.25, hatch='xx')

        # Label segments ≥3% only — smaller slivers (e.g. 1T1R's ~0.01% dynamic
        # share) can't fit a readable label and would just clutter the panel.
        for xi, (s, d, r) in enumerate(zip(stat_pct, dyn_pct, ref_pct)):
            if s >= 3:
                axR.text(xi, s / 2, f'{s:.1f}%', ha='center', va='center',
                        fontsize=8, fontweight='bold')
            if d >= 3:
                axR.text(xi, s + d / 2, f'{d:.1f}%', ha='center', va='center',
                        fontsize=8, fontweight='bold')
            if r >= 3:
                axR.text(xi, s + d + r / 2, f'{r:.1f}%', ha='center', va='center',
                        fontsize=8, fontweight='bold')

        # 22% headroom above the 100% line: every bar reaches y=100 (100%-
        # stacked), so an in-axes legend at any 'upper' position would clip
        # the top of whichever bars it sits over without this margin.
        axR.set_ylim(0, 122)
        axR.set_yticks(range(0, 101, 20))
        axR.set_ylabel('Power Composition (%)', fontsize=11, fontweight='bold')
        axR.set_xlabel('Memory Technology', fontsize=11, fontweight='bold')
        axR.set_title('Power Composition', fontsize=12, fontweight='bold')
        axR.set_xticks(px)
        axR.set_xticklabels(p_display, rotation=45, ha='right', fontsize=9)
        axR.grid(axis='y', alpha=0.3)

        legend_handles = [
            Patch(facecolor='gray', alpha=0.9, edgecolor='black', label='Static / Leakage Power'),
            Patch(facecolor='gray', alpha=0.55, hatch='//', edgecolor='black', label='Dynamic Access Power'),
            Patch(facecolor='gray', alpha=0.25, hatch='xx', edgecolor='black', label='Refresh Power'),
        ]
        axR.legend(handles=legend_handles, loc='upper right', fontsize=8, framealpha=0.95)

        formatted_bench = format_benchmark_name(benchmark)
        fig.suptitle(f'Power Breakdown: {formatted_bench}', fontsize=14, fontweight='bold')

        foot = fig.text(0.5, 0.01, STANDARD_FOOTNOTE, ha='center', va='bottom',
                        fontsize=7, style='italic', color='gray', linespacing=1.4)

        plt.tight_layout(rect=[0, 0.08, 1, 0.94])
        power_file = os.path.join(POWER_DIR, f"Bar_Power_Breakdown_{benchmark}.png")
        plt.savefig(power_file, dpi=300, bbox_inches='tight', bbox_extra_artists=(foot,))
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

        # "Lower is better" folded into the ylabel (v3) — the old in-axes
        # annotation box overlapped bars/value labels on several benchmarks.
        pdp_ylabel = ('Average PDP (W·ns), log scale — lower is better' if use_log
                     else 'Average PDP (W·ns) — lower is better')
        ax.set_ylabel(pdp_ylabel, fontsize=12, fontweight='bold')
        ax.set_xlabel('Memory Technology', fontsize=12, fontweight='bold')
        formatted_bench = format_benchmark_name(benchmark)
        ax.set_title(f'Workload Efficiency: {formatted_bench} (PDP)',
                    fontsize=14, fontweight='bold', pad=15)

        foot = fig.text(0.5, 0.01, STANDARD_FOOTNOTE, ha='center', va='bottom',
                        fontsize=7, style='italic', color='gray', linespacing=1.4)
        ax.set_xticks(bars_x)
        ax.set_xticklabels(display_techs, rotation=45, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout(rect=[0, 0.06, 1, 1])
        edp_file = os.path.join(PDP_DIR, f"Bar_PDP_{benchmark}.png")
        plt.savefig(edp_file, dpi=300, bbox_inches='tight', bbox_extra_artists=(foot,))
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
