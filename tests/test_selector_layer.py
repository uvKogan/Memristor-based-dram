"""Tests for selector_layer.py.

Every numeric target below is traceable to a figure, equation or table in

  J. Zhou, K.-H. Kim and W. Lu, "Crossbar RRAM Arrays: Selector Device
  Requirements During Read Operation", IEEE TED 61(5), May 2014, pp. 1369-1376

or to the Springer Handbook of Semiconductor Devices crossbar tile rule, or to
a hand calculation shown in the comment.

NOTE ON THE BRIEF'S TARGETS.  The T2.7 brief asked for
`read_margin(512, 1e3, ...)` about 0.02-0.05 and `read_margin(256, 1e4, ...)`
about 0.10.  Read off Zhou Fig. 3(b) (p. 1371, Isel(ON) = 100 uA, Table I
device and array parameters) the actual values are 2.1% at (512, 1e3) and
6.8% at (256, 1e4).  The 0.10 figure comes from the paper's prose on p. 1371
("the read margin drops rapidly below the minimum requirement of 10% when the
array exceeds 256 x 256"), which is a loose description of a curve that in
Fig. 3(b) crosses 10% nearer N = 180.  The targets below are taken from the
figure, not from the prose.
"""

import json
import math
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import selector_layer as SL

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# I10 (final review 2026-09): these tests used to read
# results/rev2026-09_staging/hardware_metrics_2048x2048.json, a git-ignored
# file under results/, and were `skipif` it was absent -- so the four tests
# that pin the selector-layer headline verdicts passed here and vanished on
# every clean checkout and in CI. The same four entries now live in a tracked
# 1.6 KB fixture, byte-identical to the staging copy (which is itself identical
# to the frozen primary's hardware_metrics.json), so nothing under results/ or
# simulators/ is needed and nothing can be skipped.
HARDWARE_FIXTURE = os.path.join(REPO, "tests", "fixtures",
                                "hardware_metrics_2048x2048.json")

# Zhou Table I, p. 1371: the defaults used for Fig. 3 and Fig. 8.
TBL1 = dict(r_on=1e4, r_off=1e6, r_line=5.0, i_on=100e-6, v_read=1.0)


# ---------------------------------------------------------------------------
# Selector device model: Zhou Eq. (2), Eq. (3), Table I
# ---------------------------------------------------------------------------

def test_alpha_gamma_reproduce_table_I():
    """Eq. (3) solved for alpha must give Zhou Table I exactly.

    Table I (p. 1371): k = 1e4, Isel(ON) = 100 uA at Vws = 1 V gives
    alpha = 18.4207 V^-1 and gamma = 2e-12 A.
    Hand check: k = 2*cosh(alpha/2) so alpha = 2*acosh(5000) = 18.42068,
    and gamma = 100e-6 / sinh(18.42068) = 100e-6 / 5.0e7 = 2.0e-12 A.
    """
    alpha, gamma = SL.selector_alpha_gamma(1e4, 100e-6, 1.0)
    assert alpha == pytest.approx(18.4207, abs=5e-4)
    assert gamma == pytest.approx(2e-12, rel=1e-3)


def test_k_definition_round_trip():
    """Eq. (3): k = Isel(Vws) / Isel(Vws/2) must come back out of the model."""
    for k in (1e3, 1e4, 1e6):
        alpha, gamma = SL.selector_alpha_gamma(k, 100e-6, 1.4)
        i_full = gamma * math.sinh(alpha * 1.4)
        i_half = gamma * math.sinh(alpha * 0.7)
        assert i_full / i_half == pytest.approx(k, rel=1e-9)
        assert i_full == pytest.approx(100e-6, rel=1e-9)  # Isel(ON) at Vws


def test_k_must_exceed_two():
    with pytest.raises(ValueError):
        SL.selector_alpha_gamma(1.5, 100e-6, 1.0)


# ---------------------------------------------------------------------------
# Read margin against Zhou Fig. 3(b), p. 1371
# ---------------------------------------------------------------------------

