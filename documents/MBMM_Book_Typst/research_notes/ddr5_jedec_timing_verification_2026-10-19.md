# DDR5-4800B timing re-verification (2026-10-19)

**Why this note exists.** The F4 task of the 2026-09 revision set every JEDEC-sourced key of
`configs/DDR5_4800_DRAM_subchannel.config` (and the 64B cross-check) from JESD79-5 tables read
through a third-party mirror, and the tracker's open item 3 asked for a re-check against an
official copy. The JEDEC document itself is access-gated (JESD79-5D, Nov. 2025, is listed at
USD 423 for non-members on jedec.org) and was not obtained. This note records the next best
check: every value was compared against **Micron's DDR5 SDRAM Core Product Data Sheet**, the
vendor's full transcription of JESD79-5 for a JEDEC-compliant part, and against two DDR5-4800
module datasheets that reproduce the device timing table. All values agree. The one-cycle
uncertainty the F4 review left on the power-down entry formulas is closed.

## Sources

| Tag | Document | Where it was read |
|---|---|---|
| M-core | Micron Technology, "DDR5 SDRAM" core product data sheet, Doc. CCM005-1684161373-23, Rev. D, 10/2022, 537 pp. | Farnell mirror `https://www.farnell.com/datasheets/3980285.pdf`, text-extracted with pdftotext; a copy sits outside the repo at the session scratchpad (13.8 MB, not tracked) |
| M-add | Micron, "16Gb DDR5 SDRAM Addendum, Die Rev. A", CCM005-0005-1684161373-30 (book reference [29]) | `https://www.farnell.com/datasheets/3704816.pdf` |
| T-mod | Transcend TS4GLA64V8E DDR5-4800 UDIMM datasheet, Table 4 "Timing Parameters and Specifications" and SPD table | `https://docs.rs-online.com/4f10/A700000012187024.pdf` |
| A-mod | Advantech AQD-D5V16GN48-SB DDR5-4800 UDIMM (2048Mx8 devices), "Timing Parameters & Specifications" and SPD bytes 30 to 93 | `https://advdownload.advantech.com/productfile/PIS/AQD-D5V16GN48-SB/file/AQD-D5V16GN48-SB_datasheet20221005111902.pdf` |
| gem5 | gem5 `src/mem/DRAMInterface.py`, class `DDR5_4400_4x8` (same JEDEC formulas at 4400) | GitHub, stable branch |

Micron table numbers below are from M-core: Table 361 "DDR5-4800 Speed Bins and Operating
Conditions" (p. 390), Table 429 "DDR5 4400-5200: Command and Address Timing" (p. 481), Table 438
"DDR5 4400-5200: Power-Down Timing", Table 437 "Self Refresh Timing".

## Key-by-key result

tCK = 1 / 2400 MHz = 0.4166667 ns in the config; M-core Table 361 gives tCK(AVG) min 0.416 ns for
the 4800B bin. Cycle counts are ceil(ns / tCK) with the larger of the nCK and ns terms winning.

