#!/usr/bin/env python3
"""T5.3: endurance (lifetime) sensitivity from the MEASURED write distribution.

CONTROLLER RULING ON "MEASURED" (task-T5.3-dispatch.md): the plan's original
idea -- measure wear-leveling efficiency straight from NVMain's wear counters
with the Start-Gap decoder on and off -- does not work. In a 250 ms window a
whole-channel Start-Gap decoder (one gap move per 100 writes, ~67 M lines per
channel at the revision's 8 GiB baseline) moves its gap a few tens of
thousands of lines; the in-window hot-spot factor is therefore the same with
and without it (leveling acts over YEARS, not milliseconds). So:

  - What this script MEASURES is the spatial write distribution: writes per
    64-byte line inside the trace's window (or span, for a short trace).
  - What it PROJECTS is lifetime under each of four wear-leveling schemes,
    assuming that measured pattern repeats forever -- the same long-horizon
    assumption every paper cited in documents/.../endurance_deep_dive.md
    section 3.1 makes. Every docstring and printed line below says
    "projected from the measured write distribution", never "measured
    efficiency" -- that phrase would misdescribe what is actually computed.
  - NVMain's in-simulation Start-Gap (tools/aggregate_wear.py) still
    validates the mechanism and its performance cost; it is not used here to
    derive a leveling efficiency, for the reason above.

FIX ROUND 1 (independent review): the review's brute-force simulator of the
Start-Gap mechanism confirmed the sliding-window model itself (the round-1
formula is the exact dual of the mechanism) and confirmed the sub-region
counter-example, but found the gap-move overhead was on the wrong side of
the equation (wear, not rate -- see "GAP-MOVE OVERHEAD" below) and that
`find_min_rotations`/`required_endurance_*` did not round-trip. Both are
fixed here; see the "FIX ROUND 1" comments at each affected function and the
report's "Fix round 1" section for the before/after numbers.

======================================================================
DERIVATION OF THE FOUR SCHEMES (worked from first principles; the dispatch's
formulas are reproduced below and checked against this derivation -- see
"WHERE THE DISPATCH'S FORMULAS WERE CHECKED" below for the one place a literal
reading is ambiguous and how it was resolved).

Notation: c_i = window writes to logical line i. C = sum(c_i) over whatever
population is in scope (module-wide for NONE/IDEAL, per-region for
START_GAP/RANDOMIZED_START_GAP). W = the real write rate (writes/s) that
scope receives. N = lines in scope. E = endurance (writes to failure).
T = projected lifetime (seconds).

1. NONE (no leveling). Each line i wears at rate W * c_i / C (its measured
   share of the traffic, scaled to the real rate). The hottest line
   (c_max = max(c_i)) fails first:

       T = E / (W * c_max / C)                                        (1)

2. IDEAL (uniform leveling, the book's current formula with efficiency
   forced to 1). Every one of the N_module lines in the whole module wears
   at the same rate W / N_module, whatever the real spatial distribution is:

       T = N_module * E / W                                           (2)

3. START_GAP over a region of R logical lines (module-wide by default,
   R = N_module, one region, matching the NVMain decoder's default
   whole-channel region; --region-mib splits the module into consecutive
   R-line blocks instead). This is Qureshi et al., MICRO 2009 Fig. 4:
   N = R data lines occupy R+1 physical lines via two registers START, GAP.
   GapMove (one step per `psi` writes to the region): if GAP>0, GAP--; else
   GAP=R, START=(START+1) mod R. A full "rotation" here means one such wrap
   (GAP counts R, R-1, ..., 0, then wraps): that is R+1 gap moves, i.e.
   (R+1)*psi writes to the region, after which START has incremented by
   exactly 1 and EVERY logical line's physical host has shifted by one
   physical slot (this follows directly from Remap: physical slot depends on
   (logical + START) mod R, so incrementing START by 1 shifts every mapping
   uniformly). Call this quantity of writes and elapsed time one rotation:

       tau_g = (R+1) * psi / W_g          seconds per rotation           (3)

   W_g = W * C_g / C is this region's share of the real rate, where C_g is
   the region's measured window writes. (Round 1 divided tau_g by an extra
   (1+1/psi) "gap-move overhead" factor here; FIX ROUND 1 moved that
   overhead to the wear side instead -- see "GAP-MOVE OVERHEAD" below --
   so W_g and tau_g are now exactly the plain rate/writes-per-rotation, with
   no correction factor.)

   After k rotations, a given PHYSICAL line has been the host of k
   consecutive LOGICAL lines (one per rotation, since each rotation shifts
   every mapping by exactly one slot) -- consecutive because START only ever
   moves by +1 each rotation, so a fixed physical slot's owner logical line
   decreases (mod R) by exactly 1 each rotation. During the rotation it
   hosts logical line i, it accumulates that line's share of the region's
   per-rotation traffic, (R+1)*psi * c_i/C_g (the region does (R+1)*psi
   total writes per rotation, split across lines exactly as the measured
   distribution splits real traffic, by the "same pattern repeats forever"
   projection assumption) -- PLUS one gap-move relocation write, since a
   full rotation sweeps the gap boundary past every physical position
   exactly once, physically copying that position's data to the new gap
   slot (see "GAP-MOVE OVERHEAD"). So the worst physical line's total wear
   after k rotations is (R+1)*psi/C_g times the maximum, over any k
   CONSECUTIVE logical lines (circularly, since START wraps mod R), of the
   sum of their c_i, PLUS k (one relocation write per rotation) -- with a
   full R-line cycle (k a multiple of R) contributing exactly C_g per cycle
   from the main term (every logical line visited exactly once) and exactly
   R from the relocation term:

       wear_max(k) = (R+1)*psi/C_g * [ floor(k/R)*C_g + maxwin_g(k mod R) ] + k  (4)

   maxwin_g(m) = max over circular starting position of the sum of c_i over
   m consecutive logical lines in the region (maxwin_g(0) = 0). The region
   fails at the smallest k with wear_max(k) >= E; T_g = k * tau_g, refined
   by linear interpolation between wear_max(k-1) and wear_max(k) within the
   last rotation (see startgap_region_lifetime). FIRST-ROTATION DEATH: if
   even one rotation's worth of traffic to the hottest single line, plus its
   one relocation write, already exceeds E, i.e.
   (R+1)*psi/C_g * c_max_g + 1 >= E, Start-Gap never gets a chance to
   relieve it and T_g becomes a bound on NONE's formula for this region --
   see "FIRST-ROTATION DEATH IS A LOWER BOUND" below for why round 1's
   "T_g = NONE's formula exactly" was itself only a lower bound, and how
   that is now reported. Module lifetime = min over regions that received
   any measured writes (dispatch's ruling: an untouched region cannot be
   shown to fail on this projection horizon).

4. RANDOMIZED_START_GAP: a static seeded random permutation of logical
   lines across the WHOLE MODULE, then scheme 3 on the permuted array
   (Qureshi MICRO 2009's randomized Start-Gap / address-space
   randomization). Only the M measured (written) lines are given random
   target positions -- random.sample(range(N_module), M) is used directly
   (no N_module-sized array is ever materialized), which the dispatch notes
   is fine for M up to about 10 M (LBM's ~6.7 M measured lines qualifies).

GAP-MOVE OVERHEAD (FIX ROUND 1). The dispatch says: "Add the gap-move write
overhead (one extra line write per psi writes, +1/psi on W) as a stated,
applied factor." Round 1 read this literally as a RATE correction
(W_g_eff = W_g*(1+1/psi)) and flagged the placement as ambiguous. The
independent review's physical argument settles it: a gap move physically
RELOCATES the boundary line -- it is a real write to a real physical line,
i.e. WEAR, not a change in how fast the host accepts logical writes (W_g
itself is unaffected; the device still accepts exactly W_g logical writes
per second, and the relocation write is one MORE physical write layered on
top, once per rotation, not a change to that acceptance rate). This is now
implemented as the "+k" term in eq. (4) (one extra write credited to
whichever physical line the rotation swept past, once per rotation, over
the SAME k, at the SAME rate W_g -- no rate inflation). At psi=100 the two
accountings differ by under 1% (the relocation term is a roughly R/((R+1)*
psi) fraction of the main term for a fully-covered region, ~1/100 at
psi=100 for large R); at psi=10 the two accountings differ by several
percent, and can differ in EITHER direction depending on how close to a
first-rotation boundary the answer falls (see
tests/test_endurance_sensitivity.py's psi=10 hot-block test for a
hand-derived, measurable example: the round-1 (rate) accounting would have
given ~9.00 s where the round-2 (wear) accounting gives ~9.80 s here, an
8.9% difference, in the direction round-1 UNDER-estimated lifetime for this
example -- the sign is not universal, only the existence of a measurable
gap is).

FIRST-ROTATION DEATH IS A LOWER BOUND (FIX ROUND 1, important defect #2).
The review's own brute-force simulator of the mechanism shows that in the
first-rotation-death branch, the true survival time is NOT simply NONE's
formula: Start-Gap's gap sweeps past the hot line at some point DURING that
first rotation (the sweep is uniform in time across the rotation, so the
hot line is relieved at a uniformly-distributed point in [0, tau_g) rather
than only at the rotation's end), after which the FRESH physical line the
hot line was moved to must independently accumulate E more writes before
IT dies. The true lifetime therefore lies in [T_NONE, 2*T_NONE) depending on
where in the rotation the relief happens to land, and this script's
T_NONE value is the WORST-CASE-OVER-GAP-PHASE lower bound (the review
measured true/model ratios of 0.60 and 0.62 on synthetic first-rotation-
death cases -- consistent with "some value in [1, 2)x the lower bound", not
close to either endpoint). This script keeps reporting the conservative
lower bound as `lifetime_years` (and required-endurance is computed from
that same conservative function, so it stays conservative too -- a real
device is never WORSE than this bound implies), but now also reports
`lifetime_upper_years` = 2 * lifetime_years for exactly the rows where
`first_rotation_death` is true (1x elsewhere), so the true value's bracket
is visible rather than silently collapsed to one worst-case number.

REQUIRED ENDURANCE IS THE EXACT INVERSE OF THE LIFETIME FUNCTION (FIX ROUND
1, critical defect #1). Round 1 computed required_endurance_startgap/
_randomized via a SEPARATE, ad-hoc formula (wear_max evaluated at
k = round(T_target/tau), ignoring first-rotation death and landing on
wear_max's plateaus) that did not round-trip against the table's own
lifetime function: feeding the reported E_req back into lifetime() did not
reproduce T_target, sometimes by orders of magnitude (see the report's "Fix
round 1" section for the reproduced AlexNet numbers). Every scheme's
required_endurance_* now calls invert_lifetime_for_endurance(), which
brackets and bisects the SAME lifetime_*/startgap_module_lifetime_prepared
function the table calls, to the target lifetime -- so the round-trip is
true by construction (whatever the table's lifetime function says at E_req
IS >= T_target, by definition of the search), and first-rotation death and
wear_max's plateaus are handled automatically (they are just features of
the function being inverted, not something the inverse needs to know about
separately). Every lifetime_* function used this way is non-decreasing in
E (asserted at the bisection's bracket) by construction: E only appears in
each formula's numerator (eq. 1, 2, 4), and eq. (4) is used through a
minimal-k search that is monotone in the target by construction (see
find_min_rotations).

WHERE THE DISPATCH'S FORMULAS WERE CHECKED. Every formula above was
re-derived from the Start-Gap mechanism (not copied from the dispatch) and
then compared against the dispatch's text; they agree, other than the two
FIX ROUND 1 corrections above (both are refinements the review's brute-force
simulator forced, not new disagreements with the dispatch's own text -- the
dispatch never specified the first-rotation-death survival distribution or
gave a general required-endurance procedure). The dispatch's worked examples
(uniform module, brief's 3.47/3.58 yr check, all-writes-to-one-line at
psi=10 and psi=1000) were hand-recomputed independently in the test suite's
comments (tests/test_endurance_sensitivity.py) before any code was written
against them, and matched (round 1); round 2 re-derives the Start-Gap-scheme
numbers that the gap-move-overhead move affects (the IDEAL-only brief number
is unaffected). The sub-region "RANDOMIZED approaches IDEAL" claim remains
disproved as reported in round 1 (re-confirmed here: the counter-example's
mechanism -- C_g cancelling out of the lifetime formula when the limiting
region holds an adjacent pair -- is unrelated to which side the gap-move
term sits on, and the review's own derivation agrees the round-1 defeat of
that claim was correct, per the coordinator's message).

ALGORITHMIC NOTE (performance, not a modeling change). maxwin_sparse()
implements maxwin_g exactly as specified (checked against a brute-force O(R)
scan in the property tests). The minimal-k search (find_min_rotations) no
longer reduces to a single O(n) two-pointer sweep the way round 1's pure
multiplicative formula did, because eq. (4)'s "+k" term makes the
per-rotation contribution depend on k itself, not just on k mod R -- see
find_min_rotations's own docstring for the two-level search this now uses
(an O(1) analytic guess for the number of full cycles, refined by a small
bounded correction loop, each step an O(n) weighted-window sweep
(min_window_for_weighted_target) rather than the plain-sum
min_window_for_sum round 1 used). Region bucketing/sorting (O(n log n)) is
now cached once per (line_counts identity, region_lines) via
_prepare_regions and reused across every E/write-reduction combination that
shares it (round 1 re-sorted on every call); required_endurance_* also
reuses this cache instead of re-bucketing per bisection step. See the
report's "Fix round 1" section for LBM's new wall time under this scheme.
"""