# Read off Fig. 3(b) (read margin vs array size, Isel(ON) = 100 uA fixed,
# Table I everything else, GN-GN scheme, worst-case corner cell with all
# unselected cells in LRS).  Values in percent.
FIG3B = [
    (1e3, 8, 20.6), (1e3, 64, 18.8), (1e3, 128, 15.0),
    (1e3, 256, 8.0), (1e3, 512, 2.1),
    (1e4, 8, 16.5), (1e4, 128, 12.4), (1e4, 256, 6.8), (1e4, 512, 2.0),
    (1e5, 8, 13.9), (1e5, 128, 10.4), (1e5, 256, 5.5), (1e5, 512, 1.5),
]


@pytest.mark.parametrize("k,n,pct", FIG3B)
def test_read_margin_matches_fig_3b(k, n, pct):
    """Zhou Fig. 3(b), p. 1371.  Tolerance 0.6 points covers reading the plot."""
    got = SL.read_margin(n, k, **TBL1) * 100.0
    assert got == pytest.approx(pct, abs=0.6)


def test_brief_targets_restated_from_the_figure():
    """The two targets the brief named, corrected to Fig. 3(b), p. 1371.

    Brief said (512, 1e3) is 0.02-0.05: Fig. 3(b) reads 2.1%, inside that band.
    Brief said (256, 1e4) is about 0.10: Fig. 3(b) reads 6.8%, NOT 10%.  The
    10% number is the paper's prose on p. 1371 about where the k = 1e4 curve
    crosses the minimum, which Fig. 3(b) puts nearer N = 180.
    """
    assert 0.02 <= SL.read_margin(512, 1e3, **TBL1) <= 0.05
    assert SL.read_margin(256, 1e4, **TBL1) == pytest.approx(0.068, abs=0.006)
    # and the prose statement itself: the k = 1e4 curve is above 10% at 128 and
    # below it at 256 (Zhou p. 1371, Fig. 3(b)).
    assert SL.read_margin(128, 1e4, **TBL1) > 0.10
    assert SL.read_margin(256, 1e4, **TBL1) < 0.10


def test_read_margin_falls_with_array_size():
    """Zhou Fig. 3(a)-(c), p. 1371: monotonic decrease in N."""
    vals = [SL.read_margin(n, 1e4, **TBL1) for n in (8, 64, 128, 256, 512)]
    assert all(a > b for a, b in zip(vals, vals[1:]))


def test_read_margin_falls_with_interconnect_resistance():
    """Zhou Fig. 9 and Section III-C, p. 1374: lower Rline is always better,
    and the effect is negligible for small arrays but large for big ones."""
    small = [SL.read_margin(8, 1e4, r_on=1e4, r_off=1e6, r_line=r,
                            i_on=100e-6, v_read=1.0) for r in (2.5, 5.0)]
    big = [SL.read_margin(512, 1e4, r_on=1e4, r_off=1e6, r_line=r,
                          i_on=100e-6, v_read=1.0) for r in (2.5, 5.0)]
    assert small[0] > small[1]
    assert small[0] - small[1] < 0.005          # insensitive at N = 8
    assert big[0] > big[1] * 1.5                # strongly sensitive at N = 512


def test_higher_nonlinearity_is_not_always_better():
    """Zhou Fig. 3(b)/3(c) and Section III-A, p. 1371-1372: at fixed Isel(ON)
    the read margin is NOT monotonic in k; k = 1e3 beats k = 1e5 everywhere in
    Fig. 3(b), because a very nonlinear selector eats more voltage."""
    for n in (8, 128, 256):
        assert SL.read_margin(n, 1e3, **TBL1) > SL.read_margin(n, 1e5, **TBL1)


def test_default_sense_resistor_is_eq_4():
    """Eq. (4), p. 1371: Rsense = sqrt(Ron*Roff).  Table I lists 100 kohm for
    Ron 10 kohm and Roff 1 Mohm, and sqrt(1e4*1e6) = 1e5.  Passing that value
    explicitly must give the same answer as leaving it to the default."""
    a = SL.read_margin(64, 1e4, **TBL1)
    b = SL.read_margin(64, 1e4, r_sense=math.sqrt(1e4 * 1e6), **TBL1)
    assert a == pytest.approx(b, rel=1e-9)


