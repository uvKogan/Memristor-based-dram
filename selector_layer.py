#!/usr/bin/env python3
"""Analytic 1S1R selector layer: what NVSim does not model for the crossbar.

NVSim models no selector physics for the 1S1R cell: the sneak-path row check is
commented out (`SubArray.cpp:137-155`), cell leakage is hard-zero
(`SubArray.cpp:770`), and there is no IR-drop or V/2 read-margin validity check.
At the revision's matched 2048x2048 organization NVSim therefore reports the
SAME leakage for 1T1R and 1S1R (108.384 mW per 1 Gb chip), which makes the
crossbar look free.  This module bounds the three things NVSim omits, at two
published selector qualities, so the book can state that 1S1R leakage and read
margin lie between the bounds.

Sources (page = journal page unless marked PDF page):

  [Zhou]  J. Zhou, K.-H. Kim and W. Lu, "Crossbar RRAM Arrays: Selector Device
          Requirements During Read Operation", IEEE TED 61(5), May 2014,
          pp. 1369-1376.
            Eq. (1) p. 1370 read-margin definition
            Eq. (2) p. 1370 selector I-V, I = gamma*sinh(alpha*V)
            Eq. (3) p. 1371 nonlinearity k = I(Vws)/I(Vws/2)
            Eq. (4) p. 1371 optimal sense resistor sqrt(Ron*Roff)
            Table I p. 1371 default parameters
            Fig. 3(b) p. 1371 read margin vs array size at fixed Isel(ON)
            Fig. 8(a) p. 1374 array power vs nonlinearity, GN-GN scheme
  [HB]    Springer Handbook of Semiconductor Devices.  Crossbar tile limit
          "Tile size = (I_ON / (6*I_leak))^2", I_leak taken at Vth/2,
          Fig. 17.21, pp. 642-643 (after Molas, IMW 2020).  OTS selector
          Ioff 10 nA at 0.5*Vth, Ion 100 uA, Table 30.3.
  [Liu]   T.-Y. Liu et al., "A 130.7 mm2 2-Layer 32-Gb ReRAM Memory Device in
          24-nm Technology", IEEE JSSC 49(1), 2014.  Chip current "dominated by
          the array leakage" from biased unselected cells (p. 1, p. 5); block
          size capped because "leakage current imposes adverse effect for
          sensing and writing" (p. 1); "IR drop in a large array also puts a
          constraint on the number of cells that can be written in parallel on
          the same WL" (p. 2).  This is the silicon-side support for a bounded
          tile.
  [Cross] Crossbar Inc. FAST selector, MEMSYS 2019: sneak current below 0.1 nA
          per selector, selectivity about 1e6 or better.
  [Note]  documents/MBMM_Book_Typst/research_notes/leakage_47x_organization_artifact.md
          sections 8, 9, 10, 12, 13b (the project's own reading of the above,
          with the correction that Zhou/Kim/Lu do NOT support 16 Mb crossbars:
          at k = 1e3 to 1e4 their limit is an array side of roughly 200-256).
  [Mat]   K. Matsui et al., IEICE (advpub 2025VLP0011), p. 5: interconnect
          resistance per cell pitch of 1 ohm for a 22 nm Cu single-level line
          (0.5 ohm double-level).  Used as the default r_line here; Zhou's
          Table I default of 5 ohm is kept for the validation tests.

What this layer deliberately does NOT do: it does not change any NVSim number,
it is not wired into the `mbmm_master.py` pipeline, and it does not tune any
parameter to make a verdict come out favourable.
"""

import argparse
import json
import math
import os
import re
import sys

# Module population, from the config generator's geometry table
# (3_gen_nvmain_config.py, geometry(): "full_dimm" is 8 ranks of 8 devices at
# DeviceWidth 8 on a 64-bit bus), so 8 x 8 = 64 chips on the module.  The
# generated NVMain config is NOT cited because it is regenerated per run (at two
# channels it reads RANKS 4 per channel; the module still has 8 ranks).  A single
# request is served by ONE rank, i.e. by 8 devices, which is why the per-rank
# figure and the all-ranks figure are reported separately below.
DEVICES_PER_RANK = 8
RANKS_PER_DIMM = 8
CHIPS_PER_DIMM = DEVICES_PER_RANK * RANKS_PER_DIMM
DIMM_SOURCE = ("3_gen_nvmain_config.py geometry(): full_dimm = 8 ranks x 8 devices "
               "(DeviceWidth 8, BusWidth 64)")

MIN_READ_MARGIN = 0.10  # Zhou p. 1371, "the minimum requirement of 10%"

# The NVSim config whose forced organization this layer reads.
SELECTOR_CFG = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "configs", "reram_22nm_selector_slc.cfg")

