# The 47x 1T1R-vs-1S1R leakage gap is an NVSim array-organization artifact

**Date:** 2026-09-15. **Trigger:** Shahar Kvatinsky's review note 6 ("the selector's 47x leakage advantage
seems too good to be true"), re-examined while building the one-page evidence table.
**Status:** experiment complete; book, deck and one-pager NOT yet corrected (pending the Lead's choice of
array-organization rule, see "Open decision").

## Bottom line

In NVSim, the 47x leakage gap (794.7 vs 16.9 mW per chip) is produced by **array organization**, not by
the transistor-vs-selector access device:

1. NVSim assigns memristor cells **zero leakage** for any access type. Chip leakage is entirely peripheral
   circuitry (decoders, sense amplifiers, muxes, precharger), so it scales with the number of mats.
2. The two NVSim configs set different sense-amp column muxes (1T1R 32, 1S1R 256). Under 22nm LOP, Area
   optimization and a 512-bit word, this drives NVSim to **256 mats for 1T1R vs 2 for 1S1R** (128x).
3. **At identical organization, the two cells leak identically** (or within 5% at 256 mats).

The book's explanation (transistor off-current [43]/[44] vs selector HRS current [7]) describes inputs
NVSim never uses for this number.

## 1. Source-code facts (simulators/nvsim)

- `SubArray.cpp:770`: `leakage = 0; //TO-DO: cell leaks during read/write operation` in the
  MRAM/PCRAM/memristor/FBRAM branch, independent of `AccessType`.
- `SubArray.cpp:869`: `leakage += rowDecoder.leakage + bitlineMuxDecoder.leakage + senseAmpMuxLev1Decoder.leakage
  + senseAmpMuxLev2Decoder.leakage + precharger.leakage + bitlineMux.leakage + senseAmp.leakage + ...` (periphery only).
- `MemCell.cpp:141-142`: `CellArea` only sets cell height and width (`sqrt(area)`).
- `InputParameter.cpp`: among organization settings only `-ForceBank`, `-ForceMat`, `-ForceMuxSenseAmp`,
  `-ForceMuxOutputLev1`, `-ForceMuxOutputLev2` are parsed. **`-MatHeight`, `-MatWidth`, `-NumRowMat`,
  `-NumColumnMat`, `-Max/MinNumRowMat`, `-Max/MinNumColumnMat` are not parsed and are silently ignored.**
- Organization identity: active sense amps = active mats x active subarrays x (columns / mux) = WordWidth (512),
  and total bits = mats x subarrays x rows x columns = 1 Gb. Both baselines satisfy both.

## 2. Config provenance

- `configs/reram_22nm_1t1r_slc.cfg`: `-ForceMuxSenseAmp: 32` (since the 22nm tracks, commit `3580beb`).
- `configs/reram_22nm_selector_slc.cfg`: changed 32 -> `256  // Increased to maximize sense amp width` in
  commit `bbd4bec` (2026-03-22). No citation or analysis recorded; 1T1R was not changed to match.
- `simulators/nvsim/CLAUDE.md` recommends a fixed "Stability Skeleton (e.g., 128x128 Mats)". It was written
  into the configs through the unparsed `MatHeight`/`NumRowMat` keys, so it never took effect.

## 3. Method

NVSim invoked exactly as `1_run_nvsim_hardware.py` does (`simulators/nvsim/nvsim <cfg>`, cwd
`simulators/nvsim`). Every run starts from the official `.cfg`; only the cell file, `-ForceMuxSenseAmp`,
and (where forced) `-ForceBank (Total AxB, Active CxD): AxB, 1xB` with `-ForceMat: 2x2, 2x2` change.
Cell files are unmodified copies. All inputs, raw outputs and both driver scripts are in `leak47x_runs/`
(`R1`-`R6` = swap runs, `sw_*` = organization sweep). No project config or result file was touched.

## 4. Results

**Table A - baselines and swaps** (per 1 Gb chip; 1T1R write = RESET/SET latency)

| Run | Setup | Mats | Subarray | Area mm² | Leakage mW | Read ns | Write ns |
|---|---|---|---|---|---|---|---|
| R1 | 1T1R baseline (mux 32) | 256 | 8192 x 128 | 19.802 | **794.656** | 32.1 | 32.3 |
| R2 | 1S1R baseline (mux 256) | 2 | 8192 x 16384 | 2.276 | **16.907** | 52.1 | 72.9 |
| R3 | 1T1R forced to 1S1R organization | 2 | 8192 x 16384 | 10.638 | **17.009** | 107.0 | 98.2 |
| R4 | 1S1R forced to 1T1R organization | 256 | 8192 x 128 | 11.911 | **810.475** | 17.0 | 50.1 |
| R5 | 1T1R free search, mux 256 | 1 | 8192 x 32768 | 10.532 | 8.849 | 331.5 | 330.1 |
| R6 | 1S1R free search, mux 32 | 4 | 65536 x 1024 | 4.019 | 201.346 | 589.1 | 1262 |

R1 and R2 reproduce `results/hardware/*_results.txt` exactly.

