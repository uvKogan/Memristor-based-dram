#!/usr/bin/env python3
import subprocess
import os
import argparse
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
LAST_UPDATED = "March 17, 2026"
CURRENT_STATUS = "STABLE - Analytical MLC bypassing enabled to avoid NVSim overflow bugs."

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

def print_readme():
    """Project Status and Objective Tracker."""
    readme_text = f"""
{'='*80}
{PROJECT_NAME}
Last Updated: {LAST_UPDATED} | Status: {CURRENT_STATUS}
{'='*80}

OBJECTIVES:
1. Model ReRAM cell physics using NVSim at the 22nm LOP node.
2. Bridge hardware metrics into cycle-accurate system simulations using NVMain.
3. Analyze system performance (Latency, Power, Bandwidth) for different ReRAM techs.

PROJECT STATUS:
- [DONE] NVSim build repaired for C++11 compatibility.
- [DONE] NVMain deallocation fixed in FlipNWrite.cpp.
- [DONE] Analytical MLC Bridge implemented to bypass NVSim 22nm sensing bugs.
- [DONE] Split-view visualization for Latency and Power comparison.

PIPELINE ARCHITECTURE:
Stage 1: Hardware Simulation (1_run_nvsim_hardware.py) - Skipped for MLC/DRAM.
Stage 2: Metric Extraction (2_extract_hardware_metrics.py) - Programmatic SLC->MLC generation.
Stage 3: Config Generation (3_gen_nvmain_config.py)
Stage 4: System Simulation (4_execute_simulation.py)
Stage 5: Final Report (5_summary_report.py)
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
- Bypassing: Skipped for MLC due to 22nm sensing overflow bugs.

NVMAIN (System-Level):
- Purpose: Cycle-accurate memory controller and architecture simulator.
- MLC Implementation: Uses analytical multipliers (3x Read / 4x Write).
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
    parser.add_argument("--freq", type=int, default=800, help="Override target frequency in MHz.")
    parser.add_argument("--queue-size", type=int, default=32,
                        help="FRFCFS controller QueueSize passthrough to 3_gen_nvmain_config.py "
                             "(default: 32, NVMain's own hardcoded fallback).")
    parser.add_argument("--channels", type=int, choices=[1, 2], default=1,
                        help="Passthrough to 3_gen_nvmain_config.py --channels (default: 1).")
    parser.add_argument("--decoder", choices=["Default", "StartGap"], default="Default",
                        help="Passthrough to 3_gen_nvmain_config.py --decoder (default: Default).")
    parser.add_argument("--endurance-model", choices=["RowModel", "WordModel", "NullModel"],
                        default="RowModel",
                        help="Passthrough to 3_gen_nvmain_config.py --endurance-model "
                             "(default: RowModel).")
    parser.add_argument("--ddr5-model", choices=["DDR5_4800_DRAM_subchannel", "DDR5_4800_DRAM_64B"],
                        default="DDR5_4800_DRAM_subchannel",
                        help="DDR5 config to run natively (default: DDR5_4800_DRAM_subchannel). "
                             "Falls back to DDR5_4800_DRAM with a logged note until T2.4 "
                             "generates the DDR5_4800_DRAM_subchannel/_64B configs.")
    parser.add_argument("--silicon", action="store_true",
                        help="Also generate and run the T2.8 microsecond-silicon sensitivity "
                             "full-DIMM configs (3_gen_nvmain_config.py --silicon; model names "
                             "from its SILICON_TIMINGS table) through the same simulation call, "
                             "for every trace.")
    return parser.parse_args()

def run_pipeline(models, freq, trace, cycles, queue_size=32, window_ns=250000000,
                  channels=1, decoder="Default", endurance_model="RowModel"):
    """Executes the pipeline with conditional logic for MLC/DRAM tracks.

    `cycles`, if not None, overrides the --window-ns-derived per-model
    budget for every model (with a printed warning, since models with
    different CLK then see different trace time windows).
    """
    root = get_project_root()

    if cycles is not None:
        print(f"[WARNING] --cycles override set to {cycles}: every model uses this exact "
              f"CLK-cycle count instead of a matched --window-ns budget, so models with "
              f"different CLK values will see different trace time windows.")
    
    for model in models:
        print(f"\n\n{'#'*80}")
        print(f"### FULL PIPELINE EXECUTION: {model} | Trace: {trace}")
        print(f"{'#'*80}")
        
        # ARCHITECTURAL LOGIC: Identify tracks that bypass raw hardware simulation
        is_dram = "dram" in model.lower()
        is_mlc = "_mlc" in model.lower()
        
        try:
            # Stage 1: Hardware Simulation (Conditional)
            if is_dram or is_mlc:
                print(f">>> PROCESSING MODEL: {model}")
                print(f"    [SKIP] Stage 1: {'DRAM baseline' if is_dram else 'Analytical MLC'} detected. No NVSim phase required.")
            else:
                print(f">>> PROCESSING MODEL: {model}")
                print(f"    [1/5] Running NVSim Hardware Phase...")
                subprocess.run([sys.executable, "1_run_nvsim_hardware.py", "--models", f"configs/{model}.cfg"], check=True)
            
            # Stage 2: Extraction (Now performs programatic SLC->MLC generation)
            subprocess.run([sys.executable, "2_extract_hardware_metrics.py"], check=True)
            
            # Stage 3: Config Generation
            subprocess.run([
                sys.executable, "3_gen_nvmain_config.py",
                "--freq", str(freq), "--queue-size", str(queue_size),
                "--channels", str(channels), "--decoder", decoder,
                "--endurance-model", endurance_model, "--window-ns", str(window_ns)
            ], check=True)

            # --- THE PATCH: ARCHITECTURE LOOP ---
            # Define the 4 architectures generated by Step 3
            architectures = ["single", "8chip", "16chip", "full_dimm"]

            for arch in architectures:
                # Construct the specific system model name generated by Step 3
                sys_model = f"{model}_{arch}"
                print(f"\n>>> PROCESSING SYSTEM VARIANT: {sys_model}")

                # Verify the config exists before attempting simulation
                config_path = root / "simulators" / "nvmain" / "Config" / f"{sys_model}.config"
                if not config_path.exists():
                    print(f"    [!] Skipping {sys_model}: Config not found.")
                    continue

                # Per-model CLK-cycle budget for the matched window_ns trace window,
                # unless the caller passed an explicit cycles override.
                model_cycles = cycles if cycles is not None else cycles_for(sys_model, window_ns)

                # Stage 4: System Simulation (Iterates for all 4 architectures)
                subprocess.run([
                    sys.executable, "4_execute_simulation.py",
                    "--models", sys_model,  # Use the architecture-specific name here
                    "--trace", trace,
                    "--cycles", str(model_cycles)
                ], check=True)
            
            # Stage 5: Report Generation
            subprocess.run([sys.executable, "5_summary_report.py", "--latest"], check=True)
            
            # Archive old graphs before generating new metrics
            archive_old_graphs()
            
            # Stage 6: Centralized Metrics Processing (Single source of truth for all calculations)
            print("\n" + "="*80)
            print("STAGE 6: CENTRALIZED METRICS PROCESSING")
            print("="*80)
            
            print("\n[EXECUTION] Processing metrics and generating CSVs...")
            subprocess.run([sys.executable, "process_metrics.py"], check=True)
            
            # Stage 7: Triple-track Visualization (Bar charts + Pareto analysis + Hero graphs)
            print("\n" + "="*80)
            print("STAGE 7: TRIPLE-TRACK VISUALIZATION (Reading pre-calculated metrics)")
            print("="*80)
            
            print("\n[EXECUTION] Generating Diagnostic Bar Charts...")
            subprocess.run([sys.executable, "visualize_results.py"], check=False)
            
            print("\n[EXECUTION] Generating Pareto Frontiers...")
            subprocess.run([sys.executable, "visualize_pareto.py"], check=False)
            
            print("\n[EXECUTION] Generating Hero Graphs...")
            subprocess.run([sys.executable, "visualize_hero_graphs.py"], check=False)
            
            print("\n[EXECUTION] Stage 7 visualization complete")
            print("="*80)
            
        except subprocess.CalledProcessError as e:
            print(f"\n[CRITICAL] Pipeline failed at Stage: {e.cmd}")
            # Continue to next model instead of breaking the entire batch
            continue

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
        
        reram_bases = ["reram_22nm_1t1r_slc", "reram_22nm_selector_slc"]

        # DDR5: T2.4 generates the subchannel/64B configs; fall back to the
        # existing DDR5_4800_DRAM config until they exist. The 2D/3D DRAM
        # example configs are dropped from the default list (excluded from
        # every figure already); PCM stays.
        ddr5_config_path = root / "simulators" / "nvmain" / "Config" / f"{args.ddr5_model}.config"
        if ddr5_config_path.exists():
            ddr5_model_name = args.ddr5_model
        else:
            log_event(f"--ddr5-model config not found ({ddr5_config_path.name}); T2.4 has not "
                       f"generated it yet, falling back to DDR5_4800_DRAM", "WARNING")
            ddr5_model_name = "DDR5_4800_DRAM"
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

        try:
            log_event("=" * 80)
            log_event("STAGE 1 & 2: RERAM HARDWARE EXTRACTION (SLC & MLC)")
            log_event("=" * 80)
            execution_summary["stages_run"].append("Stage 1 & 2: RERAM Hardware Extraction")
            for base in reram_bases:
                log_event(f"Running NVSim for {base}")
                run_subprocess([sys.executable, "1_run_nvsim_hardware.py", "--models", f"configs/{base}.cfg"], f"NVSim {base}")
            
            log_event("Running metric extraction")
            run_subprocess([sys.executable, "2_extract_hardware_metrics.py"], "Hardware Metric Extraction")
            
            log_event("=" * 80)
            log_event("STAGE 3: ARCHITECTURE FACTORY (RERAM ONLY)")
            log_event("=" * 80)
            execution_summary["stages_run"].append("Stage 3: Architecture Factory")
            gen_config_cmd = [
                sys.executable, "3_gen_nvmain_config.py",
                "--freq", str(args.freq), "--queue-size", str(args.queue_size),
                "--channels", str(args.channels), "--decoder", args.decoder,
                "--endurance-model", args.endurance_model, "--window-ns", str(args.window_ns)
            ]
            if args.silicon:
                gen_config_cmd.append("--silicon")
            run_subprocess(gen_config_cmd, "Architecture Factory")
            
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

            # STAGE 4: LOOP THROUGH EACH TRACE
            for trace_file in args.trace:
                log_event("=" * 80)
                log_event(f"STAGE 4: UNIFIED SYSTEM SIMULATION - TRACE: {trace_file}")
                log_event("=" * 80)
                if trace_file not in execution_summary["stages_run"]:
                    execution_summary["stages_run"].append(f"Stage 4: System Simulation ({trace_file})")
                
                architectures = ["single", "8chip", "16chip", "full_dimm"]
                factory_bases = [
                    "reram_22nm_1t1r_slc", "reram_22nm_1t1r_mlc",
                    "reram_22nm_selector_slc", "reram_22nm_selector_mlc"
                ]
                
                for base in factory_bases:
                    for arch in architectures:
                        sys_model = f"{base}_{arch}"
                        
                        # THE HACK: Duplicate base NVSim configs for SLC so Stage 4 doesn't abort
                        if "slc" in base:
                            base_cfg = root / "configs" / f"{base}.cfg"
                            arch_cfg = root / "configs" / f"{sys_model}.cfg"
                            if base_cfg.exists() and not arch_cfg.exists():
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
                    for sys_model in silicon_models():
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