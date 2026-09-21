#!/usr/bin/env python3
import subprocess
import os
import argparse
import filecmp
import hashlib
import json
import sys
import logging
import importlib.util
from pathlib import Path
from datetime import datetime

# --- ARCHIVE OLD GRAPHS, LOGS, AND METRICS ---
def archive_old_graphs(output_dir="/home/yuvalk/MBMM/results/final_graphs",
                       logs_dir="/home/yuvalk/MBMM/results/logs",
                       metrics_dir="/home/yuvalk/MBMM/results"):
    """Archive existing .png/.pdf files, .log files, and processed_*.csv files before generating new plots."""
    import os
    import shutil
    from datetime import datetime
    from pathlib import Path
    
    output_path = Path(output_dir)
    logs_path = Path(logs_dir)
    metrics_path = Path(metrics_dir)
    
    # Collect files to archive
    files_to_archive = []
    
    # Find all .png and .pdf files in output_dir and subdirectories
    for ext in ['*.png', '*.pdf']:
        files_to_archive.extend(output_path.rglob(ext))
    
    # Find all .log files in logs directory
    if logs_path.exists():
        files_to_archive.extend(logs_path.glob('*.log'))
    
    # Find all processed_*.csv files in metrics directory
    files_to_archive.extend(metrics_path.glob('processed_*.csv'))
    
    if not files_to_archive:
        return  # Nothing to archive
    
    # Create archive folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = output_path.parent / f"archive_{timestamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories in archive for organization
    (archive_dir / "graphs").mkdir(exist_ok=True)
    (archive_dir / "logs").mkdir(exist_ok=True)
    (archive_dir / "metrics").mkdir(exist_ok=True)
    
    # Move all files to archive with proper organization
    for file_to_move in files_to_archive:
        try:
            if file_to_move.suffix in ['.png', '.pdf']:
                # Graph files with directory structure
                relative_path = file_to_move.relative_to(output_path)
                dest_file = archive_dir / "graphs" / relative_path
                dest_file.parent.mkdir(parents=True, exist_ok=True)
            elif file_to_move.suffix == '.log':
                # Log files to logs subdirectory
                dest_file = archive_dir / "logs" / file_to_move.name
            elif file_to_move.suffix == '.csv':
                # CSV files to metrics subdirectory
                dest_file = archive_dir / "metrics" / file_to_move.name
            else:
                continue
            
            shutil.move(str(file_to_move), str(dest_file))
            print(f"[ARCHIVE] Moved: {file_to_move.name} → archive_{timestamp}/")
        except Exception as e:
            print(f"[ARCHIVE] Warning: Could not move {file_to_move.name}: {e}")
    
    print(f"[ARCHIVE] Created archive folder: {archive_dir.name}\n")

# --- PROJECT BASELINE DATA ---
PROJECT_NAME = "MBMM: ReRAM Hardware-to-System Research Pipeline"
LAST_UPDATED = "September 21, 2026"
CURRENT_STATUS = ("STABLE - 2026-09 revision: forced 2048x2048 mux-64 organization, "
                  "matched 250 ms window, MLC derived analytically from the SLC NVSim run.")

# Global tracking
execution_log = []
execution_errors = []
execution_summary = {
    "stages_run": [], 
    "models_completed": 0, 
    "models_failed": 0,
    "graph_dirs": [],
    "log_file": None
}

def get_project_root():
    return Path(__file__).parent.absolute()

RERAM_STAGE1_BASES_2048 = ["reram_22nm_1t1r_slc", "reram_22nm_selector_slc"]
RERAM_STAGE1_BASES_1024 = ["reram_22nm_1t1r_slc_1024", "reram_22nm_selector_slc_1024"]

RERAM_FACTORY_BASES_2048 = [
    "reram_22nm_1t1r_slc", "reram_22nm_1t1r_mlc",
    "reram_22nm_selector_slc", "reram_22nm_selector_mlc",
]
RERAM_FACTORY_BASES_1024 = [
    "reram_22nm_1t1r_1024_slc", "reram_22nm_1t1r_1024_mlc",
    "reram_22nm_selector_1024_slc", "reram_22nm_selector_1024_mlc",
]


def reram_stage1_bases(organization=2048):
    """SLC base .cfg stems (configs/<stem>.cfg) that Stage 1/2 run NVSim on
    for `organization` (T5.1 step 2, organization axis: 2048 default /
    1024 sensitivity -- configs/reram_22nm_*_slc_1024.cfg, -ForceBank 32x8,
    1x8). MLC is derived analytically from the SLC NVSim run (Stage 2), so
    it never has its own Stage-1 base cfg at either organization.

    Pure / testable without running anything: the default (2048) list is
    byte-for-byte the original hardcoded list.
    """
    if organization == 1024:
        return list(RERAM_STAGE1_BASES_1024)
    return list(RERAM_STAGE1_BASES_2048)


def reram_factory_bases(organization=2048):
    """hardware_metrics.json base keys (i.e. post-2_extract_hardware_metrics.py
    naming) that Stage 4 iterates over for `organization`.

    2_extract_hardware_metrics.py derives a result file's base key as
    `stem.replace("_results", "").replace("_slc", "")`, then appends
    "_slc"/"_mlc" back for the two tracks. For a Stage-1 base
    "reram_22nm_1t1r_slc_1024" that yields base "reram_22nm_1t1r_1024" and
    then keys "reram_22nm_1t1r_1024_slc" / "reram_22nm_1t1r_1024_mlc" -- the
    "_1024" and "_slc"/"_mlc" tokens flip order between Stage 1 (cfg
    filename) and Stage 4 (hardware_metrics.json key / NVMain config name).
    This is deliberate, not a bug to fix here: it is also what keeps a 1024
    key from ever being a startswith() match on a 2048 prefix in
    process_metrics.py's RERAM_KEY_PREFIX lookup (they would collide if the
    order were reversed to "_slc_1024").

    Pure / testable without running anything: the default (2048) list is
    byte-for-byte the original hardcoded list.
    """
    if organization == 1024:
        return list(RERAM_FACTORY_BASES_1024)
    return list(RERAM_FACTORY_BASES_2048)


