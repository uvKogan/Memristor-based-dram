import re, pathlib, sys
S = pathlib.Path(__file__).parent; D = S/(sys.argv[1] if len(sys.argv)>1 else "out")
U = {'':1,'m':1e-3,'u':1e-6,'n':1e-9,'p':1e-12,'f':1e-15}
def val(pat, o, unit):
    m = re.search(pat + r"\s*=\s*([\d.eE+-]+)([munpf]?)" + unit, o)
    return float(m.group(1))*U[m.group(2)] if m else None
def dim(s):
    m = re.match(r"([\d.]+)(mm|um)", s); return float(m.group(1))*(1e-3 if m.group(2)=="mm" else 1e-6)
def g(p,o):
    m = re.search(p,o); return m.group(1) if m else "-"
for f in sorted(D.glob("*.txt")):
    o = f.read_text()
    if "Total Area" not in o:
        print(f"{f.stem:44} INVALID ({'No valid solutions' if 'No valid' in o else o[-100:].strip()!r})"); continue
    ma = re.search(r"Total Area = .*= ([\d.]+)(mm|um)\^2", o); area = float(ma.group(1))*(1 if ma.group(2)=="mm" else 1e-6)
    leak = val(r"- Leakage Power", o, "W"); rl = val(r"-\s+Read Latency", o, "s")
    wl = val(r"- Write Latency", o, "s") or max(val(r"- RESET Latency", o, "s") or 0, val(r"- SET Latency", o, "s") or 0)
    rE = val(r"-\s+Read Dynamic Energy", o, "J")
    wE = val(r"- Write Dynamic Energy", o, "J") or max(val(r"- RESET Dynamic Energy", o, "J") or 0, val(r"- SET Dynamic Energy", o, "J") or 0)
    sub = g(r"Subarray Size\s*: (\d+ Rows x \d+ Columns)", o).replace(" Rows x ","x").replace(" Columns","")
    bank = g(r"Bank Organization: (\d+ x \d+)", o).replace(" ","")
    mux = g(r"Senseamp Mux\s*: (\d+)", o)
    m = re.search(r"Mat Area\s*= ([\d.]+(?:mm|um)) x ([\d.]+(?:mm|um))", o)
    mh, mw = dim(m.group(1)), dim(m.group(2))
    print(f"{f.stem:44} ok bank={bank:7} mux={mux:>3} sub={sub:11} area={float(area):7.3f}mm2 leak={leak*1e3:7.2f}mW "
          f"read={rl*1e9:7.2f}ns write={wl*1e9:6.2f}ns readE={rE*1e12:7.1f}pJ writeE={wE*1e12:7.1f}pJ matHxW={mh*1e6:.1f}x{mw*1e6:.1f}um")
