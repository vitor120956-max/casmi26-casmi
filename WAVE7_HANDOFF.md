# ATUALIZAÇÃO — 29/09 08:30 BRT (resultado Wave9)

**5/5 RANQUEADAS: novo melhor 0.350 (top1 e top1_dedup); rank 225/1784 (era 337). E029 superado pela arquitetura Wave9.** adduct/adduct_dedup/formula_dedup = 0.342. Top1 promovido; dedup neutro; aduto-top5 fraco. Detalhes: WAVE9_RESULTADO.md. Quota 0 livres até 21h BRT. Próximo lote: perguntas no-orphan listadas em WAVE9_RESULTADO.md, aguardando decisão do Victor. Sem timer/polling.

---

# ATUALIZAÇÃO — 29/09 (regra de armazenamento + limpeza)

**Workspace limpo: 120 MB → 24 MB, 448 arquivos.** Regra permanente do Victor: nada é salvo no workspace; persistência = GitHub `export-clean` (rebuild_export.sh clona o espelho se ausente) + Drive do Victor. Início de conversa: clonar export-clean, mesclar ZIP Drive se houver, arm.sh, ler docs. E039 registrado. Estado CASMI inalterado: Wave9 5/5 enviada (refs 56659089-90-93/94/96), aguardando UMA consulta de notas quando Victor chamar; quota 0 livres até reset 29/09 21h BRT.

---

# ATUALIZAÇÃO — 28/09 22:49 BRT (lote Wave9 enviado)

**Estado: WAVE9 5/5 ENVIADA com autorização explícita do Victor; refs 56659089-90-93/94/96; quota 0 livres. Aceite não é nota — próxima ação é UMA consulta de notas quando ele chamar.** Pré-envio: verify 5/5 PASS; release_review com autorização verbatim e sobreposição de lote documentada. Causa do E029 segue desconhecida; se o erro genérico se repetir, plano B = rascunho estrito (POLICY_REVIEW.md). (Merge das duas sessões concluído antes do envio: E036 resolvido, 128 testes PASS.) E036 resolvido: kernels Wave9 remotos originados desta retomada (código byte-idêntico, evidência no ERROR_REGISTRY). Backup CASMI_CONTINUAR mesclado (128 testes PASS). Revisão de política em next_batch_preparation/POLICY_REVIEW.md: canário = top1 remoto; rascunho estrito = plano B se o canário falhar. Git local perdido na ressincronização (E038); exportação limpa pronta em recovered/ (commit 4d5e568 sobre base 3c0974b), push pendente de OAuth do Victor. Próximo: com autorização — send_next_batch.py --execute --variant top1; consulta única de nota depois.

---

# ATUALIZAÇÃO — preparação28/09 após21h

LerPROJECT_PRIORITY.md e next_batch_preparation/STATUS.md.21:56:Wave9top1_dedupCOMPLETE comCSVtecnicamenteverificado;outros4RUNNING;quota5;0liberados.100testesPASS. Verificadorpontual esenderseco preparados;nenhumtimer/submit. Primeirocanárioantesdosdemais.

---

# ATUALIZAÇÃO — 28/09 09:16 BRT

**Wave8 encerrou com cinco erros de reexecução e zero notas (E029).** Não está pendente. Reporter corrigido para estados terminais (E030),5testesPASS e renderizaçãooffline. Ler PROJECT_PRIORITY.md. Relatório Gemma concluído, semGPU/treino/submit. PróximoCASMI: diagnóstico, não reenvio.

---

# DECISÃO EM AVALIAÇÃO — 27/09 23:04 BRT

Victor pede comparação antes de escolher CASMI vs Gemma; ver PROJECT_PRIORITY.md. CASMI337/1684,0.341; top5.404. CincoWave8PENDING na consulta23:03:53. Gemma687times, sem nota própria identificada. Nenhum novo envio/GPU/treino.

---

# PRIORIDADE ALTERADA — Gemma

