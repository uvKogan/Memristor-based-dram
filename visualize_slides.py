#!/usr/bin/env python3
"""
MBMM Visualization - Presentation Slide Charts (2026-09 revision)

Restyled, trimmed-technology-set charts built from the SAME processed data
as the report figures (visualize_results.py / visualize_pareto.py /
visualize_hero_graphs.py), for a live 60-min talk rather than a written
report: fewer technologies per chart (only the ones the slide's story is
about), larger fonts, no dense report footnotes.

Every value plotted here, and every result number quoted in a chart's
footnote, is read from the frozen result set of the 2026-09 revision. The
sources are:

  - CSV_DIR/processed_bar_chart_metrics.csv, processed_hero_metrics.csv,
    processed_geometric_means.csv, processed_pareto_metrics.csv,
    hardware_metrics.json   (the primary matrix; --csv-dir)
  - DATA_DIR/stats_*.out    (the same run's raw NVMain stats, used for
    module capacity and for write rates; --data-dir)
  - SENS_ROOT/system_rev2026-09_<axis>/_csv/...  (the sensitivity axes:
    channels1_ai, freq1333, freq2400, queue8, queue128, org1024;
    --sens-root)
  - ENDURANCE_CSV           (results/endurance_table.csv; --endurance-csv)
  - SIDECAR_DIR/<trace>.nvt.sidecar.json  (trace provenance: record counts
    and burst spans; --sidecar-dir)

The ONE exception is CITED_CONSTANTS below: a small, explicitly documented
table of figures that come from published papers rather than from any run
of this pipeline (fabricated-chip timings, a demonstrated cell area). Each
entry names its source. Nothing in CITED_CONSTANTS is a result of this
work, and no plotted value comes from it.

Two chart groups have no equivalent report script because the book carries
them as tables rather than figures:

  - Endurance (Table 5): PROJECTED lifetime by wear-leveling scheme, read
    straight out of results/endurance_table.csv. Nothing here is a measured
    lifetime; every lifetime is a projection from a write distribution that
    was measured per location in the simulation.
  - Density projection (Table 6): projected = measured 22nm
    Area_Density_Ratio (processed_hero_metrics.csv) x (22/F)^2, with the
    2x/4x deck-stacking multipliers applied only to the selector (1S1R)
    rows, exactly as derived in Project_Book.typ Section 3.3.

This script only reads existing processed outputs (or applies the book's
own documented closed-form projection to them) - it does not run NVSim/
NVMain and is not gated by mbmm_master.py. Every loader fails loudly,
naming the file and the key, rather than plotting a silent default.

Output: /home/yuvalk/MBMM/results/slide_graphs_rev2026-09/ (never touches
results/final_graphs*, which the book's embedded figures depend on).
"""

import argparse
import json
import os
import re
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from logging_config import setup_logging
from process_metrics import RERAM_KEY_PREFIX, CPUFREQ_MHZ

logger = setup_logging("visualize_slides")

# ============================================================================
# CONFIGURATION
# ============================================================================

# DATA_DIR holds the raw NVMain stats_*.out files (this revision's primary
# run). CSV_DIR holds the processed_*.csv files and hardware_metrics.json
# process_metrics.py writes at its OUTPUT_DIR. SENS_ROOT holds the
# per-axis sensitivity result directories of T5.1 step 2.
DATA_DIR = "/home/yuvalk/MBMM/results/system_rev2026-09_primary"
CSV_DIR = "/home/yuvalk/MBMM/results/rev2026-09_primary_csv"
SENS_ROOT = "/home/yuvalk/MBMM/results"
ENDURANCE_CSV = "/home/yuvalk/MBMM/results/endurance_table.csv"
SIDECAR_DIR = "/home/yuvalk/MBMM/benchmarks"
HARDWARE_METRICS_FILE = os.path.join(CSV_DIR, "hardware_metrics.json")
OUTPUT_DIR = "/home/yuvalk/MBMM/results/slide_graphs_rev2026-09"

# Published figures quoted in chart footnotes as context. NONE of these is a
# result of this pipeline and none is ever plotted; they are listed here, with
# their sources, so a reader can tell at a glance which footnote numbers are
# measurements of this work and which are citations. Everything else in a
# footnote is derived from the frozen data at render time.
CITED_CONSTANTS = {
    # Zahurak et al., "Process Integration of a 27nm, 16Gb Cu ReRAM", IEDM
    # 2014, Table 1. Project_Book.typ [49]; the source of the 1T1R SILICON
    # configuration's timings.
    'micron_1t1r_read_us': 2.3,
    'micron_1t1r_write_us': 11.7,
    # Liu et al., "A 130.7-mm2 2-Layer 32-Gb ReRAM Memory Device in 24-nm
    # Technology", IEEE JSSC 2014, Table II. Project_Book.typ [48]; the source
    # of the 1S1R SILICON configuration's timings.
    'sandisk_1s1r_read_us': 40.0,
    'sandisk_1s1r_write_us': 230.0,
    # Fackenthal et al., ISSCC 2014, the 6F2 recessed-channel 16 Gb part.
    # Project_Book.typ [33] and Section 3.3: substituting its cell area would
    # lift the 1T1R density ratio to roughly this figure.
    'recessed_channel_1t1r_density_x': 1.2,
}

# Six visually separable hues. The two access devices are deliberately NOT
# two shades of one colour any more: at a matched organization they are not
# a two-tier story, and a slide read from the back of a room should not
# suggest one.
TECH_COLORS = {
    'DDR5_4800': '#1A56DB',
    'pcm_microsoft_2009': '#D92B2B',
    '1T1R_SLC': '#3FA845',
    '1S1R_SLC': '#0E7C86',
    '1T1R_MLC': '#8A2BE2',
    '1S1R_MLC': '#D81B8C',
    'DDR5_4800_64B': '#00AACC',
    '1T1R_SILICON': '#6B705C',
    '1S1R_SILICON': '#C97A2B',
}
TECH_LABELS = {
    'DDR5_4800': 'DDR5-4800',
    'pcm_microsoft_2009': 'PCM (legacy)',
    '1T1R_SLC': '1T1R SLC',
    '1T1R_MLC': '1T1R MLC',
    '1S1R_SLC': '1S1R SLC',
    '1S1R_MLC': '1S1R MLC',
    'DDR5_4800_64B': 'DDR5-4800 (64 B cross-check)',
    '1T1R_SILICON': '1T1R silicon\n(Micron 16 Gb)',
    '1S1R_SILICON': '1S1R silicon\n(SanDisk 32 Gb)',
}

BENCH_LABELS = {
    'gcc_spec2017': 'GCC',
    'lbm_spec2017': 'LBM',
    'stream': 'STREAM',
    'gpt2_ifmap': 'GPT-2 IFMAP',
    'alexnet_layer1_ifmap': 'AlexNet IFMAP',
    'alexnet_layer1_ofmap': 'AlexNet OFMAP',
}

# The slide charts only ever plot a small, explicitly-listed subset of
# technologies (see each slide_* function below), never "every technology in
# the CSV" -- so there is no risk of a secondary/cross-check row silently
# appearing on a slide it does not belong on. The two SILICON rows DO appear
# on the counterweight charts, which load the unfiltered frame on purpose.
PRIMARY_TECHNOLOGIES = {
    'DDR5_4800', 'pcm_microsoft_2009',
    '1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC',
}
SECONDARY_TECHNOLOGIES = {'DDR5_4800_64B', '1T1R_SILICON', '1S1R_SILICON'}
KNOWN_TECHNOLOGIES = PRIMARY_TECHNOLOGIES | SECONDARY_TECHNOLOGIES

# The sensitivity axes this script reads, and what each one is. Each maps to
# results/system_rev2026-09_<axis>/_csv/ (T5.1 run record in
# documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md).
SENSITIVITY_AXES = {
    'channels1_ai': 'one memory channel, AI input maps (channel control run)',
    'freq1333': 'ReRAM interface clock 1333 MHz',
    'freq2400': 'ReRAM interface clock 2400 MHz',
    'queue8': 'controller queue depth 8',
    'queue128': 'controller queue depth 128',
    'org1024': '1024 x 1024 subarray organization',
}


