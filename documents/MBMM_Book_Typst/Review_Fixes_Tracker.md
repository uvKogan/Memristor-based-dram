# Review Fixes Tracker — Project_Book.typ

Coordination file for the super-critique fix pass (critique triaged 2026-08-22).
**Multiple workers (AI sessions / humans) may edit the book in parallel. This file is the single source of truth for who changed what.**

## Ground rules for every worker

1. **Before editing**: read this file top to bottom. Check the Change Log for edits that may have moved your target text. Locate targets by **anchor string**, not line number — line numbers drift with every edit.
2. **Claim your item**: set its Status to `in-progress` and put your session/name in Owner *before* editing.
3. **After editing**: run the compile gate — `typst compile --font-path fonts Project_Book.typ /tmp/verify.pdf` must exit 0 — then set Status to `done` and **append a Change Log entry** (template at bottom).
4. **Sync obligations**: any reference added/removed → update `Reference_Guide.md` (count + entry) and check `Reading_Guide.md`. Any table renumbering → check every in-body "Table N" mention and the List of Tables.
5. Git commits are done by the Lead Researcher only (per repo CLAUDE.md). Note in your log entry whether your change is staged.

## Preconditions / current repo state

- **Staged, uncommitted** (as of tracker creation): `Project_Book.typ` + `Reference_Guide.md` carry the XBM additions (refs [34]/[35], Section 3.3 "three fronts" sentence). **Commit these before parallel work starts** so everyone edits from a clean, shared base.
- Current reference count: **35**. Current table count: 7 (Table 7 appears *before* Table 6 in the body — see T1-1).
- List of Tables (lines ~150–166) is machine-generated (`// GEN-BEGIN lot` … `// GEN-END lot`). The generator script has **not yet been located** — find it before hand-editing that block, or your fix may be overwritten on next regeneration.

---

## Work plan

Status values: `todo` / `in-progress` / `done` / `blocked` / `wont-do`

### Tier 1 — mechanical, low-risk

| ID | Item | Target / anchor | Status | Owner |
|----|------|----------------|--------|-------|
| T1-1 | Fix Table 6/7 out-of-order numbering (Table 7 body position precedes Table 6) and the truncated List of Tables captions ("(= 1.", "66."). Renumber tables to match body order OR reorder; update every in-body "Table 6"/"Table 7" mention. Locate the `GEN-BEGIN lot` generator first. | Anchors: `Table 7: Projected die-level density`, `Table 6: Cross-technology summary`, `GEN-BEGIN lot` | todo | — |
| T1-2 | Rename "Power Flatline" (the *debunked artifact*, §3.1.2) so it no longer collides with "Flatline Paradox" (the *real finding*, §3.2). Suggested: "leakage flatline artifact". Check all occurrences incl. Conclusion. | Anchor: `named “Power Flatline.”` | todo | — |
| T1-3 | Hedge Table 6's 1S1R SLC role cell: "flagship: one gating policy from DDR5 parity" → make explicit the policy is unexercised arithmetic (e.g. "one credible — but unexercised — gating policy from DDR5 parity"); optionally reinforce in the table footnote. | Anchor: `flagship: one gating policy from DDR5 parity` | todo | — |
| T1-4 | Qualify the Abstract's 4.6x AI-inference figure in claim (1) as a memory-latency ratio under the cache-less trace methodology (one clause, pointing at §2.1) — the power claims in the same Abstract already carry their caveats inline; latency should too. | Anchor: `trailing DDR5 by 4.6x` | todo | — |
| T1-5 | Retreat the closing claim "latency-competitive … for compute-bound and streaming workloads": against DDR5, streaming is the *weak* regime (1.9–2.1x slower; LBM ratio computed over a service-limited subset). Either drop "streaming" or qualify it (e.g. "compute-bound workloads, with a disclosed 1.9–2.1x streaming penalty"). | Anchor: `latency-competitive, density-superior DDR5 alternative` (Abstract close); check Conclusion for the same claim | todo | — |
| T1-6 | Add one-sentence endurance bound in §3.1.4: lifetime scales inversely with hot-spot concentration, so a 2x hot-spot factor halves every Table 5 number — which still clears the 5–10-yr target at 64–128 GB SLC. Closes the "named but never bounded" gap. | Anchor: `these lifetimes assume ideal uniform wear leveling; hot-spot` | todo | — |
| T1-7 | Fix stale count in `Reading_Guide.md`: says "All 32 references" — true count is 35. | File: `Reading_Guide.md`, anchor: `All 32 references` | todo | — |

