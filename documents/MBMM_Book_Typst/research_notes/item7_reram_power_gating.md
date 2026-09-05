# Item 7: Literature search for ReRAM peripheral power-gating data

**Question this note answers:** Is there real, peer-reviewed, primary-source literature that would let MBMM replace its interim "ReRAM power-down state = precharge-standby energy (assume zero savings)" placeholder with an actual gatable-fraction or leakage-reduction number for ReRAM/RRAM crossbar peripheral circuitry (sense amps, decoders, charge pumps, write drivers) at a 22nm-class node?

**Bottom line up front:** No. Nothing found rises to the bar of "a citable number for what fraction of ReRAM peripheral leakage is gatable" or "a stated Nx leakage-reduction factor with entry/exit latency/energy for gating an RRAM macro's periphery." The project's existing honest placeholder (ReRAM power-down energy = existing precharge-standby energy, i.e., assume power-gating saves nothing yet) should **remain in place**. Details and the one substantive, directly-relevant primary-source data point that *was* found are below.

Method note: all primary sources cited below were read from the full-text PDFs already vetted and stored in this repository (`documents/reference_validation_papers/` and `resources/papers/`) using local text extraction, not from abstracts or secondary summaries. Search terms used against the full text: `power gat*`, `sleep`, `standby`, `power-down`, `power down`, `leakage`, `idle`, `quiescent`, `off-state`, `disable`, `shutdown`.

---

## 1. Fraction of ReRAM chip/macro static power attributable to periphery vs. crossbar array

**Not found.** No number search turned up a published ReRAM/RRAM-specific figure decomposing total static/leakage power into "peripheral circuit" vs. "crossbar array" components, at 22nm-class or any other node.

