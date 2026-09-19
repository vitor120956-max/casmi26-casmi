TRAIN_SCRIPT_SRC = '"""Spectrum->fingerprint training with BCE + hard-negative contrastive ranking loss.\n   Ranking score is f_cand . z (exact Bayes log-likelihood up to a candidate-independent constant)."""\nimport numpy as np, torch, torch.nn as nn, torch.nn.functional as F, time, pickle, os, math, argparse\nimport fpmodel\n\ndef dev_of():\n    if torch.cuda.is_available(): return \'cuda\'\n    if torch.backends.mps.is_available(): return \'mps\'\n    return \'cpu\'\n\nclass Data:\n    def __init__(self, spec=\'ds/spec.npz\', fpdir=\'up_train\', pooldir=\'.\', device=\'cpu\', pool_on_gpu=True):\n        z=np.load(spec)\n        self.off=z[\'off\']; self.mz=z[\'mz\']; self.it=z[\'it\']; self.prec=z[\'prec\']\n        self.ad=z[\'ad\'].astype(np.int64); self.ins=z[\'ins\'].astype(np.int64)\n        self.ce=z[\'ce\']; self.mode=z[\'mode\']; self.six=z[\'six\']; self.is_val=z[\'is_val\']\n        m=pickle.load(open(f\'{fpdir}/fp_meta.pkl\',\'rb\')); self.nbits=m[\'nbits\']; self.skeys=m[\'keys\']\n        pm=pickle.load(open(f\'{pooldir}/pool_meta.pkl\',\'rb\'))\n        self.pmass=np.load(f\'{pooldir}/pool_mass.npy\')\n        PFP=np.unpackbits(np.load(f\'{pooldir}/pool_fp.npy\'),axis=1)[:, :self.nbits]\n        self.pkeys=pm[\'keys\']\n        k2p={k:i for i,k in enumerate(self.pkeys)}\n        self.s2p=np.array([k2p.get(k,-1) for k in self.skeys], dtype=np.int64)\n        self.device=device\n        if pool_on_gpu and device==\'cuda\':\n            self.PFP=torch.from_numpy(np.ascontiguousarray(PFP)).to(device)\n        else:\n            self.PFP=torch.from_numpy(np.ascontiguousarray(PFP))\n        # group spectra by structure so training inputs can be MERGED the way test molecules are:\n        # the hidden test gives 1-16 spectra per molecule (median 3), but training on single\n        # spectra creates a train/test mismatch.\n        order=np.argsort(self.six, kind=\'mergesort\')\n        s_sorted=self.six[order]\n        bounds=np.searchsorted(s_sorted, np.arange(s_sorted.max()+2))\n        self._grp_order=order; self._grp_bounds=bounds\n        self.tr=np.where(~self.is_val)[0]; self.va=np.where(self.is_val)[0]\n        keep = self.s2p[self.six[self.tr]]>=0\n        self.tr = self.tr[keep]\n        print(f\'nbits={self.nbits} pool={len(self.pmass)} train={len(self.tr)} val={len(self.va)}\',flush=True)\n\n    def sample_negs(self, pos_pidx, K, ppm=10.0, rng=None):\n        m=self.pmass[pos_pidx]; tol=m*ppm/1e6\n        lo=np.searchsorted(self.pmass, m-tol,\'left\'); hi=np.searchsorted(self.pmass, m+tol,\'right\')\n        out=np.empty((len(pos_pidx),K), dtype=np.int64)\n        for r,(a,b,p) in enumerate(zip(lo,hi,pos_pidx)):\n            n=b-a\n            if n<=1: out[r]=rng.integers(0,len(self.pmass),K)   # no isomers -> random decoys\n            else:\n                c=rng.integers(a,b,K)\n                bad=(c==p)\n                if bad.any(): c[bad]=np.where(c[bad]+1<b, c[bad]+1, a)\n                out[r]=c\n        return out\n\n    def peers(self, i, rng, kmax=4):\n        """Other spectra of the same structure (for merge augmentation)."""\n        s=self.six[i]\n        a,b=self._grp_bounds[s], self._grp_bounds[s+1]\n        if b-a<=1: return [i]\n        cand=self._grp_order[a:b]\n        k=int(rng.integers(2, min(kmax, b-a)+1))\n        pick=rng.choice(cand, size=min(k,len(cand)), replace=False)\n        if i not in pick: pick=np.concatenate([[i], pick[:-1]])\n        return list(pick)\n\n    def _merged(self, idxs, maxlen):\n        mzs=[]; its=[]\n        for j in idxs:\n            a,b=self.off[j], min(self.off[j]+maxlen, self.off[j+1])\n            mzs.append(self.mz[a:b]); its.append(self.it[a:b])\n        mz=np.concatenate(mzs); it=np.concatenate(its)\n        o=np.argsort(mz); mz,it=mz[o],it[o]\n        keep=np.ones(len(mz),bool)\n        for j in range(1,len(mz)):\n            if mz[j]-mz[j-1] < 0.005:\n                if it[j]>=it[j-1]: keep[j-1]=False\n                else: keep[j]=False\n        mz,it=mz[keep],it[keep]\n        if len(mz)>maxlen:\n            top=np.argsort(-it)[:maxlen]; top.sort(); mz,it=mz[top],it[top]\n        return mz,it\n\n    def batch(self, ids, K=0, rng=None, ppm=10.0, aug=False, merge_p=0.0):\n        B=len(ids); L=fpmodel.MAX_PEAKS\n        lens=np.minimum(self.off[ids+1]-self.off[ids], L); N=max(int(lens.max()),1)\n        mz=np.zeros((B,N),np.float32); it=np.zeros((B,N),np.float32); pad=np.ones((B,N),bool)\n        for r,(i,l) in enumerate(zip(ids,lens)):\n            a=self.off[i]; mz[r,:l]=self.mz[a:a+l]; it[r,:l]=self.it[a:a+l]; pad[r,:l]=False\n        if merge_p>0 and rng is not None:\n            for r,i in enumerate(ids):\n                if rng.random()>=merge_p: continue\n                pk=self.peers(i,rng)\n                if len(pk)<2: continue\n                m2,i2=self._merged(pk, N)\n                n2=len(m2)\n                mz[r,:]=0; it[r,:]=0; pad[r,:]=True\n                mz[r,:n2]=m2; it[r,:n2]=i2; pad[r,:n2]=False\n        if aug and rng is not None:\n            # spectra are noisy measurements; jitter them so the model cannot memorise\n            # exact peak patterns of the 276k training structures (the earlier run\n            # overfit hard: val hardneg-top1 peaked at 0.46 then decayed to 0.13).\n            keep = rng.random((B,N)) > rng.uniform(0.0, 0.30, size=(B,1))   # peak dropout\n            pad = pad | (~keep)\n            it = it * np.exp(rng.normal(0.0, 0.25, size=(B,N))).astype(np.float32)  # intensity jitter\n            mz = mz * (1.0 + rng.normal(0.0, 5e-6, size=(B,N))).astype(np.float32)  # m/z jitter (~5 ppm)\n            allpad = pad.all(1)\n            if allpad.any(): pad[allpad,0]=False\n        d=self.device; T=lambda x: torch.as_tensor(x,device=d)\n        ce=np.where(self.ce[ids]<0,25.0,self.ce[ids]).astype(np.float32)\n        inp=(T(mz),T(it),T(pad),T(self.prec[ids]),T(self.ad[ids]),T(self.ins[ids]),T(ce),T(self.mode[ids]))\n        pos=self.s2p[self.six[ids]]\n        cand=None\n        if K>0:\n            negs=self.sample_negs(pos,K,ppm,rng)\n            cand=np.concatenate([pos[:,None],negs],1)         # (B,K+1), col 0 = positive\n            cand=torch.as_tensor(cand, device=self.PFP.device)\n        ypos=self.PFP[torch.as_tensor(pos, device=self.PFP.device)].to(d).float()\n        return inp, ypos, cand\n\ndef main():\n    ap=argparse.ArgumentParser()\n    ap.add_argument(\'--steps\',type=int,default=80000); ap.add_argument(\'--bs\',type=int,default=256)\n    ap.add_argument(\'--lr\',type=float,default=3e-4); ap.add_argument(\'--d\',type=int,default=512)\n    ap.add_argument(\'--layers\',type=int,default=6); ap.add_argument(\'--K\',type=int,default=63)\n    ap.add_argument(\'--lam\',type=float,default=1.0); ap.add_argument(\'--warm\',type=int,default=2000)\n    ap.add_argument(\'--out\',default=\'fp_model.pt\'); ap.add_argument(\'--resume\',default=\'\')\n    ap.add_argument(\'--val_every\',type=int,default=2000); ap.add_argument(\'--max_minutes\',type=float,default=1e9)\n    ap.add_argument(\'--seed\',type=int,default=7)\n    ap.add_argument(\'--merge_p\',type=float,default=0.6)\n    ap.add_argument(\'--spec\',default=\'ds/spec.npz\'); ap.add_argument(\'--fpdir\',default=\'up_train\'); ap.add_argument(\'--pooldir\',default=\'.\')\n    a=ap.parse_args()\n    dev=dev_of(); print(\'device\',dev,flush=True)\n    D=Data(a.spec,a.fpdir,a.pooldir,device=dev)\n    model=fpmodel.FPNet(D.nbits,d=a.d,layers=a.layers).to(dev)\n    print(\'params %.1fM\'%(sum(p.numel() for p in model.parameters())/1e6),flush=True)\n    torch.manual_seed(a.seed)\n    opt=torch.optim.AdamW(model.parameters(),lr=a.lr,weight_decay=0.01,betas=(0.9,0.98))\n    scaler=torch.amp.GradScaler(\'cuda\') if dev==\'cuda\' else None\n    start=0\n    if a.resume and os.path.exists(a.resume):\n        ck=torch.load(a.resume,map_location=dev); model.load_state_dict(ck[\'model\'])\n        try: opt.load_state_dict(ck[\'opt\'])\n        except Exception: pass\n        start=ck[\'step\']; print(\'resume\',start,flush=True)\n    def lr_at(s):\n        if s<a.warm: return a.lr*s/max(1,a.warm)\n        p=(s-a.warm)/max(1,a.steps-a.warm); return a.lr*(0.02+0.98*0.5*(1+math.cos(math.pi*min(p,1.0))))\n    rng=np.random.default_rng(a.seed)\n    t0=time.time(); rb=rc=racc=0.0; nr=0\n    best_val=-1.0   # keep the checkpoint that generalises best, not the last one\n    def save(step):\n        torch.save({\'model\':model.state_dict(),\'opt\':opt.state_dict(),\'step\':step,\n                    \'nbits\':D.nbits,\'d\':a.d,\'layers\':a.layers}, a.out)\n    for step in range(start,a.steps):\n        for g in opt.param_groups: g[\'lr\']=lr_at(step)\n        ids=rng.choice(D.tr,size=a.bs,replace=False)\n        inp,ypos,cand = D.batch(ids,K=a.K,rng=rng,aug=True,merge_p=a.merge_p)\n        opt.zero_grad(set_to_none=True)\n        ctx = torch.autocast(\'cuda\',dtype=torch.float16) if dev==\'cuda\' else torch.autocast(\'mps\',dtype=torch.float16) if dev==\'mps\' else torch.autocast(\'cpu\',enabled=False)\n        with ctx:\n            z=model(*inp)\n        z=z.float()\n        lb=F.binary_cross_entropy_with_logits(z,ypos)\n        FPc=D.PFP[cand].to(z.device).float()                     # (B,K+1,nbits)\n        raw=torch.bmm(FPc, z.unsqueeze(-1)).squeeze(-1)          # (B,K+1) = f.z  (exact Bayes LL up to const)\n        # centre within the example: subtracting (mean_c f_c).z is a per-example constant,\n        # so the ranking is untouched, but the magnitudes stay small enough for a stable softmax.\n        sc=(raw - raw.mean(dim=1, keepdim=True)) / math.sqrt(D.nbits)\n        tgt=torch.zeros(len(ids),dtype=torch.long,device=z.device)\n        lc=F.cross_entropy(sc,tgt)\n        loss=lb+a.lam*lc\n        if not torch.isfinite(loss):\n            print(f\'  non-finite loss at step {step}; skipping\', flush=True)\n            opt.zero_grad(set_to_none=True); continue\n        if scaler is not None:\n            scaler.scale(loss).backward(); scaler.unscale_(opt)\n            torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); scaler.step(opt); scaler.update()\n        else:\n            loss.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()\n        rb+=lb.item(); rc+=lc.item(); racc+=(sc.argmax(1)==0).float().mean().item(); nr+=1\n        if step%200==0:\n            el=time.time()-t0\n            print(f\'step {step} bce {rb/max(nr,1):.4f} ctr {rc/max(nr,1):.4f} top1 {racc/max(nr,1):.3f} lr {lr_at(step):.2e} {el:.0f}s {(step-start+1)*a.bs/max(el,1):.0f} spec/s\',flush=True)\n            rb=rc=racc=0.0; nr=0\n        if (step+1)%a.val_every==0:\n            model.eval(); vb=[];vacc=[]\n            with torch.no_grad():\n                vids=rng.choice(D.va,size=min(2048,len(D.va)),replace=False)\n                for s in range(0,len(vids),128):\n                    ii=vids[s:s+128]\n                    pos=D.s2p[D.six[ii]]\n                    if (pos<0).any(): ii=ii[pos>=0]\n                    if len(ii)==0: continue\n                    inp,ypos,cand=D.batch(ii,K=a.K,rng=rng,merge_p=a.merge_p)\n                    z=model(*inp).float()\n                    vb.append(F.binary_cross_entropy_with_logits(z,ypos).item())\n                    FPc=D.PFP[cand].to(z.device).float()\n                    raw=torch.bmm(FPc,z.unsqueeze(-1)).squeeze(-1)\n                    sc=(raw-raw.mean(dim=1,keepdim=True))/math.sqrt(D.nbits)\n                    vacc.append((sc.argmax(1)==0).float().mean().item())\n            va=float(np.mean(vacc))\n            print(f\'  VAL step {step} bce {np.mean(vb):.4f} hardneg-top1 {va:.3f}\'\n                  + (\'  <- best\' if va>best_val else \'\'),flush=True)\n            model.train()\n            if va>best_val:\n                best_val=va; save(step+1)          # only overwrite when validation improves\n        if (time.time()-t0)/60>a.max_minutes:\n            print(\'time budget reached; keeping best-val checkpoint\',flush=True); break\n    print(\'done. best hardneg-top1 = %.3f\'%best_val,flush=True)\n\nif __name__==\'__main__\': main()\n'

