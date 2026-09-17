# Endurance math: deep dive (Shahar's note 8)

**Date:** 2026-09-15. **Trigger:** the Lead Researcher: "we have to do a much deeper dive on the endurance
math - Shahar was very worried about it." **Status:** research, audit and primary-paper check complete; time base verified (§4.2). No book or deck
change yet; corrected sensitivity in §7, decisions in §6 and §7.

Builds on `item8_endurance_10e7_vs_10e9.md` (why 10^7, not 10^9) and book §3.1.4 / Table 5. Audit scripts
and outputs: `endurance_audit_runs/`. Literature PDFs were read from the session scratchpad (not copied).

## Bottom line

1. **The formula is the field's standard one and the arithmetic is exact.** It is Qureshi ISCA 2009 Eq. 1-2
   and Start-Gap (MICRO 2009) Eq. 1. Every lifetime in the book, deck and cheat sheet reproduces from raw
   stats to the last digit (§4.4).
2. **The inputs are the problem, not the formula.** The 1.09-year figure is ReRAM's *saturated throughput*
   during LBM's *start-up burst*, divided by a *3 GHz* time base that the trace parser did not use, with
   no correction factors. Defensible alternatives span about **0.1 to 4.5 years at 8 GB** (§4.3).
3. **Shahar's formula is the same equation solved for endurance**, and with the book's own LBM rate it
   agrees with the book (§2).
4. **Every canonical paper applies correction factors the book omits**, in both directions (§3.3). The
   book's number is defensible only as a labeled corner case ("ideal leveling, whole line worn per write,
   no ECC, 100% duty cycle") and needs a sensitivity table, not a single value.
5. **Two documented caveats look wrong.** "Uncached traces" (book §2 workload list, §3.1.6 item 6) is
   contradicted by the pipeline's own evidence, and the 3 GHz host basis conflicts with the parser (§4.2).
   Both affect far more than endurance.

## 1. The book's formula, re-checked

lifetime (yr) = (module bytes / 64) x endurance cycles / (writes per window / 0.08333 s) / 31,536,000 s

| Trace | Writes in 83.33 ms | Rate | Implied write bandwidth (64 B/write) | 8 GB | 64 GB |
|---|---|---|---|---|---|
| LBM | 3,257,597 | 39.09 M/s | 2.50 GB/s | 1.09 yr | 8.7 yr |
| GCC | 170,800 | 2.05 M/s | 0.13 GB/s | 20.8 yr | 166 yr |
| STREAM | 100,000 | 1.20 M/s | 0.08 GB/s | 35.5 yr | 284 yr |
| AlexNet OFMAP | 13,542 | 0.16 M/s | 0.01 GB/s | 262 yr | 2,095 yr |

8 GiB = 134,217,728 lines, 365-day year. Ten years at 64 GB with 10^7 cycles requires a sustained rate
below 34.0 M writes/s.

## 2. Shahar's formula, reconstructed

As written in the meeting notes: `10^9 x 60x60x24x365x10 / (64x10^9 x 8) x 8 x 64` = **3.15 x 10^8**.

- **Reading that uses every factor:**
  - 10^9 is a write rate (64-byte writes per second).
  - The middle term is ten years in seconds.
  - (64x10^9 x 8) / (8 x 64) = 10^9 line locations in a 64 GB module.
  - The result is **the endurance each line needs for ten years**: Qureshi ISCA 2009 Eq. 2,
    `Wmax = Y·F·B·2^25/S`, with B counted in 64-byte writes.
  - With the book's LBM rate (39.1 M/s) the requirement is **1.15-1.23 x 10^7 cycles** (GiB vs decimal
    GB). That sits just above the 10^7 rating, **consistent with the book's 8.7 years at 64 GB**.
- **"Magic number about 10^15":** 10^9 lines x 10^6 cycles = 10^15 total writes. With 10^7 cycles the budget
  is 10^16, which lasts 8.1 (decimal) to 8.7 (GiB) years at 39.1 M/s: his "about 10 years".
