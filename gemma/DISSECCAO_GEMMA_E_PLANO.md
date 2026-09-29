# Gemma: auditoria técnica e plano de decisão

**Para Victor · Consolidado em 28/09/2026**  
Pesquisa de regras, fontes e placar: 27/09. Auditorias locais executadas em CPU. Atualização CASMI: 28/09, 09:16 BRT.

> **Veredito:** existe espaço para investigar um agente melhor, mas ainda não demonstramos vantagem competitiva no Gemma. O primeiro investimento deve ser uma versão-base reproduzível e uma comparação controlada — não treino caro. CASMI fica preservado, agora com prioridade de diagnóstico porque os cinco envios Wave8 falharam na reexecução.

## 1. O que foi realmente investigado

- Regras da competição, descrição dos dados, paper track e licença do modelo.
- Inventário oficial completo: **524 arquivos**, sem baixar os 22,42 GB inteiros.
- As **129 tarefas públicas**, com análise estatística dos patches de referência, sem fornecê-los a um agente.
- Quatro grafos: um snapshot por repositório. Um snapshot de código HTTPX, lido como dados, sem executar seu código.
- Código de sete notebooks públicos: starter oficial, Roman, parthenos, Black Cat e três auditorias da comunidade.
- Pacotes oficiais `adk-submission 0.2.11`, `adk-eval-core 0.1.0` e `swegemma 0.2.7`, obtidos do wheelhouse indicado pelo Kaggle. Inspeção de fonte e testes de módulos específicos, **não instalação/execução do stack completo**.
- Cinco testes CPU de contratos do loader YAML e consulta de embeddings: **5 PASS**. Uma verificação adicional confirmou que a auditoria HTTPX inclui seus dois pacotes.

**Não realizado:** inferência Gemma, treino, uso de GPU, submissão Gemma, compilação completa ADK, reprodução do placar de terceiros ou execução dos 129 casos. Não temos nota própria Gemma. Esta é uma auditoria aprofundada dos materiais disponíveis, não certificação completa de execução.

## 2. O desafio e as restrições que mudam a estratégia