def _check_known_technologies(techs, source):
    unknown = sorted(set(techs) - KNOWN_TECHNOLOGIES)
    if unknown:
        raise ValueError(
            f"{source}: unknown Technology label(s) {unknown} -- add them to "
            f"PRIMARY_TECHNOLOGIES/SECONDARY_TECHNOLOGIES in visualize_slides.py "
            f"before plotting."
        )


def filter_primary_technologies(df, column='Technology'):
    """Keep only PRIMARY_TECHNOLOGIES rows; raises loudly first if df holds a
    Technology label that is neither primary nor a known secondary one."""
    _check_known_technologies(df[column].unique(), column)
    return df[df[column].isin(PRIMARY_TECHNOLOGIES)]

# Slide-scale typography (report scripts use 9-15pt; slides need to read from
# the back of a room).
plt.rcParams.update({
    'font.size': 15,
    'axes.titlesize': 19,
    'axes.labelsize': 16,
    'xtick.labelsize': 13,
    'ytick.labelsize': 13,
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
    """Write one chart. The footnote is hard-wrapped rather than left to
    matplotlib: an unwrapped one-line footnote makes bbox_inches='tight'
    widen the whole canvas to the text and squash the axes."""
    if footnote:
        if chr(0x2014) in footnote:            # U+2014, banned project-wide
            raise ValueError(f"{name}: footnote contains an em-dash")
        # Width in characters is scaled to the figure width so the wrapped
        # block stays inside the axes area at any panel count.
        width = max(80, int(fig.get_size_inches()[0] * 11))
        lines = textwrap.wrap(" ".join(footnote.split()), width=width)
        fig.tight_layout(rect=[0, 0.035 + 0.030 * len(lines), 1, 1])
        fig.text(0.5, 0.012, "\n".join(lines), ha='center', va='bottom',
                 fontsize=11, style='italic', color='dimgray',
                 linespacing=1.35)
    else:
        fig.tight_layout()
    out = os.path.join(OUTPUT_DIR, name)
    fig.savefig(out, dpi=170, facecolor='white')
    logger.info(f"  Saved: {out}")
    plt.close(fig)


# ============================================================================
# DATA LOADING
# ============================================================================

def _read_csv(path):
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing processed CSV: {path}")
    return pd.read_csv(path)


def load_bar_chart_metrics():
    """Primary matrix, unfiltered (the SILICON rows are wanted by the
    counterweight charts). Unknown labels still raise."""
    df = _read_csv(os.path.join(CSV_DIR, "processed_bar_chart_metrics.csv"))
    _check_known_technologies(df['Technology'].unique(), "processed_bar_chart_metrics.csv")
    return df


def load_hero_metrics():
    df = _read_csv(os.path.join(CSV_DIR, "processed_hero_metrics.csv"))
    _check_known_technologies(df['Technology'].unique(), "processed_hero_metrics.csv")
    return df


def load_geometric_means():
    df = _read_csv(os.path.join(CSV_DIR, "processed_geometric_means.csv"))
    _check_known_technologies(df['Technology'].unique(), "processed_geometric_means.csv")
    return dict(zip(df['Technology'], df['Geometric_Mean_PDP']))


def load_hardware_metrics(path=None):
    path = path or HARDWARE_METRICS_FILE
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing hardware metrics JSON: {path}")
    with open(path) as f:
        return json.load(f)


def sensitivity_csv_path(axis, name="processed_bar_chart_metrics.csv"):
    """Path to one file of a T5.1 sensitivity axis. Refuses an axis this
    script does not know about, so a typo cannot silently read the wrong
    directory."""
    if axis not in SENSITIVITY_AXES:
        raise ValueError(
            f"Unknown sensitivity axis {axis!r}; known axes: "
            f"{sorted(SENSITIVITY_AXES)}"
        )
    return os.path.join(SENS_ROOT, f"system_rev2026-09_{axis}", "_csv", name)


def load_sensitivity_bar_chart(axis):
    """processed_bar_chart_metrics.csv of one sensitivity axis."""
    path = sensitivity_csv_path(axis)
    df = _read_csv(path)
    _check_known_technologies(df['Technology'].unique(), path)
    return df


def load_endurance_projection(capacity_gib=64, endurance=1e6,
                              write_reduction=1.0, rate_basis='admitted'):
    """The PROJECTED lifetime rows of results/endurance_table.csv that the
    book's Table 5 is built from. Nothing in this frame is a measured
    lifetime. Fails loudly if the requested slice is empty."""
    if not os.path.isfile(ENDURANCE_CSV):
        raise FileNotFoundError(f"Missing endurance table: {ENDURANCE_CSV}")
    df = pd.read_csv(ENDURANCE_CSV)
    sel = df[(df['capacity_gib'] == capacity_gib)
             & (df['endurance'] == endurance)
             & (df['write_reduction'] == write_reduction)
             & (df['rate_basis'] == rate_basis)]
    if sel.empty:
        raise ValueError(
            f"{ENDURANCE_CSV}: no rows for capacity_gib={capacity_gib}, "
            f"endurance={endurance}, write_reduction={write_reduction}, "
            f"rate_basis={rate_basis!r}"
        )
    return sel


def endurance_value(df, trace, scheme, column='lifetime_years'):
    """One cell of the endurance projection, named by trace and scheme."""
    row = df[(df['trace'] == trace) & (df['scheme'] == scheme)]
    if row.empty:
        raise ValueError(
            f"{ENDURANCE_CSV}: no row for trace={trace!r}, scheme={scheme!r}"
        )
    value = row.iloc[0][column]
    if pd.isna(value):
        raise ValueError(
            f"{ENDURANCE_CSV}: {column} is blank for trace={trace!r}, "
            f"scheme={scheme!r}"
        )
    return value


def bench_row(df, benchmark, tech, arch='full_dimm'):
    row = df[(df['Benchmark'] == benchmark) & (df['Technology'] == tech)
             & (df['Architecture'] == arch)]
    return row.iloc[0] if not row.empty else None


def value(df, benchmark, tech, column, arch='full_dimm', source='processed_bar_chart_metrics.csv'):
    """One CSV cell, or a loud failure naming the file and the key."""
    row = bench_row(df, benchmark, tech, arch)
    if row is None:
        raise ValueError(
            f"{source}: no row for Technology={tech!r}, Architecture={arch!r}, "
            f"Benchmark={benchmark!r}"
        )
    if column not in row or pd.isna(row[column]):
        raise ValueError(
            f"{source}: missing {column} for Technology={tech!r}, "
            f"Architecture={arch!r}, Benchmark={benchmark!r}"
        )
    return row[column]


# The two non-ReRAM baselines are single, non-replicated modules, so their
# stats filenames carry no architecture token (process_metrics.py's
# extract_benchmark() strips exactly these prefixes). They are needed here
# only so the per-gigabyte charts can read each module's own capacity back
# out of its own run.
NON_RERAM_STATS_STEM = {
    'DDR5_4800': 'DDR5_4800_DRAM_subchannel',
    'DDR5_4800_64B': 'DDR5_4800_DRAM_64B',
    'pcm_microsoft_2009': 'pcm_microsoft_2009',
}


def _stats_path(technology, arch, benchmark):
    """Path to this run's raw NVMain stats file for (technology, arch,
    benchmark), under DATA_DIR. Reuses process_metrics.py's own
    RERAM_KEY_PREFIX table so the filename convention cannot drift from the
    parser that produces the processed CSVs."""
    # RERAM_KEY_PREFIX maps the SILICON labels onto the SLC hardware key (for
    # area lookups); their stats files are named differently, so resolving
    # them here would silently return the SLC run.
    if technology.endswith('_SILICON'):
        raise ValueError(
            f"{technology!r} stats files do not follow the RERAM_KEY_PREFIX "
            f"naming; _stats_path() would return the SLC run instead."
        )
    if technology in NON_RERAM_STATS_STEM:
        path = os.path.join(
            DATA_DIR, f"stats_{NON_RERAM_STATS_STEM[technology]}_{benchmark}.out")
    else:
        prefix = RERAM_KEY_PREFIX.get(technology)
        if prefix is None:
            raise ValueError(
                f"No stats-file prefix known for technology {technology!r} -- "
                f"add it to RERAM_KEY_PREFIX in process_metrics.py or to "
                f"NON_RERAM_STATS_STEM here."
            )
        path = os.path.join(DATA_DIR, f"stats_{prefix}_{arch}_{benchmark}.out")
    if not os.path.isfile(path):
        raise FileNotFoundError(
            f"Missing stats file for {technology}/{arch}/{benchmark}: {path}"
        )
    return path


def _extract_total_write_requests(content, path):
    """Sum of every 'totalWriteRequests' value in a stats file (normally a
    single DIMM-wide aggregate line, defaultMemory.totalWriteRequests)."""
    matches = re.findall(r'totalWriteRequests\s+(\d+)', content)
    if not matches:
        raise ValueError(f"{path}: no 'totalWriteRequests' stat found")
    return sum(int(m) for m in matches)


def _extract_elapsed_seconds(content, path, cpufreq_mhz=CPUFREQ_MHZ):
    """This run's own elapsed simulated time, from NVMain's 'Exiting at
    cycle <n>' line (GLOBAL/CPUFreq clock domain) -- never assume a fixed
    matched-window duration, since it can legitimately differ per run."""
    m = re.search(r'Exiting at cycle\s+(\d+)', content)
    if not m:
        raise ValueError(f"{path}: no 'Exiting at cycle' line found")
    cycles = int(m.group(1))
    if cycles <= 0:
        raise ValueError(f"{path}: non-positive elapsed cycle count ({cycles})")
    return cycles * (1000.0 / cpufreq_mhz) * 1e-9


def _extract_capacity_gib(content, path):
    """Module capacity in GiB, summed over the channels NVMain prints
    ('<controller> capacity is <n> MB.'). This is module geometry read back
    from the run itself, never a typed constant: the per-GiB power and PDP
    charts divide by it."""
    matches = re.findall(r'capacity is\s+(\d+)\s+MB', content)
    if not matches:
        raise ValueError(f"{path}: no 'capacity is <n> MB' line found")
    total_mb = sum(int(m) for m in matches)
    if total_mb <= 0:
        raise ValueError(f"{path}: non-positive module capacity ({total_mb} MB)")
    return total_mb / 1024.0


def module_capacity_gib(technology, arch='full_dimm', benchmark='gcc_spec2017'):
    """Capacity of the simulated module, read from its own stats file."""
    path = _stats_path(technology, arch, benchmark)
    with open(path) as f:
        return _extract_capacity_gib(f.read(), path)


def _lbm_completion_pct(df, techs, arch='full_dimm', benchmark='lbm_spec2017'):
    """LBM completion percentages: completion_pct() with the LBM default."""
    return completion_pct(df, techs, benchmark, arch)


def load_trace_sidecar(trace):
    """The provenance sidecar written beside a trace: record counts and the
    cycle span the parser recorded. Used for the burst figures a chart
    footnote quotes, so they cannot drift from the trace itself."""
    path = os.path.join(SIDECAR_DIR, f"{trace}.nvt.sidecar.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing trace sidecar: {path}")
    with open(path) as f:
        return json.load(f)


def trace_records(trace):
    """Whole-trace record count, from the trace's own sidecar. The gem5 parser
    nests it under `records.total`; the SCALE-Sim parser writes
    `records_written`."""
    side = load_trace_sidecar(trace)
    rec = side.get('records')
    if isinstance(rec, dict) and 'total' in rec:
        return int(rec['total'])
    if 'records_written' in side:
        return int(side['records_written'])
    raise ValueError(
        f"{trace}.nvt.sidecar.json: no record count (neither records.total "
        f"nor records_written)"
    )


def trace_span_us(trace, cpufreq_mhz=CPUFREQ_MHZ):
    """Span of a trace in microseconds, from its sidecar's own cycle range on
    the CPUFreq basis. Only meaningful for the AI traces, which end inside the
    replay window; the gem5 traces run longer than the window."""
    side = load_trace_sidecar(trace)
    cycles = side.get('cycles')
    if not isinstance(cycles, dict) or 'last_cycle' not in cycles:
        raise ValueError(f"{trace}.nvt.sidecar.json: no cycles.last_cycle")
    span_cycles = int(cycles['last_cycle']) - int(cycles.get('first_cycle', 0))
    return span_cycles * (1000.0 / cpufreq_mhz) / 1000.0


def breakeven_gating_fraction(df, benchmark='gcc_spec2017',
                              reram='1T1R_SLC', baseline='DDR5_4800'):
    """The fraction of the ReRAM module's static component that would have to
    be gated for its power per gigabyte to equal the DDR5 baseline's. This is
    the same arithmetic Project_Book.typ Section 3.1.2 performs, done here on
    the data rather than transcribed, so the footnote cannot drift."""
    r_total = value(df, benchmark, reram, 'Power')
    r_static = value(df, benchmark, reram, 'Static_Power')
    if r_static <= 0:
        raise ValueError(
            f"processed_bar_chart_metrics.csv: non-positive Static_Power for "
            f"{reram!r} on {benchmark!r}"
        )
    r_cap = module_capacity_gib(reram, benchmark=benchmark)
    b_per_gib = (value(df, benchmark, baseline, 'Power')
                 / module_capacity_gib(baseline, benchmark=benchmark))
    return (r_total - b_per_gib * r_cap) / r_static


def completion_pct(df, techs, benchmark, arch='full_dimm'):
    """Completion percentage for each of `techs` against the identical
    admission for `benchmark`, read from Completed_Requests. Fails loudly
    (file and key named) on a missing row or a blank cell."""
    completed = {}
    for t in techs:
        row = bench_row(df, benchmark, t, arch)
        if row is None:
            raise ValueError(
                f"processed_bar_chart_metrics.csv: no row for "
                f"Technology={t!r}, Architecture={arch!r}, Benchmark={benchmark!r}"
            )
        v = row.get('Completed_Requests')
        if v is None or pd.isna(v):
            raise ValueError(
                f"processed_bar_chart_metrics.csv: missing Completed_Requests for "
                f"Technology={t!r}, Architecture={arch!r}, Benchmark={benchmark!r}"
            )
        completed[t] = v

    total_admitted = max(completed.values())
    if total_admitted <= 0:
        raise ValueError(
            f"processed_bar_chart_metrics.csv: Completed_Requests for "
            f"Benchmark={benchmark!r} are all zero across {techs}"
        )
    return {t: 100.0 * completed[t] / total_admitted for t in techs}


def _endurance_write_rates(technology='1T1R_SLC', arch='full_dimm'):
    """Writes/second for the three sustained gem5 workloads, read from each
    benchmark's own stats file: totalWriteRequests divided by that same
    file's own elapsed time (its 'Exiting at cycle' line). The three AI
    traces are microsecond bursts whose rate depends on the denominator
    chosen, so they are not offered here (Project_Book.typ Table 5 note)."""
    benchmarks = {'GCC': 'gcc_spec2017', 'LBM': 'lbm_spec2017', 'STREAM': 'stream'}
    rates = {}
    for label, benchmark in benchmarks.items():
        path = _stats_path(technology, arch, benchmark)
        with open(path) as f:
            content = f.read()
        rates[label] = (_extract_total_write_requests(content, path)
                        / _extract_elapsed_seconds(content, path))
    return rates


# ============================================================================
# 1. LATENCY - GCC, the modeled array against DDR5
# ============================================================================

def slide_latency_gcc(df):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC']
    vals = [value(df, 'gcc_spec2017', t, 'Latency_ns') for t in techs]

    fig, ax = plt.subplots(figsize=(10, 6.5))
    _bar_with_labels(ax, range(len(techs)), vals, _colors(techs), fmt='{:.1f} ns')
    ax.axhline(vals[0], color=TECH_COLORS['DDR5_4800'], linestyle=':', linewidth=2, alpha=0.7)
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels(_labels(techs))
    ax.set_ylabel('Average total latency (ns)')
    ax.set_title('Compute-bound GCC: the modeled array reads below DDR5')
    ax.set_ylim(0, max(vals) * 1.22)
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "01_latency_gcc.png",
          footnote="NVSim-projected device timings, 2048 x 2048 subarrays at mux 64, 250 ms matched window. "
                   "Every configuration completes the identical request population.")


# ============================================================================
# 2. THE PUBLISHED-SILICON COUNTERWEIGHT
# ============================================================================

def slide_silicon_counterweight(df):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC', '1T1R_SILICON', '1S1R_SILICON']
    lat = [value(df, 'gcc_spec2017', t, 'Latency_ns') for t in techs]
    comp = _lbm_completion_pct(df, techs)

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(16, 6.5))

    bars = axL.bar(range(len(techs)), lat, color=_colors(techs),
                   edgecolor='black', linewidth=2.0, alpha=0.9)
    for bar, v in zip(bars, lat):
        label = f'{v:,.0f} ns' if v >= 1000 else f'{v:.1f} ns'
        axL.text(bar.get_x() + bar.get_width() / 2., bar.get_height(), label,
                 ha='center', va='bottom', fontweight='bold')
    axL.set_yscale('log')
    axL.set_xticks(range(len(techs)))
    axL.set_xticklabels(_labels(techs), rotation=18, ha='right')
    axL.set_ylabel('Average total latency (ns), log scale')
    axL.set_title('GCC: projected timings against published silicon')
    axL.grid(axis='y', which='both', alpha=0.3)

    cvals = [comp[t] for t in techs]
    _bar_with_labels(axR, range(len(techs)), cvals, _colors(techs), fmt='{:.1f}%')
    axR.set_xticks(range(len(techs)))
    axR.set_xticklabels(_labels(techs), rotation=18, ha='right')
    axR.set_ylabel('% of the identical LBM admission')
    axR.set_title('LBM: does it keep up at all?')
    axR.set_ylim(0, 118)
    axR.grid(axis='y', alpha=0.3)

    c = CITED_CONSTANTS
    fig.suptitle('The projected array core is fast. Nothing fabricated is.',
                 fontsize=18, fontweight='bold')
    _save(fig, "02_silicon_counterweight.png",
          footnote="SILICON rows replay the identical traces through the identical module geometry at published "
                   f"fabricated-chip timings: Micron/Sony 27nm 16 Gb 1T1R ({c['micron_1t1r_read_us']} us read / "
                   f"{c['micron_1t1r_write_us']} us write, Zahurak IEDM 2014) and SanDisk/Toshiba 24nm 32 Gb 1S1R "
                   f"({c['sandisk_1s1r_read_us']:.0f} us / {c['sandisk_1s1r_write_us']:.0f} us, Liu JSSC 2014).")


