# Reference Guide — MBMM Project Book

A quick-reference summary of all 32 sources cited in `Project_Book.typ`. Each entry: what it is, and the one or two things you need to know about *why* it's cited here. Compiled from an independent verification pass (Aug 2026) that re-checked every citation against its actual source (local PDF or live web fetch), not just trusted the earlier drafts.

The book's MLC penalty multipliers are: **1.5x read latency, 3.263x write latency, 1.1x read energy, 3.0x write energy** (2 bits/cell vs. 1 bit/cell), all sourced from the EMBER macro's two publications, [6] and [31] below.

---

## Market / Industry Context

**[1] Ahmad, "NAND Flash's Reversal of Fortune Amid the AI Boom," EE Times, 2026**
A NAND-market recovery story; cited here only for a secondary point it makes about Samsung/SK Hynix reallocating fab capacity from DRAM to HBM. Supporting/context citation, not the article's main topic — worth knowing when you re-read the abstract's "DRAM-to-HBM reallocation" claim.

**[2] Fleischer, "How AI Broke the Memory Market," Octopart Pulse, 2026**
The book's more central source for the AI-driven memory shortage premise. Reports HBM consuming ~3x the wafer capacity of standard DDR5 and vendors reallocating up to 40% of advanced capacity to AI memory. Verified via search-snippet corroboration only (direct fetch was blocked) — slightly lower confidence than most other refs, but consistent and specific.

**[16] "Data Center Hardware Refresh Cutback by Microsoft," Data Center Knowledge, 2022**
Cited for exactly one statistic: enterprise servers now average 5.4 years of useful life, trending toward 6-7 years. This sets the endurance/lifetime bar the book's ReRAM configs are judged against.

**[17] TrendForce, "Micron Races Ahead in 10nm-Class DRAM with 1γ DDR5...", 2025**
Confirms Micron's newest DDR5 process (1-gamma) is a 10nm-class node. Reused repeatedly throughout the book's density/scaling argument as the anchor fact for "DDR5 is near the end of its scaling roadmap."

**[18] Choe, "Comparing DDR5 Memory From Micron, Samsung, SK Hynix," EE Times, 2022**
A real die-teardown comparison giving actual measured die sizes for 16Gb DDR5 from three vendors. The book's "35 mm²/GB" DDR5 baseline and "33.1–37.6 mm²/GB" band are directly, correctly derived from this article's numbers (verified to the decimal).

**[19] Shilov, "Samsung Puts 3D DRAM on the Roadmap," Tom's Hardware, 2024**
Confirms Samsung's public roadmap for vertical-channel-transistor DRAM (2nd half of this decade) and true 3D-stacked DRAM after that. Used as the counterpoint showing DRAM's escape route from capacitor scaling is real but still years out.

**[22] Gholami et al., "AI and Memory Wall," IEEE Micro, 2024**
The paper that coined "AI and Memory Wall" — peak hardware FLOPS have scaled 3.0x per two years vs. DRAM bandwidth's 1.6x. Both numbers quoted exactly correctly in the book.

**[23] "Intel Kills Optane Memory Business Entirely," Tom's Hardware, 2022**
Intel's 2022 exit from 3D XPoint/Optane, a $559M write-off. Used as precedent: a scaled selector-gated memory reached mass production and was killed by cost economics, not physics — relevant to the book's own 1S1R selector discussion.

