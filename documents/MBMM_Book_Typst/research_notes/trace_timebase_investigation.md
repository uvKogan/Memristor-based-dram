# Trace time base and trace window: what the SPEC traces actually contain

**Date:** 2026-09-15. **Trigger:** the endurance deep dive (`endurance_deep_dive.md` §4.2) found the trace
parser used a 1 GHz basis while every NVMain config uses `CPUFreq 3000`. **Status:** verified. The pipeline
itself was not changed. Decisions for the Lead are in §6. Evidence: `timebase_runs/`.

## Bottom line

1. **One trace cycle in `lbm_spec2017.nvt` and `gcc_spec2017.nvt` is exactly 1 ns of gem5 time.** NVMain at
   `CPUFreq 3000` replays one cycle as 0.333 ns, so **every configuration replays the traces 3x too fast**.
   The book's "250 M trace cycles = 83.33 ms" window is really **250 ms** of program time.
2. **The entire 250 M-cycle window is gem5 fast-forward, not the O3 region of interest.** Every admitted
   request comes from the atomic CPU that gem5 uses to skip the first 500 M instructions from program start.
   The O3 CPU's accesses begin at cycle 517,219,363 (LBM) and 573,807,209 (GCC), outside the window. LBM's
   write burst is program initialization.
3. **The book's trace description is wrong.** §2 (line 620) and §3.1.6 item 6 (lines 1521-1526) say the traces
   are uncached and cover the first 10 M instructions. They were generated with caches, and the simulated
   window is cached fast-forward from program start.
4. **The O3 part of each trace is corrupted by 4x duplicate records**, a parser defect. It lies outside the
   window, so no current result is affected, but any replay of the O3 region would be distorted.
5. **STREAM did not come from this parser** (timestamp gcd 5, span 0-999,995). Its time unit is unresolved.

## 1. Provenance

- **Parser:** `git show 2e8514c:parse_trace.py` keeps gem5 `--debug-flags=MemCtrl` lines containing
  `system.mem_ctrls:` and sets `cycle = int(tick_str) // 1000`, commented "Convert gem5 ticks (ps) to NVMain
  cycles (assuming 1GHz = 1000ps)". It treats any `0x` token as the address.
- **Two fingerprints tie the SPEC traces to this parser version:**
  - Timestamp gcd is 1. gem5 access ticks are multiples of 500 ps (below), so a gcd of 1 is only possible after
    dividing by 1000. The older c893454 parser wrote raw ticks.
  - gem5 also prints `Access to 0x..,`, `Command for 0x..,` and `Responding to Address 0x..`. This parser turns
    each of those into an extra read with a `,` or `..` suffix on the address, and exactly those records appear
    in both traces.
- **gem5 command** (README at 2e8514c, line 18):
  `--cpu-type=X86O3CPU --caches --l2cache --fast-forward=500000000 --maxinsts=50000000`.
  gem5 refuses X86O3CPU without caches.
- **No simulated-time record survives.** The raw logs were deleted by the parser. Session Summary 18 records
  the O3 and cache switch but no sim seconds. `simulators/gem5/m5out` holds a later mlperf run.

## 2. How NVMain interprets the timestamps

- `traceSim/traceMain.cpp:167`: the global event queue runs at `CPUFreq`.
- `src/EventQueue.cpp:537-538`: memory-side events (at `CLK`) are scaled by CPUFreq/CLK.
- `traceMain.cpp:195-196`: `--cycles` is multiplied by CPUFreq/CLK.
- `traceMain.cpp:254, 269-272`: trace timestamps are compared directly with the global cycle count and never rescaled.

A request stamped T is issued at T / CPUFreq seconds. The book's arithmetic matches NVMain; only the assumed
unit of a trace cycle is wrong.

## 3. gem5 experiment (repo's gem5.opt v25.1, static test program, flags scaled to `--fast-forward=1000000 --maxinsts=2000000`)