# ============================================================================
# 3. SUSTAINED STREAMING - completion is no longer a ReRAM problem
# ============================================================================

def slide_streaming_completion(df):
    lat_techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC']
    comp_techs = lat_techs + ['pcm_microsoft_2009', '1T1R_SILICON', '1S1R_SILICON']

    lbm = [value(df, 'lbm_spec2017', t, 'Latency_ns') for t in lat_techs]
    stream = [value(df, 'stream', t, 'Latency_ns') for t in lat_techs]
    comp = _lbm_completion_pct(df, comp_techs)

    x = np.arange(len(lat_techs))
    width = 0.36
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(16.5, 6.5))

    b1 = axL.bar(x - width / 2, lbm, width, label='LBM', color='#2E7D32',
                 edgecolor='black', linewidth=1.4)
    b2 = axL.bar(x + width / 2, stream, width, label='STREAM', color='#8BC34A',
                 edgecolor='black', linewidth=1.4)
    for bars in (b1, b2):
        for bar in bars:
            axL.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                     f'{bar.get_height():.1f}', ha='center', va='bottom',
                     fontsize=11, fontweight='bold')
    axL.set_xticks(x)
    axL.set_xticklabels(_labels(lat_techs), rotation=15, ha='right')
    axL.set_ylabel('Average total latency (ns)')
    axL.set_title('Sustained streaming: latency')
    axL.legend()
    axL.grid(axis='y', alpha=0.3)

    cvals = [comp[t] for t in comp_techs]
    bars = axR.bar(range(len(comp_techs)), cvals, color=_colors(comp_techs),
                   edgecolor='black', linewidth=2.0, alpha=0.9)
    for bar, v in zip(bars, cvals):
        axR.text(bar.get_x() + bar.get_width() / 2., bar.get_height() + 2,
                 f'{v:.1f}%', ha='center', va='bottom', fontsize=10,
                 fontweight='bold')
    axR.set_xticks(range(len(comp_techs)))
    axR.set_xticklabels(_labels(comp_techs), rotation=28, ha='right', fontsize=11)
    axR.set_ylabel('% of the identical LBM admission')
    axR.set_title('LBM completion, same 250 ms window')
    axR.set_ylim(0, 132)
    axR.grid(axis='y', alpha=0.3)

    fig.suptitle('Every projected ReRAM track now completes the whole window',
                 fontsize=18, fontweight='bold')
    _save(fig, "03_streaming_completion.png",
          footnote="The completion shortfall earlier versions reported for ReRAM was an artifact of a fourfold-duplicated "
                   "trace replayed inside LBM's start-up burst. What is service-limited now is the legacy PCM baseline "
                   "and the two published-silicon configurations.")


