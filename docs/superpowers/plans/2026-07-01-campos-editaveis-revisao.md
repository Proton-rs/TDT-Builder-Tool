# Campos editáveis na tela de revisão — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar 7 campos da tabela de revisão (Tipo, Fase, Nível Tensão, Barra, Tipo Equip., Módulo, Escala) editáveis, com dropdown nos campos de domínio fechado.

**Architecture:** `AppState` ganha 7 setters finos (`_editar_nested` + `dataclasses.replace` no campo aninhado). `ModeloSinais.flags()`/`setData()` dispatcha edição pra esses setters. `DelegateCombo`/`DelegateModulo` novos em `delegate_sinal.py` fornecem o editor visual (combo). `TelaRevisao.carregar()` registra os delegates por coluna.

**Tech Stack:** Python, PySide6 (Qt widgets), pytest + pytest-qt (`qtbot`).

## Global Constraints

- Editar os 7 campos NÃO promove `status` pra `"decidido"` (só editar Sinal promove — comportamento existente de `definir_sigla`, não mexer nele).
- Nenhum dos novos setters cria snapshot de undo — mesma lacuna que `definir_sigla` já tem hoje; não é regressão, é consistência.
- Editar **Tipo Equip.** grava `equipamento_inferido=False` (deixou de ser inferido, foi definido pelo usuário).
- Editar **Tipo** grava `categoria_confiavel=True`.
- `SignalRecord` e seus campos aninhados (`Eletrico`, `TipoSinal`, `Modulo`, `GrandezasAnalogicas`) são `@dataclass(frozen=True)` — toda mutação é via `dataclasses.replace`, nunca atribuição direta.
- Domínio das colunas fechadas (copiado da spec `docs/superpowers/specs/2026-07-01-sp-campos-editaveis-revisao-design.md`):
  - Tipo: `Discrete/Input`, `Discrete/Output`, `Discrete/InputOutput`, `Analog/Input`, `Analog/Output`
  - Fase: `""`, `A`, `B`, `C`, `N`, `AB`, `BC`, `CA`, `ABC`
  - Nível Tensão: `""`, `AT`, `BT`
  - Barra: `""`, `Principal`, `Auxiliar`
  - Tipo Equip.: `""`, `Disjuntor`, `Seccionadora`

---

## Task 1: `AppState` — setters de campo de domínio

**Files:**
- Modify: `src/tdt/ui/estado.py:66-71` (depois de `definir_sigla`, fim do arquivo)
- Test: `tests/test_ui_estado.py`

**Interfaces:**
- Consumes: `tdt.contracts.SignalRecord`, `Eletrico`, `TipoSinal`, `Modulo`, `GrandezasAnalogicas` (já existem).
- Produces: `AppState.definir_tipo(indice, categoria, direcao)`, `AppState.definir_fase(indice, fase)`, `AppState.definir_nivel_tensao(indice, nivel)`, `AppState.definir_barra(indice, barra)`, `AppState.definir_tipo_equip(indice, equip)`, `AppState.definir_modulo(indice, nome)`, `AppState.definir_escala(indice, valor)` — usados pela Task 2 (`ModeloSinais.setData`).

- [ ] **Step 1: Escrever os testes que falham**

Abrir `tests/test_ui_estado.py`. Trocar a linha de import do topo:

```python
from dataclasses import replace

from tdt.contracts import (
    Candidato, Descricoes, Eletrico, Enderecamento, ItemRevisao, ListaHomogenea,
    Modulo, ResultadoPipeline, SignalRecord, TipoSinal,
)
from tdt.ui.estado import AppState
```

Acrescentar ao final do arquivo:

