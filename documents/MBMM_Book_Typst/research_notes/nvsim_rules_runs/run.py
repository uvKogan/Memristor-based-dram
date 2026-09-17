import re, subprocess, pathlib, json
from concurrent.futures import ThreadPoolExecutor
S = pathlib.Path(__file__).parent; NV = pathlib.Path("/home/yuvalk/MBMM/simulators/nvsim")
tmpl = (S/"template.cfg").read_text()
cells = {"1T1R": S/"1t1r.cell", "1S1R": S/"sel.cell"}
# (target, numRowMat, numColumnMat, mux): rows = 2^21/numRowMat/mux, cols = 128*mux/numColumnMat (CACTI 2x2 subarrays, all active)
table = {
 "1024x1024": [(256,1,8),(128,2,16),(64,4,32),(32,8,64),(16,16,128),(8,32,256)],
 "2048x1024": [(64,2,16),(32,4,32),(16,8,64),(8,16,128),(4,32,256)],
 "1024x2048": [(64,2,32),(32,4,64),(16,8,128),(8,16,256)],
 "2048x2048": [(32,2,32),(16,4,64),(8,8,128),(4,16,256)],
 "512x512":   [(256,4,16),(128,8,32),(64,16,64),(32,32,128),(16,64,256)],
}
runs = []
for tgt, combos in table.items():
    for (r,c,m) in combos:
        for cell in cells: runs.append(dict(tag=f"q4_{tgt}_{cell}_b{r}x{c}_m{m}", cell=cell, bank=(r,c), mux=m))
# Q1 confirmations: 1T1R row limit vs temperature (Ion/Ioff at T)
for T in (300,310,320,330,340,350,360):
    for (r,c) in ((1,32),(2,32),(4,32),(8,32)):
        runs.append(dict(tag=f"q1_1T1R_T{T}_b{r}x{c}_m32", cell="1T1R", bank=(r,c), mux=32, T=T))
# Q2 confirmations: 1S1R wordline driver limit vs MaxNmosSize
for nm in (100,200,400):
    for (r,c,m) in ((1,1,256),(1,2,256),(1,1,32),(1,2,32),(1,4,32)):
        runs.append(dict(tag=f"q2_1S1R_nmos{nm}_b{r}x{c}_m{m}", cell="1S1R", bank=(r,c), mux=m, nmos=nm))
def run(d):
    t = re.sub(r"(?m)^-MemoryCellInputFile:.*$", f"-MemoryCellInputFile: {cells[d['cell']]}", tmpl)
    t = re.sub(r"(?m)^-ForceMuxSenseAmp:.*$", f"-ForceMuxSenseAmp: {d['mux']}", t)
    if "T" in d: t = re.sub(r"(?m)^-Temperature \(K\):.*$", f"-Temperature (K): {d['T']}", t)
    r,c = d["bank"]
    t = t.rstrip("\n") + f"\n-ForceBank (Total AxB, Active CxD): {r}x{c}, 1x{c}\n-ForceMat (Total AxB, Active CxD): 2x2, 2x2\n"
    if "nmos" in d: t += f"-MaxNmosSize (F): {d['nmos']}\n"
    p = S/f"{d['tag']}.cfg"; p.write_text(t)
    try: o = subprocess.run([str(NV/"nvsim"), str(p)], cwd=NV, capture_output=True, text=True, timeout=900).stdout
    except subprocess.TimeoutExpired: o = "TIMEOUT"
    o = "\n".join(l for l in o.splitlines() if ">>>" not in l)
    (S/"out"/f"{d['tag']}.txt").write_text(o)
    return d["tag"]
with ThreadPoolExecutor(8) as ex: print(len(list(ex.map(run, runs))), "runs done")
