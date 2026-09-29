# Atualização 27/09 22:04 BRT

**Os cinco candidatos foram validados e enviados. Todos PENDING; quota 0 livre.** Ver `WAVE8_RESULTADO.md` e retomar somente com `python report_wave8.py`. O plano abaixo agora é histórico/metodológico, não uma ordem para reenviar.

---

# Wave8 — plano para o reset de 27/09 21h BRT

**18h: um candidato validado e quatro kernels CPU em execução. Nenhum submit novo; quota atual 0 disponível / 5 usados / 55 totais.**

| Tag | Mecanismo | Decisão que muda o próximo build | Estado |
|---|---|---|---|
| formula_dedup | Fórmula top5 após dedup/refill | Manter combinação apenas com ganho confiável sobre W088 0.341 | COMPLETE + VERIFY PASS |
| top1 | Só a primeira fórmula promove candidatos | Medir se maior seletividade evita promoção espúria; comparação sem/com refill | RUNNING |
| top1_dedup | Top1 após dedup/refill | Comparar top1 vs top5 com refill constante | RUNNING |
| adduct | Fórmula por aduto/polaridade; votação por grupos | Testar correção da evidência heterogênea, sem refill | RUNNING |
| adduct_dedup | Evidência por aduto após dedup/refill | Comparar contra formula_dedup (mesmo refill); contra adduct (efeito do refill) | RUNNING |

## Justificativa, não loteria
Perfil oficial: 400 moléculas / 1213 espectros; **108** moléculas com vários adutos e **97** com polaridades mistas. O método legado fundia tudo sob o primeiro aduto. Novo agrupamento: **513** grupos consistentes, sem perda de picos. Dentro de cada grupo: precursor mediano e espectros com o mesmo aduto/polaridade. Fórmulas agregadas por número de grupos que as sustentam e soma de 1/rank para desempate. Para grupo único preserva top5 do próprio grupo.

Top1 mantém o restante da ordem W088; não há sweep de pesos/seeds. Localmente, as duas variantes top1 mudam 148 linhas em relação às respectivas bases e têm hashes novos. Novidade das duas variantes por aduto só pode ser confirmada após outputs; não enviar se duplicarem qualquer arquivo conhecido ou outro slot.

Os cinco usam a publicação atômica corrigida, CPU-only, sem tier2/MIST-blend/dataset próprio. Golden hashes ficam apenas nos verificadores locais. **59 testes passaram**, incluindo 9 novos de agrupamento/evidência.

## Retomar
1. `bash arm.sh`
2. `python -m unittest -q test_safety_guards test_atomic_submission test_formula_evidence`
3. `python verify_wave8_extra.py` — uma leitura de status por kernel, sem polling. Gera wave8_extra_ready.json apenas para arquivos aprovados e distintos. Candidato combinado já consta em wave8_ready.json.
4. Antes das 21h: **não enviar**. Às/depois das 21h: `python submit_wave8.py` é só dry-run. Com quota e arquivos conferidos, `python submit_wave8.py --execute` envia apenas prontos, conhecidos e não enviados, priorizando mecanismos.
5. Janela do script: 27/09 21h a 28/09 21h BRT. Não reutilizar para outro dia/onda. Journal antes de cada pedido; erro interrompe; nenhum retry cego.
6. Consultar notas uma vez após avaliação; não declarar 5/5 ranqueado pelo aceite. Não usar report Wave7 para interpretar automaticamente Wave8.

**Sem duplicatas para completar 5:** se houver erro, no-op ou arquivo idêntico, preservar slot e registrar; não substituir por controle repetido.

## Evidências e persistência
- wave8_ready.json: combinado verificado (sha e46a74a79a5ddd594486f3f9dc7449c6735cbcaf8278da2c40135a4786b9ebb3).
- wave8_extra_plan.json: slugs/versões/perguntas das quatro novas probes.
- wave8_extra_remote_verify.json: quatro códigos e metadata CPU conferidos, RUNNING no pós-push.
- wave8_mechanism_profile.json: perfil de adutos e dois hashes esperados top1.
- Publicações anteriores protegidas: não repushar kernels Wave7; não reutilizar variantes antigas bloqueadas.
- Git: alterações em commit local, push remoto desta rodada não realizado.
