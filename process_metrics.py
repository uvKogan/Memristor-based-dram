#!/usr/bin/env python3
"""
MBMM Pipeline - Data Processing Stage
Process raw simulation metrics and output pre-calculated intermediate data

This module:
- Parses all stats_*.out files from /results/system/
- Performs centralized metric calculations (EDP, power splits, area density)
- Outputs pre-calculated CSV files for visualization stages
- Single source of truth for all mathematical operations
"""

import re
import glob
import json
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from logging_config import setup_logging

logger = setup_logging("process_metrics")

# ============================================================================
# CONFIGURATION: Physical Constants and Baseline Values
# ============================================================================

# Overridable via --results-dir/--output-dir (see main()) so isolated pilot/
# validation runs can target a separate directory (e.g. results/system_v2)
# without touching the documented-ground-truth results/system/ and
# results/processed_*.csv. Defaults are unchanged from the original pipeline.
RESULTS_SYS_DIR = "/home/yuvalk/MBMM/results/system"
OUTPUT_DIR = "/home/yuvalk/MBMM/results"
HARDWARE_METRICS_FILE = "/home/yuvalk/MBMM/results/hardware_metrics.json"


def _load_hardware_metrics(path):
    """Load hardware_metrics.json from `path`. Returns {} (with a WARNING logged) if the
    file is missing or fails to parse.

    T5.1 step 2 fix round 1: factored out of the module-level load below so main() can
    reload HARDWARE_METRICS against a different file via --hardware-metrics (e.g. an
    isolated sensitivity run's own hardware_metrics.json copy, which carries the _1024
    entries the live results/hardware_metrics.json may or may not still have) instead of
    always reading the shared, live default.

    I5 (final review 2026-09): returning {} here is NOT a silent degradation any
    more. The WARNING the docstring always promised is now actually logged (a
    missing file used to return {} with no log line at all), and a ReRAM row
    that needs an entry out of this dict raises in _reram_json_entry() rather
    than falling back to an area-density ratio of 1.0 ("DDR5 parity"). DDR5 and
    PCM rows never read this file, so a run that processes only those still
    works with an empty dict, as before.
    """
    metrics = {}
    try:
        if Path(path).exists():
            with open(path, 'r') as f:
                metrics = json.load(f)
                logger.debug(f"Loaded hardware metrics for {len(metrics)} technologies from {path}")
        else:
            logger.warning(
                f"hardware_metrics.json not found at {path}: no ReRAM area/capacity is "
                f"available. DDR5 and PCM rows are unaffected; any ReRAM row will fail "
                f"loudly rather than fall back to a density ratio of 1.0.")
    except Exception as e:
        logger.warning(f"Could not load hardware metrics from {path}: {e}")
    return metrics


# Load hardware metrics (area, capacity) from extraction stage
HARDWARE_METRICS = _load_hardware_metrics(HARDWARE_METRICS_FILE)


# ============================================================================
# RUN PROVENANCE (I6, final review 2026-09)
# ============================================================================
#
# mbmm_master.py writes a run_manifest.json next to the stats files it is about
# to produce (results/system/run_manifest.json), at the start of Stage 4. Until
# that existed, nothing in a stats filename or in a processed CSV said which
# flags produced it: the only thing separating a sensitivity dataset from the
# primary was the directory name someone typed. These columns carry the manifest's
# key flags into every row, so a CSV can be read on its own.
#
# The column -> manifest-flag mapping. Order is the column order appended to the
# CSVs (last, after every pre-existing column, so readers that index by name
# keep working).
RUN_PROVENANCE_COLUMNS = (
    ("Run_Channels", "channels"),
    ("Run_Decoder", "decoder"),
    ("Run_Organization", "organization"),
    ("Run_Queue_Size", "queue_size"),
    ("Run_Freq_MHz", "freq_mhz"),
    ("Run_Window_ns", "window_ns"),
    ("Run_DDR5_Model", "ddr5_model"),
)

# What a column holds when no manifest is present. The ten frozen 2026-09
# datasets predate the manifest and must NOT have one fabricated for them.
RUN_PROVENANCE_UNKNOWN = "unknown"

# The Run_* column names alone, in order, for the CSV writers.
RUN_PROVENANCE_COLUMN_NAMES = [name for name, _ in RUN_PROVENANCE_COLUMNS]

RUN_MANIFEST_NAME = "run_manifest.json"

# The manifest key listing the stats filenames THIS run is expected to produce.
# F2 fix round 1 (review Important-1): results/system is not cleared between
# master runs, so a second run with different flags could leave a folder holding
# both runs' stats files and only the second run's manifest. Without this list a
# manifest describes "whatever is in the folder", and the older files would be
# stamped with the newer run's Run_* values. With it, a manifest describes an
# explicit set of files and nothing else.
RUN_MANIFEST_STATS_KEY = "expected_stats_files"


def load_run_manifest(results_dir):
    """Read `results_dir`/run_manifest.json, or return None with a WARNING.

    Returns the parsed manifest dict, or None when the file is absent or
    unreadable. A missing manifest is expected for the frozen datasets (they
    were produced before mbmm_master.py wrote one) and must never be invented:
    the Run_* columns are then written as "unknown".
    """
    path = Path(results_dir) / RUN_MANIFEST_NAME
    if not path.exists():
        logger.warning(
            f"No {RUN_MANIFEST_NAME} in {results_dir}: the Run_* provenance columns "
            f"will be written as {RUN_PROVENANCE_UNKNOWN!r}. This is expected for a "
            f"dataset produced before mbmm_master.py wrote a run manifest; for a fresh "
            f"run it means Stage 4 did not write one.")
        return None
    try:
        with open(path, 'r') as f:
            manifest = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read {path}: {e}; Run_* columns will be "
                       f"{RUN_PROVENANCE_UNKNOWN!r}.")
        return None
    logger.info(f"Loaded run manifest {path} (date {manifest.get('date', '?')})")
    return manifest


def run_provenance_fields(manifest):
    """{column: value} for every Run_* column, from `manifest` (None -> all unknown)."""
    flags = (manifest or {}).get("flags", {})
    fields = {}
    for column, flag in RUN_PROVENANCE_COLUMNS:
        value = flags.get(flag) if manifest else None
        if value is None:
            value = RUN_PROVENANCE_UNKNOWN
        fields[column] = value
    return fields


def unknown_run_provenance_fields():
    """{column: 'unknown'} for every Run_* column."""
    return {name: RUN_PROVENANCE_UNKNOWN for name in RUN_PROVENANCE_COLUMN_NAMES}


def manifest_stats_files(manifest):
    """The set of stats filenames `manifest` claims to describe.

    Returns None when the manifest carries no list at all, which is how a
    manifest written before F2 fix round 1 is recognised. Such a manifest is
    treated as covering NOTHING (see make_run_provenance_resolver): it cannot
    say which of the files beside it are its own, and guessing is exactly the
    mislabelling this list exists to prevent.
    """
    if not manifest:
        return None
    files = manifest.get(RUN_MANIFEST_STATS_KEY)
    if files is None:
        return None
    return set(files)


def make_run_provenance_resolver(manifest, results_dir=None):
    """Return f(stats_filename) -> {Run_* column: value}.

    A stats file gets the manifest's flags only if the manifest lists it. Any
    other stats file in the same directory gets "unknown" in every column and a
    WARNING naming it, because results/system is not cleared between runs and a
    file that this manifest does not claim may well have been simulated with
    different flags (F2 fix round 1, review Important-1).
    """
    unknown = unknown_run_provenance_fields()
    where = f" in {results_dir}" if results_dir else ""

    if manifest is None:
        # load_run_manifest already logged why.
        return lambda filename: dict(unknown)

    covered = manifest_stats_files(manifest)
    if covered is None:
        logger.warning(
            f"The {RUN_MANIFEST_NAME}{where} carries no {RUN_MANIFEST_STATS_KEY!r} "
            f"list, so it cannot say which stats files beside it are its own. "
            f"Treating it as covering nothing: every Run_* column is "
            f"{RUN_PROVENANCE_UNKNOWN!r}. Re-run the master to get a manifest that "
            f"lists its own outputs.")
        return lambda filename: dict(unknown)

    fields = run_provenance_fields(manifest)

    def resolve(filename):
        name = Path(filename).name
        if name in covered:
            return dict(fields)
        logger.warning(
            f"{name}{where} is not listed in this run manifest's "
            f"{RUN_MANIFEST_STATS_KEY!r} ({len(covered)} file(s)), so it belongs to "
            f"some other run: its Run_* columns are {RUN_PROVENANCE_UNKNOWN!r}. Each "
            f"results directory should hold exactly one run's stats files.")
        return dict(unknown)

    return resolve

# Area Density Baseline (Hybrid-Empirical Approach)
DDR5_MM2_PER_GB = 35.0  # DDR5-4800 empirical baseline

# Clock frequencies for latency normalization (cycles → nanoseconds)
# DDR5-4800 transfers at 4800 MT/s on a DDR (double-data-rate) bus → 2400 MHz clock
# 2D/3D DRAM examples per their NVMain stats headers ("memory subsystem running
# at 666MHz" / "1333MHz"); all NVMain ReRAM and PCM configs run at 800 MHz
#
# T2.5 fix round 1: this table (and CPUFREQ_MHZ below) is now a FALLBACK
# only, used when a stats file's own clock-diagnostic line is absent (see
# extract_clocks_mhz/resolve_clocks_mhz). It is no longer the primary source
# of truth for any cycles-to-ns conversion: a technology can be simulated at
# more than one CLK (e.g. a ReRAM clock-sensitivity run at CLK 2400 still
# classifies as 1T1R_SLC by filename), and this table cannot know that --
# only the run's own stats file can.
CLOCK_FREQUENCY_MHZ = {
    'DDR5_4800':          2400,
    'DDR5_4800_64B':      2400,  # T2.4 cross-check: same CLK 2400 as the primary baseline
    '2D_DRAM_example':     666,
    '3D_DRAM_example':    1333,
    'pcm_microsoft_2009':  400,  # cycle-7 finding #9: CLK 800 was a stray override;
                                 # PCM's citable timing basis (and the fixed config) is 400MHz
    'PCM':                 400,  # T2.5 fix round 1: mirrors pcm_microsoft_2009 -- classify_technology()
                                 # can also return the generic 'PCM' key (any pcm-named file that
                                 # doesn't match the more specific pcm_microsoft_2009 pattern); without
                                 # this entry that case silently fell through to the 800 default.
    '1T1R_SLC':            800,
    '1T1R_MLC':            800,
    '1S1R_SLC':            800,
    '1S1R_MLC':            800,
    # T2.8: microsecond-silicon sensitivity configs mirror their SLC parent's
    # CLK (both still generated by 3_gen_nvmain_config.py at --freq 800, only
    # timing overridden) -- see resolve_clocks_mhz for why this is a fallback
    # only in practice (the stats file's own diagnostic line always wins).
    '1T1R_SILICON':        800,
    '1S1R_SILICON':        800,
}

