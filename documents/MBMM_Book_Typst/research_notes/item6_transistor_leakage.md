# Item 6: Primary-source citation for the transistor side of the "47x leakage-class separation"

**Question this note answers:** The book's 47x leakage-class separation between 1T1R (transistor-gated) and 1S1R (selector-gated) 22nm ReRAM access devices is computed by NVSim's circuit-level model. The selector side of that ratio is already cited (Matsui et al., IEICE Trans. Fundamentals, 2026, HRS/LRS = 10^9/10^5 Ohm). The transistor side has no independent citation. Does a real, primary-source, 22nm-class (or closest available node) access-transistor off-state/subthreshold leakage figure exist that can close this gap?

**Bottom line up front:** Yes. Two independent, primary, peer-reviewed/industry-roadmap sources give a directly usable number, and they agree with each other:

- **ITRS 2011 (Process Integration, Devices and Structures chapter):** Low Operating Power (LOP) logic transistor off-state leakage, Isd,leak = **5 nA/um**, fixed as a design target. High-Performance (HP) logic transistor off-state leakage, Isd,leak = **100 nA/um**, fixed as a design target across all years of that roadmap edition.
- **Intel, Auth et al., 2012 VLSI Symposium (the actual 22nm foundry process paper):** measured Ioff ranges at the 22nm tri-gate node, Table I: HP = **20-100 nA/um**, MP (mid-power) = **5-20 nA/um**, SP (low/standby-power) = **1-5 nA/um**.

Both of these are real papers/roadmap documents I downloaded and read directly (full text extracted below), not summaries. Recommended citation for the book: the ITRS 2011 PIDS chapter (Table PIDS2/PIDS3) as the roadmap-level number, corroborated by Auth et al. 2012 as an actual fabricated-silicon measurement at the same node. Because Appendix A of the book states the project's NVSim run uses **22nm FinFET LOP**, the LOP figure (ITRS: 5 nA/um; Auth et al. "MP"/"SP" range: 1-20 nA/um) is the more directly relevant match, not the HP figure.

---

## (a) Does a genuine, independently-sourced 22nm transistor Ioff citation exist?

Yes, with two independent primary sources converging on the same order of magnitude. Below is the search trail through the four candidate families named in the task, in the order they were checked.

### 1. Predictive Technology Model (PTM), Zhao & Cao

