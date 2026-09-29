# TRANSFERÊNCIA ATUAL — CASMI / Victor

**Preparada em 28/09/2026, aproximadamente 22h18 BRT.**
**Este arquivo prevalece sobre as instruções de estado antigas em `uploads/TRANSFER_26SEP.md`.** Leia o antigo para conhecer as restrições, não para reenviar lotes históricos.

## 1. O que Victor quer agora

Continuar com outro agente porque esta conversa ficou ruim. Último pedido operacional: **só preparar os próximos envios CASMI para agora**. Não há autorização nova de envio nesta transferência. Não iniciar outra competição, GPU ou treino Gemma.

Ele está frustrado com cinco envios CASMI rejeitados. Seja direto, não repita desculpas ou explicações sem avançar. Não prometa que tudo está corrigido: **a causa exata do erro na reexecução oculta continua desconhecida**.

## 2. Começo seguro na nova sessão

1. Se o workspace não for herdado, extrair `CASMI_CONTINUAR.zip` em `/home/user` (o ZIP contém caminhos relativos, sem pasta externa).
2. A credencial Kaggle foi **excluída do backup**. Se não estiver no novo workspace, Victor precisa anexar seu JSON de credenciais pelo recurso privado de arquivos, dentro de `uploads/`. Não pedir chave colada no chat, não imprimir segredos e não criar outra conta.
3. Executar **`bash arm.sh`**. Ele restaura autenticação Kaggle e dependências básicas; não inicia notebooks ou envios.
4. Ler este arquivo inteiro, `uploads/TRANSFER_26SEP.md`, `PROJECT_PRIORITY.md`, `ERROR_REGISTRY.md` e os JSONs abaixo. A evidência mais recente é `next_batch_preparation/readiness.json` (22h09), não o resumo antigo de 21h56.
5. Conferir primeiro se existe `next_batch_preparation/send_state.json`. Na montagem desta transferência **não existia**. Se surgir numa nova sessão, reconciliar antes de qualquer tentativa.
6. Uma consulta pontual: **`python check_next_batch_once.py --check-once`**. Não contém endpoint de submissão; consulta status/cota e verifica arquivos apenas se a execução terminou. Nada de sleep/poll/retry automático.

## 3. Estado confirmado — não confundir preview com nota

### CASMI / Wave8
- Competição: `enveda-CASMI26-molecule-id-mass-spectra`.
- Conta única: `victor120956`.
- Melhor referência confirmada: **W088 blend = 0.341**. Não tratar isso como probabilidade de identificação correta.
- Os cinco envios Wave8 terminaram **COMPLETE COM ERRO, SEM NOTA**, não estão pendentes.
- Refs: `56624670` adduct; `56624671` adduct_dedup; `56624673` formula_dedup; `56624674` top1; `56624675` top1_dedup.
- Mensagem oficial: `Your notebook hit an unhandled error while rerunning your code. Note that the hidden dataset can be larger/smaller/different than the public dataset`.
- Evidência: `wave8_after_send.json`, `wave8_reexec_incident.json`, `WAVE8_RESULTADO.md`.
- **Não reenviar esses kernels idênticos.** Falha não prova qualidade ruim do mecanismo nem bug do Kaggle.

### Wave9 remoto — última consulta 28/09 às 22:09 BRT

Todos são privados, CPU, **versão 1 confirmada via SDK**, não inferida do nome.

| Variante | Kernel depois de `victor120956/` | Último estado |
|---|---|---|
| top1 | `casmi26-wave9-isolated-top1-cpu` | RUNNING |
| adduct | `casmi26-wave9-isolated-adduct-cpu` | RUNNING |
| adduct_dedup | `casmi26-wave9-isolated-adduct-dedup-cpu` | RUNNING |
| formula_dedup | `casmi26-wave9-isolated-formula-dedup-cpu` | RUNNING |
| top1_dedup | `casmi26-wave9-isolated-top1-dedup-cpu` | COMPLETE; arquivo tecnicamente verificado |

Na consulta: **5 envios disponíveis, 60 totais**. Essa cota precisa ser conferida novamente antes de enviar.

`top1_dedup`: CSV com 400 registros, hash
`200764676509f414dd418c66a28c181fbc3daa1bb2716ac6ebb81a06b8566d43`;
`degraded=[]`; cobertura de fórmulas `0.9975`. Fonte, versão, CSV, IDs/SMILES, manifesto, hashes dos inputs e baseline conferidos.

**1/5 arquivos tecnicamente verificados; 0/5 liberados para submissão.**

Esses cinco Wave9 já estavam rodando quando foram descobertos. Não constavam no diário/local disponível; origem da execução não foi esclarecida. Fontes foram recuperadas em `remote_wave9_reconciliation/`. Não cancelar, repushar ou assumir que foram criados nesta retomada. A pergunta sobre outra conversa foi pulada pelo usuário. Ver E036.

## 4. Existem DUAS implementações diferentes

