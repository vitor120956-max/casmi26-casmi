BUILD_REVISION = 'a14bd9460375db73f93d9e609c63d33754d1db2c'
NOTEBOOK_CODE_SHA = 'ed7e8b8b1b759462bd6f31277ad210febddb72dc76d10c9bcfe22ee49507ec6c'

#---CELL---
import glob
import math
import os
import pickle
import subprocess
import sys
import time
from multiprocessing import Pool as MPool
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pyarrow as pa
import pyarrow.parquet as pq
import torch
import torch.nn as nn
import torch.nn.functional as F
from IPython.display import HTML, display
from numba import njit, prange
from sklearn.ensemble import HistGradientBoostingClassifier

NAVY, TEAL, GOLD, CORAL, PAPER = "#0B1F3A", "#00B4A6", "#F4C95D", "#E85D4C", "#F6F1E7"
STYLE = dict(paper_bgcolor=PAPER, plot_bgcolor=PAPER,
             font=dict(color="#1C1917", size=13), height=420,
             margin=dict(l=55, r=25, t=60, b=50))

#---CELL---
K, PPM_WIN, PPM_FALLBACK = 25, 8.5, 30.0
INT_FLOOR, MAX_PEAKS, MZ_TOL, INT_POWER = 0.002, 256, 0.01, 1.0
ANALOG_WIN, N_ANALOG, SIM_POWER = 200.0, 100, 4.0
CLASS1_TAU, FRAG_W, TOP_KEEP = 0.60, 0.35, 0
USE_BIO, USE_COLLECTION = True, False
W1_PRIORS, SEEDS = (0.30, 0.60), (0, 1, 2, 3)
GBM = dict(max_depth=6, max_iter=500, learning_rate=0.03,
           min_samples_leaf=80, l2_regularization=1.0)
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
np.random.seed(42)
print("device", DEVICE)

#---CELL---
def show_table(frame: pd.DataFrame, decimals: int = 3) -> None:
    styled = frame.style.format(precision=decimals).hide(axis="index")
    styled = styled.set_table_styles([
        {"selector": "th", "props": [("background", NAVY), ("color", PAPER), ("padding", "10px")]},
        {"selector": "td", "props": [("padding", "9px"), ("border-bottom", "1px solid #ddd")]},
        {"selector": "table", "props": [("width", "100%"), ("background", PAPER)]},
    ])
    display(HTML(styled.to_html()))


def fig_layout(fig: go.Figure, title: str) -> go.Figure:
    fig.update_layout(title=title, **STYLE)
    fig.update_xaxes(showgrid=True, gridcolor="#E7E0D4")
    fig.update_yaxes(showgrid=True, gridcolor="#E7E0D4")
    return fig

#---CELL---
log = pd.DataFrame([
    ("Host de novo GPU", 0.000, "gpu"),
    ("Our CH2/O analog", 0.142, "ours"),
    ("Our 3 h Spec2FP CNN", 0.174, "ours"),
    ("Public-13 shift blend", 0.235, "ours"),
    ("Public-10 no ChEBI", 0.315, "ours"),
    ("Public-09 stuffed lv", 0.328, "ours"),
    ("Public-12 / 14 tautomer", 0.333, "ours"),
    ("Two Rankers (reported)", 0.337, "data"),
    ("Quad-Channel (reported)", 0.339, "data"),
], columns=["method", "public_mrr", "lane"])
colors = {"gpu": CORAL, "ours": TEAL, "data": GOLD}
fig = go.Figure(go.Bar(
    x=log["public_mrr"], y=log["method"], orientation="h",
    marker_color=[colors[l] for l in log["lane"]],
    text=[f"{v:.3f}" for v in log["public_mrr"]], textposition="outside"))
fig = fig_layout(fig, "Tautomer was a wash. Do not replay the 0.235 blend")
fig.update_xaxes(title="Public MRR@25", range=[0, 0.40])
fig.update_yaxes(autorange="reversed")
fig.show()

#---CELL---
def find_file(name: str) -> str:
    roots = ["/kaggle/input", "data", str(Path.home() / "Downloads")]
    hits: list[str] = []
    for root in roots:
        if os.path.isdir(root):
            hits += glob.glob(f"{root}/**/{name}", recursive=True)
    if not hits:
        raise FileNotFoundError(f"Attach the dataset that contains {name}")
    return sorted(hits, key=len)[0]


def attached(name: str) -> list[str]:
    hits = glob.glob(f"/kaggle/input/**/{name}", recursive=True)
    hits += glob.glob(f"data/**/{name}", recursive=True)
    return hits

#---CELL---
whls = glob.glob("/kaggle/input/**/rdkit-*.whl", recursive=True)
if whls:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                    "--no-index", whls[0]], check=False)
try:
    from rdkit import Chem, RDLogger
    from rdkit.Chem import rdFingerprintGenerator, MACCSkeys
    from rdkit.Chem.Descriptors import ExactMolWt
    RDLogger.DisableLog("rdApp.*")
    HAVE_RDKIT = True
except Exception:
    Chem = ExactMolWt = rdFingerprintGenerator = MACCSkeys = None
    HAVE_RDKIT = False
print("rdkit", HAVE_RDKIT, "wheel", bool(whls), "torch", torch.__version__)

#---CELL---
COMP = os.path.dirname(find_file("test.parquet"))
TRAIN, TEST = f"{COMP}/train.parquet", f"{COMP}/test.parquet"
SAMPLE = f"{COMP}/sample_submission.csv"
t0 = time.time()
test = pd.read_parquet(TEST)
sample = pd.read_csv(SAMPLE)
assert list(sample.columns)[:2] == ["molecule_id", "smiles"]
if Path("/kaggle/input").is_dir():
    print("inputs", sorted(os.listdir("/kaggle/input")))
ATTACH = [
    "prvsiyan/casmi26-fp-models-v2",
    "aidensong123/casmi26-offline-rdkit-2026033",
    "prvsiyan/casmi26-ranker-features",
    "prvsiyan/chebi-lipidmaps-casmi26",
    "prvsiyan/coconut-casmi26-candidates",
    "thedevastator/open-source-natural-product-annotations",
]
need = []
if not HAVE_RDKIT:
    need.append("rdkit-*.whl")
