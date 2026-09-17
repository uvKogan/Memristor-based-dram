"""Endurance sensitivity on the verified 1 ns trace time base (2026-09-15).
lifetime_yr = lines * E * wl_eff * dcw / (min(demand, device_cap) * s_per_yr)
Demand rates come from trace scans (scan2_*, trace_full_scan) at 1 cycle = 1 ns.
Device write caps are the saturated completed-write rates from the 2026-09-05 re-run
(83.33 ms replay); they are approximate because that replay was 3x compressed."""
YR = 365 * 24 * 3600
LINES_PER_GB = 2**30 / 64
demand = {  # writes/s
    "LBM start-up window (0-250M ns, book population)": 6_965_793 / 0.25,
    "LBM steady FF after init (50M-517M ns)": (11_120_810 - 6_668_597) / (517_219_363 - 50_000_000) * 1e9,
    "LBM O3 region, deduplicated (517M-553M ns)": 341_157 / (552_978_157 - 517_219_363) * 1e9,
    "GCC start-up window (0-250M ns)": 170_800 / 0.25,
    "GCC O3 region, deduplicated (574M-611M ns)": 33_530 / (611_039_119 - 573_807_209) * 1e9,
}
caps = {"1T1R SLC": 3_257_597 / (0.25/3), "1S1R SLC": 2_288_852 / (0.25/3),
        "1T1R MLC": 1_825_508 / (0.25/3), "1S1R MLC": 1_090_968 / (0.25/3)}
print("Demand rates (M writes/s):")
for k, v in demand.items(): print(f"  {k}: {v/1e6:.2f}")
print("Device write caps (M writes/s):", {k: round(v/1e6, 2) for k, v in caps.items()})

def life(rate, gb, E, wl=0.97, dcw=1.0):
    return gb * LINES_PER_GB * E * wl * dcw / (rate * YR)

print("\n1T1R SLC, wear-leveling efficiency 0.97 (randomized Start-Gap). Years.")
hdr = "basis | E | 8GB | 64GB | 128GB | 64GB w/ DCW 4.5x"
print(hdr)
for name, d in demand.items():
    r = min(d, caps["1T1R SLC"])
    for E in (1e4, 1e6, 1e7):
        print(f"{name} | {E:.0e} | {life(r,8,E):.3g} | {life(r,64,E):.3g} | {life(r,128,E):.3g} | {life(r,64,E,dcw=4.5):.3g}")

print("\nAll tracks, LBM steady state, 64 GB SLC / 128 GB MLC, WL 0.97, no DCW. MLC E = SLC E x {1, 0.1}. Years.")
d = demand["LBM steady FF after init (50M-517M ns)"]
for E in (1e4, 1e6, 1e7):
    row = []
    for t, c in caps.items():
        r = min(d, c)
        if "MLC" in t:
            row.append(f"{t}: {life(r,128,E):.3g} (x1) / {life(r,128,E*0.1):.3g} (x0.1)")
        else:
            row.append(f"{t}: {life(r,64,E):.3g}")
    print(f"E={E:.0e} | " + " | ".join(row))

print("\nShahar's template: endurance required for 10 yr, 64 GiB, ideal leveling, whole line per write.")
for name, dd in demand.items():
    print(f"  {name}: {dd*10*YR/(64*LINES_PER_GB):.3g} cycles")
