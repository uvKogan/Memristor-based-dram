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
        'Background_Power_Device_Factor': 1,
        **{name: pm.RUN_PROVENANCE_UNKNOWN for name in pm.RUN_PROVENANCE_COLUMN_NAMES},
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
    # F1 (final-review C1) appended Background_Power_Device_Factor after the
    # T2.5 block, and F2 (I6) appended the Run_* provenance columns after that.
    # Every append is at the END, so a reader that indexes by name keeps working.
    run_columns = list(pm.RUN_PROVENANCE_COLUMN_NAMES)
    assert header[-len(run_columns):] == run_columns
    tail = header[:-len(run_columns)]
    assert tail[-len(new_columns) - 1:-1] == new_columns
    assert tail[-1] == 'Background_Power_Device_Factor'


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


# ==========================================================================
# F1 (final-review C1): the EnergyModel-current background-power correction
# ==========================================================================
#
# NVMain's StandardRank divides backgroundPower by the rank's device count in
# `EnergyModel current` mode and never multiplies it back, while activate,
# burst and refresh ARE multiplied back. process_metrics.py corrects the
# printed value in post-processing. These tests use synthetic stats text and a
# synthetic config in tmp_path only: nothing here reads results/ or
# simulators/, and nothing writes into results/.

# Devices per rank = BusWidth / DeviceWidth = 32 / 8 = 4.
# Two ranks (one per channel) -> 8 devices on the module.
F1_CONFIG = """\
; synthetic DDR5-shaped config for the F1 tests
CLK 2400
BusWidth 32
DeviceWidth 8
RANKS 1
CHANNELS 2
EnergyModel current
Voltage 1.1
EIDD2P0 46.87
EIDD2N 49
EIDD3P 115.94
EIDD3N 117.6
"""

# Per rank: backgroundPower 0.09 W printed (one device), so 0.36 W corrected.
# backgroundEnergy 1.96363636e+11 mA*t is chosen so that the independent
# cross-check reproduces 0.36 W exactly:
#   E * V / memory_cycles / 1000 = 1.96363636e11 * 1.1 / 6e8 / 1000 = 0.36
# Memory cycles = "Exiting at cycle 750000000" (CPUFreq 3000) x 2400/3000 = 6e8.
# Printed rank totalPower = 0.09 + 0 + 0.0001 + 0.036 = 0.1261 (NVMain's own,
# with the undercounted background); corrected = 0.36 + 0.0001 + 0.036 = 0.3961.
F1_CURRENT_MODE_STATS_TEMPLATE = """\
NVMain command line is:
/home/yuvalk/MBMM/simulators/nvmain/nvmain.fast {config} /tmp/trace.nvt 600000000

NVMain: GlobalEventQueue: Added a memory subsystem running at 2400MHz. My frequency is 3000MHz.
Creating 32 banks in all 4 devices.
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.totalEnergy 2.2e+11mA*t
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.backgroundEnergy 1.96363636e+11mA*t
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.totalPower 0.1261W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.backgroundPower 0.09W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.activatePower 0W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.burstPower 0.0001W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.refreshPower 0.036W
i0.defaultMemory.channel0.FRFCFS.mem_reads 40
i0.defaultMemory.channel0.FRFCFS.mem_writes 10
i0.defaultMemory.channel0.FRFCFS.averageTotalLatency 500.0
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.totalEnergy 2.2e+11mA*t
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.backgroundEnergy 1.96363636e+11mA*t
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.totalPower 0.1261W
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.backgroundPower 0.09W
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.activatePower 0W
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.burstPower 0.0001W
i0.defaultMemory.channel1.FRFCFS.channel1.rank0.refreshPower 0.036W
i0.defaultMemory.channel1.FRFCFS.mem_reads 40
i0.defaultMemory.channel1.FRFCFS.mem_writes 10
i0.defaultMemory.channel1.FRFCFS.averageTotalLatency 500.0
Exiting at cycle 750000000 because simCycles 750000000 reached.
"""

