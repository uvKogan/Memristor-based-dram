"""T3.5: standalone NVMain trace + sidecar validator.

Fixtures are tiny, hand-built trace/sidecar pairs written to tmp_path, not
real trace excerpts: they exist to exercise one validation rule each. Sidecar
key layout mirrors the two real parsers exactly (see parse_gem5_memctrl.py's
build_sidecar() for kind "gem5" and parse_trace.py's build_sidecar() for
kind "scalesim").
"""

import json
import pathlib
import sys

import pytest

import tools.validate_trace as vt

DATA = "0" * 128


def _trace_text(records):
    """records: list of (cycle, op, addr_hex_no_prefix_or_full, thread)."""
    lines = []
    for cycle, op, addr, thread in records:
        addr_field = addr if addr.startswith("0x") or addr.startswith("-") else f"0x{addr}"
        lines.append(f"{cycle} {op} {addr_field} {DATA} {thread}")
    return "\n".join(lines) + "\n"


def _write_trace(tmp_path, name, records):
    p = tmp_path / name
    p.write_text(_trace_text(records))
    return p


def _gem5_sidecar(total, reads, writes, first_cycle, last_cycle, aligned_fraction=1.0,
                   companion_ratio=3.0, retries_dropped=0, unmatched_retries=0,
                   malformed_request=0, truncated_final_line=0,
                   missing_accounting=False, broken_identity=False):
    """Build a kind-gem5 sidecar. By default the provenance accounting
    (dropped_lines / region_excluded_lines / lines_read) is self-consistent
    with `total` and gives a healthy companion-line ratio (3.0), so plain
    calls (as used by most fixtures) pass check_gem5_provenance() unchanged.
    Pass missing_accounting=True or broken_identity=True to deliberately
    break it for the provenance-guard tests.
    """
    companion = round(companion_ratio * total)
    dropped = {
        "access_to": companion, "command_for": 0, "responding_to_address": 0,
        "queue_dump": 0, "retry": retries_dropped, "non_mem_ctrl": 0,
        "other_mem_ctrl": 0, "unparsed": 0, "malformed_request": malformed_request,
        "truncated_final_line": truncated_final_line, "unmatched_retry": unmatched_retries,
    }
    region_excluded = {"recvAtomic": 0, "recvTimingReq": 0}
    lines_read = total + sum(dropped.values()) + sum(region_excluded.values())
    if broken_identity:
        lines_read += 1

    sidecar = {
        "parser": "parse_gem5_memctrl.py",
        "parser_version": "1.2.0",
        "cpufreq_mhz": 3000,
        "unit": "cycle = 1/3000 us (CPUFreq 3000 MHz)",
        "records": {
            "total": total, "reads": reads, "writes": writes,
            "first_cycle": first_cycle, "last_cycle": last_cycle,
        },
        "addresses": {
            "min": "0x0", "max": "0xffff",
            "aligned_64b_fraction": aligned_fraction,
            "size_histogram": {},
        },
    }
    if not missing_accounting:
        sidecar["dropped_lines"] = dropped
        sidecar["region_excluded_lines"] = region_excluded
        sidecar["lines_read"] = lines_read
        sidecar["skip_ns_excluded_lines"] = 0
        sidecar["max_held_records"] = 0
        sidecar["allow_malformed"] = 0
        sidecar["malformed_lines_seen"] = malformed_request
    return sidecar


def _scalesim_sidecar(records_written, reads, writes, first_cycle, last_cycle,
                       aligned_fraction=0.015625):
    return {
        "parser": "parse_trace.py",
        "parser_version": "2.1.0",
        "op_rule": "W if 'OFMAP' appears in the input filename (case-insensitive), else R",
        "op": "R" if reads else "W",
        "rows_read": records_written,
        "records_written": records_written,
        "padding_skipped": 0,
        "reads": reads,
        "writes": writes,
        "cycles": {"rebase_offset": 0, "first_cycle": first_cycle, "last_cycle": last_cycle},
        "addresses": {
            "min": "0x0", "max": "0xffff", "span_bytes": 65535,
            "aligned_64b_fraction": aligned_fraction,
            "distinct_64b_lines": 1, "records_sharing_line_with_previous": 0,
        },
    }


