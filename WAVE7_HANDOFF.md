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
- Git push continua pendente, sem token. Nenhuma credencial incluída no commit local.

Git local: commits `2f08873` + outputs de recuperação; push não executado (sem token).
