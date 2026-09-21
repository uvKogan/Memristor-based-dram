"""Task F2: the pipeline-hardening fixes from the 2026-09 final review.

Covers I5 (silent fallbacks became loud failures), I6 (run provenance: the run
manifest, the Run_* CSV columns and the generated-config gate) and the Minor
items that changed behavior (the partial stats file, the refreshed
per-architecture cfg copy).

Nothing here reads or writes anything under `results/` or `simulators/`: every
input is built in `tmp_path` or is a tracked file under `configs/` / `tests/`.
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import process_metrics as pm  # noqa: E402


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, REPO / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gen = _load("gen_f2", "3_gen_nvmain_config.py")
extract = _load("extract_f2", "2_extract_hardware_metrics.py")
master = _load("master_f2", "mbmm_master.py")


NVSIM_FIXTURE = REPO / "tests" / "fixtures" / "nvsim_1t1r_excerpt.txt"


# ---------------------------------------------------------------------------
# I5: 2_extract_hardware_metrics.py fails loudly, naming file and field
# ---------------------------------------------------------------------------

REQUIRED_NVSIM_LINES = {
    "Capacity": "Capacity   : 128MB",
    "Read Latency": " -  Read Latency = 10.120ns",
    "SET/Write Latency": " - SET Latency   = 15.260ns",
    "Read Dynamic Energy": " -  Read Dynamic Energy = 375.512pJ",
    "SET/Write Dynamic Energy": " - SET Dynamic Energy = 911.345pJ",
    "Leakage Power": " - Leakage Power = 108.384mW",
    "Total Area": " - Total Area = 6.610mm x 1.817mm = 12.008mm^2",
    "Subarray Size": " - Subarray Size    : 2048 Rows x 2048 Columns",
    "Bank Organization": "Bank Organization: 16 x 4",
    "Senseamp Mux": " - Senseamp Mux      : 64",
}


def _nvsim_text(drop=None):
    """A minimal NVSim RESULT block, optionally missing one required line."""
    lines = ["RESULT"]
    for field, line in REQUIRED_NVSIM_LINES.items():
        if field == drop:
            continue
        # Dropping the write line must not leave the RESET line behind, which
        # the same regex also matches (SET is a substring of RESET).
        lines.append(line)
    return "\n".join(lines) + "\n"


def test_parse_nvsim_output_still_reads_the_tracked_fixture_exactly():
    """The loud-failure rewrite must not change a single extracted value."""
    m = extract.parse_nvsim_output(str(NVSIM_FIXTURE))
    assert m["capacity_gb"] == pytest.approx(0.125)
    assert m["read_latency_ns"] == pytest.approx(10.120)
    assert m["write_latency_ns"] == pytest.approx(15.260)
    assert m["read_energy_nj"] == pytest.approx(0.375512)
    assert m["write_energy_nj"] == pytest.approx(0.913376)
    assert m["leakage_mw"] == pytest.approx(108.384)
    assert m["area_mm2"] == pytest.approx(12.008)
    assert m["subarray_rows"] == 2048 and m["subarray_cols"] == 2048
    assert m["mats"] == 64 and m["mux"] == 64


@pytest.mark.parametrize("field", sorted(REQUIRED_NVSIM_LINES))
def test_missing_nvsim_field_raises_naming_file_and_field(tmp_path, field):
    p = tmp_path / "broken_results.txt"
    p.write_text(_nvsim_text(drop=field))
    with pytest.raises(extract.NVSimParseError) as e:
        extract.parse_nvsim_output(str(p))
    msg = str(e.value)
    assert str(p) in msg
    assert field in msg


def test_missing_nvsim_result_file_raises():
    with pytest.raises(FileNotFoundError):
        extract.parse_nvsim_output("/nonexistent/no_results.txt")


def test_extract_stage_exits_non_zero_and_keeps_the_old_json(tmp_path, monkeypatch):
    """A broken result file must stop the stage AND leave the previous
    hardware_metrics.json untouched (so the staleness is at least not blessed)."""
    root = tmp_path
    (root / "results" / "hardware").mkdir(parents=True)
    (root / "results" / "hardware" / "reram_22nm_1t1r_slc_results.txt").write_text(
        _nvsim_text(drop="Leakage Power"))
    previous = root / "results" / "hardware_metrics.json"
    previous.write_text('{"stale": true}')

    monkeypatch.setattr(extract, "get_project_root", lambda: root)
    assert extract.main() == 1
    assert json.loads(previous.read_text()) == {"stale": True}


def test_extract_stage_exits_non_zero_when_nothing_was_extracted(tmp_path, monkeypatch):
    root = tmp_path
    (root / "results" / "hardware").mkdir(parents=True)
    monkeypatch.setattr(extract, "get_project_root", lambda: root)
    assert extract.main() == 1


def test_extract_stage_writes_json_on_success(tmp_path, monkeypatch):
    root = tmp_path
    (root / "results" / "hardware").mkdir(parents=True)
    (root / "results" / "hardware" / "reram_22nm_1t1r_slc_results.txt").write_text(
        NVSIM_FIXTURE.read_text())
    monkeypatch.setattr(extract, "get_project_root", lambda: root)
    assert extract.main() == 0
    data = json.loads((root / "results" / "hardware_metrics.json").read_text())
    assert set(data) == {"reram_22nm_1t1r_slc", "reram_22nm_1t1r_mlc"}


# ---------------------------------------------------------------------------
# I5: 3_gen_nvmain_config.py main() exits non-zero on a missing/empty input
# ---------------------------------------------------------------------------

def _run_generator(args, cwd=REPO):
    return subprocess.run([sys.executable, str(REPO / "3_gen_nvmain_config.py"), *args],
                          capture_output=True, text=True, cwd=str(cwd))


def test_generator_exits_non_zero_on_missing_input(tmp_path):
    r = _run_generator(["--input", "tests/fixtures/definitely_absent.json",
                        "--output-dir", str(tmp_path)])
    assert r.returncode == 1
    assert "not found" in r.stdout
    assert list(tmp_path.iterdir()) == []


def test_generator_exits_non_zero_on_empty_input(tmp_path):
    empty = tmp_path / "empty.json"
    empty.write_text("{}")
    out = tmp_path / "out"
    r = _run_generator(["--input", str(empty), "--output-dir", str(out)])
    assert r.returncode == 1
    assert "empty" in r.stdout


def test_generator_exits_non_zero_on_a_missing_required_key(tmp_path):
    hw = json.loads((REPO / "tests" / "fixtures" / "hardware_metrics_2048x2048.json").read_text())
    del hw["reram_22nm_1t1r_slc"]["leakage_mw"]
    broken = tmp_path / "broken.json"
    broken.write_text(json.dumps(hw))
    out = tmp_path / "out"
    r = _run_generator(["--input", str(broken), "--output-dir", str(out)])
    assert r.returncode == 1
    assert "leakage_mw" in r.stdout
    assert "Stage 3 ABORTED" in r.stdout


def test_generator_manifest_lists_exactly_what_it_wrote(tmp_path):
    out = tmp_path / "out"
    manifest = tmp_path / "stage3.json"
    r = _run_generator([
        "--input", "tests/fixtures/hardware_metrics_2048x2048.json",
        "--output-dir", str(out), "--manifest-out", str(manifest),
        "--channels", "2", "--decoder", "StartGap", "--silicon"])
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(manifest.read_text())
    written = sorted(p.stem for p in out.glob("*.config"))
    assert data["generated_models"] == written
    # 4 hardware tracks x 4 architectures + 2 silicon full-DIMM configs
    assert len(written) == 18
    assert data["channels"] == 2 and data["decoder"] == "StartGap"
    assert data["silicon"] is True


# ---------------------------------------------------------------------------
# I5: process_metrics.py needs hardware metrics for a ReRAM row, not for DDR5/PCM
# ---------------------------------------------------------------------------

def test_reram_lookup_raises_without_hardware_metrics(monkeypatch):
    monkeypatch.setattr(pm, "HARDWARE_METRICS", {})
    with pytest.raises(ValueError, match="1T1R_SLC"):
        pm._reram_json_entry("1T1R_SLC")


def test_reram_lookup_raises_when_the_2048_entry_is_absent(monkeypatch):
    monkeypatch.setattr(pm, "HARDWARE_METRICS", {"something_else": {}})
    with pytest.raises(ValueError, match="reram_22nm_1t1r_slc"):
        pm._reram_json_entry("1T1R_SLC")


@pytest.mark.parametrize("tech", ["DDR5_4800", "DDR5_4800_64B", "pcm_microsoft_2009"])
def test_ddr5_and_pcm_need_no_hardware_metrics(monkeypatch, tech):
    monkeypatch.setattr(pm, "HARDWARE_METRICS", {})
    assert pm.extract_area_mm2("", tech) is None
    assert pm.extract_physical_capacity_gb(tech) is None
    # and their density ratio is still the fixed one, not a failure
    assert pm.calculate_area_density_ratio(None, None, tech) is not None


def test_reram_row_with_no_area_ratio_raises_instead_of_publishing_1_0():
    record = {
        'technology': '1T1R_SLC', 'architecture': 'full_dimm', 'benchmark': 'gcc_spec2017',
        'power': 1.0, 'total_execution_cycles': 10.0, 'clk_mhz': 800,
        'hw_latency_cycles': None, 'queue_latency_cycles': None,
        'area_mm2': None, 'capacity_gb': None,
        'e2e_latency_ns': None, 'delivered_bw_mbps': None,
        'wear_max_writes': None, 'wear_hotspot_factor': None,
        'completed_requests': None, 'background_power_device_factor': 1,
        'background_power': 0.5, 'activate_power': 0.2, 'burst_power': 0.2,
        'refresh_power': 0.1,
    }
    with pytest.raises(ValueError, match="DDR5 parity"):
        pm.process_metrics([record], run_fields={})


# ---------------------------------------------------------------------------
# I6: the Run_* provenance columns
# ---------------------------------------------------------------------------

def test_run_provenance_unknown_without_a_manifest(tmp_path, caplog):
    fields = pm.run_provenance_fields(pm.load_run_manifest(tmp_path))
    assert set(fields) == set(pm.RUN_PROVENANCE_COLUMN_NAMES)
    assert set(fields.values()) == {pm.RUN_PROVENANCE_UNKNOWN}


def test_run_provenance_reads_the_manifest(tmp_path):
    (tmp_path / pm.RUN_MANIFEST_NAME).write_text(json.dumps({
        "date": "2026-09-21T00:00:00",
        "flags": {"channels": 2, "decoder": "StartGap", "organization": 2048,
                  "queue_size": 32, "freq_mhz": 800, "window_ns": 250000000,
                  "ddr5_model": "DDR5_4800_DRAM_subchannel"}}))
    fields = pm.run_provenance_fields(pm.load_run_manifest(tmp_path))
    assert fields["Run_Channels"] == 2
    assert fields["Run_Decoder"] == "StartGap"
    assert fields["Run_Organization"] == 2048
    assert fields["Run_Queue_Size"] == 32
    assert fields["Run_Freq_MHz"] == 800
    assert fields["Run_Window_ns"] == 250000000
    assert fields["Run_DDR5_Model"] == "DDR5_4800_DRAM_subchannel"


def test_run_provenance_flag_missing_from_the_manifest_is_unknown(tmp_path):
    (tmp_path / pm.RUN_MANIFEST_NAME).write_text(json.dumps({"flags": {"channels": 1}}))
    fields = pm.run_provenance_fields(pm.load_run_manifest(tmp_path))
    assert fields["Run_Channels"] == 1
    assert fields["Run_Decoder"] == pm.RUN_PROVENANCE_UNKNOWN


def test_unreadable_manifest_is_unknown_not_an_exception(tmp_path):
    (tmp_path / pm.RUN_MANIFEST_NAME).write_text("{not json")
    assert pm.load_run_manifest(tmp_path) is None


# ---------------------------------------------------------------------------
# I6: the generated-config rule
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,expected", [
    ("reram_22nm_1t1r_slc_full_dimm.config", True),
    ("reram_22nm_1t1r_slc_single.config", True),
    ("reram_22nm_selector_1024_mlc_8chip.config", True),
    ("reram_micron16gb_1t1r_full_dimm.config", True),
    ("reram_sandisk32gb_1s1r_full_dimm.config", True),
    # static / hand-written / upstream: never touched
    ("reram_22nm_1t1r_slc.config", False),
    ("reram_1t1r_slc.config", False),
    ("reram_selector_slc.config", False),
    ("DDR5_4800_DRAM_subchannel.config", False),
    ("DDR5_4800_DRAM_64B.config", False),
    ("pcm_microsoft_2009.config", False),
    ("2D_DRAM_example.config", False),
    ("reram_22nm_1t1r_slc_full_dimm.cfg", False),
])
def test_is_generated_reram_config(name, expected):
    assert master.is_generated_reram_config(name) is expected


def test_stash_moves_only_generated_configs_and_never_deletes(tmp_path):
    cfg_dir = tmp_path / "Config"
    cfg_dir.mkdir()
    keep = ["DDR5_4800_DRAM_subchannel.config", "pcm_microsoft_2009.config",
            "reram_22nm_1t1r_slc.config", "2D_DRAM_example.config"]
    move = ["reram_22nm_1t1r_slc_full_dimm.config",
            "reram_22nm_selector_1024_mlc_8chip.config",
            "reram_micron16gb_1t1r_full_dimm.config"]
    for n in keep + move:
        (cfg_dir / n).write_text(n)

    moved, stash_dir = master.stash_generated_reram_configs(
        cfg_dir, tmp_path / "stash", timestamp="20260921_000000")

    assert sorted(moved) == sorted(move)
    assert sorted(p.name for p in cfg_dir.glob("*.config")) == sorted(keep)
    # moved, not deleted, and with their contents intact
    for n in move:
        assert (stash_dir / n).read_text() == n


def test_stash_creates_nothing_when_there_is_nothing_to_move(tmp_path):
    cfg_dir = tmp_path / "Config"
    cfg_dir.mkdir()
    (cfg_dir / "DDR5_4800_DRAM_64B.config").write_text("x")
    moved, stash_dir = master.stash_generated_reram_configs(
        cfg_dir, tmp_path / "stash", timestamp="20260921_000000")
    assert moved == []
    assert not stash_dir.exists()


def test_check_live_configs_still_passes_after_a_stash(tmp_path):
    """tools/check_live_configs.py compares TRACKED configs/*.config with their
    live copies; the stash must never touch one of those."""
    sys.path.insert(0, str(REPO / "tools"))
    import check_live_configs as clc

    tracked = tmp_path / "configs"
    live = tmp_path / "Config"
    tracked.mkdir()
    live.mkdir()
    for n in ("DDR5_4800_DRAM_subchannel.config", "DDR5_4800_DRAM_64B.config"):
        (tracked / n).write_text(n)
        (live / n).write_text(n)
    (live / "reram_22nm_1t1r_slc_full_dimm.config").write_text("generated")

    master.stash_generated_reram_configs(live, tmp_path / "stash",
                                          timestamp="20260921_000000")
    ok, divergences, checked = clc.check_live_configs(tracked, live)
    assert ok and checked == 2 and divergences == []


def test_read_stage3_generated_models(tmp_path):
    p = tmp_path / "stage3.json"
    p.write_text(json.dumps({"generated_models": ["a", "b"]}))
    assert master.read_stage3_generated_models(p) == {"a", "b"}


def test_read_stage3_generated_models_rejects_an_empty_manifest(tmp_path):
    p = tmp_path / "stage3.json"
    p.write_text(json.dumps({"generated_models": []}))
    with pytest.raises(ValueError):
        master.read_stage3_generated_models(p)


def test_read_stage3_generated_models_raises_when_absent(tmp_path):
    with pytest.raises(OSError):
        master.read_stage3_generated_models(tmp_path / "nope.json")


# ---------------------------------------------------------------------------
# I6: the run manifest itself
# ---------------------------------------------------------------------------

class _Args:
    window_ns = 250000000
    cycles = None
    channels = 2
    decoder = "StartGap"
    endurance_model = "RowModel"
    silicon = True
    organization = 2048
    queue_size = 32
    freq = 800
    trace = ["gpt2_ifmap.nvt"]


def test_write_run_manifest_is_complete(tmp_path):
    root = tmp_path / "root"
    (root / "results").mkdir(parents=True)
    (root / "results" / "hardware_metrics.json").write_text('{"k": 1}')
    cfg_dir = root / "Config"
    cfg_dir.mkdir()
    (cfg_dir / "reram_x_full_dimm.config").write_text("CLK 800\n")
    (cfg_dir / "DDR5_4800_DRAM_subchannel.config").write_text("CLK 2400\n")

    out = root / "results" / "system" / "run_manifest.json"
    manifest = master.write_run_manifest(
        out, _Args(), root,
        ["reram_x_full_dimm", "DDR5_4800_DRAM_subchannel"], cfg_dir,
        {"reram_x_full_dimm"}, "DDR5_4800_DRAM_subchannel")

    assert out.exists()
    on_disk = json.loads(out.read_text())
    assert on_disk == manifest
    assert on_disk["schema"] == "mbmm_run_manifest/1"
    assert on_disk["command_line"][0] == sys.executable
    assert on_disk["date"]
    for flag, value in (("window_ns", 250000000), ("channels", 2),
                        ("decoder", "StartGap"), ("endurance_model", "RowModel"),
                        ("ddr5_model", "DDR5_4800_DRAM_subchannel"),
                        ("silicon", True), ("organization", 2048),
                        ("queue_size", 32), ("freq_mhz", 800)):
        assert on_disk["flags"][flag] == value
    assert set(on_disk["git"]) == {"superproject", "simulators/nvmain", "simulators/nvsim"}
    for entry in on_disk["git"].values():
        assert set(entry) == {"commit", "dirty"}
    assert on_disk["hardware_metrics"]["sha256"]
    assert on_disk["stage3_generated_models"] == ["reram_x_full_dimm"]
    assert set(on_disk["configs"]) == {"reram_x_full_dimm", "DDR5_4800_DRAM_subchannel"}
    assert on_disk["configs"]["reram_x_full_dimm"]["generated_this_run"] is True
    assert on_disk["configs"]["DDR5_4800_DRAM_subchannel"]["generated_this_run"] is False
    for entry in on_disk["configs"].values():
        assert len(entry["sha256"]) == 64
    assert [t["trace"] for t in on_disk["traces"]] == ["gpt2_ifmap.nvt"]


def test_git_provenance_on_a_non_repository(tmp_path):
    p = master.git_provenance(tmp_path)
    assert p["commit"] is None


def test_sha256_of_missing_file_is_none(tmp_path):
    assert master.sha256_of(tmp_path / "nope") is None


# ---------------------------------------------------------------------------
# Minor-5: NVMain's partial output never lands under the result name
# ---------------------------------------------------------------------------

def test_partial_and_failed_stats_names_are_not_picked_up_by_the_globs():
    """process_metrics.py globs stats_*.out and 5_summary_report.py globs *.out;
    neither may match the names a failed NVMain run leaves behind."""
    import fnmatch
    for name in ("stats_m_t.out.partial", "stats_m_t.out.failed"):
        assert not fnmatch.fnmatch(name, "stats_*.out")
        assert not fnmatch.fnmatch(name, "*.out")
    assert fnmatch.fnmatch("stats_m_t.out", "stats_*.out")


def test_execute_simulation_renames_only_on_success():
    """The source must write to a .partial name and rename on success."""
    src = (REPO / "4_execute_simulation.py").read_text()
    assert 'partial_file = sys_results_dir / f"stats_{model}_{trace_name}.out.partial"' in src
    assert "partial_file.replace(stats_file)" in src
    assert 'with open(partial_file, "w") as out_f:' in src
    assert 'with open(stats_file, "w") as out_f:' not in src


# ---------------------------------------------------------------------------
# Minor-5: the per-architecture cfg copy is refreshed, not written once
# ---------------------------------------------------------------------------

def test_master_refreshes_a_stale_per_architecture_cfg_copy():
    src = (REPO / "mbmm_master.py").read_text()
    assert "filecmp.cmp(base_cfg, arch_cfg, shallow=False)" in src
    assert "if base_cfg.exists() and not arch_cfg.exists():" not in src


def test_tracked_per_architecture_cfg_copies_match_their_base():
    """They are identical today; this pins that they stay so (the refresh rule
    above makes any base edit propagate)."""
    import filecmp
    for base in ("reram_22nm_1t1r_slc", "reram_22nm_selector_slc"):
        base_cfg = REPO / "configs" / f"{base}.cfg"
        for arch in ("single", "8chip", "16chip", "full_dimm"):
            arch_cfg = REPO / "configs" / f"{base}_{arch}.cfg"
            assert arch_cfg.exists(), arch_cfg
            assert filecmp.cmp(base_cfg, arch_cfg, shallow=False), arch_cfg


# ---------------------------------------------------------------------------
# Minor-3: the dead code is gone and stays gone
# ---------------------------------------------------------------------------

def test_dead_helpers_are_gone():
    assert not hasattr(master, "run_pipeline")
    assert not hasattr(pm, "extract_capacity_gb")


# ---------------------------------------------------------------------------
# Minor-2 / I8: no retired number survives in a comment or a CLI string
# ---------------------------------------------------------------------------

RETIRED = ("47x", "51 W", "50.9 W", "3x Read", "4x Write")


@pytest.mark.parametrize("path", [
    "mbmm_master.py", "process_metrics.py", "visualize_results.py",
    "3_gen_nvmain_config.py", "2_extract_hardware_metrics.py",
    "4_execute_simulation.py", "configs/CLAUDE.md", "README.md",
])
def test_no_retired_figure_is_quoted_as_current(path):
    text = (REPO / path).read_text()
    for retired in RETIRED:
        if retired not in text:
            continue
        # Allowed only where the text itself says the figure is retired.
        for line in text.splitlines():
            if retired in line:
                window = text[max(0, text.index(line) - 400):
                              text.index(line) + len(line) + 400].lower()
                assert any(w in window for w in
                           ("retired", "withdrawn", "artifact", "not used",
                            "do not quote")), (path, line)


# ---------------------------------------------------------------------------
# I5, negative checks: a failed Stage 1/2/3, and a missing DDR5 config, stop
# the master BEFORE Stage 4.
#
# These drive mbmm_master.main() against a throwaway project root in tmp_path
# with run_subprocess stubbed, so no live file is read or written and no
# simulator runs.
# ---------------------------------------------------------------------------

def _fake_root(tmp_path, with_ddr5=True):
    root = tmp_path / "root"
    (root / "results").mkdir(parents=True)
    (root / "configs").mkdir()
    cfg = root / "simulators" / "nvmain" / "Config"
    cfg.mkdir(parents=True)
    if with_ddr5:
        (cfg / "DDR5_4800_DRAM_subchannel.config").write_text("CLK 2400\n")
    (cfg / "pcm_microsoft_2009.config").write_text("CLK 400\n")
    return root


class _Recorder:
    """Stub for master.run_subprocess: succeeds unless the command matches a
    script named in `fail_on`."""

    def __init__(self, fail_on=(), stage3_models=None, root=None):
        self.fail_on = tuple(fail_on)
        self.stage3_models = stage3_models
        self.root = root
        self.calls = []

    def __call__(self, cmd, description=""):
        self.calls.append(list(cmd))
        joined = " ".join(str(c) for c in cmd)
        if any(f in joined for f in self.fail_on):
            return False
        if "3_gen_nvmain_config.py" in joined and self.stage3_models is not None:
            out = cmd[cmd.index("--manifest-out") + 1]
            pathlib.Path(out).parent.mkdir(parents=True, exist_ok=True)
            pathlib.Path(out).write_text(json.dumps(
                {"generated_models": list(self.stage3_models)}))
            if self.root is not None:
                # Stand in for the real generator: the master stashed the
                # previous run's generated configs away, so Stage 3 has to
                # write this run's back.
                cfg_dir = self.root / "simulators" / "nvmain" / "Config"
                for model in self.stage3_models:
                    (cfg_dir / f"{model}.config").write_text("CLK 800\n")
        return True

    @property
    def scripts(self):
        return [c[1] if len(c) > 1 else c[0] for c in self.calls]

    def ran(self, script):
        return any(script in " ".join(str(x) for x in c) for c in self.calls)


def _run_master(monkeypatch, root, recorder, argv_extra=()):
    monkeypatch.setattr(master, "get_project_root", lambda: root)
    monkeypatch.setattr(master, "setup_logging", lambda: root / "results" / "exec.log")
    monkeypatch.setattr(master, "run_subprocess", recorder)
    # archive_old_graphs() defaults to the REAL /home/yuvalk/MBMM/results paths
    # (they are hardcoded in its signature), so a test that reaches the end of
    # main() would move the live figures and CSVs into a results/archive_*
    # folder. Stub it out: nothing in this file may touch results/.
    monkeypatch.setattr(master, "archive_old_graphs", lambda *a, **k: None)
    monkeypatch.setattr(master, "execution_errors", [])
    monkeypatch.setattr(master, "execution_log", [])
    monkeypatch.setattr(master, "execution_summary", {
        "stages_run": [], "models_completed": 0, "models_failed": 0,
        "graph_dirs": [], "log_file": None})
    argv = ["mbmm_master.py", "--all", "--trace", "gpt2_ifmap.nvt",
            "--ddr5-model", "DDR5_4800_DRAM_subchannel", *argv_extra]
    monkeypatch.setattr(sys, "argv", argv)
    return master.main()


def test_missing_ddr5_config_aborts_before_any_stage(tmp_path, monkeypatch):
    root = _fake_root(tmp_path, with_ddr5=False)
    rec = _Recorder()
    assert _run_master(monkeypatch, root, rec) == 1
    # nothing ran at all: the check is before Stage 1
    assert rec.calls == []


def test_failed_stage1_aborts_before_stage4(tmp_path, monkeypatch):
    root = _fake_root(tmp_path)
    rec = _Recorder(fail_on=("1_run_nvsim_hardware.py",))
    assert _run_master(monkeypatch, root, rec) == 1
    assert rec.ran("1_run_nvsim_hardware.py")
    assert not rec.ran("2_extract_hardware_metrics.py")
    assert not rec.ran("4_execute_simulation.py")


def test_failed_stage2_aborts_before_stage4(tmp_path, monkeypatch):
    root = _fake_root(tmp_path)
    rec = _Recorder(fail_on=("2_extract_hardware_metrics.py",))
    assert _run_master(monkeypatch, root, rec) == 1
    assert rec.ran("2_extract_hardware_metrics.py")
    assert not rec.ran("3_gen_nvmain_config.py")
    assert not rec.ran("4_execute_simulation.py")


def test_failed_stage3_aborts_before_stage4(tmp_path, monkeypatch):
    root = _fake_root(tmp_path)
    rec = _Recorder(fail_on=("3_gen_nvmain_config.py",))
    assert _run_master(monkeypatch, root, rec) == 1
    assert rec.ran("3_gen_nvmain_config.py")
    assert not rec.ran("check_live_configs.py")
    assert not rec.ran("4_execute_simulation.py")
    # and no run manifest was written for a run that never reached Stage 4
    assert not (root / "results" / "system" / "run_manifest.json").exists()


def test_stage4_refuses_a_config_this_run_did_not_generate(tmp_path, monkeypatch):
    """The leftover-config hazard: Stage 3 generated only three of the sixteen
    ReRAM models, so Stage 4 must not fall back on whatever is in the shared
    live Config directory."""
    root = _fake_root(tmp_path)
    rec = _Recorder(stage3_models=["reram_22nm_1t1r_slc_full_dimm"])
    assert _run_master(monkeypatch, root, rec) == 1
    assert rec.ran("check_live_configs.py")
    assert not rec.ran("4_execute_simulation.py")
    assert not (root / "results" / "system" / "run_manifest.json").exists()


def test_stage3_manifest_missing_aborts_before_stage4(tmp_path, monkeypatch):
    root = _fake_root(tmp_path)
    rec = _Recorder()  # succeeds but writes no manifest
    assert _run_master(monkeypatch, root, rec) == 1
    assert not rec.ran("4_execute_simulation.py")


def test_complete_run_reaches_stage4_and_writes_the_manifest(tmp_path, monkeypatch):
    """The positive control for the four negatives above."""
    root = _fake_root(tmp_path)
    cfg_dir = root / "simulators" / "nvmain" / "Config"
    models = [f"{base}_{arch}"
              for base in master.reram_factory_bases(2048)
              for arch in ("single", "8chip", "16chip", "full_dimm")]
    # A leftover from an "earlier run" that this run's Stage 3 will not
    # regenerate: it must end up stashed, not simulated.
    leftover = cfg_dir / "reram_22nm_1t1r_1024_slc_full_dimm.config"
    leftover.write_text("CLK 800\n")
    rec = _Recorder(stage3_models=models, root=root)
    rc = _run_master(monkeypatch, root, rec)
    assert rec.ran("4_execute_simulation.py")
    manifest = json.loads((root / "results" / "system" / "run_manifest.json").read_text())
    assert manifest["flags"]["ddr5_model"] == "DDR5_4800_DRAM_subchannel"
    assert sorted(manifest["stage3_generated_models"]) == sorted(models)
    # every simulated model is in the manifest, including the two static baselines
    assert set(manifest["configs"]) == set(models) | {
        "DDR5_4800_DRAM_subchannel", "pcm_microsoft_2009"}
    assert rc == 0
    # the leftover was moved aside (never deleted) and never simulated
    assert not leftover.exists()
    stashed = list((root / "results" / "_generated_configs_prev").rglob(leftover.name))
    assert len(stashed) == 1
    assert leftover.name.replace(".config", "") not in manifest["configs"]


# ===========================================================================
# FIX ROUND 1 (review Important-1): a stale manifest must not relabel old stats
# ===========================================================================

def _manifest(files, channels=2, decoder="StartGap", with_list=True):
    m = {"date": "2026-09-21T00:00:00",
         "flags": {"channels": channels, "decoder": decoder, "organization": 2048,
                   "queue_size": 32, "freq_mhz": 800, "window_ns": 250000000,
                   "ddr5_model": "DDR5_4800_DRAM_subchannel"}}
    if with_list:
        m[pm.RUN_MANIFEST_STATS_KEY] = list(files)
    return m


def test_manifest_stats_files_reads_the_list():
    m = _manifest(["stats_a_t.out", "stats_b_t.out"])
    assert pm.manifest_stats_files(m) == {"stats_a_t.out", "stats_b_t.out"}


def test_manifest_without_the_list_covers_nothing():
    """A manifest written before fix round 1 cannot say which files are its
    own, so it must label none of them rather than guess."""
    m = _manifest([], with_list=False)
    assert pm.manifest_stats_files(m) is None
    resolve = pm.make_run_provenance_resolver(m, "/tmp/somewhere")
    assert resolve("stats_anything_t.out") == pm.unknown_run_provenance_fields()


def test_resolver_labels_only_the_files_the_manifest_lists():
    """The concrete mislabelling scenario from the review: one folder, two
    runs' stats files, one manifest."""
    mine = "stats_reram_22nm_1t1r_slc_full_dimm_traceB.out"
    theirs = "stats_reram_22nm_1t1r_slc_full_dimm_traceA.out"
    resolve = pm.make_run_provenance_resolver(_manifest([mine], channels=2), "results/system")
    assert resolve(mine)["Run_Channels"] == 2
    assert resolve(mine)["Run_Decoder"] == "StartGap"
    assert resolve(theirs) == pm.unknown_run_provenance_fields()
    # a full path resolves by basename
    assert resolve("results/system/" + mine)["Run_Channels"] == 2


def test_resolver_without_a_manifest_is_all_unknown():
    resolve = pm.make_run_provenance_resolver(None, "results/system")
    assert resolve("stats_x_t.out") == pm.unknown_run_provenance_fields()


def _stats_text():
    """A minimal ReRAM stats file process_metrics can parse end to end."""
    return (
        "NVMain command line is: ./nvmain.fast Config/x.config trace 1\n"
        "CLK = 800\n"
        "CPUFreq = 3000\n"
        "i0.defaultMemory.totalReadRequests 10\n"
        "i0.defaultMemory.totalWriteRequests 0\n"
        "i0.defaultMemory.averageTotalLatency 33.17\n"
        "i0.defaultMemory.channel0.rank0.totalPower 0.5\n"
        "i0.defaultMemory.channel0.rank0.backgroundPower 0.3\n"
        "i0.defaultMemory.channel0.rank0.activatePower 0.1\n"
        "i0.defaultMemory.channel0.rank0.burstPower 0.1\n"
        "i0.defaultMemory.channel0.rank0.refreshPower 0.0\n"
        "i0.defaultMemory.channel0.rank0.totalEnergy 1.0nJ\n"
        "Exiting at cycle 750000000 because simCycles 750000000 reached.\n"
    )


def test_end_to_end_mixed_folder_labels_only_the_listed_files(tmp_path, monkeypatch):
    """Two runs' stats files in one directory, one manifest: only the listed
    rows get the flags, the others get unknown."""
    stats_dir = tmp_path / "system"
    stats_dir.mkdir()
    listed = "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    unlisted = "stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out"
    for name in (listed, unlisted):
        (stats_dir / name).write_text(_stats_text())
    (stats_dir / pm.RUN_MANIFEST_NAME).write_text(json.dumps(_manifest([listed])))

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(stats_dir))
    monkeypatch.setattr(pm, "HARDWARE_METRICS", json.loads(
        (REPO / "tests" / "fixtures" / "hardware_metrics_2048x2048.json").read_text()))

    raw, failures = pm.parse_raw_stats()
    assert not failures and len(raw) == 2
    rows = {r['Benchmark']: r for r in pm.process_metrics(raw)}
    assert rows['gcc_spec2017']['Run_Channels'] == 2
    assert rows['gcc_spec2017']['Run_Decoder'] == "StartGap"
    assert rows['lbm_spec2017']['Run_Channels'] == pm.RUN_PROVENANCE_UNKNOWN
    assert rows['lbm_spec2017']['Run_Decoder'] == pm.RUN_PROVENANCE_UNKNOWN


def test_end_to_end_manifest_without_the_list_labels_nothing(tmp_path, monkeypatch):
    stats_dir = tmp_path / "system"
    stats_dir.mkdir()
    name = "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    (stats_dir / name).write_text(_stats_text())
    (stats_dir / pm.RUN_MANIFEST_NAME).write_text(
        json.dumps(_manifest([], with_list=False)))

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(stats_dir))
    monkeypatch.setattr(pm, "HARDWARE_METRICS", json.loads(
        (REPO / "tests" / "fixtures" / "hardware_metrics_2048x2048.json").read_text()))

    raw, failures = pm.parse_raw_stats()
    row = pm.process_metrics(raw)[0]
    for column in pm.RUN_PROVENANCE_COLUMN_NAMES:
        assert row[column] == pm.RUN_PROVENANCE_UNKNOWN


# --- the master side of Important-1 -----------------------------------------

def test_expected_stats_filenames_matches_stage4s_naming():
    names = master.expected_stats_filenames(
        ["reram_22nm_1t1r_slc_full_dimm", "DDR5_4800_DRAM_subchannel"],
        ["gpt2_ifmap.nvt", "lbm_spec2017.nvt"])
    assert names == sorted([
        "stats_reram_22nm_1t1r_slc_full_dimm_gpt2_ifmap.out",
        "stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out",
        "stats_DDR5_4800_DRAM_subchannel_gpt2_ifmap.out",
        "stats_DDR5_4800_DRAM_subchannel_lbm_spec2017.out",
    ])
    # the stem rule is the one 4_execute_simulation.py uses (trace_path.stem)
    assert master.expected_stats_filenames(["m"], ["/a/b/c.nvt"]) == ["stats_m_c.out"]


def test_stash_previous_stats_moves_every_kind_and_deletes_nothing(tmp_path):
    sys_dir = tmp_path / "system"
    sys_dir.mkdir()
    move = ["stats_a_t.out", "stats_b_t.out.partial", "stats_c_t.out.failed",
            "stats_d_t.out.superseded_20260101_000000", "run_manifest.json"]
    keep = ["notes.txt", "stats_e_t.csv"]
    for n in move + keep:
        (sys_dir / n).write_text(n)
    (sys_dir / "_ddr5_before_F4").mkdir()  # a directory must not be moved

    moved, dest = master.stash_previous_stats(sys_dir, timestamp="20260921_120000")

    assert sorted(moved) == sorted(move)
    assert dest.name == "system_previous_20260921_120000"
    assert dest.parent == sys_dir.parent
    assert sorted(p.name for p in sys_dir.iterdir()) == sorted(keep + ["_ddr5_before_F4"])
    for n in move:
        assert (dest / n).read_text() == n  # moved intact, not deleted


def test_stash_previous_stats_creates_nothing_for_an_empty_folder(tmp_path):
    sys_dir = tmp_path / "system"
    sys_dir.mkdir()
    moved, dest = master.stash_previous_stats(sys_dir, timestamp="20260921_120000")
    assert moved == []
    assert not dest.exists()


def test_stash_previous_stats_tolerates_a_missing_folder(tmp_path):
    moved, dest = master.stash_previous_stats(tmp_path / "nope",
                                               timestamp="20260921_120000")
    assert moved == [] and not dest.exists()


def test_master_stashes_the_previous_run_and_lists_its_own_outputs(tmp_path, monkeypatch):
    """End to end through main(): a previous run's files are moved aside and
    the manifest lists exactly this run's expected stats files."""
    root = _fake_root(tmp_path)
    sys_dir = root / "results" / "system"
    sys_dir.mkdir(parents=True)
    stale = ["stats_reram_22nm_1t1r_slc_full_dimm_traceA.out", "run_manifest.json"]
    for n in stale:
        (sys_dir / n).write_text("previous run")

    models = [f"{base}_{arch}"
              for base in master.reram_factory_bases(2048)
              for arch in ("single", "8chip", "16chip", "full_dimm")]
    rec = _Recorder(stage3_models=models, root=root)
    assert _run_master(monkeypatch, root, rec) == 0

    manifest = json.loads((sys_dir / "run_manifest.json").read_text())
    expected = master.expected_stats_filenames(
        models + ["DDR5_4800_DRAM_subchannel", "pcm_microsoft_2009"],
        ["gpt2_ifmap.nvt"])
    assert manifest[pm.RUN_MANIFEST_STATS_KEY] == expected
    assert len(expected) == 18

    previous = list((root / "results").glob("system_previous_*"))
    assert len(previous) == 1
    assert sorted(p.name for p in previous[0].iterdir()) == sorted(stale)
    assert (previous[0] / stale[0]).read_text() == "previous run"
    # the stale file is gone from the run's own folder
    assert not (sys_dir / stale[0]).exists()


# ===========================================================================
# FIX ROUND 1 (review Important-2): a stale success must not survive a failure
# ===========================================================================

def _run_stage4(tmp_path, monkeypatch, returncode, write_output=True):
    """Drive 4_execute_simulation.run_simulations() for one native model with a
    monkeypatched NVMain subprocess."""
    exe = _load("execute_f2", "4_execute_simulation.py")

    root = tmp_path / "root"
    (root / "configs").mkdir(parents=True)
    (root / "results" / "system").mkdir(parents=True)
    (root / "results" / "hardware").mkdir(parents=True)
    (root / "simulators" / "nvsim").mkdir(parents=True)
    cfg_dir = root / "simulators" / "nvmain" / "Config"
    cfg_dir.mkdir(parents=True)
    (cfg_dir / "DDR5_4800_DRAM_subchannel.config").write_text("CLK 2400\n")
    (root / "benchmarks").mkdir()
    (root / "benchmarks" / "t.nvt").write_text("0 R 0x0 0 0\n")

    class _Result:
        def __init__(self, rc):
            self.returncode = rc

    def fake_run(cmd, **kwargs):
        out_f = kwargs.get("stdout")
        if write_output and out_f is not None:
            out_f.write("fresh output\n")
        return _Result(returncode)

    monkeypatch.setattr(exe, "get_project_root", lambda: root)
    monkeypatch.setattr(exe.subprocess, "run", fake_run)
    monkeypatch.setattr(sys, "argv", [
        "4_execute_simulation.py", "--models", "DDR5_4800_DRAM_subchannel",
        "--trace", "t.nvt", "--cycles", "10"])
    return exe, root / "results" / "system"


def test_stale_success_is_moved_aside_when_the_rerun_fails(tmp_path, monkeypatch):
    exe, sys_dir = _run_stage4(tmp_path, monkeypatch, returncode=1)
    stats = sys_dir / "stats_DDR5_4800_DRAM_subchannel_t.out"
    stats.write_text("OLD SUCCESSFUL RESULT")

    with pytest.raises(SystemExit) as e:
        exe.run_simulations()
    assert e.value.code == 1

    # nothing fresh-looking is left at the final name
    assert not stats.exists()
    # the old file is preserved, under a name no result glob matches
    superseded = list(sys_dir.glob("stats_DDR5_4800_DRAM_subchannel_t.out.superseded_*"))
    assert len(superseded) == 1
    assert superseded[0].read_text() == "OLD SUCCESSFUL RESULT"
    # and the failed attempt's own output is kept as .failed
    assert (sys_dir / "stats_DDR5_4800_DRAM_subchannel_t.out.failed").exists()
    assert not (sys_dir / "stats_DDR5_4800_DRAM_subchannel_t.out.partial").exists()


def test_success_path_leaves_exactly_one_out_file(tmp_path, monkeypatch):
    exe, sys_dir = _run_stage4(tmp_path, monkeypatch, returncode=0)
    exe.run_simulations()
    stats = sys_dir / "stats_DDR5_4800_DRAM_subchannel_t.out"
    assert stats.read_text() == "fresh output\n"
    assert [p.name for p in sys_dir.glob("*.out")] == [stats.name]
    assert list(sys_dir.glob("*.partial")) == []
    assert list(sys_dir.glob("*.failed")) == []
    assert list(sys_dir.glob("*.superseded_*")) == []


def test_success_after_a_previous_success_keeps_the_old_one_aside(tmp_path, monkeypatch):
    exe, sys_dir = _run_stage4(tmp_path, monkeypatch, returncode=0)
    stats = sys_dir / "stats_DDR5_4800_DRAM_subchannel_t.out"
    stats.write_text("OLD SUCCESSFUL RESULT")
    exe.run_simulations()
    assert stats.read_text() == "fresh output\n"
    superseded = list(sys_dir.glob("*.superseded_*"))
    assert len(superseded) == 1 and superseded[0].read_text() == "OLD SUCCESSFUL RESULT"
    # exactly one result-shaped file remains
    assert [p.name for p in sys_dir.glob("*.out")] == [stats.name]


def test_superseded_name_is_not_picked_up_by_any_result_glob():
    import fnmatch
    name = "stats_m_t.out.superseded_20260921_153000"
    assert not fnmatch.fnmatch(name, "stats_*.out")
    assert not fnmatch.fnmatch(name, "*.out")
    # and the master sweeps it out of a run's folder anyway
    assert any(fnmatch.fnmatch(name, p) for p in master.PREVIOUS_RUN_PATTERNS)
