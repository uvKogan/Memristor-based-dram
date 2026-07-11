import math
import json
import os
import argparse
from pathlib import Path

def get_project_root():
    return Path(__file__).parent.absolute()

def setup_args():
    parser = argparse.ArgumentParser(description="MBMM Step 3: Multi-Architecture Factory")
    parser.add_argument("--input", default="results/hardware_metrics.json", help="Input JSON file.")
    parser.add_argument("--freq", type=int, default=800, help="Target frequency in MHz.")
    return parser.parse_args()

def generate_nvmain_config(base_name, hw_metrics, target_freq_mhz, output_dir, arch_type):
    # PROTECT DRAM: Do not generate NVMain configs for DRAM models!
    if "dram" in base_name.lower():
        return None
    
    cycle_time_ns = 1000.0 / target_freq_mhz
    tREAD = math.ceil(hw_metrics.get('read_latency_ns', 32.0) / cycle_time_ns)
    tWRITE = math.ceil(hw_metrics.get('write_latency_ns', 32.0) / cycle_time_ns)
    
    # --- ARCHITECTURE FACTORY LOGIC ---
    bus_width = 64
    banks = 8
    cols = 1024  
    
    if arch_type == "single":
        ranks = 1; devices_per_rank = 1; current_device_width = 64; mapping = "R:BK:C"
    elif arch_type == "8chip":
        ranks = 1; devices_per_rank = 8; current_device_width = 8; mapping = "R:BK:C"
    elif arch_type == "16chip":
        ranks = 2; devices_per_rank = 8; current_device_width = 8; mapping = "R:BK:RK:C"
    elif arch_type == "full_dimm":
        ranks = 8; devices_per_rank = 8; current_device_width = 8; mapping = "R:BK:RK:C"
    else:
        ranks = 1; devices_per_rank = 1; current_device_width = 8; mapping = "R:BK:C"

    cap_gb = hw_metrics.get('capacity_gb', 0.125)
    bits_per_chip = cap_gb * 8 * 1024 * 1024 * 1024
    rows_per_chip = int(bits_per_chip / (cols * current_device_width * banks))
    system_rows = max(rows_per_chip * ranks, 65536)

    # Static/leakage power: NVMain's NonVolatile energy model charges Eactstdby/Eprestdby
    # once per RANK per cycle (Ranks/StandardRank/StandardRank.cpp, no per-device scaling
    # for EnergyModel != "current") -- not once per device, and NOT via a "StandbyPower"
    # key, which NVMain never reads (grepped the entire nvmain source tree: zero matches
    # outside Config/*.config data files). So a per-chip NVSim leakage figure must be
    # scaled up to rank granularity (x devices_per_rank, NOT x total ranks*devices) and
    # converted from a steady-state Watts figure into per-cycle nanojoules.
    #
    # This is policy-a / "ungated" semantics: every device in the rank is always fully
    # powered (no power-down states are ever entered -- see note below), so leakage is
    # charged for every simulated cycle at the rank's full linear device-count leakage.
    # No NVSim datapoint distinguishes "active row open" leakage from "all banks
    # precharged" leakage, so the same derived value is used for both Eactstdby and
    # Eprestdby; this is a documented simplifying assumption, not a measured split.
    #
    # Epda/Epdpf/Epdps (active/precharge powerdown energy) are deliberately left unset
    # (NVMain default: 0.0). MemoryController::HandleLowPower() -- the only call site
    # that would ever transition a rank into a powerdown state -- is commented out in
    # this NVMain build (src/MemoryController.cpp:1650), confirmed dead by zero
    # fastExitActiveCycles/fastExitPrechargeCycles/slowExitCycles across every stats file
    # of every technology. No rank ever reaches PDA/PDPF/PDPS, so these constants have no
    # effect regardless of value. Restoring that state machine is out of scope here.
    chip_leakage_w = hw_metrics.get('leakage_mw', 10.0) / 1000.0
    rank_leakage_w = chip_leakage_w * devices_per_rank
    e_standby_nj = rank_leakage_w * cycle_time_ns

    r_energy = hw_metrics.get('read_energy_nj', 1.1)
    w_energy = hw_metrics.get('write_energy_nj', 1.7)

    sys_model_name = f"{base_name}_{arch_type}"

    config_content = f"""
; --- MBMM SYSTEM ARCHITECTURE: {arch_type.upper()} ---
; Base Model: {base_name} | Rank Width: {bus_width}-bit

; --- Infrastructure ---
IgnorePremappedAddresses true
IgnoreAddressError true
AddressMask 0xFFFFFFFF
PrintConfig true
PrintAllDevices true
EnableDebug false
MAP_ADDRESS true
DECODER MigratingDecoder
INTERCONNECT OffChipBus
STATS_OUT nvmain_stats_{sys_model_name}.out
CPUFreq {target_freq_mhz}

; --- Clock, Controller and Scaling ---
CLK {target_freq_mhz}
MEM_CTL FRFCFS
DEVICES_PER_RANK {devices_per_rank}

; --- Address Mapping ---
AddressMappingScheme {mapping}
BusWidth {bus_width}
DeviceWidth {current_device_width}
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
; Eactstdby/Eprestdby: rank-level standby energy per cycle (nJ), derived from NVSim
; per-chip leakage x devices_per_rank -- see comment above. Policy-a/ungated: no
; power-down state is ever reached (HandleLowPower() is dead in this NVMain build),
; so Epda/Epdpf/Epdps are intentionally left at their NVMain defaults (unset/0.0).
ReadEnergy {r_energy}
WriteEnergy {w_energy}
Eactstdby {e_standby_nj}
Eprestdby {e_standby_nj}

; --- Geometry Scaling ---
ROWS {system_rows}
COLS {cols}
CHANNELS 1
RANKS {ranks}
BANKS {banks}
SUBARRAYS 1

; --- NVM Specific Logic ---
ClosePage 1
UseRefresh false
UsePrecharge true
EnergyModel NonVolatile
"""
    file_path = output_dir / f"{sys_model_name}.config"
    with open(file_path, 'w') as f:
        f.write(config_content)
    return sys_model_name

def main():
    args = setup_args()
    root_dir = get_project_root()
    input_path = root_dir / args.input
    output_dir = root_dir / "simulators" / "nvmain" / "Config"

    if not input_path.exists():
        print(f"[!] Input metrics file not found: {input_path}")
        return

    os.makedirs(output_dir, exist_ok=True)
    with open(input_path, 'r') as f:
        all_metrics = json.load(f)

    architectures = ["single", "8chip", "16chip", "full_dimm"]
    generated_count = 0

    print("=" * 60)
    print(f"MBMM STEP 3: SYSTEM ARCHITECTURE FACTORY ({args.freq} MHz)")
    print("=" * 60)

    for model_name, metrics in all_metrics.items():
        print(f"\n>>> Base Hardware: {model_name}")
        for arch in architectures:
            sys_name = generate_nvmain_config(model_name, metrics, args.freq, output_dir, arch)
            if sys_name:
                print(f"    [OK] Generated System Model: {sys_name}")
                generated_count += 1
            else:
                print(f"    [SKIP] Protected native DRAM config.")

    print("\n" + "=" * 60)
    print(f"SUCCESS: {generated_count} system-level configurations generated.")
    print("=" * 60)

if __name__ == "__main__":
    main()