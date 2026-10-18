# Presentation Outline - MBMM (22nm ReRAM as Commodity Main Memory)

**Cut 2026-09-23 (task E8) to follow the short book.** This outline describes
`presentation_deck.html` as it now stands: **27 slides**, 6 embedded charts, 26 main-line slides
plus one backup slide. The previous 60-slide deck was built on the long document; this one follows
`Project_Book.typ`, the short, reviewed, reader-facing book, slide for section.

**Context:** about 30 to 35 min of talk (Q&A separate, after). Audience: the advisor, plus lab
colleagues who know memristors but not this project. Structure follows the book rather than a
defense template: the question, the method, the lessons, the four result axes, the discussion,
the verdict.

**Source of truth.** Every number on every slide is read from `Project_Book.typ` and cited below by
its book section, table or figure. The deck never says more than the book says. Where the book
attaches a caveat, the slide carries it too. The book itself traces every number to the frozen
result set, and the complete technical report carries the uncondensed tables and the appendix
recording claim by claim what changed since the September 3 version.

**Charts.** Six, all pre-existing and read-only: four are the book's own figures
(`media/short_book/fig_clock_sensitivity.png`, `media/media/image6.png`,
`media/short_book/fig_endurance_policy.png`, `media/media/image26.png`, `media/media/image23.png`)
and one is from the frozen slide-graph set (`results/slide_graphs_rev2026-09/12_queue_depth.png`).
Nothing was recomputed for the deck. The book's Figure 1, the pipeline diagram, is drawn as HTML
boxes on slide 3 rather than embedded, because the source is an SVG.

**Three things to say out loud, every time they come up:**

1. Every ReRAM latency is a **media** number at NVSim-projected timings. The two SILICON rows are
   the counterweight. Every Optane or CXL latency is a **device** number, measured on a product.
2. Every lifetime figure is a **projection** from a write distribution measured inside a 250 ms
   window and assumed stationary, never a measured lifetime.
3. The per-gigabyte power gap is an **upper bound**: DDR5 gets its power-down credit, ReRAM's
   power-down energy is a disclosed no-savings placeholder.

**The projection caveat is printed on the slide, not left to the speaker.** The rule is the
per-slide one, not a single caveat slide that others reference: every slide claiming modeled ReRAM
is faster than, or latency-competitive with, DDR5 carries its own highlighted caveat block naming
all three conditions (NVSim-projected device timings; published silicon at 11.9 us and 379 us, not
finishing the LBM window; slower than DDR5 on the write-dominated burst). That is slides
**8, 9, 11 and 24**. A reference to a caveat elsewhere in the deck does not travel with a
screenshot, which is the failure this rule exists to prevent. If a future edit adds another such
claim it needs the same block, and `tests/test_presentation_deck.py` will fail until it does.

**Retired values have no home in this deck.** There is no change-log appendix any more; the
technical report's change appendix is where the 3 September figures live. The test asserts every
retired string, every superseded interim value and the outside reviewer's remembered numbers are
absent from every slide.

---

## 1. The question and the method (slides 1 to 5)

| # | Slide | Key content | Book |
|---|---|---|---|
| 1 | Title | Title, name, advisor, date; short book, technical report named as a separate document | Title page, 1.3 |
| 2 | Why This Question, Now | Economic pressure (DRAM wafers to HBM, late 2025) and physical pressure (capacitor scaling); the narrow question; endurance as the binding constraint; balanced verdict, not advocacy | 1.1, 1.3 |
| 3 | The Pipeline, End to End | NVSim to extraction to generation to NVMain 2.0 to post-processing; `mbmm_master.py` as the gate; frozen datasets, 120-run primary matrix, seven sensitivity series, manifests; 783 tests | 2.1, Figure 1 |
| 4 | Device Characterization at One Matched Organization | Table 1 in full: 20F2 / 4F2, read 10.12 / 4.70 ns, write 15.26 / 24.59 ns, leakage 108.384 mW for both, area 12.008 / 3.540 mm2; MLC multipliers 1.5x and 3.263x from the EMBER macro | **Table 1**, 2.2 |
| 5 | Baselines and Traces | DDR5-4800 two 32-bit subchannels with JESD79-5 timings and the worst-case-current disclosure; legacy PCM; the two published-silicon rows; 64 B everywhere; 800 MHz assumed. Table 2 condensed: six traces, records, read/write in window, span; time base and window; mcf parked | 2.3, 2.4, **Table 2** |

