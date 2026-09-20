"""T2.5: delivered bandwidth, end-to-end latency and wear statistics.

Synthetic two-channel stats text (models a 1T1R_SLC config, CLK 800MHz) with
known mem_reads/mem_writes, averageEndToEndLatency, measuredEndToEndLatencies,
an "Exiting at cycle" elapsed-time line, and two subarrays' wear counters.
Hand-computed expected values (see comments below) are asserted against the
extractor functions directly, then again end-to-end through parse_raw_stats()
and process_metrics().
"""

import math
import sys

import pytest

import process_metrics as pm


# --- Synthetic two-channel stats text -------------------------------------
# Channel 0: mem_reads=40, mem_writes=10 -> 50 completed
#            averageEndToEndLatency=1000.0 cycles, measuredEndToEndLatencies=100
# Channel 1: mem_reads=60, mem_writes=40 -> 100 completed
#            averageEndToEndLatency=2000.0 cycles, measuredEndToEndLatencies=300
#
# Request-weighted mean E2E latency (CLK-cycle domain):
#   (1000*100 + 2000*300) / (100+300) = 700000/400 = 1750.0 cycles
#   -> ns at CLK=800MHz: 1750 * 1000/800 = 2187.5 ns
#
# Completed_Requests = 50 + 100 = 150
#
# "Exiting at cycle 3000000" is in the GLOBAL/CPUFreq (3000MHz) domain:
#   elapsed_ns = 3000000 * 1000/3000 = 1,000,000 ns = 1e-3 s
# Delivered_BW_MBps = (150*64 bytes) / 1e-3 s / 1e6 = 9600/0.001/1e6 = 9.6 MB/s
#
# Wear (two subarrays):
#   subarray0: wearLocations=10, wearTotalWrites=100, wearMaxWrites=50
#   subarray1: wearLocations=5,  wearTotalWrites=40,  wearMaxWrites=20
#   DIMM-wide: sum_locations=15, sum_total_writes=140, dimm_max=50
#   mean-per-touched-location = 140/15 = 9.333...
#   Wear_HotSpot_Factor = 50 / (140/15) = 750/140 = 5.357142857142857
SYNTHETIC_STATS = """\
NVMain: GlobalEventQueue: Added a memory subsystem running at 800MHz. My frequency is 3000MHz.
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.totalPower 0.5W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearLocations 10
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearTotalWrites 100
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearMaxWrites 50
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearMeanWrites 10
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearHotSpotFactor 5
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearLocations 5
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearTotalWrites 40
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearMaxWrites 20
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearMeanWrites 8
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wearHotSpotFactor 2.5
i0.defaultMemory.channel0.FRFCFS.mem_reads 40
i0.defaultMemory.channel0.FRFCFS.mem_writes 10
i0.defaultMemory.channel0.FRFCFS.averageTotalLatency 500.0
i0.defaultMemory.channel0.FRFCFS.averageEndToEndLatency 1000.0
i0.defaultMemory.channel0.FRFCFS.measuredEndToEndLatencies 100
i0.defaultMemory.channel0.FRFCFS.unstampedRequests 0
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.bank0.totalPower 0.4W
i0.defaultMemory.channel1.FRFCFS.mem_reads 60
i0.defaultMemory.channel1.FRFCFS.mem_writes 40
i0.defaultMemory.channel1.FRFCFS.averageTotalLatency 600.0
i0.defaultMemory.channel1.FRFCFS.averageEndToEndLatency 2000.0
i0.defaultMemory.channel1.FRFCFS.measuredEndToEndLatencies 300
i0.defaultMemory.channel1.FRFCFS.unstampedRequests 0
Exiting at cycle 3000000 because simCycles 3000000 reached.
"""

# A NullModel-style signature (DDR5/PCM, or any all-read run): every subarray
# reports 0 for wearLocations/wearTotalWrites/wearMaxWrites.
NULLMODEL_WEAR_STATS = """\
i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearLocations 0
i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearTotalWrites 0
i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearMaxWrites 0
i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearMeanWrites 0
i0.defaultMemory.channel0.FRFCFS-WQF.channel0.rank0.bank0.subarray0.wearHotSpotFactor 0
"""


def test_extract_end_to_end_latency_ns_is_request_weighted():
    # T2.5 fix round 1: extract_end_to_end_latency_ns takes clk_mhz directly
    # now (not a technology string) -- 800 matches SYNTHETIC_STATS' own
    # "running at 800MHz" diagnostic line, resolved via resolve_clocks_mhz
    # in the tests below; this test exercises the pure conversion in isolation.
    result = pm.extract_end_to_end_latency_ns(SYNTHETIC_STATS, 800)
    assert result == pytest.approx(2187.5)


