# Presentation Outline - MBMM (22nm ReRAM as Commodity Main Memory)

**Context:** ~60 min pure talk time (Q&A separate, after). Audience: lab
colleagues who know memristors but not this project, plus advisor. First
outing is internal; built to scale up to conference-level later. Standard
defense structure (Motivation → Background → Methodology → Results →
Contributions → Future Work).

**Reframing rule applied throughout:** every slide that touches the
gating-parity claim or the streaming comparison uses the *honest* framing
from `Presentation_Fixes_Tracker.md`. As of 2026-08-23 the book has been
updated to match (gating parity reworded as a projection contingent on
unmodeled gating in Abstract/§3.3/Table 7/Conclusion; streaming claim
scoped to compute-bound with the 1.9-2.1x penalty disclosed) - book and
talk now say the same thing. Canonical fix status lives in
`Review_Fixes_Tracker.md`.

**Figures:** all chart slides are generated - see `visualize_slides.py`
(repo root) and `results/slide_graphs/*.png`. Every chart tag below now
points at its actual file. Regenerate anytime with
`python3 visualize_slides.py`. Diagrams/tables with no file tag are
text/number slides - no chart needed.

Target: ~38 slides, ~1.6 min/slide average.

---

## 0. Title (1 slide, 0.5 min)

**Slide:** Title, your name, advisor, date, one-line subtitle: "Can 22nm
ReRAM replace DDR5 in a commodity DIMM?"

---

## 1. Motivation (4 slides, ~6 min)

**Slide 1 - The memory supply-demand crisis**
- On-slide: 1-2 stats on DRAM wafer reallocation to HBM (late 2025), one
  chart/timeline if available
- Say: DRAM capacity is being pulled toward AI/HBM; commodity main memory
  is getting squeezed. That's the market pressure motivating alternatives.

**Slide 2 - Why ReRAM as a candidate**
- On-slide: non-volatile (zero refresh) · higher density potential ·
  logic-compatible process
- Say: the pitch is refresh elimination and density - but endurance is
  the classic objection, flag it now so it doesn't feel dodged later.

**Slide 3 - The research question**
- On-slide: "Device-level ReRAM is well studied. System-level, commodity-
  DIMM behavior under real workloads is not."
- Say: most ReRAM literature stops at the cell or macro. This project asks
  the system question - what happens when you put it in a DIMM behind a
  memory controller and run real traces through it.

**Slide 4 - What this project actually built**
- On-slide: cross-layer pipeline, NVSim (device) → NVMain (system),
  driven by real traces - SPEC CPU2017 (gcc, lbm) via gem5, STREAM, AI
  inference via SCALE-Sim - 20 configs × 6 workloads
- Say: this is the specific, concrete thing being evaluated - sets up
  Background/Methodology without overclaiming novelty over unnamed prior
  system-level work (there's no formal related-work section yet - say
  "system-level, cross-layer, workload-driven" as the specific angle,
  not "first ever"). If asked what gem5/SCALE-Sim are: gem5 is a
  cycle-accurate CPU architecture simulator used only to record real
  SPEC CPU2017 memory-access traces (it doesn't model the memory itself);
  SCALE-Sim is a systolic-array accelerator simulator used the same way
  for the AlexNet/GPT-2 traces.

---

## 2. Background (4 slides, ~6 min - audience knows memristors, so skip device physics 101)

**Slide 5 - 1T1R vs 1S1R, in one breath**
- On-slide: 1T1R = transistor-gated, no sneak paths, bigger cell (20F²
  planar) · 1S1R = selector-gated, smaller cell (4F²), slower access
- Say: one sentence recap since the audience already has this; then land
  on why cell area *isn't* a fixed constant - it's architecture-dependent
  (recessed-channel demo hits 6F², footnote for the density slide later).

**Slide 6 - SLC vs MLC**
- On-slide: SLC = 1 bit/cell · MLC = 2+ bits/cell via ISPV programming →
  write-latency penalty
- Say: NVSim can't natively simulate MLC's iterative sensing (it crashes
  on it), so this project derived an analytical penalty method from the
  same EMBER macro's two publications instead (Upton et al., ESSCIRC
  2023 [6]; Levy et al., IEEE JSSC 2024 [31]) - sets up a methodology
  slide. On-slide now carries both citations, not just "two papers."

**Slide 7 - The cast of characters**
- On-slide: table - DDR5-4800 (baseline), PCM (legacy NVM baseline),
  1T1R SLC/MLC, 1S1R SLC/MLC - one row each, cell size + role
