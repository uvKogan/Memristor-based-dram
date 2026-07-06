#!/usr/bin/env python3
"""
MBMM Visualization - Pareto Frontier Visualization

Reads pre-calculated metrics from CSV and generates:
- Pareto frontier plots with multi-dimensional logic
- Technology-specific markers and universal point labeling
- Adaptive axes (log/linear based on data)

This is a 'dumb plotter' - zero math, zero stat parsing.
All calculations performed in process_metrics.py.
"""

import os
import re
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np
from pathlib import Path
from logging_config import setup_logging

logger = setup_logging("visualize_pareto")

# Try to import adjust_text for smart label positioning
try:
    from adjustText import adjust_text
    HAS_ADJUST_TEXT = True
except ImportError:
    HAS_ADJUST_TEXT = False
    logger.warning("adjustText not installed. Using default label positioning.")

# ============================================================================
# CONFIGURATION
# ============================================================================

METRICS_FILE = "/home/yuvalk/MBMM/results/processed_pareto_metrics.csv"
OUTPUT_DIR = "/home/yuvalk/MBMM/results/final_graphs/pareto"

# Technology marker configurations (exact hex codes matching bar charts)
TECHNOLOGY_CONFIGS = {
    '1T1R_SLC': {
        'marker': 'o',
        'color': '#32CD32',  # Forest Green
        'label': '1T1R SLC',
    },
    '1S1R_SLC': {
        'marker': 'o',
        'color': '#00FF00',  # Neon Green
        'label': '1S1R SLC',
    },
    '1T1R_MLC': {
        'marker': 'o',
        'color': '#8A2BE2',  # Dark Violet
        'label': '1T1R MLC',
    },
    '1S1R_MLC': {
        'marker': 'o',
        'color': '#FF00FF',  # Magenta
        'label': '1S1R MLC',
    },
    # Baselines — distinct shapes to separate from ReRAM trajectory lines
    'pcm_microsoft_2009': {
        'marker': 'D',       # Diamond
        'color': '#FF0000',  # Pure Red
        'label': 'PCM (Microsoft 2009)',
    },
    'DDR5_4800': {
        'marker': '*',       # Star
        'color': '#0044FF',  # Vibrant Blue
        'label': 'DDR5-4800 (Baseline)',
    },
    '2D_DRAM_example': {
        'marker': 'h',
        'color': '#00FFFF',
        'label': '2D DRAM',
    },
    '3D_DRAM_example': {
        'marker': 'h',
        'color': '#FF8800',
        'label': '3D DRAM',
    },
}

# Architecture scale configurations
ARCHITECTURE_SCALES = {
    'single':    {'size_base': 200,  'alpha': 0.65, 'edgewidth': 1.5},
    '8chip':     {'size_base': 400,  'alpha': 0.70, 'edgewidth': 1.5},
    '16chip':    {'size_base': 600,  'alpha': 0.80, 'edgewidth': 1.5},
    'full_dimm': {'size_base': 900,  'alpha': 1.0,  'edgewidth': 2.5, 'edgecolor': 'black'}
}

# Architecture ordering for scaling trajectory (Single → 16-Chip → Full DIMM)
# 8chip is excluded: its simulation values are identical to single, adding no
# new architectural information and creating visual clutter.
ARCH_ORDER = ['single', '16chip', 'full_dimm']

# Generic examples dropped — narrative focuses on literature-backed baselines
EXCLUDED_TECHNOLOGIES = {'2D_DRAM_example', '3D_DRAM_example'}


# ============================================================================
# DATA LOADING
# ============================================================================

def load_pareto_metrics():
    """Load pre-calculated Pareto frontier metrics from CSV."""
    logger.info(f"Loading Pareto metrics from {METRICS_FILE}")
    
    if not Path(METRICS_FILE).exists():
        logger.error(f"Metrics file not found: {METRICS_FILE}")
        logger.error("Run process_metrics.py first")
        return None
    
    df = pd.read_csv(METRICS_FILE)
    df = df[~df['Technology'].isin(EXCLUDED_TECHNOLOGIES)]

    # Group by benchmark
    benchmark_data = {}
    for benchmark in df['Benchmark'].unique():
        bench_df = df[df['Benchmark'] == benchmark]
        benchmark_data[benchmark] = bench_df.to_dict('records')

    logger.info(f"Loaded {len(df)} data points (2D/3D DRAM examples excluded)")
    logger.info(f"Benchmarks: {sorted(benchmark_data.keys())}\n")
    
    return benchmark_data


