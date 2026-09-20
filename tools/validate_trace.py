"""Standalone validator for NVMain memory traces and their provenance sidecars.

A trace is a text file, one record per line, five whitespace-separated fields:

    <cycle> <R|W> 0x<hexaddr> <128 hex chars of data> <thread id>

Every trace produced by this revision's parsers carries a provenance sidecar
named ``<trace filename>.sidecar.json`` next to it, written by one of:

  - parse_gem5_memctrl.py (gem5 MemCtrl logs: SPEC gcc, SPEC lbm, STREAM).
    Cycles are NVMain global cycles at CPUFreq 3000 MHz, rebased so the first
    record is cycle 0. These traces come from a cached gem5 system, so every
    address must be 64-byte aligned. kind = "gem5". Its sidecar also carries
    a line-by-line accounting of the raw gem5 log (dropped_lines,
    region_excluded_lines, lines_read): see check_gem5_provenance() below,
    added in T3.5 fix round 1 as a stronger guard than the consecutive-
    duplicate check for the retired parser's companion-line defect.
  - parse_trace.py (SCALE-Sim CSVs: GPT-2 IFMAP, AlexNet layer1 IFMAP/OFMAP).
    Addresses are tensor-element granular; about 98.4 percent are NOT 64-byte
    aligned, which is expected and is reported, not failed. These traces are
    short and will never cover the simulation window: the shortfall is
    reported, not failed. kind = "scalesim".

``--kind`` defaults from the sidecar: a top-level "cpufreq_mhz" key is only
ever written by parse_gem5_memctrl.py, so its presence means kind=gem5; a
top-level "op_rule" key is only ever written by parse_trace.py, so its
presence (with "cpufreq_mhz" absent) means kind=scalesim. A sidecar carrying
both keys, or neither, is ambiguous and a hard failure unless --kind is
given; --kind contradicting an otherwise-unambiguous sidecar is a WARNING,
not a failure, and the flag wins.

Standard library only. Importable without side effects: all work happens in
main() and the functions it calls.

Exit codes: 0 pass, 1 validation failure, 2 usage or I/O error.
"""

import argparse
import json
import os
import re
import sys

BYTES_PER_LINE = 64
DATA_FIELD_LEN = 128
GIB = 1024 ** 3
CAPACITY_BYTES = 8 * GIB
DUP_FRACTION_LIMIT_GEM5 = 0.01
COMPANION_RATIO_FLOOR_GEM5 = 0.5

# Distinct-64-byte-line tracking below the 8 GiB capacity uses a fixed-size
# bitmap (one bit per line) instead of an open-ended set, so memory is bounded
# by the address space, not by how many distinct lines a trace happens to
# touch: 2**27 lines below 8 GiB -> 2**27 bits -> 2**24 bytes = 16 MiB.
LOW_LINE_COUNT = CAPACITY_BYTES // BYTES_PER_LINE
LOW_BITMAP_BYTES = LOW_LINE_COUNT // 8

ADDR_RE = re.compile(r"^0x[0-9a-f]+$")
CYCLE_RE = re.compile(r"^\d+$")
HEX_CHARS_RE = re.compile(r"^[0-9a-fA-F]+$")
THREAD_RE = re.compile(r"^-?\d+$")

# Sidecar keys check_gem5_provenance() requires for kind gem5 (parse_gem5_memctrl.py's
# build_sidecar() / DROP_KEYS: dropped_lines is keyed by "access_to",
# "command_for", "responding_to_address", "queue_dump", "retry",
# "non_mem_ctrl", "other_mem_ctrl", "unparsed", "malformed_request",
# "truncated_final_line", "unmatched_retry").
GEM5_PROVENANCE_KEYS = ("dropped_lines", "region_excluded_lines", "lines_read", "records")


class ValidationError(Exception):
    """A hard validation failure. main() reports it and exits 1."""


class UsageError(Exception):
    """A CLI usage or I/O error unrelated to trace content. main() exits 2."""


