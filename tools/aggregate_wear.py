#!/usr/bin/env python3
"""T5.3: DIMM-wide wear aggregation from NVMain's per-subarray wear counters.

Parses the per-subarray `wearLocations`/`wearTotalWrites`/`wearMaxWrites`
triple (and the newer `wearTopLocations` top-16 dict) that
simulators/nvmain/CLAUDE.md PATCH LOG entry 3 (T1.3) added to
`SubArray::CalculateStats`, aggregates them DIMM-wide (every
channel.rank.bank.subarray in the file), and reports the Start-Gap decoder's
own `startGapMoves`/`startGapWrites`/`startGapOutOfRegion`/
`startGapBoundaryAlias` counters (patch log entry 5, T1.4) when present.

This tool does NOT compute a wear-leveling efficiency or a projected
lifetime -- that is endurance_sensitivity.py's job, and it works from the
trace's own measured spatial write distribution, not from these in-
simulation counters (see task-T5.3-dispatch.md's ruling and
endurance_sensitivity.py's module docstring for why: a 250 ms NVMain window
is far too short for Start-Gap's gap position to move meaningfully, so the
in-window hot-spot factor here is expected to be nearly IDENTICAL with the
decoder on and off -- that expectation is exactly what this tool's two
outputs, run with and without `Decoder StartGap`, are for: they validate the
MECHANISM and its performance cost, not a leveling efficiency).

`Wear_Max_Writes` and the hot-spot-factor-vs-touched-mean number reuse
process_metrics.extract_dimm_wear_stats directly (imported, not
reimplemented) so the two tools can never silently diverge on that
calculation; the touched-location count, total-writes sum, whole-capacity
hot-spot factor, decoder counters, top-16 merge and mem_writes cross-check
are new to this tool.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import process_metrics as pm  # noqa: E402

BYTES_PER_LINE = 64
GIB = 1024 ** 3
MIB = 1024 ** 2

# global-constraints.md: "forced 2048x2048 subarrays, mux 64, for 1T1R and
# 1S1R (1024x1024 as sensitivity). NVSim output must print '2048 Rows x 2048
# Columns'." Used only as a heuristic bound for the granularity inference
# below (RowModel keys wear by row -> touched-location counts bounded by the
# row count; WordModel keys by word -> can exceed it).
FORCED_ROWS = 2048

STARTGAP_STAT_NAMES = (
    "startGapMoves", "startGapWrites", "startGapOutOfRegion",
    "startGapBoundaryAlias",
)


class WearMismatchError(Exception):
    """sum(wearTotalWrites) != sum(mem_writes) for a run that has wear
    stats -- the dispatch's mandated hard-fail."""


def _all_values(content, stat_name):
    """Every numeric occurrence of `<...>.<stat_name> <value>` in content.

    Mirrors process_metrics.extract_dimm_wear_stats's own internal
    _all_values pattern exactly (same regex), per the dispatch's
    instruction to reuse its regexes rather than invent new ones; that
    function's own two aggregate numbers (Wear_Max_Writes and the
    hot-spot factor vs touched mean) are reused directly, by import, in
    aggregate_wear() below -- this local helper only fills in the
    additional raw sums (touched locations, total writes) that function
    does not expose.
    """
    pattern = rf'{re.escape(stat_name)}\s+([\d\.eE\-]+)'
    try:
        return [float(m) for m in re.findall(pattern, content)]
    except ValueError:
        return []


def _sum_mem_writes(content):
    return sum(int(m) for m in re.findall(r'\.mem_writes\s+(\d+)', content))


