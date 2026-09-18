# Revision plan: decisions and open questions

**Started:** 2026-09-17, after the 2026-09-15/16 investigations (time base, organization, endurance, Optane,
calibration). This file records what the Lead Researcher decided and what is still open. Nothing here is in the
book or deck yet.

## Round 1 decisions (Lead, 2026-09-17)

| # | Decision | Chosen |
|---|---|---|
| 1 | Next deliverable | Revised book and deck for Shahar's next review, at thesis quality. Date to confirm |
| 2 | When Shahar hears | After corrected results exist, not before, and as soon as possible |
| 3 | Trace window | Regenerate the traces with a fixed parser and a documented region of interest |
| 4 | Array organization | Matched 2048x2048 subarrays, mux 64, for both 1T1R and 1S1R; 1024x1024 as sensitivity |
| 5 | 1S1R physics | Add an analytic selector layer on top of NVSim (Zhou sinh model, handbook tile formula) |
| 6 | Endurance | 10^6 primary, 10^4 and 10^7 as bounds, plus the sensitivity table. **The Lead's top priority: Shahar's main concern; it needs real testing and explanation, not just a table** |
| 7 | MLC multipliers | Keep EMBER's per-bit values, relabeled as throughput ratios; per-line (6.5x write, 3x read) as sensitivity |
| 8 | Latency metric | Add an end-to-end latency statistic (trace timestamp to completion) before the re-run |
| 9 | ns vs us silicon | Keep NVSim as the array-core model and add a chip-level sensitivity case from fabricated-chip latencies |
| 10 | STREAM | Replace the synthetic kernel with a real traced STREAM run |
| 11 | AI traces | Fix the SCALE-Sim parser (about 10x address undercount, -1 padding) and regenerate |
| 12 | Workload set | The same six, all regenerated, plus 505.mcf |

## Evidence behind each decision

- Time base and trace window: `trace_timebase_investigation.md`
- Organization, calibration, selector physics: `leakage_47x_organization_artifact.md` §8-§14
- Endurance: `endurance_deep_dive.md`, especially §3.5 and §7
- Optane: `../Lead_Future_Work_Notes.md` §2b and §2c

## Open (Round 2 and later)

Replay-speed mechanism; region of interest and window length; endurance testing depth; selector baseline
parameters; latency-statistic scope; chip-level sensitivity implementation; re-run sequencing and gatekeeping;
book and deck revision strategy.

## NVMain prototype findings (2026-09-18)

Both prototypes are built and verified in the session scratchpad (`nvmain_probe/`, patches
`partA_e2e_latency.diff`, `partB_wear_map.diff`). The repo is untouched. Build: `scons -j8` gives `nvmain.fast`.

### A. End-to-end latency statistic: works, and the hidden wait is enormous

- **Patch site:** `MemoryController::RequestComplete` (`src/MemoryController.cpp:306`), the single point every
  completed transaction passes through, so FRFCFS, FRFCFS-WQF, FCFS and the DRC controllers are all covered
  with no edits to the controllers themselves. Plus `traceCycle` on `NVMainRequest` (declared, initialized,
  copied in `operator=`) stamped at `traceSim/traceMain.cpp:231`.
- **Clock-domain trap:** the trace cycle lives in the `CPUFreq` domain and `arrivalCycle`/`completionCycle` in
  the `CLK` domain (3000 vs 800 MHz here, a factor of 3.75). The patch converts, so the new stat is in memory
  cycles like the old one.
- **Measured (GPT-2 IFMAP, 1T1R SLC full DIMM):** `averageTotalLatency` 364.1 cycles vs
  `averageEndToEndLatency` 9,709.7 cycles. **The queue-full wait is 26.7x the reported latency**, about 11.7 us
  at 800 MHz. Every pre-existing statistic is bit-identical to the unpatched build. PCM under FRFCFS-WQF shows
  the same pattern (486.1 vs 9,866.0).
- Correctness check on a sparse trace with no backlog: 77.70 vs 77.36 cycles, the gap being sub-cycle truncation.
- **Caveat:** with a trace that outruns the device, this statistic grows with backlog and depends on the window
  length, unlike `averageTotalLatency`. Both must be reported with explicit definitions.

### B. Measured wear per location: available, and cheap at row granularity

- **One line does it:** `writeCounts[addr]++` in `EnduranceModel::DecrementLife` (`src/EnduranceModel.cpp:96`),
  the choke point for all four real models, plus six stats in `SubArray::CalculateStats`
  (`wearLocations`, `wearTotalWrites`, `wearMaxWrites`, `wearMeanWrites`, `wearHotSpotFactor`, `wearHisto`,
  `wearTopLocations`).
