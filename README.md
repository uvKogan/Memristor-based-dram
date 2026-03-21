# MBMM: Memristor-Based Main Memory Architecture Evaluation

This repository provides a full-stack, cross-layer simulation pipeline for evaluating emerging Non-Volatile Memory (NVM) technologies—specifically 22nm ReRAM (Resistive RAM)—as commodity main memory replacements for traditional DRAM.

The pipeline bridges **NVSim** (for circuit-level Area, Latency, and Energy characterization) with **NVMain 2.0** (for cycle-accurate architectural memory timing), fed by decoupled memory traces generated via **gem5**.

## 🏗️ System Architecture & Data Flow

Our simulation framework decouples the CPU simulation from the detailed memory modeling to ensure stability and rapid design space exploration:

1. **Trace Generation (gem5):** Executes benchmark binaries (e.g., SPEC2017 `505.mcf`) using standard native memory controllers, outputting raw memory transaction logs.
2. **Trace Parsing (`parse_trace.py`):** Converts gem5 debug logs into NVMain-compatible `.nvt` trace files, handling bus ticks and correct 128-byte data padding for SLC/MLC constraints.
3. **Architecture Factory (`3_gen_nvmain_config.py`):** Dynamically scales hardware definitions from single-chip devices up to 64-chip (16GB) Full DIMMs.
4. **Orchestration & Simulation (`mbmm_master.py`):** The primary Gate-Keeper. It rebuilds the C++ engines, validates sanity checks, and feeds the trace into NVMain across a matrix of 18 configurations (2D/3D DRAM, 1T1R, 1S1R, SLC, and MLC).
5. **Visualization (`visualize_results.py`):** Automatically extracts cycle latency and power metrics from the simulation outputs and generates publication-ready comparative charts.

## 🚀 How to Run the Pipeline

The pipeline is currently orchestrated via the master script. To replicate the baseline findings:

**1. Generate the System Configurations**
```bash
python3 3_gen_nvmain_config.py --freq 800

**2. Run the Architectural Batch (50M Cycles)
```bash
python3 mbmm_master.py --cycles 50000000 --trace benchmarks/mcf_spec2017.nvt --models \
2D_DRAM_example 3D_DRAM_example \
reram_22nm_1t1r_slc_single reram_22nm_1t1r_slc_8chip reram_22nm_1t1r_slc_16chip reram_22nm_1t1r_slc_full_dimm \
reram_22nm_1t1r_mlc_single reram_22nm_1t1r_mlc_8chip reram_22nm_1t1r_mlc_16chip reram_22nm_1t1r_mlc_full_dimm \
reram_22nm_selector_slc_single reram_22nm_selector_slc_8chip reram_22nm_selector_slc_16chip reram_22nm_selector_slc_full_dimm \
reram_22nm_selector_mlc_single reram_22nm_selector_mlc_8chip reram_22nm_selector_mlc_16chip reram_22nm_selector_mlc_full_dimm
```

**3. Generate Analytical Graphs
```bash
python3 visualize_results.py
```

---

## 🗺️ Research Roadmap & Development Vectors

### Phase 1: Workloads & Methodologies
- [x] Integrate SPEC2017 (505.mcf) for worst-case pointer-chasing validation.
- [ ] **AI Workload Integration:** Implement MLPerf inference traces or GEMM kernels to evaluate ReRAM's strength in read-heavy, dense parallel operations.
- [x] **Simulation Depth:** Established steady-state execution windows (50M+ cycles) to observe rank-contention and idle leakage.

### Phase 2: Architectural Baselines & Comparisons
- [x] Baseline: 2D DRAM
- [x] Baseline: 3D DRAM (HBM-style)
- [ ] **Modern Baseline:** Implement a DDR5-4800 configuration (16-beat bursts, dual 32-bit sub-channels).
- [ ] **Historical NVM Baseline:** Benchmark our ReRAM DIMM against the seminal Qureshi/Microsoft Phase Change Memory (PCM) architecture.

### Phase 3: Advanced ReRAM Modeling
- [x] **1T1R SLC:** Modeled 20 F^2 logic-compatible cells.
- [x] **1T1R MLC (Multi-Level Cell):** Modeled higher density tradeoffs using the Analytical Penalty Method (3x Read / 4x Write) to account for Iterative Step-and-Verify (ISPV) overhead.
- [x] **1S1R Cross-point (Selector):** Modeled 4 F^2 ultra-dense architectures, mitigating "sneak path" leakage via selector non-linearity.
- [ ] **Native MLC Logic:** Resolve the NVSim C++ FPE bug to replace analytical penalties with native circuit-level ADC characterization.

### Phase 4: Project DevOps
- [x] Decouple gem5 as a clean submodule.
- [x] Establish trace ignoring (`.gitignore`) to maintain repository hygiene.
- [x] **End-to-End Automation:** Consolidate execution into the `mbmm_master.py` Gate-Keeper.

### Phase 5: Literature Validation & Parameter Tuning
- [x] **Empirical Grounding:** Audited resistance targets (10^5/10^9 Ohm) against Matsui et al. (2025).
- [x] **MLC Verification:** Validated penalty heuristics against the 2024 EMBER Macro.
- [ ] **Endurance-Aware Scheduling:** Explore wear-leveling algorithms to mitigate the 10K-cycle endurance limits of 22nm cells when used as Main Memory.