# ============================================================================
# 4. AI READ BURST - queue-bound, not device-bound
# ============================================================================

def slide_ai_burst_queue_bound(df):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC']
    total = [value(df, 'gpt2_ifmap', t, 'Latency_ns') for t in techs]
    e2e_us = [value(df, 'gpt2_ifmap', t, 'E2E_Latency_ns') / 1000.0 for t in techs]

    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 6.5))

    _bar_with_labels(axL, range(len(techs)), total, _colors(techs), fmt='{:.1f} ns')
    axL.set_xticks(range(len(techs)))
    axL.set_xticklabels(_labels(techs))
    axL.set_ylabel('Average total latency (ns)')
    axL.set_title('In the controller: queue entry to completion')
    axL.set_ylim(0, max(total) * 1.22)
    axL.grid(axis='y', alpha=0.3)

    _bar_with_labels(axR, range(len(techs)), e2e_us, _colors(techs), fmt='{:,.1f} us')
    axR.set_xticks(range(len(techs)))
    axR.set_xticklabels(_labels(techs))
    axR.set_ylabel('Average end-to-end latency (us)')
    axR.set_title('End to end: trace arrival to completion')
    axR.set_ylim(0, max(e2e_us) * 1.22)
    axR.grid(axis='y', alpha=0.3)

    records = trace_records('gpt2_ifmap')
    span_us = trace_span_us('gpt2_ifmap')
    fig.suptitle('GPT-2 read burst: ReRAM is ahead, and every technology is queue-bound',
                 fontsize=18, fontweight='bold')
    _save(fig, "04_ai_burst_queue_bound.png",
          footnote=f"GPT-2 IFMAP is a {span_us:.1f} us burst of {records:,} reads, so what these three measure is how "
                   "fast the controller queue drains, not how fast the array reads. The original GPT-2 SCALE-Sim "
                   "run's configuration was not preserved, so this trace stands as a representative parallel-read "
                   "pattern, not a validated capture.")


# ============================================================================
# 5. THE WRITE-DOMINATED BURST - the one regime ReRAM loses
# ============================================================================