def extract_startgap_stats(content):
    """Parse the Start-Gap decoder's four stats. These are STATIC counters
    shared by every decoder instance (patch log entry 5: "shared across the
    six decoder instances the factory creates"), so every occurrence in the
    file should carry the identical value; disagreement is a WARNING (not a
    hard fail -- this tool reports, aggregate_wear's hard-fail is reserved
    for the wear/mem_writes cross-check) and the max is used defensively.

    Returns (values_dict_or_None, warnings_list). values_dict is None if
    the run has no Start-Gap decoder (an all-read trace, or a run without
    `Decoder StartGap` -- both legitimate: patch log entry 5's own
    verification notes a read-only trace against the decoder gives
    startGapMoves/startGapWrites both 0, which IS "present", so absence
    here specifically means the stat lines are not in the file at all).
    """
    warnings = []
    values = {}
    any_present = False
    for name in STARTGAP_STAT_NAMES:
        occurrences = _all_values(content, name)
        if not occurrences:
            values[name] = None
            continue
        any_present = True
        distinct = set(occurrences)
        if len(distinct) > 1:
            warnings.append(
                f"WARNING: disagreeing {name} occurrences in this stats "
                f"file: {sorted(distinct)} -- using the max ({max(distinct)})")
            values[name] = max(distinct)
        else:
            values[name] = occurrences[0]

    if not any_present:
        return None, warnings

    if values.get("startGapBoundaryAlias"):
        warnings.append(
            f"WARNING: startGapBoundaryAlias = {values['startGapBoundaryAlias']:g} "
            f"(non-zero): this run's wear numbers may touch the Start-Gap "
            f"region's aliased boundary line (simulators/nvmain/CLAUDE.md "
            f"PATCH LOG entry 5's disclosed limitation) -- worth a second "
            f"look before trusting them.")

    return values, warnings


def _parse_top_locations(content):
    """Merge every subarray's own wearTopLocations {addr: writes, ...} into
    one DIMM-wide top-16.

    Correct because a DIMM-wide top-16 address must also be within ITS OWN
    subarray's local top-16 (removing every other subarray's entries can
    only improve, never worsen, its local rank) -- so the union of every
    subarray's reported top-16 is guaranteed to contain the true DIMM-wide
    top 16, and re-sorting that (bounded, <=16*n_subarrays) union is exact,
    not an approximation.
    """
    entries = []  # (writes, addr, subarray_path)
    for m in re.finditer(
            r'([\w.]+)\.wearTopLocations\s+(\{[^}]*\})', content):
        subarray_path, dict_str = m.group(1), m.group(2)
        for pair in re.finditer(r'(\d+)\s*:\s*(\d+)', dict_str):
            addr, writes = int(pair.group(1)), int(pair.group(2))
            entries.append((writes, addr, subarray_path))
    # Same tie-break as SubArray.cpp's std::greater<pair<count,addr>> sort:
    # higher count first, ties broken by higher address first.
    entries.sort(key=lambda t: (-t[0], -t[1]))
    return [{"address": addr, "writes": writes, "subarray": path}
            for writes, addr, path in entries[:16]]