Victor quer aproveitar a competição recente. Ler PROJECT_PRIORITY.md e gemma/RESTART_STATUS.md. CASMI preservado, sem novos experimentos nesta retomada; cinco Wave8 já enviados, sem nova consulta hoje nesta mudança de foco.

---

# STATUS — 27/09 22:46 BRT

**Rank 336/1684, score 0.341. Top5 0.404; gap 0.063.** CSV oficial em `status_latest/leaderboard.csv`. Wave8: cinco PENDING, sem nota/erro reportado; aproximadamente 43 minutos desde o envio. Quota 0 livre, 5 usados, 60 totais.

Sem novo submit/build. Não prometer top5; ainda não há trajetória demonstrada. Diagnóstico local de cobertura de candidatos vs qualidade do ranking continua pendente. Próxima consulta de notas: report_wave8.py uma vez.

---

# Recon de notícias — 27/09 ~22:09 BRT

Leaderboard oficial atualizado: **rank 330/1682**, score 0.341; corte top5 **0.404**, gap **0.063**. CFM-ID4 recebeu aval explícito do host; release Enveda-180 Zenodo também. Fontes/quotes/limitações em `recon_27sep/NEWS.md`. Não generalizar liberação para todo derivado de NIST/METLIN; medir sobreposição do Zenodo antes de adicionar.

Wave8 na consulta única desta retomada, às 22:06: **5 PENDING**, nenhuma nota/erro. Nenhum novo build, submit, timer ou GPU. Próxima retomada de resultados permanece `python report_wave8.py` uma vez.

---

# ESTADO ATUAL — 27/09/2026 22:04 BRT

**Wave8: 5/5 enviados, 0/5 com nota por enquanto. Todos PENDING, sem erro. Quota API: 5 usados / 0 livres / 60 totais.**

| Variante | Ref |
|---|---:|
| Fórmula por aduto | 56624670 |
| Fórmula por aduto + dedup | 56624671 |
| Fórmula top5 + dedup | 56624673 |
| Fórmula top1 | 56624674 |
| Fórmula top1 + dedup | 56624675 |

Pré-envio: cinco candidatos conhecidos, válidos e distintos. Quatro novos kernels COMPLETE + verifier PASS; código remoto/CPU/publicação final e controles de regressão verificados. 59 testes locais PASS. Todos arquivos `submission.csv`, versões 1. A lista oficial de submissões confirmou os cinco refs; nenhum retry ou duplicata.

**Próxima ação no ponto do Victor:** `bash arm.sh`; ler diário; `python report_wave8.py` uma única vez. Não chamar novamente submitter nem criar timer. `report_wave8.py` registra status/erros/notas, aplica alerta de atribuição e só interpreta pares quando as cinco notas existirem sem esse alerta. Ausência de nota não é zero.

Melhor confirmado continua W088 blend **0.341**. Comparações pré-definidas: top1_dedup vs formula_dedup (seletividade), adduct_dedup vs formula_dedup (evidência por aduto), adduct_dedup vs adduct e top1_dedup vs top1 (refill). Ganhos são provisórios, sem caça a pesos/seeds. Causalidade do empate Wave7 continua não resolvida.

Evidências: `wave8_submit_state.json`, `wave8_extra_ready.json`, `wave8_after_send.json`, `WAVE8_RESULTADO.md`. Mudanças vs blend no preview: adduct 234 linhas; adduct_dedup 247; combinado top5 217; top1 148; top1_dedup 169.

Nenhum erro novo nesta rodada. Atualização em commit local; push remoto continua pendente de autenticação temporária.

---

# ESTADO ATUAL — 27/09 ~18:15 BRT

**Wave8: 1 candidato COMPLETE + VERIFY PASS; 4 novos kernels CPU RUNNING. Quota 0 disponíveis, 5 usados, 55 totais. Reset previsto 21h BRT.**