# Operating point.  Taken from the NVSim cell file that
# configs/reram_22nm_selector_slc.cfg points at via -MemoryCellInputFile,
# i.e. configs/reram_22nm_selector_slc.cell, so this layer is consistent with
# the cell NVSim actually simulated.
OPERATING_POINT = {
    "v_read": 1.4,
    "v_read_source": "configs/reram_22nm_selector_slc.cell, -ReadVoltage (V): 1.4",
    "v_half": 0.7,
    "v_half_source": "V/2 half-select scheme: v_read / 2; the handbook tile "
                     "formula takes I_leak at Vth/2 [HB Fig. 17.21]",
    "r_on": 1.0e5,
    "r_on_source": "cell file, -ResistanceOnAtReadVoltage (ohm): 100000",
    "r_off": 1.0e9,
    "r_off_source": "cell file, -ResistanceOffAtReadVoltage (ohm): 1000000000",
    "r_line": 1.0,
    "r_line_source": "22 nm Cu single-level line, 1 ohm per cell pitch [Mat p. 5]",
}

# Two published selector qualities.  Every value carries its citation.
SELECTORS = {
    "OTS": {
        "k": (1.0e4, "Zhou Table I default nonlinearity, p. 1371"),
        "i_on_a": (100e-6, "OTS Ion 100 uA [HB Table 30.3]; also Zhou Table I"),
        "i_leak_a": (10e-9, "OTS Ioff 10 nA at 0.5*Vth [HB Table 30.3]"),
        "label": ("ovonic threshold switch, present-day production selector",
                  "[HB Table 30.3]"),
    },
    "FAST": {
        "k": (1.0e6, "Crossbar FAST selectivity about 1e6 or better [Cross]"),
        "i_on_a": (100e-6, "derived: i_leak_a * selectivity = 0.1 nA * 1e6 [Cross]"),
        "i_leak_a": (0.1e-9, "Crossbar FAST sneak below 0.1 nA per selector [Cross]"),
        "label": ("Crossbar Inc. FAST selector, best published selectivity",
                  "[Cross, MEMSYS 2019]"),
    },
}


# --------------------------------------------------------------------------
# 1. Access-time half-select (sneak) leakage
# --------------------------------------------------------------------------

def sneak_leakage_w(cells_per_line, lines_active, v_half, i_leak_per_cell_a):
    """Half-select leakage power of the ACTIVE lines during one access, in W.

    Model.  In a V/2 crossbar read, every line that is driven for the access
    (each selected wordline and each selected bitline) carries
    `cells_per_line - 1` half-selected cells: the cells on that line whose
    other electrode is NOT selected.  Each of them sits at `v_half` and passes
    `i_leak_per_cell_a`, so

        P = lines_active * (cells_per_line - 1) * v_half * i_leak_per_cell_a

    `lines_active` counts wordlines AND bitlines together, since a line is a
    line.  For the revision's forced organization the count is fixed by the
    NVSim config and is computed by `active_lines_per_chip()` below.

    THIS IS AN ACCESS-TIME TERM, NOT STANDBY LEAKAGE.  Outside an access the
    crossbar lines are unbiased: an unselected, unbiased cell has zero volts
    across it and leaks nothing, which is exactly why a crossbar can be dense.
    The standby adder from this mechanism is therefore ZERO, and this number
    must never be added to a standby figure such as NVSim's 108.384 mW per
    chip.  It is an instantaneous power during an access, to be duty-cycled by
    the fraction of time the array is actually being read before it can be
    compared with anything else.

    No standby bias scheme is modelled, because none of the sources read for
    this layer (Zhou, the Handbook, Liu) describes one: Zhou's six read schemes
    (GN-GN, GN-FT, FT-GN, FT-FT, 1/2 V, 1/3 V, p. 1373) are all access-time bias
    schemes, and Liu's "array leakage" is likewise the current of cells biased
    during an operation (JSSC 49(1), p. 1, p. 5).  If a standby-biased design
    is ever cited, this function can be reused with the standby line count.
    """
    if cells_per_line < 1 or lines_active < 0:
        raise ValueError("cells_per_line must be >= 1 and lines_active >= 0")
    return lines_active * (cells_per_line - 1) * v_half * i_leak_per_cell_a


_FORCE_RE = r"^-%s\s*\(Total[^)]*\)\s*:\s*(\d+)x(\d+)\s*,\s*(\d+)x(\d+)\s*$"


def parse_forced_organization(cfg_path=SELECTOR_CFG):
    """Read `-ForceBank` and `-ForceMat` out of an NVSim config.

    Both keys have the form `-ForceBank (Total AxB, Active CxD): 16x4, 1x4`.
    Returns {"bank_total": (A, B), "bank_active": (C, D), "mat_total": ...,
    "mat_active": ...}.
    """
    try:
        text = open(cfg_path).read()
    except OSError as exc:
        raise SystemExit("ERROR: cannot read NVSim config %s (%s)"
                         % (cfg_path, exc))
    out = {}
    for key, stem in (("ForceBank", "bank"), ("ForceMat", "mat")):
        m = re.search(_FORCE_RE % key, text, re.MULTILINE)
        if not m:
            raise SystemExit(
                "ERROR: %s has no parsable '-%s (Total AxB, Active CxD): "
                "AxB, CxD' line.\n"
                "       This layer derives the number of active subarrays per "
                "access from that\n       forced organization and will not "
                "guess it." % (cfg_path, key))
        g = [int(v) for v in m.groups()]
        out[stem + "_total"] = (g[0], g[1])
        out[stem + "_active"] = (g[2], g[3])
    return out


