TITLE: Dissecting the 0.32-0.34 plateau: what four probe submissions measured

BODY:

Hi everyone —

Like many of you, I plateaued around 0.32-0.34 with the analog-propagation + HistGBR ranker family. Instead of guessing what to improve, I spent four submissions as *measurement probes* (each a legal submission containing only real candidate SMILES, never filler). Sharing the numbers because they bound what any reranking trick can achieve.

**Setup.** Fork of the public analog-propagation baseline (pool = train structures + COCONUT + ChEBI/LIPID MAPS, ~712k, ±8.5 ppm window, 31-feature ranker). Visible test = 400 molecules. MRR@25 metric.

**The probes:**

| Probe | Submission content | Score | What it measures |
|---|---|---|---|
| A2 | only the library twin at rank 1 (1 guess) | **0.275** | twin correct in 110/400 rows (27.5%) |
| B2 | only the ranker's #2 candidate at rank 1 (1 guess) | **0.055** | ranker-#2 correct in 22/400 |
| C | only the original ranks 3-25, promoted (23 guesses) | **0.059** | ~24 answers live in ranks 3-25 |
| full | normal top-25 | **0.324** | baseline |

**What falls out:**

1. **The perfect-rerank ceiling of this pipeline's top-25 is ≈ 0.40** on the visible test (~160/400 answers present somewhere in the 25). We extract 0.324 = 81% of it; public-LB leaders at 0.36x are extracting ~90%. So either their ordering is near-perfect, or their pool contains more answers (higher ceiling). Either way:

2. **Any experiment that only reorders the existing top-25 fights over at most +0.076.** Pool quality is the bigger lever — consistent with the pool-size analysis in the analog-propagation notebook (bigger windows and blind PubChem expansion measurably hurt).

3. **Filler guesses poison a row (measured 0.000, twice).** Padding a row with junk SMILES to reach 25 candidates scored the whole submission 0.000 — invalid entries appear to be counted as ranked guesses at the grader. Single-real-guess rows are safe (probes A2/B2 scored exactly as expected). If your submission scores a suspicious hard zero, check for unparseable or filler strings.

4. **Structural proximity ≠ learned probability, and they capture different answers.** Reordering ranks 2-25 by Tanimoto-to-twin instead of ranker probability scored **0.324 again — an exact tie** — yet the selected tail sets differed in ~90% of rows. Two different answer sets, same total. This is an argument for blending the signals rather than choosing one.

5. **Ranker seed noise is ±0.006.** HistGBR with random_state=None gave 0.292 vs 0.298 on identical submissions (this is also noted in the analog-propagation notebook). Pin seeds and average; differences under ~0.01 on the LB are noise, not signal.

**Open question for the community:** has anyone measured the "answer present in top-25" rate for an expanded pool? I'm trying to estimate how much of the missing ~60% is pool-limited (class 2 reachable by better retrieval) vs genuinely class 3.

Good luck everyone — see you on the private LB.
