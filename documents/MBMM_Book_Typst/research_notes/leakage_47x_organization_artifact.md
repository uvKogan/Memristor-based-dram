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

## 8. Literature on array organization (2026-09-15)

Only three sources were read in full: Xu et al. HPCA 2015, Shevgoor et al. ICCD 2015, and NVMExplorer.
The NVSim TCAD 2012 paper and the Intel and TSMC macro papers were paywalled. Everything else comes
from abstracts or secondary reporting, as marked below.

| Parameter | Literature value | Source | Confidence |
|---|---|---|---|
| 1T1R cells per local bitline | about 2,048 (tile of 8,192+256 bitlines x 2,048 wordlines) | Fackenthal, ISSCC 2014 [33], figures via EE Times 2014-03-04 | Secondary |
| 1T1R bitlines per sense amp | about 16 (512+16 sensed cells per tile, derived) | same | Secondary, derived |
| 1T1R bitline length | 256-4,096 cells modeled at 22nm FDSOI; leakage accumulation dominates above a few hundred kOhm Ron | Chen and Indiveri, arXiv:2410.20560 (2024) | Primary, preprint |
| 1S1R mat size meeting DRAM area and power | 256x256 to 1024x1024 (swept 128-1024, selector nonlinearity 3000) | Xu et al., HPCA 2015, Sec. 4.3 | Primary |
| 1S1R bitlines per sense amp | 16-256 (4/8/16 bits per mat, sense amps shared by adjacent mats); 256 only at the 1024x1024, 4-bit corner | same, derived | Primary, derived |
| 1S1R crossbar size in architecture study | 16x16 to 256x256, 128x128 baseline | Shevgoor et al., ICCD 2015 | Primary |
| How NVSim-based studies compare technologies | Iso-capacity, each technology optimized for a stated target; this yields different internal organizations | Pentecost et al., NVMExplorer, arXiv:2109.01188 | Primary |

**Current choices vs literature.**
- 1S1R 8192 x 16384 subarray: no support; 8-16x beyond Xu's largest DRAM-competitive mat.
- 1T1R 8192-row bitlines: no support; 4x Fackenthal's 2,048 and 2x the longest bitline Chen and Indiveri modeled.
- 1T1R mux 32: plausible; the nearest evidence (about 16, secondary) is lower.
- 1S1R mux 256: only a derived corner of Xu's space (1024 bitlines), never at 8192+ rows. The config
  comment "maximize sense amp width" has no source.
- Book "1024x1024": supported for crossbars (Xu), but never simulated. No source found for 1024x1024 as a 1T1R standard.

**Selector nonlinearity in this project (checked in `configs/reram_22nm_selector_slc.cell`).** The cell is
a diode approximation (`AccessType: diode`, 0.15 V drop). Its only half-select parameter is
`ResistanceOnAtHalfResetVoltage` 500 kOhm vs 100 kOhm at full voltage, a 5x ratio. Xu's size limits
assume a nonlinearity of 3000. How NVSim uses this value to bound array size was not traced.

**Not found.** Organization details (rows, mux) for Intel 22FFL (Jain, ISSCC 2019) and TSMC N40/N22 macros;
any published 3D XPoint tile size; how NVSim's own validation set the organization.

## 9. NVSim validity rules and forced organizations (source audit, 2026-09-15)

All runs: 139 NVSim configs derived from the official cfg/cell files, in `nvsim_rules_runs/`
(`out/q1_*` temperature ladder, `out/q2_*` MaxNmosSize, `out/q4_*` forced organizations,
`out2/asp_*` aspect probes, `out2/wl_*` wordline threshold, `out2/opt_*` free search per target,
`out2/forced_*` target independence). The NVSim patches in `simulators/nvsim/CLAUDE.md` (211a9eb,
bcec2ea, df92f02) do not touch organization or validity logic.

**Why 1T1R bitlines stop at 8192 rows.** The only 1T1R row limit is `SubArray.cpp:128`:
`Ion/Ioff < numRow / BITLINE_LEAKAGE_TOLERANCE` (tolerance 1, `constant.h:101`), using 22nm LOP NMOS
currents at the configured 350 K (`Technology.cpp:1232, 1254`): Ion/Ioff = 658.8 / 0.04365 = 15,094.
8192 < 15,094 < 16384. Width cancels, so cell resistance, access width, mux and bitline RC play no role.
Confirmed by sweeping temperature: 300 K (ratio 34,100) admits 32768 rows, 310-340 K admits 16384.
This is a crude leakage-accumulation rule, the same mechanism Chen and Indiveri model (§8).