### A. Wave9 remoto já em execução
- Remove a trava de cobertura de 97,5% e valida somente o resultado escolhido na etapa externa.
- **Ainda gera `blend`, `pv` e `ours` dentro do engine.**
- Exceções gerais do msbuddy viram `DEGRADED` registrado, permitindo resultado-base/resultado parcial.
- Esse fallback é registrado, mas pode prejudicar a atribuição científica se ocorrer no teste oculto. Não afirmar que corresponde à implementação estrita abaixo.
- O CSV público aprovado é igual ao preview da Wave8 rejeitada. Isso é candidato a **reteste de código corrigido**, não uma previsão inédita. Requer revisão explícita, não ultrapassar a proteção contra duplicação silenciosamente.

### B. Rascunhos locais de correção estrita
Arquivos: `selected_variant_runtime.py`, `build_selected_repair.py`, `casmi_repair_drafts/`.
- Só executam as dependências da variante escolhida; engine gera apenas CSV `blend`.
- Falta de fórmula retornada explicitamente pelo modelo preserva a ordem apenas daquela molécula, com registro.
- Erro de instalação/modelo/contrato continua fatal; nenhum fallback global substitui o mecanismo.
- Publicação final atômica e diagnóstico por etapa.
- IDs normalizados, quantidade de moléculas dinâmica.
- **Não passaram por uma execução completa no Kaggle.** A tentativa de iniciar `victor120956/casmi26-repair-v1-top1-cpu` foi bloqueada por `Maximum batch CPU session count of 5 reached.` Sem URL/versão confirmada. Não confundir com um sexto job em execução. `repair_preview_state.json` registra o bloqueio; sem retry automático.

## 5. O que realmente foi testado

- E031: reproduzidos dois riscos dos cinco Wave8: cobertura sintética 97% interrompia todos; um ramo auxiliar inválido podia bloquear um resultado escolhido válido. **Isso não prova que aconteceu no conjunto oculto.**
- Rascunhos locais: 86 testes (64 antigos + 22 novos) passaram. Usando caches, os cinco pós-processamentos preservaram exatamente os 400 registros de cada preview anterior. Não é rerun dos modelos completos.
- Preparação/liberação: mais 14 testes, **total 100 PASS**, mais um teste separado confirmando que enviar sem aprovação é bloqueado antes de importar a API.
- Logs: `casmi_repair_drafts/tests.log`, `casmi_repair_drafts/cached_equivalence.json`, `next_batch_preparation/tests.log`.
- Testes locais e preview público não garantem sucesso na reexecução oculta.

Comando dos 100 testes:

```bash
python -W error::ResourceWarning -m unittest \
  test_batch_release_checks test_selected_variant_runtime \
  test_safety_guards test_atomic_submission test_formula_evidence \
  test_wave8_report_logic -q
```

## 6. Como continuar a preparação sem gastar a cota

1. Rodar o verificador uma vez e ler `next_batch_preparation/STATUS.md` e `readiness.json`.
2. Para cada preview concluído, conferir `publication.json`, logs, `degraded`, mecanismo e hashes. Não basta existir CSV.
3. Resolver a diferença de política entre os Wave9 remotos e os rascunhos estritos. Não declarar revisão concluída sem fazê-la; se escolher alterar código, precisa de novo preview e pin de versão.
4. Não usar `send_next_batch.py --execute` só porque existe arquivo aprovado. **`release_review.json` permanece com `send_authorized=false`, sem janela temporal e sem aprovações.**
5. Plano acordado nas respostas: primeiro um envio corrigido (`top1` planejado), conferir nota/erro/atribuição, só então liberar os outros quatro. Não gastar outro lote inteiro ao mesmo tempo.
6. `python send_next_batch.py` é **dry-run**, sem rede. O modo de execução exige revisão de fonte/hash, aprovação explícita de reteste se repetir preview rejeitado, janela com timezone, quota, versão, arquivo e journal de intenção atômico. Sem retry após resultado ambíguo.
7. O usuário pediu “só preparar”. Obter confirmação para gasto da cota após demonstrar o que está pronto.

### Horário
Victor inicialmente pediu “hoje às 21h”, mas já eram 21h43 BRT. Depois pediu preparar “para agora”. **Não existe timer, agendamento, autoenvio ou tarefa de monitoramento.** Não prometer disparo enquanto o agente estiver inativo. Não reagendar silenciosamente para outro dia.

## 7. Restrições permanentes

