// MBMM Project Book - the book: the summary of the whole work, with the references it rests on.
// Extended book (the complete record underneath it): Technical_Report.typ.
// GEN-BEGIN preamble
#let blockquote(body) = block(
  inset: (left: 1.2em, top: 0.3em, bottom: 0.3em),
  stroke: (left: 2pt + luma(160)),
  quote(block: true, body)
)
#set page(paper: "us-letter", margin: 1in, numbering: "1")
#set text(font: ("Liberation Serif", "DejaVu Serif"), size: 11pt, lang: "en")
#set par(justify: false)
#show heading.where(level: 1): set text(size: 16pt)
#show heading.where(level: 2): set text(size: 13pt)
#show heading.where(level: 3): set text(size: 11.5pt)
#show heading: set block(above: 1.2em, below: 0.8em)

#set page(numbering: none)
#align(center)[
  #v(2in)
  #text(size: 20pt, weight: "bold")[Evaluation of 22nm Memristor-Based Main Memory (MBMM) in Commodity DIMM Architectures]
  #v(1em)
  #text(size: 13pt)[Yuval Kogan]
  #v(0.3em)
  #text(size: 12pt)[For Prof. Shahar Kvatinsky]
  #v(0.3em)
  #text(size: 12pt)[October 2026]
  #v(1.5em)
  #text(size: 11pt)[The project book. Extended book, with the complete record: Technical_Report.pdf.]
]
#pagebreak()
#set page(numbering: "1")
#counter(page).update(1)
// GEN-END preamble

= Abstract

Can memristor-based non-volatile memory replace DRAM in a commodity
DIMM at 22nm? To answer that I built a cross-layer simulation pipeline
that carries an NVSim device characterization of transistor-gated
(1T1R) and selector-gated (1S1R) ReRAM, as single-level and multi-level
cells, through NVMain 2.0 on six workload traces at one matched
2048 x 2048 array organization. #strong[Latency:] at projected media
timings the ReRAM DIMM has lower average memory latency than a
DDR5-4800 baseline on the three CPU traces at both ends of the
write-pulse bracket, 41.4 to 48.3 ns for
1T1R SLC and 36.8 to 47.4 ns for 1S1R SLC against 83.1 ns under GCC
(78.2 ns when the baseline runs the same close-page policy as the ReRAM
configurations), and lower in
sustained write throughput on the write-dominated AlexNet output-map
burst, which 1T1R SLC drains in 1.02 ms against 0.49 ms for DDR5 (1.5x
to 3.0x by the queue-dominated average latency), with the counterweight that the identical DIMM built from
published silicon timings averages 11.9 us and 379 us under GCC.
#strong[Power:] per gigabyte the module's power is set by the
periphery transistor class the device model is told to build, not by
the cell: with the low-operating-power periphery of the primary
characterization the SLC module costs 12.7x to 17.4x DDR5, almost all
of it a 6.94 W leakage floor, and with a low-standby-power periphery,
re-run end to end, 0.26x to 0.94x, both device-only point estimates;
nothing in the model or the literature read here says which periphery
a DIMM-class part would carry, so the power axis is open within that
band.
#strong[Endurance:] every lifetime here is a projection, and the wear
leveling rather than the cell decides it, ideal uniform leveling at
64 GiB and 10#super[6] cycles per cell giving 38.6 years under GCC, 3.6
under LBM and 4.3 under STREAM. #strong[Density:] the selector-gated
cross-point reaches 1.24x DDR5’s die-level density as SLC and 2.47x as
MLC, conditional on selector quality (Section 4.2) and on a cell near the
idealized 4F², which fabricated single-layer parts have not reached
(Section 4.5), against 0.36x and 0.73x for the transistor-gated cell, which does
not clear parity at the 20F² cell assumed here, nor at the fabricated
part's 6F². Selector-gated 22nm SLC ReRAM is therefore a density
play with competitive projected latency and a power cost per gigabyte
that the device model leaves open, while the transistor-gated variant
matches it on leakage and loses on area; #emph[neither is a drop-in
DDR5 replacement at 22nm], and what decides that is endurance under
leveling, selector validity at the simulated tile, the error-correction
cost and the absence of any fabricated part near the projected timings,
not power.

= 1. Introduction

== 1.1. Why this question, now

Two pressures meet in commodity main memory. The first is economic. By late 2025
memory vendors had turned their investment toward High-Bandwidth
Memory for AI accelerators, and the resulting supply imbalance across
DRAM and NAND was expected to persist through 2026 #strong[\[1\]]. The second is physical. DRAM's planar
cell is held back by capacitor leakage and short-channel effects, and
commodity DDR5 is fabricated on 10 nm-class DRAM nodes that sit at the
end of the capacitor's scaling roadmap #strong[\[2\]]. A resistive cell
stores its state as resistance rather than as charge, so it has no
capacitor to scale and needs no refresh.

The question this project asks is narrow and practical: can
memristor-based non-volatile memory substitute for DRAM in a standard
DIMM? One constraint shapes every answer to it. Writes physically wear
the cell, so endurance is finite, and any viable DRAM replacement has
to buy its lifetime architecturally rather than from the device.

To answer the question I built a cross-layer simulation pipeline that
carries a device-level 22nm ReRAM characterization from NVSim
#strong[\[3\]] into cycle-accurate system simulation in NVMain 2.0
#strong[\[4\]], and I ran four ReRAM tracks, a JEDEC-sourced DDR5-4800
baseline, a legacy PCM baseline and two published-silicon
configurations against six workload traces. Chapter 2 describes the
pipeline, Chapter 4 reports what it measured.

== 1.2. ReRAM in one page

A memristor cell is a two-terminal metal-insulator-metal stack,
typically an HfOx or TaOx oxide, whose electrical resistance is its
stored state. A programming voltage grows or ruptures a conductive
filament of oxygen vacancies through the oxide, switching the cell
between a low-resistance and a high-resistance state; a read applies a
small sense voltage that leaves the filament undisturbed
#strong[\[5\]]. The filament persists without power, so storage is
non-volatile. Filament formation is stochastic and writes stress the
filament, which is why the resistance targets below are engineering
choices and why endurance is the binding constraint of Chapter 4.

I standardized on a 22nm FinFET low-operating-power node, which is
logic-compatible and has fabricated ReRAM precedent at 22nm, on a
planar process #strong[\[6\]]. It is a deliberately conservative frame: 22nm has
several shrink generations of headroom ahead of it, so the density
figures here are a floor on ReRAM's potential rather than a ceiling.
Cells are calibrated to high resistance targets, $10^5 Omega$ in the
low-resistance state and $10^9 Omega$ in the high, to hold a sensing
margin against IR drop on long bitlines #strong[\[7\]]. The arrays
here are 2048 cells on a side, one doubling past that source's own
1024-cell design point, and the extended book shows the criterion
still holds to within 1%.

In a crossbar, current can flow through unselected cells as well as the
selected one. This sneak-path problem is what separates the two device
structures compared here, and it is the whole of the density argument.
#strong[1T1R] puts a CMOS access transistor in series with each cell,
which eliminates sneak paths completely and costs area: roughly
$20 F^2$ per bit on a transistor-drive-limited estimate, although the
fabricated 16 Gb 1T1R part cited below #strong[\[12\]] reports a
$6 F^2$ array, a difference Section 4.5 carries into the density
verdict. #strong[1S1R]
replaces the transistor with a two-terminal selector whose sharply
non-linear threshold suppresses the sneak current instead, reducing the
cell to an idealized $4 F^2$ #strong[\[8\]]. The selector is therefore
what buys the density, and it is also what the density claim is
conditional on. NVSim models no selector physics of its own, so whether
a 2048-cell tile is actually sneak-path-viable is settled separately,
by an analytic selector layer built on the crossbar read model of
#strong[\[9\]] (Chapter 4): at a present-day ovonic-threshold-switch
quality it is not, and at the best published selector it is.

Each cell type is evaluated at one bit per cell (SLC) and at two (MLC).
MLC puts twice the capacity behind the same chips and pays for it in
write time. NVSim has no multi-level model, so the MLC tracks apply
multipliers derived from the EMBER macro's own published measurements,
1.5x on read latency and 3.263x on write latency
#strong[\[10\], \[11\]].

Two things are worth separating before any number appears. NVSim
produces an array-core projection, and #emph[no fabricated ReRAM part
reads or writes in nanoseconds]. Micron and Sony's 27nm 16 Gb 1T1R part
reads in 2.3 us and writes in 11.7 us #strong[\[12\]]\; SanDisk and
Toshiba's 24nm 32 Gb 1S1R cross-point reads in 40 us and writes in
230 us #strong[\[13\]]. Both are carried through this evaluation as
their own configurations, on the same traces and the same module
geometry, and they appear beside every projected latency. Both are
storage parts accessed a page at a time, so their figures are page-mode
access times rather than media bounds, and the book carries no middle
rung between them and the projection.

The one non-volatile main memory ever shipped is worth naming here for
its vocabulary as much as for its history. #strong[3D XPoint] is the
#emph[media]: a phase-change storage element in series with an Ovonic
Threshold Switch selector, that is, a 1S1R cross-point, announced by
Intel and Micron in 2015, whose device structure matches the stackable
PCM-plus-OTS cross-point Intel had published in 2009 #strong[\[14\]]. #strong[Optane] was the
#emph[product] built on that media, and Intel exited the business in
2022. Optane's published latencies were measured on a
shipped module #strong[\[15\]] and are therefore #emph[device] numbers:
they include a controller, ECC and a DIMM interface. Every ReRAM
latency in this book is a #emph[media] number, produced by a device
model driving a memory simulator. The two are never the same kind of
measurement and are never compared as though they were.

== 1.3. What this book claims, and how to read it

The claim is a balanced verdict, not an advocacy case. Selector-gated
22nm SLC ReRAM is a density play with competitive projected latency and
a power cost per gigabyte that the device model leaves open between two
periphery choices (Section 4.2); the transistor-gated
variant matches it on leakage and loses on area; write endurance is the
binding constraint and wear leveling, not the cell, decides it. The
extended book states the conclusion in one line, and this book keeps
it: #emph[neither is a drop-in DDR5 replacement at 22nm.]

The question is not new, and this book sits in a line of work it
should name. Three ISCA 2009 studies made the architectural case for a
non-volatile main memory with phase-change memory: Lee et al. narrowed
PCM's raw delay and energy deficit through row-buffer reorganization
and partial writes #strong[\[17\]], Qureshi et al. put a small DRAM buffer
in front of a large PCM store #strong[\[45\]], and Zhou et al. attacked
durability with redundant-bit-write removal and row shifting
#strong[\[46\]]. The field's template since has been to hide the write
penalty, level the wear and buy density where latency cannot be
hidden, and its one commercial embodiment, Optane, was discontinued on
cost rather than physics (Section 1.2). For resistive memory the
closest prior work is Xu et al.'s HPCA 2015 study of crossbar ReRAM as
main memory, which characterized the data-dependent RESET latency that
IR drop and sneak current impose on large crossbars #strong[\[47\]]; the
device-to-system pattern this book follows, one cell characterization
carried into a system simulator against a DRAM baseline, is the one
Kultursay et al. set for STT-RAM #strong[\[48\]]. On the system side,
placing pages between near and far memory is the operating system's
job, as Meta's transparent page placement describes #strong[\[49\]], which
is why Section 5.2 treats the far position as a page-placement
question rather than a per-request one. What this book adds to that
line is the matched-organization control, the published-silicon
counterweight beside every projection, and a baseline modeled to the
current JEDEC standard rather than the DDR2 and DDR3 of that
generation.

One caveat governs every latency in this book and is stated here once,
in full, so that later chapters can refer to it rather than repeat it.

#blockquote[
#strong[The projection caveat.] First, every ReRAM timing reported here
is an NVSim projection of an array core, not a measurement of a
fabricated part. Second, the same DIMM built from published silicon
timings instead averages 11.9 us (1T1R) and 379 us (1S1R) under GCC and
does not finish the LBM window at all, completing 18.2% and 1.0% of it.
Third, on the write-dominated AlexNet output-map burst the projected
DIMM is #emph[slower] than DDR5, 353.1 ns for 1T1R SLC and 391.5 ns for
1S1R SLC against 234.3 ns; those are queue-dominated averages under a
saturated controller, and the throughput reading is the same, a burst
drained in 1.02 and 1.14 ms against 0.49 ms (Table 4b). The latency verdict of this book therefore
belongs to a projected device, and every reading of it is incomplete
without its silicon counterweight. A baseline-side condition belongs
beside these three: the DDR5 figures come from an open-page run while
the ReRAM configurations run close-page, and at matched policy the GCC
margin is 1.9 to 2.1 to one rather than two to one (Section 4.1).
]

Two further reading rules follow from the same discipline. Every ReRAM
latency here is a media number in the sense of Section 1.2, and every
Optane or CXL figure quoted in Chapter 5 is a device number. And every
endurance figure in this book is a #emph[projection] from a write
distribution measured inside a simulation window, never a measured
lifetime; the word "measured" is not used of any lifetime.

This is the book: the summary of the whole work, with every reference
it rests on. The extended book, `Technical_Report.pdf`, is the complete
record underneath it: the full methodology, every table in its
uncondensed form, the simulation-fidelity audit, the reproduction
instructions and an appendix recording claim by claim what changed
since the September 3 version. Five statements of that version are
withdrawn, so a reader who saw it knows what not to carry forward:

- the 47x leakage gap between the cell types, an artifact of two
  unmatched array organizations (Chapter 3, lesson 1);

- the DDR5 timing and power figures built on a DDR3-era template and an
  undercounted background power, replaced by JESD79-5 timings and the
  corrected device count (Section 2.3);

- "the selector lives longer", an artifact of a service-limited window:
  all four ReRAM tracks wear identically (Section 4.3);

- the 10#super[7] SLC endurance rating and the 1.09-year LBM lifetime at
  8 GB, replaced by the 10#super[6] planning value and the Table 6
  projections at 64 GiB;

- the statement that the baseline was modeled strictly after JESD79-5,
  now stated as read through vendor transcriptions with three
  documented short-value choices (Section 2.3).

Appendix D of the extended book records each of them, old value
against new.

= 2. Method

== 2.1. The pipeline

No single tool spans the distance from an oxide stack to a DIMM
latency, so I built a pipeline that does. NVSim #strong[\[3\]]
characterizes exactly #strong[one 1 Gb chip]: read and write latency in
nanoseconds, energy per access, leakage and die area.
`2_extract_hardware_metrics.py` pulls those figures into JSON and
applies the MLC penalty model. `3_gen_nvmain_config.py` turns the JSON
into an NVMain configuration, mapping the device read latency once
across tRCD plus tCAS and the cell write latency onto write recovery,
and validating both splits against the rendered configuration text.
NVMain 2.0 #strong[\[4\]] replicates that chip 1, 8, 16 or 64 times,
wraps it in its own controller, decoder and interconnect and replays a
trace against it cycle by cycle. `process_metrics.py` turns the
resulting statistics into the CSVs every table here is drawn from
(Figure 1).

#block(breakable: false)[
#image("media/media/pipeline_architecture.svg", width: 6.5in)
]
#align(center)[#emph[Figure 1: the pipeline end to end. NVMain never
re-touches cell-level physics.]]

