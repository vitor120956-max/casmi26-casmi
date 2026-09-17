# LANES.md — briefings de time multi-agente (1 humano, N sessões de IA)

Como usar: abra uma conversa nova (Arena ou outra IA de sua confiança) e cole o briefing
da raia inteira. A sessão trabalha de forma independente e grava resultados no repo.
**Fonte da verdade: este repositório (git). Bastão: HANDOFF.md.**
Repo: https://github.com/vitor120956-max/casmi26-casmi (privado).
Clone numa sessão nova: `git clone https://x-access-token:<SEU_PAT>@github.com/vitor120956-max/casmi26-casmi /home/user/casmi26-casmi`
(PAT = fine-grained token que o humano fornece; permissões Contents R/W só neste repo.)

## Regras de coordenação (TODAS as raias)
1. Uma única conta Kaggle (victor120956). Somente a **Raia A (Controlador)** faz
   `kaggle kernels push` no kernel principal e `competitions submit`. As outras raias
   NUNCA submetem nem fazem push de kernel — evitam colisão de cota (5 subs/dia, 30h GPU/sem).
2. Nunca pedir/aceitar senhas. Chave Kaggle API só onde já existe (~/.kaggle/kaggle.json),
   escopo: pull/push/status deste projeto.
3. Todo resultado vai para arquivo no repo + `git commit` com mensagem clara.
4. Antes de começar: ler HANDOFF.md e STRATEGY.md inteiros. Depois: atualizar HANDOFF.md
   com o que fez (seção da raia) e commitar.
5. Se a raia precisar de decisão estratégica, NÃO decidir sozinha: escrever a pergunta em
   `HANDOFF.md § OPEN QUESTIONS` e seguir com o resto.

---

## Raia A — CONTROLADOR / experimentos Kaggle (esta sessão principal)
Dono exclusivo de: kernel `victor120956/casmi26-analog-ranker-fork`, submissões, cota GPU.
Loop: patch → push → poll → ler log → validar → submit → registrar score em HANDOFF.md.
Fila atual: v5 probe f_t (rodando) → interpretar f_t → v6 real conforme diagnóstico →
probes P2-P4 (18/09) → hardening.

## Raia B — HARNESS LOCAL / diagnóstico sem gastar cota Kaggle
Missão: construir avaliação offline para experimentos não queimarem submissões.
- Pegar dataset público `enveda-np-examples` (kaggle datasets download — pode usar a
  chave API local, só download, nunca submit/push).
- Montar holdout: 250 moléculas NP fora do índice; pipeline de retrieval local
  (inspirado em casmi26/baseline_single_cell.py) + scorer.py como métrica.
- Entregável: `holdout/run_holdout.py` + `holdout/RESULTS.md` com MRR baseline local.
- Extra: analisar test.parquet local (já em casmi26/data/) vs submission do fork
  (forkout/submission.csv): quantos rank-1 são twins vs mudam entre versões v2/v3.

## Raia C — PESQUISA / canais novos (só leitura + código local, zero Kaggle)
Missão: levantar e prototipar os canais que atacam o jogo real (traps/isômeros e hidden NP):
1. DreaMS (weights no Google Drive, ver HANDOFF § External): embeddings de espectro p/
   retrieval — desenhar o plano de virar dataset privado Kaggle (passo a passo p/ controlador).
2. De-novo spectrum→SMILES: MS2Mol, GNPS/MoNA/EnvedaDark — o que existe pronto, licenças,
   tamanho, como rodar offline em notebook Kaggle ≤9h sem internet.
3. Isomer discrimination: literatura CASMI/SIRIUS/CSI:FingerID/CFM-ID — o que separa
   isômeros de mesma massa com evidência espectral (in-silico fragmentation).
- Entregável: `research/CANALS.md` — por canal: viabilidade, custo GPU, ganho esperado,
  plano de integração no kernel do fork.

## Raia D — SCOUTING / leaderboard e merges (leve, 1x por semana)
Missão: monitorar LB (download CSV via kaggle CLI), mapear o cluster 0.339 (quem são,
notebooks públicos, discussões), identificar alvos de merge (times top 20-40 com atividade
decrescente) para nov-dez. Entregável: `scout/LB_LOG.md` (snapshots datados) +
`scout/MERGE_TARGETS.md` (perfil dos alvos). Nada de contato com outros times sem o humano.

---
## Status (17/09/2026 ~15:00 UTC)
- Score atual: 0.324 (rank 72/441). v5 probe f_t RODANDO no kernel — resultado define
  prioridade das raias B/C (ver HANDOFF § v5).
- Descoberta do dia: visible test = 100% twins perfeitos do train no rank 1, mas MRR 0.32
  → ~2/3 das respostas têm conectividade DIFERENTE da anotação do train (traps). O jogo
  público = discriminação de isômeros; o jogo hidden = classes 2/3 (análogos/de-novo).
