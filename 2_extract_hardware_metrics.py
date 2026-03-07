import re
import json
import os
import argparse
from pathlib import Path

def get_project_root():
    """Dynamically finds the MBMM project root directory."""
    return Path(__file__).parent.absolute()

def parse_nvsim_output(file_path):
    """Extracts performance, power, and area metrics from NVSim result text."""
    metrics = {}
    if not os.path.exists(file_path):
        print(f"[!] File not found: {file_path}")
        return None
        
    with open(file_path, 'r') as f:
        content = f.read()
        try:
            # Latency Extraction (ns)
            metrics['read_latency_ns'] = float(re.search(r"Read Latency\s*=\s*([\d\.]+)ns", content).group(1))
            write_match = re.search(r"(?:SET|Write)\s+Latency\s*=\s*([\d\.]+)ns", content)
            metrics['write_latency_ns'] = float(write_match.group(1)) if write_match else 0.0
            
            # Energy Extraction (Standardized to nJ)
            read_e_match = re.search(r"Read Dynamic Energy\s*=\s*([\d\.]+)(nJ|pJ|uJ)", content)
            if read_e_match:
                val, unit = float(read_e_match.group(1)), read_e_match.group(2)
                metrics['read_energy_nj'] = val if unit == 'nJ' else (val/1000.0 if unit == 'pJ' else val*1000.0)
            
            write_e_match = re.search(r"(?:SET|Write)\s+Dynamic Energy\s*=\s*([\d\.]+)(nJ|pJ|uJ)", content)
            if write_e_match:
                val, unit = float(write_e_match.group(1)), write_e_match.group(2)
                metrics['write_energy_nj'] = val if unit == 'nJ' else (val/1000.0 if unit == 'pJ' else val*1000.0)
            
            # Leakage Power (Standardized to mW)
            leak_match = re.search(r"Leakage Power\s*=\s*([\d\.]+)(W|mW|uW|nW)", content)
            if leak_match:
                val, unit = float(leak_match.group(1)), leak_match.group(2)
                metrics['leakage_mw'] = val if unit == 'mW' else (val*1000.0 if unit == 'W' else val/1000.0)
            
            # Area Extraction (mm^2)
            area_match = re.search(r"Total Area = .* = ([\d\.]+)mm\^2", content)
            metrics['area_mm2'] = float(area_match.group(1)) if area_match else 0.0

            # Geometry and Organization
            bank_match = re.search(r"Bank Organization:\s*(\d+)", content)
            metrics['banks'] = int(bank_match.group(1)) if bank_match else 1
            
            sub_match = re.search(r"Subarray Size\s*:\s*(\d+)\s*Rows x\s*(\d+)\s*Columns", content)
            if sub_match:
                metrics['rows'] = int(sub_match.group(1))
                metrics['cols'] = int(sub_match.group(2))

            # Audit Trail
            metrics['source_file'] = os.path.basename(file_path)

        except Exception as e:
            print(f"[ERROR] Regex extraction failed for {file_path}: {e}")
            return None
    return metrics

def setup_args():
    parser = argparse.ArgumentParser(
        description="MBMM Step 2: Extract Hardware Metrics from NVSim Results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Examples:
  python3 2_extract_hardware_metrics.py --all
  python3 2_extract_hardware_metrics.py --files results/hardware/my_model_results.txt
  python3 2_extract_hardware_metrics.py --output custom_results.json --all
        """
    )
    parser.add_argument("--files", nargs="+", help="Specific result .txt files to parse.")
    parser.add_argument("--all", action="store_true", help="Automatically process all *_results.txt files in results/hardware/.")
    parser.add_argument("--output", default="hardware_metrics.json", help="Output JSON filename (saved in results/).")
    return parser.parse_args()

def main():
    args = setup_args()
    root_dir = get_project_root()
    
    # NEW: Define paths relative to the results directory
    hw_results_dir = root_dir / "results" / "hardware"
    output_path = root_dir / "results" / args.output

    # Find target files
    target_files = []
    if args.all:
        target_files = list(hw_results_dir.glob("*_results.txt"))
    elif args.files:
        target_files = [Path(f) for f in args.files]
    else:
        print(f"[!] No input files specified. Use --all to check {hw_results_dir.relative_to(root_dir)}/")
        return

    all_data = {}
    
    print("=" * 60)
    print("MBMM STEP 2: HARDWARE METRICS EXTRACTION")
    print("=" * 60)

    for file_path in target_files:
        model_name = file_path.stem.replace("_results", "")
        print(f">>> Processing: {model_name}...")
        
        metrics = parse_nvsim_output(str(file_path))
        if metrics:
            all_data[model_name] = metrics
            print(f"    [OK] Extracted {len(metrics)} metrics.")

    # Write the master JSON file to the results directory
    if all_data:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(all_data, f, indent=4)
        print("\n" + "=" * 60)
        print(f"SUCCESS: {len(all_data)} models saved to {output_path.relative_to(root_dir)}")
        print("=" * 60)

if __name__ == "__main__":
    main()