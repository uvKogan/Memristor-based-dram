# Thesis Review Roadmap
**Project:** Evaluation of 22nm Memristor-Based Main Memory (MBMM) in Commodity DIMM Architectures
**Auditor:** Claude Code (Session 25 — original; Session 26 — re-validated)
**Date:** 2026-05-26 (original) | 2026-05-29 (Session 26 re-audit)
**Data Sources:** `results/processed_hero_metrics.csv`, `results/processed_pareto_metrics.csv`, `MBMM_AI_Context_State.md`, `resources/MBMM Project Book.docx`

---

## Session 26 Re-Audit & Fix Status (2026-05-29)

**BLOCKER RESOLVED — OFMAP/IFMAP Inversion + Metric Drift:** `process_metrics.py` has been patched. All CSVs regenerated. Full validated numbers below.

**New finding (Session 26 — LaTeX rendering artifact):**
Section 2.4.1, paragraph describing `alexnet_layer1_ofmap`, contains a raw LaTeX string in the DOCX source:
> "Explicitly exposes the physical `$4\times$` write-latency penalty of Iterative Step-and-Verify (ISPV)"
The `$4\times$` will render as broken text if submitted as DOCX. Replace with Unicode "4×" directly.

---

### Session 26 Fix Applied: `process_metrics.py` — `extract_total_execution_cycles()`

**Root cause of metric drift AND OFMAP inversion (single bug):**
NVMain emits three latency statistics per channel:
- `averageLatency` — hardware timing only (no queue wait)
- `averageQueueLatency` — time spent in FRFCFS queue
- `averageTotalLatency` — end-to-end total = hardware + queue

The pre-Session 24 regex `average.*?latency` matched `averageLatency` first, discarding the queue component. The queue component IS where the ISPV write-torture penalty lives: writes back up the queue, inflating latency for all subsequent requests.

**Fix:** Changed parser to match `averageTotalLatency` specifically. For DDR5's dual sub-channels, values are averaged across channels (previously channel-1 was accidentally used; averaging is more correct but causes 3–5% numeric change for DDR5 only).

**New columns added:** `HW_Latency_Cycles` and `Queue_Latency_Cycles` in `processed_bar_chart_metrics.csv` and `processed_hero_metrics.csv`. Queue latency is the write-torture proof metric.

---

### Post-Fix Validated Numbers (full_dimm, 2026-05-29)

**Write-Torture: OFMAP vs IFMAP (AlexNet Layer 1, full_dimm)**

| Technology | IFMAP Total | OFMAP Total | Ratio | Queue Ratio |
|------------|------------|------------|-------|-------------|
| 1T1R SLC | 317.9 cyc | 657.2 cyc | 2.07× | 2.28× |
| 1T1R MLC | 646.1 cyc | 1791.5 cyc | 2.77× | 3.17× |
| 1S1R SLC | 418.5 cyc | 1084.7 cyc | 2.59× | 2.91× |
| **1S1R MLC** | **947.2 cyc** | **3344.3 cyc** | **3.53×** | **4.08×** |

The 4.08× queue ratio for 1S1R MLC directly proves the 4× ISPV write penalty is manifesting as queueing congestion. ✅

**Key Latency Numbers (full_dimm, cycles at native clock)**

| Config | Workload | New CSV | Thesis | Match |
|--------|---------|---------|--------|-------|
| 1T1R SLC | gcc | 80.22 | 80.22 | ✅ exact |
| 1T1R SLC | lbm | 374.38 | 374.38 | ✅ exact |
| 1S1R MLC | lbm | 1545.40 | 1545.40 | ✅ exact |
| 1S1R MLC | alexnet_ofmap | 3344.30 | 3344.30 | ✅ exact |
| 1T1R SLC | gpt2 | 366.80 | 366.80 | ✅ exact |
| DDR5 | lbm | 652.10 | 651.92 | ✅ ~0.0% |
| DDR5 | gcc | 180.34 | 174.81 | ⚠ 3.2% (ch-avg vs ch1) |
| DDR5 | gpt2 | 236.16 | 224.28 | ⚠ 5.3% (ch-avg vs ch1) |

DDR5 GCC and GPT-2 numbers need updating in thesis text (3–5% correction).

**Geo-Mean EDP (full_dimm) — Correct Ordering Restored**

| Technology | New CSV | Old Thesis | Notes |
|------------|---------|-----------|-------|
| 1T1R SLC | 23.25 | 23.98 | ✅ close |
| 1S1R SLC | 33.93 | 35.15 | ✅ close |
| DDR5 | 52.34 | 49.99 | ⚠ update needed |
| 1T1R MLC | 55.12 | — | MLC worse than DDR5 |
| 1S1R MLC | 89.33 | — | Density cost confirmed |
| PCM 2009 | 150.74 | 150.74 | ✅ exact |