- **Primary paper found and confirmed:** W. Zhao and Y. Cao, "New Generation of Predictive Technology Model for Sub-45 nm Early Design Exploration," *IEEE Transactions on Electron Devices*, vol. 53, no. 11, pp. 2816-2823, Nov. 2006.
- **Finding:** This paper's own bulk-CMOS PTM generation covers technology nodes from 130 nm down to **32 nm** only (Leff as low as 13 nm within that 32 nm generation). It does **not** reach 22 nm. This rules PTM's peer-reviewed 2006 paper out as a direct 22 nm source.
- **ptm.asu.edu:** confirmed **unreachable** (DNS resolution failure, `getaddrinfo ENOTFOUND ptm.asu.edu`) when fetched directly during this research. The site is effectively defunct, consistent with what the task briefing anticipated.
- **22 nm PTM SPICE model files do circulate**, but only as unpublished website downloads (originally from ptm.asu.edu, now only available via third-party mirrors, e.g. a BSIM4 model card at `CMU-SAFARI/CROW` on GitHub, path `SPICESim/PTM_transistors/HP_tox_scaled/22nm_HP.pm`). I downloaded and inspected this file directly. It is a raw BSIM4 transistor model card (threshold voltage, mobility, short-channel-effect parameters, etc.) - it does **not** publish an Ioff number as a stated parameter. Extracting an Ioff figure from it would require running a SPICE simulation (Vgs=0, Vds=Vdd sweep), which is out of scope for this task and was not done. **This file is therefore not used as a citation source** - flagged here only so the gap is documented honestly: the "PTM 22nm" files that circulate are a secondary/unpublished mirror of a dead website, not a citable number.
- **A later, more relevant peer-reviewed lead:** S. Sinha, G. Yeric, V. Chandra, B. Cline (ARM Inc.) and Y. Cao (ASU), "Exploring sub-20nm FinFET design with predictive technology models," *Proceedings of the 49th Annual Design Automation Conference (DAC '12)*, pp. 283-288, June 2012 (ACM DOI 10.1145/2228360.2228414). Per the paper's indexed abstract, this generates PTM-MG (multi-gate) FinFET model files for 5 technology nodes aligned to the 2011 ITRS roadmap, spanning 20 nm to 7 nm. This looks like the natural "PTM reaches 22/20nm, peer-reviewed" answer. **However, I was not able to retrieve the paper's full text** (ACM and IEEE Xplore both blocked automated fetch with HTTP 403; no open-access mirror was found in the time available). I am flagging this as an unverified lead, not a citation - do not cite specific Ioff numbers from it without reading the actual table.

**Conclusion on PTM:** not usable as the citation. The peer-reviewed PTM paper doesn't reach 22nm, and the 22nm-node files that do exist are unpublished, dead-website downloads that don't state an Ioff figure without further simulation.

### 2. ITRS leakage/Ioff tables - this is the source that worked

- **Document:** *International Technology Roadmap for Semiconductors: 2011 Edition - Process Integration, Devices, and Structures (PIDS)*. Retrieved as a full PDF (985,785 bytes, 41 pages) from `semiconductors.org` (the SIA's own archive of the ITRS reports); I extracted and read the full text directly.
- **Exact text (PIDS chapter, internal page 10, PDF page 14 of the file):**
  > "For the high-performance logic technology, as shown in Table PIDS2, the driver is the MOSFET intrinsic speed metric, 1/tau or I/CV... The subthreshold source/drain leakage current, Isd,leak, is fixed at a value of **100 nA/um for all years**..."
- **Exact text (PIDS chapter, internal page 11, PDF page 15 of the file):**
  > "For low-power chips, the important factor is the source/drain subthreshold leakage current, Isd,leak or off-current. For LOP logic (Table PIDS3), Isd,leak is set at **5 nA/um**, while it is **10 pA/um** for LSTP devices (Table PIDS4)."
- **Table references:** Table PIDS2 ("High-performance (HP) Logic Technology Requirements"), Table PIDS3 ("Low Operating Power (LOP) Technology Requirements"), Table PIDS4 ("Low Standby Power (LSTP) Technology Requirements") - tables themselves appear as embedded graphics on PDF page 16 (internal page 12) and were not text-extractable, but the numeric design targets they encode are stated explicitly in the body text quoted above, which is sufficient for citation purposes.
- **Node/year note:** ITRS's HP/LOP/LSTP Isd,leak figures are defined as fixed year-independent design targets within a given roadmap edition (that is explicitly what "fixed... for all years" means for HP), rather than a single-node measurement. The 2011 edition's near-term roadmap years (2011-2013) are the ones during which 22 nm-class logic was in production industry-wide, so treating these figures as "the ITRS 22nm-era design target" is standard usage in the literature and is how this note treats them.
- **Note on genre:** as the task briefing anticipated, ITRS is an industry-consortium roadmap, not an academic paper, but its own published numeric table is being cited directly here (not a summary of it), which satisfies "primary source" for this purpose.

**Conclusion on ITRS:** usable and used. This is the primary citation recommended for the book.

### 3. Foundry-published 22 nm leakage figures - corroborating primary source found

- **Paper found, downloaded, and read in full:** C. Auth et al. (Intel Corp., Logic Technology Development), "A 22nm High Performance and Low-Power CMOS Technology Featuring Fully-Depleted Tri-Gate Transistors, Self-Aligned Contacts and High Density MIM Capacitors," *2012 Symposium on VLSI Technology (VLSIT) Digest of Technical Papers*, pp. 131-132, June 2012.
- **Exact text and table (p. 131, "Transistor Performance & Reliability" section, Table I):**
  > "To support low power SoC integration with high performance microprocessors, three transistor types are offered. HP devices are targeted for high performance with leakage in the 20-100nA range, based on product need. MP and SP transistors offer lower leakage to enable SoC product power-performance optimization."
  >
  > Table I: TOX,E = 0.9 nm for all three types; LGATE = 30 nm (HP), 34 nm (MP), 34 nm (SP); **IOFF (nA/um): HP = 20-100, MP = 5-20, SP = 1-5.**
  >
  > (p. 131, Fig. 6 caption): "HP, MP and LP devices are benchmarked at 100nA, 10nA and 1nA Ioff respectively" - confirming the standard industry convention of quoting Idsat/Ieff at fixed Ioff reference points of 100 nA/um, 10 nA/um, and 1 nA/um.
- This is an actual fabricated-silicon (Intel 22 nm tri-gate, in volume manufacturing at time of publication) measurement, not a roadmap projection, and it lands squarely on the same order of magnitude as the ITRS figures above (100 nA/um HP ceiling in both; ITRS LOP's 5 nA/um sits inside Auth et al.'s MP range of 5-20 nA/um).

**Conclusion on foundry papers:** usable and used, as corroboration for the ITRS figure.

### 4. NVSim's own paper (Dong et al., TCAD 2012) - inconclusive, not independently confirmed

- I was unable to obtain the full text of X. Dong, C. Xu, Y. Xie, N. P. Jouppi, "NVSim: A Circuit-Level Performance, Energy, and Area Model for Emerging Nonvolatile Memory," *IEEE TCAD*, vol. 31, no. 7, pp. 994-1007, 2012. IEEE Xplore, ACM DL, and SpringerLink all blocked automated access (403 Forbidden or a bot-challenge page); a related PhD thesis (Penn State ETDA, likely X. Dong's) was also blocked (403).
- **Secondary-source indications only** (used here only to describe what a citation search turned up, not as a citation itself, per the task's own rules): multiple independent search-engine summaries of citing/related literature state that NVSim "uses device data from the ITRS report and the MASTAR tool to obtain the process parameters," and that NVSim covers process nodes from 180 nm down to 22 nm. This is consistent with (and would directly explain) why the ITRS figures found above are the right match for NVSim's internal 22 nm leakage model - but I could not verify this by reading NVSim's own paper text, so it should be treated as **plausible but unconfirmed**, not stated as fact in the book.
- A related, later tool by overlapping authors, NVSim-CAM (H. Li et al., ICCAD 2016 - PDF obtained and read directly, `miglopst.github.io/files/li_iccad2016.pdf`), explicitly states it is "based on PTM" (citing ptm.asu.edu) for its own device parameters, and separately references a 22 nm technology sense-margin limit (p. 5 of that PDF, Section 5.2). This confirms PTM *was* in active use by this research group for the 2016 follow-on tool, but does not by itself establish what the original 2012 NVSim used.

**Conclusion on NVSim's own paper:** the citation gap cannot be closed by NVSim's own paper text, because that text could not be accessed. This is an honest gap; do not claim NVSim explicitly cites ITRS without reading NVSim's own paper to confirm it.

---

## (b) The exact number, units, and citation to use

Recommended primary citation (two sources, use together):

1. International Technology Roadmap for Semiconductors, 2011 Edition, Process Integration, Devices, and Structures (PIDS) chapter, Semiconductor Industry Association, 2011: subthreshold source/drain leakage current (Isd,leak) design targets - High-Performance (HP) logic = **100 nA/um** (p. 10, discussion accompanying Table PIDS2), Low Operating Power (LOP) logic = **5 nA/um** (p. 11, discussion accompanying Table PIDS3), Low Standby Power (LSTP) logic = **10 pA/um** (p. 11, discussion accompanying Table PIDS4).
2. C. Auth et al., "A 22nm High Performance and Low-Power CMOS Technology Featuring Fully-Depleted Tri-Gate Transistors, Self-Aligned Contacts and High Density MIM Capacitors," 2012 Symposium on VLSI Technology Digest of Technical Papers, pp. 131-132, 2012: measured off-state leakage current (IOFF) at the 22nm node, Table I - HP = **20-100 nA/um**, MP = **5-20 nA/um**, SP = **1-5 nA/um**.

Since Appendix A of the book states the NVSim run used **22nm FinFET LOP**, the number most directly on-point is the **ITRS LOP figure of 5 nA/um**, falling inside Auth et al.'s independently measured MP band of 5-20 nA/um. If the book prefers a single round number for prose, "on the order of 5-100 nA/um depending on transistor class (LOP vs. HP), per ITRS 2011 and confirmed by Intel's fabricated 22nm process data (Auth et al. 2012)" is an accurate, defensible characterization.

---

## (c) Order-of-magnitude sanity check against the book's 47x leakage-class separation

This is a plausibility check only, not a proof, and it does not touch NVSim's C++ source.

Per Appendix A of the book (`Project_Book.typ`, "Appendix A: Simulation Parameters and Literature Grounding"), the 47x figure comes from NVSim-modeled *array-level* leakage power: 794.656 mW for the 1T1R (transistor-gated) array versus 16.907 mW for the selector-gated array (794.656 / 16.907 ~= 47.0), and the book itself states this separation "is driven entirely by the CMOS-transistor-vs-selector access-device model, not by HRS" (i.e., independent of the exact HRS value chosen).

A rough per-device comparison: at the HRS target of 10^9 Ohm and a sub-volt read/hold bias (order 0.5-1 V, typical of a 22nm-class array), a selector in its high-resistance (cutoff) state carries roughly Vhold/R_HRS ~= 0.5-1 nA per device (Ohm's law order-of-magnitude estimate, not a device physics claim). ITRS's LOP transistor Isd,leak of 5 nA/um (or Auth et al.'s MP/SP range of 1-20 nA/um) is in the same 1-10 nA scale per device/per-um-of-width. A transistor access device leaking a few nA versus a selector access device leaking a fraction of a nA is consistent with a separation factor in the tens (i.e., 47x), rather than the many-orders-of-magnitude separation one would expect if the two leakage mechanisms were, say, six or nine decades apart. In other words: the externally sourced ~1-100 nA/um order of magnitude for 22nm-class transistor off-state leakage is **not inconsistent** with a modest (~50x) transistor-vs-selector leakage-class separation at array scale. This is a coarse, back-of-envelope check, offered only to confirm the book's 47x figure is not implausible on its face; it is not a re-derivation or validation of NVSim's actual internal calculation.

---

## (d) Honesty check: what was NOT found

- No number for NVSim's own internal 22nm transistor leakage model was found or confirmed directly from NVSim's own paper text (paper access blocked everywhere tried: IEEE Xplore, ACM DL, SpringerLink, and a related PSU thesis). The "NVSim uses ITRS + MASTAR" claim is repeated in multiple independent secondary-source search summaries but was not verified against NVSim's own primary text. **Do not cite this as an established fact in the book without independently confirming it against the NVSim paper itself.**
- The Sinha et al. DAC 2012 PTM-FinFET paper (2011-ITRS-aligned, 20nm node, peer-reviewed) is a promising additional lead for a PTM-based 22/20nm Ioff figure, but its full text could not be retrieved in the time available (ACM/IEEE both blocked automated access), so no numbers from it are reported here. If someone with institutional IEEE Xplore/ACM DL access can pull that paper's device tables, it would be worth checking against the ITRS/Auth et al. figures already found.
- PTM's own peer-reviewed 22nm-node SPICE model files (as distinct from the dead ptm.asu.edu download files) were not found as a numbered, published Ioff table; the raw SPICE model card found on GitHub would require running a simulation to extract Ioff, which was intentionally not done (out of scope).

None of the above gaps undermine the recommendation in (a)/(b): the ITRS 2011 PIDS figures, corroborated by Auth et al. 2012's independently measured Intel 22nm silicon data, are a genuine, defensible, primary-source citation for the transistor side of the leakage-class separation, and they are recommended for use in the book regardless of whether NVSim's own paper is ever independently confirmed to cite the same source.

---

## Sources consulted

**Primary sources used for citations (full text obtained and read directly):**
- International Technology Roadmap for Semiconductors, 2011 Edition, Process Integration, Devices, and Structures (PIDS) chapter. PDF obtained directly from semiconductors.org (SIA's own archive); text extracted and read in full (41 pages).
- C. Auth et al., "A 22nm High Performance and Low-Power CMOS Technology Featuring Fully-Depleted Tri-Gate Transistors, Self-Aligned Contacts and High Density MIM Capacitors," 2012 Symposium on VLSI Technology Digest of Technical Papers, pp. 131-132, 2012. PDF obtained and read directly in full.

**Primary source checked and found not to reach the needed node (still worth recording):**
- W. Zhao and Y. Cao, "New Generation of Predictive Technology Model for Sub-45 nm Early Design Exploration," IEEE Transactions on Electron Devices, vol. 53, no. 11, pp. 2816-2823, Nov. 2006 (bibliographic details confirmed via multiple indexes; covers 130nm-32nm only, does not reach 22nm).
- Raw BSIM4 PTM "22nm_HP.pm" SPICE model card, mirrored on GitHub (`CMU-SAFARI/CROW`, originally from the now-unreachable ptm.asu.edu). Downloaded and inspected directly; contains no stated Ioff figure without simulation.

**Secondary sources used only to locate/describe primary sources, or flagged as unverified (not cited as the factual source for any number in this note):**
- Search-engine-synthesized summaries (via WebSearch) were used throughout to find the correct paper titles, venues, and URLs for the primary sources above - these summaries were not trusted for numeric values; every number in section (b) was independently confirmed against the primary-source full text.
- Secondary-source claims that NVSim's original paper "uses device data from the ITRS report and the MASTAR tool" - repeated across several independent search summaries but not independently verified against NVSim's own paper text (access blocked). Flagged as unconfirmed in (a)/(d) above.
- S. Sinha, G. Yeric, V. Chandra, B. Cline, Y. Cao, "Exploring sub-20nm FinFET design with predictive technology models," DAC 2012 - identified as a promising lead via bibliographic search, but its full text/tables could not be retrieved, so no numbers from it are used.
- NVSim-CAM (H. Li et al., ICCAD 2016) - PDF obtained and read directly for context on this research group's later use of PTM, but not used as a citation for the original NVSim's (2012) technology model, since it is a different, later tool.
