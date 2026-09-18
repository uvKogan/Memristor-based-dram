# NVMain prototype patches (2026-09-18)

**Origin:** both patches were built and verified as prototypes in the session scratchpad
(`nvmain_probe/`) on 2026-09-18, per `revision_plan.md` §"NVMain prototype findings (2026-09-18)".
The live repo under `simulators/nvmain/` was untouched by the prototype work; these diffs are
preserved here so the patches survive past the session. Both prototypes verified bit-identical
pre-existing statistics against the unpatched build on the reference trace before being recorded.

## Files

- `partA_e2e_latency.diff` (116 lines): adds an end-to-end latency statistic
  (`averageEndToEndLatency`) to `MemoryController`, stamped from a new `traceCycle` field on
  `NVMainRequest`.
- `partB_wear_map.diff` (199 lines): adds a measured per-location write counter
  (`writeCounts[addr]++` in `EnduranceModel::DecrementLife`) and wear-distribution stats in
  `SubArray::CalculateStats`.
- `skew.nvt`, `sparse.nvt`: small synthetic traces used to verify the two patches (a deliberately
  skewed-address trace for the wear map, and a low-backlog trace for an end-to-end latency
  correctness check). `sparse.nvt` (29 KB) is committed directly. `skew.nvt` (2.9 MB) is **not**
  committed; it is generated locally, see below.
- `gen_skew.py`: regenerates `skew.nvt`. Run `python3 gen_skew.py` from this directory (or
  `python3 gen_skew.py --out <path>` for a different location) before running the wear-map
  verification. Writes 20,000 write requests (cycle stepping by 4), address `0x40` with
  probability 0.8 and otherwise a uniformly random 64-byte-aligned address in `[0, 0x100000)`,
  64 zero-byte payload, thread 0, seeded (`--seed`, default 1234) for reproducibility.

**Note on `skew.nvt` provenance:** the file originally produced by the 2026-09-18 prototype session
was hand-verified (16,015 / 20,000 writes to the hot address, matching the ~80% skew) but was not
itself reproducible byte-for-byte from an unknown RNG call sequence, so it is not committed. Its
sha256 is recorded here for the record: `c5b5f220465579725ac83f6997d24d23f61ee82191193bbfd48e6b0d4479871c`.
From this revision on, `gen_skew.py` (seed 1234) is the source of truth for `skew.nvt`; the file it
produces (sha256 `15906b315e5c3198f64101d327c6ad659b1d38fcda39d3d4efc586a00270f04c`) is what is used
locally for T1.3 and is structurally equivalent (same op mix, same ~80% hot-address skew, same
address-space bounds) but not byte-identical to the original prototype run.

## Clock-domain conversion note (Part A)

The trace's own timestamp (`traceCycle`, stamped from `tl->GetCycle()` in `traceSim/traceMain.cpp`)
lives in the **`CPUFreq`** (global event-queue) domain, while `arrivalCycle`, `completionCycle`, and
the rest of the memory-controller-side cycle fields live in the **`CLK`** (local/memory) domain.
These two domains run at different frequencies (3000 MHz vs 800 MHz here, a factor of 3.75), so the
patch converts `traceCycle` into the local `CLK` domain (multiplying by `localFreq / globalFreq`)
before subtracting it from the completion cycle. Without this conversion the new statistic would not
be in the same unit as `averageTotalLatency`.

## Measured result

GPT-2 IFMAP trace, 1T1R SLC full DIMM: `averageTotalLatency` **364.1** memory cycles versus
`averageEndToEndLatency` **9,709.7** memory cycles, a queue-full wait about 26.7x the reported
latency (roughly 11.7 microseconds at 800 MHz). Every pre-existing statistic was bit-identical to
the unpatched build on this trace. PCM under FRFCFS-WQF shows the same pattern (486.1 vs 9,866.0).
A correctness check on `sparse.nvt` (a trace with no backlog) gave 77.70 vs 77.36 cycles, the small
remaining gap being sub-cycle truncation.

See `revision_plan.md` for the full findings, including the wear-map prototype (Part B) and the two
config defects found along the way.
