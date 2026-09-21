import importlib.util
import pathlib

import pytest

import mbmm_master as master

# 2_extract_hardware_metrics.py is digit-prefixed (not a valid module name), loaded the
# same way tests/test_gen_nvmain_config.py loads 3_gen_nvmain_config.py.
_extract_spec = importlib.util.spec_from_file_location(
    "extract_hardware_metrics_for_test",
    pathlib.Path(__file__).resolve().parents[1] / "2_extract_hardware_metrics.py")
extract_hardware_metrics = importlib.util.module_from_spec(_extract_spec)
_extract_spec.loader.exec_module(extract_hardware_metrics)


def _write_config(config_dir, model_name, clk_mhz):
    cfg = config_dir / f"{model_name}.config"
    cfg.write_text(f"; test config\nCPUFreq 3000\nCLK {clk_mhz}\n")
    return cfg


@pytest.mark.parametrize("clk_mhz,expected", [
    (800, 200000000),   # ReRAM configs
    (2400, 600000000),  # DDR5
    (400, 100000000),   # PCM
])
def test_cycles_for_matches_window(tmp_path, clk_mhz, expected):
    _write_config(tmp_path, "reram_22nm_1t1r_slc_full_dimm", clk_mhz)
    assert master.cycles_for(
        "reram_22nm_1t1r_slc_full_dimm", window_ns=250e6, config_dir=tmp_path
    ) == expected


def test_cycles_for_exact_integer_ceiling_division(tmp_path):
    # Regression for float-rounding: window 250000001 ns at CLK 1333 MHz must
    # ceil-divide exactly, not lose precision through a float multiply/divide.
    _write_config(tmp_path, "reram_22nm_1t1r_slc_full_dimm", 1333)
    assert master.cycles_for(
        "reram_22nm_1t1r_slc_full_dimm", window_ns=250000001, config_dir=tmp_path
    ) == 333250002


def test_cycles_for_non_integer_clk_raises_clear_error(tmp_path):
    cfg = tmp_path / "bad_clk.config"
    cfg.write_text("; test config\nCPUFreq 3000\nCLK 800.5\n")
    with pytest.raises(ValueError, match="CLK"):
        master.cycles_for("bad_clk", window_ns=250e6, config_dir=tmp_path)


def test_cycles_for_missing_config_raises_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="does_not_exist"):
        master.cycles_for("does_not_exist", window_ns=250e6, config_dir=tmp_path)


def test_cycles_for_missing_clk_line_raises_clear_error(tmp_path):
    cfg = tmp_path / "no_clk.config"
    cfg.write_text("; test config\nCPUFreq 3000\n")
    with pytest.raises(ValueError, match="CLK"):
        master.cycles_for("no_clk", window_ns=250e6, config_dir=tmp_path)


def test_cycles_for_default_config_dir_reads_real_reram_config():
    # Sanity check against the real, committed NVMain config (CLK 800),
    # using the default config_dir (simulators/nvmain/Config).
    cycles = master.cycles_for("reram_22nm_1t1r_slc_full_dimm", window_ns=250000000)
    assert cycles == 200000000


def test_cycles_for_default_config_dir_reads_real_ddr5_config():
    cycles = master.cycles_for("DDR5_4800_DRAM", window_ns=250000000)
    assert cycles == 600000000


def test_cycles_for_default_config_dir_reads_real_pcm_config():
    cycles = master.cycles_for("pcm_microsoft_2009", window_ns=250000000)
    assert cycles == 100000000


def test_silicon_models_matches_generator_table():
    # T2.8: mbmm_master.py must not duplicate 3_gen_nvmain_config.py's
    # SILICON_TIMINGS model-name set -- silicon_models() reads it via
    # importlib.util.spec_from_file_location instead.
    assert master.silicon_models() == [
        "reram_micron16gb_1t1r_full_dimm",
        "reram_sandisk32gb_1s1r_full_dimm",
    ]


def test_import_does_not_run_pipeline(capsys):
    # Importing the module must not execute main()/run the pipeline.
    import importlib
    importlib.reload(master)
    captured = capsys.readouterr()
    assert "MBMM EXECUTION COMPLETE" not in captured.out


