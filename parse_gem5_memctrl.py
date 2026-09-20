"""Parser: gem5 --debug-flags=MemCtrl log -> NVMain 2.0 trace + provenance sidecar.

Replaces the retired parser (git show 2e8514c:parse_trace.py) that had three
verified defects (documents/MBMM_Book_Typst/research_notes/trace_timebase_investigation.md):
1. divided ticks (ps) by 1000 and called the result an NVMain cycle at CPUFreq 1000,
   while every NVMain config uses CPUFreq 3000, so traces replayed 3x too fast;
2. turned the "Access to", "Command for" and "Responding to Address" follow-up
   debug lines for a single access into extra read records (4x duplication);
3. kept no provenance and deleted the raw log.

Standard library only. Importable without side effects (all work happens in main()).

Usage:
    python3 parse_gem5_memctrl.py --raw raw_trace.txt --stdout gem5_stdout.log \\
        --out benchmarks/<name>.nvt --cpufreq-mhz 3000 --region o3 \\
        --skip-ns 10000000 --sidecar benchmarks/<name>.sidecar.json

Per-controller ordering and settlement, and its true bound (fix round 2)
--------------------------------------------------------------------------
A gem5 log can carry more than one mem_ctrl object (multi-channel configs). A
retry rejection ("Write/Read queue full, not accepting") always belongs to the
controller object printed on ITS OWN line, and only ever resolves the most
recent unresolved `recvTimingReq` from that SAME object - never another
controller's.

Fix round 1 kept a still-open `recvTimingReq` pending until either (a) the
SAME object's next request line arrived, or (b) EOF - and buffered any record
that could not yet be safely emitted in a plain list rescanned on every
insertion. A controller that goes quiet (never issues a following request)
kept its pending record open for the rest of the file, so the deferred-emit
buffer for every OTHER controller's traffic could grow to the size of the
file, and rescanning it on each insertion made the whole parse O(n^2) -
confirmed by fix round 2's review: 2000 lines 0.10s, 4000 0.32s, 8000 1.23s,
16000 5.19s, 200000 lines did not finish in 3 minutes. Fix round 1's docstring
claimed a controller-count bound for this buffer; that claim was false.

The actual, tighter rule (verified against gem5 25.1 src/mem/mem_ctrl.cc
recvTimingReq(), lines 406-485, quoted in task-T3.1-report.md's fix-round-2
section): the entry DPRINTF ("recvTimingReq: request ...", lines 409-411) and
either rejection DPRINTF ("Write/Read queue full, not accepting", lines
444-446 / 464-466) are printed in the SAME synchronous C++ call, with no
`schedule()` (gem5's event-queue scheduler, which would defer to a later
tick) or return-and-reenter between them. A rejection for a given request can
therefore only ever be logged at that request's OWN tick, never later.
`qosSchedule()` (mem_ctrl.cc:439, defined in qos/mem_ctrl.hh) runs earlier in
the same call and uses a different debug flag (QOS, not MemCtrl) for its own
DPRINTFs, and its internal `schedule()` is the QoS priority scheduler
returning a priority value, not gem5's event-queue scheduler - no
tick-deferring path there either.

So: once the parser has seen ANY line (any object, any type, including
bookkeeping lines) whose tick is STRICTLY GREATER than a pending record's own
tick, that pending record's fate is already sealed as ACCEPTED - a rejection
for it, if one were coming, could only have appeared at its own tick, which
has now passed. `pending` (obj -> record) and `resolved_at_current_tick`
(records confirmed accepted, awaiting the tick to fully advance so they can be
emitted in a stable, tick-and-line-order) both hold ONLY records that share
the single most recent tick seen (`current_tick`): the moment a strictly
greater tick appears, the whole batch for the old tick is flushed (any
remaining `pending` entries are implicitly accepted; everything is sorted by
line number and emitted) before the new tick's own lines are processed. The
TRUE bound is therefore the number of request/atomic lines sharing one tick
value, not the number of controllers and not the file size - `max_held_records`
(the actual observed peak of `len(pending) + len(resolved_at_current_tick)`)
is tracked and reported in the sidecar to make this bound checkable rather
than asserted.

A rejection line for object X still only drops X's pending record, and only
if that record is at the SAME tick (which, given the above, is the only tick
X could have an entry in `pending` for by the time the rejection line is
reached - any older entry was already flushed by an intervening tick
advance). If X has no pending record at all when a rejection line for it
arrives, that is an anomaly: gem5's synchronous same-tick guarantee says this
should not happen in a well-formed log, so the parser does not guess - it
counts the line under dropped_lines["unmatched_retry"], warns once (not once
per occurrence, to avoid flooding stderr on a pathological log), and drops
nothing.
"""

