"""T2.8: microsecond-silicon sensitivity configs (SILICON_TIMINGS,
generate_silicon_config(), and the --silicon CLI flag on
3_gen_nvmain_config.py).
"""
import json
import importlib.util
import pathlib
import sys

import pytest

spec = importlib.util.spec_from_file_location(
    "gen_silicon", pathlib.Path(__file__).resolve().parents[1] / "3_gen_nvmain_config.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


SYNTHETIC_METRICS = {
    "reram_22nm_1t1r_slc": {
        "capacity_gb": 0.125, "read_latency_ns": 10.12, "write_latency_ns": 15.26,
        "read_energy_nj": 0.375512, "write_energy_nj": 0.913376, "leakage_mw": 108.384,
        "subarray_rows": 2048,
    },
    "reram_22nm_selector_slc": {
        "capacity_gb": 0.125, "read_latency_ns": 4.702, "write_latency_ns": 24.589,
        "read_energy_nj": 0.328591, "write_energy_nj": 1.078, "leakage_mw": 108.384,
        "subarray_rows": 2048,
    },
}

NON_TIMING_KEYS = ["ROWS", "COLS", "BANKS", "RANKS", "CHANNELS", "MATHeight",
                    "Erd", "Ewr", "Eactstdby", "Eprestdby", "Epda", "Epdpf", "Epdps",
                    "Decoder", "EnduranceModel"]
TIMING_KEYS = ["tCAS", "tRCD", "tRP", "tRAS", "tWR", "tBURST", "tCCD", "tCMD"]


def _extract_keys(content, keys):
    out = {}
    for line in content.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] in keys:
            out[parts[0]] = parts[1]
    return out


# --- (1) compute_timings: exact cycle counts from the two chip papers -------

def test_compute_timings_micron_16gb_1t1r():
    t = gen.compute_timings(2300, 11700, 800)
    assert t["tRCD"] + t["tCAS"] == 1840
    assert t["tWR"] == 9360
    assert t["tRCD"] == 920 and t["tCAS"] == 920


def test_compute_timings_sandisk_32gb_1s1r():
    t = gen.compute_timings(40000, 230000, 800)
    assert t["tRCD"] + t["tCAS"] == 32000
    assert t["tWR"] == 184000
    assert t["tRCD"] == 16000 and t["tCAS"] == 16000


# --- (2)/(3): --silicon writes exactly the two extra files, with matching ---
# --- non-timing keys and differing timing keys; without --silicon, no-op ---

def _write_metrics(tmp_path):
    p = tmp_path / "hw.json"
    p.write_text(json.dumps(SYNTHETIC_METRICS))
    return p


def _run_generator(metrics_path, output_dir, extra_args=()):
    argv = ["3_gen_nvmain_config.py", "--input", str(metrics_path), "--output-dir", str(output_dir)]
    argv += list(extra_args)
    old_argv = sys.argv
    sys.argv = argv
    try:
        gen.main()
    finally:
        sys.argv = old_argv


def _silicon_filenames(output_dir):
    return {p.name for p in output_dir.iterdir()
            if p.name.startswith("reram_micron16gb") or p.name.startswith("reram_sandisk32gb")}


def test_silicon_flag_writes_exactly_two_extra_files(tmp_path):
    metrics_path = _write_metrics(tmp_path)
    output_dir = tmp_path / "out"
    _run_generator(metrics_path, output_dir, extra_args=["--silicon"])

    assert _silicon_filenames(output_dir) == {
        "reram_micron16gb_1t1r_full_dimm.config",
        "reram_sandisk32gb_1s1r_full_dimm.config",
    }


def test_without_silicon_flag_no_silicon_files_written(tmp_path):
    metrics_path = _write_metrics(tmp_path)
    output_dir = tmp_path / "out"
    _run_generator(metrics_path, output_dir, extra_args=[])

    assert _silicon_filenames(output_dir) == set()