```python
def test_definir_fase_atualiza_eletrico():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_fase(0, "B")
    assert st.registros[0].eletrico.fase == "B"


def test_definir_nivel_tensao_atualiza_eletrico():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_nivel_tensao(0, "AT")
    assert st.registros[0].eletrico.nivel_tensao == "AT"


def test_definir_barra_atualiza_eletrico():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_barra(0, "Auxiliar")
    assert st.registros[0].eletrico.barra == "Auxiliar"


def test_definir_tipo_equip_atualiza_e_zera_inferido():
    st = AppState()
    rec = _rec("a:1", "DJF1", "decidido")
    rec = replace(rec, eletrico=Eletrico(equipamento_alvo="Disjuntor", equipamento_inferido=True))
    st.registros = [rec]
    st.definir_tipo_equip(0, "Seccionadora")
    assert st.registros[0].eletrico.equipamento_alvo == "Seccionadora"
    assert st.registros[0].eletrico.equipamento_inferido is False


def test_definir_modulo_atualiza_nome():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_modulo(0, "AL21")
    assert st.registros[0].modulo.nome == "AL21"


def test_definir_escala_atualiza_grandezas_analogicas():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_escala(0, 1.5)
    assert st.registros[0].grandezas_analogicas.escala_transmissao == 1.5


def test_definir_tipo_atualiza_categoria_direcao_e_marca_confiavel():
    st = AppState()
    rec = _rec("a:1", "DJF1", "decidido")
    rec = replace(rec, tipo_sinal=TipoSinal("DiscreteAnalog", False, "Input", categoria_confiavel=False))
    st.registros = [rec]
    st.definir_tipo(0, "Analog", "Output")
    assert st.registros[0].tipo_sinal.categoria == "Analog"
    assert st.registros[0].tipo_sinal.direcao == "Output"
    assert st.registros[0].tipo_sinal.categoria_confiavel is True


def test_editar_campo_nao_muda_status_nem_justificativa():
    st = AppState()
    st.registros = [_rec("a:1", None, "revisao")]
    st.definir_fase(0, "A")
    assert st.registros[0].status == "revisao"
    assert st.registros[0].justificativa is None
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_ui_estado.py -v -k "definir_fase or definir_nivel_tensao or definir_barra or definir_tipo_equip or definir_modulo or definir_escala or definir_tipo_atualiza or editar_campo_nao_muda"`
Expected: FAIL com `AttributeError: 'AppState' object has no attribute 'definir_fase'` (e equivalentes para os outros).

- [ ] **Step 3: Implementar os setters**

Em `src/tdt/ui/estado.py`, acrescentar depois do método `definir_sigla` (final da classe `AppState`):

```python
    def _editar_nested(self, indice: int, campo: str, **kwargs) -> None:
        """Substitui atributos de um campo aninhado (Eletrico/TipoSinal/
        Modulo/GrandezasAnalogicas) via replace, sem tocar status/justificativa.
        """
        r = self.registros[indice]
        novo = replace(getattr(r, campo), **kwargs)
        self.registros[indice] = replace(r, **{campo: novo})

    def definir_tipo(self, indice: int, categoria: str, direcao: str) -> None:
        self._editar_nested(indice, "tipo_sinal", categoria=categoria,
                             direcao=direcao, categoria_confiavel=True)

    def definir_fase(self, indice: int, fase: str | None) -> None:
        self._editar_nested(indice, "eletrico", fase=fase)

    def definir_nivel_tensao(self, indice: int, nivel: str | None) -> None:
        self._editar_nested(indice, "eletrico", nivel_tensao=nivel)

    def definir_barra(self, indice: int, barra: str | None) -> None:
        self._editar_nested(indice, "eletrico", barra=barra)

    def definir_tipo_equip(self, indice: int, equip: str | None) -> None:
        self._editar_nested(indice, "eletrico", equipamento_alvo=equip,
                             equipamento_inferido=False)

    def definir_modulo(self, indice: int, nome: str | None) -> None:
        self._editar_nested(indice, "modulo", nome=nome)

    def definir_escala(self, indice: int, valor: float | None) -> None:
        self._editar_nested(indice, "grandezas_analogicas", escala_transmissao=valor)
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_ui_estado.py -v`
Expected: todos PASS (os pré-existentes + os novos).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/estado.py tests/test_ui_estado.py
git commit -m "feat(ui): setters de campo de domínio no AppState (Fase/Módulo/Tipo/etc.)"
```

---

## Task 2: `ModeloSinais` — colunas editáveis + `setData`

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py:78-82` (`flags`), acrescentar `setData` depois de `data()` (linha 161)
- Test: `tests/test_ui_modelo_tabela.py`

