# SP-UX-PERF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cinco ajustes de UX/perf na UI: marcação de sheets em grupo, filtro por coluna fluido, geração de TDT seletiva por módulo, colunas Equipamento (ID) e Descr. bruta editáveis, e ações em massa sem travar (remover 500 sinais < 1s).

**Spec:** `docs/superpowers/specs/2026-07-15-sp-ux-perf-ferramenta-design.md`

**Architecture:** Só `src/tdt/ui/` + `tests/`. Cada dor num arquivo dono: tela_inicial (sheets), tela_revisao+proxy_revisao (filtro), tela_geracao (seleção de módulos), modelo_tabela+delegate_sinal+estado (editáveis), modelo_tabela+tela_revisao (perf em massa). Lógica nova extraída em funções puras/módulo-level onde der, para teste sem instanciar telas.

**Tech Stack:** PySide6, pytest + pytest-qt (fixture `qtbot`, já usada pelos testes `tests/test_ui_*.py`).

## Global Constraints

- Nada fora de `src/tdt/ui/` e `tests/` muda (spec, seção Não-escopo).
- Campos derivados seguem não-editáveis: Confiança, Status, Motivo, Descr. ADMS, Descr. normalizada, Tokens, Scores, Justificativa, Pareado, Sheet origem.
- Undo: 1 snapshot por operação destrutiva (padrão atual de `AppState._snapshot`). Redo fora de escopo.
- Rename de sheets: continua um a um, inline (rename em lote descartado pelo usuário 15/07).
- Critérios: remover 500 sinais < 1s; dialog de filtro fecha imediatamente ao OK; ~5k linhas filtram sem congelar perceptível.
- Simplificação deliberada = comentário `# ponytail:` com teto e upgrade path.
- Suite: `python -m pytest -q tests/` (raiz do repo).

---

### Task 1: Marcação de sheets em grupo (tela inicial)

**Files:**
- Modify: `src/tdt/ui/tela_inicial.py` (`lista_sheets` setup ~linha 136; handlers novos)
- Test: `tests/test_ui_tela_inicial.py`

**Interfaces:**
- Produces: funções módulo-level em `tela_inicial.py`: `definir_marcacao(lista: QListWidget, marcado: bool) -> None` e `inverter_marcacao(lista: QListWidget) -> None` (agem nas linhas selecionadas; sem seleção, em todas). Testáveis com QListWidget puro.

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_ui_tela_inicial.py`:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem

from tdt.ui.tela_inicial import definir_marcacao, inverter_marcacao


def _lista_com_itens(qtbot, n=4):
    lista = QListWidget()
    qtbot.addWidget(lista)
    for i in range(n):
        it = QListWidgetItem(f"Sheet{i}")
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked)
        lista.addItem(it)
    return lista


def test_definir_marcacao_age_nas_selecionadas(qtbot):
    lista = _lista_com_itens(qtbot)
    lista.item(1).setSelected(True)
    lista.item(2).setSelected(True)
    definir_marcacao(lista, False)
    estados = [lista.item(i).checkState() for i in range(4)]
    assert estados == [Qt.Checked, Qt.Unchecked, Qt.Unchecked, Qt.Checked]


def test_definir_marcacao_sem_selecao_age_em_todas(qtbot):
    lista = _lista_com_itens(qtbot)
    definir_marcacao(lista, False)
    assert all(lista.item(i).checkState() == Qt.Unchecked for i in range(4))


def test_inverter_marcacao(qtbot):
    lista = _lista_com_itens(qtbot)
    lista.item(0).setCheckState(Qt.Unchecked)
    inverter_marcacao(lista)  # sem seleção -> todas
    estados = [lista.item(i).checkState() for i in range(4)]
    assert estados == [Qt.Checked, Qt.Unchecked, Qt.Unchecked, Qt.Unchecked]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_ui_tela_inicial.py -k marcacao -v`
Expected: FAIL com `ImportError: definir_marcacao`.

- [ ] **Step 3: Implementar**

(a) Funções módulo-level em `tela_inicial.py` (antes da classe da tela):

```python
def _itens_alvo(lista: QListWidget) -> list[QListWidgetItem]:
    """Linhas selecionadas; sem seleção, todas (spec 2026-07-15 §1)."""
    sel = lista.selectedItems()
    if sel:
        return sel
    return [lista.item(i) for i in range(lista.count())]


def definir_marcacao(lista: QListWidget, marcado: bool) -> None:
    estado = Qt.Checked if marcado else Qt.Unchecked
    for it in _itens_alvo(lista):
        it.setCheckState(estado)


def inverter_marcacao(lista: QListWidget) -> None:
    for it in _itens_alvo(lista):
        it.setCheckState(
            Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)
```

