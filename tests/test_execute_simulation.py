import importlib.util
import pathlib

import pytest

spec = importlib.util.spec_from_file_location(
    "execsim", pathlib.Path(__file__).resolve().parents[1] / "4_execute_simulation.py")
execsim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(execsim)


def _make_dirs(tmp_path):
    config_dir = tmp_path / "configs"
    nvmain_config_dir = tmp_path / "nvmain_config"
    config_dir.mkdir()
    nvmain_config_dir.mkdir()
    return config_dir, nvmain_config_dir


def test_skip_nvsim_ddr5_by_name(tmp_path):
    config_dir, nvmain_config_dir = _make_dirs(tmp_path)
    skip, reason = execsim.skip_nvsim("DDR5_4800_DRAM", config_dir, nvmain_config_dir)
    assert skip is True
    assert "DRAM" in reason


def test_skip_nvsim_mlc_by_name(tmp_path):
    config_dir, nvmain_config_dir = _make_dirs(tmp_path)
    skip, reason = execsim.skip_nvsim("reram_22nm_1t1r_mlc_full_dimm", config_dir, nvmain_config_dir)
    assert skip is True
    assert "MLC" in reason


def test_skip_nvsim_pcm_native_nvmain_only(tmp_path):
    config_dir, nvmain_config_dir = _make_dirs(tmp_path)
    (nvmain_config_dir / "pcm_microsoft_2009.config").write_text("CLK 400\n")
    skip, reason = execsim.skip_nvsim("pcm_microsoft_2009", config_dir, nvmain_config_dir)
    assert skip is True
    assert "Native" in reason


def test_skip_nvsim_future_silicon_config_nvmain_only(tmp_path):
    config_dir, nvmain_config_dir = _make_dirs(tmp_path)
    (nvmain_config_dir / "reram_micron16gb_1t1r_full_dimm.config").write_text("CLK 800\n")
    skip, reason = execsim.skip_nvsim(
        "reram_micron16gb_1t1r_full_dimm", config_dir, nvmain_config_dir)
    assert skip is True
    assert "Native" in reason


def test_skip_nvsim_ordinary_reram_with_cfg_is_not_skipped(tmp_path):
    config_dir, nvmain_config_dir = _make_dirs(tmp_path)
    (config_dir / "reram_22nm_1t1r_slc_full_dimm.cfg").write_text("; nvsim config\n")
    skip, reason = execsim.skip_nvsim(
        "reram_22nm_1t1r_slc_full_dimm", config_dir, nvmain_config_dir)
    assert skip is False
    assert "NVSim" in reason


def test_skip_nvsim_neither_file_is_an_error(tmp_path):
    config_dir, nvmain_config_dir = _make_dirs(tmp_path)
    with pytest.raises(FileNotFoundError, match="no_such_model"):
        execsim.skip_nvsim("no_such_model", config_dir, nvmain_config_dir)


def test_import_does_not_run_simulations(capsys):
    # Re-executing the module body (equivalent to importing it) must not run
    # run_simulations()/argparse against the test runner's own argv; only
    # `if __name__ == "__main__":` may do that, and here __name__ != "__main__".
    spec.loader.exec_module(execsim)
    captured = capsys.readouterr()
    assert "STEP 4 COMPLETE" not in captured.out
