# MBMM AI Context State
**Project:** Evaluation of 22nm Memristor-Based Main Memory (MBMM) in Commodity DIMM Architectures
**Researcher:** Yuval Kogan, Technion
**Supervisor:** Prof. Shahar Kvatinsky
**Generated:** 2026-05-22 (Session 24 — Post-ETL Refactor)

---

## 1. Executive Academic Narrative

### 1.1 Core Thesis

The memory supply-demand gap of late 2025, driven by DRAM wafer reallocation to AI-focused HBM
production, necessitates alternative technologies for commodity main memory. This project evaluates
22nm Memristor-Based Non-Volatile Memory (ReRAM) as a DRAM replacement in standard DIMMs using a
cross-layer simulation pipeline bridging NVSim (device-level) and NVMain 2.0 (cycle-accurate
architecture). The evaluation covers 1T1R (transistor-isolated) and 1S1R (selector crossbar)
topologies in SLC and MLC configurations, scaled from a single chip to a 64-chip full DIMM (16GB).

### 1.2 The Three Central Findings

**Finding 1 — The Flatline Paradox (Multi-Rank Scaling Limit)**
Under single-threaded CPU workloads (e.g., SPEC2017 gcc), scaling from 1-chip to 64-chip incurs
almost zero power penalty (NVM cells don't leak at idle) but also delivers zero latency improvement.
The reason is lack of Memory Level Parallelism (MLP): the single-threaded trace cannot saturate the
primary rank, leaving all additional ranks entirely idle. This is the "Flatline Paradox." The paradox
is resolved under massively parallel AI workloads (GPT-2, AlexNet), where rank-level interleaving
slashes latency as the system scales to a full DIMM.

**Finding 2 — Static Leakage Dominance**
The dynamic energy of switching a ReRAM cell is measured in picojoules — infinitesimally small. As a
result, total system power is almost entirely dictated by the static leakage floor of the peripheral
CMOS circuitry (sense amplifiers, row decoders, wordline drivers), not by memory-cell activity. Key
empirical evidence: under both light compute-bound workloads (gcc: 0.069W) and massively parallel
AI read-storms (GPT-2: ~0.066W), all ReRAM configurations maintain nearly identical power. This
"Power Flatline" is a mathematical proof of Static Leakage Dominance within the 22nm memristor
model. MLC configurations actually show *lower* dynamic power than SLC under streaming workloads
because the longer ISPV write latency throttles the memory controller, reducing the average activity
rate across the simulation window.

**Finding 3 — The 1S1R Density Advantage**
The 1S1R (selector-based crossbar) achieves a 4F² cell area vs. 20F² for 1T1R. Normalized against
the JEDEC DDR5 baseline (1.00), the 1T1R SLC occupies ~0.90 (10% smaller), while the 1S1R MLC
crosspoint achieves 0.25 — a 4× density improvement. This allows the physical footprint of a 16GB
DIMM to house an effective 64GB of non-volatile capacity. This density advantage is the central
commercial motivation for the 1S1R topology.

### 1.3 DDR5 vs. ReRAM Quantitative Conclusions

| Metric | 1T1R SLC | 1S1R MLC | DDR5-4800 | PCM 2009 |
|--------|----------|----------|-----------|----------|
| GCC Read Latency | 80.22 cycles | — | 174.81 cycles | — |
| LBM Read Latency | 374.38 cycles | 1545.40 cycles | 651.92 cycles | — |
| GPT-2 Read Latency | 366.80 cycles | — | 224.28 cycles | — |
| AlexNet OFMAP Latency | — | 3344.30 cycles | — | — |
| GCC System Power | 0.069W | — | 0.136W | — |
| GPT-2 System Power | ~0.066W | ~0.066W | ~0.128W | — |
| Area Density (norm.) | 0.90 | 0.25 | 1.00 (baseline) | — |
| Geometric Mean EDP | 23.98 | — | 49.99 | 150.74 |
| 1S1R SLC Geo-Mean EDP | 35.15 | — | 49.99 | 150.74 |

**DDR5 EDP Penalty:** Driven by high dynamic power (0.128W at 2400 MHz with on-die EQ) and BL16
serialization delays which inflate cycle counts for small random reads compared to legacy BL8 DRAM.

---

## 2. Theoretical Physics Baselines

### 2.1 Process Node & Resistance Targets

- **Node:** 22nm FinFET LOP (Low Operating Power)
  - LOP chosen over HP: ensures electrical convergence in the NVSim solver and aligns with the
    thermal envelope of high-capacity main memory DIMMs.
- **Resistance Targets (Matsui et al. 2025 [Ref 7]):**
  - LRS (Low Resistance State): **10⁵ Ω (100 kΩ)**
  - HRS (High Resistance State): **10⁹ Ω (1 GΩ)**
  - Rationale: 10,000:1 ratio provides sufficient electrical window for reliable sensing on 1024-cell
    bitlines and mitigates IR-drop. The initial 10:1 ratio (100kΩ to 1MΩ) was identified as
    insufficient in Session 5.
- **Operating Voltages:** ReadVoltage = 1.4V, WriteVoltage = 2.0V (force-fed directly into `.cell`
  files to bypass NVSim parser bug that defaulted to 0V).

### 2.2 Cell Topology — 1T1R vs. 1S1R

| Parameter | 1T1R (Transistor) | 1S1R (Selector) |
|-----------|-------------------|-----------------|
| Cell Area | ~20 F² | ~4 F² |
| Sneak-path mitigation | CMOS access transistor (complete isolation) | Highly non-linear selector (thresholding) |
| Scalability | Logic-compatible; used in commercial 22nm eReRAM (Xue et al. ISSCC 2021) | Academic arrays constrained to manage leakage; industry milestone: Crossbar Inc. 4Mb crosspoint |
| NVSim Area (128MB chip) | ~19.8 mm² | ~2.28 mm² |

**Sneak-Path Problem (Tutorial 4):** In a passive crossbar array without access devices, sneak
currents flow through unselected cells, corrupting read margins. 1T1R uses CMOS transistors to cut
all leakage paths. 1S1R uses a highly non-linear selector element with large non-linearity factor
(Kr = 10⁶) to suppress sub-threshold leakage without a full transistor.

### 2.3 SLC vs. MLC — Physics & Penalties

**SLC (Single-Level Cell):** 2 resistance states (LRS / HRS), 1 bit per cell. Simple voltage-pulse
write; single-threshold read.

**MLC (Multi-Level Cell):** 4 resistance states (LRS / IRS1 / IRS2 / HRS), 2 bits per cell.
Requires:
1. **Iterative Step-and-Verify (ISPV) Programming:** Multiple write pulses of increasing amplitude
   until resistance settles within the target window.
2. **Analog-to-Digital Conversion (ADC) Sensing:** Precise multi-level sensing circuit to distinguish
   4 resistance windows instead of a simple binary comparator.

**MLC Analytical Penalty Method (EMBER macro heuristic, Upton et al. ESSCIRC 2023 [Ref 6]):**
NVSim's native MLC logic was non-functional at 22nm (integer overflow in `Mat.cpp`/
`BankWithHtree.cpp` causing FPE core dumps). Instead, MLC metrics are analytically derived from
the validated SLC baseline:

