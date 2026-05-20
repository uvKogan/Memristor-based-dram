#!/usr/bin/env python3
"""
GOLD MASTER - Pareto Frontier Visualization with Multi-Dimensional Logic
Differentiated Markers, Universal Point Labeling, Adaptive Axes
Technology-specific markers: SLC (o/*), MLC (o/*), PCM (s), DDR5 (D), DRAM variants (h)
"""

import re
import sys
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

# Try to import adjust_text for smart label positioning
try:
    from adjustText import adjust_text
    HAS_ADJUST_TEXT = True
except ImportError:
    HAS_ADJUST_TEXT = False
    print("⚠ Warning: adjustText not installed. Using default label positioning.")

# ============================================================================
# GOLD MASTER TECHNOLOGY AND MARKER CONFIGURATION
# ============================================================================

TECHNOLOGY_CONFIGS = {
    '1T1R_SLC': {
        'patterns': [r'reram.*1t1r.*slc(?!.*mlc)'],
        'marker': 'o',
        'color': '#00FF00',  # Neon Green
        'label': '1T1R SLC',
        'size_base': 100
    },
    '1S1R_SLC': {
        'patterns': [r'reram.*selector.*slc(?!.*mlc)'],
        'marker': '*',
        'color': '#00FF00',  # Neon Green
        'label': '1S1R SLC',
        'size_base': 150
    },
    '1T1R_MLC': {
        'patterns': [r'reram.*1t1r.*mlc'],
        'marker': 'o',
        'color': '#FF00FF',  # Neon Magenta
        'label': '1T1R MLC',
        'size_base': 100
    },
    '1S1R_MLC': {
        'patterns': [r'reram.*selector.*mlc'],
        'marker': '*',
        'color': '#FF00FF',  # Neon Magenta
        'label': '1S1R MLC',
        'size_base': 150
    },
    'PCM': {
        'patterns': [r'pcm_microsoft_2009', r'pcm'],
        'marker': 's',
        'color': '#FF0000',  # Pure Red
        'label': 'PCM',
        'size_base': 120
    },
    'DDR5': {
        'patterns': [r'ddr5.*4800.*dram', r'ddr5'],
        'marker': 'D',
        'color': '#0044FF',  # Vibrant Blue
        'label': 'DDR5-4800 (Dual Channel)',
        'size_base': 120
    },
    '2D_DRAM': {
        'patterns': [r'2d.*dram'],
        'marker': 'h',
        'color': '#00FFFF',  # Cyan
        'label': '2D DRAM',
        'size_base': 120
    },
    '3D_DRAM': {
        'patterns': [r'3d.*dram'],
        'marker': 'p',
        'color': '#FF8800',  # Bright Orange
        'label': '3D DRAM',
        'size_base': 120
    }
}

# Architecture scale affects marker size and edge properties
ARCHITECTURE_SCALES = {
    'single': {'size_base': 150, 'alpha': 0.6, 'edgewidth': 1.5},
    '8chip': {'size_base': 300, 'alpha': 0.6, 'edgewidth': 1.5},
    '16chip': {'size_base': 450, 'alpha': 0.6, 'edgewidth': 1.5},
    'full_dimm': {'size_base': 600, 'alpha': 1.0, 'edgewidth': 2.0, 'edgecolor': 'black'}
}

class DataExtractor:
    """Extract metrics from NVMain simulator output files"""
    
    @staticmethod
    def extract_latency(content):
        """Extract average total latency in cycles"""
        pattern = r'i0\.defaultMemory\.channel\d+\.FRFCFS[^.]*?\.averageTotalLatency\s+([\d.e+-]+)'
        matches = re.findall(pattern, content)
        if not matches:
            return None
        return float(matches[0])
    
    @staticmethod
    def extract_total_power(content):
        """Extract total system power in watts"""
        pattern = r'i0\.defaultMemory\.channel\d+\.FRFCFS[^.]*?\.channel\d+\.rank\d+\.totalPower\s+([\d.e+-]+)W'
        matches = re.findall(pattern, content)
        if not matches:
            return None
        return sum(float(m) for m in matches)

def classify_technology(filename):
    """Classify technology based on filename pattern with precise matching"""
    filename_lower = filename.lower()
    
    # Try exact technology matches in priority order
    # Order matters: Check more specific patterns first
    for tech_name in ['1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC', 
                       'DDR5', '2D_DRAM', '3D_DRAM', 'PCM']:
        config = TECHNOLOGY_CONFIGS[tech_name]
        for pattern in config['patterns']:
            if re.search(pattern, filename_lower):
                return tech_name
    
    return None

def extract_architecture_scale(filename):
    """Extract architecture scale from filename"""
    filename_lower = filename.lower()
    if 'full_dimm' in filename_lower:
        return 'full_dimm'
    elif '16chip' in filename_lower:
        return '16chip'
    elif '8chip' in filename_lower:
        return '8chip'
    else:
        return 'single'

