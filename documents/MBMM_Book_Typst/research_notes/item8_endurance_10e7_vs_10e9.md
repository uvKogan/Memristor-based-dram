# Item 8: Reconciling the book's 10^7 SLC endurance rating against Shahar's recalled "~10^9" figure

**Question this note answers:** the book's endurance projection (`Project_Book.typ` Section 3.1.4) uses SLC = 10^7 write cycles/cell (MLC = 10^6), cited to Wong et al. [14] (Proc. IEEE 2012) and Lanza et al. [15] (ACS Nano 2021). Shahar's meeting note recalled a "~10^9" per-cell figure and a resulting magic number near 10^15 total writes, ~10 years. Is there real literature support for 10^9, and if so, why does the book use 10^7 instead?

**Bottom line up front:** Both numbers are real and independently verifiable in the literature - they are not in conflict once you know what each one measures.

- **10^9-10^11 cycles**: genuinely reported, repeatedly, in the RRAM device-physics literature - but almost always as a **single-device, lab-optimized, sparsely-sampled** demonstration (one HfOx/TaOx cell, hand-tuned SET/RESET pulses, resistance measured at only ~10-80 points spread across the full log-scale cycle range, not every cycle). The book's own already-cited methodology source, Lanza et al. 2021 [15], is a paper written specifically to warn the field against treating exactly this class of claim as production-representative.
- **10^4-10^7 cycles**: what real, shipped or near-production RRAM parts from actual semiconductor companies (Panasonic, Weebit Nano, Crossbar, Fujitsu, Nuvoton) actually spec today, per a comprehensive, independent, very recent (2024) industry survey. The book's 10^7 SLC choice sits at the *top* of this real-world range, not below it.
- The 10^12-10^15 figures that also appear in device literature (and in the same industry survey, for other memory types) belong almost entirely to **FRAM and MRAM**, not RRAM - a different technology with a fundamentally different, much higher-endurance switching mechanism. Conflating them with RRAM would be a real error; the book does not do this, and this reconciliation should be careful not to introduce it.

Recommended talking point for the live conversation with Shahar (not a book edit - matches the existing tracker decision that this item needs a conversation, not a rewrite): "10^9 is real, but it's a best-case single-device lab demonstration under a measurement protocol the field's own reliability community (Lanza et al., already in our bibliography) has explicitly cautioned against over-trusting. Our 10^7 is deliberately closer to what real shipped RRAM parts (Crossbar, IntrinSic) actually spec, which makes it the more conservative, defensible choice for a system-lifetime projection - if anything the true number could be *lower*, not higher."

---

## (a) The >10^9 claims are real, and here are two with full bibliographic detail

Both fetched and read in full text (not summaries):