import argparse
import csv
import json
import math
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import process_metrics as pm  # noqa: E402  (path insert must precede this)

# --- Constants -------------------------------------------------------------

BYTES_PER_LINE = 64
GIB = 1024 ** 3

# Time-base convention (minor fix 4a): 365-day year, matching
# endurance_deep_dive.md and the book. Printed once in the stdout summary
# and in the CSV's header comment so the convention travels with the data,
# not just this source file.
DAYS_PER_YEAR = 365
SECONDS_PER_YEAR = DAYS_PER_YEAR * 24 * 3600

DEFAULT_WINDOW_NS = 250_000_000
DEFAULT_CPUFREQ_MHZ = 3000
DEFAULT_PSI = 100
DEFAULT_SEED = 1234
DEFAULT_PROGRESS_EVERY = 2_000_000

ENDURANCE_AXIS = (1e4, 1e6, 1e7)
CAPACITY_GIB_AXIS = (8, 64, 128)
WRITE_REDUCTION_AXIS = (1.0, 4.5)
SCHEMES = ("NONE", "IDEAL", "START_GAP", "RANDOMIZED_START_GAP")

# Qureshi MICRO 2009: normalized endurance vs ideal, none/Start-Gap/randomized
# Start-Gap. "literature, different workloads and 256-byte lines" -- shown
# next to the projected values, never substituted for them.
LITERATURE_EFFICIENCY = {
    "NONE": 0.05,
    "START_GAP": 0.53,
    "RANDOMIZED_START_GAP": 0.97,
}

T_TARGET_10YR_S = 10 * SECONDS_PER_YEAR


def capacity_lines(capacity_gib):
    """Module capacity in 64-byte lines: GiB * 2^30 / 64 (exact, both powers of 2)."""
    return capacity_gib * GIB // BYTES_PER_LINE


# --- Trace parsing -----------------------------------------------------------