- **Reading 10^9 as endurance** gives 811 years at 39.1 M/s, so it cannot be what he meant.
- **The same template appears in Kvatinsky's own work.** Perach, Ronen, Kimelfeld and Kvatinsky (IEEE TETC,
  arXiv 2203.10486) compute "required endurance for a ten-year operation with a 100% duty cycle" under
  uniform wear, against 10^12 RRAM endurance. No formula of his was found that includes wear-leveling
  efficiency or cell-to-cell variation.

## 3. Literature (read in full unless marked S)

### 3.1 How the canonical papers compute lifetime

| Paper | Formula / lifetime definition | Wear unit | Write reduction | Wear-leveling efficiency | Endurance, result | Measured write rates |
|---|---|---|---|---|---|---|
| Qureshi ISCA 2009 | `Wmax = Y·F·B·2^25/S`, uniform writes assumed | cell (line-level write-back) | lazy write, line write-back: 3x less traffic | ideal, assumed | 10^7; hybrid 3.0 to 9.7 yr | 0.807 B/cycle at 4 GHz, about 3.2 GB/s |
| Lee ISCA 2009 / CACM 2010 | `L = E / Ŵ`, Ŵ = writes/s per bit, ideal leveling | bit (2 Gb module) | partial writes: 59.3% of bits (64B granularity), 7.6% (4B); buffer coalesces 49-68% | ideal | 10^8; 1.4 yr (64B), 11.2 yr (4B) | 400 MHz bus, 32.8% utilization |
| Zhou ISCA 2009 | first cell failure, workload repeats forever | bit in 64-byte line | redundant bit-writes removed 85% SLC / 77% MLC-2 / 71% MLC-4: **4.5x / 3.5x / 3.0x** lifetime | bit shifting + segment swapping | 10^8 SLC and MLC; raw 171 days; final 22.1 / 17.1 / 13.4 yr | 4 cores, 1 GHz, 4 MB L2, SPEC |
| Qureshi MICRO 2009 (Start-Gap) | `Lifetime = Wmax·S/B`; normalized endurance vs ideal | 256B line, 64K spare lines | none | **none 5%, Start-Gap 53%, randomized Start-Gap 97%** of ideal | 2^25; ideal 4.4-19.5 yr; a malicious loop kills a line in about 32 s | **0.82-3.6 GB/s**; SPEC2006 mix 1.96 GB/s (8 cores) |
| Schechter ISCA 2010 (ECP) | Monte Carlo, normal cell lifetimes (mean 10^8) | 512-bit rows | bits flip with p = 0.5 | assumes existing leveling | ECP6 at 11.9% overhead | synthetic |
| Ipek ASPLOS 2010 (DRM) | lifetime at 50% capacity lost | 4KB page | n/a | ideal | mean 10^8; DRM gain 1.2x / 2.7x / >40x at CoV 0.1 / 0.2 / 0.3; weak cells pull a product spec to 10^6 | SPEC, 4 GHz |
| Zhang ISCA 2016 (Mellow Writes) | first cell reaches wear limit; target 8 yr | **64-byte block** | slower writes: 1.5x / 2x / 3x time gives 2.25x / 4x / 9x endurance | Start-Gap, quota 0.9 | ReRAM 5x10^6; best 9.30 yr | **gem5 + NVMain, same stack as MBMM; names lbm as giving "unreasonably short lifetimes"** |
| Cho and Lee MICRO 2009 (Flip-N-Write) (S) | write word or complement | word | at most N/2 bits: ">2x endurance" | n/a | n/a | n/a |
| Seong ISCA 2010 (Security Refresh) (S) | randomized remapping | n/a | n/a | n/a | >6 yr under attack | n/a |
| Wen DAC 2018 (XWL, crossbar) (S) | leveling that accounts for over-SET/RESET voltage stress | crossbar cell | n/a | +324% lifetime | voltage stress, not only write count, drives crossbar wear | n/a |
| Resch ISCA 2023 | `CellEndurance / max(WriteCount) x latency`, first failure | cell | n/a | load balancing 1.6-2.2x | MTJ 10^12; states RRAM about 10^8 | PIM |

