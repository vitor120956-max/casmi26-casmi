#!/usr/bin/env python3
"""v6 patch: DEMOTE_TWIN — perfect library twin moved to rank 25 (insurance),
   ranks 1-24 = ranker order without the twin. Tests the f_t=0 hypothesis from
   the v5 probe (probe scored 0.000 => train annotation NEVER the answer).
   Also flips PROBE_MODE back to False."""
import json

path = '/home/user/fork_bera/fork.ipynb'
nb = json.load(open(path))

def set_src(cell, s):
    lines = s.split('\n')
    cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

OLD_CFG = "    PROBE_MODE   = True    # v5: f_t probe (twin@1 + junk 2-25). FALSE for real runs!"
NEW_CFG = ("    PROBE_MODE   = False   # v5: f_t probe (twin@1 + junk 2-25). FALSE for real runs!\n"
           "    DEMOTE_TWIN  = True    # v6: perfect library hit (lv>=LIB_OVERRIDE) demoted to last rank")

OLD_ELSE = """            else:
                smis  = [pool.smiles[cand[i]] for i in order]"""
NEW_ELSE = """            else:
                if CFG.DEMOTE_TWIN and len(lv) and lv.max() >= CFG.LIB_OVERRIDE:
                    t = int(np.argmax(lv))
                    oset = set(order.tolist())
                    if t in oset:
                        front = [i for i in order.tolist() if i != t]
                        order = np.array(front + [t], dtype=order.dtype)[:CFG.TOPN]
                        demoted_n += 1
                smis  = [pool.smiles[cand[i]] for i in order]"""

OLD_INIT = "rows, diag, odiag = [], [], []"
NEW_INIT = "rows, diag, odiag, demoted_n = [], [], [], 0"

OLD_SUB = "submission = pd.DataFrame(rows, columns=['molecule_id', 'smiles'])"
NEW_SUB = "print(f'demoted twins (v6): {demoted_n}/{len(mols)}', flush=True)\n" + OLD_SUB

patched = {'cfg': False, 'else': False, 'init': False, 'print': False}
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    s = ''.join(cell['source'])
    s0 = s
    if OLD_CFG in s:
        s = s.replace(OLD_CFG, NEW_CFG, 1); patched['cfg'] = True
    if OLD_ELSE in s:
        assert s.count(OLD_ELSE) == 1
        s = s.replace(OLD_ELSE, NEW_ELSE, 1); patched['else'] = True
    if OLD_INIT in s:
        s = s.replace(OLD_INIT, NEW_INIT, 1); patched['init'] = True
    if OLD_SUB in s:
        assert s.count(OLD_SUB) == 1
        s = s.replace(OLD_SUB, NEW_SUB, 1); patched['print'] = True
    if s != s0:
        set_src(cell, s)

print(patched)
assert all(patched.values()), f'patch incomplete: {patched}'
json.dump(nb, open(path, 'w'), indent=1)
print('patched OK ->', path)
