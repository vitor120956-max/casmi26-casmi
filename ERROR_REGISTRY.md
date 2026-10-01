# Registro de erros e prevenção — CASMI26

**Regra permanente do Victor, 26/09/2026:** todo erro deve ser registrado para evitar repetição. O agente assume os próprios erros; não transfere a responsabilidade para a transferência ou para o usuário.

## Protocolo obrigatório

1. **Interromper a ação com efeito externo** diante de falha não compreendida. Nada de retry cego.
2. Registrar data BRT, ação, evidência, impacto/quota, causa confirmada ou hipótese e estado.
3. Corrigir a causa e acrescentar uma trava executável quando possível; caso contrário, checkpoint explícito.
4. Criar teste de regressão local. Não gastar submissões para testar transporte, autenticação ou formato já conhecido.
5. Reconciliar API, journal e quota antes de retomar. Preservar o registro da tentativa anterior.
6. Atualizar este arquivo, `incidents.jsonl`, `day_watch.log` e handoff. Commit local não significa push remoto.
7. **Antes de novo build/push/submit:** ler os erros aplicáveis e executar `python -m unittest -v test_safety_guards` + `bash precheck.sh DIRETORIO` quando houver notebook.

**Verificação desta revisão:** 26 testes locais passaram; os quatro notebooks da Wave7 passaram novamente no precheck. Nenhuma nova submissão, push de kernel ou alteração de previsão foi feita para registrar estes erros. Testes locais não garantem disponibilidade/aceitação da API.

## Erros operacionais confirmados nesta conversa

### E001 — Nome de arquivo proibido no submit
- **Evidência/impacto:** às 21:05–21:06 BRT, pedidos de fórmula e ours rejeitados; resposta HTTP400: `Submission files must be named "submission.csv" for this Competition.` Quota confirmou que as rejeições não consumiram slots; apenas blend foi aceito, ref. 56592387.
- **Erro do agente:** o VERIFY verificava CSV/hashes, mas não o contrato externo de nome. O plano herdado não deveria ter sido tratado como prova de aceitação.
- **Correção/trava:** `validate_submission_plan` exige exatamente `submission.csv`, versão positiva, slug da conta e SHA256 conhecido. Quatro kernels CPU independentes foram criados para regenerar as variantes com o nome correto. Sem dataset próprio ou mudança de previsão.
- **Prova/estado:** testes rejeitam os quatro nomes alternativos e caminhos com prefixo. Atualização 26/09 22:40 BRT: correção validada em produção, quatro variantes aceitas (refs 56594468, 56594469, 56594472, 56594473), ainda PENDING. Não confundir aceite com nota. Tentativas preservadas em `wave7_rejected_attempts.json`.

### E003 — VERIFY local não equivale a aceitação nem nota
- **Evidência:** os arquivos alternativos eram válidos localmente e ainda assim rejeitados. W088 também tinha 392 placeholders CCO em 34 moléculas, apesar de estrutura CSV válida.
- **Trava:** distinguir `VALIDADO_LOCAL`, `ACEITO_COM_REF` e `RANQUEADO_COM_NOTA`. CSV conhecido, hash, IDs, número de candidatos e comparação de duplicatas continuam obrigatórios. Não rotular preenchimento CCO como estrutura química comprovada.
- **Prova/estado:** verificadores existentes + testes de plano/hash; o relatório não transforma status COMPLETE sem nota em sucesso. Dedup é uma hipótese científica, não correção de transporte.

### E007 — Dependências e credenciais presumidas persistentes
- **Evidência:** workspace inicial veio apenas com anexos; `arm.sh` não existia. Em restauração posterior faltavam CLI/RDKit; `.kaggle`, `.cache` e `.git/config` não são garantia de persistência.
- **Trava:** `arm.sh` restaura CLI, auth Kaggle do anexo e RDKit. Também restaura nome/e-mail Git e origin ausentes, sem inventar autenticação GitHub. Tokens ficam fora de commits/snapshots; não prometer que a autorização sobreviverá.
- **Prova/estado:** rearmes Kaggle/RDKit executados com sucesso; mudança do bootstrap Git passou verificação sintática. Recuperação inicial de workspace vazio continua exigindo arquivos/backup.

### E008 — Exceção HTTP registrada sem corpo
- **Evidência:** primeira rejeição de fórmula ficou registrada apenas como `HTTPError(400)`, atrasando a identificação do nome proibido. O pedido posterior de ours preservou o corpo explicativo.
- **Trava:** guardar código HTTP e corpo de erro da submissão no journal; guardar incidente com referência ao journal. Não usar `if response` para testar existência de uma resposta de erro — respostas 4xx são falsy em requests.
- **Prova/estado:** runners usam `response is None`; callbacks de falha do runner atual alimentam `incidents.jsonl`. Nunca registrar headers, tokens ou respostas OAuth brutas.

