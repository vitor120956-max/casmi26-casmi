# ★ AGENT HANDOFF — CASMI 2026 (Enveda) ★
**Data: 2026-09-21 ~10:45 BRT (13:45 UTC). Autor: agente anterior (Arena.ai Agent Mode). Destinatários: próximo agente + usuário Victor.**
**Histórico cronológico detalhado: `HANDOFF.md` (log operacional dia-a-dia). Este documento = estado definitivo estruturado para transferência.**

---

## 0. PRIMEIROS PASSOS DO NOVO AGENTE (nesta ordem)
```bash
cd /home/user && bash arm.sh          # rearma kaggle/git/gh pós-restart (idempotente, ~10s)
tail -30 day_watch.log                # últimos eventos operacionais
ls wave_backup/ wave2_assets/ recon_log/ refs/
du -sh harness_data                   # se ~63M → bash harness_download.sh (background, ~13 min, 3.6GB)
git log --oneline -8                  # confirma sincronia com origin/main
```
Se o workspace NÃO for o mesmo: `git clone https://github.com/vitor120956-max/casmi26-casmi.git` — o repo tem TUDO que persiste (docs, scripts, CSVs de submissões, refs de notebooks, mapas kitopl, pins). Dados grandes são re-baixáveis (comandos na §9).

---

## 1. MISSÃO
- **Competição**: Kaggle `enveda-CASMI26-molecule-id-mass-spectra` — "Enveda CASMI 2026 – Molecule Id From Mass Spectra". Predizer SMILES a partir de espectros LC-MS/MS. Featured, $50k, 1056 times.
- **Formato submissão**: CSV longo `molecule_id,smiles`; smiles = até 25 candidatos joined por `;` em ordem de rank.
- **Métrica**: MRR@25. Correto = InChIKey14 idêntico após canonização de tautômero RDKit (pin 2026.03.3). Erros de estereo/tautômer são perdoados pela canonização.
- **Prazos**: escolha das finais ~**07/dez/2026**; fim da competição **14/dez/2026**. Máx **2 submissões finais**.
- **Objetivo do usuário (mandato 17/09)**: "almejar o top 5 pelo menos" — cadência all-in de 3–5 experimentos/semana.
- **Posição atual**: rank **183/1056**, best score **0.332** (mediana da família ~0.329). Corte top-5 = **0.365**. Top-1 = 0.409.

## 2. O USUÁRIO (Victor) — ORDENS PERMANENTES (respeitar SEMPRE)
1. **PT-BR** nas respostas (ele escreve em português). Conciso, veredito no TOPO, nunca parede de texto. Ele já interrompeu 6 respostas por verbosidade ou polling silencioso.
2. **NUNCA sleep/poll dentro do turno** — checagens one-shot; detalhes vivem em arquivos/logs. (Ele abortou 3 loops de sleep e disse "Demorou demais".)
3. **Mobile-first**: Android Chrome + desktop Windows Chrome. Passos numbered/tap-level com nomes exatos de menus/botões e URLs em code blocks. Screenshot sem texto = "o que eu faço agora".
4. **Não depender do timing dele**: ele perdeu check-in uma vez por causa do trabalho. Todo estágio tem que ser resumível a partir de logs/lista de submissões em qualquer próximo contato arbitrário.
5. **Horários**: trabalha durante o dia (~8–18h BRT), disponível à noite. Padrão "vai" = ele manda msg ~21:05 BRT para disparar submissões das 21:00 BRT (reset de slots 00:00 UTC).
6. **DISCIPLINA ANTI-SORTE** (palavras dele 20/09: "não quero contar muito com a sorte"; 21/09: "a gente não pode ficar cometendo erros nesse projeto"): nenhuma decisão por leitura única; finais por **medianas replicadas**; alavancas estruturais > caçar ruído; **verificar tudo antes de push/submeter** (protocolo §11).
7. **GitHub + HANDOFF a cada passo** (standing desde 17/09). Repo: `https://github.com/vitor120956-max/casmi26-casmi.git` (conta `vitor120956-max`).
8. **Vasculhada noturna** (standing desde 20/09: "no final da noite é sempre bom dar uma vasculhada"): rodar `recon_sweep.sh` + download do LB TODA noite; reportar kernels/datasets/scores novos.
9. **SOLO para sempre**: plano de equipe multi-lane ABANDONADO (17/09); plano de conta-proxy de amigo MORTO permanente (19/09). Nenhuma conta de terceiro toca código/submissões/dados.
10. **Agente NÃO publica em fórum nem age na conta** (ToS) — quem executa é o USUÁRIO; agente fornece texto exato + guia tap-level + caminho de recuperação, à prova de erro com checkpoints.
11. **Segurança**: nunca aceitar senhas. `~/.kaggle/kaggle.json` foi anexado DE PROPÓSITO — fica até o fim do projeto; usar SÓ para esta competição; reportar erros crus; nenhuma outra ação de conta. Mesma chave no Termux do usuário (escolha dele, mesmo escopo). O `ksubmit.py` do Termux nunca foi auditado (pendência).
12. **Sem background em química** assumido. Não presumir deliverable além do que ele entregar (contexto: "exploring").
13. **Segredos**: design de derivatives+frag, DreaMS e cadência operacional ficam SECRETOS até 14/dez; publicar só medições. (Post de discussão foi publicado pelo usuário em 19/09.)

