# MBMM AI Context State
**Project:** Evaluation of 22nm Memristor-Based Main Memory (MBMM) in Commodity DIMM Architectures
**Researcher:** Yuval Kogan, Technion
**Supervisor:** Prof. Shahar Kvatinsky

**Generated:** 2026-09-20 (hardfork); **corrected 2026-09-21** against the post-final-review book,
after two further defects were found at the source of the DDR5 data and repaired (tasks F1 and F4:
NVMain's current-mode background-power accounting, which had DDR5 static power 4x too low, and the
DDR5 write-path / power-down / activate-window timings, which were still DDR3-1333 template cycle
counts). **Both move DDR5 only** - every ReRAM and PCM figure in this file is unchanged by them -
but they move every DDR5 latency, power, PDP and ratio, and they reverse the direction of the
power argument, so every such number below was re-read from the corrected book. Both are recorded
in the book's Appendix A, "DDR5 Timing and Power Corrections of This Revision", and in Appendix D.
Regenerated from the 2026-09 revision of
`documents/MBMM_Book_Typst/Project_Book.typ`, the corrected, compile-verified edition of the Project
Book that closes out the "3 September" version. This is a full hardfork, not an in-place update: the
2026-09 revision changed the book's central architectural verdict (the transistor-versus-selector
leakage gap that the prior edition treated as its deciding fact does not exist as a device effect), so
almost nothing in the prior context file carries forward unchanged.

**Supersedes:** the 2026-08-22 version of this file, now archived byte-identical at
`archive/root_docs/MBMM_AI_Context_State_pre-hardfork_2026-09-20.md`. Do not cite that file, or
anything it describes, for any of the following (all corrected in Appendix D of the 2026-09 book,
"What Changed Since the 3 September Version"):
- **The 47x/794.7-vs-16.9-mW leakage gap between 1T1R and 1S1R, framed as a device effect.** It was an
  artifact of characterizing the two cells at different, hand-set array organizations (mux 32 for
  1T1R, giving 256 mats, vs mux 256 for 1S1R, giving 2 mats). At the matched 2048 x 2048, mux-64
  organization this revision forces for both cells, NVSim reports 108.384 mW per 1 Gb chip for
  **both**, identical to three decimals. There is no leakage-class separation.
- **The "1T1R is infeasible ungated / ~50.9 W" verdict.** Superseded: 1T1R SLC full DIMM now draws
  6.939 W (identical to 1S1R's 6.940 W) at the matched organization.
- **The old ReRAM-vs-DDR5 latency ratio ("1T1R SLC 136.2 ns, 1.51x DDR5's 90.2 ns", or any earlier
  number derived from the double-counted read path).** The generator was charging the full NVSim
  device read latency into both tRCD and tCAS (every read billed twice); that is fixed, and combined
  with the trace regeneration below, corrected GCC latency is 41.4 ns (1T1R SLC) and 36.8 ns (1S1R
  SLC) against DDR5's 83.1 ns, i.e. ReRAM is now *faster* than DDR5 on this trace - at
  NVSim-projected device timings only, and never to be stated without the counterweights of
  Section 3.
- **The 83.33 ms replay window, and any "uncached", no-warmup, no-region-of-interest trace
  description.** The traces' actual time base is exact integer NVMain cycles at `CPUFreq 3000` (1
  cycle = 1/3 ns); the real window is 250 ms; every gem5 trace was regenerated with L1/L2 caches, a
  documented detailed region and a 10 ms warm-up discard, and reconciles exactly with gem5's own
  request counters (no more fourfold record duplication).
