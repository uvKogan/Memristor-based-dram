import subprocess
import os
import shutil
import argparse
import datetime
import sys
from pathlib import Path

# T2.6 fix round 1: this script's own NVSim call (Phase 1, below) is a
# second, older invocation site alongside 1_run_nvsim_hardware.py's; both
# now share the debug-line filter and the organization gate from
# nvsim_common.py instead of one of them going without.
from nvsim_common import strip_debug_lines, check_forced_organization

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

def skip_nvsim(model, config_dir, nvmain_config_dir):
    """Decide whether the NVSim hardware phase (Phase 1) should be skipped for `model`.

    Returns (should_skip, reason):
      - (True, "DRAM baseline")   if "dram" appears in the model name (case-insensitive).
      - (True, "Analytical MLC")  if "_mlc" appears in the model name (case-insensitive).
      - (True, "Native NVMain-only model (no NVSim config, matched NVMain config found)")
        if no `configs/<model>.cfg` exists but a `simulators/nvmain/Config/<model>.config`
        does (e.g. pcm_microsoft_2009, or a future T2.8 silicon config that only ever gets
        an NVMain config): NVSim never ran for this model, Phase 2 uses NVMain directly.
      - (False, "NVSim config present") if `configs/<model>.cfg` exists: run Phase 1 normally.

    Raises FileNotFoundError if neither a `.cfg` nor a `.config` exists for `model` -- there
    is nothing to simulate, which is an error, not a skip.
    """
    model_lower = model.lower()
    if "dram" in model_lower:
        return True, "DRAM baseline"
    if "_mlc" in model_lower:
        return True, "Analytical MLC"

    cfg_path = Path(config_dir) / f"{model}.cfg"
    nvmain_cfg_path = Path(nvmain_config_dir) / f"{model}.config"

    if cfg_path.exists():
        return False, "NVSim config present"
    if nvmain_cfg_path.exists():
        return True, "Native NVMain-only model (no NVSim config, matched NVMain config found)"

    raise FileNotFoundError(
        f"No NVSim config ({cfg_path}) and no NVMain config ({nvmain_cfg_path}) "
        f"found for model '{model}'"
    )

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

    nvmain_config_dir = root_dir / "simulators" / "nvmain" / "Config"
    failed_models = []

    for model in target_models:
        print(f"\n>>> PROCESSING MODEL: {model}")

        # --- PHASE 1: NVSIM (bypass for DRAM, MLC, and native NVMain-only models) ---
        try:
            skip, reason = skip_nvsim(model, config_dir, nvmain_config_dir)
        except FileNotFoundError as e:
            print(f"    [!] {e}")
            failed_models.append((model, str(e)))
            continue

        if skip:
            print(f"    [SKIP] Phase 1: {reason}. Using native/pre-generated timings.")
        else:
            nvsim_cfg = config_dir / f"{model}.cfg"
            print(f"    [1/2] Running NVSim Hardware Phase...")
            try:
                nvsim_res = subprocess.run([str(nvsim_exe), str(nvsim_cfg)],
                                           cwd=nvsim_bin_dir, capture_output=True, text=True)

                # Strip Mat.cpp's '>>> [' debug prints immediately: they are
                # never stored or parsed, matching 1_run_nvsim_hardware.py.
                clean_stdout = strip_debug_lines(nvsim_res.stdout)

                # Same organization gate as 1_run_nvsim_hardware.py: a run
                # that exits 0 but silently explored its own organization (or
                # hit a missing/unparsed -Force* key) is not a success here
                # either.
                org_ok, org_message = check_forced_organization(clean_stdout, nvsim_cfg)
                if "RESULT" in clean_stdout and org_ok:
                    nvsim_out = hw_results_dir / f"{model}_results.txt"
                    with open(nvsim_out, "w") as f:
                        f.write(clean_stdout)
                    print(f"          -> Hardware data saved.")
                    print(f"          {org_message}")
                elif not org_ok:
                    print(f"    [!] {org_message}")
                    failed_models.append((model, org_message))
                    continue
                else:
                    print(f"    [!] NVSim Convergence Failed.")
                    failed_models.append((model, "NVSim convergence failed"))
                    continue
            except Exception as e:
                print(f"    [!] NVSim Execution Failed: {e}")
                failed_models.append((model, f"NVSim execution failed: {e}"))
                continue

        # --- PHASE 2: NVMAIN ---
        nvmain_cfg = nvmain_config_dir / f"{model}.config"
        if not nvmain_cfg.exists():
            print(f"    [!] NVMain Error: Config not found at {nvmain_cfg}")
            failed_models.append((model, f"NVMain config not found at {nvmain_cfg}"))
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
                if not stats_file.exists() or stats_file.stat().st_size == 0:
                    print(f"    [!] NVMain Error: exit 0 but stats output is missing or empty.")
                    failed_models.append((model, "NVMain exited 0 but produced no/empty stats output"))
                else:
                    print(f"          -> System stats saved: {stats_file.name}")
            else:
                print(f"    [!] NVMain Error (Code {process.returncode}).")
                failed_models.append((model, f"NVMain exited with code {process.returncode}"))
        except Exception as e:
            print(f"    [!] NVMain Execution Failed: {e}")
            failed_models.append((model, f"NVMain execution failed: {e}"))

    print("\n" + "=" * 60)
    print("STEP 4 COMPLETE.")
    print("=" * 60)

    if failed_models:
        print(f"\n[SUMMARY] {len(failed_models)} model(s) failed:")
        for m, reason in failed_models:
            print(f"    - {m}: {reason}")
        sys.exit(1)

if __name__ == "__main__":
    run_simulations()