O agente recebe um problema de software e um repositório Python. Precisa editar a implementação e entregar um patch. O avaliador aplica esse patch em ambiente separado e verifica os testes. A nota mede a proporção de tarefas resolvidas — não a qualidade da explicação. [Visão geral](https://www.kaggle.com/competitions/gemma-4-developer-agent/overview)

| Item | Consequência prática |
|---|---|
| **1 submissão por dia** | Não importar a rotina de cinco envios diários do CASMI. Cada envio precisa responder uma pergunta útil. |
| Até 2 submissões finais | Preservar um controle confiável e comparar alternativas antes da escolha. |
| Modelo obrigatório: `gemma-4-31b-it-qat-w4a16-ct` | Todos os agentes e subagentes usam a mesma base. |
| LoRA opcional | É possível iniciar sem treino. Isso não torna a inferência gratuita. |
| `submission.zip`, com `agent.yaml` na raiz | O produto submetido é configuração declarativa, prompts, skills e adaptadores opcionais. |
| Contexto do avaliador: 32.768 tokens | O contexto anunciado para o modelo fora da competição não é o limite permitido aqui. |
| Limite global de 12 horas | Inclui preparação dos ambientes; exclui validação dos patches, conforme a visão geral. |
| Tarefas sequenciais | Paralelizar subagentes não significa executar todas as tarefas em paralelo. |
| Até cinco integrantes | Colaboração exige equipe formal; uma conta por pessoa, sem contas alternativas. |

Datas: entrada/união de equipes em **25/11**; final principal em **02/12, 23:59 UTC (20:59 BRT)**. Premiação principal: US$37 mil, US$18 mil e US$10 mil, para os três primeiros. A classificação final depende do conjunto privado e da conformidade com as regras, não apenas do placar público. [Regras](https://www.kaggle.com/competitions/gemma-4-developer-agent/rules)

**Atenção aos defaults:** o README descreve limites padrão, mas uma resposta do staff diz que, no scorer, a ausência dos quatro campos de orçamento significa ausência de limite. Não precisamos resolver essa divergência por suposição: vamos definir explicitamente `timeout_seconds`, `max_tool_calls`, `max_time_minutes` e `max_turns`. O staff confirmou execução sequencial e informou que atingir 12 horas então causava erro, com correção planejada. Uma pergunta posterior ainda estava sem resposta. **Não assumir que o excedente já passou a valer apenas zero.** [Resposta do staff](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743063) · [Pendência posterior](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743964)

## 3. O que os dados públicos mostram — medido por nós

| Repositório | Tarefas |
|---|---:|
| FastAPI | 67 |
| Rich | 48 |
| Requests | 13 |
| HTTPX | 1 |
| **Total** | **129** |

**FastAPI e Rich representam 115/129, aproximadamente 89% do conjunto público.** Isso torna perigoso otimizar o agente para os nomes, convenções ou distribuição desses dois projetos: a descrição oficial diz que o teste foi obtido de repositórios privados. [Dados oficiais](https://www.kaggle.com/competitions/gemma-4-developer-agent/data)

Outros resultados de `audit_data.py`:

- **127 pares únicos repositório/commit**: existem dois pares de tarefas que compartilham snapshot. Eles devem permanecer juntos ao separar desenvolvimento e avaliação.
- **91/129 patches de referência alteram um único arquivo**. A mediana é um arquivo; o percentil 90 é quatro; há casos de até 26 arquivos.
- Mediana de **8 linhas adicionadas e 3 removidas**. Isso favorece começar com edições pequenas, mas não prova que os problemas sejam fáceis.
- **15 patches incluem `docs_src/`**. Nesse conjunto, exemplos executáveis de documentação podem ser código-alvo; não excluir toda documentação indiscriminadamente.
- Todos os campos `hints_text` estavam vazios nesta versão.
- Há extremos: patch com mais de 300 mil caracteres. Não dimensionar memória, contexto e validação apenas pela mediana.

Criamos uma divisão determinística por repositório/commit: **80 desenvolvimento, 24 validação, 24 avaliação congelada e um smoke test HTTPX**. É uma proposta de engenharia, não um benchmark independente: os rótulos públicos já são acessíveis. Para avaliar generalização, também precisamos deixar um repositório inteiro fora do ajuste. O único caso HTTPX não permite estimar desempenho nessa família.

Arquivos de evidência: `research/task_profile.json` e `research/split_v1.json`. O primeiro registra o SHA-256 da versão de tarefas analisada.

## 4. Achados técnicos que podem mudar o próximo agente

### 4.1 A busca por similaridade não é um buscador de perguntas

O código oficial de `embed()` procura uma chave de símbolo existente ou um sufixo dessa chave no arquivo de embeddings. **Não gera um embedding neural de uma frase livre.** Nosso teste CPU confirmou que uma chave exata e seu sufixo retornam vetor; uma pergunta em linguagem natural sem chave correspondente retorna `None`.

O prompt inicial sugere buscar usando palavras do erro, o que pode não satisfazer esse contrato. A correção proposta é buscar primeiro identificadores no código e só então considerar a ferramenta de similaridade. Não é ganho de placar medido.

Evidência: `swegemma/graph/embedding_utils.py` do wheelhouse oficial; `audit_harness_cpu.py`.

### 4.2 Funções assíncronas estão ausentes como nós

Nos quatro grafos amostrados, não encontramos nós cujo código próprio começa com `async def`. Fizemos uma verificação mais forte no snapshot HTTPX, incluindo **`src/httpx` e `src/ahttpx`**:

| Entidade da biblioteca | Encontradas no código | Presentes no grafo |
|---|---:|---:|
| Classes | 75 | 75 |
| Funções/métodos síncronos | 520 | 520 |
| Funções/métodos assíncronos | **98** | **0** |

Escopo: 32 arquivos Python de biblioteca, definições de módulo e métodos de classes; funções locais aninhadas não integram essa contagem. **Não extrapolar esses totais para as 129 tarefas.** Uma classe pode conter texto de métodos assíncronos sem que eles tenham nós individuais pesquisáveis.

A comunidade já havia identificado esse problema, e o staff confirmou que as funções assíncronas ainda faltavam. Portanto, **não é uma descoberta exclusiva nossa**. Oportunidade: medir se busca textual e um índice AST que inclua `AsyncFunctionDef` reduzem falhas do agente. [Discussão e resposta](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/742911)

### 4.3 Grafos podem devolver texto demais

Na amostra FastAPI, um nó contém **356.100 caracteres de código** e 34 nós excedem 10 mil caracteres. O caminho de `search_similar_code` examinado coloca o código dos resultados na resposta sem corte nesse trecho.

Isso é risco de consumo excessivo de contexto, não prova de que todas as chamadas transbordem. A ferramenta de comando ter saída limitada não garante limite equivalente para toda ferramenta de grafo.

Proposta: versão-base com buscas curtas e leitura por intervalos; testar navegação adicional apenas com saídas limitadas. Não começar com uma arquitetura que despeja classes inteiras no contexto.

### 4.4 Relações de grafo são mais estreitas que os exemplos de documentação

Os quatro grafos examinados só tinham arestas do tipo **`calls`**. Não supor cobertura de `IMPORTS` ou `DEFINED_IN` só porque esses exemplos aparecem na documentação. Precisamos de descoberta de capacidades e caminho alternativo por leitura de código.

### 4.5 `../` interno no include não era um defeito confirmado

A investigação anterior levantou dúvida sobre `!include ../prompts/analyzer.md`. O loader oficial **aceitou** essa referência quando o destino permaneceu dentro da raiz. Os testes também confirmaram rejeição de escape da raiz e de symlink.

**Conclusão corrigida:** não alterar o exemplo por esse motivo sem necessidade. Esse teste verifica resolução de YAML, não validação completa do agente.

## 5. O que as soluções públicas ensinam

| Fonte inspecionada | O que aproveitar como estudo | O que não assumir |
|---|---|---|
| [Starter oficial](https://www.kaggle.com/code/ryanholbrook/getting-started-gemma-4-developer-agent) | Instalação do wheelhouse, serving, avaliação de duas tarefas e empacotamento | Rodar o notebook inteiro exige GPU; não é só gerar um ZIP. |
| [Roman](https://www.kaggle.com/code/romanrozen/gemma-eda-baseline-for-a-start-lb-top-1) | EDA, localização lexical, montagem de analisador + programador | “TOP 1” no título não demonstra liderança atual nem reproduzibilidade nossa. |
| [Parthenos](https://www.kaggle.com/code/nihilisticneuralnet/0-10-gemma-4-developer-agent-submission) | Separação explícita entre pipeline local e configuração submetida | Código Python de desenvolvimento não vira automaticamente ferramenta do scorer. |
| [Black Cat](https://www.kaggle.com/code/lucifer19/black-cat-swe-agent-pack-instinct) | Buscas curtas, revisão do diff, controle de contexto e comparação com controle | O challenger consultado não tinha nota confirmada no próprio manifesto; complexidade não prova melhoria. |
| [Auditoria do avaliador](https://www.kaggle.com/code/busyaprime/119-of-129-sound-the-gemma-4-grader-rebuilt) | Separar falha de ambiente, teste e solução; testar o próprio instrumento | “119/129” é resultado do avaliador reconstruído pelo autor, não reprodução nossa nem teto oficial. A afirmação antiga de ausência do harness já não vale: obtivemos os wheels. |
| Auditorias públicas de Woldy | Cobertura de grafos e contrato de consulta | Não copiar conclusões para uma versão nova sem conferir arquivos e escopo. |

Nenhum desses notebooks foi executado nesta investigação. Os arquivos possuem manifesto de ref/caminho/hash para atribuição. Examinar código público não equivale a ter licença verificada para qualquer redistribuição; antes de incorporá-lo, conferir licença, atribuição e compatibilidade.

## 6. Infraestrutura e riscos operacionais

### Confirmado nas fontes consultadas

- O staff declarou o **wheelhouse oficial como referência de pacotes** e disse que **ADK 2.x não é suportado**. Nosso snapshot contém `google-adk 1.36.1`, `adk-submission 0.2.11` e `swegemma 0.2.7`. Não trocar versões por conveniência. [Resposta oficial](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743800)
- Ferramentas Python próprias devem ser empacotadas como **scripts de skills**, executados na sandbox — não imports arbitrários no host. [Resposta oficial](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743573)
- Houve falha de recursos reconhecida pelo staff, que anunciou correção e reexecução dos afetados. Isso é específico daquele incidente; não diagnostica automaticamente toda falha posterior. [Comunicado](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743683)

### Ainda incerto

- Um participante reportou adaptadores LoRA aparentemente carregados, mas sem efeito; o staff respondeu que trataria o problema. Não encontramos nessas páginas confirmação conclusiva de correção. Antes de treinar, testar **base versus adaptador** em entradas fixas e verificar se há alteração mensurável. [Relato e resposta](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/743508)
- O tratamento do limite de 12 horas precisa ser reconfirmado antes do primeiro envio.
- Distilação de modelos externos ainda tinha pedido de esclarecimento sem decisão final do staff na página consultada. Além da regra Kaggle, valem os termos do fornecedor e a licença de publicação. Não iniciar essa frente por suposição. [Discussão](https://www.kaggle.com/competitions/gemma-4-developer-agent/discussion/742807)
- Não medimos nossa disponibilidade efetiva de GPU, filas, velocidade de inferência ou custo financeiro. Relatos de outros competidores não substituem essa medição.

## 7. Custo: o que conseguimos fazer sem GPU

**CPU agora:** análise dos dados, inspeção do harness, testes de parser/YAML, preparo do pacote, desenho das ablações, análise de logs e ferramentas AST. Tudo isso já pode reduzir erros antes de gastar a submissão diária.

**Precisa de inferência:** medir quantas tarefas o agente resolve, latência, custo de contexto, efeito dos prompts e das ferramentas. O avaliador usa quatro L4; isso não significa que precisamos comprar quatro GPUs nem que sua disponibilidade pessoal esteja garantida.

**Treino:** é uma fase posterior, opcional. Só justificável quando temos um gargalo demonstrado, dados adequados, caminho de LoRA funcionando e orçamento autorizado.

Com aproximadamente 120 tarefas ocultas, 720 minutos dão uma média bruta de **6 minutos por tarefa antes dos custos adicionais**. Um limite de 8 minutos por tarefa poderia somar 960 minutos caso todos o atingissem; não é uma escolha segura sem medir término antecipado e overhead. Um cap de 3 minutos somaria 360 minutos de laço do agente, mas também **não garante** terminar em 12 horas.

Fórmula de planejamento: `tempo total ≈ inicialização do modelo + Σ(preparação da tarefa + execução do agente)`. Validação dos patches fica fora desse limite segundo a visão geral. Medir média e cauda, não só o caso mais rápido.

Não há estimativa monetária confiável ainda. Nenhuma contratação, treino ou uso de GPU foi realizado nesta pesquisa.

## 8. Plano experimental recomendado — sem loteria

| Etapa | Pergunta | Evidência necessária para avançar |
|---|---|---|
| G0 — Contrato | Nosso pacote compila no stack oficial? | Compilação completa, sem adaptadores pendentes, formatos e versões conferidos. Os cinco testes atuais não substituem isso. |
| G1 — Controle | Um agente simples resolve tarefas com custo aceitável? | Primeira avaliação autorizada, patches e logs por tarefa; separar erros de infraestrutura de respostas erradas. |
| G2 — Localização limitada | Busca textual + índice AST com async melhora o controle? | Comparação pareada, mesmas tarefas, modelo e orçamento; nenhum patch de referência no contexto do agente. |
| G3 — Verificação/edição | Estamos encontrando o arquivo, mas falhando ao editar ou testar? | Medir edição bem-sucedida, patch não vazio, regressões e tempo; mudar apenas o mecanismo diagnosticado. |
| G4 — Delegação | Um analisador separado ajuda além do seu custo? | Só testar após G1–G3; registrar chamadas compartilhadas e contexto economizado. |
| G5 — LoRA | Existe erro recorrente que treino pode corrigir? | Aprovação de recursos, teste de efeito do adaptador, licenças e conjunto de treino/validação adequados. |

**Versão-base proposta, ainda não construída/avaliada:** um agente sem LoRA, ferramentas básicas, busca lexical, leitura limitada, edição pequena, teste direcionado, inspeção do diff e `submit_patch()` por último. Orçamento explícito; sem acesso às respostas de referência. Não hardcodar nomes dos quatro repositórios públicos.

Métricas: tarefas resolvidas; falhas de ambiente; primeira edição; patches vazios; erros de ferramenta; tempo até localizar/editar/testar; chamadas; tokens; regressões. O gargalo pode ser edição ou raciocínio, não localização: o problema de grafo sozinho não decide isso.

Uma melhora isolada no placar público pequeno não comprova generalização. A descrição oficial fala em cerca de 120 tarefas divididas entre público e privado; com aproximadamente 60 públicas, um caso pode representar cerca de 1,7 ponto percentual. Não usar a diferença entre duas notas arredondadas como certeza estatística.

**Critério de investimento:** expandir apenas se execução e medição forem viáveis e uma mudança mostrar benefício reproduzível. Caso contrário, documentar e reduzir esforço; não avançar para treino para compensar falta de diagnóstico.

## 9. Chance competitiva e alternativa de pesquisa

Na fotografia de 27/09, o Gemma tinha **687 times**, líder em **0.15** e terceiro em **0.13**. Não temos nota própria. Esses números não são comparáveis ao 0.341 do CASMI: métricas e tarefas são diferentes.

Começar cedo aumenta o tempo disponível para aprender, mas muitas ideias de navegação, orçamento e contexto já aparecem publicamente. Nossa vantagem teria de vir de **execução confiável, diagnóstico e melhoria medida**, não apenas de conhecer esses problemas.

O paper track oferece outra saída, não uma premiação fácil: prazo **12/11**, até **3.000 palavras**, pesquisa original e não publicada. Avalia novidade, qualidade/generalização, relevância, verificabilidade e clareza. Há categorias de melhor artigo, novo recurso e nova aplicação. Um recurso de avaliação ou navegação pode ter valor, mas precisa de resultados e contribuição além de corrigir um problema já conhecido. Não é obrigatório competir no ranking principal. [Paper track](https://www.kaggle.com/competitions/gemma-4-developer-agent-paper/overview)

## 10. CASMI: mantido, com mudança no estado da Wave8

Consulta única em **28/09, 09:16:58 BRT**:

- Os cinco refs **56624670, 56624671, 56624673, 56624674 e 56624675** estão `COMPLETE` com erro de reexecução, **sem nota** e com zero bytes reportados pela API.
- Mensagem: “Your notebook hit an unhandled error while rerunning your code. Note that the hidden dataset can be larger/smaller/different than the public dataset”.
- **Não são mais pendentes. Não houve cinco comparações pontuadas.** Referência confirmada continua em **0.341**.
- Quota na consulta: cinco usados, zero disponíveis, 60 envios totais.
- Nenhum reenvio. Nenhuma tentativa de contornar o 403 dos artefatos avaliados da Wave7.

A mensagem é genérica e não identifica a linha que falhou. A inspeção estática encontrou pontos a investigar: cobertura mínima de fórmula de 97,5%, contratos de IDs/tipos e cálculo/validação de variantes que nem sempre são a variante submetida. **São hipóteses e dependências compartilhadas, não causas comprovadas.**

Próximo esforço CASMI: diagnóstico da reexecução e testes com entradas perturbadas antes de novo lote. Não restaurar publicação antecipada/fallback de blend apenas para obter uma nota: isso destruiria a atribuição do experimento.

O reporter também foi corrigido: não orienta mais “aguardar notas” para um lote encerrado com erros. Cinco testes de regressão passaram; o relatório foi refeito a partir da evidência salva, sem segunda consulta ao Kaggle.

## 11. Sua pergunta: o CASMI pode ser usado para construir outra IA?

**Sim. O aproveitamento mais próximo é um sistema de busca e priorização molecular:** espectro → processamento → candidatos ordenados → evidências → revisão do pesquisador.

| Possível reutilização do CASMI | O que já ajuda | O que falta |
|---|---|---|
| Buscador de moléculas por espectro | Pipeline de candidatos, features e ranking | Validar fora da competição, adaptar formatos e expor limitações |
| Busca por similaridade química | Representações e bibliotecas utilizadas | Definir a métrica de utilidade e auditar licenças |
| Organizador de dados científicos | Padronização, deduplicação e verificações | Regras próprias do laboratório e avaliação com usuários |
| Assistente conversacional de química | Motor especializado como ferramenta de um LLM | Interface, explicações baseadas em evidência e revisão humana |
| Outros projetos de ML | Versionamento, testes, validação, auditoria e controle de experimentos | Adaptar ao novo problema; modelos químicos não viram programadores |

Isso seria construir **uma aplicação de IA especializada**, não criar um modelo geral do zero. Não há produto pronto nem garantia de mercado. O 0.341 do concurso não é probabilidade de uma identificação individual estar correta. O pipeline depende de componentes de terceiros e deve separar nossa contribuição do que reutilizamos.

**Projeto de reaproveitamento que recomendo, se quisermos produto depois:** protótipo de buscador molecular com conjunto externo de avaliação, painel de candidatos e rastreabilidade de evidências. Primeiro demonstrar utilidade; só depois pensar em serviço comercial.

## 12. Licenças, publicação e manutenção

A ficha oficial do Gemma 4 aponta Apache 2.0, que permite usos comerciais sob suas condições. Isso não licencia automaticamente todos os dados, ferramentas e modelos auxiliares. [Ficha do modelo](https://www.kaggle.com/models/google/gemma-4/other/gemma-4-31b-it-qat-w4a16-ct) · [Licença](https://ai.google.dev/gemma/apache_2)

As regras da competição indicam uso comercial dos dados, mas também contêm obrigação de não disponibilizar Competition Data a quem não aceitou as regras. **Não publicar os arquivos brutos de competição em GitHub público por inferência de que “Apache” resolve tudo.** Antes de exportar: conferir obrigações do evento, licenças por componente, atribuições e possível esclarecimento do organizador. Esse cuidado também deve ser feito separadamente para as fontes do CASMI.

Materiais da investigação permanecem locais. Nenhum push remoto foi feito. O histórico local que contém materiais oficiais deve passar por revisão de exportação antes de qualquer publicação; apenas adicionar `.gitignore` não remove cópias históricas.

### Próxima ação concreta

**Manter duas frentes estreitas:** CASMI em diagnóstico de reexecução; Gemma em G0, validação do contrato de uma versão-base sem LoRA. Sem abrir um terceiro produto agora e sem autorizar GPU/treino por implicação. O aproveitamento futuro do CASMI fica documentado e preservado.

---

### Evidência reproduzível no workspace

- `gemma/audit_data.py` → `research/task_profile.json`, `research/split_v1.json`.
- `gemma/audit_harness_cpu.py` → `research/cpu_contract_tests.json`, `research/graph_audit.json`.
- `research/wheelhouse_manifest.json` e `research/public_code_manifest.json`: origem e hashes.
- `wave8_after_send.json`, `WAVE8_RESULTADO.md`: estado oficial CASMI de 28/09.
- `ERROR_REGISTRY.md`, `incidents.jsonl`: erros operacionais, correções e hipóteses abertas.

**Distinção final:** testes de contrato passaram; capacidade de resolver tarefas Gemma ainda não foi medida. Falhas de CASMI foram observadas; a causa ainda não foi demonstrada.
