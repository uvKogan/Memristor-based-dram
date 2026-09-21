# Reading Guide - MBMM Project Book

A short, practical guide for reading and self-reviewing `Project_Book.typ` (or the compiled PDF). This is not a summary of the content - it's a map of *how* to read it efficiently and *where* to slow down and check the numbers yourself.

Verification status, and read the scope of it carefully. An independent verification pass on **2026-08-22** cross-checked the Abstract/Conclusion claims, Section 3's tables as they then stood (1-4 plus the cross-technology summary, renumbered to Table 7 on 2026-08-23; the density-projection table is now Table 6), the figure set and the reference numbering against the underlying data and CSVs, and found zero discrepancies. **That pass covered references [1]-[35] and the pre-revision dataset only.** It did not see [36]-[46], added between 2026-09-01 and 2026-09-13, nor [47]-[54], added 2026-09-20; and it did not see the 2026-09 revision, which replaced every table in Section 3, every figure except Figure 19, and the whole of Sections 3.2 and 3.1.4. The 2026-09 revision carried its own checks instead: a 163-number independent re-derivation of the corrected tables against `results/rev2026-09_primary_csv/` (part A, 2026-09-20), and a figure-by-figure check of each regenerated chart against the table beside it (part B, 2026-09-20). Appendix D of the book is the authoritative record of what moved. Details below on what to still sanity-check yourself and why.

---

## Suggested reading order

Don't read front-to-back on a first pass. Read in this order instead:

1. **Abstract** - this is the actual executive summary; every numbered claim (1)-(4) in it maps directly onto a section of the book. Read it twice: once for the story, once to note the four numbered claims so you can watch for them landing correctly later.
2. **Section 3.1.6** (the fidelity audit) - read this *before* the results sections it explains. It tells you which numbers in Sections 3.1.1-3.3 are trustworthy and why, and which limitation is a permanent caveat rather than a bug (as of the 2026-09 revision that is one item, not the two the August version listed; see the audit bullet below). Reading results before this section means re-deriving context you'd otherwise get for free.
3. **Section 3.1.1 → 3.1.4** (Latency, Power, PDP, Endurance) in order - these build on each other; each one explicitly says which of the prior section's numbers it's reusing.
4. **Section 3.2 and 3.3** (Pareto frontiers, Hero graphs) - the "so what" sections; these synthesize 3.1 into a small number of headline verdicts.
5. **Conclusion** - should feel like a compressed replay of what you just read, not new information.
6. **Appendix A** - read last, as a reference appendix for "where did this parameter/multiplier come from," not as narrative.

Skip on a first pass: the Introduction/Background (1.x) and Methodology (2.x) sections if you already know the project - they're setup, not findings. Exception: **§1.3 Related Work** (added 2026-08-23) is worth reading even if you know the project - it's the "what's novel here" answer an examiner will ask for.

---

## Points to notice while reading

### Section 3.1.6 (the audit) - the single most important section
- It lists **14 audit items**, of which **13 are repaired** as of the 2026-09 revision. Items (5) (idle-power gating) and (6) (trace provenance) were the two open ones in the August version and both have since been closed: gating is restored for every technology, with ReRAM's power-down energy an explicit no-savings placeholder, and every gem5 trace has been regenerated with a provenance sidecar. The one item that remains a disclosed permanent limitation is that one AI trace cannot be attributed to a preserved generator configuration.
- Items (13) and (14) are the MLC read-latency correction story (first wrong at 1.917x, corrected to 1.5x). Everywhere else in the book that cites the MLC multipliers should say 1.5x/3.263x/1.1x/3.0x - if you ever see 1.917x or the old 3x/4x placeholders anywhere else in the book, that's a stale-data bug, flag it.
- Watch the language: "Found and fixed" vs. "Found and documented - still open" vs. "Found and partially fixed" (item 8) are meaningfully different claims. Don't skim past the qualifier.

### Section 3.1.1 (Latency) - the trickiest interpretive point in the book
- **This bullet described the pre-revision dataset and is superseded.** On the regenerated traces and the matched 250 ms window, all four ReRAM tracks and DDR5 complete 100% of every one of the six workloads, LBM included. What is now service-limited is the *legacy PCM baseline* (50.2% of LBM, 46.1% of STREAM) and the *two published-silicon configurations* (18.2% and 1.0% of LBM), and only those rows' latency averages cover a completed prefix rather than the whole population. Table 2's note marks them.
- The AI-inference deficit the August version reported is **withdrawn**: on the corrected read path and the regenerated AI traces, ReRAM is faster than DDR5 under GPT-2 IFMAP (143.3 ns and 130.1 ns against 222.1 ns), not slower. What the AI traces do show is a queueing result rather than a device result, and the caveat that survives is the same one: every such figure is a memory-latency ratio, not a projected application slowdown, because the pipeline has no CPU or accelerator feedback loop.

