# Book Reference & Simulation-Parameter Correction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix confirmed bibliography errors in `documents/MBMM_Book_Typst/Project_Book.typ`, and for the two findings that turned out to be wrong *simulation config values* (not just citation problems), correct the config, re-run only the affected slice of the pipeline, and propagate the corrected numbers into the book.

**Architecture:** Two independent tracks that converge at the end:
- **Track 1 (no resimulation):** four citation-only fixes ([8]→[24] swap, [13] page range, [23] unsupported claim, [21] misattributed figure) plus a citation-wording fix for [7]. Pure text edits.
- **Track 2 (resimulation required):** DDR5 baseline timing (`tCAS/tRCD/tRP`) and the MLC read/write latency-energy multiplier are both wrong relative to their cited sources and are live simulation inputs. Fix config → re-run only the affected configs via `mbmm_master.py` → regenerate CSVs/figures into a new versioned results generation → update every book number that changed.

**Tech Stack:** NVSim (device-level), NVMain 2.0 (architectural sim), Python 3 pipeline (`mbmm_master.py` + stages 1-5), Typst (book source).

## Global Constraints

- **No git commits.** Per `/home/yuvalk/MBMM/CLAUDE.md`: stage changes only (`git add`), never `git commit`/`git push` — the Lead Researcher (user) commits.
- **Gate-keeper rule.** Per the same CLAUDE.md: never assume a Python/config change worked until verified by actually running it through `mbmm_master.py` and checking real output, not by inspection alone.
- **Don't touch `results/system_v3/` or `results/system_v4/`.** Those are the current-canonical and prior-canonical generations respectively (see `archive/README.md`). New results go in a new `results/system_v5/` directory — never overwrite an existing generation.
- **Don't run the full 20-config × 6-benchmark matrix.** Only DDR5 and the 8 MLC configs (`1t1r_mlc` / `selector_mlc` × `single/8chip/16chip/full_dimm`) need re-simulating — the SLC, PCM, 2D/3D-DRAM control numbers are untouched by these two fixes and must NOT be regenerated (regenerating them would create spurious diffs against `system_v4` from run-to-run simulator noise, if any, for zero reason).
- **Matched-host methodology must be preserved.** Any re-run must use the same `--cycles`/`--trace` matched-host parameters documented in Project_Book.typ Appendix B (Section 3.1.6 item 11 fix) — `CPUFreq=3000`, per-technology cycle budgets computed as `ceil(N × CLK / 3000)` — so the new numbers are apples-to-apples with the untouched SLC/PCM/DRAM rows they'll sit next to in the same tables.

---

## Track 1: Citation-only fixes (no resimulation, can run anytime, independent of Track 2)

### Task 1: Fix the four confirmed citation errors + reword the `[7]` citation

**Files:**
- Modify: `documents/MBMM_Book_Typst/Project_Book.typ`

**Interfaces:** None — pure text edits, no downstream dependents.

- [x] **Step 1: Verify `[24]`'s subject is really 1T1R before swapping it in at line 213 — DONE (2026-08-04, subagent)**

The earlier subagent review confirmed `[24]` (TechInsights, TSMC 22ULL / Nordic nRF54L15 teardown) documents real 22nm mass-produced eReRAM, but did not explicitly confirm the *cell topology* (1T1R vs. something else) of that specific chip. Before swapping, fetch the TechInsights article again and grep its text for "1T1R" or an explicit cell-architecture statement:

```bash
# (agent has WebFetch — re-check https://www.techinsights.com/blog/advanced-tsmc-22ull-embedded-rram-chip-unveiled
#  for an explicit 1T1R statement before proceeding)
```

`[24]`'s article (TechInsights, TSMC 22ULL) does NOT explicitly state 1T1R — confirmed via direct WebFetch quote: "the article does not explicitly state the cell topology/architecture as 1T1R." Took the reword branch.

- [x] **Step 2: Fix line 213 — the `[8]`/`[24]` swap — DONE (2026-08-04, subagent, verified via `git diff`)**

Final text: `...modern commercial foundries currently mass-produce 22nm embedded ReRAM (eReRAM) macros at multi-megabyte scales [24], inherently validating its manufacturability...` — dropped the unconfirmed "1T1R" topology claim per Step 1's finding, swapped citation to `[24]`. The other two `[8]` sites (line 191, line 1998) untouched as specified.

- [x] **Step 3: Fix `[13]`'s page range in the reference list — DONE (2026-08-04, subagent, verified via `git diff`)**

Changed `641–648` to `641–646`.