def slide_write_burst_penalty(df):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC']
    ifmap = [value(df, 'alexnet_layer1_ifmap', t, 'Latency_ns') for t in techs]
    ofmap = [value(df, 'alexnet_layer1_ofmap', t, 'Latency_ns') for t in techs]

    x = np.arange(len(techs))
    width = 0.36
    fig, ax = plt.subplots(figsize=(12, 6.8))
    b1 = ax.bar(x - width / 2, ifmap, width, label='AlexNet IFMAP (pure read)',
                color='#00838F', edgecolor='black', linewidth=1.4)
    b2 = ax.bar(x + width / 2, ofmap, width, label='AlexNet OFMAP (pure write)',
                color='#E64A19', edgecolor='black', linewidth=1.4)
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                    f'{bar.get_height():.0f}', ha='center', va='bottom',
                    fontsize=11, fontweight='bold')
    # The degradation factor sits just above each pair's taller bar, so it
    # can never land underneath the legend the way a fixed height would.
    for i, (r, w) in enumerate(zip(ifmap, ofmap)):
        ax.text(i, max(r, w) * 1.10, f'{w / r:.1f}x', ha='center', va='bottom',
                fontsize=14, fontweight='bold', color='#B71C1C')
    ax.set_xticks(x)
    ax.set_xticklabels(_labels(techs))
    ax.set_ylabel('Average total latency (ns)')
    ax.set_title('Write-dominated burst: the one regime ReRAM loses to DDR5')
    ax.set_ylim(0, max(ifmap + ofmap) * 1.28)
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "05_write_burst_penalty.png",
          footnote="The factor above each pair is the write-side degradation, OFMAP over IFMAP. DRAM reads and writes "
                   "at nearly the same cost; a resistive cell does not, and a dense write stream leaves the banks "
                   "busy. Two bounds point opposite ways: the ReRAM side is a LOWER bound on the deficit, because "
                   "this project's generator leaves the cell write pulse off the request path, while the DDR5 side "
                   "now carries JEDEC write recovery and write latency rather than DDR3-template cycle counts.")


# ============================================================================
# 6. MATCHED ORGANIZATION - the leakage gap was an organization artifact
# ============================================================================

def slide_matched_organization(hw_2048, hw_1024):
    cells = [('reram_22nm_1t1r_slc', 'reram_22nm_1t1r_1024_slc', '1T1R'),
             ('reram_22nm_selector_slc', 'reram_22nm_selector_1024_slc', '1S1R')]

    def pick(hw, key, field, source):
        if key not in hw:
            raise ValueError(f"{source}: no hardware entry {key!r}")
        if field not in hw[key]:
            raise ValueError(f"{source}: entry {key!r} has no {field!r}")
        return hw[key][field]

    leak_2048 = [pick(hw_2048, k, 'leakage_mw', 'primary hardware_metrics.json') for k, _, _ in cells]
    leak_1024 = [pick(hw_1024, k, 'leakage_mw', 'org1024 hardware_metrics.json') for _, k, _ in cells]
    area = [pick(hw_2048, k, 'area_mm2', 'primary hardware_metrics.json') for k, _, _ in cells]
    names = [n for _, _, n in cells]

    x = np.arange(len(names))
    width = 0.36
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 6.5))

    b1 = axL.bar(x - width / 2, leak_2048, width, label='2048 x 2048 (primary)',
                 color='#1565C0', edgecolor='black', linewidth=1.4)
    b2 = axL.bar(x + width / 2, leak_1024, width, label='1024 x 1024 (sensitivity)',
                 color='#90CAF9', edgecolor='black', linewidth=1.4)
    for bars in (b1, b2):
        for bar in bars:
            axL.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                     f'{bar.get_height():.1f}', ha='center', va='bottom',
                     fontsize=12, fontweight='bold')
    axL.set_xticks(x)
    axL.set_xticklabels(names)
    axL.set_ylabel('Peripheral leakage (mW per 1 Gb chip)')
    axL.set_title('At a matched organization, both cells leak the same')
    axL.set_ylim(0, max(leak_1024) * 1.25)
    axL.legend()
    axL.grid(axis='y', alpha=0.3)

    _bar_with_labels(axR, x, area, _colors(['1T1R_SLC', '1S1R_SLC']), fmt='{:.3f}')
    axR.set_xticks(x)
    axR.set_xticklabels(names)
    axR.set_ylabel('Die area (mm2 per 1 Gb chip)')
    axR.set_title(f'What the selector still buys: a {area[0] / area[1]:.1f}x smaller die')
    axR.set_ylim(0, max(area) * 1.22)
    axR.grid(axis='y', alpha=0.3)

    _save(fig, "06_matched_organization.png",
          footnote="NVSim assigns memristor cells no leakage at all, so chip leakage is peripheral circuitry and follows "
                   "mat count, not access-device type. Four times the mats at 1024 x 1024 is twice the sense amplifiers "
                   "and about twice the leakage, for both cells alike.")


# ============================================================================
# 7. POWER PER GIGABYTE
# ============================================================================

def slide_power_per_gib(df, benchmark='gcc_spec2017'):
    techs = ['DDR5_4800', 'pcm_microsoft_2009', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC']
    caps = {t: module_capacity_gib(t, benchmark=benchmark) for t in techs}
    per_gib = [value(df, benchmark, t, 'Power') / caps[t] for t in techs]
    ddr5 = per_gib[0]

    fig, ax = plt.subplots(figsize=(12, 6.8))
    bars = ax.bar(range(len(techs)), per_gib, color=_colors(techs),
                  edgecolor='black', linewidth=2.0, alpha=0.9)
    for i, (bar, v) in enumerate(zip(bars, per_gib)):
        ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                f'{v:.4f} W/GiB\n({v / ddr5:.1f}x)', ha='center', va='bottom',
                fontsize=11, fontweight='bold')
    ax.set_yscale('log')
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels([f'{TECH_LABELS[t]}\n{caps[t]:.0f} GiB' for t in techs],
                       rotation=12, ha='center', fontsize=12)
    ax.set_ylabel('Module power per gigabyte (W/GiB), log scale')
    ax.set_title('Power per gigabyte: the central negative result')
    ax.grid(axis='y', which='both', alpha=0.3)
    ax.set_ylim(min(per_gib) * 0.4, max(per_gib) * 4.0)
    breakeven = breakeven_gating_fraction(df, benchmark=benchmark)
    _save(fig, "07_power_per_gib.png",
          footnote="Module sums divided by each module's own simulated capacity, which is the only form in which these "
                   "technologies compare. Both sides count MEMORY DEVICES ONLY: no register clock driver, "
                   "power-management IC, PHY, termination or ReRAM-side controller, so a fixed per-module overhead "
                   "would compress this ratio while moving the gating break-even the other way. An UPPER BOUND on the "
                   "gap: DDR5 realizes its JEDEC power-down credit while ReRAM's power-down energy is a disclosed "
                   f"no-savings placeholder. Break-even needs {breakeven:.1%} of the static component gated.")


# ============================================================================
# 8. EFFICIENCY PER GIGABYTE (geometric-mean PDP)
# ============================================================================