def extract_benchmark_name(filename):
    """Extract benchmark name from filename (stats_<tech>_<benchmark>.out)"""
    parts = filename.split('_')
    for i, part in enumerate(parts):
        part_clean = part.replace('.out', '')
        if part_clean in ['alexnet', 'gcc', 'gpt2', 'lbm', 'stream', 'hello', 'mcf']:
            benchmark_parts = parts[i:]
            benchmark = '_'.join(benchmark_parts).replace('.out', '')
            return benchmark
    return None

def parse_results_files():
    """Parse all stats_*.out files and extract data"""
    results_dir = Path('/home/yuvalk/MBMM/results/system')
    
    # Excluded benchmarks
    excluded_benchmarks = ['mlperf_inference', 'mlperf']
    
    # Data structure: benchmark_name -> list of data points
    data = defaultdict(list)
    
    stats_files = sorted(results_dir.glob('stats_*.out'))
    print(f"Processing {len(stats_files)} result files...\n")
    
    for file_path in stats_files:
        try:
            content = file_path.read_text()
            
            # Extract components
            benchmark = extract_benchmark_name(file_path.name)
            if not benchmark or any(excl in benchmark for excl in excluded_benchmarks):
                print(f"⊘ {file_path.name}: Excluded benchmark")
                continue
            
            latency = DataExtractor.extract_latency(content)
            power = DataExtractor.extract_total_power(content)
            
            if latency is None or power is None or latency == 0 or power == 0:
                print(f"⚠ {file_path.name}: Skipped (incomplete data)")
                continue
            
            tech = classify_technology(file_path.name)
            if not tech:
                print(f"⚠ {file_path.name}: Skipped (unknown technology)")
                continue
            
            arch = extract_architecture_scale(file_path.name)
            
            # Store data point
            data[benchmark].append({
                'technology': tech,
                'architecture': arch,
                'latency': latency,
                'power': power,
                'filename': file_path.name
            })
            
            print(f"✓ {file_path.name}: Tech={tech:12s} Arch={arch:10s} L={latency:8.1f}c P={power:.4f}W")
        
        except Exception as e:
            print(f"✗ {file_path.name}: Error - {str(e)}")
    
    return data

def create_gold_master_plot(benchmark, data_points):
    """Create Gold Master Pareto plot with:
    - Differentiated markers by technology and variant
    - Universal (X,Y) labeling on all points
    - Adaptive axes (log for gcc/mcf, linear for others)
    - Scaling indicators via marker size
    """
    fig, ax = plt.subplots(figsize=(16, 10), dpi=150)
    
    # Track all text labels for smart positioning
    all_texts = []
    
    # Plot all data points with technology-specific markers
    plotted_techs = set()
    
    for data_point in data_points:
        tech = data_point['technology']
        arch = data_point['architecture']
        latency = data_point['latency']
        power = data_point['power']
        
        tech_config = TECHNOLOGY_CONFIGS[tech]
        arch_config = ARCHITECTURE_SCALES[arch]
        
        # Use absolute marker size from architecture scale (not multiplier)
        marker_size = arch_config['size_base']
        
        # Determine edge color and width
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
        
        # Add text label with (Latency, Power) coordinates for EVERY point using annotate
        label_text = f"({latency:.0f}, {power:.3f})"
        
        # Intelligent offset to avoid marker overlap - increased offset for better clarity
        # Dynamic offset: larger offset for better label separation
        xytext_offset = (20, 20)  # Offset from marker to prevent collisions
        
        annotation = ax.annotate(
            label_text,
            xy=(latency, power),
            xytext=xytext_offset,
            textcoords='offset points',
            fontsize=9,
            fontweight='bold',
            ha='left',
            va='bottom',
            bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=2),
            zorder=5
        )
        all_texts.append(annotation)
    
    # Use adjust_text to prevent label overlaps if available
    if HAS_ADJUST_TEXT and all_texts:
        try:
            adjust_text(all_texts, ax=ax, 
                       arrowprops=dict(arrowstyle='-', lw=0.5, color='gray', alpha=0.5),
                       expand_points=(1.5, 1.5), expand_text=(1.2, 1.2),
                       force_points=(0.5, 0.5))
        except Exception as e:
            print(f"  Warning: adjust_text failed - {str(e)}. Using default positioning.")
    
    # Build custom legend with all plotted technologies
    legend_elements = []
    
    # Organize legend: Group by technology type
    tech_order = ['DDR5', '2D_DRAM', '3D_DRAM', 'PCM', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC']
    for tech_name in tech_order:
        if tech_name not in plotted_techs:
            continue
        
        config = TECHNOLOGY_CONFIGS[tech_name]
        legend_elements.append(
            Line2D([0], [0], marker=config['marker'], color='w', 
                   markerfacecolor=config['color'], markersize=8, 
                   label=config['label'], markeredgecolor='black', markeredgewidth=0.5)
        )
    
    # Add architecture scale legend
    legend_elements.append(Line2D([0], [0], color='none', label=''))  # Separator
    legend_elements.append(Line2D([0], [0], color='none', label='Architecture Scale:'))
    
    arch_indicators = [
        ('●', 'single', 'Single (smallest)'),
        ('●', '8chip', '8-Chip'),
        ('●', '16chip', '16-Chip'),
        ('●', 'full_dimm', 'Full DIMM (largest, outlined)')
    ]
    
    for symbol, arch_key, arch_label in arch_indicators:
        arch_config = ARCHITECTURE_SCALES[arch_key]
        # Convert absolute marker size to legend display size
        size = arch_config['size_base']
        legend_elements.append(
            Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                   markersize=np.sqrt(size/np.pi), label=arch_label,
                   alpha=arch_config['alpha'],
                   markeredgecolor='black' if arch_key == 'full_dimm' else 'none',
                   markeredgewidth=2.0 if arch_key == 'full_dimm' else 0)
        )
    
    # Create legend with dynamic placement
    ax.legend(handles=legend_elements, loc='best', fontsize=9, 
              title='Architecture & Capacity Scaling', framealpha=0.95, 
              edgecolor='black', title_fontsize=10)
    
    # Formatting
    ax.set_ylabel('Total System Power (W)', fontsize=12, fontweight='bold')
    ax.set_title(f'Gold Master Pareto Frontier: {benchmark}', fontsize=13, fontweight='bold')
    
    # Adaptive axes: Log for gcc_spec2017 and mcf_spec2017; Linear for others
    if 'gcc' in benchmark or 'mcf' in benchmark:
        ax.set_xscale('log')
        ax.set_xlim(50, 10000)
        ax.set_xlabel('Average Total Latency (Cycles) — Log Scale', fontsize=12, fontweight='bold')
    else:
        ax.set_xlim(left=50)
        ax.set_xlabel('Average Total Latency (Cycles)', fontsize=12, fontweight='bold')
    
    # Set fixed Y-axis range for consistent cross-comparison
    ax.set_ylim(0, 1.2)
    # Do NOT apply margins that would override the fixed y-axis range
    
    ax.grid(True, which='both', alpha=0.25, linestyle='-', linewidth=0.5)
    
    plt.tight_layout()
    return fig