### Tier 2 — bounded additions

| ID | Item | Target / anchor | Status | Owner |
|----|------|----------------|--------|-------|
| T2-1 | Add a short memristor primer paragraph at the top of §1.2 (what a memristor physically is/does — resistance as stored state, filament formation, nonvolatility) before the process/topology discussion. | Anchor: `== 1.2. ReRAM Fundamentals` | todo | — |
| T2-2 | Add a validation-scope paragraph to §2.2: parameters are real-world-anchored (vendor IDD datasheets, EMBER silicon multipliers) but all "0.0% error" checks verify pipeline self-consistency against NVSim anchors — no end-to-end result is validated against a measured chip/DIMM. State this plainly as scope, not weakness. | Anchor: `== 2.2. Validation & Protocol` | todo | — |
| T2-3 | Add a cell-area sensitivity paragraph to §3.3 near Table 7: density ratios scale linearly with assumed cell area; promote Appendix A's existing 112F² measured-chip counterpoint (`about 112F² at that node`) into an explicit best/worst-case density band. | Anchors: `Table 7 makes the third level concrete`, Appendix A `112F²` | todo | — |
| T2-4 | Consolidate the 20F²/4F²/6F² cell-area argument: full argument lives once (Appendix A), other sites (§1.2, §3.3, §4.2, Table 6 footnote) get one sentence + cross-reference instead of re-arguing. | Anchor: grep `20F` (currently ~8 hits across 5 sections) | todo | — |
| T2-5 | Acknowledge spec-vs-typical DDR5 current: all four "11% of parity" mentions carry the floor/ceiling band already, but both ends are vendor *spec* values — add one sentence (§3.1.2 or §3.3) noting a typical-current DDR5 module would sit below the ceiling, widening the gap. | Anchor: `within 11% of outright` | todo | — |

### Tier 3 — structural (each is its own task; get Lead Researcher sign-off on approach before starting)

| ID | Item | Notes | Status | Owner |
|----|------|-------|--------|-------|
| T3-1 | Add a Related Work section (situate vs prior NVM-main-memory system studies: PCM ISCA-era work, other NVMain/ReRAM evaluations). Requires sourcing + verifying new references (same workflow as the XBM patent: primary sources only). Updates Reference_Guide.md. | Biggest examiner-facing gap; no partial mitigation exists in the book | todo | — |
| T3-2 | §3.1.6 placement: either move the 14-item audit to an appendix with a one-paragraph inline summary in §3.1, or move it before the results it underwrites. Keep the audit content itself untouched — it is a strength. | ~230 lines; heavy cross-reference checking needed | todo | — |
| T3-3 | Rewrite Conclusion (§4) as synthesis rather than paragraph-for-paragraph replay of §3. | Subjective; draft for Lead Researcher review before replacing | todo | — |

### Explicitly NOT doing (critique findings triaged as overstated)

- Abstract gating caveat "doesn't travel" — it does; the Abstract discloses "unexercised / disabled in source" inline twice. Only Table 6's cell needed the hedge (T1-3).
- "Two worst-case assumptions stacked in ReRAM's favor" — the two assumptions cut in opposite directions, and the floor/ceiling band is disclosed at all four "11%" sites. Residue handled by T2-5.
- "Trace fidelity surfaces too late" — disclosed in §2.1 and §2.4.1, *before* results. Residue handled by T1-4.

---

## Change Log

Append entries newest-last. Template:

```
### YYYY-MM-DD — <item ID> — <owner>
- File(s): <paths>
- What changed: <1–3 sentences, with anchor strings for moved/edited text>
- Compile gate: pass/fail
- Staged: yes/no
```

### 2026-08-22 — (pre-tracker baseline) — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Reference_Guide.md`
- What changed: Added refs [34] (Intel XBM patent US 2026/0191095 A1) and [35] (TrendForce corroboration); Section 3.3 DRAM-roadmap paragraph expanded from "two fronts" to "three fronts" with a new XBM sentence after the `Notably, even that challenger's` sentence. Reference_Guide.md count bumped 33→35 with matching entries.
- Compile gate: pass
- Staged: yes (uncommitted)