def slide_pdp_per_gib(geomeans, df):
    techs = ['DDR5_4800', 'pcm_microsoft_2009', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC']
    missing = [t for t in techs if t not in geomeans]
    if missing:
        raise ValueError(f"processed_geometric_means.csv: missing technologies {missing}")
    caps = {t: module_capacity_gib(t) for t in techs}
    per_gib = {t: geomeans[t] / caps[t] for t in techs}
    ratios = [per_gib[t] / per_gib['DDR5_4800'] for t in techs]

    fig, ax = plt.subplots(figsize=(12, 6.8))
    _bar_with_labels(ax, range(len(techs)), ratios, _colors(techs), fmt='{:.1f}x')
    ax.axhline(1.0, color='gray', linestyle=':', linewidth=1.8)
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels([f'{TECH_LABELS[t]}\n{caps[t]:.0f} GiB' for t in techs],
                       rotation=12, ha='center', fontsize=12)
    ax.set_ylabel('Geo-mean PDP per GiB (x DDR5), lower is better')
    ax.set_title('Efficiency per gigabyte: the ReRAM tracks land within 2x of each other')
    ax.set_ylim(0, max(ratios) * 1.2)
    ax.grid(axis='y', alpha=0.3)
    pcm_lbm = completion_pct(df, techs, 'lbm_spec2017')['pcm_microsoft_2009']
    pcm_stream = completion_pct(df, techs, 'stream')['pcm_microsoft_2009']
    _save(fig, "08_pdp_per_gib.png",
          footnote="Six-workload geometric mean of module power x average latency, divided by each module's own "
                   "capacity. The legacy PCM bar averages a completed prefix on two of its six workloads "
                   f"({pcm_lbm:.1f}% of LBM, {pcm_stream:.1f}% of STREAM), so it is a lower bound on the full-window "
                   "cost, not a win.")


# ============================================================================
# 9. CHIP-COUNT SCALING (Pareto, all four architectures)
# ============================================================================

def slide_scaling_pareto_gcc(pareto_df, hw):
    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC']
    markers = {'DDR5_4800': '*', '1T1R_SLC': 'o', '1S1R_SLC': 's'}
    sizes = {'single': 180, '8chip': 340, '16chip': 540, 'full_dimm': 850}
    arch_order = ['single', '8chip', '16chip', 'full_dimm']

    fig, ax = plt.subplots(figsize=(11, 7.5))
    bdf = pareto_df[pareto_df['Benchmark'] == 'gcc_spec2017']
    if bdf.empty:
        raise ValueError("processed_pareto_metrics.csv: no gcc_spec2017 rows")

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
            ax.plot(xs, ys, color=TECH_COLORS[tech], linestyle='--', linewidth=2,
                    alpha=0.6, zorder=2)

    ax.set_yscale('log')
    ax.set_xlabel('Average total latency (ns)')
    ax.set_ylabel('Total module power (W), log scale')
    ax.set_title('Chip-count scaling under GCC: power climbs, latency barely moves')
    ax.grid(True, alpha=0.3, linestyle='--')

    legend_elements = [Line2D([0], [0], marker=markers[t], color='w',
                              markerfacecolor=TECH_COLORS[t], markersize=13,
                              label=TECH_LABELS[t], markeredgecolor='black') for t in techs]
    legend_elements += [Line2D([0], [0], color='none', label=''),
                        Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
                               markersize=9,
                               label='1 chip to 8, 16, 64 chips (small to large)')]
    ax.legend(handles=legend_elements, loc='best', framealpha=0.95)
    leak_mw = hw['reram_22nm_1t1r_slc']['leakage_mw']
    _save(fig, "09_scaling_pareto_gcc.png",
          footnote="All four architectures plotted. The one-chip point is a non-physical decode and carries no "
                   f"conclusion. Static power is exactly 1, 8, 16 and 64 times {leak_mw} mW per chip.")


# ============================================================================
# 10. THE CHANNEL CONTROL RUN
# ============================================================================

def slide_channel_control(primary_df, one_channel_df):
    archs = ['8chip', '16chip', 'full_dimm']
    arch_labels = ['8 chips\n(1 rank)', '16 chips\n(2 ranks)', '64 chips\n(8 ranks)']
    benchmarks = ['gpt2_ifmap', 'alexnet_layer1_ifmap']

    fig, axes = plt.subplots(1, 2, figsize=(15.5, 6.8), sharey=True)
    x = np.arange(len(archs))
    width = 0.36

    for ax, bench in zip(axes, benchmarks):
        one = [value(one_channel_df, bench, '1T1R_SLC', 'Latency_ns', arch=arch,
                     source=sensitivity_csv_path('channels1_ai')) for arch in archs]
        two = [value(primary_df, bench, '1T1R_SLC', 'Latency_ns', arch=arch) for arch in archs]
        # The 8-chip module has a single rank, so channels cannot be formed by
        # splitting ranks and it is single-channel in BOTH runs. Labelling the
        # second series "2 channels" would therefore be wrong on that pair,
        # which is exactly why those two bars are identical.
        b1 = ax.bar(x - width / 2, one, width, label='one-channel control run',
                    color='#B0BEC5', edgecolor='black', linewidth=1.4)
        b2 = ax.bar(x + width / 2, two, width, label='primary configuration',
                    color='#3FA845', edgecolor='black', linewidth=1.4)
        for bars in (b1, b2):
            for bar in bars:
                ax.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                        f'{bar.get_height():.1f}', ha='center', va='bottom',
                        fontsize=11, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(arch_labels)
        ax.set_title(BENCH_LABELS[bench])
        ax.grid(axis='y', alpha=0.3)
        ax.set_ylim(0, max(one + two) * 1.38)

    axes[0].set_ylabel('Average total latency (ns), 1T1R SLC')
    axes[0].legend(loc='upper center', ncol=2)
    dev = [value(primary_df, b, '1T1R_SLC', 'HW_Latency_ns', arch=a)
           for b in benchmarks for a in archs]
    fig.suptitle('Channel count moves burst latency. Rank depth does not.',
                 fontsize=18, fontweight='bold')
    _save(fig, "10_channel_control.png",
          footnote="The 8-chip module has one rank, so it cannot be split into channels and is single-channel in both "
                   "runs: that is why its two bars are identical. At one channel the 16-chip and 64-chip points "
                   "collapse onto it too; in the primary configuration they drop, with the device service term flat "
                   f"at {min(dev):.1f} to {max(dev):.1f} ns throughout. The gain is admission queueing at a second "
                   "controller, not device parallelism.")


# ============================================================================
# 11. INTERFACE CLOCK
# ============================================================================

def slide_interface_clock(primary_df, f1333_df, f2400_df):
    clocks = ['800 MHz\n(baseline)', '1333 MHz', '2400 MHz']
    frames = [(primary_df, 'processed_bar_chart_metrics.csv'),
              (f1333_df, sensitivity_csv_path('freq1333')),
              (f2400_df, sensitivity_csv_path('freq2400'))]

    cpu_techs = ['1T1R_SLC', '1S1R_SLC']
    cpu = {t: [value(d, 'gcc_spec2017', t, 'Latency_ns', source=s) for d, s in frames]
           for t in cpu_techs}
    ddr5 = value(primary_df, 'gcc_spec2017', 'DDR5_4800', 'Latency_ns')
    burst = [value(d, 'alexnet_layer1_ofmap', '1T1R_SLC', 'Latency_ns', source=s)
             for d, s in frames]

    x = np.arange(len(clocks))
    width = 0.36
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15.5, 6.8))

    for i, t in enumerate(cpu_techs):
        bars = axL.bar(x + (i - 0.5) * width, cpu[t], width, label=TECH_LABELS[t],
                       color=TECH_COLORS[t], edgecolor='black', linewidth=1.4)
        for bar in bars:
            axL.text(bar.get_x() + bar.get_width() / 2., bar.get_height(),
                     f'{bar.get_height():.1f}', ha='center', va='bottom',
                     fontsize=11, fontweight='bold')
    axL.axhline(ddr5, color=TECH_COLORS['DDR5_4800'], linestyle='--', linewidth=2)
    # Label at the LEFT end of the rule: at the right end it lands under the
    # legend box and obscures it.
    axL.text(-0.42, ddr5 * 1.03, f'DDR5-4800: {ddr5:.1f} ns',
             ha='left', va='bottom', color=TECH_COLORS['DDR5_4800'], fontsize=12,
             fontweight='bold')
    axL.set_xticks(x)
    axL.set_xticklabels(clocks)
    axL.set_ylabel('Average total latency (ns)')
    axL.set_title('GCC: the interface is a real term')
    axL.set_ylim(0, max(ddr5, max(max(v) for v in cpu.values())) * 1.30)
    axL.legend(loc='upper right')
    axL.grid(axis='y', alpha=0.3)

    _bar_with_labels(axR, x, burst, ['#E64A19'] * len(clocks), fmt='{:.1f} ns')
    axR.set_xticks(x)
    axR.set_xticklabels(clocks)
    axR.set_ylabel('Average total latency (ns), 1T1R SLC')
    axR.set_title('AlexNet write burst: the queue binds, not the bus')
    axR.set_ylim(0, max(burst) * 1.22)
    axR.grid(axis='y', alpha=0.3)

    fig.suptitle(f'Interface clock: {cpu["1T1R_SLC"][0] / cpu["1T1R_SLC"][-1]:.1f}x on the CPU traces, '
                 f'{burst[0] / burst[-1]:.1f}x where the queue binds',
                 fontsize=18, fontweight='bold')
    _save(fig, "11_interface_clock.png",
          footnote="Media, traces and window unchanged; the DDR5 and PCM baselines stay at their own clocks and every "
                   "configuration completes the identical request population at every clock. Interface clock does not "
                   "enter the NVSim leakage figure at all, so this buys latency at no modeled static-power cost.")