---

## 2. What the pipeline taught me (slides 6, 7)

| # | Slide | Key content | Book |
|---|---|---|---|
| 6 | Lessons 1 to 4 | Match the organization; establish the time base; the classic metric lies under saturation; a template inherits more than it declares | Chapter 3 |
| 7 | Lessons 5 to 8 | Read the power accounting to the line; charge a device latency once; keep a silicon counterweight; know which timing key sits on the request path | Chapter 3 |

Stated as mechanisms, never as retired values. Lesson 8 sets up slide 11.

---

## 3. Results (slides 8 to 19)

### Latency (slides 8 to 11)

| # | Slide | Chart | Headline | Book |
|---|---|---|---|---|
| 8 | Latency: the Whole Table, With the Silicon Rows | (table) | Table 4 in full, eight configurations against six traces; completion 46.1% / 9.2% / 0.5% for the three service-limited rows. **Caveat block** | **Table 4** |
| 9 | The Interface Clock Is Three Quarters of the Number | `fig_clock_sensitivity.png` | 41.4 / 27.9 / 19.0 and 36.8 / 23.6 / 14.9 ns at 800 / 1333 / 2400 MHz against 83.1; of 41.40 ns only 11.25 is NVSim device time; direction robust, magnitude model-dependent. **Caveat block** | 4.1, **Figure 2** |
| 10 | The Write Burst: the One Regime ReRAM Loses | (stats) | DDR5 234.3 ns against 353.1 / 391.5 / 512.0 / 652.9; 1.507x, 1.671x, 2.185x, 2.787x; a lower bound on the deficit | 4.1, Table 4 |
| 11 | MLC and the Write-Pulse Bracket | (table) | The bracket table; ratios become 1.507x to 2.973x through 2.787x to 10.665x; the CPU-trace mechanism (write fraction times pulse, to within 1%) against the burst mechanism (76% open-row hits, 21 to 23 times the pulse); **upper end, not a prediction**; below DDR5 on the CPU traces survives at the upper end, worst case 0.871x; the literature bound. **Caveat block** | 4.1, the write-pulse bracket table |

Slides 8 and 9 are a **pair**: the table states the result, the figure states how much of it is the
assumed clock.

### Power (slides 12 to 14)

| # | Slide | Chart | Headline | Book |
|---|---|---|---|---|
| 12 | Where the Watts Are | `image6.png` | No transistor-versus-selector leakage gap; one shared static floor of 6.937 W; dynamic power 2.9 to 4.9 mW under GCC, 346 to 417 mW under the AI bursts | 4.2, **Figure 3** |
| 13 | Power per Gigabyte, and the Gating Break-Even | (table) | Table 5; 12.7x to 17.4x SLC and 6.4x to 8.7x MLC per gigabyte, an upper bound, memory devices only; gating break-even 94.3%, inside the 94 to 98% idleness band; 0.142 W and 0.419 W against 0.399 W at the two ends | 4.2, **Table 5** |
| 14 | Overhead, Organization and the Selector | (text) | Overhead raises the threshold: 97.9% at 0.5 W, no parity beyond 0.79 W; leakage is an organization result (224.138 and 220.224 mW at 1024, within 2%); selector adds 0 to standby, 7.56 / 0.076 mW during an access; **OTS tile ceiling 1666 cells a side** against the 2048 simulated | 4.2, `results/selector_layer.json` |

### Endurance (slides 15, 16)

| # | Slide | Chart | Headline | Book |
|---|---|---|---|---|
| 15 | Endurance: the Projection and the Requirement | (table) | Table 6: no leveling 7.7 / 23.2 / 69.5 hours, randomized Start-Gap, ideal 38.6 / 3.6 / 4.3 years, required endurance 2.6e5 / 2.8e6 / 2.3e6 ideal and 6.3 / 6.5 / 4.3e6 randomized; **stationarity stated on the slide** | **Table 6** |
| 16 | The Leveling Decides It | `fig_endurance_policy.png` | The leveling decides it, not the cell; sparse footprints (577 / 826 / 1,954 locations); a larger module is worse over one region; the simulation cannot show leveling at work (2,207 and 23,848 gap moves), and the projection is validated to 0.3% | 4.3, **Figure 4** |

