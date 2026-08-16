# MBMM AI Context State
**Project:** Evaluation of 22nm Memristor-Based Main Memory (MBMM) in Commodity DIMM Architectures
**Researcher:** Yuval Kogan, Technion
**Supervisor:** Prof. Shahar Kvatinsky
**Generated:** 2026-08-16 (Hardfork — regenerated from `documents/MBMM_Book_Typst/Project_Book.typ`,
the canonical, compile-verified edition of the Project Book, now including the reference-audit and
re-simulation cycle summarized in §3 below)

**Supersedes:** the 2026-07-22 hardfork of this file (archived at
`archive/root_docs/MBMM_AI_Context_State_pre-hardfork_2026-07-22.md` is the version *before that*;
the 2026-07-22 version itself has not yet been separately archived — see housekeeping note in §7).
That version's DDR5 timing, MLC read/write penalty multipliers, and every number derived from them
(Findings 2 and 4 below, the §1.3 table, §2.3, §3's audit-item count) have since been corrected by
the work in §3, items (12) and (13). Do not cite the 2026-07-22 version's DDR5 or MLC-specific
numbers; its qualitative structure (Findings 1, 3, and the density baseline) is still accurate and
carried forward unchanged.

---

## 1. Executive Academic Narrative

### 1.1 Core Thesis

The memory supply-demand gap of late 2025, driven by DRAM wafer reallocation to AI-focused HBM
production, necessitates alternative technologies for commodity main memory. This project evaluates
22nm Memristor-based Non-Volatile Memory (NVM) as a DRAM replacement in standard DIMMs, using a
cross-layer pipeline bridging NVSim (device-level) and NVMain 2.0 (cycle-accurate architecture).
The evaluation characterizes 1T1R (transistor-gated) and 1S1R (selector-gated) architectures
across six benchmarks spanning compute-bound, memory-streaming, and AI-inference workloads.

### 1.2 The Central Findings (current, book-verified, post-re-simulation)

**Finding 1 — The Flatline Paradox (multi-rank scaling limit) — unchanged.**
Under single-threaded workloads (SPEC2017 gcc), scaling from 1-chip to 64-chip buys almost zero
latency benefit — the trace lacks the Memory Level Parallelism (MLP) to saturate even the primary
rank, so added ranks sit idle. The paradox resolves under massively parallel AI workloads (GPT-2,
AlexNet), where rank-level interleaving drives large latency reductions as the system scales.

**Finding 2 — Leakage-Class Separation — numbers refined, conclusion strengthened.**
The technologies split into two sharply separated power tiers set entirely by standby physics:
- **Transistor-gated (1T1R) family: ~50.9 W** full-DIMM (99.99% static) — infeasible ungated at
  DIMM scale, **65–78× DDR5's floor** (corrected from the prior doc's "50–78×" — that lower bound
  was never actually reproducible from the underlying data, in either the pre- or post-repair
  generation; see §3 item (12) for the DDR5-side correction that prompted re-deriving this range).
- **Selector-gated (1S1R) family: 1.12–1.30 W** full-DIMM (97–99% static) — 1.7× DDR5's 0.651 W
  calibration floor, within 11% of parity at the vendor spec-limit ceiling.
The 47× device-level leakage gap NVSim characterizes (794.7 mW vs. 16.9 mW per chip) propagates
faithfully to the system level, and **is the single most consequential number in the evaluation**
— leakage discipline, not raw cell speed, decides architectural viability. A dedicated NVSim
sensitivity sweep (HRS held at 25×–10,000× LRS) confirmed this separation is completely insensitive
to the exact resistance-target citation that originally motivated it — it is driven entirely by the
access-device model (CMOS transistor vs. selector), not by the memristor's own resistance values
(book Appendix A).

**MLC-vs-SLC dynamic power is now workload-direction-dependent, not uniformly lower (revised from
the prior doc's blanket claim).** With the corrected MLC latency/energy multipliers (§2.3, §3 item
13), MLC dynamic power *exceeds* SLC's under GCC, LBM, STREAM, and AlexNet OFMAP — the corrected
write-latency penalty (3.263×, down from the previous unsourced 4.0×) throttles MLC write
throughput less than assumed, so more energy-costly writes complete per second even though each
write still costs more energy per operation. MLC dynamic power stays *below* SLC's only on the two
read-dominated workloads (GPT-2, AlexNet IFMAP), where the corrected read-energy penalty (1.1×, down
sharply from the previous unsourced 3.0×) dominates instead. In every case, module total power
remains anchored to its technology's leakage tier regardless of which direction the dynamic term
moves — this is a second-order effect against the leakage-class backdrop above, not a challenge to
it.

