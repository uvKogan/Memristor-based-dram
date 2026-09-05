# Real Hardware Ground-Truth Numbers: Intel Optane DC PMM / 3D XPoint

Research notes compiled to replace unused/uncited claims in the MBMM book with real, precisely-cited
numbers for the only NVM main-memory module ever commercially shipped (Intel Optane DC Persistent
Memory Module, built on Intel/Micron 3D XPoint PCM technology).

---

## Item 1: Measured Latency (Optane DC PMM, App Direct / "uncached" mode)

**Source:** J. Izraelevitz, J. Yang, L. Zhang, J. Kim, X. Liu, A. Memaripour, Y. J. Soh, Z. Wang, Y. Xu,
S. R. Dulloor, J. Zhao, S. Swanson, "Basic Performance Measurements of the Intel Optane DC Persistent
Memory Module," arXiv:1903.05714v3 [cs.DC], 9 Aug 2019 (Version 1.0.1).

All numbers below are **idle/unloaded** latency, measured on the App Direct ("uncached", PM-Optane)
configuration with the DRAM cache disabled, using Intel's Memory Latency Checker (MLC) and the
authors' own kernel-module tool "LATTester". Test platform: dual-socket Cascade Lake-SP, 256 GB Optane
DC PMMs, firmware 01.01.00.5253 (Table 1, p. 14; configuration PM-Optane, Table 2, p. 15).

### Read latency
- **Random read latency: 305 ns** (single core, cold cache, prefetching disabled, using Intel MLC).
  Compared to **81 ns for local DRAM** on the same platform (**~3x slower**).
  - Citation: p. 6, Section 3 ("Basic Optane DC Performance") body text; restated p. 18, Section 3.1.1
    ("Read Latency"), **Observation 1**; plotted in **Figure 7** ("Read latency"), p. 19.
- **Sequential read latency: 169 ns** (~2x faster than random), "suggesting some buffering or caching
  inside the Optane DC PMM."
  - Citation: p. 6, Section 3 body text; restated p. 18, Section 3.1.1, **Observation 2**; **Figure 7**, p. 19.

### Write latency
- **94 ns for Optane DC vs. 86 ns for local DRAM.** Measured as the latency from a store instruction to
  the point the store reaches the processor's Asynchronous DRAM Refresh (ADR) domain (i.e., guaranteed
  persistent), via a store + cache-flush + fence sequence — not the latency to the physical media itself,
  which the authors state cannot be directly measured.
  - Citation: p. 6, Section 3 body text ("Latency" paragraph).
  - A fuller breakdown across instruction types (load / non-temporal load / store+clflush /
    non-temporal store / store+clflushopt / store+clwb, at 64/128/256-byte granularity) for local
    DRAM (PM-LDRAM), remote DRAM (PM-RDRAM), and Optane DC (PM-Optane) is given in **Figure 8**
    ("Memory Instruction Latency"), p. 20, Section 3.1.2, **Observation 3** (p. 19).

### Local vs. remote and sequential vs. random
- Figure 7 (p. 19) and Figure 8 (p. 20) both report **PM-LDRAM** (local DRAM), **PM-RDRAM** (remote-socket
  DRAM used to emulate NVMM, per configuration Table 2, p. 15), and **PM-Optane** side by side. Remote
  DRAM (PM-RDRAM) idle latency falls between local DRAM and Optane DC in these figures.
- Loaded (non-idle) latency-vs-bandwidth curves, showing latency degradation under increasing load, are
  in **Figure 14** ("Performance under load"), p. 26, Section 3.2.5.

---

## Item 2: Measured Bandwidth (Optane DC PMM)

**Source:** same paper as Item 1.

### Per-DIMM (single Optane DC PMM) maximum bandwidth
- **Max read bandwidth: 6.6 GB/s**
- **Max write bandwidth: 2.3 GB/s**
- Read is **2.9x** the write bandwidth for a single DIMM; DRAM's read/write gap is smaller, **1.3x**.
  - Citation: Abstract, p. 2 ("its max read bandwidth is 6.6 GB/s, whereas its max write bandwidth is
    2.3 GB/s"); restated p. 6, Section 3 body text; restated p. 21, Section 3.2.2 body text (with the
    2.9x / 1.3x comparison); plotted in **Figure 10** ("Bandwidth vs. thread count"), p. 22.