def parse_trace_window(trace_path, window_ns=DEFAULT_WINDOW_NS,
                        cpufreq_mhz=DEFAULT_CPUFREQ_MHZ,
                        progress_every=DEFAULT_PROGRESS_EVERY, quiet=False):
    """Stream trace_path ONCE; tally WRITE records with cycle < window_cycles
    per 64-byte line (line = address >> 6), matching tools/validate_trace.py's
    own window_cycles = window_ns * cpufreq_mhz // 1000 formula so a given
    --window-ns/--cpufreq-mhz pair means the same window there and here.

    Stops reading as soon as a record's cycle reaches window_cycles (the
    window is then provably covered; nothing past it can change the window
    tally) -- this lets a trace far longer than the window (LBM, 4.6 GB) be
    read only up to the point that matters, not end to end.

    FIX ROUND 1 (minor 4c): window-vs-burst is decided from whether the
    window was actually REACHED (a record with cycle >= window_cycles was
    seen, which is exactly the early-exit condition below), not from
    `last_cycle - first_cycle >= window_cycles` -- round 1's proxy was wrong
    whenever the trace's own last two records straddled the boundary in a
    way that made the span alone ambiguous, and conflated "trace is long
    enough" with "we actually observed enough of it". The boundary record
    itself (the one that triggers the break, whose cycle is already >=
    window_cycles and is therefore not counted towards writes_in_window
    either) is EXCLUDED from `records_read`, since it was read from the file
    but not actually processed as part of the window/span being reported.

    Returns a dict: line_counts (dict line -> write count in window/span),
    writes_in_window, distinct_lines, first_cycle, last_cycle_seen,
    window_cycles, rate_basis ("window" or "burst"), offered_rate (writes/s).
    """
    window_cycles = window_ns * cpufreq_mhz // 1000
    cycle_ns = 1000.0 / cpufreq_mhz  # ns per cycle, matches process_metrics'
                                       # elapsed_ns = cycles * (1000.0/cpufreq_mhz)

    line_counts = {}
    writes_in_window = 0
    reads_in_window = 0
    first_cycle = None
    last_cycle = None
    n_records = 0
    window_reached = False

    with open(trace_path, "r") as f:
        for raw in f:
            rec = raw.rstrip("\n")
            if not rec:
                continue
            fields = rec.split()
            if len(fields) != 5:
                continue  # tolerate stray lines; tools/validate_trace.py is
                          # the strict validator, not this streaming reader
            cycle_s, op, addr_s, _data, _thread = fields
            cycle = int(cycle_s)

            if cycle >= window_cycles:
                window_reached = True
                break  # boundary record: not counted in records_read/last_cycle

            if first_cycle is None:
                first_cycle = cycle
            last_cycle = cycle
            n_records += 1
            if progress_every and not quiet and n_records % progress_every == 0:
                print(f"  ...{trace_path}: {n_records:,} records read, "
                      f"at cycle {cycle:,} (window ends at {window_cycles:,})",
                      file=sys.stderr)
            if op == "W":
                addr = int(addr_s, 16)
                line = addr >> 6
                line_counts[line] = line_counts.get(line, 0) + 1
                writes_in_window += 1
            elif op == "R":
                reads_in_window += 1

    if first_cycle is None and not window_reached:
        raise ValueError(f"{trace_path}: zero records")
    if first_cycle is None:
        # window_reached on the very first record (window_cycles <= 0, or a
        # degenerate trace): treat as an empty, window-covering trace.
        first_cycle = 0
        last_cycle = 0

    span_cycles = last_cycle - first_cycle
    window_seconds = window_ns / 1e9
    span_seconds = span_cycles * cycle_ns * 1e-9

    if window_reached:
        rate_basis = "window"
        offered_rate = writes_in_window / window_seconds if window_seconds else 0.0
    else:
        rate_basis = "burst"
        offered_rate = writes_in_window / span_seconds if span_seconds > 0 else 0.0

    return {
        "trace": str(trace_path),
        "line_counts": line_counts,
        "writes_in_window": writes_in_window,
        "reads_in_window": reads_in_window,
        "distinct_lines": len(line_counts),
        "records_read": n_records,
        "first_cycle": first_cycle,
        "last_cycle_seen": last_cycle,
        "span_cycles": span_cycles,
        "span_seconds": span_seconds,
        "window_cycles": window_cycles,
        "window_seconds": window_seconds,
        "window_reached": window_reached,
        "rate_basis": rate_basis,
        "offered_rate": offered_rate,
    }


def read_admitted_stats(stats_path):
    """Admitted write rate from an NVMain stats file: sum('.mem_writes') over
    channels, divided by elapsed time from the file's own "Exiting at cycle"
    line. Elapsed time reuses process_metrics.resolve_clocks_mhz (dispatch:
    "reuse process_metrics.resolve_clocks_mhz and its elapsed-time logic by
    import"), so a run recorded at a non-default CPUFreq still resolves
    correctly; CPUFreq is the GLOBAL/CPUFreq domain "Exiting at cycle" is
    printed in (see process_metrics.py's CPUFREQ_MHZ comment for the source
    proof), NOT the model's own CLK domain.
    """
    content = Path(stats_path).read_text()

    writes = re.findall(r'\.mem_writes\s+(\d+)', content)
    if not writes:
        raise ValueError(f"{stats_path}: no '.mem_writes' stat found")
    admitted_writes = sum(int(w) for w in writes)

    exit_match = re.search(r'Exiting at cycle\s+(\d+)', content)
    if exit_match is None:
        raise ValueError(f"{stats_path}: no 'Exiting at cycle' line found")
    exit_cycle = int(exit_match.group(1))

    _clk_mhz, cpufreq_mhz = pm.resolve_clocks_mhz(content, technology="",
                                                    filename=str(stats_path))
    elapsed_ns = exit_cycle * (1000.0 / cpufreq_mhz)
    elapsed_s = elapsed_ns * 1e-9
    if elapsed_s <= 0:
        raise ValueError(f"{stats_path}: non-positive elapsed time")

    return {
        "stats_path": str(stats_path),
        "admitted_writes": admitted_writes,
        "elapsed_s": elapsed_s,
        "cpufreq_mhz": cpufreq_mhz,
        "admitted_rate": admitted_writes / elapsed_s,
    }


# --- Scheme 1 & 2: NONE, IDEAL ----------------------------------------------

def lifetime_none(W, c_max, C, E):
    """NONE (no leveling): T = E / (W * c_max / C). See eq. (1)."""
    if C <= 0 or c_max <= 0 or W <= 0:
        return float("inf")
    hot_rate = W * c_max / C
    return E / hot_rate if hot_rate > 0 else float("inf")


def lifetime_ideal(W, n_module, E):
    """IDEAL: T = N_module * E / W. See eq. (2)."""
    if W <= 0:
        return float("inf")
    return n_module * E / W


# --- Sparse circular-window primitives --------------------------------------

def maxwin_sparse(positions, counts, R, m):
    """maxwin_g(m): max sum of counts over any m consecutive integer
    positions on a circular ring of size R, given SPARSE (position, count)
    pairs (positions distinct, sorted ascending, all in [0, R)).

    O(n): a two-pointer sweep over the positions doubled by +R (handling
    wraparound), restricting candidate window starts to the n data points
    (starting a window strictly before the next data point never increases
    its sum, so checking only data-point starts is exhaustive). This is the
    reference implementation checked directly against a brute-force O(R)
    scan (tests/test_endurance_sensitivity.py).
    """
    n = len(positions)
    if n == 0 or m <= 0:
        return 0
    total = sum(counts)
    if m >= R:
        return total
    pos2 = positions + [p + R for p in positions]
    cnt2 = counts + counts
    n2 = len(pos2)
    best = 0
    j = 0
    window_sum = 0
    for i in range(n):
        if j < i:
            j = i
            window_sum = 0
        end = pos2[i] + m
        while j < n2 and pos2[j] < end:
            window_sum += cnt2[j]
            j += 1
        if window_sum > best:
            best = window_sum
        window_sum -= cnt2[i]
    return best


def min_window_for_sum(positions, counts, R, tau):
    """Smallest window length m (>= 0) such that SOME circular window of
    that length has sum >= tau, i.e. the smallest m with maxwin_sparse(m)
    >= tau. Returns None if tau exceeds the total (unreachable at any
    m <= R). Kept as a directly-tested primitive (round 1's property tests
    still exercise it); the minimal-k search now uses the weighted variant
    below instead, because eq. (4)'s "+k" term needs a target that mixes
    the window's sum AND its own length (see find_min_rotations).
    """
    n = len(positions)
    if n == 0:
        return None
    total = sum(counts)
    if tau <= 0:
        return 0
    if tau > total:
        return None

    pos2 = positions + [p + R for p in positions]
    cnt2 = counts + counts
    n2 = len(pos2)

    best = None
    i = 0
    window_sum = 0
    for j in range(n2):
        window_sum += cnt2[j]
        while window_sum >= tau:
            candidate = pos2[j] - pos2[i] + 1
            if best is None or candidate < best:
                best = candidate
            window_sum -= cnt2[i]
            i += 1
    return best


