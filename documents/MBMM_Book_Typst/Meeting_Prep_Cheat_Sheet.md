# Meeting Prep Cheat Sheet - hard questions and the answer's book location

Personal rehearsal notes for the deck at `presentation_deck.html` (60 slides, rebuilt 2026-09-20
on the corrected 2026-09 dataset). Not part of the book's fix tracker.

> **Rewritten 2026-09-20 (T6.2).** Every answer below is checked against `Project_Book.typ` as it
> now stands. The pre-revision answers are not preserved here: they are tabulated properly, with
> their causes, in the book's Appendix D and on the deck's change-log slides, 55 to 60.

## The three sentences to have ready before anything else

1. **Latency.** At NVSim-projected device timings the modeled ReRAM DIMM is faster than DDR5 on
   five of six workloads, 41.4 ns (1T1R SLC) and 36.8 ns (1S1R SLC) against 83.1 ns under GCC. At
   published silicon timings the same module is 11.9 us and 379 us. Both are true, and the second
   bounds the first. (§3.1.1, Table 2; slides 23 and 24.)
2. **Power.** 6.94 W for 8 GiB, 99.96% of it static, which is 12.7x to 17.4x DDR5 per gigabyte. The
   central negative result, and an upper bound. (§3.1.2, Table 3; slide 31.)
3. **Endurance.** Every lifetime here is a projection from a write distribution measured per
   location. Wear leveling decides viability, not the cell: 38.6 years ideal against 7.7 hours
   with none, under GCC. (§3.1.4, Table 5; slide 38.)

## What this revision withdraws

Say these before being asked. They are the reason the revision exists.

- **The leakage gap between the two access devices.** It was an array-organization artifact: the
  cells had been characterized at unequal column muxes. At a matched organization NVSim gives them
  identical leakage, 108.384 mW per 1 Gb chip. (§3.1.2; Appendix D.)
- **"The selector lives longer."** Withdrawn. The apparent difference was the slower configuration
  completing fewer writes inside a service-limited window. All four tracks now wear identically.
  (§3.1.4; Table 7 note.)
- **The chip-count scaling story.** Reversed by the data: channel count, not rank depth, is what
  moves burst latency, shown by a one-channel control run. Rank depth is worth at most 7.5%, only
  on the three CPU traces, and exactly nothing on the three AI traces. (§3.2.)

## The likely hard questions

**"Your DDR5 power was four times too low yesterday. Why should I trust it now?"**
Because it is now checked against three things it was not checked against before, and the defect is
understood rather than patched around. NVMain's current-mode energy model accumulates a rank's
background energy for all its devices and then divides by the device count when converting to power,
while activate, burst and refresh power are multiplied by it as they should be. That is upstream
code from 2014, internally self-consistent, which is why the pipeline's own power-reconciliation
residual could never see it. Three checks now bound the corrected figure: the configuration's own
lowest standby current (EIDD2P0, 46.87 mA at 1.1 V across eight devices) puts a **0.412 W floor**
under the module, and the uncorrected figure sat *below its own floor*; the correction factor is
derived from the run's own configuration (BusWidth / DeviceWidth = 4) and cross-checked against
NVMain's printed "Creating N banks in all D devices" line; and the rank's background-energy counter
reproduces it independently. It is corrected in **post-processing**, so the simulator's source and
its printed statistics are untouched and the correction is reproducible from the frozen stats.
Every ReRAM and PCM row is byte-identical before and after, which is itself the check that it is
confined where it belongs. (Appendix A, "DDR5 Timing and Power Corrections of This Revision";
Appendix D rows 26 and 27.)

**"What about the RDIMM overhead? A real module is not 0.797 W."**
Correct, and the book says so wherever the ratio appears. Both sides count **memory devices only**:
no register clock driver, power-management IC, PHY, termination, SPD hub, or on-DIMM ReRAM
controller. Two consequences that point in *opposite* directions, and they must be kept apart. A
fixed per-module overhead added to both sides **compresses the ungated per-gigabyte ratio** (a ratio
of totals; 17.4x falls toward an asymptote of 2x as the overhead grows) - that flatters ReRAM. And
it **tightens the gated comparison**, because the same overhead is carried by 8 GiB of ReRAM against
16 GiB of DDR5, so the break-even gating fraction *rises*: 94.3% at zero, 97.9% at 0.5 W per module,
and beyond 0.79 W no gating fraction reaches parity at all - which is below any plausible
register-plus-PMIC figure. The second is the one the parity argument depends on. (§3.1.2, §3.3.)