## 3. REGRAS DA COMPETIÇÃO (operacionais)
- **5 submissões/dia**, reset **00:00 UTC** (= 21:00 BRT). Hoje (21/09 UTC): 5/5 já usadas às 00:02 UTC (onda 1) → **próximos 5 slots: 22/09 00:00 UTC = segunda 21:00 BRT**.
- Code competition: submeter = re-run do kernel no servidor (~50–60 min p/ sair o score). Erros 400 NÃO consomem slot.
- Kernel: ≤9h runtime, **sem internet em runtime**, GPU T4×2, **máx 2 sessões GPU concorrentes por conta** (3º push → "Maximum batch GPU session count of 2 reached").
- **`enable_gpu: true` OBRIGATÓRIO** nos kernels desta competição (false → dados da competição não anexam).
- LB público ≈ **132 moléculas** (test privado = 400). Regras de leitura na §4.

## 4. HISTÓRICO COMPLETO DE SCORES (nosso) + REGRAS DE LEITURA
| # | Config | Score | Ref |
|---|--------|-------|-----|
| 1 | own v2 | 0.097 | — |
| 2 | own v3 | 0.101 | — |
| 3 | fork v2 | 0.306 | — |
| 4 | fork v3 | 0.324 | — |
| 5 | v6 anomalous | 0.324 | — |
| 6-7 | junk ×2 | 0.000 | — |
| 8-10 | A2 / B2 / C | 0.275 / 0.055 / 0.059 | — |
| 11 | v12 TIE | 0.324 | — |
| 12 | canonical as-is | 0.320 | — |
| 13 | fusion v2 | 0.320 | — |
| 14 | knobs v3 | 0.322 | — |
| 15 | fp-v4 | 0.323 | — |
| 16 | fp-late | **0.312 REGRESSÃO — nunca ressubmeter** | — |
| 17 | **fp-v2-models (ADOPTED)** | **0.328** | 56374189 |
| 18 | canonical replica | 0.320 | — |
| 19-20 | v2-models replicas | 0.328 / 0.328 (3/3 spread zero) | 56375929 / 56375933 |
| 21 | WAVE1 haideptry-probe (claim 0.339) | **0.290 FALHOU** | 56408390 |
| 22 | WAVE1 berat-probe (claim 0.341) | **0.236 FALHOU FEIO** | 56408413 |
| 23 | WAVE1 megayak2 (claim 0.337) | **0.323 FALHOU** (= starkhushi 0.323, 2 leituras indep.) | 56408437 |
| 24 | WAVE1 seedswap2 (0.328 c/ seeds 4-7) | **0.332** (+0.004 = ruído de seed) | 56408465 |
| 25 | WAVE1 priors2 (priors .55/.65/.75) | **0.329** (+0.001 = priors inertes) | 56408488 |