- **The old LBM write rate (39.1 M/s) and every endurance lifetime derived from it** (e.g. "1.09 years
  at 8 GB, 8.7 years at 64 GB"). That rate came from a window sitting inside LBM's own start-up burst
  on a fourfold-duplicated trace. The corrected sustained rate is 9.54 M writes/s, and endurance is now
  projected across four wear-leveling policies (Section 3.1.4 below), not assumed ideal.
- **The 512 GB and 32 GiB capacity errors** (the full-DIMM ReRAM configuration decoded 512 GB of
  address space against an 8 GB physical module; the DDR5 baseline was actually a single 64-bit
  channel, 32 devices, 32 GiB, while the book's prose claimed two 32-bit subchannels and 16 GiB). Both
  are fixed: the ReRAM full DIMM is 8 GiB SLC / 16 GiB MLC of 64 x 1 Gb chips; DDR5 is 16 GiB of eight
  16 Gb x8 devices on two real 32-bit subchannels.
- **The old chip-count / rank-depth scaling verdict** ("GCC improves ~14% across chip count", "GPT-2
  IFMAP is exactly flat"; any claim that rank depth or chip count by itself is the scaling lever). The
  corrected matrix shows the three CPU traces are offered-rate limited (6.4-10.4% improvement, no
  monotonic trend), the two AI read bursts gain 1.68x entirely from the *second channel* (a one-channel
  control run collapses all three physical chip-count points onto one latency), and rank depth alone is
  worth at most 7.5%, only on the CPU traces.
- **The old AI trace sizes/record counts** (GPT-2 IFMAP 6,554 records; AlexNet IFMAP 184,320; AlexNet
  OFMAP 13,543). The SCALE-Sim parser was keeping one address per trace row instead of every address
  and writing padding markers in as real addresses; corrected counts are 65,536 / 1,269,600 / 135,424
  (undercounts of 10.0x / 6.9x / 10.0x in the old numbers).

Also retired, though not named individually by the task that produced this hardfork: the old die-area
ratios (1T1R 19.802 mm², 1S1R 2.276 mm², an "8.7x selector advantage"; now 12.008 and 3.540 mm², 3.4x);
the old density figures (1S1R 1.92x/3.84x DDR5, 1T1R 0.22x/0.44x; now 1.24x/2.47x and 0.36x/0.73x); the
old geometric-mean PDP figures and the "29x intra-ReRAM gap" claim (now a 1.08x-1.2x near-tie); the
"selector lives longer" endurance claim (withdrawn: all four ReRAM tracks wear identically once every
track completes the same request population); and the SLC/MLC endurance rating basis of 10^7/10^6
cycles cited to Wong et al. [14] (that paper gives no such rating; the basis is now 10^6, cited to
Chen's 2020 review [47], with 10^4 and 10^7 carried as bounds). Full row-by-row detail for every one of
these is Appendix D of the book; nothing above should be treated as an exhaustive restatement of it.

---

## 1. Executive Academic Narrative

### 1.1 Core Thesis

The memory supply-demand gap of late 2025, driven by DRAM wafer reallocation to AI-focused HBM
production, motivates evaluating 22nm Memristor-based Non-Volatile Memory (NVM) as a DRAM replacement
in standard DIMMs, via a cross-layer pipeline bridging NVSim (device-level) and NVMain 2.0
(cycle-accurate architecture). The 2026-09 revision's single most consequential methodological change
is that 1T1R (transistor-gated) and 1S1R (selector-gated) are now characterized at one **matched array
organization** (2048 x 2048 subarrays, sense-amp mux 64, forced identically for both cells and verified
against NVSim's own printed geometry on every run), so that every cross-technology difference reported
is a device difference, not an organization difference. Six workloads are evaluated, drawn from five
benchmarks (AlexNet split into read-dominant IFMAP and write-dominant OFMAP phases): 502.gcc_r
(compute-bound), 519.lbm_r (memory-streaming), the real STREAM benchmark, AlexNet IFMAP/OFMAP and
GPT-2 IFMAP (both SCALE-Sim). A seventh planned workload, 505.mcf_r, is **absent**: gem5 panics inside
the benchmark's own input reader about 0.13 ms into the detailed region, identically on the March and
September attempts; no mcf number appears anywhere in the book, and recovering it needs a rebuilt
benchmark binary from the Lead plus a new, explicit SPEC2017 access grant (the 2026-09-18 exception
closed 2026-09-20).

### 1.2 The Central Findings (2026-09 revision, all book-verified)

**Finding 1, Latency: the projected ReRAM array beats DDR5 on five of six workloads, bounded hard by a
published-silicon counterweight.** At NVSim-projected device timings, full-DIMM average total latency
under GCC is 41.4 ns (1T1R SLC) and 36.8 ns (1S1R SLC) against DDR5's 83.1 ns; under LBM 43.1 / 38.1
against 78.3; under STREAM 42.3 / 37.3 against 79.4; under GPT-2 IFMAP 143.3 / 130.1 against 222.1;
under AlexNet IFMAP 143.6 / 130.0 against 212.3. Those DDR5 figures are the corrected ones: they carry
the JESD79-5 write path, power-down path and activate window that replaced the DDR3-1333 template cycle
counts (Appendix A), which raised DDR5's own average latency by 6.4 to 47.5% across the six traces. The
one reversal is the write-dominated AlexNet OFMAP burst, where DDR5 (234.3 ns) beats every ReRAM track
(1T1R SLC 353.1, 1S1R SLC 391.5, 1T1R MLC 512.0, 1S1R MLC 652.9 ns; DDR5 is 1.507x faster than 1T1R
SLC and 1.671x faster than 1S1R SLC, 2.185x and 2.787x against the MLC tracks): DRAM reads and writes
at the same cost, a resistive cell does not. ReRAM still loses this regime, but by less than before
the DDR5 timing correction. **Why the projected array is faster is itself model-dependent:** of the
41.40 ns 1T1R SLC GCC average only 11.25 ns is NVSim device time, charged once as tRCD + tCAS; the
other 30.2 ns is NVMain's default protocol cycle counts at the assumed 800 MHz interface, so roughly
three quarters of the ReRAM figure is an interface assumption, not a device measurement. The
*direction* is robust (ReRAM is below DDR5 at all three measured clocks) and the *magnitude* is
model-dependent. For the same reason the **MLC latencies are lower bounds**: this project's generator
books NVSim's write latency as tWR and leaves tWP at zero, so the cell write pulse is off the request
path entirely. This result is bounded by a hard condition: replaying the identical
traces at published fabricated-chip timings (Micron/Sony's 16 Gb 1T1R [49], SanDisk/Toshiba's 32 Gb
1S1R [48]) gives 11.9 us and 379 us under GCC, three to four orders of magnitude above the projection,
and neither part completes the LBM window (18.2% and 1.0%). **The latency advantage belongs to the
projected device, not to any shipped part.** Under sustained LBM streaming every ReRAM track now
completes the whole 250 ms window (5,564,704 of 5,564,704 requests), same as DDR5; the legacy PCM
baseline completes only 50.2%. A new `averageEndToEndLatency` statistic (trace-arrival to completion,
vs. `averageTotalLatency`'s queue-entry to completion) is the saturation measure: where a configuration
keeps up the two agree to a fraction of a cycle; where it does not (PCM, both silicon rows) they
diverge by up to six orders of magnitude.

**Finding 2, Power: there is no transistor-versus-selector leakage gap.** At the matched organization
NVSim gives both cell types identical peripheral leakage, 108.384 mW per 1 Gb chip (NVSim assigns
memristor cells zero leakage; chip leakage is entirely peripheral circuitry and scales with mat count).
The full 8 GiB ReRAM DIMM draws 6.94 W under GCC, 99.96% static, against **0.797 W** for a 16 GiB DDR5
module (the corrected current-mode background accounting, four times the figure NVMain printed):
**about 17.4x more power per gigabyte under GCC, 12.7 to 17.4x across the suite for SLC and 6.4 to
8.7x for MLC**. This ratio is an **upper bound**: DDR5's figure carries a real, restored JEDEC
power-down credit, while ReRAM's power-down energy is an explicit, disclosed no-savings placeholder (no
NVSim datapoint decomposes ReRAM leakage into gatable-periphery vs. ungatable-crossbar, and no citable
ReRAM power-gating figure exists), so the model cannot price a gated ReRAM module at all.
**The power argument changed direction as well as size with the DDR5 correction.** Break-even now
needs **94.3%** of the static component gated at 22nm (80.8% at a 12nm-class port), which sits
*inside*, not above, the 94-98% idleness implied by Malladi et al.'s reported 2-6% memory-bandwidth
utilization for web-serving/data-analytics servers [21]: at f = 0.98 the gated module would draw
0.142 W against DDR5's 0.399 W for the same 8 GiB, a ratio of 0.36x - *below* DDR5 - and at f = 0.94
it would draw 0.419 W, 1.05x. **The cited band brackets break-even**, so the arithmetic no longer
forbids parity for that deployment class; what forbids the book from claiming it is the unpriceable
placeholder above. Two scope bounds must travel with all of this. **Both module figures count memory
devices only** - no register clock driver, power-management IC, PHY, termination or ReRAM-side
controller on either side. And a fixed per-module overhead O points the two statements in *opposite*
directions: it *compresses* the ungated per-GiB ratio (17.4x falling toward an asymptote of 2x) while
*raising* the gating fraction parity needs - 97.9% at O = 0.5 W per module, and beyond **O = 0.79 W**
no gating fraction reaches parity at all. The overhead flatters the ratio and moves the gated
comparison *against* ReRAM. A dedicated analytic selector layer (NVSim models no selector physics) finds the sneak-current
budget adds **zero** to standby power at either bound and 7.56 mW/chip (present-day OTS) or 0.076
mW/chip (best-published FAST selector [9]) during an access; but tile validity, not leakage, binds:
the OTS bound supports only a 1,666-cell tile side, so **the simulated 2048 x 2048 organization is not
valid at present-day selector quality**, and every 1S1R result in the book is conditional on a selector
better than today's production ovonic threshold switch.

**Finding 3, Efficiency (PDP): the four ReRAM tracks are within 1.2x of one another, not separated by
29x.** Geometric-mean PDP across the six workloads: DDR5 **136.21** W·ns, legacy PCM 173.6, 1S1R SLC
594.5, 1T1R SLC 641.0, 1S1R MLC 645.4, 1T1R MLC 722.8 W·ns. DDR5's own figure *rose* (from 103.3 in
the 3 September version) once the corrected background accounting and the corrected JEDEC write path
were both in it, so the gap it sets is narrower than any this book has reported: the best ReRAM
configuration trails DDR5 by **4.4x** at module level and **4.7x to 9.4x** per gigabyte (4.7x 1S1R
MLC, 5.3x 1T1R MLC, 8.7x 1S1R SLC, 9.4x 1T1R SLC). The gap narrowed because both terms of the DDR5
side were corrected, not because ReRAM improved. PCM's module-level lead over ReRAM does not survive
per-gigabyte normalization against MLC (PCM 5.1x DDR5 vs. 1S1R MLC 4.7x), and PCM's own figure rests
on two service-limited workloads (50.2%/46.1% completion) and an inherited, uncharacterized
configuration constant, not a characterized device.

**Finding 4, Endurance: wear leveling, not the cell, decides viability, and every figure is a
projection.** Rating basis corrected to 10^6 cycles/cell (Chen 2020 [47]; Wong et al. [14], previously
cited for 10^7 SLC/10^6 MLC, gives no such rating at all and has been withdrawn for that purpose). At
64 GiB, ideal uniform leveling gives 38.6 yr (GCC), 3.6 yr (LBM), 4.3 yr (STREAM); **no leveling at all
gives 7.7, 23.2 and 69.5 hours** (these traces are sparse: GCC touches 577 row locations out of
131,072 at 8 GiB). A faithful, newly-added deterministic Start-Gap remapper [52] over one whole-module
region recovers essentially none of that gap for these footprints (the hottest line fails before the
gap rotates once); randomizing the region recovers part of it (0.20 yr LBM, 0.96 yr STREAM, still
nothing on GCC). Required endurance for a ten-year life at 64 GiB: 2.6x10^5 (GCC), 2.8x10^6 (LBM),
2.3x10^6 (STREAM) cycles under ideal leveling, 6.3/6.5/4.3x10^6 under randomized Start-Gap, against the
10^6 planning value. The claim that the selector variant outlives the transistor variant is
**withdrawn**: it was an artifact of the slower configuration completing fewer writes inside a
service-limited window; all four tracks now wear identically (7.1 yr at 128 GiB, ideal leveling). MLC
does not "live longer" than SLC either. AlexNet OFMAP's 132.5 M/s figure is a burst rate (a 4.5 us
burst spread over its 1.022 ms drain time), never a sustained requirement, and is flagged as such
wherever used.

**Finding 5, Density: the selector's density edge shrank sharply, and is now conditional.** At the
matched organization, 1S1R delivers 1.24x DDR5's die-level density as SLC and 2.47x as MLC (down from
the retired 1.92x/3.84x, which came from an implausibly small two-mat periphery); 1T1R lands at 0.36x
and 0.73x (up from 0.22x/0.44x). Cell-level, node-independent bound: DRAM 6F²/bit, 1T1R 20F²/bit, 1S1R
4F²/bit, so 1S1R SLC is 1.5x denser than DRAM and MLC 3.0x by cell arithmetic alone; the measured
1.24x die-level SLC figure now falls *short* of that bound (sense-amp/decoder/mux overhead at a
2048-cell tile), which is the expected, credible direction. A factor-of-two miss on the idealized 4F²
cell area would drop 22nm SLC *below* DDR5 parity (0.62x); MLC is what carries the density case.

**Finding 6, Simulation-Fidelity Audit: fourteen silent failure modes found, thirteen repaired.** See
Section 5 below. The one unrepaired item is the GPT-2 trace's generator configuration (its SCALE-Sim
run was never preserved, so it is treated as a representative parallel-read pattern, not a validated
GPT-2 capture); NVMain's power-down state machine, previously disabled, has been **restored** this
cycle (it was open in the 2026-08-22 predecessor of this file).

### 1.3 Cross-Technology Summary (book Table 7, full-DIMM)

| Technology | GCC latency (ns) | GCC power (W / W per GiB) | Geo-mean PDP (W·ns) | Die density (× DDR5) | Projected lifetime @128 GiB (ideal) | Role |
|---|---|---|---|---|---|---|
| DDR5-4800 | 83.1 | 0.797 / 0.0498 | 136.21 | 1.00 | n/a (volatile) | commodity baseline; sets every bar |
| PCM (legacy) | 12,168.2 | 0.046 / 0.0115 | 173.6 | 1.25* | not evaluated | floor-power reference; two service-limited workloads; loses on latency by ~150x |
| 1T1R SLC | 41.4 | 6.939 / 0.8674 | 641.0 | 0.36 | 7.1 yr | most write-symmetric ReRAM track |
| **1S1R SLC** | 36.8 | 6.940 / 0.8674 | 594.5 | 1.24 | 7.1 yr | fastest reader, 3.4x smaller die; conditional on selector quality |
| 1T1R MLC | 44.5 | 6.941 / 0.4338 | 722.8 | 0.73 | 7.1 yr | capacity tier; halves the per-GiB power penalty |
| 1S1R MLC | 37.9 | 6.941 / 0.4338 | 645.4 | 2.47 | 7.1 yr | densest configuration; read-dominant roles only |

Under single-region Start-Gap the same lifetime projection is 23.2 hours, not 7.1 years (Table 5); the
ideal-leveling number above is an upper bound, not the realistic case. Two published-silicon rows (11.9
us / 379 us under GCC) are deliberately excluded from this table; no row here describes a fabricated
part. **Power is comparable only in the per-GiB column** (the modules are 16, 8 and 4 GiB), and both
sides count memory devices only, with no RCD, PMIC, PHY, termination or ReRAM controller (book
Section 3.1.2). **\*** The PCM density figure is a fixed constant in the metrics pipeline with no
device or datasheet source behind it - read it as *not characterized*, like the lifetime cell beside
it. Source: `results/rev2026-09_primary_csv/processed_bar_chart_metrics.csv`,
`processed_geometric_means.csv`.

---

## 2. Method and Pipeline (as it now stands)

- **The pipeline:** NVSim hardware characterization -> JSON extraction (`2_extract_hardware_metrics.py`)
  -> system config generation (`3_gen_nvmain_config.py`) -> cycle-accurate NVMain trace execution
  (`4_execute_simulation.py`) -> `process_metrics.py` -> visualizers, all gated by `mbmm_master.py`
  (unchanged in shape from prior revisions; the Gate-Keeper rule still applies: no simulation data is
  accepted without a complete end-to-end pass).
- **Run provenance, added after the final review (tasks F1/F2):** `mbmm_master.py` writes
  `results/system/run_manifest.json` (`schema: mbmm_run_manifest/1`) at the start of Stage 4, before
  any simulation, recording the run's own flags; `process_metrics.py` carries the same axes into every
  processed CSV as the **`Run_*` columns** (`Run_Channels`, `Run_Decoder`, `Run_Organization`,
  `Run_Queue_Size`, `Run_Freq_MHz`, `Run_Window_ns`, `Run_DDR5_Model`), so a row can no longer be
  read without knowing which sensitivity axis produced it. Both are live in the code as of
  2026-09-21. Four safeguards go with them, so that a folder can never be mislabelled: the manifest
  carries an `expected_stats_files` list and `process_metrics.py` gives the `Run_*` values ONLY to
  stats files on that list (any other file, and every file in a folder whose manifest has no list,
  reads `unknown` with a WARNING; the frozen `results/system_rev2026-09_*` datasets predate the
  manifest and therefore read `unknown`); before Stage 4 the master moves a previous run's stats,
  partial or failed outputs and old manifest out of `results/system` into
  `results/system_previous_<timestamp>/` (never deletes); Stage 3 lists the configs it generated,
  older generated ReRAM configs are moved aside, and Stage 4 refuses any generated model not on this
  run's list; and `4_execute_simulation.py` writes NVMain's output to `<name>.out.partial`, renames it
  to `.out` only on success (`.out.failed` otherwise), and first moves a pre-existing output of the
  same name aside to `.out.superseded_<timestamp>`, so a failed re-run can never leave a
  fresh-looking result behind.
- **Current-mode background-power correction (task F1), and the rule that goes with it:** NVMain 2.0's
  `EnergyModel current` path - which **only the DDR5 configs use** - accumulates each rank's
  `backgroundEnergy` for all its devices but then divides by the device count when converting it to
  power, while activate, burst and refresh are multiplied by it as they should be
  (`Ranks/StandardRank/StandardRank.cpp`, ~line 992). The printed rank `backgroundPower`, and the
  `totalPower` that sums it, therefore carry **one device's** standby draw against the whole rank's
  other three components. **The C++ is deliberately left unpatched** (patching it would invalidate
  `tools/golden/` and force a re-record of the frozen datasets); the correction is applied in
  `process_metrics.py` and surfaced as the **`Background_Power_Device_Factor`** CSV column (4 for
  `DDR5_4800_DRAM_subchannel`, 8 for `DDR5_4800_DRAM_64B`, 1 for every ReRAM and PCM row, which use
  other energy models and never divide). **Rule: never read a rank's `backgroundPower` or its
  `totalPower` raw from an `EnergyModel current` stats file** (recognisable by `mA*t` energy units
  rather than `nJ`) - multiply by the rank's device count (`BusWidth / DeviceWidth`) first. **And
  never read a rank's `totalEnergy` from such a file at all**: in current mode it double-counts one
  device's bank energy. Both quirks are written up as items 6 and 7 of
  `simulators/nvmain/CLAUDE.md`; nothing in the pipeline reads `totalEnergy`.
- **DDR5 config provenance is labelled key by key:** a sweep of the baseline's 36 device and simulator
  keys classifies each into one of **four labels** - 22 JEDEC-sourced, 9 NVMain-specific with no DDR5
  counterpart (three of which can never bind here), 2 parsed but read by no timing code, and 3
  short-versus-long bank-group judgements (tCCD, tWTR, tRRD) taken at the **short**, DDR5-friendly
  value and recorded as judgements rather than transcriptions. `configs/DDR5_4800_DRAM_subchannel.config`
  carries the JESD79-5 table and page number for every value inline, plus the disclosure that the
  tables were read through a third-party mirror and **should be re-verified against an official copy**.
- **Matched array organization:** both cell types forced to 2048 x 2048 subarrays at sense-amp mux 64
  via NVSim's `-ForceBank`/`-ForceMat`/`-ForceMuxSenseAmp`, with an anchored gate that fails the run on
  any mismatch against NVSim's own printed geometry.
- **Module geometry:** ReRAM full DIMM 8 GiB SLC / 16 GiB MLC, 64 x 1 Gb chips, 2 channels x 4 ranks x
  8 devices, 8 banks of 2048 x 1024 sixty-four-byte locations per device. DDR5 baseline 16 GiB, eight
  16 Gb x8 devices, two independent 32-bit subchannels (each its own command bus, 32 banks), 64-byte
  access as a 16-beat burst per subchannel. Every technology accessed at 64-byte granularity.
- **Primary pipeline flags** (the exact invocation that generated Tables 1-5 and Figures 1-27):
  `python3 mbmm_master.py --all --trace gcc_spec2017.nvt lbm_spec2017.nvt stream.nvt gpt2_ifmap.nvt
  alexnet_layer1_ifmap.nvt alexnet_layer1_ofmap.nvt --window-ns 250000000 --ddr5-model
  DDR5_4800_DRAM_subchannel --channels 2 --decoder StartGap --endurance-model RowModel --silicon`
  (120 runs: 4 ReRAM cell tracks x 4 chip-count architectures x 6 traces, plus DDR5, PCM and the two
  silicon configs). Other flags used for sensitivity axes: `--organization {2048,1024}`, `--freq`
  (800/1333/2400 MHz), `--queue-size` (8/32/128), `--models` (scopes `4_execute_simulation.py` only,
  not `mbmm_master.py`'s own `--models`/`--all` path).
- **Trace tools:** `parse_gem5_memctrl.py` (new gem5 MemCtrl parser, provenance sidecar,
  `--cpufreq-mhz 3000 --region o3 --skip-ns 10000000`); `parse_trace.py` (SCALE-Sim parser, fixed to
  keep every address and drop padding markers); `tools/validate_trace.py` (checks monotonic timestamps,
  64-byte alignment, span coverage, reads/writes in window; exit 1 on hard failure). Every trace ships a
  `.sidecar.json` (generator command line, source-log hash, region boundaries, full line accounting).
- **Endurance tools:** `endurance_sensitivity.py` (sweeps endurance rating x capacity x leveling policy
  x write reduction, emits `results/endurance_table.csv`); `tools/aggregate_wear.py` (DIMM-wide wear
  from a stats file: touched locations, total/max/mean writes, hot-spot factor, top 16 locations).
- **Other new/changed tools this revision:** `selector_layer.py` (analytic 1S1R selector bounds: sneak
  leakage, read margin, tile validity, at OTS and FAST bounds; writes `results/selector_layer.json`);
  `tools/nvmain_regress.sh [--record]` (build/regression harness against golden stats, run as PASS x3
  before and after every C++-touching change); `tools/check_live_configs.py` (byte-identity check
  between `configs/*.config` and the live `simulators/nvmain/Config/` copies NVMain actually reads;
  wired into `mbmm_master.py` stage 4, fail-fast).
- **Frozen dataset folders (2026-09 revision):** primary run `results/system_rev2026-09_primary/` (120
  stats files) with CSVs in `results/rev2026-09_primary_csv/`; sensitivity runs each in their own
  `results/system_rev2026-09_<axis>/` for axis in {decoder_default, channels1, channels1_ai, ddr5_64b,
  freq1333, freq2400, queue8, queue128, org1024}; book figures in `results/book_figures_rev2026-09/`;
  deck charts in `results/slide_graphs_rev2026-09/`. The pre-revision dataset is preserved at
  `results/archive_2026-09_pre_revision/`.
- **MLC analytical model:** NVSim's native MLC logic FPEs in `Mat.cpp`'s ISPV sensing; MLC metrics are
  derived from the SLC baseline via four multipliers, both measured on the same EMBER macro across two
  publications (Upton et al. [6], ESSCIRC 2023, for read energy; Levy et al. [31], IEEE JSSC 2024, for
  read latency and both write-side figures): **1.5x read latency, 3.263x write latency, 1.1x read
  energy, 3.0x write energy**.
- **Validation scope, restated:** internal pipeline consistency, not hardware correlation. Inputs are
  anchored to real silicon/vendor datasheets and every repair is verified against device-level output or
  exact arithmetic (0.0% error), but no end-to-end result is checked against a measured ReRAM DIMM or
  instrumented DDR5 system, because no ReRAM main-memory module exists to measure.

---

## 3. Corrected Findings and Their Binding Caveats

- **Latency (ReRAM below DDR5 on CPU traces):** holds at NVSim-projected device timings **only**. Must
  always be read alongside the published-silicon rows (11.9 us / 379 us under GCC, completing 18%/1% of
  LBM) and the write-dominated AlexNet OFMAP burst (DDR5 wins, 234.3 vs. 353.1-652.9 ns). Never state
  the latency win without one of these two counterweights attached.
- **Latency magnitude is an interface assumption, not a device result:** only tRCD + tCAS come from
  NVSim (11.25 ns of the 41.40 ns 1T1R SLC GCC average); the remaining 30.2 ns is NVMain's default
  protocol cycle counts at the assumed 800 MHz clock, which has no ReRAM citation behind it. State the
  direction as robust and the magnitude as model-dependent. The same mapping puts the cell write pulse
  off the request path, so **MLC latencies are lower bounds** and MLC's near-parity with SLC is a
  consequence of this project's generator, never a device finding.
- **Power per GiB (12.7-17.4x DDR5 for SLC, 6.4-8.7x for MLC):** an **upper bound**, not a settled gap.
  DDR5's number carries a real power-down credit; ReRAM's does not (disclosed no-savings placeholder).
  Break-even needs **94.3%** gating at 22nm, which sits *inside* the 94-98% idleness the cited
  web-serving deployment class implies - the band **brackets** break-even (0.36x DDR5 at f = 0.98,
  1.05x at f = 0.94). Never state the power gap as closed or as unclosable; both overclaims are wrong,
  and the parity the band brackets is arithmetic, not a result.
- **Both module power figures are memory-device-only:** no register clock driver, PMIC, PHY,
  termination or ReRAM-side controller on either side. Quote this scope wherever a per-module ratio is
  quoted. A fixed per-module overhead moves the two statements in opposite directions: it *compresses*
  the ungated per-GiB ratio toward an asymptote of 2x, and it *raises* the gating fraction parity needs
  (97.9% at 0.5 W per module; beyond 0.79 W no gating fraction reaches parity at all). Never say an
  overhead helps ReRAM without saying which of the two comparisons is meant.
- **Leakage identical at matched organization:** true for the simulated 2048 x 2048 tile, but 1S1R's
  validity at that tile size is **conditional on selector quality** (invalid at present-day OTS
  quality, valid at the best-published FAST bound). Never cite an 1S1R result without this caveat.
- **Endurance (projected, four leveling policies, 10-year requirement):** every lifetime is a
  **projection**, never "measured". Burst-derived rows (AlexNet OFMAP) must carry their burst-rate
  flag. NVMain's `wearMaxWrites` statistic is a **per-row** total (1024 lines/row) and overstates
  per-cell wear by up to 1024x; never read it as a cell-wear figure.
- **Scaling: channel count moves burst latency; rank depth at most 7.5%, CPU traces only.** Shown by a
  one-channel control run (`results/system_rev2026-09_channels1_ai/`) that collapses the 8/16/64-chip
  points onto one latency for the two AI read bursts. Static power and capacity scale exactly linearly
  with chip count (108.384 mW/chip to six digits); latency for the three CPU traces barely moves at all
  (6.4-10.4% across physically realizable points, no monotonic trend) because they are offered-rate
  limited, not device limited.
- **End-to-end latency is the saturation measure**, not total latency: total latency cannot see time a
  request spends waiting to be admitted, so under a saturated configuration (PCM, either silicon row)
  it stays flat while the real backlog (visible only in end-to-end latency) grows without bound.
- **Sensitivities run this cycle, each with its own scope:** interface clock (800/1333/2400 MHz: 2.2x on
  CPU traces, 1.7-1.8x where the queue binds, zero effect on static power); queue depth (8/32/128: zero
  effect on CPU traces, opposite-direction movement of total vs. end-to-end latency on the write burst);
  channels (1 vs. 2: isolates the 1.68x AI-burst gain to the second channel); DDR5 64B cross-check
  (79.6 vs. 83.1 ns under GCC and 75.9 vs. 78.3 under LBM, a 3-4% difference, but **3.4x faster in the
  controller and 3.3x end to end** on the dense AlexNet write burst; it is a **legacy-shape reference,
  not a JEDEC DDR5 configuration** - a 64-bit channel serving a 64 B line in 8 beats is a DDR4 shape
  DDR5 does not offer, and it holds tCCD at 4 cycles, below the 8-cycle JEDEC floor - so its speed
  advantage is an optimistic upper bound and the two-subchannel model stays the primary baseline);
  array organization 1024 x 1024 (faster device,
  larger die, ~2x leakage vs. 2048 x 2048; module gains 4-10% latency but pays 14.3 W vs. 6.9 W).

---

## 4. Withdrawn Wordings: Do Not Reintroduce

These phrasings appeared in earlier drafts of the 2026-09 revision and were walked back during review.
None should be used again, even as a paraphrase, without the correction attached:

- **"Channel count is the only latency lever."** Wrong: the interface clock (2.2x on CPU traces) and
  the controller queue depth (1.6x end-to-end on the write burst) are separate, independently measured
  levers. The book's actual claim is narrower: among the *module-organization* choices the chip-count
  matrix varies (chips, ranks, channels), channel count is the one that moves burst latency.
- **"Rank depth bought nothing."** Wrong on the CPU traces: rank depth is worth up to 7.5% there (a
  fall in the device component of latency across the 16-to-64-chip step). It bought exactly nothing
  only on the three AI traces, because their footprints never leave one rank.
- **"No gating fraction closes it."** Wrong: the arithmetic does not forbid parity for the web-serving
  deployment class Malladi et al. describe - break-even (94.3%) sits *inside* that class's 94-98%
  idleness band, and the band brackets it. What is true is narrower: this book cannot *claim* the gap
  is closed, because no citable ReRAM power-gating energy characterization exists to price a gated
  module with.
- **"PCM beats every ReRAM track" as a headline.** Only true at module level and only with three
  attached caveats: two of PCM's six workload terms are service-limited completions (lower bounds), its
  module is 4 GiB against ReRAM's 8-16 GiB, and per gigabyte the ordering reverses against MLC ReRAM
  (PCM 5.1x DDR5 vs. 1S1R MLC's 4.7x).
- **"Modeled strictly after JESD79-5"** (of the DDR5 baseline). Withdrawn in favour of a scope
  sentence: the baseline is JEDEC-sourced *with three documented, DDR5-friendly short-versus-long
  choices* (tCCD, tWTR, tRRD) and a handful of NVMain-specific keys, on values transcribed through a
  public mirror that should be re-verified. See the four-label provenance in Section 2.
- **"40 to 55x DDR5 power per GiB"** (and the 20-27x MLC companion). Retired with the background-power
  correction: the figures are **12.7 to 17.4x** for SLC and **6.4 to 8.7x** for MLC, and they are
  upper bounds.
- **"Break-even needs 98.2% of the static component gated."** Retired with the same correction: it is
  **94.3%** at 22nm (80.8% at a 12nm-class port), which lands *inside* the cited idleness band instead
  of above it. Any sentence built on 98.2% has the direction of the power argument backwards.
- **"MLC is barely slower than SLC"** stated as a device finding. Wrong as a device claim: it is a
  consequence of this project's own configuration generator, which books NVSim's write latency as tWR
  and leaves tWP at zero, so the cell write pulse never reaches request latency. The MLC latencies are
  **lower bounds**; with the write pulse on the request path a 1T1R MLC write would cost about 63 ns
  instead of 13.75. The MLC write penalty surfaces as endurance and energy per write instead.
- **"A per-module overhead moves break-even in ReRAM's favour."** Wrong, and it inverts the argument.
  A fixed overhead added to both sides *compresses the ungated per-GiB ratio* (a ratio of totals,
  falling toward 2x) but *raises the gating fraction parity requires* - 97.9% at 0.5 W, no parity at
  all beyond 0.79 W - because 8 GiB of ReRAM carries the same overhead as 16 GiB of DDR5. The first
  flatters ReRAM, the second does not, and the two must never be conflated.

---

## 5. Simulation-Fidelity Audit (fourteen items, thirteen repaired)

A systematic audit of the NVSim-to-NVMain flow (book Section 3.1.6) found fourteen silent failure
modes across the ReRAM configurations, the metrics pipeline and both non-ReRAM baselines. Items 1-11
were the pre-2026-09 repairs (mixed-clock-domain PDP, dead `StandbyPower` config, generic
standby-energy defaults, single-rank power reported as system power, disabled power-down state machine,
weak trace provenance, unrescaled DDR3-era DDR5 refresh, NVMain-default DDR5 supply voltage/uncalibrated
IDD, PCM running at 2x its cited clock, dead ReRAM access-energy config keys, heterogeneous host-CPU
frequencies). This revision added:

- **Item 12 (fixed):** DDR5's tCAS/tRCD/tRP (34-34-34 cycles) was an unsourced placeholder; corrected
  to 40-39-39 via SK hynix's public DDR5-4800 speed-bin decoder. DDR5 total latency rose 2.3-8.6% across
  the suite; power unaffected.
- **Item 13 (fixed):** the double-count in the read path (full device read latency billed into both
  tRCD and tCAS) is the single largest correction of this revision; the generator now splits it so
  tRCD + tCAS sums to the device read latency.
- **Item 14 (fixed):** trace regeneration. All gem5 traces rebuilt from scratch (L1/L2 caches, documented
  region, 10 ms warm-up discard, exact reconciliation with gem5's own request counters); SCALE-Sim
  parser fixed to keep every address instead of one-per-row and drop padding markers instead of writing
  them in as addresses; STREAM switched from a hand-written synthetic stand-in to the real benchmark.
  **The one item not repaired**, and the sole disclosed permanent limitation on this list: the GPT-2
  trace's original SCALE-Sim generator configuration was never preserved, so it is a representative
  parallel-read pattern, not a validated GPT-2 capture (AlexNet's TPU-v1 256x256 output-stationary run
  is confirmed and reproducible).

**Two further DDR5 defects were found AFTER this audit list had been closed** (tasks F1 and F4,
2026-09-21) and are therefore *not* items of it; they are recorded in the book's Appendix A under
"DDR5 Timing and Power Corrections of This Revision". (a) The current-mode background-power accounting
described in Section 2 above, which had DDR5 static power 4x too low; corrected in post-processing to
a static 0.724 W inside a 0.797 W module total under GCC, with the sanity bound that the uncorrected
figure sat *below* the 0.412 W floor the configuration's own EIDD2P0 current allows. (b) The DDR5
write path, power-down path and activate window, still DDR3-1333 template cycle counts, now taken from
JESD79-5 for the DDR5-4800 bin (tCWD 7->38, tWR 10->72, tRTP 5->18, tWTR 5->6, tPD and tXP 6->18,
tRRD 5->8, tFAW 20->32), raising DDR5's average total latency by 6.4 to 47.5% across the six traces
while moving module power by at most 3%. **Both move DDR5 only**: every ReRAM and PCM row is
byte-identical before and after, which is itself the check that they are confined to where they
belong. Regression coverage lives in `tests/test_ddr5_jedec_timings.py`.

Note: the item numbering above (12-14) is this context file's own grouping of "what changed this
cycle" for readability; the book's own Section 3.1.6 numbers these as items (12), (13) and (14) too,
but with different content boundaries (its item 13 is the first MLC-multiplier correction round, and
its item 14 is a second, independent fix to that round's own read-latency figure). Consult the book
directly for the authoritative item-by-item text before citing a specific number to a specific item.

Idle-power gating (`MemoryController::HandleLowPower()`), previously disabled in source and an open
item in the 2026-08-22 predecessor of this file, has been **restored** and is live for every
technology: DDR5 realizes real, JEDEC-backed savings from it; ReRAM's power-down energy remains a
disclosed no-savings placeholder (no ReRAM figure claims a gating benefit); PCM shows no power-down
activity at all (plausibly its `FRFCFS-WQF` write-queue-flush controller keeps its queue non-empty,
starving the power-down entry condition; not yet root-caused to full confidence).

---

## 6. Known Limitations and Open Items

1. **GPT-2 trace provenance** (Section 5 above): unconfirmed generator configuration; treated as a
   representative pattern, not a validated model trace.
2. **ReRAM power-down energy is a disclosed no-savings placeholder**, not a real characterization: no
   NVSim datapoint splits ReRAM leakage into gatable-periphery vs. ungatable-crossbar, and no citable
   ReRAM power-gating figure exists in the literature searched. It is what stops the book pricing a
   gated ReRAM module at all, and therefore what keeps the bracketed gated parity of Section 3 an
   arithmetic statement rather than a result - but with the corrected DDR5 baseline it is **no longer
   the item on which the power verdict turns** (book Sections 3.3 and 4.1).
3. **DDR5 IDD figures are vendor specification limits, not measured typicals**; no typical-current
   datasheet column was found for either vendor checked. A typical-current module would sit *below*
   the figures used here, widening rather than narrowing the ReRAM power deficit.
4. **Open-loop trace replay**: no CPU/accelerator feedback path, so every latency figure is a
   memory-subsystem quantity, not a projected end-to-end application slowdown.
5. **mcf is parked**, not evaluated: gem5 panics inside the benchmark's own input reader ~0.13 ms into
   the detailed region on both the March and September attempts. Needs a rebuilt benchmark binary from
   the Lead and a new, explicit SPEC2017 access grant; the launch script
   `benchmarks/raw_logs/mcf/run_mcf.sh` is ready, but there is currently no grant in force
   (`/home/yuvalk/CLAUDE.md` and `/home/yuvalk/MBMM/CLAUDE.md` both close the 2026-09-18 exception as
   of 2026-09-20).
6. **The ReadVoltage sensitivity sweep (Figure 19, book Section 3.1.5) was not re-run** at either the
   power-model repair or the matched 2048 x 2048 organization; its absolute numbers (32.13 ns read
   latency, <4% PDP movement) belong to the pre-revision dataset and are not comparable to Tables 2-5.
   Its qualitative conclusion (read-latency invariance, small PDP movement) is argued to survive a
   fortiori, since static power's share of the module total is now 99.96%, but this has not been
   measured at the current organization.
7. **All endurance figures are projections from a measured write distribution**, never measured
   lifetimes; wear-leveling policies (Start-Gap, randomized Start-Gap) are modeled analytically, not
   simulated end to end (a 250 ms window completes ~10^-5 of one whole-module Start-Gap rotation, so
   the simulator cannot show leveling actually working within any feasible window).
8. **Density projections beyond 22nm (16nm/12nm columns of Table 6) are bounding geometry, not
   measurements**, and are linear in the assumed cell area, which is itself an assumption (20F² for
   1T1R, 4F² for 1S1R) rather than a measured value; a factor-of-two miss on cell area would drop
   22nm SLC 1S1R below DDR5 parity.
9. **No known active blocking bug** in the pipeline itself as of this hardfork.

---

## 7. Where Things Live

- **Book (source of truth):** `documents/MBMM_Book_Typst/Project_Book.typ` (105 pages, compiles clean).
  Key sections: Abstract; 1 Introduction; 2 Infrastructure & Methodology; 3.1.1-3.1.6 latency/power/PDP
  /endurance/robustness/fidelity-audit; 3.2 scaling; 3.3 global viability; 4 Conclusion & Future Work;
  Appendix A (simulation parameters and literature grounding); Appendix B (pipeline CLI); Appendix C
  (reproducibility); Appendix D (what changed since 3 September, the only place old headline values are
  tabulated).
- **Revision tracker:** `documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md` (task list plus dated
  session log; source for the operational facts, pipeline flags and folder names in Section 2 above).
- **Orchestration:** `mbmm_master.py` (7-stage ETL, the Gate-Keeper).
- **Config generation:** `3_gen_nvmain_config.py`, `1_run_nvsim_hardware.py`,
  `2_extract_hardware_metrics.py`; forced-organization configs `configs/reram_22nm_*_slc.cfg` (+
  `_1024` variants); DDR5 configs `configs/DDR5_4800_DRAM_subchannel.config` (primary) and
  `configs/DDR5_4800_DRAM_64B.config` (cross-check); stale `configs/DDR5_4800_DRAM.config` (34-34-34,
  never read by the pipeline) deleted this revision.
- **Metrics/post-processing:** `process_metrics.py`, `visualize_results.py`, `visualize_pareto.py`,
  `visualize_hero_graphs.py`, `visualize_slides.py`, `logging_config.py`.
- **Selector layer, endurance, regression, config-liveness:** `selector_layer.py`,
  `endurance_sensitivity.py`, `tools/aggregate_wear.py`, `tools/nvmain_regress.sh`,
  `tools/check_live_configs.py`, `tools/validate_trace.py`.
- **Trace parsers:** `parse_gem5_memctrl.py`, `parse_trace.py`.
- **Results:** see Section 2's "Frozen dataset folders" bullet for the full 2026-09 layout;
  `results/archive_2026-09_pre_revision/` preserves the pre-revision dataset for diffability.
- **Correction-round backups (2026-09-21):** each of the three post-final-review rounds snapshotted the
  artefacts it was about to regenerate, with the round's tag appended - `*_before_F1` (the
  background-power correction), `*_before_F4` and `*_before_F4b` (the DDR5 JEDEC timing rounds). They
  exist for `results/rev2026-09_primary_csv`, `results/_live_csv`, `results/book_figures_rev2026-09`,
  `results/slide_graphs_rev2026-09`, `results/final_graphs` and the per-axis sensitivity folders
  under `results/system_rev2026-09_*`. Use them to diff what a round actually moved; the unsuffixed
  folder is always the current one.
- **DDR5 timing regression test:** `tests/test_ddr5_jedec_timings.py` (guards the JESD79-5 DDR5-4800
  write-path, power-down and activate-window values in both DDR5 configs against regression).
- **Subdirectory CLAUDE.md files** (domain knowledge, still the right first stop before reading source):
  `simulators/nvsim/CLAUDE.md`, `simulators/nvmain/CLAUDE.md`, `configs/CLAUDE.md`.
- **Deck / one-pager:** `documents/MBMM_Book_Typst/presentation_deck.html` (rebuilt this cycle on the
  corrected book: 60 slides, 15 data-driven charts from `visualize_slides.py`, guarded by
  `tests/test_presentation_deck.py`; outline in `Presentation_Outline.md`); `Shahar_Review_Evidence.typ`/`.pdf` (one-pager, rewritten and
  reviewed this cycle); `Note_to_Shahar_2026-09.md` (drafted, reviewed, not sent).

---

## 8. Operating Rules for AI Assistants on This Project (carried forward, updated where facts changed)

- **Every number cited about this project's results must trace to `Project_Book.typ` (the 2026-09
  revision) or to a file it cites** (a `results/rev2026-09_*` CSV, `results/system_rev2026-09_*` stats,
  a `.sidecar.json`), never to memory or to a prior version of this context file.
- **Projected endurance figures are projections, never "measured".** Say "projected lifetime" or
  "required endurance", not "measured lifetime" or "the cell survives X years".
- **Never state a 1S1R result without its selector-quality conditional attached**, and never state a
  latency-win result without one of its two counterweights (published-silicon timings, or the
  write-dominated AlexNet OFMAP trace) attached.
- **Never cite the withdrawn wordings of Section 4** above, even loosely paraphrased, without their
  correction.
- **`mbmm_master.py` remains the Gate-Keeper**: no Python modification affecting simulation output is
  considered verified until run through it (per `/home/yuvalk/MBMM/CLAUDE.md` guardrail 2).
- **SPEC2017 quarantine is back in full force** as of 2026-09-20: do not read, list, search or modify
  anything under `/home/yuvalk/spec2017/`. The 2026-09-18 exception closed when the regenerated gcc and
  lbm traces were validated and accepted; mcf remains parked and needs a fresh, explicit grant.
- **No em-dashes anywhere this project's assistants write** (project-wide style rule, independent of the
  book's own typography).
- **Git discipline** (per `/home/yuvalk/MBMM/CLAUDE.md` guardrail 1): no `git commit`/`git push`/history
  changes on `main`/`master` or any branch other than a Lead-confirmed `autoresearch/<tag>` branch; the
  Lead Researcher handles all commits and pushes everywhere else, always.

---

## 9. Recent History (this cycle)

The 2026-09 revision replaced the entire "3 September" dataset: regenerated traces (gem5 and
SCALE-Sim), a matched 2048 x 2048 array organization for both cell types, a corrected DDR5
subchannel/64-byte baseline, a corrected read-latency double-count, a corrected endurance rating basis
and four-policy wear-leveling projection, a restored idle-power-gating mechanism, an analytic 1S1R
selector layer, and a full sensitivity suite (organization, interface clock, queue depth, channels,
DDR5 granularity). The book was rewritten end to end (105 pages, compiles clean, Appendix D added as the
single place retired values are tabulated) and re-reviewed (13/13 number mismatches fixed in the final
pass). The deck was rebuilt on the corrected book (T6.2) and this file regenerated (T6.4) in the same
cycle.

A **final internal review on 2026-09-21** then found two more defects, both at the source of the DDR5
data, and three follow-up tasks repaired them and propagated the result. **F1** corrected NVMain's
current-mode background-power accounting in post-processing (DDR5 static power had been 4x too low),
added the `Background_Power_Device_Factor` CSV column and wrote the two upstream quirks up as items 6
and 7 of `simulators/nvmain/CLAUDE.md`; **F2** added the run-provenance manifest and the `Run_*` CSV
columns; **F4** (in two rounds, F4 and F4b) brought the DDR5 write path, power-down path and activate
window to JESD79-5 DDR5-4800 and re-simulated DDR5, with `tests/test_ddr5_jedec_timings.py` guarding
the values. Together they moved every DDR5 latency, power, PDP and ratio in the book - and reversed
the direction of the power argument, since break-even now sits inside the cited idleness band rather
than above it - while leaving every ReRAM and PCM figure byte-identical. **F3** then brought the
downstream documents into line with the corrected book: F3a the book's own dependent text, and F3c
(2026-09-21) the one-pager `Shahar_Review_Evidence.typ`, the draft `Note_to_Shahar_2026-09.md` and
this context file.

Earlier session history (Sessions 1-26, the 2026-07-22 fidelity audit, the
2026-08-16/08-22 bibliography-verification cycles that produced the *previous* hardfork of this file)
is preserved in `archive/root_docs/MBMM_AI_Context_State_pre-hardfork_2026-08-16.md` and
`archive/root_docs/MBMM_AI_Context_State_pre-hardfork_2026-09-20.md` (this file's immediate
predecessor) and is not restated here, since the 2026-09 revision supersedes essentially everything
those sessions established about the book's numbers.

---

*Document regenerated via a hardfork task (T6.4) from: `documents/MBMM_Book_Typst/Project_Book.typ`
(the 2026-09, compile-verified, corrected revision) and
`documents/MBMM_Book_Typst/Revision_Workflow_2026-09.md` (operational facts: pipeline flags, dataset
folders, tool names, the mcf parking note). Cross-referenced against the immediately prior version of
this file, now archived at `archive/root_docs/MBMM_AI_Context_State_pre-hardfork_2026-09-20.md`.*
