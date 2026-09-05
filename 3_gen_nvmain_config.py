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
    parser.add_argument("--queue-size", type=int, default=32,
                        help="FRFCFS controller QueueSize (default: 32, matching NVMain's own "
                             "hardcoded fallback - see FRFCFS.cpp). Kept as an explicit, "
                             "documented generator parameter instead of an implicit simulator "
                             "default; override for a write-queue-depth sensitivity sweep.")
    parser.add_argument("--output-dir", default=None,
                        help="Override the Config output directory (default: "
                             "simulators/nvmain/Config/). Use a separate directory for a "
                             "sensitivity sweep so it never touches the official configs.")
    return parser.parse_args()

def generate_nvmain_config(base_name, hw_metrics, target_freq_mhz, output_dir, arch_type, queue_size=32):
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
    # Epda/Epdpf/Epdps (active/precharge powerdown energy): MemoryController::HandleLowPower()
    # is now restored (src/MemoryController.cpp:1650) -- power-down is live for every
    # technology sharing this controller base, not ReRAM-specific. No NVSim datapoint
    # decomposes ReRAM leakage into a gatable-periphery vs. ungatable-crossbar split, and
    # no JEDEC-style power-down current spec exists for ReRAM the way it does for DDR5 --
    # so rather than fabricate a number, these are set to an explicit, honest placeholder
    # equal to the technology's own Eactstdby/Eprestdby: "assume power-gating saves
    # nothing beyond existing precharge-standby, pending real characterization." This
    # avoids crediting a physically-impossible free (zero-cost) power-down while still
    # letting the mechanism run. See Project_Book.typ Appendix A for the full disclosure;
    # upgrade this placeholder if a real ReRAM power-gating citation is found.
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
; Cycle-8 finding #11 fix: CPUFreq is the *host* issue-rate assumption used only
; by traceMain.cpp to rescale the trace-timestamp admission cutoff (see
; results/throughput_check/throughput_mechanism_report.md) -- it is decoupled
; from CLK (the device's own clock, which drives all timing/energy formulas)
; and fixed at 3000 (matching DDR5's existing calibration) for every technology,
; so every config assumes the same "modern server host" issuing the trace.
CPUFreq 3000

; --- Clock, Controller and Scaling ---
CLK {target_freq_mhz}
MEM_CTL FRFCFS
; QueueSize: the plain FRFCFS controller (MemControl/FRFCFS/FRFCFS.cpp) reads a
; single combined read+write QueueSize key (falls back to a hardcoded 32 if unset --
; the ReadQueueSize/WriteQueueSize keys seen in some bundled example configs belong
; to the different FRFCFS-WQF controller and are never read here). Previously left
; unset everywhere in this project, silently relying on that hardcoded default; now
; written explicitly so it's a documented, deliberate, sweepable parameter instead of
; an implicit simulator behavior. See documents/MBMM_Book_Typst/Post_Meeting_Notes_Shahar_2026-09-03.md
; item 5 and the write-queue-depth sensitivity study (Section 3.1.x) for why.
QueueSize {queue_size}
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
; per-chip leakage x devices_per_rank -- see comment above.
; Epda/Epdpf/Epdps: power-down is now live (HandleLowPower() restored). Set to an
; explicit honest placeholder (= Eactstdby/Eprestdby) rather than a fabricated real
; number -- see comment above and Project_Book.typ Appendix A.
;
; Cycle-7 finding #10: this template previously wrote "ReadEnergy"/"WriteEnergy",
; which NVMain never parses (no such Params field exists) -- every ReRAM run to
; date silently used NVMain's generic stock Erd/Ewr defaults (3.405401/1.023750 nJ)
; instead of these real, per-technology NVSim values. The correct keys, per
; SubArray.cpp's "flat energy model" branch (used whenever EnergyModel != "current"),
; are Erd (charged once per access at Activate(), row-open energy) and Ewr (charged
; once per access at Write()) -- both in nJ, direct, no unit conversion needed.
; Eopenrd (separate per-access burst-read term) and Ewrpb (per-bit write savings)
; are left at NVMain's stock defaults: NVSim's read_energy_nj/write_energy_nj are
; single lumped per-access figures with no open/burst or per-bit decomposition to
; derive those two from, and inventing a split would be tuning, not calibration.
Erd {r_energy}
Ewr {w_energy}
Eactstdby {e_standby_nj}
Eprestdby {e_standby_nj}
Epda {e_standby_nj}
Epdpf {e_standby_nj}
Epdps {e_standby_nj}

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
    output_dir = Path(args.output_dir) if args.output_dir else root_dir / "simulators" / "nvmain" / "Config"

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
            sys_name = generate_nvmain_config(model_name, metrics, args.freq, output_dir, arch, args.queue_size)
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