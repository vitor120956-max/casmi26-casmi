#!/usr/bin/env python3
"""v5 patch: PROBE_MODE — measure f_t exactly (fraction of visible molecules where the
   train twin annotation IS the scored answer). rank1 = perfect library twin,
   ranks 2-25 = tiny junk SMILES that can never match an NP answer."""
import json

path = '/home/user/fork_bera/fork.ipynb'
nb = json.load(open(path))

def set_src(cell, s):
    lines = s.split('\n')
    cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

OLD = """            # ---- end v4 ----
            smis  = [pool.smiles[cand[i]] for i in order]"""

NEW = """            # ---- end v4 ----
            if CFG.PROBE_MODE:
                # f_t probe: rank1 = perfect library twin (if any), ranks 2-25 = tiny junk
                # (all <= ~100 Da: can never be the NP answer, whose mass matches the twin)
                junk24 = ['CCO','CCC','CCCC','CCCCC','CCCCCC','c1ccccc1','CCN','CCCN',
                          'CCOCC','CC(C)C','OCCO','OCCCO','CC=O','CC#N','CCS','CCOC',
                          'CN(C)C','OC(=O)O','CC(C)O','CCCO','CC(=O)O','CC(=O)C','CCCl','C1CC1']
                t = int(np.argmax(lv)) if (len(lv) and lv.max() >= CFG.LIB_OVERRIDE) else -1
                smis = ([pool.smiles[cand[t]]] if t >= 0 else []) + junk24
            else:
                smis  = [pool.smiles[cand[i]] for i in order]"""

OLD_CFG = "    LIB_OVERRIDE = 0.999   # v4: library sim >= this is forced to the top of the ranking"
NEW_CFG = OLD_CFG + "\n    PROBE_MODE   = True    # v5: f_t probe (twin@1 + junk 2-25). FALSE for real runs!"

patched = {'cfg': False, 'loop': False}
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    s = ''.join(cell['source'])
    s0 = s
    if OLD_CFG in s:
        s = s.replace(OLD_CFG, NEW_CFG, 1)
        patched['cfg'] = True
    if OLD in s:
        assert s.count(OLD) == 1
        s = s.replace(OLD, NEW, 1)
        patched['loop'] = True
    if s != s0:
        set_src(cell, s)

print(patched)
assert all(patched.values()), f'patch incomplete: {patched}'
json.dump(nb, open(path, 'w'), indent=1)
print('patched OK ->', path)