#---CELL---

# ===================================================================================
#  CONFIG — every knob in one place. Each is annotated with the measurement behind it.
# ===================================================================================
class CFG:
    # --- candidate generation -------------------------------------------------------
    PPM_WIN      = 10.0   # neutral-mass window for candidates. Tighter IS better -- up to the
                          # point where it starts deleting answers, which is the same trap as
                          # CAND_CAP below. Check window RECALL, not just MRR:
                          #   5.0 ppm 0.972 | 7.0 0.992 | 8.5 0.992 | 10.0 1.000 | 12+ 1.000
                          # 10 ppm is the smallest window that loses nothing, and everything
                          # wider only adds decoys. Full four-channel ranker agrees:
                          #   8.5 -> predLB 0.361 | 10.0 -> 0.371 | 12.0 -> 0.363
                          # (Much wider genuinely does hurt: +-20 -> 0.509, +-30 -> 0.500 C2 MRR.)
                          # timsTOF precursor error stays under ~9 ppm (+1.4 ppm offset).
    PPM_FALLBACK = 30.0   # only used if the tight window returns nothing at all.

    # --- spectrum cleaning ----------------------------------------------------------
    INT_FLOOR    = 0.002  # drop peaks below this fraction of the base peak
    MAX_PEAKS    = 256    # keep the N most intense peaks after the floor
    MZ_TOL       = 0.01   # Da tolerance when matching two peaks
    INT_POWER    = 1.0    # intensity transform before similarity (1.0 + entropy weighting
                          # beat sqrt: Class-1 0.919 vs 0.895)
    ENT_WEIGHT   = True   # Li et al. 2021 entropy weighting of low-entropy spectra

    # --- analog propagation (the main idea) -----------------------------------------
    ANALOG_WIN   = 200.0  # +- Da mass-shift window. +-400 gave no gain (0.520 vs 0.521).
    N_ANALOG     = 80     # analogs kept per molecule. Flat above 80 -- predicted LB 0.3683 (60),
                          # 0.3709 (80), 0.3705 (100), 0.3703 (140). Nothing to win here.
    SIM_POWER    = 3.0    # sim^p weighting. p=1 -> 0.498, p=3 -> 0.521, p=4 -> 0.525 on local
                          # validation -- but see the model-selection section: that validation set
                          # is the one the checkpoint was early-stopped on, so small local wins on
                          # it are not trustworthy. p=3 is the value that actually scored 0.335.

    # --- ranker ---------------------------------------------------------------------
    W1_PRIORS    = (0.30, 0.60)  # REVERTED. A narrow plateau (.40,.45,.50) scored 0.3789 in my
                          # own sweep and then LOST on the leaderboard (0.335 -> 0.330). The sweep
                          # was in-sample: it trained on all 819 query groups and evaluated on 250
                          # of them. See the ranker section -- hold out BY QUERY or you are just
                          # measuring capacity to memorise your own evaluation set.
    SEEDS        = (0, 1, 2, 3)  # seed alone moves the LB by ~0.006; bag several.
    W1           = 0.50   # weight on the Class-1 simulation. NOT the class share (0.16) --
                          # it is the leaderboard-calibrated value, chosen by 5-fold CV held out
                          # by query in make_ranker3.py.
    GBM = dict(max_depth=6, max_iter=500, learning_rate=0.03,
               min_samples_leaf=80, l2_regularization=1.0)
               # Depth 6, also REVERTED from 10. In-sample, depth 10 looked worth +0.007; on the
               # leaderboard it was not. Deeper trees fit the evaluation queries better precisely
               # because those queries were in the training rows.
    USE_BIO_DB   = False  # add ChEBI + LIPID MAPS. Costs -0.026 Class-2 MRR in dilution but
                          # adds 7-19% coverage of in-library structures. Looked net-positive
                          # on validation but the leaderboard disagreed (0.299 -> 0.295), so it
                          # ships OFF. Flip it if your pool recall differs.
                          # (Adding all of PubChem instead costs -0.35: measured, do not.)
    CAND_CAP     = 500    # pure runtime guard on in-silico fragmentation (~14 ms/candidate).
                          # It is deliberately LARGE. A cap of 80 ranked by "library hit, then
                          # closest in mass" looks like an adaptive version of "tighter windows
                          # win" -- it is not, it is a recall bug. Class-2 answers have
                          # library_sim = 0 *by definition* (no reference spectrum exists), so
                          # they get ordered by mass alone, which inside a +-8.5 ppm window is
                          # arbitrary. Measured truth retention on the Class-2 holdout:
                          #   no cap 0.992 | cap 400 0.992 | cap 200 0.952 | cap 80 0.752
                          # i.e. a cap of 80 throws away a QUARTER of the reachable answers.
                          # Class 1 is untouched (0.992 at every cap) because lv*100 protects it,
                          # which is exactly why the bug survives casual validation.
                          # Median window is 52 candidates, max 401, so 500 essentially never
                          # fires -- and when it does it ranks by the model, not by mass.
    PC_TOPK      = 50     # PubChem isomers admitted per query, ranked by the model's f.z.
                          # 0 disables the expansion entirely. Admitting ALL isomers costs a
                          # dilution factor d ~ 0.52; admitting the model's top 50 keeps d close
                          # to 1 while still reaching answers COCONUT does not contain.
    PC_WINCAP    = 10000  # isomers fingerprinted per query. This is the binding constraint on
                          # the whole expansion, not the admission cut: retain(50) = presence x
                          # conditional-retention = 0.788 x 0.79, and presence is set entirely by
                          # this number. Measured presence: 2k -> 0.788 | 5k -> 0.884 |
                          # 12k -> 0.940 | all -> 0.948. Windows run to 36,518 isomers.
                          # Costs ~5x the fingerprinting time; widen it before tuning PC_TOPK.
    TOPN         = 25     # the metric allows 25 guesses; there is no penalty for using them all