### Six interleaved Optane DC PMMs (one socket's worth)
- **Max read bandwidth: 39.4 GB/s** (sequential access, peaks around 12-17 threads)
- **Max write bandwidth: 13.9 GB/s** (saturates at just 4 threads)
  - Citation: p. 6, Section 3 body text; restated p. 20, Section 3.2.1, **Observation 4**; plotted in
    **Figure 1** ("Optane DC Sequential Bandwidth," compares to 6-DIMM local and remote DRAM arrays), p. 6,
    and again as **Figure 9**, p. 21.
  - DRAM comparison in the same experiment (6 local DRAM DIMMs): read bandwidth reaches over 100 GB/s
    (Figure 1/9, left panels).

### Random-access bandwidth vs. access size (single thread, single DIMM)
- Peaks at **2.8 GB/s for reads** and **1.5 GB/s for stores**, with a "knee" at 256 B (Optane DC's
  internal access/block granularity — sub-256 B accesses waste bandwidth and cause write amplification).
  - Citation: p. 6, Section 3 body text; **Figure 2** ("Optane DC Random Access Bandwidth"), p. 7.

### Bandwidth under load (queuing/loaded-latency test, Section 3.2.5, p. 25)
- Sequential: Optane DC **38.9 GB/s** vs. DRAM **105.9 GB/s** (reads).
- Random: Optane DC **10.3 GB/s** vs. DRAM **70.4 GB/s** (reads).
- Sequential writes: Optane DC **~11.5 GB/s** vs. DRAM **52.3 GB/s**.
  - Citation: p. 25, Section 3.2.5 body text; **Figure 14**, p. 26; **Observation 8**, p. 25.

### Interleaving effect
- Interleaving across all six DIMMs on a socket improves peak read/write bandwidth by **5.8x / 5.6x**
  respectively over a single DIMM — matching the DIMM count and confirming the per-DIMM bandwidth ceiling.
  - Citation: p. 22, Section 3.2.3 body text; **Figure 11** ("Bandwidth over access size"), p. 23.

---

## Item 3: Die Area / Cell Size for 3D XPoint

### Confirmed absent from the Izraelevitz et al. performance paper
The Izraelevitz et al. paper (arXiv:1903.05714) is exclusively a system/software performance-measurement
study. It never discusses the storage mechanism, materials, cell size, die area, or array
architecture of 3D XPoint at all — not even to name "phase-change memory" or a resistance-change
mechanism. Section 2.1.1 ("Intel's Optane DC PMM," pp. 13-14) covers only system-integration facts:
DDR-T electrical/protocol interface, three capacities (128/256/512 GB), 256-byte internal media
access granularity, an on-DIMM address-indirection table for wear-leveling, and configurable power
budgets (15 W average / 20 W peak, per Table 1, p. 15). No die-area or cell-size figures appear
anywhere in the document. This confirms the prediction that a performance-measurement paper would not
contain this data.

### Numbers found, with source-quality caveat
No ISSCC or IEDM paper describing the actual, shipped 3D XPoint die's array architecture, cell size, or
die area could be located; Intel and Micron kept the exact process/cell details of the commercial 2015
3D XPoint product proprietary and did not publish a dedicated conference paper disclosing its die
geometry. The original 2015 Intel/Micron technology announcement materials likewise did not disclose
die area or cell size figures in what is publicly available.