| Check | Result |
|---|---|
| Tick unit | 1 ps (`simFreq` 1e12); CPU clock 500 ps (2 GHz) |
| 2e8514c parser span vs gem5 `finalTick`/1000 | 8,098,327 vs 8,098,355 cycles: **1 cycle = 1 ns** |
| Fast-forward accesses logged? | yes, as `recvAtomic` (62,024 lines), on 500 ps multiples |
| Address alignment | all 64-byte aligned in both regions (caches present) |
| Raw tick gcd / after // 1000 | 500 / 1, same as the real traces |
| O3 region | each access written 4x (one real record plus three suffixed reads); the real LBM trace shows the same pattern (796,060 clean, 796,060 `..`, 1,592,086 `,`) |

Spot-check (2026-09-15): GCC's first suffixed record is line 1,014,077 at cycle 573,807,209. Records below
250 M cycles: 407,363, zero suffixed. This equals the book's GCC admission count exactly.

## 4. Plausibility of 1 cycle = 1 ns

| Region | GCC | LBM |
|---|---|---|
| Fast-forward (500 M instructions) | 1.148 ns/instruction | 1.034 ns/instruction |
| O3 (50 M instructions) | 37.2 M ns, 0.745 ns/instruction | 35.8 M ns, 0.715 ns/instruction |

- At 1 ps per cycle, 500 M instructions would take 0.57 ms, impossible with a 500 ps CPU clock.
- At 0.333 ns per cycle, fast-forward would run faster than the clock allows.
- **Only 1 ns fits.** Book admissions reproduce exactly: GCC 236,563 R + 170,800 W; LBM 9,481,309 R + 6,965,793 W.

## 5. What this changes (directions; magnitudes need a rerun)

| Result | Direction | Notes |
|---|---|---|
| Queueing latency (item 11: 1T1R SLC GCC 130.9 ns, 1.61x DDR5) | down; DDR5 gap narrows | requests arrive 3x more slowly |
| LBM completion (39.8 / 28.0 / 22.4 / 13.5 / 3.9%) | up for all resistive tracks | 16.4 M requests over 250 ms is about 65.5 M/s; 1T1R SLC already serves about 78.6 M/s |
| Endurance write rates | down; lifetimes up 1.4-3x | LBM 39.1 M/s becomes 13.0-27.9 M/s; 1.09 yr becomes about 1.5-3.3 yr |
| Window-averaged dynamic power | down, about 3x for trace-limited workloads | static power unchanged |
| Workload characterization (§2, §3.1.1) | reframed | the window is program start-up under fast-forward, not steady-state O3 execution |

## 6. Decisions for the Lead

1. **Fix the replay speed.** The recommended option keeps `CPUFreq 3000` and multiplies trace timestamps by 3,
   with cycle budgets `ceil(750,000,000 x CLK / 3000)`: ReRAM 200 M, PCM 100 M, DDR5 600 M.
   - Setting `CPUFreq 1000` instead violates `assert(CLK <= CPUFreq)` for DDR5 (`EventQueue.cpp:461`). The
     assert is compiled out in `nvmain.fast` (`-DNDEBUG`), and fractional scaling is untested.
   - Any change goes through `mbmm_master.py`.
2. **Choose the trace window.**
   - (a) Keep the start-up window and describe it honestly.
   - (b) Replay the O3 region of interest after removing the 4x duplicate records.
   - (c) Regenerate traces with a fixed parser (dropping `Access`/`Command`/`Responding` lines and keeping
     real packet sizes) and a documented region of interest. This is the most defensible and should be timed
     with the 2048x2048 NVSim re-run, so the matrix is re-simulated once.
3. **Resolve STREAM's time unit** (`archive/scripts/gen_stream.py`) before reusing its per-second rates.
4. **Correct the book's trace description** (§2 line 620, §3.1.6 item 6, slide 16), whatever is decided above.

## 7. Other traces and regeneration feasibility (2026-09-16)

Scratch evidence: session scratchpad `regen_facts/` (tested stdlib gem5 script `se_ff_o3_trace.py`, log analyzer
`msgstats.py`). Repo unchanged; nothing under `spec2017` touched.

**STREAM is synthetic, not a trace of STREAM.**
- `archive/scripts/gen_stream.py` (ef1d8c1, dad4fd6) regenerates `stream.nvt` byte-identically.
- Pattern: for i = 0..99,999, read A[i] at cycle 10i and write B[i] at cycle 10i+5, 64-byte strides. That is a
  copy kernel; real STREAM has four kernels over 8-byte doubles.
