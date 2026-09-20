"""Parser: SCALE-Sim DRAM trace CSV -> NVMain 2.0 trace + provenance sidecar.

Replaces the defective column-1-only reading of the previous version (see
documents/MBMM_Book_Typst/research_notes/trace_timebase_investigation.md,
section 7, "AI traces"), which had two verified defects:
1. SCALE-Sim's `Bandwidth: N` rows carry up to N addresses (one CSV row is N
   DRAM accesses made in the same cycle), but the old parser kept only the
   FIRST address column, undercounting `gpt2_ifmap.nvt` by about 10x (6,554
   records against 65,540 DRAM reads in SCALE-Sim's own
   DETAILED_ACCESS_REPORT.csv).
2. SCALE-Sim pads short/unused address slots with -1. The old parser wrote
   that straight through as address `-0x1` (31 percent of
   `alexnet_layer1_ifmap.nvt`).

What SCALE-Sim's own source says about the CSV (verified 2026-09-20):
  - simulators/SCALE-Sim/scalesim/single_layer_sim.py:315-324 names the file
    "<layer dir>/IFMAP_DRAM_TRACE.csv" etc. and writes it via
    memory_system.print_ifmap_dram_trace(), which is
    simulators/SCALE-Sim/scalesim/memory/double_buffered_scratchpad_mem.py:725-743
    -> self.ifmap_buf.print_trace(filename).
  - simulators/SCALE-Sim/scalesim/memory/read_buffer.py:578-586 print_trace()
    writes self.trace_matrix with `np.savetxt(filename, self.trace_matrix,
    fmt='%s', delimiter=",")`. No header row.
  - trace_matrix is built at read_buffer.py:426
    (`np.column_stack((response_cycles_arr, prefetch_requests))`) and
    concatenated per steady-state batch at line 522. Column 0 is the RESPONSE
    cycle of each batch, i.e. issue cycle plus the port latency
    (read_port.py:82, `out_cycles_arr = incoming_cycles_arr + self.latency`),
    float-valued from arithmetic on cycle counters; the parser only needs it
    to be non-decreasing; columns 1..N are up to N addresses (N = the config's
    `Bandwidth`) requested at that cycle, in a fixed-width matrix.
  - Unused address slots are padded with -1: read_buffer.py:154
    (`self.fetch_matrix = np.ones((num_lines, self.req_gen_bandwidth)) * -1`),
    :404, :495, :502 (`prefetch_requests[...] = -1`).
  - Cycles CAN be negative at the start: read_buffer.py's
    prefetch_active_buffer() computes the initial prefetch batch's cycles as
    `-1 * (num_lines - start_cycle - (i - latency))` (line ~414), which is
    negative for early rows and increases (less negative, then positive)
    with i - i.e. non-decreasing. Confirmed against a real file
    (benchmarks/ml_trace_output/GoogleTPU_v1_os/layer0/IFMAP_DRAM_TRACE.csv):
    first row's cycle is -6554.0, rows increase monotonically to 0 and
    beyond. Steady-state batches (read_buffer.py:508-509,
    `cycles_arr[i][0] = self.last_prefetch_cycle + i + 1`) are strictly
    increasing by construction, so the whole file is non-decreasing in
    cycle. This parser asserts that (fatal if violated) rather than assuming
    it.
  - Column count is fixed per file (a numpy matrix), equal to the
    architecture config's Bandwidth (10 for configs/google.cfg, used for
    both the GPT-2 and AlexNet regenerations in this revision).

Standard library only. Importable without side effects (all work happens in
main()). CLI is unchanged from the previous version so existing callers
(README.md; no code caller found in this repo outside simulators/ and
archive/ as of 2026-09-20) keep working:

    python3 parse_trace.py <input.csv> <output.nvt> [--scalesim-cmd CMD]
                            [--sidecar PATH] [--force]
                            [--note KEY=VALUE [--note KEY=VALUE ...]]

--note is repeatable and merges arbitrary extra KEY=VALUE fields into the
sidecar's top level (e.g. to record which SCALE-Sim output folder / layer a
trace came from); a key that collides with a field the parser itself writes
is rejected.
"""