def min_window_for_weighted_target(positions, counts, R, A, tau):
    """Smallest window length m (0 <= m <= R) such that SOME circular window
    of that length satisfies A*sum(window) + m >= tau -- i.e. the smallest m
    with A*maxwin_sparse(m) + m >= tau.

    Well posed because A*maxwin_sparse(m)+m is STRICTLY increasing in m:
    maxwin_sparse is non-decreasing (a longer window's best sum can only be
    >= a shorter one's) and "+m" is strictly increasing, so their sum is
    strictly increasing, giving a single well-defined crossing point --
    found here by binary search over m, calling maxwin_sparse (O(n)) at
    each of the O(log R) steps.

    FIX ROUND 1 DEFECT (this replaces an earlier, WRONG two-pointer
    attempt): a first version of this function tried to generalize
    min_window_for_sum's O(n) two-pointer sweep by tracking, for each
    (i, j) point-cluster, its own tight enclosing span pos[j]-pos[i]+1 as
    the candidate m. That misses a real case: the true minimal m for a
    cluster can be LARGER than its tight span, because padding the window
    past the cluster's own edge (while it still captures the SAME points,
    i.e. the padding lands in an empty gap) keeps the sum fixed but still
    grows the "+m" term, which can be exactly what tips A*sum+m over tau
    when the tight span alone falls just short. Concretely (found while
    testing against a direct linear scan, not by the property test's
    random cases -- it takes a wide, specific gap to trigger): with A
    around 2.24e6 a cluster with tight span 55362 and sum 22 gave
    A*22+55362 = 49268529.3, just under a target of 49268544; the true
    answer pads the SAME cluster to m=55377 (A*22+55377 = 49268544.3),
    which the tight-span-only search could never propose. Binary search
    over m sidesteps this entirely, since it asks maxwin_sparse for the
    actual best sum AT a chosen m (padding included, since maxwin_sparse
    already searches over all windows of exactly that length) rather than
    only considering the tight spans of specific point clusters. This
    function is called O(log R) times per find_min_rotations correction
    step, and find_min_rotations itself only for the small endurance axis
    (not per required-endurance bisection step -- see
    required_endurance_region_direct, which avoids searching entirely).
    """
    if tau <= 0:
        return 0
    n = len(positions)
    if n == 0:
        # No measured points at all: maxwin_sparse is always 0, so the
        # target reduces to m >= tau (an empty window still counts, since
        # A*0+m=m) -- the smallest integer m >= tau, if it fits in the ring.
        m = math.ceil(tau)
        return m if m <= R else None
    total = sum(counts)
    if A * total + R < tau:
        return None  # unreachable even filling the whole ring

    lo, hi = 0, R
    while lo < hi:
        mid = (lo + hi) // 2
        val = A * maxwin_sparse(positions, counts, R, mid) + mid
        if val >= tau:
            hi = mid
        else:
            lo = mid + 1
    return lo


def find_min_rotations(positions, counts, R, C_g, psi, E):
    """Smallest k >= 0 with wear_max(k) >= E, eq. (4):
    wear_max(k) = (R+1)*psi/C_g * (floor(k/R)*C_g + maxwin_g(k mod R)) + k.

    FIX ROUND 1 (critical defect #1, first cause): round 1's find_min_
    rotations searched only among k of the form q*R + m with
    q = floor(target/C_g) fixed by the MAIN term alone, which is not
    minimal once the "+k" term is added: k also grows with q directly (not
    only through the main term), so the true minimal q must account for
    BOTH q*(R+1)*psi/C_g*C_g = q*(R+1)*psi (main term per cycle) AND q*R
    (the "+k" term's own per-cycle contribution) -- i.e. q's true
    per-cycle wear contribution is B = (R+1)*psi + R, not (R+1)*psi alone.
    Missing the "+R" made round 1 systematically pick a q that was too
    small whenever an exact multiple of C_g was targeted (reported by the
    review: 652/3000 brute-force draws violated minimality) -- with too
    small a q, min_window_for_sum would still find A SATISFYING m (just a
    needlessly large one), so the result was valid but not minimal.

    Correct search: k = q*R + m, m in [0, R). Achievability of a given q
    (does SOME m in [0,R) reach the remaining target?) is monotonic in q,
    since increasing q strictly decreases the remaining target
    tau_q = E - q*B while the maximum reachable amount within one cycle
    (at m = R-1) is fixed -- so there is a unique smallest feasible q,
    found by an O(1) analytic guess (from the maximum single-cycle
    reachable amount, computed once) refined by a small bounded correction
    loop (each step one O(n) min_window_for_weighted_target call). Returns
    (k, m).
    """
    if C_g <= 0:
        return None, None
    A = (R + 1) * psi / C_g
    B = A * C_g + R  # = (R+1)*psi + R: wear added by one full R-line cycle

    if R <= 1:
        # Degenerate: no real "ring" to rotate through; every write lands on
        # the same single physical line forever.
        k = math.ceil((E - 1) / (A + 1)) if A + 1 > 0 else 0
        return max(k, 0), 0

    max_reachable = A * maxwin_sparse(positions, counts, R, R - 1) + (R - 1)

    def achievable(q):
        tau = E - q * B
        m = min_window_for_weighted_target(positions, counts, R, A, tau)
        ok = m is not None and m < R
        return ok, m

    if E <= max_reachable:
        q_guess = 0
    else:
        q_guess = max(0, math.ceil((E - max_reachable) / B))

    ok, m = achievable(q_guess)
    q = q_guess
    guard = 0
    if ok:
        # walk q down while (q-1) is still achievable (the analytic guess
        # can overshoot by a small amount due to the max_reachable bound
        # being only an upper estimate of what a SPECIFIC m achieves).
        while q > 0:
            ok2, m2 = achievable(q - 1)
            if not ok2:
                break
            q, m = q - 1, m2
            guard += 1
            if guard > 10_000:
                raise RuntimeError("find_min_rotations: correction loop did "
                                     "not converge (down)")
    else:
        while not ok:
            q += 1
            ok, m = achievable(q)
            guard += 1
            if guard > 10_000:
                raise RuntimeError("find_min_rotations: correction loop did "
                                     "not converge (up)")

    return q * R + m, m


def wear_max_at_k(positions, counts, R, C_g, psi, k):
    """wear_max(k), eq. (4), evaluated directly (used for the linear
    interpolation refinement and cross-checks, not inside the k-search
    itself). FIX ROUND 1: adds the "+k" gap-move relocation term."""
    if C_g <= 0 or k < 0:
        return 0.0
    q, m = divmod(k, R)
    mw = maxwin_sparse(positions, counts, R, m)
    return (R + 1) * psi / C_g * (q * C_g + mw) + k


# --- Scheme 3: START_GAP -----------------------------------------------------

def startgap_region_profile(positions, counts, R, psi, C_g, E):
    """The W-INDEPENDENT part of one region's Start-Gap lifetime at this E:
    first_rotation_death, hot_ratio (c_max_g/C_g, only meaningful in the
    death branch), rotations_k and frac (only meaningful otherwise).
    Neither find_min_rotations nor the linear-interpolation frac involves
    W_g anywhere -- W_g only converts a rotation count into wall-clock
    seconds (see startgap_region_lifetime_from_profile) -- so this,
    the expensive part (find_min_rotations' O(n log R) search), can be
    computed ONCE per (region, psi, E) and reused for every W_g
    (every rate_basis/write_reduction combination) that shares it. See
    startgap_module_profiles_prepared/evaluate_all for the caching this
    enables (FIX ROUND 1, minor 4e extended: this is what made the LBM
    run's `lifetime_years` axis tractable, on top of the required-endurance
    fix which already avoided a search entirely).
    """
    c_max_g = max(counts)
    first_rotation_wear = (R + 1) * psi / C_g * c_max_g + 1

    if first_rotation_wear >= E:
        return {"first_rotation_death": True, "hot_ratio": c_max_g / C_g,
                "rotations_k": 1, "at_m": None, "frac": None}

    k, m = find_min_rotations(positions, counts, R, C_g, psi, E)

    if k <= 0:
        frac = 0.0
    else:
        wear_km1 = wear_max_at_k(positions, counts, R, C_g, psi, k - 1)
        wear_k = wear_max_at_k(positions, counts, R, C_g, psi, k)
        frac = ((E - wear_km1) / (wear_k - wear_km1)) if wear_k > wear_km1 else 0.0
        frac = min(max(frac, 0.0), 1.0)

    return {"first_rotation_death": False, "hot_ratio": None,
            "rotations_k": k, "at_m": m, "frac": frac}


