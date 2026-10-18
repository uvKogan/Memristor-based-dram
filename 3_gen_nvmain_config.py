import math
import json
import os
import re
import sys
import argparse
from pathlib import Path

# Fixed by this template for every technology and architecture: burst length in
# columns (tBURST, and the divisor NVMain's own "capacity is ... MB" print folds
# in alongside RATE) and the DDR-style prefetch RATE (columns transferred per
# CLK, from "RATE 2" in the template). Used by compute_timings(), geometry() and
# the template itself so there is exactly one place that defines them.
BURST_CYCLES = 4
RATE = 2

# Documented modeling constants kept as constants, NOT as stand-ins for missing
# measured data (I5, final review 2026-09). Each is a ruling of this project or
# a property of the NVMain template, identical for every technology, and is
# never read from hardware_metrics.json:
#   BUS_WIDTH_BITS - the rank's data bus width; the template's own fixed
#     64-bit rank width (see the "Rank Width" header line it prints).
#   CPU_FREQ_MHZ   - traceMain.cpp's host issue-rate assumption, fixed at 3000
#     for every technology (cycle-8 finding #11; see the template comment).
#   TRP_CYCLES     - precharge fixed at one cycle by ruling (non-destructive
#     ReRAM read; fix round 1, 2026-09), see compute_timings' docstring.
#   TCMD_CYCLES    - command transport, one cycle, as in every NVMain example.
BUS_WIDTH_BITS = 64
CPU_FREQ_MHZ = 3000
TRP_CYCLES = 1
TCMD_CYCLES = 1

# tWR in the --write-pulse-on-path bounding mode. In that mode the whole cell
# write time is carried by tWP, which NVMain's SubArray::Write() adds to the
# write completion, nextPrecharge, nextRead AND nextWrite, so the pulse sits on
# the request path. tWR is then the residual write-recovery time only, and is
# set to one cycle rather than to the write time (NVMain adds tWP and tWR to
# nextPrecharge both, so leaving the write time in tWR would charge the same
# physical write twice) and rather than to zero (a zero timing is an untested
# edge in NVMain's event arithmetic that this study does not want to exercise).
BOUNDING_MODE_TWR_CYCLES = 1

# Every per-model key generate_nvmain_config() needs out of
# hardware_metrics.json. I5 (final review 2026-09): these used to be
# `.get(key, <invented default>)` calls - 32.0 ns read/write latency (the
# RETIRED pre-revision figure), 10 mW leakage, 1.1 / 1.7 nJ energies, 2048
# subarray rows - so a hardware entry missing a key produced a
# complete-looking config built on numbers no NVSim run ever measured. Every
# one of them is now required, and a missing key aborts generation naming the
# file, the model and the key.
REQUIRED_HW_KEYS = (
    "capacity_gb",
    "read_latency_ns",
    "write_latency_ns",
    "read_energy_nj",
    "write_energy_nj",
    "leakage_mw",
    "subarray_rows",
)


class MissingHardwareMetric(ValueError):
    """A hardware_metrics.json entry is missing a key the generator needs.

    Raised instead of substituting a default: an invented hardware value is
    exactly the silent failure the 2026-09 revision's "every stage fails
    loudly" rule forbids.
    """


def require_hw_metric(hw_metrics, key, model_name="<unknown model>",
                      source="results/hardware_metrics.json"):
    """Return hw_metrics[key], or raise MissingHardwareMetric naming file, model and key."""
    if key not in hw_metrics or hw_metrics[key] is None:
        raise MissingHardwareMetric(
            f"{source}: hardware entry {model_name!r} has no {key!r} "
            f"(present keys: {sorted(k for k in hw_metrics)}). This value is a "
            f"measured NVSim output, not something this generator may default: "
            f"re-run 1_run_nvsim_hardware.py and 2_extract_hardware_metrics.py "
            f"for {model_name!r}."
        )
    return hw_metrics[key]

# T2.8: microsecond-silicon sensitivity pair. NVSim's ReRAM latencies are
# nanosecond-class (this project's own 22nm estimates); the only fabricated
# Gb-class ReRAM chips report MICROSECOND latencies. Each entry keeps every
# other NVSim-derived value (energies, leakage, area, organization, channels,
# decoder, endurance, queue settings) from its `parent` hardware-metrics key's
# full-DIMM config, overriding only read_latency_ns/write_latency_ns before
# compute_timings() runs -- see generate_silicon_config(). Values verified
# against the source PDFs in documents/reference_validation_papers/:
#   - Zahurak et al., IEDM 2014, Table 1 (p. IEDM14-143): Read Performance
#     Latency (uS) "Actual Demonstration" 2.3; Write Performance Latency (uS)
#     "Actual Demonstration" 11.7.
#   - Liu et al., JSSC 49(1) 2014, Table II "DEVICE FEATURES" (p. 149):
#     Read Latency 40us; Write Latency 230us.
SILICON_TIMINGS = {
    "reram_micron16gb_1t1r": {
        "parent": "reram_22nm_1t1r_slc",
        "read_ns": 2300.0,
        "write_ns": 11700.0,
        "citation": "Zahurak et al., IEDM 2014, Table 1 (16 Gb Cu-ReRAM, 27 nm): "
                     "read 2.3 us, write 11.7 us",
    },
    "reram_sandisk32gb_1s1r": {
        "parent": "reram_22nm_selector_slc",
        "read_ns": 40000.0,
        "write_ns": 230000.0,
        "citation": "Liu et al., JSSC 2014, Table II (32 Gb 2-layer cross-point, 24 nm): "
                     "read 40 us, write 230 us",
    },
}


def silicon_model_names():
    """Sys-model names --silicon writes (full-DIMM only), in SILICON_TIMINGS order.

    mbmm_master.py imports this (via importlib.util.spec_from_file_location, the
    same pattern tests/test_gen_nvmain_config.py uses for this digit-prefixed
    script) instead of duplicating SILICON_TIMINGS' key set."""
    return [f"{key}_full_dimm" for key in SILICON_TIMINGS]


def get_project_root():
    return Path(__file__).parent.absolute()