def _write_sidecar(tmp_path, name, sidecar):
    p = tmp_path / name
    p.write_text(json.dumps(sidecar))
    return p


def _validate(trace_path, sidecar, kind, window_ns=250_000_000, cpufreq_mhz=3000,
              require_window=False, max_distinct=50_000_000):
    return vt.validate_trace(
        str(trace_path), sidecar, kind, window_ns, cpufreq_mhz,
        require_window, max_distinct,
    )


# ---------------------------------------------------------------------------
# Good traces
# ---------------------------------------------------------------------------

def test_good_gem5_style_passes(tmp_path):
    records = [(0, "R", "40", 0), (10, "W", "80", 0), (20, "R", "c0", 0)]
    trace = _write_trace(tmp_path, "good.nvt", records)
    sidecar = _gem5_sidecar(total=3, reads=2, writes=1, first_cycle=0, last_cycle=20)
    report = _validate(trace, sidecar, "gem5")
    assert report["verdict"] == "PASS"
    assert report["records"] == 3
    assert report["alignment_fraction"] == 1.0
    assert report["duplicate_count"] == 0


def test_good_scalesim_style_unaligned_passes_with_report(tmp_path):
    # Tensor-element granular addresses: mostly NOT 64-byte aligned. Must be
    # reported, not failed, for kind scalesim.
    records = [(0, "R", "1", 0), (1, "R", "2", 0), (2, "R", "3", 0)]
    trace = _write_trace(tmp_path, "good_scalesim.nvt", records)
    sidecar = _scalesim_sidecar(records_written=3, reads=3, writes=0, first_cycle=0, last_cycle=2)
    report = _validate(trace, sidecar, "scalesim")
    assert report["verdict"] == "PASS"
    assert report["alignment_fraction"] == 0.0
    assert report["shortfall_ms"] is not None


def test_kind_inferred_from_sidecar_gem5(tmp_path):
    records = [(0, "R", "40", 0)]
    trace = _write_trace(tmp_path, "t.nvt", records)
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    assert vt.infer_kind(sidecar) == "gem5"


