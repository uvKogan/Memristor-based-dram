// MBMM Project Book — Typst edition (faithful copy of MBMM Project Book UPDATED.docx)
// GEN-BEGIN preamble
#let blockquote(body) = block(
  inset: (left: 1.2em, top: 0.3em, bottom: 0.3em),
  stroke: (left: 2pt + luma(160)),
  quote(block: true, body)
)
#set page(paper: "us-letter", margin: 1in, numbering: none)
#set text(font: ("Carlito", "DejaVu Sans"), size: 11pt, lang: "en")
#set par(justify: false)
#show heading.where(level: 1): set text(size: 16pt)
#show heading.where(level: 2): set text(size: 13pt)
#show heading.where(level: 3): set text(size: 11.5pt)
#show heading: set block(above: 1.2em, below: 0.8em)

#align(center)[
  #v(2in)
  #text(size: 20pt, weight: "bold")[Evaluation of 22nm Memristor-Based Main Memory (MBMM) in Commodity DIMM Architectures]
]
#pagebreak()
// GEN-END preamble

= Abstract
<abstract>
The memory supply-demand gap of late 2025, driven by the reallocation of
DRAM wafers to High-Bandwidth Memory (HBM) for AI #strong[\[1\], \[2\]],
necessitates alternative technologies for commodity main memory. This
research evaluates 22nm Memristor-based Non-Volatile Memory (NVM) as a
DRAM replacement in standard DIMMs. Utilizing a cross-layer pipeline
bridging NVSim #strong[\[3\]] and NVMain 2.0 #strong[\[4\]], I
characterize 1T1R (transistor-gated) and 1S1R (selector-gated)
architectures across six benchmarks spanning compute-bound,
memory-streaming, and AI-inference workloads. Under
bandwidth-saturating, high-MLP workloads, multi-rank configurations
achieve substantial latency reductions through rank-level interleaving.
However, single-threaded latency-bound workloads exhibit a \"Flatline
Paradox\": insufficient Memory Level Parallelism (MLP) leaves ranks
idle, preventing latency or power scaling regardless of chip count.

The key quantitative results are: (1) In wall-clock latency, 1T1R SLC
ReRAM operates within 1.61x of DDR5-4800 under compute-bound workloads -
where it runs 49x faster than the legacy PCM baseline (13-16x under
sustained streaming) - while trailing DDR5 by 4.7x under
high-parallelism AI inference; the selector-gated 1S1R SLC follows 1T1R
at a \~1.5x average-latency cost (1.3-1.7x across the suite) while
offering 1.9x DDR5\'s die-level density (3.8x as MLC). (2) Under a
repaired, ungated power model, selector-gated 1S1R ReRAM emerges as a
credible low-power path past DRAM: a full module draws 1.12 W - 1.7x
DDR5\'s 0.651 W at the conservative calibration floor, and within 11% of
outright parity at the vendor spec-limit ceiling - with zero refresh
cost, and because that draw is 97% static, essentially all of it is
exposed to idle-power gating, which remains unexercised (NVMain\'s
power-down machinery is disabled in source). One credible gating policy
separates 1S1R SLC from DDR5 power parity, while DDR5 spends 33-45% of
its module power on refresh it can never shed - a concrete opening for
gating-capable memory controllers and selector-first DIMM designs. The
contrast that proves the point: the transistor-gated 1T1R module leaks
50.9 W (50-78x DDR5) - infeasible ungated at DIMM scale - so the
selector\'s 47x leakage discipline, not raw cell speed, decides
architectural viability, and 1S1R SLC is the flagship configuration.
These power results rest on a fidelity audit of the simulation flow
(Section 3.1.6) that found eleven silent failure modes in the standard
NVSim-to-NVMain toolchain - a mixed-clock-domain efficiency metric, two
silently ignored parameter families (leakage and access energy), a
technology-blind static-power default, single-rank power reported as
system power, a disabled power-down model, weak trace provenance, DDR5
refresh timing and supply parameters inherited unrescaled from a
DDR3-era template, a PCM baseline running at twice its cited clock
basis, and heterogeneous host-CPU frequencies that replayed each
technology against a different offered load and admitted trace
population - of which this work repaired nine, validating every repair
against device-level anchors (0.0% error) or exact predicted arithmetic,
and re-running the affected simulations (the DRAM and PCM baselines
model standard idle behavior; ReRAM figures are worst-case ungated). (3)
DIMM write endurance scales linearly with module capacity: at the
modeled 8 GB SLC module, worst-case sustained streaming (LBM) yields 1.1
years - below the 5-10 year server replacement target - but at the
64-128 GB capacities where ReRAM\'s density advantage is actually
realized, worst-case SLC lifetime reaches 9-17 years (the slower-writing
selector variant, 12-25), while compute-bound and read-dominant
workloads clear the target severalfold to a hundredfold even at 8 GB.
Endurance is thus a capacity- and workload-dependent design constraint
rather than a categorical barrier. (4) Read latency is invariant to a
±20% ReadVoltage perturbation, with Power-Delay Product changing less
than 4%, confirming robustness to supply voltage variation and
operating-point selection.

ReRAM write-latency penalties are workload-dependent and are confined to
write-active workloads, positioning selector-gated 22nm SLC ReRAM as a
latency-competitive, density-superior DDR5 alternative for compute-bound
and streaming workloads, with a clear research path - restoring
idle-power gating to both the simulation stack and the architecture -
standing between it and outright power parity. High-parallelism AI
inference remains DDR5 territory.

// GEN-BEGIN toc
= Table of Contents
<table-of-contents>
#outline(title: none, indent: auto)
// GEN-END toc

= List of Figures
<list-of-figures>
// GEN-BEGIN lof
- Figure 1: Average Total Latency under the compute-bound GCC (SPEC2017)

- Figure 2: Average Total Latency under the continuous memory-streaming LBM (SPEC2017)

- Figure 3: Average Total Latency under the parallel read-storm of GPT-2 Inference (IFMAP)

- Figure 4 & 5: Average Total Latency under AlexNet Layer 1 IFMAP (pure-read)

- Figure 6: Average Total Latency under the STREAM memory bandwidth benchmark.

- Figure 7: System Power Breakdown (Static / Dynamic / Refresh)

- Figure 8: System Power Breakdown (Static / Dynamic / Refresh)

- Figure 9: System Power Breakdown (Static / Dynamic / Refresh)

- Figure 10: System Power Breakdown (Static / Dynamic / Refresh)

- Figure 11 & 12: System Power Breakdown (Static / Dynamic / Refresh)

- Figure 13 & 14: Power-Delay Product under single-threaded compute (GCC SPEC2017)

- Figure 15 & 16: Power-Delay Product under heavy continuous memory-streaming workloads (LBM SPEC2017 and STREAM)

- Figure 17 & 18: Power-Delay Product under AlexNet Layer 1 IFMAP (Read-Heavy)

- Figure 19: ReadVoltage Sensitivity Analysis - 1T1R SLC Full DIMM (LBM and GCC, +/-20% sweep)

- Figure 20: Pareto scaling trajectory under the single-threaded GCC workload.

- Figure 21 & 22: Pareto scaling trajectories under highly parallel AI inference workloads (GPT-2 IFMAP and AlexNet IFMAP)

- Figure 23: Pareto scaling trajectory under write-torture conditions (AlexNet OFMAP)

- Figure 24 & 25: Pareto scaling trajectories under continuous memory-streaming workloads (LBM SPEC2017 and STREAM)

- Figure 26: Die-Level Density Comparison, normalized to DDR5 \= 1.

- Figure 27: Overall System Efficiency (Geometric Mean PDP)
// GEN-END lof
= List of Tables
<list-of-tables>
// GEN-BEGIN lot
- Table 1: NVSim device-level characterization per 1 Gb chip (22nm FinFET LOP, 1.

- Table 2: Average total latency (ns)

- Table 3: Total module power (W)

- Table 4: Power-Delay Product (W·ns \= nJ)

- Table 5: Projected DIMM Write Endurance Lifetime (1T1R SLC Full DIMM, physical capacity 8 GB, 66.

- Table 7: Projected die-level density versus DDR5 (\= 1.

- Table 6: Cross-technology summary, full-DIMM configurations.
// GEN-END lot
#pagebreak()
= 1. Introduction & Background
<introduction-background>
== 1.1. Project Context
<project-context>
- #strong[The External Memory Wall]: Traditional DRAM is struggling to
  meet the bandwidth requirements of modern processors due to physical
  scaling limits, specifically capacitor leakage and transistor
  short-channel effects #strong[\[5\]].

- #strong[Economic Drivers]: By late 2025, the massive reallocation of
  DRAM wafers to AI-focused HBM production created a severe
  supply-demand gap for commodity main memory #strong[\[1\], \[2\]].

- #strong[The Objective]: This project investigates whether
  memristor-based non-volatile memory (NVM) can effectively substitute
  traditional DRAM in standard DIMM modules to alleviate this
  constraint.

- #strong[The Endurance Constraint]: However, deploying NVM as main
  memory introduces a critical challenge: endurance. Because physical
  wear-out limits are the primary bottleneck of memristive technologies,
  a viable DRAM alternative necessitates architectural interventions to
  prevent premature device failure.

== 1.2. ReRAM Fundamentals
<reram-fundamentals>
- #strong[Process Selection:] I standardized on 22nm FinFET LOP (Low
  Operating Power). This node allows for logic-compatible integration
  #strong[\[8\]] while the LOP profile aligns with the thermal and power
  constraints of high-capacity main memory replacement. The choice also
  frames the entire comparison conservatively: commodity DDR5 is
  fabricated on 10 nm-class DRAM nodes (1γ \[17\]) that sit at the end
  of the capacitor\'s scaling roadmap \[5\], whereas 22nm is a mature,
  logic-compatible CMOS node with several shrink generations of headroom
  still ahead of it - the density figures in this evaluation are
  therefore a floor on ReRAM\'s potential, not a ceiling.

- #strong[Resistance Design:] Cells are calibrated to high resistance
  targets ($10^5 Omega$ LRS and $10^9 Omega$ HRS) #strong[\[7\]] to
  mitigate IR-drop on 1024-cell bitlines, ensuring reliable sensing
  margins.

- #strong[Device Structures & Sneak-Path Mitigation:] I evaluate two
  distinct hardware topologies to handle array sneak-paths:

  - #strong[1T1R (Transistor-based):] Utilizes CMOS access transistors
    to completely eliminate sneak-paths. While this results in a
    logic-compatible but larger bit-cell area of approximately $20 F^2$
    #strong[\[3\], \[14\]], modern commercial foundries currently
    mass-produce 22nm 1T1R embedded ReRAM (eReRAM) macros at
    multi-megabyte scales #strong[\[8\]], inherently validating its
    manufacturability far beyond the 1Mb subarrays evaluated here.

  - #strong[1S1R (Selector-based):] Suppresses local sneak-paths via
    highly non-linear thresholding. While academic 1S1R test-chips
    frequently restrict subarray sizes to manage leakage, industry
    milestones - such as Crossbar Inc.\'s fabrication of a 4Mb
    cross-point array utilizing a super-linear threshold selector
    #strong[\[9\]] - demonstrate the physical viability of massive
    crossbar scaling. Building on this foundation, combining the NVSim
    non-linear selector model #strong[\[3\]] with the aforementioned
    ultra-high resistance calibration #strong[\[7\]] provides a
    theoretical architectural projection capable of scaling to 1024-cell
    bitlines. This reduces the cell to an idealized $4 F^2$, enabling a
    significant footprint reduction for high-density DIMMs.

- #strong[Area Realism over Financial Metrics:] To evaluate module cost
  and density objectively across these topologies, I utilize
  area-per-bit ($F^2$) rather than financial cost-per-bit, isolating
  architectural evaluation from fabrication economics and market
  volatility.

= 2. Infrastructure & Methodology
<infrastructure-methodology>
== 2.1. Decentralized Structure & Simulation Stack
<decentralized-structure-simulation-stack>
- #strong[The Bridge:] I developed a cross-layer pipeline that
  automatically translates device-level physical metrics from NVSim
  (Area, absolute Latency in nanoseconds, Energy) into cycle-accurate
  architectural parameters for NVMain 2.0 (JEDEC timing constraints such
  as Column Address Strobe latency (tCAS), Row-to-Column Delay (tRCD),
  Row Precharge time (tRP), and dynamic energy-per-access coefficients).
  \
  Core memristive cell parameters and resistance targets were rigorously
  calibrated against established silicon fabrication literature. A full
  table of these electrical parameters and their corresponding
  references is provided in #strong[Appendix A].

- #strong[Simulation Pipeline]: The pipeline follows a structured
  sequence: hardware characterization in NVSim $arrow.r$ diagnostic
  extraction to JSON $arrow.r$ system configuration generation $arrow.r$
  cycle-accurate trace execution in NVMain.

- #strong[Decoupled Benchmarking]: To ensure simulation stability, I
  bypassed brittle integrated wrappers in favor of a robust trace-based
  pipeline utilizing gem5 v25.1 memory access logs. \
  I transitioned to 602.gcc and 619.lbm using gem5\'s X86O3CPU
  (Out-of-Order). The audit of Section 3.1.6 later established that
  these traces were captured without L1/L2 caches or warmup (raw
  CPU-to-memory stream, first 10M instructions), so they represent
  maximum memory pressure rather than cache-filtered traffic - a
  conservative choice for endurance bounds, and a documented limitation
  for absolute latency magnitudes.

== 2.2. Validation & Protocol
<validation-protocol>
- #strong[The Gate-Keeper]: All architectural conclusions are gated by
  the #strong[mbmm\_master.py] script. This script mandates a validation
  flow of cleaning build artifacts, recompiling the C++ engines, and
  passing a sanity-check simulation before data is accepted.

- #strong[Critical C++ Repairs]: To modernize the legacy simulation
  engines, I applied legacy compatibility patches:

  - #blockquote[
    #strong[NVSim]: Enforced -std\=c++11 to resolve namespace collisions
    between MemoryType::data and std::data in modern GCC.
    ]

  - #blockquote[
    #strong[NVMain]: Repaired a fatal memory deallocation bug in
    FlipNWrite.cpp (mismatched new/delete) that triggered SIGSEGV
    failures.
    ]

  - #blockquote[
    #strong[Build Migration]: Migrated the legacy build system from
    Python 2 to #strong[Python 3] using 2to3.
    ]

  - #blockquote[
    #strong[MLC Analytical Modeling]: Prior to simulating Multi-Level
    Cell (MLC) scaling, I established the physical and architectural
    differences between SLC and MLC. Recognizing that NVSim lacks native
    support for the complex Analog-to-Digital (ADC) sensing and
    Iterative Step-and-Verify (ISPV) programming required for MLC, I
    implemented an Analytical Penalty Method (3x read / 4x write latency
    factors derived from EMBER macro heuristics \[6\], consistent with
    published multi-level ReRAM characterization \[13\]) rather than
    relying on NVSim\'s native MLC implementation, which triggers a
    floating-point exception in Mat.cpp\'s ISPV sensing logic.
    ]

