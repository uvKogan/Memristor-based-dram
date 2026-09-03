# Meeting Prep Cheat Sheet - grilling arc, corrected answers

Personal rehearsal notes from the pre-meeting grilling sessions. Not part of the
book's fix tracker - a separate, personal prep artifact.

## Parking lot (cover separately, not yet done)
- How the NVMain memory system is actually built/configured *from* NVSim's
  device-level output - the ETL translation mechanics (Area/Latency-ns/Energy →
  JEDEC-style tCAS/tRCD/tRP + energy-per-access coefficients). Walk through this
  before the meeting if time allows; it wasn't covered in Rounds 1–3.

## Round 1 - Narrative & mechanics
- Pitch: AI accelerators need HBM → fabs reallocate DRAM wafer capacity → is 22nm
  ReRAM viable as a DDR5 drop-in? Simulation study. Say "literature-characterized"
  device physics, never "proven" - the *system-level* claim is what's untested.
- Two simulators: NVSim = device-level (no workload notion); NVMain = system-level
  (needs device params as input). Need both for an end-to-end, workload-grounded
  answer.
- ETL pipeline exists for two reasons: avoids manual-transcription errors at scale,
  and the toolchain *seams* are exactly where bugs hide - the audit found 14, fixed
  12, accepted 2 as permanent. Say "assessed and documented as permanent," never
  "bypassed."
- 1T1R: 20F², transistor-gated, faster, sneak-path-free. 1S1R: 4F² (~5x denser),
  selector-gated, slower access. Neither dominates - compared head-to-head on
  purpose.
- SLC→MLC penalty: 1.5x read latency, 3.263x write latency, 1.1x read energy, 3.0x
  write energy. **Not** one of the 14 audit bugs - a distinct NVSim limitation:
  native MLC (ADC sensing/ISPV) triggers a floating-point exception in NVSim's own
  `Mat.cpp`, so an Analytical Penalty Method is used instead, grounded in two real
  papers (Upton et al., ESSCIRC 2023; Levy et al., IEEE JSSC 2024).

## Round 2 - Headline results
- Latency: close (1.3–1.7x) on compute-bound GCC; far (4.6x) on the
  highest-parallelism workload (GPT-2 inference). Caveat every time: 4.6x is a
  memory-latency ratio, not an application-level slowdown. Never say "faster than
  DDR5" - ReRAM is always somewhat slower than DDR5; the "faster" claim is against
  legacy PCM (49x under compute-bound GCC), a different baseline entirely.
- Power: leakage is the dominant story, not its absence - 97% static for 1S1R,
  99.99% static for 1T1R ("Static Leakage Dominance," the book's named headline
  finding). "Zero refresh" is the separate, correct claim: DDR5 spends 44.7% of its
  GCC power on refresh alone; ReRAM (non-volatile) spends none.
- Power is nearly workload-*independent* (1.12W→1.23W, ~10% swing across the whole
  suite) because leakage swamps dynamic energy. What differs is technology: 1T1R
  ~50.9W tier vs. 1S1R ~1.12–1.30W tier - a 47x device-level leakage gap
  (794.7 vs 16.9 mW/chip). Verified clean: matches live NVSim run logs to 4
  significant figures; no external paper independently confirms the exact
  magnitude, but the direction (selectors eliminate transistor leakage) is field
  consensus.
- State both ends of the power comparison, never just one: 1.7x DDR5 at the
  conservative calibration floor, within 11% of parity at the favorable ceiling -
  both ends of the DDR5 band are vendor spec currents, not measured typicals.
- Endurance: 8GB worst-case streaming (LBM) → 1.1 years; 64–128GB → 9–17 years;
  every other workload clears the target 2x–100x+ even at 8GB.

## Round 3 - Defense of the four disclosed limitations
- **Validation scope**: internal consistency only (NVMain reproduces NVSim's own
  device number exactly, 0.0% anchor error) - never checked against real fabricated
  ReRAM hardware, because none exists. Device-level physics is real/published;
  system-level DIMM behavior is 100% simulated. Keep those two claims separate.
- **Idle-gating / power parity**: idle-gating is a power-*saving policy*, not "static
  power" itself - currently un-simulatable (NVMain's power-down state machine is
  disabled in source, a tool limitation). The comparison asymmetry cuts **both
  ways** (DDR5 also has unexercised power-down states) - the one truly one-sided,
  physical asymmetry: DRAM must keep refreshing to retain data even when idle;
  gated non-volatile ReRAM retains data at zero power. Real-world gated ReRAM would
  very likely beat these worst-case numbers - bounding arithmetic (grounded in
  Malladi et al.'s real Microsoft Bing/Cosmos idle-time measurements, already
  cited) shows break-even with DDR5 needs only 43% idle-gating captured (10%
  against the vendor ceiling); a plausible 90%-idle capture would land ~0.14W, 4.5x
  *below* DDR5. Say "the arithmetic suggests X, pending actual simulation," never
  "we showed X." The datacenter-workload citation already exists - it is not a
  future-work gap. What's actually future work: simulating an actual gating policy.
