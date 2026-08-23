# Book Fixes Tracker — driven by presentation prep

> **RECONCILED 2026-08-23.** The book-fix work items below were executed in a parallel
> session; canonical status and the append-only change log live in
> **`Review_Fixes_Tracker.md`** — treat that file as the single source of truth and log
> any further edits there. Note two renames that postdate this tracker's creation:
> the **density table is now Table 6 and the cross-technology summary is Table 7**
> (swapped to match body order), and **"Power Flatline" is renamed "Standby
> Convergence"**. This file is kept for the presentation workstream's context; statuses
> below are updated in place.

Source: 2026-08-22 super-critique (4 independent read-throughs: rigor/methodology,
overclaiming/data-honesty, defensibility/completeness, structure/clarity) plus the
decision to reframe the flagship claim before presenting it live.

Status legend: `[ ]` open · `[~]` in progress · `[x]` done · `[-]` decided not to fix

## Critical — must land before the talk is finalized (these are what the talk will say out loud)

- [x] **Gating-parity claim (Abstract, §3.3, summary table).** Done 2026-08-23,
      Lead-approved: reworded in all four sites as a *projection contingent on
      unmodeled gating* — Abstract ("bounding arithmetic on measured static power, not
      a simulated result"), §3.3 ("bounded by the arithmetic below, not demonstrated"),
      Table 7 role cell ("flagship; power parity contingent on future gating work" —
      now matches the deck's wording), Conclusion ("credible, bounded projection…
      contingent on idle-gating not yet simulated"). Book and talk now say the same thing.

- [x] **Streaming framing (Abstract).** Done: Abstract close now reads "for
      compute-bound workloads - and within a disclosed 1.9-2.1x of DDR5 under
      sustained streaming"; the 4.6x AI figure is additionally labeled a
      memory-latency ratio, not an application slowdown. (Qualified rather than
      dropped; the deck's completion-panel slide stays the sharper telling.)

- [x] **Worst-case-stacking in the DDR5 comparison.** Done: §3.1.2 now states both
      band ends are vendor *specification* currents, a typical-current module sits
      below the ceiling, and 11%-of-parity is the most favorable end of a disclosed
      range. (Note: the two assumptions cut in opposite directions — spec-max DDR5
      favors ReRAM, ungated ReRAM penalizes ReRAM — so "compound" was not quite right.)

## Important — strengthens defensibility, not fatal if deferred

- [x] **No sensitivity sweep on CellArea (20F² / 4F²).** Done: §3.3 (after the now-
      Table-6 bounded-claims paragraph) states the linear sensitivity with
      demonstrated endpoints — 1T1R spans ~0.04x (112F² [20]) to ~0.7x (6F² [33]);
      a 2x-area selector cell halves every 1S1R entry (22nm SLC → 0.96x parity,
      MLC retains 1.92x).

- [x] **Validation is entirely self-referential (§3.1.6).** Done: new "Validation
      Scope" bullet at the end of §2.2 — internal consistency vs hardware
      correlation stated plainly; "0.0% error" reframed as a pipeline-fidelity
      guarantee, not hardware accuracy.

- [~] **No related-work section anywhere in the book.** Proposal drafted, awaiting
      Lead sign-off: new §1.3, six candidate sources (ISCA'09 PCM trio, Xu HPCA'15
      crossbar ReRAM, Kültürsay ISPASS'13 STT-RAM, Izraelevitz Optane measurements)
      — see `Tier3_Prep_Proposals.md` (item T3-1). Still a required slide for the
      talk regardless.

- [x] **Trace fidelity caveat surfaces too late.** Done: the Abstract's 4.6x now
      carries the caveat inline ("memory-latency ratio under the cache-less trace
      capture of Section 2.1"). (Nuance: the caveat was already disclosed *before*
      results, in §2.1 and §2.4.1 — the genuinely-unqualified site was the Abstract.)

- [x] **Endurance hot-spot bound (Table 5).** Done: §3.1.4 closing now bounds it —
      a 2x hot-spot factor halves every figure; 128 GB SLC still clears the target
      (8.7 / 12.4 yr), 64 GB drops to the target's lower edge (4.3-6.2 yr).

## Structural / polish — no science risk, but visible to any careful reader

- [x] **List of Tables out of order / truncated.** Done: tables renumbered (density →
      Table 6, summary → Table 7, matching body order), list rebuilt with full
      captions, dead `GEN-BEGIN` generator markers removed (no generator script
      exists in the repo).
- [~] **§3.1.6 positioned after the results that depend on it.** Recommendation
      drafted (Tier3_Prep_Proposals.md, T3-2): do NOT move it — 35 in-body
      cross-references — add a one-paragraph audit summary at the top of §3.1 instead.
      Awaiting sign-off.
- [~] **Conclusion re-derives instead of synthesizing.** Compression approach
      proposed (T3-3): keep opening synthesis, collapse five recap paragraphs into
      one verdicts paragraph, add a consolidated honest-scope close. Draft-first;
      awaiting sign-off.
- [x] **Naming collision.** Done: the debunked §3.1.2 artifact is renamed "Standby
      Convergence" with an explicit in-text note that it is unrelated to the
      Flatline Paradox.
- [x] **20F²/6F² re-argued four times.** Done: Appendix A is canonical; §1.2, §3.3,
      §4.2 trimmed to one-line statements + cross-references.
- [x] **§1.2 skips the basic memristor mechanism.** Done: primer paragraph added at
      the top of §1.2 (filament physics, LRS/HRS, non-volatility, finite endurance).
- [x] **"intrinsically 3.3x less dense".** Done: "intrinsically" dropped.

## Explicitly not fixing (for now)

- [-] Appendix C repo link is a search-redirect URL rather than a direct GitHub link —
      cosmetic, low priority.

## What's genuinely strong (don't touch)

- §3.1.6's 14-item fidelity audit — exact-arithmetic validated, independently
  blind-re-verified. This is the book's real methodological asset.
- §3.1's opening signposting and the overall results arc
  (per-workload → scaling → global viability).
