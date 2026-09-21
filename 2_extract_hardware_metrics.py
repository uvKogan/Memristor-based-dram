import re
import json
import os
import sys
import argparse
from pathlib import Path

def get_project_root():
    return Path(__file__).parent.absolute()


class NVSimParseError(ValueError):
    """An NVSim result file is missing a field this stage must extract.

    I5 (final review 2026-09): a parse failure used to drop that model
    silently and let the script exit 0, so the previous
    results/hardware_metrics.json stayed live and Stage 3 built configs from
    stale hardware. Every failure now names the file and the field and stops
    the stage.
    """

# T2.6 fix round 1: per-architecture result files that 4_execute_simulation.py
# writes into results/hardware/ during Stage 4 (e.g.
# "reram_22nm_1t1r_slc_full_dimm_results.txt") are re-runs of the same base
# cfg's forced organization at a different chip count -- not independent
# hardware base models. If they are left in results/hardware/ when this
# script next runs (e.g. a second pipeline run in the same results directory,
# without clearing it first), the glob below would otherwise treat each one
# as its own base and inject stale entries into hardware_metrics.json, which
# 3_gen_nvmain_config.py would then build double-suffixed NVMain configs
# from (e.g. "..._full_dimm_slc_single.config"). "_1024" (the T2.6
# sensitivity cfg) is not an architecture suffix and must NOT be excluded.
ARCHITECTURE_SUFFIXES = ("_single", "_8chip", "_16chip", "_full_dimm")

def is_architecture_suffixed_result(file_path):
    """True if `file_path`'s stem, with a trailing "_results" removed, ends
    in one of the per-architecture suffixes (_single/_8chip/_16chip/
    _full_dimm). See ARCHITECTURE_SUFFIXES above for why these are skipped."""
    stem = Path(file_path).stem
    if stem.endswith("_results"):
        stem = stem[: -len("_results")]
    return stem.endswith(ARCHITECTURE_SUFFIXES)

def base_name_from_result_stem(stem):
    """Derive a hardware_metrics.json base name from a Stage-1 result file's stem.

    E.g. "reram_22nm_1t1r_slc_1024_results" -> "reram_22nm_1t1r_1024" (the "_1024"
    sensitivity token, if present, ends up AFTER "_slc" is stripped, not before it --
    see mbmm_master.reram_factory_bases()'s docstring for why this token-order flip is
    deliberate and left as-is). Factored out (T5.1 step 2 fix round 1, Minor-2) so
    tests exercise the real derivation instead of re-implementing it inline.
    """
    return stem.replace("_results", "").replace("_slc", "")


