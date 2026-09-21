#!/usr/bin/env python3
"""
MBMM Visualization - Hero Graphs

Reads pre-calculated metrics from CSV and generates:
- Hero Graph 1: Normalized Area/Density (F² scaling)
- Hero Graph 2: Global Average EDP (geometric mean)

This is a 'dumb plotter' - zero math, zero stat parsing.
All calculations performed in process_metrics.py.
"""

import argparse
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path
from logging_config import setup_logging

logger = setup_logging("visualize_hero_graphs")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Overridable via CLI flags (see main()); defaults unchanged.
OUTPUT_DIR = "/home/yuvalk/MBMM/results/final_graphs/hero"
HERO_METRICS_FILE = "/home/yuvalk/MBMM/results/processed_hero_metrics.csv"
GEOMETRIC_MEANS_FILE = "/home/yuvalk/MBMM/results/processed_geometric_means.csv"

# v3: replaces the old caption+UNGATED_CAVEAT footnote, which measured wider than
# the axes (1299px vs 1085px axes, starting off-canvas at x0=50 vs axes x0=175) --
# see the matching fix in visualize_results.py for the pixel measurements that
# established this bug across the power/PDP/hero-PDP figure families.
STANDARD_FOOTNOTE = (
    'Full-DIMM sums; 250 ms matched window (1 trace cycle = 1/3 ns); 2048x2048 subarrays, '
    'mux 64; DDR5 two 32-bit subchannels, 64 B per access; Start-Gap wear leveling; '
    'NVSim to NVMain.'
)

# Gold Master color palette (exact hex codes)
TECHNOLOGY_COLORS = {
    'DDR5_4800': '#0044FF',              # Vibrant Blue
    'pcm_microsoft_2009': '#FF0000',     # Pure Red
    '1T1R_SLC': '#32CD32',               # Forest Green
    '1S1R_SLC': '#00FF00',               # Neon Green
    '1T1R_MLC': '#8A2BE2',               # Dark Violet
    '1S1R_MLC': '#FF00FF',               # Magenta
    # Secondary/cross-check technologies (T2.4/T2.8): known, but excluded from
    # the primary hero figures -- see PRIMARY_TECHNOLOGIES/SECONDARY_TECHNOLOGIES.
    'DDR5_4800_64B': '#00AACC',          # Teal
    '1T1R_SILICON': '#556B2F',           # Dark Olive
    '1S1R_SILICON': '#CC7722',           # Ochre
}

TECH_LABELS = {
    'DDR5_4800':          'DDR5-4800',
    'pcm_microsoft_2009': 'PCM',
    '1T1R_SLC':           '1T1R SLC',
    '1T1R_MLC':           '1T1R MLC',
    '1S1R_SLC':           '1S1R SLC',
    '1S1R_MLC':           '1S1R MLC',
    '2D_DRAM_example':    '2D DRAM',
    '3D_DRAM_example':    '3D DRAM',
    'DDR5_4800_64B':      'DDR5-4800 (64 B cross-check)',
    '1T1R_SILICON':       '1T1R silicon timings (Micron 16 Gb)',
    '1S1R_SILICON':       '1S1R silicon timings (SanDisk 32 Gb)',
}

# Generic DRAM examples dropped - narrative focuses on literature-backed baselines only
EXCLUDED_TECHNOLOGIES = {'2D_DRAM_example', '3D_DRAM_example'}

# The primary hero figures show exactly these six -- see visualize_results.py
# for the identical convention (kept as a separate copy per-script, matching
# this codebase's existing "dumb plotter, self-contained config" style).
PRIMARY_TECHNOLOGIES = {
    'DDR5_4800', 'pcm_microsoft_2009',
    '1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC',
}
SECONDARY_TECHNOLOGIES = {'DDR5_4800_64B', '1T1R_SILICON', '1S1R_SILICON'}
KNOWN_TECHNOLOGIES = PRIMARY_TECHNOLOGIES | SECONDARY_TECHNOLOGIES | EXCLUDED_TECHNOLOGIES


def primary_only(df, column='Technology'):
    """Rows whose Technology is in PRIMARY_TECHNOLOGIES -- drops known
    secondary technologies (DDR5_4800_64B/1T1R_SILICON/1S1R_SILICON)
    explicitly rather than silently."""
    return df[df[column].isin(PRIMARY_TECHNOLOGIES)]


def primary_only_dict(d):
    """Same as primary_only() for a {Technology: value} dict (geometric means)."""
    return {k: v for k, v in d.items() if k in PRIMARY_TECHNOLOGIES}


def _check_known_technologies(techs, source):
    """Raise loudly on a genuinely unknown Technology label; known-but-
    secondary labels (64B/SILICON) are handled by the primary-set filter in
    each figure function, not here."""
    unknown = sorted(set(techs) - KNOWN_TECHNOLOGIES)
    if unknown:
        raise ValueError(
            f"{source}: unknown Technology label(s) {unknown} -- add them to "
            f"PRIMARY_TECHNOLOGIES/SECONDARY_TECHNOLOGIES/EXCLUDED_TECHNOLOGIES "
            f"in visualize_hero_graphs.py before plotting."
        )


