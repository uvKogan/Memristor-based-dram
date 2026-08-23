# Presentation Outline — MBMM (22nm ReRAM as Commodity Main Memory)

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
scoped to compute-bound with the 1.9-2.1x penalty disclosed) — book and
talk now say the same thing. Canonical fix status lives in
`Review_Fixes_Tracker.md`.

**Figures:** all chart slides are generated — see `visualize_slides.py`
(repo root) and `results/slide_graphs/*.png`. Every chart tag below now
points at its actual file. Regenerate anytime with
`python3 visualize_slides.py`. Diagrams/tables with no file tag are
text/number slides — no chart needed.

Target: ~35 slides, ~1.7 min/slide average.

---

## 0. Title (1 slide, 0.5 min)

**Slide:** Title, your name, advisor, date, one-line subtitle: "Can 22nm
ReRAM replace DDR5 in a commodity DIMM?"

---

## 1. Motivation (4 slides, ~6 min)

**Slide 1 — The memory supply-demand crisis**
- On-slide: 1-2 stats on DRAM wafer reallocation to HBM (late 2025), one
  chart/timeline if available
- Say: DRAM capacity is being pulled toward AI/HBM; commodity main memory
  is getting squeezed. That's the market pressure motivating alternatives.

**Slide 2 — Why ReRAM as a candidate**
- On-slide: non-volatile (zero refresh) · higher density potential ·
  logic-compatible process
- Say: the pitch is refresh elimination and density — but endurance is
  the classic objection, flag it now so it doesn't feel dodged later.

**Slide 3 — The research question**
- On-slide: "Device-level ReRAM is well studied. System-level, commodity-
  DIMM behavior under real workloads is not."
- Say: most ReRAM literature stops at the cell or macro. This project asks
  the system question — what happens when you put it in a DIMM behind a
  memory controller and run real traces through it.

**Slide 4 — What this project actually built**
- On-slide: cross-layer pipeline, NVSim (device) → NVMain (system),
  driven by real gem5/SCALE-Sim traces, 20 configs × 6 workloads
- Say: this is the specific, concrete thing being evaluated — sets up
  Background/Methodology without overclaiming novelty over unnamed prior
  system-level work (there's no formal related-work section yet — say
  "system-level, cross-layer, workload-driven" as the specific angle,
  not "first ever").

---

## 2. Background (4 slides, ~6 min — audience knows memristors, so skip device physics 101)

**Slide 5 — 1T1R vs 1S1R, in one breath**
- On-slide: 1T1R = transistor-gated, no sneak paths, bigger cell (20F²
  planar) · 1S1R = selector-gated, smaller cell (4F²), slower access
- Say: one sentence recap since the audience already has this; then land
  on why cell area *isn't* a fixed constant — it's architecture-dependent
  (recessed-channel demo hits 6F², footnote for the density slide later).

**Slide 6 — SLC vs MLC**
- On-slide: SLC = 1 bit/cell · MLC = 2+ bits/cell via ISPV programming →
  write-latency penalty
- Say: NVSim can't natively simulate MLC's iterative sensing (it crashes
  on it), so this project derived an analytical penalty method from two
  independent EMBER macro papers instead — sets up a methodology slide.

**Slide 7 — The cast of characters**
- On-slide: table — DDR5-4800 (baseline), PCM (legacy NVM baseline),
  1T1R SLC/MLC, 1S1R SLC/MLC — one row each, cell size + role
- Say: six configurations, this is what gets compared for the rest of
  the talk.

**Slide 8 — Where this sits**
- On-slide: device-level ReRAM literature = extensive · system-level,
  DIMM-scale, workload-driven evaluation = the gap this fills
- Say: honest positioning — acknowledges you haven't done a formal
  literature survey slide, but states the angle precisely.

---

## 3. Methodology (6 slides, ~10 min)

**Slide 9 — The pipeline**
- On-slide: diagram — NVSim (device chars) → JSON → NVMain config →
  cycle-accurate trace execution
- New diagram, not a report figure. Say: this bridge is itself a
  contribution — most tools stop at one layer or the other.

**Slide 10 — Real workloads, not synthetic averages**
- On-slide: table — GCC (compute-bound) · LBM (streaming) · STREAM
  (bandwidth) · AlexNet IFMAP/OFMAP (read/write storm) · GPT-2 (AI
  parallel read)
- Say: six traces chosen to bracket the workload space, from idle-mostly
  to fully saturating.

**Slide 11 — Baselines**
- On-slide: DDR5-4800 modeled to JEDEC spec · legacy PCM baseline for
  historical NVM context
- Say: DDR5 is the real target to beat; PCM shows how far NVM has come.