== 2.3. Hardware Baselines & Memory Models
<hardware-baselines-memory-models>
- #strong[The DDR5-4800 Baseline Reference:] The DDR5 configuration is
  modeled strictly after the JEDEC Solid State Technology Association,
  Standard JESD79-5 (DDR5 SDRAM) \[10\]. I engineered the timing
  parameters for a 4800 MT/s module (tCAS-tRCD-tRP of 34-34-34 at 1.1V)
  and explicitly modeled DDR5\'s defining architectural upgrade: two
  independent 32-bit sub-channels per DIMM and a Burst Length of 16.
  This model inherently imposes the rigorous, real-world JEDEC bus
  serialization and complex bank-group switching penalties that define
  modern commodity DIMM performance. Refresh is modeled explicitly to
  the same standard: an all-bank refresh command every tREFI \= 3.906 µs
  (the JEDEC 32 ms retention window spread over 8,192 commands), each
  occupying tRFC \= 295 ns, at the DDR5 supply of 1.1 V, with refresh
  energy accumulated in dedicated rank-level counters - the source of
  the refresh decomposition in Section 3.1.2. These refresh and voltage
  parameters were corrected during the fidelity audit (Section 3.1.6,
  items 7-8) after being found inherited, unrescaled, from a DDR3-1333
  template configuration.

- #strong[The Microsoft PCM 2009 Baseline:] A legacy non-volatile memory
  baseline modeled after the architectural parameters established by Lee
  et al. #strong[\[11\]], used to benchmark modern 22nm ReRAM against
  older NVM scaling constraints. It runs at its cited derivation basis
  of CLK \= 400 MHz - restored during the fidelity audit (Section 3.1.6,
  item 9) after a stray clock override was found running it twice as
  fast as its timing parameters intend - and runs a 33.3M-cycle budget
  at that basis - the matched-host window of Section 3.1.6, item 11:
  83.33 ms wall-clock and an identical admitted trace population for
  every configuration.

- #strong[The ReRAM DIMM Interface (800 MHz):] All ReRAM configurations
  run behind an 800 MHz (1600 MT/s) DIMM interface - a deliberate
  modeling choice, not a device limit. The interface clock sets only
  command granularity and the channel\'s bandwidth ceiling; the
  NVSim-characterized cell latencies are specified in nanoseconds and
  are clock-independent by construction (a 32.13 ns 1T1R read occupies
  26 cycles at 800 MHz and would occupy 77 at 2400 MHz - the same
  wall-clock time). The rate is positioned between two precedents: twice
  the 400 MHz basis of NVMain\'s PCM reference lineage \[11\], and below
  the DDR4-class DDR-T interface of Intel\'s shipped Optane
  persistent-memory DIMMs \[23\] - the industry precedent that NVM DIMM
  interfaces trail the contemporary DRAM PHY rather than match it. Where
  the choice matters is the bandwidth-bound AI regime of Section 3.1.1:
  part of the 4.7x queueing deficit reflects this interface asymmetry
  against dual-channel DDR5-4800, so the reported gap is conservative
  against ReRAM, and pairing the same media with a faster PHY is an
  available mitigation, not a hidden cost.

- The 2D and 3D DRAM Control Configurations: NVMain 2.0 ships with
  native 2d\_dram (legacy planar, DDR3-era, 666 MHz) and 3d\_dram (Wide
  I/O-style Through-Silicon Via, 1333 MHz) example models. These are
  idealized textbook abstractions rather than models of purchasable
  products: unlike the DDR5-4800 model, which faithfully pays JEDEC bus
  serialization, Burst Length 16 transfer, and bank-group switching
  penalties, the example configurations bypass real-world interface
  overheads. They were retained in the simulation matrix as pipeline
  control variables - useful for verifying clock-domain normalization
  and for bounding theoretical throughput - but they are excluded from
  every reported cross-technology comparison, which is restricted to
  technologies with commodity referents: DDR5-4800, PCM, and the four
  ReRAM configurations. The 2D/3D runs are preserved in the released
  dataset (Appendix C) for completeness.

Table 1 collects the NVSim device-level characterization that the system
simulation inherits - the quantitative form of the trade-off profile
stated above: the selector costs 1.6x on reads and 2.3x on writes, and
repays it with a 47x lower leakage floor and an 8.7x smaller die.

#strong[Table 1: NVSim device-level characterization per 1 Gb chip (22nm
FinFET LOP, 1.4 V ReadVoltage nominal).]

#align(center)[#table(
  columns: 8,
  align: (col, row) => (auto,auto,auto,auto,auto,auto,auto,auto,).at(col),
  inset: 6pt,
  table.header(
    [#strong[Configuration]],
    [#strong[Cell size]],
    [#strong[Read lat. (ns)]],
    [#strong[Write lat. (ns)]],
    [#strong[Read energy (nJ)]],
    [#strong[Write energy (nJ)]],
    [#strong[Leakage (mW/chip)]],
    [#strong[Die area (mm²)]],
  ),
  [#strong[1T1R SLC]],
  [20F²],
  [32.13],
  [32.28],
  [1.19],
  [1.74],
  [794.7],
  [19.80],
  [#strong[1T1R MLC\*]],
  [20F²],
  [96.40],
  [129.12],
  [3.57],
  [5.21],
  [794.7],
  [19.80],
  [#strong[1S1R SLC]],
  [4F²],
  [52.13],
  [72.89],
  [6.77],
  [2.47],
  [16.9],
  [2.28],
  [#strong[1S1R MLC\*]],
  [4F²],
  [156.39],
  [291.58],
  [20.32],
  [7.41],
  [16.9],
  [2.28],
)
]

#emph[\*MLC rows apply the Analytical Penalty Method (3x read / 4x write
latency, 3x access energy); leakage and die area are unchanged. Sources:
results/hardware\_metrics.json; Sections 2.1-2.2.]

== 2.4. Workload Traces & Benchmarks
<workload-traces-benchmarks>
To rigorously evaluate the memory architectures across different access
patterns, I selected a diverse suite of workloads spanning traditional
single-threaded execution, pure bandwidth stress tests, and modern
parallel AI:

- #strong[SPEC CPU2017 (602.gcc & 619.lbm):] Generated via gem5 \[26\],
  from the SPEC CPU2017 suite \[28\]. gcc was selected as a
  compute-bound, control-flow heavy workload with irregular memory
  accesses. In contrast, lbm (fluid dynamics) was selected as a
  memory-bound workload to test sustained, sequential memory throughput.

- #strong[STREAM Benchmark:] An industry-standard synthetic diagnostic
  \[27\] used specifically to measure the practical upper bound of
  sustained memory bandwidth and expose baseline latency bottlenecks.

- #strong[SCALE-Sim ML Traces (AlexNet & GPT-2):] Generated via the
  SCALE-Sim systolic array simulator. These workloads were selected to
  represent modern, highly parallel AI operations. AlexNet is split into
  IFMAP (read-dominant) and OFMAP (write-heavy \"Write-Torture\") to
  isolate the ReRAM write-latency penalty, while GPT-2 evaluates massive
  transformer-based memory-level parallelism (MLP).

=== #strong[2.4.1. Diagnostic Trace Dictionary]
<diagnostic-trace-dictionary>
The following specific traces were executed across all simulated
architectures to isolate distinct memory behaviors:

- #strong[gcc\_spec2017 (Compute-Bound):] A standard CPU compilation
  workload whose control-flow-heavy instruction mix generates sparse,
  irregular memory traffic (measured mix: 236,562 reads / 170,800 writes
  per window - 58/42). #strong[Purpose:] It leaves the main memory
  mostly idle, perfectly exposing the pure #emph[Static Leakage Power]
  of the DIMMs. Note that the gem5 traces are uncached raw CPU-to-memory
  streams (Section 3.1.6, item 6), so this idleness stems from the
  workload\'s own compute-bound arithmetic density, not from cache
  filtering - its memory pressure is, if anything, overstated.

- #strong[lbm\_spec2017 (Memory-Streaming):] A fluid dynamics simulation
  that constantly streams large data vectors from memory (measured mix:
  9,481,308 reads / 6,965,793 writes - 58/42, at roughly 40x GCC\'s
  request density). #strong[Purpose:] It highlights the #emph[Dynamic
  Energy] penalty of switching topologies, as memory is constantly
  active.

- #strong[stream] #strong[(Vector-Streaming)]: A standard synthetic
  memory benchmark designed to measure sustainable memory bandwidth and
  simple vector kernel execution, providing a baseline for continuous,
  predictable memory traffic (measured mix: 99,999 reads / 100,000
  writes - an exact 50/50 copy kernel).

- #strong[alexnet\_layer1\_ifmap (CNN Read-Storm):] A neural network
  loading its Input Feature Map. Cycle-accurate traces for this and all
  subsequent neural network workloads were generated using the SCALE-Sim
  systolic array simulator #strong[\[12\]]. #strong[Purpose:] Exposes
  memory controller queueing delays under massive, parallel read
  requests (pure-read: 184,319 reads, zero writes).

- #strong[alexnet\_layer1\_ofmap (CNN Write-Torture):] A neural network
  writing its computed activations back to memory. #strong[Purpose:]
  Explicitly exposes the physical 4× write-latency penalty of Iterative
  Step-and-Verify (ISPV) MLC programming (pure-write: 13,542 writes,
  zero reads).

- #strong[gpt2\_ifmap (Transformer-style Inference):] A General Matrix
  Multiply (GEMM) read trace representing transformer-style weight
  streaming. #strong[Purpose:] The maximum-parallelism read test,
  comparing ReRAM\'s read-bandwidth behavior directly against modern
  dual-channel DDR5 (pure-read: 6,553 reads, zero writes). Provenance
  caveat (Section 3.1.6): unlike the AlexNet traces (confirmed SCALE-Sim
  TPU-v1 configuration), this trace could not be tied to a preserved
  SCALE-Sim run; it is treated as a representative parallel-read stress
  pattern rather than a validated GPT-2 model trace.

Together, the six traces span the three canonical intensity classes:
compute-bound with memory mostly idle (GCC), mixed sustained streaming
(LBM and STREAM, 58/42 and 50/50 read/write), and pure single-operation
stress at both extremes - read-intensive (GPT-2, AlexNet IFMAP) and
write-intensive (AlexNet OFMAP). Under the matched-host replay of
Section 3.1.6, item 11, every technology admits the identical request
mix for every trace, so these classifications hold uniformly across the
comparison.

#pagebreak()
<section>
= 3. Results: Multi-Rank Architecture & Scaling
<results-multi-rank-architecture-scaling>
== 3.1. #strong[Granular Workload Diagnostics] (Latency & Power Bar Charts)
<granular-workload-diagnostics-latency-power-bar-charts>
To fully understand the system-level tradeoffs of memristor-based main
memory, I isolated the physical variables of latency and power across
distinct workload profiles. The evaluation is organized around the
canonical ReRAM trade-off profile - slower access than DRAM, zero
refresh, higher density, and individually expensive write operations -
and quantifies each axis in turn: latency in Section 3.1.1, the
refresh-free but leakage-bound power identity (including where the
write-energy cost actually surfaces) in Section 3.1.2, their balance in
Section 3.1.3, write endurance in Section 3.1.4, and density in Section
3.3.

=== 3.1.1 Latency Analysis: The MLC Write Penalty
<latency-analysis-the-mlc-write-penalty>
The most critical operational constraint of ReRAM is its write latency,
which is exacerbated when utilizing Multi-Level Cells (MLC) due to the
required Iterative Step-and-Verify (ISPV) programming. To quantify this
impact at the architectural level, I evaluated the memory configurations
across compute-bound, streaming, and neural network traces. A
methodological note governs how performance is read throughout this
section: in fixed-window trace replay the trace dictates the offered
load, and after the matched-host correction of Section 3.1.6, item 11,
every configuration admits the identical request population per workload
(a uniform 250M-trace-cycle cutoff at a 3 GHz host; 83.33 ms wall-clock
for every technology). Five of the six workloads - GCC, STREAM, GPT-2,
and both AlexNet phases - are completed in full by every technology, so
there the cost of a slower memory appears purely as latency and queueing
over identical populations. LBM\'s sustained streaming is the one
service-limited case, and it is a clean, like-for-like throughput
result: of an identical 16,447,102-request admission, DDR5 completes
100%, 1T1R SLC 40.0%, 1S1R SLC 28.0%, 1T1R MLC 16.3%, 1S1R MLC 9.3%, and
PCM 3.9% - a delivered-throughput ordering, graded exactly by device
write speed, that hardens this section\'s MLC verdict and quantifies the
sustained-streaming cost of every resistive technology at once; its
single accounting consequence is that LBM latency averages cover each
configuration\'s completed prefix.

#block(breakable: false)[
#image("media/media/image1.png", width: 6.5in, height: 3.7983464566929133in)

#strong[Figure 1: Average Total Latency under the compute-bound GCC
(SPEC2017) workload.]
]

Under standard compute-bound workloads with small, infrequent memory
bursts like gcc (Figure 1), the 22nm 1T1R SLC ReRAM configuration
demonstrates exceptional responsiveness. Averaging 104.73 cycles at 800
MHz (130.91 ns), 1T1R SLC is slower than DDR5-4800 in absolute
wall-clock time (81.16 ns, or 194.78 cycles at 2400 MHz - an average
that now includes DDR5\'s faithfully modeled refresh blocking; Section
3.1.6, item 7) - a 61% latency overhead that is the smallest
cross-technology gap in the suite. The selector-gated 1S1R SLC follows
at 190.35 ns, a 1.5x cost over 1T1R for the selector\'s slower access
path: NVSim\'s device characterization prices a 1S1R read at 52.1 ns
versus 32.1 ns for 1T1R (1.6x) and a write at 72.9 versus 32.3 ns
(2.3x), because the crossbar must sense through the non-linear selector
at the deliberately high 10⁵ Ω resistance calibration and bias writes
past the selector threshold, whereas the access transistor - the very
thing that costs 1T1R its 20F² cell - provides isolated, full-drive
access. This gap is not a modeling artifact but the latency half of the
selector trade-off, and Section 3.1.3 shows it is decisively repaid in
the power term. Whether this latency proximity translates into system
efficiency is a power question, and it is answered in Sections 3.1.2 and
3.1.3 under the repaired power model of Section 3.1.6.

#block(breakable: false)[
#image("media/media/image2.png", width: 6.5in, height: 3.7983464566929133in)

#strong[Figure 2: Average Total Latency under the continuous
memory-streaming LBM (SPEC2017) workload.]
]

To contrast the compute-bound nature of GCC, I evaluated the memory
subsystem under the lbm trace (Figure 2), a fluid dynamics workload
characterized by heavy, continuous memory streaming. Here, the
architectural dynamics change significantly. The 1T1R SLC configuration
averages 374.50 cycles at 800 MHz (468.12 ns), compared to DDR5-4800 at
600.31 cycles at 2400 MHz (250.13 ns) - a 1.9x wall-clock edge to DDR5
from its higher operating frequency. The efficiency implications under
streaming are governed by each technology\'s leakage tier and are
quantified in Section 3.1.3. This workload also exposes the limits of
Multi-Level Cells: the 1S1R MLC latency spikes to 1549.42 cycles
(1936.78 ns), as continuous write-pressure backs up the FRFCFS
controller queue with ISPV programming operations, increasing average
total latency by 4.1x relative to 1T1R SLC (2.9x relative to its own
1S1R SLC sibling).

#block(breakable: false)[
#image("media/media/image3.png", width: 6.5in, height: 3.7983464566929133in)

#strong[Figure 3: Average Total Latency under the parallel read-storm of
GPT-2 Inference (IFMAP).]
]

However, when the system is subjected to the massive parallel
read-storms typical of Large Language Model (LLM) inference, the
dynamics shift. In the GPT-2 trace (Figure 3), the 1T1R SLC
configuration averages 366.73 cycles at 800 MHz (458.41 ns), trailing
the DDR5-4800 baseline (234.01 cycles at 2400 MHz, 97.51 ns) by
approximately 4.7x in wall-clock terms. Despite ReRAM\'s fast raw read
speed, this data exposes the queueing delays within the memory
controller. Under extreme read pressure, the ReRAM DIMM cannot clear its
request buffers as efficiently as the highly-pipelined, dual-channel
DDR5 interface. Under AI inference, DDR5 wins decisively on latency -
with the caveat that 4.7x is a memory-latency ratio, not a projected
end-to-end application slowdown (Section 3.1.6) - and the PDP analysis
of Section 3.1.3 shows that the efficiency verdict compounds rather than
offsets this deficit. Any ReRAM role in AI inference deployment is
therefore confined to duty-cycled or standby-dominated serving
scenarios, where zero-refresh retention between bursts - not sustained
throughput - carries the value; under sustained inference load, DDR5
wins on latency, efficiency, and absolute power (Section 3.1.2).

#image("media/media/image4.png", width: 6.5in, height: 3.7983464566929133in)

#block(breakable: false)[
#image("media/media/image5.png", width: 6.5in, height: 3.7983464566929133in)

#strong[Figure 4 & 5: Average Total Latency under AlexNet Layer 1 IFMAP
(pure-read) and OFMAP (pure-write) workloads, highlighting the MLC
write-latency penalty.]
]

