#!/usr/bin/env python3
"""Extra LBM/GCC write-rate bases from full-trace scan outputs (read-only inputs)."""
import json
SPY = 365*24*3600; LINES8 = 8*2**30/64; E = 1e7
def life(rate, cap=8, e=E): return (cap/8)*LINES8*e/rate/SPY
lbm = json.load(open('full_lbm_spec2017.json')); gcc = json.load(open('full_gcc_spec2017.json'))
wb = {int(k): v for k, v in lbm['writes_per_bin'].items()}; BIN = 25e6
steady = sum(wb.get(b, 0) for b in range(11, 21)) / (10*BIN)          # writes per trace cycle, bins 11-20
post_init = (lbm['writes'] - wb[0] - wb[1]) / (lbm['last_cycle'] - 50e6)
whole = lbm['writes'] / lbm['last_cycle']
reram_init = 3_257_597 / 22_586_868                                   # first 6,550,154 records
bases = {
 'ReRAM completed, book (3,257,597 / 83.33 ms)': 3_257_597 / (0.25/3),
 'Same 3,257,597 writes at their own trace time (22.59M cycles, 3 GHz)': reram_init*3e9,
 'DDR5 admitted = trace writes in 250M cycles (6,965,793 / 83.33 ms)': 6_965_793/(0.25/3),
 'Trace write-active span in window (335,266..154,503,725, 3 GHz)': 6_965_793/((154_503_725-335_266)/3e9),
 'LBM steady-state bins 275-525M cycles (3 GHz)': steady*3e9,
 'LBM post-init long-run 50M-553M cycles (3 GHz)': post_init*3e9,
 'LBM whole trace 0-553M cycles (3 GHz)': whole*3e9,
 'Book window, trace cycle = 1 gem5 ns (6,965,793 / 250 ms)': 6_965_793/0.25,
 'LBM steady-state, trace cycle = 1 gem5 ns': steady*1e9,
 'LBM post-init long-run, trace cycle = 1 gem5 ns': post_init*1e9,
}
out = []
for k, r in bases.items():
    row = dict(basis=k, writes_per_s=r, **{f'SLC_{c}GB_y': life(r, c) for c in (8, 16, 64, 128)},
               MLC_16GB_y=life(r, 16, 1e6))
    out.append(row)
    print(f"{k:72s} {r/1e6:8.2f} M/s  SLC 8GB={row['SLC_8GB_y']:.3g}y 16GB={row['SLC_16GB_y']:.3g}y 64GB={row['SLC_64GB_y']:.3g}y 128GB={row['SLC_128GB_y']:.3g}y  MLC16GB(1e6)={row['MLC_16GB_y']:.3g}y")
# No-wear-leveling per-line views (3 GHz basis; x3 for gem5-ns basis)
nowl = {}
for name, d in (('lbm', lbm), ('gcc', gcc)):
    T = d['last_cycle']/3e9; s = d['skew_whole_trace']
    hot = s['max']/T; mean = s['mean']/T
    nowl[name] = dict(trace_seconds_3GHz=T, footprint_MB=s['distinct_MB'], hottest_line_writes=s['max'],
                      hottest_line_rate=hot, hottest_line_life_days=E/hot/86400,
                      mean_touched_line_rate=mean, mean_touched_line_life_days=E/mean/86400,
                      leveled_over_footprint_life_days=E/mean/86400,
                      leveled_over_8GB_life_years=E*LINES8/(d['writes']/T)/SPY,
                      footprint_fraction_of_8GB=s['distinct_lines']/LINES8)
    print(name, json.dumps(nowl[name]))
json.dump(dict(bases=out, no_wear_leveling=nowl), open('alt_bases.json', 'w'), indent=1)