(b) No setup da `lista_sheets` (após a linha 137 `itemChanged.connect`):

```python
        self.lista_sheets.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lista_sheets.setContextMenuPolicy(Qt.CustomContextMenu)
        self.lista_sheets.customContextMenuRequested.connect(self._menu_sheets)
        self.lista_sheets.itemPressed.connect(self._sheet_pressionada)
        self.lista_sheets.itemClicked.connect(self._sheet_clicada)
        self.lista_sheets.itemDoubleClicked.connect(self._sheet_duplo_clique)
        self._check_no_press = Qt.Unchecked
        atalho_espaco = QShortcut(QKeySequence(Qt.Key_Space), self.lista_sheets)
        atalho_espaco.setContext(Qt.WidgetShortcut)
        atalho_espaco.activated.connect(
            lambda: inverter_marcacao(self.lista_sheets))
```

Imports novos: `QAbstractItemView`, `QMenu` (PySide6.QtWidgets), `QShortcut`, `QKeySequence` (PySide6.QtGui), `QApplication` se ainda não importado.

(c) Handlers novos na classe:

```python
    # --- marcação em grupo / hitbox (spec 2026-07-15 §1) ---
    def _menu_sheets(self, pos) -> None:
        if self.lista_sheets.count() == 0:
            return
        menu = QMenu(self.lista_sheets)
        menu.addAction("Marcar selecionadas",
                       lambda: definir_marcacao(self.lista_sheets, True))
        menu.addAction("Desmarcar selecionadas",
                       lambda: definir_marcacao(self.lista_sheets, False))
        menu.addAction("Inverter marcação",
                       lambda: inverter_marcacao(self.lista_sheets))
        menu.exec(self.lista_sheets.viewport().mapToGlobal(pos))

    def _sheet_pressionada(self, it: QListWidgetItem) -> None:
        self._check_no_press = it.checkState()

    def _sheet_clicada(self, it: QListWidgetItem) -> None:
        """Hitbox maior: clique em qualquer ponto da linha alterna o
        checkbox. Se o clique caiu no próprio indicador, o Qt já alternou
        entre o press e o click (estado difere do gravado no press) — não
        alterna de novo. Shift/Ctrl só selecionam."""
        if QApplication.keyboardModifiers() & (Qt.ShiftModifier | Qt.ControlModifier):
            return
        if it.checkState() != self._check_no_press:
            return
        it.setCheckState(
            Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)

    def _sheet_duplo_clique(self, it: QListWidgetItem) -> None:
        # o 1º clique do duplo-clique alternou via _sheet_clicada; reverte
        # para o rename (edição inline) não mudar a marcação
        it.setCheckState(
            Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)
```

`_sheet_alterada` (linha 285) continua sendo o único escritor de `sheets_excluidas`/aliases — as ações em grupo disparam `itemChanged` por item e reusam esse caminho.

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest -q tests/test_ui_tela_inicial.py tests/test_tela_inicial.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tela_inicial.py tests/test_ui_tela_inicial.py
git commit -m "feat(ui): marcacao de sheets em grupo + hitbox de linha inteira"
```

---

### Task 2: Filtro por coluna fluido (tela_revisao + proxy_revisao)

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py` (accessor novo `valor_texto`)
- Modify: `src/tdt/ui/proxy_revisao.py:99-134` (`valores_unicos`, `filterAcceptsRow`)
- Modify: `src/tdt/ui/tela_revisao.py:434-453` (`_filtrar_coluna`)
- Test: `tests/test_ui_proxy_revisao.py`

**Interfaces:**
- Produces: `ModeloSinais.valor_texto(row: int, col: int) -> str` — valor de exibição da célula sem QModelIndex (caminho quente do filtro).
- `_filtrar_coluna` aplica o filtro via `QTimer.singleShot(0, ...)` após o dialog fechar.

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_ui_proxy_revisao.py` (seguir os imports/builders existentes do arquivo; se não houver builder de registro, usar este):

```python
def _rec_filtro(rid, modulo):
    return SignalRecord(
        id=rid, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("X", "X"), status="decidido",
    )


def test_valor_texto_espelha_display(qtbot):
    st = AppState()
    st.registros = [_rec_filtro("S:1", "AL11"), _rec_filtro("S:2", "AL12")]
    m = ModeloSinais(st)
    col = ModeloSinais.COLUNAS.index("Módulo")
    for row in range(2):
        assert m.valor_texto(row, col) == str(m.data(m.index(row, col)) or "")


