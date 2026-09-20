import math
import importlib.util
import pathlib

import pytest

spec = importlib.util.spec_from_file_location(
    "gen", pathlib.Path(__file__).resolve().parents[1] / "3_gen_nvmain_config.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def test_read_latency_is_charged_once():
    t = gen.compute_timings(read_ns=32.134, write_ns=32.3, freq_mhz=800)
    assert t["tRCD"] + t["tCAS"] == math.ceil(32.134 / 1.25)      # 26 cycles total, not 52
    assert t["tRCD"] >= 1 and t["tCAS"] >= 1


def test_tras_covers_activate_plus_burst():
    t = gen.compute_timings(read_ns=32.134, write_ns=32.3, freq_mhz=800)
    assert t["tRAS"] >= t["tRCD"] + t["tBURST"]


def test_tccd_not_below_tburst():
    t = gen.compute_timings(read_ns=10.12, write_ns=15.26, freq_mhz=2400)
    assert t["tCCD"] >= t["tBURST"]


def test_validate_rejects_clk_above_cpufreq():
    v = gen.validate_config({"CLK": 4000, "CPUFreq": 3000, "tBURST": 4, "tCCD": 4, "tRAS": 30, "tRCD": 13})
    assert any("CLK" in s for s in v)


def test_capacity_matches_physical_module():
    hw = {"capacity_gb": 0.125, "read_latency_ns": 10.12, "write_latency_ns": 15.26,
          "read_energy_nj": 0.3755, "write_energy_nj": 0.9113, "leakage_mw": 108.384}
    g = gen.geometry(hw, arch_type="full_dimm")
    # NVMain's own capacity print is PER CHANNEL; the DIMM total is that figure
    # times CHANNELS. At the default channels=1 this is unchanged from before
    # fix round 1 (RANKS is the architecture's full rank count, CHANNELS is 1).
    assert g["ROWS"] * g["COLS"] * 64 * g["BANKS"] * g["RANKS"] * g["CHANNELS"] == 8 * 2**30


_TWO_CHANNEL_HW = {"capacity_gb": 0.125, "read_latency_ns": 10.12, "write_latency_ns": 15.26,
                    "read_energy_nj": 0.3755, "write_energy_nj": 0.9113, "leakage_mw": 108.384}


def test_geometry_channels_split_ranks_not_rows_full_dimm():
    # Fix round 1: --channels 2 must split RANKS (8 -> 4 per channel), never ROWS.
    # The pre-fix code divided ROWS instead, which for the real 2048x2048 ReRAM
    # full-DIMM capacity took ROWS below MATHeight and crashed generation outright.
    g1 = gen.geometry(_TWO_CHANNEL_HW, arch_type="full_dimm", channels=1)
    g2 = gen.geometry(_TWO_CHANNEL_HW, arch_type="full_dimm", channels=2)

    assert g2["ROWS"] == g1["ROWS"] == 2048
    assert g2["CHANNELS"] == 2
    assert g2["RANKS"] == 4
    # Total DIMM capacity (per-channel print x CHANNELS) is unchanged by the split.
    per_channel_bytes = g2["ROWS"] * g2["COLS"] * 64 * g2["BANKS"] * g2["RANKS"]
    assert per_channel_bytes * g2["CHANNELS"] == 8 * 2**30
    assert per_channel_bytes == 4 * 2**30  # 4096 MB on each of 2 channels


def test_geometry_channels_split_ranks_16chip():
    g = gen.geometry(_TWO_CHANNEL_HW, arch_type="16chip", channels=2)
    assert g["RANKS"] == 1
    assert g["CHANNELS"] == 2


@pytest.mark.parametrize("arch", ["single", "8chip"])
def test_geometry_single_rank_archs_fall_back_to_one_channel(arch):
    # A one-rank module cannot be split across channels: single and 8chip both
    # have RANKS 1, so --channels 2 must not change their RANKS/CHANNELS at all.
    g1 = gen.geometry(_TWO_CHANNEL_HW, arch_type=arch, channels=1)
    g2 = gen.geometry(_TWO_CHANNEL_HW, arch_type=arch, channels=2)
    assert g2["RANKS"] == g1["RANKS"] == 1
    assert g2["CHANNELS"] == 1


def test_channels_two_writes_channels_note_for_single_rank_archs(tmp_path):
    sys_name = gen.generate_nvmain_config("reram_22nm_1t1r_slc", _TWO_CHANNEL_HW, 800,
                                           tmp_path, "8chip", channels=2)
    content = (tmp_path / f"{sys_name}.config").read_text()
    assert "CHANNELS 1" in content
    assert "generated at 1 channel" in content


def test_channels_two_full_dimm_config_has_no_channels_note(tmp_path):
    sys_name = gen.generate_nvmain_config("reram_22nm_1t1r_slc", _TWO_CHANNEL_HW, 800,
                                           tmp_path, "full_dimm", channels=2)
    content = (tmp_path / f"{sys_name}.config").read_text()
    assert "CHANNELS 2" in content
    assert "RANKS 4" in content
    assert "generated at 1 channel" not in content


def test_validate_config_violation_is_fatal_and_writes_nothing(tmp_path):
    hw = {"capacity_gb": 0.125, "read_latency_ns": 32.134, "write_latency_ns": 32.3,
          "read_energy_nj": 1.191, "write_energy_nj": 1.738, "leakage_mw": 794.656}
    with pytest.raises(SystemExit):
        gen.generate_nvmain_config("reram_22nm_1t1r_slc", hw, 4000, tmp_path, "full_dimm")
    assert list(tmp_path.iterdir()) == []


def test_mat_height_is_subarray_rows_and_divides_rows(tmp_path):
    slc = {"capacity_gb": 0.125, "read_latency_ns": 32.134, "write_latency_ns": 32.3,
           "read_energy_nj": 1.191, "write_energy_nj": 1.738, "leakage_mw": 794.656}
    mlc = {"capacity_gb": 0.25, "read_latency_ns": 48.201, "write_latency_ns": 105.333,
           "read_energy_nj": 1.310, "write_energy_nj": 5.214, "leakage_mw": 794.656}
    for hw in (slc, mlc):
        for arch in ("single", "8chip", "16chip", "full_dimm"):
            g = gen.geometry(hw, arch_type=arch)
            assert g["ROWS"] % g["MATHeight"] == 0

    sys_name = gen.generate_nvmain_config("reram_22nm_1t1r_slc", slc, 800, tmp_path, "full_dimm")
    content = (tmp_path / f"{sys_name}.config").read_text()
    assert "MATHeight 2048" in content
