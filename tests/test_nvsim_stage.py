"""T2.6: organization gate + debug-line filter (nvsim_common.py, shared by
1_run_nvsim_hardware.py and 4_execute_simulation.py), the architecture-suffix
skip rule (2_extract_hardware_metrics.py, fix round 1), and the four new
subarray/mat/mux fields extracted by 2_extract_hardware_metrics.py.

nvsim_common.py has an ordinary (non-digit-prefixed) name, so it's imported
normally. 1_run_nvsim_hardware.py and 2_extract_hardware_metrics.py start
with a digit, so they are imported with
importlib.util.spec_from_file_location, the same pattern
tests/test_gen_nvmain_config.py uses.
"""
import importlib.util
import pathlib

import pytest

import nvsim_common

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

spec1 = importlib.util.spec_from_file_location(
    "run_nvsim_hardware", REPO_ROOT / "1_run_nvsim_hardware.py")
run_nvsim_hardware = importlib.util.module_from_spec(spec1)
spec1.loader.exec_module(run_nvsim_hardware)

spec2 = importlib.util.spec_from_file_location(
    "extract_hardware_metrics", REPO_ROOT / "2_extract_hardware_metrics.py")
extract_hardware_metrics = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(extract_hardware_metrics)

spec3 = importlib.util.spec_from_file_location(
    "execute_simulation", REPO_ROOT / "4_execute_simulation.py")
execute_simulation = importlib.util.module_from_spec(spec3)
spec3.loader.exec_module(execute_simulation)


# --- Organization gate + debug-line filter (nvsim_common.py) ---

def test_gate_passes_on_correct_2048_organization():
    stdout = (
        "Bank Organization: 16 x 4\n"
        "Mat Organization: 2 x 2\n"
        " - Subarray Size    : 2048 Rows x 2048 Columns\n"
        " - Senseamp Mux      : 64\n"
    )
    ok, message = nvsim_common.check_forced_organization(
        stdout, "configs/reram_22nm_1t1r_slc.cfg")
    assert ok is True
    assert "2048 Rows x 2048 Columns" in message


def test_gate_fails_on_wrong_organization():
    # NVSim exited 0 but explored its own organization instead of honoring
    # the forced one (e.g. a typo'd -Force* key that NVSim silently ignored).
    stdout = (
        "Bank Organization: 8 x 8\n"
        "Mat Organization: 1 x 2\n"
        " - Subarray Size    : 8192 Rows x 128 Columns\n"
        " - Senseamp Mux      : 32\n"
    )
    ok, message = nvsim_common.check_forced_organization(
        stdout, "configs/reram_22nm_1t1r_slc.cfg")
    assert ok is False
    assert "2048 Rows x 2048 Columns" in message


def test_gate_fails_on_cannot_be_found_message():
    # A missing/misspelled -ForceBank key: NVSim still exits 0 but reports
    # the key "cannot be found" and falls back to its own exploration.
    stdout = "-ForceBank (Total AxB, Active CxD) cannot be found\n"
    ok, message = nvsim_common.check_forced_organization(
        stdout, "configs/reram_22nm_1t1r_slc.cfg")
    assert ok is False
    assert "cannot be found" in message.lower()


def test_gate_uses_1024_target_for_1024_cfgs():
    stdout = " - Subarray Size    : 1024 Rows x 1024 Columns\n"
    ok, _ = nvsim_common.check_forced_organization(
        stdout, "configs/reram_22nm_1t1r_slc_1024.cfg")
    assert ok is True

    # The 2048 baseline organization must NOT satisfy the 1024 sensitivity gate.
    ok2, _ = nvsim_common.check_forced_organization(
        stdout.replace("1024", "2048"), "configs/reram_22nm_1t1r_slc_1024.cfg")
    assert ok2 is False


def test_strip_debug_lines_removes_mat_cpp_prints():
    raw = (
        ">>> [DEBUG-SOLVER] Exploring Geometry: 2x2\n"
        ">>> [DEBUG-AREA] width: 0.000 | height: 0.000\n"
        "Bank Organization: 16 x 4\n"
        ">>> [CRITICAL] Zero dimension detected!\n"
        "Finished!\n"
    )
    cleaned = nvsim_common.strip_debug_lines(raw)
    assert ">>> [" not in cleaned
    assert "Bank Organization: 16 x 4" in cleaned
    assert "Finished!" in cleaned