`mbmm_master.py` orchestrates the whole sequence. It cleans build
artifacts, recompiles both C++ engines, runs a sanity simulation, then
executes characterization, extraction, configuration generation,
simulation and post-processing as one gated flow: no result is accepted
that did not come through it. It takes the replay window in
nanoseconds and converts it to each technology's own cycle budget from
that technology's own clock, so every configuration replays the same
wall-clock window.

The results in this book come from frozen datasets, not from a live
working directory: a 120-run primary matrix of twenty configurations
against six workloads, plus twelve sensitivity series that each change
one flag or one configuration line, a 1024-organization axis and a one-channel control run. The
write-pulse bounding run and the close-page baseline run carry a
manifest of their flags and provenance columns on every processed row;
the primary matrix and the other series are recorded by their run
logs, the revision tracker and the NVMain command line in every
stats-file header.
The controller's queue depth is one of those axes, and the write-queue
sizing question it answers is reported in Section 4.4. The Python layer
is covered by a test suite, 903 tests at the October 2026 revision,
and by a regression harness that re-runs a fixed
configuration against a stored reference. Both are part of the gate: a
pipeline change is not considered to have worked until the suite, the
harness and `mbmm_master.py` all pass.

== 2.2. Device characterization

Both cell types are characterized at #emph[one matched array
organization], 2048 x 2048 subarrays at a sense-amp column mux of 64,
forced identically for 1T1R and 1S1R and verified against NVSim's own
printed geometry on every run. This is the single most consequential
methodological choice in the evaluation, and Chapter 3 explains why.
Table 1 is the characterization the system simulation inherits.

#strong[Table 1: NVSim device-level characterization per 1 Gb chip
(22nm FinFET LOP, 1.4 V ReadVoltage nominal), at the forced matched
organization of 2048 x 2048 subarrays at sense-amp mux 64.]

#align(center)[#text(size: 10pt)[#table(
  columns: 6,
  align: (col, row) => (auto,auto,auto,auto,auto,auto,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Track]],
    [#strong[Cell size]],
    [#strong[Read lat. (ns)]],
    [#strong[Write lat. (ns)]],
    [#strong[Leakage (mW/chip)]],
    [#strong[Die area (mm²)]],
  ),
  [#strong[1T1R SLC]], [20F²], [10.12], [15.26], [108.384], [12.008],
  [#strong[1T1R MLC]], [20F²], [15.18], [49.79], [108.384], [12.008],
  [#strong[1S1R SLC]], [4F²], [4.70], [24.59], [108.384], [3.540],
  [#strong[1S1R MLC]], [4F²], [7.05], [80.23], [108.384], [3.540],
)]
]

#emph[The one device-level advantage besides read latency that survives
a matched organization is the selector's die area, 3.540 against 12.008 mm² per
1 Gb chip; leakage is identical for both cell types, for the reason
lesson 1 of Chapter 3 gives. The 1S1R rows are uncalibrated against any
fabricated part. Source:
results/rev2026-09\_primary\_csv/hardware\_metrics.json.]

NVSim has no multi-level-cell model, so the MLC rows apply an analytic
penalty on top of the SLC characterization: 1.5x read latency and
3.263x write latency, with twice the capacity behind the same chips.
Both multipliers are derived by the same bandwidth-ratio method from
the EMBER macro's own published measurements, the journal report
#strong[\[10\]] and its conference precursor #strong[\[11\]]\; leakage
and die area are unchanged, because the array is the same array.

The periphery transistor class is a second choice the characterization
makes, and Section 4.2 shows it is the decisive one for power. NVSim
builds the peripheral circuits from one of three ITRS transistor
roadmaps; the primary characterization uses the low-operating-power
(LOP) profile at 350 K, and a second characterization with the
low-standby-power (LSTP) profile, one line changed in each cell
configuration (`configs/reram_22nm_*_slc_lstp.cfg`), was run end to end
as a sensitivity series in the October revision. It cuts the chip's
peripheral leakage from 108.384 to 1.599 mW, raises the device read
time by 5% (10.12 to 10.60 ns for 1T1R, 4.70 to 4.97 ns for 1S1R) and
leaves the die area within 0.3%. No fabricated ReRAM die located gives
a leakage figure that would choose between the two.

== 2.3. Baselines

#strong[DDR5-4800.] The primary baseline is a conventional 16 GiB
DDR5-4800 RDIMM built from eight 16 Gb x8 devices, modeled with DDR5’s
defining architectural feature: two independent 32-bit subchannels per
DIMM, each with its own command bus and 32 banks, serving a 64-byte
access as a 16-beat burst on its 32-bit bus. Its timings are the
JESD79-5 values for the 4800B bin #strong[\[16\]], transcribed from a
third-party mirror of the JESD79-5 PDF (retrieved 2026-09-21, with the
table and page recorded against every key in the configuration file)
and cross-checked against a vendor's transcription (Micron's DDR5 core
data sheet) and two DDR5-4800 module datasheets, all of which agree;
the official JEDEC copy is access-gated, and the values have not been
verified against it. The scope of that statement is
exact: #emph[every DDR5-4800 device timing is taken from JESD79-5, with
three documented short-value choices that favor the baseline (tCCD,
tWTR, tRRD) and a handful of NVMain-specific keys with no DDR5
counterpart; the extended book labels all 36 device and simulator keys
with their provenance.] The core numbers are
the 4800 MT/s bin at 1.1 V: tCAS-tRCD-tRP of 40-39-39, CWL of 38
cycles, tWR 30 ns, tRRD_S 8 cycles and tFAW 32 cycles, with an all-bank
refresh every tREFI of 3.906 us occupying tRFC of 295 ns. The baseline
keeps NVMain's open-page row-buffer policy (`ClosePage 0`), the value
the configuration was introduced with, while every ReRAM configuration
runs the relaxed close-page policy (`ClosePage 1`); Section 4.1 gives
the baseline under both policies. The two modules also differ in
geometry: the ReRAM DIMM runs 4 ranks of 8 banks per channel with
64 KiB rows against DDR5’s 1 rank of 32 banks with 4 KiB rows, under
different address mappings, and both use one FRFCFS queue of 32
entries; the baseline interleaves its two subchannels above the column
bits, one 4 KiB row at a time, while the ReRAM configurations
interleave their two channels at 64 B, and the ReRAM configurations
carry NVMain's default protocol constants at 800 MHz, whose off-chip
term alone is 12.5 ns against the baseline's 4.2 ns, a default that
works against ReRAM; the one-channel control and the rank-depth bound
of Section 4.4 limit what the geometry differences can be worth. One more
disclosure belongs with the power model:
the DDR5 power model uses SK hynix's published 16 Gb DDR5-4800 IDD
limits, the lower of the two vendor
tables consulted, and the two power-down currents hynix does not
publish are scaled from Micron's. Datasheet IDD values are
specification limits rather than typicals, with no typical DDR5 figure
published to use instead, so the 0.797 W of Table 5 is a
worst-case-current figure for the lower-current vendor, not a typical
power. A typical-current module would draw less than 0.797 W, so the
DDR5 side of every per-gigabyte power ratio in Section 4.2 is a lower
bound, and a typical module would widen every ratio.

#strong[PCM.] A legacy non-volatile baseline, named for its
architectural framing in Lee et al. #strong[\[17\]], is carried as the
floor-power reference. It was never run through NVSim: its timing and
energy constants are inherited unmodified from NVMain's own bundled
example configuration and were not independently re-derived here. It
runs at its cited 400 MHz derivation basis and on the same 250 ms
matched window as everything else. Its configuration specifies no
access-device topology, so it is a black-box timing and energy model
rather than a characterization of any particular PCM cell, and the one
PCM product ever shipped is, as Section 1.2 records, a selector-gated
1S1R cross-point that is not modeled here at all.

#strong[Published silicon.] The two fabricated-timing configurations of
Section 1.2 are generated directly from those data sheets and run on
the same traces and the same module geometry, labeled 1T1R SILICON and
1S1R SILICON, and they appear beside every projected latency in Chapter
4\. The extended book puts the reason plainly, and this book keeps
it: #emph[the two published-silicon rows sit in the same table
deliberately: they are the counterweight to every projected row above
them, and no reading of this table is complete without them.] Those
timings are the page-mode read and write times of storage parts, not
media bounds; they are the only fabricated ReRAM figures at this
capacity, which is why they are carried, and why they must not be read
as what a DIMM-class part would do.

#strong[Access granularity.] Every technology in this comparison is
accessed at #strong[64 bytes]. That is the x86-64 cache line, matched
by 64 B lines on contemporary Arm server cores; it is what DDR5’s two
32-bit subchannels deliver at a burst length of 16 #strong[\[16\]]\; and it is what NVMain's address translator is
hardwired to. The gem5 traces are 64 B aligned as they come. The
SCALE-Sim traces are not: they are tensor-element granular and only
1.6% aligned, so for them the 64 B width is imposed by the
configuration rather than carried by the trace. A dedicated 64 versus
128 B study, reported in the extended book, found 128 B worse on
every axis.

#strong[The ReRAM interface.] All ReRAM configurations run behind an
800 MHz (1600 MT/s) DIMM interface, and this is a modeling assumption
that must be read as one. Only two protocol timings in a generated
ReRAM configuration come from NVSim: tRCD plus tCAS, carrying the
device read latency once, and tWR, carrying write recovery. Every other
protocol timing is a constant in #emph[interface cycles] and therefore
scales in nanoseconds with whatever clock is chosen. The 800 MHz figure
itself carries #emph[no independent ReRAM-interface citation]\: a
targeted search found none, and the only datasheet-verified ReRAM chip
I/O clocks located run 80 to 160x slower, actively contradicting rather
than merely failing to support it. The figure is positioned only
between two precedents, twice the 400 MHz basis of NVMain's PCM lineage
and below the DDR4-2666 electrical interface that carried the DDR-T
protocol on Intel's shipped Optane DIMMs. Chapter 4 quantifies what the
assumption is worth by re-running the same media at 1333 and 2400 MHz.

== 2.4. Traces

Table 2 lists the six traces, from three sources. The three SPEC and
STREAM traces were
captured with gem5 #strong[\[18\]] running the X86 out-of-order model
with L1 and L2 caches enabled, after 500 M fast-forwarded instructions,
with the first 10 ms of the detailed region discarded as cache warm-up;
each reconciles exactly with gem5’s own memory-controller request
counters. The three AI traces come from the SCALE-Sim systolic-array
simulator #strong[\[19\]].

Time base and window: one trace cycle is one NVMain cycle at CPUFreq
3000, that is three cycles per nanosecond, and every configuration
replays the same 250 ms wall-clock window against the identical
admitted request population.

#strong[Table 2: the six workload traces.]

#align(center)[#text(size: 10pt)[#table(
  columns: 5,
  align: (col, row) => (auto,auto,auto,auto,auto,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Trace]],
    [#strong[Source]],
    [#strong[Records]],
    [#strong[Read/write in window]],
    [#strong[Span in the 250 ms window]],
  ),
  [#strong[gcc\_spec2017]], [gem5, SPEC CPU2017 502.gcc\_r #strong[\[20\]]],
  [545,566], [298,792 / 220,776 (58/42)], [fills the window, sustained],
  [#strong[lbm\_spec2017]], [gem5, SPEC CPU2017 519.lbm\_r #strong[\[20\]]],
  [10,779,425], [3,179,900 / 2,384,804 (57/43)], [fills the window, sustained],
  [#strong[stream]], [gem5, STREAM #strong[\[21\]]],
  [48,439,056], [3,996,254 / 1,998,124 (67/33)], [fills the window, sustained],
  [#strong[gpt2\_ifmap]], [SCALE-Sim #strong[\[19\]]],
  [65,536], [65,536 / 0 (pure read)], [2.2 us burst],
  [#strong[alexnet\_layer1#linebreak()\_ifmap]], [SCALE-Sim #strong[\[19\]]],
  [1,269,600], [1,269,600 / 0 (pure read)], [60.5 us burst],
  [#strong[alexnet\_layer1#linebreak()\_ofmap]], [SCALE-Sim #strong[\[19\]]],
  [135,424], [0 / 135,424 (pure write)], [4.5 us burst],
)]
]

#emph[Records are trace totals from each trace's provenance sidecar;
the in-window columns are what the 250 ms replay window admits, which
for the three gem5 traces is a prefix of the trace. Each AI trace is a
single microsecond burst delivered once inside the window, 2.2, 60.5
and 4.5 us respectively, so every rate derived from one is a burst rate
and is marked as such wherever it is used. SCALE-Sim's `layer1` folder
is zero-indexed, so the AlexNet traces are AlexNet's second convolution
layer, Conv2; the label is kept for continuity.]

A seventh workload was planned and is absent. 505.mcf\_r could not be
traced: gem5 panics inside the benchmark's own input reader about
0.13 ms into the detailed region, identically on two independent
attempts, so mcf is parked rather than approximated and no mcf number
appears anywhere in this book.

== 2.5. What was built

The pipeline as described above is not what I found. A systematic audit
of the NVSim-to-NVMain flow, conducted against the raw simulator
sources and statistics files rather than against their documentation,
found fourteen #emph[silent] failure modes: defects that produced
plausible numbers rather than errors. Thirteen were repaired in this
project's toolchain and the affected simulations re-run. Table 3 is the
list. It records the mode and the fix only; the values each repair
moved are tabulated in the extended book's change appendix.

#strong[Table 3: the thirteen repaired silent failure modes, in eleven
rows, two pairs sharing one repair between them.]

#align(center)[#text(size: 10pt)[#table(
  columns: (2.9in, 2.9in),
  align: (col, row) => (auto,auto,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Failure mode]],
    [#strong[Repair]],
  ),
  [Efficiency metric mixed clock domains: watts times cycles from two different clocks],
  [Every power-delay product computed in physical W·ns],

  [The generator's leakage key was dead configuration, NVMain's source never reads it, and in its place generic standby defaults gave every non-volatile track the same static floor],
  [NVSim leakage mapped onto the standby-energy parameters NVMain does read; static power is technology-specific for the first time],

  [Reported "total system power" was the most-loaded rank, not the module],
  [Whole-module sums for every technology],

  [NVMain's power-down state machine was disabled in source: no idle policy could be simulated],
  [Dormant call site restored; a shared mechanism, so it activated for every technology at once],

  [Trace provenance: no region of interest, no warm-up, a parser keeping about four records per request],
  [Every trace regenerated with caches, a documented region, a warm-up discard and a provenance sidecar],

  [DDR5 refresh machinery inherited from a DDR3-era template, never rescaled to the DDR5 clock],
  [Recalibrated to JESD79-5: tREFI 3.906 us, tRFC 295 ns],

  [PCM ran at twice its cited clock basis; a typo zeroed its per-bit write energy],
  [400 MHz basis restored in configuration and reporting layer; typo fixed],

  [ReRAM access energies written under key names NVMain never reads],
  [Live energy keys wired; the ReRAM matrix re-run],

  [Heterogeneous host-CPU frequencies gave each technology a different offered load],
  [One host frequency everywhere, every cycle budget matched to one wall-clock window],

  [DDR5 CAS/RCD/RP timings were unsourced placeholders],
  [Corrected to the DDR5-4800 speed bin, 40-39-39; full suite re-run],

  [MLC multipliers were unsourced, attributed to a paper that does not support them, and the replacement read multiplier was itself a data error, read off the wrong column],
  [Both derived from the EMBER macro's own published measurements, the read multiplier re-derived as 1.5x from its one- and two-bit-per-cell read bandwidths],
)]
]

#emph[Every repair was validated before its results were adopted,
against a device-level anchor, exact predicted arithmetic or the
simulator's own counters; the extended book's simulation-fidelity
audit records each check. The fourteenth mode, the DDR5 supply and
current parameters, is recorded there as #strong[partially] fixed: the
supply voltage was corrected and the currents calibrated to vendor
datasheets, but datasheet IDD values are specification limits rather
than typicals, so what remains is a disclosed characteristic of the
source data and not a repairable defect.]

= 3. What the pipeline taught me

Every one of the repairs in Table 3 began as a number that looked
right. The lessons below are what I would tell the next person to
build a cross-layer memory evaluation. They are stated as mechanisms,
because a mechanism transfers and a retired value does not.

#strong[1\. Match the array organization before you compare cells.] I
compared two ReRAM cell types for months at column-mux settings chosen
independently for each. NVSim charges memristor cells no leakage at
all, so a chip's leakage is peripheral circuitry and follows mat count:
two different muxes meant two different mat counts, and what I was
reading as a property of the access device was a property of my own
configuration. The comparison became a device comparison only once the
organization was forced identical and verified on every run.

#strong[2\. Establish the time base and the window before you read any
rate.] My trace parser emitted timestamps without ever establishing
what one unit of them meant, and the replay window I quoted followed
from that unstated assumption; writes per second, endurance years and
the admitted request population all inherited it. A rate is a count
divided by a time, and if the time is unestablished the rate is
decoration. Fix the unit first, and reconcile the trace against the
generator's own counters.