**Slide 12 — We audited our own toolchain**
- On-slide: "14 silent failure modes found in the standard NVSim→NVMain
  flow; 12 repaired and validated" — pick 3 illustrative ones (disabled
  power-down model, DDR3-era refresh params inherited unscaled, unsourced
  MLC multipliers)
- Say: this is a genuine strength — present it as rigor, not confession.

**Slide 13 — What "validated" means here (limitation, stated upfront)**
- On-slide: "Validation = internal consistency (NVMain matches NVSim to
  0.0% error), NOT external silicon validation" — one clean caveat
- Say: be the one who raises this before someone in the audience does.

**Slide 14 — Assumptions that shape every result that follows**
- On-slide: 4 bullets — gem5 traces are uncached (max memory pressure) ·
  GPT-2 trace provenance unverified · DDR5 power = datasheet spec-limit,
  not typical · ReRAM power = worst-case, gating not yet simulated
- Say: read every number in the next 25 minutes through this lens — this
  slide is the fix for "caveats surfacing too late."

---

## 4. Results (15 slides, ~28 min)

### Latency (4 slides)
**Slide 15 — Compute-bound: the closest gap**
`results/slide_graphs/15_latency_gcc.png`
- On-slide: 1T1R SLC 131 ns vs DDR5 87 ns — 1.5x, smallest gap in
  the suite

**Slide 16 — Streaming: the honest number**
`results/slide_graphs/16_streaming_honest.png`
- On-slide: STREAM latency (DDR5/1T1R SLC/1S1R SLC, 1.9-2.1x DDR5) next
  to LBM completion rate (100% → 40% → 28% → 16% → 9% → 4%)
- Say: the book was updated 2026-08-23 to match this framing
  (compute-bound, streaming penalty disclosed) — the completion panel is the point: 1T1R only finishes 40% of
  what DDR5 finishes in the same window, so the reported latency ratio
  understates the real gap. Streaming is the weakest regime, say so
  plainly.

**Slide 17 — AI inference: DDR5 wins**
`results/slide_graphs/17_latency_gpt2.png`
- On-slide: 4.6x DDR5 under GPT-2 parallel read-storm; small-print
  caveat baked into the chart footnote: GPT-2 trace provenance
  unverified, treat as representative stress pattern
- Say: no hedging — DDR5 territory today for high-parallelism serving.

**Slide 18 — The MLC write tax**
`results/slide_graphs/18_mlc_write_penalty.png`
- On-slide: 1S1R MLC OFMAP latency = 2x its SLC sibling; MLC → read-
  mostly applications only

### Power (3 slides)
**Slide 19 — The 47x fact**
`results/slide_graphs/19_device_leakage.png`
- On-slide: device-level leakage, 1T1R 795 mW/chip vs 1S1R 17 mW/chip
  — the single number that decides everything downstream
- Say: this is the fact the whole power story hangs on.

**Slide 20 — Full-module power**
`results/slide_graphs/20_module_power.png`
- On-slide: 1T1R 50.9 W (infeasible) · 1S1R 1.12 W · DDR5 0.651 W ·
  PCM 0.040 W

**Slide 21 — Power-Delay Product**
`results/slide_graphs/21_pdp_geomean.png`
- On-slide: 1S1R beats 1T1R by ~29-31x; DDR5 still ~3.7-5x ahead of
  ungated 1S1R

### Scaling (2 slides)
**Slide 22 — The Flatline Paradox**
`results/slide_graphs/22_pareto_gcc.png`
- On-slide: low-MLP workloads gain zero latency from more ranks — just
  pay linear leakage for capacity you can't use

**Slide 23 — Breaking the flatline**
`results/slide_graphs/23_pareto_gpt2.png`
- On-slide: high-MLP AI workloads DO benefit from rank interleaving —
  parallelism is the precondition, not chip count alone

### Global viability / density (3 slides)
**Slide 24 — Density**
`results/slide_graphs/24_density.png`
- On-slide: 1S1R SLC 1.92x DDR5 density (3.84x MLC) · 1T1R 0.22x — cell
  area, not node, decides this; footnote: 20F² isn't a hard ceiling
  (6F² recessed-channel demo exists, real device-physics work needed to
  close that gap)

**Slide 25 — Scaling projections (clearly labeled)**
`results/slide_graphs/25_density_projection.png`
- On-slide: 12-16nm + 3D deck-stacking projections, big "PROJECTED — NOT
  MEASURED" badge baked into the chart itself

