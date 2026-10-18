# Reference Guide - Technical_Report.typ

This guide covers `Technical_Report.typ`'s reference list only. As of the 2026-09 short-book revision, the document set has two separate books with two separate, independent reference numberings: `Technical_Report.typ` (122 pages, the complete technical report and knowledge base, 100 references, [1]-[100]) and `Project_Book.typ` (the short, reader-facing book, 26 printed pages, 48 references, [1]-[48], its own numbering - a citation like "book [12]" always needs the book named, the two [12]s are different sources). This guide's per-reference entries below are Technical_Report numbering.

A quick-reference summary of all 100 sources cited in `Technical_Report.typ`. Each entry: what it is, and the one or two things you need to know about *why* it's cited here. Compiled from an independent verification pass (Aug 2026) that re-checked every citation against its actual source (local PDF or live web fetch), not just trusted the earlier drafts; [55]-[100] were added by the September 2026 revision's Section 3.4 (Near and Far Memory) and the bit-errors-and-ECC subsection of 3.1.2, and are summarized more briefly below in three themed groups rather than individually re-verified against their full texts (most are used for a single named figure, quoted directly from the reference entry's own parenthetical in `Technical_Report.typ`).

The book's MLC penalty multipliers are: **1.5x read latency, 3.263x write latency, 1.1x read energy, 3.0x write energy** (2 bits/cell vs. 1 bit/cell), all sourced from the EMBER macro's two publications, [6] and [31] below.

---

## Market / Industry Context

**[1] Ahmad, "NAND Flash's Reversal of Fortune Amid the AI Boom," EE Times, 2026**
A NAND-market recovery story; cited here only for a secondary point it makes about Samsung/SK Hynix reallocating fab capacity from DRAM to HBM. Supporting/context citation, not the article's main topic - worth knowing when you re-read the abstract's "DRAM-to-HBM reallocation" claim.

**[2] Fleischer, "How AI Broke the Memory Market," Octopart Pulse, 2026**
The book's more central source for the AI-driven memory shortage premise. Verified via direct fetch of a mirrored copy (Octopart itself blocks fetches with bot protection) - confirms the article is real and on-topic (data centers consuming up to 70% of high-end memory chips in 2026, Samsung/SK Hynix wafer output declines, sharp DRAM price spikes), and it directly backs the book's only claim drawn from it: DRAM-to-HBM wafer reallocation causing a supply-demand gap (Technical_Report.typ Abstract and Section 1.1 "Economic Drivers" - both stated qualitatively, no numbers). An earlier annotation here cited "~3x HBM wafer capacity" and "40% advanced-capacity reallocation" figures attributed to this article; neither appears in it (the 3x figure traces to an unrelated, uncited Substack post) and neither is used in the book text, so no book fix was needed - this was a reference-guide-only error, now corrected.

**[16] "Data Center Hardware Refresh Cutback by Microsoft," Data Center Knowledge, 2022**
Cited for exactly one statistic: enterprise servers now average 5.4 years of useful life, trending toward 6-7 years. This sets the endurance/lifetime bar the book's ReRAM configs are judged against.

**[17] TrendForce, "Micron Races Ahead in 10nm-Class DRAM with 1γ DDR5...", 2025**
Confirms Micron's newest DDR5 process (1-gamma) is a 10nm-class node. Reused repeatedly throughout the book's density/scaling argument as the anchor fact for "DDR5 is near the end of its scaling roadmap."

**[18] Choe, "Comparing DDR5 Memory From Micron, Samsung, SK Hynix," EE Times, 2022**
A real die-teardown comparison giving actual measured die sizes for 16Gb DDR5 from three vendors. The book's "35 mm²/GB" DDR5 baseline and "33.1–37.6 mm²/GB" band are directly, correctly derived from this article's numbers (verified to the decimal).

**[19] Shilov, "Samsung Puts 3D DRAM on the Roadmap," Tom's Hardware, 2024**
Confirms Samsung's public roadmap for vertical-channel-transistor DRAM (2nd half of this decade) and true 3D-stacked DRAM after that. Used as the counterpoint showing DRAM's escape route from capacitor scaling is real but still years out.

**[22] Gholami et al., "AI and Memory Wall," IEEE Micro, 2024**
The paper that coined "AI and Memory Wall" - peak hardware FLOPS have scaled 3.0x per two years vs. DRAM bandwidth's 1.6x. Both numbers quoted exactly correctly in the book.

**[23] "Intel Kills Optane Memory Business Entirely," Tom's Hardware, 2022**
Intel's 2022 exit from 3D XPoint/Optane, a $559M write-off. Used as precedent: a scaled selector-gated memory reached mass production and was killed by cost economics, not physics - relevant to the book's own 1S1R selector discussion.

**[25] "Neo Semiconductor's 3D X-DRAM...Passed Proof-of-Concept Validation," Tom's Hardware, 2026**
A very recent (Apr. 2026) challenger DRAM technology: sub-10ns access, >1 second retention (~15x longer refresh interval - the book correctly notes this is refresh *reduction*, not elimination; it's still charge-based DRAM).

**[34] Intel Corp., "Ultra High Bandwidth Memory with Backend Transistors," U.S. Patent Application Pub. No. US 2026/0191095 A1, filed 2024, published Jul. 2026**
Intel's real, publicly filed patent for "Cross-Batch Memory" (XBM): moves the 1T1C DRAM cell into back-end-of-line thin-film transistors and replaces HBM's silicon interposer with direct die-to-die UCIe links, targeting HBM4's footprint at lower packaging cost. A third DRAM-roadmap front alongside [19]/[25] - this one attacks packaging economics, not cell density. Patent-stage only: no independent performance data, not targeted for commercialization before 2030.

**[35] TrendForce, "Intel Patent Reveals XBM Matching HBM4 Footprint Without Interposers...," 2026**
Trade-press corroboration of [34]'s technical claims (32 GT/s UCIe links, 0.5–5GB per die, 8/16-high stacks) and the post-2030 commercialization timeline, independently of the patent text itself.

---

## Core Simulation Tools & Benchmarks

**[3] Dong et al., "NVSim," IEEE TCAD, 2012**
The device-level circuit simulator (area/energy/timing) this project uses for hardware characterization. One soft spot: it's co-cited with [14] for a "~20F²" bit-cell area figure that neither paper actually states as a specific number - the wording has been softened to reflect this.

**[4] Poremba, Zhang, Xie, "NVMain 2.0," IEEE CAL, 2015**
The architectural (system-level) memory simulator paired with NVSim. NVSim answers "how good is one memory array"; NVMain answers "how does a full memory system with many arrays and ranks behave."

**[12] Samajdar et al., "SCALE-Sim," ISPASS 2020**
A cycle-accurate systolic-array DNN accelerator simulator, used purely as a trace generator - produces realistic AI-inference memory-access patterns (e.g., AlexNet layers) to stress-test the memory systems.

**[26] Binkert et al., "The gem5 Simulator," ACM SIGARCH CAN, 2011**
The well-known general-purpose CPU+memory architecture simulator used to run SPEC CPU2017 and capture memory traces.

**[27] McCalpin, "Memory Bandwidth and Machine Balance," TCCA Newsletter, 1995**
The origin paper of the STREAM benchmark - the standard synthetic test for *sustained* (not burst) memory bandwidth. Used as the book's pure-bandwidth baseline workload.

**[28] SPEC CPU2017 Benchmark Suite**
The industry-standard real-world compute benchmark suite. The book picks two sub-benchmarks as opposite ends of a spectrum: 602.gcc (irregular, branch-heavy, compute-bound) and 619.lbm (regular, bandwidth-heavy).

---

## ReRAM Device Physics (the load-bearing group)

**[7] Matsui et al., "ReRAM resistance design of LRS and HRS...," IEICE Trans. Fundamentals, 2026**
Derives the book's HRS/LRS resistance targets (10⁵Ω / 10⁹Ω). Verified precisely: the paper gives 10⁵Ω as its direct recommendation for *digital* memory, but only pairs a 10⁹Ω HRS with its *analog computation-in-memory* design point - it never gives a companion HRS for the digital case. The book is transparent about this mixed provenance, and a dedicated NVSim sensitivity sweep (Appendix A) shows the exact HRS value doesn't actually matter for any headline finding.

**[9] Jo et al. (Crossbar Inc.), "3D-stackable crossbar resistive memory...FAST selector," IEDM 2014**
Real industrial evidence (not just academic) that selector-based crossbar arrays scale to real multi-megabit capacities and support 3D stacking - Crossbar Inc.'s own press materials confirm the exact 4Mb array claimed in the book.

**[13] Le et al., "Resistive RAM With Multiple Bits Per Cell: 3 Bits Per Cell," IEEE TED, 2019**
First array-level (not just single-cell) demonstration of 3-bit-per-cell ReRAM, using 7,746 real cells. Cited purely to establish that multi-bit-per-cell ReRAM has real, measured precedent in the literature.

**[14] Wong et al., "Metal-Oxide RRAM," Proc. IEEE, 2012**
The single most-cited comprehensive RRAM review paper. Correctly sourced for: endurance-range variability, 10×10nm HfOx switching demonstrations, and device-to-device variability as RRAM's chief scaling barrier (all near-verbatim matches to the book's phrasing). The "20F²" cell-area number is *not* stated in this paper - only the qualitative "transistor-limited scaling" reasoning is; treat 20F² as a rule-of-thumb, not a number quoted from Wong et al.

**[20] Yang et al., "A 14nm-FinFET 1Mb Embedded 1T1R RRAM with 0.022µm² Cell Size," ISSCC 2021**
A real, commercial-grade 14nm 1T1R macro. Its actual cell size (0.022 µm² ≈ 112F² at that node) is used as a reality check showing the book's 20F² assumption is generous/conservative for 1T1R *relative to planar/FinFET logic-transistor integration* - see [33] for the counter-case where it isn't generous at all.

**[33] Fackenthal et al., "A 16Gb ReRAM with 200MB/s Write and 1GB/s Read in 27nm Technology," ISSCC 2014**
Verified real: DOI 10.1109/ISSCC.2014.6757460, confirmed via three independent sources. The commercial Micron/Sony 16Gb ReRAM chip - uses a DRAM-process **buried recessed-channel access transistor** (not a planar/FinFET logic transistor) to hit a **6F² 1T1R cell**, i.e. parity with DRAM's own 6F². Added as the counterpoint to [20]: it shows 1T1R density is architecture-dependent, not that 20F² is wrong. Two caveats keep it from being a substitute data point for this book's own 1T1R track: (1) it's a Cu-filament CBRAM cell, not the HfOx/TaOx oxide-RRAM family this book simulates; (2) NVSim as configured here (`configs/reram_22nm_1t1r_slc.cell`) only supports width-driven CMOS or diode access devices - no recessed-channel model - so no simulated numbers for this architecture are claimed anywhere in the book. Discussed in Technical_Report.typ Appendix A (Bit-Cell Area) and Section 4.2 (future work).

---

## The EMBER Papers

**[6] Upton et al., "EMBER...RRAM Macro in 40nm CMOS," ESSCIRC 2023**
The original conference announcement of EMBER, a Stanford/TSMC multi-bit-per-cell RRAM chip. Its Table I is the source for the read-energy multiplier: 1.0/1.1 pJ/bit at 1/2 bits-per-cell.

**[31] Levy et al., "EMBER: Efficient Multiple-Bits-Per-Cell...," IEEE JSSC 2024**
The full journal follow-up to [6], same team, with room for data the conference paper's page limit cut. Its Section V (Abstract and V.A/V.B) is the source for the read-latency, write-latency, and write-energy multipliers: read bandwidth 2.4/1.6 Gbps at 1/2 bits/cell (→ 1.5x read latency), write-verify bandwidth 12.4/3.8 Mbps (→ 3.263x write latency), and write-verify energy 0.40/1.2 nJ/bit (→ 3.0x write energy).

---

## DDR5 / DRAM Baseline Sources

**[5] IRDS, "More Moore," 2024**
IEEE's official semiconductor industry roadmap. Its DRAM section states planar capacitor scaling is nearing its practical limit and the industry must pivot to 3D-stacked cells. The book's "no remaining capacitor runway" phrasing is a fair paraphrase, not a verbatim quote.

**[10] JEDEC JESD79-5D, "DDR5 SDRAM Standard," 2025**
The authoritative DDR5 spec. Genuinely paywalled (confirmed via direct 403 on JEDEC's own site) - the book honestly discloses it couldn't be consulted directly and used a public vendor decoder as a substitute for the specific timing numbers. This disclosure is accurate, not a cover story.

**[24] TechInsights, "Advanced TSMC 22ULL Embedded RRAM Chip Unveiled"**
Confirms TSMC's 22nm eRRAM is real and commercially shipping (in Nordic Semiconductor's nRF54L chips). One soft spot: the article itself gives no capacity numbers, so "megabyte-scale" (revised down from an overstated "multi-megabyte") is the accurate framing - the real chip is ~1.5MB.

**[29] Micron, "16Gb DDR5 SDRAM Addendum"**
Micron's manufacturer datasheet giving guaranteed maximum IDD/IPP current specs by speed grade - one half of the book's two-vendor power-calibration band.

**[30] SK hynix, "16Gb DDR5 SDRAM" datasheet**
SK hynix's equivalent datasheet - the other half of the two-vendor band, and the source of this book's headline (conservative-floor) DDR5 power numbers.

---

## Miscellaneous (PCM baseline, endurance, workload profiling)

**[8] Xue et al., "22nm 4Mb ReRAM Computing-in-Memory Macro," ISSCC 2021**
Real, fabricated, working 22nm ReRAM silicon - direct evidence the book's chosen process node isn't hypothetical.

**[11] Lee, Ipek, Mutlu, Burger, "Architecting PCM as a Scalable DRAM Alternative," ISCA 2009**
The seminal PCM architecture paper (Persistent Impact Prize winner). Provides the book's PCM baseline model, its 400 MHz clock reference point, and precedent that smart write-buffering can offset a new memory technology's write weaknesses.

**[15] Lanza et al., "Standards for the Characterization of Endurance in Resistive Switching Devices," ACS Nano, 2021**
A field-standards paper arguing most published RRAM endurance numbers are measured from too few devices to trust. Justifies the book's choice of conservative endurance targets.

**[21] Malladi et al., "Towards Energy-Proportional Datacenter Memory with Mobile DRAM," ISCA 2012**
Real Microsoft server profiling data (Bing, Cosmos): 67-97% CPU utilization but only 2-6% memory bandwidth utilization. The book's "under 6%" web-search figure is an exact, verified quote (an earlier draft's "3%" was the wrong number - now correctly fixed).