import argparse
import hashlib
import json
import os
import re
import sys

PARSER_VERSION = "2.1.0"

# Top-level sidecar keys the parser itself writes; a --note may not clobber
# one of these (see parse_notes()).
RESERVED_SIDECAR_KEYS = frozenset({
    "parser", "parser_version", "argv", "source", "unit", "op_rule", "op",
    "rows_read", "records_written", "padding_skipped", "reads", "writes",
    "cycles", "addresses",
})

# NVMain requires a 128-character dummy hex string for SLC/MLC padding.
DUMMY_DATA = "0" * 128

# A header line SCALE-Sim itself never writes (print_trace() has no header),
# but older/foreign CSVs might; skip it defensively, same as the retired
# parser did.
HEADER_HINT_RE = re.compile(r"cycle|address", re.IGNORECASE)

# Heuristic sniff for a gem5 --debug-flags=MemCtrl log accidentally handed to
# this tool: gem5 debug lines look like "<tick>: <object>: <message>" -
# nothing resembling a comma-separated numeric CSV row. See
# parse_gem5_memctrl.py, the tool that actually handles this format.
GEM5_LINE_RE = re.compile(r"^\s*\d+:\s+\S+:\s+")
GEM5_KEYWORD_RE = re.compile(r"recvTimingReq:|recvAtomic:|mem_ctrl")


class ParseError(Exception):
    """A fatal, user-facing parse failure. main() reports it and exits non-zero."""


def sniff_gem5_memctrl_log(path, max_lines=20):
    """Return True if `path` looks like a gem5 --debug-flags=MemCtrl log, not a CSV."""
    checked = 0
    with open(path, "r", errors="replace") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line:
                continue
            checked += 1
            if GEM5_LINE_RE.match(line) and GEM5_KEYWORD_RE.search(line):
                return True
            if checked >= max_lines:
                break
    return False


def sha256_and_size(path):
    h = hashlib.sha256()
    total = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


def parse_notes(note_args):
    """Turn repeated --note KEY=VALUE strings into a dict merged into the
    sidecar's top level. Raises ValueError (a CLI usage error, not a
    ParseError about the CSV) on a malformed note, a duplicate key, or a
    key that collides with a field the parser itself writes."""
    notes = {}
    for raw in note_args:
        if "=" not in raw:
            raise ValueError(f"--note {raw!r} is not KEY=VALUE (missing '=')")
        key, value = raw.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"--note {raw!r} has an empty key")
        if key in RESERVED_SIDECAR_KEYS:
            raise ValueError(
                f"--note key {key!r} collides with a sidecar field the "
                f"parser itself writes; choose a different key"
            )
        if key in notes:
            raise ValueError(f"--note key {key!r} was given more than once")
        notes[key] = value
    return notes


def parse_int_field(field, line_no, what):
    """Parse a CSV field as an integer, tolerating SCALE-Sim's float formatting
    ("1024.0", "-1.0"). Raises ParseError naming the row on anything else."""
    field = field.strip()
    try:
        if field.lower().startswith("0x") or field.lower().startswith("-0x"):
            return int(field, 16)
        # int(float(...)) accepts "1024", "1024.0", "-1", "-1.0" but rejects
        # anything non-numeric (empty string, garbage) with ValueError.
        as_float = float(field)
        if as_float != int(as_float):
            raise ParseError(
                f"row at line {line_no}: {what} {field!r} is not an integer value"
            )
        return int(as_float)
    except ValueError:
        raise ParseError(
            f"row at line {line_no}: {what} {field!r} is not a valid integer"
        )


