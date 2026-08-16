# MBMM: Memristor-Based Main Memory Architecture Evaluation

This repository provides a full-stack, cross-layer simulation pipeline for evaluating emerging Non-Volatile Memory (NVM) technologies—specifically 22nm ReRAM—as commodity main memory replacements for traditional DRAM.

## 🏗️ System Architecture & Data Flow
1. **Trace Generation (gem5 / SCALE-Sim):** Executes benchmark binaries (`gcc`, `lbm`) using an Out-of-Order CPU (`X86O3CPU`) and L1/L2 caches to capture real Memory Level Parallelism (MLP). Also includes ML/LLM specific traces via SCALE-Sim.
2. **Trace Parsing (`parse_trace.py`):** Converts gem5 raw logs into NVMain-compatible `.nvt` files, handling 128-byte data padding. *Includes automated raw-file deletion to prevent WSL storage bloat.*
3. **Architecture Factory (`3_gen_nvmain_config.py`):** Dynamically scales hardware definitions from single-chip up to 64-chip (16GB) Full DIMMs.
4. **Orchestration (`mbmm_master.py`):** The Gate-Keeper. Runs the traces through NVMain across multiple configurations (DDR5, 2D/3D DRAM, PCM, 1T1R, 1S1R, SLC, MLC).
5. **Visualization Suite (Stage 6):** Automatically extracts metrics and organizes publication-ready charts into `results/final_graphs/`:
   - `visualize_results.py`: Diagnostic Bar Charts (Latency, Power, EDP).
   - `visualize_pareto.py`: Multi-objective Pareto Frontiers mapping scaling trajectories.
   - `visualize_hero_graphs.py`: Global Average EDP and Theoretical Density comparisons.

## 🚀 How to Run the Pipeline

The pipeline is currently orchestrated via the master script. To replicate the baseline findings:

**1. Extract Traces**
```bash
# For standard workloads (gem5 Out-of-Order):
/path/to/gem5.opt --debug-flags=MemCtrl --debug-file=raw_trace.txt fs.py --cpu-type=X86O3CPU --caches --l2cache

# For AI/ML Workloads (SCALE-Sim):
export PYTHONPATH=$PWD:$PYTHONPATH
python3 simulators/SCALE-Sim/scalesim/scale.py -c configs/google.cfg -t topologies/conv_nets/alexnet.csv -p benchmarks/ml_trace_output/
```

**2. Parse Traces & Clean Disk
```bash
python3 parse_trace.py raw_trace.txt benchmarks/workload.nvt
```

**3. Generate Configs & Run Batch
```bash
python3 3_gen_nvmain_config.py --freq 800
python3 mbmm_master.py --cycles 50000000 --trace benchmarks/workload.nvt --models DDR5_4800_DRAM pcm_microsoft_2009 reram_22nm_selector_slc_full_dimm # ... (add other desired models)
```

(Note: mbmm_master.py will automatically call the 3 visualization scripts at the end of the simulation batch).

**⚠️ `--models` does not scope the run.** In `mbmm_master.py`'s `main()`, `args.models` is only checked to decide whether to enter the `--models`/`--all` branch at all (`if args.models or args.all:`) — the actual model list is never read again inside that branch. Once inside, it unconditionally runs the full 16-config ReRAM matrix (1T1R/selector × SLC/MLC × single/8chip/16chip/full_dimm) plus all 3 DRAM baselines (2D/3D/DDR5), for every `--trace` given, regardless of what `--models` lists. If you need a genuinely scoped re-run of specific models (e.g. re-simulating only the configs affected by a parameter fix), call `4_execute_simulation.py --models <names> --trace <file> --cycles <n>` directly instead — that script's `--models` *is* respected (confirmed in its source: `elif args.models: target_models = args.models`). Just ensure Stage 2 (`2_extract_hardware_metrics.py`) and Stage 3 (`3_gen_nvmain_config.py --freq 800`) have already run first if your fix touches hardware-metric-derived `.config` files, since `4_execute_simulation.py` skips NVSim/Stage-1 entirely for any model whose name contains `DRAM` or `_mlc` and expects the `.config` file to already exist.

---

## 🗺️ Research Roadmap & Development Vectors

- [x] Integrate SPEC2017 (gcc, lbm) for high-bandwidth and instruction-heavy validation.
- [x] Model 1T1R SLC/MLC and 1S1R Cross-point architectures.
- [x] Automate WSL storage hygiene and trace parsing.
- [x] AI Workload Integration: Implemented MLPerf inference traces via SCALE-Sim to benchmark backpressure limits and evaluate ReRAM's strength in read-heavy, dense parallel operations.
- [x] LLM Workload Integration: Added pure GEMM traces (GPT-2) via SCALE-Sim to test parallel inference read-storms.
- [x] Power Scaling Resolution: Audited NVMain configurations to resolve the StandbyPower leakage paradox across multi-chip DIMMs.
- [x] Modern Baselines: Engineered a JEDEC-compliant DDR5-4800 dual-channel baseline for direct ReRAM comparison, alongside Microsoft PCM 2009.
- [x] Automated Data Analytics: Engineered a self-organizing 3-tier visualization suite (Pareto Frontiers, EDP, Density).
- [ ] Rank Interleaving Analysis: Investigate custom rank/bank topologies and memory controller queue depth.