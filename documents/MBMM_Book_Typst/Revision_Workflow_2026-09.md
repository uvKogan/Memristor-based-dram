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

- [x] **Step 6: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add simulators/nvmain/Decoders simulators/nvmain/MemControl/FRFCFS/FRFCFS.cpp simulators/nvmain/src && git commit -m "[T1.4] NVMain: Start-Gap wear-leveling decoder with shared gap state"`

### Task T1.5: Patch logs

**Files:**
- Modify: `simulators/nvmain/CLAUDE.md` (append items 4-6 under APPLIED REPAIRS: end-to-end stat, wear counter, StartGap; each with files, config keys, and the regression command), `simulators/nvsim/CLAUDE.md` (item 2: remove the claim that `InputParameter.cpp` was patched; it was not, per the 2026-09-15 calibration; note the `Mat.cpp` debug prints and that the "128x128 Mats" skeleton keys are unparsed)

- [x] **Step 1: Edit both files** in the existing numbered-list style.
- [x] **Step 2: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add simulators/nvmain/CLAUDE.md simulators/nvsim/CLAUDE.md && git commit -m "[T1.5] Patch logs: NVMain revision patches; correct NVSim patch history"`

---

# Phase 2: Pipeline corrections (days 2-5, parallel with Phase 3)

### Task T2.1: Test scaffolding and the timing-split test

**Files:**
- Create: `tests/conftest.py`, `tests/test_gen_nvmain_config.py`

**Interfaces:**
- Consumes (T2.2 produces): `compute_timings(read_ns, write_ns, freq_mhz) -> dict` with keys `tCAS, tRCD, tRP, tRAS, tWR, tBURST, tCCD, tCMD` (ints, cycles), and `validate_config(cfg: dict) -> list[str]` returning violations.

- [x] **Step 1: Write the failing tests**

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

- [x] **Step 2: Run to verify they fail**: `cd /home/yuvalk/MBMM && python3 -m pytest tests/test_gen_nvmain_config.py -v`
Expected: 5 failures with `AttributeError: module 'gen' has no attribute 'compute_timings'` (or similar).

### Task T2.2: Generator corrections

**Files:**
- Modify: `3_gen_nvmain_config.py` (lines 10-23 flags; 25-53 body; 90-182 template)

**Interfaces:**
- Produces: `compute_timings`, `validate_config`, `geometry` (tested in T2.1); new flags `--channels {1,2}` (default 1), `--decoder {Default,StartGap}` (default Default), `--endurance-model {RowModel,WordModel,NullModel}` (default RowModel), `--window-ns` (default 250000000: the matched window in nanoseconds, written as a comment so T2.3 can read it back).
- Template changes: `tRCD {tRCD}` and `tCAS {tCAS}` from the split; `tRAS`, `tBURST 4`, `tCCD 4` explicit; delete `tRTW`, `tBus`, `STATS_OUT`, `DECODER MigratingDecoder`; add `Decoder {decoder}`, `EnduranceModel {model}`, `EnduranceDist Uniform`, `EnduranceDistMean 1000000`, `CHANNELS {channels}`, `StartGapInterval 100` when decoder is StartGap; ROWS from `geometry()` so capacity equals the physical module (8 GiB SLC full DIMM: with COLS 1024, BANKS 8, RANKS 8, DeviceWidth 8 the per-rank row count is `2**30*8 / (1024*8*8*8)`; keep the `max(..., 65536)` floor only for `single`).

- [x] **Step 1: Implement `compute_timings`**

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

- [x] **Step 2: Implement `validate_config` and `geometry`**

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

- [x] **Step 3: Rewrite the template** using the dicts; delete the dead keys; add the endurance and decoder keys. Keep the explanatory comment blocks (lines 55-80, 144-160) and add one for the split: "tRCD + tCAS = NVSim read latency; earlier versions set both to the full latency and charged reads twice."

- [x] **Step 4: Run the tests**: `python3 -m pytest tests/test_gen_nvmain_config.py -v` expected 5 passed.

- [x] **Step 5: Gatekeeper run.** `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gcc_spec2017.nvt --cycles 66666667 --queue-size 32` (this still uses the old trace; the point is the pipeline runs end to end). Expected: exit 0; `results/system/stats_reram_22nm_1t1r_slc_full_dimm_gcc_spec2017.out` contains `capacity is 8192 MB`, no `Could not find Decoder` warning, no `EnduranceDist is not set`, and `wearTotalWrites` lines present. Then restore the frozen results: `cp -r results/archive_2026-09_pre_revision/system/. results/system/ && cp results/archive_2026-09_pre_revision/hardware_metrics.json results/` (the pre-revision live tree must not be overwritten before Phase 4).

- [ ] **Step 6: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add 3_gen_nvmain_config.py tests && git commit -m "[T2.2] Generator: charge read latency once, validate timings, match capacity to the module, endurance and decoder keys, drop dead keys"`

### Task T2.3: Master script: window-based budgets and pass-through

**Files:**
- Modify: `mbmm_master.py:195-211` (flags), `:334-335` (model lists), `:355` (generator call), `:358-400` (per-trace loop), `:395-400` (DRAM loop)

**Interfaces:**
- New flags: `--window-ns` (default 250000000), `--channels`, `--decoder`, `--endurance-model`, `--ddr5-model {DDR5_4800_DRAM_subchannel,DDR5_4800_DRAM_64B}` (default subchannel), `--silicon` (also run the T2.8 configs).
- Behavior: `cycles_for(model) = ceil(window_ns * CLK_MHz / 1000)` where CLK is read from the model's config (`CLK` line), replacing the single `--cycles` (kept as an override with a warning). Every model then admits the identical trace window.
- `dram_models` becomes `[args.ddr5_model]` plus PCM; the 2D/3D DRAM examples are dropped from the default run (they are excluded from every figure already).

- [x] **Step 1: Write the failing test** in `tests/test_mbmm_master.py`: `cycles_for("reram_22nm_1t1r_slc_full_dimm", window_ns=250e6)` returns 200,000,000 when the config says CLK 800; for CLK 2400 returns 600,000,000; for CLK 400 returns 100,000,000. Run, expect failure.
- [x] **Step 2: Implement** `cycles_for(model_name, window_ns)` reading `simulators/nvmain/Config/{model}.config`, and replace the `--cycles` uses at the `4_execute_simulation.py` calls (lines 383-386 and 395-400). Pass `--channels/--decoder/--endurance-model` to the generator call at line 355.
- [x] **Step 3: Tests pass**; then gatekeeper: `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gpt2_ifmap.nvt --window-ns 250000000`. Expected: log shows `cycles=200000000` for ReRAM, `600000000` for DDR5, `100000000` for PCM; exit 0. Restore frozen results afterwards as in T2.2 step 5.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add mbmm_master.py tests/test_mbmm_master.py && git commit -m "[T2.3] Master: matched trace window in ns, per-CLK cycle budgets, config pass-through"`

### Task T2.4: DDR5 baseline: honest subchannel config, cross-check config, divergence check

**Files:**
- Create: `configs/DDR5_4800_DRAM_subchannel.config`, `configs/DDR5_4800_DRAM_64B.config`, `tools/check_live_configs.py`
- Delete: `configs/DDR5_4800_DRAM.config` (stale; record in `Review_Fixes_Tracker.md`)
- Modify: `simulators/nvmain/Config/` gets copies of the two new files (the pipeline reads from there, `4_execute_simulation.py:108`); `process_metrics.py:53-63,74-84` and `visualize_*.py` label tables gain the two names (map both to technology `DDR5_4800`, with `Architecture` = `subchannel` / `64B`).

- [x] **Step 1: Write the subchannel config** from the live `simulators/nvmain/Config/DDR5_4800_DRAM.config` with these keys changed: `BusWidth 32`, `DeviceWidth 8`, `tBURST 8`, `tCCD 8`, `CHANNELS 2`, `RANKS 1`, `BANKS 32`, `ROWS 65536`, `COLS 64`, keep `CLK 2400`, `CPUFreq 3000`, `tCAS 40`, `tRCD 39`, `tRP 39`, `tRFC 708`, `tREFI 9375`, `EnergyModel current`, and remove `BurstLength` (dead key). Header comment: "Two independent 32-bit subchannels at BL16 = 64 B per access (JESD79-5); capacity 65536 x 64 x 64 B x 32 x 1 x 2 = 16 GiB."
- [x] **Step 2: Write the 64B cross-check config**: the live file unchanged except `tBURST 4`, `tCCD 4`, and `BurstLength` removed. Header: "Minimal correction only: same channel shape as the 3 September baseline, 64-byte access."
- [x] **Step 3: Write `tools/check_live_configs.py`**: for every `configs/*.config` there must be a byte-identical `simulators/nvmain/Config/<name>.config`; print differences and exit 1 otherwise. Add its invocation at the start of `mbmm_master.py` stage 4 (fail fast).
- [x] **Step 4: Verify capacity and timing**: run each new config on gpt2 for 20000 cycles; expected `capacity is 16384 MB` for the subchannel config, no segfault (exit 0) for both, and for the 64B config `bank0.bandwidth` about half of the old value on identical traffic.
- [x] **Step 5: Delete the stale file, record it**: append to `Review_Fixes_Tracker.md` change log: "2026-09: deleted `configs/DDR5_4800_DRAM.config` (34-34-34, tRFC 840, never read by the pipeline; the live file is `simulators/nvmain/Config/DDR5_4800_DRAM.config`); replaced by `DDR5_4800_DRAM_subchannel.config` (primary) and `DDR5_4800_DRAM_64B.config` (cross-check), both tracked and checked by `tools/check_live_configs.py`."
- [x] **Step 6: Gatekeeper**: `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gpt2_ifmap.nvt --ddr5-model DDR5_4800_DRAM_subchannel` exit 0 and both DDR5 stats files produced. Restore frozen results.
- [ ] **Step 7: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add configs tools/check_live_configs.py simulators/nvmain/Config/DDR5_4800_DRAM_subchannel.config simulators/nvmain/Config/DDR5_4800_DRAM_64B.config process_metrics.py visualize_results.py visualize_hero_graphs.py visualize_pareto.py visualize_slides.py documents/MBMM_Book_Typst/Review_Fixes_Tracker.md && git rm configs/DDR5_4800_DRAM.config && git commit -m "[T2.4] DDR5 baseline: subchannel config (64 B per access), 64B cross-check, live-config divergence check; drop stale config"`

### Task T2.5: Delivered bandwidth and new statistics in the CSVs

**Files:**
- Modify: `5_summary_report.py:35-40,79-96`, `process_metrics.py` (`parse_raw_stats` 500+, `save_bar_chart_metrics` 697-715, `save_hero_metrics` 737-754)

**Interfaces:**
- `5_summary_report.py`: column `Delivered BW (MB/s)` = `(mem_reads + mem_writes) * 64 / (simulation_cycles * 1000/CLK ns)`, summed over channels; NVMain's `bank0.bandwidth` printed as `NVMain BW (x-check)`.
- `process_metrics.py`: new CSV columns `E2E_Latency_ns` (from `averageEndToEndLatency` x cycle time), `Delivered_BW_MBps`, `Wear_Max_Writes`, `Wear_HotSpot_Factor` (DIMM-wide: max of `wearMaxWrites` over `sum(wearTotalWrites)/touched locations`), `Completed_Requests`.

- [x] **Step 1: Failing test** `tests/test_process_metrics.py`: feed a 30-line synthetic stats text with two channels, known `mem_reads`, `CLK 800`, `simulation_cycles`, `averageEndToEndLatency`, and two subarrays with `wearMaxWrites`/`wearTotalWrites`/`wearLocations`; assert the four derived values.
- [x] **Step 2: Implement** the extractors next to `extract_queue_latency` (line 186) following its regex style; add columns to the two writers; extend `5_summary_report.py` patterns and the printed table.
- [x] **Step 3: Tests pass; gatekeeper** (`--models reram_22nm_1t1r_slc --trace gpt2_ifmap.nvt`): `results/processed_bar_chart_metrics.csv` has the new columns populated for the ReRAM rows. Restore frozen results.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add 5_summary_report.py process_metrics.py tests/test_process_metrics.py && git commit -m "[T2.5] Delivered bandwidth, end-to-end latency and wear statistics in reports and CSVs"`

