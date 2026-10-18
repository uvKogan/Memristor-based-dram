import math
import re
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
    # I4: validate_config now also checks the tRCD + tCAS read split, so tCAS
    # and read_latency_ns are required keys. At CLK 4000 the cycle is 0.25 ns,
    # so 13 + 13 = 26 = ceil(6.5 / 0.25): this cfg's split is CORRECT, and CLK
    # is the only violation reported. T2 added the write-mode keys: tWR 30 =
    # ceil(7.4 / 0.25) is the correct default-mode write charge, with no tWP.
    v = gen.validate_config({"CLK": 4000, "CPUFreq": 3000, "tBURST": 4, "tCCD": 4,
                             "tRAS": 30, "tRCD": 13, "tCAS": 13,
                             "read_latency_ns": 6.5,
                             "tWR": 30, "write_latency_ns": 7.4,
                             "write_pulse_on_path": False})
    assert any("CLK" in s for s in v)
    assert not any("tRCD + tCAS" in s for s in v)
    assert not any("tWR" in s or "tWP" in s for s in v)


# --- I4: the read-latency split the book says validation enforces -----------

def test_validate_refuses_a_hand_corrupted_read_split():
    """tRCD + tCAS must equal ceil(read_ns / cycle_ns); a hand-edited split is
    refused (Technical_Report.typ:961-965, Appendix B.1 :3843-3845, Appendix D :3982)."""
    good = gen.compute_timings(read_ns=10.12, write_ns=15.26, freq_mhz=800)
    base = {"CLK": 800, "CPUFreq": 3000, "tBURST": good["tBURST"],
            "tCCD": good["tCCD"], "tRAS": good["tRAS"], "tRCD": good["tRCD"],
            "tCAS": good["tCAS"], "read_latency_ns": 10.12,
            "tWR": good["tWR"], "tWP": good["tWP"], "write_latency_ns": 15.26,
            "write_pulse_on_path": False}
    assert gen.validate_config(base) == []
    for delta in (-1, +1, +5):
        bad = dict(base, tCAS=base["tCAS"] + delta)
        violations = gen.validate_config(bad)
        assert any("tRCD + tCAS" in s for s in violations), (delta, violations)
    # moving the same cycles from tCAS to tRCD keeps the SUM right, which is
    # exactly what the check is about: the read latency charged once.
    moved = dict(base, tRCD=base["tRCD"] + 1, tCAS=base["tCAS"] - 1)
    assert not any("tRCD + tCAS" in s for s in gen.validate_config(moved))


@pytest.mark.parametrize("freq", [800, 1333, 2400])
@pytest.mark.parametrize("subarray_rows", [1024, 2048])
@pytest.mark.parametrize("cell", ["1t1r_slc", "1t1r_mlc", "selector_slc", "selector_mlc"])
def test_every_generated_config_passes_the_read_split_check(tmp_path, cell, subarray_rows, freq):
    """Every config the generator itself produces must validate, for all four
    cell types, both organizations and the three clocks the revision uses."""
    # The real 2026-09 hardware metrics for the four tracks (latencies and
    # energies as 2_extract_hardware_metrics.py derives them).
    metrics = {
        "1t1r_slc": (10.12, 15.26, 0.375512, 0.913376),
        "1t1r_mlc": (15.18, 49.79338, 0.4130632, 2.740128),
        "selector_slc": (4.702, 24.589, 0.328591, 1.078),
        "selector_mlc": (7.053, 80.233907, 0.36145010, 3.234),
    }
    read_ns, write_ns, r_nj, w_nj = metrics[cell]
    hw = {"capacity_gb": 0.25 if cell.endswith("mlc") else 0.125,
          "read_latency_ns": read_ns, "write_latency_ns": write_ns,
          "read_energy_nj": r_nj, "write_energy_nj": w_nj,
          "leakage_mw": 108.384, "subarray_rows": subarray_rows}
    for arch in ("single", "8chip", "16chip", "full_dimm"):
        timings = gen.compute_timings(read_ns, write_ns, freq)
        cfg = {"CLK": freq, "CPUFreq": gen.CPU_FREQ_MHZ, "tBURST": timings["tBURST"],
               "tCCD": timings["tCCD"], "tRAS": timings["tRAS"],
               "tRCD": timings["tRCD"], "tCAS": timings["tCAS"],
               "read_latency_ns": read_ns,
               "tWR": timings["tWR"], "tWP": timings["tWP"],
               "write_latency_ns": write_ns, "write_pulse_on_path": False}
        assert gen.validate_config(cfg) == [], (cell, subarray_rows, freq, arch)
        # And end to end: generation must not sys.exit on any of them.
        out = tmp_path / f"{cell}_{subarray_rows}_{freq}_{arch}"
        out.mkdir()
        name = gen.generate_nvmain_config(f"reram_22nm_{cell}", hw, freq, out, arch)
        text = (out / f"{name}.config").read_text()
        t_rcd = int(re.search(r"(?m)^tRCD (\d+)$", text).group(1))
        t_cas = int(re.search(r"(?m)^tCAS (\d+)$", text).group(1))
        assert t_rcd + t_cas == gen.read_latency_cycles(read_ns, freq)


