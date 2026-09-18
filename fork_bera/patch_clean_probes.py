#!/usr/bin/env python3
"""Clean probes (no junk): add A2 (twin only) and B2 (ranker #2 only) modes."""
import json

path = '/home/user/fork_bera/fork.ipynb'
nb = json.load(open(path))

def set_src(cell, s):
    lines = s.split('\n')
    cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

OLD_CFG = "    PROBE        = 'B'     # ''=off | 'B'=ranker#2@1+junk (p_2) | 'C'=ranks3-25 promoted (tail)"
NEW_CFG = "    PROBE        = 'A2'    # ''=off | 'A2'=twin only | 'B2'=ranker#2 only | 'C'=ranks3-25 (no junk!)"

OLD = """                if CFG.PROBE in ('B', 'C'):
                    o_orig = np.argsort(-p)[:CFG.TOPN]   # pristine ranker order (pre-override)
                    if CFG.PROBE == 'B':"""
NEW = """                if CFG.PROBE in ('A2', 'B2', 'B', 'C'):
                    o_orig = np.argsort(-p)[:CFG.TOPN]   # pristine ranker order (pre-override)
                    if CFG.PROBE == 'A2':
                        smis = [pool.smiles[cand[o_orig[0]]]] if len(o_orig) else []
                    elif CFG.PROBE == 'B2':
                        smis = [pool.smiles[cand[o_orig[1]]]] if len(o_orig) > 1 else []
                    elif CFG.PROBE == 'B':"""

patched = {'cfg': False, 'branch': False}
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    s = ''.join(cell['source'])
    s0 = s
    if OLD_CFG in s:
        s = s.replace(OLD_CFG, NEW_CFG, 1); patched['cfg'] = True
    if OLD in s:
        assert s.count(OLD) == 1
        s = s.replace(OLD, NEW, 1); patched['branch'] = True
    if s != s0:
        set_src(cell, s)

print(patched)
assert all(patched.values()), f'incomplete: {patched}'
json.dump(nb, open(path, 'w'), indent=1)
print('patched OK (clean probes A2/B2/C) ->', path)
