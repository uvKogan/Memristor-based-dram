# gem5 ↔ NVMain integration patches (exported 2026-08-23)

`simulators/gem5/` is gitignored (14G working tree), so its local NVMain
integration existed only on the working machine until this export. This
directory is the tracked, restorable copy of **every** local change gem5
carries relative to pristine upstream.

**Base version:** gem5 `v25.1.0.0`, commit `7a2b0e413d` ("misc: Release
v25.1.0.0 (#2803)"), cloned from https://github.com/gem5/gem5.

## Contents

| File | Restores to | What it is |
|---|---|---|
| `gem5-v25.1.0.0_nvmain_integration.diff` | `configs/common/Options.py`, `src/mem/SConscript` | Adds the `--nvmain-config` CLI option; registers the `NVMainMemory` SimObject and links the NVMain engine into the gem5 build |
| `NVMainMemory.cc` | `src/mem/NVMainMemory.cc` | The gem5-side memory-controller shim driving NVMain |
| `NVMainMemory.hh` | `src/mem/NVMainMemory.hh` | Its header |
| `NVMainMemory.py` | `src/mem/NVMainMemory.py` | SimObject Python declaration |

Excluded deliberately: `configs/common/Options.py.orig` / `.rej` (leftovers
from an earlier patch attempt, no content of value) and `build/` / `m5out/`
(regenerable artifacts / old run output).

## Restore procedure

```bash
git clone --branch v25.1 https://github.com/gem5/gem5.git simulators/gem5
cd simulators/gem5
git apply ../gem5-nvmain-patches/gem5-v25.1.0.0_nvmain_integration.diff
cp ../gem5-nvmain-patches/NVMainMemory.{cc,hh,py} src/mem/
scons build/X86/gem5.opt -j$(nproc)
```

⚠️ **Machine-specific paths:** the `SConscript` hunk hardcodes
`/home/yuvalk/MBMM/simulators/nvmain` (header include path + NVMain's own
SConscript) — edit those two lines if restoring under a different root.

## Status note

The MBMM pipeline has been trace-based since the gem5 decoupling — NVMain
consumes `.nvt` traces from `benchmarks/` directly, and gem5 is only needed to
*generate new traces*. This export exists so that capability is never lost,
not because gem5 is part of the active pipeline. Verified on export:
`git apply --check --reverse` of the diff passes against the live tree, i.e.
the diff exactly reproduces the working gem5's delta from upstream.