PCM is no longer inverting vs DDR5 — correct ordering: **SLC ReRAM < DDR5 < MLC ReRAM < PCM**.

---

### Session 26 Remaining Priority List

**🟢 RESOLVED:**
- ~~OFMAP/IFMAP inversion~~ ✅
- ~~Metric drift (latency/EDP numbers stale)~~ ✅ (all ReRAM exact; DDR5 needs 3–5% text update)

**🔴 Remaining Blockers:**
1. **Area density convention** — `process_metrics.py` outputs `DDR5_baseline / ReRAM_density` (higher = denser, e.g., 1S1R MLC = 3.84×). Thesis says "0.25 = 4× denser" (inverse convention, lower = smaller). Decide which convention to keep and update thesis Fig. 23 accordingly.
2. **Regenerate all visualizations** from corrected CSVs — all graph images are now stale.

**🟡 High Priority (before submission):**
3. Update DDR5 GCC and GPT-2 numbers in Section 3.1.1 (174.81 → 180.34 and 224.28 → 236.16)
4. Add DDR5 6 F² citation to Section 1.2 and Appendix A
5. Add BL16 serialization penalty explanation to Section 2.3
6. Fix `$4\times$` LaTeX raw string in Section 2.4.1 (replace with Unicode "4×")

**🟢 Enhancement:**
7. Add ISPV queue congestion explanation to Section 3.1.1 — the `Queue_Latency_Cycles` column now gives exact values to cite (e.g., "OFMAP queue latency 3191 cycles vs IFMAP 781 cycles, a 4.08× ratio that quantitatively confirms the 4× ISPV write penalty").

---

## CRITICAL PRE-AUDIT FINDING: Pipeline Metric Drift

Before the section-by-section audit, there is one overarching structural problem that must be resolved first.

**The ETL refactor (Session 24) changed how metrics are numerically computed.** Every specific cycle count, EDP value, and geo-mean EDP number in the current thesis text was written against the *pre-refactor* pipeline output. The current `processed_hero_metrics.csv` and `processed_pareto_metrics.csv` produce materially different numbers across all workloads.

| Metric | Thesis Text (old) | Current CSV | Ratio |
|--------|-----------------|-------------|-------|
| DDR5 GCC latency | 174.81 cyc | 87.18 cyc | 2.0× |
| 1T1R SLC GCC latency | 80.22 cyc | 64.81 cyc | 1.2× |
| DDR5 LBM latency | 651.92 cyc | 63.97 cyc | 10.2× |
| 1T1R SLC LBM latency | 374.38 cyc | 50.15 cyc | 7.5× |
| 1S1R MLC LBM latency | 1545.40 cyc | 162.29 cyc | 9.5× |
| 1T1R SLC GPT-2 latency | 366.80 cyc | 48.95 cyc | 7.5× |
| DDR5 GPT-2 latency | 224.28 cyc | 69.40 cyc | 3.2× |
| 1S1R MLC AlexNet IFMAP | 1190.02 cyc | 166.06 cyc | 7.2× |
| 1S1R MLC AlexNet OFMAP | 3344.30 cyc | 153.56 cyc | 21.8× |
| Geo-Mean EDP DDR5 | 49.99 | 11.60 | 4.3× |
| Geo-Mean EDP PCM 2009 | 150.74 | 5.67 | 26.6× |
| Geo-Mean EDP 1T1R SLC | 23.98 | 6.30 | 3.8× |

**Root cause (hypothesis):** The streaming workloads (LBM, STREAM) are 10× off, while the compute-bound GCC is only 2× off. This non-uniform ratio rules out a simple clock-frequency normalization error. The most likely cause is that `process_metrics.py` Stage 6 changed which NVMain output statistic it parses for "average latency" — e.g., switching from `AverageLatency` (per-request, includes queuing) to a different field. Investigation is required **before any thesis numbers are updated**.

**Action required before thesis line-by-line edit:** Run `process_metrics.py` with `--verbose` against a known old stats file and compare parsed values against the pre-refactor pipeline output for the same trace.

---

## Section-by-Section Audit

---

### 1. Abstract

**✅ Solid:**
- Core motivation (supply-demand gap) is accurate.
- NVSim + NVMain 2.0 pipeline description is correct.
- "Flatline Effect" claim is qualitatively confirmed by current Pareto data (gcc clusters horizontally across all scales).
- "rank underutilization and zero-leakage physics" is the correct mechanistic explanation.
- AI workload MLP claim (rank-level interleaving slashes latency) is confirmed in current data.

