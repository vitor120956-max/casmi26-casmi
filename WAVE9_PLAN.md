# Wave9 — isolamento de falhas (correção E031) — 28/09 21:21 BRT

**Estado: cinco kernels v1 pushados, RUNNING na única consulta pós-push. Nenhum submit feito. Quota 0 usados / 5 livres / 60 totais; janela até 29/09 21h BRT.**

## O que mudou vs Wave8 (mesmas 5 perguntas científicas, arquitetura nova)

| Problema Wave8 (E031) | Correção Wave9 |
|---|---|
| `if coverage < 0.975: raise` derrubava o lote | Cobertura é métrica registrada (`MSBUDDY_COVERAGE` no log/prova); molécula sem fórmula recebe no-op explícito por linha |
| Loop validava as 8 variantes; ramo auxiliar inválido abortava antes de publicar o escolhido | Um mecanismo por kernel; só o escolhido é validado/publicado; `AtomicSubmission.validate` existe apenas dentro do publisher |
| Falha do msbuddy (install/assets/IDs) matava o kernel | `except` degrada: `buddy_formulas={}` + registro `MSBUDDY_UNAVAILABLE` na prova; nunca silencioso |
| `assert` de pool/massa no dedup abortava | Shortfall vira padding CCO documentado + registro `DEDUP_SHORTFALL_PADDED`/`NO_VALID_MASS` |
| `split_spectra`/`combine` estritos abortavam em linha/grupo ruim | `*_lenient` ignoram com registro (`SPECTRA_ROWS_SKIPPED`, `DUPLICATE_ADDUCT_GROUPS_SKIPPED`) |
| — | Publicação atômica e falha estrutural explícita preservadas (schema, 25 SMILES válidos, ordem de IDs) |

Runtime único testado (`wave9_runtime.py`) embutido via `%%writefile`; mesma fonte nos cinco kernels. Engine (células do W088) idêntico ao Wave8 — não tocado.

## Kernels (todos v1, CPU, internet off, assets aprovados, código remoto == local)

| Tag | Slug | Mecanismo |
|---|---|---|
| adduct | casmi26-wave9-isolated-adduct-cpu | Fórmula por grupo aduto/polaridade sobre o blend |
| adduct_dedup | casmi26-wave9-isolated-adduct-dedup-cpu | Idem após dedup/refill |
| formula_dedup | casmi26-wave9-isolated-formula-dedup-cpu | Fórmula top5 após dedup/refill |
| top1 | casmi26-wave9-isolated-top1-cpu | Somente fórmula rank1 promove |
| top1_dedup | casmi26-wave9-isolated-top1-dedup-cpu | Top1 após dedup/refill |

## Evidências locais

- 92 testes PASS (64 anteriores + 28 novos `test_wave9_isolation.py`): portabilidade (cobertura 0/50/97%, IDs faltantes, massa ausente, pool curto, aduto inválido), isolamento (validação só no publisher; cardinalidade publish/begin == 1), guards e metadados.
- `audit_wave9_failure_modes.py`: 15 checagens — gate de cobertura e loop multi-ramo ausentes nos cinco fontes (AST); modos Wave8 reproduzidos sinteticamente agora publicam degradados em vez de abortar.
- Precheck PASS nos cinco. Push aceite; verificação pós-push única em `wave9_push_verify.json`.
- Identidade do preview com expectativas locais Wave8 (top1/formula_dedup/top1_dedup) é ESPERADA e exigida pelo verificador: mesmo mecanismo, mesmos dados públicos. O histórico de bloqueio contém apenas hashes ranqueados (Wave7); Wave8 nunca foi avaliada.

## Retomar (sem polling)

1. `bash arm.sh`; ler `ERROR_REGISTRY.md` e `tail day_watch.log`.
2. `python -m unittest -q test_safety_guards test_atomic_submission test_formula_evidence test_wave9_isolation` (92 testes).
3. `python verify_wave9.py` — UMA leitura por kernel. Gera `wave9_ready.json` só para COMPLETE com: código remoto idêntico, prova íntegra, `audit_blend` == W088 (regressão do engine), `degraded == []` no preview, mecanismo com mudanças > 0, expectativas locais batendo (top1/fórmula/top1_dedup), 513 grupos (aduto), artefato distinto do histórico e entre si.
4. Só com quota e `wave9_ready.json`: `python submit_wave9.py` (dry-run) → `--execute`. Prioridade: adduct > adduct_dedup > formula_dedup > top1 > top1_dedup. Janela do script: 29/09 00:00–24:00 UTC. Erro interrompe; journal `wave9_submit_state.json`.
5. Notas: uma única consulta após avaliação; não declarar 5/5 pelo aceite; ausência de nota não é zero.

## Decisões pós-nota (no-orphan)

- adduct vs formula_dedup: evidência por grupo aduto vale o custo? Ganho confiável promove; empate/perda não.
- top1 vs formula_dedup e top1_dedup vs formula_dedup: seletividade top1 vs top5, com refill constante.
- adduct_dedup vs adduct: efeito do refill sobre a evidência por aduto.
- Qualquer kernel com `degraded` não vazio no rerun (visível só se houver output): interpretar como execução degradada, não como veredito do mecanismo.
- Referência permanece W088 blend 0.341; gap top5 0.063.

Sem timer armado. Push remoto Git continua pendente de autenticação; commits apenas locais.
