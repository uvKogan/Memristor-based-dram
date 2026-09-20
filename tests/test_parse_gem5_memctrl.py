"""T3.1: gem5 MemCtrl log -> NVMain trace parser, with provenance sidecar.

Fixtures:
  tests/fixtures/memctrl_sample.txt
      Real lines from a gem5 25.1 --debug-flags=MemCtrl run (memtest.c,
      --cpu-type=X86O3CPU --caches --l2cache --fast-forward=1000000
      --maxinsts=2000000; see task-T3.1-report.md for the full command,
      wall time and log size), trimmed to ~24 lines: 4 real `recvAtomic`
      lines (ticks 0-12000, before the real switch tick 1154819500), 3 real
      `recvTimingReq` lines (2 R, 1 W) with their real `Access to` /
      `Command for` / `Responding to Address` companion lines and queue
      bookkeeping lines, and one line
      ("20000: system.cpu.dcache: Sending packet 0x20000") that is
      CONSTRUCTED, not from the real log: gem5 with --debug-flags=MemCtrl
      only ever emits MemCtrl-tagged lines, so a real run cannot produce a
      non-mem_ctrl line for us to test the object-name filter against.

  tests/fixtures/memctrl_retry_constructed.txt
      Fully CONSTRUCTED (see the file name). The scratch gem5 run never
      filled a controller queue, so no real "queue full, not accepting"
      pair was available (see task-T3.1-report.md). This fixture reuses
      the exact message wording gem5 prints at
      simulators/gem5/src/mem/mem_ctrl.cc:445 and :465, in the real order
      confirmed by reading recvTimingReq() (mem_ctrl.cc:406-480): the
      queue-limit DPRINTF and the full/not-accepting DPRINTF both fire, at
      the same tick as the request line, before any later request line.

  tests/fixtures/memctrl_two_controllers_constructed.txt
      Fully CONSTRUCTED (fix round 1, item 1). Reproduces the reviewer's
      report: two controller objects at the same tick, ctrl0's WriteReq
      rejected, ctrl1's ReadReq accepted, with the request/rejection lines
      interleaved across the two objects. A single-global-pending parser
      (the pre-fix design) misattributes the rejection to ctrl1's read and
      keeps ctrl0's rejected write instead. The correct behavior is
      per-object: only ctrl0's write is dropped, only ctrl1's read is kept.
"""

import json
import pathlib

import pytest

import parse_gem5_memctrl as pgm

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]

# Real switch tick from the same scratch run that produced memctrl_sample.txt.
REAL_SWITCH_TICK = 1154819500


def _write_stdout(tmp_path, switch_tick=REAL_SWITCH_TICK, command="gem5.opt --debug-flags=MemCtrl ..."):
    p = tmp_path / "gem5_stdout.log"
    p.write_text(
        "gem5 Simulator System.\n"
        f"command line: {command}\n"
        "Switch at instruction count:1000000\n"
        f"Switched CPUS @ tick {switch_tick}\n"
        "Exiting @ tick 4385572000 because a thread reached the max instruction count\n"
    )
    return p


def _run_cli(tmp_path, region, skip_ns=0, raw_path=None, stdout_path=None, cpufreq_mhz=3000,
             out_path=None, sidecar_path=None, force=False, allow_malformed=None):
    raw_path = raw_path or (FIXTURES / "memctrl_sample.txt")
    out_path = out_path or (tmp_path / "out.nvt")
    sidecar_path = sidecar_path or (tmp_path / "out.sidecar.json")
    argv = [
        "--raw", str(raw_path),
        "--out", str(out_path),
        "--cpufreq-mhz", str(cpufreq_mhz),
        "--region", region,
        "--skip-ns", str(skip_ns),
        "--sidecar", str(sidecar_path),
    ]
    if stdout_path is not None:
        argv += ["--stdout", str(stdout_path)]
    if force:
        argv += ["--force"]
    if allow_malformed is not None:
        argv += ["--allow-malformed", str(allow_malformed)]
    rc = pgm.main(argv)
    return rc, out_path, sidecar_path


# --- (a) exactly the real requests, per region -----------------------------

def test_region_all_keeps_every_real_request(tmp_path):
    stdout_path = _write_stdout(tmp_path)
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", stdout_path=stdout_path)
    assert rc == 0
    lines = out_path.read_text().splitlines()
    # 4 recvAtomic (all R) + 3 recvTimingReq (2 R, 1 W) = 7; the one
    # constructed non-mem_ctrl line and all companion lines are dropped.
    assert len(lines) == 7
    ops = [l.split(" ")[1] for l in lines]
    assert ops.count("R") == 6
    assert ops.count("W") == 1


def test_region_o3_keeps_only_post_switch_recvTimingReq(tmp_path):
    stdout_path = _write_stdout(tmp_path)
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="o3", skip_ns=0, stdout_path=stdout_path)
    assert rc == 0
    lines = out_path.read_text().splitlines()
    # Only the 3 recvTimingReq records are at/after the switch tick.
    assert len(lines) == 3
    ops = [l.split(" ")[1] for l in lines]
    assert ops.count("R") == 2
    assert ops.count("W") == 1