- **Endurance hot-spot bound**: a 2x hot-spot factor halves every SLC figure - 128GB
  still clears the server target even halved (8.7yr 1T1R / 12.4yr 1S1R); 64GB drops
  to the target's lower edge (4.3–6.2yr). MLC is separately bad at any capacity
  (0.39–0.65yr at its own 16GB physical size, marginal even at 128GB) - an
  independent argument to restrict MLC to read-dominant use.
- **Trace fidelity**: cache-less/first-10M-instruction capture is a *safe,
  conservative* bias for endurance, but *direction-unknown* for absolute
  latency/queueing (queueing delay is nonlinear in request rate, so an inflated
  request stream can compress or exaggerate cross-technology gaps unpredictably).
  The GPT-2/AI-inference trace (behind the 4.6x number) has unverifiable
  provenance; AlexNet's is confirmed. **The 4.6x figure is the single number
  resting on the weakest data provenance** - know this if asked "which number do
  you trust least."
- Bonus (you independently re-derived this, and it was already fixed): the
  "fixed-time vs. fixed-transaction" concern was a real bug (audit item 11 -
  heterogeneous host clock frequencies not rescaled). Fixed via a "matched-host
  correction" - every technology now admits the identical request population per
  workload for 5 of 6 workloads. LBM (streaming) is deliberately the one
  service-limited exception, disclosed as a genuine throughput finding: of an
  identical 16,447,102-request admission, DDR5 completes 100%, 1T1R SLC 40.0%,
  1S1R SLC 28.0%, PCM 3.9%.

## Round 4 - What's next

- Headline answer to "what's next": **Power-Down Restoration** - the book's own
  named "single highest-leverage item." Restore NVMain's disabled power-down state
  machine with a defensible idle-gating policy. It's a config/policy change
  against existing NVMain source - no new device physics, no fab access - which is
  exactly why it's also the honest answer to "if you only had 3 months."
- Three fronts, not a flat wishlist:
  - **A - Close the simulator's known gaps**: Power-Down Restoration; Parameter
    Optimization (sensitivity sweep on NVSim's ReadVoltage/WritePulseWidth to find
    the efficiency-optimal LOP operating region); Native MLC Logic (fix NVSim's
    `Mat.cpp` floating-point exception, replace the Analytical Penalty Method with
    native circuit-level ISPV characterization).
  - **B - System-level scaling, same toolchain**: L3/near-memory write buffer
    (historically proven for PCM, targets write-heavy AI workloads); memory
    controller queue-depth analysis (the real multi-rank Flatline Paradox -
    distinct from the renamed "Standby Convergence"); endurance-aware wear-leveling
    scheduling.
  - **C - Device-physics frontier**: macro-scale 1T1R beyond the 1024×1024
    baseline-parity restriction; recessed-channel 1T1R density (a real commercial
    part hits 6F² via a DRAM-process recessed-channel access transistor - closing
    this gap for oxide-RRAM could overturn the book's own "1T1R isn't
    density-competitive" verdict); node scaling and 3D die-stacking projections.
    Explicitly real device-physics work, not a config change - multi-year, and
    outside direct control (foundry/device access).
- 3-month answer, stated plainly: **Theme A / Power-Down Restoration, full stop.**
  Theme B is real but needs more runway; Theme C isn't a software problem at all -
  don't hedge this, the clean separation of "tractable now" vs. "interesting but
  not a 3-month claim" is itself the strong answer.
- **The FPGA-emulation idea is a live agenda item for this meeting, not a
  held-in-reserve answer to a follow-up question.** Pitch it directly, framed as
  genuinely undecided: two possible containers for the same open problem
  (idle-gating), and an actual ask for Shahar's input on which is the better use
  of the next stretch -
  1. Stay inside MBMM: continue the software-simulation Power-Down Restoration
     (Theme A, 3-month tractable, matches the book as written).
  2. Pivot the same problem into an FPGA hardware-in-the-loop emulation of just
     the idle-gating/power-down state machine - a genuinely new research
     direction (verification-of-PIM-hardware, where the ASIC-verification
     background applies directly). Deliberately scoped down from "emulate the
     whole memory system" (not 3-month feasible) to just the power-down logic
     (is).
  - Say it as an open question: "I haven't committed to either - I wanted your
    read on which is the better use of the next stretch of time." Not rhetorical
    framing - a real ask.
  - Keep the claim boundary sharp if pressed: FPGA emulation would validate
    system/architectural behavior under real hardware timing (does the controller
    actually behave as predicted under real clock-edge timing and a real
    idle-gating state machine?). It would **not** validate NVSim's own
    device-level circuit numbers (e.g. the 47x leakage gap) against real silicon -
    the emulated cell still runs on the same literature-derived parameters, just
    in FPGA fabric instead of on a CPU. Never let "validated in hardware" collapse
    into "validated against silicon."

## Verified housekeeping
- Moved two stale, broken NVSim debug outputs (`slc_1t1r_results.txt`,
  `slc_selector_results.txt` - mislabeled "MLC NAND Flash," not the book's real
  data) to `archive/archive_nvsim_stale_debug_20260830/`.