@pytest.mark.parametrize("freq", [800, 1333, 2400])
@pytest.mark.parametrize("silicon_key", sorted(gen.SILICON_TIMINGS))
def test_silicon_timing_configs_pass_the_read_split_check(tmp_path, silicon_key, freq):
    """I4 for the two T2.8 microsecond-silicon models (review Minor-1).

    Their read latencies are 2.3 us and 40 us, three to four orders of
    magnitude above the NVSim-derived ReRAM ones, so the split lands on
    thousands of cycles rather than single digits; the rule must hold there
    too, and generate_silicon_config must not sys.exit on any of them.
    """
    entry = gen.SILICON_TIMINGS[silicon_key]
    parent_metrics = {
        "reram_22nm_1t1r_slc": {"capacity_gb": 0.125, "read_latency_ns": 10.12,
                                 "write_latency_ns": 15.26, "read_energy_nj": 0.375512,
                                 "write_energy_nj": 0.913376, "leakage_mw": 108.384,
                                 "subarray_rows": 2048},
        "reram_22nm_selector_slc": {"capacity_gb": 0.125, "read_latency_ns": 4.702,
                                     "write_latency_ns": 24.589, "read_energy_nj": 0.328591,
                                     "write_energy_nj": 1.078, "leakage_mw": 108.384,
                                     "subarray_rows": 2048},
    }
    name = gen.generate_silicon_config(silicon_key, entry, parent_metrics, freq,
                                        tmp_path, channels=2, decoder="StartGap")
    text = (tmp_path / f"{name}.config").read_text()
    t_rcd = int(re.search(r"(?m)^tRCD (\d+)$", text).group(1))
    t_cas = int(re.search(r"(?m)^tCAS (\d+)$", text).group(1))
    expected = gen.read_latency_cycles(entry["read_ns"], freq)
    assert t_rcd + t_cas == expected, (silicon_key, freq, t_rcd, t_cas, expected)
    # the silicon entry overrides ONLY the timings: the split is derived from
    # the fabricated chip's own read latency, not from the parent's.
    assert expected != gen.read_latency_cycles(
        parent_metrics[entry["parent"]]["read_latency_ns"], freq)
    # and validate_config agrees with what was written
    assert gen.validate_config({
        "CLK": freq, "CPUFreq": gen.CPU_FREQ_MHZ,
        "tBURST": int(re.search(r"(?m)^tBURST (\d+)$", text).group(1)),
        "tCCD": int(re.search(r"(?m)^tCCD (\d+)$", text).group(1)),
        "tRAS": int(re.search(r"(?m)^tRAS (\d+)$", text).group(1)),
        "tRCD": t_rcd, "tCAS": t_cas,
        "read_latency_ns": entry["read_ns"],
        "tWR": int(re.search(r"(?m)^tWR (\d+)$", text).group(1)),
        "write_latency_ns": entry["write_ns"], "write_pulse_on_path": False}) == []
    # default mode: no tWP key at all in the written file
    assert re.search(r"(?m)^tWP ", text) is None


# --- T2: the --write-pulse-on-path bounding mode ----------------------------

# The real 2026-09 hardware metrics for the four tracks, shared by the tests
# below and by test_every_generated_config_passes_the_read_split_check above
# (same numbers, kept beside each other deliberately).
_T2_CELL_METRICS = {
    "1t1r_slc": (10.12, 15.26, 0.375512, 0.913376),
    "1t1r_mlc": (15.18, 49.79338, 0.4130632, 2.740128),
    "selector_slc": (4.702, 24.589, 0.328591, 1.078),
    "selector_mlc": (7.053, 80.233907, 0.36145010, 3.234),
}