**Table B - matched organization, mux 256**

| Bank | Mats | 1T1R leak mW | 1S1R leak mW | 1T1R read ns | 1S1R read ns | 1T1R area mm² | 1S1R area mm² |
|---|---|---|---|---|---|---|---|
| 1x1 | 1 | 8.849 | invalid | 331.5 | - | 10.532 | - |
| 1x2 | 2 | 17.009 | 16.907 | 107.0 | 52.1 | 10.638 | 2.276 |
| 1x4 | 4 | 33.144 | 33.144 | 51.4 | 25.7 | 10.854 | 2.455 |
| 1x8 | 8 | 52.707 | 52.707 | 37.4 | 19.4 | 11.042 | 2.652 |
| 2x8 | 16 | 55.061 | 55.061 | 31.1 | 12.9 | 11.143 | 2.697 |
| 8x32 | 256 | 259.920 | 246.839 | 32.1 | 18.0 | 13.180 | 4.524 |

**Table C - validity ladder at mux 32** (bank forced, 2x2 subarrays per mat)

| Bank | Mats | 1T1R | 1S1R leak mW / read ns |
|---|---|---|---|
| 1x1, 1x2 | 1-2 | invalid | invalid |
| 1x4 | 4 | invalid | 201.3 / 589.1 |
| 1x8 | 8 | invalid | 402.5 / 589.2 |
| 1x16 | 16 | invalid | 609.2 / 589.5 |
| 1x32 | 32 | invalid | 802.3 / 590.4 |
| 2x32 | 64 | invalid | 803.4 / 153.2 |
| 4x32 | 128 | invalid (16384-row bitlines) | 805.8 / 44.0 |
| 8x32 | 256 | **794.7 / 32.1** (first valid) | 810.5 / 17.0 |
| 16x32 | 512 | 801.2 / 25.8 | 816.7 / 10.7 |
| 32x32 | 1024 | 814.6 / 25.5 | 824.6 / 10.1 |

## 5. Findings

1. **Leakage follows organization, not cell type** (Table B): identical to three decimals at 4, 8 and 16 mats.
2. **The 128x mat gap has two causes:** the hand-set mux difference (32 vs 256), and NVSim's 1T1R validity
   limit at mux 32 (bitlines no longer than 8192 rows; with 512 active sense amps that forces 128-column
   subarrays and 256 mats). The limit's physical cause inside NVSim (bitline RC or sense margin with
   access-transistor drain capacitance) was not traced.
3. **Latency is organization-dependent too.** At matched organization NVSim reads the selector cell faster
   than 1T1R (Table B), the reverse of the book's "the selector costs 1.6x on reads" (Table 1 paragraph, §3.1.1).
4. **Die-area advantage is organization-dependent:** 1T1R/1S1R area is 4.7x at 2 mats and 2.9x at 256 mats
   (mux 256), vs 8.7x in Table 1.
5. **Subarrays were never 1024x1024.** Book §1.2 ("1024-cell bitlines") and §4.2 ("1T1R subarrays restricted
   to 1024x1024") do not match the simulated 8192-row bitlines.
6. **NVSim cannot answer the physical question.** Real cell-level leakage (off-state current of unselected
   1T1R access transistors; half-select and sneak current through selectors) is not modeled at all.

## 6. Claims affected (inventory, 2026-09-15)

- **Project_Book.typ:** Abstract ("selector's 47x leakage discipline ... decides architectural viability";
  1T1R 50.9 W infeasible); §1.3 contribution (c); Table 1 and its paragraph; §3.1.1 selector-latency
  explanation; §3.1.2 (leakage-class separation, 794.7 vs 16.9); §3.1.3 (32x PDP "because the 47x leakage
  gap"); §3.1.6 item 3; §3.2 leakage-scaling statements; §3.3 (x3); Table 7 roles; Conclusion (x3);
  Appendix A (HRS-sweep sentence, "Access-Device Leakage Model", "Bit-Cell Area"); §1.2 and §4.2 1024x1024.
- **Deck:** slides 18, 26, 50, 51 (47x wording); every slide using 50.9 W, 1.12 W or PDP ratios (27, 28, 34,
  35, 36, 39); slide 8 (selector "slower access path").
- **Shahar_Review_Evidence.typ** rows 6 and 10; `Reference_Guide.md` [43]/[44] rationale;
  `Post_Meeting_Notes_Shahar_2026-09-03.md` item 6; `Presentation_Outline.md`; `Meeting_Prep_Cheat_Sheet.md`.
- **Downstream results:** NVMain configs take leakage, latency and energy from NVSim, so Tables 2-5 and 7,
  Figures 1-27 and the endurance projections (write rates depend on latency) all inherit the organization choice.

## 7. Open decision (Lead Researcher)

Which organization rule to adopt before re-running NVSim and the NVMain matrix:
(a) one matched organization for both technologies, or (b) each technology at a literature-backed
organization of its own. A literature search on realistic subarray sizes, bitline lengths and sense-amp
mux ratios for 1T1R and 1S1R arrays is in progress (2026-09-15).
