# Future Work Notes - Lead Researcher

Personal idea log for work beyond the current book. Nothing here is in `Project_Book.typ` §4 yet
unless stated. Each note records the idea, why it matters, what was checked, the catch, a smallest
useful version, and a rough effort. Effort figures are rough estimates, not plans.

| # | Idea | Status |
|---|---|---|
| 1 | Re-simulate the 1T1R family at 6F² | Idea, assessed 2026-09-14 |
| 2 | Simulate Intel Optane (enough data? worth it?) | Assessed 2026-09-15: usable as a reference point, not simulable faithfully |

---

## 1. Re-simulate the 1T1R family at 6F²

**Idea.** Re-run the whole 1T1R matrix (SLC and MLC, all chip counts, all six workloads) with a 6F²
cell instead of 20F².

**Why it matters.** The book's density verdict against 1T1R (0.22x DDR5 die-level density) rests on the
20F² planar-transistor assumption. A real 16Gb, 27nm 1T1R part reached 6F² with a recessed-channel
access transistor [33]. Today the book only estimates the effect linearly ("roughly 0.7x", §3.3) and
lists it as future work (§4.2, Appendix A "Bit-Cell Area"). A simulation would replace that estimate.

**What the pipeline does today (checked in source).**
- `configs/reram_22nm_1t1r_slc.cell`: `CellArea (F^2): 20.0`, `CellAspectRatio: 1`, `AccessType: CMOS`,
  `AccessCMOSWidth (F): 4.0`.
- NVSim uses `CellArea` only to set the cell's height and width (`sqrt(area)`, `MemCell.cpp:141-142`).
- The access transistor's on-resistance, capacitance and gate leakage all come from `AccessCMOSWidth`
  (`SubArray.cpp:250-300`, `:690`). Nothing checks that the transistor fits inside the cell.

**The catch.** Changing only `CellArea` to 6 would put a 4F-wide planar transistor inside a
2.45F x 2.45F cell. NVSim would accept it silently, but the device is physically impossible. A recessed
channel gets a large effective width in a small footprint by folding the channel into the silicon, and
NVSim's access-device model cannot represent that (book Appendix A, §4.2).

**Proposed approach: a bounding pair, always reported together.**
- **A, optimistic:** `CellArea 6`, `AccessCMOSWidth 4F`. Density at 6F², with drive current and leakage
  unchanged. Stands in for "the recessed channel delivers full planar-equivalent drive".
- **B, conservative:** `CellArea 6`, `AccessCMOSWidth` reduced to fit a planar 6F² footprint (about 2F).
  Less drive current and less leakage; SET/RESET may get slower or fail to reach the target current.
- A real recessed-channel device should sit between A and B.