**[32] Izraelevitz et al., "Basic Performance Measurements of the Intel Optane DC PMM," arXiv, 2019**
Confirms Optane's real DDR-T interface: electrically DDR4-compatible but running a different, latency-tolerant protocol. Used as industry precedent that even a major NVM product didn't try to match the newest DRAM PHY generation.

## Related Work (Section 1.3 - academic prior art)

**[36] B. C. Lee, E. Ipek, O. Mutlu, D. Burger, "Architecting Phase Change Memory as a Scalable DRAM Alternative," ISCA 2009**
One of the three founding ISCA 2009 NVM-main-memory papers. Narrows PCM's raw 1.6x delay / 2.2x energy deficit vs DRAM to within 1.2x / 1.0x via row-buffer reorganization and partial writes. Cited in §1.3 as the origin of the field's template (hide the write penalty, level the wear, buy density). Verified: pp. 2-13, DOI 10.1145/1555754.1555758.

**[37] M. K. Qureshi, V. Srinivasan, J. A. Rivers, "Scalable High Performance Main Memory System Using Phase-Change Memory Technology," ISCA 2009**
The hybrid-memory founding paper: large PCM store fronted by a small DRAM buffer (~3% of PCM capacity) with lazy write, line-level writeback, and fine-grained wear leveling. Cited in §1.3. Verified: pp. 24-33, DOI 10.1145/1555754.1555760.

