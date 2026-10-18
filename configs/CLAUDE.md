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
  `--endurance-model`, `--freq`, `--write-pulse-on-path`) therefore reach the
  ReRAM/silicon configs only - never the DDR5 or PCM baselines.
* Timing mapping in those generated configs: the NVSim **read** latency is split
  once across `tRCD` + `tCAS`, and the NVSim cell **write** latency goes to `tWR`
  (write recovery) - or, with `mbmm_master.py --write-pulse-on-path`, to `tWP`
  with `tWR 1`. Both splits are enforced by
  `3_gen_nvmain_config.validate_config()`, which re-reads them out of the
  rendered config text before the file is written.
* **What the two write modes actually differ in, and for which writes**
  (corrected twice, 2026-09-22: the original "delays only the next precharge" was
  wrong, and so was the first correction's unconditional "the delta is the
  completion event" - the answer depends on the branch the write takes).

  Scope first: `nextActivate`, `nextPrecharge`, `nextRead` and `nextWrite` are
  **`SubArray` members** (`SubArray.h:137-140`), and a bank holds
  `ROWS / MATHeight` subarrays (`DDR3Bank.cpp:129`) - one for the SLC full DIMM,
  two for MLC. Everything below therefore blocks the write's own **subarray**,
  not the whole bank.

  In **default** mode the cell write time sits in `tWR` and reaches the request
  path **only when a write closes its row**. `MemoryController::IsLastRequest`
  (`MemoryController.cpp:1114-1144`) decides which: under `ClosePage 1` it
  returns false as soon as another queued request hits the same
  rank/bank/row/subarray, and only a true result sets `FLAG_LAST_REQUEST`.
  - **Last queued request to its row** -> `WRITE_PRECHARGE`
    (`MakeImplicitPrechargeRequest`, `:1055-1063`, called at `:1596` and `:1658`
    under the `FLAG_LAST_REQUEST` guards at `:1594` and `:1653`). NVMain adds
    `tWR` to the subarray's next activation (`SubArray.cpp:625-629`) and MAXes
    `nextPrecharge`/`nextRead`/`nextWrite` against it (`:631-633`), so the next
    read or write to that subarray waits for it.
  - **Another queued request to the same open row** -> the plain `WRITE` branch
    (`SubArray.cpp:648-660`). `tWR` reaches only `nextPrecharge` (`:648-651`);
    `nextRead` (`:653-656`) and `nextWrite` (`:658-660`) carry `writeTimer` but
    **no `tWR`**, so nothing beyond the burst and the write-to-read turnaround
    (`tWTR`, NVMain's default of 5 because these configs never emit the key, and
    identical in both modes) is charged.

  In **neither** branch does the cell write time delay the write's own completion
  event (`writeEventTime`, `:671-672`, carries `writeTimer` alone).

  **Bounding** mode moves the same cycle count to `tWP` (`tWR` becomes one
  cycle). `tWP` is what `WriteCellData` returns (`:991`) and so becomes
  `writeTimer` (`:581`): every write's completion carries the pulse, and in the
  plain `WRITE` branch `nextRead` and `nextWrite` on that subarray carry it too,
  while in the `WRITE_PRECHARGE` branch the subarray's next activation is
  unchanged to within one cycle.

  **The delta between the modes is therefore the write's own completion latency
  with the pulse excluded versus included, plus, for open-row writes, the
  subarray time that default mode did not charge. It is an upper end of the
  write-path cost, not a prediction** - how the two effects mix in a given run is
  set by the trace's row locality and the queue depth, so quote a T3 number with
  that qualification and not as a single mechanism.
* The `Run_*` provenance columns describe the **run**, not the individual config,
  so `Run_Write_Pulse_On_Path` reads `true` on the DDR5 and PCM rows too although
  the flag never reaches their static configs (the same already holds for
  `Run_Queue_Size`, `Run_Decoder` and `Run_Freq_MHz`).
