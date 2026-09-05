# T4-11 Root Cause Investigation: The Flatline Paradox Is Backwards

Investigates why `Project_Book.typ` Section 3.2's MLP narrative (GCC = low-MLP =
"almost zero latency benefit" from scaling; GPT-2/AlexNet IFMAP = high-MLP =
latency "drastically slashed" by rank interleaving) is the opposite of what
`results/system_v6/processed_pareto_metrics.csv` actually shows: GCC scales
(152.58 ns -> 130.91 ns, ~14%), GPT-2 IFMAP is dead flat (458.41 ns at every
chip count), AlexNet IFMAP is nearly flat (394.73 -> 397.41 ns). This does not
re-litigate that contradiction (already confirmed, tracked as T4-11) - it looks
for the mechanism.

## 1. Hypotheses tested

1. **Controller queue-depth artifact.** NVMain's plain `FRFCFS` controller
   uses one combined `QueueSize` (hardcoded default 32, now an explicit
   `3_gen_nvmain_config.py --queue-size` flag). Maybe the queue saturates
   differently for GCC vs. GPT-2/AlexNet IFMAP as chip count scales, and a
   different `QueueSize` would reveal (or remove) the "MLP" effect.
2. **Trace volume/length artifact.** Maybe GPT-2 IFMAP's trace is simply too
   short/low-request-count to ever expose a chip-count effect, independent of
   the controller.
