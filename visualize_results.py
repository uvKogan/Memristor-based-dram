import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import os
import re
import numpy as np
import shutil

# ============================================================================
# GOLD MASTER BAR CHART VISUALIZATION (Matching Pareto Frontier Aesthetics)
# ============================================================================

# Output configuration - organized into subdirectories
BASE_OUTPUT_DIR = "/home/yuvalk/MBMM/results/final_graphs"
LATENCY_DIR = os.path.join(BASE_OUTPUT_DIR, "latency")
POWER_DIR = os.path.join(BASE_OUTPUT_DIR, "power")
EDP_DIR = os.path.join(BASE_OUTPUT_DIR, "edp")
RESULTS_SYS_DIR = "/home/yuvalk/MBMM/results/system"

# Gold Master color palette (exact hex codes matching Pareto frontier)
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

def setup_output_directories():
    """Create organized subdirectories for latency, power, and EDP charts."""
    print("\n" + "="*80)
    print("SETUP PHASE: Creating output directories")
    print("="*80)
    
    os.makedirs(LATENCY_DIR, exist_ok=True)
    print(f"[OK] Latency output directory: {LATENCY_DIR}")
    
    os.makedirs(POWER_DIR, exist_ok=True)
    print(f"[OK] Power output directory: {POWER_DIR}")
    
    os.makedirs(EDP_DIR, exist_ok=True)
    print(f"[OK] EDP output directory: {EDP_DIR}\n")


def classify_technology(filename):
    """Classify technology from filename."""
    filename_lower = filename.lower()
    
    # Exact matches for specific models (order matters - check longer names first)
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
    """Extract benchmark name from filename by removing technology and architecture prefixes."""
    # Remove 'stats_' prefix and '.out' suffix
    name = filename.replace('stats_', '').replace('.out', '')
    
    # Handle DRAM models (DDR5_4800_DRAM, 2D_DRAM_example, 3D_DRAM_example)
    if 'DDR5_4800_DRAM' in name:
        return name.replace('DDR5_4800_DRAM_', '', 1)
    elif '2D_DRAM_example' in name:
        return name.replace('2D_DRAM_example_', '', 1)
    elif '3D_DRAM_example' in name:
        return name.replace('3D_DRAM_example_', '', 1)
    
    # Handle PCM
    elif 'pcm_microsoft_2009' in name:
        return name.replace('pcm_microsoft_2009_', '', 1)
    
    # Handle ReRAM models (reram_22nm_1t1r_slc_*, reram_22nm_1t1r_mlc_*, reram_22nm_selector_*)
    elif 'reram_22nm' in name:
        # Pattern: reram_22nm_[arch]_[mlc/slc]_[scale]_benchmark
        # Find where the benchmark starts (after full_dimm, 16chip, 8chip, or single)
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



