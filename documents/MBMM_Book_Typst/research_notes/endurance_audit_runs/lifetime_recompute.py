#!/usr/bin/env python3
"""Independent Table-5-style lifetime recomputation from raw NVMain stats (read-only).
lifetime_years = (capacity_bytes/64) * E / (writes / window_s) / (365*24*3600)"""
import re, glob, os, json, csv
SYS = '/home/yuvalk/MBMM/results/system'
SPY = 365 * 24 * 3600
WIN = 0.25 / 3
TRACKS = {'1T1R SLC': ('reram_22nm_1t1r_slc_full_dimm', 1e7, 8),
          '1T1R MLC': ('reram_22nm_1t1r_mlc_full_dimm', 1e6, 16),
          '1S1R SLC': ('reram_22nm_selector_slc_full_dimm', 1e7, 8),
          '1S1R MLC': ('reram_22nm_selector_mlc_full_dimm', 1e6, 16)}
TRACES = ['lbm_spec2017', 'gcc_spec2017', 'stream', 'alexnet_layer1_ofmap', 'alexnet_layer1_ifmap', 'gpt2_ifmap']
CAPS = [8, 16, 64, 128]
def stat(model, trace, key):
    f = f'{SYS}/stats_{model}_{trace}.out'
    tot = 0; n = 0
    for line in open(f, errors='ignore'):
        m = re.match(r'\S+\.FRFCFS\.' + key + r'\s+(\d+)', line)
        if m: tot += int(m.group(1)); n += 1
    return tot, n, f
def life(writes, E, cap_gb, window=WIN):
    if writes == 0: return float('inf')
    return (cap_gb * 2**30 / 64) * E / (writes / window) / SPY
rows = []
for tname, (model, E, native) in TRACKS.items():
    for tr in TRACES:
        w, nch, f = stat(model, tr, 'mem_writes')
        r = dict(track=tname, trace=tr, writes=w, channels=nch, rate_per_s=w / WIN, E=E, native_GB=native)
        for c in CAPS: r[f'life_{c}GB_y'] = life(w, E, c)
        rows.append(r)
# code's hardcoded numbers (visualize_slides.py slide_endurance)
code = {'lbm_spec2017': 3_257_597, 'gcc_spec2017': 170_800, 'stream': 100_000, 'alexnet_layer1_ofmap': 13_542}
check = []
for tr, w in code.items():
    raw = next(x['writes'] for x in rows if x['track'] == '1T1R SLC' and x['trace'] == tr)
    check.append(dict(trace=tr, code_writes=w, raw_writes=raw, match=(w == raw),
                      code_8=life(w, 1e7, 8), code_64=life(w, 1e7, 64), code_128=life(w, 1e7, 128)))
# LBM alternative bases, 1T1R SLC 1e7, 8 GB
ddr5_w, _, _ = stat('DDR5_4800_DRAM', 'lbm_spec2017', 'mem_writes')
alt = {
 'a_reram_completed_stats(3,257,597)': (3_257_597, WIN),
 'a2_reram_cycle8_table(3,269,479)': (3_269_479, WIN),
 'b_ddr5_admitted=trace_writes_in_250M': (ddr5_w, WIN),
 'c_trace_write_span_335266..154503725_at_3GHz': (6_965_793, (154_503_725 - 335_266) / 3e9),
 'd_trace_cycles_as_gem5_ns(tick//1000)_250ms': (6_965_793, 0.25),
 'e_reram_completed_at_gem5_ns_basis': (3_257_597, 0.25),
}
altrows = []
for k, (w, win) in alt.items():
    altrows.append(dict(basis=k, writes=w, window_s=win, rate=w / win,
                        **{f'SLC_1e7_{c}GB_y': life(w, 1e7, c, win) for c in CAPS},
                        **{f'MLC_1e6_{c}GB_y': life(w, 1e6, c, win) for c in CAPS}))
out = dict(rows=rows, code_check=check, lbm_alternatives=altrows, ddr5_lbm_writes=ddr5_w)
d = os.path.dirname(os.path.abspath(__file__))
json.dump(out, open(f'{d}/lifetime_recompute.json', 'w'), indent=1)
with open(f'{d}/lifetime_table.csv', 'w', newline='') as fh:
    wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys())); wr.writeheader(); wr.writerows(rows)
fmt = lambda v: 'inf' if v == float('inf') else (f'{v:.3g}' if v < 1000 else f'{v:,.0f}')
for r in rows:
    print(f"{r['track']:9s} {r['trace']:22s} W={r['writes']:>9,} ch={r['channels']} rate={r['rate_per_s']:>12,.0f}/s  " +
          '  '.join(f"{c}GB={fmt(r[f'life_{c}GB_y'])}" for c in CAPS))
print('--- code check'); [print(c) for c in check]
print('--- LBM alternatives')
for a in altrows:
    print(f"{a['basis']:48s} W={a['writes']:>9,} win={a['window_s']:.5f}s rate={a['rate']:>12,.0f}/s  SLC: " +
          ' '.join(f"{c}GB={a[f'SLC_1e7_{c}GB_y']:.3g}" for c in CAPS) + '  MLC: ' +
          ' '.join(f"{c}GB={a[f'MLC_1e6_{c}GB_y']:.3g}" for c in CAPS))