**1S1R crossbars have no size physics.** The sneak-path row check is commented out
(`SubArray.cpp:137-155`). `ResistanceOnAtHalfResetVoltage` is read only for `AccessType none`
(`:164-165, 176-177`); for diode access the half-select current is `LeakageCurrentAccessDevice`, which
defaults to 0 (`MemCell.cpp:76`) and is unset in our cell, so the 500 kOhm value is dead. No IR-drop or
V/2 validity check exists. The only limits are wordline driver current (at most 78 selected columns per
wordline here; 8192x32768 needs MaxNmosSize 164 F, confirmed at 163/164) and bank aspect ratio <= 10
(`BankWithHtree.cpp:518`). So 8192x16384 was accepted only because nothing in NVSim forbids it.

**Search and forcing.** NVSim keeps the design with the smallest target metric (`Result.cpp:102-151`).
`ForceBank`, `ForceMat` and the mux keys fully set the subarray: at 1 Gb, WordWidth 512 and CACTI
assumptions, rows = 2^21 / (numRowMat x mux) and columns = 128 x mux / numColumnMat.
`UseCactiAssumption` overwrites `ForceMat` if it appears later in the file. With all organization keys
forced, the optimization target has no effect.

**Free search by target** (1 Gb, 350 K):

| Cell, mux | Area / LeakagePower pick | ReadLatency pick | ReadEDP pick |
|---|---|---|---|
| 1T1R, free | 1x1 bank, m256, 8192x32768: 10.53 mm², 8.85 mW, 331.5 ns | 32x8, m64, 1024x1024: 13.55 mm², 224 mW, 9.31 ns | same as ReadLatency |
| 1S1R, free | 1x2, m256, 8192x16384: 2.28 mm², 16.91 mW, 52.1 ns | 32x8, m64, 1024x1024: 4.45 ns | 32x4, m64, 1024x2048 |
| 1T1R, m32 | 8x32, 8192x128, 794.7 mW (the book's baseline) | 32x32, 2048x128 | same as ReadLatency |

Both project configs use `OptimizationTarget: Area`, which is what drives the oversized subarrays.
Under latency-oriented targets both cells independently land on 1024x1024 subarrays, the size Xu et al.
report for DRAM-competitive crossbars (§8).

**Forced realistic organizations** (area mm² / leakage mW / read ns / write ns; write = RESET/SET for 1T1R):

| Subarray | Bank, mux | 1T1R | 1S1R |
|---|---|---|---|
| 1024x1024 | 32x8, m64 | 13.55 / 224.1 / 9.31 / 14.33 | 5.13 / 220.2 / 4.45 / 22.81 |
| 1024x1024 | 16x16, m128 | 13.30 / 235.5 / 10.90 / 15.09 | 4.72 / 228.5 / 6.34 / 23.71 |
| 2048x1024 | 16x8, m64 | 13.03 / 213.2 / 9.70 / 15.01 | 4.72 / 211.6 / 4.72 / 24.65 |
| 1024x2048 | 32x4, m64 | 12.23 / 115.7 / 9.90 / 14.89 | 3.85 / 115.7 / 4.50 / 22.78 |
| 2048x2048 | 16x4, m64 | 12.01 / 108.4 / 10.12 / 15.26 | 3.54 / 108.4 / 4.70 / 24.59 |
| 512x512 | 64x16, m64 | 16.61 / 462.8 / 10.13 / 14.54 | 9.01 / 457.6 / 5.95 / 22.88 |

The full table, including invalid combinations and their causes (wordline limit or aspect ratio > 10),
is in `nvsim_rules_runs/`. At matched realistic organizations: leakage is the same for both cells
(identical to 0.01 mW at 1024x2048 and 2048x2048); 1S1R is 2.6-3.5x smaller in area, reads about 2x
faster, and writes about 1.6x slower.

**Unselected-cell leakage is not modeled anywhere.** Cell leakage is 0 (`SubArray.cpp:770`); NMOS off
current appears only in the pass/fail rule above and in periphery gate leakage (`formula.cpp:286-293`);
the current-sense bitline delay has no leakage term (`SubArray.cpp:560`); mux leakage is 0 (`Mux.cpp:137`).

## 10. Fabricated-chip ground truth (2026-09-15)

No full-text chip paper was reachable (IEEE Xplore, ResearchGate and Springer blocked). The two Gb-class
organizations below are therefore secondary. P = source text read; S = quoted by the named source;
S-abs = abstract text from a search listing; D = derived arithmetic.

| Chip | Organization facts | Conf. | Source |
|---|---|---|---|
| Micron/Sony 16Gb 1T1R, 27nm, Cu CBRAM, 6F² (Fackenthal ISSCC 2014 [33]) | 8 banks x 8 strips x (16+1 redundant) tiles; tile = 8,192+256 local bitlines x 2,048 wordlines (16 Mib); 8 tiles written at once, one active sub-tile each, up to 66 cells sensed or programmed per sub-tile | S | EE Times, "Showtime for the Micron-Sony 16Gb ReRAM" |
| same | about 2,048 cells per local bitline (if each local bitline spans the tile); local bitlines feed global bitlines shared per strip | D | |
| same | about 128 local bitlines per sensed bit (8,448 / 66); a hypothesis, not a confirmed mux ratio | D | |
| Intel/Micron 3D XPoint gen-1, 128Gb, PCM + OTS, 1S1R, 2 decks, 4F² | 16,384 tiles; 7.81 Mb per tile; "2,150 BLs and 2,150 WLs per tile including dummy"; all CMOS under the array; 91.4% array efficiency | S | TechInsights teardown blogs (gen-1, gen-2) |
| same | 128 Gib / 16,384 = 8 Mib = 2 decks x 2,048 x 2,048, leaving about 102 dummy lines per side | D | |
| SanDisk/Toshiba 32Gb, 24nm, oxide + diode cross-point (Liu JSSC 2014) | blocks share wordlines and bitlines with neighbours; sense amps under the array "limited" in number; block dimensions not found | S-abs | IEEE 6605602 |
| Crossbar Inc. 1S1R (vendor figures in Jagasivamani MEMSYS 2019) | 4-16F²; 4-8 bits read or written per array; read 200-700 ns; selectivity >10^6 to 10^10 | P | MEMSYS 2019 PDF |
| Embedded 1T1R macros (Intel 22FFL, TSMC N40/N22, Weebit S130, Panasonic 40nm, a 40nm 1Mb macro) | Mb-class only; the only sub-array size found is 512 Kb (1Mb macro = two 512 Kb sub-arrays); cells per bitline not found | S-abs / P | IEEE 10475670 and vendor pages |

**Physical size limits.**

| Study | Result | Assumptions | Conf. |
|---|---|---|---|
| Liang and Wong, TED 2010 (no selector) | 1000x1000 with >50% signal swing | Ron >3 MOhm | S-abs |
| Zhou, Kim and Lu, TED 2014 (1S1R read) | up to 16 Mb per crossbar (4096x4096, D) | selector rectification 10^3 | S-abs |
| Xu et al., HPCA 2015 | 256x256 to 1024x1024 mats, 4-16 bits per mat, meet DRAM area and power | nonlinearity 3000, 20 uA RESET, 4F² | P |
| Shevgoor et al., ICCD 2015 | 128x128, 1 bit per array, one sense amp per 16-64 arrays | assumed | P |
| Chen and Indiveri, arXiv 2410.20560 (1T1R, 22nm FDSOI) | columns of 256-4096 cells; best Ron 20-150 kOhm; unselected-transistor leakage dominates above a few hundred kOhm | 40 pA leakage at 0.2 V | P |
| Levisse et al. (EPFL/CEA) | IR drop shrinks the maximum crosspoint as F shrinks; acceptable only for Iprog <20 uA at 25 nm | crosspoint with selector leakage | P |

**Synthesis.** Both Gb-class ground truths converge on lines of about 2,048 cells: the Micron 1T1R tile
(about 2,048 cells per local bitline, many sensed bits per tile) and the XPoint 1S1R tile (about 2,048 x
2,048 active, few sense amps). 1S1R modeling supports 256-2,048 per side depending on selector
nonlinearity. Neither chip gives an NVSim-style mux ratio, so any mux value is an inference and must be
labelled as one. In NVSim at 1 Gb, 2048x2048 subarrays are valid for both cells at mux 64, 128 and 256
(§9): leakage identical, 1S1R 3.4-3.6x smaller.

**Most valuable unread sources:** Fackenthal ISSCC 2014 digest and slides; Liu ISSCC 2013 / JSSC 2014;
Kawahara JSSC 2013; Jo IEDM 2014 / TED 2015; Zhou/Kim/Lu TED 2014 full texts; Jain ISSCC 2019; Chou
ISSCC 2018 / VLSI 2020; Zahurak IEDM 2014; the full TechInsights XPoint report. Several are likely
available through Technion access.

## 11. Prior NVSim-based studies and calibration targets (2026-09-15)

Scratch clones and PDFs: session scratchpad `nvsim_prior/` (not copied into the repo). The NVSim TCAD
2012 full text (validation chips) and Niu ICCAD 2013 (1T1R vs 1D1R vs 0T1R) remain unread (paywalled).

**Key corrections to how prior work is read.**
- Xu et al. HPCA 2015 and Shevgoor et al. ICCD 2015 did **not** use NVSim (HSPICE crossbar models, a
  modified CACTI, USIMM). Their organizations are design guidance, not NVSim settings.
- NVMExplorer (arXiv 2109.01188, fork `lpentecost/nvsim-merged`) runs NVSim with **nothing forced**, a free
  search per optimization target: the same practice that produced our artifact. Its fork also keeps
  memristor cell leakage at 0.
- DESTINY (DATE 2015 / JLPEA 2017) is the only NVSim-lineage tool found with published ReRAM validation,
  and it forces organization for it: Kawahara 8Mb cross-point as 4 subarrays (read 24.16 vs 25 ns,
  write 20.13 vs 17.2 ns); Sheu 4Mb 1T1R as 4x8 mats (MLC write 157.8 vs 160 ns).

| Study | Tool | Organization | Tag |
|---|---|---|---|
| NVSim samples (SEAL-UCSB @6334d00) | NVSim | `sample_PCRAM.cfg` (256Mb PCRAM, JSSC 2007) forces `ForceBank 8x4, 1x1`, `ForceMat 1x4, 1x4`, mux 8; `sample_RRAM.cell` is 4F², `AccessType: None`, half-reset 500k | P |
| Xu HPCA 2015 | HSPICE + CACTI | 22nm 8Gb, mats 128-1024 swept, feasible 256-1024 with 4/8/16 bits per mat, baseline 512x512 n=8, 45 mm² DRAM area bound | P |
| Shevgoor ICCD 2015 | HSPICE + USIMM | 128x128 crossbars, 1 bit each; half-select leakage 1 uA; 134-146 uA sneak on a selected bitline | P |
| Zhang "Mellow Writes" ISCA 2016 | NVSim (energy only) | organization not reported | P |
| NVMExplorer | NVSim fork | free search; default RRAM 53F², CMOS width 6F | P |
| DESTINY | extended NVSim | forced for validation (above) | P |
| Jagasivamani MEMSYS 2019 | layout study | Crossbar 1S1R: about 1000x1000, 4-8 bits per array, cell leakage 0.1 nA/cell | P |
| NVMain `RRAM_ISSCC_2012_4GB.config` | NVMain | Panasonic 8Mb basis; 4 banks, ROWS 8192, COLS 512 | P |

**Calibration targets.**
- **A (software drift):** NVMExplorer tutorial pair: 22nm LOP RRAM 53F², CMOS 6F, 1 MB, WordWidth 64,
  ReadEDP gives 0.2467 mm², read 0.775 ns, write 10.64 ns, read 4.028 pJ, write 53.19 pJ, leakage 3.432 mW.
  Inputs public (`EducationalTutorial/RRAM_1BPC-combined.csv`, `cell_cfgs.py`); cell aspect ratio differs
  between CSV (1.46) and `.cell` (1.0).
- **B (1T1R silicon):** Sheu ISSCC 2011 4Mb, 7.2 ns SLC access; a DESTINY fork has an 8 MB, 4x8 bank config
  and a 20F² CMOS cell. Only the SLC figure applies to stock NVSim.
- **C (cross-point silicon):** Kawahara 8Mb, read 25 ns / write 17.2 ns; DESTINY's config is not public and
  needs 3D, so stock NVSim is approximate at best.
- NVSim TCAD validation table: not found.

**NVSim knob for crossbar validity.** Setting `-LeakageCurrentAccessDevice (uA)` from a published selector
(Shevgoor 1 uA half-select; Crossbar 0.1 nA per cell) activates the existing wordline and bitline
half-select sizing checks (§9). It does not change reported leakage, which stays periphery-only.

**Side note.** The public GitHub repo `uvKogan/Memristor-based-dram` already contains `leak47x.py` and
`leak47x_sweep.py`, while the book still states the 47x claim.

## 12. Decision (Lead Researcher, 2026-09-15)

**Primary organization: 2048x2048 subarrays, identical for 1T1R and 1S1R**, anchored to the fabricated-chip
ground truth in §10 (Micron/Sony 16Gb 1T1R tile, 3D XPoint 1S1R tile). 1024x1024 and 512x512 are
sensitivity runs. Re-run time is not a consideration; matching prior studies and ground truth is.

Agreed method, in order:
1. **Calibrate our NVSim** against target A (NVMExplorer tutorial pair, software drift) and target B (Sheu
   ISSCC 2011 4Mb 1T1R, 7.2 ns SLC access), §11. Fix any mismatch before continuing.
2. **Force the 2048x2048 organization** with `ForceBank`/`ForceMat`/`ForceMuxSenseAmp` (§9 formula), and
   verify the subarray size NVSim prints. The mux value has no chip source and is labeled an inference.
3. **Engage NVSim's crossbar validity checks** by setting `-LeakageCurrentAccessDevice` from a published
   selector (Shevgoor 1 uA half-select or Crossbar 0.1 nA per cell). Report cell-level leakage separately as
   an analytic bound, since NVSim cannot model it.
4. **Re-run the full NVMain matrix** through `mbmm_master.py`, then correct the claims inventoried in §6.

## 13. Primary papers supplied by the Lead (2026-09-15, in progress)

Folder: `documents/reference_validation_papers/`. Text extracted with pypdf into the session scratchpad.
The organization papers (Liu JSSC 2014, Zahurak IEDM 2014, Chou VLSI 2020, Zhou/Kim/Lu TED 2014, and the
Springer Handbook of Semiconductor Devices) and the endurance/MLC papers (Wong [14], Chen TED 2020,
Guan/Yu/Wong TED 2012 I-II, EMBER [6]/[31], Le [13], Zangeneh and Joshi TVLSI 2014) are being read in
full; results will be added here and in `endurance_deep_dive.md`.

**Matsui et al. [7] (IEICE, advpub 2025VLP0011): the book's 1e5 / 1e9 Ohm targets rest on a 1024-cell
bitline.**
- Model: a 1T1R bitline read with the k-th cell selected; I_BL = V_SL / (R + k·r_BL) (Eq. 2, p. 3),
  where r_BL is the bitline interconnect resistance per cell pitch.
- Design point (p. 5): "When the memory number k to be read is 1024 in the digital ReRAM memory, the
  ReRAM LRS resistance R_LRS should be set as high as 1.0x10^5 Ohm with r_BL = 1 Ohm and alpha = 0.99",
  where alpha is the retained fraction of ideal bitline current and 1 Ohm is a 22 nm Cu single-level line
  (0.5 Ohm double-level).
- This is the likely origin of the book's "1024-cell bitlines" (§1.2, lines 217 and 242). It is the
  resistance-design basis, not the organization NVSim simulated (8192-row bitlines).

Retained current alpha = 1e5 / (1e5 + k·r_BL) at the book's LRS (derived from Matsui Eq. 2):

| Cells per bitline k | alpha, r_BL = 1 Ohm | alpha, r_BL = 0.5 Ohm |
|---|---|---|
| 1024 (Matsui design point) | 0.990 | 0.995 |
| **2048 (chosen organization)** | **0.980** | **0.990** |
| 4096 | 0.961 | 0.980 |
| 8192 (current NVSim baseline) | 0.924 | 0.961 |
| 16384 | 0.859 | 0.924 |

**Implication for the 2048x2048 decision.**
- 2048-cell bitlines keep 98% of ideal current with single-level Cu. They meet Matsui's alpha = 0.99
  criterion exactly with double-level interconnect.
- The decision stays consistent with the resistance source, but the book should state the 2048 bitline
  and the interconnect assumption rather than "1024-cell bitlines".
- Eq. 2 omits the access transistor; Matsui's HSPICE check degrades more than Eq. 2 (p. 3).

**Other files in the folder (triage).**
- `TR-20230620152301412.pdf`: SK hynix DDR5 component part-number decoder. Lists "EB 4800 40-39-39",
  a vendor confirmation of the DDR5-4800 CL-tRCD-tRP timing the book uses. `TR-20230620152301091.pdf` is
  the matching module decoder.
- `2510.14750v2.pdf` (ColumnDisturb, ETH 2025), `000000190906.pdf` (Minbok Wi, SNU PhD 2025, DRAM
  security), `2.+Endita+Layla+Sulistiyowati.pdf` (DDR4 vs DDR5 comparison, JDAICS 2026): DRAM-side
  background, not used for organization or endurance.

### 13b. Organization papers, read in full (2026-09-15)

Page = PDF page of the extraction [journal page]. Q = stated in the source; D = derived.

**Liu et al., JSSC 49(1) 2014, SanDisk/Toshiba 32Gb 24nm cross-point (primary 1S1R ground truth).**
- Chip and cell: 130.7 mm², 2 memory layers; metal-oxide cell with a **diode** selector; circuits under the
  array (Q, p.1-2). Cell size not stated.
- Hierarchy: 16 bays x 128 blocks = 2048 blocks. **Block = "2K BLs x 4K WLs" per layer, 16 Mb**, BLs shared
  between the two layers, drivers shared by adjacent blocks (Q, p.2, Fig. 4).
- Sensing: 1024 sense amps, 64 per bay, shared by the bay's blocks; a selected pair of blocks gets all 64
  (Q, p.2). About **32 sensed bits per block and 64-128 BLs per sensed bit** (D, Figs. 6 and 10a).
- Why this block size: large blocks help die efficiency, but "leakage current imposes adverse effect for sensing
  and writing"; 16 Mb chosen to fit control, sense amps, page buffer and drivers under the array (Q, p.1).
  "IR drop in a large array also puts a constraint on the number of cells that can be written in parallel on
  the same WL" (Q, p.2).
- **Chip current is "dominated by the array leakage"** from biased unselected cells (Q, p.1, p.5).
- Latency: read 40 us, write 230 us, NAND-like interface; page 2 KB (Q, Table II).

**Zahurak et al., IEDM 2014, Micron/Sony 16Gb 27nm Cu ReRAM 1T1R.**
- Confirmed: 6F² (4374 nm²), 168 mm², 8-bank interleaved DDR architecture (Q, p.1-2, Table 1).
- Access device: buried recessed transistor, Ion 40 uA per device at VGS 5.5 V. ReRAM needs "significantly higher
  drive with moderate Ioff" than DRAM (Q, p.1-2).
- "ReRAM cell technology requires an access device to enable sufficiently large array blocks" (Q, p.1).
- **Read latency 2.3 us, write 11.7 us**; 900 MB/s read, 180 MB/s write (Q, Table 1).
- Endurance: BER reported only through 10^5 cycles; retention BER after cycling and bake 1.4e-3 to 2.2e-3
  (Q, Table 2).
- **Tile, strip, bitline, wordline and sense-amp counts: NOT IN SOURCE.**

**Chou et al., VLSI 2020, TSMC 22nm 96Kx144 1T1R macro (13.5 Mb, 53F²).**
- 28 blocks of 640x768 cells; each block has 10 subarrays; "Each subarray has a read-SA sitting between two
  32X768 cell arrays", 32:1 mux on each side (Q, p.1, Fig. 5).
- **768 cells per BL, 64 BLs per sense amp** (D). The only primary 22nm 1T1R organization found.
- Access 10 ns (10K-cycle use), 6.5 ns (OTP) at 0.7 V; qualified for 10K SET+RESET cycles (Q, p.1).

**Springer Handbook of Semiconductor Devices** (the file labeled "Liu / Fackenthal").
- Fackenthal is only cited; the tile organization is NOT IN SOURCE.
- Crossbar tile limit: **"Tile size = (I_ON / (6·I_leak))²"**, with I_leak at Vth/2 (Fig. 17.21, p.642-643, from
  Molas IMW 2020). Selector on/off ratio is "dictated by the array memory size mainly" (Table 17.3).
- Selector on/off >10^6 "is enough to build a crossbar RRAM array with size >10 M" (p.1079, citing Deng TED 2013).
- OTS Ioff 10 nA at 0.5 Vth, Ion 100 uA (Table 30.3).

**Zhou, Kim and Lu, TED 2014.**
- Model: selector I = γ·sinh(αV), nonlinearity k = I(V)/I(V/2); worst-case corner cell with all unselected cells
  in LRS; 10% read margin minimum. The largest array simulated is 512x512.
- Results:
  - k = 10^4: below 10% above 256x256 regardless of selector on-current (Q, p.3).
  - k = 10^3: crosses 10% near N = 200 (F).
  - Best biasing scheme: 10% at N = 512 needs k of about 2e3-7e3 (F, Fig. 9).
- **Correction to §8 and §10:** the row "up to 16 Mb per crossbar (4096x4096) at rectification 10^3" is not in the
  paper (it came from a search summary). No 16 Mb or Gb-class condition is given.

**Verdicts on the secondary rows of §10.**

| Row | Verdict |
|---|---|
| Micron 16Gb, 27nm, Cu, 6F², 8 banks | CONFIRMED (Zahurak) |
| Micron tile 8,192+256 x 2,048, 66 cells per sub-tile, 512+16 sensed | NOT IN SOURCE (still EE Times only) |
| SanDisk/Toshiba block dimensions "not found" | CORRECTED: 2K BLs x 4K WLs per layer, 2 layers, 16 Mb, 64 SAs per bay |
| Zhou/Kim/Lu "16 Mb at 10^3" | CORRECTED: not in paper; about 200-256 per side at k = 10^3-10^4 |
| XPoint tile 2,150 x 2,150 | unchanged (teardown only) |

**What this means for the decision (§12).**
- **1S1R 2048-line blocks are now backed by a primary chip** (Liu, 2K x 4K per layer). The mux value best supported
  is **64** (64-128 BLs per sensed bit, D).
- **1T1R 2048 remains secondary** (EE Times). The only primary 22nm 1T1R organization is 768 cells per BL with
  **64 BLs per sense amp** (Chou), closer to the 1024 sensitivity point.
- Recommended forced setting: **2048x2048 at mux 64 for both** (the §9 "16x4, m64" row), with 1024x1024 m64 as the
  first sensitivity run. Label the 1S1R geometry "Liu, primary", the 1T1R geometry "secondary", and mux 64
  "derived from Chou (1T1R) and Liu (1S1R)".

**Physics NVSim cannot represent, now with primary backing.**
1. Liu's crossbar current is dominated by unselected-cell leakage; NVSim sets cell leakage to 0. A matched-organization
   leakage "tie" between 1T1R and 1S1R is therefore not physical for 1S1R.
2. The project's diode selector (0.15 V drop, half-select ratio 5) cannot support any multi-kb crossbar by Zhou's
   curves or the handbook's tile formula ((5/6)² < 1). A 2048-line crossbar needs I_ON/I_leak >= about 12,300.
   NVSim accepts it only because no check exists.
3. **Latency class.** Gb-class fabricated ReRAM is microsecond-class at chip level (Micron 1T1R read 2.3 us, write
   11.7 us; SanDisk 1S1R read 40 us, write 230 us), including interface and page overhead. Only Mb-class embedded
   macros reach ns (TSMC 10 ns). NVSim's 1 Gb ns-class latencies have no fabricated precedent; this must be
   stated as a validity limit.
4. Parallel writes on a WL are IR-drop limited (Liu); NVSim's only analog is the wordline driver current limit.

## 14. NVSim calibration (2026-09-15)

Inputs and outputs under 1 MB: `calibration_runs/`. Large debug-print outputs are listed in
`calibration_runs/OMITTED_LARGE_FILES.txt`. Builds compared: ours, upstream SEAL-UCSB/NVSim @6334d00, and the
NVMExplorer fork nvsim-merged @282038a.

**Software drift: none.** On every case run, ours and upstream give identical output once the local debug-print
lines are removed:
- upstream `nvsim.cfg`
- `sample_NVM_macro`, `sample_PCRAM`, `sample_SLCNAND`, `sample_STTRAM_cache`
- `sample_RRAM` (both access types)
- Target A
- the planned re-run cfgs

The local patches are only the `-std=c++11` Makefile flag, debug prints (`Mat.cpp:187-190, 253-257`), and in
`main.cpp:473-516` the CAM-to-RAM redirect, a commented-out MLCNAND exit and debug prints.
`simulators/nvsim/CLAUDE.md` wrongly claims an `InputParameter.cpp` patch.

**Target A (NVMExplorer tutorial pair: 22nm LOP, 53F², 1 MB, ReadEDP).**
- The fork reproduces all six published numbers exactly. Ours and upstream differ from them, and each difference
  traces to the fork's sense-amp rewrite:

| Metric | Published = fork | Ours = upstream, same organization |
|---|---|---|
| Area | 0.2467 mm² | +40% |
| Read latency | 0.775 ns | +186% |
| Write latency | 10.64 ns | +0.5% |
| Read energy | 4.03 pJ | +245% |
| Write energy | 53.19 pJ | +1.4% |
| Leakage | 3.43 mW | -54% |

- **Code-level causes:**
  - Sense-amp delay below 22nm: 1.45 ns upstream (`SenseAmp.cpp:149`) vs 0.1 ns in the fork.
  - Sense-amp energy: 15e-14 J vs 8e-15 J.
  - Sense-amp leakage: 15e-8 W vs 0 in the fork.
  - Sense-amp layout and IV-converter area differ between the two.
  - The fork adds a subarray buffer, requires subarray column counts to be multiples of 64, and limits bank aspect
    ratio to 3 instead of 10.
- The published row used cell aspect ratio 1.46, not the shipped `.cell` value of 1.0.

**Target B (Sheu ISSCC 2011, 4Mb 180nm 1T1R, 7.2 ns).**
- **Organization dominates:** free and forced organizations give 1.3 to 25.8 ns.
- At the true 4 Mb, the DESTINY 4x8-mat organizations give 2.0-2.6 ns (63-72% fast).
- Only the DESTINY fork's 8 MB (64 Mbit) capacity lands at +15%.
- 180nm device parameters come from the 200nm branch marked "only for test" (`Technology.cpp:58`), and the
  current-sense amp uses the fixed 120nm value.
- NVSim's 1T1R write time is decoder delay plus the input pulse width, so write is not a calibration.

**Target C (Kawahara 8Mb 2-layer cross-point).**
- Skipped as a calibration: a 2D approximation of a 2-layer chip, a sample cell rather than Kawahara's, and no
  sneak-path or IR-drop model.
- Ours and official DESTINY 2D agree within 0.2% (6.07 / 14.37 ns vs 25 / 17.2 ns on silicon).

**Smoke test of the planned re-run** (22nm LOP, 1 Gb, `ForceBank 16x4`, `ForceMat 2x2`, mux 64): ours = upstream,
both "2048 Rows x 2048 Columns".

| Cell | Area | Read | Write | Leakage |
|---|---|---|---|---|
| 1T1R | 12.008 mm² | 10.12 ns | 15.26 ns | 108.38 mW |
| 1S1R | 3.540 mm² | 4.70 ns | 24.59 ns | 108.38 mW |

This matches §9.

**Verdict.** The software is trustworthy for the re-run (no drift). As a predictor of silicon it is loosely
calibrated: 1T1R read is organization-sensitive (-72% to +15% on Sheu), and 1S1R has no silicon anchor.

**Required before the re-run:**
1. **Verify the organization in every NVSim output, not the exit code.** The project cfgs lack a trailing
   newline; an appended `-ForceBank` line glued onto the cell path gave "-ForceBank cannot be found!" with exit
   code 0. The generator must write a newline first, remove the existing `-ForceMuxSenseAmp` lines, and place the
   force keys after `-UseCactiAssumption`.
2. **State the sense-amp model.** Stock NVSim's 22nm sense-amp constants are marked "TO-DO, need calibration below
   22nm" (`SenseAmp.cpp:149, 186-187`). The fixed 1.453 ns is 14% of 1T1R and 31% of 1S1R read at 2048x2048.
   Keep stock and say so; optionally run NVMExplorer's constants as a sensitivity case.
3. **Label 1S1R results uncalibrated and 1T1R latency organization-sensitive.**
4. **Housekeeping:** filter the `Mat.cpp` debug prints (one sample produced 7.28 M lines) and fix
   `simulators/nvsim/CLAUDE.md`.