import argparse
import hashlib
import json
import os
import re
import sys

PARSER_VERSION = "1.2.1"

# gem5 25.1 src/mem/mem_ctrl.cc format strings this parser depends on:
#   recvAtomic (line ~138):      DPRINTF(MemCtrl, "recvAtomic: %s 0x%x\n", ...)
#   recvTimingReq (line ~410):   DPRINTF(MemCtrl, "recvTimingReq: request %s addr %#x size %d\n", ...)
#   write queue full (line ~445): DPRINTF(MemCtrl, "Write queue full, not accepting\n")
#   read queue full (line ~465):  DPRINTF(MemCtrl, "Read queue full, not accepting\n")
#   Access to (line ~811):       DPRINTF(MemCtrl, "Access to %#x, ready at %lld next burst at %lld.\n", ...)
#   Command for (line ~1009/1101): DPRINTF(MemCtrl, "Command for %#x, issued at %lld.\n", ...)
#   Responding to Address (line ~625): DPRINTF(MemCtrl, "Responding to Address %#x.. \n", ...)
#   queue dumps (lines ~385-400): "===READ QUEUE===", "Read %#x\n", "===RESP QUEUE===",
#                                 "Response %#x\n", "===WRITE QUEUE===", "Write %#x\n"
#
# Confirmed against a real log on 2026-09-20 (see task-T3.1-report.md): the object
# name gem5 actually prints is "system.mem_ctrls" (plural), which still matches
# \S*mem_ctrl\S*. The brief's two regexes matched the real log byte for byte; no
# departure was needed.
#
# One departure found on the real SPEC gcc log (2026-09-20): gem5 formats addresses with
# "%#x", and C's %#x prints the value zero as a bare "0" with no "0x" prefix. A request to
# physical address 0 therefore appears as "addr 0 size 64". The patterns accept that single
# spelling (exactly "0") in addition to "0x<hex>"; anything else is still malformed.

GENERAL_LINE_RE = re.compile(r"^\s*(\d+):\s+(\S+):\s+(.*?)\s*$")
MEM_CTRL_OBJECT_RE = re.compile(r"\S*mem_ctrl\S*")

RECV_ATOMIC_RE = re.compile(
    r"^\s*(\d+):\s+(\S*mem_ctrl\S*):\s+recvAtomic:\s+(\w+)\s+(?:0x([0-9a-fA-F]+)|(0))\s*$"
)
RECV_TIMING_RE = re.compile(
    r"^\s*(\d+):\s+(\S*mem_ctrl\S*):\s+recvTimingReq:\s+request\s+(\w+)\s+addr\s+(?:0x([0-9a-fA-F]+)|(0))\s+size\s+(\d+)\s*$"
)
RETRY_RE = re.compile(r"^(?:Write|Read) queue full, not accepting\s*$")
ACCESS_TO_RE = re.compile(r"^Access to\b")
COMMAND_FOR_RE = re.compile(r"^Command for\b")
RESPONDING_RE = re.compile(r"^Responding to Address\b")
QUEUE_DUMP_RE = re.compile(
    r"^(===READ QUEUE===|===RESP QUEUE===|===WRITE QUEUE===|"
    r"(?:Read|Write) 0x[0-9a-fA-F]+|Response 0x[0-9a-fA-F]+)$"
)
REQUEST_LIKE_RE = re.compile(r"recvAtomic:|recvTimingReq:")

SWITCH_TICK_RE = re.compile(r"Switched CPUS @ tick (\d+)")

