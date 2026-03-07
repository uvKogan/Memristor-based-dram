import re
import os
import argparse
from pathlib import Path

def get_project_root():
    """Dynamically finds the MBMM project root directory."""
    return Path(__file__).parent.absolute()

def setup_args():
    parser = argparse.ArgumentParser(
        description="MBMM Step 5: Extract and Summarize NVMain Simulation Results",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Execution Examples:
  python3 5_summary_report.py --latest
  python3 5_summary_report.py --files results/system/stats_model_*.out
  python3 5_summary_report.py --compare
        """
    )
    parser.add_argument("--files", nargs="+", help="Specific NVMain .out files to parse.")
    parser.add_argument("--latest", action="store_true", help="Automatically parse the most recent .out file in results/system/.")
    parser.add_argument("--compare", action="store_true", help="Parse and compare all .out files in results/system/.")
    return parser.parse_args()

def extract_metrics(filename):
    """Parses NVMain output for key performance and energy metrics."""
    if not os.path.exists(filename):
        return None
    
    with open(filename, 'r') as f:
        content = f.read()
    
    # Precise regex patterns based on verified NVMain terminal output
    patterns = {
        "Total Writes": r"totalWriteRequests\s+(\d+)",
        "Avg Latency (cyc)": r"averageTotalLatency\s+(\d+)",
        "Total Power (W)": r"rank0\.totalPower\s+([\d\.e-]+)W",
        "Bandwidth": r"bank0\.bandwidth\s+([\d\.]+MB/s)"
    }
    
    results = {}
    for label, pattern in patterns.items():
        match = re.search(pattern, content)
        results[label] = match.group(1) if match else "N/A"
    
    return results

def main():
    args = setup_args()
    root_dir = get_project_root()
    # NEW: Targeted results subdirectory for system simulation stats
    results_dir = root_dir / "results" / "system"
    
    target_files = []
    
    if not results_dir.exists():
        print(f"[!] Results directory not found: {results_dir}")
        print("    Ensure Step 4 (4_execute_simulation.py) has been run.")
        return

    if args.latest:
        # Find the newest file by modification time in results/system/
        files = list(results_dir.glob("*.out"))
        if files:
            target_files = [max(files, key=os.path.getmtime)]
    elif args.compare:
        target_files = list(results_dir.glob("*.out"))
    elif args.files:
        target_files = [Path(f) for f in args.files]
    else:
        print("[!] No files specified. Use --latest, --compare, or --files. Use --help for info.")
        return

    if not target_files:
        print(f"[!] No valid .out files found in {results_dir}")
        return

    print("=" * 85)
    print(f"{'FILE / MODEL':<45} | {'WRITES':<7} | {'LATENCY':<7} | {'POWER (W)':<10}")
    print("-" * 85)

    for file_path in sorted(target_files):
        metrics = extract_metrics(str(file_path))
        if metrics:
            # Shorten filename for clean display
            display_name = file_path.name[:42] + ".." if len(file_path.name) > 44 else file_path.name
            print(f"{display_name:<45} | "
                  f"{metrics['Total Writes']:<7} | "
                  f"{metrics['Avg Latency (cyc)']:<7} | "
                  f"{metrics['Total Power (W)']:<10}")
        else:
            print(f"{file_path.name:<45} | [ERROR: FAILED TO PARSE]")

    print("=" * 85)
    print("STEP 5 COMPLETE: Summary generated successfully.")

if __name__ == "__main__":
    main()