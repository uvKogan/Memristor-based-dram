# Lead Handoff — Tier-3 Structural Decisions

**Purpose:** this session did the original super-critique and reviewed the Tier-3
proposals in `Tier3_Prep_Proposals.md`. Another agent is actively editing
`Project_Book.typ` in parallel — **no edits to the book are made from this file or
this session.** This document packages the Lead's decisions/guidance for that agent
to execute, per the ground rules in `Review_Fixes_Tracker.md` (claim the item, set
`in-progress`, run the compile gate, log the change).

---

## T3-1: Related Work (§1.3) — APPROVED, ready to execute

The proposal in `Tier3_Prep_Proposals.md` is sound and directly answers the
original critique's finding #5 ("no related-work section anywhere in the book").
Approved as proposed. Prompt for the book-editing agent:

> Add a new **§1.3 "Related Work"**, placed after §1.2 (ReRAM Fundamentals) and
> before §2, per the structure already drafted in `Tier3_Prep_Proposals.md`
> (T3-1): (1) the three ISCA 2009 PCM-as-DRAM-alternative papers (Lee/Ipek/Mutlu/
> Burger; Qureshi/Srinivasan/Rivers; Zhou/Zhao/Yang/Zhang), (2) Xu et al., HPCA
> 2015 (crossbar ReRAM main memory — the closest prior work to this book) and
> Kültürsay et al., ISPASS 2013 (STT-RAM parallel study), (3) Izraelevitz et al.'s
> Optane DC measurement paper, (4) a positioning paragraph stating what this book
> adds over all of the above (DDR5-era baselines, device-anchored 22nm
> characterization feeding a cycle-accurate system model, explicit 1T1R-vs-1S1R
> comparison at matched process, the toolchain fidelity audit, endurance from
> measured per-subarray write counts).
>
> **Before citing any of these**, verify each one's exact title, venue, year, and
> DOI via web search — do not cite from memory. Add as refs [36]–[41] in
> bibliography order, with matching `Reference_Guide.md` entries (same verification
> standard already used for refs [33]–[35]). Note the "skip 1.x on a first pass"
> guidance in `Reading_Guide.md` needs an exception carved out for §1.3.
>
> Claim `T3-1` in `Review_Fixes_Tracker.md`, run the compile gate, log the change
> with anchor strings for the new section's start/end.

---

## T3-2: §3.1.6 placement — DECIDED 2026-08-23: Option A, no further action