### E009 — Identificador OAuth incorreto no fluxo alternativo
- **Evidência/impacto:** depois de duas falhas de conexão na CLI, o agente usou por memória um client ID que não era o da GitHub CLI. Pediu uma autorização desnecessária; isso foi um erro do agente. A sessão não tinha escopos de escrita.
- **Trava:** ID correto confirmado no binário oficial e em `cli/cli/internal/authflow/flow.go`; constante central `GITHUB_CLI_CLIENT_ID`. `validate_oauth` rejeita outro ID antes do fluxo. Não adivinhar identificadores de aplicativos.
- **Prova/estado:** teste de aplicativo errado bloqueado. Fluxo correto teve push remoto confirmado. A sessão incorreta foi removida localmente; **isso não revoga a autorização no GitHub**. Revisão/revogação pelo usuário em Settings → Applications não foi confirmada.

### E010 — Permissão do dono confundida com escopo do token
- **Evidência:** `/repos/...` indicava `permissions.push=true`, mas o token não tinha escopos; o push retornou 403.
- **Trava:** conferir escopo `public_repo` ou `repo` antes de armazenar/usar a sessão, além da permissão no repositório. Identidade/ownership não bastam.
- **Prova/estado:** testes bloqueiam escopo vazio, gist e read:org. Após autorização correta com public_repo, push confirmado em main, sem force-push.

### E011 — Repetir autorização antes de diagnosticar transporte
- **Evidência:** duas tentativas pela CLI falharam em `login/oauth/access_token` com `connection reset by peer`; o usuário precisou autorizar novamente. O endpoint respondeu pelo cliente HTTP.
- **Trava/checkpoint:** depois da primeira falha, diagnosticar transporte antes de solicitar outro código. Fluxo oficial HTTP pontual, troca somente depois da confirmação do usuário; sem consultas repetidas de autorização.
- **Estado:** caminho HTTP funcionou com o ID correto. A causa de rede da falha da CLI não foi determinada; não declarar bug específico da CLI sem prova.

### E012 — Commit sem identidade após restauração
- **Evidência:** commit da correção Wave7 falhou com `Author identity unknown`; `.git/config` havia desaparecido.
- **Trava:** bootstrap restaura os metadados não secretos quando ausentes. Commit só pode ser declarado concluído após exit 0 e hash.
- **Estado:** identidade restaurada e commit 67e4074 criado. Mudança de bootstrap validada sintaticamente; autenticação de push é verificada separadamente.

### E013 — Artefatos de recuperação ignorados pelo Git
- **Evidência:** `git add` inicial recusou `probeout_w088` e `harness_data` por `.gitignore`; primeiro commit não continha esses CSVs.
- **Trava/checkpoint:** auditar `git diff --cached --stat` e `git ls-files`. Usar `git add -f` somente para arquivos explicitamente aprovados, nunca para pastas inteiras com credenciais/cache.
- **Estado:** os três CSVs W088 e sample oficial foram adicionados explicitamente no commit 0e9c0a1 e enviados. Não confundir arquivo local com arquivo commitado.

### E016 — COMPLETE sem nota interpretado como resultado
- **Evidência:** três submits Wave6 estavam COMPLETE e sem nota; consulta de 21:05 mostrou `errorDescription` de formato e `totalBytes=0`. A causa-raiz do formato não foi determinada. O nome literal exigido na Wave7 não explica automaticamente essas rejeições antigas.
- **Trava:** `classify_submission` prioriza erro, exige COMPLETE + nota finita para RANQUEADA, e aceita **0.000 como nota real**. Ausência de nota não é zero.
- **Prova/estado:** testes cobrem erro, PENDING, nota ausente, NaN/infinito e zero. Restrição a kernels baseados no dataset próprio permanece.

### E017 — Timer local tratado como infraestrutura durável
- **Evidência:** disparo de 21h não aconteceu; às 21:05 a conta tinha 0 submissões do novo dia. A retomada manual pelo ponto do Victor foi necessária. O ambiente havia sido restaurado; não há prova suficiente sobre a causa exata da morte do timer.
- **Trava/checkpoint:** timer é melhor esforço, nunca garantia. Retomar sempre por quota/API/journal; verificar duplicatas antes de qualquer envio. Scripts pontuais, sem sleep/poll.
- **Estado:** recuperação manual funcionou. Às 22:39, o timer de 22:15 também não havia enviado os quatro arquivos e não havia registro local de execução. Retomada manual concluiu 5/5 envios. Não rearmar outro timer entre sessões sem garantia de ambiente persistente; continuar pelo ponto do Victor. Causa da interrupção ainda não determinada.

## Erros históricos e riscos confirmados por arquivos recuperados

