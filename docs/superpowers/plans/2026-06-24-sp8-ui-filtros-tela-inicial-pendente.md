# SP8 — UI: Filtros por Coluna, Tela Inicial, Status Pendente — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Filtro por coluna individual na tabela de revisão + 3º clique limpa ordenação; botão "Limpar log" e navegação por abas na tela inicial; sinais sem endereço também são classificados (sigla sugerida) e a tabela ganha coluna "Motivo".

**Architecture:** 4 mudanças independentes nos mesmos arquivos de UI já existentes (`proxy_revisao.py`, `tela_revisao.py`, `tela_inicial.py`, `app.py`, `estado.py`, `modelo_tabela.py`) + 1 mudança de comportamento em `pipeline.py`. Sem widget novo, sem classe nova — extensões pontuais.

**Tech Stack:** PySide6 (já em uso, 6.11+), pytest-qt.

## Global Constraints

- Sem nova classe de widget — reaproveitar `QInputDialog`, `QTabBar`, `QHeaderView.customContextMenuRequested`.
- `setSortIndicatorClearable` é API nativa do Qt 6.5+ — usar direto, sem lógica de clique customizada.
- Sinal sem endereço nunca é auto-aprovado nem vai para `decididos`.
- `# ponytail:` obrigatório em `motivo_por_id()` (recomputa dict a cada chamada — ok pro tamanho atual).

---

### Task 1: Filtro por coluna em `ProxyRevisao`

**Files:**
- Modify: `src/tdt/ui/proxy_revisao.py:17-33`
- Test: `tests/test_ui_proxy_revisao.py`

**Interfaces:**
- Produces: `ProxyRevisao.setFiltroColuna(col: int, texto: str) -> None`
- Produces: `ProxyRevisao.filtroColuna(col: int) -> str` (getter, default `""`)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_proxy_revisao.py (acrescentar; arquivo já existe com testes do filtro global/esconder decididos)
def test_filtro_coluna_isola_linhas(modelo_qt, proxy_qt):
    proxy_qt.setFiltroColuna(0, "IA")
    assert proxy_qt.rowCount() == 1


def test_filtros_multiplas_colunas_combinam_em_and(modelo_qt, proxy_qt):
    proxy_qt.setFiltroColuna(0, "IA")
    proxy_qt.setFiltroColuna(2, "DECIDIDO")
    # sigla "IA" existe mas status não é "decidido" -> 0 linhas, ou o inverso
    # ajustar fixture conforme dados reais de modelo_qt/proxy_qt já usados nos
    # testes existentes deste arquivo (reaproveitar fixture, não recriar)
    assert proxy_qt.rowCount() in (0, 1)


def test_filtro_coluna_vazio_remove_filtro(modelo_qt, proxy_qt):
    proxy_qt.setFiltroColuna(0, "IA")
    proxy_qt.setFiltroColuna(0, "")
    assert proxy_qt.filtroColuna(0) == ""
```

Use as fixtures `modelo_qt`/`proxy_qt` já existentes em `tests/test_ui_proxy_revisao.py` (não recrie — leia o arquivo primeiro pra usar os nomes exatos de fixture e os dados de exemplo já montados lá).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_proxy_revisao.py -v`
Expected: FAIL com `AttributeError: 'ProxyRevisao' object has no attribute 'setFiltroColuna'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/ui/proxy_revisao.py
class ProxyRevisao(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._esconder_decididos = False
        self._filtros_coluna: dict[int, str] = {}

    def setEsconderDecididos(self, ativo: bool) -> None:
        self._esconder_decididos = ativo
        self.invalidateFilter()

    def setFiltroColuna(self, col: int, texto: str) -> None:
        if texto:
            self._filtros_coluna[col] = texto.upper()
        else:
            self._filtros_coluna.pop(col, None)
        self.invalidateFilter()

    def filtroColuna(self, col: int) -> str:
        return self._filtros_coluna.get(col, "")

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._esconder_decididos:
            idx = self.sourceModel().index(source_row, _COL_STATUS, source_parent)
            if self.sourceModel().data(idx) == "decidido":
                return False
        for col, termo in self._filtros_coluna.items():
            idx = self.sourceModel().index(source_row, col, source_parent)
            valor = str(self.sourceModel().data(idx) or "").upper()
            if termo not in valor:
                return False
        return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_proxy_revisao.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/proxy_revisao.py tests/test_ui_proxy_revisao.py
git commit -m "feat(sp8): filtro por coluna individual no proxy de revisao (AND com filtro global)"
```