**Interfaces:**
- Consumes: `AppState.definir_tipo/fase/nivel_tensao/barra/tipo_equip/modulo/escala` (Task 1).
- Produces: `ModeloSinais.flags(index)` retorna `Qt.ItemIsEditable` pras 8 colunas; `ModeloSinais.setData(index, value, role)` — usado pelos delegates da Task 3 e pelo editor padrão (Escala).

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_ui_modelo_tabela.py`, trocar o bloco de imports do topo por:

```python
from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Eletrico, Enderecamento, GrandezasAnalogicas,
    Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
```

Acrescentar ao final do arquivo:

```python
def test_flags_colunas_dominio_sao_editaveis():
    m = ModeloSinais(_state(_rec()))
    for nome in ("Sinal", "Tipo", "Fase", "Nível Tensão", "Barra",
                 "Tipo Equip.", "Módulo", "Escala"):
        flags = m.flags(m.index(0, _col(nome)))
        assert flags & Qt.ItemIsEditable, nome


def test_flags_colunas_derivadas_nao_sao_editaveis():
    m = ModeloSinais(_state(_rec()))
    for nome in ("Status", "Motivo", "Descr. ADMS", "Score tf-idf",
                 "Justificativa", "Equipamento"):
        flags = m.flags(m.index(0, _col(nome)))
        assert not (flags & Qt.ItemIsEditable), nome


def test_set_data_fase_atualiza_estado_e_emite_data_changed(qtbot):
    st = _state(_rec())
    m = ModeloSinais(st)
    idx = m.index(0, _col("Fase"))
    with qtbot.waitSignal(m.dataChanged, timeout=1000):
        ok = m.setData(idx, "B", Qt.EditRole)
    assert ok is True
    assert st.registros[0].eletrico.fase == "B"


def test_set_data_tipo_faz_split_categoria_direcao():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Tipo")), "Analog/Output", Qt.EditRole)
    assert ok is True
    assert st.registros[0].tipo_sinal.categoria == "Analog"
    assert st.registros[0].tipo_sinal.direcao == "Output"


def test_set_data_tipo_sem_barra_retorna_false():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Tipo")), "Discrete", Qt.EditRole)
    assert ok is False


def test_set_data_escala_converte_texto_com_virgula_para_float():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Escala")), "1,5", Qt.EditRole)
    assert ok is True
    assert st.registros[0].grandezas_analogicas.escala_transmissao == 1.5


def test_set_data_escala_vazio_limpa_valor():
    st = _state(_rec())
    st.registros[0] = replace(
        st.registros[0],
        grandezas_analogicas=GrandezasAnalogicas(escala_transmissao=3.0),
    )
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Escala")), "", Qt.EditRole)
    assert ok is True
    assert st.registros[0].grandezas_analogicas.escala_transmissao is None


def test_set_data_escala_invalida_retorna_false_sem_mutar():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Escala")), "abc", Qt.EditRole)
    assert ok is False
    assert st.registros[0].grandezas_analogicas.escala_transmissao is None


def test_set_data_coluna_nao_editavel_retorna_false():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Status")), "decidido", Qt.EditRole)
    assert ok is False
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_ui_modelo_tabela.py -v -k "flags_colunas or set_data"`
Expected: FAIL — `flags` ainda só libera "Sinal"; `setData` não existe em `ModeloSinais` (usa o `setData` default de `QAbstractTableModel`, que retorna `False`/não muta nada, então as asserções `ok is True` falham).

- [ ] **Step 3: Implementar `flags` e `setData`**

Em `src/tdt/ui/modelo_tabela.py`, acrescentar a constante logo antes de `class ModeloSinais` (depois de `COR_REVISAO`, linha 39):

```python
_EDITAVEIS = frozenset({
    "Sinal", "Tipo", "Fase", "Nível Tensão", "Barra", "Tipo Equip.",
    "Módulo", "Escala",
})
```

Trocar o método `flags` (linhas 78-82):

```python
    def flags(self, index):
        base = super().flags(index)
        if COLUNAS[index.column()] in _EDITAVEIS:
            return base | Qt.ItemIsEditable
        return base