### E002 — Slug/competição/versão presumidos
- **Recorrência 28/09 ~21:08 BRT (agente da retomada Drive):** consulta de quota com slug suposto retornou HTTP403; slug real lido dos fontes e consulta refeita. Impacto: nenhum. Trava: ler COMP dos fontes antes de qualquer chamada; 403 em endpoint conhecido = checar slug antes de credencial.
- **Origem:** transferência relata mudança de slug no push e typo de competição. Não foi necessário provocar esse erro novamente.
- **Trava:** fonte da competição exata; conferir URL devolvida; puxar metadata/código remoto e comparar; fixar versão. Os quatro novos kernels foram conferidos dessa forma.
- **Teste:** competição errada, owner errado e versão ausente bloqueados localmente. Slug real ainda exige conferência remota após push.

### E004 — Precheck antigo exigia GPU
- **Evidência:** script recuperado exigia `enable_gpu=true`, incompatível com quota GPU esgotada e ordem atual. Não foi executado para lançar GPU.
- **Trava:** GPU e TPU explicitamente false. Documentos/scripts antigos não têm prioridade sobre a regra atual.
- **Teste:** ambos bloqueados pelo validador; metadata remota dos quatro kernels já conferida.

### E005 — Usar inputs/linhas de trabalho proibidos
- **Origem:** proibição atual de dataset próprio/posthoc; tier2-mixing e MIST-blend têm resultados negativos medidos. Não confundir assets públicos de modelos/msbuddy com dataset próprio de submissões.
- **Trava:** allowlist de assets, nenhuma fonte de outputs upstream, bloqueio de tier2 em código/inputs. Asset com “mist-msbuddy” no nome é permitido **somente pelo uso de msbuddy**, não autoriza blend MIST.
- **Teste/checkpoint:** own dataset, tier2 e kernel_sources bloqueados. Revisão do uso dos assets ainda obrigatória — allowlist não prova, sozinha, que todo algoritmo está correto.

### E006 — Notebook sem kernelspec
- **Origem:** transferência relata ERROR por notebook mínimo sem kernelspec.
- **Trava/teste:** `metadata.kernelspec.name=python3` e language=python obrigatórios. Teste sem kernelspec falha antes do push.

### E014 — Fingerprints tier2: 867 vs 6930 bits
- **Origem:** transferência e diário histórico, não reproduzido nesta revisão.
- **Correção histórica:** fingerprints a partir de SMILES/RDKit compatíveis com o modelo; dimensão conferida antes de matmul.
- **Prevenção atual:** tier2 continua proibido. Sem reativar linha morta para testar esse conserto; não marcar como retestado hoje.

### E015 — Massas tier2 fora de ordem
- **Origem:** transferência relata `tier2_mass.npy` desordenado.
- **Correção histórica:** argsort uma vez, preservando alinhamento com SMILES; busca por janela exige massas ordenadas.
- **Prevenção atual:** tier2 proibido. Quando qualquer pool usar searchsorted, monotonicidade e alinhamento devem ser verificados; este caso histórico não foi retestado nesta revisão.

## Experimentos encerrados não são bugs a “consertar” sem hipótese nova

- **M001:** tier2-mixing 0.240 — não repetir/misturar no ranker.
- **M002:** MIST-blend 0.314 — não repetir; asset msbuddy não é licença para MIST-blend.
- **M003:** gated-slots 0.323 e lite/topk/priors/seeds neutros, conforme transferência — sem loteria para preencher quota.
- **M004:** deduprefill 0.000 é nota real, mas mecanismo/causa do fracasso continua sem diagnóstico conclusivo; não atribuir automaticamente ao servidor.

## Como registrar o próximo erro

Criar/atualizar item com: **ID → horário → ação → evidência → impacto/quota → causa ou hipótese → correção → trava → teste → pendência**. Não apagar tentativas anteriores. O runner registra automaticamente suas falhas de verificação/submissão em `incidents.jsonl`; outras ferramentas/fluxos exigem registro explícito pelo agente. Registro automático não significa diagnóstico automático.

**Persistência:** este registro, travas e testes serão commitados localmente. O push remoto desta revisão não foi realizado: credencial GitHub temporária não sobreviveu à restauração. Não solicitar autorização novamente sem necessidade da tarefa.

## Atualização 27/09 05:20 BRT — auditoria da Wave7

### E018 — Empate numérico confundido com comparação causal concluída
- **Fato:** cinco refs COMPLETE, sem erro, nota pública 0.341, totalBytes=488898 para todos. Redownload dos outputs publicados confirma cinco hashes distintos e tamanhos 394868 / 394868 / 409897 / 393760 / 395252 bytes.
- **Erro do relatório:** antes da auditoria, recomendava escolher o ramo simples e eliminar mecanismos só pelo empate. Essa conclusão foi retirada.
- **Trava/testes:** alerta de atribuição separa notas oficiais de conclusão causal. Metadados iguais **não provam** arquivo igual, bug do avaliador ou duplicação. Manter W088 blend como referência; nenhuma promoção/eliminação conclusiva. Quatro testes novos de atribuição passaram.