**LINHAGEM ADOTADA (finals-safe #1)**: engine canonical do prvsiyan ("Analog Propagation") + dataset `prvsiyan/casmi26-fp-models-v2` = **0.328 com 3 réplicas idênticas**. Família: 0.328–0.332.
**REGRAS DE LEITURA**: (a) mesma config+mesmas seeds = determinismo exato (arquivos byte-idênticos); (b) só seeds mudam = ±0.004 (nosso) a ±0.017 (megayak); (c) <0.02 no LB público (132 mols) = TIE, não confiar em transferência; (d) curva de fp-versions v2>v4>v6>late provavelmente genuína mas perto do limite de confiança; (e) **TODO claim público ≥0.34 FALHOU em replicação** (onda 1) — doutrina confirmada.

## 5. ★ DESCOBERTA: CONVERGÊNCIA DE RANK-1 (20/09, auditada)
- Comparação offline de 7 CSVs de submissão (`wave_backup/`): **TODOS os engines sérios cravam o MESMO rank-1 em 400/400** moléculas teste (única exceção: berat, 398/400 — 2 trocas de isômeros: m_773a95 amina 2ª↔3ª, m_e8d835 furano).
- O jogo inteiro mora nos **ranks 2–25**: overlap de conjuntos top-25 entre engines = 2.8–15.8% (base↔berat 2.8%, base↔seedswap 15.8%, base↔megayak-blend 10.8%, base↔canal-pv-do-megayak 56.0%).
- Faixa LB 0.27–0.34 = **piso compartilhado de rank-1 (~0.27) + qualidade de deep-rank**. Scores junk (0.055) eram os únicos que quebravam o rank-1.
- Deep-rank é dirigido pelo **canal fp** (spectrum→fingerprint, Bayes f·z) + ranker GBM → fp melhor / fusão melhor = a alavanca. Risco das finais no rank-1 é BAIXO (consenso).
- Bônus: output do megayak2 trouxe os canais separados (`submission_ours.csv`, `submission_pv.csv`) — matéria-prima de fusão, em `wave_backup/`.

## 6. ★ HIPÓTESE DE TRABALHO: EXPANSÃO DE POOL PUBCHEM = O SALTO 0.38+
- O notebook do prvsiyan (nosso canon — markdown completo dentro de `prvsiyan_fork/canon_fpv2.ipynb`) documenta a álgebra: pool atual (COCONUT+ChEBI+LIPIDMAPS, 712,199 estruturas) → teto `A+B ≈ 0.162+0.271 ≈ 0.43` com ranker perfeito. Class-1 ≈16% do test (saturado, A=f₁≈0.162); Class-2 27–72% (B=f₂·recall).
- **"PubChem pool expansion, top-50 isômeros por f·z" = "a jogada de maior valor não testada"** (palavras dele). Break-even: paga iff ρ'<0.52 (ρ = cobertura COCONUT das respostas Class-2; bracket medido 0.377–0.996). Validação local NÃO consegue medir (recall local já é 100% → só vê diluição, nunca o ganho de recall) → decisão por álgebra + submissão.
- **NOSSO CANON JÁ TEM O CÓDIGO**: `PC_TOPK = 50`, `load_pcstore()` (glob `/kaggle/input/**/mass_sorted.npy` + `order.npy` + `off.npy` + `ln*`), `pubchem_extra()` — **mas roda OFF** ("PubChem store not attached") porque nunca anexamos o dataset store.
- Candidato público: `ngdminh31/casmi26-pubchem-tier2-fp-public` (subido 19/09 14:09; `tier2_fp.npy` 6.3GB + `tier2_mass.npy` 57.8MB + `tier2_meta.pkl` 618MB). **Formato ≠ mass_sorted.npy → precisa adaptação** (ver §12.A.3).
- Timeline compatível: ngdminh31 sobe sábado 14:09 → Ozymandias 0.363→0.396 (dom 00:00:57, bot) → Randy 0.357→0.388 (dom 13:20) → Udam 0.383 (dom 14:49) → Ozy **0.409** (seg 03:36) ≈ teto 0.43. Todos os três submetem diariamente (Ozy: 30 subs).
- **m1b-36k DESPRIORIZADO**: o dataset `rogersjohnson/casmi26-fp-merged-m1b-36k` (dom 12:49) = o modelo m1@36k do PRÓPRIO prvsiyan; o A/B single-variable dele no LB: m1@36k merged-only = **0.311** vs m1@24k+s2 (o NOSSO combo fp-v2) = **0.330**. Rogers Johnson tem 0.328 com 2 subs. Não é o salto do Randy.
- prvsiyan **privatizou o kernel** (pull = 403) e parou de submeter em 19/09 (#133, 0.335, 17 subs).

## 7. LB SNAPSHOT 21/09 ~13:40 UTC (csv no repo: `lb_20260921_morning.csv`)
| # | Time | Score | Subs | Última |
|---|------|-------|------|--------|
| 1 | Ozymandias31415 | **0.409** | 30 | 21/09 03:36 |
| 2 | Randy | 0.388 | 11 | 21/09 12:06 |
| 3 | Udam Liyanage | 0.387 | 23 | 21/09 06:37 |
| 4 | Alperen Aydın | 0.366 | 19 | 21/09 10:16 |
| 5 | Naoism | 0.365 | 17 | 21/09 01:07 |
| 27 | NEU | 0.347 | 20 | 21/09 11:07 (escalando) |
| 57 | haideptry | 0.339 | 18 | 21/09 04:15 (conta dele sustenta o claim; o NOTEBOOK público replica 0.290 → notebook≠submissão real) |
| 104 | starkhushi | 0.337 | 16 | 19/09 |
| 111 | megayak (인공저능연구소) | 0.337 | 20 | 20/09 20:51 |
| 133 | prvsiyan | 0.335 | 17 | 19/09 18:11 |
| **183** | **NÓS** | **0.332** | 25 | 21/09 00:03 |
| 310 | Rogers Johnson | 0.328 | 2 | 20/09 |
| 343 | kito_pl | 0.328 | 8 | 21/09 11:21 (ativo) |
| 388 | Berat Erol ÇELİK | **0.319** | 7 | 20/09 — **a conta DELE nunca chegou no 0.341 do título** |

## 8. ONDA 1 — VEREDITO (submetida 21/09 00:02 UTC, disparo manual com gatilho humano)
Ver tabela §4 (refs 56408390–56408488). Interpretações:
- **Nenhum claim público alto replicou.** berat 0.341→0.236 (−0.105); haideptry 0.339→0.290 (−0.049); megayak 0.337→0.323 (−0.014, idêntico ao 0.323 independente do starkhushi → two-ranker blend está MORTO por 2 leituras).
- seedswap2 0.332 = régua de ruído de seed (+0.004); priors2 0.329 = priors inertes.
- A disciplina anti-sorte do usuário se pagou na mesma noite: teríamos adotado um engine 0.236 como "0.341".

## 9. MAPA DO WORKSPACE / REPO
**Persistidos no git (pequenos):**
- `AGENT_HANDOFF.md` (este), `HANDOFF.md` (log cronológico completo), `day_watch.log` (log operacional compartilhado), `wave_submitted.txt` (ledger de submissões — fonte anti-double-submit)
- `wave_backup/` — **8 CSVs coroa**: base_v2models (0.328×3), seedswap2, megayak2 (+_ours +_pv), berat, haideptry, priors2
- `wave2_assets/kitopl/` — **aceleradores do harness offline**: `ik14_map.csv` (275,811 linhas: inchikey14→metric_ik14 + heavy_atom_comp + tautomer_shifted = canonização métrica pré-computada), `library_map.csv` (inchikey14→n_libs/n_spectra/libs = **labels de classe** p/ moléculas train), `collapsed_structures.csv` (1542 grupos tautômero), `np_examples_contamination.csv` (250 enveda-np-examples × libs contaminantes: drug_plus,gnps,massbank,mona,msdial,pluskal_ms2,riken = o leak do FPNet documentado)
- `wave2_assets/pins/` — `itsuki89/casmi26-ranker-features-v4-pin` (espelho version-pinado = seguro anti-drift) + `dionet2/casmi26-ranker-features-big` (harness CV 1199-query)
- `refs/` — notebooks puxados: `starkhushi_frag/` (Fragmentation Check, rodou 21/09), `alexchilton_tut/` (tutorial "0.342 scorer"), `flexonafft/` (Strong Retrieval Clean Ranking, 6 votos), `berat_sota/` (+berat_code.py), `haideptry/0-339-top-1-.../`, `haideptry_cosine/` (V17), `megayak_nine/` (one-engine-nine-scores, LIDO por completo), `megayak_engine/`, `prvsiyan_latest/` (VAZIO — kernel 403 privado)
- `prvsiyan_fork/canon_fpv2.ipynb` — **config adotada 0.328** (engine prvsiyan + fp-v2; contém o markdown de conhecimento medido dele + código PubChem OFF)
- `prvsiyan_out_v2models/` — output vencedor (md5 `b5492c3fc6da9ae871bc8cd5cec87059`)
- Scripts: `arm.sh` (rearme pós-restart), `precheck.sh` (gate de push), `verify_out.sh` (gate de submissão), `recon_sweep.sh` (vasculhada noturna → `recon_log/`), `manual_wave.py` (disparo idempotente de onda), `submit_wave.sh` (auto-disparo — corrigido p/ `num_allowed_now`; NÃO confiar: hibernação mata), `score_poll.sh`, `harness_download.sh`, `finish_line.sh`/`priors_watch.sh` (aposentados), `set_probe.py`
- `kpush_*` dirs (kernel-metadata + probe.ipynb por probe): ativos/usados `kpush_berat`, `kpush_haideptry`, `kpush_seedswap2`, `kpush_megayak2`, `kpush_priors2` (todos enveda-corrigidos); `kpush_hello` (diagnóstico, deletável); aposentados `kpush_{megayak,seedswap,priors}` (metadata velho c/ typo)
- `drafts/derivatives_frag_design.md` — spec do frag-harness (derivativos + fragmentação; starkhushi mediu +0.033 só do canal frag)
- `lb_20260920_2141.csv`, `lb_20260921_morning.csv` — snapshots do LB
- `casmi26/` (scorer local antigo), `fork_bera/`, DreaMS dataset (468MB, ideia de canal parkada)

**Re-baixáveis (NÃO persistem — snapshot cap ~128MB):**
```bash
export PATH="$HOME/.local/bin:$PATH"
mkdir -p wave2_assets
kaggle datasets download rogersjohnson/casmi26-fp-merged-m1b-36k -p wave2_assets --unzip   # fp_merged_m1.pt 144MB
kaggle datasets download megayak/casmi26-simulated-ranker-rows -p wave2_assets --unzip      # ours_fpnet_{merged_26k,single_16k}.pt + sim_rank_rows_{fp16k,fppair,nofp}.npz + README
bash harness_download.sh   # harness_data/ 3.6GB: train.parquet 2.9G + test 4.7M + coconut/chebi/ranker-features/fp-models-v2 (~13 min)
```

## 10. ERROS COMETIDOS — LISTA COMPLETA (pedido explícito do usuário)
**Estratégia/competição:**
1. 2 submissões junk 0.000 (formato errado) no início.
2. fp-late 0.312 = regressão (nunca ressubmeter).
3. Fusion v2 = tie (0.320); knobs v3 0.322 = fork-knobs inertes/nocivos (cap-80 de forks custa −0.055 previsto e derruba 24% do recall Class-2 — medição do prvsiyan).
4. Teoria DEMOTE_TWIN do v6 falsificada.
5. Port de offset/recalibração CANCELADO (megayak row6: ganha 250/250 offline, perde no LB).
6. "PubChem DEAD" foi conclusão prematura (teste do starkhushi foi pool CHEIO; top-50 gated é outra aposta — álgebra do prvsiyan, break-even ρ<0.52).
7. Quase confiar em claims públicos (0.339/0.341/0.337) — TODOS falharam em replicação.
8. Plano de equipe multi-agente abandonado → solo; plano de conta de amigo → morto permanente (ToS).
9. Diversificação de portfólio (ARC-AGI-2/3, Paper Track, RSNA knee, Biohub, Kaggriculture, comps $3k) → tudo morto; single-thread CASMI; revisitar comps $3k ~1/nov.
**Kaggle API/CLI:**
10. ★ **TYPO `envida` vs `enveda`** em 6 kernel-metadata.json clonados → 7h perdidas + 9 versões de kernel ERROR (`FileNotFoundError: test.parquet`). O warning do servidor IMPRIMIA o slug inválido literalmente desde o início. Lições: (a) warning é DADO — ler literalmente; (b) clonar metadata = diff obrigatório contra golden (`kpush_berat/kernel-metadata.json`); (c) duas teorias falsas foram construídas antes da causa real (kernel "tainted" e capacidade GPU) — bissecionar até a raiz ANTES de construir workaround.
11. `CreateCodeSubmission 400 "Did not find provided Notebook Output File"` → fix: `os.chdir(dir_do_output)` + `'submission.csv'` RELATIVO (path absoluto quebra).
12. `api.competition_submit()` é ERRADO p/ code comps → `competition_submit_code(file, msg, comp, kernel=, kernel_version=)`.
13. CLI novo: `kaggle kernels output REF -p DIR` (positional `.` = "unrecognized arguments"); LONG flags only; `kernels pull REF -p dir`.
14. ★ API rename silencioso: `numAllowedNow` → **`num_allowed_now`** (kaggle 2.x) — teria abortado a onda às 21:00 sem erro visível. `publicScore` → `public_score`. SEMPRE testar leitura de API antes de automatizar.
15. Máx 2 sessões GPU concorrentes → fila com retry; bug do queue_push3: contou push COM WARNING como sucesso (toda saída de push deve ser grepada).
16. `enable_gpu: false` → competition sources não anexam (megayak v1-v3).
17. CLI não pineia versão antiga de dataset → risco de drift nas FINALS (mitigar: re-replicar pré-finais ou re-upload congelado dos assets como dataset nosso).
18. Kernel privado = 403 (prvsiyan) — respeitar, não contornar.
**Sandbox/ops (Arena/e2b):**
19. ★ **Hibernação entre turnos mata processos de fundo** (a onda morreu 4×; vigias idem) → **submissões com gatilho humano** ("vai" do usuário → disparo manual no turno via `manual_wave.py`). NUNCA depender de timer do sandbox.
20. ★ **Restarts revertem .git** (identity, remote, HEAD) e limpam pip/`/tmp`/arquivos >~128MB (train.parquet 2.9GB perdido 2×; wave2_assets 487MB perdido) → ritual `arm.sh` + `git reset --hard origin/main` no início de turno; commitar artefatos pequenos IMEDIATAMENTE; re-baixar dados pesados por sessão.
21. Quase-desastre git: `git add -A` com 3.6GB de dados → `.gitignore` endurecido (harness_data/, probeout_*/, wave2_assets grandes, *.parquet, logs).
22. Push rejeitado pós-rollback (3×) → padrão: fetch + `reset --hard origin/main` + re-aplicar seções novas (salvar em /tmp antes).
23. Sleep até meia-noite → data errada no dia seguinte; nunca sleep-poll in-turn.
24. `fetch_page` proxy quebrado desde 19/09 (SignatureDoesNotMatch) → usar CLI/API ou pedir paste ao usuário.
25. Termux do usuário com kaggle travado em 1.6.17; `ksubmit.py` dele nunca auditado.

## 11. PROTOCOLOS OBRIGATÓRIOS (nascidos dos erros acima)
1. **ANTES de todo push**: `bash precheck.sh <kpush_dir>` — FAIL = não pushar. (Compara competition slug com GOLDEN `enveda-CASMI26-molecule-id-mass-spectra`, enable_gpu=true, id, code_file parseável, formato dos dataset slugs.)
2. **DEPOIS do push**: ler o output LITERALMENTE — "not valid competition sources"/"error" = FALHA (nunca contar como sucesso).
3. **ANTES de toda submissão**: `bash verify_out.sh <probeout_dir>` — PASS = 400 linhas, cols `molecule_id,smiles`, 0 vazias, 0 placeholder CCO, sem Traceback no log. FAIL = não submeter.
4. Clonou metadata → **diff contra golden** (`kpush_berat/kernel-metadata.json`).
5. Antes de planejar submissões: `competition_get_submission_limits` (num_allowed_now!) + listar submissões recentes + checar `wave_submitted.txt` (anti-double-submit; fonte de verdade = lista no servidor, tags `PROBE-WAVE<N>:<tag>` na description).
6. GPU: máx 2 sessões; pushar 1-2 por vez com status-gate; NUNCA pushar c/ pool ocupado sem necessidade.
7. **Reconexão pós-restart**: `bash arm.sh`; checar `day_watch.log`, status dos kernels (`kaggle kernels status victor120956/<slug>`), `du -sh harness_data wave2_assets`.
8. **Toda noite**: `bash recon_sweep.sh <label>` + download LB (`kaggle competitions leaderboard enveda-CASMI26-molecule-id-mass-spectra -d` → zip → csv) + reportar novidades ao usuário.
9. Mecânica de submissão (template testado):
```python
import os
from kaggle.api.kaggle_api_extended import KaggleApi
api = KaggleApi(); api.authenticate()
os.chdir('/home/user/<probeout_dir>')
api.competition_submit_code('submission.csv', 'PROBE-WAVE<N>:<tag> — <descrição>',
    'enveda-CASMI26-molecule-id-mass-spectra',
    kernel='victor120956/<slug>', kernel_version=<N>)
```
10. A cada passo relevante: entrada no `HANDOFF.md` + `git add -A && git commit && git push`.

## 12. O QUE FALTA FAZER — PASSO A PASSO
### A. HOJE (segunda 21/09) — Onda 2 mira os slots das 21:00 BRT
1. `bash arm.sh`; garantir harness baixando (`bash harness_download.sh` se `du -sh harness_data` ≈ 63M); re-baixar `wave2_assets` grandes se ausentes (§9).
2. **LER** (já em disco): `refs/alexchilton_tut/` (o que compõe um 0.342?), `refs/flexonafft/` (strong retrieval/clean ranking, 6 votos), `refs/starkhushi_frag/` (fragmentation check — cruza com `drafts/derivatives_frag_design.md`; canal frag valeu +0.033 p/ starkhushi).
3. **Store PubChem**: (a) procurar store pronto no formato do canon: `kaggle datasets list -s pubchem`, `-s mass-sorted`, `-s casmi26 store`; inspecionar `ranjithch/casmi26-pubchem-candidates` (156KB — o que é?); (b) se não houver: inspecionar `ngdminh31/casmi26-pubchem-tier2-fp-public` (baixar `tier2_meta.pkl` 618MB p/ entender estrutura) e escolher: **adaptar o loader DENTRO do kernel** p/ consumir tier2_* via mmap (caminho mais rápido, tudo server-side) OU converter localmente e **re-upload como dataset nosso congelado** (livre de drift, mais pesado); (c) ler `load_pcstore()`/`pubchem_extra()` inteiros no canon antes de tocar.
4. **Montar `kpush_pubchem/`**: cópia EXATA de `prvsiyan_fork/canon_fpv2.ipynb` (config 0.328) + loader adaptado + `dataset_sources` += store. `bash precheck.sh kpush_pubchem` → push com pool GPU livre → status até COMPLETE (~50-90 min, store é grande) → download (`kaggle kernels output REF -p probeout_pubchem`) → `bash verify_out.sh`.
5. **ONDA 2 — segunda 21:00 BRT** (gatilho humano "vai" ~21:05; usar padrão `manual_wave.py` com tags `PROBE-WAVE2:<tag>`; 5 slots). Prioridade sugerida: (1) canon+PubChem-top50; (2) variante PubChem (PC_TOPK=25 ou gating diferente — A/B da diluição); (3) melhor insight das leituras do passo 2; (4) canal fp alternativo (megayak `ours_fpnet_merged_26k` como canal extra leak-free — o nine-scores dele mostra o canal fp dominando; m1b-36k sozinho NÃO, ver §6); (5) fusão RRF/mediana dos rankings de `wave_backup/` SÓ se o harness offline apoiar.
6. **Noite**: `recon_sweep.sh` + LB + `score_poll` (ou checagem manual no próximo contato) + HANDOFF/git.
### B. ESTA SEMANA
7. **Harness offline** (agora acelerado pelos mapas kitopl): scorer local em subconjunto do `train.parquet` (200–500 moléculas) usando `ik14_map.csv` (canonização métrica sem RDKit lento) + `library_map.csv` (labels Class-1/2) → medir variantes de canal fp, frag e fusão por classe ANTES de gastar slot. Spec do frag-harness: `drafts/derivatives_frag_design.md`.
8. **Recall/derivativos** (recomendação #2 do prvsiyan): enumeração direcionada (glicosilação/hidroxilação/metilação de scaffolds COCONUT) — testar offline; "naive derivatives" já morreu no LB do starkhushi (0.335), então precisa ser gating inteligente.
9. Se PubChem pagar na onda 2: iterar store (qualidade/tamanho), sweep de PC_TOPK, **re-sweep de class prior e tree depth** (prvsiyan: re-sweepar hiperparâmetros SEMPRE que um canal melhora — o ótimo de prior moveu 0.50→0.45 quando o canal fp melhorou).
10. Mais seeds no ranker (bagging = redução de variância grátis contra noise floor 0.0072 — medição prvsiyan).
11. **Vigiar**: ressurgimento do prvsiyan (kernel 403 pode voltar público), stores PubChem novos no formato mass_sorted, cadência Ozy/Randy/Udam, subida do NEU (#27), atividade do kitopl (8 subs, ativo), threads de fórum (IDs na §13; agente não navega bem — pedir paste ao usuário).
### C. FINAIS (até 07/dez escolha, 14/dez fim)
12. ≤2 finais por **medianas replicadas** (mín. 2–3 leituras idênticas da config exata). **Re-replicar antes das finais** (drift: CLI puxa sempre a última versão dos datasets) — considerar congelar assets críticos re-upando como datasets nossos versionados.
13. Finals-safe #1 atual = linhagem canonical+fp-v2 (0.328×3). Substituir só por linhagem replicada superior.

## 13. INTELIGÊNCIA EXTERNA (resumos que não estão em arquivos)
- **megayak one-engine-nine-scores** (lido por completo; refs/megayak_nine/): 9 submissões do mesmo engine: ranker-próprio-only 0.272×3 (determinismo); ranker-prvsiyan-only ±10ppm 0.333; blend 0.65prv+0.35mega 2-seed **0.337** (melhor deles); MESMO blend 4-seed 0.320 (swing de seed −0.017); blend 0.80 0.331; recenter −1.45ppm ±8 0.312/0.329/0.322 (**offset perde no LB apesar de 250/250 offline**); fp leak-free 0.327/0.326. Leak FPNet: treinado com estruturas de biblioteca → ~+0.3 MRR em gnps/mona/massbank (enveda-np-examples NÃO afetado); weights leak-free = `megayak/casmi26-simulated-ranker-rows`; offline Class-2 sim MRR 0.655→0.689 (5-fold grouped CV); engine ~56 min CPU. Regra deles: ±0.02 = tie.
- **prvsiyan (markdown no nosso canon)** — tabela de progresso 0.151→0.335 e DEAD ENDS medidos: PubChem pool cheio 0.52→0.35 (diluição; mas top-50 gated = aposta algébrica); consensus-fp-averaging 0.43 vs max-over-analogs 0.52; normalização por instrumento inerte; confidence gate AUC 0.627 fraco; 2º modelo merged 0.335→0.329 (ensemble DENTRO da mesma view não ajuda — só views DIFERENTES: per-spectrum + merged = +0.019, maior efeito único medido); test-time augmentation perde; re-weighting de análogos por fp 0.521→0.512; ChEBI+LIPIDMAPS não resolvido (0.299→0.295, dentro do ruído); 3 refs/estrutura 0.52→0.49; janela de análogos larga inerte; NP-likeness prior 0.037 (pior que random); predição de fórmula só 1.4× redução; lib-sim como termo aditivo fixo 0.52→0.27; cap-80 de forks −0.055 previsto (−24% recall Class-2); z-score blend 0.606 vs GBM 0.620; N_ANALOG flat ≥80. Teto A+B≈0.43. Recomendações dele em ordem de EV: (1) fp model treinado por mais tempo/com maior (data-limited, pico em 36k de 50k steps), (2) recall via derivativos direcionados, (3) mais seeds de ranker, (4) recall Class-1 cross-instrument.
- **starkhushi thread 742055**: ladder lib 0.158 → +COCONUT 0.243 → +gated lib 0.250 → **+frag 0.283 (+0.033 só do canal frag)**; engine prvsiyan as-is 0.335; +2 fp próprias 0.337; fp próprias alone 0.330; derivativos naive 0.335 DEAD; two-ranker 0.323 DEAD (confirma nosso megayak2). Teto de retrieval ~0.34 suspeitado.
- **haideptry thread 741745**: ±8.5 ppm ótimo; PubChem/janelas largas FALHARAM (atenção: gating deles ≠ top-50 por f·z do prvsiyan).
- **Alperen Aydın** (top1 ontem): zero notebooks públicos de CASMI → trabalho privado.
- **Threads de fórum** (IDs p/ o usuário paste): 741359, 741404, 741471, 741597, 741607, 741745, 741815, 741844, 741851, 741857, 741876, 741912, 741984, 742011, 741791, 742055.
- **kitopl "Scoring Keys & Contamination Map"** (dataset, 21/09 00:10, 30 downloads): ver §9 — usar como acelerador do harness (ik14_map = canonização métrica pré-computada; library_map = classes).

## 14. KERNELS NOSSOS (victor120956/)
| slug | versão útil | papel |
|------|------------|-------|
| casmi26-prvsiyan-canonical-fp-v6-ensemble | v6 | config 0.328 ADOPTED (refs das submissões 17-20) |
| casmi26-haideptry-0339-probe | v1 | wave1 (0.290) |
| casmi26-berat-sota-probe | v1 | wave1 (0.236) |
| casmi26-megayak-engine-probe2 | v3 | wave1 (0.323) |
| casmi26-seedswap-probe2 | v3 | wave1 (0.332) |
| casmi26-priors-high-probe2 | v2 | wave1 (0.329) |
| casmi26-hello-test | v1-2 | diagnóstico (deletável) |
| casmi26-{megayak-engine,seedswap,priors-high}-probe | — | APOSENTADOS (metadata c/ typo envida nas versões ERROR) |
Regra: kernel com versão ERROR não é "tainted" (teoria falsa) — mas slugs velhos com metadata errado ficam sujos de histórico; preferir slug novo p/ experimento novo (sufixo 2/3).

## 15. CHECKLIST DE QUALQUER PRÓXIMO CONTATO (resumão)
1. `bash arm.sh` 2. `tail day_watch.log` 3. Status dos kernels/ondas pendentes 4. `du -sh harness_data wave2_assets` (re-baixar se preciso) 5. Se noite: recon_sweep + LB 6. Trabalhar o item §12 corrente 7. HANDOFF + git push antes de encerrar o turno.

— Fim do documento. Boa sorte, próximo agente. O usuário merece o top 5 sem contar com a sorte. 💪
