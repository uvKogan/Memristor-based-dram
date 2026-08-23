#!/usr/bin/env python3
"""
MBMM Visualization - Presentation Slide Charts

Restyled, trimmed-technology-set charts built from the SAME processed data
as the report figures (visualize_results.py / visualize_pareto.py /
visualize_hero_graphs.py), for a live 60-min talk rather than a written
report: fewer technologies per chart (only the ones the slide's story is
about), larger fonts, no dense report footnotes.

Two chart groups here have no equivalent report script because the report
never plots them as figures (they're prose/table-only in the book):
  - Endurance (Table 5): lifetime = per-cell endurance rating x cell count
    / measured write rate. Write rates are taken from
    results/cycle8_matched_host_report.md's endurance-counters table
    (module-summed, 83.33 ms window) - the same inputs the book's Table 5
    used - not re-simulated here.
  - Density projection (Table 7): projected = measured 22nm
    Area_Density_Ratio (processed_hero_metrics.csv) x (22/F)^2, with the
    2x/4x deck-stacking multipliers applied only to the selector (1S1R)
    rows, exactly as derived in Project_Book.typ Section 3.3.

This script only reads existing processed outputs (or applies the book's
own documented closed-form projection to them) — it does not run NVSim/
NVMain and is not gated by mbmm_master.py.

Output: /home/yuvalk/MBMM/results/slide_graphs/ (never touches
results/final_graphs*, which the book's embedded figures depend on).
"""

import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from logging_config import setup_logging

logger = setup_logging("visualize_slides")

# ============================================================================
# CONFIGURATION
# ============================================================================

DATA_DIR = "/home/yuvalk/MBMM/results/system_v6"
HARDWARE_METRICS_FILE = "/home/yuvalk/MBMM/results/hardware_metrics.json"
OUTPUT_DIR = "/home/yuvalk/MBMM/results/slide_graphs"

TECH_COLORS = {
    'DDR5_4800': '#0044FF',
    'pcm_microsoft_2009': '#FF0000',
    '1T1R_SLC': '#32CD32',
    '1S1R_SLC': '#00FF00',
    '1T1R_MLC': '#8A2BE2',
    '1S1R_MLC': '#FF00FF',
}
TECH_LABELS = {
    'DDR5_4800': 'DDR5-4800',
    'pcm_microsoft_2009': 'PCM',
    '1T1R_SLC': '1T1R SLC',
    '1T1R_MLC': '1T1R MLC',
    '1S1R_SLC': '1S1R SLC',
    '1S1R_MLC': '1S1R MLC',
}

# Slide-scale typography (report scripts use 9-15pt; slides need to read from
# the back of a room).
plt.rcParams.update({
    'font.size': 15,
    'axes.titlesize': 20,
    'axes.labelsize': 17,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
    'legend.fontsize': 13,
})


def _labels(techs):
    return [TECH_LABELS.get(t, t) for t in techs]


def _colors(techs):
    return [TECH_COLORS.get(t, '#808080') for t in techs]


def _bar_with_labels(ax, xs, vals, colors, fmt='{:.1f}'):
    bars = ax.bar(xs, vals, color=colors, edgecolor='black', linewidth=2.0, alpha=0.9)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                fmt.format(val), ha='center', va='bottom', fontweight='bold')
    return bars


def _save(fig, name, footnote=None):
    if footnote:
        fig.text(0.5, 0.01, footnote, ha='center', va='bottom',
                  fontsize=11, style='italic', color='dimgray')
        fig.tight_layout(rect=[0, 0.06, 1, 1])
    else:
        fig.tight_layout()
    out = os.path.join(OUTPUT_DIR, name)
    fig.savefig(out, dpi=200, bbox_inches='tight')
    logger.info(f"  ✓ Saved: {out}")
    plt.close(fig)


# ============================================================================
# DATA LOADING
# ============================================================================

def load_bar_chart_metrics():
    return pd.read_csv(os.path.join(DATA_DIR, "processed_bar_chart_metrics.csv"))