**Slide 26 — Endurance**
`results/slide_graphs/26_endurance.png`
- On-slide: 8 GB module @ worst-case streaming = 1.1 yr (below the 5-10
  yr target) · 64 GB = 8.7-9 yr (clears it) · every other workload clears
  it by 20x+ even at 8 GB · caveat baked into chart: assumes ideal wear
  leveling, no controller implemented yet

### The flagship claim — reframed (3 slides, the most important section)
**Slide 27 — Where this stands today** *(number callouts, no chart)*
- On-slide, three big stat callouts:
  - **1.12 W** — 1S1R SLC, full module, ungated
  - **0.651 W** — DDR5-4800, conservative calibration floor
  - **1.7x** — the gap, today, with zero gating credit taken
  - (small print) at DDR5's spec-limit ceiling (1.008 W) the gap narrows
    to 1.11x — a secondary bound, not the headline
- Say: this is the honest baseline number — no gating credit taken yet.

**Slide 28 — The path to parity (explicitly unsimulated)** *(number
callouts + badge, no chart)*
- On-slide, prominent badge: "NOT YET SIMULATED — TOP FUTURE-WORK ITEM"
  - **43%** idle time needed to break even with DDR5's floor
  - **90%** idle time (plausible for web-serving deployments, per
    published Bing/Cosmos utilization data) → ~0.14 W, ~4.5x below the
    DDR5 floor
  - Both numbers are back-of-envelope arithmetic on measured static
    power, not a simulated gating policy
- Say: name this as a projection out loud. Advisors respect "here's what
  I haven't shown yet" far more than an unlabeled leap.

**Slide 29 — Summary table** *(table, no chart)*

| Technology | GCC latency | Power | Geo-mean PDP | Density (×DDR5) | Lifetime @128GB | Role |
|---|---|---|---|---|---|---|
| DDR5-4800 | 87 ns | 0.651 W | 104 | 1.00 | n/a (volatile) | commodity baseline |
| PCM | 6,399 ns | 0.040 W | 165 | 1.25 | not evaluated | floor-power niche, 4-49x latency cost |
| 1T1R SLC | 131 ns | 50.9 W | 21,351 | 0.22 | 17.3 yr | latency-only niche, infeasible ungated |
| **1S1R SLC** | 190 ns | 1.12 W | 737 | 1.92 | 24.8 yr | **highest-potential candidate — power parity contingent on future gating work** |
| 1T1R MLC | 183 ns | 50.9 W | 32,567 | 0.44 | 3.1 yr | infeasible ungated |
| 1S1R MLC | 289 ns | 1.13 W | 1,222 | 3.84 | 5.2 yr | read-only capacity tier (frozen weights) |

- Say: this is the whole evaluation on one slide. Note the 1S1R SLC role
  wording deliberately does not say "flagship, one policy from parity" —
  that's the book's current wording, and it's what's changing.

---

## 5. Contributions (2 slides, ~4 min)

**Slide 30 — What this delivers**
- On-slide: (1) an open-sourced NVSim→NVMain cross-layer pipeline for
  ReRAM DIMM evaluation, (2) a 14-item toolchain fidelity audit —
  reusable beyond this project's own numbers

**Slide 31 — The one-sentence takeaway**
- On-slide: "1S1R ReRAM is latency-competitive and density-superior for
  compute-bound and moderate workloads today, with a credible but
  unproven path to power parity via idle-gating; 1T1R is a latency-only
  niche; AI-inference serving stays DDR5 territory for now."

---

## 6. Future Work (3 slides, ~4 min)

**Slide 32 — Top priority: restore idle-gating simulation**
- On-slide: this is what converts Slide 28's projection into a real
  result — the single highest-leverage next step

**Slide 33 — Other fronts**
- On-slide: wear-leveling controller / write-coalescing cache ·
  recessed-channel 1T1R density (could overturn the density verdict) ·
  node scaling + 3D deck stacking

---

## 7. Close (1 slide, ~1 min)

**Slide 34 — Thank you / Questions**

---

## Backup slides (prepare, don't present unless asked)

- Full 14-item fidelity audit list
- ReadVoltage sensitivity sweep (±20%, PDP change <4%)
- Worst-case-stacking explanation (DDR5 spec-limit vs typical, ReRAM
  ungated) — have this ready, it's the most likely hard question
- Device-level literature ReRAM sits within (citations from the book's
  bibliography)

---

## Open items before this is fully locked

1. **Book edits** — `Presentation_Fixes_Tracker.md` lists what should
   change in `Project_Book.typ` to match this talk's honest framing;
   not yet applied.
2. **Slide 9 pipeline diagram** and **Slide 7 cast-of-characters table**
   are still text placeholders in this doc — no chart script produces
   them since they're structural, not data, visuals. Build directly in
   the deck.
