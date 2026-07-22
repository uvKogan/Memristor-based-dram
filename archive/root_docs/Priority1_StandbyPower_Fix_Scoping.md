# Priority-1 Fix Scoping: ReRAM Static Power Derivation

**Status: scoping only. No config, code, or results files have been changed.**
Verified clean: `git status --short` shows only the three files already modified in the
prior (unrelated) power-decomposition session; nothing touched during this audit or this
scoping pass.

Verdict accepted from the prior audit: `StandbyPower` is dead NVMain config (never read by
any `.cpp`/`.h` in the tree). Real ReRAM static power currently comes from NVMain's
`Eactstdby`/`Eprestdby` defaults (`0.09009`/`0.083333` nJ), which are identical for every
ReRAM technology — 1T1R and 1S1R currently simulate to the same ~68mW leakage floor despite
a 47× real difference in NVSim-characterized chip leakage (794.656mW vs 16.907mW).

---

## 1. Derivation spec

### NVMain's semantics (quoted)

`Ranks/StandardRank/StandardRank.cpp:882-940`, inside `StandardRank::Cycle(ncycle_t steps)`
— called every simulation cycle, **at rank granularity**:

```cpp
/* active standby */
case STANDARDRANK_REFRESHING:
case STANDARDRANK_OPEN:
    activeCycles += steps;
    if( p->EnergyModel == "current" )
        backgroundEnergy += ( p->EIDD3N * (double)steps ) * (double)deviceCount;
    else
        backgroundEnergy += ( p->Eactstdby * (double)steps );
    break;

/* precharge standby */
case STANDARDRANK_CLOSED:
    standbyCycles += steps;
    if( p->EnergyModel == "current" )
        backgroundEnergy += ( p->EIDD2N * (double)steps ) * (double)deviceCount;
    else
        backgroundEnergy += ( p->Eprestdby * (double)steps );
    break;
```

Then `StandardRank.cpp:999`: `backgroundPower = backgroundEnergy / simulationTime`.

**Critical semantic point**: for `EnergyModel != "current"` (our ReRAM `NonVolatile` model),
there is **no `deviceCount` multiplication** — `Eactstdby`/`Eprestdby` are charged once per
rank per cycle, full stop. Contrast with the `"current"` branch (DDR5/PCM), where `EIDD3N`
etc. are explicitly per-device datasheet currents and get multiplied by `deviceCount` to
reach rank scale. **This means `Eactstdby`/`Eprestdby`, as NVMain expects them, must already
represent the whole rank's (all `devices_per_rank` chips, assumed in lockstep) standby draw
per cycle — not a single chip's.** Any per-chip NVSim number must be pre-scaled by
`devices_per_rank` before being written into these keys — same principle the original
(buggy) code was reaching for, just landing in the wrong field with the wrong units.

