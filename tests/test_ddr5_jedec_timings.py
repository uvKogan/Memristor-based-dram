"""F4: pin the DDR5 baseline's JEDEC DDR5-4800 timings in both tracked configs.

Before F4 the two DDR5 configs carried DDR5-4800 values for tCAS / tRCD / tRP /
tRAS / tRFC / tREFW but NVMain's DDR3-1333 template cycle counts for the write
path (tCWD, tWTR, tWR, tRTP) and the power-down path (tPD, tXP, tRDPDEN,
tWRPDEN, tWRAPDEN), while running at CLK 2400.  That made DDR5 writes about 5x
too cheap in write latency and 7x too cheap in write recovery and flattered the
baseline.  These tests pin the corrected values so the regression cannot come
back silently, and they re-derive each one from the JEDEC formula rather than
just comparing two literals.

Sources (recorded in full in each config's own header comment block):

* JESD79-5 (JEDEC Standard No. 79-5, DDR5 SDRAM, July 2020)
  - Table 471, standard p.354, "DDR5-4800 Speed Bins and Operations":
    DDR5-4800B, CWL = CL - 2 = 38 nCK at CL 40 / tCK 0.416 ns.
  - Table 521, standard p.454, "Timing Parameters for DDR5-4400 to DDR5-5200",
    DDR5-4800 column: tWTR_S = max(4 nCK, 2.5 ns), tWTR_L = max(16 nCK, 10 ns),
    tRTP = max(12 nCK, 7.5 ns), tWR = 29.952 ns (the 30.000 ns nominal scaled
    and rounded down to 1 ps, i.e. exactly 72 x 0.416 ns), tCCD_S = 8 nCK,
    tCCD_L = max(8 nCK, 5 ns), tRRD_S = 8 nCK, tRRD_L = max(8 nCK, 5 ns),
    tFAW_1K = Max(32 nCK, 13.312 ns), tFAW_2K = Max(40 nCK, 16.640 ns).
  - Table 272, standard p.144, "Power Down Timing Parameters":
    tPD = max(7.5 ns, 8 nCK), tXP = max(7.5 ns, 8 nCK),
    tRDPDEN = RL + RBL/2 + 1, tWRPDEN = WL + WBL/2 + ceil(tWR/tCK) + 1,
    tWRAPDEN = WL + WBL/2 + WR + 1.
  - Table 271, standard p.143: DDR5 power-down is DLL On / Fast exit for both
    active and precharged, so there is no DLL-off slow-exit counterpart and
    tXPDLL is deliberately left at the template value.
* Micron, "16Gb DDR5 SDRAM Addendum: MT60B4G4, MT60B2G8, MT60B1G16, Die
  Revision A", CCM005-0005-1684161373-30, Rev. D 02/2023 (the book's reference
  [29]), Table 1: speed grade -48B, speed bin 4800B, target CL-nRCD-nRP
  40-39-39, tCK 0.416 ns at CL 40.
"""

import math
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
CONFIG_DIR = REPO / "configs"
LIVE_CONFIG_DIR = REPO / "simulators" / "nvmain" / "Config"

SUBCHANNEL = "DDR5_4800_DRAM_subchannel.config"
CONFIG_64B = "DDR5_4800_DRAM_64B.config"

# CLK 2400 in both configs.  tCK = 1 / 2400 MHz.  JESD79-5 Table 521 gives
# tCK(avg) min 0.416 ns for DDR5-4800; these agree to 0.7 ps.
TCK_NS = 1000.0 / 2400.0