# ============================================================================
# 12. QUEUE DEPTH - the two latency measures move in opposite directions
# ============================================================================

def slide_queue_depth(primary_df, q8_df, q128_df):
    depths = ['8', '32\n(primary)', '128']
    frames = [(q8_df, sensitivity_csv_path('queue8')),
              (primary_df, 'processed_bar_chart_metrics.csv'),
              (q128_df, sensitivity_csv_path('queue128'))]

    in_ctrl = [value(d, 'alexnet_layer1_ofmap', '1T1R_SLC', 'Latency_ns', source=s)
               for d, s in frames]
    e2e_us = [value(d, 'alexnet_layer1_ofmap', '1T1R_SLC', 'E2E_Latency_ns', source=s) / 1000.0
              for d, s in frames]

    x = np.arange(len(depths))
    fig, (axL, axR) = plt.subplots(1, 2, figsize=(15, 6.8))

    _bar_with_labels(axL, x, in_ctrl, ['#9E9E9E', '#616161', '#212121'], fmt='{:,.1f} ns')
    axL.set_xticks(x)
    axL.set_xticklabels(depths)
    axL.set_xlabel('Controller queue depth')
    axL.set_ylabel('Average total latency (ns)')
    axL.set_title('In the controller: rises with depth')
    axL.set_ylim(0, max(in_ctrl) * 1.22)
    axL.grid(axis='y', alpha=0.3)

    _bar_with_labels(axR, x, e2e_us, ['#4FC3F7', '#039BE5', '#01579B'], fmt='{:,.0f} us')
    axR.set_xticks(x)
    axR.set_xticklabels(depths)
    axR.set_xlabel('Controller queue depth')
    axR.set_ylabel('Average end-to-end latency (us)')
    axR.set_title('End to end: falls with depth')
    axR.set_ylim(0, max(e2e_us) * 1.22)
    axR.grid(axis='y', alpha=0.3)

    fig.suptitle('AlexNet write burst, 1T1R SLC: the metric that improves with a shallower queue\n'
                 'is the metric measuring the wrong thing',
                 fontsize=17, fontweight='bold')
    _save(fig, "12_queue_depth.png",
          footnote="A short queue reports a fast average over the few requests it admits while the rest of the burst "
                   "backs up outside the controller, where the total-latency counter cannot see it. Completion is "
                   "identical at every depth, and on GCC and LBM depth makes no difference at all.")


# ============================================================================
# 13. DENSITY (characterized at 22nm)
# ============================================================================

def slide_density(hero_df):
    techs = ['DDR5_4800', 'pcm_microsoft_2009', '1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC']
    vals = []
    for t in techs:
        sub = hero_df[hero_df['Technology'] == t]['Area_Density_Ratio']
        if sub.empty:
            raise ValueError(f"processed_hero_metrics.csv: no Area_Density_Ratio for {t!r}")
        vals.append(sub.mean())

    fig, ax = plt.subplots(figsize=(11.5, 6.8))
    _bar_with_labels(ax, range(len(techs)), vals, _colors(techs), fmt='{:.2f}x')
    ax.axhline(1.0, color='gray', linestyle=':', linewidth=1.8)
    ax.set_xticks(range(len(techs)))
    ax.set_xticklabels(_labels(techs), rotation=12, ha='center', fontsize=12)
    ax.set_ylabel('Die-level density (x DDR5), higher is better')
    ax.set_title('Die-level density at the matched organization')
    ax.set_ylim(0, max(vals) * 1.22)
    ax.grid(axis='y', alpha=0.3)
    _save(fig, "13_density.png",
          footnote="NVSim-characterized die area per gigabyte against a commodity DDR5 baseline, at 2048 x 2048 mux 64. "
                   "The 20F2 1T1R cell is a logic-transistor assumption, not a ceiling: a 6F2 recessed-channel part "
                   f"exists (Fackenthal ISSCC 2014) and would lift the 1T1R SLC bar to about "
                   f"{CITED_CONSTANTS['recessed_channel_1t1r_density_x']}x.")


# ============================================================================
# 14. NODE-SCALING PROJECTION (Table 6)
# ============================================================================

def slide_density_projection(hero_df):
    """Reproduces Project_Book.typ Table 6: measured 22nm Area_Density_Ratio
    x (22/F)^2, deck-stack multipliers (x2, x4) applied only to 1S1R."""
    techs = ['1S1R_SLC', '1S1R_MLC', '1T1R_SLC', '1T1R_MLC']
    measured = {}
    for t in techs:
        sub = hero_df[hero_df['Technology'] == t]['Area_Density_Ratio']
        if sub.empty:
            raise ValueError(f"processed_hero_metrics.csv: no Area_Density_Ratio for {t!r}")
        measured[t] = sub.mean()

    nodes = [22, 16, 12]
    projected = {t: [measured[t] * (22 / f) ** 2 for f in nodes] for t in techs}
    deck2 = {t: projected[t][-1] * 2 for t in ('1S1R_SLC', '1S1R_MLC')}
    deck4 = {t: projected[t][-1] * 4 for t in ('1S1R_SLC', '1S1R_MLC')}

    x_labels = ['22nm\n(characterized)', '16nm\n(projected)', '12nm\n(projected)',
                '12nm\n+2 decks', '12nm\n+4 decks']
    x = np.arange(len(x_labels))
    width = 0.2

    fig, ax = plt.subplots(figsize=(13, 7.5))
    for i, t in enumerate(techs):
        ys = list(projected[t])
        ys += [deck2[t], deck4[t]] if t in deck2 else [np.nan, np.nan]
        bars = ax.bar(x + (i - 1.5) * width, ys, width, label=TECH_LABELS[t],
                      color=TECH_COLORS[t], edgecolor='black', linewidth=1.2)
        for bar, v in zip(bars, ys):
            if not np.isnan(v):
                ax.text(bar.get_x() + bar.get_width() / 2., v * 1.01,
                        f'{v:.2f}' if v < 10 else f'{v:.1f}',
                        ha='center', va='bottom', fontsize=9, fontweight='bold',
                        rotation=90)

    ax.axhline(1.0, color='gray', linestyle=':', linewidth=1.8)
    ax.set_xticks(x)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel('Die-level density (x DDR5)')
    ax.set_title('Node scaling and deck stacking: where the density could go')
    ax.legend(loc='upper left')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim(0, max(deck4.values()) * 1.25)

    ax.axvspan(0.5, len(x_labels) - 0.5, color='#FFD700', alpha=0.12, zorder=0)
    ax.text(0.55, 0.97, 'PROJECTED, NOT MEASURED\n(bounding geometry only)',
            transform=ax.transAxes, ha='left', va='top', fontsize=15, fontweight='bold',
            color='#8B6F00', bbox=dict(boxstyle='round', facecolor='#FFF8DC', edgecolor='#8B6F00'))

    _save(fig, "14_density_projection.png",
          footnote="Projection = characterized 22nm ratio x (22/F)^2, DDR5 baseline held fixed; deck rows multiply the "
                   "12nm figure by 2 and 4. 1T1R cannot deck-stack: its access transistor is a front-end-of-line "
                   "device. Selector physics below the 2x-nm regime is unvalidated.")


# ============================================================================
# 15. PROJECTED LIFETIME BY WEAR-LEVELING SCHEME (Table 5)
# ============================================================================

