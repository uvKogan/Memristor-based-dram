#!/usr/bin/env python3
"""
Supplementary script: Theoretical Effective F² Cell-Area Scaling

Generates a process-agnostic, feature-size-normalized bar chart for the
Project Book academic appendix. No simulation data is read; values are
derived purely from published cell-area formulas:

    Effective F² = cell_area_F² / bits_per_cell

References:
  - 1T1R cell area:  20 F²  (CMOS access transistor, Xue et al. ISSCC 2021)
  - 1S1R cell area:   4 F²  (selector crossbar,  Crossbar Inc. 4 Mb array)
  - JEDEC DRAM:       6 F²  (industry consensus baseline, JEDEC JESD79-5)
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

OUTPUT_PATH = "/home/yuvalk/MBMM/results/final_graphs/theoretical_f2_scaling.png"

# ── Data ──────────────────────────────────────────────────────────────────────
ARCHITECTURES = ['1T1R\nSLC', '1T1R\nMLC', '1S1R\nSLC', '1S1R\nMLC']
EFFECTIVE_F2  = [20.0,         10.0,         4.0,          2.0]
DDR5_BASELINE = 6.0

# Gold Master color palette (matches project-wide TECHNOLOGY_COLORS)
COLORS = ['#32CD32', '#8A2BE2', '#00FF00', '#FF00FF']

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(8, 5.5))
fig.patch.set_facecolor('#0d0d0d')
ax.set_facecolor('#1a1a1a')

bars = ax.bar(ARCHITECTURES, EFFECTIVE_F2, color=COLORS,
              width=0.55, edgecolor='white', linewidth=0.6, zorder=3)

# Value labels on bars
for bar, val in zip(bars, EFFECTIVE_F2):
    ax.text(bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.25,
            f'{val:.1f} F²',
            ha='center', va='bottom',
            fontsize=11, fontweight='bold', color='white')

# DDR5 baseline reference line
ax.axhline(y=DDR5_BASELINE, color='#0044FF', linewidth=1.8,
           linestyle='--', zorder=4)
ax.text(len(ARCHITECTURES) - 0.45, DDR5_BASELINE + 0.35,
        'DDR5 Equivalent (6 F²)',
        color='#0044FF', fontsize=9.5, fontweight='bold', ha='right')

# Axes styling
ax.set_ylim(0, max(EFFECTIVE_F2) * 1.18)
ax.set_ylabel('Effective F² (Cell Area per Bit)', color='white', fontsize=11)
ax.set_title('Theoretical Cell-Area Scaling: Effective F² per Bit\n'
             '22 nm Process Node — Process-Agnostic Normalization',
             color='white', fontsize=12, fontweight='bold', pad=12)

ax.tick_params(colors='white', labelsize=10)
for spine in ax.spines.values():
    spine.set_edgecolor('#444444')
ax.yaxis.label.set_color('white')
ax.xaxis.label.set_color('white')
ax.grid(axis='y', color='#333333', linewidth=0.7, zorder=0)

# Legend patch for DDR5 line
ddr5_patch = mpatches.Patch(color='#0044FF', label='JEDEC DDR5-4800 Baseline (6 F²)')
ax.legend(handles=[ddr5_patch], loc='upper right',
          facecolor='#2a2a2a', edgecolor='#555555',
          labelcolor='white', fontsize=9)

plt.tight_layout()
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
plt.close()

print(f"[OK] Chart saved → {OUTPUT_PATH}")

# ── Console summary ───────────────────────────────────────────────────────────
print("\nEffective F² Summary (22 nm, process-agnostic)")
print(f"  {'Architecture':<12}  {'Effective F²':>12}  {'vs DDR5 (6F²)':>14}")
print("  " + "-" * 42)
for arch, f2 in zip(ARCHITECTURES, EFFECTIVE_F2):
    label = arch.replace('\n', '_')
    ratio = f2 / DDR5_BASELINE
    direction = f"{ratio:.2f}× larger" if ratio > 1 else f"{1/ratio:.2f}× smaller"
    print(f"  {label:<12}  {f2:>10.1f} F²  {direction:>14}")
print(f"  {'DDR5_baseline':<12}  {DDR5_BASELINE:>10.1f} F²  {'1.00× (baseline)':>14}")
