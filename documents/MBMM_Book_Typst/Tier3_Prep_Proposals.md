# Tier 3 Prep Proposals — for Lead Researcher sign-off

Prepared 2026-08-23 (tracker items T3-1, T3-2, T3-3). **No book edits have been made for any Tier 3 item.** Approve, amend, or reject each proposal; implementation happens only after sign-off.

---

## T3-1: Related Work section — proposed placement, structure, and source list

**Placement**: new subsection **§1.3 "Related Work"** (after §1.2 ReRAM Fundamentals, before §2). Rationale: examiners look for it in the introduction; placing it after §1.2 lets it use the 1T1R/1S1R vocabulary just introduced. Alternative (rejected): distributing comparisons through §3 — harder for an examiner to find, and it can't answer "what's novel" in one place.

**Structure** (~4 paragraphs, ~1 page):

1. **NVM-as-main-memory system studies (the PCM generation).** The three concurrent ISCA 2009 papers that founded the field — all evaluating PCM, not ReRAM, against DDR-era DRAM:
   - B. C. Lee, E. Ipek, O. Mutlu, D. Burger, "Architecting Phase Change Memory as a Scalable DRAM Alternative," ISCA 2009.
   - M. K. Qureshi, V. Srinivasan, J. A. Rivers, "Scalable High Performance Main Memory System Using Phase-Change Memory Technology," ISCA 2009.
   - P. Zhou, B. Zhao, J. Yang, Y. Zhang, "A Durable and Energy Efficient Main Memory Using Phase Change Memory Technology," ISCA 2009.
2. **ReRAM/crossbar-specific main-memory architecture.** The closest prior work to this book:
   - C. Xu, D. Niu, N. Muralimanohar, R. Balasubramonian, T. Zhang, S. Yu, Y. Xie, "Overcoming the Challenges of Crossbar Resistive Memory Architectures," HPCA 2015. (Crossbar ReRAM as main memory; sneak-path/IR-drop-aware; the single most important comparison point.)
   - E. Kültürsay, M. Kandemir, A. Sivasubramaniam, O. Mutlu, "Evaluating STT-RAM as an Energy-Efficient Main Memory Alternative," ISPASS 2013. (The parallel study for a competing NVM.)
3. **Real-hardware NVM main memory.** The only shipped datapoint:
   - J. Izraelevitz et al., "Basic Performance Measurements of the Intel Optane DC Persistent Memory Module," arXiv:1903.05714, 2019. (Measured behavior of a real selector-based NVM DIMM; pairs with the Optane business-failure reference already in the bibliography.)
4. **Positioning paragraph.** What this book adds over all of the above: (a) DDR5-era baselines rather than DDR2/DDR3-era; (b) a device-anchored 22nm characterization feeding a cycle-accurate system model, rather than abstract latency multipliers; (c) an explicit 1T1R-vs-1S1R topology comparison at matched process; (d) the toolchain fidelity audit (no prior study validates its NVSim→NVMain wiring); (e) endurance projected from measured per-subarray write counts rather than analytic write rates.

**Sourcing workflow** (same standard as the XBM patent): each candidate above is from memory and must be verified (exact title, venue, year, DOI) via web search before entering the bibliography as refs [36]–[41], with matching `Reference_Guide.md` entries. Estimated ~6 new references.

**Risk note**: adding §1.3 renumbers nothing (subsections are per-chapter), but the "skip 1.x on a first pass" advice in `Reading_Guide.md` should get an exception for §1.3.

---

## T3-2: §3.1.6 placement — recommendation: DO NOT MOVE; add a summary box instead

Options considered:

- **Option A (recommended): keep §3.1.6 in place; add a one-paragraph audit summary near the top of §3.1** (immediately after the existing signposting): "fourteen failure modes found, twelve repaired and re-simulated, two disclosed as permanent limitations (idle gating disabled, trace provenance); full audit in §3.1.6" — so a linear reader hits the trust framework *before* the numbers, without the 230-line forensic detour.
  - Why: there are **35 in-body cross-references to "3.1.6"** (table captions, item-number citations like "Section 3.1.6, item 11"). Moving the section to an appendix would require retargeting all of them and re-verifying every one — high mechanical risk, zero content gain. The critique's real complaint (trust framework arrives after the results) is fully solved by the summary paragraph.
- **Option B (rejected): move the audit to an appendix**, leave a stub. Retarget 35 references; pagination churn; results sections lose adjacency to the audit items they cite.
- **Option C (rejected): move the audit before §3.1.1.** Buries the results under 230 lines of toolchain forensics — the exact opposite of what a reader/examiner wants first.

If Option A is approved, the edit is one paragraph (~6 lines) and touches nothing else.

---

## T3-3: Conclusion rewrite — proposed approach

Current §4 opens with a strong synthesis paragraph (the "two things delivered" framing) but then re-derives §3.1.1→3.2 nearly section-by-section across five paragraphs (~60 lines). Proposal:

- **Keep**: the opening synthesis paragraph (already does the job), the deployment-recommendation sentence, the open-source contribution sentence.
- **Compress**: the five per-section recap paragraphs (3.1.1 latency, 3.1.2 power, 3.1.3 PDP, 3.1.4 endurance, 3.1.5 robustness, 3.2 Pareto) into **one paragraph of verdicts** (one sentence each) — the numbers already live in §3 and Table 7; the Conclusion should state what each result *means*, not restate it.
- **Add**: a closing paragraph the book currently lacks — the honest scope statement in one place: simulation-only validation (§2.2 scope bullet), unexercised gating, ideal wear leveling, cache-less traces — followed by the argument for why the headline survives these caveats. This converts the critique's "limitations scattered" observation into a strength.

Draft will be produced for side-by-side review before anything is replaced. Estimated net change: §4 shrinks by roughly a third.

---

## Sign-off checklist

- [ ] T3-1: approve §1.3 placement + source list (or amend)
- [ ] T3-2: approve Option A (summary box, no move)
- [ ] T3-3: approve compression approach (draft-first, side-by-side)