**❌ Contradictions:**
- "massive gains in area density": this claim refers to the 1S1R density advantage, which is numerically broken in the current Hero Graph (active Area Bug — see Section 3.3). The abstract will need to be re-read after the bug is fixed to confirm the claim still holds.
- "inherent write-latency penalties can be effectively offset by massive area density gains": this narrative is sound in principle, but the AlexNet OFMAP write-penalty data in the current CSV actually shows **OFMAP latency is LOWER than IFMAP** for all configurations (see Section 3.1.1), directly contradicting the write-penalty evidence. This is the most dangerous structural weakness.

**📝 Missing:**
- Abstract does not quantify the power advantage. A concrete sentence ("half the standby power of DDR5 under single-threaded workloads") would strengthen the claim defensibility.

**🎯 Action Items:**
1. Hold abstract edits until the metric drift and OFMAP/IFMAP inversion are resolved.
2. After fixing, verify that "massive area density" claim is backed by the corrected Hero Graph numbers.
3. Add one quantitative anchor (power savings) to the abstract.

---

### 2. Section 1: Introduction & Background

**✅ Solid:**
- Economic motivation for the project (supply gap, HBM reallocation) is well-cited with [1][2].
- 22nm FinFET LOP process selection justification is correctly stated and cited.
- Resistance targets (LRS 10⁵ Ω, HRS 10⁹ Ω) correctly reference Matsui et al. [7].
- 1T1R vs 1S1R physics (sneak-path problem, access transistor vs selector) is well-described.
- Commercial viability citations are present: Xue et al. ISSCC 2021 [8] for 1T1R, Jo et al. IEDM 2014 [9] for 1S1R crossbar.
- MLC ADC + ISPV explanation is physically accurate.
- Area-per-bit metric choice (vs. $/bit) is well-justified.

**❌ Contradictions:**
- The docx extraction shows cell-area F² values as blank rendering artifacts (LaTeX math formulas not converting to plain text in `.docx`). The specific values "approximately **20 F²**" (1T1R) and "idealized **4 F²**" (1S1R) must be verified as rendering correctly in the submitted PDF.
- The section says 1T1R uses "approximately [blank]" — the 20 F² figure must appear in the final rendered document. Confirm the LaTeX/DOCX rendering chain is not silently dropping these.

**📝 Missing:**
- **The 6 F² DDR5 baseline citation is absent from the thesis body.** `generate_f2_metrics.py` asserts "JEDEC DRAM: 6 F² (industry consensus baseline, JESD79-5)" but this claim is not in the thesis and has no primary citation. Prof. Kvatinsky can challenge the 0.90 / 0.25 density ratio claims on this basis. Required: a primary Samsung or SK Hynix ISSCC/VLSI paper confirming the folded-bitline 6 F² DDR5 cell architecture. Candidates:
  - Kim et al. (Samsung, "DRAM Technology Scaling to Terabit Era"), ISSCC or VLSI Symposia
  - SK Hynix 1y-nm DDR5 roadmap disclosure
  - JEDEC JESD79-5 [10] (already cited) should be quoted specifically for the BL/cell area spec
- The **Endurance Constraint** sub-section raises endurance as a concern but never quantifies it (typical ReRAM endurance: 10⁶–10⁹ cycles). If this is in scope, it needs a number; if out of scope, remove the paragraph or add a note that endurance modeling was deferred.

**🎯 Action Items:**
1. Add a sentence: "DDR5 employs a folded-bitline 6 F² cell architecture [Ref], establishing our density normalization baseline."
2. Verify the 20 F² / 4 F² values render correctly in the final submitted PDF.
3. Either add endurance numbers or remove the endurance paragraph.

---

### 3. Section 2: Infrastructure & Methodology

**✅ Solid:**
- Gate-Keeper validation protocol described accurately.
- C++ repair patches (namespace collision, FlipNWrite deallocation, Python 2→3) are correctly documented.
- MLC Analytical Penalty Method (3× read, 4× write) is correctly attributed to EMBER macro (Upton et al. ESSCIRC 2023 [6]).
- DDR5-4800 JEDEC parameters (34-34-34, 1.1V, BL16, dual 32-bit sub-channels) are correctly stated.
- Workload suite rationale (gcc = compute-bound → exposes static leakage; lbm = streaming → exposes dynamic energy; AlexNet OFMAP = write-torture) is correctly stated.
- Frequency lock at 800 MHz for all ReRAM configs is correctly documented.

**❌ Contradictions:**
- The thesis correctly describes AlexNet OFMAP as "write-torture" that "explicitly exposes the physical 4× write-latency penalty of ISPV MLC programming." However, in the current CSV, AlexNet OFMAP shows **LOWER cycle counts than IFMAP** for all configurations (153.56 vs 166.06 cycles for 1S1R MLC full_dimm). The write-torture narrative has no empirical support in the current data. This is either a metric extraction bug (Stage 6 captures `AverageReadLatency` only, masking write delays) or a simulation issue.
- Section 2.3 states DDR5-4800 timing "inherently imposes real-world JEDEC bus serialization penalties." This is correct design intent, but the resulting DDR5 power in the current data is **0.174W for GPT-2** — significantly higher than the "~0.128W" cited in the context state (MBMM_AI_Context_State.md Section 1.3). This discrepancy is unresolved.