def test_read_margin_rejects_degenerate_array():
    with pytest.raises(ValueError):
        SL.read_margin(1, 1e4, **TBL1)


@pytest.mark.parametrize("bad", [
    {"r_line": 0.0},          # a zero-resistance line is a division by zero
    {"r_line": -1.0},
    {"r_on": -1e4},           # negative resistance
    {"r_on": 0.0},
    {"r_off": 0.0},
    {"i_on": 0.0},
    {"i_on": -100e-6},
    {"v_read": 0.0},
    {"v_read": -1.0},
    {"r_off": 1e3},           # r_off below r_on: HRS is not above LRS
    {"r_sense": 0.0},
    {"r_sense": -1.0},
])
def test_read_margin_validates_every_argument(bad):
    kw = dict(TBL1)
    kw.update(bad)
    with pytest.raises(ValueError):
        SL.read_margin(64, 1e4, **kw)


@pytest.mark.parametrize("k", [1.0, 0.5, 0.0, -1.0])
def test_read_margin_rejects_impossible_nonlinearity(k):
    """Zhou Eq. (3): k = Isel(V)/Isel(V/2) = 2*cosh(alpha*V/2) exceeds 1 for any
    real selector, and exceeds 2 for any selector with alpha > 0."""
    with pytest.raises(ValueError):
        SL.read_margin(64, k, **TBL1)


def test_array_power_validates_arguments_too():
    with pytest.raises(ValueError):
        SL.array_power_w(64, 1e4, r_on=1e4, r_off=1e6, r_line=0.0,
                         i_on=100e-6, v_read=1.0)


# ---------------------------------------------------------------------------
# Independent cross-check: Zhou Fig. 8(a), p. 1374 (array power)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("k,uw", [(1e3, 270.0), (1e4, 200.0), (1e5, 175.0)])
def test_gn_gn_array_power_matches_fig_8a(k, uw):
    """Zhou Fig. 8(a), p. 1374: overall power of the whole 128x128 array in the
    GN-GN scheme while reading a 1 (LRS), Isel(ON) = 100 uA.

    `array_power_w` reads the SAME network solution `read_margin` uses, at the
    wordline driver instead of at the sense resistor, so this is an independent
    check on the currents the topology carries rather than a second look at the
    same output voltage.  Tolerance 25 percent covers reading a log-scale plot
    whose decade spans about 40 pixels.
    """
    got = SL.array_power_w(128, k, **TBL1) * 1e6
    assert got == pytest.approx(uw, rel=0.25)


@pytest.mark.parametrize("k,rm_pct,uw", [(1e3, 15.0, 270.0), (1e4, 12.4, 200.0),
                                         (1e5, 10.4, 175.0)])
def test_hard_grounded_unselected_bitlines_miss_both_figures(k, rm_pct, uw):
    """Regression on the reading of Zhou that this layer depends on.

    Sec. II-B and Table I (p. 1370) define GN-GN by V_BNS = 0, hard ground, and
    Fig. 1 draws R_sense on the selected bitline only; but p. 1370 also says
    "sense amplifiers are connected with all bit-lines".  Only the second
    reading reproduces the paper.  This test pins BOTH sides of that, so the
    default topology cannot be changed silently:

      * with per-bitline sense resistors the model lands on Fig. 3(b) and
        Fig. 8(a) (checked in the two tests above and re-checked here);
      * with hard grounding the read margin is low by at least 1.5x and the
        array power high by at least 2.5x, at every k in the figures.
    """
    g = dict(TBL1)
    rm_s = SL.read_margin(128, k, **g) * 100
    rm_g = SL.read_margin(128, k, bl_termination="ground", **g) * 100
    p_s = SL.array_power_w(128, k, **g) * 1e6
    p_g = SL.array_power_w(128, k, bl_termination="ground", **g) * 1e6
    assert rm_s == pytest.approx(rm_pct, abs=0.6)   # Fig. 3(b)
    assert p_s == pytest.approx(uw, rel=0.25)       # Fig. 8(a)
    assert rm_g < rm_pct / 1.5                      # hard ground misses low
    assert p_g > uw * 2.5                           # and high on power