def parse_nvmain_stats():
    """Parse all stats_*.out files and extract metrics."""
    data = []
    
    # Find all stat files in results/system/
    stat_files = glob.glob(os.path.join(RESULTS_SYS_DIR, "stats_*.out"))
    
    print("\n" + "="*80)
    print("PARSING STATS FILES: Gold Master Data Extraction")
    print("="*80)
    
    if not stat_files:
        print(f"[!] CRITICAL: No stats files found in {RESULTS_SYS_DIR}")
        return pd.DataFrame()
    
    print(f"[INFO] Found {len(stat_files)} stats files\n")
    
    for filepath in sorted(stat_files):
        filename = os.path.basename(filepath)
        
        # Classify technology
        tech = classify_technology(filename)
        if not tech:
            continue
        
        # Extract architecture
        arch = extract_architecture(filename)
        if not arch:
            continue
        
        # CRITICAL FILTER: Only include full_dimm ReRAM variants
        # (DDR5, DRAM variants, and PCM don't need filtering - they're always full_dimm)
        if tech not in ['DDR5_4800', '2D_DRAM_example', '3D_DRAM_example', 'pcm_microsoft_2009']:
            # This is ReRAM - only include full_dimm variants
            if arch != 'full_dimm':
                continue
        
        # Extract benchmark name
        bench_name = extract_benchmark(filename)
        
        # Skip excluded benchmarks
        if bench_name in ['mlperf_inference', 'mlperf']:
            continue
        
        # Parse latency and power from file
        latency = 0.0
        power = 0.0
        
        try:
            with open(filepath, 'r') as f:
                for line in f:
                    line_lower = line.lower()
                    
                    # Extract latency (average total latency)
                    if 'latency' in line_lower and 'average' in line_lower:
                        nums = re.findall(r'[\d\.\-eE]+', line)
                        if nums:
                            latency = float(nums[-1])
                    
                    # Extract power (total power)
                    if 'totalpower' in line_lower or 'total power' in line_lower.replace('_', ' '):
                        nums = re.findall(r'[\d\.\-eE]+', line)
                        if nums:
                            power = float(nums[-1])
        except Exception as e:
            print(f"[!] Error reading {filepath}: {e}")
            continue
        
        # Calculate EDP (Energy-Delay Product)
        edp = power * latency if power > 0 and latency > 0 else 0.0
        
        if latency > 0 and power > 0:
            print(f"[OK] {tech:20s} | {arch:10s} | {bench_name:25s} | Lat: {latency:10.2f} | Pow: {power:10.4f} | EDP: {edp:12.2f}")
            data.append({
                "Technology": tech,
                "Benchmark": bench_name,
                "Latency": latency,
                "Power": power,
                "EDP": edp
            })
    
    print()
    return pd.DataFrame(data)

