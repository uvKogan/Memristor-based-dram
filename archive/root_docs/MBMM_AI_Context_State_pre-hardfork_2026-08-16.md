# MBMM AI Context State
**Project:** Evaluation of 22nm Memristor-Based Main Memory (MBMM) in Commodity DIMM Architectures
**Researcher:** Yuval Kogan, Technion
**Supervisor:** Prof. Shahar Kvatinsky
**Generated:** 2026-07-22 (Hardfork — regenerated from `documents/MBMM_Book_Typst/book.typ`,
the canonical, compile-verified, text-parity-audited edition of the Project Book)

**Supersedes:** the pre-hardfork version of this file (Session 24, 2026-05-22), archived at
`archive/root_docs/MBMM_AI_Context_State_pre-hardfork_2026-07-22.md`. That version's headline
findings — the "Power Flatline" and the 18-config/`StandbyPower` pipeline description — have
since been overturned by the repair work summarized in §3 below. Do not cite the archived
version for current numbers; it is kept only as a historical snapshot of the pre-repair state.

---

## 1. Executive Academic Narrative

### 1.1 Core Thesis

The memory supply-demand gap of late 2025, driven by DRAM wafer reallocation to AI-focused HBM
production, necessitates alternative technologies for commodity main memory. This project evaluates
22nm Memristor-based Non-Volatile Memory (NVM) as a DRAM replacement in standard DIMMs, using a
cross-layer pipeline bridging NVSim (device-level) and NVMain 2.0 (cycle-accurate architecture).
The evaluation characterizes 1T1R (transistor-gated) and 1S1R (selector-gated) architectures
across six benchmarks spanning compute-bound, memory-streaming, and AI-inference workloads.

### 1.2 The Central Findings (current, book-verified)

**Finding 1 — The Flatline Paradox (multi-rank scaling limit) — unchanged from prior narrative.**
Under single-threaded workloads (SPEC2017 gcc), scaling from 1-chip to 64-chip buys almost zero
latency benefit — the trace lacks the Memory Level Parallelism (MLP) to saturate even the primary
rank, so added ranks sit idle. The paradox resolves under massively parallel AI workloads (GPT-2,
AlexNet), where rank-level interleaving drives large latency reductions as the system scales.

**Finding 2 — Leakage-Class Separation (REPLACES the old "Power Flatline" finding).**
The prior narrative's "Power Flatline" — all ReRAM configs converging to ~0.066–0.069W regardless
of technology — is now understood to have been a **modeling artifact**: the pipeline was writing a
config field (`StandbyPower`) that NVMain never actually reads, so every non-volatile configuration
silently fell back to the same generic ~68mW/rank default regardless of its real NVSim-characterized
leakage. Once real per-technology leakage was wired into the parameters NVMain actually consumes
(`Eactstdby`/`Eprestdby`, module-summed across all ranks), the technologies split into two sharply
separated power tiers set entirely by standby physics:
- **Transistor-gated (1T1R) family: ~50.9 W** full-DIMM (99.99% static) — infeasible ungated at
  DIMM scale, 50–78× DDR5's floor.
- **Selector-gated (1S1R) family: 1.12–1.18 W** full-DIMM (97–99% static) — 1.7× DDR5's 0.651W
  calibration floor, within 11% of parity at the vendor spec-limit ceiling.
The 47× device-level leakage gap NVSim characterizes (794.7 mW vs. 16.9 mW per chip) now
propagates faithfully to the system level, and **is the single most consequential number in the
evaluation** — leakage discipline, not raw cell speed, decides architectural viability. MLC still
shows *lower* dynamic power than SLC under streaming workloads (ISPV throttles request rate faster
than it raises per-access energy), but this is now a second-order effect against a leakage-class
backdrop, not the primary story.

**Finding 3 — Density Advantage (numbers corrected, direction unchanged).**
1S1R's 4F² cell vs. 1T1R's 20F² still drives the density story, but the reported ratios changed
convention and magnitude after the Session ~25–26 area-density bug (fallback-to-1.0 on extraction
failure) was fixed and the die-area baseline was made fully empirical. Current, book-verified
figures (NVSim-characterized die area per GB vs. a commodity DDR5 baseline of 35 mm²/GB,
**higher = denser**, DDR5 = 1.00):
- 1S1R SLC: **1.92×** DDR5. 1S1R MLC: **3.84×** DDR5.
- 1T1R SLC: **0.22×** DDR5 (i.e. DDR5 is 4.5× denser). 1T1R MLC: **0.44×**.
(The old "0.90 / 0.25, lower = denser" framing is retired — it used an inverse convention and,
per the same-era `PARAMETER_TABLE.md` audit, produced a magnitude that wasn't reproducible from the
underlying NVSim area figures either. The archived pre-hardfork doc's 0.90/0.25 numbers should not
be cited.)