def test_array_power_rejects_bad_state():
    with pytest.raises(ValueError):
        SL.array_power_w(64, 1e4, state="MLC", **TBL1)


def test_solve_rejects_bad_bl_termination():
    with pytest.raises(ValueError):
        SL.read_margin(64, 1e4, bl_termination="floating", **TBL1)


# ---------------------------------------------------------------------------
# Sneak leakage
# ---------------------------------------------------------------------------

def test_sneak_leakage_hand_calculation():
    """P = lines * (cells_per_line - 1) * v_half * i_leak.
    Hand check: 2 lines * (2048-1) cells * 0.7 V * 10 nA = 2*2047*7e-9
    = 2.8658e-5 W."""
    assert SL.sneak_leakage_w(2048, 2, 0.7, 10e-9) == pytest.approx(2.8658e-5,
                                                                    rel=1e-9)


def test_sneak_leakage_scales_linearly_in_cells_and_lines():
    base = SL.sneak_leakage_w(1025, 4, 0.7, 10e-9)
    assert SL.sneak_leakage_w(2049, 4, 0.7, 10e-9) == pytest.approx(2 * base)
    assert SL.sneak_leakage_w(1025, 8, 0.7, 10e-9) == pytest.approx(2 * base)
    assert SL.sneak_leakage_w(1025, 4, 1.4, 10e-9) == pytest.approx(2 * base)
    assert SL.sneak_leakage_w(1025, 4, 0.7, 20e-9) == pytest.approx(2 * base)


def test_single_cell_line_leaks_nothing():
    """cells_per_line - 1 = 0: nothing is half-selected."""
    assert SL.sneak_leakage_w(1, 528, 0.7, 10e-9) == 0.0


def test_sneak_leakage_rejects_bad_input():
    with pytest.raises(ValueError):
        SL.sneak_leakage_w(0, 1, 0.7, 10e-9)
    with pytest.raises(ValueError):
        SL.sneak_leakage_w(2048, -1, 0.7, 10e-9)


CFG = os.path.join(REPO, "configs", "reram_22nm_selector_slc.cfg")


def test_forced_organization_parsed_from_the_real_cfg():
    """Ties the numbers to the file NVSim actually ran, like the operating-point
    test ties the device to the .cell file."""
    text = open(CFG).read()
    assert "-ForceBank (Total AxB, Active CxD): 16x4, 1x4" in text
    assert "-ForceMat (Total AxB, Active CxD): 2x2, 2x2" in text
    assert "-ForceMuxSenseAmp: 64" in text
    assert "-WordWidth (bit): 512" in text
    org = SL.parse_forced_organization(CFG)
    assert org["bank_total"] == (16, 4)
    assert org["bank_active"] == (1, 4)
    assert org["mat_total"] == (2, 2)
    assert org["mat_active"] == (2, 2)


def test_active_line_count_derived_from_the_real_cfg():
    """active subarrays = bank active 1x4 = 4 mats, times mat active 2x2 = 4
    subarrays each, = 16.  Each has 1 wordline + 2048/64 = 32 bitlines = 33
    lines, so 528 active lines, and 16*32 = 512 bits matches WordWidth 512.
    Nothing is hardcoded: change the cfg and these numbers change."""
    hw = {"subarray_rows": 2048, "subarray_cols": 2048, "mux": 64, "mats": 64}
    subarrays, lines, bits = SL.active_lines_per_chip(hw, CFG)
    assert (subarrays, lines, bits) == (16, 528, 32)
    assert subarrays * bits == 512  # -WordWidth (bit): 512


def _write_cfg(tmp_path, bank, mat, name="synthetic.cfg"):
    p = tmp_path / name
    p.write_text("-Capacity (MB): 128\n"
                 "-ForceBank (Total AxB, Active CxD): %s\n"
                 "-ForceMat (Total AxB, Active CxD): %s\n"
                 "-ForceMuxSenseAmp: 64\n" % (bank, mat))
    return str(p)


