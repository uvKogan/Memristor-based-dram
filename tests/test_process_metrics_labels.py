import pytest

import process_metrics as pm


DDR5_FILENAMES = {
    "legacy": "stats_DDR5_4800_DRAM_gcc_spec2017.out",
    "subchannel": "stats_DDR5_4800_DRAM_subchannel_gcc_spec2017.out",
    "64B": "stats_DDR5_4800_DRAM_64B_gcc_spec2017.out",
}

EXPECTED_TECH_ARCH = {
    "legacy": ("DDR5_4800", "full_dimm"),
    "subchannel": ("DDR5_4800", "full_dimm"),
    "64B": ("DDR5_4800_64B", "full_dimm"),
}


@pytest.mark.parametrize("variant", ["legacy", "subchannel", "64B"])
def test_ddr5_variant_technology_and_architecture(variant):
    filename = DDR5_FILENAMES[variant]
    expected_tech, expected_arch = EXPECTED_TECH_ARCH[variant]

    assert pm.classify_technology(filename) == expected_tech
    assert pm.extract_architecture(filename) == expected_arch


@pytest.mark.parametrize("variant", ["legacy", "subchannel", "64B"])
def test_ddr5_variant_benchmark_name_unaffected_by_longer_model_name(variant):
    filename = DDR5_FILENAMES[variant]

    # The longer model names (subchannel/64B) must not leak into the parsed
    # benchmark name -- all three variants describe the same gcc_spec2017 run.
    assert pm.extract_benchmark(filename) == "gcc_spec2017"


def test_classify_technology_64b_not_captured_by_legacy_pattern_first():
    # Order-sensitivity regression: 'DDR5_4800_DRAM_64B...' contains the
    # legacy 'ddr5.*4800' substring too, so the 64B-specific pattern must be
    # checked first or every 64B file would misclassify as plain DDR5_4800.
    assert pm.classify_technology("stats_DDR5_4800_DRAM_64B_stream.out") == "DDR5_4800_64B"
    assert pm.classify_technology("stats_DDR5_4800_DRAM_subchannel_stream.out") == "DDR5_4800"
    assert pm.classify_technology("stats_DDR5_4800_DRAM_stream.out") == "DDR5_4800"


SILICON_FILENAMES = {
    "micron": "stats_reram_micron16gb_1t1r_full_dimm_gcc_spec2017.out",
    "sandisk": "stats_reram_sandisk32gb_1s1r_full_dimm_gcc_spec2017.out",
}

EXPECTED_SILICON_TECH_ARCH = {
    "micron": ("1T1R_SILICON", "full_dimm"),
    "sandisk": ("1S1R_SILICON", "full_dimm"),
}


@pytest.mark.parametrize("variant", ["micron", "sandisk"])
def test_silicon_technology_and_architecture(variant):
    filename = SILICON_FILENAMES[variant]
    expected_tech, expected_arch = EXPECTED_SILICON_TECH_ARCH[variant]

    assert pm.classify_technology(filename) == expected_tech
    assert pm.extract_architecture(filename) == expected_arch


@pytest.mark.parametrize("variant", ["micron", "sandisk"])
def test_silicon_benchmark_name(variant):
    filename = SILICON_FILENAMES[variant]
    assert pm.extract_benchmark(filename) == "gcc_spec2017"


def test_silicon_not_captured_by_slc_pattern_first():
    # 'reram_micron16gb_1t1r_full_dimm' / 'reram_sandisk32gb_1s1r_full_dimm'
    # contain '1t1r'/'1s1r' (like the SLC/MLC filenames) but never 'slc',
    # 'mlc' or 'selector' -- the SILICON-specific patterns are still checked
    # first in classify_technology, so this stays true even if a future
    # SLC/MLC pattern is loosened to no longer require those substrings.
    assert pm.classify_technology("stats_reram_micron16gb_1t1r_full_dimm_stream.out") == "1T1R_SILICON"
    assert pm.classify_technology("stats_reram_sandisk32gb_1s1r_full_dimm_stream.out") == "1S1R_SILICON"
    assert pm.classify_technology("stats_reram_22nm_1t1r_slc_full_dimm_stream.out") == "1T1R_SLC"
    assert pm.classify_technology("stats_reram_22nm_selector_slc_full_dimm_stream.out") == "1S1R_SLC"


