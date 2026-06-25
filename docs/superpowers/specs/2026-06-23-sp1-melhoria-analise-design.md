# SP1 — Melhoria da Análise de Sinal (ensemble/scoring)

**Data:** 2026-06-23
**Status:** Spec aprovada para implementação
**Goal:** **certeza do sinal sem falsos positivos + taxa de decisão alta.**

## Evidência (benchmark, 28 pares rotulados, roteação pct≥0.45 gap≥0.08)

| método | acc@1 | prec@decididos | decid |
|---|---|---|---|
| tfidf+vet(MiniLM)+fuzzy (atual) | 79% | 88% | 86% |
| **tfidf+e5+fuzzy** | **82%** | **95%** | 75% |
| e5 sozinho | 75% | 0% | 0% |
| combo+rerank (mmarco) | 36% | 42% | 43% |

Decisões dirigidas por dado: **trocar MiniLM→e5**; **descartar o cross-encoder mmarco**; e5 sozinho decide 0% → **calibração é pré-requisito**.

## Componentes (cada um = módulo SRP, TDD; harness `bench/benchmark.py` é o gate de regressão)

### A. Calibração de scores — `scoring/calibracao.py`
Hoje somamos tfidf-cosine + e5-cosine + fuzzy-ratio, que vivem em escalas
diferentes (e5 comprime em ~0.8–0.9). Calibrar cada método para [0,1]
comparável (min-max sobre a distribuição do corpus, ou temperature scaling)
antes da mescla. Sem isso, pesos e thresholds enganam.
- `calibrar(scores, metodo) -> scores` com parâmetros por método (config).
- Critério: e5 passa a decidir >0% após calibração.

### B. Embedding e5 (assimétrico) — `dados/encoder.py`, `dados/indice_vetorial.py`
`intfloat/multilingual-e5-base` com prefixos `query: ` (consulta) e `passage: `
(corpus). `IndiceVetorial.construir(..., prefixo_passagem)` e `buscar(...,
prefixo_consulta)`. Config: `modelo_embedding`, `e5_prefixos: bool`.

### C. Roteação por consenso + gap dinâmico — `roteador.py` (estende, não apaga)
- **Voto/consenso**: decide só se ≥2 métodos calibrados concordam no top-1
  (acima do threshold). Mata FP de um score mediano puxando os outros.
- **Gap dinâmico**: gap exigido depende da confiança — todos altos → gap 0.05;
  só 1 método confiante → gap 0.15+. Config: `gaps_por_confianca`.

### D. Cascata com rastreabilidade — `roteador.py`
Decide em cascata pelo sinal mais confiável (fuzzy muito alto = grafia; e5 muito
alto = semântica; consenso = fallback) e **grava qual método decidiu** em
`SignalRecord.justificativa` (auditoria/UI). Mantém a saída do quadrante atual
como fallback.

### E. Desambiguação contrastiva de pares opostos (hard/soft negatives)
Sinais opostos recebem scores próximos por similaridade mas são contrários
(sobrecorrente×subcorrente, 59 sobretensão × 27 subtensão, TAP máx×mín,
ligado×desligado, barra×linha). Define um catálogo de **pares confusáveis** e,
quando o token discriminador está presente, **penaliza o candidato de
polaridade errada**. Implementado como regra (ver spec do motor de regras) e
referenciado aqui. Reduz ambiguidade dos casos mais perigosos para FP.

## Fora de escopo (Tier C — depende de ampliar o ground-truth além de 28)
Stacking meta-learner, hard-negatives em escala, data augmentation, active
learning. Pré-condição: expandir `bench/rotulos.py` (curadoria). Documentar como
fase futura.

## Critérios de sucesso
- tfidf+e5+fuzzy calibrado ≥ baseline atual em acc@1 **e** prec@decididos no harness.
- e5 calibrado decide >0%.
- Nenhuma regressão nos testes existentes; `justificativa` registra o método decisor.