Ler `WAVE8_PLAN.md` para a retomada. Os quatro novos kernels são `casmi26-wave8-atomic-{top1,top1-dedup,adduct,adduct-dedup}-cpu`, todos owner victor120956, v1, URLs/código/GPU false conferidos. Novas hipóteses fundamentadas no perfil real de 108/400 moléculas multi-aduto e 97/400 com polaridades mistas. 59 testes PASS.

Próxima ação: `bash arm.sh`; testes; `python verify_wave8_extra.py` uma vez. Só após reset + quota + arquivos aprovados: `python submit_wave8.py --execute`. Sem flag, é dry-run. Esse script é da Wave8 e tem janela 27/09 21h a 28/09 21h BRT; não executar runner Wave7 para o novo dia.

**Não há cinco prontas ainda.** Nova ciência precisa de nota; causalidade do empate Wave7 continua em aberto. Nenhum submit/novo timer nesta rodada. Downloads redundantes de auditoria histórica foram compactados em `read_only_audits_27sep.tar.gz`; fixtures científicas permanecem nos diretórios originais.

---

# Estado atual — 27/09/2026 ~17:10 BRT

**Quota confirmada: 0 disponíveis / 5 usados / 55 totais. Reset previsto hoje às 21h BRT. Nenhum submit nesta retomada.** Melhor oficial permanece 0.341; Wave7 5/5 oficiais com empate causal ainda inconclusivo.

## Correção implementada e validação CPU iniciada
- Novo kernel **v1**, `RUNNING` na única consulta pós-push:
  https://www.kaggle.com/code/victor120956/casmi26-wave8-atomic-formula-dedup-cpu
- URL real, código remoto, kernelspec e GPU/TPU=false conferidos. Full pipeline a partir de train/test; nenhum dataset próprio, upstream outputs, tier2 ou MIST-blend.
- `atomic_submission.py` remove output obsoleto antes de computar; valida IDs/contagem contra sample da execução; staging + uma publicação atômica final. Nenhum blend intermediário sob `submission.csv`.
- Hashes de referência e contagem fixa 400 removidos do notebook de produção. Golden tests somente no verificador local do preview.
- **50 testes locais PASS**: 35 anteriores + 15 de publicação, incluindo falhas em cinco etapas, erro de rename/manifesto, IDs errados e contagens 1, 3, 401. Testes garantem os caminhos exercitados; não provam a causa da anomalia antiga nem antecipam o resultado do job remoto.
- Os quatro kernels antigos continuam bloqueados, não foram corrigidos por repush.

## Um candidato novo (não cinco prontos)
**W088 + dedup/refill + fórmula top5**, nessa ordem: fórmula promove candidatos após preencher slots do próprio pool. Hipótese: combinação melhora o rank em relação ao W088 blend 0.341; ganho validado promove a combinação, ausência de ganho não a promove. Não inferir efeitos individuais da Wave7 inconclusiva.

Regressão local sobre artefatos já conhecidos:
- Método fórmula reproduziu exatamente o CSV fórmula da Wave7.
- Combinado altera **217 linhas vs blend**, 201 vs dedup.
- SHA256 esperado do preview combinado: `e46a74a79a5ddd594486f3f9dc7449c6735cbcaf8278da2c40135a4786b9ebb3`.
- Não é duplicata dos cinco artefatos Wave7 ou do histórico recuperado (histórico não é exaustivo de todas as versões antigas).
- Ainda **não** está autorizado a enviar sem terminar o job e verificar o resultado. Controles blend/ours/pv/fórmula/dedup gerados como `audit_*.csv` são só regressão, não probes novas.

## Próxima retomada
1. `bash arm.sh`; ler ERROR_REGISTRY.md; `python -m unittest -q test_safety_guards test_atomic_submission`.
2. `python verify_wave8_atomic.py` uma vez. Se COMPLETE, baixa outputs, checa código remoto, publicação final, todos os controles, hash do combinado e ausência de duplicata. Escreve `wave8_ready.json` somente se tudo passar. **Não submete nada.** Se RUNNING, parar sem polling.
3. Se erro, registrar e corrigir antes de push/submit. Nenhum timer foi armado.
4. Às 21h, consultar quota + lista de submissões. Plano de submit Wave8 ainda precisa ser criado: não usar o runner Wave7 cuja janela acaba nesse reset e cujos planos já foram enviados.
5. Para 5/5 no novo dia ainda faltam quatro probes novas com mecanismo/decisão explícitos. NÃO preencher com controles duplicados nem alegar que cinco estão prontas.