def should_duplicate_stage1_cfg(organization):
    """Whether Stage 4's per-architecture SLC cfg duplication ("THE HACK": a
    redundant NVSim re-verification of the forced organization, once per
    architecture) applies for `organization`.

    2048 (default, unchanged): the factory-base name equals the real Stage-1
    cfg stem, so configs/<base>.cfg can be duplicated straight to
    configs/<base>_<arch>.cfg and 4_execute_simulation.py's own NVSim call
    re-checks the forced organization on it.

    1024: the factory-base name ("reram_22nm_1t1r_1024_slc") and the real
    Stage-1 cfg stem ("reram_22nm_1t1r_slc_1024") disagree in "_1024"/"_slc"
    order (see reram_factory_bases' docstring), and
    nvsim_common.SENSITIVITY_1024_RE requires "_1024" to be the LAST token
    (optionally followed only by an architecture suffix) to recognize a cfg
    as the 1024 sensitivity organization -- a cfg named
    "reram_22nm_1t1r_1024_slc_full_dimm.cfg" would not match it and would be
    gated against the WRONG (2048) organization. Rather than special-case
    that regex for a duplicate cfg this project does not actually need
    (Stage 3 already generated a correct, already-organization-gated NVMain
    config for every 1024 architecture directly from the Stage-1 SLC base's
    own hardware_metrics.json entry), Stage 4 skips the duplicate for 1024:
    4_execute_simulation.py's skip_nvsim() then classifies each 1024 SLC
    architecture variant as "Native NVMain-only model" (no
    configs/<model>.cfg present) and goes straight to Phase 2 (NVMain) --
    exactly how every MLC variant, at either organization, has always been
    handled.
    """
    return organization == 2048


def silicon_models():
    """T2.8 sys-model names for the microsecond-silicon sensitivity configs.

    Read from 3_gen_nvmain_config.py's SILICON_TIMINGS table (via its
    silicon_model_names() helper), loaded with importlib.util.spec_from_file_location
    -- the same pattern tests/test_gen_nvmain_config.py uses to import this
    digit-prefixed script -- instead of duplicating the model-name list here.
    """
    root = get_project_root()
    spec = importlib.util.spec_from_file_location(
        "gen_nvmain_config_for_master", root / "3_gen_nvmain_config.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.silicon_model_names()

def cycles_for(model_name, window_ns, config_dir=None):
    """Per-model CLK-cycle budget for a matched window_ns trace window.

    NVMain's traceSim/traceMain.cpp (lines ~195-196) scales the --cycles
    argument by CPUFreq/CLK internally, so the value handed to
    4_execute_simulation.py's --cycles must already be expressed in the
    model's own memory-clock (CLK) cycles, not wall time. A window of
    window_ns nanoseconds is therefore:

        ceil(window_ns * CLK_MHz / 1000)

    computed with exact integer ceiling division (no float rounding).
    CLK is read from the "CLK <n>" line of the model's NVMain config
    (simulators/nvmain/Config/<model_name>.config by default) and must be an
    integer MHz value. Every model then admits the identical trace window
    regardless of its own CLK.
    """
    if config_dir is None:
        config_dir = get_project_root() / "simulators" / "nvmain" / "Config"
    config_dir = Path(config_dir)
    config_path = config_dir / f"{model_name}.config"

    if not config_path.exists():
        raise FileNotFoundError(
            f"cycles_for: no config found for model '{model_name}' at {config_path}"
        )

    clk_mhz = None
    with open(config_path) as f:
        for line in f:
            parts = line.split()
            if parts and parts[0] == "CLK":
                if len(parts) < 2:
                    raise ValueError(
                        f"cycles_for: malformed 'CLK' line in {config_path}: {line.strip()!r}"
                    )
                clk_str = parts[1]
                try:
                    clk_mhz = int(clk_str)
                except ValueError:
                    raise ValueError(
                        f"cycles_for: CLK value in {config_path} is not an integer: {clk_str!r}"
                    )
                break

    if clk_mhz is None:
        raise ValueError(
            f"cycles_for: no 'CLK' line found in {config_path}"
        )

    return -(-int(window_ns) * clk_mhz // 1000)

def setup_logging():
    """Setup logging to file (overwrites on each run)."""
    root = get_project_root()
    log_dir = root / "results"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "mbmm_execution.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)s | %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w')
        ],
        force=True
    )
    return log_file

def log_event(message, level="INFO"):
    """Log message to file and execution log."""
    execution_log.append(f"[{level}] {message}")
    if level == "INFO":
        logging.info(message)
    elif level == "ERROR":
        logging.error(message)
        execution_errors.append(message)
    elif level == "WARNING":
        logging.warning(message)

