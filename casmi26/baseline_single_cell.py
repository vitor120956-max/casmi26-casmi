# CASMI 2026 tier-1 baseline - SINGLE-BLOCK VERSION
# Identical logic to baseline_retrieval.ipynb, concatenated so it can be
# pasted into ONE Kaggle notebook cell (handy on mobile).
# Requires: competition dataset attached as input. Writes submission.csv.

import os, re
import numpy as np
import pandas as pd
import scipy.sparse as sp

import glob
_CAND = ['/kaggle/input/enveda-CASMI2026-molecule-id-mass-spectra',
         '/kaggle/input/enveda-casmi2026-molecule-id-mass-spectra']
INPUT = next((p for p in _CAND if os.path.exists(os.path.join(p, 'train.parquet'))), None)
if INPUT is None:
    _hits = [os.path.join(r, f) for r, _d, fs in os.walk('/kaggle/input')
             for f in fs if f == 'train.parquet']
    INPUT = os.path.dirname(_hits[0]) if _hits else os.environ.get('CASMI_INPUT', '.')
if not os.path.exists(os.path.join(INPUT, 'train.parquet')):
    print('WARNING: train.parquet not found under INPUT =', INPUT)
    if os.path.isdir('/kaggle/input'):
        print('--- tree of /kaggle/input ---')
        for root, dirs, files in os.walk('/kaggle/input'):
            depth = root.replace('/kaggle/input', '').count(os.sep)
            if depth <= 4:
                print('  ' * depth + os.path.basename(root) + '/' + (f'  {files[:8]}' if files else ''))
        print('--- end tree ---')
    else:
        print('(no /kaggle/input dir)')
else:
    print('INPUT =', INPUT)

# ---------------- config ----------------
BIN_DA      = 0.02    # m/z bin width (Da) for cosine vectors
INT_FLOOR   = 0.01    # drop peaks below 1% of base peak
TOP_N_PEAKS = 128     # keep at most this many peaks per spectrum
MAX_MZ      = 2000.0  # safety cap on binned m/z range
PPM_TOL     = 25.0    # neutral-mass tolerance for candidate filtering
TOPK_MATCH  = 100     # train spectra retrieved per query spectrum
HIT_BONUS   = 0.02    # additive bonus per repeat hit of the same structure
MAX_GUESSES = 25

# Libraries used for the retrieval index. enveda-180 is excluded by default:
# instrument-matched but drug-like chemistry (different region of space).
INDEX_LIBS = ['enveda-np-examples', 'gnps', 'mona', 'massbank', 'riken',
              'spectraverse', 'msdial', 'masaryk', 'pluskal_ms2']

ADDUCT_MASS = {   # ion mass = neutral mono mass + offset
    '[M+H]+': 1.00728, '[M+NH4]+': 18.03383, '[M-H2O+H]+': -17.00328,
    '[M-2H2O+H]+': -35.01385, '[M+Na]+': 22.98922, '[M+K]+': 38.96316,
    '[M-H]-': -1.00728, '[M-H2O-H]-': -19.01784,
    '[M+CH2O2-H]-': 44.99820, '[M+Cl]-': 34.96940,
}

MONO = {'H':1.00783,'C':12.0,'N':14.00307,'O':15.99491,'P':30.97376,'S':31.97207,
        'F':18.99840,'Cl':34.96885,'Br':78.91834,'I':126.90447,'Na':22.98977,
        'K':38.96371,'Ca':39.96259,'Mg':23.98504,'Zn':63.92915,'Fe':55.93494,
        'B':11.00931,'Si':27.97693,'Se':79.91652,'As':74.92159,'Cu':62.92959,
        'Mn':54.93804,'Co':58.93319,'Ni':57.93534,'Li':7.01600,'Al':26.98154,
        'Sb':120.90381,'Ba':137.90525,'Sr':87.90561,'Ag':106.90509,'Cd':113.90336,
        'Pb':207.97665,'Sn':119.90220,'Ti':47.94794,'V':50.94396,'Cr':51.94051,
        'Mo':97.90541,'W':183.95093,'Hg':201.97061,'Au':196.96657,'Pt':194.96479,
        'Pd':105.90348,'La':138.90635,'Ce':139.90544,'Rb':84.91179,'Cs':132.90545,
        'Be':9.01218,'Ge':73.92118,'Ga':68.92558,'In':114.90388,'Tl':204.97443,
        'Zr':91.90504,'Hf':179.94655,'Nb':92.90638,'Ta':180.94799,'Bi':208.98040,
        'Te':129.90622,'Ru':100.90558,'Rh':102.90550,'Ir':192.96292,'Os':191.96148}
_ELEM = re.compile(r'([A-Z][a-z]?)(\d*)')
_PAREN = re.compile(r'\(([^()]+)\)(\d*)')

def _expand_formula(f):
    prev = None
    while prev != f:
        prev = f
        f = _PAREN.sub(lambda m: m.group(1) * int(m.group(2) or 1), f)
    return f

_BAD_FORMULAS = set()

def formula_mass(formula):
    total = 0.0
    for seg in _expand_formula(str(formula)).split('.'):
        seg = seg.strip()
        if not seg:
            continue
        coef = 1
        m = re.match(r'^(\d+)', seg)
        if m:
            coef, seg = int(m.group(1)), seg[m.end():]
        for el, n in _ELEM.findall(seg):
            if el not in MONO:
                _BAD_FORMULAS.add(str(formula))
                return float('nan')
            total += coef * int(n or 1) * MONO[el]
    return total

def neutral_mass(precursor_mz, adduct):
    return precursor_mz - ADDUCT_MASS.get(adduct, 0.0)