def test_filtro_valores_continua_funcionando(qtbot):
    st = AppState()
    st.registros = [_rec_filtro("S:1", "AL11"), _rec_filtro("S:2", "AL12")]
    m = ModeloSinais(st)
    proxy = ProxyRevisao()
    proxy.setSourceModel(m)
    col = ModeloSinais.COLUNAS.index("Módulo")
    proxy.set_filtro_coluna(col, {"AL11"})
    assert proxy.rowCount() == 1
    proxy.set_filtro_coluna(col, None)
    assert proxy.rowCount() == 2
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_ui_proxy_revisao.py -k "valor_texto or continua" -v`
Expected: FAIL com `AttributeError: valor_texto` (o 2º teste deve passar antes e depois — é o guarda de regressão).

- [ ] **Step 3: Implementar**

(a) `modelo_tabela.py` — antes de implementar, conferir o branch `Qt.DisplayRole` de `data()` (região ~linhas 200-285): ele deve delegar a `self._texto(rec, col)`. `valor_texto` precisa espelhar EXATAMENTE esse branch (o teste do Step 1 trava isso). Adicionar na classe `ModeloSinais`:

```python
    def valor_texto(self, row: int, col: int) -> str:
        """Valor de exibição da célula sem construir QModelIndex — caminho
        quente do filtro por coluna (spec 2026-07-15 §2). Deve espelhar o
        branch DisplayRole de data()."""
        rec = self._estado.registros[row]
        v = self._texto(rec, col)
        return "" if v is None else str(v)
```

(Se `data()` DisplayRole tiver formatação além de `_texto` para alguma coluna, replicar aqui — o teste `test_valor_texto_espelha_display` pega divergência.)

(b) `proxy_revisao.py` — usar o accessor nos dois lugares e reordenar o filtro (barato primeiro, `super()` por último — ele varre todas as colunas quando há busca global):

```python
    def valores_unicos(self, col: int) -> list[str]:
        modelo = self.sourceModel()
        if modelo is None:
            return []
        return sorted({
            modelo.valor_texto(row, col) for row in range(modelo.rowCount())
        })

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        modelo = self.sourceModel()
        if self._sheet is not None:
            rec = modelo._estado.registros[source_row]
            if sheet_origem(rec) != self._sheet:
                return False
        if self._status_visivel is not None:
            if modelo.valor_texto(source_row, _COL_STATUS) != self._status_visivel:
                return False
        for col, valores in self._filtros_coluna_valores.items():
            if modelo.valor_texto(source_row, col) not in valores:
                return False
        for col, termo in self._filtros_coluna.items():
            if termo not in modelo.valor_texto(source_row, col).upper():
                return False
        # busca global de texto (setFilterKeyColumn(-1), varre todas as
        # colunas) por último -- é o passo mais caro
        return super().filterAcceptsRow(source_row, source_parent)
```

(c) `tela_revisao.py` — `_filtrar_coluna` fecha o dialog e aplica no tick seguinte com cursor busy. Substituir da linha 446 (`novos = ...`) até a 453 por:

```python
        novos = dialog.valores_selecionados()
        texto_contem = dialog.texto_contem()
        if novos is None:
            self._selecao_filtro_coluna.pop(col, None)
        else:
            self._selecao_filtro_coluna[col] = novos

        def aplicar() -> None:
            # roda no tick seguinte: o dialog já sumiu da tela antes do
            # invalidateFilter pesado (spec 2026-07-15 §2)
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                self._proxy.set_filtro_coluna(col, novos)
                self._proxy.setFiltroColuna(col, texto_contem)
                self._atualizar_chip_filtros()
            finally:
                QApplication.restoreOverrideCursor()

        QTimer.singleShot(0, aplicar)