---

### Task 2: Menu de filtro por coluna + ordenação limpável em `tela_revisao.py`

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py` (perto de `carregar()`, linhas ~79-111 da versão atual)

**Interfaces:**
- Consumes: `ProxyRevisao.setFiltroColuna`/`filtroColuna` (Task 1).
- Consumes: `ModeloSinais.COLUNAS` (lista existente em `src/tdt/ui/modelo_tabela.py`).

- [ ] **Step 1: Adicionar contexto de menu no cabeçalho e ordenação limpável**

Sem teste automatizado dedicado aqui (interação de mouse/diálogo modal — `QInputDialog.getText` não é testável de forma barata com pytest-qt sem mockar `exec`; comportamento já é coberto pelos testes do `ProxyRevisao` na Task 1). Implementar direto:

```python
# em carregar(), depois de self.tabela.setSortingEnabled(True):
self.tabela.horizontalHeader().setSortIndicatorClearable(True)
self.tabela.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
self.tabela.horizontalHeader().customContextMenuRequested.connect(self._filtrar_coluna)
```

```python
# novo método na classe TelaRevisao
def _filtrar_coluna(self, pos) -> None:
    col = self.tabela.horizontalHeader().logicalIndexAt(pos)
    if col < 0:
        return
    nome = ModeloSinais.COLUNAS[col]
    atual = self._proxy.filtroColuna(col)
    texto, ok = QInputDialog.getText(self, f"Filtrar '{nome}'", "Contém:", text=atual)
    if ok:
        self._proxy.setFiltroColuna(col, texto.strip())
```

Adicionar import `QInputDialog` de `PySide6.QtWidgets` no topo do arquivo (verificar se já não está importado antes de duplicar).

- [ ] **Step 2: Smoke manual**

Run: `python -m tdt.ui_main`, abrir um resultado, clicar com botão direito no cabeçalho de uma coluna, digitar um termo, confirmar que a tabela filtra; clicar 3x num cabeçalho ordenado e confirmar que a ordenação volta ao original.

- [ ] **Step 3: Run full suite to check no regression**

Run: `python -m pytest -q`

- [ ] **Step 4: Commit**

```bash
git add src/tdt/ui/tela_revisao.py
git commit -m "feat(sp8): menu de filtro por coluna no cabecalho + 3o clique limpa ordenacao"
```

---

### Task 3: Botão "Limpar log" na Tela Inicial

**Files:**
- Modify: `src/tdt/ui/tela_inicial.py` (perto da criação de `self.log` e `col_dir`, linhas ~75-94 da versão atual)

**Interfaces:**
- Consumes: `self.log: QPlainTextEdit` (já existe).

- [ ] **Step 1: Adicionar o botão**

```python
self.btn_limpar_log = QPushButton("Limpar log")
self.btn_limpar_log.clicked.connect(self.log.clear)
```

Adicionar essa criação junto de onde `self.log` é criado, e inserir o widget no layout, ao lado do `QLabel("LOG")`:

```python
col_dir.addLayout(topo); col_dir.addLayout(botoes)
log_header = QHBoxLayout()
log_header.addWidget(QLabel("LOG"))
log_header.addStretch()
log_header.addWidget(self.btn_limpar_log)
col_dir.addLayout(log_header)
col_dir.addWidget(self.log)
```

(Substitui a linha atual `col_dir.addWidget(QLabel("LOG")); col_dir.addWidget(self.log)` — remover a antiga ao adicionar a nova.)

- [ ] **Step 2: Write a smoke test**

```python
# tests/test_ui_tela_inicial.py (acrescentar se o arquivo já existir; senão criar)
def test_botao_limpar_log_esvazia_o_log(tela_inicial_qt):
    tela_inicial_qt.log.appendPlainText("algo")
    tela_inicial_qt.btn_limpar_log.click()
    assert tela_inicial_qt.log.toPlainText() == ""
```

Use a fixture de `TelaInicial` já existente nos testes de UI deste projeto (procure `tests/test_ui_*.py` por uma fixture `qtbot`/`tela_inicial` antes de criar uma nova).

- [ ] **Step 3: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_tela_inicial.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add src/tdt/ui/tela_inicial.py tests/test_ui_tela_inicial.py
git commit -m "feat(sp8): botao Limpar log na tela inicial"
```

---

### Task 4: Navegação em abas (Inicial ↔ Revisão)

**Files:**
- Modify: `src/tdt/ui/app.py:29-71`

