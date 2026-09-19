#!/usr/bin/env python3
"""v12 patch (fixed): TWIN_SIM_RERANK — twin locked at rank 1; ranks 2-25 = window
candidates by Tanimoto fp similarity TO THE TWIN (tie-break: ranker prob).
CFG replacement is regex-based (set_probe.py mangled the exact spacing)."""
import json, re

path = '/home/user/fork_bera/fork.ipynb'
nb = json.load(open(path))

def set_src(cell, s):
    lines = s.split('\n')
    cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

NEW_CFG_LINE = ("    PROBE        = ''      # ''=off | 'A2'=twin only | 'B2'=ranker#2 only | 'C'=ranks3-25\n"
                "    TWIN_SIM_RERANK = True # v12: ranks 2-25 = Tanimoto-to-twin order (tie: ranker p)")

OLD = """            p   = RANKER.predict_proba(X)[:, 1]
            order = np.argsort(-p)[:CFG.TOPN]"""
NEW = """            p   = RANKER.predict_proba(X)[:, 1]
            if CFG.TWIN_SIM_RERANK and len(lv) and lv.max() >= CFG.LIB_OVERRIDE:
                t = int(np.argmax(lv))                       # the perfect twin
                tb = cfp[t].astype(bool)
                cb = cfp.astype(bool)
                inter = np.logical_and(cb, tb).sum(1)
                union = np.logical_or(cb, tb).sum(1)
                tani = np.where(union > 0, inter / np.maximum(union, 1), 0.0).astype(np.float32)
                score = tani + 1e-6 * p                      # tie-break by ranker prob
                score[t] = -1.0                              # twin goes to rank 1 separately
                rest = np.argsort(-score)[:CFG.TOPN - 1]
                order = np.concatenate([[t], rest]).astype(rest.dtype)
                tani_top.append(float(tani[rest[0]]))
            else:
                order = np.argsort(-p)[:CFG.TOPN]"""

OLD_INIT = "rows, diag, odiag, demoted_n = [], [], [], 0"
NEW_INIT = "rows, diag, odiag, demoted_n, tani_top = [], [], [], 0, []"

OLD_SUB = "print(f'demoted twins (v6): {demoted_n}/{len(mols)}', flush=True)"
NEW_SUB = (OLD_SUB + "\n"
           "if tani_top:\n"
           "    import statistics\n"
           "    print(f'v12 twin-sim rerank: {len(tani_top)}/{len(mols)} molecules; '\n"
           "          f'top-tani mean={statistics.mean(tani_top):.3f} median={statistics.median(tani_top):.3f} '\n"
           "          f'min={min(tani_top):.3f} max={max(tani_top):.3f}', flush=True)")

patched = {'cfg': False, 'loop': False, 'init': False, 'print': False}
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    s = ''.join(cell['source'])
    s0 = s
    if 'class CFG' in s and re.search(r"    PROBE        = '\w+'", s):
        s = re.sub(r"    PROBE        = '\w+'[^\n]*", NEW_CFG_LINE, s, count=1)
        patched['cfg'] = True
    if OLD in s:
        assert s.count(OLD) == 1
        s = s.replace(OLD, NEW, 1); patched['loop'] = True
    if OLD_INIT in s:
        s = s.replace(OLD_INIT, NEW_INIT, 1); patched['init'] = True
    if OLD_SUB in s:
        s = s.replace(OLD_SUB, NEW_SUB, 1); patched['print'] = True
    if s != s0:
        set_src(cell, s)

print(patched)
assert all(patched.values()), f'incomplete: {patched}'
json.dump(nb, open(path, 'w'), indent=1)
print('patched OK (v12 twin-sim rerank) ->', path)
