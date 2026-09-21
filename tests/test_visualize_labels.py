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
    # T6.2: only the three SUSTAINED gem5 workloads. The AlexNet OFMAP row was
    # dropped because its "rate" depends entirely on the denominator chosen
    # (a 4.5 us burst against either its own drain time or the 250 ms window),
    # which Project_Book.typ Table 5 flags as burst-derived and not a
    # sustained requirement.
    assert set(rates) == {'GCC', 'LBM', 'STREAM'}
    # 1,000,000 writes / (750,000,000 cycles * 1/3000 MHz-derived ns * 1e-9 s) = 4,000,000 writes/s
    for rate in rates.values():
        assert rate == pytest.approx(4_000_000.0, rel=1e-6)


def test_endurance_write_rates_fails_loudly_on_missing_stats_file(tmp_path, monkeypatch):
    empty_dir = tmp_path / "empty_system"
    empty_dir.mkdir()
    monkeypatch.setattr(vs, "DATA_DIR", str(empty_dir))
    # Whichever of the three sustained workloads is reached first, the
    # failure must name the missing stats file rather than plot a default.
    with pytest.raises(FileNotFoundError, match="Missing stats file"):
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


# ----------------------------------------------------------------------
# (d) T6.2: the loaders the rebuilt deck charts added -- sensitivity axes,
# the endurance projection table, module capacity and the CSV cell reader.
# Each must fail loudly, naming the file and the key.
# ----------------------------------------------------------------------

def test_sensitivity_csv_path_refuses_unknown_axis():
    with pytest.raises(ValueError, match="nonexistent_axis"):
        vs.sensitivity_csv_path('nonexistent_axis')


@pytest.mark.parametrize("axis", sorted(vs.SENSITIVITY_AXES))
def test_sensitivity_csv_path_builds_the_documented_layout(axis, monkeypatch):
    monkeypatch.setattr(vs, "SENS_ROOT", "/tmp/sensroot")
    path = vs.sensitivity_csv_path(axis)
    assert path == os.path.join(
        "/tmp/sensroot", f"system_rev2026-09_{axis}", "_csv",
        "processed_bar_chart_metrics.csv")


def test_load_sensitivity_bar_chart_fails_loudly_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "SENS_ROOT", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="freq1333"):
        vs.load_sensitivity_bar_chart('freq1333')


def test_load_sensitivity_bar_chart_raises_on_unknown_technology(tmp_path, monkeypatch):
    axis_dir = tmp_path / "system_rev2026-09_freq2400" / "_csv"
    axis_dir.mkdir(parents=True)
    pd.DataFrame([{'Technology': 'TOTALLY_UNKNOWN_TECH', 'Architecture': 'full_dimm',
                   'Benchmark': 'gcc_spec2017', 'Latency_ns': 1.0}]).to_csv(
        axis_dir / "processed_bar_chart_metrics.csv", index=False)
    monkeypatch.setattr(vs, "SENS_ROOT", str(tmp_path))
    with pytest.raises(ValueError, match="TOTALLY_UNKNOWN_TECH"):
        vs.load_sensitivity_bar_chart('freq2400')


@pytest.fixture
def synthetic_endurance_csv(tmp_path):
    rows = []
    for trace in ('gcc_spec2017', 'lbm_spec2017'):
        for scheme, years in (('NONE', 0.001), ('START_GAP', 0.001),
                              ('RANDOMIZED_START_GAP', 0.2), ('IDEAL', 3.5)):
            rows.append({'trace': trace, 'scheme': scheme, 'capacity_gib': 64,
                         'endurance': 1e6, 'write_reduction': 1.0,
                         'rate_basis': 'admitted', 'lifetime_years': years,
                         'required_endurance_10yr': 1e6})
    path = tmp_path / "endurance_table.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    return path


def test_load_endurance_projection_selects_the_documented_slice(
        synthetic_endurance_csv, monkeypatch):
    monkeypatch.setattr(vs, "ENDURANCE_CSV", str(synthetic_endurance_csv))
    df = vs.load_endurance_projection()
    assert len(df) == 8
    assert set(df['scheme']) == {'NONE', 'START_GAP', 'RANDOMIZED_START_GAP', 'IDEAL'}


def test_load_endurance_projection_fails_loudly_on_empty_slice(
        synthetic_endurance_csv, monkeypatch):
    monkeypatch.setattr(vs, "ENDURANCE_CSV", str(synthetic_endurance_csv))
    with pytest.raises(ValueError, match="capacity_gib=128"):
        vs.load_endurance_projection(capacity_gib=128)


def test_load_endurance_projection_fails_loudly_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(vs, "ENDURANCE_CSV", str(tmp_path / "nope.csv"))
    with pytest.raises(FileNotFoundError, match="nope.csv"):
        vs.load_endurance_projection()