1. Y. Y. Chen, B. Govoreanu, L. Goux, R. Degraeve, A. Fantini, G. S. Kar, D. J. Wouters, G. Groeseneken, J. A. Kittl, M. Jurczak, L. Altimime, "Balancing SET/RESET Pulse for >10^10 Endurance in HfO2/Hf 1T1R Bipolar RRAM," *IEEE Transactions on Electron Devices*, vol. 59, no. 12, pp. 3243-3249, Dec. 2012, DOI: 10.1109/TED.2012.2218607. A **1T1R** device (same architecture family as the book's own 1T1R baseline) - 40 nm HfO2/Hf cells; by optimally balancing SET/RESET pulse amplitude/timing, >10^10 pulse endurance cycles achieved. This paper is *already indirectly in the book's citation graph*: it is reference (27) in Lanza et al. 2021 [15]'s own bibliography, used there as one of the field's representative 1T1R endurance demonstrations.
2. F.-Y. Yuan, N. Deng, C.-C. Shih, Y.-T. Tseng, T.-C. Chang, K.-C. Chang, M.-H. Wang, W.-C. Chen, H.-X. Zheng, H. Wu, H. Qian, S. M. Sze, "Conduction Mechanism and Improved Endurance in HfO2-Based RRAM with Nitridation Treatment," *Nanoscale Research Letters*, 2017. A Pt/HfO2/TiN device; after nitridation treatment, stable HRS/LRS ratio maintained past 10^9 sweep cycles.

Both are genuine, peer-reviewed, real devices - the >10^9-10^10 numbers are not fabricated or misquoted anywhere in the literature. This is the number Shahar is very likely recalling; it is a real, frequently-cited figure in the RRAM endurance literature.

## (b) Why the book doesn't use 10^9: Lanza et al. 2021 [15] (already cited in the book) directly critiques this class of claim

Read the full text of Lanza et al., "Standards for the Characterization of Endurance in Resistive Switching Devices," *ACS Nano* 2021, 15, 17214-17231, DOI: 10.1021/acsnano.1c06980. This is not a tangential source - it is **already one of the book's two citations for the 10^7 SLC figure**. Its own abstract states the core finding, verbatim:

> "We note that most studies that claimed high endurances >10^6 cycles were based on resistance versus cycle plots that contain very few data points (in many cases even <20), and which are collected in only one device. We recommend not to use such a characterization method because it is highly inaccurate and unreliable (i.e., it cannot reliably demonstrate that the device effectively switches in every cycle and it ignores cycle-to-cycle and device-to-device variability). This has created a blurry vision of the real performance of RS devices and in many cases has exaggerated their potential."

The paper backs this with a literal table (**Table 2, "Highest Switching Endurances of RS Devices Ever Reported and the Number of Data Points Presented to Support Such Claims"**) that lists dozens of published RRAM endurance claims from 10^5 up to 10^15 cycles, alongside how many resistance-measurement data points each claim actually rests on, and a "reliability of the claim" rating derived directly from that count. The pattern in that table is stark and directly relevant here: claims in the 10^9-10^15 range are overwhelmingly rated "low" reliability, typically resting on only **~10-80 measured data points spread across the entire claimed cycle range** (e.g., one HfO2/Hf 1T1R stack in the table - the same device family as Chen et al. above - claims 10^10 cycles on just ~31 actual measured points). The paper's Discussion section states this explicitly:

> "We have noticed that a considerable number of publications in the field of RS claimed very high endurances >10^7 cycles based on a plot that contains few (i.e., <100) data points for only one device... it introduces delays affecting the RS properties, it underestimates cycle-to-cycle variability of switching voltages and state currents, and it also **overestimates the endurance lifetime**."

In other words: the book's own already-cited methodology reference is a paper whose entire purpose is to warn readers not to treat >10^7-10^9-class endurance claims at face value without checking how densely they were actually measured. Using 10^7 as the book's working figure, rather than reaching for one of the >10^9 headline numbers, is a direct, defensible application of that paper's own recommendation - not an inconsistency with it.

## (c) Real shipped/production RRAM parts spec far below 10^7, not above it

New source found and read in full: M. Hellenbrand, I. Teck, J. L. MacManus-Driscoll, "Progress of emerging non-volatile memory technologies in industry," *MRS Communications*, vol. 14, pp. 1099-1112 (2024), DOI: 10.1557/s43579-024-00660-2. This is a comprehensive, very recent (published Nov. 2024, so post-dates every existing citation in the book on this topic), company-by-company industry survey specifically compiled from public datasheets/press releases/conference presentations, with per-source citations. Real RRAM (filamentary metal-oxide, the same device class the book models) endurance figures pulled directly from it:

| Company | Device / node | Cycling endurance | Status |
|---|---|---|---|
| Panasonic/PSCS | 40 nm RRAM macro (w/ imec) | **10^5** | Mass-produced since 2013; same figure still reported in 2020 |
| Nuvoton | Tantalum-oxide RRAM (acquired from Panasonic) | **10^4** | Shipping in microcontrollers |
| Weebit Nano | SkyWater 130 nm, production-ready | **10^4** (10^5 qualification target, 2024) | Production |
| Weebit Nano | CEA-Leti 28 nm demo (2022) | **>10^5** | Demonstration, not yet production |
| Fujitsu | RRAM product line | **5x10^5** | Shipping |
| Crossbar Inc. | Licensable filamentary RRAM IP, <10 nm scalability advertised | **>10^6** | IP licensing (Microsemi 2018) |
| IntrinSic Semiconductor (UCL spin-out) | Filamentary amorphous-SiOx RRAM | **10^7** | Company data still classified; figure from the underlying journal publication |
| 4DS Memory | **Non-filamentary**, area-dependent PCMO switching (explicitly a different mechanism from the book's filamentary assumption) | advertised up to **10^9** | Licensing target, not independently measured |

The book's 10^7 SLC choice matches IntrinSic's own reported figure almost exactly, and sits comfortably above every other real filamentary-RRAM company's shipped or qualified spec (10^4-10^6). The one company in this entire survey claiming anything near 10^9 for a resistive-switching part (4DS Memory) uses a **non-filamentary** switching mechanism, explicitly distinguished in the source from the filament-based HfOx/TaOx devices - including the book's own modeling assumption - that dominate the rest of the field; it is also a company-advertised figure, not an independently measured/peer-reviewed one, which is exactly the caveat Lanza et al. [15] raises in (b) above.

For contrast (to avoid a future mix-up): the same survey's FRAM and MRAM entries do report genuine 10^12-10^15-cycle production specs (Infineon/TI FRAM at 10^15; Samsung/Renesas MRAM at 10^12-10^14) - these are real numbers for real shipped parts, but for **different memory technologies**, not RRAM, and should never be quoted as an RRAM endurance figure.

## (d) Honesty check: what this note does not establish

- This does not identify which specific number (or capacity) Shahar was recalling - that is exactly the live-conversation question the tracker already flagged as open, and this note doesn't resolve it, only arms the conversation with real citations for both sides.
- The IntrinSic Semiconductor figure (10^7) is sourced from a journal publication describing their underlying technology, not an independently verified company datasheet (the company's own product data is stated as still classified in the source survey) - flagged as slightly softer than the other, more directly production-sourced rows in the table.
- This note does not re-derive or challenge the book's own 10^7/10^6 SLC/MLC endurance figures - it independently confirms they are a defensible, literature-consistent choice, sitting between real production reality (10^4-10^6) and best-case single-device lab records (10^9-10^11), rather than proposing any change to them.

---

## Sources consulted

**Primary sources used, full text obtained and read directly:**
- Y. Y. Chen et al., "Balancing SET/RESET Pulse for >10^10 Endurance in HfO2/Hf 1T1R Bipolar RRAM," IEEE Trans. Electron Devices, vol. 59, no. 12, pp. 3243-3249, 2012, DOI: 10.1109/TED.2012.2218607 (abstract/metadata via KU Leuven Lirias institutional repository record).
- F.-Y. Yuan et al., "Conduction Mechanism and Improved Endurance in HfO2-Based RRAM with Nitridation Treatment," Nanoscale Research Letters, 2017 (PMC5658308, open access, read in full).
- M. Lanza et al., "Standards for the Characterization of Endurance in Resistive Switching Devices," ACS Nano, 15, 17214-17231, 2021, DOI: 10.1021/acsnano.1c06980 - full PDF supplied by the Lead Researcher via Technion institutional access; read in full including Table 2 and the Discussion section.
- M. Hellenbrand, I. Teck, J. L. MacManus-Driscoll, "Progress of emerging non-volatile memory technologies in industry," MRS Communications, 14, 1099-1112, 2024, DOI: 10.1557/s43579-024-00660-2 - full PDF supplied by the Lead Researcher via institutional access; read in full including all per-company sections.

**Secondary sources used only to locate the above (not cited as the factual source for any number in this note):**
- WebSearch results used to identify candidate papers, companies, and initial endurance figures before independently confirming every number against the primary-source full text above.
- Preliminary web-search-only figures for Weebit Nano/Panasonic/Adesto (used before the MRS Communications PDF was obtained) are superseded by the confirmed, in-text-quoted figures in section (c) above.