```

Imports novos em `tela_revisao.py`: `QTimer` (PySide6.QtCore), `QApplication` (PySide6.QtWidgets) — conferir os já existentes.

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest -q tests/test_ui_proxy_revisao.py tests/test_ui_tela_revisao.py tests/test_ui_modelo_tabela.py`
Expected: PASS (filtros por status/sheet/valores/texto preservam comportamento).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py src/tdt/ui/proxy_revisao.py src/tdt/ui/tela_revisao.py tests/test_ui_proxy_revisao.py
git commit -m "perf(ui): filtro por coluna aplica pos-fechamento + caminho quente sem QModelIndex"
```

---

### Task 3: Geração seletiva por módulo (tela_geracao)

**Files:**
- Modify: `src/tdt/ui/tela_geracao.py` (`carregar:102-121`, `_gerar:174-222`, widget novo)
- Test: `tests/test_ui_tela_geracao.py`

**Interfaces:**
- Produces: `filtrar_por_modulos(registros, marcados: set) -> list` (módulo-level, pura); lista `self.lista_modulos` (QListWidget checkable); `self._modulos_marcados() -> set`.
- Sentinela: registros com `modulo.nome` None entram como `"(sem módulo)"` na lista; o set `marcados` carrega os nomes reais (None incluído via UserRole).

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_ui_tela_geracao.py` (reusar builder de registro existente do arquivo se houver; senão este):

```python
def _rec_mod(rid, modulo):
    return SignalRecord(
        id=rid, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("X", "X"), status="decidido",
    )


def test_filtrar_por_modulos():
    regs = [_rec_mod("a:1", "AL11"), _rec_mod("a:2", "AL12"), _rec_mod("a:3", None)]
    assert [r.id for r in filtrar_por_modulos(regs, {"AL11"})] == ["a:1"]
    assert [r.id for r in filtrar_por_modulos(regs, {"AL11", "AL12", None})] == [
        "a:1", "a:2", "a:3"]
    assert filtrar_por_modulos(regs, set()) == []


def test_filtrar_por_modulos_none_e_o_sem_modulo():
    regs = [_rec_mod("a:1", None)]
    assert [r.id for r in filtrar_por_modulos(regs, {None})] == ["a:1"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_ui_tela_geracao.py -k filtrar -v`
Expected: FAIL com `ImportError: filtrar_por_modulos`.

- [ ] **Step 3: Implementar**

(a) Função pura módulo-level em `tela_geracao.py`:

```python
def filtrar_por_modulos(registros, marcados: set) -> list:
    """Subconjunto de registros cujos módulos estão marcados p/ geração
    (spec 2026-07-15 §3). `None` no set = registros sem módulo."""
    return [r for r in registros
            if (r.modulo.nome if r.modulo else None) in marcados]
```

(b) Widget: no `__init__`, entre `grupo_resumo` e `grupo_avisos`, criar grupo "Módulos" com `self.lista_modulos = QListWidget()` + `self.lista_modulos.itemChanged.connect(self._modulos_alterados)`. Em `carregar()`, popular (todos marcados por default):

```python
        self.lista_modulos.blockSignals(True)
        self.lista_modulos.clear()
        modulos = sorted(
            {(r.modulo.nome if r.modulo else None) for r in regs},
            key=lambda m: (m is None, m or ""))
        for mod in modulos:
            it = QListWidgetItem(mod if mod is not None else "(sem módulo)")
            it.setData(Qt.UserRole, mod)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            self.lista_modulos.addItem(it)
        self.lista_modulos.blockSignals(False)
```

(c) Coletor + reação:

```python
    def _modulos_marcados(self) -> set:
        return {
            self.lista_modulos.item(i).data(Qt.UserRole)
            for i in range(self.lista_modulos.count())
            if self.lista_modulos.item(i).checkState() == Qt.Checked
        }

    def _modulos_alterados(self, _it) -> None:
        self._atualizar_contadores()
```

(d) Extrair de `carregar()` o cálculo dos cards para `_atualizar_contadores()`, calculando sobre `regs = filtrar_por_modulos(self._estado.registros, self._modulos_marcados())` (contadores refletem a seleção, spec §3) e desabilitando o botão sem seleção:

```python
    def _atualizar_contadores(self) -> None:
        regs = filtrar_por_modulos(
            self._estado.registros, self._modulos_marcados())
        total = len(regs)
        pendentes = sum(1 for r in regs if r.status == "revisao")
        decididos = sum(1 for r in regs if r.status == "decidido")
        taxa = f"{decididos / total * 100:.0f}%" if total else "—"
        self._cards["total"].setText(str(total))
        self._cards["decididos"].setText(str(decididos))
        self._cards["pendentes"].setText(str(pendentes))
        self._cards["taxa"].setText(taxa)
        pend_lbl = self._cards["pendentes"]
        pend_lbl.setProperty("nivel", "aviso" if pendentes else "ok")
        pend_lbl.style().unpolish(pend_lbl)
        pend_lbl.style().polish(pend_lbl)
        self._montar_avisos(pendentes, regs)
        self.btn_gerar.setEnabled(bool(self._modulos_marcados()))
```