def parse_nvsim_output(file_path):
    """Extracts raw SLC hardware metrics and Capacity from NVSim output.

    Every field below is required. A field the file does not carry raises
    NVSimParseError naming the file and the field (I5): a hardware entry with
    a missing or invented number silently becomes an NVMain config, a
    simulation and a published result, so there is no safe default to fall
    back on here.

    Raises FileNotFoundError if `file_path` does not exist.
    """
    metrics = {}
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"NVSim result file not found: {file_path}")

    with open(file_path, 'r') as f:
        content = f.read()

    def _require(pattern, field, flags=0):
        m = re.search(pattern, content, flags)
        if not m:
            raise NVSimParseError(
                f"{file_path}: NVSim result carries no {field!r} "
                f"(no match for {pattern!r}). The run did not converge, or its "
                f"output format changed; this model cannot be turned into an "
                f"NVMain config without it.")
        return m

    # --- CAPACITY EXTRACTION (Standardized to GB) ---
    # Looks for "Capacity : 128MB" in the NVSim RESULT header
    cap_match = _require(r"Capacity\s*:\s*(\d+)(MB|GB|KB)", "Capacity")
    val, unit = float(cap_match.group(1)), cap_match.group(2)
    if unit == 'MB': metrics['capacity_gb'] = val / 1024.0
    elif unit == 'GB': metrics['capacity_gb'] = val
    else: metrics['capacity_gb'] = val / (1024.0**2)

    # Latency (ns). The write-side pattern deliberately matches NVSim's
    # "RESET Latency" line too ("SET Latency" is a substring of it), which is
    # the conservative (slower) of the two write directions this project
    # charges; unchanged behavior, only the missing-field path is new.
    metrics['read_latency_ns'] = float(
        _require(r"Read Latency\s*=\s*([\d\.]+)ns", "Read Latency").group(1))
    metrics['write_latency_ns'] = float(
        _require(r"(?:SET|Write)\s+Latency\s*=\s*([\d\.]+)ns",
                 "SET/Write Latency").group(1))

    # Energy (Standardized to nJ)
    read_e_match = _require(r"Read Dynamic Energy\s*=\s*([\d\.]+)(nJ|pJ|uJ)",
                            "Read Dynamic Energy")
    val, unit = float(read_e_match.group(1)), read_e_match.group(2)
    metrics['read_energy_nj'] = val if unit == 'nJ' else (val/1000.0 if unit == 'pJ' else val*1000.0)

    write_e_match = _require(r"(?:SET|Write)\s+Dynamic Energy\s*=\s*([\d\.]+)(nJ|pJ|uJ)",
                             "SET/Write Dynamic Energy")
    val, unit = float(write_e_match.group(1)), write_e_match.group(2)
    metrics['write_energy_nj'] = val if unit == 'nJ' else (val/1000.0 if unit == 'pJ' else val*1000.0)

    # Leakage (mW) and Area (mm^2)
    leak_match = _require(r"Leakage Power\s*=\s*([\d\.]+)(W|mW|uW|nW)", "Leakage Power")
    val, unit = float(leak_match.group(1)), leak_match.group(2)
    metrics['leakage_mw'] = val if unit == 'mW' else (val*1000.0 if unit == 'W' else val/1000.0)

    metrics['area_mm2'] = float(
        _require(r"Total Area = .* = ([\d\.]+)mm\^2", "Total Area").group(1))

    # --- T2.6: FORCED-ORGANIZATION FIELDS ---
    # NVSim's "Subarray Size" line gives the forced subarray geometry
    # (2048x2048 baseline / 1024x1024 sensitivity, T2.6). Required:
    # 3_gen_nvmain_config.py writes subarray_rows straight into MATHeight and
    # selector_layer.py reads all four.
    subarray_match = _require(r"(\d+) Rows x (\d+) Columns", "Subarray Size")
    metrics['subarray_rows'] = int(subarray_match.group(1))
    metrics['subarray_cols'] = int(subarray_match.group(2))

    # "Bank Organization: A x B" is NVSim's label for the -ForceBank
    # grid, which is actually the total mat count (A x B mats); see
    # research_notes/leakage_47x_organization_artifact.md SS1/SS4
    # ("Mats" column = the Bank-Organization product).
    bank_match = _require(r"Bank Organization:\s*(\d+)\s*x\s*(\d+)", "Bank Organization")
    metrics['mats'] = int(bank_match.group(1)) * int(bank_match.group(2))

    # "Senseamp Mux" is the forced -ForceMuxSenseAmp value.
    metrics['mux'] = int(_require(r"Senseamp Mux\s*:\s*(\d+)", "Senseamp Mux").group(1))

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

    skipped_architecture_suffixed = 0
    failures = []
    # sorted() so the set of files processed (and any failure order) does not
    # depend on directory iteration order.
    for file_path in sorted(hw_results_dir.glob("*_results.txt")):
        if is_architecture_suffixed_result(file_path):
            skipped_architecture_suffixed += 1
            continue

        base_name = base_name_from_result_stem(file_path.stem)

        # 1. Process SLC Track
        print(f">>> Processing Baseline: {base_name}...")
        try:
            slc_metrics = parse_nvsim_output(str(file_path))
        except (NVSimParseError, FileNotFoundError) as e:
            # I5: previously this model was dropped and the stage still exited
            # 0, leaving the previous results/hardware_metrics.json live.
            print(f"    [!] EXTRACTION FAILED: {e}")
            failures.append((str(file_path), str(e)))
            continue

        slc_metrics['is_analytical_mlc'] = False
        all_data[f"{base_name}_slc"] = slc_metrics

        # 2. Programmatically Generate MLC Track (Doubling Volume)
        print(f"    [GEN] Generating Analytical MLC variant for {base_name}...")
        all_data[f"{base_name}_mlc"] = apply_mlc_penalty(slc_metrics)

    print(f"\n[SKIP] Ignored {skipped_architecture_suffixed} architecture-suffixed "
          f"result file(s) (not independent hardware base models; see "
          f"ARCHITECTURE_SUFFIXES).")

    if failures:
        print(f"\n[CRITICAL] {len(failures)} NVSim result file(s) could not be parsed; "
              f"results/hardware_metrics.json was NOT rewritten (the previous one, if "
              f"any, is still in place and is now stale):")
        for fname, err in failures:
            print(f"    - {fname}: {err}")
        return 1

    if not all_data:
        print(f"\n[CRITICAL] No hardware model was extracted from {hw_results_dir} "
              f"(no non-architecture-suffixed *_results.txt file). Stage 3 would "
              f"build NVMain configs from a stale hardware_metrics.json; stopping.")
        return 1

    with open(output_path, 'w') as f:
        json.dump(all_data, f, indent=4)
    print(f"\nSUCCESS: {len(all_data)} tracks (SLC/MLC pairs) saved to JSON.")
    return 0

if __name__ == "__main__":
    sys.exit(main())