def test_1_run_nvsim_hardware_and_4_execute_simulation_share_nvsim_common():
    # Fix round 1: both call sites must import the SAME functions from
    # nvsim_common.py rather than each defining their own copy.
    assert run_nvsim_hardware.check_forced_organization is nvsim_common.check_forced_organization
    assert run_nvsim_hardware.strip_debug_lines is nvsim_common.strip_debug_lines
    assert execute_simulation.check_forced_organization is nvsim_common.check_forced_organization
    assert execute_simulation.strip_debug_lines is nvsim_common.strip_debug_lines


# --- Architecture-suffix skip rule (2_extract_hardware_metrics.py, fix round 1) ---

@pytest.mark.parametrize("filename", [
    "reram_22nm_1t1r_slc_single_results.txt",
    "reram_22nm_1t1r_slc_8chip_results.txt",
    "reram_22nm_1t1r_slc_16chip_results.txt",
    "reram_22nm_1t1r_slc_full_dimm_results.txt",
    "reram_22nm_selector_slc_full_dimm_results.txt",
])
def test_architecture_suffixed_results_are_excluded(filename):
    assert extract_hardware_metrics.is_architecture_suffixed_result(filename) is True


@pytest.mark.parametrize("filename", [
    "reram_22nm_1t1r_slc_results.txt",
    "reram_22nm_selector_slc_results.txt",
    "reram_22nm_1t1r_slc_1024_results.txt",
    "reram_22nm_selector_slc_1024_results.txt",
])
def test_base_and_1024_sensitivity_results_are_not_excluded(filename):
    # The _1024 sensitivity cfgs must NOT be treated as architecture-suffixed.
    assert extract_hardware_metrics.is_architecture_suffixed_result(filename) is False


# --- Extraction of the four new fields (2_extract_hardware_metrics.py) ---

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "nvsim_1t1r_excerpt.txt"


def test_parse_nvsim_output_extracts_subarray_mats_mux_fields():
    metrics = extract_hardware_metrics.parse_nvsim_output(str(FIXTURE))
    assert metrics is not None
    assert metrics["subarray_rows"] == 2048
    assert metrics["subarray_cols"] == 2048
    # "Bank Organization: 16 x 4" is NVSim's label for the -ForceBank grid,
    # which is the total mat count (16 x 4 = 64 mats); see
    # research_notes/leakage_47x_organization_artifact.md SS1/SS4.
    assert metrics["mats"] == 64
    assert metrics["mux"] == 64


def test_parse_nvsim_output_still_extracts_pre_existing_fields():
    metrics = extract_hardware_metrics.parse_nvsim_output(str(FIXTURE))
    assert metrics["area_mm2"] == pytest.approx(12.008)
    assert metrics["read_latency_ns"] == pytest.approx(10.120)
    assert metrics["write_latency_ns"] == pytest.approx(15.260)
    assert metrics["leakage_mw"] == pytest.approx(108.384)


def test_mlc_variant_inherits_new_organization_fields():
    slc_metrics = extract_hardware_metrics.parse_nvsim_output(str(FIXTURE))
    slc_metrics["is_analytical_mlc"] = False
    mlc_metrics = extract_hardware_metrics.apply_mlc_penalty(slc_metrics)
    for key in ("subarray_rows", "subarray_cols", "mats", "mux"):
        assert mlc_metrics[key] == slc_metrics[key]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))


def test_gate_is_anchored_not_a_substring_match():
    """Review finding: '12048 Rows x 2048 Columns' must not pass the 2048 gate."""
    import nvsim_common
    for wrong in ("Subarray: 12048 Rows x 2048 Columns", "Subarray: 2048 Rows x 20480 Columns",
                  "Subarray: 1024 Rows x 1024 Columns"):
        ok, _ = nvsim_common.check_forced_organization(wrong, "configs/reram_22nm_1t1r_slc.cfg")
        assert not ok, wrong
    ok, _ = nvsim_common.check_forced_organization("Subarray Size    : 2048 Rows x 2048 Columns\n",
                                                   "configs/reram_22nm_1t1r_slc.cfg")
    assert ok


def test_1024_is_a_suffix_rule_not_a_substring_rule():
    import nvsim_common
    exp = nvsim_common.expected_organization
    assert exp("configs/reram_22nm_1t1r_slc_1024.cfg") == "1024 Rows x 1024 Columns"
    assert exp("configs/reram_22nm_1t1r_slc_1024_full_dimm.cfg") == "1024 Rows x 1024 Columns"
    assert exp("configs/reram_1024nm_foo_slc.cfg") == "2048 Rows x 2048 Columns"
    assert exp("configs/reram_22nm_1t1r_slc.cfg") == "2048 Rows x 2048 Columns"