def test_region_ff_keeps_only_pre_switch_recvAtomic(tmp_path):
    stdout_path = _write_stdout(tmp_path)
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="ff", stdout_path=stdout_path)
    assert rc == 0
    lines = out_path.read_text().splitlines()
    assert len(lines) == 4
    ops = [l.split(" ")[1] for l in lines]
    assert ops == ["R", "R", "R", "R"]


def test_region_o3_or_ff_without_stdout_switch_line_fails_clearly(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="o3", stdout_path=None)
    assert rc != 0
    assert not out_path.exists()


# --- (b) ops mapped R/W -----------------------------------------------------

def test_op_mapping_write_and_read_commands():
    assert pgm.map_op("WritebackDirty", 1) == "W"
    assert pgm.map_op("WritebackClean", 1) == "W"
    assert pgm.map_op("WriteReq", 1) == "W"
    assert pgm.map_op("WriteLineReq", 1) == "W"
    assert pgm.map_op("WriteClean", 1) == "W"
    assert pgm.map_op("ReadReq", 1) == "R"
    assert pgm.map_op("ReadSharedReq", 1) == "R"
    assert pgm.map_op("ReadExReq", 1) == "R"


def test_unknown_command_raises(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("      0: system.mem_ctrls: recvAtomic: FooBarReq 0x10\n")
    with pytest.raises(pgm.ParseError, match=r"line 1.*FooBarReq"):
        with open(tmp_path / "out.nvt", "w") as out_f:
            pgm.parse(str(raw), 3000, "all", None, 0, out_f)


def test_unknown_command_cli_exits_nonzero(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("      0: system.mem_ctrls: recvAtomic: FooBarReq 0x10\n")
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", raw_path=raw)
    assert rc != 0
    assert not out_path.exists()


# --- (c) integer rounding ---------------------------------------------------

@pytest.mark.parametrize(
    "tick_ps,cpufreq_mhz,expected_cycle",
    [
        (999999999999, 3000, 3000000000),
        (600000000500, 3000, 1800000002),
        (0, 3000, 0),
        (1000, 3000, 3),  # 1 ns at 3 GHz -> 3 cycles exactly
    ],
)
def test_round_half_up_scaled(tick_ps, cpufreq_mhz, expected_cycle):
    assert pgm.round_half_up_scaled(tick_ps, cpufreq_mhz) == expected_cycle


def test_cycles_are_rebased_and_rounded_end_to_end(tmp_path):
    raw = tmp_path / "raw.txt"
    # Two recvAtomic records, offset = first tick (999999999999), second
    # record's rebased tick = 600000000500.
    raw.write_text(
        "999999999999: system.mem_ctrls: recvAtomic: ReadReq 0x40\n"
        f"{999999999999 + 600000000500}: system.mem_ctrls: recvAtomic: WriteReq 0x80\n"
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)
    lines = out_path.read_text().splitlines()
    assert lines[0].split(" ")[0] == "0"
    assert lines[1].split(" ")[0] == "1800000002"
    assert result["rebase_offset_ticks"] == 999999999999


# --- (d) sidecar counts match ------------------------------------------------

def test_sidecar_counts_and_fields(tmp_path):
    stdout_path = _write_stdout(tmp_path)
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", stdout_path=stdout_path)
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())

    assert sidecar["parser_version"] == pgm.PARSER_VERSION
    assert sidecar["records"]["total"] == 7
    assert sidecar["records"]["reads"] == 6
    assert sidecar["records"]["writes"] == 1
    assert sidecar["records"]["first_cycle"] == 0
    assert sidecar["region"]["mode"] == "all"
    assert sidecar["region"]["switch_tick_ps"] == REAL_SWITCH_TICK
    assert sidecar["cpufreq_mhz"] == 3000
    assert sidecar["unit"] == "cycle = 1/3000 us (CPUFreq 3000 MHz)"
    assert sidecar["addresses"]["aligned_64b_fraction"] == 1.0
    assert sidecar["addresses"]["size_histogram"] == {"64": 3}
    assert len(sidecar["source"]["raw_log_sha256_first_1mb"]) == 64
    assert sidecar["source"]["raw_log_size_bytes"] > 0
    assert "--raw" in sidecar["argv"]

    # dropped-line counts by type: 4 access_to+command_for+responding lines
    # among the real companion lines, plus the constructed non_mem_ctrl line,
    # plus assorted "other_mem_ctrl" bookkeeping lines (queue limit, Adding
    # to *, Setting up controller, Done).
    dl = sidecar["dropped_lines"]
    assert dl["access_to"] == 2
    assert dl["command_for"] == 2
    assert dl["responding_to_address"] == 3
    assert dl["non_mem_ctrl"] == 1
    assert dl["retry"] == 0
    assert dl["queue_dump"] == 0
    assert dl["malformed_request"] == 0
    assert dl["truncated_final_line"] == 0

    # Single controller in this fixture.
    assert sidecar["records"]["controller_objects"] == ["system.mem_ctrls"]
    assert sidecar["records"]["by_object"]["system.mem_ctrls"] == {
        "total": 7, "reads": 6, "writes": 1,
    }

    assert sidecar["region_excluded_lines"] == {"recvAtomic": 0, "recvTimingReq": 0}
    assert sidecar["skip_ns_excluded_lines"] == 0
    assert sidecar["allow_malformed"] == 0
    assert sidecar["malformed_lines_seen"] == 0
    assert sidecar["lines_read"] > 0


# --- region ff / o3 arithmetic ----------------------------------------------

def test_region_ok_all_ff_o3():
    assert pgm.region_ok(0, "all", None, 0) is True
    assert pgm.region_ok(10**12, "all", None, 0) is True
    assert pgm.region_ok(999, "ff", 1000, 0) is True
    assert pgm.region_ok(1000, "ff", 1000, 0) is False
    assert pgm.region_ok(1000, "o3", 1000, 0) is True
    assert pgm.region_ok(999, "o3", 1000, 0) is False
    # skip_ns applied as ps
    assert pgm.region_ok(1000 + 5000 - 1, "o3", 1000, 5_000_000) is False
    assert pgm.region_ok(1000 + 5_000_000, "o3", 1000, 5_000_000) is True


def test_region_decision_distinguishes_skip_ns_from_before_o3():
    # before the switch tick entirely: excluded, but NOT a skip_ns exclusion
    assert pgm.region_decision(999, "o3", 1000, 5_000_000) == (False, False)
    # in [switch, switch+skip): excluded specifically because of --skip-ns
    assert pgm.region_decision(1000, "o3", 1000, 5_000_000) == (False, True)
    assert pgm.region_decision(1000 + 4_999_999, "o3", 1000, 5_000_000) == (False, True)
    # at/after switch+skip: kept
    assert pgm.region_decision(1000 + 5_000_000, "o3", 1000, 5_000_000) == (True, False)
    # region "ff"/"all" never report a skip_ns exclusion
    assert pgm.region_decision(0, "ff", 1000, 5_000_000) == (True, False)
    assert pgm.region_decision(2000, "ff", 1000, 5_000_000) == (False, False)
    assert pgm.region_decision(0, "all", None, 0) == (True, False)


# --- retries -----------------------------------------------------------------

def test_retry_drop_uses_constructed_fixture(tmp_path):
    raw = FIXTURES / "memctrl_retry_constructed.txt"
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)
    assert result["dropped"]["retry"] == 2
    assert result["records"]["total"] == 1
    lines = out_path.read_text().splitlines()
    assert len(lines) == 1
    assert lines[0].split(" ")[1] == "R"
    assert lines[0].split(" ")[2] == "0x30080"

    # Line-accounting identity: every one of the 9 raw lines in this fixture
    # ends up counted exactly once, including the two "queue full, not
    # accepting" rejection lines themselves (fix round 1, item 3's self-check
    # would have caught the earlier omission of those two lines).
    accounted = (
        result["records"]["total"]
        + sum(result["dropped"].values())
        + sum(result["region_excluded"].values())
    )
    assert accounted == result["lines_read"] == 9