def infer_kind(sidecar):
    """Infer the trace kind from sidecar keys unique to one parser.

    'cpufreq_mhz' is written only by parse_gem5_memctrl.py -> "gem5".
    'op_rule' is written only by parse_trace.py -> "scalesim".
    A sidecar with both, or neither, is ambiguous: a hard failure here (the
    caller may instead resolve it via resolve_kind() when --kind is given).
    """
    has_gem5 = "cpufreq_mhz" in sidecar
    has_scalesim = "op_rule" in sidecar
    if has_gem5 and has_scalesim:
        raise ValidationError(
            "sidecar carries both 'cpufreq_mhz' (gem5) and 'op_rule' "
            "(scalesim) top-level keys; kind is ambiguous, pass --kind explicitly"
        )
    if has_gem5:
        return "gem5"
    if has_scalesim:
        return "scalesim"
    raise ValidationError(
        "cannot infer trace kind from sidecar: neither 'cpufreq_mhz' "
        "(gem5) nor 'op_rule' (scalesim) top-level key is present; "
        "pass --kind explicitly"
    )


def resolve_kind(sidecar, kind_arg):
    """Resolve the kind to validate against.

    If kind_arg is given, it always wins; but if the sidecar unambiguously
    signals a different kind, a WARNING string is returned alongside it (an
    ambiguous or unknown sidecar signal is silently overridden, since
    --kind was explicitly given to resolve exactly that). If kind_arg is
    None, falls back to infer_kind() (raises on an ambiguous/unknown
    sidecar). Returns (kind, warning_or_None).
    """
    if kind_arg is not None:
        try:
            inferred = infer_kind(sidecar)
        except ValidationError:
            inferred = None
        warning = None
        if inferred is not None and inferred != kind_arg:
            warning = (
                f"WARNING: --kind {kind_arg} contradicts the sidecar's "
                f"unambiguous kind signal ({inferred}); --kind wins"
            )
        return kind_arg, warning
    return infer_kind(sidecar), None


def sidecar_record_fields(sidecar, kind):
    """Return (total, reads, writes, first_cycle, last_cycle, aligned_fraction)
    from the sidecar, using the key layout for `kind`."""
    if kind == "gem5":
        rec = sidecar.get("records")
        if not isinstance(rec, dict):
            raise ValidationError("sidecar missing 'records' object (kind gem5)")
        addr = sidecar.get("addresses")
        if not isinstance(addr, dict):
            raise ValidationError("sidecar missing 'addresses' object (kind gem5)")
        try:
            return (
                rec["total"], rec["reads"], rec["writes"],
                rec["first_cycle"], rec["last_cycle"],
                addr["aligned_64b_fraction"],
            )
        except KeyError as e:
            raise ValidationError(f"sidecar missing expected key {e} (kind gem5)")
    elif kind == "scalesim":
        addr = sidecar.get("addresses")
        if not isinstance(addr, dict):
            raise ValidationError("sidecar missing 'addresses' object (kind scalesim)")
        cyc = sidecar.get("cycles")
        if not isinstance(cyc, dict):
            raise ValidationError("sidecar missing 'cycles' object (kind scalesim)")
        try:
            return (
                sidecar["records_written"], sidecar["reads"], sidecar["writes"],
                cyc["first_cycle"], cyc["last_cycle"],
                addr["aligned_64b_fraction"],
            )
        except KeyError as e:
            raise ValidationError(f"sidecar missing expected key {e} (kind scalesim)")
    else:
        raise UsageError(f"unknown kind {kind!r} (expected 'gem5' or 'scalesim')")