def setup_args():
    parser = argparse.ArgumentParser(description="MBMM Step 3: Multi-Architecture Factory")
    parser.add_argument("--input", default="results/hardware_metrics.json", help="Input JSON file.")
    parser.add_argument("--freq", type=int, default=800, help="Target frequency in MHz.")
    parser.add_argument("--queue-size", type=int, default=32,
                        help="FRFCFS controller QueueSize (default: 32, matching NVMain's own "
                             "hardcoded fallback - see FRFCFS.cpp). Kept as an explicit, "
                             "documented generator parameter instead of an implicit simulator "
                             "default; override for a write-queue-depth sensitivity sweep.")
    parser.add_argument("--output-dir", default=None,
                        help="Override the Config output directory (default: "
                             "simulators/nvmain/Config/). Use a separate directory for a "
                             "sensitivity sweep so it never touches the official configs.")
    parser.add_argument("--channels", type=int, choices=[1, 2], default=1,
                        help="Number of memory channels (default: 1). 2 splits RANKS across "
                             "two independent channels (a channel is a set of ranks on its "
                             "own bus; ROWS/COLS/BANKS/MATHeight are per-channel geometry and "
                             "stay unchanged), DDR5-subchannel style. Architectures with a "
                             "single rank (single, 8chip) cannot be split and are generated "
                             "at 1 channel regardless, with a note in the config header.")
    parser.add_argument("--decoder", choices=["Default", "StartGap"], default="Default",
                        help="NVMain address-translation Decoder (default: Default). StartGap "
                             "also writes StartGapInterval.")
    parser.add_argument("--endurance-model", choices=["RowModel", "WordModel", "NullModel"],
                        default="RowModel",
                        help="NVMain EnduranceModel (default: RowModel).")
    parser.add_argument("--window-ns", type=int, default=250000000,
                        help="Matched simulation window in nanoseconds, recorded as a comment "
                             "in the generated config for T2.3 to read back (default: "
                             "250000000).")
    parser.add_argument("--silicon", action="store_true",
                        help="Also write the T2.8 microsecond-silicon sensitivity full-DIMM "
                             "configs (SILICON_TIMINGS): same template/geometry/energies/"
                             "leakage/channels/decoder/endurance/queue settings as each entry's "
                             "parent full-DIMM config, with only read/write latency overridden "
                             "to the cited fabricated chip's own timing.")
    parser.add_argument("--write-pulse-on-path", action="store_true",
                        help="Bounding mode: charge the NVSim cell write latency to the "
                             "write's own completion as well. The generated ReRAM/silicon "
                             "configs then emit tWP = ceil(write_latency_ns / cycle_ns) with "
                             "tWR 1. In the DEFAULT mode (unchanged) no tWP key is written "
                             "and tWR carries those write cycles, which reach the request "
                             "path only when a write closes its row: a close-page "
                             "WRITE_PRECHARGE charges them to the subarray's next activation, "
                             "while a write followed by another queued request to the same "
                             "open row charges them to nextPrecharge alone (nothing beyond "
                             "the burst and the tWTR turnaround, identical in both modes). "
                             "Neither branch delays the write's own completion. So bounding "
                             "mode puts the pulse on every write's completion, and for "
                             "row-hit writes also on the next read and write to that "
                             "subarray, while leaving close-page subarray occupancy "
                             "unchanged to within one cycle. It is an upper end of "
                             "the write-path cost, not a prediction. Reaches the GENERATED "
                             "ReRAM/silicon configs only: the DDR5 and PCM configs are "
                             "static files.")
    parser.add_argument("--manifest-out", default=None,
                        help="Write a JSON manifest of the config names generated by THIS "
                             "run (plus the flags they were generated with) to this path. "
                             "mbmm_master.py passes it and then refuses to simulate any "
                             "generated ReRAM/silicon config that is not in the manifest, so "
                             "leftovers from an earlier run with different flags can never "
                             "be picked up out of the shared live Config directory (I6).")
    return parser.parse_args()

def read_latency_cycles(read_ns, freq_mhz):
    """Interface cycles the NVSim read latency occupies at `freq_mhz`.

    The single source of truth for the read-latency split: compute_timings()
    divides exactly this many cycles between tRCD and tCAS, and
    validate_config() refuses any config whose tRCD + tCAS does not add back
    up to it (I4, final review 2026-09 - the book says the generator's
    validation enforces the split, so it now does, instead of the split merely
    holding by construction). The floor of 2 cycles is what makes a split into
    two >= 1 cycle halves possible at all for a sub-cycle read latency.
    """
    cyc = 1000.0 / freq_mhz
    return max(2, math.ceil(read_ns / cyc))


def write_pulse_cycles(write_ns, freq_mhz):
    """Interface cycles the NVSim cell write latency occupies at `freq_mhz`.

    The single source of truth for the write-time split, exactly as
    read_latency_cycles() is for the read split: compute_timings() puts this
    cycle count either in tWR (default mode) or in tWP (--write-pulse-on-path
    bounding mode), and validate_config() reads the SAME function back to check
    whichever key the mode says must carry it. The two therefore cannot drift,
    and a hand-edited tWP or tWR is refused rather than silently simulated.

    The floor of 1 cycle is the pre-existing behaviour of the tWR computation
    this function was extracted from: a sub-cycle write still costs one cycle.
    """
    cyc = 1000.0 / freq_mhz
    return max(1, math.ceil(write_ns / cyc))