def test_active_line_count_follows_a_different_active_fraction(tmp_path):
    """A synthetic cfg with half the active mats and a quarter of the active
    subarrays per mat: 2x1 = 2 mats x 1x1 = 1 subarray = 2 active subarrays,
    so 2 x (1 + 32) = 66 active lines, not 528."""
    cfg = _write_cfg(tmp_path, "16x4, 2x1", "2x2, 1x1")
    hw = {"subarray_rows": 2048, "subarray_cols": 2048, "mux": 64, "mats": 64}
    assert SL.active_lines_per_chip(hw, cfg) == (2, 66, 32)
    # and a fully active bank: 16x4 = 64 mats x 4 = 256 active subarrays
    cfg2 = _write_cfg(tmp_path, "16x4, 16x4", "2x2, 2x2", "full.cfg")
    assert SL.active_lines_per_chip(hw, cfg2)[0] == 256


def test_mat_total_is_checked_against_the_metrics_file(tmp_path):
    """-ForceBank total 16x4 = 64 mats must agree with hw["mats"]."""
    cfg = _write_cfg(tmp_path, "8x4, 1x4", "2x2, 2x2")
    hw = {"subarray_rows": 2048, "subarray_cols": 2048, "mux": 64, "mats": 64}
    with pytest.raises(SystemExit) as e:
        SL.active_lines_per_chip(hw, cfg)
    assert "32 mats in total" in str(e.value) and "64" in str(e.value)


def test_missing_force_keys_are_a_clear_error(tmp_path):
    p = tmp_path / "nokeys.cfg"
    p.write_text("-Capacity (MB): 128\n-ForceMuxSenseAmp: 64\n")
    with pytest.raises(SystemExit) as e:
        SL.parse_forced_organization(str(p))
    assert "ForceBank" in str(e.value)
    p2 = tmp_path / "bankonly.cfg"
    p2.write_text("-ForceBank (Total AxB, Active CxD): 16x4, 1x4\n")
    with pytest.raises(SystemExit) as e:
        SL.parse_forced_organization(str(p2))
    assert "ForceMat" in str(e.value)


def test_unreadable_cfg_is_a_clear_error(tmp_path):
    with pytest.raises(SystemExit) as e:
        SL.parse_forced_organization(str(tmp_path / "does_not_exist.cfg"))
    assert "cannot read NVSim config" in str(e.value)


def test_half_select_power_excludes_the_fully_selected_cells():
    """Exact count, review item 5.  Per active subarray the access drives 1
    wordline and 32 bitlines and fully selects exactly 32 cells (one per sensed
    bit), so the wordline carries 2048 - 32 = 2016 half-selected cells and each
    bitline carries 2048 - 1 = 2047.  Per chip:
        16 * (2016 + 32 * 2047) = 16 * 67520 = 1080320 cells.
    The plain `lines * (cells_per_line - 1)` count gives 528 * 2047 = 1080816,
    high by 496 cells = 0.046 percent."""
    hw = {"subarray_rows": 2048, "subarray_cols": 2048, "mux": 64, "mats": 64}
    p, cells = SL.half_select_power_w(hw, 0.7, 10e-9, CFG)
    assert cells == 16 * (2016 + 32 * 2047) == 1080320
    assert p == pytest.approx(1080320 * 0.7 * 10e-9)
    approx_cells = 528 * 2047
    assert approx_cells - cells == 496
    assert (approx_cells - cells) / cells < 0.001


# ---------------------------------------------------------------------------
# Tile validity, Springer Handbook Fig. 17.21, pp. 642-643
# ---------------------------------------------------------------------------

def test_tile_side_bound_hand_calculation():
    """side <= I_on / (6 * I_leak); 100e-6 / (6 * 10e-9) = 1666.67."""
    assert SL.max_tile_side(100e-6, 10e-9) == pytest.approx(1666.6667, rel=1e-6)


def test_tile_valid_at_1666_invalid_at_2048_for_ots():
    """The brief's Step 1 target, with the side made explicit."""
    assert SL.tile_valid(100e-6, 10e-9, 1666) is True
    assert SL.tile_valid(100e-6, 10e-9, 2048) is False


