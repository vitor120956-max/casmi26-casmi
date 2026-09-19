#!/usr/bin/env python3
"""FUSION patch para canon.ipynb (linhagem prvsiyan).
Pós-ranker blend: p_final = p_ranker + FUSE_LAM * Tanimoto(candidate, best-library-hit).
Twin NÃO é boostado (tani[t]=0) — preserva o agree-gating canônico no rank 1;
a fusão age apenas na ORDENAÇÃO DA CAUDA (ranks 2-25).
Evidência: v12 (cauda só-tani) = 0.324 = v3 (cauda só-ranker), conjuntos 90% diferentes
=> blend dos dois sinais tem espaço. NÃO EXECUTAR antes do score canônico decidir a linhagem.
Hook de verificação no log: 'FUSE-tani blend:'
"""
import json, re, sys

path = sys.argv[1] if len(sys.argv) > 1 else '/home/user/prvsiyan_fork/canon.ipynb'
nb = json.load(open(path))

def set_src(cell, s):
    lines = s.split('\n')
    cell['source'] = [l + '\n' for l in lines[:-1]] + ([lines[-1]] if lines[-1] else [])

CFG_ANCHOR = re.compile(r"(^|\n)(\s*)TOPN\s*=\s*25[^\n]*")
CFG_ADD = ("{nl}{ind}FUSE_TANI    = True   # v2: cauda = p_ranker + LAM*Tanimoto-ao-melhor-hit-de-lib (twin nao boostado)\n"
           "{ind}FUSE_LAM     = 0.25\n"
           "{ind}FUSE_MIN_LV  = 0.999")

LOOP_ANCHOR = re.compile(r"(\n(?P<ind>[ \t]+))p\s*=\s*rank_proba\(X\)(\n[ \t]+)order\s*=\s*np\.argsort\(-p\)\[:CFG\.TOPN\]")
def loop_repl(m):
    ind = m.group('ind')
    return (f"\n{ind}p   = rank_proba(X)\n"
            f"{ind}if CFG.FUSE_TANI and len(lv) and lv.max() >= CFG.FUSE_MIN_LV:\n"
            f"{ind}    t = int(np.argmax(lv))\n"
            f"{ind}    cb = cfp.astype(bool); tb = cb[t]\n"
            f"{ind}    inter = np.logical_and(cb, tb).sum(1); union = np.logical_or(cb, tb).sum(1)\n"
            f"{ind}    tani = np.where(union > 0, inter / np.maximum(union, 1), 0.0).astype(np.float32)\n"
            f"{ind}    tani[t] = 0.0  # rank-1 fica com o gating canonico; fusao so reordena a cauda\n"
            f"{ind}    p = p + CFG.FUSE_LAM * tani\n"
            f"{ind}    fuse_n += 1\n"
            f"{ind}    srt = np.sort(tani)[::-1]\n"
            f"{ind}    fuse_t2.append(float(srt[0]) if len(srt) else 0.0)\n"
            f"{ind}order = np.argsort(-p)[:CFG.TOPN]")

INIT_ANCHOR = re.compile(r"rows, diag = \[\], \[\]")
INIT_NEW = "rows, diag, fuse_n, fuse_t2 = [], [], 0, []"

PRINT_ANCHOR = re.compile(r"(\n(?P<ind>[ \t]+))submission = pd\.DataFrame\(rows")
def print_repl(m):
    ind = m.group('ind')
    return (f"\n{ind}if fuse_t2:\n"
            f"{ind}    import statistics\n"
            f"{ind}    print(f'FUSE-tani blend: {{fuse_n}}/{{len(mols)}} molecules; lam={{CFG.FUSE_LAM}}; '\n"
            f"{ind}          f'top-tani mean={{statistics.mean(fuse_t2):.3f}} median={{statistics.median(fuse_t2):.3f}}', flush=True)\n"
            f"{ind}submission = pd.DataFrame(rows")

patched = {'cfg': False, 'loop': False, 'init': False, 'print': False}
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    s = ''.join(cell['source']); s0 = s
    m = CFG_ANCHOR.search(s)
    if m and 'class CFG' in s or (m and 'PPM_WIN' in s):
        nl = '' if m.group(1) == '\n' else ''
        ind = m.group(2) or '    '
        s = CFG_ANCHOR.sub(lambda mm: mm.group(0) + CFG_ADD.format(nl='\n', ind=(mm.group(2) or '    ')), s, count=1)
        patched['cfg'] = True
    if LOOP_ANCHOR.search(s):
        s = LOOP_ANCHOR.sub(loop_repl, s, count=1); patched['loop'] = True
    if INIT_ANCHOR.search(s):
        s = INIT_ANCHOR.sub(INIT_NEW, s, count=1); patched['init'] = True
    if PRINT_ANCHOR.search(s):
        s = PRINT_ANCHOR.sub(print_repl, s, count=1); patched['print'] = True
    if s != s0:
        set_src(cell, s)

print(patched)
assert all(patched.values()), f'incompleto: {patched}'
json.dump(nb, open(path, 'w'), indent=1)
json.load(open(path))  # re-parse sanity
print('FUSE patch OK ->', path)