for name in ("coco_mass.npy", "coco_fp.npy", "coco_meta.pkl",
             "fp_bits.npy", "rank_train.npz"):
    if not attached(name):
        need.append(name)
if not glob.glob("/kaggle/input/**/fp_*.pt", recursive=True):
    need.append("fp_*.pt")
if need:
    print("Add Input missing files", need)
    print("Attach:", ATTACH)
    raise FileNotFoundError("Add Input missing: " + ", ".join(need))
print("attachments ok", "test mols", test["molecule_id"].nunique())

#---CELL---
@njit(cache=True, fastmath=True)
def _clean(mz, it, floor, topk, power, ent_weight):
    n = len(mz)
    if n == 0:
        return np.empty(0, np.float32), np.empty(0, np.float32), 0.0
    mx = 0.0
    for i in range(n):
        if it[i] > mx:
            mx = it[i]
    if mx <= 0:
        return np.empty(0, np.float32), np.empty(0, np.float32), 0.0
    thr, c = floor * mx, 0
    for i in range(n):
        if it[i] >= thr:
            c += 1
    idx = np.empty(c, np.int64)
    j = 0
    for i in range(n):
        if it[i] >= thr:
            idx[j] = i
            j += 1
    if c > topk:
        v = np.empty(c, np.float32)
        for i in range(c):
            v[i] = it[idx[i]]
        o = np.argsort(v)[c - topk:]
        k2 = np.empty(topk, np.int64)
        for i in range(topk):
            k2[i] = idx[o[i]]
        k2.sort()
        idx, c = k2, topk
    om, oi, s = np.empty(c, np.float32), np.empty(c, np.float32), 0.0
    for i in range(c):
        om[i] = mz[idx[i]]; oi[i] = it[idx[i]] ** power; s += oi[i]
    if s > 0:
        for i in range(c):
            oi[i] /= s
    return om, oi, mx

#---CELL---
@njit(cache=True, fastmath=True)
def _ent_apply(oi, ent_weight):
    if not ent_weight:
        return oi
    S, s2 = 0.0, 0.0
    for i in range(len(oi)):
        if oi[i] > 0:
            S -= oi[i] * np.log(oi[i])
    if S >= 3.0:
        return oi
    w = 0.25 + 0.25 * S
    out = np.empty(len(oi), np.float32)
    for i in range(len(oi)):
        out[i] = oi[i] ** w
        s2 += out[i]
    if s2 > 0:
        for i in range(len(out)):
            out[i] /= s2
    return out


@njit(cache=True, fastmath=True)
def clean_peaks(mz, it, floor, topk, power, ent_weight):
    om, oi, _mx = _clean(mz, it, floor, topk, power, ent_weight)
    if len(om) == 0:
        return om, oi
    return om, _ent_apply(oi, ent_weight)

#---CELL---
@njit(cache=True, fastmath=True)
def entropy_sim(qmz, qp, cmz, cp, tol):
    i = j = b = 0
    n, m = len(qmz), len(cmz)
    sa = sb = sab = tot = 0.0
    for x in range(n):
        if qp[x] > 0:
            sa -= qp[x] * np.log(qp[x])
    for x in range(m):
        if cp[x] > 0:
            sb -= cp[x] * np.log(cp[x])
    buf = np.empty(n + m, np.float64)
    while i < n and j < m:
        d = qmz[i] - cmz[j]
        if d < -tol:
            buf[b] = qp[i]; i += 1
        elif d > tol:
            buf[b] = cp[j]; j += 1
        else:
            buf[b] = qp[i] + cp[j]; i += 1; j += 1
        b += 1
    while i < n:
        buf[b] = qp[i]; i += 1; b += 1
    while j < m:
        buf[b] = cp[j]; j += 1; b += 1
    for x in range(b):
        tot += buf[x]
    if tot <= 0:
        return 0.0
    for x in range(b):
        v = buf[x] / tot
        if v > 0:
            sab -= v * np.log(v)
    return 1.0 - (2.0 * sab - sa - sb) / np.log(4.0)

#---CELL---
@njit(cache=True, fastmath=True)
def entropy_sim_shift(qmz, qp, cmz, cp, tol, shift):
    a = entropy_sim(qmz, qp, cmz, cp, tol)
    if -0.001 < shift < 0.001:
        return a
    sm = np.empty(len(cmz), np.float32)
    for i in range(len(cmz)):
        sm[i] = cmz[i] + shift
    b = entropy_sim(qmz, qp, sm, cp, tol)
    return a if a > b else b


@njit(cache=True, fastmath=True, parallel=True)
def search_shift(qmz, qp, cand, off, allmz, allin, tol, floor, topk, power, shift):
    out = np.zeros(len(cand), np.float32)
    for k in prange(len(cand)):
        c = cand[k]
        a, b = off[c], off[c + 1]
        if b <= a:
            continue
        cm, cp = clean_peaks(allmz[a:b], allin[a:b], floor, topk, power, True)
        if len(cm) == 0:
            continue
        out[k] = entropy_sim_shift(qmz, qp, cm, cp, tol, shift[k])
    return out

#---CELL---
MASS = dict(C=12.0, H=1.00782503207, N=14.0030740048, O=15.9949146196,
            Na=22.9897692809, K=38.96370668, Cl=34.96885268)
E = 0.00054857990
PROTON = MASS["H"] - E
H2O = 2 * MASS["H"] + MASS["O"]
NH4 = MASS["N"] + 4 * MASS["H"]
FORMATE = MASS["C"] + 2 * MASS["H"] + 2 * MASS["O"]
ACETATE = 2 * MASS["C"] + 4 * MASS["H"] + 2 * MASS["O"]

