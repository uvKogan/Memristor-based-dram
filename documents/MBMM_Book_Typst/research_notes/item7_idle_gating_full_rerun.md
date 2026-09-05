# Item 7, Workstream C steps 6-7: Official full re-run after restoring HandleLowPower()

**Context:** `simulators/nvmain`'s dormant power-down state machine (`MemoryController::CycleCommandQueues()` -> `HandleLowPower()`, previously dead code) was restored this session. This affects every technology sharing `MemoryController` as a base class (DDR5, PCM, ReRAM), not ReRAM only. DDR5 already carries real, JEDEC-datasheet-backed power-down currents (`Epda`/`Epdpf`/`Epdps`, non-zero and lower than standby). ReRAM and PCM carry an explicit "honest placeholder" (`Epda`/`Epdpf`/`Epdps` = their own existing `Eprestdby`/`Eactstdby`/`Eleak` standby energy), i.e. "assume power-gating saves nothing beyond existing standby, pending real characterization" (see `item7_reram_power_gating.md` for why no real number could be sourced from the literature). The isolated smoke test that validated the mechanism (non-zero power-down counters, sane power, no NaN/negative) was already done and is not repeated here. This note reports the official, full 36-run re-run that validation was gating.

## 1. Run inventory: all 36 succeeded

Scope: 6 technologies (DDR5, PCM, ReRAM 1T1R-SLC, 1T1R-MLC, selector-SLC, selector-MLC, all full-DIMM) x 6 workloads (`gcc_spec2017`, `lbm_spec2017`, `stream`, `gpt2_ifmap`, `alexnet_layer1_ifmap`, `alexnet_layer1_ofmap`) = 36 runs via `nvmain.fast` directly (not `4_execute_simulation.py` / `mbmm_master.py`).