The most credible numbers found come from a professional physical teardown/technical-analysis
organization, **TechInsights**, which physically decapsulated and imaged (SEM/TEM cross-sections) an
actual retail Optane product and measured the die directly. These are presented as TechInsights' own
first-party analysis (not a journalist's or blogger's paraphrase of TechInsights' work), but they are
published on TechInsights' public blog as a *summary* of TechInsights' full paid technical report; the
complete underlying report itself (with full methodology) was not obtained or verified line-by-line —
only the public blog-level summary was read. Treat the specific numeric values below as reasonably
credible (first-party teardown, stated methodology, physical measurement) but not verified against the
full formal report:

- **Die size: 206.5 mm²** (16.16 mm x 12.78 mm), package size 241.12 mm²
- **Process node: 20 nm** (both word line and bit line)
- **Cell size: 0.00176 µm²**
- **Memory density: 0.62 Gb/mm²**; **128 Gb per die**
- **Array/memory efficiency: 91.4%** (TechInsights terms the cell layout "4F²")
- Cell stack: "double storage-selector stacked memory cell between metal 4 and metal 5" — GST
  (Ge-Sb-Te) phase-change alloy as the storage element, arsenic-doped Se-Ge-Si chalcogenide as the
  Ovonic Threshold Switch (OTS) selector element.
- Citation: TechInsights blog, "Intel 3D XPoint Memory Die Removed from Intel Optane™ PCM (Phase
  Change Memory)," https://www.techinsights.com/blog/intel-3d-xpoint-memory-die-removed-intel-optanetm-pcm-phase-change-memory
  (teardown subject: Intel Optane M.2 80 mm, 16 GB, PCIe 3.0 module); corroborated by a second
  TechInsights blog post, "Memory/Selector Elements for Intel Optane™ XPoint Memory,"
  https://www.techinsights.com/blog/memoryselector-elements-intel-optanetm-xpoint-memory (same 0.62
  Gb/mm² density and 128 Gb/die figures, explicit "1S1R" architecture label).

**Not confirmed from a primary (Intel/Micron-authored or peer-reviewed conference) source:** the die
area, cell size, process node, and density figures above rest solely on a third-party teardown vendor's
public blog summary, not on an Intel/Micron technical disclosure, an ISSCC/IEDM paper, or the full
TechInsights report. They should be labeled in the book as "third-party teardown estimate (TechInsights),
not an Intel/Micron-disclosed figure" if used, rather than as an Intel-confirmed specification.

For historical/architectural context only (not the commercial 3D XPoint product's actual density): an
earlier Intel/Numonyx *research* prototype of the same PCM+OTS cross-point cell concept, described in a
peer-reviewed IEDM paper (see Item 4), used a 64 Mb test chip with a **40 nm** cell — this predates and
is denser/smaller than the actual 2015 3D XPoint commercial product and should not be conflated with it.

---

## Item 4: 1S1R / Ovonic Threshold Switch (OTS) Cross-Point Architecture

### Not addressed by the Izraelevitz et al. paper
As with Item 3, the Izraelevitz et al. arXiv paper never mentions "selector," "OTS," "1S1R," "phase
change," or any storage-mechanism/array-architecture term. It treats Optane DC as a performance black
box. This item's confirmation must come from other primary/near-primary sources.

### Primary source found: Intel/Numonyx IEDM 2009 paper (architectural precursor)
D. Kau, S. Tang, I. V. Karpov, R. Dodge, B. Klehn, J. A. Kalb, J. Strand, A. Diaz, N. Leung, J. Wu,
S. Lee, T. Langtry, K.-W. Chang, C. Papagianni, J. Lee, J. Hirst, S. Erra, E. Flores, N. Righos,
H. Castro, G. Spadini, **"A Stackable Cross Point Phase Change Memory,"** *2009 IEEE International
Electron Devices Meeting (IEDM)*, Baltimore, MD, Dec. 2009, pp. 617-620.
DOI: 10.1109/IEDM.2009.5424263.

This is a peer-reviewed IEDM conference paper authored directly by Intel and Numonyx (the company later
acquired by Micron in 2010) device engineers. It describes a 64 Mb test chip built from a vertically
stackable **cross-point array in which each memory cell is one Ovonic Threshold Switch (OTS) selector
in series with one phase-change memory (PCM) resistive storage element — i.e., a 1-Selector-1-Resistor
(1S1R) cell** with no access transistor, using a 40 nm cell. This is the direct architectural and
material-technology ancestor of the 2015 Intel/Micron 3D XPoint product; the same OTS+PCM 1S1R
cross-point concept, refined and commercialized, underlies the shipped Optane DC PMM. This paper predates
the "3D XPoint" brand name (announced 2015) and its exact numbers (40 nm cell, 64 Mb) describe the 2009
research prototype, not the shipped product — but it is a genuine primary source for the **architectural
principle** (1S1R OTS+PCM cross-point, transistor-free) that Item 4 asks to confirm.

### Near-primary confirmation for the actual shipped product: TechInsights physical teardown
TechInsights' physical/materials teardown of a retail Intel Optane product (same source as Item 3)
explicitly labels the die's architecture "1S1R (one selector, one resistor per cell)" and identifies,
via cross-sectional TEM imaging and materials analysis, a GST-based PCM storage element in series with
an arsenic-doped chalcogenide (Se-Ge-Si) Ovonic Threshold Switch selector, in a stacked
metal-4-to-metal-5 cross-point structure.
- Citation: TechInsights blog, "Memory/Selector Elements for Intel Optane™ XPoint Memory,"
  https://www.techinsights.com/blog/memoryselector-elements-intel-optanetm-xpoint-memory (explicit
  "1S1R" architecture statement, OTS material identification via physical/materials analysis).