# Same shape, energy model `NonVolatile`/`energy`: energies in nJ, no
# deviceCount division anywhere in NVMain, so nothing may be corrected.
F1_ENERGY_MODE_STATS = """\
NVMain command line is:
/home/yuvalk/MBMM/simulators/nvmain/nvmain.fast /tmp/does_not_exist.config /tmp/trace.nvt 600000000

NVMain: GlobalEventQueue: Added a memory subsystem running at 800MHz. My frequency is 3000MHz.
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.totalEnergy 2.17684e+08nJ
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.backgroundEnergy 2.16768e+08nJ
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.totalPower 0.867416W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.backgroundPower 0.867072W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.activatePower 0.0002W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.burstPower 0.000144W
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.refreshPower 0W
i0.defaultMemory.channel0.FRFCFS.mem_reads 40
i0.defaultMemory.channel0.FRFCFS.mem_writes 10
i0.defaultMemory.channel0.FRFCFS.averageTotalLatency 500.0
Exiting at cycle 750000000 because simCycles 750000000 reached.
"""


def _f1_current_mode(tmp_path, config_text=F1_CONFIG, config_name="F1_DDR5.config"):
    """Write the synthetic config into tmp_path and return the stats text that
    names it on its own NVMain command line."""
    config = tmp_path / config_name
    config.write_text(config_text)
    return F1_CURRENT_MODE_STATS_TEMPLATE.format(config=config)


def test_f1_current_mode_detected_from_energy_units(tmp_path):
    assert pm.uses_current_energy_model(_f1_current_mode(tmp_path)) is True
    assert pm.uses_current_energy_model(F1_ENERGY_MODE_STATS) is False


def test_f1_device_factor_is_four_for_current_mode(tmp_path):
    stats = _f1_current_mode(tmp_path)
    assert pm.background_power_device_factor(stats, stats_name="synthetic") == 4


def test_f1_device_factor_is_one_for_energy_mode():
    # No config is even consulted: an energy-mode file names a config that does
    # not exist here, and the factor is still 1 without raising.
    assert pm.background_power_device_factor(
        F1_ENERGY_MODE_STATS, stats_name="synthetic") == 1


def test_f1_background_power_multiplied_by_four(tmp_path):
    stats = _f1_current_mode(tmp_path)
    factor = pm.background_power_device_factor(stats, stats_name="synthetic")
    components = pm.extract_module_power_components(stats, background_factor=factor)

    # Two ranks x 0.09 W printed = 0.18 W raw, x 4 = 0.72 W corrected.
    assert components['backgroundPowerRaw'] == pytest.approx(0.18)
    assert components['backgroundPower'] == pytest.approx(0.72)
    assert components['backgroundPowerCorrection'] == pytest.approx(0.54)
    assert components['backgroundPowerDeviceFactor'] == 4
    assert components['rankCount'] == 2

    # The other three components are NVMain's own, untouched: they were already
    # multiplied back by deviceCount inside StandardRank.
    assert components['activatePower'] == pytest.approx(0.0)
    assert components['burstPower'] == pytest.approx(0.0002)
    assert components['refreshPower'] == pytest.approx(0.072)


def test_f1_energy_mode_components_are_untouched():
    factor = pm.background_power_device_factor(
        F1_ENERGY_MODE_STATS, stats_name="synthetic")
    corrected = pm.extract_module_power_components(
        F1_ENERGY_MODE_STATS, background_factor=factor)
    baseline = pm.extract_module_power_components(F1_ENERGY_MODE_STATS)

    assert factor == 1
    for key in ('backgroundPower', 'activatePower', 'burstPower', 'refreshPower'):
        assert corrected[key] == baseline[key]
    assert corrected['backgroundPowerCorrection'] == 0.0
    assert corrected['backgroundPower'] == pytest.approx(0.867072)