**"Is 800 MHz doing the work in your latency result?"**
Partly, and the deck says so on the slide. Of the 41.4 ns 1T1R SLC average only **11.25 ns** is
NVSim device time, charged once as tRCD + tCAS; the other 30.2 ns is NVMain's default protocol cycle
counts (tCWD, tRTP, tXP, tPD, tWTR, tBURST, tCCD) at an 800 MHz interface that has **no ReRAM
citation** behind it. So roughly three quarters of the ReRAM figure is an interface assumption, and
the same is true in the other direction of DDR5, whose protocol timings are JEDEC's. The
**direction** is robust: ReRAM is below DDR5 at all three clocks measured (41.4 / 27.9 / 19.0 ns at
800 / 1333 / 2400), and it stays below the *corrected, slower* DDR5. The **magnitude** is
model-dependent: read 41.4 against 83.1 as the outcome of one clock choice, not as a device ratio.
(§2.3, §3.1.1.)

**"Is your DDR5 really JEDEC?"**
JEDEC-sourced, with a stated scope rather than a blanket claim. A key-by-key sweep labels the
configuration's 36 device and simulator keys: 22 JEDEC-sourced, 9 NVMain-specific with no DDR5
counterpart (three of which can never bind here), 2 parsed but read by no timing code, and **3
short-versus-long judgements** - tCCD, tWTR and tRRD, where NVMain keeps one rank-wide value and
JEDEC splits by bank group; the *short* value is used, which is the DDR5-friendly choice. Two
further disclosures: the values were transcribed from a public mirror rather than an official copy
of the standard and should be re-verified against one; and NVMain charges tRRD and advances its
four-activate window on every *refresh* as well as every activate, which JEDEC does not do for an
all-bank refresh, making the baseline slightly pessimistic. The earlier "to the letter of JESD79-5"
claim is withdrawn. (§2.3.)

**"Why is MLC not slower than SLC?"**
Because of a mapping choice in this project's own configuration generator, not because of device
physics and not because of anything NVMain does on its own. The generator books NVSim's write
latency as **tWR**, the write *recovery* time, and leaves NVMain's write-pulse parameter tWP at its
default of zero. tWR blocks the bank after the burst finishes; tWP would sit on the request's own
completion path. With tWP zero a write retires after tCWD + tBURST = 13.75 ns on *every* track, so
the cell write pulse that distinguishes MLC from SLC (49.79 against 15.26 ns for 1T1R) never reaches
request latency. **The MLC latencies are lower bounds**, and "MLC is barely slower" is a consequence
of this book's mapping. With the pulse on the request path a 1T1R MLC write would cost about 63 ns
instead of 13.75. What the tWR mapping does capture is bank occupancy, which the banks absorb at
five of these six traces' request rates. (§3.1.1.)

**"Your ReRAM is faster than DDR5. Do you believe that?"**
As a statement about the projected array core, yes, and it is arithmetic: a DDR5 row miss pays
tRCD plus CAS, 16.25 + 16.67 ns at 2400 MHz, then senses and restores a capacitor; a 2048 x 2048
ReRAM subarray reads in 10.12 ns with no row to precharge. As a statement about anything
purchasable, no, and that is why the two SILICON rows run on every trace. (§3.1.1; slides 23, 24.)

**"What changed to make the latency a third of what it was?"**
Three corrections compounding: the generator wrote the full device read latency into *both* tRCD
and tCAS, so every read was charged twice; the traces were regenerated, removing a fourfold record
duplication and moving the window out of each benchmark's start-up burst; and the organization was
matched. (§3.1.1; Appendix D; slide 15 and slide 57.)

**"Did you show the wear leveling actually working?"**
No, and the deck says so. With one whole-module region and one gap move per 100 writes, a 250 ms
window completes about 10^-5 of one rotation, so the decoder's statistics are identical on and off.
The claim is carried by the projection instead, whose model was validated against a write-by-write
simulator to within 0.3%. (§3.1.4; Appendix D; **slide 52**.)

**"Start-Gap is a published, proven scheme. Why does it fail here?"**
It does not fail as a mechanism; it fails against these write distributions. Rotating the gap once
through a 64 GiB module of 1.07 billion lines takes about 10^11 writes, while the hottest line in
these sparse footprints exhausts its 10^6-cycle budget after about 10^6. The hot line dies long
before relief arrives. Qureshi's reported 97% of ideal was obtained against a very different
distribution. Randomizing the region assignment recovers part of it. (§3.1.4; slide 39.)

**"A bigger module should last longer."**
Under ideal leveling it does. Under a single whole-module Start-Gap region it can be *worse*,
because the rotation period grows with the region while the gap still advances one line per hundred
writes: projected under *randomized* Start-Gap, LBM falls from 0.22 years at 8 GiB to 0.20 at 64
and 0.05 at 128. With no leveling, lifetime is set by the hottest line and is independent of module
size. (§3.1.4, Table 5 note.)