# --- monotonic assertion ------------------------------------------------------

def test_non_monotonic_raises_with_line_number(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "2000: system.mem_ctrls: recvAtomic: ReadReq 0x10\n"
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0x20\n"
    )
    with pytest.raises(pgm.ParseError, match=r"line 2"):
        with open(tmp_path / "out.nvt", "w") as out_f:
            pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)


def test_equal_ticks_allowed(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0x10\n"
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0x20\n"
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)
    assert result["records"]["total"] == 2


# --- zero records --------------------------------------------------------------

def test_zero_kept_records_fails(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("      0: system.mem_ctrls: Setting up controller\n")
    with pytest.raises(pgm.ParseError, match="zero records"):
        with open(tmp_path / "out.nvt", "w") as out_f:
            pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)


def test_zero_kept_records_cli_exits_nonzero_and_no_output(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("      0: system.mem_ctrls: Setting up controller\n")
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", raw_path=raw)
    assert rc != 0
    assert not out_path.exists()
    assert not sidecar_path.exists()


# --- output line structure matches the existing traces ------------------------

def test_output_line_structure_matches_existing_trace(tmp_path):
    stdout_path = _write_stdout(tmp_path)
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", stdout_path=stdout_path)
    assert rc == 0
    new_line = out_path.read_text().splitlines()[0]

    existing_path = REPO_ROOT / "benchmarks" / "gpt2_ifmap.nvt"
    existing_line = existing_path.read_text().splitlines()[0]

    new_fields = new_line.split(" ")
    existing_fields = existing_line.split(" ")
    assert len(new_fields) == len(existing_fields) == 5
    assert new_fields[1] in ("R", "W")
    assert existing_fields[1] in ("R", "W")
    assert new_fields[2].startswith("0x")
    assert existing_fields[2].startswith("0x")
    assert len(new_fields[3]) == len(existing_fields[3]) == 128
    assert set(new_fields[3]) <= {"0"}
    assert set(existing_fields[3]) <= {"0"}
    assert new_fields[4] == existing_fields[4] == "0"


# --- classify_drop buckets -----------------------------------------------------

@pytest.mark.parametrize(
    "obj,msg,expected_bucket",
    [
        ("system.mem_ctrls", "Access to 0x10, ready at 5 next burst at 6.", "access_to"),
        ("system.mem_ctrls", "Command for 0x10, issued at 5.", "command_for"),
        ("system.mem_ctrls", "Responding to Address 0x10.. ", "responding_to_address"),
        ("system.mem_ctrls", "===READ QUEUE===", "queue_dump"),
        ("system.mem_ctrls", "Read 0x10", "queue_dump"),
        ("system.mem_ctrls", "Write 0x10", "queue_dump"),
        ("system.mem_ctrls", "Response 0x10", "queue_dump"),
        ("system.mem_ctrls", "Setting up controller", "other_mem_ctrl"),
        ("system.mem_ctrls", "Read queue limit 32, current size 0, entries needed 1", "other_mem_ctrl"),
        ("system.l2", "some unrelated cache event", "non_mem_ctrl"),
        ("system.cpu.dcache", "Sending packet 0x20000", "non_mem_ctrl"),
    ],
)
def test_classify_drop(obj, msg, expected_bucket):
    assert pgm.classify_drop("0", obj, msg) == expected_bucket


# --- addresses: never altered, strict hex, alignment fraction -----------------

def test_addresses_never_altered_and_alignment_fraction(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0xff\n"  # not 64-aligned
        "2000: system.mem_ctrls: recvAtomic: ReadReq 0x40\n"  # 64-aligned
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)
    lines = out_path.read_text().splitlines()
    assert lines[0].split(" ")[2] == "0xff"
    assert lines[1].split(" ")[2] == "0x40"
    assert result["records"]["aligned_64b"] == 1
    # addr_min/addr_max track the raw parsed addresses
    assert result["records"]["addr_min"] == 0x40
    assert result["records"]["addr_max"] == 0xFF


# --- switch tick / command line extraction from stdout -------------------------

def test_read_switch_tick(tmp_path):
    p = _write_stdout(tmp_path, switch_tick=123456789)
    assert pgm.read_switch_tick(str(p)) == 123456789


def test_read_switch_tick_missing_returns_none(tmp_path):
    p = tmp_path / "stdout.log"
    p.write_text("gem5 Simulator System.\nno switch line here\n")
    assert pgm.read_switch_tick(str(p)) is None


def test_read_gem5_command(tmp_path):
    cmd = "gem5.opt --outdir=x --debug-flags=MemCtrl configs/deprecated/example/se.py --cmd=./memtest"
    p = _write_stdout(tmp_path, command=cmd)
    assert pgm.read_gem5_command(str(p)) == cmd


# --- module is importable without side effects ---------------------------------

def test_module_import_has_no_side_effects():
    # Re-importing must not touch the filesystem or print anything; if
    # parse_gem5_memctrl did file I/O at import time this would already
    # have failed the module-level collection of this test file.
    assert hasattr(pgm, "main")
    assert callable(pgm.main)


# =============================================================================
# Fix round 1
# =============================================================================

# --- item 1: per-controller retry look-ahead, ordered emission --------------

def test_interleaved_two_controllers_reproduces_reviewer_case():
    """ctrl0's WriteReq is rejected, ctrl1's ReadReq (interleaved) is accepted.

    A single-global-pending parser would flush ctrl0's write as "accepted" the
    moment ctrl1's read request line arrives (since it looks like "the next
    request line"), then misattribute the later "Write queue full, not
    accepting" line to ctrl1's still-pending read instead, keeping the wrong
    request. The correct, per-object behavior keeps only ctrl1's read.
    """
    raw = FIXTURES / "memctrl_two_controllers_constructed.txt"
    import io
    out_f = io.StringIO()
    result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)

    assert result["dropped"]["retry"] == 1
    assert result["records"]["total"] == 1
    lines = out_f.getvalue().splitlines()
    assert len(lines) == 1
    fields = lines[0].split(" ")
    assert fields[1] == "R"
    assert fields[2] == "0x2000"  # ctrl1's ReadReq address, not ctrl0's WriteReq

    by_obj = result["records"]["by_object"]
    assert "system.mem_ctrls1" in by_obj
    assert by_obj["system.mem_ctrls1"] == {"total": 1, "reads": 1, "writes": 0}
    assert "system.mem_ctrls0" not in by_obj  # its only request was rejected