#---CELL---

import os, glob, time, pickle, math
import numpy as np, pandas as pd, pyarrow.parquet as pq, pyarrow as pa
T0 = time.time()

def find(name):
    hits = glob.glob(f'/kaggle/input/**/{name}', recursive=True)
    if not hits: raise FileNotFoundError(name)
    return sorted(hits, key=len)[0]

COMP   = os.path.dirname(find('test.parquet'))
TRAIN  = os.path.join(COMP, 'train.parquet')
TEST   = os.path.join(COMP, 'test.parquet')
SAMPLE = os.path.join(COMP, 'sample_submission.csv')
print('competition files:', os.listdir(COMP))

#---CELL---

# RDKit is not in the Kaggle image and internet is off for code competitions, so install the
# wheel from an attached dataset. Only the fragmentation channel needs it.
import subprocess, sys, glob
whl = glob.glob('/kaggle/input/**/rdkit-*.whl', recursive=True)
if whl:
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '--no-index', whl[0]], check=False)
try:
    from rdkit import Chem
    HAVE_RDKIT = True
except Exception:
    HAVE_RDKIT = False
print('RDKit available:', HAVE_RDKIT, '(fragmentation channel is optional - the notebook runs without it)')

#---CELL---
"""Similarity kernels: weighted cosine + spectral entropy similarity (Li et al. 2021)."""
import numpy as np
from numba import njit, prange

@njit(cache=True, fastmath=True)
def _clean(mz, it, floor, topk, power, ent_weight):
    n=len(mz)
    if n==0: return np.empty(0,np.float32), np.empty(0,np.float32)
    mx=0.0
    for i in range(n):
        if it[i]>mx: mx=it[i]
    if mx<=0: return np.empty(0,np.float32), np.empty(0,np.float32)
    thr=floor*mx; c=0
    for i in range(n):
        if it[i]>=thr: c+=1
    idx=np.empty(c,np.int64); j=0
    for i in range(n):
        if it[i]>=thr: idx[j]=i; j+=1
    if c>topk:
        v=np.empty(c,np.float32)
        for i in range(c): v[i]=it[idx[i]]
        o=np.argsort(v)[c-topk:]
        k2=np.empty(topk,np.int64)
        for i in range(topk): k2[i]=idx[o[i]]
        k2.sort(); idx=k2; c=topk
    om=np.empty(c,np.float32); oi=np.empty(c,np.float32)
    s=0.0
    for i in range(c):
        om[i]=mz[idx[i]]; v=it[idx[i]]**power; oi[i]=v; s+=v
    if s>0:
        for i in range(c): oi[i]/=s
    if ent_weight:
        S=0.0
        for i in range(c):
            if oi[i]>0: S-=oi[i]*np.log(oi[i])
        if S<3.0:
            w=0.25+0.25*S; s2=0.0
            for i in range(c): oi[i]=oi[i]**w; s2+=oi[i]
            if s2>0:
                for i in range(c): oi[i]/=s2
    return om, oi

@njit(cache=True, fastmath=True)
def entropy_sim(qmz,qp,cmz,cp,tol):
    i=0;j=0;n=len(qmz);m=len(cmz)
    SA=0.0
    for x in range(n):
        if qp[x]>0: SA-=qp[x]*np.log(qp[x])
    SB=0.0
    for x in range(m):
        if cp[x]>0: SB-=cp[x]*np.log(cp[x])
    SAB=0.0; tot=0.0
    buf=np.empty(n+m,np.float64); b=0
    while i<n and j<m:
        d=qmz[i]-cmz[j]
        if d<-tol: buf[b]=qp[i]; i+=1; b+=1
        elif d>tol: buf[b]=cp[j]; j+=1; b+=1
        else: buf[b]=qp[i]+cp[j]; i+=1; j+=1; b+=1
    while i<n: buf[b]=qp[i]; i+=1; b+=1
    while j<m: buf[b]=cp[j]; j+=1; b+=1
    for x in range(b): tot+=buf[x]
    if tot<=0: return 0.0
    for x in range(b):
        v=buf[x]/tot
        if v>0: SAB-=v*np.log(v)
    return 1.0-(2.0*SAB-SA-SB)/np.log(4.0)

@njit(cache=True, fastmath=True)
def cos_sim(qmz,qp,cmz,cp,tol):
    i=0;j=0;n=len(qmz);m=len(cmz); dot=0.0; na=0.0; nb=0.0
    for x in range(n): na+=qp[x]*qp[x]
    for x in range(m): nb+=cp[x]*cp[x]
    while i<n and j<m:
        d=qmz[i]-cmz[j]
        if d<-tol: i+=1
        elif d>tol: j+=1
        else: dot+=qp[i]*cp[j]; i+=1; j+=1
    if na<=0 or nb<=0: return 0.0
    return dot/np.sqrt(na*nb)

@njit(cache=True, fastmath=True, parallel=True)
def search(qmz,qp,cand,off,allmz,allin,tol,floor,topk,power,ent_weight,kind):
    out=np.zeros(len(cand),np.float32)
    for k in prange(len(cand)):
        c=cand[k]; a=off[c]; b=off[c+1]
        if b<=a: continue
        cm,cp=_clean(allmz[a:b],allin[a:b],floor,topk,power,ent_weight)
        if len(cm)==0: continue
        out[k]= entropy_sim(qmz,qp,cm,cp,tol) if kind==1 else cos_sim(qmz,qp,cm,cp,tol)
    return out

def prep(mz,it,floor=0.002,topk=256,power=0.5,ent_weight=False):
    return _clean(np.asarray(mz,np.float32),np.asarray(it,np.float32),floor,topk,power,ent_weight)

@njit(cache=True, fastmath=True)
def entropy_sim_shift(qmz,qp,cmz,cp,tol,shift):
    """Best of direct and mass-shifted entropy similarity."""
    a = entropy_sim(qmz,qp,cmz,cp,tol)
    if shift > -0.001 and shift < 0.001: return a
    sm = np.empty(len(cmz), np.float32)
    for i in range(len(cmz)): sm[i]=cmz[i]+shift
    b = entropy_sim(qmz,qp,sm,cp,tol)
    return a if a>b else b

@njit(cache=True, fastmath=True, parallel=True)
def search_shift(qmz,qp,cand,off,allmz,allin,tol,floor,topk,power,ent_weight,kind,shift):
    out=np.zeros(len(cand),np.float32)
    for k in prange(len(cand)):
        c=cand[k]; a=off[c]; b=off[c+1]
        if b<=a: continue
        cm,cp=_clean(allmz[a:b],allin[a:b],floor,topk,power,ent_weight)
        if len(cm)==0: continue
        out[k]=entropy_sim_shift(qmz,qp,cm,cp,tol,shift[k])
    return out

#---CELL---

# ===================================================================================
#  Adduct -> neutral mass.  The instrument measures the *ion*; candidates are neutral
#  molecules, so every adduct has to be undone before we can compare masses.
# ===================================================================================

MASS = dict(C=12.0,H=1.00782503207,N=14.0030740048,O=15.9949146196,P=30.97376163,
            S=31.97207100,F=18.99840322,Cl=34.96885268,Br=78.9183371,I=126.904473,
            Na=22.9897692809,K=38.96370668,Si=27.9769265325,B=11.0093054,Se=79.9165213)