#---CELL---
ADDUCTS = {
    "[M+H]+": (1, 1, PROTON), "[M+NH4]+": (1, 1, NH4 - E),
    "[M+Na]+": (1, 1, MASS["Na"] - E), "[M+K]+": (1, 1, MASS["K"] - E),
    "[M-H2O+H]+": (1, 1, PROTON - H2O), "[M-2H2O+H]+": (1, 1, PROTON - 2 * H2O),
    "[M+2H]2+": (1, 2, 2 * PROTON), "[M]+": (1, 1, -E), "[M-H2O]+": (1, 1, -E - H2O),
    "[M+CH3OH+H]+": (1, 1, PROTON + MASS["C"] + 4 * MASS["H"] + MASS["O"]),
    "[M+CH3CN+H]+": (1, 1, PROTON + 2 * MASS["C"] + 3 * MASS["H"] + MASS["N"]),
    "[M-H]-": (1, 1, -PROTON), "[M-H2O-H]-": (1, 1, -PROTON - H2O),
    "[M+CH2O2-H]-": (1, 1, FORMATE - PROTON),
    "[M+C2H4O2-H]-": (1, 1, ACETATE - PROTON),
    "[M+Cl]-": (1, 1, MASS["Cl"] + E), "[M]-": (1, 1, E),
    "[M-2H]-": (1, 2, -2 * PROTON), "[M+Na-2H]-": (1, 1, MASS["Na"] - 2 * PROTON),
    "[2M+H]+": (2, 1, PROTON), "[2M+Na]+": (2, 1, MASS["Na"] - E),
    "[2M+NH4]+": (2, 1, NH4 - E), "[2M+K]+": (2, 1, MASS["K"] - E),
    "[2M-H]-": (2, 1, -PROTON), "[2M+CH2O2-H]-": (2, 1, FORMATE - PROTON),
    "[2M+C2H4O2-H]-": (2, 1, ACETATE - PROTON),
    "[2M+Na-2H]-": (2, 1, MASS["Na"] - 2 * PROTON),
    "[3M+H]+": (3, 1, PROTON), "[3M-H]-": (3, 1, -PROTON),
}


def neutral_mass(mz, adduct) -> np.ndarray:
    out = np.full(len(mz), np.nan)
    ad = np.asarray(adduct, dtype=object)
    for name, (n, z, delta) in ADDUCTS.items():
        mask = ad == name
        if mask.any():
            out[mask] = (mz[mask] * z - delta) / n
    return out

#---CELL---
def load_library(path: str) -> dict:
    t = pq.read_table(path, columns=["inchikey14", "normalized_smiles", "adduct",
                                     "precursor_mz", "ms2_mzs",
                                     "ms2_normalized_intensities"])
    mzc, itc = t.column("ms2_mzs").combine_chunks(), t.column("ms2_normalized_intensities").combine_chunks()
    off = mzc.offsets.to_numpy().astype(np.int64)
    allmz = mzc.values.to_numpy(zero_copy_only=False).astype(np.float32)
    allin = itc.values.to_numpy(zero_copy_only=False).astype(np.float32)
    prec = t.column("precursor_mz").to_numpy(zero_copy_only=False).astype(np.float64)
    add = np.asarray(t.column("adduct").cast(pa.string()).to_pylist(), dtype=object)
    ik = np.asarray(t.column("inchikey14").cast(pa.string()).to_pylist(), dtype=object)
    smi = np.asarray(t.column("normalized_smiles").cast(pa.string()).to_pylist(), dtype=object)
    nm = neutral_mass(prec, add)
    ok = np.isfinite(nm)
    order = np.argsort(np.where(ok, nm, 1e18), kind="mergesort")
    print("library", len(off) - 1, "ok", int(ok.sum()), f"{time.time()-t0:.0f}s")
    return dict(off=off, mz=allmz, it=allin, nm=nm, ik=ik, smi=smi, add=add,
                order=order, snm=nm[order], n_ok=int(ok.sum()))

#---CELL---
def build_rep(L: dict):
    npk = np.diff(L["off"])
    best: dict[str, int] = {}
    for i, k in enumerate(L["ik"]):
        if k and (k not in best or npk[i] > npk[best[k]]):
            best[k] = i
    smi_of = {}
    for i, k in enumerate(L["ik"]):
        if k and k not in smi_of and L["smi"][i]:
            smi_of[k] = L["smi"][i]
    rep = np.array(sorted(best.values()))
    nm, ok = L["nm"][rep], np.isfinite(L["nm"][rep])
    rep, nm, key = rep[ok], nm[ok], L["ik"][rep][ok]
    o = np.argsort(nm)
    print("representatives", len(rep))
    return rep[o], key[o], nm[o], smi_of


L = load_library(TRAIN)
REP, REP_KEY, REP_NM, SMI_OF = build_rep(L)

#---CELL---
vc = pd.Series(L["add"]).value_counts()
tab = pd.DataFrame({
    "adduct": vc.index.astype(str),
    "spectra": vc.values,
    "in_table": [a in ADDUCTS for a in vc.index],
}).head(16)
show_table(tab, decimals=0)
print("adduct types", len(vc), "covered", int(sum(a in ADDUCTS for a in vc.index)),
      "finite mass", L["n_ok"], "/", len(L["add"]))

#---CELL---
def clean_spectrum(mz, it):
    return clean_peaks(np.asarray(mz, np.float32), np.asarray(it, np.float32),
                       INT_FLOOR, MAX_PEAKS, INT_POWER, True)


def lib_sim(specs, target: float) -> dict[str, float]:
    tol = target * PPM_WIN / 1e6
    lo = np.searchsorted(L["snm"][:L["n_ok"]], target - tol, "left")
    hi = np.searchsorted(L["snm"][:L["n_ok"]], target + tol, "right")
    cand = L["order"][lo:hi]
    if len(cand) == 0:
        return {}
    agg: dict[str, float] = {}
    zshift = np.zeros(len(cand), np.float32)
    for mz, it in specs:
        qm, qp = clean_spectrum(mz, it)
        if len(qm) == 0:
            continue
        sc = search_shift(qm, qp, cand, L["off"], L["mz"], L["it"],
                          MZ_TOL, INT_FLOOR, MAX_PEAKS, INT_POWER, zshift)
        for c, s in zip(cand, sc, strict=True):
            k = L["ik"][c]
            if s > agg.get(k, -1.0):
                agg[k] = float(s)
    return agg