**Finding 3 — Density Advantage — unchanged.**
1S1R's 4F² cell vs. 1T1R's 20F² still drives the density story (NVSim-characterized die area per GB
vs. a commodity DDR5 baseline of 35 mm²/GB, **higher = denser**, DDR5 = 1.00):
- 1S1R SLC: **1.92×** DDR5. 1S1R MLC: **3.84×** DDR5.
- 1T1R SLC: **0.22×** DDR5 (i.e. DDR5 is 4.5× denser). 1T1R MLC: **0.44×**.
Density is purely a NVSim die-area characterization, independent of the DDR5-timing and
MLC-multiplier corrections in §3 items (12)/(13) — confirmed unaffected by direct diff of the
regenerated results against the prior generation (byte-identical).

**Finding 4 — Endurance is a capacity- and workload-dependent constraint, not a categorical
barrier — MLC lifetimes revised downward.**
At the modeled 8 GB SLC module, worst-case sustained streaming (LBM) yields only **1.1 years** of
projected lifetime — below the 5–10 year server-replacement target — while every other workload
clears the target by 2× to two orders of magnitude even at 8 GB. At the 64–128 GB capacities where
ReRAM's density advantage is actually realized, worst-case SLC lifetime reaches **9–17 years** (the
slower-writing selector variant, 12–25 years), meeting or beating the target. MLC is harsher, and
now measurably harsher than the prior doc reported: at the physical 16 GB module, measured LBM
lifetimes are **0.42 years for 1T1R MLC** (was 0.54 — 1,706,535 writes per 83.33ms window, up from
1,320,096, since the corrected write-latency multiplier throttles MLC less) and **0.75 years for
1S1R selector MLC** (was 0.94 — 942,439 writes, up from 751,405); even at 128 GB these reach only
**3.3 and 6.0 years** respectively (was 4.3/7.5) — still an independent argument (beyond the
write-latency one) for restricting MLC to read-dominant deployments, now with a somewhat sharper
edge than previously reported.

**Finding 5 — A Simulation-Fidelity Audit found thirteen silent failure modes; eleven were
repaired (count and two items added since the prior doc, both in §3).** See §3 for the full list.
In short: the toolchain — and, this cycle, the *book's own bibliography* — was silently producing
numbers that looked plausible but weren't measuring or citing what they claimed to. Two of the
thirteen remain open (idle-power gating is simulated nowhere in the current NVMain fork; the GPT-2
trace's SCALE-Sim provenance couldn't be confirmed against a preserved run) — both are disclosed as
residual limitations in the book, not silently absorbed into the headline numbers.

### 1.3 DDR5 vs. ReRAM Quantitative Conclusions (current, from book Table 6 — full-DIMM,
repaired power model + corrected DDR5 timing + corrected MLC multipliers, ungated ReRAM /
standard-idle DRAM & PCM)

| Technology | GCC latency (ns) | GCC power (W) | Geo-mean PDP (W·ns) | Die density (× DDR5) | Worst-case lifetime @128GB | Architectural role |
|---|---|---|---|---|---|---|
| DDR5-4800 | 87.2 | 0.651 (44.7% refresh) | 104.3 | 1.00 | n/a (volatile) | commodity baseline |
| PCM (Lee et al. 2009) | 6,399.2 | 0.040 | 165.3 | 1.25 | not evaluated | floor-power NVM; 4–49× latency cost |
| 1T1R SLC | 130.9 | 50.870 | 21,350.6 | 0.22 | 17.3 yr | latency-optimized niche; infeasible ungated |
| **1S1R SLC** | 190.3 | 1.118 | 737.1 | 1.92 | 24.8 yr | **flagship: one gating policy from DDR5 parity** |
| 1T1R MLC | 223.2 | 50.877 | 37,074.9 | 0.44 | 3.3 yr | infeasible ungated |
| 1S1R MLC | 354.2 | 1.130 | 1,396.1 | 3.84 | 6.0 yr | read-only capacity tier (frozen weights) |