def parse(input_file, out_f, default_op):
    """Stream input_file, write kept NVMain trace lines to out_f, return a stats dict.

    Raises ParseError on: a gem5 MemCtrl log mistakenly handed in, a
    non-integer address field, non-monotonic cycles after rebasing, or zero
    rows read.
    """
    state = {
        "rows_read": 0,
        "records_written": 0,
        "padding_skipped": 0,
        "reads": 0,
        "writes": 0,
        "first_cycle": None,
        "last_cycle": None,
        "addr_min": None,
        "addr_max": None,
        "aligned_64b": 0,
        "lines_touched": set(),
        "same_line_as_prev": 0,
        "rebase_offset": 0,
    }

    offset = None
    prev_cycle = None
    prev_line = None
    line_no = 0

    with open(input_file, "r") as fin:
        for raw_line in fin:
            line_no += 1
            line = raw_line.strip()
            if not line:
                continue
            if HEADER_HINT_RE.search(line) and not re.match(r"^-?[\d.]", line):
                # A textual header row (SCALE-Sim itself never writes one,
                # but tolerate a foreign/manually-edited CSV that does).
                continue

            parts = [p for p in line.split(",") if p.strip() != ""]
            if len(parts) < 1:
                continue

            raw_cycle = parse_int_field(parts[0], line_no, "cycle")
            state["rows_read"] += 1

            if offset is None:
                offset = -raw_cycle if raw_cycle < 0 else 0
                state["rebase_offset"] = offset
            cycle = raw_cycle + offset

            if prev_cycle is not None and cycle < prev_cycle:
                raise ParseError(
                    f"row at line {line_no}: non-monotonic cycle {cycle} "
                    f"(rebased) follows {prev_cycle}"
                )
            prev_cycle = cycle

            for col_idx, addr_field in enumerate(parts[1:], start=1):
                addr = parse_int_field(addr_field, line_no, f"address column {col_idx}")
                if addr < 0:
                    state["padding_skipped"] += 1
                    continue

                out_f.write(f"{cycle} {default_op} {hex(addr)} {DUMMY_DATA} 0\n")
                state["records_written"] += 1
                if default_op == "W":
                    state["writes"] += 1
                else:
                    state["reads"] += 1
                if state["first_cycle"] is None:
                    state["first_cycle"] = cycle
                state["last_cycle"] = cycle
                if state["addr_min"] is None or addr < state["addr_min"]:
                    state["addr_min"] = addr
                if state["addr_max"] is None or addr > state["addr_max"]:
                    state["addr_max"] = addr
                if addr % 64 == 0:
                    state["aligned_64b"] += 1
                line64 = addr // 64
                state["lines_touched"].add(line64)
                if prev_line is not None and line64 == prev_line:
                    state["same_line_as_prev"] += 1
                prev_line = line64

    if state["rows_read"] == 0:
        raise ParseError(f"{input_file}: no data rows found (empty or all-header CSV)")

    return state


def build_sidecar(args, argv, source_sha256, source_size, default_op, state, notes):
    total = state["records_written"]
    sidecar = {
        "parser": "parse_trace.py",
        "parser_version": PARSER_VERSION,
        "argv": list(argv),
        "source": {
            "csv_path": args.input,
            "csv_sha256": source_sha256,
            "csv_size_bytes": source_size,
            "scalesim_command": args.scalesim_cmd,
        },
        "unit": (
            "1 SCALE-Sim cycle = 1 NVMain cycle at CPUFreq 3000 (0.333 ns); "
            "SCALE-Sim's own plots assume 2.4 GHz"
        ),
        "op_rule": (
            "W if 'OFMAP' appears in the input filename (case-insensitive), else R"
        ),
        "op": default_op,
        "rows_read": state["rows_read"],
        "records_written": total,
        "padding_skipped": state["padding_skipped"],
        "reads": state["reads"],
        "writes": state["writes"],
        "cycles": {
            "rebase_offset": state["rebase_offset"],
            "first_cycle": state["first_cycle"],
            "last_cycle": state["last_cycle"],
        },
        "addresses": {
            "min": None if state["addr_min"] is None else hex(state["addr_min"]),
            "max": None if state["addr_max"] is None else hex(state["addr_max"]),
            "span_bytes": (
                None if state["addr_min"] is None
                else state["addr_max"] - state["addr_min"]
            ),
            "aligned_64b_fraction": (state["aligned_64b"] / total) if total else 0.0,
            "distinct_64b_lines": len(state["lines_touched"]),
            "records_sharing_line_with_previous": state["same_line_as_prev"],
        },
    }
    sidecar.update(notes)
    return sidecar


