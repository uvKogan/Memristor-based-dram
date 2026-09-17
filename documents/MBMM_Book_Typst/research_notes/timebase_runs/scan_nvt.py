import sys
f=sys.argv[1]; B=50_000_000
first=last=None; n=0; w=r=0; wb={}; rb={}; nonmono=0; prev=-1; misal=0
with open(f,'rb') as fh:
    for line in fh:
        p=line.split(b' ',3)
        c=int(p[0]); op=p[1]
        if first is None: first=c
        if c<prev: nonmono+=1
        prev=c; last=c; n+=1
        b=c//B
        if op==b'W': w+=1; wb[b]=wb.get(b,0)+1
        else: r+=1; rb[b]=rb.get(b,0)+1
        if int(p[2].rstrip(b","),16)%64: misal+=1
print(f, "first",first,"last",last,"span",last-first,"n",n,"W",w,"R",r,"nonmono",nonmono,"addr%64!=0",misal)
print("W<=250M", sum(v for k,v in wb.items() if k<5), "R<=250M", sum(v for k,v in rb.items() if k<5))
for k in sorted(set(wb)|set(rb)): print(f"  [{k*50}M,{(k+1)*50}M) W={wb.get(k,0)} R={rb.get(k,0)}")
