# CASMI — preparação para envio em 28/09

Victor pediu preparar o próximo lote para HOJE às21h. Na solicitação já eram21h43BRT. Não agendar horário passado ou transferir silenciosamente para29/09. Nenhumtimer/disparoautomático.

## Estado da consulta21:56BRT
- Cota5enviosdisponíveis,60totais.
- Wave9top1_dedupCOMPLETE:arquivoverificadocommetadados/hash/IDs/SMILES/inputs ebaseline. degraded=[],coverage0.9975. SHA200764676509f414dd418c66a28c181fbc3daa1bb2716ac6ebb81a06b8566d43.
- Outros4Wave9RUNNING.1/5artefatostecnicamenteverificados,0/5liberadosparaenvio.
- Cincofontes/versionNumber1conferidosviaSDKget_kernel, hashesbatemcomfontesrecuperadas. CLIpullomiteversão;nãoinferir.

## Preparação executada
next_batch_preparation/plan.json eSTATUS.md. check_next_batch_once.py consultaumaúnicavez;semloopsdepoll/submit. batch_release_checks.py valida sem liberar automaticamente. send_next_batch.py seco porpadrão;--execute exigevariante,aprovaçãofonte/hash,retesteexplícito,janela temporal,quota,evidência econtroleconferidoantesdosdemais;intençãoatômicaemjournal. release_review.json permanece send_authorized=false.

100testesPASS;testeextra confirmaexecutesemaaprovaçãobloqueadoantesdeimportarAPI. Nenhumenviofoirealizado.

## Próximo
Uma consulta pontual por retomada, verificar outputs faltantes. Revisar política de fallback dosWave9externos econsiderarmesmopreviewdaWave8rejeitadacomofonteretestadacorrigida,nãoprediçãoinédita. Primeirocanárioplanejadotop1;outros4aguardamresultado/revisãodeste. Não sacrificarloteinteiroporhorário.

E029:causarealdeWave8desconhecida.E031corrigidorascunhoslocaisestritos(86testesanteriores),masfontesWave9emexecuçãodiferem:engineaindablend/pv/ours,exceçõesmsbuddyviramDEGRADEDregistrado.Revisãonecessáriaantesdeliberar.

Gemma/Solarpreservados,semGPU/treinonovo. Uma conta;semsleep/poll;primeiroarm.sh/transferência;errosregistrados;exportaçãopúblicabloqueadaatélicenças/históricosanitizado.

## Correção 30/09 (~19:35 BRT) — Victor
"Mas a ideia não é deixar a conta intacta e sim fazer 5 de 5" → quota de submissão é
recurso operacional, não troféu. Preservar quota NÃO é objetivo; o objetivo é executar
o plano completo (5/5) quando verificado, dentro da janela. Preservação só se aplica a
retrials cegos / envios duplicados / lixo científico.