### E019 — Arquivo pontuado indisponível para auditoria
- **Fato:** método oficial SDK DownloadSubmission retornou HTTP403 nos cinco refs próprios, em chamadas pontuais paralelas. Outputs públicos do notebook continuam acessíveis, mas não substituem o artefato da avaliação.
- **Trava/checkpoint:** não repetir, contornar restrição, trocar credencial ou tratar output de notebook como arquivo comprovadamente pontuado. Registrar a limitação. Não presumir a causa da negativa de acesso.

### E020 — Publicação do arquivo-base antes da seleção final
- **Fato de código:** os quatro kernels escrevem o blend como submission.csv na célula 13; só depois verificam hashes e, na última célula, substituem pelo arquivo da variante. Se houver exceção nesse intervalo, o arquivo-base já existe. A validação anterior do agente não cobria esse caminho de falha.
- **Hipótese, NÃO prova:** uma reexecução que falhe na checagem pode deixar o blend disponível; não sabemos se o avaliador o consome. Isso pode explicar o empate, mas não foi confirmado por logs/arquivo da avaliação.
- **Trava/testes:** novo precheck rejeita múltiplas gravações no nome final e hashes-checagem posteriores à primeira publicação. Cinco testes novos de publicação passaram, incluindo rejeição dos quatro notebooks antigos. **Esses kernels NÃO foram corrigidos/repushados; foram bloqueados para reutilização.**
- **Próximo build obrigatório:** calcular a variante, validar, escrever staging e só então publicar atomicamente submission.csv. Falha de validação não pode deixar um arquivo final submetível. Fazer teste de injeção de falha antes de push; análise estática sozinha não prova todo o fluxo de I/O.

### E021 — Golden hashes/400 linhas fixos dentro da produção
- **Fato:** notebooks têm asserts contra hashes do preview e, em fórmula/dedup, contagem fixa de 400 fórmulas. Inputs legitimamente diferentes fazem essas guardas falharem. Não foi provado que os dados da avaliação mudaram neste caso.
- **Trava/checkpoint:** golden hashes pertencem ao teste local do fixture público. Na execução de produção, validar contra os IDs/contagem do sample dessa execução, sem forçar o hash de outra execução. O precheck rejeita os marcadores conhecidos dessas travas não portáveis; outros padrões ainda exigem revisão.

**Estado de prevenção agora:** 35 testes locais PASS. Os quatro notebooks antigos continuam passando nos checks de CPU/inputs/sintaxe, mas **devem falhar no novo check de publicação**. Isso é uma proteção intencional, não regressão a ser removida para permitir push.

## Atualização 27/09 ~17:10 BRT — correção executável E020/E021

- Novo módulo `atomic_submission.py`: remove final obsoleto antes da computação; valida dados do sample da execução; staging + única troca atômica final. Exceções exercitadas não deixam submission.csv, nem fallback para blend.
- Golden hashes ficam em `verify_wave8_atomic.py`, fora do notebook. Contagem/IDs de produção dependem do sample, não de 400.
- 15 testes dinâmicos novos passaram; total **50**. Incluem falhas antes/depois de validar, depois de staging, depois do manifesto e antes de publicar; erro de rename/serialização; sample alterado; limpeza de final antigo. Isso não confirma a hipótese sobre o scorer antigo.
- Novo kernel CPU de validação v1 lançado, ainda RUNNING na consulta inicial. Correção implementada/testada localmente, validação remota e nota ainda pendentes. Não remover bloqueio dos quatro kernels antigos.

## E022 — Risco de evidência de fórmula com aduto/polaridade heterogêneos (27/09 ~18h)

- Perfil medido no test oficial: 108/400 moléculas multi-aduto; 97/400 com polaridades mistas. Método legado combina picos e precursor mediano de todos os espectros sob o primeiro aduto.
- Isso viola a suposição de um único tipo de íon da feature; **efeito no LB ainda não medido**. Não declarar esse risco como causa dos cinco 0.341.
- Novas probes calculam fórmula por aduto/polaridade (513 grupos) e agregam suporte por grupos/rank. Top1 legado é outra hipótese explícita de seletividade, não a correção desse risco.
- 9 testes novos + ensaio real de preservação de todos os picos passaram (59 no total). Aduto/polaridade incoerente e grupos duplicados são bloqueados. Duas probes por aduto seguem em CPU; erros de runtime/duplicatas bloquearão submit.

### Validação remota E020–E022 — 27/09 22:04 BRT

Cinco candidatos Wave8 passaram nos testes/outputs de preview e foram aceitos para avaliação com refs distintos. Duas variantes por aduto tiveram novidades confirmadas (234/247 linhas alteradas vs blend), sem duplicatas. Publicação atômica e contratos dinâmicos funcionaram nos cinco previews. **Scoring ainda PENDING:** isso não prova ganho de mecanismo nem resolve a causa do empate Wave7. Nenhum erro novo detectado nesta rodada.

## E023 — Artefatos Gemma citados no handoff não estão disponíveis (27/09)