E=0.00054857990; PROTON=MASS['H']-E; H2O=2*MASS['H']+MASS['O']
NH4=MASS['N']+4*MASS['H']; FORMATE=MASS['C']+2*MASS['H']+2*MASS['O']
ACETATE=2*MASS['C']+4*MASS['H']+2*MASS['O']
ADDUCTS = {
 "[M+H]+":(1,1,PROTON), "[M+NH4]+":(1,1,NH4-E), "[M+Na]+":(1,1,MASS['Na']-E),
 "[M+K]+":(1,1,MASS['K']-E), "[M-H2O+H]+":(1,1,PROTON-H2O), "[M-2H2O+H]+":(1,1,PROTON-2*H2O),
 "[M+2H]2+":(1,2,2*PROTON), "[M]+":(1,1,-E), "[M-H2O]+":(1,1,-E-H2O),
 "[M+CH3OH+H]+":(1,1,PROTON+MASS['C']+4*MASS['H']+MASS['O']),
 "[M+CH3CN+H]+":(1,1,PROTON+2*MASS['C']+3*MASS['H']+MASS['N']),
 "[M-H]-":(1,1,-PROTON), "[M-H2O-H]-":(1,1,-PROTON-H2O), "[M+CH2O2-H]-":(1,1,FORMATE-PROTON),
 "[M+C2H4O2-H]-":(1,1,ACETATE-PROTON), "[M+Cl]-":(1,1,MASS['Cl']+E), "[M]-":(1,1,E),
 "[M-2H]-":(1,2,-2*PROTON), "[M+Na-2H]-":(1,1,MASS['Na']-2*PROTON),
 "[2M+H]+":(2,1,PROTON), "[2M+Na]+":(2,1,MASS['Na']-E), "[2M+NH4]+":(2,1,NH4-E),
 "[2M+K]+":(2,1,MASS['K']-E), "[2M-H]-":(2,1,-PROTON), "[2M+CH2O2-H]-":(2,1,FORMATE-PROTON),
 "[2M+C2H4O2-H]-":(2,1,ACETATE-PROTON), "[2M+Na-2H]-":(2,1,MASS['Na']-2*PROTON),
 "[3M+H]+":(3,1,PROTON), "[3M-H]-":(3,1,-PROTON),
}
def neutral_mass(mz, adduct):
    out=np.full(len(mz), np.nan); ad=np.asarray(adduct, dtype=object)
    for a,(n,z,d) in ADDUCTS.items():
        m=(ad==a)
        if m.any(): out[m]=(mz[m]*z-d)/n
    return out


# ===================================================================================
#  Library + candidate pool
# ===================================================================================
def load_library(path):
    t0 = time.time()
    t = pq.read_table(path, columns=['inchikey14','normalized_smiles','adduct','precursor_mz',
                                     'ms2_mzs','ms2_normalized_intensities'])
    mzc = t.column('ms2_mzs').combine_chunks(); itc = t.column('ms2_normalized_intensities').combine_chunks()
    off = mzc.offsets.to_numpy().astype(np.int64)
    allmz = mzc.values.to_numpy(zero_copy_only=False).astype(np.float32)
    allin = itc.values.to_numpy(zero_copy_only=False).astype(np.float32)
    prec = t.column('precursor_mz').to_numpy(zero_copy_only=False).astype(np.float64)
    add = np.asarray(t.column('adduct').cast(pa.string()).to_pylist(), dtype=object)
    ik  = np.asarray(t.column('inchikey14').cast(pa.string()).to_pylist(), dtype=object)
    smi = np.asarray(t.column('normalized_smiles').cast(pa.string()).to_pylist(), dtype=object)
    nm  = neutral_mass(prec, add); ok = np.isfinite(nm)
    order = np.argsort(np.where(ok, nm, 1e18), kind='mergesort')
    best = {}
    for k, s in zip(ik, smi):
        if k and s and k not in best: best[k] = s
    print(f'library: {len(off)-1:,} spectra / {len(best):,} structures  ({time.time()-t0:.0f}s)', flush=True)
    return dict(off=off, mz=allmz, it=allin, nm=nm, ik=ik, best=best,
                order=order, snm=nm[order], n_ok=int(ok.sum()))

def lib_window(L, target, tol):
    lo = np.searchsorted(L['snm'][:L['n_ok']], target-tol, 'left')
    hi = np.searchsorted(L['snm'][:L['n_ok']], target+tol, 'right')
    return L['order'][lo:hi]

def build_rep(L):
    """One representative spectrum per structure (the richest), sorted by neutral mass.
       Using 3 per structure was WORSE (0.49 vs 0.52): extra spectra raise the max similarity
       of irrelevant structures too, which flattens the discrimination."""
    npk = np.diff(L['off']); best = {}; ik = L['ik']
    for i in range(len(ik)):
        k = ik[i]
        if k and (k not in best or npk[i] > npk[best[k]]): best[k] = i
    rep = np.array(sorted(best.values()))
    nm = L['nm'][rep]; ok = np.isfinite(nm)
    rep = rep[ok]; nm = nm[ok]; key = ik[rep]
    o = np.argsort(nm)
    return rep[o], key[o], nm[o]

# ===================================================================================
#  The two evidence channels
# ===================================================================================
def clean(mz, it):
    return _clean(np.asarray(mz, np.float32), np.asarray(it, np.float32),
                  CFG.INT_FLOOR, CFG.MAX_PEAKS, CFG.INT_POWER, CFG.ENT_WEIGHT)

def lib_sim(L, specs, target):
    """CLASS 1: direct match against library spectra of the same neutral mass."""
    cand = lib_window(L, target, target*CFG.PPM_WIN/1e6)
    if len(cand) == 0: return {}
    agg = {}
    for mz, it in specs:
        qm, qp = clean(mz, it)
        if len(qm) == 0: continue
        sc = search(qm, qp, cand, L['off'], L['mz'], L['it'],
                    CFG.MZ_TOL, CFG.INT_FLOOR, CFG.MAX_PEAKS, CFG.INT_POWER, CFG.ENT_WEIGHT, 1)
        for c, s in zip(cand, sc):
            k = L['ik'][c]
            if s > agg.get(k, -1.0): agg[k] = float(s)
    return agg

def analog_sim(L, specs, target, rep, rep_key, rep_nm):
    """CLASS 2: mass-SHIFTED match over a wide window. Relatives of the unknown fragment
       into the same ions offset by the mass difference, so they still match."""
    lo = np.searchsorted(rep_nm, target-CFG.ANALOG_WIN, 'left')
    hi = np.searchsorted(rep_nm, target+CFG.ANALOG_WIN, 'right')
    cand = rep[lo:hi]
    if len(cand) == 0: return []
    shift = (target - rep_nm[lo:hi]).astype(np.float32)
    ckey = rep_key[lo:hi]; agg = {}
    for mz, it in specs:
        qm, qp = clean(mz, it)
        if len(qm) == 0: continue
        sc = search_shift(qm, qp, cand, L['off'], L['mz'], L['it'],
                          CFG.MZ_TOL, CFG.INT_FLOOR, CFG.MAX_PEAKS,
                          CFG.INT_POWER, CFG.ENT_WEIGHT, 1, shift)
        for c, k, s in zip(cand, ckey, sc):
            if s > agg.get(k, -1.0): agg[k] = float(s)
    return sorted(agg.items(), key=lambda x: -x[1])[:CFG.N_ANALOG]

#---CELL---

# ===================================================================================
#  Candidate pool = COCONUT (attached, CC-BY) U training structures (rebuilt here).
#  Only the COCONUT half is redistributable, so the other half is computed at runtime.
# ===================================================================================
from rdkit import Chem, RDLogger
from rdkit.Chem import rdFingerprintGenerator, MACCSkeys
from rdkit.Chem.Descriptors import ExactMolWt
from multiprocessing import Pool as MPool
RDLogger.DisableLog('rdApp.*')

BITS = np.load(find('fp_bits.npy'))
_g = {}
def _fp_init():
    _g['m2'] = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=4096)
    _g['m3'] = rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=4096)
    _g['rk'] = rdFingerprintGenerator.GetRDKitFPGenerator(fpSize=2048, maxPath=6)

def fp_and_mass(smi):
    if not _g: _fp_init()
    m = Chem.MolFromSmiles(smi)
    if m is None: return None
    try:
        fp = np.concatenate([_g['m2'].GetFingerprintAsNumPy(m).astype(np.uint8),
                             _g['m3'].GetFingerprintAsNumPy(m).astype(np.uint8),
                             _g['rk'].GetFingerprintAsNumPy(m).astype(np.uint8),
                             np.array(MACCSkeys.GenMACCSKeys(m), dtype=np.uint8)])[BITS]
        return fp, float(ExactMolWt(m))
    except Exception:
        return None

