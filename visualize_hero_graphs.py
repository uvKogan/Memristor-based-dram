#!/usr/bin/env python3
"""
MBMM Visualization - Hero Graphs

Reads pre-calculated metrics from CSV and generates:
- Hero Graph 1: Normalized Area/Density (F² scaling)
- Hero Graph 2: Global Average EDP (geometric mean)

This is a 'dumb plotter' - zero math, zero stat parsing.
All calculations performed in process_metrics.py.
"""

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

OUTPUT_DIR = "/home/yuvalk/MBMM/results/final_graphs/hero"
HERO_METRICS_FILE = "/home/yuvalk/MBMM/results/processed_hero_metrics.csv"
GEOMETRIC_MEANS_FILE = "/home/yuvalk/MBMM/results/processed_geometric_means.csv"

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
    # Average area density per technology (in case of multiple benchmarks/archs)
    df_metrics = df_metrics[~df_metrics['Technology'].isin(EXCLUDED_TECHNOLOGIES)]
    area_by_tech = df_metrics.groupby('Technology')['Area_Density_Ratio'].mean()
    
    # Sort descending — higher ratio = denser = better
    area_by_tech = area_by_tech.sort_values(ascending=False)

    technologies = area_by_tech.index.tolist()
    values = area_by_tech.values
    colors = [TECHNOLOGY_COLORS.get(tech, '#808080') for tech in technologies]

    # Create display labels
    display_labels = []
    for tech in technologies:
        if tech == 'DDR5_4800':
            display_labels.append('DDR5-4800')
        elif tech == 'pcm_microsoft_2009':
            display_labels.append('PCM')
        elif tech == '2D_DRAM_example':
            display_labels.append('2D DRAM')
        elif tech == '3D_DRAM_example':
            display_labels.append('3D DRAM')
        else:
            display_labels.append(tech.replace('_', ' '))

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
    ax.set_ylabel('Normalized Area Density (vs DDR5) — Higher is Better', fontsize=14, fontweight='bold')
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
    
    # Sort by EDP (ascending = better efficiency), excluding generic DRAM examples
    geometric_means = {k: v for k, v in geometric_means.items()
                       if k not in EXCLUDED_TECHNOLOGIES}
    sorted_techs = sorted(geometric_means.items(), key=lambda x: x[1])
    technologies = [tech for tech, _ in sorted_techs]
    values = [edp for _, edp in sorted_techs]
    
    # Get colors
    colors = [TECHNOLOGY_COLORS.get(tech, '#808080') for tech in technologies]
    
    # Create display labels
    display_labels = []
    for tech in technologies:
        if tech == 'DDR5_4800':
            display_labels.append('DDR5')
        elif tech == 'pcm_microsoft_2009':
            display_labels.append('PCM')
        else:
            display_labels.append(tech.replace('_', ' '))
    
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
    
    # Determine if log scale needed
    max_val = max(values)
    min_val = min(values)
    if max_val > 0 and min_val > 0 and max_val / min_val > 10:
        ax.set_yscale('log')
        ylabel = 'Average PDP (Cycle-Watts) — Lower is Better — Log Scale'
    else:
        ylabel = 'Average PDP (Cycle-Watts) — Lower is Better'
    
    # Formatting
    ax.set_ylabel(ylabel, fontsize=14, fontweight='bold')
    ax.set_xlabel('Memory Technology', fontsize=14, fontweight='bold')
    ax.set_title('Overall System Efficiency (Geometric Mean PDP)',
                fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(range(len(technologies)))
    ax.set_xticklabels(display_labels, rotation=45, ha='right', fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    # Add source caption
    fig.text(0.5, 0.02,
            'Data generated via MBMM Pipeline (NVSim + NVMain 2.0). '
            'PDP = Total Execution Cycles × Total System Power. '
            'Geometric mean across all benchmarks — Full DIMM (64-chip) configuration.',
            ha='center', fontsize=10, style='italic')
    
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    output_file = os.path.join(OUTPUT_DIR, "Hero_Average_PDP.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"✓ Saved: {output_file}\n")
    plt.close(fig)


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Execute hero graphs visualization pipeline."""
    
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