**Finding 4 — Endurance is a capacity- and workload-dependent constraint, not a categorical
barrier (NEW — absent from the prior context state entirely).**
At the modeled 8 GB SLC module, worst-case sustained streaming (LBM) yields only **1.1 years** of
projected lifetime — below the 5–10 year server-replacement target — while every other workload
clears the target by 2× to two orders of magnitude even at 8 GB. At the 64–128 GB capacities where
ReRAM's density advantage is actually realized, worst-case SLC lifetime reaches **9–17 years**
(the slower-writing selector variant, 12–25 years), meeting or beating the target. MLC is harsher:
measured 16 GB-module LBM lifetimes are 0.54 years (1T1R) / 0.94 years (1S1R), remaining marginal
even at 128 GB — an independent argument (beyond the write-latency one) for restricting MLC to
read-dominant deployments.

**Finding 5 — A Simulation-Fidelity Audit found eleven silent failure modes; nine were repaired
(NEW — this is the single biggest addition since the prior context state, and the reason Findings
2–4 above changed at all).** See §3 for the full list. In short: the toolchain was silently
producing numbers that looked plausible but weren't measuring what they claimed to measure, across
the power model, the DRAM baselines, the PCM baseline, and the trace-admission methodology. Two of
the eleven remain open (idle-power gating is simulated nowhere in the current NVMain fork; the
GPT-2 trace's SCALE-Sim provenance couldn't be confirmed against a preserved run) — both are
disclosed as residual limitations in the book, not silently absorbed into the headline numbers.

### 1.3 DDR5 vs. ReRAM Quantitative Conclusions (current, from book Table 6 — full-DIMM,
repaired power model, ungated ReRAM / standard-idle DRAM & PCM)

| Technology | GCC latency (ns) | GCC power (W) | Geo-mean PDP (W·ns) | Die density (× DDR5) | Worst-case lifetime @128GB | Architectural role |
|---|---|---|---|---|---|---|
| DDR5-4800 | 81.2 | 0.651 (44.7% refresh) | 99.5 | 1.00 | n/a (volatile) | commodity baseline |
| PCM (Lee et al. 2009) | 6,399.2 | 0.040 | 165.3 | 1.25 | not evaluated | floor-power NVM; 4–49× latency cost |
| 1T1R SLC | 130.9 | 50.870 | 21,350.6 | 0.22 | 17.3 yr | latency-optimized niche; infeasible ungated |
| **1S1R SLC** | 190.3 | 1.118 | 737.1 | 1.92 | 24.8 yr | **flagship: one gating policy from DDR5 parity** |
| 1T1R MLC | 330.2 | 50.886 | 50,426.6 | 0.44 | 4.3 yr | infeasible ungated |
| 1S1R MLC | 544.4 | 1.180 | 1,991.4 | 3.84 | 7.5 yr | read-only capacity tier (frozen weights) |

**Headline reframe vs. the pre-hardfork doc:** selector-gated 1S1R SLC — not raw 1T1R latency — is
now the flagship configuration. It trails DDR5 by only 1.7× on power at the conservative
calibration floor (within 11% at the spec-limit ceiling), with zero refresh cost against DDR5's
33–45% refresh tax, and offers 1.9–3.8× DDR5's density. One credible idle-gating policy is what
separates it from outright power parity — currently unsimulated (Finding 5 / §3, item 5).

---

## 2. Theoretical Physics Baselines

### 2.1 Process Node & Resistance Targets — unchanged, still current
- **Node:** 22nm FinFET LOP (Low Operating Power) — LOP over HP for NVSim solver convergence and
  thermal envelope alignment with high-capacity main memory.
- **Resistance Targets** (Matsui et al. [7]): LRS = 10⁵ Ω, HRS = 10⁹ Ω. 10,000:1 ratio for
  reliable sensing margin on 1024-cell bitlines.
