# MBMM Project Book — Remaining Edits (Post Pipeline Fix)
**Updated:** 2026-06-13 (Session 27)
**Status:** Session 26 edits already applied. This file contains ONLY the re-edits required because the power extraction bug (median→max) changed EDP values after those edits were made.

**What changed:** For GPT-2 IFMAP and AlexNet IFMAP/OFMAP workloads, the trace data concentrates in rank 0 of the 8-rank DIMM. The old pipeline's median power picked an idle rank (~0.067 W). The correct max picks rank 0 (the active rank). This increased power — and therefore EDP — for those benchmarks only. GCC, LBM, STREAM are unaffected (all ranks uniformly loaded).

---

## Priority Table

| # | Section | Find (what you wrote in Session 26) | Urgency |
|---|---------|--------------------------------------|---------|
| A | 3.1.1 GPT-2 | "EDP of **41.24** vs. 1T1R SLC's **79.46**" | ✅ Already correct |
| B | 3.1.3 GCC/GPT-2 EDP | "1T1R SLC (**24.45**) comprehensively defeats…PCM…(**52.67**)" | 🔴 Re-do |
| C | 3.1.3 AlexNet EDP | "moderate EDP increase (**21.19 to 63.15**)…spikes to **222.95**" | 🔴 Re-do |
| D | 3.3 Fig 24 geo-mean | "1T1R SLC (**23.25**) and 1S1R SLC (**33.93**)…DDR5-4800 (**52.34**)…MLC (55.12)…(89.33)" | 🔴 Re-do |
| E | Injection B | "more than double the 0.066–0.069 W of the equivalent 22nm ReRAM" | 🟡 Re-do |
| F | 3.1.1 GCC latency | "Energy-Delay Product of 5.54…DDR5 (EDP 24.58)" | 🟢 Optional minor |
| G | 3.1.1 LBM latency | "EDP of 100.16 against 1T1R SLC's 33.04" | 🟢 Optional minor |

> Note: Change 4 (GPT-2 latency) — if you applied the Session 26 replacement text it already contains the corrected latency values (366.80 cycles / 458.50 ns / 236.16 cycles / 98.40 ns). Only the EDP sentence at the end changed. Check item A below.

---

## ITEM A — Section 3.1.1 · GPT-2 Latency (verify only)

The Session 27 replacement text for Change 4 already had the correct EDP framing. If you applied the text from the updated checklist, it reads:

> "…DDR5 achieves a superior EDP of **41.24** vs. 1T1R SLC's **79.46** — DDR5 wins on both latency and total efficiency…"

**If you applied this version: nothing to do.**

If you applied the Session 26 version which ended with:
> "…yielding competitive EDPs of 24.45 (1T1R SLC) vs. 41.20 (DDR5), confirming that ReRAM's power advantage partially offsets its latency deficit even under heavy AI read pressure."

**Find:**
```
yielding competitive EDPs of 24.45 (1T1R SLC) vs. 41.20 (DDR5), confirming that ReRAM's power advantage partially offsets its latency deficit even under heavy AI read pressure.
```

**Replace with:**
```
Under AI inference, DDR5 achieves a superior EDP of 41.24 vs. 1T1R SLC's 79.46 — DDR5 wins on both latency and total efficiency because the 4.7× latency advantage outweighs ReRAM's power profile. ReRAM's advantage for AI inference deployment lies in its zero-leakage standby power for sustained, thermally-constrained inference where long-run energy budget matters more than per-request EDP.
```

---

## ITEM B — Section 3.1.3 · Figure 13 (GPT-2 EDP) 🔴

The Session 26 text you applied claimed 1T1R SLC beats PCM on GPT-2 EDP. With the corrected power, 1T1R SLC EDP = 79.46 — which is *worse* than both DDR5 (41.24) and PCM (52.67).

**Find:**
```
1T1R SLC (24.45) comprehensively defeats the historical Microsoft PCM 2009 baseline [11] (52.67)
```
*(or with bold markdown if the editor preserved it: `1T1R SLC (**24.45**) comprehensively defeats…(**52.67**)`)*

**Replace with:**
```
DDR5-4800 achieves the best EDP (41.24), with 1T1R SLC reaching 79.46 — DDR5 wins here because its 4.7× latency advantage over ReRAM outweighs ReRAM's lower static power profile. PCM (52.67) falls between DDR5 and ReRAM SLC, as its lower access power partially compensates its high latency.
```

Also update the GCC sentence in the same paragraph:

**Find:**
```
5.54, making it 4.4× more efficient than state-of-the-art DDR5-4800 (24.58)
```

**Replace with:**
```
5.57, making it 4.4× more efficient than state-of-the-art DDR5-4800 (24.59)
```

---

## ITEM C — Section 3.1.3 · Figures 16 & 17 (AlexNet EDP) 🔴

**Find:**
```
moving from 1T1R SLC to the ultra-dense 1S1R MLC topology incurs a moderate EDP increase (21.19 to 63.15). However, under the write-heavy AlexNet OFMAP trace, the 1S1R MLC EDP catastrophically spikes to 222.95.
```
*(numbers may appear with bold formatting)*

**Replace with:**
```
moving from 1T1R SLC to the ultra-dense 1S1R MLC topology incurs an EDP increase (61.19 to 107.49). However, under the write-heavy AlexNet OFMAP trace, the 1S1R MLC EDP catastrophically spikes to 260.12.
```

---

## ITEM D — Section 3.3 · Figure 24 (Geo-Mean EDP) 🔴