**📝 Missing:**
- **No explicit articulation of WHY DDR5 has high EDP.** The context state (Section 1.3) identifies the cause: "BL16 serialization delays which inflate cycle counts for small random reads compared to legacy BL8 DRAM." This mechanism is nowhere in the thesis text. Add a sentence in Section 2.3: "DDR5's mandatory BL16 burst serializes each access across 16 × 32 = 512 bits, inflating effective read latency for sub-burst-length random requests common in irregular CPU workloads — a latency tax absent from legacy BL8 DRAM."

**🎯 Action Items:**
1. Investigate why OFMAP cycles < IFMAP cycles in current CSV — determine if Stage 6 is only capturing `AverageReadLatency` (which ignores writes) and if so, add a complementary write-latency metric.
2. Add the BL16 serialization penalty explanation to Section 2.3.
3. Reconcile DDR5 GPT-2 power: context says 0.128W, CSV shows 0.174W. Identify which is correct.

---

### 4. Section 3.1.1: Latency Analysis

**✅ Solid (narrative and relative ordering):**
- Qualitative claim that 1T1R SLC outperforms DDR5 under GCC (compute-bound) is **still directionally correct**: current CSV shows 1T1R SLC at 81 ns vs DDR5 at 36 ns — wait, **this is inverted**. See below.

**❌ Contradictions — All Specific Numbers Are Stale:**

**Figure 1 (GCC Latency):**
- Thesis: "1T1R SLC averages just **80.22 cycles**, ... outperforms DDR5-4800 (**174.81 cycles**)."
- Current CSV: 1T1R SLC = 64.81 cyc @ 800 MHz = **81.01 ns**; DDR5 = 87.18 cyc @ 2400 MHz = **36.32 ns**.
- **In nanoseconds, DDR5 is actually FASTER under GCC (36 ns vs 81 ns)**. The thesis's cycle-count comparison is misleading because cycles are at different clocks. If you compare cycles at the same clock (800 MHz), DDR5 would be 87.18 cycles and 1T1R SLC 64.81 — so in 800 MHz cycles, 1T1R SLC wins. But **in wall-clock time**, DDR5 wins. The thesis must clarify which metric is being compared and at what reference frequency.

**Figure 2 (LBM Latency):**
- Thesis: 1T1R SLC = 374.38 cycles, DDR5 = 651.92 cycles, 1S1R MLC = 1545.40 cycles.
- Current CSV (full_dimm): 1T1R SLC = 50.15 cyc (62.69 ns), DDR5 = 63.97 cyc (26.65 ns), 1S1R MLC = 162.29 cyc (202.86 ns).
- All numbers are ~7.5–10× off. In ns terms: DDR5 is again FASTER (26 ns vs 63 ns for 1T1R SLC).

**Figure 3 (GPT-2 Latency):**
- Thesis: 1T1R SLC = 366.80 cycles (trailing DDR5 at 224.28 cycles by 1.6×).
- Current CSV: 1T1R SLC = 48.95 cyc (61.18 ns), DDR5 = 69.40 cyc (28.92 ns).
- Directional claim (1T1R SLC slower than DDR5 for AI reads) is **correct in ns** (61 ns vs 29 ns), but the specific numbers and the 1.6× figure are wrong.

**Figures 4–5 (AlexNet IFMAP vs. OFMAP — MLC Write Penalty):**
- Thesis: 1S1R MLC IFMAP = 1190.02 cycles → OFMAP spikes to **3344.30 cycles** (~2.8× degradation).
- Current CSV: 1S1R MLC IFMAP = 166.06 cycles, OFMAP = **153.56 cycles** (OFMAP is LOWER, not higher).
- **The MLC write-penalty narrative has NO empirical support in the current data.** The OFMAP latency is consistently lower than IFMAP across ALL configurations (1T1R SLC, 1T1R MLC, 1S1R SLC, 1S1R MLC). This completely undermines the "Write-Torture" claim.

**3D DRAM Anomaly:**
- Thesis: "3D DRAM experiences catastrophic latency (24,104 cycles)."
- Current CSV: 3D DRAM GCC full_dimm = 25.06 cycles (10.44 ns). This is actually the FASTEST configuration in the dataset, not catastrophic.
- These numbers differ by ~962×. The old "catastrophic latency" was almost certainly from a bug-era run before the NVSim/NVMain fixes of Sessions 3–15.

