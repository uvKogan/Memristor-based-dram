# Meeting Notes: Shahar Kvatinsky Review - 2026-09-03

Status: **baseline for the next revision pass** on `Project_Book.typ`, `presentation_deck.html`,
and (where a config/simulation change is implied) the pipeline itself. Each item below is RAW
(Shahar's note, cleaned up for readability but not reinterpreted) followed by IMPROVED
(grounded in what the book/deck/configs actually say today, checked against the source files
during this session, with concrete pointers for the fix). **RESOLVED: overarching framing, items
1, 2, 3&9, 5, 6, 7, 10** (2026-09-04/05) - see each item's note below. **Item 4/T4-10 partially
resolved**: research confirmed no DDR5 "typical" IDD figure exists anywhere (vendors only publish
worst-case max, by JEDEC design) - the book's existing disclosure was already correct; DDR5's
dead EIDD6 placeholder was corrected to a real sourced value regardless, no simulated result
moves. **Item 8** partially resolved: calculation now shown on-slide; the 10⁷-vs-10⁹
Shahar-reconciliation still needs a live conversation, not a book fix (the only remaining item
that genuinely can't be closed from a desk). Everything else from this baseline is now closed.

## Overarching conclusion

**RAW:** Every memory system is described by three axes - latency, density, and endurance. We
must address all three, explicitly, everywhere in the book and the deck.

**IMPROVED:** The book already implicitly organizes around these three axes (§3.1.1 latency,
§3.1.4 endurance, §3.3 density) plus power, but no single slide or section states this framing
as the evaluation's organizing principle up front. Recommendation: add an explicit "we judge
every technology on three axes: latency, density, endurance" framing early in both documents
(book: end of Introduction/§1; deck: right after "The Cast of Characters"), and use it as the
checklist against which every technology's verdict gets stated (this also gives a natural home
for admitting when one axis is *not* evaluated for a technology - see item 1, PCM's density row).

**RESOLVED (2026-09-05):** framing statement added to `Project_Book.typ` §1.3 and the deck's
"Cast of Characters" slide, exactly as recommended above.

---

## 1. PCM's cell architecture is not "N/A" - it's commonly 1S1R

**RAW:** PCM IS 1S1R - it is described as N/A in one of the slides. We need to address it
correctly.

**IMPROVED:** Confirmed in the deck - two separate `N/A` cells, and they are two different
problems:

- Slide "The Cast of Characters" (`presentation_deck.html` ~line 433): the table lists
  DDR5=6F², **PCM (legacy)=N/A**, 1T1R=20F², 1S1R=4F². This `N/A` reads as "PCM has no
  applicable cell architecture," which is wrong - real PCM, and specifically Intel/Micron's
  shipped 3D XPoint/Optane, is a **selector-gated (OTS - Ovonic Threshold Switch) cross-point
  design**, i.e. architecturally a 1S1R device, not a bare cell with nothing to categorize.
- Slide "The Whole Evaluation, One Slide" (~line 771): PCM's `Lifetime@128GB` = `N/A`. This one
  is more defensible (endurance was never projected for PCM in this study - only ReRAM went
  through the Table-5-style lifetime projection), but it still needs a footnote, not a bare N/A.

Root cause, checked directly: `Project_Book.typ` **never once states what access/selector
device the study's PCM baseline uses** (grepped for PCM + 1T1R/1S1R/transistor/selector/
diode/ovonic/OTS - zero hits). The PCM baseline comes from NVMain's stock
`pcm_microsoft_2009.config` / `PCM_MLC_estimated.config`, inherited as a black-box timing/power
baseline, with its cell architecture never characterized. So the deck's `N/A` isn't a labeling
slip - it's an honest reflection of a real gap: **this project never disclosed what PCM's
cell architecture is, or explicitly justified excluding it from the F² density comparison.**

**RESOLVED (2026-09-05):** `Project_Book.typ` §2.3 now states plainly that neither the PCM
baseline's inherited config nor its cited source papers specify an access-device architecture -
it's a black-box timing/energy model, not a characterization of any specific cell topology -
distinct from the real shipped product (Optane/3D XPoint), confirmed 1S1R cross-point via a
genuine primary source (Kau et al., IEDM 2009, new ref [42]). Deck's `N/A` cells (both "Cast of
Characters" and the summary slide) replaced with footnoted `n/s`/`N/A†`.

Action items for the next pass (superseded by RESOLVED above, kept for the record):
- Book: add a sentence in §2.1/§1 explicitly stating the PCM baseline's device architecture
  (transistor-gated, per the microprocessor-era config it's inherited from) and, separately,
  that *real-world modern PCM* (Optane/3D XPoint) is selector-gated cross-point - already have
  refs [23] (Optane exit) and [32] (Optane DC PMM measurements) in the bibliography for this.
- Deck: replace the bare `N/A` in "The Cast of Characters" with either a real F² figure for
  cross-point PCM (needs a citation - see item 9) or an explicit label like "1T1R-style
  (this study) / 1S1R cross-point (Optane, real product)" so it reads as a disclosed scope
  choice, not a missing fact.
- Add a one-line footnote to the `Lifetime@128GB = N/A` PCM row: "endurance not modeled for
  PCM in this study - scope was ReRAM lifetime projection."

---

## 2. The 800 MHz ReRAM clock is literally 2x a ~2009 PCM number, not an independent ReRAM figure

**RAW:** 800 MHz? If we chose it because of the 400 MHz of the PCM - it is almost 20-year-old
research...

**IMPROVED:** Confirmed exactly as suspected - this is real, not a misreading. `Project_Book.typ`
line 464 states the 800 MHz ReRAM interface was chosen as "twice... the 400 MHz basis of
NVMain's PCM reference lineage **[11]**." Reference [11] is:

> B. C. Lee, E. Ipek, O. Mutlu, and D. Burger, "Architecting phase change memory as a scalable
> DRAM alternative," ISCA 2009.

That's 17 years old as of 2026 (Shahar's "almost 20 years" is a fair characterization) - and
it's a *PCM* paper, not a ReRAM paper. The fidelity audit (item 9 in §3.1.6) independently
confirms the PCM baseline's own timings are calibrated to that same 400 MHz/Lee-et-al. basis,
and that ReRAM's 800 MHz was a **deliberate 2x multiple of it**, not a figure independently
sourced from ReRAM device/interface literature.

This is a real, defensible-but-thin methodological choice ("positioned between PCM's known
basis and DDR5's much faster PHY," per the existing deck speaker-note on slide "One Chip → a
Full DIMM") but it currently has **no independent ReRAM-interface citation** backing the 800 MHz
number itself - only an arithmetic relationship to a 2009 PCM paper.

Action items:
- Find a ReRAM-specific interface/PHY speed citation (look at EMBER [6]/[31], already used for
  MLC characterization - check if either states an achievable interface clock; also check
  ISSCC ReRAM prototypes like Crossbar [9] or Xue et al. [8] for reported I/O rates).
- If no independent ReRAM interface citation exists, say so explicitly in the book rather than
  letting the "2x PCM" derivation stand implicitly - e.g. "800 MHz was chosen as a deliberate,
  arbitrary interface target between PCM's established 400 MHz basis and DDR5's PHY, pending a
  ReRAM-specific interface characterization; this is flagged as a modeling assumption, not a
  literature-derived number."
- This also feeds the already-known future-work item (dual-channel/faster-PHY ReRAM, logged in
  a prior session's tracker note) - worth cross-referencing there once §4 is revised.

**RESOLVED (2026-09-05):** no independent ReRAM interface citation exists - confirmed via
`/research` (`research_notes/item2_reram_interface_speed.md`). EMBER's "100 MHz" is an internal
sense/write clock, not an interface rate. The only real ReRAM chip I/O clocks found (Fujitsu SPI
parts, 5-10 MHz) actively contradict 800 MHz rather than support it. `Project_Book.typ` §1.3 now
states this explicitly as a disclosed modeling assumption; deck speaker note updated to match.

---

## 3 & 9. Intel Optane (3D XPoint) - the real PCM product - is cited but never actually engaged with

**RAW (3):** How didn't I even mention Intel's Optane? It's their PCM product, we did not even
take a look at it.
**RAW (9):** Optane is a better PCM - we must look at it.

**IMPROVED:** Optane is already in the bibliography ([23] Tom's Hardware, Optane business exit;
[32] Izraelevitz et al., "Basic Performance Measurements of the Intel Optane DC PMM," arXiv 2019)
and gets one sentence each in §1 (discontinuation precedent) and the 800 MHz rationale (Optane's
DDR-T interface as an upper reference point) - but it is **never used as a data point**: no
Optane latency/power/endurance numbers appear anywhere in the results, comparison tables, or the
deck. Given it's the only NVM main-memory module ever actually shipped (the book says so itself,
line ~290), that's a real gap - it's the single best piece of real-world ground truth available
for the entire study, and it's sitting unused in the reference list.

**RESOLVED (2026-09-05):** `/research` (`research_notes/item3_9_optane_real_numbers.md`) pulled
real measured numbers (305 ns idle random-read latency vs. 81 ns local DRAM; 6.6/2.3 GB/s
single-DIMM read/write bandwidth) and confirmed the 1S1R/OTS cross-point architecture via a
genuine primary source (Kau et al., IEDM 2009, new ref [42]). Added to `Project_Book.typ` §1.3,
explicitly marked as the field's one real-hardware anchor point. A die-area/cell-size figure was
also found (via a professional teardown) but is a third-party estimate, not Intel-confirmed - not
used for any precise density claim, per the research file's own caveat.

Action items (superseded by RESOLVED above, kept for the record):
- Pull real numbers from [32] (Izraelevitz et al. measured Optane DC PMM latency/bandwidth on
  real hardware) and add them as a labeled "real hardware" row/point on the relevant latency and
  power comparisons - explicitly marked as measured-on-real-silicon vs. this study's simulated
  numbers, since that distinction (sim vs. real) is itself a disclosed limitation worth
  reinforcing with an actual anchor point.
- Use Optane's real cross-point (1S1R/OTS) architecture as the citation needed for item 1's density
  fix - if [32] or a follow-up Optane paper reports die area / cell size, that closes the "PCM
  cell size = N/A" gap with a real number instead of a placeholder.
- Frame explicitly in the book: "this study's PCM baseline is a generic 1T1R-style timing model
  from 2009-era literature, not a characterization of Optane; Optane is presented separately as
  the real-world reference point."

---

## 4. DDR5 numbers must be compared against typical operation, not only worst-case datasheet limits

**RAW:** DDR5 numbers - we need to compare to typical and not worst case, real world is not
working on worst case.

**IMPROVED:** Already partially disclosed (confirmed, fidelity item 8, §3.1.6): every DDR5 IDD
current used in this study comes from **vendor datasheet spec-limit values** (SK hynix as the
"conservative floor," Micron as the "ceiling"), with an explicit caveat already in the book that
"datasheet IDD values are specification limits rather than typicals." So the book already knows
and says this - but it stops at disclosure; it never goes and gets an actual typical number. This
is the same gap already logged in a prior session as an open tracker residual (real DDR5 IDD6/
typical datasheet value, not yet added).

Shahar's framing sharpens the priority: this isn't a nice-to-have footnote fix, it changes the
power-parity headline. Since all current DDR5 numbers are ceiling/floor spec limits (not
measured typicals), the true gap between ReRAM and real-world DDR5 power is **likely wider than
currently reported**, not narrower - worth stating as a takeaway, not just a caveat.

**PARTIALLY RESOLVED (2026-09-05):** `/research` (`research_notes/item4_ddr5_typical_current.md`)
checked every Micron and SK hynix DDR5 datasheet reachable and found **no typical/nominal IDD
column exists anywhere** - every datasheet labels its sole IDD column "Current Limits"/"Maximum
values...worst-case." A 2017 JEDEC JC42.3 ballot draft confirms this is by design: the standard's
own template defines only a numeric "IDD Max" column, with typical reporting merely optional
for IDD6E/IDD6A specifically (and not exercised by either vendor here). **So the book's existing
"spec limits, not typicals" disclosure is confirmed accurate, and Shahar's "likely wider gap"
takeaway stands as stated - there is no real typical figure to add**, because vendors don't
publish one. The one concrete fix that WAS possible: `DDR5_4800_DRAM_micron.config`'s `EIDD6`
(self-refresh) corrected from an unsourced 12mA placeholder to Micron's own real, already-cited
[29] value (IDD6N=102mA) - a documentation-accuracy fix only, since EIDD6 is confirmed dead
(never read by any energy formula) and no simulated number moves. No SK hynix IDD6 counterpart
could be confirmed. The "Path to Power Parity" reframing action item below is superseded by
Workstream C (idle-gating restoration) once that lands, since that section will be replaced by
real simulated numbers rather than projected arithmetic - not addressed separately here.

Action items (mostly superseded by RESOLVED above, kept for the record):
- Source a real "typical operating current" figure - JEDEC IDD specs distinguish IDD (typical)
  from IDD-max; vendor datasheets (Micron, SK hynix - already cited as [29]/[30]) may separately
  publish typical/nominal current alongside the spec-limit table already used.
- Add a third column/row to the power comparison: spec-floor / spec-ceiling / typical (if
  found), so the book shows the full band rather than implying the two extremes are the whole
  picture.
- Update the "Path to Power Parity" framing to state directly: "parity is claimed against DDR5's
  worst-case datasheet floor; against typical DDR5 operation the gap is larger."

---

## 5. LBM's incomplete-workload runs point at write-buffer/queue sizing - currently untuned and identical across every technology

**RAW:** Regarding the LBM graph where most of the architectures did not finish the workload -
we need to address the write buffers in the memory systems. What are their size? Can we play
with their size and make it improve?

**IMPROVED:** Checked every NVMain `.config` file used in this project
(`simulators/nvmain/Config/*.config`, including `pcm_microsoft_2009.config`,
`DDR5_4800_DRAM_micron.config`, and every ReRAM config): **every single one uses
`ReadQueueSize 32` / `WriteQueueSize 32`** - NVMain's stock default, completely untuned,
identical across DDR5, PCM, and every ReRAM variant. This has never been swept or
technology-differentiated anywhere in the pipeline.

This is a real, concrete, actionable lever - not just a hand-wave. It's also not a new idea:
it matches an already-identified (but not yet executed) future-work item, "Memory Controller
Queue Analysis" (§4.2 - deep-dive into NVMain's controller queue depths/bus saturation), which
was previously flagged as the likely real explanation for the multi-rank latency-flatline
finding (T4-11, currently open). Shahar independently arriving at the same lever from a
different angle (LBM non-completion) is a strong signal this should be promoted, not left as a
someday item.

**RESOLVED (2026-09-04):** the premise was refined then confirmed. `ReadQueueSize`/
`WriteQueueSize` turned out to be dead keys for every ReRAM/DDR5 config - they belong to a
different controller (`FRFCFS-WQF`) that only PCM's config uses; ReRAM/DDR5 use plain `FRFCFS`,
which reads a single combined `QueueSize` (hardcoded default 32, previously never set
explicitly anywhere in the pipeline). `3_gen_nvmain_config.py` and `mbmm_master.py` now expose
`--queue-size` as an explicit, documented generator parameter (default unchanged at 32, so no
headline result moved; verified via a scoped `mbmm_master.py` gatekeeper run reproducing the
existing baseline byte-for-byte). A dedicated `sweep_queue_size.py` (reuses the real generator,
isolated output dirs, no shared-results interference) found: at 1T1R SLC full-DIMM scale,
raising `QueueSize` from 32 to 64 improves LBM completion from 40.0% to 40.7% of DDR5's
reference admission, at a real cost (+83% average latency); the effect is much larger at
single-chip scale (+4.16% completion at QueueSize 128, +258% latency) since less inherent
parallelism leaves more of the workload queue-depth-limited. Both scales hit a wall-clock
simulation-time ceiling well before any completion ceiling (full-DIMM dies between 64-80,
single-chip between 128-256). Full write-up: `Project_Book.typ` Appendix A, new "Memory
Controller Queue Depth" item, cross-referenced from §3.1.1. Conclusion for Shahar: yes, it's a
real, tunable lever, and it's characterized now - but it doesn't dissolve the LBM gap, it narrows
it modestly at real latency cost, so the headline 32-entry default stands.

---

## 6. The selector's 47x leakage advantage needs literature backing on *both* sides, not just one

**RAW:** The selector (vs the transistor) seems too good to be true. What is the selector we
picked? How is it defined? Is it in NVSim or a real number? We must find papers to support the
leakage power/current for selector vs transistor because Shahar can't believe the x47 number.

**IMPROVED:** Traced the full chain. The 47x figure (confirmed real, appears throughout §3.1.2/
3.1.3 and cross-checked via a dedicated NVSim sensitivity sweep in Appendix A that shows it's
insensitive to the HRS target across four orders of magnitude) comes from two *different*
sources, one well-cited and one not:

- **Selector side:** NVSim's own non-linear selector model **[3]** (Dong et al., NVSim, IEEE
  TCAD 2012), calibrated to an explicit HRS/LRS resistance target of **10⁵ Ω (LRS) / 10⁹ Ω
  (HRS)**, sourced from **[7]** C. Matsui et al., "ReRAM resistance design of LRS and HRS for
  ultrahigh-capacity digital memory..." IEICE Trans. Fundamentals, 2026 - a real, recent
  (2026), directly-on-point paper. The selector `.cell` file
  (`configs/reram_22nm_selector_slc.cell`) encodes exactly this: `ResistanceOffAtReadVoltage:
  1e9 ohm`. This side is well-sourced.
- **Transistor side:** the access-transistor's off-state/subthreshold leakage current at 22nm
  comes from **NVSim's own internal circuit-level leakage model** - there is no separate,
  independently-cited paper anywhere in the book for the transistor leakage number itself (this
  was checked directly: no PTM/ITRS/foundry-leakage citation exists in `Project_Book.typ`). It's
  an NVSim-internal number, not an externally validated one in the text.

So Shahar's instinct is well-placed: **one side of the 47x ratio (selector) has a strong, recent,
directly-relevant citation; the other side (transistor) currently rests entirely on trusting
NVSim's built-in 22nm process model, uncited.** That asymmetry, not the ratio itself, is the gap.

**RESOLVED (2026-09-05):** `/research` (`research_notes/item6_transistor_leakage.md`) found two
convergent sources for the transistor side: ITRS 2011 PIDS chapter (22nm LOP logic subthreshold
leakage target, 5 nA/µm) and Auth et al.'s (Intel) measured 22nm FinFET silicon (VLSI 2012,
5-20 nA/µm) - the roadmap target sits inside Intel's independently measured band. Added as new
refs [43]/[44] plus a new "Access-Device Leakage Model" bullet in Appendix A. Both sides of the
47x ratio are now independently cited; the exact 47x figure itself remains this project's own
NVSim simulation output, not a number published anywhere externally - that distinction is stated
explicitly in both the book and the deck.

