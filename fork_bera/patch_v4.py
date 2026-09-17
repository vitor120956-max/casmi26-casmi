#!/usr/bin/env python3
"""v4 patch: high-confidence library override (sim >= 0.999 -> top of ranking)
   + diagnostics showing where the perfect library hit sat BEFORE the override."""
import json

path = '/home/user/fork_bera/fork.ipynb'
nb = json.load(open(path))

def set_src(cell, s):
    lines = s.split('\n')
    cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

OLD_LOOP = """            p   = RANKER.predict_proba(X)[:, 1]
            order = np.argsort(-p)[:CFG.TOPN]
            smis  = [pool.smiles[cand[i]] for i in order]"""

NEW_LOOP = """            p   = RANKER.predict_proba(X)[:, 1]
            order = np.argsort(-p)[:CFG.TOPN]
            # ---- v4: high-confidence library override + ranking diagnostics ----
            n_perfect = int((lv >= CFG.LIB_OVERRIDE).sum())
            b_idx = int(np.argmax(lv)) if len(lv) else -1
            if b_idx >= 0 and len(order):
                in_top = np.where(order == b_idx)[0]
                rob = int(in_top[0]) if len(in_top) else -1
                r1lv = float(lv[order[0]])
            else:
                rob, r1lv = -1, 0.0
            odiag.append((mid, float(lv.max()) if len(lv) else 0.0, n_perfect, rob, r1lv))
            if n_perfect:
                perf = np.where(lv >= CFG.LIB_OVERRIDE)[0]
                perf = perf[np.argsort(-p[perf], kind='stable')]
                pset = set(perf.tolist())
                rest = np.array([i for i in order if i not in pset], dtype=order.dtype)
                order = np.concatenate([perf, rest])[:CFG.TOPN]
            # ---- end v4 ----
            smis  = [pool.smiles[cand[i]] for i in order]"""

OLD_CFG = "    N_ANALOG     = 100     # analogs kept per molecule; saturates here (40 -> 0.515)"
NEW_CFG = OLD_CFG + "\n    LIB_OVERRIDE = 0.999   # v4: library sim >= this is forced to the top of the ranking"

PRINT_BLOCK = """

# ---- v4 override diagnostics ----
od = pd.DataFrame(odiag, columns=['molecule_id','lv_max','n_perfect','rank_of_best_lv','rank1_lv'])
print('=== v4 OVERRIDE DIAGNOSTICS (ranker order BEFORE override) ===')
print(od[['lv_max','n_perfect','rank_of_best_lv','rank1_lv']].describe().round(3).to_string())
print()
print('rank_of_best_lv counts (where the best library hit sat in ranker top-25; -1 = absent):')
print(od.rank_of_best_lv.value_counts().sort_index().head(20).to_string())
print()
print('n_perfect counts (candidates with lv >= LIB_OVERRIDE):')
print(od.n_perfect.value_counts().sort_index().head(20).to_string())
print()
print('rank1 already a perfect hit: %.1f%%' % (100.0*(od.rank1_lv >= 0.999).mean()))
print('override active (n_perfect>0):    %.1f%%' % (100.0*(od.n_perfect > 0).mean()))
print('override changed the top:        %.1f%%' % (100.0*((od.n_perfect > 0) & (od.rank_of_best_lv != 0)).mean()))
"""

patched = {'cfg': False, 'init': False, 'loop': False, 'print': False}
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    s = ''.join(cell['source'])
    s0 = s
    if 'class CFG' in s and OLD_CFG in s:
        s = s.replace(OLD_CFG, NEW_CFG, 1)
        patched['cfg'] = True
    if 'rows, diag = [], []' in s:
        s = s.replace('rows, diag = [], []', 'rows, diag, odiag = [], [], []', 1)
        patched['init'] = True
    if OLD_LOOP in s:
        assert s.count(OLD_LOOP) == 1
        s = s.replace(OLD_LOOP, NEW_LOOP, 1)
        patched['loop'] = True
    if 'carried by analog propagation' in s:
        s = s.rstrip('\n') + '\n' + PRINT_BLOCK
        patched['print'] = True
    if s != s0:
        set_src(cell, s)

print(patched)
assert all(patched.values()), f'patch incomplete: {patched}'
json.dump(nb, open(path, 'w'), indent=1)
print('patched OK ->', path)