def test_two_controllers_no_rejection_keep_both_in_order(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls0: recvTimingReq: request WriteReq addr 0x1000 size 64\n"
        "1000: system.mem_ctrls1: recvTimingReq: request ReadReq addr 0x2000 size 64\n"
        "2000: system.mem_ctrls0: recvTimingReq: request WriteReq addr 0x1040 size 64\n"
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)

    assert result["dropped"]["retry"] == 0
    assert result["records"]["total"] == 3
    lines = out_path.read_text().splitlines()
    assert len(lines) == 3
    # Tick order preserved: 1000 (ctrl0 W), 1000 (ctrl1 R), 2000 (ctrl0 W).
    ticks = [int(l.split(" ")[0]) for l in lines]
    assert ticks == sorted(ticks)
    addrs = [l.split(" ")[2] for l in lines]
    assert set(addrs) == {"0x1000", "0x2000", "0x1040"}

    by_obj = result["records"]["by_object"]
    assert by_obj["system.mem_ctrls0"] == {"total": 2, "reads": 0, "writes": 2}
    assert by_obj["system.mem_ctrls1"] == {"total": 1, "reads": 1, "writes": 0}
    assert sorted(by_obj.keys()) == ["system.mem_ctrls0", "system.mem_ctrls1"]


def test_sidecar_records_controller_objects_and_per_object_counts(tmp_path):
    rc, out_path, sidecar_path = _run_cli(
        tmp_path, region="all",
        raw_path=FIXTURES / "memctrl_two_controllers_constructed.txt",
        force=True,
    )
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["records"]["controller_objects"] == ["system.mem_ctrls1"]
    assert sidecar["records"]["by_object"] == {
        "system.mem_ctrls1": {"total": 1, "reads": 1, "writes": 0},
    }