def startgap_region_lifetime_from_profile(profile, R, psi, W_g, E):
    """Cheap (O(1)): turn a W-independent profile (startgap_region_profile)
    into an actual lifetime_s/lifetime_upper_s for a specific W_g, without
    re-running find_min_rotations. lifetime_upper_s is 2x lifetime_s
    exactly in the first-rotation-death branch (the review's brute-force
    bracket, [T_NONE, 2*T_NONE)) and equal to lifetime_s otherwise.
    """
    if profile["first_rotation_death"]:
        hot_rate = W_g * profile["hot_ratio"]
        T = E / hot_rate if hot_rate > 0 else float("inf")
        T_upper = T if T == float("inf") else 2.0 * T
        return {"lifetime_s": T, "lifetime_upper_s": T_upper,
                "first_rotation_death": True, "rotations_k": 1, "at_m": None}

    k = profile["rotations_k"]
    tau_g = (R + 1) * psi / W_g
    T = 0.0 if k <= 0 else tau_g * ((k - 1) + profile["frac"])
    return {"lifetime_s": T, "lifetime_upper_s": T, "first_rotation_death": False,
            "rotations_k": k, "at_m": profile["at_m"]}


def startgap_region_lifetime(positions, counts, R, psi, W_g, C_g, E):
    """One-off convenience: startgap_region_profile + _lifetime_from_profile.
    Batch callers (evaluate_all) compute the profile once per E and reuse
    it across every W_g via startgap_module_profiles_prepared /
    startgap_module_lifetime_from_profiles instead of calling this
    per-(region, W_g) combination.

    FIX ROUND 1: no more (1+1/psi) rate inflation (gap-move overhead now
    lives in wear_max's "+k" term, via find_min_rotations); the
    first-rotation-death check gets the same "+1" relocation-write term.
    """
    profile = startgap_region_profile(positions, counts, R, psi, C_g, E)
    return startgap_region_lifetime_from_profile(profile, R, psi, W_g, E)


def _bucket_regions(line_counts, region_lines):
    """Partition a {line: count} dict into {region_index: {local_pos: count}}."""
    regions = {}
    for line, count in line_counts.items():
        g = line // region_lines
        local = line - g * region_lines
        regions.setdefault(g, {})[local] = count
    return regions


def _prepare_regions(line_counts, region_lines):
    """Bucket + sort ONCE: {region_index: (sorted_positions, counts, C_g)}
    for every region that received a measured write. FIX ROUND 1 (minor
    4e): reused across every E/write-reduction combination that shares the
    same (line_counts, region_lines) instead of re-bucketing/re-sorting on
    every lifetime/required-endurance call (round 1 re-sorted from scratch
    every time, which dominated the LBM run's cost -- see the report).
    """
    regions = _bucket_regions(line_counts, region_lines)
    prepared = {}
    for g, d in regions.items():
        positions = sorted(d.keys())
        counts = [d[p] for p in positions]
        C_g = sum(counts)
        if C_g > 0:
            prepared[g] = (positions, counts, C_g)
    return prepared


def startgap_module_profiles_prepared(prepared_regions, region_lines, psi, E):
    """{region_index: (profile, C_g)} for every written region, at this E --
    the W-independent (expensive) part of scheme 3, computed once per
    (prepared_regions, region_lines, E) and reused across every
    rate_basis/write_reduction combination that shares it (see
    evaluate_all)."""
    profiles = {}
    for g, (positions, counts, C_g) in prepared_regions.items():
        profiles[g] = (startgap_region_profile(positions, counts,
                                                  region_lines, psi, C_g, E),
                        C_g)
    return profiles


def startgap_module_lifetime_from_profiles(profiles, region_lines, psi, W, C, E):
    """Scheme 3 over the whole module from a profiles cache (see
    startgap_module_profiles_prepared): cheap, no searching. Takes the min
    over regions that received writes (dispatch: "Module lifetime = min
    over regions that received writes")."""
    if C <= 0 or not profiles:
        return {"lifetime_s": float("inf"), "lifetime_upper_s": float("inf"),
                "first_rotation_death": False, "rotations_k": None,
                "at_m": None, "region": None, "n_regions_written": 0}

    best = None
    for g, (profile, C_g) in profiles.items():
        W_g = W * C_g / C
        result = startgap_region_lifetime_from_profile(profile, region_lines,
                                                          psi, W_g, E)
        result["region"] = g
        if best is None or result["lifetime_s"] < best["lifetime_s"]:
            best = result
    best["n_regions_written"] = len(profiles)
    return best


def startgap_module_lifetime_prepared(prepared_regions, region_lines, psi, W, C, E):
    """Scheme 3 over the whole module, using pre-bucketed/sorted region data
    from _prepare_regions (see its docstring): one-off convenience
    (profiles + rescale in one call). Batch callers (evaluate_all) compute
    startgap_module_profiles_prepared once per E and call
    startgap_module_lifetime_from_profiles directly for each W.
    """
    profiles = startgap_module_profiles_prepared(prepared_regions,
                                                    region_lines, psi, E)
    return startgap_module_lifetime_from_profiles(profiles, region_lines,
                                                    psi, W, C, E)


def startgap_module_lifetime(line_counts, region_lines, psi, W, C, E):
    """Convenience wrapper: _prepare_regions + startgap_module_lifetime_prepared,
    for one-off calls (tests, single-E lookups). Batch callers (evaluate_all)
    prepare once and call the _prepared variant directly.
    """
    prepared = _prepare_regions(line_counts, region_lines)
    return startgap_module_lifetime_prepared(prepared, region_lines, psi, W, C, E)


# --- Scheme 4: RANDOMIZED_START_GAP -----------------------------------------

def randomize_line_counts(line_counts, n_module, seed):
    """Draw distinct random physical positions in [0, n_module) for the M
    measured (written) lines only -- random.sample over range(n_module),
    fine for M up to about 10 M per the dispatch. Deterministic given seed
    (sorted input order before sampling)."""
    rng = random.Random(seed)
    items = sorted(line_counts.items())
    m = len(items)
    if m > n_module:
        raise ValueError(
            f"{m} written lines exceeds module capacity {n_module} lines; "
            f"cannot assign distinct random positions")
    new_positions = rng.sample(range(n_module), m)
    return {new_positions[i]: items[i][1] for i in range(m)}


def randomized_startgap_module_lifetime(line_counts, n_module, region_lines,
                                         psi, W, C, E, seed=DEFAULT_SEED):
    """Scheme 4: randomize_line_counts, then scheme 3 (one-off convenience
    wrapper; see randomized_startgap_module_lifetime_prepared for the
    cached-placement batch path)."""
    permuted = randomize_line_counts(line_counts, n_module, seed)
    return startgap_module_lifetime(permuted, region_lines, psi, W, C, E)


# --- Required endurance: exact inverse of the lifetime function ------------

ANY_ENDURANCE_SUFFICES_NOTE = "any endurance suffices at this write rate"


def invert_lifetime_for_endurance(lifetime_fn, T_target, e_lo=1.0,
                                    rel_tol=1e-6, max_bracket_doublings=200,
                                    max_bisect_iters=200):
    """FIX ROUND 1 (critical defect #1): the smallest E such that
    lifetime_fn(E) >= T_target, found by bracketing then bisecting
    lifetime_fn directly -- the SAME function the endurance table calls for
    its lifetime_years column, so the round-trip (lifetime_fn(E_req) >=
    T_target, and lifetime_fn(E_req * (1-rel_tol)) < T_target) is true by
    construction, not by a second, independently-derived formula that could
    (and, in round 1, did) drift out of sync.

    lifetime_fn must be non-decreasing in E; asserted on the final bracket
    (a cheap, meaningful sanity check -- every lifetime_* function here is
    non-decreasing in E by construction, since E only ever appears in a
    numerator, but this catches any future regression directly rather than
    trusting that invariant silently).

    Returns (E, note). FIX ROUND 2 (minor #2): round 1 returned the bracket
    floor `e_lo` (1.0) SILENTLY whenever lifetime_fn(e_lo) already met (or
    exceeded, including infinitely) T_target -- a real, meaningful answer
    (the write rate is so low, or the lifetime formula so generous, that
    even the smallest endurance considered already clears the target), but
    indistinguishable in the return value from "the search actually solved
    for E=1.0". `note` is ANY_ENDURANCE_SUFFICES_NOTE in that case, None
    otherwise, so callers (and the CSV's required_endurance_note column)
    can tell the two apart explicitly.
    """
    lt_lo = lifetime_fn(e_lo)
    if lt_lo >= T_target:
        return e_lo, ANY_ENDURANCE_SUFFICES_NOTE

    e_hi = max(e_lo * 2, 2.0)
    lt_hi = lifetime_fn(e_hi)
    doublings = 0
    while lt_hi < T_target:
        e_lo, lt_lo = e_hi, lt_hi
        e_hi *= 2
        lt_hi = lifetime_fn(e_hi)
        doublings += 1
        if doublings > max_bracket_doublings:
            raise RuntimeError(
                "invert_lifetime_for_endurance: could not bracket a target "
                "lifetime within the doubling budget -- lifetime_fn may not "
                "be non-decreasing in E, or the target is unreachable")

    assert lt_lo <= T_target, "lifetime_fn must be non-decreasing in E"

    for _ in range(max_bisect_iters):
        mid = (e_lo + e_hi) / 2.0
        lt_mid = lifetime_fn(mid)
        if lt_mid >= T_target:
            e_hi = mid
        else:
            assert lt_mid >= lt_lo, "lifetime_fn must be non-decreasing in E"
            e_lo, lt_lo = mid, lt_mid
        if e_hi - e_lo <= rel_tol * e_hi:
            break

    return e_hi, None


