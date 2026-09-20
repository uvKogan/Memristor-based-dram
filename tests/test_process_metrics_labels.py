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