def _t2_hw(cell, subarray_rows):
    read_ns, write_ns, r_nj, w_nj = _T2_CELL_METRICS[cell]
    return {"capacity_gb": 0.25 if cell.endswith("mlc") else 0.125,
            "read_latency_ns": read_ns, "write_latency_ns": write_ns,
            "read_energy_nj": r_nj, "write_energy_nj": w_nj,
            "leakage_mw": 108.384, "subarray_rows": subarray_rows}


@pytest.mark.parametrize("freq", [800, 1333, 2400])
@pytest.mark.parametrize("subarray_rows", [1024, 2048])
@pytest.mark.parametrize("cell", sorted(_T2_CELL_METRICS))
def test_bounding_mode_configs_put_the_write_pulse_on_the_path(tmp_path, cell,
                                                                subarray_rows, freq):
    """Every config --write-pulse-on-path produces must validate and must carry
    tWP = ceil(write_ns / cycle_ns) with tWR 1, for all four cell types, both
    organizations and the three clocks the revision uses."""
    hw = _t2_hw(cell, subarray_rows)
    read_ns, write_ns = hw["read_latency_ns"], hw["write_latency_ns"]
    expected_wp = math.ceil(write_ns / (1000.0 / freq))
    assert expected_wp == gen.write_pulse_cycles(write_ns, freq)
    for arch in ("single", "8chip", "16chip", "full_dimm"):
        timings = gen.compute_timings(read_ns, write_ns, freq, write_pulse_on_path=True)
        cfg = {"CLK": freq, "CPUFreq": gen.CPU_FREQ_MHZ, "tBURST": timings["tBURST"],
               "tCCD": timings["tCCD"], "tRAS": timings["tRAS"],
               "tRCD": timings["tRCD"], "tCAS": timings["tCAS"],
               "read_latency_ns": read_ns,
               "tWR": timings["tWR"], "tWP": timings["tWP"],
               "write_latency_ns": write_ns, "write_pulse_on_path": True}
        assert gen.validate_config(cfg) == [], (cell, subarray_rows, freq, arch)

        out = tmp_path / f"{cell}_{subarray_rows}_{freq}_{arch}"
        out.mkdir()
        name = gen.generate_nvmain_config(f"reram_22nm_{cell}", hw, freq, out, arch,
                                           write_pulse_on_path=True)
        text = (out / f"{name}.config").read_text()
        assert int(re.search(r"(?m)^tWP (\d+)$", text).group(1)) == expected_wp
        assert int(re.search(r"(?m)^tWR (\d+)$", text).group(1)) == 1
        assert "write pulse on the request path (bounding mode)" in text
        # the read split is untouched by the mode
        t_rcd = int(re.search(r"(?m)^tRCD (\d+)$", text).group(1))
        t_cas = int(re.search(r"(?m)^tCAS (\d+)$", text).group(1))
        assert t_rcd + t_cas == gen.read_latency_cycles(read_ns, freq)


@pytest.mark.parametrize("freq", [800, 1333, 2400])
@pytest.mark.parametrize("subarray_rows", [1024, 2048])
@pytest.mark.parametrize("cell", sorted(_T2_CELL_METRICS))
def test_default_mode_configs_carry_no_write_pulse(tmp_path, cell, subarray_rows, freq):
    """Default mode is unchanged: no tWP key anywhere, and tWR carries the write
    cycles that bounding mode would put in tWP."""
    hw = _t2_hw(cell, subarray_rows)
    read_ns, write_ns = hw["read_latency_ns"], hw["write_latency_ns"]
    expected_wr = math.ceil(write_ns / (1000.0 / freq))
    for arch in ("single", "8chip", "16chip", "full_dimm"):
        assert gen.compute_timings(read_ns, write_ns, freq)["tWP"] is None
        out = tmp_path / f"{cell}_{subarray_rows}_{freq}_{arch}"
        out.mkdir()
        name = gen.generate_nvmain_config(f"reram_22nm_{cell}", hw, freq, out, arch)
        text = (out / f"{name}.config").read_text()
        assert "tWP" not in text
        assert "bounding mode" not in text
        assert int(re.search(r"(?m)^tWR (\d+)$", text).group(1)) == expected_wr


