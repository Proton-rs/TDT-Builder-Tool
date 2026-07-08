# AGENTS.md — src/tdt/dados

## Purpose
Serviços de dados compartilhados: lista padrão ADMS e índice vetorial (gerados uma vez, cacheáveis).

## Local Contracts
- `lista_padrao.py`: lê a Lista Padrão ADMS (default `docs/Pontos Padrao ADMS_v2.xlsx`, ver `defaults.py`; v1/v3/v4/v5 ficam no repo como histórico — não editar, são listas oficiais compartilhadas. v4 = v3 com descrições ANSI melhoradas + DJF1 enriquecido resgatado da v2 - Não usar v4, poís piorou o benchmark) — DiscreteSignals/AnalogSignals; colunas por nome; ignora linhas inválidas (#N/A). `SinalPadrao.tipo_medicao`/`unidade_exibicao` lidos de `AnalogSignals` (`TIPO DE MEDIÇÃO`/`UNIDADE DE EXIBIÇÃO`), consumidos por `engine_tdt._valores_analog` (Measurement Type/Display Unit, tradução PT→EN). `SinalPadrao.type_severidade` (só discretos, coluna `TYPE SEVERIDADE`; `None` em analógicos) — lido mas não consumido no matching (tentativas de regra de desempate e de enriquecimento do corpus vetorial regrediram o gate `gate_tdt_real` e foram revertidas, ver `bench/resultados/spMET_baseline_gate.txt`). `descricoes_por_sigla(path) -> dict[str, str]` (sigla UPPER → descrição, `lru_cache`, `{}` se arquivo ausente/ilegível) alimenta o `Signal Alias` da TDT gerada a partir da lista padrão **v1** fixa (`defaults.DEFAULT_LISTA_ALIAS`), independente da lista carregada para matching — ver `engine_tdt.gerar(..., alias_v1=...)`.
- `indice_vetorial.py`: FAISS IP sobre vetores L2-normalizados; **encoder injetado** (`list[str]->ndarray`) para testabilidade; persistível; rebuild por hash do conteúdo.
- `encoder.py`: wrappers lazy de SentenceTransformer (`criar_encoder`, com `prefixo` p/ e5) e CrossEncoder (`criar_scorer_cross_encoder`). Não testar com modelo real (lento/download).

## Work Guidance
Embedding atual MiniLM; e5 (intfloat/multilingual-e5-base, prefixos query:/passage:) vence o benchmark — troca pendente.

## Verification
`python -m pytest -q tests/test_lista_padrao.py tests/test_indice_vetorial.py`