def build_argparser():
    p = argparse.ArgumentParser(
        description="Parse a SCALE-Sim DRAM trace CSV into an NVMain trace with a provenance sidecar."
    )
    p.add_argument("input", help="SCALE-Sim *_DRAM_TRACE.csv input")
    p.add_argument("output", help="output .nvt trace path")
    p.add_argument(
        "--scalesim-cmd", default=None,
        help="the exact SCALE-Sim command that produced the input CSV (recorded in the sidecar)",
    )
    p.add_argument(
        "--sidecar", default=None,
        help="output provenance sidecar .json path (default: <output>.sidecar.json)",
    )
    p.add_argument("--force", action="store_true", help="overwrite an existing output or sidecar")
    p.add_argument(
        "--note", action="append", default=[], metavar="KEY=VALUE",
        help="repeatable extra key=value pair merged into the sidecar's top level "
             "(e.g. --note scalesim_layer_folder=layer1); the key may not collide "
             "with a field the parser itself writes",
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

    sidecar_path = args.sidecar or (args.output + ".sidecar.json")

    try:
        notes = parse_notes(args.note)
    except ValueError as e:
        print(f"parse_trace: error: {e}", file=sys.stderr)
        return 1

    if not os.path.exists(args.input):
        print(f"parse_trace: error: input not found: {args.input}", file=sys.stderr)
        return 1

    if sniff_gem5_memctrl_log(args.input):
        print(
            "parse_trace: error: this looks like a gem5 --debug-flags=MemCtrl "
            "log, not a SCALE-Sim DRAM trace CSV. That format is handled by "
            "parse_gem5_memctrl.py, not this tool. Refusing to parse it here "
            "to avoid re-applying this parser's old, defective gem5 rule.",
            file=sys.stderr,
        )
        return 1

    if not args.force:
        existing = [p for p in (args.output, sidecar_path) if os.path.exists(p)]
        if existing:
            print(
                "parse_trace: error: refusing to overwrite existing "
                f"output(s) without --force: {', '.join(existing)}",
                file=sys.stderr,
            )
            return 1

    default_op = "W" if "OFMAP" in args.input.upper() else "R"
    tmp_out = args.output + ".tmp"

    print(f">>> Translating SCALE-Sim trace {args.input} to NVMain format...")

    try:
        source_sha256, source_size = sha256_and_size(args.input)

        with open(tmp_out, "w") as out_f:
            state = parse(args.input, out_f, default_op)

        sidecar = build_sidecar(args, effective_argv, source_sha256, source_size, default_op, state, notes)
        with open(sidecar_path, "w") as sc_f:
            json.dump(sidecar, sc_f, indent=2, sort_keys=True)
            sc_f.write("\n")

        # Only now does a complete .nvt exist at its real name - after its
        # sidecar was written successfully. os.replace is atomic on the same
        # filesystem, so a crash between here and the write above never
        # leaves a complete-looking .nvt without a sidecar. The input file
        # is never touched.
        os.replace(tmp_out, args.output)

    except ParseError as e:
        print(f"parse_trace: error: {e}", file=sys.stderr)
        _remove_if_exists(tmp_out)
        return 1
    except Exception as e:
        print(
            f"parse_trace: error: unexpected failure: {type(e).__name__}: {e}",
            file=sys.stderr,
        )
        _remove_if_exists(tmp_out)
        return 1

    print(
        f"SUCCESS: Created stable NVMain trace at {args.output} with "
        f"{state['records_written']} memory accesses "
        f"({state['padding_skipped']} padding slots skipped)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
