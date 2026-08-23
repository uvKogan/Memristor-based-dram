#!/usr/bin/env python3
"""
ReadVoltage Sensitivity Sweep
Technology: reram_22nm_1t1r_slc_full_dimm
Benchmarks: lbm_spec2017, gcc_spec2017
Voltages  : 1.12V, 1.40V, 1.68V (baseline ±20%)
Cycles    : 200M

Outputs per voltage:
  results/hardware/sweep_rv{tag}/reram_22nm_1t1r_slc_results.txt
  results/system/sweep_{tag}/stats_reram_22nm_1t1r_slc_full_dimm_{bench}.out
  results/sweep_voltage_results.json   (summary for plot_voltage_sweep.py)
"""

import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT         = Path(__file__).parent.absolute()
CELL_FILE    = ROOT / "configs" / "reram_22nm_1t1r_slc.cell"
NVSIM_EXE    = ROOT / "simulators" / "nvsim" / "nvsim"
NVSIM_DIR    = NVSIM_EXE.parent
NVMAIN_EXE   = ROOT / "simulators" / "nvmain" / "nvmain.fast"
BASE_CFG     = ROOT / "configs" / "reram_22nm_1t1r_slc.cfg"
BASE_NVMAIN  = ROOT / "simulators" / "nvmain" / "Config" / "reram_22nm_1t1r_slc_full_dimm.config"

VOLTAGES   = [1.12, 1.40, 1.68]
BENCHMARKS = ["lbm_spec2017", "gcc_spec2017"]
CYCLES     = 50_000_000
CLK_MHZ    = 800


def vtag(v):
    return f"rv{int(round(v * 100)):03d}"


def run_nvsim():
    for cell in (ROOT / "configs").glob("*.cell"):
        shutil.copy(cell, NVSIM_DIR)
    r = subprocess.run([str(NVSIM_EXE), str(BASE_CFG)], cwd=NVSIM_DIR,
                       capture_output=True, text=True)
    return r.stdout


def parse_nvsim(out):
    metrics = {}
    m = re.search(r'Read Latency\s*=\s*([\d.]+)ns', out)
    metrics['read_latency_ns'] = float(m.group(1)) if m else None

    m = re.search(r'Read Dynamic Energy\s*=\s*([\d.]+)(nJ|pJ|uJ)', out)
    if m:
        val, unit = float(m.group(1)), m.group(2)
        metrics['read_energy_nj'] = val if unit == 'nJ' else (val / 1000 if unit == 'pJ' else val * 1000)

    m = re.search(r'Leakage Power\s*=\s*([\d.]+)(W|mW|uW)', out)
    if m:
        val, unit = float(m.group(1)), m.group(2)
        metrics['leakage_mw'] = val if unit == 'mW' else (val * 1000 if unit == 'W' else val / 1000)

    return metrics


def make_nvmain_config(hw):
    """Patch ReadEnergy, tCAS/tRCD/tRAS, StandbyPower in the base NVMain config."""
    config = BASE_NVMAIN.read_text()

    if hw.get('read_energy_nj'):
        config = re.sub(r'^ReadEnergy [\d.eE+\-]+',
                        f"ReadEnergy {hw['read_energy_nj']:.4f}",
                        config, flags=re.MULTILINE)

    if hw.get('read_latency_ns'):
        tcas = max(1, math.ceil(hw['read_latency_ns'] * CLK_MHZ / 1000.0))
        for param in ('tCAS', 'tRCD', 'tRAS', 'tRTW'):
            config = re.sub(rf'^{param} \d+', f"{param} {tcas}",
                            config, flags=re.MULTILINE)

    if hw.get('leakage_mw'):
        standby_w = hw['leakage_mw'] * 64.0 / 1000.0
        config = re.sub(r'^StandbyPower [\d.eE+\-]+',
                        f"StandbyPower {standby_w:.6f}",
                        config, flags=re.MULTILINE)

    return config


def run_nvmain(config_text, bench, sweep_dir):
    trace = ROOT / "benchmarks" / f"{bench}.nvt"
    if not trace.exists():
        return None, f"Trace not found: {trace}"

    tmp_cfg = sweep_dir / "sweep_config.config"
    tmp_cfg.write_text(config_text)

    stats = sweep_dir / f"stats_reram_22nm_1t1r_slc_full_dimm_{bench}.out"
    with open(stats, "w") as f:
        p = subprocess.Popen([str(NVMAIN_EXE), str(tmp_cfg), str(trace), str(CYCLES)],
                             stdout=f, stderr=subprocess.STDOUT)
        # Print a heartbeat dot every 20s so the harness doesn't kill us during long runs
        import time
        while p.poll() is None:
            time.sleep(20)
            print(".", end="", flush=True)
        rc = p.wait()

    if rc != 0:
        return None, f"NVMain failed (code {rc}) for {bench}"
    return stats, None