def test_the_two_modes_differ_only_in_the_write_lines(tmp_path):
    """The bounding flag must move the write time and change nothing else."""
    hw = _t2_hw("1t1r_mlc", 2048)
    default_dir, bounding_dir = tmp_path / "default", tmp_path / "bounding"
    default_dir.mkdir()
    bounding_dir.mkdir()
    gen.generate_nvmain_config("reram_22nm_1t1r_mlc", hw, 800, default_dir, "full_dimm",
                                channels=2, decoder="StartGap")
    gen.generate_nvmain_config("reram_22nm_1t1r_mlc", hw, 800, bounding_dir, "full_dimm",
                                channels=2, decoder="StartGap", write_pulse_on_path=True)
    name = "reram_22nm_1t1r_mlc_full_dimm.config"
    a = (default_dir / name).read_text().splitlines()
    b = (bounding_dir / name).read_text().splitlines()
    only_a = [line for line in a if line not in b]
    only_b = [line for line in b if line not in a]
    expected_wp = gen.write_pulse_cycles(hw["write_latency_ns"], 800)
    assert only_a == [f"tWR {expected_wp}"]
    assert only_b == [
        "tWR 1",
        "; write pulse on the request path (bounding mode): tWP carries the NVSim "
        "write latency, tWR is 1 cycle",
        f"tWP {expected_wp}",
    ]


@pytest.mark.parametrize("delta", [-1, +1])
def test_validate_refuses_a_hand_corrupted_write_pulse(delta):
    """An off-by-one tWP in bounding mode is refused, as a corrupted read split is."""
    good = gen.compute_timings(read_ns=10.12, write_ns=15.26, freq_mhz=800,
                                write_pulse_on_path=True)
    base = {"CLK": 800, "CPUFreq": 3000, "tBURST": good["tBURST"],
            "tCCD": good["tCCD"], "tRAS": good["tRAS"], "tRCD": good["tRCD"],
            "tCAS": good["tCAS"], "read_latency_ns": 10.12,
            "tWR": good["tWR"], "tWP": good["tWP"], "write_latency_ns": 15.26,
            "write_pulse_on_path": True}
    assert gen.validate_config(base) == []
    bad = dict(base, tWP=base["tWP"] + delta)
    assert any("tWP" in s for s in gen.validate_config(bad)), delta
    # and a bounding-mode config that kept the write time in tWR too (the
    # double-charge the ruling forbids) is refused
    doubled = dict(base, tWR=base["tWP"])
    assert any("tWR" in s for s in gen.validate_config(doubled))
    # so is a bounding-mode config with no tWP at all: it would silently be a
    # default-mode run
    missing = dict(base)
    del missing["tWP"]
    assert any("tWP" in s for s in gen.validate_config(missing))


def test_validate_refuses_a_default_mode_config_that_carries_a_write_pulse():
    good = gen.compute_timings(read_ns=10.12, write_ns=15.26, freq_mhz=800)
    base = {"CLK": 800, "CPUFreq": 3000, "tBURST": good["tBURST"],
            "tCCD": good["tCCD"], "tRAS": good["tRAS"], "tRCD": good["tRCD"],
            "tCAS": good["tCAS"], "read_latency_ns": 10.12,
            "tWR": good["tWR"], "tWP": good["tWP"], "write_latency_ns": 15.26,
            "write_pulse_on_path": False}
    assert gen.validate_config(base) == []
    stray = dict(base, tWP=13)
    assert any("tWP" in s for s in gen.validate_config(stray))
    # and a default-mode tWR that is not the write cycles
    assert any("tWR" in s for s in gen.validate_config(dict(base, tWR=1)))


@pytest.mark.parametrize("silicon_key", sorted(gen.SILICON_TIMINGS))
def test_silicon_configs_take_the_bounding_mode_too(tmp_path, silicon_key):
    entry = gen.SILICON_TIMINGS[silicon_key]
    parent_metrics = {
        "reram_22nm_1t1r_slc": _t2_hw("1t1r_slc", 2048),
        "reram_22nm_selector_slc": _t2_hw("selector_slc", 2048),
    }
    name = gen.generate_silicon_config(silicon_key, entry, parent_metrics, 800, tmp_path,
                                        channels=2, decoder="StartGap",
                                        write_pulse_on_path=True)
    text = (tmp_path / f"{name}.config").read_text()
    assert int(re.search(r"(?m)^tWP (\d+)$", text).group(1)) == \
        gen.write_pulse_cycles(entry["write_ns"], 800)
    assert int(re.search(r"(?m)^tWR (\d+)$", text).group(1)) == 1