# --- item 2: catch-all exceptions, atomic write, --force --------------------

def test_sidecar_path_is_a_directory_gives_clean_nonzero_and_no_nvt_left(tmp_path, capsys):
    sidecar_dir = tmp_path / "out.sidecar.json"
    sidecar_dir.mkdir()
    out_path = tmp_path / "out.nvt"
    argv = [
        "--raw", str(FIXTURES / "memctrl_sample.txt"),
        "--stdout", str(_write_stdout(tmp_path)),
        "--out", str(out_path),
        "--region", "all",
        "--sidecar", str(sidecar_dir),
        "--force",  # the directory already "exists"; bypass the overwrite guard
    ]
    rc = pgm.main(argv)
    assert rc != 0
    err = capsys.readouterr().err
    assert "parse_gem5_memctrl: error:" in err
    assert not out_path.exists()
    assert not (tmp_path / "out.nvt.tmp").exists()
    # the directory itself is untouched (not replaced, not deleted)
    assert sidecar_dir.is_dir()


def test_refuses_to_overwrite_existing_out_without_force(tmp_path):
    out_path = tmp_path / "out.nvt"
    out_path.write_text("PRE-EXISTING ACCEPTED TRACE\n")
    sidecar_path = tmp_path / "out.sidecar.json"
    rc, _, _ = _run_cli(
        tmp_path, region="all", stdout_path=_write_stdout(tmp_path),
        out_path=out_path, sidecar_path=sidecar_path,
    )
    assert rc != 0
    # untouched
    assert out_path.read_text() == "PRE-EXISTING ACCEPTED TRACE\n"
    assert not sidecar_path.exists()


def test_refuses_to_overwrite_existing_sidecar_without_force(tmp_path):
    out_path = tmp_path / "out.nvt"
    sidecar_path = tmp_path / "out.sidecar.json"
    sidecar_path.write_text('{"pre-existing": true}\n')
    rc, _, _ = _run_cli(
        tmp_path, region="all", stdout_path=_write_stdout(tmp_path),
        out_path=out_path, sidecar_path=sidecar_path,
    )
    assert rc != 0
    assert not out_path.exists()
    assert sidecar_path.read_text() == '{"pre-existing": true}\n'


def test_force_allows_overwrite(tmp_path):
    out_path = tmp_path / "out.nvt"
    out_path.write_text("OLD\n")
    sidecar_path = tmp_path / "out.sidecar.json"
    sidecar_path.write_text("OLD\n")
    rc, _, _ = _run_cli(
        tmp_path, region="all", stdout_path=_write_stdout(tmp_path),
        out_path=out_path, sidecar_path=sidecar_path, force=True,
    )
    assert rc == 0
    assert out_path.read_text() != "OLD\n"
    assert sidecar_path.read_text() != "OLD\n"


def test_successful_run_leaves_no_tmp_file(tmp_path):
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", stdout_path=_write_stdout(tmp_path))
    assert rc == 0
    assert not pathlib.Path(str(out_path) + ".tmp").exists()
    assert out_path.exists()
    assert sidecar_path.exists()


# --- item 3: region-excluded counters and self-check identity ---------------

@pytest.mark.parametrize("region,expected_region_excluded", [
    ("all", {"recvAtomic": 0, "recvTimingReq": 0}),
    ("ff", {"recvAtomic": 0, "recvTimingReq": 3}),
    ("o3", {"recvAtomic": 4, "recvTimingReq": 0}),
])
def test_region_excluded_counts_and_self_check_identity(tmp_path, region, expected_region_excluded):
    stdout_path = _write_stdout(tmp_path)
    rc, out_path, sidecar_path = _run_cli(tmp_path, region=region, skip_ns=0, stdout_path=stdout_path)
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())

    assert sidecar["region_excluded_lines"] == expected_region_excluded
    assert sidecar["skip_ns_excluded_lines"] == 0

    accounted = (
        sidecar["records"]["total"]
        + sum(sidecar["dropped_lines"].values())
        + sum(sidecar["region_excluded_lines"].values())
    )
    assert accounted == sidecar["lines_read"]


