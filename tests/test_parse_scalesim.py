"""T3.3: SCALE-Sim DRAM trace CSV -> NVMain trace parser, with provenance sidecar.

Fixture: tests/fixtures/scalesim_sample.csv
    -3,4096,-1
    5,1024,1088,-1,-1
    7,100,101,102,103,104,105,106,107,108,-1

Three rows, matching the task brief's example:
  - row 1: cycle -3 (first row, to exercise rebasing), one valid address
    (4096) and one -1 padding slot.
  - row 2: cycle 5, addresses 1024,1088,-1,-1 (2 valid, 2 padding), exactly
    as specified in task-T3.3-brief.md step 1.
  - row 3: cycle 7, 10 address columns (matching SCALE-Sim's `Bandwidth: 10`
    width), 9 valid (100..108) and 1 padding.

Rebase offset is 3 (row 1's raw cycle is -3). Rebased cycles: 0, 8, 10.
Valid (non-negative) addresses: 1 + 2 + 9 = 12, matching the brief's expected
record count. Row 1 contributes the record at rebased cycle 0.
"""

import json
import pathlib

import pytest

import parse_trace as pt

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
GEM5_SAMPLE = FIXTURES / "memctrl_sample.txt"


def _run_cli(tmp_path, input_path, out_name="out.nvt", scalesim_cmd=None,
             sidecar_path=None, force=False):
    out_path = tmp_path / out_name
    argv = [str(input_path), str(out_path)]
    if scalesim_cmd is not None:
        argv += ["--scalesim-cmd", scalesim_cmd]
    if sidecar_path is not None:
        argv += ["--sidecar", str(sidecar_path)]
    if force:
        argv += ["--force"]
    rc = pt.main(argv)
    resolved_sidecar = sidecar_path or (tmp_path / (out_name + ".sidecar.json"))
    return rc, out_path, pathlib.Path(resolved_sidecar)


# --- brief's three core assertions ------------------------------------------