Action items (superseded by RESOLVED above, kept for the record):
- Find and add an explicit citation for the 22nm access-transistor off-state leakage current
  NVSim assumes (Predictive Technology Model / PTM papers, e.g. Zhao & Cao, or a foundry-published
  22nm leakage figure) so both halves of the 47x ratio are independently sourced, not just one.
- Once both sides are cited, add a short "how the 47x number is built" explainer to the book/deck
  (both a transistor leakage current and a selector leakage current, cited independently, whose
  ratio is 47x) - this is exactly the kind of "show your work" framing Shahar is asking for
  across items 6 and 8.
- The 47x-fact slide already exists in the deck ("The 47× Fact") - this is where the two-sided
  citation and the actual current numbers (not just the ratio) should go.

---

## 7. PCM's "too good" power number is largely a modeling asymmetry: PCM gets idle-gating, ReRAM deliberately doesn't

**RAW:** In slide 27 - why would PCM be so good? It seems like an anomaly, it should not be
this good.

**IMPROVED:** Found the actual mechanism, and it's a real, well-supported answer - not an
unexplained anomaly. Confirmed in `Project_Book.typ` (fidelity audit item 2, §3.1.6): **"the
DRAM and PCM baselines model standard idle behavior; ReRAM figures are worst-case ungated."**
That is: PCM's headline 0.040 W already includes an idle/standby power-down state (NVMain's
stock PCM model has this), while ReRAM's power numbers are deliberately reported *without* any
idle-gating, because ReRAM's power-down state machine is disabled in this pipeline (this is
exactly the "Restore Idle-Gating Simulation" item already logged as §4.1's single highest-priority
future-work item).

