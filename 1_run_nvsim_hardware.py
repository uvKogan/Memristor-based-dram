import subprocess
import os
import sys
import argparse
from pathlib import Path

# T2.6 fix round 1: the debug-line filter and the organization gate are
# shared with 4_execute_simulation.py's own NVSim call site; both live in
# nvsim_common.py so the logic is defined once. Re-imported here under their
# original names so the rest of this file (and any external caller) is
# unchanged.
from nvsim_common import strip_debug_lines, expected_organization, check_forced_organization

def get_project_root():
    """Dynamically finds the MBMM project root directory."""
    return Path(__file__).parent.absolute()

def setup_args():
    parser = argparse.ArgumentParser(
        description="MBMM Research Pipeline Step 1: NVSim Hardware Simulation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Examples:
  python3 1_run_nvsim_hardware.py --models configs/reram_22nm_1t1r_slc.cfg
  python3 1_run_nvsim_hardware.py --all
  python3 1_run_nvsim_hardware.py --rebuild --models configs/my_new_model.cfg
        """
    )
    parser.add_argument("--models", nargs="+", help="Path to one or more NVSim .cfg files.")
    parser.add_argument("--all", action="store_true", help="Run simulation for all .cfg files in configs/.")
    parser.add_argument("--rebuild", action="store_true", help="Force clean and rebuild NVSim engine.")
    parser.add_argument("--skip_sanity", action="store_true", help="Skip the engine sanity check.")
    return parser.parse_args()

def build_nvsim(nvsim_dir):
    """Internal helper to compile the NVSim engine."""
    print(f"\n>>> Building NVSim engine in {nvsim_dir}...")
    try:
        # Perform a clean build to ensure C++11 fixes are active
        subprocess.run(["make", "clean"], cwd=nvsim_dir, capture_output=True, check=False)
        subprocess.run(["make"], cwd=nvsim_dir, capture_output=True, check=True)
        print("--- NVSim Engine Build: SUCCESS ---")
        return True
    except Exception as e:
        print(f"!!! ERROR: Build failed. Check your compiler and Makefile.\n{e}")
        return False

def run_nvsim_hardware():
    args = setup_args()
    root_dir = get_project_root()
    nvsim_dir = root_dir / "simulators" / "nvsim"
    nvsim_exe = nvsim_dir / "nvsim"
    config_dir = root_dir / "configs"
    sanity_model = root_dir / "sanity_check" / "standard.cfg"
    hw_results_dir = root_dir / "results" / "hardware"
    hw_results_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("MBMM STEP 1: NVSIM HARDWARE SIMULATION")
    print("=" * 60)

    # 1. Automatic Build Logic: Build if missing or if --rebuild is requested
    if not nvsim_exe.exists() or args.rebuild:
        if not nvsim_exe.exists():
            print(f"[!] NVSim binary not found at {nvsim_exe}.")
        if not build_nvsim(nvsim_dir):
            sys.exit(1)

    # 2. Engine Sanity Check
    if not args.skip_sanity:
        print(f"\n>>> Step 1: Running Engine Sanity Check ({sanity_model.name})")
        if not sanity_model.exists():
            print(f"!!! WARNING: Sanity model not found at {sanity_model}. Skipping...")
        else:
            sanity_proc = subprocess.run([str(nvsim_exe), str(sanity_model)], cwd=nvsim_dir, capture_output=True, text=True)
            if sanity_proc.returncode != 0 or "Floating point exception" in sanity_proc.stderr:
                print("!!! CRITICAL FAILURE: Engine is unstable !!!")
                sys.exit(1)
            print("--- Sanity Check: PASS ---")

    # 3. Determine target models
    target_configs = []
    if args.all:
        target_configs = list(config_dir.glob("*.cfg"))
    elif args.models:
        target_configs = [Path(m) for m in args.models]
    else:
        print("[!] No models specified. Use --models or --all.")
        sys.exit(0)

    # 4. Run Research Track Validation
    any_failure = False
    for cfg in target_configs:
        if not cfg.exists():
            print(f"\n[!] Missing .cfg file at: {cfg}")
            any_failure = True
            continue

        print(f"\n>>> Step 2: Simulating Hardware: {cfg.name}")
        
        # Executing NVSim
        process = subprocess.run([str(nvsim_exe), str(cfg.absolute())], cwd=nvsim_dir, capture_output=True, text=True)

        # Strip Mat.cpp's '>>> [' debug prints immediately: they are never
        # stored or parsed, and everything below (the gate, the saved file)
        # works only off the cleaned text.
        clean_stdout = strip_debug_lines(process.stdout)

        # We define success as having produced a result table in stdout AND
        # having honored the forced organization (T2.6 gate): a run that
        # exits 0 but silently explored its own organization (or hit a
        # missing/unparsed -Force* key) must not be treated as a success.
        org_ok, org_message = check_forced_organization(clean_stdout, cfg)
        if "RESULT" in clean_stdout and "Area:" in clean_stdout and org_ok:
            output_filename = hw_results_dir / f"{cfg.stem}_results.txt"
            with open(output_filename, "w") as f:
                f.write(clean_stdout)
            print(f"--- SUCCESS: Results saved to {output_filename.name} ---")
            print(f"    {org_message}")
        else:
            any_failure = True
            print(f"!!! RESEARCH TRACK FAILED: {cfg.name} !!!")
            if not org_ok:
                print(f"REASON: {org_message}")
            else:
                print("REASON: Output does not contain a valid RESULT table.")
            if process.stderr:
                print(f"DEBUG STDERR: {process.stderr}")

    print("\n" + "=" * 60)
    print("STEP 1 COMPLETE")
    print("=" * 60)

    return 1 if any_failure else 0

if __name__ == "__main__":
    sys.exit(run_nvsim_hardware())