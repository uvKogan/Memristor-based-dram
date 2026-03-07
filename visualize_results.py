import matplotlib.pyplot as plt
import re
import os
from pathlib import Path
from collections import defaultdict

def parse_stats(file_path):
    """Parses NVMain output for key metrics using project-standard regex[cite: 1350, 1537]."""
    metrics = {"power": 0, "latency": 0}
    with open(file_path, "r") as f:
        content = f.read()
        # totalPower (Watts) extraction 
        p = re.search(r"totalPower\s+([\d.]+)W", content)
        # averageTotalLatency (System Cycles) extraction 
        l = re.search(r"averageTotalLatency\s+([\d.]+)", content)
        
        if p: metrics["power"] = float(p.group(1))
        if l: metrics["latency"] = float(l.group(1))
    return metrics

def build_dynamic_comparison():
    root_dir = Path(__file__).parent
    sys_results_dir = root_dir / "results" / "system"
    
    # 1. Auto-identify benchmarks and models by scanning files
    # Pattern: stats_{model}_{benchmark}.out
    bench_data = defaultdict(list)
    
    for file_path in sys_results_dir.glob("stats_*.out"):
        parts = file_path.stem.split('_')
        if len(parts) >= 3:
            benchmark = parts[-1]  # The tagged trace name
            model = "_".join(parts[1:-1]) # Everything between 'stats' and the benchmark
            
            metrics = parse_stats(file_path)
            metrics['model_name'] = model
            bench_data[benchmark].append(metrics)

    # 2. Generate a chart for EACH benchmark found
    for benchmark, results in bench_data.items():
        # Sort results by model name for consistency
        results.sort(key=lambda x: x['model_name'])
        
        names = [r['model_name'] for r in results]
        powers = [r['power'] for r in results]
        latencies = [r['latency'] for r in results]

        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax2 = ax1.twinx()

        x = range(len(names))
        width = 0.35

        ax1.bar([i - width/2 for i in x], powers, width, label='Avg Power (W)', color='teal')
        ax2.bar([i + width/2 for i in x], latencies, width, label='Avg Latency (Cycles)', color='indianred')

        ax1.set_ylabel('Power (Watts)', color='teal')
        ax2.set_ylabel('Latency (Cycles)', color='indianred')
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, rotation=15, ha='right')
        
        # Dynamic Headline
        plt.title(f'MBMM Performance Analysis: Benchmark [{benchmark.upper()}]')
        
        # Legend management
        lines, labels = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax2.legend(lines + lines2, labels + labels2, loc='upper left')

        output_path = root_dir / "results" / f"Comparison_{benchmark}.png"
        plt.tight_layout()
        plt.savefig(output_path)
        print(f">>> Dynamic Chart generated for {benchmark}: {output_path}")

if __name__ == "__main__":
    build_dynamic_comparison()