But the deck slide itself ("Full-Module Power (Ungated)") states the numbers side by side - 1T1R
50.9 W, 1S1R 1.12 W, DDR5 0.651 W, PCM 0.040 W - under a single title, "(Ungated)," that in
reality only applies to the two ReRAM columns. DDR5 and PCM are not on the same footing as
labeled: **it's an apples-to-oranges comparison, gated baselines vs. an intentionally ungated
ReRAM worst case, presented under one blanket label that implies otherwise.**

**RESOLVED (2026-09-05), with a correction to the original diagnosis:** idle-gating has now
actually been restored and fully re-run (item 5/Workstream C above) - and the result complicates
the original theory rather than simply confirming it. DDR5 *did* benefit for real (0.651 to
0.623 W). **PCM did not** - its power-down counters are exactly zero in both the pre- and
post-restoration runs, for every workload, most likely because its `FRFCFS-WQF`
write-queue-flush controller keeps its request queue non-empty far more of the time than the
plain `FRFCFS` controller ReRAM/DDR5 use, starving the power-down entry condition entirely
(structural, not yet root-caused to full confidence). So PCM's 0.040 W was never actually
resting on an idle-gating advantage over ReRAM the way the original diagnosis assumed - it
reflects PCM's own inherited baseline leakage characterization, not power-down credit, and it
still isn't gated now that the mechanism exists. The deck's "Full-Module Power" slide has been
re-titled ("Idle-Gating Restored") and re-annotated to state this precisely: DDR5's number is
real and gated, ReRAM's mechanism is mechanically live but placeholder-valued (no benefit
claimed), and PCM shows no gating activity at all in either run.

