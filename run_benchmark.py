import subprocess
import os
import csv
import math
import shutil
import time

# --- CONFIGURATION ---
BASE_DIR = "/home/yuvalk/MBMM"
CONFIG_DIR = os.path.join(BASE_DIR, "configs")
NVSIM_EXE = os.path.join(BASE_DIR, "simulators/nvsim/nvsim")
CLOCK_NS = 1.25
OUTPUT_CSV = "simulation_results.csv"

MODELS = [
    "reram_22nm_1t1r_slc",
    "reram_22nm_1t1r_mlc",
    "reram_22nm_selector_slc",
    "reram_22nm_selector_mlc"
]

def save_results(results):
    with open(OUTPUT_CSV, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Model", "Read Latency (ns)", "Write Latency (ns)", "Read Cycles", "Write Cycles"])
        writer.writerows(results)
    print(f"\n[!] Final results saved to: {OUTPUT_CSV}")

def run_simulations():
    results = []
    NVSIM_CSV_NAME = "output_131072K_64_1_IN_CUR.csv"
    nvsim_dir = os.path.dirname(NVSIM_EXE)
    csv_full_path = os.path.join(nvsim_dir, NVSIM_CSV_NAME)

    for model in MODELS:
        print(f"\n{'='*60}")
        print(f"[*] STARTING SIMULATION: {model}")
        print(f"{'='*60}")
        
        if os.path.exists(csv_full_path):
            os.remove(csv_full_path)

        cfg_path = os.path.join(CONFIG_DIR, f"{model}.cfg")
        
        # Use check_output or capture_output to see what NVSim is saying
        try:
            result = subprocess.run(
                [NVSIM_EXE, cfg_path],
                cwd=nvsim_dir,
                capture_output=True,
                text=True
            )
            # Print the simulator's actual output to the terminal
            print(result.stdout)
            if result.stderr:
                print(f"DEBUG STDERR: {result.stderr}")
                
        except Exception as e:
            print(f"[!] Subprocess execution failed: {e}")
            continue

        # Check if CSV exists after the run
        if os.path.exists(csv_full_path):
            with open(csv_full_path, mode='r') as f:
                content = f.read().splitlines()
                if content:
                    data = content[0].split(',')
                    raw_r = float(data[21]) / 1000.0 # Convert ps to ns
                    raw_w = float(data[24]) / 1000.0
                    r_cyc = math.ceil(raw_r / CLOCK_NS)
                    w_cyc = math.ceil((raw_w + 10.0) / CLOCK_NS)
                    
                    print(f"===> RESULT FOUND: R={raw_r:.2f}ns, W={raw_w:.2f}ns")
                    results.append([model, raw_r, raw_w, r_cyc, w_cyc])
        else:
            print(f"\n[!] FAILURE: {model} did not generate a CSV result.")
            print(f"[!] Review the output above to find the electrical or range error.")

    save_results(results)

if __name__ == "__main__":
    # Ensure cell files are in the simulator directory
    print("============================================================")
    print("MBMM RESEARCH PIPELINE: HARDWARE-TO-SYSTEM BRIDGE")
    print("============================================================")
    for f in os.listdir(CONFIG_DIR):
        if f.endswith(".cell"):
            shutil.copy(os.path.join(CONFIG_DIR, f), os.path.dirname(NVSIM_EXE))
    
    run_simulations()