#strong[3\. The classic latency metric can lie under saturation.] The
in-controller average latency rises with queue depth while the time the
workload actually waits falls: a short queue reports a fast average
over the few requests it admits, and the rest of the burst backs up
outside the controller where the total-latency counter cannot see it.
Under a load that saturates the controller the honest measure is end to
end, and both numbers belong in the same table.

#strong[4\. A configuration template inherits more than it declares.]
The DDR5 baseline was derived from a DDR3-era example configuration.
Raising the clock did not rescale the cycle counts that came with it,
so refresh, write recovery, power-down and the activate window were all
running at DDR3 cycle counts on a DDR5 clock, and nothing in the
simulator objected. A cycle count is not a time. Every inherited key
needs to be traced to a standard or a datasheet and labeled with which
one, including the keys that look boring.

#strong[5\. Read a simulator's power accounting to the line.] The
background-power path divided a rank's background power by its device
count and never multiplied it back, so the reported module power was a
per-device figure wearing a module label. No warning, no anomaly, a
plausible number. Where a simulator sums, averages or normalizes, read
the source and anchor the result against an independent target.

#strong[6\. Charge a device latency exactly once.] The generator wrote
the full NVSim device read latency into both tRCD and tCAS, so every
read paid for the array twice. The repair was a rule and a check rather
than a constant: tRCD plus tCAS must sum to the device read latency
rounded up to whole interface cycles, and the generator re-reads the
rendered configuration to confirm it. A device-to-protocol mapping
needs that closed loop, because the error it catches is invisible in
the output.

#strong[7\. Keep a silicon counterweight beside every projection.] A
circuit-level model will happily project a nanosecond array, and no
fabricated ReRAM part reads or writes in nanoseconds. Running two
published-silicon configurations on the same traces cost very little
and changed how every latency result here has to be read. A projection
without a fabricated reference beside it is an argument about a model,
not about a technology.

#strong[8\. Know which timing key sits on the request path.] In the
default configuration the cell write time sits in write recovery, and
reaches the request path only when a write closes its row, where the
simulator charges it to the subarray's next activation; a write into an
already open row charges nothing beyond the burst and the turnaround,
and neither branch delays the write's own completion. Moving the same
count onto the write pulse charges every write instead. Which key holds
the number decides whether a write penalty reaches the results at all.

= 4. Results

== 4.1. Latency

#block(breakable: false)[
#strong[Table 4: Average total latency (ns), eight full-DIMM
configurations against the six traces, 250 ms matched window. The
projected rows are NVSim media timings under the three-part caveat of
Section 1.3.]

#align(center)[#text(size: 10pt)[#table(
  columns: (1.5fr, 1fr, 1fr, 1fr, 1fr, 1.15fr, 1.15fr),
  align: (col, row) => (auto,auto,auto,auto,auto,auto,auto,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Technology]],
    [#strong[GCC]],
    [#strong[LBM]],
    [#strong[STREAM]],
    [#strong[GPT-2 (sat.)]],
    [#strong[AlexNet IFMAP (sat.)]],
    [#strong[AlexNet OFMAP (sat.)]],
  ),
  [#strong[DDR5-4800]],
  [83.1], [78.3], [79.4], [222.1], [212.3], [234.3],
  [#strong[1T1R SLC]],
  [41.4], [43.1], [42.3], [143.3], [143.6], [353.1],
  [#strong[1S1R SLC]],
  [36.8], [38.1], [37.3], [130.1], [130.0], [391.5],
  [#strong[1T1R MLC]],
  [44.5], [42.9], [46.6], [157.2], [154.1], [512.0],
  [#strong[1S1R MLC]],
  [37.9], [35.5], [36.9], [129.6], [131.4], [652.9],
  [#strong[PCM (legacy)]],
  [12,168.2], [5,136.8], [5,190.7], [1,835.8], [1,871.3], [4,747.1],
  [#strong[1T1R SILICON]],
  [11,888.5], [17,349.5], [27,802.3], [10,934.1], [10,758.9], [80,066.6],
  [#strong[1S1R SILICON]],
  [378,763.1], [324,174.4], [530,595.6], [193,995.8], [193,699.1], [1,092,759.4],
)]
]
]

#emph[Average total latency, wall-clock nanoseconds: queue entry to
completion, the like-for-like device comparison. The four ReRAM rows
above PCM are NVSim-projected device timings at the matched
2048 x 2048 organization; the last two rows replay the identical traces
at published fabricated-chip timings. DDR5 and all four
projected tracks complete every request the 250 ms window admits, one
short of the admitted count on every trace (the last admitted request
is still in flight at the cut), and the window holds 95%, 52% and 12%
of the gcc, lbm and stream trace files (Table 2); PCM, 1T1R SILICON and
1S1R SILICON complete as little as 46.1%, 9.2% and 0.5% of STREAM, and
a latency
average over a service-limited run covers only that run's completed
prefix, which is why end-to-end latency is the saturation measure. The
PCM row charges its 150 ns write pulse on the request path, unlike the
ReRAM default (Section 4.1), so its latencies sit on a different
write-path convention. The DDR5 row runs the open-page policy and the
ReRAM rows the relaxed close-page policy (Section 2.3); under the same
close-page policy the baseline reads 78.2, 69.9 and 93.5 ns on the
three CPU traces. The three AI columns, marked "sat.", are
saturated-queue averages: each burst fills the 32-entry controller
queue, queue time is 80 to 90% of the figure, and the average equals
queue depth over service rate rather than a device latency; Table 4b
gives the time each configuration takes to drain the burst, which is
the throughput measure those columns stand for.
Source: results/rev2026-09\_primary\_csv/processed\_bar\_chart\_metrics.csv,
column Latency\_ns.]

#block(breakable: false)[
#strong[Table 4b: burst drain time (ms), first request to last
completion, the throughput measure behind the three saturated columns
of Table 4.]

#align(center)[#text(size: 10pt)[#table(
  columns: (1.5fr, 1fr, 1.15fr, 1.15fr),
  align: (col, row) => (left,right,right,right,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Technology]],
    [#strong[GPT-2]],
    [#strong[AlexNet IFMAP]],
    [#strong[AlexNet OFMAP]],
  ),
  [#strong[DDR5-4800]], [0.28], [4.26], [0.49],
  [#strong[1T1R SLC]], [0.21], [4.22], [1.02],
  [#strong[1S1R SLC]], [0.20], [3.87], [1.14],
  [#strong[1T1R MLC]], [0.23], [4.43], [1.54],
  [#strong[1S1R MLC]], [0.20], [3.91], [1.98],
  [#strong[PCM (legacy)]], [3.58], [70.6], [25.1],
  [#strong[1T1R SILICON]], [15.6], [cut at 250 (76.7%)], [250.0],
  [#strong[1S1R SILICON]], [cut at 250 (89.1%)], [cut at 250 (4.5%)], [cut at 250 (5.5%)],
)]
]

#emph[Drain time is the "Exiting at cycle" value of each run at the
3 GHz global clock; "cut at 250" marks runs the 250 ms window ended
first, with the completed share in parentheses. On the two read bursts
DDR5 and the projected tracks drain within 10% of one another although
Table 4 shows 212 against 144 ns on the input map: the lower ReRAM
averages there reflect a shallower queue, not a faster device. On the
write burst the projected tracks take 2.1x to 4.0x longer than DDR5.
Source: the stats files of results/system\_rev2026-09\_primary.]
]

On the three CPU traces the projected ReRAM DIMM has lower average
memory latency than the DDR5-4800 baseline, and under GCC the margin is
about two to one: 41.4 ns for 1T1R SLC and 36.8 ns for 1S1R SLC against
83.1 ns (Table 4). The baseline runs NVMain's open-page policy while
the ReRAM configurations run its relaxed close-page policy; re-run
under the same close-page policy the baseline gives 78.2 ns under GCC,
69.9 ns under LBM and 93.5 ns under STREAM, so at matched policy the
GCC margin is 1.9 to one for 1T1R SLC and 2.1 to one for 1S1R SLC, and
on STREAM, where the open-page baseline serves 45% of requests from the
open row, close-page makes the baseline slower. The baseline carries
its JEDEC timings, write path and refresh blocking (Section 2.3), while
the ReRAM subarray reads in 10.12 ns (1T1R) or 4.70 ns (1S1R) and
precharges in one 1.25 ns cycle, a placeholder that Table 4c shows is
worth under 1% on CPU traffic. The 0.797 W DDR5 power figure that
Table 5 retains comes from the open-page run; the close-page runs are
used only for the latency margin. Their power column is not quoted:
under NVMain's current-mode model the shorter active-standby time
lowers the close-page DDR5 figure to 0.52 W under GCC while the extra
activates are charged nothing, because the model clamps the activate
energy to zero at these datasheet currents (EIDD0 below EIDD3N), so
that figure is a model side effect rather than a measurement.

The decomposition of that margin belongs before any interpretation of
it. Of the 41.40 ns 1T1R SLC average, #strong[11.25 ns is NVSim device
time], charged once as tRCD plus tCAS; the other 30.2 ns is NVMain's
default protocol cycle counts at the assumed 800 MHz interface that
Section 2.3 records as carrying no ReRAM citation. Roughly three
quarters of the ReRAM figure is therefore an interface assumption
rather than a device measurement, as is the DDR5 figure in the other
direction, whose protocol timings are JEDEC's. #strong[The direction of
the comparison is robust]\: ReRAM stays below DDR5 at all three
interface clocks measured here. #strong[Its magnitude is
model-dependent], and 41.4 against 83.1 ns is the outcome of one clock
choice rather than a device ratio; Figure 2 shows what the choice is
worth. The sweep runs only upward. Extrapolating the same decomposition
downward, 1T1R SLC would average about 72 to 75 ns at 400 MHz, and the
two SLC cells would cross the 83.1 ns baseline between about 325 and
360 MHz, depending on whether the device-plus-protocol decomposition or
a linear fit of the three measured points is extrapolated, so
the direction holds only while the interface runs faster than roughly a
third of the assumed clock; no run below 800 MHz was made.

#block(breakable: false)[
#align(center)[#image("media/short_book/fig_clock_sensitivity.png", width: 3.8in)]

#align(center)[#emph[Figure 2: GCC latency against the assumed ReRAM
interface clock. 1T1R SLC falls 41.4, 27.9, 19.0 ns and 1S1R SLC 36.8,
23.6, 14.9 ns at 800, 1333 and 2400 MHz, against the modeled DDR5
baseline of 83.1 ns. Only tRCD plus tCAS are NVSim device time; every
other protocol timing is a constant in interface cycles and therefore
scales with the clock.]]
]

Two of the untested conditions behind that margin were then run as
sensitivities, each a one-line change to the four full-DIMM
configurations (Table 4c). #strong[The precharge placeholder is worth
under 1% on CPU traffic.] Raising tRP from the one-cycle placeholder to
4 and 8 cycles (5 and 10 ns) moves the three CPU averages by at most
0.7 ns, because under the close-page policy an access completes before
its precharge and only a later access to the same bank waits for it,
and with 64 banks per module that is rare on sparse traffic; the
one-row AI bursts, where every access returns to the same bank, rise 10
to 26%. #strong[A decoder on every read adds its latency times the
read fraction.] Adding 20 and 40 ns of fixed delay to the read data
path, a pipelined stand-in for the BCH decoder of Section 5.3, raises
the CPU averages by 11.3 to 14.1 ns and 19.5 to 25.0 ns, the decode
time times the 57 to 67% read share, leaves the all-write burst
untouched and lengthens the read bursts by exactly the decode time
without changing their drain. The direction survives: at 40 ns on
every read the SLC tracks average 58.4 to 66.0 ns on the CPU traces
against 78.3 to 83.1 ns for the open-page baseline (1.20x to 1.41x) and
69.9 to 93.5 ns for the close-page one (1.12x to 1.53x), and the
worst combination in the dataset, 1T1R MLC under LBM at 40 ns against
the close-page baseline, keeps 1.06x. The latency axis therefore has
its own band, 41.4 to 63.4 ns for 1T1R SLC under GCC and 36.8 to 58.9
for 1S1R SLC, whose lower end is the primary matrix and whose upper
end is a 40 ns decoder; the interface clock of Figure 2 remains the
larger lever.

#block(breakable: false)[
#strong[Table 4c: precharge and read-decode sensitivities (ns), SLC
tracks, full DIMM, one line changed per run.]

#align(center)[#text(size: 9.5pt)[#table(
  columns: (1.6fr, 0.8fr, 0.8fr, 0.8fr, 1fr, 1fr, 0.8fr),
  align: (col, row) => (left,right,right,right,right,right,right,).at(col),
  inset: 4pt,
  table.header(
    [#strong[Track, trace]],
    [#strong[Primary]],
    [#strong[tRP 4]],
    [#strong[tRP 8]],
    [#strong[+20 ns decode]],
    [#strong[+40 ns decode]],
    [#strong[DDR5]],
  ),
  [1T1R SLC, GCC], [41.4], [41.4], [41.5], [52.9], [63.4], [83.1],
  [1T1R SLC, LBM], [43.1], [42.6], [42.7], [54.7], [62.6], [78.3],
  [1T1R SLC, STREAM], [42.3], [42.3], [42.3], [55.6], [66.0], [79.4],
  [1T1R SLC, AlexNet IFMAP (sat.)], [143.6], [158.1], [179.4], [163.6], [183.6], [212.3],
  [1S1R SLC, GCC], [36.8], [36.8], [36.8], [48.3], [58.9], [83.1],
  [1S1R SLC, LBM], [38.1], [38.2], [38.1], [49.4], [58.4], [78.3],
  [1S1R SLC, STREAM], [37.3], [37.4], [37.3], [50.6], [61.0], [79.4],
  [1S1R SLC, AlexNet IFMAP (sat.)], [130.0], [144.2], [164.5], [150.0], [170.0], [212.3],
)]
]

#emph[Average total latency as in Table 4; the MLC tracks move by the
same amounts within 2 ns (1T1R MLC under GCC 44.5, 44.6, 44.7, 56.1,
67.0; 1S1R MLC 37.9, 37.9, 38.0, 49.4, 60.4). The decode variants add
16 and 32 interface cycles to tCAS, which NVMain applies to the data
return and read completion of every read and to the read-to-write
turnaround on the same subarray; writes carry no decode, so the
output-map column is unchanged and is omitted. Completed request
counts are identical to the primary in every run. Sources:
results/system\_rev2026-09\_precharge\_trp4, \_precharge\_trp8,
\_eccdecode\_20ns and \_eccdecode\_40ns, each with its run note,
manifest and \_csv/.]
]

The write-dominated burst reverses the verdict, and it is a throughput
result: the burst saturates every controller, so the averages are
queue depth over service rate. DDR5 drains the AlexNet output map in
0.49 ms against 1.02 ms for 1T1R SLC, 1.14 for 1S1R SLC, 1.54 for 1T1R
MLC and 1.98 for 1S1R MLC (Table 4b), 2.1x to 4.0x longer. By the
queue-dominated averages, 234.3 ns against 353.1, 391.5, 512.0 and
652.9 ns, DDR5 is 1.507x and 1.671x faster than the two SLC tracks and
2.185x and 2.787x faster than the two MLC tracks. On the two read
bursts the drain times are equal within 10% (4.26 against 4.22 and
3.87 ms on the input map), so the lower ReRAM averages in those columns
reflect a shallower queue, not a faster device. Those ratios are a #emph[lower] bound
on the deficit, because in the default configuration the cell write
pulse does not delay the write's own completion at all.

=== MLC, and where the write pulse is charged

MLC is barely slower than SLC in Table 4, and that is a consequence of
this project's device-to-protocol mapping rather than a device finding.
The generator books the cell write latency as tWR and leaves the
write-pulse parameter tWP at zero, so, as lesson 8 describes, it
reaches the request path only when a write closes its row and never
delays the write's own completion, 13.75 ns on every track; the
49.79 ns that separates a 1T1R MLC write from a 15.26 ns SLC write
never reaches the write.

Rather than assert the size of that bound, the primary matrix was
re-run with the choice inverted: the same latency written to tWP, tWR
held at one cycle, so every write's completion carries the pulse and an
open-row write charges it to its subarray's next read and next write.
Everything else is identical, and the two all-read traces come back
byte-identical between the datasets. #strong[The write-pulse bracket
table] below sets the two ends side by side.

#block(breakable: false)[
#strong[The write-pulse bracket table: average total latency (ns),
full-DIMM, default mapping against the bounding run.]

#align(center)[#text(size: 10pt)[#table(
  columns: 5,
  align: (col, row) => (left,right,right,right,right,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Track]],
    [#strong[GCC, default]],
    [#strong[GCC, bounding]],
    [#strong[OFMAP, default]],
    [#strong[OFMAP, bounding]],
  ),
  [#strong[1T1R SLC]], [41.4], [48.3], [353.1], [696.6],
  [#strong[1T1R MLC]], [44.5], [65.8], [512.0], [1,649.9],
  [#strong[1S1R SLC]], [36.8], [47.4], [391.5], [916.6],
  [#strong[1S1R MLC]], [37.9], [72.4], [652.9], [2,498.7],
)]
]
]

#emph[Default values are the Latency\_ns column of
results/rev2026-09\_primary\_csv/processed\_bar\_chart\_metrics.csv;
bounding values are the same column of
results/system\_rev2026-09\_writepulse/\_csv/processed\_bar\_chart\_metrics.csv,
in both cases the full\_dimm rows. The two all-read traces are omitted
because they are identical in the two datasets. These are media
latencies at an assumed 800 MHz interface, not device latencies of any
shipped part.]

Read against DDR5’s 234.3 ns on the output map, each ratio above
becomes a bracket, derived from the two OFMAP columns of the
write-pulse bracket table: 1.507x
to 2.973x against 1T1R SLC, 1.671x to 3.912x against 1S1R SLC, 2.185x
to 7.042x against 1T1R MLC and 2.787x to 10.665x against 1S1R MLC. MLC
costs up to 1.53x SLC on CPU traffic and up to 2.73x on the write
burst, derived the same way.

#strong[What produced the bracket is not the same thing on the CPU
traces as on the write burst.] On GCC, LBM and STREAM the rise equals
the write fraction of the completed requests times the cell pulse, rounded to whole
interface cycles, to within 1% on every track-trace pair, which is what the simulator's own
row-buffer counters predict, because under the close-page policy the
ReRAM configurations run, those traces leave almost no row hits: the
hit share in the ReRAM runs is about 0.03% under GCC and effectively
zero under LBM and STREAM, so nearly every write closed its row and the
default mapping had already charged the cell to the subarray's next
activation. On the AlexNet output map the picture inverts. That trace is
pure writes, 76% of its accesses hit an open row, and the measured rise
is 21 to 23 times the per-write pulse, so the headline write-burst
bracket is mostly subarray blocking that the default mode never
charged rather than the write's own completion latency. #strong[The
bracket is an upper end of the write-path cost inside this model, not a
prediction of a device], and a reader who takes the output-map figure
as the cell pulse added to every write will be wrong by a factor of
about 22. Two consequences follow. "Below DDR5 on the CPU traces"
survives for all four projected tracks at the upper end, the worst case
in the matrix being 1S1R MLC under GCC at 72.398 ns against DDR5’s
83.111 ns, which is 0.871x of DDR5 (derived); and no endurance number
moves, because the same traces present the same writes and the mode
changes only when they are served.

One comparison bounds the whole MLC treatment. Multi-level 1T1R ReRAM
is written by iterative program-and-verify pulses #strong[\[22\]], and the
closest published two-bit #emph[array] result is MLC phase-change
memory, more than seventy iterations for a total write of 9.7 us
#strong[\[23\]]\; against
that, the 3.263x write multiplier used here understates the media-level
MLC write cost by one to two orders of magnitude, and the bounding run
does not close that gap, because it moves this project's own pulse onto
the request path rather than replacing it with a verify loop. On the read side the
honest statement is an absence: no primary source pairing SLC and MLC
array-level read times was found. TLC and QLC carry no defensible
number at all, only a qualitative trend, that verify iterations grow
and the sensing window and retention worsen as levels are added.

== 4.2. Power

#strong[NVSim reports no transistor-versus-selector leakage gap.] At
the matched organization it assigns both cell types the same 108.384 mW
of peripheral leakage per 1 Gb chip, and all four ReRAM full-DIMM
configurations sit on one shared static floor of 6.937 W. That is a
statement about the periphery: NVSim models no selector leakage of its
own, and the 1S1R characterization is uncalibrated against any
fabricated cross-point part, so the selector's contribution is bounded
separately below. Table 5 is the module accounting.

#strong[Table 5: total module power (W) and power per gigabyte
(W/GiB), full-DIMM, module-sum semantics.]

