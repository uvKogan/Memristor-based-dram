"""
Tests for T5.4: label/color-table completeness and explicit primary/secondary
technology handling across the four visualize_*.py scripts, plus
visualize_slides.py's data-driven value loading.

Uses matplotlib's Agg backend (headless, no display needed) and never writes
into results/ -- all figure output goes to tmp_path / a module-scoped tmp dir.
"""
import json
import os

import matplotlib
matplotlib.use("Agg")

import pandas as pd
import pytest

import process_metrics as pm
import visualize_results as vr
import visualize_hero_graphs as vh
import visualize_pareto as vp
import visualize_slides as vs


# The technology labels process_metrics.py's classify_technology() can
# actually produce for this revision (task dispatch's authoritative list).
# Cross-checked below against representative filenames so this can't silently
# drift from classify_technology's own patterns.
TECHNOLOGY_LABELS_PRODUCED = {
    '1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC',
    'DDR5_4800', 'DDR5_4800_64B', 'pcm_microsoft_2009',
    '1T1R_SILICON', '1S1R_SILICON',
}

REPRESENTATIVE_FILENAMES = {
    '1T1R_SLC': 'stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out',
    '1T1R_MLC': 'stats_reram_22nm_1t1r_mlc_full_dimm_gcc_spec2017.out',
    '1S1R_SLC': 'stats_reram_22nm_selector_slc_full_dimm_gcc_spec2017.out',
    '1S1R_MLC': 'stats_reram_22nm_selector_mlc_full_dimm_gcc_spec2017.out',
    'DDR5_4800': 'stats_DDR5_4800_DRAM_subchannel_gcc_spec2017.out',
    'DDR5_4800_64B': 'stats_DDR5_4800_DRAM_64B_gcc_spec2017.out',
    'pcm_microsoft_2009': 'stats_pcm_microsoft_2009_gcc_spec2017.out',
    '1T1R_SILICON': 'stats_reram_micron16gb_1t1r_full_dimm_gcc_spec2017.out',
    '1S1R_SILICON': 'stats_reram_sandisk32gb_1s1r_full_dimm_gcc_spec2017.out',
}


@pytest.mark.parametrize("tech,filename", sorted(REPRESENTATIVE_FILENAMES.items()))
def test_representative_filenames_classify_as_expected(tech, filename):
    # Guards TECHNOLOGY_LABELS_PRODUCED against drifting from
    # process_metrics.classify_technology's own patterns.
    assert pm.classify_technology(filename) == tech


# ----------------------------------------------------------------------
# (a) every technology label has a label/color-table entry in each script
# ----------------------------------------------------------------------

def test_visualize_results_label_and_color_tables_complete():
    missing_labels = TECHNOLOGY_LABELS_PRODUCED - set(vr.TECH_LABELS)
    missing_colors = TECHNOLOGY_LABELS_PRODUCED - set(vr.TECHNOLOGY_COLORS)
    assert not missing_labels, f"visualize_results.TECH_LABELS missing: {missing_labels}"
    assert not missing_colors, f"visualize_results.TECHNOLOGY_COLORS missing: {missing_colors}"


def test_visualize_hero_graphs_label_and_color_tables_complete():
    missing_labels = TECHNOLOGY_LABELS_PRODUCED - set(vh.TECH_LABELS)
    missing_colors = TECHNOLOGY_LABELS_PRODUCED - set(vh.TECHNOLOGY_COLORS)
    assert not missing_labels, f"visualize_hero_graphs.TECH_LABELS missing: {missing_labels}"
    assert not missing_colors, f"visualize_hero_graphs.TECHNOLOGY_COLORS missing: {missing_colors}"


def test_visualize_pareto_technology_configs_complete():
    missing = TECHNOLOGY_LABELS_PRODUCED - set(vp.TECHNOLOGY_CONFIGS)
    assert not missing, f"visualize_pareto.TECHNOLOGY_CONFIGS missing: {missing}"
    for tech in TECHNOLOGY_LABELS_PRODUCED:
        cfg = vp.TECHNOLOGY_CONFIGS[tech]
        assert {'marker', 'color', 'label'} <= set(cfg)


def test_visualize_slides_label_and_color_tables_complete():
    missing_labels = TECHNOLOGY_LABELS_PRODUCED - set(vs.TECH_LABELS)
    missing_colors = TECHNOLOGY_LABELS_PRODUCED - set(vs.TECH_COLORS)
    assert not missing_labels, f"visualize_slides.TECH_LABELS missing: {missing_labels}"
    assert not missing_colors, f"visualize_slides.TECH_COLORS missing: {missing_colors}"


# ----------------------------------------------------------------------
# (b) the primary-figure filter drops the 64B and SILICON labels
# ----------------------------------------------------------------------

SECONDARY = {'DDR5_4800_64B', '1T1R_SILICON', '1S1R_SILICON'}