def parse_system(stats_file):
    content = stats_file.read_text()

    lat_vals = re.findall(r'averageTotalLatency\s+([\d.eE+\-]+)', content, re.IGNORECASE)
    latency = sum(float(v) for v in lat_vals) / len(lat_vals) if lat_vals else None

    pow_vals = re.findall(r'totalpower\s+([\d.eE+\-]+)', content, re.IGNORECASE)
    valid = [float(v) for v in pow_vals if 0.01 <= float(v) <= 200.0]
    power = max(valid) if valid else None

    return latency, power


def main():
    print("=" * 70)
    print("MBMM ReadVoltage Sensitivity Sweep")
    print(f"  Voltages  : {VOLTAGES} V")
    print(f"  Benchmarks: {BENCHMARKS}")
    print(f"  Cycles    : {CYCLES:,}")
    print("=" * 70)

    errors = []
    results = {}
    original_cell = CELL_FILE.read_text()

    try:
        for voltage in VOLTAGES:
            tag = vtag(voltage)
            sweep_sys = ROOT / "results" / "system" / f"sweep_{tag}"
            sweep_hw  = ROOT / "results" / "hardware" / f"sweep_{tag}"
            sweep_sys.mkdir(parents=True, exist_ok=True)
            sweep_hw.mkdir(parents=True, exist_ok=True)

            print(f"\n{'='*50}")
            print(f"  ReadVoltage = {voltage:.2f}V")
            print(f"{'='*50}")

            patched = re.sub(r'-ReadVoltage \(V\): [\d.]+',
                             f'-ReadVoltage (V): {voltage:.2f}', original_cell)
            CELL_FILE.write_text(patched)
            print(f"  [1/3] Cell patched to ReadVoltage={voltage:.2f}V")

            print(f"  [2/3] NVSim...", end=" ", flush=True)
            nvsim_out = run_nvsim()
            (sweep_hw / "reram_22nm_1t1r_slc_results.txt").write_text(nvsim_out)

            if "Read Latency" not in nvsim_out:
                msg = f"NVSim no output at {voltage:.2f}V"
                print(f"FAIL — {msg}")
                errors.append(msg)
                results[voltage] = {'hw': {}, 'system': {}}
                continue

            hw = parse_nvsim(nvsim_out)
            print(f"OK  lat={hw.get('read_latency_ns','?'):.3f}ns  "
                  f"E={hw.get('read_energy_nj','?'):.4f}nJ  "
                  f"leak={hw.get('leakage_mw','?'):.1f}mW")

            results[voltage] = {'hw': hw, 'system': {}}
            config_text = make_nvmain_config(hw)

            print(f"  [3/3] NVMain ({CYCLES//1_000_000}M cycles)...")
            for bench in BENCHMARKS:
                print(f"    {bench}...", end=" ", flush=True)
                sf, err = run_nvmain(config_text, bench, sweep_sys)
                if err:
                    print(f"FAIL — {err}")
                    errors.append(err)
                    continue
                lat, pwr = parse_system(sf)
                pdp = lat * pwr if (lat and pwr) else None
                results[voltage]['system'][bench] = {
                    'avg_total_latency_cycles': lat,
                    'power_w': pwr,
                    'pdp': pdp
                }
                lat_s = f"{lat:.1f}" if lat else "?"
                pwr_s = f"{pwr:.4f}" if pwr else "?"
                pdp_s = f"{pdp:.1f}" if pdp else "?"
                print(f"lat={lat_s}cyc  pwr={pwr_s}W  pdp={pdp_s}")

    finally:
        CELL_FILE.write_text(original_cell)
        print(f"\n[RESTORE] {CELL_FILE.name} → ReadVoltage=1.40V")

    summary = ROOT / "results" / "sweep_voltage_results.json"
    with open(summary, "w") as f:
        json.dump({str(k): v for k, v in results.items()}, f, indent=2)
    print(f"[OK] {summary}")

    if errors:
        err_log = ROOT / "sweep_errors.log"
        err_log.write_text("\n".join(errors))
        print(f"[WARN] {len(errors)} error(s) → {err_log}")

    print("\nDone. Run: python3 plot_voltage_sweep.py")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