```

Acrescentar `setData` logo depois do método `data` (depois da linha 161, antes de `definir_sigla`):

```python
    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        nome = COLUNAS[index.column()]
        linha = index.row()
        texto = str(value).strip()
        if nome == "Tipo":
            if "/" not in texto:
                return False
            categoria, direcao = texto.split("/", 1)
            self._estado.definir_tipo(linha, categoria, direcao)
        elif nome == "Fase":
            self._estado.definir_fase(linha, texto or None)
        elif nome == "Nível Tensão":
            self._estado.definir_nivel_tensao(linha, texto or None)
        elif nome == "Barra":
            self._estado.definir_barra(linha, texto or None)
        elif nome == "Tipo Equip.":
            self._estado.definir_tipo_equip(linha, texto or None)
        elif nome == "Módulo":
            self._estado.definir_modulo(linha, texto or None)
        elif nome == "Escala":
            try:
                valor = float(texto.replace(",", ".")) if texto else None
            except ValueError:
                return False
            self._estado.definir_escala(linha, valor)
        else:
            return False
        topo = self.index(linha, 0)
        fim = self.index(linha, len(COLUNAS) - 1)
        self.dataChanged.emit(topo, fim)
        return True
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_ui_modelo_tabela.py -v`
Expected: todos PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py tests/test_ui_modelo_tabela.py
git commit -m "feat(ui): ModeloSinais.setData dispatcha edição pros novos campos"
```

---

## Task 3: `DelegateCombo` + `DelegateModulo`

**Files:**
- Modify: `src/tdt/ui/delegate_sinal.py` (acrescentar 2 classes + import `Qt`)
- Test: `tests/test_ui_delegate_sinal.py` (novo)

**Interfaces:**
- Consumes: `ModeloSinais.setData` (Task 2), `AppState.registros` (Task 1/existente).
- Produces: `DelegateCombo(opcoes: list[str], parent=None)`, `DelegateModulo(estado: AppState, parent=None)` — usados pela Task 4 (`TelaRevisao.carregar`).

`DelegateCombo` e `setModelData`/`createEditor` de ambas as classes são
passthrough fino pro Qt (`addItems`, `.currentText().strip()` → `model.setData`)
— comportamento do framework, não lógica nossa (decisão já tomada na spec).
A única lógica de verdade nesta task é o cálculo da lista de módulos
sugeridos em `DelegateModulo.createEditor` (distinct + sort + filtra `None`)
— é o único ponto que ganha teste dedicado.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_ui_delegate_sinal.py`:

```python
import pytest

pytest.importorskip("PySide6")

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.delegate_sinal import DelegateModulo
from tdt.ui.estado import AppState


def _rec(id_, modulo_nome):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo_nome, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"),
    )


def test_delegate_modulo_sugere_nomes_distintos_ordenados_sem_none(qtbot):
    st = AppState()
    st.registros = [
        _rec("a:1", "AL22"), _rec("a:2", "AL21"), _rec("a:3", "AL21"),
        _rec("a:4", None),
    ]
    delegate = DelegateModulo(st)
    combo = delegate.createEditor(None, None, None)
    qtbot.addWidget(combo)
    assert combo.isEditable() is True
    assert [combo.itemText(i) for i in range(combo.count())] == ["AL21", "AL22"]
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_ui_delegate_sinal.py -v`
Expected: FAIL com `ImportError: cannot import name 'DelegateModulo' from 'tdt.ui.delegate_sinal'`.

- [ ] **Step 3: Implementar as 2 classes**

Em `src/tdt/ui/delegate_sinal.py`, trocar a linha de import do topo:

```python
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate
```

Acrescentar ao final do arquivo:

```python
class DelegateCombo(QStyledItemDelegate):
    """Editor combo p/ colunas de domínio fechado (Tipo/Fase/Nível Tensão/
    Barra/Tipo Equip.). Sempre não-editável — só os valores fixos passados.
    """

    def __init__(self, opcoes: list[str], parent=None):
        super().__init__(parent)
        self._opcoes = opcoes

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self._opcoes)
        return combo

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)


class DelegateModulo(QStyledItemDelegate):
    """Editor combo editável p/ Módulo: sugere nomes já presentes nos
    registros, aceita texto livre (módulo novo).
    """

    def __init__(self, estado: AppState, parent=None):
        super().__init__(parent)
        self._estado = estado

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        modulos = sorted({
            r.modulo.nome for r in self._estado.registros
            if r.modulo and r.modulo.nome
        })
        combo.addItems(modulos)
        return combo

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `pytest tests/test_ui_delegate_sinal.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/delegate_sinal.py tests/test_ui_delegate_sinal.py
git commit -m "feat(ui): DelegateCombo e DelegateModulo pros novos campos editáveis"
```