def test_endurance_value_reads_a_named_cell(synthetic_endurance_csv, monkeypatch):
    monkeypatch.setattr(vs, "ENDURANCE_CSV", str(synthetic_endurance_csv))
    df = vs.load_endurance_projection()
    assert vs.endurance_value(df, 'lbm_spec2017', 'IDEAL') == pytest.approx(3.5)


def test_endurance_value_fails_loudly_on_missing_scheme(
        synthetic_endurance_csv, monkeypatch):
    monkeypatch.setattr(vs, "ENDURANCE_CSV", str(synthetic_endurance_csv))
    df = vs.load_endurance_projection()
    with pytest.raises(ValueError, match="NO_SUCH_SCHEME"):
        vs.endurance_value(df, 'lbm_spec2017', 'NO_SUCH_SCHEME')


def test_endurance_value_fails_loudly_on_blank_cell(
        synthetic_endurance_csv, monkeypatch):
    monkeypatch.setattr(vs, "ENDURANCE_CSV", str(synthetic_endurance_csv))
    df = vs.load_endurance_projection().copy()
    df.loc[df['scheme'] == 'IDEAL', 'lifetime_years'] = float('nan')
    with pytest.raises(ValueError, match="lifetime_years"):
        vs.endurance_value(df, 'lbm_spec2017', 'IDEAL')


def test_extract_capacity_gib_sums_every_channel():
    content = ("defaultMemory.channel0.FRFCFS capacity is 4096 MB.\n"
               "defaultMemory.channel1.FRFCFS capacity is 4096 MB.\n")
    assert vs._extract_capacity_gib(content, "fake.out") == pytest.approx(8.0)


def test_extract_capacity_gib_fails_loudly_on_missing_key():
    with pytest.raises(ValueError, match="capacity is"):
        vs._extract_capacity_gib("no relevant stats here\n", "fake_path.out")


def test_extract_capacity_gib_fails_loudly_on_zero_capacity():
    with pytest.raises(ValueError, match="non-positive"):
        vs._extract_capacity_gib("channel0.FRFCFS capacity is 0 MB.\n", "fake.out")


def test_module_capacity_gib_resolves_the_non_reram_baselines(tmp_path, monkeypatch):
    # The DDR5 and PCM stats filenames carry no architecture token; without
    # NON_RERAM_STATS_STEM the per-GiB charts could not read their capacity.
    stats_dir = tmp_path / "system"
    stats_dir.mkdir()
    for stem, mb in (('DDR5_4800_DRAM_subchannel', 8192), ('pcm_microsoft_2009', 4096)):
        (stats_dir / f"stats_{stem}_gcc_spec2017.out").write_text(
            f"defaultMemory.channel0.FRFCFS capacity is {mb} MB.\n")
    monkeypatch.setattr(vs, "DATA_DIR", str(stats_dir))
    assert vs.module_capacity_gib('DDR5_4800') == pytest.approx(8.0)
    assert vs.module_capacity_gib('pcm_microsoft_2009') == pytest.approx(4.0)


def test_stats_path_fails_loudly_on_a_technology_with_no_stem():
    with pytest.raises(ValueError, match="2D_DRAM_example"):
        vs._stats_path('2D_DRAM_example', 'full_dimm', 'gcc_spec2017')


def test_value_fails_loudly_on_missing_row(synthetic_csv_dir):
    df = pd.read_csv(synthetic_csv_dir / "processed_bar_chart_metrics.csv")
    with pytest.raises(ValueError, match="NONEXISTENT_TECH"):
        vs.value(df, 'gcc_spec2017', 'NONEXISTENT_TECH', 'Latency_ns')


def test_value_fails_loudly_on_blank_cell(synthetic_csv_dir):
    df = pd.read_csv(synthetic_csv_dir / "processed_bar_chart_metrics.csv")
    df.loc[df['Technology'] == '1T1R_SLC', 'Latency_ns'] = float('nan')
    with pytest.raises(ValueError, match="Latency_ns"):
        vs.value(df, 'gcc_spec2017', '1T1R_SLC', 'Latency_ns')


def test_value_reads_a_named_cell(synthetic_csv_dir):
    df = pd.read_csv(synthetic_csv_dir / "processed_bar_chart_metrics.csv")
    assert vs.value(df, 'gcc_spec2017', '1T1R_SLC', 'Latency_ns') == pytest.approx(50.0)


def test_save_refuses_an_em_dash_in_a_footnote(tmp_path, monkeypatch):
    # The deck, the outline and the cheat sheet must contain no U+2014; a
    # footnote baked into a PNG is the one place a grep over the HTML would
    # not catch one.
    import matplotlib.pyplot as plt
    monkeypatch.setattr(vs, "OUTPUT_DIR", str(tmp_path))
    fig, ax = plt.subplots()
    try:
        with pytest.raises(ValueError, match="em-dash"):
            vs._save(fig, "scratch.png", footnote="a — b")
    finally:
        plt.close(fig)