def check_gem5_provenance(sidecar):
    """Cross-check a kind-gem5 sidecar's own line-by-line accounting.

    This is a stronger guard than the consecutive-duplicate check for the
    retired parser's companion-line defect (see parse_gem5_memctrl.py's
    module docstring): that defect turned "Access to" / "Command for" /
    "Responding to Address" follow-up debug lines into extra read records,
    ~4x duplication. The consecutive-duplicate check catches this weakly
    (the retired parser's extra records also carried mangled address
    suffixes, caught by the address regex first); this check instead uses
    parse_gem5_memctrl.py's own accounting identity directly:

        kept (records.total) + sum(dropped_lines.values())
            + sum(region_excluded_lines.values()) == lines_read

    and the companion-line ratio (access_to + command_for +
    responding_to_address) / kept, which is about 3.0 on a healthy gem5
    25.1 log (T3.1 measured ~3.999x total lines per kept record, i.e. 1 kept
    + ~3 companion lines). A ratio below 0.5 means companion lines were
    probably kept as records instead of dropped.

    Raises ValidationError if the accounting keys are missing, the identity
    does not hold, or the ratio is implausibly low. Returns a dict of
    provenance fields for the report otherwise.
    """
    missing = [k for k in GEM5_PROVENANCE_KEYS if k not in sidecar]
    if missing:
        raise ValidationError(
            "gem5 sidecar missing provenance accounting key(s): "
            + ", ".join(missing) + " (a gem5 sidecar without this line-by-line "
            "accounting is not acceptable provenance)"
        )

    dropped = sidecar["dropped_lines"]
    region_excluded = sidecar["region_excluded_lines"]
    lines_read = sidecar["lines_read"]
    records = sidecar["records"]

    if not isinstance(dropped, dict) or not isinstance(region_excluded, dict) \
            or not isinstance(records, dict):
        raise ValidationError(
            "gem5 sidecar provenance keys (dropped_lines / region_excluded_lines "
            "/ records) have an unexpected shape"
        )
    if "total" not in records:
        raise ValidationError("gem5 sidecar 'records' is missing 'total'")

    kept = records["total"]
    dropped_total = sum(dropped.values())
    region_excluded_total = sum(region_excluded.values())
    accounted = kept + dropped_total + region_excluded_total
    if accounted != lines_read:
        raise ValidationError(
            f"gem5 sidecar line-accounting identity fails: kept ({kept}) + "
            f"dropped ({dropped_total}) + region_excluded "
            f"({region_excluded_total}) = {accounted}, expected sidecar "
            f"lines_read {lines_read}"
        )

    companion = (
        dropped.get("access_to", 0)
        + dropped.get("command_for", 0)
        + dropped.get("responding_to_address", 0)
    )
    companion_ratio = (companion / kept) if kept else None
    if kept > 0 and companion_ratio is not None and companion_ratio < COMPANION_RATIO_FLOOR_GEM5:
        raise ValidationError(
            f"gem5 sidecar companion-line ratio {companion_ratio:.3f} is below "
            f"{COMPANION_RATIO_FLOOR_GEM5:.1f} with {kept} kept detailed-region "
            f"record(s); companion lines (Access to / Command for / Responding "
            f"to Address) were probably kept as records instead of dropped "
            f"(a healthy gem5 25.1 log runs about 3.0)"
        )

    return {
        "identity_ok": True,
        "companion_ratio": companion_ratio,
        "retries_dropped": dropped.get("retry", 0),
        "unmatched_retries": dropped.get("unmatched_retry", 0),
        "malformed_request": dropped.get("malformed_request", 0),
        "truncated_final_line": dropped.get("truncated_final_line", 0),
    }


def load_sidecar(sidecar_path):
    if not os.path.exists(sidecar_path):
        raise ValidationError(f"missing sidecar: {sidecar_path}")
    try:
        with open(sidecar_path, "r") as f:
            return json.load(f)
    except OSError as e:
        raise ValidationError(f"missing or unreadable sidecar {sidecar_path}: {e}")
    except json.JSONDecodeError as e:
        raise ValidationError(f"sidecar {sidecar_path} is not valid JSON: {e}")