Action items (superseded by RESOLVED above, kept for the record):
- Re-title or annotate the slide so it's explicit: "ReRAM: worst-case, no idle-gating modeled.
  DDR5/PCM: standard idle behavior included." This turns "PCM looks anomalously good" into "PCM
  looks good *because* it's being compared against a ReRAM number that hasn't been given the
  same courtesy yet" - which is honest and, more importantly, turns the anomaly into a concrete
  argument for why the idle-gating restoration (§4.1) is the single highest-leverage next step.
  It also directly strengthens the case that a fair, gated ReRAM number would be meaningfully
  better than 50.9 W / 1.12 W - useful framing for "what's next," not just a caveat.
- Once idle-gating is restored (§4.1 future work), re-run this comparison on equal footing and
  replace the placeholder framing.

---

## 8. Endurance: show the actual calculation, and reconcile against the literature-cited cycle count (10⁷, not 10⁹)

**RAW:** Slide 33 - what is the endurance? What is the number? We need to show calculations -
again, it seems too good to be true. We must support the number with literature, too. Calculation
example: 10⁹×60×60×24×365×10/(64×10⁹×8)×8×64 - to get an assumption for system lifetime. Magic
number should be somewhere around 10¹⁵, leading to about 10 years, if he remembers correctly.
What is the wear level?

