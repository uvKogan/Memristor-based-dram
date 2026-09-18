# MBMM Revision 2026-09 Implementation Plan

**Live tracker.** Tick a box only after the step's expected output was observed. Session log at the
bottom.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-run the MBMM ReRAM-vs-DDR5 evaluation on corrected traces, a corrected simulator pipeline and a literature-backed array organization, and rewrite the book, deck and one-pager from the results, within two weeks.

**Architecture:** Three layers change. (1) NVMain gains an end-to-end latency statistic, a per-location wear counter and a Start-Gap wear-leveling decoder, each a separate gated commit. (2) The Python pipeline (`3_gen_nvmain_config.py`, `mbmm_master.py`, `5_summary_report.py`, `process_metrics.py`, a new trace parser) is corrected and validated. (3) Traces are regenerated from gem5 and SCALE-Sim with a parser that keeps provenance. A pilot gate sits between the pipeline work and the full matrix; the book is rewritten only from gated results.

**Tech Stack:** Python 3 (pipeline, pytest for new tests), C++ (NVMain 2.0, SCons), NVSim (Makefile), gem5 25.1 `gem5.opt` (X86, SE mode), SCALE-Sim, Typst (book), HTML deck.

**Spec:** `documents/MBMM_Book_Typst/research_notes/revision_plan.md` (44 decisions), with evidence in `trace_timebase_investigation.md`, `leakage_47x_organization_artifact.md` §9-§14, `endurance_deep_dive.md`, `interface_clock_study.md`, `access_granularity_study.md`, and `Lead_Future_Work_Notes.md` §2b-2c.

**Tracker copy:** on approval, this plan is copied verbatim to `documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md` (decision: next to the trackers, checkboxes in the file). Every session starts by reading it and ends by ticking verified steps and appending a dated line to its "Session log" section. Commit messages reference task ids (`[T2.2]`).

## Global Constraints

- Git: the Lead Researcher runs every `git commit` and `git push`. The assistant stages and hands the exact command via `!`. No commit trailers. Never use the em-dash character anywhere.
- Gatekeeper: every Python change is verified through `mbmm_master.py` before it is called done.
- SPEC: only the scoped exception in `MBMM/CLAUDE.md` guardrail 3 (launch gem5 from a SPEC run directory on the binary and its reference input; no indexing, searching or reading otherwise). It ends when the regenerated traces are accepted.
- Time base: NVMain configs keep `CPUFreq 3000`; regenerated traces carry NVMain cycles on the 3 GHz basis; every trace has a sidecar recording its unit.
- Access granularity: 64 bytes for every technology; DDR5 modeled as two 32-bit subchannels at BL16.
- Organization: forced 2048x2048 subarrays, mux 64, for 1T1R and 1S1R (1024x1024 as sensitivity). NVSim output must print `2048 Rows x 2048 Columns`.
- Endurance: 10^6 cycles primary, 10^4 and 10^7 bounds; wear-leveling efficiency measured, not cited; write reduction stays a literature factor.
- Every NVMain patch: separate commit, `simulators/nvmain/CLAUDE.md` patch-log entry, regression run showing all pre-existing statistics bit-identical on the reference trace.
- Nothing is cut for time; a slip moves the date.

---

## File map

| Path | Responsibility | Status |
|---|---|---|
| `documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md` | This plan as the live tracker, with session log | create (T0.2) |
| `documents/MBMM_Book_Typst/research_notes/nvmain_patches/` | Copies of the prototype diffs from the session scratchpad, so they survive | create (T0.1) |
| `results/archive_2026-09_pre_revision/` | Frozen pre-revision results | create (T0.3) |
| `tools/nvmain_regress.sh` | Build NVMain, run the reference trace, diff pre-existing stats against a golden file | create (T1.1) |
| `tools/golden/` | Golden stats for the regression harness | create (T1.1) |
| `simulators/nvmain/include/NVMainRequest.h`, `src/MemoryController.{h,cpp}`, `traceSim/traceMain.cpp` | End-to-end latency statistic | modify (T1.2) |
| `simulators/nvmain/src/EnduranceModel.{h,cpp}`, `src/SubArray.{h,cpp}`, `Endurance/RowModel.h`, `Endurance/WordModel.h` | Wear counter and `NeedsOldData()` | modify (T1.3) |
| `simulators/nvmain/Decoders/StartGap/StartGap.{h,cpp}`, `Decoders/StartGap/SConscript`, `Decoders/DecoderFactory.cpp` | Start-Gap decoder | create/modify (T1.4) |
| `simulators/nvmain/CLAUDE.md`, `simulators/nvsim/CLAUDE.md` | Patch logs | modify (T1.5) |
| `tests/test_gen_nvmain_config.py`, `tests/test_parse_gem5_memctrl.py`, `tests/test_parse_scalesim.py`, `tests/conftest.py` | New pytest suite | create (T2.1, T3.1, T3.3) |
| `3_gen_nvmain_config.py` | Timing split, validation, capacity, channels, clock, endurance keys, dead keys removed | modify (T2.2) |
| `mbmm_master.py` | Window-based cycle budgets, channel and clock pass-through, DDR5 model names | modify (T2.3) |
| `configs/DDR5_4800_DRAM_subchannel.config`, `configs/DDR5_4800_DRAM_64B.config`, `tools/check_live_configs.py` | Honest DDR5, cross-check DDR5, divergence check; stale `configs/DDR5_4800_DRAM.config` deleted | create/delete (T2.4) |
| `5_summary_report.py`, `process_metrics.py` | Delivered bandwidth; new statistics into CSVs | modify (T2.5) |
| `configs/reram_22nm_*_slc.cfg` (+ `_1024` variants), `1_run_nvsim_hardware.py`, `2_extract_hardware_metrics.py` | Forced organization, organization assertion, subarray extraction | modify (T2.6) |
| `selector_layer.py` | Analytic 1S1R selector bounds (sneak leakage, read margin, tile validity) | create (T2.7) |
| `configs/silicon/reram_micron16gb_1t1r_*.config`, `configs/silicon/reram_sandisk32gb_1s1r_*.config` | Microsecond-silicon sensitivity configs | create (T2.8) |
| `parse_gem5_memctrl.py` | New gem5 MemCtrl parser with sidecar | create (T3.1) |
| `parse_trace.py` | SCALE-Sim parser fixed (all addresses, drop padding) | modify (T3.3) |
| `tools/validate_trace.py` | Trace validation (alignment, monotonic, region, counts) | create (T3.5) |
| `benchmarks/*.nvt` + `benchmarks/*.sidecar.json` | Regenerated traces | regenerate (T3.2-T3.4) |
| `endurance_sensitivity.py`, `tools/aggregate_wear.py` | Endurance table from run stats; DIMM-wide wear aggregation | create (T5.3) |
| `documents/MBMM_Book_Typst/Project_Book.typ` (+ new Appendix "What changed since the 3 September version") | Book revision | modify (T6.x) |
| `documents/MBMM_Book_Typst/presentation_deck.html`, `Shahar_Review_Evidence.typ` | Deck rebuild, one-pager rewrite | modify (T6.x) |

---

# Phase 0: Freeze and preserve (day 1)

### Task T0.1: Preserve the prototype patches and study addenda

**Files:**
- Create: `documents/MBMM_Book_Typst/research_notes/nvmain_patches/partA_e2e_latency.diff`, `partB_wear_map.diff`, `README.md`
- Modify: `documents/MBMM_Book_Typst/research_notes/access_granularity_study.md` (append addendum)

- [ ] **Step 1: Copy the two prototype diffs out of the session scratchpad** (they vanish with the session)

```bash
S=/tmp/claude-1000/-home-yuvalk-MBMM/a48717c5-f1ac-424d-b2fd-6e1c778b12f7/scratchpad
D=/home/yuvalk/MBMM/documents/MBMM_Book_Typst/research_notes/nvmain_patches
mkdir -p $D && cp $S/partA_e2e_latency.diff $S/partB_wear_map.diff $D/
cp $S/run/skew.nvt $S/run/sparse.nvt $D/   # the two synthetic verification traces
ls -la $D
```
Expected: two `.diff` files (about 116 and 199 lines) and two small `.nvt` files.

- [ ] **Step 2: Write `nvmain_patches/README.md`** stating: origin (2026-09-18 prototype, verified bit-identical pre-existing stats), the clock-domain conversion note (trace cycles are in the `CPUFreq` domain, `arrivalCycle` in the `CLK` domain), and the measured result (GPT-2 IFMAP: `averageTotalLatency` 364.1 vs `averageEndToEndLatency` 9709.7 memory cycles).

- [ ] **Step 3: Append the literature addendum to `access_granularity_study.md`** as "§8 Addendum (2026-09-18)": Qureshi ISCA 2009 uses 256 B lines and moves granularity down; Xu HPCA 2015 uses 64 B L2 blocks on gem5+NVMain; Udipi ISCA 2010, Yoon ISCA 2011, O'Connor MICRO 2017 all argue for finer DRAM access; x86-64 is 64 B, POWER 128 B sectored as 2x64 B, Apple M-series 128 B; write amplification WA = 2/(1+f) with measured f = 0.127 for GCC (0.57x lifetime at 128 B); required endurance for 10 years at 64 GB: 2.8e6 (64 B), 5.6e6 (128 B), 1.12e7 (256 B).

- [ ] **Step 4: Hand the commit to the Lead**

```bash
! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/research_notes && git commit -m "[T0.1] Preserve NVMain prototype patches and granularity addendum"
```

### Task T0.2: Create the live tracker

**Files:**
- Create: `documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md`