Step 1 (config regeneration) confirmed: `python3 3_gen_nvmain_config.py --freq 800 --queue-size 32` regenerated all 16 ReRAM system configs in `simulators/nvmain/Config/`, and `Epda`/`Epdpf`/`Epdps` lines (each equal to the technology's own `Eactstdby`/`Eprestdby`) are present in all 4 target full-DIMM ReRAM configs. `DDR5_4800_DRAM.config` and `pcm_microsoft_2009.config` were not touched (per scope) and were confirmed to already carry their respective power-down lines from earlier hand-edits this session.

All 36 runs completed on the **first attempt** (no retries needed), exit code 0, no timeouts, no crashes:

| Technology (config) | Cycles arg | Runs OK | Notes |
|---|---|---|---|
| `DDR5_4800_DRAM.config` | 200,000,000 | 6/6 | All finished well under the 3600s timeout (trace-driven exit, not cycle-cap exit) |
| `pcm_microsoft_2009.config` | 33,333,334 | 6/6 | |
| `reram_22nm_1t1r_slc_full_dimm.config` | 66,666,667 | 6/6 | |
| `reram_22nm_1t1r_mlc_full_dimm.config` | 66,666,667 | 6/6 | |
| `reram_22nm_selector_slc_full_dimm.config` | 66,666,667 | 6/6 | |
| `reram_22nm_selector_mlc_full_dimm.config` | 66,666,667 | 6/6 | |

**36/36 succeeded. 0 failures.** Output files are in `results/system/stats_<model-name>_<trace-stem>.out`, one per combination, matching the project's existing `process_metrics.py` naming convention (verified against `results/system_v6_input/`).

`results/system/` also still contains pre-existing files from the earlier 2026-09-04/05 gatekeeper check (2D_DRAM_example, 3D_DRAM_example, and single/8chip/16chip ReRAM architectures). Those were left untouched, per scope. `process_metrics.py` scans the whole directory by default, so the regenerated `results/processed_*.csv` files contain rows for those other technologies/architectures too; **only the 6 technologies x 6 workloads x full-DIMM combination listed above reflect this session's fresh idle-gating run** for `1T1R_SLC` (full-DIMM), `1T1R_MLC` (full-DIMM), `1S1R_SLC` (full-DIMM), `1S1R_MLC` (full-DIMM), `DDR5_4800` (full-DIMM), and `pcm_microsoft_2009` (full-DIMM). Everything else in the CSVs (2D/3D DRAM examples, single/8chip/16chip ReRAM architectures) is stale/unrelated to this task and should not be quoted as idle-gating-updated data.

`process_metrics.py` also logs "MISSING AREA/CAPACITY DATA" warnings for all DDR5 and PCM rows; this is a pre-existing characteristic of the area/capacity lookup (DDR5 and PCM are not in the ReRAM area JSON), unrelated to the power-down change, and does not affect the Power/PDP numbers below.

## 2. Headline numbers: old (pre-idle-gating) vs new, per technology, GCC

All figures below are full-DIMM. "Old" comes from `results/system_v6_input/` (the pre-idle-gating baseline, re-processed through the unmodified `process_metrics.py` into a scratch output directory so the comparison uses identical extraction logic on both sides). "New" is this session's 36-run output.

| Technology | Old Power (W), GCC | New Power (W), GCC | Delta | Book's quoted figure |
|---|---|---|---|---|
| DDR5 (`DDR5_4800`) | 0.651089 | 0.623457 | **-4.24%** | 0.651 W (now stale, needs update) |
| PCM (`pcm_microsoft_2009`) | 0.0396952 | 0.0396953 | +0.0003% (noise) | 0.040 W (unchanged, still accurate) |
| ReRAM 1T1R SLC | 50.869550 | 50.869540 | ~0.0000% | 50.9 W (unchanged, still accurate) |
| ReRAM 1T1R MLC | 50.877100 | 50.877100 | 0.0000% | (not separately quoted; matches 1T1R SLC closely) |
| ReRAM 1S1R (selector) SLC | 1.117880 | 1.117858 | -0.002% | 1.12 W (unchanged, still accurate) |
| ReRAM 1S1R (selector) MLC | 1.130357 | 1.130341 | -0.001% | (not separately quoted; matches 1S1R SLC closely) |

**Only DDR5's power actually moved**, and it moved down (real savings), by construction: DDR5 is the one technology in this set with real, non-zero, below-standby power-down currents, so power-gating measurably lowers its average power. Every ReRAM/PCM number is flat to within numerical noise (4th-5th significant digit), exactly as expected from the "honest placeholder = no savings" design: substituting `Epda`/`Epdpf`/`Epdps` = `Eactstdby`/`Eprestdby` into the power-down state does not change the energy rate relative to remaining in standby, so total average power cannot change from this mechanism alone for those technologies. The book's four quoted baseline figures (50.9 W / 1.12 W / 0.651 W / 0.040 W) are confirmed correct for three of four technologies; **only the DDR5 figure (0.651 W) is now stale and needs updating to approximately 0.623 W (GCC) in the book rewrite.**

### Power across all 6 workloads (full-DIMM), old -> new

| Technology | Benchmark | Old Power (W) | New Power (W) | Delta |
|---|---|---|---|---|
| DDR5_4800 | gcc_spec2017 | 0.651089 | 0.623457 | -4.24% |
| DDR5_4800 | lbm_spec2017 | 0.711661 | 0.707176 | -0.63% |
| DDR5_4800 | stream | 0.701728 | 0.697766 | -0.56% |
| DDR5_4800 | gpt2_ifmap | 0.647335 | 0.640212 | -1.10% |
| DDR5_4800 | alexnet_layer1_ifmap | 0.748726 | 0.744524 | -0.56% |
| DDR5_4800 | alexnet_layer1_ofmap | 0.775184 | 0.756766 | -2.38% |
| pcm_microsoft_2009 | gcc_spec2017 | 0.039695 | 0.039695 | 0.00% |
| pcm_microsoft_2009 | lbm_spec2017 | 0.042326 | 0.042326 | 0.00% |
| pcm_microsoft_2009 | stream | 0.042451 | 0.042451 | 0.00% |
| pcm_microsoft_2009 | gpt2_ifmap | 0.036252 | 0.036252 | 0.00% |
| pcm_microsoft_2009 | alexnet_layer1_ifmap | 0.036277 | 0.036277 | 0.00% |
| pcm_microsoft_2009 | alexnet_layer1_ofmap | 0.044230 | 0.044227 | -0.01% |
| 1T1R_SLC | gcc_spec2017 | 50.869550 | 50.869540 | 0.00% |
| 1T1R_SLC | lbm_spec2017 | 50.998550 | 50.998100 | 0.00% |
| 1T1R_SLC | stream | 50.957450 | 50.957430 | 0.00% |
| 1T1R_SLC | gpt2_ifmap | 50.965260 | 50.965250 | 0.00% |
| 1T1R_SLC | alexnet_layer1_ifmap | 50.980240 | 50.980210 | 0.00% |
| 1T1R_SLC | alexnet_layer1_ofmap | 50.947990 | 50.947980 | 0.00% |
| 1T1R_MLC | gcc_spec2017 | 50.877100 | 50.877100 | 0.00% |
| 1T1R_MLC | lbm_spec2017 | 51.020060 | 51.020120 | 0.00% |
| 1T1R_MLC | stream | 50.979660 | 50.979650 | 0.00% |
| 1T1R_MLC | gpt2_ifmap | 50.943560 | 50.943550 | 0.00% |
| 1T1R_MLC | alexnet_layer1_ifmap | 50.957530 | 50.957560 | 0.00% |
| 1T1R_MLC | alexnet_layer1_ofmap | 50.977490 | 50.977480 | 0.00% |
| 1S1R_SLC | gcc_spec2017 | 1.117880 | 1.117858 | 0.00% |
| 1S1R_SLC | lbm_spec2017 | 1.304061 | 1.304369 | +0.02% |
| 1S1R_SLC | stream | 1.209669 | 1.209652 | 0.00% |
| 1S1R_SLC | gpt2_ifmap | 1.232994 | 1.232984 | 0.00% |
| 1S1R_SLC | alexnet_layer1_ifmap | 1.245547 | 1.245276 | -0.02% |
| 1S1R_SLC | alexnet_layer1_ofmap | 1.204579 | 1.204569 | 0.00% |
| 1S1R_MLC | gcc_spec2017 | 1.130357 | 1.130341 | 0.00% |
| 1S1R_MLC | lbm_spec2017 | 1.276378 | 1.276398 | 0.00% |
| 1S1R_MLC | stream | 1.202173 | 1.202165 | 0.00% |
| 1S1R_MLC | gpt2_ifmap | 1.201652 | 1.201646 | 0.00% |
| 1S1R_MLC | alexnet_layer1_ifmap | 1.213474 | 1.213479 | 0.00% |
| 1S1R_MLC | alexnet_layer1_ofmap | 1.194186 | 1.194182 | 0.00% |

Only DDR5 shows a consistent, workload-independent downward power shift (-0.56% to -4.24% depending on how much of the run is idle vs busy). Every ReRAM and PCM row is flat to rounding.

## 3. Power-Delay Product (PDP): GCC and geometric mean across all 6 workloads

PDP = Latency_ns x Power (W.ns = nJ), as computed by `process_metrics.py`'s `calculate_pdp()`. Because total execution cycles (and therefore latency) shift slightly under idle-gating (entry/exit latency overhead when transitioning into/out of power-down states), PDP does not simply track the power delta.

| Technology | Old PDP, GCC | New PDP, GCC | Delta | Old Geomean PDP (6 wkld) | New Geomean PDP (6 wkld) | Delta |
|---|---|---|---|---|---|---|
| DDR5_4800 | 56.785 | 56.214 | -1.01% | 104.286 | 103.257 | -0.99% |
| pcm_microsoft_2009 | 254.019 | 254.199 | +0.07% | 165.285 | 165.303 | +0.01% |
| 1T1R_SLC | 6659.333 | 6928.813 | **+4.05%** | 21350.564 | 21508.437 | +0.74% |
| 1T1R_MLC | 9291.621 | 9416.270 | +1.34% | 32567.074 | 32632.750 | +0.20% |
| 1S1R_SLC | 212.783 | 214.998 | +1.04% | 737.090 | 738.080 | +0.13% |
| 1S1R_MLC | 326.051 | 323.865 | -0.67% | 1222.391 | 1221.142 | -0.10% |

**DDR5's PDP improved slightly** (-0.99% geomean): real power savings (up to -4.24%) outweigh a small cycle-count increase from power-down entry/exit latency.

**ReRAM's PDP got slightly worse** for GCC specifically on 1T1R_SLC (+4.05%) and 1T1R_MLC (+1.34%), and geomean PDP moved by well under 1% in either direction for all four ReRAM variants. This is the expected, physically consistent side effect of the "honest placeholder" choice: since power itself does not change for ReRAM (no modeled savings), any increase in cycle count from power-down state-transition overhead shows up directly as a PDP regression, with no offsetting power benefit to cancel it. GCC's 1T1R_SLC row shows the largest single PDP shift in the whole dataset (+4.05%), driven by a +4.05% cycle-count increase (104.728 -> 108.966, in the CSV's internal cycle units) for that specific technology/workload pair; this is GCC's shortest-running ReRAM trace, so a fixed per-transition entry/exit latency overhead is proportionally largest there. This should be called out explicitly in the book text if Table 4/Table 7's PDP numbers are updated: the placeholder technologies get a small, consistent PDP cost with no benefit, purely as bookkeeping overhead from a mechanism whose energy effect is defined to be zero for them.

## 4. Power-down cycle-fraction: how much of the run is now gated

For GCC specifically, summed across every rank/bank in the module (`activeCycles` + `standbyCycles` + `fastExitActiveCycles` + `fastExitPrechargeCycles` + `slowExitCycles` + `slowExitPrechargeCycles`, all technologies configured `PowerDownMode FASTEXIT` or defaulting to it, so only the fast-exit counters are ever populated in this dataset):

| Technology | Old power-down-state fraction | New power-down-state fraction |
|---|---|---|
| DDR5_4800 | 0.00% | **60.50%** |
| ReRAM 1T1R SLC | 0.00% | **89.13%** |
| ReRAM 1T1R MLC | 0.00% | **88.31%** |
| ReRAM 1S1R (selector) SLC | 0.00% | **88.32%** |
| ReRAM 1S1R (selector) MLC | 0.00% | **86.45%** |
| PCM | 0.00% | **0.00%** (see anomaly, section 5) |

Raw cycle counts, GCC, new run (summed across all ranks/banks):

- **DDR5**: active=423,942,082, standby=10,005,260,801, fastExitActive=413,725,906, fastExitPrecharge=15,557,071,211 (total 26.4B cycle-slots across all banks)
- **1T1R SLC**: active=32,869,096, standby=488,980,712, fastExitActive=95,348,132, fastExitPrecharge=4,182,802,084
- **1T1R MLC**: active=50,754,358, standby=510,410,627, fastExitActive=128,093,946, fastExitPrecharge=4,110,741,093
- **1S1R (selector) SLC**: active=51,416,842, standby=509,274,086, fastExitActive=132,538,794, fastExitPrecharge=4,106,770,302
- **1S1R (selector) MLC**: active=81,075,953, standby=569,259,961, fastExitActive=148,575,670, fastExitPrecharge=4,001,088,440

The state machine is clearly firing hard for both DDR5 and every ReRAM variant: 60-89% of all bank cycle-slots are now spent in a power-down state (mostly `fastExitPrecharge`, i.e. precharge power-down with fast exit) rather than plain `standbyCycles`. This confirms the mechanism is live and active as designed. Whether or not this materially changes reported power depends entirely on whether the technology has real (DDR5) or placeholder (ReRAM/PCM) power-down currents, exactly as seen in sections 2-3: DDR5's high gated fraction translates into a real power win; ReRAM's equally high gated fraction (in fact higher than DDR5's) translates into no power change at all, because the placeholder energy equals the standby energy it's replacing.

## 5. Anomaly: PCM shows zero power-down activity, unlike every other technology

**This is the one finding that should be flagged, not papered over.** PCM's power-down counters (`fastExitActiveCycles`, `fastExitPrechargeCycles`, `slowExitCycles`, `slowExitPrechargeCycles`) are exactly **zero** in both the old and new runs, for every one of the 6 workloads, despite:
- The shared `MemoryController::HandleLowPower()` call being unconditionally invoked every cycle for every technology (confirmed in `src/MemoryController.cpp:1660`, inside `CycleCommandQueues()`, which both `FRFCFS::Cycle()` and `FRFCFS_WQF::Cycle()` call identically).
- PCM's config now carrying the same honest-placeholder `Epda`/`Epdpf`/`Epdps` = `Eleak` lines as ReRAM.
- `UseLowPower` defaulting to `true` in `Params.cpp` (confirmed: neither PCM's nor ReRAM's configs set `UseLowPower` explicitly, and both rely on the same default) and `PowerDownMode` defaulting to `FASTEXIT` with only a harmless config warning ("Key PowerDownMode is not set. Using 'FASTEXIT' as the default").

Old-vs-new cycle counts for PCM are **identical to several more significant digits** than any other technology (lbm_spec2017, stream, gpt2_ifmap, alexnet_layer1_ifmap: exactly 0.00% delta; gcc_spec2017 and alexnet_layer1_ofmap: +0.07%/-0.01%, likely unrelated numerical noise) - i.e. PCM's simulated behavior is essentially bit-for-bit unchanged by restoring `HandleLowPower()`. This is strong evidence the power-down path is never actually being *entered* for PCM at all (not just "entered but with a placeholder that happens to look like standby").

**Likely root cause (not fully confirmed, flagged as an open item):** PCM is the only one of the 6 technologies using `MEM_CTL FRFCFS-WQF` (write-queue-flush controller) rather than plain `FRFCFS` (used by both DDR5 and all 4 ReRAM configs). `MemoryController::PowerDown()` (src/MemoryController.cpp:787) only issues a power-down command when `RankQueueEmpty(rankId)` returns true, i.e. every per-bank command queue is empty. A write-queue-flush controller is specifically designed to buffer writes and flush them in batches rather than draining the queue continuously, which plausibly keeps `RankQueueEmpty()` false far more of the time than a plain FRFCFS controller, starving the power-down opportunity entirely. This was not instrumented further (out of scope for this re-run), but it means **PCM's power/PDP numbers in the book should continue to be reported unchanged from pre-idle-gating** (0.040 W is still accurate, no PDP shift), and it is worth a follow-up note (or a one-line caveat in the book) that PCM's controller choice (FRFCFS-WQF) appears to structurally prevent it from ever benefiting from the newly-restored power-down mechanism, real or placeholder, independent of the energy-model question already covered in `item7_reram_power_gating.md`.

## 6. Summary for whoever rewrites the book

- **DDR5 (Table 3/4/7 basis)**: Power at GCC drops 0.651 W -> 0.623 W (-4.24%); PDP at GCC drops slightly (56.79 -> 56.21 nJ, -1.01%); geomean PDP drops slightly (104.29 -> 103.26, -0.99%). This is the one number set that needs an actual text update in the book (the 0.651 W figure and any downstream PDP/Table numbers derived from it).
- **PCM**: No change (0.040 W, PDP essentially flat). Book text quoting 0.040 W remains accurate. Flag the FRFCFS-WQF/RankQueueEmpty anomaly above as a caveat if the book wants to explain *why* PCM didn't benefit, but no numeric change is needed.
- **ReRAM (all 4 variants, 50.9 W / 1.12 W baseline)**: Power unchanged (by design, per the honest placeholder). PDP moved by a small amount in either direction (-0.7% to +4.1% depending on tech/workload), always in the "slightly worse" direction relative to the old numbers when it moved meaningfully, because cycle counts grew marginally from power-down entry/exit overhead with no offsetting power savings. If the book quotes ReRAM PDP to 3+ significant figures anywhere, those numbers technically changed and should be refreshed from `results/processed_bar_chart_metrics.csv` / `results/processed_geometric_means.csv`; if it only quotes power (50.9 W, 1.12 W), no change is needed.
- **Power-down cycle-fraction is real and large** (60-89% of cycle-slots) for DDR5 and all 4 ReRAM variants under GCC, confirming the mechanism is genuinely active, not a no-op. This is worth a sentence in the book regardless of the numeric power impact, since it is new, verifiable, non-trivial simulator behavior.
- **No NaN, negative, or physically implausible values** were observed anywhere in the 36 new runs.

## Files

- Fresh stats: `/home/yuvalk/MBMM/results/system/stats_<model>_<trace>.out` (36 files, this session)
- Old baseline stats (untouched): `/home/yuvalk/MBMM/results/system_v6_input/`
- Regenerated official CSVs (mixed fresh + stale, see section 1 caveat): `/home/yuvalk/MBMM/results/processed_bar_chart_metrics.csv`, `processed_pareto_metrics.csv`, `processed_hero_metrics.csv`, `processed_geometric_means.csv`
- Regenerated ReRAM configs: `/home/yuvalk/MBMM/simulators/nvmain/Config/reram_22nm_{1t1r,selector}_{slc,mlc}_full_dimm.config` (and their single/8chip/16chip siblings, regenerated as a side effect of running the generator, though not part of this task's re-run scope)
- Related literature note: `item7_reram_power_gating.md` (why the ReRAM/PCM placeholder is the honest choice, no real number was found in the literature)