# GLOBAL/CPUFreq clock domain (T2.5). NVMain's traceSim/traceMain.cpp sets
# `globalEventQueue->SetFrequency(config->GetEnergy("CPUFreq") * 1000000.0)`
# before the simulation loop (traceMain.cpp ~line 167), so every cycle
# GlobalEventQueue tracks -- including the "Exiting at cycle <n>" value it
# prints at trace exit/drain (traceMain.cpp ~line 305) -- is on the CPUFreq
# domain, NOT the model's own memory-clock (CLK) domain used by
# CLOCK_FREQUENCY_MHZ above. Every stats file's own diagnostic line confirms
# this directly, e.g. "NVMain: GlobalEventQueue: Added a memory subsystem
# running at 800MHz. My frequency is 3000MHz." -- "My frequency" there is
# GlobalEventQueue's own frequency, i.e. CPUFreq. global-constraints.md fixes
# CPUFreq at 3000 MHz for every model, so this is a single constant, not a
# per-technology table.
CPUFREQ_MHZ = 3000


# ============================================================================
# CLOCK RESOLUTION (T2.5 fix round 1)
# ============================================================================

def extract_clocks_mhz(content):
    """
    Parse NVMain's own per-run clock-domain diagnostic line, printed once per
    channel by src/EventQueue.cpp:472-473:

        NVMain: GlobalEventQueue: Added a memory subsystem running at
        <CLK>MHz. My frequency is <CPUFreq>MHz.

    <CLK> is the model's own memory-clock domain for THIS run (the same
    domain averageTotalLatency/averageEndToEndLatency/averageQueueLatency
    are reported in). <CPUFreq> is the GLOBAL event-queue domain the
    "Exiting at cycle <n>" line is printed in (see CPUFREQ_MHZ's comment
    above for the full source-code proof). Reading both from the file itself
    -- rather than from CLOCK_FREQUENCY_MHZ/CPUFREQ_MHZ, which only know a
    technology's *default* clock -- is what makes a clock-sensitivity run
    (e.g. a ReRAM config regenerated at CLK 2400 instead of the usual 800)
    convert cycles to ns correctly: the filename still classifies as
    1T1R_SLC either way, so a table keyed by technology name cannot tell the
    two runs apart, only the run's own stats file can.

    With more than one channel the line is printed once per channel; every
    occurrence must report the same (CLK, CPUFreq) pair -- a single run has
    exactly one CLK and one CPUFreq for the whole DIMM. If any two
    occurrences disagree, this raises ValueError rather than silently
    picking one (a malformed or concatenated stats file should be fixed, not
    guessed at).

    Returns (clk_mhz, cpufreq_mhz), both int. Returns (None, None) if the
    line is absent entirely (e.g. a hand-written test fixture, or a
    truncated/aborted-run file) -- callers must fall back to
    CLOCK_FREQUENCY_MHZ/CPUFREQ_MHZ in that case (see resolve_clocks_mhz,
    which does exactly that with a logged warning); this function itself
    never falls back silently.
    """
    matches = re.findall(
        r'running at\s+(\d+)MHz\.\s*My frequency is\s+(\d+)MHz', content)

    if not matches:
        return None, None

    clk_values = {int(m[0]) for m in matches}
    cpufreq_values = {int(m[1]) for m in matches}

    if len(clk_values) > 1 or len(cpufreq_values) > 1:
        raise ValueError(
            f"extract_clocks_mhz: disagreeing clock-diagnostic lines in the "
            f"same stats file -- CLK values found: {sorted(clk_values)}, "
            f"CPUFreq values found: {sorted(cpufreq_values)}. A single run "
            f"has exactly one CLK and one CPUFreq for the whole DIMM; this "
            f"looks like a malformed or concatenated stats file."
        )

    return clk_values.pop(), cpufreq_values.pop()


def resolve_clocks_mhz(content, technology, filename=""):
    """
    Resolve the (clk_mhz, cpufreq_mhz) pair to use for every cycles-to-ns
    conversion on this stats file, preferring the run's own recorded clocks
    (extract_clocks_mhz) over the CLOCK_FREQUENCY_MHZ/CPUFREQ_MHZ fallback.

    This is the single resolution point every cycles-to-time conversion in
    this file goes through (see calculate_latency_ns, extract_end_to_end_
    latency_ns, and parse_raw_stats' call site, which resolves once per file
    and reuses the result for Total/HW/Queue/E2E latency and for the
    delivered-bandwidth elapsed-time calculation).

    Falls back to CLOCK_FREQUENCY_MHZ[technology] (default 800, matching the
    table's own pre-T2.5 default) and CPUFREQ_MHZ only when the diagnostic
    line is absent entirely -- logged as a WARNING naming the file, since
    this should only happen for a hand-made or truncated stats file, never
    for a real NVMain run. When the line IS present and its CLK disagrees
    with the table's default for this technology, that is the expected,
    intended clock-sensitivity-run case (a technology simulated at a
    non-default CLK): logged at INFO, not a warning, and the file's own
    value always wins.
    """
    clk_mhz, cpufreq_mhz = extract_clocks_mhz(content)

    if clk_mhz is None:
        table_clk = CLOCK_FREQUENCY_MHZ.get(technology, 800)
        logger.warning(
            f"[CLOCK-FALLBACK] {filename}: no 'My frequency is' diagnostic "
            f"line found in this stats file; falling back to "
            f"CLOCK_FREQUENCY_MHZ[{technology}]={table_clk} MHz and "
            f"CPUFREQ_MHZ={CPUFREQ_MHZ} MHz. This should only happen for a "
            f"hand-made or truncated stats file, never a real NVMain run."
        )
        return table_clk, CPUFREQ_MHZ

    table_clk = CLOCK_FREQUENCY_MHZ.get(technology)
    if table_clk is not None and table_clk != clk_mhz:
        logger.info(
            f"[CLOCK-SENSITIVITY] {filename}: this run's own CLK "
            f"({clk_mhz} MHz) differs from CLOCK_FREQUENCY_MHZ[{technology}] "
            f"({table_clk} MHz) -- using the run's own value, as intended. "
            f"Expected for a clock-sensitivity config; unexpected otherwise."
        )

    return clk_mhz, cpufreq_mhz


# ============================================================================
# CLASSIFICATION FUNCTIONS
# ============================================================================

def classify_technology(filename):
    """Classify technology from filename using priority matching."""
    filename_lower = filename.lower()
    
    # Priority order: More specific patterns first. T2.4: the 64B cross-check
    # config is its own technology (DDR5_4800_64B), distinct from the primary
    # baseline (DDR5_4800, which both the legacy DDR5_4800_DRAM name and the
    # new DDR5_4800_DRAM_subchannel name classify to) -- its pattern must be
    # checked before the plain 'ddr5.*4800' pattern, which would otherwise
    # match it first (DDR5_4800_DRAM_64B contains 'ddr5...4800' too).
    patterns = [
        # T2.8: microsecond-silicon sensitivity configs (reram_micron16gb_1t1r_*,
        # reram_sandisk32gb_1s1r_*) contain '1t1r'/'1s1r' but never 'slc'/'mlc'/
        # 'selector', so the existing SLC/MLC patterns below would not actually
        # match them either way -- these are listed first regardless, so that
        # stays true even if a future SLC/MLC pattern is loosened.
        ('1T1R_SILICON', r'reram.*micron16gb.*1t1r'),
        ('1S1R_SILICON', r'reram.*sandisk32gb.*1s1r'),
        ('1T1R_MLC', r'reram.*1t1r.*mlc'),
        ('1T1R_SLC', r'reram.*1t1r.*slc(?!.*mlc)'),
        ('1S1R_MLC', r'reram.*selector.*mlc'),
        ('1S1R_SLC', r'reram.*selector.*slc(?!.*mlc)'),
        ('pcm_microsoft_2009', r'pcm_microsoft_2009'),
        ('PCM', r'pcm'),
        ('DDR5_4800_64B', r'ddr5.*4800.*64b'),
        ('DDR5_4800', r'ddr5.*4800'),
        ('3D_DRAM_example', r'3d_dram'),
        ('2D_DRAM_example', r'2d_dram'),
    ]
    
    for tech_name, pattern in patterns:
        if re.search(pattern, filename_lower):
            return tech_name
    
    logger.warning(f"Unknown technology in filename: {filename}")
    return None


def classify_reram_organization(filename):
    """T5.1 step 2 organization axis: ReRAM subarray organization (2048
    default / 1024 sensitivity) encoded in a stats filename.

    Technology stays 1T1R_SLC/1S1R_SLC/etc for either organization (a
    1024-organization run's Technology label is not distinguished from the
    2048 baseline's -- acceptable per T5.1 step 2's requirement, since each
    sensitivity run is processed into its own results directory/CSV, and
    parse_raw_stats() below refuses to let stats files for both
    organizations coexist in one --results-dir). The filename itself still
    makes the organization explicit: mbmm_master.py's reram_factory_bases()/
    2_extract_hardware_metrics.py's base-key convention puts a literal
    "_1024" token in the ReRAM base name for every 1024 stats file (e.g.
    "stats_reram_22nm_1t1r_1024_slc_full_dimm_<bench>.out"), never for a
    2048 one.

    Returns 1024 or 2048 for a ReRAM stats filename, None for a non-ReRAM
    technology (DDR5/PCM/silicon), which has no organization axis.

    T5.1 step 2 fix round 1 (Important-2): anchored to the model-name convention
    (mbmm_master.reram_factory_bases()/2_extract_hardware_metrics.py's key naming) rather
    than a bare '_1024' substring search over the whole filename
    ("stats_{model}_{trace_name}.out"). The '_1024' token always sits directly between the
    base model name and the '_slc'/'_mlc' track suffix in a 1024 stats file (e.g.
    "stats_reram_22nm_1t1r_1024_slc_full_dimm_<bench>.out"); requiring '_1024_slc' or
    '_1024_mlc' specifically means a trace/benchmark name that happens to contain "1024"
    (e.g. a future "..._matmul_1024.out") cannot be misclassified as organization 1024.
    """
    filename_lower = filename.lower()
    if not re.search(r'reram.*(1t1r|selector)', filename_lower):
        return None
    return 1024 if re.search(r'_1024_(?:slc|mlc)', filename_lower) else 2048


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

    # Default for DRAM/PCM (no architecture suffix). T2.4: both DDR5-4800
    # baseline variants (legacy, subchannel, 64B) are Architecture full_dimm
    # -- they are distinguished from each other by Technology instead (see
    # classify_technology), not by Architecture.
    if any(x in filename_lower for x in ['ddr5', '2d_dram', '3d_dram', 'pcm']):
        return 'full_dimm'

    logger.warning(f"Unknown architecture in filename: {filename}")
    return None


def extract_benchmark(filename):
    """Extract benchmark name from filename."""
    name = filename.replace('stats_', '').replace('.out', '')
    
    # Remove technology/architecture prefixes to isolate benchmark name.
    # T2.4: the two DDR5-4800 baseline variants' longer prefixes must be
    # checked before the plain 'DDR5_4800_DRAM_' prefix (a substring of
    # both), or only their 'subchannel_'/'64B_' tag gets stripped and it
    # ends up misread as part of the benchmark name.
    removal_patterns = [
        'DDR5_4800_DRAM_subchannel_',
        'DDR5_4800_DRAM_64B_',
        'DDR5_4800_DRAM_',
        '2D_DRAM_example_',
        '3D_DRAM_example_',
        'pcm_microsoft_2009_',
    ]
    
    for pattern in removal_patterns:
        if pattern in name:
            return name.replace(pattern, '', 1)
    
    # Handle ReRAM models (reram_22nm_[arch]_[mlc/slc]_[scale]_benchmark), and
    # T2.8's microsecond-silicon sensitivity configs (reram_micron16gb_1t1r_
    # full_dimm_benchmark / reram_sandisk32gb_1s1r_full_dimm_benchmark), which
    # also start with 'reram_' but not 'reram_22nm' -- both strip the same way
    # (find the architecture token, keep everything after it).
    if name.startswith('reram_'):
        for arch in ['full_dimm', '16chip', '8chip', 'single']:
            if arch in name:
                idx = name.find(arch + '_') + len(arch + '_')
                return name[idx:]
    
    return name