# --- M1 (T2 review fix round 1): validation runs on the RENDERED text ---------

def _rendered(tmp_path, write_pulse_on_path):
    hw = _t2_hw("1t1r_mlc", 2048)
    out = tmp_path / ("wp" if write_pulse_on_path else "def")
    out.mkdir()
    name = gen.generate_nvmain_config("reram_22nm_1t1r_mlc", hw, 800, out, "full_dimm",
                                       write_pulse_on_path=write_pulse_on_path)
    return (out / f"{name}.config").read_text(), hw


def test_config_check_from_text_reads_the_rendered_keys(tmp_path):
    text, hw = _rendered(tmp_path, True)
    cfg = gen.config_check_from_text(text, hw["read_latency_ns"], hw["write_latency_ns"], True)
    assert set(gen.CONFIG_CHECK_KEYS).issubset(cfg)
    assert cfg["tWP"] == gen.write_pulse_cycles(hw["write_latency_ns"], 800)
    assert cfg["tWR"] == 1
    assert cfg["CLK"] == 800
    assert gen.validate_config(cfg) == []

    text_default, _ = _rendered(tmp_path, False)
    cfg_default = gen.config_check_from_text(text_default, hw["read_latency_ns"],
                                              hw["write_latency_ns"], False)
    assert cfg_default["tWP"] is None
    assert gen.validate_config(cfg_default) == []


def test_a_rendering_bug_that_drops_the_write_pulse_line_is_refused(tmp_path):
    """The gap M1 names: suppressing the tWP line in bounding mode used to pass
    validation because the check read the in-memory dict, not the text."""
    text, hw = _rendered(tmp_path, True)
    mutated = "\n".join(line for line in text.splitlines()
                        if not line.startswith("tWP "))
    cfg = gen.config_check_from_text(mutated, hw["read_latency_ns"],
                                      hw["write_latency_ns"], True)
    assert cfg["tWP"] is None
    assert any("tWP" in v for v in gen.validate_config(cfg))


def test_a_rendering_bug_in_the_read_split_is_refused(tmp_path):
    """The same guard covers the pre-existing I4 read split."""
    text, hw = _rendered(tmp_path, False)
    t_rcd = int(re.search(r"(?m)^tRCD (\d+)$", text).group(1))
    mutated = re.sub(r"(?m)^tRCD \d+$", f"tRCD {t_rcd + 1}", text)
    cfg = gen.config_check_from_text(mutated, hw["read_latency_ns"],
                                      hw["write_latency_ns"], False)
    assert any("tRCD + tCAS" in v for v in gen.validate_config(cfg))


@pytest.mark.parametrize("key", ["tCAS", "tWR", "CLK"])
def test_config_check_from_text_refuses_a_duplicated_key(tmp_path, key):
    """R3: NVMain's parser takes the LAST occurrence, a re.search would have
    taken the first, so a key rendered twice must be a loud error naming it."""
    text, hw = _rendered(tmp_path, False)
    value = int(re.search(rf"(?m)^{key} (\d+)$", text).group(1))
    duplicated = text.replace(f"{key} {value}\n", f"{key} {value}\n{key} {value + 7}\n", 1)
    assert len(re.findall(rf"(?m)^{key} \d+$", duplicated)) == 2
    with pytest.raises(ValueError, match=key):
        gen.config_check_from_text(duplicated, hw["read_latency_ns"],
                                    hw["write_latency_ns"], False)


def test_config_check_from_text_refuses_a_duplicated_write_pulse(tmp_path):
    """The optional key needs the same guard: absence is legal, ambiguity is not."""
    text, hw = _rendered(tmp_path, True)
    value = int(re.search(r"(?m)^tWP (\d+)$", text).group(1))
    duplicated = text.replace(f"tWP {value}\n", f"tWP {value}\ntWP {value + 1}\n", 1)
    with pytest.raises(ValueError, match="tWP"):
        gen.config_check_from_text(duplicated, hw["read_latency_ns"],
                                    hw["write_latency_ns"], True)


