# MBMM: Memristor-Based Main Memory Architecture Evaluation

A full-stack, cross-layer simulation pipeline for evaluating 22 nm ReRAM as a commodity
main-memory replacement for DRAM: NVSim for the device and array, NVMain 2.0 for the
memory system, Python for the ETL between them and for the analysis.

**Results are in the book, not here.** `documents/MBMM_Book_Typst/Project_Book.typ`
(and its compiled PDF) carries every number, its caveats and its provenance. This file
is only how to run the thing.

## 🏗️ Data flow

1. **Trace capture**
   - CPU workloads: gem5 with `--debug-flags=MemCtrl`, X86O3CPU, L1/L2 caches, against
     SPEC CPU2017 binaries (gcc, lbm) and STREAM.
   - AI/ML workloads: SCALE-Sim DRAM traces (GPT-2 GEMM, AlexNet layer 1 input and
     output maps).
2. **Trace parsing** - two different parsers, one per source:
   - `parse_gem5_memctrl.py` for **gem5 MemCtrl logs** (exact 3 GHz cycles, per-controller
     retry drops, full line accounting).
   - `parse_trace.py` for **SCALE-Sim DRAM trace CSVs**. It *refuses* a gem5 log.
   - Both write a provenance sidecar `<trace>.nvt.sidecar.json` beside the trace.
   - `tools/validate_trace.py` checks a trace against its sidecar (record counts, address
     span, window coverage, read/write ratio).
3. **Hardware (NVSim)** - `1_run_nvsim_hardware.py` runs the forced-organization ReRAM
   cfgs; `2_extract_hardware_metrics.py` turns the results into
   `results/hardware_metrics.json` and derives the analytical MLC track from the SLC one.
4. **Architecture factory** - `3_gen_nvmain_config.py` generates one NVMain config per
   (hardware model x architecture): `single` (1 chip), `8chip`, `16chip` and
   `full_dimm` (64 chips, 8 GiB SLC / 16 GiB MLC). The one-chip point is a construction
   step, excluded from every conclusion in the book.
5. **System simulation** - `4_execute_simulation.py` runs NVMain per model and trace into
   `results/system/stats_<model>_<trace>.out`.
6. **Metrics** - `process_metrics.py` is the single source of truth for every derived
   number and writes `results/processed_*.csv`.