#align(center)[#text(size: 10pt)[#table(
  columns: (1.4fr, 0.6fr, 0.9fr, 1.25fr, 1fr),
  align: (col, row) => (left,right,right,right,right,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Technology]],
    [#strong[GiB]],
    [#strong[GCC (W)]],
    [#strong[Suite range (W)]],
    [#strong[GCC (W/GiB)]],
  ),
  [#strong[DDR5-4800]], [16], [0.797], [0.797 to 1.110], [0.0498],
  [#strong[PCM (legacy)]], [4], [0.046], [0.036 to 0.046], [0.0115],
  [#strong[1T1R SLC]], [8], [6.939], [6.939 to 7.291], [0.8674],
  [#strong[1S1R SLC]], [8], [6.940], [6.940 to 7.318], [0.8674],
  [#strong[1T1R MLC]], [16], [6.941], [6.941 to 7.287], [0.4338],
  [#strong[1S1R MLC]], [16], [6.941], [6.941 to 7.353], [0.4338],
)]
]

#emph[Whole-module sums; the suite range is the lowest and highest of
that row's six workload values, and the per-GiB column divides each
module total by its own capacity, which is the only form in which these
technologies are comparable. #strong[Every figure in this table counts memory devices
only] - no register clock driver, power-management IC, PHY, termination
or ReRAM-side controller, on either side. ReRAM's power-down mechanism
is mechanically live but its power-down energy is an explicit,
disclosed placeholder equal to existing standby energy, so no ReRAM
figure claims a gating benefit; every per-GiB ratio here is a point
estimate whose ReRAM side would fall with gating and whose DDR5 side
would fall with typical currents or the matched close-page policy
(Sections 2.3, 4.1). Source:
results/rev2026-09\_primary\_csv/processed\_bar\_chart\_metrics.csv.]

Read per gigabyte, #strong[ReRAM SLC costs 12.7x to 17.4x DDR5’s power
and ReRAM MLC 6.4x to 8.7x] across the suite, MLC halving the penalty
because leakage is per chip and MLC puts twice the capacity behind the
same chips. The legacy PCM baseline sits #emph[below] DDR5 per
gigabyte, which reflects the leakage constant of the configuration it
inherits rather than a characterized device. Figure 3 shows where the
watts are: dynamic power is 2.9 to 4.9 mW module-wide under GCC and
rises only to 346 to 417 mW under the AI read bursts, under 6% of the
total. DDR5’s refresh alone, 9.1% of its 0.797 W under GCC or about
73 mW, is fifteen to twenty-five times the whole ReRAM module's dynamic
draw, and ReRAM refreshes nothing; the 6.94 W leakage floor outweighs
that saved refresh about ninety-five times over. ReRAM power is leakage, and at the matched organization that is
a statement about both cell types equally.

#block(breakable: false)[
#align(center)[#block(clip: true, height: 2.28in)[
#image("media/media/image6.png", width: 6.5in)]]

#align(center)[#emph[Figure 3: system power breakdown under GCC. All
four ReRAM tracks sit on one shared leakage floor near 6.94 W for 8 GiB
(SLC) or 16 GiB (MLC), against a 16 GiB DDR5 module; that floor is the
LOP periphery of the primary characterization, and the LSTP
re-characterization of Table 5b puts it at 0.10 W. The chart is a
module-level view; the per-gigabyte normalization, which is the only
form in which these modules are comparable, exists only in Table 5.]]
]

#strong[The floor is a transistor choice, not a cell result.] NVSim
builds the periphery from one of three ITRS transistor roadmaps, and
the primary characterization uses the low-operating-power (LOP) profile
at 350 K (Section 2.2). Re-characterized with the low-standby-power
(LSTP) profile, with that one line changed and everything else
identical, the chip's peripheral leakage falls from 108.384 to
1.599 mW, the device read time rises 5% and the die area moves 0.3%;
carried through the same pipeline into the same 24 full-DIMM runs, the
module's static floor is 0.102 W instead of 6.937 W, and Table 5b is
the result. Per gigabyte ReRAM SLC then draws 0.26x to 0.29x of DDR5 on
the CPU traces and 0.48x to 0.94x on the AI bursts, MLC 0.14x to
0.54x, with every CPU latency within 2% of Table 4 and the write burst
at most 4% slower from the longer write recovery. Nothing in the model
says which periphery a DIMM-class ReRAM would carry: NVSim's own
non-volatile memory examples use LOP, commodity DRAM periphery is built
for standby current, and no fabricated ReRAM die located reports a
leakage figure that decides it. #strong[The power axis of this
comparison is therefore open within two orders of magnitude], and the
ratios of Table 5 are its LOP end, not its value.

#block[
#strong[Table 5b: the same module accounting with the low-standby-power
(LSTP) periphery, full-DIMM, the four ReRAM tracks.]

#align(center)[#text(size: 10pt)[#table(
  columns: (1.3fr, 0.5fr, 0.8fr, 1.1fr, 0.9fr, 1.2fr),
  align: (col, row) => (left,right,right,right,right,right,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Technology]],
    [#strong[GiB]],
    [#strong[GCC (W)]],
    [#strong[Suite range (W)]],
    [#strong[GCC (W/GiB)]],
    [#strong[Per GiB vs DDR5, suite]],
  ),
  [#strong[1T1R SLC]], [8], [0.106], [0.106 to 0.476], [0.0133], [0.26x to 0.89x],
  [#strong[1S1R SLC]], [8], [0.106], [0.106 to 0.502], [0.0132], [0.26x to 0.94x],
  [#strong[1T1R MLC]], [16], [0.108], [0.108 to 0.485], [0.0068], [0.14x to 0.45x],
  [#strong[1S1R MLC]], [16], [0.108], [0.108 to 0.573], [0.0068], [0.14x to 0.54x],
)]
]

#emph[Same semantics as Table 5, DDR5 side unchanged. The static floor
is 64 chips at 1.599 mW; the dynamic term rises only slightly because
the per-access burst-read energy is NVMain's default in both series and
only the activate, write and standby energies carry the
re-characterization. Source:
results/system\_rev2026-09\_periphery\_lstp/\_csv/processed\_bar\_chart\_metrics.csv,
full\_dimm rows, against the primary CSV.]
]

At the LOP end the deficit is not the end of the arithmetic either,
because a non-volatile module can in principle gate the periphery a
DRAM module cannot. Gating
the static component for an idle fraction $f$ leaves
$(1-f) times 6.937 + 0.003$ W, so reaching DDR5’s 0.399 W for the same
8 GiB requires $f = 94.3%$. #strong[That threshold sits inside, not
above, the idleness band this project cites]\: the 2 to 6%
memory-bandwidth utilization that #strong[\[24\]] cites from an earlier
characterization of web-search and data-analytics servers corresponds to 94 to 98% of time
with no memory traffic in aggregate; that band is compatible with,
though not evidence of, a gateable fraction of that size, and taken at
face value it brackets break-even, 0.142 W against DDR5’s 0.399 W at
the idle end and 0.419 against 0.399 W at the busy end. Whether a module realizes that
idleness depends on the wake-up latency and granularity of the gating,
which no cited ReRAM part characterizes, against a request arriving
every 481 ns on average under GCC. What the model cannot price is
the gated module itself, because no citable ReRAM power-gating
characterization exists; and fixed per-module overhead moves the
arithmetic against ReRAM, since 8 GiB of ReRAM carries the same
register, PMIC and PHY overhead $O$ as 16 GiB of DDR5, so the required
gating fraction #emph[rises] with $O$, 94.3% at $O = 0$,
#strong[97.9% at $O = 0.5$ W per module], and beyond
#strong[$O = 0.79$ W] parity is out of reach at any gating fraction.
The same overhead compresses the ungated ratio and tightens the gated
comparison, and the parity claim rests on the second. At the LSTP end
none of this arithmetic is needed: the ungated module already sits
below DDR5 per gigabyte on every CPU trace.

Two device-level results complete the picture. #strong[The leakage
figure is an organization result, not a cell result.] At a 1024 x 1024
organization both cells leak about twice as much, 224.138 and
220.224 mW per chip (results/hardware/reram\_22nm\_1t1r\_slc\_1024\_results.txt
and reram\_22nm\_selector\_slc\_1024\_results.txt), still within 2% of
each other, so whatever
organization is matched the two cells land together. #strong[The
selector's sneak current adds nothing to standby power and little
during an access.] The standby adder is exactly zero at both selector
bounds; during an access the budget is 7.56 mW per chip at an
ovonic-threshold-switch bound and 0.076 mW at a best-published FAST
bound, which at the OTS figure is 0.87% of the module's 6.937 W static
floor while a rank is being accessed. What binds
is tile validity, not leakage: under the handbook rule that a tile side
may not exceed $I_"on" \/ (6 I_"leak")$ #strong[\[41\]], the OTS bound
supports a tile of at most 1666 cells a side, so #strong[the 2048 x 2048 organization simulated
here is not valid at present-day selector quality], while the FAST
bound supports 166,666. Every 1S1R number in this book is conditional
on a selector better than today's production ovonic threshold
switch. #emph[Source: results/selector\_layer.json.]

