# casmi26 — Enveda CASMI 2026 (private competition repo)

Predict 2D structures (SMILES) from LC-MS/MS spectra · MRR@25 · $50k Featured competition.
Team: victor120956 + agent. **Goal: top 5.** Status 17/09: public 0.306, rank ~83/408.

➡️ **New here (human or agent)? Read [`HANDOFF.md`](HANDOFF.md) first**, then
[`casmi26/STRATEGY.md`](casmi26/STRATEGY.md).

## Layout
```
HANDOFF.md            resumption handbook (state, credentials protocol, queue, gotchas)
casmi26/              toolkit: scorer, validator, tier-1 notebook+builder, smoke test, STRATEGY
fork_bera/            GPU fork kernel (beraterolelk-based + our patches) + metadata
kpush/                our CPU baseline kernel source + metadata
refs/                 pulled public notebooks of the top teams (attribution inside)
forkout/, forklogs/   latest fork outputs and run logs
```

## Quickstart (new machine/agent)
```bash
pip install kaggle rdkit pyarrow scipy
# kaggle.json -> ~/.kaggle/ (chmod 600)  [see HANDOFF.md §2]
python casmi26/scorer.py --selftest
python casmi26/validate_submission.py <submission.csv>
kaggle kernels push -p fork_bera        # new fork version
kaggle kernels push -p kpush            # new baseline version
```

Private during the competition; licensing/cleanup decisions at the end (winner
obligations may require open-sourcing the winning code — MIT).
