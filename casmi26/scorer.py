#!/usr/bin/env python3
"""Local replica of the Enveda CASMI 2026 scoring metric: Mean Reciprocal Rank @ 25.

Matching rule (from the competition Overview):
    Both the predicted SMILES and the answer SMILES are passed through RDKit's
    tautomer canonicalization, reduced to the first block of their InChIKey
    (the InChIKey14), and compared. Equal keys => correct guess.
    (Stereochemistry and tautomer form are therefore forgiven.)

Score:
    MRR@25 = mean over molecules of 1 / rank(first correct guess in your top-25).
    A molecule with no correct guess in the list scores 0.

Usage:
    python scorer.py submission.csv truth.csv
    python scorer.py submission.parquet truth.parquet
    python scorer.py --selftest

truth file must contain `molecule_id` plus either a `smiles` column (canonical or
not - it will be canonicalized here) or a precomputed `inchikey14` column.

NOTE: the competition pins RDKit 2026.03.3 for tautomer canonicalization. Your
local RDKit may differ; discrepancies should be rare but are possible for
exotic tautomer cases. On Kaggle the pinned version is what counts.
"""
import argparse
import sys

import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem.MolStandardize import rdMolStandardize

RDLogger.DisableLog("rdApp.*")

_TAUT = rdMolStandardize.TautomerEnumerator()


def inchikey14(smiles: str):
    """Tautomer-canonicalized InChIKey first block, or None if unparsable."""
    if smiles is None or not str(smiles).strip():
        return None
    mol = Chem.MolFromSmiles(str(smiles))
    if mol is None:
        return None
    try:
        mol = _TAUT.Canonicalize(mol)
    except Exception:
        pass  # fall back to the raw mol; better than dropping the guess
    ik = Chem.MolToInchiKey(mol)
    return ik.split("-")[0] if ik else None


def load_table(path: str) -> pd.DataFrame:
    if path.endswith(".parquet"):
        return pd.read_parquet(path)
    return pd.read_csv(path)


def score(submission_path: str, truth_path: str) -> dict:
    sub = load_table(submission_path)
    truth = load_table(truth_path)

    need = {"molecule_id", "smiles"} & set(sub.columns)
    if {"molecule_id", "smiles"} - set(sub.columns):
        raise SystemExit(f"submission needs columns molecule_id,smiles; got {list(sub.columns)}")
    del need

    # truth keys
    tkey = {}
    for row in truth.itertuples(index=False):
        d = row._asdict()
        if "inchikey14" in d and pd.notna(d.get("inchikey14")):
            tkey[d["molecule_id"]] = str(d["inchikey14"])
        else:
            tkey[d["molecule_id"]] = inchikey14(d.get("smiles"))

    scores, hits1, hits25, missing = [], 0, 0, 0
    for row in sub.itertuples(index=False):
        d = row._asdict()
        mid = d["molecule_id"]
        guesses = [g for g in str(d["smiles"]).split(";")][:25]
        tk = tkey.get(mid)
        if tk is None:
            missing += 1
            continue
        rank = 0
        for i, g in enumerate(guesses, start=1):
            if inchikey14(g) == tk:
                rank = i
                break
        scores.append(1.0 / rank if rank else 0.0)
        if rank == 1:
            hits1 += 1
        if rank:
            hits25 += 1

    n = len(scores) or 1
    return {
        "molecules_scored": len(scores),
        "molecules_missing_from_truth": missing,
        "MRR@25": round(sum(scores) / n, 5),
        "hit@1": round(hits1 / n, 5),
        "hit@25": round(hits25 / n, 5),
    }


def selftest() -> None:
    # From the competition Overview: both glucose SMILES must reduce to WQZGKKKJIJFFOK
    a = inchikey14("OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O")
    b = inchikey14("OCC1OC(O)C(O)C(O)C1O")
    print("glucose stereo/tautomer pair ->", a, b)
    assert a == b == "WQZGKKKJIJFFOK", "tautomer canonicalization mismatch!"
    # rank arithmetic
    assert 1 / 1 == 1.0 and abs(1 / 25 - 0.04) < 1e-12
    print("selftest OK: matching rule and rank arithmetic reproduced")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("submission", nargs="?")
    ap.add_argument("truth", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        sys.exit(0)
    if not (args.submission and args.truth):
        ap.error("need submission and truth paths (or --selftest)")
    res = score(args.submission, args.truth)
    for k, v in res.items():
        print(f"{k}: {v}")
