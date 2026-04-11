# Phase 1 - NVSim Physics (Device Level)

| Target Architecture | LRS (Ω) | HRS (Ω) | Resistance Ratio (HRS/LRS) |
| :--- | :--- | :--- | :--- |
| reram_22nm_1t1r_mlc | $1 \times 10^{5}$ | $1 \times 10^{9}$ | $1 \times 10^{4}$ |
| reram_22nm_1t1r_slc | $1 \times 10^{5}$ | $1 \times 10^{9}$ | $1 \times 10^{4}$ |
| reram_22nm_selector_mlc | $1 \times 10^{5}$ | $1 \times 10^{9}$ | $1 \times 10^{4}$ |
| reram_22nm_selector_slc | $1 \times 10^{5}$ | $1 \times 10^{9}$ | $1 \times 10^{4}$ |

# Phase 2 - NVMain Architecture (System Level)

| System Configuration | Timing (tCAS/tRCD/tRP) | Latency (ns) | StandbyPower (W) |
| :--- | :--- | :--- | :--- |
| 2D_DRAM_example | — | 31.16 | — |
| 3D_DRAM_example | — | 18.54 | — |
| DDR5_4800_DRAM | 34–34–34 | 73.07 | — |
| reram_22nm_1t1r_mlc | — | 101.99 | 794.6560 |
| reram_22nm_1t1r_slc | — | 45.07 | 794.6560 |
| reram_22nm_1t1r_slc_16chip | — | 44.82 | 12.7145 |
| reram_22nm_1t1r_slc_8chip | — | 44.73 | 6.3572 |
| reram_22nm_1t1r_slc_full_dimm | — | 46.00 | 50.8580 |
| reram_22nm_1t1r_slc_single | — | 44.73 | 0.7947 |
| reram_22nm_selector_mlc | — | 158.05 | 16.9070 |
| reram_22nm_selector_slc | — | 63.28 | 16.9070 |
| reram_22nm_selector_slc_16chip | — | 62.98 | 0.2705 |
| reram_22nm_selector_slc_8chip | — | 62.82 | 0.1353 |
| reram_22nm_selector_slc_full_dimm | — | 64.48 | 1.0820 |
| reram_22nm_selector_slc_single | — | 62.82 | 0.0169 |