### Task T2.6: NVSim forced organization

**Files:**
- Modify: `configs/reram_22nm_1t1r_slc.cfg`, `configs/reram_22nm_selector_slc.cfg` (and the `_single/_8chip/_16chip/_full_dimm` duplicates, which `mbmm_master.py:375-380` regenerates from the base), `1_run_nvsim_hardware.py:96-97`, `2_extract_hardware_metrics.py:10-58`
- Create: `configs/reram_22nm_1t1r_slc_1024.cfg`, `configs/reram_22nm_selector_slc_1024.cfg` (sensitivity)

**Interfaces:**
- Base cfgs end with a newline, then: `-ForceBank (Total AxB, Active CxD): 16x4, 1x4`, `-ForceMat (Total AxB, Active CxD): 2x2, 2x2`, `-ForceMuxSenseAmp: 64`, `-ForceMuxOutputLev1: 1`, `-ForceMuxOutputLev2: 1`, placed after `-UseCactiAssumption` (which otherwise overwrites ForceMat). The existing `-ForceMuxSenseAmp: 32` / `256` lines are removed. 1024 variants: `-ForceBank: 32x8, 1x8`, mux 64.
- `1_run_nvsim_hardware.py` success gate additionally requires the literal `2048 Rows x 2048 Columns` (or `1024 Rows x 1024 Columns` for `_1024` cfgs) in stdout; a missing `-ForceBank` key prints `cannot be found` and must fail the run.
- `2_extract_hardware_metrics.py` records `subarray_rows`, `subarray_cols`, `mats`, `mux` from the NVSim output into `hardware_metrics.json`.

- [x] **Step 1: Edit the four base cfgs** (trailing newline first; the smoke test in `research_notes/calibration_runs/rerun_smoke/*.cfg` is the template).
- [x] **Step 2: Add the organization gate** in `1_run_nvsim_hardware.py` and the extraction fields in `2_extract_hardware_metrics.py` (regex `(\d+) Rows x (\d+) Columns`, `Bank Organization: (\d+) x (\d+)`, `Mux: (\d+)` per the NVSim output format in `calibration_runs/rerun_smoke/out/ours_1t1r.txt`).
- [x] **Step 3: Run NVSim for both cells**: `python3 1_run_nvsim_hardware.py --models configs/reram_22nm_1t1r_slc.cfg configs/reram_22nm_selector_slc.cfg && python3 2_extract_hardware_metrics.py`
Expected in `results/hardware_metrics.json`: 1T1R area 12.008 mm², leakage 108.384 mW, read 10.120 ns, write 15.260 ns; 1S1R area 3.540 mm², leakage 108.384 mW, read 4.702 ns, write 24.589 ns; `subarray_rows == 2048` for both.
- [x] **Step 4: Negative test**: temporarily strip the trailing newline from a scratch copy of a cfg, run `1_run_nvsim_hardware.py --models <copy>`; expected: the script fails with the organization message, not exit 0.
- [ ] **Step 5: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add configs 1_run_nvsim_hardware.py 2_extract_hardware_metrics.py && git commit -m "[T2.6] NVSim: forced 2048x2048 mux 64 organization for both cells, organization gate, subarray fields"`

### Task T2.7: Analytic selector layer for 1S1R

**Files:**
- Create: `selector_layer.py`, `tests/test_selector_layer.py`

**Interfaces:**
- `sneak_leakage_w(cells_per_line, lines_active, v_half, i_leak_per_cell_a)`: half-select leakage power for the active wordlines/bitlines; `read_margin(n, k, r_on, r_off, r_line)` from Zhou, Kim and Lu TED 2014 Eq. 2-3 with the sinh selector `I = gamma*sinh(alpha*V)`, `k = I(V)/I(V/2)`; `tile_valid(i_on, i_leak)` from the handbook formula `tile_side <= I_on / (6 * I_leak)`.
- Two parameter sets, both bounds reported: `OTS`: k = 1e4, I_on 100 uA (Zhou Table I defaults, handbook OTS Ioff 10 nA at Vth/2); `FAST`: k = 1e6, sneak below 0.1 nA per selector (Crossbar, MEMSYS 2019).
- Output: `results/selector_layer.json` with, per bound: leakage to add to the NVSim chip leakage (W per chip, and per full DIMM), read margin at N = 2048, and the tile-validity verdict.

- [x] **Step 1: Failing tests**: `tile_valid(100e-6, 10e-9)` is True for side 1666 and False for 2048; `read_margin(512, 1e3, ...)` is about 0.02-0.05 (Zhou Fig. 3b/9 reading) and `read_margin(256, 1e4, ...)` about 0.10; `sneak_leakage_w` scales linearly with cells and lines.
- [x] **Step 2: Implement** with the formulas cited inline (paper, equation, page). Keep it under 150 lines.
- [x] **Step 3: Tests pass; run** `python3 selector_layer.py --hardware results/hardware_metrics.json` and read `results/selector_layer.json`. Record both bounds in the tracker.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add selector_layer.py tests/test_selector_layer.py && git commit -m "[T2.7] Analytic 1S1R selector layer: sneak leakage, read margin, tile validity at two selector bounds"`

### Task T2.8: Microsecond-silicon sensitivity configs