- **Operating Voltages:** ReadVoltage = 1.4V nominal (swept ±20% in the robustness analysis, §3.1.5
  of the book — read latency is invariant to the sweep; PDP changes <4%).

### 2.2 Cell Topology — 1T1R vs. 1S1R — unchanged
| Parameter | 1T1R | 1S1R |
|---|---|---|
| Cell Area | 20 F² | 4 F² |
| Sneak-path mitigation | CMOS access transistor (full isolation) | Non-linear selector (thresholding) |
| Commercial precedent | 22nm eReRAM in volume production (Xue et al., ISSCC 2021) | Crossbar Inc. 4Mb crosspoint milestone |

### 2.3 SLC vs. MLC — unchanged
MLC (2 bits/cell) requires Iterative Step-and-Verify (ISPV) programming and ADC-precision sensing;
NVSim's native MLC logic is non-functional at 22nm (FPE in `Mat.cpp`), so MLC metrics are
analytically derived from the SLC baseline via the EMBER-macro-heuristic penalty method (Upton et
al. [6]): **3× read latency, 4× write latency**, consistent with published multi-level ReRAM
characterization (Le et al. [13]).

### 2.4 Area Density Baseline — CORRECTED (convention and worked numbers both changed)
- **DDR5 physical baseline:** 35 mm²/GB (commodity DDR5-4800 dies, Choe [18]) — same anchor value
  as the prior doc, but the *formula orientation* was wrong there and is corrected here.
- **Corrected formula:** `Area_Density_Ratio = DDR5_baseline_mm²/GB / (NVSim_area_mm² / capacity_GB)`
  — i.e. **DDR5 divided by the technology**, not the reverse. Under this convention, **higher is
  denser** (matches Table 6 / Finding 3 above). The prior doc's formula
  (`(NVSim_area_mm² / capacity_GB) / 35.0`) computes the inverse ratio and, when actually evaluated
  against NVSim's own area figures, doesn't reproduce the "~0.90 / ~0.25" numbers it claimed either
  — that inconsistency is what the `Session ~25` audit (`PARAMETER_TABLE.md`, now archived) first
  flagged, and what the fix in §1.3 above resolves.
- Node-independent cell-level bound (process-agnostic sanity check, book Appendix A / §3.3):
  DRAM 6F²/bit, 1T1R 20F²/bit, 1S1R 4F²/bit (2 bits/cell as MLC) — at any matched process node,
  1S1R MLC is 3.0× denser than DRAM by cell arithmetic alone; the measured die-level 3.84× exceeds
  this because DRAM carries more real peripheral/spare-area overhead than the pure-cell bound
  ignores.

---

## 3. Simulation-Fidelity Audit (NEW SECTION — supersedes old §3.1/3.2 "Engine Patches" framing)

A systematic audit of the NVSim-to-NVMain flow (book §3.1.6), conducted against the raw simulator
sources and statistics files, found **eleven silent failure modes** that bounded which conclusions
the evaluation could honestly draw. **Nine of eleven have been repaired**, with affected
simulations re-run; every power and PDP figure in the current book derives from the resulting
repaired dataset.

