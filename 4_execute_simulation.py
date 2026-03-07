import subprocess
import os
import shutil
import argparse
import datetime
from pathlib import Path

def get_project_root():
    """Dynamically finds the MBMM project root directory."""
    return Path(__file__).parent.absolute()

def setup_args():
    parser = argparse.ArgumentParser(
        description="MBMM Step 4: Unified Execution Wrapper (NVSim & NVMain)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Examples:
  python3 4_execute_simulation.py --models reram_22nm_1t1r_slc
  python3 4_execute_simulation.py --all --cycles 100000
  python3 4_execute_simulation.py --models my_model --trace traces/workload.nvt
        """
    )
    parser.add_argument("--models", nargs="+", help="Model names without extensions (e.g., reram_22nm_1t1r_slc).")
    parser.add_argument("--all", action="store_true", help="Run simulation for all .cfg files in the configs/ directory.")
    parser.add_argument("--trace", default="test_reram.nvt", help="Path to the .nvt trace file (default: test_reram.nvt).")
    parser.add_argument("--cycles", type=int, default=50000, help="Maximum simulation cycles for NVMain (default: 50000).")
    return parser.parse_args()

def run_simulations():
    args = setup_args()
    root_dir = get_project_root()
    
    # Path Definitions
    config_dir = root_dir / "configs"
    # NEW: Organized results subdirectories
    hw_results_dir = root_dir / "results" / "hardware"
    sys_results_dir = root_dir / "results" / "system"
    
    nvsim_exe = root_dir / "simulators" / "nvsim" / "nvsim"
    nvmain_exe = root_dir / "simulators" / "nvmain" / "nvmain.fast"
    trace_path = root_dir / args.trace
    
    # Ensure directories exist
    hw_results_dir.mkdir(parents=True, exist_ok=True)
    sys_results_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # 1. Determine Target Models
    target_models = []
    if args.all:
        target_models = [f.stem for f in config_dir.glob("*.cfg")]
    elif args.models:
        target_models = args.models
    else:
        print("[!] No models specified. Use --models <name> or --all. Use --help for info.")
        return

    print("=" * 60)
    print("MBMM STEP 4: UNIFIED SIMULATION PIPELINE")
    print(f"Trace: {args.trace} | Max Cycles: {args.cycles}")
    print("=" * 60)

    # 2. Sync .cell files for NVSim
    nvsim_bin_dir = nvsim_exe.parent
    for cell_file in config_dir.glob("*.cell"):
        shutil.copy(cell_file, nvsim_bin_dir)

    for model in target_models:
        print(f"\n>>> PROCESSING MODEL: {model}")
        
        # --- PHASE 1: NVSIM (Hardware Cell Simulation) ---
        nvsim_cfg = config_dir / f"{model}.cfg"
        if not nvsim_cfg.exists():
            print(f"    [!] NVSim config not found: {nvsim_cfg}")
            continue

        print(f"    [1/2] Running NVSim Hardware Phase...")
        try:
            nvsim_res = subprocess.run([str(nvsim_exe), str(nvsim_cfg)], 
                                       cwd=nvsim_bin_dir, capture_output=True, text=True)
            
            # Save hardware results to results/hardware/
            nvsim_out = hw_results_dir / f"{model}_results.txt"
            if "RESULT" in nvsim_res.stdout:
                with open(nvsim_out, "w") as f:
                    f.write(nvsim_res.stdout)
                print(f"          -> Hardware data saved: {nvsim_out.relative_to(root_dir)}")
            else:
                print(f"    [!] NVSim Convergence Failed for {model}. Check configs.")
                continue

        except Exception as e:
            print(f"    [!] NVSim Execution Failed: {e}")
            continue

        # --- PHASE 2: NVMAIN (System Architecture Simulation) ---
        nvmain_cfg = root_dir / "simulators" / "nvmain" / "Config" / f"{model}.config"
        if not nvmain_cfg.exists():
            print(f"    [!] NVMain config not found: {nvmain_cfg}")
            print("        (Ensure Step 3 was run for this model)")
            continue

        if not trace_path.exists():
            print(f"    [!] Trace file not found: {trace_path}")
            continue

        print(f"    [2/2] Running NVMain System Phase...")
        # Save system stats to results/system/
        stats_file = sys_results_dir / f"stats_{model}_{timestamp}.out"
        
        try:
            # Capture the full terminal table for the Step 5 parser
            with open(stats_file, "w") as out_f:
                process = subprocess.run(
                    [str(nvmain_exe), str(nvmain_cfg), str(trace_path), str(args.cycles)],
                    stdout=out_f,
                    stderr=subprocess.STDOUT
                )
            
            if process.returncode == 0:
                print(f"          -> System stats saved: {stats_file.relative_to(root_dir)}")
            else:
                print(f"    [!] NVMain Error (Code {process.returncode}). Check log: {stats_file.name}")

        except Exception as e:
            print(f"    [!] NVMain Execution Failed: {e}")

    print("\n" + "=" * 60)
    print("STEP 4 COMPLETE: Simulation batch finished.")
    print("=" * 60)

if __name__ == "__main__":
    run_simulations()