def test_skip_ns_excluded_is_distinguished_from_before_o3(tmp_path):
    switch_tick = 1_000_000
    raw = tmp_path / "raw.txt"
    raw.write_text(
        # before switch: excluded, not a skip_ns exclusion
        f"{switch_tick - 500}: system.mem_ctrls: recvTimingReq: request ReadReq addr 0x40 size 64\n"
        # in [switch, switch+skip_ns*1000): excluded specifically by skip_ns
        f"{switch_tick + 100}: system.mem_ctrls: recvTimingReq: request ReadReq addr 0x80 size 64\n"
        # at/after switch+skip: kept
        f"{switch_tick + 10000}: system.mem_ctrls: recvTimingReq: request ReadReq addr 0xc0 size 64\n"
    )
    stdout_path = _write_stdout(tmp_path, switch_tick=switch_tick)
    rc, out_path, sidecar_path = _run_cli(
        tmp_path, region="o3", skip_ns=10, raw_path=raw, stdout_path=stdout_path,
    )
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["records"]["total"] == 1
    assert sidecar["region_excluded_lines"] == {"recvAtomic": 0, "recvTimingReq": 2}
    # Of those 2 exclusions, exactly 1 was specifically because of --skip-ns.
    assert sidecar["skip_ns_excluded_lines"] == 1

    accounted = (
        sidecar["records"]["total"]
        + sum(sidecar["dropped_lines"].values())
        + sum(sidecar["region_excluded_lines"].values())
    )
    assert accounted == sidecar["lines_read"] == 3


# --- item 4: truncated final line --------------------------------------------

def test_truncated_final_line_dropped_and_warned(tmp_path, capsys):
    raw = tmp_path / "raw.txt"
    # A complete first record, then a final line with NO trailing newline -
    # simulating a killed gem5 / full disk mid-write.
    raw.write_text(
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0x40\n"
        "2000: system.mem_ctrls: recvAtomic: ReadReq 0x8"  # note: no trailing \n, cut mid-address
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)

    assert result["records"]["total"] == 1
    assert result["dropped"]["truncated_final_line"] == 1
    lines = out_path.read_text().splitlines()
    assert len(lines) == 1
    assert lines[0].split(" ")[2] == "0x40"

    err = capsys.readouterr().err
    assert "line 2" in err
    assert "trailing newline" in err.lower() or "truncated" in err.lower()

    accounted = (
        result["records"]["total"]
        + sum(result["dropped"].values())
        + sum(result["region_excluded"].values())
    )
    assert accounted == result["lines_read"] == 2


def test_file_ending_with_newline_has_no_truncation(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("1000: system.mem_ctrls: recvAtomic: ReadReq 0x40\n")
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)
    assert result["dropped"]["truncated_final_line"] == 0
    assert result["records"]["total"] == 1


# --- item 5: malformed request lines -----------------------------------------

def test_malformed_request_line_fails_by_default_naming_line(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0x40\n"
        # 0xZZ is not valid hex - looks like a request line, fails the strict regex
        "2000: system.mem_ctrls: recvAtomic: ReadReq 0xZZ\n"
    )
    with pytest.raises(pgm.ParseError, match=r"line 2.*malformed"):
        with open(tmp_path / "out.nvt", "w") as out_f:
            pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)


def test_malformed_request_line_cli_exits_nonzero_and_no_output(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text("2000: system.mem_ctrls: recvTimingReq: request ReadReq addr 0xZZ size 64\n")
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", raw_path=raw)
    assert rc != 0
    assert not out_path.exists()


def test_allow_malformed_tolerates_up_to_n(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0x40\n"
        "2000: system.mem_ctrls: recvAtomic: ReadReq 0xZZ\n"     # malformed 1
        "3000: system.mem_ctrls: recvAtomic: ReadReq 0xYY\n"     # malformed 2
        "4000: system.mem_ctrls: recvAtomic: ReadReq 0x80\n"
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False, allow_malformed=2)
    assert result["records"]["total"] == 2
    assert result["dropped"]["malformed_request"] == 2
    assert result["malformed_seen"] == 2

    accounted = (
        result["records"]["total"]
        + sum(result["dropped"].values())
        + sum(result["region_excluded"].values())
    )
    assert accounted == result["lines_read"] == 4


def test_allow_malformed_budget_exceeded_still_raises(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0xZZ\n"
        "2000: system.mem_ctrls: recvAtomic: ReadReq 0xYY\n"
    )
    with pytest.raises(pgm.ParseError, match="allow-malformed"):
        with open(tmp_path / "out.nvt", "w") as out_f:
            pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False, allow_malformed=1)


def test_allow_malformed_cli_flag_recorded_in_sidecar(tmp_path):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: recvAtomic: ReadReq 0x40\n"
        "2000: system.mem_ctrls: recvAtomic: ReadReq 0xZZ\n"
        "3000: system.mem_ctrls: recvAtomic: ReadReq 0x80\n"
    )
    rc, out_path, sidecar_path = _run_cli(
        tmp_path, region="all", raw_path=raw, allow_malformed=1,
    )
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    assert sidecar["allow_malformed"] == 1
    assert sidecar["malformed_lines_seen"] == 1
    assert sidecar["dropped_lines"]["malformed_request"] == 1


