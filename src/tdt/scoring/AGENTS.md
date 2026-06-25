# AGENTS.md — src/tdt/scoring

## Purpose
Scorers que rankeiam candidatos de sigla a partir da descrição normalizada.

## Local Contracts
- Cada scorer devolve `list[Candidato]` (sigla, score 0..1, fonte) ordenado desc.
- `tfidf.py`: TF-IDF vs descrições da lista padrão (cosseno). `vetorial.py`: FAISS sobre embeddings. `mescla.py`: funde N fontes via `list[(candidatos, peso)]`.
- Scores de métodos diferentes vivem em escalas diferentes → calibração planejada (ver spec de melhoria da análise) antes de comparar/mesclar.

## Work Guidance
TDD; entrada é `SignalRecord.descricoes.normalizada`. Não acessar disco aqui (índice/corpus vêm prontos do chamador).

## Verification
`python -m pytest -q tests/test_scoring_*.py`