**[38] P. Zhou, B. Zhao, J. Yang, Y. Zhang, "A Durable and Energy Efficient Main Memory Using Phase Change Memory Technology," ISCA 2009**
The durability-focused member of the ISCA 2009 trio: redundant-bit-write removal, row shifting, and segment-swapping wear leveling extend projected PCM lifetime to 13-22 years. Cited in §1.3. Verified: pp. 14-23, DOI 10.1145/1555754.1555759.

**[39] C. Xu et al., "Overcoming the Challenges of Crossbar Resistive Memory Architectures," HPCA 2015**
The closest prior work to this whole book: crossbar ReRAM as main memory, modeling circuit-level IR-drop/sneak-current-induced data-dependent RESET latency, recovering to within ~10% of an ideal DRAM-only system via split-phase RESET and compression-based encoding. §1.3 explicitly contrasts its circuit-level write timing with this book's calibrated array-level abstraction - complementary levels of analysis. Verified: pp. 476-488, DOI 10.1109/HPCA.2015.7056056.

**[40] E. Kültürsay, M. Kandemir, A. Sivasubramaniam, O. Mutlu, "Evaluating STT-RAM as an Energy-Efficient Main Memory Alternative," ISPASS 2013**
The parallel evaluation for the competing NVM: unmodified STT-RAM main memory is not competitive with DRAM, but partial writes + row-buffer bypass make it performance-comparable at ~60% lower memory energy. Cited in §1.3. Verified: pp. 256-267, DOI 10.1109/ISPASS.2013.6557176.

