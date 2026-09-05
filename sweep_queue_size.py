"""
MBMM: Write-Queue-Depth Sensitivity Sweep

Answers Shahar Kvatinsky's meeting note #5 (documents/MBMM_Book_Typst/
Post_Meeting_Notes_Shahar_2026-09-03.md): does the FRFCFS memory controller's
QueueSize (added as an explicit, documented parameter in 3_gen_nvmain_config.py --
previously an implicit NVMain default) change how much of LBM's write-heavy trace
completes within the fixed matched-host simulation window?

Reuses the real 3_gen_nvmain_config.py generator (subprocess call, not reimplemented)
for each swept value, writing into an isolated Config subdirectory per value so the
official simulators/nvmain/Config/ configs used by the main results matrix are never
touched. Skips NVSim/hardware extraction entirely (QueueSize is a system/controller
parameter -- it does not affect device-level hardware metrics), so this only re-runs
NVMain, directly, per value -- no full mbmm_master.py pipeline invocation needed.

Follows the project's existing single-value sensitivity-sweep convention
(configs/hrs_sweep/, archive/system/sweep_rv<N>/, results/sweep_voltage_results.json)
rather than the main 96-run matrix.

Usage:
    python3 sweep_queue_size.py --values 16,32,48,64,96,128 --model reram_22nm_1t1r_slc \\
        --archs single,full_dimm --trace lbm_spec2017.nvt --cycles 66666667
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path


def get_project_root():
    return Path(__file__).parent.absolute()


def setup_args():
    parser = argparse.ArgumentParser(description="MBMM: Write-Queue-Depth Sensitivity Sweep")
    parser.add_argument("--values", default="16,32,48,64,96,128",
                        help="Comma-separated QueueSize values to sweep (default includes 32, "
                             "the current baseline, as a built-in reference point).")
    parser.add_argument("--model", default="reram_22nm_1t1r_slc", help="Base hardware model name.")
    parser.add_argument("--archs", default="single,full_dimm",
                        help="Comma-separated architectures to test (single/8chip/16chip/full_dimm).")
    parser.add_argument("--trace", default="lbm_spec2017.nvt", help="Trace file name.")
    parser.add_argument("--cycles", type=int, default=66666667,
                        help="Input (host) cycles -- 66666667 reproduces the book's own "
                             "83.33ms matched-host window at ReRAM's 800MHz/CPUFreq 3000.")
    parser.add_argument("--freq", type=int, default=800, help="Target frequency in MHz.")
    parser.add_argument("--timeout", type=int, default=240,
                        help="Per-run wall-clock timeout in seconds.")
    return parser.parse_args()


def parse_stats(stats_path):
    text = stats_path.read_text(errors="replace")

    def grab(pattern):
        m = re.search(pattern, text, re.MULTILINE)
        return float(m.group(1)) if m else None

    reads = grab(r"^i0\.defaultMemory\.channel0\.FRFCFS\.mem_reads\s+(\d+)")
    writes = grab(r"^i0\.defaultMemory\.channel0\.FRFCFS\.mem_writes\s+(\d+)")
    avg_total_latency = grab(r"^i0\.defaultMemory\.channel0\.FRFCFS\.averageTotalLatency\s+([\d.]+)")
    return reads, writes, avg_total_latency


def run_sweep():
    args = setup_args()
    root = get_project_root()
    values = [int(v.strip()) for v in args.values.split(",")]
    archs = [a.strip() for a in args.archs.split(",")]
    trace_path = root / "benchmarks" / args.trace
    trace_stem = Path(args.trace).stem
    nvmain_exe = root / "simulators" / "nvmain" / "nvmain.fast"

    if not trace_path.exists():
        print(f"[!] Trace not found: {trace_path}")
        sys.exit(1)

    sweep_config_root = root / "simulators" / "nvmain" / "Config" / "sweeps" / "queue_size"
    sweep_results_root = root / "results" / "system" / "queue_size_sweep"
    sweep_config_root.mkdir(parents=True, exist_ok=True)
    sweep_results_root.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"WRITE-QUEUE-DEPTH SENSITIVITY SWEEP: {args.model} / {trace_stem}")
    print(f"Values: {values} | Archs: {archs} | Cycles: {args.cycles} (host)")
    print("=" * 70)

    all_results = []

    for qs in values:
        out_dir = sweep_config_root / f"qs{qs}"
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n>>> Generating configs for QueueSize={qs}")
        gen_proc = subprocess.run(
            [sys.executable, "3_gen_nvmain_config.py",
             "--freq", str(args.freq), "--queue-size", str(qs),
             "--output-dir", str(out_dir)],
            cwd=root, capture_output=True, text=True,
        )
        if gen_proc.returncode != 0:
            print(f"    [!] Config generation failed: {gen_proc.stderr[-500:]}")
            continue

        for arch in archs:
            config_path = out_dir / f"{args.model}_{arch}.config"
            if not config_path.exists():
                print(f"    [!] Missing generated config: {config_path}")
                continue

            stats_path = sweep_results_root / f"stats_qs{qs}_{args.model}_{arch}_{trace_stem}.out"
            print(f"    Running QueueSize={qs}, arch={arch} ...", end=" ", flush=True)

            start = time.time()
            with open(stats_path, "w") as out_f:
                proc = subprocess.run(
                    ["timeout", str(args.timeout), str(nvmain_exe),
                     str(config_path), str(trace_path), str(args.cycles)],
                    cwd=root, stdout=out_f, stderr=subprocess.STDOUT,
                )
            elapsed = time.time() - start

            row = {"queue_size": qs, "arch": arch, "wall_time_s": round(elapsed, 1)}
            if proc.returncode == 124:
                row["status"] = "timeout"
                print(f"TIMEOUT ({elapsed:.0f}s)")
            elif proc.returncode != 0:
                row["status"] = "crash"
                print(f"CRASH (exit {proc.returncode})")
            else:
                reads, writes, avg_lat = parse_stats(stats_path)
                if reads is None or writes is None:
                    row["status"] = "crash"
                    print("CRASH (no stats found)")
                else:
                    row.update({
                        "status": "ok",
                        "mem_reads": int(reads),
                        "mem_writes": int(writes),
                        "total_completed": int(reads + writes),
                        "avg_total_latency_ns": avg_lat,
                    })
                    print(f"completed={int(reads + writes)} avgLatency={avg_lat} ({elapsed:.0f}s)")

            all_results.append(row)

    summary_path = root / "results" / "queue_size_sweep_results.json"
    with open(summary_path, "w") as f:
        json.dump({
            "model": args.model, "trace": trace_stem, "cycles": args.cycles,
            "freq_mhz": args.freq, "results": all_results,
        }, f, indent=2)

    print("\n" + "=" * 70)
    print(f"SWEEP COMPLETE. Summary: {summary_path}")
    print("=" * 70)
    print(f"\n{'QueueSize':>10} {'Arch':>10} {'Status':>8} {'Completed':>12} {'AvgLatency(ns)':>15}")
    for row in all_results:
        print(f"{row['queue_size']:>10} {row['arch']:>10} {row['status']:>8} "
              f"{row.get('total_completed', '-'):>12} {row.get('avg_total_latency_ns', '-'):>15}")


if __name__ == "__main__":
    run_sweep()