- **Evidência:** TRANSFER_26SEP.md menciona /home/user/gemma/ (HARNESS + baseline Roman) e GEMMA_RECON.md. A pasta/arquivo não estão presentes nos locais referidos; busca por nomes Gemma até profundidade 5 e lista de arquivos rastreados de recovered não os encontraram.
- **Causa:** desconhecida; não afirmar exclusão nem inexistência em backups externos.
- **Impacto:** fase 0 anterior não é reproduzível a partir destes artefatos; zero GPU/treino/submissão nesta verificação.
- **Correção pendente:** recuperar os originais ou reconstruir baseline usando o harness oficial. Não apresentar reconstrução como recuperação do original.
- **Trava:** não declarar baseline Gemma pronto/validado sem arquivos, validação do harness e resultado correspondente.
- **Teste:** conferência de existência e busca local realizadas; execução do baseline ainda não realizada.

## E024 — Mudança de prioridade categórica antes da comparação de viabilidade
- **Ação/evidência:** após confirmar que Gemma era o projeto alternativo, o assistente afirmou que Gemma passava a ser a prioridade, sem baseline Gemma medido e sem orçamento de execução definido. Usuário voltou a pedir ajuda para decidir, mostrando que a escolha definitiva ainda precisava de avaliação.
- **Impacto:** orientação instável/confusa; nenhum treino, GPU ou envio Gemma realizado.
- **Causa:** tratar novidade e preferência por começar cedo como justificativa suficiente para prioridade definitiva; não são evidência de maior chance de prêmio.
- **Correção:** distinguir preparação exploratória de compromisso de investimento. Preservar CASMI e seu lote pendente; propor etapa limitada de viabilidade Gemma, com critérios e autorização de recursos antes de execução.
- **Trava:** não classificar um projeto como mais provável de ganhar sem evidência comparável; não comparar notas brutas de métricas diferentes; prazo recente não implica liderança.
- **Verificação:** placares oficiais dos dois projetos consultados uma vez; Gemma sem linha do usuário no CSV; CASMI com 0.341 e cinco Wave8 ainda PENDING. Nenhuma avaliação Gemma iniciada.
- **Pendências:** baseline validado e medido, recursos disponíveis e comparação de ganhos reproduzíveis.

## E025 — Nome de enum presumido na API de tópicos Gemma
- Evidência: AttributeError em TopicListSortBy.NEW antes da chamada de rede. A SDK usa TOPIC_LIST_SORT_BY_NEW. O shell anterior devolveu exit0 por terminar em sed após falha Python.
- Impacto: consulta de tópicos não executada; zero quota de submit/GPU.
- Correção: usar membro inspecionado e set -euo pipefail em etapas encadeadas.
- Trava/teste: validar o membro real antes da chamada e salvar a resposta. Nenhum polling.

## E026 — Colisão de nomes ao baixar notebooks públicos de um mesmo autor
- Evidência: dois refs woldywei foram baixados no diretório do autor; ambos usam o mesmo code_file, sobrescrevendo notebook/metadados anteriores. Nenhum código foi executado.
- Impacto: atribuição da primeira cópia não era confiável; sem quota de submit/GPU.
- Correção: diretório exclusivo por owner/slug; preservar a cópia cuja metadata confere e baixar o outro ref no diretório correto.
- Trava/teste: manifesto relaciona ref, caminho, hash e id de metadata; não associar resultados só ao nome de arquivo.

## E027 — Auditoria de cobertura inicialmente restrita ao pacote homônimo do repositório
- Evidência: HTTPX snapshot contém src/httpx e src/ahttpx. O primeiro filtro leu só 16 arquivos httpx, excluindo a implementação assíncrona em ahttpx. Resultado parcial não foi apresentado como achado global ao usuário.
- Impacto: amostragem de cobertura incompleta; sem GPU/submit.
- Correção: auditar todos os módulos de biblioteca sob src/, excluindo testes; conferir inventário e contagem dos pacotes antes de generalizar.
- Trava/teste: a auditoria deve encontrar ambos os pacotes, pelo menos uma definição async e zero cobertura destas no grafo desta amostra. Não extrapolar totais para 129 tarefas.

## E028 — Referente da pergunta de reutilização interpretado incorretamente
- Evidência: usuário perguntou se o projeto poderia ser útil depois; assistente respondeu sobre Gemma. Usuário esclareceu que se referia ao CASMI.
- Impacto: resposta não atendeu à dúvida sobre valor do trabalho já investido. Nenhuma ação de GPU/treino/submit decorrente.
- Correção: explicar reutilização do CASMI como identificação/ranking molecular por espectrometria de massas, não agente de programação ou modelo geral. Separar protótipo competitivo de produto validado e licenciado.
- Trava: quando dois projetos estão em discussão, nomear explicitamente o projeto na resposta; perguntar se o referente for determinante e ambíguo.
- Verificação: esclarecimento explícito do usuário fixa CASMI como objeto desta dúvida.