class Pool:
    """Candidates + fingerprints, sorted by exact mass."""
    def __init__(s, fp, mass, keys, smiles, nbits):
        o = np.argsort(mass)
        s._fp = fp[o]; s.mass = mass[o]
        s.keys = np.asarray(keys, dtype=object)[o]
        s.smiles = np.asarray(smiles, dtype=object)[o]
        s.nbits = nbits
        s.k2i = {k: i for i, k in enumerate(s.keys)}
    def window(s, t, ppm):
        a = np.searchsorted(s.mass, t*(1-ppm/1e6), 'left')
        b = np.searchsorted(s.mass, t*(1+ppm/1e6), 'right')
        return np.arange(a, b)
    def fps(s, idx):
        return np.unpackbits(np.asarray(s._fp[idx]), axis=1)[:, :s.nbits]

def build_pool():
    t0 = time.time()
    d = os.path.dirname(find('coco_fp.npy'))
    cm = pickle.load(open(d + '/coco_meta.pkl', 'rb'))
    co_fp = np.load(d + '/coco_fp.npy'); co_mass = np.load(d + '/coco_mass.npy')
    co_keys = np.asarray(cm['keys'], dtype=object); co_smis = np.asarray(cm['smiles'], dtype=object)
    print(f'COCONUT: {len(co_mass):,} structures', flush=True)

    # ChEBI + LIPID MAPS: small, high-precision, and covers mammalian/lipid metabolites that a
    # plant/microbe-focused NP database misses. +8.8% candidates for +7-19% coverage of the
    # structures in the public spectral libraries (see the pool section).
    if CFG.USE_BIO_DB:
        try:
            bd = os.path.dirname(find('bio_fp.npy'))
            bm = pickle.load(open(bd + '/bio_meta.pkl', 'rb'))
            bi_fp = np.load(bd + '/bio_fp.npy'); bi_mass = np.load(bd + '/bio_mass.npy')
            co_fp = np.vstack([co_fp, bi_fp]); co_mass = np.concatenate([co_mass, bi_mass])
            co_keys = np.concatenate([co_keys, np.asarray(bm['keys'], dtype=object)])
            co_smis = np.concatenate([co_smis, np.asarray(bm['smiles'], dtype=object)])
            print(f'+ ChEBI/LIPID MAPS: {len(bi_mass):,} structures', flush=True)
        except FileNotFoundError:
            print('ChEBI/LIPID MAPS dataset not attached - skipping', flush=True)

    tr = pq.read_table(TRAIN, columns=['inchikey14', 'normalized_smiles']).to_pandas()
    tr = tr.dropna().drop_duplicates('inchikey14')
    tr = tr[~tr.inchikey14.isin(set(co_keys))]
    print(f'training structures to fingerprint: {len(tr):,}  (~5 min)', flush=True)
    with MPool(4) as mp:
        res = mp.map(fp_and_mass, list(tr.normalized_smiles), chunksize=500)
    ok = [i for i, r in enumerate(res) if r is not None]
    tr_fp = np.packbits(np.stack([res[i][0] for i in ok]), axis=1)
    tr_mass = np.array([res[i][1] for i in ok])
    tr_keys = tr.inchikey14.values[ok]; tr_smi = tr.normalized_smiles.values[ok]

    fp = np.vstack([co_fp, tr_fp])
    mass = np.concatenate([co_mass, tr_mass])
    keys = np.concatenate([co_keys, tr_keys])
    smis = np.concatenate([co_smis, tr_smi])
    good = np.isfinite(mass)
    print(f'pool: {int(good.sum()):,} structures   ({time.time()-t0:.0f}s)', flush=True)
    return Pool(fp[good], mass[good], keys[good], smis[good], cm['nbits'])

#---CELL---
"""Single source of truth for candidate ranking features (used by local fitting AND the notebook).

Deliberately EXCLUDES any feature revealing pool provenance (src / np_likeness): in the Class-2
simulation the answer is always a training-library structure, so those columns leak.
"""
import numpy as np

N_ANALOG = 80
P_SIM    = 3.0
N_FEAT   = 31

def _rank_norm(x):
    o=np.argsort(-x); r=np.empty(len(x)); r[o]=np.arange(len(x)); return r/max(1,len(x)-1)

def _z(x):
    s=x.std()
    return (x-x.mean())/s if s>1e-9 else np.zeros_like(x)

def rank_features(cand_fp, cand_lib, analog_fp, analog_sim, model_logits=None, frag=None):
    """cand_fp (nc,nbits), cand_lib (nc,) library similarity (0 if none),
       analog_fp (na,nbits), analog_sim (na,) descending,
       model_logits (nbits,) or None -> fingerprint-model evidence,
       frag (nc,) or None -> in-silico fragmentation explain-score (MetFrag-lite).
       Returns X (nc, N_FEAT)."""
    nc = cand_fp.shape[0]
    cf = cand_fp.astype(np.float32); cs = cf.sum(1)
    lv = np.asarray(cand_lib, np.float32)
    lvmax = float(lv.max()) if nc else 0.0
    if analog_fp is not None and len(analog_sim):
        af = analog_fp.astype(np.float32); asum = af.sum(1)
        inter = cf @ af.T
        tan = inter/(cs[:,None]+asum[None,:]-inter+1e-9)
        w = np.clip(np.asarray(analog_sim,np.float32),0,None)
        ap = (tan*(w**P_SIM)[None,:]).max(1)
        a1 = (tan*w[None,:]).max(1)
        best_tan = tan.max(1); top_tan = tan[:,0]; top_sim = float(w[0])
        mean_tan = (tan*(w**P_SIM)[None,:]).sum(1)/((w**P_SIM).sum()+1e-9)
    else:
        ap=a1=best_tan=top_tan=mean_tan=np.zeros(nc,np.float32); top_sim=0.0
    apmax = float(ap.max()) if nc else 0.0
    if model_logits is not None:
        raw = cf @ np.asarray(model_logits, np.float32)       # exact Bayes LL up to a constant
        nrm = raw/np.sqrt(np.maximum(cs,1.0))                 # length-corrected variant
        mfeat = [_z(raw), _rank_norm(raw), raw-raw.max(), _z(nrm), _rank_norm(nrm),
                 (raw==raw.max()).astype(np.float32)]
    else:
        mfeat = [np.zeros(nc,np.float32)]*6
    # cross-channel agreement: a genuine Class-1 hit should look good to the MODEL too.
    # When the library's best match also ranks high under f.z, the library evidence is
    # corroborated; when it does not, the library hit is probably a same-mass impostor.
    if model_logits is not None and nc:
        mr = _rank_norm(cf @ np.asarray(model_logits, np.float32))
        lbest = int(np.argmax(lv)) if lvmax > 0 else -1
        agree = float(1.0 - mr[lbest]) if lbest >= 0 else 0.0      # 1 = model also ranks it first
        abest = int(np.argmax(ap)) if apmax > 0 else -1
        agree_a = float(1.0 - mr[abest]) if abest >= 0 else 0.0
        xfeat = [lv*(1.0-mr), ap*(1.0-mr), np.full(nc, agree), np.full(nc, agree_a),
                 np.full(nc, agree*lvmax), np.full(nc, float(np.corrcoef(lv, -mr)[0,1]) if lv.std()>1e-9 else 0.0)]
    else:
        xfeat = [np.zeros(nc,np.float32)]*6
    if frag is not None:
        fr = np.asarray(frag, np.float32)
        ffeat = [fr, _rank_norm(fr), fr-fr.max() if nc else fr, _z(fr)]
    else:
        ffeat = [np.zeros(nc,np.float32)]*4
    return np.column_stack([
        lv, _rank_norm(lv), np.full(nc,lvmax), lv-lvmax, (lv>0).astype(float),
        ap, _rank_norm(ap), np.full(nc,apmax), ap-apmax,
        a1, best_tan, top_tan, mean_tan, np.full(nc,top_sim),
        np.full(nc, np.log(max(nc,1))),
        *mfeat, *ffeat, *xfeat,
    ]).astype(np.float32)

#---CELL---
"""MetFrag-lite: score a candidate by how much of the observed spectrum its bond-breaking
   fragments can explain. Independent evidence from analog propagation."""
import numpy as np
from rdkit import Chem, RDLogger
RDLogger.DisableLog('rdApp.*')

AMU = {'C':12.0,'H':1.00782503207,'N':14.0030740048,'O':15.9949146196,'P':30.97376163,
       'S':31.97207100,'F':18.99840322,'Cl':34.96885268,'Br':78.9183371,'I':126.904473,
       'Na':22.9897692809,'K':38.96370668,'Si':27.9769265325,'B':11.0093054,'Se':79.9165213}
H = AMU['H']; PROTON = H - 0.00054857990

def mol_graph(smi):
    m = Chem.MolFromSmiles(smi)
    if m is None: return None
    n = m.GetNumAtoms()
    w = np.zeros(n)
    for a in m.GetAtoms():
        w[a.GetIdx()] = AMU.get(a.GetSymbol(), 0.0) + a.GetTotalNumHs()*H
    if (w == 0).any(): return None
    bonds = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in m.GetBonds()]
    return w, bonds, n

def _components(n, bonds, drop):
    adj = [[] for _ in range(n)]
    for i,(a,b) in enumerate(bonds):
        if i in drop: continue
        adj[a].append(b); adj[b].append(a)
    seen = np.zeros(n, bool); comps=[]
    for s in range(n):
        if seen[s]: continue
        stack=[s]; seen[s]=True; cur=[s]
        while stack:
            u=stack.pop()
            for v in adj[u]:
                if not seen[v]: seen[v]=True; stack.append(v); cur.append(v)
        comps.append(cur)
    return comps