def load_hero_metrics():
    return pd.read_csv(os.path.join(DATA_DIR, "processed_hero_metrics.csv"))


def load_geometric_means():
    df = pd.read_csv(os.path.join(DATA_DIR, "processed_geometric_means.csv"))
    return dict(zip(df['Technology'], df['Geometric_Mean_PDP']))


def load_hardware_metrics():
    import json
    with open(HARDWARE_METRICS_FILE) as f:
        return json.load(f)


def bench_row(df, benchmark, tech, arch='full_dimm'):
    row = df[(df['Benchmark'] == benchmark) & (df['Technology'] == tech)
             & (df['Architecture'] == arch)]
    return row.iloc[0] if not row.empty else None


# ============================================================================
# 1. LATENCY — GCC (compute-bound, closest gap)  [Slide 15]
# ============================================================================

def slide_latency_gcc(df):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC']
    vals = [bench_row(df, 'gcc_spec2017', t)['Latency_ns'] for t in techs]

    fig, ax = plt.subplots(figsize=(9, 6.5))
    _bar_with_labels(ax, range(len(techs)), vals, _colors(techs), fmt='{:.0f} ns')
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels(_labels(techs))
    ax.set_ylabel('Average Latency (ns)')
    ax.set_title('Compute-Bound (GCC): the closest gap')
    ax.set_ylim(0, max(vals) * 1.2)
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "15_latency_gcc.png")


# ============================================================================
# 2. STREAMING — honest view: latency + completion %  [Slide 16]
# ============================================================================

def slide_streaming_honest(df):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC', 'pcm_microsoft_2009']

    # Left panel: STREAM latency (~100% completion for every tech, clean comparison)
    stream_techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC']
    stream_vals = [bench_row(df, 'stream', t)['Latency_ns'] for t in stream_techs]

    # Right panel: LBM completion % out of the identical 16,447,102-request
    # admission (results/cycle8_matched_host_report.md, admission/completion
    # table) — the same matched-host correction Project_Book.typ Section
    # 3.1.6 item 11 documents. Hardcoded here because it is a raw
    # admission/completion count, not a column in any processed_*.csv.
    completion_pct = {
        'DDR5_4800': 100.00,
        '1T1R_SLC': 39.97,
        '1S1R_SLC': 27.99,
        '1T1R_MLC': 16.27,
        '1S1R_MLC': 9.35,
        'pcm_microsoft_2009': 3.90,
    }
    comp_vals = [completion_pct[t] for t in techs]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(16, 6.5))

    _bar_with_labels(axL, range(len(stream_techs)), stream_vals, _colors(stream_techs), fmt='{:.0f} ns')
    axL.set_xticks(range(len(stream_techs)))
    axL.set_xticklabels(_labels(stream_techs))
    axL.set_ylabel('Average Latency (ns)')
    axL.set_title('STREAM: latency (fully comparable)')
    axL.set_ylim(0, max(stream_vals) * 1.2)
    axL.grid(axis='y', alpha=0.3)

    _bar_with_labels(axR, range(len(techs)), comp_vals, _colors(techs), fmt='{:.0f}%')
    axR.set_xticks(range(len(techs)))
    axR.set_xticklabels(_labels(techs), rotation=20, ha='right')
    axR.set_ylabel('% of identical admitted requests completed')
    axR.set_title('LBM: completion rate, same window')
    axR.set_ylim(0, 115)
    axR.grid(axis='y', alpha=0.3)

    fig.suptitle('Streaming: the reported latency ratio understates the real gap', fontsize=18, fontweight='bold')
    _save(fig, "16_streaming_honest.png",
          footnote="LBM latency averages are computed over each config's completed prefix, not the full admitted population.")


# ============================================================================
# 3. AI INFERENCE — GPT-2  [Slide 17]
# ============================================================================