@pytest.mark.parametrize("module", [vr, vh, vp, vs])
def test_secondary_technologies_are_not_primary(module):
    assert SECONDARY <= module.SECONDARY_TECHNOLOGIES
    assert module.PRIMARY_TECHNOLOGIES.isdisjoint(module.SECONDARY_TECHNOLOGIES)
    assert SECONDARY.isdisjoint(module.PRIMARY_TECHNOLOGIES)


def test_visualize_results_primary_tech_order_drops_secondary():
    order = vr.primary_tech_order()
    assert not (set(order) & SECONDARY)
    assert set(order) == set(vr.PRIMARY_TECHNOLOGIES)


def test_visualize_hero_graphs_primary_only_drops_secondary():
    df = pd.DataFrame({
        'Technology': ['DDR5_4800', '1T1R_SLC', 'DDR5_4800_64B', '1T1R_SILICON'],
        'Area_Density_Ratio': [1.0, 2.0, 1.0, 2.0],
    })
    filtered = vh.primary_only(df)
    assert set(filtered['Technology']) == {'DDR5_4800', '1T1R_SLC'}

    d = {'DDR5_4800': 1.0, '1T1R_SLC': 2.0, 'DDR5_4800_64B': 3.0, '1S1R_SILICON': 4.0}
    filtered_d = vh.primary_only_dict(d)
    assert set(filtered_d) == {'DDR5_4800', '1T1R_SLC'}


def test_visualize_pareto_load_drops_secondary(tmp_path):
    rows = []
    for tech in ['DDR5_4800', '1T1R_SLC', 'DDR5_4800_64B', '1T1R_SILICON']:
        rows.append({'Technology': tech, 'Architecture': 'full_dimm',
                      'Benchmark': 'gcc_spec2017', 'Latency_ns': 40.0, 'Power': 1.0})
    csv_path = tmp_path / "processed_pareto_metrics.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    old_metrics_file = vp.METRICS_FILE
    vp.METRICS_FILE = str(csv_path)
    try:
        benchmark_data = vp.load_pareto_metrics()
    finally:
        vp.METRICS_FILE = old_metrics_file

    techs_present = {d['Technology'] for d in benchmark_data['gcc_spec2017']}
    assert techs_present == {'DDR5_4800', '1T1R_SLC'}


def test_visualize_slides_filter_primary_technologies_drops_secondary():
    df = pd.DataFrame({
        'Technology': ['DDR5_4800', '1T1R_SLC', 'DDR5_4800_64B', '1S1R_SILICON'],
        'Latency_ns': [1, 2, 3, 4],
    })
    filtered = vs.filter_primary_technologies(df)
    assert set(filtered['Technology']) == {'DDR5_4800', '1T1R_SLC'}


@pytest.mark.parametrize("module", [vr, vp])
def test_unknown_technology_raises_loudly(module, tmp_path):
    rows = [{'Technology': 'TOTALLY_UNKNOWN_TECH', 'Architecture': 'full_dimm',
             'Benchmark': 'gcc_spec2017', 'Latency_ns': 1.0, 'Power': 1.0,
             'HW_Latency_ns': 1.0, 'Queue_Latency_ns': 1.0, 'PDP': 1.0,
             'Dynamic_Power': 1.0, 'Static_Power': 1.0, 'Refresh_Power': 0.0}]
    csv_path = tmp_path / "metrics.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)

    attr = "METRICS_FILE"
    old_value = getattr(module, attr)
    setattr(module, attr, str(csv_path))
    try:
        with pytest.raises(ValueError, match="TOTALLY_UNKNOWN_TECH"):
            if module is vr:
                module.load_bar_chart_metrics()
            else:
                module.load_pareto_metrics()
    finally:
        setattr(module, attr, old_value)


def test_visualize_slides_filter_primary_technologies_raises_on_unknown():
    df = pd.DataFrame({'Technology': ['DDR5_4800', 'TOTALLY_UNKNOWN_TECH'],
                        'Latency_ns': [1, 2]})
    with pytest.raises(ValueError, match="TOTALLY_UNKNOWN_TECH"):
        vs.filter_primary_technologies(df)


# ----------------------------------------------------------------------
# (c) visualize_slides.py value loading from a tiny synthetic CSV/stats set,
# and loud failure on a missing key
# ----------------------------------------------------------------------

def _write_stats_file(path, total_write_requests=1_000_000, exit_cycle=750_000_000):
    path.write_text(
        f"i0.defaultMemory.totalWriteRequests {total_write_requests}\n"
        f"Exiting at cycle {exit_cycle} because simCycles {exit_cycle} reached.\n"
    )


@pytest.fixture
def synthetic_csv_dir(tmp_path):
    techs = ['DDR5_4800', 'pcm_microsoft_2009', '1T1R_SLC', '1T1R_MLC', '1S1R_SLC', '1S1R_MLC']
    rows = []
    for tech in techs:
        for benchmark in ('gcc_spec2017', 'lbm_spec2017'):
            completed = 2_500_000 if tech == 'pcm_microsoft_2009' else 5_000_000
            rows.append({
                'Technology': tech, 'Architecture': 'full_dimm', 'Benchmark': benchmark,
                'Latency_ns': 50.0, 'Power': 1.0, 'Completed_Requests': completed,
            })
    pd.DataFrame(rows).to_csv(tmp_path / "processed_bar_chart_metrics.csv", index=False)
    return tmp_path