To explicitly isolate and prove the MLC write penalty, I engineered a
\"Write-Torture\" test by comparing the Input Feature Map (IFMAP) and
Output Feature Map (OFMAP) traces of AlexNet Layer 1 #strong[(Figures 4
and 5)]. The data reveals a severe architectural bottleneck. Under the
read-heavy IFMAP workload, 1S1R MLC averages 948.74 cycles. However,
under the write-heavy OFMAP workload, the 1S1R MLC latency spikes to
3335.20 cycles - just over 3× degradation compared to its SLC
counterpart (1081.98 cycles). This empirical gap confirms the analytical
penalty method implemented in my simulation stack: MLC ReRAM incurs a
severe latency tax during write operations, dictating that MLC
topologies must be strictly relegated to read-only or read-mostly
applications, such as housing frozen LLM weights.

The IFMAP/OFMAP pair also yields the suite\'s cleanest read-versus-write
comparison at the system level, because the two traces isolate pure
operation streams - IFMAP issues only reads (184,319 requests), OFMAP
only writes (13,542) - and every technology replays the identical pair.
The write-side degradation factor (OFMAP over IFMAP average latency)
therefore ranks write tolerance directly: DDR5 is nearly
read/write-symmetric at 1.08x, 1T1R SLC degrades 2.1x, 1S1R SLC 2.6x,
1T1R MLC 2.8x, 1S1R MLC 3.5x, and PCM 3.6x. Two device-level facts from
Table 1 sit beneath that ranking. The selector prices writes
intrinsically: a 1S1R write costs 1.4x its read at the device (72.9 vs
52.1 ns) before ISPV programming multiplies it toward 1.9x for MLC
(291.6 vs 156.4 ns). The access transistor, by contrast, makes the 1T1R
device almost perfectly symmetric (32.3 vs 32.1 ns) - so 1T1R\'s 2.1x
system-level degradation measures burst structure and bank pressure
under the write stream, not cell physics, and marks the asymmetry floor
that controller-level write buffering (Section 4.1) could attack.
DRAM\'s near-symmetry is the benchmark every resistive contender chases;
this ordering quantifies the fourth axis of the trade-off profile stated
at the top of Section 3.1 - individually expensive write operations - as
measured system latency.

The STREAM benchmark (Figure 6) applies pure vector-kernel bandwidth
pressure, isolating sustained memory bandwidth from compute
dependencies. The 1T1R SLC configuration averages 473.17 cycles (591.46
ns), trailing the DDR5-4800 baseline (276.04 ns) by 2.1x in wall-clock
latency, with 1S1R SLC at 890.29 ns; together with the LBM result, this
brackets sustained streaming as a 1.9-3.2x latency-deficit regime across
the SLC ReRAM family. The efficiency consequences are quantified in
Section 3.1.3.

#block(breakable: false)[
#image("media/media/image25.png", width: 6.5in, height: 3.7983464566929133in)

#strong[Figure 6: Average Total Latency under the STREAM memory
bandwidth benchmark.]
]

Table 2 collects the average total latencies across the full workload
suite, complementing the per-workload bar charts.

#strong[Table 2: Average total latency (ns), full-DIMM configurations,
83.33 ms matched-host window (Section 3.1.6, item 11).]

#align(center)[#table(
  columns: 7,
  align: (col, row) => (auto,auto,auto,auto,auto,auto,auto,).at(col),
  inset: 6pt,
  table.header(
    [#strong[Workload]],
    [#strong[DDR5-4800]],
    [#strong[PCM]],
    [#strong[1T1R SLC]],
    [#strong[1S1R SLC]],
    [#strong[1T1R MLC]],
    [#strong[1S1R MLC]],
  ),
  [#strong[GCC]],
  [81.2],
  [6,399.2],
  [130.9],
  [190.3],
  [330.2],
  [544.4],
  [#strong[LBM]],
  [250.1],
  [7,363.4],
  [468.1],
  [662.1],
  [1,127.9],
  [1,936.8],
  [#strong[STREAM]],
  [276.0],
  [7,666.5],
  [591.5],
  [890.3],
  [1,433.0],
  [2,466.8],
  [#strong[GPT-2]],
  [97.5],
  [1,816.1],
  [458.4],
  [618.4],
  [978.4],
  [1,458.4],
  [#strong[AlexNet IFMAP]],
  [115.9],
  [1,438.0],
  [397.4],
  [523.9],
  [806.6],
  [1,185.9],
  [#strong[AlexNet OFMAP]],
  [125.2],
  [5,209.3],
  [819.7],
  [1,352.5],
  [2,233.6],
  [4,169.0],
)
]

#emph[Wall-clock nanoseconds (clock domains: ReRAM 800 MHz, PCM 400 MHz,
DDR5 2400 MHz). Source:
results/system\_v4/processed\_bar\_chart\_metrics.csv.]

=== 3.1.2 Power Analysis: Static Leakage Dominance
<power-analysis-static-leakage-dominance>
While ReRAM exhibits latency penalties under write-heavy and massive
parallel read workloads, its candidate advantage has always been the
energy profile: traditional DRAM requires continuous, power-intensive
capacitive refresh cycles to maintain data integrity - a permanent power
tax paid regardless of workload activity - whereas non-volatile
retention is free. Whether ReRAM actually realizes that advantage,
however, is decided by peripheral leakage, and quantifying leakage
correctly required repairing the simulation toolchain first. All power
figures in this section therefore come from the repaired model
documented in Section 3.1.6: NVSim\'s per-technology leakage is wired
into the standby-energy parameters NVMain actually reads (validated
against device-level anchors to 0.0% error), power is accounted as the
whole-module sum for every technology, and no idle-gating is applied,
because NVMain\'s power-down machinery is disabled in source. The ReRAM
figures are consequently worst-case ungated, while the DRAM and PCM
baselines model their standard idle behavior - an asymmetry restated
wherever cross-technology totals are compared.

#block(breakable: false)[
#image("media/media/image6.png", width: 6.5in, height: 2.494313210848644in)

#strong[Figure 7: System Power Breakdown (Static / Dynamic / Refresh)
under the compute-bound GCC (SPEC2017) workload.]
]

In instruction-heavy, compute-bound workloads like gcc (Figure 7), the
main memory subsystem remains idle for the vast majority of the
execution time, making GCC the cleanest probe of each technology\'s
standing power floor. The non-volatile opportunity shows immediately:
ReRAM\'s refresh component is identically zero, because retention is
free, while the decomposition in Figure 7 exposes DDR5\'s structural
burden - 44.7% of its 0.651 W module-sum draw under GCC is refresh
power, energy spent merely retaining data, on top of a 55% standby
floor, with actual access activity accounting for about 0.1%. The
selector-gated 1S1R module converts that opportunity into a
commodity-envelope number: 1.12 W (97% static), refresh-free, with
essentially every milliwatt of its draw exposed to future idle-gating.
The repaired leakage wiring prices the alternative just as clearly: the
transistor-gated 1T1R module leaks 50.9 W (99.99% static), roughly two
orders of magnitude above DDR5, and PCM sits at 0.040 W (91% static).
Real dynamic power is small for every ReRAM configuration (12-98 mW
module-wide under GCC, now technology-differentiated through the
repaired access energies of Section 3.1.6, item 10): ungated ReRAM power
is leakage, full stop.

#block(breakable: false)[
#image("media/media/image7.png", width: 6.5in, height: 2.494313210848644in)

#strong[Figure 8: System Power Breakdown (Static / Dynamic / Refresh)
under the highly active GPT-2 Inference (IFMAP) workload.]
]

The repaired model also retires an artifact of this project\'s earlier
analysis. Under the simulator\'s generic standby defaults, total power
appeared to cluster at nearly the same level for every ReRAM
configuration under any given workload - a convergence previously read
as a named “Power Flatline.” With real per-technology leakage wired in,
that flatline stands revealed as a modeling artifact; the true signature
is leakage-class separation. The four ReRAM full-DIMM configurations
fall into two power tiers set entirely by their standby physics - 50.9 W
for the transistor-gated 1T1R family and 1.12-1.30 W for the
selector-gated 1S1R family, against DDR5\'s 0.651 W and PCM\'s 0.040 W -
and within each ReRAM tier, SLC and MLC variants are nearly
indistinguishable (50.870 vs. 50.886 W under GCC), because dynamic
energy contributes only milliwatts. What survives from the earlier
observation is the intra-family invariance: write intensity never spikes
power, and MLC imposes no power penalty relative to SLC under active
workloads. The 47x leakage gap that NVSim characterizes at the device
level (794.7 vs. 16.9 mW per chip) now propagates faithfully to the
system level, where it becomes the single most consequential number in
this evaluation.

This confirms Static Leakage Dominance end-to-end: peripheral and
access-device leakage governs ReRAM\'s power identity at the device
level (NVSim: 794.7 vs. 16.9 mW per chip) and - now measured with real
leakage physics - at the system level as well. Under AI inference
(GPT-2, Figure 8), the most parallel workload in the suite, accumulated
dynamic read energy raises the 1S1R SLC module only from 1.12 W to 1.23
W - roughly a 10% excursion - while DDR5 spans 0.65-0.78 W across the
entire suite, so the standby floor decides the cross-technology ranking
under every workload. The architectural consequence is decisive: 1S1R
lands within 1.7x of DDR5 at the conservative calibration floor (within
11% of parity at the ceiling) with zero refresh cost and its gating
headroom unexercised - a credible successor profile - while an always-on
1T1R DIMM, at 50-78x DDR5\'s power, is infeasible without gating. The
selector\'s leakage discipline is thereby elevated from a device
curiosity to the deciding architectural requirement.

#block(breakable: false)[
#image("media/media/image8.png", width: 6.5in, height: 2.494313210848644in)

#strong[Figure 9: System Power Breakdown (Static / Dynamic / Refresh)
under the continuous memory-streaming LBM (SPEC2017) workload.]
]

This leakage dominance also exposes a genuine tug-of-war in the dynamic
term under streaming write-heavy workloads like lbm (Figure 9;
components this small cannot be resolved visually against the 50.9 W
static tier - the values come directly from the NVMain energy counters).
The MLC configuration\'s extended Iterative Step-and-Verify (ISPV)
writes bottleneck the memory controller, so it processes fewer requests
per second - but with the repaired per-technology access energies
(Section 3.1.6, item 10), each MLC access also costs 3x its SLC
counterpart, and under lbm the energy penalty outweighs the throughput
throttling: 1T1R MLC dynamic power reaches 140.6 mW against SLC\'s 111.1
mW. At module scale, both variants remain pinned to the same 50.9 W
static tier, reconfirming that ReRAM DIMMs are fundamentally bounded by
their static peripheral leakage rather than dynamic cell activity.

#block(breakable: false)[
#image("media/media/image9.png", width: 6.5in, height: 2.494313210848644in)

#strong[Figure 10: System Power Breakdown (Static / Dynamic / Refresh)
under the STREAM benchmark.]
]

The standard stream benchmark (Figure 10) shows where the balance tips
the other way: 1T1R SLC dynamic power reaches 99.5 mW while the slower
MLC configuration lands marginally below it at 95.2 mW - here the
throughput throttling just outweighs the 3x access-energy penalty. The
two effects - fewer operations per second versus more energy per
operation - trade the lead workload by workload, and in every case the
module total remains anchored to its technology\'s leakage tier.

#image("media/media/image10.png", width: 6.5in, height: 2.494313210848644in)

#block(breakable: false)[
#image("media/media/image11.png", width: 6.5in, height: 2.494313210848644in)

#strong[Figure 11 & 12: System Power Breakdown (Static / Dynamic /
Refresh) under AlexNet Layer 1 IFMAP (Read-Heavy) and OFMAP
(Write-Heavy) workloads.]
]