- [ ] **Step 1: Copy this plan file verbatim** to the tracker path, prepend a short header ("Live tracker. Tick a box only after the step's expected output was observed. Session log at the bottom."), and append a `## Session log` section with the first line: `2026-09-18: plan approved; Phase 0 started.`
- [ ] **Step 2: Add a "Pilot record" empty table** under Phase 4 with columns: criterion, expected, observed, pass/fail, evidence path.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md && git commit -m "[T0.2] Add revision workflow tracker"`

### Task T0.3: Freeze the pre-revision results

**Files:**
- Create: `results/archive_2026-09_pre_revision/` (git-ignored: `results/` is in `.gitignore`, so this is a local freeze plus a tag)
- Modify: `documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md` (record which figures came from which dataset)

- [ ] **Step 1: Snapshot the live results and hardware metrics**

```bash
cd /home/yuvalk/MBMM && mkdir -p results/archive_2026-09_pre_revision && cp -r results/system results/system_v6 results/system_v6_input results/hardware results/final_graphs results/slide_graphs results/hardware_metrics.json results/processed_*.csv results/archive_2026-09_pre_revision/ && du -sh results/archive_2026-09_pre_revision && sha256sum results/archive_2026-09_pre_revision/hardware_metrics.json
```
Expected: directory populated; note the checksum in the tracker.

- [ ] **Step 2: Record provenance in the tracker**: "Book figures 1-17, 25, 27 and Tables 2-7 of the 3 September version came from `results/system` (post idle-gating, 2026-09-05); §3.2 chip-count trajectories from `results/system_v6`; frozen at `results/archive_2026-09_pre_revision/`, tag `pre-revision-2026-09`."
- [ ] **Step 3: Hand the tag to the Lead**: `! cd /home/yuvalk/MBMM && git tag -a pre-revision-2026-09 -m "State of the pipeline and book before the 2026-09 revision" && git push origin pre-revision-2026-09`

---

# Phase 1: NVMain changes (days 1-5)

### Task T1.1: Regression harness

**Files:**
- Create: `tools/nvmain_regress.sh`, `tools/golden/README.md`, `tools/golden/*.golden`

**Interfaces:**
- Produces: `tools/nvmain_regress.sh [--record]` exits 0 when every pre-existing statistic line in the reference runs matches the golden file; `--record` writes the golden files.

- [ ] **Step 1: Write the harness**

```bash
#!/usr/bin/env bash
# tools/nvmain_regress.sh: build nvmain.fast and compare pre-existing stats to golden files.
# Usage: tools/nvmain_regress.sh [--record]
set -euo pipefail
ROOT=/home/yuvalk/MBMM
NV=$ROOT/simulators/nvmain
GOLD=$ROOT/tools/golden
TRACE=$ROOT/benchmarks/gpt2_ifmap.nvt        # small, deterministic, 6553 reads
CYCLES=20000
CONFIGS=("reram_22nm_1t1r_slc_full_dimm" "DDR5_4800_DRAM" "pcm_microsoft_2009")
mkdir -p "$GOLD"
( cd "$NV" && scons -j8 >/dev/null )
rc=0
for c in "${CONFIGS[@]}"; do
  out=$(mktemp)
  "$NV/nvmain.fast" "$NV/Config/$c.config" "$TRACE" "$CYCLES" > "$out" 2>&1 || true
  # keep only statistic lines (i0. prefix), drop the new stats we are adding so old ones are compared alone
  grep -E '^i0\.' "$out" | grep -vE 'EndToEnd|unstampedRequests|wear[A-Z]' | sort > "$out.stats"
  if [[ "${1:-}" == "--record" ]]; then
    cp "$out.stats" "$GOLD/$c.golden"; echo "recorded $c ($(wc -l < "$GOLD/$c.golden") lines)"
  else
    if diff -q "$GOLD/$c.golden" "$out.stats" >/dev/null; then echo "PASS $c"; else echo "FAIL $c"; diff "$GOLD/$c.golden" "$out.stats" | head -20; rc=1; fi
  fi
  rm -f "$out" "$out.stats"
done
exit $rc
```

- [ ] **Step 2: Record the golden files from the unpatched tree**

Run: `cd /home/yuvalk/MBMM && chmod +x tools/nvmain_regress.sh && tools/nvmain_regress.sh --record`
Expected: three `recorded ...` lines; `tools/golden/*.golden` non-empty.

- [ ] **Step 3: Verify the harness passes on itself**

Run: `tools/nvmain_regress.sh`
Expected: `PASS` for all three configs, exit 0.

- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add tools/nvmain_regress.sh tools/golden && git commit -m "[T1.1] NVMain regression harness with golden stats"`

### Task T1.2: End-to-end latency statistic (patch A)

**Files:**
- Modify: `simulators/nvmain/include/NVMainRequest.h:128,161,205`, `simulators/nvmain/src/MemoryController.h:134`, `simulators/nvmain/src/MemoryController.cpp:66,306-325,559-562`, `simulators/nvmain/traceSim/traceMain.cpp:231`

**Interfaces:**
- Produces: statistics `averageEndToEndLatency` (memory cycles, same unit as `averageTotalLatency`), `measuredEndToEndLatencies`, `unstampedRequests` on every `MemoryController` (`i0.defaultMemory.channelN.<CTL>.averageEndToEndLatency`). `process_metrics.py` (T2.5) reads them.

- [x] **Step 1: Apply the preserved diff**

Run: `cd /home/yuvalk/MBMM/simulators/nvmain && git apply --check ../../documents/MBMM_Book_Typst/research_notes/nvmain_patches/partA_e2e_latency.diff && git apply ../../documents/MBMM_Book_Typst/research_notes/nvmain_patches/partA_e2e_latency.diff`
Expected: no output from `--check`; files modified. If `--check` fails (line drift), apply by hand using the content below.

The substance of the patch (repeat here so it survives without the diff):

```cpp
// include/NVMainRequest.h: in the constructor init list area (line 128)
traceCycle = 0;
// member declaration (line 161)
ncycle_t traceCycle;      // trace record timestamp, CPUFreq domain, 0 = unstamped
// operator= (line 205)
traceCycle = m.traceCycle;

// traceSim/traceMain.cpp, right after request->threadId = tl->GetThreadId( ); (line 231)
request->traceCycle = tl->GetCycle( );

// src/MemoryController.h (protected, line 134)
double averageEndToEndLatency;
ncounter_t measuredEndToEndLatencies;
ncounter_t unstampedRequests;

// src/MemoryController.cpp constructor (line 66)
averageEndToEndLatency = 0.0; measuredEndToEndLatencies = 0; unstampedRequests = 0;

// src/MemoryController.cpp RegisterStats (line 561)
AddStat(averageEndToEndLatency); AddStat(measuredEndToEndLatencies); AddStat(unstampedRequests);

// src/MemoryController.cpp RequestComplete, in the else branch (owner != this), before returning to the parent
if( request->type == READ || request->type == READ_PRECHARGE
 || request->type == WRITE || request->type == WRITE_PRECHARGE )
{
    if( request->traceCycle == 0 && request->arrivalCycle != 0 ) unstampedRequests++;
    else
    {
        // convert the CPUFreq-domain trace cycle into memory (CLK) cycles
        double ratio = static_cast<double>( GetEventQueue()->GetFrequency() )
                     / static_cast<double>( GetGlobalEventQueue()->GetFrequency() );
        double start = static_cast<double>( request->traceCycle ) * ratio;
        double e2e = static_cast<double>( request->completionCycle ) - start;
        averageEndToEndLatency = ( averageEndToEndLatency * static_cast<double>( measuredEndToEndLatencies ) + e2e )
                               / static_cast<double>( measuredEndToEndLatencies + 1 );
        measuredEndToEndLatencies++;
    }
}
```

- [x] **Step 2: Build and run the regression**

Run: `cd /home/yuvalk/MBMM && tools/nvmain_regress.sh`
Expected: `PASS` x3 (the harness filters the new stats out of the comparison).

- [x] **Step 3: Verify the new statistic on the reference and on the sparse trace**

Run: `cd /home/yuvalk/MBMM/simulators/nvmain && ./nvmain.fast Config/reram_22nm_1t1r_slc_full_dimm.config ../../benchmarks/gpt2_ifmap.nvt 20000 | grep -E 'averageTotalLatency|averageEndToEndLatency|unstampedRequests'`
Expected: `averageTotalLatency 364.146`, `averageEndToEndLatency` about `9709.69`, `unstampedRequests 0`.
Run the same with `../../documents/MBMM_Book_Typst/research_notes/nvmain_patches/sparse.nvt`: the two averages differ by under 0.5 cycles.

- [x] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add simulators/nvmain/include/NVMainRequest.h simulators/nvmain/src/MemoryController.h simulators/nvmain/src/MemoryController.cpp simulators/nvmain/traceSim/traceMain.cpp && git commit -m "[T1.2] NVMain: end-to-end latency statistic from trace timestamp to completion"`

### Task T1.3: Per-location wear counter (patch B)

**Files:**
- Modify: `simulators/nvmain/src/EnduranceModel.h` (+`writeCounts`, `GetWriteCounts()`, `virtual bool NeedsOldData()`), `src/EnduranceModel.cpp:96` (one line), `Endurance/RowModel.h`, `Endurance/WordModel.h` (override `NeedsOldData()` to false), `src/SubArray.h:185`, `src/SubArray.cpp:250,1389,1478`

**Interfaces:**
- Produces per subarray: `wearLocations`, `wearTotalWrites`, `wearMaxWrites`, `wearMeanWrites`, `wearHotSpotFactor`, `wearHisto` (log2 buckets, PyDict format), `wearTopLocations` (top 16). Consumed by `tools/aggregate_wear.py` (T5.3).
- Config keys used: `EnduranceModel RowModel` (default for the re-run), `EnduranceDist Uniform`, `EnduranceDistMean 1000000` (T2.2 writes them; the Uniform value is irrelevant to the counter).

- [x] **Step 1: Apply the preserved diff** (`git apply --check` first, as in T1.2). Substance:

```cpp
// src/EnduranceModel.h
std::map<uint64_t, uint64_t> writeCounts;
const std::map<uint64_t, uint64_t>& GetWriteCounts( ) const { return writeCounts; }
virtual bool NeedsOldData( ) { return true; }
// src/EnduranceModel.cpp, first line of DecrementLife( uint64_t addr )
writeCounts[addr]++;
// Endurance/RowModel.h and Endurance/WordModel.h
bool NeedsOldData( ) { return false; }
// src/SubArray.cpp UpdateEndurance: after the NullModel early return, before NVMDataBlock oldData
if( !endrModel->NeedsOldData( ) )
{
    uint64_t row, col, bank, rank, channel, subarray;
    GetParent()->GetTrampoline()->GetDecoder()->Translate( request->address.GetPhysicalAddress(), &row, &col, &bank, &rank, &channel, &subarray );
    endrModel->Write( request->address, request->oldData, request->data );   // models ignore data
    return 0;
}
// src/SubArray.cpp CalculateStats: compute the six stats from endrModel->GetWriteCounts()
```
(If the exact `Write` call signature in this tree differs, use the one `UpdateEndurance` already calls a few lines below; the point is to skip `SimInterface::SetDataAtAddress` for models that never read old data.)

- [x] **Step 2: Regression**: `tools/nvmain_regress.sh` expected `PASS` x3.
- [x] **Step 3: Verify on the skew trace** with a scratch copy of the 1T1R full-DIMM config plus `EnduranceModel WordModel` / `EnduranceDist Uniform` / `EnduranceDistMean 1000000` appended:

Run: `grep -E 'wearMaxWrites|wearHotSpotFactor|wearTotalWrites' <out> | sort -t' ' -k2 -n | tail -3`
Expected: one subarray with `wearMaxWrites 16014`, `wearHotSpotFactor` about `220`; sum of `wearTotalWrites` equals 19,999.
Also run with `RowModel` and confirm `wearTotalWrites` sums equal the trace's write count, and RSS (`/usr/bin/time -v`) within 1 MB of the NullModel run.

- [x] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add simulators/nvmain/src/EnduranceModel.h simulators/nvmain/src/EnduranceModel.cpp simulators/nvmain/src/SubArray.h simulators/nvmain/src/SubArray.cpp simulators/nvmain/Endurance/RowModel.h simulators/nvmain/Endurance/WordModel.h && git commit -m "[T1.3] NVMain: per-location wear counter and hot-spot statistics"`

### Task T1.4: Start-Gap wear-leveling decoder

**Files:**
- Create: `simulators/nvmain/Decoders/StartGap/StartGap.h`, `StartGap.cpp`, `SConscript` (copy `Decoders/Migrator/SConscript`, rename)
- Modify: `simulators/nvmain/Decoders/DecoderFactory.cpp:47-49` (add `"StartGap"`), `Decoders/SConscript` if it lists subdirectories

**Interfaces:**
- Config: `Decoder StartGap`, `StartGapInterval 100` (writes per gap move; Qureshi 2009 uses 100), `StartGapRegionBytes` (default: the channel capacity). Stats: `startGapMoves`, `startGapWrites`.
- Property: `Translate` applies `PA' = (PA + gap*64) mod (N+1)*64` on 64-byte units before the base translation; `ReverseTranslate` applies the exact inverse. All decoder instances share one static gap state (the factory creates a decoder at six hierarchy levels).

- [x] **Step 1: Write the header**

```cpp
// Decoders/StartGap/StartGap.h
#ifndef __DECODERS_STARTGAP_H__
#define __DECODERS_STARTGAP_H__
#include "src/AddressTranslator.h"
#include "src/Config.h"
namespace NVM {
class StartGap : public AddressTranslator
{
  public:
    StartGap( );
    ~StartGap( );
    void SetConfig( Config *config, bool createChildren = true );
    using AddressTranslator::Translate;
    virtual void Translate( uint64_t address, uint64_t *row, uint64_t *col, uint64_t *bank,
                            uint64_t *rank, uint64_t *channel, uint64_t *subarray );
    virtual uint64_t ReverseTranslate( const uint64_t& row, const uint64_t& col, const uint64_t& bank,
                                       const uint64_t& rank, const uint64_t& channel, const uint64_t& subarray );
    void RegisterStats( );
    static void NoteWrite( );            // called once per WRITE request that enters the channel
  private:
    static uint64_t gap;                 // shared across all instances
    static uint64_t writesSinceMove;
    static uint64_t lines;               // N: number of 64-byte lines in the region
    static uint64_t interval;
    static ncounter_t moves;
    static ncounter_t writes;
    uint64_t Remap( uint64_t address );
    uint64_t Unmap( uint64_t address );
};
};
#endif
```

- [x] **Step 2: Write the implementation**

```cpp
// Decoders/StartGap/StartGap.cpp
#include "Decoders/StartGap/StartGap.h"
#include <iostream>
using namespace NVM;
uint64_t StartGap::gap = 0; uint64_t StartGap::writesSinceMove = 0; uint64_t StartGap::lines = 0;
uint64_t StartGap::interval = 100; ncounter_t StartGap::moves = 0; ncounter_t StartGap::writes = 0;
StartGap::StartGap( ) { }
StartGap::~StartGap( ) { }
void StartGap::SetConfig( Config *config, bool createChildren )
{
    AddressTranslator::SetConfig( config, createChildren );
    if( config->KeyExists( "StartGapInterval" ) ) interval = static_cast<uint64_t>( config->GetValue( "StartGapInterval" ) );
    if( lines == 0 )
    {
        uint64_t bytes;
        if( config->KeyExists( "StartGapRegionBytes" ) ) bytes = static_cast<uint64_t>( config->GetValue( "StartGapRegionBytes" ) );
        else bytes = static_cast<uint64_t>( config->GetValue( "ROWS" ) ) * config->GetValue( "COLS" ) * 64
                   * config->GetValue( "BANKS" ) * config->GetValue( "RANKS" );
        lines = bytes / 64;
    }
}
uint64_t StartGap::Remap( uint64_t address )      // Qureshi et al., MICRO 2009, Fig. 4: one gap line, lines rotate by one every interval writes
{
    uint64_t line = address / 64, off = address % 64;
    uint64_t mapped = ( line + gap ) % ( lines + 1 );
    if( mapped == lines ) mapped = 0;                // the gap slot is never used by data
    return mapped * 64 + off;
}
uint64_t StartGap::Unmap( uint64_t address )
{
    uint64_t line = address / 64, off = address % 64;
    uint64_t orig = ( line + lines + 1 - ( gap % ( lines + 1 ) ) ) % ( lines + 1 );
    return orig * 64 + off;
}
void StartGap::Translate( uint64_t address, uint64_t *row, uint64_t *col, uint64_t *bank, uint64_t *rank, uint64_t *channel, uint64_t *subarray )
{
    AddressTranslator::Translate( Remap( address ), row, col, bank, rank, channel, subarray );
}
uint64_t StartGap::ReverseTranslate( const uint64_t& row, const uint64_t& col, const uint64_t& bank, const uint64_t& rank, const uint64_t& channel, const uint64_t& subarray )
{
    return Unmap( AddressTranslator::ReverseTranslate( row, col, bank, rank, channel, subarray ) );
}
void StartGap::NoteWrite( )
{
    writes++; writesSinceMove++;
    if( writesSinceMove >= interval ) { gap = ( gap + 1 ) % ( lines + 1 ); writesSinceMove = 0; moves++; }
}
void StartGap::RegisterStats( ) { AddStat(moves); AddStat(writes); }
```
Note: the real Start-Gap moves one line per gap move (a read plus a write of one line). Model that data movement as one extra WRITE request injected by the controller only if time allows (T5.2 sensitivity); the first version counts moves and applies the remap, and the book states the omission.

- [x] **Step 3: Wire the write hook and the factory.** In `src/MemoryController.cpp` `IssueCommand` path where a WRITE request is accepted (the FRFCFS `IssueCommand` at `MemControl/FRFCFS/FRFCFS.cpp:145-163` is the simplest single site): add `if( req->type == WRITE || req->type == WRITE_PRECHARGE ) StartGap::NoteWrite( );` guarded by an `#include` and a config check `p->KeyExists("Decoder") && value == "StartGap"` cached in a bool at `SetConfig`. In `Decoders/DecoderFactory.cpp:49` add `else if( decoder == "StartGap" ) at = new StartGap( );` with the include. Add the SConscript so the new directory builds.

- [x] **Step 4: Build; regression** (`tools/nvmain_regress.sh`: PASS x3, since no config uses the decoder yet).

- [x] **Step 5: Verify the remap is a bijection and lowers hot-spot factor.** Run the skew trace (T1.3 config plus `Decoder StartGap`, `StartGapInterval 100`) and compare `wearHotSpotFactor`:
Expected: DIMM-wide max writes to one location falls from 16,014 toward about `16014 * 100 / lines`-scale values (the exact number depends on region size; it must fall by more than 10x), `wearTotalWrites` sum unchanged at 19,999, `startGapMoves` = 19,999 / 100. Also run gpt2 with and without the decoder: `mem_reads`, `mem_writes` and `totalReadRequests` identical (the remap must not lose requests).

- [ ] **Step 6: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add simulators/nvmain/Decoders simulators/nvmain/MemControl/FRFCFS/FRFCFS.cpp simulators/nvmain/src && git commit -m "[T1.4] NVMain: Start-Gap wear-leveling decoder with shared gap state"`

### Task T1.5: Patch logs

**Files:**
- Modify: `simulators/nvmain/CLAUDE.md` (append items 4-6 under APPLIED REPAIRS: end-to-end stat, wear counter, StartGap; each with files, config keys, and the regression command), `simulators/nvsim/CLAUDE.md` (item 2: remove the claim that `InputParameter.cpp` was patched; it was not, per the 2026-09-15 calibration; note the `Mat.cpp` debug prints and that the "128x128 Mats" skeleton keys are unparsed)

- [x] **Step 1: Edit both files** in the existing numbered-list style.
- [ ] **Step 2: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add simulators/nvmain/CLAUDE.md simulators/nvsim/CLAUDE.md && git commit -m "[T1.5] Patch logs: NVMain revision patches; correct NVSim patch history"`

---

# Phase 2: Pipeline corrections (days 2-5, parallel with Phase 3)

### Task T2.1: Test scaffolding and the timing-split test

**Files:**
- Create: `tests/conftest.py`, `tests/test_gen_nvmain_config.py`

**Interfaces:**
- Consumes (T2.2 produces): `compute_timings(read_ns, write_ns, freq_mhz) -> dict` with keys `tCAS, tRCD, tRP, tRAS, tWR, tBURST, tCCD, tCMD` (ints, cycles), and `validate_config(cfg: dict) -> list[str]` returning violations.

- [ ] **Step 1: Write the failing tests**

```python
# tests/conftest.py
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

# tests/test_gen_nvmain_config.py
import importlib, math
gen = importlib.import_module("3_gen_nvmain_config") if False else None  # module name starts with a digit
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("gen", pathlib.Path(__file__).resolve().parents[1] / "3_gen_nvmain_config.py")
gen = importlib.util.module_from_spec(spec); spec.loader.exec_module(gen)

def test_read_latency_is_charged_once():
    t = gen.compute_timings(read_ns=32.134, write_ns=32.3, freq_mhz=800)
    assert t["tRCD"] + t["tCAS"] == math.ceil(32.134 / 1.25)      # 26 cycles total, not 52
    assert t["tRCD"] >= 1 and t["tCAS"] >= 1

def test_tras_covers_activate_plus_burst():
    t = gen.compute_timings(read_ns=32.134, write_ns=32.3, freq_mhz=800)
    assert t["tRAS"] >= t["tRCD"] + t["tBURST"]

def test_tccd_not_below_tburst():
    t = gen.compute_timings(read_ns=10.12, write_ns=15.26, freq_mhz=2400)
    assert t["tCCD"] >= t["tBURST"]

def test_validate_rejects_clk_above_cpufreq():
    v = gen.validate_config({"CLK": 4000, "CPUFreq": 3000, "tBURST": 4, "tCCD": 4, "tRAS": 30, "tRCD": 13})
    assert any("CLK" in s for s in v)

def test_capacity_matches_physical_module():
    hw = {"capacity_gb": 0.125, "read_latency_ns": 10.12, "write_latency_ns": 15.26,
          "read_energy_nj": 0.3755, "write_energy_nj": 0.9113, "leakage_mw": 108.384}
    g = gen.geometry(hw, arch_type="full_dimm")
    assert g["ROWS"] * g["COLS"] * 64 * g["BANKS"] * g["RANKS"] * g["CHANNELS"] == 8 * 2**30
```

- [ ] **Step 2: Run to verify they fail**: `cd /home/yuvalk/MBMM && python3 -m pytest tests/test_gen_nvmain_config.py -v`
Expected: 5 failures with `AttributeError: module 'gen' has no attribute 'compute_timings'` (or similar).

### Task T2.2: Generator corrections

**Files:**
- Modify: `3_gen_nvmain_config.py` (lines 10-23 flags; 25-53 body; 90-182 template)

**Interfaces:**
- Produces: `compute_timings`, `validate_config`, `geometry` (tested in T2.1); new flags `--channels {1,2}` (default 1), `--decoder {Default,StartGap}` (default Default), `--endurance-model {RowModel,WordModel,NullModel}` (default RowModel), `--window-ns` (default 250000000: the matched window in nanoseconds, written as a comment so T2.3 can read it back).
- Template changes: `tRCD {tRCD}` and `tCAS {tCAS}` from the split; `tRAS`, `tBURST 4`, `tCCD 4` explicit; delete `tRTW`, `tBus`, `STATS_OUT`, `DECODER MigratingDecoder`; add `Decoder {decoder}`, `EnduranceModel {model}`, `EnduranceDist Uniform`, `EnduranceDistMean 1000000`, `CHANNELS {channels}`, `StartGapInterval 100` when decoder is StartGap; ROWS from `geometry()` so capacity equals the physical module (8 GiB SLC full DIMM: with COLS 1024, BANKS 8, RANKS 8, DeviceWidth 8 the per-rank row count is `2**30*8 / (1024*8*8*8)`; keep the `max(..., 65536)` floor only for `single`).

- [ ] **Step 1: Implement `compute_timings`**

```python
def compute_timings(read_ns, write_ns, freq_mhz, burst=4):
    """Cycle counts for NVMain. The device read latency is charged once: tRCD (activate) plus
    tCAS (column access) sum to the NVSim read latency (Section 3.1.6 correction, 2026-09)."""
    cyc = 1000.0 / freq_mhz
    t_read = max(2, math.ceil(read_ns / cyc))
    t_write = max(1, math.ceil(write_ns / cyc))
    t_rcd = max(1, t_read // 2)
    t_cas = max(1, t_read - t_rcd)
    t_burst = burst
    t_ccd = max(4, t_burst)                       # NVMain requires tCCD >= tBURST (segfault otherwise)
    t_ras = max(t_read, t_rcd + t_burst)          # activate must outlast tRCD + burst
    return {"tCAS": t_cas, "tRCD": t_rcd, "tRP": 1, "tRAS": t_ras, "tWR": t_write,
            "tBURST": t_burst, "tCCD": t_ccd, "tCMD": 1}
```

- [ ] **Step 2: Implement `validate_config` and `geometry`**

```python
def validate_config(cfg):
    v = []
    if cfg["CLK"] > cfg["CPUFreq"]: v.append(f"CLK {cfg['CLK']} exceeds CPUFreq {cfg['CPUFreq']}: NVMain corrupts admission silently")
    if cfg["tCCD"] < cfg["tBURST"]: v.append("tCCD below tBURST: NVMain can segfault")
    if cfg["tRAS"] < cfg["tRCD"] + cfg["tBURST"]: v.append("tRAS below tRCD + tBURST")
    return v

def geometry(hw, arch_type, channels=1):
    cols, banks = 1024, 8
    ranks, dev, width = {"single": (1, 1, 64), "8chip": (1, 8, 8), "16chip": (2, 8, 8), "full_dimm": (8, 8, 8)}.get(arch_type, (1, 1, 8))
    bits_per_chip = hw["capacity_gb"] * 8 * 1024**3
    rows_per_chip = int(bits_per_chip / (cols * width * banks))
    rows = rows_per_chip * ranks if arch_type != "single" else max(rows_per_chip, 65536)
    return {"ROWS": rows // channels if channels > 1 else rows, "COLS": cols, "BANKS": banks,
            "RANKS": ranks, "CHANNELS": channels, "DEVICES_PER_RANK": dev, "DeviceWidth": width}
```
Check the arithmetic against NVMain's capacity print (`capacity is ... MB`) in Step 5; adjust the `rows` formula until the printed capacity equals 8192 MB for SLC full DIMM and 16384 MB for MLC.

- [ ] **Step 3: Rewrite the template** using the dicts; delete the dead keys; add the endurance and decoder keys. Keep the explanatory comment blocks (lines 55-80, 144-160) and add one for the split: "tRCD + tCAS = NVSim read latency; earlier versions set both to the full latency and charged reads twice."

- [ ] **Step 4: Run the tests**: `python3 -m pytest tests/test_gen_nvmain_config.py -v` expected 5 passed.

- [ ] **Step 5: Gatekeeper run.** `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gcc_spec2017.nvt --cycles 66666667 --queue-size 32` (this still uses the old trace; the point is the pipeline runs end to end). Expected: exit 0; `results/system/stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out` contains `capacity is 8192 MB`, no `Could not find Decoder` warning, no `EnduranceDist is not set`, and `wearTotalWrites` lines present. Then restore the frozen results: `cp -r results/archive_2026-09_pre_revision/system/. results/system/ && cp results/archive_2026-09_pre_revision/hardware_metrics.json results/` (the pre-revision live tree must not be overwritten before Phase 4).

- [ ] **Step 6: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add 3_gen_nvmain_config.py tests && git commit -m "[T2.2] Generator: charge read latency once, validate timings, match capacity to the module, endurance and decoder keys, drop dead keys"`

### Task T2.3: Master script: window-based budgets and pass-through

**Files:**
- Modify: `mbmm_master.py:195-211` (flags), `:334-335` (model lists), `:355` (generator call), `:358-400` (per-trace loop), `:395-400` (DRAM loop)

**Interfaces:**
- New flags: `--window-ns` (default 250000000), `--channels`, `--decoder`, `--endurance-model`, `--ddr5-model {DDR5_4800_DRAM_subchannel,DDR5_4800_DRAM_64B}` (default subchannel), `--silicon` (also run the T2.8 configs).
- Behavior: `cycles_for(model) = ceil(window_ns * CLK_MHz / 1000)` where CLK is read from the model's config (`CLK` line), replacing the single `--cycles` (kept as an override with a warning). Every model then admits the identical trace window.
- `dram_models` becomes `[args.ddr5_model]` plus PCM; the 2D/3D DRAM examples are dropped from the default run (they are excluded from every figure already).

- [ ] **Step 1: Write the failing test** in `tests/test_mbmm_master.py`: `cycles_for("reram_22nm_1t1r_slc_full_dimm", window_ns=250e6)` returns 200,000,000 when the config says CLK 800; for CLK 2400 returns 600,000,000; for CLK 400 returns 100,000,000. Run, expect failure.
- [ ] **Step 2: Implement** `cycles_for(model_name, window_ns)` reading `simulators/nvmain/Config/{model}.config`, and replace the `--cycles` uses at the `4_execute_simulation.py` calls (lines 383-386 and 395-400). Pass `--channels/--decoder/--endurance-model` to the generator call at line 355.
- [ ] **Step 3: Tests pass**; then gatekeeper: `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gpt2_ifmap.nvt --window-ns 250000000`. Expected: log shows `cycles=200000000` for ReRAM, `600000000` for DDR5, `100000000` for PCM; exit 0. Restore frozen results afterwards as in T2.2 step 5.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add mbmm_master.py tests/test_mbmm_master.py && git commit -m "[T2.3] Master: matched trace window in ns, per-CLK cycle budgets, config pass-through"`

### Task T2.4: DDR5 baseline: honest subchannel config, cross-check config, divergence check

**Files:**
- Create: `configs/DDR5_4800_DRAM_subchannel.config`, `configs/DDR5_4800_DRAM_64B.config`, `tools/check_live_configs.py`
- Delete: `configs/DDR5_4800_DRAM.config` (stale; record in `Review_Fixes_Tracker.md`)
- Modify: `simulators/nvmain/Config/` gets copies of the two new files (the pipeline reads from there, `4_execute_simulation.py:108`); `process_metrics.py:53-63,74-84` and `visualize_*.py` label tables gain the two names (map both to technology `DDR5_4800`, with `Architecture` = `subchannel` / `64B`).

- [ ] **Step 1: Write the subchannel config** from the live `simulators/nvmain/Config/DDR5_4800_DRAM.config` with these keys changed: `BusWidth 32`, `DeviceWidth 8`, `tBURST 8`, `tCCD 8`, `CHANNELS 2`, `RANKS 1`, `BANKS 32`, `ROWS 65536`, `COLS 64`, keep `CLK 2400`, `CPUFreq 3000`, `tCAS 40`, `tRCD 39`, `tRP 39`, `tRFC 708`, `tREFI 9375`, `EnergyModel current`, and remove `BurstLength` (dead key). Header comment: "Two independent 32-bit subchannels at BL16 = 64 B per access (JESD79-5); capacity 65536 x 64 x 64 B x 32 x 1 x 2 = 16 GiB."
- [ ] **Step 2: Write the 64B cross-check config**: the live file unchanged except `tBURST 4`, `tCCD 4`, and `BurstLength` removed. Header: "Minimal correction only: same channel shape as the 3 September baseline, 64-byte access."
- [ ] **Step 3: Write `tools/check_live_configs.py`**: for every `configs/*.config` there must be a byte-identical `simulators/nvmain/Config/<name>.config`; print differences and exit 1 otherwise. Add its invocation at the start of `mbmm_master.py` stage 4 (fail fast).
- [ ] **Step 4: Verify capacity and timing**: run each new config on gpt2 for 20000 cycles; expected `capacity is 16384 MB` for the subchannel config, no segfault (exit 0) for both, and for the 64B config `bank0.bandwidth` about half of the old value on identical traffic.
- [ ] **Step 5: Delete the stale file, record it**: append to `Review_Fixes_Tracker.md` change log: "2026-09: deleted `configs/DDR5_4800_DRAM.config` (34-34-34, tRFC 840, never read by the pipeline; the live file is `simulators/nvmain/Config/DDR5_4800_DRAM.config`); replaced by `DDR5_4800_DRAM_subchannel.config` (primary) and `DDR5_4800_DRAM_64B.config` (cross-check), both tracked and checked by `tools/check_live_configs.py`."
- [ ] **Step 6: Gatekeeper**: `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gpt2_ifmap.nvt --ddr5-model DDR5_4800_DRAM_subchannel` exit 0 and both DDR5 stats files produced. Restore frozen results.
- [ ] **Step 7: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add configs tools/check_live_configs.py simulators/nvmain/Config/DDR5_4800_DRAM_subchannel.config simulators/nvmain/Config/DDR5_4800_DRAM_64B.config process_metrics.py visualize_results.py visualize_hero_graphs.py visualize_pareto.py visualize_slides.py documents/MBMM_Book_Typst/Review_Fixes_Tracker.md && git rm configs/DDR5_4800_DRAM.config && git commit -m "[T2.4] DDR5 baseline: subchannel config (64 B per access), 64B cross-check, live-config divergence check; drop stale config"`

### Task T2.5: Delivered bandwidth and new statistics in the CSVs

**Files:**
- Modify: `5_summary_report.py:35-40,79-96`, `process_metrics.py` (`parse_raw_stats` 500+, `save_bar_chart_metrics` 697-715, `save_hero_metrics` 737-754)

**Interfaces:**
- `5_summary_report.py`: column `Delivered BW (MB/s)` = `(mem_reads + mem_writes) * 64 / (simulation_cycles * 1000/CLK ns)`, summed over channels; NVMain's `bank0.bandwidth` printed as `NVMain BW (x-check)`.
- `process_metrics.py`: new CSV columns `E2E_Latency_ns` (from `averageEndToEndLatency` x cycle time), `Delivered_BW_MBps`, `Wear_Max_Writes`, `Wear_HotSpot_Factor` (DIMM-wide: max of `wearMaxWrites` over `sum(wearTotalWrites)/touched locations`), `Completed_Requests`.

- [ ] **Step 1: Failing test** `tests/test_process_metrics.py`: feed a 30-line synthetic stats text with two channels, known `mem_reads`, `CLK 800`, `simulation_cycles`, `averageEndToEndLatency`, and two subarrays with `wearMaxWrites`/`wearTotalWrites`/`wearLocations`; assert the four derived values.
- [ ] **Step 2: Implement** the extractors next to `extract_queue_latency` (line 186) following its regex style; add columns to the two writers; extend `5_summary_report.py` patterns and the printed table.
- [ ] **Step 3: Tests pass; gatekeeper** (`--models reram_22nm_1t1r_slc --trace gpt2_ifmap.nvt`): `results/processed_bar_chart_metrics.csv` has the new columns populated for the ReRAM rows. Restore frozen results.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add 5_summary_report.py process_metrics.py tests/test_process_metrics.py && git commit -m "[T2.5] Delivered bandwidth, end-to-end latency and wear statistics in reports and CSVs"`

### Task T2.6: NVSim forced organization

**Files:**
- Modify: `configs/reram_22nm_1t1r_slc.cfg`, `configs/reram_22nm_selector_slc.cfg` (and the `_single/_8chip/_16chip/_full_dimm` duplicates, which `mbmm_master.py:375-380` regenerates from the base), `1_run_nvsim_hardware.py:96-97`, `2_extract_hardware_metrics.py:10-58`
- Create: `configs/reram_22nm_1t1r_slc_1024.cfg`, `configs/reram_22nm_selector_slc_1024.cfg` (sensitivity)

**Interfaces:**
- Base cfgs end with a newline, then: `-ForceBank (Total AxB, Active CxD): 16x4, 1x4`, `-ForceMat (Total AxB, Active CxD): 2x2, 2x2`, `-ForceMuxSenseAmp: 64`, `-ForceMuxOutputLev1: 1`, `-ForceMuxOutputLev2: 1`, placed after `-UseCactiAssumption` (which otherwise overwrites ForceMat). The existing `-ForceMuxSenseAmp: 32` / `256` lines are removed. 1024 variants: `-ForceBank: 32x8, 1x8`, mux 64.
- `1_run_nvsim_hardware.py` success gate additionally requires the literal `2048 Rows x 2048 Columns` (or `1024 Rows x 1024 Columns` for `_1024` cfgs) in stdout; a missing `-ForceBank` key prints `cannot be found` and must fail the run.
- `2_extract_hardware_metrics.py` records `subarray_rows`, `subarray_cols`, `mats`, `mux` from the NVSim output into `hardware_metrics.json`.

- [ ] **Step 1: Edit the four base cfgs** (trailing newline first; the smoke test in `research_notes/calibration_runs/rerun_smoke/*.cfg` is the template).
- [ ] **Step 2: Add the organization gate** in `1_run_nvsim_hardware.py` and the extraction fields in `2_extract_hardware_metrics.py` (regex `(\d+) Rows x (\d+) Columns`, `Bank Organization: (\d+) x (\d+)`, `Mux: (\d+)` per the NVSim output format in `calibration_runs/rerun_smoke/out/ours_1t1r.txt`).
- [ ] **Step 3: Run NVSim for both cells**: `python3 1_run_nvsim_hardware.py --models configs/reram_22nm_1t1r_slc.cfg configs/reram_22nm_selector_slc.cfg && python3 2_extract_hardware_metrics.py`
Expected in `results/hardware_metrics.json`: 1T1R area 12.008 mm², leakage 108.384 mW, read 10.120 ns, write 15.260 ns; 1S1R area 3.540 mm², leakage 108.384 mW, read 4.702 ns, write 24.589 ns; `subarray_rows == 2048` for both.
- [ ] **Step 4: Negative test**: temporarily strip the trailing newline from a scratch copy of a cfg, run `1_run_nvsim_hardware.py --models <copy>`; expected: the script fails with the organization message, not exit 0.
- [ ] **Step 5: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add configs 1_run_nvsim_hardware.py 2_extract_hardware_metrics.py && git commit -m "[T2.6] NVSim: forced 2048x2048 mux 64 organization for both cells, organization gate, subarray fields"`

### Task T2.7: Analytic selector layer for 1S1R

**Files:**
- Create: `selector_layer.py`, `tests/test_selector_layer.py`

**Interfaces:**
- `sneak_leakage_w(cells_per_line, lines_active, v_half, i_leak_per_cell_a)`: half-select leakage power for the active wordlines/bitlines; `read_margin(n, k, r_on, r_off, r_line)` from Zhou, Kim and Lu TED 2014 Eq. 2-3 with the sinh selector `I = gamma*sinh(alpha*V)`, `k = I(V)/I(V/2)`; `tile_valid(i_on, i_leak)` from the handbook formula `tile_side <= I_on / (6 * I_leak)`.
- Two parameter sets, both bounds reported: `OTS`: k = 1e4, I_on 100 uA (Zhou Table I defaults, handbook OTS Ioff 10 nA at Vth/2); `FAST`: k = 1e6, sneak below 0.1 nA per selector (Crossbar, MEMSYS 2019).
- Output: `results/selector_layer.json` with, per bound: leakage to add to the NVSim chip leakage (W per chip, and per full DIMM), read margin at N = 2048, and the tile-validity verdict.

- [ ] **Step 1: Failing tests**: `tile_valid(100e-6, 10e-9)` is True for side 1666 and False for 2048; `read_margin(512, 1e3, ...)` is about 0.02-0.05 (Zhou Fig. 3b/9 reading) and `read_margin(256, 1e4, ...)` about 0.10; `sneak_leakage_w` scales linearly with cells and lines.
- [ ] **Step 2: Implement** with the formulas cited inline (paper, equation, page). Keep it under 150 lines.
- [ ] **Step 3: Tests pass; run** `python3 selector_layer.py --hardware results/hardware_metrics.json` and read `results/selector_layer.json`. Record both bounds in the tracker.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add selector_layer.py tests/test_selector_layer.py && git commit -m "[T2.7] Analytic 1S1R selector layer: sneak leakage, read margin, tile validity at two selector bounds"`

### Task T2.8: Microsecond-silicon sensitivity configs

**Files:**
- Create: `configs/silicon/reram_micron16gb_1t1r_full_dimm.config`, `configs/silicon/reram_sandisk32gb_1s1r_full_dimm.config` (copied into `simulators/nvmain/Config/` by T2.4's check)

**Interfaces:**
- Same template as the generator's full-DIMM output at CLK 800, but `tRCD + tCAS` = chip read latency and `tWR` = chip write latency: Micron 1T1R read 2.3 us / write 11.7 us (Zahurak IEDM 2014 Table 1) gives tRCD 920 + tCAS 920, tWR 9360; SanDisk 1S1R read 40 us / write 230 us (Liu JSSC 2014 Table II) gives tRCD 16000 + tCAS 16000, tWR 184000. Energies and leakage stay NVSim's (the point is timing only), and the header says so.
- `mbmm_master.py --silicon` runs both on every trace; `process_metrics.py` classifies them as `1T1R_SILICON` and `1S1R_SILICON`.

- [ ] **Step 1: Write the two configs** (from a generated full-DIMM config, with a header citing the two papers and page numbers).
- [ ] **Step 2: Smoke run** each on gpt2 for 200000 cycles: exit 0, `averageTotalLatency` in the thousands of cycles.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add configs/silicon mbmm_master.py process_metrics.py && git commit -m "[T2.8] Microsecond-silicon sensitivity configs from fabricated-chip latencies"`

---

# Phase 3: Traces (days 2-4, parallel with Phase 2)

### Task T3.1: gem5 MemCtrl parser with sidecar

**Files:**
- Create: `parse_gem5_memctrl.py`, `tests/test_parse_gem5_memctrl.py`, `tests/fixtures/memctrl_sample.txt`

**Interfaces:**
- CLI: `parse_gem5_memctrl.py --raw raw_trace.txt --stdout gem5_stdout.log --out benchmarks/<name>.nvt --cpufreq-mhz 3000 --region o3 --skip-ns 10000000 --sidecar benchmarks/<name>.sidecar.json`
- Keeps only `recvAtomic: <Cmd> 0x<addr>` and `recvTimingReq: request <Cmd> addr 0x<addr> size <n>` lines whose object matches `\S*mem_ctrl\S*`; drops `Access to`, `Command for`, `Responding to Address`, queue dumps; drops a request followed by a `queue full, not accepting` line.
- Ops: W = `WritebackDirty|WritebackClean|WriteReq|WriteLineReq|WriteClean`; R = `ReadReq|ReadSharedReq|ReadExReq`; any other command raises.
- Time: tick (ps) to NVMain cycle `round(tick_ps * cpufreq_mhz / 1e6)`; `--region o3` keeps ticks at or after the "Switched CPUS @ tick N" line in stdout plus `--skip-ns`; timestamps are rebased to 0 and asserted monotonic.
- Output line: `{cycle} {op} 0x{addr:x} {128 zeros} 0` (unchanged NVMain format). Sidecar JSON: source files, gem5 command (from stdout head), switch tick, region, skip, unit `"cycle = 1/3000 us (CPUFreq 3000 MHz)"`, record count, read/write counts, first/last cycle, 64-byte alignment fraction, dropped-line counts by type.

- [ ] **Step 1: Write the fixture and failing tests.** Fixture: 12 hand-written lines: two `recvAtomic` (ticks 1000, 2500), one `recvTimingReq` ReadSharedReq size 64 at tick 600000000500 with its `Access to`/`Command for`/`Responding to` companions, one WritebackDirty, one `queue full` retry pair, one unrelated `system.l2` line. Tests: (a) output has exactly the real requests (4 with region all, 2 with region o3 given a fake stdout "Switched CPUS @ tick 600000000000"); (b) ops mapped R/W; (c) cycle = tick*3/1000 rounded, rebased; (d) unknown command raises; (e) sidecar counts match.
- [ ] **Step 2: Run tests, expect failures.** `python3 -m pytest tests/test_parse_gem5_memctrl.py -v`
- [ ] **Step 3: Implement** (about 120 lines; regexes: `^\s*(\d+):\s+(\S*mem_ctrl\S*):\s+recvAtomic:\s+(\w+)\s+0x([0-9a-f]+)` and `^\s*(\d+):\s+(\S*mem_ctrl\S*):\s+recvTimingReq:\s+request\s+(\w+)\s+addr\s+0x([0-9a-f]+)\s+size\s+(\d+)`).
- [ ] **Step 4: Tests pass. Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add parse_gem5_memctrl.py tests && git commit -m "[T3.1] gem5 MemCtrl trace parser with provenance sidecar"`

### Task T3.2: STREAM trace (assistant runs it)

**Files:**
- Modify: nothing tracked; produces `benchmarks/stream.nvt` (git-ignored) and `benchmarks/stream.sidecar.json` (tracked: add `!benchmarks/*.sidecar.json` to `.gitignore`)

- [ ] **Step 1: Build STREAM static, OpenMP off**: `cd /home/yuvalk/MBMM/benchmarks && gcc -O2 -static -DSTREAM_ARRAY_SIZE=10000000 -DNTIMES=10 -o stream_bin/stream_static stream.c && ls -la stream_bin/stream_static` (default 10M doubles = 80 MB per array).
- [ ] **Step 2: Run gem5** (same recipe as SPEC, scaled so the detailed region covers 200 ms):
```bash
cd /home/yuvalk/MBMM/benchmarks && /home/yuvalk/MBMM/simulators/gem5/build/X86/gem5.opt --outdir=stream_bin/m5out --debug-flags=MemCtrl --debug-file=raw_trace.txt \
  /home/yuvalk/MBMM/simulators/gem5/configs/deprecated/example/se.py --cmd=stream_bin/stream_static \
  --cpu-type=X86O3CPU --caches --l2cache --fast-forward=500000000 --maxinsts=300000000 --mem-size=1GB > stream_bin/m5out/gem5_stdout.log 2>&1
```
Expected: exit 0; stdout contains `Switched CPUS @ tick`; `raw_trace.txt` of order 1 GB.
- [ ] **Step 3: Parse**: `python3 parse_gem5_memctrl.py --raw benchmarks/stream_bin/m5out/raw_trace.txt --stdout benchmarks/stream_bin/m5out/gem5_stdout.log --out benchmarks/stream.nvt --cpufreq-mhz 3000 --region o3 --skip-ns 10000000 --sidecar benchmarks/stream.sidecar.json`
Expected: sidecar shows about 3 reads per write (copy, scale, add, triad kernels), 100% 64-byte alignment, span at least 190 ms (570 M cycles).
- [ ] **Step 4: Keep the raw log** (decision 35) at `benchmarks/stream_bin/m5out/raw_trace.txt` until Phase 6 ends.

### Task T3.3: SCALE-Sim parser fix and AI traces

**Files:**
- Modify: `parse_trace.py:24-49`, create `tests/test_parse_scalesim.py`, `tests/fixtures/scalesim_sample.csv`

**Interfaces:**
- Every address column of a CSV row is emitted (SCALE-Sim `Bandwidth: 10` rows carry up to 10 addresses); `-1` padding is skipped; op from the filename as before; cycle basis documented in a sidecar (`"1 SCALE-Sim cycle = 1 NVMain cycle at CPUFreq 3000 (0.333 ns); SCALE-Sim's own plots assume 2.4 GHz"`).

- [ ] **Step 1: Fixture** (3 rows: cycle 5 with addresses `1024,1088,-1,-1`, cycle 7 with 10 addresses, cycle -3 first row to test rebasing) and failing tests: record count equals the number of non-negative addresses (12), no `-0x1` in output, first cycle is 0.
- [ ] **Step 2: Implement** (loop over `parts[1:]`, skip values < 0), keep the OFMAP op rule, write the sidecar.
- [ ] **Step 3: Regenerate**: `python3 parse_trace.py benchmarks/ml_trace_output/GoogleTPU_v1_os/layer0/IFMAP_DRAM_TRACE.csv benchmarks/gpt2_ifmap.nvt` and the AlexNet layer-1 IFMAP/OFMAP CSVs (rerun SCALE-Sim for AlexNet first: `cd simulators/SCALE-Sim && python3 scale.py -c configs/google.cfg -t topologies/conv_nets/alexnet.csv -p ../../benchmarks/ml_trace_output/alexnet` per its README; record the exact command in the sidecar).
Expected: gpt2 record count about 65,540 (matches `DETAILED_ACCESS_REPORT.csv` DRAM reads), zero negative addresses in all three.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add parse_trace.py tests .gitignore benchmarks/*.sidecar.json && git commit -m "[T3.3] SCALE-Sim parser: keep every address, drop padding; AI traces regenerated"`

### Task T3.4: SPEC traces (gcc, lbm, mcf) under the scoped exception

**Files:**
- Produces: `benchmarks/gcc_spec2017.nvt`, `lbm_spec2017.nvt`, `mcf_spec2017.nvt` and sidecars; raw logs kept under `benchmarks/raw_logs/<bench>/` (git-ignored via `*_raw.txt`; add `benchmarks/raw_logs/` to `.gitignore`)

- [ ] **Step 1: Locate the run directories without indexing**: the earlier runs used `/home/yuvalk/spec2017/benchspec/CPU/<id>/run/run_base_refrate_*` (per `cleanup_traces.sh:3`). Ask the Lead for the exact three run-directory paths and the `speccmds.cmd` argument line for each (602.gcc_s or 502.gcc_r, 619.lbm_s or 519.lbm_r, 505.mcf_r). Do not `find` or `ls -R` the suite.
- [ ] **Step 2: Run gcc and lbm first** (each in its run directory, one command, kept in the sidecar):
```bash
/home/yuvalk/MBMM/simulators/gem5/build/X86/gem5.opt --outdir=/home/yuvalk/MBMM/benchmarks/raw_logs/<bench> --debug-flags=MemCtrl --debug-file=raw_trace.txt \
  /home/yuvalk/MBMM/simulators/gem5/configs/deprecated/example/se.py --cmd=./<binary> --options="<args from speccmds.cmd>" \
  --cpu-type=X86O3CPU --caches --l2cache --fast-forward=500000000 --maxinsts=300000000 --mem-size=8GB > /home/yuvalk/MBMM/benchmarks/raw_logs/<bench>/gem5_stdout.log 2>&1
```
Expected: 30-60 min each; `Switched CPUS @ tick` present; LBM log of order 2.5 GB.
- [ ] **Step 3: Parse both** with `--region o3 --skip-ns 10000000` as in T3.2; expected sidecar spans of at least 190 ms and 100% alignment.
- [ ] **Step 4: Run mcf the same way**, then parse.
- [ ] **Step 5: Record in the tracker** the three commands, wall times, log sizes and sidecar summaries. The SPEC exception ends when T3.5 accepts the traces; note the date in `MBMM/CLAUDE.md` guardrail 3.

### Task T3.5: Trace validation

**Files:**
- Create: `tools/validate_trace.py`, `tests/test_validate_trace.py`

**Interfaces:**
- `validate_trace.py benchmarks/<name>.nvt --sidecar benchmarks/<name>.sidecar.json --window-ns 250000000`: checks monotonic timestamps, 5 fields per line, 128-char data, 64-byte alignment (SPEC and STREAM must be 100%; AI traces reported), no negative addresses, span covers the window (or reports the shortfall), and prints reads/writes inside the window. Exit 1 on any hard failure.

- [ ] **Step 1: Failing tests** on three tiny fixtures (good, non-monotonic, misaligned).
- [ ] **Step 2: Implement; tests pass.**
- [ ] **Step 3: Validate all seven traces**; paste the summary table (trace, records, reads, writes in window, span ms, alignment) into the tracker. Acceptance = all seven pass. Then edit `MBMM/CLAUDE.md` guardrail 3 to "ended <date>" and hand the commit: `! cd /home/yuvalk/MBMM && git add tools/validate_trace.py tests CLAUDE.md benchmarks/*.sidecar.json .gitignore && git commit -m "[T3.5] Trace validation; regenerated traces accepted; SPEC exception closed"`

---

# Phase 4: Pilot and gate (day 5-6)

### Task T4.1: Pilot run

- [ ] **Step 1: Run** `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gcc_spec2017.nvt lbm_spec2017.nvt --window-ns 250000000 --ddr5-model DDR5_4800_DRAM_subchannel --channels 1 --decoder Default --endurance-model RowModel 2>&1 | tee results/logs/pilot_$(date +%F).log`
- [ ] **Step 2: Fill the Pilot record table** in the tracker from `results/system/stats_*` and `results/processed_bar_chart_metrics.csv`, comparing with `results/archive_2026-09_pre_revision/`:

| Criterion | Expected | Where to read it |
|---|---|---|
| Latency down, DDR5 gap narrower | 1T1R SLC GCC `Latency_ns` well below 136.2 (interface-clock study predicts about 76 with the double-count fix at the new organization); ratio to DDR5 below 1.51x | processed CSV |
| LBM completion up | `Completed_Requests` for 1T1R SLC above 6,550,154 of the old window; ideally near the trace's window total | stats `totalReadRequests + totalWriteRequests` |
| Write rates down about 3x | LBM `mem_writes / 0.25 s` compared to the old `3,257,597 / 0.08333 s` | stats |
| Unrelated stats bit-identical | `tools/nvmain_regress.sh` PASS on the golden reference | harness |
| NVSim organization | `subarray_rows == 2048` in `hardware_metrics.json` | JSON |
| New stats self-consistent | `sum(wearTotalWrites) == mem_writes` per channel; `unstampedRequests == 0`; `averageEndToEndLatency >= averageTotalLatency` | stats |

- [ ] **Step 3: Decision.** All six pass: tick and proceed to Phase 5. Any failure: stop, write the explanation in the tracker, fix, re-run the pilot. Hand the tracker commit: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md && git commit -m "[T4.1] Pilot record"`

### Pilot record

| Criterion | Expected | Observed | Pass/fail | Evidence path |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |
| | | | | |

---

# Phase 5: Full matrix and analysis (days 6-9)

### Task T5.1: Primary matrix

- [ ] **Step 1:** `python3 mbmm_master.py --all --trace gcc_spec2017.nvt lbm_spec2017.nvt mcf_spec2017.nvt stream.nvt gpt2_ifmap.nvt alexnet_layer1_ifmap.nvt alexnet_layer1_ofmap.nvt --window-ns 250000000 --ddr5-model DDR5_4800_DRAM_subchannel --channels 2 --decoder StartGap --endurance-model RowModel --silicon` (matched two channels is primary per decision 38; StartGap on is primary per decision 22). Expected: 4 ReRAM tracks x 4 architectures x 7 traces + DDR5 + PCM + 2 silicon configs, exit 0, `results/processed_*.csv` complete. Copy `results/system` to `results/system_rev2026-09_primary/`.
- [ ] **Step 2: Sensitivity runs**, each into its own `results/system_rev2026-09_<axis>/` via `process_metrics.py --results-dir ... --output-dir ...`:
  - channels 1 (decision 38 cross-check)
  - DDR5 64B cross-check (`--ddr5-model DDR5_4800_DRAM_64B`)
  - decoder Default (wear leveling off; the before/after for decision 22)
  - interface clock 1333 and 2400 for the ReRAM tracks (`--freq 1333`, `--freq 2400`; the generator's validation refuses anything above 3000)
  - organization 1024x1024 (swap in the `_1024` cfgs, NVSim stage only, then NVMain)
  - queue size 8 and 128 (`--queue-size`, future-work note 3, cheap now that the window is right)
- [ ] **Step 3: Record** every run's command, date and output directory in the tracker.

### Task T5.2: Start-Gap data-movement sensitivity (only if T1.4 step 2's note applies)

- [ ] **Step 1:** If time allows, add to `StartGap::NoteWrite` an injected line read+write per gap move via the controller (a `NVMainRequest` pair issued from `MemoryController` when `moves` increments) and re-run LBM only; report the completion and latency delta as the cost of wear leveling. Otherwise state in the book that gap-move traffic (one line per 100 writes, 1% overhead) is not simulated.

### Task T5.3: Endurance analysis

**Files:**
- Create: `endurance_sensitivity.py` (from `research_notes/endurance_audit_runs/sensitivity_v2.py`), `tools/aggregate_wear.py`

**Interfaces:**
- `tools/aggregate_wear.py results/system_rev2026-09_primary/stats_<model>_<trace>.out` prints DIMM-wide: touched locations, total writes, max writes to one location, mean over touched, hot-spot factor (max / (total / total capacity locations)), and top 16; JSON to `results/wear_<model>_<trace>.json`.
- `endurance_sensitivity.py` reads write counts from the stats (window-based rate: `mem_writes / window_s`), and produces `results/endurance_table.csv` and a Typst table snippet over axes: endurance {1e4, 1e6, 1e7} x capacity {8, 64, 128 GB} x wear-leveling {measured with StartGap, measured without, ideal 1.0} x write reduction {1x, 4.5x}; plus Shahar's "required endurance for 10 years" row per workload.

- [ ] **Step 1: Failing test** for `aggregate_wear` on a 3-subarray synthetic stats text; for `endurance_sensitivity` on known inputs (e.g., 9.5 M writes/s, 64 GB, 1e6, 0.97 -> 3.47 yr).
- [ ] **Step 2: Implement; tests pass; run on the primary and the decoder-off runs.** Expected: hot-spot factor with StartGap far below without (record both); LBM steady write rate near 9.5 M/s on the new traces.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add endurance_sensitivity.py tools/aggregate_wear.py tests && git commit -m "[T5.3] Endurance sensitivity table and DIMM-wide wear aggregation"`

### Task T5.4: Figures

- [ ] **Step 1:** `visualize_slides.py` must read write counts and completion from the CSVs instead of the hardcoded dicts at lines 175-182 and 474-479, and `DATA_DIR` (line 48) must point at `results/system_rev2026-09_primary`. Update `STANDARD_FOOTNOTE` (`visualize_results.py:45-48`, `visualize_hero_graphs.py:36-39`) to: "Full-DIMM sums; 250 ms matched window (1 trace cycle = 1/3 ns); 2048x2048 subarrays, mux 64; DDR5 two 32-bit subchannels, 64 B per access; Start-Gap wear leveling; NVSim to NVMain."
- [ ] **Step 2:** Regenerate all figures via `mbmm_master.py` stage 7 (it runs automatically at the end of T5.1) and `python3 visualize_slides.py`; copy `results/final_graphs/*.png` to `documents/MBMM_Book_Typst/media/media/image{n}.png` using the same mapping as the 2026-09-12 realignment (recorded in `Review_Fixes_Tracker.md` 2026-09-12 entry).
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add visualize_slides.py visualize_results.py visualize_hero_graphs.py documents/MBMM_Book_Typst/media && git commit -m "[T5.4] Figures regenerated from the revision run"`

---

# Phase 6: Book, deck, one-pager (days 9-14)

### Task T6.1: Book corrections, section by section

**Files:**
- Modify: `documents/MBMM_Book_Typst/Project_Book.typ`; compile with `cd documents/MBMM_Book_Typst && typst compile --font-path fonts Project_Book.typ Project_Book.pdf`

Work through this list in order, ticking each; every number comes from `results/processed_*.csv`, `results/endurance_table.csv` or `results/wear_*.json`, never typed from memory:

- [ ] Abstract: remove "47x leakage discipline" and "1T1R 50.9 W infeasible"; state the matched-organization result and the selector-layer bounds; new LBM completion and endurance headline (10^6 basis, 64 GB, measured wear leveling).
- [ ] §1.2 "1024-cell bitlines" -> 2048, with the Matsui alpha figures (leakage note §13); §1.3 contribution (c) rewritten.
- [ ] §2 workload list (line 620) and §3.1.6 item 6: traces are cached gem5 O3-region traces, window starts 10 ms after the CPU switch, 250 ms; STREAM is the real benchmark; mcf added; "uncached" removed everywhere (grep `uncached`).
- [ ] §2.3 DDR5 paragraph (line 434): replace the false subchannel/BL16 claim with the true model (two 32-bit subchannels, BL16, 64 B, from T2.4); remove the bank-group claim (line 513); state 64 B for every technology; interface clock paragraph gains the 800/1333/2400 sensitivity and the Optane 2666 MT/s citation.
- [ ] §3.1.1 latency: new Table 2; the double-count correction stated; end-to-end latency introduced as the saturation measure with both definitions; queue-depth sweep numbers replaced (Appendix A "Memory Controller Queue Depth" rewritten from the new sweep).
- [ ] §3.1.2 power: leakage identical at matched organization; selector-layer bounds added; 47x and 794.7/16.9 removed (grep `47x`, `794.7`, `16.9 mW`, `50.9 W`).
- [ ] §3.1.3 PDP recomputed.
- [ ] §3.1.4 endurance: rewritten around Table 5 = `results/endurance_table.csv`; 10^6 primary cited to Chen TED 2020 (new ref), [14] no longer cited for the ratings; measured hot-spot factor with and without Start-Gap; Shahar's required-endurance row; MLC multipliers relabeled as per-bit throughput ratios with per-line as sensitivity; "1S1R lives longer" removed.
- [ ] §3.2 scaling: rerun the address-footprint explanation against the corrected capacity; rewrite whichever way the data goes.
- [ ] §3.3 ranking and Table 7; Conclusion; §4.1/§4.2 future work (Optane comparison row per `Lead_Future_Work_Notes.md` §2c option A; wide internal word behind a write-combining buffer; queue depth done).
- [ ] Appendix A: "Access-Device Leakage Model" replaced by the organization finding and the selector layer; queue-depth entry rewritten; new entry "Trace time base and window" from `trace_timebase_investigation.md`; new entry "NVSim calibration" from leakage note §14 (no drift vs upstream; sense-amp model differs from NVMExplorer; 1T1R organization-sensitive; 1S1R uncalibrated).
- [ ] New Appendix: "What changed since the 3 September version": one row per corrected claim (old value, new value, cause, evidence note path). Include the trace time base, the trace window, the double-count, the 512 GB capacity, DDR5 granularity and channels, the 47x organization artifact, endurance basis and rate, STREAM provenance, AI trace undercount, dead config lines.
- [ ] References: add Chen TED 2020, Liu JSSC 2014, Zahurak IEDM 2014, Chou VLSI 2020, Zhou/Kim/Lu TED 2014, Qureshi MICRO 2009 (Start-Gap), Yang FAST 2020, Intel PMem 200 brief; update `Reference_Guide.md`, `README.md`, `Reading_Guide.md` counts.
- [ ] Compile; grep the PDF text for every retired number (`47x`, `1.09 yr`, `83.33 ms`, `uncached`, `1024x1024`, `3.8x`); expected zero hits except inside the change appendix.
- [ ] Hand the commit to the Lead: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst && git commit -m "[T6.1] Book revision: corrected traces, organization, DDR5 baseline, endurance, change appendix"`

### Task T6.2: Deck rebuild

- [ ] **Step 1:** Rebuild `presentation_deck.html` around the new story (decision 28): keep the structure of the existing 52 slides where it still holds, replace every number from the CSVs, re-embed the regenerated charts (`visualize_slides.py` outputs, base64 as before), rewrite slides 8, 15, 18, 20, 26-28, 33-36, 39, 50-52, and make "Since the 3 September review" the change log.
- [ ] **Step 2:** Publish the artifact update to the existing URL (`https://claude.ai/code/artifact/b74b813e-da98-4f3c-972d-7f6ba3c62499`), then update `Presentation_Outline.md` and `Meeting_Prep_Cheat_Sheet.md`.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/presentation_deck.html documents/MBMM_Book_Typst/Presentation_Outline.md documents/MBMM_Book_Typst/Meeting_Prep_Cheat_Sheet.md && git commit -m "[T6.2] Deck rebuilt on the revision results"`

### Task T6.3: One-pager and note to Shahar

- [ ] **Step 1:** Rewrite `Shahar_Review_Evidence.typ` rows 6, 8 and 10 from the results (row 6: organization artifact plus selector bounds; row 8: required-endurance in his own template, measured wear leveling; row 10: matched-organization comparison), update the book section and slide references, compile.
- [ ] **Step 2:** Draft `documents/MBMM_Book_Typst/Note_to_Shahar_2026-09.md`: what his notes 6 and 8 uncovered, the five corrections, and where each is shown. Decision 2: sent only after the corrected results exist, which is now.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/Shahar_Review_Evidence.typ documents/MBMM_Book_Typst/Shahar_Review_Evidence.pdf documents/MBMM_Book_Typst/Note_to_Shahar_2026-09.md && git commit -m "[T6.3] One-pager rewritten; note to Shahar"`

### Task T6.4: Close out

- [ ] Delete raw gem5 logs (decision 35) after the book is final; keep sidecars.
- [ ] Update `MBMM_AI_Context_State.md` and the memory files (`project_leakage_47x_artifact.md`, `project_trace_timebase_endurance.md`) to "corrected in the 2026-09 revision".
- [ ] Final tracker session-log line; hand the final commit and push.

---

## Verification (end to end)

1. `python3 -m pytest tests -v`: all tests pass.
2. `tools/nvmain_regress.sh`: PASS x3 against the pre-patch golden files.
3. `tools/check_live_configs.py`: exit 0.
4. `tools/validate_trace.py` on all seven traces: pass.
5. Pilot record: six criteria observed and recorded.
6. `python3 mbmm_master.py --all ...` (T5.1) exit 0; `results/processed_bar_chart_metrics.csv` has every technology x architecture x benchmark row with the new columns populated.
7. Book compiles; retired-number grep returns zero hits outside the change appendix.
8. Every commit message carries its task id; the tracker's session log has one line per session.

## Self-review notes

- Spec coverage: decisions 1-44 map to tasks (1-2, 26-28: Phase 6; 3, 14-16, 35: T3.x; 4: T2.6; 5, 18: T2.7; 6, 22: T1.3, T1.4, T5.3; 7: T6.1 §3.1.4; 8, 23: T1.2, T2.5; 9, 19: T2.8; 10: T3.2; 11: T3.3; 12, 17: T3.4; 13, 30: schedule; 20, 32: T4.1; 21: T6.1; 24, 25, 44: T2.2; 29, 31, 40: T3.4 and the CLAUDE.md edits already made; 33: T1.1-T1.5; 34: T3.2; 36: T5.1 clock axis; 37: T2.2; 38: T5.1; 39, 41: T2.4; 42, 43: T2.5, T2.4).
- Type consistency: `compute_timings`, `validate_config`, `geometry` (T2.1/T2.2); `cycles_for` (T2.3); stat names `averageEndToEndLatency`, `wearTotalWrites`, `wearMaxWrites`, `wearHotSpotFactor` (T1.2, T1.3, T2.5, T5.3); config keys `Decoder StartGap`, `StartGapInterval`, `EnduranceModel`, `EnduranceDist`, `EnduranceDistMean` (T1.4, T2.2).
- Known uncertainty: the exact `EnduranceModel::Write` signature and the `geometry` row arithmetic are checked against the tree at execution time (steps say so).

## Pre-revision results provenance (T0.3)

Book figures 1-17, 25, 27 and Tables 2-7 of the 3 September version came from `results/system`
(post idle-gating, 2026-09-05); §3.2 chip-count trajectories from `results/system_v6`; frozen at
`results/archive_2026-09_pre_revision/`, tag `pre-revision-2026-09`.

`results/archive_2026-09_pre_revision` total size: 73M. `sha256sum hardware_metrics.json`:
`6cf3d3a11c5766573049d84a6b35ed6dfffc150bf340070c53e71c537c6e1140`.

## Session log

2026-09-18: plan approved; Phase 0 started.
2026-09-18: T1.4 Start-Gap decoder done (faithful Qureshi 2009 mapping after the plan's remap was found non-bijective; boundary-alias stat added on review); T1.5 NVSim patch log corrected. Phase 1 complete; commits for T1.4/T1.5 handed to the Lead. Phase 2 starts with T2.1/T2.2.