7. **Figures** - `visualize_results.py` (bar charts), `visualize_pareto.py` (Pareto
   frontiers), `visualize_hero_graphs.py` (headline comparisons), and
   `visualize_slides.py` (the deck's figures, run separately).

`mbmm_master.py` is the Gate-Keeper: it orchestrates stages 1 to 7 and is what a pipeline
change must be verified through. It does **not** run `visualize_slides.py`,
`endurance_sensitivity.py`, `selector_layer.py` or `tools/aggregate_wear.py`.

## 🚀 Running it

### The primary matrix (2026-09 revision)

```bash
python3 mbmm_master.py --all \
  --trace gcc_spec2017.nvt lbm_spec2017.nvt stream.nvt \
          gpt2_ifmap.nvt alexnet_layer1_ifmap.nvt alexnet_layer1_ofmap.nvt \
  --window-ns 250000000 \
  --ddr5-model DDR5_4800_DRAM_subchannel \
  --channels 2 --decoder StartGap --endurance-model RowModel --silicon
```

120 runs, about 90 minutes. `--window-ns` is a **matched window**: it is converted per
model into that model's own CLK-cycle budget, so every technology admits the identical
slice of trace time. Do not use `--cycles` for a comparison run - it hands every model the
same cycle count, which is a different amount of time at each CLK.

Note the master's flag defaults (`--channels 1 --decoder Default`) are **not** the primary
matrix's settings. Stage 4 writes `results/system/run_manifest.json` recording the full
command line, the git commits of the superproject and both submodules, every flag's
effective value, the traces with their sidecar checksums and the sha256 of every config it
is about to simulate; `process_metrics.py` carries the key flags into every CSV as
`Run_*` columns.

### Sensitivity axes

Each into its own results directory, with three traces
(`gcc_spec2017.nvt lbm_spec2017.nvt alexnet_layer1_ofmap.nvt`), otherwise the primary
flags, changing one thing:

| Axis | Flag |
|---|---|
| Decoder off | `--decoder Default` |
| One channel | `--channels 1` |
| DDR5 64 B bus | `--ddr5-model DDR5_4800_DRAM_64B` |
| Interface clock | `--freq 1333`, `--freq 2400` |
| Queue depth | `--queue-size 8`, `--queue-size 128` |
| Subarray organization | `--organization 1024` |

`--freq`, `--queue-size`, `--channels`, `--decoder` and `--endurance-model` reach the
**generated ReRAM and silicon configs only**; the DDR5 and PCM configs are static tracked
files.

### Scoping a re-run

`--models` does **not** scope a master run: `main()` only checks whether it was given at
all, then runs the full matrix. To re-simulate specific models, call the stage directly:

```bash
python3 4_execute_simulation.py --models <name> --trace <file>.nvt --cycles <n>
```

Its `--models` *is* respected. Run stages 2 and 3 first if your change touches anything
`hardware_metrics.json`-derived.

### Trace tools

```bash
python3 parse_gem5_memctrl.py --raw <m5out>/raw_trace.txt --stdout <gem5_stdout.log> \
    --out benchmarks/<name>.nvt --sidecar benchmarks/<name>.nvt.sidecar.json
python3 parse_trace.py <layer>/IFMAP_DRAM_TRACE.csv benchmarks/<name>.nvt \
    --scalesim-cmd "<the exact SCALE-Sim command>"
python3 tools/validate_trace.py benchmarks/<name>.nvt --window-ns 250000000 --table
```

### Analysis tools (not run by the master)

```bash
python3 endurance_sensitivity.py --trace benchmarks/lbm_spec2017.nvt \
    --stats results/system_rev2026-09_primary/stats_<model>_lbm_spec2017.out \
    --window-ns 250000000            # -> results/endurance_table.csv
python3 tools/aggregate_wear.py results/system_rev2026-09_primary/stats_<model>_<trace>.out
python3 selector_layer.py --hardware results/hardware_metrics.json \
    --out results/selector_layer.json
python3 visualize_slides.py         # the deck's figures
```

## 🧪 Tests and regression

```bash
python3 -m pytest tests -q            # fast suite (slow tests deselected by pytest.ini)
python3 -m pytest tests -q -m ""      # everything, including the slow ones
python3 tools/check_live_configs.py   # tracked configs/*.config == live NVMain copies
bash tools/nvmain_regress.sh          # replays a frozen trace against tools/golden/
```

`tools/nvmain_regress.sh` is the NVMain C++ regression harness: it rebuilds `nvmain.fast`
and compares three configurations' stats against recorded golden files, so a submodule
patch that changes simulator behavior cannot land silently.

## 📦 Where the data lives

- `results/system_rev2026-09_primary/` - the frozen primary stats (120 files).
- `results/rev2026-09_primary_csv/` - its processed CSVs and `hardware_metrics.json`.
- `results/system_rev2026-09_<axis>/` with `_csv/` - the nine sensitivity datasets.
- `results/book_figures_rev2026-09/`, `results/slide_graphs_rev2026-09/` - the figures the
  book and the deck use.
- `results/endurance_table.csv`, `results/selector_layer.json` - the two analysis outputs.
- `benchmarks/*.nvt` are **git-ignored** (gigabytes, and the SPEC-derived ones cannot be
  redistributed); only the `*.sidecar.json` provenance files are tracked.

## ⚠️ Two upstream NVMain caveats you must know before reading a raw stats file

Both are in `simulators/nvmain/CLAUDE.md` (items 6 and 7), and both are left unpatched on
purpose so the frozen stats stay exactly what NVMain printed.

1. **DDR5 background power is printed per DEVICE, not per rank.** In `EnergyModel current`
   mode (the DDR5 configs only) `StandardRank::CalculateStats` divides `backgroundPower` by
   the device count and never multiplies it back, while activate, burst and refresh are
   per rank - and the printed rank `totalPower` inherits the same omission. The correction
   is applied in `process_metrics.py`, which multiplies each rank's background by
   `BusWidth / DeviceWidth` and records the factor in the `Background_Power_Device_Factor`
   CSV column. **Never read a current-mode rank's `backgroundPower` or `totalPower` raw.**
   A current-mode stats file is recognisable by its energy units: `mA*t`, not `nJ`.
2. **A current-mode rank's `totalEnergy` double-counts one device's bank energy.** Sum the
   four energy components instead. Nothing in this pipeline reads `totalEnergy`.

## 🗺️ Status

- [x] SPEC CPU2017 (gcc, lbm) and STREAM traces, regenerated 2026-09 with provenance
      sidecars and a validator; mcf is parked (gem5 panics inside its input reader).
- [x] 1T1R and 1S1R crossbar tracks, SLC and MLC, at a forced 2048x2048 mux-64
      organization, with a 1024x1024 sensitivity.
- [x] AI/LLM workloads (GPT-2 GEMM, AlexNet layer 1) via SCALE-Sim.
- [x] DDR5-4800 baseline (two 32-bit subchannels, 64 B per access) with JEDEC write-path
      and power-down timings, plus a legacy Microsoft PCM 2009 baseline.
- [x] Start-Gap wear-leveling decoder and per-location wear counters in NVMain, with an
      endurance projection from the measured write distribution.
- [x] Analytic 1S1R selector layer (sneak current, read margin, tile ceiling) - the part
      NVSim does not model.
- [ ] Rank interleaving: custom rank/bank topologies beyond the channel-count axis.