def compute_timings(read_ns, write_ns, freq_mhz, burst=BURST_CYCLES,
                    write_pulse_on_path=False):
    """Cycle counts for NVMain. The device read latency is charged once: tRCD (activate) plus
    tCAS (column access) sum to the NVSim read latency (Section 3.1.6 correction, 2026-09).
    Earlier versions set both tRCD and tCAS to the full read latency, charging every read
    twice.

    The cell WRITE time goes to one of two keys, chosen by `write_pulse_on_path`.
    What the choice actually changes is CONDITIONAL ON THE BRANCH the write takes
    in SubArray::Write() (T2 review fix round 2; round 0's "never sits on a
    request's path" and round 1's unconditional "the delta is the completion
    event" were each right for only one of the two branches):

    These timers are SUBARRAY state, not bank state: nextActivate, nextPrecharge,
    nextRead and nextWrite are SubArray members (SubArray.h:137-140), and a bank
    holds ROWS/MATHeight of them (DDR3Bank.cpp:129) - one for the SLC full DIMM,
    two for MLC. So what a write blocks is its own subarray, not the whole bank.

      * In DEFAULT mode the cell write time sits in tWR and reaches the request
        path ONLY WHEN A WRITE CLOSES ITS ROW. Under the close-page policy these
        configs generate (ClosePage 1, UsePrecharge true), a write that is the
        last queued request to its row becomes WRITE_PRECHARGE
        (MemoryController::MakeImplicitPrechargeRequest, MemoryController.cpp:1055-1063,
        called at :1596 and :1658 under the FLAG_LAST_REQUEST guards at :1594 and
        :1653, and that flag is set only where MemoryController::IsLastRequest
        :1114-1144 returns true), and NVMain adds tWR to the subarray's next
        activation (SubArray.cpp:625-629), with nextPrecharge/nextRead/nextWrite
        all MAXed against it (:631-633), so the next read or write to that
        subarray waits for it.
        A write followed by another queued request to the same open row takes
        the plain WRITE branch (SubArray.cpp:648-660), where tWR reaches only
        nextPrecharge (:648-651): nextRead (:653-656) and nextWrite (:658-660)
        carry writeTimer but NO tWR, so nothing beyond the burst and the
        write-to-read turnaround (tWTR, NVMain's default of 5 since these configs
        never emit the key, and identical in both modes) is charged.
        In NEITHER branch does the cell write time delay the write's own
        completion event (writeEventTime, :671-672, carries writeTimer alone).
      * BOUNDING mode moves the same cycle count to tWP (tWR becomes
        BOUNDING_MODE_TWR_CYCLES). tWP is what WriteCellData returns (:991) and
        so becomes writeTimer (:581): EVERY write's completion carries the pulse,
        and in the plain WRITE branch nextRead and nextWrite on that subarray
        carry it too, while in the WRITE_PRECHARGE branch the subarray's next
        activation is unchanged to within one cycle (writeTimer + tWR is 0 + W
        in default mode and W + 1 here).

    The delta between the modes is therefore the write's own completion latency
    with the pulse excluded versus included, PLUS, for open-row writes, the
    subarray time that default mode did not charge. It is an upper end of the
    write-path cost, not a prediction, and how the two effects mix in any one run
    is set by the trace's row locality and the queue depth.

    The returned "tWP" is None in default mode, and the template omits the key
    entirely then, so a default-mode config is byte-identical to what this
    generator wrote before the mode existed.

    tRP is fixed at 1 cycle, not latency-proportional (fix round 1 ruling, 2026-09):
    ReRAM reads are non-destructive -- there is no restore/precharge phase the way a
    destructive-read DRAM row needs after every access -- and the device's full
    read latency (NVSim-derived or, for the T2.8 silicon configs, the fabricated
    chip's published figure) is already charged in full to tRCD + tCAS above. Scaling
    tRP with read latency would double-charge that same physical read latency a
    second time on every access."""
    t_read = read_latency_cycles(read_ns, freq_mhz)
    t_write = write_pulse_cycles(write_ns, freq_mhz)
    t_rcd = max(1, t_read // 2)
    t_cas = max(1, t_read - t_rcd)
    t_burst = burst
    t_ccd = max(4, t_burst)                       # NVMain requires tCCD >= tBURST (segfault otherwise)
    t_ras = max(t_read, t_rcd + t_burst)          # activate must outlast tRCD + burst
    if write_pulse_on_path:
        t_wp, t_wr = t_write, BOUNDING_MODE_TWR_CYCLES
    else:
        t_wp, t_wr = None, t_write
    return {"tCAS": t_cas, "tRCD": t_rcd, "tRP": TRP_CYCLES, "tRAS": t_ras, "tWR": t_wr,
            "tWP": t_wp, "tBURST": t_burst, "tCCD": t_ccd, "tCMD": TCMD_CYCLES}

def validate_config(cfg):
    """Return the list of timing-relationship violations in `cfg` (empty = valid).

    `cfg` must carry CLK, CPUFreq, tBURST, tCCD, tRAS, tRCD, tCAS,
    read_latency_ns, tWR, write_latency_ns and write_pulse_on_path. None of
    them is optional: the read-latency split check below is the one the book
    claims this function performs (Technical_Report.typ:961-965, Appendix B.1
    :3843-3845, Appendix D :3982), and a caller that omitted the keys would
    silently skip it, which is the class of defect this whole pass removes. A
    missing key is a KeyError. `tWP` is read with .get() because its ABSENCE is
    the default mode's required state, which is exactly what the write check
    below asserts.

    The production caller builds `cfg` with config_check_from_text(), i.e. by
    re-reading the rendered config text, so both splits are checked on what
    NVMain will actually parse rather than on the dict the template was rendered
    from (M1, T2 review fix round 1).
    """
    v = []
    if cfg["CLK"] > cfg["CPUFreq"]: v.append(f"CLK {cfg['CLK']} exceeds CPUFreq {cfg['CPUFreq']}: NVMain corrupts admission silently")
    if cfg["tCCD"] < cfg["tBURST"]: v.append("tCCD below tBURST: NVMain can segfault")
    if cfg["tRAS"] < cfg["tRCD"] + cfg["tBURST"]: v.append("tRAS below tRCD + tBURST")

    # I4: the read latency must be charged exactly once, split across tRCD
    # (activate) and tCAS (column access). compute_timings() builds the split
    # from read_latency_cycles(); this check is the same function read back, so
    # the two cannot drift apart, and a hand-edited or hand-corrupted split is
    # refused rather than silently simulated.
    expected_read_cycles = read_latency_cycles(cfg["read_latency_ns"], cfg["CLK"])
    if cfg["tRCD"] + cfg["tCAS"] != expected_read_cycles:
        v.append(
            f"tRCD + tCAS = {cfg['tRCD']} + {cfg['tCAS']} = "
            f"{cfg['tRCD'] + cfg['tCAS']} cycles does not equal the device read "
            f"latency {cfg['read_latency_ns']} ns at CLK {cfg['CLK']} MHz "
            f"({expected_read_cycles} cycles): the read latency would be charged "
            f"twice or not at all")

    # T2: the cell write time must be carried by exactly one key, and by the
    # key this run's mode says. compute_timings() builds the split from
    # write_pulse_cycles(); this check is the same function read back, so the
    # two cannot drift apart, and a hand-edited tWP or tWR is refused.
    expected_write_cycles = write_pulse_cycles(cfg["write_latency_ns"], cfg["CLK"])
    t_wp = cfg.get("tWP")
    if cfg["write_pulse_on_path"]:
        if t_wp != expected_write_cycles:
            v.append(
                f"--write-pulse-on-path: tWP is {t_wp!r}, not the device write "
                f"latency {cfg['write_latency_ns']} ns at CLK {cfg['CLK']} MHz "
                f"({expected_write_cycles} cycles): in bounding mode tWP is what "
                f"puts the cell write pulse on the request path, so a wrong or "
                f"missing tWP silently makes the run a default-mode run")
        if cfg["tWR"] != BOUNDING_MODE_TWR_CYCLES:
            v.append(
                f"--write-pulse-on-path: tWR is {cfg['tWR']}, not "
                f"{BOUNDING_MODE_TWR_CYCLES}: NVMain adds BOTH tWP and tWR to "
                f"nextPrecharge, so any other tWR charges the same physical write "
                f"a second time")
    else:
        if t_wp is not None:
            v.append(
                f"default mode: tWP is {t_wp!r}, but a default-mode config must "
                f"carry no tWP at all (NVMain's own default is 0). Pass "
                f"--write-pulse-on-path to put the write pulse on the request path")
        if cfg["tWR"] != expected_write_cycles:
            v.append(
                f"default mode: tWR is {cfg['tWR']}, not the device write latency "
                f"{cfg['write_latency_ns']} ns at CLK {cfg['CLK']} MHz "
                f"({expected_write_cycles} cycles): the cell write time would be "
                f"charged wrongly or not at all")
    return v

# The integer keys validate_config() needs that the config text itself carries.
# read_latency_ns / write_latency_ns / write_pulse_on_path are NOT among them:
# they are the generator's inputs, not config keys, and are what the rendered
# numbers are checked AGAINST.
CONFIG_CHECK_KEYS = ("CLK", "CPUFreq", "tBURST", "tCCD", "tRAS", "tRCD", "tCAS", "tWR")


def config_check_from_text(config_text, read_latency_ns, write_latency_ns,
                           write_pulse_on_path):
    """Build validate_config()'s input by re-reading a RENDERED config's own text.

    M1 (T2 review fix round 1). Validation used to run on the in-memory timings
    dict, which left the dict-to-text rendering unguarded: a template bug that
    dropped the tWP line in bounding mode still passed validation and exited 0.
    Reading every timing key back out of the string that is about to be written
    closes that for the read split and the write split at once, so what is
    checked is exactly what NVMain will parse.

    `tWP` is optional by design: its ABSENCE is the default mode's required
    state, and validate_config's default-mode branch asserts exactly that. Any
    other missing key is a ValueError naming it, since the template is supposed
    to emit all of them.

    Each key must appear EXACTLY ONCE (R3, T2 review fix round 2). A re.search
    would validate the first occurrence while NVMain's own parser acts on the
    last, so a template that emitted a key twice could be validated on a value
    the simulator never uses. Not reachable with today's template; refused loudly
    rather than left as a silent hazard.
    """
    def one_value(key, required):
        found = re.findall(rf"(?m)^{key} (\d+)$", config_text)
        if len(found) > 1:
            raise ValueError(
                f"config_check_from_text: the rendered config has {len(found)} "
                f"integer {key!r} lines ({', '.join(found)}), so it is ambiguous "
                f"which value NVMain would use (its parser takes the last, this "
                f"check would have taken the first). Every key must appear exactly "
                f"once. This is a template bug, not a data problem.")
        if not found:
            if not required:
                return None
            raise ValueError(
                f"config_check_from_text: the rendered config has no integer {key!r} "
                f"line, so its timing relationships cannot be verified. This is a "
                f"template bug, not a data problem: every key in CONFIG_CHECK_KEYS "
                f"must appear as '<key> <integer>' on its own line.")
        return int(found[0])

    cfg = {key: one_value(key, required=True) for key in CONFIG_CHECK_KEYS}
    cfg["tWP"] = one_value("tWP", required=False)
    cfg["read_latency_ns"] = read_latency_ns
    cfg["write_latency_ns"] = write_latency_ns
    cfg["write_pulse_on_path"] = bool(write_pulse_on_path)
    return cfg


def geometry(hw, arch_type, channels=1, model_name="<unknown model>",
             source="results/hardware_metrics.json"):
    """Compute per-architecture ROWS/COLS/BANKS/RANKS/CHANNELS/MATHeight for the NVMain config.

    Note on the `single` architecture: its ROWS is floored to 65536 as an address-space
    floor so the trace footprint fits, not physical capacity; a single 1 Gb chip holds
    128 MB (SLC). Do not quote this config's capacity print.

    Fix round 1 (2026-09): channels split RANKS, never ROWS. A channel is a set of
    ranks on its own bus -- each channel sees the full per-rank ROWS/COLS/BANKS
    geometry, and NVMain's own capacity print is PER CHANNEL (ROWS * COLS * tBURST *
    RATE * BusWidth * BANKS * RANKS / 8, using THIS channel's own RANKS), so the DIMM
    total is that per-channel figure times CHANNELS. The earlier `channels > 1: rows
    // channels` code divided ROWS instead, which for the real 2048x2048 ReRAM
    full-DIMM capacity took ROWS below MATHeight (2048 -> 1024 < 2048) and crashed
    generation outright at --channels 2 -- the primary matrix's setting -- since
    every earlier gatekeeper run used the default of 1 channel and never exercised
    this path.
    """
    cols, banks = 1024, 8
    ranks, dev, width = {"single": (1, 1, 64), "8chip": (1, 8, 8), "16chip": (2, 8, 8), "full_dimm": (8, 8, 8)}.get(arch_type, (1, 1, 8))
    bits_per_chip = require_hw_metric(hw, "capacity_gb", model_name, source) * 8 * 1024**3
    rows_per_chip = int(bits_per_chip / (cols * width * banks))
    # NVMain's own capacity print (MemoryController.cpp:457) is ROWS * COLS * tBURST *
    # RATE * BusWidth * BANKS * RANKS / 8, so the column word is tBURST * RATE * BusWidth/8
    # bytes and the divisor below is exactly the burst beats per column -- not a coincidence.
    #
    # RANKS is already a factor of that formula, so ROWS must be the per-chip row count
    # alone -- multiplying by ranks here too (the pre-revision bug) double-counts ranks
    # and prints a DIMM 64x too big (512 GB instead of 8 GB for the SLC full DIMM). The
    # printed capacity was checked against the live binary: 8192 MB for the SLC full DIMM,
    # 16384 MB for the MLC full DIMM (both at CHANNELS 1; see the channel-splitting note
    # above for the per-channel print at CHANNELS 2).
    rows = rows_per_chip // (BURST_CYCLES * RATE)
    if arch_type == "single":
        rows = max(rows, 65536)
    final_rows = rows
    if final_rows == 0:
        raise ValueError(
            f"geometry(): computed ROWS is 0 for arch_type={arch_type!r}, "
            f"capacity_gb={hw.get('capacity_gb')!r} -- hardware capacity is too small for "
            f"this architecture's per-chip geometry (cols={cols}, banks={banks}, width={width}).")

    # Channels split RANKS, not ROWS (see docstring). Only architectures whose RANKS
    # divides evenly by the requested channel count are actually split -- `single`
    # (1 rank) and `8chip` (1 rank) fall back to 1 channel unconditionally, since a
    # one-rank module cannot be split across channels; the two-channel comparison
    # applies to the 16-chip (2 ranks) and full-DIMM (8 ranks) modules.
    if channels > 1 and ranks % channels == 0:
        effective_channels = channels
    else:
        effective_channels = 1
    final_ranks = ranks // effective_channels

    # MATHeight is NOT ROWS: it is the NVSim subarray row count for this chip's own
    # array organization (DDR3Bank::SetConfig computes subArrayNum = ROWS / MATHeight,
    # Banks/DDR3Bank/DDR3Bank.cpp:129), independent of how many rows the *system-level*
    # NVMain config exposes as ROWS. NVMain's own MATHeight default is set at Params
    # construction time from the *struct* default ROWS (65536, Params.cpp:133
    # "MATHeight = ROWS;"), before the config file's ROWS override is applied -- so an
    # unset MATHeight silently stays 65536 regardless of the real ROWS, which is stale
    # and wrong either way (it isn't derived from the real per-chip NVSim organization).
    # T2.6 populated a real "subarray_rows" field in hardware_metrics.json from the
    # NVSim run's own "N Rows x N Columns" line, so this is a measured value and is
    # REQUIRED here (I5): the old `hw.get("subarray_rows", 2048)` placeholder would
    # quietly hold a 1024-organization model to the 2048 baseline geometry. MATHeight
    # and ROWS are both per-channel geometry, unaffected by the RANKS/CHANNELS split
    # above.
    subarray_rows = require_hw_metric(hw, "subarray_rows", model_name, source)
    if final_rows % subarray_rows != 0:
        raise ValueError(
            f"geometry(): ROWS ({final_rows}) is not evenly divisible by subarray_rows/"
            f"MATHeight ({subarray_rows}) for arch_type={arch_type!r} -- NVMain's "
            f"subArrayNum = ROWS // MATHeight would silently truncate or misconfigure the "
            f"bank's subarrays; adjust capacity_gb or subarray_rows so ROWS divides evenly.")

    return {"ROWS": final_rows, "COLS": cols, "BANKS": banks,
            "RANKS": final_ranks, "CHANNELS": effective_channels, "DEVICES_PER_RANK": dev,
            "DeviceWidth": width, "MATHeight": subarray_rows}

def generate_nvmain_config(base_name, hw_metrics, target_freq_mhz, output_dir, arch_type, queue_size=32,
                            channels=1, decoder="Default", endurance_model="RowModel", window_ns=250000000,
                            header_extra="", metrics_source="results/hardware_metrics.json",
                            write_pulse_on_path=False):
    # PROTECT DRAM: Do not generate NVMain configs for DRAM models!
    if "dram" in base_name.lower():
        return None

    cycle_time_ns = 1000.0 / target_freq_mhz

    # I5: every physical quantity below is a required key. A hardware entry
    # missing one aborts generation (MissingHardwareMetric names the file, the
    # model and the key) instead of yielding a complete-looking config built on
    # invented numbers.
    read_latency_ns = require_hw_metric(hw_metrics, 'read_latency_ns', base_name, metrics_source)
    write_latency_ns = require_hw_metric(hw_metrics, 'write_latency_ns', base_name, metrics_source)
    timings = compute_timings(read_latency_ns, write_latency_ns, target_freq_mhz,
                              write_pulse_on_path=write_pulse_on_path)

    # --- ARCHITECTURE FACTORY LOGIC ---
    bus_width = BUS_WIDTH_BITS
    geo = geometry(hw_metrics, arch_type, channels=channels,
                   model_name=base_name, source=metrics_source)
    banks = geo["BANKS"]
    cols = geo["COLS"]
    ranks = geo["RANKS"]
    effective_channels = geo["CHANNELS"]
    devices_per_rank = geo["DEVICES_PER_RANK"]
    current_device_width = geo["DeviceWidth"]
    system_rows = geo["ROWS"]
    mat_height = geo["MATHeight"]

    if arch_type in ("single", "8chip"):
        mapping = "R:BK:C"
    else:
        mapping = "R:BK:RK:C"

    # Validation happens further down, on the RENDERED config text rather than on
    # the `timings` dict (M1, T2 review fix round 1): see config_check_from_text()
    # and the check immediately before the file is written.

    # Static/leakage power: NVMain's NonVolatile energy model charges Eactstdby/Eprestdby
    # once per RANK per cycle (Ranks/StandardRank/StandardRank.cpp, no per-device scaling
    # for EnergyModel != "current") -- not once per device, and NOT via a "StandbyPower"
    # key, which NVMain never reads (grepped the entire nvmain source tree: zero matches
    # outside Config/*.config data files). So a per-chip NVSim leakage figure must be
    # scaled up to rank granularity (x devices_per_rank, NOT x total ranks*devices) and
    # converted from a steady-state Watts figure into per-cycle nanojoules.
    #
    # This is policy-a / "ungated" semantics: every device in the rank is always fully
    # powered, so leakage is charged for every simulated cycle at the rank's full linear
    # device-count leakage. Power-down IS entered (HandleLowPower() is restored -- see
    # the Epda/Epdpf/Epdps note below); it simply costs the same per cycle as standby
    # here, which is what makes the two indistinguishable in the leakage total.
    # No NVSim datapoint distinguishes "active row open" leakage from "all banks
    # precharged" leakage, so the same derived value is used for both Eactstdby and
    # Eprestdby; this is a documented simplifying assumption, not a measured split.
    #
    # Epda/Epdpf/Epdps (active/precharge powerdown energy): MemoryController::HandleLowPower()
    # is now restored (src/MemoryController.cpp:1650) -- power-down is live for every
    # technology sharing this controller base, not ReRAM-specific. No NVSim datapoint
    # decomposes ReRAM leakage into a gatable-periphery vs. ungatable-crossbar split, and
    # no JEDEC-style power-down current spec exists for ReRAM the way it does for DDR5 --
    # so rather than fabricate a number, these are set to an explicit, honest placeholder
    # equal to the technology's own Eactstdby/Eprestdby: "assume power-gating saves
    # nothing beyond existing precharge-standby, pending real characterization." This
    # avoids crediting a physically-impossible free (zero-cost) power-down while still
    # letting the mechanism run. See Technical_Report.typ Appendix A for the full disclosure;
    # upgrade this placeholder if a real ReRAM power-gating citation is found.
    chip_leakage_w = require_hw_metric(hw_metrics, 'leakage_mw', base_name, metrics_source) / 1000.0
    rank_leakage_w = chip_leakage_w * devices_per_rank
    e_standby_nj = rank_leakage_w * cycle_time_ns

    r_energy = require_hw_metric(hw_metrics, 'read_energy_nj', base_name, metrics_source)
    w_energy = require_hw_metric(hw_metrics, 'write_energy_nj', base_name, metrics_source)

    sys_model_name = f"{base_name}_{arch_type}"

    startgap_line = f"StartGapInterval 100\n" if decoder == "StartGap" else ""
    single_floor_line = (
        "; ROWS floored to 65536: address-space floor so the trace footprint fits, not\n"
        "; physical capacity; a single 1 Gb chip holds 128 MB (SLC). Do not quote this\n"
        "; config's capacity print.\n"
        if arch_type == "single" else "")

    # T2 bounding mode: the tWP line exists only when --write-pulse-on-path was
    # passed. In default mode this is the empty string and the timing block is
    # byte-identical to what this generator wrote before the mode existed.
    write_pulse_lines = ""
    if timings["tWP"] is not None:
        write_pulse_lines = (
            "; write pulse on the request path (bounding mode): tWP carries the NVSim "
            "write latency, tWR is 1 cycle\n"
            f"tWP {timings['tWP']}\n"
        )

    # Fix round 1: channels split RANKS, never ROWS (see geometry()'s docstring). A
    # one-rank module (single, 8chip) cannot be split across channels, so geometry()
    # silently falls back to 1 channel for those two architectures -- flagged here,
    # both on stdout and in the generated config's own header, rather than left silent.
    channels_note = ""
    if channels > 1 and effective_channels == 1:
        print(f"    [i] {base_name}_{arch_type}: generated at 1 channel (a one-rank "
              f"module cannot be split across {channels} channels); the two-channel "
              f"comparison applies to the 16-chip and full-DIMM modules.")
        channels_note = (
            "; NOTE: generated at 1 channel: a one-rank module cannot be split across\n"
            "; channels; the two-channel comparison applies to the 16-chip and\n"
            "; full-DIMM modules.\n"
        )

    config_content = f"""
; --- MBMM SYSTEM ARCHITECTURE: {arch_type.upper()} ---
; Base Model: {base_name} | Rank Width: {bus_width}-bit
; Matched simulation window: {window_ns} ns (WINDOW_NS, recorded for T2.3 to read back)
{header_extra}{single_floor_line}{channels_note}

; --- Infrastructure ---
IgnorePremappedAddresses true
IgnoreAddressError true
AddressMask 0xFFFFFFFF
PrintConfig true
PrintAllDevices true
EnableDebug false
MAP_ADDRESS true
Decoder {decoder}
{startgap_line}INTERCONNECT OffChipBus
; Cycle-8 finding #11 fix: CPUFreq is the *host* issue-rate assumption used only
; by traceMain.cpp to rescale the trace-timestamp admission cutoff (see
; results/throughput_check/throughput_mechanism_report.md) -- it is decoupled
; from CLK (the device's own clock, which drives all timing/energy formulas)
; and fixed at {CPU_FREQ_MHZ} (matching DDR5's existing calibration) for every technology,
; so every config assumes the same "modern server host" issuing the trace.
CPUFreq {CPU_FREQ_MHZ}

; --- Clock, Controller and Scaling ---
CLK {target_freq_mhz}
MEM_CTL FRFCFS
; QueueSize: the plain FRFCFS controller (MemControl/FRFCFS/FRFCFS.cpp) reads a
; single combined read+write QueueSize key (falls back to a hardcoded 32 if unset --
; the ReadQueueSize/WriteQueueSize keys seen in some bundled example configs belong
; to the different FRFCFS-WQF controller and are never read here). Previously left
; unset everywhere in this project, silently relying on that hardcoded default; now
; written explicitly so it's a documented, deliberate, sweepable parameter instead of
; an implicit simulator behavior. See documents/MBMM_Book_Typst/Post_Meeting_Notes_Shahar_2026-09-03.md
; item 5 and the write-queue-depth sensitivity study (Section 3.1.x) for why.
QueueSize {queue_size}
DEVICES_PER_RANK {devices_per_rank}

; --- Address Mapping ---
AddressMappingScheme {mapping}
BusWidth {bus_width}
DeviceWidth {current_device_width}
RATE {RATE}

; --- Timing Parameters (Cycles) ---
; tRCD + tCAS = NVSim read latency; earlier versions set both to the full latency
; and charged reads twice (Section 3.1.6 correction, 2026-09).
tCAS {timings['tCAS']}
tRCD {timings['tRCD']}
tRP {timings['tRP']}
tRAS {timings['tRAS']}
tWR {timings['tWR']}
{write_pulse_lines}tBURST {timings['tBURST']}
tCCD {timings['tCCD']}
tCMD {timings['tCMD']}

; --- Energy and Power ---
; Eactstdby/Eprestdby: rank-level standby energy per cycle (nJ), derived from NVSim
; per-chip leakage x devices_per_rank -- see comment above.
; Epda/Epdpf/Epdps: power-down is now live (HandleLowPower() restored). Set to an
; explicit honest placeholder (= Eactstdby/Eprestdby) rather than a fabricated real
; number -- see comment above and Technical_Report.typ Appendix A.
;
; Cycle-7 finding #10: this template previously wrote "ReadEnergy"/"WriteEnergy",
; which NVMain never parses (no such Params field exists) -- every ReRAM run to
; date silently used NVMain's generic stock Erd/Ewr defaults (3.405401/1.023750 nJ)
; instead of these real, per-technology NVSim values. The correct keys, per
; SubArray.cpp's "flat energy model" branch (used whenever EnergyModel != "current"),
; are Erd (charged once per access at Activate(), row-open energy) and Ewr (charged
; once per access at Write()) -- both in nJ, direct, no unit conversion needed.
; Eopenrd (separate per-access burst-read term) and Ewrpb (per-bit write savings)
; are left at NVMain's stock defaults: NVSim's read_energy_nj/write_energy_nj are
; single lumped per-access figures with no open/burst or per-bit decomposition to
; derive those two from, and inventing a split would be tuning, not calibration.
Erd {r_energy}
Ewr {w_energy}
Eactstdby {e_standby_nj}
Eprestdby {e_standby_nj}
Epda {e_standby_nj}
Epdpf {e_standby_nj}
Epdps {e_standby_nj}

; --- Geometry Scaling ---
; ROWS is sized by geometry() so the NVMain "capacity is ... MB" print matches the
; physical module (8192 MB for the SLC full DIMM, 16384 MB for the MLC full DIMM);
; see the comment in geometry() for the derivation.
ROWS {system_rows}
COLS {cols}
CHANNELS {effective_channels}
RANKS {ranks}
BANKS {banks}
SUBARRAYS 1
; MATHeight is the NVSim subarray row count, read from the required "subarray_rows"
; field of this model's hardware_metrics.json entry (T2.6; the NVSim run's own
; "N Rows x N Columns" line), NOT
; ROWS -- DDR3Bank::SetConfig computes subArrayNum = ROWS / MATHeight
; (Banks/DDR3Bank/DDR3Bank.cpp:129), so with this value subArrayNum is 1 for SLC
; full-DIMM and 8chip, 2 for MLC and 16chip (ranked archs scale with capacity_gb,
; not with RANKS), and 32 for single (floored ROWS). NVMain's unset-MATHeight
; default is stale regardless (fixed at Params construction time from the struct's
; default ROWS=65536, before this file's ROWS is read; see geometry()'s comment) --
; leaving it unset would truncate subArrayNum to 0 for any ROWS below 65536 and
; segfault in NVMObject::GetChild() on the first request (empty subarray-children
; vector). geometry() asserts ROWS is evenly divisible by MATHeight.
MATHeight {mat_height}

; --- Endurance ---
EnduranceModel {endurance_model}
EnduranceDist Uniform
EnduranceDistMean 1000000

; --- NVM Specific Logic ---
ClosePage 1
UseRefresh false
UsePrecharge true
EnergyModel NonVolatile
"""
    # M1 (T2 review fix round 1): validate the RENDERED text, not the in-memory
    # `timings` dict. Validating the dict left the dict-to-text step unguarded:
    # the reviewer proved that suppressing the tWP line in bounding mode still
    # passed validation and exited 0, with only the new tests catching it. Every
    # timing key is now read back out of the very string that is about to be
    # written, which closes the gap for the read split (I4) and the write split
    # (T2) at once. Still before any file I/O, so a rejected config is never
    # written.
    cfg_check = config_check_from_text(config_content, read_latency_ns, write_latency_ns,
                                        write_pulse_on_path)
    violations = validate_config(cfg_check)
    if violations:
        # Fatal, not a warning: a config with a rejected timing relationship must never be
        # written, since NVMain either silently corrupts admission or segfaults on it (see
        # validate_config()'s own violation messages). Refuse before any file I/O happens.
        print(f"    [!] Config validation FAILED for {base_name}_{arch_type}:")
        for problem in violations:
            print(f"        - {problem}")
        sys.exit(2)

    file_path = output_dir / f"{sys_model_name}.config"
    with open(file_path, 'w') as f:
        f.write(config_content)
    return sys_model_name

def generate_silicon_config(silicon_key, timing_entry, all_metrics, target_freq_mhz, output_dir,
                             queue_size=32, channels=1, decoder="Default",
                             endurance_model="RowModel", window_ns=250000000,
                             metrics_source="results/hardware_metrics.json",
                             write_pulse_on_path=False):
    """T2.8: generate one microsecond-silicon sensitivity full-DIMM config.

    Same template, geometry, energies, leakage, channels, decoder, endurance and
    queue settings as `timing_entry["parent"]`'s full-DIMM config -- only
    read_latency_ns/write_latency_ns are overridden (to the fabricated chip's own
    read/write latency) before compute_timings() runs inside
    generate_nvmain_config(). Architecture is always full_dimm; T2.8 defines no
    single/8chip/16chip silicon variants.

    Raises ValueError with a clear message if timing_entry["parent"] is missing
    from `all_metrics` (i.e. hardware_metrics.json has no entry for it -- run
    1_run_nvsim_hardware.py / 2_extract_hardware_metrics.py for that base model
    first).
    """
    parent = timing_entry["parent"]
    if parent not in all_metrics:
        raise ValueError(
            f"generate_silicon_config: parent hardware-metrics key {parent!r} "
            f"(required by silicon entry {silicon_key!r}) is missing from the "
            f"loaded hardware metrics -- have: {sorted(all_metrics)}. Run "
            f"1_run_nvsim_hardware.py and 2_extract_hardware_metrics.py for "
            f"{parent} first."
        )

    hw = dict(all_metrics[parent])
    hw["read_latency_ns"] = timing_entry["read_ns"]
    hw["write_latency_ns"] = timing_entry["write_ns"]

    header_extra = (
        "; --- T2.8 MICROSECOND-SILICON SENSITIVITY ---\n"
        "; Read/write timing below is sourced from a fabricated chip, NOT this\n"
        f"; project's own NVSim run. Citation: {timing_entry['citation']}.\n"
        "; Energies, leakage, area and organization remain NVSim's 22 nm values\n"
        f"; from parent hardware model {parent!r} unchanged: this is a timing-only\n"
        "; sensitivity study, not a re-simulation of the fabricated chip.\n"
        "; tRP is fixed at 1 cycle: ReRAM reads are non-destructive (no restore/\n"
        "; precharge phase), and the fabricated chip's read latency above is already\n"
        "; charged in full to tRCD + tCAS -- a latency-proportional tRP would\n"
        "; double-charge it (fix round 1 ruling, 2026-09).\n"
    )

    return generate_nvmain_config(
        silicon_key, hw, target_freq_mhz, output_dir, "full_dimm",
        queue_size=queue_size, channels=channels, decoder=decoder,
        endurance_model=endurance_model, window_ns=window_ns,
        header_extra=header_extra, metrics_source=metrics_source,
        write_pulse_on_path=write_pulse_on_path,
    )

def main():
    args = setup_args()
    root_dir = get_project_root()
    input_path = root_dir / args.input
    output_dir = Path(args.output_dir) if args.output_dir else root_dir / "simulators" / "nvmain" / "Config"

    # I5: a missing input used to print and `return`, i.e. exit 0 with nothing
    # generated, and the pipeline then simulated whatever configs happened to
    # be lying in the output directory from an earlier run.
    if not input_path.exists():
        print(f"[!] Input metrics file not found: {input_path}")
        print( "    Stage 3 cannot generate any NVMain config without it. Run "
               "1_run_nvsim_hardware.py and 2_extract_hardware_metrics.py first.")
        sys.exit(1)

    os.makedirs(output_dir, exist_ok=True)
    with open(input_path, 'r') as f:
        all_metrics = json.load(f)
    if not all_metrics:
        print(f"[!] Input metrics file is empty: {input_path}")
        sys.exit(1)

    architectures = ["single", "8chip", "16chip", "full_dimm"]
    generated = []

    print("=" * 60)
    print(f"MBMM STEP 3: SYSTEM ARCHITECTURE FACTORY ({args.freq} MHz)")
    print("=" * 60)

    try:
        for model_name, metrics in all_metrics.items():
            print(f"\n>>> Base Hardware: {model_name}")
            for arch in architectures:
                sys_name = generate_nvmain_config(model_name, metrics, args.freq, output_dir, arch, args.queue_size,
                                                   channels=args.channels, decoder=args.decoder,
                                                   endurance_model=args.endurance_model, window_ns=args.window_ns,
                                                   metrics_source=str(input_path),
                                                   write_pulse_on_path=args.write_pulse_on_path)
                if sys_name:
                    print(f"    [OK] Generated System Model: {sys_name}")
                    generated.append(sys_name)
                else:
                    print(f"    [SKIP] Protected native DRAM config.")

        if args.silicon:
            print("\n" + "=" * 60)
            print("T2.8: MICROSECOND-SILICON SENSITIVITY CONFIGS")
            print("=" * 60)
            for silicon_key, timing_entry in SILICON_TIMINGS.items():
                sys_name = generate_silicon_config(
                    silicon_key, timing_entry, all_metrics, args.freq, output_dir,
                    args.queue_size, channels=args.channels, decoder=args.decoder,
                    endurance_model=args.endurance_model, window_ns=args.window_ns,
                    metrics_source=str(input_path),
                    write_pulse_on_path=args.write_pulse_on_path)
                print(f"    [OK] Generated Silicon Sensitivity Model: {sys_name}")
                generated.append(sys_name)
    except (MissingHardwareMetric, ValueError) as e:
        # I5: a hardware entry missing a required key, or a silicon entry whose
        # parent is absent, stops Stage 3 with a non-zero exit instead of
        # leaving a partly-regenerated Config directory that Stage 4 would then
        # simulate as if it were complete.
        print(f"\n[!] Stage 3 ABORTED: {e}")
        sys.exit(1)

    # I6: record exactly which configs THIS run generated, so mbmm_master.py
    # can refuse to simulate any generated ReRAM/silicon config left behind by
    # an earlier run with different flags (an organization-1024 sensitivity run
    # left eight of them in the shared live Config directory before this fix).
    if args.manifest_out:
        manifest_path = Path(args.manifest_out)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(manifest_path, 'w') as f:
            json.dump({
                "generated_models": sorted(generated),
                "output_dir": str(output_dir),
                "input": str(input_path),
                "freq_mhz": args.freq,
                "queue_size": args.queue_size,
                "channels": args.channels,
                "decoder": args.decoder,
                "endurance_model": args.endurance_model,
                "window_ns": args.window_ns,
                "silicon": bool(args.silicon),
                "write_pulse_on_path": bool(args.write_pulse_on_path),
            }, f, indent=4)
        print(f"\n[OK] Wrote generated-config manifest: {manifest_path}")

    print("\n" + "=" * 60)
    print(f"SUCCESS: {len(generated)} system-level configurations generated.")
    print("=" * 60)

if __name__ == "__main__":
    main()
