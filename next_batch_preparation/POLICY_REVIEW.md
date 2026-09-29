# Revisão de política — Wave9 remoto vs rascunho estrito (29/09 01:55 UTC)

Exigida pelos bloqueios `SOURCE_RUNTIME_POLICY_REVIEW_REQUIRED` e `REPAIR_RETEST_REQUIRES_EXPLICIT_REVIEW`. Veredito no topo.

## Veredito

**Canário = `top1` remoto (v1, sha fonte `463a3d13…`, sha CSV `6bad69c7…`).** Rascunho estrito local fica como ramo de hipótese se o canário falhar. Nenhum dos quatro restantes sem conferir a nota do canário.

## Diferença A (remoto) vs B (rascunho estrito)

| Ponto | A: Wave9 remoto (em execução, 5/5 COMPLETE verificados) | B: rascunho estrito (local, nunca executado) |
|---|---|---|
| Ramos do engine | Gera blend/pv/ours numa única chamada; só o blend alimenta o mecanismo | Engine modificado para gerar só blend |
| Falha de dependência (msbuddy) | Degrada com registro `DEGRADED` e publica base | Fatal, sem publicação |
| Execução remota | 5/5 COMPLETE; preview `degraded=[]`, cobertura 0.9975; hashes == expectativa local | Nenhuma; push bloqueado por limite de CPU (E034) |
| Risco de falha no rerun | Degradação registrada (atribuição parcial possível) | Zero fallback, mas código nunca testado nem em preview |

## Análise

1. **Ramos blend/pv/ours não são risco de falha:** o engine é byte-idêntico ao W088 que pontuou 0.341 cinco vezes em reexecução oculta (Wave7). As três saídas vêm de uma única chamada; ramos não usados não acrescentam caminho de erro, só tempo de CPU.
2. **Fallback DEGRADED é a escolha correta para canário:** a pergunta do canário é "fonte corrigida consegue nota válida?". Se o msbuddy falhar no rerun oculto, A publica a base e a submissão é pontuada (~0.341 esperado, detectável); B morreria e viraria uma sexta rejeição sem informação. Preview rodou limpo (`degraded=[]`), então a expectativa real é o mecanismo completo.
3. **Reteste explícito:** os CSVs públicos são iguais aos do preview Wave8 rejeitado. Isso é deliberado — isola a correção de código como única variável. Não é previsão inédita; exige aprovação explícita de Victor (gate `corrected_rerun_explicitly_approved`).
4. **B sem preview não pode receber slot:** submeter kernel nunca executado violaria a regra de preview COMPLETE + verificação antes do envio. Se o canário A falhar com o mesmo erro genérico, B ganha peso causal e deve ser pushado para preview (slots CPU agora livres).

## Sequência liberada por esta revisão (pendente de autorização de Victor)

1. `send_next_batch.py --execute --variant top1` (canário) com janela e aprovação registradas.
2. Consulta única de nota/erro após avaliação. Sem polling.
3. Nota válida → liberar os quatro restantes (cada um com sua aprovação). Erro igual → não reenviar; pushar preview do rascunho estrito e registrar E029-atualizado.

Causa exata do E029 continua desconhecida; nada aqui a afirma.
