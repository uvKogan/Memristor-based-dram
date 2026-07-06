# Hardware Configurations & Physics Baselines
[cite_start]**Context**: Stores `.cell` and `.cfg` hardware definitions.

## 🔬 PHYSICAL TARGETS
* [cite_start]**Resistance Window**: LRS = 10^5 Ohms, HRS = 10^9 Ohms (Matsui et al. 2025 calibration)[cite: 66, 176].
* [cite_start]**1T1R Track (Logic-Compatible)**: Access transistors target ~20 F^2[cite: 113, 205].
* [cite_start]**1S1R Track (Storage-Class Selector)**: Idealized crossbar targets 4 F^2[cite: 113]. [cite_start]Requires `-AccessType: Diode` and Nonlinearity (Kr=10^6) for crossbar stability[cite: 14].
* **MLC Penalty**: Modeled heuristically in the Python pipeline. [cite_start]Expect 3x Read / 4x Write latency and energy penalties for 2-bit MLC vs SLC[cite: 66, 98].