Git: atualização commitada localmente; push remoto pendente da credencial temporária ausente. Nenhuma nova autorização GitHub solicitada.

---

# Estado atual — 27/09/2026, 05:20 BRT

**Wave7: 5/5 ranqueados oficialmente; todas as notas 0.341. Melhor medido segue 0.341 (+0.009 sobre 0.332).** Quota API: 5 usados, 0 disponíveis, 55 totais. Próximo reset previsto 27/09 21:00 BRT; sempre consultar quota na hora.

**Não tratar o empate como conclusão causal.** Todos os submits reportam 488898 bytes, mas os outputs publicados têm hashes distintos e tamanhos diferentes. Redownload dos cinco outputs confirmou hashes planejados. DownloadSubmission da avaliação retornou HTTP403; não contornar/repetir. Dados da reexecução/cache/contagem do avaliador continuam desconhecidos.

## Defeito local confirmado; explicação do scoring ainda hipotética
Os quatro kernels gravam o blend no nome final antes dos asserts de hash e da seleção da variante. Além disso, forçam hashes do preview/400 moléculas. Uma falha intermediária pode deixar o blend; não está provado que o avaliador usou esse arquivo. E018–E021 registrados.

**Novos envios desses quatro kernels estão bloqueados por precheck.** Não retirar o bloqueio para completar quota. W088 blend original 0.341 permanece referência; não promover/eliminar fórmula/dedup/ours/pv pelo aparente empate.

## Próximo build (ainda NÃO construído/pushado)
- Full pipeline CPU, sem dataset próprio/tier2/MIST-blend.
- Uma única publicação de submission.csv ao final; nunca gravar blend intermediário nesse nome.
- IDs e contagens validados contra sample da execução; hashes fixos somente nos testes locais do fixture, não contra dados potencialmente diferentes na produção.
- Staging + publicação atômica após validação, nenhum fallback submetível em caso de erro.
- Teste com falha injetada garantindo ausência do arquivo final antes de qualquer push. Esse teste dinâmico ainda está pendente.
- Só depois planejar probes de mecanismo. Nenhum novo envio, build remoto ou timer nesta rodada.

35 testes locais PASS; conferir ERROR_REGISTRY.md. Atualizações em commit local; push remoto pendente de autenticação. `WAVE7_RESULTADO.md` agora suspende interpretação causal; `wave7_output_reaudit.json` e `wave7_scored_audit/audit.json` são evidências.

---

# ESTADO ATUAL — 26/09/2026 22:40 BRT

**Wave7: 5/5 enviados; 1/5 ranqueado, 4 PENDING. Quota API: numToday=5, numTotal=55, numAllowedNow=0.**

| Probe | Ref | Estado confirmado |
|---|---:|---|
| W088 blend | 56592387 | COMPLETE, **0.341** — novo recorde (+0.009 vs 0.332) |
| W088+fórmula | 56594468 | PENDING, sem erro/nota |
| W088+dedup | 56594469 | PENDING, sem erro/nota |
| W088 ours | 56594472 | PENDING, sem erro/nota |
| W088 pv | 56594473 | PENDING, sem erro/nota |

Quatro kernels COMPLETE + provas e hashes exatos validados antes do envio. Todos CPU, versão 1, nome obrigatório `submission.csv`. Nenhuma duplicação do blend. E001 corrigido e comprovado em produção; não voltar aos nomes alternativos.

**Próxima retomada:** `bash arm.sh`; ler ERROR_REGISTRY.md e tail do diário; `python wave7_run.py --report` uma única vez para notas. **Não submeter outra coisa nesta quota.** NÃO inferir placar das quatro pendentes; não repushar os slugs v1 durante avaliação.

