import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import glob
import os
import re
from scipy import stats

# ============================================================================
# HERO GRAPHS: Final Research Defense Visualizations
# ============================================================================

OUTPUT_DIR = "/home/yuvalk/MBMM/results/final_graphs/hero"
RESULTS_SYS_DIR = "/home/yuvalk/MBMM/results/system"

# Gold Master color palette (exact hex codes)
TECHNOLOGY_COLORS = {
    'DDR5_4800': '#0044FF',              # Vibrant Blue
    '2D_DRAM_example': '#00FFFF',        # Cyan
    '3D_DRAM_example': '#FF8800',        # Bright Orange
    'pcm_microsoft_2009': '#FF0000',     # Pure Red
    '1T1R_SLC': '#32CD32',               # Forest Green
    '1S1R_SLC': '#00FF00',               # Neon Green
    '1T1R_MLC': '#8A2BE2',               # Dark Violet
    '1S1R_MLC': '#FF00FF'                # Magenta
}

# Theoretical area density ratios (Lower is better)
AREA_DENSITY_DATA = {
    'DDR5_4800': 1.0,                    # Baseline (1T1C)
    'pcm_microsoft_2009': 0.8,           # PCM 2009
    '1T1R_SLC': 0.9,                     # Transistor limited
    '1S1R_SLC': 0.5,                     # True Crossbar 4F^2
    '1T1R_MLC': 0.45,                    # 2 bits/cell
    '1S1R_MLC': 0.25                     # Crossbar + 2 bits/cell
}