**What changed vs. the 2026-07-22 doc:** DDR5's GCC latency rose 81.2→87.2 ns (+7.5%) and geo-mean
PDP 99.5→104.3 W·ns (+4.8%) — the corrected `tCAS`/`tRCD`/`tRP` timing (34-34-34→40-39-39, §3 item
12) diluted into total latency once blended with the unaffected `tRAS`/`tWR`/refresh components.
Both MLC rows dropped substantially: 1T1R MLC latency 330.2→223.2 ns (-32.4%) and geo-mean PDP
50,426.6→37,074.9 W·ns (-26.5%); 1S1R MLC latency 544.4→354.2 ns (-34.9%) and geo-mean PDP
1,991.4→1,396.1 W·ns (-29.9%) — the corrected read/write latency multipliers (1.917×/3.263×, down
from the unsourced 3.0×/4.0×, §3 item 13) throttle MLC access less severely than previously modeled.
DDR5 power and both SLC rows are unaffected (neither fix touches SLC device characterization or
DDR5's IDD/energy calibration) — confirmed byte-identical across the re-simulation.

**Headline reframe, still current:** selector-gated 1S1R SLC — not raw 1T1R latency — remains the
flagship configuration. It trails DDR5 by only 1.7× on power at the conservative calibration floor
(within 11% at the spec-limit ceiling), with zero refresh cost against DDR5's 33–45% refresh tax,
and offers 1.9–3.8× DDR5's density. One credible idle-gating policy is what separates it from
outright power parity — currently unsimulated (Finding 5 / §3, item 5).

---

## 2. Theoretical Physics Baselines

### 2.1 Process Node & Resistance Targets — reworded (citation scope corrected, values unchanged)
- **Node:** 22nm FinFET LOP (Low Operating Power) — LOP over HP for NVSim solver convergence and
  thermal envelope alignment with high-capacity main memory.
- **Resistance Targets:** LRS = 10⁵ Ω, HRS = 10⁹ Ω. The LRS floor is Matsui et al.'s [7] direct
  recommendation for high-capacity *digital* ReRAM memory; the paired HRS value is adopted from the
  same paper's analog Computation-in-Memory (CiM) design point as a representative high-resistance
  target — [7] does not separately specify an HRS floor for the digital case, and the prior doc's
  citation overstated how directly [7] supports the pair. A dedicated NVSim sensitivity sweep
  (HRS = 25×–10,000× LRS) subsequently showed this precision doesn't matter for any result in the
  book: modeled leakage power is bit-for-bit identical across the whole swept range for both 1T1R
  and 1S1R, and read latency varies by at most 1.7% — the 47× leakage-class separation (§1.2 Finding
  2) is driven entirely by the access-device model, not by HRS.
- **Operating Voltages:** ReadVoltage = 1.4V nominal (swept ±20% in the robustness analysis, §3.1.5
  of the book — read latency is invariant to the sweep; PDP changes <4%).

### 2.2 Cell Topology — 1T1R vs. 1S1R — unchanged
| Parameter | 1T1R | 1S1R |
|---|---|---|
| Cell Area | 20 F² | 4 F² |
| Sneak-path mitigation | CMOS access transistor (full isolation) | Non-linear selector (thresholding) |
| Commercial precedent | 22nm eReRAM in volume production (TechInsights TSMC 22ULL teardown [24]) | Crossbar Inc. 4Mb crosspoint milestone |

(Commercial-precedent citation corrected this cycle: the prior doc's source, Xue et al. [8], is a
2T2R ISSCC research macro, not a 1T1R commercial-production example — [24] is the reference that
actually documents shipping 22nm eReRAM; the book text was reworded to drop the unconfirmed "1T1R"
topology claim rather than assert something [24] doesn't state either.)

### 2.3 SLC vs. MLC — multipliers and citations corrected, largest single change this cycle
MLC (2 bits/cell) requires Iterative Step-and-Verify (ISPV) programming and ADC-precision sensing;
NVSim's native MLC logic is non-functional at 22nm (FPE in `Mat.cpp`), so MLC metrics are
analytically derived from the SLC baseline via four multipliers applied to latency and energy. The
prior doc's **3× read latency, 4× write latency, 3× access energy**, attributed to "EMBER-macro
heuristics," were unsourced placeholders — that attribution does not exist in either EMBER
publication, and the conference paper (Upton et al. [6], ESSCIRC 2023) reports no write-latency or
write-energy data of any kind. The corrected multipliers, each traced to a real measured figure on
the same EMBER macro across its two publications:
- **Read latency 1.917×, read energy 1.1×** — Upton et al. [6] (ESSCIRC 2023) Table I: 1b/cell vs.
  2b/cell read latency 12/23 ns, read energy 1.0/1.1 pJ/bit.
- **Write latency 3.263×, write energy 3.0×** — Levy et al. [31] (IEEE JSSC 2024, the full journal
  follow-up the conference paper's page budget omitted) Section III: 1b/cell vs. 2b/cell
  write-verify bandwidth 12.4/3.8 Mbps, write-verify energy 0.40/1.2 nJ/bit.

Write energy is numerically unchanged (3.0× both times, now properly sourced instead of unsourced);
the read-energy correction (3.0×→1.1×) is the largest single change of the four, and drives most of
the MLC dynamic-power reordering described in §1.2's Finding 2 addendum. The prior doc's
cross-reference to Le et al. [13] as a consistency check for the old placeholder values has been
dropped — [13] uses a different multi-level resistance-encoding scheme with no comparable SLC
baseline, so it never actually supported a specific multiplier value either way.

### 2.4 Area Density Baseline — unchanged this cycle (see prior hardfork for the convention fix)
- **DDR5 physical baseline:** 35 mm²/GB (commodity DDR5-4800 dies, Choe [18]).
- **Formula:** `Area_Density_Ratio = DDR5_baseline_mm²/GB / (NVSim_area_mm² / capacity_GB)` — DDR5
  divided by the technology; **higher is denser**.
- Node-independent cell-level bound (process-agnostic sanity check, book Appendix A / §3.3):
  DRAM 6F²/bit, 1T1R 20F²/bit, 1S1R 4F²/bit (2 bits/cell as MLC) — at any matched process node,
  1S1R MLC is 3.0× denser than DRAM by cell arithmetic alone; the measured die-level 3.84× exceeds
  this because DRAM carries more real peripheral/spare-area overhead than the pure-cell bound
  ignores.

---

## 3. Simulation-Fidelity Audit (extended this cycle — two new items, both "found and fixed")

A systematic audit of the NVSim-to-NVMain flow (book §3.1.6), conducted against the raw simulator
sources and statistics files, found **thirteen silent failure modes** that bounded which
conclusions the evaluation could honestly draw — the last two found via a rigorous bibliography
verification pass on the book itself, not the simulator. **Eleven of thirteen have been repaired**,
with affected simulations re-run; every power and PDP figure in the current book derives from the
resulting repaired dataset.

| # | Failure mode | Status | Effect |
|---|---|---|---|
| 1 | Efficiency metric multiplied Watts by cycle counts from mismatched clock domains (800 MHz ReRAM vs. 2400 MHz DDR5) | **Fixed** | Biased comparison 3× against DDR5; PDP now computed in physical W·ns |
| 2 | `StandbyPower` config field written by the generator but never read by NVMain (dead config) | **Fixed** | Device-characterized leakage never reached the simulation at all |
| 3 | Generic standby-energy defaults (`Eactstdby`/`Eprestdby`) gave every non-volatile config the same ~68mW/rank floor | **Fixed** | This is the direct cause of the old "Power Flatline" |
| 4 | Reported "Total System Power" was the single most-loaded rank, not the module sum | **Fixed** | ReRAM spans 8 ranks, DDR5 spans 2 — per-rank reporting wasn't comparable across technologies |
| 5 | NVMain's power-down state machine is disabled in source (`HandleLowPower()` call site commented out) | **Open — top-priority future work** | Every ReRAM power figure in the book is worst-case *ungated*; DRAM/PCM model standard idle behavior |
| 6 | gem5 traces generated without L1/L2 caches or warmup (raw CPU-to-memory stream, first 10M instructions) | **Documented, not fixed** | Overstates memory pressure — conservative for endurance bounds, a caveat for absolute queueing magnitudes |
| 7 | DDR5 refresh machinery inherited unrescaled from a DDR3-1333 template | **Fixed** | Refresh fired 3.6× too often at 6.6× too little cost each; recalibrating to JEDEC JESD79-5 raised DDR5's refresh share to the final 33–45% band |
| 8 | DDR5 supply voltage was NVMain's stock default (1.5V) rather than the JEDEC-specified 1.1V; IDD currents also uncalibrated | **Fixed** | Corrected + calibrated to published vendor IDD tables (Micron/SK hynix, run as a two-vendor band — the Micron-ceiling side of this band has an unresolved reproducibility gap, see §6) |
| 9 | PCM baseline ran at 800 MHz — twice its cited 400 MHz basis (Lee et al. [11]) | **Fixed** | Roughly doubled PCM's reported latencies once corrected |
| 10 | ReRAM access energies written under config keys NVMain never reads (dead keys, same class of bug as #2) | **Fixed** | Every ReRAM config had silently used identical stock access-energy constants despite a real 5.7× read-energy difference between 1T1R/1S1R |
| 11 | Heterogeneous, unmatched host-CPU frequencies across technologies (800 MHz ReRAM host vs. 2/3 GHz others) with an unrescaled trace-admission cutoff | **Fixed** | Every technology now admits the identical request population per workload (matched-host correction: 250M-trace-cycle admission at a 3 GHz reference host, 83.33ms wall-clock for every configuration) |
| 12 | DDR5's `tCAS`/`tRCD`/`tRP` timing (34-34-34 cycles) was an unsourced placeholder, no citation or datasheet attached | **Fixed (2026-08-16)** | Cross-referenced SK hynix's public DDR5 part-number decoders against the standard DDR5-4800 (non-3DS) speed bin: real value is 40-39-39, a 15.7% increase in the CAS+RCD+RP timing component. Re-simulated; DDR5 total latency rose 2.3-8.6% across the 6-benchmark suite (diluted from 15.7% once blended with the unaffected `tRAS`/`tWR`/refresh timing); DDR5 power unaffected (this fix is timing-only, item 8's IDD calibration is untouched) |
| 13 | MLC read/write latency and energy penalty multipliers (3×/4×/3×/3×) were unsourced placeholders attributed to a citation ("EMBER Macro analytical heuristics") that does not support them in either of its publications | **Fixed (2026-08-16)** | Real measured multipliers located on the EMBER macro's full JSSC 2024 journal publication (missing from the ESSCIRC 2023 conference version cited alone): 1.917× read latency, 3.263× write latency, 1.1× read energy, 3.0× write energy (§2.3 above has the full derivation). All 8 MLC configurations re-simulated across all 6 benchmarks; MLC latency fell 20.6-34.9%, MLC dynamic power reordered relative to SLC in a workload-dependent way (§1.2 Finding 2 addendum) |

**Validation discipline:** every repair was checked against device-level anchors (0.0% error) or
exact predicted arithmetic. Items (12) and (13) were additionally checked by: re-running the full
9-config × 6-benchmark affected slice with a gate-keeper pass confirming every output file's
admission ceiling matched the documented matched-host methodology exactly; diffing every *untouched*
row (SLC, PCM, 2D/3D-DRAM controls — 66 rows across 5 technologies) against the pre-fix generation
and confirming byte-for-byte identity; and catching + correcting a genuine data-contamination bug
found mid-validation (a stale, never-fully-processed "DDR5 Micron-calibration" data slice that would
have corrupted the DDR5 geometric-mean PDP by ~26% instead of the real ~4.8%, had it not been
excluded before the final CSVs were generated).

---

## 4. Pipeline Architecture (updated: results generation, config-authority notes)

`mbmm_master.py` remains the Gate-Keeper: no simulation data is accepted without a complete
end-to-end pass. Architecture unchanged (`1_run_nvsim_hardware.py` → `2_extract_hardware_metrics.py`
→ `3_gen_nvmain_config.py` → `4_execute_simulation.py` → `process_metrics.py` →
`visualize_results.py`/`visualize_pareto.py`/`visualize_hero_graphs.py`, all through
`logging_config.py`'s unified logger).

**Known pipeline caveat found this cycle:** `mbmm_master.py`'s `--models` flag does not scope a run
to specific models — it is only checked to decide whether to enter the `--models`/`--all` code path
at all; once inside, the full 16-config ReRAM matrix + all 3 DRAM baselines run unconditionally for
every `--trace` given, regardless of what `--models` lists. For a genuinely scoped re-run (e.g.
re-simulating only the configs affected by a specific parameter fix), call `4_execute_simulation.py`
directly — its `--models` *is* respected. `README.md` was updated with an explicit callout on this;
the root README's own worked example previously reproduced the same wrong assumption.

**Matrix size:** 20 configurations (16 ReRAM variants: 4 technologies × 4 scales, + DDR5-4800, PCM,
2D_DRAM_example, 3D_DRAM_example) × 6 workloads = 120 stats files per full generation.

**Matched-host cycle budgets (post-repair, §3 item 11):** every configuration runs to the same
250M-trace-cycle admission at a fixed 3 GHz reference host — 83.33ms wall-clock for all (ReRAM
66.7M memory cycles at 800 MHz, PCM 33.3M at 400 MHz, DDR5's 200M unchanged at 2400 MHz).

**Current results generation: `results/system_v5/`** (supersedes `results/system_v4/`, which is
kept, not deleted, for diffability — the established archival pattern in this repo). `system_v5`
was produced by re-running only the 9 configs affected by items (12)/(13) (`DDR5_4800_DRAM` + the
8 MLC configs) and carrying every other technology's raw stats forward byte-identical from
`system_v4`, rather than a full 20-config re-run — the Global-Constraints-style scoping this repo
has settled on for parameter fixes that don't touch every technology.

---

## 5. Session History — Key Milestones (extended)

Formal session-summary `.docx` files (`resources/session summaries/`) stop at **Session 24**
(2026-05-22). Everything below Session 24 is reconstructed from git history, the book's own §3.1.6
narrative, and (now-archived) scoping/audit docs — not from a formal session summary. Treat session
*numbers* below Session 25/26 as approximate; dates and commit hashes are the reliable anchor.

| Session | Date | Milestone |
|---|---|---|
| 1–24 | 2026-02-21 → 2026-05-22 | See archived pre-hardfork context state for full detail; ends with the ETL refactor (`process_metrics.py` as single source of truth, `logging_config.py`, Hybrid-Empirical density adopted, Area Bug identified) |
| 25 (2026-05-26) | 2026-05-26 | Thesis Review audit: flagged OFMAP/IFMAP latency inversion, area-density convention mismatch, metric drift vs. pre-refactor pipeline, PCM-beats-DDR5 EDP inversion |
| 26 (2026-05-29) | 2026-05-29 | Re-audit: root-caused metric drift + OFMAP/IFMAP inversion to a single bug (`extract_total_execution_cycles()` matching `averageLatency` instead of `averageTotalLatency`); patched, all CSVs regenerated |
| — (2026-07-06, commit `9734bc0`) | 2026-07-06 | ETL latency/area-density extraction fix (queue-aware PDP, JSON-sourced area), visualizers aligned |
| — (2026-07-06, commits `2e1d213`/`3335bd4`) | 2026-07-06 | nvsim submodule maintenance (URL rename, CLAUDE.md docs) |
| — (2026-07-11, commit `923aa8f`) | 2026-07-11 | **The power-model repair**: real per-technology leakage derived from NVSim and wired into `Eactstdby`/`Eprestdby`; power extraction switched to module-sum across all ranks; dead `StandbyPower` config retired |
| — (2026-07-13, commit `c728173`) | 2026-07-13 | Investigated the throughput mechanism behind the book's §3.1.1 sustained-streaming sentence; matched-host `CPUFreq` correction (§3 item 11); `results/system_v4` established as canonical |
| — (2026-07-22/23) | 2026-07-22 | Full §3.1.6 fidelity audit completed (11 findings, 9 repaired); endurance analysis and ReadVoltage robustness sweep added; Project Book converted to a compile-verified Typst edition; this file's first hardfork regeneration |
| — (2026-08-16, this cycle) | 2026-08-16 | **Bibliography reference-verification audit**: every citation in the book checked against its actual cited source (6 independently-dispatched research passes). Found and fixed: an eReRAM commercial-production citation pointing at the wrong (2T2R research, not 1T1R production) paper; a page-range typo; an unsupported technical claim (Optane's DDR-T interface) cited to an article that never discusses it; a misattributed bandwidth-utilization figure; an over-claimed resistance-target citation. Found, via a much longer multi-round investigation (two AI research assistants, both of which initially overreached with unverifiable claims later retracted under direct primary-source checking), that the MLC read/write penalty multipliers were unsourced placeholders — real values eventually located on a second, journal-length publication of the same source macro. Separately found the DDR5 baseline's CAS/RCD/RP timing was *also* an unsourced placeholder. Both corrected (§3 items 12/13), the affected 9-config slice re-simulated, and every table/prose paragraph/figure in the book that cited the old numbers updated (turned out to be at least 6 separate restatements of the same headline figures scattered across the Abstract, five tables, and the Conclusion, plus 26 embedded figure images regenerated). A dedicated NVSim sensitivity sweep separately confirmed the leakage-class-separation finding (§1.2 Finding 2) is completely insensitive to the disputed resistance-target citation, closing that question without needing a re-simulation. This file regenerated to match |

---

## 6. Current Status

**No known active blocking bug.** The area-density extraction failure that an earlier doc version
described as open was fixed between Sessions 25–26; current values are the Finding 3 figures in
§1.3.

**Known, disclosed residual limitations** (from the book's §3.1.6, carried forward honestly rather
than fixed):
1. **Idle-power gating is unsimulated** (§3 item 5) — every ReRAM power figure is worst-case
   ungated. This is the single highest-leverage open item; restoring it is the top-priority future
   work item (book §4.1).
2. **gem5 trace provenance is weaker than ideal** (§3 item 6) — no L1/L2 caches, no warmup,
   confirmed for gcc/lbm but the GPT-2 SCALE-Sim trace's provenance could not be tied to a preserved
   run (AlexNet's TPU-v1 256×256 output-stationary configuration is confirmed; GPT-2 is not).
3. **Open-loop trace replay**: no CPU/accelerator feedback path, so every latency figure is a
   memory-subsystem quantity, not a projected end-to-end application slowdown.
4. **DDR5 power is reported as a two-vendor calibration band** (Micron ceiling / SK hynix floor)
   rather than a single point value. **The Micron-ceiling side of this band has a known
   reproducibility gap**: no live NVMain config for the Micron-only calibration survives on disk
   (it was produced by a one-off manual edit of the shared DDR5 config, run, and reverted — not a
   repeatable pipeline step), so the Micron-ceiling PDP figure quoted in the book's headline-reframe
   paragraph (150.9 W·ns) predates this cycle's item (12) DDR5 timing correction and has *not* been
   re-verified against it. This is a pre-existing gap (first flagged 2026-07-13, `results/
   cycle8_matched_host_report.md`), not something this cycle introduced, but it is now stale in a
   way that's worth resolving: reconstructing a proper, saved Micron-only config and re-running it
   is the cleanest fix, flagged for a future session.

---

## 7. Pending Documentation / Narrative Items

**New this cycle:**
1. **Micron-calibration DDR5 config reconstruction** (see §6 item 4 above) — no live config exists;
   the Micron-ceiling PDP figure in the book is now known-stale relative to the item (12) timing
   correction.
2. **This file's own prior version** (the 2026-07-22 hardfork, superseded by this regeneration) has
   not yet been moved to `archive/root_docs/` under the naming convention used for the version
   before it (`MBMM_AI_Context_State_pre-hardfork_2026-07-22.md`) — worth doing in a future
   housekeeping pass so the superseded-version chain stays consistent, though nothing currently
   depends on it being archived promptly.
3. **`archive/README.md`** has not yet received a dated entry for this cycle's DDR5-timing /
   MLC-multiplier correction and re-simulation, unlike every other major correction cycle in this
   repo's history — worth adding for consistency with the established documentation pattern, though
   this file and the book's own §3.1.6 items (12)/(13) already carry the full record.

No other pending documentation items are currently tracked in this file.

---

*Document regenerated via `mbmm_hardfork` from: `documents/MBMM_Book_Typst/Project_Book.typ`
(canonical, compile-verified, post-reference-audit edition). Cross-referenced against: git log,
`results/cycle8_matched_host_report.md`, `docs/superpowers/plans/2026-07-29-book-reference-fixes.md`
(this cycle's working plan, with full task-by-task execution notes), and the prior (2026-07-22)
version of this file.*