### 3.2 ReRAM endurance ground truth

| Item | Value | Source | Conf. |
|---|---|---|---|
| Lab HfO2/Hf 1T1R | >10^10 (balanced SET/RESET) | Chen TED 2012 [45] | single-cell lab |
| Micron/Sony 16Gb CBRAM (Gb-class, the density anchor [33]) | >10^5 | EE Times on ISSCC 2014 | S |
| Intel 22FFL embedded RRAM | 10^4 cycles, 10 yr at 85 °C | Golonzka VLSI 2019 / Jain ISSCC 2019 | S |
| TSMC 22nm RRAM | 10^4 cycles, 10 yr at 125 °C | eeNews / TSMC | S |
| Weebit 1T1R | 10^5 at 150 °C (AEC-Q100) | Weebit | P |
| Fujitsu / Nuvoton MB85AS8MT, 8 Mb | 10^6 cycles per 4 bytes | datasheet | S |
| Crossbar 1S1R | >10^5 to 10^8 | Jagasivamani MEMSYS 2019 | P |
| Shipped filamentary RRAM (survey) | 10^4-10^7 | Hellenbrand 2024 [46] | P |
| MLC vs SLC | same-array data exists: EMBER (TSMC 40 nm HfOx 1T1R) reaches 10K cycles at both 1 and 2 b/cell, with 2 b/cell failing about 0.3-1x as late (Levy [31] p.8, Fig. 13); earlier "no ratio found" is superseded (§3.5) | [31] | P |
| Endurance vs write pulse / retention | endurance rises linearly to cubically with write time (Strukov 2016); larger window or retention costs endurance (Nail IEDM 2016) | S |
| First failure vs mean (derived) | a 1 Gb-class population's weakest cell sits about 6.9 sigma below the mean: first failure at 65% of the mean for CoV 0.05, 31% for CoV 0.1, about 0 for CoV >= 0.14 | D |

The book's 10^7 SLC rating is at the top of shipped RRAM. **The Gb-class 1T1R part the book uses as its
density anchor [33] was reported at >10^5**, and the 22nm embedded parts are specified at 10^4.

### 3.3 Correction factors

| # | Factor | Supported multiplier | Source | In the book? |
|---|---|---|---|---|
| 1 | Wear-leveling efficiency | x0.97 (randomized Start-Gap), x0.53 (Start-Gap), x0.05 (none) | Qureshi MICRO 2009 | omitted (1.0) |
| 2 | Only changed bits wear (DCW / FNW) | x4.5 SLC, x3.5 MLC-2 (measured); >= x2 (FNW) | Zhou ISCA 2009; Cho MICRO 2009 | omitted (whole line wears) |
| 3 | Partial writes, buffer coalescing | 59.3% of bits (64B); coalescing removes 49-68% | Lee CACM 2010 | omitted |
| 4 | Endurance spread and failure definition | first failure x0.31 at CoV 0.1; DRM half-capacity x1.2 to >40 | derived; Ipek ASPLOS 2010 | omitted |
| 5 | ECP, spare lines | ECP6 at 11.9%; 64K spares even for Start-Gap | Schechter 2010; Qureshi 2009 | omitted |
| 6 | Product spec vs lab | 10^4 (Intel, TSMC) to 10^10 (lab) | §3.2 | 10^7, top of shipped |
| 7 | MLC endurance | about x0.1 (low confidence); Zhou's lower MLC redundancy x0.78 | §3.2; Zhou 2009 | included (10^6) |
| 8 | Write speed vs endurance | x2.25-x9 per cell, 2.58x system | Mellow Writes; Strukov | omitted |
| 9 | Crossbar voltage stress (1S1R) | XWL recovers 3.24x, so naive crossbar lifetime is overstated | Wen DAC 2018 | omitted |
| 10 | Duty cycle | 100% for 10 yr is the convention (Perach/Kvatinsky); Lee calls it conservative | Perach; Lee | implicit 100% |
| 11 | Adversarial writes | <1 minute without region-based leveling | Qureshi 2009 | omitted, state as scope |
| 12 | Capacity units | GiB gives 8.7 yr at 64 GB, decimal GB 8.1 yr | derived | GiB, not stated |

