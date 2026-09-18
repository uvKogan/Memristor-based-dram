# ReRAM interface clock: 800 vs 2400 vs 3000 MHz, and what else the sweep exposed

**Date:** 2026-09-18. **Trigger:** the Lead asked whether the 800 MHz ReRAM DIMM interface (old-hardware-era)
could be raised toward DDR5 speed. **Status:** measured; decisions pending. Runs and configs are in the session
scratchpad `clockrate/`. The regenerated 800 MHz config is byte-identical to the tracked one, so the sweep used
the real generator on the real `results/hardware_metrics.json`. Nothing in the repo was changed.

## Bottom line

1. **Technically supported up to CLK 3000, which is a hard ceiling** (CPUFreq is 3000). Above it NVMain
   silently corrupts admission: the `assert(CLK <= CPUFreq)` at `src/EventQueue.cpp:460` is compiled out of
   `nvmain.fast` by `-DNDEBUG` (`SConstruct:27-37`). A run at CLK 4000 completed with exit 0 and admitted 298 of
   6,553 requests.
2. **Raising the clock buys queueing, not device physics.** 1T1R SLC on GCC: 263.24 ns at 800 to 93.80 ns at
   3000 (-64%), of which service latency improves only 23% and queue latency 79%. The curve is flat past 2400.
3. **The tCAS/tRCD read double-count is a bigger lever than the clock**, and it is a modeling error rather than
   an assumption: fixing it at 800 MHz gives 103.81 ns on GCC (-61%), about the same as tripling the clock.
   Both together give 56.41 ns against DDR5's 52.47 ns, essentially parity.
4. **Power is unaffected** (under 0.01% on GCC). The standby term is clock-invariant by construction:
   `e_standby_nj = rank_leakage_w x cycle_time_ns` cancels the clock exactly.
5. **2400 or 3000 MHz has no more citation support than 800 does, and less defensible framing.** The only
   shipped NVM DIMM precedent, Optane DDR-T, runs **2666 MT/s = 1333 MHz interface clock**, below contemporary
   DRAM. Going faster than the only shipped precedent inverts the book's current, defensible position.

## 1. What the clock actually changes

- **Command granularity is clock-independent:** no ReRAM config sets `tBURST` or `tCCD`, so NVMain's DDR3-era
  defaults apply silently (`src/Params.cpp:137,139`), giving a 64-byte memory word.
- **Peak channel bandwidth** = CLK x RATE x BusWidth/8: 12.8 / 38.4 / 48.0 GB/s at 800 / 2400 / 3000.
- **Bus occupancy per 64-byte access** (tBURST = 4 cycles): 5.00 / 1.67 / 1.33 ns.
- **Command issue slot** (one command per memory cycle, `src/MemoryController.cpp:1673-1676`): 1.25 / 0.417 /
  0.333 ns. This is the dominant queueing lever.
- **Array latencies stay fixed in nanoseconds** by construction (tCAS, tRAS, tWR derive from the NVSim ns
  values), which confirms the book's §2.3 claim numerically at all three clocks.
- **Clock-domain crossing:** the multiplier CPUFreq/CLK is 3.75 / 1.25 / 1.0. CLK 3000 is numerically cleanest
  (no truncation).

## 2. What the generator writes, and what it does not

`3_gen_nvmain_config.py` writes eight timing keys. `tCAS`, `tRCD`, `tRAS` and `tWR` follow the device
nanoseconds faithfully at every clock. But:

- **`tRP` is hard-coded to 1 cycle**, so precharge drops from 1.25 ns to 0.33 ns purely by raising the clock.
- **`tRTW` and `tBus` are dead keys**: NVMain never parses them.
- **About a dozen uncalibrated DDR3-1333 stock timings** (`tBURST`, `tCCD`, `tCWD`, `tRTP`, `tWTR`, `tRRDR`,
  `tRRDW`, `tRTRS`, `tXP`, `tPD`, `RAW`) shrink in wall-clock terms as the clock rises. None was ever chosen for
  ReRAM. A clock sweep must say so, or it credits ReRAM with gains that came from NVMain defaults.

**The read double-count, confirmed in C++:** `SubArray::Activate` completes at `+tRCD`
(`src/SubArray.cpp:319`), then `SubArray::Read` at `+tCAS +tBURST` (`:463-464`). With `tRCD = tCAS = tREAD`, a
row-miss read costs twice the full NVSim read latency plus burst. 1T1R SLC's 32.134 ns device read shows up as
69.57 ns of service latency at 800 MHz. Raising the clock does not fix it.