def test_silicon_config_non_timing_keys_match_parent_timing_keys_differ(tmp_path):
    metrics = SYNTHETIC_METRICS

    parent_name = gen.generate_nvmain_config(
        "reram_22nm_1t1r_slc", metrics["reram_22nm_1t1r_slc"], 800, tmp_path, "full_dimm")
    parent_content = (tmp_path / f"{parent_name}.config").read_text()

    silicon_name = gen.generate_silicon_config(
        "reram_micron16gb_1t1r", gen.SILICON_TIMINGS["reram_micron16gb_1t1r"], metrics, 800, tmp_path)
    silicon_content = (tmp_path / f"{silicon_name}.config").read_text()

    parent_non_timing = _extract_keys(parent_content, NON_TIMING_KEYS)
    silicon_non_timing = _extract_keys(silicon_content, NON_TIMING_KEYS)
    assert set(NON_TIMING_KEYS) == set(parent_non_timing.keys())  # sanity: every key found
    assert parent_non_timing == silicon_non_timing

    parent_timing = _extract_keys(parent_content, TIMING_KEYS)
    silicon_timing = _extract_keys(silicon_content, TIMING_KEYS)
    assert parent_timing["tRCD"] != silicon_timing["tRCD"]
    assert parent_timing["tCAS"] != silicon_timing["tCAS"]
    assert parent_timing["tWR"] != silicon_timing["tWR"]
    assert silicon_timing["tRCD"] == "920"
    assert silicon_timing["tCAS"] == "920"
    assert silicon_timing["tWR"] == "9360"


def test_silicon_config_sandisk_timing_values(tmp_path):
    metrics = SYNTHETIC_METRICS
    silicon_name = gen.generate_silicon_config(
        "reram_sandisk32gb_1s1r", gen.SILICON_TIMINGS["reram_sandisk32gb_1s1r"], metrics, 800, tmp_path)
    content = (tmp_path / f"{silicon_name}.config").read_text()
    timing = _extract_keys(content, TIMING_KEYS)
    assert timing["tRCD"] == "16000"
    assert timing["tCAS"] == "16000"
    assert timing["tWR"] == "184000"


def test_silicon_config_header_states_citation_and_timing_only_scope(tmp_path):
    metrics = SYNTHETIC_METRICS
    silicon_name = gen.generate_silicon_config(
        "reram_micron16gb_1t1r", gen.SILICON_TIMINGS["reram_micron16gb_1t1r"], metrics, 800, tmp_path)
    content = (tmp_path / f"{silicon_name}.config").read_text()
    assert "Zahurak" in content
    assert "fabricated chip" in content
    assert "NVSim's 22 nm values" in content or "NVSim" in content


# --- (4) missing parent key fails clearly -----------------------------------

def test_missing_parent_key_fails_clearly(tmp_path):
    with pytest.raises(ValueError, match="reram_22nm_1t1r_slc"):
        gen.generate_silicon_config(
            "reram_micron16gb_1t1r", gen.SILICON_TIMINGS["reram_micron16gb_1t1r"],
            {}, 800, tmp_path)


def test_silicon_channels_two_yields_channels_2_ranks_4(tmp_path):
    # Fix round 1: the silicon configs inherit the geometry()/channels fix through
    # the shared generate_nvmain_config() path -- both must end up CHANNELS 2 /
    # RANKS 4 (full_dimm's 8 ranks split across 2 channels), not crash or silently
    # keep CHANNELS 1.
    metrics_path = _write_metrics(tmp_path)
    output_dir = tmp_path / "out"
    _run_generator(metrics_path, output_dir, extra_args=["--silicon", "--channels", "2"])

    for name in ("reram_micron16gb_1t1r_full_dimm.config", "reram_sandisk32gb_1s1r_full_dimm.config"):
        content = (output_dir / name).read_text()
        assert "CHANNELS 2" in content, f"{name}: expected CHANNELS 2"
        assert "RANKS 4" in content, f"{name}: expected RANKS 4"


def test_silicon_model_names_helper_matches_table():
    assert gen.silicon_model_names() == [
        "reram_micron16gb_1t1r_full_dimm",
        "reram_sandisk32gb_1s1r_full_dimm",
    ]
