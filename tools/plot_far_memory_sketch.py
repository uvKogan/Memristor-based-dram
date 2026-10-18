#!/usr/bin/env python3
"""
Figure for Section 3.4 of the MBMM technical report (task E3):

  fig_far_memory_sketch.png -- die-level density (cost axis, DDR5 = 1.00)
  against latency, with the measured far-memory acceptance window shaded and
  Intel Optane PMem drawn as a latency-only device point.

This is a SKETCH OF POSITION, not a cost model. It carries no price, no
projection and no fitted curve: the cost axis is die-level area density,
which is this project's standing cost proxy (Section 3.3, Table 6).

Data provenance -- every plotted value is either read from a frozen CSV under
results/ or is a cited literature constant declared below:

  * Latency (x): `Latency_ns`, Architecture == full_dimm, Benchmark ==
    gcc_spec2017, from results/rev2026-09_primary_csv/
    processed_bar_chart_metrics.csv (the DEFAULT write mode of the primary
    matrix). These are MEDIA latencies at an assumed 800 MHz interface.
  * Density (y): `Area_Density_Ratio` from results/rev2026-09_primary_csv/
    processed_hero_metrics.csv, DDR5_4800 == 1.0 by construction.
  * Optane PMem 305 ns idle random read: DEVICE number, Izraelevitz et al.
    2019, arXiv:1903.05714, via research_notes/
    reviewer_notes_golander_2026-09.md theme (d) and its source [22]. No
    density value is published for it, so it is drawn on the latency axis
    only and labelled as such.
  * Far-memory window 214 to 394 ns: DEVICE idle load-to-use latency of
    shipped CXL-attached DRAM expanders (ASIC-based at the low end, an
    FPGA-based one at the high end), same research note theme (a), sources
    [4] and [5].

Style reference: tools/plot_short_book_figures.py (BOOK_RC, black-edged
marks, bold value labels, italic gray footnote). Colours are the Gold Master
palette of visualize_results.py TECHNOLOGY_COLORS, lines 58-70.

This script never writes into results/ and never runs the pipeline.
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

# Gold Master palette (visualize_results.py TECHNOLOGY_COLORS, lines 58-70)
TECH_COLORS = {
    'DDR5_4800': '#0044FF',
    '1T1R_SLC': '#32CD32',
    '1S1R_SLC': '#00FF00',
    '1T1R_MLC': '#8A2BE2',
    '1S1R_MLC': '#FF00FF',
}
TECH_LABELS = {
    'DDR5_4800': 'DDR5-4800 (modeled)',
    '1T1R_SLC': '1T1R SLC',
    '1S1R_SLC': '1S1R SLC',
    '1T1R_MLC': '1T1R MLC',
    '1S1R_MLC': '1S1R MLC',
}
# Plot order; DDR5 last so its marker sits on top of the reference lines.
TECH_ORDER = ['1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC', 'DDR5_4800']

BENCHMARK = 'gcc_spec2017'
ARCHITECTURE = 'full_dimm'

# --- cited literature constants (see module docstring for the sources) -----
OPTANE_LATENCY_NS = 305.0        # device, idle random read
FAR_MEMORY_WINDOW_NS = (214.0, 394.0)   # device, CXL-attached DRAM expanders

BOOK_RC = {
    'font.size': 9,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 8.5,
    'ytick.labelsize': 8.5,
    'legend.fontsize': 8,
}


def _read_csv(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing frozen CSV: {path}")
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def _value(rows, column, source, **match):
    for row in rows:
        if all(row.get(k) == v for k, v in match.items()):
            raw = row.get(column)
            if raw is None or raw == '':
                raise ValueError(f"{source}: blank {column} for {match}")
            return float(raw)
    raise ValueError(f"{source}: no row for {match}")


def load_points(bar_csv, hero_csv):
    """Return {technology: (latency_ns, density_ratio)} for the five modeled
    tracks, read from the two frozen CSVs. No arithmetic is performed on
    either value."""
    bar_rows = _read_csv(bar_csv)
    hero_rows = _read_csv(hero_csv)
    points = {}
    for tech in TECH_ORDER:
        latency = _value(bar_rows, 'Latency_ns', bar_csv, Technology=tech,
                         Architecture=ARCHITECTURE, Benchmark=BENCHMARK)
        density = _value(hero_rows, 'Area_Density_Ratio', hero_csv,
                         Technology=tech, Benchmark=BENCHMARK)
        points[tech] = (latency, density)
    return points


def plot(points, out_path, dpi=200):
    with plt.rc_context(BOOK_RC):
        fig, ax = plt.subplots(figsize=(6.5, 4.4))

        lo, hi = FAR_MEMORY_WINDOW_NS
        ax.axvspan(lo, hi, color='#9E9E9E', alpha=0.22, zorder=0)
        # Annotation placed to the LEFT of the band's low edge so that the
        # Optane rule inside the band does not overprint it (review L5).
        ax.text(lo * 0.93, 0.06, 'measured far-memory window\n'
                f'{lo:.0f} to {hi:.0f} ns (CXL DRAM devices)',
                ha='right', va='bottom', fontsize=7.5, style='italic',
                color='#424242', zorder=1)

        # Per-track label placement: the two 1T1R points sit close together,
        # so their labels are pushed to opposite sides of their markers.
        label_offset = {
            '1T1R_SLC': (10, -4, 'left'),
            '1T1R_MLC': (-10, 4, 'right'),
            '1S1R_SLC': (10, 6, 'left'),
            '1S1R_MLC': (10, 6, 'left'),
            'DDR5_4800': (10, 6, 'left'),
        }
        for tech in TECH_ORDER:
            x, y = points[tech]
            dx, dy, ha = label_offset[tech]
            ax.scatter([x], [y], s=110, color=TECH_COLORS[tech],
                       edgecolor='black', linewidth=1.0, zorder=4)
            ax.annotate(f'{TECH_LABELS[tech]}\n{x:.1f} ns, {y:.2f}x',
                        (x, y), textcoords='offset points', xytext=(dx, dy),
                        ha=ha, fontsize=7.5, fontweight='bold', zorder=5)

        # Optane: a DEVICE point with no published density. Drawn on the
        # latency axis only, as a vertical rule plus a baseline caret.
        ax.axvline(OPTANE_LATENCY_NS, color='#B71C1C', linestyle=':',
                   linewidth=1.8, zorder=2)
        ax.annotate(f'Optane PMem (device)\n{OPTANE_LATENCY_NS:.0f} ns idle '
                    'random read\nno published density: latency axis only',
                    (OPTANE_LATENCY_NS, 2.72), textcoords='offset points',
                    xytext=(-6, 0), ha='right', va='top', fontsize=7.5,
                    fontweight='bold', color='#B71C1C', zorder=5)

        ax.axhline(1.0, color=TECH_COLORS['DDR5_4800'], linestyle='--',
                   linewidth=1.0, alpha=0.5, zorder=1)

        ax.set_xscale('log')
        ax.set_xlim(30, 560)
        ax.set_ylim(0, 3.0)
        ax.set_xticks([30, 50, 80, 120, 200, 300, 500])
        ax.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.set_xlabel('Latency (ns, log scale)')
        ax.set_ylabel('Die-level density versus DDR5 (DDR5 = 1.00)')
        ax.set_title('Density against latency: a sketch of position')
        ax.grid(alpha=0.3)

        ax.text(0.5, -0.22,
                'Media latencies for the modeled tracks; device latencies for '
                'Optane and for the window.\nSketch of position, not a cost '
                'model: the cost axis is die-level area density (Table 6), '
                'never price.',
                transform=ax.transAxes, ha='center', va='top', fontsize=7.5,
                style='italic', color='dimgray')

        fig.tight_layout()
        fig.savefig(out_path, dpi=dpi, facecolor='white',
                    bbox_inches='tight')
        plt.close(fig)
    return out_path


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(
        description="Render the far-memory density-versus-latency sketch (task E3).")
    parser.add_argument('--bar-csv', default=os.path.join(
        repo_root, 'results', 'rev2026-09_primary_csv',
        'processed_bar_chart_metrics.csv'))
    parser.add_argument('--hero-csv', default=os.path.join(
        repo_root, 'results', 'rev2026-09_primary_csv',
        'processed_hero_metrics.csv'))
    parser.add_argument('--out-dir', default=os.path.join(
        repo_root, 'documents', 'MBMM_Book_Typst', 'media', 'short_book'))
    parser.add_argument('--dpi', type=int, default=200)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    points = load_points(args.bar_csv, args.hero_csv)
    out = os.path.join(args.out_dir, 'fig_far_memory_sketch.png')
    plot(points, out, dpi=args.dpi)
    for tech in TECH_ORDER:
        x, y = points[tech]
        print(f"  {tech:<12} {x:10.4f} ns   {y:.4f}x")
    print(f"Wrote {out}")


if __name__ == '__main__':
    main()
