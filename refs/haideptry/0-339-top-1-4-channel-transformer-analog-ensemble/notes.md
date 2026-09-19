# ⚡ [0.339 Top 1] 4-Channel Transformer & Analog Ensemble
### *Enveda CASMI 2026 - High-Throughput Molecule Identification from Mass Spectra*
**Author:** haideptry | **Public LB:** **0.339 (Rank 1 / Gold Medal Zone)** | **Runtime:** ~35 mins (Dual T4)

---

## 🎯 TL;DR & Architectural Innovations

Evaluating exact 14-character tautomer-canonical InChIKeys under **MRR@25** suffers from combinatorial failure when using generative de-novo approaches.
This solution formulates molecule identification as an end-to-end **quad-channel retrieval and Bayes multi-evidence reranking** pipeline:

1. **Channel 1 (Direct Library Matching):** Fast Numba spectral entropy alignment over reference libraries (`train.parquet`).
2. **Channel 2 (Mass-Shifted Analog Propagation):** Cross-homolog structural propagation ($|\Delta M| \le 200\text{ Da}$) via power-weighted Tanimoto ($sim(a)^4 \cdot \text{Tanimoto}$).
3. **Channel 3 (In-Silico Fragmentation - MetFrag-lite):** Bond dissociation explainability scoring on observed MS2 peaks.
4. **Channel 4 (Neural Spectrum-to-Fingerprint Transformer):** 6-layer Transformer (`FPNet`) predicting 6,930-bit logits $z$, evaluated via **exact Bayes log-likelihood linear dot product** ($f \cdot z$).
5. **Bagged Seed & Prior Ensemble:** 4 seeds $\times$ 2 class priors eliminating the $\pm 0.006$ Kaggle noise floor.

```mermaid
flowchart TD
    Q["Query MS/MS Spectra & Precursor m/z"] --> ADDUCT["Neutral Mass Derivation & Multi-Spectra Peak Fusion"]
    
    subgraph Evidence_Channels["Quad-Channel Evidence Extraction"]
        ADDUCT -->|Direct Entropy Match +/- 8.5 ppm| C1["Channel 1: Library Search\n(Class 1 hit scoring)"]
        ADDUCT -->|Mass Shift +/- 200 Da| C2["Channel 2: Analog Propagation\n(Scaffold relative matching)"]
        ADDUCT -->|Bond-Breaking Simulation| C3["Channel 3: MetFrag-lite\n(Peak explainability score)"]
        ADDUCT -->|Deep MS2 Transformer| C4["Channel 4: Neural Fingerprint\n(6,930-bit logits z -> f . z)"]
    end
    
    subgraph Candidate_Pool["Unified Candidate Pool (711,705 Structures)"]
        COCO["COCONUT 2.0 (462k) ∪ Training Scaffolds (275k)"]
        WIN["Optimal Neutral-Mass Window (+/- 8.5 ppm)\nPruned Top-80 SNR Candidates"]
        COCO --> WIN
    end
    
    C1 --> FEAT["31-Feature Matrix Assembly\n- Library Sim & Z-score\n- Analog Sim & Tanimoto (ap, a1, best, mean)\n- MetFrag Intensity Explain Ratio\n- Model Logits f.z & Rank Agreement Features"]
    C2 --> FEAT
    C3 --> FEAT
    C4 --> FEAT
    WIN --> FEAT
    
    FEAT --> GBDT["Ensemble HistGradientBoosting Ranker\n- 2 Class Priors (W1 = 0.30, 0.60)\n- 4 Seed Iterations (Bagging Variance Reduction)"]
    GBDT --> POST["Calibrated Posterior Probabilities P(Candidate is Truth)"]
    POST --> SUB["Deduplicated Top 25 SMILES per Molecule (submission.csv)"]
```