def required_endurance_none(W, c_max, C, T_target=T_TARGET_10YR_S):
    """Returns (E, note); see invert_lifetime_for_endurance."""
    if C <= 0 or W <= 0 or c_max <= 0:
        return None, None
    return invert_lifetime_for_endurance(
        lambda E: lifetime_none(W, c_max, C, E), T_target)


def required_endurance_ideal(W, n_module, T_target=T_TARGET_10YR_S):
    """Returns (E, note); see invert_lifetime_for_endurance."""
    if W <= 0:
        return None, None
    return invert_lifetime_for_endurance(
        lambda E: lifetime_ideal(W, n_module, E), T_target)


def required_endurance_region_direct(positions, counts, R, psi, W_g, C_g,
                                       T_target):
    """Closed-form exact inverse of startgap_region_lifetime's own T(E) for
    ONE region -- no search. Performance note: required_endurance_startgap
    (below) is called once per (capacity, write_reduction, rate_basis)
    combination, and a naive bisection on startgap_module_lifetime would
    call find_min_rotations (and therefore min_window_for_weighted_target's
    O(n log R) binary search) at every one of ~30-40 bisection steps -- far
    too slow on a multi-million-line trace. This function instead runs
    startgap_region_lifetime's own two-piece definition of T(E) BACKWARDS
    directly:

      - Below the first-rotation-death boundary, T(E) = E/hot_rate is
        exactly linear (NONE's own formula for this region), so its
        inverse is the trivial closed form E = hot_rate * T_target -- this
        is also FIX ROUND 1's important defect #2 fix in the required-
        endurance direction: required endurance from a region that is
        first-rotation-death-limited all the way out to T_target reduces
        to exactly NONE's own required endurance for that region (see
        tests/test_endurance_sensitivity.py's GCC-shaped test).
      - Above that boundary, T(E) = tau_g*((k-1)+frac) where k is the
        smallest integer with wear_max(k)>=E and frac linearly interpolates
        E between wear_max(k-1) and wear_max(k) -- i.e. T is a PIECEWISE
        LINEAR, invertible function of a continuous k = (T/tau_g) + 1 - 1
        = T/tau_g. Running that backwards: given T_target, compute the
        (generally non-integer) k_real = T_target/tau_g directly, then
        E_req = wear_max(floor(k_real)) interpolated towards
        wear_max(ceil(k_real)) by k_real's fractional part -- the EXACT
        same two integer points and the EXACT same linear interpolation
        lifetime() itself would use, so this is bit-for-bit what bisecting
        startgap_region_lifetime to convergence would return (verified
        directly against invert_lifetime_for_endurance in the test suite),
        just two wear_max_at_k calls (O(n) each) instead of a ~30-40-step
        search.
    """
    c_max_g = max(counts)
    hot_rate = W_g * c_max_g / C_g
    if hot_rate <= 0:
        return float("inf")

    e_thresh = (R + 1) * psi / C_g * c_max_g + 1  # = wear_max_at_k(..., 1)
    t_thresh = e_thresh / hot_rate

    if T_target <= t_thresh:
        return hot_rate * T_target

    tau_g = (R + 1) * psi / W_g
    k_real = T_target / tau_g
    k_floor = int(math.floor(k_real))
    k_ceil = k_floor + 1
    w_floor = wear_max_at_k(positions, counts, R, C_g, psi, k_floor)
    w_ceil = wear_max_at_k(positions, counts, R, C_g, psi, k_ceil)
    frac = k_real - k_floor
    return w_floor + frac * (w_ceil - w_floor)


def required_endurance_startgap_prepared(prepared_regions, region_lines, psi,
                                           W, C, T_target=T_TARGET_10YR_S):
    """E at which T = T_target for Start-Gap, using the pre-bucketed region
    cache (see _prepare_regions): the max over written regions of each
    region's own required_endurance_region_direct (the module needs every
    region to individually survive T_target, so the module's required
    endurance is set by whichever region needs the most -- FIX ROUND 1,
    important defect #2: this is the conservative, lower-bound
    required-endurance, since it inverts each region's own lower-bound
    lifetime_s, never lifetime_upper_s).

    Returns (E, note) for API symmetry with required_endurance_none/ideal
    (FIX ROUND 2, minor #2); note is always None here in practice --
    required_endurance_region_direct is a direct closed-form algebraic
    inverse with no bounded-search floor to silently fall back to, unlike
    invert_lifetime_for_endurance's bisection.
    """
    if C <= 0 or not prepared_regions:
        return None, None
    worst = 0.0
    for g, (positions, counts, C_g) in prepared_regions.items():
        W_g = W * C_g / C
        e_req = required_endurance_region_direct(positions, counts,
                                                    region_lines, psi, W_g,
                                                    C_g, T_target)
        if e_req > worst:
            worst = e_req
    return worst, None


def required_endurance_startgap(line_counts, region_lines, psi, W, C,
                                  T_target=T_TARGET_10YR_S):
    """One-off convenience wrapper; see required_endurance_startgap_prepared.
    Returns (E, note)."""
    if C <= 0 or not line_counts:
        return None, None
    prepared = _prepare_regions(line_counts, region_lines)
    return required_endurance_startgap_prepared(prepared, region_lines, psi,
                                                  W, C, T_target)


def required_endurance_randomized(line_counts, n_module, region_lines, psi,
                                    W, C, seed=DEFAULT_SEED,
                                    T_target=T_TARGET_10YR_S):
    """Returns (E, note)."""
    if C <= 0 or not line_counts:
        return None, None
    permuted = randomize_line_counts(line_counts, n_module, seed)
    return required_endurance_startgap(permuted, region_lines, psi, W, C, T_target)


# --- Driver: build the long-format table ------------------------------------