Finally, to ensure the Static Leakage Dominance principle holds across
diverse neural network operations, I evaluated both the read-intensive
AlexNet IFMAP and the write-intensive AlexNet OFMAP workloads (Figures
11 and 12). A ReRAM write is individually an expensive operation: NVSim
prices a 1T1R write at 1.74 nJ against 1.19 nJ for a read, delivered as
\~100 uA-class programming currents, and MLC writes stretch into 4x-long
ISPV sequences - so write-heavy traffic is precisely where one would
expect ReRAM power to spike. It does not. Despite the severe latency
penalty incurred during OFMAP writes (as established in Section 3.1.1),
no configuration exhibits a power spike - in fact, OFMAP dynamic power
is consistently lower than IFMAP dynamic power (87.7 vs. 122.2 mW for
1T1R SLC and 120.6 vs. 163.3 mW for 1S1R SLC, with the same ordering
across all four ReRAM configurations), because slow ISPV write
operations throttle request throughput: the higher energy per write is
more than offset by fewer operations per second. Extended write
durations therefore never translate into elevated average power; total
power tracks the technology\'s leakage tier, perturbed only marginally
by request throughput.

Table 3 collects the whole-module power totals, making the leakage-class
tiers directly comparable across every workload.

#strong[Table 3: Total module power (W), full-DIMM, repaired model,
module-sum semantics.]

