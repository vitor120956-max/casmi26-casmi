# Recon — CASMI26, 27/09/2026 ~22:09 BRT

## Placar verificado ao vivo
Fonte: API Kaggle + CSV oficial de leaderboard nesta consulta (não o snippet da busca, que estava atrasado).
- Victor alexandre / victor120956: **330/1682**, score **0.341**.
- Top5: Ozymandias31415 0.425; pikachu 0.421; Udam Liyanage 0.414; Randy 0.411; Shehab Alshehabi 0.404.
- Corte top5: **0.404**; gap aritmético para 0.341: **0.063**. Não é estimativa de probabilidade de alcançar o top5.
- Leaderboard mostra 55 entradas ranqueadas/contabilizadas na linha do time; a quota/API de submissões registra 60 totais, com os cinco Wave8 ainda PENDING.
- URL: https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/leaderboard

## Novas respostas do organizador

### CFM-ID 4: aval explícito
https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/743774

David Healey (Competition Host), resposta com atividade em 27/09, confirmou:
> “CFM ID 4 is fine. It's published by a major lab in a major journal, so we'll proceed with the assumption that the authors had permission to distribute the weights.”

A pergunta tratava dos modelos stock treinados em METLIN. A resposta libera especificamente CFM-ID 4; **não generalizar para qualquer modelo/derivado de NIST ou METLIN**. Também não tratar como evidência de ganho de leaderboard. Próxima frente possível: auditar evidência de fragmentação/espectros simulados e sua cobertura, licença efetiva dos artefatos e custo CPU, antes de qualquer probe. Não foi instalado, treinado nem submetido nada nesta consulta de notícias.

### Enveda-180 no Zenodo: autorizado
https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/743569

David Healey (Competition Host):
> “Yes you can use the Zenodo release”

A pergunta era sobre o release Enveda-180 como dado externo para treino/biblioteca de referência. Outro participante questiona se já está incluído em train.parquet; isso **não foi auditado aqui**. Antes de adicionar, medir sobreposição para não tratar duplicação de dados como mecanismo novo.

## Latência e depuração: separar relatos de confirmação oficial
- https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/742789
  Há relatos de participantes de avaliações levando algumas horas. Não é SLA, confirmação de falha da plataforma nem diagnóstico dos nossos submits.
- https://www.kaggle.com/competitions/enveda-CASMI26-molecule-id-mass-spectra/discussion/742463
  Um participante relata divergência entre execução interativa e rerun oculto, com fallback levando a zero. Staff `inversion` não confirmou a causa; informou que não fornece suporte individual e indicou https://www.kaggle.com/code-competition-debugging.

## Nosso lote, consulta única desta retomada
Wave8: cinco PENDING, nenhuma nota/erro reportado. Referência 0.341. Quota: 5 usados, 0 disponíveis, 60 totais. Nenhum reenvio, publicação no fórum, novo kernel, GPU ou timer nesta consulta.