NCOLS = int(MAX_MZ / BIN_DA) + 2

def curate(mzs, ints, precursor_mz):
    mzs = np.asarray(mzs, dtype=float); ints = np.asarray(ints, dtype=float)
    if mzs.size == 0:
        return mzs, ints
    keep = (mzs <= precursor_mz + 2.0) & (mzs >= 0) & (ints >= INT_FLOOR * ints.max())
    mzs, ints = mzs[keep], ints[keep]
    if mzs.size > TOP_N_PEAKS:
        idx = np.argsort(ints)[::-1][:TOP_N_PEAKS]
        mzs, ints = mzs[idx], ints[idx]
    ints = np.sqrt(ints)
    n = np.linalg.norm(ints)
    if n > 0:
        ints = ints / n
    return mzs, ints

def bin_cols(mzs):
    return np.clip(np.round(mzs / BIN_DA).astype(np.int64), 0, NCOLS - 1)

def row_vector(mzs, ints):
    return sp.csr_matrix((ints, (np.zeros(mzs.size, dtype=np.int64), bin_cols(mzs))),
                         shape=(1, NCOLS), dtype=np.float32)

import pyarrow.parquet as pq

_NEED = ['ingest_lib', 'molecular_formula', 'inchikey14', 'normalized_smiles',
         'ms2_mzs', 'ms2_normalized_intensities', 'precursor_mz']
pf = pq.ParquetFile(os.path.join(INPUT, 'train.parquet'))
pieces, IK_l, SMI_l, NM_l = [], [], [], []
for batch in pf.iter_batches(batch_size=250_000, columns=_NEED):
    df = batch.to_pandas()
    df = df[df.ingest_lib.isin(INDEX_LIBS)]
    if len(df) == 0:
        continue
    NM_l.append(df.molecular_formula.map(formula_mass).to_numpy(dtype=np.float64))
    IK_l.append(df.inchikey14.to_numpy())
    SMI_l.append(df.normalized_smiles.to_numpy())
    rr, cc, vv = [], [], []
    for i, (mzs, ints, pmz) in enumerate(zip(df.ms2_mzs, df.ms2_normalized_intensities,
                                             df.precursor_mz)):
        mzs, ints = curate(mzs, ints, pmz)
        if mzs.size == 0:
            continue
        rr.append(np.full(mzs.size, i, dtype=np.int32))
        cc.append(bin_cols(mzs).astype(np.int32))
        vv.append(ints.astype(np.float32))
    if rr:
        pieces.append(sp.csr_matrix((np.concatenate(vv), (np.concatenate(rr), np.concatenate(cc))),
                                    shape=(len(df), NCOLS), dtype=np.float32))
    del df, rr, cc, vv

X = sp.vstack(pieces, format='csr') if pieces else sp.csr_matrix((0, NCOLS), dtype=np.float32)
del pieces
IK    = np.concatenate(IK_l)
SMI   = np.concatenate(SMI_l)
NMASS = np.concatenate(NM_l)
if _BAD_FORMULAS:
    print('WARN unparsable formulas (excluded from mass filter):', sorted(_BAD_FORMULAS)[:5], 'total:', len(_BAD_FORMULAS))
print('index spectra:', X.shape[0], ' unique structures:', len(set(IK.tolist())))
print('index matrix:', X.shape, 'nnz:', X.nnz)

test = pd.read_parquet(os.path.join(INPUT, 'test.parquet'))
print('test spectra:', len(test), ' molecules:', test.molecule_id.nunique())

results = {}
for mid, grp in test.groupby('molecule_id', sort=False):
    m_est = np.median([neutral_mass(p, a) for p, a in zip(grp.precursor_mz, grp.adduct)])
    ok = np.where(np.abs(NMASS - m_est) <= m_est * PPM_TOL * 1e-6)[0]
    best = {}   # inchikey14 -> [score, smiles, hits]
    if ok.size:
        Xsub = X[ok]
        for mzs, ints, pmz in zip(grp.ms2_mzs, grp.ms2_normalized_intensities, grp.precursor_mz):
            mzs, ints = curate(mzs, ints, pmz)
            if mzs.size == 0:
                continue
            cos = (Xsub @ row_vector(mzs, ints).T).toarray().ravel().astype(np.float64)
            order = np.argsort(cos)[::-1][:TOPK_MATCH]
            for t in order:
                c = float(cos[t])
                if c <= 0.0:
                    break
                ik = IK[ok[t]]
                cur = best.get(ik)
                if cur is None:
                    best[ik] = [c, SMI[ok[t]], 1]
                else:
                    cur[2] += 1
                    if c > cur[0]:
                        cur[0], cur[1] = c, SMI[ok[t]]
    ranked = sorted(best.values(), key=lambda r: -(r[0] + HIT_BONUS * (r[2] - 1)))
    results[mid] = [smi for _, smi, _ in ranked[:MAX_GUESSES]]

n_with = sum(1 for v in results.values() if v)
print('molecules with >=1 candidate:', n_with, '/', len(results))

out = pd.DataFrame(
    [(mid, ';'.join(results.get(mid, []) or ['CCO'])) for mid in test.molecule_id.unique()],
    columns=['molecule_id', 'smiles'])
out.to_csv('submission.csv', index=False)
print(out.head(3).to_string())

# inline format checks (same rules as casmi26/validate_submission.py)
assert list(out.columns) == ['molecule_id', 'smiles']
assert out.notna().all().all() and (out.smiles.str.len() > 0).all()
assert out.molecule_id.is_unique and len(out) == test.molecule_id.nunique()
assert (out.smiles.str.count(';') + 1 <= MAX_GUESSES).all()
print('submission.csv written:', out.shape)