def _infer_capacity_lines(content):
    """Read the DIMM's total capacity from the stats file's own
    'defaultMemory.channelN.FRFCFS capacity is <X> MB.' lines (one per
    channel; NVMain prints these in binary MB = MiB, powers of two in every
    file checked), summed across channels. Returns (capacity_lines, note)
    or (None, note) if the line is absent (e.g. a hand-built test fixture).
    """
    matches = re.findall(r'capacity is\s+([\d.]+)\s*MB', content)
    if not matches:
        return None, "no 'capacity is <N> MB' line found in this stats file"
    total_mib = sum(float(m) for m in matches)
    capacity_lines = int(total_mib * MIB // BYTES_PER_LINE)
    return capacity_lines, (
        f"inferred from {len(matches)} 'capacity is <N> MB' line(s) "
        f"summing to {total_mib:g} MiB")


def infer_wear_granularity(locations_list):
    """Best-effort inference of whether the wear counters shown are keyed
    by row (RowModel) or by word (WordModel) -- simulators/nvmain/
    CLAUDE.md PATCH LOG entry 3's skew-trace verification: RowModel gives
    wearLocations==1 (keyed by row only) where WordModel gives one entry
    per distinct 64-byte word written. Heuristic, not a certainty (the
    stats file does not itself record which EnduranceModel produced it):
    if every subarray's touched-location count stays within the forced
    row count (2048, global-constraints.md), RowModel is far more likely
    (a WordModel run touching many distinct addresses would typically
    exceed 2048 touched locations somewhere); otherwise WordModel is
    inferred. Says "unknown" when there is nothing to infer from.
    """
    if not locations_list:
        return "unknown (no wear stats present in this file)"
    if max(locations_list) <= 0:
        return "unknown (all-zero wear stats: NullModel, or an all-read trace)"
    if max(locations_list) <= FORCED_ROWS:
        return (f"RowModel (inferred: every subarray's touched-location "
                 f"count stays <= {FORCED_ROWS}, the forced row count -- "
                 f"RowModel keys wear by row; see simulators/nvmain/"
                 f"CLAUDE.md PATCH LOG entry 3. Not certain: a very cold "
                 f"WordModel run could also stay under this bound.)")
    return (f"WordModel (inferred: some subarray's touched-location count "
             f"exceeds the forced {FORCED_ROWS}-row count, which a "
             f"row-keyed model cannot produce -- see simulators/nvmain/"
             f"CLAUDE.md PATCH LOG entry 3.)")


def aggregate_wear(content, capacity_lines=None, infer_capacity=True):
    """Compute the full DIMM-wide wear aggregation dict for one stats file's
    content. Raises WearMismatchError on the mandated hard-fail.
    """
    locations = _all_values(content, "wearLocations")
    total_writes = _all_values(content, "wearTotalWrites")

    sum_locations = int(sum(locations))
    sum_total_writes = int(sum(total_writes))

    # Reused by import, not recomputed: process_metrics.extract_dimm_wear_stats
    # already implements Wear_Max_Writes and the hot-spot-factor-vs-touched-
    # mean calculation exactly as this tool needs them.
    dimm_max_writes, hotspot_vs_touched_mean = pm.extract_dimm_wear_stats(content)

    mean_touched = (sum_total_writes / sum_locations) if sum_locations > 0 else None

    mem_writes_total = _sum_mem_writes(content)
    has_wear_stats = sum_locations > 0
    if has_wear_stats and sum_total_writes != mem_writes_total:
        raise WearMismatchError(
            f"sum(wearTotalWrites)={sum_total_writes} != "
            f"sum(mem_writes)={mem_writes_total} for a run that has wear "
            f"stats (sum(wearLocations)={sum_locations} > 0); NVMain's own "
            f"wear counter and its completed-write counter disagree -- "
            f"treat this run's wear numbers as untrustworthy until "
            f"resolved. Per the dispatch, this is a hard failure, not a "
            f"warning.")

    capacity_note = None
    if capacity_lines is None and infer_capacity:
        capacity_lines, capacity_note = _infer_capacity_lines(content)
    elif capacity_lines is not None:
        capacity_note = "given explicitly (--capacity-gib/--capacity-lines)"

    hotspot_vs_capacity = None
    if (capacity_lines and capacity_lines > 0 and dimm_max_writes is not None
            and sum_total_writes > 0):
        whole_capacity_mean = sum_total_writes / capacity_lines
        if whole_capacity_mean > 0:
            hotspot_vs_capacity = dimm_max_writes / whole_capacity_mean

    startgap, startgap_warnings = extract_startgap_stats(content)
    top16 = _parse_top_locations(content)
    granularity = infer_wear_granularity(locations)

    return {
        "touched_locations": sum_locations,
        "total_writes": sum_total_writes,
        "max_writes": dimm_max_writes,
        "mean_writes_touched": mean_touched,
        "hotspot_factor_vs_touched_mean": hotspot_vs_touched_mean,
        "hotspot_factor_vs_whole_capacity_mean": hotspot_vs_capacity,
        "capacity_lines": capacity_lines,
        "capacity_note": capacity_note,
        "mem_writes_total": mem_writes_total,
        "wear_mem_writes_match": (sum_total_writes == mem_writes_total
                                    if has_wear_stats else None),
        "has_wear_stats": has_wear_stats,
        "wear_granularity": granularity,
        "startgap": startgap,
        "startgap_warnings": startgap_warnings,
        "top16": top16,
        "n_subarrays_reporting": len(locations),
    }


def format_report(result, source_path=""):
    lines = []
    lines.append(f"=== DIMM-wide wear aggregation: {source_path} ===")
    if not result["has_wear_stats"]:
        lines.append("No wear stats measured (NullModel EnduranceModel, or "
                       "an all-read trace against a real endurance model) -- "
                       "every wear metric below is blank, not zero.")
    lines.append(f"subarrays reporting: {result['n_subarrays_reporting']}")
    lines.append(f"touched locations: {result['touched_locations']:,}")
    lines.append(f"total writes: {result['total_writes']:,}")
    lines.append(f"max writes to one location: "
                  f"{result['max_writes'] if result['max_writes'] is not None else '-'}")
    mwt = result["mean_writes_touched"]
    lines.append(f"mean writes per touched location: "
                  f"{mwt:.4g}" if mwt is not None else "mean writes per touched location: -")
    hvt = result["hotspot_factor_vs_touched_mean"]
    lines.append(f"hot-spot factor vs touched mean: "
                  f"{hvt:.4g}" if hvt is not None else "hot-spot factor vs touched mean: -")
    hvc = result["hotspot_factor_vs_whole_capacity_mean"]
    if hvc is not None:
        lines.append(f"hot-spot factor vs whole-capacity mean: {hvc:.4g} "
                      f"(capacity {result['capacity_lines']:,} lines, "
                      f"{result['capacity_note']})")
    else:
        lines.append(f"hot-spot factor vs whole-capacity mean: - "
                      f"({result['capacity_note'] or 'no capacity available'})")
    lines.append(f"mem_writes (summed over channels): "
                  f"{result['mem_writes_total']:,}")
    if result["has_wear_stats"]:
        lines.append(f"wear/mem_writes cross-check: "
                      f"{'OK' if result['wear_mem_writes_match'] else 'MISMATCH'}")
    lines.append(f"wear counter granularity: {result['wear_granularity']}")

    sg = result["startgap"]
    if sg is None:
        lines.append("Start-Gap decoder stats: not present in this file "
                       "(no `Decoder StartGap` in this run's config).")
    else:
        lines.append("Start-Gap decoder stats: "
                      f"startGapMoves={sg['startGapMoves']}, "
                      f"startGapWrites={sg['startGapWrites']}, "
                      f"startGapOutOfRegion={sg['startGapOutOfRegion']}, "
                      f"startGapBoundaryAlias={sg['startGapBoundaryAlias']}")
    for w in result["startgap_warnings"]:
        lines.append(w)

    if result["top16"]:
        lines.append("top 16 hottest locations (DIMM-wide):")
        for i, e in enumerate(result["top16"], 1):
            lines.append(f"  {i:2d}. addr/row {e['address']}: {e['writes']} "
                          f"writes ({e['subarray']})")
    else:
        lines.append("top 16 hottest locations: none reported "
                       "(no wearTopLocations stats in this file)")
    return "\n".join(lines)


def build_argparser():
    p = argparse.ArgumentParser(
        description="DIMM-wide aggregation of NVMain's per-subarray wear "
                     "counters (touched locations, total/max writes, "
                     "hot-spot factors, Start-Gap decoder stats).")
    p.add_argument("stats_file", help="an NVMain stats_<model>_<trace>.out file")
    p.add_argument("--capacity-gib", type=float, default=None,
                    help="module capacity in GiB, for the whole-capacity "
                         "hot-spot factor (overrides inference from the "
                         "stats file's own 'capacity is <N> MB' lines)")
    p.add_argument("--capacity-lines", type=int, default=None,
                    help="module capacity directly in 64-byte lines "
                         "(overrides --capacity-gib and inference)")
    p.add_argument("--out-dir", default="results")
    p.add_argument("--no-json", action="store_true",
                    help="skip writing the results/wear_<model>_<trace>.json file")
    return p


def main(argv=None):
    args = build_argparser().parse_args(argv)
    stats_path = Path(args.stats_file)
    content = stats_path.read_text()

    capacity_lines = args.capacity_lines
    if capacity_lines is None and args.capacity_gib is not None:
        capacity_lines = int(args.capacity_gib * GIB // BYTES_PER_LINE)

    try:
        result = aggregate_wear(content, capacity_lines=capacity_lines)
    except WearMismatchError as e:
        print(f"HARD FAIL: {e}", file=sys.stderr)
        return 1

    print(format_report(result, source_path=str(stats_path)))

    if not args.no_json:
        model = pm.classify_technology(stats_path.name) or "unknown"
        trace = pm.extract_benchmark(stats_path.name)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        json_path = out_dir / f"wear_{model}_{trace}.json"
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nwrote {json_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