def active_lines_per_chip(hw, cfg_path=SELECTOR_CFG):
    """Crossbar lines driven per access, derived from the forced organization.

    Nothing here is hardcoded: the counts come from the NVSim config at
    `cfg_path` (default `configs/reram_22nm_selector_slc.cfg`), which forces
    `-ForceBank (Total 16x4, Active 1x4)`, `-ForceMat (Total 2x2, Active 2x2)`
    and `-ForceMuxSenseAmp: 64` (see [Note] section 12).

        active mats per access      = C x D of ForceBank = 1 x 4 = 4
        active subarrays per mat    = C x D of ForceMat  = 2 x 2 = 4
        active subarrays per access = 4 x 4              = 16

    and the total mat count A x B of ForceBank (16 x 4 = 64) is checked against
    `hw["mats"]`, so a config and a metrics file that disagree are an error
    rather than a silent wrong answer.

    With mux 64 each active subarray sensed `subarray_cols / mux` = 32 bits, so
    16 x 32 = 512, which is the config's `-WordWidth (bit): 512`.  Per active
    subarray that is 1 selected wordline and 32 selected bitlines.

    Returns (active_subarrays, active_lines, bits_per_subarray).
    """
    org = parse_forced_organization(cfg_path)
    total_mats = org["bank_total"][0] * org["bank_total"][1]
    if "mats" in hw and hw["mats"] != total_mats:
        raise SystemExit(
            "ERROR: %s forces %dx%d = %d mats in total, but the metrics file "
            "records mats = %s.\n       The config and the NVSim run do not "
            "describe the same part."
            % (cfg_path, org["bank_total"][0], org["bank_total"][1],
               total_mats, hw["mats"]))
    subarrays = (org["bank_active"][0] * org["bank_active"][1] *
                 org["mat_active"][0] * org["mat_active"][1])
    bits = hw["subarray_cols"] // hw["mux"]
    return subarrays, subarrays * (1 + bits), bits


def half_select_power_w(hw, v_half, i_leak_per_cell_a, cfg_path=SELECTOR_CFG):
    """Access-time half-select power of one chip, exactly, in W.

    The cells that are FULLY selected are excluded rather than approximated
    away (review item 5).  Per active subarray, with `b` = subarray_cols / mux
    sensed bits, the access drives 1 wordline and `b` bitlines, and exactly `b`
    cells are fully selected: one per sensed bit, each sitting on the selected
    wordline at the crossing of a selected bitline.  So

        on the selected wordline : subarray_cols - b half-selected cells
        on each selected bitline : subarray_rows - 1 half-selected cells

    At the revision's organization that is 16 x ((2048 - 32) + 32 x 2047)
    = 1,080,320 half-selected cells per access per chip.  Treating every active
    line as carrying `cells_per_line - 1` half-selected cells, as the plain
    `sneak_leakage_w` formula does, would give 528 x 2047 = 1,080,816, high by
    496 cells or 0.046 percent, because it counts the 32 fully selected cells
    of each chip twice over on the wordline side.  Both are computed through
    `sneak_leakage_w`; this function just feeds it the exact line lengths.
    """
    subarrays, _, bits = active_lines_per_chip(hw, cfg_path)
    # wordline side: one line per active subarray, (cols - bits) half-selected
    p_wl = sneak_leakage_w(hw["subarray_cols"] - bits + 1, subarrays,
                           v_half, i_leak_per_cell_a)
    # bitline side: `bits` lines per active subarray, (rows - 1) half-selected
    p_bl = sneak_leakage_w(hw["subarray_rows"], subarrays * bits,
                           v_half, i_leak_per_cell_a)
    cells = (subarrays * (hw["subarray_cols"] - bits) +
             subarrays * bits * (hw["subarray_rows"] - 1))
    return p_wl + p_bl, cells


# --------------------------------------------------------------------------
# 2. Read margin (Zhou, TED 2014)
# --------------------------------------------------------------------------

