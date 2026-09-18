#!/usr/bin/env bash
# tools/nvmain_regress.sh: build nvmain.fast and compare pre-existing stats to golden files.
# Usage: tools/nvmain_regress.sh [--record]
set -euo pipefail
ROOT=/home/yuvalk/MBMM
NV=$ROOT/simulators/nvmain
GOLD=$ROOT/tools/golden
TRACE=$ROOT/benchmarks/gpt2_ifmap.nvt        # small, deterministic, 6553 reads
CYCLES=20000
CONFIGS=("reram_22nm_1t1r_slc_full_dimm" "DDR5_4800_DRAM" "pcm_microsoft_2009")
mkdir -p "$GOLD/configs"
( cd "$NV" && scons -j8 >/dev/null )
if [[ "${1:-}" == "--record" ]]; then
  for c in "${CONFIGS[@]}"; do
    cp "$NV/Config/$c.config" "$GOLD/configs/$c.config"
  done
fi
rc=0
for c in "${CONFIGS[@]}"; do
  out=$(mktemp)
  "$NV/nvmain.fast" "$GOLD/configs/$c.config" "$TRACE" "$CYCLES" > "$out" 2>&1 || true
  # keep only statistic lines (i0. prefix), drop the new stats we are adding so old ones are compared alone
  grep -E '^i0\.' "$out" | grep -vE 'EndToEnd|unstampedRequests|wear[A-Z]' | sort > "$out.stats"
  if [[ "${1:-}" == "--record" ]]; then
    cp "$out.stats" "$GOLD/$c.golden"; echo "recorded $c ($(wc -l < "$GOLD/$c.golden") lines)"
  else
    if diff -q "$GOLD/$c.golden" "$out.stats" >/dev/null; then echo "PASS $c"; else echo "FAIL $c"; diff "$GOLD/$c.golden" "$out.stats" | head -20; rc=1; fi
  fi
  rm -f "$out" "$out.stats"
done
exit $rc