**IMPROVED:** Traced the exact calculation the book actually does (§3.1.4, `Project_Book.typ`
~lines 1295-1390) and it reconciles well - with one important correction to Shahar's recalled
assumption:

- **Endurance rating used:** SLC = **10⁷** write cycles/cell, MLC = **10⁶** - not 10⁹. This is
  explicitly literature-cited: **[14]** H.-S. P. Wong et al., "Metal-Oxide RRAM," Proc. IEEE 2012
  (a foundational, heavily-cited review), and **[15]** M. Lanza et al., "Standards for the
  Characterization of Endurance in Resistive Switching Devices," ACS Nano 2021 - explicitly
  described as a *conservative* choice within a wide reported range, warranted by [15]'s finding
  of methodological inconsistency in reported RRAM endurance numbers across the field.
- **The actual "magic number" calculation** (physical 8 GB SLC module): the module has
  **134.2 million 64-byte cache-line locations** (8 GB / 64 B). Total write budget under uniform
  wear leveling = 134.2×10⁶ lines × 10⁷ cycles/line ≈ **1.342×10¹⁵ total writes** - this matches
  Shahar's recalled order of magnitude (~10¹⁵) closely, even though the underlying per-cell
  assumption differs (10⁷, not 10⁹). At LBM's measured write rate (3,269,479 writes per
  83.33 ms window ≈ 39.2×10⁶ writes/s), lifetime = 1.342×10¹⁵ / (39.2×10⁶ × 31,536,000 s/yr) ≈
  **1.08 years** - exactly Table 5's reported figure. At 64 GB (8x the lines), the same
  arithmetic gives ≈ **8.7 years** - closer to the "~10 years" Shahar recalled, suggesting he may
  be recalling the 64 GB figure rather than the 8 GB one, or a genuinely different per-cell
  assumption (10⁹) applied at a different capacity. Worth clarifying directly with him which one
  he means, since the two independently-sourced numbers (10⁷ vs. a hypothetical 10⁹) are 100x
  apart and this matters for how impressive the endurance story actually is.
