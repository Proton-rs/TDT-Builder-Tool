# AGENTS.md — src/tdt/dados

## Purpose
Serviços de dados compartilhados: lista padrão ADMS e índice vetorial (gerados uma vez, cacheáveis).

## Local Contracts
- `lista_padrao.py`: lê a Lista Padrão ADMS (default `docs/Pontos Padrao ADMS_v2.xlsx`, ver `defaults.py`; v1 fica no repo como histórico — não editar v1, é a lista oficial compartilhada) — DiscreteSignals/AnalogSignals; colunas por nome; ignora linhas inválidas (#N/A). `SinalPadrao.tipo_medicao`/`unidade_exibicao` lidos de `AnalogSignals` (`TIPO DE MEDIÇÃO`/`UNIDADE DE EXIBIÇÃO`), consumidos por `engine_tdt._valores_analog` (Measurement Type/Display Unit, tradução PT→EN).
- `indice_vetorial.py`: FAISS IP sobre vetores L2-normalizados; **encoder injetado** (`list[str]->ndarray`) para testabilidade; persistível; rebuild por hash do conteúdo.
- `encoder.py`: wrappers lazy de SentenceTransformer (`criar_encoder`, com `prefixo` p/ e5) e CrossEncoder (`criar_scorer_cross_encoder`). Não testar com modelo real (lento/download).

## Work Guidance
Embedding atual MiniLM; e5 (intfloat/multilingual-e5-base, prefixos query:/passage:) vence o benchmark — troca pendente.

## Verification
`python -m pytest -q tests/test_lista_padrao.py tests/test_indice_vetorial.py`