def _keys(name):
    """Parse a config into {key: first token after the key}, comments dropped."""
    out = {}
    for line in (CONFIG_DIR / name).read_text().splitlines():
        line = line.split(";", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 2:
            out.setdefault(parts[0], parts[1])
    return out


@pytest.fixture(scope="module")
def sub():
    return _keys(SUBCHANNEL)


@pytest.fixture(scope="module")
def cfg64():
    return _keys(CONFIG_64B)


# --- the write path -------------------------------------------------------


def test_tcwd_is_jedec_cwl_38(sub, cfg64):
    """JESD79-5 Table 471: DDR5-4800B CWL = CL - 2.  CL is tCAS 40 here."""
    for cfg in (sub, cfg64):
        assert int(cfg["tCAS"]) == 40
        assert int(cfg["tCWD"]) == int(cfg["tCAS"]) - 2 == 38
        # 38 nCK = 15.83 ns, not the 2.9 ns the DDR3 template's 7 gave.
        assert int(cfg["tCWD"]) * TCK_NS == pytest.approx(15.833, abs=0.001)


def test_twr_is_jedec_30ns(sub, cfg64):
    """JESD79-5 Table 521: tWR = 30 ns nominal (29.952 ns = 72 x 0.416)."""
    expected = math.ceil(30.0 / TCK_NS)
    assert expected == 72
    for cfg in (sub, cfg64):
        assert int(cfg["tWR"]) == 72


def test_trtp_is_max_12nck_7p5ns(sub, cfg64):
    """JESD79-5 Table 521: tRTP = max(12 nCK, 7.5 ns)."""
    expected = max(12, math.ceil(7.5 / TCK_NS))
    assert expected == 18
    for cfg in (sub, cfg64):
        assert int(cfg["tRTP"]) == 18


def test_tccd_is_jedec_tccd_s_on_the_primary_baseline(sub, cfg64):
    """F4b. JESD79-5 Table 521: tCCD_S = 8 nCK for a different bank group (the
    same 8 nCK for BL16, BC8 fixed and BC8 on-the-fly), tCCD_L =
    max(8 nCK, 5 ns) = 12 nCK for the same bank group.  NVMain has one
    rank-wide value and no bank groups, so tCCD_S is the DDR5-friendly pick.

    The 64B cross-check config keeps tCCD 4, BELOW the JEDEC floor, on purpose:
    that is the T2.4 legacy channel shape it exists to reproduce, not a JEDEC
    claim.  Pinned here so the divergence stays deliberate and visible.
    """
    expected_s, expected_l = 8, max(8, math.ceil(5.0 / TCK_NS))
    assert (expected_s, expected_l) == (8, 12)
    assert int(sub["tCCD"]) == expected_s
    assert int(cfg64["tCCD"]) == 4 < expected_s


def test_trrdr_is_jedec_trrd_s(sub, cfg64):
    """F4b. JESD79-5 Table 521: tRRD_S = 8 nCK (different bank group),
    tRRD_L = max(8 nCK, 5 ns) = 12 nCK (same bank group).  tRRDR is NVMain's
    only activate-to-activate constraint (StandardRank.cpp:283 on every
    ACTIVATE, :602 on every REFRESH), applied rank-wide with no bank groups,
    so tRRD_S is the deliberate DDR5-friendly mapping, as for tWTR."""
    expected_s, expected_l = 8, max(8, math.ceil(5.0 / TCK_NS))
    assert (expected_s, expected_l) == (8, 12)
    for cfg in (sub, cfg64):
        assert int(cfg["tRRDR"]) == 8


def test_trrdw_is_dead_but_consistent(sub, cfg64):
    """F4b. tRRDW is parsed (Params.cpp:342) and stored (Params.h:153) but read
    by no timing code in NVMain; tRRDR serves both directions.  It is set to
    tRRD_S only so the config carries no DDR3-1333 leftovers."""
    for cfg in (sub, cfg64):
        assert int(cfg["tRRDW"]) == int(cfg["tRRDR"]) == 8


def test_raw_and_traw_are_jedec_four_activate_window(sub, cfg64):
    """F4b. RAW is the NUMBER of activates in NVMain's rolling window
    (StandardRank.cpp:113-120) and tRAW is its width, with the gate at :270
    admitting an ACTIVATE only when lastActivate[(RAWindex+1) % RAW] + tRAW
    <= now.  That is exactly JEDEC tFAW with a four-activate window.
    JESD79-5 Table 521: tFAW_1K = Max(32 nCK, 13.312 ns) for the 1 KB page of a
    x8 part (Micron [29] Table 1); tFAW_2K = Max(40 nCK, 16.640 ns) = 40 is the
    x16 value and is NOT what this x8 config uses."""
    faw_1k = max(32, math.ceil(13.312 / TCK_NS))
    faw_2k = max(40, math.ceil(16.640 / TCK_NS))
    assert (faw_1k, faw_2k) == (32, 40)
    for cfg in (sub, cfg64):
        assert int(cfg["RAW"]) == 4
        assert int(cfg["DeviceWidth"]) == 8
        assert int(cfg["tRAW"]) == faw_1k == 32


def test_twtr_is_jedec_twtr_s(sub, cfg64):
    """JESD79-5 Table 521: tWTR_S = max(4 nCK, 2.5 ns) = 6.

    NVMain has a single rank-wide tWTR and no bank groups.  tWTR_S is the
    deliberate conservative mapping (the common case, and the one that does
    not make the baseline slower than a real part); tWTR_L = max(16 nCK,
    10 ns) = 24 is the pessimistic bound and is NOT what this config uses.
    """
    expected_s = max(4, math.ceil(2.5 / TCK_NS))
    expected_l = max(16, math.ceil(10.0 / TCK_NS))
    assert (expected_s, expected_l) == (6, 24)
    for cfg in (sub, cfg64):
        assert int(cfg["tWTR"]) == 6


# --- the power-down path --------------------------------------------------


def test_tpd_and_txp_are_max_7p5ns_8nck(sub, cfg64):
    """JESD79-5 Table 272: tPD = tXP = max(7.5 ns, 8 nCK)."""
    expected = max(8, math.ceil(7.5 / TCK_NS))
    assert expected == 18
    for cfg in (sub, cfg64):
        assert int(cfg["tPD"]) == 18
        assert int(cfg["tXP"]) == 18


def test_trdpden_follows_jedec_formula(sub, cfg64):
    """JESD79-5 Table 272: tRDPDEN = RL + RBL/2 + 1, RL = tAL + tCAS,
    RBL/2 = tBURST (BL16 -> 8 nCK on the subchannel, BL8 -> 4 nCK on the 64B
    cross-check config)."""
    for cfg, want in ((sub, 49), (cfg64, 45)):
        rl = int(cfg["tAL"]) + int(cfg["tCAS"])
        assert int(cfg["tRDPDEN"]) == rl + int(cfg["tBURST"]) + 1 == want


def test_twrpden_and_twrapden_follow_jedec_formula(sub, cfg64):
    """JESD79-5 Table 272: tWRPDEN = WL + WBL/2 + ceil(tWR/tCK) + 1 and
    tWRAPDEN = WL + WBL/2 + WR + 1, with WR the MR6-programmed write recovery
    in nCK, which is the same 72 cycles.  tWRAPDEN is inert in NVMain (parsed
    at Params.cpp:356, read by no timing code) but is kept consistent."""
    for cfg, want in ((sub, 119), (cfg64, 115)):
        wl = int(cfg["tCWD"])
        expected = wl + int(cfg["tBURST"]) + int(cfg["tWR"]) + 1
        assert int(cfg["tWRPDEN"]) == expected == want
        assert int(cfg["tWRAPDEN"]) == expected == want


# --- what must NOT have moved --------------------------------------------


def test_already_jedec_values_unchanged(sub, cfg64):
    """The 2026-08 and finding-#7 corrections stay exactly as they were."""
    for cfg in (sub, cfg64):
        assert int(cfg["CLK"]) == 2400
        assert int(cfg["tCAS"]) == 40
        assert int(cfg["tRCD"]) == 39
        assert int(cfg["tRP"]) == 39
        assert int(cfg["tRAS"]) == 77
        assert int(cfg["tRFC"]) == 708
        assert int(cfg["tREFW"]) == 76800000
        assert int(cfg["tAL"]) == 0
        assert float(cfg["Voltage"]) == 1.1


def test_unsourceable_powerdown_keys_left_alone(sub, cfg64):
    """tXPDLL has no DDR5 counterpart (JESD79-5 Table 271: no DLL-off slow
    exit) and is unreachable under PowerDownMode FASTEXIT; tXS/tXSDLL are
    self-refresh exit, which NVMain never enters.  F4 deliberately did not
    invent values for them."""
    for cfg in (sub, cfg64):
        assert cfg["PowerDownMode"] == "FASTEXIT"
        assert int(cfg["tXPDLL"]) == 17
        assert int(cfg["tXS"]) == 5
        assert int(cfg["tXSDLL"]) == 512


def test_nvmain_only_keys_left_alone(sub, cfg64):
    """F4b sweep. tCMD is only a one-cycle start-up offset
    (StandardRank.cpp:177-180); tRTRS is a bus-turnaround term JEDEC does not
    define; tOST is used only in StandardRank::Notify, which OffChipBus sends
    to OTHER ranks only, so it never binds with RANKS 1.  None has a DDR5
    counterpart and none was invented."""
    for cfg in (sub, cfg64):
        assert int(cfg["tCMD"]) == 1
        assert int(cfg["tRTRS"]) == 1
        assert int(cfg["tOST"]) == 1
    assert int(sub["RANKS"]) == 1        # tOST cannot bind in the primary
    assert int(cfg64["RANKS"]) == 2      # it can in the cross-check config


def test_jedec_provenance_recorded_in_both_configs():
    """Concern 5 / round-2 item 5: each config must state that its JEDEC
    numbers were transcribed from a third-party mirror of JESD79-5 and should
    be re-verified against an official copy."""
    for name in (SUBCHANNEL, CONFIG_64B):
        raw = (CONFIG_DIR / name).read_text()
        # Un-wrap the comment block so a phrase split across two ";" lines
        # still matches.
        flat = " ".join(
            line.lstrip().lstrip(";").strip() for line in raw.splitlines()
        )
        assert "JESD79-5" in flat
        assert "raw.githubusercontent.com/RAMGuide" in flat
        assert "retrieved 2026-09-21" in flat
        assert "re-verified against an official copy" in flat


def test_only_burst_dependent_powerdown_keys_differ_between_the_two_configs(sub, cfg64):
    """Every F4 key is identical in the two configs except the three whose
    JEDEC formula depends on the burst length."""
    same = ["tCWD", "tWTR", "tWR", "tRTP", "tPD", "tXP",
            "tRRDR", "tRRDW", "RAW", "tRAW"]
    for k in same:
        assert sub[k] == cfg64[k], k
    for k in ["tRDPDEN", "tWRPDEN", "tWRAPDEN"]:
        assert sub[k] != cfg64[k], k
    assert int(sub["tBURST"]) == 8 and int(cfg64["tBURST"]) == 4


def test_live_nvmain_copies_carry_the_same_values():
    """tools/check_live_configs.py enforces byte identity; this is the
    cheap direct assertion that the corrected values really reached the copy
    NVMain reads at runtime."""
    for name in (SUBCHANNEL, CONFIG_64B):
        tracked = (CONFIG_DIR / name).read_text()
        live = (LIVE_CONFIG_DIR / name).read_text()
        assert tracked == live, name