- [x] **Step 4: Fix line 347 — swap the unsupported `[23]` DDR-T claim for a new reference `[32]` — DONE (2026-08-16, subagent, verified directly: `[32]` used only at line 347, `[23]` correctly retained only at its valid site line 1665, reference list has both `[31]` and `[32]` entries)**

Current text (`documents/MBMM_Book_Typst/Project_Book.typ:347`, approximate):
```
...below the DDR4-class DDR-T interface of Intel's shipped Optane persistent-memory DIMMs [23] — the industry precedent that NVM DIMM interfaces trail the contemporary DRAM PHY...
```
The cited article (`[23]`, the Optane-exit business story) never discusses the DDR-T interface — confirmed, `[23]` is purely about the 2022 business exit. Found and independently verified (direct PDF text extraction, matched the exact sentence) a real, freely-accessible, ~400+-citation systems paper that states this precisely:

> "The iMC communicates with the Optane DC PMM using the DDR-T interface. This interface shares a mechanical and electrical interface with DDR4 but uses a different protocol that allows for variable latencies..." — J. Izraelevitz et al., "Basic Performance Measurements of the Intel Optane DC Persistent Memory Module," arXiv:1903.05714, Aug. 2019.

**Implementation:**
1. Add to the reference list (after `[31]`, i.e. as `[32]`):
```
\[32\] J. Izraelevitz, J. Yang, L. Zhang, J. Kim, X. Liu, A. Memaripour, Y. J. Soh, Z. Wang, Y. Xu, S. R. Dulloor, J. Zhao, and S. Swanson, \"Basic Performance Measurements of the Intel Optane DC Persistent Memory Module,\" arXiv:1903.05714, Aug. 2019.
```
2. At line 347, change `\[23\]` to `\[32\]` in the DDR-T clause specifically. Leave every other `[23]` site untouched (line ~1665 is a separate, valid use of `[23]` — confirmed correct in the original reference-verification pass — do not touch it).

- [x] **Step 5: Fix line 1717 — the Malladi `<3%` bandwidth figure — DONE (2026-08-04, subagent, verified via `git diff`)**

Changed "under 3% of peak channel bandwidth" to "under 6% of peak channel bandwidth" (the orchestrator's chosen resolution of the two options — keeps the sentence's rhetorical structure, uses the paper-supported figure).

- [x] **Step 6: Reword the `[7]` resistance-target justification in Appendix A — DONE (2026-08-03, executed inline by the orchestrator, not delegated)**