# =============================================================================
# Fix round 2
# =============================================================================
#
# Round 1's per-controller fix was ordering-correct but used an O(n^2)
# buffering scheme: a controller that goes quiet (never issues a following
# request) held its pending record open until EOF, so every OTHER
# controller's accepted-but-not-yet-safe-to-emit records piled up in a list
# that got rescanned on every insertion. Verified against gem5 25.1
# src/mem/mem_ctrl.cc recvTimingReq() (lines 406-485, quoted in
# task-T3.1-report.md): the request DPRINTF and either rejection DPRINTF are
# printed in the same synchronous call, with no schedule()/return-and-reenter
# between them, so a rejection can only ever be logged at its own request's
# tick, never later. This lets the parser settle (accept) any pending record
# the instant a strictly later tick is seen anywhere in the log, so both
# `pending` and `resolved_at_current_tick` only ever hold the current tick's
# records - bounded by how many request lines share one tick, not by file
# size or controller count.

def test_quiet_controller_does_not_cause_quadratic_blowup(tmp_path):
    """The reviewer's reproduction: one controller with an old open request
    that is never rejected (and never followed by another request from that
    same controller, so round 1's per-object flush never resolves it either),
    while another controller emits 200,000 accepted requests at increasing
    ticks. Round 1: did not finish in 3 minutes at this N. Round 2: must
    finish in well under 5 seconds, and max_held_records must stay small
    (not proportional to N).
    """
    import time

    raw = tmp_path / "raw.txt"
    n = 200_000
    with open(raw, "w") as f:
        f.write("1: system.mem_ctrls0: recvTimingReq: request WriteReq addr 0x1000 size 64\n")
        for i in range(n):
            tick = 1000 + i * 10
            addr = 0x2000 + i * 64
            f.write(f"{tick}: system.mem_ctrls1: recvTimingReq: request ReadReq addr 0x{addr:x} size 64\n")

    out_path = tmp_path / "out.nvt"
    start = time.monotonic()
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)
    elapsed = time.monotonic() - start

    assert elapsed < 5.0, f"parse took {elapsed:.2f}s, expected well under 5s (was O(n^2) in round 1)"
    assert result["records"]["total"] == n + 1  # ctrl0's one request + all n ctrl1 requests, all accepted
    assert result["dropped"]["retry"] == 0
    # The true bound is "records sharing one tick", not controller count or
    # file size - for this file (one request per line, all distinct ticks
    # after the first), that bound is tiny, not O(n).
    assert result["max_held_records"] <= 3

    accounted = (
        result["records"]["total"]
        + sum(result["dropped"].values())
        + sum(result["region_excluded"].values())
    )
    assert accounted == result["lines_read"] == n + 1


def test_rejection_at_later_tick_than_pending_is_anomaly_not_a_drop(tmp_path):
    """A rejection line's tick is later than the tick of the pending record it
    would naively seem to match. Per the source, a real rejection can only be
    logged at its own request's tick, so by the time a later-tick line
    arrives, any pending record has already been settled as accepted - this
    rejection line cannot legitimately belong to it. The parser must not
    retroactively drop the already-accepted record; it must count the
    rejection line itself as an anomaly and warn once.
    """
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: recvTimingReq: request WriteReq addr 0x1000 size 64\n"
        "2000: system.mem_ctrls: Write queue full, not accepting\n"
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)

    # The WriteReq was already settled as accepted (tick advanced past 1000
    # before the rejection line, at tick 2000, was even read) - it must stay kept.
    assert result["records"]["total"] == 1
    lines = out_path.read_text().splitlines()
    assert len(lines) == 1
    assert lines[0].split(" ")[2] == "0x1000"

    assert result["dropped"]["retry"] == 0
    assert result["dropped"]["unmatched_retry"] == 1

    accounted = (
        result["records"]["total"]
        + sum(result["dropped"].values())
        + sum(result["region_excluded"].values())
    )
    assert accounted == result["lines_read"] == 2


def test_unmatched_retry_warns_once(tmp_path, capsys):
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "1000: system.mem_ctrls: Write queue full, not accepting\n"
        "2000: system.mem_ctrls: Write queue full, not accepting\n"
        "3000: system.mem_ctrls: recvAtomic: ReadReq 0x40\n"
    )
    out_path = tmp_path / "out.nvt"
    with open(out_path, "w") as out_f:
        result = pgm.parse(str(raw), 3000, "all", None, 0, out_f, progress=False)
    assert result["dropped"]["unmatched_retry"] == 2
    err = capsys.readouterr().err
    assert err.count("anomaly") == 1  # warned once, not per occurrence


def test_max_held_records_in_sidecar(tmp_path):
    rc, out_path, sidecar_path = _run_cli(
        tmp_path, region="all",
        raw_path=FIXTURES / "memctrl_two_controllers_constructed.txt",
        force=True,
    )
    assert rc == 0
    sidecar = json.loads(sidecar_path.read_text())
    assert isinstance(sidecar["max_held_records"], int)
    assert sidecar["max_held_records"] >= 1