- **Wear level, answered:** the projection assumes **ideal uniform wear leveling** - every write
  is assumed spread perfectly evenly across all 134.2M line locations (not a real controller
  algorithm, just a modeling assumption). The book already includes a sensitivity check for
  *imperfect* leveling (a hot-spot absorbing 2x its uniform share halves every lifetime figure,
  and even then 128 GB SLC still clears the 5-10 year server-replacement target). A real
  wear-leveling controller is explicitly still future work (§4.2, "Endurance-Aware Scheduling").

**PARTIALLY RESOLVED (2026-09-05):** the calculation is now shown as a visible worked equation in
both `Project_Book.typ` §3.1.4 and the deck's Endurance slide (matching the numbers above exactly).
Still open, and NOT fixable from the book alone: the 10⁷-vs-10⁹ reconciliation needs an actual
conversation with Shahar to find out which figure/capacity he was recalling - flag this live.

Action items (calculation part superseded by RESOLVED above; reconciliation still open):
- Add the actual calculation (module line count × per-cell endurance rating ÷ write rate) as a
  visible worked example in both the book (currently it's stated in prose, not shown as an
  equation) and the deck's Endurance slide - this is exactly what Shahar asked for, and the
  numbers already check out, so showing the work should defuse the "too good to be true"
  reaction rather than requiring new data.