def slide_latency_gpt2(df):
    techs = ['DDR5_4800', '1T1R_SLC']
    vals = [bench_row(df, 'gpt2_ifmap', t)['Latency_ns'] for t in techs]

    fig, ax = plt.subplots(figsize=(7.5, 6.5))
    _bar_with_labels(ax, range(len(techs)), vals, _colors(techs), fmt='{:.0f} ns')
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels(_labels(techs))
    ax.set_ylabel('Average Latency (ns)')
    ratio = vals[1] / vals[0]
    ax.set_title(f'AI Inference (GPT-2): DDR5 wins, {ratio:.1f}x')
    ax.set_ylim(0, max(vals) * 1.2)
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "17_latency_gpt2.png",
          footnote="GPT-2 trace provenance unverified — treated as a representative parallel-read stress pattern.")


# ============================================================================
# 4. MLC WRITE PENALTY — AlexNet IFMAP vs OFMAP  [Slide 18]
# ============================================================================

def slide_mlc_write_penalty(df):
    techs = ['1S1R_SLC', '1S1R_MLC']
    ifmap = [bench_row(df, 'alexnet_layer1_ifmap', t)['Latency_ns'] for t in techs]
    ofmap = [bench_row(df, 'alexnet_layer1_ofmap', t)['Latency_ns'] for t in techs]

    x = np.arange(len(techs))
    width = 0.35
    fig, ax = plt.subplots(figsize=(9, 6.5))
    b1 = ax.bar(x - width / 2, ifmap, width, label='IFMAP (read)', color='#00CED1', edgecolor='black', linewidth=1.5)
    b2 = ax.bar(x + width / 2, ofmap, width, label='OFMAP (write)', color='#FF6347', edgecolor='black', linewidth=1.5)
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(), f'{bar.get_height():.0f}',
                    ha='center', va='bottom', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(_labels(techs))
    ax.set_ylabel('Average Latency (ns)')
    ax.set_title('MLC write penalty: OFMAP vs IFMAP')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "18_mlc_write_penalty.png")


# ============================================================================
# 5. THE 47x FACT — device-level leakage  [Slide 19]
# ============================================================================

def slide_device_leakage(hw):
    pairs = [('reram_22nm_1t1r_slc', '1T1R'), ('reram_22nm_selector_slc', '1S1R')]
    vals = [hw[k]['leakage_mw'] for k, _ in pairs]
    labels = [lbl for _, lbl in pairs]
    colors = [TECH_COLORS['1T1R_SLC'], TECH_COLORS['1S1R_SLC']]

    fig, ax = plt.subplots(figsize=(8, 6.5))
    _bar_with_labels(ax, range(len(labels)), vals, colors, fmt='{:.0f} mW/chip')
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels)
    ax.set_ylabel('Leakage (mW/chip)')
    ratio = vals[0] / vals[1]
    ax.set_title(f'Device-level leakage: {ratio:.0f}x apart')
    ax.set_ylim(0, max(vals) * 1.2)
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "19_device_leakage.png",
          footnote="NVSim device characterization, per 1 Gb chip, 22nm FinFET LOP.")


# ============================================================================
# 6. FULL-MODULE POWER  [Slide 20]
# ============================================================================

def slide_module_power(df, benchmark='gcc_spec2017'):
    techs = ['DDR5_4800', 'pcm_microsoft_2009', '1T1R_SLC', '1S1R_SLC']
    vals = [bench_row(df, benchmark, t)['Power'] for t in techs]

    fig, ax = plt.subplots(figsize=(9, 6.5))
    bars = ax.bar(range(len(techs)), vals, color=_colors(techs), edgecolor='black', linewidth=2.0, alpha=0.9)
    for bar, val in zip(bars, vals):
        label = f'{val:.3f} W' if val < 1 else f'{val:.1f} W'
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(), label,
                ha='center', va='bottom', fontweight='bold')
    ax.set_yscale('log')
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels(_labels(techs), rotation=15, ha='right')
    ax.set_ylabel('Total Module Power (W), log scale')
    ax.set_title('Full-module power (ungated)')
    ax.grid(axis='y', which='both', alpha=0.3)
    _save(fig, "20_module_power.png",
          footnote="ReRAM figures are worst-case ungated (idle-power gating not yet simulated).")


