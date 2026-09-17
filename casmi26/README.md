# casmi26 — Enveda CASMI 2026 toolkit

Local companion tools for the Kaggle competition
*Enveda CASMI 2026 – Molecule ID From Mass Spectra* (predict SMILES from LC-MS/MS).

| File | Purpose |
|---|---|
| `scorer.py` | Local replica of the metric: MRR@25 with RDKit tautomer canonicalization → InChIKey14 matching. `--selftest` reproduces the Overview's glucose example. |
| `validate_submission.py` | Enforces the submission rejection rules (header, nulls, duplicate ids, ≤25 guesses); `--expect test.parquet` checks the id set; `--check-parsable` warns on unparsable SMILES. |
| `baseline_retrieval.ipynb` | Kaggle-ready tier-1 baseline: binned-cosine spectral retrieval + precursor-mass filter, per-molecule evidence aggregation, writes `submission.csv`. CPU-only, minutes of runtime. |
| `build_notebook.py` | Regenerates the notebook from source cells. |

## Quick start

```bash
pip install rdkit pandas pyarrow scipy          # local deps
python scorer.py --selftest                     # verify matching rule
python validate_submission.py ../uploads/sample_submission.csv
python scorer.py my_submission.csv truth.csv    # truth: molecule_id + smiles|inchikey14
```

On Kaggle: upload `baseline_retrieval.ipynb` as a notebook, point `INPUT` at the
competition data directory (auto-detected), run all cells → `submission.csv`.

## Honest expectations

- Tier 1 (this notebook) should score > 0 mainly on class-1 molecules (in public
  spectral libraries). It cannot reach class 2 (needs structure-DB retrieval) or
  class 3 (de novo).
- Local holdout recipe: hold out the 250 `enveda-np-examples` compounds (same
  instrument/pipeline as the hidden test), remove them from the index, score with
  `scorer.py`. Best public proxy for the real leaderboard.
- Competition scoring pins RDKit **2026.03.3** for tautomer canonicalization; local
  versions may differ marginally.
