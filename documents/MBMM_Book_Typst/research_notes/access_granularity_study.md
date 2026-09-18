# Access granularity: 64 vs 128 bytes, and the DDR5 baseline's fidelity

**Date:** 2026-09-18. **Trigger:** the Lead asked whether a 128-byte access could actually be better for ReRAM,
and whether there is evidence. **Status:** measured. Runs in the session scratchpad `burstwidth/`. Repo unchanged.

## Bottom line

1. **128 bytes is worse for this project, on every axis, for mechanical reasons.** Total latency rises 57%
   (1T1R) and 66% (1S1R) on GCC, and 59% and 75% on GPT-2. Lifetime falls 43-50%. There is no device-side gain
   to trade against it.
2. **It also cannot be modeled honestly here.** NVMain's address translator hardcodes a 64-byte address grid
   (`src/AddressTranslator.cpp:52-54`, offsets at `:93-95` and `:203-205`) regardless of `BusWidth` and
   `tBURST`. Raising `tBURST` bills 128 bytes of bus time and capacity for a 64-byte transaction: not a wider
   memory, just a slower one. Decision 39's own fallback clause is therefore triggered.
3. **The DDR5 baseline is not faithful DDR5, and the book claims it is.** Real DDR5 splits a DIMM into two
   independent 32-bit subchannels at burst length 16, so one access delivers **64 bytes** (32 bits x 16), which
   is why JEDEC doubled the burst when it halved the channel width. Our config is a DDR4-style 64-bit channel
   with a doubled burst, delivering 128 bytes.
4. **Every DDR5 bandwidth number in the book is 2x high** relative to delivered bytes, and DDR5 gets *faster*
   when corrected, which narrows ReRAM's advantage.

## 1. Device side: a wider word is free per byte, and buys nothing

NVSim, forced 2048x2048 at mux 64, 1 Gb chip. WordWidth 1024 needs `ForceBank 8x8, 1x8` (versus `16x4, 1x4`).
Mat count is unchanged; the bank simply activates 8 mat-columns instead of 4.

| Metric | 1T1R 64 B | 1T1R 128 B | 1S1R 64 B | 1S1R 128 B |
|---|---|---|---|---|
| Area | 12.008 mm² | 12.008 mm² (0.0%) | 3.540 mm² | 3.540 mm² (0.0%) |
| Leakage | 108.384 mW | 108.384 mW (0.0%) | 108.384 mW | 108.384 mW (0.0%) |
| Read latency | 10.120 ns | 10.902 ns (+7.7%) | 4.702 ns | 5.503 ns (+17.0%) |
| Read energy per byte | 5.87 pJ | 5.94 pJ (+1.2%) | 5.13 pJ | 5.30 pJ (+3.4%) |
| Write energy per byte | 14.24 pJ | 14.30 pJ (+0.4%) | 16.84 pJ | 17.02 pJ (+1.1%) |
| Read latency per byte | 0.158 ns | 0.085 ns (-46%) | 0.073 ns | 0.043 ns (-41%) |

At WordWidth 1024 the mux must stay at 32 or 64: mux 128 collapses read latency to 28.1 ns.

**Caveat:** this neutrality is an upper bound for 1S1R. NVSim models no cell leakage, sneak current, IR drop or
mux leakage, while Liu et al. (JSSC 2014) state that IR drop limits how many cells can be written in parallel on
one wordline, which is exactly what a wider word doubles.

## 2. End to end: 128 bytes costs 22-75%

Window-matched (identical admitted requests: GCC 236,562 reads + 170,800 writes; GPT-2 6,553 reads).

| Config | Trace | Access | Service | Queue | Total |
|---|---|---|---|---|---|
| 1T1R at 2048x2048 | GCC | 64 B | 52.2 ns | 23.5 ns | **75.7 ns** |
| 1T1R at 2048x2048 | GCC | 128 B | 64.3 ns | 54.8 ns | **119.0 ns (+57%)** |
| 1S1R at 2048x2048 | GCC | 64 B | 42.7 ns | 23.4 ns | **66.1 ns** |
| 1S1R at 2048x2048 | GCC | 128 B | 52.7 ns | 56.8 ns | **109.5 ns (+66%)** |
| 1T1R at 2048x2048 | GPT-2 | 64 B | 35.4 ns | 253.0 ns | **288.5 ns** |
| 1T1R at 2048x2048 | GPT-2 | 128 B | 45.4 ns | 412.6 ns | **458.0 ns (+59%)** |

Power barely moves (leakage dominates), but **dynamic energy is 1.98x for the same delivered bytes**.

**Why, mechanically:** the address grid is fixed at 64 bytes, so a 128-byte burst coalesces nothing. The same
requests each hold the bus twice as long, and `MAX(tBURST, tCCD)` doubles the column-to-column floor.

**The experiment that would let 128 bytes win:** rebuilding traces as if the host had 128-byte lines. Break-even
needs the request count to more than halve. Measured coalescing at a queue-sized reuse window is **27.9% (GCC)**
and **28.6% (GPT-2)**, both short of 50%. Only GPT-2 at a 256-access reuse window wins, and that coalescing would
happen in the last-level cache, which NVMain cannot model, not at the DIMM.

## 3. Endurance: a 128-byte access costs 43-50% of lifetime

Wear granularity doubles unconditionally, halving the number of independently wearable words, while writes
coalesce far worse than reads: only **12.7% of GCC writes** disappear at a 32-access reuse window.

