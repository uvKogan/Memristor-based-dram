import re
import os
import sys
import argparse
from pathlib import Path

# T2.5 fix round 1: the delivered-bandwidth/end-to-end-latency extractors
# and the clock-resolution helpers live in process_metrics.py; this script
# imports them instead of keeping its own duplicate copies, so there is one
# implementation of each formula, not two that can drift apart. No import
# cycle: process_metrics.py does not import this module (it can't -- this
# file's name starts with a digit and isn't a valid module name), and
# process_metrics is importable without side effects (no argparse/main() call
# at import time).
import process_metrics as pm

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
    parser.add_argument("--allow-parse-failures", action="store_true",
                        help="T2.5 fix round 2: downgrade per-file parse failures from a "
                             "fatal condition (exit 1) to a WARNING (exit 0). The rows that "
                             "DID parse are always printed regardless of this flag -- one bad "
                             "file never hides the others; this flag only controls the exit "
                             "code, for knowingly processing an old/partial dataset that has "
                             "files this version can't parse.")
    return parser.parse_args()

def extract_metrics(filename):
    """Parses NVMain output for key performance and energy metrics."""
    if not os.path.exists(filename):
        return None

    with open(filename, 'r') as f:
        content = f.read()

    # Precise regex patterns based on verified NVMain terminal output.
    # T2.5: the old "Bandwidth" column (NVMain's bank0.bandwidth, a per-bank
    # instantaneous figure) is kept only as a cross-check; Delivered BW below
    # is the real, DIMM-wide delivered-bandwidth number.
    patterns = {
        "Total Writes": r"totalWriteRequests\s+(\d+)",
        "Avg Latency (cyc)": r"averageTotalLatency\s+(\d+)",
        "Total Power (W)": r"rank0\.totalPower\s+([\d\.e-]+)W",
        "NVMain BW (x-check)": r"bank0\.bandwidth\s+([\d\.]+MB/s)"
    }

    results = {}
    for label, pattern in patterns.items():
        match = re.search(pattern, content)
        results[label] = match.group(1) if match else "N/A"

    # F1 (final-review C1): the printed rank totalPower is NOT the rank's total
    # power for an EnergyModel-current run (every DDR5 config). NVMain divides
    # backgroundPower by the rank's device count and never multiplies it back
    # (StandardRank.cpp:992 against :1015-1017), so the printed rank totalPower
    # carries one device's background against the whole rank's activate, burst
    # and refresh. This column is a per-rank diagnostic display, but it must
    # still not show a number that is physically impossible under the config's
    # own currents, so the same correction process_metrics.py applies to the
    # CSVs is applied here, through the same helpers. Energy-mode technologies
    # (ReRAM NonVolatile, PCM energy) get factor 1 and are untouched. A config
    # that cannot be resolved raises, and main()'s per-file try/except reports
    # it as a parse failure -- no silent default device count.
    if results["Total Power (W)"] != "N/A":
        factor = pm.background_power_device_factor(content, stats_name=str(filename))
        if factor != 1:
            bg = re.search(r"rank0\.backgroundPower\s+([\d\.eE+-]+)W", content)
            if bg is None:
                raise ValueError(
                    f"{filename}: EnergyModel-current stats file with a rank0.totalPower "
                    f"but no rank0.backgroundPower, so the per-device background "
                    f"undercount cannot be corrected."
                )
            corrected = float(results["Total Power (W)"]) + (factor - 1) * float(bg.group(1))
            results["Total Power (W)"] = f"{corrected:.6g}"

    # T2.5 fix round 1: this script has no per-technology classification (it
    # just globs .out files), so `technology` is unknown here -- pm.resolve_
    # clocks_mhz falls back to CLOCK_FREQUENCY_MHZ.get(None, 800) == 800 only
    # if the file's own clock-diagnostic line is absent, same generic default
    # this script always used pre-T2.5. When the line IS present (every real
    # NVMain run), the run's own CLK/CPUFreq are used, so a clock-sensitivity
    # run prints correctly here too, not just in the CSVs.
    clk_mhz, cpufreq_mhz = pm.resolve_clocks_mhz(content, None, filename=str(filename))

    # T2.5: end-to-end latency (now in ns, using this run's own resolved CLK
    # -- a small change once resolve_clocks_mhz existed, see fix-round report),
    # completed requests, delivered bandwidth.
    e2e_ns = pm.extract_end_to_end_latency_ns(content, clk_mhz)
    results["E2E Lat (ns)"] = f"{e2e_ns:.1f}" if e2e_ns is not None else "N/A"

    completed_requests, delivered_bw_mbps = pm.extract_completed_requests_and_bandwidth(
        content, cpufreq_mhz)
    results["Completed Reqs"] = str(completed_requests) if completed_requests is not None else "N/A"
    results["Delivered BW (MB/s)"] = (f"{delivered_bw_mbps:.2f}" if delivered_bw_mbps is not None
                                       else "N/A")

    return results