def run_subprocess(cmd, description=""):
    """Run subprocess, capture output, log it, and return success status."""
    log_event(f"Executing: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        # Log captured output
        if result.stdout:
            logging.info(f"--- STDOUT: {description} ---")
            logging.info(result.stdout)
        if result.stderr:
            logging.warning(f"--- STDERR: {description} ---")
            logging.warning(result.stderr)
        
        if result.returncode != 0:
            log_event(f"Command failed with exit code {result.returncode}: {description}", "ERROR")
            return False
        return True
    except subprocess.TimeoutExpired:
        log_event(f"Command timed out: {description}", "ERROR")
        return False
    except Exception as e:
        log_event(f"Command error: {str(e)}", "ERROR")
        return False

def abort_before_stage4(reason):
    """Log `reason` as an ERROR, print it, and return the master's exit code 1.

    I5 (final review 2026-09): Stages 1 to 3 have no safe "carry on" -- every
    one of them feeds Stage 4 through a SHARED file (results/hardware_metrics.json,
    simulators/nvmain/Config/*.config) that still holds the previous run's
    contents when the stage fails. Same shape as the live-config divergence
    check, which was already fail-fast.
    """
    log_event(reason + " Aborting before Stage 4 (fail fast).", "ERROR")
    print(f"\n[CRITICAL] {reason} Aborting before Stage 4.")
    return 1


# Generated NVMain configs are named "<hardware-metrics base>_<architecture>.config".
# The four architectures are the only suffixes 3_gen_nvmain_config.py ever writes
# (including the T2.8 silicon pair, which is always full_dimm), so this pattern
# matches every generated file and no static tracked one: configs/*.config (the
# two DDR5 baselines, checked by tools/check_live_configs.py),
# pcm_microsoft_2009.config, the upstream NVMain examples and the four old
# hand-written reram_*.config stubs all lack an architecture suffix.
GENERATED_CONFIG_SUFFIXES = ("_single", "_8chip", "_16chip", "_full_dimm")


def is_generated_reram_config(path):
    """True if `path` is an NVMain config 3_gen_nvmain_config.py generates."""
    name = Path(path).name
    if not name.startswith("reram") or not name.endswith(".config"):
        return False
    return Path(name).stem.endswith(GENERATED_CONFIG_SUFFIXES)


def stash_generated_reram_configs(config_dir, stash_root, timestamp=None):
    """Move every generated ReRAM/silicon config out of `config_dir` into a new
    timestamped folder under `stash_root`. Returns (moved_names, stash_dir).

    I6 (final review 2026-09): simulators/nvmain/Config/ is shared between runs
    and is not cleared, so a run inherited every generated config an earlier run
    with different flags had left there -- the live directory held eight
    `reram_22nm_*_1024_*.config` files from an organization-1024 sensitivity run
    while the primary configs sat beside them. Nothing was mixed in the frozen
    datasets, because Stage 4 iterates a fixed model list, but the directory
    could not tell anyone which run wrote what.

    The rule chosen (smallest one that makes Stage 4's set exactly Stage 3's
    set of THIS run): move the generated configs aside, regenerate, and refuse
    in Stage 4 to simulate any generated model that is not in this run's Stage-3
    manifest. Moved, never deleted, and only files matching
    is_generated_reram_config(): the tracked configs/*.config copies that
    tools/check_live_configs.py compares are static DDR5 files with no
    architecture suffix and are never touched, so that tool keeps passing.
    """
    import shutil
    config_dir = Path(config_dir)
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stash_dir = Path(stash_root) / timestamp

    moved = []
    for cfg in sorted(config_dir.glob("*.config")):
        if not is_generated_reram_config(cfg):
            continue
        stash_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(cfg), str(stash_dir / cfg.name))
        moved.append(cfg.name)
    return moved, stash_dir


# Everything a previous run leaves in results/system. Explicit patterns, not
# one glob, because "stats_*.out" does not match "stats_*.out.partial".
PREVIOUS_RUN_PATTERNS = ("stats_*.out", "stats_*.out.partial", "stats_*.out.failed",
                         "stats_*.out.superseded_*", "run_manifest.json")


def stash_previous_stats(sys_results_dir, timestamp=None):
    """Move a previous run's outputs out of `sys_results_dir` into a timestamped
    sibling folder. Returns (moved_names, destination).

    F2 fix round 1 (review Important-1): results/system was never cleared
    between master runs. Two runs with different flags and different traces (so
    no filename collision) left one folder holding both runs' stats files and
    only the second run's manifest, and process_metrics.py would then stamp all
    of them with the second run's flags. The manifest's own
    `expected_stats_files` list closes that on the reading side; this closes it
    on the writing side, so a run's folder holds exactly that run.

    Moved, never deleted: the destination is `<dir>_previous_<timestamp>` beside
    the directory itself, so the previous run's data stays reachable.
    """
    import shutil
    sys_results_dir = Path(sys_results_dir)
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destination = sys_results_dir.parent / f"{sys_results_dir.name}_previous_{timestamp}"

    moved = []
    if sys_results_dir.is_dir():
        for pattern in PREVIOUS_RUN_PATTERNS:
            for path in sorted(sys_results_dir.glob(pattern)):
                if not path.is_file():
                    continue
                destination.mkdir(parents=True, exist_ok=True)
                shutil.move(str(path), str(destination / path.name))
                moved.append(path.name)
    return sorted(moved), destination


def expected_stats_filenames(models, traces):
    """The stats filenames Stage 4 will write for `models` x `traces`.

    4_execute_simulation.py names them `stats_<model>_<trace stem>.out`, so this
    mirrors that one rule in one place. Listed in the run manifest so
    process_metrics.py can tell this run's outputs from anything else that ends
    up in the same directory.
    """
    return sorted(f"stats_{model}_{Path(trace).stem}.out"
                  for model in models for trace in traces)


def read_stage3_generated_models(manifest_path):
    """Return the set of model names 3_gen_nvmain_config.py wrote in this run.

    Raises OSError if the manifest is absent (Stage 3 exited 0 without writing
    one, which cannot happen when the master passes --manifest-out) and
    ValueError if it is empty or malformed.
    """
    with open(manifest_path) as f:
        data = json.load(f)
    models = data.get("generated_models")
    if not models:
        raise ValueError(f"{manifest_path} lists no generated models")
    return set(models)