Net: factors 2, 3 and 10 lengthen lifetime about 2-6x; 1, 4, 6, 7 and 9 shorten it by 1x to over 10x.

### 3.4 Is 2.5 GB/s of LBM writes plausible?

- Measured on real hardware (arXiv 1910.00651): lbm_s peaks at 2.3 GB/s and averages 0.9 GB/s of LLC load
  plus store misses (reads and writes combined, 4 threads).
- PCM papers measured 0.82-3.6 GB/s written to main memory on multi-core systems.
- Verdict: the right order of magnitude for a code that rewrites its lattice each step, but at or above the
  measured combined read+write average, so a worst-case rate. Mellow Writes independently flags lbm as the
  lifetime outlier on the same gem5 + NVMain stack.

## 4. Code and trace audit

### 4.1 What one write represents

- **Trace format:** `cycle R|W 0xaddr <128 hex zeros> thread`. The data field is always zero
  (`parse_trace.py`; 0 non-zero fields in LBM, GCC, STREAM, OFMAP).
- **Address alignment:** 100% of LBM (11,461,967 W / 18,634,490 R) and GCC (476,324 W / 845,316 R) addresses
  are multiples of 64. That fits 64-byte cache-block packets, not uncached 1-8 byte data accesses. STREAM is
  synthetic 64-byte elements; OFMAP is not 64-aligned.
- **NVMain:** fixed 64-byte data (`NVMainTraceReader.cpp:158-166`); address translator shifts to 64-byte words
  (`AddressTranslator.cpp:54, 93-94, 203-210`); WordModel word = 64 bytes.
- **Verdict:** "one write = one 64-byte line" is justified. If writes were 8-byte words, lifetime would be 8x
  longer; if 4 KB pages, 64x shorter.
- **Data-dependent wear cannot be simulated with these traces.** NVMain's BitModel counts only changed bits,
  but all data is zero, so it would record zero wear. Factor 2 (§3.3) must come from the literature.

### 4.2 Two caveats contradicted by the pipeline's own evidence (verified 2026-09-15)

**Cached vs uncached.** The book says the gem5 traces are "uncached raw CPU-to-memory streams" (§2 workload
list, §3.1.6 item 6).
- **Where the claim came from:** `archive/root_docs/Priority1_StandbyPower_Fix_Scoping.md:288-307` flagged
  it as conditional ("*if* produced by run_gem5_trace.py", TimingSimpleCPU, no caches) and unprovable. It was
  later recorded as fact in `MBMM_AI_Context_State.md`, the book and slide 16.
- **Evidence for cached traces:**
  - The O3CPU commit `2e8514c` (2026-03-28, the same day as both .nvt files) documents
    `se.py --cpu-type=X86O3CPU --caches --l2cache --fast-forward=500000000 --maxinsts=50000000` (README).
  - Session Summary 18 records a switch from a 139 GB uncached gcc trace to about 2.5 GB cached traces.
  - The 100% 64-byte address alignment (§4.1).
- **Open point:** LBM has about 30 M memory accesses for 50 M instructions, which is high for a cached trace.
  `--maxinsts` interacts with fast-forward, so this is not conclusive. Status: **likely cached, needs a
  definitive check before the book is changed.**

**Trace time base.** The book assumes 250 M trace cycles at a 3 GHz host = 83.33 ms (§3.1.6 item 11,
Appendix B; every config has `CPUFreq 3000`).
- **What the parser did:** the parser that produced the LBM and GCC traces (`git show 2e8514c:parse_trace.py`)
  converts gem5 ticks with `cycle = int(tick_str) // 1000`, commented "Convert gem5 ticks (ps) to NVMain
  cycles (assuming 1GHz = 1000ps)".