def test_extract_completed_requests_and_bandwidth():
    completed, bw_mbps = pm.extract_completed_requests_and_bandwidth(SYNTHETIC_STATS)
    assert completed == 150
    assert bw_mbps == pytest.approx(9.6)


def test_extract_dimm_wear_stats():
    wear_max, wear_hotspot = pm.extract_dimm_wear_stats(SYNTHETIC_STATS)
    assert wear_max == pytest.approx(50)
    assert wear_hotspot == pytest.approx(750.0 / 140.0)


def test_extract_dimm_wear_stats_all_zero_is_blank_not_zero():
    # NullModel (DDR5/PCM) or an all-read ReRAM trace: every subarray reports
    # 0 -- must be None (blank in the CSV), never a zero-filled 0.
    wear_max, wear_hotspot = pm.extract_dimm_wear_stats(NULLMODEL_WEAR_STATS)
    assert wear_max is None
    assert wear_hotspot is None


def test_extract_dimm_wear_stats_missing_lines_is_blank():
    wear_max, wear_hotspot = pm.extract_dimm_wear_stats("no wear stats here\n")
    assert wear_max is None
    assert wear_hotspot is None


def test_extract_dimm_wear_stats_missing_total_writes_keeps_max_blanks_hotspot():
    # T2.5 fix round 1, Important finding #2: wearLocations and wearMaxWrites
    # present but wearTotalWrites absent entirely must not raise (the old
    # code divided by sum([]) == 0 here, a ZeroDivisionError that killed the
    # caller's entire row through parse_raw_stats' broad except). Wear_Max_Writes
    # is known, so it must survive; only the hot-spot factor is blank.
    content = (
        "i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearLocations 10\n"
        "i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearMaxWrites 50\n"
    )
    wear_max, wear_hotspot = pm.extract_dimm_wear_stats(content)
    assert wear_max == pytest.approx(50)
    assert wear_hotspot is None


def test_extract_dimm_wear_stats_total_writes_present_but_zero_keeps_max_blanks_hotspot():
    content = (
        "i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearLocations 10\n"
        "i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearTotalWrites 0\n"
        "i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wearMaxWrites 50\n"
    )
    wear_max, wear_hotspot = pm.extract_dimm_wear_stats(content)
    assert wear_max == pytest.approx(50)
    assert wear_hotspot is None


def test_extract_dimm_wear_stats_never_raises_on_partial_input():
    # Broader safety net for the same finding: a grab-bag of malformed/
    # partial wear fragments must never raise, whatever they return.
    fragments = [
        "wearLocations 10\nwearMaxWrites 50\n",                       # no totals
        "wearLocations 10\nwearTotalWrites 0\nwearMaxWrites 50\n",    # zero totals
        "wearMaxWrites 50\n",                                         # no locations at all
        "wearLocations 0\nwearTotalWrites 0\nwearMaxWrites 0\n",      # all zero
        "",                                                           # empty
    ]
    for content in fragments:
        pm.extract_dimm_wear_stats(content)  # must not raise


def test_extract_completed_requests_and_bandwidth_missing_exit_line_is_blank():
    content_no_exit = SYNTHETIC_STATS.replace(
        "Exiting at cycle 3000000 because simCycles 3000000 reached.\n", "")
    completed, bw_mbps = pm.extract_completed_requests_and_bandwidth(content_no_exit)
    assert completed is None
    assert bw_mbps is None


def test_extract_end_to_end_latency_ns_missing_is_none():
    assert pm.extract_end_to_end_latency_ns("nothing here\n", 800) is None


# --- T2.5 fix round 1: extract_clocks_mhz / resolve_clocks_mhz ------------
# Important finding #1: the memory clock must come from the run, not from
# CLOCK_FREQUENCY_MHZ, since a technology can be simulated at more than one
# CLK (a clock-sensitivity run still classifies by filename as 1T1R_SLC).

SYNTHETIC_STATS_2400MHZ = SYNTHETIC_STATS.replace(
    "running at 800MHz. My frequency is 3000MHz.",
    "running at 2400MHz. My frequency is 3000MHz.")

SYNTHETIC_STATS_NO_CLOCK_LINE = "\n".join(
    line for line in SYNTHETIC_STATS.splitlines()
    if "My frequency is" not in line) + "\n"


def test_extract_clocks_mhz_parses_clk_and_cpufreq():
    assert pm.extract_clocks_mhz(SYNTHETIC_STATS) == (800, 3000)
    assert pm.extract_clocks_mhz(SYNTHETIC_STATS_2400MHZ) == (2400, 3000)