# ============================================================================
# METRIC EXTRACTION FUNCTIONS
# ============================================================================

def _extract_latency_stat(content, stat_name):
    """
    Extract a named NVMain latency statistic, averaging across all channels.

    NVMain emits one line per channel: channel0.FRFCFS.<stat_name> <value>
    DDR5-4800 has two sub-channels; single-channel ReRAM/PCM has one.
    Averaging gives a single representative number regardless of channel count.
    """
    pattern = rf'{re.escape(stat_name)}\s+([\d\.eE+\-]+)'
    matches = re.findall(pattern, content, re.IGNORECASE)
    if not matches:
        return None
    try:
        values = [float(m) for m in matches]
        return sum(values) / len(values)
    except ValueError:
        return None


def extract_total_execution_cycles(content):
    """
    Extract averageTotalLatency (hardware latency + queue wait) from stats file.

    This is the correct end-to-end latency seen by a memory request.
    Previously the parser used a broad 'average.*latency' regex which matched
    averageLatency first (hardware-only, no queuing), losing the ISPV write-
    torture signal that lives in the queue component.
    """
    return _extract_latency_stat(content, 'averageTotalLatency')


def extract_hw_latency(content):
    """
    Extract averageLatency (pure hardware timing, no queue wait).

    Useful as a secondary column to decompose total latency into
    hardware vs queue components.
    """
    return _extract_latency_stat(content, 'averageLatency')


def extract_queue_latency(content):
    """
    Extract averageQueueLatency (time spent waiting in the FRFCFS queue).

    For write-heavy workloads (OFMAP), ISPV MLC writes back up the queue,
    causing a massive spike here relative to read-heavy (IFMAP) workloads.
    This is the primary empirical proof of the Write-Torture / ISPV penalty.
    """
    return _extract_latency_stat(content, 'averageQueueLatency')


def extract_end_to_end_latency_ns(content, clk_mhz):
    """
    Extract averageEndToEndLatency (NVMain T1.2 patch), combined across
    channels and converted to nanoseconds.

    NVMain emits one averageEndToEndLatency/measuredEndToEndLatencies pair
    per channel (per controller: channelN.FRFCFS or channelN.FRFCFS-WQF for
    PCM's write-queue controller), in the model's own memory-clock (CLK)
    cycle domain -- the same domain as averageTotalLatency, so it is
    comparable to Latency_ns/HW_Latency_ns/Queue_Latency_ns elsewhere in this
    file. With more than one channel (DDR5's two subchannels) the two
    channels rarely complete the same number of requests, so a plain mean
    across channels would over/under-weight whichever channel measured fewer
    end-to-end latencies; instead this combines the per-channel averages as a
    request-weighted mean, weighted by each channel's own
    measuredEndToEndLatencies count.

    `clk_mhz` must be the run's own memory-clock frequency (see
    resolve_clocks_mhz) -- T2.5 fix round 1: this used to take a `technology`
    string and look up CLOCK_FREQUENCY_MHZ internally, which silently used
    the table's default CLK for a technology even when the actual run used a
    different one (e.g. a clock-sensitivity config); callers now resolve the
    real clock once (per file, via resolve_clocks_mhz) and pass it in here.
    """
    lat_matches = re.findall(r'averageEndToEndLatency\s+([\d\.eE+\-]+)', content)
    cnt_matches = re.findall(r'measuredEndToEndLatencies\s+(\d+)', content)

    if not lat_matches or not cnt_matches or len(lat_matches) != len(cnt_matches):
        return None

    try:
        lats = [float(m) for m in lat_matches]
        counts = [int(m) for m in cnt_matches]
    except ValueError:
        return None

    total_count = sum(counts)
    if total_count <= 0:
        return None

    weighted_cycles = sum(l * c for l, c in zip(lats, counts)) / total_count
    return calculate_latency_ns(weighted_cycles, clk_mhz)


def extract_completed_requests_and_bandwidth(content, cpufreq_mhz=CPUFREQ_MHZ):
    """
    Compute Completed_Requests and delivered bandwidth (MB/s) from NVMain's
    per-channel mem_reads/mem_writes counters and the elapsed simulated time.

    Completed_Requests = sum over channels of (mem_reads + mem_writes) --
    the same per-channel completed-request counts used for bandwidth, not
    NVMain's own totalReadRequests/totalWriteRequests (issued, not
    necessarily completed).

    Delivered_BW_MBps = (mem_reads + mem_writes) * 64 bytes / elapsed_time,
    summed over channels, in MB/s (1 MB = 1e6 bytes). This replaces NVMain's
    own bank-level `bandwidth` statistic, which is a per-bank instantaneous
    figure, not a DIMM-wide delivered-bandwidth number.

    Elapsed time comes from NVMain's own "Exiting at cycle <n>" line
    (traceSim/traceMain.cpp), printed once per run when the trace drains or
    the requested cycle budget is reached -- whichever happens first, so a
    trace that drains early correctly yields the (smaller) drain time, not
    the requested budget. That cycle count is in the GLOBAL/CPUFreq clock
    domain, NOT the model's own CLK domain used for E2E/queue/total latency
    elsewhere in this file.

    `cpufreq_mhz` defaults to CPUFREQ_MHZ (3000, global-constraints.md's
    fixed value) only for standalone/test callers that don't have a
    resolved value handy; T2.5 fix round 1: parse_raw_stats() always passes
    the run's own resolved CPUFreq explicitly (from resolve_clocks_mhz), so
    the default here is a fallback of last resort, not the normal path.

    Returns (completed_requests, delivered_bw_mbps), either element None if
    the stats file is missing the data needed (e.g. an aborted/incomplete
    run with no "Exiting at cycle" line).
    """
    reads = re.findall(r'\.mem_reads\s+(\d+)', content)
    writes = re.findall(r'\.mem_writes\s+(\d+)', content)
    exit_match = re.search(r'Exiting at cycle\s+(\d+)', content)

    if not reads or not writes or len(reads) != len(writes) or exit_match is None:
        return None, None

    try:
        read_counts = [int(m) for m in reads]
        write_counts = [int(m) for m in writes]
        elapsed_cycles = int(exit_match.group(1))
    except ValueError:
        return None, None

    if elapsed_cycles <= 0:
        return None, None

    elapsed_ns = elapsed_cycles * (1000.0 / cpufreq_mhz)
    elapsed_s = elapsed_ns * 1e-9

    completed_requests = sum(read_counts) + sum(write_counts)
    total_bytes = completed_requests * 64
    delivered_bw_mbps = (total_bytes / elapsed_s) / 1e6

    return completed_requests, delivered_bw_mbps


def extract_dimm_wear_stats(content):
    """
    Compute DIMM-wide wear-leveling summary stats from NVMain's per-subarray
    wear counters (T1.3 patch: wearLocations, wearTotalWrites, wearMaxWrites,
    one triple printed per subarray).

    Wear_Max_Writes = max(wearMaxWrites) over every subarray in the DIMM --
    the single hottest location anywhere in the module.
    Wear_HotSpot_Factor = that max, divided by the DIMM-wide mean writes per
    touched location (sum(wearTotalWrites) / sum(wearLocations)) -- i.e. how
    many times hotter the worst location is than the DIMM-wide average
    touched location.

    These stat lines are present (all reporting 0) even for a NullModel
    EnduranceModel (DDR5/PCM configs set `EnduranceModel NullModel`, which
    NVMain still registers stats for, but never populates: "Don't track data
    for NullModel"), and an all-read trace against a real (RowModel/
    WordModel) EnduranceModel produces the identical every-subarray-zero
    signature since no write ever happened. Both cases are handled the same
    way here: when no subarray recorded any write to any location
    (sum(wearLocations) <= 0) or every wearMaxWrites is 0, every DIMM-wide
    wear metric is None (blank in the CSV) -- never zero-filled, since a
    literal 0 would misleadingly read as "wear was measured and found to be
    zero" rather than "not measured for this technology/run".

    Never raises on partial/malformed input (T2.5 fix round 1): if
    wearLocations and wearMaxWrites are present but wearTotalWrites is
    absent entirely, or present but sums to 0, Wear_Max_Writes is still
    returned since it IS known -- only Wear_HotSpot_Factor (whose
    denominator depends on wearTotalWrites) comes back None. A malformed or
    partial wear block must blank the wear columns, not raise and lose the
    caller's entire row through parse_raw_stats' broad per-file
    `except Exception`.

    Returns (wear_max_writes, wear_hotspot_factor), either element None.
    """
    def _all_values(stat_name):
        pattern = rf'{re.escape(stat_name)}\s+([\d\.eE+\-]+)'
        try:
            return [float(m) for m in re.findall(pattern, content)]
        except ValueError:
            return []

    locations = _all_values('wearLocations')
    total_writes = _all_values('wearTotalWrites')
    max_writes = _all_values('wearMaxWrites')

    if not locations or not max_writes:
        return None, None

    sum_locations = sum(locations)
    sum_total_writes = sum(total_writes)
    dimm_max_writes = max(max_writes)

    if sum_locations <= 0 or dimm_max_writes <= 0:
        return None, None

    if sum_total_writes <= 0:
        # wearTotalWrites missing entirely, or present but summing to 0:
        # Wear_Max_Writes is known (locations/max_writes are non-empty and
        # dimm_max_writes > 0, checked above), but the mean-per-touched-
        # location denominator is not -- blank only the hot-spot factor,
        # never divide by zero.
        return dimm_max_writes, None

    mean_writes_per_location = sum_total_writes / sum_locations
    dimm_hotspot_factor = dimm_max_writes / mean_writes_per_location

    return dimm_max_writes, dimm_hotspot_factor


# ============================================================================
# CURRENT-MODE BACKGROUND-POWER CORRECTION (F1, final-review C1)
# ============================================================================
#
# UPSTREAM NVMAIN DEFECT, CORRECTED HERE AND NOT IN THE C++:
#
# simulators/nvmain/Ranks/StandardRank/StandardRank.cpp, EnergyModel "current"
# mode only. backgroundEnergy is accumulated for the WHOLE RANK (every term at
# lines ~895-941 is multiplied by deviceCount), but line ~992 computes
#
#     backgroundPower = ( backgroundEnergy / deviceCount * Voltage )
#                       / simulationTime / 1000.0
#
# and, unlike activatePower / burstPower / refreshPower (which ARE multiplied
# back by deviceCount at lines ~1015-1017), backgroundPower is never
# re-multiplied. The printed rank backgroundPower is therefore ONE device's
# background power while the rank's other three components are the whole
# rank's, and the printed rank totalPower (line ~1021, the sum of the four)
# inherits the same omission. In current mode the stats file is internally
# consistent and self-reconciling, so no residual check can see the loss.
#
# Only the DDR5 configs set `EnergyModel current`. PCM uses `energy` and ReRAM
# `NonVolatile`; both take the else-branch (backgroundPower = backgroundEnergy
# / simulationTime), which has no deviceCount division at all, so those
# technologies are unaffected and their device factor is 1.
#
# The correction is applied HERE, in post-processing, not in the submodule:
# the frozen raw stats stay exactly what NVMain printed, the golden regression
# files stay valid, and nothing has to be re-simulated. See
# simulators/nvmain/CLAUDE.md for the deliberately-unpatched note.

