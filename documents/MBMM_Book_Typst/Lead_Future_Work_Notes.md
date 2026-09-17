# Future Work Notes - Lead Researcher

Personal idea log for work beyond the current book. Nothing here is in `Project_Book.typ` §4 yet
unless stated. Each note records the idea, why it matters, what was checked, the catch, a smallest
useful version, and a rough effort. Effort figures are rough estimates, not plans.

| # | Idea | Status |
|---|---|---|
| 1 | Re-simulate the 1T1R family at 6F² | Idea, assessed 2026-09-14 |
| 2 | Simulate Intel Optane (enough data? worth it?) | Assessed 2026-09-15: usable as a reference point, not simulable faithfully. Deeper pass in progress (2b) |
| 3 | Sweep controller queue depth properly (below 32, above 64) | Assessed 2026-09-15: prior sweep was narrow; latency metric hides stall time |

---

## 1. Re-simulate the 1T1R family at 6F²

**Idea.** Re-run the whole 1T1R matrix (SLC and MLC, all chip counts, all six workloads) with a 6F²
cell instead of 20F².

**Why it matters.** The book's density verdict against 1T1R (0.22x DDR5 die-level density) rests on the
20F² planar-transistor assumption. A real 16Gb, 27nm 1T1R part reached 6F² with a recessed-channel
access transistor [33]. Today the book only estimates the effect linearly ("roughly 0.7x", §3.3) and
lists it as future work (§4.2, Appendix A "Bit-Cell Area"). A simulation would replace that estimate.

**What the pipeline does today (checked in source).**
- `configs/reram_22nm_1t1r_slc.cell`: `CellArea (F^2): 20.0`, `CellAspectRatio: 1`, `AccessType: CMOS`,
  `AccessCMOSWidth (F): 4.0`.
- NVSim uses `CellArea` only to set the cell's height and width (`sqrt(area)`, `MemCell.cpp:141-142`).
- The access transistor's on-resistance, capacitance and gate leakage all come from `AccessCMOSWidth`
  (`SubArray.cpp:250-300`, `:690`). Nothing checks that the transistor fits inside the cell.

**The catch.** Changing only `CellArea` to 6 would put a 4F-wide planar transistor inside a
2.45F x 2.45F cell. NVSim would accept it silently, but the device is physically impossible. A recessed
channel gets a large effective width in a small footprint by folding the channel into the silicon, and
NVSim's access-device model cannot represent that (book Appendix A, §4.2).

**Proposed approach: a bounding pair, always reported together.**
- **A, optimistic:** `CellArea 6`, `AccessCMOSWidth 4F`. Density at 6F², with drive current and leakage
  unchanged. Stands in for "the recessed channel delivers full planar-equivalent drive".
- **B, conservative:** `CellArea 6`, `AccessCMOSWidth` reduced to fit a planar 6F² footprint (about 2F).
  Less drive current and less leakage; SET/RESET may get slower or fail to reach the target current.
- A real recessed-channel device should sit between A and B.

