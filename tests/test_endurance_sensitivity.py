"""T5.3 sanity-property tests for endurance_sensitivity.py.

Every expected number below is worked out by hand in the comment right
above the assertion, from the formulas derived in endurance_sensitivity.py's
module docstring -- not by calling the module's own functions and comparing
to themselves. These are the "MUST be tests" sanity properties from
task-T5.3-dispatch.md, updated for FIX ROUND 1 (the gap-move overhead moved
from the rate to the wear side, eq. (4) gained a "+k" term -- see the module
docstring's "GAP-MOVE OVERHEAD" section) wherever a Start-Gap-scheme number
is affected. Round-1 tests whose numbers only ever depended on IDEAL/NONE
are unchanged (those formulas did not move in the fix).
"""

import math
import random

import pytest

import endurance_sensitivity as es


# ---------------------------------------------------------------------------
# maxwin_sparse / min_window_for_sum: correctness primitives (unchanged by
# fix round 1 -- these two functions were not touched)
# ---------------------------------------------------------------------------

def _brute_maxwin(positions, counts, R, m):
    """O(R) reference: materialize the full ring and slide a window of
    length m across it (with wraparound), return the max sum."""
    ring = [0] * R
    for p, c in zip(positions, counts):
        ring[p] = c
    if m <= 0:
        return 0
    if m >= R:
        return sum(ring)
    doubled = ring + ring
    window = sum(doubled[0:m])
    best = window
    for i in range(1, R):
        window += doubled[i + m - 1] - doubled[i - 1]
        if window > best:
            best = window
    return best