== 4.3. Endurance

Writes wear the cell, so endurance is the constraint that decides
whether any of the above matters. The projection carries the write
distribution measured per line location inside the 250 ms window (the
per-line counts are taken from the trace inside the window; the
simulator's per-row wear counters are the cross-check) onto a 64 GiB
module at the best-sourced 10#super[6] cycle rating
#strong[\[25\]], and asks how long it lives under four wear-leveling
policies. Table 6 is that projection for the three sustained
workloads, and Figure 4 is the same projection by policy.

#strong[Table 6: projected lifetime and required endurance (1T1R SLC
full DIMM, 64 GiB, 10#super[6] cycles/cell, 250 ms window, one write
per line per request).]

#align(center)[#text(size: 10pt)[#table(
  columns: (1fr, 1fr, 1.1fr, 1.4fr, 0.9fr, 1.2fr),
  align: (col, row) => (left,right,right,right,right,right,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Workload]],
    [#strong[Write rate]],
    [#strong[No leveling]],
    [#strong[Rand. Start-Gap]],
    [#strong[Ideal]],
    [#strong[Req. endur. (ideal)]],
  ),
  [#strong[GCC]], [0.88 M/s], [7.7 h], [7.7 to 15.4 h], [38.6 yr],
  [2.6 × 10#super[5]],
  [#strong[LBM]], [9.54 M/s], [23.2 h], [0.20 yr], [3.6 yr],
  [2.8 × 10#super[6]],
  [#strong[STREAM]], [7.99 M/s], [69.4 h], [0.96 yr], [4.3 yr],
  [2.3 × 10#super[6]],
)]
]

#emph[Ranges in the randomized Start-Gap column mark cases where the
hottest line fails before the gap completes its first rotation, so the
true lifetime lies between the no-leveling value and twice it.
#strong[Required endurance] is the per-cell cycle count a ten-year life
would demand at this write rate and capacity, which is the same
equation solved for endurance rather than for time. #strong[Every row
assumes a stationary write distribution:] the spatial pattern of writes
measured inside the 250 ms window is taken to repeat unchanged for the
module's whole life, and the no-leveling column assumes an operating
system that never remaps a hot line. Source: results/endurance\_table.csv, rows
capacity\_gib \= 64, endurance \= 1e6, write\_reduction \= 1.0,
rate\_basis \= admitted.]

#block(breakable: false)[
#align(center)[#image("media/short_book/fig_endurance_policy.png", width: 3.6in)]

#align(center)[#emph[Figure 4: projected lifetime by wear-leveling
policy. Every value is a projection from the write distribution
measured in a 250 ms window, assumed stationary for the module's life;
never a measured lifetime.]]
]

The distance between those columns is the finding. #strong[Endurance
viability is decided almost entirely by the wear-leveling mechanism,
not by the cell.] With no leveling the module survives #emph[hours]
under every sustained workload, because the traces are sparse: GCC
touches 577 row locations, LBM 826 and STREAM 1,954
(results/wear\_1T1R\_SLC\_<trace>.json) out of the 131,072 rows of the simulated 8 GiB module, and of 1,048,576 at the 64 GiB
capacity Table 6 projects. A workload that concentrates its write
stream on a few hundred locations exhausts them however much unused
capacity sits beside them. With ideal leveling the same module reaches
38.6 years under GCC and 3.6 under LBM, four to five orders of
magnitude away.

Deterministic Start-Gap #strong[\[26\]] does not close that gap for
these footprints. Over a single whole-module region the hottest line
fails before the gap has rotated once, so it recovers essentially
nothing; randomizing the region assignment recovers part of it in the
two streaming cases (0.20 years under LBM and 0.96 under STREAM against
ideals of 3.6 and 4.3) and still nothing under GCC, whose footprint is
too small to randomize over. One consequence runs against intuition:
over a single region #strong[a larger module is worse, not better],
because the rotation period grows with the region while the gap still
advances one line per hundred writes: projected under randomized
Start-Gap, GCC survives 0.69 years at 8 GiB but only 7.7 hours at
64 GiB.

Two levers the projection does not price are visible in the same
table. A write-absorbing cache in front of the module, the pattern of
Optane's Memory Mode (Section 5.2), cuts $W$: at a 4.5x write reduction
the randomized Start-Gap projection for GCC at 8 GiB rises from 0.69 to
3.1 years and the ideal 64 GiB figure from 38.6 to 173 years
(results/endurance\_table.csv, write\_reduction 4.5), while the
single-region failure at 64 GiB remains. And every leveling scheme
carries metadata, remapping traffic and energy that the analytic model
does not charge: the Start-Gap moves are counted, the data they move is
not, and the simulator runs are identical with and without the decoder
(Section 4.4), so the cost of leveling is unpriced here.

The arithmetic is one equation. With ideal leveling the $N$ lines of
the module share the write rate $W$ equally, so a cell endurance $E$
gives a lifetime $T = N E \/ W$, and the endurance a life $T$ demands
is $E_"req" = W T \/ N$: at 64 GiB, $N = 2^30$ lines, GCC's
0.88 million writes per second and $E = 10^6$ give 38.6 years. The
required-endurance form is Prof. Kvatinsky's. The extended book's
Section 3.1.4 places the 10#super[6] planning value inside the
literature, where shipped filamentary parts are rated at 10#super[4]
to 10#super[7] cycles and laboratory single-device results reach
10#super[10] and beyond.

Solved for endurance instead of for time, a ten-year life on a 64 GiB
module demands #strong[2.6 × 10#super[5] cycles under GCC,
2.8 × 10#super[6] under LBM and 2.3 × 10#super[6] under STREAM] with
ideal leveling, and 6.3, 6.5 and 4.3 × 10#super[6] under randomized
Start-Gap: against the 10#super[6] planning value GCC clears the bar
fourfold under ideal leveling and everything else fails it by 2.3 to
6.5x. A ten-year
ReRAM main memory needs a cell in the high 10#super[6] range
#emph[and] a leveling scheme better than a single-region Start-Gap.

One negative result bounds what the simulation can contribute.
#strong[It cannot show wear leveling at work.] With one Start-Gap region
of 67,108,864 lines (4 GiB: NVMain sizes the region from the
per-channel geometry, without the channel count, and the two channels
share one gap register; the simulator's region is therefore half the
simulated 8 GiB module, while the projection assumes one region over
the whole 64 GiB module) and one gap move per hundred writes, a 250 ms
window makes 2,207 gap moves under GCC and 23,848 under LBM, roughly
3 x 10#super[-5] and 4 x 10#super[-4] of one rotation, so
running the matrix with the remapper off reproduces the
primary run's wear statistics and latencies identically. At those
move rates one rotation of the region takes about 7,600 s of simulated
time under GCC, 2.1 hours, and about 700 s under LBM, 11.7 minutes:
30,000 and 2,800 windows of 250 ms, far beyond any trace this pipeline
could replay. Leveling's
effect is carried entirely by the projection behind Table 6, whose
sliding-window model was checked against a brute-force write-by-write
reference in an independent review round; the record is
research\_notes/endurance\_audit\_runs/ and
tests/test\_endurance\_sensitivity.py.

== 4.4. Scaling and sensitivities

Seven sensitivity series each change one flag against the primary
matrix, and a pre-revision NVSim voltage sweep sits beside them.
Table 7 takes the chip-count axis at the two extremes of behavior.

#strong[Table 7: chip-count scaling, 1T1R SLC, average total latency
(ns) and Power-Delay Product (W·ns), 250 ms matched window.]

#align(center)[#text(size: 10pt)[#table(
  columns: (1.5fr, 0.9fr, 0.9fr, 0.95fr, 0.9fr, 0.9fr, 1fr),
  align: (col, row) => (left,right,right,right,right,right,right,).at(col),
  inset: 5pt,
  table.header(
    [#strong[Workload]],
    [#strong[Lat. 8]],
    [#strong[Lat. 16]],
    [#strong[Lat. 64]],
    [#strong[PDP 8]],
    [#strong[PDP 16]],
    [#strong[PDP 64]],
  ),
  [GCC], [45.4], [44.8], [41.4], [39.5], [77.8], [287.3],
  [AlexNet OFMAP], [391.3], [352.1], [353.1], [375.0], [657.6], [2,496.2],
)]
]

#emph[Chip counts are 8, 16 and 64 devices; the one-chip point of the
series is omitted because its decoded address space is a generator
floor rather than a physical module. Source:
results/rev2026-09\_primary\_csv/processed\_bar\_chart\_metrics.csv,
rows Technology \= 1T1R\_SLC.]

#strong[The latency return on scaling is a queueing return, not a
parallelism return.] GCC moves only from 45.4 ns at eight chips to
41.4 at sixty-four, and the write burst is flatter still, 352.1 against
353.1 ns between sixteen chips and sixty-four, for a 3.8-fold
efficiency loss. The two AI read bursts do gain, by 1.68x, and a
one-channel control run shows the gain is entirely the second channel
rather than the added devices; rank depth, isolated the same way, buys
at most 7.5% on any of the six traces. Figure 5 plots the same
trajectory in the power-latency plane.

#block(breakable: false)[
#align(center)[#block(clip: true, height: 3.15in)[
#image("media/media/image26.png", width: 4.7in)]]

#align(center)[#emph[Figure 5: Pareto scaling trajectory under
write-torture conditions (AlexNet OFMAP), all four ReRAM tracks with
the two baselines. The leftmost point of each trajectory is the
single-chip architecture, a non-physical generator floor that enters no
conclusion here.]]
]

Queue depth changes how the results should be read rather than what
they say. Across depths of 8, 32 and 128 the CPU traces do not move at
all, but under the AlexNet output-map write burst the two latency
measures move in opposite directions: for 1T1R SLC the in-controller
average goes 124.9, 353.1 and 1,049.2 ns while the end-to-end average
goes 680.1, 486.1 and 432.5 us. A deeper queue #emph[raises] the
classic metric and #emph[lowers] the time the workload actually waits,
because a short queue reports a fast average over the few requests it
admits while the rest of the burst backs up outside the controller
where the total-latency counter cannot see it. That answers the
write-queue sizing question of Section 2.1, and it is a #emph[write]
effect: on a write burst a deeper queue pays off end to end, and the
in-controller average reports that gain as a regression.

Three further series, one sentence each. At a 1024 x 1024 organization
the 1T1R SLC full DIMM is 4 to 10% faster and every track pays 14.1 to
14.7 W against 6.9 W, the two cells still leaking within 2% of each
other (Section 4.2). A 64 B DDR5
cross-check on a legacy single-channel shape averages 79.6 against
83.1 ns under GCC but holds tCCD below the JEDEC floor, so its
advantage is optimistic. And a pre-revision three-point NVSim
ReadVoltage sweep, plus or minus 20%, not re-run at the matched
organization or under the repaired power model, moved the power-delay
product by less than 4% with read latency invariant; its numbers are
not comparable with Tables 4 to 7.

== 4.5. Density, and the comparison in one table

Density is the axis on which the selector earns its place. At the
matched organization NVSim gives the 1S1R chip a die area of 3.540 mm²
against 12.008 for 1T1R, a 3.4x advantage that is now the selector's
only device-level advantage besides read latency, and it converts into
a die-level density of #strong[1.24x DDR5 for 1S1R SLC and 2.47x for
1S1R MLC] against #strong[0.36x and 0.73x for the two 1T1R tracks]
(Figure 6), normalized to a DDR5 anchor of 35 mm² per GB, a figure
inside the 33.1 to 37.6 mm²/GB band of Micron, Samsung and SK hynix
production 16 Gb DDR5 dies at 10 nm-class nodes #strong[\[40\]]: the
transistor-gated cell is less dense than the DRAM it would replace, and
only the cross-point clears parity at the 20F² cell assumed here. At
the 6F² array the fabricated 16 Gb 1T1R part reports #strong[\[12\]],
scaling the cell area alone and holding NVSim's periphery (about
1.6 mm² of the 12.0 mm² die) gives roughly 0.9x as SLC and 1.9x as
MLC, so even the fabricated cell does not clear parity as SLC at 22nm;
the 1T1R density verdict is robust to the cell assumption, and the
20F² figure sets only its margin. Scaled
quadratically to a
12nm-class node the same anchors project 4.15x and 8.31x for 1S1R SLC
and MLC and 1.22x and 2.45x for 1T1R, with deck stacking available only
to the cross-point. Those columns are geometry, not characterization,
and are linear in an assumed cell area: a realized 1S1R cell at twice
the idealized 4F² would drop 22nm SLC below parity.

Fabricated silicon says where a realized cell sits. The only
cross-point ReRAM die at this capacity, the 2-layer 32 Gb part at 24 nm
#strong[\[13\]], is 130.7 mm² for 32 Gb: 4.1 mm² per Gb with both layers
and 8.2 mm² per Gb per layer, or about 6.9 mm² per Gb per layer scaled
quadratically to 22 nm, which is 0.64x DDR5’s die-level density for one
layer and 1.3x for two, against the 3.54 mm² per Gb (1.24x) the
idealized single-layer cell gives here. The modeled 1S1R figure is
therefore about twice as dense per layer as the fabricated part, and
the parity reported above for one idealized layer is what the
fabricated part reaches with two. Usable capacity reads the same way:
the 27% storage overhead of the NVM error-correction design point of
Section 5.3, applied to the ReRAM side only, takes 1S1R SLC from 1.24x
to 0.98x and 1S1R MLC from 2.47x to 1.94x (Table 8, last density
column).

#block(breakable: false)[
#align(center)[#block(clip: true, height: 1.87in)[
#image("media/media/image23.png", width: 3.61in)]]

#align(center)[#emph[Figure 6: die-level density normalized to
DDR5 \= 1.00, higher is better. The PCM bar, 1.25x, is #strong[not
characterized]\: a fixed constant in the metrics pipeline inverted from
an older 0.80 mm²/GB placeholder, with no device or datasheet source
behind it.]]
]

Head to head, the two cells differ in exactly three places. The
selector buys die area, 3.540 against 12.008 mm² per chip (3.4x), and a
faster read, 4.70 against 10.12 ns, at the price of a slower write,
24.59 against 15.26 ns, so its write-to-read ratio is 5.2x against 1.5x
for the transistor-gated cell; leakage and wear are identical at the
matched organization (Table 1). Each advantage is conditional: the
selector's on a selector quality that supports the tile (Section 4.2),
the transistor's on the 20F² cell assumed above.

Table 8 puts every axis side by side.

#strong[Table 8: cross-technology summary, full-DIMM configurations.]