# ============================================================================
# 7. PDP GEOMETRIC MEAN  [Slide 21]
# ============================================================================

def slide_pdp_geomean(geomeans):
    techs = ['DDR5_4800', 'pcm_microsoft_2009', '1T1R_SLC', '1S1R_SLC']
    vals = [geomeans[t] for t in techs]

    fig, ax = plt.subplots(figsize=(9, 6.5))
    _bar_with_labels(ax, range(len(techs)), vals, _colors(techs), fmt='{:.0f}')
    ax.set_yscale('log')
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels(_labels(techs), rotation=15, ha='right')
    ax.set_ylabel('Geometric-mean PDP (W·ns), log scale — lower is better')
    ax.set_title('Overall efficiency: 1S1R closes most of the ReRAM gap')
    ax.grid(axis='y', which='both', alpha=0.3)
    _save(fig, "21_pdp_geomean.png",
          footnote="ReRAM worst-case ungated; DDR5/PCM standard idle behavior.")


# ============================================================================
# 8/9. PARETO — GCC (flatline) and GPT-2 (breaking it)  [Slides 22-23]
# ============================================================================

def _pareto_slide(pareto_df, benchmark, title, filename):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC']
    markers = {'DDR5_4800': '*', '1T1R_SLC': 'o', '1S1R_SLC': 'o'}
    sizes = {'single': 220, '16chip': 500, 'full_dimm': 850}
    arch_order = ['single', '16chip', 'full_dimm']

    fig, ax = plt.subplots(figsize=(10, 7.5))
    bdf = pareto_df[pareto_df['Benchmark'] == benchmark]

    for tech in techs:
        tdf = bdf[bdf['Technology'] == tech]
        pts = []
        for arch in arch_order:
            r = tdf[tdf['Architecture'] == arch]
            if not r.empty:
                pts.append((r.iloc[0]['Latency_ns'], r.iloc[0]['Power']))
                ax.scatter(r.iloc[0]['Latency_ns'], r.iloc[0]['Power'],
                           marker=markers[tech], s=sizes[arch],
                           color=TECH_COLORS[tech], edgecolor='black', linewidth=1.5,
                           alpha=0.85, zorder=3)
        if len(pts) >= 2:
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=TECH_COLORS[tech], linestyle='--', linewidth=2, alpha=0.6, zorder=2)

    all_p = bdf[bdf['Technology'].isin(techs)]['Power']
    if all_p.max() / max(all_p.min(), 1e-9) > 10:
        ax.set_yscale('log')
    ax.set_xlabel('Latency (ns)')
    ax.set_ylabel('Total System Power (W)')
    ax.set_title(title)
    ax.grid(True, alpha=0.3, linestyle='--')

    legend_elements = [Line2D([0], [0], marker=markers[t], color='w', markerfacecolor=TECH_COLORS[t],
                               markersize=12, label=TECH_LABELS[t], markeredgecolor='black') for t in techs]
    legend_elements += [Line2D([0], [0], color='none', label=''),
                         Line2D([0], [0], marker='o', color='w', markerfacecolor='gray', markersize=8,
                                label='1-chip → 16-chip → Full DIMM (small → large)')]
    ax.legend(handles=legend_elements, loc='best', framealpha=0.95)
    _save(fig, filename)


def slide_pareto_gcc(pareto_df):
    _pareto_slide(pareto_df, 'gcc_spec2017', 'The Flatline Paradox: no MLP, no benefit from scaling', "22_pareto_gcc.png")


def slide_pareto_gpt2(pareto_df):
    _pareto_slide(pareto_df, 'gpt2_ifmap', 'Breaking the flatline: high-MLP workloads reward scaling', "23_pareto_gpt2.png")


# ============================================================================
# 10. DENSITY  [Slide 24]
# ============================================================================

