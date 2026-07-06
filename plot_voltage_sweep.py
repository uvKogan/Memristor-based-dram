#!/usr/bin/env python3
"""
ReadVoltage Sensitivity Figure
Reads results/sweep_voltage_results.json → results/final_graphs/sensitivity/Sensitivity_ReadVoltage.png

Run run_voltage_sweep.py first to generate the input JSON.
"""

import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from pathlib import Path

ROOT        = Path(__file__).parent.absolute()
RESULTS_JSON = ROOT / "results" / "sweep_voltage_results.json"
OUTPUT_DIR  = ROOT / "results" / "final_graphs" / "sensitivity"
OUTPUT_FILE = OUTPUT_DIR / "Sensitivity_ReadVoltage.png"

BENCHMARKS = ["lbm_spec2017", "gcc_spec2017"]
BENCH_LABELS = {
    "lbm_spec2017": "LBM (Memory-Bound)",
    "gcc_spec2017":  "GCC (Compute-Bound)"
}
BENCH_COLORS = {
    "lbm_spec2017": "#0044FF",
    "gcc_spec2017":  "#FF6600"
}


def load():
    if not RESULTS_JSON.exists():
        raise FileNotFoundError(
            f"Missing: {RESULTS_JSON}\nRun python3 run_voltage_sweep.py first.")
    with open(RESULTS_JSON) as f:
        raw = json.load(f)
    return {float(k): v for k, v in raw.items()}


def get_hw(results, voltages, key):
    return [results[v]['hw'].get(key) or 0.0 for v in voltages]


def get_sys(results, voltages, bench, key):
    return [results[v]['system'].get(bench, {}).get(key) or 0.0 for v in voltages]


def bar_group(ax, x, data_by_bench, width=0.35):
    n = len(data_by_bench)
    offsets = np.linspace(-(n - 1) / 2, (n - 1) / 2, n) * width
    for bench, offset in zip(BENCHMARKS, offsets):
        vals = data_by_bench[bench]
        bars = ax.bar(x + offset, vals, width=width,
                      color=BENCH_COLORS[bench], edgecolor='black',
                      linewidth=1.0, alpha=0.85, label=BENCH_LABELS[bench])
        for bar, val in zip(bars, vals):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                        f'{val:.1f}', ha='center', va='bottom', fontsize=8, fontweight='bold')


def main():
    print(f"Loading {RESULTS_JSON}")
    results = load()
    voltages = sorted(results.keys())
    x = np.arange(len(voltages))
    xlabels = [f'{v:.2f}V' for v in voltages]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    fig = plt.figure(figsize=(16, 10))
    fig.suptitle('ReadVoltage Sensitivity — 1T1R SLC Full DIMM\n'
                 'NVSim @ 22nm LOP | NVMain 2.0 @ 50M cycles | Benchmarks: LBM + GCC — All metrics: lower is better',
                 fontsize=14, fontweight='bold', y=0.98)
    gs = gridspec.GridSpec(2, 2, hspace=0.50, wspace=0.35)

    # --- Subplot 1: NVSim Read Latency (single bar, no per-bench breakdown) ---
    ax1 = fig.add_subplot(gs[0, 0])
    hw_lat = get_hw(results, voltages, 'read_latency_ns')
    hw_bars = ax1.bar(x, hw_lat, color='#555555', edgecolor='black', linewidth=1.2, alpha=0.85)
    for bar, val in zip(hw_bars, hw_lat):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                 f'{val:.2f}ns', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax1.set_title('Circuit Read Latency (NVSim)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Read Latency (ns)', fontsize=11)
    ax1.set_xlabel('NVSim ReadVoltage (V)', fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(xlabels)
    ax1.set_ylim(0, max(hw_lat) * 1.25 if hw_lat else 1)
    ax1.grid(axis='y', alpha=0.3)


    # --- Subplot 2: System Avg Total Latency ---
    ax2 = fig.add_subplot(gs[0, 1])
    sys_lat = {b: get_sys(results, voltages, b, 'avg_total_latency_cycles') for b in BENCHMARKS}
    bar_group(ax2, x, sys_lat)
    ax2.set_title('System Avg Total Latency (NVMain)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Avg Total Latency (cycles)', fontsize=11)
    ax2.set_xlabel('NVSim ReadVoltage (V)', fontsize=11)
    ax2.set_xticks(x)
    ax2.set_xticklabels(xlabels)
    ax2.grid(axis='y', alpha=0.3)

    # --- Subplot 3: System Power ---
    ax3 = fig.add_subplot(gs[1, 0])
    sys_pwr = {b: get_sys(results, voltages, b, 'power_w') for b in BENCHMARKS}
    bar_group(ax3, x, sys_pwr)
    ax3.set_title('System Power (NVMain)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Total System Power (W)', fontsize=11)
    ax3.set_xlabel('NVSim ReadVoltage (V)', fontsize=11)
    ax3.set_xticks(x)
    ax3.set_xticklabels(xlabels)
    ax3.grid(axis='y', alpha=0.3)

    # --- Subplot 4: PDP ---
    ax4 = fig.add_subplot(gs[1, 1])
    sys_pdp = {b: get_sys(results, voltages, b, 'pdp') for b in BENCHMARKS}
    bar_group(ax4, x, sys_pdp)
    ax4.set_title('PDP (cycles × W)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('PDP (cycles × W)', fontsize=11)
    ax4.set_xlabel('NVSim ReadVoltage (V)', fontsize=11)
    ax4.set_xticks(x)
    ax4.set_xticklabels(xlabels)
    ax4.grid(axis='y', alpha=0.3)

    # Single shared legend centred between the two rows
    handles, labels = ax2.get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 0.04),
               ncol=2, fontsize=10, framealpha=0.9)

    fig.text(0.5, -0.01,
             'ReadVoltage swept ±20% (1.12V, 1.40V, 1.68V) around the 1.40V design point. '
             'tCAS/ReadEnergy/StandbyPower updated per voltage via NVSim. '
             'Full DIMM = 64 chips × 128MB = 8 GB. System sim at 50M cycles.',
             ha='center', fontsize=9, style='italic')

    plt.savefig(OUTPUT_FILE, dpi=300, bbox_inches='tight')
    print(f"Saved: {OUTPUT_FILE}")
    plt.close(fig)


if __name__ == "__main__":
    main()