# ----------------------------------------------------------------------
# (e) Minor-6 (final review 2026-09): the four label tables must AGREE
#
# The review asked for the four duplicated technology label/color/order
# tables to be merged into one module. That is deliberately NOT done here (it
# would touch every figure script at once, for no change in output). Instead
# this section pins the agreement the duplication is supposed to preserve, so
# the next edit to one table cannot silently drift from the other three.
# ----------------------------------------------------------------------

def _label_tables():
    """{module name: {technology: display label}} for the four visualizers."""
    return {
        "visualize_results": dict(vr.TECH_LABELS),
        "visualize_hero_graphs": dict(vh.TECH_LABELS),
        "visualize_pareto": {k: v["label"] for k, v in vp.TECHNOLOGY_CONFIGS.items()},
        "visualize_slides": dict(vs.TECH_LABELS),
    }


def _normalize(label):
    """Collapse whitespace: visualize_slides wraps two labels onto two lines
    for a slide, which is a layout choice, not a different name."""
    return " ".join(label.split())


# The only display names that deliberately differ between scripts, each pinned
# exactly. A NEW divergence, or a change to one of these, fails the test below.
#
# visualize_pareto's scatter legend has no axis title to lean on, so it spells
# out what each baseline is; visualize_slides says "legacy" for the same reason
# on a slide read from the back of a room. Both were chosen in T5.4 / T6.2.
DELIBERATE_LABEL_VARIANTS = {
    ("visualize_pareto", "DDR5_4800"): "DDR5-4800 (Baseline)",
    ("visualize_pareto", "pcm_microsoft_2009"): "PCM (Microsoft 2009)",
    ("visualize_slides", "pcm_microsoft_2009"): "PCM (legacy)",
    # The deck wraps the two silicon labels onto two lines and drops the word
    # "timings" to fit a slide legend; the citation itself is kept.
    ("visualize_slides", "1T1R_SILICON"): "1T1R silicon\n(Micron 16 Gb)",
    ("visualize_slides", "1S1R_SILICON"): "1S1R silicon\n(SanDisk 32 Gb)",
}


def test_all_four_label_tables_cover_exactly_the_produced_labels():
    """Key sets: every label process_metrics.classify_technology can produce,
    and nothing beyond the two documented excluded DRAM examples."""
    allowed_extra = vr.EXCLUDED_TECHNOLOGIES
    for name, table in _label_tables().items():
        missing = TECHNOLOGY_LABELS_PRODUCED - set(table)
        extra = set(table) - TECHNOLOGY_LABELS_PRODUCED - allowed_extra
        assert not missing, f"{name} is missing {missing}"
        assert not extra, f"{name} carries unknown technologies {extra}"


def test_all_four_label_tables_agree_on_every_display_name():
    tables = _label_tables()
    canonical = tables["visualize_results"]  # the primary bar charts
    for name, table in tables.items():
        for tech in sorted(TECHNOLOGY_LABELS_PRODUCED):
            expected = DELIBERATE_LABEL_VARIANTS.get((name, tech),
                                                      canonical[tech])
            assert _normalize(table[tech]) == _normalize(expected), (
                f"{name}[{tech!r}] = {table[tech]!r}; expected {expected!r}. "
                f"Either fix the table or add the difference to "
                f"DELIBERATE_LABEL_VARIANTS with a reason.")


def test_every_deliberate_label_variant_is_still_a_real_difference():
    """Guards the allow-list itself: an entry that has become identical to the
    canonical label is stale and must be removed."""
    tables = _label_tables()
    canonical = tables["visualize_results"]
    for (name, tech), variant in DELIBERATE_LABEL_VARIANTS.items():
        assert _normalize(tables[name][tech]) == _normalize(variant)
        assert _normalize(variant) != _normalize(canonical[tech]), (
            f"{name}[{tech!r}] now matches the canonical label; drop it from "
            f"DELIBERATE_LABEL_VARIANTS.")


def test_the_three_color_tables_cover_the_same_technologies():
    """Colors themselves differ on purpose (the deck has its own palette), but
    the three tables must cover the same technology set."""
    sets = {
        "visualize_results": set(vr.TECHNOLOGY_COLORS),
        "visualize_hero_graphs": set(vh.TECHNOLOGY_COLORS),
        "visualize_slides": set(vs.TECH_COLORS),
        "visualize_pareto": set(vp.TECHNOLOGY_CONFIGS) - vr.EXCLUDED_TECHNOLOGIES,
    }
    reference = sets["visualize_results"]
    assert reference == TECHNOLOGY_LABELS_PRODUCED
    for name, s in sets.items():
        assert s == reference, f"{name} colors cover {s ^ reference} differently"


def test_primary_and_secondary_partitions_agree_across_the_four():
    for module in (vr, vh, vp, vs):
        assert module.PRIMARY_TECHNOLOGIES == vr.PRIMARY_TECHNOLOGIES
        assert module.SECONDARY_TECHNOLOGIES == vr.SECONDARY_TECHNOLOGIES
        assert (module.PRIMARY_TECHNOLOGIES | module.SECONDARY_TECHNOLOGIES
                == TECHNOLOGY_LABELS_PRODUCED)