NO-ORPHAN: comparar fórmula/dedup contra blend **0.341** para decidir promoção dos mecanismos; comparar ours/pv/blend para definir o ramo do próximo build. Não combinar efeitos antes das notas. Diferenças pequenas são provisórias, não justificam loteria de pesos/seeds.

O timer 22:15 não enviou; a retomada manual do Victor às 22:39 completou os quatro pedidos. **Não foi armado novo timer nesta rodada.** Sem sleep/poll. A próxima leitura de notas depende de nova retomada, salvo processo externo com execução comprovada.

`WAVE7_RESULTADO.md`, `wave7_submit_state.json` e `submissions_score_check.json` são as evidências atuais. Registro de erros atualizado (E017 recorrente; E001 agora verificado em produção). Atualizações desta rodada em commit local; push remoto não realizado sem autenticação.

---

# REGRA PERMANENTE — REGISTRAR E BLOQUEAR REPETIÇÃO DE ERROS

Por ordem do Victor: ler `ERROR_REGISTRY.md` antes de agir. Todo erro exige evidência, causa/hipótese, impacto, correção, trava e teste. Antes de novo build/push/submit: `python -m unittest -v test_safety_guards`. São 26 testes locais aprovados nesta revisão. `incidents.jsonl` preserva os registros; erros de runner entram automaticamente, demais erros devem ser registrados pelo agente. Não solicitar nova autorização GitHub nem enviar probes para testar transporte já conhecido.

# ATUALIZAÇÃO PRIORITÁRIA — 26/09 21:09 BRT

**1/5 enviado, 0/5 com nota confirmada; 4 slots disponíveis.** W088 blend ref **56592387**, `PENDING`, sem erro. Quota final API: numToday=1, numTotal=51, numAllowedNow=4.

## Bug de transporte descoberto e corrigido
- A competição **exige literalmente `submission.csv`**. `submission_ours.csv`, `submission_pv.csv`, `submission_formula.csv`, `submission_dedup.csv` são válidos localmente, mas NÃO aceitos como nome no submit.
- Tentativas formula/ours rejeitadas HTTP400, sem consumir slots. Não foram submissões ranqueadas. Histórico em `wave7_rejected_attempts.json`; journal ativo reconciliado e contém somente o blend aceito.
- Não repetir os comandos antigos com nomes alternativos. `wave7_run.py` agora delega ao `wave7_named_run.py` com a correção. Idempotência por journal + API.
- Anomalia Wave6 ganhou mensagem: rrf/fstrict/mistform têm `errorDescription` de formato e totalBytes=0, ainda sem nota. Isso não prova a causa-raiz; bloqueio de dataset próprio permanece.

## Quatro kernels CPU de transporte correto
Todos v1, full pipeline independente, GPU/TPU=false, kernelspec presente. URLs reais e código remoto comparados aos locais; consulta única pós-push: **4 RUNNING**.
- https://www.kaggle.com/code/victor120956/casmi26-wave7-w088-formula-submit-cpu
- https://www.kaggle.com/code/victor120956/casmi26-wave7-w088-dedup-submit-cpu
- https://www.kaggle.com/code/victor120956/casmi26-wave7-w088-ours-submit-cpu
- https://www.kaggle.com/code/victor120956/casmi26-wave7-w088-pv-submit-cpu

Cada notebook regenera previsões e **só então** salva a variante sob `submission.csv`; preserva blend em `submission_blend_control.csv`. Hash SHA256 deve repetir exatamente a variante já verificada; sem essa prova (`wave7_ready.json`) o runner bloqueia. Nenhuma leitura de dataset próprio ou output upstream.

A 2ª leva original já terminou e passou: fórmula altera **201 linhas**; dedup altera **34 linhas** e substitui **392 placeholders**. Recomputação atual muda somente o nome de entrega, não a experiência.