WRITE_CMDS = frozenset(
    {"WritebackDirty", "WritebackClean", "WriteReq", "WriteLineReq", "WriteClean"}
)
READ_CMDS = frozenset({"ReadReq", "ReadSharedReq", "ReadExReq"})

PROGRESS_EVERY = 5_000_000

ZERO_DATA = "0" * 128

# dropped_lines keys that are part of the "kept + dropped + region_excluded ==
# total lines read" self-check identity (region_excluded is tracked separately;
# skip_ns_excluded is an informational SUBSET of region_excluded, not summed
# again).
DROP_KEYS = (
    "access_to", "command_for", "responding_to_address", "queue_dump",
    "retry", "non_mem_ctrl", "other_mem_ctrl", "unparsed",
    "malformed_request", "truncated_final_line", "unmatched_retry",
)


class ParseError(Exception):
    """A fatal, user-facing parse failure. main() reports it and exits non-zero."""


def map_op(cmd, line_no):
    if cmd in WRITE_CMDS:
        return "W"
    if cmd in READ_CMDS:
        return "R"
    raise ParseError(
        f"line {line_no}: unknown command '{cmd}' (not in the known "
        f"read/write command sets)"
    )


def round_half_up_scaled(rebased_tick_ps, cpufreq_mhz):
    """cycle = round-half-up(tick_ps * cpufreq_mhz / 1e6), exact integer arithmetic.

    rebased_tick_ps is always >= 0 (monotonic, rebased from the first kept record),
    so plain floor-with-offset gives round-half-up for non-negative inputs.
    """
    numerator = rebased_tick_ps * cpufreq_mhz
    return (numerator + 500_000) // 1_000_000


def read_switch_tick(stdout_path):
    """Return the tick (int, ps) from the first 'Switched CPUS @ tick N' line, or None."""
    if stdout_path is None:
        return None
    with open(stdout_path, "r", errors="replace") as f:
        for line in f:
            m = SWITCH_TICK_RE.search(line)
            if m:
                return int(m.group(1))
    return None


def read_gem5_command(stdout_path):
    """Return the 'command line: ...' line from the gem5 stdout head, or None."""
    if stdout_path is None:
        return None
    with open(stdout_path, "r", errors="replace") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("command line:"):
                return line[len("command line:"):].strip()
    return None


def sha256_first_mb_and_size(raw_path):
    h = hashlib.sha256()
    total = 0
    with open(raw_path, "rb") as f:
        first = f.read(1024 * 1024)
        h.update(first)
        total += len(first)
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
    return h.hexdigest(), total


def classify_drop(tick, obj, msg):
    """Classify a line that is not a keep-line, not a retry line, not malformed."""
    if not MEM_CTRL_OBJECT_RE.search(obj):
        return "non_mem_ctrl"
    if ACCESS_TO_RE.match(msg):
        return "access_to"
    if COMMAND_FOR_RE.match(msg):
        return "command_for"
    if RESPONDING_RE.match(msg):
        return "responding_to_address"
    if QUEUE_DUMP_RE.match(msg):
        return "queue_dump"
    return "other_mem_ctrl"


def region_decision(tick, region, switch_tick, skip_ps):
    """Return (keep: bool, skip_ns_excluded: bool) for a record's raw tick.

    skip_ns_excluded is only ever True for region 'o3': it distinguishes "this
    record is excluded specifically by --skip-ns" from "this record is
    excluded because it is not in the o3/ff window at all".
    """
    if region == "all":
        return True, False
    if region == "ff":
        return (tick < switch_tick), False
    if region == "o3":
        if tick < switch_tick:
            return False, False
        if tick < switch_tick + skip_ps:
            return False, True
        return True, False
    raise ParseError(f"unknown region '{region}'")


def region_ok(tick, region, switch_tick, skip_ps):
    """Backward-compatible boolean wrapper around region_decision()."""
    keep, _ = region_decision(tick, region, switch_tick, skip_ps)
    return keep