| Case | Lifetime, 1T1R SLC 64 GB, E = 10^7, GCC | Ratio |
|---|---|---|
| 64 B (current) | 166.1 yr | 1.00x |
| 128 B, no write coalescing | 83.1 yr | 0.50x |
| 128 B, measured write coalescing | 95.1 yr | 0.57x |
| 128 B, perfect coalescing (hypothetical) | 166.1 yr | break-even |

Intel's PMem 200 brief prices the same failure mode on shipped silicon at the full granularity ratio: 292-497 PBW
at 256 B versus 73-125 PBW at 64 B.

## 4. Literature: the field chose narrower, and Intel put the widening inside the device

- **Lee et al., ISCA 2009** (the canonical PCM main-memory paper) argues for narrower buffers, not wider: wide
  DRAM-style buffering "incurs unnecessary energy costs in PCM given the expensive current injection required
  when writing", and a 32x reduction in buffer width produced only a 2x increase in array reads, "suggesting
  very little spatial locality within wide rows". Our 27.9% coalescing measurement is the same finding.
- **Yang et al., FAST 2020** on Optane: media granularity is 256 bytes, and small stores become read-modify-write
  with an effective write ratio of 0.25 at 64 B versus 0.98 at 256 B. **But Intel kept the bus transaction at
  64 bytes** and put the widening inside the device, behind a write-combining buffer.
- **x86-64 uses a 64-byte cache line**, which is why JEDEC sized the DDR5 subchannel transaction at 64 bytes.
  A 128-byte memory transaction has no consumer on a standard server host.
- **Crossbar physics** (Liu JSSC 2014; Xu HPCA 2015) makes wide activation worse specifically for 1S1R.

## 5. The DDR5 baseline: three defects

1. **`BurstLength` is a dead key.** No parser reads it; the only setter has no callers. `BurstLength 16` does
   nothing.
2. **The address translator ignores `BusWidth` and `tBURST`** and always decodes on a 64-byte grid. Access
   granularity is not a free parameter in this toolchain.
3. **The reported bandwidth is proportional to `tBURST`.** Measured on identical traffic, the DDR5 config reports
   12,672 MB/s at `tBURST 8` and 6,338 MB/s at `tBURST 4`: exactly 2.0x for the same delivered bytes.
   `5_summary_report.py:39` scrapes this figure, so **every DDR5 bandwidth number in the book is 2x high**.

**Correcting DDR5 makes it faster**, not slower: GCC total latency 90.2 to 85.8 ns (-4.8%), GPT-2 100.4 to
59.9 ns (-40%, and it drains the trace 2.04x faster). On the honest comparison, GCC becomes ReRAM 1T1R 75.7 ns
versus DDR5 85.8 ns (ReRAM still ahead); at 128 bytes ReRAM would be behind at 119.0 versus 90.2 ns.

**An honest DDR5-4800 subchannel config** would be `BusWidth 32`, `DeviceWidth 8`, `tBURST 8` (64 B),
`tCCD 8`, `CHANNELS 2` (the subchannels), `RANKS 1`, `BANKS 32`, `ROWS 65536`, `COLS 64`, 40-39-39,
`tRFC 708`, `tREFI 9375`. Capacity checks out at 16 GiB, unlike either current file. It halves NVMain's
device-count-scaled background energy, so DDR5 power will move and must be re-run.

**Book claims that must be retracted or fixed:** `Project_Book.typ:434` says the baseline models "two
independent 32-bit sub-channels per DIMM and a Burst Length of 16". Neither is modeled. Line 513's bank-group
switching penalty claim is also unmodeled: NVMain has no bank-group model, only a flat `tCCD`.

## 6. Two NVMain defects found along the way

- **`tCCD < tBURST` can segfault NVMain**, reproducibly (exit 139). The live DDR5 config sits in exactly that
  region (`tCCD 4` with `tBURST 8`) and escapes only by luck. Setting `tCCD 8` fixes it and changes no timing,
  since NVMain uses `MAX(tBURST, tCCD)`.
- **`3_gen_nvmain_config.py` sets `tRAS = tREAD`**, which violates `tRAS >= tRCD + tBURST` at any burst longer
  than the default.

Also: `configs/DDR5_4800_DRAM.config` is tracked but unused and stale (34-34-34, tRFC 840). The pipeline reads
`simulators/nvmain/Config/DDR5_4800_DRAM.config` (40-39-39, CHANNELS 2). A reproducibility hazard on its own.

## 7. Recommendation

Keep **64 bytes for ReRAM and fix DDR5 to 64 bytes**, so both transact one x86 cache line: what the host
requests, what JEDEC sized the DDR5 subchannel for, and what Intel shipped. If a wide internal word is ever
wanted, the defensible route is Optane's: keep the 64-byte bus transaction and put a write-combining buffer in
front of a wider internal word. That belongs in future work, not in `tBURST`.

## 8. Addendum: line sizes in the literature (2026-09-18)

- **Qureshi, ISCA 2009** uses 256-byte lines and moves granularity down.
- **Xu, HPCA 2015** uses 64-byte L2 blocks on gem5+NVMain.
- **Udipi, ISCA 2010; Yoon, ISCA 2011; O'Connor, MICRO 2017** all argue for finer DRAM access.
- Real hosts: x86-64 uses a 64-byte line; POWER is 128-byte sectored as 2x64 bytes; Apple M-series is
  128 bytes.
- **Write amplification:** WA = 2/(1+f), with measured f = 0.127 for GCC, giving 0.57x lifetime at
  128 bytes (consistent with §3's measured write-coalescing figure).
- **Required endurance for 10 years at 64 GB:** 2.8e6 cycles (64 B), 5.6e6 cycles (128 B), 1.12e7
  cycles (256 B).
