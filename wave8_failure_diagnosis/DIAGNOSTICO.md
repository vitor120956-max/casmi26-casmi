# Wave8 — o que sabemos sobre as cinco rejeições

Mensagem oficial: erro não tratado na reexecução. As cinco terminaram sem nota. Não é evidência de modelo ruim, duplicação, erro de formato inicial ou bug do Kaggle.

## Confirmado no código e reproduzido em CPU
1. Todos abortam se o msbuddy não fornecer fórmula para pelo menos97.5% das moléculas. Cenário sintético97/100 derrubou o guard dos cinco fontes;97.5% e100% passaram.
2. Todos validam todos os ramos (inclusive controles não submetidos). Um ramo auxiliar inválido interrompe o loop antes de publicar um escolhido estruturalmente válido. Reproduzido nos cinco.
3. Os arquivos distintos não forneciam isolamento de falhas: o pipeline compartilhado pode derrubar o lote inteiro.

## Limitação
Não há traceback oculto identificando qual condição ocorreu. Esses testes não demonstram a causa real dos cinco erros. Nenhum novo dado oculto foi obtido; nenhuma tentativa de contornar403. Evidência mais recente continua a consulta28/09 09:16.

## Próximo trabalho
Separar mecanismo escolhido de diagnósticos/variantes opcionais; não tratar cobertura científica como validade estrutural universal; testar mudança de IDs, quantidade, adutos, cobertura e falha de dependência. Preservar publicação atômica e falha explícita de erros estruturais. Não reenviar pacote antigo nem retirar todas as validações indiscriminadamente.

Reprodutor: audit_wave8_failure_modes.py.25checagens de reproduçãoPASS, não25correções. Fontes/hash/resultados em synthetic_reproductions.json. Responsabilidade operacional: a validação prévia foi insuficiente para o lote compartilhado; testes de preview/publisher não provaram portabilidade do pipeline inteiro.