- PT-BR, conciso, veredito no topo, instruções simples para celular.
- **Registrar TODO erro** com evidência, hipótese/causa, impacto, correção e trava/teste.
- **Nunca sleep/poll.** Não usar loops de consulta esperando terminar. Não executar scripts antigos de timers/autoenvio (`auto_submit*`, `day_watch*.sh`, `queue_push*`, `finish_line.sh`); usar os fluxos atuais descritos aqui.
- NO-ORPHAN: cada experimento responde pergunta que muda a decisão seguinte. Sem loteria, arquivo desconhecido ou duplicação cega.
- Meta histórica de cinco envios diários não é autorização para gastar cinco slots sem validação.
- CPU; nada de GPU/treino Gemma sem ordem. Não presumir que quota GPU voltou só por ser segunda-feira.
- **Nunca tier2 no ranker (0.240), nunca MIST-blend (0.314)** sem nova justificativa explícita. Gated 0.323 e variações neutras também já foram registradas.
- Não usar kernels baseados em dataset próprio até resolver a anomalia histórica. Assets públicos autorizados são outra coisa; `safety_guards.py` contém allowlist.
- `submission.csv` literal; kernelspec obrigatório; conferir URL real após push, pois slug pode mudar.
- Não repetir/contornar os cinco `DownloadSubmission 403` da Wave7. Output do notebook público não é prova do arquivo pontuado.
- Uma conta Kaggle. Credenciais nunca no chat, no ZIP ou em Git público.

## 8. Histórico essencial e erros

- Wave7: cinco notas 0.341 com outputs locais distintos e metadados iguais; comparações inconclusivas. W088 permanece referência, não prova de que fórmula/dedup não funcionam.
- E018–E022: atribuição, 403, publicação antecipada, fixtures públicas fixas e mistura de adutos.
- E023–E024: artefatos Gemma históricos ausentes e prioridade Gemma declarada cedo demais.
- E025–E028: enum da SDK, colisão ao baixar notebooks, amostra HTTPX incompleta corrigida, pergunta de reutilização era CASMI e não Gemma.
- E029: cinco falhas de reexecução Wave8; causa exata aberta.
- E030: reporter corrigido para não esperar notas de erros terminais.
- E031: riscos de cobertura/ramos auxiliares reproduzidos e correção local estrita.
- E032–E033: limpeza de arquivos/diagnósticos locais corrigida.
- E034–E036: limite CPU, ref vazia da API e Wave9 remotos não registrados localmente.
- E037: na transferência, Git local mostrou HEAD **272b189**, embora a conversa tenha relatado commits posteriores, inclusive `8db4867`. Os arquivos recentes existem. **Causa da divergência não determinada; o backup dos arquivos atuais é a referência.**

## 9. Mapa dos arquivos críticos

- `next_batch_preparation/`: plano, versões, readiness, revisão bloqueada, outputs aprovados e status.
- `remote_wave9_reconciliation/`: cinco fontes reais e metadados/hash recuperados.
- `casmi_repair_drafts/`: implementação local diferente, testes e equivalência por cache; não liberada remotamente.
- `wave8_failure_diagnosis/`, `audit_wave8_failure_modes.py`: reprodução dos riscos, não causa oculta.
- `wave8_submit_state.json`, `wave8_after_send.json`: journal e resultado Wave8.
- `probeout_w088/`, `probeout_wave7_cpu/`, `probeout_wave8_atomic/`, `probeout_wave8_extra/`: referências e previews históricos.
- `harness_data/`, `regression_formula_assets/`, `historical_hashes.json`: fixtures e controle de duplicação.
- `ERROR_REGISTRY.md`, `incidents.jsonl`, `day_watch.log`: histórico.

## 10. Outros projetos — preservar, não mudar o foco por impulso

- Gemma: `gemma/DISSECCAO_GEMMA_E_PLANO.md`. 129 tarefas analisadas, 4 grafos, snapshot HTTPX, wheels e fontes públicas. 5 testes CPU de contratos. Nenhum treino/GPU/inferência/submissão/nota Gemma. Baseline completo ainda não validado. Gemma permite **1 envio/dia**, não 5.
- Pergunta comercial do usuário era sobre **CASMI**: potencial buscador molecular/IA científica, mas produto/cliente/licenças/validação externa não comprovados. Não dizer que é inútil nem prometer renda.
- Outras competições pesquisadas em `opportunities_28sep/RESUMO.md`; Solar era só candidato a triagem CPU, não decisão de migração. Prêmios ARC têm condições; não apresentar o banner como dinheiro garantido.

## 11. Backup e Git

O ZIP contém os arquivos atuais necessários e materiais auxiliares do workspace, com manifesto SHA-256. **Exclui credenciais, `.git`, pacotes instalados, caches e processos.** O diretório `recovered/` é incluído como arquivos; não presumir que traz um repositório Git funcional após extração.

Não clonar o remoto por cima do backup: o último push confirmado era `3c0974b`, mais antigo. Não confiar em commits posteriores apenas citados na conversa sem verificar sua existência.

Há materiais de competição no backup: **uso privado para a continuação de Victor, não publicação pública**. Ver `PUBLIC_EXPORT_BLOCKED.md`. Não fazer push antes de auditar licenças, dados e histórico. Dependências precisam ser reinstaladas no ambiente novo; o backup não inclui `.venv`/`.local`.
