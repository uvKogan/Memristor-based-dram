#!/usr/bin/env python3
"""Streaming trace scan: counts R/W in first CUTOFF trace cycles, write address skew,
alignment, per-4KB-page and per-64B-line histograms. Read-only on the trace."""
import sys, time, json, collections
path, cutoff, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
t0 = time.time()
nR = nW = 0; first = last = None; lastW = None; firstW = None
w64 = collections.Counter(); wpage = collections.Counter()
align = collections.Counter()  # addr mod 64 for writes
sizes_seen = collections.Counter()
nonzero_data = 0; lines = 0; stopped = False
with open(path, 'rb') as f:
    for raw in f:
        p = raw.split()
        if len(p) < 3: continue
        c = int(p[0])
        if c >= cutoff:
            stopped = True; break
        lines += 1
        if first is None: first = c
        last = c
        a = int(p[2], 16)
        if p[1] == b'W':
            nW += 1
            if firstW is None: firstW = c
            lastW = c
            w64[a >> 6] += 1; wpage[a >> 12] += 1
            align[a & 63] += 1
            if len(p) > 3: sizes_seen[len(p[3])] += 1
            if len(p) > 3 and p[3].strip(b'0'): nonzero_data += 1
        else:
            nR += 1
def skew(cnt):
    if not cnt: return {}
    v = sorted(cnt.values(), reverse=True); tot = sum(v); n = len(v)
    k1 = max(1, n // 100)
    return dict(distinct=n, total=tot, max=v[0], mean=tot / n, median=v[n // 2],
                top1pct_units=k1, top1pct_share=sum(v[:k1]) / tot,
                top10_share=sum(v[:10]) / tot, max_over_mean=v[0] / (tot / n))
res = dict(trace=path, cutoff=cutoff, stopped_at_cutoff=stopped, records=lines, reads=nR, writes=nW,
           first_cycle=first, last_cycle=last, first_write_cycle=firstW, last_write_cycle=lastW,
           write_addr_mod64_top=align.most_common(8), data_field_lengths=dict(sizes_seen),
           writes_with_nonzero_data=nonzero_data,
           skew_64B_lines=skew(w64), skew_4KB_pages=skew(wpage),
           write_span_bytes_64B=(len(w64) * 64), runtime_s=time.time() - t0)
json.dump(res, open(out, 'w'), indent=1); print(json.dumps(res, indent=1))