def slide_density(hero_df):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC', '1S1R_MLC']
    vals = [hero_df[hero_df['Technology'] == t]['Area_Density_Ratio'].mean() for t in techs]

    fig, ax = plt.subplots(figsize=(9, 6.5))
    _bar_with_labels(ax, range(len(techs)), vals, _colors(techs), fmt='{:.2f}x')
    ax.axhline(1.0, color='gray', linestyle=':', linewidth=1.5)
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels(_labels(techs))
    ax.set_ylabel('Die-Level Density (× DDR5) — higher is better')
    ax.set_title('Density: architecture, not node, decides this')
    ax.set_ylim(0, max(vals) * 1.2)
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "24_density.png",
          footnote="20F² 1T1R cell is architecture-dependent, not a ceiling — a 6F² recessed-channel demo exists (real device-physics work needed to apply it here).")


# ============================================================================
# 11. DENSITY PROJECTION (Table 7) — NEW, clearly labeled a projection [Slide 25]
# ============================================================================

def slide_density_projection(hero_df):
    """Reproduces Project_Book.typ Table 7: measured 22nm Area_Density_Ratio
    x (22/F)^2, deck-stack multipliers (x2, x4) applied only to 1S1R."""
    techs = ['1S1R_SLC', '1S1R_MLC', '1T1R_SLC', '1T1R_MLC']
    measured = {t: hero_df[hero_df['Technology'] == t]['Area_Density_Ratio'].mean() for t in techs}

    nodes = [22, 16, 12]
    projected = {t: [measured[t] * (22 / f) ** 2 for f in nodes] for t in techs}
    # 1S1R deck-stacking rows at 12nm only
    deck2 = {t: projected[t][-1] * 2 for t in ('1S1R_SLC', '1S1R_MLC')}
    deck4 = {t: projected[t][-1] * 4 for t in ('1S1R_SLC', '1S1R_MLC')}

    x_labels = ['22nm\n(measured)', '16nm\n(projected)', '12nm\n(projected)',
                '12nm\n+2 decks', '12nm\n+4 decks']
    x = np.arange(len(x_labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(13, 7.5))
    for i, t in enumerate(techs):
        ys = list(projected[t])
        if t in deck2:
            ys += [deck2[t], deck4[t]]
        else:
            ys += [np.nan, np.nan]
        ax.bar(x + (i - 1.5) * width, ys, width, label=TECH_LABELS[t],
               color=TECH_COLORS[t], edgecolor='black', linewidth=1.2)

    ax.axhline(1.0, color='gray', linestyle=':', linewidth=1.5)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel('Die-Level Density (× DDR5)')
    ax.set_title('Node scaling: where this could go')
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, max(deck4.values()) * 1.25)

    # Prominent "not measured" badge on the projected region, placed top-left
    # (over the small 16nm/22nm bars) so it never overlaps the tall +4-deck bars.
    ax.axvspan(0.5, len(x_labels) - 0.5, color='#FFD700', alpha=0.12, zorder=0)
    ax.text(0.55, 0.97, 'PROJECTED — NOT MEASURED\n(bounding geometry only)',
            transform=ax.transAxes, ha='left', va='top', fontsize=15, fontweight='bold',
            color='#8B6F00', bbox=dict(boxstyle='round', facecolor='#FFF8DC', edgecolor='#8B6F00'))

    _save(fig, "25_density_projection.png",
          footnote="Projection = measured 22nm ratio x (22/F)^2; DDR5 baseline held fixed. Selector device physics below ~20nm is unvalidated.")


# ============================================================================
# 12. ENDURANCE (Table 5) — NEW  [Slide 26]
# ============================================================================

