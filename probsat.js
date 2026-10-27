// probSAT (poly break) for k-SAT. usage: node probsat.js inst.json [seconds] [seed] [cb] [init.txt]
const fs=require('fs');
const d=JSON.parse(fs.readFileSync(process.argv[2]));
const T=(+process.argv[3]||60)*1000, seed0=+process.argv[4]||1, cb=+process.argv[5]||3.7;
const n=d.variables, cl=d.clauses, m=cl.length, k=cl[0].length;
let s=seed0>>>0||1; const rnd=()=>{s^=s<<13;s>>>=0;s^=s>>>17;s^=s<<5;s>>>=0;return s/4294967296;};
const L=new Int32Array(m*k); for(let a=0;a<m;a++)for(let j=0;j<k;j++)L[a*k+j]=cl[a][j];
// occurrence lists per literal: index lit -> 2*v + (pos?0:1)
const cnt=new Int32Array(2*(n+1)); for(let i=0;i<m*k;i++){const l=L[i];cnt[2*Math.abs(l)+(l>0?0:1)]++;}
const st=new Int32Array(2*(n+1)+1); for(let i=0;i<2*(n+1);i++)st[i+1]=st[i]+cnt[i];
const occ=new Int32Array(m*k); const fill=st.slice(0,-1);
for(let a=0;a<m;a++)for(let j=0;j<k;j++){const l=L[a*k+j];occ[fill[2*Math.abs(l)+(l>0?0:1)]++]=a;}
const x=new Uint8Array(n+1);
if(process.argv[6]&&fs.existsSync(process.argv[6])){const t=fs.readFileSync(process.argv[6],'utf8').trim();for(let v=1;v<=n;v++)x[v]=t[v-1]=='1'?1:0;}
else for(let v=1;v<=n;v++)x[v]=rnd()<0.5?1:0;
const nt=new Int32Array(m), crit=new Int32Array(m); // crit = xor of true vars (when nt==1 gives the var)
const U=new Int32Array(m), pos=new Int32Array(m).fill(-1); let nu=0;
const add=a=>{pos[a]=nu;U[nu++]=a;}, rem=a=>{const p=pos[a],b=U[--nu];U[p]=b;pos[b]=p;pos[a]=-1;};
const tl=l=> (l>0)===(x[Math.abs(l)]===1);
for(let a=0;a<m;a++){let c=0,cr=0;for(let j=0;j<k;j++){const l=L[a*k+j];if(tl(l)){c++;cr^=Math.abs(l);}}nt[a]=c;crit[a]=cr;if(c===0)add(a);}
const pw=new Float64Array(64); for(let i=0;i<64;i++)pw[i]=process.env.EXP?Math.pow(cb,-i):Math.pow(1+i,-cb);
const brk=v=>{const lt=2*v+(x[v]?0:1);let b=0;for(let i=st[lt];i<st[lt+1];i++)if(nt[occ[i]]===1)b++;return b;};
const flip=v=>{const lt=2*v+(x[v]?0:1), lf=2*v+(x[v]?1:0); x[v]^=1;
  for(let i=st[lt];i<st[lt+1];i++){const a=occ[i];nt[a]--;crit[a]^=v;if(nt[a]===0)add(a);}
  for(let i=st[lf];i<st[lf+1];i++){const a=occ[i];nt[a]++;crit[a]^=v;if(nt[a]===1)rem(a);}};
let bx=null; const t0=Date.now(); let best=nu, f=0; const pr=new Float64Array(k);
while(nu>0){
  if((f&65535)===0){ if(Date.now()-t0>T)break; }
  f++;
  const a=U[Math.floor(rnd()*nu)]; let sum=0;
  for(let j=0;j<k;j++){const v=Math.abs(L[a*k+j]);const b=brk(v);pr[j]=pw[b<63?b:63];sum+=pr[j];}
  let r=rnd()*sum,j=0; for(;j<k-1;j++){r-=pr[j];if(r<=0)break;}
  flip(Math.abs(L[a*k+j]));
  if(nu<best){best=nu;if(nu<120){bx=x.slice();}}
}
let out='';for(let v=1;v<=n;v++)out+=x[v]?'1':'0';
// verify
let bad=0;for(let a=0;a<m;a++){let ok=false;for(let j=0;j<k;j++)if(tl(L[a*k+j])){ok=true;break;}if(!ok)bad++;}
console.error(JSON.stringify({ok:bad===0,unsat:bad,best,flips:f,sec:(Date.now()-t0)/1000}));
if(bad===0)console.log(out); else {fs.writeFileSync('/tmp/probsat_last'+seed0+'.txt',out); if(bx){let o='';for(let v=1;v<=n;v++)o+=bx[v]?'1':'0';fs.writeFileSync('/tmp/probsat_best'+seed0+'.txt',o);}}
