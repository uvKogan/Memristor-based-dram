"""Tests for tools/aggregate_wear.py.

FIXTURE_A: two subarrays (channel0.rank0.bank0 and channel0.rank0.bank1),
one channel, with wear stats, mem_writes, a capacity line, Start-Gap
decoder stats and wearTopLocations -- hand-computed expected values below.

  subarray0: wearLocations=10, wearTotalWrites=100, wearMaxWrites=50,
             wearTopLocations {100: 50, 200: 20, 300: 10}
  subarray1: wearLocations=5,  wearTotalWrites=40,  wearMaxWrites=20,
             wearTopLocations {150: 20, 250: 15}

  touched_locations = 10 + 5 = 15
  total_writes       = 100 + 40 = 140
  max_writes          = max(50, 20) = 50
  mean_writes_touched = 140 / 15 = 9.3333...
  hotspot_vs_touched_mean = 50 / (140/15) = 750/140 = 5.357142857142857
    (this is process_metrics.extract_dimm_wear_stats' own SYNTHETIC_STATS
    example, reused here so the two tools' numbers cannot silently diverge)

  mem_writes (channel0.FRFCFS.mem_writes) = 140  -> matches total_writes.

  capacity: "defaultMemory.channel0.FRFCFS capacity is 8192 MB." -> 8192 MiB
    -> capacity_lines = 8192 * 2**20 // 64 = 134,217,728 (== 8 GiB / 64 B).
  hotspot_vs_whole_capacity_mean = 50 / (140/134217728)
                                  = 50 * 134217728 / 140 = 47,935,617.142857...

  top16 merge (5 total entries across both subarrays, sorted by writes desc,
  ties by address desc -- SubArray.cpp's std::greater<pair<count,addr>>):
    50@100, 20@200, 20@150, 15@250, 10@300
"""

import json

import pytest

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "tools"))
import aggregate_wear as aw  # noqa: E402


FIXTURE_A = """\
NVMain: GlobalEventQueue: Added a memory subsystem running at 800MHz. My frequency is 3000MHz.
defaultMemory.channel0.FRFCFS capacity is 8192 MB.
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearLocations 10
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearTotalWrites 100
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearMaxWrites 50
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearMeanWrites 10
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearHotSpotFactor 5
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearTopLocations {100: 50, 200: 20, 300: 10}
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearLocations 5
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearTotalWrites 40
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearMaxWrites 20
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearMeanWrites 8
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearHotSpotFactor 2.5
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearTopLocations {150: 20, 250: 15}
i0.defaultMemory.channel0.FRFCFS.mem_writes 140
i0.defaultMemory.channel0.startGapMoves 1999
i0.defaultMemory.channel0.FRFCFS.startGapMoves 1999
i0.defaultMemory.channel0.startGapWrites 19999
i0.defaultMemory.channel0.FRFCFS.startGapWrites 19999
i0.defaultMemory.channel0.startGapOutOfRegion 87830
i0.defaultMemory.channel0.FRFCFS.startGapOutOfRegion 87830
i0.defaultMemory.channel0.startGapBoundaryAlias 0
i0.defaultMemory.channel0.FRFCFS.startGapBoundaryAlias 0
Exiting at cycle 2000000 because simCycles 2000000 reached.
"""


def test_aggregate_wear_basic_fixture():
    result = aw.aggregate_wear(FIXTURE_A)
    assert result["touched_locations"] == 15
    assert result["total_writes"] == 140
    assert result["max_writes"] == pytest.approx(50)
    assert result["mean_writes_touched"] == pytest.approx(140 / 15)
    assert result["hotspot_factor_vs_touched_mean"] == pytest.approx(750.0 / 140.0)
    assert result["mem_writes_total"] == 140
    assert result["wear_mem_writes_match"] is True
    assert result["has_wear_stats"] is True
    assert result["capacity_lines"] == 134_217_728
    assert result["hotspot_factor_vs_whole_capacity_mean"] == pytest.approx(
        50 * 134_217_728 / 140)
    assert result["wear_granularity"].startswith("RowModel")


def test_aggregate_wear_startgap_stats_present_no_warning():
    result = aw.aggregate_wear(FIXTURE_A)
    sg = result["startgap"]
    assert sg["startGapMoves"] == 1999
    assert sg["startGapWrites"] == 19999
    assert sg["startGapOutOfRegion"] == 87830
    assert sg["startGapBoundaryAlias"] == 0
    assert not any("boundary" in w.lower() for w in result["startgap_warnings"])


def test_aggregate_wear_startgap_boundary_alias_warns():
    content = FIXTURE_A.replace("startGapBoundaryAlias 0", "startGapBoundaryAlias 14")
    result = aw.aggregate_wear(content)
    assert result["startgap"]["startGapBoundaryAlias"] == 14
    assert any("boundary" in w.lower() and "14" in w
               for w in result["startgap_warnings"])