- Explicitly reconcile the 10⁷ vs. 10⁹ discrepancy with Shahar in the next conversation - confirm
  which capacity/assumption he was recalling, and consider citing where in the literature the
  wider 10⁶-10⁹+ range comes from (this is likely already inside [14]/[15] - re-read them for a
  usable quote on the reported range) so both the conservative choice *and* the existence of
  higher-endurance reports in the literature are visible side by side.
- State the "ideal uniform wear leveling" assumption explicitly on the deck slide itself, not
  just in the book - it's currently a book-only caveat.

---

## 10. 1S1R vs 1T1R needs a single, direct, three-axis comparison - not scattered mentions

**RAW:** We need to compare 1S1R vs 1T1R better.

**IMPROVED:** The comparison exists but is spread across the document rather than presented as
one direct head-to-head: density (20F² vs 4F², §3.3/Table 6), latency (1S1R pays a 1.5-2.3x
selector-access-path cost over 1T1R, §3.1.1), power (the 47x leakage-class separation, §3.1.2/
3.1.3 - see item 6), and endurance (1S1R's slower write path gives it *longer* projected lifetime
than 1T1R at the same capacity - 12.4 vs 8.7 years at 64 GB SLC, per Table 5's own numbers -
because fewer writes complete in the same window). That last point is a genuinely interesting,
underused result: 1S1R's latency penalty is also, mechanically, part of why it lives longer -
the two axes aren't independent, and the book never states that connection explicitly.