def test_extract_clocks_mhz_absent_returns_none_none():
    assert pm.extract_clocks_mhz(SYNTHETIC_STATS_NO_CLOCK_LINE) == (None, None)


def test_extract_clocks_mhz_disagreeing_clk_raises():
    two_channels_disagree = SYNTHETIC_STATS + (
        "NVMain: GlobalEventQueue: Added a memory subsystem running at "
        "2400MHz. My frequency is 3000MHz.\n")
    with pytest.raises(ValueError):
        pm.extract_clocks_mhz(two_channels_disagree)


def test_extract_clocks_mhz_disagreeing_cpufreq_raises():
    two_channels_disagree = SYNTHETIC_STATS + (
        "NVMain: GlobalEventQueue: Added a memory subsystem running at "
        "800MHz. My frequency is 1500MHz.\n")
    with pytest.raises(ValueError):
        pm.extract_clocks_mhz(two_channels_disagree)


def test_resolve_clocks_mhz_2400mhz_line_yields_729_17_for_1750_cycles():
    # The reviewer's literal regression case: a ReRAM clock-sensitivity run
    # at CLK 2400 still classifies as 1T1R_SLC by filename; the run's own
    # 2400MHz line must win over CLOCK_FREQUENCY_MHZ['1T1R_SLC'] == 800.
    clk_mhz, cpufreq_mhz = pm.resolve_clocks_mhz(SYNTHETIC_STATS_2400MHZ, '1T1R_SLC')
    assert clk_mhz == 2400
    assert cpufreq_mhz == 3000
    result = pm.extract_end_to_end_latency_ns(SYNTHETIC_STATS_2400MHZ, clk_mhz)
    assert result == pytest.approx(729.1666666666666, abs=0.005)
    assert f"{result:.2f}" == "729.17"


def test_resolve_clocks_mhz_800mhz_line_yields_2187_5_for_1750_cycles():
    clk_mhz, cpufreq_mhz = pm.resolve_clocks_mhz(SYNTHETIC_STATS, '1T1R_SLC')
    assert clk_mhz == 800
    assert cpufreq_mhz == 3000
    result = pm.extract_end_to_end_latency_ns(SYNTHETIC_STATS, clk_mhz)
    assert result == pytest.approx(2187.5)


def test_resolve_clocks_mhz_no_line_falls_back_to_table_with_warning(caplog):
    with caplog.at_level("WARNING"):
        clk_mhz, cpufreq_mhz = pm.resolve_clocks_mhz(
            SYNTHETIC_STATS_NO_CLOCK_LINE, '1T1R_SLC', filename="stats_no_clock_line.out")

    assert clk_mhz == pm.CLOCK_FREQUENCY_MHZ['1T1R_SLC']  # 800, the table default
    assert cpufreq_mhz == pm.CPUFREQ_MHZ  # 3000
    assert any("stats_no_clock_line.out" in record.message for record in caplog.records)
    assert any(record.levelname == "WARNING" for record in caplog.records)


def test_resolve_clocks_mhz_sensitivity_case_logs_info_not_warning(caplog):
    with caplog.at_level("INFO"):
        clk_mhz, cpufreq_mhz = pm.resolve_clocks_mhz(
            SYNTHETIC_STATS_2400MHZ, '1T1R_SLC', filename="stats_sensitivity.out")

    assert clk_mhz == 2400
    info_records = [r for r in caplog.records if r.levelname == "INFO"
                     and "stats_sensitivity.out" in r.message]
    assert info_records, "expected an INFO log naming the file for the clock-sensitivity case"
    warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
    assert not warning_records


def test_calculate_latency_ns_uses_given_clk_mhz_directly():
    assert pm.calculate_latency_ns(1750.0, 800) == pytest.approx(2187.5)
    assert pm.calculate_latency_ns(1750.0, 2400) == pytest.approx(729.1666666666666)


# --- End-to-end through parse_raw_stats() / process_metrics() -------------

