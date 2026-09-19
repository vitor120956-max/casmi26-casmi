# 🧪 CASMI 2026: Mastering the Domain Gap, Diagnostic Post-Mortem & Two-Ranker SOTA Engine
### *The Definitive Guide to timsTOF Domain Discrepancies, Candidate Traps, and the 0.353+ Two-Ranker Architecture*

> **Author:** [haideptry](https://www.kaggle.com/haideptry) (Author of the #1 Most-Voted Baseline & 0.339 Milestone)  
> **Topic:** Post-Mortem Analysis (Why LB Crashes from 0.339 to 0.297/0.327), Visual Domain Gap Diagnostics & The Two-Ranker SOTA Engine  
> **Hardware:** Runs completely offline on Dual T4 GPUs (`NvidiaTeslaT4x2`) or fast multi-threaded CPU.

---

## 🧭 Executive Summary: The Journey & Key Questions Answered

Across the CASMI 2026 competition, many teams observe confounding phenomena on the Public Leaderboard:
1. *Why does a notebook with 99% identical code score 0.339 in one run, but crash to 0.297 or 0.327 in another?*
2. *Why do tautomer deduplication and naive candidate caps destroy Leaderboard scores instead of boosting them?*
3. *Why does the public deep fingerprint model suffer from a subtle 0.49 vs 0.80 data leak, and how does a Two-Ranker Engine resolve it?*

This notebook is built in two integrated halves:
* **Part I — The Diagnostic Post-Mortem & Interactive Domain Gap Dashboard:** Pinpointing the exact chemistry and mathematical mechanisms behind the 3 lethal traps.
* **Part II — The Production Two-Ranker Adduct-Shifted Engine:** Full end-to-end execution combining `prvsiyan`'s held-out FPNet ranker with `megayak`'s 7-library adduct-shifted ranker to output a high-scoring `submission.csv`.

---

## 🏆 Community Credits & Standing on the Shoulders of Giants
* **prvsiyan**: For the pioneer *Analog Propagation* pipeline, the 6,930-bit FPNet Transformer architecture, and calibrated 31-feature ranking formulation.
* **megayak**: For discovering the deep FPNet training leak, simulating 2,250 molecules across 7 libraries (`megayak/casmi26-simulated-ranker-rows`), and introducing the Two-Ranker framework with adduct-shifted library search.
* **dariushafshar**: For pioneering metric-exact InChIKey14 evaluation canonicalization principles.
* **Enveda Biosciences**: For hosting this milestone dataset bridging natural product chemistry and machine learning.


# 🔬 Part I: Deconstructing the 3 Lethal Traps in CASMI 2026

### ⚠️ Trap 1: The Candidate Cap Recall Bug (The 0.339 $	o$ 0.297 Drop)
* **What happened**: When optimizing inference speed, capping candidates (e.g. `CAND_CAP = 80`) based on coarse score:
  $$\text{coarse\_score} = \text{lib\_sim} \times 100 - |\Delta \text{mass}|$$
* **The Fatal Flaw**: For Class 1 (library hits, $\text{lib\_sim} > 0$), this works fine. But for **Class 2** (no library hit, $\text{lib\_sim} = 0$), the coarse score reduces purely to $-|\Delta \text{mass}|$.
* In high-resolution mass spectrometry within an isobaric $\pm 8.5$ ppm window, whether an isomer deviates by $0.001$ Da or $0.003$ Da is completely random. Capping at 80 silently **eliminated 24.8% of true Class-2 reachable structures** before the ranker ever inspected them!

---

### ⚠️ Trap 2: The Premature Tautomer Deduplication Trap (The 0.339 $	o$ 0.327 Drop)
* **What happened**: In V20, candidates were aggressively canonicalized using `TautomerEnumerator().Canonicalize()` and deduplicated on InChIKey14 early in the candidate list.
* **The Fatal Flaw**: While the competition metric evaluates canonical InChIKey14, canonicalization alters ~10% of COCONUT identifiers. Applying it aggressively across raw top candidates **dropped 1,309 valid V17 candidate positions (13.1% of top-25 slots)**, replacing true high-probability isomers with lower-ranked decoys.

---

### ⚠️ Trap 3: The timsTOF Domain Gap & Deep FPNet Training Leak
* The test set is **100% timsTOF**. But the public FPNet model weights were pre-trained on GNPS, MoNA, MSDIAL, MassBank, and Pluskal structures.
* On those libraries, FPNet single-channel MRR looks unrealistically high (**0.76 – 0.82**), while on held-out timsTOF molecules (`enveda-np-examples`), its true MRR is **0.49**.
* **The Two-Ranker Solution**: We run two distinct rankers on the exact same evidence:
  1. **Ranker 1 (0.65 weight)**: prvsiyan's held-out timsTOF ranker + FPNet models.
  2. **Ranker 2 (0.35 weight)**: An extended ranker fitted on 2,250 molecules from 7 libraries without FPNet, powered by Adduct-Shifted matching and same-polarity analogs.


# 🚀 Part II: Production Two-Ranker Engine Execution (0.353+ SOTA)

We now execute the full, standalone Two-Ranker Engine:
1. **Unpack & Install Offline Wheels**: RDKit 2026.3.3.
2. **Build Neutral-Mass Reference Library & COCONUT 2.0 Pool** (711k candidates).
3. **Multi-Channel Evidence Extraction**:
   - Direct & Adduct-Shifted Entropy Matching (`search_shift_rows`).
   - Same-Polarity Analog Search (`pos` / `neg` representatives).
   - Adduct-Aware MetFrag-lite Charge Carrier Modeling.
   - Dual FPNet Neural Transformer Logits ($f \cdot z$).
4. **Two-Ranker Ensembling**:
   - Fit 8 GBDT models on `rank_train.npz` (weight 0.65).
   - Fit 4 GBDT models on 7-library `sim_rank_rows_nofp.npz` (weight 0.35).
   - Within-molecule reciprocal probability blending.
5. **Exact Evaluation Metric Canonicalization & Output Validation**:
   - Output exact 400 rows $\times$ 25 valid SMILES.


## 1 · Similarity kernels, adducts, ranking features, MetFrag-lite
Entropy similarity (Li et al. 2021), mass-shifted search, adduct table and prvsiyan's 31 ranking features, plus `search_shift_rows` (adduct-shifted library match) and `explain_score_adduct`.

## 2 · Spectrum → fingerprint model
prvsiyan's FPNet; weights from `prvsiyan/casmi26-fp-models-v2` (single-spectrum and merged-spectrum models, averaged views).

## 3 · Engine
Library (row groups straight to float32), candidate pool (COCONUT ∪ training structures, ±10 ppm), index (all / positive / negative representatives), per-molecule channels, feature blocks, ranker and submission. The feature code is byte-for-byte the code that produced the training rows; a local check asserts both give identical matrices.

## 4 · Run
Both rankers are fitted here: ours from `megayak/casmi26-simulated-ranker-rows` (4 HistGradientBoosting models), prvsiyan's from `prvsiyan/casmi26-ranker-features` (8 models: 2 priors × 4 seeds, as in his notebook).

## 5 · Numbers behind the choices

Predicted LB uses prvsiyan's calibration `0.162·c1 + 0.220·c2` on enveda-np-examples (the only held-out timsTOF set).

| Features (no fingerprint channel, trained on 7 sets) | np Class-1 | np Class-2 | predicted LB |
|---|---|---|---|
| prvsiyan's 31 features | 0.852 | 0.644 | 0.280 |
| + adduct-shifted / mean / count library block | **0.872** | **0.655** | **0.285** |
| + polarity analogs | 0.856 | 0.651 | 0.282 |
| all blocks | 0.871 | 0.646 | 0.283 |

Channel-only MRR, Class-2 simulation (enveda-np-examples): analog 0.524 · same-polarity analog 0.532 · public fingerprint model 0.493 · MetFrag-lite 0.243. Class-1: library 0.930 · adduct-shifted library 0.938.

**Dead end measured along the way:** DreaMS embeddings as an analog channel tie the classical mass-shifted search on Class-2 (0.58 vs 0.57–0.63) and only help Class-1.