| # | Failure mode | Status | Effect |
|---|---|---|---|
| 1 | Efficiency metric multiplied Watts by cycle counts from mismatched clock domains (800 MHz ReRAM vs. 2400 MHz DDR5) | **Fixed** | Biased comparison 3× against DDR5; PDP now computed in physical W·ns |
| 2 | `StandbyPower` config field written by the generator but never read by NVMain (dead config) | **Fixed** | Device-characterized leakage never reached the simulation at all |
| 3 | Generic standby-energy defaults (`Eactstdby`/`Eprestdby`) gave every non-volatile config the same ~68mW/rank floor | **Fixed** | This is the direct cause of the old "Power Flatline" (§1.2 Finding 2) |
| 4 | Reported "Total System Power" was the single most-loaded rank, not the module sum | **Fixed** | ReRAM spans 8 ranks, DDR5 spans 2 — per-rank reporting wasn't comparable across technologies |
| 5 | NVMain's power-down state machine is disabled in source (`HandleLowPower()` call site commented out) | **Open — top-priority future work** | Every ReRAM power figure in the book is worst-case *ungated*; DRAM/PCM model standard idle behavior. This asymmetry is restated wherever cross-technology power is compared |
| 6 | gem5 traces generated without L1/L2 caches or warmup (raw CPU-to-memory stream, first 10M instructions) | **Documented, not fixed** | Overstates memory pressure — conservative for endurance bounds, a caveat for absolute queueing magnitudes |
| 7 | DDR5 refresh machinery inherited unrescaled from a DDR3-1333 template | **Fixed** | Refresh fired 3.6× too often at 6.6× too little cost each; recalibrating to JEDEC JESD79-5 raised DDR5's refresh share from 57.9% to the final 33–45% band |
| 8 | DDR5 supply voltage was NVMain's stock default (1.5V) rather than the JEDEC-specified 1.1V | **Fixed** | Corrected + calibrated to published vendor IDD tables (Micron/SK hynix, run as a two-vendor band) |
| 9 | PCM baseline ran at 800 MHz — twice its cited 400 MHz basis (Lee et al. [11]) | **Fixed** | Roughly doubled PCM's reported latencies once corrected |
| 10 | ReRAM access energies written under config keys NVMain never reads (dead keys, same class of bug as #2) | **Fixed** | Every ReRAM config had silently used identical stock access-energy constants despite a real 5.7× read-energy difference between 1T1R/1S1R |
| 11 | Heterogeneous, unmatched host-CPU frequencies across technologies (800 MHz ReRAM host vs. 2/3 GHz others) with an unrescaled trace-admission cutoff | **Fixed** | Every technology now admits the identical request population per workload (matched-host correction: 250M-trace-cycle admission at a 3 GHz reference host, 83.33ms wall-clock for every configuration) |

**Validation discipline:** every repair was checked against device-level anchors (0.0% error) or
exact predicted arithmetic, and an independent blind re-verification pass re-derived every check
from configs, sources, and raw statistics before the repaired dataset was adopted.

---

## 4. Pipeline Architecture (updated: config count, matched-host correction)

`mbmm_master.py` remains the Gate-Keeper: no simulation data is accepted without a complete
end-to-end pass. Architecture unchanged from the prior doc (`1_run_nvsim_hardware.py` →
`2_extract_hardware_metrics.py` → `3_gen_nvmain_config.py` → `4_execute_simulation.py` →
`process_metrics.py` → `visualize_results.py`/`visualize_pareto.py`/`visualize_hero_graphs.py`,
all through `logging_config.py`'s unified logger) — the `ARCHITECTURE_REFACTOR_PROPOSAL.md`
(archived, `archive/root_docs/`) that specified this split was fully implemented and is no longer
a live proposal.

**Corrected matrix size:** the prior doc said "18 configs." The book's Appendix B and the
`Priority1_StandbyPower_Fix_Scoping.md` blast-radius analysis (archived) both confirm the actual
matrix is **20 configurations** (16 ReRAM variants: 4 technologies × 4 scales, + DDR5-4800, PCM,
2D_DRAM_example, 3D_DRAM_example) × 6 workloads = 120 stats files.

**Matched-host cycle budgets (post-repair, §3 item 11):** every configuration now runs to the same
250M-trace-cycle admission at a fixed 3 GHz reference host — 83.33ms wall-clock for all (ReRAM
66.7M memory cycles at 800 MHz, PCM 33.3M at 400 MHz, DDR5's 200M unchanged at 2400 MHz).

---

## 5. Session History — Key Milestones (extended)

Formal session-summary `.docx` files (`resources/session summaries/`) stop at **Session 24**
(2026-05-22). Everything below Session 24 is reconstructed from git history, the book's own §3.1.6
narrative, and the (now-archived) scoping/audit docs — not from a formal session summary, since
none exists for this span. Treat session *numbers* below Session 25/26 as approximate; dates and
commit hashes are the reliable anchor.

| Session | Date | Milestone |
|---|---|---|
| 1–24 | 2026-02-21 → 2026-05-22 | See archived pre-hardfork context state for full detail; ends with the ETL refactor (`process_metrics.py` as single source of truth, `logging_config.py`, Hybrid-Empirical density adopted, Area Bug identified) |
| 25 (2026-05-26) | 2026-05-26 | Thesis Review audit: flagged OFMAP/IFMAP latency inversion, area-density convention mismatch, metric drift vs. pre-refactor pipeline, PCM-beats-DDR5 EDP inversion |
| 26 (2026-05-29) | 2026-05-29 | Re-audit: root-caused metric drift + OFMAP/IFMAP inversion to a single bug (`extract_total_execution_cycles()` matching `averageLatency` instead of `averageTotalLatency`, discarding queue-wait time — exactly where the ISPV write-torture penalty lives). Patched; all CSVs regenerated |
| — (2026-07-06, commit `9734bc0`) | 2026-07-06 | ETL latency/area-density extraction fix (queue-aware PDP, JSON-sourced area), visualizers aligned |
| — (2026-07-06, commits `2e1d213`/`3335bd4`) | 2026-07-06 | nvsim submodule maintenance (URL rename, CLAUDE.md docs) |
| — (2026-07-11, commit `923aa8f`; scoped in the now-archived `Priority1_StandbyPower_Fix_Scoping.md`) | 2026-07-11 | **The power-model repair**: real per-technology leakage derived from NVSim and wired into `Eactstdby`/`Eprestdby`; power extraction switched to module-sum across all ranks; dead `StandbyPower` config retired. This is the direct cause of §1.2 Finding 2 above |
| — (2026-07-13, commit `c728173`) | 2026-07-13 | Investigated the throughput mechanism (stamp-coverage vs. service-limited completion) behind the book's §3.1.1 sustained-streaming sentence; archived superseded `results/` generations |
| — (unlabeled, in progress at generation time) | 2026-07-22/23 | Full §3.1.6 fidelity audit completed and written into the book (11 findings, 9 repaired); endurance analysis (§3.1.4) and ReadVoltage robustness sweep (§3.1.5) added; Project Book converted to a compile-verified Typst edition (`documents/MBMM_Book_Typst/`, see its `TYPST_QA_REPORT.md`) with zero real text-parity diffs against the source docx; root-level repo housekeeping (stale scripts/docs archived or deleted, `documents/` reorganized); this file regenerated via `mbmm_hardfork` against the current book |

---

## 6. Current Status (replaces old §5 "Current Active Bug" — that bug is resolved)

**No known active blocking bug.** The area-density extraction failure that the pre-hardfork doc
described as open (`Area_Density_Ratio` stuck at 1.0 fallback) was fixed between Sessions 25–26 and
again refined in the 2026-07-06 ETL fix; current values are the Finding 3 figures in §1.3.

**Known, disclosed residual limitations** (from the book's §3.1.6, carried forward honestly rather
than fixed):
1. **Idle-power gating is unsimulated** (§3 item 5) — every ReRAM power figure is worst-case
   ungated. This is the single highest-leverage open item; restoring it is the top-priority future
   work item (book §4.1).
2. **gem5 trace provenance is weaker than ideal** (§3 item 6) — no L1/L2 caches, no warmup,
   confirmed for gcc/lbm but the GPT-2 SCALE-Sim trace's provenance could not be tied to a
   preserved run (AlexNet's TPU-v1 256×256 output-stationary configuration is confirmed; GPT-2 is
   not).
3. **Open-loop trace replay**: no CPU/accelerator feedback path, so every latency figure is a
   memory-subsystem quantity, not a projected end-to-end application slowdown.
4. **DDR5 power is reported as a two-vendor calibration band** (Micron ceiling / SK hynix floor)
   rather than a single point value, since datasheet IDD figures are specification limits, not
   measured typicals.

---

## 7. Pending Documentation / Narrative Items (replaces old §6 — the 6F² citation item is retired)

The old pending item ("inject IEEE citations to defend a 6F² DDR5 baseline") is **no longer
applicable** — the density methodology it was defending was abandoned. The book's current density
baseline is the fully empirical 35mm²/GB DDR5 figure (§2.4 above), already cited (Choe [18]) in the
book. `generate_f2_metrics.py` (the script that produced the old 6F² theoretical chart) and its
output were confirmed orphaned — referenced by nothing in the current book — and have been deleted
rather than carried forward as a stale pending item.

No other pending documentation items are currently tracked in this file. Future gaps found during
review should be logged here rather than left implicit.

---

*Document regenerated via `mbmm_hardfork` from: `documents/MBMM_Book_Typst/book.typ` (canonical,
compile-verified). Cross-referenced against: git log (commits `80bc42a` through `c728173`),
`archive/root_docs/Priority1_StandbyPower_Fix_Scoping.md`,
`archive/root_docs/Thesis_Review_Roadmap.md`, `archive/root_docs/ARCHITECTURE_REFACTOR_PROPOSAL.md`,
and the archived pre-hardfork version of this file.*