def parse(raw_path, cpufreq_mhz, region, switch_tick, skip_ns, out_f,
          progress=True, allow_malformed=0):
    """Stream raw_path, write kept NVMain trace lines to out_f, return a stats dict.

    Raises ParseError on: unknown command, missing switch tick when required,
    non-monotonic ticks, zero kept records, a malformed request line beyond
    --allow-malformed's budget, or a failed internal line-accounting check.
    """
    if region in ("ff", "o3") and switch_tick is None:
        raise ParseError(
            f"--region {region} requires a 'Switched CPUS @ tick N' line in "
            f"--stdout, but none was found"
        )

    skip_ps = skip_ns * 1000

    dropped = {k: 0 for k in DROP_KEYS}
    region_excluded = {"recvAtomic": 0, "recvTimingReq": 0}
    # Informational SUBSET of region_excluded["recvTimingReq"] (or recvAtomic):
    # kept in its own single-key dict (not a plain int) so the nested emit()
    # closure below can mutate it in place without needing `nonlocal`.
    skip_ns_excluded_holder = {"n": 0}

    state = {
        "offset": None,
        "prev_tick": None,
        "total": 0,
        "reads": 0,
        "writes": 0,
        "first_cycle": None,
        "last_cycle": None,
        "addr_min": None,
        "addr_max": None,
        "aligned_64b": 0,
        "size_histogram": {},
        "by_object": {},
        "max_held_records": 0,
    }

    def emit(tick, op, addr, size, line_no, line_type, obj):
        keep, skip_excl = region_decision(tick, region, switch_tick, skip_ps)
        if not keep:
            region_excluded[line_type] += 1
            if skip_excl:
                skip_ns_excluded_holder["n"] += 1
            return
        if state["offset"] is None:
            state["offset"] = tick
        if state["prev_tick"] is not None and tick < state["prev_tick"]:
            raise ParseError(
                f"line {line_no}: non-monotonic tick {tick} follows "
                f"{state['prev_tick']}"
            )
        state["prev_tick"] = tick
        rebased = tick - state["offset"]
        cycle = round_half_up_scaled(rebased, cpufreq_mhz)
        out_f.write(f"{cycle} {op} 0x{addr:x} {ZERO_DATA} 0\n")
        state["total"] += 1
        if op == "R":
            state["reads"] += 1
        else:
            state["writes"] += 1
        if state["first_cycle"] is None:
            state["first_cycle"] = cycle
        state["last_cycle"] = cycle
        if state["addr_min"] is None or addr < state["addr_min"]:
            state["addr_min"] = addr
        if state["addr_max"] is None or addr > state["addr_max"]:
            state["addr_max"] = addr
        if addr % 64 == 0:
            state["aligned_64b"] += 1
        if size is not None:
            state["size_histogram"][size] = state["size_histogram"].get(size, 0) + 1
        by_obj = state["by_object"].setdefault(obj, {"total": 0, "reads": 0, "writes": 0})
        by_obj["total"] += 1
        by_obj["reads" if op == "R" else "writes"] += 1

    # pending: obj -> record dict, holding ONLY records at `current_tick` (a
    # rejection can only ever apply to a same-tick pending; see the module
    # docstring). resolved_at_current_tick: records already confirmed
    # accepted (recvAtomic, or a recvTimingReq whose own object issued a new
    # request) but held back until `current_tick`'s batch is flushed, so
    # output stays in stable (tick, original line order). Both structures
    # hold only the current tick's records; their combined size is the true
    # bound, tracked live as max_held_records.
    pending = {}
    resolved_at_current_tick = []
    current_tick_holder = {"tick": None}
    unmatched_retry_warned = [False]

    def note_held_size():
        n = len(pending) + len(resolved_at_current_tick)
        if n > state["max_held_records"]:
            state["max_held_records"] = n

    def flush_current_tick_batch():
        # Everything still in `pending` never saw a same-tick rejection, so
        # by the time the tick advances it is settled as accepted.
        for obj, rec in pending.items():
            resolved_at_current_tick.append(rec)
        pending.clear()
        note_held_size()
        resolved_at_current_tick.sort(key=lambda r: r["line_no"])
        for rec in resolved_at_current_tick:
            emit(rec["tick"], rec["op"], rec["addr"], rec["size"], rec["line_no"], rec["line_type"], rec["obj"])
        resolved_at_current_tick.clear()

    def advance_to(tick_now):
        t = current_tick_holder["tick"]
        if t is not None and tick_now > t:
            flush_current_tick_batch()
        if t is None or tick_now > t:
            current_tick_holder["tick"] = tick_now

    def flush_object_pending(obj):
        # A brand new request/atomic line for object X proves X's previous
        # pending record (if any) already concluded - it cannot still be
        # awaiting a same-tick rejection decision, whether that old record's
        # tick was strictly earlier (already handled by advance_to()) or, in
        # the edge case of two same-tick lines for one object, equal.
        old = pending.pop(obj, None)
        if old is not None:
            resolved_at_current_tick.append(old)
            note_held_size()

    line_no = 0
    malformed_seen = 0
    with open(raw_path, "r", errors="replace") as f:
        for raw_line in f:
            line_no += 1

            if progress and line_no % PROGRESS_EVERY == 0:
                print(f"parse_gem5_memctrl: processed {line_no} lines...", file=sys.stderr)

            if not raw_line.endswith("\n"):
                # A raw log missing its final newline was truncated mid-write
                # (killed gem5, full disk, ...). The last token(s) may be cut,
                # so this line could parse as a syntactically valid but wrong
                # record. Never emit it, and don't use it to advance the tick.
                dropped["truncated_final_line"] += 1
                print(
                    f"parse_gem5_memctrl: warning: line {line_no} has no "
                    f"trailing newline (truncated raw log); dropping it",
                    file=sys.stderr,
                )
                continue

            line = raw_line.rstrip("\n")

            m = RECV_ATOMIC_RE.match(line)
            if m:
                obj = m.group(2)
                tick = int(m.group(1))
                advance_to(tick)
                flush_object_pending(obj)
                cmd = m.group(3)
                addr = int(m.group(4), 16) if m.group(4) is not None else 0
                op = map_op(cmd, line_no)
                resolved_at_current_tick.append({
                    "tick": tick, "op": op, "addr": addr, "size": None,
                    "line_no": line_no, "line_type": "recvAtomic", "obj": obj,
                })
                note_held_size()
                continue

            m = RECV_TIMING_RE.match(line)
            if m:
                obj = m.group(2)
                tick = int(m.group(1))
                advance_to(tick)
                flush_object_pending(obj)
                cmd = m.group(3)
                addr = int(m.group(4), 16) if m.group(4) is not None else 0
                size = int(m.group(6))
                op = map_op(cmd, line_no)
                pending[obj] = {
                    "tick": tick, "op": op, "addr": addr, "size": size,
                    "line_no": line_no, "line_type": "recvTimingReq", "obj": obj,
                }
                note_held_size()
                continue

            gm = GENERAL_LINE_RE.match(line)
            if not gm:
                dropped["unparsed"] += 1
                continue
            tick_s, obj, msg = gm.group(1), gm.group(2), gm.group(3)
            tick_now = int(tick_s)
            advance_to(tick_now)

            if MEM_CTRL_OBJECT_RE.search(obj) and REQUEST_LIKE_RE.search(msg):
                # Looked like a request line (contains "recvAtomic:" or
                # "recvTimingReq:") but failed the strict format regex - e.g. a
                # non-hex address from a damaged byte. A silently lost request
                # is worse than a stopped parse, so this is fatal by default.
                dropped["malformed_request"] += 1
                malformed_seen += 1
                print(
                    f"parse_gem5_memctrl: warning: line {line_no}: malformed "
                    f"request line (matched recvAtomic:/recvTimingReq: but "
                    f"failed the strict format): {line!r}",
                    file=sys.stderr,
                )
                if malformed_seen > allow_malformed:
                    raise ParseError(
                        f"line {line_no}: malformed request line exceeds "
                        f"--allow-malformed {allow_malformed} (see the "
                        f"warning above for the raw line)"
                    )
                continue

            if RETRY_RE.match(msg):
                # advance_to(tick_now) already ran above, so if `obj` still
                # has a pending record at this point it is guaranteed (by the
                # same-tick source guarantee - see the module docstring) to
                # be at exactly tick_now: any older entry for this object was
                # already flushed as accepted by advance_to() before we got
                # here. Two distinct raw lines are involved in a genuine
                # rejection: the earlier recvTimingReq request line (X,
                # accounted for via dropped["retry"], its deferred fate
                # finally decided) and this "queue full, not accepting" line
                # (Y) itself (a bookkeeping line like its sibling "Read/Write
                # queue limit ...", counted under other_mem_ctrl) - so both
                # get one accounting unit, keeping the line-count identity
                # exact.
                if obj in pending:
                    del pending[obj]
                    dropped["retry"] += 1
                    dropped["other_mem_ctrl"] += 1
                else:
                    # No matching same-tick pending for this object. Given
                    # the synchronous same-tick guarantee this should never
                    # happen in a well-formed log; do not guess which record
                    # (if any) it might apply to. Count it distinctly and
                    # warn once.
                    dropped["unmatched_retry"] += 1
                    if not unmatched_retry_warned[0]:
                        print(
                            f"parse_gem5_memctrl: warning: line {line_no}: "
                            f"a queue-full rejection for {obj} has no "
                            f"matching same-tick pending request (already "
                            f"resolved, or never seen); counted as an "
                            f"anomaly, nothing dropped for it (further "
                            f"occurrences are not individually warned)",
                            file=sys.stderr,
                        )
                        unmatched_retry_warned[0] = True
                continue

            bucket = classify_drop(tick_s, obj, msg)
            dropped[bucket] += 1

    # EOF: the final tick's batch never saw a "later tick" line to trigger
    # advance_to(), so flush it explicitly. Everything remaining in `pending`
    # never saw a rejection and is accepted.
    flush_current_tick_batch()

    skip_ns_excluded = skip_ns_excluded_holder["n"]

    # Self-check: every raw line read must be accounted for exactly once,
    # either as a kept (emitted) record, a dropped line, or a region-excluded
    # request line. skip_ns_excluded is an informational subset of
    # region_excluded["recvTimingReq"] (or recvAtomic) and is NOT added again.
    accounted = state["total"] + sum(dropped.values()) + sum(region_excluded.values())
    if accounted != line_no:
        raise ParseError(
            f"internal accounting error: kept ({state['total']}) + dropped "
            f"({sum(dropped.values())}) + region_excluded "
            f"({sum(region_excluded.values())}) = {accounted}, expected "
            f"{line_no} total lines read. This is a parser bug, not a data "
            f"problem; please report it."
        )

    if state["total"] == 0:
        raise ParseError(
            "zero records kept after parsing and region filtering; check "
            "--region/--skip-ns and the raw log"
        )

    return {
        "dropped": dropped,
        "region_excluded": region_excluded,
        "skip_ns_excluded": skip_ns_excluded,
        "records": state,
        "rebase_offset_ticks": state["offset"],
        "lines_read": line_no,
        "malformed_seen": malformed_seen,
        "max_held_records": state["max_held_records"],
    }