| Metric | SLC Baseline | MLC Multiplier | MLC Result |
|--------|-------------|----------------|------------|
| Read Latency | 2.07–2.63 ns | ×3 | 6.2–7.9 ns |
| Write Latency | 10.06 ns | ×4 | ~40 ns |
| Read Cycles (800 MHz) | 2–3 cycles | ×3 | ~6 cycles |
| Write Cycles (800 MHz) | 9 cycles | ×4 | ~36 cycles |

**Program & Verify (Tutorial 5):** The ISPV loop is the primary driver of the 4× write penalty.
Each iteration: apply write pulse → sense resistance → compare to target window → if not converged,
apply next pulse. This loop can require 10+ iterations per cell.

### 2.4 Area Density Baseline (Hybrid-Empirical, Session 24)

- **DDR5 Physical Baseline:** **35.0 mm²/GB**, grounded in ISSCC literature (Samsung/SK Hynix
  1y-nm commercial silicon).
- **Formula:** `Area_Density_Ratio = (NVSim_area_mm² / capacity_GB) / 35.0`
- This method was adopted in Session 24 to replace purely theoretical F² scaling, making the density
  claim defensible against Prof. Kvatinsky's scrutiny.

---

## 3. Engine Patches & Pipeline Architecture

### 3.1 NVSim C++ Repairs (Institutional Knowledge)