### Table 1 - worth hand-verifying once
- The MLC rows are SLC rows times the four penalty multipliers (1.5x read latency, 3.263x write latency, 1.1x read energy, 3.0x write energy). Pick one row and multiply it yourself - it's fast, and it's the load-bearing calculation the rest of Section 3 inherits.

### Every table's footnote
- Each power/PDP table states its gating assumption explicitly. Since the 2026-09-05 idle-gating restoration (audit item 5), the asymmetry is: DDR5 realizes real, datasheet-backed power-down savings; ReRAM's power-down mechanism runs but its energy is a no-savings placeholder; PCM shows no power-down activity. So never directly compare a ReRAM power number to a DDR5 power number without remembering that only DDR5's carries a gating credit.

### References
- All 54 references are cited somewhere in the body and numbered sequentially. [47]-[54] were added 2026-09-20 for the September revision: [47] (Chen, IEEE TED 2020) is the new endurance-rating basis replacing [14]; [48] (Liu, JSSC 2014) and [49] (Zahurak, IEDM 2014) are the fabricated-part anchors behind both the 2048x2048 organization and the published-silicon sensitivity configurations; [50] (Chou, VLSI 2020) is the 22nm array-qualified endurance floor; [51] (Zhou, Kim and Lu, IEEE TED 2014) is the read model behind the analytic selector layer; [52] (Qureshi, MICRO 2009) is Start-Gap; [53] (Yang, FAST 2020) and [54] (Intel PMem 200 brief) are the Optane reference points. [45] (Chen et al., IEEE TED 2012) and [46] (Hellenbrand et al., MRS Communications 2024) were added 2026-09-13 for the 10^7-vs-10^9 endurance reconciliation in §3.1.4. [42] (Kau et al., IEDM 2009 - Optane's 1S1R architecture) and [43]/[44] (ITRS 2011 and Auth et al., VLSI 2012 - transistor subthreshold leakage at 22nm) were added 2026-09-05. Note that [43] and [44] were originally added to corroborate a transistor-versus-selector leakage separation that the September revision withdrew: NVSim assigns memristor cells no leakage at all and charges chip leakage entirely to peripheral circuitry, so that separation was an artifact of two different array organizations, and no leakage ratio in the book rests on [43] or [44]. They remain cited in Appendix A, under "Array Organization (and the withdrawal of the leakage-gap figure)", as correct external statements about transistor leakage that NVSim never used, and the physical question they speak to is recorded there as open. [41] (Choi et al., ISSCC 2012) was added 2026-09-01 - the actual source of the PCM baseline's inherited timing/energy numbers, distinct from [11] (Lee et al.), which is only the baseline's architectural-framing citation. The EMBER papers - **[6]** (conference, gives read-energy figures) and **[31]** (journal follow-up, gives read-latency + write-side figures) - are the most load-bearing pair in the whole bibliography; see `Reference_Guide.md` for a one-paragraph summary of each reference if you want the "what is this and why is it here" without reading the papers.
- If you want a deeper, source-by-source walkthrough, `NotebookLM_Podcast_Prompt.md` in this same folder is a ready-to-paste prompt for generating an audio explainer from the references.

### Figures
- NOTE (2026-09-20): the figure files in `media/` have been regenerated from the revision's primary dataset (`results/book_figures_rev2026-09/`) and each one now agrees with the table beside it. The single exception is **Figure 19** (the ReadVoltage sweep), which is retained from the pre-revision dataset because that sweep was not re-run at the matched organization; its caption and Section 3.1.5 both say so. Every bar chart plots the six primary configurations only: the two published-silicon rows and the 64 B DDR5 cross-check are deliberately kept out of the figures and live in Table 2 and Section 2.3. The Pareto figures plot all four architectures (1, 8, 16 and 64 chips); the leftmost, lowest-power marker of each trajectory is the non-physical one-chip decode, which the captions flag and which enters no conclusion. NOTE (2026-09-21): 25 of the 27 figure files were regenerated again after the DDR5 background-power and JEDEC-timing corrections of Appendix A; only Figure 19 (retained, as above) and Figure 26 (die density, which carries no DDR5 power or timing term) are unchanged.
- 27 figures total (numbered 1-27 including two that share unusual filenames - image23.png is Figure 26, image27.png is Figure 19). All are referenced and present; if you're cross-checking a printed/exported copy against the source repo, don't be alarmed that the figure number and the underlying filename number don't match - that's cosmetic, not an error.

---

## A 15-minute self-check, if you only have 15 minutes

1. Read the Abstract's four numbered claims.
2. Read Section 3.1.6's two-sentence intro paragraph (the "fourteen found, thirteen fixed" framing as of the 2026-09 revision) and skim the 14 item headers only (not the full text), just to note which one is still open.
3. Pick one row of Table 1, multiply it by the four MLC multipliers yourself, and confirm it matches the MLC row.
4. Read the Conclusion and check it doesn't contradict anything you just read.

That's enough to catch the two failure modes this project has actually had before: an unsourced multiplier slipping in unnoticed, and a section going stale after a correction elsewhere in the book.