#---CELL---
def analog_sim(specs, target: float) -> list[tuple[str, float]]:
    lo = np.searchsorted(REP_NM, target - ANALOG_WIN, "left")
    hi = np.searchsorted(REP_NM, target + ANALOG_WIN, "right")
    cand = REP[lo:hi]
    if len(cand) == 0:
        return []
    shift = (target - REP_NM[lo:hi]).astype(np.float32)
    ckey = REP_KEY[lo:hi]
    agg: dict[str, float] = {}
    for mz, it in specs:
        qm, qp = clean_spectrum(mz, it)
        if len(qm) == 0:
            continue
        sc = search_shift(qm, qp, cand, L["off"], L["mz"], L["it"],
                          MZ_TOL, INT_FLOOR, MAX_PEAKS, INT_POWER, shift)
        for k, s in zip(ckey, sc, strict=True):
            if s > agg.get(k, -1.0):
                agg[k] = float(s)
    return sorted(agg.items(), key=lambda x: -x[1])[:N_ANALOG]

#---CELL---
BITS = np.load(find_file("fp_bits.npy"))
_g: dict = {}


def _fp_init():
    _g["m2"] = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=4096)
    _g["m3"] = rdFingerprintGenerator.GetMorganGenerator(radius=3, fpSize=4096)
    _g["rk"] = rdFingerprintGenerator.GetRDKitFPGenerator(fpSize=2048, maxPath=6)


def fp_and_mass(smi: str):
    if not HAVE_RDKIT:
        return None
    if not _g:
        _fp_init()
    mol = Chem.MolFromSmiles(str(smi))
    if mol is None:
        return None
    fp = np.concatenate([
        _g["m2"].GetFingerprintAsNumPy(mol).astype(np.uint8),
        _g["m3"].GetFingerprintAsNumPy(mol).astype(np.uint8),
        _g["rk"].GetFingerprintAsNumPy(mol).astype(np.uint8),
        np.array(MACCSkeys.GenMACCSKeys(mol), dtype=np.uint8),
    ])[BITS]
    return fp, float(ExactMolWt(mol))

#---CELL---
class CandidatePool:
    def __init__(self, fp, mass, keys, smiles, nbits):
        o = np.argsort(mass)
        self._fp, self.mass = fp[o], mass[o]
        self.keys = np.asarray(keys, dtype=object)[o]
        self.smiles = np.asarray(smiles, dtype=object)[o]
        self.nbits = nbits
        self.k2i = {k: i for i, k in enumerate(self.keys)}

    def window(self, t, ppm):
        a = np.searchsorted(self.mass, t * (1 - ppm / 1e6), "left")
        b = np.searchsorted(self.mass, t * (1 + ppm / 1e6), "right")
        return np.arange(a, b)

    def fps(self, idx):
        return np.unpackbits(np.asarray(self._fp[idx]), axis=1)[:, :self.nbits]

#---CELL---
def stack_block(fp, mass, keys, smis, seen: set) -> tuple:
    keep = [i for i, k in enumerate(keys) if k not in seen]
    for i in keep:
        seen.add(keys[i])
    if not keep:
        return (fp[:0], mass[:0], keys[:0], smis[:0])
    ix = np.array(keep)
    return fp[ix], mass[ix], np.asarray(keys, dtype=object)[ix], np.asarray(smis, dtype=object)[ix]


def load_named_block(mass_name: str, fp_name: str, meta_name: str, seen: set):
    if not attached(mass_name):
        return None
    d = os.path.dirname(find_file(mass_name))
    meta = pickle.load(open(os.path.join(d, meta_name), "rb"))
    fp = np.load(os.path.join(d, fp_name))
    mass = np.load(os.path.join(d, mass_name))
    keys = np.asarray(meta["keys"], dtype=object)
    smis = np.asarray(meta["smiles"], dtype=object)
    return stack_block(fp, mass, keys, smis, seen) + (int(meta["nbits"]),)

#---CELL---
seen: set = set()
co = load_named_block("coco_mass.npy", "coco_fp.npy", "coco_meta.pkl", seen)
assert co is not None
parts = [co[:4]]
nbits = co[4]
bio = load_named_block("bio_mass.npy", "bio_fp.npy", "bio_meta.pkl", seen) if USE_BIO else None
if bio is not None:
    parts.append(bio[:4])
    print("unique bio", len(bio[2]))
else:
    print("bio dump attached but not merged; USE_BIO", USE_BIO)
fp = np.vstack([p[0] for p in parts])
mass = np.concatenate([p[1] for p in parts])
keys = np.concatenate([p[2] for p in parts])
smis = np.concatenate([p[3] for p in parts])
print("structure dump", len(mass), "nbits", nbits, f"{time.time()-t0:.0f}s")

#---CELL---
def extra_np_rows(seen: set) -> tuple[list[str], list[str]]:
    keys, smis = [], []
    hits = glob.glob("/kaggle/input/**/*.csv", recursive=True)
    hits += glob.glob("/kaggle/input/**/*.parquet", recursive=True)
    for path in hits:
        if "competitions" in path or "sample_submission" in path:
            continue
        try:
            df = pd.read_parquet(path) if path.endswith("parquet") else pd.read_csv(path, nrows=80000)
        except Exception:
            continue
        cols = {c.lower(): c for c in df.columns}
        sc = next((cols[c] for c in ("smiles", "canonical_smiles") if c in cols), None)
        if sc is None:
            continue
        kc = cols.get("inchikey14") or cols.get("inchikey")
        for rec in df[[sc] + ([kc] if kc else [])].dropna().itertuples(index=False):
            smi = str(rec[0])
            key = (str(rec[1])[:14] if kc else smi[:14])
            if smi and key not in seen:
                seen.add(key); keys.append(key); smis.append(smi)
        print("collection extras", os.path.basename(path), len(keys))
        break
    return keys, smis


ek, es = extra_np_rows(seen) if USE_COLLECTION else ([], [])
print("collection into pool", len(es), "USE_COLLECTION", USE_COLLECTION)