**Find:**
```
1T1R SLC (23.25) and 1S1R SLC (33.93) strictly dominate the legacy Microsoft PCM 2009 baseline (150.74) and outperform DDR5-4800 (52.34)
```
*(numbers may appear with bold formatting)*

**Replace with:**
```
1T1R SLC (37.03) and 1S1R SLC (49.58) dominate the legacy Microsoft PCM 2009 baseline (150.74) and outperform DDR5-4800 (52.38), confirming that zero-leakage non-volatile physics yield superior global efficiency across general computing workloads. The 1S1R SLC margin over DDR5 is narrow (49.58 vs. 52.38), reflecting that AI-inference workloads partially erode ReRAM's efficiency advantage.
```

Also update the MLC sentence immediately after:

**Find:**
```
1T1R MLC (55.12) and 1S1R MLC (89.33) trail DDR5
```

**Replace with:**
```
1T1R MLC (73.11) and 1S1R MLC (110.78) trail DDR5
```

---

## ITEM E — Injection B (BL16 sentence power range) 🟡

**Find:**
```
more than double the 0.066–0.069 W of the equivalent 22nm ReRAM configuration — directly inflating its EDP relative to the non-volatile baseline.
```

**Replace with:**
```
Under compute-bound workloads (GCC, LBM, STREAM), where memory requests spread evenly across the full DIMM, 22nm ReRAM draws only 0.069–0.088 W — less than half DDR5's power, directly yielding its EDP advantage. Under AI inference (GPT-2), where the active footprint concentrates in a single DIMM rank, ReRAM's per-rank dynamic power rises to ~0.217 W, erasing the power advantage and explaining why DDR5 wins on EDP for that workload.
```

---

## ITEM F — Section 3.1.1 GCC latency (minor) 🟢

**Find:** `Energy-Delay Product of 5.54 — 4.4× more efficient than DDR5 (EDP 24.58)`

**Replace with:** `Energy-Delay Product of 5.57 — 4.4× more efficient than DDR5 (EDP 24.59)`

---

## ITEM G — Section 3.1.1 LBM latency (minor) 🟢

**Find:** `EDP of 100.16 against 1T1R SLC's 33.04 — a 3.0× efficiency advantage`

**Replace with:** `EDP of 100.17 against 1T1R SLC's 33.07 — a 3.0× efficiency advantage`

---

## Full Validated Number Reference Table

### Latency & EDP — full DIMM, key benchmarks

| Config | Benchmark | Cycles | Latency (ns) | EDP |
|--------|-----------|--------|--------------|-----|
| DDR5-4800 | gcc | 180.34 | 75.14 | 24.59 |
| 1T1R SLC | gcc | 80.22 | 100.28 | 5.57 |
| DDR5-4800 | lbm | 652.10 | 271.71 | 100.17 |
| 1T1R SLC | lbm | 374.38 | 467.97 | 33.07 |
| 1S1R MLC | lbm | 1545.40 | 1931.75 | 112.87 |
| DDR5-4800 | stream | 659.87 | 274.95 | 101.19 |
| 1T1R SLC | stream | 473.17 | 591.46 | 38.53 |
| DDR5-4800 | gpt2 | 236.16 | 98.40 | 41.24 |
| 1T1R SLC | gpt2 | 366.80 | 458.50 | 79.46 |
| PCM | gpt2 | 726.41 | 908.01 | 52.67 |
| 1S1R MLC | alexnet_ifmap | 947.18 | 1184.0 | 107.49 |
| 1T1R SLC | alexnet_ifmap | 317.86 | 397.33 | 61.19 |
| 1S1R MLC | alexnet_ofmap | 3344.30 | 4180.4 | 260.12 |
| 1S1R SLC | alexnet_ofmap | 1084.65 | 1355.8 | 104.23 |

### Power — full DIMM (corrected: max-rank power extraction)

| Config | gcc | gpt2 | lbm | alexnet_ifmap |
|--------|-----|------|-----|---------------|
| 1T1R SLC | 0.069 W | **0.217 W** ⚠ | 0.088 W | **0.192 W** ⚠ |
| 1T1R MLC | 0.069 W | 0.141 W | 0.077 W | 0.132 W |
| 1S1R SLC | 0.069 W | 0.180 W | 0.083 W | 0.164 W |
| 1S1R MLC | 0.071 W | 0.118 W | 0.073 W | 0.113 W |
| DDR5-4800 | 0.136 W | 0.175 W | 0.154 W | 0.164 W |

⚠ GPT-2 and AlexNet IFMAP power is high because the small trace concentrates all requests in rank 0 of the 8-rank DIMM. GCC/LBM/STREAM spread requests evenly, giving low per-rank power.

### Geo-Mean EDP (across all benchmarks, full DIMM)

| Technology | Geo-Mean EDP |
|-----------|-------------|
| 1T1R SLC | **37.03** |
| 1S1R SLC | **49.58** |
| DDR5-4800 | **52.38** |
| 1T1R MLC | 73.11 |
| 1S1R MLC | 110.78 |
| PCM 2009 | **150.74** |

### Area Density Ratios (Higher = Denser than DDR5) — unchanged

| Technology | Ratio | Physical meaning |
|-----------|-------|-----------------|
| 1S1R MLC | 3.8445× | 3.84× denser than DDR5 |
| 1S1R SLC | 1.9222× | 1.92× denser than DDR5 |
| DDR5-4800 | 1.0000× | Baseline |
| 1T1R MLC | 0.4419× | 2.3× less dense than DDR5 |
| 1T1R SLC | 0.2209× | 4.5× less dense than DDR5 |