## Retomar sem duplicação
1. `bash arm.sh` (agora também restaura RDKit para verificação).
2. `tail -25 day_watch.log` + `wave7_submit_state.json`.
3. `python wave7_run.py` — quota/API primeiro; uma leitura de status por kernel; somente COMPLETE com arquivo, prova e hash corretos; preserva slots de jobs incompletos e nunca repete journal ambíguo.
4. Notas, somente leitura pontual: `python wave7_run.py --report`.

Timer `wave7_afterbuild_timer.py`, process ID `wave7-concluir-quatro-variantes--a92f174f`: tentativa única **22:15 BRT**; notas uma vez **23:30 BRT**. É melhor esforço e depende do sandbox ativo. O timer anterior de 21h **não executou**; o ponto do Victor permitiu esta retomada manual.

**Git:** remoto confirmado anteriormente em `3c0974b`; atualizações desta rodada serão commitadas localmente. Credencial GitHub em `.cache` não sobreviveu à restauração; não prometer push remoto desta rodada.

---

# Registro anterior (histórico, superado pelos itens acima)

# Wave7 — 26/09/2026, BRT

## Veredito
Às 19:21 BRT: **nenhuma submissão nova**. Quota confirmada pela API: 5 usados / 0 disponíveis / 50 totais. Reset 26/09 21:00 BRT = 27/09 00:00 UTC.

## Restaurado e confirmado
- `bash arm.sh` foi a primeira ação; falhou porque o workspace só tinha os dois anexos.
- `uploads/TRANSFER_26SEP.md` foi lido inteiro. CLI 2.2.4/auth restauradas sem expor chave.
- O link Drive era somente `arm.sh`, não um backup. Script original salvo em `uploads/arm_drive.sh`; não executado cegamente.
- Repo público recuperado em `recovered/`, commit remoto `aa560bd81a97ed28bad9aff5173504ed9944600a`. Diário remoto termina em 22/09, portanto é desatualizado. **Não rodar watchers/precheck antigos: há polling e exigência GPU.**
- `day_watch.log` raiz contém histórico recuperado + novos eventos.
- W088 `victor120956/casmi26-w088-replica-llccqq624-apache-2-0`, v1, COMPLETE.
- MD5s batem transferência: blend `74dd3e23f5c4d6941239708cf20260e3`; ours `71dc98afa17a950e01d6dadd48c69f49`; pv `5364114d02f583ac518ffad28a8e1ca2`.
- Validação local: 400 IDs na ordem do sample oficial; 25 SMILES válidos por linha. Outputs diferentes entre si e sem igualdade com 38 outputs históricos recuperados (não representa prova de cobertura exaustiva de cada versão histórica).
- Anomalia persiste na consulta inicial: 3 posthoc-dataset COMPLETE sem nota. Não reutilizar dataset próprio como entrada.

## Descoberta e 2ª leva CPU
W088 já canonical-deduplica top40 e completa com CCO: **392 placeholders em 34 moléculas**, 33 linhas com SMILES repetidos. A nova probe dedup não é mera repetição do mecanismo existente.

**Kernel real**: https://www.kaggle.com/code/victor120956/casmi26-wave7-w088-formula-dedup-cpu
- Versão 1, push aceito; consulta única posterior: RUNNING.
- Metadata remota conferida: GPU=false, TPU=false, internet=false, kernelspec Python3, sem kernel_sources/dataset próprio/tier2.
- Full pipeline: regenera W088 a partir de train/test; usa apenas assets públicos necessários. Dataset `casmi26-mist-msbuddy-assets` serve ao msbuddy, **não há inferência ou blend MIST**.
- Um único job gera `submission_formula.csv` e `submission_dedup.csv`.
- Controle regenerado deve repetir os 3 MD5s W088; divergência interrompe antes de aceitar variantes.
- Fórmula: particionamento estável dos mesmos 25 SMILES, promovendo fórmulas do top5 msbuddy; cobertura >=390/400; mudança obrigatória.
- Dedup/refill: mantém sequência de identidades reais, remove CCO/duplicatas/inválidos e preenche até 25 identidades do mesmo pool COCONUT+train por massa. Sem tier2 e sem modificar ranker. Mudança obrigatória; testes unitários passaram.
- `wave7_verify.json` comprova hashes, mudanças e contratos. Sem esse arquivo válido: não submeter a 2ª leva.