def _write_stat_file(path, extra_power=0.5):
    path.write_text(f"averageTotalLatency 123.4\ntotalPower {extra_power}W\n")


def test_parse_raw_stats_raises_on_duplicate_key(tmp_path, monkeypatch):
    # Legacy DDR5_4800_DRAM and the new DDR5_4800_DRAM_subchannel config both
    # classify to (DDR5_4800, full_dimm, gcc_spec2017) -- exactly the
    # collision a leftover archive stats file plus a freshly-run subchannel
    # stats file would produce in the same results/system directory.
    legacy = tmp_path / DDR5_FILENAMES["legacy"]
    subchannel = tmp_path / DDR5_FILENAMES["subchannel"]
    _write_stat_file(legacy)
    _write_stat_file(subchannel)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    with pytest.raises(ValueError) as excinfo:
        pm.parse_raw_stats()

    message = str(excinfo.value)
    assert legacy.name in message
    assert subchannel.name in message
    assert "Duplicate" in message


def test_parse_raw_stats_no_duplicate_across_distinct_ddr5_technologies(tmp_path, monkeypatch):
    # The 64B cross-check config is a distinct Technology (DDR5_4800_64B), so
    # it must NOT collide with the primary DDR5_4800 baseline even though
    # both share Architecture=full_dimm and the same benchmark name.
    subchannel = tmp_path / DDR5_FILENAMES["subchannel"]
    sixty_four_b = tmp_path / DDR5_FILENAMES["64B"]
    _write_stat_file(subchannel)
    _write_stat_file(sixty_four_b)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    data, failures = pm.parse_raw_stats()

    assert len(data) == 2
    assert failures == []
    technologies = {d["technology"] for d in data}
    assert technologies == {"DDR5_4800", "DDR5_4800_64B"}


# --- T5.1 step 2: organization axis (2048 default / 1024 sensitivity) -----

ORG_FILENAMES = {
    "1t1r_2048": "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out",
    "1t1r_1024": "stats_reram_22nm_1t1r_1024_slc_full_dimm_gcc_spec2017.out",
    "1t1r_1024_mlc": "stats_reram_22nm_1t1r_1024_mlc_full_dimm_gcc_spec2017.out",
    "1s1r_2048": "stats_reram_22nm_selector_slc_full_dimm_lbm_spec2017.out",
    "1s1r_1024": "stats_reram_22nm_selector_1024_slc_full_dimm_lbm_spec2017.out",
}


def test_classify_reram_organization_2048_default():
    assert pm.classify_reram_organization(ORG_FILENAMES["1t1r_2048"]) == 2048
    assert pm.classify_reram_organization(ORG_FILENAMES["1s1r_2048"]) == 2048


def test_classify_reram_organization_1024_sensitivity():
    assert pm.classify_reram_organization(ORG_FILENAMES["1t1r_1024"]) == 1024
    assert pm.classify_reram_organization(ORG_FILENAMES["1t1r_1024_mlc"]) == 1024
    assert pm.classify_reram_organization(ORG_FILENAMES["1s1r_1024"]) == 1024


def test_classify_reram_organization_none_for_non_reram():
    assert pm.classify_reram_organization(DDR5_FILENAMES["subchannel"]) is None
    assert pm.classify_reram_organization("stats_pcm_microsoft_2009_gcc_spec2017.out") is None


def test_classify_reram_organization_1024_still_matches_technology_slc():
    # Technology stays 1T1R_SLC for either organization (T5.1 step 2 allows
    # this); only classify_reram_organization distinguishes them.
    assert pm.classify_technology(ORG_FILENAMES["1t1r_1024"]) == "1T1R_SLC"
    assert pm.classify_technology(ORG_FILENAMES["1t1r_2048"]) == "1T1R_SLC"