def build_sidecar(args, argv, raw_sha256, raw_size, gem5_command, switch_tick, result):
    state = result["records"]
    unit = f"cycle = 1/{args.cpufreq_mhz} us (CPUFreq {args.cpufreq_mhz} MHz)"
    return {
        "parser": "parse_gem5_memctrl.py",
        "parser_version": PARSER_VERSION,
        "argv": list(argv),
        "source": {
            "raw_log": args.raw,
            "raw_log_sha256_first_1mb": raw_sha256,
            "raw_log_size_bytes": raw_size,
            "gem5_stdout": args.stdout,
            "gem5_command": gem5_command,
        },
        "region": {
            "mode": args.region,
            "switch_tick_ps": switch_tick,
            "skip_ns": args.skip_ns,
            "rebase_offset_ticks": result["rebase_offset_ticks"],
        },
        "cpufreq_mhz": args.cpufreq_mhz,
        "unit": unit,
        "records": {
            "total": state["total"],
            "reads": state["reads"],
            "writes": state["writes"],
            "first_cycle": state["first_cycle"],
            "last_cycle": state["last_cycle"],
            "controller_objects": sorted(state["by_object"].keys()),
            "by_object": state["by_object"],
        },
        "addresses": {
            "min": None if state["addr_min"] is None else hex(state["addr_min"]),
            "max": None if state["addr_max"] is None else hex(state["addr_max"]),
            "aligned_64b_fraction": (
                state["aligned_64b"] / state["total"] if state["total"] else 0.0
            ),
            "size_histogram": {str(k): v for k, v in sorted(state["size_histogram"].items())},
        },
        "dropped_lines": result["dropped"],
        "region_excluded_lines": result["region_excluded"],
        "skip_ns_excluded_lines": result["skip_ns_excluded"],
        "lines_read": result["lines_read"],
        "allow_malformed": args.allow_malformed,
        "malformed_lines_seen": result["malformed_seen"],
        "max_held_records": result["max_held_records"],
    }