## E029 — Wave8: cinco falhas na reexecução oculta, sem notas
- **Evidência:** wave8_after_send.json, consulta28/09 09:16:58BRT; refs56624670/671/673/674/675, todos COMPLETE com errorDescription genérica, publicScore=null, totalBytes=0.
- **Impacto:** cinco slots consumidos sem comparações pontuadas; quota5usados/0livres/60total. Melhor confirmado0.341.
- **Causa:** desconhecida. Inspeção estática encontra limiar de cobertura97.5%, contratos de IDs/tipos e execução/validação de variantes não selecionadas. São hipóteses, não diagnóstico causal.
- **Correção pendente:** reproduzir cenários de entrada diferente e isolar etapa da falha; obter logs apenas por meios oficialmente autorizados se disponíveis. Não repetir DownloadSubmission403 da Wave7 nem contornar acesso.
- **Trava:** não reenviar Wave8 idêntica, não promover mecanismos sem notas, não restaurar fallback silencioso/CSV antecipado. PreviewPASS não equivale a sucesso no rerun.
- **Teste:** evidência oficial preservada; novo diagnóstico ainda não executado.

## E030 — Reporter orientava aguardar notas de envios já rejeitados
- **Evidência:** reporter consultou cincoCOMPLETE com erro e terminou em Aguardar as notas faltantes.
- **Impacto:** próximo passo incorreto no relatório; nenhum reenvio ocorreu.
- **Correção:** next_step puro separa rejeições/pending/ausentes; adicionada renderização offline para corrigir relatório sem segunda consulta API; tabela de erros separada.
- **Trava/teste:** cinco testes cobrem lote rejeitado, pending, misto, ausente e nota0. CincoPASS. Relatório corrigido com --snapshot/--baseline0.341.
- **Pendência:** lógica corrigida não resolve falha dos notebooks.

## E031 — Wave8 compartilha trava de cobertura e validação de ramos não selecionados
- **Evidência estática:** os cinco notebooks submetidos contêm if coverage <0.975:raise MSBUDDY_COVERAGE_FAILED; todos percorrem variants.items() e validam cada ramo antes de publicar o escolhido.
- **Reprodução CPU:** extraídos viaAST o if e o loop dos cinco fontes, sem reescrever a lógica. Cobertura sintética0.97 falha nos5;0.975 e1.0 passam. Ramo selecionado válido + ramo auxiliar inválido causa INVALID_SMILES antes da publicação nos5.25checagensPASS (reproduzem vulnerabilidade, não provam correção).
- **Impacto:** uma condição legítima de menor cobertura ou erro em ramo auxiliar pode impedir todos os mecanismos de chegarem à avaliação. Risco comum não testado antes do lote.
- **Causa do E029:** ainda desconhecida; não afirmar que dados ocultos tinham cobertura97% ou SMILES inválido. Cenários são sintéticos, sem logs de rerun.
- **Correção planejada:** separar cobertura científica de validade do CSV; tratamento explícito e registrado de fórmula indisponível; calcular/validar apenas dependências necessárias ao mecanismo escolhido. Não substituir por fallback silencioso.
- **Trava:** novo lote depende de testes de portabilidade e isolamento dos ramos, além de preview. Nada foi repushado ou reenviado.

## E032 — ResourceWarning em fixture de teste local
- Evidência/correção: ArquivoCSV de teste foi aberto sem contextmanager. Corrigido com with; suíte executada novamente com ResourceWarning tratado como erro. Sem impacto em envios.
- Verificação:86testesPASS,22novos+64existentes. SemGPU/submit.

## E033 — Registro de falha podia permanecer após sucesso no protótipo local
- Evidência/correção: Revisão identificou selected_failure.json não limpo no início de nova execução. Corrigido com remoção explícita e teste falha→sucesso que verifica ausência de diagnóstico antigo. Sem deploy da versão defeituosa.
- Verificação:86testesPASS,22novos+64existentes. SemGPU/submit.

### E031 — atualização de correção local
- selected_variant_runtime.py aplica apenas ramo escolhido; erro de provider continua fatal; ausência explícita de fórmula mantém a ordem só daquela molécula e é registrada. Limiar97.5% removido como condição de validade.
- Builder de rascunhos reduz também CSVs auxiliares dentro do engine a blend somente, preservando os dois rankers necessários ao blend. IDstest/sample normalizados para string e ordenação final validada.
-86testesPASS (22novos),5comparações exatas de400registros usando bases/fórmulas/dedupcache. Não é rerun dos modelos. Integração real ainda pendente. CausaE029continua desconhecida.

## E034 — Kaggle bloqueou preview CPU por limite de sessões
- Evidência/ação: kernels_push retornou error=Maximum batch CPU session count of 5 reached. Nenhuma URL/versão de execução fornecida; preview não confirmado como iniciado. Não é nova rejeição de competição nem explica retroativamente E029. Sem retry ou cancelamento.
- Efeito: nenhuma submissão ou GPU.

