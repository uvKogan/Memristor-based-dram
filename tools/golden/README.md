# NVMain regression golden files

## What these are

This directory holds the frozen reference inputs and expected outputs for
`tools/nvmain_regress.sh`, the regression harness that guards the upcoming
NVMain C++ patches (end-to-end latency stat, wear counter, Start-Gap decoder).

- `configs/*.config`: frozen copies of the three reference NVMain configs
  (`reram_22nm_1t1r_slc_full_dimm`, `DDR5_4800_DRAM`, `pcm_microsoft_2009`),
  copied from `simulators/nvmain/Config/` at record time. The harness always
  runs against these frozen copies, never against the live `Config/` tree, so
  a later task that regenerates the live ReRAM configs cannot silently change
  what this harness compares against.
- `*.golden`: for each config, the sorted set of pre-existing `i0.`-prefixed
  statistic lines produced by running `nvmain.fast` against the reference
  trace `benchmarks/gpt2_ifmap.nvt` for 20000 cycles, on the unpatched tree.

## When to re-record

Only re-record (`tools/nvmain_regress.sh --record`) when a *deliberate*
change to a frozen config or to the reference trace is intended, and the
resulting shift in pre-existing statistics has been reviewed and is expected.
Re-recording overwrites both the frozen configs (from the then-current
`simulators/nvmain/Config/`) and the golden stat files, so it establishes a
new baseline; do it deliberately, not as a way to make a failing comparison
pass. A change to NVMain C++ source that alters pre-existing statistics
should FAIL this harness, not be papered over by re-recording.

## What is filtered out by design

The comparison only covers statistics that existed before the three planned
patches. Newly introduced statistics are intentionally excluded from both the
golden files and the live comparison, via `grep -vE`:

- `EndToEnd*` (end-to-end latency stat patch)
- `unstampedRequests` (end-to-end latency stat patch)
- `wear*` (wear counter patch)

This lets the harness prove that each patch leaves every pre-existing
statistic bit-identical, without the harness itself needing to know the
exact values the new stats should report.