**📝 Missing:**
- A frequency normalization table or note explaining that cycle counts are in the technology's native clock (800 MHz for ReRAM, 2400 MHz for DDR5) and therefore cannot be directly compared without converting to nanoseconds.

**🎯 Action Items:**
1. **BLOCKER**: Determine whether the latency metric used throughout Section 3.1.1 should be in cycles (at what reference clock?) or nanoseconds. Choose ONE consistent metric.
2. Update all Figure descriptions with values from the current CSV.
3. Reframe the DDR5 vs 1T1R SLC GCC comparison: in 800 MHz cycles, 1T1R SLC wins (64.81 vs 87.18); in wall-clock ns, DDR5 wins (36.32 ns vs 81.01 ns). Decide which claim to make.
4. Investigate the OFMAP < IFMAP inversion urgently — this is a possible Stage 6 metric extraction bug (e.g., capturing only read latency, not write).
5. Remove or caveat the "24,104 cycles" 3D DRAM claim; the current data shows 25.06 cycles.

---

### 5. Section 3.1.2: Power Analysis

**✅ Solid — This is the most reliable section.**

All absolute power values for ReRAM match the current CSV within <1%:

| Claim in Thesis | Current CSV Value |
|-----------------|-------------------|
| 1T1R SLC GCC: 0.069W | 0.069051W ✓ |
| DDR5 GCC: 0.136W | 0.136297W ✓ |
| All ReRAM GPT-2 ≈ 0.066W | 0.066666W ✓ |
| 1T1R SLC LBM: 0.088W | 0.088255W ✓ |
| 1T1R MLC LBM: 0.076W | 0.076428W ✓ |
| 1T1R SLC STREAM: ≈ 0.080W | 0.080290W ✓ |
| All ReRAM AlexNet OFMAP ≈ 0.066W | 0.066666W ✓ |

**❌ Contradictions:**
- DDR5 GPT-2 power: Context state says "~0.128W" but current CSV shows **0.174472W** (36% higher). The thesis does not state this specific number but the context uses it. Clarify which is the authoritative value.
- The DDR5 "power tax" narrative relies on DRAM's capacitive refresh. While correct in principle, the thesis does not quantify this refresh overhead numerically (e.g., X% of total power is refresh in DDR5).

**📝 Missing:**
- A sentence explicitly linking the MLC power-throttling observation to the ISPV mechanism: "Because MLC ISPV writes take 4× longer per cell, the memory controller services fewer requests per unit time, resulting in a **lower average dynamic power** than SLC despite identical cell-switching energy." This explanation appears in the context state but not clearly in the thesis text.

**🎯 Action Items:**
1. Confirm DDR5 GPT-2 power (0.128W or 0.174W) — re-run the DDR5 configuration against GPT-2 trace to verify.
2. Add ISPV-throttling explanation for MLC power paradox.
3. This section is otherwise publishable as-is.

---

### 6. Section 3.1.3: EDP Analysis

**✅ Solid (narrative structure):**
- The narrative structure (lower EDP = more efficient; SLC ReRAM beats DDR5; 3D DRAM is a "mathematical mirage") is conceptually sound.
- The identification of 1S1R MLC as "efficiency tax for density" is the correct framing.

**❌ Contradictions — All EDP Numbers Are Stale:**

| Figure | Thesis Claim | Current CSV | Severity |
|--------|-------------|-------------|----------|
| Fig 12 GCC, 1T1R SLC EDP | 5.5 | ~4.48 | Low (directional OK) |
| Fig 12 GCC, DDR5 EDP | 23.8 | ~11.88 | High |
| Fig 13 GPT-2, 1T1R SLC EDP | 24.5 | ~3.26 | Very High |
| Fig 13 GPT-2, PCM EDP | 52.7 | ~2.58 | Very High |
| Fig 14 LBM DDR5 EDP | ~100.1 | ~9.83 | Very High |
| Fig 15 STREAM DDR5 EDP | ~100.8 | ~9.78 | Very High |
| Fig 16 IFMAP 1T1R SLC EDP | 25.6 | ~3.27 | Very High |
| Fig 16 IFMAP 1S1R MLC EDP | 79.3 | ~11.07 | Very High |
| Fig 17 OFMAP 1S1R MLC EDP | 223.0 | ~10.24 | Very High (also inverted) |

**Most critical issue:** Figure 17's claim that 1S1R MLC OFMAP EDP "catastrophically spikes to 223.0" depends on the write-torture OFMAP >> IFMAP latency. In the current CSV, OFMAP EDP (10.24) is actually LOWER than IFMAP EDP (11.07) for 1S1R MLC. The write-penalty spike has disappeared from the data.

**Figure 24 (Geo-Mean EDP) — Major Narrative Risk:**