- Same caveat as Item 3 applies: this is TechInsights' own public blog summary of its (paid, not
  independently obtained) full technical report, not an Intel/Micron-authored disclosure.

### Corroborating (non-primary) academic review
M. Zhu, K. Ren, Z. Song, "Ovonic threshold switching selectors for three-dimensional stackable
phase-change memory," *MRS Bulletin*, vol. 44, 2019, pp. 715-720 (DOI via Cambridge Core /
Springer Nature Link). This is a peer-reviewed review article, but the authors are third-party academic
researchers, not Intel/Micron engineers, and it is a literature review rather than a primary
measurement of Intel's actual product. It corroborates (does not independently establish) the claim
that 3D XPoint uses an OTS selector paired with PCM in a 1S1R cross-point array, citing Intel's public
statements and the broader OTS-selector literature. Cited here only as corroboration, not as the primary
basis for the claim — the primary/near-primary basis is the IEDM 2009 Intel/Numonyx paper and the
TechInsights teardown, above.

### Overall conclusion for Item 4
The 1S1R Ovonic Threshold Switch cross-point architecture of Optane/3D XPoint is confirmed by (a) a
peer-reviewed IEDM paper directly authored by Intel/Numonyx engineers describing the identical
architectural principle in the technology's direct research precursor (2009), and (b) a professional
physical teardown of the actual shipped commercial product (TechInsights) that independently verifies
the same 1S1R OTS+PCM structure via materials/cross-sectional analysis. Confidence is high, though
neither source is an Intel/Micron technical disclosure specifically about the *2015-vintage commercial
3D XPoint die*; no such document was located.

---

## Sources

1. J. Izraelevitz, J. Yang, L. Zhang, J. Kim, X. Liu, A. Memaripour, Y. J. Soh, Z. Wang, Y. Xu,
   S. R. Dulloor, J. Zhao, S. Swanson, "Basic Performance Measurements of the Intel Optane DC
   Persistent Memory Module," arXiv:1903.05714v3 [cs.DC], 9 Aug 2019.
   Abstract: https://arxiv.org/abs/1903.05714 — PDF: https://arxiv.org/pdf/1903.05714

2. D. Kau, S. Tang, I. V. Karpov, R. Dodge, B. Klehn, J. A. Kalb, J. Strand, A. Diaz, N. Leung, J. Wu,
   S. Lee, T. Langtry, K.-W. Chang, C. Papagianni, J. Lee, J. Hirst, S. Erra, E. Flores, N. Righos,
   H. Castro, G. Spadini, "A Stackable Cross Point Phase Change Memory," 2009 IEEE International
   Electron Devices Meeting (IEDM), Baltimore, MD, Dec. 2009, pp. 617-620.
   DOI: https://doi.org/10.1109/IEDM.2009.5424263

3. TechInsights, "Intel 3D XPoint Memory Die Removed from Intel Optane™ PCM (Phase Change Memory)"
   (blog post / teardown summary).
   https://www.techinsights.com/blog/intel-3d-xpoint-memory-die-removed-intel-optanetm-pcm-phase-change-memory

4. TechInsights, "Memory/Selector Elements for Intel Optane™ XPoint Memory" (blog post / teardown
   summary).
   https://www.techinsights.com/blog/memoryselector-elements-intel-optanetm-xpoint-memory

5. (Corroborating, non-primary) M. Zhu, K. Ren, Z. Song, "Ovonic threshold switching selectors for
   three-dimensional stackable phase-change memory," MRS Bulletin, vol. 44, 2019, pp. 715-720.
   https://link.springer.com/article/10.1557/mrs.2019.206