#align(center)[#text(size: 9.5pt)[#table(
  columns: (1.1fr, 0.75fr, 1.1fr, 0.75fr, 0.7fr, 0.8fr, 0.95fr),
  align: (col, row) => (left,right,right,right,right,right,right,).at(col),
  inset: 4pt,
  table.header(
    [#strong[Technology]],
    [#strong[GCC lat. (ns)]],
    [#strong[GCC power (W / W per GiB)]],
    [#strong[Geo-mean PDP]],
    [#strong[Die density]],
    [#strong[Usable density (27% ECC)]],
    [#strong[LBM lifetime \@64 GiB (ideal / rand.)]],
  ),
  [#strong[DDR5-4800]], [83.1], [0.797 / 0.0498], [136.2], [1.00], [1.00],
  [n/a (volatile)],
  [#strong[PCM (legacy)]], [12,168.2], [0.046 / 0.0115], [173.6], [1.25\*],
  [n/a],
  [not evaluated],
  [#strong[1T1R SLC]], [41.4], [6.939 / 0.8674], [641.0], [0.36], [0.28],
  [3.6 / 0.20 yr],
  [#strong[1S1R SLC]], [36.8], [6.940 / 0.8674], [594.5], [1.24], [0.98],
  [3.6 / 0.20 yr],
  [#strong[1T1R MLC]], [44.5], [6.941 / 0.4338], [722.8], [0.73], [0.57],
  [3.6 / 0.20 yr],
  [#strong[1S1R MLC]], [37.9], [6.941 / 0.4338], [645.4], [2.47], [1.94],
  [3.6 / 0.20 yr],
)]
]

#emph[Power is module watts / watts per gigabyte; only the second is
comparable, because the modules are 16 GiB (DDR5, ReRAM MLC), 8 GiB
(ReRAM SLC) and 4 GiB (PCM), and both sides count memory devices only.
Geo-mean PDP is W·ns over the six workloads. DDR5 latency and power
come from the open-page baseline run; at the ReRAM configurations'
close-page policy its GCC latency is 78.2 ns (Section 4.1). The GCC
power column is the LOP end of the periphery band; at the LSTP end
every ReRAM track reads 0.106 to 0.108 W, 0.0133 (SLC) and 0.0068 (MLC)
W per GiB (Table 5b). Usable
density applies the 27% total storage overhead of the NVM
error-correction design point of Section 5.3 to the ReRAM die figures
(raw divided by 1.27); DDR5's on-die ECC is already inside its 16 Gb
user capacity. #strong[\*] The PCM
density figure is a fixed constant in the metrics pipeline with no
device or datasheet source behind it, not a characterized die area; it
is reported here for completeness and should be read as #emph[not
characterized], like the lifetime cell beside it. The
published-silicon counterweights of Table 4 are deliberately not
repeated here: no row of this table describes a fabricated part.
#strong[Projected lifetime] is the LBM projection at 64 GiB, the
capacity Section 4.3 projects, the worst of the three traces under
ideal leveling (under randomized Start-Gap GCC is worse, 7.7 to
15.4 hours, Table 6), under #emph[ideal] uniform leveling and
under randomized Start-Gap, at 10#super[6] cycles per cell; the MLC
tracks carry the SLC rating, because MLC programming is not counted as
extra wear; every value is a projection in the sense of Section 4.3,
not a measured lifetime.
Source: results/rev2026-09\_primary\_csv/processed\_bar\_chart\_metrics.csv,
processed\_geometric\_means.csv and results/endurance\_table.csv.]

= 5. Discussion

== 5.1. The verdict

Chapter 4 produces three kinds of statement, and keeping them apart is
the discipline of this book.

#strong[What holds is direction.] On the CPU traces the projected media
has lower average latency than the DDR5-4800 baseline, and that
ordering survives at the upper end of the write-pulse bracket and at a
baseline re-run under the ReRAM configurations' close-page policy; at a
matched organization the cross-point clears DDR5’s die-level density
and the transistor-gated cell does not at the 20F² cell assumed here
(Section 4.5). Neither magnitude is robust in the way
its direction is.

#strong[What is open is the power axis, and what is bounded is the
write burst.] The per-gigabyte figure counts memory devices only on
both sides and is set by the periphery transistor class the
characterization assumes: 12.7x to 17.4x DDR5 with the
low-operating-power periphery, 0.26x to 0.94x with the
low-standby-power one, and the model cannot choose between them
(Section 4.2). At the first end gating break-even sits inside the
idleness band inferred from the cited utilization figures
#strong[\[24\]], a band compatible with, but not evidence of, a gateable
fraction that large, so the arithmetic locates parity for that class
without pricing it; at the second end no gating is needed. The
upper end of the output-map bracket is an upper end of the write-path
cost inside this model, not a prediction of a device.

#strong[What is projected is every lifetime, and the latency advantage
itself.] The endurance claim lives in the leveling mechanism, not the
cell, and no figure here is a measured lifetime; the latency result is
a projection in the strict sense of the caveat of Section 1.3, and the
same DIMM at published silicon timings runs in microseconds.

== 5.2. Near and far memory

Everything above places the module in the #emph[near] memory position,
reached over the processor's own latency-controlled interconnect, where
latency is the figure of merit. A second position, reached over PCI
Express instead, values capacity and density above the last fifty
nanoseconds; it adds memory from a slot that would otherwise carry
none, not bandwidth beyond what a socket's own channels already
deliver. This section asks where the projected device would sit if
it were aimed there, and answers with measured numbers.

The window real systems accept is narrow and it is measured. Local DRAM
at idle sits well below it: DDR5 measures 111 to 114 ns on two-socket
servers, where the far socket of the same machine costs 191 to 193 ns
#strong[\[27\]], and earlier DDR4 two-socket platforms measure 78 to
115 ns locally and 142 to 255 ns to the far socket #strong[\[27\]],
#strong[\[28\]]. Shipped CXL-attached DRAM expanders measure about 214,
239 and 271 ns idle load-to-use for ASIC-based devices and about 394 ns
for an FPGA-based one #strong[\[27\]], a band #strong[\[29\]]
corroborates as ratios. What does #emph[not] survive contact with that
data is a single blanket threshold for acceptable far memory: in Pond's
workload study, at an added 64 ns only 43% of 158 workloads stay within
5% of their local performance and 21% lose more than 25%, and at an
added 140 ns 37% stay within 5% #strong[\[28\]], so acceptability is a
per-workload property, not a number. And #strong[the
few-hundred-nanosecond band belongs to CXL-attached DRAM #emph[devices],
not to local DRAM], so no figure drawn from it is a DRAM reference.

#strong[This book's two latency lines sit on opposite sides of that
window, and neither is inside it.] The projected media is 36.8 to
44.5 ns under GCC and 353.1 to 652.9 ns on the write burst, so on CPU
traffic it is below the entire window, with room for a controller and
an error-correction stack before it would reach the low end. The
published-silicon counterweights, 11.9 us and 379 us under GCC, are far
above it. That gap is the state of the technology: nothing shipped is
close, and nothing in the device physics says it could not be.

One mechanism decides how such a device would be used. A CXL-attached
region surfaces to Linux as a CPU-less NUMA node, with the ACPI
Heterogeneous Memory Attribute Table supplying latency and bandwidth
per initiator-target pair so the kernel can rank it #strong[\[30\]],
and what the kernel does with that ranking is #strong[page placement,
not per-request routing] #strong[\[49\]]: pages move between tiers at 4 KiB granularity
on a millisecond-to-second timescale, and nothing routes an individual
load or store by projected access time. A far memory can afford to be
slower than DRAM; it cannot afford to be slower by a factor page
migration cannot amortize.

The bandwidth half of the same claim does not hold as stated either. A
shipping x8 CXL 2.0 expander is held by its PCIe 5.0 link to about
the bandwidth of a single DDR5-4800 channel, 38.4 GB/s
#strong[\[29\]], and far below the eight such channels of a socket, so
#strong[CXL adds capacity and bandwidth from a slot that otherwise
carries no memory at all], not bandwidth a DIMM channel could not
deliver. That framing is what makes the density dividend of
Section 4.5 the quantity such a slot is bought for.

Table 9 is the one place in this book where the modeled tracks sit
beside measured hardware, each row labelled with the kind of number it
carries.

#block(breakable: false)[
#strong[Table 9: device reference row, this book's modeled media beside
measured devices.]

#align(center)[#text(size: 9pt)[#table(
  columns: (0.95fr, 0.6fr, 1.5fr, 1.25fr, 0.6fr),
  align: (col, row) => (left,left,left,left,left,).at(col),
  inset: 4pt,
  table.header(
    [#strong[Row]],
    [#strong[Kind]],
    [#strong[Latency]],
    [#strong[Note]],
    [#strong[Source]],
  ),
  [1T1R SLC, full DIMM],
  [media],
  [GCC 41.4 to 48.3 ns; burst 353.1 to 696.6 ns],
  [smallest write penalty of the four],
  [primary CSV and the write-pulse bracket table],

  [1T1R MLC, full DIMM],
  [media],
  [GCC 44.5 to 65.8 ns; burst 512.0 to 1,649.9 ns],
  [twice the capacity per chip],
  [as above],

  [1S1R SLC, full DIMM],
  [media],
  [GCC 36.8 to 47.4 ns; burst 391.5 to 916.6 ns],
  [conditional on a selector better than production OTS],
  [as above],

  [1S1R MLC, full DIMM],
  [media],
  [GCC 37.9 to 72.4 ns; burst 652.9 to 2,498.7 ns],
  [densest track, 2.47x DDR5],
  [as above],

  [DDR5-4800 baseline],
  [media (modeled)],
  [GCC 83.1 ns; burst 234.3 ns],
  [two 32-bit subchannels, 64 B per access, JEDEC timings],
  [primary CSV],

  [DDR5, two-socket server],
  [device],
  [111 to 114 ns idle; 191 to 193 ns to the far socket],
  [measured on shipped platforms],
  [#strong[\[27\]]],

  [CXL-attached DRAM expanders],
  [device],
  [214, 239, 271 ns (ASIC), about 394 ns (FPGA), idle load-to-use],
  [shipped expander modules behind a link],
  [#strong[\[27\]], #strong[\[29\]]],

  [Optane PMem 100],
  [device],
  [305 ns idle random read; 169 ns sequential read],
  [#box[6.6 GB/s] read, #box[2.3 GB/s] write per module; no open loaded-latency figure],
  [#strong[\[15\]]],
)]]
]

#emph[The four ReRAM rows share the assumed 800 MHz interface and carry
no controller, ECC or PHY. ReRAM and DDR5 rows are the Latency\_ns column, full\_dimm, of
results/rev2026-09\_primary\_csv/processed\_bar\_chart\_metrics.csv and,
for the second figure of each range, of
results/system\_rev2026-09\_writepulse/\_csv/processed\_bar\_chart\_metrics.csv;
"burst" is the AlexNet output map. DDR5 appears twice on purpose: as
the modeled media number this book compares against (open-page run;
78.2 ns at the ReRAM configurations' close-page policy, Section 4.1),
and as the measured device latency of a real server, about a third
higher.
#strong[No ReRAM row here is a device number, and no device row is a
prediction for ReRAM.]]

The conditional statement that follows is honest in both directions.
#strong[ReRAM could serve as far memory only if a #emph[device] built
on it, controller, error correction, and a DRAM cache in front of it as
in Optane's Memory Mode #strong[\[15\]], landed in the same
few-hundred-nanosecond class as the measured CXL-attached DRAM devices
above. No published ReRAM silicon does.] The public record of non-DRAM
media behind CXL is NAND with a DRAM cache in front of it
#strong[\[42\]], #strong[\[43\]], and the far slot at hyperscale is being
filled with decommissioned DDR4 behind a 50 ns ASIC #strong[\[44\]], so the
cost bar a ReRAM far-memory device would have to clear is depreciated
DRAM, not DDR5. What the projected numbers do
say is which half of that problem is open: at 36.8 to 44.5 ns of media
latency under CPU traffic, with 1.24x to 2.47x DDR5’s die-level density
on the selector track, the device physics is not the obstacle. The
interface, the error-correction stack and the controller are.

== 5.3. Reliability: bit errors and error correction

The selector layer of Section 4.2 answers whether a 2048-cell tile can
be #emph[read] at all, not how often the bit that comes back is wrong
or what correcting it costs. Neither NVSim nor NVMain models a bit
error anywhere in this pipeline, so what follows is a literature result
set, and three categories are kept apart throughout, because literature
that conflates them is unusable here: #emph[retention] errors, a cell
drifting out of its window while idle; #emph[endurance] errors, a cell
cycled past its rating, which hard-fails; and #emph[read-disturb]
errors, a cell perturbed by the reads of its neighbours or of itself.

#emph[Layer one, the raw device rate.] For the cross-point track
#strong[no measured array bit error rate is published at all]. The only
numeric figure is a channel model: a 1024 x 1024 array at 10 ohm per
junction with an #emph[ideal] selector, which gives a read bit error
rate from 4.29 x 10#super[-4] for the best-positioned cell to
7.33 x 10#super[-2] for the worst #strong[\[31\]]. The ideal-selector
assumption is exactly what Section 4.2 exists to question, so that
figure is a model output and never silicon. The 1T1R track does have
measured macros, and they span orders of magnitude with the write
scheme: a 128 kb macro with a smart-write algorithm reports under
10#super[-7] after 10#super[6] cycles #strong[\[32\]], while HfO#sub[2]
arrays under adverse cycling sit between 10#super[-3] and
10#super[-2] #strong[\[33\]]. The usable statement is a band, and where a design lands inside it is a
write-algorithm and margin decision rather than a material property.

#emph[Layer two, what the selector itself contributes.] A measured 1S1R
selector stacked with STT-MRAM reports a per-read disturb rate of
10#super[-9] and 10#super[9] read-disturb-free cycles
#strong[\[34\]], and an ovonic-threshold-switch cross-point cell
reports a failure rate of 9% falling to 0.02% after read-endurance
optimization #strong[\[35\]]. #strong[The selector's own contribution
is therefore bounded well below the layer-one array rates], which is
the result that matters here: the 1S1R disadvantage established in
Chapter 4 is tile validity and sneak current, not error rate.

#emph[Layer three, the design point an NVM main memory actually uses.]
A design point used in the persistent-memory architecture literature
is a raw rate of 2 x 10#super[-4] corrected with BCH(2312,2048,22),
13% in code bits plus chip-level parity for about 27% total storage
overhead #strong[\[36\]]\; DRAM's
DIMM-level SECDED, by contrast, tolerates only about 10#super[-6] raw
#strong[\[37\]], and the only shipped NVM media has an SSD sibling
rated by datasheet at under one uncorrectable sector per 10#super[17]
bits #strong[\[38\]]. Side by side the three layers give the answer
this section exists for. #strong[A main memory built on published raw
ReRAM error rates is possible, but it needs SSD-class rather than
DRAM-class correction, at roughly a 27% total cost in bits.] The stronger
claim sometimes made in discussion, that the error rate rules out a
memory system altogether, is not supportable against this literature.

Two closing statements belong here. The selector layer of Section 4.2
was built independently of this literature and agrees with it: it
applies the same #strong[10% minimum read-margin criterion]
#strong[\[39\]], and the limit that binds the 2048-cell tile is the
line-resistance and tile-leakage mechanism, not a sneak-path bit error
rate. And, plainly: #strong[the modeled latencies exclude ECC decode.]
The generated configurations carry no coding block and no decoder, so
every latency in Chapter 4 is optimistic by exactly the decode time a code of
that class would add, on top of being a media rather than a
device number. Section 4.1 prices that decode at 20 and 40 ns of fixed
read-path delay (Table 4c): the CPU averages rise by the decode time
times the read fraction, 11 to 25 ns, and the direction against DDR5
survives at both values.

== 5.4. Limits of the model

Nine limits bound every number in this book, and all nine are
disclosed rather than discovered.

#strong[The 800 MHz interface is assumed]\: it carries no ReRAM
citation, the only datasheet-verified ReRAM chip I/O clocks located run
80 to 160x slower, and roughly three quarters of every ReRAM latency
average is protocol cycles at that clock; the clock sweep runs only
upward, and by the same decomposition the latency advantage would
invert around 330 MHz by linear extrapolation (Sections 2.3, 4.1).
#strong[The baseline's page policy and refresh model are choices]\: the
DDR5 baseline runs open-page with all-bank refresh while the ReRAM
configurations run close-page, so the GCC margin is 1.9 to 2.1 to one
at matched policy rather than two to one, and same-bank refresh is not
modeled (Sections 2.3, 4.1).
#strong[The write path is a bracket, not a model]\: the cell write time
is charged either as write recovery or, in the bounding run, to every
write's completion, and neither end models the program-and-verify loop
an MLC part actually runs (Section 4.1). #strong[Power is
device-only]\: both sides count memory devices, with no register clock
driver, power-management IC, PHY, termination or ReRAM-side controller,
and the ReRAM power-down energy is a no-savings placeholder
(Section 4.2). #strong[The periphery transistor class is a choice]\:
NVSim's low-operating-power profile sets the 6.94 W floor and its
low-standby-power profile removes it, the two ends of the power axis
differ by two orders of magnitude, and nothing in the model or the
literature read here decides between them (Sections 2.2, 4.2). #strong[No ECC decode sits on the primary read path]\: Section 4.1
brackets it at 20 and 40 ns of fixed delay (Table 4c) and Table 8's
usable-density column charges the 27% capacity cost, but no code-level
model ties the two together. #strong[Endurance rests on stationarity]\: every
lifetime extrapolates a write distribution measured inside a 250 ms
window to years, and the leveling schemes are modeled analytically
rather than simulated end to end (Section 4.3). #strong[Every ReRAM
timing is projected]\: no fabricated part has matched NVSim's array
core, which is why the published-silicon counterweight accompanies
every latency table. #strong[There is no CXL, controller or device
model anywhere in this book]\: Section 5.2 positions the projected
media against measured devices; it does not simulate one.