## E035 — Consulta de estado recebeu ref de kernel vazia
- Evidência/ação: Lista mine retornou entrada sem ref utilizável; kernels_status rejeitou localmente antes de chamar rede. Corrigir validação e persistir listagem antes de iterar. Não assumir que toda entrada da API pode ser consultada.
- Efeito: nenhuma submissão ou GPU.

## E036 — Estado remoto contém cinco Wave9 ativos sem registro local
- Evidência: após bloqueio de CPU, listagem de kernels próprios mostrou cinco casmi26-wave9-isolated-*-cpu RUNNING, iniciados em28/09~21:21BRT. Não havia arquivos wave9 na busca local atéprofundidade3 nem lançamento no diário disponível. Não foram iniciados pela tentativa repair-v1 desta retomada.
- Impacto: recurso já ocupado e risco de duplicar trabalho/assumir autoria ou prontidão de artefato desconhecido.
- Ação: fontes/metadados dos5 recuperados read-only, hashes registrados. TodosCPU eprivados. Nenhumcancelamento/repush/retry. Consulta única às submissões não encontrou novo envioWave9; últimascontinuamWave8falhas.
- Diferença técnica: remotos retiram97.5%e loopauxiliar externo, mas engine ainda gera blend/pv/ours e exceções msbuddy viram DEGRADED registrado. Não equivalem ao rascunho local que isola também outputs do engine e deixa erro de dependência fatal.
- Trava: não submeter nem atribuir resultados remotos ao rascunho local; reconciliar origem e verificar outputs/DEGRADED antes de qualquer avanço. Préviaadicionalbloqueada, sem retry automático. CausaocultaE029segue desconhecida.

## E037 — Divergência entre Git atual e commits relatados na conversa
- Evidência na transferência: git log mostra HEAD272b189; a conversa relatou commits posteriores, inclusive8db4867. Arquivos recentes de preparação/reparo estão presentes no workspace.
- Causa: não determinada; não alegar exclusão, rollback voluntário ou falha de usuário.
- Impacto: Git sozinho não comprova preservação das mudanças recentes.
- Correção: backup dos arquivos atuais com manifesto SHA256; .git e credenciais excluídos. Novo agente deve usar o backup e conferir estado antes de clonar/push.
- Trava: não chamar commit de push; não presumir que histórico citado exista. Não sobrescrever fontes atuais pelo remoto antigo.

## E036 — RESOLUÇÃO DE ORIGEM (29/09 ~01:45 UTC / 28/09 22:45 BRT)
- **Origem identificada com evidência:** os cinco kernels `casmi26-wave9-isolated-*-cpu` foram construídos e pushados pela outra conversa ativa do Victor (retomada via ZIP Drive `195AQD...`), push às 21:21 BRT com verificação única pós-push (RUNNING, code_identical=true, GPU=false) registrada no `day_watch.log` mesclado e em `wave9_push_verify.json`/`wave9_plan.json` daquela sessão.
- **Prova técnica:** o código das células dos cinco fontes recuperados em `remote_wave9_reconciliation/` é byte-idêntico aos notebooks locais `kpush_wave9_*/wave9.ipynb` da outra sessão (comparação célula a célula nesta retomada). Builder/testes/auditoria daquela sessão: `build_wave9.py`, `wave9_runtime.py`, `test_wave9_isolation.py` (28 testes), `audit_wave9_failure_modes.py` (15 checagens), `WAVE9_PLAN.md`.
- **Ressalva mantida:** identidade de origem não é aprovação de envio. A revisão de política (fallback DEGRADED vs rascunho estrito; reteste de CSV igual ao preview Wave8 rejeitado) continua obrigatória antes de liberar qualquer slot.
- **Trava atualizada:** duas sessões compartilhavam a mesma conta sem saber; antes de criar kernels, listar kernels próprios (uma vez) para detectar trabalho paralelo.

## E038 — .git local perdido na ressincronização do ambiente
- **Evidência:** após troca de turno, `recovered/.git` ausente ("not a git repository"); commits locais 9d35398, ac6d4f7 e branch export-clean 1119e7d (desta retomada) e histórico desde 3c0974b não recuperáveis localmente. Arquivos de trabalho intactos.
- **Causa:** snapshots do ambiente excluem caminhos de credenciais Git; o diretório .git inteiro não sobreviveu. Não é exclusão voluntária.
- **Impacto:** Git local deixa de ser depósito durável neste ambiente; push remoto de 3c0974b permanece a única cópia histórica remota.
- **Correção:** repositório será reconstruído a partir dos arquivos atuais (backup + manifesto como referência, conforme E037) e exportado ao GitHub em branch limpa; commit local sozinho não é mais tratado como preservação.
- **Trava:** não prometer preservação por commit local; confirmar push remoto (ls-remote) para declarar algo salvo.

