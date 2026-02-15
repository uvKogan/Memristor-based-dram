import subprocess
import os
import sys

def run_step(name, command, directory):
    print(f"\n>>> Running in {directory}...")
    try:
        # Run command and wait for completion
        result = subprocess.run(command, cwd=directory, shell=True, check=True)
        print(f"--- {name} SUCCEEDED ---")
    except subprocess.CalledProcessError as e:
        print(f"\n!!! ERROR: {name} FAILED with exit code {e.returncode}!!!")
        sys.exit(1)

def main():
    root = os.getcwd()
    nvsim_dir = os.path.join(root, "simulators/nvsim")
    nvmain_dir = os.path.join(root, "simulators/nvmain")

    print("="*60)
    print("MBMM GATE-KEEPER: VALIDATING SIMULATION STACK")
    print("="*60)

    # --- NVSIM VALIDATION ---
    run_step("NVSim Clean", "make clean", nvsim_dir)
    run_step("NVSim Build", "make", nvsim_dir)
    # Test with a basic config to ensure logic is intact
    run_step("NVSim Test Run", "./nvsim sample_STTRAM_cache.cfg", nvsim_dir)

    # --- NVMAIN VALIDATION ---
    run_step("NVMain Clean", "scons -c", nvmain_dir)
    run_step("NVMain Build", "scons --build-type=fast", nvmain_dir)
    # Test with a basic trace to ensure state-machine is healthy [4]
    run_step("NVMain Test Run", "./nvmain.fast Config/PCM_ISSCC_2012_4GB.config Tests/Traces/hello_world.nvt 1000000", nvmain_dir)

    print("\n" + "="*60)
    print(">>> SUCCESS: ALL SYSTEMS HEALTHY. READY TO PUSH TO GIT. <<<")
    print("="*60)

if __name__ == "__main__":
    main()