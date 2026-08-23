# Book Fixes Tracker — driven by presentation prep

Source: 2026-08-22 super-critique (4 independent read-throughs: rigor/methodology,
overclaiming/data-honesty, defensibility/completeness, structure/clarity) plus the
decision to reframe the flagship claim before presenting it live.

Status legend: `[ ]` open · `[~]` in progress · `[x]` done · `[-]` decided not to fix

## Critical — must land before the talk is finalized (these are what the talk will say out loud)

- [ ] **Gating-parity claim (Abstract, §3.3, Table 6).** Currently stated as "1S1R sits
      one credible gating policy from DDR5 power parity." NVMain's power-down state
      machine is disabled in source — no gating policy has actually been simulated
      (§4.1 item 5). The 43%-idle break-even is hand arithmetic on one borrowed
      utilization statistic, not a modeled result.
      **Fix direction:** reword every instance (Abstract, §3.3, Table 6, Conclusion) to
      state this as a *projection contingent on unmodeled gating*, not a near-achieved
      result. The talk will present it this way regardless — the book should match.

- [ ] **Streaming framing (Abstract).** Headline picks PCM as the streaming
      comparandum instead of DDR5, while the real DDR5 comparison is unflattering
      (1.9–2.1x slower under LBM/STREAM), and the LBM latency ratio is computed over a
      completed-request subset that's much smaller for ReRAM (40%/28%) than DDR5
      (100%) — understating the true deficit.
      **Fix direction:** drop "streaming" from the abstract's viability claim, or add a
      completion-adjusted throughput number and let that govern the framing.

- [ ] **Worst-case-stacking in the DDR5 comparison.** DDR5 IDD = vendor spec-limit
      maxima (not typical); ReRAM = worst-case-ungated. Both unfavorable-to-DDR5
      choices compound into the "within 11% of parity" headline with no estimate of
      where a typical-current DDR5 module would land.
      **Fix direction:** add an explicit sentence bounding which direction (and roughly
      how much) the gap could move under typical-current DDR5 assumptions.

## Important — strengthens defensibility, not fatal if deferred

- [ ] **No sensitivity sweep on CellArea (20F² / 4F²).** Single most load-bearing
      geometric constant in the book (drives every density claim, Fig. 26, Table 7);
      never swept, despite Appendix A/[33] establishing it's architecture-dependent.
      **Fix direction:** add a bounded sensitivity range (e.g. 6F²–20F² per [33]) to at
      least the density/viability conclusions.

- [ ] **Validation is entirely self-referential (§3.1.6).** Every "0.0% error" claim
      checks NVMain against NVSim's own numbers, never against a real fabricated chip
      or measured DDR5 DIMM behavior.
      **Fix direction:** add one paragraph explicitly scoping validation as
      internal/toolchain consistency, not external ground-truth validation — don't let
      the strength of the internal audit imply more than it does.

- [ ] **No related-work section anywhere in the book.** No section situates this
      system-level NVSim→NVMain ReRAM evaluation against other published
      architecture-level ReRAM/NVM main-memory studies.
      **Fix direction:** add a short related-work subsection to §1 or §2; this is also
      a required slide for the talk regardless (advisor will ask "what's novel here?").

- [ ] **Trace fidelity caveat surfaces too late (§3.1.6 item 6).** gem5 traces have no
      cache hierarchy/warmup; GPT-2 trace provenance is unverified — yet the Abstract's
      "4.6x AI-inference deficit" is stated as unqualified fact three sections earlier.
      **Fix direction:** pull the caveat (or a compressed version of it) forward to
      wherever the number is first stated.

- [ ] **Endurance assumes an unimplemented wear-leveling controller (Table 5).**
      Hot-spot degradation named but never bounded.
      **Fix direction:** add a pessimistic-case bound, not just the idealized number.

## Structural / polish — no science risk, but visible to any careful reader

- [ ] **List of Tables (lines ~150–166) is out of order and has truncated captions**
      (Table 7 listed before Table 6; several entries cut off mid-sentence). First
      thing a reader sees after the Abstract.
- [ ] **§3.1.6 fidelity audit (~230 lines) is positioned after the results that depend
      on it**, despite being forward-referenced from as early as line 336. Consider
      moving earlier (end of §2) or to an appendix with a one-paragraph inline summary.
- [ ] **Conclusion re-derives the results section almost paragraph-for-paragraph**
      instead of synthesizing — should spend that space on what future work actually
      unlocks.
- [ ] **Naming collision:** "Power Flatline" (a debunked measurement bug, §3.1.2) vs.
      "Flatline Paradox" (a real finding, §3.2) — near-identical names for opposite
      things.
- [ ] **20F²/6F² cell-density discussion is fully re-argued four times** (§1.2, §3.3,
      Appendix A, §4.2) — collapse three of the four into one-sentence cross-references.
- [ ] **§1.2 skips the basic memristor mechanism** before jumping into 1T1R-vs-1S1R
      topology — a scaffolding gap for anyone less specialized than your advisor.
- [ ] Line ~1642: "intrinsically 3.3x less dense" sits awkwardly next to its own hedge
      ("under the planar-access-transistor assumption...") — drop "intrinsically."

## Explicitly not fixing (for now)

- [-] Appendix C repo link is a search-redirect URL rather than a direct GitHub link —
      cosmetic, low priority.

## What's genuinely strong (don't touch)

- §3.1.6's 14-item fidelity audit — exact-arithmetic validated, independently
  blind-re-verified. This is the book's real methodological asset.
- §3.1's opening signposting (lines 536–545) and the overall results arc
  (per-workload → scaling → global viability).
