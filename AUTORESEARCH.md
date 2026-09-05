# AUTORESEARCH.md - write-queue size sweep (LBM)

Run tag: `queue-sweep-lbm`. Branch: `autoresearch/queue-sweep-lbm`.
Origin: Shahar Kvatinsky's meeting note #5 (`documents/MBMM_Book_Typst/Post_Meeting_Notes_Shahar_2026-09-03.md`).

## What we're testing

Every ReRAM NVMain config in this project uses the plain `FRFCFS` memory controller,
which reads a single combined `QueueSize` key (default 32, hardcoded in
`simulators/nvmain/MemControl/FRFCFS/FRFCFS.cpp`). None of the generated ReRAM configs
set `QueueSize` explicitly - it's silently defaulting. (Note: the `ReadQueueSize`/
`WriteQueueSize` keys seen in some static example configs like DDR5's and PCM's belong
to a *different* controller, `FRFCFS-WQF` - only PCM's config actually uses that
controller; ReRAM and DDR5 both use plain `FRFCFS` and ignore those keys entirely.)

Question: does raising `QueueSize` change LBM's completed-request count within the
fixed matched-host simulation window, narrowing the gap to DDR5's completion rate?

## Editable surface

- `simulators/nvmain/Config/reram_22nm_1t1r_slc_single.config`
- `simulators/nvmain/Config/reram_22nm_1t1r_slc_full_dimm.config`

Only the `QueueSize` key (a new line added under `MEM_CTL FRFCFS`) may be touched.
Nothing else in these files, and no other config file, is in scope.

## Eval command

Single-chip (fast, primary sweep surface):
```
timeout 90 ./simulators/nvmain/nvmain.fast simulators/nvmain/Config/reram_22nm_1t1r_slc_single.config benchmarks/lbm_spec2017.nvt 66666667 > run.log 2>&1
```

Full DIMM (slower, used only to confirm the best value found on single-chip):
```
timeout 180 ./simulators/nvmain/nvmain.fast simulators/nvmain/Config/reram_22nm_1t1r_slc_full_dimm.config benchmarks/lbm_spec2017.nvt 66666667 > run.log 2>&1
```

`66666667` is the correct matched-host cycle count for ReRAM's 800 MHz clock at
CPUFreq 3000 (reproduces the book's own 83.33 ms matched-host window - verified by
reproducing the existing cached baseline stats exactly before starting this run).

Metric extraction:
```
grep '^i0\.defaultMemory\.channel0\.FRFCFS\.mem_reads\|^i0\.defaultMemory\.channel0\.FRFCFS\.mem_writes\|^i0\.defaultMemory\.channel0\.FRFCFS\.averageTotalLatency' run.log
```

## Metric

`total_completed = mem_reads + mem_writes` - **higher is better** (more of the fixed
admitted trace completes within the window; closes the gap toward DDR5's completion
rate in the same window). Tie-break: `averageTotalLatency` - lower is better.

No noise margin needed: NVMain trace replay is fully deterministic given fixed config
+ trace + cycle count (re-running the baseline reproduced the existing cached result
to the exact integer). Any strict improvement in `total_completed` counts as `keep`.

## Reproduced baselines (verified before starting the loop)

| Config | mem_reads | mem_writes | total_completed | avgTotalLatency | wall-clock |
|---|---|---|---|---|---|
| single | 2,499,233 | 2,464,273 | **4,963,506** | 472.832 | ~43s |
| full_dimm | 3,304,439 | 3,269,479 | **6,573,918** | 374.497 | ~117s |

## Constraints

- No new dependencies, no touching `prepare`-equivalent files (NVMain source,
  `3_gen_nvmain_config.py`, any other technology's config).
- Simplicity criterion: not applicable here (a single integer config value - no
  complexity tradeoff to weigh).
- CLAUDE.md guardrail 2 (mbmm_master.py gate-keeper) does not apply: this loop invokes
  `nvmain.fast` directly for fast iteration and does not modify any Python pipeline
  stage. If a result from this sweep is later adopted into the real pipeline/book, it
  goes through `3_gen_nvmain_config.py` and the normal `mbmm_master.py` verification at
  that point, not during this exploratory loop.
- Git: `settings.json`'s deny rule blocks `git commit`/`git push` outright and Claude
  Code's own permission classifier refuses to let that rule be loosened, even on
  explicit request - so this run does NOT commit per iteration as the skill normally
  would. Instead: each edit is preceded by a plain file copy of the config
  (`<config>.bak`), and a discard restores from that copy - no git operations during
  the loop at all. At the end, if a value is worth keeping, the Lead Researcher runs a
  single `git commit` themselves (via `!`) covering the kept change plus this branch's
  setup files. No push, no merge, by this loop, ever.

## Loop ceiling

12 iterations total (commits), combined across both configs. Plan: baseline + a
QueueSize sweep on `single` (fast, ~45s/run) to find the best value, then confirm that
value (plus baseline) on `full_dimm` (~2min/run) with remaining budget.

## Results log

See `autoresearch_results.tsv` (git-ignored, not tracked) in the repo root.
