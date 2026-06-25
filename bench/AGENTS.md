# AGENTS.md — bench

## Purpose
Harness de benchmark e diagnóstico para medir qualidade de matching (gate de regressão da análise).

## Local Contracts
- `rotulos.py`: ground-truth curado (descrição real → sigla ADMS). Cada sigla DEVE existir na lista padrão.
- `benchmark.py`: compara métodos no ground-truth (acc@1, recall@3, precisão@decididos, taxa). Métodos pesados (e5/reranker) em try/except. Escreve `resultados/benchmark.log`. stdout reconfigurado p/ UTF-8 (Windows).
- `diag_colunas.py`: audita detecção de header/colunas por sheet → `resultados/diag_colunas.log`.
- `resultados/`: logs para leitura humana — não versionar como fonte da verdade.

## Work Guidance
- Ampliar `rotulos.py` é pré-requisito para Tier C (stacking/hard-negatives/augmentation).
- Achados atuais: tfidf+e5+fuzzy = 82%/95% (melhor); reranker mmarco descartado.

## Verification
`PYTHONPATH=src python bench/benchmark.py` (compara; não deve regredir acc@1/precisão).