def fragment_masses(smi, max_breaks=2, max_bonds=34):
    """Neutral fragment masses from breaking 1 or 2 bonds."""
    g = mol_graph(smi)
    if g is None: return np.zeros(0)
    w, bonds, n = g
    nb = len(bonds)
    if nb == 0 or nb > max_bonds: return np.array([w.sum()])
    out = {w.sum()}
    for i in range(nb):
        for c in _components(n, bonds, {i}):
            out.add(float(w[c].sum()))
    if max_breaks >= 2:
        for i in range(nb):
            for j in range(i+1, nb):
                for c in _components(n, bonds, {i, j}):
                    out.add(float(w[c].sum()))
    return np.array(sorted(out))

def explain_score(frag_mass, peak_mz, peak_int, mode=1.0, tol=0.01, h_shifts=(-2,-1,0,1,2)):
    """Fraction of total (sqrt) intensity explained by some fragment ion."""
    if len(frag_mass) == 0 or len(peak_mz) == 0: return 0.0
    ion = []
    for dh in h_shifts:
        ion.append(frag_mass + dh*H + (PROTON if mode > 0 else -PROTON))
    ion = np.sort(np.concatenate(ion))
    w = np.sqrt(np.asarray(peak_int, float)); tot = w.sum()
    if tot <= 0: return 0.0
    idx = np.searchsorted(ion, peak_mz)
    ok = np.zeros(len(peak_mz), bool)
    for off in (-1, 0):
        k = np.clip(idx+off, 0, len(ion)-1)
        ok |= np.abs(ion[k]-peak_mz) <= tol
    return float(w[ok].sum()/tot)

#---CELL---

from multiprocessing import Pool as MPool

def _frag_masses(smi):
    try:  return fragment_masses(smi)
    except Exception: return np.zeros(0)

def frag_scores(cand_smiles, specs, mode, workers=4):
    """MetFrag-lite explain-score for every candidate, max over the molecule's spectra."""
    if not HAVE_RDKIT: return None
    with MPool(workers) as mp:
        frags = mp.map(_frag_masses, cand_smiles, chunksize=8)
    peaks = []
    for mz, it in specs:
        m2, i2 = _clean(np.asarray(mz, np.float32), np.asarray(it, np.float32),
                        CFG.INT_FLOOR, CFG.MAX_PEAKS, 1.0, False)
        peaks.append((np.asarray(m2, float), np.asarray(i2, float)))
    out = np.zeros(len(cand_smiles), np.float32)
    for j, f in enumerate(frags):
        out[j] = max((explain_score(f, a, b, mode=mode, tol=CFG.MZ_TOL) for a, b in peaks), default=0.0)
    return out

#---CELL---
"""Spectrum -> molecular fingerprint model (CSI:FingerID-style neural ranker)."""
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F, math

MAX_PEAKS = 128
ADDUCT_LIST = ["[M+H]+","[M+NH4]+","[M+Na]+","[M+K]+","[M-H2O+H]+","[M-2H2O+H]+","[M]+",
               "[M-H]-","[M-H2O-H]-","[M+CH2O2-H]-","[M+C2H4O2-H]-","[M+Cl]-","[M]-",
               "[M+2H]2+","[M-2H]-","[2M+H]+","[2M+Na]+","[2M+NH4]+","[2M-H]-","[2M+K]+",
               "[2M+CH2O2-H]-","[2M+C2H4O2-H]-","[2M+Na-2H]-","[M+Na-2H]-","[M-H2O]+","<unk>"]
ADDUCT_IX = {a:i for i,a in enumerate(ADDUCT_LIST)}
INSTR_LIST = ["timsTOF","Orbitrap","QTOF","IT","other"]
INSTR_IX = {a:i for i,a in enumerate(INSTR_LIST)}

def instr_family(s):
    if s is None: return 4
    t = str(s).lower()
    if 'timstof' in t: return 0
    if 'orbitrap' in t or 'qft' in t or 'ftms' in t or 'hybrid ft' in t or 'itft' in t or 'exactive' in t: return 1
    if 'tof' in t: return 2
    if 'trap' in t or 'qq' in t: return 3
    return 4