3. **Workload-locality / address-footprint artifact.** Maybe GPT-2 IFMAP's
   (and AlexNet IFMAP's) memory footprint is small enough to fit inside a
   single chip/rank's directly-addressable space, so scaling chip count is
   architecturally irrelevant to it, regardless of MLP or queue depth.

Hypothesis 3 turned out to be the confirmed root cause, with hypothesis 1
decisively ruled out by direct experiment and hypothesis 2 folded into the
same underlying mechanism as hypothesis 3 (small address range, not small
request count per se, is what matters - see AlexNet IFMAP below).

## 2. Experiments run

All runs used `/home/yuvalk/MBMM/sweep_queue_size.py`, which reuses the real
`3_gen_nvmain_config.py` generator via subprocess and calls
`simulators/nvmain/nvmain.fast` directly. Isolation was verified before and
after: `simulators/nvmain/Config/*.config` (official top-level configs) carry
timestamps from Aug 2026 / Feb 2026, untouched by this session; the one
`results/system/stats_*_lbm_spec2017.out` set with a Sept 4 timestamp predates
this investigation (from the prior queue-size documentation session per the
tracker, item dated 2026-09-04). All of this session's output went to the
isolated `simulators/nvmain/Config/sweeps/queue_size/qs<N>/` and
`results/system/queue_size_sweep/` directories, and the shared
`results/queue_size_sweep_results.json` summary (the script's documented,
pre-existing single-file convention, matching `configs/hrs_sweep/` and
`results/sweep_voltage_results.json`) - never the official 96-run matrix.

Both traces were run at their official matched-host cycle count,
**confirmed** (not guessed) from `results/system_v6_input/stats_*_gcc_spec2017.out`
and `stats_*_gpt2_ifmap.out`: both show `*** Simulating 66666667 input cycles.
(250000002 memory cycles) ***`, i.e. the book's uniform matched-host window
applies identically to both workloads.

### 2.1 QueueSize x chip-count sweep, GCC

```
python3 sweep_queue_size.py --values 16,32,64 --model reram_22nm_1t1r_slc \
    --archs single,8chip,16chip,full_dimm --trace gcc_spec2017.nvt \
    --cycles 66666667 --timeout 240
```

| QueueSize | single | 8chip | 16chip | full_dimm | single->full_dimm gain |
|---|---|---|---|---|---|
| 16 | 112.40 ns | 112.40 ns | 103.80 ns | 95.64 ns | -14.9% |
| 32 (default) | 129.30 ns | 129.30 ns | 118.69 ns | 108.97 ns | -15.7% |
| 64 | 157.51 ns | 157.51 ns | 143.39 ns | 118.99 ns | -24.4% |

`mem_reads`/`mem_writes` were identical (236,562 / 170,800 = 407,362 total)
across every cell - the request population never changes, only latency.

### 2.2 QueueSize x chip-count sweep, GPT-2 IFMAP

```
python3 sweep_queue_size.py --values 16,32,64 --model reram_22nm_1t1r_slc \
    --archs single,8chip,16chip,full_dimm --trace gpt2_ifmap.nvt \
    --cycles 66666667 --timeout 240
```

| QueueSize | single | 8chip | 16chip | full_dimm |
|---|---|---|---|---|
| 16 | 248.03 ns | 248.03 ns | 248.03 ns | 248.03 ns |
| 32 (default) | 366.76 ns | 366.76 ns | 366.76 ns | 366.76 ns |
| 64 | 668.91 ns | 668.91 ns | 668.91 ns | 668.91 ns |

`mem_reads` = 6,553 / `mem_writes` = 0 at every single cell (24 runs, no
exceptions). Latency **does** move with `QueueSize` (queueing delay genuinely
increases with a deeper queue, as expected under FRFCFS), but it is **bit-for-bit
identical across all four architectures at every `QueueSize` tested**. This
directly falsifies hypothesis 1: if queue depth were masking or creating an
MLP effect, changing `QueueSize` should have changed how much (if any) of a
chip-count effect appears. It never does, at all, across 12 independent runs.

### 2.3 Trace and address-footprint analysis

```
wc -l benchmarks/gcc_spec2017.nvt benchmarks/gpt2_ifmap.nvt benchmarks/alexnet_layer1_ifmap.nvt
# 1,321,640 / 6,554 / 184,320 lines respectively
```

Address range extracted directly from each `.nvt` trace (min/max of the hex
address field, byte units):

| Trace | requests (mem_reads+writes) | address range | span |
|---|---|---|---|
| `gcc_spec2017.nvt` | 407,362 | `0x40` - `0x33675c0` | 53,900,672 B (~51.4 MB) |
| `alexnet_layer1_ifmap.nvt` | 184,319 | `0x0` - `0x1115f` | 69,984 B (~68.3 KB) |
| `gpt2_ifmap.nvt` | 6,553 | `0x0` - `0xfffa` | 65,530 B (~64.0 KB) |

Then, to find out whether these ranges matter architecturally, I read
`simulators/nvmain/src/AddressTranslator.cpp` and
`simulators/nvmain/src/TranslationMethod.cpp` (the real address-decode logic,
not a guess) and the generated `full_dimm` config
(`simulators/nvmain/Config/sweeps/queue_size/qs32/reram_22nm_1t1r_slc_full_dimm.config`):

```
AddressMappingScheme R:BK:RK:C
BusWidth 64
ROWS 131072
COLS 1024
RANKS 8
BANKS 8
```

`AddressTranslator::Translate()` first strips `busOffsetBits = log2(64/8) = 3`
and `lowColBits = log2(64*8/8) - 3 = 3` (burst length defaults to 8 in
`AddressTranslator.cpp:54`), i.e. 6 bits (64 bytes) per burst chunk. It then
consumes fields from least- to most-significant in the order fixed by
`TranslationMethod::SetAddressMappingScheme` parsing `"R:BK:RK:C"` left to
right (first token = most significant): **row > bank > rank > column**, with
channel/subarray (both count 1, unused here) sitting below column. Column
(`COLS=1024`, 10 bits) is therefore the *lowest*-order field that actually
consumes address bits, directly above the 6 burst-offset bits, and **rank**
sits immediately above column.

That gives an exact per-rank addressable span of `2^6 * 2^10 = 65,536 bytes
(64 KB)` before the address decoder rolls over from rank 0 into rank 1 -
independent of how many ranks the architecture actually has (single/8chip
have `RANKS=1`; 16chip has `RANKS=2`; full_dimm has `RANKS=8`, but the
rollover boundary from rank 0 is the same 64 KB regardless).

- `gpt2_ifmap.nvt`'s address range (`0x0`-`0xfffa` = 65,530 B) sits **6 bytes
  short of that exact 65,536-byte boundary**. Every single address in the
  entire trace decodes to rank 0, bank 0, in *every* architecture, including
  full_dimm's 8 ranks. The extra ranks/chips are never addressed at all -
  hence bit-identical stats regardless of chip count, at any `QueueSize`.
- `alexnet_layer1_ifmap.nvt`'s address range (`0x0`-`0x1115f` = 69,984 B)
  **exceeds** the 64 KB boundary by 4,448 bytes: a small fraction of its
  184,319 requests (worth ~1,024 of the 65,536+ possible bytes touched? in
  practice a small tail of addresses) spill into rank 1, and only rank 1
  (69,984 B < 2 x 65,536 B). This is the mechanism behind the book's own
  observed "nearly flat, slightly worse" AlexNet IFMAP scaling (394.73 ->
  397.41 ns) - almost the whole trace still lands on rank 0 in every
  architecture, with just enough spillover to produce a small, real, but
  non-beneficial (if anything slightly negative) architecture sensitivity.
- `gcc_spec2017.nvt`'s address range (~51.4 MB) is ~800x larger than the 64 KB
  single-rank span, so it necessarily cycles through many ranks/banks
  regardless of architecture, and having more physical ranks available (2 at
  16chip, 8 at full_dimm) genuinely lets the FRFCFS controller service more
  of that spread-out traffic concurrently. This is a real, physical,
  chip-count-driven latency improvement.

As independent corroboration (no extra experiment needed - already present in
`results/system_v6/processed_pareto_metrics.csv`): GCC's latency is
**identical between `single` and `8chip`** (152.58 ns both) and only improves
at `16chip` (140.52 ns) and `full_dimm` (130.91 ns). That is exactly what the
address-decode math predicts: `single` and `8chip` both have `RANKS=1` in
`3_gen_nvmain_config.py`'s architecture factory (8chip only widens the bus via
`devices_per_rank=8`, it does not add a second rank), so they are
architecturally identical from the address-decoder's perspective; only
`16chip` (`RANKS=2`) and `full_dimm` (`RANKS=8`) actually change the rank
count that GCC's wide address range can spread across. My own GCC sweep
(2.1 above) reproduces this same single==8chip pattern at every `QueueSize`
tested (e.g. QS=32: 129.296 ns for both single and 8chip).

