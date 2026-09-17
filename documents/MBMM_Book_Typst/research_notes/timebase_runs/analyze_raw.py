import sys, re, math, collections
raw=sys.argv[1]; SWITCH=int(sys.argv[2]); END=int(sys.argv[3])
msg=collections.Counter(); ex={}
g_all=0; g_ff=0; g_o3=0
ff_ticks=[]; o3_ticks=[]
parsed=[]  # 2e8514c logic
aln=collections.Counter()
for line in open(raw):
    if "system.mem_ctrls:" not in line: continue
    parts=line.split()
    tick=int(parts[0].rstrip(':'))
    body=" ".join(parts[2:])
    key=re.sub(r'0x[0-9a-f]+|\d+','N',body)[:60]
    msg[key]+=1; ex.setdefault(key,line.rstrip())
    if body.startswith("recvTimingReq") or body.startswith("recvAtomic"):
        g_all=math.gcd(g_all,tick)
        (ff_ticks if tick<SWITCH else o3_ticks).append(tick)
        a=int(re.search(r'0x([0-9a-f]+)',body).group(1),16)
        aln[("ff" if tick<SWITCH else "o3", body.split()[0], a%64==0)]+=1
    # --- 2e8514c parse_trace.py logic, verbatim semantics ---
    try:
        cycle=int(parts[0].replace(':',''))//1000
        op="R"; addr=None
        for p in parts:
            if p.startswith('0x'): addr=p
            elif 'Write' in p: op="W"
        if addr: parsed.append((cycle,op,addr,tick,body.split()[0]))
    except Exception: pass
print("== message types (MemCtrl lines) ==")
for k,v in msg.most_common(): print(f"{v:9d}  {ex[k][:130]}")
def stats(name,t):
    if not t: print(name,"none"); return
    d=[b-a for a,b in zip(t,t[1:]) if b>a]
    g=0
    for x in t: g=math.gcd(g,x)
    print(f"{name}: n={len(t)} first={t[0]} last={t[-1]} span_ps={t[-1]-t[0]} gcd={g} min_pos_delta={min(d) if d else None}")
stats("FF-region access ticks",ff_ticks); stats("O3-region access ticks",o3_ticks)
print("alignment (region,msg,addr%64==0):",dict(aln))
print("== 2e8514c parser output ==")
c=[p[0] for p in parsed]
print("records",len(parsed),"first cycle",c[0],"last cycle",c[-1],"span",c[-1]-c[0])
print("records by source msg:",collections.Counter(p[4] for p in parsed))
g=0
for x in c[:200000]: g=math.gcd(g,x)
dd=[b-a for a,b in zip(c,c[1:]) if b>a]
print("parsed cycle gcd(first200k)=",g,"min pos delta",min(dd))
print("expected span from stats: END/1000 =",END//1000,"; O3 part (END-SWITCH)/1000 =",(END-SWITCH)//1000,"; FF part SWITCH/1000 =",SWITCH//1000)
ff_c=[x for x,_,_,t,_ in parsed if t<SWITCH]; o3_c=[x for x,_,_,t,_ in parsed if t>=SWITCH]
print("parsed records FF",len(ff_c),"O3",len(o3_c), "W in FF",sum(1 for x in parsed if x[3]<SWITCH and x[1]=='W'),"W in O3",sum(1 for x in parsed if x[3]>=SWITCH and x[1]=='W'))
with open(sys.argv[4],'w') as f:
    for cy,op,ad,t,src in parsed: f.write(f"{cy} {op} {ad} {'0'*8} 0\n")
