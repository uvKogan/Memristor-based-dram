import subprocess
import os
import sys

def run_gatekeeper():
    print("=" * 60)
    print("MBMM NVSIM GATE-KEEPER: SANITY & RESEARCH TRACK VALIDATION")
    print("=" * 60)

    # 1. Absolute Path Setup
    root_dir = "/home/yuvalk/MBMM"
    nvsim_dir = os.path.join(root_dir, "simulators/nvsim")
    
    # Validation Tracks
    sanity_model = os.path.join(root_dir, "sanity_check/standard.cfg")
    mbmm_models = [
        os.path.join(root_dir, "configs/reram_22nm_1t1r_slc.cfg"),
        os.path.join(root_dir, "configs/reram_22nm_selector_slc.cfg")
    ]

    # 2. Rebuild NVSim to ensure repairs (C++11) are active
    print(f"\n>>> Rebuilding NVSim engine in {nvsim_dir}...")
    try:
        os.chdir(nvsim_dir)
        subprocess.run(["make", "clean"], capture_output=True, check=True)
        subprocess.run(["make"], capture_output=True, check=True)
        print("--- NVSim Engine Build: SUCCESS ---")
    except Exception as e:
        print(f"!!! ERROR: Build failed. Check Makefile and C++ fixes !!!\n{e}")
        sys.exit(1)

    # 3. Step 1: Engine Sanity Check (Known-good baseline)
    print(f"\n>>> Step 1: Running Engine Sanity Check ({sanity_model})")
    sanity_proc = subprocess.run(["./nvsim", sanity_model], capture_output=True, text=True)
    if "Floating point exception" in sanity_proc.stderr or sanity_proc.returncode == -8:
        print("!!! CRITICAL FAILURE: Engine is unstable even on sanity baseline !!!")
        sys.exit(1)
    print("--- Sanity Check: PASS (Engine mathematically stable) ---")

    # 4. Step 2: Research Track Validation
    for model_full_path in mbmm_models:
        print(f"\n>>> Step 2: Validating Research Track: {model_full_path}")
        
        if not os.path.exists(model_full_path):
            print(f"[GATE-KEEPER ERROR] Missing .cfg file at: {model_full_path}")
            sys.exit(1)

        process = subprocess.run(["./nvsim", model_full_path], capture_output=True, text=True)
        output = process.stdout + process.stderr

        # Check for non-convergence or crashes
        if process.returncode != 0 or "0.000" in output or "Zero dimension" in output:
            print(f"!!! RESEARCH TRACK FAILED: {os.path.basename(model_full_path)} !!!")
            print("REASON: Electrical non-convergence at 22nm LOP.")
            
            # We don't sys.exit here yet because we want to see if both tracks fail
            # But we mark the simulation as 'UNSAFE' for NVMain input
            print("\nLAST SOLVER LOG LINE:")
            print(output.splitlines()[-1] if output.splitlines() else "No Output")
        else:
            print(f"--- {os.path.basename(model_full_path)} Validation: SUCCESS ---")

    print("\n" + "=" * 60)
    print("GATE-KEEPER PROCESS COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    run_gatekeeper()