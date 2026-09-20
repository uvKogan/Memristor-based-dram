"""T2.5: end-to-end latency, delivered bandwidth, completed requests in the
per-run terminal report (5_summary_report.py).

5_summary_report.py starts with a digit and cannot be imported with a plain
`import`; loaded via importlib.util.spec_from_file_location, same pattern as
tests/test_gen_nvmain_config.py.
"""

import importlib.util
import pathlib
import sys

import pytest

spec = importlib.util.spec_from_file_location(
    "summary_report", pathlib.Path(__file__).resolve().parents[1] / "5_summary_report.py")
summary_report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(summary_report)


# Same synthetic two-channel content and hand-computed values as
# tests/test_process_metrics.py (see that file's header comment for the
# arithmetic): E2E latency weighted mean = 1750.0 cycles -> at this file's
# own 800MHz clock line, 2187.5 ns; Completed_Requests = 150; elapsed
# 3,000,000 CPUFreq cycles -> 1e-3 s -> Delivered BW = 9.6 MB/s.
SYNTHETIC_STATS = """\
NVMain: GlobalEventQueue: Added a memory subsystem running at 800MHz. My frequency is 3000MHz.
i0.defaultMemory.channel0.FRFCFS.mem_reads 40
i0.defaultMemory.channel0.FRFCFS.mem_writes 10
i0.defaultMemory.channel0.FRFCFS.averageTotalLatency 500.0
i0.defaultMemory.channel0.FRFCFS.averageEndToEndLatency 1000.0
i0.defaultMemory.channel0.FRFCFS.measuredEndToEndLatencies 100
i0.defaultMemory.channel1.FRFCFS.mem_reads 60
i0.defaultMemory.channel1.FRFCFS.mem_writes 40
i0.defaultMemory.channel1.FRFCFS.averageTotalLatency 600.0
i0.defaultMemory.channel1.FRFCFS.averageEndToEndLatency 2000.0
i0.defaultMemory.channel1.FRFCFS.measuredEndToEndLatencies 300
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.bandwidth 601.123MB/s
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.bank0.totalWriteRequests 10
i0.defaultMemory.channel0.FRFCFS.channel0.rank0.totalPower 0.5W
Exiting at cycle 3000000 because simCycles 3000000 reached.
"""

SYNTHETIC_STATS_2400MHZ = SYNTHETIC_STATS.replace(
    "running at 800MHz. My frequency is 3000MHz.",
    "running at 2400MHz. My frequency is 3000MHz.")

# Disagreeing clock lines: extract_clocks_mhz (via resolve_clocks_mhz, called
# from extract_metrics) raises ValueError on this -- the T2.5 fix round 2
# regression case.
DISAGREEING_CLOCK_STATS = SYNTHETIC_STATS + (
    "NVMain: GlobalEventQueue: Added a memory subsystem running at "
    "2400MHz. My frequency is 3000MHz.\n")


def test_no_duplicate_extractors_imports_from_process_metrics():
    # T2.5 fix round 1, Minor finding #3: this module must not keep its own
    # copy of these extractors -- it imports process_metrics (as `pm`) and
    # calls its functions directly, so there is exactly one implementation.
    assert hasattr(summary_report, "pm")
    assert summary_report.pm.__name__ == "process_metrics"
    assert not hasattr(summary_report, "extract_end_to_end_latency_cycles")
    assert not hasattr(summary_report, "extract_completed_requests_and_delivered_bw")