def prep_peaks(mz, inten, prec_mz, max_peaks=MAX_PEAKS, floor=1e-3, win=50.0, per_win=8):
    """Filter -> window-diversified top-N -> sort by m/z. Returns (mz, sqrt-intensity)."""
    mz = np.asarray(mz, np.float64); it = np.asarray(inten, np.float64)
    if len(mz)==0: return np.zeros(0,np.float32), np.zeros(0,np.float32)
    keep = (mz <= prec_mz + 1.5)
    mz, it = mz[keep], it[keep]
    if len(mz)==0: return np.zeros(0,np.float32), np.zeros(0,np.float32)
    mx = it.max()
    if mx <= 0: return np.zeros(0,np.float32), np.zeros(0,np.float32)
    keep = it >= floor*mx
    mz, it = mz[keep], it[keep]
    if len(mz) > max_peaks:
        # keep the top `per_win` peaks inside each `win` Da bucket, then global top-N
        order = np.argsort(-it)
        bucket = (mz//win).astype(np.int64)
        cnt = {}; sel=[]
        for i in order:
            b = bucket[i]; c = cnt.get(b,0)
            if c < per_win: cnt[b]=c+1; sel.append(i)
        sel = np.array(sel)
        if len(sel) > max_peaks:
            sel = sel[np.argsort(-it[sel])[:max_peaks]]
        elif len(sel) < max_peaks:
            rest = np.array([i for i in order if i not in set(sel.tolist())])
            need = max_peaks-len(sel)
            if len(rest): sel = np.concatenate([sel, rest[:need]])
        mz, it = mz[sel], it[sel]
    o = np.argsort(mz)
    mz, it = mz[o], it[o]
    v = np.sqrt(it/it.max())
    return mz.astype(np.float32), v.astype(np.float32)

class SinEmb(nn.Module):
    """Log-spaced sinusoidal embedding for m/z values (Voronov et al.)."""
    def __init__(self, dim, lo=-2.0, hi=3.2, power=1.0):
        super().__init__()
        n = dim//2
        wav = torch.pow(10.0, (hi-lo)*torch.pow(torch.linspace(0,1,n), power) + lo)
        self.register_buffer('inv', (2*math.pi)/wav)
    def forward(self, x):                      # x: (...,)
        a = x.unsqueeze(-1) * self.inv
        return torch.cat([torch.sin(a), torch.cos(a)], -1)

class Block(nn.Module):
    def __init__(self, d, h, drop):
        super().__init__(); self.h=h
        self.n1=nn.LayerNorm(d); self.qkv=nn.Linear(d,3*d); self.o=nn.Linear(d,d)
        self.n2=nn.LayerNorm(d)
        self.ff=nn.Sequential(nn.Linear(d,4*d), nn.GELU(), nn.Dropout(drop), nn.Linear(4*d,d))
        self.drop=nn.Dropout(drop)
    def forward(self, x, pad):
        B,N,D=x.shape; y=self.n1(x)
        q,k,v = self.qkv(y).view(B,N,3,self.h,D//self.h).permute(2,0,3,1,4)
        m = (~pad)[:,None,None,:]                       # True = attend
        a = F.scaled_dot_product_attention(q,k,v, attn_mask=m)
        x = x + self.drop(self.o(a.transpose(1,2).reshape(B,N,D)))
        return x + self.drop(self.ff(self.n2(x)))

class FPNet(nn.Module):
    def __init__(self, nbits, d=512, layers=6, heads=8, drop=0.1):
        super().__init__()
        self.d=d
        self.mz_emb  = SinEmb(d)
        self.nl_emb  = SinEmb(d)
        self.pk = nn.Linear(2*d+1, d)
        self.prec_emb = SinEmb(d)
        self.ad = nn.Embedding(len(ADDUCT_LIST), d)
        self.ins = nn.Embedding(len(INSTR_LIST), d)
        self.gl = nn.Linear(d+3, d)
        self.blocks = nn.ModuleList([Block(d,heads,drop) for _ in range(layers)])
        self.norm = nn.LayerNorm(d)
        self.head = nn.Sequential(nn.Linear(2*d, 2048), nn.GELU(), nn.Dropout(drop), nn.Linear(2048, nbits))
    def forward(self, mz, it, pad, prec, ad, ins, ce, mode):
        B,N = mz.shape
        nl = (prec[:,None] - mz).clamp(min=0)
        p = self.pk(torch.cat([self.mz_emb(mz), self.nl_emb(nl), it.unsqueeze(-1)], -1))
        g = self.gl(torch.cat([self.prec_emb(prec),
                               (ce/100.0).unsqueeze(-1), mode.unsqueeze(-1),
                               torch.log1p(prec).unsqueeze(-1)/10.0], -1)) + self.ad(ad) + self.ins(ins)
        x = torch.cat([g.unsqueeze(1), p], 1)
        pad = torch.cat([torch.zeros(B,1,dtype=torch.bool,device=pad.device), pad], 1)
        for b in self.blocks: x = b(x, pad)
        x = self.norm(x)
        cls = x[:,0]
        msk = (~pad[:,1:]).float().unsqueeze(-1)
        mean = (x[:,1:]*msk).sum(1)/msk.sum(1).clamp(min=1)
        return self.head(torch.cat([cls, mean], -1))

#---CELL---

# ===================================================================================
#  Channel 4: spectrum -> molecular fingerprint (CSI:FingerID-style), ranked by f . z
# ===================================================================================
import torch
_MODEL = None
def load_model():
    """Optional. If the weights dataset is not attached, everything still runs without it."""
    global _MODEL
    import glob
    paths = sorted(glob.glob('/kaggle/input/**/fp_*.pt', recursive=True))
    if not paths:
        print('fingerprint model not attached - running with 3 channels'); return None
    dev = 'cuda' if torch.cuda.is_available() else 'cpu'
    # Each model is fed the input distribution it was TRAINED on. 'fp_merged_*' saw fused
    # multi-spectrum inputs (--merge_p 0.6) and wants one merged peak list; 'fp_single_*' saw
    # one spectrum at a time. Feeding either the wrong way costs ~0.02 Class-2 MRR:
    #   m1: merged 0.4896 / per-spectrum 0.4687     s2: per-spectrum 0.4799 / merged 0.4597
    single, merged = [], []
    for pth in paths:
        ck = torch.load(pth, map_location='cpu', weights_only=False)
        net = FPNet(ck['nbits'], d=ck['d'], layers=ck['layers']).to(dev).eval()
        net.load_state_dict(ck['model'])
        (merged if 'merged' in pth.split('/')[-1] else single).append(net)
        print(f'  loaded {pth.split("/")[-1]}: d={ck["d"]} layers={ck["layers"]} step={ck.get("step")}')
    print(f'fingerprint models: {len(single)} single-input, {len(merged)} merged-input, on {dev}')
    _MODEL = (single, merged, dev, ck['nbits'])
    return _MODEL

def _merge_peaks(sub):
    """All of a molecule's peaks collapsed into one pseudo-spectrum (near-duplicate m/z merged,
       keeping the stronger peak). A second view of the same molecule."""
    mz = np.concatenate([np.asarray(r.ms2_mzs, float) for r in sub.itertuples()])
    it = np.concatenate([np.asarray(r.ms2_normalized_intensities, float) /
                         max(float(np.asarray(r.ms2_normalized_intensities, float).max()), 1e-9)
                         for r in sub.itertuples()])
    o = np.argsort(mz); mz, it = mz[o], it[o]
    keep = np.ones(len(mz), bool)
    for j in range(1, len(mz)):
        if mz[j]-mz[j-1] < 0.005:
            if it[j] >= it[j-1]: keep[j-1] = False
            else: keep[j] = False
    return mz[keep], it[keep]

@torch.no_grad()
def model_logits(sub):
    """Two fusion views, averaged: (a) per-spectrum logits averaged, (b) one merged peak list.
       Measured on the Class-2 holdout: (a) 0.468, (b) 0.459, mean of both 0.475."""
    if _MODEL is None: return None
    single, merged, dev, nbits = _MODEL
    out = []
    if single:
        za = _logits_from(sub, single)
        if za is not None: out.append(za)
    if merged:
        mz, it = _merge_peaks(sub)
        r0 = next(sub.itertuples())
        zb = _logits_raw([(mz, it)], merged, float(np.median(sub.precursor_mz)), r0.adduct,
                         r0.instrument_type, 25.0,
                         float(np.mean([1.0 if m=='positive' else -1.0 for m in sub.ionization_mode])))
        if zb is not None: out.append(zb)
    return np.mean(out, axis=0) if out else None

@torch.no_grad()
def _logits_from(sub, nets):
    if _MODEL is None: return None
    dev = _MODEL[2]
    rows = list(sub.itertuples())
    P = [prep_peaks(r.ms2_mzs, r.ms2_normalized_intensities, float(r.precursor_mz)) for r in rows]
    P = [(a,b) for a,b in P if len(a)]
    if not P: return None
    B = len(P); N = max(len(a) for a,_ in P)
    mz=np.zeros((B,N),np.float32); it=np.zeros((B,N),np.float32); pad=np.ones((B,N),bool)
    for i,(a,b) in enumerate(P):
        mz[i,:len(a)]=a; it[i,:len(b)]=b; pad[i,:len(a)]=False
    def ce_of(r):
        v=r.collision_energy_ev
        try: return float(np.mean(np.atleast_1d(v))) if v is not None and len(np.atleast_1d(v)) else 25.0
        except Exception: return 25.0
    T=lambda x: torch.as_tensor(x, device=dev)
    args = (T(mz), T(it), T(pad),
            T(np.array([float(r.precursor_mz) for r in rows[:B]],np.float32)),
            T(np.array([ADDUCT_IX.get(r.adduct, ADDUCT_IX['<unk>']) for r in rows[:B]])),
            T(np.array([instr_family(r.instrument_type) for r in rows[:B]])),
            T(np.array([ce_of(r) for r in rows[:B]],np.float32)),
            T(np.array([1.0 if r.ionization_mode=='positive' else -1.0 for r in rows[:B]],np.float32)))
    # average over the ensemble, then over the molecule's spectra
    return np.mean([n(*args).float().mean(0).cpu().numpy() for n in nets], axis=0)

@torch.no_grad()
def _logits_raw(pairs, nets, prec, adduct, instrument, ce, mode):
    """Same forward pass for an explicitly supplied peak list."""
    if _MODEL is None: return None
    dev = _MODEL[2]
    P=[prep_peaks(mz, it, prec) for mz, it in pairs]
    P=[(a,b) for a,b in P if len(a)]
    if not P: return None
    B=len(P); N=max(len(a) for a,_ in P)
    mz=np.zeros((B,N),np.float32); it=np.zeros((B,N),np.float32); pad=np.ones((B,N),bool)
    for i,(a,b) in enumerate(P):
        mz[i,:len(a)]=a; it[i,:len(b)]=b; pad[i,:len(a)]=False
    T=lambda x: torch.as_tensor(x, device=dev)
    args=(T(mz),T(it),T(pad), T(np.full(B,prec,np.float32)),
          T(np.full(B, ADDUCT_IX.get(adduct, ADDUCT_IX['<unk>']))),
          T(np.full(B, instr_family(instrument))),
          T(np.full(B, ce, np.float32)), T(np.full(B, mode, np.float32)))
    return np.mean([n(*args).float().mean(0).cpu().numpy() for n in nets], axis=0)

#---CELL---

# ===================================================================================
#  Optional pool expansion: PubChem isomers inside the same ppm window.
#  This is the one lever the local holdout CANNOT score. Every validation answer is
#  already in the pool (recall 100% at +-10 ppm), so adding a database can only ever
#  show up as dilution -- never as the recall it buys. The decision is therefore made
#  by algebra, not by validation:
#      adding pays  iff  rho' * d > rho
#  where rho is current pool recall, rho' the expanded recall, and d the dilution
#  factor. Measured COCONUT coverage of natural products brackets rho at 0.38-0.99,
#  and the break-even sits at 0.52 -- inside the bracket. So it gets a submission.
#  Dilution is controlled by admitting only the top PC_TOPK isomers by the model's
#  f.z, which is real evidence, rather than all of them (that cost d ~ 0.52).
# ===================================================================================
import glob, os

PC = None
def load_pcstore():
    global PC
    hits = sorted(glob.glob('/kaggle/input/**/mass_sorted.npy', recursive=True))
    if not hits or not CFG.PC_TOPK:
        print('PubChem store not attached - pool expansion off'); return None
    d = os.path.dirname(hits[0])
    PC = dict(ms=np.load(d + '/mass_sorted.npy', mmap_mode='r'),
              order=np.load(d + '/order.npy', mmap_mode='r'),
              off=np.load(d + '/off.npy', mmap_mode='r'),
              ln=np.load(d + '/len.npy', mmap_mode='r'),
              fh=open(d + '/smiles.txt', 'rb'))
    print(f'PubChem store: {len(PC["ms"]):,} NP-formula structures, mass-indexed')
    return PC

def pc_window(target, ppm, cap):
    lo = np.searchsorted(PC['ms'], target*(1-ppm/1e6), 'left')
    hi = np.searchsorted(PC['ms'], target*(1+ppm/1e6), 'right')
    idx = np.asarray(PC['order'][lo:hi])
    if len(idx) > cap:                      # even sample, not a mass-biased prefix
        idx = idx[np.linspace(0, len(idx)-1, cap).astype(np.int64)]
    return idx

def pc_smiles(idx):
    out = []; o = np.asarray(PC['off'][idx]); l = np.asarray(PC['ln'][idx])
    for a, b in zip(o, l):
        PC['fh'].seek(int(a)); out.append(PC['fh'].read(int(b)).decode('ascii', 'ignore'))
    return out

def _fp_canon(smi):
    """Fingerprint + a canonical, stereo-free SMILES so we can drop entries the pool already has."""
    if not _g: _fp_init()
    m = Chem.MolFromSmiles(smi)
    if m is None: return None
    try:
        Chem.RemoveStereochemistry(m)
        return Chem.MolToSmiles(m), np.concatenate([
            _g['m2'].GetFingerprintAsNumPy(m).astype(np.uint8),
            _g['m3'].GetFingerprintAsNumPy(m).astype(np.uint8),
            _g['rk'].GetFingerprintAsNumPy(m).astype(np.uint8),
            np.array(MACCSkeys.GenMACCSKeys(m), dtype=np.uint8)])[BITS]
    except Exception:
        return None

def pubchem_extra(target, zlog, known, workers=4):
    """Top-PC_TOPK PubChem isomers by f.z that the pool does not already contain."""
    if PC is None or zlog is None or not CFG.PC_TOPK: return None, []
    idx = pc_window(target, CFG.PPM_WIN, CFG.PC_WINCAP)
    if len(idx) == 0: return None, []
    smis = pc_smiles(idx)
    with MPool(workers) as mp:
        res = mp.map(_fp_canon, smis, chunksize=64)
    fps = []; sms = []
    for r in res:
        if r is None: continue
        cs, f = r
        if cs in known: continue
        known.add(cs); fps.append(f); sms.append(cs)
    if not fps: return None, []
    F = np.stack(fps).astype(np.uint8)
    z = F.astype(np.float32) @ np.asarray(zlog, np.float32)
    k = np.argsort(-z)[:CFG.PC_TOPK]
    return F[k], [sms[i] for i in k]

#---CELL---

# ===================================================================================
#  Calibrated ranker.  Fitted here, in-notebook, from shipped simulation features so
#  the whole thing is reproducible and you can retune W1 in one line.
# ===================================================================================
from sklearn.ensemble import HistGradientBoostingClassifier
z = np.load(find('rank_train.npz'))
NFEAT = z['X'].shape[1]

# ---------------------------------------------------------------------------------
#  ⚠️  HistGradientBoostingClassifier defaults to random_state=None.
#  I submitted the SAME notebook version twice and got 0.292 and 0.298 -- a 0.006
#  spread from the ranker's seed alone (5 local seeds span 0.2961-0.3033). If you are
#  chasing a 0.005 leaderboard difference in this competition, you may be chasing noise.
#  Fix: pin the seed AND average over several, which removes the variance and lifts the mean.
# ---------------------------------------------------------------------------------
RANKERS = []
for w1 in CFG.W1_PRIORS:                  # a NARROW plateau around the swept peak -- see CFG
    W = np.where(z['M'] == 0, w1, 1.0 - w1)
    for sd in CFG.SEEDS:
        m = HistGradientBoostingClassifier(random_state=sd, **CFG.GBM)
        m.fit(z['X'], z['Y'], sample_weight=W)
        RANKERS.append(m)

def rank_proba(X):
    """Averaged over seeds and class priors -> deterministic and lower variance."""
    return np.mean([m.predict_proba(X)[:, 1] for m in RANKERS], axis=0)

print(f'ranker: {len(RANKERS)} GBMs ({len(CFG.W1_PRIORS)} priors x {len(CFG.SEEDS)} seeds) '
      f'on {z["X"].shape[0]:,} rows x {NFEAT} features')

#---CELL---

# ===================================================================================
#  Run: one ranked list of 25 SMILES per molecule
# ===================================================================================
load_model()
load_pcstore()
pool = build_pool()
print(f'candidate pool: {len(pool.mass):,} structures, {pool.nbits} fingerprint bits', flush=True)

L = load_library(TRAIN)
rep, rep_key, rep_nm = build_rep(L)
print(f'analog reference set: {len(rep):,} spectra (one per structure)', flush=True)

te = pq.read_table(TEST).to_pandas()
te['nm'] = neutral_mass(te.precursor_mz.values.astype(np.float64), te.adduct.values)
mols = list(te.groupby('molecule_id'))
print(f'{len(te):,} spectra / {len(mols):,} molecules to identify', flush=True)

rows, diag = [], []
for gi, (mid, sub) in enumerate(mols):
    nms  = sub.nm.values[np.isfinite(sub.nm.values)]
    smis = []
    if len(nms):
        target = float(np.median(nms))                       # fuse all spectra of the molecule
        specs  = [(r.ms2_mzs, r.ms2_normalized_intensities) for r in sub.itertuples()]

        lib_hits = lib_sim(L, specs, target)                 # Class-1 evidence
        analogs  = analog_sim(L, specs, target, rep, rep_key, rep_nm)   # Class-2 evidence

        cand = pool.window(target, CFG.PPM_WIN)
        if len(cand) == 0:
            cand = pool.window(target, CFG.PPM_FALLBACK)
        if len(cand):
            lv = np.array([lib_hits.get(pool.keys[c], 0.0) for c in cand], np.float32)
            zlog = model_logits(sub)
            if CFG.CAND_CAP and len(cand) > CFG.CAND_CAP:
                # Rank by real evidence, not by mass: library hit first, then the model's f.z.
                coarse = lv * 100.0
                if zlog is not None:
                    mz = pool.fps(cand).astype(np.float32) @ zlog
                    coarse = coarse + (mz - mz.mean()) / max(float(mz.std()), 1e-9)
                else:
                    coarse = coarse - np.abs(pool.mass[cand] - target)
                keep = np.argsort(-coarse)[:CFG.CAND_CAP]
                cand, lv = cand[keep], lv[keep]
            cfp = pool.fps(cand)
            csmi = [pool.smiles[c] for c in cand]
            ex_fp, ex_smi = pubchem_extra(target, zlog, set(csmi))
            if ex_smi:
                cfp = np.concatenate([cfp, ex_fp])
                lv  = np.concatenate([lv, np.zeros(len(ex_smi), np.float32)])
                csmi = csmi + ex_smi
            ids, sims = [], []
            for k, s in analogs:
                i = pool.k2i.get(k, -1)
                if i >= 0: ids.append(i); sims.append(s)
            afp = pool.fps(np.array(ids)) if ids else None
            fsc = frag_scores(csmi, specs,
                              float(np.mean([1.0 if m == 'positive' else -1.0
                                             for m in sub.ionization_mode])))
            X   = rank_features(cfp, lv, afp, np.array(sims, np.float32), zlog, fsc)[:, :NFEAT]
            p   = rank_proba(X)
            order = np.argsort(-p)[:CFG.TOPN]
            smis  = [csmi[i] for i in order]
            diag.append((mid, target, len(csmi), float(lv.max()),
                         float(sims[0]) if sims else 0.0, float(p[order[0]])))
    if not smis: smis = ['CCO']
    rows.append((mid, ';'.join(smis[:CFG.TOPN])))
    if gi % 50 == 0: print(f'  {gi}/{len(mols)}  {time.time()-T0:.0f}s', flush=True)

submission = pd.DataFrame(rows, columns=['molecule_id', 'smiles'])
samp = pd.read_csv(SAMPLE)
submission = samp[['molecule_id']].merge(submission, on='molecule_id', how='left')
submission['smiles'] = submission['smiles'].fillna('CCO')

assert len(submission) == len(samp)
assert submission.molecule_id.duplicated().sum() == 0
assert submission.smiles.isnull().sum() == 0
assert submission.smiles.str.split(';').map(len).max() <= 25
submission.to_csv('submission.csv', index=False)
print(f'\nwrote submission.csv  {submission.shape}   total {time.time()-T0:.0f}s')
submission.head()

#---CELL---

# ===================================================================================
#  Diagnostics — what the engine actually saw
# ===================================================================================
import matplotlib.pyplot as plt
d = pd.DataFrame(diag, columns=['molecule_id','neutral_mass','n_candidates',
                                'best_library_sim','best_analog_sim','top_prob'])
print(d[['n_candidates','best_library_sim','best_analog_sim','top_prob']].describe().round(3).to_string())

fig, ax = plt.subplots(1, 4, figsize=(18, 3.6))
ax[0].hist(d.n_candidates, bins=40, color='#4C72B0'); ax[0].set_title('candidates per molecule'); ax[0].set_xlabel('n')
ax[1].hist(d.best_library_sim, bins=40, color='#DD8452'); ax[1].set_title('best library similarity'); ax[1].set_xlabel('entropy sim')
ax[2].hist(d.best_analog_sim, bins=40, color='#55A868'); ax[2].set_title('best analog similarity'); ax[2].set_xlabel('entropy sim (mass-shifted)')
ax[3].scatter(d.best_library_sim, d.best_analog_sim, s=8, alpha=.5, color='#C44E52')
ax[3].set_xlabel('library sim'); ax[3].set_ylabel('analog sim'); ax[3].set_title('the two evidence channels')
for a in ax: a.spines[['top','right']].set_visible(False)
plt.tight_layout(); plt.show()

# molecules where the library is confident are likely Class 1; the rest lean on analogs
likely_c1 = (d.best_library_sim > 0.85).mean()
print(f'\nmolecules with a confident library hit (sim > 0.85): {likely_c1:.1%}'
      f'  -> the other {1-likely_c1:.1%} are carried by analog propagation')

#---CELL---
# Training script - NOT executed here (needs a GPU). Copy into a separate notebook.
# Saved to disk so you can fork this notebook and run it directly.
open("train_fingerprint_model.py","w").write(TRAIN_SCRIPT_SRC)
print("wrote train_fingerprint_model.py", len(TRAIN_SCRIPT_SRC), "bytes")