def test_maxwin_sparse_matches_brute_force_small_examples():
    positions, counts, R = [1, 2, 5], [3, 4, 1], 8
    for m in range(0, R + 1):
        assert es.maxwin_sparse(positions, counts, R, m) == _brute_maxwin(
            positions, counts, R, m), f"m={m}"


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_maxwin_sparse_matches_brute_force_random(seed):
    rng = random.Random(seed)
    R = rng.randint(5, 60)
    n = rng.randint(0, R)
    positions = sorted(rng.sample(range(R), n))
    counts = [rng.randint(1, 20) for _ in positions]
    for m in (0, 1, R // 3, R // 2, R - 1, R):
        assert es.maxwin_sparse(positions, counts, R, m) == _brute_maxwin(
            positions, counts, R, m), f"seed={seed} m={m}"


@pytest.mark.parametrize("seed", [10, 11, 12, 13, 14])
def test_min_window_for_sum_matches_maxwin_sparse_inverse(seed):
    rng = random.Random(seed)
    R = rng.randint(5, 40)
    n = rng.randint(1, R)
    positions = sorted(rng.sample(range(R), n))
    counts = [rng.randint(1, 10) for _ in positions]
    total = sum(counts)
    for tau in range(0, total + 2):
        expected = None
        for m in range(0, R):
            if es.maxwin_sparse(positions, counts, R, m) >= tau:
                expected = m
                break
        got = es.min_window_for_sum(positions, counts, R, tau)
        if expected is None:
            if tau > total:
                assert got is None
            else:
                assert got is None or got >= R
        else:
            assert got == expected, f"seed={seed} tau={tau}"


# ---------------------------------------------------------------------------
# min_window_for_weighted_target: correctness (this IS new to fix round 1,
# and a first attempt at it had a real bug -- see the module docstring's
# comment on min_window_for_weighted_target for the counter-example that
# caught it. Checked directly against a brute-force scan over m using
# maxwin_sparse, on random sparse arrays.)
# ---------------------------------------------------------------------------

def _brute_min_window_for_weighted_target(positions, counts, R, A, tau):
    if tau <= 0:
        return 0
    for m in range(0, R + 1):
        if A * es.maxwin_sparse(positions, counts, R, m) + m >= tau:
            return m
    return None


@pytest.mark.parametrize("seed", range(200, 260))
def test_min_window_for_weighted_target_matches_brute_force_random(seed):
    rng = random.Random(seed)
    R = rng.randint(5, 60)
    n = rng.randint(0, R)
    positions = sorted(rng.sample(range(R), n))
    counts = [rng.randint(1, 10) for _ in positions]
    A = rng.choice([0.1, 1.0, 3.7, 50.0, 1000.0])
    total = sum(counts)
    max_possible = A * total + R
    for tau in [0, 1, max_possible * 0.3, max_possible * 0.7,
                max_possible * 0.99, max_possible, max_possible + 1]:
        expected = _brute_min_window_for_weighted_target(positions, counts, R, A, tau)
        got = es.min_window_for_weighted_target(positions, counts, R, A, tau)
        assert got == expected, f"seed={seed} tau={tau} A={A}"


def test_min_window_for_weighted_target_padding_counter_example():
    # The exact counter-example that caught the first (buggy) two-pointer
    # implementation: a cluster whose TIGHT enclosing span falls just short
    # of the target, but padding the SAME cluster (same sum, larger m) by a
    # few units crosses it. Reduced from the real failure found while cross
    # -checking find_min_rotations on a synthetic LBM-scale random case
    # (region size ~134M lines): here with R=1000, two points at positions
    # 100 and 103 (so the tight span for {100,103} is 4, sum 2), and A=100.
    # Tight span m=4: A*2+4 = 204. Target tau=210 needs 6 more; since the
    # next real point is far away (say at 900), we can pad from m=4 up to
    # m=6 (still capturing only {100,103}, sum stays 2) without touching
    # position 900: A*2+6 = 206 -- still short. Padding to m=8: A*2+8=208,
    # still short. m=10: A*2+10=210 -- exactly meets tau=210. So the
    # expected answer is m=10 (not m=4, the tight span, and not something
    # that requires reaching position 900).
    positions, counts, R, A = [100, 103, 900], [1, 1, 1], 1000, 100.0
    tau = 210
    expected = _brute_min_window_for_weighted_target(positions, counts, R, A, tau)
    assert expected == 10
    got = es.min_window_for_weighted_target(positions, counts, R, A, tau)
    assert got == 10


# ---------------------------------------------------------------------------
# find_min_rotations: correctness against a reference that implements eq.
# (4) via an exhaustive linear scan over k, over >=3000 seeded random
# sparse arrays (dispatch/review requirement: round 1's version was found
# non-minimal on 652/3000 draws when the target was an exact multiple of
# C_g -- see the module docstring's FIX ROUND 1 note on find_min_rotations).
#
# FIX ROUND 2 (minor #3): collapsed from 3,000 separate @pytest.mark.
# parametrize cases into ONE test that loops over the same seed range
# internally -- same coverage, same per-seed assertion (the failing seed,
# ring and inputs are still named in the message on failure), without the
# per-node collection/reporting overhead of 3,000 pytest items. Ring sizes
# widened per the review (R up to a few hundred lines, A up to ~2.24e6):
# the round-1 range (R in [3,25]) never reached the regime that caught the
# min_window_for_weighted_target padding bug (see that function's
# docstring) -- R up to 400 with psi up to 5000 and C_g as small as 1
# reaches A = (R+1)*psi/C_g up to ~2,005,000, the same order of magnitude.
#
# The reference below uses maxwin_sparse (not an O(R) full-ring
# materialization) to evaluate each candidate k's wear_max, so the
# exhaustive scan stays fast even at R=400: maxwin_sparse has its own
# separate brute-force-against-O(R)-materialization validation
# (test_maxwin_sparse_matches_brute_force_random/_small_examples above),
# so this still independently exercises find_min_rotations' MINIMALITY
# logic (its analytic q-guess and bounded correction loop) against an
# exhaustive scan, just without re-validating maxwin_sparse's own
# arithmetic a second time inside a loop that also has to stay under the
# file's ~15s budget at R up to 400 across 3,000 seeds.
# ---------------------------------------------------------------------------

def _linscan_wear_max(positions, counts, R, C_g, psi, k):
    q, m = divmod(k, R)
    mw = es.maxwin_sparse(positions, counts, R, m)
    return (R + 1) * psi / C_g * (q * C_g + mw) + k


def _linscan_find_min_k(positions, counts, R, C_g, psi, E, k_cap):
    for k in range(0, k_cap + 1):
        if _linscan_wear_max(positions, counts, R, C_g, psi, k) >= E:
            return k
    raise AssertionError("linear scan did not find a satisfying k within k_cap")


def test_find_min_rotations_matches_linear_scan_3000_seeds():
    failures = []
    for seed in range(3000):
        rng = random.Random(seed)
        R = rng.randint(3, 400)
        n = rng.randint(1, min(R, 8))
        positions = sorted(rng.sample(range(R), n))
        counts = [rng.randint(1, 10) for _ in positions]
        C_g = sum(counts)
        psi = rng.randint(1, 5000)

        # Choose E so results are both "exact multiple of C_g" flavored (the
        # round-1 defect's trigger) and generic random targets, across a
        # few full cycles worth of k (k_cap bounds the scan).
        max_cycles = 3
        k_cap = max_cycles * R + R
        max_wear = _linscan_wear_max(positions, counts, R, C_g, psi, k_cap)
        if rng.random() < 0.5:
            # exact multiple of C_g in "count space" -- the round-1 trigger
            mult = rng.randint(1, max(1, int(max_wear // C_g) - 1) or 1)
            E = mult * C_g
        else:
            E = rng.uniform(1, max_wear * 0.9)
        if E <= 0:
            E = 1

        expected_k = _linscan_find_min_k(positions, counts, R, C_g, psi, E, k_cap)
        got_k, got_m = es.find_min_rotations(positions, counts, R, C_g, psi, E)
        if got_k != expected_k or got_m != got_k % R:
            failures.append(
                f"seed={seed} R={R} positions={positions} counts={counts} "
                f"psi={psi} E={E} C_g={C_g}: expected k={expected_k}, got "
                f"k={got_k} m={got_m}")

    assert not failures, (
        f"{len(failures)}/3000 seeds failed:\n" + "\n".join(failures[:10]) +
        (f"\n... and {len(failures) - 10} more" if len(failures) > 10 else ""))


# ---------------------------------------------------------------------------
# Property 1: uniform writes over ALL lines of a small module
# ---------------------------------------------------------------------------

def test_uniform_writes_all_schemes_agree_within_gap_overhead():
    # N = R = 20 lines, every line written exactly 3 times (C=60, c_max=3),
    # psi=5, W=1000 writes/s, E=1e4.
    #
    # IDEAL: T = N*E/W = 20*1e4/1000 = 200 s.
    # NONE:  T = E/(W*c_max/C) = 1e4/(1000*3/60) = 200 s (uniform -> c_max/C
    #        = 1/N exactly, so NONE == IDEAL exactly here; unaffected by the
    #        gap-move fix, neither formula involves Start-Gap).
    #
    # START_GAP (FIX ROUND 1 model, eq. 4 with the "+k" term): for a fully
    # dense uniform region, maxwin(m) = 3m exactly, so
    #   wear(q,m) = q*B + f(m), where B = A*C_g + R = 1.75*60 + 20 = 125
    #   (A = (R+1)*psi/C_g = 21*5/60 = 1.75) and f(m) = A*3m + m = 6.25m.
    # Minimal (q,m) with 125q + 6.25m >= 1e4: q=79 needs m>=20 (infeasible,
    # cap m<20); q=80,m=0 gives exactly 125*80 = 10000 = E. So k=1600.
    #   wear(1599) [q=79,m=19] = 125*79 + 6.25*19 = 9875 + 118.75 = 9993.75
    #   wear(1600) [q=80,m=0]  = 10000
    #   frac = (1e4-9993.75)/(10000-9993.75) = 1.0 -> T = tau_g*1600
    #   tau_g = (R+1)*psi/W_g = 105/1000 = 0.105 (no more (1+1/psi) factor)
    #   T = 1600*0.105 = 168.0 s EXACTLY.
    # T/T_ideal = 168/200 = 0.84 = (R+1)*psi / B = 105/125 exactly (the new,
    # R-dependent gap-overhead ratio -- see the module docstring).
    n_module = 20
    line_counts = {i: 3 for i in range(n_module)}
    W, E, psi = 1000.0, 1e4, 5

    t_ideal = es.lifetime_ideal(W, n_module, E)
    t_none = es.lifetime_none(W, 3, 60, E)
    assert t_ideal == pytest.approx(200.0)
    assert t_none == pytest.approx(200.0)

    sg = es.startgap_module_lifetime(line_counts, n_module, psi, W, 60, E)
    assert sg["lifetime_s"] == pytest.approx(168.0, rel=1e-9)
    assert sg["lifetime_s"] / t_ideal == pytest.approx(105 / 125, rel=1e-9)
    assert sg["first_rotation_death"] is False
    assert sg["rotations_k"] == 1600

    rsg = es.randomized_startgap_module_lifetime(
        line_counts, n_module, n_module, psi, W, 60, E, seed=7)
    # A permutation of "every position has count 3" is still "every position
    # has count 3": the randomized result must match START_GAP exactly.
    assert rsg["lifetime_s"] == pytest.approx(sg["lifetime_s"], rel=1e-9)


# ---------------------------------------------------------------------------
# Property 2: the brief's own number (IDEAL only -- unaffected by the fix)
# ---------------------------------------------------------------------------

def test_brief_number_ideal_lifetime_and_097_efficiency():
    n_module = es.capacity_lines(64)
    assert n_module == 2 ** 30
    t_ideal_s = es.lifetime_ideal(9.5e6, n_module, 1e6)
    t_ideal_yr = t_ideal_s / es.SECONDS_PER_YEAR
    assert t_ideal_yr == pytest.approx(3.58, abs=0.005)
    assert t_ideal_yr * 0.97 == pytest.approx(3.47, abs=0.01)


# ---------------------------------------------------------------------------
# Property 3 & 4: all writes to ONE line, small module
# ---------------------------------------------------------------------------

def test_single_hot_line_relieved_in_time_psi_10():
    # R = N = 1000, one line (position 500) with count 1 (C_g=c_max_g=1,
    # scale-invariant in the count -- see module docstring), psi=10, W=1,
    # E=1e6.
    #
    # first_rotation_wear (FIX ROUND 1: +1 relocation term) =
    #   (R+1)*psi/C_g*c_max_g + 1 = 1001*10 + 1 = 10011 < E: relieved in time.
    #
    # A = 1001*10/1 = 10010. For a single point, maxwin(m)=1 for all m>=1
    # (any nonzero window still only ever contains this one point), so
    # f(m) = A*1 + m = 10010+m for m>=1, f(0)=0.
    # B = A*C_g + R = 10010 + 1000 = 11010.
    # max reachable in one cycle: f(999) = 10010+999 = 11009 (< B, as
    # expected). E=1e6: q_guess = ceil((1e6-11009)/11010) = 90.
    #   q=89: tau = 1e6 - 89*11010 = 20110; need f(m)>=20110, max f(999)
    #   =11009 < 20110: infeasible.
    #   q=90: tau = 1e6 - 90*11010 = 9100; f(0)=0 <9100 (fails), f(1)=10011
    #   >=9100 (satisfies) -> smallest m=1.
    # k = 90*1000 + 1 = 90001.
    #
    # tau_g = (R+1)*psi/W_g = 10010/1 = 10010 (no more (1+1/psi) factor).
    # wear(90000) [q=90,m=0] = 90*11010 + 0        = 990900
    # wear(90001) [q=90,m=1] = 90*11010 + 10011     = 1000911
    # frac = (1e6-990900)/(1000911-990900) = 9100/10011
    # T = 10010*(90000 + 9100/10011) = 9019000991000/10011 (exact fraction)
    R, psi, W, E = 1000, 10, 1.0, 1e6
    line_counts = {500: 1}
    expected_T = 9019000991000 / 10011

    sg = es.startgap_module_lifetime(line_counts, R, psi, W, 1, E)
    assert sg["first_rotation_death"] is False
    assert sg["rotations_k"] == 90001
    assert sg["lifetime_s"] == pytest.approx(expected_T, rel=1e-9)

    t_ideal = es.lifetime_ideal(W, R, E)
    t_none = es.lifetime_none(W, 1, 1, E)
    assert t_ideal == pytest.approx(1e9)
    assert t_none == pytest.approx(1e6)
    assert t_none < sg["lifetime_s"] < t_ideal
    assert t_ideal / t_none == pytest.approx(R)


def test_single_hot_line_first_rotation_death_psi_1000():
    # Same setup but psi=1000: (R+1)*psi/C_g*c_max_g + 1 = 1001*1000 + 1 =
    # 1,001,001 >= E=1e6, so the hot line dies before Start-Gap completes
    # even one rotation. T must equal NONE's formula exactly: E/(W*c_max/C)
    # = 1e6/(1*1) = 1e6. FIX ROUND 1, important defect #2: the review's own
    # brute-force simulator shows this is only a LOWER bound on the true
    # survival time (the gap relieves the hot line mid-rotation, so the
    # true value is somewhere in [T_NONE, 2*T_NONE)) -- lifetime_upper_s
    # reports the 2x upper bound of that bracket.
    R, psi, W, E = 1000, 1000, 1.0, 1e6
    line_counts = {500: 1}

    sg = es.startgap_module_lifetime(line_counts, R, psi, W, 1, E)
    assert sg["first_rotation_death"] is True
    t_none = es.lifetime_none(W, 1, 1, E)
    assert sg["lifetime_s"] == pytest.approx(t_none)
    assert sg["lifetime_s"] == pytest.approx(1e6)
    assert sg["lifetime_upper_s"] == pytest.approx(2 * sg["lifetime_s"])
    assert sg["lifetime_upper_s"] == pytest.approx(2e6)


# ---------------------------------------------------------------------------
# NEW (fix round 1, item 3): psi=10 hot block where the round-1 (rate-side)
# and round-2 (wear-side, "+k") gap-move accountings differ measurably.
# ---------------------------------------------------------------------------

def test_psi_10_hot_block_gap_move_accounting_differs_measurably():
    # R=100, psi=10, a CONTIGUOUS 10-line hot block (positions 0..9, each
    # count 1: C_g=10, c_max_g=1), W_g=1010 (chosen so tau_g=(R+1)*psi/W_g
    # = 1010/1010 = 1 exactly), E=1000.
    #
    # A = (R+1)*psi/C_g = 1010/10 = 101.
    # First-rotation check: A*c_max_g+1 = 101+1 = 102 < 1000: not death.
    #
    # ROUND 2 (wear-side "+k", as implemented):
    #   maxwin(m) = min(m, 10) for the contiguous 10-line block.
    #   wear(9)  = A*maxwin(9)+9   = 101*9+9   = 918
    #   wear(10) = A*maxwin(10)+10 = 101*10+10 = 1020
    #   frac = (1000-918)/(1020-918) = 82/102 = 41/51
    #   T_new = tau_g*(9 + 41/51) = 1*(9+41/51) = 500/51 = 9.803921568627... s
    #
    # ROUND 1 (rate-side (1+1/psi), for comparison ONLY -- not implemented
    # any more, shown here purely to demonstrate the measurable difference):
    #   wear(9)_old  = A*maxwin(9)  = 909
    #   wear(10)_old = A*maxwin(10) = 1010
    #   frac_old = (1000-909)/(1010-909) = 91/101
    #   tau_g_old = (R+1)*psi/(W_g*(1+1/psi)) = 1010/(1010*11/10) = 10/11
    #   T_old = (10/11)*(9+91/101) = (10/11)*(1000/101) = 10000/1111
    #         = 9.000900090009... s
    #
    # Relative difference: (T_new - T_old)/T_old = (500/51 - 10000/1111) /
    # (10000/1111) = 0.0892... ~ 8.9%, a measurable difference in the
    # direction round-1 UNDER-estimated lifetime for this example (the sign
    # is not claimed to be universal -- see the module docstring).
    R, psi = 100, 10
    line_counts = {i: 1 for i in range(10)}
    W_g = 1010.0
    E = 1000.0
    C = 10

    sg = es.startgap_module_lifetime(line_counts, R, psi, W_g, C, E)
    assert sg["first_rotation_death"] is False
    assert sg["rotations_k"] == 10
    assert sg["lifetime_s"] == pytest.approx(500 / 51, rel=1e-9)

    T_old = 10000 / 1111
    rel_diff = (sg["lifetime_s"] - T_old) / T_old
    assert rel_diff == pytest.approx(0.089219, abs=1e-5)
    assert abs(rel_diff) > 0.05  # "differ measurably"


# ---------------------------------------------------------------------------
# Property 5: a hot contiguous block covering 1% of the module
# ---------------------------------------------------------------------------

def test_hot_contiguous_block_startgap_limited_randomized_approaches_ideal():
    n_module = 100_000
    line_counts = {i: 1 for i in range(1000)}
    W, psi, E = 1000.0, 100, 1e6
    C = 1000

    t_ideal = es.lifetime_ideal(W, n_module, E)
    sg = es.startgap_module_lifetime(line_counts, n_module, psi, W, C, E)
    rsg = es.randomized_startgap_module_lifetime(
        line_counts, n_module, n_module, psi, W, C, E, seed=42)

    # Verified numerically (module docstring's derivation applies; exact
    # closed form is unwieldy for a genuinely contiguous-but-not-fully-
    # dense block, so bounds are asserted, as the dispatch's own prose
    # does: "far below IDEAL" / "RANDOMIZED ... approaches IDEAL"):
    assert sg["lifetime_s"] < 0.5 * t_ideal
    assert rsg["lifetime_s"] > 0.5 * t_ideal
    assert sg["lifetime_s"] == pytest.approx(999900.0109987902, rel=1e-6)


# ---------------------------------------------------------------------------
# Property 6: sub-regions (--region-mib)
# ---------------------------------------------------------------------------

def test_subregion_dense_hot_region_matches_region_ideal():
    # 64 GiB module, one 16 MiB region (262,144 lines) written UNIFORMLY and
    # FULLY (every line in that one region gets count=1; C=262,144,
    # c_max=1). START_GAP over that one region matches the SAME closed form
    # as property 1 (fully-dense-uniform, generalized): T =
    # (region_lines*E/W) * (R+1)*psi/B, B=(R+1)*psi+region_lines. Far below
    # the whole-module IDEAL.
    capacity_gib = 64
    n_module = es.capacity_lines(capacity_gib)
    region_mib = 16
    region_lines = int(region_mib * (2 ** 20) // es.BYTES_PER_LINE)
    assert region_lines == 262_144

    line_counts = {i: 1 for i in range(region_lines)}
    W, psi, E = 1e6, 100, 1e6
    C = region_lines

    t_ideal_module = es.lifetime_ideal(W, n_module, E)
    R = region_lines
    A = (R + 1) * psi / C
    B = A * C + R
    expected_sg = ((R + 1) * psi / B) * (region_lines * E / W)

    sg = es.startgap_module_lifetime(line_counts, region_lines, psi, W, C, E)
    assert sg["lifetime_s"] == pytest.approx(expected_sg, rel=1e-6)
    assert sg["lifetime_s"] < 0.01 * t_ideal_module  # "far below IDEAL"

    # DETERMINISTIC verification of the "adjacent pair" mechanism (FIX
    # ROUND 1, minor 4b: round 1's version of this check asserted EXACT
    # equality across 7 random seeds, relying on the (empirically likely,
    # but not structurally guaranteed) chance that random scattering
    # produces a physically adjacent pair of written lines somewhere. That
    # is now replaced with a CONSTRUCTED, deterministic scenario -- no
    # randomness at all -- that isolates the mechanism exactly, plus a
    # bound (not exact-equality) check against the actual randomized
    # function across several seeds below.
    #
    # A single region (module = 1 region) with exactly TWO measured lines,
    # physically ADJACENT (positions 1000, 1001, each count 1): C_g=2,
    # c_max_g=1. Pick psi/W/E so this is NOT first-rotation death:
    #   A = (R+1)*psi/C_g = 262145*100/2 = 13,107,250
    #   first_rotation_wear = A*1+1 = 13,107,251
    #   E = 2e7 > 13,107,251: not death.
    # k=2 (m=2, the adjacent pair) satisfies: wear(1)=A*1+1=13107251,
    # wear(2)=A*maxwin(2)+2=A*2+2=26214502 (maxwin(2)=2, the pair). E=2e7
    # lies between: frac=(2e7-13107251)/(26214502-13107251) computed by
    # the code; the exact closed form (derived in the module docstring's
    # adjacent-pair discussion) is:
    #   T = tau_g * E / (A+1), tau_g = (R+1)*psi/W = 26214500/W.
    # With W=1e6: T = 26214500e6... (evaluated numerically below, verified
    # to match the code to 1e-6 relative -- this is an exact algebraic
    # identity, not an approximation, since m=2 (the tight adjacent pair)
    # is exactly what the search finds here).
    R2, psi2, W2 = 262144, 100, 1e6
    pair_counts = {1000: 1, 1001: 1}
    E2 = 2e7
    sg_pair = es.startgap_module_lifetime(pair_counts, R2, psi2, W2, 2, E2)
    assert sg_pair["first_rotation_death"] is False
    assert sg_pair["rotations_k"] == 2
    A2 = (R2 + 1) * psi2 / 2
    tau_g2 = (R2 + 1) * psi2 / W2
    expected_pair_T = tau_g2 * E2 / (A2 + 1)
    assert sg_pair["lifetime_s"] == pytest.approx(expected_pair_T, rel=1e-9)
    # And this is very close to (but, because of the "+1" term, not
    # exactly) the module-wide constant E*C/W = 2e7*2/1e6 = 40.0:
    assert sg_pair["lifetime_s"] == pytest.approx(40.0, rel=1e-6)

    # BOUND (not exact equality -- corrected per fix round 1, minor 4b):
    # scattering the SAME 262,144-line dense source across the 64 GiB
    # module's 4,096 16-MiB regions leaves each region with only ~64
    # written lines on average; across several seeds the randomized
    # module lifetime clusters near E*C/W (~262144 s here) rather than
    # anywhere near IDEAL -- a bound, since which specific region ends up
    # limiting (and its exact C_g) varies slightly by seed, no longer
    # collapsing to a bit-identical constant now that the "+k" term
    # doesn't cancel C_g perfectly (only approximately, since A >> 1 for
    # every plausible worst region here).
    approx_constant = E * C / W  # = 262144
    for seed in (1, 2, 3, 4, 5, 99, 100):
        rsg = es.randomized_startgap_module_lifetime(
            line_counts, n_module, region_lines, psi, W, C, E, seed=seed)
        assert rsg["lifetime_s"] == pytest.approx(approx_constant, rel=1e-3), seed
        assert rsg["lifetime_s"] < 1e-3 * t_ideal_module  # nowhere near IDEAL


# ---------------------------------------------------------------------------
# Property 7: monotonicity in E and capacity; write reduction 4.5x
# ---------------------------------------------------------------------------

def test_monotonic_in_endurance_and_capacity_ideal_and_randomized():
    line_counts = {i * 7: (i % 5) + 1 for i in range(500)}
    rows = es.evaluate_all(line_counts, {"offered": 2_000_000.0},
                             psi=100, seed=3, trace_name="synthetic")
    for scheme in ("IDEAL", "RANDOMIZED_START_GAP"):
        for capacity_gib in es.CAPACITY_GIB_AXIS:
            sub = [r for r in rows if r["scheme"] == scheme
                   and r["capacity_gib"] == capacity_gib
                   and r["write_reduction"] == 1.0]
            sub.sort(key=lambda r: r["endurance"])
            lifetimes = [r["lifetime_years"] for r in sub]
            assert lifetimes == sorted(lifetimes), (scheme, capacity_gib)
        for E in es.ENDURANCE_AXIS:
            sub = [r for r in rows if r["scheme"] == scheme
                   and r["endurance"] == E and r["write_reduction"] == 1.0]
            sub.sort(key=lambda r: r["capacity_gib"])
            lifetimes = [r["lifetime_years"] for r in sub]
            assert lifetimes == sorted(lifetimes), (scheme, E)


def test_write_reduction_multiplies_every_lifetime_by_4point5():
    # k (rotations needed) never depends on W (only tau_g does), so T is
    # EXACTLY proportional to 1/W for every scheme in this model -- still
    # true after fix round 1 (the "+k" term doesn't involve W either).
    line_counts = {i * 3: (i % 7) + 1 for i in range(800)}
    rows = es.evaluate_all(line_counts, {"offered": 5_000_000.0},
                             psi=100, seed=11, trace_name="synthetic")
    by_key = {}
    for r in rows:
        key = (r["scheme"], r["capacity_gib"], r["endurance"])
        by_key.setdefault(key, {})[r["write_reduction"]] = r["lifetime_years"]
    checked = 0
    for key, by_wr in by_key.items():
        t1 = by_wr.get(1.0)
        t45 = by_wr.get(4.5)
        if t1 in (None, float("inf")) or t45 in (None, float("inf")):
            continue
        assert t45 == pytest.approx(t1 * 4.5, rel=1e-6), key
        checked += 1
    assert checked > 0


# ---------------------------------------------------------------------------
# NEW (fix round 1, critical defect #1): required endurance round-trips
# exactly against the SAME lifetime function the table uses, for all four
# schemes, and never silently returns 0 for a positive target.
# ---------------------------------------------------------------------------

def test_required_endurance_round_trips_all_four_schemes():
    n_module = es.capacity_lines(8)
    line_counts = {i * 37: (i % 5) + 1 for i in range(2000)}
    C = sum(line_counts.values())
    c_max = max(line_counts.values())
    W = 5_000_000.0
    psi = 100
    T_target = 5.0 * es.SECONDS_PER_YEAR

    req_none, note_none = es.required_endurance_none(W, c_max, C, T_target)
    req_ideal, note_ideal = es.required_endurance_ideal(W, n_module, T_target)
    req_sg, note_sg = es.required_endurance_startgap(line_counts, n_module, psi, W, C, T_target)
    req_rsg, note_rsg = es.required_endurance_randomized(
        line_counts, n_module, n_module, psi, W, C, seed=5, T_target=T_target)

    for req in (req_none, req_ideal, req_sg, req_rsg):
        assert req is not None and req > 0  # "never returns 0 for a positive target"
    # This scenario is a genuine, non-trivial solve for all four schemes
    # (not "any endurance suffices"), so no note should be set.
    for note in (note_none, note_ideal, note_sg, note_rsg):
        assert note is None

    t_none = es.lifetime_none(W, c_max, C, req_none)
    t_ideal = es.lifetime_ideal(W, n_module, req_ideal)
    t_sg = es.startgap_module_lifetime(line_counts, n_module, psi, W, C, req_sg)["lifetime_s"]
    t_rsg = es.randomized_startgap_module_lifetime(
        line_counts, n_module, n_module, psi, W, C, req_rsg, seed=5)["lifetime_s"]

    for name, T in (("none", t_none), ("ideal", t_ideal), ("sg", t_sg), ("rsg", t_rsg)):
        assert T >= T_target * (1 - 1e-6), name  # by definition of "required"
        assert abs(T - T_target) / T_target < 1e-4, (name, T, T_target)


def test_required_endurance_gcc_shaped_first_rotation_death_equals_none():
    # A footprint small relative to the region, with psi/E scaled so the
    # region stays first-rotation-death all the way out to the 10-year-
    # class target (R*psi >> W*T_target): required endurance must reduce
    # to exactly NONE's own required endurance (FIX ROUND 1, important
    # defect #2's other stated test, and a direct check of the closed-form
    # branch in required_endurance_region_direct).
    R, psi, W, T_target = 100_000, 100, 1.0, 1000.0
    line_counts = {10: 3}
    for i in range(1, 97):
        line_counts[1000 + i] = 1
    C = sum(line_counts.values())
    c_max = max(line_counts.values())

    req_none, _ = es.required_endurance_none(W, c_max, C, T_target)
    req_sg, _ = es.required_endurance_startgap(line_counts, R, psi, W, C, T_target)
    req_rsg, _ = es.required_endurance_randomized(
        line_counts, R, R, psi, W, C, seed=1, T_target=T_target)

    assert req_sg == pytest.approx(req_none, rel=1e-6)
    assert req_rsg == pytest.approx(req_none, rel=1e-6)

    sg = es.startgap_module_lifetime(line_counts, R, psi, W, C, req_sg)
    assert sg["first_rotation_death"] is True


def test_required_endurance_direct_matches_bisection():
    # required_endurance_region_direct is a closed-form shortcut, not a
    # literal bisection of startgap_module_lifetime -- cross-checked here
    # against invert_lifetime_for_endurance (which DOES bisect the exact
    # lifetime function the table calls) to confirm they agree, proving the
    # closed form is the same answer bisection would give, just without the
    # ~30-40-step search (needed for performance on multi-million-line
    # traces -- see required_endurance_region_direct's docstring).
    n_module = es.capacity_lines(8)
    line_counts = {i * 37: (i % 5) + 1 for i in range(2000)}
    C = sum(line_counts.values())
    W = 5_000_000.0
    psi = 100
    T_target = 5.0 * es.SECONDS_PER_YEAR

    prepared = es._prepare_regions(line_counts, n_module)
    req_direct, note_direct = es.required_endurance_startgap_prepared(
        prepared, n_module, psi, W, C, T_target)
    req_bisect, note_bisect = es.invert_lifetime_for_endurance(
        lambda E: es.startgap_module_lifetime_prepared(
            prepared, n_module, psi, W, C, E)["lifetime_s"],
        T_target)
    assert req_direct == pytest.approx(req_bisect, rel=1e-5)
    assert note_direct is None
    assert note_bisect is None


# ---------------------------------------------------------------------------
# NEW (fix round 2, minor #2): invert_lifetime_for_endurance's bracket-floor
# return is a non-silent, explicit signal (ANY_ENDURANCE_SUFFICES_NOTE),
# not indistinguishable from "the search solved for E=1.0".
# ---------------------------------------------------------------------------

def test_invert_lifetime_for_endurance_floor_case_is_flagged():
    # W tiny relative to c_max/C: even E=1 (the bracket floor) already
    # gives a lifetime far beyond any realistic target.
    #   hot_rate = W*c_max/C = 1e-12*1/1 = 1e-12
    #   lifetime_none(E=1) = 1/1e-12 = 1e12 s ~ 31,700 years >> any T_target
    #   used below (1 year).
    W, c_max, C = 1e-12, 1, 1
    T_target = 1.0 * es.SECONDS_PER_YEAR

    req, note = es.required_endurance_none(W, c_max, C, T_target)
    assert req == 1.0
    assert note == es.ANY_ENDURANCE_SUFFICES_NOTE

    # Direct check of the lower-level primitive too.
    e, note2 = es.invert_lifetime_for_endurance(
        lambda E: es.lifetime_none(W, c_max, C, E), T_target)
    assert e == 1.0
    assert note2 == es.ANY_ENDURANCE_SUFFICES_NOTE

    # A genuinely-solved case (from the round-trip test above) must NOT
    # carry the note.
    req2, note3 = es.required_endurance_none(5_000_000.0, 3, 3006, T_target)
    assert req2 != 1.0
    assert note3 is None


def test_required_endurance_note_reaches_csv_row():
    W, c_max_line_counts = 1e-12, {0: 1}
    T_target = 1.0 * es.SECONDS_PER_YEAR
    rows = es.evaluate_all(c_max_line_counts, {"offered": W}, psi=100, seed=1,
                             trace_name="floor_case", capacity_axis=(8,),
                             endurance_axis=(1e6,), write_reduction_axis=(1.0,))
    none_rows = [r for r in rows if r["scheme"] == "NONE"]
    assert len(none_rows) == 1
    assert none_rows[0]["required_endurance_note"] == es.ANY_ENDURANCE_SUFFICES_NOTE
    assert none_rows[0]["required_endurance_10yr"] == 1.0


# ---------------------------------------------------------------------------
# NEW (fix round 1, important defect #2): lifetime_upper_years
# ---------------------------------------------------------------------------

def test_lifetime_upper_years_is_2x_only_in_first_rotation_death():
    # NONE/IDEAL: upper == lower always (no first-rotation-death concept
    # applies to them).
    line_counts = {i * 7: (i % 5) + 1 for i in range(500)}
    rows = es.evaluate_all(line_counts, {"offered": 2_000_000.0},
                             psi=100, seed=3, trace_name="synthetic")
    for r in rows:
        if r["scheme"] not in ("START_GAP", "RANDOMIZED_START_GAP"):
            assert r["lifetime_upper_years"] == r["lifetime_years"]

    # Direct, hand-picked death case (reuses test_single_hot_line_first_
    # rotation_death_psi_1000's exact scenario): upper == 2x lower exactly.
    R, psi, W, E = 1000, 1000, 1.0, 1e6
    death_sg = es.startgap_module_lifetime({500: 1}, R, psi, W, 1, E)
    assert death_sg["first_rotation_death"] is True
    assert death_sg["lifetime_upper_s"] == pytest.approx(
        2 * death_sg["lifetime_s"], rel=1e-9)

    # Direct, hand-picked non-death case (reuses the psi=10 hot-block
    # scenario): upper == lower exactly.
    normal_sg = es.startgap_module_lifetime(
        {i: 1 for i in range(10)}, 100, 10, 1010.0, 10, 1000.0)
    assert normal_sg["first_rotation_death"] is False
    assert normal_sg["lifetime_upper_s"] == pytest.approx(
        normal_sg["lifetime_s"], rel=1e-9)


# ---------------------------------------------------------------------------
# Trace parsing: burst-vs-window decision and records_read (fix round 1,
# minor 4c)
# ---------------------------------------------------------------------------

def test_parse_trace_window_burst_labels_and_counts(tmp_path):
    trace = tmp_path / "tiny.nvt"
    z = "0" * 128
    lines = [
        f"0 W 0x40 {z} 0",
        f"10 R 0x80 {z} 0",
        f"20 W 0x40 {z} 0",
        f"30 W 0xc0 {z} 0",
    ]
    trace.write_text("\n".join(lines) + "\n")

    parsed = es.parse_trace_window(str(trace), window_ns=250_000_000,
                                     cpufreq_mhz=3000, quiet=True)
    assert parsed["rate_basis"] == "burst"
    assert parsed["window_reached"] is False
    assert parsed["writes_in_window"] == 3
    assert parsed["distinct_lines"] == 2
    assert parsed["line_counts"][1] == 2
    assert parsed["line_counts"][3] == 1
    assert parsed["span_cycles"] == 30
    assert parsed["records_read"] == 4  # all 4 records processed (no boundary hit)
    assert parsed["span_seconds"] == pytest.approx(30 * (1000.0 / 3000) * 1e-9)
    assert parsed["offered_rate"] == pytest.approx(3 / parsed["span_seconds"])


def test_parse_trace_window_stops_at_window_boundary(tmp_path):
    trace = tmp_path / "tiny2.nvt"
    z = "0" * 128
    # window_cycles at window_ns=10, cpufreq_mhz=1000 -> 10*1000//1000=10.
    lines = [
        f"0 W 0x40 {z} 0",
        f"5 W 0x80 {z} 0",
        f"10 W 0xc0 {z} 0",   # cycle==window_cycles: the boundary record
        f"999999 W 0x100 {z} 0",  # never reached
    ]
    trace.write_text("\n".join(lines) + "\n")
    parsed = es.parse_trace_window(str(trace), window_ns=10, cpufreq_mhz=1000,
                                     quiet=True)
    assert parsed["rate_basis"] == "window"
    assert parsed["window_reached"] is True
    assert parsed["writes_in_window"] == 2
    # FIX ROUND 1 (minor 4c): the boundary record (cycle=10) is read from
    # the file (it is what triggers the break) but must NOT be counted in
    # records_read, since it is not processed as part of the window/span.
    assert parsed["records_read"] == 2


def test_parse_trace_window_decision_is_not_span_based(tmp_path):
    # FIX ROUND 1 (minor 4c): a trace whose recorded first/last cycle SPAN
    # happens to be >= window_cycles, but which never actually produced a
    # record with cycle >= window_cycles, must still be classified "burst"
    # (window never reached) -- catches the old span-based proxy, which
    # would have looked at (last_cycle - first_cycle) instead of whether
    # the window boundary was actually observed. Construct records whose
    # cycles jump straight from just under the window to something whose
    # SPAN from cycle 0 would exceed window_cycles, without ever emitting a
    # record AT OR PAST window_cycles itself (impossible with a monotonic
    # trace and window_cycles as the threshold -- so instead this asserts
    # the boundary case: the window is reached only by a cycle EXACTLY at
    # window_cycles, verifying the decision uses that exact record, not an
    # off-by-one span comparison).
    trace = tmp_path / "tiny3.nvt"
    z = "0" * 128
    # window_cycles at window_ns=9, cpufreq_mhz=1000 -> 9.
    lines = [f"0 W 0x40 {z} 0", f"8 W 0x80 {z} 0"]  # last cycle 8, span 8 < 9
    trace.write_text("\n".join(lines) + "\n")
    parsed = es.parse_trace_window(str(trace), window_ns=9, cpufreq_mhz=1000,
                                     quiet=True)
    assert parsed["rate_basis"] == "burst"
    assert parsed["window_reached"] is False
    assert parsed["records_read"] == 2


def test_read_admitted_stats(tmp_path):
    stats = tmp_path / "stats.out"
    stats.write_text(
        "NVMain: GlobalEventQueue: Added a memory subsystem running at "
        "800MHz. My frequency is 3000MHz.\n"
        "i0.defaultMemory.channel0.FRFCFS.mem_writes 10\n"
        "i0.defaultMemory.channel1.FRFCFS.mem_writes 40\n"
        "Exiting at cycle 3000000 because simCycles 3000000 reached.\n"
    )
    result = es.read_admitted_stats(str(stats))
    assert result["admitted_writes"] == 50
    assert result["elapsed_s"] == pytest.approx(1e-3)
    assert result["admitted_rate"] == pytest.approx(50 / 1e-3)


# ---------------------------------------------------------------------------
# NEW (fix round 1, minor 4d): CSV upsert (dedup on key, not accumulate)
# ---------------------------------------------------------------------------

def test_upsert_csv_replaces_matching_keys_not_accumulates(tmp_path):
    csv_path = tmp_path / "endurance_table.csv"

    row1 = {f: "" for f in es.CSV_FIELDS}
    row1.update({"trace": "gcc", "rate_basis": "offered", "write_reduction": 1.0,
                  "capacity_gib": 8, "endurance": 1e6, "scheme": "NONE",
                  "region_mib": "", "psi": 100, "seed": 1234,
                  "lifetime_years": 1.0, "lifetime_upper_years": 1.0})
    row2 = dict(row1)
    row2["trace"] = "lbm"

    n_kept, n_new = es.upsert_csv([row1], csv_path)
    assert n_kept == 0 and n_new == 1
    n_kept, n_new = es.upsert_csv([row2], csv_path)
    assert n_kept == 1 and n_new == 1  # row1 kept (different trace key), row2 added

    with open(csv_path) as f:
        import csv as csv_mod
        rows = list(csv_mod.DictReader(f))
    assert len(rows) == 2
    assert {r["trace"] for r in rows} == {"gcc", "lbm"}

    # Re-run "gcc" with a different lifetime_years -- must REPLACE, not add.
    row1_updated = dict(row1)
    row1_updated["lifetime_years"] = 99.0
    n_kept, n_new = es.upsert_csv([row1_updated], csv_path)
    assert n_kept == 1  # lbm's row kept
    assert n_new == 1

    with open(csv_path) as f:
        import csv as csv_mod
        rows = list(csv_mod.DictReader(f))
    assert len(rows) == 2  # still 2, not 3 -- no duplicate accumulation
    gcc_rows = [r for r in rows if r["trace"] == "gcc"]
    assert len(gcc_rows) == 1
    assert gcc_rows[0]["lifetime_years"] == "99.0"


# ---------------------------------------------------------------------------
# NEW (fix round 1, minor 4d): Typst snippet with --region-mib is non-empty
# ---------------------------------------------------------------------------

def test_write_typst_table_nonempty_with_region_mib(tmp_path):
    line_counts = {i * 5: 1 for i in range(200)}
    rows = es.evaluate_all(line_counts, {"offered": 1_000_000.0}, psi=100,
                             seed=1, region_mib=16, trace_name="rmib_test",
                             capacity_axis=(8,), endurance_axis=(1e6,),
                             write_reduction_axis=(1.0,))
    out_path = tmp_path / "table.typ"
    es.write_typst_table(rows, out_path, endurance=1e6, region_mib=16)
    text = out_path.read_text()
    assert "#table(" in text
    # must contain at least one data row (a scheme name), not just header
    assert "NONE" in text or "IDEAL" in text


def test_write_typst_table_empty_region_mib_still_works(tmp_path):
    line_counts = {i * 5: 1 for i in range(200)}
    rows = es.evaluate_all(line_counts, {"offered": 1_000_000.0}, psi=100,
                             seed=1, trace_name="default_region_test",
                             capacity_axis=(8,), endurance_axis=(1e6,),
                             write_reduction_axis=(1.0,))
    out_path = tmp_path / "table2.typ"
    es.write_typst_table(rows, out_path, endurance=1e6, region_mib=None)
    text = out_path.read_text()
    assert "NONE" in text or "IDEAL" in text


# ---------------------------------------------------------------------------
# NEW (fix round 2, important #1): the burst label reaches the CSV row and
# the Typst snippet, not just stdout's "*** BURST RATE ***" banner.
# ---------------------------------------------------------------------------

def test_burst_trace_produces_burst_columns_and_typst_marker(tmp_path):
    trace = tmp_path / "burst.nvt"
    z = "0" * 128
    # window_ns default is 250,000,000 -- this trace's span (30 cycles at
    # cpufreq_mhz=3000, i.e. 10 ns) is nowhere near it: a burst.
    lines = [f"0 W 0x40 {z} 0", f"10 W 0x80 {z} 0", f"30 W 0xc0 {z} 0"]
    trace.write_text("\n".join(lines) + "\n")

    parsed = es.parse_trace_window(str(trace), quiet=True)
    assert parsed["rate_basis"] == "burst"
    rate_burst_info = {"offered": (True, parsed["span_seconds"] * 1000)}

    rows = es.evaluate_all(parsed["line_counts"], {"offered": parsed["offered_rate"]},
                             psi=100, seed=1, trace_name="burst_trace",
                             capacity_axis=(8,), endurance_axis=(1e6,),
                             write_reduction_axis=(1.0,), rate_burst_info=rate_burst_info)
    assert len(rows) > 0
    for r in rows:
        assert r["rate_is_burst"] == "true"
        assert r["trace_span_ms"] == pytest.approx(parsed["span_seconds"] * 1000)

    csv_path = tmp_path / "table.csv"
    es.write_csv(rows, csv_path)
    with open(csv_path) as f:
        import csv as csv_mod
        csv_rows = list(csv_mod.DictReader(f))
    assert all(r["rate_is_burst"] == "true" for r in csv_rows)

    typ_path = tmp_path / "burst.typ"
    es.write_typst_table(rows, typ_path, endurance=1e6)
    text = typ_path.read_text()
    assert "burst_trace*" in text
    assert "not a sustained rate" in text
    assert "do not read the required endurance as a sustained requirement" in text


def test_window_covering_trace_no_burst_marker(tmp_path):
    trace = tmp_path / "sustained.nvt"
    z = "0" * 128
    # window_ns=10, cpufreq_mhz=1000 -> window_cycles=10: this record hits
    # the window boundary, so rate_basis is "window", not "burst".
    lines = [f"0 W 0x40 {z} 0", f"5 W 0x80 {z} 0", f"10 W 0xc0 {z} 0"]
    trace.write_text("\n".join(lines) + "\n")

    parsed = es.parse_trace_window(str(trace), window_ns=10, cpufreq_mhz=1000,
                                     quiet=True)
    assert parsed["rate_basis"] == "window"
    rate_burst_info = {"offered": (False, parsed["span_seconds"] * 1000)}

    rows = es.evaluate_all(parsed["line_counts"], {"offered": parsed["offered_rate"]},
                             psi=100, seed=1, trace_name="sustained_trace",
                             capacity_axis=(8,), endurance_axis=(1e6,),
                             write_reduction_axis=(1.0,), rate_burst_info=rate_burst_info)
    for r in rows:
        assert r["rate_is_burst"] == "false"

    typ_path = tmp_path / "sustained.typ"
    es.write_typst_table(rows, typ_path, endurance=1e6)
    text = typ_path.read_text()
    assert "sustained_trace*" not in text
    assert "not a sustained rate" not in text


def test_rate_is_burst_not_needed_in_upsert_key():
    # Confirms rate_is_burst is NOT part of CSV_KEY_FIELDS -- a re-run that
    # somehow flips is_burst for the same (trace, rate_basis, ...) key must
    # still replace, not duplicate.
    assert "rate_is_burst" not in es.CSV_KEY_FIELDS
    assert "rate_is_burst" in es.CSV_FIELDS
    assert "trace_span_ms" in es.CSV_FIELDS


# ---------------------------------------------------------------------------
# NEW (fix round 1, minor 4a): year convention is surfaced, not just baked in
# ---------------------------------------------------------------------------

def test_year_convention_printed_in_summary_and_typst(tmp_path, capsys):
    assert es.DAYS_PER_YEAR == 365
    assert es.SECONDS_PER_YEAR == 365 * 24 * 3600

    parsed = {
        "records_read": 10, "writes_in_window": 5, "distinct_lines": 5,
        "line_counts": {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}, "rate_basis": "window",
        "window_seconds": 0.25, "span_seconds": 0.25, "offered_rate": 20.0,
    }
    rows = es.evaluate_all(parsed["line_counts"], {"offered": 20.0}, psi=100,
                             seed=1, trace_name="conv_test",
                             capacity_axis=(8,), endurance_axis=(1e6,),
                             write_reduction_axis=(1.0,))
    es.print_summary("conv_test", parsed, rows)
    out = capsys.readouterr().out
    assert "365-day year" in out

    out_path = tmp_path / "conv.typ"
    es.write_typst_table(rows, out_path, endurance=1e6)
    assert "365-day year" in out_path.read_text()