def main():
    """Returns True on success (exit 0), False on a fatal condition (exit 1).

    T2.5 fix round 2: pre-existing early-return paths (missing results dir,
    no files specified/found) keep their original exit-0 behavior -- they
    return True explicitly now instead of falling off the end with an
    implicit None, so the new non-zero-exit path below (per-file parse
    failures) is the only thing that changes this script's exit code.
    """
    args = setup_args()
    root_dir = get_project_root()
    # NEW: Targeted results subdirectory for system simulation stats
    results_dir = root_dir / "results" / "system"

    target_files = []

    if not results_dir.exists():
        print(f"[!] Results directory not found: {results_dir}")
        print("    Ensure Step 4 (4_execute_simulation.py) has been run.")
        return True

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
        return True

    if not target_files:
        print(f"[!] No valid .out files found in {results_dir}")
        return True

    header = (f"{'FILE / MODEL':<45} | {'WRITES':<7} | {'LATENCY':<7} | {'E2E(ns)':<10} | "
              f"{'POWER (W)':<10} | {'REQS':<8} | {'DELIV BW(MB/s)':<15} | {'NVMain BW(x-chk)':<17}")
    rule = "=" * len(header)

    print(rule)
    print(header)
    print("-" * len(header))

    # T2.5 fix round 2: one bad file (e.g. a stats file whose clock-diagnostic
    # lines disagree, raising inside resolve_clocks_mhz/extract_clocks_mhz)
    # must not crash the whole report -- each file gets its own try/except,
    # same principle and same --allow-parse-failures flag as process_metrics.py.
    failures = []

    for file_path in sorted(target_files):
        try:
            metrics = extract_metrics(str(file_path))
        except Exception as e:
            print(f"{file_path.name:<45} | [ERROR: FAILED TO PARSE] {e}")
            failures.append((file_path.name, str(e)))
            continue

        if metrics:
            # Shorten filename for clean display
            display_name = file_path.name[:42] + ".." if len(file_path.name) > 44 else file_path.name
            print(f"{display_name:<45} | "
                  f"{metrics['Total Writes']:<7} | "
                  f"{metrics['Avg Latency (cyc)']:<7} | "
                  f"{metrics['E2E Lat (ns)']:<10} | "
                  f"{metrics['Total Power (W)']:<10} | "
                  f"{metrics['Completed Reqs']:<8} | "
                  f"{metrics['Delivered BW (MB/s)']:<15} | "
                  f"{metrics['NVMain BW (x-check)']:<17}")
        else:
            print(f"{file_path.name:<45} | [ERROR: FAILED TO PARSE]")
            failures.append((file_path.name, "extract_metrics returned None (file not found)"))

    print(rule)
    print("STEP 5 COMPLETE: Summary generated successfully.")

    if failures:
        tag = "[WARNING]" if args.allow_parse_failures else "[ERROR]"
        print(f"\n{tag} {len(failures)} file(s) failed to parse:")
        for fname, err in failures:
            print(f"  - {fname}: {err}")
        if args.allow_parse_failures:
            print("[WARNING] --allow-parse-failures set: continuing with exit 0 despite the "
                  "failure(s) above.")
        else:
            print("[ERROR] Failing (exit 1) because of the parse failure(s) above. Pass "
                  "--allow-parse-failures to continue with a WARNING instead, once these are "
                  "understood/expected.")
            return False

    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)