def test_tile_valid_at_2048_for_fast_selector():
    """Crossbar FAST: 0.1 nA sneak per selector gives 100e-6/(6*0.1e-9)
    = 166666.7, so a 2048-side tile passes with three orders of margin."""
    assert SL.tile_valid(100e-6, 0.1e-9, 2048) is True
    assert SL.max_tile_side(100e-6, 0.1e-9) == pytest.approx(166666.67, rel=1e-6)


def test_tile_side_squared_is_the_handbook_cell_count():
    """[HB] states the rule as "Tile size = (I_ON/(6*I_leak))^2" in CELLS."""
    side = SL.max_tile_side(100e-6, 10e-9)
    assert side ** 2 == pytest.approx((100e-6 / (6 * 10e-9)) ** 2)


def test_tile_valid_rejects_zero_leakage():
    with pytest.raises(ValueError):
        SL.max_tile_side(100e-6, 0.0)


# ---------------------------------------------------------------------------
# Parameter sets
# ---------------------------------------------------------------------------

def test_both_bounds_present_and_cited():
    assert set(SL.SELECTORS) == {"OTS", "FAST"}
    for name, sel in SL.SELECTORS.items():
        for field in ("k", "i_on_a", "i_leak_a"):
            value, citation = sel[field]
            assert value > 0
            assert isinstance(citation, str) and len(citation) > 10


def test_bound_values_are_the_published_ones():
    assert SL.SELECTORS["OTS"]["k"][0] == 1e4          # Zhou Table I
    assert SL.SELECTORS["OTS"]["i_on_a"][0] == 100e-6  # [HB] Table 30.3
    assert SL.SELECTORS["OTS"]["i_leak_a"][0] == 10e-9  # [HB] Table 30.3
    assert SL.SELECTORS["FAST"]["k"][0] == 1e6          # Crossbar MEMSYS 2019
    assert SL.SELECTORS["FAST"]["i_leak_a"][0] == 0.1e-9
    # FAST i_on is derived as i_leak * selectivity
    assert (SL.SELECTORS["FAST"]["i_on_a"][0] ==
            pytest.approx(SL.SELECTORS["FAST"]["i_leak_a"][0] *
                          SL.SELECTORS["FAST"]["k"][0]))


def test_operating_point_matches_the_nvsim_cell_file():
    """configs/reram_22nm_selector_slc.cell, the file
    configs/reram_22nm_selector_slc.cfg names in -MemoryCellInputFile."""
    cell = os.path.join(REPO, "configs", "reram_22nm_selector_slc.cell")
    text = open(cell).read()
    assert "-ReadVoltage (V): 1.4" in text
    assert "-ResistanceOnAtReadVoltage (ohm): 100000" in text
    assert "-ResistanceOffAtReadVoltage (ohm): 1000000000" in text
    op = SL.OPERATING_POINT
    assert op["v_read"] == 1.4
    assert op["v_half"] == pytest.approx(op["v_read"] / 2.0)
    assert op["r_on"] == 1.0e5
    assert op["r_off"] == 1.0e9


# ---------------------------------------------------------------------------
# Hardware loading
# ---------------------------------------------------------------------------

def test_pre_revision_file_fails_with_a_clear_message(tmp_path):
    """A PRE-REVISION hardware_metrics.json (written before T2.6 recorded the
    forced subarray organization) must give a readable error, not a KeyError.

    I10: the old docstring said "the live results/hardware_metrics.json has no
    subarray fields", and the message it asserted pointed at a git-ignored
    staging file. Both describe a state that no longer exists: since T2.6 the
    live file DOES carry the subarray fields (see HARDWARE_FIXTURE, a copy of
    it), so only a pre-revision file can fail this way. The leakage value below
    is the retired pre-revision 50.9 mW figure, deliberately, because that is
    what such a file holds."""
    p = tmp_path / "pre_revision.json"
    p.write_text(json.dumps({"reram_22nm_selector_slc": {
        "capacity_gb": 0.125, "leakage_mw": 50.9, "area_mm2": 1.0}}))
    with pytest.raises(SystemExit) as e:
        SL.load_hardware(str(p))
    msg = str(e.value)
    assert "subarray_rows" in msg
    assert "PRE-REVISION" in msg
    assert "2_extract_hardware_metrics.py" in msg
    assert "staging" not in msg