#---CELL---
tr = pq.read_table(TRAIN, columns=["inchikey14", "normalized_smiles"]).to_pandas()
tr = tr.dropna().drop_duplicates("inchikey14")
tr = tr[~tr.inchikey14.isin(seen)]
todo_smi = list(tr.normalized_smiles) + list(es)
todo_key = list(tr.inchikey14) + list(ek)
print("structures to fingerprint", len(todo_smi), "collection", len(es))
if HAVE_RDKIT and todo_smi:
    with MPool(4) as mp:
        res = mp.map(fp_and_mass, todo_smi, chunksize=500)
    ok = [i for i, r in enumerate(res) if r is not None]
    if ok:
        tr_fp = np.packbits(np.stack([res[i][0] for i in ok]), axis=1)
        tr_mass = np.array([res[i][1] for i in ok])
        tr_keys = np.asarray(todo_key, dtype=object)[ok]
        tr_smi = np.asarray(todo_smi, dtype=object)[ok]
        fp = np.vstack([fp, tr_fp])
        mass = np.concatenate([mass, tr_mass])
        keys = np.concatenate([keys, tr_keys])
        smis = np.concatenate([smis, tr_smi])
good = np.isfinite(mass)
POOL = CandidatePool(fp[good], mass[good], keys[good], smis[good], nbits)
print("pool", len(POOL.mass), f"{time.time()-t0:.0f}s")

#---CELL---
AMU = {"C": 12.0, "H": 1.007825, "N": 14.003074, "O": 15.994915,
       "P": 30.973762, "S": 31.972071, "F": 18.998403, "Cl": 34.968853,
       "Br": 78.918338, "I": 126.904473}


def fragment_masses(smi: str, max_bonds: int = 34) -> np.ndarray:
    mol = Chem.MolFromSmiles(str(smi)) if HAVE_RDKIT else None
    if mol is None:
        return np.zeros(0)
    n = mol.GetNumAtoms()
    bonds = [(b.GetBeginAtomIdx(), b.GetEndAtomIdx()) for b in mol.GetBonds()]
    w = np.array([AMU.get(a.GetSymbol(), 0.0) + a.GetTotalNumHs() * AMU["H"]
                  for a in mol.GetAtoms()])
    if (w == 0).any() or not bonds or len(bonds) > max_bonds:
        return np.array([float(w.sum())])
    out = {float(w.sum())}
    return w, bonds, n, out

#---CELL---
def _components(n, bonds, drop):
    adj = [[] for _ in range(n)]
    for i, (a, b) in enumerate(bonds):
        if i not in drop:
            adj[a].append(b); adj[b].append(a)
    seen = np.zeros(n, dtype=bool)
    comps = []
    for s in range(n):
        if seen[s]:
            continue
        stack, cur = [s], [s]
        seen[s] = True
        while stack:
            u = stack.pop()
            for v in adj[u]:
                if not seen[v]:
                    seen[v] = True; stack.append(v); cur.append(v)
        comps.append(cur)
    return comps


def fragment_masses2(smi: str) -> np.ndarray:
    pack = fragment_masses(smi)
    if not isinstance(pack, tuple):
        return pack
    w, bonds, n, out = pack
    for i in range(len(bonds)):
        for c in _components(n, bonds, {i}):
            out.add(float(w[c].sum()))
        for j in range(i + 1, len(bonds)):
            for c in _components(n, bonds, {i, j}):
                out.add(float(w[c].sum()))
    return np.array(sorted(out))

#---CELL---
def explain_score(frag, peak_mz, peak_int, mode: float) -> float:
    if len(frag) == 0 or len(peak_mz) == 0:
        return 0.0
    ion = np.sort(np.concatenate([
        frag + dh * AMU["H"] + (PROTON if mode > 0 else -PROTON)
        for dh in (-2, -1, 0, 1, 2)]))
    wt = np.sqrt(np.asarray(peak_int, float))
    tot = float(wt.sum())
    if tot <= 0:
        return 0.0
    idx = np.searchsorted(ion, peak_mz)
    ok = np.zeros(len(peak_mz), dtype=bool)
    for off in (-1, 0):
        k = np.clip(idx + off, 0, len(ion) - 1)
        ok |= np.abs(ion[k] - peak_mz) <= MZ_TOL
    return float(wt[ok].sum() / tot)


def _frag_one(smi):
    try:
        return fragment_masses2(smi)
    except Exception:
        return np.zeros(0)

#---CELL---
def frag_scores(smiles: list[str], specs, mode: float) -> np.ndarray:
    if not HAVE_RDKIT:
        return np.zeros(len(smiles), np.float32)
    with MPool(4) as mp:
        frags = mp.map(_frag_one, smiles, chunksize=8)
    peaks = [clean_spectrum(mz, it) for mz, it in specs]
    out = np.zeros(len(smiles), np.float32)
    for j, frag in enumerate(frags):
        out[j] = max((explain_score(frag, a, b, mode) for a, b in peaks if len(a)),
                     default=0.0)
    return out

#---CELL---
class SinEmb(nn.Module):
    def __init__(self, dim, lo=-2.0, hi=3.2, power=1.0):
        super().__init__()
        n = dim // 2
        wav = torch.pow(10.0, (hi - lo) * torch.pow(torch.linspace(0, 1, n), power) + lo)
        self.register_buffer("inv", (2 * math.pi) / wav)

    def forward(self, x):
        a = x.unsqueeze(-1) * self.inv
        return torch.cat([torch.sin(a), torch.cos(a)], -1)


