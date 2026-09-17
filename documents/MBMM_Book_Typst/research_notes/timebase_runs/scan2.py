import sys
f=sys.argv[1]; WIN=250_000_000
n=0; first=None; last=0; o3start=None
cls={}   # (region, op, suffix) -> count
win={}   # same but only cycle<=WIN
wb={}
for line in open(f,'rb'):
    p=line.split(b' ',3); c=int(p[0]); op=p[1]; a=p[2]
    suf = b',' if a.endswith(b',') else (b'..' if a.endswith(b'..') else b'')
    if suf and o3start is None: o3start=c
    if first is None: first=c
    last=c; n+=1
    reg = 'pre' if o3start is None else 'post'
    k=(reg,op.decode(),suf.decode()); cls[k]=cls.get(k,0)+1
    if c<=WIN: win[k]=win.get(k,0)+1
    if op==b'W': b=c//50_000_000; wb[b]=wb.get(b,0)+1
print(f,"records",n,"first",first,"last",last,"first suffixed (O3 start) cycle",o3start)
print(" all  (region,op,suffix):",cls)
print(" <=250M (region,op,suffix):",win)
print(" writes per 50M bin:",{f"{k*50}M":v for k,v in sorted(wb.items())})
