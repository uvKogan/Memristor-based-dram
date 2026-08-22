import re
import json
import os
import argparse
from pathlib import Path

def get_project_root():
    return Path(__file__).parent.absolute()

def parse_nvsim_output(file_path):
    """Extracts raw SLC hardware metrics and Capacity from NVSim output."""
    metrics = {}
    if not os.path.exists(file_path):
        return None
        
    with open(file_path, 'r') as f:
        content = f.read()
        try:
            # --- NEW: CAPACITY EXTRACTION (Standardized to GB) ---
            # Looks for "Capacity : 128MB" in the NVSim RESULT header
            cap_match = re.search(r"Capacity\s*:\s*(\d+)(MB|GB|KB)", content)
            if cap_match:
                val, unit = float(cap_match.group(1)), cap_match.group(2)
                if unit == 'MB': metrics['capacity_gb'] = val / 1024.0
                elif unit == 'GB': metrics['capacity_gb'] = val
                else: metrics['capacity_gb'] = val / (1024.0**2)
            else:
                metrics['capacity_gb'] = 0.125 # Default fallback

            # Latency (ns)
            metrics['read_latency_ns'] = float(re.search(r"Read Latency\s*=\s*([\d\.]+)ns", content).group(1))
            write_match = re.search(r"(?:SET|Write)\s+Latency\s*=\s*([\d\.]+)ns", content)
            metrics['write_latency_ns'] = float(write_match.group(1)) if write_match else 0.0
            
            # Energy (Standardized to nJ)
            read_e_match = re.search(r"Read Dynamic Energy\s*=\s*([\d\.]+)(nJ|pJ|uJ)", content)
            if read_e_match:
                val, unit = float(read_e_match.group(1)), read_e_match.group(2)
                metrics['read_energy_nj'] = val if unit == 'nJ' else (val/1000.0 if unit == 'pJ' else val*1000.0)
            
            write_e_match = re.search(r"(?:SET|Write)\s+Dynamic Energy\s*=\s*([\d\.]+)(nJ|pJ|uJ)", content)
            if write_e_match:
                val, unit = float(write_e_match.group(1)), write_e_match.group(2)
                metrics['write_energy_nj'] = val if unit == 'nJ' else (val/1000.0 if unit == 'pJ' else val*1000.0)
            
            # Leakage (mW) and Area (mm^2)
            leak_match = re.search(r"Leakage Power\s*=\s*([\d\.]+)(W|mW|uW|nW)", content)
            if leak_match:
                val, unit = float(leak_match.group(1)), leak_match.group(2)
                metrics['leakage_mw'] = val if unit == 'mW' else (val*1000.0 if unit == 'W' else val/1000.0)
            
            area_match = re.search(r"Total Area = .* = ([\d\.]+)mm\^2", content)
            metrics['area_mm2'] = float(area_match.group(1)) if area_match else 0.0

        except Exception as e:
            print(f"[ERROR] Regex failed for {file_path}: {e}")
            return None
    return metrics

def apply_mlc_penalty(slc_metrics):
    """Applies Phase 5 Analytical Penalties and DOUBLES capacity."""
    mlc = slc_metrics.copy()
    # Performance penalties derived from EMBER, same author group, two papers:
    # - Upton et al., ESSCIRC 2023 (Table I) for read energy: 1b/cell vs 2b/cell
    #   1.0/1.1 pJ/bit (1.1x). (An earlier draft paired EMBER's 12ns read time
    #   with a "23ns" figure for a read-latency multiplier -- confirmed by
    #   direct table read to be a DIFFERENT competing macro's own 1b/cell read
    #   time from the same comparison table, not EMBER's 2b/cell number, which
    #   the ESSCIRC paper never reports. Corrected below using EMBER's own data.)
    # - Levy et al., IEEE JSSC 2024, DOI 10.1109/JSSC.2024.3387566 (Section V.A
    #   / Abstract) for read latency and write: 1b/cell vs 2b/cell read
    #   bandwidth 2.4/1.6 Gbps -> 1.5x read-latency penalty (same
    #   bandwidth-ratio methodology as the write-side derivation below);
    #   write-verify bandwidth 12.4/3.8 Mbps -> 3.263x write-latency penalty;
    #   write-verify energy 0.40/1.2 nJ/bit -> 3.0x write-energy penalty.
    mlc['read_latency_ns'] *= 1.5
    mlc['write_latency_ns'] *= 3.263
    mlc['read_energy_nj'] *= 1.1
    mlc['write_energy_nj'] *= 3.0
    
    # Capacity Scaling: MLC doubles bit storage volume [cite: 933, 939]
    mlc['capacity_gb'] *= 2.0
    
    mlc['is_analytical_mlc'] = True
    return mlc

def main():
    root_dir = get_project_root()
    hw_results_dir = root_dir / "results" / "hardware"
    output_path = root_dir / "results" / "hardware_metrics.json"

    all_data = {}
    print("=" * 60)
    print("MBMM STEP 2: DUAL-TRACK HARDWARE EXTRACTION (SLC + MLC)")
    print("=" * 60)

    for file_path in hw_results_dir.glob("*_results.txt"):
        base_name = file_path.stem.replace("_results", "").replace("_slc", "")
        
        # 1. Process SLC Track
        print(f">>> Processing Baseline: {base_name}...")
        slc_metrics = parse_nvsim_output(str(file_path))
        if slc_metrics:
            slc_metrics['is_analytical_mlc'] = False
            all_data[f"{base_name}_slc"] = slc_metrics
            
            # 2. Programmatically Generate MLC Track (Doubling Volume)
            print(f"    [GEN] Generating Analytical MLC variant for {base_name}...")
            all_data[f"{base_name}_mlc"] = apply_mlc_penalty(slc_metrics)

    if all_data:
        with open(output_path, 'w') as f:
            json.dump(all_data, f, indent=4)
        print(f"\nSUCCESS: {len(all_data)} tracks (SLC/MLC pairs) saved to JSON.")

if __name__ == "__main__":
    main()