---

## Task 4: registrar os delegates em `TelaRevisao.carregar()`

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py:22` (import), `:28` (constante nova), `:165-181` (`carregar`)
- Test: `tests/test_ui_tela_revisao.py`

**Interfaces:**
- Consumes: `DelegateCombo`, `DelegateModulo` (Task 3).
- Produces: nada consumido por outra task — é o ponto final de integração.

- [ ] **Step 1: Escrever os testes que falham**

Em `tests/test_ui_tela_revisao.py`, trocar a linha de import do módulo `delegate_sinal`/`modelo_tabela` no topo (a linha 7 já importa `ModeloSinais`; acrescentar a importação de `DelegateCombo`/`DelegateModulo`):

```python
from tdt.ui.delegate_sinal import DelegateCombo, DelegateModulo
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
from tdt.ui.tela_revisao import TelaRevisao, decidir_acao_pareamento
```

Acrescentar ao final do arquivo:

```python
def test_carregar_registra_delegate_combo_nas_colunas_de_dominio(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    for nome in ("Tipo", "Fase", "Nível Tensão", "Barra", "Tipo Equip."):
        col = ModeloSinais.COLUNAS.index(nome)
        delegate = tela.tabela.itemDelegateForColumn(col)
        assert isinstance(delegate, DelegateCombo), nome


def test_carregar_registra_delegate_modulo_na_coluna_modulo(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    col = ModeloSinais.COLUNAS.index("Módulo")
    delegate = tela.tabela.itemDelegateForColumn(col)
    assert isinstance(delegate, DelegateModulo)
```

- [ ] **Step 2: Rodar os testes e confirmar que falham**

Run: `pytest tests/test_ui_tela_revisao.py -v -k "delegate"`
Expected: FAIL — `itemDelegateForColumn` retorna o delegate padrão (`QStyledItemDelegate` genérico da view), não `DelegateCombo`/`DelegateModulo`.

- [ ] **Step 3: Registrar os delegates**

Em `src/tdt/ui/tela_revisao.py`, trocar a linha de import (linha 22):

```python
from tdt.ui.delegate_sinal import DelegateCombo, DelegateModulo, DelegateSinal
```

Acrescentar a constante logo depois de `_METODOS` (linha 28):

```python
_OPCOES_COMBO = {
    "Tipo": ["Discrete/Input", "Discrete/Output", "Discrete/InputOutput",
             "Analog/Input", "Analog/Output"],
    "Fase": ["", "A", "B", "C", "N", "AB", "BC", "CA", "ABC"],
    "Nível Tensão": ["", "AT", "BT"],
    "Barra": ["", "Principal", "Auxiliar"],
    "Tipo Equip.": ["", "Disjuntor", "Seccionadora"],
}
```

No método `carregar`, depois do bloco que registra `DelegateSinal` (linhas 177-179), acrescentar:

```python
        col_sinal = ModeloSinais.COLUNAS.index("Sinal")
        self.tabela.setItemDelegateForColumn(
            col_sinal, DelegateSinal(self._estado, self._modelo, self._proxy, self.tabela))
        for nome, opcoes in _OPCOES_COMBO.items():
            col = ModeloSinais.COLUNAS.index(nome)
            self.tabela.setItemDelegateForColumn(col, DelegateCombo(opcoes, self.tabela))
        col_modulo = ModeloSinais.COLUNAS.index("Módulo")
        self.tabela.setItemDelegateForColumn(col_modulo, DelegateModulo(self._estado, self.tabela))
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_ui_tela_revisao.py -v`
Expected: todos PASS.

- [ ] **Step 5: Rodar a suíte completa**

Run: `pytest -q`
Expected: todos os testes (existentes + novos) PASS, nenhuma regressão.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/tela_revisao.py tests/test_ui_tela_revisao.py
git commit -m "feat(ui): registra DelegateCombo/DelegateModulo na tela de revisão"
```