def build_argparser():
    p = argparse.ArgumentParser(
        description="Parse a gem5 --debug-flags=MemCtrl log into an NVMain trace with a provenance sidecar."
    )
    p.add_argument("--raw", required=True, help="gem5 --debug-file MemCtrl raw log")
    p.add_argument("--stdout", default=None, help="gem5 stdout/stderr capture (for the switch tick and command line)")
    p.add_argument("--out", required=True, help="output .nvt trace path")
    p.add_argument("--cpufreq-mhz", type=int, default=3000, help="NVMain CPUFreq in MHz (default 3000)")
    p.add_argument("--region", choices=("all", "ff", "o3"), default="all", help="which region of the log to keep")
    p.add_argument("--skip-ns", type=int, default=0, help="ns after the switch tick to additionally skip for --region o3")
    p.add_argument("--sidecar", required=True, help="output provenance sidecar .json path")
    p.add_argument("--force", action="store_true", help="overwrite an existing --out or --sidecar")
    p.add_argument(
        "--allow-malformed", type=int, default=0, metavar="N",
        help="tolerate up to N malformed request lines instead of failing (default 0)",
    )
    return p


def _remove_if_exists(path):
    try:
        if path is not None and os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


def main(argv=None):
    effective_argv = sys.argv[1:] if argv is None else list(argv)
    args = build_argparser().parse_args(argv)

    if not args.force:
        existing = [p for p in (args.out, args.sidecar) if os.path.exists(p)]
        if existing:
            print(
                "parse_gem5_memctrl: error: refusing to overwrite existing "
                f"output(s) without --force: {', '.join(existing)}",
                file=sys.stderr,
            )
            return 1

    tmp_out = args.out + ".tmp"

    try:
        switch_tick = read_switch_tick(args.stdout)
        gem5_command = read_gem5_command(args.stdout)
        raw_sha256, raw_size = sha256_first_mb_and_size(args.raw)

        with open(tmp_out, "w") as out_f:
            result = parse(
                args.raw, args.cpufreq_mhz, args.region, switch_tick,
                args.skip_ns, out_f, allow_malformed=args.allow_malformed,
            )

        sidecar = build_sidecar(args, effective_argv, raw_sha256, raw_size, gem5_command, switch_tick, result)
        with open(args.sidecar, "w") as sc_f:
            json.dump(sidecar, sc_f, indent=2, sort_keys=True)
            sc_f.write("\n")

        # Only now does a complete .nvt exist at its real name - after its
        # sidecar was written successfully. os.replace is atomic on the same
        # filesystem, so a crash between here and the write above never
        # leaves a complete-looking .nvt without a sidecar.
        os.replace(tmp_out, args.out)

    except ParseError as e:
        print(f"parse_gem5_memctrl: error: {e}", file=sys.stderr)
        _remove_if_exists(tmp_out)
        return 1
    except Exception as e:
        print(
            f"parse_gem5_memctrl: error: unexpected failure: "
            f"{type(e).__name__}: {e}",
            file=sys.stderr,
        )
        _remove_if_exists(tmp_out)
        return 1

    print(
        f"parse_gem5_memctrl: wrote {result['records']['total']} records to {args.out}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
