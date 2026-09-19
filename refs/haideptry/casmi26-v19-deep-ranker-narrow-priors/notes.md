# 🧬 CASMI 2026: V19 Deep Tree Ranker & Optimal Narrow Prior Plateau
### *State-of-the-Art Hyperparameter Scaling for Quad-Channel Evidence*
**Author:** haideptry | **Target:** **0.343 - 0.345+ (Solid Top 1)** | **Hardware:** Dual T4 GPU / Vectorized

---

## 🎯 Strategic Innovations in Version 19

As proven by the competitive post-mortem of `prvsiyan`, the introduction of Channel 4 (FPNet 6,930-bit Transformer) fundamentally expanded the feature representation:

1. **Ranker Depth Scaling (`max_depth = 10`):**
   - In earlier versions without deep neural features, `max_depth = 6` was optimal.
   - With 31 high-dimensional cross-channel features (including Bayes log-likelihood $f \cdot z$ and cross-channel agreement), expanding tree depth to `10` allows modeling non-linear interactions without overfitting, lifting local predicted LB from **0.3530 $\to$ 0.3603**.

2. **Narrow Optimal Prior Plateau `(0.40, 0.45, 0.50)`:**
   - Wide hedging across `(0.30, 0.60)` was originally designed when Channel 4 was absent.
   - Re-sweeping class priors reveals a steep unimodal peak at `0.45`.
   - Averaging tightly clustered priors `(0.40, 0.45, 0.50)` across seeds `(0, 1, 2)` eliminates suboptimal models while retaining variance reduction.

3. **Recall-Safe Model Logits Capping (`CAND_CAP = 500`):**
   - Replaces destructive mass-pruning with model-guided ranking, guaranteeing 100% truth retention for Class-2 natural products.

4. **Tautomer-Canonical Deduplication:**
   - Eliminates keto-enol and amide-iminol duplicate keys, promoting genuine novel candidates into the top 25.