# Where to look for the NVMain .config a stats file names on its own "NVMain
# command line" line, when that absolute path no longer resolves (a moved
# checkout, an archived dataset). Tried in order, by basename. The tracked
# project copies come first so a repo-local config always wins over whatever
# happens to sit in the submodule's working tree.
NVMAIN_CONFIG_SEARCH_DIRS = (
    "/home/yuvalk/MBMM/configs",
    "/home/yuvalk/MBMM/simulators/nvmain/Config",
)

# Config keys this module needs, and what each is used for.
#   BusWidth / DeviceWidth -> devices per rank (StandardRank.cpp:125)
#   Voltage                -> the independent backgroundEnergy cross-check
#   EIDD2P0 / EIDD3N       -> the module static-power floor and ceiling
_DEVICE_COUNT_KEYS = ('BusWidth', 'DeviceWidth')


def uses_current_energy_model(content):
    """
    True when this stats file came from a run with `EnergyModel current`.

    Detection is on the file's own printed output, not on a filename or a
    technology guess: in current mode every NVMain energy counter is printed
    in milliamp-cycles ("...Energy 1.97967e+11mA*t"), while the `energy` and
    `NonVolatile` models print nanojoules ("...Energy 2.16768e+08nJ"). The
    unit is therefore a direct, per-file witness of which branch of
    StandardRank::CalculateStats ran.
    """
    return re.search(r'Energy\s+[\d\.eE+\-]+\s*mA\*t', content) is not None


def extract_nvmain_config_ref(content):
    """
    The .config path NVMain was launched with, read from the stats file's own
    "NVMain command line is:" banner (traceMain.cpp prints it first thing).
    Returns None if the banner or a .config token is absent.
    """
    match = re.search(r'NVMain command line is:\s*\n(.+)', content)
    if not match:
        return None
    for token in match.group(1).split():
        if token.endswith('.config') or token.endswith('.cfg'):
            return token
    return None


def resolve_nvmain_config(config_ref, stats_name="", search_dirs=None):
    """
    Resolve `config_ref` (as printed on the stats file's command line) to a
    readable config file. The literal path is tried first; if it no longer
    exists, the basename is looked for in NVMAIN_CONFIG_SEARCH_DIRS.

    Raises ValueError naming the stats file and every location tried. There is
    no default and no fallback device count: a silently-assumed device count
    would reintroduce exactly the class of error this correction exists to
    remove.
    """
    dirs = tuple(search_dirs) if search_dirs is not None else NVMAIN_CONFIG_SEARCH_DIRS

    if config_ref is None:
        raise ValueError(
            f"{stats_name or '<stats file>'}: EnergyModel-current stats file with no "
            f"'NVMain command line is:' config path, so the rank device count "
            f"(BusWidth/DeviceWidth) cannot be resolved and the rank backgroundPower "
            f"cannot be corrected. Refusing to guess a device count."
        )

    tried = []
    candidate = Path(config_ref)
    tried.append(str(candidate))
    if candidate.is_file():
        return candidate

    for directory in dirs:
        candidate = Path(directory) / Path(config_ref).name
        tried.append(str(candidate))
        if candidate.is_file():
            return candidate

    raise ValueError(
        f"{stats_name or '<stats file>'}: cannot find the NVMain config {config_ref!r} "
        f"named on its own command line, so the rank device count "
        f"(BusWidth/DeviceWidth) cannot be resolved and the rank backgroundPower "
        f"cannot be corrected. Tried: {tried}."
    )


def read_nvmain_config_keys(config_path, keys, stats_name=""):
    """
    Read the named keys out of an NVMain .config file ("KEY value" per line,
    ';' starts a comment). Returns {key: float}. Keys that are absent are
    simply missing from the returned dict; the caller decides which ones are
    mandatory and raises with its own message.
    """
    wanted = set(keys)
    values = {}
    try:
        text = Path(config_path).read_text(encoding='utf-8', errors='ignore')
    except OSError as exc:
        raise ValueError(
            f"{stats_name or '<stats file>'}: cannot read NVMain config "
            f"{config_path}: {exc}"
        )

    for line in text.splitlines():
        line = line.split(';')[0].split('#')[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] in wanted:
            try:
                values[parts[0]] = float(parts[1])
            except ValueError:
                continue
    return values