# --- all seven earlier ordering cases (round 1) still pass under the new
# tick-batched settlement (kept as explicit smoke checks here; the full
# originals are the round-1 tests above, all still present and unmodified) ---

def test_round1_ordering_cases_still_hold_smoke():
    # 1. per-controller matching: interleaved rejection only drops its own object
    raw1 = FIXTURES / "memctrl_two_controllers_constructed.txt"
    import io
    result1 = pgm.parse(str(raw1), 3000, "all", None, 0, io.StringIO(), progress=False)
    assert result1["dropped"]["retry"] == 1
    assert result1["records"]["total"] == 1

    # 2. tick-ordered output across controllers, no rejection
    import pathlib as _p
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        raw2 = _p.Path(td) / "raw.txt"
        raw2.write_text(
            "1000: system.mem_ctrls0: recvTimingReq: request WriteReq addr 0x1000 size 64\n"
            "1000: system.mem_ctrls1: recvTimingReq: request ReadReq addr 0x2000 size 64\n"
            "2000: system.mem_ctrls0: recvTimingReq: request WriteReq addr 0x1040 size 64\n"
        )
        out2 = io.StringIO()
        result2 = pgm.parse(str(raw2), 3000, "all", None, 0, out2, progress=False)
        ticks = [int(l.split(" ")[0]) for l in out2.getvalue().splitlines()]
        assert ticks == sorted(ticks)

        # 3. EOF flush: a still-open pending at EOF is accepted
        raw3 = _p.Path(td) / "raw3.txt"
        raw3.write_text("1000: system.mem_ctrls: recvTimingReq: request ReadReq addr 0x40 size 64\n")
        out3 = io.StringIO()
        result3 = pgm.parse(str(raw3), 3000, "all", None, 0, out3, progress=False)
        assert result3["records"]["total"] == 1

        # 4. monotonicity error still raised, naming the line
        raw4 = _p.Path(td) / "raw4.txt"
        raw4.write_text(
            "2000: system.mem_ctrls: recvAtomic: ReadReq 0x10\n"
            "1000: system.mem_ctrls: recvAtomic: ReadReq 0x20\n"
        )
        with pytest.raises(pgm.ParseError, match=r"line 2"):
            pgm.parse(str(raw4), 3000, "all", None, 0, io.StringIO(), progress=False)

    # 5. rebase on the first emitted record
    assert result2  # (uses the same file as case 2; first emitted tick 1000 -> cycle 0)
    first_line = out2.getvalue().splitlines()[0]
    assert first_line.split(" ")[0] == "0"

    # 6. self-check identity (line-accounting) still holds
    accounted1 = (
        result1["records"]["total"]
        + sum(result1["dropped"].values())
        + sum(result1["region_excluded"].values())
    )
    assert accounted1 == result1["lines_read"]

    # 7. single-controller case unaffected (matches test_region_all_keeps_every_real_request)
    out5 = io.StringIO()
    result5 = pgm.parse(str(FIXTURES / "memctrl_sample.txt"), 3000, "all", None, 0, out5, progress=False)
    assert result5["records"]["total"] == 7


# --- gem5 prints address zero as a bare "0" (C's %#x), found on the real SPEC gcc log ---

def test_address_zero_is_printed_without_0x_and_is_a_valid_request(tmp_path):
    """Real line from the gcc run: 'recvTimingReq: request ReadSharedReq addr 0 size 64'.
    It is a legitimate read of physical address 0, not a malformed line."""
    raw = tmp_path / "raw.txt"
    raw.write_text(
        "   1000: system.mem_ctrls: recvAtomic: ReadSharedReq 0\n"
        "   2000: system.mem_ctrls: recvTimingReq: request ReadSharedReq addr 0 size 64\n"
        "   3000: system.mem_ctrls: recvTimingReq: request WritebackDirty addr 0x40 size 64\n"
    )
    rc, out_path, sidecar_path = _run_cli(tmp_path, region="all", raw_path=raw)
    assert rc == 0
    got = [tuple(l.split()[:3]) for l in out_path.read_text().splitlines()]
    assert got == [("0", "R", "0x0"), ("3", "R", "0x0"), ("6", "W", "0x40")]
    side = json.loads(sidecar_path.read_text())
    assert side["dropped_lines"]["malformed_request"] == 0


def test_other_unprefixed_addresses_are_still_malformed(tmp_path):
    """Only the exact spelling '0' is accepted without a prefix; '40' or '00' is malformed."""
    for bad in ("40", "00", "0x"):
        raw = tmp_path / f"raw_{bad}.txt"
        raw.write_text(f"   1000: system.mem_ctrls: recvTimingReq: request ReadSharedReq addr {bad} size 64\n")
        rc, out_path, _ = _run_cli(tmp_path, region="all", raw_path=raw,
                                   out_path=tmp_path / f"o_{bad}.nvt", sidecar_path=tmp_path / f"o_{bad}.json")
        assert rc != 0
        assert not out_path.exists()