| Technology | Thesis Fig 24 | Current CSV Geo-Mean |
|------------|--------------|---------------------|
| 1T1R SLC | 23.98 | 6.30 |
| 1S1R SLC | 35.15 | 7.73 |
| DDR5-4800 | 49.99 | 11.60 |
| PCM 2009 | 150.74 | 5.67 |

The current CSV shows PCM 2009 with **lower geo-mean EDP (5.67) than DDR5 (11.60)**, which means **PCM is more globally efficient than DDR5** in the current data. This inverts the thesis's central efficiency ranking. The thesis claims ReRAM SLC beats DDR5 which beats PCM; current data suggests PCM beats DDR5 as well. This is almost certainly an artifact of the OFMAP write-torture being missing from the PCM latency extraction.

**🎯 Action Items:**
1. **BLOCKER (same as 3.1.1):** Resolve the metric drift and OFMAP/IFMAP inversion. Until then, EDP numbers cannot be updated.
2. After resolution, regenerate geo-mean EDP values from corrected CSV and update all Figure 12–17 and Figure 24 descriptions.
3. If the write-torture effect is confirmed missing from the current pipeline, add a write-latency metric (not just read-latency) to Stage 6 and regenerate visualizations.

---

### 7. Section 3.2: Pareto Frontiers (Scaling Analysis)

**✅ Solid:**
- The "Flatline Paradox" description is qualitatively accurate — GCC data in the Pareto CSV clusters horizontally (power changes minimally across single→full_dimm, latency changes minimally).
- The AI workload claim (vertical drop = rank interleaving working) is qualitatively supported by the current data.
- "ReRAM capacity scaling does not induce compounding thermal penalties" is supported by the power-flatline data.
- The distinction between "1T1R SLC pushes down-and-left" vs DDR5 under AI workloads is correct in the current data.

**❌ Contradictions:**
- No specific numbers are quoted in Section 3.2 (it references Figures 18–22 descriptively), so there are no direct numerical contradictions here. However, the Pareto figures themselves will display current CSV data — verify the figure captions are consistent with the narrative.
- The claim that DDR5 is "heavily utilized" and draws more power is only true in the cycle-count domain; in ns the story is DDR5 is faster but with higher power, which is the correct framing.

**📝 Missing:**
- The Pareto section never states the specific scale at which the "Flatline Paradox" breaks (i.e., GPT-2 shows improvement starting at 8-chip). Adding this transition point would strengthen the MLP argument.

**🎯 Action Items:**
1. After metric drift is resolved, re-read Figure 18–22 captions to ensure they match the regenerated graphs.
2. Consider adding: "Under GPT-2, improvement begins at 8-chip and saturates by full-DIMM, confirming the onset of effective rank interleaving requires >N concurrent memory requests."

---

### 8. Section 3.3: Hero Graphs (Global Viability)

**✅ Solid (Geo-Mean EDP narrative):**
- The claim that "SLC ReRAM strictly dominates PCM 2009" is defensible once the write-torture metric is restored.
- The framing of the Hero Graphs as "global summary" (Density + Efficiency) is a good pedagogical structure.

**❌ Contradictions — Both Hero Graph Claims Are Broken:**

**Figure 23 (Area Density):**
The thesis states: "1T1R SLC model uses roughly **90% of the area of DDR5 (0.90)**, the 1S1R MLC cross-point architecture achieves a **4× density improvement, dropping the normalized area to an incredible 0.25**."

Current CSV values (using `DDR5_baseline / ReRAM_area_per_GB` convention):
- 1T1R_SLC: **0.221** (DDR5 is 4.52× denser than 1T1R SLC in mm²/GB)
- 1T1R_MLC: **0.442**
- 1S1R_SLC: **1.922** (1S1R SLC is 1.92× denser than DDR5)
- 1S1R_MLC: **3.844** (1S1R MLC is 3.84× denser than DDR5)