def test_f1_missing_config_raises_naming_the_file(tmp_path):
    # Current-mode stats naming a config that exists nowhere: no default.
    stats = F1_CURRENT_MODE_STATS_TEMPLATE.format(
        config=str(tmp_path / "never_written.config"))
    with pytest.raises(ValueError) as excinfo:
        pm.background_power_device_factor(
            stats, stats_name="stats_synthetic.out", search_dirs=[str(tmp_path)])
    message = str(excinfo.value)
    assert "stats_synthetic.out" in message
    assert "never_written.config" in message


def test_f1_missing_config_keys_raise_naming_the_key(tmp_path):
    config_text = "\n".join(
        line for line in F1_CONFIG.splitlines() if not line.startswith("DeviceWidth"))
    stats = _f1_current_mode(tmp_path, config_text=config_text + "\n")
    with pytest.raises(ValueError) as excinfo:
        pm.background_power_device_factor(stats, stats_name="stats_synthetic.out")
    message = str(excinfo.value)
    assert "stats_synthetic.out" in message
    assert "DeviceWidth" in message


def test_f1_no_command_line_raises(tmp_path):
    stats = _f1_current_mode(tmp_path).split("\n", 2)[2]  # drop the command-line banner
    with pytest.raises(ValueError) as excinfo:
        pm.background_power_device_factor(stats, stats_name="stats_synthetic.out")
    assert "stats_synthetic.out" in str(excinfo.value)


def test_f1_printed_device_count_disagreement_raises(tmp_path):
    stats = _f1_current_mode(tmp_path).replace(
        "Creating 32 banks in all 4 devices.", "Creating 32 banks in all 8 devices.")
    with pytest.raises(ValueError) as excinfo:
        pm.background_power_device_factor(stats, stats_name="stats_synthetic.out")
    assert "disagree" in str(excinfo.value)


def test_f1_background_energy_crosscheck_reproduces_corrected_power(tmp_path):
    # The independent check: rank backgroundEnergy (mA*t) x Voltage / elapsed
    # memory cycles / 1000 must equal the CORRECTED rank background power,
    # without going through the printed backgroundPower at all.
    stats = _f1_current_mode(tmp_path)
    checks = pm.crosscheck_current_mode_background(
        stats, 4, clk_mhz=2400, cpufreq_mhz=3000, stats_name="synthetic")

    assert len(checks) == 2
    for check in checks:
        assert check['expected_w'] == pytest.approx(0.36, rel=1e-6)
        assert check['corrected_w'] == pytest.approx(0.36)
        assert check['ok'] is True


def test_f1_background_energy_crosscheck_fails_on_the_uncorrected_value(tmp_path):
    # Factor 1 is what the defect amounts to; the cross-check must reject it.
    stats = _f1_current_mode(tmp_path)
    checks = pm.crosscheck_current_mode_background(
        stats, 1, clk_mhz=2400, cpufreq_mhz=3000, stats_name="synthetic")
    assert checks and all(check['ok'] is False for check in checks)


def test_f1_memory_clock_cycles_from_global_exit_cycle(tmp_path):
    stats = _f1_current_mode(tmp_path)
    assert pm.extract_memory_clock_cycles(stats, 2400, 3000) == pytest.approx(6e8)


def test_f1_static_power_floor_and_ceiling(tmp_path):
    stats = _f1_current_mode(tmp_path)
    components = pm.extract_module_power_components(stats, background_factor=4)
    floor_w, ceiling_w, devices = pm.current_mode_static_power_bounds(
        stats, 4, components['rankCount'], stats_name="synthetic")

    # 8 devices (4 per rank x 2 ranks) x EIDD2P0 46.87 mA x 1.1 V / 1000.
    assert devices == 8
    assert floor_w == pytest.approx(8 * 46.87 * 1.1 / 1000.0)
    assert ceiling_w == pytest.approx(8 * 117.6 * 1.1 / 1000.0)

    # The corrected module static power sits inside the config's own range;
    # the uncorrected one is below the floor, which is the defect made visible.
    assert floor_w <= components['backgroundPower'] <= ceiling_w
    assert components['backgroundPowerRaw'] < floor_w