def slide_endurance_projection(endurance_df, write_rates, capacity_gib=64, endurance=1e6):
    schemes = [('NONE', 'No leveling', '#B71C1C'),
               ('START_GAP', 'Start-Gap\n(one whole-module region)', '#EF6C00'),
               ('RANDOMIZED_START_GAP', 'Randomized Start-Gap', '#FBC02D'),
               ('IDEAL', 'Ideal uniform leveling', '#2E7D32')]
    traces = [('gcc_spec2017', 'GCC'), ('lbm_spec2017', 'LBM'), ('stream', 'STREAM')]

    x = np.arange(len(traces))
    width = 0.2
    fig, ax = plt.subplots(figsize=(13, 7.5))

    # Sub-year lifetimes are shown in hours, on the Gregorian mean year
    # (365.2425 days) that Project_Book.typ Table 5 converts with: that is
    # what makes 7.7 h, 23.2 h and 69.5 h come out exactly as the book
    # prints them.
    hours_per_year = 365.2425 * 24

    def fmt_years(v):
        if v >= 0.1:
            return f'{v:.1f} yr' if v >= 1.0 else f'{v:.2f} yr'
        hours = v * hours_per_year
        return f'{hours:.1f} h' if hours >= 1.0 else f'{hours * 60:.1f} min'

    for i, (scheme, label, color) in enumerate(schemes):
        ys = [endurance_value(endurance_df, t, scheme) for t, _ in traces]
        # Where the hottest line fails before the gap completes its first
        # rotation, the model reports a RANGE between the no-leveling value and
        # twice it (Table 5's Start-Gap columns). Plot the lower bound and draw
        # the range as an error bar, so the chart shows the cell the book shows.
        ups = [endurance_value(endurance_df, t, scheme, 'lifetime_upper_years')
               for t, _ in traces]
        err = [u - v for u, v in zip(ups, ys)]
        bars = ax.bar(x + (i - 1.5) * width, ys, width, label=label,
                      color=color, edgecolor='black', linewidth=1.2,
                      yerr=[[0.0] * len(ys), err], capsize=4,
                      error_kw=dict(ecolor='#37474F', lw=1.6))
        for bar, v, u in zip(bars, ys, ups):
            text = fmt_years(v) if u <= v * 1.001 else f'{fmt_years(v)} to {fmt_years(u)}'
            ax.text(bar.get_x() + bar.get_width() / 2., u * 1.20,
                    text, ha='center', va='bottom', fontsize=10,
                    fontweight='bold', rotation=90)

    ax.set_yscale('log')
    ax.axhspan(5, 10, color='green', alpha=0.12, zorder=0)
    ax.text(-0.42, 7.0, '5 to 10 yr\nserver target', ha='left', va='center',
            fontsize=12, color='darkgreen', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels([f'{label}\n{write_rates[label] / 1e6:.2f} M writes/s'
                        for _, label in traces])
    ax.set_ylabel('PROJECTED lifetime (years), log scale')
    ax.set_title('Endurance is decided by the leveling scheme, not by the cell')
    ax.legend(loc='upper left', ncol=2, fontsize=12)
    ax.grid(axis='y', which='both', alpha=0.3)
    top = max(endurance_value(endurance_df, t, 'IDEAL') for t, _ in traces)
    ax.set_ylim(2e-4, top * 300)

    ax.text(0.99, 0.985,
            'PROJECTION from a measured write distribution.\nNo lifetime here was measured.',
            transform=ax.transAxes, ha='right', va='top', fontsize=13, fontweight='bold',
            color='#7B1FA2', bbox=dict(boxstyle='round', facecolor='#F3E5F5', edgecolor='#7B1FA2'))

    _save(fig, "15_endurance_projection.png",
          footnote=f"{capacity_gib} GiB module, 10^{int(round(np.log10(endurance)))} cycles per cell, one write per "
                   "line per request, admitted write rate. A range marks a case where the hottest line fails before "
                   "the gap completes its first rotation. The three AI traces are microsecond bursts rather than "
                   "sustained workloads and are deliberately not plotted. Gap-move traffic is charged as wear here "
                   "but is not issued as traffic in the simulation.")


# ============================================================================
# MAIN
# ============================================================================

def main():
    global OUTPUT_DIR, DATA_DIR, CSV_DIR, SENS_ROOT, ENDURANCE_CSV, SIDECAR_DIR
    global HARDWARE_METRICS_FILE

    parser = argparse.ArgumentParser(description="MBMM slide-deck chart generation")
    parser.add_argument("--data-dir", default=DATA_DIR,
                        help="Directory holding stats_*.out (default: results/system_rev2026-09_primary).")
    parser.add_argument("--csv-dir", default=CSV_DIR,
                        help="Directory holding processed_*.csv and hardware_metrics.json "
                             "(default: results/rev2026-09_primary_csv).")
    parser.add_argument("--sens-root", default=SENS_ROOT,
                        help="Directory holding the system_rev2026-09_<axis>/ sensitivity runs "
                             "(default: results/).")
    parser.add_argument("--endurance-csv", default=ENDURANCE_CSV,
                        help="Endurance projection table (default: results/endurance_table.csv).")
    parser.add_argument("--sidecar-dir", default=SIDECAR_DIR,
                        help="Directory holding <trace>.nvt.sidecar.json (default: benchmarks/).")
    parser.add_argument("--output-dir", default=OUTPUT_DIR,
                        help="Output directory for slide PNGs "
                             "(default: results/slide_graphs_rev2026-09, never final_graphs*).")
    args = parser.parse_args()
    DATA_DIR = args.data_dir
    CSV_DIR = args.csv_dir
    SENS_ROOT = args.sens_root
    ENDURANCE_CSV = args.endurance_csv
    SIDECAR_DIR = args.sidecar_dir
    OUTPUT_DIR = args.output_dir
    HARDWARE_METRICS_FILE = os.path.join(CSV_DIR, "hardware_metrics.json")

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logger.info(f"Reading stats from:      {DATA_DIR}")
    logger.info(f"Reading CSVs from:       {CSV_DIR}")
    logger.info(f"Reading sensitivities:   {SENS_ROOT}/system_rev2026-09_<axis>/_csv")
    logger.info(f"Reading endurance table: {ENDURANCE_CSV}")
    logger.info(f"Reading trace sidecars:  {SIDECAR_DIR}")
    logger.info(f"Writing slides to:       {OUTPUT_DIR}\n")

    bar_df = load_bar_chart_metrics()
    hero_df = filter_primary_technologies(load_hero_metrics())
    geomeans = load_geometric_means()
    pareto_df = filter_primary_technologies(
        _read_csv(os.path.join(CSV_DIR, "processed_pareto_metrics.csv")))
    hw_2048 = load_hardware_metrics()
    hw_1024 = load_hardware_metrics(sensitivity_csv_path('org1024', 'hardware_metrics.json'))

    ch1_df = load_sensitivity_bar_chart('channels1_ai')
    f1333_df = load_sensitivity_bar_chart('freq1333')
    f2400_df = load_sensitivity_bar_chart('freq2400')
    q8_df = load_sensitivity_bar_chart('queue8')
    q128_df = load_sensitivity_bar_chart('queue128')

    endurance_df = load_endurance_projection()
    write_rates = _endurance_write_rates()

    slide_latency_gcc(bar_df)
    slide_silicon_counterweight(bar_df)
    slide_streaming_completion(bar_df)
    slide_ai_burst_queue_bound(bar_df)
    slide_write_burst_penalty(bar_df)
    slide_matched_organization(hw_2048, hw_1024)
    slide_power_per_gib(bar_df)
    slide_pdp_per_gib(geomeans, bar_df)
    slide_scaling_pareto_gcc(pareto_df, hw_2048)
    slide_channel_control(bar_df, ch1_df)
    slide_interface_clock(bar_df, f1333_df, f2400_df)
    slide_queue_depth(bar_df, q8_df, q128_df)
    slide_density(hero_df)
    slide_density_projection(hero_df)
    slide_endurance_projection(endurance_df, write_rates)

    logger.info("\nSLIDE CHART GENERATION COMPLETE\n")
    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