## NO-ORPHAN — decisão após notas
| Probe | Pergunta | Próximo build |
|---|---|---|
| W088 blend | O ganho alegado replica na conta? | Referência medida, não tratar 0.341 como fato |
| W088 ours | O ranker simulado sozinho supera a mistura? | Se vencer, usar esse ramo como referência provisória |
| W088 pv | O ranker público sozinho basta? | Se vencer/empatar, evitar blend sem benefício |
| W088+fórmula | O mecanismo de fórmula transfere ao W088? | Delta positivo vs W088 promove mecanismo; empate/perda não promove |
| W088+dedup | Recuperar posições desperdiçadas ajuda? | Delta positivo vs W088 promove refill; empate/perda mantém saída original |

Mudanças pequenas no LB são evidência provisória; ausência de nota não é zero, nem motivo para resubmit.

## Disparo pontual (sem sleep/poll)
`wave7_timer.py` está armado via start_process:
- Process ID: `wave7-disparo-pontual-s-21h-brt-b6de68a9`.
- **26/09 21:00:05 BRT:** executa `wave7_run.py` uma vez.
- **26/09 23:30 BRT:** consulta de notas uma única vez, gera `WAVE7_RESULTADO.md`; não há repetição automática.
- Usa eventos asyncio de prazo absoluto; nenhuma consulta durante a espera.
- **Melhor esforço: depende do ambiente permanecer ativo. Não é cron externo nem garantia de execução após encerramento/reset do sandbox.**

Runner: rearma auth; consulta quota; checa CPU uma vez; baixa/valida apenas outputs conhecidos; prioriza fórmula/dedup se prontas, depois blend/ours/pv. Se CPU não estiver validada, envia só os 3 W088 e deixa 2 slots livres. Nunca loteria para completar 5.
- Usa API equivalente a `kaggle competitions submit COMP -f NOME -k SLUG -v 1 -m MSG`.
- Janela autorizada de submissão: 26/09 21h a 27/09 21h BRT; fora dela aborta.
- Lock local; journal de intenção gravado antes da chamada; não repete pedido ambíguo; confere mensagens já existentes na conta.
- Quota insuficiente para lote validado: aborta em vez de criar alocação parcial sem controle.
- Aceite/ref não significa nota. 5/5 só conta como ranqueado quando cada nota existir.
- Dry-run dos 3 W088 PASS, sem chamadas de submissão.

## Retomar
1. `bash arm.sh`
2. `tail -25 day_watch.log` e ler `wave7_submit_state.json`, se existir.
3. Consultar `competition_get_submission_limits` + submissões antes de qualquer nova tentativa.
4. Se dentro da janela e timer não executou: `python wave7_run.py` (idempotência local + mensagens na conta).
5. Para notas, apenas consulta pontual: `python wave7_run.py --report`.
6. Intenção `ambiguous_or_failed`: reconciliar com API antes de editar journal. Nunca retry cego.
7. Não repushar esses slugs durante o disparo: v1 e arquivos estão fixados.

## Pendências
- Ainda não há nota W088 medida nem garantia de 5/5 novos ranqueados.
- GPU segue proibida; Gemma não foi acionado, `GEMMA_RECON.md` não veio no workspace/repo recuperado.
- GitHub autorizado via navegador (cliente oficial GitHub CLI, escopo public_repo). Push dos 3 commits confirmado em origin/main=4e983561b844ce38fcf3421c707f77c3ca42f082. Nenhuma credencial incluída nos commits.

Git: commits `2f08873`, `0e9c0a1`, `4e98356` enviados e HEAD remoto verificado. Credencial temporária em .cache (excluída do snapshot), não no repo. Este registro acrescenta um commit documental.
