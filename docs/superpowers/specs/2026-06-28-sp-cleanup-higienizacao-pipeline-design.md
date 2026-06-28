# SP-Cleanup — Higienização do Pipeline

**Data:** 2026-06-28
**Status:** Aguardando revisão do usuário
**Origem:** Análise de bottlenecks do projeto — dívidas técnicas que impedem o pipeline de produção de ser confiável e portátil.

## Problema

O pipeline acumulou ao longo do desenvolvimento vários pontos que reduzem confiabilidade, testabilidade e portabilidade:

1. **cross_encoder.py** — módulo de reranker que o benchmark mostrou piorar o matching (acc@1 cai de 82% para 36%). Existe como código independente mas não é chamado pelo pipeline. Sem documentação clara de que não deve ser usado.
2. **Rota de consenso no roteador** — benchmark mostra precisão de 42% com taxa de decisão de 93%, ou seja, decide muito mas decide errado em mais da metade dos casos.
3. **filtro_preciso.py** — 278 linhas, 7 filtros de domínio, sem teste unitário direto (só `filtrar_especificidade()` tem teste).
4. **Fixture desalinhada** — `tests/conftest.py` aponta para `Pontos Padrao ADMS_v1.xlsx`, mas a produção usa v2 como default.
5. **rapidfuzz implícito** — usado em `fuzzy_match.py` e no `normalizador.corrigir_typos()`, mas não listado em `pyproject.toml`.
6. **config.toml com caminhos absolutos** — impossível compartilhar entre máquinas sem editar manualmente.

## Escopo

### Item 1: cross_encoder.py — documentar que não é para produção

Estado atual: o módulo existe em `src/tdt/matchers/cross_encoder.py`, tem factory em `src/tdt/dados/encoder.py`, e não é chamado por ninguém no pipeline. O AGENTS.md de matchers já menciona que "não usar em produção", mas é fácil de ignorar.

O que fazer:
- Adicionar docstring clara no topo do módulo: `DEPRECATED — não usar em produção. Benchmark mostrou que o reranker mmarco piora o matching (acc@1: 82% → 36%). Mantido apenas para referência histórica.`
- Remover a referência ao cross-encoder do pipeline config padrão (se existir) — verificar se `Config` tem campo para ele
- Não deletar arquivo nenhum

### Item 2: Rota de consenso — desativar por padrão

Estado atual: o roteador (`src/tdt/roteador.py`) aplica 4 passos em cascata: fuzzy altíssimo → e5 altíssimo → consenso → quadrante. O passo de consenso tem precisão de 42% no benchmark, contra 95% dos outros métodos.

O que fazer:
- Adicionar flag `Config.usar_consenso: bool = False`
- Em `roteador.rotear()`, pular o passo 3 (`_decidir_por_votos`) quando a flag for False
- Quando True, mantém o comportamento atual (para quem quiser testar/calibrar depois)
- Não deletar código do consenso

### Item 3: Testes para filtro_preciso.py

Estado atual: `src/tdt/filtro_preciso.py` tem 278 linhas com 7 filtros (provavelmente `f_r1` a `f_r6` + `f_equip`). A função `filtrar()` que aplica todos eles não tem teste direto. Só `test_filtro_especificidade.py` cobre a função `filtrar_especificidade()`.

O que fazer:
- Criar `tests/test_filtro_preciso.py`
- Testes para cada filtro individual: dado um `SignalRecord` + candidatos, verificar se o filtro remove/retém o esperado
- Teste para `filtrar()` integrado: garantir que todos os filtros rodam na ordem certa
- Casos de borda: lista vazia, todos removidos, nenhum removido

### Item 4: Fixture alinhar para v2

Estado atual: `tests/conftest.py:18` retorna `Pontos Padrao ADMS_v1.xlsx`, mas `src/tdt/defaults.py` aponta para v2.

O que fazer:
- Alterar `conftest.py` para usar v2
- Rodar a suite completa e verificar se todos os testes continuam passando
- Se algum teste quebrar, ajustar o teste (não o contrário — a v2 é a fonte da verdade de produção)

### Item 5: rapidfuzz no pyproject.toml

Estado atual: `rapidfuzz` é usado em `fuzzy_match.py` e no `normalizador.corrigir_typos()` (via `rapidfuzz.fuzz.ratio`), mas não está listado nas dependências.

O que fazer:
- Adicionar `rapidfuzz>=3.6` nas dependências principais em `pyproject.toml`
- (Ele pode estar vindo como dependência transitória de sentence-transformers, mas explícito é mais seguro)

### Item 6: config.toml portátil

Estado atual: `config.toml` (se existir como arquivo) tem caminhos absolutos `C:/Users/vinic/...`. Isso impede rodar o projeto em outra máquina.

O que fazer:
- Investigar onde/config.toml é usado exatamente
- Se for arquivo separado: tornar caminhos relativos ao diretório do projeto, ou usar variável de ambiente `TDT_DOCS_DIR`
- Se for gerado pela UI (`config_io.py`): ajustar o IO para salvar caminhos relativos
- Se não existir como arquivo (só dataclass Config em config.py): confirmar e remover este item

## Fora de escopo

- Melhoria de performance ou acurácia — só confiabilidade/testabilidade/portabilidade
- Refatoração de arquitetura (ex: separar roteador em sub-módulos)
- Cobertura de testes além do `filtro_preciso.py` (cada spec cuida dos seus)

## Critérios de aceite

1. `cross_encoder.py` tem docstring clara de DEPRECATED
2. `roteador.rotear()` pula consenso quando `config.usar_consenso=False` (default)
3. `tests/test_filtro_preciso.py` com 7+ testes e todos verdes
4. Fixture `conftest.py` aponta para v2 e suite toda passa
5. `rapidfuzz` listado em `pyproject.toml` → `dependencies`
6. `config.toml` (se existir) aceita caminhos relativos ou variável de ambiente
7. `python -m pytest -q` verde
