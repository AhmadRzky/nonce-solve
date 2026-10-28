import numpy as np, json, sys, time
d=json.load(open(sys.argv[1])); C=np.array(d['clauses']); n=d['variables']; m,k=C.shape
V=np.abs(C)-1; S=np.where(C>0,1.0,-1.0)
def unsat(x): return int((~((x[V]==1)==(S>0)).any(1)).sum())
def bp(q,init=None,eps=0.3,iters=300,damp=0.5,seed=0,beta=1.0,rho=0.0):
    ext=np.zeros(n)
    rng=np.random.default_rng(seed)
    w=np.array([q**j for j in range(k+1)]); w[0]=0
    if init is None: u=rng.normal(0,eps,(m,k))
    else:
        s=np.where(init[V]==1,1.0,-1.0)*S   # +1 if literal true under init
        u=eps*s/ k
    best=(None,10**9)
    for it in range(iters):
        H=np.zeros(n); np.add.at(H,V,S*u)
        h=H[V]-S*u+ext[V]
        p=1/(1+np.exp(-2*np.clip(S*h,-30,30)))
        # DP of count of true among all k, then remove each via division-free: compute prefix/suffix
        pre=[np.ones((m,1))]
        for t in range(k):
            a=pre[-1]; nd=np.zeros((m,a.shape[1]+1)); nd[:,:-1]+=a*(1-p[:,t:t+1]); nd[:,1:]+=a*p[:,t:t+1]; pre.append(nd)
        suf=[np.ones((m,1))]
        for t in range(k-1,-1,-1):
            a=suf[-1]; nd=np.zeros((m,a.shape[1]+1)); nd[:,:-1]+=a*(1-p[:,t:t+1]); nd[:,1:]+=a*p[:,t:t+1]; suf.append(nd)
        suf=suf[::-1]
        new=np.empty((m,k))
        for t in range(k):
            A=pre[t]; B=suf[t+1]
            dist=np.zeros((m,k))
            for i in range(A.shape[1]):
                dist[:,i:i+B.shape[1]]+=A[:,i:i+1]*B
            wt=(dist*w[1:]).sum(1); wf=(dist*w[:-1]).sum(1)
            new[:,t]=0.5*beta*np.log(np.maximum(wt,1e-300)/np.maximum(wf,1e-300))
        diff=np.abs(new-u).max(); u=damp*u+(1-damp)*new
        if rho>0:
            Hn=np.zeros(n); np.add.at(Hn,V,S*u); ext=ext+rho*Hn
        if it%10==9 or diff<1e-5:
            H=np.zeros(n); np.add.at(H,V,S*u); H=H+ext; x=(H>0).astype(np.int8); us=unsat(x)
            if us<best[1]: best=(x,us); np.save('/tmp/bp_H.npy',H)
            print(it,round(diff,4),us,round(np.abs(H).mean(),3),flush=True)
            if us==0 or (diff<1e-5 and rho==0): break
    return best
if __name__=='__main__':
    q=float(sys.argv[2]); init=None
    if len(sys.argv)>3 and sys.argv[3]: init=np.array([int(c) for c in open(sys.argv[3]).read().strip()],dtype=np.int8)
    eps=float(sys.argv[4]) if len(sys.argv)>4 else 0.3
    x,us=bp(q,init,eps=eps,iters=int(sys.argv[5]) if len(sys.argv)>5 else 200,rho=float(sys.argv[6]) if len(sys.argv)>6 else 0,seed=int(sys.argv[7]) if len(sys.argv)>7 else 0)
    print('final',us); open('/tmp/bp_best.txt','w').write(''.join(map(str,x)))
    if us==0: open('/tmp/bp_sol.txt','w').write(''.join(map(str,x)))