> **Resolution:** discussed with the book-editing agent; the Lead chose to keep
> Option A as implemented (summary paragraph at top of §3.1, anchor "One framing
> note before the numbers"; §3.1.6 unmoved, all 35 cross-references intact).
> Options B/C/D below are retained for the record only.

The Lead wants to discuss this directly with the book-editing agent before
choosing. Full pros/cons below — the existing proposal recommends Option A, but
that recommendation is driven primarily by mechanical risk (35 cross-references),
not necessarily by what reads best, so it's presented here without a thumb on the
scale.

### Option A — Leave §3.1.6 in place; add a one-paragraph trust-summary near the top of §3.1
**Pros**
- Zero risk to the 35 existing in-body "Section 3.1.6, item N" cross-references — nothing to retarget.
- Small edit (~6 lines), fast to implement and easy to verify by diff.
- Keeps the audit adjacent to the results pipeline it repairs — useful for a reader doing a deep methodological check.
- Directly answers the critique's actual complaint (trust framework arrives after the results): the summary now arrives first even though the full detail stays put.

**Cons**
- Doesn't fully resolve the structural complaint — a reader wanting the full audit still scrolls ~230 lines forward to find it.
- Two places now describe the audit (new summary + full section) — a minor future drift risk if one is edited without the other.
- Doesn't touch §3.1's disproportionate length (987 lines vs. 3.2's 90 and 3.3's 344) — the bloat complaint from the original critique stands regardless.

### Option B — Move §3.1.6 to an appendix, leave a stub/pointer
**Pros**
- Directly fixes the proportionality complaint — §3.1 shrinks by ~230 lines, much closer to 3.2/3.3's scale.
- Matches common paper convention (validation/audit detail in an appendix, "see Appendix D" inline).
- Frees §3.1 to read as a clean results narrative without a 230-line methodological detour in the middle.

**Cons**
- Requires retargeting all 35 "Section 3.1.6, item N" references to a new appendix label — real mechanical risk of a missed or mistyped reference in a 2,300+ line file with no automated rename tooling.
- Breaks locality: a reader hits an item citation inline and now has to flip to the back of the document instead of scrolling a few hundred lines within the same section.
- Any future edit to the audit's item list requires synchronized updates across two increasingly distant locations.
- Changes the reader's mental map of what appendices contain — Appendix A is currently "Simulation Parameters and Literature Grounding"; a second, differently-purposed appendix sits alongside it.

### Option C — Move §3.1.6 before §3.1.1 (audit-first ordering)
**Pros**
- Puts the full trust framework before any result is stated at all — no "trust me for now" gap, the most rigorous possible reading order.
- Makes Option A's summary paragraph unnecessary (the full audit already leads).

**Cons**
- Larger renumbering blast radius than Option B: every subsequent §3.1 subsection (3.1.1 latency, 3.1.2 power, etc.) shifts, not just the cross-reference targets.
- Buries the actual results — what most readers (this book's own lab audience included) come for — under 230 lines of toolchain forensics before a single result number appears.
- The worst reader-experience option of the three for anyone not doing a line-by-line methodological audit.

### Option D — Partial restructuring (not in the original proposal, worth naming)
Extract only a **scannable summary table** of the 14 audit items (what was found →
what was repaired, one line each) to the top of §3.1, while leaving the full
forensic narrative — why each bug existed, how it was diagnosed, the validation
arithmetic — in place at §3.1.6.

**Pros**
- A middle path: gives the up-front scannability of Option C without moving or renumbering anything.
- The table itself becomes a useful standalone artifact (could double as a backup/appendix slide for the talk).

**Cons**
- Adds an editing task neither A nor B requires: extracting currently-prose content into a new table, then keeping that table in sync with §3.1.6 if it's ever edited later.

---

## T3-3: Conclusion rewrite (§4) — APPROVED, ready to execute

The draft in `Conclusion_Rewrite_Draft.md` was checked against the current §4 text
during this session (independently re-derived from the same §3 source numbers this
session read directly: the 1.7x/2.8x MLC streaming slowdowns, the 50.9/1.12/0.651/
0.040 W leakage tiers, the 47x device leakage gap, the 21,350.6/737.1 → 29x PDP
ratio, and the ±20% ReadVoltage sweep's <4% PDP variation all match the book's
existing §3 content verbatim). Approved as drafted, with two small additions below.

**Two suggested additions before applying** (for consistency with this book's own
citation density — every other claim in §4 cites its source section/table inline):

1. In paragraph 2, "the density ratios survive their cell-area sensitivity bounds"
   → append "(§3.3, cell-area sensitivity passage)".
2. In paragraph 2, "the endurance threshold moves but does not vanish under
   pessimistic leveling" → append "(§3.1.4 hot-spot bound)".

Prompt for the book-editing agent:

> Apply the replacement text in `Conclusion_Rewrite_Draft.md` verbatim, with the
> two citation additions above, replacing the six per-section recap paragraphs in
> §4 (the block starting "Latency analysis (3.1.1) revealed…" through "…only
> high-MLP AI workloads convert added ranks into latency gains."). Leave the
> opening synthesis paragraph, §4.1, §4.2, and §4.3 untouched, per the draft's own
> scope note. Claim `T3-3` in `Review_Fixes_Tracker.md`, run the compile gate, and
> log the change with the anchor strings for the replaced block's start and end.

---

## Summary for the Lead

| Item | Status | Next step |
|---|---|---|
| T3-1 Related Work | Executed 2026-08-23 | None. Note: refs are [36]–[40], not [36]–[41] — Izraelevitz was already ref [32], Optane-exit [23] |
| T3-2 §3.1.6 placement | Decided: Option A, closed | None |
| T3-3 Conclusion rewrite | Executed 2026-08-23 (+2 citation additions) | None |
