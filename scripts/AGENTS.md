# AGENTS.md — scripts

## Purpose
Scripts utilitários avulsos de calibração, treino e enriquecimento de dados. **Não fazem parte do pipeline principal** — são ferramentas de suporte.

## Ownership
- `calibrar.py`: treina calibrador probabilístico (Platt/isotonic) combinando scores tfidf+fuzzy+vetorial contra ground-truth. Lê lista padrão, executa scorers, treina calibrador, salva parâmetros.
- `enriquecer_v5/`: geração da Lista Padrão v5 com descrições enriquecidas (ANSI C37.2 + domínio). Módulos: `ansi_ref.py` (códigos ANSI), `composer.py` (composição de descrições), `mapa_dominio.py` (domínio por sigla), `gerar_v5.py` (script principal). Testes próprios em `test_*.py`.
- `treino/`: geração de mockups/corrupção para treino de modelos. Módulos: `mockup.py` (gera descrições sintéticas a partir da lista padrão), `corrupt.py` (aplica corrupções realistas), `dump_mockup.py` (exporta mockups para CSV). Testes próprios em `test_*.py`.

## Local Contracts
- Cada subdiretório é auto-contido com seus próprios testes (`test_*.py`) e `conftest.py`.
- Importam módulos do pipeline principal via `tdt.*`.
- Não criar dependências entre `enriquecer_v5/` e `treino/`.

## Verification
`PYTHONPATH=src python -m pytest -q scripts/enriquecer_v5/ scripts/treino/`