**[25] "Neo Semiconductor's 3D X-DRAM...Passed Proof-of-Concept Validation," Tom's Hardware, 2026**
A very recent (Apr. 2026) challenger DRAM technology: sub-10ns access, >1 second retention (~15x longer refresh interval — the book correctly notes this is refresh *reduction*, not elimination; it's still charge-based DRAM).

---

## Core Simulation Tools & Benchmarks

**[3] Dong et al., "NVSim," IEEE TCAD, 2012**
The device-level circuit simulator (area/energy/timing) this project uses for hardware characterization. One soft spot: it's co-cited with [14] for a "~20F²" bit-cell area figure that neither paper actually states as a specific number — the wording has been softened to reflect this.

**[4] Poremba, Zhang, Xie, "NVMain 2.0," IEEE CAL, 2015**
The architectural (system-level) memory simulator paired with NVSim. NVSim answers "how good is one memory array"; NVMain answers "how does a full memory system with many arrays and ranks behave."

**[12] Samajdar et al., "SCALE-Sim," ISPASS 2020**
A cycle-accurate systolic-array DNN accelerator simulator, used purely as a trace generator — produces realistic AI-inference memory-access patterns (e.g., AlexNet layers) to stress-test the memory systems.

**[26] Binkert et al., "The gem5 Simulator," ACM SIGARCH CAN, 2011**
The well-known general-purpose CPU+memory architecture simulator used to run SPEC CPU2017 and capture memory traces.

**[27] McCalpin, "Memory Bandwidth and Machine Balance," TCCA Newsletter, 1995**
The origin paper of the STREAM benchmark — the standard synthetic test for *sustained* (not burst) memory bandwidth. Used as the book's pure-bandwidth baseline workload.

**[28] SPEC CPU2017 Benchmark Suite**
The industry-standard real-world compute benchmark suite. The book picks two sub-benchmarks as opposite ends of a spectrum: 602.gcc (irregular, branch-heavy, compute-bound) and 619.lbm (regular, bandwidth-heavy).

---

## ReRAM Device Physics (the load-bearing group)

**[7] Matsui et al., "ReRAM resistance design of LRS and HRS...," IEICE Trans. Fundamentals, 2026**
Derives the book's HRS/LRS resistance targets (10⁵Ω / 10⁹Ω). Verified precisely: the paper gives 10⁵Ω as its direct recommendation for *digital* memory, but only pairs a 10⁹Ω HRS with its *analog computation-in-memory* design point — it never gives a companion HRS for the digital case. The book is transparent about this mixed provenance, and a dedicated NVSim sensitivity sweep (Appendix A) shows the exact HRS value doesn't actually matter for any headline finding.

**[9] Jo et al. (Crossbar Inc.), "3D-stackable crossbar resistive memory...FAST selector," IEDM 2014**
Real industrial evidence (not just academic) that selector-based crossbar arrays scale to real multi-megabit capacities and support 3D stacking — Crossbar Inc.'s own press materials confirm the exact 4Mb array claimed in the book.

**[13] Le et al., "Resistive RAM With Multiple Bits Per Cell: 3 Bits Per Cell," IEEE TED, 2019**
First array-level (not just single-cell) demonstration of 3-bit-per-cell ReRAM, using 7,746 real cells. Cited purely to establish that multi-bit-per-cell ReRAM has real, measured precedent in the literature.

**[14] Wong et al., "Metal-Oxide RRAM," Proc. IEEE, 2012**
The single most-cited comprehensive RRAM review paper. Correctly sourced for: endurance-range variability, 10×10nm HfOx switching demonstrations, and device-to-device variability as RRAM's chief scaling barrier (all near-verbatim matches to the book's phrasing). The "20F²" cell-area number is *not* stated in this paper — only the qualitative "transistor-limited scaling" reasoning is; treat 20F² as a rule-of-thumb, not a number quoted from Wong et al.

**[20] Yang et al., "A 14nm-FinFET 1Mb Embedded 1T1R RRAM with 0.022µm² Cell Size," ISSCC 2021**
A real, commercial-grade 14nm 1T1R macro. Its actual cell size (0.022 µm² ≈ 112F² at that node) is used as a reality check showing the book's 20F² assumption is generous/conservative for 1T1R, not stacked in ReRAM's favor.

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
The authoritative DDR5 spec. Genuinely paywalled (confirmed via direct 403 on JEDEC's own site) — the book honestly discloses it couldn't be consulted directly and used a public vendor decoder as a substitute for the specific timing numbers. This disclosure is accurate, not a cover story.

**[24] TechInsights, "Advanced TSMC 22ULL Embedded RRAM Chip Unveiled"**
Confirms TSMC's 22nm eRRAM is real and commercially shipping (in Nordic Semiconductor's nRF54L chips). One soft spot: the article itself gives no capacity numbers, so "megabyte-scale" (revised down from an overstated "multi-megabyte") is the accurate framing — the real chip is ~1.5MB.

**[29] Micron, "16Gb DDR5 SDRAM Addendum"**
Micron's manufacturer datasheet giving guaranteed maximum IDD/IPP current specs by speed grade — one half of the book's two-vendor power-calibration band.

**[30] SK hynix, "16Gb DDR5 SDRAM" datasheet**
SK hynix's equivalent datasheet — the other half of the two-vendor band, and the source of this book's headline (conservative-floor) DDR5 power numbers.

---

## Miscellaneous (PCM baseline, endurance, workload profiling)

**[8] Xue et al., "22nm 4Mb ReRAM Computing-in-Memory Macro," ISSCC 2021**
Real, fabricated, working 22nm ReRAM silicon — direct evidence the book's chosen process node isn't hypothetical.

**[11] Lee, Ipek, Mutlu, Burger, "Architecting PCM as a Scalable DRAM Alternative," ISCA 2009**
The seminal PCM architecture paper (Persistent Impact Prize winner). Provides the book's PCM baseline model, its 400 MHz clock reference point, and precedent that smart write-buffering can offset a new memory technology's write weaknesses.

**[15] Lanza et al., "Standards for the Characterization of Endurance in Resistive Switching Devices," ACS Nano, 2021**
A field-standards paper arguing most published RRAM endurance numbers are measured from too few devices to trust. Justifies the book's choice of conservative endurance targets.

**[21] Malladi et al., "Towards Energy-Proportional Datacenter Memory with Mobile DRAM," ISCA 2012**
Real Microsoft server profiling data (Bing, Cosmos): 67-97% CPU utilization but only 2-6% memory bandwidth utilization. The book's "under 6%" web-search figure is an exact, verified quote (an earlier draft's "3%" was the wrong number — now correctly fixed).

**[32] Izraelevitz et al., "Basic Performance Measurements of the Intel Optane DC PMM," arXiv, 2019**
Confirms Optane's real DDR-T interface: electrically DDR4-compatible but running a different, latency-tolerant protocol. Used as industry precedent that even a major NVM product didn't try to match the newest DRAM PHY generation.

---

*This guide reflects the current state of `Project_Book.typ`.*