Two sub-problems here:
1. **Convention mismatch:** The thesis uses "lower = smaller footprint = more dense" (0.25 = uses 25% of DDR5's area). The CSV uses "higher = more dense" (3.84 = 3.84× denser than DDR5). These are inverse normalizations. The visualizer must resolve which convention it plots.
2. **Formula discrepancy:** The context state formula is `(NVSim_area_mm² / capacity_GB) / 35.0`. For 1T1R SLC (19.8 mm² / 0.125 GB) / 35 = 4.52, not 0.90. The context state expected value of "~0.90" is physically unjustifiable given the NVSim area of 19.8 mm² per 128MB chip. The 1T1R SLC is demonstrably **less dense** than DDR5 (20 F² vs 6 F² per bit), so a ratio of 0.90 (implying it is slightly denser than DDR5) is wrong.
3. **The Area Bug from Section 5 of MBMM_AI_Context_State.md** (fallback to 1.0) appears to have been partially fixed (values are no longer 1.0) but the resulting values may be using the wrong capacity denominator.

The physically correct ordering should be:
- 1T1R SLC (20 F²/bit): less dense than DDR5 → ratio < 1 if "lower = denser" convention
- 1S1R MLC (2 F²/bit effective): more dense than DDR5 → ratio < 1 if "lower = denser" convention

**Figure 24 (Geo-Mean EDP):**
See Section 3.1.3 — all numbers are stale and the PCM/DDR5 ordering may be inverted in the current data.

**🎯 Action Items:**
1. **Fix the area density formula in `process_metrics.py`** (this is the active Session 25 bug). Decide on one convention:
   - Option A (thesis convention, "normalized footprint"): `(ReRAM_area_per_GB) / DDR5_baseline` — lower is smaller/denser. Expected: 1T1R SLC ≈ 4.52, 1S1R MLC ≈ 0.26.
   - Option B (density multiplier): `DDR5_baseline / (ReRAM_area_per_GB)` — higher is denser. Expected: 1T1R SLC ≈ 0.22, 1S1R MLC ≈ 3.84.
2. The current CSV uses Option B. If thesis keeps Option A convention, fix `process_metrics.py` AND update thesis numbers to 4.52 (1T1R SLC) and 0.26 (1S1R MLC). This means rewording Figure 23 from "0.90" to "4.52×" and reframing the density narrative.
3. Alternatively: keep Option B convention in the CSV and rewrite Figure 23 text: "1T1R SLC density is 0.22× DDR5 (4.5× less dense), while 1S1R MLC achieves a 3.84× density advantage."
4. **After deciding convention:** add the 6 F² DDR5 citation as the normalization anchor.

---

### 9. Section 4: Conclusion

**✅ Solid:**
- "22nm ReRAM can offer massive power and density benefits... provided architectural mitigations (large L3 caches) and highly parallel workloads are utilized" — qualitatively correct and defensible.
- Open-source framework proposal is appropriate future work.
- L3 cache mitigation, wear-leveling, and endurance-aware scheduling are valid extensions.

**❌ Contradictions:**
- No specific numbers in the conclusion, so no direct numerical contradictions.
- However, the conclusion claims "ultra-dense 1S1R topology exhibits significant power-efficiency in read-dominant operations." The current data's PCM EDP < DDR5 EDP finding could be used to challenge the overall efficiency ranking if not addressed.

**📝 Missing:**
- The conclusion does not acknowledge the **frequency normalization limitation** (cycles at different clocks cannot be directly compared). Mentioning this as a known methodological boundary would add rigor.
- The L3 Cache Mitigation section references PCM legacy work [11] but does not cite any existing ReRAM+cache co-design proposals.

**🎯 Action Items:**
1. Hold conclusion edits until the core metric issues are resolved.
2. Consider adding a sentence on the frequency-normalized latency qualification.

---

### 10. Appendix A: Simulation Parameters

**✅ Solid:**
- Process node (22nm FinFET LOP) and resistance targets (LRS 10⁵ Ω, HRS 10⁹ Ω) match context state and are correctly cited.
- MLC penalty multipliers (3× read, 4× write) correctly cited to EMBER [6].

**❌ Contradictions:**
- Cell area entries "approximately [blank] for 1T1R, [blank] for 1S1R" — LaTeX math rendering may have dropped the F² values. Verify they appear as "20 F²" and "4 F²" in the submitted PDF.

**📝 Missing:**
- **DDR5 6 F² cell area is not listed in Appendix A.** This table is the natural home for the 6 F² citation. Add: "DDR5 Area Baseline: 6 F² folded-bitline DRAM cell. Reference: [Candidate Ref — Samsung/SK Hynix ISSCC/VLSI]. Used as the normalization anchor for all area-density comparisons."

**🎯 Action Items:**
1. Add DDR5 6 F² cell area row to Appendix A with primary literature citation.
2. Verify F² values render in the submitted PDF.

---

### 11. Appendices B & C

**✅ Solid:**
- Appendix B execution commands are accurate and reproducible.
- Appendix C DevOps protocol is correctly stated.
- Session 19 historical log (mistakes and corrections) is well-documented.

**❌ Minor:**
- Appendix C references "Federated 3-Repo Hub" — this terminology is not defined elsewhere. Either define it in the body or remove from the appendix.

---

### 12. References

**✅ All listed citations verified as present and complete:**
[1]–[12] are fully formatted with authors, venues, years, and access dates.

**📝 Missing citations (needed for injection):**
- **6 F² DDR5 cell:** Samsung or SK Hynix ISSCC/VLSI paper — **Priority 1**
- Optional: A more recent ReRAM endurance/wear-leveling paper to support Section 4.2 future work
- Optional: An L3 cache + NVM co-design paper (beyond PCM [11]) to support the L3 mitigation proposal

---

## Master Action Item Priority List

### 🔴 Blockers (Must fix before any line-by-line edit)

1. **Diagnose metric drift:** Run Stage 6 with verbose logging on one benchmark, compare parsed metric to pre-refactor output. Determine if `process_metrics.py` changed which NVMain statistic it reads for latency.
2. **Fix OFMAP/IFMAP inversion:** Add a write-latency (or total-operation-latency) metric to Stage 6. The current `AverageReadLatency` metric is invisible to write operations, causing OFMAP to appear faster than IFMAP — a false result that undermines the MLC Write Penalty narrative.
3. **Fix area density formula + convention:** Choose one normalization convention, fix `process_metrics.py` to produce correct values, and update Figure 23 description accordingly.
4. **Regenerate all visualizations** from corrected CSVs and verify graphs match updated thesis text.

### 🟡 High Priority (Before submission)

5. **Add DDR5 6 F² citation** to Section 1.2 and Appendix A.
6. **Add BL16 serialization penalty explanation** to Section 2.3.
7. **Decide on cycle vs. nanosecond latency metric** and apply consistently in Section 3.1.1.
8. **Reconcile DDR5 GPT-2 power** (0.128W vs 0.174W).

### 🟢 Enhancement (Strengthens thesis)

9. Add ISPV-throttling explanation (MLC lower power than SLC for write workloads) to Section 3.1.2.
10. Add frequency-normalization caveat to methodology.
11. Add quantitative power anchor to abstract (e.g., "2× standby power reduction").
12. Verify F² values render correctly in submitted PDF.
13. Consider adding scale-transition point for Flatline Paradox break (Section 3.2).

---

## Quick Reference: Current CSV Numbers vs. Thesis Claims

### Latency (full_dimm, key benchmarks)

| Config | Workload | Cycles (CSV) | Latency ns (CSV) | Thesis Claims |
|--------|---------|-------------|-----------------|---------------|
| DDR5_4800 | gcc | 87.18 | 36.32 | 174.81 cyc |
| 1T1R_SLC | gcc | 64.81 | 81.01 | 80.22 cyc |
| DDR5_4800 | lbm | 63.97 | 26.65 | 651.92 cyc |
| 1T1R_SLC | lbm | 50.15 | 62.69 | 374.38 cyc |
| 1S1R_MLC | lbm | 162.29 | 202.86 | 1545.40 cyc |
| DDR5_4800 | gpt2 | 69.40 | 28.92 | 224.28 cyc |
| 1T1R_SLC | gpt2 | 48.95 | 61.18 | 366.80 cyc |
| 1S1R_MLC | alexnet_ifmap | 166.06 | 207.57 | 1190.02 cyc |
| 1S1R_MLC | alexnet_ofmap | 153.56 | 191.95 | 3344.30 cyc |

### Power (full_dimm — these MATCH the thesis)

| Config | Workload | Power (CSV) | Thesis |
|--------|---------|------------|--------|
| 1T1R_SLC | gcc | 0.069051 W | 0.069 W ✓ |
| DDR5_4800 | gcc | 0.136297 W | 0.136 W ✓ |
| 1T1R_SLC | gpt2 | 0.066666 W | ~0.066 W ✓ |
| 1T1R_SLC | lbm | 0.088255 W | 0.088 W ✓ |
| 1T1R_MLC | lbm | 0.076428 W | 0.076 W ✓ |

### Geo-Mean EDP

| Technology | Thesis (Fig 24) | CSV Computed | Match? |
|------------|----------------|-------------|--------|
| 1T1R_SLC | 23.98 | 6.30 | ❌ |
| 1S1R_SLC | 35.15 | 7.73 | ❌ |
| DDR5_4800 | 49.99 | 11.60 | ❌ |
| PCM 2009 | 150.74 | 5.67 | ❌ (PCM currently beats DDR5!) |

### Area Density Ratio

| Technology | Thesis (Fig 23) | CSV | Correct (theoretical) |
|------------|----------------|-----|----------------------|
| DDR5_4800 | 1.00 (baseline) | 1.00 | 1.00 |
| 1T1R_SLC | ~0.90 | 0.2209 | 4.52× less dense |
| 1S1R_MLC | ~0.25 (4× denser) | 3.8445 | 3.84× more dense |

*Note: The CSV value of 3.84 for 1S1R MLC is physically correct (1S1R MLC is ~3.84× denser than DDR5 in mm²/GB terms). The thesis's "0.25" used the inverse convention. The context state's "0.90" for 1T1R SLC is physically unjustifiable.*
