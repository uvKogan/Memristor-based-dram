import pytest

import mbmm_master as master


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
