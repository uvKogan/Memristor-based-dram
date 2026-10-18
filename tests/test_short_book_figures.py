"""Tests for tools/plot_short_book_figures.py (task E2).

Checks the two loaders against the frozen CSVs they read (re-read
independently here with the csv module, not via the module under test), and
that the two plot functions write a PNG. Frozen CSV paths under results/ are
acceptable test inputs (they are the project's frozen, checked-in datasets),
but a test skips cleanly with a message if one of them is absent -- these
tests must not depend on the live results/system tree or on anything
generated under simulators/.
"""
import csv
import os
import sys
import pathlib

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import plot_short_book_figures as fig  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

CLOCK_PATHS = {
    800: REPO_ROOT / "results" / "rev2026-09_primary_csv" / "processed_bar_chart_metrics.csv",
    1333: REPO_ROOT / "results" / "system_rev2026-09_freq1333" / "_csv" / "processed_bar_chart_metrics.csv",
    2400: REPO_ROOT / "results" / "system_rev2026-09_freq2400" / "_csv" / "processed_bar_chart_metrics.csv",
}
ENDURANCE_PATH = REPO_ROOT / "results" / "endurance_table.csv"


def _require_frozen(*paths):
    missing = [str(p) for p in paths if not os.path.isfile(p)]
    if missing:
        pytest.skip(f"frozen file(s) not present in this checkout: {missing}")


def _read_bar_chart_value(path, technology, benchmark='gcc_spec2017', architecture='full_dimm',
                           column='Latency_ns'):
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            if (row['Technology'] == technology and row['Benchmark'] == benchmark
                    and row['Architecture'] == architecture):
                return float(row[column])
    raise AssertionError(f"no row for {technology}/{architecture}/{benchmark} in {path}")


def _read_endurance_value(path, trace, scheme, capacity_gib='64', endurance='1000000.0',
                           write_reduction='1.0', rate_basis='admitted', column='lifetime_years'):
    with open(path, newline='') as f:
        for row in csv.DictReader(f):
            if (row['trace'] == trace and row['scheme'] == scheme
                    and row['capacity_gib'] == capacity_gib and row['endurance'] == endurance
                    and row['write_reduction'] == write_reduction
                    and row['rate_basis'] == rate_basis):
                return float(row[column])
    raise AssertionError(f"no row for {trace}/{scheme} in {path}")


# ---------------------------------------------------------------------------
# load_clock_series
# ---------------------------------------------------------------------------

def test_load_clock_series_keys():
    _require_frozen(*CLOCK_PATHS.values())
    series = fig.load_clock_series(CLOCK_PATHS)
    assert set(series) == {'1T1R_SLC', '1S1R_SLC', 'DDR5_4800', 'mhz'}
    assert series['mhz'] == [800, 1333, 2400]
    assert len(series['1T1R_SLC']) == 3
    assert len(series['1S1R_SLC']) == 3


def test_load_clock_series_matches_frozen_csvs():
    _require_frozen(*CLOCK_PATHS.values())
    series = fig.load_clock_series(CLOCK_PATHS)

    for i, mhz in enumerate(series['mhz']):
        path = CLOCK_PATHS[mhz]
        expected_1t1r = _read_bar_chart_value(path, '1T1R_SLC')
        expected_1s1r = _read_bar_chart_value(path, '1S1R_SLC')
        assert series['1T1R_SLC'][i] == pytest.approx(expected_1t1r)
        assert series['1S1R_SLC'][i] == pytest.approx(expected_1s1r)

    expected_ddr5 = _read_bar_chart_value(CLOCK_PATHS[800], 'DDR5_4800')
    assert series['DDR5_4800'] == pytest.approx(expected_ddr5)


def test_load_clock_series_expected_values_from_dispatch():
    """Cross-check against the dispatch's stated expected values (confirmed,
    not copied, from the frozen files) so a silent CSV drift is caught even
    if the loader and the independent re-read above agreed with each other."""
    _require_frozen(*CLOCK_PATHS.values())
    series = fig.load_clock_series(CLOCK_PATHS)
    assert series['1T1R_SLC'] == pytest.approx([41.4, 27.9, 19.0], abs=0.05)
    assert series['1S1R_SLC'] == pytest.approx([36.8, 23.6, 14.9], abs=0.05)
    assert series['DDR5_4800'] == pytest.approx(83.1, abs=0.05)


# ---------------------------------------------------------------------------
# load_endurance_rows
# ---------------------------------------------------------------------------

def test_load_endurance_rows_keys():
    _require_frozen(ENDURANCE_PATH)
    rows = fig.load_endurance_rows(str(ENDURANCE_PATH))
    traces = {r['trace'] for r in rows}
    schemes = {r['scheme'] for r in rows}
    assert traces == {'gcc_spec2017', 'lbm_spec2017', 'stream'}
    assert schemes == {'NONE', 'IDEAL', 'START_GAP', 'RANDOMIZED_START_GAP'}
    assert len(rows) == 12
    for r in rows:
        assert set(r) == {'trace', 'scheme', 'lifetime_years'}


def test_load_endurance_rows_matches_frozen_csv():
    _require_frozen(ENDURANCE_PATH)
    rows = fig.load_endurance_rows(str(ENDURANCE_PATH))
    for trace, _ in fig.TRACE_ORDER:
        for scheme, _, _ in fig.SCHEME_STYLE:
            expected = _read_endurance_value(str(ENDURANCE_PATH), trace, scheme)
            actual = fig._endurance_value(rows, trace, scheme)
            assert actual == pytest.approx(expected)


# ---------------------------------------------------------------------------
# plot functions write a PNG
# ---------------------------------------------------------------------------

def test_plot_clock_writes_png(tmp_path):
    _require_frozen(*CLOCK_PATHS.values())
    series = fig.load_clock_series(CLOCK_PATHS)
    out = tmp_path / "fig_clock_sensitivity.png"
    fig.plot_clock(series, str(out), dpi=80)
    assert out.is_file()
    assert out.stat().st_size > 0


def test_plot_endurance_writes_png(tmp_path):
    _require_frozen(ENDURANCE_PATH)
    rows = fig.load_endurance_rows(str(ENDURANCE_PATH))
    out = tmp_path / "fig_endurance_policy.png"
    fig.plot_endurance(rows, str(out), dpi=80)
    assert out.is_file()
    assert out.stat().st_size > 0


# ---------------------------------------------------------------------------
# no em-dash / en-dash anywhere the script writes text
# ---------------------------------------------------------------------------

def test_no_em_or_en_dash_in_source():
    src = pathlib.Path(fig.__file__).read_text()
    assert chr(0x2014) not in src, "em-dash (U+2014) found in plot_short_book_figures.py"
    assert chr(0x2013) not in src, "en-dash (U+2013) found in plot_short_book_figures.py"