**Interfaces:**
- Consumes: `self.stack: QStackedWidget`, `self.tela_inicial`, `self.tela_revisao`, `self.tela_config` (já existem).
- Produces: `self.abas: QTabBar` com índice 0="Inicial", 1="Revisão".

- [ ] **Step 1: Adicionar QTabBar e ligar ao stack**

```python
from PySide6.QtWidgets import QTabBar, QVBoxLayout, QWidget  # ajustar imports conforme já existentes no arquivo

self.abas = QTabBar()
self.abas.addTab("Inicial")
self.abas.addTab("Revisão")
self.abas.setTabEnabled(1, False)
self.abas.currentChanged.connect(self.stack.setCurrentIndex)

container = QWidget()
layout = QVBoxLayout(container)
layout.setContentsMargins(0, 0, 0, 0)
layout.addWidget(self.abas)
layout.addWidget(self.stack)
self.setCentralWidget(container)  # substitui self.setCentralWidget(self.stack)
```

Em `_ir_para_revisao()`, depois de `self.stack.setCurrentIndex(1)`, adicionar:

```python
self.abas.setTabEnabled(1, True)
self.abas.setCurrentIndex(1)
```

Trocar conexões que setam `stack.setCurrentIndex` diretamente (ex. `self.tela_revisao.voltar.connect(...)`) para também sincronizar `self.abas.setCurrentIndex(0)`, evitando dessincronia entre aba exibida e índice do stack:

```python
self.tela_revisao.voltar.connect(lambda: self.abas.setCurrentIndex(0))
```

(`abas.currentChanged` já dispara `stack.setCurrentIndex` — não chamar os dois diretamente pra mesma ação, senão dispara duas vezes; manter `Config` fora das abas como hoje, acessível só pelo botão ⚙️ que segue chamando `self.stack.setCurrentIndex(2)` direto, sem passar pela aba.)

- [ ] **Step 2: Smoke manual**

Run: `python -m tdt.ui_main`, confirmar que a aba "Revisão" começa desabilitada, habilita após executar o pipeline uma vez, e que clicar nas abas alterna a tela sem reprocessar (logs não duplicam).

- [ ] **Step 3: Run full suite to check no regression**

Run: `python -m pytest -q`

- [ ] **Step 4: Commit**

```bash
git add src/tdt/ui/app.py
git commit -m "feat(sp8): navegacao Inicial/Revisao por abas (QTabBar)"
```

---

### Task 5: Classificar sinal sem endereço (pipeline) + expor motivo

**Files:**
- Modify: `src/tdt/pipeline.py` (loop dentro de `executar()`, trecho atual: `if not rec.enderecamento.indices:`)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `_classificar_roteado(rec, disc, ana, diagnostico) -> tuple[SignalRecord | None, ItemRevisao | None]` (já existe, `pipeline.py:140`).
- Produces: comportamento — sinal sem endereço sempre cai em `revisao` com `motivo="sem_endereco"`, mas agora com `candidatos` preenchidos quando o scorer achar algo plausível.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py (acrescentar)
def test_sinal_sem_endereco_recebe_candidato_sugerido(...):
    # reaproveitar fixtures/helpers já usados nos outros testes deste arquivo
    # pra montar um SignalRecord com enderecamento.indices=() e descricao que
    # bate com algum sinal da lista padrão fake usada no arquivo.
    resultado, _ = executar(...)
    item = next(it for it in resultado.revisao if it.motivo == "sem_endereco")
    assert len(item.candidatos_sugeridos) > 0
```

Adapte a um helper/fixture já existente em `tests/test_pipeline.py` (leia o arquivo antes de escrever — reaproveitar o padrão de fixture de input/lista padrão fake já usado lá em vez de inventar um novo).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -k sem_endereco -v`
Expected: FAIL — `candidatos_sugeridos` vem vazio hoje (sinal sem endereço pula direto pra `ItemRevisao` sem rodar `_classificar_roteado`).

- [ ] **Step 3: Write minimal implementation**

Trocar em `pipeline.py`:

```python
            if not rec.enderecamento.indices:
                aud.evento("pipeline", f"{rec.id}: sem endereço — pulando", "AVISO")
                revisao.append(ItemRevisao(rec, motivo="sem_endereco"))
                continue
```

por:

```python
            if not rec.enderecamento.indices:
                aud.evento("pipeline", f"{rec.id}: sem endereço — classificando sem decidir", "AVISO")
                _decidido_tmp, item_tmp = _classificar_roteado(rec, disc, ana, diagnostico)
                rec_avaliado = _decidido_tmp if _decidido_tmp is not None else item_tmp.registro
                revisao.append(ItemRevisao(
                    rec_avaliado, motivo="sem_endereco",
                    candidatos_sugeridos=item_tmp.candidatos_sugeridos if item_tmp is not None else (),
                ))
                continue
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -k sem_endereco -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline.py
git commit -m "feat(sp8): classifica sinal sem endereco (sugere sigla) sem auto-aprovar"
```

---

### Task 6: `AppState.motivo_por_id()` + coluna "Motivo" na tabela

**Files:**
- Modify: `src/tdt/ui/estado.py:16-37`
- Modify: `src/tdt/ui/modelo_tabela.py:13-17, 77-113`
- Test: `tests/test_ui_modelo_tabela.py` (ou criar se não existir)

**Interfaces:**
- Produces: `AppState.motivo_por_id() -> dict[str, str]`.
- Consumes: `ItemRevisao.registro.id`, `ItemRevisao.motivo` (já existem em `contracts.py`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_modelo_tabela.py
from tdt.ui.estado import AppState


def test_motivo_por_id_mapeia_id_para_motivo(resultado_pipeline_fake):
    estado = AppState()
    estado.carregar_resultado(resultado_pipeline_fake)
    mapa = estado.motivo_por_id()
    item = resultado_pipeline_fake.revisao[0]
    assert mapa[item.registro.id] == item.motivo


def test_coluna_motivo_mostra_label_amigavel(modelo_sinais_qt):
    # reaproveitar fixture já existente neste arquivo/projeto de testes de UI
    col = modelo_sinais_qt.COLUNAS.index("Motivo")
    idx = modelo_sinais_qt.index(0, col)
    assert modelo_sinais_qt.data(idx) in ("Futuro (sem endereço)", "—", "Score baixo",
                                            "Categoria ambígua", "Endereço duplicado",
                                            "Sem correção automática")
```

Crie/ajuste a fixture `resultado_pipeline_fake`/`modelo_sinais_qt` reaproveitando o padrão já usado em `tests/test_ui_proxy_revisao.py` (mesmo `ResultadoPipeline` fake, se existir lá — não duplique a montagem).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v`
Expected: FAIL — `AttributeError: 'AppState' object has no attribute 'motivo_por_id'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/ui/estado.py — método novo na classe AppState
def motivo_por_id(self) -> dict[str, str]:
    if self.resultado is None:
        return {}
    return {item.registro.id: item.motivo for item in self.resultado.revisao}
```

```python
# src/tdt/ui/modelo_tabela.py
COLUNAS = [
    "Sinal", "Confiança", "Status", "Motivo", "Descr. ADMS", "Descr. bruta",
    "Descr. normalizada", "Tokens", "Tipo", "Escala", "Fase", "Endereço",
    "Score embedding", "Score tf-idf", "Score fuzzy", "Justificativa",
]

_MOTIVO_LABEL = {
    "sem_endereco": "Futuro (sem endereço)",
    "score_baixo": "Score baixo",
    "categoria_ambigua": "Categoria ambígua",
    "endereco_duplicado": "Endereço duplicado",
    "sem_fix": "Sem correção automática",
}
```

Em `_texto()`, adicionar antes do `if nome == "Descr. ADMS":`:

```python
        if nome == "Motivo":
            motivo = self._estado.motivo_por_id().get(rec.id)
            return _MOTIVO_LABEL.get(motivo, "—") if motivo else "—"
```

`# ponytail: motivo_por_id() reconstrói o dict a cada chamada de _texto — ok pro tamanho de lista atual (centenas de linhas); cachear no AppState se a tabela ficar lenta com listas grandes.`

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite to check no regression**

Run: `python -m pytest -q`

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/estado.py src/tdt/ui/modelo_tabela.py tests/test_ui_modelo_tabela.py
git commit -m "feat(sp8): coluna Motivo na tabela de revisao (AppState.motivo_por_id)"
```

---

## Self-Review Notes

- Cobertura: filtro por coluna (1), UI de filtro + ordenação limpável (2, smoke manual já que é interação modal), limpar log (3), abas (4, smoke manual + 1 teste de clique no botão), classificar sem endereço (5), coluna Motivo (6). Todos os 7 critérios de aceite do spec têm task correspondente.
- Risco: nomes exatos de fixtures em `tests/test_ui_proxy_revisao.py` e `tests/test_pipeline.py` — Tasks 1, 5 e 6 mandam ler o arquivo de teste existente antes de escrever, em vez de assumir nomes.