def selector_alpha_gamma(k, i_on, v_read):
    """Zhou Eq. (2) and Eq. (3) solved for the selector's two parameters.

    Eq. (3) k = sinh(alpha*V) / sinh(alpha*V/2).  Using
    sinh(x) = 2*sinh(x/2)*cosh(x/2) this is exactly k = 2*cosh(alpha*V/2), so

        alpha = (2 / v_read) * acosh(k / 2)        [V^-1]
        gamma = i_on / sinh(alpha * v_read)        [A]

    Check against Zhou Table I (k = 1e4, Isel(ON) = 100 uA at Vws = 1 V):
    alpha = 2*acosh(5000) = 18.4207 V^-1 and gamma = 2.0e-12 A, which is what
    Table I prints, to every digit given.
    """
    if k <= 2.0:
        raise ValueError("k must exceed 2 (Zhou Eq. 3 gives k = 2*cosh(...))")
    alpha = 2.0 / v_read * math.acosh(k / 2.0)
    return alpha, i_on / math.sinh(alpha * v_read)


def _cell(v, r, alpha, gamma):
    """Current and conductance of one cell: selector Eq. (2) in series with r.

    The forward characteristic is inverted explicitly,
    V(I) = I*r + asinh(I/gamma)/alpha, and Newton is run on I.  The cell is
    odd-symmetric, as a bipolar selector is (Zhou Section II-C).
    """
    sign = -1.0 if v < 0 else 1.0
    va = abs(v)
    if va == 0.0:
        c = gamma * alpha
        return 0.0, c / (1.0 + c * r)
    i = va / (r + 1.0 / (alpha * gamma))
    for _ in range(80):
        f = i * r + math.asinh(i / gamma) / alpha - va
        step = f / (r + 1.0 / (alpha * math.sqrt(gamma * gamma + i * i)))
        if step > 0.5 * i:
            step = 0.5 * i
        i -= step
        if i <= 0.0:
            i = 1e-30
        if abs(step) <= 1e-15 * i + 1e-30:
            break
    return sign * i, 1.0 / (r + 1.0 / (alpha * math.sqrt(gamma * gamma + i * i)))


def _thomas(a, b, c, d):
    """Tridiagonal solve (Thomas)."""
    n = len(b)
    cp = [0.0] * n
    dp = [0.0] * n
    m = b[0]
    cp[0] = c[0] / m
    dp[0] = d[0] / m
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp[i] = c[i] / m
        dp[i] = (d[i] - a[i] * dp[i - 1]) / m
    x = [0.0] * n
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return x


def _solve(n, alpha, gamma, r_on, r_target, r_line, v_read, r_sense,
           bl_termination="sense"):
    """Solve the worst-case n x n crossbar in Zhou's GN-GN scheme.

    Returns the node voltage vector `x` of length 2n+1.  `x[-1]` is Vout and
    `(v_read - x[0]) / r_line` is the current the wordline driver supplies, so
    both the read margin and the array power come from this one solve.

    Network (Zhou Fig. 1, p. 1370, and Section II-B).  Selected wordline driven
    at v_read from one end; selected bitline read through r_sense at the far
    end; unselected wordlines and bitlines grounded; `r_line` between
    neighbouring cells.  Worst case per Zhou p. 1370: the target cell sits at
    the corner farthest from both sources and every unselected cell is in LRS.

    Reduction.  Zhou solve the whole n x n network in HSPICE; the paper gives
    no closed form for the read margin, only Eq. (1)-(4).  Ordering the
    unknowns along the selected wordline and then back down the selected
    bitline turns the dominant part of that network into a single chain of
    2n+1 nodes, which is tridiagonal and solves in milliseconds:

      * nodes 0..n-1  : the selected wordline, cell j shunted to its
                        unselected bitline through an LRS cell in series with
                        r_sense (`bl_termination="sense"`, the default) or
                        straight to ground (`bl_termination="ground"`).

                        THE PAPER IS IN TENSION WITH ITSELF HERE.  Table I and
                        Sec. II-B (p. 1370) define the GN-GN scheme by
                        V_BNS = 0, i.e. unselected bitlines hard grounded, and
                        Fig. 1 draws R_sense on the selected bitline only.  But
                        the same page says "sense amplifiers are connected with
                        all bit-lines to convert the output current into voltage
                        signal", which puts an R_sense in every bitline's path
                        to its 0 V supply.  The sense reading is used here
                        because it is the only one that reproduces the paper's
                        own results: with hard grounding the model gives 7.0
                        percent read margin at N = 128, k = 1e4 against
                        Fig. 3(b)'s 12.4 percent (out by 1.8x) and 660 uW array
                        power against Fig. 8(a)'s roughly 200 uW (out by 3.3x),
                        while the sense reading lands at 12.4 percent and
                        209 uW.  `bl_termination="ground"` is kept so that this
                        comparison is an executable test, not a claim in a
                        report.  The detail matters because it sets the current
                        the selected wordline carries and hence its IR drop.
      * node n-1 -> n : the target cell, r_target = r_on (LRS) or r_off (HRS).
      * nodes n..2n   : the selected bitline, each node shunted by an LRS cell
                        to its grounded unselected wordline, and node 2n tied
                        to ground through r_sense.  x[2n] is Vout.

    The only physics dropped relative to the full HSPICE network is the
    resistance of the UNSELECTED lines, i.e. the third-order sneak path through
    the (n-1)^2 cells that touch neither selected line.  With a nonlinear
    selector that path carries almost nothing (at k >= 1e3 an unselected line
    floats up by a few mV and the cells on it pass well under a pA), which the
    validation below confirms; at k = 1e2 it is not negligible and this
    reduction is optimistic, so `read_margin` is documented as valid for
    k >= 1e3.  Both published bounds here are k >= 1e4.

    Validation, in tests/test_selector_layer.py: at Zhou's Table I parameters
    this reproduces Fig. 3(b) to about 0.2 percentage points over N = 8..512 for
    k = 1e3, 1e4 and 1e5, and independently reproduces the GN-GN array power of
    Fig. 8(a) to about 5 percent over the same k range.
    """
    if bl_termination not in ("sense", "ground"):
        raise ValueError("bl_termination must be 'sense' or 'ground'")
    r_shunt_extra = r_sense if bl_termination == "sense" else 0.0
    m = 2 * n + 1
    gl = 1.0 / r_line
    x = [0.0] * m
    steps = 6
    for st in range(1, steps + 1):
        vsrc = v_read * st / steps
        for _ in range(60):
            a = [0.0] * m
            b = [0.0] * m
            c = [0.0] * m
            f = [0.0] * m
            f[0] += (x[0] - vsrc) * gl
            b[0] += gl
            for j in list(range(n - 1)) + list(range(n, 2 * n)):
                cur = (x[j] - x[j + 1]) * gl
                f[j] += cur
                f[j + 1] -= cur
                b[j] += gl
                b[j + 1] += gl
                c[j] -= gl
                a[j + 1] -= gl
            it, dt = _cell(x[n - 1] - x[n], r_target, alpha, gamma)
            f[n - 1] += it
            f[n] -= it
            b[n - 1] += dt
            b[n] += dt
            c[n - 1] -= dt
            a[n] -= dt
            for j in range(n - 1):
                ii, dd = _cell(x[j], r_on + r_shunt_extra, alpha, gamma)
                f[j] += ii
                b[j] += dd
            for j in range(n + 1, 2 * n):
                ii, dd = _cell(x[j], r_on, alpha, gamma)
                f[j] += ii
                b[j] += dd
            f[m - 1] += x[m - 1] / r_sense
            b[m - 1] += 1.0 / r_sense
            dx = _thomas(a, b, c, [-v for v in f])
            worst = 0.0
            for i in range(m):
                s = max(-0.15, min(0.15, dx[i]))
                x[i] += s
                worst = max(worst, abs(s))
            if worst < 1e-13:
                break
    return x