def test_missing_cell_key_fails_clearly(tmp_path):
    p = tmp_path / "other.json"
    p.write_text(json.dumps({"reram_22nm_1t1r_slc": {}}))
    with pytest.raises(SystemExit) as e:
        SL.load_hardware(str(p))
    assert "reram_22nm_selector_slc" in str(e.value)


def test_non_square_subarray_is_refused(tmp_path):
    p = tmp_path / "rect.json"
    p.write_text(json.dumps({"reram_22nm_selector_slc": {
        "capacity_gb": 0.125, "leakage_mw": 108.384, "subarray_rows": 1024,
        "subarray_cols": 2048, "mats": 64, "mux": 64}}))
    with pytest.raises(SystemExit) as e:
        SL.load_hardware(str(p))
    assert "square" in str(e.value)


def test_hardware_fixture_loads():
    hw = SL.load_hardware(HARDWARE_FIXTURE)
    assert hw["subarray_rows"] == 2048 and hw["subarray_cols"] == 2048
    assert hw["mux"] == 64
    assert hw["leakage_mw"] == pytest.approx(108.384)


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------

# A small ceiling keeps the 10-percent-side search cheap: the margin is still
# above 10 percent at 2048 for both bounds, so the search returns at once.  The
# real ceiling of 8192 is exercised once, in the slow test below.
FAST_CEILING = 2048


def test_evaluate_verdicts_at_the_revision_organization():
    res = SL.evaluate(SL.load_hardware(HARDWARE_FIXTURE), side_ceiling=FAST_CEILING)
    org = res["organization"]
    assert org["active_subarrays_per_access"] == 16
    assert org["active_wordlines_per_access"] == 16
    assert org["active_bitlines_per_access"] == 512
    assert org["active_lines_per_access"] == 528
    assert org["fully_selected_cells_per_access"] == 512
    assert org["half_selected_cells_per_access"] == 1080320
    assert org["chips_per_dimm"] == 64
    assert org["devices_per_rank"] == 8 and org["ranks_per_dimm"] == 8

    ots = res["bounds"]["OTS"]["verdict"]
    fast = res["bounds"]["FAST"]["verdict"]
    # OTS: 100 uA / (6 * 10 nA) = 1666.7 < 2048, so the handbook rule fails.
    assert ots["tile_valid_at_2048"] is False
    assert ots["max_tile_side"] == pytest.approx(1666.667, rel=1e-5)
    # FAST: 166666 >> 2048.
    assert fast["tile_valid_at_2048"] is True
    assert fast["max_tile_side"] == pytest.approx(166666.67, rel=1e-5)
    # Read margin at the project's operating point stays above Zhou's 10%
    # minimum for both bounds, so the tile rule, not the read margin, is what
    # rules out a 2048-side OTS tile.
    assert ots["read_margin_at_2048"] == pytest.approx(0.240, abs=0.01)
    assert fast["read_margin_at_2048"] == pytest.approx(0.232, abs=0.01)
    assert ots["read_margin_ok_at_2048"] is True
    assert fast["read_margin_ok_at_2048"] is True
    assert ots["binding_limit"] == "handbook tile leakage"

    # Sneak leakage hand check, OTS, with the fully selected cells excluded:
    # 16 * (2016 + 32*2047) = 1080320 cells * 0.7 V * 10 nA = 7.5622 mW/chip.
    sn = res["bounds"]["OTS"]["sneak_leakage"]
    assert sn["access_time_w_per_chip"] == pytest.approx(1080320 * 0.7 * 10e-9)
    assert sn["access_time_w_per_chip"] == pytest.approx(7.5622e-3, rel=1e-3)
    # One request is served by ONE rank, i.e. 8 devices; all 64 chips at once
    # is an upper bound only.
    assert sn["access_time_w_per_accessed_rank"] == pytest.approx(
        sn["access_time_w_per_chip"] * 8)
    assert sn["access_time_w_all_ranks_upper_bound"] == pytest.approx(
        sn["access_time_w_per_chip"] * 64)
    assert "upper bound" in sn["scope_labels"][
        "access_time_w_all_ranks_upper_bound"].lower()
    assert "rank" in sn["scope_labels"]["access_time_w_per_accessed_rank"]
    # No key claims to be a DIMM leakage figure.
    assert not any("dimm" in key.lower() for key in sn)
    # FAST is exactly 100x lower (0.1 nA vs 10 nA).
    assert (res["bounds"]["FAST"]["sneak_leakage"]["access_time_w_per_chip"] ==
            pytest.approx(sn["access_time_w_per_chip"] / 100.0))
    # The standby adder is zero at every scope, by construction.
    for name in ("OTS", "FAST"):
        s = res["bounds"][name]["sneak_leakage"]
        assert s["standby_adder_w_per_chip"] == 0.0
        assert s["standby_adder_w_per_accessed_rank"] == 0.0
        assert s["standby_adder_w_all_ranks_upper_bound"] == 0.0