def validate_trace(trace_path, sidecar, kind, window_ns, cpufreq_mhz,
                    require_window, max_distinct):
    """Stream trace_path, cross-check against sidecar, return a report dict.

    Raises ValidationError on any hard failure. Streams the trace file line
    by line. Memory stays bounded regardless of record count: distinct
    64-byte lines below 8 GiB are tracked with a fixed 16 MiB bitmap (one
    bit per line, 2**27 lines), and lines at or above 8 GiB (already a
    WARNING condition) are tracked with a small set capped at max_distinct.
    """
    total = 0
    reads = 0
    writes = 0
    first_cycle = None
    last_cycle = None
    prev_cycle = None
    aligned_64b = 0
    addr_max = -1
    over_capacity_count = 0
    duplicates = 0
    prev_key = None

    low_bitmap = bytearray(LOW_BITMAP_BYTES)
    high_lines = set()
    high_truncated = False

    reads_in_window = 0
    writes_in_window = 0

    window_cycles = window_ns * cpufreq_mhz // 1000

    try:
        f = open(trace_path, "r")
    except OSError as e:
        raise ValidationError(f"unreadable file {trace_path}: {e}")

    try:
        with f:
            for line_no, raw_line in enumerate(f, start=1):
                line = raw_line.rstrip("\n")
                if not line:
                    continue
                fields = line.split()
                if len(fields) != 5:
                    raise ValidationError(
                        f"line {line_no}: expected 5 fields, got {len(fields)}"
                    )
                cycle_s, op, addr_s, data_s, thread_s = fields

                if op not in ("R", "W"):
                    raise ValidationError(f"line {line_no}: op {op!r} is not R or W")

                if not CYCLE_RE.match(cycle_s):
                    raise ValidationError(
                        f"line {line_no}: cycle {cycle_s!r} is not a non-negative integer"
                    )
                cycle = int(cycle_s)

                if not ADDR_RE.match(addr_s):
                    raise ValidationError(
                        f"line {line_no}: address {addr_s!r} does not match "
                        f"strict lowercase 0x[0-9a-f]+ (or is negative, or "
                        f"missing the 0x prefix, or uses uppercase hex digits)"
                    )
                addr = int(addr_s, 16)

                if len(data_s) != DATA_FIELD_LEN:
                    raise ValidationError(
                        f"line {line_no}: data field is not exactly "
                        f"{DATA_FIELD_LEN} characters (got {len(data_s)})"
                    )
                if not HEX_CHARS_RE.match(data_s):
                    bad_chars = "".join(sorted(set(
                        c for c in data_s if not HEX_CHARS_RE.match(c)
                    )))
                    raise ValidationError(
                        f"line {line_no}: data field is {DATA_FIELD_LEN} "
                        f"characters but contains non-hex character(s): "
                        f"{bad_chars!r}"
                    )

                if not THREAD_RE.match(thread_s):
                    raise ValidationError(
                        f"line {line_no}: thread id {thread_s!r} is not an integer"
                    )

                if prev_cycle is not None and cycle < prev_cycle:
                    raise ValidationError(
                        f"line {line_no}: cycle {cycle} is less than the "
                        f"previous record's cycle {prev_cycle} (non-monotonic)"
                    )
                prev_cycle = cycle

                is_aligned = (addr % BYTES_PER_LINE == 0)
                if kind == "gem5" and not is_aligned:
                    raise ValidationError(
                        f"line {line_no}: address {addr_s} is not "
                        f"{BYTES_PER_LINE}-byte aligned (kind gem5 requires it)"
                    )

                total += 1
                if op == "R":
                    reads += 1
                else:
                    writes += 1
                if first_cycle is None:
                    first_cycle = cycle
                last_cycle = cycle
                if is_aligned:
                    aligned_64b += 1
                if addr > addr_max:
                    addr_max = addr
                if addr >= CAPACITY_BYTES:
                    over_capacity_count += 1
                    if not high_truncated:
                        high_lines.add(addr // BYTES_PER_LINE)
                        if len(high_lines) > max_distinct:
                            high_truncated = True
                else:
                    line64 = addr // BYTES_PER_LINE
                    low_bitmap[line64 >> 3] |= (1 << (line64 & 7))

                key = (cycle, op, addr_s)
                if prev_key is not None and key == prev_key:
                    duplicates += 1
                prev_key = key

                if cycle < window_cycles:
                    if op == "R":
                        reads_in_window += 1
                    else:
                        writes_in_window += 1
    except UnicodeDecodeError as e:
        raise ValidationError(f"unreadable file {trace_path}: {e}")

    if total == 0:
        raise ValidationError("zero records in trace")

    (sc_total, sc_reads, sc_writes, sc_first, sc_last,
     sc_aligned_fraction) = sidecar_record_fields(sidecar, kind)

    mismatches = []
    if total != sc_total:
        mismatches.append(f"record count {total} != sidecar {sc_total}")
    if reads != sc_reads:
        mismatches.append(f"read count {reads} != sidecar {sc_reads}")
    if writes != sc_writes:
        mismatches.append(f"write count {writes} != sidecar {sc_writes}")
    if first_cycle != sc_first:
        mismatches.append(f"first cycle {first_cycle} != sidecar {sc_first}")
    if last_cycle != sc_last:
        mismatches.append(f"last cycle {last_cycle} != sidecar {sc_last}")
    if mismatches:
        raise ValidationError("sidecar disagreement: " + "; ".join(mismatches))

    warnings = []

    if kind == "gem5" and sc_aligned_fraction != 1.0:
        raise ValidationError(
            f"kind gem5 requires sidecar aligned_64b_fraction == 1.0, "
            f"got {sc_aligned_fraction}"
        )

    provenance = None
    if kind == "gem5":
        provenance = check_gem5_provenance(sidecar)
        if provenance["malformed_request"]:
            warnings.append(
                f"WARNING: sidecar dropped_lines.malformed_request = "
                f"{provenance['malformed_request']} (non-zero)"
            )
        if provenance["truncated_final_line"]:
            warnings.append(
                f"WARNING: sidecar dropped_lines.truncated_final_line = "
                f"{provenance['truncated_final_line']} (non-zero)"
            )

    dup_fraction = duplicates / total if total else 0.0
    if kind == "gem5" and dup_fraction > DUP_FRACTION_LIMIT_GEM5:
        raise ValidationError(
            f"duplicate consecutive record fraction {dup_fraction:.4f} exceeds "
            f"{DUP_FRACTION_LIMIT_GEM5:.2f} for kind gem5 "
            f"({duplicates} of {total} records)"
        )

    span_cycles = (last_cycle - first_cycle) if (first_cycle is not None) else 0
    cycle_ns = 1000.0 / cpufreq_mhz
    span_ms = span_cycles * cycle_ns / 1e6
    window_ms = window_ns / 1e6
    shortfall_ms = None
    if span_cycles < window_cycles:
        shortfall_cycles = window_cycles - span_cycles
        shortfall_ms = shortfall_cycles * cycle_ns / 1e6
        if kind == "gem5" and require_window:
            raise ValidationError(
                f"span {span_ms:.3f} ms is shorter than the "
                f"{window_ms:.3f} ms window (shortfall {shortfall_ms:.3f} ms); "
                f"--require-window was given"
            )

    window_seconds = window_ns / 1e9
    if span_cycles >= window_cycles:
        write_rate = writes_in_window / window_seconds if window_seconds else 0.0
        rate_basis = "window"
    else:
        span_seconds = span_cycles * cycle_ns / 1e9
        write_rate = writes_in_window / span_seconds if span_seconds else 0.0
        rate_basis = "span"

    alignment_fraction = aligned_64b / total if total else 0.0
    low_distinct = int.from_bytes(bytes(low_bitmap), "little").bit_count()
    distinct_64b_lines = low_distinct + len(high_lines)
    footprint_mib = distinct_64b_lines * BYTES_PER_LINE / (1024 * 1024)
    read_write_ratio = (reads / writes) if writes else None

    if over_capacity_count:
        warnings.append(
            f"WARNING: {over_capacity_count} record(s) have an address >= "
            f"8 GiB (the full-DIMM capacity); NVMain would wrap or reject them"
        )
    if high_truncated:
        warnings.append(
            f"WARNING: distinct-64B-line counting for addresses >= 8 GiB "
            f"stopped at --max-distinct {max_distinct}; the distinct-line "
            f"count and footprint below are a lower bound for that region"
        )

    report = {
        "trace": trace_path,
        "kind": kind,
        "records": total,
        "reads": reads,
        "writes": writes,
        "read_write_ratio": read_write_ratio,
        "first_cycle": first_cycle,
        "last_cycle": last_cycle,
        "span_ms": span_ms,
        "window_ms": window_ms,
        "window_cycles": window_cycles,
        "shortfall_ms": shortfall_ms,
        "reads_in_window": reads_in_window,
        "writes_in_window": writes_in_window,
        "write_rate_per_sec": write_rate,
        "write_rate_basis": rate_basis,
        "alignment_fraction": alignment_fraction,
        "distinct_64b_lines": distinct_64b_lines,
        "distinct_lines_truncated": high_truncated,
        "footprint_mib": footprint_mib,
        "max_address": addr_max,
        "over_8gib_count": over_capacity_count,
        "duplicate_count": duplicates,
        "duplicate_fraction": dup_fraction,
        "gem5_provenance": provenance,
        "warnings": warnings,
        "verdict": "PASS",
    }
    return report


def format_report(report):
    lines = []
    lines.append(f"trace: {report['trace']} (kind={report['kind']})")
    ratio = report["read_write_ratio"]
    ratio_str = f"{ratio:.3f}" if ratio is not None else "n/a (no writes)"
    lines.append(
        f"records: {report['records']} (reads {report['reads']}, "
        f"writes {report['writes']}, R/W ratio {ratio_str})"
    )
    lines.append(
        f"cycles: first {report['first_cycle']}, last {report['last_cycle']}, "
        f"span {report['span_ms']:.3f} ms"
    )
    lines.append(
        f"window: {report['window_ms']:.3f} ms "
        f"({report['window_cycles']} cycles) -> "
        f"reads_in_window {report['reads_in_window']}, "
        f"writes_in_window {report['writes_in_window']}, "
        f"write rate {report['write_rate_per_sec']:.3f}/s "
        f"(basis: {report['write_rate_basis']})"
    )
    if report["shortfall_ms"] is not None:
        lines.append(f"shortfall: span is {report['shortfall_ms']:.3f} ms short of the window")
    lines.append(
        f"alignment: {report['alignment_fraction']:.6f} 64-byte aligned "
        f"(distinct lines {report['distinct_64b_lines']}, "
        f"footprint {report['footprint_mib']:.3f} MiB)"
    )
    lines.append(
        f"addresses: max 0x{report['max_address']:x}, "
        f"{report['over_8gib_count']} record(s) >= 8 GiB"
    )
    lines.append(
        f"duplicates: {report['duplicate_count']} "
        f"({report['duplicate_fraction']:.6f} of records)"
    )
    prov = report.get("gem5_provenance")
    if prov:
        cr = prov["companion_ratio"]
        cr_str = f"{cr:.3f}" if cr is not None else "n/a"
        lines.append(
            f"gem5 provenance: line-accounting identity OK; companion-line "
            f"ratio {cr_str} per kept record (rule: fail if < "
            f"{COMPANION_RATIO_FLOOR_GEM5:.1f}; healthy gem5 25.1 logs run "
            f"about 3.0); retries dropped {prov['retries_dropped']}, "
            f"unmatched retries {prov['unmatched_retries']}, "
            f"malformed_request {prov['malformed_request']}, "
            f"truncated_final_line {prov['truncated_final_line']}"
        )
    for w in report["warnings"]:
        lines.append(w)
    lines.append(f"verdict: {report['verdict']}")
    return "\n".join(lines)


def table_row(report):
    alignment = f"{report['alignment_fraction']:.4f}"
    return (
        f"| {report['trace']} | {report['records']} | "
        f"{report['reads_in_window']} | {report['writes_in_window']} | "
        f"{report['span_ms']:.3f} | {alignment} | "
        f"{report['footprint_mib']:.3f} | {report['verdict']} |"
    )


TABLE_HEADER = (
    "| trace | records | reads in window | writes in window | span ms | "
    "alignment | footprint MiB | verdict |"
)
TABLE_SEP = "|---|---|---|---|---|---|---|---|"


def build_argparser():
    p = argparse.ArgumentParser(
        description="Validate an NVMain memory trace against its provenance sidecar."
    )
    p.add_argument("traces", nargs="+", help="trace .nvt file(s)")
    p.add_argument("--sidecar", default=None,
                    help="sidecar path (single-trace mode only; default <trace>.sidecar.json)")
    p.add_argument("--window-ns", type=int, default=250_000_000,
                    help="simulation window in ns (default 250,000,000 = 250 ms)")
    p.add_argument("--cpufreq-mhz", type=int, default=3000,
                    help="NVMain CPUFreq in MHz (default 3000)")
    p.add_argument("--kind", choices=("gem5", "scalesim"), default=None,
                    help="trace kind; default: inferred from the sidecar")
    p.add_argument("--json", default=None, metavar="REPORT.json",
                    help="also write a machine-readable report (single-trace mode only)")
    p.add_argument("--require-window", action="store_true",
                    help="for kind gem5, fail if the trace span is shorter than the window")
    p.add_argument("--max-distinct", type=int, default=1_000_000,
                    help="cap on distinct 64-byte lines tracked at/above 8 GiB "
                         "(default 1,000,000; lines below 8 GiB use a fixed-size "
                         "16 MiB bitmap and are never capped)")
    p.add_argument("--table", action="store_true",
                    help="validate several traces and print one Markdown table row per trace")
    return p


def validate_one(trace_path, sidecar_path, args):
    """Run the full validation for a single trace. Returns a report dict with
    verdict PASS, or a dict with verdict FAIL and an 'error' key (never
    raises ValidationError; UsageError still propagates)."""
    sidecar_path = sidecar_path or (trace_path + ".sidecar.json")
    try:
        sidecar = load_sidecar(sidecar_path)
        kind, kind_warning = resolve_kind(sidecar, args.kind)
        report = validate_trace(
            trace_path, sidecar, kind, args.window_ns, args.cpufreq_mhz,
            args.require_window, args.max_distinct,
        )
        report["sidecar"] = sidecar_path
        if kind_warning:
            report["warnings"].insert(0, kind_warning)
        return report
    except ValidationError as e:
        return {
            "trace": trace_path,
            "sidecar": sidecar_path,
            "kind": args.kind or "unknown",
            "records": 0,
            "reads_in_window": 0,
            "writes_in_window": 0,
            "span_ms": 0.0,
            "alignment_fraction": 0.0,
            "footprint_mib": 0.0,
            "verdict": "FAIL",
            "error": str(e),
        }


def _write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def main(argv=None):
    args = build_argparser().parse_args(argv)

    if args.table:
        reports = [validate_one(t, None, args) for t in args.traces]
        print(TABLE_HEADER)
        print(TABLE_SEP)
        any_fail = False
        for report in reports:
            print(table_row(report))
            if report["verdict"] != "PASS":
                any_fail = True
        if args.json:
            try:
                _write_json(args.json, reports)
            except (OSError, ValueError) as e:
                print(f"validate_trace: error: cannot write --json report: {e}", file=sys.stderr)
                return 2
        for report in reports:
            if "error" in report:
                print(f"{report['trace']}: {report['error']}", file=sys.stderr)
        return 1 if any_fail else 0

    if len(args.traces) != 1:
        print("validate_trace: error: pass exactly one trace, or use --table for several",
              file=sys.stderr)
        return 2

    trace_path = args.traces[0]

    try:
        sidecar_path = args.sidecar or (trace_path + ".sidecar.json")
        sidecar = load_sidecar(sidecar_path)
        kind, kind_warning = resolve_kind(sidecar, args.kind)
        report = validate_trace(
            trace_path, sidecar, kind, args.window_ns, args.cpufreq_mhz,
            args.require_window, args.max_distinct,
        )
        report["sidecar"] = sidecar_path
        if kind_warning:
            report["warnings"].insert(0, kind_warning)
    except ValidationError as e:
        print(f"validate_trace: FAIL: {e}", file=sys.stderr)
        return 1
    except UsageError as e:
        print(f"validate_trace: error: {e}", file=sys.stderr)
        return 2

    print(format_report(report))

    if args.json:
        try:
            _write_json(args.json, report)
        except (OSError, ValueError) as e:
            print(f"validate_trace: error: cannot write --json report: {e}", file=sys.stderr)
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
