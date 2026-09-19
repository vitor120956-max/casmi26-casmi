import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Progression data across versions
versions = [
    {"Version": "V6", "LB": 0.149, "Highlight": "Baseline Spectral Cosine", "Class": "Ch 1 only"},
    {"Version": "V10", "LB": 0.163, "Highlight": "COCONUT NP Fallback Pool", "Class": "+ Flat DB"},
    {"Version": "V14", "LB": 0.193, "Highlight": "Sylva Confidence Gating (C1_HI=0.60)", "Class": "+ Gating"},
    {"Version": "V15", "LB": 0.205, "Highlight": "Dual-Channel Neutral Loss Consensus", "Class": "+ Consensus"},
    {"Version": "V16", "LB": 0.266, "Highlight": "Analog Propagation (711k Pool)", "Class": "+ Ch 2 Analog"},
    {"Version": "V17", "LB": 0.339, "Highlight": "FPNet Transformer + Bagging Ensemble", "Class": "+ Ch 4 Neural (Top 1)"}
]

df_prog = pd.DataFrame(versions)
print("=== VERSION PROGRESSION TO TOP 1 ===")
print(df_prog.to_string(index=False))

# Visualization
plt.figure(figsize=(10, 5), dpi=120)
plt.plot(df_prog["Version"], df_prog["LB"], marker='o', color='#10b981', linewidth=2.5, markersize=8)
for _, row in df_prog.iterrows():
    plt.annotate(f"{row['LB']:.3f}\n({row['Highlight'][:18]}...)", 
                 (row['Version'], row['LB']), 
                 textcoords="offset points", 
                 xytext=(0, 10), 
                 ha='center', fontsize=8, weight='bold', color='#1e293b')

plt.title("Enveda CASMI 2026: Leaderboard Progression to Top 1 (0.339)", fontsize=13, weight='bold', pad=15)
plt.xlabel("Notebook Version", fontsize=11)
plt.ylabel("Public MRR@25", fontsize=11)
plt.ylim(0.12, 0.37)
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.show()



#---CELL---

import numpy as np

def fast_bayes_ranking(candidate_fps: np.ndarray, predicted_logits: np.ndarray) -> np.ndarray:
    """
    Vectorized computation of Bayes Log-Likelihood ranking.
    candidate_fps: (N_candidates, 6930) binary array {0, 1}
    predicted_logits: (6930,) continuous float array from FPNet
    """
    # Direct dot-product: O(N * 6930) vectorized BLAS operation
    log_likelihood_scores = np.dot(candidate_fps, predicted_logits)
    return log_likelihood_scores

# Quick verification test
np.random.seed(42)
n_cands = 100
n_bits = 6930
dummy_fps = np.random.binomial(1, 0.05, size=(n_cands, n_bits)).astype(np.float32)
dummy_logits = np.random.randn(n_bits).astype(np.float32)

scores = fast_bayes_ranking(dummy_fps, dummy_logits)
print(f"Computed scores for {n_cands} candidates in real-time.")
print(f"Top 5 Candidate Scores: {np.sort(scores)[::-1][:5]}")

