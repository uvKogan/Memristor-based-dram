# MBMM: Memristor-Based Main Memory Architecture Evaluation

This repository provides a full-stack, cross-layer simulation pipeline for evaluating emerging Non-Volatile Memory (NVM) technologies—specifically 22nm ReRAM—as commodity main memory replacements for traditional DRAM.

## 🏗️ System Architecture & Data Flow
1. **Trace Generation (gem5):** Executes benchmark binaries (`gcc`, `lbm`) using an Out-of-Order CPU (`X86O3CPU`) and L1/L2 caches to capture real Memory Level Parallelism (MLP).
2. **Trace Parsing (`parse_trace.py`):** Converts gem5 raw logs into NVMain-compatible `.nvt` files, handling 128-byte data padding. *Includes automated raw-file deletion to prevent WSL storage bloat.*
3. **Architecture Factory (`3_gen_nvmain_config.py`):** Dynamically scales hardware definitions from single-chip up to 64-chip (16GB) Full DIMMs.
4. **Orchestration (`mbmm_master.py`):** The Gate-Keeper. Runs the traces through NVMain across 18 configurations (2D/3D DRAM, 1T1R, 1S1R, SLC, MLC).
5. **Visualization (`visualize_results.py`):** Automatically scales and extracts cycle latency/power metrics into publication-ready charts.

## 🚀 How to Run the Pipeline

The pipeline is currently orchestrated via the master script. To replicate the baseline findings:

**1. Extract Traces (gem5 Out-of-Order)**
```bash
*For standard workloads (gem5 Out-of-Order):*
/path/to/gem5.opt --debug-flags=MemCtrl --debug-file=raw_trace.txt fs.py --cpu-type=X86O3CPU --caches --l2cache

*For AI/ML Workloads (SCALE-Sim):*
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
python3 mbmm_master.py --cycles 50000000 --trace benchmarks/workload.nvt --models [list_of_models]
```

**4. Generate Analytical Graphs
```bash
python3 visualize_results.py
```

---

## 🗺️ Research Roadmap & Development Vectors

- [x] Integrate SPEC2017 (gcc, lbm) for high-bandwidth and instruction-heavy validation.
- [x] Model 1T1R SLC/MLC and 1S1R Cross-point architectures.
- [x] Automate WSL storage hygiene and trace parsing.
- [x] **AI Workload Integration**: Implemented MLPerf inference traces via SCALE-Sim to benchmark backpressure limits and evaluate ReRAM's strength in read-heavy, dense parallel operations.
- [ ] **Power Scaling Resolution**: Audit NVMain configurations to resolve the StandbyPower leakage paradox across multi-chip DIMMs.
- [ ] **Rank Interleaving Analysis**: Investigate custom rank/bank topologies and memory controller queue depth
