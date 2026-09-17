#!/usr/bin/env python3
"""End-to-end smoke test for baseline_retrieval.ipynb on synthetic data.

Builds a tiny fake train/test parquet pair (12 structures, 5 spectra each; 3 test
molecules x 2 adducts whose spectra are copies of their train spectra), executes
every code cell of the notebook against it, then validates submission.csv and
scores it with scorer.py. Expect: VALID format and MRR@25 = 1.0 (the copied
spectra must be retrieved at rank 1).
"""
import json
import os
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors
from rdkit.Chem.rdMolDescriptors import CalcMolFormula

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scorer import inchikey14  # noqa: E402

RDLogger.DisableLog("rdApp.*")

SMILES = ["CCO", "C(=O)O", "c1ccccc1", "OC(=O)CC", "OCC(O)CO",
          "CN1C=NC2=C1C(=O)N(C)C(=O)N2C", "CC1=CC(=O)C=CC1=O", "OC(=O)c1ccccc1O",
          "NCCc1ccc(O)cc1", "CC(=O)Nc1ccc(O)cc1", "CCCCCCCCCC", "OC1=CC=CC=C1"]
ADDUCTS = {"[M+H]+": 1.00728, "[M+Na]+": 22.98922, "[M+NH4]+": 18.03383}


def fake_spectrum(rng, mass):
    n = 30
    low = 30.0
    mzs = np.sort(rng.uniform(low, max(mass * 0.95, low + 20.0), n))
    ints = rng.random(n) ** 2
    ints = ints / ints.max()
    return mzs, ints


def main():
    tmp = tempfile.mkdtemp(prefix="casmi_smoke_")
    rows, sid = [], 0
    test_rows, truth = [], []
    test_pick = [0, 4, 5]
    for si, smi in enumerate(SMILES):
        mol = Chem.MolFromSmiles(smi)
        can = Chem.MolToSmiles(mol)
        mass = Descriptors.ExactMolWt(mol)
        ik = inchikey14(can)
        for k in range(5):
            rng = np.random.default_rng(1000 * si + k)
            mzs, ints = fake_spectrum(rng, mass)
            adduct = "[M+H]+" if k % 2 == 0 else "[M+Na]+"
            rows.append(dict(molecule_id=f"tr_{si}", spectrum_id=f"s_{sid}", ms2_mzs=mzs,
                             ms2_normalized_intensities=ints, adduct=adduct,
                             ionization_mode="positive", precursor_mz=mass + ADDUCTS[adduct],
                             ingest_lib="gnps", normalized_smiles=can, inchikey14=ik,
                             molecular_formula=CalcMolFormula(mol)))
            sid += 1
            if si in test_pick and k < 2:  # test spectra = copies, new adducts
                tadd = ["[M+H]+", "[M+NH4]+"][k]
                test_rows.append(dict(molecule_id=f"m_t{si}", spectrum_id=f"t_{sid}",
                                      ms2_mzs=mzs, ms2_normalized_intensities=ints,
                                      adduct=tadd, ionization_mode="positive",
                                      precursor_mz=mass + ADDUCTS[tadd]))
        if si in test_pick:
            truth.append(dict(molecule_id=f"m_t{si}", smiles=can))

    pd.DataFrame(rows).to_parquet(os.path.join(tmp, "train.parquet"))
    pd.DataFrame(test_rows).to_parquet(os.path.join(tmp, "test.parquet"))
    pd.DataFrame(truth).to_csv(os.path.join(tmp, "truth.csv"), index=False)

    # execute the pipeline (notebook cells or single-block script) on fake data
    here = os.path.dirname(os.path.abspath(__file__))
    target = sys.argv[1] if len(sys.argv) > 1 else "notebook"
    if target == "single":
        sources = [open(os.path.join(here, "baseline_single_cell.py")).read()]
    else:
        nb = json.load(open(os.path.join(here, "baseline_retrieval.ipynb")))
        sources = ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]
    os.environ["CASMI_INPUT"] = tmp
    workdir = os.getcwd()
    os.chdir(tmp)  # submission.csv lands next to the fake data
    try:
        ns2 = {"__name__": "__main__"}
        for i, s in enumerate(sources):
            exec(compile(s, f"<{target} block {i}>", "exec"), ns2)
    finally:
        os.chdir(workdir)

    v = subprocess.run([sys.executable, os.path.join(here, "validate_submission.py"),
                        os.path.join(tmp, "submission.csv")], capture_output=True, text=True)
    print(v.stdout.strip(), v.stderr.strip())
    s = subprocess.run([sys.executable, os.path.join(here, "scorer.py"),
                        os.path.join(tmp, "submission.csv"), os.path.join(tmp, "truth.csv")],
                       capture_output=True, text=True)
    print(s.stdout.strip(), s.stderr.strip())
    ok = v.returncode == 0 and "MRR@25: 1.0" in s.stdout
    print("SMOKE TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