= 6. Conclusion and Future Work

At 22nm, on a matched 2048 x 2048 organization and six workloads, the
projected ReRAM DIMM has lower average memory latency than a DDR5-4800
baseline on CPU traffic and lower sustained write throughput on the
write-dominated AlexNet output-map burst, a single 4.5 us burst that it
drains in 1.02 ms against DDR5's 0.49 ms, denser than DDR5 as a
selector-gated cross-point and less dense as a transistor-gated cell at
the 20F² cell assumed here, and, per gigabyte in power, device for
device, either 12.7x to 17.4x more expensive as SLC or 0.26x to 0.94x
as cheap, depending on which periphery transistor class the device
model is told to build, a choice nothing in this book can settle. Write
endurance is the binding
constraint and the wear leveling, not the cell, decides it. Every
latency here is a media number for a projected array that no fabricated
part has matched: the same DIMM built from published silicon timings
averages 11.9 us and 379 us under GCC. #emph[Neither cell is a drop-in
DDR5 replacement at 22nm]\; the selector-gated cross-point is a density
play with competitive projected latency and a power cost per gigabyte
the model leaves open, and the transistor-gated variant matches it on
leakage and loses on area; what decides the verdict is endurance under
leveling, selector validity at the simulated tile, the error-correction
cost and the absence of a fabricated part near the projected timings.

#strong[What would overturn this verdict.] Each negative result above
carries the threshold that would reverse it, and stating them together
is the most useful thing a negative result can do. The power deficit of
the primary characterization closes if the periphery is built from
low-standby-power transistors, which the LSTP series shows directly,
or, at the low-operating-power end, only if idle gating removes at
least 94.3% of the static component with no module overhead or a larger
1T1R subarray cuts the peripheral leakage floor, and no gating fraction
closes it there once the module's own register, PMIC and PHY overhead
exceeds 0.79 W; what would settle the axis is a leakage figure from a
fabricated ReRAM die of DIMM class, which the literature read here
does not contain (Section 4.2). The 1S1R results hold at the simulated 2048 x
2048 tile only with a selector that supports that tile side, which a
production ovonic threshold switch, at 1666 cells, does not and a
FAST-class selector does (Section 4.2). A ten-year life at 64 GiB needs
a cell rated for 2.6 x 10#super[5] cycles under GCC and
2.8 x 10#super[6] under LBM with ideal leveling, or 4.3 to
6.5 x 10#super[6] under randomized Start-Gap (Section 4.3). The
cross-point's density lead holds only while the realized cell stays
near the idealized 4F²; at twice that area 22nm SLC falls below DDR5
parity (Section 4.5). And the latency advantage becomes a statement
about hardware only when a ReRAM array and interface at the assumed
800 MHz exist: at published silicon timings the same DIMM averages
11.9 us and 379 us under GCC (Section 4.1). A decoder does not overturn
it: at 40 ns on every read the SLC tracks stay 1.2x to 1.4x below the
open-page baseline and 1.1x to 1.5x below the close-page one, and the
one-cycle precharge placeholder is worth under 1% on CPU traffic
(Table 4c). Two thresholds sit on the
baseline side: the latency margin is 1.9 to 2.1 to one, not two to one,
once DDR5 runs the ReRAM configurations' close-page policy, and a
typical-current DDR5 module would widen the power deficit rather than
close it (Sections 2.3, 4.1).

Eight pieces of work follow directly from what this book could not
settle.

- #strong[Native MLC logic with the write pulse and verify on the
  path.] Replace the analytic MLC penalty with native circuit-level
  characterization of iterative sensing in NVSim, and put an
  iteration-count distribution and a verify-read cost on the request
  path instead of one scalar pulse. That is the only way the MLC
  latency question stops being a modeling-choice question.

- #strong[Faster-PHY interface parity.] The 800 MHz interface is a
  modeling choice, not a property of the media; the clock sweep of
  Section 4.1 quantifies it, and what remains open is a defensible
  ReRAM PHY rather than an assumed one.

- #strong[The Optane reference row completed with loaded-latency
  data.] Table 9 carries the only shipped NVM main memory at its idle
  measured latency; no open figure exists for it under load, and that
  gap is what keeps the row from being a full comparison.

- #strong[A CXL Type 3 device model with capacity-bound traces.] Model
  the far position directly: a memory region behind a link model,
  exposed as a CPU-less NUMA node, driven by traces that are
  #emph[capacity]-bound rather than latency-bound, which none of the
  six traces here is. The deliverable is the far-memory counterpart of
  Table 9, with this project's own rows measured rather than
  positioned.

- #strong[ECC decode on the read path, code-level.] Section 4.1 now
  brackets the decoder at 20 and 40 ns of fixed delay and Table 8
  applies the 27% capacity cost, each from a separate assumption. What
  remains is a code-level model in which the decode latency and the
  capacity cost come from the same code, with a verify-read cost on
  writes, so that the latency and density verdicts are re-derived
  together rather than bracketed apart.

- #strong[Endurance-aware scheduling.] Wear-leveling algorithms at the
  controller level, simulated end to end rather than modeled
  analytically, against the finding of Section 4.3 that a single-region
  Start-Gap recovers nothing for these footprints.

- #strong[Macro-scale 1T1R array limits.] The matched organization is a
  constraint on 1T1R rather than a description of its ceiling, and
  because chip leakage follows mat count, enlarging the 1T1R subarray
  is the most direct attack available on the peripheral-leakage floor,
  reporting leakage per gigabyte rather than latency as the primary
  metric.

- #strong[A workload that would actually use rank depth.] None of the
  six traces asks for it: the CPU traces are offered-rate limited and
  the AI traces never leave the first rank span. A trace with a large
  address footprint #emph[and] a sustained arrival rate above one
  controller's service rate would turn the strongest negative result of
  Section 4.4 into a measurement.

#strong[Data availability.] The complete simulation stack, including
the `mbmm_master.py` orchestration script, the modified NVSim and
NVMain C++ sources, the configuration generators and the tracked cell
files and DDR5 configurations, is publicly available; the frozen result
datasets this book reports are retained by the author and available on
request. The six `.nvt` traces are not distributed either: regenerating
gcc and lbm needs SPEC CPU2017 and gem5, STREAM needs gem5 and the
three AI traces SCALE-Sim, with the exact commands recorded in each
trace's tracked provenance sidecar.

#blockquote[
#strong[Project Repository:]
#link("https://github.com/uvKogan/Memristor-based-dram")[#underline[https:\/\/github.com/uvKogan/Memristor-based-dram]]
]

The two simulators are git submodules of that repository, pinned at the
patched NVMain fork `uvKogan/NVmain`, branch `ddr5-timing-fix`, commit
`c89988d`, and the patched NVSim fork `uvKogan/MBMM`, commit `9a90d44`.
A clone with `--recursive` checks out exactly the trees that produced
the numbers in this book. The primary 120-run matrix is one
invocation, 87 minutes on a standard Linux workstation; the extended
book's Appendix C lists the sensitivity series and the standalone tools
that produce the rest.

```bash
git clone --recursive https://github.com/uvKogan/Memristor-based-dram.git
cd Memristor-based-dram
python3 mbmm_master.py --all \
  --trace gcc_spec2017.nvt lbm_spec2017.nvt stream.nvt \
          gpt2_ifmap.nvt alexnet_layer1_ifmap.nvt alexnet_layer1_ofmap.nvt \
  --window-ns 250000000 --ddr5-model DDR5_4800_DRAM_subchannel \
  --channels 2 --decoder StartGap --endurance-model RowModel --silicon
```

#pagebreak(weak: true)

= References

#set text(size: 9pt)
#set par(spacing: 0.6em, leading: 0.45em)

#strong[\[1\]] M. Ahmad, \"NAND Flash\'s Reversal of Fortune Amid the AI Boom,\" #emph[EE Times], Jan. 26, 2026. \[Online\]. Available: #link("https://www.eetimes.com/nand-flashs-reversal-of-fortune-amid-the-ai-boom/")[#underline[https:\/\/www.eetimes.com/nand-flashs-reversal-of-fortune-amid-the-ai-boom/]]. \[Accessed: Apr. 25, 2026\].

#strong[\[2\]] International Roadmap for Devices and Systems (IRDS), \"More Moore,\" 2024. \[Online\]. Available: #link("https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MM.pdf")[#underline[https:\/\/irds.ieee.org/images/files/pdf/2024/2024IRDS\_MM.pdf]].

#strong[\[3\]] X. Dong et al., \"NVSim: A Circuit-Level Performance, Energy, and Area Model for Emerging Nonvolatile Memory,\" #emph[IEEE Trans. Comput.-Aided Design Integr. Circuits Syst.], vol. 31, no. 7, pp. 994-1007, July 2012.

#strong[\[4\]] M. Poremba, T. Zhang, and Y. Xie, \"NVMain 2.0: A user-friendly memory simulator to model (non-)volatile memory systems,\" IEEE Comput. Archit. Lett., vol. 14, no. 2, pp. 140-143, July-Dec. 2015.

#strong[\[5\]] H.-S. P. Wong et al., \"Metal-Oxide RRAM,\" #emph[Proc. IEEE], vol. 100, no. 6, pp. 1951-1970, June 2012. DOI: 10.1109/JPROC.2012.2190369

#strong[\[6\]] C. Xue et al., \"16.1 A 22nm 4Mb 8b-Precision ReRAM Computing-in-Memory Macro with 11.91 to 195.7TOPS/W for Tiny AI Edge Devices,\" #emph[2021 IEEE International Solid-State Circuits Conference (ISSCC)], San Francisco, CA, USA, 2021, pp. 245-247.

#strong[\[7\]] C. Matsui, A. Yamada, N. Misawa, and K. Takeuchi, \"ReRAM resistance design of LRS and HRS for ultrahigh-capacity digital memory and analog Computation-in-Memory,\" IEICE Trans. Fundamentals, vol. E109.A, no. 3, pp. 596-603, Mar. 2026. DOI: 10.1587/transfun.2025VLP0011

#strong[\[8\]] S. H. Jo et al., \"3D-stackable crossbar resistive memory based on Field Assisted Superlinear Threshold (FAST) selector,\" #emph[2014 IEEE International Electron Devices Meeting (IEDM)], San Francisco, CA, USA, 2014, pp. 6.7.1-6.7.4.

#strong[\[9\]] J. Zhou, K.-H. Kim, and W. Lu, \"Crossbar RRAM Arrays: Selector Device Requirements During Read Operation,\" #emph[IEEE Trans. Electron Devices], vol. 61, no. 5, pp. 1369-1376, May 2014.

#strong[\[10\]] A. Levy, L. R. Upton, M. D. Scott, D. Rich, W.-S. Khwa, Y.-D. Chih, M.-F. Chang, S. Mitra, B. Murmann, and P. Raina, \"EMBER: Efficient Multiple-Bits-Per-Cell Embedded RRAM Macro for High-Density Digital Storage,\" #emph[IEEE J. Solid-State Circuits], vol. 59, no. 7, pp. 2081-2092, July 2024. DOI: 10.1109/JSSC.2024.3387566

#strong[\[11\]] L. R. Upton et al., \"EMBER: A 100 MHz, 0.86 mm2, multiple-bits-per-cell RRAM macro in 40 nm CMOS with compact peripherals and 1.0 pJ/bit read circuitry,\" in Proc. IEEE 49th Eur. Solid State Circuits Conf. (ESSCIRC), Sep. 2023, pp. 469-472.

#strong[\[12\]] J. Zahurak et al., \"Process Integration of a 27nm, 16Gb Cu ReRAM,\" in #emph[Proc. IEEE Int. Electron Devices Meeting (IEDM)], Dec. 2014.

#strong[\[13\]] T.-y. Liu et al., \"A 130.7-mm² 2-Layer 32-Gb ReRAM Memory Device in 24-nm Technology,\" #emph[IEEE J. Solid-State Circuits], vol. 49, no. 1, pp. 140-153, Jan. 2014.

#strong[\[14\]] D. Kau, S. Tang, I. V. Karpov, R. Dodge, B. Klehn, J. A. Kalb, J. Strand, A. Diaz, N. Leung, J. Wu, S. Lee, T. Langtry, K.-W. Chang, C. Papagianni, J. Lee, J. Hirst, S. Erra, E. Flores, N. Righos, H. Castro, and G. Spadini, \"A Stackable Cross Point Phase Change Memory,\" in #emph[2009 IEEE International Electron Devices Meeting (IEDM)], Baltimore, MD, Dec. 2009, pp. 617-620. DOI: 10.1109/IEDM.2009.5424263

