import pathlib

import pytest

import tools.check_live_configs as clc


def _mk(tmp_path):
    tracked_dir = tmp_path / "configs"
    live_dir = tmp_path / "nvmain_config"
    tracked_dir.mkdir()
    live_dir.mkdir()
    return tracked_dir, live_dir


def test_identical_configs_pass(tmp_path):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\nBusWidth 32\n")
    (live_dir / "a.config").write_text("CLK 2400\nBusWidth 32\n")

    ok, divergences, checked = clc.check_live_configs(tracked_dir, live_dir)

    assert ok is True
    assert divergences == []
    assert checked == 1


def test_differing_config_fails_with_diff(tmp_path):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\nBusWidth 32\n")
    (live_dir / "a.config").write_text("CLK 2400\nBusWidth 64\n")

    ok, divergences, checked = clc.check_live_configs(tracked_dir, live_dir)

    assert ok is False
    assert checked == 1
    assert len(divergences) == 1
    assert "DIFFERS" in divergences[0]
    assert "BusWidth" in divergences[0]


def test_missing_live_copy_fails(tmp_path):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\n")
    # No live_dir/a.config written.

    ok, divergences, checked = clc.check_live_configs(tracked_dir, live_dir)

    assert ok is False
    assert checked == 1
    assert len(divergences) == 1
    assert "MISSING" in divergences[0]


def test_sync_repairs_missing_and_differing(tmp_path):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\nBusWidth 32\n")
    (tracked_dir / "b.config").write_text("CLK 800\n")
    (live_dir / "a.config").write_text("CLK 2400\nBusWidth 64\n")
    # b.config has no live copy at all yet.

    copied = clc.sync_live_configs(tracked_dir, live_dir)

    assert len(copied) == 2
    assert (live_dir / "a.config").read_text() == "CLK 2400\nBusWidth 32\n"
    assert (live_dir / "b.config").read_text() == "CLK 800\n"

    # After --sync, a plain check passes.
    ok, divergences, checked = clc.check_live_configs(tracked_dir, live_dir)
    assert ok is True
    assert divergences == []
    assert checked == 2


def test_silicon_subdir_covered_when_present(tmp_path):
    tracked_dir, live_dir = _mk(tmp_path)
    silicon_dir = tracked_dir / "silicon"
    silicon_dir.mkdir()
    (silicon_dir / "s.config").write_text("CLK 800\n")
    (live_dir / "s.config").write_text("CLK 900\n")

    ok, divergences, checked = clc.check_live_configs(tracked_dir, live_dir)

    assert ok is False
    assert checked == 1
    assert "DIFFERS" in divergences[0]


def test_silicon_subdir_absent_is_fine(tmp_path):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\n")
    (live_dir / "a.config").write_text("CLK 2400\n")
    # configs/silicon/ does not exist at all.

    ok, divergences, checked = clc.check_live_configs(tracked_dir, live_dir)

    assert ok is True
    assert checked == 1


def test_main_exit_code_ok(tmp_path, monkeypatch, capsys):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\n")
    (live_dir / "a.config").write_text("CLK 2400\n")

    monkeypatch.setattr(
        "sys.argv",
        ["check_live_configs.py", "--tracked-dir", str(tracked_dir), "--live-dir", str(live_dir)],
    )
    rc = clc.main()
    captured = capsys.readouterr()

    assert rc == 0
    assert "OK" in captured.out


def test_main_exit_code_failure(tmp_path, monkeypatch, capsys):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\n")
    (live_dir / "a.config").write_text("CLK 800\n")

    monkeypatch.setattr(
        "sys.argv",
        ["check_live_configs.py", "--tracked-dir", str(tracked_dir), "--live-dir", str(live_dir)],
    )
    rc = clc.main()
    captured = capsys.readouterr()

    assert rc == 1
    assert "FAILED" in captured.err


def test_main_sync_flag(tmp_path, monkeypatch, capsys):
    tracked_dir, live_dir = _mk(tmp_path)
    (tracked_dir / "a.config").write_text("CLK 2400\n")
    (live_dir / "a.config").write_text("CLK 800\n")

    monkeypatch.setattr(
        "sys.argv",
        ["check_live_configs.py", "--tracked-dir", str(tracked_dir),
         "--live-dir", str(live_dir), "--sync"],
    )
    rc = clc.main()

    assert rc == 0
    assert (live_dir / "a.config").read_text() == "CLK 2400\n"


def test_import_does_not_run_main(capsys):
    # Re-importing must not execute main()/argparse against pytest's own argv.
    import importlib
    importlib.reload(clc)
    captured = capsys.readouterr()
    assert "OK" not in captured.out
    assert "FAILED" not in captured.out
