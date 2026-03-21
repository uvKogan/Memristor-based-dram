import subprocess
import os
import shutil
import argparse
import datetime
import sys
from pathlib import Path

def get_project_root():
    """Dynamically finds the MBMM project root directory."""
    return Path(__file__).parent.absolute()

def find_trace_path(root_dir, trace_arg):
    """Tries to find the trace file in multiple logical locations."""
    p = Path(trace_arg)
    if p.exists():
        return p
    p_bench = root_dir / "benchmarks" / trace_arg
    if p_bench.exists():
        return p_bench
    p_nvmain = root_dir / "simulators" / "nvmain" / "Tests" / "Traces" / trace_arg
    if p_nvmain.exists():
        return p_nvmain
    return None

def setup_args():
    parser = argparse.ArgumentParser(description="MBMM Step 4: Unified Execution Wrapper")
    parser.add_argument("--models", nargs="+", help="Model names without extensions.")
    parser.add_argument("--all", action="store_true", help="Run for all .cfg in configs/.")
    parser.add_argument("--trace", default="test_reram.nvt", help="Trace file name or path.")
    parser.add_argument("--cycles", type=int, default=50000, help="Simulation cycles.")
    return parser.parse_args()

def run_simulations():
    args = setup_args()
    root_dir = get_project_root()
    
    # Path Definitions
    config_dir = root_dir / "configs"
    hw_results_dir = root_dir / "results" / "hardware"
    sys_results_dir = root_dir / "results" / "system"
    nvsim_exe = root_dir / "simulators" / "nvsim" / "nvsim"
    nvmain_exe = root_dir / "simulators" / "nvmain" / "nvmain.fast"
    
    # 1. SEARCH FOR TRACE
    trace_path = find_trace_path(root_dir, args.trace)
    
    if trace_path is None:
        print(f"\n[CRITICAL ERROR] Trace file '{args.trace}' not found!")
        sys.exit(1)

    # 2. DEFINE FILENAME TAG
    trace_name = trace_path.stem 

    hw_results_dir.mkdir(parents=True, exist_ok=True)
    sys_results_dir.mkdir(parents=True, exist_ok=True)
    
    target_models = []
    if args.all:
        target_models = [f.stem for f in config_dir.glob("*.cfg")]
    elif args.models:
        target_models = args.models

    print("=" * 60)
    print("MBMM STEP 4: UNIFIED SIMULATION PIPELINE")
    print(f"Trace Found: {trace_path.name}")
    print(f"Max Cycles: {args.cycles}")
    print("=" * 60)

    # Sync .cell files for NVSim
    nvsim_bin_dir = nvsim_exe.parent
    for cell_file in config_dir.glob("*.cell"):
        shutil.copy(cell_file, nvsim_bin_dir)

    for model in target_models:
        print(f"\n>>> PROCESSING MODEL: {model}")
        
        # ARCHITECTURAL BYPASS LOGIC
        is_dram = "DRAM" in model.upper()
        is_mlc = "_mlc" in model.lower()
        
        # --- PHASE 1: NVSIM (Bypass for DRAM and Analytical MLC) ---
        if is_dram or is_mlc:
            print(f"    [SKIP] Phase 1: {'DRAM baseline' if is_dram else 'Analytical MLC'} detected. Using native/pre-generated timings.")
        else:
            nvsim_cfg = config_dir / f"{model}.cfg"
            if not nvsim_cfg.exists():
                print(f"    [!] NVM Error: Missing NVSim config {nvsim_cfg}")
                continue

            print(f"    [1/2] Running NVSim Hardware Phase...")
            try:
                nvsim_res = subprocess.run([str(nvsim_exe), str(nvsim_cfg)], 
                                           cwd=nvsim_bin_dir, capture_output=True, text=True)
                if "RESULT" in nvsim_res.stdout:
                    nvsim_out = hw_results_dir / f"{model}_results.txt"
                    with open(nvsim_out, "w") as f:
                        f.write(nvsim_res.stdout)
                    print(f"          -> Hardware data saved.")
                else:
                    print(f"    [!] NVSim Convergence Failed.")
                    continue
            except Exception as e:
                print(f"    [!] NVSim Execution Failed: {e}")
                continue

        # --- PHASE 2: NVMAIN ---
        nvmain_cfg = root_dir / "simulators" / "nvmain" / "Config" / f"{model}.config"
        if not nvmain_cfg.exists():
            print(f"    [!] NVMain Error: Config not found at {nvmain_cfg}")
            continue

        print(f"    [2/2] Running NVMain System Phase...")
        # Tagging stats file with benchmark name
        stats_file = sys_results_dir / f"stats_{model}_{trace_name}.out"
        
        try:
            with open(stats_file, "w") as out_f:
                process = subprocess.run(
                    [str(nvmain_exe), str(nvmain_cfg), str(trace_path), str(args.cycles)],
                    stdout=out_f, stderr=subprocess.STDOUT
                )
            if process.returncode == 0:
                print(f"          -> System stats saved: {stats_file.name}")
            else:
                print(f"    [!] NVMain Error (Code {process.returncode}).")
        except Exception as e:
            print(f"    [!] NVMain Execution Failed: {e}")

    print("\n" + "=" * 60)
    print("STEP 4 COMPLETE.")
    print("=" * 60)

if __name__ == "__main__":
    run_simulations()