`carregar()` passa a: popular `lista_modulos` (item b), setar título/saída, e chamar `self._atualizar_contadores()`. `_montar_avisos` muda de assinatura para `_montar_avisos(self, pendentes: int, regs) -> None` e calcula `dups = enderecos_duplicados(regs)` sobre o subconjunto recebido (não mais `self._estado.registros`).

(e) `_gerar()`: no início, `regs = filtrar_por_modulos(self._estado.registros, self._modulos_marcados())`; usar `regs` no lugar de `self._estado.registros` em: contagem de `pendentes`, `pipeline.gerar_tdt(regs, ...)`, `por_id = {r.id: r for r in regs}` e `gerar_relatorio_revisao(regs, ...)` — TDT, relatório e avisos cobrem o MESMO subconjunto.

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest -q tests/test_ui_tela_geracao.py tests/test_ui_smoke.py`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tela_geracao.py tests/test_ui_tela_geracao.py
git commit -m "feat(ui): geracao de TDT seletiva por modulo"
```

---

### Task 4: Colunas Equipamento (ID) e Descr. bruta editáveis

**Files:**
- Modify: `src/tdt/ui/estado.py` (2 métodos novos, junto dos `definir_*` ~linha 119)
- Modify: `src/tdt/ui/modelo_tabela.py:86-89` (`_EDITAVEIS`) e `:287-329` (`setData`)
- Modify: `src/tdt/ui/delegate_sinal.py` (delegate novo)
- Modify: `src/tdt/ui/tela_revisao.py` (wiring do delegate, junto do `DelegateModulo`)
- Test: `tests/test_ui_modelo_tabela.py`, `tests/test_ui_estado.py`

**Interfaces:**
- Consumes: `AppState._editar_nested` (padrão existente — cuida do snapshot como os demais `definir_*`).
- Produces: `AppState.definir_equipamento(indice, nome: str | None)`; `AppState.definir_descricao_bruta(indice, texto: str)`; `DelegateEquipamento(estado, proxy, parent)`.

- [ ] **Step 1: Escrever os testes falhando**

Em `tests/test_ui_estado.py` (seguir builders existentes do arquivo):

```python
def test_definir_equipamento_e_undo(qtbot):
    st = _estado_com_um_registro()  # usar o builder existente do arquivo
    st.definir_equipamento(0, "52-11")
    assert st.registros[0].eletrico.nome_equipamento == "52-11"
    st.definir_equipamento(0, None)  # vazio limpa
    assert st.registros[0].eletrico.nome_equipamento is None
    assert st.desfazer()
    assert st.registros[0].eletrico.nome_equipamento == "52-11"


def test_definir_descricao_bruta(qtbot):
    st = _estado_com_um_registro()
    st.definir_descricao_bruta(0, "DISJUNTOR 52-11 MOLA")
    assert st.registros[0].descricoes.bruta == "DISJUNTOR 52-11 MOLA"
    # normalizada NÃO reprocessa (spec §4)
    assert st.registros[0].descricoes.normalizada == _NORMALIZADA_ORIGINAL
```

(Adaptar `_estado_com_um_registro`/`_NORMALIZADA_ORIGINAL` ao builder real do arquivo — o registro base já tem `descricoes` preenchidas.)

Em `tests/test_ui_modelo_tabela.py`:

```python
def test_equipamento_e_descr_bruta_editaveis(qtbot):
    assert "Equipamento" in _EDITAVEIS
    assert "Descr. bruta" in _EDITAVEIS


def test_setdata_equipamento(qtbot):
    st = _state(_rec())
    m = ModeloSinais(st)
    assert m.setData(m.index(0, _col("Equipamento")), "52-11", Qt.EditRole)
    assert st.registros[0].eletrico.nome_equipamento == "52-11"
    assert m.setData(m.index(0, _col("Equipamento")), "", Qt.EditRole)
    assert st.registros[0].eletrico.nome_equipamento is None


def test_setdata_descr_bruta_rejeita_vazio(qtbot):
    st = _state(_rec())
    m = ModeloSinais(st)
    assert not m.setData(m.index(0, _col("Descr. bruta")), "  ", Qt.EditRole)
    assert m.setData(m.index(0, _col("Descr. bruta")), "NOVA DESC", Qt.EditRole)
    assert st.registros[0].descricoes.bruta == "NOVA DESC"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_ui_estado.py tests/test_ui_modelo_tabela.py -k "equipamento or descr_bruta or descricao_bruta" -v`