def extract_printed_device_count(content):
    """
    The device count NVMain itself printed, from StandardRank's own
    "Creating <banks> banks in all <devices> devices." line. Returns None when
    the line is absent (it is printed only when the rank creates its children,
    which every real run does, but hand-made fixtures need not). Used purely
    as a cross-check against the config arithmetic.
    """
    match = re.search(r'Creating\s+\d+\s+banks in all\s+(\d+)\s+devices', content)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def rank_device_count(content, stats_name="", search_dirs=None):
    """
    Devices per rank for the run that produced `content`, computed exactly the
    way StandardRank.cpp:125 computes it:

        deviceCount = BusWidth / DeviceWidth        (rounded up if not exact)

    from the run's OWN config, located through its own command line. Cross-
    checked against NVMain's printed "Creating N banks in all D devices." line
    when that line is present; a disagreement raises rather than picking one.

    Raises ValueError, naming the stats file and the missing key or file, if
    the config cannot be found or either key is absent. Never returns a
    default.
    """
    config_path = resolve_nvmain_config(
        extract_nvmain_config_ref(content), stats_name=stats_name, search_dirs=search_dirs)

    values = read_nvmain_config_keys(config_path, _DEVICE_COUNT_KEYS, stats_name=stats_name)
    missing = [k for k in _DEVICE_COUNT_KEYS if k not in values]
    if missing:
        raise ValueError(
            f"{stats_name or '<stats file>'}: NVMain config {config_path} is missing "
            f"{missing} (needed as BusWidth/DeviceWidth for the rank device count of "
            f"an EnergyModel-current run). Refusing to guess a device count."
        )

    bus_width = values['BusWidth']
    device_width = values['DeviceWidth']
    if device_width <= 0 or bus_width <= 0:
        raise ValueError(
            f"{stats_name or '<stats file>'}: NVMain config {config_path} has "
            f"non-positive BusWidth={bus_width} / DeviceWidth={device_width}; cannot "
            f"derive a rank device count."
        )

    device_count = int(bus_width // device_width)
    if bus_width % device_width != 0:
        # Mirrors StandardRank.cpp:126-130, which increments on a non-multiple.
        device_count += 1

    printed = extract_printed_device_count(content)
    if printed is not None and printed != device_count:
        raise ValueError(
            f"{stats_name or '<stats file>'}: NVMain printed 'in all {printed} devices' "
            f"but its config {config_path} gives BusWidth/DeviceWidth = "
            f"{bus_width:g}/{device_width:g} = {device_count}. The stats file and the "
            f"config disagree about the rank device count; refusing to correct "
            f"backgroundPower with either."
        )

    return device_count


def background_power_device_factor(content, stats_name="", search_dirs=None):
    """
    The factor each rank's printed backgroundPower must be multiplied by to
    become that rank's real background power.

    1 for every energy-mode technology (ReRAM `NonVolatile`, PCM `energy`):
    their backgroundPower is already per rank and nothing is corrected.
    The rank device count for an `EnergyModel current` run (DDR5), which is
    the exact factor StandardRank.cpp divides by and never multiplies back.
    """
    if not uses_current_energy_model(content):
        return 1
    return rank_device_count(content, stats_name=stats_name, search_dirs=search_dirs)


def extract_memory_clock_cycles(content, clk_mhz, cpufreq_mhz=CPUFREQ_MHZ):
    """
    Elapsed simulated time in MEMORY-clock cycles, which is NVMain's
    `simulationTime` in EnergyModel-current mode (StandardRank.cpp:975,
    GetCurrentCycle() - lastReset on the memory subsystem's own event queue).

    The stats file's "Exiting at cycle <n>" line is on the GLOBAL/CPUFreq
    domain (see extract_completed_requests_and_bandwidth), so it is converted
    here: cycles_mem = cycles_global * CLK / CPUFreq. Returns None when the
    line is absent or the clocks are unusable.
    """
    match = re.search(r'Exiting at cycle\s+(\d+)', content)
    if match is None or not clk_mhz or not cpufreq_mhz:
        return None
    try:
        global_cycles = int(match.group(1))
    except ValueError:
        return None
    if global_cycles <= 0:
        return None
    return global_cycles * (float(clk_mhz) / float(cpufreq_mhz))


def crosscheck_current_mode_background(content, device_factor, clk_mhz,
                                       cpufreq_mhz=CPUFREQ_MHZ, stats_name="",
                                       search_dirs=None, rel_tol=1e-3):
    """
    Independent check of the correction that does not go through the printed
    backgroundPower at all.

    NVMain's own current-mode definition (StandardRank.cpp:992), with the
    deviceCount division removed, is

        rank background power [W] = backgroundEnergy [mA*t] * Voltage [V]
                                    / simulationTime [memory cycles] / 1000

    so the RANK's backgroundEnergy counter (which IS accumulated per rank)
    reproduces the corrected power directly. This recomputes it from
    backgroundEnergy and compares against device_factor x the printed
    backgroundPower for every rank in the file.

    Returns a list of per-rank dicts (rank, expected_w, corrected_w, rel_err,
    ok). Returns [] when the file is not current-mode or lacks the inputs --
    never raises on a missing input, so one odd file cannot lose a whole row
    through parse_raw_stats' per-file except.
    """
    if not uses_current_energy_model(content):
        return []

    cycles = extract_memory_clock_cycles(content, clk_mhz, cpufreq_mhz)
    if not cycles:
        return []

    try:
        config_path = resolve_nvmain_config(
            extract_nvmain_config_ref(content), stats_name=stats_name,
            search_dirs=search_dirs)
        voltage = read_nvmain_config_keys(
            config_path, ('Voltage',), stats_name=stats_name).get('Voltage')
    except ValueError:
        return []
    if not voltage:
        return []

    energies = dict(re.findall(
        r'([\w.\-]+\.rank\d+)\.backgroundEnergy\s+([\d\.eE\-\+]+)mA\*t', content))
    powers = dict(re.findall(
        r'([\w.\-]+\.rank\d+)\.backgroundPower\s+([\d\.eE\-\+]+)W', content))

    checks = []
    for rank, energy_str in energies.items():
        if rank not in powers:
            continue
        try:
            expected = float(energy_str) * voltage / cycles / 1000.0
            corrected = float(powers[rank]) * device_factor
        except ValueError:
            continue
        rel_err = abs(expected - corrected) / expected if expected else 0.0
        checks.append({'rank': rank, 'expected_w': expected,
                       'corrected_w': corrected, 'rel_err': rel_err,
                       'ok': rel_err <= rel_tol})
    return checks


def current_mode_static_power_bounds(content, device_factor, rank_count,
                                     stats_name="", search_dirs=None):
    """
    Physical floor and ceiling the config's OWN datasheet currents put on the
    module's corrected static (background) power:

        floor   = devices x EIDD2P0 x Voltage / 1000   (deepest power-down)
        ceiling = devices x EIDD3N  x Voltage / 1000   (active standby)

    with devices = device_factor x rank_count (devices per rank x ranks in the
    module). The uncorrected DDR5 static figure sits BELOW this floor, which is
    the check that makes the defect visible without reading any source.

    Returns (floor_w, ceiling_w, devices), or None when the file is not
    current-mode or the config/keys are unavailable.
    """
    if not uses_current_energy_model(content) or rank_count <= 0:
        return None
    try:
        config_path = resolve_nvmain_config(
            extract_nvmain_config_ref(content), stats_name=stats_name,
            search_dirs=search_dirs)
        values = read_nvmain_config_keys(
            config_path, ('Voltage', 'EIDD2P0', 'EIDD3N'), stats_name=stats_name)
    except ValueError:
        return None

    if not all(k in values for k in ('Voltage', 'EIDD2P0', 'EIDD3N')):
        return None

    devices = device_factor * rank_count
    floor_w = devices * values['EIDD2P0'] * values['Voltage'] / 1000.0
    ceiling_w = devices * values['EIDD3N'] * values['Voltage'] / 1000.0
    return floor_w, ceiling_w, devices


def extract_total_power(content):
    """
    Extract total system power from a stats file: the sum of every rank's
    totalPower, across every channel.

    NVMain has no channel- or module-level totalPower aggregate of its own —
    only per-rank counters exist. A full DIMM keeps drawing background/leakage
    power on every rank whether or not that rank is doing work, so "total
    system power" must sum all ranks, not just the most-loaded one; picking a
    single rank silently discards the other (RANKS-1) ranks' contribution,
    understating the true total by a factor that tracks each technology's own
    rank x channel count (8x for full_dimm ReRAM, 4x for DDR5's 2 ranks x 2
    channels) — i.e. a different, incomparable discount per technology.
    Applied uniformly here, to every technology, for a like-for-like total.
    """
    # Pattern: "totalPower" followed by value and optional "W" unit
    pattern = r'totalpower\s+([\d\.eE+\-]+)(?:\s*w)?'
    matches = re.findall(pattern, content, re.IGNORECASE)

    if not matches:
        return None

    # Filter for reasonable per-rank values (0.01W to 100W for memory systems)
    valid_powers = []
    for match_str in matches:
        try:
            power_val = float(match_str)
            if 0.01 <= power_val <= 100.0:
                valid_powers.append(power_val)
        except ValueError:
            continue

    if not valid_powers:
        return None

    return sum(valid_powers)


def extract_module_power_components(content, background_factor=1):
    """
    Return the module-level (all ranks, all channels, summed) Watt-level power
    breakdown: backgroundPower, activatePower, burstPower, refreshPower.

    Sums the same per-rank totalPower entries extract_total_power() sums, so
    Static + Dynamic + Refresh reconciles to the Power column by construction
    (module-sum semantics, applied uniformly across every technology).
    Returns None if no rank block with a plausible totalPower (0.01-100W) is
    found in the file.

    F1 (final-review C1): `background_factor` is the rank device count for an
    `EnergyModel current` run (DDR5) and 1 for every energy-mode technology.
    Each rank's printed backgroundPower is multiplied by it BEFORE the module
    sum, which is the whole correction: see this module's
    "CURRENT-MODE BACKGROUND-POWER CORRECTION" section for why the printed
    value is one device's and the other three components are the rank's. The
    caller gets both the corrected sum ('backgroundPower') and the raw one
    ('backgroundPowerRaw'), plus 'backgroundPowerCorrection' (the Watts added,
    which is also exactly what the printed rank totalPower omits) and
    'rankCount', so nothing downstream has to re-derive the delta.

    The rank-validity filter still uses the PRINTED totalPower: it is a
    sanity window on NVMain's own output, and widening it for corrected values
    would change which ranks are admitted.
    """
    pattern = r'([\w.\-]+\.rank\d+)\.(totalPower|backgroundPower|activatePower|burstPower|refreshPower)\s+([\d\.eE\-\+]+)W'
    matches = re.findall(pattern, content)
    if not matches:
        return None

    ranks = {}
    for prefix, field, value_str in matches:
        try:
            ranks.setdefault(prefix, {})[field] = float(value_str)
        except ValueError:
            continue

    valid_ranks = {p: f for p, f in ranks.items()
                   if 'totalPower' in f and 0.01 <= f['totalPower'] <= 100.0}
    if not valid_ranks:
        return None

    totals = {'backgroundPower': 0.0, 'activatePower': 0.0,
              'burstPower': 0.0, 'refreshPower': 0.0}
    for fields in valid_ranks.values():
        for key in totals:
            totals[key] += fields.get(key, 0.0)

    raw_background = totals['backgroundPower']
    totals['backgroundPowerRaw'] = raw_background
    totals['backgroundPower'] = raw_background * background_factor
    totals['backgroundPowerCorrection'] = totals['backgroundPower'] - raw_background
    totals['backgroundPowerDeviceFactor'] = background_factor
    totals['rankCount'] = len(valid_ranks)

    return totals


RERAM_KEY_PREFIX = {
    '1T1R_SLC': 'reram_22nm_1t1r_slc',
    '1T1R_MLC': 'reram_22nm_1t1r_mlc',
    '1S1R_SLC': 'reram_22nm_selector_slc',
    '1S1R_MLC': 'reram_22nm_selector_mlc',
    # T2.8: silicon sensitivity is timing-only -- area, capacity, energies and
    # leakage stay NVSim's 22nm values from the same parent hardware-metrics
    # key 3_gen_nvmain_config.py's SILICON_TIMINGS table borrows them from, so
    # area/capacity lookups here mirror the SLC parent exactly.
    '1T1R_SILICON': 'reram_22nm_1t1r_slc',
    '1S1R_SILICON': 'reram_22nm_selector_slc',
}

# T5.1 step 2 fix round 1 (Critical-1): the 1024-organization equivalents of
# RERAM_KEY_PREFIX's keys. mbmm_master.reram_factory_bases()'s docstring explains the
# token-order flip: 2_extract_hardware_metrics.py derives "reram_22nm_1t1r_1024_slc" (not
# "reram_22nm_1t1r_slc_1024") from the Stage-1 result filename, so the 1024 prefix is NOT
# simply RERAM_KEY_PREFIX[tech] + "_1024". No silicon entries here: T2.8's silicon
# sensitivity configs have no organization axis of their own (classify_reram_organization
# never returns 1024 for a silicon filename -- their parent hardware is always the 2048
# SLC entry), so RERAM_KEY_PREFIX's existing silicon rows are always correct.
RERAM_KEY_PREFIX_1024 = {
    '1T1R_SLC': 'reram_22nm_1t1r_1024_slc',
    '1T1R_MLC': 'reram_22nm_1t1r_1024_mlc',
    '1S1R_SLC': 'reram_22nm_selector_1024_slc',
    '1S1R_MLC': 'reram_22nm_selector_1024_mlc',
}


def _reram_json_entry(technology_model, organization=2048):
    """Return the matching hardware_metrics.json entry for a ReRAM tech at `organization`
    (2048 default / 1024 T5.1 step 2 sensitivity).

    T5.1 step 2 fix round 1 (Critical-1): Technology alone (e.g. 1T1R_SLC) does not
    distinguish the two organizations -- that is by design (see
    classify_reram_organization's docstring) -- so a lookup keyed only by
    RERAM_KEY_PREFIX[technology_model] always resolves the 2048 entry: the 1024
    hardware_metrics.json key never startswith()-matches the 2048 prefix (verified by
    mbmm_master's test_reram_factory_bases_1024_do_not_collide_with_2048_key_prefixes),
    so silently it is also never matched BY it. Callers must pass the organization the
    stats file this lookup is for actually is (classify_reram_organization(filename)).

    Raises ValueError, naming the missing key, when the required entry is absent from
    HARDWARE_METRICS -- no silent fallback to the 2048 entry, and (I5, final review
    2026-09) no silent None for a missing file or a missing 2048 entry either. Only a
    technology that is not ReRAM at all (not in RERAM_KEY_PREFIX) returns None, which is
    how DDR5 and PCM keep working with no hardware_metrics.json at all.
    """
    if technology_model not in RERAM_KEY_PREFIX:
        return None

    if not HARDWARE_METRICS:
        raise ValueError(
            f"_reram_json_entry: technology {technology_model!r} is a ReRAM track and "
            f"needs its area/capacity from {HARDWARE_METRICS_FILE}, but no hardware "
            f"metrics were loaded (the file is missing, empty or unreadable). Run "
            f"2_extract_hardware_metrics.py, or point --hardware-metrics at the "
            f"hardware_metrics.json that belongs to this results directory."
        )

    if organization == 1024 and technology_model in RERAM_KEY_PREFIX_1024:
        prefix = RERAM_KEY_PREFIX_1024[technology_model]
        for key, entry in HARDWARE_METRICS.items():
            if key.startswith(prefix):
                return entry
        raise ValueError(
            f"_reram_json_entry: organization 1024 requires a hardware_metrics.json key "
            f"starting with {prefix!r} for technology {technology_model!r}, but none was "
            f"found (have: {sorted(HARDWARE_METRICS)}). Run 1_run_nvsim_hardware.py on the "
            f"_1024 base cfg and 2_extract_hardware_metrics.py first, or point "
            f"--hardware-metrics at a hardware_metrics.json copy that has it."
        )

    prefix = RERAM_KEY_PREFIX[technology_model]
    for key, entry in HARDWARE_METRICS.items():
        if key.startswith(prefix):
            return entry
    # I5: same loud failure the 1024 branch above already had. Returning None
    # here used to end as an Area_Density_Ratio of 1.0, i.e. a ReRAM row
    # published as exactly DDR5-dense, with exit 0.
    raise ValueError(
        f"_reram_json_entry: technology {technology_model!r} (organization "
        f"{organization}) requires a hardware_metrics.json key starting with "
        f"{prefix!r}, but none was found in {HARDWARE_METRICS_FILE} "
        f"(have: {sorted(HARDWARE_METRICS)}). Run 1_run_nvsim_hardware.py and "
        f"2_extract_hardware_metrics.py for that base model, or point "
        f"--hardware-metrics at the hardware_metrics.json that belongs to this "
        f"results directory."
    )


def extract_area_mm2(content, technology_model, organization=2048):
    """
    Extract silicon area in mm² from hardware_metrics.json, at `organization`
    (T5.1 step 2 fix round 1: organization-aware, see _reram_json_entry).
    DRAM/PCM use fixed ratios and return None here.
    """
    if technology_model in ['DDR5_4800', 'DDR5_4800_64B', 'pcm_microsoft_2009', '2D_DRAM_example', '3D_DRAM_example']:
        return None

    entry = _reram_json_entry(technology_model, organization)
    if entry is None:
        logger.error(f"[CRITICAL] hardware_metrics.json lookup failed for {technology_model} "
                     f"(organization {organization})")
        return None

    area = entry.get('area_mm2', None)
    if area is None or area <= 0:
        # I5: a missing/zero area is a broken hardware entry, not a reason to
        # publish this ReRAM row with a fabricated density ratio.
        raise ValueError(
            f"Invalid area_mm2 in {HARDWARE_METRICS_FILE} for {technology_model} "
            f"(organization {organization}): {area!r}")

    logger.debug(f"Found area for {technology_model} (organization {organization}): {area} mm²")
    return area


def extract_physical_capacity_gb(technology_model, organization=2048):
    """
    Return per-chip physical capacity (GB) from hardware_metrics.json, at `organization`
    (T5.1 step 2 fix round 1: organization-aware, see _reram_json_entry).

    NVMain stats report the *simulated system* address space, which varies with
    chip count and does not reflect the single-chip physical capacity needed for
    the area-density ratio.  This function always uses the JSON ground-truth.
    """
    if technology_model in ['DDR5_4800', 'DDR5_4800_64B', 'pcm_microsoft_2009', '2D_DRAM_example', '3D_DRAM_example']:
        return None

    entry = _reram_json_entry(technology_model, organization)
    if entry is None:
        logger.error(f"[CRITICAL] hardware_metrics.json lookup failed for capacity of "
                     f"{technology_model} (organization {organization})")
        return None

    cap = entry.get('capacity_gb', None)
    if cap is None or cap <= 0:
        # I5: see extract_area_mm2 -- fail loudly rather than fall back.
        raise ValueError(
            f"Invalid capacity_gb in {HARDWARE_METRICS_FILE} for {technology_model} "
            f"(organization {organization}): {cap!r}")

    logger.debug(f"Found per-chip capacity for {technology_model} (organization {organization}): {cap} GB")
    return cap


# Minor-3 (final review 2026-09): extract_capacity_gb() used to sit here. It
# read the NVMain stats "capacity is N MB" line, took only the FIRST channel,
# and nothing called it: the area-density ratio deliberately uses the per-chip
# physical capacity from hardware_metrics.json instead (see
# extract_physical_capacity_gb above and the comment in parse_raw_stats).
# visualize_slides._extract_capacity_gib() is the live, channel-summing reader
# of that stats line. Removed rather than left as a second, wrong answer.


# ============================================================================
# CALCULATION FUNCTIONS
# ============================================================================

def decompose_power(record, technology, power):
    """
    Decompose total system power into static (leakage), dynamic (access), and
    refresh components using real, module-summed NVMain counters — no fixed
    per-technology ratios, and (as of the Priority-1 repair) no NonVolatile
    special-casing either.

    Single path for every technology: rank-level backgroundPower + activatePower
    + burstPower + refreshPower, summed across all ranks/channels by
    extract_module_power_components(), reconciles to totalPower by construction
    (both are sums over the same set of ranks). For ReRAM this now holds because
    Eactstdby/Eprestdby are derived per-technology from real NVSim leakage
    (see 3_gen_nvmain_config.py) instead of the previously-unused StandbyPower
    key — backgroundPower is a real, technology-differentiated NVMain counter
    now, not a generic default, so it no longer needs a separate residual-based
    path the way it did before that fix.

    F1 (final-review C1): `record['background_power']` is the CORRECTED module
    background sum -- each rank's printed backgroundPower multiplied by that
    rank's device count for an EnergyModel-current (DDR5) run, unchanged for
    every energy-mode technology. `record['power']` carries the identical
    correction (parse_raw_stats), because the printed rank totalPower omits the
    same Watts. The reconciliation below therefore still holds by construction;
    note that it could never have DETECTED the omission, since totalPower and
    the components shared it.

    Returns (dynamic, static, refresh, unattributed_power). unattributed_power
    is the leftover after Static+Dynamic+Refresh is subtracted from Power;
    should be ~0 (logged as a warning if it exceeds 3% of Power).
    """
    background = record.get('background_power')
    if background is None:
        logger.error(f"[CRITICAL] No rank-level power counters found for "
                    f"{technology} — cannot compute power split")
        return None, None, None, None

    static = background
    dynamic = (record.get('activate_power') or 0.0) + (record.get('burst_power') or 0.0)
    refresh = record.get('refresh_power') or 0.0
    unattributed = power - (static + dynamic + refresh)

    if power > 0 and abs(unattributed) > 0.03 * power:
        logger.warning(f"[POWER-RECONCILE] {technology}: components sum to "
                       f"{static + dynamic + refresh:.6f}W vs Power={power:.6f}W "
                       f"(unattributed {unattributed:.6f}W, {100 * unattributed / power:.1f}%)")

    return dynamic, static, refresh, unattributed


def calculate_pdp(latency_ns, power):
    """
    Calculate Power-Delay Product: Latency_ns × Total_System_Power (W·ns = nJ).

    Delay must be in nanoseconds, not cycles: each technology runs in its own
    clock domain (DDR5 2400 MHz vs ReRAM/PCM 800 MHz), so cycle-based PDP
    inflated higher-clocked technologies in cross-technology comparisons.
    """
    if latency_ns > 0 and power > 0:
        return latency_ns * power
    return 0.0


def calculate_latency_ns(cycles, clk_mhz):
    """
    Convert raw cycle count to nanoseconds using the given clock frequency.
    Formula: latency_ns = cycles * (1000 / clk_mhz)

    T2.5 fix round 1: `clk_mhz` must be the run's own memory-clock
    frequency, resolved once per file via resolve_clocks_mhz (preferring the
    stats file's own diagnostic line over CLOCK_FREQUENCY_MHZ's per-
    technology default) -- this used to take a `technology` string and look
    the frequency up in CLOCK_FREQUENCY_MHZ directly, which silently used
    the table's default CLK for a technology even when the actual run used a
    different one (a clock-sensitivity config, for example).
    """
    return cycles * (1000.0 / clk_mhz)


def calculate_area_density_ratio(area_mm2, capacity_gb, technology):
    """
    Calculate normalized area density ratio (Higher is Better).

    Formula: DDR5_baseline_mm2_per_GB / (tech_mm2_per_GB)
    DDR5 = 1.0.  Values > 1.0 are denser than DDR5; values < 1.0 are less dense.

    For ReRAM: extracted from hardware_metrics.json via hybrid-empirical method.
    For DRAM/PCM: fixed empirical ratios (inverted from the mm²/GB baseline).
    """

    # Fixed ratios expressed as density relative to DDR5 (higher = denser)
    # PCM 0.80 in the old mm²/GB system → inverted: 1/0.80 = 1.25
    fixed_ratios = {
        'DDR5_4800': 1.00,
        'DDR5_4800_64B': 1.00,  # T2.4: same physical DIMM/channel shape as the primary baseline
        'pcm_microsoft_2009': 1.25,
        '2D_DRAM_example': 1.053,
        '3D_DRAM_example': 1.176,
    }

    if technology in fixed_ratios:
        return fixed_ratios[technology]

    # For ReRAM: Require successful extraction (STRICT ERROR LOGGING)
    if area_mm2 is None or capacity_gb is None:
        logger.error(f"[CRITICAL] FAILED to extract area/capacity for {technology}. "
                    f"Area={area_mm2}, Capacity={capacity_gb}. Aborting calculation.")
        return None

    if capacity_gb <= 0:
        logger.error(f"[CRITICAL] Invalid capacity for {technology}: {capacity_gb} GB")
        return None

    if area_mm2 <= 0:
        logger.error(f"[CRITICAL] Invalid area for {technology}: {area_mm2} mm²")
        return None

    # Inverted: DDR5_baseline / tech → higher means denser than DDR5
    reram_mm2_per_gb = area_mm2 / capacity_gb
    ratio = DDR5_MM2_PER_GB / reram_mm2_per_gb

    logger.debug(f"{technology}: Area={area_mm2:.2f} mm², Capacity={capacity_gb:.2f} GB, "
                f"Density ratio = {DDR5_MM2_PER_GB}/({area_mm2:.2f}/{capacity_gb:.2f}) = {ratio:.4f}")

    return ratio


# ============================================================================
# PARSING AND AGGREGATION
# ============================================================================

def parse_raw_stats():
    """
    Parse all stats_*.out files and extract raw metrics.

    Returns (data, failures): `data` is the list of successfully-parsed
    records (unchanged shape from before T2.5 fix round 2); `failures` is a
    list of (filename, error_message) tuples for every file whose per-file
    parse raised an exception (e.g. extract_clocks_mhz's ValueError on
    disagreeing clock-diagnostic lines within one file).

    T2.5 fix round 2: this used to swallow such per-file exceptions
    completely -- logged at ERROR, the row silently dropped, no trace left
    in the return value, and the calling process still exited 0. The
    per-file try/except below is UNCHANGED in that one bad file still does
    not stop the rest of the files from parsing, but every failure is now
    collected and returned so the caller (main(), the CLI entry point) can
    decide whether that should be a fatal (non-zero exit) condition -- this
    library function itself never raises SystemExit or calls exit(); see
    main()'s --allow-parse-failures flag for the decision policy.

    The duplicate (Technology, Architecture, Benchmark) guard is NOT part of
    this failures list and is unchanged: it is a hard `raise ValueError`,
    deliberately not caught here, since a duplicate key would silently
    corrupt aggregates rather than just lose one row.
    """

    logger.info("="*80)
    logger.info("STAGE 6: DATA PROCESSING - Metric Extraction & Calculation")
    logger.info("="*80)
    logger.info(f"\nScanning for stats files in: {RESULTS_SYS_DIR}")

    stat_files = sorted(glob.glob(f"{RESULTS_SYS_DIR}/stats_*.out"))

    if not stat_files:
        logger.error(f"No stats files found in {RESULTS_SYS_DIR}")
        return [], []

    logger.info(f"Found {len(stat_files)} stats files\n")

    data = []
    failures = []
    # MLPerf excluded: all stats_*_mlperf_inference.out runs (2026-03-29) hit trace
    # EOF at cycle 0 with zero requests — mlperf_inference.nvt was missing/empty at
    # launch. Raw source survives at simulators/gem5/m5out/mlperf_raw.txt if we ever
    # regenerate the .nvt and re-run. See session audit 2026-07-06.
    excluded_benchmarks = ['mlperf_inference', 'mlperf']

    # T2.4: guard against two different stats files mapping to the same
    # (Technology, Architecture, Benchmark) key -- e.g. a legacy
    # stats_DDR5_4800_DRAM_*.out left over from an archive alongside a
    # freshly-generated stats_DDR5_4800_DRAM_subchannel_*.out for the same
    # benchmark: both classify to (DDR5_4800, full_dimm, <benchmark>).
    # Silently keeping one (or appending both as ambiguous duplicate rows)
    # would corrupt every downstream aggregate; fail loudly instead, naming
    # both files, so the results/ directory can be cleaned up deliberately.
    seen_keys = {}

    # T5.1 step 2: guard against a --results-dir mixing stats files from both
    # the 2048 (default) and 1024 (sensitivity) ReRAM organizations. Technology
    # alone does not distinguish them (classify_reram_organization's docstring),
    # so this is a separate, directory-wide check, not something the
    # (Technology, Architecture, Benchmark) duplicate-key guard above would
    # always catch (it only fires when the two organizations happen to share a
    # benchmark for the same tech/arch).
    seen_organization = None  # (organization, filename) of the first ReRAM file seen

    for filepath in stat_files:
        filename = Path(filepath).name

        org = classify_reram_organization(filename)
        if org is not None:
            if seen_organization is not None and seen_organization[0] != org:
                raise ValueError(
                    f"Mixed ReRAM organization in {RESULTS_SYS_DIR}: "
                    f"{seen_organization[1]!r} is {seen_organization[0]}x"
                    f"{seen_organization[0]} but {filename!r} is {org}x{org}. Each "
                    f"results directory must hold stats files for exactly one "
                    f"organization (T5.1 step 2, organization axis); move one run's "
                    f"stats files to its own results directory before re-running "
                    f"process_metrics.py."
                )
            if seen_organization is None:
                seen_organization = (org, filename)

        # Classify
        tech = classify_technology(filename)
        if not tech:
            logger.debug(f"⊘ {filename}: Unknown technology, skipping")
            continue

        arch = extract_architecture(filename)
        if not arch:
            logger.debug(f"⊘ {filename}: Unknown architecture, skipping")
            continue

        bench = extract_benchmark(filename)
        if any(excl in bench for excl in excluded_benchmarks):
            logger.debug(f"⊘ {filename}: Excluded benchmark, skipping")
            continue

        key = (tech, arch, bench)
        if key in seen_keys:
            raise ValueError(
                f"Duplicate (Technology, Architecture, Benchmark) key {key}: "
                f"both {seen_keys[key]!r} and {filename!r} map to it. Remove or "
                f"rename one of the two stats files in {RESULTS_SYS_DIR} before "
                f"re-running process_metrics.py."
            )
        seen_keys[key] = filename

        # Parse file
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            cycles = extract_total_execution_cycles(content)
            power = extract_total_power(content)

            if cycles is None or power is None or cycles <= 0 or power <= 0:
                logger.debug(f"⊘ {filename}: Missing or invalid metrics")
                continue

            hw_latency = extract_hw_latency(content)
            queue_latency = extract_queue_latency(content)

            # Extract area and per-chip physical capacity for ReRAM density ratio.
            # Both come from hardware_metrics.json so they are at the same scale.
            # The NVMain stats "capacity is N MB" line reports the simulated
            # address space, which scales with chip count and must NOT be used
            # for the density formula.
            # T5.1 step 2 fix round 1 (Critical-1): pass this file's own organization
            # (already classified above for the mixed-organization guard) so a
            # 1024-organization stats file gets the 1024 hardware entry, not the 2048
            # one -- `org` is None for non-ReRAM technologies, where organization is
            # unused anyway (extract_area_mm2/extract_physical_capacity_gb return None
            # for DDR5/PCM before ever looking at it), so default to 2048 for those.
            area_mm2 = extract_area_mm2(content, tech, org if org is not None else 2048)
            capacity_gb = extract_physical_capacity_gb(tech, org if org is not None else 2048)

            # F1 (final-review C1): the factor each rank's printed
            # backgroundPower must be multiplied by. 1 for ReRAM/PCM
            # (energy-mode), the rank device count for DDR5 (EnergyModel
            # current), where NVMain divides background by deviceCount and
            # never multiplies it back. This RAISES (caught by the per-file
            # except below, which turns it into a reported parse failure and a
            # non-zero exit) if the run's config or its BusWidth/DeviceWidth
            # keys cannot be found: a silently-defaulted device count is the
            # exact failure mode being repaired here.
            bg_factor = background_power_device_factor(content, stats_name=filename)

            # Real, module-summed power-component counters (all ranks, all
            # channels) for the static/dynamic/refresh decomposition.
            module_power = extract_module_power_components(
                content, background_factor=bg_factor)

            # T2.5 fix round 1: resolve this file's OWN clocks once (prefers
            # the stats file's own diagnostic line over the CLOCK_FREQUENCY_MHZ/
            # CPUFREQ_MHZ fallback -- see resolve_clocks_mhz), then reuse the
            # result for every cycles-to-ns conversion below and in
            # process_metrics() (Total/HW/Queue/E2E latency, delivered-bandwidth
            # elapsed time), instead of each conversion looking up a
            # technology-keyed table default independently.
            clk_mhz, cpufreq_mhz = resolve_clocks_mhz(content, tech, filename)

            # T2.5: end-to-end latency, delivered bandwidth, completed
            # requests, and DIMM-wide wear-leveling summary stats.
            e2e_latency_ns = extract_end_to_end_latency_ns(content, clk_mhz)
            completed_requests, delivered_bw_mbps = extract_completed_requests_and_bandwidth(
                content, cpufreq_mhz)
            wear_max_writes, wear_hotspot_factor = extract_dimm_wear_stats(content)

            # F1: Power is the sum of the ranks' PRINTED totalPower, and each
            # printed rank totalPower omits exactly (deviceCount - 1) x that
            # rank's printed backgroundPower (StandardRank.cpp:1021 adds the
            # un-re-multiplied background to the three re-multiplied
            # components). Adding the same correction here keeps Power equal
            # to the sum of the corrected components, so decompose_power's
            # reconciliation still holds by construction and Unattributed_Power
            # stays the small printing residual it has always been. For every
            # energy-mode technology the correction is exactly 0.0 W and Power
            # is bit-for-bit what it was before this change.
            if module_power is not None and module_power['backgroundPowerCorrection']:
                power += module_power['backgroundPowerCorrection']

                for check in crosscheck_current_mode_background(
                        content, bg_factor, clk_mhz, cpufreq_mhz, stats_name=filename):
                    if not check['ok']:
                        logger.error(
                            f"[BACKGROUND-XCHECK] {filename}: {check['rank']} "
                            f"backgroundEnergy x Voltage / memory cycles / 1000 = "
                            f"{check['expected_w']:.6f}W but corrected backgroundPower "
                            f"({bg_factor} x printed) = {check['corrected_w']:.6f}W "
                            f"(relative error {check['rel_err']:.2%})")

                bounds = current_mode_static_power_bounds(
                    content, bg_factor, module_power['rankCount'], stats_name=filename)
                if bounds is not None:
                    floor_w, ceiling_w, devices = bounds
                    static_w = module_power['backgroundPower']
                    if not (floor_w <= static_w <= ceiling_w):
                        logger.error(
                            f"[STATIC-BOUNDS] {filename}: corrected module static power "
                            f"{static_w:.6f}W is outside the config's own datasheet range "
                            f"[{floor_w:.6f}W, {ceiling_w:.6f}W] for {devices} devices "
                            f"(devices x EIDD2P0 x V .. devices x EIDD3N x V)")

            data.append({
                'filename': filename,
                'technology': tech,
                'architecture': arch,
                'benchmark': bench,
                'total_execution_cycles': cycles,
                'hw_latency_cycles': hw_latency,
                'queue_latency_cycles': queue_latency,
                'power': power,
                'area_mm2': area_mm2,
                'capacity_gb': capacity_gb,
                'background_power': module_power['backgroundPower'] if module_power else None,
                'activate_power': module_power['activatePower'] if module_power else None,
                'burst_power': module_power['burstPower'] if module_power else None,
                'refresh_power': module_power['refreshPower'] if module_power else None,
                # F1: 1 for every energy-mode technology, the rank device count
                # for an EnergyModel-current (DDR5) run. Carried into the CSVs
                # as Background_Power_Device_Factor so a corrected row can never
                # be mistaken for a raw one.
                'background_power_device_factor': bg_factor,
                'clk_mhz': clk_mhz,
                'cpufreq_mhz': cpufreq_mhz,
                'e2e_latency_ns': e2e_latency_ns,
                'delivered_bw_mbps': delivered_bw_mbps,
                'completed_requests': completed_requests,
                'wear_max_writes': wear_max_writes,
                'wear_hotspot_factor': wear_hotspot_factor,
            })
            
            # T2.5 fix round 2: hw_latency/queue_latency can legitimately be
            # None (no averageLatency/averageQueueLatency line in a partial
            # or hand-made stats fixture) even when the row above parsed and
            # was appended successfully -- format them defensively instead
            # of crashing on None.__format__, which used to be silently
            # swallowed by the except block below (harmless before fix round
            # 2, since data.append() already ran) but would now be wrongly
            # counted as a parse FAILURE for a row that actually succeeded.
            hw_latency_str = f"{hw_latency:8.2f}" if hw_latency is not None else "     N/A"
            queue_latency_str = f"{queue_latency:8.2f}" if queue_latency is not None else "     N/A"

            if area_mm2 is not None and capacity_gb is not None:
                logger.debug(f"✓ {filename}: Tech={tech:15s} | Arch={arch:10s} | "
                            f"TotalCyc={cycles:10.2f} | HWCyc={hw_latency_str} | QCyc={queue_latency_str} | "
                            f"Power={power:10.4f}W | Area={area_mm2:.2f}mm² | Cap={capacity_gb:.2f}GB")
            else:
                logger.warning(f"⚠ {filename}: Tech={tech:15s} | Arch={arch:10s} | "
                              f"TotalCyc={cycles:10.2f} | HWCyc={hw_latency_str} | QCyc={queue_latency_str} | "
                              f"Power={power:10.4f}W | MISSING AREA/CAPACITY DATA")
        
        except Exception as e:
            logger.error(f"✗ {filename}: Failed to parse - {str(e)}")
            failures.append((filename, str(e)))
            continue

    logger.info(f"\nTotal data points extracted: {len(data)}\n")
    if failures:
        logger.error(f"{len(failures)} stats file(s) failed to parse and were skipped:")
        for fname, err in failures:
            logger.error(f"  - {fname}: {err}")
    return data, failures


def process_metrics(raw_data, run_fields=None):
    """Calculate derived metrics from raw data.

    `run_fields` carries the Run_* provenance columns (I6). It may be:
      - None (default): build a PER-FILE resolver from the run_manifest.json
        beside the stats files being processed. A directory without a manifest,
        a manifest that does not list its own outputs, and any stats file a
        manifest does not list, each get "unknown" in every Run_* column and a
        WARNING - never a fabricated value (F2 fix round 1, review Important-1).
      - a callable f(stats_filename) -> {column: value}.
      - a plain dict, applied to every row (used by tests).
    """

    logger.info("Calculating derived metrics...")

    if run_fields is None:
        resolve_run_fields = make_run_provenance_resolver(
            load_run_manifest(RESULTS_SYS_DIR), RESULTS_SYS_DIR)
    elif callable(run_fields):
        resolve_run_fields = run_fields
    else:
        fixed_fields = dict(run_fields)
        def resolve_run_fields(filename):
            return dict(fixed_fields)

    processed = []

    for record in raw_data:
        tech = record['technology']
        power = record['power']
        cycles = record['total_execution_cycles']
        # T2.5 fix round 1: this run's OWN clock (resolve_clocks_mhz, resolved
        # once in parse_raw_stats), not a technology-keyed table lookup -- see
        # calculate_latency_ns's docstring for why that distinction matters.
        clk_mhz = record['clk_mhz']

        # Power decomposition (real NVMain counters, see decompose_power())
        dyn_power, stat_power, refresh_power, unattributed_power = decompose_power(record, tech, power)

        # Latency normalization: cycles → nanoseconds (clock-domain corrected)
        latency_ns = calculate_latency_ns(cycles, clk_mhz)
        hw_latency_ns = (calculate_latency_ns(record['hw_latency_cycles'], clk_mhz)
                         if record['hw_latency_cycles'] is not None else None)
        queue_latency_ns = (calculate_latency_ns(record['queue_latency_cycles'], clk_mhz)
                            if record['queue_latency_cycles'] is not None else None)

        # PDP in W·ns (queue-aware: latency_ns derives from averageTotalLatency)
        pdp = calculate_pdp(latency_ns, power)

        # Area density ratio (ReRAM hybrid-empirical)
        area_ratio = calculate_area_density_ratio(
            record['area_mm2'],
            record['capacity_gb'],
            tech
        )

        # I5 (final review 2026-09): a ReRAM row whose area density could not be
        # derived used to be published with a ratio of 1.0, i.e. as exactly
        # DDR5-dense, and the run still exited 0. It is now fatal. DDR5/PCM
        # never reach here (calculate_area_density_ratio returns their fixed
        # ratio), so this cannot affect a DDR5-only or PCM-only run.
        if area_ratio is None:
            raise ValueError(
                f"Area density ratio could not be computed for {tech} "
                f"({record['architecture']}, {record['benchmark']}): "
                f"area_mm2={record['area_mm2']!r}, capacity_gb={record['capacity_gb']!r}. "
                f"A ReRAM row must not be published with a fallback ratio of 1.0 "
                f"('DDR5 parity'); fix the hardware metrics for this technology or "
                f"point --hardware-metrics at the right file.")

        processed.append({
            'Technology': tech,
            'Architecture': record['architecture'],
            'Benchmark': record['benchmark'],
            'Total_Execution_Cycles': cycles,
            'HW_Latency_Cycles': record['hw_latency_cycles'],
            'Queue_Latency_Cycles': record['queue_latency_cycles'],
            'Latency_ns': latency_ns,
            'HW_Latency_ns': hw_latency_ns,
            'Queue_Latency_ns': queue_latency_ns,
            'Power': power,
            'Dynamic_Power': dyn_power,
            'Static_Power': stat_power,
            'Refresh_Power': refresh_power,
            'Unattributed_Power': unattributed_power,
            'PDP': pdp,
            'Area_Density_Ratio': area_ratio,
            'E2E_Latency_ns': record['e2e_latency_ns'],
            'Delivered_BW_MBps': record['delivered_bw_mbps'],
            'Wear_Max_Writes': record['wear_max_writes'],
            'Wear_HotSpot_Factor': record['wear_hotspot_factor'],
            'Completed_Requests': record['completed_requests'],
            # F1 (final-review C1): makes the background-power correction
            # visible in every CSV that carries a power number. 1 means the
            # row's Static_Power/Power are exactly NVMain's printed rank sums
            # (ReRAM, PCM); > 1 means each rank's printed backgroundPower was
            # multiplied by this rank device count first, because the run used
            # EnergyModel current and NVMain prints that one component per
            # device (4 for DDR5_4800_DRAM_subchannel, 8 for the 64 B and
            # legacy 64-bit DDR5 configs).
            'Background_Power_Device_Factor': record['background_power_device_factor'],
            # I6 (final review 2026-09): the run's own flags, from the run
            # manifest mbmm_master.py wrote beside these stats files - but only
            # for the stats files that manifest lists as its own (F2 fix round 1).
            **resolve_run_fields(record.get('filename', '')),
        })

    logger.info(f"Processed {len(processed)} data points\n")
    return processed


def calculate_geometric_mean_pdp(df_metrics):
    """Calculate geometric mean PDP per technology — full DIMM only."""

    logger.info("Calculating geometric mean PDP per technology (full_dimm only)...")

    # Filter to full_dimm for an apples-to-apples comparison.
    # DDR5 and PCM only have full_dimm records; including single/8chip/16chip
    # ReRAM configs would inflate their averages relative to the DRAM baselines.
    df_full_dimm = df_metrics[df_metrics['Architecture'] == 'full_dimm']

    geometric_means = {}

    for tech in df_full_dimm['Technology'].unique():
        tech_df = df_full_dimm[df_full_dimm['Technology'] == tech]
        edp_values = tech_df['PDP'].values

        if len(edp_values) > 0:
            # Geometric mean = exp(mean(ln(values)))
            geom_mean = np.exp(np.mean(np.log(edp_values)))
            geometric_means[tech] = geom_mean

            logger.debug(f"  {tech:20s}: {len(edp_values):2d} data points, "
                        f"Geometric Mean PDP = {geom_mean:12.2f}")

    logger.info(f"Calculated geometric means for {len(geometric_means)} technologies\n")
    return geometric_means


# ============================================================================
# OUTPUT FUNCTIONS
# ============================================================================

def save_bar_chart_metrics(df_processed):
    """Save metrics for bar chart visualization."""
    
    output_file = Path(OUTPUT_DIR) / "processed_bar_chart_metrics.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Select columns for bar charts (includes latency decomposition for write-torture analysis).
    # T2.5: E2E_Latency_ns, Delivered_BW_MBps, Wear_Max_Writes, Wear_HotSpot_Factor,
    # Completed_Requests are appended at the end (existing columns/order unchanged)
    # so downstream visualize_*.py scripts that index by name keep working.
    df_output = df_processed[[
        'Technology', 'Architecture', 'Benchmark',
        'Total_Execution_Cycles', 'HW_Latency_Cycles', 'Queue_Latency_Cycles',
        'Latency_ns', 'HW_Latency_ns', 'Queue_Latency_ns',
        'Power', 'Dynamic_Power', 'Static_Power', 'Refresh_Power', 'Unattributed_Power', 'PDP',
        'E2E_Latency_ns', 'Delivered_BW_MBps', 'Wear_Max_Writes', 'Wear_HotSpot_Factor',
        'Completed_Requests',
        # F1 (final-review C1): appended after the T2.5 block, so every
        # downstream reader that indexes by name keeps working.
        'Background_Power_Device_Factor'
    ] + RUN_PROVENANCE_COLUMN_NAMES]

    df_output.to_csv(output_file, index=False)

    logger.info(f"✓ Saved bar chart metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Benchmarks: {df_output['Benchmark'].nunique()}")


def save_pareto_metrics(df_processed):
    """Save metrics for Pareto frontier visualization."""
    
    output_file = Path(OUTPUT_DIR) / "processed_pareto_metrics.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Select columns for Pareto plots (all architectures)
    df_output = df_processed[[
        'Technology', 'Architecture', 'Benchmark',
        'Total_Execution_Cycles', 'Latency_ns', 'Power',
        # F1 (final-review C1): Power carries the corrected background, so the
        # factor that corrected it travels with it here too.
        'Background_Power_Device_Factor'
    ] + RUN_PROVENANCE_COLUMN_NAMES]
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved Pareto metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Architectures: {df_output['Architecture'].nunique()}")


def save_hero_metrics(df_processed):
    """Save metrics for hero graph visualization."""
    
    output_file = Path(OUTPUT_DIR) / "processed_hero_metrics.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Select columns for hero graphs (include write-torture decomposition + area density).
    # T2.5: same five new columns as save_bar_chart_metrics, appended at the end.
    df_output = df_processed[[
        'Technology', 'Benchmark',
        'Total_Execution_Cycles', 'HW_Latency_Cycles', 'Queue_Latency_Cycles',
        'Power', 'PDP', 'Area_Density_Ratio',
        'E2E_Latency_ns', 'Delivered_BW_MBps', 'Wear_Max_Writes', 'Wear_HotSpot_Factor',
        'Completed_Requests',
        # F1 (final-review C1): Power and PDP here carry the corrected
        # background, so the factor travels with them.
        'Background_Power_Device_Factor'
    ] + RUN_PROVENANCE_COLUMN_NAMES]
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved hero metrics: {output_file}")
    logger.debug(f"  Records: {len(df_output)}, Technologies: {df_output['Technology'].nunique()}")


def save_geometric_means(geometric_means_dict):
    """Save pre-calculated geometric mean PDP values."""
    
    output_file = Path(OUTPUT_DIR) / "processed_geometric_means.csv"
    output_dir = output_file.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    df_output = pd.DataFrame(
        list(geometric_means_dict.items()),
        columns=['Technology', 'Geometric_Mean_PDP']
    )
    
    df_output.to_csv(output_file, index=False)
    
    logger.info(f"✓ Saved geometric means: {output_file}")


# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    """Execute data processing pipeline."""

    global RESULTS_SYS_DIR, OUTPUT_DIR, HARDWARE_METRICS_FILE, HARDWARE_METRICS

    parser = argparse.ArgumentParser(description="MBMM Step 6: Metrics Processing")
    parser.add_argument("--results-dir", default=RESULTS_SYS_DIR,
                        help="Directory to scan for stats_*.out files (default: results/system).")
    parser.add_argument("--output-dir", default=OUTPUT_DIR,
                        help="Directory to write processed_*.csv files (default: results/).")
    parser.add_argument("--hardware-metrics", default=HARDWARE_METRICS_FILE,
                        help="Path to the hardware_metrics.json to read ReRAM area/capacity "
                             "from (default: results/hardware_metrics.json, the live shared "
                             "file). T5.1 step 2 fix round 1: point this at an isolated "
                             "sensitivity run's own copy (e.g. "
                             "results/system_rev2026-09_org1024/_csv/hardware_metrics.json) "
                             "to re-derive that run's processed CSVs without depending on "
                             "whatever the live file currently holds.")
    parser.add_argument("--allow-parse-failures", action="store_true",
                        help="T2.5 fix round 2: downgrade per-file stats-parse failures from "
                             "a fatal condition (ERROR logged, process exits 1) to a WARNING "
                             "(process exits 0). The rows that DID parse are always written to "
                             "the CSVs regardless of this flag -- one bad file never hides the "
                             "others; this flag only controls the exit code, for knowingly "
                             "processing an old/partial dataset that has files this version "
                             "can't parse.")
    args = parser.parse_args()
    RESULTS_SYS_DIR = args.results_dir
    OUTPUT_DIR = args.output_dir
    HARDWARE_METRICS_FILE = args.hardware_metrics
    HARDWARE_METRICS = _load_hardware_metrics(HARDWARE_METRICS_FILE)

    try:
        # Step 1: Parse raw stats files
        raw_data, parse_failures = parse_raw_stats()

        if parse_failures:
            log_fn = logger.warning if args.allow_parse_failures else logger.error
            log_fn(f"{len(parse_failures)} stats file(s) failed to parse and were skipped "
                   f"(see per-file errors above):")
            for fname, err in parse_failures:
                log_fn(f"  - {fname}: {err}")
            if args.allow_parse_failures:
                logger.warning("--allow-parse-failures set: continuing with exit 0 despite "
                                "the failure(s) above.")
            else:
                logger.error("Failing (exit 1) because of the parse failure(s) above. Pass "
                              "--allow-parse-failures to continue with a WARNING instead, once "
                              "these are understood/expected (e.g. an old dataset this version "
                              "can't fully parse).")

        if not raw_data:
            logger.error("No data extracted from stats files")
            return False

        # Step 2: Convert to DataFrame for processing
        df_processed = pd.DataFrame(process_metrics(raw_data))
        
        # Step 3: Calculate geometric means
        geometric_means = calculate_geometric_mean_pdp(df_processed)
        
        # Step 4: Output intermediate CSV files
        logger.info("Saving intermediate metric files...")
        
        save_bar_chart_metrics(df_processed)
        save_pareto_metrics(df_processed)
        save_hero_metrics(df_processed)
        save_geometric_means(geometric_means)
        
        logger.info("="*80)
        logger.info("✅ DATA PROCESSING COMPLETE")
        logger.info("="*80)
        logger.info("\nGenerated intermediate metric files:")
        logger.info("  - processed_bar_chart_metrics.csv")
        logger.info("  - processed_pareto_metrics.csv")
        logger.info("  - processed_hero_metrics.csv")
        logger.info("  - processed_geometric_means.csv")
        logger.info("\nReady for visualization stage.\n")

        # T2.5 fix round 2: the CSVs above are always written from whatever
        # DID parse (one bad file never hides the others), but the process
        # still exits non-zero on unallowed parse failures -- decided here,
        # in the CLI entry point, not inside the library function
        # parse_raw_stats() itself.
        if parse_failures and not args.allow_parse_failures:
            return False

        return True

    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}", exc_info=True)
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