- **Today NVSim-side wear stats are useless:** only `worstCaseEndurance` (prints UINT64_MAX from an empty map)
  and `averageEndurance` (0) exist.
- **Costs, measured:** with an added `NeedsOldData()` short-circuit for RowModel and WordModel, RowModel costs
  **0 MB and no measurable time**, WordModel about 10 MB on a 100k-write trace. Cost scales with the trace's
  write footprint (about 139 bytes per touched location), not with capacity.
- **Prototype result:** on a deliberately skewed trace, WordModel reports `wearMaxWrites` 16,014 and a DIMM-wide
  **hot-spot factor of 2,831**. This is exactly the measurement that replaces "ideal uniform wear leveling".
- **Blockers found:** `BitModel` and `ByteModel` are dead with our traces (all-zero data plus a real bug in
  `SimInterface::GetDataAtAddress`, `src/SimInterface.cpp:40-55`, which assigns the local pointer instead of
  copying the block), so data-dependent wear (write only changed bits) stays a literature factor. Setting
  `EnduranceModel` without `EnduranceDist` segfaults. Write counts cannot be recovered from the `life` map.
- **Wear leveling:** NVMain has none, and no Start-Gap. The right seam is a new `AddressTranslator` subclass
  (like `Decoders/Migrator`), with three pitfalls: the decoder is instantiated at six hierarchy levels, so the
  gap pointer must be shared; `ReverseTranslate` must be the exact inverse; and advancing the gap needs a hook
  or controller-side injector.

### Two config defects found along the way

1. **The full-DIMM config models 512 GB, not 8 GB.** `reram_22nm_1t1r_slc_full_dimm.config` gives
   ROWS 131072 x COLS 1024 x 64 B x 8 ranks x 8 banks, and NVMain prints "capacity is 524288 MB". The book
   describes an 8 GB module (64 chips of 1 Gb) and calls the gap a generator artifact affecting neither timing
   nor energy. It does affect address mapping, which is the mechanism behind the Section 3.2 scaling result.
2. **`DECODER MigratingDecoder` is dead in every ReRAM config** (`Config/reram_22nm_*.config:13`). The key
   NVMain reads is `Decoder` (case-sensitive) and the factory knows only `Default`, `DRCDecoder`, `Migrator`.
   The configs silently run the default decoder. Also `STATS_OUT` is ignored by traceSim, which honors
   `StatsFile`.

## Round 2 and 3 decisions (Lead, 2026-09-18)

Target: **two weeks**, moving as fast as correctness allows.

| # | Decision | Chosen |
|---|---|---|
| 13 | Deadline | Two weeks from 2026-09-18 |
| 14 | Simulation length | Keep 500 M skipped instructions, raise the detailed region to 300 M (about 200 ms), 30-60 min per benchmark |
| 15 | Cache warm-up | Discard the first 10 ms of the detailed region; the window starts after it |
| 16 | Timestamp unit | Parser emits NVMain cycles on the 3 GHz basis, `CPUFreq 3000` unchanged, unit recorded in a sidecar file |
| 17 | mcf | Added as a seventh workload with the reference input, in every figure and table |
| 18 | Selector model | Both bounds: OTS-like 10^4 as the headline, Crossbar-class 10^6 as best case |
| 19 | Microsecond-silicon case | Real NVMain configs at fabricated-chip latencies, run on the same traces |
| 20 | Re-run sequencing | Pilot first (one ReRAM track plus DDR5, GCC and LBM), verify directions, then the full matrix |
| 21 | Book revision format | **Open.** The Lead wants old results kept and new results shown, without flooding the book |
| 22 | Endurance depth | Measured wear counter **plus** a Start-Gap wear-leveling remapper, so hot-spot is measured before and after |
| 23 | Latency reporting | Current statistic stays primary; end-to-end reported alongside as the saturation measure, both defined |
| 24 | Simulated capacity | Fix the generator so capacity matches the physical module (8 GB SLC, 16 GB MLC); expect §3.2 mapping results to move |
| 25 | Dead config lines | Clean up `DECODER MigratingDecoder`, `STATS_OUT`, the missing `EnduranceDist` |

**New question raised by the Lead (16b):** the ReRAM DIMM interface is modeled at 800 MHz, which suits older
parts. Should it be raised, for example to DDR5-comparable speed? Under investigation.

## Round 3 decisions (Lead, 2026-09-18)

