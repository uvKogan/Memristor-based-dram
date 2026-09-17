import re, subprocess, pathlib
from concurrent.futures import ThreadPoolExecutor
S = pathlib.Path(__file__).parent; NV = pathlib.Path("/home/yuvalk/MBMM/simulators/nvsim")
tmpl = (S/"template.cfg").read_text()
cells = {"1T1R": S/"1t1r.cell", "1S1R": S/"sel.cell"}
runs = []
# aspect-ratio probes: same subarray + mux as an invalid Q4 point, but capacity scaled so the bank is square (mat dims unchanged)
asp = [("1024x1024",8,32,8192,4,4),("1024x1024",16,2048,2,2),("1024x1024",8,512,1,1),
       ("2048x1024",32,8192,2,4),("2048x1024",16,4096,2,2),("1024x2048",32,4096,2,2),
       ("2048x2048",32,8192,2,2),("512x512",32,8192,8,8),("512x512",16,2048,4,4),("512x512",256,524288,64,64)]
asp = [("1024x1024",32,8192,4,4),("1024x1024",16,2048,2,2),("1024x1024",8,512,1,1),
       ("2048x1024",32,8192,2,4),("2048x1024",16,4096,2,2),("1024x2048",32,4096,2,2),
       ("2048x2048",32,8192,2,2),("512x512",32,8192,8,8),("512x512",16,2048,4,4),("512x512",256,524288,64,64)]
for sub,m,kb,r,c in asp:
    for cell in cells: runs.append(dict(tag=f"asp_{sub}_{cell}_m{m}_cap{kb}KB_b{r}x{c}", cell=cell, mux=m, bank=(r,c), kb=kb))
for nm in (163,164):
    runs.append(dict(tag=f"wl_1S1R_nmos{nm}_b1x1_m256", cell="1S1R", mux=256, bank=(1,1), nmos=nm))
for cell in cells:
    for tgt in ("Area","ReadLatency","ReadEDP","LeakagePower"):
        for m in (32,256,None):
            runs.append(dict(tag=f"opt_{cell}_{tgt}_m{m or 'free'}", cell=cell, mux=m, tgt=tgt))
for tgt in ("ReadLatency","LeakagePower"):
    runs.append(dict(tag=f"forced_1T1R_{tgt}_b32x32_m128", cell="1T1R", mux=128, bank=(32,32), tgt=tgt))
def run(d):
    t = re.sub(r"(?m)^-MemoryCellInputFile:.*$", f"-MemoryCellInputFile: {cells[d['cell']]}", tmpl)
    if d.get("mux"): t = re.sub(r"(?m)^-ForceMuxSenseAmp:.*$", f"-ForceMuxSenseAmp: {d['mux']}", t)
    else: t = re.sub(r"(?m)^-ForceMuxSenseAmp:.*$\n", "", t)
    if "kb" in d: t = re.sub(r"(?m)^-Capacity \(MB\):.*$", f"-Capacity (KB): {d['kb']}", t)
    if "tgt" in d: t = re.sub(r"(?m)^-OptimizationTarget:.*$", f"-OptimizationTarget: {d['tgt']}", t)
    t = t.rstrip("\n") + "\n"
    if "bank" in d:
        r,c = d["bank"]; t += f"-ForceBank (Total AxB, Active CxD): {r}x{c}, 1x{c}\n-ForceMat (Total AxB, Active CxD): 2x2, 2x2\n"
    if "nmos" in d: t += f"-MaxNmosSize (F): {d['nmos']}\n"
    p = S/f"{d['tag']}.cfg"; p.write_text(t)
    try: o = subprocess.run([str(NV/"nvsim"), str(p)], cwd=NV, capture_output=True, text=True, timeout=1800).stdout
    except subprocess.TimeoutExpired: o = "TIMEOUT"
    o = "\n".join(l for l in o.splitlines() if ">>>" not in l)
    (S/"out2"/f"{d['tag']}.txt").write_text(o); return d["tag"]
with ThreadPoolExecutor(8) as ex: print(len(list(ex.map(run, runs))), "runs done")