def sha256_of(path):
    """Hex sha256 of a file, or None if it cannot be read."""
    try:
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(1 << 16), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def git_provenance(repo_dir):
    """{'commit': <sha or None>, 'dirty': <bool or None>} for `repo_dir`.

    Read-only git calls only (`rev-parse HEAD`, `status --porcelain`). Returns
    None values rather than raising when the directory is not a git repository
    or git is unavailable: provenance that cannot be read must be recorded as
    unknown, not fabricated and not fatal.
    """
    def _git(*a):
        try:
            r = subprocess.run(["git", "-C", str(repo_dir), *a],
                               capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            return None
        if r.returncode != 0:
            return None
        return r.stdout.strip()

    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain")
    return {"commit": commit,
            "dirty": None if status is None else bool(status.strip())}


def trace_sidecar_info(root, trace_file):
    """Locate `trace_file` and read its provenance sidecar's checksum(s), if any.

    The trace parsers write a `<trace>.sidecar.json` next to the trace
    (parse_gem5_memctrl.py / parse_trace.py); tools/validate_trace.py reads it.
    Only the checksum-bearing fields are copied here (`source.csv_sha256` for a
    SCALE-Sim trace, `source.raw_log_sha256_first_1mb` for a gem5 one), so the
    manifest says WHICH trace bytes were simulated, not just which filename.

    The trace itself is NOT hashed: these files run to gigabytes (stream.nvt is
    7.4 GB), so hashing one on every run would cost minutes. Size and mtime,
    plus the sidecar's own source checksum and record counts, identify it.
    """
    info = {"trace": trace_file, "path": None, "size_bytes": None, "mtime": None,
            "sidecar": None, "sidecar_checksums": None, "sidecar_records": None}
    candidates = [Path(trace_file),
                  root / "benchmarks" / trace_file,
                  root / "simulators" / "nvmain" / "Tests" / "Traces" / trace_file]
    for cand in candidates:
        if not cand.exists():
            continue
        info["path"] = str(cand)
        try:
            st = cand.stat()
            info["size_bytes"] = st.st_size
            info["mtime"] = datetime.fromtimestamp(st.st_mtime).isoformat()
        except OSError:
            pass
        sidecar = Path(str(cand) + ".sidecar.json")
        if sidecar.exists():
            info["sidecar"] = str(sidecar)
            try:
                with open(sidecar) as f:
                    meta = json.load(f)
            except (OSError, ValueError):
                break
            source = meta.get("source", {})
            checksums = {k: v for k, v in source.items() if "sha256" in k.lower()}
            info["sidecar_checksums"] = checksums or None
            info["sidecar_records"] = {
                k: meta[k] for k in ("records", "records_written", "reads", "writes")
                if k in meta} or None
        break
    return info


def write_run_manifest(manifest_path, args, root, models_to_simulate, config_dir,
                       generated_models, ddr5_model_name):
    """Write results/system/run_manifest.json at the start of Stage 4.

    I6 (final review 2026-09): nothing in a stats filename or a processed CSV
    said which flags produced it, and the master's own defaults (channels 1,
    decoder Default) differ from the primary run's (2 / StartGap), so
    `mbmm_master.py --all` with no flags silently regenerated the shared Config
    directory in a non-primary state. This manifest is written next to the stats
    it describes, before the first simulation, and process_metrics.py carries
    its key flags into every CSV as Run_* columns.
    """
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    hw_metrics_path = root / "results" / "hardware_metrics.json"
    manifest = {
        "schema": "mbmm_run_manifest/1",
        "command_line": [sys.executable] + sys.argv,
        "date": datetime.now().astimezone().isoformat(),
        "project_root": str(root),
        "git": {
            "superproject": git_provenance(root),
            "simulators/nvmain": git_provenance(root / "simulators" / "nvmain"),
            "simulators/nvsim": git_provenance(root / "simulators" / "nvsim"),
        },
        "flags": {
            "window_ns": args.window_ns,
            "cycles_override": args.cycles,
            "channels": args.channels,
            "decoder": args.decoder,
            "endurance_model": args.endurance_model,
            "ddr5_model": ddr5_model_name,
            "silicon": bool(args.silicon),
            "organization": args.organization,
            "queue_size": args.queue_size,
            "freq_mhz": args.freq,
        },
        "traces": [trace_sidecar_info(root, t) for t in args.trace],
        # F2 fix round 1 (review Important-1): the stats files THIS run is
        # expected to produce. process_metrics.py gives this manifest's Run_*
        # values only to files on this list; anything else in the same
        # directory belongs to another run and is labelled "unknown".
        "expected_stats_files": expected_stats_filenames(models_to_simulate, args.trace),
        "hardware_metrics": {
            "path": str(hw_metrics_path),
            "sha256": sha256_of(hw_metrics_path),
        },
        "stage3_generated_models": sorted(generated_models),
        "configs": {},
    }
    for model in sorted(models_to_simulate):
        cfg = Path(config_dir) / f"{model}.config"
        manifest["configs"][model] = {
            "path": str(cfg),
            "sha256": sha256_of(cfg),
            "generated_this_run": model in generated_models,
        }

    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=4)
    return manifest


def print_readme():
    """Project Status and Objective Tracker."""
    readme_text = f"""
{'='*80}
{PROJECT_NAME}
Last Updated: {LAST_UPDATED} | Status: {CURRENT_STATUS}
{'='*80}

OBJECTIVES:
1. Model ReRAM cell physics using NVSim at the 22nm LOP node, at a forced
   2048x2048 mux-64 subarray organization.
2. Bridge hardware metrics into cycle-accurate system simulations using NVMain.
3. Analyze system performance (Latency, Power, Bandwidth) for different ReRAM techs
   against a DDR5-4800 and a legacy PCM baseline, over a matched time window.

PROJECT STATUS (2026-09 revision):
- [DONE] NVSim build repaired for C++11 compatibility.
- [DONE] NVMain deallocation fixed in FlipNWrite.cpp.
- [DONE] Analytical MLC bridge: the MLC track is derived from the SLC NVSim run by
        published multipliers instead of a separate NVSim run (see --sims).
- [DONE] Forced organization gate: an NVSim run that silently explores its own
        organization fails the stage (nvsim_common.check_forced_organization).
- [DONE] Matched window: --window-ns is converted per model into its own CLK-cycle
        budget, so every technology admits the same slice of trace time.
- [DONE] Split-view visualization for Latency and Power comparison.
- [DONE] Every stage fails loudly: stages 1 to 3 abort the run before Stage 4, and
        Stage 4 refuses to simulate a config this run's Stage 3 did not generate.

PIPELINE ARCHITECTURE:
Stage 1: Hardware Simulation (1_run_nvsim_hardware.py) - Skipped for MLC/DRAM.
Stage 2: Metric Extraction (2_extract_hardware_metrics.py) - Programmatic SLC->MLC generation.
Stage 3: Config Generation (3_gen_nvmain_config.py) - ReRAM/silicon configs only.
Stage 4: System Simulation (4_execute_simulation.py) - writes results/system/run_manifest.json first.
Stage 5: Final Report (5_summary_report.py)
Stage 6: Metrics Processing (process_metrics.py) - the processed_*.csv files.
Stage 7: Visualization (visualize_results/pareto/hero_graphs.py)

NOT run by this master (so guardrail 2 does not cover them): visualize_slides.py,
endurance_sensitivity.py, selector_layer.py, tools/aggregate_wear.py.
{'='*80}
"""
    print(readme_text)