def _check_array(n, k, r_on, r_off, r_line, i_on, v_read, r_sense):
    """Validate every array and device argument, with a clear message each."""
    if n < 2:
        raise ValueError("n must be at least 2, got %r" % (n,))
    if k <= 1.0:
        raise ValueError("k (selector nonlinearity) must exceed 1, got %r" % (k,))
    for name, value in (("r_on", r_on), ("r_off", r_off), ("r_line", r_line),
                        ("i_on", i_on), ("v_read", v_read)):
        if not value > 0.0:
            raise ValueError("%s must be positive, got %r" % (name, value))
    if r_off <= r_on:
        raise ValueError("r_off must exceed r_on (HRS above LRS), got "
                         "r_on=%r r_off=%r" % (r_on, r_off))
    if r_sense is not None and not r_sense > 0.0:
        raise ValueError("r_sense must be positive, got %r" % (r_sense,))


def read_margin(n, k, r_on, r_off, r_line, i_on=100e-6, v_read=1.0, r_sense=None,
                bl_termination="sense"):
    """Worst-case read margin of an n x n 1S1R crossbar, Zhou Eq. (1) p. 1370.

        RM = (Vout(LRS) - Vout(HRS)) / v_read

    with the selector of Eq. (2)-(3) (nonlinearity `k`, on-current `i_on` at
    `v_read`) and, by default, the optimal sense resistor of Eq. (4),
    r_sense = sqrt(r_on * r_off).  Zhou's minimum acceptable value is 10%
    (p. 1371).  Valid for k >= 1e3; see `_solve` for why, and for what
    `bl_termination` does.
    """
    _check_array(n, k, r_on, r_off, r_line, i_on, v_read, r_sense)
    if r_sense is None:
        r_sense = math.sqrt(r_on * r_off)
    alpha, gamma = selector_alpha_gamma(k, i_on, v_read)
    lrs = _solve(n, alpha, gamma, r_on, r_on, r_line, v_read, r_sense,
                 bl_termination)[-1]
    hrs = _solve(n, alpha, gamma, r_on, r_off, r_line, v_read, r_sense,
                 bl_termination)[-1]
    return (lrs - hrs) / v_read