def test_every_generated_config_has_each_checked_key_exactly_once(tmp_path):
    """The guard above must not be able to fire on the real template."""
    for write_pulse in (False, True):
        root = tmp_path / f"once_{write_pulse}"
        root.mkdir()
        text, _ = _rendered(root, write_pulse)
        for key in gen.CONFIG_CHECK_KEYS:
            assert len(re.findall(rf"(?m)^{key} \d+$", text)) == 1, key
        assert len(re.findall(r"(?m)^tWP \d+$", text)) == (1 if write_pulse else 0)


def test_config_check_from_text_names_a_missing_template_key(tmp_path):
    text, hw = _rendered(tmp_path, False)
    mutated = "\n".join(line for line in text.splitlines()
                        if not line.startswith("tCCD "))
    with pytest.raises(ValueError, match="tCCD"):
        gen.config_check_from_text(mutated, hw["read_latency_ns"],
                                    hw["write_latency_ns"], False)


def test_stage3_manifest_records_the_bounding_flag(tmp_path):
    """--manifest-out records write_pulse_on_path, in both modes."""
    import json
    import subprocess
    import sys
    root = pathlib.Path(__file__).resolve().parents[1]
    metrics = {"reram_22nm_1t1r_slc": _t2_hw("1t1r_slc", 2048)}
    metrics_path = tmp_path / "hardware_metrics.json"
    metrics_path.write_text(json.dumps(metrics))

    for flag, expected in ((None, False), ("--write-pulse-on-path", True)):
        out_dir = tmp_path / f"cfg_{expected}"
        manifest = tmp_path / f"manifest_{expected}.json"
        cmd = [sys.executable, str(root / "3_gen_nvmain_config.py"),
               "--input", str(metrics_path), "--output-dir", str(out_dir),
               "--manifest-out", str(manifest)]
        if flag:
            cmd.append(flag)
        proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert json.loads(manifest.read_text())["write_pulse_on_path"] is expected


# --- I5: required hardware-metric keys --------------------------------------

@pytest.mark.parametrize("key", sorted(gen.REQUIRED_HW_KEYS))
def test_missing_hardware_key_aborts_naming_file_model_and_key(tmp_path, key):
    hw = {"capacity_gb": 0.125, "read_latency_ns": 10.12, "write_latency_ns": 15.26,
          "read_energy_nj": 0.3755, "write_energy_nj": 0.9113, "leakage_mw": 108.384,
          "subarray_rows": 2048}
    del hw[key]
    with pytest.raises(gen.MissingHardwareMetric) as e:
        gen.generate_nvmain_config("reram_22nm_1t1r_slc", hw, 800, tmp_path, "full_dimm",
                                    metrics_source="results/hardware_metrics.json")
    msg = str(e.value)
    assert key in msg
    assert "reram_22nm_1t1r_slc" in msg
    assert "results/hardware_metrics.json" in msg
    # Nothing is written when a required value is missing.
    assert list(tmp_path.iterdir()) == []


def test_retired_defaults_are_gone_from_the_source():
    """The invented defaults I5 names must not come back: 32.0 ns read/write
    latency (the RETIRED pre-revision figure), 10 mW leakage, 1.1 / 1.7 nJ
    energies, 2048 subarray rows."""
    raw = (pathlib.Path(__file__).resolve().parents[1] / "3_gen_nvmain_config.py").read_text()
    # Comments may quote the retired defaults (they explain what was removed);
    # only live code counts.
    src = "\n".join(line for line in raw.splitlines()
                    if not line.lstrip().startswith("#"))
    for forbidden in ("get('read_latency_ns', 32.0", "get('write_latency_ns', 32.0",
                      "get('leakage_mw', 10.0", "get('read_energy_nj', 1.1",
                      "get('write_energy_nj', 1.7", 'get("subarray_rows", 2048'):
        assert forbidden not in src, forbidden


def test_capacity_matches_physical_module():
    hw = {"capacity_gb": 0.125, "read_latency_ns": 10.12, "write_latency_ns": 15.26,
          "read_energy_nj": 0.3755, "write_energy_nj": 0.9113, "leakage_mw": 108.384,
          "subarray_rows": 2048}
    g = gen.geometry(hw, arch_type="full_dimm")
    # NVMain's own capacity print is PER CHANNEL; the DIMM total is that figure
    # times CHANNELS. At the default channels=1 this is unchanged from before
    # fix round 1 (RANKS is the architecture's full rank count, CHANNELS is 1).
    assert g["ROWS"] * g["COLS"] * 64 * g["BANKS"] * g["RANKS"] * g["CHANNELS"] == 8 * 2**30