def print_simulator_info():
    """Documentation for NVSim and NVMain."""
    sim_info = f"""
{'='*80}
SIMULATOR KNOWLEDGE BASE
{'='*80}

NVSIM (Hardware-Level):
- Purpose: Models area, timing, and energy of non-volatile memory chips.
- Organization: every ReRAM .cfg forces a 2048 x 2048 subarray at Senseamp Mux 64
  (-ForceBank 16x4 / 1x4, -ForceMat 4x1, -ForceMuxSenseAmp 64), and a run that does
  not report that organization literally FAILS the stage
  (nvsim_common.check_forced_organization). configs/reram_22nm_*_slc_1024.cfg are
  the 1024 x 1024 sensitivity variants (-ForceBank 32x8, 1x8), selected with
  --organization 1024.
- Bypassing: skipped for MLC due to 22nm sensing overflow bugs; the MLC track is
  derived from the SLC result in 2_extract_hardware_metrics.py.

MLC DERIVATION (2_extract_hardware_metrics.py apply_mlc_penalty):
- Read latency x1.5, write latency x3.263, read energy x1.1, write energy x3.0,
  capacity x2. Sources: Levy et al., IEEE JSSC 2024 (DOI 10.1109/JSSC.2024.3387566),
  Section V.A / Abstract, for the three latency/write figures; Upton et al.,
  ESSCIRC 2023, Table I, for read energy. The retired "3x Read / 4x Write"
  multipliers were unsourced (book audit items 13-14) and are NOT used.

NVMAIN (System-Level):
- Purpose: Cycle-accurate memory controller and architecture simulator.
- Config sources: the ReRAM and T2.8 silicon configs are GENERATED per run by
  3_gen_nvmain_config.py; the DDR5 and PCM configs are static files (configs/*.config
  and simulators/nvmain/Config/pcm_microsoft_2009.config), so generator flags such as
  --queue-size do not reach them.
- Two upstream caveats a reader of raw stats must know: DDR5 (EnergyModel current)
  prints rank backgroundPower PER DEVICE, corrected in post-processing by
  process_metrics.py; never quote a current-mode rank's raw backgroundPower or
  totalEnergy. See simulators/nvmain/CLAUDE.md items 6 and 7.
{'='*80}
"""
    print(sim_info)

def setup_args():
    parser = argparse.ArgumentParser(
        description=f"{PROJECT_NAME} - Master Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--models", nargs="+", help="Run the full pipeline for specific model names.")
    parser.add_argument("--all", action="store_true", help="Run the full pipeline for all models in configs/.")
    parser.add_argument("--trace", nargs="+", default=["test_reram.nvt"], help="Trace file(s) to use for simulation.")
    parser.add_argument("--cycles", type=int, default=None,
                        help="Override: use this exact CLK-cycle count for every model instead "
                             "of a --window-ns-derived per-model budget. Since CLK differs by "
                             "model, this means models then see different trace time windows "
                             "(a warning is printed when this is set).")
    parser.add_argument("--window-ns", type=int, default=250000000,
                        help="Matched simulation window in nanoseconds, converted per model "
                             "into a CLK-cycle budget via cycles_for() so every model admits "
                             "the identical trace window (default: 250000000). Ignored if "
                             "--cycles is set.")
    parser.add_argument("--readme", action="store_true", help="Print status and history.")
    parser.add_argument("--sims", action="store_true", help="Detailed info on simulators.")
    parser.add_argument("--extended_help", action="store_true", help="Describe every sub-script.")
    parser.add_argument("--freq", type=int, default=800,
                        help="Interface clock (CLK) in MHz for the GENERATED ReRAM/silicon "
                             "configs (default: 800). The DDR5 (CLK 2400) and PCM (CLK 400) "
                             "configs are static files and are unaffected; the per-model cycle "
                             "budget for --window-ns is derived from each config's own CLK.")
    # M4 / I6 (final review 2026-09): these five reach the GENERATED ReRAM and
    # silicon configs only. The DDR5 and PCM configs are static tracked files,
    # so none of them changes the baselines. Note also that the defaults below
    # are NOT the primary matrix's settings (the 2026-09 primary run used
    # --channels 2 --decoder StartGap): `mbmm_master.py --all` with no flags is
    # a different experiment, and the run manifest records which one was run.
    parser.add_argument("--queue-size", type=int, default=32,
                        help="FRFCFS controller QueueSize passthrough to 3_gen_nvmain_config.py "
                             "(default: 32, NVMain's own hardcoded fallback). Reaches the "
                             "GENERATED ReRAM/silicon configs only: the DDR5 configs carry "
                             "ReadQueueSize/WriteQueueSize, which plain FRFCFS never reads, so "
                             "DDR5 and PCM always run at NVMain's hardcoded 32.")
    parser.add_argument("--channels", type=int, choices=[1, 2], default=1,
                        help="Passthrough to 3_gen_nvmain_config.py --channels (default: 1; the "
                             "2026-09 primary matrix used 2). Generated ReRAM/silicon configs "
                             "only; the DDR5 and PCM configs are static files.")
    parser.add_argument("--decoder", choices=["Default", "StartGap"], default="Default",
                        help="Passthrough to 3_gen_nvmain_config.py --decoder (default: Default; "
                             "the 2026-09 primary matrix used StartGap). Generated ReRAM/silicon "
                             "configs only.")
    parser.add_argument("--endurance-model", choices=["RowModel", "WordModel", "NullModel"],
                        default="RowModel",
                        help="Passthrough to 3_gen_nvmain_config.py --endurance-model "
                             "(default: RowModel). Generated ReRAM/silicon configs only.")
    parser.add_argument("--ddr5-model", choices=["DDR5_4800_DRAM_subchannel", "DDR5_4800_DRAM_64B"],
                        default="DDR5_4800_DRAM_subchannel",
                        help="DDR5 config to run natively (default: DDR5_4800_DRAM_subchannel, "
                             "the primary baseline: two 32-bit subchannels, 64 B per access). "
                             "DDR5_4800_DRAM_64B is the 64 B-bus cross-check. Both are static "
                             "tracked files under configs/, mirrored into "
                             "simulators/nvmain/Config/; the run aborts if the requested one is "
                             "missing (there is no fallback to the retired DDR5_4800_DRAM).")
    parser.add_argument("--silicon", action="store_true",
                        help="Also generate and run the T2.8 microsecond-silicon sensitivity "
                             "full-DIMM configs (3_gen_nvmain_config.py --silicon; model names "
                             "from its SILICON_TIMINGS table) through the same simulation call, "
                             "for every trace.")
    parser.add_argument("--organization", type=int, choices=[2048, 1024], default=2048,
                        help="ReRAM subarray organization (default: 2048, the forced "
                             "2048x2048 mux-64 baseline). 1024 runs the T5.1 step 2 "
                             "1024x1024 mux-64 sensitivity organization instead "
                             "(configs/reram_22nm_*_slc_1024.cfg, -ForceBank 32x8, 1x8) for "
                             "Stage 1 NVSim and all four Stage 4 ReRAM architectures/tracks "
                             "(SLC and MLC, 1T1R and 1S1R); DDR5 and PCM are unaffected. "
                             "Behavior at the default is byte-for-byte unchanged.")
    return parser.parse_args()