def test_parse_raw_stats_raises_on_mixed_organization(tmp_path, monkeypatch):
    f2048 = tmp_path / ORG_FILENAMES["1t1r_2048"]
    f1024 = tmp_path / ORG_FILENAMES["1s1r_1024"]
    _write_stat_file(f2048)
    _write_stat_file(f1024)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    with pytest.raises(ValueError) as excinfo:
        pm.parse_raw_stats()

    message = str(excinfo.value)
    assert "organization" in message.lower()
    assert f2048.name in message
    assert f1024.name in message


def test_parse_raw_stats_allows_uniform_1024_organization(tmp_path, monkeypatch):
    f1 = tmp_path / ORG_FILENAMES["1t1r_1024"]
    f2 = tmp_path / ORG_FILENAMES["1s1r_1024"]
    _write_stat_file(f1)
    _write_stat_file(f2)

    # Self-contained: never depend on whether the live results/hardware_metrics.json
    # happens to hold the _1024 entries (it does not after a 2048 run).
    monkeypatch.setattr(pm, "HARDWARE_METRICS", _SYNTHETIC_HW_METRICS)
    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    data, failures = pm.parse_raw_stats()

    assert len(data) == 2
    assert failures == []


# --- T5.1 step 2 fix round 1 (Critical-1): organization-aware hardware lookup ---

_SYNTHETIC_HW_METRICS = {
    "reram_22nm_1t1r_slc": {"area_mm2": 12.008, "capacity_gb": 0.125},
    "reram_22nm_1t1r_mlc": {"area_mm2": 12.008, "capacity_gb": 0.25},
    "reram_22nm_selector_slc": {"area_mm2": 3.54, "capacity_gb": 0.125},
    "reram_22nm_selector_mlc": {"area_mm2": 3.54, "capacity_gb": 0.25},
    "reram_22nm_1t1r_1024_slc": {"area_mm2": 13.545, "capacity_gb": 0.125},
    "reram_22nm_1t1r_1024_mlc": {"area_mm2": 13.545, "capacity_gb": 0.25},
    "reram_22nm_selector_1024_slc": {"area_mm2": 5.128, "capacity_gb": 0.125},
    "reram_22nm_selector_1024_mlc": {"area_mm2": 5.128, "capacity_gb": 0.25},
}


def test_reram_json_entry_default_organization_is_2048(monkeypatch):
    monkeypatch.setattr(pm, "HARDWARE_METRICS", _SYNTHETIC_HW_METRICS)
    entry = pm._reram_json_entry("1T1R_SLC")
    assert entry["area_mm2"] == 12.008


def test_reram_json_entry_1024_picks_the_1024_entry(monkeypatch):
    monkeypatch.setattr(pm, "HARDWARE_METRICS", _SYNTHETIC_HW_METRICS)
    entry_2048 = pm._reram_json_entry("1T1R_SLC", organization=2048)
    entry_1024 = pm._reram_json_entry("1T1R_SLC", organization=1024)
    assert entry_2048["area_mm2"] == 12.008
    assert entry_1024["area_mm2"] == 13.545
    assert entry_2048["area_mm2"] != entry_1024["area_mm2"]


def test_reram_json_entry_1024_missing_entry_raises_named_key(monkeypatch):
    # Only the 2048 entry exists in this hardware_metrics.json -- the 1024 lookup
    # must raise, naming the missing key, not silently fall back to the 2048 entry.
    monkeypatch.setattr(pm, "HARDWARE_METRICS", {
        "reram_22nm_1t1r_slc": {"area_mm2": 12.008, "capacity_gb": 0.125},
    })
    with pytest.raises(ValueError) as excinfo:
        pm._reram_json_entry("1T1R_SLC", organization=1024)
    message = str(excinfo.value)
    assert "reram_22nm_1t1r_1024_slc" in message
    assert "1T1R_SLC" in message


def test_extract_area_mm2_and_capacity_are_organization_aware(monkeypatch):
    monkeypatch.setattr(pm, "HARDWARE_METRICS", _SYNTHETIC_HW_METRICS)
    assert pm.extract_area_mm2("", "1T1R_SLC", organization=2048) == 12.008
    assert pm.extract_area_mm2("", "1T1R_SLC", organization=1024) == 13.545
    assert pm.extract_physical_capacity_gb("1T1R_SLC", organization=2048) == 0.125
    assert pm.extract_physical_capacity_gb("1S1R_MLC", organization=1024) == 0.25