def test_record_count_equals_non_negative_addresses(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc == 0
    lines = out_path.read_text().splitlines()
    assert len(lines) == 12


def test_no_negative_address_in_output(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc == 0
    text = out_path.read_text()
    assert "-0x1" not in text
    assert " -" not in text  # no negative field anywhere in a record line


def test_first_cycle_is_zero_after_rebase(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc == 0
    lines = out_path.read_text().splitlines()
    first_cycle = int(lines[0].split(" ")[0])
    assert first_cycle == 0


# --- column order / per-row cycle sharing -----------------------------------

def test_records_keep_column_order_and_share_row_cycle(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc == 0
    lines = out_path.read_text().splitlines()
    # Row 3 (rebased cycle 10) contributes the last 9 records, addresses
    # 100..108 in that exact order.
    row3_lines = lines[-9:]
    cycles = [int(l.split(" ")[0]) for l in row3_lines]
    assert all(c == 10 for c in cycles)
    addrs = [int(l.split(" ")[2], 16) for l in row3_lines]
    assert addrs == list(range(100, 109))


def test_row1_and_row2_cycles(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc == 0
    lines = out_path.read_text().splitlines()
    # line 0: row1's single record, cycle 0, addr 4096
    assert lines[0].split(" ")[0] == "0"
    assert lines[0].split(" ")[2] == hex(4096)
    # lines 1-2: row2's two records, cycle 8, addrs 1024, 1088
    row2_lines = lines[1:3]
    assert all(l.split(" ")[0] == "8" for l in row2_lines)
    assert [int(l.split(" ")[2], 16) for l in row2_lines] == [1024, 1088]


# --- padding accounting ------------------------------------------------------

def test_padding_skipped_is_counted(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    # row1: 1 padding, row2: 2 padding, row3: 1 padding = 4 total.
    assert sidecar["padding_skipped"] == 4
    assert sidecar["records_written"] == 12
    assert sidecar["rows_read"] == 3


# --- op rule ------------------------------------------------------------------

def test_default_op_is_read_for_ifmap(tmp_path):
    ifmap_csv = tmp_path / "IFMAP_DRAM_TRACE.csv"
    ifmap_csv.write_text((FIXTURES / "scalesim_sample.csv").read_text())
    rc, out_path, sidecar_path = _run_cli(tmp_path, ifmap_csv)
    assert rc == 0
    lines = out_path.read_text().splitlines()
    assert all(l.split(" ")[1] == "R" for l in lines)
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["op"] == "R"


def test_ofmap_filename_gives_write_op(tmp_path):
    ofmap_csv = tmp_path / "OFMAP_DRAM_TRACE.csv"
    ofmap_csv.write_text((FIXTURES / "scalesim_sample.csv").read_text())
    rc, out_path, sidecar_path = _run_cli(tmp_path, ofmap_csv)
    assert rc == 0
    lines = out_path.read_text().splitlines()
    assert all(l.split(" ")[1] == "W" for l in lines)
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["op"] == "W"
    assert sidecar["writes"] == 12
    assert sidecar["reads"] == 0


# --- output line structure ---------------------------------------------------

def test_output_line_structure_matches_existing_traces(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc == 0
    line = out_path.read_text().splitlines()[0]
    fields = line.split(" ")
    assert len(fields) == 5
    cycle, op, addr, data, last = fields
    assert op in ("R", "W")
    assert addr.startswith("0x")
    assert len(data) == 128
    assert set(data) == {"0"}
    assert last == "0"


# --- non-integer address error ------------------------------------------------

def test_non_integer_address_names_the_row(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("1,100,not_a_number\n2,200,300\n")
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(bad_csv), str(out_path)])
    assert rc == 1
    assert not out_path.exists()


def test_non_integer_address_error_message_names_line(tmp_path, capsys):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("1,100,not_a_number\n2,200,300\n")
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(bad_csv), str(out_path)])
    assert rc == 1
    captured = capsys.readouterr()
    assert "line 1" in captured.err


# --- failure leaves no partial output ----------------------------------------

def test_failure_leaves_no_partial_output_or_tmp(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("1,100,200\n2,not_a_cycle,300\n")
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(bad_csv), str(out_path)])
    assert rc == 1
    assert not out_path.exists()
    assert not (tmp_path / "out.nvt.tmp").exists()


def test_non_monotonic_cycle_is_an_error(tmp_path):
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("5,100\n3,200\n")
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(bad_csv), str(out_path)])
    assert rc == 1
    assert not out_path.exists()


# --- overwrite refusal / --force ---------------------------------------------

def test_overwrite_refused_without_force(tmp_path):
    rc1, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc1 == 0
    rc2, _, _ = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc2 == 1


def test_overwrite_allowed_with_force(tmp_path):
    rc1, out_path, sidecar_path = _run_cli(tmp_path, FIXTURES / "scalesim_sample.csv")
    assert rc1 == 0
    rc2, out_path2, sidecar_path2 = _run_cli(
        tmp_path, FIXTURES / "scalesim_sample.csv", force=True
    )
    assert rc2 == 0
    assert out_path2.exists()


# --- gem5 MemCtrl log refusal -------------------------------------------------

def test_gem5_memctrl_log_is_refused_with_pointer(tmp_path, capsys):
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(GEM5_SAMPLE), str(out_path)])
    assert rc == 1
    assert not out_path.exists()
    captured = capsys.readouterr()
    assert "parse_gem5_memctrl.py" in captured.err


# --- sidecar fields present ---------------------------------------------------

def test_sidecar_has_expected_fields(tmp_path):
    rc, out_path, sidecar_path = _run_cli(
        tmp_path, FIXTURES / "scalesim_sample.csv",
        scalesim_cmd="python3 scale.py -c configs/google.cfg -t topologies/x.csv -p out",
    )
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["parser"] == "parse_trace.py"
    assert "parser_version" in sidecar
    assert sidecar["argv"][0] == str(FIXTURES / "scalesim_sample.csv")
    assert sidecar["source"]["csv_path"] == str(FIXTURES / "scalesim_sample.csv")
    assert len(sidecar["source"]["csv_sha256"]) == 64
    assert sidecar["source"]["csv_size_bytes"] > 0
    assert sidecar["source"]["scalesim_command"] == (
        "python3 scale.py -c configs/google.cfg -t topologies/x.csv -p out"
    )
    assert sidecar["unit"] == (
        "1 SCALE-Sim cycle = 1 NVMain cycle at CPUFreq 3000 (0.333 ns); "
        "SCALE-Sim's own plots assume 2.4 GHz"
    )
    assert sidecar["rows_read"] == 3
    assert sidecar["records_written"] == 12
    assert sidecar["padding_skipped"] == 4
    assert sidecar["reads"] == 12
    assert sidecar["writes"] == 0
    assert sidecar["cycles"]["rebase_offset"] == 3
    assert sidecar["cycles"]["first_cycle"] == 0
    assert sidecar["cycles"]["last_cycle"] == 10
    assert sidecar["addresses"]["min"] == hex(100)
    assert sidecar["addresses"]["max"] == hex(4096)
    assert sidecar["addresses"]["span_bytes"] == 4096 - 100
    assert 0.0 <= sidecar["addresses"]["aligned_64b_fraction"] <= 1.0
    assert sidecar["addresses"]["distinct_64b_lines"] >= 1
    assert "records_sharing_line_with_previous" in sidecar["addresses"]