_TWO_CHANNEL_HW = {"capacity_gb": 0.125, "read_latency_ns": 10.12, "write_latency_ns": 15.26,
                    "read_energy_nj": 0.3755, "write_energy_nj": 0.9113, "leakage_mw": 108.384,
                    "subarray_rows": 2048}


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
          "read_energy_nj": 1.191, "write_energy_nj": 1.738, "leakage_mw": 794.656,
          "subarray_rows": 2048}
    with pytest.raises(SystemExit):
        gen.generate_nvmain_config("reram_22nm_1t1r_slc", hw, 4000, tmp_path, "full_dimm")
    assert list(tmp_path.iterdir()) == []


def test_mat_height_is_subarray_rows_and_divides_rows(tmp_path):
    slc = {"capacity_gb": 0.125, "read_latency_ns": 32.134, "write_latency_ns": 32.3,
           "read_energy_nj": 1.191, "write_energy_nj": 1.738, "leakage_mw": 794.656,
           "subarray_rows": 2048}
    mlc = {"capacity_gb": 0.25, "read_latency_ns": 48.201, "write_latency_ns": 105.333,
           "read_energy_nj": 1.310, "write_energy_nj": 5.214, "leakage_mw": 794.656,
           "subarray_rows": 2048}
    for hw in (slc, mlc):
        for arch in ("single", "8chip", "16chip", "full_dimm"):
            g = gen.geometry(hw, arch_type=arch)
            assert g["ROWS"] % g["MATHeight"] == 0

    sys_name = gen.generate_nvmain_config("reram_22nm_1t1r_slc", slc, 800, tmp_path, "full_dimm")
    content = (tmp_path / f"{sys_name}.config").read_text()
    assert "MATHeight 2048" in content


# --- T5.1 step 2: organization axis (2048 default / 1024 sensitivity) -----

_1024_HW = {"capacity_gb": 0.125, "read_latency_ns": 32.134, "write_latency_ns": 32.3,
            "read_energy_nj": 1.191, "write_energy_nj": 1.738, "leakage_mw": 794.656,
            "subarray_rows": 1024}
_2048_HW = {"capacity_gb": 0.125, "read_latency_ns": 32.134, "write_latency_ns": 32.3,
            "read_energy_nj": 1.191, "write_energy_nj": 1.738, "leakage_mw": 794.656,
            "subarray_rows": 2048}


def test_geometry_1024_organization_mat_height_and_divisibility():
    for arch in ("single", "8chip", "16chip", "full_dimm"):
        g = gen.geometry(_1024_HW, arch_type=arch)
        assert g["MATHeight"] == 1024
        assert g["ROWS"] % g["MATHeight"] == 0


def test_geometry_1024_organization_same_capacity_as_2048():
    # Same physical module capacity at either organization -- only the
    # subarray geometry (MATHeight) differs, per T5.1 step 2's requirement.
    for arch in ("single", "8chip", "16chip", "full_dimm"):
        g1024 = gen.geometry(_1024_HW, arch_type=arch)
        g2048 = gen.geometry(_2048_HW, arch_type=arch)
        assert g1024["ROWS"] == g2048["ROWS"]
        assert g1024["COLS"] == g2048["COLS"]
        assert g1024["BANKS"] == g2048["BANKS"]
        assert g1024["RANKS"] == g2048["RANKS"]
        cap_1024 = g1024["ROWS"] * g1024["COLS"] * 64 * g1024["BANKS"] * g1024["RANKS"]
        cap_2048 = g2048["ROWS"] * g2048["COLS"] * 64 * g2048["BANKS"] * g2048["RANKS"]
        assert cap_1024 == cap_2048


def test_generate_nvmain_config_1024_organization_validates_and_writes_mat_height(tmp_path):
    sys_name = gen.generate_nvmain_config("reram_22nm_1t1r_1024_slc", _1024_HW, 800,
                                           tmp_path, "full_dimm")
    content = (tmp_path / f"{sys_name}.config").read_text()
    assert "MATHeight 1024" in content
    assert sys_name == "reram_22nm_1t1r_1024_slc_full_dimm"