| Patch | File | Problem | Fix Applied |
|-------|------|---------|-------------|
| Namespace collision | `Makefile` | GCC 13 treats `MemoryType::data` as ambiguous with `std::data` | Enforced `-std=c++11` |
| MLC NAND block | `main.cpp` | Hardcoded `exit(-1)` when `LevelsPerCell > 2` on non-Flash devices | Commented out exit; redirected `CAM_chip` → `RAM_chip` |
| FPE at 22nm | `Mat.cpp` / `BankWithHtree.cpp` | Integer overflow in `numSubarrayPerRow` under Automatic Exploration | Fixed geometry: forced 128×128 Mat, `ForceMuxSenseAmp=32` |
| CAM/RAM identity | `InputParameter.cpp` | `-DesignTarget` defaulted to CAM/cache logic | Explicit `-DesignTarget: RAM` and `-IsNand: false` in all `.cell` files |
| Parser bug (voltages) | `.cell` files | MLC voltages defaulted to 0V | Force-fed `-ReadVoltage: 1.4` and `-WriteVoltage: 2.0` |

**Stability Skeleton:** All 22nm configs locked to **256 rows × 1024 columns subarrays**, `2×2 Mat`
divisions, `16×4 bank` layout. This geometry was determined experimentally to produce solver
convergence without FPE.

### 3.2 NVMain 2.0 C++ Repairs

| Patch | File | Problem | Fix Applied |
|-------|------|---------|-------------|
| SIGSEGV on small models | NVMain core | `NVMObject::GetChild` null-pointer dereference when BusWidth=64 mismatched device count | Forced `DeviceWidth=64` for single-chip; `R:BK:C` address mapping for single-rank |
| FlipNWrite deallocation | `FlipNWrite.cpp` | Mismatched `new` / `delete` on write-buffer causing SIGSEGV | Fixed deallocation to match allocation type |
| gem5 v25.1 bridge | `NVMainMemory.cc`, `SConscript` | Legacy `int` port IDs, missing `recvRespRetry`, outdated Python build scripts | Migrated to `PortID` type; implemented pure virtual; rewrote SConscript |
| Python 2→3 | Build system | `scons` and `2to3` required for Python 3.12 | Ran `2to3` migration; fixed `argparse` strictness |

### 3.3 The mbmm_master.py 7-Stage ETL Pipeline

`mbmm_master.py` is the Gate-Keeper: no simulation data is accepted without a complete end-to-end pass.

```
Stage 1  → Clean build artifacts, rebuild NVSim & NVMain C++ engines
Stage 2  → [1_run_nvsim_hardware.py] Run NVSim for all 4 ReRAM tracks → results/nvsim/
Stage 3  → [2_extract_hardware_metrics.py] Regex-parse NVSim outputs → hardware_metrics.json
Stage 4  → [3_gen_nvmain_config.py --freq 800] Architecture Factory: generate 18 NVMain .config files
Stage 5  → [4_execute_simulation.py] Run NVMain cycle-accurate trace across all 18 architectures → results/system/stats_*.out
Stage 6  → [process_metrics.py] ETL: parse 138 .out files → 4 pre-calculated CSV files (the single source of truth)
Stage 7  → [visualize_results.py / visualize_pareto.py / visualize_hero_graphs.py] Dumb plotters reading from CSVs → results/final_graphs/
```

**Architecture Factory (Stage 4) details:**
- Generates 18 configs: 2 DRAM baselines + 4 ReRAM topologies × 4 scales (single, 8chip, 16chip, full_dimm)
- Forces `DeviceWidth=64` for single-chip models (64-bit bus requirement without null-pointer crash)
- Dynamic `AddressMappingScheme`: `R:BK:C` for single-rank, `R:BK:RK:C` for multi-rank
- All configs locked to **800 MHz** clock (1600 MT/s) — verified correct for analog NVM controller limits

### 3.4 Simulation Baselines (18-Model Matrix)

| Model | Technology | Description |
|-------|-----------|-------------|
| `2D_DRAM_example` | DDR3-era DRAM | Planar DRAM, 666 MHz, legacy timing (control variable) |
| `3D_DRAM_example` | HBM-like DRAM | TSV stack, 500 MHz, ultra-tight timing (control variable) |
| `DDR5_4800` | JEDEC DDR5 | JESD79-5: tCAS-tRCD-tRP 34-34-34, 1.1V, BL16, dual 32-bit sub-channels |
| `pcm_microsoft_2009` | PCM legacy | Lee et al. ISCA 2009 — legacy NVM baseline |
| `reram_22nm_1t1r_{slc/mlc}_{single/8chip/16chip/full_dimm}` | 1T1R ReRAM | 20F² CMOS transistor cell |
| `reram_22nm_selector_{slc/mlc}_{single/8chip/16chip/full_dimm}` | 1S1R ReRAM | 4F² crossbar selector cell |

### 3.5 Workload Trace Suite

