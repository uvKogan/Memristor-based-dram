# Reading Guide — MBMM Project Book

A short, practical guide for reading and self-reviewing `Project_Book.typ` (or the compiled PDF). This is not a summary of the content — it's a map of *how* to read it efficiently and *where* to slow down and check the numbers yourself.

Independent verification status as of 2026-08-22: Abstract/Conclusion claims, all of Section 3's tables (1-4 and the cross-technology summary — renumbered to Table 7 on 2026-08-23; the density-projection table is now Table 6), the figure set, and the reference numbering have all been cross-checked against the underlying data/CSVs and found consistent, with zero discrepancies. Details below on what to still sanity-check yourself and why.

---

## Suggested reading order

Don't read front-to-back on a first pass. Read in this order instead:

1. **Abstract** — this is the actual executive summary; every numbered claim (1)-(4) in it maps directly onto a section of the book. Read it twice: once for the story, once to note the four numbered claims so you can watch for them landing correctly later.
2. **Section 3.1.6** (the fidelity audit) — read this *before* the results sections it explains. It tells you which numbers in Sections 3.1.1-3.3 are trustworthy and why, and which two limitations (items 5 and 6) are permanent caveats rather than bugs. Reading results before this section means re-deriving context you'd otherwise get for free.
3. **Section 3.1.1 → 3.1.4** (Latency, Power, PDP, Endurance) in order — these build on each other; each one explicitly says which of the prior section's numbers it's reusing.
4. **Section 3.2 and 3.3** (Pareto frontiers, Hero graphs) — the "so what" sections; these synthesize 3.1 into a small number of headline verdicts.
5. **Conclusion** — should feel like a compressed replay of what you just read, not new information.
6. **Appendix A** — read last, as a reference appendix for "where did this parameter/multiplier come from," not as narrative.

Skip on a first pass: the Introduction/Background (1.x) and Methodology (2.x) sections if you already know the project — they're setup, not findings.

---

## Points to notice while reading

### Section 3.1.6 (the audit) — the single most important section
- It lists **14 audit items**; only **12 are repaired**, items **(5)** (idle-power gating disabled) and **(6)** (trace provenance) are permanent, disclosed limitations — not oversights. If a later section's number surprises you, check whether it's downstream of one of these two open items.
- Items (13) and (14) are the MLC read-latency correction story (first wrong at 1.917x, corrected to 1.5x). Everywhere else in the book that cites the MLC multipliers should say 1.5x/3.263x/1.1x/3.0x — if you ever see 1.917x or the old 3x/4x placeholders anywhere else in the book, that's a stale-data bug, flag it.
- Watch the language: "Found and fixed" vs. "Found and documented — still open" vs. "Found and partially fixed" (item 8) are meaningfully different claims. Don't skim past the qualifier.

### Section 3.1.1 (Latency) — the trickiest interpretive point in the book
- **LBM is not like the other 5 workloads.** GCC, STREAM, GPT-2, and both AlexNet phases run to full completion for every technology under the matched 250M-cycle window — so their latency averages compare identical populations. LBM is *service-limited*: slower technologies simply complete less of the trace (DDR5 100% down to PCM 3.9%), so its latency average only covers each configuration's completed prefix. If you're comparing LBM numbers across technologies, know you're comparing different amounts of completed work, not the same population under different speeds.
- The 4.6x AI-inference "DDR5 wins" number (GPT-2) is explicitly called out as a **memory-latency ratio, not a projected application slowdown** — the pipeline has no CPU/accelerator feedback loop. Don't over-read this number as "your LLM will be 4.6x slower."

### Table 1 — worth hand-verifying once
- The MLC rows are SLC rows times the four penalty multipliers (1.5x read latency, 3.263x write latency, 1.1x read energy, 3.0x write energy). Pick one row and multiply it yourself — it's fast, and it's the load-bearing calculation the rest of Section 3 inherits.

### Every table's footnote
- Each table states its power/gating assumption explicitly ("ReRAM worst-case ungated; DRAM/PCM standard idle"). This asymmetry is intentional and disclosed (it's audit item 5), but it means you should never directly compare a ReRAM power number to a DDR5 power number without remembering one is worst-case and the other is realistic-idle.

### References
- All 35 references are cited somewhere in the body (verified) and numbered sequentially. The EMBER papers — **[6]** (conference, gives read-energy figures) and **[31]** (journal follow-up, gives read-latency + write-side figures) — are the most load-bearing pair in the whole bibliography; see `Reference_Guide.md` for a one-paragraph summary of each reference if you want the "what is this and why is it here" without reading the papers.
- If you want a deeper, source-by-source walkthrough, `NotebookLM_Podcast_Prompt.md` in this same folder is a ready-to-paste prompt for generating an audio explainer from the references.

### Figures
- 27 figures total (numbered 1-27 including two that share unusual filenames — image23.png is Figure 26, image27.png is Figure 19). All are referenced and present; if you're cross-checking a printed/exported copy against the source repo, don't be alarmed that the figure number and the underlying filename number don't match — that's cosmetic, not an error.

---

## A 15-minute self-check, if you only have 15 minutes

1. Read the Abstract's four numbered claims.
2. Read Section 3.1.6's two-sentence intro paragraph (the "fourteen found, twelve fixed" framing) and skim the 14 item headers only (not the full text) — just note which two are "still open."
3. Pick one row of Table 1, multiply it by the four MLC multipliers yourself, and confirm it matches the MLC row.
4. Read the Conclusion and check it doesn't contradict anything you just read.

That's enough to catch the two failure modes this project has actually had before: an unsourced multiplier slipping in unnoticed, and a section going stale after a correction elsewhere in the book.
