import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import glob
import os
import re

def parse_nvmain_stats():
    data = []
    
    # Locate all stat files
    search_paths = ["stats_*.out", "results/stats_*.out", "results/system/stats_*.out"]
    stat_files = []
    for p in search_paths:
        stat_files.extend(glob.glob(p))
    stat_files = list(set(stat_files))
    
    target_order = [
        "reram_22nm_1t1r_slc", 
        "reram_22nm_1t1r_mlc", 
        "reram_22nm_selector_slc", 
        "reram_22nm_selector_mlc", 
        "2D_DRAM_example", 
        "3D_DRAM_example"
    ]

    print("\n" + "="*60)
    print("EXTRACTING METRICS: DIAGNOSTIC MODE")
    print("="*60)

    if not stat_files:
        print("[!] CRITICAL: Could not find any .out files in the directory!")
        return pd.DataFrame(), []

    for filepath in stat_files:
        filename = os.path.basename(filepath)
        
        base_model = None
        for target in target_order:
            if target in filename:
                base_model = target
                break
        if not base_model: continue

        if "DRAM" in base_model: arch = "full_dimm" 
        else:
            if "8chip" in filename: arch = "8chip"
            elif "16chip" in filename: arch = "16chip"
            elif "full_dimm" in filename: arch = "full_dimm"
            else: arch = "single"

        bench = "unknown"
        if "spec2017" in filename: bench = "spec2017"
        elif "stream" in filename: bench = "stream"
        elif "world" in filename: bench = "world"

        latency, power = 0.0, 0.0
        
        # Check if the file is physically empty (NVMain Crash)
        file_size = os.path.getsize(filepath)
        if file_size == 0:
            print(f"[EMPTY] {filename} is 0 bytes. (NVMain Simulation Aborted)")
            continue

        # FOOLPROOF LINE-BY-LINE PARSER
        with open(filepath, 'r') as f:
            for line in f:
                line_lower = line.lower()
                
                # Extract Latency
                if 'latency' in line_lower and 'average' in line_lower:
                    nums = re.findall(r'[\d\.\-eE]+', line)
                    if nums: latency = float(nums[-1]) # Grab the last number on the line
                
                # Extract Power
                if 'totalpower' in line_lower:
                    nums = re.findall(r'[\d\.\-eE]+', line)
                    if nums: power = float(nums[-1])

        # Verification
        if latency > 0 or power > 0:
            print(f"[OK] {filename} -> Latency: {latency} | Power: {power}")
            data.append({
                "Base_Model": base_model,
                "Architecture": arch,
                "Benchmark": bench,
                "Latency": latency,
                "Power": power
            })
        else:
            print(f"[FAILED] {filename} -> Has {file_size} bytes, but no Latency/Power numbers found.")
        
    return pd.DataFrame(data), target_order

