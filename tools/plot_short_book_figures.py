#!/usr/bin/env python3
"""
Two new figures for the MBMM book, Project_Book.typ (task E2):

  F3  fig_clock_sensitivity.png  -- GCC average total latency versus the
      assumed ReRAM interface clock (800/1333/2400 MHz), 1T1R_SLC and
      1S1R_SLC, full DIMM, with a DDR5-4800 reference line.
  F5  fig_endurance_policy.png   -- projected lifetime at 64 GiB and 1e6
      cycles per cell, grouped by trace and wear-leveling scheme.

Every plotted number is read from a frozen CSV under results/; this script
does no recomputation beyond the stated ns/hours unit conversions. It never
calls, imports from, or modifies any of the existing visualize_*.py scripts
(they carry a hardcoded archive_old_graphs() hazard) -- it only reads their
source as a style/color reference, cited inline below, and (for F5) copies
two small data-loading functions rather than importing them.

Style reference: results/book_figures_rev2026-09/latency/Bar_Latency_gcc_spec2017.png
(black-edged bars, bold title/axis labels, italic gray footnote, value labels
on bars). Colour reference: visualize_results.py TECHNOLOGY_COLORS dict,
lines 58-70 ("Gold Master color palette") -- DDR5_4800 = #0044FF,
1T1R_SLC = #32CD32, 1S1R_SLC = #00FF00. F5's per-scheme colours are new
(visualize_results.py has no per-scheme table); the choice of which scheme
reads as "worst" (red) versus "best" (green) follows the precedent set by
visualize_slides.py slide_endurance_projection(), lines ~1166-1169.

Reuse note (F5): results/slide_graphs_rev2026-09/_deck_builder/ holds only
build_deck.py (HTML assembly from already-rendered PNGs) -- no chart-drawing
code. The actual generator of results/slide_graphs_rev2026-09/15_endurance_projection.png
is slide_endurance_projection() in visualize_slides.py, which reads the same
rows this figure needs via load_endurance_projection() and endurance_value()
(visualize_slides.py lines ~294-328). Those two functions' logic is copied
below (not imported -- the dispatch and the project's CLAUDE.md both forbid
importing from under results/ or calling the existing visualizers) as
load_endurance_rows().
"""
import argparse
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------------------------------------------------------------------
# Colour / style reference (see module docstring for citations)
# ---------------------------------------------------------------------------
TECH_COLORS = {
    'DDR5_4800': '#0044FF',
    '1T1R_SLC': '#32CD32',
    '1S1R_SLC': '#00FF00',
}
TECH_LABELS = {
    'DDR5_4800': 'DDR5-4800',
    '1T1R_SLC': '1T1R SLC',
    '1S1R_SLC': '1S1R SLC',
}

# Scheme display order, label and colour for F5. Order/worst-to-best colour
# sense follows visualize_slides.py slide_endurance_projection() (see module
# docstring); the hex values themselves are chosen fresh for book scale.
SCHEME_STYLE = [
    ('NONE', 'No leveling', '#B71C1C'),
    ('START_GAP', 'Start-Gap (deterministic)', '#EF6C00'),
    ('RANDOMIZED_START_GAP', 'Randomized Start-Gap', '#FBC02D'),
    ('IDEAL', 'Ideal uniform leveling', '#2E7D32'),
]
TRACE_ORDER = [('gcc_spec2017', 'GCC'), ('lbm_spec2017', 'LBM'), ('stream', 'STREAM')]

DDR5_LABEL = 'DDR5-4800 (modeled)'

# Gregorian mean year, used only to render a sub-year lifetime as hours for
# the bar annotation; matches the conversion visualize_slides.py uses for the
# same endurance_table.csv numbers (slide_endurance_projection(), ~line 1180).
HOURS_PER_YEAR = 365.2425 * 24


# ---------------------------------------------------------------------------
# F3 data loading
# ---------------------------------------------------------------------------