#align(center)[#table(
  columns: 7,
  align: (col, row) => (auto,auto,auto,auto,auto,auto,auto,).at(col),
  inset: 6pt,
  table.header(
    [#strong[Workload]],
    [#strong[DDR5-4800]],
    [#strong[PCM]],
    [#strong[1T1R SLC]],
    [#strong[1S1R SLC]],
    [#strong[1T1R MLC]],
    [#strong[1S1R MLC]],
  ),
  [#strong[GCC]],
  [0.651],
  [0.040],
  [50.870],
  [1.118],
  [50.886],
  [1.180],
  [#strong[LBM]],
  [0.712],
  [0.042],
  [50.999],
  [1.304],
  [50.998],
  [1.299],
  [#strong[STREAM]],
  [0.704],
  [0.042],
  [50.957],
  [1.210],
  [50.953],
  [1.203],
  [#strong[GPT-2]],
  [0.648],
  [0.036],
  [50.965],
  [1.233],
  [50.928],
  [1.220],
  [#strong[AlexNet IFMAP]],
  [0.745],
  [0.036],
  [50.980],
  [1.246],
  [50.939],
  [1.231],
  [#strong[AlexNet OFMAP]],
  [0.776],
  [0.044],
  [50.948],
  [1.205],
  [50.956],
  [1.200],
)
]

#emph[ReRAM figures are worst-case ungated (NVMain power-down disabled
in source); DRAM/PCM baselines model standard idle behavior. Source:
results/system\_v4/processed\_bar\_chart\_metrics.csv.]

=== 3.1.3 Power-Delay Product (PDP): The Architectural Sweet Spot
<power-delay-product-pdp-the-architectural-sweet-spot>
While isolated latency and power metrics define physical boundaries,
true architectural viability is measured by the balance between them. I
utilized the Power-Delay Product (PDP \= Total System Power \[W\] ×
Average Request Latency \[ns\]; units W·ns \= nJ) to rank
configurations. All PDP values in this section are computed from the
repaired, module-sum power model of Section 3.1.6 with no idle gating
applied: the ReRAM values are therefore worst-case ungated, while the
DRAM and PCM baselines model standard idle behavior. This asymmetry must
accompany any reading of the cross-technology ranking.

#image("media/media/image12.png", width: 6.5in, height: 3.816531058617673in)

#block(breakable: false)[
#image("media/media/image13.png", width: 6.5in, height: 3.816531058617673in)

#strong[Figure 13 & 14: Power-Delay Product under single-threaded
compute (GCC SPEC2017) and massively parallel AI inference (GPT-2 IFMAP)
workloads.]
]

The repaired power model inverts the intra-ReRAM hierarchy that the
earlier technology-blind analysis suggested. Once each family carries
its real leakage, the selector-gated configurations dominate: under GCC
(Figure 13), 1S1R SLC posts 212.8 W·ns against 1T1R SLC\'s 6,659.3 - a
31x advantage - because the 47x leakage gap in the power term dwarfs the
1.6x latency cost of the selector\'s slower access path. The same
inversion holds under every workload in the suite. Against the
baselines, DDR5 posts 52.8 W·ns under GCC and 63.2 under GPT-2 (Figure
14); ungated 1S1R SLC trails DDR5 by roughly 3.2x under GCC, and the
ungated 1T1R family is uncompetitive at any operating point. Cell-level
density still costs efficiency within each family - MLC multiplies the
delay term (642.2 vs. 212.8 W·ns for 1S1R under GCC) - but the deciding
term is now leakage class, not cell type.

#image("media/media/image14.png", width: 6.5in, height: 3.816531058617673in)

#block(breakable: false)[
#image("media/media/image15.png", width: 6.5in, height: 3.816531058617673in)

#strong[Figure 15 & 16: Power-Delay Product under heavy continuous
memory-streaming workloads (LBM SPEC2017 and STREAM).]
]

Under maximum bandwidth pressure (Figures 15 and 16), the repaired
ordering persists: 1S1R SLC posts 863.4 W·ns under lbm and 1,077.0 under
stream, with its MLC sibling at roughly 2.8x those values (2,515.3 and
2,968.5 W·ns) as streaming amplifies every write-side penalty, and the
1T1R family remains more than an order of magnitude further adrift
(23,874 W·ns for 1T1R SLC under lbm). DDR5 holds a \~5x edge over ungated
1S1R SLC in the streaming regime (178.2 and 194.3 W·ns).

#image("media/media/image16.png", width: 6.5in, height: 3.816531058617673in)

#block(breakable: false)[
#image("media/media/image17.png", width: 6.5in, height: 3.816531058617673in)

#strong[Figure 17 & 18: Power-Delay Product under AlexNet Layer 1 IFMAP
(Read-Heavy) and OFMAP (Write-Heavy) workloads, highlighting the MLC
write-latency penalty on system efficiency.]
]

Finally, the PDP diagnostics explicitly map the efficiency limits of
density scaling within the viable selector family. Under the read-heavy
AlexNet IFMAP (Figure 17), moving from 1S1R SLC to the ultra-dense 1S1R
MLC topology incurs a 2.2x PDP increase (652.5 to 1,460.2 W·ns). Under
the write-heavy AlexNet OFMAP trace (Figure 18), the 1S1R MLC PDP spikes
to 5,003.8 W·ns - 3.1x its SLC sibling\'s 1,629.2. This confirms a
strict efficiency tax for density: MLC solves the physical capacity
problem, but its iterative write penalties severely degrade overall
system efficiency under active write stress.

Table 4 collects the Power-Delay Products with the suite geometric
means, the tabular form of Figures 13-18 and 27.

#strong[Table 4: Power-Delay Product (W·ns \= nJ), full-DIMM, and
six-workload geometric means.]

#align(center)[#table(
  columns: 7,
  align: (col, row) => (auto,auto,auto,auto,auto,auto,auto,).at(col),
  inset: 6pt,
  table.header(
    [#strong[Workload]],
    [#strong[DDR5-4800]],
    [#strong[PCM]],
    [#strong[1T1R SLC]],
    [#strong[1S1R SLC]],
    [#strong[1T1R MLC]],
    [#strong[1S1R MLC]],
  ),
  [#strong[GCC]],
  [52.8],
  [254.0],
  [6,659.3],
  [212.8],
  [16,802.3],
  [642.2],
  [#strong[LBM]],
  [178.2],
  [311.7],
  [23,873.5],
  [863.4],
  [57,518.3],
  [2,515.3],
  [#strong[STREAM]],
  [194.3],
  [325.5],
  [30,139.9],
  [1,077.0],
  [73,013.9],
  [2,968.5],
  [#strong[GPT-2]],
  [63.2],
  [65.8],
  [23,363.0],
  [762.5],
  [49,828.1],
  [1,779.8],
  [#strong[AlexNet IFMAP]],
  [86.3],
  [52.2],
  [20,260.2],
  [652.5],
  [41,087.4],
  [1,460.2],
  [#strong[AlexNet OFMAP]],
  [97.2],
  [230.4],
  [41,763.3],
  [1,629.2],
  [113,813.4],
  [5,003.8],
  [#strong[Geometric mean]],
  [99.5],
  [165.3],
  [21,350.6],
  [737.1],
  [50,426.6],
  [1,991.4],
)
]

#emph[PDP \= total module power x average request latency. ReRAM
worst-case ungated; DRAM/PCM standard idle (Section 3.1.6, item 5).
Source: results/system\_v4 processed CSVs.]

=== #strong[3.1.4 Endurance Viability Analysis]
<endurance-viability-analysis>
A key viability question for ReRAM as a main memory replacement is write
endurance: how many write cycles before cell degradation? While SLC
ReRAM cells are typically rated at 10#super[7] cycles and MLC at
10#super[6] write cycles - conservative engineering targets within the
wide range of endurance values reported across published metal-oxide
RRAM demonstrations \[14\], with conservatism warranted by documented
methodological inconsistencies in reported endurance data \[15\] - the
practical lifetime under real workloads depends on the actual write
frequency, not the worst-case specification. In NVMain, each recorded
write event programs one 64-byte cache line, so wear is accounted per
line location: the physical 8 GB SLC full-DIMM module (64 chips of 1 Gb)
comprises 134.2 million cache-line locations, and lifetime is the time
for any location to accumulate the rated endurance under uniform wear
leveling. (NVMain\'s decoded address space is 64x larger than the
physical module - a configuration-generator artifact that affects
neither per-request timing nor energy; endurance is computed over the
physical cell population, and lifetime scales linearly with module
capacity.) Using the per-subarray write counts extracted from the NVMain
simulation statistics, the projected lifetimes are summarized below.

Table 5: Projected DIMM Write Endurance Lifetime (1T1R SLC Full DIMM,
physical capacity 8 GB, 66.7M cycles at 800 MHz \= 83.33 ms matched-host
window (Section 3.1.6, item 11), uniform wear leveling over 134.2
million 64-byte line locations; lifetime scales linearly with module
capacity).

#align(center)[#table(
  columns: 5,
  align: (col, row) => (auto,auto,auto,auto,auto,).at(col),
  inset: 6pt,
  table.header(
    [#strong[Workload]],
    [#strong[Total Writes (83.33 ms)]],
    [#strong[Write Rate]],
    [#strong[Lifetime (SLC 10⁷, 8 GB)]],
    [#strong[Lifetime (SLC 10⁷, 64 GB)]],
  ),
  [LBM (worst case)],
  [3,269,479],
  [39.2 M/s],
  [1.08 years],
  [8.7 years†],
  [GCC],
  [170,800],
  [2.05 M/s],
  [20.8 years],
  [166 years],
  [STREAM],
  [100,000],
  [1.20 M/s],
  [35.4 years],
  [283 years],
  [AlexNet OFMAP],
  [13,542],
  [0.16 M/s],
  [262 years],
  [2,094 years],
)
]

†Lifetimes scale linearly with module capacity; the 64 GB column
reflects a commodity server-class module, where ReRAM\'s density
advantage is realized. Directly measured MLC lifetimes at the physical
16 GB module under LBM: 0.54 years for 1T1R MLC (1,320,096 writes in
83.33 ms at 15.8 M/s) and 0.94 years for 1S1R selector MLC (751,405
writes at 9.0 M/s); even at 128 GB these reach only 4.3 and 7.5 years
respectively. All lifetimes assume uniform wear leveling.

The results reframe endurance as a capacity- and workload-dependent
constraint. At the modeled 8 GB module, the worst-case sustained
streaming workload (LBM) yields a projected lifetime of only 1.1 years
for SLC - below the 5-10 year server replacement target (enterprise
server useful life currently averages 5.4 years and is trending toward
six to seven years \[16\]) - while every other workload clears the
target - by 2-4x for compute-bound GCC (20.8 years) and by an order of
magnitude or more beyond it (35.4 years for STREAM, 262 years for
AlexNet OFMAP). Because uniform wear leveling spreads a fixed workload
write rate over the module\'s entire cell population, lifetime scales
linearly with capacity: at the 64-128 GB module sizes where ReRAM\'s
density advantage is actually realized, worst-case SLC lifetime reaches
9-17 years (the slower-writing selector variant, 12-25), meeting the
target at 64 GB and exceeding it at 128 GB. MLC is harsher: at its
physical 16 GB module the measured LBM lifetimes are 0.54 years (1T1R)
and 0.94 years (1S1R), and even at 128 GB they remain below or marginal
to the target - an independent endurance argument for restricting MLC to
read-dominant deployments that converges with the write-latency argument
of Section 3.1.1. Endurance is therefore not a categorical barrier but a
design constraint that binds only for small modules under sustained
write streaming, directly motivating the wear-leveling controller and
write-coalescing cache proposed in Section 4.2. Note additionally that
these lifetimes assume ideal uniform wear leveling; hot-spot write
patterns without such a controller would reduce projected lifetime
proportionally.

=== #strong[3.1.5 Design Robustness: ReadVoltage Sensitivity]
<design-robustness-readvoltage-sensitivity>
A persistent concern with resistive memories is parameter sensitivity:
do the efficiency conclusions hold if the actual fabricated device
deviates from the target resistance? To quantify this, I ran a
three-point sweep of the NVSim ReadVoltage parameter at -20%, nominal,
and +20% of the 1.4V design point ({1.12V, 1.40V, 1.68V}) for the 1T1R
SLC Full DIMM configuration under LBM and GCC, the two workloads that
bracket the bandwidth-bound and compute-bound extremes.

The results, shown in Figure 19, reveal a key robustness property: read
latency is completely invariant to a +/-20% ReadVoltage perturbation.
The current-sensing amplifier operates within its saturation margin at
all three voltages, producing identical read latency (32.13 ns)
regardless of supply. Only read energy scales with applied voltage: read
energy is 22.4% lower at 1.12V and 27.5% higher at 1.68V relative to the
1.4V baseline. At the full-DIMM system level, where static peripheral
leakage dominates over per-operation read energy, the per-read energy
variation is negligible: total PDP changed by less than 4% across the
full +/-20% sweep. One limitation applies: this sweep was executed
before the power-model repair of Section 3.1.6 and has not been re-run
under the repaired dataset. Because the repair raises the static share
of ReRAM system power to 99.5% or more (Section 3.1.2), per-operation
read energy becomes an even smaller fraction of the total, so the
insensitivity conclusion holds a fortiori; read-latency invariance is
unaffected by the repair, which changes power accounting only.

#block(breakable: false)[
#image("media/media/image27.png", width: 6.5in, height: 3.7916666666666665in)

#strong[Figure 19: ReadVoltage Sensitivity Analysis - 1T1R SLC Full DIMM
(LBM and GCC, +/-20% sweep). Left: NVSim read latency is invariant
across all three voltages. Right: System-level PDP changes by less than
4% across the full sweep, confirming that efficiency conclusions are
robust to process variation in the ReadVoltage operating point.]
]

=== #strong[3.1.6 Simulation-Fidelity Audit: Where the Toolchain Could Not Be Trusted - and How It Was Repaired]
<simulation-fidelity-audit-where-the-toolchain-could-not-be-trusted---and-how-it-was-repaired>
A systematic audit of the NVSim-to-NVMain flow, conducted against the
raw simulator sources and statistics files, found eleven silent failure
modes that bounded which conclusions this evaluation could honestly draw
\- across the ReRAM configurations, the metrics pipeline, and both
non-ReRAM baselines. Nine of the eleven have since been repaired in this
project\'s toolchain, with the affected simulations re-run; every power
and PDP figure in this book derives from the resulting repaired dataset.
(1) Found and fixed: the pipeline\'s original efficiency metric
multiplied Watts by cycle counts taken from different clock domains (800
MHz ReRAM vs. 2400 MHz DDR5), biasing the comparison 3x against DDR5;
all PDP values are computed in physical W·ns. (2) Found and fixed: the
StandbyPower parameter written by the configuration generator was dead
configuration - NVMain\'s source contains no reference to it, so the
device-characterized leakage never reached the simulation. The repair
maps NVSim\'s per-technology leakage onto the standby-energy parameters
NVMain actually reads. (3) Found and fixed: in place of real leakage,
NVMain applied generic standby-energy defaults (Eactstdby/Eprestdby),
giving every non-volatile configuration the same \~68 mW-per-rank static
floor - the original power results were technology-blind in their static
component, even though NVSim characterizes a 47x leakage difference
between 1T1R (794.7 mW/chip) and 1S1R (16.9 mW/chip). Under the repaired
wiring, the simulated full-DIMM static floors (50.858 W for 1T1R, 1.082
W for 1S1R) reproduce the NVSim characterization exactly (0.0% anchor
error). (4) Found and fixed: the reported “Total System Power” was the
single most-loaded rank, not the module sum; because the ReRAM
configurations span 8 ranks while DDR5 spans 2 ranks across 2
sub-channels, per-rank accounting distorted every cross-technology
comparison. All power figures in this book are whole-module sums for
every technology. (5) Found and documented - still open: NVMain\'s
power-down state machine is disabled in source, so no idle-gating policy
\- the mechanism a real ReRAM DIMM would rely on to tame its leakage -
can currently be simulated. Every ReRAM power figure in this book is
therefore worst-case ungated, while the DRAM and PCM baselines model
their standard idle behavior; restoring this subsystem is the
top-priority future work (Section 4.1). (6) Found and documented: trace
provenance is weaker than the methodology narrative implied - the gem5
traces were generated without L1/L2 caches, warmup, or region selection
(raw CPU-to-memory stream, first 10M instructions), which overstates
memory pressure (conservatively for the endurance bounds, but distorting
for absolute queueing behavior), and the GPT-2 trace could not be tied
to any preserved SCALE-Sim configuration (AlexNet\'s TPU-v1 256x256
output-stationary provenance is confirmed). (7) Found and fixed: the
DDR5 configuration\'s refresh machinery was inherited from a DDR3-1333
template and never rescaled when the clock was raised to 2400 MHz -
refresh operations fired 3.6x too often (derived tREFI 1.085 µs vs.
JEDEC 3.906 µs) at 6.6x too little cost each (tRFC 44.6 vs. 295 ns).
Recalibrating to JEDEC JESD79-5 raised DDR5\'s refresh share from 57.9%
to 71.3% of module power under GCC (a share subsequently reduced to the
final 33-45% band once item 8\'s vendor-current calibration repriced the
non-refresh components) and its average GCC latency from 69.9 to 81.2
ns, because refresh blocking is now faithfully priced. (8) Found and
partially fixed: every supply parameter in the DDR5 configuration proved
to be NVMain\'s stock built-in default rather than a datasheet value.
The supply voltage - 1.5 V against DDR5\'s JEDEC-specified 1.1 V - was
corrected, scaling all DDR5 power linearly by 0.733 (verified exact);
the IDD current magnitudes were subsequently calibrated to published
vendor datasheets (Micron and SK hynix 16 Gb DDR5-4800 tables) \[29\],
\[30\], run as a two-vendor band - the conservative SK hynix floor is
this book\'s headline, the Micron ceiling is reported alongside - with a
documented caveat that datasheet IDD values are specification limits
rather than typicals; calibrating with real currents also exposed and
forced the repair of a sign artifact in NVMain\'s activate-energy
formula (clamped at zero, worst case 2.8% of module power before the
fix). (9) Found and fixed: the PCM baseline\'s cycle timings were
derived for its cited 400 MHz basis, but a stray trailing clock override
ran it at 800 MHz - twice as fast as Lee et al.\'s parameters intend -
and a second instance of the same bug sat in the reporting layer\'s
hardcoded clock table; a syntax typo additionally zeroed its per-bit
write energy. Restoring the 400 MHz basis roughly doubled PCM\'s
latencies (e.g., LBM 3,732 to 7,465 ns) and corrected its power to
0.036-0.044 W. (10) Found and fixed: the configuration generator wrote
ReRAM access energies under key names NVMain never reads
(ReadEnergy/WriteEnergy vs. the live Erd/Ewr) - so every ReRAM
configuration had silently used identical stock access-energy constants
for the pipeline\'s entire history, despite NVSim characterizing a 5.7x
read-energy difference between the families. Wiring the live keys and
re-running the 96-run ReRAM matrix left every static floor, latency, and
endurance counter identical while making dynamic power
technology-differentiated for the first time (hand-reconciled against
access counts to four significant figures). A definitive key-liveness
audit of every generator-written key against the simulator\'s parameter
readers closed this bug class permanently.

The repair was validated before its results were adopted. Pilot runs
confirmed the leakage wiring end-to-end: the repaired 1T1R full-DIMM
configuration measures 50.858 W of static power against a 50.858 W
device-derived target (0.0% error), with real dynamic power resolving to
approximately 5 mW under GCC - confirming that ungated ReRAM power is,
to three significant figures, leakage. The full 120-run matrix (20
configurations × 6 workloads, including all 96 ReRAM runs) was then
re-executed under the repaired model with anchor checks passing, and the
endurance write counters were verified bit-identical to the pre-repair
runs - the repair changes power accounting, not timing. The DDR5
baseline repairs were validated by the same discipline: the recalibrated
refresh model produced exactly the predicted 21,333 refresh events per
bank over the 200M-cycle window, the voltage correction reproduced the
predicted linear scaling to within 4×10⁻⁶ relative deviation, and all
non-DDR5 rows remained byte-identical across re-runs. The final
calibration cycle added an independent, blind re-verification pass (a
fresh session re-deriving every check from configs, sources, and raw
statistics), which validated the DDR5 calibration end-to-end, refuted
one suspected regression, and surfaced item (10). (11) Found and fixed:
the configurations assumed heterogeneous host CPU frequencies - CPUFreq
800 MHz for every ReRAM configuration, 2 GHz for PCM, 3 GHz for DDR5 -
and NVMain admits trace timestamps against a (CPUFreq/CLK)-scaled cutoff
without rescaling them, so ReRAM was replayed under \~3.75x slower
wall-clock request arrivals than DDR5 and each clock domain saw a
different admitted trace population. Repaired by fixing CPUFreq \= 3 GHz
for every configuration and matching every cycle budget to the same
250M-trace-cycle admission - 83.33 ms wall-clock for all (ReRAM 66.7M
memory cycles, PCM 33.3M, DDR5\'s existing 200M unchanged): every
technology now processes the identical request population per workload,
verified exactly (407,363 GCC / 16,447,102 LBM admissions across all
eight configuration families). The correction moved exactly what its
direction analysis predicted: admission-sensitive compute-bound latency
rose (1T1R SLC GCC 98.0 to 130.9 ns, widening the DDR5 gap from 1.21x to
1.61x), trace-limited AI workloads did not move (the 4.7x GPT-2 deficit
is unchanged), static power did not move (anchors exact to the last
digit), and endurance write pressure rose toward each configuration\'s
service ceiling (worst-case 1T1R SLC lifetime 24.4 to 17.3 years at 128
GB). Exact-config snapshots now ship with every results generation,
closing a reproducibility gap in which on-disk configurations had
drifted from the state that produced banked results. The residual
limitations are items (5) and (6), plus the spec-limit character of
vendor IDD tables: ReRAM totals are worst-case ungated, absolute
queueing magnitudes inherit the uncached-trace caveat - and, more
broadly, the pipeline is open-loop trace replay with no CPU or
accelerator feedback path, so every latency reported here is a
memory-subsystem quantity: the 4.7x AI-inference deficit of Section
3.1.1 is a memory-latency ratio, not a projected application slowdown,
and latency-tolerant accelerators that overlap compute with memory
access would experience a smaller end-to-end penalty; additionally, the
completed-request and trace-player mechanism audit that exposed item
(11) confirms that, after the matched-host correction, every
configuration admits the identical request population per workload: GCC
and the four lighter traces complete in full for every technology, so
their latency averages compare identical populations, while LBM - the
one genuinely service-limited workload - is completed to a
technology-dependent depth (the sustained-throughput ordering of Section
3.1.1), so its latency averages cover each configuration\'s completed
prefix, and DDR5 power is reported as a two-vendor calibration band.
Within those bounds, the cross-technology power and PDP comparisons that
earlier drafts of this work withheld are restored in Sections 3.1.2,
3.1.3, and 3.3.

== 3.2. #strong[Architectural Scaling & Memory Level Parallelism] (Pareto Frontiers)
<architectural-scaling-memory-level-parallelism-pareto-frontiers>
While granular diagnostics reveal the baseline physical characteristics
of 22nm ReRAM, understanding its viability as a main memory replacement
requires evaluating how these modules scale. To map this, I plotted
multi-objective Pareto frontiers comparing Total System Power against
Average Total Latency as the ReRAM architecture scales from a single
chip to a 64-chip Full DIMM (8 GB SLC / 16 GB MLC).

#block(breakable: false)[
#image("media/media/image18.png", width: 6.5in, height: 4.682203630796151in)

#strong[Figure 20: Pareto scaling trajectory under the single-threaded
GCC workload.]
]

Under standard CPU-bound workloads like gcc (Figure 20), I identified a
phenomenon I term the “Flatline Paradox.” As the ReRAM architecture
scales from 1 chip up to 64 chips, the data points cluster horizontally:
the system gains almost zero latency benefit from the additional memory
ranks, because the single-threaded trace lacks the Memory Level
Parallelism (MLP) required to saturate the primary rank, leaving the
extended DIMM capacity unutilized. The repaired power model prices this
scaling honestly: peripheral leakage grows linearly with chip count
(0.80 W single-chip to 50.9 W full-DIMM for 1T1R SLC; 0.027 W to 1.12 W
for 1S1R SLC), so under low-MLP workloads capacity scaling buys no
latency and costs full leakage. This is the worst corner of the design
space for the transistor-gated family - and the strongest scaling
argument for the selector\'s leakage discipline.

#image("media/media/image19.png", width: 6.5in, height: 4.682203630796151in)

#block(breakable: false)[
#image("media/media/image20.png", width: 6.5in, height: 4.682203630796151in)

#strong[Figure 21 & 22: Pareto scaling trajectories under highly
parallel AI inference workloads (GPT-2 IFMAP and AlexNet IFMAP).]
]

To break the Flatline Paradox, I subjected the architecture to the
massive parallel read-storms of AI inference (Figures 21 and 22). Here,
the Pareto trajectories drop vertically. As the system scales to a Full
DIMM (indicated by the outlined markers), the memory controller
successfully leverages rank-level interleaving to clear the massive
request queue, drastically slashing latency. The 1T1R SLC Full DIMM
pushes aggressively downward on the latency axis, remaining
significantly faster than legacy NVMs - though its ungated 51.0 W module
power (Section 3.1.2) keeps it far above the DDR5 baseline on the power
axis at every scale point, while the selector-gated family achieves the
same vertical latency drop within a 1.25 W envelope. This confirms that
to extract maximum performance from ReRAM DIMMs, the host processor must
supply high-MLP workloads.

The Pareto trajectory for AlexNet OFMAP (Figure 23) reveals the most
extreme manifestation of the write-penalty scaling wall. Under sustained
write pressure, the 1S1R MLC configuration suffers a PDP spike to
5,003.8 W·ns against 1,629.2 W·ns for 1S1R SLC - a 3.1x write-torture
tax within the selector family - while the 1T1R family, whatever its
latency behavior, is priced out entirely by its 50.9 W leakage floor
(41,763.3 W·ns for 1T1R SLC). This confirms that high-density
cross-point topologies face fundamental efficiency limits under
write-intensive AI workloads, where iterative ISPV programming
operations saturate the memory controller queue.

#block(breakable: false)[
#image("media/media/image26.png", width: 6.5in, height: 4.682203630796151in)

#strong[Figure 23: Pareto scaling trajectory under write-torture
conditions (AlexNet OFMAP).]
]

#image("media/media/image21.png", width: 6.5in, height: 4.682203630796151in)

#block(breakable: false)[
#image("media/media/image22.png", width: 6.5in, height: 4.682203630796151in)

#strong[Figure 24 & 25: Pareto scaling trajectories under continuous
memory-streaming workloads (LBM SPEC2017 and STREAM).]
]

Finally, evaluating heavy streaming workloads (Figures 24 and 25) shows
each family riding its own leakage tier as capacity scales. The
selector-gated configurations remain within commodity power envelopes at
every scale point (1.31 W full-DIMM under LBM), while the
transistor-gated family scales linearly into infeasibility (51.0 W). In
both cases the power cost of scaling is linear peripheral leakage rather
than compounding dynamic or thermal penalties - the memory controller\'s
activity level perturbs module power by under 0.3% for 1T1R and by at
most \~11% for 1S1R (LBM) - never enough to change tier - and the latency
benefit of added ranks remains gated on workload MLP.

== 3.3. #strong[Global Viability] (Hero Graphs)
<global-viability-hero-graphs>
With the scaling dynamics established, the final evaluation must address
the core question: does 22nm ReRAM present a globally viable alternative
to DRAM?

#block(breakable: false)[
#image("media/media/image23.png", width: 6.5in, height: 3.699808617672791in)

#strong[Figure 26: Die-Level Density Comparison, normalized to DDR5 \=
1.00 (higher is better): NVSim-characterized die areas per GB versus a
commodity DDR5 baseline of 35 mm² per GB \[18\].]
]

To alleviate the severe memory supply-demand gap, MBMM must provide
superior physical scaling, and density is best read at three levels. At
the die level - what a module vendor can actually buy - Figure 26
normalizes NVSim\'s characterized die areas against a commodity DDR5
baseline of 35 mm² per GB (1.00) - a figure sitting inside the 33.1-37.6
mm²/GB band measured across Micron, Samsung, and SK hynix production 16
Gb DDR5 dies \[18\]: the selector cross-point delivers 1.92x DDR5\'s
density as SLC and 3.84x as MLC, while the transistor-gated 1T1R lands
at 0.22x (0.44x as MLC) - a 20F² access-transistor cell fabricated at
22nm cannot compete with 10 nm-class DRAM on area, which reinforces
1T1R\'s latency-niche verdict. At the cell level, the comparison becomes
node-independent and exact: DRAM stores one bit per 6F², 1T1R one per
20F² - a transistor-drive-limited figure \[14\] - and the selector
cross-point one per 4F² (two per 4F² as MLC) - so at any matched process
node, 1S1R MLC is 3.0x denser than DRAM and 1S1R SLC 1.5x denser, while
1T1R is intrinsically 3.3x less dense. That the measured die-level
advantage (1.92x) exceeds the 1.5x cell-level bound reflects real-die
overheads on the DRAM side - peripheral, spare, and interface area that
pure cell arithmetic ignores. The third level is headroom: the die-level
ratios are achieved across an asymmetric process comparison - DDR5
fabricated on 10 nm-class nodes (1γ \[17\]) with no remaining capacitor
runway \[5\], the ReRAM figures from a mature 22nm logic-compatible
process. A 4F² cross-point cell scales quadratically with feature size:
a port to a 12 nm-class node would multiply the density ratios by
roughly (22/12)² ≈ 3.4x before any stacking, and cross-point arrays
additionally admit back-end-of-line 3D deck stacking \[9\], a lever
planar DRAM does not possess. Node scaling further compounds through the
endurance capacity law of Section 3.1.4: a denser module is, by that
law, directly a longer-lived module.

Table 7 makes the third level concrete: the measured die-level ratios of
Figure 26, scaled quadratically to 16nm- and 12nm-class nodes, with the
back-end-of-line deck-stacking lever that only the cross-point
possesses.

#strong[Table 7: Projected die-level density versus DDR5 (\= 1.00) under
quadratic feature-size scaling and 3D deck stacking.]

#align(center)[#table(
  columns: 6,
  align: (col, row) => (auto,auto,auto,auto,auto,auto,).at(col),
  inset: 6pt,
  table.header(
    [#strong[Configuration]],
    [#strong[22nm (measured)]],
    [#strong[16nm (projected)]],
    [#strong[12nm (projected)]],
    [#strong[12nm, 2 decks]],
    [#strong[12nm, 4 decks]],
  ),
  [#strong[1S1R SLC]],
  [1.92],
  [3.63],
  [6.45],
  [12.9],
  [25.8],
  [#strong[1S1R MLC]],
  [3.84],
  [7.26],
  [12.9],
  [25.8],
  [51.6],
  [#strong[1T1R SLC]],
  [0.22],
  [0.42],
  [0.74],
  [—],
  [—],
  [#strong[1T1R MLC]],
  [0.44],
  [0.83],
  [1.48],
  [—],
  [—],
)
]

#emph[Projection: measured 22nm die-level anchors (Figure 26) x (22/F)²,
with the DDR5 baseline held fixed at its 10 nm-class density per the
end-of-roadmap capacitor argument \[5\]\[17\]. Deck rows multiply the
12nm figure by 2 and 4; 1T1R cannot deck-stack - its access transistor
is a front-end-of-line device.]

These projections are bounded claims, not measurements: the 16nm and
12nm columns are geometry rather than NVSim characterizations, they
optimistically assume peripheral circuits shrink with the cell array,
and selector device physics below the 2x-nm regime is unvalidated. The
counterpoint is equally real, and moving on two fronts: DRAM\'s escape
from the planar capacitor is on the incumbents\' public roadmap, with
Samsung outlining vertical-channel-transistor 3D DRAM for the second
half of the decade \[19\], and the challenger ecosystem is moving faster
still - a monolithic 3D X-DRAM built on 3D NAND-style vertical
processing passed proof-of-concept validation in April 2026, reporting
sub-10 ns access and second-scale retention \[25\]. Notably, even that
challenger\'s headline retention claim is a 15x longer refresh interval,
not refresh elimination: charge-based storage refreshes by construction,
so while 3D DRAM contests the density column of this comparison, the
zero-refresh power asymmetry this work quantifies survives every DRAM
roadmap, planar or vertical. The window Table 7 quantifies is therefore
real but not permanent - it is the interval in which a cross-point that
ports to logic-compatible nodes today faces a DRAM that must first
re-architect its cell to go vertical. Every density multiplier in the
table also compounds through the endurance capacity law of Section
3.1.4: each projected doubling of module capacity is, by that law,
directly a doubling of worst-case lifetime.

The same geometry extends beyond density to power - and this is the
extrapolation with architectural teeth. 1S1R\'s ungated draw is 97%
peripheral leakage, and periphery is standard CMOS that shrinks with the
process: to first order, static power per gigabyte falls by the same
(22/F)^2 factor that density rises. Holding the 8 GB module and its
measured 1.082 W static anchor fixed, a 16nm-class port lands at roughly
0.61 W ungated - at parity with DDR5\'s 0.651 W calibration floor with
no gating at all (the exact crossover sits at a 16.6nm feature size) -
and a 12nm-class port at roughly 0.36 W, 1.8x below the floor. Under
this arithmetic the gating requirement of Section 3.1.2 is not a
permanent architectural tax but a 22nm artifact: one full shrink buys
ungated parity, the second buys outright dominance, while the same
scaling leaves the transistor-gated family unsalvageable (50.9 W falls
only to \~15 W at 12nm - still 23x the DDR5 floor). Latency, by contrast,
neither improves nor collapses under scaling: filament switching is
voltage- and material-limited rather than lithography-limited - HfOx
devices demonstrated at 10 x 10 nm retain nanosecond-class switching
\[14\] - so the latency profile of Section 3.1.1 carries to first order,
with thinner-wire RC the main unmodeled risk. Endurance splits both
ways: device variability - the field\'s named barrier to large arrays
and multilevel operation, rooted in the stochastic filament process
\[14\] - is unvalidated at scaled dimensions, but the capacity law
converts every density multiplier in Table 7 into an equal lifetime
multiplier at fixed footprint. The caveats of the preceding paragraph
apply with full force - this is bounding geometry, not simulation, and
per-transistor leakage densities worsen at advanced nodes, making
area-proportional scaling an optimistic first order - but the direction
is uniform: every process generation moves the comparison in ReRAM\'s
favor, against a DDR5 baseline whose capacitor cannot follow
\[5\]\[17\].

A fair challenge to these projections is why no sub-22nm ReRAM exists to
measure, given that logic CMOS ships below 5nm. The answer is primarily
market structure, not device physics. ReRAM\'s commercial role today is
embedded flash replacement on mature 40-22nm foundry processes \[24\] -
the node range where embedded flash itself stops scaling - so no product
pull exists toward leading nodes, even though devices have been
demonstrated at 10 x 10 nm - with sub-10 nm filaments observed - in the
laboratory \[14\] and a 14nm-FinFET megabit macro has been demonstrated
\[20\]. The one scaled, selector-gated cross-point that did reach volume
production - Intel and Micron\'s 20nm-class 3D XPoint - was discontinued
in 2022 on cost-per-bit economics, squeezed between DRAM and NAND, not
on device failure \[23\]: an instructive precedent that the barrier at
scaled nodes has been the business model, not the physics. What scaling
genuinely risks at the device level is variability - the cycle-to-cycle
and device-to-device spread rooted in the stochastic motion of the
oxygen vacancies that form the filament, which the field itself names
the major remaining barrier to large arrays and multilevel operation
\[14\] - which is exactly why Table 7\'s 16nm and 12nm columns are
labeled projections rather than measurements, and why the memory
supply-demand crisis that motivates this work (Section 1.1) may be the
demand-side event that finally changes the economics.

#block(breakable: false)[
#image("media/media/image24.png", width: 6.5in, height: 3.7274365704286962in)

#strong[Figure 27: Overall System Efficiency (Geometric Mean PDP).]
]

However, density is a liability if the system is too slow or burns too
much power. The Geometric Mean PDP across all six workloads (Figure 27)
ranks the architectures under the repaired, whole-module power model -
with the mandatory caveat that the DRAM and PCM baselines model standard
idle behavior while the ReRAM figures are worst-case ungated (Section
3.1.6, item 5). The headline is an opportunity: ungated 1S1R SLC -
drawing 1.12 W with zero refresh - lands 1.7x from DDR5\'s 0.651 W at
the conservative vendor-calibration floor, and within 11% of outright
parity at the spec-limit ceiling; that gap is precisely the component an
idle-gating policy attacks, because 1S1R\'s draw is 97% static while
DDR5 spends 33-45% of its module power on refresh it can never shed. One
credible gating policy separates 1S1R SLC from DDR5 power parity - a
concrete research and product opening for gating-capable controllers and
selector-first DIMM architectures. The full ungated ranking, matching
Figure 27 bar-for-bar: DDR5 99.5 W·ns (150.9 at the Micron calibration
ceiling), PCM 165.3, 1S1R SLC 737.1, 1S1R MLC 1,991.4, 1T1R SLC
21,350.6, and 1T1R MLC 50,426.6. The selector\'s 47x standby discipline
cleanly partitions the ReRAM family: ungated 1T1R is not a viable DDR5
successor at any cell density (50.9 W per module, 50-78x DDR5) - the
contrast that elevates leakage discipline to the deciding architectural
requirement. PCM, for its part, survives on its 0.04 W floor at latency
costs relative to 1T1R SLC that range from \~4-6x under parallel AI to
13-16x under streaming and 49x under compute-bound GCC (now that it runs
at its cited 400 MHz basis - Section 3.1.6, item 9): it is not
displaced, but it marks the floor-power bound that gated ReRAM must
beat. ReRAM\'s path past both DDR5 and PCM therefore runs exclusively
through the idle-gating capability that the current toolchain cannot yet
simulate (Section 4.1).

How much of that draw a gating policy could actually reclaim is bounded
by how idle real memory is - a fraction that is strongly
workload-dependent, so one measured example is quoted to make the point,
not as a universal constant. Profiling Microsoft\'s Bing web-search and
Cosmos data-analytics servers, Malladi et al. report 67-97% processor
utilization against only 2-6% memory bandwidth utilization, with web
search drawing under 3% of peak channel bandwidth \[21\]: in that
deployment class - a large and commercially central one - the memory
channel sits idle the overwhelming majority of the time. Memory-bound
workloads occupy the other extreme, and it is a growing one: transformer
token generation is dominated by matrix-vector products of such low
arithmetic intensity that memory bandwidth, not compute, is its binding
constraint - and with peak hardware FLOPS scaling at 3.0x per two years
against DRAM bandwidth\'s 1.6x, the imbalance worsens by design \[22\].
This suite brackets that extreme deliberately: LBM and STREAM saturate
the channel, and GPT-2 is precisely the decode-class workload Gholami et
al. analyze. The arithmetic is honest about what this means - a
channel-saturating deployment gates little (f approaches 0), leaving the
ungated comparison to stand as measured, 1S1R at 1.72x the DDR5 floor
and 1.11x the ceiling - while Section 3.1.1\'s latency verdict already
assigns sustained high-parallelism serving to DDR5. The two verdicts are
mutually consistent: the workload class where gating cannot rescue ReRAM
power is the same class ReRAM already loses on latency, and even there
the ungated penalty is bounded at 1.7x, not the 50-78x of the
transistor-gated alternative. The bounding arithmetic for the 1S1R SLC
module follows directly from its measured composition (1.082 W static +
\~0.036 W dynamic under GCC): gating the static component for an idle
fraction f leaves (1-f) x 1.082 + 0.036 W of module power. Break-even
with DDR5\'s 0.651 W calibration floor requires only f \= 43% - a
threshold far below the web-serving example above, and one that much
busier deployments still clear - and just f \= 10% against the 1.008 W
vendor ceiling; a policy capturing 90% idleness, plausible for the
measured web-serving class, lands at roughly 0.14 W, about 4.5x below
the DDR5 floor. Two honesty bounds and one physical asymmetry frame
this: bandwidth utilization overstates achievable gating, since
power-down entry and exit residency consume part of every idle window;
DRAM also possesses power-down states that this comparison does not
exercise (the asymmetry caveat of Section 3.1.6, item 5, cuts both
ways); but the floor asymmetry is physical - an idle DRAM module must
keep refreshing to retain data, while a gated non-volatile module
retains it at zero power. These are bounding calculations, not
simulations; simulating the actual gating policy is the top future-work
item (Section 4.1).

#pagebreak()
<section-1>
Table 6 places every axis of the comparison side by side - the tabular
summary of the entire evaluation.

#strong[Table 6: Cross-technology summary, full-DIMM configurations.]

#align(center)[#table(
  columns: 7,
  align: (col, row) => (auto,auto,auto,auto,auto,auto,auto,).at(col),
  inset: 6pt,
  table.header(
    [#strong[Technology]],
    [#strong[GCC latency (ns)]],
    [#strong[GCC power (W)]],
    [#strong[Geo-mean PDP (W·ns)]],
    [#strong[Die density (× DDR5)]],
    [#strong[Worst-case lifetime \@128 GB]],
    [#strong[Architectural role]],
  ),
  [#strong[DDR5-4800]],
  [81.2],
  [0.651 (44.7% refresh)],
  [99.5],
  [1.00],
  [n/a (volatile)],
  [commodity baseline],
  [#strong[PCM]],
  [6,399.2],
  [0.040],
  [165.3],
  [1.25],
  [not evaluated],
  [floor-power NVM; 4-49x latency cost],
  [#strong[1T1R SLC]],
  [130.9],
  [50.870],
  [21,350.6],
  [0.22],
  [17.3 yr],
  [latency-optimized niche; infeasible ungated],
  [#strong[1S1R SLC]],
  [190.3],
  [1.118],
  [737.1],
  [1.92],
  [24.8 yr],
  [flagship: one gating policy from DDR5 parity],
  [#strong[1T1R MLC]],
  [330.2],
  [50.886],
  [50,426.6],
  [0.44],
  [4.3 yr],
  [infeasible ungated],
  [#strong[1S1R MLC]],
  [544.4],
  [1.180],
  [1,991.4],
  [3.84],
  [7.5 yr],
  [read-only capacity tier (frozen weights)],
)
]

#emph[Power/PDP: ReRAM worst-case ungated, DRAM/PCM standard idle.
Die-level density \= NVSim-characterized die area per GB vs a commodity
DDR5 baseline (Figure 26); node-independent cell-level bounds: DRAM
6F²/bit, 1T1R 20F²/bit, 1S1R 4F²/bit (2 bits/cell as MLC). Lifetime: LBM
worst case, uniform wear leveling, SLC 10⁷ / MLC 10⁶ endurance; under
the matched-host window the write streams are service-limited and differ
per configuration - 1T1R SLC absorbs 3,269,479 LBM writes per 83.33 ms
(39.2 M/s) versus 2,284,570 for 1S1R SLC (27.4 M/s), so the slower
writer wears correspondingly slower (1S1R SLC worst case 24.8 yr at 128
GB versus 1T1R\'s 17.3).]

= 4. Conclusion and Future Work
<conclusion-and-future-work>
This research delivers two things: a rigorous cross-layer
characterization of 22nm ReRAM as a DDR5 alternative - whose headline is
that selector-gated ReRAM sits one credible gating policy from DDR5
power parity - and a quantified fidelity audit of the standard
NVSim-to-NVMain toolchain in which nine of eleven discovered failure
modes were repaired - spanning the ReRAM configurations, the metrics
pipeline, and both non-ReRAM baselines - each repair validated by exact
anchor arithmetic and an independent blind re-verification, with the
affected simulations re-run. Using a cross-layer simulation pipeline
spanning device physics (NVSim), cycle-accurate memory simulation
(NVMain 2.0), and real workload traces from gem5 and SCALE-Sim, I
evaluated 20 memory configurations across 6 benchmarks. The key
quantitative findings are: 1T1R SLC ReRAM operates within 1.61x of
DDR5-4800\'s wall-clock latency under compute-bound execution - where it
runs 49x faster than the legacy PCM baseline (13-16x under sustained
streaming) - while trailing DDR5 by 4.7x under parallel AI inference
(Section 3.1.1); DDR5 spends 33-45% of its module power on refresh
across every workload while ReRAM\'s refresh cost is identically zero
(Figure 7); and under the repaired, ungated power model the technologies
separate into leakage classes in which the selector-gated 1S1R module is
the opportunity - 1.12 W, 1.7x DDR5\'s 0.651 W at the conservative
calibration floor and within 11% of parity at the ceiling, with
idle-gating unexercised - against 50.9 W for the transistor-gated 1T1R
module (50-78x DDR5, infeasible at DIMM scale) and 0.040 W for PCM, so
the 47x selector leakage discipline that NVSim characterizes at the
device level (794.7 vs. 16.9 mW per chip) becomes the deciding
architectural fact of the evaluation (ReRAM figures are worst-case
ungated; the DRAM and PCM baselines model standard idle behavior). A
critical and previously unquantified result is the endurance
characterization: under real workload write rates with uniform wear
leveling, lifetime scales linearly with module capacity - the modeled 8
GB SLC module yields 1.1 years under worst-case sustained streaming
(below the 5-10 year server target), while server-class 64-128 GB
modules reach 9-17 years, and compute-bound and read-dominant workloads
exceed the target by an order of magnitude at any capacity (Table 5).
The deployment recommendation follows directly from the repaired data,
and it inverts the intuitive choice: 1S1R SLC is the flagship
configuration - scale-viable power, 1.9x DDR5\'s die-level density (3.8x
as MLC), and a modest \~1.5x average-latency cost against 1T1R (1.3-1.7x
across the suite) - while 1T1R SLC, despite the best raw latency in the
ReRAM family, is infeasible ungated at DIMM scale and is relegated to a
latency-optimized niche pending aggressive idle-gating; MLC density
remains restricted to read-dominant applications (static weight storage
in AI inference pipelines) where the 4x write-latency penalty is rarely
triggered. Together these findings define a concrete agenda for research
and product work: gating-capable memory controllers (Section 4.1),
selector-first DIMM architectures, and MLC read-only capacity tiers for
frozen model weights. Finally, the mbmm\_master.py orchestration
framework, which bridges NVSim device characterization to NVMain system
simulation in a single reproducible pipeline - now with per-technology
leakage faithfully propagated - is contributed as an open-source
Physical-to-System memory simulator for the non-volatile memory research
community.

Latency analysis (3.1.1) revealed that the MLC write penalty is
workload-dependent rather than uniform. Under compute-bound traces such
as GCC, where memory requests arrive infrequently, MLC write latency is
absorbed by the memory controller queue with negligible impact on
average read latency. Under continuous streaming workloads such as LBM
and STREAM, the penalty compounds: 1T1R MLC latency reaches 1,128 ns
compared to 468 ns for 1T1R SLC, and 1S1R MLC reaches 1,937 ns (Figure
2) - 2.4x and 4.1x slowdowns that make MLC unsuitable for
bandwidth-saturating applications.

Power analysis (3.1.2), executed on the repaired power model,
established DDR5\'s structural refresh burden (33-45% of module power on
every workload, from real rank-level counters under the
vendor-calibrated model) and replaced the earlier technology-blind
“flatline” with a leakage-class hierarchy: 50.9 W ungated 1T1R, 1.12 W
ungated 1S1R, 0.651 W DDR5 (calibration floor), 0.040 W PCM. Real ReRAM
dynamic power is small and now technology-differentiated (12-98 mW
module-wide under GCC), so ungated ReRAM power is leakage - and the
selector\'s 47x leakage advantage is the largest
technology-differentiating fact this project measured.

The Power-Delay Product analysis (3.1.3), restored to cross-technology
scope by the repaired model (with the ungated-ReRAM caveat attached
throughout), inverts the intra-ReRAM hierarchy: 1S1R SLC (geometric mean
737.1 W·ns) dominates 1T1R SLC (21,350.6) by 29x, because the leakage
term dwarfs the latency term; DDR5 stands at 99.5 W·ns and PCM at 165.3.
Density still costs efficiency within each family (1S1R MLC at 1,991.4),
but leakage class - not cell type - decides the ranking.

Endurance analysis (3.1.4) addressed the most common objection to
resistive memory deployment. Under real workload write rates with
uniform wear leveling, lifetime scales linearly with module capacity:
the modeled 8 GB SLC module yields 1.1 years under worst-case sustained
streaming (LBM) - below the 5-10 year server replacement cycle - while
64-128 GB server-class modules reach 9-17 years, and all other workloads
exceed 20 years even at 8 GB (Table 5). Endurance is thus a capacity-
and workload-dependent design constraint, binding only for small modules
under sustained write streaming, and directly motivates the
wear-leveling and write-coalescing work of Section 4.2.

Robustness analysis (3.1.5) demonstrated that the simulated operating
point is stable under device-level manufacturing variation. A
three-point ReadVoltage sweep at +/-20% of the nominal 1.40 V operating
point showed read latency to be completely invariant while read energy
scales monotonically with applied voltage (Figure 19). System-level PDP
variation across the full sweep is below 4%; the sweep predates the
power-model repair, and the repair only strengthens the insensitivity
conclusion by raising the static share of total power (Section 3.1.5).

Pareto scaling analysis (3.2) revealed that multi-rank and multi-chip
scaling does not uniformly improve efficiency. Under compute-bound
workloads, scaling from a single chip to a full 64-chip DIMM buys no
latency while multiplying leakage roughly 64x - the Flatline Paradox
(Figure 20) - because the memory subsystem remains idle and the dominant
cost is static leakage, which scales linearly with capacity. Under
write-heavy workloads, multi-rank scaling likewise hurts efficiency
(Figure 23), making single-chip or 8-chip configurations the
Pareto-optimal choice for write-intensive deployments; only high-MLP AI
workloads convert added ranks into latency gains.

== 4.1. Future Work: Simulator and Infrastructure Enhancements
<future-work-simulator-and-infrastructure-enhancements>
#strong[Power-Down Restoration (top priority)]: The power-model repair
scoped by the audit has landed - NVSim\'s per-technology leakage is
wired into NVMain\'s standby-energy parameters, module-sum power
semantics are adopted for every technology, and the full simulation
matrix was re-run and anchor-validated (Section 3.1.6). The remaining
item is restoring NVMain\'s disabled power-down state machine with a
defensible idle-gating policy: every ReRAM figure in this book is
worst-case ungated, and the 1.7x gap separating 1S1R SLC from DDR5 - as
well as the 0.04 W PCM floor - can only be closed or conceded once
idle-gating can actually be simulated. This is the single
highest-leverage item of future work.

- #strong[Parameter Optimization]: Conduct a sensitivity analysis on
  NVSim parameters, such as ReadVoltage and WritePulseWidth, to identify
  the efficiency-optimal operating region for LOP (Low Operating Power)
  devices that maximizes sensing margin while minimizing energy.

- #strong[Native MLC Logic]: Resolve the NVSim C++ \"Floating Point
  Exception\" (FPE) specifically within the Mat.cpp sensing logic to
  replace my current \"Analytical Penalty Method\" with native
  circuit-level characterization of iterative sensing.

== 4.2. Future Work: Architectural Extensions and System Scaling
<future-work-architectural-extensions-and-system-scaling>
- #strong[The L3 Cache Mitigation:] Evaluating the integration of a
  large last-level cache (LLC) or near-memory write buffer to absorb and
  coalesce ReRAM write penalties, a mitigation strategy historically
  proven essential for legacy phase-change memory #strong[\[11\]],
  specifically for write-intensive AI workloads like AlexNet OFMAP.

- #strong[Memory Controller Queue Analysis (The Flatline Paradox):]
  Deep-diving into the NVMain memory controller interface, queue depths,
  and bus saturation limits to definitively resolve the multi-rank
  scaling flatline.

- #strong[Endurance-Aware Scheduling:] Implementing wear-leveling
  algorithms at the controller level to protect the finite lifecycle of
  the 22nm cells.

- #strong[Macro-Scale 1T1R Array Limits:] While this evaluation
  restricted 1T1R subarrays to 1024x1024 cells to maintain baseline
  architectural parity with the 1S1R models, 1T1R arrays are not
  fundamentally bound by the same sneak-path leakage limits. Future
  research should evaluate the latency, power, and routing tradeoffs of
  enlarging 1T1R arrays to their absolute commercial foundry
  manufacturing limits (e.g., TSMC maximum macro bounds) to push DIMM
  capacity to the extreme.

- #strong[Node Scaling and 3D Stacking]: this evaluation deliberately
  fixed ReRAM at 22nm - a manufacturability-anchored choice \[8\] -
  while DRAM competes from 10 nm-class nodes with no remaining capacitor
  runway \[5\], \[17\]. Future work should project the 4F²
  cross-point\'s quadratic density dividend at 1x-nm feature sizes,
  quantify the multiplicative effect of back-end-of-line deck stacking
  \[9\], and re-derive the NVSim characterization at scaled nodes -
  where access-transistor leakage is expected to worsen while the
  selector\'s leakage discipline widens - propagating every density gain
  through the endurance capacity law, which converts capacity directly
  into lifetime.

== 4.3 Data Availability and Reproducibility
<data-availability-and-reproducibility>
To ensure the scientific reproducibility of the 22nm ReRAM models, the
complete simulation stack, including the mbmm\_master.py orchestration
script, modified NVSim/NVMain C++ source files, and JSON configuration
data, has been made publicly available.

#blockquote[
#strong[Project Repository:]
#link("https://www.google.com/search?q=https://github.com/uvKogan/MBMM&authuser=3")[#underline[https:\/\/github.com/uvKogan/MBMM]]
]

#pagebreak()
<section-2>
= References
<references> #strong[\[1\]] M. Ahmad, \"NAND Flash\'s Reversal of Fortune Amid the AI Boom,\" #emph[EE Times], Jan. 26, 2026. \[Online\]. Available: #link("https://www.eetimes.com/nand-flashs-reversal-of-fortune-amid-the-ai-boom/")[#underline[https:\/\/www.eetimes.com/nand-flashs-reversal-of-fortune-amid-the-ai-boom/]]. \[Accessed: Apr. 25, 2026\].

#strong[\[2\]] A. J. Fleischer, \"How AI Broke the Memory Market,\" #emph[Octopart Pulse], Mar. 13, 2026. \[Online\]. Available: #link("https://octopart.com/pulse/p/how-ai-broke-memory-market")[#underline[https:\/\/octopart.com/pulse/p/how-ai-broke-memory-market]]. \[Accessed: Apr. 25, 2026\].

#strong[\[3\]] X. Dong et al., \"NVSim: A Circuit-Level Performance, Energy, and Area Model for Emerging Nonvolatile Memory,\" #emph[IEEE Trans. Comput.-Aided Design Integr. Circuits Syst.], vol. 31, no. 7, pp. 994-1007, July 2012.

#strong[\[4\]] M. Poremba, T. Zhang, and Y. Xie, \"NVMain 2.0: A user-friendly memory simulator to model (non-)volatile memory systems,\" IEEE Comput. Archit. Lett., vol. 14, no. 2, pp. 140-143, July-Dec. 2015.

#strong[\[5\]] International Roadmap for Devices and Systems (IRDS), \"More Moore,\" 2024. \[Online\]. Available: #link("https://irds.ieee.org/images/files/pdf/2024/2024IRDS_MM.pdf")[#underline[https:\/\/irds.ieee.org/images/files/pdf/2024/2024IRDS\_MM.pdf]].

#strong[\[6\]] L. R. Upton et al., \"EMBER: A 100 MHz, 0.86 mm2, multiple-bits-per-cell RRAM macro in 40 nm CMOS with compact peripherals and 1.0 pJ/bit read circuitry,\" in Proc. IEEE 49th Eur. Solid State Circuits Conf. (ESSCIRC), Sep. 2023, pp. 469-472.

#strong[\[7\]] C. Matsui, A. Yamada, N. Misawa, and K. Takeuchi, \"ReRAM resistance design of LRS and HRS for ultrahigh-capacity digital memory and analog Computation-in-Memory,\" IEICE Trans. Fundamentals, vol. E109.A, no. 3, pp. 596-603, Mar. 2026. DOI: 10.1587/transfun.2025VLP0011

#strong[\[8\]] C. Xue et al., \"16.1 A 22nm 4Mb 8b-Precision ReRAM Computing-in-Memory Macro with 11.91 to 195.7TOPS/W for Tiny AI Edge Devices,\" #emph[2021 IEEE International Solid-State Circuits Conference (ISSCC)], San Francisco, CA, USA, 2021, pp. 245-247.

#strong[\[9\]] S. H. Jo et al., \"3D-stackable crossbar resistive memory based on Field Assisted Superlinear Threshold (FAST) selector,\" #emph[2014 IEEE International Electron Devices Meeting (IEDM)], San Francisco, CA, USA, 2014, pp. 6.7.1-6.7.4.

#strong[\[10\]] JEDEC Solid State Technology Association, \"DDR5 SDRAM Standard,\" JESD79-5D, Nov. 2025. \[Online\]. Available: #link("https://www.jedec.org/standards-documents/docs/jesd79-5d")[#underline[https:\/\/www.jedec.org/standards-documents/docs/jesd79-5d]].

#strong[\[11\]] B. C. Lee, E. Ipek, O. Mutlu, and D. Burger, \"Architecting phase change memory as a scalable dram alternative,\" in #emph[Proc. 36th Annu. Int. Symp. Comput. Archit. (ISCA)], 2009, pp. 2-13.

#strong[\[12\]] A. Samajdar, J. M. Joseph, Y. Zhu, P. Whatmough, M. Mattina, and T. Krishna, \"A Systematic Methodology for Characterizing Scalability of DNN Accelerators Using SCALE-Sim,\" in #emph[Proc. IEEE Int. Symp. Perform. Anal. Syst. Softw. (ISPASS)], 2020, pp. 58-68.

#strong[\[13\]] B. Q. Le et al., “Resistive RAM With Multiple Bits Per Cell: Array-Level Demonstration of 3 Bits Per Cell,” #emph[IEEE Trans. Electron Devices], vol. 66, no. 1, pp. 641–648, Jan. 2019.

#strong[\[14\]] H.-S. P. Wong et al., “Metal–Oxide RRAM,” #emph[Proc. IEEE], vol. 100, no. 6, pp. 1951–1970, June 2012. DOI: 10.1109/JPROC.2012.2190369

#strong[\[15\]] M. Lanza et al., “Standards for the Characterization of Endurance in Resistive Switching Devices,” #emph[ACS Nano], vol. 15, no. 11, pp. 17214–17231, Nov. 2021. DOI: 10.1021/acsnano.1c06980

#strong[\[16\]] Data Center Knowledge, “Data Center Hardware Refresh Cutback by Microsoft – What’s Next?,” Aug. 25, 2022. \[Online\]. Available: https:\/\/www.datacenterknowledge.com/hyperscalers/data-center-hardware-refresh-cutback-by-microsoft-what-s-next-. \[Accessed: Jul. 10, 2026\].

\[17\] TrendForce, \"Micron Races Ahead in 10nm-Class DRAM with 1γ DDR5 Samples Delivered to Intel & AMD,\" Feb. 26, 2025. \[Online\]. Available: https:\/\/www.trendforce.com/news/2025/02/26/news-micron-races-ahead-in-10nm-class-dram-with-1γ-ddr5-samples-delivered-to-intel-amd/. \[Accessed: Jul. 11, 2026\].

\[18\] J. Choe, \"Comparing DDR5 Memory From Micron, Samsung, SK Hynix,\" EE Times, Feb. 15, 2022. \[Online\]. Available: https:\/\/www.eetimes.com/comparing-ddr5-memory-from-micron-samsung-sk-hynix/. \[Accessed: Jul. 12, 2026\].

\[19\] A. Shilov, \"Samsung Puts 3D DRAM on the Roadmap, Stacked DRAM to Follow,\" Tom\'s Hardware, Apr. 3, 2024. \[Online\]. Available: https:\/\/www.tomshardware.com/pc-components/dram/samsung-outlines-plans-for-3d-dram-which-will-come-in-the-second-half-of-the-decade. \[Accessed: Jul. 12, 2026\].

\[20\] J. Yang et al., \"A 14nm-FinFET 1Mb Embedded 1T1R RRAM with a 0.022µm² Cell Size Using Self-Adaptive Delayed Termination and Multi-Cell Reference,\" in Proc. IEEE Int. Solid-State Circuits Conf. (ISSCC), 2021. DOI: 10.1109/ISSCC42613.2021.9365945

\[21\] K. T. Malladi, F. A. Nothaft, K. Periyathambi, B. C. Lee, C. Kozyrakis, and M. Horowitz, \"Towards Energy-Proportional Datacenter Memory with Mobile DRAM,\" in Proc. 39th Annu. Int. Symp. Computer Architecture (ISCA), 2012. DOI: 10.1109/ISCA.2012.6237004

\[22\] A. Gholami, Z. Yao, S. Kim, C. Hooper, M. W. Mahoney, and K. Keutzer, \"AI and Memory Wall,\" IEEE Micro, vol. 44, no. 3, May/June 2024. DOI: 10.1109/MM.2024.3373763

\[23\] Tom\'s Hardware, \"Intel Kills Optane Memory Business Entirely, Pays \$559 Million to Exit,\" Jul. 28, 2022. \[Online\]. Available: https:\/\/www.tomshardware.com/news/intel-kills-optane-memory-business-for-good. \[Accessed: Jul. 13, 2026\].

\[24\] TechInsights, \"Advanced TSMC 22ULL Embedded RRAM Chip Unveiled.\" \[Online\]. Available: https:\/\/www.techinsights.com/blog/advanced-tsmc-22ull-embedded-rram-chip-unveiled. \[Accessed: Jul. 13, 2026\].

\[25\] Tom\'s Hardware, \"Neo Semiconductor\'s Revolutionary 3D X-DRAM for AI Processors Has Passed Proof-of-Concept Validation,\" Apr. 24, 2026. \[Online\]. Available: https:\/\/www.tomshardware.com/tech-industry/artificial-intelligence/neo-semiconductors-revolutionary-3d-x-dram-for-ai-processors-has-passed-proof-of-concept-validation-company-secures-funding-to-develop-next-gen-memory-hbm-alternative. \[Accessed: Jul. 13, 2026\].

\[26\] N. Binkert et al., \"The gem5 Simulator,\" ACM SIGARCH Computer Architecture News, vol. 39, no. 2, pp. 1-7, May 2011. DOI: 10.1145/2024716.2024718

\[27\] J. D. McCalpin, \"Memory Bandwidth and Machine Balance in Current High Performance Computers,\" IEEE Computer Society Technical Committee on Computer Architecture (TCCA) Newsletter, pp. 19-25, Dec. 1995.

\[28\] Standard Performance Evaluation Corporation, \"SPEC CPU 2017 Benchmark Suite.\" \[Online\]. Available: https:\/\/www.spec.org/cpu2017/. \[Accessed: Jul. 13, 2026\].

\[29\] Micron Technology, Inc., \"16Gb DDR5 SDRAM Addendum: MT60B4G4, MT60B2G8, MT60B1G16, Die Revision A,\" Doc. No. CCM005-0005-1684161373-30, Rev. D, Feb. 2023. \[Online\]. Available: https:\/\/www.micron.com/products/memory/dram-components/ddr5-sdram/part-catalog

\[30\] SK hynix Inc., \"16Gb DDR5 SDRAM,\" datasheet. \[Online\]. Available (registration required): https:\/\/product.skhynix.com/support/downloads.go

#pagebreak() <section-3>
= Appendix A: Simulation Parameters and Literature Grounding
<appendix-a-simulation-parameters-and-literature-grounding>
- #strong[Process Node:] 22nm FinFET LOP (Low Operating Power).
  #emph[Justification:] LOP was selected over High Performance (HP) to
  guarantee electrical convergence in the NVSim solver and to accurately
  reflect the strict thermal envelopes required for high-capacity Main
  Memory modules.

- #strong[Resistance Targets:] $10^5 Omega$ LRS and $10^9 Omega$ HRS.
  #emph[Reference:] Calibrated to #strong[Matsui et al. \[7\]] to
  mitigate bitline IR-drop on dense arrays.

- #strong[MLC Penalties:] 3x Read Latency, 4x Write Latency.
  #emph[Reference:] Derived from the analytical heuristics of the
  #strong[EMBER Macro \[6\]] to account for ADC precision and ISPV
  (Iterative Step-and-Verify) overhead. These penalty factors are
  consistent with published multi-level ReRAM characterization (e.g., Le
  et al. \[13\], 3-bit/cell RRAM array-level demonstration), and
  represent a conservative lower bound for ISPV overhead at 2 bits/cell.

- #strong[Bit-Cell Area:] $20 med F^2$ for 1T1R, $4 med F^2$ for 1S1R.
  #emph[Justification:] $20 med F^2$ reflects the physical reality of
  CMOS-compatible access transistors, whereas $4 med F^2$ represents the
  idealized limit of cross-point selector technology. The 1T1R figure is
  transistor-limited, not memristor-limited: the memristor occupies the
  back-end-of-line above the cell, while the access transistor must be
  sized wide enough to source the SET/RESET programming current \[14\].
  A production-grade 14nm FinFET embedded 1T1R macro reports a 0.022 µm²
  cell - about 112F² at that node \[20\] - so 20F² is a generous
  assumption for 1T1R, which makes the density verdict against it
  conservative. Note that the 4F² figure is the array-level cell
  footprint; peripheral circuitry (sense amplifiers, row decoders,
  column multiplexers) adds overhead, and the periphery-inclusive
  die-level density ratios are reported in Section 3.3 and Figure 26
  (1S1R: 1.92x SLC / 3.84x MLC versus DDR5).

#pagebreak()
<section-4>
= Appendix B: Execution Pipeline and Command Interface
<appendix-b-execution-pipeline-and-command-interface>
To facilitate replication of the system scaling and trace execution, the
following command-line interface (CLI) instructions document the exact
mbmm\_master.py parameters used to generate the results in Section 3.

#strong[B.1: Configuration Generation] The system architecture factory
dynamically maps hardware constraints (e.g., forcing a 64-bit bus width
for single-chip models) sets the DIMM clock frequency to 800 MHz, and -
since the matched-host correction (Section 3.1.6, item 11) - pins the
host reference frequency to CPUFreq \= 3000 MHz for every configuration:

Bash

#box(width: 0pt)[#text(fill: white)[]]python3 3\_gen\_nvmain\_config.py \-\-freq 800

#box(width: 0pt)[#text(fill: white)[]]#strong[B.2: High-Cycle Batch Simulation] The master orchestration
script executes the gcc\_spec2017.nvt trace across the full matrix of 18
architectures (DRAM baselines, 1T1R, and 1S1R up to 64-chip Full DIMMs)
with matched-host cycle budgets, cycles \= ceil(250,000,000 x CLK /
3000), so that every configuration admits the identical trace population
over an identical 83.33 ms window (Section 3.1.6, item 11) - 66,666,667
cycles for the 800 MHz ReRAM matrix:

Bash

#box(width: 0pt)[#text(fill: white)[]]python3 mbmm\_master.py \-\-cycles 66666667 \-\-trace
benchmarks/gcc\_spec2017.nvt \-\-models \\

2D\_DRAM\_example 3D\_DRAM\_example \\

reram\_22nm\_1t1r\_slc\_single reram\_22nm\_1t1r\_slc\_8chip
reram\_22nm\_1t1r\_slc\_16chip reram\_22nm\_1t1r\_slc\_full\_dimm \\

reram\_22nm\_1t1r\_mlc\_single reram\_22nm\_1t1r\_mlc\_8chip
reram\_22nm\_1t1r\_mlc\_16chip reram\_22nm\_1t1r\_mlc\_full\_dimm \\

reram\_22nm\_selector\_slc\_single reram\_22nm\_selector\_slc\_8chip
reram\_22nm\_selector\_slc\_16chip
reram\_22nm\_selector\_slc\_full\_dimm \\

reram\_22nm\_selector\_mlc\_single reram\_22nm\_selector\_mlc\_8chip
reram\_22nm\_selector\_mlc\_16chip
reram\_22nm\_selector\_mlc\_full\_dimm

The DDR5-4800 and PCM baselines complete the 20-configuration matrix and
are executed with the same interface using their model names
(DDR5\_4800\_DRAM, pcm\_microsoft\_2009) and their own matched-host
budgets (200,000,000 and 33,333,334 cycles; 2D/3D controls: 55,500,000
and 111,083,334); the same command is repeated for each of the six
benchmark traces.

#box(width: 0pt)[#text(fill: white)[]]

== Appendix C: Reproducibility Statement
<appendix-c-reproducibility-statement>
Repository: https:\/\/github.com/uvKogan/MBMM. The complete simulation
stack (NVSim 22nm FinFET LOP models, NVMain 2.0 configurations, workload
traces, and all post-processing scripts) is available under the MIT
License.

Software versions: NVSim (patched, commit hash in repo README), NVMain
2.0 (patched, commit hash in repo README), gem5 v25.1, SCALE-Sim v2,
Python 3.10+, matplotlib 3.9, pandas 2.2.

Pipeline interface: The master orchestration script mbmm\_master.py
accepts \-\-cycles (simulation window), \-\-trace (NVMain trace file), and
\-\-models (space-separated list of named configurations). A complete
simulation run across all 20 configurations and 6 benchmarks at 200M
cycles completes in approximately 8-12 hours on a standard Linux
workstation. All statistical outputs
(processed\_bar\_chart\_metrics.csv, processed\_hero\_metrics.csv,
processed\_geometric\_means.csv) and generated figures are written to
results/ and are fully reproducible from the raw NVMain stats files.