# --- input not found ----------------------------------------------------------

def test_missing_input_file_errors_cleanly(tmp_path, capsys):
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(tmp_path / "does_not_exist.csv"), str(out_path)])
    assert rc == 1
    assert not out_path.exists()


# --- --note KEY=VALUE ---------------------------------------------------------

def test_note_option_adds_fields_to_sidecar(tmp_path):
    out_path = tmp_path / "out.nvt"
    sidecar_path = tmp_path / "out.sidecar.json"
    rc = pt.main([
        str(FIXTURES / "scalesim_sample.csv"), str(out_path),
        "--sidecar", str(sidecar_path),
        "--note", "scalesim_layer_folder=layer1",
        "--note", "layer_note=some free text",
    ])
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["scalesim_layer_folder"] == "layer1"
    assert sidecar["layer_note"] == "some free text"


def test_note_value_may_contain_equals_sign(tmp_path):
    out_path = tmp_path / "out.nvt"
    sidecar_path = tmp_path / "out.sidecar.json"
    rc = pt.main([
        str(FIXTURES / "scalesim_sample.csv"), str(out_path),
        "--sidecar", str(sidecar_path),
        "--note", "formula=a=b+c",
    ])
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["formula"] == "a=b+c"


def test_note_without_equals_sign_is_rejected(tmp_path, capsys):
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(FIXTURES / "scalesim_sample.csv"), str(out_path), "--note", "no_equals_here"])
    assert rc == 1
    assert not out_path.exists()
    captured = capsys.readouterr()
    assert "note" in captured.err.lower()


def test_note_colliding_with_reserved_key_is_rejected(tmp_path, capsys):
    out_path = tmp_path / "out.nvt"
    rc = pt.main([str(FIXTURES / "scalesim_sample.csv"), str(out_path), "--note", "records_written=999"])
    assert rc == 1
    assert not out_path.exists()
    captured = capsys.readouterr()
    assert "records_written" in captured.err


def test_duplicate_note_key_is_rejected(tmp_path, capsys):
    out_path = tmp_path / "out.nvt"
    rc = pt.main([
        str(FIXTURES / "scalesim_sample.csv"), str(out_path),
        "--note", "foo=1", "--note", "foo=2",
    ])
    assert rc == 1
    assert not out_path.exists()


# --- input file is never modified or deleted ---------------------------------

def test_input_file_is_never_deleted_or_modified(tmp_path):
    src = FIXTURES / "scalesim_sample.csv"
    before = src.read_text()
    rc, out_path, sidecar_path = _run_cli(tmp_path, src)
    assert rc == 0
    assert src.exists()
    assert src.read_text() == before


def test_padding_in_the_middle_of_a_row_is_skipped_in_place(tmp_path):
    """Real SCALE-Sim rows can carry -1 padding BETWEEN valid addresses (1,943 rows of
    AlexNet layer1 IFMAP do, e.g. CSV line 120079). Every non-negative address must still
    be emitted, in column order; a parser that stops at the first -1 would lose them."""
    src = tmp_path / "IFMAP_DRAM_TRACE.csv"
    src.write_text("10.0,4096.0,4160.0,-1.0,-1.0,8192.0,8256.0\n"
                   "11.0,-1.0,12288.0,-1.0,12352.0,-1.0,-1.0\n")
    rc, out_path, sidecar = _run_cli(tmp_path, src)
    assert rc == 0
    lines = out_path.read_text().splitlines()
    got = [(l.split()[0], l.split()[1], l.split()[2]) for l in lines]
    # The parser rebases only a NEGATIVE first cycle, so cycles 10 and 11 are kept as they are.
    assert got == [("10", "R", "0x1000"), ("10", "R", "0x1040"), ("10", "R", "0x2000"), ("10", "R", "0x2040"),
                   ("11", "R", "0x3000"), ("11", "R", "0x3040")]
    side = json.loads(sidecar.read_text())
    assert side["padding_skipped"] == 6

