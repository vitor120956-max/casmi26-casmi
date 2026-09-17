# CASMI 2026 — strategy & landscape (living notes)

## MODO DE OPERAÇÃO (decisão do user, 17/09)
**ALL-IN, alvo top 5** (top 3+ = bônus). Cadência 3–5 experimentos/semana.
Backup completo no GitHub (repo privado `casmi26-casmi`) + `HANDOFF.md` na raiz do
workspace para retomada por qualquer agente. Probabilidades calibradas declaradas ao
user: top5 ~8–18%, top3 ~5–10% (all-in); ele aceitou o risco conscientemente.

## Submission mechanics (Code Competition)
- Submissions ONLY from notebooks: input = competition data → write
  `submission.csv` to `/kaggle/working` → **Save Version → Save & Run All** →
  open the notebook viewer → Output → **Submit**.
- 5 submissions/day per team; select up to **2** for the final leaderboard
  (screenshot 2026-09-16: 0/2 selected). If you pick fewer, Kaggle auto-selects
  your best scored ones — so "Auto-selection candidates" ON is a safe hedge.
- Rerun at deadline swaps the visible test (train-derived!) for the hidden
  ~400-molecule timsTOF set. Public LB ≠ final; don't overfit it.

## Public leaderboard snapshot (2026-09-16, from /code page)
| Score | Notebook | Approach family |
|---|---|---|
| 0.319 (claims 0.336+) | beraterolelk "⚡ [0.336+ SOTA] Analog Ranker" | analog ranking |
| 0.299 | prvsiyan "Analog Propagation baseline" | analog propagation |
| 0.259 | evgendvorkin "Enveda CASMI 2026" | ? |
| 0.241 | denpugovkin "We Mutated SMILES…" | SMILES mutation / analogs |
| 0.239 | haideptry "Fast Spectral Cosine Baseline" | binned cosine retrieval |
| 0.227 | plagiagia "analog propagation ranker" | analog propagation |
| 0.18 | foysalemonshanto (copy of haideptry) | cosine retrieval |
| 0.16 | lucifer19 "SHARDWRIGHT" | fragment assembly |
| 0.155 | dmitriigluzdov "EDA, Search, Model" | retrieval+ |
| 0.14 | avikdas567 "Physics-Informed Spectral Transformer" | de novo transformer |
| pinned | inversion "CASMI denovo tutorial notebook" | host de novo tutorial |

Read: retrieval-only ≈ 0.18–0.24 (our tier-1 lives here). The 0.25–0.34 band is
**analog propagation**: retrieve neighbors → expand to structural analogs
(mass-shift / SMILES mutation) → rank. De novo transformers alone trail (0.14–0.16).

## External assets
- Drive folder (user-provided): `dreams-pytorch-default-v1.tar.gz` (415.5 MB) =
  DreaMS pretrained spectrum-embedding weights (GeMS-pretrained; listed on the
  Data page as a resource) + `sample_submission.csv`.
  Usage path: upload weights to a **Kaggle dataset** and attach as notebook
  input (rerun has no internet). Rules allow freely/public pretrained models.
  Too big to persist in the agent workspace (snapshot cap ~128 MB) — keep on
  Drive/Kaggle, not here.

## Plan vs status
- [x] Tier 1: binned-cosine retrieval + mass filter (`baseline_retrieval.ipynb`, smoke-tested)
- [x] 2026-09-17: tier-1 executado no Kaggle (notebook7fb09d9a5d): index 1.383.278 espectros /
      94.998 estruturas, nnz 30.2M (~0.5 GB), test 1213 espectros / 400 moléculas,
      398/400 com candidatos, submission.csv (400,2) VÁLIDO. Aguardando commit + score.
- [x] 2026-09-17 scores públicos: v2 (tier-1 NP-libs) = 0.097; v3 (variante B: +enveda-180
      + prior NP 0.05) = 0.101. Rank ~281/309. Hipótese enveda-180 REFUTADA (delta +0.004).
      Gap p/ 0.239 está no método de similaridade/agregação → dissecar notebooks top.
- [x] Auditoria de conta: 8 kernels antigos (2026-08-15, inertes); GPU 30h/TPU 20h intactas
      (refresh 09-19); team solo; entry OK; 0/2 finais selecionadas (auto-select ON);
      3 submits restantes no dia. CLI Kaggle operacional via API key (delegada pelo user).
- [x] 2026-09-17 fork SOTA: puxados códigos públicos (haideptry 0.239 / prvsiyan 0.299 /
      beraterolelk 0.319). Ecossistema compartilhado de datasets (prvsiyan: fp-models,
      ranker-features, coconut, chebi; wheel rdkit offline). HEAD público do beraterolelk
      QUEBRADO (N_FEAT 25 vs ranker npz 31) → patch: refit do GBM em X[:, :25].
      Kernel novo victor120956/casmi26-analog-ranker-fork (GPU T4, ~65 min/run):
      v1 ERROR (schema), v2 COMPLETE. Submissão ref 56295650 (v2) enviada; scoring PENDING
      (fila lenta; arquivo validado localmente OK). Restam 2 submits no dia.
- [x] 2026-09-17 manhã: score do fork v2 = **0.306** (rank 83/408). Fork v3 pushado:
      xfeat restaurado (schema 31 colunas), ensemble 8 GBMs (seeds 0-3 × priors 0.30/0.60),
      N_ANALOG=100, P_SIM=4. Run ~70 min COMPLETE; submission ref pendente na fila de
      scoring (arquivo validado). Resta 1 submit hoje.
- [ ] Próximo contato: conferir score v3; se >0.306, adotar como base; senão, manter v2
      como final candidate #1 e usar v3 só se trouxer ganho privado-plausível.- [ ] R&D próprio (variante C): spectral-entropy similarity + analog mass-shift rerank no
      nosso índice esparso (independente dos assets de terceiros).
- [x] 2026-09-17 DIAGNÓSTICO-CHAVE (log do fork v3): no test VISÍVEL, 100% das moléculas
      têm library hit sim>0.85 (mediana ~1.0) → perda pública = RANKING (isômeros na
      janela ppm), não cobertura; hidden (classes 2/3) = canais analog/de novo + prior NP.
      Fila: v4 = high-confidence override (sim≥0.90 → rank 1 incondicional) após score v3.
- [x] Decisão de portfólio (user delegou): 100% CASMI agora; side-comp $3k só se top20
      consolidado em 01/11; scouting de MERGE em nov-dez = alavanca #1 p/ medalha.
- [ ] Tier 1.5: holdout eval on the 250 `enveda-np-examples` compounds (measure before changing anything)
- [ ] Tier 2: analog propagation on top of retrieval (mass-diff / SMILES-mutation candidates, rerank) → target public ≥ 0.25
- [ ] Tier 2.5: DreaMS embeddings replace/augment binned cosine
- [ ] Tier 3: de novo (transformer / fragment assembly) for class-3 molecules; blend into ranks 10–25
