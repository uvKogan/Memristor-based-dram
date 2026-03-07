#!/usr/bin/env python3
import subprocess
import os
import argparse
import sys
from pathlib import Path

# --- PROJECT BASELINE DATA ---
PROJECT_NAME = "MBMM: ReRAM Hardware-to-System Research Pipeline"
LAST_UPDATED = "March 07, 2026"
CURRENT_STATUS = "STABLE - Pipeline fully modularized with parameter pass-through for traces/cycles."

def get_project_root():
    return Path(__file__).parent.absolute()

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
- [DONE] NVMain 'std::out_of_range' bit-slicing bug fixed via R:BK:CH:C mapping.
- [DONE] Pipeline fully automated through 5 stages.
- [DONE] Unified directory structure (configs/, results/, simulators/).

PIPELINE ARCHITECTURE:
Stage 1: Hardware Simulation (1_run_nvsim_hardware.py)
Stage 2: Metric Extraction (2_extract_hardware_metrics.py)
Stage 3: Config Generation (3_gen_nvmain_config.py)
Stage 4: System Simulation (4_execute_simulation.py)
Stage 5: Final Report (5_summary_report.py)

IMPORTANT INFO:
- Trace Format: 5-column hexadecimal (Cycle R/W 0xAddr 0xData ThreadID).
- Geometry: Fixed 65536 Rows/1024 Cols to satisfy NVMain address translation.
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
- Inputs: .cfg file (cell parameters) and .cell file (electrical properties).
- Typical Command: ./nvsim <config_file>
- Expectations: Requires high electrical convergence; outputs results to stdout.

NVMAIN (System-Level):
- Purpose: Cycle-accurate memory controller and architecture simulator.
- Inputs: .config file (architecture settings) and .nvt file (memory trace).
- Typical Command: ./nvmain.fast <config> <trace> <cycles>
- Key Fix: AddressMappingScheme must provide enough bit-width for the trace address.
{'='*80}
"""
    print(sim_info)

def setup_args():
    parser = argparse.ArgumentParser(
        description=f"{PROJECT_NAME} - Master Controller",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    # Primary Functionality
    parser.add_argument("--models", nargs="+", help="Run the full pipeline for specific model names.")
    parser.add_argument("--all", action="store_true", help="Run the full pipeline for all models in configs/.")
    
    # NEW: Trace and Cycle pass-through arguments
    parser.add_argument("--trace", default="test_reram.nvt", help="Trace file to use for simulation (default: test_reram.nvt).")
    parser.add_argument("--cycles", type=int, default=50000, help="Simulation cycles (default: 50000).")
    
    # Documentation Flags
    parser.add_argument("--readme", action="store_true", help="Print project objectives, status, and history.")
    parser.add_argument("--sims", action="store_true", help="Detailed info on NVSim and NVMain usage.")
    parser.add_argument("--extended_help", action="store_true", help="Describe every sub-script in the pipeline.")
    
    # Custom Overrides
    parser.add_argument("--freq", type=int, default=800, help="Override target frequency in MHz (default: 800).")
    return parser.parse_args()

def run_pipeline(models, freq, trace, cycles):
    """Executes the 5-stage pipeline sequentially with parameter pass-through."""
    root = get_project_root()
    
    for model in models:
        print(f"\n\n{'#'*80}")
        print(f"### FULL PIPELINE EXECUTION: {model} | Trace: {trace}")
        print(f"{'#'*80}")
        
        try:
            # Stage 1: Hardware
            subprocess.run([sys.executable, "1_run_nvsim_hardware.py", "--models", f"configs/{model}.cfg"], check=True)
            
            # Stage 2: Extraction
            subprocess.run([sys.executable, "2_extract_hardware_metrics.py", "--all"], check=True)
            
            # Stage 3: Config Gen
            subprocess.run([sys.executable, "3_gen_nvmain_config.py", "--freq", str(freq)], check=True)
            
            # Stage 4: Simulation (Now with Trace and Cycle variables)
            subprocess.run([
                sys.executable, "4_execute_simulation.py", 
                "--models", model,
                "--trace", trace,
                "--cycles", str(cycles)
            ], check=True)
            
            # Stage 5: Report
            subprocess.run([sys.executable, "5_summary_report.py", "--latest"], check=True)
            
        except subprocess.CalledProcessError as e:
            print(f"\n[CRITICAL] Pipeline failed at Stage: {e.cmd}")
            break

def main():
    args = setup_args()
    
    if args.readme:
        print_readme()
        return
        
    if args.sims:
        print_simulator_info()
        return

    if args.extended_help:
        print("\nPIPELINE SUB-SCRIPT DOCUMENTATION:")
        scripts = ["1_run_nvsim_hardware.py", "2_extract_hardware_metrics.py", "3_gen_nvmain_config.py", "4_execute_simulation.py", "5_summary_report.py"]
        for s in scripts:
            print(f"\n--- {s} ---")
            subprocess.run([sys.executable, s, "--help"])
        return

    if args.models or args.all:
        root = get_project_root()
        target_models = args.models
        if args.all:
            target_models = [f.stem for f in (root / "configs").glob("*.cfg")]
        
        # Pass the trace and cycles into the execution loop
        run_pipeline(target_models, args.freq, args.trace, args.cycles)
    else:
        print(f"\n{PROJECT_NAME}")
        print("Use --help for usage, --readme for status, or --models to run.")

if __name__ == "__main__":
    main()