#!/usr/bin/env python3
"""Full-trace streaming scan (read-only): write/read counts per 25M-cycle bin, address alignment
for reads and writes, write sequentiality (addr == prev_write+64), per-64B-line write counts
over the first 250M cycles and over the whole trace (numpy unique)."""
import sys, time, json, collections, re
HEX = re.compile(rb"0x[0-9a-fA-F]+")
import numpy as np
path, out = sys.argv[1], sys.argv[2]
BIN = 25_000_000; CUT = 250_000_000
t0 = time.time()
binsW = collections.Counter(); binsR = collections.Counter()
alignR = collections.Counter(); alignW = collections.Counter()
seq = 0; prevW = None; nW = nR = 0; last = 0
buf = []; lines_all = []  # chunks of write line ids (addr>>6)
chunk = np.empty(4_000_000, dtype=np.uint64); k = 0
cut_idx = None
with open(path, 'rb') as f:
    for raw in f:
        p = raw.replace(b",", b" ").split()
        if len(p) < 3: continue
        m = HEX.match(p[2])
        if not m: continue
        c = int(p[0]); a = int(m.group(0), 16); last = c
        b = c // BIN
        if p[1] == b'W':
            if cut_idx is None and c >= CUT: cut_idx = nW
            nW += 1; binsW[b] += 1; alignW[a & 63] += 1
            if prevW is not None and a == prevW + 64: seq += 1
            prevW = a
            chunk[k] = a >> 6; k += 1
            if k == len(chunk):
                lines_all.append(chunk.copy()); k = 0
        else:
            nR += 1; binsR[b] += 1; alignR[a & 63] += 1
lines_all.append(chunk[:k].copy())
arr = np.concatenate(lines_all)
if cut_idx is None: cut_idx = nW
def skew(x):
    if len(x) == 0: return {}
    _, cnt = np.unique(x, return_counts=True)
    cnt = np.sort(cnt)[::-1]; n = len(cnt); tot = int(cnt.sum()); k1 = max(1, n // 100)
    return dict(writes=tot, distinct_lines=int(n), distinct_MB=n * 64 / 2**20, max=int(cnt[0]), mean=tot / n,
                p99=int(cnt[min(n - 1, n // 100)]), top1pct_share=float(cnt[:k1].sum() / tot),
                lines_written_ge2=int((cnt >= 2).sum()), hist={str(v): int((cnt == v).sum()) for v in range(1, 9)})
res = dict(trace=path, reads=nR, writes=nW, last_cycle=last, bin_cycles=BIN,
           writes_per_bin={int(k): v for k, v in sorted(binsW.items())},
           reads_per_bin={int(k): v for k, v in sorted(binsR.items())},
           read_align_mod64_top=alignR.most_common(4), write_align_mod64_top=alignW.most_common(4),
           sequential_write_frac=seq / max(1, nW - 1),
           skew_first250M=skew(arr[:cut_idx]), skew_whole_trace=skew(arr), runtime_s=time.time() - t0)
json.dump(res, open(out, 'w'), indent=1); print(json.dumps(res, indent=1))