def test_aggregate_wear_startgap_absent():
    content = "\n".join(l for l in FIXTURE_A.splitlines() if "startGap" not in l)
    result = aw.aggregate_wear(content)
    assert result["startgap"] is None
    assert result["startgap_warnings"] == []


def test_aggregate_wear_top16_merge_order_and_tiebreak():
    result = aw.aggregate_wear(FIXTURE_A)
    top = result["top16"]
    got = [(e["writes"], e["address"]) for e in top]
    assert got == [(50, 100), (20, 200), (20, 150), (15, 250), (10, 300)]


def test_aggregate_wear_hard_fails_on_mem_writes_mismatch():
    content = FIXTURE_A.replace(
        "i0.defaultMemory.channel0.FRFCFS.mem_writes 140",
        "i0.defaultMemory.channel0.FRFCFS.mem_writes 999")
    with pytest.raises(aw.WearMismatchError):
        aw.aggregate_wear(content)


def test_aggregate_wear_nullmodel_all_zero_no_hard_fail_even_if_mem_writes_nonzero():
    # A NullModel (DDR5/PCM) run: every wear stat is 0, but mem_writes can
    # still be nonzero (real completed writes, just not wear-tracked). This
    # must NOT hard-fail -- the mismatch check only applies "for a run that
    # has wear stats" (sum(wearLocations) > 0).
    content = (
        "i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearLocations 0\n"
        "i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearTotalWrites 0\n"
        "i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearMaxWrites 0\n"
        "i0.defaultMemory.channel0.FRFCFS-WQF.mem_writes 500\n"
    )
    result = aw.aggregate_wear(content)
    assert result["has_wear_stats"] is False
    assert result["wear_mem_writes_match"] is None
    assert result["max_writes"] is None
    assert result["mean_writes_touched"] is None


def test_aggregate_wear_capacity_explicit_overrides_inference():
    result = aw.aggregate_wear(FIXTURE_A, capacity_lines=1000)
    assert result["capacity_lines"] == 1000
    assert "explicitly" in result["capacity_note"]
    assert result["hotspot_factor_vs_whole_capacity_mean"] == pytest.approx(
        50 / (140 / 1000))


def test_aggregate_wear_no_capacity_line_leaves_it_blank():
    content = FIXTURE_A.replace(
        "defaultMemory.channel0.FRFCFS capacity is 8192 MB.\n", "")
    result = aw.aggregate_wear(content)
    assert result["capacity_lines"] is None
    assert result["hotspot_factor_vs_whole_capacity_mean"] is None
    assert "no 'capacity is" in result["capacity_note"]


def test_aggregate_wear_capacity_summed_across_two_channels():
    content = FIXTURE_A + (
        "defaultMemory.channel1.FRFCFS capacity is 8192 MB.\n"
    )
    result = aw.aggregate_wear(content)
    assert result["capacity_lines"] == 2 * 134_217_728


def test_infer_wear_granularity_wordmodel_when_locations_exceed_forced_rows():
    assert aw.infer_wear_granularity([10, 5]).startswith("RowModel")
    assert aw.infer_wear_granularity([10, 5000]).startswith("WordModel")
    assert aw.infer_wear_granularity([]).startswith("unknown")
    assert aw.infer_wear_granularity([0, 0]).startswith("unknown")


def test_format_report_runs_without_error():
    result = aw.aggregate_wear(FIXTURE_A)
    text = aw.format_report(result, source_path="fixture_a.out")
    assert "touched locations: 15" in text
    assert "DIMM-wide wear aggregation" in text


def test_cli_main_writes_json_and_prints_report(tmp_path, capsys):
    stats_path = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out"
    stats_path.write_text(FIXTURE_A)
    out_dir = tmp_path / "results"

    rc = aw.main([str(stats_path), "--out-dir", str(out_dir)])
    assert rc == 0

    captured = capsys.readouterr()
    assert "touched locations: 15" in captured.out
    assert "wrote" in captured.out

    json_path = out_dir / "wear_1T1R_SLC_lbm_spec2017.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert data["touched_locations"] == 15
    assert data["total_writes"] == 140


def test_cli_main_hard_fail_returns_nonzero(tmp_path, capsys):
    content = FIXTURE_A.replace(
        "i0.defaultMemory.channel0.FRFCFS.mem_writes 140",
        "i0.defaultMemory.channel0.FRFCFS.mem_writes 999")
    stats_path = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out"
    stats_path.write_text(content)

    rc = aw.main([str(stats_path), "--out-dir", str(tmp_path / "results")])
    assert rc == 1
    captured = capsys.readouterr()
    assert "HARD FAIL" in captured.err