- The EMBER papers (both versions, see below) give an **area** breakdown (peripheral area dominated by BL/SL write drivers, pass gates, and multiplexers — EMBER ESSCIRC 2023, p. 471/472, Fig. 9a discussion: *"the BL/SL write drivers and multiplexers dominate the peripheral area"*), but neither paper gives a **power or leakage** breakdown between array and periphery. Area share is not a valid proxy for leakage share (periphery uses different device types/voltages than the array's access transistors), so this cannot be reused as the fraction the project needs.
- NVSim (X. Dong et al., IEEE TCAD, vol. 31, no. 7, pp. 994–1007, July 2012) computes leakage *per structural block* (row decoder, column decoder/mux, sense amp, precharger, output driver, subarray matrix, etc. — see `SenseAmp.cpp`, `BasicDecoder.cpp`, `Precharger.cpp`, `Mux.cpp` in this project's `simulators/nvsim/`) via `Power_leakage = V_DD × I_leak` (NVSim paper, p. ~981, Eq. 12) applied independently to each component's transistor sizing. This means a periphery-vs-array leakage split is *mechanically derivable from this project's own NVSim runs* — but that is an artifact of re-running the project's own simulator on its own characterized cell, not a *published, external, peer-reviewed* number. It does not satisfy "real, citable peripheral-leakage-reduction fraction" from the literature, and the project has explicitly noted it hasn't yet extracted this decomposition from its own NVSim output. That remains a possible *future* internal-data path, not a literature citation.
- Generic SRAM/cache literature (not ReRAM) does report periphery-dominated leakage in some designs — e.g., word-line drivers and row decoders reported to dissipate the large majority of cache leakage in some 65 nm SRAM/cache studies (Hu & Homayoun et al., UC Davis, "Reducing Leakage Power in Peripheral Circuits of L2 Caches," and related work). These are **CMOS SRAM/cache figures, not RRAM crossbar figures**, and are flagged here only to confirm the general engineering intuition (periphery can plausibly dominate static power in a memory macro) — they must **not** be borrowed as a ReRAM number. RRAM crossbars have a qualitatively different leakage mechanism (cell/access-transistor and, for 1R passive crossbars, sneak-path leakage through unselected cells) that has no established quantitative correspondence to SRAM bit-cell/periphery leakage ratios.

## 2. Published power-gating/sleep-transistor scheme for an RRAM macro's periphery, with a stated leakage-reduction factor and/or entry/exit latency/energy

**Not found as an on-die sleep-transistor scheme with a stated Nx factor.** However, one directly relevant, primary-source data point was found in the EMBER papers (see Section 3) describing a *coarser* power-gating practice: gating the write-DAC supply off-chip during idle. It does not include a reduction factor, nor entry/exit latency/energy — see Section 3 for the exact text and why it falls short of what's needed.

General (non-ReRAM) sleep-transistor/power-gating literature does report leakage-reduction factors (e.g., generic CMOS power-gating studies cite header/footer sleep-transistor schemes reducing leakage by large factors, commonly cited as >90% reduction in various sub-100nm CMOS logic/SRAM contexts — e.g., sleep-transistor sizing and row-based power-gating literature such as Kim & Roy et al.'s and related IEEE TVLSI/DAC works on sleep-transistor design). These are generic CMOS logic/SRAM power-gating results, not RRAM-macro-specific, and were not chased down to exact figures because they fail the "directly on-point to RRAM periphery" bar the task set. They are noted only to confirm the well-established *general* feasibility of periphery power-gating in principle — not to supply a number for this project.

One tangential hit worth flagging and explicitly ruling out: a "10T1R nonvolatile SRAM" design integrating a conventional 6T SRAM bit-cell with a memristor as a non-volatile backup element, combined with power-gating of the *SRAM* supply during idle (to reduce standby power, with restore-from-memristor on wake). This is a hybrid SRAM+memristor nonvolatile logic/cache cell, not a pure RRAM/memristor crossbar array macro — the thing being power-gated is the SRAM part, not RRAM crossbar periphery. **Not applicable to this project's ReRAM main-memory macro model.**

## 3. Do the two EMBER papers or the NVSim paper discuss power-gating/sleep-mode behavior?

This is the most useful, concrete, and directly on-point finding.

### EMBER (both versions) — yes, one sentence, applies to the write-DAC supply only

Both the ESSCIRC 2023 conference paper and its JSSC 2024 journal extension contain the **identical statement**, word-for-word except for trivial rewording:

> ESSCIRC 2023 (L. R. Upton, A. Levy, M. D. Scott, D. Rich, W.-S. Khwa, Y.-D. Chih, M.-F. Chang, S. Mitra, P. Raina, and B. Murmann, "EMBER: A 100 MHz, 0.86 mm², Multiple-Bits-per-Cell RRAM Macro in 40 nm CMOS with Compact Peripherals and 1.0 pJ/bit Read Circuitry," *Proc. ESSCIRC*, Lisbon, Portugal, Sep. 2023, pp. 469–472), p. 471:
> *"The macro quiescent power draw is 5 μW, excluding the digital controller and using off-chip power gating for the write DAC supply."*

> JSSC 2024 (A. Levy, L. R. Upton, M. D. Scott, D. Rich, W.-S. Khwa, Y.-D. Chih, M.-F. Chang, S. Mitra, B. Murmann, and P. Raina, "EMBER: Efficient Multiple-Bits-Per-Cell Embedded RRAM Macro for High-Density Digital Storage," *IEEE J. Solid-State Circuits*, vol. 59, no. 7, pp. 2081–2092, July 2024), p. 2087 (Section III-B, immediately following the read-energy discussion):
> *"The macro quiescent power is 5 µW, excluding the digital controller and using off-chip power gating for the write DAC supply."*

What this does and does not give us:

- **What it confirms:** it is real, primary-source, peer-reviewed evidence that at least one directly-comparable, already-vetted RRAM macro design (40 nm CMOS periphery, 1T1R HfOx RRAM, TSMC-fabricated periphery — a reasonably adjacent node to this project's 22nm target) treats the write-path supply (DAC) as something to be power-gated when not writing, and reports a resulting macro-level quiescent power number (5 µW) for everything else (array + read periphery, sense amps, decoders — excluding only the digital controller).
- **What it does not give us:**
  - **No decomposition.** The 5 µW figure is a lumped, whole-macro quiescent number. It is *not* broken into "array leakage" vs. "gatable sense-amp/decoder leakage," so it cannot be used to derive a gatable fraction.
  - **No before/after comparison.** There is no reported quiescent power *without* the write-DAC gating, so no leakage-reduction factor (no "Nx") can be computed or cited.
  - **No entry/exit latency or energy overhead** is reported for the gating action anywhere in either paper.
  - **The gating described is off-chip**, applied to an external test/bench power supply rail feeding the write DAC — not an on-die sleep-transistor circuit gating the sense amplifiers, row/column decoders, or charge pumps that this project's ReRAM power-down state would need to model. It is closer to "the test setup turns off an unused external supply" than to a characterized on-die power-gating circuit block with its own overhead.
  - Confirmed by full-text search of both papers: neither contains the words "sleep," "standby," "power-down," "idle," or any leakage-reduction percentage/factor anywhere outside this one sentence. The only other adjacent hit is an unrelated mention that each 1T1R cell's own access transistor is used "to mitigate off-state current leakage" of the *cell itself* (JSSC 2024, p. 2083, Section II) — a per-cell selector-transistor leakage detail, not a periphery power-gating scheme.

**Conclusion for EMBER:** real and citable as evidence that RRAM macro designers do treat some supply rails as gatable, but it supplies no fraction, no reduction factor, and no entry/exit overhead — i.e., it does not clear the bar needed to replace the project's placeholder with a real number.

### NVSim (X. Dong, C. Xu, Y. Xie, N. P. Jouppi, IEEE TCAD, vol. 31, no. 7, pp. 994–1007, July 2012) — confirmed: no power-gating modeling at all

Full-text search of the NVSim paper (as archived in `resources/papers/NVSim A Circuit-Level Performance Energy.pdf`) turns up **zero** occurrences of "power gating," "sleep," "standby," "power-down," or "idle" as memory states. NVSim's leakage model is purely static/steady-state:

> p. ~1002 (Section IV-A, "Data Sensing Models" preamble): *"The dynamic energy and leakage power consumptions can be modeled as follows: Energy_dynamic = CV²_DD ... Power_leakage = V_DD · I_leak, where we model both gate leakage and sub-threshold leakage currents in I_leak."*

This is a fixed steady-state leakage current model per component (row decoder, column mux, sense amp, precharger, etc.), computed once from HSPICE-characterized or analytically-modeled transistor sizing at a given process node. There is no notion in the paper of an active vs. idle vs. power-gated *state* for any component, no sleep transistors, and no state-dependent leakage current. NVSim's "Leakage Opt." design corner (Table XI, p. 1006, e.g., 1372 mW leakage for a 32 nm 8 MB ReRAM chip design point) is a **design-time area/leakage trade-off optimization target** (favoring smaller, leakier or larger, less-leaky transistor sizing choices at layout time), not a **runtime power-gated operating state**. This directly confirms the premise stated in this project's task: NVSim itself provides no power-gating capability to draw on, at the device-characterization level or otherwise.

## 4. Broader IEEE Xplore / ISSCC / ESSCIRC / VLSI / JSSC search for "ReRAM power gating," "RRAM sleep mode," "memristor standby power reduction"

No additional directly on-point paper was found beyond what's covered above. Notes from the broader search:

- P. Jain et al. (Intel), "A 3.6Mb 10.1Mb/mm² Embedded Non-Volatile ReRAM Macro in 22nm FinFET Technology with Adaptive Forming/Set/Reset Schemes...," *ISSCC 2019*, pp. 212–214 — this is the single closest node-match candidate found (22 nm FinFET, Intel embedded ReRAM macro) and is already in EMBER's own reference list (EMBER ESSCIRC 2023, ref. [5]). Full text sits behind the IEEE Xplore/ISSCC paywall and was not accessible through the tools available in this session (IEEE Xplore blocked automated fetch with HTTP 418; no cached full text found elsewhere; not present in this project's local paper archive). **This paper could not be checked and is flagged as an open lead** if institutional/IEEE Xplore access becomes available — it is the most promising unexamined candidate for a 22nm-class ReRAM standby-power figure.
- No ISSCC/ESSCIRC/VLSI-Symposium/JSSC paper was found (via title/abstract search) whose title or abstract explicitly centers on "ReRAM power gating" or "RRAM sleep mode" as its subject — searches for these exact phrases return only generic CMOS/SRAM power-gating hits, or unrelated ReRAM-crossbar circuit-design papers that happen to also use the word "leakage" (e.g., sneak-path leakage current suppression schemes for passive 1R crossbars, which address *bias-scheme* leakage during normal read/write operation, not standby power-down).
- Sneak-path/half-select leakage suppression papers for passive 1R RRAM crossbars (a large, well-established literature) address a different problem: leakage *during active array access*, mitigated by bias schemes (V/2, V/3 schemes) or selector devices — not periphery standby leakage during a power-down state. Out of scope for this task; noted only to avoid confusing the two leakage phenomena.

---

## Recommendation

Do not replace the placeholder. No peer-reviewed, primary-source, ReRAM/RRAM-macro-specific number was found for:
- what fraction of ReRAM static power is peripheral (gatable) vs. array (ungatable), or
- a leakage-reduction factor for power-gating RRAM periphery, with or without entry/exit latency/energy overhead.

The one real data point (EMBER's 5 µW macro quiescent power with off-chip write-DAC gating) is genuine and citable as color/context — it can reasonably be mentioned in the thesis text as evidence that RRAM macro designers already treat some rails as gatable in practice — but it must not be repurposed into a fabricated gating-savings number for the simulator, since it provides no fraction, no reduction factor, and no on-die entry/exit overhead. The project's interim choice (ReRAM power-down-state energy = existing precharge-standby energy, i.e., assume power-gating saves nothing yet, pending real characterization) remains the most honest option and should stay in place. The one open lead worth chasing if IEEE Xplore access becomes available is P. Jain et al., ISSCC 2019, pp. 212–214 (Intel 22 nm FinFET embedded ReRAM macro).

## Sources consulted (primary, full text read unless noted)

1. X. Dong, C. Xu, Y. Xie, and N. P. Jouppi, "NVSim: A Circuit-Level Performance, Energy, and Area Model for Emerging Nonvolatile Memory," *IEEE Trans. Computer-Aided Design of Integrated Circuits and Systems*, vol. 31, no. 7, pp. 994–1007, July 2012. (Local copy: `resources/papers/NVSim A Circuit-Level Performance Energy.pdf` — full text read.)
2. L. R. Upton, A. Levy, M. D. Scott, D. Rich, W.-S. Khwa, Y.-D. Chih, M.-F. Chang, S. Mitra, P. Raina, and B. Murmann, "EMBER: A 100 MHz, 0.86 mm², Multiple-Bits-per-Cell RRAM Macro in 40 nm CMOS with Compact Peripherals and 1.0 pJ/bit Read Circuitry," *Proc. ESSCIRC*, Lisbon, Portugal, Sep. 2023, pp. 469–472. (Local copy: `documents/reference_validation_papers/EMBER_A_100_MHz_0.86_mm2_...pdf` — full text read.)
3. A. Levy, L. R. Upton, M. D. Scott, D. Rich, W.-S. Khwa, Y.-D. Chih, M.-F. Chang, S. Mitra, B. Murmann, and P. Raina, "EMBER: Efficient Multiple-Bits-Per-Cell Embedded RRAM Macro for High-Density Digital Storage," *IEEE J. Solid-State Circuits*, vol. 59, no. 7, pp. 2081–2092, July 2024. (Local copy: `documents/reference_validation_papers/EMBER_Efficient_Multiple-Bits-Per-Cell_Embedded_RRAM_Macro_for_High-Density_Digital_Storage.pdf` — full text read.)
4. P. Jain et al., "A 3.6Mb 10.1Mb/mm² Embedded Non-Volatile ReRAM Macro in 22nm FinFET Technology with Adaptive Forming/Set/Reset Schemes Yielding Down to 0.5V with Sensing Time of 5ns at 0.7V," *ISSCC Dig. Tech. Papers*, 2019, pp. 212–214. (Cited only via secondary bibliographic metadata and EMBER's own reference list [5] — full text NOT accessible in this session; IEEE Xplore blocked automated fetch. Flagged as an open lead, not used as a source of any claim above.)
5. Generic (non-ReRAM) CMOS/SRAM power-gating and cache-peripheral-leakage literature (e.g., sleep-transistor sizing/row-based power-gating IEEE TVLSI/DAC papers; UC Davis L2-cache peripheral-leakage studies) — consulted only for general background context, explicitly not used as a source for any ReRAM-specific number in this note.