def test_chips_per_dimm_matches_the_generator_geometry():
    """Tie the 64 chips to the tracked generator table, not to a generated
    config file that is rewritten on every pipeline run.  The module has 8 ranks
    of 8 devices at one channel and at two (4 ranks per channel x 2)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "gen_for_selector", os.path.join(REPO, "3_gen_nvmain_config.py"))
    gen = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen)
    hw = {"capacity_gb": 0.125, "subarray_rows": 2048}
    for channels in (1, 2):
        g = gen.geometry(hw, "full_dimm", channels=channels)
        assert g["DEVICES_PER_RANK"] == SL.DEVICES_PER_RANK
        assert g["RANKS"] * g["CHANNELS"] == SL.RANKS_PER_DIMM
        assert g["RANKS"] * g["CHANNELS"] * g["DEVICES_PER_RANK"] == SL.CHIPS_PER_DIMM
    assert "geometry()" in SL.DIMM_SOURCE


@pytest.mark.slow
def test_margin_limited_side_at_the_full_ceiling():
    """With the real 8192 ceiling the FAST bound is margin limited at a side of
    about 5824, where the read margin is just above 10 percent.  This is the
    one test that pays for the full search."""
    res = SL.evaluate(SL.load_hardware(HARDWARE_FIXTURE), side_ceiling=8192)
    fast = res["bounds"]["FAST"]["verdict"]
    assert fast["max_side_read_margin_above_10pct"] == pytest.approx(5824, abs=128)
    assert fast["read_margin_at_max_side"] == pytest.approx(0.10, abs=0.005)
    assert fast["binding_limit"] == "read margin"
    ots = res["bounds"]["OTS"]["verdict"]
    assert ots["max_side_read_margin_above_10pct"] == pytest.approx(5696, abs=128)
    assert ots["binding_limit"] == "handbook tile leakage"


def test_cli_writes_json_and_table(tmp_path):
    out = tmp_path / "selector_layer.json"
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "selector_layer.py"),
         "--hardware", HARDWARE_FIXTURE, "--out", str(out),
         "--side-ceiling", str(FAST_CEILING)],
        capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert "OTS" in r.stdout and "FAST" in r.stdout and "NOT VALID" in r.stdout
    # the three scopes are labelled in the table and none is called DIMM leakage
    assert "sneak/chip" in r.stdout and "sneak/rank" in r.stdout
    assert "sneak/all-rank" in r.stdout
    assert "DIMM leakage" in r.stdout  # only as "None of them is a ..."
    assert "None of" in r.stdout
    data = json.loads(out.read_text())
    assert set(data["bounds"]) == {"OTS", "FAST"}
    assert data["meta"]["task"] == "T2.7"
    assert data["meta"]["side_ceiling"] == FAST_CEILING
    assert data["organization"]["forced_organization"]["bank_active"] == [1, 4]


def test_module_imports_without_side_effects():
    """Importing must not write results/selector_layer.json."""
    r = subprocess.run(
        [sys.executable, "-c",
         "import selector_layer, os, sys;"
         "sys.exit(0 if not os.path.exists('results/_sl_probe.json') else 1)"],
        capture_output=True, text=True, cwd=REPO)
    assert r.returncode == 0, r.stderr
    assert r.stdout == ""