def test_extract_metrics_reports_new_columns(tmp_path):
    stats_file = tmp_path / "stats_probe.out"
    stats_file.write_text(SYNTHETIC_STATS)

    metrics = summary_report.extract_metrics(str(stats_file))

    assert metrics is not None
    # T2.5 fix round 1: now in ns (via process_metrics.resolve_clocks_mhz),
    # not cycles -- this file's own 800MHz line matches the pre-T2.5
    # CLOCK_FREQUENCY_MHZ default, so 1750 cycles -> 2187.5 ns.
    assert metrics["E2E Lat (ns)"] == "2187.5"
    assert metrics["Completed Reqs"] == "150"
    assert metrics["Delivered BW (MB/s)"] == "9.60"
    # Renamed x-check column keeps NVMain's own bank-level bandwidth stat.
    assert metrics["NVMain BW (x-check)"] == "601.123MB/s"
    assert "Bandwidth" not in metrics
    assert "E2E Lat (cyc)" not in metrics


def test_extract_metrics_uses_runs_own_clock_for_sensitivity_run(tmp_path):
    # Same clock-sensitivity regression as test_process_metrics.py: a run's
    # own 2400MHz line must be used, not the (here, unknown/default) table.
    stats_file = tmp_path / "stats_probe_2400.out"
    stats_file.write_text(SYNTHETIC_STATS_2400MHZ)

    metrics = summary_report.extract_metrics(str(stats_file))

    assert metrics["E2E Lat (ns)"] == "729.2"  # 1750 cycles * 1000/2400, rounded to .1f


def test_extract_metrics_missing_data_is_na(tmp_path):
    stats_file = tmp_path / "stats_empty.out"
    stats_file.write_text("nothing useful here\n")

    metrics = summary_report.extract_metrics(str(stats_file))

    assert metrics["E2E Lat (ns)"] == "N/A"
    assert metrics["Completed Reqs"] == "N/A"
    assert metrics["Delivered BW (MB/s)"] == "N/A"


def test_module_has_main_guard():
    # Loading this module above via spec.loader.exec_module() already proves
    # main() didn't run as a side effect of import (no argparse SystemExit,
    # no "STEP 5 COMPLETE" print); this additionally confirms *why*, i.e.
    # the module guards its entry point.
    import inspect
    source = inspect.getsource(summary_report)
    assert 'if __name__ == "__main__":' in source


# --- T2.5 fix round 2: parse failures are reported, not an uncaught crash -

def test_extract_metrics_raises_on_disagreeing_clock_lines(tmp_path):
    # extract_metrics() itself still raises (it calls resolve_clocks_mhz
    # internally, unchanged) -- main()'s per-file try/except, tested below,
    # is what turns this from an uncaught crash into a reported failure.
    bad_file = tmp_path / "stats_bad.out"
    bad_file.write_text(DISAGREEING_CLOCK_STATS)

    with pytest.raises(ValueError):
        summary_report.extract_metrics(str(bad_file))


def test_main_cli_exits_nonzero_on_parse_failure_reports_bad_file_by_name(
        tmp_path, monkeypatch, capsys):
    good_file = tmp_path / "stats_good.out"
    good_file.write_text(SYNTHETIC_STATS)

    bad_file = tmp_path / "stats_bad.out"
    bad_file.write_text(DISAGREEING_CLOCK_STATS)

    monkeypatch.setattr(
        sys, "argv", ["5_summary_report.py", "--files", str(good_file), str(bad_file)])

    success = summary_report.main()
    captured = capsys.readouterr()

    assert success is False
    assert bad_file.name in captured.out
    assert good_file.name in captured.out  # one bad file must not hide the other


def test_main_cli_allow_parse_failures_flag_exits_zero(tmp_path, monkeypatch, capsys):
    good_file = tmp_path / "stats_good.out"
    good_file.write_text(SYNTHETIC_STATS)

    bad_file = tmp_path / "stats_bad.out"
    bad_file.write_text(DISAGREEING_CLOCK_STATS)

    monkeypatch.setattr(
        sys, "argv",
        ["5_summary_report.py", "--files", str(good_file), str(bad_file),
         "--allow-parse-failures"])

    success = summary_report.main()
    captured = capsys.readouterr()

    assert success is True
    assert bad_file.name in captured.out
    assert "[WARNING]" in captured.out