# --- T5.1 step 2: organization axis (2048 default / 1024 sensitivity) -----

def test_organization_flag_default_is_2048():
    import argparse
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ["mbmm_master.py", "--all"]
        args = master.setup_args()
    finally:
        sys.argv = old_argv
    assert args.organization == 2048


def test_organization_flag_accepts_1024():
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ["mbmm_master.py", "--all", "--organization", "1024"]
        args = master.setup_args()
    finally:
        sys.argv = old_argv
    assert args.organization == 1024


def test_organization_flag_rejects_other_values():
    import sys
    old_argv = sys.argv
    try:
        sys.argv = ["mbmm_master.py", "--all", "--organization", "512"]
        with pytest.raises(SystemExit):
            master.setup_args()
    finally:
        sys.argv = old_argv


def test_reram_stage1_bases_default_matches_original_hardcoded_list():
    # 2048 (default) must be byte-for-byte the original hardcoded list.
    assert master.reram_stage1_bases() == ["reram_22nm_1t1r_slc", "reram_22nm_selector_slc"]
    assert master.reram_stage1_bases(2048) == master.reram_stage1_bases()


def test_reram_stage1_bases_1024_uses_real_cfg_filenames():
    # These must match the actual configs/*.cfg files on disk (_1024 suffix
    # at the end of the SLC cfg stem, matching nvsim_common.SENSITIVITY_1024_RE).
    bases = master.reram_stage1_bases(1024)
    assert bases == ["reram_22nm_1t1r_slc_1024", "reram_22nm_selector_slc_1024"]
    root = master.get_project_root()
    for base in bases:
        assert (root / "configs" / f"{base}.cfg").exists(), base


def test_reram_factory_bases_default_matches_original_hardcoded_list():
    assert master.reram_factory_bases() == [
        "reram_22nm_1t1r_slc", "reram_22nm_1t1r_mlc",
        "reram_22nm_selector_slc", "reram_22nm_selector_mlc",
    ]
    assert master.reram_factory_bases(2048) == master.reram_factory_bases()


def test_reram_factory_bases_1024_matches_extraction_naming():
    # 2_extract_hardware_metrics.py's REAL base_name_from_result_stem() (T5.1 step 2
    # fix round 1, Minor-2: calling the real function instead of re-implementing its
    # logic inline, so a future change to that derivation is caught here too), applied
    # to the Stage-1 result filename "reram_22nm_1t1r_slc_1024_results.txt", strips
    # "_slc" out of the middle and leaves "reram_22nm_1t1r_1024" -- the
    # hardware_metrics.json keys are that base plus "_slc"/"_mlc".
    stage1_base = "reram_22nm_1t1r_slc_1024"
    result_stem = f"{stage1_base}_results"
    extracted_base = extract_hardware_metrics.base_name_from_result_stem(result_stem)
    assert extracted_base == "reram_22nm_1t1r_1024"

    bases = master.reram_factory_bases(1024)
    assert bases == [
        "reram_22nm_1t1r_1024_slc", "reram_22nm_1t1r_1024_mlc",
        "reram_22nm_selector_1024_slc", "reram_22nm_selector_1024_mlc",
    ]
    assert f"{extracted_base}_slc" in bases


def test_reram_factory_bases_1024_do_not_collide_with_2048_key_prefixes():
    # process_metrics.py's RERAM_KEY_PREFIX lookup does a startswith() match
    # on hardware_metrics.json keys; a 1024 factory base must never be a
    # prefix-match on a 2048 one (or vice versa), or the wrong hardware
    # entry (area/capacity) would be picked up silently.
    bases_2048 = master.reram_factory_bases(2048)
    bases_1024 = master.reram_factory_bases(1024)
    for b2048 in bases_2048:
        for b1024 in bases_1024:
            assert not b1024.startswith(b2048), (b1024, b2048)
            assert not b2048.startswith(b1024), (b2048, b1024)


def test_should_duplicate_stage1_cfg_only_at_2048():
    assert master.should_duplicate_stage1_cfg(2048) is True
    assert master.should_duplicate_stage1_cfg(1024) is False