- **Consistent with the data:** trace timestamps have gcd 1 and minimum delta 1 in the first 200,000 records.
  That is consistent with nanoseconds from picosecond ticks, and not with raw picoseconds from a 2 GHz O3
  clock, which would be multiples of 500.
- **So one trace cycle = 1 ns of gem5 time (a 1 GHz basis).** With `CPUFreq 3000`, NVMain replays the program
  3x faster than gem5 ran it: 250 M cycles is 250 ms of program time, not 83.33 ms.
- **VERIFIED 2026-09-15** (`trace_timebase_investigation.md`): 1 trace cycle = 1 ns, confirmed with a gem5
  run. The whole 250 M-cycle window is cached gem5 fast-forward from program start, so the traces are cached
  but the window is start-up, not the O3 region.
- **Scope:** item 11 made all technologies consistent with each other, but at a timeline compressed 3x relative
  to the trace. This touches every per-second rate (endurance), the queueing load behind latency, and LBM
  completion, not only endurance. It must be verified (for example against the gem5 run's recorded
  simulated seconds for the traced instructions) and assessed before any change.

### 4.3 Which write rate?

- **Replay behavior:** the trace reader stalls until the controller accepts a request (`traceMain.cpp:254-293`).
  1T1R SLC replayed exactly the first 6,550,154 LBM records (3,257,597 W, 3,292,557 R, matching the stats to the
  unit). Those records end at trace cycle 22,586,868, only 9% of the window's timeline. 1S1R SLC reached 15.98 M,
  1T1R MLC 12.83 M, 1S1R MLC 7.82 M.
- **LBM's write pattern over time:** 3.61 M and 3.06 M writes in the first two 25 M-cycle bins (lattice
  initialization, 409 MB written once). Then almost nothing, and no writes from 175 M to 275 M cycles. Steady
  state is about 423 k writes per 25 M cycles (275 M to 525 M).
- **Consequence:** the book's rate is ReRAM's saturated throughput during start-up. Because it is
  device-limited, a slower track "lives longer": this is the only reason 1S1R and MLC look better per write.
- **Correct definition:** wear rate = min(workload demand, device write throughput) over a representative
  steady-state stretch.

LBM lifetime (years) under each basis (1T1R SLC 10^7; MLC 10^6 at 16 GB):

| Basis | Writes/s | 8 GB | 64 GB | 128 GB | MLC 16 GB |
|---|---|---|---|---|---|
| Book: ReRAM completed / 83.33 ms | 39.1 M | 1.09 | 8.71 | 17.4 | 0.218 |
| Same writes at their own trace time | 432.7 M | 0.098 | 0.787 | 1.57 | 0.020 |
| Demand (DDR5-admitted, 6,965,793) / 83.33 ms | 83.6 M | 0.509 | 4.07 | 8.15 | 0.102 |
| Write-active span (0.34 M-154.5 M cycles) | 135.5 M | 0.314 | 2.51 | 5.02 | 0.063 |
| Steady state (275 M-525 M), 3 GHz | 50.7 M | 0.839 | 6.71 | 13.4 | 0.168 |
| Long run after start-up (50 M-553 M), 3 GHz | 28.6 M | 1.49 | 11.9 | 23.8 | 0.298 |
| Whole trace, 3 GHz | 62.2 M | 0.684 | 5.48 | 11.0 | 0.137 |
| Demand on the 1 GHz (ns) basis | 27.9 M | 1.53 | 12.2 | 24.4 | 0.305 |
| Steady state, 1 GHz basis | 16.9 M | 2.52 | 20.1 | 40.3 | 0.503 |
| Long run, 1 GHz basis | 9.5 M | 4.47 | 35.7 | 71.5 | 0.893 |

- **Short traces are diluted by the window.** STREAM's 100,000 writes span 1 M cycles (0.14 yr at 8 GB on its
  own timeline) and OFMAP spans 13.5 k cycles. Dividing them by 83.33 ms makes their lifetimes a function of
  the window length, not the workload.
- **Bandwidth check.** LBM demand over 83.33 ms is 5.35 GB/s, above every measured figure in §3.4. That is
  one more hint that the 3 GHz basis overstates rates. The 1 GHz basis gives 1.8 GB/s, inside the measured
  0.9-2.3 GB/s range.

