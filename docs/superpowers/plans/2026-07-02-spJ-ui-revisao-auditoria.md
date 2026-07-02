# SP-J — UI revisão + auditoria estendida — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ou superpowers:executing-plans. TDD onde há lógica (proxy/model/auditoria); UI pura valida por smoke test manual roteirizado. Steps com checkbox.

**Goal:** abas por sheet + filtro estilo Excel + indicador de filtro + auditoria com máximo de informação (spec `2026-07-02-spJ-ui-revisao-auditoria-design.md`).

**Architecture:** filtro por coluna vive no `QSortFilterProxyModel` existente (`proxy_revisao.py`) com predicados por coluna; abas = `QTabBar` acima da tabela alimentando um predicado de sheet no mesmo proxy; auditoria estendida = colunas novas em `auditoria.py` alimentadas pelos campos já presentes no `SignalRecord`/pipeline.

**Tech Stack:** Python 3.14, PySide6/PyQt (conferir import em `ui/app.py`), pytest (com `pytest-qt` se já for dependência; senão testar o proxy sem Qt widgets).

## Global Constraints

- Lógica de filtro 100% no proxy model — testável sem abrir janela.
- Sem dependência nova.
- ~2.3k linhas (LISTA 1) sem travar UI: filtros aplicam em O(n) por mudança.

---

### Task 1: Auditoria estendida

**Files:**
- Modify: `src/tdt/auditoria.py` (colunas novas), ponto do pipeline que registra auditoria
- Test: `tests/test_auditoria.py`

**Interfaces:**
- Produces: `Auditoria_Revisao.xlsx` ganha colunas: `Sheet Origem`, `Desc Normalizada`, `Desc Canônica`, `Equip Alvo (N0)`, `Nome Equip`, `Barra`, `Fase`, `Estado Semântico`, `Regras Aplicadas`, `Gap`, `Gap Exigido`, `Etapa Decisora`, `Endereço Bruto`.

- [ ] Step 1: ler `auditoria.py` e o ponto do pipeline que popula as linhas; mapear quais dos campos acima já existem no record (`descricoes.normalizada`, `eletrico.*`, `justificativa`) e quais precisam ser propagados (gap/gap exigido: expor do roteador na justificativa estruturada ou campo novo; regras: `motor_regras.aplicar_rastreado` já devolve `ajustes` — pipeline:243).
- [ ] Step 2: teste RED — processa registro sintético e verifica presença + valor das colunas novas na planilha gerada.
- [ ] Step 3: implementar (propagação mínima: dict `diagnostico` por sinal montado no pipeline e passado à auditoria; nada de estado global).
- [ ] Step 4: testes PASS; reprocessar LISTA 1 e abrir o xlsx: colunas preenchidas para decididos E revisões.
- [ ] Step 5: commit `feat(spJ): auditoria estendida (contexto N0, regras, gap, etapa decisora)`

---

### Task 2: Sheet de origem no modelo + abas

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py` (expor sheet), `src/tdt/ui/tela_revisao.py` (QTabBar no lugar do filtro global), `src/tdt/ui/proxy_revisao.py` (predicado de sheet)
- Test: `tests/test_proxy_revisao.py` (criar se não existir)

**Interfaces:**
- Produces: `ProxyRevisao.set_sheet(nome: str | None)` — `None` = aba "Tudo".

- [ ] Step 1: teste RED do proxy:

```python
def test_filtro_por_sheet(qapp):
    modelo = _modelo_com_itens([("sig1", "Discreto"), ("sig2", "Analogicos")])
    proxy = ProxyRevisao(); proxy.setSourceModel(modelo)
    proxy.set_sheet("Discreto")
    assert proxy.rowCount() == 1
    proxy.set_sheet(None)
    assert proxy.rowCount() == 2
```

- [ ] Step 2: implementar predicado no `filterAcceptsRow`; abas na tela: `QTabBar` com uma aba por sheet distinta dos itens + "Tudo" (primeira); remover o campo de filtro global e seu wiring.
- [ ] Step 3: testes PASS; smoke manual: abrir revisão da LISTA 1, alternar abas.
- [ ] Step 4: commit `feat(spJ): abas por sheet na revisao (substitui filtro global)`

---

### Task 3: Filtro estilo Excel por coluna

**Files:**
- Modify: `src/tdt/ui/proxy_revisao.py` (predicados por coluna), `src/tdt/ui/tela_revisao.py` (popup no header)
- Test: `tests/test_proxy_revisao.py`

**Interfaces:**
- Produces: `ProxyRevisao.set_filtro_coluna(col: int, valores: set[str] | None)` (None = sem filtro), `ProxyRevisao.valores_unicos(col: int) -> list[str]`, `ProxyRevisao.colunas_filtradas() -> set[int]`.

- [ ] Step 1: testes RED

```python
def test_filtro_coluna_combina_and(qapp):
    proxy = _proxy_padrao()
    proxy.set_filtro_coluna(COL_MOTIVO, {"score_baixo"})
    proxy.set_filtro_coluna(COL_SHEET, {"Discreto"})
    assert all(_motivo(proxy, i) == "score_baixo" for i in range(proxy.rowCount()))

def test_limpar_filtro(qapp):
    proxy = _proxy_padrao()
    proxy.set_filtro_coluna(COL_MOTIVO, {"score_baixo"})
    proxy.set_filtro_coluna(COL_MOTIVO, None)
    assert COL_MOTIVO not in proxy.colunas_filtradas()
```

- [ ] Step 2: implementar predicados (dict col→set aceito; `filterAcceptsRow` = AND entre colunas + sheet da Task 2).
- [ ] Step 3: popup do header: clique no botão de filtro abre `QMenu`/widget com busca (`QLineEdit`), lista de `valores_unicos` com checkboxes (`QListWidget` checkable), "Selecionar tudo", OK/Limpar. Só wiring — zero lógica fora do proxy.
- [ ] Step 4: testes PASS; smoke manual com LISTA 1 (2.3k linhas — sem travar).
- [ ] Step 5: commit `feat(spJ): filtro estilo excel por coluna`

---

### Task 4: Indicador de coluna filtrada

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py` (header)
- Test: `tests/test_proxy_revisao.py` (fonte da verdade = `colunas_filtradas()`)

- [ ] Step 1: no header view, decorar colunas em `proxy.colunas_filtradas()` (ícone de funil via `QHeaderView` custom paint ou sufixo "▼*" no texto do header — escolher o menor diff).
- [ ] Step 2: atualizar ao aplicar/limpar filtro (sinal do proxy).
- [ ] Step 3: smoke manual: aplicar filtro → indicador aparece; limpar → some.
- [ ] Step 4: commit `feat(spJ): indicador de filtro ativo no header`

---

### Task 5: Validação final

- [ ] Step 1: `python -m pytest -q` verde
- [ ] Step 2: roteiro manual completo na LISTA 1: abas ok, filtros combinam, indicador ok, auditoria com colunas novas
- [ ] Step 3: commit final