class Block(nn.Module):
    def __init__(self, d, h, drop):
        super().__init__()
        self.h, self.n1, self.n2 = h, nn.LayerNorm(d), nn.LayerNorm(d)
        self.qkv, self.o = nn.Linear(d, 3 * d), nn.Linear(d, d)
        self.ff = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Dropout(drop),
                                nn.Linear(4 * d, d))
        self.drop = nn.Dropout(drop)

    def forward(self, x, pad):
        B, N, D = x.shape
        y = self.n1(x)
        q, k, v = self.qkv(y).view(B, N, 3, self.h, D // self.h).permute(2, 0, 3, 1, 4)
        a = F.scaled_dot_product_attention(q, k, v, attn_mask=(~pad)[:, None, None, :])
        x = x + self.drop(self.o(a.transpose(1, 2).reshape(B, N, D)))
        return x + self.drop(self.ff(self.n2(x)))

#---CELL---
class FPNet(nn.Module):
    def __init__(self, nbits, d=512, layers=6, heads=8, drop=0.1):
        super().__init__()
        self.mz_emb, self.nl_emb, self.prec_emb = SinEmb(d), SinEmb(d), SinEmb(d)
        self.pk = nn.Linear(2 * d + 1, d)
        self.ad = nn.Embedding(26, d)
        self.ins = nn.Embedding(5, d)
        self.gl = nn.Linear(d + 3, d)
        self.blocks = nn.ModuleList([Block(d, heads, drop) for _ in range(layers)])
        self.norm = nn.LayerNorm(d)
        self.head = nn.Sequential(nn.Linear(2 * d, 2048), nn.GELU(), nn.Dropout(drop),
                                  nn.Linear(2048, nbits))

    def forward(self, mz, it, pad, prec, ad, ins, ce, mode):
        nl = (prec[:, None] - mz).clamp(min=0)
        p = self.pk(torch.cat([self.mz_emb(mz), self.nl_emb(nl), it.unsqueeze(-1)], -1))
        g = self.gl(torch.cat([self.prec_emb(prec), (ce / 100.0).unsqueeze(-1),
                               mode.unsqueeze(-1), torch.log1p(prec).unsqueeze(-1) / 10.0], -1))
        g = g + self.ad(ad) + self.ins(ins)
        x = torch.cat([g.unsqueeze(1), p], 1)
        pad = torch.cat([torch.zeros(mz.size(0), 1, dtype=torch.bool, device=mz.device), pad], 1)
        for blk in self.blocks:
            x = blk(x, pad)
        x = self.norm(x)
        msk = (~pad[:, 1:]).float().unsqueeze(-1)
        mean = (x[:, 1:] * msk).sum(1) / msk.sum(1).clamp(min=1)
        return self.head(torch.cat([x[:, 0], mean], -1))

#---CELL---
ADDUCT_LIST = ["[M+H]+", "[M+NH4]+", "[M+Na]+", "[M+K]+", "[M-H2O+H]+", "[M-2H2O+H]+",
               "[M]+", "[M-H]-", "[M-H2O-H]-", "[M+CH2O2-H]-", "[M+C2H4O2-H]-", "[M+Cl]-",
               "[M]-", "[M+2H]2+", "[M-2H]-", "[2M+H]+", "[2M+Na]+", "[2M+NH4]+", "[2M-H]-",
               "[2M+K]+", "[2M+CH2O2-H]-", "[2M+C2H4O2-H]-", "[2M+Na-2H]-", "[M+Na-2H]-",
               "[M-H2O]+", "<unk>"]
ADDUCT_IX = {a: i for i, a in enumerate(ADDUCT_LIST)}


def instr_family(s) -> int:
    t = str(s or "").lower()
    if "timstof" in t:
        return 0
    if "orbitrap" in t or "qft" in t or "ftms" in t or "hybrid ft" in t or "itft" in t or "exactive" in t:
        return 1
    if "tof" in t:
        return 2
    if "trap" in t or "qq" in t:
        return 3
    return 4

#---CELL---
def prep_peaks(mz, inten, prec_mz, max_peaks=128, floor=1e-3, win=50.0, per_win=8):
    mz = np.asarray(mz, np.float64); it = np.asarray(inten, np.float64)
    if len(mz) == 0:
        return np.zeros(0, np.float32), np.zeros(0, np.float32)
    keep = (mz <= prec_mz + 1.5)
    mz, it = mz[keep], it[keep]
    if len(mz) == 0 or it.max() <= 0:
        return np.zeros(0, np.float32), np.zeros(0, np.float32)
    keep = it >= floor * it.max()
    mz, it = mz[keep], it[keep]
    if len(mz) > max_peaks:
        order = np.argsort(-it)
        bucket = (mz // win).astype(np.int64)
        cnt, sel = {}, []
        for i in order:
            b = int(bucket[i]); c = cnt.get(b, 0)
            if c < per_win:
                cnt[b] = c + 1; sel.append(i)
        sel = np.array(sel)
        if len(sel) > max_peaks:
            sel = sel[np.argsort(-it[sel])[:max_peaks]]
        mz, it = mz[sel], it[sel]
    o = np.argsort(mz)
    mz, it = mz[o], it[o]
    return mz.astype(np.float32), np.sqrt(it / it.max()).astype(np.float32)

#---CELL---
SINGLE, MERGED = [], []
for pth in sorted(glob.glob("/kaggle/input/**/fp_*.pt", recursive=True)):
    ck = torch.load(pth, map_location="cpu", weights_only=False)
    net = FPNet(ck["nbits"], d=ck["d"], layers=ck["layers"]).to(DEVICE).eval()
    net.load_state_dict(ck["model"])
    name = os.path.basename(pth).lower()
    (MERGED if "merged" in name else SINGLE).append(net)
    print("loaded", os.path.basename(pth), "merged" if "merged" in name else "single")
assert SINGLE or MERGED, "fingerprint dataset must contain fp_*.pt"
print("fpnets single", len(SINGLE), "merged", len(MERGED), DEVICE)

#---CELL---
def merge_peaks(sub: pd.DataFrame):
    mz = np.concatenate([np.asarray(r.ms2_mzs, float) for r in sub.itertuples()])
    it = np.concatenate([
        np.asarray(r.ms2_normalized_intensities, float)
        / max(float(np.asarray(r.ms2_normalized_intensities, float).max()), 1e-9)
        for r in sub.itertuples()])
    o = np.argsort(mz); mz, it = mz[o], it[o]
    keep = np.ones(len(mz), bool)
    for j in range(1, len(mz)):
        if mz[j] - mz[j - 1] < 0.005:
            if it[j] >= it[j - 1]:
                keep[j - 1] = False
            else:
                keep[j] = False
    return mz[keep], it[keep]


def ce_of(r) -> float:
    v = getattr(r, "collision_energy_ev", None)
    try:
        arr = np.atleast_1d(v)
        return float(np.mean(arr)) if v is not None and len(arr) else 25.0
    except Exception:
        return 25.0

#---CELL---
@torch.no_grad()
def logits_batch(rows, nets):
    kept, P = [], []
    for r in rows:
        a, b = prep_peaks(r.ms2_mzs, r.ms2_normalized_intensities, float(r.precursor_mz))
        if len(a):
            kept.append(r); P.append((a, b))
    if not P or not nets:
        return None
    B, N = len(P), max(len(a) for a, _ in P)
    mz = np.zeros((B, N), np.float32); it = np.zeros((B, N), np.float32)
    pad = np.ones((B, N), bool)
    for i, (a, b) in enumerate(P):
        mz[i, :len(a)] = a; it[i, :len(b)] = b; pad[i, :len(a)] = False
    T = lambda x: torch.as_tensor(x, device=DEVICE)
    args = (T(mz), T(it), T(pad),
            T(np.array([float(r.precursor_mz) for r in kept], np.float32)),
            T(np.array([ADDUCT_IX.get(r.adduct, 25) for r in kept])),
            T(np.array([instr_family(r.instrument_type) for r in kept])),
            T(np.array([ce_of(r) for r in kept], np.float32)),
            T(np.array([1.0 if r.ionization_mode == "positive" else -1.0 for r in kept], np.float32)))
    return np.mean([n(*args).float().mean(0).cpu().numpy() for n in nets], axis=0)

#---CELL---
@torch.no_grad()
def model_logits(sub: pd.DataFrame):
    rows = list(sub.itertuples())
    if not rows:
        return None
    out = []
    if SINGLE:
        za = logits_batch(rows, SINGLE)
        if za is not None:
            out.append(za)
    if MERGED:
        mz, it = merge_peaks(sub)
        r0 = rows[0]
        fake = SimpleNamespace(
            ms2_mzs=mz, ms2_normalized_intensities=it,
            precursor_mz=float(np.median([float(r.precursor_mz) for r in rows])),
            adduct=r0.adduct, instrument_type=r0.instrument_type,
            collision_energy_ev=25.0, ionization_mode=r0.ionization_mode)
        zb = logits_batch([fake], MERGED)
        if zb is not None:
            out.append(zb)
    return np.mean(out, axis=0) if out else None

#---CELL---
def _rank_norm(x):
    o = np.argsort(-x)
    r = np.empty(len(x))
    r[o] = np.arange(len(x))
    return r / max(1, len(x) - 1)


def _z(x):
    s = float(x.std())
    return (x - x.mean()) / s if s > 1e-9 else np.zeros_like(x)

#---CELL---
def analog_feats(cand_fp, analog_fp, analog_sim):
    nc = cand_fp.shape[0]
    cf = cand_fp.astype(np.float32)
    cs = cf.sum(1)
    if analog_fp is None or not len(analog_sim):
        z = np.zeros(nc, np.float32)
        return z, z, z, z, z, 0.0
    af = analog_fp.astype(np.float32)
    tan = (cf @ af.T) / (cs[:, None] + af.sum(1)[None, :] - (cf @ af.T) + 1e-9)
    w = np.clip(np.asarray(analog_sim, np.float32), 0, None)
    wp = w ** SIM_POWER
    ap = (tan * wp[None, :]).max(1)
    return ap, (tan * w[None, :]).max(1), tan.max(1), tan[:, 0], (
        (tan * wp[None, :]).sum(1) / (wp.sum() + 1e-9)), float(w[0])

#---CELL---
def rank_features(cand_fp, cand_lib, analog_fp, analog_sim, logits, frag):
    nc = cand_fp.shape[0]
    lv = np.asarray(cand_lib, np.float32)
    lvmax = float(lv.max()) if nc else 0.0
    ap, a1, best_tan, top_tan, mean_tan, top_sim = analog_feats(
        cand_fp, analog_fp, analog_sim)
    apmax = float(ap.max()) if nc else 0.0
    cf = cand_fp.astype(np.float32)
    if logits is not None:
        raw = cf @ np.asarray(logits, np.float32)
        nrm = raw / np.sqrt(np.maximum(cf.sum(1), 1.0))
        mfeat = [_z(raw), _rank_norm(raw), raw - raw.max(), _z(nrm),
                 _rank_norm(nrm), (raw == raw.max()).astype(np.float32)]
    else:
        mfeat = [np.zeros(nc, np.float32)] * 6
    fr = np.asarray(frag, np.float32) if frag is not None else np.zeros(nc, np.float32)
    ffeat = [fr, _rank_norm(fr), fr - fr.max() if nc else fr, _z(fr)]
    return lv, lvmax, ap, apmax, a1, best_tan, top_tan, mean_tan, top_sim, mfeat, ffeat, cf

#---CELL---
def rank_features2(lv, lvmax, ap, apmax, a1, best_tan, top_tan, mean_tan,
                   top_sim, mfeat, ffeat, cf, logits):
    nc = len(lv)
    if logits is not None and nc:
        mr = _rank_norm(cf @ np.asarray(logits, np.float32))
        lbest = int(np.argmax(lv)) if lvmax > 0 else -1
        abest = int(np.argmax(ap)) if apmax > 0 else -1
        agree = float(1.0 - mr[lbest]) if lbest >= 0 else 0.0
        agree_a = float(1.0 - mr[abest]) if abest >= 0 else 0.0
        corr = float(np.corrcoef(lv, -mr)[0, 1]) if lv.std() > 1e-9 else 0.0
        xfeat = [lv * (1.0 - mr), ap * (1.0 - mr), np.full(nc, agree),
                 np.full(nc, agree_a), np.full(nc, agree * lvmax), np.full(nc, corr)]
    else:
        xfeat = [np.zeros(nc, np.float32)] * 6
    return np.column_stack([
        lv, _rank_norm(lv), np.full(nc, lvmax), lv - lvmax, (lv > 0).astype(float),
        ap, _rank_norm(ap), np.full(nc, apmax), ap - apmax,
        a1, best_tan, top_tan, mean_tan, np.full(nc, top_sim),
        np.full(nc, np.log(max(nc, 1))), *mfeat, *ffeat, *xfeat,
    ]).astype(np.float32)

#---CELL---
z = np.load(find_file("rank_train.npz"))
NFEAT = z["X"].shape[1]
RANKERS = []
for w1 in W1_PRIORS:
    W = np.where(z["M"] == 0, w1, 1.0 - w1)
    for sd in SEEDS:
        m = HistGradientBoostingClassifier(random_state=sd, **GBM)
        m.fit(z["X"], z["Y"], sample_weight=W)
        RANKERS.append(m)
print("rankers", len(RANKERS), "rows", z["X"].shape[0], "feats", NFEAT)


def rank_proba(X):
    return np.mean([m.predict_proba(X)[:, 1] for m in RANKERS], axis=0)

#---CELL---
def prune_window(cand, lib_hits, target):
    if TOP_KEEP <= 0 or len(cand) <= TOP_KEEP:
        return cand
    lv = np.array([lib_hits.get(POOL.keys[c], 0.0) for c in cand], np.float32)
    mass_diff = np.abs(POOL.mass[cand] - target)
    must = np.where(lv > 0)[0]
    rest = np.where(lv == 0)[0]
    n_fill = max(0, TOP_KEEP - len(must))
    fill = rest[np.argsort(mass_diff[rest])[:n_fill]] if n_fill else rest[:0]
    keep = np.unique(np.concatenate([must, fill])) if len(fill) else must
    return cand[keep]


def rank_molecule(rows: pd.DataFrame) -> str:
    nms = rows["_nm"].to_numpy(dtype=float)
    nms = nms[np.isfinite(nms)]
    if len(nms) == 0:
        sign = float(np.mean([1.0 if str(m) == "positive" else -1.0
                              for m in rows["ionization_mode"].astype(str)]))
        nms = rows["precursor_mz"].to_numpy(dtype=float) - PROTON * sign
        nms = nms[np.isfinite(nms)]
    if len(nms) == 0:
        return ""
    target = float(np.median(nms))
    specs = list(zip(rows["ms2_mzs"].to_numpy(),
                     rows["ms2_normalized_intensities"].to_numpy(), strict=True))
    lib_hits = lib_sim(specs, target)
    analogs = analog_sim(specs, target)
    cand = POOL.window(target, PPM_WIN)
    if len(cand) == 0:
        cand = POOL.window(target, PPM_FALLBACK)
    if len(cand) == 0:
        return ";".join(SMI_OF[k] for k, _ in sorted(lib_hits.items(), key=lambda x: -x[1])[:K]
                        if k in SMI_OF)
    cand = prune_window(cand, lib_hits, target)
    return cand, specs, lib_hits, analogs, target

#---CELL---
def rank_molecule2(pack, rows: pd.DataFrame) -> str:
    if isinstance(pack, str):
        return pack
    cand, specs, lib_hits, analogs, target = pack
    cfp = POOL.fps(cand)
    lv = np.array([lib_hits.get(POOL.keys[c], 0.0) for c in cand], np.float32)
    ids, sims = [], []
    for k, s in analogs:
        i = POOL.k2i.get(k, -1)
        if i >= 0:
            ids.append(i); sims.append(s)
    afp = POOL.fps(np.array(ids)) if ids else None
    mode = float(np.mean([1.0 if str(m) == "positive" else -1.0
                          for m in rows["ionization_mode"].astype(str)]))
    fsc = frag_scores([str(POOL.smiles[c]) for c in cand], specs, mode)
    zlog = model_logits(rows)
    parts = rank_features(cfp, lv, afp, np.array(sims, np.float32), zlog, fsc)
    X = rank_features2(*parts, zlog)[:, :NFEAT]
    order = np.argsort(-rank_proba(X))
    pool_ord = [str(POOL.smiles[cand[i]]) for i in order]
    return ";".join(list(dict.fromkeys(pool_ord))[:K])

#---CELL---
test = test.copy()
test["_nm"] = neutral_mass(test["precursor_mz"].to_numpy(dtype=float),
                          test["adduct"].to_numpy())
records = []
groups = list(test.groupby("molecule_id", sort=True))
for i, (mol_id, rows) in enumerate(groups, start=1):
    field = rank_molecule2(rank_molecule(rows), rows)
    tokens = [t for t in str(field).split(";") if t] or ["CCO"]
    tokens = (tokens + ["CCO"] * K)[:K]
    records.append({"molecule_id": mol_id, "smiles": ";".join(tokens)})
    if i % 25 == 0 or i == len(groups):
        print(f"{i}/{len(groups)} molecules {time.time()-t0:.0f}s", flush=True)
sub = pd.DataFrame(records)
missing = sorted(set(sample["molecule_id"]) - set(sub["molecule_id"]))
if missing:
    sub = pd.concat([sub, pd.DataFrame({
        "molecule_id": missing, "smiles": ";".join(["CCO"] * K)})], ignore_index=True)
sub = sub.drop_duplicates("molecule_id")
sub["n_guess"] = sub["smiles"].str.split(";").map(len)

#---CELL---
assert set(["molecule_id", "smiles"]).issubset(sub.columns)
assert sub["molecule_id"].is_unique
assert (sub["n_guess"] == 25).all()
out = Path("/kaggle/working") if Path("/kaggle/working").exists() else Path("outputs/casmi-08")
out.mkdir(parents=True, exist_ok=True)
path = out / "submission.csv"
sub[["molecule_id", "smiles"]].to_csv(path, index=False)
print("wrote", path, "rows", len(sub), "elapsed", f"{time.time()-t0:.0f}s")
preview = sub.head(8).copy()
preview["preview"] = preview["smiles"].str.slice(0, 70)
show_table(preview.drop(columns=["smiles"]), decimals=0)

#---CELL---
if "normalized_smiles" in test.columns:
    raise AssertionError("test labels leaked into the download")
fig = go.Figure(go.Histogram(x=sub["n_guess"], marker_color=GOLD, nbinsx=25))
fig = fig_layout(fig, "Exactly 25 guesses after the 8.5 ppm window")
fig.update_xaxes(title="SMILES per molecule")
fig.show()