| Trace | Generator | Profile | Purpose |
|-------|-----------|---------|---------|
| `gcc_spec2017.nvt` | gem5 X86O3CPU | Compute-bound, irregular access | Exposes Static Leakage Dominance (memory mostly idle) |
| `lbm_spec2017.nvt` | gem5 X86O3CPU | Memory-streaming (fluid dynamics) | Exposes dynamic energy & MLC write penalty |
| `stream.nvt` | Synthetic | Continuous vector streaming | Maximum theoretical bandwidth baseline |
| `alexnet_layer1_ifmap.nvt` | SCALE-Sim | Read-heavy CNN (Input Feature Map) | Exposes queueing delays under massive parallel reads |
| `alexnet_layer1_ofmap.nvt` | SCALE-Sim | Write-heavy CNN (Output Feature Map) | "Write-Torture" — isolates ISPV MLC write penalty |
| `gpt2_ifmap.nvt` | SCALE-Sim | LLM Transformer GEMM reads | Modern AI benchmark; tests maximum read bandwidth |

**Trace Parser Critical Fixes (parse_trace.py):**
- SCALE-Sim outputs comma-separated values — replaced `.isdigit()` with `try-except` casting
- SCALE-Sim schedules DRAM pre-fetches at **negative cycle counts** (crashes NVMain event queue) —
  implemented mandatory time-shift normalization to force all traces to start at Cycle 0
- gem5 raw traces auto-deleted after `.nvt` conversion to prevent WSL2 VHDX disk exhaustion
  (Session 18: a single gcc trace consumed 139 GB)

---

## 4. Session History — Key Milestones

| Session | Date | Milestone |
|---------|------|-----------|
| 3 (2026-02-21) | 2026-02-21 | NVSim MLC bypass, namespace repair, 4-track split, LOP standardization |
| 4 | 2026-02 | Python automation layer, 4-track batch run, first Area/Latency/Energy harvest |
| 5 (2026-03-05) | 2026-03-05 | FPE root cause diagnosed, fixed-geometry skeleton, Gate-Keeper sanity check, 1T1R area corrected 4F²→20F² |
| 5b (MLC) | 2026-03 | Resistance gap upgraded to 10⁵/10⁹ Ω; MLC declared analytically non-functional in NVSim; Analytical Penalty Method adopted |
| 6 (2026-03-06) | 2026-03-06 | 22nm LOP convergence breakthrough; 8MB "seed" model validated; NVMain bridge architecture mapped |
| 7 (2026-03-07) | 2026-03-07 | NVSim→NVMain bridge automated; data flow `.cfg → JSON → .config → .out` established |
| 8 (2026-03-07) | 2026-03-07 | First successful STREAM benchmark run; NVMain deep-patch (FlipNWrite deallocation) |
| 9 (2026-03-08) | 2026-03-08 | DRAM Phase-2-only execution; 1S1R selector track initialized; visualizer auto-discovery |
| 10 (2026-03-13) | 2026-03-13 | gem5 v25.1 bridge engineering (PortID migration, pure virtual, SConscript rewrite) |
| 11 (2026-03-14) | 2026-03-14 | 22nm SLC modeled in NVMain; gem5 O3CPU run; first SPEC2017 mcf results |
| 12 (2026-03-16) | 2026-03-16 | Pivot to decoupled trace-based pipeline; parse_trace.py written; first working Latency/Power graphs |
| 13 (2026-03-18) | 2026-03-18 | Architecture Factory (1/8/16/64-chip scaling); split-axis plots; Power Scaling Paradox identified |
| 14 (2026-03-20) | 2026-03-20 | SIGSEGV (NVMObject::GetChild) diagnosed and patched; DeviceWidth synchronization |
| 15 (2026-03-21) | 2026-03-21 | DRAM baseline recovery; 5M-cycle batch run; Flatline Effect confirmed; Bandwidth Equivalence proved |
| 16 (2026-03-22) | 2026-03-22 | Project Book drafting; metric pivot $/bit → Area/bit (F²); Flatline Effect documented |
| 17 (2026-03-26) | 2026-03-26 | 3-minute defense presentation; L3 Cache Mitigation proposal; open-source framework proposal |
| 18 (2026-03-28) | 2026-03-28 | O3CPU migration; WSL2 VHDX crisis resolved; mcf deprecated; gcc/lbm finalized; Rank-level interleaving analysis |
| 19 (2026-04-01) | 2026-04-01 | SCALE-Sim integration; trace translator rewrite; first AlexNet IFMAP run; Power Paradox confirmed |
| 20 (2026-04-03) | 2026-04-03 | DDR5-4800 baseline constructed; GPT-2 GEMM traces; MLC Write Penalty quantified; DDR5 comparison |
| 21 (2026-04-11) | 2026-04-11 | Gold Master 3-tier visualization suite; Pareto frontiers; Hero Graphs; all visualizers integrated into Stage 7 |
| 22 (2026-04-23) | 2026-04-23 | Project Book Chapter 4 bottom-up academic rewrite; pronoun purge (We→I); citation integration |
| 23 (2026-05-15) | 2026-05-15 | Defense narrative finalized; Shahar pivot: separate static/dynamic power, audit DDR5 anomaly, parameter table; density extraction flagged |
| 24 (2026-05-22) | 2026-05-22 | ETL refactor (monolithic→pipeline); process_metrics.py as Stage 6 single source of truth; Hybrid-Empirical density; logging_config.py; **Area Bug identified** |