**Hypothesis to test (not a result).** Density should rise sharply in both variants, less than the
3.3x cell-level ratio at die level because the periphery does not shrink. Power is harder to predict
than it first looked. NVSim assigns memristor cells zero leakage whatever the access device
(`SubArray.cpp:770`); chip leakage is all peripheral circuitry (`:869`), so it tracks how many mats and
subarrays NVSim builds. Today's 1T1R chip is split into 256 mats against the selector's 2 (checked
2026-09-15, `results/hardware/*_results.txt`). A smaller cell shortens wordlines and bitlines and can
change that organization, so leakage may move in both variants, not only in B. Resolve the pending
47x-mechanism question (1T1R and selector swapped onto each other's array settings) before running
this, because it determines what a 6F² result would mean.

**Open questions.**
- What effective width or drive current does [33]'s recessed-channel transistor actually have? This
  would anchor A vs B to a real device.
- Material mismatch: [33] uses a Cu-filament CBRAM layer, while the book models oxide RRAM with
  1e5 / 1e9 ohm targets [7]. The re-run keeps the oxide targets, so it is a geometry study, not a
  replica of [33].
- Does variant B still complete SET/RESET at 2.0 V into a 1e5 ohm LRS, or does NVSim reject it?
- MLC follows automatically, because its penalties are analytical multipliers on the SLC result.

**Pipeline work.**
- Add new model names (for example `reram_22nm_1t1r6f2a_slc` / `..._mlc` and a `6f2b` pair) instead of
  editing the 20F² files, so the book's baseline stays reproducible.
- Model names are hard-coded in `mbmm_master.py` (`reram_bases`, `factory_bases`), in
  `process_metrics.py` (`classify_technology`, `RERAM_KEY_PREFIX`), and in the technology color and label
  tables of the `visualize_*.py` scripts. An isolated driver in the style of `sweep_queue_size.py`
  (separate output directory) would avoid touching the official results.
- Run count: 2 cell types (SLC, MLC) x 4 chip counts x 6 workloads = 48 runs per variant, 96 for A and B.
  Any Python change goes through `mbmm_master.py` per CLAUDE.md.
- Book impact if adopted: §3.3 density discussion, Tables 6 and 7, Figure 26, Appendix A "Bit-Cell Area",
  and §4.2's "Recessed-Channel 1T1R Density" bullet becomes a result.

**Rough effort.** About 1 day of plumbing, an overnight simulation batch, and about 1 day to analyze and
write up.

---

## 2. Simulate Intel Optane? (enough data? worth it?)

**Verdict (researched 2026-09-15).** There is enough published data to use Optane as a **reference point**,
but not enough to **simulate it faithfully**, at either the cell or the module level. Optane's measured
latency is dominated by its on-DIMM controller, which NVMain does not model.

**What exists.**

| Parameter | Value | Source | Confidence |
|---|---|---|---|
| Cell stack | GST phase-change element + OTS selector, stacked 1S1R | Kau et al., IEDM 2009 [42]; TechInsights teardown | Primary (design principle) |
| Cell area | 0.00176 µm² at 20 nm (about 4.4F², 42 nm pitch) | TechInsights teardown blog | Secondary |
| RESET pulse, endurance | 9 ns, 10^6 cycles (2009 64 Mb prototype, not the product) | Kau 2009 abstract | Not viewed directly |
| SET/RESET currents, voltages, resistances, OTS thresholds | Not published for the shipped product | - | Not found |
| Media timing (NVMain tRCD/tWP equivalents) | Not published | - | Not found |
| Interface, capacities | DDR-T protocol on DDR4-2666 electricals; 128/256/512 GB | Intel ARK; Izraelevitz [32] | Primary |
| Power | PMem 100: 12-18 W envelope (15 W average default); PMem 200: 12-15 W. Idle power not found | StorageReview; [32] Table 1; Intel brief | Secondary / primary |
| Endurance | PMem 100 256 GB: 360 PBW over 5 years (about 1.4M full-module writes) | Intel via Blocks and Files | Secondary |
| Measured latency | 305 ns random / 169 ns sequential read vs 81 ns DDR4 DRAM | [32] | Primary |
| Measured bandwidth | 6.6 GB/s read / 2.3 GB/s write, one DIMM | [32] | Primary |
| On-DIMM internals | 16 KB SRAM read-modify-write buffer, 16 MB DRAM address-indirection buffer, 4 KB write-combining queue, wear-leveling tail latency | Wang et al., "LENS/VANS", MICRO 2020 | Primary (reverse-engineered) |

**How the 305 ns was measured** (matters for any comparison): Intel Memory Latency Checker reading one
random 64-byte cache line on one core, from a file memory-mapped on an ext4-DAX pmem device (App Direct
mode), prefetching off, cold cache. It is a CPU-side, end-to-end number: memory controller, DDR-T bus and
on-DIMM controller included. It is not a media latency.

**Can we simulate it?**
- **NVSim Optane cell: no.** NVSim supports PCM cells natively (`MemCellType: PCRAM`; example cell at `configs/samples/sample_PCRAM.cell`), but the shipped product's SET/RESET currents, resistance states and
  OTS selector characteristics were never published. Any cell would be generic selector-PCM, not Optane,
  and the OTS selector could only be approximated as a diode, as this project's 1S1R cells already are.
- **NVMain Optane module: no, not honestly.** No media timing is published, so tuning `tRCD` until the
  model hits 305 ns would be circular. NVMain also lacks everything that makes Optane slow: the DDR-T
  request/grant handshake, the write-combining and read-modify-write buffers, the address-indirection
  buffer, and wear-leveling translation. The VANS paper shows DDR-style simulators (DRAMSim2, Ramulator)
  miss Optane's latency and bandwidth badly; NVMain was not tested there, so that part is inferred.
- **As an external validation target: only partly.** Matching Optane's ratios after tuning a config is
  calibration, not hardware correlation.

**What it could do for the project.**
- **It cannot close the "internal validation only" limitation.** Optane is PCM, so it says nothing about
  the NVSim ReRAM device layer, and its measurement setup (CPU-side, cold cache, DDR4, unmodeled
  controller) differs from NVMain's trace-driven controller timing.
- **It can strengthen an honest limitation.** The only NVM DIMM ever shipped was about 3x slower than
  DRAM on random reads ([32] Observation 1; see 2c on 81 vs 101 ns), largely because of its controller, buffers and wear leveling. MBMM models none of
  these, so its DIMM-level latency is probably optimistic. That caveat belongs in the book.
- **It gives a real-product endurance anchor** for Shahar's note 8: 360 PBW over 5 years for a shipped
  NVM DIMM.
- **VANS is open source and was validated against real Optane** (86.5% average accuracy on
  microbenchmarks, 87.1% on SPEC with gem5, as reported in the paper). Running MBMM's traces through
  VANS would be the most credible Optane cross-check available, though still against a validated
  simulator, not hardware.

**Recommended scope.**
1. **Now, about half a day, no simulation:** a limitations and future-work paragraph citing [32], VANS
   and the PBW figure, with the controller-overhead caveat. This adds references, so the reference-count
   updates apply.
2. **Skip:** an NVSim Optane cell or a tuned NVMain Optane config. About 2-3 days of work that
   demonstrates nothing and invites reviewer criticism.
3. **Optional future work, roughly 1-2 weeks:** convert MBMM traces to VANS input, run its published
   Optane configuration, and compare read-latency and bandwidth ratios with NVMain's. VANS's trace and
   config formats have not been inspected yet, so this estimate is uncertain.

**Not verified from a primary source.** TechInsights cell figures (blog summary only); Kau 2009's 9 ns and
10^6 (abstract seen via a search listing); PMem 200 PBW and TDP (search snippet); PMem 100 PBW and power
(trade press quoting Intel); VANS configuration values (not inspected); NVMain's mismatch with Optane
(inferred, not tested).

**Sources.** Izraelevitz et al., arXiv:1903.05714 · Wang et al., MICRO 2020
(swanson.ucsd.edu/data/bib/pdfs/MICRO20-LensVans.pdf) · VANS code (github.com/TheNetAdmin/VANS) ·
Intel ARK, PMem 100 256 GB · Intel PMem 200 product brief · StorageReview (Optane DC PMM) · Blocks and
Files (Optane DIMM endurance, 2019-04-04) · Lenovo Press LP1066 · TechInsights 3D XPoint teardown · Kau et
al., IEDM 2009.

### 2b. Deeper pass: local simulation checks (2026-09-15)

Smoke tests only, run on copies in the session scratchpad; no project config or result touched.

- **A newer PCM media config already ships with NVMain.** `simulators/nvmain/Config/PCM_ISSCC_2012_4GB.config`
  models Samsung's 20nm 1.8 V 8 Gb PRAM (ISSCC 2012): `tRCD 48` (120 ns read) and `tWP 60` (150 ns write) at
  400 MHz, global sense amps, `FRFCFS-WQF` controller. It runs in our trace build (GPT-2 IFMAP: all 6,553
  reads, 495.7 cycles average total latency). It is a closer relative of Optane's media era than the
  book's `pcm_microsoft_2009.config` (`tRCD 22`, 55 ns read), but still not Optane.
- **NVMain can put a DRAM cache in front of slower memory** (`MEM_CTL DRC`, `DRCVariant LO_Cache`,
  `MM_CONFIG` for the backing memory; `3D_DRAMCache_example.config`), which is the shape of Optane's
  Memory Mode. The stock example backs the cache with DRAM, not NVM. It runs in trace mode.
- **Pointing that cache at the Samsung PCM config runs, but the write path is broken.** On LBM
  (5 M cycles) the DRAM layer accepted 337,300 writes, yet the PCM layer received 0 writes and the cache
  reported 0 `drc_hits`. The stock `LO_Cache` does not model flushing writes to the backing memory in this
  setup, and Optane's write path is exactly what makes it slow. Using it for Optane would need controller
  work first, and it would still not model DDR-T or Optane's on-DIMM buffers.

### 2c. Deeper pass: can Optane be simulated, and how to compare it (2026-09-15)

**Short answer.** Optane can be simulated at the level of its controller and buffers, and only with VANS
(the one validated public model). No NVMain configuration can honestly be called "Optane". The
defensible book and deck route is a real-hardware reference row with carefully matched ratios, optionally
backed by a small VANS cross-check. P = primary source read; S = secondary; D = derived.

**VANS (Wang et al., MICRO 2020; github.com/TheNetAdmin/VANS, MIT, commit 541d2fb).**
- Standalone trace mode; also a gem5 mode pinned to an old gem5 commit. Builds here with gcc 13 in 8 s (D).
- Trace format: one 64-byte access per line, `0xaddr R|W|C[:gap]`. No timestamp, data or thread ID;
  closed-loop (a busy model stalls the trace). An NVMain `.nvt` converter is about 30 lines of Python.
- Shipped Optane config (tick = 0.75 ns): media read/write 75 / 225 ns; RMW buffer 16 KB (256 B entries),
  read 135 ns; AIT buffer 16 MB (4 KB entries) backed by DDR4-2666; wear-level migration about 51.8 us every
  896 writes per block; iMC write/read queues 4 / 4 (P, `config/vans.cfg`). **The 75 / 225 ns media values
  are fitted model parameters, not measured media timing.**
- Validation (P): 86.5% average accuracy on latency and bandwidth microbenchmarks; 87.1% on SPEC speedup vs DRAM
  through gem5. A Lee-2009-style PCM model (Ramulator, the same lineage as the book's PCM baseline) scored 65.6%.
- **No energy or power model at all** (P, code).
- Output: total simulated time and buffer event counters; per-request latency needs about 1 day of instrumentation.
- Test runs here (D, 20,000 accesses each, single sample): VANS Optane vs VANS DDR4 random read 433 vs 48.7 ns
  (8.9x), sequential 188 vs 19.1 ns (9.8x). Standalone ratios are inflated versus measured software-visible
  ratios because the DRAM side has no CPU or iMC latency. Speed: about 5.5k ticks/s, so one 83.33 ms window
  would take about 5-6 hours per trace.

**Optane numbers with provenance.**

| Parameter | Value | Source | Conf. |
|---|---|---|---|
| Capacity | 128 / 256 / 512 GB per DIMM | Intel ARK; PMem 200 brief | P |
| Power | settings 12 / 15 / 18 W (PMem 100); max TDP 18 W (PMem 100), 15 W (PMem 200) | Intel support 000032853; PMem 200 brief | P |
| Idle / active read / active write power | never published | - | not found |
| Endurance, PMem 200 (128 / 256 / 512 GB) | 100% write: 292 / 497 / 410 PBW at 256 B, 73 / 125 / 103 PBW at 64 B; 67R/33W: 224 / 297 / 242 and 56 / 74 / 60 PBW | PMem 200 brief | P |
| Endurance per day (D) | 512 GB at 410 PBW over 5 yr is about 0.44 drive writes per day | derived | D |
| Bandwidth, PMem 200 | 256 B: read 7.45-8.10, mix 4.25-5.65, write 2.25-3.15 GB/s; 64 B: read 1.86-2.03, write 0.56-0.79 GB/s | PMem 200 brief | P |
| Measured latency (DRAM vs Optane) | sequential 81 vs 169 ns; random 101 vs 305 ns; ntstore 86 vs 90 ns; clwb 57 vs 62 ns | Yang et al. FAST 2020 Fig. 2 (bar mapping from extracted text) | P, mapping to verify |
| Tail latency | 0.006% of accesses about 100x normal | FAST 2020 | P |
| On-DIMM buffers | RMW 16 KB, AIT 16 MB, WPQ 512 B, LSQ 4 KB | MICRO 2020 (reverse-engineered) | P |
| Media read/write latency | never published; VANS values are fitted | - | not found |
| Workload energy | fptree at 16 threads used 56.3% less energy on Optane than on DRAM | Katsaragakis et al., HiPC 2022 | P, not per-op |

**Simulator landscape.**
- **gem5 `NVM_2400_1x64`:** tREAD 150 ns, tWRITE 500 ns. The code comment says "mimic PCM like memory" and gives
  no source. Not validated against Optane.
- **UDCC:** labels gem5's default "3DXPoint" without a source.
- **Mess simulator:** supports Optane curves but publishes no Optane accuracy.
- **Ramulator PCM:** Lee 2009 timing. DRAMsim3: no NVM. NVMain forks: no Optane-calibrated config found.
- **Quartz and PMEP emulators:** FAST 2020 shows these delay-injection methods are inaccurate for real Optane.
- **No paper was found** that compares a simulated ReRAM, PCM or STT memory against an Optane-calibrated model.

**Comparison options.**
- **A. Reference row or annotation (recommended, about 1 day).**
  - Comparable if labeled carefully:
    - density (512 GB per DIMM)
    - power envelope per GB (max TDP only)
    - endurance in PBW with test conditions stated
    - bandwidth envelope
    - read-latency ratio vs DRAM, shown as "software-visible, system-measured" beside our device-level ratio
  - Not comparable:
    - absolute latency (includes CPU, iMC and controller)
    - write latency (hidden by ADR and the write queue)
    - energy per operation or idle power (unpublished)
    - tail latency
    - our 83.33 ms completion metric
- **B. NVMain "Optane-like" config (not recommended).** There is no sourced media timing to put in it, and the
  buffers, controller and wear leveling that dominate Optane's behaviour are missing. If built anyway, name it a
  "3DXP-media-assumption PCM variant", never "Optane".
- **C. Our traces through VANS.**
  - Full version: about 1-2 weeks, hours per trace. It still gives only a ratio to VANS's own DDR4-2666, with no
    energy and a single serialized stream.
  - Reduced version (about 2-3 days, defensible): short random, sequential and write-heavy patterns through VANS
    Optane and VANS DDR4. Report the within-VANS ratio next to the within-NVMain ReRAM/DDR5 ratio as a qualitative
    cross-check.

**Claims the book can make.**
- Optane's software-visible read latency is 2-3x DRAM (FAST 2020, Izraelevitz), a different metric from ours.
- PMem 200 is rated 73-497 PBW depending on access size and mix, at a 15 W max TDP, up to 512 GB per DIMM.
- The only validated Optane simulator (VANS) models buffering and wear leveling but not power; Intel never
  published media timing.
- A Lee-2009-style PCM model is not an Optane proxy (65.6% accuracy in MICRO 2020).

**Claims the book must not make.**
- Any Optane media latency value.
- That our PCM baseline, gem5's NVM defaults, or any NVMain config models Optane.
- Any Optane energy per operation or idle power.
- A direct ratio between NVMain device-level latency and the measured 305 / 169 ns.

**81 vs 101 ns, checked in [32] (arXiv 1903.05714) on 2026-09-15.** The book quotes [32] faithfully: its
text says "random loads take 305 ns compared to 81 ns for DRAM accesses on the same platform" (p. 6). But
[32]'s own Observation 1 calls 305 ns "about 3x slower than local DRAM" (pp. 18, 60), while 305/81 is 3.8x
and 305/101 is 3.0x. FAST 2020 Fig. 2 (the same group's data) appears to put 81 ns on DRAM *sequential* and
101 ns on DRAM *random*. So [32] is internally inconsistent. Quote the ratio as "about 3x" (as the book
already does, §1.3), never compute 3.8x from 305/81, and add a short footnote if the 81 ns figure is kept.

**Sources.** VANS repo and MICRO 2020 paper (zixuan.wang/files/micro20-lens-vans.pdf) · Yang et al. FAST 2020
(arXiv 1908.03583) · Izraelevitz et al. (arXiv 1903.05714) · Intel PMem 200 product brief · Intel support
000032853 · Intel ARK PMem 100 · gem5 `src/mem/NVMInterface.py` · UDCC (arXiv 2303.13026) · Mess (arXiv
2405.10170) · Ramulator `src/PCM.h` · DRAMsim3 configs · Katsaragakis et al. HiPC 2022.

---

## 3. Sweep the controller queue depth properly (below 32, above 64)

**Idea.** The 2026-09-04 sweep (Shahar's note 5) stopped at `QueueSize` 64 at full-DIMM scale and never
went below 32 there. Push it much further in both directions, across every technology and workload,
before treating 32 as a settled choice.

**What was actually tested (checked 2026-09-15, `results/system/queue_size_sweep/`).**

| Scale | Trace | Values run | Result |
|---|---|---|---|
| 1T1R SLC full DIMM | LBM | 32, 48, 64 (80 timed out) | Completion 39.97% / 40.00% / 40.73% of DDR5's 16,447,102 requests; latency 468.1 / 670.6 / 858.6 ns |
| 1T1R SLC single chip | LBM | 16, 32, 48, 64, 96, 128 (256 timed out) | Completion 30.00% (16) to 31.43% (128); latency 324.1 ns (16) to 2,116.3 ns (128) |
| 1T1R SLC, all 4 scales | GCC, GPT-2 IFMAP | 16, 32, 64 | All requests complete at every value; full-DIMM GCC latency 25.5 / 38.6 / 48.4 cycles, GPT-2 248.0 / 366.8 / 668.9 ns |

**Gaps in that sweep.**
1. **The ceiling was a timeout, not a result.** `sweep_queue_size.py` kills each run after 240 s of
   wall-clock time (`--timeout 240`). "64 is the practical ceiling" (book Appendix A) means "80 took longer
   than 4 minutes to simulate". It says nothing about the model.
2. **Nothing below 32 at full-DIMM scale**, and only 16 at single-chip scale for LBM.
3. **One technology only (1T1R SLC).** DDR5 also runs `FRFCFS` at `QueueSize` 32. Enlarging only ReRAM's
   queue would tilt the comparison, so any change has to be swept for DDR5 too. 1S1R and both MLC tracks
   were never swept. PCM uses a different controller (`FRFCFS-WQF`, separate `ReadQueueSize`/`WriteQueueSize`
   keys) and needs its own axis.
4. **Completion was measured on LBM only**, and all LBM runs predate the idle-gating restoration.
5. **The LBM entries in `results/queue_size_sweep_results.json` were overwritten** by the later GPT-2 run;
   only the per-run stats files remain.

**The catch: NVMain's latency ignores time spent waiting for a queue slot (verified in source).**
- `traceSim/traceMain.cpp:282-292`: when the queue is full, the trace reader waits cycle by cycle until
  `IsIssuable()` is true, then calls `IssueCommand()`.
- `MemControl/FRFCFS/FRFCFS.cpp:152`: `arrivalCycle` is stamped inside `IssueCommand()`, after that wait.
- `FRFCFS.cpp:210-213`: `averageTotalLatency = completionCycle - arrivalCycle`.
- So a request's wait before a slot frees up is **not counted**. A smaller queue pushes waiting outside
  the measurement and reports a lower latency; a larger queue moves the same wait inside it. The earlier
  "+83% latency at 64" is at least partly this accounting shift, not a real cost.
- This also affects the book's headline latencies at 32, for every `FRFCFS` technology. GCC and GPT-2
  complete every request at 16, 32 and 64, yet their reported latency still grows with queue depth.
  Ratios between technologies may partly survive, since all share the same rule; that is untested.

**Hypothesis to test (not a result).** Measured from the trace timestamp, end-to-end latency should vary
far less with queue depth than today's numbers do. LBM completion should keep creeping up with depth and
flatten once the device, not the queue, limits throughput. Where it flattens is the real ceiling.

**Proposed study.**
1. **Fix the metric first.** Add an end-to-end latency statistic measured from the trace-record cycle
   (`tl->GetCycle()`) to completion. Keep the existing statistics untouched for reproducibility. This is
   a C++ change to NVMain, so it needs a rebuild and a byte-identical check of the existing stats.
2. **Values:** 4, 8, 16, 32, 64, 128, 256, 512.
3. **Models:** four ReRAM tracks plus DDR5, full-DIMM scale; single-chip for LBM only, as a sensitivity check.
4. **Traces:** all six.
5. **Runtime:** raise or remove the 240 s timeout and run in the background overnight. Record wall time
   per run so any remaining cutoff is reported as a simulation-budget limit, not a model limit.
6. **Realism anchor (not yet researched):** what queue depths real DDR5 integrated memory controllers and
   NVM DIMM controllers use. Without this, "best" depth is only a simulator optimum.

**Run count.** 8 values × 5 models × 6 traces = 240 full-DIMM runs, plus about 40 single-chip LBM runs.
Wall time is uncertain: full-DIMM LBM already exceeded 240 s at 80 entries, and 256-512 may take much longer.

**Book impact if adopted.** Appendix A "Memory Controller Queue Depth" (the "practical ceiling" and
"latency cost" wording), the §3.1.1 cross-reference, the "Streaming: the Honest Number" slide and the
backup slide. If end-to-end latency differs materially from `averageTotalLatency`, Table 2 and the latency
figures too.

**Rough effort.** About half a day for the NVMain statistic and its verification, half a day to extend
`sweep_queue_size.py` (models, traces, timeout, new metric), one or two overnight batches, and about a
day of analysis.