def test_parse_raw_stats_1024_stats_file_gets_1024_area_ratio(tmp_path, monkeypatch):
    # End-to-end: a 1024 stats file parsed through parse_raw_stats() must carry the
    # 1024 hardware entry's area (13.545), not the 2048 one's (12.008), yielding a
    # different Area_Density_Ratio downstream.
    f1024 = tmp_path / ORG_FILENAMES["1t1r_1024"]
    _write_stat_file(f1024)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))
    monkeypatch.setattr(pm, "HARDWARE_METRICS", _SYNTHETIC_HW_METRICS)

    data, failures = pm.parse_raw_stats()

    assert failures == []
    assert len(data) == 1
    assert data[0]["area_mm2"] == 13.545
    assert data[0]["capacity_gb"] == 0.125


def test_parse_raw_stats_missing_1024_hardware_entry_is_a_loud_failure(tmp_path, monkeypatch):
    f1024 = tmp_path / ORG_FILENAMES["1t1r_1024"]
    _write_stat_file(f1024)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))
    # Only the 2048 entry present -- must fail loudly, not silently use it.
    monkeypatch.setattr(pm, "HARDWARE_METRICS", {
        "reram_22nm_1t1r_slc": {"area_mm2": 12.008, "capacity_gb": 0.125},
    })

    data, failures = pm.parse_raw_stats()

    assert data == []
    assert len(failures) == 1
    assert "reram_22nm_1t1r_1024_slc" in failures[0][1]


# --- T5.1 step 2 fix round 1 (Important-2): organization anchored to the model token ---

def test_classify_reram_organization_2048_file_with_1024_in_trace_name_stays_2048():
    # A 2048-organization stats file whose TRACE name happens to contain "1024" (e.g.
    # a future matrix-size-named benchmark) must not be misclassified as organization
    # 1024 -- the token must sit between the model name and the _slc/_mlc suffix.
    filename = "stats_reram_22nm_1t1r_slc_full_dimm_matmul_1024.out"
    assert pm.classify_reram_organization(filename) == 2048


def test_classify_reram_organization_real_1024_file_still_classifies_1024():
    filename = "stats_reram_22nm_1t1r_1024_slc_full_dimm_gcc_spec2017.out"
    assert pm.classify_reram_organization(filename) == 1024


def test_parse_raw_stats_2048_file_with_1024_trace_name_does_not_trip_mixed_guard(tmp_path, monkeypatch):
    normal = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    tricky = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_matmul_1024.out"
    _write_stat_file(normal)
    _write_stat_file(tricky)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    data, failures = pm.parse_raw_stats()

    assert failures == []
    assert len(data) == 2


def test_parse_raw_stats_1024_reram_with_ddr5_does_not_raise(tmp_path, monkeypatch):
    # DDR5/PCM/silicon have no organization axis (classify_reram_organization
    # returns None for them) and must never trip the mixed-organization guard.
    reram = tmp_path / ORG_FILENAMES["1t1r_1024"]
    ddr5 = tmp_path / DDR5_FILENAMES["subchannel"]
    _write_stat_file(reram)
    _write_stat_file(ddr5)

    # Self-contained: never depend on whether the live results/hardware_metrics.json
    # happens to hold the _1024 entries (it does not after a 2048 run).
    monkeypatch.setattr(pm, "HARDWARE_METRICS", _SYNTHETIC_HW_METRICS)
    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    data, failures = pm.parse_raw_stats()

    assert len(data) == 2
    assert failures == []


def test_import_does_not_run_main(capsys):
    # process_metrics.py must be importable without side effects; only
    # `if __name__ == "__main__":` may invoke main()/argparse.
    import importlib
    importlib.reload(pm)
    captured = capsys.readouterr()
    assert "DATA PROCESSING COMPLETE" not in captured.out
    assert "STAGE 6: DATA PROCESSING" not in captured.out


def test_module_has_main_guard():
    import inspect
    source = inspect.getsource(pm)
    assert 'if __name__ == "__main__":' in source