# ============================================================================
# DATA LOADING
# ============================================================================

def load_hero_metrics():
    """Load pre-calculated hero graph metrics from CSV."""
    logger.info(f"Loading hero metrics from {HERO_METRICS_FILE}")
    
    if not Path(HERO_METRICS_FILE).exists():
        logger.error(f"Metrics file not found: {HERO_METRICS_FILE}")
        logger.error("Run process_metrics.py first")
        return None
    
    df = pd.read_csv(HERO_METRICS_FILE)
    _check_known_technologies(df['Technology'].unique(), HERO_METRICS_FILE)
    logger.info(f"Loaded {len(df)} data points\n")
    return df


def load_geometric_means():
    """Load pre-calculated geometric mean EDP values from CSV."""
    logger.info(f"Loading geometric means from {GEOMETRIC_MEANS_FILE}")
    
    if not Path(GEOMETRIC_MEANS_FILE).exists():
        logger.error(f"Geometric means file not found: {GEOMETRIC_MEANS_FILE}")
        logger.error("Run process_metrics.py first")
        return None
    
    df = pd.read_csv(GEOMETRIC_MEANS_FILE)
    _check_known_technologies(df['Technology'].unique(), GEOMETRIC_MEANS_FILE)
    geom_means = dict(zip(df['Technology'], df['Geometric_Mean_PDP']))

    logger.info(f"Loaded geometric means for {len(geom_means)} technologies\n")
    return geom_means