def test_f1_end_to_end_power_pdp_and_new_column(tmp_path, monkeypatch):
    stats_dir = tmp_path / "system"
    stats_dir.mkdir()
    config = tmp_path / "F1_DDR5.config"
    config.write_text(F1_CONFIG)

    (stats_dir / "stats_DDR5_4800_DRAM_subchannel_gcc_spec2017.out").write_text(
        F1_CURRENT_MODE_STATS_TEMPLATE.format(config=config))
    (stats_dir / "stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out").write_text(
        F1_ENERGY_MODE_STATS)

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(stats_dir))
    raw, failures = pm.parse_raw_stats()
    assert failures == []

    rows = {r['technology']: r for r in raw}

    # DDR5: Power carries the same correction the components do, so the
    # decomposition still reconciles.
    ddr5 = rows['DDR5_4800']
    assert ddr5['background_power_device_factor'] == 4
    assert ddr5['background_power'] == pytest.approx(0.72)
    assert ddr5['power'] == pytest.approx(0.1261 * 2 + 0.54)

    # ReRAM: factor 1, power exactly NVMain's printed rank sum.
    reram = rows['1T1R_SLC']
    assert reram['background_power_device_factor'] == 1
    assert reram['power'] == pytest.approx(0.867416)

    processed = {r['Technology']: r for r in pm.process_metrics(raw)}

    ddr5_row = processed['DDR5_4800']
    assert ddr5_row['Background_Power_Device_Factor'] == 4
    assert ddr5_row['Static_Power'] == pytest.approx(0.72)
    assert ddr5_row['Unattributed_Power'] == pytest.approx(0.0, abs=1e-9)
    assert ddr5_row['PDP'] == pytest.approx(
        ddr5_row['Latency_ns'] * ddr5_row['Power'])

    assert processed['1T1R_SLC']['Background_Power_Device_Factor'] == 1

    # The column reaches every CSV that carries a power number.
    import pandas as pd
    monkeypatch.setattr(pm, "OUTPUT_DIR", str(tmp_path / "out"))
    df = pd.DataFrame(pm.process_metrics(raw))
    pm.save_bar_chart_metrics(df)
    pm.save_pareto_metrics(df)
    pm.save_hero_metrics(df)
    for name in ("processed_bar_chart_metrics.csv", "processed_pareto_metrics.csv",
                 "processed_hero_metrics.csv"):
        header = (tmp_path / "out" / name).read_text().splitlines()[0].split(',')
        # F2 (I6): the Run_* provenance columns are appended after it.
        assert header[-len(pm.RUN_PROVENANCE_COLUMN_NAMES) - 1] == 'Background_Power_Device_Factor'


def test_f1_current_mode_file_with_unresolvable_config_is_a_reported_failure(
        tmp_path, monkeypatch):
    # A current-mode stats file whose config cannot be found must surface as a
    # named parse failure (and a non-zero exit), never as a silently
    # uncorrected row.
    stats_dir = tmp_path / "system"
    stats_dir.mkdir()
    bad = stats_dir / "stats_DDR5_4800_DRAM_subchannel_gcc_spec2017.out"
    bad.write_text(F1_CURRENT_MODE_STATS_TEMPLATE.format(
        config=str(tmp_path / "never_written.config")))

    monkeypatch.setattr(pm, "RESULTS_SYS_DIR", str(stats_dir))
    monkeypatch.setattr(pm, "NVMAIN_CONFIG_SEARCH_DIRS", (str(tmp_path),))

    raw, failures = pm.parse_raw_stats()
    assert raw == []
    assert [name for name, _ in failures] == [bad.name]
    assert "never_written.config" in failures[0][1]
