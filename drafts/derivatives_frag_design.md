# Design: Derivados bio-plausíveis + gating por FRAG (o anti-starkhushi-E)

Data: 19/09/2026 · Status: DRAFT de engenharia · Prioridade: fim de semana (20-21/09)

## Por que existe
- prvsiyan (docs): ~57% das verdades do hidden estão a 1–2 deltas biossintéticos do melhor análogo encontrado. O pool não as contém; o ranker não as distingue.
- starkhushi E (público, 0.335→0.335): expansão naive de derivados COMO CANDIDATOS + ranker existente = NEUTRO. Conclusão: adicionar não basta; o ranker (31 features pré-treinadas, sem retrain possível) trata derivado e análogo com as mesmas features → diluição.
- Nosso diferencial obrigatório: **regra de troca (swap) pós-ranker com evidência de fragmentos**, não adição cega.

## Pipeline proposto (pós-ranker, mesmo slot onde a fusão λ vivia)
1. **Geração** (por molécula de teste, só se top-K análogos fortes existem — lv.max() ≥ τ_analog, ex. 0.99):
   - Transformações RDKit EditableMol sobre o SMILES do análogo:
     ±CH₂ (14.01565), ±O (15.99491), ±hexose (162.05282), +acetil (42.01056), ±2H (2.01565), −H₂O (18.01056)
   - Enumerar posições quimicamente válidas (grupos funcionais presentes), canonicizar (SMILES+InChIKey14), dedup vs pool (não duplicar candidato existente).
   - Filtro de massa: derivado precisa cair na janela de precursor da query (±10 ppm) — senão é candidato impossível, descartar.
2. **Evidência de fragmentos** (MetFrag-lite já existente no canônico):
   - Para cada derivado: explained_fraction E_deriv (fração da massa dos íons de fragmento explicada).
   - Para o análogo pai: E_parent.
3. **Regra de swap conservadora**:
   - Promover derivado ACIMA do pai somente se: E_deriv ≥ E_parent + margin (ex. +0.10) E derivado na janela ppm E transformação ∈ lista branca bio-plausível.
   - Nunca tocar rank 1 a não ser que margin seja grande (ex. +0.20) — gating cauda-como-fusão.
   - Cap: no máximo 2 swaps por molécula.
4. **Hooks de log** (verificação obrigatória):
   - `DERIV-gen: <n> molecules com análogo forte; <m> derivados gerados; <k> na janela ppm`
   - `DERIV-swap: <s> swaps; margin med <x>; E_deriv med <y>`

## Validação offline SEM slots (o santo graal — resposta à pergunta #1 do starkhushi)
- Amostra: 200 moléculas do TRAIN com verdade conhecida (espectros timsTOF se possível p/ casar domain).
- Rodar o pipeline canônico local (sandbox: pool amostrado ~50k p/ caber em RAM/CPU; fp models v4 em CPU p/ amostra pequena; MetFrag-lite é python puro).
- Métricas: (a) recall ganho: verdades ausentes do pool que a geração recupera; (b) precisão do swap: das promoções feitas, quantas movem a verdade p/ cima no ranking (MRR local delta); (c) calibração do margin.
- Se MRR local da amostra subir → probe LB (1 slot). Se não subir → ajustar margin/τ ou matar a lane com evidência.

## Riscos
- CPU local p/ fp inference: lento; mitigar com amostra 200 + batch pequeno (~10 min aceitável).
- Pool amostrado muda distribuição de análogos → recall absoluto não compara com LB; usar só DELTAS (com/sem derivado).
- Overfit do margin na amostra → manter regra simples (2 parâmetros), sweep grosso.

## Custos
- 0 slots até a validação offline passar; 1 slot p/ probe LB; ~1 dia de engenharia.