def create_output_directory():
    """Create output directory for hero graphs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"[OK] Output directory: {OUTPUT_DIR}\n")


# ============================================================================
# HERO GRAPH 1: NORMALIZED AREA DENSITY
# ============================================================================

def generate_hero_area_density(df_metrics):
    """Generate Hero Graph 1: Normalized Area/Density (F² scaling)."""
    
    logger.info("="*80)
    logger.info("HERO GRAPH 1: Normalized Area/Density (F² Scaling @ 22nm)")
    logger.info("="*80)
    
    # Get unique technologies and their area density ratios
    # Average area density per technology (in case of multiple benchmarks/archs).
    # Only the primary set is shown here -- secondary/cross-check technologies
    # (DDR5_4800_64B, 1T1R_SILICON, 1S1R_SILICON) are known but filtered out
    # explicitly, not left to an incidental EXCLUDED_TECHNOLOGIES-only filter.
    df_metrics = primary_only(df_metrics)
    area_by_tech = df_metrics.groupby('Technology')['Area_Density_Ratio'].mean()

    # Sort descending - higher ratio = denser = better
    area_by_tech = area_by_tech.sort_values(ascending=False)

    technologies = area_by_tech.index.tolist()
    values = area_by_tech.values
    colors = [TECHNOLOGY_COLORS.get(tech, '#808080') for tech in technologies]

    # Create display labels
    display_labels = [TECH_LABELS.get(tech, tech.replace('_', ' ')) for tech in technologies]

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))

    # Create bars
    bars = ax.bar(range(len(technologies)), values, color=colors, edgecolor='black',
                  linewidth=2.0, alpha=0.85)

    # Add value labels on top of bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{val:.2f}',
               ha='center', va='bottom', fontsize=12, fontweight='bold')

    # Formatting
    ax.set_ylabel('Normalized Area Density (vs DDR5) - Higher is Better', fontsize=14, fontweight='bold')
    ax.set_xlabel('Memory Technology', fontsize=14, fontweight='bold')
    ax.set_title('Silicon Density Comparison: Normalized Area Density (Hybrid-Empirical)',
                fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(range(len(technologies)))
    ax.set_xticklabels(display_labels, rotation=45, ha='right', fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, max(values) * 1.15)

    # Add source caption
    fig.text(0.5, 0.02,
            'Normalized area density = DDR5 baseline (35 mm²/GB) ÷ technology mm²/GB. '
            'Values > 1.0 indicate denser integration than DDR5. ReRAM area extracted from NVSim @ 22nm.',
            ha='center', fontsize=9, style='italic')
    
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    output_file = os.path.join(OUTPUT_DIR, "Hero_Normalized_Area.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved: {output_file}\n")
    plt.close(fig)


# ============================================================================
# HERO GRAPH 2: GLOBAL AVERAGE EDP
# ============================================================================

def generate_hero_average_pdp(geometric_means):
    """Generate Hero Graph 2: Overall System Efficiency (Geometric Mean PDP)."""

    logger.info("="*80)
    logger.info("HERO GRAPH 2: Overall System Efficiency (Geometric Mean PDP)")
    logger.info("="*80)
    
    # Sort by EDP (ascending = better efficiency); only the primary set is
    # shown (secondary/cross-check technologies filtered out explicitly, see
    # PRIMARY_TECHNOLOGIES).
    geometric_means = primary_only_dict(geometric_means)
    sorted_techs = sorted(geometric_means.items(), key=lambda x: x[1])
    technologies = [tech for tech, _ in sorted_techs]
    values = [edp for _, edp in sorted_techs]

    # Get colors
    colors = [TECHNOLOGY_COLORS.get(tech, '#808080') for tech in technologies]

    # Create display labels
    display_labels = [TECH_LABELS.get(tech, tech.replace('_', ' ')) for tech in technologies]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Create bars
    bars = ax.bar(range(len(technologies)), values, color=colors, edgecolor='black',
                  linewidth=2.0, alpha=0.85)
    
    # Add value labels on top of bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
               f'{val:.2f}',
               ha='center', va='bottom', fontsize=12, fontweight='bold')
    
    # Axis choice: log when the spread exceeds 10x -- same convention used for
    # every latency/PDP chart in this pipeline. With real, ungated leakage the
    # geometric-mean PDP spread is now large (~38 to ~49,000+ W*ns across
    # technologies), so this reliably triggers; a linear axis would flatten
    # every technology except 1T1R to an indistinguishable sliver near zero.
    max_val = max(values)
    min_val = min(values)
    use_log = max_val > 0 and min_val > 0 and max_val / min_val > 10
    if use_log:
        ax.set_yscale('log')
        # "Lower is better" appears exactly once, here in the ylabel (v3 dedupe -
        # this figure never had a separate in-axes annotation box).
        ylabel = 'Average PDP (W·ns), log scale - lower is better'
        logger.info(f"  [AXIS] Hero_Average_PDP: log scale "
                   f"(range {min_val:.1f}-{max_val:.1f} W*ns, {max_val/min_val:.0f}x spread > 10x threshold)")
    else:
        ylabel = 'Average PDP (W·ns) - lower is better'

    # Formatting
    ax.set_ylabel(ylabel, fontsize=14, fontweight='bold')
    ax.set_xlabel('Memory Technology', fontsize=14, fontweight='bold')
    ax.set_title('Overall System Efficiency (Geometric Mean PDP)',
                fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(range(len(technologies)))
    ax.set_xticklabels(display_labels, rotation=45, ha='right', fontsize=11)
    ax.grid(axis='y', alpha=0.3)

    # Standardized v3 footnote (see STANDARD_FOOTNOTE definition)
    foot = fig.text(0.5, 0.01, STANDARD_FOOTNOTE, ha='center', va='bottom',
                    fontsize=8, style='italic', color='gray', linespacing=1.4)

    plt.tight_layout(rect=[0, 0.08, 1, 1])
    output_file = os.path.join(OUTPUT_DIR, "Hero_Average_PDP.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight', bbox_extra_artists=(foot,))
    logger.info(f"✓ Saved: {output_file}\n")
    plt.close(fig)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Execute hero graphs visualization pipeline."""

    global OUTPUT_DIR, HERO_METRICS_FILE, GEOMETRIC_MEANS_FILE

    parser = argparse.ArgumentParser(description="MBMM Step 7C: Hero Graphs Generation")
    parser.add_argument("--hero-metrics-file", default=HERO_METRICS_FILE,
                        help="Path to processed_hero_metrics.csv (default: results/).")
    parser.add_argument("--geometric-means-file", default=GEOMETRIC_MEANS_FILE,
                        help="Path to processed_geometric_means.csv (default: results/).")
    parser.add_argument("--output-dir", default=OUTPUT_DIR,
                        help="Output directory for hero graphs (default: results/final_graphs/hero).")
    args = parser.parse_args()
    HERO_METRICS_FILE = args.hero_metrics_file
    GEOMETRIC_MEANS_FILE = args.geometric_means_file
    OUTPUT_DIR = args.output_dir

    logger.info("\n" + "="*80)
    logger.info("STAGE 7C: HERO GRAPHS GENERATION")
    logger.info("="*80 + "\n")

    # Create output directory
    create_output_directory()
    
    # Load metrics
    df_hero = load_hero_metrics()
    geometric_means = load_geometric_means()
    
    if df_hero is None or geometric_means is None:
        logger.error("✗ HERO GRAPHS GENERATION FAILED\n")
        return False
    
    # Generate graphs
    generate_hero_area_density(df_hero)
    generate_hero_average_pdp(geometric_means)

    logger.info("="*80)
    logger.info("✅ HERO GRAPHS GENERATION COMPLETE")
    logger.info("="*80)
    logger.info(f"\nOutput directory: {OUTPUT_DIR}/")
    logger.info(f"Generated files:")
    logger.info(f"  1. Hero_Normalized_Area.png (Hybrid-Empirical)")
    logger.info(f"  2. Hero_Average_PDP.png (Empirical)\n")
    
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