## 3. Measured (window-matched: identical admitted requests in every row)

**GCC, 29,392 reads + 360 writes, full DIMM:**

| Model | CLK | Service ns | Queue ns | Total ns | Module power |
|---|---|---|---|---|---|
| 1T1R SLC | 800 | 69.57 | 193.68 | 263.24 | 50.9039 W |
| 1T1R SLC | 2400 | 55.12 | 41.84 | 96.96 | 50.9067 W |
| 1T1R SLC | 3000 | 53.67 | 40.13 | 93.80 | 50.9071 W |
| 1S1R SLC | 800 | 96.09 | 277.01 | 373.10 | 1.1887 W |
| 1S1R SLC | 2400 | 79.59 | 84.55 | 164.13 | 1.1885 W |
| 1S1R SLC | 3000 | 78.15 | 78.61 | 156.77 | 1.1900 W |
| DDR5-4800 (2 channels) | 2400 | 31.60 | 20.87 | 52.47 | 0.6615 W |

MLC tracks follow the same pattern (1T1R MLC 353.06 to 143.72 ns; 1S1R MLC 521.42 to 416.02 ns).

**The double-count lever (1T1R SLC, same windows):**

| Configuration | GCC total | GPT-2 total |
|---|---|---|
| 800 MHz, as shipped | 263.24 ns | 458.45 ns |
| 3000 MHz, as shipped | 93.80 ns (-64%) | 311.73 ns (-32%) |
| **800 MHz, double-count removed** | **103.81 ns (-61%)** | **331.25 ns (-28%)** |
| 3000 MHz + double-count removed | 56.41 ns (-79%) | 249.97 ns (-45%) |
| DDR5-4800 reference | 52.47 ns | 100.39 ns |

## 4. Two comparison asymmetries found in passing (clock-independent, larger than the clock question)

1. **DDR5 runs two channels, ReRAM one.** `Config/DDR5_4800_DRAM.config` never sets `CHANNELS`, so it defaults
   to 2, while every ReRAM config sets `CHANNELS 1`. The DDR5 baseline therefore has twice the channel
   parallelism and 76.8 vs 12.8 GB/s of peak bandwidth. The book discloses "single-channel", but the headline
   comparison is one channel against two.
2. **DDR5 uses a 128-byte burst word, ReRAM 64 bytes** (`tBURST 8` / `BurstLength 16` vs the silent default 4).
   Different command granularity between the technologies, never declared.

## 5. Precedent for an NVM DIMM interface clock

- No ReRAM-specific primary source states any DIMM-class interface clock (confirmed again;
  `item2_reram_interface_speed.md`). Real ReRAM datasheet parts are SPI at 5-20 MHz.
- **Optane DC Persistent Memory: DDR-T on a DDR4 interface at 2666 MT/s, a 1333 MHz interface clock**
  (Intel support article 000032853; Lenovo Press LP1066). `item3_9_optane_real_numbers.md` records DDR-T but not
  the rate; it should be added.
- NVDIMM-N modules run the full contemporary DDR4 rate, and Everspin's STT-MRAM DIMMs use a DDR4 PHY, so an NVM
  DIMM behind a DRAM-class PHY is clearly buildable. Optane at 2666 MT/s still delivered far below DDR4
  bandwidth because the media, not the PHY, was the bottleneck: exactly the effect in §3.

## 6. Recommendation (pending the Lead's decision)

1. Keep **800 MHz as the baseline** (disclosed, conservative against ReRAM), and add the interface clock as a
   declared sensitivity axis at **800 / 1333 / 2400**, with 1333 included because it is the only NVM-DIMM
   interface clock with a real citation.
2. **Fix the tCAS/tRCD double-count**, before or alongside any clock discussion. It is an error, not an
   assumption, and it is the larger lever.
3. Guardrails for any sweep: the generator must refuse CLK above CPUFreq (the assert is dead in `nvmain.fast`),
   and `--cycles` must be scaled by CLK/CPUFreq or runs compare different trace windows
   (`traceSim/traceMain.cpp:195-196`; `4_execute_simulation.py:262` does not do this today).
4. State that raising the clock also shrinks `tRP` and about a dozen uncalibrated stock timings.
5. Decide separately on the channel-count and burst-width asymmetries in §4.