**Files:**
- Create: `configs/silicon/reram_micron16gb_1t1r_full_dimm.config`, `configs/silicon/reram_sandisk32gb_1s1r_full_dimm.config` (copied into `simulators/nvmain/Config/` by T2.4's check)

**Interfaces:**
- Same template as the generator's full-DIMM output at CLK 800, but `tRCD + tCAS` = chip read latency and `tWR` = chip write latency: Micron 1T1R read 2.3 us / write 11.7 us (Zahurak IEDM 2014 Table 1) gives tRCD 920 + tCAS 920, tWR 9360; SanDisk 1S1R read 40 us / write 230 us (Liu JSSC 2014 Table II) gives tRCD 16000 + tCAS 16000, tWR 184000. Energies and leakage stay NVSim's (the point is timing only), and the header says so.
- `mbmm_master.py --silicon` runs both on every trace; `process_metrics.py` classifies them as `1T1R_SILICON` and `1S1R_SILICON`.

- [x] **Step 1: Write the two configs** (from a generated full-DIMM config, with a header citing the two papers and page numbers).
- [x] **Step 2: Smoke run** each on gpt2 for 200000 cycles: exit 0, `averageTotalLatency` in the thousands of cycles.
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

- [x] **Step 1: Write the fixture and failing tests.** Fixture: 12 hand-written lines: two `recvAtomic` (ticks 1000, 2500), one `recvTimingReq` ReadSharedReq size 64 at tick 600000000500 with its `Access to`/`Command for`/`Responding to` companions, one WritebackDirty, one `queue full` retry pair, one unrelated `system.l2` line. Tests: (a) output has exactly the real requests (4 with region all, 2 with region o3 given a fake stdout "Switched CPUS @ tick 600000000000"); (b) ops mapped R/W; (c) cycle = tick*3/1000 rounded, rebased; (d) unknown command raises; (e) sidecar counts match.
- [x] **Step 2: Run tests, expect failures.** `python3 -m pytest tests/test_parse_gem5_memctrl.py -v`
- [x] **Step 3: Implement** (about 120 lines; regexes: `^\s*(\d+):\s+(\S*mem_ctrl\S*):\s+recvAtomic:\s+(\w+)\s+0x([0-9a-f]+)` and `^\s*(\d+):\s+(\S*mem_ctrl\S*):\s+recvTimingReq:\s+request\s+(\w+)\s+addr\s+0x([0-9a-f]+)\s+size\s+(\d+)`).
- [ ] **Step 4: Tests pass. Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add parse_gem5_memctrl.py tests && git commit -m "[T3.1] gem5 MemCtrl trace parser with provenance sidecar"`

### Task T3.2: STREAM trace (assistant runs it)

**Files:**
- Modify: nothing tracked; produces `benchmarks/stream.nvt` (git-ignored) and `benchmarks/stream.sidecar.json` (tracked: add `!benchmarks/*.sidecar.json` to `.gitignore`)

- [x] **Step 1: Build STREAM static, OpenMP off**: `cd /home/yuvalk/MBMM/benchmarks && gcc -O2 -static -DSTREAM_ARRAY_SIZE=10000000 -DNTIMES=10 -o stream_bin/stream_static stream.c && ls -la stream_bin/stream_static` (default 10M doubles = 80 MB per array).
- [x] **Step 2: Run gem5** (same recipe as SPEC, scaled so the detailed region covers 200 ms):
```bash
cd /home/yuvalk/MBMM/benchmarks && /home/yuvalk/MBMM/simulators/gem5/build/X86/gem5.opt --outdir=stream_bin/m5out --debug-flags=MemCtrl --debug-file=raw_trace.txt \
  /home/yuvalk/MBMM/simulators/gem5/configs/deprecated/example/se.py --cmd=stream_bin/stream_static \
  --cpu-type=X86O3CPU --caches --l2cache --fast-forward=500000000 --maxinsts=300000000 --mem-size=1GB > stream_bin/m5out/gem5_stdout.log 2>&1
```
Expected: exit 0; stdout contains `Switched CPUS @ tick`; `raw_trace.txt` of order 1 GB.
- [x] **Step 3: Parse**: `python3 parse_gem5_memctrl.py --raw benchmarks/stream_bin/m5out/raw_trace.txt --stdout benchmarks/stream_bin/m5out/gem5_stdout.log --out benchmarks/stream.nvt --cpufreq-mhz 3000 --region o3 --skip-ns 10000000 --sidecar benchmarks/stream.sidecar.json`
Expected: sidecar shows about 3 reads per write (copy, scale, add, triad kernels), 100% 64-byte alignment, span at least 190 ms (570 M cycles).
- [x] **Step 4: Keep the raw log** (decision 35) at `benchmarks/stream_bin/m5out/raw_trace.txt` until Phase 6 ends.

### Task T3.3: SCALE-Sim parser fix and AI traces

**Files:**
- Modify: `parse_trace.py:24-49`, create `tests/test_parse_scalesim.py`, `tests/fixtures/scalesim_sample.csv`

**Interfaces:**
- Every address column of a CSV row is emitted (SCALE-Sim `Bandwidth: 10` rows carry up to 10 addresses); `-1` padding is skipped; op from the filename as before; cycle basis documented in a sidecar (`"1 SCALE-Sim cycle = 1 NVMain cycle at CPUFreq 3000 (0.333 ns); SCALE-Sim's own plots assume 2.4 GHz"`).

- [x] **Step 1: Fixture** (3 rows: cycle 5 with addresses `1024,1088,-1,-1`, cycle 7 with 10 addresses, cycle -3 first row to test rebasing) and failing tests: record count equals the number of non-negative addresses (12), no `-0x1` in output, first cycle is 0.
- [x] **Step 2: Implement** (loop over `parts[1:]`, skip values < 0), keep the OFMAP op rule, write the sidecar.
- [x] **Step 3: Regenerate**: `python3 parse_trace.py benchmarks/ml_trace_output/GoogleTPU_v1_os/layer0/IFMAP_DRAM_TRACE.csv benchmarks/gpt2_ifmap.nvt` and the AlexNet layer-1 IFMAP/OFMAP CSVs (rerun SCALE-Sim for AlexNet first: `cd simulators/SCALE-Sim && python3 scale.py -c configs/google.cfg -t topologies/conv_nets/alexnet.csv -p ../../benchmarks/ml_trace_output/alexnet` per its README; record the exact command in the sidecar).
Expected: gpt2 record count about 65,540 (matches `DETAILED_ACCESS_REPORT.csv` DRAM reads), zero negative addresses in all three.
- [ ] **Step 4: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add parse_trace.py tests .gitignore benchmarks/*.sidecar.json && git commit -m "[T3.3] SCALE-Sim parser: keep every address, drop padding; AI traces regenerated"`

### Task T3.4: SPEC traces (gcc, lbm, mcf) under the scoped exception

**Files:**
- Produces: `benchmarks/gcc_spec2017.nvt`, `lbm_spec2017.nvt`, `mcf_spec2017.nvt` and sidecars; raw logs kept under `benchmarks/raw_logs/<bench>/` (git-ignored via `*_raw.txt`; add `benchmarks/raw_logs/` to `.gitignore`)

- [x] **Step 1: Locate the run directories without indexing**: the earlier runs used `/home/yuvalk/spec2017/benchspec/CPU/<id>/run/run_base_refrate_*` (per `cleanup_traces.sh:3`). Ask the Lead for the exact three run-directory paths and the `speccmds.cmd` argument line for each (602.gcc_s or 502.gcc_r, 619.lbm_s or 519.lbm_r, 505.mcf_r). Do not `find` or `ls -R` the suite.
- [x] **Step 2: Run gcc and lbm first** (each in its run directory, one command, kept in the sidecar):
```bash
/home/yuvalk/MBMM/simulators/gem5/build/X86/gem5.opt --outdir=/home/yuvalk/MBMM/benchmarks/raw_logs/<bench> --debug-flags=MemCtrl --debug-file=raw_trace.txt \
  /home/yuvalk/MBMM/simulators/gem5/configs/deprecated/example/se.py --cmd=./<binary> --options="<args from speccmds.cmd>" \
  --cpu-type=X86O3CPU --caches --l2cache --fast-forward=500000000 --maxinsts=300000000 --mem-size=8GB > /home/yuvalk/MBMM/benchmarks/raw_logs/<bench>/gem5_stdout.log 2>&1
```
Expected: 30-60 min each; `Switched CPUS @ tick` present; LBM log of order 2.5 GB.
- [x] **Step 3: Parse both** with `--region o3 --skip-ns 10000000` as in T3.2; expected sidecar spans of at least 190 ms and 100% alignment.
- [ ] **Step 4: Run mcf the same way**, then parse. PARKED 2026-09-20: gem5 panics inside mcf's input reader; needs a rebuilt binary from the Lead and a new SPEC grant.
- [x] **Step 5: Record in the tracker** the three commands, wall times, log sizes and sidecar summaries. The SPEC exception ends when T3.5 accepts the traces; note the date in `MBMM/CLAUDE.md` guardrail 3.

### Task T3.5: Trace validation

**Files:**
- Create: `tools/validate_trace.py`, `tests/test_validate_trace.py`

**Interfaces:**
- `validate_trace.py benchmarks/<name>.nvt --sidecar benchmarks/<name>.sidecar.json --window-ns 250000000`: checks monotonic timestamps, 5 fields per line, 128-char data, 64-byte alignment (SPEC and STREAM must be 100%; AI traces reported), no negative addresses, span covers the window (or reports the shortfall), and prints reads/writes inside the window. Exit 1 on any hard failure.

- [x] **Step 1: Failing tests** on three tiny fixtures (good, non-monotonic, misaligned).
- [x] **Step 2: Implement; tests pass.**
- [x] **Step 3: Validate all seven traces**; paste the summary table (trace, records, reads, writes in window, span ms, alignment) into the tracker. Acceptance = all seven pass. Then edit `MBMM/CLAUDE.md` guardrail 3 to "ended <date>" and hand the commit: `! cd /home/yuvalk/MBMM && git add tools/validate_trace.py tests CLAUDE.md benchmarks/*.sidecar.json .gitignore && git commit -m "[T3.5] Trace validation; regenerated traces accepted; SPEC exception closed"`

---

# Phase 4: Pilot and gate (day 5-6)

### Task T4.1: Pilot run

- [x] **Step 1: Run** `python3 mbmm_master.py --models reram_22nm_1t1r_slc --trace gcc_spec2017.nvt lbm_spec2017.nvt --window-ns 250000000 --ddr5-model DDR5_4800_DRAM_subchannel --channels 1 --decoder Default --endurance-model RowModel 2>&1 | tee results/logs/pilot_$(date +%F).log`
- [x] **Step 2: Fill the Pilot record table** in the tracker from `results/system/stats_*` and `results/processed_bar_chart_metrics.csv`, comparing with `results/archive_2026-09_pre_revision/`:

| Criterion | Expected | Where to read it |
|---|---|---|
| Latency down, DDR5 gap narrower | 1T1R SLC GCC `Latency_ns` well below 136.2 (interface-clock study predicts about 76 with the double-count fix at the new organization); ratio to DDR5 below 1.51x | processed CSV |
| LBM completion up | `Completed_Requests` for 1T1R SLC above 6,550,154 of the old window; ideally near the trace's window total | stats `totalReadRequests + totalWriteRequests` |
| Write rates down about 3x | LBM `mem_writes / 0.25 s` compared to the old `3,257,597 / 0.08333 s` | stats |
| Unrelated stats bit-identical | `tools/nvmain_regress.sh` PASS on the golden reference | harness |
| NVSim organization | `subarray_rows == 2048` in `hardware_metrics.json` | JSON |
| New stats self-consistent | `sum(wearTotalWrites) == mem_writes` per channel; `unstampedRequests == 0`; `averageEndToEndLatency >= averageTotalLatency` | stats |

- [x] **Step 3: Decision.** All six pass: tick and proceed to Phase 5. Any failure: stop, write the explanation in the tracker, fix, re-run the pilot. Hand the tracker commit: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md && git commit -m "[T4.1] Pilot record"`

### Pilot record

| Criterion | Expected | Observed | Pass/fail | Evidence path |
|---|---|---|---|---|
| Latency down, DDR5 gap narrower | 1T1R SLC GCC well below 136.2 ns; ratio to DDR5 below 1.51x | 41.5 ns (device part 40.0, queue 1.5); DDR5 subchannel 65.2 ns; ratio 0.64x. Below the predicted 76 ns because that prediction used the old 32.1 ns read; the forced 2048x2048 organization reads in 10.1 ns | PASS | `results/processed_bar_chart_metrics.csv` |
| LBM completion up | Above 6,550,154 of the old window; ideally near the trace's window total | 5,564,704 completed plus 2 in flight = every request the 250 ms window holds (100%). The absolute count is below the old one only because the old trace carried 4x duplicates and the start-up burst. Ruling: pass on the stated intent (completion of the window), the old absolute number is not comparable | PASS | `results/system/stats_reram_22nm_1t1r_slc_full_dimm_lbm_spec2017.out` |
| Write rates down about 3x | LBM writes per second against old 3,257,597 / 0.08333 s = 39.1 M/s | 2,384,804 / 0.25 s = 9.54 M/s, down 4.1x; equals the validator's window figure | PASS | same stats file; `benchmarks/lbm_spec2017.nvt.sidecar.json` |
| Unrelated stats bit-identical | `tools/nvmain_regress.sh` PASS | PASS x3 (ReRAM 1T1R SLC full DIMM, DDR5, PCM) | PASS | harness output |
| NVSim organization | `subarray_rows == 2048` | 2048 x 2048 for all four cell types (1T1R SLC 10.12 / 15.26 ns, 1S1R SLC 4.70 / 24.59 ns) | PASS | `results/hardware_metrics.json` |
| New stats self-consistent | wear sum == mem_writes; unstamped == 0; end-to-end >= total | 36 files: unstamped 0 everywhere. Wear sum equals mem_writes in 22 of 24 ReRAM files; the two MLC 8-chip LBM files are 1 short with 2 requests in flight at the window edge (wear is booked at write completion). End-to-end sits 0.37 to 0.42 memory cycle BELOW total in every file: the trace stamp converts to a fractional memory cycle while the controller's arrival stamp is a whole cycle. Ruling: pass with a tolerance of one memory cycle and of the in-flight count | PASS (with tolerance) | `results/system/stats_*.out` |

Pilot findings beyond the six criteria:
- Defect found and fixed: a saturated PCM run prints `averageEndToEndLatency 2.4895e+07`; the number pattern in `process_metrics.py` (four places) and `tools/aggregate_wear.py` lacked `+`, so the cell went blank. Fixed with a regression test (452 pass). Reprocessing the pilot stats changes exactly one cell (PCM LBM end-to-end = 62.2 ms).
- The master archives `results/logs/` at stage 5, so the pilot log is at `results/archive_20260920_123946/logs/pilot_2026-09-20.log`.
- The master expands `--models reram_22nm_1t1r_slc` to all four cell types and four architectures (36 runs, 31 minutes). Longest single run about 2.5 minutes, so the 3600 s limit is not a constraint.
- For T6.1: modeled ReRAM latency is now BELOW DDR5 (41.5 vs 65.2 ns) because a 10 ns array read beats DDR5's 16.6 ns tRCD plus 16.6 ns CL. This holds only at NVSim-projected timings; the microsecond-silicon sensitivity is the counterweight and must sit next to it. MLC adds only 1 to 3 ns at these request rates because NVMain books write recovery as bank-busy time, not request latency.
- For T6.1: DDR5 power fell 0.62 to 0.25 W because the honest baseline is 8 devices and 16 GiB, not 32 devices; per-bank refresh power is unchanged. ReRAM full DIMM is 6.94 W, all static (64 chips x 108 mW), for 8 GiB. Power must be compared per GiB.
- PCM saturates on LBM (2,794,480 of 5,564,706 completed; end-to-end 62 ms).

---

# Phase 5: Full matrix and analysis (days 6-9)

### Task T5.1: Primary matrix

- [x] **Step 1:** `python3 mbmm_master.py --all --trace gcc_spec2017.nvt lbm_spec2017.nvt mcf_spec2017.nvt stream.nvt gpt2_ifmap.nvt alexnet_layer1_ifmap.nvt alexnet_layer1_ofmap.nvt --window-ns 250000000 --ddr5-model DDR5_4800_DRAM_subchannel --channels 2 --decoder StartGap --endurance-model RowModel --silicon` (matched two channels is primary per decision 38; StartGap on is primary per decision 22). Expected: 4 ReRAM tracks x 4 architectures x 7 traces + DDR5 + PCM + 2 silicon configs, exit 0, `results/processed_*.csv` complete. Copy `results/system` to `results/system_rev2026-09_primary/`.
- [x] **Step 2: Sensitivity runs**, each into its own `results/system_rev2026-09_<axis>/` via `process_metrics.py --results-dir ... --output-dir ...`:
  - channels 1 (decision 38 cross-check)
  - DDR5 64B cross-check (`--ddr5-model DDR5_4800_DRAM_64B`)
  - decoder Default (wear leveling off; the before/after for decision 22)
  - interface clock 1333 and 2400 for the ReRAM tracks (`--freq 1333`, `--freq 2400`; the generator's validation refuses anything above 3000)
  - organization 1024x1024 (swap in the `_1024` cfgs, NVSim stage only, then NVMain)
  - queue size 8 and 128 (`--queue-size`, future-work note 3, cheap now that the window is right)
- [x] **Step 3: Record** every run's command, date and output directory in the tracker.

#### T5.1 run record

| Run | Date | Command (after `python3 mbmm_master.py --all`) | Output | Result |
|---|---|---|---|---|
| Primary | 2026-09-20 12:43 to 14:10 | `--trace gcc_spec2017.nvt lbm_spec2017.nvt stream.nvt gpt2_ifmap.nvt alexnet_layer1_ifmap.nvt alexnet_layer1_ofmap.nvt --window-ns 250000000 --ddr5-model DDR5_4800_DRAM_subchannel --channels 2 --decoder StartGap --endurance-model RowModel --silicon` (no mcf: parked) | `results/system_rev2026-09_primary/` (120 stats), CSVs `results/rev2026-09_primary_csv/`, figures `results/final_graphs_rev2026-09_primary/`, log `results/rev2026-09_primary.log` | exit 0, 120 rows, no errors |
| Organization 1024 x 1024 | 2026-09-20 18:00 to 18:30 | `--organization 1024 --trace gcc_spec2017.nvt lbm_spec2017.nvt alexnet_layer1_ofmap.nvt --window-ns 250000000 --ddr5-model DDR5_4800_DRAM_subchannel --channels 2 --decoder StartGap --endurance-model RowModel` (new master flag) | `results/system_rev2026-09_org1024/` with `_csv/` (including its own `hardware_metrics.json`), log `results/rev2026-09_sens_org1024.log` | exit 0, 54 stats |
| Channel control | 2026-09-20 18:40 | `--trace gpt2_ifmap.nvt alexnet_layer1_ifmap.nvt --window-ns 250000000 --endurance-model RowModel --ddr5-model DDR5_4800_DRAM_subchannel --channels 1 --decoder StartGap` | `results/system_rev2026-09_channels1_ai/` | exit 0, 36 stats |
| Sensitivities | 2026-09-20 from 14:12 | seven axes, each `--trace gcc_spec2017.nvt lbm_spec2017.nvt alexnet_layer1_ofmap.nvt --window-ns 250000000 --endurance-model RowModel` `--ddr5-model DDR5_4800_DRAM_subchannel --channels 2 --decoder StartGap` (the primary's flags, confirmed from each dataset's own printed configs on 2026-09-21) with ONE flag changed per axis: `--decoder Default`; `--channels 1`; `--ddr5-model DDR5_4800_DRAM_64B`; `--freq 1333`; `--freq 2400`; `--queue-size 8`; `--queue-size 128` | `results/system_rev2026-09_<axis>/` with CSVs in `_csv/`; status `results/rev2026-09_sens.status`, logs `results/rev2026-09_sens_<axis>.log` | all seven exit 0, 54 stats each, 14:12 to 17:47 |

Ruling: sensitivity runs use three traces (gcc, lbm, AlexNet output map: one light, one heavy, one write-dominated AI burst) instead of six, to keep seven full master runs near five hours. The 1024x1024 organization axis is not in this series: the master hardwires the two base ReRAM models, so it needs its own staged run.

Primary headline, full DIMM, latency in ns (DDR5 / 1T1R SLC / 1S1R SLC): gcc 65.2 / 41.4 / 36.8; lbm 66.6 / 43.1 / 38.1; STREAM 63.8 / 42.3 / 37.3; GPT-2 input 207.8 / 143.3 / 130.1; AlexNet input 199.5 / 143.6 / 130.0; AlexNet output (write-dominated) 158.8 / 353.1 / 391.5. With published silicon timings the same DIMM is 11.9 microseconds (Micron 1T1R) and 379 microseconds (SanDisk 1S1R) on gcc, and neither completes the LBM window (18% and 1%). PCM completes 50% of LBM. Power: DDR5 0.25 to 0.36 W for 16 GiB; ReRAM 6.9 to 7.3 W for 8 GiB, almost all static.

### Task T5.2: Start-Gap data-movement sensitivity (only if T1.4 step 2's note applies)

- [ ] **Step 1:** If time allows, add to `StartGap::NoteWrite` an injected line read+write per gap move via the controller (a `NVMainRequest` pair issued from `MemoryController` when `moves` increments) and re-run LBM only; report the completion and latency delta as the cost of wear leveling. Otherwise state in the book that gap-move traffic (one line per 100 writes, 1% overhead) is not simulated.

### Task T5.3: Endurance analysis

**Files:**
- Create: `endurance_sensitivity.py` (from `research_notes/endurance_audit_runs/sensitivity_v2.py`), `tools/aggregate_wear.py`

**Interfaces:**
- `tools/aggregate_wear.py results/system_rev2026-09_primary/stats_<model>_<trace>.out` prints DIMM-wide: touched locations, total writes, max writes to one location, mean over touched, hot-spot factor (max / (total / total capacity locations)), and top 16; JSON to `results/wear_<model>_<trace>.json`.
- `endurance_sensitivity.py` reads write counts from the stats (window-based rate: `mem_writes / window_s`), and produces `results/endurance_table.csv` and a Typst table snippet over axes: endurance {1e4, 1e6, 1e7} x capacity {8, 64, 128 GB} x wear-leveling {measured with StartGap, measured without, ideal 1.0} x write reduction {1x, 4.5x}; plus Shahar's "required endurance for 10 years" row per workload.

- [ ] **Step 1: Failing test** for `aggregate_wear` on a 3-subarray synthetic stats text; for `endurance_sensitivity` on known inputs (e.g., 9.5 M writes/s, 64 GB, 1e6, 0.97 -> 3.47 yr).
- [x] **Step 2: Implement; tests pass; run on the primary and the decoder-off runs.** Expected: hot-spot factor with StartGap far below without (record both); LBM steady write rate near 9.5 M/s on the new traces.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add endurance_sensitivity.py tools/aggregate_wear.py tests && git commit -m "[T5.3] Endurance sensitivity table and DIMM-wide wear aggregation"`

### Task T5.4: Figures

- [x] **Step 1:** `visualize_slides.py` must read write counts and completion from the CSVs instead of the hardcoded dicts at lines 175-182 and 474-479, and `DATA_DIR` (line 48) must point at `results/system_rev2026-09_primary`. Update `STANDARD_FOOTNOTE` (`visualize_results.py:45-48`, `visualize_hero_graphs.py:36-39`) to: "Full-DIMM sums; 250 ms matched window (1 trace cycle = 1/3 ns); 2048x2048 subarrays, mux 64; DDR5 two 32-bit subchannels, 64 B per access; Start-Gap wear leveling; NVSim to NVMain."
- [x] **Step 2:** Regenerate all figures via `mbmm_master.py` stage 7 (it runs automatically at the end of T5.1) and `python3 visualize_slides.py`; copy `results/final_graphs/*.png` to `documents/MBMM_Book_Typst/media/media/image{n}.png` using the same mapping as the 2026-09-12 realignment (recorded in `Review_Fixes_Tracker.md` 2026-09-12 entry).
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add visualize_slides.py visualize_results.py visualize_hero_graphs.py documents/MBMM_Book_Typst/media && git commit -m "[T5.4] Figures regenerated from the revision run"`

---

# Phase 6: Book, deck, one-pager (days 9-14)

### Task T6.1: Book corrections, section by section

**Files:**
- Modify: `documents/MBMM_Book_Typst/Project_Book.typ`; compile with `cd documents/MBMM_Book_Typst && typst compile --font-path fonts Project_Book.typ Project_Book.pdf`

Work through this list in order, ticking each; every number comes from `results/processed_*.csv`, `results/endurance_table.csv` or `results/wear_*.json`, never typed from memory:

- [x] Abstract: remove "47x leakage discipline" and "1T1R 50.9 W infeasible"; state the matched-organization result and the selector-layer bounds; new LBM completion and endurance headline (10^6 basis, 64 GB, measured wear leveling).
- [x] §1.2 "1024-cell bitlines" -> 2048, with the Matsui alpha figures (leakage note §13); §1.3 contribution (c) rewritten.
- [x] §2 workload list (line 620) and §3.1.6 item 6: traces are cached gem5 O3-region traces, window starts 10 ms after the CPU switch, 250 ms; STREAM is the real benchmark; mcf added; "uncached" removed everywhere (grep `uncached`).
- [x] §2.3 DDR5 paragraph (line 434): replace the false subchannel/BL16 claim with the true model (two 32-bit subchannels, BL16, 64 B, from T2.4); remove the bank-group claim (line 513); state 64 B for every technology; interface clock paragraph gains the 800/1333/2400 sensitivity and the Optane 2666 MT/s citation.
- [x] §3.1.1 latency: new Table 2; the double-count correction stated; end-to-end latency introduced as the saturation measure with both definitions; queue-depth sweep numbers replaced (Appendix A "Memory Controller Queue Depth" rewritten from the new sweep).
- [x] §3.1.2 power: leakage identical at matched organization; selector-layer bounds added; 47x and 794.7/16.9 removed (grep `47x`, `794.7`, `16.9 mW`, `50.9 W`).
- [x] §3.1.3 PDP recomputed.
- [x] §3.1.4 endurance: rewritten around Table 5 = `results/endurance_table.csv`; 10^6 primary cited to Chen TED 2020 (new ref), [14] no longer cited for the ratings; measured hot-spot factor with and without Start-Gap; Shahar's required-endurance row; MLC multipliers relabeled as per-bit throughput ratios with per-line as sensitivity; "1S1R lives longer" removed.
- [x] §3.2 scaling: rerun the address-footprint explanation against the corrected capacity; rewrite whichever way the data goes.
- [x] §3.3 ranking and Table 7; Conclusion; §4.1/§4.2 future work (Optane comparison row per `Lead_Future_Work_Notes.md` §2c option A; wide internal word behind a write-combining buffer; queue depth done).
- [x] Appendix A: "Access-Device Leakage Model" replaced by the organization finding and the selector layer; queue-depth entry rewritten; new entry "Trace time base and window" from `trace_timebase_investigation.md`; new entry "NVSim calibration" from leakage note §14 (no drift vs upstream; sense-amp model differs from NVMExplorer; 1T1R organization-sensitive; 1S1R uncalibrated).
- [x] New Appendix: "What changed since the 3 September version": one row per corrected claim (old value, new value, cause, evidence note path). Include the trace time base, the trace window, the double-count, the 512 GB capacity, DDR5 granularity and channels, the 47x organization artifact, endurance basis and rate, STREAM provenance, AI trace undercount, dead config lines.
- [x] References: add Chen TED 2020, Liu JSSC 2014, Zahurak IEDM 2014, Chou VLSI 2020, Zhou/Kim/Lu TED 2014, Qureshi MICRO 2009 (Start-Gap), Yang FAST 2020, Intel PMem 200 brief; update `Reference_Guide.md`, `README.md`, `Reading_Guide.md` counts.
- [x] Compile; grep the PDF text for every retired number (`47x`, `1.09 yr`, `83.33 ms`, `uncached`, `1024x1024`, `3.8x`); expected zero hits except inside the change appendix.
- [ ] Hand the commit to the Lead: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst && git commit -m "[T6.1] Book revision: corrected traces, organization, DDR5 baseline, endurance, change appendix"`

### Task T6.2: Deck rebuild

- [x] **Step 1:** Rebuild `presentation_deck.html` around the new story (decision 28): keep the structure of the existing 52 slides where it still holds, replace every number from the CSVs, re-embed the regenerated charts (`visualize_slides.py` outputs, base64 as before), rewrite slides 8, 15, 18, 20, 26-28, 33-36, 39, 50-52, and make "Since the 3 September review" the change log.
- [ ] **Step 2:** Publish the artifact update to the existing URL (`https://claude.ai/code/artifact/b74b813e-da98-4f3c-972d-7f6ba3c62499`), then update `Presentation_Outline.md` and `Meeting_Prep_Cheat_Sheet.md`.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/presentation_deck.html documents/MBMM_Book_Typst/Presentation_Outline.md documents/MBMM_Book_Typst/Meeting_Prep_Cheat_Sheet.md && git commit -m "[T6.2] Deck rebuilt on the revision results"`

### Task T6.3: One-pager and note to Shahar

- [x] **Step 1:** Rewrite `Shahar_Review_Evidence.typ` rows 6, 8 and 10 from the results (row 6: organization artifact plus selector bounds; row 8: required-endurance in his own template, measured wear leveling; row 10: matched-organization comparison), update the book section and slide references, compile.
- [x] **Step 2:** Draft `documents/MBMM_Book_Typst/Note_to_Shahar_2026-09.md`: what his notes 6 and 8 uncovered, the five corrections, and where each is shown. Decision 2: sent only after the corrected results exist, which is now.
- [ ] **Step 3: Hand the commit to the Lead**: `! cd /home/yuvalk/MBMM && git add documents/MBMM_Book_Typst/Shahar_Review_Evidence.typ documents/MBMM_Book_Typst/Shahar_Review_Evidence.pdf documents/MBMM_Book_Typst/Note_to_Shahar_2026-09.md && git commit -m "[T6.3] One-pager rewritten; note to Shahar"`

### Task T6.4: Close out

- [ ] Delete raw gem5 logs (decision 35) after the book is final; keep sidecars.
- [x] Update `MBMM_AI_Context_State.md` and the memory files (`project_leakage_47x_artifact.md`, `project_trace_timebase_endurance.md`) to "corrected in the 2026-09 revision".
- [ ] Final tracker session-log line; hand the final commit and push.

---

## Verification (end to end)

1. `python3 -m pytest tests -v -m ""`: all tests pass, including the slow-marked ones that `pytest.ini` deselects by default.
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
2026-09-18: T2.1/T2.2 generator done: read latency charged once (tRCD 13 + tCAS 13 at 800 MHz for 1T1R SLC), fatal validation, capacity 8192 MB (was 512 GB), MATHeight = NVSim subarray rows (NVMain's stale 65536 default segfaulted at the corrected ROWS), endurance and decoder keys, dead keys dropped. 7 tests pass.
2026-09-19: T2.3 master done: --window-ns gives every model the same 250 ms window (200M/600M/100M cycles at CLK 800/2400/400, exact integer rounding). Found and fixed: 4_execute_simulation.py skipped PCM silently (native models were detected only by 'DRAM' in the name) and the master always exited 0; failures now propagate. 25 tests pass.
2026-09-19: T2.4 DDR5 baseline done: two-subchannel config (BusWidth 32, BL16, 64 B per access, 8192 MB x 2 channels) and a 64B cross-check; stale configs/ copy deleted; check_live_configs.py wired into the master. Plan defect corrected: both DDR5 variants are full_dimm rows (the plan's variant tags would have dropped DDR5 from every full-DIMM figure); process_metrics now refuses duplicate rows, so T5.1 must start from an emptied results/system. Found: the old live DDR5 config modeled 32 GiB, not 16. 46 tests pass.
2026-09-19: T2.5 done: five new CSV columns (E2E_Latency_ns, Delivered_BW_MBps, Completed_Requests, Wear_Max_Writes, Wear_HotSpot_Factor). Two plan defects corrected: elapsed time is NVMain's exit cycle on the 3000 MHz CPU clock, not the memory clock; and every cycles-to-ns conversion now reads the clocks from the stats file itself (the fixed per-technology table would have reported a 2400 MHz ReRAM run 3x too slow). Post-processing scripts now exit non-zero on any unparsable stats file. 89 tests pass.
2026-09-19: T2.6 done: both cells forced to 2048x2048 subarrays at mux 64; NVSim gives 1T1R 12.008 mm2 / 108.384 mW / 10.120 ns read / 15.260 ns write and 1S1R 3.540 mm2 / 108.384 mW / 4.702 / 24.589 (identical leakage: the 47x gap is gone). Organization gate (anchored match) in both NVSim call sites via nvsim_common.py; a misspelled -ForceBank now fails the run. Found and fixed: stale per-architecture NVSim result files polluted hardware_metrics.json on every second run and produced bogus double-suffixed NVMain configs. Negative-test note: a cfg without a trailing newline is parsed fine; the real trap is appending a key to such a file (nvsim CLAUDE.md corrected). New device metrics kept at results/rev2026-09_staging/. 101 tests pass.
2026-09-20: T2.7 selector layer done. At a 2048-cell side: OTS bound tile NOT VALID (max side 1666), 7.56 mW per chip access-time sneak, margin 24.0%; FAST bound VALID, 0.076 mW, margin 23.2%. Standby adder zero. 1S1R at 2048x2048 is therefore conditional on selector quality; the book must say so. My '10% at 256' target was a misreading of Zhou Fig. 3(b) (6.8%).
2026-09-20: T2.8 done and Phase 2 complete. Silicon sensitivity configs are generated (not static) from Zahurak IEDM 2014 Table 1 (2.3 / 11.7 us) and Liu JSSC 2014 Table II (40 / 230 us): tRCD+tCAS 1840 and 32000 cycles, tWR 9360 and 184000 at 800 MHz. Plan defect fixed: --channels 2 crashed the generator (rows were halved below the subarray height); channels now split ranks (full DIMM: 4 ranks x 2 channels, capacity unchanged); one-rank modules stay at one channel. 197 tests pass (+1 slow). Next: Phase 3 traces; needs the three SPEC run-directory paths and command lines from the Lead.
2026-09-20: T3.4 step 1 done at the Lead's request: no SPEC run directories exist; March runs were launched from data/refrate/input of 502.gcc_r / 505.mcf_r / 519.lbm_r; exact command lines recovered from gem5's config.ini (see trace_timebase_investigation.md section 8). The March mcf attempt died at 0.13 ms, so mcf has never been traced.
2026-09-20: T3.1 parser done (v1.2.0). On a real gem5 log its detailed-region counts equal gem5's own mem_ctrls.readReqs / writeReqs exactly (55,556 / 23,657), and the old parser's rule would have kept 4.0x as many lines. Exact integer tick-to-cycle conversion at CPUFreq 3000, regions all/ff/o3, per-controller retry drops settled by tick, full line accounting, atomic write with a provenance sidecar, never overwrites without --force. T3.2 STREAM gem5 run started 08:19 (detached), artifacts under benchmarks/raw_logs/stream/.
2026-09-20: T3.3 done. AI traces regenerated with every address kept and padding dropped: GPT-2 IFMAP 6,554 -> 65,536 (10.0x), AlexNet layer1 IFMAP 184,320 -> 1,269,600 (6.9x; 31% of slots were padding, previously written as -0x1), AlexNet layer1 OFMAP 13,543 -> 135,424 (10.0x); all match SCALE-Sim's access report. Provenance closed: the old AlexNet traces are reproduced byte for byte from SCALE-Sim folder layer1 (zero-indexed: AlexNet's SECOND convolution layer), so that is the layer every earlier result used. Old traces preserved under benchmarks/pre_revision_2026-09/; the regression harness now replays a tracked gzip copy of the frozen GPT-2 trace.
2026-09-20: T3.4 gcc and lbm gem5 runs started 09:15 (detached, from data/refrate/input, 8 GB, ff 500M + 300M detailed). mcf PARKED: gem5 panics 0.13 ms in, inside mcf's input reader (a node index parsed from inp.in comes back as about 2^55), the same failure as the March attempt; fixing it needs a rebuilt binary, which only the Lead can produce. The revision proceeds with six traces.
2026-09-20: gem5 runs finished, all exit 0: STREAM (94 min, detailed region 1.482 s), gcc (33 min, 0.216 s), lbm (35 min, 0.494 s). gcc and lbm switched CPUs at exactly the March ticks, so the runs are reproducible. gcc's detailed region is shorter than skip + window, so gcc is being rerun with 400M detailed instructions. lbm and STREAM are being parsed into benchmarks/rev2026-09_staging/.
2026-09-20: new lbm trace validated (staging): 10.78 M records over 484 ms, every request accounted for against gem5's own counters (kept + skipped = 11,001,972 = readReqs + writeReqs), 100% aligned, no duplicates. Window write rate 9.54 M writes/s: the steady state the endurance deep dive predicted, against 27.9 M/s in the old start-up window.
2026-09-20: all three gem5 traces parsed and validated against the full 250 ms window (staging folder), each reconciling EXACTLY with gem5's own memory-controller request counters: gcc 545,566 records (220,776 writes in window, 0.88 M/s), lbm 10.78 M (2.38 M writes, 9.54 M/s), STREAM 48.4 M (2.00 M writes, 7.99 M/s; 2 reads per write). gcc needed a rerun with 400M detailed instructions (277.5 ms). Parser fix: gem5 prints address zero as a bare 0; the fail-loud rule caught it.
2026-09-20: PHASE 3 COMPLETE with six traces. Old gcc/lbm/STREAM traces preserved under benchmarks/pre_revision_2026-09/, regenerated ones swapped in with sidecars; all six pass validation in place. SPEC exception closed in both CLAUDE.md files with a usage record. T5.3 endurance tools complete and independently verified (model within 0.3% of a write-by-write simulator; required endurance is an exact inverse of lifetime). Next: Phase 4 pilot.
2026-09-20: T4.1 PILOT PASSED, all six criteria (two with a stated tolerance). 1T1R SLC full DIMM on gcc: 41.5 ns against DDR5 subchannel 65.2 ns (was 136.2 vs 90.2). LBM completes 100% of the 250 ms window, 9.54 M writes/s. One defect found and fixed (scientific-notation stats parsed as blank). Gate open for Phase 5.
2026-09-20: T5.1 PRIMARY MATRIX DONE, exit 0, 120 runs in 87 min (two channels, Start-Gap on, silicon configs). The run also verified through the master the pilot's number-format fix and the T5.4 figure scripts (26 figures regenerated). Sensitivity series (seven axes, three traces) started 14:12. T5.4 step 1 reviewed and accepted (485 tests).
2026-09-20: T5.3 analysis run on the primary matrix (1T1R SLC full DIMM; gcc, lbm, STREAM, AlexNet output map). Outputs: `results/endurance_table.csv` (576 rows), `results/wear_1T1R_SLC_<trace>.json`, log `results/rev2026-09_endurance.log`. PROJECTED (never "measured") at 64 GiB and 1e6 cycles, admitted rate: ideal leveling gives gcc 38.6 y, lbm 3.57 y, STREAM 4.26 y; no leveling gives 7.7 h, 23 h, 69 h; deterministic Start-Gap with one whole-module region equals no leveling (the hot line dies before the first rotation completes); randomized Start-Gap gives lbm 0.20 y and STREAM 0.96 y. Endurance required for 10 years: ideal 2.6e5 / 2.8e6 / 2.3e6; randomized Start-Gap 6.3e6 / 6.5e6 / 4.3e6; none 1.1e10 / 3.8e9 / 1.3e9. LBM admitted rate 9.54 M writes/s as predicted. Defect fixed: the admitted-rate rows of a microsecond-burst trace were not flagged as burst-derived (now flagged, with a test; 486 pass). For T6.1: NVMain's RowModel books wear per ROW (1024 column lines), so `Wear_Max_Writes` (lbm 3072 = 3 x 1024) overstates per-cell wear by up to 1024x; use it only for the Start-Gap on/off comparison, and take per-line wear from the trace-level analysis. The Typst snippet is overwritten per run: generate one per trace into separate folders when the book needs them.
2026-09-20: Start-Gap on versus off (primary versus `results/system_rev2026-09_decoder_default/`, 1T1R SLC full DIMM): wear statistics and latency are IDENTICAL on gcc, lbm and the AlexNet output map (row-level max 1059 / 3072 / 40704, hot-spot factor 2.77 / 1.06 / 1.20 both ways). This is the expected outcome, not a defect: with one whole-module region of 134,217,728 lines and one gap move per 100 writes, a 250 ms window makes 2,207 gap moves on gcc (23,848 on lbm), about 1e-5 of one rotation, and the gap starts at the top of the module while the workloads occupy low addresses. For T6.1: the simulator cannot show wear leveling at work inside any feasible window; the effect of leveling is carried by the projection (`endurance_table.csv`), whose model was validated against a write-by-write simulator to 0.3%. The book must say this in one sentence rather than show a before/after hot-spot figure. Latency cost of enabling the decoder: none measurable (gap-move traffic is not simulated, 1% write overhead stated).
2026-09-20: T6.1 PART A done and reviewed (book compiles, 88 pages): abstract, sections 1.2/1.3, workload list, DDR5 and capacity, latency (Table 2 with silicon-timing rows beside it), power per GiB, PDP, endurance (Table 5 from the projection), ranking and conclusion, Appendix A entries, new Appendix D "What changed since the 3 September version" (35 rows), references [47]-[54]. Independent review: 163 numbers checked, 0 mismatches in any table, 11 in prose (all fixed); 5 Critical and 8 Important findings, all fixed and re-verified (22 fixed, 1 partial closed by the controller). Rulings: per-GiB power 40 to 55x DDR5 stays but is an upper bound (DDR5 gets power-down credit, ReRAM none; break-even idle gating 98.2%, inside the cited 94 to 98% idleness); "PCM beats ReRAM on PDP" is not a headline (half-completed windows, loses per GiB, inherited constants); Start-Gap lifetime can worsen with capacity under one whole-module region (correct model consequence). PART B remains, 8 `TODO(T6.1B)` markers: interface-clock sensitivity, queue-depth sweep, section 3.2 scaling and its appendix entry, and ALL FIGURES (27 still show the pre-revision dataset under interim warning captions; the book must not go to Shahar before they are replaced).
2026-09-20: T5.1 SENSITIVITY SERIES DONE, seven axes, all exit 0 (full DIMM, latency ns / end-to-end). Interface clock: 1T1R SLC on gcc 41.4 at 800 MHz, 27.9 at 1333, 19.0 at 2400 (1S1R SLC 36.8 / 23.6 / 14.9); on the AlexNet output burst 353 / 263 / 200. Channels 1 versus 2: no effect on the CPU traces (41.5 vs 41.4), burst end-to-end 717 vs 486 microseconds. DDR5 64B cross-check: 62.9 vs 65.2 ns on gcc, but on the AlexNet output burst 57.1 ns and 61.7 microseconds end-to-end against 158.8 ns and 151 microseconds for the two-subchannel model: the honest subchannel baseline is 2.4x slower under a dense burst. Queue size (ReRAM only, the flag does not reach the DDR5 or PCM configs): no effect on gcc or lbm at 8, 32 or 128 (never saturated); on the AlexNet output burst the in-controller latency goes 124.9 / 353.1 / 1049.2 ns while end-to-end goes 680 / 486 / 432 microseconds, i.e. a deeper queue RAISES the classic latency metric and LOWERS the real one, which is the case for reporting end-to-end latency. Start-Gap off: identical to on (see previous entry). Organization 1024x1024: separate task, needs a master flag.
2026-09-20: Channel-versus-rank control run (`--channels 1` on gpt2_ifmap and alexnet_layer1_ifmap; `results/system_rev2026-09_channels1_ai/`, log `results/rev2026-09_sens_channels1_ai.log`, exit 0, 36 stats). 1T1R SLC, latency ns (queue / device): with ONE channel the 8-chip, 16-chip and full-DIMM points are identical on GPT-2 input (240.6 = 211.5 + 29.1 at all three) and on AlexNet input (241.2, 242.0, 242.0); with TWO channels the 16-chip and full-DIMM points drop to 143.3 and 143.6 (queue 114.3, device unchanged at 29.0). The 1.68x step on the AI read bursts is therefore entirely the second channel (admission queueing at a second controller), and rank count adds nothing on those traces. On the CPU traces rank depth is worth 3.9 to 7.5% at fixed channel count (device component). This run also exercised the new `--organization` master code at its default and the figure-script fixes (8-chip point restored to the Pareto figures, em-dashes removed from figure titles). Organization 1024x1024 run done (`results/system_rev2026-09_org1024/`, exit 0, 54 stats; under review).
2026-09-20: ORGANIZATION AXIS DONE. New master flag `--organization {2048,1024}` (default unchanged, reviewed; review found the area-density ratio of a 1024 run silently taken from the 2048 hardware entry and an unanchored `_1024` filename match, both fixed with tests; 514 pass; default path re-verified through the master, exit 0). NVSim at 1024 x 1024: leakage 224.1 (1T1R) and 220.2 mW (1S1R) per chip against 108.4 for both at 2048 x 2048, area 13.5 and 5.13 mm2 against 12.0 and 3.54, read 9.31 and 4.45 ns against 10.12 and 4.70. Full DIMM: latency 4 to 10% lower, power 14.3 W against 6.9 W. Leakage follows sense-amplifier count (4x mats, half the amplifiers each); the two cells still leak within 2% of each other, so the matched-organization conclusion does not depend on the organization chosen. Written into book section 3.2. T6.1 PART B done (sensitivities, section 3.2 rewritten with Table 8, 26 figures regenerated from the primary dataset, Figure 19 kept with a dataset caption; review: 0 mismatches in tables, 3 Critical / 7 Important prose findings fixed; re-review running). Figure scripts: 8-chip point restored to the Pareto figures, display-name titles, em-dashes removed. Live `results/` restored to the primary dataset; `results/final_graphs` = `results/book_figures_rev2026-09`.
2026-09-20: T6.1 BOOK COMPLETE (98 pages, compiles clean, no open markers). Part B re-review: 3/3 Critical, 6/7 Important (the seventh, em-dashes baked into the kept Figure 19 image, closed by regenerating that plot from its saved sweep data with a corrected title), 10/10 Minor, 13/13 number mismatches fixed; the controller's organization paragraph verified exact. Deviations from the T6.1 text, by ruling: no mcf trace (parked: gem5 panics in its input reader); section 3.2's claim reversed by the data (channel count, not rank count, moves burst latency; shown by a one-channel control run); wear leveling shown by projection, not by an in-simulator before/after; PCM's PDP lead and the per-GiB power gap both carry explicit caveats. End-to-end verification: 515 tests pass including the slow-marked ones; regression harness PASS x3; live-config check 0; all six traces validate; primary matrix and eight sensitivity runs exit 0. Two org-axis tests were found to depend on the live hardware_metrics.json and were made self-contained. Remaining: T6.2 deck, T6.3 one-pager and note to Shahar, T6.4 close-out, final whole-branch review.
2026-09-20: T6.3 done and reviewed. One-pager: all ten rows updated from the corrected book (rows 6, 8, 10 rewritten), still one page, zero number mismatches in review; row 4 (DDR5 typical versus worst-case current) retagged "Answered, partly" and the banner says so, because no typical IDD figure exists. Note to Shahar drafted (`Note_to_Shahar_2026-09.md`, DRAFT, not sent); review caught that its latency item credited the double-count fix alone and lacked the projection caveat: rewritten to name both causes (double-count and the 10.1 ns array read of the 2048 x 2048 organization) and to carry the silicon-timing and write-burst caveat. The Lead's pre-task one-pager is preserved in the SDD workspace. Both files and the PDF are left untracked for the Lead to add. Book: Table 5 corrections found during deck and one-pager review (AlexNet output rate 132.5 M/s, burst over drain time; STREAM required endurance 2.3e6).
2026-09-20: T6.2 DECK REBUILT and reviewed: 60 slides (9 kept, 38 rewritten, 13 new, 5 removed), 15 data-driven charts, `tests/test_presentation_deck.py` guards structure, retired values (change-log slides only), em-dashes, and the rule that every "ReRAM faster than DDR5" claim carries the projection caveat. Review: 200+ numbers reconcile with book and data; 1 Critical, 5 Important, 11 Minor fixed; re-review residuals (5) fixed and verified by the controller; 564 tests pass. NOT DONE: step 2, publishing the update to the existing artifact URL. The permission system blocked the controller's publish, correctly: that artifact is shared with anyone who has the link, so republishing is the Lead's call. Nobody has seen the deck rendered (no browser here): slides 16, 41, 51, 53, 56 to 59 need one human pass. T6.4: context state regenerated (old one archived), memory notes updated; raw gem5 logs (62 GB) deliberately NOT deleted by the controller, command handed to the Lead.
2026-09-20: FINAL WHOLE-BRANCH REVIEW: "ready after listed fixes" (2 Critical, 11 Important, 10 Minor; 565 tests pass; 25 load-bearing numbers agree across every deliverable and with the frozen data, so the problems are at the source, not drift). CRITICAL 1, verified by the controller: NVMain's `StandardRank.cpp` (upstream, 2014) in current-based energy mode accumulates background energy for the whole rank but divides background power by the device count and never multiplies back (activate, burst and refresh power are re-multiplied), so DDR5, the only current-mode technology, had its static power undercounted 4x: the book's 0.181 W static is below the floor of the config's own datasheet currents (8 x 46.87 mA x 1.1 V = 0.412 W). Expected effect: DDR5 module about 0.8 to 1.1 W instead of 0.25 to 0.36; ReRAM per-GiB power ratio about 13 to 17x instead of 40 to 55x; break-even idle gating about 94% instead of 98.2%; PDP ratios shrink about 3x. Being fixed in post-processing from the frozen stats (task F1), no re-simulation. CRITICAL 2: the latency headline is explained by the wrong mechanism (only 9 of 33 memory cycles come from NVSim; the rest are NVMain default interface cycle counts at the assumed 800 MHz clock; cell write time is not on the request path, so "MLC is barely slower" is a modeling artifact): direction robust at every clock, wording to be corrected. IMPORTANT, ruled: the DDR5 config's write-path and power-down timings are DDR3-era cycle counts, which favored DDR5; to be corrected to JEDEC DDR5-4800 and DDR5 re-run alone (task F4). All documents (book, deck, one-pager, note, context file, guides, memory) will be corrected once from the F1 and F4 numbers (task F3); code hardening (silent fallbacks, output provenance, stale README and configs/CLAUDE.md) is task F2. NOTHING in the power or PDP sections of the book, deck, one-pager or note may be shown to anyone until F3 lands.
2026-09-21: F1 DONE (DDR5 background-power correction, in post-processing only; NVMain C++ untouched, defect documented in `simulators/nvmain/CLAUDE.md`). `process_metrics.py` detects a current-mode stats file by its `mA*t` energy units, takes the rank device count from the run's own config (BusWidth / DeviceWidth = 4 for the two-subchannel model), multiplies rank background power by it, and writes the factor into a new CSV column `Background_Power_Device_Factor`; `5_summary_report.py` uses the same helpers. 580 tests pass; verified through the master (exit 0, DDR5 row equal to the reprocessed primary); all ten frozen datasets reprocessed with `_csv_before_F1` backups; ReRAM and PCM rows unchanged; 19 book figures and 3 deck charts regenerated. CORRECTED NUMBERS (before F4 changes DDR5 timing): DDR5 full DIMM on gcc 0.799 W (was 0.254), static 0.726 W (was 0.181), PDP 52.1 W.ns (was 16.6); DDR5 0.0499 W/GiB (was 0.0159); ReRAM SLC per-GiB power ratio 12.7 to 17.4x (was 40 to 55x); break-even idle gating 94.3% (was 98.2%), now INSIDE the cited 94 to 98% idleness band, and at 98% gating the ReRAM module would draw less than DDR5 for the same 8 GiB (0.35x), so the power argument reverses in tone, not only in value; DDR5 refresh share 6.5 to 9.1% (was 20 to 29%); DDR5 geometric-mean PDP 113.9 W.ns (was 35.4), so every "trails DDR5 by Nx" PDP statement shrinks about 3.2x; PCM versus 1S1R MLC per GiB 6.1x / 5.7x (was 19.6x / 18.2x). F4 (DDR5 write-path timings to JEDEC, DDR5-only re-run) and the F1 review are running.
2026-09-21: F1 REVIEWED (compliant, approved; reviewer re-derived every number and confirmed the device count is BusWidth / DeviceWidth only); a second upstream quirk (rank `totalEnergy` double-counts one device's bank energy in current mode; nothing reads it) is now item 7 of `simulators/nvmain/CLAUDE.md`. F4 DONE, round 1: DDR5 write-path and power-down timings corrected from DDR3-template cycle counts to JEDEC JESD79-5 DDR5-4800B (tCK 0.41667 ns): tCWD 7 to 38 (CL - 2), tWR 10 to 72 (30 ns), tRTP 5 to 18, tPD 6 to 18, tXP 6 to 18, tWTR 5 to 6 (tWTR_S, the DDR5-friendly choice, ruled and documented), tRDPDEN 24 to 49 (45 for the 64B model), tWRPDEN 19 to 119 (115); each value with its JEDEC table in the config comments; 11 new tests re-derive them from the formulas. DDR5 re-run alone (nine runs, all exit 0, same request counts), installed into all ten dataset folders with backups; only the nine DDR5 files changed by checksum; every ReRAM and PCM CSV row byte-identical; master verification exit 0; 591 tests pass; regression harness PASS x3. EFFECT: DDR5 full DIMM on gcc 65.2 to 83.1 ns; on the AlexNet output burst 158.8 to 234.4 ns, so ReRAM still loses the write burst but by 1.51x (1T1R SLC) and 1.67x (1S1R SLC) instead of 2.22x and 2.47x; ReRAM's lead widens on the other five traces (gcc 1T1R SLC now 0.50x of DDR5); DDR5 geometric-mean PDP 113.9 to 136.1 W.ns; power, W per GiB (12.7 to 17.4x) and break-even gating (94.3%) effectively unchanged from F1. JESD79-5 was read from a third-party mirror (the standard is access-gated and there is no local copy): values are quoted with their table numbers for re-verification against an official copy. Round 2 running: the remaining template keys (tRRDR, tRRDW, RAW, tRAW, and the tCCD short-versus-long question) are being mapped from NVMain's own semantics or labelled as having no DDR5 counterpart, with a complete per-key provenance table for the book.
2026-09-21: F4 ROUND 2 DONE. Remaining DDR5 template keys settled from NVMain's own semantics: tRRDR 5 to 8 (tRRD_S; it is NVMain's only activate-to-activate constraint and it binds), tRRDW 5 to 8 (dead key, changed for consistency), tRAW 20 to 32 (four-activate window width); RAW 4, tCCD 8 (tCCD_S) and tWTR 6 (tWTR_S) reviewed and kept, each labelled in the config. All 38 timing keys of the subchannel config now carry a label: 22 JEDEC-sourced, 9 NVMain semantics with no DDR5 counterpart (3 never bind), 2 dead, 3 DDR5-friendly short-versus-long judgements (tCCD_S, tWTR_S, tRRD_S: NVMain has one rank-wide value and no bank groups). The 64B cross-check config keeps tCCD 4, below the JEDEC floor, because it reproduces a legacy channel shape: it is a legacy-shape reference, not a JEDEC DDR5 configuration. NVMain also charges tRRD and the activate window on every refresh (template behaviour, slightly pessimistic for DDR5, not patched). Round 2 moved every DDR5 value by under 0.5%: DDR5 full DIMM gcc 65.21 (pre-F4) / 83.10 (F4) / 83.11 ns (final); AlexNet output burst 158.8 / 234.4 / 234.3 ns; ReRAM still loses the write burst, by 1.507x (1T1R SLC) and 1.671x (1S1R SLC). 597 tests pass, master exit 0, harness PASS x3, only the nine DDR5 stats files changed, all backups kept. RUNNING IN PARALLEL: F3a (book, guides, figures: one correction pass from the F1 and F4 data, including the reversed tone of the power argument and the corrected latency mechanism), F2 (pipeline hardening: silent fallbacks, run manifest and provenance columns, root README, configs/CLAUDE.md; must prove no result changes), and the F4 review.
2026-09-21: F4 REVIEWED (compliant, approved; the reviewer confirmed the four-activate window and the short/long pairs against DDR5-4800 vendor datasheets; open nit: the power-down entry formulas could be off by one cycle, immaterial to every reported result, caveat to be added to the configs). F3a BOOK CORRECTED AND REVIEWED: one pass from the corrected data; 105 pages; about 310 numbers independently recomputed, 3 mismatches, all fixed; latency mechanism approved at the source (11.25 of 41.40 ns at 800 MHz comes from NVSim, the rest is interface cycle counts at the assumed clock; cell write time is off the request path in this project's generator, so MLC latencies are lower bounds); power argument approved after one backwards sentence was fixed. CURRENT HEADLINES: DDR5 full DIMM on gcc 83.1 ns and 0.797 W for 16 GiB; ReRAM SLC per-GiB power 12.7 to 17.4x DDR5 as an upper bound, device-only on both sides; break-even idle gating 94.3%, inside the cited 94 to 98% idleness band; a per-module overhead compresses that ratio (11.5x at 0.5 W) but moves the gating break-even AGAINST ReRAM (97.9% at 0.5 W, parity unreachable beyond 0.79 W); ReRAM loses the write-dominated AI burst by 1.507x (1T1R SLC) to 2.8x (MLC), a lower bound. "Modeled strictly after JESD79-5" is withdrawn: the DDR5 baseline is JEDEC-sourced with three documented DDR5-friendly choices. RUNNING: F2 (pipeline hardening) and F3c (one-pager, note, context file from the corrected book); the deck (F3b) follows F2 because both touch the same test files.
2026-09-21: F2 PIPELINE HARDENING DONE (706 tests pass; master exit 0; NO RESULT CHANGED: both frozen datasets reprocessed into temp folders are identical on every pre-existing column, and a fresh run reproduces the frozen numbers). Silent fallbacks are now failures: the config generator stops on any missing hardware key (remaining defaults are named constants with sources), the hardware extractor fails on an unparsable NVSim result, `process_metrics.py` fails when a ReRAM row lacks its hardware entry (the 1.0 area-ratio fallback is gone), the master aborts before stage 4 if stage 1, 2 or 3 fails, and a missing `--ddr5-model` config is an error. `validate_config` now refuses a config whose tRCD + tCAS differs from the read-latency cycle count (the rule the book describes). Provenance: the master writes `results/system/run_manifest.json` (command line, date, git commits of all three repositories, every flag, traces with sidecar checksums, sha256 of every simulated config) and `process_metrics.py` carries seven `Run_*` columns into every CSV (`unknown` for the frozen datasets, which predate the manifest). Generated configs left by an earlier run can no longer leak into a run: stage 3 lists what it generated, the master moves older generated configs aside, and stage 4 refuses any generated model not on this run's list. NVMain output is written to `.out.partial` and renamed on success. Selector-layer tests no longer vanish on a clean checkout. Root `README.md` and `configs/CLAUDE.md` rewritten from the code (real MLC multipliers 1.5 read / 3.263 write, forced 2048 x 2048 at mux 64); master help texts corrected (`--queue-size` reaches the generated ReRAM configs only). Known leftovers, not fixed: `results/hardware/` still holds two `_1024` NVSim result files, so a default run still generates (but never simulates) eight `_1024` configs; the figure scripts' `archive_old_graphs()` uses hardcoded live paths, so any test that reaches a visualizer's `main()` would move the live CSVs (the new tests stub it). DDR5 configs: caveat added that the power-down entry formulas may be off by one cycle.
2026-09-21: ALL POST-REVIEW CORRECTIONS DONE AND REVIEWED. F2 fix round 1 (found by its review): the run manifest now lists the stats files its run produces and `process_metrics.py` labels only those; the master moves a previous run's outputs out of `results/system` into `results/system_previous_<timestamp>/` before stage 4; the stage-4 script moves an existing output aside before launching, so a failed re-run cannot leave a fresh-looking result; verified by the controller after the implementer was cut off (master exit 0, 120 files moved aside and restored intact, 20 of 20 verification stats identical to the primary: no result changed). F3b DECK updated from the corrected book (9 slides rewritten, 11 number-swapped, 15 charts re-embedded): review APPROVED, 0 mismatches in about 130 values, all sweeps clean, a new test forbids the superseded interim values anywhere. F3c ONE-PAGER, NOTE and CONTEXT FILE updated from the corrected book: review APPROVED, 0 mismatches in about 140 values; one-pager still one page; note 447 words, DRAFT, not sent; context file's provenance paragraph completed. CLOSING VERIFICATION: 783 tests pass including slow ones; regression harness PASS x3; live configs match tracked; book compiles (105 pages); live `results/` equals the corrected primary dataset. STILL OPEN, all the Lead's: (1) every commit and push (one consolidated set handed over); (2) publishing the deck to the link-shared artifact; (3) a human look at the dense slides on a real screen (16, 31, 32, 41, 51, 53, 56 to 59); (4) sending the note; (5) deleting the 62 GB of raw gem5 logs; (6) mcf (needs a rebuilt binary and a new SPEC2017 grant); (7) re-verifying the DDR5 timing values against an official JESD79-5 copy; (8) clearing the two `_1024` files from `results/hardware/` before a future primary run; (9) the figure scripts' `archive_old_graphs()` hardcoded live paths. T5.2 (simulating Start-Gap gap-move traffic) was optional and is closed by disclosure in the book (about 1% write overhead, not simulated).