def create_output_directory():
    """Create output directory for final graphs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n[OK] Output directory ready: {OUTPUT_DIR}")

def generate_hero_area_density():
    """Generate Hero Graph 1: Normalized Area/Density (Theoretical)."""
    print("\n" + "="*80)
    print("HERO GRAPH 1: Normalized Area/Density (Theoretical)")
    print("="*80)
    
    # Prepare data
    technologies = list(AREA_DENSITY_DATA.keys())
    values = list(AREA_DENSITY_DATA.values())
    colors = [TECHNOLOGY_COLORS[tech] for tech in technologies]
    
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
    ax.set_ylabel('Normalized Area per GB (Lower is Better)', fontsize=13, fontweight='bold')
    ax.set_xlabel('Memory Technology', fontsize=13, fontweight='bold')
    ax.set_title('Physical Density Comparison: Normalized Area per GB', 
                fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(range(len(technologies)))
    ax.set_xticklabels(technologies, rotation=45, ha='right', fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    # Set y-axis to start at 0
    ax.set_ylim(0, max(values) * 1.15)
    
    plt.tight_layout()
    output_file = os.path.join(OUTPUT_DIR, "Hero_Normalized_Area.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close(fig)

def classify_technology(filename):
    """Classify technology from filename."""
    filename_lower = filename.lower()
    
    if 'ddr5_4800' in filename_lower:
        return 'DDR5_4800'
    elif '2d_dram_example' in filename_lower:
        return '2D_DRAM_example'
    elif '3d_dram_example' in filename_lower:
        return '3D_DRAM_example'
    elif 'pcm_microsoft_2009' in filename_lower:
        return 'pcm_microsoft_2009'
    elif 'reram_22nm' in filename_lower:
        if '1t1r_mlc' in filename_lower:
            return '1T1R_MLC'
        elif '1t1r_slc' in filename_lower:
            return '1T1R_SLC'
        elif 'selector_mlc' in filename_lower:
            return '1S1R_MLC'
        elif 'selector_slc' in filename_lower:
            return '1S1R_SLC'
    
    return None

def extract_architecture(filename):
    """Extract architecture scale from filename."""
    filename_lower = filename.lower()
    
    if 'full_dimm' in filename_lower:
        return 'full_dimm'
    elif '16chip' in filename_lower:
        return '16chip'
    elif '8chip' in filename_lower:
        return '8chip'
    elif 'single' in filename_lower:
        return 'single'
    
    # DRAM and PCM models don't have architecture suffix (implicit full_dimm)
    if 'ddr5' in filename_lower or '2d_dram' in filename_lower or '3d_dram' in filename_lower or 'pcm' in filename_lower:
        return 'full_dimm'
    
    return None

def extract_benchmark(filename):
    """Extract benchmark name from filename."""
    name = filename.replace('stats_', '').replace('.out', '')
    
    if 'DDR5_4800_DRAM' in name:
        return name.replace('DDR5_4800_DRAM_', '', 1)
    elif '2D_DRAM_example' in name:
        return name.replace('2D_DRAM_example_', '', 1)
    elif '3D_DRAM_example' in name:
        return name.replace('3D_DRAM_example_', '', 1)
    elif 'pcm_microsoft_2009' in name:
        return name.replace('pcm_microsoft_2009_', '', 1)
    elif 'reram_22nm' in name:
        if 'full_dimm' in name:
            idx = name.find('full_dimm_') + len('full_dimm_')
            return name[idx:]
        elif '16chip' in name:
            idx = name.find('16chip_') + len('16chip_')
            return name[idx:]
        elif '8chip' in name:
            idx = name.find('8chip_') + len('8chip_')
            return name[idx:]
        elif 'single' in name:
            idx = name.find('single_') + len('single_')
            return name[idx:]
    
    return name

def parse_all_stats_files():
    """Parse all stats files and calculate EDP for each data point."""
    print("\n" + "="*80)
    print("HERO GRAPH 2: Global Average EDP (Empirical) - Data Extraction")
    print("="*80)
    
    data = []
    stat_files = glob.glob(os.path.join(RESULTS_SYS_DIR, "stats_*.out"))
    
    if not stat_files:
        print(f"[!] No stats files found in {RESULTS_SYS_DIR}")
        return pd.DataFrame()
    
    print(f"[INFO] Processing {len(stat_files)} stats files\n")
    
    for filepath in sorted(stat_files):
        filename = os.path.basename(filepath)
        
        # Classify and extract
        tech = classify_technology(filename)
        if not tech:
            continue
        
        arch = extract_architecture(filename)
        if not arch:
            continue
        
        # Only include full_dimm for ReRAM
        if tech not in ['DDR5_4800', 'pcm_microsoft_2009']:
            if arch != 'full_dimm':
                continue
        
        bench_name = extract_benchmark(filename)
        if bench_name in ['mlperf_inference', 'mlperf']:
            continue
        
        # Parse metrics
        latency = 0.0
        power = 0.0
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line_lower = line.lower()
                    
                    if 'latency' in line_lower and 'average' in line_lower:
                        nums = re.findall(r'[\d\.\-eE]+', line)
                        if nums:
                            latency = float(nums[-1])
                    
                    if 'totalpower' in line_lower or 'total power' in line_lower.replace('_', ' '):
                        nums = re.findall(r'[\d\.\-eE]+', line)
                        if nums:
                            power = float(nums[-1])
        except Exception as e:
            continue
        
        # Calculate EDP
        edp = power * latency if power > 0 and latency > 0 else 0.0
        
        if latency > 0 and power > 0:
            print(f"[OK] {tech:20s} | {bench_name:25s} | Lat: {latency:10.2f} | Pow: {power:10.4f} | EDP: {edp:12.2f}")
            data.append({
                "Technology": tech,
                "Benchmark": bench_name,
                "Latency": latency,
                "Power": power,
                "EDP": edp
            })
    
    print()
    return pd.DataFrame(data)

def calculate_geometric_mean_edp(df):
    """Calculate geometric mean EDP for each technology across all benchmarks."""
    print("="*80)
    print("CALCULATING GEOMETRIC MEAN EDP PER TECHNOLOGY")
    print("="*80)
    
    geometric_means = {}
    
    for tech in df['Technology'].unique():
        tech_df = df[df['Technology'] == tech]
        edp_values = tech_df['EDP'].values
        
        if len(edp_values) > 0:
            # Geometric mean = exp(mean(log(values)))
            geom_mean = np.exp(np.mean(np.log(edp_values)))
            geometric_means[tech] = geom_mean
            
            print(f"[OK] {tech:20s} | Data points: {len(edp_values):2d} | Geom Mean EDP: {geom_mean:12.2f}")
    
    print()
    return geometric_means

def generate_hero_average_edp(geometric_means):
    """Generate Hero Graph 2: Global Average EDP (Empirical)."""
    print("="*80)
    print("HERO GRAPH 2: Overall System Efficiency (Geometric Mean EDP)")
    print("="*80)
    
    # Sort technologies by EDP
    sorted_techs = sorted(geometric_means.items(), key=lambda x: x[1])
    technologies = [tech for tech, _ in sorted_techs]
    values = [edp for _, edp in sorted_techs]
    
    # Get colors
    colors = [TECHNOLOGY_COLORS.get(tech, '#808080') for tech in technologies]
    
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
        ylabel = 'Geometric Mean EDP (Lower is Better) — Log Scale'
    else:
        ylabel = 'Geometric Mean EDP (Lower is Better)'
    
    # Formatting
    ax.set_ylabel(ylabel, fontsize=13, fontweight='bold')
    ax.set_xlabel('Memory Technology', fontsize=13, fontweight='bold')
    ax.set_title('Overall System Efficiency (Geometric Mean EDP)', 
                fontsize=15, fontweight='bold', pad=20)
    ax.set_xticks(range(len(technologies)))
    ax.set_xticklabels(technologies, rotation=45, ha='right', fontsize=11)
    ax.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_file = os.path.join(OUTPUT_DIR, "Hero_Average_EDP.png")
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_file}")
    plt.close(fig)

if __name__ == "__main__":
    print("\n" + "="*80)
    print("HERO GRAPHS GENERATION: Research Defense Final Visualizations")
    print("="*80)
    
    # Create output directory
    create_output_directory()
    
    # Generate Hero Graph 1: Theoretical Area Density
    generate_hero_area_density()
    
    # Generate Hero Graph 2: Empirical Global Average EDP
    df_all = parse_all_stats_files()
    
    if not df_all.empty:
        geometric_means = calculate_geometric_mean_edp(df_all)
        generate_hero_average_edp(geometric_means)
        
        print("="*80)
        print("✅ HERO GRAPHS GENERATION COMPLETE")
        print("="*80)
        print(f"\nOutput directory: {OUTPUT_DIR}/")
        print(f"Generated files:")
        print(f"  1. Hero_Normalized_Area.png (Theoretical)")
        print(f"  2. Hero_Average_EDP.png (Empirical)")
        print("="*80)
    else:
        print("[!] No data extracted for EDP analysis")
