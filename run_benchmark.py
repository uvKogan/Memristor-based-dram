import subprocess
import os
import csv
import re

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NVSIM_EXE = os.path.join(BASE_DIR, "simulators/nvsim/nvsim")
CONFIG_DIR = os.path.join(BASE_DIR, "configs")
OUTPUT_DB = os.path.join(BASE_DIR, "simulation_results.csv")

# The 4 Hardware Tracks
MODELS = [
    "reram_22nm_1t1r_slc",
    "reram_22nm_1t1r_mlc",
    "reram_22nm_selector_slc",
    "reram_22nm_selector_mlc"
]

def parse_value(pattern, text):
    match = re.search(pattern, text)
    return match.group(1).strip() if match else "N/A"

def run_simulations():
    fieldnames = ["Model", "Area (mm^2)", "Read Latency", "Write Latency", "Read Energy", "Write Energy", "Leakage Power"]
    db_rows = []

    print("[*] Rebuilding NVSim engine...")
    subprocess.run(["make"], cwd=os.path.dirname(NVSIM_EXE), capture_output=True)

    print("="*60)
    print("MBMM RESEARCH PIPELINE: BATCH EXECUTION")
    print("="*60)

    for model in MODELS:
        cfg_file = os.path.abspath(os.path.join(CONFIG_DIR, f"{model}.cfg"))
        print(f"[*] Running {model}...")

        # Run NVSim and capture output
        try:
            # We run from the simulator directory to avoid path issues
            result = subprocess.run(
                ["./nvsim", cfg_file],
                capture_output=True, text=True, check=True,
                cwd=os.path.dirname(NVSIM_EXE)
            )
            output = result.stdout
            
            # Extract Metrics using Regex
            data = {
                "Model": model,
                "Area (mm^2)": parse_value(r"Total Area = .* = (.*mm\^2)", output),
                "Read Latency": parse_value(r"Read Latency = (.*s)", output),
                "Write Latency": parse_value(r"Write Latency = (.*s)", output),
                "Read Energy": parse_value(r"Read Dynamic Energy = (.*J)", output),
                "Write Energy": parse_value(r"Write Dynamic Energy = (.*J)", output),
                "Leakage Power": parse_value(r"Leakage Power = (.*W)", output)
            }
            db_rows.append(data)
            print(f"    [+] Success. Area: {data['Area (mm^2)']}")

        except subprocess.CalledProcessError as e:
            print(f"    [!] Error running {model}: {e}")

    # Write to "Database" (CSV)
    with open(OUTPUT_DB, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(db_rows)

    print("="*60)
    print(f"DONE. Database updated: {OUTPUT_DB}")
    print("="*60)

if __name__ == "__main__":
    run_simulations()