### Scaling, sensitivities, density (slides 17 to 19)

| # | Slide | Chart | Headline | Book |
|---|---|---|---|---|
| 17 | Scaling Is a Queueing Return | `image26.png` | Table 7 plus the Pareto trajectory; GCC 45.4 to 41.4 ns, the burst flat; the AI bursts gain 1.68x and it is entirely the second channel; rank depth at most 7.5% | **Table 7**, **Figure 5** |
| 18 | Queue Depth, and Four Sensitivities | `12_queue_depth.png` | 124.9 / 353.1 / 1,049.2 ns in the controller against 680.1 / 486.1 / 432.5 us end to end; the 1024 organization, the 64 B cross-check, the ReadVoltage sweep in one line each | 4.4 |
| 19 | Density, and the Whole Evaluation in One Table | `image23.png` | 1.24x and 2.47x for 1S1R against 0.36x and 0.73x for 1T1R; the 3.4x area advantage; the 12nm projection as geometry; then Table 8 with the per-gigabyte column as the only comparable one | 4.5, **Table 8**, **Figure 6** |

---

## 4. Discussion and verdict (slides 20 to 24)

| # | Slide | Key content | Book |
|---|---|---|---|
| 20 | Near and Far Memory: the Window | Local DDR5 111 to 114 ns idle, CXL DRAM devices 214 / 239 / 271 / about 394 ns, all device numbers; no blanket threshold survives the workload data; this work's two lines sit on opposite sides of the window; page placement, not per-request routing; the bandwidth framing | 5.2 |
| 21 | The Device Reference Table | Table 9: four media rows, DDR5 twice (modeled media and measured device), CXL devices, Optane PMem 305 / 169 ns; the conditional statement, and which half of the problem is open | **Table 9** |
| 22 | Bit Errors and Error Correction | Three layers kept apart: the channel model against measured 1T1R macros; the selector's own contribution; the 2e-4 with BCH design point at about 27% overhead against DRAM SECDED; SSD-class rather than DRAM-class correction; modeled latencies exclude ECC decode | 5.3 |
| 23 | Limits of the Model | The seven disclosed limits, in the book's own order | 5.4 |
| 24 | The Verdict | What holds is direction, what is bounded is the power deficit and the write burst, what is projected is every lifetime and the latency advantage; the one-line conclusion. **Caveat block** | 5.1, Chapter 6 |

---

## 5. Close (slides 25 to 27)

| # | Slide | Key content | Book |
|---|---|---|---|
| 25 | Future Work | The book's eight items, two columns | Chapter 6 |
| 26 | Data Availability, and Where the Full Record Is | The repository; the technical report named as the uncondensed record; the gated pipeline, frozen datasets and 783 tests | 1.3, Chapter 6 |
| 27 | Backup: Shahar's Ten Notes, Mapped | Each of the ten notes against the slide that answers it. Prepare, do not present unless asked; open the meeting here if he asks what came of his review | review mapping |

---

## Deck mechanics

Unchanged: horizontal track, arrow keys or click the screen edges, swipe on touch, `N` toggles
speaker notes (hidden by default), `Home` and `End` jump to the ends, the URL hash is the slide
number. The progress rail and the slide counter read `slides.length`, so they track the 27 slides
automatically.

The file is standalone: the six charts are embedded as base64 PNG data URIs, and the only external
reference is the Google Fonts stylesheet the deck already used.

Rebuild: the slide source is `results/slide_graphs_rev2026-09/_deck_builder/deck_slides.html` and
the assembly step is `build_deck.py` beside it, which reuses the committed deck's CSS and
navigation script, inlines any chart named `__CHART__<file>.png` from the frozen slide-graph set or
the book's media folders, and refuses to write a deck containing an em-dash or an en-dash.
