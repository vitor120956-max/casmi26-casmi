# Próximo lote CASMI — preparação, não autorização automática

Atualizado: 2026-09-28T22:40:21.854116-03:00.
Arquivos tecnicamente verificados: 5/5. Liberados para envio: 0/5.
Nenhum envio realizado. Nenhum timer armado. As 21h de 28/09 já passaram; não foi reagendado silenciosamente para outro dia.

| Variante | Execução | Arquivo verificado | Bloqueios |
|---|---|---|---|
| top1 | COMPLETE | SIM | SOURCE_RUNTIME_POLICY_REVIEW_REQUIRED; REPAIR_RETEST_REQUIRES_EXPLICIT_REVIEW |
| adduct | COMPLETE | SIM | SOURCE_RUNTIME_POLICY_REVIEW_REQUIRED; REPAIR_RETEST_REQUIRES_EXPLICIT_REVIEW; WAIT_FOR_CANARY_RESULT_REVIEW |
| adduct_dedup | COMPLETE | SIM | SOURCE_RUNTIME_POLICY_REVIEW_REQUIRED; REPAIR_RETEST_REQUIRES_EXPLICIT_REVIEW; WAIT_FOR_CANARY_RESULT_REVIEW |
| formula_dedup | COMPLETE | SIM | SOURCE_RUNTIME_POLICY_REVIEW_REQUIRED; REPAIR_RETEST_REQUIRES_EXPLICIT_REVIEW; WAIT_FOR_CANARY_RESULT_REVIEW |
| top1_dedup | COMPLETE | SIM | SOURCE_RUNTIME_POLICY_REVIEW_REQUIRED; REPAIR_RETEST_REQUIRES_EXPLICIT_REVIEW; WAIT_FOR_CANARY_RESULT_REVIEW |

## Sequência preparada
1. Confirmar fonte, versão, arquivo e mecanismo efetivamente executado.
2. Resolver a política de fallback dos Wave9 existentes e o reteste dos CSVs públicos já rejeitados.
3. Liberar apenas um envio corrigido, após revisão e autorização. Não há envio automático neste programa.
4. Conferir nota, erro e atribuição desse controle antes de liberar os outros quatro.
5. Reconsultar quota antes de qualquer envio; a disponibilidade da preparação não reserva vagas.

Passar nos testes públicos não prova compatibilidade com todos os dados ocultos. A causa exata da Wave8 continua sem confirmação.
