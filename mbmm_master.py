#!/usr/bin/env python3
import subprocess
import os
import argparse
import sys
import logging
from pathlib import Path
from datetime import datetime

# --- ARCHIVE OLD GRAPHS ---
def archive_old_graphs(output_dir="/home/yuvalk/MBMM/results/final_graphs"):
    """Archive existing .png and .pdf files before generating new plots."""
    import os
    import shutil
    from datetime import datetime
    from pathlib import Path
    
    output_path = Path(output_dir)
    if not output_path.exists():
        return  # No output dir yet, nothing to archive
    
    # Find all .png and .pdf files in output_dir and subdirectories
    graph_files = []
    for ext in ['*.png', '*.pdf']:
        graph_files.extend(output_path.rglob(ext))
    
    if not graph_files:
        return  # No old graphs to archive
    
    # Create archive folder with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = output_path.parent / f"archive_{timestamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    # Move all graph files to archive
    for graph_file in graph_files:
        relative_path = graph_file.relative_to(output_path)
        dest_file = archive_dir / relative_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(graph_file), str(dest_file))
        print(f"[ARCHIVE] Moved: {relative_path} → archive_{timestamp}/")
    
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
    parser.add_argument("--cycles", type=int, default=50000, help="Simulation cycles.")
    parser.add_argument("--readme", action="store_true", help="Print status and history.")
    parser.add_argument("--sims", action="store_true", help="Detailed info on simulators.")
    parser.add_argument("--extended_help", action="store_true", help="Describe every sub-script.")
    parser.add_argument("--freq", type=int, default=800, help="Override target frequency in MHz.")
    return parser.parse_args()

def run_pipeline(models, freq, trace, cycles):
    """Executes the pipeline with conditional logic for MLC/DRAM tracks."""
    root = get_project_root()
    
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
            subprocess.run([sys.executable, "3_gen_nvmain_config.py", "--freq", str(freq)], check=True)
            
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
                
                # Stage 4: System Simulation (Iterates for all 4 architectures)
                subprocess.run([
                    sys.executable, "4_execute_simulation.py", 
                    "--models", sys_model,  # Use the architecture-specific name here
                    "--trace", trace,
                    "--cycles", str(cycles)
                ], check=True)
            
            # Stage 5: Report Generation
            subprocess.run([sys.executable, "5_summary_report.py", "--latest"], check=True)
            
            # Stage 6: Triple-track Visualization (Diagnostic bar charts + Pareto analysis + Hero graphs)
            print("\n" + "="*80)
            print("STAGE 6: TRIPLE-TRACK VISUALIZATION")
            print("="*80)
            
            print("\n[EXECUTION] Generating Diagnostic Bar Charts...")
            subprocess.run([sys.executable, "visualize_results.py"], check=False)
            
            print("\n[EXECUTION] Generating Pareto Frontiers...")
            subprocess.run([sys.executable, "visualize_pareto.py"], check=False)
            
            print("\n[EXECUTION] Generating Hero Graphs...")
            subprocess.run([sys.executable, "visualize_hero_graphs.py"], check=False)
            
            print("\n[EXECUTION] Stage 6 visualization complete")
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
        dram_models = ["2D_DRAM_example", "3D_DRAM_example", "DDR5_4800_DRAM"]
        
        log_event(f"Starting pipeline execution with {len(args.trace)} trace(s): {', '.join(args.trace)}, cycles: {args.cycles}")
        
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
            run_subprocess([sys.executable, "3_gen_nvmain_config.py", "--freq", str(args.freq)], "Architecture Factory")
            
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
                        
                        log_event(f"Running RERAM variant: {sys_model} with {trace_file}")
                        success = run_subprocess([
                            sys.executable, "4_execute_simulation.py", 
                            "--models", sys_model, "--trace", trace_file, "--cycles", str(args.cycles)
                        ], f"System Simulation: {sys_model} ({trace_file})")
                        
                        if success:
                            execution_summary["models_completed"] += 1
                        else:
                            execution_summary["models_failed"] += 1
                            log_event(f"FAILED: {sys_model} ({trace_file})", "ERROR")
                            
                # Run DRAM natively for this trace
                for dram in dram_models:
                    log_event(f"Running NATIVE DRAM: {dram} with {trace_file}")
                    success = run_subprocess([
                        sys.executable, "4_execute_simulation.py", 
                        "--models", dram, "--trace", trace_file, "--cycles", str(args.cycles)
                    ], f"System Simulation: {dram} ({trace_file})")
                    
                    if success:
                        execution_summary["models_completed"] += 1
                    else:
                        execution_summary["models_failed"] += 1
                        log_event(f"FAILED: {dram} ({trace_file})", "ERROR")
            
            archive_old_graphs()

            log_event("=" * 80)
            log_event("STAGE 5 & 6: SUMMARY AND TRIPLE-TRACK VISUALIZATION")
            log_event("=" * 80)
            execution_summary["stages_run"].append("Stage 5 & 6: Summary & Triple-Track Visualization")
            
            run_subprocess([sys.executable, "5_summary_report.py"], "Summary Report Generation")
            
            # STAGE 6: TRIPLE-TRACK VISUALIZATION
            print("\n" + "="*80)
            print("STAGE 6: VISUALIZATION")
            print("="*80)
            
            print("\nGenerating Diagnostic Bar Charts...")
            subprocess.run(['python3', 'visualize_results.py'], check=True)
            
            print("\nGenerating Pareto Frontiers...")
            subprocess.run(['python3', 'visualize_pareto.py'], check=True)
            
            print("\nGenerating Hero Graphs...")
            subprocess.run(['python3', 'visualize_hero_graphs.py'], check=True)
            
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

if __name__ == "__main__":
    main()