def array_power_w(n, k, r_on, r_off, r_line, i_on=100e-6, v_read=1.0,
                  r_sense=None, state="LRS", bl_termination="sense"):
    """Total power the wordline driver supplies to the array during a read, W.

    Zhou Fig. 8, p. 1374, "overall power consumption of the entire crossbar
    array", for the GN-GN scheme reading a 1 (`state="LRS"`) or a 0
    (`state="HRS"`).  This is the SAME network solve `read_margin` uses, read
    out at the source instead of at the sense resistor:

        I_supply = (v_read - x[0]) / r_line ,   P = v_read * I_supply

    so it is an independent check on the currents the topology carries, not
    just on the output voltage.  See `_solve` for `bl_termination`.
    """
    _check_array(n, k, r_on, r_off, r_line, i_on, v_read, r_sense)
    if state not in ("LRS", "HRS"):
        raise ValueError("state must be 'LRS' or 'HRS', got %r" % (state,))
    if r_sense is None:
        r_sense = math.sqrt(r_on * r_off)
    alpha, gamma = selector_alpha_gamma(k, i_on, v_read)
    r_target = r_on if state == "LRS" else r_off
    x = _solve(n, alpha, gamma, r_on, r_target, r_line, v_read, r_sense,
               bl_termination)
    return v_read * (v_read - x[0]) / r_line