| # | Decision | Chosen |
|---|---|---|
| 26 | Book format | One book with corrected numbers inline, plus a "What changed since the 3 September version" appendix (old value, new value, cause, evidence note). The old PDF stays frozen in the repo |
| 27 | Old data | Move current results to `results/archive_2026-09_pre_revision/` and tag the commit; new runs write to the normal locations |
| 28 | Deck and one-pager | Rebuild the deck around the new story, decided once the results land; the one-pager is rewritten then too |
| 29 | Who runs gem5 | Either the assistant runs the SPEC traces, or the Lead runs them in a parallel terminal. Scope of SPEC access to be confirmed |
| 30 | Scope under time pressure | Cut nothing; extend past two weeks if needed |

## Round 4 decisions (Lead, 2026-09-18)

| # | Decision | Chosen |
|---|---|---|
| 31 | SPEC access | Narrow, task-scoped exception: the assistant may run gem5 from the SPEC run directories on the benchmark binary and its reference input, reading only what that run needs. No indexing or searching the tree. Recorded in `MBMM/CLAUDE.md` |
| 32 | Pilot gate | All six criteria must pass (latency down and DDR5 gap narrower, completion up, write rates down about 3x, unrelated stats bit-identical, NVSim prints 2048x2048, new stats self-consistent). Any failure stops the full run until explained. Results recorded here |
| 33 | NVMain patches | Separate documented commits, patch log in `simulators/nvnmain/CLAUDE.md` (and fix its wrong NVSim parser claim), each gated by a bit-identical regression run |
| 34 | STREAM | Real STREAM, default arrays (about 80 MB each), static, OpenMP off, all four kernels |
| 35 | Raw gem5 logs | Kept until the book is finished, then deleted, with the parser sidecar retained |

## Round 5 decisions (Lead, 2026-09-18)

| # | Decision | Chosen |
|---|---|---|
| 36 | Interface clock | 800 MHz stays the baseline; declared sensitivity axis at 800 / 1333 / 2400, with 1333 as the citable Optane DDR-T precedent |
| 37 | Read double-count | Fix it (activate plus column access sums to the device read latency), and report the correction prominently in the change appendix. This is the largest single correction of the revision |
| 38 | Channel count | Run both: one channel (product-style) and two channels matched to DDR5; the matched case is primary |
| 39 | Burst width | Sensitivity run at 64 and 128 bytes, falling back to 64 only if 128 cannot be modeled honestly. **Open question from the Lead: would 128 actually be better, and is there evidence?** Under investigation |
| 40 | Guardrail visibility | Exception recorded in `MBMM/CLAUDE.md` guardrail 3, with a pointer added to the parent `/home/yuvalk/CLAUDE.md` rule 2 |

Evidence for 36 and 37: `interface_clock_study.md`.

## Decision 39 resolved (2026-09-18)

**64 bytes for ReRAM, and DDR5 corrected to 64 bytes too.** Evidence: `access_granularity_study.md`.
128 bytes costs 57-75% in latency and 43-50% in lifetime, gains nothing at the device (identical area and
leakage, slightly worse energy per byte), and cannot be modeled honestly because NVMain's address translator is
hardwired to a 64-byte grid. The wide-internal-word idea survives as future work in Optane's form: a 64-byte bus
transaction in front of a wider internal word with a write-combining buffer.

**New items surfaced by that study (Round 6, pending):** DDR5 subchannel fidelity and the false §434 and §513
claims; the 2x-inflated bandwidth metric in `5_summary_report.py`; the stale tracked
`configs/DDR5_4800_DRAM.config`; generator validation for `tCCD >= tBURST`, `tRAS >= tRCD + tBURST` and
`CLK <= CPUFreq`.

## Round 6 decisions (Lead, 2026-09-18)

| # | Decision | Chosen |
|---|---|---|
| 41 | DDR5 baseline | Build the honest subchannel config (32-bit bus, 2 subchannels, BL16 = 64 B, 32 banks, corrected capacity) **and** run the minimal 64-byte fix as a cross-check, to separate granularity from module shape |
| 42 | Bandwidth metric | Compute delivered bandwidth in `5_summary_report.py` from completed requests x 64 B / elapsed time; NVMain's figure kept only as a cross-check |
| 43 | Stale tracked DDR5 config | Delete `configs/DDR5_4800_DRAM.config`, record the deletion and its reason in the project files, and add a pipeline check that fails when a tracked config diverges from the live one |
| 44 | Generator validation | `3_gen_nvmain_config.py` refuses invalid combinations (`tCCD >= tBURST`, `tRAS >= tRCD + tBURST`, `CLK <= CPUFreq`), verified through `mbmm_master.py` |

**The design tree is complete.** All 44 decisions are recorded. Execution plan follows.
