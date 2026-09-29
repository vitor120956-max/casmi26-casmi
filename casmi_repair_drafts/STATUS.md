# CASMI — correção local e reconciliação de execuções

## Correção local realizada
- selected_variant_runtime.py processa apenas o mecanismo escolhido. Sem limite rígido97.5%: ausência explícita de fórmula preserva somente a ordem daquela molécula e é registrada.
- Erros reais de instalação/modelo/contrato continuam fatais, semCSVsubstituto. Logs identificam a etapa da falha.
- Builder reduz também saídas internas do engine a blend; não valida CSVsours/pv não escolhidos. Os dois rankers continuam necessários ao cálculo do blend.
- IDs normalizados/reordenados com validação, sem quantidade fixa400.
-86testesPASS:64anteriores+22novos. ResourceWarningtratadocomoerro.
- Comparação de pós-processamento com caches:400moléculas emcadauma das5variantes idênticas às previsõesWave8 anteriores. Não houve novo cálculo completo dos modelos.

## Kaggle — tentativa e bloqueio
Um único push privadoCPU do rascunho top1 foi tentado; APIretornou Maximum batch CPU session count of5reached. NenhumaURL/versãofornecida, execução não confirmada. Semretry.

## Execuções já existentes descobertas
Consulta aos20kernelspróprios maisrecentes encontrou5Wave9isolatedRUNNING. Uma entrada semref foi pulada após corrigir a validação. Fontes/metadados desses5 recuperados read-only, CPUprivados, hashes emremote_wave9_reconciliation/manifest.json. Nenhumcancelamento ou alteração.

Os5nãoestavam no diário/local disponíveis; origem ainda precisa ser reconciliada. Uma consulta às submissões confirmou ausência de novosenviosWave9 na resposta; últimosenvioscontinuam os5Wave8falhos.

Esses remotos NÃO são os rascunhos construídos nesta retomada: conservam3saídasnoengine e têm fallbackDEGRADEDexplícito parafalhamsbuddy. Portanto, seus resultadosnão validam automaticamentenossonovo runtime.

## Próximo passo
Não abrir outra execução nem submeter lote. Na próxima consulta pontual, conferir resultados dos5 járodando, ler publicação/logs/DEGRADED e reconciliar qualimplementaçãoestáautorizada. Confirmar comVictor se vieramdeoutrasessão. Semsleep/poll.

E029: a causa concreta das rejeiçõesWave8 continua desconhecida. Os consertos locais corrigem riscos reproduzidos, não constituem prova do erro oculto nem de nova nota.