def test_parse_and_process_populate_new_columns(tmp_path, monkeypatch):
    stats_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    stats_file.write_text(SYNTHETIC_STATS)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    raw, failures = pm.parse_raw_stats()
    assert failures == []
    assert len(raw) == 1
    record = raw[0]

    assert record['clk_mhz'] == 800
    assert record['cpufreq_mhz'] == 3000
    assert record['completed_requests'] == 150
    assert record['delivered_bw_mbps'] == pytest.approx(9.6)
    assert record['e2e_latency_ns'] == pytest.approx(2187.5)
    assert record['wear_max_writes'] == pytest.approx(50)
    assert record['wear_hotspot_factor'] == pytest.approx(750.0 / 140.0)

    processed = pm.process_metrics(raw)
    assert len(processed) == 1
    row = processed[0]

    assert row['Completed_Requests'] == 150
    assert row['Delivered_BW_MBps'] == pytest.approx(9.6)
    assert row['E2E_Latency_ns'] == pytest.approx(2187.5)
    assert row['Wear_Max_Writes'] == pytest.approx(50)
    assert row['Wear_HotSpot_Factor'] == pytest.approx(750.0 / 140.0)


def test_parse_and_process_clock_sensitivity_run_uses_runs_own_clk(tmp_path, monkeypatch):
    # T2.5 fix round 1, Important finding #1, end to end: a ReRAM run at CLK
    # 2400 still classifies as 1T1R_SLC by filename (classify_technology has
    # no other signal), so if this fell back to CLOCK_FREQUENCY_MHZ it would
    # silently use 800 and mis-convert every cycle count in this row.
    stats_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    stats_file.write_text(SYNTHETIC_STATS_2400MHZ)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    raw, failures = pm.parse_raw_stats()
    assert failures == []
    assert len(raw) == 1
    record = raw[0]

    assert record['technology'] == '1T1R_SLC'
    assert record['clk_mhz'] == 2400
    assert record['e2e_latency_ns'] == pytest.approx(729.1666666666666, abs=0.001)

    processed = pm.process_metrics(raw)
    row = processed[0]
    # Total_Execution_Cycles (averageTotalLatency) = 500.0*100/400... no --
    # averageTotalLatency isn't request-weighted like E2E; extract_total_execution_cycles
    # averages channel0 (500.0) and channel1 (600.0) -> 550.0 cycles.
    assert row['Total_Execution_Cycles'] == pytest.approx(550.0)
    assert row['Latency_ns'] == pytest.approx(550.0 * 1000.0 / 2400)
    assert row['Latency_ns'] != pytest.approx(550.0 * 1000.0 / 800)  # the old, wrong table value
    assert row['E2E_Latency_ns'] == pytest.approx(729.1666666666666, abs=0.001)


def test_ddr5_style_run_has_blank_wear_but_populated_bandwidth(tmp_path, monkeypatch):
    # DDR5/PCM (NullModel): wear columns must be blank, but the delivered
    # bandwidth / completed requests / E2E latency columns are unaffected.
    # Build content with only the all-zero NullModel wear signature (no
    # subarray in this file ever reports a non-zero wear counter).
    lines_without_wear = [
        line for line in SYNTHETIC_STATS.splitlines()
        if not line.startswith('i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.subarray0.wear')
        and not line.startswith('i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank1.subarray0.wear')
    ]
    content = "\n".join(lines_without_wear) + "\n" + NULLMODEL_WEAR_STATS
    stats_file = tmp_path / "stats_DDR5_4800_DRAM_subchannel_gcc_spec2017.out"
    stats_file.write_text(content)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    raw, failures = pm.parse_raw_stats()
    assert failures == []
    assert len(raw) == 1
    record = raw[0]

    assert record['wear_max_writes'] is None
    assert record['wear_hotspot_factor'] is None
    assert record['completed_requests'] == 150
    assert record['delivered_bw_mbps'] == pytest.approx(9.6)


def test_save_bar_chart_metrics_appends_new_columns_at_end(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "OUTPUT_DIR", str(tmp_path))

    row = {
        'Technology': '1T1R_SLC', 'Architecture': 'full_dimm', 'Benchmark': 'gcc_spec2017',
        'Total_Execution_Cycles': 1.0, 'HW_Latency_Cycles': 1.0, 'Queue_Latency_Cycles': 1.0,
        'Latency_ns': 1.0, 'HW_Latency_ns': 1.0, 'Queue_Latency_ns': 1.0,
        'Power': 1.0, 'Dynamic_Power': 1.0, 'Static_Power': 1.0, 'Refresh_Power': 1.0,
        'Unattributed_Power': 1.0, 'PDP': 1.0,
        'Area_Density_Ratio': 1.0,
        'E2E_Latency_ns': 2187.5, 'Delivered_BW_MBps': 9.6,
        'Wear_Max_Writes': 50, 'Wear_HotSpot_Factor': 5.357142857142857,
        'Completed_Requests': 150,
    }
    import pandas as pd
    df = pd.DataFrame([row])
    pm.save_bar_chart_metrics(df)

    out_file = tmp_path / "processed_bar_chart_metrics.csv"
    assert out_file.exists()
    header = out_file.read_text().splitlines()[0].split(',')

    original_columns = [
        'Technology', 'Architecture', 'Benchmark',
        'Total_Execution_Cycles', 'HW_Latency_Cycles', 'Queue_Latency_Cycles',
        'Latency_ns', 'HW_Latency_ns', 'Queue_Latency_ns',
        'Power', 'Dynamic_Power', 'Static_Power', 'Refresh_Power', 'Unattributed_Power', 'PDP',
    ]
    assert header[:len(original_columns)] == original_columns

    new_columns = ['E2E_Latency_ns', 'Delivered_BW_MBps', 'Wear_Max_Writes',
                   'Wear_HotSpot_Factor', 'Completed_Requests']
    assert header[-len(new_columns):] == new_columns