def evaluate_all(line_counts, rate_by_basis, psi=DEFAULT_PSI, seed=DEFAULT_SEED,
                  region_mib=None, trace_name="",
                  endurance_axis=ENDURANCE_AXIS, capacity_axis=CAPACITY_GIB_AXIS,
                  write_reduction_axis=WRITE_REDUCTION_AXIS,
                  rate_burst_info=None):
    """Build the long-format row list. rate_by_basis: {"offered": rate, or
    "admitted": rate, ...} (writes/s, un-reduced). C = total measured window
    writes (same for every rate basis: only the RATE differs, not the
    measured spatial distribution).

    rate_burst_info: optional {rate_basis: (is_burst, span_ms)} (FIX ROUND
    2, important #1). Round 1 only ever printed the "*** BURST RATE ***"
    banner to stdout (print_summary); the CSV/Typst table itself carried no
    trace of it, so a burst-extrapolated rate (e.g. AlexNet OFMAP's ~3.0e10
    writes/s from a 4.5 us burst) looked identical to a genuine sustained
    "offered" measurement to anyone reading results/endurance_table.csv or
    the Typst snippet directly. Every row now carries `rate_is_burst`
    ("true"/"false") and `trace_span_ms`, sourced per rate_basis from this
    dict (defaults to not-burst/blank for any rate_basis not present --
    "admitted" never is a burst in this sense, since it comes from NVMain's
    own completed-write counters over the stats file's own elapsed time,
    not from the trace's own span).

    FIX ROUND 1 (minor 4e, extended): capacity is the outer loop so the
    region bucketing/sorting (original AND randomized placement) is
    prepared once per capacity and reused across every rate_basis/
    write_reduction/E combination. On top of that, the expensive part of
    the lifetime search (startgap_module_profiles_prepared, i.e.
    find_min_rotations) is W-INDEPENDENT (see startgap_region_profile's
    docstring), so it is computed once per (capacity, E) and reused across
    every rate_basis/write_reduction combination too, instead of
    re-searching per (capacity, rate_basis, write_reduction, E) as an
    earlier version of this function did. required_endurance_startgap_
    prepared already avoids searching entirely (see
    required_endurance_region_direct), so it stays inside the
    rate_basis/write_reduction loop (T_target's answer genuinely does
    depend on W) but costs little.
    """
    C = sum(line_counts.values())
    c_max = max(line_counts.values()) if line_counts else 0
    rate_burst_info = rate_burst_info or {}
    rows = []

    for capacity_gib in capacity_axis:
        n_module = capacity_lines(capacity_gib)
        region_lines = (int(region_mib * (2**20) // BYTES_PER_LINE)
                         if region_mib else n_module)
        region_mib_col = region_mib if region_mib else ""

        prepared_orig = _prepare_regions(line_counts, region_lines)
        permuted = randomize_line_counts(line_counts, n_module, seed) if line_counts else {}
        prepared_rand = _prepare_regions(permuted, region_lines)

        profiles_orig_by_E = {E: startgap_module_profiles_prepared(
                                    prepared_orig, region_lines, psi, E)
                                for E in endurance_axis}
        profiles_rand_by_E = {E: startgap_module_profiles_prepared(
                                    prepared_rand, region_lines, psi, E)
                                for E in endurance_axis}

        for rate_basis, base_rate in rate_by_basis.items():
            is_burst, span_ms = rate_burst_info.get(rate_basis, (False, None))
            rate_is_burst_col = "true" if is_burst else "false"
            span_ms_col = span_ms if span_ms is not None else ""

            for write_reduction in write_reduction_axis:
                W = base_rate / write_reduction

                req_none, note_none = required_endurance_none(W, c_max, C)
                req_ideal, note_ideal = required_endurance_ideal(W, n_module)
                req_sg, note_sg = required_endurance_startgap_prepared(
                    prepared_orig, region_lines, psi, W, C)
                req_rsg, note_rsg = required_endurance_startgap_prepared(
                    prepared_rand, region_lines, psi, W, C)
                req_by_scheme = {"NONE": req_none, "IDEAL": req_ideal,
                                  "START_GAP": req_sg,
                                  "RANDOMIZED_START_GAP": req_rsg}
                note_by_scheme = {"NONE": note_none, "IDEAL": note_ideal,
                                    "START_GAP": note_sg,
                                    "RANDOMIZED_START_GAP": note_rsg}

                for E in endurance_axis:
                    t_ideal = lifetime_ideal(W, n_module, E)
                    t_none = lifetime_none(W, c_max, C, E)
                    sg = startgap_module_lifetime_from_profiles(
                        profiles_orig_by_E[E], region_lines, psi, W, C, E)
                    rsg = startgap_module_lifetime_from_profiles(
                        profiles_rand_by_E[E], region_lines, psi, W, C, E)

                    results = {
                        "NONE": {"lifetime_s": t_none, "lifetime_upper_s": t_none,
                                  "first_rotation_death": "", "rotations_k": ""},
                        "IDEAL": {"lifetime_s": t_ideal, "lifetime_upper_s": t_ideal,
                                   "first_rotation_death": "", "rotations_k": ""},
                        "START_GAP": sg,
                        "RANDOMIZED_START_GAP": rsg,
                    }

                    for scheme in SCHEMES:
                        r = results[scheme]
                        lifetime_yr = (r["lifetime_s"] / SECONDS_PER_YEAR
                                        if r["lifetime_s"] not in (None, float("inf"))
                                        else float("inf"))
                        lifetime_upper_yr = (r["lifetime_upper_s"] / SECONDS_PER_YEAR
                                              if r["lifetime_upper_s"] not in
                                              (None, float("inf"))
                                              else float("inf"))
                        efficiency = (r["lifetime_s"] / t_ideal
                                       if t_ideal not in (None, 0, float("inf"))
                                       and r["lifetime_s"] != float("inf")
                                       else (1.0 if scheme == "IDEAL" else None))
                        rows.append({
                            "trace": trace_name,
                            "rate_basis": rate_basis,
                            "rate_is_burst": rate_is_burst_col,
                            "trace_span_ms": span_ms_col,
                            "write_reduction": write_reduction,
                            "capacity_gib": capacity_gib,
                            "endurance": E,
                            "scheme": scheme,
                            "region_mib": region_mib_col,
                            "psi": psi,
                            "seed": seed,
                            "lifetime_years": lifetime_yr,
                            "lifetime_upper_years": lifetime_upper_yr,
                            "efficiency_vs_ideal": efficiency,
                            "first_rotation_death": r.get("first_rotation_death", ""),
                            "rotations_k": r.get("rotations_k", ""),
                            "required_endurance_10yr": req_by_scheme[scheme],
                            "required_endurance_note": note_by_scheme[scheme] or "",
                        })
    return rows


CSV_FIELDS = ["trace", "rate_basis", "rate_is_burst", "trace_span_ms",
              "write_reduction", "capacity_gib",
              "endurance", "scheme", "region_mib", "psi", "seed",
              "lifetime_years", "lifetime_upper_years", "efficiency_vs_ideal",
              "first_rotation_death", "rotations_k", "required_endurance_10yr",
              "required_endurance_note"]

CSV_KEY_FIELDS = ["trace", "rate_basis", "write_reduction", "capacity_gib",
                   "endurance", "scheme", "region_mib", "psi"]


def _row_key(row):
    return tuple(str(row[f]) for f in CSV_KEY_FIELDS)


def write_csv(rows, path):
    """Write rows fresh (no dedup/merge -- used by tests and one-shot
    callers). main() uses upsert_csv instead for the append-across-runs path."""
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def upsert_csv(rows, path):
    """FIX ROUND 1 (minor 4d): append-without-duplicating. Rows are keyed by
    (trace, rate_basis, write_reduction, capacity_gib, endurance, scheme,
    region_mib, psi); re-running a trace (same key fields) REPLACES its
    rows rather than accumulating duplicates. Reads any existing CSV, drops
    rows whose key matches one of the new rows, appends the new rows, and
    rewrites atomically (write to a temp file in the same directory, then
    os.replace -- so a crash mid-write never leaves a truncated/corrupt CSV
    in place of a good one).
    """
    path = Path(path)
    new_keys = {_row_key(r) for r in rows}
    kept = []
    if path.exists():
        with open(path, "r", newline="") as f:
            reader = csv.DictReader(f)
            for old_row in reader:
                if _row_key(old_row) not in new_keys:
                    kept.append(old_row)

    all_rows = kept + rows
    tmp_path = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    with open(tmp_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in all_rows:
            writer.writerow(row)
    os.replace(tmp_path, path)
    return len(kept), len(rows)


def _row_is_burst(row):
    """Robust truthy check for the rate_is_burst column: "true" (written by
    evaluate_all) if read straight from a Python row dict, or the same
    string if round-tripped through a CSV DictReader."""
    return str(row.get("rate_is_burst", "")).strip().lower() == "true"


def write_typst_table(rows, path, endurance=1e6, region_mib=None):
    """Primary slice: E = endurance, write_reduction = 1.0, every rate basis,
    capacity and scheme, as a Typst #table snippet.

    FIX ROUND 1 (minor 4d): filters on the CURRENT run's region_mib value
    (round 1 always filtered on `region_mib == ""`, so a --region-mib run
    produced an EMPTY table -- every row's region_mib column was the given
    MiB value, never blank).

    FIX ROUND 2 (important #1): if any row in this slice was extrapolated
    from a burst (rate_is_burst), the trace name in the title comment gets
    a visible "*" footnote marker and a note paragraph is appended after
    the table stating the burst span and warning against reading the
    required-endurance column as a sustained-rate requirement -- round 1's
    burst warning only ever reached stdout (print_summary's "*** BURST
    RATE ***" banner), never the CSV or this Typst snippet, so anyone
    reading either file directly (not this script's own stdout) had no way
    to tell a burst-extrapolated row from a genuine sustained measurement.
    """
    region_mib_col = region_mib if region_mib else ""
    slice_rows = [r for r in rows if r["endurance"] == endurance
                  and r["write_reduction"] == 1.0
                  and r["region_mib"] == region_mib_col]
    trace_name = slice_rows[0]["trace"] if slice_rows else ""
    burst_rows = [r for r in slice_rows if _row_is_burst(r)]
    marker = "*" if burst_rows else ""

    lines = []
    lines.append(f"// Endurance sensitivity, E = {endurance:.0e}, {trace_name}{marker}")
    lines.append("// Projected from the measured write distribution (see")
    lines.append("// endurance_sensitivity.py); not a measured efficiency.")
    lines.append(f"// Lifetimes use a {DAYS_PER_YEAR}-day year.")
    lines.append("#table(")
    lines.append("  columns: (auto, auto, auto, auto, auto),")
    lines.append("  table.header([*Rate basis*], [*Capacity (GiB)*], [*Scheme*], "
                  "[*Lifetime (yr)*], [*Efficiency vs ideal*]),")
    for r in slice_rows:
        lt = r["lifetime_years"]
        lt_s = "inf" if lt == float("inf") else f"{lt:.3g}"
        eff = r["efficiency_vs_ideal"]
        eff_s = "-" if eff is None else f"{eff:.3g}"
        rate_basis_s = r["rate_basis"] + ("*" if _row_is_burst(r) else "")
        lines.append(f"  [{rate_basis_s}], [{r['capacity_gib']}], "
                      f"[{r['scheme']}], [{lt_s}], [{eff_s}],")
    lines.append(")")

    if burst_rows:
        span_val = burst_rows[0].get("trace_span_ms")
        try:
            span_str = f"{float(span_val):.3f}"
        except (TypeError, ValueError):
            span_str = "an unmeasured number of"
        lines.append("")
        lines.append(
            f"* rate extrapolated from a burst of {span_str} ms, not a "
            f"sustained rate; do not read the required endurance as a "
            f"sustained requirement.")

    Path(path).write_text("\n".join(lines) + "\n")


def print_summary(trace_name, parsed, rows, deep_dive_check=None):
    print(f"\n=== {trace_name} ===")
    print(f"(lifetimes below use a {DAYS_PER_YEAR}-day year: "
          f"SECONDS_PER_YEAR = {SECONDS_PER_YEAR:,})")
    print(f"records read: {parsed['records_read']:,}, "
          f"writes in {parsed['rate_basis']}: {parsed['writes_in_window']:,}, "
          f"distinct written lines: {parsed['distinct_lines']:,}, "
          f"max writes to one line: "
          f"{max(parsed['line_counts'].values()) if parsed['line_counts'] else 0}")
    if parsed["rate_basis"] == "burst":
        print(f"*** BURST RATE, NOT SUSTAINED: the {parsed['window_seconds']*1000:.1f} ms "
              f"window was never reached (trace span "
              f"{parsed['span_seconds']*1000:.3f} ms); rate is extrapolated "
              f"from the burst, not a steady-state measurement. ***")
    print(f"offered rate ({parsed['rate_basis']} basis): "
          f"{parsed['offered_rate']/1e6:.3f} M writes/s")
    if deep_dive_check:
        print(f"deep-dive 4.5 cross-check: {deep_dive_check}")

    e1e6 = [r for r in rows if r["endurance"] == 1e6 and r["write_reduction"] == 1.0
            and r["region_mib"] == ""]
    for rate_basis in sorted(set(r["rate_basis"] for r in e1e6)):
        print(f"\nE=1e6, rate_basis={rate_basis}, write_reduction=1x:")
        print(f"{'capacity_gib':>12} {'scheme':>24} {'lifetime_yr':>14} "
              f"{'upper_yr':>12} {'eff_vs_ideal':>13} {'1st-rot-death':>13} "
              f"{'rotations_k':>14}")
        for r in e1e6:
            if r["rate_basis"] != rate_basis:
                continue
            lt = r["lifetime_years"]
            lt_s = "inf" if lt == float("inf") else f"{lt:.4g}"
            up = r["lifetime_upper_years"]
            up_s = "inf" if up == float("inf") else f"{up:.4g}"
            eff = r["efficiency_vs_ideal"]
            eff_s = "-" if eff is None else f"{eff:.4g}"
            print(f"{r['capacity_gib']:>12} {r['scheme']:>24} {lt_s:>14} "
                  f"{up_s:>12} {eff_s:>13} {str(r['first_rotation_death']):>13} "
                  f"{str(r['rotations_k']):>14}")


# --- CLI ---------------------------------------------------------------------

def build_argparser():
    p = argparse.ArgumentParser(
        description="Endurance sensitivity projected from the measured "
                     "write distribution (see module docstring: this "
                     "PROJECTS, it does not measure, wear-leveling efficiency).")
    p.add_argument("--trace", required=True, help="path to a .nvt trace")
    p.add_argument("--stats", default=None,
                    help="optional NVMain stats file for the admitted rate")
    p.add_argument("--window-ns", type=int, default=DEFAULT_WINDOW_NS)
    p.add_argument("--cpufreq-mhz", type=int, default=DEFAULT_CPUFREQ_MHZ)
    p.add_argument("--psi", type=int, default=DEFAULT_PSI,
                    help="writes per Start-Gap move (default 100)")
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--region-mib", type=float, default=None,
                    help="Start-Gap region size in MiB (default: one "
                         "whole-module region, matching NVMain's default)")
    p.add_argument("--out-dir", default="results")
    p.add_argument("--progress-every", type=int, default=DEFAULT_PROGRESS_EVERY)
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--deep-dive-check", default=None,
                    help="free-text label for the cross-check line printed "
                         "to stdout (informational only)")
    return p


