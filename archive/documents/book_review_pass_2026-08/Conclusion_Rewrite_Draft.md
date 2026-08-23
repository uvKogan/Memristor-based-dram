# Conclusion Rewrite Draft (T3-3) — for side-by-side review

**STATUS: APPLIED 2026-08-23** per the Lead's approval in `Lead_Decisions_and_Handoff.md`, including its two citation additions ("(Section 3.3, cell-area sensitivity passage)" and "(Section 3.1.4 hot-spot bound)"). This file is retained as the review record; the book is the canonical text.

## What stays untouched

- The opening synthesis paragraph ("This research delivers two things…"), including the deployment recommendation, the research-agenda sentence, and the open-source contribution sentence — it already does the synthesis job.
- §4.1, §4.2, §4.3 (future work and reproducibility) — unchanged.

## What gets replaced

The six per-section recap paragraphs (starting "Latency analysis (3.1.1) revealed…" through "…only high-MLP AI workloads convert added ranks into latency gains.") — roughly 60 lines that re-derive §3 nearly paragraph-for-paragraph.

## Replacement text (two paragraphs)

> Each results axis resolves to a one-line verdict. Latency (3.1.1): the MLC write penalty is workload-dependent, not uniform — absorbed by controller queueing under compute-bound traces, compounding to 1.7x/2.8x under saturating streams — which confines MLC to read-dominant roles. Power (3.1.2): the earlier technology-blind "Standby Convergence" gave way to a leakage-class hierarchy — 50.9 W ungated 1T1R, 1.12 W ungated 1S1R, 0.651 W DDR5 (calibration floor), 0.040 W PCM — so ungated ReRAM power *is* leakage, and the selector's 47x standby discipline is the largest technology-differentiating fact this project measured. Efficiency (3.1.3): that same leakage term inverts the intra-ReRAM hierarchy — 1S1R SLC dominates 1T1R SLC by 29x on geometric-mean PDP — leakage class, not cell speed, decides efficiency. Endurance (3.1.4): lifetime scales linearly with capacity, so the constraint binds only for small modules under sustained write streaming. Robustness (3.1.5): the operating point is stable — read latency invariant and system-level PDP within 4% across a ±20% ReadVoltage sweep. Scaling (3.2): added ranks pay off only where memory-level parallelism exists to use them — the Flatline Paradox — making single-chip or 8-chip configurations Pareto-optimal for write-heavy deployments.
>
> The scope of these claims is bounded by four disclosed limitations, gathered here deliberately in one place: validation is internal to the toolchain — parameters are anchored to real silicon and vendor datasheets, but no end-to-end result is checked against measured hardware (Section 2.2); the power-parity path rests on bounding arithmetic over idle-gating the simulator cannot yet exercise (Sections 3.1.6 item 5 and 3.3); endurance projections assume ideal uniform wear leveling, with the hot-spot exposure bounded but not simulated (Section 3.1.4); and the traces are cache-less, first-10M-instruction captures with one AI trace of unverifiable provenance (Sections 2.1, 3.1.6 item 6). None of these caveats inverts a headline — the leakage-class hierarchy is measured device physics propagated to module scale, the density ratios survive their cell-area sensitivity bounds, and the endurance threshold moves but does not vanish under pessimistic leveling — but together they draw the boundary between what this book demonstrates and what remains to be demonstrated. That boundary is, by construction, the future-work agenda of Sections 4.1-4.2.

## Net effect

- §4's body shrinks by roughly a third; no numbers are lost that don't already live in §3 and Table 7.
- The Conclusion gains the one thing it lacked: a consolidated honest-scope statement (this also answers the critique's "validation is entirely internal" and "caveats scattered" findings in a single examiner-visible place).
- All cross-references stay valid (nothing in §4.1-4.3 refers back into the replaced paragraphs).

## Checks performed on the draft's numbers

1.7x/2.8x (MLC streaming slowdowns), 50.9/1.12/0.651/0.040 W, 47x, 29x PDP ratio (21,350.6/737.1), ±20% sweep with <4% PDP variation — all verified against the current §4 text they replace.
