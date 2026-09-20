#!/usr/bin/env bash
# tools/nvmain_regress.sh: build nvmain.fast and compare pre-existing stats to golden files.
# Usage: tools/nvmain_regress.sh [--record]
set -euo pipefail
ROOT=/home/yuvalk/MBMM
NV=$ROOT/simulators/nvmain
GOLD=$ROOT/tools/golden
# Frozen pre-revision GPT-2 IFMAP trace (6554 reads), tracked compressed so the harness works on a fresh clone.
# T3.3 regenerated benchmarks/gpt2_ifmap.nvt with 10x the records; this harness tests NVMain behavior, not the
# trace, so it keeps replaying the input the golden files were recorded with.
TRACE_GZ=$GOLD/gpt2_ifmap_pre_revision.nvt.gz
TRACE_SHA256=fa31910b2dcf4e1ad40f32f5bc79eb3f3482e9d1b060a9add4ef5b07581419f9
[[ -f "$TRACE_GZ" ]] || { echo "nvmain_regress: missing $TRACE_GZ (tracked file; restore it with: git checkout -- tools/golden)"; exit 2; }
TRACE=$(mktemp --suffix=.nvt)
trap 'rm -f "$TRACE"' EXIT
gzip -dc "$TRACE_GZ" > "$TRACE"
echo "$TRACE_SHA256  $TRACE" | sha256sum -c --status || { echo "nvmain_regress: frozen trace checksum mismatch"; exit 2; }
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
