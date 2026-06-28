# AGENTS.md — src/tdt/analise

## Purpose
Análise de colunas e identificação de rota (homogênea/não-homogênea) das sheets de entrada.

## Ownership
- `analise_colunas.py`: localiza colunas-chave por CONTEÚDO (descrição via embedding, índice por inteiros, tipo por vocabulário). Exporta `analisar()`, `normalizar_emb()`.
- `identificador.py`: classifica sheets como "de dados" ou não; decide rota homogênea/não-homogênea. Exporta `classificar()`, `ler_rows()`, `Rota`.

## Local Contracts
- `identificador` importa `analise_colunas` via `.analise_colunas`.
- `vocabulario_tipo` (em `normalizacao/`) é importado via `tdt.normalizacao.vocabulario_tipo`.
- Módulo NÃO é detectado por coluna — vem do nome da sheet.

## Verification
`python -m pytest -q tests/test_analise_colunas.py tests/test_identificador.py`