*(Note: §1.3 also cites the pre-existing [23] (Optane business exit) and [32] (Optane DC PMM measurements) - [32] now does double duty as the field's only real-hardware datapoint.)*

**[41] Y. Choi et al., "A 20nm 1.8V 8Gb PRAM with 40MB/s Program Bandwidth," ISSCC 2012**
Added 2026-09-01 to close a citation gap found during meeting prep: the book's PCM baseline (§2.3) is named for Lee et al. [11]'s architectural framing, but PCM was never run through this project's own NVSim pipeline - its actual timing/energy numbers are inherited unmodified from NVMain's bundled `pcm_microsoft_2009.config`, whose own header comment attributes those specific numbers to this Samsung ISSCC 2012 PRAM paper, not to Lee et al. [11] is the "why PCM as a DRAM alternative" citation; [41] is the "where these specific numbers came from" citation - different questions, both now answered. Verified via web search (IEEE Xplore, pp. 46-48); not independently re-derived or checked against the paper's own tables.

**[42] D. Kau et al., "A Stackable Cross Point Phase Change Memory," IEDM 2009**
Added 2026-09-05 (Shahar-notes items 1, 3&9): Intel/Numonyx's own device paper confirming that the shipped PCM product line (3D XPoint/Optane) is a selector-gated 1S1R cross-point design - an Ovonic Threshold Switch in series with the phase-change element, no access transistor. Cited in §2.3 to separate that real architecture from the book's PCM baseline, which specifies no access device at all. pp. 617-620, DOI 10.1109/IEDM.2009.5424263.

**[43] International Technology Roadmap for Semiconductors, 2011 Edition, PIDS chapter**
Added 2026-09-05 (Shahar-notes item 6): the 22nm Low Operating Power logic subthreshold-leakage design target (5 nA/µm). It was added as one of two independent sources for the transistor side of a large transistor-versus-selector leakage separation that the September revision has since **withdrawn**: NVSim assigns memristor cells zero leakage and charges chip leakage entirely to peripheral circuitry, so that separation was an artifact of two different array organizations and was never computed from [43] at all. Now cited in Appendix A under "Array Organization (and the withdrawal of the leakage-gap figure)", as a correct external statement about transistor leakage that the simulator does not use; the appendix entry it was originally cited in ("Access-Device Leakage Model") no longer exists. A roadmap target, not a measurement - [44] supplies the measured counterpart.

**[44] C. Auth et al., "A 22nm High Performance and Low-Power CMOS Technology Featuring Fully-Depleted Tri-Gate Transistors, Self-Aligned Contacts and High Density MIM Capacitors," VLSI Technology 2012**
Added 2026-09-05 (Shahar-notes item 6): Intel's measured off-state leakage on fabricated 22nm FinFET silicon, 5-20 nA/µm for the mid-power variant. [43]'s 5 nA/µm LOP target sits inside this measured band. As with [43], the leakage separation this pair was added to corroborate has been **withdrawn** in the September revision, and NVSim never used either figure: chip leakage in NVSim is peripheral circuitry and scales with mat count. Cited in Appendix A, "Array Organization (and the withdrawal of the leakage-gap figure)", as context for the open physical question of what an unselected 1T1R access transistor actually leaks in a real array, which NVSim does not model. pp. 131-132.

**[45] Y. Y. Chen et al., "Balancing SET/RESET Pulse for >10^10 Endurance in HfO2/Hf 1T1R Bipolar RRAM," IEEE Trans. Electron Devices, 2012**
Added 2026-09-13 (Shahar-notes item 8): a real, peer-reviewed >10^10-cycle demonstration on a 40 nm HfO2/Hf 1T1R cell - the kind of figure behind a recalled "~10^9" endurance rating. Cited in §3.1.4 as the high end of the literature, next to [15]'s caution that such single-device, sparsely sampled claims overestimate lifetime. Also appears in [15]'s own bibliography. vol. 59, no. 12, pp. 3243-3249, DOI 10.1109/TED.2012.2218607.

**[46] M. Hellenbrand, I. Teck, J. L. MacManus-Driscoll, "Progress of emerging non-volatile memory technologies in industry," MRS Communications, 2024**
Added 2026-09-13 (Shahar-notes item 8): a company-by-company industry survey showing shipped or qualified filamentary RRAM parts (Panasonic, Nuvoton, Weebit Nano, Fujitsu, Crossbar, IntrinSic) rated at 10^4-10^7 cycles. Cited in §3.1.4 to show the book's 10^7 SLC rating sits at the top of production reality. Its 10^12-10^15 figures are FRAM/MRAM, not RRAM - never quote them as RRAM endurance. vol. 14, pp. 1099-1112, DOI 10.1557/s43579-024-00660-2.

---

*This guide reflects the current state of `Technical_Report.typ`.*

---

## Added in the 2026-09 revision (see Technical_Report.typ Appendix D)

**[47] Y. Chen, "ReRAM: History, Status, and Future," IEEE TED 67(4), 2020**
An invited review. It is the book's new endurance-rating basis: it states 10^6 cycles as the typical spec for storage-class memory and 10^4 as the typical lower limit for embedded 1T1R. It replaces [14] for this purpose, because [14] gives no SLC or MLC rating at all - the single most consequential citation correction of the revision.

**[48] T.-y. Liu et al., "A 130.7-mm2 2-Layer 32-Gb ReRAM Memory Device in 24-nm Technology," IEEE JSSC 49(1), 2014**
SanDisk/Toshiba's shipped 32 Gb cross-point: the book's primary 1S1R ground truth. Two uses: its 2K-bitline x 4K-wordline block anchors the 2048-cell subarray side, and its Table II read/write timings (40 / 230 us) generate the 1S1R SILICON sensitivity configuration.

**[49] J. Zahurak et al., "Process Integration of a 27nm, 16Gb Cu ReRAM," IEDM 2014**
Micron/Sony's 16 Gb 1T1R part: the primary 1T1R ground truth, with a buried recessed-channel access transistor at 6F2. Its Table 1 read/write timings (2.3 / 11.7 us) generate the 1T1R SILICON sensitivity configuration. Note it is the same device family as [33].

**[50] C.-C. Chou et al., "A 22nm 96Kx144 RRAM Macro...," VLSI 2020**
TSMC's 22nm macro, the only primary 22nm 1T1R organization located (768 cells per bitline, 64 bitlines per sense amp). Cited in the book for its qualification endurance, 10K SET+RESET cycles, which is the array-level floor beneath the 10^6 planning value.

**[51] J. Zhou, K.-H. Kim, W. Lu, "Crossbar RRAM Arrays: Selector Device Requirements During Read Operation," IEEE TED 61(5), 2014**
The read model behind the book's analytic selector layer. The paper publishes no closed-form equation (it runs HSPICE), so the layer implements a reduced network solve validated against 13 points of its Fig. 3(b) and the array power of its Fig. 8(a). Its Table I also supplies the OTS nonlinearity bound.

**[52] M. K. Qureshi et al., "Enhancing Lifetime and Security of PCM-Based Main Memory with Start-Gap Wear Leveling," MICRO 2009**
The wear-leveling scheme implemented faithfully in NVMain for this revision (one gap line, rotation every 100 writes). The book's finding is that its reported 97%-of-ideal result does not transfer to the sparse footprints these traces produce, because the hot line fails before the gap rotates once.

**[53] J. Yang, J. Kim, M. Hoseinzadeh, J. Izraelevitz, S. Swanson, "An Empirical Guide to the Behavior and Use of Scalable Persistent Memory," USENIX FAST 2020**
The other real-Optane measurement paper beside [32], and the one that resolves [32]'s internal inconsistency over 81 vs 101 ns DRAM latency. Cited for the DDR4-2666 electrical interface precedent and in the Optane future-work item.

**[54] Intel Corporation, "Intel Optane Persistent Memory 200 Series Brief"**
The product brief supplying the only published endurance (PBW by access size and mix), bandwidth envelope and maximum TDP for a shipped NVM DIMM. Cited only for the scoped Optane reference row in Section 4.2; the brief publishes no media timing, idle power or energy per operation, which is why no NVMain configuration in this book is called Optane.

---

## Added in the September 2026 short-book revision (Section 3.4 and the bit-errors subsection of 3.1.2)

### MLC write-iteration characterization ([55]-[59]), cited in 3.1.1's bounding-run and Appendix A's smart-write discussion

**[55] Program-and-verify pulse-count characterization of MLC 1T1R RRAM, arXiv:2108.07879**
Average 49 pulses per level move, median 36 - the measured cost of an iterative program-and-verify MLC write, cited as the "how bad could the write iteration really be" upper end.

**[56] Self-terminating single-pulse MLC RRAM write technique, DATE 2022 (ACM DL 10.5555/3539845.3540141)**
The counterpoint to [55]: a single-pulse, non-iterative MLC write scheme, showing the iterative multiplier this book uses is not the only published approach and may overstate the real write cost.

**[57] Program-and-verify MLC PCM characterization, PMC6680789**
More than 70 program-and-verify iterations for a 9.7 us total write, under 1.6 us with the verify step skipped - the same iterative-write question as [55]/[56], for PCM rather than ReRAM.

**[58] Kawahara et al., "An 8Mb multi-layered cross-point ReRAM macro with 443MB/s write throughput," ISSCC 2012**
Source of the 17.2 ns write-cycle figure quoted in Section 3.1.1. Flagged in its own reference entry: the figure is taken from the published abstract only, the full text was requested and has not been read.

**[59] Kim et al. (SK hynix), "High-performance, cost-effective 2z nm two-deck cross-point memory...for 128 Gb SCM," IEDM 2018**
Source of array-level set/read timing figures quoted secondhand in Section 3.1.1. Flagged in its own reference entry: the full text was requested and has not been read.

### Bit errors, ECC and reliability ([60]-[83]), cited in the "Bit errors and error correction" subsection of 3.1.2

**[60] Channel-model bit error rates for a 1S1R cross-point array, arXiv:1912.02963**
The core source behind the book's BER answer: read BER from 4.29e-4 (best-positioned cell) to worse, write BER 3.35e-4 to 1.75e-2, for a 1024x1024 array at 10 ohm per junction with an ideal selector. This is the "channel model, not a measured device" the book's finding rests on - no measured 1S1R RBER exists in the literature it could find.

**[61] BCH coding over 128- and 256-bit blocks applied to [60]'s channel model, arXiv:2104.14011**
The coding layer built directly on [60]'s raw rates, with location-dependent interleaving.

**[62] Raw bit error rate of 1T1R HfO2 RRAM arrays under cycling (incl. a 2T2R variant), arXiv:1902.02528**
A measured 1T1R cycling BER data point, distinct from [60]'s 1S1R channel model.

**[63] Weebit Nano, smart-write algorithm technical resource**
The source of the "1T1R macros below 1e-7 with smart write" fact: a 128 kb 1T1R macro with a smart-write scheme reports under 1e-7 after 1e6 cycles at a 28.1 dB read margin.

**[64] Error-rate analysis of embedded RRAM, ICCAD 2023**
Raw BER about 1e-6, corrected to an uncorrectable rate of 2e-15 by a 2-bit-per-128-bit code - an embedded-RRAM (not main-memory-array) data point for the same ECC-overhead question.

**[65] Endurance of TSMC 28 nm embedded RRAM under 2-bit and 3-bit error correction, IEEE Xplore 9830374**
500,000 cycles at 2-bit correction, 1,000,000 at 3-bit - ties ECC strength directly to endurance rating for embedded RRAM.

**[66] Reliability of a 1S1R selector stacked with STT-MRAM, IEDM 2023**
1e-9 per-read disturb rate, 1e9 read-disturb-free cycles - a selector-reliability data point, not itself an array BER.

**[67] IBM Research, 3D XPT/SOM reliability strategies, IMW 2025**
Cell failure rate 9% falling to 0.02% after read-endurance optimization - shows the scale of improvement achievable engineering effort buys, not a number this book adopts directly.

**[68] Alfaro Robayo et al. (CEA-Leti), OxRAM-plus-OTS 1S1R reliability, IEDM 2019**
Five decades of selectivity, more than 1e6 program cycles, 1e8 read cycles, 1e9 read-disturb-free cycles - another 1S1R selector reliability data point.

**[69] Subthreshold-read reliability of OTS phase-change cross-point cells, ScienceDirect S0167931724000807**
1e12 disturb-free reads under subthreshold read bias.

**[70] Read-disturb model for 28 nm embedded RRAM, IRPS 2020**
Per-bit read-disturb rate below about 1e-18 - the most optimistic read-disturb figure in the reliability group.

**[71] Review of threshold-voltage drift in ovonic threshold switches, J. Semiconductors**
Under 40 mV per decade in typical material stacks - an OTS-selector aging figure.

**[72] Saturation of OTS threshold-voltage drift near 1e3 seconds, arXiv:2102.07264**
Shows the drift characterized in [71] saturates rather than growing unbounded.

**[73] imec, "The promise of OTS-only memories for next-gen compute system architectures"**
Half-bias nonlinearity in the low thousands, up to about 1e4 - an industrial-lab selector-quality figure, cited alongside the book's own selector-layer analytic bound (Section 3.1.2, "every 1S1R number in this book is conditional on a selector better than today's production OTS").

**[74] Zhang, Sridharan, and Jian, chipkill-correct for persistent memory, MICRO 2018 (via ar5iv:2309.00304)**
The single most load-bearing reference in this group: the book's design-point BER answer is "2e-4 with BCH(2312,2048,22)," and both numbers come directly from here - the 2e-4 raw design point and the BCH(2312,2048,22) code at about 27% coding overhead.

**[75] ArchShield, DRAM architecture for high bit-error rates (via ar5iv:1704.03991)**
DRAM on-die SECDED tolerates about 1e-6 raw - the comparison point the book uses to show how much worse ReRAM's raw rate is than DRAM's.

**[76] Gugnani et al., Proc. VLDB Endowment 14, 2021**
Documents Intel Optane's real, shipped 256-byte "XPLine" error-correction block - the one instance of a shipped NVM product's own ECC granularity in this reference group.

**[77] Intel Optane SSD 905P series product specifications**
Uncorrectable bit error rate under 1 sector per 1e17 bits - a shipped-product UBER figure, several orders of magnitude better than any raw ReRAM rate in this group, illustrating how much correction a real product applies.

**[78] Schechter et al., "Use ECP, Not ECC, for Hard Failures in Resistive Memories," ISCA 2010**
Argues resistive-memory hard failures need error-correcting pointers (ECP), not ECC, since ECC is built for soft (transient) errors. Cited to keep the book's three-category framing (hard failures, soft/read-disturb errors, sneak-path/array-level effects) honest about which correction scheme answers which category.

**[79] Yoon et al., "FREE-p: Protecting Non-Volatile Memory against Both Hard and Soft Errors," HPCA 2011**
A combined hard-and-soft-error protection scheme for NVM, cited alongside [78] as the other half of the hard-versus-soft error-correction literature.

**[80] Read-margin analysis of 1R against 1S1R crossbar arrays, arXiv:2407.10466**
Establishes the 10% minimum read-margin criterion used throughout the book's selector-layer analysis (also cited, under its own [48], by `Project_Book.typ` - same source, independent numbering in the two books).

**[81] Flocke and Noll, "Fundamental analysis of resistive nano-crossbars," ESSCIRC 2007**
Flagged in its own reference entry: consulted only through its bibliographic record, the full proceedings text was requested and has not been read.

**[82] A. Chen, crossbar-array model resolving line resistance and nonlinear device characteristics, IEEE TED 2013**
Identifies line resistance, not the selector alone, as the binding constraint on read margin in a large crossbar - a caveat on how far the book's selector-only analytic model can be trusted at scale.

**[83] "Effect of threshold switching selectors on one-selector one-resistor crossbar arrays," ResearchGate 351467888**
A 10% read margin needs a half-bias nonlinearity around 8,000 and an on/off window of 5 - a second, independent source for the selector-quality bar the book's own analytic layer is checked against.

### Far memory, CXL and Optane ([84]-[100]), cited in Section 3.4 (Near and Far Memory)

**[84] Measured idle latency of local and remote-socket DDR5 and of CXL-attached DRAM devices, arXiv:2409.14317**
A primary measured-latency source behind the far-memory window the book quotes (device-level idle latencies, local versus remote-socket versus CXL-attached).

**[85] "Pond": CXL-based memory pooling for cloud platforms (Microsoft Azure), arXiv:2203.00241**
Local DDR5 platform baselines, pooling latency overheads and a workload latency-acceptability study - the production-deployment half of the far-memory evidence.

**[86] Sun et al., "Demystifying CXL Memory with Genuine CXL-Ready Systems and Devices," arXiv:2303.15375**
Measurements from real, shipped CXL hardware rather than simulation - corroborates [84]/[85] on real silicon.

**[87] Compute Express Link Consortium, "About CXL"**
The protocol-level reference (CXL.io, CXL.cache, CXL.mem; Type 3 memory devices) - what CXL actually is, cited for definitional grounding.

**[88] Linux kernel documentation, "NUMA performance"**
ACPI HMAT latency and bandwidth attributes exposed per initiator-target pair - how the OS would actually see a far-memory device's advertised performance.

**[89] Linux kernel documentation, sysctl reference**
`numa_balancing` mode 2 and its page-promotion rate limit - the kernel mechanism that would migrate hot pages off a far-memory device.

**[90] LWN.net, "Memory tiering"**
Abstract distance of 512, demotion disabled by default - further detail on how the Linux tiering machinery [88]/[89] actually behaves out of the box.

**[91] Meta Platforms, Transparent Page Placement for CXL-enabled tiered memory, arXiv:2206.02878**
CXL adds about 50 to 100 ns over local DRAM, FPGA-based cards about 250 ns higher - the other primary source (with [84]) behind the book's quoted far-memory latency window; a production-scale (Meta) rather than benchmark-scale study.

**[92] Micron Technology, CXL 2.0 memory expansion module portfolio launch, Aug. 2023**
CZ120, x8, up to 36 GB/s - a real, shipped CXL memory-expansion product, cited as evidence the far-memory category is commercially real, not hypothetical.

**[93] Intel Corporation, 4th Gen Intel Xeon Scalable processor overview**
Eight DDR5-4800 channels per socket - the near-memory (local DDR5) channel-count baseline the far-memory numbers are compared against.

**[94] Izraelevitz et al., performance measurements of the Intel Optane DC PMM, arXiv:1903.05714**
305 ns idle random read, 169 ns sequential read, 6.6/2.3 GB/s read/write per module - real, measured Optane numbers (same paper as [32] in the pre-revision numbering) used as the shipped-precedent data point in 3.4.4.

**[95] Intel Corporation, 2nd-gen Intel Xeon Scalable processor family technical overview**
Optane PMem Memory Mode and App Direct mode; 64-byte byte-addressable lines - how the one shipped near/far-memory-adjacent precedent (Optane) was actually exposed to software.

**[96] Intel Corporation, discontinuation of Intel Optane persistent memory 300 series, Jan. 2023**
The formal end-of-product-life notice for Optane PMem.

**[97] The Register, report on Intel's Optane wind-down and inventory write-off, Jul. 2022**
Trade-press corroboration and additional detail (financial write-off) on the same exit covered by [96].

**[98] Google Research, software-defined far memory in warehouse-scale computers**
Single-digit microsecond tolerance for far memory in a real hyperscale fleet - the production-workload latency-tolerance bar the book's far-memory verdict is checked against.

**[99] Astera Labs, CM5162 Leo smart memory controller product page**
CXL 1.1/2.0, x16 at 32 GT/s, two DDR5 channels, up to 2 TB; no published latency figure - a current commercial CXL controller product, cited to show the category is actively shipping while also flagging that vendors do not publish the one number (latency) this book's far-memory discussion needs most.

**[100] Intel Corporation and Micron Technology, 3D XPoint technology announcement, Jul. 2015**
The original 3D XPoint (later marketed as Optane) announcement - historical anchor for when the one shipped 1S1R-adjacent main-memory-class NVM product was introduced.