#strong[\[15\]] J. Izraelevitz, J. Yang, L. Zhang, J. Kim, X. Liu, A. Memaripour, Y. J. Soh, Z. Wang, Y. Xu, S. R. Dulloor, J. Zhao, and S. Swanson, \"Basic Performance Measurements of the Intel Optane DC Persistent Memory Module,\" arXiv:1903.05714, Aug. 2019.

#strong[\[16\]] JEDEC Solid State Technology Association, \"DDR5 SDRAM Standard,\" JESD79-5D, Nov. 2025. \[Online\]. Available: #link("https://www.jedec.org/standards-documents/docs/jesd79-5d")[#underline[https:\/\/www.jedec.org/standards-documents/docs/jesd79-5d]]. Access-gated; the values used here were read from Micron Technology, \"DDR5 SDRAM\" core product data sheet, Doc. CCM005-1684161373-23, Rev. D, Oct. 2022, the vendor's transcription of the standard, and checked against two DDR5-4800 module datasheets (extended book, reference [101]).

#strong[\[17\]] B. C. Lee, E. Ipek, O. Mutlu, and D. Burger, \"Architecting phase change memory as a scalable dram alternative,\" in #emph[Proc. 36th Annu. Int. Symp. Comput. Archit. (ISCA)], 2009, pp. 2-13.

#strong[\[18\]] N. Binkert et al., \"The gem5 Simulator,\" ACM SIGARCH Computer Architecture News, vol. 39, no. 2, pp. 1-7, May 2011. DOI: 10.1145/2024716.2024718

#strong[\[19\]] A. Samajdar, J. M. Joseph, Y. Zhu, P. Whatmough, M. Mattina, and T. Krishna, \"A Systematic Methodology for Characterizing Scalability of DNN Accelerators Using SCALE-Sim,\" in #emph[Proc. IEEE Int. Symp. Perform. Anal. Syst. Softw. (ISPASS)], 2020, pp. 58-68.

#strong[\[20\]] Standard Performance Evaluation Corporation, \"SPEC CPU 2017 Benchmark Suite.\" \[Online\]. Available: https:\/\/www.spec.org/cpu2017/. \[Accessed: Jul. 13, 2026\].

#strong[\[21\]] J. D. McCalpin, \"Memory Bandwidth and Machine Balance in Current High Performance Computers,\" IEEE Computer Society Technical Committee on Computer Architecture (TCCA) Newsletter, pp. 19-25, Dec. 1995.

#strong[\[22\]] W. Wan et al., \"Edge AI without Compromise: Efficient, Versatile and Accurate Neurocomputing in Resistive Random-Access Memory,\" preprint, arXiv:2108.07879, Aug. 2021 (the NeuRRAM chip; iterative program-and-verify writing of multi-level 1T1R cells).

#strong[\[23\]] C. Xie et al., \"Speeding Up the Write Operation for Multi-Level Cell Phase Change Memory with Programmable Ramp-Down Current Pulses,\" #emph[Micromachines], vol. 10, no. 7, p. 461, 2019. DOI: 10.3390/mi10070461 (more than 70 iterations for a 9.7 us total write; under 1.6 us with the verify step skipped), PMC6680789. \[Online\]. Available: #link("https://pmc.ncbi.nlm.nih.gov/articles/PMC6680789/")[#underline[https:\/\/pmc.ncbi.nlm.nih.gov/articles/PMC6680789/]].

#strong[\[24\]] K. T. Malladi, F. A. Nothaft, K. Periyathambi, B. C. Lee, C. Kozyrakis, and M. Horowitz, \"Towards Energy-Proportional Datacenter Memory with Mobile DRAM,\" in Proc. 39th Annu. Int. Symp. Computer Architecture (ISCA), 2012, pp. 37-48. DOI: 10.1109/ISCA.2012.6237004

#strong[\[25\]] Y. Chen, \"ReRAM: History, Status, and Future,\" #emph[IEEE Trans. Electron Devices], vol. 67, no. 4, pp. 1420-1433, Apr. 2020.

#strong[\[26\]] M. K. Qureshi, J. Karidis, M. Franceschini, V. Srinivasan, L. Lastras, and B. Abali, \"Enhancing Lifetime and Security of PCM-Based Main Memory with Start-Gap Wear Leveling,\" in #emph[Proc. 42nd Annu. IEEE/ACM Int. Symp. Microarchitecture (MICRO)], 2009, pp. 14-23.

#strong[\[27\]] J. Liu, H. Hadian, H. Xu, D. S. Berger, and H. Li, \"Dissecting CXL Memory Performance at Scale: Analysis, Modeling, and Optimization,\" preprint, arXiv:2409.14317, Sept. 2024, the version read here; published as J. Liu et al., \"Systematic CXL Memory Characterization and Performance Analysis at Scale,\" in #emph[Proc. 30th ACM Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS)], 2025. DOI: 10.1145/3676641.3715987 (measured idle latency of local and remote-socket DDR5 and of CXL-attached DRAM devices).

#strong[\[28\]] H. Li, D. S. Berger, L. Hsu, D. Ernst, P. Zardoshti, S. Novakovic, M. Shah, S. Rajadnya, S. Lee, I. Agarwal, M. D. Hill, M. Fontoura, and R. Bianchini, \"Pond: CXL-Based Memory Pooling Systems for Cloud Platforms,\" in #emph[Proc. 28th ACM Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS)], vol. 2, Mar. 2023, pp. 574-587. DOI: 10.1145/3575693.3578835; preprint arXiv:2203.00241 (local DDR4 platform baselines of 78 and 115 ns, pooling latency overheads, workload latency-acceptability study).

#strong[\[29\]] Y. Sun et al., \"Demystifying CXL Memory with Genuine CXL-Ready Systems and Devices,\" in #emph[Proc. 56th Annu. IEEE/ACM Int. Symp. Microarchitecture (MICRO)], 2023, pp. 105-121. DOI: 10.1145/3613424.3614256; preprint arXiv:2303.15375.

#strong[\[30\]] Linux kernel documentation, \"NUMA performance\" (ACPI HMAT latency and bandwidth attributes exposed per initiator-target pair). \[Online\]. Available: #link("https://docs.kernel.org/admin-guide/mm/numaperf.html")[#underline[https:\/\/docs.kernel.org/admin-guide/mm/numaperf.html]].

#strong[\[31\]] Z. Chen and L. Dolecek, \"Write and Read Channel Models for 1S1R Crossbar Resistive Memory with High Line Resistance,\" in #emph[Proc. IEEE Global Communications Conf. (GLOBECOM)], 2020. DOI: 10.1109/GLOBECOM42002.2020.9322521; preprint arXiv:1912.02963 (channel-model bit error rates for a 1024 x 1024 1S1R array, 10 ohm per junction, ideal selector; read and write error rates by cell position).

#strong[\[32\]] B. Giraud et al., \"Smart Write Algorithm to Enhance Performances and Reliability of an RRAM Macro,\" #emph[IEEE J. Solid-State Circuits], vol. 59, no. 9, pp. 3045-3057, Sept. 2024. DOI: 10.1109/JSSC.2024.3386429 (128 kb 1T1R macro: below 10#super[-7] after 10#super[6] cycles); summarized at Weebit Nano, smart-write algorithm technical resource. \[Online\]. Available: #link("https://www.weebit-nano.com/technical_resources/smart-write-algorithm-to-enhance-performances-and-reliability-of-an-rram-macro/")[#underline[https:\/\/www.weebit-nano.com/technical\_resources/smart-write-algorithm-to-enhance-performances-and-reliability-of-an-rram-macro/]].

#strong[\[33\]] M. Bocquet et al., \"In-Memory and Error-Immune Differential RRAM Implementation of Binarized Deep Neural Networks,\" in #emph[Proc. IEEE Int. Electron Devices Meeting (IEDM)], Dec. 2018. DOI: 10.1109/IEDM.2018.8614639; preprint arXiv:1902.02528 (raw bit error rate of 1T1R HfO#sub[2] RRAM arrays under cycling, including a 2T2R variant).

#strong[\[34\]] E. Ambrosi et al., \"Low voltage (\<1.8 V) and high endurance (\>1M) 1-Selector/1-STT-MRAM with ultra-low (1 ppb) read disturb for high density embedded memory arrays,\" in #emph[Proc. IEEE Int. Electron Devices Meeting (IEDM)], Dec. 2023. DOI: 10.1109/IEDM45741.2023.10413809 (10#super[-9] per-read disturb rate, 10#super[9] read-disturb-free cycles). \[Online\]. Available: #link("https://ieeexplore.ieee.org/document/10413809/")[#underline[https:\/\/ieeexplore.ieee.org/document/10413809/]].

#strong[\[35\]] IBM Research, \"Enhancing 3D XPT/SOM reliability: strategies for mitigating spike current and improving read endurance,\" IMW 2025 (cell failure rate 9% falling to 0.02% after read-endurance optimization). \[Online\]. Available: #link("https://research.ibm.com/publications/enhancing-3d-xptsom-reliability-strategies-for-mitigating-spike-current-and-improving-read-endurance")[#underline[https:\/\/research.ibm.com/publications/enhancing-3d-xptsom-reliability-strategies-for-mitigating-spike-current-and-improving-read-endurance]].

#strong[\[36\]] D. Zhang, V. Sridharan, and X. Jian, \"Exploring and Optimizing Chipkill-Correct for Persistent Memory Based on High-Density NVRAMs,\" in #emph[Proc. 51st Annu. IEEE/ACM Int. Symp. Microarchitecture (MICRO)], 2018, pp. 710-723. DOI: 10.1109/MICRO.2018.00063 (2 x 10#super[-4] raw design point, BCH(2312,2048,22), about 27% coding overhead); reached through H. Volos, \"The Case for Replication-Aware Memory-Error Protection in Disaggregated Memory,\" #emph[IEEE Computer Architecture Letters], vol. 20, no. 2, 2021, arXiv:2309.00304, which cites it.

#strong[\[37\]] P. J. Nair, D.-H. Kim, and M. K. Qureshi, \"ArchShield: Architectural Framework for Assisting DRAM Scaling by Tolerating High Error Rates,\" in #emph[Proc. 40th Annu. Int. Symp. Computer Architecture (ISCA)], 2013, pp. 72-83. DOI: 10.1145/2485922.2485929 (DRAM on-die SECDED tolerates about 10#super[-6] raw); consulted through P. J. Nair, \"Architectural Techniques to Enable Reliable and Scalable Memory Systems,\" Ph.D. dissertation, Georgia Inst. of Technology, 2017, arXiv:1704.03991.

#strong[\[38\]] Intel Corporation, Intel Optane SSD 905P series product specifications (uncorrectable bit error rate under 1 sector per 10#super[17] bits). \[Online\]. Available: #link("https://www.intel.com/content/www/us/en/products/sku/147526/intel-optane-ssd-905p-series-1-5tb-2-5in-pcie-x4-3d-xpoint/specifications.html")[#underline[https:\/\/www.intel.com/content/www/us/en/products/sku/147526/intel-optane-ssd-905p-series-1-5tb-2-5in-pcie-x4-3d-xpoint/specifications.html]].

#strong[\[39\]] A. Tyagi and S. Kvatinsky, \"Assessing the Performance of Stateful Logic in 1-Selector-1-RRAM Crossbar Arrays,\" in #emph[Proc. IEEE Int. Symp. Circuits and Systems (ISCAS)], 2024. DOI: 10.1109/ISCAS58744.2024.10558539; preprint arXiv:2407.10466 (read-margin analysis of 1R against 1S1R crossbar arrays; the 10% minimum read-margin criterion).

#strong[\[40\]] J. Choe, \"Comparing DDR5 Memory From Micron, Samsung, SK Hynix,\" #emph[EE Times], Feb. 15, 2022. \[Online\]. Available: #link("https://www.eetimes.com/comparing-ddr5-memory-from-micron-samsung-sk-hynix/")[#underline[https:\/\/www.eetimes.com/comparing-ddr5-memory-from-micron-samsung-sk-hynix/]]. \[Accessed: Jul. 12, 2026\].

#strong[\[41\]] M. Rudan, R. Brunetti, and S. Reggiani, Eds., #emph[Springer Handbook of Semiconductor Devices]. Cham, Switzerland: Springer, 2023 (crossbar tile limit, Fig. 17.21, pp. 642-643, after Molas et al., IMW 2020; OTS selector currents, Table 30.3).

#strong[\[42\]] S.-P. Yang, M. Kim, S. Nam, J. Park, J.-Y. Choi, E. H. Nam, E. Lee, S. Lee, and B. S. Kim, \"Overcoming the Memory Wall with CXL-Enabled SSDs,\" in #emph[Proc. USENIX Annu. Technical Conf. (ATC)], Jul. 2023, pp. 601-617.

#strong[\[43\]] J. Zeng et al., \"Performance Characterizations and Usage Guidelines of Samsung CXL Memory Module Hybrid Prototype,\" preprint, arXiv:2503.22017, Mar. 2025.

#strong[\[44\]] N. Gholkar, J. Stojkovic, H. Al Maruf, G. Price, P. Chauhan, H. Patel, C. Van Goethem, K. Vemuri, K. Sriadibhatla, K. Subramanian, S. Kanaujia, C. Tang, and A. Dhanotia, \"Vistara: Making CXL Real: Full Path from ASIC Design and OS Support to Hyperscale Deployment,\" in #emph[Proc. 53rd Annu. Int. Symp. Computer Architecture (ISCA)], industry session, 2026.

#strong[\[45\]] M. K. Qureshi, V. Srinivasan, and J. A. Rivers, \"Scalable High Performance Main Memory System Using Phase-Change Memory Technology,\" in #emph[Proc. 36th Annu. Int. Symp. Computer Architecture (ISCA)], 2009, pp. 24-33. DOI: 10.1145/1555754.1555760

#strong[\[46\]] P. Zhou, B. Zhao, J. Yang, and Y. Zhang, \"A Durable and Energy Efficient Main Memory Using Phase Change Memory Technology,\" in #emph[Proc. 36th Annu. Int. Symp. Computer Architecture (ISCA)], 2009, pp. 14-23. DOI: 10.1145/1555754.1555759

#strong[\[47\]] C. Xu, D. Niu, N. Muralimanohar, R. Balasubramonian, T. Zhang, S. Yu, and Y. Xie, \"Overcoming the Challenges of Crossbar Resistive Memory Architectures,\" in #emph[Proc. 21st IEEE Int. Symp. High Performance Computer Architecture (HPCA)], 2015, pp. 476-488. DOI: 10.1109/HPCA.2015.7056056

#strong[\[48\]] E. Kültürsay, M. Kandemir, A. Sivasubramaniam, and O. Mutlu, \"Evaluating STT-RAM as an Energy-Efficient Main Memory Alternative,\" in #emph[Proc. IEEE Int. Symp. Performance Analysis of Systems and Software (ISPASS)], 2013, pp. 256-267. DOI: 10.1109/ISPASS.2013.6557176

#strong[\[49\]] H. A. Maruf, H. Wang, A. Dhanotia, J. Weiner, N. Agarwal, P. Bhattacharya, C. Petersen, M. Chowdhury, S. Kanaujia, and P. Chauhan, \"TPP: Transparent Page Placement for CXL-Enabled Tiered-Memory,\" in #emph[Proc. 28th ACM Int. Conf. Architectural Support for Programming Languages and Operating Systems (ASPLOS)], vol. 3, Mar. 2023, pp. 742-755; preprint arXiv:2206.02878.

#set text(size: 12pt)