def slide_endurance():
    """Reproduces Project_Book.typ Table 5. Lifetime = (endurance_cycles x
    cell_count) / write_rate, module-summed, 83.33ms matched-host window.
    Write rates: results/cycle8_matched_host_report.md endurance-counters
    table (module-summed LBM writes/sec)."""
    SECONDS_PER_YEAR = 365.25 * 24 * 3600
    SLC_ENDURANCE = 1e7
    CELLS_8GB = 134_200_000  # 8 GB / 64B line, per Project_Book.typ Section 3.1.4

    # LBM (worst case) write rates/sec, module-summed, from cycle8 report
    write_rate_lbm = {
        '1T1R_SLC': 39_233_764,
        '1S1R_SLC': 27_414_851,
    }
    workloads = {
        'LBM\n(worst case)': write_rate_lbm['1T1R_SLC'],
        'GCC': 2.05e6,
        'STREAM': 1.20e6,
        'AlexNet\nOFMAP': 0.16e6,
    }

    def lifetime_years(write_rate, capacity_gb=8):
        cells = CELLS_8GB * (capacity_gb / 8)
        return (SLC_ENDURANCE * cells) / write_rate / SECONDS_PER_YEAR

    labels = list(workloads.keys())
    at_8gb = [lifetime_years(r, 8) for r in workloads.values()]
    at_64gb = [lifetime_years(r, 64) for r in workloads.values()]

    x = np.arange(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(11, 7))
    ax.bar(x - width / 2, at_8gb, width, label='8 GB (modeled)', color='#4682B4', edgecolor='black', linewidth=1.2)
    ax.bar(x + width / 2, at_64gb, width, label='64 GB (server-class)', color='#87CEEB', edgecolor='black', linewidth=1.2)
    ax.axhspan(5, 10, color='green', alpha=0.12, zorder=0)
    ax.text(len(labels) - 0.5, 7.5, '5–10 yr\nserver target', ha='right', va='center', fontsize=12, color='darkgreen')

    ax.set_yscale('log')
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel('Projected Lifetime (years), log scale')
    ax.set_title('Endurance: capacity- and workload-dependent, 1T1R SLC')
    ax.legend()
    ax.grid(axis='y', which='both', alpha=0.3)

    for i, (v8, v64) in enumerate(zip(at_8gb, at_64gb)):
        ax.text(i - width / 2, v8, f'{v8:.1f}y', ha='center', va='bottom', fontsize=11, fontweight='bold')
        ax.text(i + width / 2, v64, f'{v64:.0f}y', ha='center', va='bottom', fontsize=11, fontweight='bold')

    _save(fig, "26_endurance.png",
          footnote="Assumes ideal uniform wear leveling — no wear-leveling controller implemented in this codebase.")


# ============================================================================
# MAIN
# ============================================================================

def main():
    global OUTPUT_DIR, DATA_DIR

    parser = argparse.ArgumentParser(description="MBMM slide-deck chart generation")
    parser.add_argument("--data-dir", default=DATA_DIR,
                        help="Directory holding processed_*.csv (default: results/system_v6, the book's source dataset).")
    parser.add_argument("--output-dir", default=OUTPUT_DIR,
                        help="Output directory for slide PNGs (default: results/slide_graphs, never final_graphs*).")
    args = parser.parse_args()
    DATA_DIR = args.data_dir
    OUTPUT_DIR = args.output_dir

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"Reading data from: {DATA_DIR}")
    logger.info(f"Writing slides to: {OUTPUT_DIR}\n")

    bar_df = load_bar_chart_metrics()
    hero_df = load_hero_metrics()
    geomeans = load_geometric_means()
    pareto_df = pd.read_csv(os.path.join(DATA_DIR, "processed_pareto_metrics.csv"))
    hw = load_hardware_metrics()

    slide_latency_gcc(bar_df)
    slide_streaming_honest(bar_df)
    slide_latency_gpt2(bar_df)
    slide_mlc_write_penalty(bar_df)
    slide_device_leakage(hw)
    slide_module_power(bar_df)
    slide_pdp_geomean(geomeans)
    slide_pareto_gcc(pareto_df)
    slide_pareto_gpt2(pareto_df)
    slide_density(hero_df)
    slide_density_projection(hero_df)
    slide_endurance()

    logger.info("\n✅ SLIDE CHART GENERATION COMPLETE\n")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