def generate_charts(df, target_order):
    os.makedirs("results", exist_ok=True)
    sns.set_theme(style="whitegrid")
    
    df['Base_Model'] = pd.Categorical(df['Base_Model'], categories=target_order, ordered=True)
    df = df.dropna(subset=['Base_Model']).sort_values(['Base_Model', 'Architecture'])

    arch_order = ["single", "8chip", "16chip", "full_dimm"]
    benchmarks = df['Benchmark'].unique()

    for bench in benchmarks:
        bench_df = df[df['Benchmark'] == bench]
        if bench_df.empty: continue

        # ==========================================
        # 1. FULL ARCHITECTURE LATENCY
        # ==========================================
        max_lat = bench_df['Latency'].max()
        if pd.notna(max_lat) and max_lat > 350:
            fig, (ax_top, ax_bottom) = plt.subplots(2, 1, sharex=True, figsize=(14, 8), gridspec_kw={'height_ratios': [1, 3]})
            fig.subplots_adjust(hspace=0.05)

            sns.barplot(data=bench_df, x="Base_Model", y="Latency", hue="Architecture", hue_order=arch_order, palette="viridis", ax=ax_top)
            sns.barplot(data=bench_df, x="Base_Model", y="Latency", hue="Architecture", hue_order=arch_order, palette="viridis", ax=ax_bottom)

            ax_bottom.set_ylim(0, 350)
            ax_top.set_ylim(max_lat * 0.95, max_lat * 1.05)

            ax_top.spines['bottom'].set_visible(False)
            ax_bottom.spines['top'].set_visible(False)
            ax_top.xaxis.tick_top()
            ax_top.tick_params(labeltop=False)
            ax_bottom.xaxis.tick_bottom()

            for ax_target in [ax_top, ax_bottom]:
                for container in ax_target.containers:
                    labels = [f'{v.get_height():.0f}' if v.get_height() > 0 else '' for v in container]
                    if ax_target == ax_top:
                        labels = [l if (l and float(l) >= 350) else '' for l in labels]
                    else:
                        labels = [l if (l and float(l) < 350) else '' for l in labels]
                    ax_target.bar_label(container, labels=labels, padding=3, fontsize=9)

            d = .015
            kwargs = dict(transform=ax_top.transAxes, color='k', clip_on=False)
            ax_top.plot((-d, +d), (-d*3, +d*3), **kwargs)
            ax_top.plot((1 - d, 1 + d), (-d*3, +d*3), **kwargs)
            kwargs.update(transform=ax_bottom.transAxes)
            ax_bottom.plot((-d, +d), (1 - d, 1 + d), **kwargs)
            ax_bottom.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)

            ax_top.set_ylabel("")
            ax_bottom.set_ylabel("Average Latency (Cycles)", fontweight='bold')
            ax_bottom.set_xlabel("Memory Technology", fontweight='bold')
            ax_top.set_title(f"[{bench.upper()}] Memory Latency Comparison", pad=20, fontweight='bold', fontsize=14)
            ax_top.get_legend().remove()
            ax_bottom.legend(title="Architecture Scale", loc='upper left')
            for label in ax_bottom.get_xticklabels(): label.set_rotation(45); label.set_ha('right')

            plt.savefig(f"results/Latency_All_Architectures_{bench}.png", bbox_inches='tight', dpi=300)
            plt.close(fig)
            
        elif pd.notna(max_lat) and max_lat > 0:
            plt.figure(figsize=(14, 6))
            ax = sns.barplot(data=bench_df, x="Base_Model", y="Latency", hue="Architecture", hue_order=arch_order, palette="viridis")
            for container in ax.containers:
                ax.bar_label(container, labels=[f'{v.get_height():.0f}' if v.get_height() > 0 else '' for v in container], padding=3, fontsize=9)
            plt.title(f"[{bench.upper()}] Memory Latency Comparison", fontweight='bold', fontsize=14)
            plt.ylabel("Average Latency (Cycles)", fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            plt.legend(title="Architecture Scale", loc='upper left')
            plt.savefig(f"results/Latency_All_Architectures_{bench}.png", bbox_inches='tight', dpi=300)
            plt.close()

        # ==========================================
        # 2. FULL ARCHITECTURE POWER
        # ==========================================
        plt.figure(figsize=(14, 6))
        ax = sns.barplot(data=bench_df, x="Base_Model", y="Power", hue="Architecture", hue_order=arch_order, palette="magma")
        for container in ax.containers:
            ax.bar_label(container, labels=[f'{v.get_height():.4f}' if v.get_height() > 0 else '' for v in container], padding=3, fontsize=9)
        plt.title(f"[{bench.upper()}] System Power Comparison", fontweight='bold', fontsize=14)
        plt.ylabel("Power (Watts)", fontweight='bold')
        plt.xticks(rotation=45, ha='right')
        plt.legend(title="Architecture Scale", loc='upper left')
        plt.savefig(f"results/Power_All_Architectures_{bench}.png", bbox_inches='tight', dpi=300)
        plt.close()

        # ==========================================
        # 3. FULL DIMM COMPARISON 
        # ==========================================
        comp_df = bench_df[bench_df['Architecture'] == 'full_dimm']
        if not comp_df.empty:
            plt.figure(figsize=(10, 6))
            ax = sns.barplot(data=comp_df, x="Base_Model", y="Latency", hue="Base_Model", palette="mako", legend=False)
            plt.yscale("log") 
            for container in ax.containers:
                ax.bar_label(container, labels=[f'{v.get_height():.0f}' if v.get_height() > 0 else '' for v in container], padding=3, fontsize=10)
            plt.title(f"[{bench.upper()}] Baseline Latency (Full DIMM / Native DRAM)", fontweight='bold', fontsize=14)
            plt.ylabel("Latency (Cycles) [Log Scale]", fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            plt.savefig(f"results/Comparison_Full_DIMM_Latency_{bench}.png", bbox_inches='tight', dpi=300)
            plt.close()

            plt.figure(figsize=(10, 6))
            ax = sns.barplot(data=comp_df, x="Base_Model", y="Power", hue="Base_Model", palette="rocket", legend=False)
            for container in ax.containers:
                ax.bar_label(container, labels=[f'{v.get_height():.4f}' if v.get_height() > 0 else '' for v in container], padding=3, fontsize=10)
            plt.title(f"[{bench.upper()}] Baseline Power (Full DIMM / Native DRAM)", fontweight='bold', fontsize=14)
            plt.ylabel("Power (Watts)", fontweight='bold')
            plt.xticks(rotation=45, ha='right')
            plt.savefig(f"results/Comparison_Full_DIMM_Power_{bench}.png", bbox_inches='tight', dpi=300)
            plt.close()

if __name__ == "__main__":
    df, target_order = parse_nvmain_stats()
    if not df.empty:
        generate_charts(df, target_order)
        cwd = os.getcwd()
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE. CHARTS GENERATED:")
        print("="*60)
        for bench in sorted(df['Benchmark'].unique()):
            print(f"\n[{bench.upper()}]")
            for chart in sorted(glob.glob("results/*.png")):
                if bench in chart:
                    print(f"    {os.path.basename(chart).split('.')[0]}:  {cwd}/{chart}")
    else:
        print("\n[!] VISUALIZATION ABORTED. No data could be plotted.")