Expected: FAIL (`AttributeError: definir_equipamento`; asserts de `_EDITAVEIS`).

- [ ] **Step 3: Implementar**

(a) `estado.py`, junto dos demais `definir_*` (após `definir_tipo_equip`, linha ~121):

```python
    def definir_equipamento(self, indice: int, nome: str | None) -> None:
        """ID do equipamento (ex. corrigir "81-1" -> "52-11"); None limpa."""
        self._editar_nested(indice, "eletrico", nome_equipamento=nome)

    def definir_descricao_bruta(self, indice: int, texto: str) -> None:
        """Só o texto bruto (afeta fallback de Signal Alias no export);
        normalizada/tokens NÃO reprocessam (spec 2026-07-15 §4)."""
        self._editar_nested(indice, "descricoes", bruta=texto)
```

(b) `modelo_tabela.py` — `_EDITAVEIS` (linha 86):

```python
_EDITAVEIS = frozenset({
    "Sinal", "Tipo", "Fase", "Nível Tensão", "Barra", "Tipo Equip.",
    "Módulo", "Escala", "Endereço", "Endereço Output",
    "Equipamento", "Descr. bruta",
})
```

Em `setData`, antes do `else: return False` (linha 323):

```python
        elif nome == "Equipamento":
            self._estado.definir_equipamento(linha, texto or None)
        elif nome == "Descr. bruta":
            if not texto:
                return False  # descrição bruta é dado de origem, não pode esvaziar
            self._estado.definir_descricao_bruta(linha, texto)
```

(c) `delegate_sinal.py` — delegate novo (após `DelegateModulo`):

```python
class DelegateEquipamento(QStyledItemDelegate):
    """Editor combo editável p/ Equipamento (ID): sugere os IDs já presentes
    em registros do MESMO módulo, aceita texto livre; opção vazia limpa
    (spec 2026-07-15 §4). Caso alvo: corrigir 81-1 -> 52-11 na revisão."""

    def __init__(self, estado: AppState, proxy, parent=None):
        super().__init__(parent)
        self._estado = estado
        self._proxy = proxy

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        fonte = self._proxy.mapToSource(index)
        modulo = None
        if fonte.isValid():
            rec = self._estado.registros[fonte.row()]
            modulo = rec.modulo.nome if rec.modulo else None
        ids = sorted({
            r.eletrico.nome_equipamento for r in self._estado.registros
            if r.eletrico.nome_equipamento
            and (r.modulo.nome if r.modulo else None) == modulo
        })
        combo.addItems([""] + ids)
        return combo

    def setEditorData(self, editor, index):
        _preselecionar(editor, index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)
```

(d) `tela_revisao.py`: localizar onde `DelegateModulo` é instalado (grep `setItemDelegateForColumn`) e, no mesmo bloco, instalar:

```python
        self.tabela.setItemDelegateForColumn(
            ModeloSinais.COLUNAS.index("Equipamento"),
            DelegateEquipamento(estado, self._proxy, self.tabela))
```

(import junto dos demais delegates). "Descr. bruta" fica com o editor de texto default do Qt (QLineEdit) — sem delegate.

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest -q tests/test_ui_estado.py tests/test_ui_modelo_tabela.py tests/test_ui_delegate_sinal.py tests/test_estado_lote.py`
Expected: PASS — inclusive o lote (`aplicar_valor_em_lote` já aceita qualquer coluna de `_EDITAVEIS`, então edição em massa de Equipamento vem de graça).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/estado.py src/tdt/ui/modelo_tabela.py src/tdt/ui/delegate_sinal.py src/tdt/ui/tela_revisao.py tests/test_ui_estado.py tests/test_ui_modelo_tabela.py
git commit -m "feat(ui): colunas Equipamento (ID) e Descr. bruta editaveis na revisao"
```

---

### Task 5: Performance de ações em massa (remover + lote)

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py:402-413` (`remover_linhas`), `:331-356` (`aplicar_valor_em_lote`), `setData:325-328` (emissão)
- Modify: `src/tdt/ui/tela_revisao.py:602-605` (`_aplicar_em_lote`)
- Test: `tests/test_ui_modelo_tabela.py`

**Interfaces:**
- Produces: `_ranges_contiguos(indices: list[int]) -> list[tuple[int, int]]` (módulo-level, pura); `LIMIAR_RESET_REMOCAO = 100` (módulo-level); `ModeloSinais._suprimir_datachanged` (flag interna).
- Semântica de `remover_linhas` inalterada para o chamador (mesmos índices removidos; snapshot continua responsabilidade de quem chama).

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_ui_modelo_tabela.py`:

```python
from tdt.ui.modelo_tabela import _ranges_contiguos, LIMIAR_RESET_REMOCAO


def _state_n(n):
    st = AppState()
    st.registros = [replace(_rec(), id=f"S:{i}") for i in range(n)]
    return st


def test_ranges_contiguos():
    assert _ranges_contiguos([1, 2, 3, 7, 9, 10]) == [(1, 3), (7, 7), (9, 10)]
    assert _ranges_contiguos([5]) == [(5, 5)]
    assert _ranges_contiguos([3, 1, 2, 3]) == [(1, 3)]  # dedup + ordena
    assert _ranges_contiguos([]) == []


def test_remover_linhas_lote_pequeno(qtbot):
    st = _state_n(10)
    m = ModeloSinais(st)
    m.remover_linhas([1, 2, 5, 9])
    assert [r.id for r in st.registros] == [
        "S:0", "S:3", "S:4", "S:6", "S:7", "S:8"]


def test_remover_linhas_lote_grande_via_reset(qtbot):
    n = LIMIAR_RESET_REMOCAO + 50
    st = _state_n(n + 10)
    m = ModeloSinais(st)
    m.remover_linhas(list(range(n)))  # > limiar -> caminho de reset
    assert [r.id for r in st.registros] == [f"S:{i}" for i in range(n, n + 10)]


def test_remover_linhas_ignora_indices_invalidos(qtbot):
    st = _state_n(3)
    m = ModeloSinais(st)
    m.remover_linhas([-1, 1, 99])
    assert [r.id for r in st.registros] == ["S:0", "S:2"]


def test_lote_emite_um_datachanged_agregado(qtbot):
    st = _state_n(5)
    st.lista_padrao = None
    m = ModeloSinais(st)
    emitidos = []
    m.dataChanged.connect(lambda *a: emitidos.append(a))
    ids = [r.id for r in st.registros]
    m.aplicar_valor_em_lote(ids, "Fase", "A")
    assert all(r.eletrico.fase == "A" for r in st.registros)
    assert len(emitidos) == 1  # agregado, não 1 por linha
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_ui_modelo_tabela.py -k "ranges or remover or agregado" -v`
Expected: FAIL com `ImportError: _ranges_contiguos` (e 5 dataChanged no teste de lote).

- [ ] **Step 3: Implementar**

(a) `modelo_tabela.py`, módulo-level (junto de `sheet_origem`):

```python
LIMIAR_RESET_REMOCAO = 100  # acima disso, reset único em vez de removeRows


def _ranges_contiguos(indices: list[int]) -> list[tuple[int, int]]:
    """[1,2,3,7,9,10] -> [(1,3),(7,7),(9,10)]. Dedupa e ordena a entrada."""
    ranges: list[tuple[int, int]] = []
    for i in sorted(set(indices)):
        if ranges and i == ranges[-1][1] + 1:
            ranges[-1] = (ranges[-1][0], i)
        else:
            ranges.append((i, i))
    return ranges
```

(b) `remover_linhas` (substituir o corpo, spec §5):

```python
    def remover_linhas(self, indices: list[int]) -> None:
        """Remove as linhas (índices da fonte, 0-based) da lista subjacente.

        Lote grande (> LIMIAR_RESET_REMOCAO): um reset único — O(n) — em vez
        de N cascatas begin/endRemoveRows (o gargalo do "remover 500 trava",
        spec 2026-07-15 §5). Lote pequeno: begin/endRemoveRows por RANGE
        contíguo, preservando seleção/scroll da view.
        """
        validos = [
            i for i in sorted(set(indices))
            if 0 <= i < len(self._estado.registros)
        ]
        if not validos:
            return
        if len(validos) > LIMIAR_RESET_REMOCAO:
            alvo = set(validos)
            self.beginResetModel()
            self._estado.registros = [
                r for i, r in enumerate(self._estado.registros) if i not in alvo
            ]
            self.endResetModel()
            return
        for inicio, fim in reversed(_ranges_contiguos(validos)):
            self.beginRemoveRows(QModelIndex(), inicio, fim)
            del self._estado.registros[inicio:fim + 1]
            self.endRemoveRows()
```

(c) Emissão agregada no lote — em `__init__` da `ModeloSinais`: `self._suprimir_datachanged = False`. Em `setData`, trocar a emissão final (linhas 326-328) por:

```python
        self.ultima_edicao = (nome, value)
        if not self._suprimir_datachanged:
            topo = self.index(linha, 0)
            fim = self.index(linha, len(COLUNAS) - 1)
            self.dataChanged.emit(topo, fim)
        return True
```

Em `aplicar_valor_em_lote`, envolver o loop e emitir uma vez:

```python
        self._estado._snapshot()
        snapshot_original = self._estado._snapshot
        self._estado._snapshot = lambda: None
        self._suprimir_datachanged = True
        aplicados = 0
        try:
            for linha in linhas:
                if self.setData(self.index(linha, col), valor, Qt.EditRole):
                    aplicados += 1
        finally:
            self._suprimir_datachanged = False
            self._estado._snapshot = snapshot_original
        if aplicados:
            self.dataChanged.emit(
                self.index(min(linhas), 0),
                self.index(max(linhas), len(COLUNAS) - 1))
        return aplicados
```

(d) `tela_revisao.py` — `_aplicar_em_lote` suspende repaint durante o lote:

```python
    def _aplicar_em_lote(self, coluna: str, valor, linhas: list[int]) -> None:
        ids = [self._estado.registros[i].id for i in linhas]
        self.tabela.setUpdatesEnabled(False)
        try:
            self._modelo.aplicar_valor_em_lote(ids, coluna, valor)
        finally:
            self.tabela.setUpdatesEnabled(True)
        self.refresh()
```

- [ ] **Step 4: Rodar a suite de UI**

Run: `python -m pytest -q tests/test_ui_modelo_tabela.py tests/test_estado_lote.py tests/test_ui_tela_revisao.py tests/test_ui_smoke.py`
Expected: PASS. `_parear_sinais` (tela_revisao.py:623) também chama `remover_linhas` com poucos índices — segue no caminho de ranges, sem mudança de comportamento.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py src/tdt/ui/tela_revisao.py tests/test_ui_modelo_tabela.py
git commit -m "perf(ui): remocao em massa por reset/ranges + dataChanged agregado no lote"
```

---

### Task 6: Verificação manual + closeout DOX

**Files:**
- Modify: `docs/AGENTS.md` (ledger), `src/tdt/ui/AGENTS.md` (papéis), `docs/superpowers/specs/2026-07-15-sp-ux-perf-ferramenta-design.md` (status)

- [ ] **Step 1: Suite completa**

Run: `python -m pytest -q tests/`
Expected: tudo PASS.

- [ ] **Step 2: Verificação manual (critérios da spec)**

Run: `PYTHONPATH=src python -m tdt.ui_main`, com uma lista real grande (ex. a da SE CVA/LVA, fora do repo):
1. Tela inicial: shift-click seleciona várias sheets; botão direito → Marcar/Desmarcar/Inverter; Espaço alterna; clique na linha alterna; duplo-clique renomeia SEM mudar a marcação.
2. Revisão: botão direito no header → filtro → OK: dialog fecha na hora; filtro aplica com cursor busy; sem travamento perceptível.
3. Revisão: selecionar ~500 linhas → Remover: < 1s, sem congelar; desfazer restaura.
4. Revisão: editar Equipamento (combo sugere IDs do módulo) e Descr. bruta; aplicar em lote numa seleção grande sem repaint por célula.
5. Geração: desmarcar módulos → contadores mudam; nenhum marcado → botão desabilitado; gerar com 1 módulo → TDT/relatório só com ele.

Anotar os resultados (tempos aproximados) para o closeout. Qualquer critério reprovado → voltar à task correspondente antes do closeout.

- [ ] **Step 3: DOX pass**

- `docs/AGENTS.md`: linha da spec na lista + ledger: marcação em grupo de sheets; filtro pós-fechamento + `valor_texto`; geração seletiva por módulo (TDT+relatório no mesmo subconjunto); editáveis Equipamento/Descr. bruta; remoção reset>100/ranges; rename em lote descartado (usuário 15/07).
- `src/tdt/ui/AGENTS.md`: atualizar descrições (delegate novo, funções de marcação, `filtrar_por_modulos`, `LIMIAR_RESET_REMOCAO`).
- Spec: marcar **implementado** + resultados da verificação manual.

- [ ] **Step 4: Commit final**

```bash
git add docs/AGENTS.md src/tdt/ui/AGENTS.md docs/superpowers/specs/2026-07-15-sp-ux-perf-ferramenta-design.md
git commit -m "docs: closeout SP-UX-PERF (ledger + DOX + verificacao manual)"
```