def setup_output_directory():
    """Create output directory for Pareto plots."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"[OK] Output directory: {OUTPUT_DIR}\n")


# ============================================================================
# PARETO PLOT GENERATION
# ============================================================================

def create_pareto_plot(benchmark, data_points):
    """
    Create Pareto frontier plot with technology-specific markers,
    log-scale Y axis, dynamic axes, and outside legend.

    Points are drawn largest-first so smaller markers sit on top, creating
    a visible bullseye effect where all three capacity tiers are discernible
    even when their latency coordinates are identical (Flatline Paradox).
    """

    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    all_texts = []
    plotted_techs = set()

    # Collect true axis extents before drawing (used for xlim padding)
    all_latencies = [d['Latency_ns'] for d in data_points if d['Architecture'] in ARCH_ORDER]
    all_powers    = [d['Power']      for d in data_points if d['Architecture'] in ARCH_ORDER]
    # Include single-point baselines (DDR5, PCM) in extent calculation
    all_latencies += [d['Latency_ns'] for d in data_points
                      if d['Architecture'] not in ARCH_ORDER]
    all_powers    += [d['Power']      for d in data_points
                      if d['Architecture'] not in ARCH_ORDER]

    # Bullseye draw order: largest marker first (bottom), smallest last (top).
    # Descending arch_order_idx → full_dimm drawn before 16chip before single.
    # 8chip rows are excluded (not in ARCH_ORDER / ARCHITECTURE_SCALES).
    RERAM_TECHS = {'1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC'}
    arch_order_idx = {a: i for i, a in enumerate(ARCH_ORDER)}
    data_sorted = sorted(
        [dp for dp in data_points if dp['Architecture'] in ARCH_ORDER
         or dp['Technology'] in ('DDR5_4800', 'pcm_microsoft_2009')],
        key=lambda d: arch_order_idx.get(d['Architecture'], -1),
        reverse=True   # full_dimm first → drawn on bottom; single last → on top
    )

    for dp in data_sorted:
        tech    = dp['Technology']
        arch    = dp['Architecture']
        latency = dp['Latency_ns']
        power   = dp['Power']

        if tech not in TECHNOLOGY_CONFIGS or arch not in ARCHITECTURE_SCALES:
            continue

        tech_config = TECHNOLOGY_CONFIGS[tech]
        arch_config = ARCHITECTURE_SCALES[arch]

        # ReRAM markers semi-transparent for bullseye visibility;
        # DDR5 / PCM baselines stay fully opaque.
        point_alpha = 0.6 if tech in RERAM_TECHS else arch_config['alpha']

        ax.scatter(
            latency, power,
            marker=tech_config['marker'],
            s=arch_config['size_base'],
            color=tech_config['color'],
            alpha=point_alpha,
            edgecolors=arch_config.get('edgecolor', 'none') if arch == 'full_dimm' else 'none',
            linewidths=arch_config['edgewidth'] if arch == 'full_dimm' else 0,
            zorder=3
        )
        plotted_techs.add(tech)

    # Scaling trajectory lines (Single → 16-Chip → Full DIMM)
    for tech in sorted(plotted_techs):
        ordered_pts = []
        for arch in ARCH_ORDER:
            matches = [(d['Latency_ns'], d['Power'])
                       for d in data_points
                       if d['Technology'] == tech and d['Architecture'] == arch]
            if matches:
                ordered_pts.append(matches[0])
        logger.debug(f"  Trajectory {tech}: {len(ordered_pts)} points "
                     f"({[a for a in ARCH_ORDER if any(d['Technology']==tech and d['Architecture']==a for d in data_points)]})")
        if len(ordered_pts) < 2:
            continue
        xs = [p[0] for p in ordered_pts]
        ys = [p[1] for p in ordered_pts]
        ax.plot(xs, ys,
                color=TECHNOLOGY_CONFIGS[tech]['color'],
                linewidth=2.5, linestyle='--', alpha=0.75, zorder=2)

    # ── Axes: dynamic range-based padding so no marker is clipped ──────────
    # Use the full data range to compute absolute padding (not % of minimum)
    # This prevents DDR5 (far-left outlier) from being cut off.
    min_lat, max_lat = min(all_latencies), max(all_latencies)
    min_pwr, max_pwr = min(all_powers),    max(all_powers)
    if min_lat > 0 and max_lat / min_lat > 10:
        ax.set_xscale('log')
        ax.set_xlim(min_lat * 0.8, max_lat * 1.25)
    else:
        x_pad = 0.10 * (max_lat - min_lat)
        ax.set_xlim(min_lat - x_pad, max_lat + 0.05 * (max_lat - min_lat))

    # Linear Y scale with tight symmetric headroom so the 0.06–0.15 W band
    # spreads across the full vertical canvas with auto tick marks.
    ax.set_ylim(min_pwr * 0.90, max_pwr * 1.10)

    # ── Legend: outside the axes to the right ──────────────────────────────
    legend_elements = []
    # Technology entries (canonical order)
    tech_order_for_legend = ['DDR5_4800', 'pcm_microsoft_2009',
                              '1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC']
    for tech_name in tech_order_for_legend:
        if tech_name not in plotted_techs:
            continue
        cfg = TECHNOLOGY_CONFIGS[tech_name]
        legend_elements.append(
            Line2D([0], [0], marker=cfg['marker'], color='w',
                   markerfacecolor=cfg['color'], markersize=9,
                   label=cfg['label'],
                   markeredgecolor='black', markeredgewidth=0.5)
        )

    # Architecture scale entries
    legend_elements += [
        Line2D([0], [0], color='none', label=''),
        Line2D([0], [0], color='none', label='── Capacity Scale ──'),
    ]
    for arch_key, arch_label in [('single',    '1-Chip  (smallest marker)'),
                                  ('16chip',    '16-Chip'),
                                  ('full_dimm', '64-Chip / Full DIMM (outlined)')]:
        acfg = ARCHITECTURE_SCALES[arch_key]
        legend_elements.append(
            Line2D([0], [0], marker='o', color='w', markerfacecolor='#888888',
                   markersize=np.sqrt(acfg['size_base'] / np.pi),
                   label=arch_label,
                   alpha=acfg['alpha'],
                   markeredgecolor='black' if arch_key == 'full_dimm' else 'none',
                   markeredgewidth=2.0 if arch_key == 'full_dimm' else 0)
        )

    lgd = ax.legend(handles=legend_elements,
                    bbox_to_anchor=(1.02, 1), loc='upper left',
                    fontsize=9, title='Technology & Scale',
                    framealpha=0.95, edgecolor='black', title_fontsize=10,
                    labelspacing=1.8)

    # ── Labels & grid ───────────────────────────────────────────────────────
    ax.set_xlabel('Latency (ns)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Total System Power (W)', fontsize=12, fontweight='bold')
    ax.set_title(f'Pareto Frontier — Latency vs. Power: {benchmark}',
                 fontsize=13, fontweight='bold', pad=12)
    ax.grid(True, alpha=0.3, linestyle='--')

    # Reserve 30 % of canvas width for the outside legend — no tight_layout
    plt.subplots_adjust(right=0.70)
    return fig, lgd


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Execute Pareto visualization pipeline."""
    
    logger.info("="*100)
    logger.info("STAGE 7B: PARETO FRONTIER VISUALIZATION")
    logger.info("="*100 + "\n")
    
    # Load metrics
    benchmark_data = load_pareto_metrics()
    
    if not benchmark_data:
        logger.error("✗ PARETO VISUALIZATION FAILED\n")
        return False
    
    # Setup output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate plots
    logger.info("Generating Pareto frontier plots...\n")
    
    for benchmark in sorted(benchmark_data.keys()):
        logger.info(f"  Creating: Pareto_{benchmark}.png")
        fig, lgd = create_pareto_plot(benchmark, benchmark_data[benchmark])
        output_file = Path(OUTPUT_DIR) / f'Pareto_{benchmark}.png'
        fig.savefig(output_file, dpi=150, bbox_inches='tight',
                    bbox_extra_artists=(lgd,))
        logger.info(f"    ✓ Saved: {output_file}")
        plt.close(fig)
    
    logger.info("\n" + "="*100)
    logger.info("✅ PARETO FRONTIER VISUALIZATION COMPLETE")
    logger.info("="*100 + "\n")
    
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