**"What endurance would a cell actually need?"**
For a ten-year life at 64 GiB: 2.6e5 (GCC), 2.8e6 (LBM) and 2.3e6 (STREAM) under ideal leveling,
and 6.3e6, 6.5e6 and 4.3e6 under randomized Start-Gap, against a best-sourced production planning
value of 10^6. So GCC clears it; the streaming workloads need 2.3x to 2.8x the rating under ideal
leveling and 4.3x to 6.5x under randomized Start-Gap. (Table 5; slide 40.)

**"Where does the 10^6 rating come from, and what happened to 10^7?"**
10^6 is cited to Chen, IEEE TED 2020 [47], with 10^4 and 10^7 carried as bounds. The 10^7 SLC /
10^6 MLC pair used in earlier versions was cited to a reference that gives no SLC or MLC rating at
all; that citation has been withdrawn. (§3.1.4; Appendix D.)

**"The power number is enormous. Is it fair?"**
It is deliberately unfair to ReRAM. DDR5 realizes its JEDEC power-down credit while ReRAM's
power-down energy is an explicit no-savings placeholder, so every per-gigabyte ratio is an upper
bound. What can be stated is the threshold: break-even needs 94.3% of the static component gated at
22nm, 80.8% at a 12nm-class port, and that now sits **inside** the 94 to 98% idleness implied by the
2 to 6% memory-bandwidth utilization Malladi et al. report for web serving [21]. The band therefore
**brackets** parity: 0.142 W against DDR5's 0.399 W at the idle end, 0.419 W at the busy end. What
cannot be stated is a gated ReRAM number, because no measured ReRAM power-down energy exists, so
neither parity nor its impossibility is demonstrated. And the device-only scope cuts against the
bracketed parity: a per-module overhead raises the required fraction to 97.9% at 0.5 W and removes
parity entirely beyond 0.79 W. (§3.1.2; slides 31, 32.)

**"MLC looks better per gigabyte. Should you recommend it?"**
Only for read-dominant roles. MLC halves the per-gigabyte power penalty purely because leakage is
per chip and MLC puts twice the capacity behind the same chips. But on the write-dominated burst
1S1R MLC degrades 5.0x against its own read stream, and its write energy is 3.0x. (§3.1.1;
Table 3; slide 27.)

**"Why is PCM ahead on power-delay product?"**
At module level it is, and the book declines to make that a headline for three stated reasons: two
of its six workloads are service-limited so its PDP averages a completed prefix and is a lower
bound; its power constants are inherited from the NVMain configuration and were never run through
this project's NVSim pipeline; and per gigabyte MLC ReRAM is ahead of it. It also loses on latency
by two orders of magnitude. (Table 4 note; slide 33.)

**"Which number do you trust least?"**
The three AI results, and say why without hedging: they are microsecond bursts (2.2, 60.5 and
4.5 us) inside a 250 ms window, they are queueing measurements rather than device measurements, and
the GPT-2 trace's original SCALE-Sim configuration was never preserved, so it stands as a
representative parallel-read pattern rather than a validated capture. The AlexNet traces *are*
attributed: they reproduce byte for byte from a known TPU-v1 256x256 output-stationary run.
(§3.1.6 item 6; §2.4; slide 21.)

**"Fourteen bugs, thirteen repaired. Which one did you not fix?"**
Item 6's trace provenance, and only one part of it: the GPT-2 trace's original SCALE-Sim generator
configuration was never preserved and cannot be recovered, so that trace stands as a representative
parallel-read pattern rather than a validated capture. Everything else in item 6 *was* repaired this
revision, and the traces were regenerated from scratch. Do not name item 8 here: it counts among the
thirteen repaired, and its residual caveat is only that DDR5's IDD currents are vendor specification
limits, because no vendor publishes a typical figure to use instead. (§3.1.6 items 6 and 8; slides
19 and 50.)

**"Is this validated?"**
Internal consistency only: NVMain reproduces NVSim's own numbers to 0.0% error and every audit
repair is checked against a device-level anchor or exact predicted arithmetic. Nothing here is
checked against measured hardware, because no fabricated ReRAM main-memory part exists. Keep the
two claims separate: the device physics is literature-characterized, the system behavior is
simulated. (§2.2; slide 20.)

**"Why 800 MHz?"**
A disclosed modeling assumption with no independent ReRAM-interface citation. It is positioned
between two precedents: twice NVMain's PCM reference basis, and below the DDR4-2666 electricals
that carried DDR-T on shipped Optane DIMMs. A targeted search found no ReRAM PHY rate; the only
datasheet-verified ReRAM chip I/O clocks located (Fujitsu SPI parts, 5 and 10 MHz) run 80x to 160x
slower. And it was quantified rather than left open: 1333 and 2400 MHz were run, worth 2.2x on the
CPU traces at no modeled power cost. (§2.3; slide 29.)