@pytest.fixture
def synthetic_stats_dir(tmp_path):
    stats_dir = tmp_path / "system"
    stats_dir.mkdir()
    for benchmark in ('gcc_spec2017', 'lbm_spec2017', 'stream', 'alexnet_layer1_ofmap'):
        _write_stats_file(
            stats_dir / f"stats_reram_22nm_1t1r_slc_full_dimm_{benchmark}.out")
    return stats_dir


def test_lbm_completion_pct_reads_from_csv(synthetic_csv_dir):
    df = pd.read_csv(synthetic_csv_dir / "processed_bar_chart_metrics.csv")
    techs = ['DDR5_4800', '1T1R_SLC', 'pcm_microsoft_2009']
    pct = vs._lbm_completion_pct(df, techs)
    assert pct['DDR5_4800'] == pytest.approx(100.0)
    assert pct['1T1R_SLC'] == pytest.approx(100.0)
    assert pct['pcm_microsoft_2009'] == pytest.approx(50.0)


def test_lbm_completion_pct_fails_loudly_on_missing_row(synthetic_csv_dir):
    df = pd.read_csv(synthetic_csv_dir / "processed_bar_chart_metrics.csv")
    with pytest.raises(ValueError, match="NONEXISTENT_TECH"):
        vs._lbm_completion_pct(df, ['DDR5_4800', 'NONEXISTENT_TECH'])


def test_lbm_completion_pct_fails_loudly_on_missing_completed_requests(synthetic_csv_dir):
    df = pd.read_csv(synthetic_csv_dir / "processed_bar_chart_metrics.csv")
    df.loc[df['Technology'] == 'DDR5_4800', 'Completed_Requests'] = float('nan')
    with pytest.raises(ValueError, match="Completed_Requests"):
        vs._lbm_completion_pct(df, ['DDR5_4800', '1T1R_SLC'])


def test_endurance_write_rates_read_from_stats_files(synthetic_stats_dir, monkeypatch):
    monkeypatch.setattr(vs, "DATA_DIR", str(synthetic_stats_dir))
    rates = vs._endurance_write_rates()
    assert set(rates) == {'LBM\n(worst case)', 'GCC', 'STREAM', 'AlexNet\nOFMAP'}
    # 1,000,000 writes / (750,000,000 cycles * 1/3000 MHz-derived ns * 1e-9 s) = 4,000,000 writes/s
    for rate in rates.values():
        assert rate == pytest.approx(4_000_000.0, rel=1e-6)


def test_endurance_write_rates_fails_loudly_on_missing_stats_file(tmp_path, monkeypatch):
    empty_dir = tmp_path / "empty_system"
    empty_dir.mkdir()
    monkeypatch.setattr(vs, "DATA_DIR", str(empty_dir))
    with pytest.raises(FileNotFoundError, match="lbm_spec2017"):
        vs._endurance_write_rates()


def test_extract_total_write_requests_fails_loudly_on_missing_key():
    with pytest.raises(ValueError, match="totalWriteRequests"):
        vs._extract_total_write_requests("no relevant stats here\n", "fake_path.out")


def test_extract_elapsed_seconds_fails_loudly_on_missing_key():
    with pytest.raises(ValueError, match="Exiting at cycle"):
        vs._extract_elapsed_seconds("no relevant stats here\n", "fake_path.out")


def test_visualize_slides_full_pipeline_smoke(synthetic_csv_dir, synthetic_stats_dir, tmp_path, monkeypatch):
    # End-to-end smoke test for the two value-loading paths this task
    # rewired (completion % and endurance write rates), using a tiny
    # synthetic CSV + stats set -- not the full slide deck (that needs
    # stream/gpt2/alexnet benchmarks too, out of scope for a "tiny synthetic"
    # fixture), just the pieces item 1 replaced.
    df = pd.read_csv(synthetic_csv_dir / "processed_bar_chart_metrics.csv")
    monkeypatch.setattr(vs, "DATA_DIR", str(synthetic_stats_dir))

    techs = ['DDR5_4800', '1T1R_SLC', '1S1R_SLC', '1T1R_MLC', '1S1R_MLC', 'pcm_microsoft_2009']
    pct = vs._lbm_completion_pct(df, techs)
    assert all(0.0 <= v <= 100.0 for v in pct.values())

    rates = vs._endurance_write_rates()
    assert all(r > 0 for r in rates.values())


def test_slides_stats_path_refuses_silicon_label():
    # T5.4 review: RERAM_KEY_PREFIX maps 1T1R_SILICON onto the SLC hardware
    # key, so _stats_path() would have returned the SLC stats file mislabeled.
    import visualize_slides as vs
    with pytest.raises(ValueError, match="SILICON"):
        vs._stats_path('1T1R_SILICON', 'full_dimm', 'gcc_spec2017')