def load_clock_series(paths):
    """paths: dict of {mhz: csv_path}, each a processed_bar_chart_metrics.csv.

    Returns a dict:
      {
        '1T1R_SLC': [latency_ns_at_each_mhz_in_paths_order...],
        '1S1R_SLC': [...],
        'DDR5_4800': latency_ns (single float, read from the 800 MHz file),
        'mhz': [sorted mhz values, matching the per-tech lists' order],
      }

    Reads Latency_ns for Technology in {1T1R_SLC, 1S1R_SLC}, Architecture ==
    full_dimm, Benchmark == gcc_spec2017, from each frozen CSV in `paths`,
    in ascending MHz order. DDR5_4800 is read once, from the file at the
    lowest MHz key (the dispatch's primary CSV), since it does not depend on
    the ReRAM interface clock.
    """
    mhz_order = sorted(paths)
    result = {'1T1R_SLC': [], '1S1R_SLC': [], 'mhz': mhz_order}
    for mhz in mhz_order:
        path = paths[mhz]
        rows = _read_bar_chart_csv(path)
        for tech in ('1T1R_SLC', '1S1R_SLC'):
            result[tech].append(_bar_chart_value(
                rows, tech, 'full_dimm', 'gcc_spec2017', 'Latency_ns', path))
    ddr5_path = paths[mhz_order[0]]
    ddr5_rows = _read_bar_chart_csv(ddr5_path)
    result['DDR5_4800'] = _bar_chart_value(
        ddr5_rows, 'DDR5_4800', 'full_dimm', 'gcc_spec2017', 'Latency_ns', ddr5_path)
    return result


