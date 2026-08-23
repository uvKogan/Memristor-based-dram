# Review Fixes Tracker — Project_Book.typ

Coordination file for the super-critique fix pass (critique triaged 2026-08-22).
**Multiple workers (AI sessions / humans) may edit the book in parallel. This file is the single source of truth for who changed what.**

## ⚠️ NOTICES FOR PARALLEL WORKERS (read before citing the book)

Applied 2026-08-23 — these change names/numbers you may be quoting (relevant to the presentation-planning session):

1. **Tables 6 and 7 SWAPPED numbers.** The density-projection table (16nm/12nm/deck-stacking) is now **Table 6**; the cross-technology summary table is now **Table 7**. Body order and List of Tables now match.
2. **"Power Flatline" no longer exists.** The debunked §3.1.2 artifact is renamed **"Standby Convergence"**. "Flatline Paradox" (the real §3.2 multi-rank finding) is unchanged — they are different things.
3. The Abstract's closing claim now scopes streaming honestly: "…for compute-bound workloads - and within a disclosed 1.9-2.1x of DDR5 under sustained streaming".
4. The `GEN-BEGIN lot` markers are gone — no generator script exists anywhere in the repo (verified); the List of Tables is now hand-maintained.

## Ground rules for every worker

1. **Before editing**: read this file top to bottom. Locate targets by **anchor string**, not line number — line numbers drift with every edit.
2. **Claim your item**: set its Status to `in-progress` and put your session/name in Owner *before* editing.
3. **After editing**: run the compile gate — `typst compile --font-path fonts Project_Book.typ /tmp/verify.pdf` must exit 0 — then set Status to `done` and **append a Change Log entry** (template at bottom).
4. **Sync obligations**: any reference added/removed → update `Reference_Guide.md` (count + entry) and check `Reading_Guide.md`. Any table renumbering → check every in-body "Table N" mention and the List of Tables.
5. Git commits are done by the Lead Researcher only (per repo CLAUDE.md). Note in your log entry whether your change is staged.

## Repo state

- XBM additions (refs [34]/[35]) committed and pushed 2026-08-22. Current reference count: **35**.
- Tier 1 + Tier 2 edits below are complete, compile-verified, **not yet committed** as of the last log entry.

---

## Work plan

Status values: `todo` / `in-progress` / `done` / `blocked` / `wont-do` / `prep-done`

### Tier 1 — mechanical, low-risk

