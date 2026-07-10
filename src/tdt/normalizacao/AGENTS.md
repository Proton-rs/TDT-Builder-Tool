# AGENTS.md — src/tdt/normalizacao

## Purpose
Normalização e estruturação do dado de entrada: do texto bruto da planilha até descrições canônicas + `SignalRecord` montados.

## Ownership
- `normalizador.py`: pipeline N0..N5 de normalização de descrições (N0=contexto estrutural, N1=abreviações, N2=IDs, N3=boilerplate, N4=typos, N5=unidades). Exporta `canonizar()`, `extrair_contexto_estrutural()`, `FASES`.
- `tokenizer.py`: rejunta siglas separadas por espaço (ex. "67 N" → "67N").
- `vocabulario_tipo.py`: vocabulário de classificação Discreto/Analógico/Comando. Exporta `classificar()`, `CODIGOS_TIPO`.
- `estruturador.py`: monta `SignalRecord` a partir de linhas de sheet não-homogênea (marcadores de seção, coluna Tipo). Exporta `estruturar()`, `_parse_indices()`.
- `estruturador_homogeneo.py`: caminho determinístico para sheets homogêneas com cabeçalho fixo. Exporta `detectar_header()`, `estruturar_homogeneo()` (retorna 4-tupla `(decididos, pendentes, revisao, avisos)`; usa `identidade_homogenea.resolver()` para nome de módulo/equipamento; tipo `A/D` → `DiscreteAnalog`/`Input`; sigla em `config.siglas_sem_ponto` (ex. COMTAP) vai pra `revisao` com motivo `comando_tap_nao_modelado` em vez de virar sinal; lint não-bloqueante compara NOME do cliente x nome calculado).
- `identidade_homogenea.py`: resolve módulo/equipamento do caminho homogêneo pelo bloco de cabeçalho (spec 2026-07-10). Exporta `extrair_bloco()`, `resolver()`, `Identidade`.

## Local Contracts
- Módulos usam imports relativos entre si. `normalizador` → `.tokenizer`, `estruturador` → `.normalizador` + `.vocabulario_tipo`.
- `FASES` é público e consumido por `engine_tdt` (dropdown de Phases).
- `config.py` e `contracts.py` são importados via `..config` / `..contracts`.

## Work Guidance
TDD. `normalizador` é o módulo mais crítico — qualquer mudança impacta todos os scorers. Benchmarkar em `bench/`.

## Verification
`python -m pytest -q tests/test_normalizador.py tests/test_tokenizer.py tests/test_vocabulario_tipo.py tests/test_estruturador.py tests/test_estruturador_homogeneo.py`