def test_kind_inferred_from_sidecar_scalesim(tmp_path):
    sidecar = _scalesim_sidecar(records_written=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    assert vt.infer_kind(sidecar) == "scalesim"


# ---------------------------------------------------------------------------
# Hard failures
# ---------------------------------------------------------------------------

def test_non_monotonic_cycles_fail(tmp_path):
    records = [(10, "R", "40", 0), (5, "R", "80", 0)]
    trace = _write_trace(tmp_path, "nonmono.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=2, writes=0, first_cycle=10, last_cycle=5)
    with pytest.raises(vt.ValidationError, match=r"line 2.*non-monotonic"):
        _validate(trace, sidecar, "gem5")


def test_misaligned_address_in_gem5_kind_fails(tmp_path):
    records = [(0, "R", "40", 0), (1, "R", "41", 0)]  # 0x41 not 64-byte aligned
    trace = _write_trace(tmp_path, "misaligned.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=2, writes=0, first_cycle=0, last_cycle=1)
    with pytest.raises(vt.ValidationError, match=r"line 2.*aligned"):
        _validate(trace, sidecar, "gem5")


def test_bad_data_field_length_fails(tmp_path):
    p = tmp_path / "baddata.nvt"
    p.write_text(f"0 R 0x40 {'0' * 127} 0\n")  # one char short
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*not exactly 128 characters"):
        _validate(p, sidecar, "gem5")


def test_negative_address_fails(tmp_path):
    p = tmp_path / "negaddr.nvt"
    p.write_text(f"0 R -0x40 {DATA} 0\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*address"):
        _validate(p, sidecar, "gem5")


def test_sidecar_count_mismatch_fails(tmp_path):
    records = [(0, "R", "40", 0), (1, "R", "80", 0)]
    trace = _write_trace(tmp_path, "mismatch.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=99, writes=0, first_cycle=0, last_cycle=1)
    with pytest.raises(vt.ValidationError, match=r"sidecar disagreement.*read count"):
        _validate(trace, sidecar, "gem5")


def test_missing_sidecar_fails(tmp_path):
    with pytest.raises(vt.ValidationError, match=r"missing sidecar"):
        vt.load_sidecar(str(tmp_path / "does_not_exist.sidecar.json"))


def test_four_x_consecutive_duplicates_in_gem5_kind_fails(tmp_path):
    records = (
        [(0, "R", "40", 0)] * 4 +
        [(10, "R", "80", 0)] * 4
    )
    trace = _write_trace(tmp_path, "dup.nvt", records)
    sidecar = _gem5_sidecar(total=8, reads=8, writes=0, first_cycle=0, last_cycle=10)
    with pytest.raises(vt.ValidationError, match=r"duplicate"):
        _validate(trace, sidecar, "gem5")


def test_duplicates_reported_not_failed_for_scalesim(tmp_path):
    records = (
        [(0, "R", "1", 0)] * 4 +
        [(10, "R", "2", 0)] * 4
    )
    trace = _write_trace(tmp_path, "dup_scalesim.nvt", records)
    sidecar = _scalesim_sidecar(records_written=8, reads=8, writes=0, first_cycle=0, last_cycle=10)
    report = _validate(trace, sidecar, "scalesim")
    assert report["verdict"] == "PASS"
    assert report["duplicate_count"] == 6
    assert report["duplicate_fraction"] == pytest.approx(0.75)


def test_zero_records_fails(tmp_path):
    p = tmp_path / "empty.nvt"
    p.write_text("")
    sidecar = _gem5_sidecar(total=0, reads=0, writes=0, first_cycle=None, last_cycle=None)
    with pytest.raises(vt.ValidationError, match=r"zero records"):
        _validate(p, sidecar, "gem5")


def test_op_not_r_or_w_fails(tmp_path):
    p = tmp_path / "badop.nvt"
    p.write_text(f"0 X 0x40 {DATA} 0\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*not R or W"):
        _validate(p, sidecar, "gem5")


def test_wrong_field_count_fails(tmp_path):
    p = tmp_path / "badfields.nvt"
    p.write_text(f"0 R 0x40 {DATA}\n")  # missing thread id
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*5 fields"):
        _validate(p, sidecar, "gem5")


def test_thread_id_not_integer_fails(tmp_path):
    p = tmp_path / "badthread.nvt"
    p.write_text(f"0 R 0x40 {DATA} abc\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*thread id"):
        _validate(p, sidecar, "gem5")


def test_sidecar_alignment_fraction_not_1_fails_for_gem5(tmp_path):
    records = [(0, "R", "40", 0)]
    trace = _write_trace(tmp_path, "t.nvt", records)
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0,
                             aligned_fraction=0.5)
    with pytest.raises(vt.ValidationError, match=r"aligned_64b_fraction"):
        _validate(trace, sidecar, "gem5")


# ---------------------------------------------------------------------------
# Window arithmetic
# ---------------------------------------------------------------------------

def test_window_boundary_record_is_outside(tmp_path):
    # 250 ms at 3000 MHz = 750,000,000 cycles. A record exactly at that
    # cycle is outside the window ("inside" means cycle < window_cycles).
    records = [(749_999_999, "R", "40", 0), (750_000_000, "R", "80", 0)]
    trace = _write_trace(tmp_path, "boundary.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=2, writes=0,
                             first_cycle=749_999_999, last_cycle=750_000_000)
    report = _validate(trace, sidecar, "gem5")
    assert report["window_cycles"] == 750_000_000
    assert report["reads_in_window"] == 1


def test_require_window_shortfall_fails_for_gem5(tmp_path):
    records = [(0, "R", "40", 0), (100, "R", "80", 0)]
    trace = _write_trace(tmp_path, "short.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=2, writes=0, first_cycle=0, last_cycle=100)
    with pytest.raises(vt.ValidationError, match=r"shorter than the"):
        _validate(trace, sidecar, "gem5", require_window=True)


def test_shortfall_reported_not_failed_without_require_window(tmp_path):
    records = [(0, "R", "40", 0), (100, "R", "80", 0)]
    trace = _write_trace(tmp_path, "short2.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=2, writes=0, first_cycle=0, last_cycle=100)
    report = _validate(trace, sidecar, "gem5", require_window=False)
    assert report["verdict"] == "PASS"
    assert report["shortfall_ms"] is not None


def test_shortfall_never_fails_scalesim_even_with_require_window(tmp_path):
    records = [(0, "R", "1", 0), (100, "R", "2", 0)]
    trace = _write_trace(tmp_path, "short3.nvt", records)
    sidecar = _scalesim_sidecar(records_written=2, reads=2, writes=0, first_cycle=0, last_cycle=100)
    report = _validate(trace, sidecar, "scalesim", require_window=True)
    assert report["verdict"] == "PASS"


# ---------------------------------------------------------------------------
# 8 GiB capacity warning (reported, never failing)
# ---------------------------------------------------------------------------

def test_address_above_8gib_warns_but_passes(tmp_path):
    over_addr = hex(8 * 1024 ** 3)  # exactly 8 GiB, 64-byte aligned
    records = [(0, "R", over_addr, 0)]
    trace = _write_trace(tmp_path, "over8g.nvt", records)
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    report = _validate(trace, sidecar, "gem5")
    assert report["verdict"] == "PASS"
    assert report["over_8gib_count"] == 1
    assert any("8 GiB" in w for w in report["warnings"])


def test_address_below_8gib_does_not_warn(tmp_path):
    records = [(0, "R", "40", 0)]
    trace = _write_trace(tmp_path, "under8g.nvt", records)
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    report = _validate(trace, sidecar, "gem5")
    assert report["over_8gib_count"] == 0
    assert report["warnings"] == []


# ---------------------------------------------------------------------------
# CLI-level: exit codes, --table, --json
# ---------------------------------------------------------------------------

def _write_pair(tmp_path, name, records, kind):
    trace = _write_trace(tmp_path, f"{name}.nvt", records)
    total = len(records)
    reads = sum(1 for r in records if r[1] == "R")
    writes = total - reads
    first_cycle = records[0][0]
    last_cycle = records[-1][0]
    if kind == "gem5":
        sidecar = _gem5_sidecar(total, reads, writes, first_cycle, last_cycle)
    else:
        sidecar = _scalesim_sidecar(total, reads, writes, first_cycle, last_cycle)
    _write_sidecar(tmp_path, f"{name}.nvt.sidecar.json", sidecar)
    return trace


def test_cli_pass_exits_0(tmp_path, capsys):
    trace = _write_pair(tmp_path, "cli_good", [(0, "R", "40", 0), (10, "W", "80", 0)], "gem5")
    rc = vt.main([str(trace)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "verdict: PASS" in out


def test_cli_hard_failure_exits_1(tmp_path, capsys):
    trace = _write_pair(tmp_path, "cli_bad", [(10, "R", "40", 0), (5, "R", "80", 0)], "gem5")
    rc = vt.main([str(trace)])
    assert rc == 1


def test_cli_missing_sidecar_exits_1(tmp_path, capsys):
    trace = _write_trace(tmp_path, "nosidecar.nvt", [(0, "R", "40", 0)])
    rc = vt.main([str(trace)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "missing sidecar" in err


def test_cli_json_report_written(tmp_path, capsys):
    trace = _write_pair(tmp_path, "cli_json", [(0, "R", "40", 0)], "gem5")
    json_out = tmp_path / "report.json"
    rc = vt.main([str(trace), "--json", str(json_out)])
    assert rc == 0
    data = json.loads(json_out.read_text())
    assert data["verdict"] == "PASS"
    assert data["records"] == 1


def test_cli_table_prints_one_row_per_trace(tmp_path, capsys):
    t1 = _write_pair(tmp_path, "table1", [(0, "R", "40", 0)], "gem5")
    t2 = _write_pair(tmp_path, "table2", [(0, "R", "1", 0)], "scalesim")
    rc = vt.main(["--table", str(t1), str(t2)])
    out = capsys.readouterr().out
    lines = [l for l in out.splitlines() if l.startswith("|")]
    assert len(lines) == 4  # header + separator + 2 rows
    assert str(t1) in lines[2]
    assert str(t2) in lines[3]
    assert rc == 0


def test_cli_table_reports_failure_row_and_nonzero_exit(tmp_path, capsys):
    t1 = _write_pair(tmp_path, "tableok", [(0, "R", "40", 0)], "gem5")
    t2 = _write_trace(tmp_path, "tablebad.nvt", [(0, "R", "40", 0)])  # no sidecar
    rc = vt.main(["--table", str(t1), str(t2)])
    out = capsys.readouterr().out
    assert "FAIL" in out
    assert rc == 1


# ---------------------------------------------------------------------------
# Fix round 1, item 1: --json must not emit bare Infinity for an all-read
# or all-write trace (read_write_ratio must serialize as JSON null).
# ---------------------------------------------------------------------------

def test_json_report_on_all_read_trace_parses_with_strict_json(tmp_path):
    trace = _write_pair(tmp_path, "allread", [(0, "R", "40", 0), (1, "R", "80", 0)], "gem5")
    json_out = tmp_path / "report.json"
    rc = vt.main([str(trace), "--json", str(json_out)])
    assert rc == 0
    text = json_out.read_text()
    assert "Infinity" not in text
    data = json.loads(text)  # a bare `Infinity` token is not valid per RFC 8259
    assert data["read_write_ratio"] is None


def test_json_report_on_real_gpt2_all_read_trace(tmp_path):
    # Reproduces the exact failure the reviewer found on real data.
    real_trace = pathlib.Path(__file__).resolve().parents[1] / "benchmarks" / "gpt2_ifmap.nvt"
    if not real_trace.exists():
        pytest.skip("benchmarks/gpt2_ifmap.nvt not present in this checkout")
    json_out = tmp_path / "gpt2_report.json"
    rc = vt.main([str(real_trace), "--kind", "scalesim", "--json", str(json_out)])
    assert rc == 0
    text = json_out.read_text()
    assert "Infinity" not in text
    json.loads(text)


def test_human_readable_ratio_na_for_no_writes(tmp_path):
    records = [(0, "R", "40", 0), (1, "R", "80", 0)]
    trace = _write_trace(tmp_path, "allread2.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=2, writes=0, first_cycle=0, last_cycle=1)
    report = _validate(trace, sidecar, "gem5")
    assert report["read_write_ratio"] is None
    assert "n/a (no writes)" in vt.format_report(report)


# ---------------------------------------------------------------------------
# Fix round 1, item 2: gem5 sidecar provenance (line-accounting identity and
# companion-line ratio), tested directly against synthetic sidecars.
# ---------------------------------------------------------------------------

def test_provenance_identity_violated_fails():
    sidecar = _gem5_sidecar(total=10, reads=10, writes=0, first_cycle=0, last_cycle=9,
                             broken_identity=True)
    with pytest.raises(vt.ValidationError, match=r"line-accounting identity fails"):
        vt.check_gem5_provenance(sidecar)


def test_provenance_missing_accounting_keys_fails():
    sidecar = _gem5_sidecar(total=10, reads=10, writes=0, first_cycle=0, last_cycle=9,
                             missing_accounting=True)
    with pytest.raises(vt.ValidationError, match=r"missing provenance accounting key"):
        vt.check_gem5_provenance(sidecar)


def test_provenance_ratio_0_1_fails():
    sidecar = _gem5_sidecar(total=100, reads=100, writes=0, first_cycle=0, last_cycle=99,
                             companion_ratio=0.1)
    with pytest.raises(vt.ValidationError, match=r"companion-line ratio 0\.100 is below"):
        vt.check_gem5_provenance(sidecar)


def test_provenance_ratio_3_0_passes():
    sidecar = _gem5_sidecar(total=100, reads=100, writes=0, first_cycle=0, last_cycle=99,
                             companion_ratio=3.0)
    result = vt.check_gem5_provenance(sidecar)
    assert result["companion_ratio"] == pytest.approx(3.0)
    assert result["identity_ok"] is True


def test_provenance_reports_retries_and_malformed_as_warnings(tmp_path):
    records = [(0, "R", "40", 0)]
    trace = _write_trace(tmp_path, "prov_warn.nvt", records)
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0,
                             retries_dropped=2, unmatched_retries=1,
                             malformed_request=1, truncated_final_line=1)
    report = _validate(trace, sidecar, "gem5")
    assert report["verdict"] == "PASS"
    assert report["gem5_provenance"]["retries_dropped"] == 2
    assert report["gem5_provenance"]["unmatched_retries"] == 1
    assert any("malformed_request" in w for w in report["warnings"])
    assert any("truncated_final_line" in w for w in report["warnings"])


def test_provenance_full_validate_trace_surfaces_identity_failure(tmp_path):
    records = [(0, "R", "40", 0), (1, "R", "80", 0)]
    trace = _write_trace(tmp_path, "prov_full.nvt", records)
    sidecar = _gem5_sidecar(total=2, reads=2, writes=0, first_cycle=0, last_cycle=1,
                             broken_identity=True)
    with pytest.raises(vt.ValidationError, match=r"line-accounting identity fails"):
        _validate(trace, sidecar, "gem5")


def test_provenance_not_checked_for_scalesim():
    sidecar = _scalesim_sidecar(records_written=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    assert "dropped_lines" not in sidecar  # scalesim sidecars never carry this


# ---------------------------------------------------------------------------
# Fix round 1, item 3: distinct-64B-line counting via a fixed 16 MiB bitmap
# below 8 GiB, and a small capped set at/above 8 GiB.
# ---------------------------------------------------------------------------

def test_bitmap_distinct_count_matches_expected(tmp_path):
    # Four records, three distinct 64-byte lines (0x40 and 0x80 repeat).
    records = [(0, "R", "40", 0), (1, "R", "40", 0), (2, "R", "80", 0), (3, "R", "c0", 0)]
    trace = _write_trace(tmp_path, "bitmap.nvt", records)
    sidecar = _gem5_sidecar(total=4, reads=4, writes=0, first_cycle=0, last_cycle=3)
    report = _validate(trace, sidecar, "gem5")
    assert report["distinct_64b_lines"] == 3
    assert report["footprint_mib"] == pytest.approx(3 * 64 / (1024 * 1024))
    assert report["distinct_lines_truncated"] is False


def test_capped_distinct_path_above_8gib_warns_and_truncates(tmp_path):
    base = 8 * 1024 ** 3
    # Three distinct 64-byte-aligned lines at/above 8 GiB, cap of 2.
    records = [
        (0, "R", hex(base), 0),
        (1, "R", hex(base + 64), 0),
        (2, "R", hex(base + 128), 0),
    ]
    trace = _write_trace(tmp_path, "capped.nvt", records)
    sidecar = _gem5_sidecar(total=3, reads=3, writes=0, first_cycle=0, last_cycle=2)
    report = _validate(trace, sidecar, "gem5", max_distinct=2)
    assert report["distinct_lines_truncated"] is True
    assert report["over_8gib_count"] == 3
    assert any("max-distinct" in w for w in report["warnings"])


def test_four_traces_footprint_unchanged_by_bitmap_rewrite(tmp_path):
    # Same fixture as the earlier good-gem5 test; the bitmap path must give
    # the identical distinct-line count the old set-based path gave (1 line:
    # addresses 0x40, 0x80, 0xc0 are each their own distinct 64B line -> 3).
    records = [(0, "R", "40", 0), (10, "W", "80", 0), (20, "R", "c0", 0)]
    trace = _write_trace(tmp_path, "unchanged.nvt", records)
    sidecar = _gem5_sidecar(total=3, reads=2, writes=1, first_cycle=0, last_cycle=20)
    report = _validate(trace, sidecar, "gem5")
    assert report["distinct_64b_lines"] == 3


# ---------------------------------------------------------------------------
# Fix round 1, item 4: regression tests for previously-untested hard failures.
# ---------------------------------------------------------------------------

def test_nonexistent_trace_file_fails(tmp_path):
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"unreadable file"):
        _validate(tmp_path / "does_not_exist.nvt", sidecar, "gem5")


def test_non_integer_cycle_text_fails(tmp_path):
    p = tmp_path / "badcycle.nvt"
    p.write_text(f"abc R 0x40 {DATA} 0\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*cycle 'abc'"):
        _validate(p, sidecar, "gem5")


def test_six_field_line_fails(tmp_path):
    p = tmp_path / "sixfields.nvt"
    p.write_text(f"0 R 0x40 {DATA} 0 extra\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1: expected 5 fields, got 6"):
        _validate(p, sidecar, "gem5")


def test_uppercase_hex_address_fails(tmp_path):
    p = tmp_path / "upper.nvt"
    p.write_text(f"0 R 0x4F {DATA} 0\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*address"):
        _validate(p, sidecar, "gem5")


def test_address_without_0x_prefix_fails(tmp_path):
    p = tmp_path / "noprefix.nvt"
    p.write_text(f"0 R 40 {DATA} 0\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*address"):
        _validate(p, sidecar, "gem5")


def test_data_field_non_hex_character_fails_distinctly_from_length(tmp_path):
    bad_data = "g" + "0" * 127  # 128 characters, one non-hex
    p = tmp_path / "nonhexdata.nvt"
    p.write_text(f"0 R 0x40 {bad_data} 0\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"line 1.*non-hex character"):
        _validate(p, sidecar, "gem5")


# ---------------------------------------------------------------------------
# Fix round 1, item 5 (minor): data-field length vs content error messages;
# ambiguous/missing kind signal handling.
# ---------------------------------------------------------------------------

def test_data_field_wrong_length_message_differs_from_content_message(tmp_path):
    p = tmp_path / "shortdata.nvt"
    p.write_text(f"0 R 0x40 {'0' * 127} 0\n")
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    with pytest.raises(vt.ValidationError, match=r"not exactly 128 characters \(got 127\)"):
        _validate(p, sidecar, "gem5")


def test_sidecar_with_both_kind_keys_is_ambiguous_error():
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    sidecar["op_rule"] = "W if 'OFMAP' appears in the input filename (case-insensitive), else R"
    with pytest.raises(vt.ValidationError, match=r"ambiguous"):
        vt.infer_kind(sidecar)


def test_sidecar_with_neither_kind_key_is_unknown_error():
    sidecar = {"parser": "some_other_tool.py"}
    with pytest.raises(vt.ValidationError, match=r"cannot infer trace kind"):
        vt.infer_kind(sidecar)


def test_kind_arg_resolves_ambiguous_sidecar_without_error():
    sidecar = _gem5_sidecar(total=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    sidecar["op_rule"] = "W if 'OFMAP' appears in the input filename (case-insensitive), else R"
    kind, warning = vt.resolve_kind(sidecar, "gem5")
    assert kind == "gem5"
    assert warning is None  # --kind matches one of the two signals; ambiguity resolved silently


def test_kind_arg_contradicting_unambiguous_sidecar_warns_and_wins(tmp_path):
    records = [(0, "R", "1", 0)]  # unaligned: only valid for kind scalesim
    trace = _write_trace(tmp_path, "contradict.nvt", records)
    sidecar = _scalesim_sidecar(records_written=1, reads=1, writes=0, first_cycle=0, last_cycle=0)
    kind, warning = vt.resolve_kind(sidecar, "scalesim")
    assert kind == "scalesim"
    assert warning is None

    # Now force --kind to contradict the sidecar's unambiguous "scalesim" signal.
    kind2, warning2 = vt.resolve_kind(sidecar, "gem5")
    assert kind2 == "gem5"
    assert warning2 is not None
    assert "contradicts" in warning2