def test_import_does_not_run_main(capsys):
    import importlib
    importlib.reload(pm)
    captured = capsys.readouterr()
    assert "DATA PROCESSING COMPLETE" not in captured.out


# --- T2.5 fix round 2: parse failures are reported, not silently dropped --
# Previously a per-file exception (e.g. extract_clocks_mhz's ValueError on
# disagreeing clock lines within one file) was caught, logged at ERROR, and
# the row silently dropped -- the process still exited 0 either via main()
# or the module's own exception handling. Now parse_raw_stats() returns the
# list of (filename, error) failures alongside the successfully-parsed data,
# and main() (the CLI entry point) turns unallowed failures into a non-zero
# exit, with a --allow-parse-failures flag to downgrade to a WARNING.

DISAGREEING_CLOCK_STATS = SYNTHETIC_STATS + (
    "NVMain: GlobalEventQueue: Added a memory subsystem running at "
    "2400MHz. My frequency is 3000MHz.\n")


def test_parse_raw_stats_reports_bad_file_but_keeps_good_row(tmp_path, monkeypatch):
    good_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    good_file.write_text(SYNTHETIC_STATS)

    bad_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out"
    bad_file.write_text(DISAGREEING_CLOCK_STATS)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(tmp_path))

    data, failures = pm.parse_raw_stats()

    assert len(data) == 1
    assert data[0]['benchmark'] == 'gcc_spec2017'

    assert len(failures) == 1
    fname, err = failures[0]
    assert fname == bad_file.name
    assert "disagreeing" in err.lower() or "CLK" in err


def test_main_cli_exits_nonzero_on_parse_failure_reports_bad_file_by_name(tmp_path, monkeypatch, caplog):
    good_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    good_file.write_text(SYNTHETIC_STATS)

    bad_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out"
    bad_file.write_text(DISAGREEING_CLOCK_STATS)

    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        sys, "argv",
        ["process_metrics.py", "--results-dir", str(tmp_path), "--output-dir", str(output_dir)])

    with caplog.at_level("ERROR"):
        success = pm.main()

    assert success is False
    assert any(bad_file.name in record.message for record in caplog.records)

    # One bad file must not hide the other: the good row is still written.
    out_csv = output_dir / "processed_bar_chart_metrics.csv"
    assert out_csv.exists()
    import pandas as pd
    df = pd.read_csv(out_csv)
    assert len(df) == 1
    assert df.iloc[0]['Benchmark'] == 'gcc_spec2017'


def test_main_cli_allow_parse_failures_flag_exits_zero(tmp_path, monkeypatch, caplog):
    good_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out"
    good_file.write_text(SYNTHETIC_STATS)

    bad_file = tmp_path / "stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out"
    bad_file.write_text(DISAGREEING_CLOCK_STATS)

    output_dir = tmp_path / "out"

    monkeypatch.setattr(
        sys, "argv",
        ["process_metrics.py", "--results-dir", str(tmp_path), "--output-dir", str(output_dir),
         "--allow-parse-failures"])

    with caplog.at_level("WARNING"):
        success = pm.main()

    assert success is True
    assert any(bad_file.name in record.message and record.levelname == "WARNING"
               for record in caplog.records)


def test_extract_end_to_end_latency_ns_accepts_positive_exponent():
    # T4.1 pilot: a saturated PCM run printed "averageEndToEndLatency 2.4895e+07";
    # the number pattern lacked '+', matched "2.4895e", and the column went blank.
    stats = (
        "i0.defaultMemory.channel0.FRFCFS-WQF.averageEndToEndLatency 2.4895e+07\n"
        "i0.defaultMemory.channel0.FRFCFS-WQF.measuredEndToEndLatencies 2794420\n"
    )
    result = pm.extract_end_to_end_latency_ns(stats, 400)
    assert result == pytest.approx(2.4895e7 * 2.5)