# Minor-3 (final review 2026-09): the module-level run_pipeline() helper that
# used to sit here was never called by anything (main() drives the pipeline
# directly, and nothing imported it). It also ran the three visualizers with
# check=False, so reviving it would have swallowed their failures. Removed.

def main():
    global execution_summary
    
    # Setup logging first
    log_file = setup_logging()
    execution_summary["log_file"] = log_file
    
    log_event(f"Starting {PROJECT_NAME}")
    log_event(f"Status: {CURRENT_STATUS}")
    
    args = setup_args()
    
    if args.readme:
        print_readme()
        return
        
    if args.sims:
        print_simulator_info()
        return

    if args.extended_help:
        log_event("Extended help requested")
        print("\nPIPELINE SUB-SCRIPT DOCUMENTATION:")
        scripts = ["1_run_nvsim_hardware.py", "2_extract_hardware_metrics.py", "3_gen_nvmain_config.py", "4_execute_simulation.py", "5_summary_report.py"]
        for s in scripts:
            print(f"\n--- {s} ---")
            run_subprocess([sys.executable, s, "--help"], s)
        return

    if args.models or args.all:
        import shutil # Required for copying the cfg files
        root = get_project_root()
        
        reram_bases = reram_stage1_bases(args.organization)

        # DDR5: T2.4's subchannel/64B configs are the only DDR5 baselines this
        # revision runs. I5 (final review 2026-09): the old silent fallback to
        # the retired legacy DDR5_4800_DRAM config produced a complete-looking
        # run against a DDR5 baseline nobody asked for (different BusWidth,
        # RANKS, tBURST and, since F4, different JEDEC write-path timings), with
        # only a WARNING in a log file that is overwritten on every run. A
        # missing requested config is now an error. The 2D/3D DRAM example
        # configs are dropped from the default list (excluded from every figure
        # already); PCM stays.
        ddr5_config_path = root / "simulators" / "nvmain" / "Config" / f"{args.ddr5_model}.config"
        if not ddr5_config_path.exists():
            log_event(f"--ddr5-model {args.ddr5_model} has no config at {ddr5_config_path}; "
                       f"aborting before any simulation. There is no fallback: running the "
                       f"legacy DDR5_4800_DRAM config instead would silently change the DDR5 "
                       f"baseline. Run tools/check_live_configs.py --sync, or pass a "
                       f"--ddr5-model whose config exists.", "ERROR")
            print(f"\n[CRITICAL] --ddr5-model config not found: {ddr5_config_path}; aborting.")
            return 1
        ddr5_model_name = args.ddr5_model
        dram_models = [ddr5_model_name, "pcm_microsoft_2009"]

        if args.cycles is not None:
            log_event(f"--cycles override set to {args.cycles}: every model uses this exact "
                       f"CLK-cycle count instead of a matched --window-ns budget, so models "
                       f"with different CLK values will see different trace time windows.",
                       "WARNING")
            log_event(f"Starting pipeline execution with {len(args.trace)} trace(s): "
                       f"{', '.join(args.trace)}, cycles (override): {args.cycles}")
        else:
            log_event(f"Starting pipeline execution with {len(args.trace)} trace(s): "
                       f"{', '.join(args.trace)}, window_ns: {args.window_ns} "
                       f"(per-model CLK-cycle budgets)")

        log_event(f"Organization: {args.organization}x{args.organization} subarrays"
                   + ("" if args.organization == 2048
                      else " (T5.1 step 2 sensitivity, not the primary matrix)"))

        try:
            log_event("=" * 80)
            log_event("STAGE 1 & 2: RERAM HARDWARE EXTRACTION (SLC & MLC)")
            log_event("=" * 80)
            execution_summary["stages_run"].append("Stage 1 & 2: RERAM Hardware Extraction")
            # I5 (final review 2026-09): a failed Stage 1, 2 or 3 used to be
            # logged and the run continued into Stage 4 on whatever configs
            # happened to be in simulators/nvmain/Config/ already. The run
            # exited 1 at the very end, but only after producing a full set of
            # stats, CSVs and figures from stale inputs. Every one of these now
            # aborts BEFORE Stage 4, in the same shape as the live-config
            # divergence check below.
            for base in reram_bases:
                log_event(f"Running NVSim for {base}")
                if not run_subprocess([sys.executable, "1_run_nvsim_hardware.py",
                                        "--models", f"configs/{base}.cfg"], f"NVSim {base}"):
                    return abort_before_stage4(
                        f"Stage 1 (NVSim) failed for {base}: the hardware metrics this run "
                        f"would be built from are stale or missing.")

            log_event("Running metric extraction")
            if not run_subprocess([sys.executable, "2_extract_hardware_metrics.py"],
                                   "Hardware Metric Extraction"):
                return abort_before_stage4(
                    "Stage 2 (hardware metric extraction) failed: results/hardware_metrics.json "
                    "was not rewritten, so Stage 3 would generate configs from a stale file.")

            log_event("=" * 80)
            log_event("STAGE 3: ARCHITECTURE FACTORY (RERAM ONLY)")
            log_event("=" * 80)
            execution_summary["stages_run"].append("Stage 3: Architecture Factory")

            # I6: move every generated ReRAM/silicon config aside (never
            # delete) before regenerating, so the live Config directory holds
            # exactly what THIS run's Stage 3 produced. See
            # stash_generated_reram_configs' docstring for the rule and why the
            # static tracked configs are untouched.
            stashed, stash_dir = stash_generated_reram_configs(
                root / "simulators" / "nvmain" / "Config",
                root / "results" / "_generated_configs_prev")
            if stashed:
                log_event(f"Moved {len(stashed)} generated ReRAM/silicon config(s) aside to "
                           f"{stash_dir} before regenerating (never deleted).")

            stage3_manifest = root / "results" / "stage3_generated_configs.json"
            if stage3_manifest.exists():
                stage3_manifest.unlink()
            gen_config_cmd = [
                sys.executable, "3_gen_nvmain_config.py",
                "--freq", str(args.freq), "--queue-size", str(args.queue_size),
                "--channels", str(args.channels), "--decoder", args.decoder,
                "--endurance-model", args.endurance_model, "--window-ns", str(args.window_ns),
                "--manifest-out", str(stage3_manifest),
            ]
            if args.silicon:
                gen_config_cmd.append("--silicon")
            if not run_subprocess(gen_config_cmd, "Architecture Factory"):
                return abort_before_stage4(
                    "Stage 3 (architecture factory) failed: the NVMain configs in "
                    "simulators/nvmain/Config/ are not this run's, so Stage 4 would simulate "
                    "something other than what was asked for.")

            try:
                generated_models = read_stage3_generated_models(stage3_manifest)
            except (OSError, ValueError) as e:
                return abort_before_stage4(f"Stage 3 manifest unusable: {e}")
            log_event(f"Stage 3 generated {len(generated_models)} config(s) in this run.")

            # STAGE 4: fail fast if the tracked configs/*.config files and the
            # live simulators/nvmain/Config/ copies have diverged (T2.4) --
            # every simulation below reads the live copy, so a silent
            # divergence there would simulate something other than what's
            # tracked/reviewed. Checked once, before any Stage 4 simulation
            # call, not per-trace.
            log_event("=" * 80)
            log_event("STAGE 4: LIVE-CONFIG DIVERGENCE CHECK")
            log_event("=" * 80)
            if not run_subprocess([sys.executable, "tools/check_live_configs.py"],
                                   "Live-config divergence check"):
                log_event("Tracked configs/*.config and simulators/nvmain/Config/ have "
                           "diverged; aborting before any Stage 4 simulation (fail fast). "
                           "Re-run tools/check_live_configs.py directly for the full diff, "
                           "or with --sync to repair.", "ERROR")
                print("\n[CRITICAL] Live-config divergence check failed; aborting.")
                return 1

            # I6: the exact model set Stage 4 will simulate, decided once,
            # before anything runs. Every ReRAM/silicon model here must have
            # been generated by THIS run's Stage 3; the two DDR5/PCM baselines
            # are static tracked files, not generated, and are exempt.
            architectures = ["single", "8chip", "16chip", "full_dimm"]
            factory_bases = reram_factory_bases(args.organization)
            reram_models = [f"{base}_{arch}" for base in factory_bases
                            for arch in architectures]
            silicon_model_list = silicon_models() if args.silicon else []
            models_to_simulate = reram_models + list(dram_models) + silicon_model_list

            stale = [m for m in reram_models + silicon_model_list
                     if m not in generated_models]
            if stale:
                return abort_before_stage4(
                    f"Stage 4 would simulate {len(stale)} config(s) this run's Stage 3 did "
                    f"not generate: {sorted(stale)}. simulators/nvmain/Config/ is shared "
                    f"between runs, so these would be another run's configs.")

            # I6 / F2 fix round 1: results/system must hold exactly one run's
            # output. Move any previous run's stats files and manifest aside
            # (never delete) before this run writes its own.
            sys_results_dir = root / "results" / "system"
            previous, previous_dir = stash_previous_stats(sys_results_dir)
            if previous:
                log_event(f"Moved {len(previous)} file(s) from a previous run out of "
                           f"{sys_results_dir} into {previous_dir} (never deleted); this "
                           f"run's results directory now holds only this run.")

            run_manifest_path = sys_results_dir / "run_manifest.json"
            manifest = write_run_manifest(
                run_manifest_path, args, root, models_to_simulate,
                root / "simulators" / "nvmain" / "Config",
                generated_models, ddr5_model_name)
            log_event(f"Wrote run manifest: {run_manifest_path} "
                       f"({len(manifest['configs'])} config sha256s, "
                       f"{len(manifest['traces'])} trace(s))")

            # STAGE 4: LOOP THROUGH EACH TRACE
            for trace_file in args.trace:
                log_event("=" * 80)
                log_event(f"STAGE 4: UNIFIED SYSTEM SIMULATION - TRACE: {trace_file}")
                log_event("=" * 80)
                if trace_file not in execution_summary["stages_run"]:
                    execution_summary["stages_run"].append(f"Stage 4: System Simulation ({trace_file})")

                for base in factory_bases:
                    for arch in architectures:
                        sys_model = f"{base}_{arch}"

                        # Per-architecture NVSim cfg duplicate. 4_execute_simulation.py's
                        # skip_nvsim() runs its NVSim re-verification phase for a model
                        # only when configs/<model>.cfg exists (otherwise the model is a
                        # "Native NVMain-only model" and goes straight to NVMain), so
                        # these copies are what keeps the forced-organization gate
                        # running once per architecture. Only at organization 2048 (see
                        # should_duplicate_stage1_cfg's docstring for why 1024 skips this
                        # and relies on the "Native NVMain-only" path instead).
                        #
                        # Minor-5 (final review 2026-09): the copy used to be made only
                        # `if not arch_cfg.exists()`, so an edit to a base cfg never
                        # reached the eight copies and the gate silently re-verified a
                        # retired organization. The copy is now refreshed whenever it
                        # differs from its base.
                        if should_duplicate_stage1_cfg(args.organization) and "slc" in base:
                            base_cfg = root / "configs" / f"{base}.cfg"
                            arch_cfg = root / "configs" / f"{sys_model}.cfg"
                            if base_cfg.exists() and not (
                                    arch_cfg.exists()
                                    and filecmp.cmp(base_cfg, arch_cfg, shallow=False)):
                                if arch_cfg.exists():
                                    log_event(f"Refreshing stale per-architecture cfg copy "
                                               f"{arch_cfg.name} from {base_cfg.name}")
                                shutil.copy(base_cfg, arch_cfg)

                        if args.cycles is not None:
                            model_cycles = args.cycles
                        else:
                            try:
                                model_cycles = cycles_for(sys_model, args.window_ns)
                            except (FileNotFoundError, ValueError) as e:
                                log_event(str(e), "ERROR")
                                execution_summary["models_failed"] += 1
                                continue

                        log_event(f"Running RERAM variant: {sys_model} with {trace_file} "
                                   f"(cycles={model_cycles})")
                        success = run_subprocess([
                            sys.executable, "4_execute_simulation.py",
                            "--models", sys_model, "--trace", trace_file, "--cycles", str(model_cycles)
                        ], f"System Simulation: {sys_model} ({trace_file})")

                        if success:
                            execution_summary["models_completed"] += 1
                        else:
                            execution_summary["models_failed"] += 1
                            log_event(f"FAILED: {sys_model} ({trace_file})", "ERROR")

                # Run DRAM (and PCM) natively for this trace
                for dram in dram_models:
                    if args.cycles is not None:
                        model_cycles = args.cycles
                    else:
                        try:
                            model_cycles = cycles_for(dram, args.window_ns)
                        except (FileNotFoundError, ValueError) as e:
                            log_event(str(e), "ERROR")
                            execution_summary["models_failed"] += 1
                            continue

                    log_event(f"Running NATIVE DRAM: {dram} with {trace_file} "
                               f"(cycles={model_cycles})")
                    success = run_subprocess([
                        sys.executable, "4_execute_simulation.py",
                        "--models", dram, "--trace", trace_file, "--cycles", str(model_cycles)
                    ], f"System Simulation: {dram} ({trace_file})")

                    if success:
                        execution_summary["models_completed"] += 1
                    else:
                        execution_summary["models_failed"] += 1
                        log_event(f"FAILED: {dram} ({trace_file})", "ERROR")

                # Silicon sensitivity configs (T2.8), only when --silicon is set.
                # Model names come from 3_gen_nvmain_config.py's SILICON_TIMINGS
                # table (silicon_models(), above) -- 3_gen_nvmain_config.py
                # --silicon (passed through above) writes them straight into
                # simulators/nvmain/Config/, the default cycles_for()/
                # 4_execute_simulation.py config directory, so no separate
                # configs/silicon/ glob or config_dir override is needed.
                if args.silicon:
                    for sys_model in silicon_model_list:
                        if args.cycles is not None:
                            model_cycles = args.cycles
                        else:
                            try:
                                model_cycles = cycles_for(sys_model, args.window_ns)
                            except (FileNotFoundError, ValueError) as e:
                                log_event(str(e), "ERROR")
                                execution_summary["models_failed"] += 1
                                continue

                        log_event(f"Running SILICON variant: {sys_model} with {trace_file} "
                                   f"(cycles={model_cycles})")
                        success = run_subprocess([
                            sys.executable, "4_execute_simulation.py",
                            "--models", sys_model, "--trace", trace_file, "--cycles", str(model_cycles)
                        ], f"System Simulation: {sys_model} ({trace_file})")

                        if success:
                            execution_summary["models_completed"] += 1
                        else:
                            execution_summary["models_failed"] += 1
                            log_event(f"FAILED: {sys_model} ({trace_file})", "ERROR")

            archive_old_graphs()

            log_event("=" * 80)
            log_event("STAGE 5 & 6: SUMMARY AND CENTRALIZED METRICS PROCESSING")
            log_event("=" * 80)
            execution_summary["stages_run"].append("Stage 5 & 6: Summary & Metrics Processing")
            
            run_subprocess([sys.executable, "5_summary_report.py"], "Summary Report Generation")
            
            # STAGE 6: CENTRALIZED METRICS PROCESSING
            print("\n" + "="*80)
            print("STAGE 6: CENTRALIZED METRICS PROCESSING")
            print("="*80)
            
            print("\nProcessing metrics and generating CSVs...")
            run_subprocess([sys.executable, "process_metrics.py"], "Centralized Metrics Processing")
            
            # STAGE 7: TRIPLE-TRACK VISUALIZATION
            print("\n" + "="*80)
            print("STAGE 7: TRIPLE-TRACK VISUALIZATION (Reading pre-calculated metrics)")
            print("="*80)
            execution_summary["stages_run"].append("Stage 7: Triple-Track Visualization")
            
            print("\nGenerating Diagnostic Bar Charts...")
            run_subprocess([sys.executable, "visualize_results.py"], "Bar Chart Visualization")
            
            print("\nGenerating Pareto Frontiers...")
            run_subprocess([sys.executable, "visualize_pareto.py"], "Pareto Visualization")
            
            print("\nGenerating Hero Graphs...")
            run_subprocess([sys.executable, "visualize_hero_graphs.py"], "Hero Graphs Visualization")
            
            log_event("Pipeline execution completed successfully")

            
            # Collect graph directories
            results_dir = root / "results"
            if results_dir.exists():
                for item in results_dir.iterdir():
                    if item.is_dir() and item.name not in ["hardware", "system", "unknown"]:
                        execution_summary["graph_dirs"].append(item)
            
        except Exception as e:
            log_event(f"Pipeline execution failed: {str(e)}", "ERROR")
        
    else:
        log_event(f"No execution mode selected")
    
    # Print final summary to terminal only
    print("\n" + "="*80)
    print("MBMM EXECUTION COMPLETE")
    print("="*80)
    print(f"\nLog File:")
    print(f"  {execution_summary['log_file']}")
    
    if execution_summary["graph_dirs"]:
        print(f"\nGenerated Result Directories:")
        for graph_dir in sorted(execution_summary["graph_dirs"]):
            print(f"  📊 {graph_dir}")
    
    print(f"\nExecution Summary:")
    print(f"  Stages Executed: {len(execution_summary['stages_run'])}")
    for stage in execution_summary["stages_run"]:
        print(f"    ✓ {stage}")
    
    print(f"\n  Models Processed:")
    print(f"    ✓ Completed: {execution_summary['models_completed']}")
    if execution_summary['models_failed'] > 0:
        print(f"    ✗ Failed: {execution_summary['models_failed']}")
    
    if execution_errors:
        print(f"\nErrors Encountered ({len(execution_errors)}):")
        for i, error in enumerate(execution_errors, 1):
            print(f"  {i}. {error}")
    else:
        print(f"\n✓ No errors encountered")

    print("="*80 + "\n")

    # Do not swallow failures: any logged ERROR (a failed subprocess, a model that
    # failed simulation, a cycles_for lookup failure, etc.) makes the master exit
    # non-zero, so CI/callers can tell a partially-failed run from a clean one.
    if execution_errors:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())