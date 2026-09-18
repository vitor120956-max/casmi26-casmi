#!/usr/bin/env python3
"""v8/v9 patch: PROBE infrastructure.
   PROBE='B' -> rank1 = original ranker #2, ranks 2-25 = junk  (measures p_2)
   PROBE='C' -> ranks 1-23 = original ranker ranks 3-25        (measures tail)
   PROBE=''  -> normal run (demote logic available, DEMOTE_TWIN=False now)
   Version marker in log: probe runs print 'demoted twins (v6): 0/400'."""
import json, sys

mode = sys.argv[1] if len(sys.argv) > 1 else 'B'
assert mode in ('B', 'C')

path = '/home/user/fork_bera/fork.ipynb'
nb = json.load(open(path))

def set_src(cell, s):
    lines = s.split('\n')
    cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

OLD_CFG = "    DEMOTE_TWIN  = True    # v6: perfect library hit (lv>=LIB_OVERRIDE) demoted to last rank"
NEW_CFG = ("    DEMOTE_TWIN  = False   # v6 result: demotion ties twin@1 (0.324) -> keep twin@1 lineage\n"
           f"    PROBE        = '{mode}'     # ''=off | 'B'=ranker#2@1+junk (p_2) | 'C'=ranks3-25 promoted (tail)")

OLD_ELSE = """            else:
                if CFG.DEMOTE_TWIN and len(lv) and lv.max() >= CFG.LIB_OVERRIDE:
                    t = int(np.argmax(lv))
                    oset = set(order.tolist())
                    if t in oset:
                        front = [i for i in order.tolist() if i != t]
                        order = np.array(front + [t], dtype=order.dtype)[:CFG.TOPN]
                        demoted_n += 1
                smis  = [pool.smiles[cand[i]] for i in order]"""

NEW_ELSE = """            else:
                if CFG.PROBE in ('B', 'C'):
                    o_orig = np.argsort(-p)[:CFG.TOPN]   # pristine ranker order (pre-override)
                    if CFG.PROBE == 'B':
                        junk24 = ['CCO','CCC','CCCC','CCCCC','CCCCCC','c1ccccc1','CCN','CCCN',
                                  'CCOCC','CC(C)C','OCCO','OCCCO','CC=O','CC#N','CCS','CCOC',
                                  'CN(C)C','OC(=O)O','CC(C)O','CCCO','CC(=O)O','CC(=O)C','CCCl','C1CC1']
                        second = [pool.smiles[cand[o_orig[1]]]] if len(o_orig) > 1 else []
                        smis = second + junk24
                    else:
                        smis = [pool.smiles[cand[i]] for i in o_orig[2:]]
                else:
                    if CFG.DEMOTE_TWIN and len(lv) and lv.max() >= CFG.LIB_OVERRIDE:
                        t = int(np.argmax(lv))
                        oset = set(order.tolist())
                        if t in oset:
                            front = [i for i in order.tolist() if i != t]
                            order = np.array(front + [t], dtype=order.dtype)[:CFG.TOPN]
                            demoted_n += 1
                    smis  = [pool.smiles[cand[i]] for i in order]"""

patched = {'cfg': False, 'else': False}
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
    if s != s0:
        set_src(cell, s)

print(patched)
assert all(patched.values()), f'patch incomplete: {patched}'
json.dump(nb, open(path, 'w'), indent=1)
print(f'patched OK (PROBE={mode}) ->', path)
