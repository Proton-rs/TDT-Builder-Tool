# AGENTS.md — src/tdt/matchers

## Purpose
Métodos alternativos de matching, candidatos a benchmark. Complementam os scorers de `scoring/`.

## Local Contracts
- `fuzzy_match.py`: rapidfuzz token_set_ratio + boost de sigla literal. fonte="fuzzy".
- `cross_encoder.py`: rerank de top-k com scorer injetável (callable `[(query,doc)]->[float]`). fonte="rerank". **Benchmark mostrou que o reranker mmarco PIORA** — não usar em produção sem novo benchmark.
- Não apagar métodos originais (`scoring/`) ao adicionar candidatos.

## Work Guidance
TDD com fake injetável (encoder/scorer) — nunca baixar modelo em teste unitário.

## Verification
`python -m pytest -q tests/test_fuzzy_match.py tests/test_cross_encoder.py`
