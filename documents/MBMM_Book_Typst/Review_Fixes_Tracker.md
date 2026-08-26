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
- Tier 1 + Tier 2 committed as `aa43746`; presentation files (parallel session) committed as `0227ea4`.
- Reconciliation batch (T1-8, T1-9, tracker merge, deck/outline stale-note fixes) is complete and compile-verified — see last change-log entry for commit status.
- `Presentation_Fixes_Tracker.md` (parallel session's tracker) is reconciled into this file; THIS file is the single source of truth for book-fix status.

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
| T1-8 | Gating-parity claim reworded as "projection contingent on unmodeled gating" in all four sites (Abstract, §3.3, Table 7 role cell, Conclusion) to match the talk's framing — Lead-approved 2026-08-23; originated in `Presentation_Fixes_Tracker.md` | done | Claude f2ad0d1b |
| T1-9 | Dropped "intrinsically" from "3.3x less dense" in §3.3 (sat awkwardly against its own planar-assumption hedge) — originated in `Presentation_Fixes_Tracker.md` | done | Claude f2ad0d1b |

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
| T3-1 | Related Work: new §1.3 added with all sources web-verified (titles/venues/pages/DOIs). New refs [36]-[40] (ISCA'09 PCM trio, Xu HPCA'15, Kültürsay ISPASS'13); Izraelevitz was ALREADY ref [32] and Optane-exit [23] — reused, no duplicates. Reference count now **40**; `Reference_Guide.md` + `Reading_Guide.md` synced | done | Claude f2ad0d1b |
| T3-2 | §3.1.6 placement: audit-summary paragraph added at top of §3.1 ("fourteen found, twelve repaired, two permanent"); section itself NOT moved (35 in-body cross-references preserved) | done | Claude f2ad0d1b |
| T3-3 | Conclusion rewrite APPLIED: six recap paragraphs replaced with verdicts paragraph + consolidated honest-scope paragraph, plus the Lead's two citation additions (§3.3 cell-area passage, §3.1.4 hot-spot bound). Approved via `Lead_Decisions_and_Handoff.md` 2026-08-23 | done | Claude f2ad0d1b |

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
- Staged: committed (`aa43746`)

### 2026-08-23 — T1-8, T1-9 + parallel-session reconciliation — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Project_Book.pdf`, `Presentation_Fixes_Tracker.md`, `Presentation_Outline.md`, `presentation_deck.html`
- What changed: Gating-parity claim reworded as projection-contingent at all four sites (new anchors: Abstract `Power parity is therefore`, §3.3 `Power parity for 1S1R SLC is therefore a projection`, Table 7 cell `flagship; power parity contingent on future gating work`, Conclusion `credible, bounded projection to DDR5 power parity`); "intrinsically" dropped in §3.3. Parallel session's tracker reconciled: statuses flipped to done/in-progress with pointers here, renumbering + Standby Convergence notices added at top. Deck slide-16 speaker note and outline updated — they claimed the book still said "competitive for streaming"; it no longer does.
- Compile gate: pass
- Staged: committed (`3331683`)

### 2026-08-23 — T3-1, T3-2 executed; T3-3 drafted — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Project_Book.pdf`, `Reference_Guide.md`, `Reading_Guide.md`, `Conclusion_Rewrite_Draft.md` (new)
- What changed: New §1.3 Related Work (anchor: `== 1.3. Related Work`) citing new refs [36]-[40] plus existing [23]/[32]; five verified bibliography entries inserted after [35]; reference count 35→40. Audit-summary paragraph added at top of §3.1 (anchor: `One framing note before the numbers`). Conclusion replacement text drafted only — NOT applied. ToC updates automatically (typst `#outline()`).
- Compile gate: pass
- Staged: yes (uncommitted)

### 2026-08-23 — T3-3 applied — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Project_Book.pdf`, `Conclusion_Rewrite_Draft.md`, this file
- What changed: §4's six per-section recap paragraphs (old anchors: `Latency analysis (3.1.1) revealed` through `convert added ranks into latency gains.`) replaced by two paragraphs (new anchors: `Each results axis resolves to a one-line verdict.` and `The scope of these claims is bounded by four disclosed limitations`), per `Conclusion_Rewrite_Draft.md` with the Lead's two citation additions from `Lead_Decisions_and_Handoff.md`. Opening synthesis paragraph and §4.1-4.3 untouched. Note for the handoff file: its T3-1 spec assumed refs [36]-[41]; actual is [36]-[40] because Izraelevitz was already ref [32] (and Optane-exit [23]) — no duplicates were added. Its T3-2 question (options A-D) is still open with the Lead; Option A is what's currently implemented.
- Compile gate: pass
- Staged: yes (uncommitted)

### 2026-08-23 — pre-review leftover sweep — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Project_Book.pdf`, `Presentation_Fixes_Tracker.md`
- What changed: Appendix C repo link target fixed — was a Google-search redirect carrying a leaked `authuser=3` parameter; now links `https://github.com/uvKogan/MBMM` directly (display text unchanged; anchor: `#link("https://github.com/uvKogan/MBMM")`). This closes the last deferred `[-]` item. `Presentation_Fixes_Tracker.md`'s three stale `[~]` entries (related work, §3.1.6, Conclusion) flipped to `[x]` with final outcomes — all book-fix work is now complete in both trackers.
- Compile gate: pass
- Staged: yes (uncommitted)

### 2026-08-23 — review-process docs archived — Claude session f2ad0d1b
- File(s): `README.md` (this folder), `archive/documents/book_review_pass_2026-08/` (new)
- What changed: With every item closed, the finished process docs were `git mv`'d out of the book folder: `Tier3_Prep_Proposals.md`, `Conclusion_Rewrite_Draft.md`, `Lead_Decisions_and_Handoff.md`, `TYPST_QA_REPORT.md`, `qa_screenshots/` → `archive/documents/book_review_pass_2026-08/`. Any mention of those filenames in earlier log entries above now resolves to that archive path. Both trackers stay in place until the talk is delivered (they are the parallel-session coordination surface). The folder `README.md` was rewritten — it still claimed docx parity and refs [1]-[30], both false since this fix pass began.
- Compile gate: n/a (no book edit)
- Staged: yes (uncommitted)

### 2026-08-26 — review finding: "six benchmarks" → "six workloads" — Claude session f2ad0d1b
- File(s): `Project_Book.typ`, `Project_Book.pdf`
- What changed: The evaluated set is five benchmark programs (GCC, LBM, STREAM, GPT-2, AlexNet) yielding six workload traces (AlexNet split into IFMAP/OFMAP), and the book already said "workloads" at its other count sites (§3.1.1, §2.4, §3.1.3). Fixed the three inconsistent "benchmarks" sites: Abstract now reads "across six workloads - drawn from five benchmarks, with AlexNet split into read-dominant and write-dominant phases"; Conclusion and Appendix C now say "6 workloads". Found by the Lead during the review read.
- Compile gate: pass
- Staged: yes (uncommitted)