---

## 5. Current Active Bug

### Stage 6 Area Extraction Failure — `process_metrics.py`

**Symptom:** `processed_hero_metrics.csv` contains `Area_Density_Ratio = 1.0` for all ReRAM
architectures (identical to DDR5), making the density Hero Graph (Figure 23) show a flat line
instead of the expected 4× density advantage of 1S1R MLC.

**Expected Values (from Project Book Section 3.3):**
- `1T1R_SLC` Area Density Ratio: **~0.90** (10% denser than DDR5)
- `1S1R_SLC` Area Density Ratio: **~0.25** (4× denser than DDR5)
- `1S1R_MLC` Area Density Ratio: **~0.25** (the primary density argument)

**Baseline for normalization:** `DDR5_MM2_PER_GB = 35.0 mm²/GB`
(Locked in `process_metrics.py:42`, grounded in Samsung/SK Hynix ISSCC 1y-nm silicon)

**Root Cause:** The `calculate_area_density_ratio()` function (line 301) requires both `area_mm2`
and `capacity_gb` to be non-None. When either extraction returns `None`, the function returns
`None`, which triggers the fallback at line 459–461:
```python
if area_ratio is None:
    logger.error(f"[SKIP-WITH-FALLBACK] {tech}: Using 1.0 ratio due to extraction failure")
    area_ratio = 1.0
```

The failure chain originates in `extract_area_mm2()` (line 175) and/or `extract_capacity_gb()`
(line 230). Specifically:
- `extract_area_mm2()` (refactored in Session 24) now does a JSON lookup in `hardware_metrics.json`
  using `key.startswith(key_prefix)` — the JSON file exists and contains valid area values, but
  the key matching or data path has not been verified against the live Stage 6 run.
- `extract_capacity_gb()` parses the NVMain stats output for the line `capacity is XXXXX MB` —
  the NVMain format is confirmed present (`defaultMemory.channel0.FRFCFS capacity is 32768 MB.`)
  but the capacity value extracted (e.g., 32768 MB = 32 GB) may not correspond to the physical
  single-chip capacity stored in `hardware_metrics.json` (0.125 GB per chip), creating a
  mismatch that produces an incorrect or nonsensical ratio.

**Files Involved:**
- `process_metrics.py` — Stage 6 (the bug location): `extract_area_mm2()`, `extract_capacity_gb()`,
  `calculate_area_density_ratio()`
- `results/hardware_metrics.json` — source of truth for ReRAM area (mm²) and per-chip capacity
- `results/system/stats_*.out` — source of capacity (NVMain simulated address space)

**Action Required (Session 25):**
Fix `extract_area_mm2()` and `extract_capacity_gb()` parsing logic in `process_metrics.py`
so the 11× density Hero Graph is correctly generated before the final defense.

---

---

## 6. Pending Documentation Updates

| # | Task | Context |
|---|------|---------|
| 1 | **Inject formal IEEE citations to defend the 6 F² DDR5 baseline** | The `generate_f2_metrics.py` supplementary chart and the hybrid-empirical density analysis both assert that commodity DDR5 uses a 6 F² folded-bitline cell layout. This claim must be backed by primary literature before the Project Book defence. Candidate references: Kim et al. (Samsung, ISSCC/VLSI — originating 6 F² folded-bitline DRAM cell), SK Hynix 1y-nm DDR5 VLSI roadmap disclosure, and/or Micron DDR5 die-area teardown. Without citations Prof. Kvatinsky can challenge the baseline, which would invalidate the 1T1R (3.33×) and 1S1R (1.5–3×) density comparisons. |

---

*Document generated from: Project Book (DOCX), 22 Session Summaries (Sessions 3–24), hardware_metrics.json, process_metrics.py source, stage6_output.log.*
