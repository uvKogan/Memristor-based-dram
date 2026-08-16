# system_v2_2 — retroactive config reconstruction (cycle 7, Task 5)

`results/` never snapshotted the exact configs consumed by each run before
this cycle, and configs on disk can drift after the fact (see the cycle-6c
independent verification report — this is exactly the bug this snapshot
policy exists to prevent). This directory is a best-effort, retroactive
reconstruction for `system_v2_2`, with honest limits stated per technology.

## Fully reconstructed (16 files, `<model>.reconstructed.txt`)
All 16 ReRAM configs set `PrintConfig true`, so their stats files embed a
full `KEY = VALUE` dump of every parameter NVMain actually parsed for that
run. Extracted verbatim from `stats_<model>_stream.out`'s dump block. **Not**
byte-identical to the original `.config` file (comments, formatting, and
key ordering are lost — only the parsed key/value pairs survive), but a
complete, accurate record of every value NVMain used.

## Snapshotted as-is (2 files)
`2D_DRAM_example.config`, `3D_DRAM_example.config` — copied directly from
`simulators/nvmain/Config/` as of 2026-07-12. Neither cycle 6c nor cycle 7
touched these technologies (they're the excluded/control set), so the
current on-disk files are confirmed still valid for `system_v2_2`.

## Cannot be reconstructed (DDR5, PCM)
Neither `DDR5_4800_DRAM.config` nor `pcm_microsoft_2009.config` set
`PrintConfig`, so their `system_v2_2` stats files carry no embedded dump —
there is no mechanism to recover the exact parsed state after the fact.
What IS documented, in lieu of a snapshot:
- **DDR5**: `system_v2_2` was generated before the finding #8b calibration —
  the pre-calibration EIDD placeholder values are recorded in
  `results/cycle6c_ddr5_calibration_and_provenance_report.md`'s "old
  (placeholder)" column, and the pre-finding-#7 refresh timing in that same
  file's config-diff section.
- **PCM**: `system_v2_2` was generated under the finding #9 bug (`CLK 800`
  silently overriding `CLK 400`, `Ewrpb` silently zeroed) — both the buggy
  and fixed states are fully documented in
  `results/cycle7_final_calibration_report.md`'s Task 2 section.

Going forward (`system_v3` and later), every generation gets a live
`configs_used/` snapshot at simulation time — see `archive/README.md` for
the policy.
