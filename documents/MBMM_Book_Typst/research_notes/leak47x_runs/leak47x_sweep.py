import re, subprocess, pathlib
from concurrent.futures import ThreadPoolExecutor
S = pathlib.Path("/home/yuvalk/MBMM/documents/MBMM_Book_Typst/research_notes/leak47x_runs")
R = pathlib.Path("/home/yuvalk/MBMM"); NVSIM = R / "simulators/nvsim"
tmpl = (R / "configs/reram_22nm_1t1r_slc.cfg").read_text()   # one template for every run: only cell, mux, bank differ
cells = {"1T1R": S / "1t1r.cell", "1S1R": S / "sel.cell"}
banks = [(1,1),(1,2),(1,4),(1,8),(1,16),(1,32),(2,32),(4,32),(8,32),(16,32),(32,32)]
runs = [(c, 32, b) for c in cells for b in banks] + [(c, 256, b) for c in cells for b in [(1,1),(1,2),(1,4),(1,8),(2,8),(8,32)]] \
     + [(c, m, None) for c in cells for m in (32, 256)]
def run(spec):
    c, mux, b = spec
    txt = re.sub(r"(?m)^-MemoryCellInputFile:.*$", f"-MemoryCellInputFile: {cells[c]}", tmpl)
    txt = re.sub(r"(?m)^-ForceMuxSenseAmp:.*$", f"-ForceMuxSenseAmp: {mux}", txt)
    if b:
        txt = txt.rstrip("\n") + f"\n-ForceBank (Total AxB, Active CxD): {b[0]}x{b[1]}, 1x{b[1]}\n-ForceMat (Total AxB, Active CxD): 2x2, 2x2\n"
    tag = f"sw_{c}_m{mux}_{'free' if not b else f'{b[0]}x{b[1]}'}"
    p = S / f"{tag}.cfg"; p.write_text(txt)
    try: out = subprocess.run([str(NVSIM / "nvsim"), str(p)], cwd=NVSIM, capture_output=True, text=True, timeout=600).stdout
    except subprocess.TimeoutExpired: out = "TIMEOUT"
    (S / f"{tag}.txt").write_text(out)
    return spec, out
def g(pat, o):
    m = re.search(pat, o); return m.group(1).strip() if m else "-"
with ThreadPoolExecutor(8) as ex: res = list(ex.map(run, runs))
print(f"{'cell':5}{'mux':>4} {'forced bank':11} {'valid':5} {'mats':>5} {'subarray (rows x cols)':26} {'area mm2':>9} {'leak mW':>9} {'read ns':>9} {'write ns':>9}")
def to_ns(v):
    m = re.match(r"([\d.]+)([munp]?)s", v or "")
    return "-" if not m else f"{float(m.group(1)) * {'':1e9,'m':1e6,'u':1e3,'n':1,'p':1e-3}[m.group(2)]:.1f}"
def to_mw(v):
    m = re.match(r"([\d.]+)([munp]?)W", v or "")
    return "-" if not m else f"{float(m.group(1)) * {'':1e3,'m':1,'u':1e-3,'n':1e-6,'p':1e-9}[m.group(2)]:.3f}"
for (c, mux, b), o in res:
    ok = "Leakage Power" in o and "No valid" not in o
    bank = g(r"Bank Organization: (\d+) x (\d+)", o); m = re.search(r"Bank Organization: (\d+) x (\d+)", o)
    mats = int(m.group(1)) * int(m.group(2)) if m else 0
    wl = g(r"- (?:Write|RESET) Latency\s*=\s*([\d.]+[munp]?s)", o)
    print(f"{c:5}{mux:>4} {('free' if not b else f'{b[0]}x{b[1]}'):11} {('yes' if ok else 'NO'):5} {mats if ok else '-':>5} "
          f"{g(r'Subarray Size\s*: (\d+ Rows x \d+ Columns)', o) if ok else '-':26} "
          f"{g(r'Total Area = .*= ([\d.]+)mm\^2', o) if ok else '-':>9} {to_mw(g(r'- Leakage Power = ([\d.]+[munp]?W)', o)) if ok else '-':>9} "
          f"{to_ns(g(r'- Read Latency\s*=\s*([\d.]+[munp]?s)', o)) if ok else '-':>9} {to_ns(wl) if ok else '-':>9}")