**Hypothesis to test (not a result).** Density should rise sharply in both variants, less than the
3.3x cell-level ratio at die level because the periphery does not shrink. Power is harder to predict
than it first looked. NVSim assigns memristor cells zero leakage whatever the access device
(`SubArray.cpp:770`); chip leakage is all peripheral circuitry (`:869`), so it tracks how many mats and
subarrays NVSim builds. Today's 1T1R chip is split into 256 mats against the selector's 2 (checked
2026-09-15, `results/hardware/*_results.txt`). A smaller cell shortens wordlines and bitlines and can
change that organization, so leakage may move in both variants, not only in B. Resolve the pending
47x-mechanism question (1T1R and selector swapped onto each other's array settings) before running
this, because it determines what a 6F² result would mean.

**Open questions.**
- What effective width or drive current does [33]'s recessed-channel transistor actually have? This
  would anchor A vs B to a real device.
- Material mismatch: [33] uses a Cu-filament CBRAM layer, while the book models oxide RRAM with
  1e5 / 1e9 ohm targets [7]. The re-run keeps the oxide targets, so it is a geometry study, not a
  replica of [33].
- Does variant B still complete SET/RESET at 2.0 V into a 1e5 ohm LRS, or does NVSim reject it?
- MLC follows automatically, because its penalties are analytical multipliers on the SLC result.

**Pipeline work.**
- Add new model names (for example `reram_22nm_1t1r6f2a_slc` / `..._mlc` and a `6f2b` pair) instead of
  editing the 20F² files, so the book's baseline stays reproducible.
- Model names are hard-coded in `mbmm_master.py` (`reram_bases`, `factory_bases`), in
  `process_metrics.py` (`classify_technology`, `RERAM_KEY_PREFIX`), and in the technology color and label
  tables of the `visualize_*.py` scripts. An isolated driver in the style of `sweep_queue_size.py`
  (separate output directory) would avoid touching the official results.
- Run count: 2 cell types (SLC, MLC) x 4 chip counts x 6 workloads = 48 runs per variant, 96 for A and B.
  Any Python change goes through `mbmm_master.py` per CLAUDE.md.
- Book impact if adopted: §3.3 density discussion, Tables 6 and 7, Figure 26, Appendix A "Bit-Cell Area",
  and §4.2's "Recessed-Channel 1T1R Density" bullet becomes a result.

**Rough effort.** About 1 day of plumbing, an overnight simulation batch, and about 1 day to analyze and
write up.

---

## 2. Simulate Intel Optane? (enough data? worth it?)

**Verdict (researched 2026-09-15).** There is enough published data to use Optane as a **reference point**,
but not enough to **simulate it faithfully**, at either the cell or the module level. Optane's measured
latency is dominated by its on-DIMM controller, which NVMain does not model.

**What exists.**

| Parameter | Value | Source | Confidence |
|---|---|---|---|
| Cell stack | GST phase-change element + OTS selector, stacked 1S1R | Kau et al., IEDM 2009 [42]; TechInsights teardown | Primary (design principle) |
| Cell area | 0.00176 µm² at 20 nm (about 4.4F², 42 nm pitch) | TechInsights teardown blog | Secondary |
| RESET pulse, endurance | 9 ns, 10^6 cycles (2009 64 Mb prototype, not the product) | Kau 2009 abstract | Not viewed directly |
| SET/RESET currents, voltages, resistances, OTS thresholds | Not published for the shipped product | - | Not found |
| Media timing (NVMain tRCD/tWP equivalents) | Not published | - | Not found |
| Interface, capacities | DDR-T protocol on DDR4-2666 electricals; 128/256/512 GB | Intel ARK; Izraelevitz [32] | Primary |
| Power | PMem 100: 12-18 W envelope (15 W average default); PMem 200: 12-15 W. Idle power not found | StorageReview; [32] Table 1; Intel brief | Secondary / primary |
| Endurance | PMem 100 256 GB: 360 PBW over 5 years (about 1.4M full-module writes) | Intel via Blocks and Files | Secondary |
| Measured latency | 305 ns random / 169 ns sequential read vs 81 ns DDR4 DRAM | [32] | Primary |
| Measured bandwidth | 6.6 GB/s read / 2.3 GB/s write, one DIMM | [32] | Primary |
| On-DIMM internals | 16 KB SRAM read-modify-write buffer, 16 MB DRAM address-indirection buffer, 4 KB write-combining queue, wear-leveling tail latency | Wang et al., "LENS/VANS", MICRO 2020 | Primary (reverse-engineered) |

**How the 305 ns was measured** (matters for any comparison): Intel Memory Latency Checker reading one
random 64-byte cache line on one core, from a file memory-mapped on an ext4-DAX pmem device (App Direct
mode), prefetching off, cold cache. It is a CPU-side, end-to-end number: memory controller, DDR-T bus and
on-DIMM controller included. It is not a media latency.

**Can we simulate it?**
- **NVSim Optane cell: no.** NVSim supports PCM cells natively (`MemCellType: PCRAM`; example cell at `configs/samples/sample_PCRAM.cell`), but the shipped product's SET/RESET currents, resistance states and
  OTS selector characteristics were never published. Any cell would be generic selector-PCM, not Optane,
  and the OTS selector could only be approximated as a diode, as this project's 1S1R cells already are.
- **NVMain Optane module: no, not honestly.** No media timing is published, so tuning `tRCD` until the
  model hits 305 ns would be circular. NVMain also lacks everything that makes Optane slow: the DDR-T
  request/grant handshake, the write-combining and read-modify-write buffers, the address-indirection
  buffer, and wear-leveling translation. The VANS paper shows DDR-style simulators (DRAMSim2, Ramulator)
  miss Optane's latency and bandwidth badly; NVMain was not tested there, so that part is inferred.
- **As an external validation target: only partly.** Matching Optane's ratios after tuning a config is
  calibration, not hardware correlation.

**What it could do for the project.**
- **It cannot close the "internal validation only" limitation.** Optane is PCM, so it says nothing about
  the NVSim ReRAM device layer, and its measurement setup (CPU-side, cold cache, DDR4, unmodeled
  controller) differs from NVMain's trace-driven controller timing.
- **It can strengthen an honest limitation.** The only NVM DIMM ever shipped was about 3.8x slower than
  DRAM on random reads, largely because of its controller, buffers and wear leveling. MBMM models none of
  these, so its DIMM-level latency is probably optimistic. That caveat belongs in the book.
- **It gives a real-product endurance anchor** for Shahar's note 8: 360 PBW over 5 years for a shipped
  NVM DIMM.
- **VANS is open source and was validated against real Optane** (86.5% average accuracy on
  microbenchmarks, 87.1% on SPEC with gem5, as reported in the paper). Running MBMM's traces through
  VANS would be the most credible Optane cross-check available, though still against a validated
  simulator, not hardware.

**Recommended scope.**
1. **Now, about half a day, no simulation:** a limitations and future-work paragraph citing [32], VANS
   and the PBW figure, with the controller-overhead caveat. This adds references, so the reference-count
   updates apply.
2. **Skip:** an NVSim Optane cell or a tuned NVMain Optane config. About 2-3 days of work that
   demonstrates nothing and invites reviewer criticism.
3. **Optional future work, roughly 1-2 weeks:** convert MBMM traces to VANS input, run its published
   Optane configuration, and compare read-latency and bandwidth ratios with NVMain's. VANS's trace and
   config formats have not been inspected yet, so this estimate is uncertain.

**Not verified from a primary source.** TechInsights cell figures (blog summary only); Kau 2009's 9 ns and
10^6 (abstract seen via a search listing); PMem 200 PBW and TDP (search snippet); PMem 100 PBW and power
(trade press quoting Intel); VANS configuration values (not inspected); NVMain's mismatch with Optane
(inferred, not tested).

**Sources.** Izraelevitz et al., arXiv:1903.05714 · Wang et al., MICRO 2020
(swanson.ucsd.edu/data/bib/pdfs/MICRO20-LensVans.pdf) · VANS code (github.com/TheNetAdmin/VANS) ·
Intel ARK, PMem 100 256 GB · Intel PMem 200 product brief · StorageReview (Optane DC PMM) · Blocks and
Files (Optane DIMM endurance, 2019-04-04) · Lenovo Press LP1066 · TechInsights 3D XPoint teardown · Kau et
al., IEDM 2009.