- The cycle has no physical meaning. Relative comparisons at equal offered load are fine; absolute per-second
  figures (bandwidth, write rate, endurance) are not. The book's "industry-standard" STREAM [27] description
  (lines 599-601, 632-636) overstates it.

**AI traces (SCALE-Sim, current `parse_trace.py` from c5b8141).**
- **GPT-2 provenance resolved:** re-parsing `benchmarks/ml_trace_output/GoogleTPU_v1_os/layer0/IFMAP_DRAM_TRACE.csv`
  reproduces `gpt2_ifmap.nvt` byte-identically (GEMM run with `configs/google.cfg`, `topologies/GEMM_mnk/gpt2.csv`).
  This closes the book's "could not be tied" caveat (lines 655-660, 1526). The AlexNet CSVs were overwritten
  and cannot be re-verified.
- **Time unit:** a SCALE-Sim cycle is abstract (no `TimeLinearModel` in `google.cfg`). SCALE-Sim's own plots
  assume 2.4 GHz and the TPUv4 model implies 0.39-2.8 ns, so CPUFreq 3000 is defensible if stated.
- **Parser defect 1, about 10x undercount:** with `Bandwidth: 10`, each CSV line lists up to 10 addresses, but
  only the first is kept. `gpt2_ifmap` has 6,554 records vs 65,540 DRAM reads in SCALE-Sim's report.
- **Parser defect 2, invalid addresses:** SCALE-Sim's `-1` padding becomes address `-0x1`, 31% of
  `alexnet_layer1_ifmap.nvt` records.

**SPEC regeneration: feasible, but only the Lead can run it** (SPEC binaries and inputs live in `spec2017`).
- gem5 25.1 `gem5.opt` is built. `configs/example/se.py` is a stub; `configs/deprecated/example/se.py` still runs.
  The original runs used SPEC run directories (`cleanup_traces.sh:3`). Benchmarks 602.gcc and 619.lbm; inputs
  and `--mem-size` were never recorded.
- Command per benchmark, run from the SPEC run directory:
  `gem5.opt --outdir=<out> --debug-flags=MemCtrl --debug-file=raw_trace.txt configs/deprecated/example/se.py
  --cmd=./<binary> --options="<args>" --cpu-type=X86O3CPU --caches --l2cache --fast-forward=500000000
  --maxinsts=50000000 [--mem-size=8GB]`.
  - Keep stdout for the "Switched CPUS @ tick" line.
  - Add `--debug-start=<tick>` to log only the O3 region.
- Estimated cost: 10-30 min per benchmark; LBM log about 2.5 GB (0.8 GB if O3 only), GCC about 0.14 GB; 860 GB free.
- A modern stdlib script works too, but its caches and clock differ from se.py, so its traces would not be
  comparable to the old ones.

**Fixed-parser specification** (gem5 25.1 `src/mem/mem_ctrl.cc`):
- **Keep only:**
  - `recvAtomic: <Cmd> 0x<addr>` (line 138, fast-forward, no size)
  - `recvTimingReq: request <Cmd> addr 0x<addr> size <n>` (line 410, O3)
  - Match the object by `\S*mem_ctrl\S*`.
- **Drop:** `Access to` (811), `Command for` (1009, 1101), `Responding to Address` (625) and queue dumps
  (388-400). These cause the 4x duplicates.
- **Retries:** drop any request followed by "queue full, not accepting" (445, 465).
- **Operations:** W = WritebackDirty/WritebackClean/WriteReq/WriteLineReq/WriteClean; R = ReadReq/ReadSharedReq/
  ReadExReq. Anything else is an error. Use a strict address regex.
- **Output:**
  - Timestamps in documented units, with an explicit NVMain conversion `cycle = round(tick_ps x CPUFreq_MHz / 1e9)`.
  - Assert timestamps are monotonic.
  - Write a sidecar recording unit, switch tick, region, command and binary.
  - Do not auto-delete the raw log.