| ID | Item | Status | Owner |
|----|------|--------|-------|
| T1-1 | Table 6/7 renumbering (density table → Table 6, summary → Table 7; all 5 in-body mentions updated) + List of Tables rebuilt with full untruncated captions, GEN markers removed | done | Claude f2ad0d1b |
| T1-2 | "Power Flatline" renamed "Standby Convergence" (intro at §3.1.2 anchor `a convergence this project's earlier analysis`, plus the §4 recap `technology-blind "Standby Convergence" artifact`); collision with "Flatline Paradox" resolved and explicitly disclaimed in-text | done | Claude f2ad0d1b |
| T1-3 | Table 7 (summary) flagship cell hedged: "one credible - but unexercised - gating policy from DDR5 parity" | done | Claude f2ad0d1b |
| T1-4 | Abstract 4.6x now qualified: "(a memory-latency ratio under the cache-less trace capture of Section 2.1, not a projected application slowdown)" | done | Claude f2ad0d1b |
| T1-5 | Abstract closing claim retreats to compute-bound with disclosed 1.9-2.1x streaming penalty | done | Claude f2ad0d1b |
| T1-6 | Endurance hot-spot bound added at end of §3.1.4 (2x hot-spot factor halves Table 5 figures: 128 GB SLC still clears target at 8.7 / 12.4 yr; 64 GB drops to 4.3-6.2 yr, the target's lower edge) | done | Claude f2ad0d1b |
| T1-7 | `Reading_Guide.md`: reference count fixed 32→35; table-verification note updated for the 6/7 renumbering | done | Claude f2ad0d1b |

### Tier 2 — bounded additions

| ID | Item | Status | Owner |
|----|------|--------|-------|
| T2-1 | Memristor primer paragraph added at top of §1.2 (filament physics, LRS/HRS, non-volatility, finite endurance; cites [14], [5]) | done | Claude f2ad0d1b |
| T2-2 | "Validation Scope" bullet added at end of §2.2: internal consistency vs hardware correlation stated plainly; "0.0% error" reframed as pipeline-fidelity, not hardware-accuracy, guarantee | done | Claude f2ad0d1b |
| T2-3 | Cell-area sensitivity added in §3.3 after the Table 6 bounded-claims paragraph: 1T1R spans ~0.04x (112F² [20]) to ~0.7x (6F² [33]); 2x-area selector cell halves 1S1R entries (SLC → 0.96x parity, MLC retains 1.92x) | done | Claude f2ad0d1b |
| T2-4 | 20F² argument consolidated: Appendix A canonical; §1.2, §3.3, §4.2 trimmed to one-line statements + Appendix A cross-references | done | Claude f2ad0d1b |
| T2-5 | Spec-vs-typical DDR5 sentence added in §3.1.2 after the 65-78x comparison: both band ends are vendor spec currents; 11%-of-parity is the most favorable end of a disclosed range | done | Claude f2ad0d1b |

### Tier 3 — structural (proposals drafted, NO book edits made; see `Tier3_Prep_Proposals.md`)

| ID | Item | Status | Owner |
|----|------|--------|-------|
| T3-1 | Related Work section: proposed as new §1.3; 6 candidate sources listed (ISCA'09 PCM trio, Xu HPCA'15 crossbar ReRAM, Kültürsay ISPASS'13 STT-RAM, Izraelevitz Optane measurements); each requires web verification before citing | prep-done (awaiting sign-off) | Claude f2ad0d1b |
| T3-2 | §3.1.6 placement: recommendation is DO NOT MOVE (35 in-body cross-references); add a one-paragraph audit summary at top of §3.1 instead | prep-done (awaiting sign-off) | Claude f2ad0d1b |
| T3-3 | Conclusion rewrite: keep opening synthesis, compress five per-section recaps into one verdicts paragraph, add a consolidated honest-scope closing paragraph; draft-first, side-by-side review | prep-done (awaiting sign-off) | Claude f2ad0d1b |

### Explicitly NOT doing (critique findings triaged as overstated)

- Abstract gating caveat "doesn't travel" — it does; the Abstract discloses "unexercised / disabled in source" inline twice. Only the summary table's cell needed the hedge (T1-3).
- "Two worst-case assumptions stacked in ReRAM's favor" — the two assumptions cut in opposite directions, and the floor/ceiling band is disclosed at all four "11%" sites. Residue handled by T2-5.
- "Trace fidelity surfaces too late" — disclosed in §2.1 and §2.4.1, *before* results. Residue handled by T1-4.

---

## Change Log

Append entries newest-last. Template:

```
### YYYY-MM-DD — <item ID> — <owner>
- File(s): <paths>
- What changed: <1-3 sentences, with anchor strings for moved/edited text>
- Compile gate: pass/fail
- Staged: yes/no
```

### 2026-08-22 — (pre-tracker baseline) — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Reference_Guide.md`
- What changed: Added refs [34] (Intel XBM patent US 2026/0191095 A1) and [35] (TrendForce corroboration); Section 3.3 DRAM-roadmap paragraph expanded to "three fronts". Reference_Guide.md count bumped 33→35.
- Compile gate: pass
- Staged: committed & pushed 2026-08-22

### 2026-08-23 — T1-1..T1-7, T2-1..T2-5 — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Reading_Guide.md`
- What changed: All Tier 1 + Tier 2 items as described in the tables above. Highest-impact for other workers: Table 6/7 number swap, "Power Flatline"→"Standby Convergence" rename, Abstract streaming/4.6x qualifiers (see NOTICES at top). New anchors: primer starts `Before the engineering choices, the device itself`; validation bullet starts `#strong[Validation Scope]`; sensitivity passage starts `Every ratio in the table is also linear in the assumed cell area`; endurance bound starts `That proportionality also bounds the exposure`; spec-vs-typical sentence starts `One honest bound on that comparison`.
- Compile gate: pass (verified after final .typ edit)
- Staged: no (pending Lead Researcher review)

### 2026-08-23 — T3-1/T3-2/T3-3 prep — Claude session f2ad0d1b
- File(s): `Tier3_Prep_Proposals.md` (new)
- What changed: Proposals + sign-off checklist for the three structural items. No book edits.
- Compile gate: n/a
- Staged: no