def generate_bar_charts(df):
    """Generate 3 Gold Master bar charts per benchmark: Latency, Power, EDP."""
    
    if df.empty:
        print("[!] No data to visualize")
        return
    
    plt.rcdefaults()
    sns.set_theme(style="whitegrid")
    
    benchmarks = sorted(df['Benchmark'].unique())
    
    print("="*80)
    print("GENERATING BAR CHARTS: Gold Master Presentation Quality")
    print("="*80)
    
    for benchmark in benchmarks:
        bench_df = df[df['Benchmark'] == benchmark].copy()
        if bench_df.empty:
            continue
        
        # Sort by technology in consistent order
        tech_order = list(TECHNOLOGY_COLORS.keys())
        bench_df['Technology'] = pd.Categorical(bench_df['Technology'], categories=tech_order, ordered=True)
        bench_df = bench_df.sort_values('Technology')
        
        print(f"\n[PROCESSING] Benchmark: {benchmark}")
        print(f"  Data points: {len(bench_df)}")
        
        # Extract values and colors
        techs = bench_df['Technology'].astype(str).tolist()
        bars_x = range(len(bench_df))
        colors = [TECHNOLOGY_COLORS.get(t, '#808080') for t in techs]
        
        # ====================================================================
        # 1. LATENCY BAR CHART
        # ====================================================================
        fig, ax = plt.subplots(figsize=(12, 7))
        
        latency_vals = bench_df['Latency'].values
        bars = ax.bar(bars_x, latency_vals, color=colors, edgecolor='black', linewidth=1.5, alpha=0.85)
        
        # Add value labels on top of bars
        for i, (bar, val) in enumerate(zip(bars, latency_vals)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.2f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Determine if log scale is needed
        max_lat = latency_vals.max()
        min_lat = latency_vals.min()
        if max_lat > 0 and min_lat > 0 and max_lat / min_lat > 10:
            ax.set_yscale('log')
            ylabel = 'Average Latency (Cycles) — Log Scale'
        else:
            ylabel = 'Average Latency (Cycles)'
        
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_xlabel('Memory Technology', fontsize=12, fontweight='bold')
        ax.set_title(f'[{benchmark.upper()}] Latency Comparison', fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(bars_x)
        ax.set_xticklabels(techs, rotation=45, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        latency_file = os.path.join(LATENCY_DIR, f"Bar_Latency_{benchmark}.png")
        plt.savefig(latency_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {latency_file}")
        plt.close(fig)
        
        # ====================================================================
        # 2. POWER BAR CHART
        # ====================================================================
        fig, ax = plt.subplots(figsize=(12, 7))
        
        power_vals = bench_df['Power'].values
        bars = ax.bar(bars_x, power_vals, color=colors, edgecolor='black', linewidth=1.5, alpha=0.85)
        
        # Add value labels on top of bars
        for i, (bar, val) in enumerate(zip(bars, power_vals)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.2f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        ax.set_ylabel('System Power (Watts)', fontsize=12, fontweight='bold')
        ax.set_xlabel('Memory Technology', fontsize=12, fontweight='bold')
        ax.set_title(f'[{benchmark.upper()}] Power Consumption Comparison', fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(bars_x)
        ax.set_xticklabels(techs, rotation=45, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        power_file = os.path.join(POWER_DIR, f"Bar_Power_{benchmark}.png")
        plt.savefig(power_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {power_file}")
        plt.close(fig)
        
        # ====================================================================
        # 3. EDP BAR CHART
        # ====================================================================
        fig, ax = plt.subplots(figsize=(12, 7))
        
        edp_vals = bench_df['EDP'].values
        bars = ax.bar(bars_x, edp_vals, color=colors, edgecolor='black', linewidth=1.5, alpha=0.85)
        
        # Add value labels on top of bars
        for i, (bar, val) in enumerate(zip(bars, edp_vals)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{val:.2f}',
                   ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Determine if log scale is needed for EDP
        max_edp = edp_vals.max()
        min_edp = edp_vals.min()
        if max_edp > 0 and min_edp > 0 and max_edp / min_edp > 10:
            ax.set_yscale('log')
            ylabel = 'Energy-Delay Product (Power × Latency) — Log Scale'
        else:
            ylabel = 'Energy-Delay Product (Power × Latency)'
        
        ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
        ax.set_xlabel('Memory Technology', fontsize=12, fontweight='bold')
        ax.set_title(f'[{benchmark.upper()}] Energy-Delay Product (EDP) Comparison', fontsize=14, fontweight='bold', pad=15)
        ax.set_xticks(bars_x)
        ax.set_xticklabels(techs, rotation=45, ha='right', fontsize=10)
        ax.grid(axis='y', alpha=0.3)
        
        plt.tight_layout()
        edp_file = os.path.join(EDP_DIR, f"Bar_EDP_{benchmark}.png")
        plt.savefig(edp_file, dpi=300, bbox_inches='tight')
        print(f"  ✓ Saved: {edp_file}")
        plt.close(fig)
    
    print("\n" + "="*80)

if __name__ == "__main__":
    # Step 1: Setup output directories
    setup_output_directories()
    
    # Step 2: Parse data
    df = parse_nvmain_stats()
    
    # Step 3: Generate bar charts
    if not df.empty:
        print(f"\n[INFO] Total data points collected: {len(df)}")
        print(f"[INFO] Benchmarks: {sorted(df['Benchmark'].unique().tolist())}")
        print(f"[INFO] Technologies: {sorted(df['Technology'].unique().tolist())}")
        
        generate_bar_charts(df)
        
        print("✅ GOLD MASTER BAR CHART GENERATION COMPLETE")
        print("="*80)
        print(f"Output directories:")
        print(f"  Latency: {LATENCY_DIR}/")
        print(f"  Power: {POWER_DIR}/")
        print(f"  EDP: {EDP_DIR}/")
        print(f"Total plots generated: {len(df['Benchmark'].unique()) * 3}")
        print("="*80)
    else:
        print("[!] No data extracted. Check stats files and filters.")