def main(argv=None):
    args = build_argparser().parse_args(argv)

    parsed = parse_trace_window(args.trace, window_ns=args.window_ns,
                                  cpufreq_mhz=args.cpufreq_mhz,
                                  progress_every=args.progress_every,
                                  quiet=args.quiet)

    rate_by_basis = {"offered": parsed["offered_rate"]}
    # FIX ROUND 2 (important #1): thread the burst/window classification
    # into evaluate_all's rows (rate_is_burst, trace_span_ms), not just the
    # stdout banner in print_summary -- round 1 hardcoded rate_by_basis
    # keyed by name only, with no way for evaluate_all to know an "offered"
    # rate was actually extrapolated from a burst.
    rate_burst_info = {
        "offered": (parsed["rate_basis"] == "burst", parsed["span_seconds"] * 1000),
    }
    if args.stats:
        admitted = read_admitted_stats(args.stats)
        rate_by_basis["admitted"] = admitted["admitted_rate"]
        # T5.3 analysis run: a burst trace's admitted rate is still derived
        # from the burst (its few writes spread over the simulator's elapsed
        # time), so the admitted rows carry the same burst flag.
        rate_burst_info["admitted"] = (parsed["rate_basis"] == "burst", None)
        print(f"admitted: {admitted['admitted_writes']:,} writes over "
              f"{admitted['elapsed_s']:.6f} s = "
              f"{admitted['admitted_rate']/1e6:.3f} M writes/s "
              f"(CPUFreq {admitted['cpufreq_mhz']} MHz)")

    trace_name = Path(args.trace).stem
    rows = evaluate_all(parsed["line_counts"], rate_by_basis, psi=args.psi,
                          seed=args.seed, region_mib=args.region_mib,
                          trace_name=trace_name, rate_burst_info=rate_burst_info)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "endurance_table.csv"
    typ_path = out_dir / "endurance_table.typ"

    n_kept, n_new = upsert_csv(rows, csv_path)

    write_typst_table(rows, typ_path, region_mib=args.region_mib)

    print_summary(trace_name, parsed, rows, deep_dive_check=args.deep_dive_check)
    print(f"\nwrote {n_new} rows to {csv_path} ({n_kept} pre-existing rows "
          f"kept, duplicates of this run's keys replaced), typst snippet to "
          f"{typ_path}")


if __name__ == "__main__":
    main()