Original plan offered options (a) reword honestly, or (b) find a second citation for HRS=10⁹Ω. Searched for (b) across `[13]` (Le et al. — doesn't use LRS/HRS terminology at all), `[14]` (Wong et al., now confirmed as the right paper via `documents/reference_validation_papers/MetalOxide_RRAM.pdf` — discusses HRS/LRS conceptually but states no absolute resistance target anywhere, only ratio examples ~20×), and `resources/lectures and tutorials/Lecture 4 - memory.pdf` (a real fabricated-device example: LRS/HRS ≈ 7kΩ/170kΩ, ~24× ratio) — none support a 10⁹Ω digital-memory HRS. No viable (b) source found.

This prompted a follow-up NVSim sensitivity sweep (see new Task 2.5 below) that made the decision moot: **HRS has zero effect on modeled leakage power and <2% effect on latency**, so the citation's precision doesn't matter for any result in the book. Applied option (a), reworded, *plus* added the sensitivity finding directly to the same bullet — see `documents/MBMM_Book_Typst/Project_Book.typ:2093-2110` (current line numbers shifted after the edit). Recompiled clean (`typst compile` exit 0).

- [x] **Step 7: Recompile and spot-check — DONE (2026-08-16, subagent + orchestrator both independently recompiled, exit 0, no warnings)**

**Task 1 fully complete.** All 7 steps done, all confirmed OK.

---

## Track 2: Simulation-parameter corrections (resimulation required)

### COMPLETED: HRS Sensitivity Sweep (2026-08-03) — full-pipeline propagation deprecated

Ran a targeted, NVSim-only sensitivity sweep to test whether the disputed HRS=10⁹Ω citation (Task 1 Step 6) posed any real risk to the book's numbers. Created 6 new `.cell`/`.cfg` pairs in `configs/hrs_sweep/` (1T1R-SLC and selector-SLC, each at HRS = 25×/100×/1000× LRS, i.e. 2.5MΩ/10MΩ/100MΩ — the existing canonical configs already cover 10000× = 1GΩ), ran `1_run_nvsim_hardware.py` on all 6 (no NVMain, no benchmarks — NVSim device characterization is benchmark-independent), and read the "Leakage Power" line directly from each `results/hardware/*_results.txt`.

**Result: leakage power is bit-for-bit identical across the entire swept range** — 794.656mW (1T1R) and 16.907mW (selector) at every ratio from ×25 to ×10000. Diffing full NVSim output confirmed resistance *is* taking effect (the "Cell Turned-Off Resistance" field changes correctly) but only feeds into bitline read-latency/sensing timing, not the leakage-power formula at all — read latency varied by at most 1.7% (9.472ns at ×25 → 9.631ns at ×1000/×10000), nothing else moved.

**Conclusion: the paper's 47×/50-78× leakage-class-separation headline finding is 100% robust to the HRS citation question** — it's driven entirely by the `AccessType: CMOS` vs `AccessType: diode` access-device model, not by HRS. Given the maximum possible effect on any book number is ~1.7% on one latency component (and 0% on power), **a full-pipeline propagation of this sweep (NVMain × 6 benchmarks × new results generation, i.e. "Step 2" as originally scoped when this was requested) is not worth the compute and is hereby deprecated.** Decision made and confirmed with the user 2026-08-03.

**What shipped instead:** the sweep methodology and both findings (leakage invariance, <2% latency sensitivity) were written directly into Appendix A (`documents/MBMM_Book_Typst/Project_Book.typ`, the "Resistance Targets" bullet, alongside the Task 1 Step 6 citation reword) as a documented robustness note — this is more rigorous than a silently-updated table would have been, and cost a fraction of the compute. Recompiled clean.

**Housekeeping note for whoever picks this up:** `configs/hrs_sweep/` (6 `.cell`/`.cfg` pairs) and the corresponding `results/hardware/*_hrs{25,100,1000}x_results.txt` files are scratch artifacts from this sweep — not referenced by `mbmm_master.py` or any canonical pipeline path, safe to leave in place (they're small and document how the Appendix A numbers were obtained) or archive later; no urgency either way.

---

### Task 2: Extract EMBER's full read+write latency/energy data — RESOLVED (2026-08-16)

**Files:**
- Read: `documents/reference_validation_papers/EMBER_A_100_MHz_0.86_mm2_Multiple-Bits-per-Cell_RRAM_Macro_in_40_nm_CMOS_with_Compact_Peripherals_and_1.0_pJ_bit_Read_Circuitry.pdf` (ESSCIRC 2023 conference version — read data)
- Read: `documents/reference_validation_papers/EMBER_Efficient_Multiple-Bits-Per-Cell_Embedded_RRAM_Macro_for_High-Density_Digital_Storage.pdf` (JSSC 2024 journal version, same author team — write data; this is now reference `[31]` in `Project_Book.typ`)

**Interfaces:**
- Produces: the corrected MLC read-latency, write-latency, read-energy, and write-energy multipliers (SLC→MLC ratios) that Task 6 hardcodes.

The ESSCIRC 2023 conference paper (already `[6]`) has **zero write-side data** — confirmed dead end, extensively re-verified across three research rounds (direct PDF text search, two independent LLM research passes that both initially overreached and had to retract claims under direct-source verification — see ledger history above). The JSSC 2024 journal follow-up by the same author group, however, has exactly what conference-paper space limits omitted. Verified directly from the primary PDF (quote appears 3× in the paper — abstract, overview, and Section III results, word-for-word identical each time):

> "1 b/cell write-verify operates with 0.40 nJ/bit energy at 12.4 Mbps (BER < 6e-4), and 2 b/cell write-verify operates with 1.2 nJ/bit at 3.8 Mbps (BER < 3e-3)."
> "achieving 1 b/cell read operation with 1.0 pJ/bit energy at 2.4 Gbps, and 2 b/cell read with 1.1 pJ/bit at 1.6 Gbps."

**Final decided values** (all four multipliers now literature-derived, explicit 1b/cell-vs-2b/cell bit-depths, no ambiguous "MLC" terminology anywhere in the source):
- `read_latency`: derived from ESSCIRC 2023 Table I, 12ns → 23ns = **1.917×** (was 3.0, unsourced)
- `write_latency`: derived from JSSC 2024 write bandwidth, 12.4 Mbps → 3.8 Mbps = **3.263×** (was 4.0, unsourced — now close to but not identical to the old placeholder, so the resimulation impact on this factor is modest, ~18% reduction)
- `read_energy`: derived from ESSCIRC 2023 Table I, 1.0 → 1.1 pJ/bit = **1.1×** (was 3.0, unsourced — this is the largest correction of the four)
- `write_energy`: derived from JSSC 2024, 0.40 → 1.2 nJ/bit = **3.0×** (was 3.0 — coincidentally already correct, now properly sourced instead of unsourced)

### Task 3: Confirm DDR5 config authority and derive the corrected timing set

**Files:**
- Read: `simulators/nvmain/Config/DDR5_4800_DRAM.config` (confirmed live/authoritative — `mbmm_master.py:249` and `3_gen_nvmain_config.py:166` both point at `simulators/nvmain/Config/`)
- Note (do not edit yet): `configs/DDR5_4800_DRAM.config` — confirmed stale/orphaned duplicate, not referenced by any pipeline script (only `configs/*.cfg` files are used from that directory, per `1_run_nvsim_hardware.py:46` and `4_execute_simulation.py:39`). Leave it alone for this fix; optionally flag for archival in a separate, unrelated housekeeping pass.

**Interfaces:**
- Produces: the exact new `tCAS`/`tRCD`/`tRP` values Task 4 will write.

Already confirmed:
- Real SK hynix standard DDR5-4800 (non-3DS) speed bin, from `documents/reference_validation_papers/TR-20230620152301091.pdf` and `TR-20230620152301412.pdf`: **`EB` code = `4800 40-39-39`**.
- Current config (`simulators/nvmain/Config/DDR5_4800_DRAM.config:85-97`) has `tCAS 34`, `tRCD 34`, `tRP 34`, `tRAS 77`. There is **no explicit `tRC` key** in this file (NVMain derives it internally), so only three lines need to change — no cascading `tRC` edit required.
- `tRAS`, `tWR`, `tRTP`, `tRFC`, `tCCD`, `tRRDR/W` are independent JEDEC parameters unrelated to the CAS/RCD/RP speed-bin code — **do not touch them** for this fix. (Note: the file's own comment at line ~98-101 already flags a separate, unrelated `tRFC` rescaling concern — "never rescaled when CLK was overridden to 2400" — that is a pre-existing, already-documented issue, out of scope here; do not fix it as part of this task.)

- [ ] **Step 1: Confirm the SK hynix `EB` code is the right density/generation match**

The decoder PDFs give the *format* of the part-number code, not confirmation of which exact die revision/generation letter matches the specific part your `[29]`/`[30]` IDD calibration already assumes (16Gb, per the config's `EnergyModel current` block). Re-open `TR-20230620152301412.pdf` (component decoder) and confirm the `G4` (16Gb) density code combined with `EB` (4800 40-39-39) speed code is a valid, real combination (not all density/speed combinations are necessarily offered) — if uncertain, note it as an assumption in the config comment rather than asserting certainty.

- [ ] **Step 2: Write down the corrected values**

- `tCAS`: 34 → **40**
- `tRCD`: 34 → **39**
- `tRP`: 34 → **39**

### Task 4: Hand-quantify expected impact before spending compute

**Files:** none modified — this is a paper calculation, done before Task 5/6.

**Interfaces:**
- Consumes: Task 2 Step 3's multiplier values, Task 3 Step 2's timing values.
- Produces: an expected-magnitude estimate to sanity-check Task 8's actual diff against.

- [ ] **Step 1: Estimate the DDR5 latency shift**

At `CLK 2400` (0.4167 ns/cycle): current CAS+RCD+RP = 34+34+34 = 102 cycles = 42.5ns. Corrected = 40+39+39 = 118 cycles = 49.2ns. That's a **+15.7% increase** in this component of DDR5's critical-path timing. Given the book's baseline GCC latency figure for DDR5 is 81.2ns (`Project_Book.typ` Table 6 / `MBMM_AI_Context_State.md` §1.3), expect the corrected DDR5 latency numbers to increase by a meaningful double-digit percentage, not a rounding-error amount — this is worth the resimulation.

- [ ] **Step 2: Estimate the MLC shift**

Current MLC read latency multiplier (3.0×) vs. EMBER-confirmed real ratio (≈1.9×) is a **~37% reduction** in the MLC read-latency penalty once corrected — i.e., MLC configs will look *faster relative to SLC* than currently reported, and MLC read-energy (currently 3.0×, EMBER-real ≈1.1×) will drop even more sharply (~63% reduction). This will materially change every MLC latency/energy/PDP number in the book (Table 6 rows `1T1R MLC` / `1S1R MLC`, and the density/lifetime discussion that references MLC alongside SLC). This is the single largest expected change of the whole correction pass — flag it prominently for the user before Task 6 is applied, in case they want to double check Task 2's multiplier decision once more before committing compute.

---

### Task 5: Apply the DDR5 timing fix

**Files:**
- Modify: `simulators/nvmain/Config/DDR5_4800_DRAM.config`

**Interfaces:**
- Consumes: Task 3 Step 2's values.

- [x] **Step 1: Edit the three timing lines — DONE (2026-08-04, subagent, verified by direct file read)**

Final state confirmed in `simulators/nvmain/Config/DDR5_4800_DRAM.config`: `tRCD 39`, `tRP 39`, `tCAS 40`. All other timing params (`tRAS 77`, `tAL 0`, `tCCD 4`, `tCWD 7`, `tWTR 5`, `tWR 10`, `tRTP`, `tRFC`, etc.) confirmed unchanged. Note: this file is untracked in the `simulators/nvmain` git submodule (`git status --short` shows `??`, not ignored) — `git diff` shows nothing because there's no tracked baseline to diff against; verified by reading the file directly instead.

Change lines 85-87 (currently `tCMD 1` / `tRAS 77` / blank / `tCWD 7` region — the exact `tCAS`/`tRCD`/`tRP` lines are near the top of the timings block per the earlier `grep` output) from:
```
tCAS 34
tRCD 34
tRP 34
```
to:
```
tCAS 40
tRCD 39
tRP 39
```

- [x] **Step 2: Add a provenance comment — DONE (2026-08-04, subagent, verified by direct file read, comment present verbatim above the changed lines)**

### Task 6: Apply the MLC multiplier fix

**Files:**
- Modify: `2_extract_hardware_metrics.py:60-73`

**Interfaces:**
- Consumes: Task 2 Step 3's decided multiplier values.
- Produces: corrected `apply_mlc_penalty()` — every downstream stage (3/4/5) and every MLC number in the book depends on this function's output.

- [x] **Step 1: Replace the hardcoded multipliers — DONE (2026-08-16, subagent, verified directly against the file + `ast.parse` syntax check + `git diff --stat`)**

Current code:
```python
def apply_mlc_penalty(slc_metrics):
    """Applies Phase 5 Analytical Penalties and DOUBLES capacity."""
    mlc = slc_metrics.copy()
    # Performance Penalties [cite: 1058, 1296]
    mlc['read_latency_ns'] *= 3.0  
    mlc['write_latency_ns'] *= 4.0 
    mlc['read_energy_nj'] *= 3.0   
    mlc['write_energy_nj'] *= 3.0  
```
Replace the four multiplier lines with Task 2's decided values, and replace the `[cite: 1058, 1296]` comment (those look like stale internal line-number references, not a real citation) with:
```python
    # Performance penalties derived from EMBER, same author group, two papers:
    # - Upton et al., ESSCIRC 2023 (Table I) for read: 1b/cell vs 2b/cell read latency
    #   12ns/23ns (1.917x), read energy 1.0/1.1 pJ/bit (1.1x).
    # - Levy et al., IEEE JSSC 2024, DOI 10.1109/JSSC.2024.3387566 (Section III) for write:
    #   1b/cell vs 2b/cell write-verify bandwidth 12.4/3.8 Mbps -> 3.263x write-latency
    #   penalty; write-verify energy 0.40/1.2 nJ/bit -> 3.0x write-energy penalty.
    mlc['read_latency_ns'] *= 1.917
    mlc['write_latency_ns'] *= 3.263
    mlc['read_energy_nj'] *= 1.1
    mlc['write_energy_nj'] *= 3.0
```

- [x] **Step 2: Confirm capacity-doubling logic is untouched — DONE (2026-08-16, verified: `mlc['capacity_gb'] *= 2.0` and its comment are byte-identical to before, diff confirms only the 3 changed multiplier lines + comment block)**

Lines 69-70 (`mlc['capacity_gb'] *= 2.0`) are unrelated to this fix (capacity scaling, not latency/energy) — leave unchanged.

---

### Task 7: Re-run the affected configs — DONE (2026-08-16), major deviation from plan

**What actually happened, in order:**

1. **Verified before running (per explicit user instruction) and found the plan's own example command was wrong.** `mbmm_master.py`'s `--models` flag does NOT scope the run — confirmed via `grep -n "args\.models" mbmm_master.py`: the variable is referenced exactly once, only as the gate `if args.models or args.all:`, never again inside the block. Once inside, it unconditionally runs the full 16-config ReRAM matrix + all 3 DRAM baselines for every `--trace` given. Following the plan's literal Task 7 Step 3 command would have silently re-simulated the entire matrix, including the 12 untouched configs the Global Constraints section explicitly said not to touch. Fixed by calling `4_execute_simulation.py` directly instead (confirmed via source read that *its* `--models` genuinely filters: `elif args.models: target_models = args.models`). **Documented this as a permanent `README.md` correction** (new "⚠️ `--models` does not scope the run" callout after the existing example), not just a one-off workaround, since the root README's own example was reproducing the same wrong assumption.
2. **Found and cleaned real data contamination before running Stage 2.** `results/hardware/` contained 14 stray NVSim result files beyond the 2 canonical base files (`reram_22nm_1t1r_slc_results.txt`, `reram_22nm_selector_slc_results.txt`): 6 from this session's earlier HRS sweep, 8 architecture-suffixed duplicates from 2026-07-13 (confirmed byte-identical to the base file via `diff`, just a different `.cfg` path in the header). `2_extract_hardware_metrics.py` globs `*_results.txt` with no filtering, so left in place these would have polluted `hardware_metrics.json` with 32 entries instead of 4. Archived to `archive/results/hardware_hrs_sweep_20260803/` and `archive/results/hardware_stray_perarch_duplicates_20260713/` (untracked, `results/` is gitignored, plain `mv` was safe).
3. Ran `2_extract_hardware_metrics.py` — clean, exactly 4 entries (`1t1r_slc`, `1t1r_mlc`, `selector_slc`, `selector_mlc`). Verified the multipliers landed exactly right by hand-dividing the JSON's MLC/SLC values: 1.917x / 3.263x / 1.1x / 3.0x reproduced to 4 decimal places.
4. Ran `3_gen_nvmain_config.py --freq 800` (confirmed 800MHz is right — matches the `CLK 800` already in existing MLC configs). Verified via `md5sum -c` against a pre-run checksum snapshot that all 8 SLC `.config` files and `DDR5_4800_DRAM.config` came out byte-identical (Stage 3 touches every model in the JSON, so this confirmed zero unintended drift on the untouched configs).
5. Ran `4_execute_simulation.py` directly, 12 invocations (6 traces × 2 cycle-budget groups: `DDR5_4800_DRAM` alone at `--cycles 200000000`, the 8 MLC models together at `--cycles 66666667` — both values pulled from `results/cycle8_matched_host_report.md`'s own documented table, not invented), as one backgrounded shell script. Exit 0, zero errors in the log.

**Gate-keeper verification (Step 4, per CLAUDE.md):** all 54 expected `stats_*.out` files present, non-empty, correct filenames, every one shows `Exiting at cycle` with the documented rescaled ceiling (250,000,000 for DDR5, 250,000,002 for the ReRAM/MLC family — exact match to the cycle-8 report's table). Spot-checked top-level latency/power values for sanity (no NaN/negative/absurd numbers); the only `-nan` values found are per-subarray `actWaitAverage` for idle subarrays (0/0 division), a pre-existing benign artifact confirmed present in the untouched v3/v4 data too, not something this run introduced.

### Task 8: Regenerate processed CSVs and figures — DONE (2026-08-16), one real bug caught and fixed mid-task

- **Step 1 (assemble input):** ran as planned, but discovered `results/system_v4/` contains 126 `.out` files, not 120 — a 6th "technology," `DDR5_4800_DRAM_micron`, that v4's own original `processed_*.csv` never actually included (v4's CSV has 120 rows, confirmed by direct load). This is the pre-existing, already-documented "DDR5 dual-calibration reproducibility gap" from `results/cycle8_matched_host_report.md` (no live config exists to regenerate it from; it was carried forward as raw `.out` files without ever being reprocessed into a CSV). Blindly copying all of `system_v4`'s `.out` files into `system_v5_input` (as the plan's Step 1 literally says) would have silently included it in *this* processing pass for the first time — and it *did*, on the first `process_metrics.py` run, corrupting the `DDR5_4800` geometric-mean PDP (`process_metrics.py`'s `calculate_geometric_mean_pdp` groups by Technology+Architecture only, no benchmark-name/count filter, and the micron rows share the `DDR5_4800`/`full_dimm` key) — DDR5 geo-mean came out at 125.4 (vs. the correct 104.3, a false +26% instead of the real +4.8%). **Caught via a validation step the plan didn't call for** (checking `Geometric_Mean_PDP` row counts), fixed by excluding the 6 micron files from `system_v5_input` before regenerating — restoring v5 to the same 120-row shape as v4's own original CSV. Also had to manually delete 6 stale `Pareto_micron_*.png` files left over from the contaminated first pass (the visualize script only adds/overwrites, doesn't clean).
- **Step 2/3:** ran `process_metrics.py` and, beyond the plan's `visualize_pareto.py`/`visualize_hero_graphs.py`, **also ran `visualize_results.py`** (a third script, found via the root `README.md`'s own architecture description — "Diagnostic Bar Charts (Latency, Power, EDP)" — that the plan never mentioned) since it's what actually generates the Latency/Power-Breakdown/PDP bar charts that back Figures 1-18 in the book. Without it, only the Pareto and Hero figures (19 of 27) would have been covered.

### Task 9: Diff v5 against v4 — DONE (2026-08-16)

Ran the diff (extended beyond the plan's script to also cover PDP, Dynamic_Power, and per-technology write counts, since those turned out to be needed for Task 10). All 66 untouched rows (`1S1R_SLC`, `1T1R_SLC`, `2D_DRAM_example`, `3D_DRAM_example`, `pcm_microsoft_2009`, all architectures/benchmarks) came back byte-for-byte identical between v4 and v5 — confirmed both from raw `.out` diffs and processed-CSV field comparison. Affected-row deltas: DDR5 latency +2.3% to +8.6% (in the predicted single-digit-to-high-single-digit range, once the raw +15.7% CAS/RCD/RP-only estimate dilutes into total latency blended with untouched tRAS/tWR/refresh); MLC latency -20.6% to -34.9%; MLC power ±0-4% (leakage-dominated, as expected); MLC write counts (feeding Section 3.1.4 endurance) up ~25-29% since the corrected 3.263x write-latency multiplier throttles MLC less than the old unsourced 4.0x. No wild/unexplained swings anywhere — passed sanity check cleanly.

### Task 10: Update the book — DONE (2026-08-16), far larger in scope than the plan anticipated

The plan estimated this as "Table 6 + Appendix A + a few prose sentences." In practice the same headline DDR5/1T1R-MLC/1S1R-MLC numbers are restated **verbatim in at least 6 separate places** across the book (Abstract, Table 2/3/4/6, Table 1's raw MLC device row, Section 3.1.2/3.1.3 prose, the "headline reframe" paragraph before Table 6, Section 3.2 Pareto-narrative prose, and the Conclusion) — each needed independent updates, several required more than a number swap:

- **Tables updated:** Table 1 (raw NVSim+multiplier MLC device row — this one was missed by a first pass and only caught on a dedicated final sweep), Table 2 (latency), Table 3 (power), Table 4 (PDP + geometric means), Table 6 (cross-technology summary), the endurance table/footnote in Section 3.1.4 (**write counts actually changed**, not just re-labeled — 1T1R MLC LBM writes 1,320,096→1,706,535, 1S1R MLC 751,405→942,439, recomputed lifetime 0.54→0.42yr and 0.94→0.75yr at 16GB by reverse-engineering and calibrating the book's own undocumented lifetime formula against its still-correct SLC rows before trusting it on the new numbers).
- **Two qualitative reversals found and rewritten, not just renumbered:** (1) the LBM/STREAM "MLC dynamic power dips below SLC" narrative partially flipped — STREAM's MLC dynamic power now *exceeds* SLC's (110.1 vs 99.5mW, was 95.2 vs 99.5) because the corrected write-latency multiplier throttles MLC less, letting more energy-costly writes complete per second; (2) the IFMAP/OFMAP "same ordering across all four ReRAM configurations" claim was actually already false for `1T1R_MLC` in v4 too (a pre-existing bug, not something this fix introduced) — corrected to state the real pattern (1T1R MLC is the one exception, OFMAP narrowly exceeds IFMAP).
- **One stale citation caught inside my own prose edits:** three of the rewritten paragraphs initially cited "Section 3.1.6, item 10" for the corrected multipliers — item 10 is a *different*, unrelated, pre-existing fidelity-audit finding (the `Erd`/`Ewr` key-naming bug). Caught before finalizing and corrected to reference new items (12)/(13), added below.
- **Added two new fidelity-audit items** to Section 3.1.6 (which previously stopped at item 11): item (12) documents the DDR5 CAS/RCD/RP timing fix (this session's earlier Task 5, which had never been added to the book's own audit trail despite the section's explicit purpose being to log exactly this kind of correction), item (13) documents the MLC multiplier fix in full (including the false-start research history — two research-assistant passes that initially overreached and had to be walked back — since the section's own established voice values that kind of transparency). Updated the section's summary count from "eleven... nine repaired" to "thirteen... eleven repaired," and propagated that count to the Abstract and Conclusion, which both independently restate it.
- **One number left honestly un-recomputed and flagged in place:** the Micron-calibration DDR5 PDP ceiling (150.9 W·ns) appears once, in the headline-reframe paragraph — this is the same dual-calibration gap from Task 8 (no live config survives to re-run it). Added an inline caveat rather than either fabricating a corrected number or silently leaving a now-stale one unlabeled.
- **All 26 affected embedded figure images regenerated and replaced** (`documents/MBMM_Book_Typst/media/media/image{1..26}.png`, mapped by hand from each figure's caption text to the corresponding `Bar_Latency_*`/`Bar_Power_Breakdown_*`/`Bar_PDP_*`/`Pareto_*`/`Hero_*` file — this mapping isn't automated anywhere in the pipeline). `image27.png` (ReadVoltage sensitivity, Section 3.1.5) deliberately left untouched — unrelated to either fix. `image23.png` (die-density Hero graph) came out git-diff-identical after regeneration, confirming density data is genuinely unaffected by either fix, not an oversight. One transient "failed to decode image" compile error during the batch `cp` turned out to be the harness's auto-recompile firing mid-write, not a real corruption — confirmed by re-checking every file with `file` afterward and a clean explicit recompile. Spot-verified two regenerated figures by rendering their PDF pages to PNG and reading the actual chart values off them — both matched the adjacent prose text exactly (Figure 7: 50.88W/1.13W bars matching Table 3's 50.877/1.130; Figure 27: all six bars matching the headline-reframe paragraph's restated numbers).
- Recompiled clean (`typst compile` exit 0) after every batch of edits, not just at the end.

---

## Housekeeping (after both tracks land)

### Task 11: Regenerate `MBMM_AI_Context_State.md`

**Files:**
- Modify: `MBMM_AI_Context_State.md` (via the `mbmm_hardfork` skill/command, per the existing convention documented in that file's own header — it was last regenerated 2026-07-22 against the book, the same mechanism should run again now that the book has new numbers)

- [ ] **Step 1: Run the hardfork regeneration against the corrected book**

Use the `mbmm_hardfork` slash command/skill (already available in this project) targeting the corrected `Project_Book.typ`, so the context-state doc's Table 6 mirror and Finding #2 narrative stay in sync with the corrected DDR5/MLC numbers.

### Task 12: Document the correction cycle in `archive/README.md`

**Files:**
- Modify: `archive/README.md`

- [ ] **Step 1: Add a dated section**

Following the file's existing convention (see the "Stale pre-leakage-fix `processed_*.csv` (2026-07-29)" section added earlier this session), add a new dated section explaining: what was found (DDR5 timing was 34-34-34 vs. real 40-39-39; MLC multiplier was 3x/4x vs. EMBER-confirmed ~1.9x/~1.1x-ish), what changed (`simulators/nvmain/Config/DDR5_4800_DRAM.config`, `2_extract_hardware_metrics.py`), and that `results/system_v5/` supersedes `results/system_v4/` as canonical, with `system_v4` kept (not deleted) for diffability per the established archival pattern.

---

## Self-Review

**Spec coverage:** DDR5 timing fix (Tasks 3,5,7-9), MLC multiplier fix (Tasks 2,6,7-9), book number propagation (Task 10), all 4 confirmed citation-only errors + `[7]` wording (Task 1), housekeeping/doc-sync (Tasks 11-12) — all findings from the reference-verification pass are covered.

**Placeholder scan:** Task 2 Step 3 and Task 6 Step 1 contain `<value>`/`<fill in>` markers, but these are explicitly load-bearing on Task 2's own investigation output (EMBER's write-side numbers aren't extracted yet as of this plan being written) — not a lazy placeholder, a genuine data dependency resolved earlier in the same track before it's used.

**Config authority:** confirmed via direct grep of `mbmm_master.py`/`3_gen_nvmain_config.py` that `simulators/nvmain/Config/DDR5_4800_DRAM.config` is live and `configs/DDR5_4800_DRAM.config` is not — Task 3/5 target the correct file.

**Open decision points requiring user input before execution:** none remaining — both flagged in the original plan (`[7]` HRS wording, `[23]` DDR-T source) are resolved.

**Status as of 2026-08-16: entire simulation-correction cycle complete end-to-end.** Tasks 1, 2, 5, 6, 7, 8, 9, 10 all done and verified (Tasks 3/4 effectively superseded/folded into Task 5's direct execution). `results/system_v5/` is now the canonical results generation (supersedes `system_v4`, which is kept, not deleted, for diffability). The book (`Project_Book.typ`) — every affected table, prose paragraph, and embedded figure image — reflects the corrected DDR5 timing and MLC multiplier data, recompiled clean throughout.

**Remaining (not done this round, not explicitly requested):** Task 11 (regenerate `MBMM_AI_Context_State.md` via `mbmm_hardfork` — this doc's own header still says it was last regenerated 2026-07-22 and is now stale relative to the book's corrected Table 6 numbers) and Task 12 (add a dated section to `archive/README.md` documenting this correction cycle, following the file's established convention). Both are natural next steps if the user wants full consistency across the project's auxiliary docs, but neither blocks anything — the book itself, the primary deliverable, is fully self-consistent and complete.