| Config key | Config value | JEDEC parameter | Vendor value and source | Cycles at 0.41667 ns | Agrees |
|---|---|---|---|---|---|
| tCAS | 40 | CL (4800B) | 40, tAA 16.666 ns (Table 361; M-add) | 40 | yes |
| tRCD | 39 | tRCD (4800B) | 16.250 ns (Table 361: bin 40-39-39) | 39 | yes |
| tRP | 39 | tRP (4800B) | 16.250 ns (Table 361) | 39 | yes |
| tRAS | 77 | tRAS | 32.000 ns (Table 361; T-mod; A-mod SPD 0x7D00 = 32,000 ps) | 76.8 to 77 | yes |
| tCWD | 38 | CWL | CL - 2 (M-core mode register table; A-mod note 6; gem5) | 38 | yes |
| tWR | 72 | tWR | 30 ns (Table 429; A-mod; T-mod 29.952; SPD 0x7530 = 30,000 ps) | 72 | yes |
| tRTP | 18 | tRTP | max(12 nCK, 7.5 ns) (Table 429; T-mod; A-mod; SPD 0x1D4C = 7,500 ps, floor 12 nCK) | 18 | yes |
| tWTR | 6 | tWTR_S (chosen short value) | max(4 nCK, 2.5 ns) (T-mod; A-mod tCCD_S_WTR = CWL + WBL/2 + max(4 nCK, 2.5 ns); SPD 0x09C4 = 2,500 ps) | 6 | yes |
| (not used) | | tWTR_L | max(16 nCK, 10 ns) = 24 nCK (T-mod; A-mod) | 24 | n/a, documented judgement |
| tCCD | 8 | tCCD_S | 8 nCK (Table 429; T-mod; A-mod) | 8 | yes |
| (not used) | | tCCD_L | max(8 nCK, 5 ns) = 12 nCK (Table 429) | 12 | n/a, documented judgement |
| tRRDR, tRRDW | 8 | tRRD_S (1K page) | 8 nCK (Table 429; T-mod; A-mod) | 8 | yes |
| (not used) | | tRRD_L | max(8 nCK, 5 ns) = 12 nCK (Table 429) | 12 | n/a, documented judgement |
| RAW | 4 | four-activate window | 4 activates by definition (tFAW) | | yes |
| tRAW | 32 | tFAW (1 KB page) | max(32 nCK, 13.333 ns) (Table 429; A-mod); T-mod and the mirror print 13.312 ns; both round to 32 nCK | 32 | yes |
| tRFC | 708 | tRFC1 (16 Gb) | 295 ns (A-mod SPD 0x0127 = 295 ns; gem5) | 708 | yes |
| tREFW | 76,800,000 | tREFW | 32 ms, 8192 REF commands, tREFI 3.9 us (M-add) | 32 ms x 2400 MHz | yes |
| tPD | 18 | tPD min | max(7.5 ns, 8 nCK) (Table 438) | 18 | yes |
| tXP | 18 | tXP | max(7.5 ns, 8 nCK) (Table 438; gem5 7.5 ns) | 18 | yes |
| tRDPDEN | 49 | tRDPDEN | CL + RBL/2 + 1 (Table 438) = 40 + 8 + 1 | 49 | yes |
| tWRPDEN | 119 | tWRPDEN | CWL + WBL/2 + WR + 1 (Table 438) = 38 + 8 + 72 + 1 | 119 | yes |
| tWRAPDEN | 119 | tWRAPDEN | CWL + WBL/2 + tWR + 1 (Table 438) | 119 | yes (never read by NVMain) |
| tXS | 5 | tXS | tRFC1 = 295 ns (Table 437) | 708 | NO, but inert: NVMain never enters self refresh; the only reader is the disabled DRAMPower trace hook (config comment) |
| tXPDLL | 17 | none | DDR5 has no DLL-off power-down exit (Table 438 lists only tXP) | | n/a, documented as unmapped |

RBL/2 = WBL/2 = 8 for BL16, which is the config's `tBURST 8`.

## What this closes and what it does not

- The F4 review caveat on `tRDPDEN`, `tWRPDEN` and `tWRAPDEN` ("may be off by one cycle") is
  closed: Micron's Table 438 formulas are exactly the ones the config implements, including the
  trailing "+ 1" and the rounding of tWR to 72 nCK.
- The `tFAW` nanosecond term differs between sources (13.312 ns in the mirror and Transcend,
  13.333 ns in Micron and Advantech). At 0.41667 ns both give 32 nCK and the nCK floor binds, so
  the config value is unaffected.
- The check is against the vendor's statement of JESD79-5, not against the JEDEC text. The
  configs' inline provenance comments still say "read from a third-party mirror, re-verify
  against an official copy". Those comments live in files tracked twice (under `configs/` and in
  the NVMain submodule, byte-identical by the Stage 4 gate), so updating them means a new NVMain
  commit and a new submodule pin; the Lead can fold a two-line pointer to this note into both
  copies at the next NVMain commit. Nothing numeric changes.