def max_side_above_margin(k, r_on, r_off, r_line, i_on, v_read,
                          margin=MIN_READ_MARGIN, lo=64, hi=8192, step=64):
    """Largest crossbar side (multiple of `step`) whose read margin >= margin."""
    if read_margin(lo, k, r_on, r_off, r_line, i_on, v_read) < margin:
        return 0
    if read_margin(hi, k, r_on, r_off, r_line, i_on, v_read) >= margin:
        return hi
    while hi - lo > step:
        mid = ((lo + hi) // 2 // step) * step
        if mid <= lo:
            break
        if read_margin(mid, k, r_on, r_off, r_line, i_on, v_read) >= margin:
            lo = mid
        else:
            hi = mid
    return lo


# --------------------------------------------------------------------------
# 3. Tile validity (handbook)
# --------------------------------------------------------------------------

def max_tile_side(i_on, i_leak):
    """Largest crossbar side the handbook rule allows: I_ON / (6 * I_leak).

    [HB] Fig. 17.21, pp. 642-643 gives "Tile size = (I_ON / (6*I_leak))^2" in
    CELLS, with I_leak the selector leakage at Vth/2, so the tile SIDE is
    I_ON / (6 * I_leak).  Hand check: 100 uA / (6 * 10 nA) = 1666.7.
    """
    if i_leak <= 0.0:
        raise ValueError("i_leak must be positive")
    return i_on / (6.0 * i_leak)


def tile_valid(i_on, i_leak, side):
    """True if a `side` x `side` crossbar tile passes the handbook rule.

    The brief's two-argument `tile_valid(i_on, i_leak)` cannot return a verdict
    for a given side, so the side is the third argument; `max_tile_side` gives
    the bound itself.
    """
    return side <= max_tile_side(i_on, i_leak)


# --------------------------------------------------------------------------
# 4. Driver
# --------------------------------------------------------------------------

def load_hardware(path, key="reram_22nm_selector_slc"):
    """Load the 1S1R device metrics, failing clearly on a pre-revision file."""
    with open(path) as fh:
        data = json.load(fh)
    if key not in data:
        raise SystemExit("ERROR: %s has no '%s' entry." % (path, key))
    hw = data[key]
    missing = [f for f in ("subarray_rows", "subarray_cols", "mats", "mux",
                           "leakage_mw", "capacity_gb") if f not in hw]
    if missing:
        raise SystemExit(
            "ERROR: %s['%s'] is missing %s.\n"
            "       This looks like the FROZEN pre-revision hardware_metrics.json,\n"
            "       which records no subarray organization. Point --hardware at the\n"
            "       2026-09 staging file, e.g.\n"
            "         results/rev2026-09_staging/hardware_metrics_2048x2048.json"
            % (path, key, ", ".join(missing)))
    if hw["subarray_rows"] != hw["subarray_cols"]:
        raise SystemExit(
            "ERROR: this layer models a square crossbar; %s['%s'] is %dx%d."
            % (path, key, hw["subarray_rows"], hw["subarray_cols"]))
    return hw


def evaluate(hw, op=OPERATING_POINT, cfg_path=SELECTOR_CFG, side_ceiling=8192):
    """Both bounds, for the organization in `hw` at the operating point `op`.

    `side_ceiling` caps the search in `max_side_above_margin`; the default 8192
    is well past where the margin falls through 10 percent at this operating
    point, and tests pass a small ceiling to stay fast.
    """
    side = hw["subarray_rows"]
    subarrays, lines, bits = active_lines_per_chip(hw, cfg_path)
    org = parse_forced_organization(cfg_path)
    out = {
        "operating_point": dict(op),
        "organization": {
            "subarray_rows": side,
            "subarray_cols": hw["subarray_cols"],
            "mux": hw["mux"],
            "mats": hw["mats"],
            "sensed_bits_per_subarray": bits,
            "active_subarrays_per_access": subarrays,
            "active_wordlines_per_access": subarrays,
            "active_bitlines_per_access": subarrays * bits,
            "active_lines_per_access": lines,
            "fully_selected_cells_per_access": subarrays * bits,
            "nvsim_leakage_mw_per_chip": hw["leakage_mw"],
            "devices_per_rank": DEVICES_PER_RANK,
            "ranks_per_dimm": RANKS_PER_DIMM,
            "chips_per_dimm": CHIPS_PER_DIMM,
            "chips_source": DIMM_SOURCE,
            "forced_organization": {"config": cfg_path,
                                    "bank_total": list(org["bank_total"]),
                                    "bank_active": list(org["bank_active"]),
                                    "mat_total": list(org["mat_total"]),
                                    "mat_active": list(org["mat_active"])},
            "note": "active subarrays = (bank active C x D) x (mat active "
                    "C x D), parsed from the config; see active_lines_per_chip()",
        },
        "bounds": {},
    }
    for name, sel in SELECTORS.items():
        k = sel["k"][0]
        i_on = sel["i_on_a"][0]
        i_leak = sel["i_leak_a"][0]
        p_chip, cells = half_select_power_w(hw, op["v_half"], i_leak, cfg_path)
        out["organization"]["half_selected_cells_per_access"] = cells
        rm_here = read_margin(side, k, op["r_on"], op["r_off"], op["r_line"],
                              i_on, op["v_read"])
        best = max_side_above_margin(k, op["r_on"], op["r_off"], op["r_line"],
                                     i_on, op["v_read"], hi=side_ceiling)
        out["bounds"][name] = {
            "parameters": {f: {"value": v[0], "source": v[1]}
                           for f, v in sel.items() if f != "label"},
            "description": sel["label"][0] + " " + sel["label"][1],
            "sneak_leakage": {
                "access_time_w_per_chip": p_chip,
                "access_time_w_per_accessed_rank": p_chip * DEVICES_PER_RANK,
                "access_time_w_all_ranks_upper_bound": p_chip * CHIPS_PER_DIMM,
                "standby_adder_w_per_chip": 0.0,
                "standby_adder_w_per_accessed_rank": 0.0,
                "standby_adder_w_all_ranks_upper_bound": 0.0,
                "standby_reasoning":
                    "unselected, unbiased crossbar lines have no voltage across "
                    "their cells and leak nothing, so this mechanism adds ZERO "
                    "to standby leakage. The per-chip number above is an "
                    "instantaneous power DURING an access and must be "
                    "duty-cycled before being compared with anything; it must "
                    "never be added to the NVSim standby figure of %.3f mW."
                    % hw["leakage_mw"],
                "scope_labels": {
                    "access_time_w_per_chip":
                        "one 1 Gb device while it is being accessed",
                    "access_time_w_per_accessed_rank":
                        "the %d devices of the ONE rank that serves a single "
                        "request; this is the figure to pair with a request "
                        "(%s)" % (DEVICES_PER_RANK, DIMM_SOURCE),
                    "access_time_w_all_ranks_upper_bound":
                        "UPPER BOUND ONLY: all %d ranks (%d devices) accessing "
                        "at the same instant. A single request never does this. "
                        "None of these three numbers is a DIMM leakage figure."
                        % (RANKS_PER_DIMM, CHIPS_PER_DIMM),
                },
            },
            "verdict": {
                "tile_valid_at_%d" % side: tile_valid(i_on, i_leak, side),
                "max_tile_side": max_tile_side(i_on, i_leak),
                "read_margin_at_%d" % side: rm_here,
                "read_margin_min_required": MIN_READ_MARGIN,
                "read_margin_ok_at_%d" % side: rm_here >= MIN_READ_MARGIN,
                "max_side_read_margin_above_10pct": best,
                "read_margin_at_max_side":
                    read_margin(best, k, op["r_on"], op["r_off"], op["r_line"],
                                i_on, op["v_read"]) if best else None,
                "binding_limit":
                    "handbook tile leakage" if max_tile_side(i_on, i_leak) < best
                    else "read margin",
            },
        }
    return out


def render(res):
    """Human-readable table."""
    org, op = res["organization"], res["operating_point"]
    side = org["subarray_rows"]
    L = ["Analytic 1S1R selector layer (T2.7) - bounds on what NVSim omits",
         "=" * 74,
         "Operating point (from configs/reram_22nm_selector_slc.cell):",
         "  V_read %.2f V, V_half %.2f V, R_on %.3g ohm, R_off %.3g ohm, "
         "r_line %.3g ohm/cell" % (op["v_read"], op["v_half"], op["r_on"],
                                   op["r_off"], op["r_line"]),
         "Organization (forced in %s):" % org["forced_organization"]["config"],
         "  %dx%d subarray, mux %d, %d active subarrays "
         "(bank active %dx%d x mat active %dx%d), %d sensed bits/subarray"
         % (side, org["subarray_cols"], org["mux"],
            org["active_subarrays_per_access"],
            org["forced_organization"]["bank_active"][0],
            org["forced_organization"]["bank_active"][1],
            org["forced_organization"]["mat_active"][0],
            org["forced_organization"]["mat_active"][1],
            org["sensed_bits_per_subarray"]),
         "  per access, per chip: %d wordlines + %d bitlines = %d active lines,"
         " %d fully selected cells,"
         % (org["active_wordlines_per_access"],
            org["active_bitlines_per_access"],
            org["active_lines_per_access"],
            org["fully_selected_cells_per_access"]),
         "                        %d half-selected cells"
         % org["half_selected_cells_per_access"],
         "  NVSim standby leakage, per chip: %.3f mW (identical for 1T1R and "
         "1S1R)" % org["nvsim_leakage_mw_per_chip"], "",
         "%-6s %7s %8s %9s %11s %11s %13s %8s %8s %10s %9s"
         % ("bound", "k", "I_on", "I_leak", "sneak/chip", "sneak/rank",
            "sneak/all-rank", "standby", "RM@%d" % side, "tile@%d" % side,
            "max side"), "-" * 112]
    tag = {}
    for name, b in res["bounds"].items():
        v, p, s = b["verdict"], b["parameters"], b["sneak_leakage"]
        tag[name] = "VALID" if v["tile_valid_at_%d" % side] else "NOT VALID"
        L.append("%-6s %7.0e %7.0fu %8.1fn %8.3f mW %8.3f mW %10.3f mW %7.1f "
                 "%7.1f%% %10s %9d"
                 % (name, p["k"]["value"], p["i_on_a"]["value"] * 1e6,
                    p["i_leak_a"]["value"] * 1e9,
                    s["access_time_w_per_chip"] * 1e3,
                    s["access_time_w_per_accessed_rank"] * 1e3,
                    s["access_time_w_all_ranks_upper_bound"] * 1e3,
                    s["standby_adder_w_per_chip"],
                    v["read_margin_at_%d" % side] * 100, tag[name],
                    int(v["max_tile_side"])))
    L += ["-" * 112,
          "All three sneak columns are ACCESS-TIME power, duty-cycled by array "
          "activity. None of",
          "them is a DIMM leakage figure. The standby adder is zero: unbiased "
          "crossbar lines leak",
          "nothing. sneak/chip is one 1 Gb device during an access; sneak/rank "
          "is the %d devices of" % DEVICES_PER_RANK,
          "the one rank that serves a single request, and is the figure to pair "
          "with a request;",
          "sneak/all-rank is an UPPER BOUND with all %d ranks (%d devices) "
          "accessing at once, which" % (RANKS_PER_DIMM, CHIPS_PER_DIMM),
          "a single request never does. Source: %s." % DIMM_SOURCE,
          "", "Verdicts:"]
    for name, b in res["bounds"].items():
        v = b["verdict"]
        L += ["  %-5s tile %dx%d: %s (handbook max side %d, I_on/(6*I_leak))"
              % (name, side, side, tag[name], int(v["max_tile_side"])),
              "        read margin at %d: %.1f%% (%s the 10%% minimum); largest "
              "side above 10%%: %d"
              % (side, v["read_margin_at_%d" % side] * 100,
                 "above" if v["read_margin_ok_at_%d" % side] else "below",
                 v["max_side_read_margin_above_10pct"]),
              "        binding limit: %s" % v["binding_limit"]]
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--hardware", default="results/hardware_metrics.json",
                    help="NVSim device metrics JSON (needs subarray fields; "
                         "the frozen pre-revision file does not have them)")
    ap.add_argument("--out", default="results/selector_layer.json")
    ap.add_argument("--config", default=SELECTOR_CFG,
                    help="NVSim config holding the forced organization")
    ap.add_argument("--side-ceiling", type=int, default=8192,
                    help="upper bound of the search for the largest crossbar "
                         "side that keeps the read margin above 10 percent")
    args = ap.parse_args(argv)
    res = evaluate(load_hardware(args.hardware), cfg_path=args.config,
                   side_ceiling=args.side_ceiling)
    res["meta"] = {"hardware_source": args.hardware,
                   "config_source": args.config,
                   "side_ceiling": args.side_ceiling,
                   "module": "selector_layer.py",
                   "task": "T2.7"}
    outdir = os.path.dirname(args.out)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump(res, fh, indent=2, sort_keys=False)
        fh.write("\n")
    print(render(res))
    print("\nwrote %s" % args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
