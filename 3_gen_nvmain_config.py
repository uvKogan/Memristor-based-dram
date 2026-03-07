import math
import json
import os
import argparse
from pathlib import Path

def get_project_root():
    """Dynamically finds the MBMM project root directory."""
    return Path(__file__).parent.absolute()

def setup_args():
    parser = argparse.ArgumentParser(
        description="MBMM Step 3: Generate NVMain Configs from Hardware Metrics",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Examples:
  python3 3_gen_nvmain_config.py --input results/hardware_metrics.json
  python3 3_gen_nvmain_config.py --freq 1000 --input results/custom_metrics.json
        """
    )
    parser.add_argument("--input", default="results/hardware_metrics.json", help="Input JSON file from Step 2.")
    parser.add_argument("--freq", type=int, default=800, help="Target memory frequency in MHz (default: 800).")
    return parser.parse_args()

def generate_nvmain_config(name, hw_metrics, target_freq_mhz, output_dir):
    """Creates a stable NVMain .config file using hardware-specific metrics."""
    # Calculate cycle time (e.g., 1.25ns for 800MHz)
    cycle_time_ns = 1000.0 / target_freq_mhz
    
    # Timing Calculations (Standardized to cycles)
    tREAD = math.ceil(hw_metrics.get('read_latency_ns', 32.0) / cycle_time_ns)
    tWRITE = math.ceil(hw_metrics.get('write_latency_ns', 32.0) / cycle_time_ns)
    
    # --- STABILITY FIX: Long-form AddressMappingScheme ---
    mapping_scheme = "SA:R:BK:RK:CH:C"

    config_content = f"""
; --- MBMM SYSTEM ARCHITECTURE CONFIGURATION ---
; Model: {name}
; Hardware Source: {hw_metrics.get('source_file', 'Extracted JSON')}

; --- Infrastructure ---
MAP_ADDRESS true
DECODER MigratingDecoder
INTERCONNECT OffChipBus
STATS_OUT nvmain_stats_{name}.out
CPUFreq {target_freq_mhz}

; --- Clock and Controller ---
CLK {target_freq_mhz}
MEM_CTL FRFCFS

; --- Address Mapping (Stability Fix: Long-form string) ---
AddressMappingScheme {mapping_scheme}
BusWidth 64
DeviceWidth 8
RATE 2

; --- Timing Parameters (Cycles) ---
tCAS {tREAD}
tRCD {tREAD}
tRP 1       
tRAS {tREAD}
tWR {tWRITE}
tRTW {tREAD}
tBus 4
tCMD 1

; --- Energy and Power ---
ReadEnergy {hw_metrics.get('read_energy_nj', 1.1)}
WriteEnergy {hw_metrics.get('write_energy_nj', 1.7)}
StandbyPower {hw_metrics.get('leakage_mw', 794.0)}

; --- Stable Geometry (Prevents Address Slicing Underflow) ---
; Standard geometry ensures bit-depth satisfies the translator
ROWS 65536
COLS 1024
CHANNELS 1
RANKS 1
BANKS 8
SUBARRAYS 1
MATHeight 65536

; --- NVM Specific Logic ---
ClosePage 1
UseRefresh false
UsePrecharge true
"""
    file_path = output_dir / f"{name}.config"
    with open(file_path, 'w') as f:
        f.write(config_content)
    return file_path

def main():
    args = setup_args()
    root_dir = get_project_root()
    
    # Use absolute path for input to ensure no assumptions on working directory
    input_path = root_dir / args.input
    output_dir = root_dir / "simulators" / "nvmain" / "Config"

    if not input_path.exists():
        print(f"[!] Input metrics file not found: {input_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("MBMM STEP 3: NVMAIN CONFIG GENERATION")
    print(f"Target Frequency: {args.freq} MHz")
    print("=" * 60)

    with open(input_path, 'r') as f:
        all_metrics = json.load(f)

    for model_name, metrics in all_metrics.items():
        print(f">>> Generating config for: {model_name}...")
        config_file = generate_nvmain_config(model_name, metrics, args.freq, output_dir)
        print(f"    [OK] Saved to: simulators/nvmain/Config/{config_file.name}")

    print("\n" + "=" * 60)
    print(f"SUCCESS: {len(all_metrics)} configurations generated.")
    print("=" * 60)

if __name__ == "__main__":
    main()