### 4.4 Where the numbers come from

- **The only endurance code is `visualize_slides.py:462-515`**, with hardcoded write counts equal to the raw stats.
- There are no endurance columns in `results/processed_*.csv` and no code in `process_metrics.py` or
  `5_summary_report.py`.
- The MLC and 1S1R lifetimes exist only in documents.
- An independent recomputation (`endurance_audit_runs/lifetime_recompute.*`) matches every book, deck and
  cheat-sheet figure.
- **One stale input:** 3,269,479 writes (pre-idle-gating) in `Post_Meeting_Notes_Shahar_2026-09-03.md`
  item 8 gives 1.08 yr instead of 1.09.

Full recomputed table (years; SLC 10^7, MLC 10^6; each track's own completed writes):

| Track | Trace | Writes | 8 GB | 16 GB | 64 GB | 128 GB |
|---|---|---|---|---|---|---|
| 1T1R SLC | LBM | 3,257,597 | 1.09 | 2.18 | 8.71 | 17.4 |
| 1T1R SLC | GCC | 170,800 | 20.8 | 41.5 | 166 | 332 |
| 1T1R SLC | STREAM | 100,000 | 35.5 | 70.9 | 284 | 567 |
| 1T1R SLC | OFMAP | 13,542 | 262 | 524 | 2,095 | 4,190 |
| 1T1R MLC | LBM | 1,825,508 | 0.194 | 0.389 | 1.55 | 3.11 |
| 1S1R SLC | LBM | 2,288,852 | 1.55 | 3.10 | 12.4 | 24.8 |
| 1S1R MLC | LBM | 1,090,968 | 0.325 | 0.650 | 2.60 | 5.20 |

GCC, STREAM and OFMAP complete identical write counts on all four tracks, so throttling affects LBM only.

### 4.5 Measured wear skew (64-byte lines)

| Metric | LBM, 250 M cycles | LBM, whole (553 M) | GCC, 250 M | GCC, whole (611 M) |
|---|---|---|---|---|
| Writes | 6,965,793 | 11,461,967 | 170,800 | 476,324 |
| Distinct lines written | 6,700,637 (409 MB) | 6,700,638 | 164,665 (10.1 MB) | 452,229 (27.6 MB) |
| Max writes to one line | 7 | 8 | 6 | 13 |
| Top 1% of lines' share | 1.92% | 2.92% | 2.39% | 3.65% |

- **Within the footprint, wear is nearly uniform.** The real skew is footprint vs module: LBM touches 5.0% of
  8 GB, GCC 0.34%.
- **Without wear leveling** (3 GHz basis): LBM's hottest line fails in about 2.7 days, GCC's in about 1.8 days.
  The "ideal uniform wear leveling" assumption is carrying a factor of about 20x (LBM) to 300x (GCC), so a real
  leveling scheme and its efficiency (§3.3 factor 1) are central, not a footnote.
- NVMain cannot report per-location wear here: `EnduranceModel` is unset (NullModel), and even Word/Row models
  expose only worst and average life.
- **MLC programming iterations are not counted as wear.** There is no SET/RESET distinction, and MLC is SLC
  with latency and energy multipliers.

## 5. Claims affected

- **Book:**
  - §3.1.4 prose, the worked equation, Table 5 and its MLC footnote.
  - Table 7 lifetimes (1S1R "longer life" rests on throttling).
  - §3.3 and the Conclusion endurance statements.
  - Appendix A hot-spot bound.
  - §2 workload list and §3.1.6 item 6 ("uncached").
  - §3.1.6 item 11 and Appendix B (3 GHz basis), pending verification.
- **Deck:** slide 33 (Endurance) and its chart; slide 16 ("uncached"); slides 36 and 50 (endurance lines).
- **Other documents:**
  - One-pager `Shahar_Review_Evidence.typ`, row 8.
  - `Post_Meeting_Notes_Shahar_2026-09-03.md` item 8 (stale 3,269,479).
  - `Meeting_Prep_Cheat_Sheet.md` and `Presentation_Outline.md` endurance lines.

## 6. Recommended approach (for the Lead's decision)

1. **Settle the time base first** (1 GHz per the parser vs 3 GHz per the configs). It moves every rate 3x and
   also affects latency and completion across the whole book.
2. **Define the wear rate as min(demand, device throughput) over LBM's steady state**, not its start-up burst,
   and report start-up separately as a transient.
3. **Replace the single number with a sensitivity table** built on Qureshi's formula. Axes:
   - endurance: 10^5 (Gb-class [33]), 10^6, 10^7
   - wear-leveling efficiency: 0.97 and 0.53
   - write reduction: 1x (whole line) and 4.5x (DCW, Zhou)
   - capacity: 8, 64 and 128 GB
   - failure definition: first failure without ECP vs with ECP or spares
4. **Remove the "1S1R lives longer" framing.** With a demand-based rate all tracks see the same wear rate for
   the same work.
5. **Divide STREAM and OFMAP by their own trace spans**, or mark them as window-diluted.
6. **Show Shahar his own formula** (§2) with the book's numbers plugged in, next to the sensitivity table.

## 3.5 Primary papers supplied by the Lead (read in full, 2026-09-15)

Page = PDF page of the extraction. Q = quoted; F = read off a figure; D = derived.

**The book's citation for the endurance ratings does not support them.**
- The book (§3.1.4, lines 1327-1331) says SLC is "typically rated at 10^7 cycles and MLC at 10^6 ... [14]".
- Wong et al. [14] gives **no SLC/MLC rating at all**.
  - Its Table 4 (p.15) lists single lab devices from 100 to 10^12 cycles. The only entry near 10^7 is one 10 nm
    Hf/HfOx cell at 5x10^7.
  - Its only MLC endurance is WOx: under 100 cycles without verify, over 8,000 per state with verify (p.13).
- Y. Chen, TED 2020 (invited review):
  - "for SCM application, **10^6 cycle is the typical spec**"; "10^4 cycle is typically the lower limit" for
    embedded 1T1R; NAND replacement "few thousands and 10^6" (Q, p.7).
  - Lab records reach 10^12 (p.7). "Most of the ReRAM devices could only operate reliably in SLC" (p.9).
- EMBER [31] (TSMC 40 nm HfOx 1T1R, 6,144 cells tested): "10 K for 1-2 b/cell" (Q, p.1, p.8).
- Micron/Sony 16Gb (Zahurak IEDM 2014): BER reported through 10^5 cycles only (Table 2).
- TSMC 22nm (Chou VLSI 2020): qualified at 10K cycles.
- Zangeneh and Joshi (TVLSI 2014) tabulate RRAM at 10^8, from a 180 nm device [Chiang VLSI 2009].

**Consequence.** No supplied source gives 10^7 as a product rating. The best-sourced planning value for a Gb-class
storage-class memory is **10^6** (Chen), with **10^4** as the measured array floor (EMBER, TSMC) and 10^10-10^12 as
single-device lab results.

**MLC wear and latency.**
- Le et al. [13] (130 nm HfOx, 4 Kbit arrays): 2 b/cell needs 3 program iterations (RESET+SET each), fresh and after
  4K cycles; 3 b/cell needs 7-9, rising to 11 after 4K cycles (Q, p.5). This is an upper bound on extra wear per
  MLC write if endurance is counted in RESET/SET pairs.
- If endurance is counted in write operations, as EMBER's 10K is, there is no extra multiplier. Do not double count.
- **Where the book's 3.263x MLC write multiplier comes from:** exactly 12.4 / 3.8 Mbps, EMBER's write throughput per
  bit (p.9, Table II). Details:
  - It is a per-bit throughput ratio, measured before cycling.
  - It pairs allocations with unequal BER (3.08e-4 vs 2.36e-3).
  - Per 48-cell word it is **6.5x**. The low-BER pairing used in the endurance test gives 6.48x (Table I).
  - Read: 1.5x per bit, **3x per fixed word** (2 vs 6 cycles at 10 ns, p.8).
- The book's claim that the multipliers are "measured on the same EMBER macro" is correct. Labelling them latency
  multipliers is only partly supported: they are throughput ratios.

**Variation.**
- None of the six papers gives a distribution of cycles to failure.
- The first-failure factor in §3.2 (x0.31 at CoV 0.1) remains a derivation with no source.
- Le's 16-28% CoV is a resistance CoV, not an endurance CoV.
- EMBER relies on BCH error correction (BER < 3e-3), which supports a "with ECC" failure definition.

**Other [14] sentences in the book** (filament mechanism, 10x10 nm ns switching, variability as the barrier,
sub-10 nm filaments) are SUPPORTED. The access-transistor sizing sentence (line 2603) is PARTLY SUPPORTED.

## 7. Corrected sensitivity on the verified 1 ns time base

Script and output: `endurance_audit_runs/sensitivity_v2.py`, `sensitivity_v2.txt`.
lifetime = lines x E x wear-leveling efficiency x write reduction / (min(demand, device write cap) x s/yr).

**Demand rates (1 trace cycle = 1 ns):**

| Basis | LBM | GCC |
|---|---|---|
| Book's admitted population, 0-250 M ns (start-up, fast-forward) | 27.86 M writes/s | 0.68 M/s |
| After initialization, 50 M-517 M ns (fast-forward) | 9.53 M/s | n/a |
| O3 region of interest, deduplicated | 9.54 M/s | 0.90 M/s |

**LBM's steady-state write demand is 9.5 M writes/s by two independent regions**, 4.1x below the book's 39.1 M/s. It
is also below every track's write cap (1T1R SLC 39.1, 1S1R SLC 27.5, 1T1R MLC 21.9, 1S1R MLC 13.1 M/s), so no
track is throttled. **All tracks wear at the same rate**, and the "1S1R lives longer" framing disappears.

**1T1R SLC, LBM steady state, wear-leveling efficiency 0.97 (years):**

| Endurance E | 8 GB | 64 GB | 128 GB | 64 GB with write reduction 4.5x |
|---|---|---|---|---|
| 10^4 (array floor: EMBER, TSMC) | 0.004 | 0.035 | 0.069 | 0.16 |
| **10^6 (SCM spec, Chen 2020)** | **0.43** | **3.5** | **6.9** | **15.6** |
| 10^7 (book) | 4.3 | 34.7 | 69.3 | 156 |

For comparison, the start-up window (27.9 M/s) at E = 10^6 gives 0.15 / 1.19 / 2.37 yr, and GCC's O3 region at
E = 10^6 gives 4.6 / 36.7 / 73.3 yr.

**Shahar's template** (endurance needed for 10 years, 64 GiB, ideal leveling, whole line per write):

| Basis | Required endurance |
|---|---|
| LBM start-up | 8.2x10^6 |
| **LBM steady state** | **2.8x10^6** |
| GCC | 2.0-2.6x10^5 |

**Reading.** At the storage-class-memory spec (10^6):
- A 64 GB module under continuous LBM lasts 3.5 years with good wear leveling. It needs 128 GB, or a data-comparison
  write scheme, to reach the 5-10 year server target.
- A compute-bound workload (GCC) clears it at any capacity.
- **This is one sourced, time-base-correct answer to Shahar's question:** LBM needs about 3x10^6 cycles for ten years
  at 64 GB. That is above the SCM spec and far below lab records.

**Decisions for the Lead:**
1. Endurance value: 10^6 (sourced SCM spec) as primary, with 10^7 and 10^4 as bounds. Replace the [14] citation for
   the ratings with Chen 2020, keeping Lanza [15] and Hellenbrand [46].
2. Rate basis: LBM steady state (9.5 M/s). Start-up is reported as a transient.
3. MLC: endurance counted in write operations (EMBER), so no extra wear multiplier. Label the latency multipliers
   as per-bit throughput ratios, with the per-word 3x read / 6.5x write as a sensitivity.