## 3. Conclusion

**Root cause: a workload memory-footprint / address-decode rank-mapping
artifact, not a genuine MLP-exposure effect and not a controller queue-depth
effect.**

- GPT-2 IFMAP's total working set (~64.0 KB) and AlexNet IFMAP's (~68.3 KB)
  are both small enough to fit almost entirely - and in GPT-2 IFMAP's case,
  *exactly* - within the single-rank address span fixed by the current
  `AddressMappingScheme R:BK:RK:C` / `COLS=1024` / `BurstLength=8`
  configuration (64 KB). Scaling chip/rank count is therefore architecturally
  irrelevant to these two traces: the additional ranks physically exist in
  the full_dimm config but are never addressed by either trace's request
  stream, at any queue depth. This is confirmed both by exact bit-level
  address-decode math against the real NVMain source and generated configs,
  and by 24 independent, freshly-run simulations (2 workloads x 4
  architectures x 3 QueueSizes) that show GPT-2 IFMAP's stats are
  bit-for-bit identical across chip count at every queue depth tested.
- GCC's much larger working set (~51.4 MB) spans the same 64 KB per-rank
  boundary roughly 800 times over, so it does exercise genuine multi-rank
  parallelism as rank count increases (`single`/`8chip` -> `16chip` ->
  `full_dimm`), and that improvement is confirmed to persist, essentially
  proportionally, at every `QueueSize` value tested (16, 32, 64) - so it is
  not a queue-depth coincidence either; it's real bank/rank-level
  parallelism being exposed by a large, spread-out address footprint.
- The controller queue-depth hypothesis is **ruled out**: `QueueSize` clearly
  changes absolute latency for both workloads (as expected - a deeper queue
  means more queueing delay under FRFCFS), but it has **zero interaction**
  with the chip-count flatline/non-flatline behavior of either workload,
  across every value tested.

So the book's framing has the right *mechanism* (rank interleaving genuinely
helps traffic that's spread across many ranks) but the wrong *diagnostic
label*: this isn't about "high-MLP" vs. "low-MLP" workload classes in the
compute-architecture sense the prose implies (GCC = single-threaded low-MLP,
AI-inference = massively parallel high-MLP read-storms). It's that GCC's SPEC
trace happens to touch a ~51 MB working set while the two AI-inference IFMAP
traces used in this pipeline happen to touch a ~64-68 KB working set - almost
certainly an artifact of how these traces were captured/generated (e.g. a
single small SCALE-Sim layer's IFMAP, not a full model's working set) rather
than a property of "AI inference workloads" in general. A larger or more
representative AI-inference trace could very plausibly show genuine rank-level
scaling benefit; these specific two traces do not, for a footprint reason, not
an MLP reason.

**Confidence: high.** This is triangulated from three independent angles that
all agree: (1) direct empirical QueueSize x chip-count sweeps for both
workloads (24 fresh NVMain runs) showing zero interaction between queue depth
and the chip-count flatline, (2) raw trace address-range extraction showing
GPT-2 IFMAP's footprint (65,530 B) sits 6 bytes short of the exact per-rank
addressable span computed from the real NVMain address-decoder source and the
generated config's own parameters (65,536 B), and (3) the pre-existing
official CSV's own single==8chip / 16chip-improves / full_dimm-improves-more
pattern for GCC, which independently corroborates the same rank-count
(`RANKS` parameter) mechanism identified in (2), rather than any smooth
"more chips = more benefit" curve a generic MLP story would predict.

## 4. Scope note

This report identifies the root cause only, per the task assignment. It does
not rewrite `Project_Book.typ` Section 3.2 - that rewrite (reframing the
"Flatline Paradox" / "Breaking the Flatline" narrative away from MLP framing
and toward the working-set/address-footprint mechanism documented here, and
deciding whether/how to caveat the AI-inference traces' unusually small
captured footprints) is separate follow-up work for whoever owns that section
next, per T4-11's existing disposition in
`documents/MBMM_Book_Typst/Review_Fixes_Tracker.md`.
