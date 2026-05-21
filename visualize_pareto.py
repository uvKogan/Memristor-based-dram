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
        'size_base': 100
    },
    '1S1R_SLC': {
        'marker': '*',
        'color': '#00FF00',  # Neon Green
        'label': '1S1R SLC',
        'size_base': 150
    },
    '1T1R_MLC': {
        'marker': 'o',
        'color': '#8A2BE2',  # Dark Violet
        'label': '1T1R MLC',
        'size_base': 100
    },
    '1S1R_MLC': {
        'marker': '*',
        'color': '#FF00FF',  # Magenta
        'label': '1S1R MLC',
        'size_base': 150
    },
    'PCM': {
        'marker': 's',
        'color': '#FF0000',  # Pure Red
        'label': 'PCM',
        'size_base': 120
    },
    'pcm_microsoft_2009': {
        'marker': 's',
        'color': '#FF0000',  # Pure Red
        'label': 'PCM',
        'size_base': 120
    },
    'DDR5_4800': {
        'marker': 'D',
        'color': '#0044FF',  # Vibrant Blue
        'label': 'DDR5-4800 (Dual Channel)',
        'size_base': 120
    },
    '2D_DRAM_example': {
        'marker': 'h',
        'color': '#00FFFF',  # Cyan
        'label': '2D DRAM',
        'size_base': 120
    },
    '3D_DRAM_example': {
        'marker': 'h',
        'color': '#FF8800',  # Bright Orange
        'label': '3D DRAM',
        'size_base': 120
    },
}

# Architecture scale configurations
ARCHITECTURE_SCALES = {
    'single': {'size_base': 150, 'alpha': 0.6, 'edgewidth': 1.5},
    '8chip': {'size_base': 300, 'alpha': 0.6, 'edgewidth': 1.5},
    '16chip': {'size_base': 450, 'alpha': 0.6, 'edgewidth': 1.5},
    'full_dimm': {'size_base': 600, 'alpha': 1.0, 'edgewidth': 2.0, 'edgecolor': 'black'}
}


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
    
    # Group by benchmark
    benchmark_data = {}
    for benchmark in df['Benchmark'].unique():
        bench_df = df[df['Benchmark'] == benchmark]
        benchmark_data[benchmark] = bench_df.to_dict('records')
    
    logger.info(f"Loaded {len(df)} data points")
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
    Create Pareto frontier plot with technology-specific markers
    and adaptive axes (log/linear).
    """
    
    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    all_texts = []
    plotted_techs = set()
    
    # Plot all data points
    for data_point in data_points:
        tech = data_point['Technology']
        arch = data_point['Architecture']
        latency = data_point['Total_Execution_Cycles']
        power = data_point['Power']
        
        if tech not in TECHNOLOGY_CONFIGS:
            logger.warning(f"Unknown technology: {tech}")
            continue
        
        if arch not in ARCHITECTURE_SCALES:
            logger.warning(f"Unknown architecture: {arch}")
            continue
        
        tech_config = TECHNOLOGY_CONFIGS[tech]
        arch_config = ARCHITECTURE_SCALES[arch]
        
        marker_size = arch_config['size_base']
        edge_color = arch_config.get('edgecolor', 'black')
        edge_width = arch_config['edgewidth']
        
        # Plot point
        ax.scatter(
            latency, power,
            marker=tech_config['marker'],
            s=marker_size,
            color=tech_config['color'],
            alpha=arch_config['alpha'],
            edgecolors=edge_color if arch == 'full_dimm' else 'none',
            linewidth=edge_width if arch == 'full_dimm' else 0,
            zorder=3
        )
        
        plotted_techs.add(tech)
        
        # Add text label with (Latency, Power) coordinates
        label_text = f"({latency:.0f}, {power:.3f})"
        
        annotation = ax.annotate(
            label_text,
            xy=(latency, power),
            xytext=(20, 20),
            textcoords='offset points',
            fontsize=9,
            fontweight='bold',
            ha='left',
            va='bottom',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=2),
            zorder=5
        )
        all_texts.append(annotation)
    
    # Use adjust_text if available
    if HAS_ADJUST_TEXT and all_texts:
        try:
            adjust_text(all_texts, ax=ax,
                       arrowprops=dict(arrowstyle='-', lw=0.5, color='gray', alpha=0.5),
                       expand_points=(1.5, 1.5), expand_text=(1.2, 1.2),
                       force_points=(0.5, 0.5))
        except Exception as e:
            logger.debug(f"adjust_text failed for {benchmark}: {e}")
    
    # Determine if log scale for X-axis
    latencies = [d['Total_Execution_Cycles'] for d in data_points]
    min_lat = min(latencies)
    max_lat = max(latencies)
    
    if max_lat > 0 and min_lat > 0 and max_lat / min_lat > 10:
        ax.set_xscale('log')
        xlabel = 'Total Execution Cycles (Log Scale)'
    else:
        xlabel = 'Total Execution Cycles'
    
    # Set Y-axis fixed range for consistency
    ax.set_ylim(0, 1.2)
    
    # Create legend for technologies
    legend_elements = []
    for tech_name in sorted(plotted_techs):
        config = TECHNOLOGY_CONFIGS[tech_name]
        legend_elements.append(
            Line2D([0], [0], marker=config['marker'], color='w',
                   markerfacecolor=config['color'], markersize=8,
                   label=config['label'], markeredgecolor='black', markeredgewidth=0.5)
        )
    
    # Add architecture scale legend
    legend_elements.append(Line2D([0], [0], color='none', label=''))
    legend_elements.append(Line2D([0], [0], color='none', label='Architecture Scale:'))
    
    arch_indicators = [
        ('single', 'Single (smallest)'),
        ('8chip', '8-Chip'),
        ('16chip', '16-Chip'),
        ('full_dimm', 'Full DIMM (largest, outlined)')
    ]
    
    for arch_key, arch_label in arch_indicators:
        arch_config = ARCHITECTURE_SCALES[arch_key]
        size = arch_config['size_base']
        legend_elements.append(
            Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                   markersize=np.sqrt(size/np.pi), label=arch_label,
                   alpha=arch_config['alpha'],
                   markeredgecolor='black' if arch_key == 'full_dimm' else 'none',
                   markeredgewidth=2.0 if arch_key == 'full_dimm' else 0)
        )
    
    ax.legend(handles=legend_elements, loc='best', fontsize=9,
              title='Architecture & Capacity Scaling', framealpha=0.95,
              edgecolor='black', title_fontsize=10)
    
    # Formatting
    ax.set_ylabel('Total System Power (W)', fontsize=12, fontweight='bold')
    ax.set_xlabel(xlabel, fontsize=12, fontweight='bold')
    ax.set_title(f'Gold Master Pareto Frontier: {benchmark}', fontsize=13, fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')
    
    plt.tight_layout()
    return fig


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
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Generate plots
    logger.info("Generating Pareto frontier plots...\n")
    
    for benchmark in sorted(benchmark_data.keys()):
        logger.info(f"  Creating: Pareto_{benchmark}.png")
        fig = create_pareto_plot(benchmark, benchmark_data[benchmark])
        output_file = Path(OUTPUT_DIR) / f'Pareto_{benchmark}.png'
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
        logger.info(f"    ✓ Saved: {output_file}")
        plt.close(fig)
    
    logger.info("\n" + "="*100)
    logger.info("✅ PARETO FRONTIER VISUALIZATION COMPLETE")
    logger.info("="*100 + "\n")
    
    return True


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
