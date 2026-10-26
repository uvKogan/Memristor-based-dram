"""D1 (wrap-up review, 2026-10-26): the pipeline's default locations are
derived from each script's own position in the checkout, never from a
hardcoded absolute path, so a clone anywhere reads and writes its own
results/ folder when run without flags."""
import pathlib
import importlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
PIPELINE_SCRIPTS = [
    "mbmm_master.py", "logging_config.py", "process_metrics.py",
    "visualize_results.py", "visualize_hero_graphs.py", "visualize_pareto.py",
    "visualize_slides.py",
]


@pytest.mark.parametrize("script", PIPELINE_SCRIPTS)
def test_no_hardcoded_home_path_in_pipeline_scripts(script):
    text = (REPO / script).read_text(encoding="utf-8")
    assert "/home/yuvalk" not in text, f"{script} still carries a machine-specific path"


def test_process_metrics_defaults_follow_the_checkout():
    pm = importlib.import_module("process_metrics")
    assert pm.RESULTS_SYS_DIR == str(REPO / "results" / "system")
    assert pm.OUTPUT_DIR == str(REPO / "results")
    assert pm.HARDWARE_METRICS_FILE == str(REPO / "results" / "hardware_metrics.json")
    assert tuple(pm.NVMAIN_CONFIG_SEARCH_DIRS) == (
        str(REPO / "configs"), str(REPO / "simulators" / "nvmain" / "Config"))


def test_visualizer_defaults_follow_the_checkout():
    vr = importlib.import_module("visualize_results")
    vh = importlib.import_module("visualize_hero_graphs")
    vp = importlib.import_module("visualize_pareto")
    vs = importlib.import_module("visualize_slides")
    assert vr.BASE_OUTPUT_DIR == str(REPO / "results" / "final_graphs")
    assert vr.METRICS_FILE == str(REPO / "results" / "processed_bar_chart_metrics.csv")
    assert vh.OUTPUT_DIR == str(REPO / "results" / "final_graphs" / "hero")
    assert vh.HERO_METRICS_FILE == str(REPO / "results" / "processed_hero_metrics.csv")
    assert vh.GEOMETRIC_MEANS_FILE == str(REPO / "results" / "processed_geometric_means.csv")
    assert vp.METRICS_FILE == str(REPO / "results" / "processed_pareto_metrics.csv")
    assert vp.OUTPUT_DIR == str(REPO / "results" / "final_graphs" / "pareto")
    assert vs.DATA_DIR == str(REPO / "results" / "system_rev2026-09_primary")
    assert vs.CSV_DIR == str(REPO / "results" / "rev2026-09_primary_csv")
    assert vs.SENS_ROOT == str(REPO / "results")
    assert vs.ENDURANCE_CSV == str(REPO / "results" / "endurance_table.csv")
    assert vs.SIDECAR_DIR == str(REPO / "benchmarks")
    assert vs.OUTPUT_DIR == str(REPO / "results" / "slide_graphs_rev2026-09")


def test_archive_old_graphs_and_logging_defaults_follow_the_checkout(tmp_path, monkeypatch):
    master = importlib.import_module("mbmm_master")
    # The defaults resolve at call time through get_project_root(), so a
    # redirected root is honoured (this is also what keeps tests off results/).
    monkeypatch.setattr(master, "get_project_root", lambda: tmp_path)
    master.archive_old_graphs()            # nothing to archive; must not touch REPO/results
    assert not any(tmp_path.glob("results/archive_*"))
    lc = importlib.import_module("logging_config")
    assert lc.default_log_dir() == str(REPO / "results" / "logs")