Also relevant here: the previously-flagged, still-open density-bound disclosure gap between
1T1R's 20F² (this study's planar/FinFET assumption) and the 6F² a real commercial recessed-
channel 1T1R part has demonstrated (Fackenthal et al., ISSCC 2014, already cited in §4.2 future
work) - if that gap were closed, 1T1R's density disadvantage relative to 1S1R would mostly
disappear, which changes how "1S1R is the clear architectural winner" should be framed (it's the
winner *given this study's transistor-geometry assumption*, not unconditionally).

**RESOLVED (2026-09-05):** turned out mostly already satisfied - `Project_Book.typ`'s existing
Table 7 ("Cross-technology summary, full-DIMM configurations") already places latency, power,
PDP, density, and lifetime side by side for every technology including both 1T1R and 1S1R, and
its footnote already states the endurance-is-mechanical-consequence point verbatim ("the slower
writer wears correspondingly slower"). The only genuine gap was the recessed-channel 6F² density
caveat not being cross-referenced next to the density comparison itself (only living in
Appendix A) - added directly to Table 7's footnote now.

Action items (first two superseded by RESOLVED above; third addressed):
- Add one dedicated table/slide: 1T1R vs 1S1R, all four axes side by side (density, latency,
  power/leakage, endurance), each cell citing the section it's drawn from - make the "why 1S1R
  wins" argument in one place instead of requiring the reader to assemble it themselves.
- State explicitly that 1S1R's endurance advantage over 1T1R at matched capacity is a *mechanical
  consequence* of its latency penalty (fewer writes admitted per unit time under the fixed
  measurement window), not an independent virtue - both to be accurate and because it's a more
  interesting, defensible claim than treating the two as unrelated wins.
- Flag the recessed-channel 6F² 1T1R caveat directly next to the density comparison, not only in
  §4.2 - "1T1R's density disadvantage is conditional on this study's planar-transistor
  assumption; a real 6F² recessed-channel part would close most of the gap" - so the comparison
  reads as honestly bounded rather than a clean, unconditional verdict.

---

## Cross-cutting observations

- **Several of Shahar's items independently rediscover already-known, already-logged future-work
  items** (item 5 → §4.2 controller-queue analysis; item 7 → §4.1 idle-gating restoration; item 8
  → §4.2 wear-leveling). That convergence is a strong signal these three should be re-prioritized
  as the near-term roadmap, not just listed alongside everything else in §4.
- **A recurring pattern across items 2, 4, 6, 7, and 8: numbers that are correct but under-
  explained.** In every one of these cases the underlying figure checked out against the book's
  own text and configs - the actual problem was that the *derivation* wasn't shown or wasn't
  cited on both sides. The fix in each case is "show the work / add the missing citation," not
  "the number is wrong." Worth calling out as a pattern when planning the next revision: prioritize
  visible derivations and citations over re-deriving new numbers.
- **Optane (items 3 & 9) is the connective thread** for at least three other items: it would
  supply a real F² number for item 1's PCM density row, a real hardware anchor point missing
  from every comparison, and (per its OTS cross-point architecture) a natural bridge into item
  10's 1S1R discussion. Prioritize pulling real numbers from ref [32] early - it likely pays off
  in multiple places at once.

## Suggested next steps (once local changes are pushed)

1. Open new `Review_Fixes_Tracker.md` items for each of the 10 points above (not done yet - this
   file is the baseline they should be drawn from).
2. Item 5 (write-queue sweep) is now done (see its RESOLVED note above). Item 8 (show the
   endurance calculation) is the next cheap, presentation-only change with no open research
   question - it directly defuses a "too good to be true" reaction with data that already exists.
3. Items 2, 6, and 10's transistor-leakage citation are literature-search tasks (no simulation
   changes) - good candidates to parallelize.
4. Items 1, 3, 9 (PCM architecture disclosure + Optane real numbers) are the most book-narrative-
   affecting - do these together, since fixing PCM's characterization and adding Optane's real
   numbers are the same piece of work.