- On-slide (2026-09-05, Shahar-notes overarching item): a lede below the
  table states the three-axis framing - every technology is judged on
  latency, density, endurance, power as a fourth - and notes that an
  axis not evaluated for a technology (e.g. PCM's density row) is a
  disclosed scope choice, not a missing fact.
- On-slide (2026-09-05, Shahar-notes item 1): PCM's Cell Size cell
  changed from bare "N/A" to "n/s*" with a footnote - PCM's baseline is
  a black-box timing/energy model with no stated access-device
  architecture (neither transistor- nor selector-gated); the real
  shipped product (Intel Optane/3D XPoint) is a confirmed 1S1R
  cross-point design (IEDM 2009 Intel/Numonyx paper, new ref [42], plus
  a corroborating physical teardown), not modeled here at all.
- Say: six configurations, this is what gets compared for the rest of
  the talk. Name the three-axis framing out loud here.

**Slide 8 - Where this sits**
- On-slide: device-level ReRAM literature = extensive · system-level,
  DIMM-scale, workload-driven evaluation = the gap this fills
- Say: honest positioning - acknowledges you haven't done a formal
  literature survey slide, but states the angle precisely.

---

## 3. Methodology (8 slides, ~12 min)

**Slide 9 - The pipeline**
- On-slide: diagram - 1_run_nvsim_hardware.py (NVSim device chars) →
  2_extract_hardware_metrics.py (parse → JSON, + analytical MLC) →
  3_gen_nvmain_config.py (replicate chip ×1/8/16/64 → NVMain config) →
  4_execute_simulation.py (NVMain 2.0 controller + trace execution) -
  orchestrated end-to-end by mbmm_master.py ("The Gate-Keeper")
- Implemented directly in the deck (HTML/CSS pipeline boxes, not a report
  figure). Say: NVSim only ever characterizes ONE chip - everything from
  step 3 onward is NVMain replicating that chip a small, fixed number of
  times and wrapping it in its own controller; NVSim never sees a rank,
  a controller, or a workload. This bridge is itself a contribution -
  most tools stop at one layer or the other.
- On-slide addition (2026-09-02, Lead-requested): teaser line pointing
  forward to Slide 11 ("what actually crosses step 1→2, field by field,
  coming up shortly") so the audience knows detail is coming, not
  skipped.

**Slide 10 - One chip → a full DIMM (numbers to have cold)**
- On-slide: stat callouts - 1 Gb per-chip capacity (gigabit, not
  gigabyte; Table 1) · 1-64 chips replicated per config (single →
  8chip → 16chip → full DIMM) · 800 MHz ReRAM device clock (PCM 400 MHz,
  DDR5 2400 MHz) · 64-bit DIMM bus width · 8/16 GB full-DIMM capacity,
  SLC / MLC (2 bits/cell doubles it) · 3 GHz host CPU issue rate
  (CPUFreq) - same for ReRAM, PCM, and DDR5, explicitly labeled "not a
  device clock" so it doesn't read as DDR5's own frequency · one lede line: 64 × 1 Gb
  ÷ 8 (bits to bytes) = 8 GB SLC; MLC's 2 bits/cell doubles it to 16 GB.
  NVMain adds the FRFCFS controller, decoder, and interconnect NVSim has
  none of.
- Say: NVSim gives one 1 Gb (gigabit) chip - a cell count, not a byte
  count; NVMain's controller and address-mapping logic turns up to 64 of
  them into an 8-16 GB DIMM. The 800 MHz interface is a deliberate
  choice, not a device limit, and has no independent ReRAM citation
  backing it - it costs ground in the bandwidth-bound AI regime, which
  is why dual-channel/faster-PHY ReRAM is scoped as future work.
- 2026-09-05 (Shahar-notes item 2, research completed): a `/research`
  dispatch confirmed no independent ReRAM interface-speed citation
  exists for 800 MHz - EMBER's "100 MHz" is the macro's internal
  sense/write clock, not an interface rate (confirmed from both EMBER
  papers' own text); the only real ReRAM chip I/O clocks found (Fujitsu
  SPI parts) run 5-10 MHz, 80-160x slower, actively contradicting rather
  than merely failing to support 800 MHz. `Project_Book.typ`'s 800 MHz
  passage (§1.3) now states this explicitly as a disclosed modeling
  assumption; speaker note above updated to match.
- 2026-09-02 (Lead-caught, two rounds): (1) the original "(64×1 Gb
  chips)" parenthetical read like 64×1 should equal 8 or 16 directly -
  it never showed the bits-to-bytes conversion or MLC's 2-bits/cell
  doubling; fixed with explicit unit labels and an arithmetic line.
  (2) that fix plus the earlier "PCM 2 GHz" clock correction (see
  Change Log) made the slide too dense - two stat-rows, two lede lines,
  and a 4-sentence speaker note all fighting for the same fixed,
  non-scrolling slide height (`.speaker-note` renders inline, always
  visible - it isn't a hidden presenter layer in this deck), so text
  overlapped ("technology" collided with neighboring text, arithmetic
  and speaker-note lines stacked on top of each other). Fixed by
  trimming every label back to its essential form, merging the two lede
  lines into one, and cutting the speaker note to the load-bearing
  facts only. Re-verified overlap-free via a headless-Chrome screenshot
  of the live slide (`--headless --screenshot`), not just a balance
  check.
- 2026-09-02 (Lead-caught, third round): asked whether "3 GHz" was
  DDR5's own frequency and why it's on the slide at all - it's CPUFreq
  (the simulated host's request-issue rate), a different axis from the
  800 MHz/400 MHz/2400 MHz device clocks shown above it, deliberately
  unified to 3 GHz across all three technologies (§3.1.6 item 11) so the
  comparison is matched-host on the request-generation side. Fixed the
  label to make that distinction explicit on-slide: "host CPU issue rate
  (CPUFreq) - same for ReRAM, PCM, and DDR5; not a device clock".

**Slide 11 - The Bridge, in parameters**
- On-slide: two-column list - NVSim output (Table 1) [3]: read/write
  latency (ns), read/write energy (nJ), leakage (mW/chip), die area
  (mm²), capacity · NVMain input (Appendix B) [4]: tCAS/tRCD/tRP
  (cycles), Erd/Ewr (nJ/access), Eactstdby/Eprestdby (nJ/cycle),
  ROWS/COLS/RANKS/BANKS
- Say: this is what "the bridge" does at the field level - unit and
  granularity conversion, not new physics. This exact seam is where
  the toolchain audit found most of its 14 bugs.

**Slide 12 - Real workloads, not synthetic averages**
- On-slide: table, now 6 rows matching the "six traces" said below (was
  5 rows with AlexNet IFMAP/OFMAP merged into one, contradicting its own
  speaker note) - GCC (compute-bound, isolates static leakage power,
  DIMM mostly idle) · LBM (sustained streaming, isolates dynamic
  switching energy) · STREAM (bandwidth benchmark, isolates a
  sustained-bandwidth baseline - predictable traffic, no compute noise)
  · AlexNet IFMAP (read-storm, isolates controller queueing under
  massive parallel reads) · AlexNet OFMAP (write-storm, isolates MLC -
  multi-level-cell - write-latency penalty) · GPT-2 IFMAP
  (max-parallelism AI read, isolates controller queueing under MLP -
  memory-level parallelism)
- Say: six traces chosen to bracket the workload space, from idle-mostly
  to fully saturating.
- 2026-09-02 (Lead-caught): the old "Isolates" column used unexplained
  acronyms (MLC, MLP) and a vague phrase ("clean streaming comparison")
  with no definition on-slide - spelled both acronyms out inline and
  replaced the vague phrase; also split the merged AlexNet row so the
  table's own row count matches its "six traces" speaker note.

**Slide 13 - Baselines**
- On-slide: DDR5-4800 modeled to JEDEC spec · legacy PCM baseline for
  historical NVM context
- Say: DDR5 is the real target to beat; PCM shows how far NVM has come.

**Slide 14 - I audited my own toolchain**
- On-slide: "14 silent failure modes found in the standard NVSim→NVMain
  flow; 12 repaired and validated" - 4 bullets, each an issue → fix pair:
  leakage/access-energy silently ignored → wired into the power model
  (this is what the 47x leakage gap and 1.12 W rest on) · DDR5's
  refresh timing/supply inherited unscaled from a DDR3-1333 template →
  corrected to real DDR5-4800 JEDEC values · ReRAM's MLC multipliers
  unsourced ("EMBER heuristics" not in the cited paper) → re-sourced to
  Upton et al. [6] / Levy et al. [31], re-derived · idle power-down
  still disabled in NVMain's source → found and documented, NOT yet
  fixed (explicitly flagged as still-open, ties to the top-priority
  future-work item)
- Say: this is a genuine strength - present it as rigor, not confession.
  Twelve of fourteen are fixed and re-validated; the two still open
  (idle power-down, trace provenance) are disclosed, not hidden.
- 2026-09-02 (Lead-caught, two fixes): (1) title was "We Audited Our Own
  Toolchain" - plural voice, inconsistent with this being single-author
  work (confirmed the book itself is 100% first-person "I" throughout,
  the deck's title was the one outlier) - fixed to "I Audited My Own
  Toolchain". (2) the Lead asked for more substance on what was actually
  fixed and what the issue was - the old 3 bullets were bare labels with
  no issue/fix framing, and one of them (disabled power-down model) was
  presented as if it were an example of a "repaired" item when it's
  actually one of the 2 still-open findings, contradicting the "12
  repaired" framing above it. Rewrote all 4 bullets as explicit issue →
  fix pairs and explicitly flagged the power-down item as still open.
- 2026-09-02 (Lead-caught, follow-up): the richer bullets from the fix
  above then overflowed the slide again - but the Lead correctly
  diagnosed the actual cause: `ul.points` has a shared `max-width: 66ch`
  in the deck's CSS, so the bullets were wrapping into 3-4 lines each
  while using only the left half of the slide's actual width, not
  because there was too much text for the available space. Fixed by
  widening just this slide's list via an inline `max-width:min(96ch,
  88vw)` override (left the shared `ul.points` CSS rule alone, so no
  other slide's bullet width changed) - same words, roughly one fewer
  wrapped line per bullet, comfortable margin restored below the last
  bullet. Re-verified overlap-free via screenshot.

**Slide 15 - What "validated" means here (limitation, stated upfront)**
- On-slide: "Validation = internal consistency (NVMain matches NVSim to
  0.0% error), NOT external silicon validation" - one clean caveat
- Say: be the one who raises this before someone in the audience does.

**Slide 16 - Assumptions that shape every result that follows**
- On-slide: 4 bullets - gem5 traces are uncached (max memory pressure) ·
  GPT-2 trace provenance unverified · DDR5 power = datasheet spec-limit,
  not typical · ReRAM power = worst-case, gating not yet simulated
- Say: read every number in the next 25 minutes through this lens - this
  slide is the fix for "caveats surfacing too late."

---

## 4. Results (15 slides, ~28 min)

### Latency (4 slides)
**Slide 17 - Compute-bound: the closest gap**
`results/slide_graphs/15_latency_gcc.png`
- On-slide: 1T1R SLC 131 ns vs DDR5 87 ns - 1.5x, smallest gap in
  the suite

**Slide 18 - Streaming: the honest number**
`results/slide_graphs/16_streaming_honest.png`
- On-slide: STREAM latency (DDR5/1T1R SLC/1S1R SLC, 1.9-2.1x DDR5) next
  to LBM completion rate (100% → 40% → 28% → 16% → 9% → 4%)
- Say: the book was updated 2026-08-23 to match this framing
  (compute-bound, streaming penalty disclosed) - the completion panel is the point: 1T1R only finishes 40% of
  what DDR5 finishes in the same window, so the reported latency ratio
  understates the real gap. Streaming is the weakest regime, say so
  plainly.
- 2026-09-02 (Lead-caught): "the same window" was never defined anywhere
  on the slide - added the value inline: "the same 83.33 ms matched-host
  window" (the fixed wall-clock, identical-admission window from
  §3.1.6 item 11, already used throughout the book/deck). Re-verified
  overlap-free via screenshot.

**Slide 19 - AI inference: DDR5 wins**
`results/slide_graphs/17_latency_gpt2.png`
- On-slide: 4.6x DDR5 under GPT-2 parallel read-storm; small-print
  caveat baked into the chart footnote: GPT-2 trace provenance
  unverified, treat as representative stress pattern
- Say: no hedging - DDR5 territory today for high-parallelism serving.

**Slide 20 - The MLC write tax**
`results/slide_graphs/18_mlc_write_penalty.png`
- On-slide: 1S1R MLC OFMAP latency = 2x its SLC sibling; MLC → read-
  mostly applications only

### Power (3 slides)
**Slide 21 - The 47x fact**
`results/slide_graphs/19_device_leakage.png`
- On-slide: device-level leakage, 1T1R 795 mW/chip vs 1S1R 17 mW/chip
  [3] - the single number that decides everything downstream. Added:
  DDR5 standby floor (~358 mW, whole-module vendor spec, not
  like-for-like) alongside it for scale.
- Say: this comes straight out of NVSim's own transistor-vs-selector
  access-device model (Dong et al., IEEE TCAD 2012 [3]) at 22nm FinFET
  LOP - before any workload is simulated. A dedicated sweep confirms
  it's the access-device model driving this, not the HRS/LRS targets
  (Matsui et al. [7]). Direction is field consensus; the exact 47x
  magnitude is this project's simulation, not externally confirmed.

**Slide 22 - Full-module power**
`results/slide_graphs/20_module_power.png`
- On-slide: 1T1R 50.9 W (infeasible) · 1S1R 1.12 W · DDR5 0.651 W ·
  PCM 0.040 W

**Slide 23 - Power-Delay Product**
`results/slide_graphs/21_pdp_geomean.png`
- On-slide: 1S1R beats 1T1R by ~29-31x; DDR5 still ~3.7-5x ahead of
  ungated 1S1R

### Scaling (2 slides)
**Slide 24 - Compute-bound scaling: a real, modest gain** (retitled
2026-09-02, was "The Flatline Paradox")
`results/slide_graphs/22_pareto_gcc.png`
- On-slide: GCC (1T1R SLC) latency improves ~14% from 1-chip to full
  DIMM (152.6 -> 130.9 ns, `results/system_v6/processed_pareto_metrics.csv`)
  - a real gain, not zero. Linear leakage cost still applies alongside it.
- Say: the opposite of what the "low-MLP, no scaling benefit" theory
  predicts - flagged as an open question, next-step work on the book,
  not resolved here.
- 2026-09-02 (Lead-caught, major finding): the Lead independently
  observed while looking at the live deck that this chart visually shows
  latency DECREASING as chip count increases, contradicting the "zero
  latency benefit" bullet. Verified against the book's own source figure
  (`media/media/image18.png`) AND the raw data
  (`results/system_v6/processed_pareto_metrics.csv`) - confirmed real:
  GCC 1T1R SLC goes 152.58 ns (single) -> 152.58 (8chip) -> 140.52
  (16chip) -> 130.91 (full DIMM), a genuine ~14% improvement. This is
  the opposite of `Project_Book.typ` §3.2's own prose ("the system
  gains almost zero latency benefit"). Per the Lead's explicit
  direction, patched the DECK's wording to state the true, verified
  finding and flagged the "why" as unresolved future work on the book -
  did NOT rewrite `Project_Book.typ` §3.2 itself (out of scope for this
  session, tracked as a new open item, see Review_Fixes_Tracker.md).
  Known limitation: the embedded chart PNG's own baked-in matplotlib
  title ("The Flatline Paradox: no MLP, no benefit from scaling") still
  reflects the old, incorrect framing and can only be corrected by
  re-running `visualize_pareto.py` - flagged, not fixed, in this pass.

**Slide 25 - AI-inference is the actual flatline** (retitled 2026-09-02,
was "Breaking the flatline")
`results/slide_graphs/23_pareto_gpt2.png`
- On-slide: GPT-2 IFMAP latency is bit-for-bit identical at every chip
  count (458.41 ns, 1-chip through full DIMM - exact match in the raw
  CSV). AlexNet IFMAP is nearly as flat (394.7 -> 397.4 ns). The two
  highest-parallelism (highest-MLP) workloads in the whole suite show
  NO scaling benefit at all - the opposite of the book's MLP theory.
- Say: this directly contradicts the MLP-driven explanation as
  originally written - flagged as the top open item for the next book
  revision, not resolved yet.
- 2026-09-02 (Lead-caught, same finding as Slide 24): same root cause
  and same disposition - deck wording corrected to the verified data,
  root-cause explanation deferred to future book work, chart PNG's own
  stale title ("Breaking the flatline: high-MLP workloads reward
  scaling") flagged as a known, unfixed limitation of this pass.

### Global viability / density (3 slides)
**Slide 26 - Density**
`results/slide_graphs/24_density.png`
- On-slide: 1S1R SLC 1.92x DDR5 density (3.84x MLC) · 1T1R 0.22x - cell
  area, not node, decides this; footnote: 20F² isn't a hard ceiling
  (6F² recessed-channel demo exists, real device-physics work needed to
  close that gap)

**Slide 27 - Scaling projections (clearly labeled)**
`results/slide_graphs/25_density_projection.png`
- On-slide: 12-16nm + 3D deck-stacking projections, big "PROJECTED - NOT
  MEASURED" badge baked into the chart itself

**Slide 28 - Endurance**
`results/slide_graphs/26_endurance.png`
- On-slide: 8 GB module (the physically simulated capacity) @ worst-case
  streaming = 1.1 yr (below the 5-10 yr target) · 64 GB = ~9 yr, 128 GB
  = ~17 yr (both clear it, both flagged as a linear-scaling projection,
  not a separately simulated capacity - no 64 GB or 128 GB config was
  ever built or run) · every other workload clears it by 20x+ even at
  8 GB · caveat baked into chart: assumes ideal wear leveling, no
  controller implemented yet
- 2026-09-02 (Lead-caught): the Lead noticed the summary slide's table
  header ("Lifetime@128GB*") never seemed to have been set up earlier -
  this slide's on-slide bullets previously stopped at 64 GB (~9 yr),
  leaving 128 GB mentioned only in the speaker note (not visible during
  a presentation). Added the 128 GB figure (~17 yr, matching the
  summary table's 17.3 yr for 1T1R SLC, both sourced from
  `Project_Book.typ`'s "9-17 years" range) to the visible bullet so the
  summary slide's column header doesn't introduce a new number with no
  visible setup. (Since fixed for real, same session: the chart PNG was
  regenerated via `visualize_slides.py` to add a genuine third "128 GB
  (server-class)" bar series, not just the on-slide text - see
  `Review_Fixes_Tracker.md`'s 2026-09-02 entry. The note above about a
  missing 128 GB bar is stale/outdated as of that fix.)
- On-slide (2026-09-05, Shahar-notes item 8): added a lede showing the
  actual endurance calculation worked out (134.2M cache-line locations ×
  10⁷ rated cycles ≈ 1.34×10¹⁵ total writes ÷ LBM's ~39.2M writes/s
  annualized ≈ 1.08 yr at 8 GB) instead of only stating the conclusion -
  answers Shahar's "show calculations" request directly. First version
  overflowed the slide (equation + full speaker note together); fixed by
  trimming the speaker note, which was largely redundant once the math
  is visible on-slide.
- Say: only 8/16 GB was ever actually simulated - the architecture
  factory's physical ceiling at 64 chips. 64/128 GB figures elsewhere
  are the same linear arithmetic shown on-slide, never separately built
  or run.

### The flagship claim - reframed (3 slides, the most important section)
**Slide 29 - Where this stands today** *(number callouts, no chart)*
- On-slide, three big stat callouts:
  - **1.12 W** - 1S1R SLC, full module, ungated
  - **0.651 W** - DDR5-4800, conservative calibration floor
  - **1.7x** - the gap, today, with zero gating credit taken
  - (small print) at DDR5's spec-limit ceiling (1.008 W) the gap narrows
    to 1.11x - a secondary bound, not the headline
- Say: this is the honest baseline number - no gating credit taken yet.

**Slide 30 - The path to parity (explicitly unsimulated)** *(number
callouts + badge, no chart)*
- On-slide, prominent badge: "NOT YET SIMULATED - TOP FUTURE-WORK ITEM"
  - **43%** idle time needed to break even with DDR5's floor
  - **90%** idle time (plausible for web-serving deployments, per
    published Bing/Cosmos utilization data) → ~0.14 W, ~4.5x below the
    DDR5 floor
  - Both numbers are back-of-envelope arithmetic on measured static
    power, not a simulated gating policy
- Say: name this as a projection out loud. Advisors respect "here's what
  I haven't shown yet" far more than an unlabeled leap.

**Slide 31 - Summary table** *(table, no chart)*
- On-slide footnote added: "*128 GB lifetime is a linear-scaling
  projection from the physically simulated 8 GB (SLC) / 16 GB (MLC)
  capacity - no 64 GB or 128 GB configuration was separately built or
  run."

| Technology | GCC latency | Power | Geo-mean PDP | Density (×DDR5) | Lifetime @128GB* | Role |
|---|---|---|---|---|---|---|
| DDR5-4800 | 87 ns | 0.651 W | 104 | 1.00 | n/a (volatile) | commodity baseline |
| PCM | 6,399 ns | 0.040 W | 165 | 1.25 | not evaluated | floor-power niche, 4-49x latency cost |
| 1T1R SLC | 131 ns | 50.9 W | 21,351 | 0.22 | 17.3 yr | latency-only niche, infeasible ungated |
| **1S1R SLC** | 190 ns | 1.12 W | 737 | 1.92 | 24.8 yr | **highest-potential candidate - power parity contingent on future gating work** |
| 1T1R MLC | 183 ns | 50.9 W | 32,567 | 0.44 | 3.1 yr | infeasible ungated |
| 1S1R MLC | 289 ns | 1.13 W | 1,222 | 3.84 | 5.2 yr | read-only capacity tier (frozen weights) |

- Say: this is the whole evaluation on one slide. Note the 1S1R SLC role
  wording deliberately does not say "flagship, one policy from parity" -
  that's the book's current wording, and it's what's changing.

---

## 5. Contributions (2 slides, ~4 min)

**Slide 32 - What this delivers**
- On-slide: (1) an open-sourced NVSim→NVMain cross-layer pipeline for
  ReRAM DIMM evaluation, (2) a 14-item toolchain fidelity audit -
  reusable beyond this project's own numbers

**Slide 33 - The one-sentence takeaway**
- On-slide: "1S1R ReRAM is latency-competitive and density-superior for
  compute-bound and moderate workloads today, with a credible but
  unproven path to power parity via idle-gating; 1T1R is a latency-only
  niche; AI-inference serving stays DDR5 territory for now."

---

## 6. Future Work (3 slides, ~4 min)

**Slide 34 - Top priority, next 3 months**
- On-slide: idle-gating itself is already restored and mechanically
  live (Section 3.1.6) - the one thing still missing is a real ReRAM
  power-gating characterization (what fraction of its leakage is
  peripheral/gatable, at what entry/exit energy cost), now the single
  highest-leverage next step and a literature/analysis task, not new
  simulation infrastructure. Added: alongside it in the same 3-month
  window, an Interface Parity evaluation (dual-channel/faster-PHY
  ReRAM) - closes part of the 4.6x AI-inference latency gap, an
  already-flagged available mitigation, not a hidden cost.
- Say: if asked why ReRAM's power number didn't move even after
  idle-gating was restored - the mechanism is live (86-89% of
  cycle-slots gated, confirmed), but no NVSim datapoint or literature
  source splits ReRAM leakage into gatable-vs-ungatable, so its
  power-down energy is an honest zero-savings placeholder pending real
  characterization - exactly this priority. PCM separately shows zero
  power-down activity in either run, plausibly its FRFCFS-WQF
  controller keeping the request queue non-empty; a second, smaller
  open item, not yet root-caused.

**Slide 35 - Beyond 3 months, by theme**
- On-slide, ordered by amount-of-work per theme (largest first, per
  the Lead's own prioritization): **Architectural scaling & density**
  (recessed-channel 1T1R density - could overturn the density verdict
  · macro-scale 1T1R array limits beyond the 1024x1024 baseline-parity
  restriction · L3 cache/write-buffer mitigation for ReRAM writes ·
  node scaling + 3D deck stacking · endurance-aware wear-leveling) →
  **Model fidelity** (Native MLC Logic - resolve NVSim's Mat.cpp
  floating-point exception · PCM's zero power-down activity, not yet
  root-caused · ReadVoltage/WritePulseWidth parameter-optimization
  sweep) → **Validation** (standalone device-to-system simulator
  wrapper - generalizing "The Bridge," idea originated in discussion
  with the HW/SW co-design course tutor · FPGA-based hardware-in-the-
  loop validation of the idle-gating policy, closes the internal-only
  validation gap without needing fabricated ReRAM silicon).
- Note: the former "Memory Controller Queue Analysis (Flatline
  Paradox)" future-work item was removed here and from
  `Project_Book.typ` §4.2 - it's now resolved (see T4-11, Section 3.2 /
  Appendix A: an address-footprint/rank-mapping artifact, not a queue-
  depth question), so it no longer belongs in future work.

---

## 7. Close (1 slide, ~1 min)

**Slide 36 - Thank you / Questions**

---

## Backup slides (prepare, don't present unless asked)

- Full 14-item fidelity audit list
- ReadVoltage sensitivity sweep (±20%, PDP change <4%)
- Worst-case-stacking explanation (DDR5 spec-limit vs typical - confirmed
  no typical figure exists in any datasheet checked; ReRAM's power-down
  mechanism now live but an honest zero-savings placeholder; DDR5 now
  gets a real measured power-down credit ReRAM doesn't, so the
  comparison no longer uniformly favors ReRAM) - have this ready, it's
  the most likely hard question
- References Used on the Slides: resolves every [N] bracket now appearing
  on main slides (47x-fact, SLC/MLC, Bridge-in-parameters) - [3] NVSim,
  [4] NVMain, [6]/[31] EMBER, [7] resistance targets, [33] recessed-channel
- 2026-09-02 (Lead-caught): both the "Full 14-item fidelity audit" list
  and "References Used on the Slides" (grown to 10 and 9 items
  respectively as items were added over this session) overflowed the
  fixed slide height - Lead reported the References slide's title
  pushed above the visible viewport and its last item clipped at the
  bottom, confirmed via screenshot. A single-column width fix (as used
  on the earlier "I Audited My Own Toolchain" slide) wasn't enough for
  lists this long - switched both to a genuine 2-column CSS grid
  (`display:grid; grid-template-columns:1fr 1fr`) instead of the
  flex-column default, roughly halving the vertical height needed for
  the same content. Re-verified overlap-free via screenshot on both.
- New: Section B divider "Progress Since Last Presented" + 2 slides, added
  2026-09-02 for the Shahar meeting specifically (not backup-only in
  spirit - usable to open the meeting or answer "what changed" if asked
  first): (1) since `MBMM Project Book UPDATED.docx` (last version
  presented) - fidelity audit deepened 11/9 found/repaired to 14/12, the
  DDR5 CAS-RCD-RP timing and ReRAM MLC-multiplier fixes, new Section 1.3
  Related Work, references 30->41, 128GB 1T1R SLC lifetime 24.4->17.3yr,
  headline verdict unchanged; (2) since the SysTOR poster - the poster's
  numbers held up under re-verification (2.3x latency, ~25yr@128GB both
  match), what's new is the explicit measured-vs-projected disclosure
  layer (only 8/16GB was ever physically simulated) and the audit
  narrative growing from the poster's implicit lineage to a documented
  14/12. Exact positions: Slide 49 (divider), Slide 50 (Backup 1/2,
  Since the Last Book Version), Slide 51 (Backup 2/2, Since the SysTOR
  Poster).
- 2026-09-02 (Lead-caught): Slides 50 and 51 each originally carried an
  intro/closing lede, 5 long multi-clause bullets, and a 3-4 sentence
  speaker note - genuinely overflowed the fixed slide height (title
  clipped, closing lede and speaker note rendered on top of each
  other), confirmed via headless-Chrome screenshots at both slides
  (not just a section/div count check, which stayed balanced throughout
  and caught nothing). Fixed by trimming every bullet to one compact
  line, dropping the intro lede and speaker note on both slides
  entirely (matching the plain "bullets + one short lede" shape the
  deck's other backup slides already use), and keeping only one closing
  lede line each. All facts preserved, no content removed - only
  compressed. Re-verified overlap-free via screenshot after the fix.

---

## 2026-09-05 additions: Item 7 fully resolved (idle-gating restoration folded in)

Following the mechanism restoration and full 36-run re-run (see `Review_Fixes_Tracker.md`),
every slide touching DDR5's power/latency or ReRAM's PDP was updated with the real new numbers:
**"Full-Module Power"** (retitled "Idle-Gating Restored," DDR5 0.651→0.623 W, chart regenerated),
**"Power-Delay Product"** (geomean chart regenerated: DDR5 104→103, 1T1R 21,351→21,508, 1S1R
737→738), **"Path to Power Parity"** (badge/break-even updated 43%→46%, ratios updated),
**"Where This Stands Today"** (1.7×→1.8× gap stat), **"Compute-Bound: the Closest Gap"** (chart
regenerated: 87/131/190 ns → 90/136/192 ns - caught via screenshot that the chart image itself
was still showing the old numbers after the bullet text was updated), **"Streaming: the Honest
Number"** (chart regenerated with new DDR5/ReRAM latencies), **"The Whole Evaluation, One Slide"**
(DDR5 and all 4 ReRAM rows updated to match Table 7). Underlying chart regeneration used
`visualize_slides.py` against the live re-run data (`results/processed_*.csv`), with 5 stale
titles/footnotes ("ungated," "not yet simulated") corrected in the script itself. Re-verified
deck section/div balance (51/51, 248/248) and re-screenshotted every touched slide overlap-free.

## 2026-09-05 additions: T4-11 fully resolved (Flatline/Scaling contradiction)

**"Compute-Bound Scaling: A Real, Modest Gain"** and **"AI-Inference Is the Actual Flatline"**
(deck slides 29-30, no dedicated per-slide entry above - added post-renumbering in the
2026-09-02 T4-11 deck-only patch): the deck-only patch from that session correctly stated the
real numbers but left the ROOT CAUSE as an open question ("flagged as an open question, not yet
explained"). Root-caused this session via fresh experiments (queue-depth x chip-count sweep,
address-footprint analysis against real NVMain source) - it's a workload address-footprint /
rank-mapping artifact, not MLP or a queueing effect. Updated both slides' bullets and speaker
notes to state the resolved cause, and - the actual remaining gap - regenerated the two
embedded chart images themselves via `visualize_slides.py` (`slide_pareto_gcc`/`slide_pareto_gpt2`,
which had hardcoded stale titles "The Flatline Paradox: no MLP, no benefit from scaling" /
"Breaking the flatline: high-MLP workloads reward scaling" baked into the matplotlib figure -
missed in the original deck-only patch since these are base64-embedded images, not text). Book's
`Project_Book.typ` §3.2 rewritten to match (see `Review_Fixes_Tracker.md`), plus a new Appendix A
entry with the full root-cause methodology. Re-verified overlap-free via screenshot on both
slides after the chart swap.

## 2026-09-05 additions (Shahar-notes items 1, 2, 3&9, 8, overarching)

- **"The Whole Evaluation, One Slide"** (summary table, no dedicated per-slide entry above):
  PCM's `Lifetime@128GB` cell changed from bare `N/A` to `N/A†` with a footnote ("PCM endurance
  not modeled in this study - scope was ReRAM lifetime projection") - same item 1 fix as Slide 7's
  Cell Size cell, applied to this slide's own N/A instance.
- **§1.3 Related Work / positioning** (no dedicated deck slide - this is a book-only fix, item
  3&9): added real Optane DC PMM measured numbers (305 ns idle random-read latency vs. 81 ns
  local DRAM; 6.6 GB/s read / 2.3 GB/s write single-DIMM bandwidth, both from Izraelevitz et al.
  [32]) to `Project_Book.typ` alongside the existing qualitative Optane discussion - explicitly
  marked as the field's one real-hardware anchor point, distinct from every simulated result.
- Re-verified deck section/div balance (51/51, 248/248) and re-screenshotted every touched slide
  (Slides 7/10 numbering, and the Whole Evaluation summary slide) overlap-free after all of the
  above 2026-09-05 changes.

## Open items before this is fully locked

All items below are resolved as of 2026-08-31 - kept here as a record,
not a live TODO list. Book edits from `Presentation_Fixes_Tracker.md`
were applied 2026-08-23 (see `Review_Fixes_Tracker.md` NOTICES). The
Slide 9 pipeline diagram and Slide 10 numbers-at-a-glance slide are both
built directly in the deck (HTML/CSS, no chart script) as of the T4-2
meeting-prep pass. Slide 7's cast-of-characters table was already a
real table, not a placeholder.