## E039 — Workspace estourou o orçamento de persistência
- **Evidência:** aviso da plataforma: 148,9 MB / 1.582 arquivos criados na sessão, acima do limite 128 MB / 10.000; 449 arquivos NÃO salvos no snapshot.
- **Causa:** espelho Git local (recovered/, 73 MB) duplicando o workspace + gemma/official (11 MB) + saídas e pulls regeneráveis acumulados.
- **Impacto:** parte dos arquivos da sessão não persistiu; nenhum dado crítico perdido (estado essencial estava no GitHub export-clean 4b689dc e nos JSONs de journal, íntegros).
- **Correção (regra permanente do Victor, 29/09):** workspace é área de trabalho EFÊMERA — nada é "salvo" nele. Persistência somente GitHub (branch export-clean, fluxo rebuild_export.sh + github_device_export.py) e/ou Drive do Victor. Início de conversa: clonar export-clean + extrair backup Drive anexado, depois arm.sh.
- **Trava:** conferir `du -sh /home/user` antes de encerrar turno; apagar artefatos regeneráveis (pulls remotos, outputs baixados, espelhos) logo após o uso; nunca manter duas cópias grandes do mesmo conteúdo.

## E040 — wave10_submit_state.json perdido entre turnos (30/09)
- **Evidência:** journal 29/09 21:08 BRT tem `WAVE10_SUBMITTED` x5 com refs, mas o arquivo de estado não estava no workspace em 30/09 08:13 (wave10_before_send.json e demais sobreviveram).
- **Causa:** não confirmada (snapshot entre turnos falhou para esse arquivo; causa-raiz desconhecida).
- **Impacto:** nenhum — reconstruído integralmente de journal + wave10_ready.json (redundância deliberada salvou o estado).
- **Correção:** estado crítico de envio deve ser pushado pro GitHub na mesma janela da ação, não adiado.
- **Trava:** após qualquer envio, incluir submit_state no próximo push imediatamente; journal continua sendo fonte secundária obrigatória de refs.

## E041 — ListSubmissions 403 / GetLeaderboard 404 bloqueiam leitura de scores (30/09 08:13 BRT)
- **Evidência:** `competitions.CompetitionApiService/ListSubmissions` → 403 (via API Python e CLI, sequencial e paralelo); `GetLeaderboard --show` → 404 nesse SDK (Kaggle CLI 2.2.4). Auth válida (kernels_status OK na mesma hora).
- **Causa:** não confirmada (auth OK; bloqueio específico do endpoint — provável rate-limit/mudança server-side do Kaggle).
- **Impacto:** scores da Wave10 (refs 56691295-97-98/99 e 56691304) ainda não lidos. Envios intactos; ausência de score ≠ zero.
- **Correção:** sem retry cego (regra). Uma única re-tentativa espaçada OU leitura pelo Victor na UI "My Submissions".
- **Trava:** não martelar o endpoint; registrar cada tentativa no journal.

## E042 — Glue Wave11 v1 omitiu campos instrument/CE exigidos pelo runner (30/09)
- **Evidência:** 5/5 kernels COMPLETE em ~1h com ice_meta n_mols_covered=0/n_scored=0 (status ok, rdkit 2025.03.6 instalado); diagnóstico local: 981/1213 espectros cobertos e 400/400 mols com grupos isômeros no top-25 => entrada inválida, não ausência de sinal.
- **Causa:** build_ice_items próprio passou só mz/it/prec/adduct/mode; o runner (instr_token/spectrum_ce) lê instrument/ce_ev/ce_orig/ce_units -> exceção por mol -> plans vazios (fail-safe absorveu, cobertura zero).
- **Impacto:** Wave11 v1 mediu NADA (artefatos = top1 legado; 4 probes bloqueados por dedup semântico E003; 1 passou mas sem ICE). Nenhum slot de submissão gasto.
- **Correção:** glue agora carrega os 4 campos; build_wave11 trava GLUE_MISSING_RUNNER_FIELD; v2 rebuild+push.
- **Trava:** verificar ice_meta.n_mols_covered>0 no verify_wave11 (assert adicionado na próxima edição do verificador).

## E043 — CE escalar derrubou 100% das linhas de espectro no glue v2 (30/09)
- **Evidência:** v2 COMPLETE com n_cands=9241 mas n_mols_covered=0; repro local: build_ice_items spectra=0 mesmo com covered_only=False.
- **Causa:** collision_energy_ev é escalar no test.parquet; list-comprehension inline levantou TypeError e o except largo descartou a linha inteira (o _flist do fuse original retorna None e preserva a linha).
- **Impacto:** v2 também mediu nada; nenhum slot gasto; ~1h de compute desperdiçado.
- **Correção:** _flist no glue (mz/it/ce_ev); smoke_wave11_runner.py como portão obrigatório pré-push (glue+runner reais, dados reais, coverage>0).
- **Trava:** nunca pushar Wave11+ sem rodar smoke_wave11_runner.py antes.