def main():
    """Master Gold Master visualization pipeline"""
    print("=" * 100)
    print("GOLD MASTER - PARETO FRONTIER VISUALIZATION WITH MULTI-DIMENSIONAL LOGIC")
    print("=" * 100 + "\n")
    
    # Parse all stats_*.out files
    benchmark_data = parse_results_files()
    
    total_points = sum(len(points) for points in benchmark_data.values())
    print(f"\n{'=' * 100}")
    print(f"GOLD MASTER ANALYSIS SUMMARY (BATCH 2 FINALIZATION):")
    print(f"  Benchmarks identified: {len(benchmark_data)}")
    print(f"  Total data points: {total_points}")
    print(f"  Output directory: /home/yuvalk/MBMM/results/final_graphs/pareto/")
    print(f"  Output naming: Pareto_[Benchmark].png")
    print(f"  Axis strategy: LOG for gcc_spec2017, mcf_spec2017 | LINEAR [50, ∞) for others")
    print(f"  Y-Axis (Power): Fixed range [0, 1.2] for consistent cross-comparison")
    print(f"  Point labeling: UNIVERSAL - all points annotated with (X, Y) coordinates")
    print(f"  Label positioning: adjust_text with anti-collision algorithm")
    print(f"  Marker transparency: Full-DIMM (alpha=1.0) vs Non-DIMM (alpha=0.6) for visual hierarchy")
    print(f"  Baseline labeling: DDR5-4800 (Dual Channel) for clarity on comparison standard")
    print(f"  Legend title: 'Architecture & Capacity Scaling' for research emphasis")
    print(f"{'=' * 100}\n")
    
    # Generate plots
    output_dir = Path('/home/yuvalk/MBMM/results/final_graphs/pareto')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("Generating Gold Master Pareto plots...\n")
    
    for benchmark in sorted(benchmark_data.keys()):
        print(f"  Creating: Pareto_{benchmark}.png")
        fig = create_gold_master_plot(benchmark, benchmark_data[benchmark])
        output_file = output_dir / f'Pareto_{benchmark}.png'
        fig.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close(fig)
        print(f"    ✓ Saved: {output_file}")
    
    print(f"\n{'=' * 100}")
    print("✅ GOLD MASTER PARETO VISUALIZATIONS COMPLETE")
    print(f"{'=' * 100}\n")

if __name__ == '__main__':
    main()