**"Why 64 bytes, and why two channels?"**
64 B for every technology, so granularity is not a confound; a 128 B study found it worse on every
modelable axis and unmodelable in NVMain. Two channels is the matched case against DDR5's two
subchannels, and one channel was run as a control. Channels are formed by splitting ranks, so
one-rank modules (single chip, 8 chips) stay single-channel - which is why the 8-chip bars on the
channel-control slide are identical. (Appendix D; §3.2; slide 35.)

**"Why is there no mcf?"**
gem5 panics inside the benchmark's own input reader roughly 0.13 ms into the detailed region,
identically on two attempts. That is a benchmark-binary fault, not a pipeline fault; recovering it
needs a rebuilt binary. The revision proceeds with six workloads. (§2.4; Appendix D.)

**"Two latency numbers is convenient. Which is the real one?"**
Both, and they answer different questions. Total latency is queue entry to completion and is the
like-for-like device comparison; end-to-end is trace arrival to completion and is the saturation
measure. Where a configuration keeps up they agree to a fraction of a memory cycle. The queue-depth
sweep is the clean proof that the classic metric alone is not safe: a deeper queue *raises* it and
*lowers* the time the workload actually waits. (§3.1.1; slides 18, 28.)

**"You changed the organization to get the result you wanted."**
The organization was matched, not chosen: both cells forced to the same 2048 x 2048 subarray at
mux 64, verified against NVSim's printed geometry on every run. The 1024 x 1024 sensitivity was run
end to end, and the two cells still leak within 2% of each other there, so the conclusion does not
depend on which organization is matched. The 2048 choice is simply the lower-power one. (§3.2;
slide 30 and slide 53.)

## Numbers worth knowing cold

| Quantity | Value | Where |
|---|---|---|
| GCC latency, full DIMM | DDR5 83.1, 1T1R SLC 41.4, 1S1R SLC 36.8 ns | Table 2 |
| Published silicon, GCC | 11,888.5 and 378,763.1 ns | Table 2 |
| LBM completion | DDR5 and all four ReRAM tracks 100% of 5,564,704; PCM 50.2% | Table 2 note |
| AlexNet OFMAP | DDR5 234.3 ns; 1T1R SLC 353.1; 1S1R MLC 652.9; ReRAM loses by 1.51x to 2.79x | Table 2 |
| Device, per 1 Gb chip | read 10.12 / 4.70 ns; write 15.26 / 24.59 ns; leakage 108.384 mW both; area 12.008 / 3.540 mm2 | Table 1 |
| Module power, GCC | DDR5 0.797 W (16 GiB); ReRAM 6.939 W (8 GiB); per GiB 0.0498 against 0.8674 | Table 3 |
| Geo-mean PDP | DDR5 136.21; 1S1R SLC 594.5; 1T1R SLC 641.0 W ns; per GiB 4.7x to 9.4x | Table 4 |
| Density | 1S1R 1.24x / 2.47x; 1T1R 0.36x / 0.73x | Table 6, Table 7 |
| Write rates | GCC 0.88, LBM 9.54, STREAM 7.99 M writes/s | Table 5 |
| Lifetime at 64 GiB, 10^6 | ideal 38.6 / 3.6 / 4.3 yr; none 7.7 / 23.2 / 69.5 h | Table 5 |
| Break-even gating | 94.3% at 22nm, 80.8% at a 12nm-class port; inside the cited idleness band | §3.1.2, §3.3 |
| Selector layer | 0 mW standby; 7.56 / 0.076 mW during an access; OTS tile ceiling 1666 cells | §3.1.2 |
| Interface clock, GCC | 41.4 / 27.9 / 19.0 ns at 800 / 1333 / 2400 MHz | §2.3 |
| Static power by chip count | 0.108384, 0.867072, 1.734144, 6.936576 W | Table 8 note |

## Housekeeping

- Retired values appear **only** on the change-log slides, 55 to 60, and in the book's Appendix D. If one
  surfaces anywhere else, it is a defect.
- Charts regenerate with `MPLBACKEND=Agg python3 visualize_slides.py` into
  `results/slide_graphs_rev2026-09/`. No plotted value and no result number in a chart footnote is
  hardcoded; the only exception is `CITED_CONSTANTS`, a documented table of published figures used
  as footnote context, each with its source named.
- The em-dash character is banned project-wide, including inside chart images; the chart generator
  refuses a footnote containing one.
