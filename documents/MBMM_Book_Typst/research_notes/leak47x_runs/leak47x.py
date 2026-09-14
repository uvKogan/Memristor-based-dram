import re, shutil, subprocess, time, pathlib
from concurrent.futures import ThreadPoolExecutor
S = pathlib.Path("/home/yuvalk/MBMM/documents/MBMM_Book_Typst/research_notes/leak47x_runs"); S.mkdir(exist_ok=True)
R = pathlib.Path("/home/yuvalk/MBMM"); NVSIM = R / "simulators/nvsim"
cell = {k: S / f"{k}.cell" for k in ("1t1r", "sel")}
shutil.copy(R / "configs/reram_22nm_1t1r_slc.cell", cell["1t1r"]); shutil.copy(R / "configs/reram_22nm_selector_slc.cell", cell["sel"])
tmpl = {"1t1r": (R / "configs/reram_22nm_1t1r_slc.cfg").read_text(), "sel": (R / "configs/reram_22nm_selector_slc.cfg").read_text()}
RUNS = [  # name, template, cell, mux, (ForceBank, ForceMat) or None, purpose
 ("R1", "1t1r", "1t1r", 32,  None, "1T1R baseline (expect 794.656 mW)"),
 ("R2", "sel",  "sel",  256, None, "selector baseline (expect 16.907 mW)"),
 ("R3", "1t1r", "1t1r", 256, ("1x2, 1x2", "2x2, 2x2"), "1T1R forced to selector org"),
 ("R4", "sel",  "sel",  32,  ("8x32, 1x32", "2x2, 2x2"), "selector forced to 1T1R org"),
 ("R5", "1t1r", "1t1r", 256, None, "1T1R free search, mux 256"),
 ("R6", "1t1r", "sel",  32,  None, "selector cell, 1T1R cfg, mux 32"),
]
def build(name, t, c, mux, force):
    txt = tmpl[t]
    txt, n1 = re.subn(r"(?m)^-MemoryCellInputFile:.*$", f"-MemoryCellInputFile: {cell[c]}", txt)
    txt, n2 = re.subn(r"(?m)^-ForceMuxSenseAmp:.*$", f"-ForceMuxSenseAmp: {mux}", txt)
    assert n1 == 1 and n2 == 1, (name, n1, n2)
    assert not re.search(r"(?m)^-Force(Bank|Mat)", txt)
    if force:
        txt = txt.rstrip("\n") + f"\n-ForceBank (Total AxB, Active CxD): {force[0]}\n-ForceMat (Total AxB, Active CxD): {force[1]}\n"
    p = S / f"{name}.cfg"; p.write_text(txt); return p
def run(spec):
    name = spec[0]; cfg = build(*spec[:5]); t0 = time.time()
    try:
        out = subprocess.run([str(NVSIM / "nvsim"), str(cfg)], cwd=NVSIM, capture_output=True, text=True, timeout=2400).stdout
    except subprocess.TimeoutExpired:
        out = "TIMEOUT"
    (S / f"{name}.txt").write_text(out)
    return name, out, time.time() - t0
def g(pat, out):
    m = re.search(pat, out); return m.group(1).strip() if m else "-"
with ThreadPoolExecutor(6) as ex:
    res = {n: (o, dt) for n, o, dt in ex.map(run, RUNS)}
print(f"{'run':4} {'purpose':34} {'valid':5} {'bank':8} {'mat':6} {'subarray':24} {'mux':4} {'area':11} {'leakage':11} {'per mat':10} {'readLat':10} {'writeLat':10} {'sec':5}")
for name, t, c, mux, force, purpose in RUNS:
    o, dt = res[name]
    valid = "NO" if ("No valid" in o or o == "TIMEOUT" or "Leakage Power" not in o) else "yes"
    print(f"{name:4} {purpose:34} {valid:5} {g(r'Bank Organization: (\d+ x \d+)', o):8} {g(r'Mat Organization: (\d+ x \d+)', o):6} "
          f"{g(r'Subarray Size\s*: (.*)', o):24} {g(r'Senseamp Mux\s*: (\d+)', o):4} {g(r'Total Area = .*= ([\d.]+[mu]m\^2)', o):11} "
          f"{g(r'- Leakage Power = ([\d.]+[munp]?W)', o):11} {g(r'Mat Leakage Power\s*= ([\d.]+[munp]?W)', o):10} "
          f"{g(r'Read Latency\s*=\s*([\d.]+[mnpu]?s)', o):10} {g(r'Write Latency\s*=\s*([\d.]+[mnpu]?s)', o):10} {dt:5.0f}")
    if valid == "NO": print("     tail:", o.strip().splitlines()[-3:] if o.strip() else "(empty)")
