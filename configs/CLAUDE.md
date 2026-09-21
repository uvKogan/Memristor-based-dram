# Hardware Configurations & Physics Baselines
[cite_start]**Context**: Stores `.cell` and `.cfg` NVSim hardware definitions, and the two
static tracked NVMain `.config` DDR5 baselines.

## 🔬 PHYSICAL TARGETS
* [cite_start]**Resistance Window**: LRS = 10^5 Ohms, HRS = 10^9 Ohms (Matsui et al. 2025 calibration)[cite: 66, 176].
* [cite_start]**1T1R Track (Logic-Compatible)**: Access transistors target ~20 F^2[cite: 113, 205].
* [cite_start]**1S1R Track (Storage-Class Selector)**: Idealized crossbar targets 4 F^2[cite: 113]. [cite_start]Requires `-AccessType: Diode` and Nonlinearity (Kr=10^6) for crossbar stability[cite: 14].
* **MLC Penalty**: derived analytically in `2_extract_hardware_metrics.py`
  (`apply_mlc_penalty`), not by a separate NVSim run. The multipliers are
  **read latency x1.5, write latency x3.263, read energy x1.1, write energy x3.0,
  capacity x2**. Sources: Levy et al., IEEE JSSC 2024 (DOI 10.1109/JSSC.2024.3387566),
  Section V.A / Abstract, for the two latency multipliers and the write energy;
  Upton et al., ESSCIRC 2023, Table I, for read energy. The older "3x Read /
  4x Write" figures were unsourced (book audit items 13-14) and are **retired** -
  do not quote them.

## 🧱 FORCED ORGANIZATION (T2.6)
* Every ReRAM `.cfg` here forces its array organization instead of letting NVSim
  explore: **2048 x 2048 subarray at Senseamp Mux 64**, via
  `-ForceBank (Total AxB, Active CxD): 16x4, 1x4`,
  `-ForceMat (Total AxB, Active CxD): 2x2, 2x2` and `-ForceMuxSenseAmp: 64`
  (with `-ForceMuxOutputLev1/2: 1`). NVSim reports it as
  `Subarray Size : 2048 Rows x 2048 Columns` and `Senseamp Mux : 64`.
* `nvsim_common.check_forced_organization()` gates on that literal line: a run
  that exits 0 but explored its own organization, or that printed
  "cannot be found" for a misspelled force key, **fails the stage**. Both
  `1_run_nvsim_hardware.py` and `4_execute_simulation.py` apply the gate.
* `reram_22nm_1t1r_slc_1024.cfg` and `reram_22nm_selector_slc_1024.cfg` are the
  **1024 x 1024 mux-64 sensitivity variants** (`-ForceBank ...: 32x8, 1x8`), selected
  with `mbmm_master.py --organization 1024`. `nvsim_common.SENSITIVITY_1024_RE`
  requires `_1024` to be the last token (optionally followed by an architecture
  suffix), so a cfg must be named `<base>_1024[_<arch>].cfg` to be gated at 1024.
* `<base>_single.cfg`, `_8chip.cfg`, `_16chip.cfg`, `_full_dimm.cfg` are
  per-architecture **copies of their base cfg**, refreshed by `mbmm_master.py` when
  the base changes. They exist only so `4_execute_simulation.py`'s `skip_nvsim()`
  re-runs the organization gate once per architecture; the
  `results/hardware/<base>_<arch>_results.txt` files they produce are deliberately
  ignored by `2_extract_hardware_metrics.py` (`ARCHITECTURE_SUFFIXES`).

## 📄 NVMAIN CONFIGS IN THIS DIRECTORY
* `DDR5_4800_DRAM_subchannel.config` (primary baseline, two 32-bit subchannels,
  64 B per access) and `DDR5_4800_DRAM_64B.config` (64 B-bus cross-check) are
  **static tracked files**, not generated. They are mirrored into
  `simulators/nvmain/Config/`, and `tools/check_live_configs.py` fails if the two
  copies ever diverge (`mbmm_master.py` runs it as a fail-fast before Stage 4;
  `--sync` repairs).
* Every ReRAM and T2.8 silicon `.config` is **generated per run** by
  `3_gen_nvmain_config.py` straight into `simulators/nvmain/Config/` and is not
  tracked here. Generator flags (`--queue-size`, `--channels`, `--decoder`,
  `--endurance-model`, `--freq`) therefore reach the ReRAM/silicon configs only -
  never the DDR5 or PCM baselines.