def _read_bar_chart_csv(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing frozen CSV: {path}")
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def _bar_chart_value(rows, technology, architecture, benchmark, column, source):
    for row in rows:
        if (row.get('Technology') == technology
                and row.get('Architecture') == architecture
                and row.get('Benchmark') == benchmark):
            raw = row.get(column)
            if raw is None or raw == '':
                raise ValueError(
                    f"{source}: missing {column} for Technology={technology!r}, "
                    f"Architecture={architecture!r}, Benchmark={benchmark!r}")
            return float(raw)
    raise ValueError(
        f"{source}: no row for Technology={technology!r}, "
        f"Architecture={architecture!r}, Benchmark={benchmark!r}")


# ---------------------------------------------------------------------------
# F5 data loading (copied from visualize_slides.py's
# load_endurance_projection()/endurance_value(), lines ~294-328; not
# imported, per the dispatch's "do not import from under results/" and the
# project rule against calling the existing visualizers)
# ---------------------------------------------------------------------------

def load_endurance_rows(path, capacity_gib=64, endurance=1000000.0,
                         write_reduction=1.0, rate_basis='admitted'):
    """Rows of results/endurance_table.csv matching the F5 slice: the given
    capacity_gib/endurance/write_reduction/rate_basis, for the three CPU/
    streaming traces (gcc_spec2017, lbm_spec2017, stream) and every scheme
    the file itself carries for those rows.

    Returns a list of dicts: {'trace', 'scheme', 'lifetime_years'}.
    Fails loudly (not silently) if the file is missing or the slice is
    empty, matching load_endurance_projection()'s behaviour.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing endurance table: {path}")
    with open(path, newline='') as f:
        all_rows = list(csv.DictReader(f))

    wanted_traces = {t for t, _ in TRACE_ORDER}

    def matches(row):
        try:
            return (float(row['capacity_gib']) == capacity_gib
                    and float(row['endurance']) == endurance
                    and float(row['write_reduction']) == write_reduction
                    and row['rate_basis'] == rate_basis
                    and row['trace'] in wanted_traces)
        except (KeyError, ValueError):
            return False

    sel = [row for row in all_rows if matches(row)]
    if not sel:
        raise ValueError(
            f"{path}: no rows for capacity_gib={capacity_gib}, "
            f"endurance={endurance}, write_reduction={write_reduction}, "
            f"rate_basis={rate_basis!r}")

    out = []
    for row in sel:
        raw = row.get('lifetime_years')
        if raw is None or raw == '':
            raise ValueError(
                f"{path}: lifetime_years is blank for trace={row['trace']!r}, "
                f"scheme={row['scheme']!r}")
        out.append({
            'trace': row['trace'],
            'scheme': row['scheme'],
            'lifetime_years': float(raw),
        })
    return out


def _endurance_value(rows, trace, scheme):
    for row in rows:
        if row['trace'] == trace and row['scheme'] == scheme:
            return row['lifetime_years']
    raise ValueError(f"no endurance row for trace={trace!r}, scheme={scheme!r}")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

BOOK_RC = {
    'font.size': 9,
    'axes.titlesize': 11,
    'axes.labelsize': 10,
    'xtick.labelsize': 8.5,
    'ytick.labelsize': 8.5,
    'legend.fontsize': 8,
}


def plot_clock(series, out_path, dpi=200):
    """series: the dict returned by load_clock_series()."""
    with plt.rc_context(BOOK_RC):
        fig, ax = plt.subplots(figsize=(6.5, 4.2))
        mhz = series['mhz']

        # 1T1R_SLC is always the higher of the two series at every clock, so
        # placing its labels above the marker and 1S1R_SLC's below moves the
        # two label sets apart rather than toward each other (fix round 1,
        # legibility item 1). 1S1R_SLC also gets a square marker and a
        # dashed line (legibility item 2) so the two similarly-green series
        # (colors from visualize_results.py TECHNOLOGY_COLORS, lines 58-70;
        # see module docstring) stay distinguishable in grayscale.
        MARKER_STYLE = {'1T1R_SLC': ('o', '-'), '1S1R_SLC': ('s', '--')}
        LABEL_STYLE = {'1T1R_SLC': (9, 'bottom'), '1S1R_SLC': (-9, 'top')}

        for tech in ('1T1R_SLC', '1S1R_SLC'):
            marker, linestyle = MARKER_STYLE[tech]
            ax.plot(mhz, series[tech], marker=marker, linestyle=linestyle,
                    linewidth=2, markersize=6, color=TECH_COLORS[tech],
                    label=TECH_LABELS[tech])
            y_offset, va = LABEL_STYLE[tech]
            for x, y in zip(mhz, series[tech]):
                ax.annotate(f'{y:.1f}', (x, y), textcoords='offset points',
                            xytext=(0, y_offset), ha='center', va=va,
                            fontsize=7.5, fontweight='bold')

        ddr5 = series['DDR5_4800']
        ax.axhline(ddr5, color=TECH_COLORS['DDR5_4800'], linestyle='--', linewidth=1.6)
        ax.text(mhz[0], ddr5 * 1.02, f'{DDR5_LABEL}: {ddr5:.1f} ns',
                ha='left', va='bottom', color=TECH_COLORS['DDR5_4800'],
                fontsize=8, fontweight='bold')

        ax.set_xticks(mhz)
        ax.set_xlabel('ReRAM interface clock (MHz)')
        ax.set_ylabel('Average total latency (ns)')
        ax.set_title('GCC: latency versus the assumed interface clock, full DIMM')
        ax.set_ylim(0, max(ddr5, max(series['1T1R_SLC'])) * 1.25)
        ax.grid(axis='y', alpha=0.3)
        ax.legend(loc='upper right')

        ax.text(0.98, 0.60,
                'only tRCD + tCAS are NVSim device time;\nthe rest are interface cycle counts',
                transform=ax.transAxes, ha='right', va='top', fontsize=7.5,
                style='italic', color='dimgray',
                bbox=dict(boxstyle='round', facecolor='white', edgecolor='lightgray', alpha=0.9))

        fig.tight_layout()
        fig.savefig(out_path, dpi=dpi, facecolor='white')
        plt.close(fig)
    return out_path


def _format_lifetime(years):
    if years >= 1.0:
        return f'{years:.1f} yr'
    if years >= 0.1:
        return f'{years:.2f} yr'
    hours = years * HOURS_PER_YEAR
    if hours >= 1.0:
        return f'{hours:.1f} h'
    return f'{hours * 60:.1f} min'


def plot_endurance(rows, out_path, dpi=200):
    """rows: the list returned by load_endurance_rows()."""
    with plt.rc_context(BOOK_RC):
        fig, ax = plt.subplots(figsize=(6.5, 4.6))

        x = range(len(TRACE_ORDER))
        n_schemes = len(SCHEME_STYLE)
        width = 0.8 / n_schemes

        for i, (scheme, label, color) in enumerate(SCHEME_STYLE):
            ys = [_endurance_value(rows, trace, scheme) for trace, _ in TRACE_ORDER]
            xs = [xi + (i - (n_schemes - 1) / 2.0) * width for xi in x]
            bars = ax.bar(xs, ys, width, label=label, color=color,
                          edgecolor='black', linewidth=1.0)
            for bar, y in zip(bars, ys):
                ax.text(bar.get_x() + bar.get_width() / 2., y * 1.15,
                        _format_lifetime(y), ha='center', va='bottom',
                        fontsize=6.5, fontweight='bold', rotation=90)

        ax.set_yscale('log')
        ax.set_xticks(list(x))
        ax.set_xticklabels([label for _, label in TRACE_ORDER])
        ax.set_ylabel('Projected lifetime (years, log scale)')
        ax.set_title('Projected lifetime at 64 GiB and 1e6 cycles per\ncell, by wear-leveling policy', fontsize=10.5)
        ax.legend(loc='upper left', ncol=2, fontsize=6.8)
        ax.grid(axis='y', which='both', alpha=0.3)

        top = max(_endurance_value(rows, trace, 'IDEAL') for trace, _ in TRACE_ORDER)
        bottom = min(_endurance_value(rows, trace, scheme)
                     for trace, _ in TRACE_ORDER for scheme, _, _ in SCHEME_STYLE)
        ax.set_ylim(bottom * 0.3, top * 40)

        fig.tight_layout()
        fig.savefig(out_path, dpi=dpi, facecolor='white')
        plt.close(fig)
    return out_path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def _default_paths(repo_root):
    return {
        800: os.path.join(repo_root, 'results', 'rev2026-09_primary_csv',
                           'processed_bar_chart_metrics.csv'),
        1333: os.path.join(repo_root, 'results', 'system_rev2026-09_freq1333',
                            '_csv', 'processed_bar_chart_metrics.csv'),
        2400: os.path.join(repo_root, 'results', 'system_rev2026-09_freq2400',
                            '_csv', 'processed_bar_chart_metrics.csv'),
    }


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    parser = argparse.ArgumentParser(description="Render the two book figures (task E2).")
    parser.add_argument('--out-dir', default=os.path.join(
        repo_root, 'documents', 'MBMM_Book_Typst', 'media', 'short_book'))
    parser.add_argument('--endurance-csv', default=os.path.join(
        repo_root, 'results', 'endurance_table.csv'))
    parser.add_argument('--dpi', type=int, default=200)
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    clock_series = load_clock_series(_default_paths(repo_root))
    clock_out = os.path.join(args.out_dir, 'fig_clock_sensitivity.png')
    plot_clock(clock_series, clock_out, dpi=args.dpi)
    print(f"Wrote {clock_out}")

    endurance_rows = load_endurance_rows(args.endurance_csv)
    endurance_out = os.path.join(args.out_dir, 'fig_endurance_policy.png')
    plot_endurance(endurance_rows, endurance_out, dpi=args.dpi)
    print(f"Wrote {endurance_out}")


if __name__ == '__main__':
    main()