Two states only in practice, confirmed against real data below — `STANDARDRANK_OPEN` (row
open, "active standby") and `STANDARDRANK_CLOSED`/default (all banks precharged, "precharge
standby"). NVSim's single "Leakage Power" figure doesn't distinguish these; the simplification
below sets `Eactstdby = Eprestdby` — **flagging this as an assumption for reviewer sign-off**,
not an established fact. ReRAM crossbar leakage (sneak-path current) is plausibly closer to
state-independent than DRAM cell leakage is, but nothing in our NVSim output confirms this.

### Proposed formula

```
E [nJ per rank per NVMain cycle] = chip_leakage_mW × devices_per_rank / CLK_MHz
```

Dimensional check: `mW / MHz = (1e-3 W) / (1e6 Hz) = 1e-9 J = nJ`. Exact, no hidden scale error.

Equivalently, per-rank steady-state background power in Watts (what actually lands in the
stats file, since the `CLK` term cancels — leakage power is frequency-independent, as it
should be):

```
backgroundPower[rank, W] = chip_leakage_mW × devices_per_rank / 1000
```

### Worked examples (full_dimm: `devices_per_rank=8`, `CLK=800MHz`, `RANKS=8`)

| | chip leakage (NVSim, 1 chip) | `Eactstdby = Eprestdby` (nJ/cycle) | per-rank `backgroundPower` (W) | full-DIMM background, 8 ranks summed (W) |
|---|---|---|---|---|
| 1T1R SLC | 794.656 mW | **7.9466** | **6.357248** | **50.857984** |
| 1S1R SLC | 16.907 mW | **0.16907** | **0.135256** | **1.082048** |

Notable: the full-DIMM summed totals (50.858 W, 1.082 W) are numerically **identical** to
the original buggy `StandbyPower` values — confirming the original arithmetic
(`leakage_mw/1000 × total_devices`) was accidentally computing the *correct number* for a
*different quantity* (full-DIMM watts) than what it was feeding (a dead field, wrong
implied unit). The fix isn't really new arithmetic — it's redirecting the existing
`scaled_leakage_w` computation to the right field, divided by `RANKS` to get to per-rank
scale, and converted to per-cycle nJ.

### Where the fix would go

`3_gen_nvmain_config.py:46-50` — replace the `StandbyPower` write (line 98) with:
```python
rank_leakage_w = base_leakage_w * devices_per_rank      # per-rank, not total_devices
e_standby_nj = rank_leakage_w * cycle_time_ns            # nJ per NVMain cycle
```
and emit `Eactstdby {e_standby_nj}` / `Eprestdby {e_standby_nj}` instead of `StandbyPower`.

---

## 2. NVMain low-power model — documented, and mostly dead

Config defaults (`src/Params.cpp:107-108`, confirmed applied via the `Config: Warning: Key
UseLowPower is not set. Using 'true'...` / `PowerDownMode ... 'FASTEXIT'` lines every stats
file already shows): `UseLowPower=true`, `PowerDownMode=FASTEXIT`. Neither is explicitly set
by any of our configs — both are silently defaulted.

**States implemented**: `STANDARDRANK_PDA` (active powerdown, charged `Epda`),
`STANDARDRANK_PDPF` (precharge powerdown fast-exit, `Epdpf`), `STANDARDRANK_PDPS` (precharge
powerdown slow-exit, `Epdps`) — chosen by `PowerDownMode` in `MemoryController::PowerDown()`
(`src/MemoryController.cpp:787-816`).

**But the trigger is dead code**: `MemoryController.cpp:1650`:
```cpp
//HandleLowPower( );
```
`HandleLowPower()` (`MemoryController.cpp:841`) is the *only* place that ever calls
`PowerDown()`/`PowerUp()`, and its own single call site is commented out. No rank, in any of
our simulations, ever transitions into `PDA`/`PDPF`/`PDPS`.

**Empirical confirmation** — every stats file, every technology, `fastExitActiveCycles=0`,
`fastExitPrechargeCycles=0`, `slowExitCycles=0` (checked 1T1R SLC, 1S1R SLC, **and DDR5** for
GCC). `activeCycles + standbyCycles` sums exactly to the simulated cycle count
(40,986,830 + 159,013,170 = 200,000,000 for 1T1R SLC/GCC) — confirming those two states are
the *only* ones ever occupied, for every technology, today.

**Consequence for the derivation**: `Epda`/`Epdpf`/`Epdps` are irrelevant to every current
and near-future result regardless of what value they hold — they're unreachable without an
NVMain source change (uncommenting `HandleLowPower()`, and probably fixing an adjacent logic
issue: as written, the non-refresh branch calls `PowerUp()` when a rank is *already* powered
down and `PowerDown()` when it isn't — i.e., it looks like it toggles rather than gates on
idleness; this would need review before being wired in, not just uncommented).

---

## 3. Policy options — decision table (back-of-envelope, labeled as such)

Baseline for comparison: **DDR5-4800 GCC reported total = 0.136 W** (today's `Power` column,
one rank of two channels × two ranks).

| Policy | Mechanism | 1T1R SLC predicted (full-DIMM background, summed 8 ranks) | 1S1R SLC predicted | vs DDR5 (0.136W) | Achievable today? |
|---|---|---|---|---|---|
| **(a) No gating / all-active standby** | `Eactstdby=Eprestdby` derived per §1, no powerdown | **50.86 W** background alone (+ ~18mW dynamic, negligible by comparison) | **1.08 W** background (+ ~68mW dynamic) | 1T1R: **~374×** DDR5. 1S1R: **~8×** DDR5. | Yes — config-only change, no NVMain source touch. |
| **(b) NVMain default powerdown, as configured today** | `UseLowPower=true`/`FASTEXIT` set, but `HandleLowPower()` dead — mechanism never fires | **Unchanged from today: ~0.069 W** (generic default, technology-blind) | **Unchanged from today: ~0.069 W** | ~0.5× DDR5 (today's number) | Yes — this is what we already have; "fixing" the config here changes nothing. |
| **(c) Aggressive idle-rank/bank gating** | Wire `HandleLowPower()` back in (source change), fix its toggle logic, derive `Epda`/`Epdpf`/`Epdps` from *something* — no NVSim datapoint distinguishes powered-down leakage from standby leakage, so those constants would themselves need an assumption (e.g. DRAM self-refresh literature suggests 10-20% of standby leakage survives power-gating — **not verified for ReRAM crossbars**, where sneak-path current may not respond the same way to word-line/bit-line gating) | Speculative: if idle ranks gate to ~15% of (a)'s per-rank background, full-DIMM total ≈ 6.36 + 7×(6.36×0.15) ≈ **13.0 W** | ≈ 0.135 + 7×(0.135×0.15) ≈ **0.28 W** | 1T1R: ~96× DDR5. 1S1R: ~2× DDR5. | **No** — requires an NVMain source change beyond config, plus an unvalidated ReRAM-specific gating-efficacy assumption. |

**This table is the actual decision point.** (a) is the physically-honest "what does NVSim's
own leakage characterization say a real, ungated full DIMM would draw" — and it says ReRAM
is *dramatically* worse than DDR5 on leakage alone, which may be uncomfortable relative to
the thesis's current "zero-leakage non-volatile physics" framing, but it's what the input
data supports. (b) is a no-op — flagging it only so it's clear "leave it as-is" is a real,
nameable option, not silence. (c) requires source-level work and an assumption we can't
derive from anything in this repo; if that's the direction, it becomes its own scoped
sub-project, not a config regeneration.

---

## 4. Total-power semantics — `extract_total_power()` under-counts idle ranks, and not consistently across technologies

`process_metrics.py`'s `extract_total_power()` takes the **max single rank's** `totalPower`
across the whole stats file as "Total System Power" (deliberate choice, per its own comment:
picks the most-loaded rank so a narrow-footprint workload doesn't get diluted by idle ranks
in a median/mean). Per `StandardRank.cpp:CalculateStats()`, NVMain's `rank_N.totalPower` is
**exactly that — one rank**, aggregated across that rank's own banks only. There is no
channel- or module-level `totalPower` aggregate anywhere in NVMain's output (confirmed: no
`defaultMemory.totalPower` / `channel0.totalPower` field exists in any stats file).

**The other ranks are not idle-and-free** — under today's model, background power is nearly
uniform across ranks regardless of load (§1's finding), so every "idle" rank still
contributes its ~68mW. Summing all ranks vs. the reported max-rank value, GCC:

| Technology | RANKS × CHANNELS | Reported `Power` (max rank) | True sum, all ranks (today's model) | Under-count factor |
|---|---|---|---|---|
| 1T1R SLC (full_dimm) | 8 × 1 = 8 | 0.0687 W | **0.5483 W** | **~8.0×** (= RANKS) |
| DDR5-4800 | 2 × 2 = 4 | 0.1362 W | **0.5447 W** | **~4.0×** (= RANKS×CHANNELS) |

Two things follow:

1. **The semantics are not equivalent across technologies** — the under-count factor tracks
   each technology's own rank/channel count, so DDR5 and ReRAM are not being compared on a
   like-for-like "total system power" basis today, even before touching the leakage-model bug.
2. **Striking, and worth sitting with**: under today's model, summed-across-all-ranks totals
   for 1T1R SLC (0.5483 W) and DDR5 (0.5447 W) are nearly *identical* — because both are
   dominated by a similarly-sized generic per-rank background term, not by real technology
   physics. This is independent corroboration of the Priority-1 finding, from a completely
   different angle (rank-summing instead of Eactstdby tracing).
3. **Connects to §3, policy (c)**: since reported `Power` only ever reflects the *loaded*
   rank, idle-rank power-gating would not move the reported number *at all* under the current
   extraction methodology — its benefit would only be visible if `extract_total_power()` is
   changed to sum ranks. If gating is the eventual policy, the extraction method needs to
   change in the same pass, or the fix's effect will be invisible in every downstream figure.

**Recommendation for this sub-question**: decide total-power semantics (sum-all-ranks vs.
max-loaded-rank) *together with* the leakage-model policy in §3 — they're coupled. I'm not
proposing which; flagging that the current choice quietly under-counts, differently per
technology, and that this predates and is independent of the `StandbyPower` bug.

---

## 5. Blast radius and cost

**Matrix scope**: 20 configs total (16 ReRAM arch variants: 4 technologies × 4 architectures,
+ DDR5-4800, PCM, 2D_DRAM_example, 3D_DRAM_example) × 6 benchmarks (gcc, lbm, alexnet
ifmap/ofmap, gpt2, stream) = 120 stats files today (confirmed: `processed_bar_chart_metrics.csv`
has exactly 120 rows). **Only the 16 ReRAM variants are affected by this fix** — DDR5/PCM/
2D_DRAM/3D_DRAM already derive background power from real `EIDD`/`current`-model formulas,
untouched by an `Eactstdby`/`Eprestdby` change. So the affected re-run is **16 configs × 6
benchmarks = 96 NVMain runs**, not the full 120.

**Re-run needed**: Stage 3 (`3_gen_nvmain_config.py`) regeneration is seconds — it just
rewrites config text. Stage 4 (`nvmain.fast`) is the cost driver; I don't have a clean
runtime number from this repo (no timing logs found), but the `lbm_spec2017.nvt` trace file
alone is 4.6 GB (vs. 202 MB for gcc, 30 MB for stream) — LBM runs are very likely the long
pole. Order-of-magnitude "hours" for the full 96-run set is a reasonable prior; **not
confirmed** — hence the pilot plan below.

**`sweep_rv112`/`rv140`/`rv168`**: NVSim-hardware-stage-only sweeps (each directory holds a
single `reram_22nm_1t1r_slc_results.txt`, no associated NVMain/system-level stats). This fix
lives entirely in stage 3 (Python config generation from already-existing
`hardware_metrics.json`), not in NVSim invocation — **these sweeps don't need to be re-run**
for this fix regardless of which policy is chosen.

**Downstream regeneration**, once a policy is picked and the 96 runs complete:
`process_metrics.py` → `processed_bar_chart_metrics.csv`, `processed_hero_metrics.csv`,
`processed_pareto_metrics.csv`, `processed_geometric_means.csv` → all three visualizers
(`visualize_results.py`, `visualize_pareto.py`, `visualize_hero_graphs.py`) → every PNG in
`results/final_graphs/`. This also invalidates the `Static_Power`/`Dynamic_Power`/
`Refresh_Power` columns and the six `Bar_Power_Breakdown_*.png` figures from the prior
session (§6 below) and the geometric-mean PDP/EDP rankings that drive the thesis's headline
efficiency claims.

**Pilot plan** (recommended before committing to the full 96-run matrix):
1. Apply the policy-(a) formula (§1) to **one config**: `reram_22nm_1t1r_slc_full_dimm`.
2. Run **one benchmark**: GCC (`stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out`).
3. Time it, to calibrate the full-matrix estimate.
4. Sanity checks before proceeding:
   - `rank_N.backgroundPower` ≈ 6.357 W (§1 predicted value) for every rank, not ~68mW.
   - `Config: Warning: Key Eactstdby is not set` warning **disappears** from the log (proves
     the value actually landed).
   - `fastExitActiveCycles`/`fastExitPrechargeCycles`/`slowExitCycles` still all 0 (confirms
     §2's dead-powerdown-path finding still holds, i.e. policy (a) was applied as intended,
     not accidentally triggering something else).
   - `totalPower` for the loaded rank ≈ 6.36 W + today's dynamic (~18mW) ≈ 6.38 W — an
     ~92× jump from today's 0.069W, matching §3's table. If it doesn't land near that, stop
     and re-check the formula before running the other 95 configs.

---

## 6. Cleanup items to fold into the same pass

- Retire the dead `StandbyPower {scaled_leakage_w}` write at `3_gen_nvmain_config.py:98`.
- Fix the misleading comment at `3_gen_nvmain_config.py:46-47` ("This ensures the correct
  total power is written to the config before NVMain reads it" — it doesn't; NVMain never
  reads this key).
- Revise `process_metrics.py`'s `extract_standby_power_mw()` (added in the prior session) to
  stop reading the dead `StandbyPower` echo and instead read real rank `backgroundPower`
  counters — directly, the same way the DDR5/PCM path already does. Once §1's fix lands,
  ReRAM's `backgroundPower` field becomes real and technology-differentiated, so the
  NonVolatile-specific branch in `decompose_power()` (config-constant + residual) can likely
  be retired entirely in favor of the current/energy-model path used for everything else —
  simplifying that function down to one code path instead of two.

---

## 7. Resending: Priority 3 and Priority 4 (unabridged)

### Priority 3 — FRFCFS queue depth

This NVMain fork has no parameter literally named `NumBuffers`; the equivalent is
`QueueSize` (plain `FRFCFS`) or `ReadQueueSize`/`WriteQueueSize` (`FRFCFS-WQF`).

| Config family | Controller | Value used | Source |
|---|---|---|---|
| ReRAM (1T1R/1S1R, SLC/MLC, all 4 architectures) | `FRFCFS` | **32** (code default) | Never set — `MemControl/FRFCFS/FRFCFS.cpp:57` `queueSize = 32`; `3_gen_nvmain_config.py` never writes `QueueSize`. |
| DDR5_4800, 2D_DRAM_example | `FRFCFS` | **32** (code default) | Configs *do* set `ReadQueueSize 32`/`WriteQueueSize 32`, but plain `FRFCFS.cpp` only reads `QueueSize` — those keys are dead for this controller. Coincidentally same value as the default. |
| pcm_microsoft_2009, 3D_DRAM_example | `FRFCFS-WQF` | `ReadQueueSize=32`, `WriteQueueSize=32` (explicit) | `Config/pcm_microsoft_2009.config:180-181`, `Config/3D_DRAM_example.config:200,202`; read by `MemControl/FRFCFS-WQF/FRFCFS-WQF.cpp:138-144`, overriding that controller's own coded defaults (32/**8**) — write queue explicitly widened from 8→32. |

Net: queue depth is uniformly **32** across all six technologies, but for three of them
(DDR5, 2D_DRAM, and every ReRAM variant) that's the compiled-in default, not anything our
configs actually control.

### Priority 4 — Trace provenance

**a) gem5 (602.gcc / 619.lbm)**: `4_execute_simulation.py` — the script that actually
produces every `results/system/*.out` file — never invokes gem5; it calls NVMain's
standalone trace replayer directly (`nvmain.fast <config> <trace.nvt> <cycles>`, line 120).
So `gcc_spec2017.nvt`/`lbm_spec2017.nvt` were generated **outside the reproducible
pipeline**. The only plausible generator in the repo, `run_gem5_trace.py` ("MBMM gem5 Trace
Generation"):
```python
system.cpu = TimingSimpleCPU()
system.cpu.icache_port = system.membus.cpu_side_ports
system.cpu.dcache_port = system.membus.cpu_side_ports
...
exit_event = m5.simulate(args.maxinsts)   # default 10,000,000
```
If this is indeed what produced the traces: **no L1/L2 caches exist in the model at all**
(CPU ports wire straight to the crossbar), and there is **no warmup, instruction-skip, or
SimPoint sampling** — `m5.simulate()` runs from process start to `maxinsts` (default 10M) or
natural exit. I could not find the actual invocation (no wrapper script, no log) tying the
two SPEC2017 `.nvt` files to a specific run of this script with specific arguments, so I
can't confirm the 10M default wasn't overridden. **This is a provenance gap**, not just "no
warmup" — the link between script and artifact isn't demonstrable from the repo as it stands.

**b) SCALE-Sim (AlexNet/GPT-2)**: The only preserved SCALE-Sim intermediate output is
`benchmarks/ml_trace_output/GoogleTPU_v1_os/` (layers 0-5), matching
`simulators/SCALE-Sim/configs/google.cfg`:
```
[architecture_presets]
ArrayHeight: 256
ArrayWidth:  256
IfmapSramSzkB: 6144
FilterSramSzkB: 6144
OfmapSramSzkB: 2048
Dataflow : os
```
256×256 systolic array, output-stationary, "Google TPU v1" preset — confirmed for **at
least** the AlexNet trace. No separate preserved SCALE-Sim output directory exists for
GPT-2, and no orchestration script in the repo invokes SCALE-Sim itself (only
`parse_trace.py`, which converts SCALE-Sim's *output* CSVs to NVMain's `.nvt` format,
downstream of SCALE-Sim). I checked whether `gpt2_ifmap.nvt`'s row count (6,554) matching
`layer1/OFMAP_DRAM_TRACE.csv`'s row count was a mislabeling clue — it isn't:
`gpt2_ifmap.nvt` is 100% read ops, and `parse_trace.py` only emits write ops when
`"OFMAP"` appears in the *input* filename, so it wasn't sourced from that file. I could not
identify what actually produced `gpt2_ifmap.nvt`. Reporting this as unverifiable rather than
guessing: config/array-dimension evidence exists for AlexNet (`google.cfg`, 256×256, OS
dataflow); no equivalent evidence exists for GPT-2.

---

**Nothing in `configs/`, `simulators/nvmain/Config/`, or `results/` was modified.** This
file is a new document; no existing file was touched.
