#!/usr/bin/env python3
"""Format validator for an Enveda CASMI 2026 submission.csv.

Enforces exactly the rejection rules from the Overview:
  * header must be: molecule_id,smiles
  * no nulls / empty strings in either column
  * every molecule_id appears exactly once
  * at most 25 semicolon-separated guesses per molecule
Optional:
  --expect IDS_FILE   compare the molecule_id set against a truth/test file
  --check-parsable    warn (not fail) on SMILES RDKit cannot parse

Exit code 0 = valid submission format.
"""
import argparse
import csv
import sys

MAX_GUESSES = 25


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("submission")
    ap.add_argument("--expect", help="csv/parquet with molecule_id column (e.g. test.parquet)")
    ap.add_argument("--check-parsable", action="store_true")
    args = ap.parse_args()

    errs, warns = [], []
    with open(args.submission, newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header != ["molecule_id", "smiles"]:
            errs.append(f"header must be exactly ['molecule_id','smiles'], got {header}")
            return report(errs, warns)
        seen = {}
        nrows = 0
        for lineno, row in enumerate(reader, start=2):
            if len(row) != 2:
                errs.append(f"line {lineno}: expected 2 fields, got {len(row)}")
                continue
            mid, smi = row
            nrows += 1
            if not mid.strip() or mid.strip().lower() in {"na", "nan", "null", "none"}:
                errs.append(f"line {lineno}: null/empty molecule_id")
            if not smi.strip() or smi.strip().lower() in {"na", "nan", "null", "none"}:
                errs.append(f"line {lineno}: null/empty smiles")
            if mid in seen:
                errs.append(f"line {lineno}: duplicate molecule_id {mid}")
            seen[mid] = lineno
            guesses = smi.split(";")
            if len(guesses) > MAX_GUESSES:
                errs.append(f"line {lineno}: {len(guesses)} guesses (> {MAX_GUESSES})")
            if any(not g.strip() for g in guesses):
                errs.append(f"line {lineno}: empty guess token inside smiles field")
    if nrows == 0:
        errs.append("submission is empty")

    if args.expect:
        import pandas as pd
        exp = pd.read_parquet(args.expect) if args.expect.endswith(".parquet") else pd.read_csv(args.expect)
        want, got = set(exp["molecule_id"]), set(seen)
        for m in sorted(want - got):
            errs.append(f"missing molecule_id {m}")
        for m in sorted(got - want):
            errs.append(f"unexpected molecule_id {m}")

    if args.check_parsable:
        try:
            from rdkit import Chem, RDLogger
            RDLogger.DisableLog("rdApp.*")
            with open(args.submission, newline="") as f:
                for row in csv.DictReader(f):
                    for i, g in enumerate(row["smiles"].split(";")):
                        if Chem.MolFromSmiles(g) is None:
                            warns.append(f"{row['molecule_id']} guess {i+1} unparsable: {g!r}")
        except ImportError:
            warns.append("rdkit not installed; skipped parsability check")

    return report(errs, warns)


def report(errs, warns) -> int:
    for w in warns:
        print("WARN:", w)
    if errs:
        for e in errs[:50]:
            print("ERROR:", e)
        print(f"INVALID submission ({len(errs)} error(s))")
        return 1
    print("VALID submission format")
    return 0


if __name__ == "__main__":
    sys.exit(main())
