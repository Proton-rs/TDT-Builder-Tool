# SP-UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesenhar a UX da UI desktop (PySide6): sidebar retrátil com etapas, tema grafite, Entrada guiada, Revisão com fluxo de teclado e filtro unificado, tela Geração nova, Análise clicável e Config humana.

**Architecture:** Mantém a arquitetura Qt existente (AppState compartilhado + QStackedWidget + models/proxies). Troca a navegação QTabBar por `Sidebar` (widget novo), adiciona `TelaGeracao` (índice 4 do stack) e fecha a lacuna de undo criando snapshots dentro dos setters do `AppState`.

**Tech Stack:** Python 3.12, PySide6, pytest + pytest-qt. Persistência de UI via `QSettings("tdt", "ui")`. Zero dependências novas.

**Spec:** `docs/superpowers/specs/2026-07-06-sp-ui-redesign-design.md` (fonte de verdade para tokens de cor e comportamento).

## Global Constraints

- Somente `src/tdt/ui/`, `src/tdt/defaults.py` NÃO, pipeline NÃO, `contracts.py` NÃO.
- Estilo visual só em `tema.qss` (nunca inline), exceto a cor dinâmica do chunk das barras de score (padrão já existente).
- Nenhuma dependência nova; ícones são glifos unicode (`✓ 🔒 ☰ ⚙ ▤ ✎ ▼`).
- Tokens de cor (usar exatamente): fundo `#14161d` · painel `#1e2430` · painel-2 `#232a38` · borda `#2b3242` · borda forte `#3a4356` · texto `#e8ebf2` · secundário `#9aa3b5` · apagado `#5f6880` · acento `#4f8cff` (hover `#6ba0ff`, pressed `#3d74d9`, texto sobre acento `#0b1526`) · seleção `#243456` · ok `#35c48f` (tint `#173226`) · aviso `#e0a83f` (tint `#2a2118`, texto `#2c2005`) · erro `#e0604c` (tint `#3a1d18`).
- Testes: `python -m pytest tests/<arquivo>.py -v` (pythonpath já configurado no pyproject). Suíte completa da UI: `python -m pytest tests -k "test_ui" -q`.
- Commits pequenos, mensagens `feat(ui): ...` / `refactor(ui): ...` / `test(ui): ...`.
- Textos de UI em pt-BR, sentence case ("Executar análise", não "EXECUTAR").
- Helpers de teste: copiar `_rec`/`_tela_carregada` de `tests/test_ui_tela_revisao.py:15-40` quando o arquivo de teste novo precisar deles (assinaturas exatas usadas abaixo).

---

## Fase 0 — SP-UI-0: Fundação de tema

### Task 1: Cores semânticas novas + fonte monospace por coluna

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py`
- Test: `tests/test_ui_modelo_tabela.py` (adicionar no fim)

**Interfaces:**
- Produces: `cor_faixa(score)` passa a devolver `#35c48f`/`#e0a83f`/`#e0604c`; `ModeloSinais.data(..., Qt.FontRole)` devolve `QFont("Consolas")` nas colunas de dados.

- [ ] **Step 1: Write the failing tests**

Adicionar ao fim de `tests/test_ui_modelo_tabela.py`:

```python
from PySide6.QtCore import Qt

from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais, cor_faixa


def test_cor_faixa_novas_cores():
    assert cor_faixa(0.9).name() == "#35c48f"
    assert cor_faixa(0.5).name() == "#e0a83f"
    assert cor_faixa(0.1).name() == "#e0604c"


def test_font_role_monospace_so_em_colunas_de_dados(qtbot):
    st = AppState()
    st.registros = [_rec("s:1", "M1", "DESCR")]
    modelo = ModeloSinais(st)
    col_sinal = ModeloSinais.COLUNAS.index("Sinal")
    fonte = modelo.data(modelo.index(0, col_sinal), Qt.FontRole)
    assert fonte is not None and "Consolas" in fonte.family()
    col_status = ModeloSinais.COLUNAS.index("Status")
    assert modelo.data(modelo.index(0, col_status), Qt.FontRole) is None
```

Nota: `_rec` já existe nesse arquivo de teste; se o nome do helper local divergir, usar o helper existente do próprio arquivo (mesma assinatura de `tests/test_ui_tela_revisao.py:25`). Ajustar imports duplicados se o arquivo já importa esses símbolos.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v -k "cor_faixa_novas or font_role"`
Expected: FAIL (`#1d9e75 != #35c48f`; FontRole devolve None)

- [ ] **Step 3: Implement**

Em `src/tdt/ui/modelo_tabela.py`:

1. Trocar o import de QtGui: `from PySide6.QtGui import QColor, QFont`
2. Substituir o bloco de constantes de cor (linhas ~36-40) por:

```python
COR_ALTO = QColor("#35c48f")
COR_MEDIO = QColor("#e0a83f")
COR_BAIXO = QColor("#e0604c")
COR_DECIDIDO = COR_ALTO
COR_REVISAO = COR_BAIXO
```

3. Após `_EDITAVEIS`, adicionar:

```python
_COLUNAS_MONO = frozenset({
    "Sinal", "Endereço", "Endereço Output", "Tokens",
    "Score embedding", "Score tf-idf", "Score fuzzy",
})
```

4. Em `data()`, antes do `return None` final, adicionar:

```python
        if role == Qt.FontRole and nome in _COLUNAS_MONO:
            return QFont("Consolas")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v`
Expected: PASS (todos, incluindo os pré-existentes)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py tests/test_ui_modelo_tabela.py
git commit -m "feat(ui): cores semanticas do tema grafite + monospace por coluna (SP-UI-0)"
```

### Task 2: Reescrever tema.qss (tema grafite)

**Files:**
- Modify: `src/tdt/ui/tema.qss` (substituição integral)

**Interfaces:**
- Produces: propriedades QSS consumidas pelas tasks seguintes — `QPushButton[acao="principal"]`, `QPushButton[item="normal|ativo|bloqueado"]`, `#sidebar`, `#sidebarContexto`, `QFrame[estado="ok|faltando"]`, `QLabel[nivel="ok|aviso|erro"]`, `QLabel[tipo="tecnico"]`.

- [ ] **Step 1: Substituir o conteúdo integral de `src/tdt/ui/tema.qss` por:**

```css
/* SP-UI-0 — tema grafite.
   fundo #14161d · painel #1e2430 · painel-2 #232a38 · borda #2b3242 · borda forte #3a4356
   texto #e8ebf2 · secundário #9aa3b5 · apagado #5f6880
   acento #4f8cff (hover #6ba0ff · pressed #3d74d9 · sobre acento #0b1526) · seleção #243456
   ok #35c48f (#173226) · aviso #e0a83f (#2a2118 / texto #2c2005) · erro #e0604c (#3a1d18) */

QMainWindow, QWidget {
    background-color: #14161d;
    color: #e8ebf2;
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}

QGroupBox {
    background-color: #1e2430;
    border: 1px solid #2b3242;
    border-radius: 10px;
    margin-top: 14px;
    padding: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; color: #9aa3b5; }

#painelDetalhe {
    background-color: #1e2430;
    border: 1px solid #2b3242;
    border-radius: 10px;
    padding: 8px;
}

QLabel { color: #e8ebf2; background: transparent; }
QLabel[nivel="ok"] { color: #35c48f; }
QLabel[nivel="aviso"] { color: #e0a83f; }
QLabel[nivel="erro"] { color: #e0604c; }
QLabel[tipo="tecnico"] { color: #5f6880; font-size: 11px; }

QPushButton {
    background-color: #232a38;
    border: 1px solid #2b3242;
    border-radius: 8px;
    padding: 7px 13px;
    color: #e8ebf2;
}
QPushButton:hover { background-color: #2b3446; }
QPushButton:pressed { background-color: #1a1f29; }
QPushButton:disabled { background-color: #1e2430; color: #5f6880; }
QPushButton:focus { border: 1px solid #4f8cff; }
QPushButton:checked { background-color: #243456; border: 1px solid #4f8cff; }

QPushButton[acao="principal"] {
    background-color: #4f8cff;
    color: #0b1526;
    border: none;
    font-weight: bold;
    padding: 9px 16px;
}
QPushButton[acao="principal"]:hover { background-color: #6ba0ff; }
QPushButton[acao="principal"]:pressed { background-color: #3d74d9; }
QPushButton[acao="principal"]:disabled { background-color: #31394a; color: #8b93a6; }

#sidebar { background-color: #191d26; border-right: 1px solid #2b3242; }
#sidebarContexto { color: #5f6880; font-family: Consolas, monospace; font-size: 11px; }
QPushButton[item="normal"], QPushButton[item="ativo"], QPushButton[item="bloqueado"] {
    background: transparent;
    border: none;
    border-radius: 8px;
    text-align: left;
    padding: 8px 10px;
}
QPushButton[item="normal"] { color: #9aa3b5; }
QPushButton[item="normal"]:hover { background-color: #232a38; }
QPushButton[item="ativo"] { background-color: #243456; color: #e8ebf2; font-weight: bold; }
QPushButton[item="bloqueado"] { color: #5f6880; }

QFrame[estado="ok"] { background-color: #1e2430; border: 1px solid #2b3242; border-radius: 8px; }
QFrame[estado="faltando"] { background-color: #2a2118; border: 1px solid #e0a83f; border-radius: 8px; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #1a1f29;
    color: #e8ebf2;
    border: 1px solid #2b3242;
    border-radius: 7px;
    padding: 6px 8px;
    selection-background-color: #243456;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 1px solid #4f8cff; }
QComboBox QAbstractItemView { background-color: #1e2430; color: #e8ebf2; selection-background-color: #243456; }

QPlainTextEdit, QTextEdit {
    background-color: #1e2430;
    color: #c6ccd9;
    border: 1px solid #2b3242;
    border-radius: 7px;
    font-family: Consolas, monospace;
    font-size: 12px;
    selection-background-color: #243456;
}

QTableView {
    background-color: #1a1f29;
    alternate-background-color: #1e2430;
    color: #c6ccd9;
    gridline-color: #232a38;
    border: 1px solid #2b3242;
    border-radius: 10px;
    selection-background-color: #243456;
    selection-color: #e8ebf2;
}
QTableView::item { padding: 5px 8px; }

QHeaderView::section {
    background-color: #191d26;
    color: #9aa3b5;
    padding: 8px 10px;
    border: none;
    border-bottom: 2px solid #2b3242;
    font-weight: bold;
}

QTabBar::tab { background: transparent; color: #9aa3b5; padding: 7px 12px; border: none; }
QTabBar::tab:selected { color: #e8ebf2; border-bottom: 2px solid #4f8cff; }

QListWidget {
    background-color: #1a1f29;
    color: #c6ccd9;
    border: 1px solid #2b3242;
    border-radius: 7px;
    padding: 2px;
}
QListWidget::item { padding: 5px 8px; border-radius: 5px; }
QListWidget::item:selected { background-color: #243456; color: #e8ebf2; }

QProgressBar {
    background-color: #232a38;
    border: none;
    border-radius: 6px;
    text-align: center;
    color: #e8ebf2;
}
QProgressBar::chunk { background-color: #4f8cff; border-radius: 6px; }

QScrollBar:vertical { background: #191d26; width: 10px; margin: 0; }
QScrollBar::handle:vertical { background: #3a4356; border-radius: 5px; min-height: 24px; }
QScrollBar:horizontal { background: #191d26; height: 10px; margin: 0; }
QScrollBar::handle:horizontal { background: #3a4356; border-radius: 5px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

QCheckBox, QRadioButton { color: #e8ebf2; spacing: 7px; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px; height: 15px;
    border: 2px solid #3a4356;
    background: #1a1f29;
}
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: #4f8cff;
    border: 2px solid #3d74d9;
}

QSplitter::handle { background-color: #2b3242; width: 3px; }

QMenu { background-color: #1e2430; color: #e8ebf2; border: 1px solid #2b3242; }
QMenu::item:selected { background-color: #243456; }

QToolTip { background-color: #232a38; color: #e8ebf2; border: 1px solid #3a4356; }

QSpinBox::up-button, QDoubleSpinBox::up-button { width: 18px; subcontrol-position: top right; }
QSpinBox::down-button, QDoubleSpinBox::down-button { width: 18px; subcontrol-position: bottom right; }
```

- [ ] **Step 2: Run smoke + suíte UI**

Run: `python -m pytest tests -k "test_ui" -q`
Expected: PASS (tema não afeta lógica; se algum teste referenciar cor antiga `#7d7796`/`#1d9e75`, atualizar o teste para o token novo correspondente)

- [ ] **Step 3: Verificação visual manual (opcional mas recomendada)**

Run: `python -m tdt.ui_main` — janela abre grafite, foco de teclado desenha borda azul nos inputs. Fechar.

- [ ] **Step 4: Commit**

```bash
git add src/tdt/ui/tema.qss
git commit -m "feat(ui): tema grafite completo em tema.qss (SP-UI-0)"
```

---

## Fase 1 — SP-UI-1: Undo na raiz + Sidebar + Shell

### Task 3: Snapshot de undo dentro dos setters do AppState

Fecha a lacuna documentada em `src/tdt/ui/AGENTS.md` (Local Contracts): editar
Sinal/campos de domínio não criava snapshot — Ctrl+Z não teria o que desfazer.

**Files:**
- Modify: `src/tdt/ui/estado.py`
- Test: `tests/test_ui_estado.py` (adicionar no fim)

**Interfaces:**
- Produces: `AppState.definir_sigla(indice, sigla, *, snapshot=True)` — o
  parâmetro novo permite lote sem snapshot por item (usado na Task 5).
  `_editar_nested` sempre faz snapshot. Assinaturas dos 7 setters de domínio
  inalteradas.

- [ ] **Step 1: Write the failing tests**

Adicionar ao fim de `tests/test_ui_estado.py` (o helper `_rec(id_, sigla, status)` já existe no topo do arquivo):

```python
def test_undo_definir_sigla_restaura_sigla_e_status():
    st = AppState()
    st.registros = [_rec("a:1", None, "revisao")]
    st.definir_sigla(0, "DJF1")
    assert st.desfazer() is True
    assert st.registros[0].sigla_sinal is None
    assert st.registros[0].status == "revisao"


def test_undo_editar_nested_restaura_campo():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_fase(0, "A")
    assert st.registros[0].eletrico.fase == "A"
    assert st.desfazer() is True
    assert st.registros[0].eletrico.fase is None


def test_definir_sigla_sem_snapshot_nao_cria_historico():
    st = AppState()
    st.registros = [_rec("a:1", None, "revisao")]
    st.definir_sigla(0, "DJF1", snapshot=False)
    assert len(st._historico) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_estado.py -v -k "undo or sem_snapshot"`
Expected: FAIL — `desfazer()` retorna `False` (histórico vazio) nos dois primeiros; o terceiro falha com `TypeError` (parâmetro `snapshot` não existe)

- [ ] **Step 3: Implement**

Em `src/tdt/ui/estado.py`:

1. Substituir a assinatura e o corpo de `definir_sigla`:

```python
    def definir_sigla(self, indice: int, sigla: str, *, snapshot: bool = True) -> None:
        if snapshot:
            self._snapshot()
        r = self.registros[indice]
        self.registros[indice] = replace(
            r, sigla_sinal=sigla, status="decidido",
            justificativa="editado manualmente",
        )
```

2. Em `_editar_nested`, adicionar `self._snapshot()` como primeira linha do corpo (antes de `r = self.registros[indice]`).

- [ ] **Step 4: Run the full estado + revisão tests**

Run: `python -m pytest tests/test_ui_estado.py tests/test_ui_tela_revisao.py -v`
Expected: PASS. Os testes existentes que contam `_historico` cobrem remover/adicionar/parear (snapshot explícito externo, inalterado) — não contam snapshots de `definir_sigla`, então continuam verdes. Se algum contar, somar +1 à expectativa com comentário.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/estado.py tests/test_ui_estado.py
git commit -m "fix(ui): snapshot de undo dentro de definir_sigla/_editar_nested (SP-UI-1)"
```

### Task 4: Widget Sidebar retrátil

**Files:**
- Create: `src/tdt/ui/sidebar.py`
- Test: `tests/test_ui_sidebar.py` (novo)

**Interfaces:**
- Produces (consumido pela Task 5):
  - `Sidebar(itens_fluxo, itens_fixos, settings=None)` — itens são
    `list[tuple[chave: str, rotulo: str, glifo: str]]`.
  - sinal `navegar = Signal(str)` (chave).
  - `definir_estado(chave, estado)` com `estado ∈ {"disponivel", "bloqueada", "completa"}`.
  - `definir_ativa(chave)`, `atualizar_badge(chave, n: int)`, `definir_contexto(texto: str)`.
  - constantes `LARGURA_COLAPSADA = 48`, `LARGURA_EXPANDIDA = 200`.

- [ ] **Step 1: Write the failing tests**

Criar `tests/test_ui_sidebar.py`:

```python
import pytest
from PySide6.QtCore import QSettings

from tdt.ui.sidebar import LARGURA_COLAPSADA, LARGURA_EXPANDIDA, Sidebar

pytest.importorskip("PySide6")

_FLUXO = [("entrada", "1 · Entrada", "①"), ("revisao", "2 · Revisão", "②")]
_FIXOS = [("config", "Configurações", "⚙")]


def _settings(tmp_path):
    return QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat)


def _sidebar(qtbot, tmp_path):
    sb = Sidebar(_FLUXO, _FIXOS, settings=_settings(tmp_path))
    qtbot.addWidget(sb)
    return sb


def test_item_bloqueado_nao_navega(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    sb.definir_estado("revisao", "bloqueada")
    chamadas = []
    sb.navegar.connect(chamadas.append)
    sb._botoes["revisao"].click()
    assert chamadas == []


def test_item_disponivel_emite_chave(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    chamadas = []
    sb.navegar.connect(chamadas.append)
    sb._botoes["entrada"].click()
    assert chamadas == ["entrada"]


def test_comeca_colapsada_e_toggle_expande_persistindo(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    assert sb.width() == LARGURA_COLAPSADA or sb.minimumWidth() == LARGURA_COLAPSADA
    sb._btn_toggle.click()
    assert sb.minimumWidth() == LARGURA_EXPANDIDA
    sb2 = Sidebar(_FLUXO, _FIXOS, settings=_settings(tmp_path))
    qtbot.addWidget(sb2)
    assert sb2.minimumWidth() == LARGURA_EXPANDIDA


def test_badge_aparece_no_texto_e_some_com_zero(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    sb._btn_toggle.click()  # expande p/ ver rótulo completo
    sb.atualizar_badge("revisao", 37)
    assert "37" in sb._botoes["revisao"].text()
    sb.atualizar_badge("revisao", 0)
    assert "37" not in sb._botoes["revisao"].text()


def test_estado_completa_troca_glifo(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    sb.definir_estado("entrada", "completa")
    assert "✓" in sb._botoes["entrada"].text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_sidebar.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'tdt.ui.sidebar'`

- [ ] **Step 3: Implement**

Criar `src/tdt/ui/sidebar.py`:

```python
"""Sidebar retrátil: etapas do fluxo (topo) + itens fixos (rodapé).

ponytail: QPushButtons flat num QVBoxLayout, sem model. Expansão persiste em
QSettings("tdt", "ui") — injetável nos testes via parâmetro `settings`.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

LARGURA_COLAPSADA = 48
LARGURA_EXPANDIDA = 200

_GLIFO_COMPLETA = "✓"
_GLIFO_BLOQUEADA = "🔒"


class Sidebar(QWidget):
    navegar = Signal(str)

    def __init__(self, itens_fluxo, itens_fixos, settings: QSettings | None = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._settings = settings if settings is not None else QSettings("tdt", "ui")
        self._expandida = self._settings.value("sidebar_expandida", False, type=bool)
        self._botoes: dict[str, QPushButton] = {}
        self._glifos: dict[str, str] = {}
        self._rotulos: dict[str, str] = {}
        self._estados: dict[str, str] = {}
        self._badges: dict[str, int] = {}
        self._ativa: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(2)

        self._btn_toggle = QPushButton("☰")
        self._btn_toggle.setProperty("item", "normal")
        self._btn_toggle.setToolTip("Expandir/recolher menu")
        self._btn_toggle.clicked.connect(self._alternar)
        layout.addWidget(self._btn_toggle)

        for chave, rotulo, glifo in itens_fluxo:
            layout.addWidget(self._criar_botao(chave, rotulo, glifo))
        layout.addStretch()
        for chave, rotulo, glifo in itens_fixos:
            layout.addWidget(self._criar_botao(chave, rotulo, glifo))

        self._contexto = QLabel("")
        self._contexto.setObjectName("sidebarContexto")
        self._contexto.setWordWrap(True)
        layout.addWidget(self._contexto)

        self._aplicar_largura()

    def _criar_botao(self, chave: str, rotulo: str, glifo: str) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("item", "normal")
        btn.clicked.connect(lambda _=False, c=chave: self._clicado(c))
        self._botoes[chave] = btn
        self._glifos[chave] = glifo
        self._rotulos[chave] = rotulo
        self._estados[chave] = "disponivel"
        self._badges[chave] = 0
        self._atualizar_botao(chave)
        return btn

    def _clicado(self, chave: str) -> None:
        if self._estados[chave] == "bloqueada":
            return
        self.navegar.emit(chave)

    def _alternar(self) -> None:
        self._expandida = not self._expandida
        self._settings.setValue("sidebar_expandida", self._expandida)
        self._aplicar_largura()

    def _aplicar_largura(self) -> None:
        self.setFixedWidth(LARGURA_EXPANDIDA if self._expandida else LARGURA_COLAPSADA)
        for chave in self._botoes:
            self._atualizar_botao(chave)
        self._contexto.setVisible(self._expandida and bool(self._contexto.text()))

    def _atualizar_botao(self, chave: str) -> None:
        btn = self._botoes[chave]
        estado = self._estados[chave]
        glifo = self._glifos[chave]
        if estado == "completa":
            glifo = _GLIFO_COMPLETA
        elif estado == "bloqueada":
            glifo = _GLIFO_BLOQUEADA
        badge = self._badges[chave]
        sufixo = f" ({badge})" if badge else ""
        if self._expandida:
            btn.setText(f"{glifo}  {self._rotulos[chave]}{sufixo}")
            btn.setToolTip("")
        else:
            btn.setText(f"{glifo}{sufixo}" if badge else glifo)
            btn.setToolTip(self._rotulos[chave] + sufixo)
        if chave == self._ativa:
            item = "ativo"
        elif estado == "bloqueada":
            item = "bloqueado"
        else:
            item = "normal"
        btn.setProperty("item", item)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def definir_estado(self, chave: str, estado: str) -> None:
        self._estados[chave] = estado
        self._atualizar_botao(chave)

    def definir_ativa(self, chave: str) -> None:
        anterior, self._ativa = self._ativa, chave
        if anterior in self._botoes:
            self._atualizar_botao(anterior)
        self._atualizar_botao(chave)

    def atualizar_badge(self, chave: str, n: int) -> None:
        self._badges[chave] = n
        self._atualizar_botao(chave)

    def definir_contexto(self, texto: str) -> None:
        self._contexto.setText(texto)
        self._contexto.setVisible(self._expandida and bool(texto))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_sidebar.py -v`
Expected: PASS (5 testes)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/sidebar.py tests/test_ui_sidebar.py
git commit -m "feat(ui): sidebar retratil com etapas, badge e persistencia (SP-UI-1)"
```

### Task 5: MainWindow com sidebar + undo global + placeholder Geração

**Files:**
- Modify: `src/tdt/ui/app.py` (substituição integral)
- Modify: `src/tdt/ui/tela_revisao.py` (adicionar método `refresh`)
- Modify: `src/tdt/ui/tela_inicial.py` (adicionar método `log_msg`)
- Test: `tests/test_ui_app.py` (novo)

**Interfaces:**
- Consumes: `Sidebar` (Task 4), `AppState.definir_sigla(..., snapshot=False)` (Task 3).
- Produces:
  - `MainWindow._navegar(chave: str)` com chaves `entrada|revisao|config|analise|geracao` (stack 0|1|2|3|4).
  - `TelaRevisao.refresh()` — re-sincroniza view após mutação externa (undo).
  - `TelaInicial.log_msg(texto: str)` — appenda no log (indireção usada pela Task 7 ao trocar o widget de log).
  - Atributo `MainWindow.tela_geracao` (placeholder QWidget até a Task 14).

- [ ] **Step 1: Write the failing tests**

Criar `tests/test_ui_app.py`:

```python
import pytest

from tdt.contracts import (
    Descricoes, Enderecamento, ItemRevisao, ListaHomogenea, Modulo,
    ResultadoPipeline, SignalRecord, TipoSinal,
)
from tdt.ui.app import MainWindow
from tdt.ui.estado import AppState

pytest.importorskip("PySide6")


def _rec(id_, sigla, status):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"), sigla_sinal=sigla, status=status,
    )


def _estado_com_resultado():
    rev = _rec("s:2", None, "revisao")
    estado = AppState()
    estado.resultado = ResultadoPipeline(
        lista=ListaHomogenea(None, "DNP3", (_rec("s:1", "DJF1", "decidido"),)),
        revisao=(ItemRevisao(rev, "score_baixo", ()),),
    )
    estado.registros = [_rec("s:1", "DJF1", "decidido"), rev]
    estado.flags["aprovar_acima_threshold"] = False
    return estado


def _win(qtbot, estado):
    win = MainWindow(estado, config_path="config_inexistente.toml")
    qtbot.addWidget(win)
    return win


def test_comeca_com_etapas_bloqueadas(qtbot):
    win = _win(qtbot, AppState())
    assert win.sidebar._estados["revisao"] == "bloqueada"
    assert win.sidebar._estados["geracao"] == "bloqueada"
    assert win.sidebar._estados["config"] == "disponivel"


def test_executou_desbloqueia_e_vai_para_revisao(qtbot):
    win = _win(qtbot, _estado_com_resultado())
    win.tela_inicial.executou.emit()
    assert win.sidebar._estados["revisao"] == "disponivel"
    assert win.sidebar._estados["entrada"] == "completa"
    assert win.stack.currentIndex() == 1


def test_navegar_por_chave(qtbot):
    win = _win(qtbot, AppState())
    win._navegar("config")
    assert win.stack.currentIndex() == 2


def test_undo_global_restaura_e_refresca(qtbot):
    estado = _estado_com_resultado()
    win = _win(qtbot, estado)
    win.tela_inicial.executou.emit()
    estado.definir_sigla(1, "DJA1")
    assert estado.registros[1].status == "decidido"
    win._desfazer()
    assert estado.registros[1].status == "revisao"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_app.py -v`
Expected: FAIL (`AttributeError: sidebar` / `ImportError`)

- [ ] **Step 3: Implement — substituir `src/tdt/ui/app.py` integralmente por:**

```python
"""MainWindow: sidebar retrátil + QStackedWidget; navegação por chave.

ponytail: mapeamento chave->índice fixo em _INDICE; tela Geração é placeholder
até SP-UI-4 (Task 14 troca por TelaGeracao real).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QStackedWidget, QWidget,
)

from tdt.ui.estado import AppState
from tdt.ui.sidebar import Sidebar
from tdt.ui.tela_analise import TelaAnalise
from tdt.ui.tela_config import TelaConfig
from tdt.ui.tela_inicial import TelaInicial
from tdt.ui.tela_revisao import TelaRevisao

_TEMA = Path(__file__).resolve().parent / "tema.qss"

_INDICE = {"entrada": 0, "revisao": 1, "config": 2, "analise": 3, "geracao": 4}

_ITENS_FLUXO = [
    ("entrada", "1 · Entrada", "①"),
    ("revisao", "2 · Revisão", "②"),
    ("geracao", "3 · Geração", "③"),
]
_ITENS_FIXOS = [
    ("analise", "Análise", "▤"),
    ("config", "Configurações", "⚙"),
]


class MainWindow(QMainWindow):
    def __init__(self, estado: AppState, config_path="config.toml"):
        super().__init__()
        self._estado = estado
        self._config_path = Path(config_path)
        self.setWindowTitle("TDT — Analisador de Subestação")
        self.resize(1200, 700)

        self.stack = QStackedWidget()
        self.tela_inicial = TelaInicial(estado)
        self.tela_revisao = TelaRevisao(estado)
        self.tela_config = TelaConfig(estado, config_path=config_path)
        self.tela_analise = TelaAnalise()
        self.tela_geracao = self._criar_tela_geracao()

        self.stack.addWidget(self.tela_inicial)   # 0
        self.stack.addWidget(self.tela_revisao)   # 1
        self.stack.addWidget(self.tela_config)    # 2
        self.stack.addWidget(self.tela_analise)   # 3
        self.stack.addWidget(self.tela_geracao)   # 4

        self.sidebar = Sidebar(_ITENS_FLUXO, _ITENS_FIXOS)
        for chave in ("revisao", "geracao", "analise"):
            self.sidebar.definir_estado(chave, "bloqueada")
        self.sidebar.definir_ativa("entrada")
        self.sidebar.navegar.connect(self._navegar)

        self.tela_inicial.executou.connect(self._pos_execucao)
        self.tela_inicial.abrir_config.connect(lambda: self._navegar("config"))
        self.tela_revisao.voltar.connect(lambda: self._navegar("entrada"))
        self.tela_config.voltar.connect(self._voltar_config)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(container)

        self._atalho_undo = QShortcut(QKeySequence.Undo, self)
        self._atalho_undo.activated.connect(self._desfazer)

        if _TEMA.exists():
            with open(_TEMA, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _criar_tela_geracao(self) -> QWidget:
        # ponytail: placeholder até SP-UI-4 (Task 14) — evita bloquear o shell.
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.addWidget(QLabel("Geração — em construção (SP-UI-4)"))
        return w

    def _navegar(self, chave: str) -> None:
        self.stack.setCurrentIndex(_INDICE[chave])
        self.sidebar.definir_ativa(chave)

    def _voltar_config(self) -> None:
        self.tela_inicial.recarregar()
        self._navegar("entrada")

    def _desfazer(self) -> None:
        if self._estado.desfazer():
            self.tela_revisao.refresh()

    def _pos_execucao(self) -> None:
        self.tela_analise.carregar(self._estado.resultado)
        self.sidebar.definir_estado("entrada", "completa")
        for chave in ("revisao", "geracao", "analise"):
            self.sidebar.definir_estado(chave, "disponivel")
        pendentes = sum(1 for r in self._estado.registros if r.status == "revisao")
        self.sidebar.atualizar_badge("revisao", pendentes)
        self.sidebar.definir_contexto(
            f"{self._estado.subestacao or '—'} · DNP3 · "
            f"{len(self._estado.registros)} sinais"
        )
        self._ir_para_revisao()

    def _ir_para_revisao(self) -> None:
        try:
            flags = self._estado.flags
            if flags.get("pular_revisao"):
                self.tela_inicial.log_msg("[INFO] UI: revisão pulada (flag ativa)")
                return
            if flags.get("aprovar_acima_threshold"):
                threshold = self._estado.config.threshold_pct
                self._estado._snapshot()  # 1 snapshot p/ o lote inteiro
                for i, r in enumerate(self._estado.registros):
                    if r.status == "revisao" and r.candidatos \
                            and r.candidatos[0].score >= threshold:
                        self._estado.definir_sigla(
                            i, r.candidatos[0].sigla, snapshot=False)
                    if i % 100 == 0:
                        QApplication.processEvents()
            self.tela_inicial.log_msg("[INFO] UI: abrindo tela de revisão…")
            QApplication.processEvents()
            self.tela_revisao.carregar()
            self._navegar("revisao")
        except Exception as e:
            self.tela_inicial.log_msg(f"[ERRO] UI: falha ao abrir revisão — {e}")
            QMessageBox.critical(
                self, "Erro", f"Não foi possível abrir a tela de revisão:\n{e}")
```

- [ ] **Step 4: Adicionar `log_msg` em `src/tdt/ui/tela_inicial.py`**

Dentro da classe `TelaInicial` (após `recarregar`):

```python
    def log_msg(self, texto: str) -> None:
        """Indireção de log — a Task 7 troca o widget sem tocar os callers."""
        self.log.appendPlainText(texto)
```

- [ ] **Step 5: Adicionar `refresh` em `src/tdt/ui/tela_revisao.py`**

Dentro da classe `TelaRevisao` (após `carregar`):

```python
    def refresh(self) -> None:
        """Re-sincroniza a view após mutação externa de registros (ex.: undo)."""
        if not hasattr(self, "_modelo"):
            return
        self._modelo.beginResetModel()
        self._modelo.endResetModel()
        self._atualizar_painel()
```

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_ui_app.py tests/test_ui_smoke.py -v`
Expected: PASS. Se `test_ui_smoke.py` referenciar `win.abas` (QTabBar antigo), atualizar o teste para `win.sidebar` com asserts equivalentes (estado bloqueado em vez de `isTabEnabled`).

- [ ] **Step 7: Run suíte completa da UI**

Run: `python -m pytest tests -k "test_ui" -q`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add src/tdt/ui/app.py src/tdt/ui/tela_revisao.py src/tdt/ui/tela_inicial.py tests/test_ui_app.py tests/test_ui_smoke.py
git commit -m "feat(ui): shell com sidebar retratil, undo global Ctrl+Z e gating de etapas (SP-UI-1)"
```

---

## Fase 2 — SP-UI-2: Tela Entrada guiada

### Task 6: Helpers puros `motivo_bloqueio` e `linha_log_html`

**Files:**
- Modify: `src/tdt/ui/tela_inicial.py` (adicionar funções no nível do módulo)
- Test: `tests/test_ui_tela_inicial.py` (novo)

**Interfaces:**
- Produces (consumido pela Task 7):
  - `motivo_bloqueio(sigla: str, paths: dict) -> list[str]` — pendências na
    ordem `sigla da SE`, `arquivo de input`, `template DNP3`,
    `lista padrão ADMS`; lista vazia = pode executar.
  - `linha_log_html(texto: str) -> str` — linha envolta em
    `<span style="color:...">`, cor por prefixo de nível.

- [ ] **Step 1: Write the failing tests**

Criar `tests/test_ui_tela_inicial.py`:

```python
import pytest

from tdt.ui.tela_inicial import linha_log_html, motivo_bloqueio

pytest.importorskip("PySide6")


def test_motivo_bloqueio_lista_pendencias_na_ordem(tmp_path):
    arq = tmp_path / "a.xlsx"
    arq.write_text("x")
    paths = {"input": str(arq), "template": "", "lista_padrao": str(arq)}
    assert motivo_bloqueio("", paths) == ["sigla da SE", "template DNP3"]


def test_motivo_bloqueio_vazio_quando_tudo_ok(tmp_path):
    arq = tmp_path / "a.xlsx"
    arq.write_text("x")
    paths = {"input": str(arq), "template": str(arq), "lista_padrao": str(arq)}
    assert motivo_bloqueio("SAN2", paths) == []


def test_motivo_bloqueio_path_inexistente_conta_como_falta(tmp_path):
    paths = {"input": str(tmp_path / "nao_existe.xlsx"), "template": "",
             "lista_padrao": ""}
    assert motivo_bloqueio("SAN2", paths) == [
        "arquivo de input", "template DNP3", "lista padrão ADMS"]


def test_linha_log_html_cor_por_nivel():
    assert 'color:#e0604c' in linha_log_html("[ERRO] x")
    assert 'color:#e0a83f' in linha_log_html("[AVISO] x")
    assert 'color:#9aa3b5' in linha_log_html("[INFO] x")
    assert 'color:#c6ccd9' in linha_log_html("linha sem nivel")


def test_linha_log_html_escapa_html():
    assert "<b>" not in linha_log_html("[INFO] <b>oi</b>")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_inicial.py -v`
Expected: FAIL com `ImportError: cannot import name 'motivo_bloqueio'`

- [ ] **Step 3: Implement**

Em `src/tdt/ui/tela_inicial.py`, adicionar no nível do módulo (abaixo de `_MODOS`):

```python
from html import escape

_ROTULOS_FALTA = {
    "input": "arquivo de input",
    "template": "template DNP3",
    "lista_padrao": "lista padrão ADMS",
}

_CORES_NIVEL = {"[ERRO]": "#e0604c", "[AVISO]": "#e0a83f", "[INFO]": "#9aa3b5"}


def motivo_bloqueio(sigla: str, paths: dict) -> list[str]:
    """Pendências que impedem executar, na ordem de exibição. Vazio = pode."""
    faltas = []
    if not sigla.strip():
        faltas.append("sigla da SE")
    for chave, rotulo in _ROTULOS_FALTA.items():
        p = paths.get(chave, "")
        if not p or not Path(p).exists():
            faltas.append(rotulo)
    return faltas


def linha_log_html(texto: str) -> str:
    """Linha de log com cor por nível, pronta para QTextEdit.append."""
    cor = "#c6ccd9"
    for prefixo, c in _CORES_NIVEL.items():
        if texto.startswith(prefixo):
            cor = c
            break
    return f'<span style="color:{cor}">{escape(texto)}</span>'
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_tela_inicial.py -v`
Expected: PASS (5 testes)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tela_inicial.py tests/test_ui_tela_inicial.py
git commit -m "feat(ui): helpers motivo_bloqueio e linha_log_html (SP-UI-2)"
```

### Task 7: Refactor da TelaInicial (cards, motivo, etapa, log colapsável)

**Files:**
- Modify: `src/tdt/ui/tela_inicial.py` (reescrever a classe; helpers da Task 6 ficam)
- Modify: `src/tdt/ui/app.py` (1 linha: passar `config_path` à TelaInicial)
- Test: `tests/test_ui_tela_inicial.py` (adicionar)

**Interfaces:**
- Consumes: `motivo_bloqueio`, `linha_log_html` (Task 6); `salvar_config(path, config, paths)` de `tdt.ui.config_io`; QSS `QFrame[estado=...]` (Task 2).
- Produces:
  - `TelaInicial(estado, worker_factory=PipelineWorker, config_path="config.toml")` — parâmetro novo.
  - `TelaInicial.cards: dict[str, CardArquivo]` com chaves `input|template|lista_padrao|output`.
  - `CardArquivo.definir_caminho(caminho: str)` — recalcula estado ok/faltando.
  - `TelaInicial.log_msg(texto)` mantém a assinatura (agora via `linha_log_html`).
  - Sinais `executou`/`abrir_config` e API do worker inalterados.

- [ ] **Step 1: Write the failing tests (adicionar em `tests/test_ui_tela_inicial.py`)**

```python
from tdt.ui.estado import AppState
from tdt.ui.tela_inicial import CardArquivo, TelaInicial


class _WorkerFake:
    """Nunca inicia thread; só oferece a superfície de sinais usada pela tela."""

    def __init__(self, **kwargs):
        raise AssertionError("worker não deve ser criado nestes testes")


def _tela(qtbot, tmp_path, paths=None):
    estado = AppState()
    if paths:
        estado.paths.update(paths)
    tela = TelaInicial(estado, worker_factory=_WorkerFake,
                       config_path=str(tmp_path / "config.toml"))
    qtbot.addWidget(tela)
    return tela


def test_card_faltando_vira_ok_apos_recarregar(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    assert tela.cards["template"].property("estado") == "faltando"
    arq = tmp_path / "t.xlsx"
    arq.write_text("x")
    tela._estado.paths["template"] = str(arq)
    tela.recarregar()
    assert tela.cards["template"].property("estado") == "ok"


def test_label_motivo_lista_pendencias(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    tela._atualizar_estado_botao()
    assert not tela.btn_executar.isEnabled()
    assert "sigla da SE" in tela.lbl_motivo.text()


def test_botao_habilita_com_tudo_preenchido(qtbot, tmp_path):
    arq = tmp_path / "a.xlsx"
    arq.write_text("x")
    paths = {"input": str(arq), "template": str(arq), "lista_padrao": str(arq)}
    tela = _tela(qtbot, tmp_path, paths)
    tela.combo_sub.lineEdit().setText("SAN2")
    assert tela.btn_executar.isEnabled()
    assert not tela.lbl_motivo.isVisibleTo(tela)


def test_erro_do_worker_expande_log(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    assert not tela.log.isVisibleTo(tela)
    tela._on_erro("explodiu")
    assert tela.log.isVisibleTo(tela)
    assert "explodiu" in tela.log.toPlainText()


def test_log_msg_info_atualiza_etapa(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    tela._on_log("[INFO] pipeline: normalizando descrições…")
    assert "normalizando" in tela.lbl_etapa.text()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_inicial.py -v`
Expected: FAIL (`cards`/`lbl_motivo`/`lbl_etapa` não existem; `config_path` não aceito)

- [ ] **Step 3: Implement — reescrever `src/tdt/ui/tela_inicial.py`**

Substituir o arquivo inteiro por (helpers da Task 6 já incluídos):

```python
"""Tela Entrada: setup guiado com cards de estado; dispara o pipeline.

ponytail: cards são QFrame com propriedade QSS estado="ok|faltando"; a
validação vive em motivo_bloqueio (pura). Worker injetável p/ teste.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import openpyxl
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QPushButton, QRadioButton, QTextEdit, QVBoxLayout, QWidget,
)

from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT, DEFAULT_TEMPLATE
from tdt.ui.config_io import salvar_config
from tdt.ui.estado import AppState
from tdt.ui.worker import PipelineWorker

_MODOS = [("Automático (detecta pelo header)", "auto"),
          ("Homogêneo", "homogeneo"),
          ("Não homogêneo", "nao-homogeneo")]

_ROTULOS_FALTA = {
    "input": "arquivo de input",
    "template": "template DNP3",
    "lista_padrao": "lista padrão ADMS",
}

_CORES_NIVEL = {"[ERRO]": "#e0604c", "[AVISO]": "#e0a83f", "[INFO]": "#9aa3b5"}


def motivo_bloqueio(sigla: str, paths: dict) -> list[str]:
    """Pendências que impedem executar, na ordem de exibição. Vazio = pode."""
    faltas = []
    if not sigla.strip():
        faltas.append("sigla da SE")
    for chave, rotulo in _ROTULOS_FALTA.items():
        p = paths.get(chave, "")
        if not p or not Path(p).exists():
            faltas.append(rotulo)
    return faltas


def pode_executar(sigla_se: str, input_ok: bool) -> bool:
    """Mantida por compatibilidade com testes/chamadores existentes."""
    return bool(sigla_se.strip()) and input_ok


def linha_log_html(texto: str) -> str:
    """Linha de log com cor por nível, pronta para QTextEdit.append."""
    cor = "#c6ccd9"
    for prefixo, c in _CORES_NIVEL.items():
        if texto.startswith(prefixo):
            cor = c
            break
    return f'<span style="color:{cor}">{escape(texto)}</span>'


class CardArquivo(QFrame):
    """Card de pré-requisito com estado visual ok/faltando."""

    def __init__(self, titulo: str, ao_clicar):
        super().__init__()
        self._titulo = titulo
        self.lbl_titulo = QLabel(titulo)
        self.lbl_valor = QLabel("não configurado")
        self.lbl_valor.setProperty("nivel", "aviso")
        self.btn = QPushButton("Selecionar…")
        self.btn.clicked.connect(ao_clicar)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(self.lbl_titulo)
        col.addWidget(self.lbl_valor)
        lay = QHBoxLayout(self)
        lay.addLayout(col, 1)
        lay.addWidget(self.btn)
        self.definir_caminho("")

    def definir_caminho(self, caminho: str) -> None:
        ok = bool(caminho) and Path(caminho).exists()
        self.setProperty("estado", "ok" if ok else "faltando")
        if ok:
            self.lbl_titulo.setText(f"✓ {self._titulo}")
            self.lbl_valor.setText(Path(caminho).name)
            self.lbl_valor.setProperty("nivel", "")
            self.setToolTip(caminho)
            self.btn.setText("Trocar…")
        else:
            self.lbl_titulo.setText(f"! {self._titulo}")
            self.lbl_valor.setText("não configurado")
            self.lbl_valor.setProperty("nivel", "aviso")
            self.setToolTip("")
            self.btn.setText("Selecionar…")
        for w in (self, self.lbl_valor):
            w.style().unpolish(w)
            w.style().polish(w)


class TelaInicial(QWidget):
    abrir_config = Signal()
    executou = Signal()

    def __init__(self, estado: AppState, worker_factory=PipelineWorker,
                 config_path="config.toml"):
        super().__init__()
        self._estado = estado
        self._worker_factory = worker_factory
        self._worker = None
        self._config_path = config_path

        # --- coluna Arquivos: cards ---
        self.cards: dict[str, CardArquivo] = {}
        defs = [
            ("input", "Input", False, DEFAULT_LISTA),
            ("template", "Template DNP3", False, DEFAULT_TEMPLATE),
            ("lista_padrao", "Lista Padrão ADMS", False, DEFAULT_LISTA),
            ("output", "Pasta de saída", True, DEFAULT_OUTPUT),
        ]
        col_arq = QVBoxLayout()
        for chave, titulo, is_pasta, _default in defs:
            card = CardArquivo(
                titulo,
                lambda _=False, c=chave, p=is_pasta: self._escolher(c, p))
            self.cards[chave] = card
            col_arq.addWidget(card)
        self._defaults_dialogo = {c: d for c, _t, _p, d in defs}

        self.lbl_sheets = QLabel("Sheets")
        self.lista_sheets = QListWidget()
        self.lista_sheets.itemChanged.connect(self._sheet_alterada)
        col_arq.addWidget(self.lbl_sheets)
        col_arq.addWidget(self.lista_sheets, 1)

        # --- coluna Análise ---
        self.combo_sub = QComboBox()
        self.combo_sub.setEditable(True)
        self.combo_sub.lineEdit().setPlaceholderText("sigla da SE, ex.: SAN2")
        self.combo_sub.lineEdit().textChanged.connect(self._atualizar_estado_botao)

        self.combo_proto = QComboBox()
        self.combo_proto.addItem("DNP3")

        self.grupo_modo = QButtonGroup(self)
        cx_modo = QVBoxLayout()
        for i, (rotulo, _val) in enumerate(_MODOS):
            rb = QRadioButton(rotulo)
            if i == 0:
                rb.setChecked(True)
            self.grupo_modo.addButton(rb, i)
            cx_modo.addWidget(rb)

        self.chk_pular = QCheckBox("Pular revisão manual")
        self.chk_aprovar = QCheckBox("Aprovar auto. acima do threshold")
        self.chk_aprovar.setChecked(
            estado.flags.get("aprovar_acima_threshold", True))

        col_ana = QVBoxLayout()
        col_ana.addWidget(QLabel("Subestação *"))
        col_ana.addWidget(self.combo_sub)
        col_ana.addWidget(QLabel("Protocolo"))
        col_ana.addWidget(self.combo_proto)
        col_ana.addWidget(QLabel("Método de processamento"))
        col_ana.addLayout(cx_modo)
        col_ana.addWidget(QLabel("Flags"))
        col_ana.addWidget(self.chk_pular)
        col_ana.addWidget(self.chk_aprovar)
        col_ana.addStretch()

        # --- faixa de execução ---
        self.btn_executar = QPushButton("Executar análise")
        self.btn_executar.setProperty("acao", "principal")
        self.btn_executar.clicked.connect(self._executar)
        self.btn_parar = QPushButton("Parar")
        self.btn_parar.clicked.connect(self._parar)
        self.btn_parar.setEnabled(False)
        btn_cfg = QPushButton("⚙")
        btn_cfg.setToolTip("Configurações")
        btn_cfg.clicked.connect(self.abrir_config.emit)

        self.lbl_motivo = QLabel("")
        self.lbl_motivo.setProperty("nivel", "aviso")
        self.lbl_motivo.setVisible(False)

        self.lbl_etapa = QLabel("")
        self.lbl_etapa.setVisible(False)
        self.progresso_bar = QProgressBar()
        self.progresso_bar.setVisible(False)

        self.btn_toggle_log = QPushButton("Ver log ▾")
        self.btn_toggle_log.clicked.connect(self._alternar_log)
        self.btn_limpar_log = QPushButton("Limpar log")
        self.btn_limpar_log.clicked.connect(lambda: self.log.clear())
        self.btn_limpar_log.setVisible(False)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)

        botoes = QHBoxLayout()
        botoes.addWidget(self.btn_executar)
        botoes.addWidget(self.btn_parar)
        botoes.addStretch()
        botoes.addWidget(self.btn_toggle_log)
        botoes.addWidget(self.btn_limpar_log)
        botoes.addWidget(btn_cfg)

        faixa_exec = QVBoxLayout()
        faixa_exec.addLayout(botoes)
        faixa_exec.addWidget(self.lbl_motivo)
        faixa_exec.addWidget(self.lbl_etapa)
        faixa_exec.addWidget(self.progresso_bar)
        faixa_exec.addWidget(self.log, 1)

        def _grupo(titulo, layout):
            g = QGroupBox(titulo)
            g.setLayout(layout)
            return g

        colunas = QHBoxLayout()
        colunas.addWidget(_grupo("Arquivos", col_arq), 1)
        colunas.addWidget(_grupo("Análise", col_ana), 1)

        raiz = QVBoxLayout(self)
        raiz.addLayout(colunas, 1)
        raiz.addLayout(faixa_exec)

        self.recarregar()

    # --- estado / validação ---
    def recarregar(self) -> None:
        p = self._estado.paths
        for chave, card in self.cards.items():
            card.definir_caminho(p.get(chave, ""))
        self._atualizar_estado_botao()

    def _atualizar_estado_botao(self) -> None:
        faltas = motivo_bloqueio(self.combo_sub.currentText(), self._estado.paths)
        self.btn_executar.setEnabled(not faltas)
        self.lbl_motivo.setText("Falta: " + ", ".join(faltas) if faltas else "")
        self.lbl_motivo.setVisible(bool(faltas))

    def _escolher(self, chave: str, is_pasta: bool) -> None:
        atual = self._estado.paths.get(chave, "") or self._defaults_dialogo[chave]
        if is_pasta:
            caminho = QFileDialog.getExistingDirectory(
                self, "Pasta de saída", dir=atual)
        else:
            caminho, _ = QFileDialog.getOpenFileName(
                self, f"Selecionar {chave}", dir=atual, filter="Excel (*.xlsx)")
        if not caminho:
            return
        self._estado.paths[chave] = caminho
        self.cards[chave].definir_caminho(caminho)
        salvar_config(self._config_path, self._estado.config, self._estado.paths)
        if chave == "input":
            self._popular_sheets(caminho)
        self._atualizar_estado_botao()

    # --- sheets (inalterado em relação à versão anterior) ---
    def _popular_sheets(self, caminho):
        self.lista_sheets.clear()
        try:
            wb = openpyxl.load_workbook(caminho, read_only=True)
            nomes = wb.sheetnames
            wb.close()
        except Exception as e:
            self.log_msg(f"[ERRO] não li sheets: {e}")
            return
        aliases = self._estado.aliases
        for nome in nomes:
            texto = aliases.get(nome, nome)
            it = QListWidgetItem(texto)
            it.setData(Qt.UserRole, nome)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            it.setCheckState(Qt.Checked)
            self.lista_sheets.addItem(it)
        self._atualizar_rotulo_sheets()

    def _sheet_alterada(self, it: QListWidgetItem) -> None:
        original = it.data(Qt.UserRole)
        novo = it.text().strip()
        if novo and novo != original:
            self._estado.aliases[original] = novo
        elif original in self._estado.aliases:
            del self._estado.aliases[original]
        if it.checkState() == Qt.Unchecked:
            self._estado.sheets_excluidas.add(original)
        else:
            self._estado.sheets_excluidas.discard(original)
        self._atualizar_rotulo_sheets()

    def _atualizar_rotulo_sheets(self) -> None:
        total = self.lista_sheets.count()
        marcadas = sum(
            1 for i in range(total)
            if self.lista_sheets.item(i).checkState() == Qt.Checked)
        self.lbl_sheets.setText(
            f"Sheets · {marcadas} de {total} marcadas" if total else "Sheets")

    def _sheets_selecionadas(self) -> list[str] | None:
        if self.lista_sheets.count() == 0:
            return None
        return [
            it.data(Qt.UserRole)
            for i in range(self.lista_sheets.count())
            if (it := self.lista_sheets.item(i)).checkState() == Qt.Checked
        ]

    # --- execução ---
    def _coletar(self):
        self._estado.modo = _MODOS[self.grupo_modo.checkedId()][1]
        self._estado.flags["pular_revisao"] = self.chk_pular.isChecked()
        self._estado.flags["aprovar_acima_threshold"] = self.chk_aprovar.isChecked()
        texto = self.combo_sub.currentText().strip()
        self._estado.subestacao = None if not texto else texto

    def _executar(self):
        self._coletar()
        faltas = motivo_bloqueio(self.combo_sub.currentText(), self._estado.paths)
        if faltas:
            QMessageBox.warning(self, "Pendências",
                                "Resolva antes de executar:\n"
                                + "\n".join(f"  • {f}" for f in faltas))
            self._fim()
            return
        self.btn_executar.setEnabled(False)
        self.btn_parar.setEnabled(True)
        sheets = self._sheets_selecionadas()
        self._worker = self._worker_factory(
            paths=self._estado.paths, config=self._estado.config,
            modo=self._estado.modo, subestacao=self._estado.subestacao,
            app_state=self._estado, sheets=sheets,
            aliases=dict(self._estado.aliases),
        )
        self._worker.log.connect(self._on_log)
        self._worker.erro.connect(self._on_erro)
        self._worker.erro.connect(self._fim)
        self._worker.terminado.connect(self._terminado)
        self._worker.progresso.connect(self._atualizar_progresso)
        self._worker.start()

    # --- log / progresso ---
    def log_msg(self, texto: str) -> None:
        self.log.append(linha_log_html(texto))

    def _on_log(self, texto: str) -> None:
        self.log_msg(texto)
        if texto.startswith("[INFO]"):
            self.lbl_etapa.setText(texto[len("[INFO]"):].strip())
            self.lbl_etapa.setVisible(True)

    def _on_erro(self, msg: str) -> None:
        self.log_msg(f"[ERRO] {msg}")
        self._mostrar_log(True)

    def _alternar_log(self) -> None:
        self._mostrar_log(not self.log.isVisibleTo(self))

    def _mostrar_log(self, visivel: bool) -> None:
        self.log.setVisible(visivel)
        self.btn_limpar_log.setVisible(visivel)
        self.btn_toggle_log.setText("Ocultar log ▴" if visivel else "Ver log ▾")

    def _atualizar_progresso(self, atual: int, total: int) -> None:
        self.progresso_bar.setVisible(True)
        self.progresso_bar.setMaximum(total)
        self.progresso_bar.setValue(atual)

    def _terminado(self, resultado):
        self._estado.carregar_resultado(resultado)
        caminho_lp = self._estado.paths.get("lista_padrao", "")
        if caminho_lp:
            try:
                self._estado.lista_padrao = ListaPadraoADMS.carregar(caminho_lp)
            except Exception as e:
                self.log_msg(f"[AVISO] não carreguei lista padrão p/ UI: {e}")
        self._fim()
        self.executou.emit()

    def _parar(self):
        if self._worker is not None:
            self._worker.parar()
            self.log_msg("[AVISO] Parar solicitado")

    def _fim(self, *args):
        self._atualizar_estado_botao()
        self.btn_parar.setEnabled(False)
        self.progresso_bar.setVisible(False)
        self.lbl_etapa.setVisible(False)
```

- [ ] **Step 4: Ajustar o call site em `src/tdt/ui/app.py`**

Trocar `self.tela_inicial = TelaInicial(estado)` por:

```python
        self.tela_inicial = TelaInicial(estado, config_path=config_path)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_ui_tela_inicial.py tests/test_ui_app.py -v`
Expected: PASS. Se algum teste antigo referenciar `ed_input`/`ed_output` (removidos), atualizar para `cards["input"]`/`cards["output"]`.

- [ ] **Step 6: Run suíte completa + verificação visual**

Run: `python -m pytest tests -k "test_ui" -q` → PASS
Run: `python -m tdt.ui_main` → cards refletem config.toml; botão explica pendências; "Ver log ▾" alterna o log. Fechar.

- [ ] **Step 7: Commit**

```bash
git add src/tdt/ui/tela_inicial.py src/tdt/ui/app.py tests/test_ui_tela_inicial.py
git commit -m "feat(ui): tela Entrada guiada com cards de estado e log colapsavel (SP-UI-2)"
```

---

## Fase 3 — SP-UI-3: Revisão — teclado, filtro unificado, colunas

### Task 8: `set_status_visivel` no proxy + segmented Todos/Pendentes/Decididos

**Files:**
- Modify: `src/tdt/ui/proxy_revisao.py`
- Modify: `src/tdt/ui/tela_revisao.py`
- Test: `tests/test_ui_proxy_revisao.py` (adicionar; atualizar usos de `setEsconderDecididos`)

**Interfaces:**
- Produces:
  - `ProxyRevisao.set_status_visivel(status: str | None)` — `None`=todos,
    `"revisao"`, `"decidido"`. **Remove** `setEsconderDecididos`.
  - `TelaRevisao.mostrar_pendentes()` — ativa o segmented "Pendentes"
    (consumido pela Task 14).

- [ ] **Step 1: Write the failing tests (adicionar em `tests/test_ui_proxy_revisao.py`)**

Usar os helpers/fixtures já existentes no arquivo para construir o proxy com registros mistos (um `decidido`, um `revisao`) e adicionar:

```python
def test_set_status_visivel_revisao_esconde_decididos(qtbot):
    proxy = _proxy_com([_rec("a:1", "DJF1", "decidido"), _rec("a:2", None, "revisao")])
    proxy.set_status_visivel("revisao")
    assert proxy.rowCount() == 1


def test_set_status_visivel_none_mostra_tudo(qtbot):
    proxy = _proxy_com([_rec("a:1", "DJF1", "decidido"), _rec("a:2", None, "revisao")])
    proxy.set_status_visivel("decidido")
    proxy.set_status_visivel(None)
    assert proxy.rowCount() == 2
```

Nota: se o arquivo não tiver um helper `_proxy_com`/`_rec` com essas assinaturas, criar localmente no padrão do arquivo (ModeloSinais sobre AppState com os registros, proxy.setSourceModel). Atualizar TODOS os testes existentes que chamam `setEsconderDecididos(True)` para `set_status_visivel("revisao")` (e `False` → `None`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_proxy_revisao.py -v`
Expected: FAIL com `AttributeError: set_status_visivel`

- [ ] **Step 3: Implement no proxy**

Em `src/tdt/ui/proxy_revisao.py`:

1. No `__init__`: trocar `self._esconder_decididos = False` por
   `self._status_visivel: str | None = None`.
2. Substituir o método `setEsconderDecididos` por:

```python
    def set_status_visivel(self, status: str | None) -> None:
        """None = todos; "revisao"/"decidido" mostram só esse status."""
        self._status_visivel = status
        self.invalidateFilter()
```

3. Em `filterAcceptsRow`, substituir o bloco `if self._esconder_decididos:` por:

```python
        if self._status_visivel is not None:
            idx = self.sourceModel().index(source_row, _COL_STATUS, source_parent)
            if self.sourceModel().data(idx) != self._status_visivel:
                return False
```

- [ ] **Step 4: Implement na tela**

Em `src/tdt/ui/tela_revisao.py`:

1. No `__init__`, substituir o bloco do `self.chk_so_revisao` (criação e
   conexão) por:

```python
        self.grupo_status = QButtonGroup(self)
        self._status_por_id = {0: None, 1: "revisao", 2: "decidido"}
        botoes_status = QHBoxLayout()
        for i, rotulo in enumerate(("Todos", "Pendentes", "Decididos")):
            b = QPushButton(rotulo)
            b.setCheckable(True)
            if i == 0:
                b.setChecked(True)
            self.grupo_status.addButton(b, i)
            botoes_status.addWidget(b)
        self.grupo_status.idClicked.connect(self._filtrar_status_id)
```

   e na montagem da `barra_filtro`, trocar `barra_filtro.addWidget(self.chk_so_revisao)` por `barra_filtro.addLayout(botoes_status)`.
   Importar `QButtonGroup` de `PySide6.QtWidgets`.

2. Substituir `_filtrar_status` por:

```python
    def _filtrar_status_id(self, id_botao: int) -> None:
        if hasattr(self, "_proxy"):
            self._proxy.set_status_visivel(self._status_por_id[id_botao])

    def mostrar_pendentes(self) -> None:
        """Ativa o filtro Pendentes (usado pela tela de Geração)."""
        self.grupo_status.button(1).setChecked(True)
        self._filtrar_status_id(1)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_ui_proxy_revisao.py tests/test_ui_tela_revisao.py -v`
Expected: PASS (corrigir qualquer teste remanescente que use `chk_so_revisao`)

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/proxy_revisao.py src/tdt/ui/tela_revisao.py tests/test_ui_proxy_revisao.py tests/test_ui_tela_revisao.py
git commit -m "feat(ui): filtro de status segmented Todos/Pendentes/Decididos (SP-UI-3)"
```

### Task 9: Filtro de coluna unificado (um gatilho, um popup) + chip limpar

**Files:**
- Modify: `src/tdt/ui/proxy_revisao.py`
- Modify: `src/tdt/ui/tela_revisao.py`
- Test: `tests/test_ui_tela_revisao.py`, `tests/test_ui_proxy_revisao.py`

**Interfaces:**
- Produces:
  - `ProxyRevisao.filtros_ativos() -> int`, `ProxyRevisao.limpar_filtros()`.
  - Marcador `" ▼*"` no header agora cobre também filtros de texto ("contém").
  - `FiltroColunaDialog(nome, valores, selecionados, contem_inicial="", parent=None)`
    com `texto_contem() -> str`.
  - `TelaRevisao.filtrar_endereco(texto: str)` — aplica "contém" na coluna
    Endereço (consumido pela Task 14).
- Removes: `TelaRevisao._construir_menu_coluna`, `_eh_coluna_modulo`,
  `_abrir_filtro_coluna_excel` e a conexão `sectionDoubleClicked`.

- [ ] **Step 1: Write the failing tests**

Em `tests/test_ui_proxy_revisao.py`, adicionar:

```python
def test_filtros_ativos_conta_texto_e_valores(qtbot):
    proxy = _proxy_com([_rec("a:1", "DJF1", "decidido")])
    assert proxy.filtros_ativos() == 0
    proxy.setFiltroColuna(0, "DJ")
    proxy.set_filtro_coluna(2, {"decidido"})
    assert proxy.filtros_ativos() == 2
    proxy.limpar_filtros()
    assert proxy.filtros_ativos() == 0


def test_marcador_header_para_filtro_texto(qtbot):
    from PySide6.QtCore import Qt
    proxy = _proxy_com([_rec("a:1", "DJF1", "decidido")])
    proxy.setFiltroColuna(0, "DJ")
    assert "▼" in proxy.headerData(0, Qt.Horizontal, Qt.DisplayRole)
```

Em `tests/test_ui_tela_revisao.py`: **remover** os testes
`test_menu_filtro_modulo_lista_valores_distintos`,
`test_selecionar_modulo_no_menu_aplica_filtro_via_proxy`,
`test_outras_colunas_continuam_usando_dialogo_texto_livre` e
`test_coluna_modulo_nao_usa_dialogo_texto_livre` (mecanismos removidos), e
adicionar:

```python
def test_popup_unificado_aplica_contem_e_valores(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
    ])
    col = ModeloSinais.COLUNAS.index("Descr. bruta")

    class _DialogFake:
        def __init__(self, *a, **k):
            pass
        def exec(self):
            from PySide6.QtWidgets import QDialog
            return QDialog.Accepted
        def valores_selecionados(self):
            return None
        def texto_contem(self):
            return "DISJ"

    monkeypatch.setattr("tdt.ui.tela_revisao.FiltroColunaDialog", _DialogFake)
    monkeypatch.setattr(
        tela.tabela.horizontalHeader(), "logicalIndexAt", lambda pos: col)
    tela._filtrar_coluna(QPoint(0, 0))
    assert tela._proxy.filtroColuna(col) == "DISJ"
    assert tela._proxy.rowCount() == 1
    assert tela.btn_limpar_filtros.isVisibleTo(tela)


def test_limpar_todos_zera_filtros(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A"), _rec("2", "SE2", "B")])
    col = ModeloSinais.COLUNAS.index("Módulo")
    tela._proxy.setFiltroColuna(col, "SE1")
    tela._atualizar_chip_filtros()
    tela._limpar_filtros()
    assert tela._proxy.filtros_ativos() == 0
    assert tela._proxy.rowCount() == 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_proxy_revisao.py tests/test_ui_tela_revisao.py -v`
Expected: FAIL (`filtros_ativos` não existe; `btn_limpar_filtros` não existe)

- [ ] **Step 3: Implement no proxy (`src/tdt/ui/proxy_revisao.py`)**

1. Substituir `setFiltroColuna` por (ganha notificação de header):

```python
    def setFiltroColuna(self, col: int, texto: str) -> None:
        estava = col in self._filtros_coluna
        if texto:
            self._filtros_coluna[col] = texto.upper()
        else:
            self._filtros_coluna.pop(col, None)
        self.invalidateFilter()
        if estava != (col in self._filtros_coluna):
            self.headerDataChanged.emit(Qt.Horizontal, col, col)
```

2. Em `headerData`, trocar a condição `secao in self._filtros_coluna_valores`
   por `(secao in self._filtros_coluna_valores or secao in self._filtros_coluna)`.
3. Adicionar após `colunas_filtradas`:

```python
    def filtros_ativos(self) -> int:
        return len(set(self._filtros_coluna) | set(self._filtros_coluna_valores))

    def limpar_filtros(self) -> None:
        cols = set(self._filtros_coluna) | set(self._filtros_coluna_valores)
        self._filtros_coluna.clear()
        self._filtros_coluna_valores.clear()
        self.invalidateFilter()
        for col in cols:
            self.headerDataChanged.emit(Qt.Horizontal, col, col)
```

- [ ] **Step 4: Implement na tela (`src/tdt/ui/tela_revisao.py`)**

1. `FiltroColunaDialog.__init__` ganha `contem_inicial: str = ""` (antes de
   `parent`) e, como primeiro widget do layout:

```python
        self.ed_contem = QLineEdit(contem_inicial)
        self.ed_contem.setPlaceholderText("contém… (texto livre)")
        layout.addWidget(self.ed_contem)
```

   e o método:

```python
    def texto_contem(self) -> str:
        return "" if self._limpo else self.ed_contem.text().strip()
```

2. Substituir `_filtrar_coluna` inteiro por:

```python
    def _filtrar_coluna(self, pos) -> None:
        col = self.tabela.horizontalHeader().logicalIndexAt(pos)
        if col < 0:
            return
        nome = ModeloSinais.COLUNAS[col]
        valores = self._proxy.valores_unicos(col)
        atuais = self._selecao_filtro_coluna.get(col)
        dialog = FiltroColunaDialog(
            nome, valores, atuais,
            contem_inicial=self._proxy.filtroColuna(col), parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        novos = dialog.valores_selecionados()
        self._proxy.set_filtro_coluna(col, novos)
        self._proxy.setFiltroColuna(col, dialog.texto_contem())
        if novos is None:
            self._selecao_filtro_coluna.pop(col, None)
        else:
            self._selecao_filtro_coluna[col] = novos
        self._atualizar_chip_filtros()
```

3. **Deletar** `_construir_menu_coluna`, `_eh_coluna_modulo`,
   `_abrir_filtro_coluna_excel`; em `carregar()`, deletar a linha
   `...sectionDoubleClicked.connect(...)` e o comentário sobre gatilhos
   distintos. Remover import de `QMenu` e `QInputDialog` se ficarem sem uso.
4. No `__init__`, adicionar à `barra_filtro` (antes do `addStretch`):

```python
        self.btn_limpar_filtros = QPushButton("")
        self.btn_limpar_filtros.setVisible(False)
        self.btn_limpar_filtros.clicked.connect(self._limpar_filtros)
        barra_filtro.addWidget(self.btn_limpar_filtros)
```

5. Adicionar os métodos:

```python
    def _atualizar_chip_filtros(self) -> None:
        n = self._proxy.filtros_ativos()
        self.btn_limpar_filtros.setText(f"Filtros ativos: {n} — limpar todos")
        self.btn_limpar_filtros.setVisible(n > 0)

    def _limpar_filtros(self) -> None:
        self._proxy.limpar_filtros()
        self._selecao_filtro_coluna.clear()
        self._atualizar_chip_filtros()

    def filtrar_endereco(self, texto: str) -> None:
        """Filtro "contém" na coluna Endereço (usado pela tela de Geração)."""
        col = ModeloSinais.COLUNAS.index("Endereço")
        self._proxy.setFiltroColuna(col, texto)
        self._atualizar_chip_filtros()
```

6. Em `carregar()`, após montar o proxy, chamar `self._atualizar_chip_filtros()`.

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_ui_tela_revisao.py tests/test_ui_proxy_revisao.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/proxy_revisao.py src/tdt/ui/tela_revisao.py tests/test_ui_tela_revisao.py tests/test_ui_proxy_revisao.py
git commit -m "feat(ui): filtro de coluna unificado com chip limpar todos (SP-UI-3)"
```

### Task 10: Aprovar e ir ao próximo + atalhos de teclado

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py`
- Modify: `src/tdt/ui/app.py` (conectar `desfazer_pedido`)
- Test: `tests/test_ui_tela_revisao.py`

**Interfaces:**
- Consumes: `ModeloSinais.definir_sigla(linha, sigla)` (existente).
- Produces:
  - `TelaRevisao._aprovar_e_proximo(indice_candidato: int | None = None)`.
  - sinal `TelaRevisao.desfazer_pedido = Signal()` (MainWindow conecta ao `_desfazer`).
  - Atalhos: Enter/Return (aprovar+próximo), `1`–`5` (candidato N), Ctrl+F (busca ADMS).

- [ ] **Step 1: Write the failing tests (adicionar em `tests/test_ui_tela_revisao.py`)**

```python
from tdt.contracts import Candidato


def _rec_cand(id_, bruta, status="revisao", candidatos=()):
    return SignalRecord(
        id=id_, modulo=Modulo("M1", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,), ()),
        descricoes=Descricoes(bruta, bruta), status=status,
        candidatos=tuple(candidatos),
    )


def test_aprovar_e_proximo_define_sigla_e_move_selecao(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec_cand("s:1", "A", candidatos=[Candidato("DJF1", 0.9)]),
        _rec_cand("s:2", "B", status="decidido"),
        _rec_cand("s:3", "C", candidatos=[Candidato("DJA1", 0.8)]),
    ])
    tela.tabela.selectRow(0)
    tela._aprovar_e_proximo()
    assert tela._estado.registros[0].sigla_sinal == "DJF1"
    assert tela._estado.registros[0].status == "decidido"
    linha_proxy = tela.tabela.selectionModel().currentIndex().row()
    fonte = tela._proxy.mapToSource(tela._proxy.index(linha_proxy, 0)).row()
    assert tela._estado.registros[fonte].id == "s:3"


def test_aprovar_e_proximo_com_indice_usa_candidato_n(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec_cand("s:1", "A", candidatos=[
            Candidato("DJF1", 0.9), Candidato("DJA1", 0.5)]),
    ])
    tela.tabela.selectRow(0)
    tela._aprovar_e_proximo(1)
    assert tela._estado.registros[0].sigla_sinal == "DJA1"


def test_aprovar_sem_candidatos_e_noop(qtbot):
    tela = _tela_carregada(qtbot, [_rec_cand("s:1", "A", candidatos=[])])
    tela.tabela.selectRow(0)
    tela._aprovar_e_proximo()
    assert tela._estado.registros[0].status == "revisao"
```

Nota: verificar a assinatura real de `Candidato` em `src/tdt/contracts.py`
antes de escrever (esperado: `Candidato(sigla, score)`; se houver campos
extras com default, os posicionais bastam).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_revisao.py -v -k "aprovar"`
Expected: FAIL com `AttributeError: _aprovar_e_proximo`

- [ ] **Step 3: Implement (`src/tdt/ui/tela_revisao.py`)**

1. Imports: `from PySide6.QtGui import QKeySequence, QShortcut` e adicionar
   `QApplication` ao import de QtWidgets.
2. Adicionar `desfazer_pedido = Signal()` ao lado de `voltar = Signal()`.
3. No `__init__`, no `topo` (após `btn_voltar`):

```python
        btn_desfazer = QPushButton("↶ Desfazer (Ctrl+Z)")
        btn_desfazer.clicked.connect(self.desfazer_pedido.emit)
        topo.insertWidget(1, btn_desfazer)
```

   e o botão principal na barra de ações do topo — trocar
   `btn_gerar = QPushButton("aprovar / gerar TDT")` por:

```python
        btn_gerar = QPushButton("Gerar TDT…")
        btn_gerar.clicked.connect(self._gerar)
        self.btn_aprovar = QPushButton("Aprovar e ir ao próximo (Enter)")
        self.btn_aprovar.setProperty("acao", "principal")
        self.btn_aprovar.clicked.connect(lambda: self._aprovar_e_proximo())
        topo.addWidget(self.btn_aprovar)
```

   (mantendo `topo.addWidget(btn_gerar)` — a Task 14 remove o botão Gerar.)
4. Ainda no `__init__`, registrar os atalhos:

```python
        for tecla in (Qt.Key_Return, Qt.Key_Enter):
            atalho = QShortcut(QKeySequence(tecla), self.tabela)
            atalho.setContext(Qt.WidgetShortcut)
            atalho.activated.connect(lambda: self._aprovar_e_proximo())
        for n in range(1, 6):
            atalho = QShortcut(QKeySequence(str(n)), self.tabela)
            atalho.setContext(Qt.WidgetShortcut)
            atalho.activated.connect(
                lambda n=n: self._aprovar_e_proximo(n - 1))
        atalho_busca = QShortcut(QKeySequence.Find, self)
        atalho_busca.activated.connect(self.busca.setFocus)
```

5. Adicionar os métodos:

```python
    def _proximo_pendente(self, apos_linha_proxy: int) -> int:
        """Próxima linha visível no proxy com status "revisao" (com wrap)."""
        total = self._proxy.rowCount()
        if total == 0:
            return -1
        col_status = ModeloSinais.COLUNAS.index("Status")
        for delta in range(1, total + 1):
            linha = (apos_linha_proxy + delta) % total
            if self._proxy.index(linha, col_status).data() == "revisao":
                return linha
        return -1

    def _aprovar_e_proximo(self, indice_candidato: int | None = None) -> None:
        if not hasattr(self, "_proxy"):
            return
        r = self._registro()
        if r is None:
            return
        if indice_candidato is not None:
            if indice_candidato >= len(r.candidatos):
                QApplication.beep()
                return
            sigla = r.candidatos[indice_candidato].sigla
        else:
            item = self.lista_candidatos.currentItem()
            sigla = item.data(Qt.UserRole) if item else None
            if not sigla and r.candidatos:
                sigla = r.candidatos[0].sigla
        if not sigla:
            QApplication.beep()
            return
        atual = self.tabela.selectionModel().currentIndex()
        linha_proxy = atual.row() if atual.isValid() else -1
        self._modelo.definir_sigla(self._linha, sigla)
        proxima = self._proximo_pendente(linha_proxy)
        if proxima >= 0:
            self.tabela.selectRow(proxima)
        else:
            self._atualizar_painel()
```

6. Em `src/tdt/ui/app.py`, junto das outras conexões:

```python
        self.tela_revisao.desfazer_pedido.connect(self._desfazer)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_ui_tela_revisao.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tela_revisao.py src/tdt/ui/app.py tests/test_ui_tela_revisao.py
git commit -m "feat(ui): aprovar-e-proximo com atalhos Enter/1-5 e botao desfazer (SP-UI-3)"
```

### Task 11: Abas por sheet com contador de pendentes + badge da sidebar

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py` (método novo)
- Modify: `src/tdt/ui/tela_revisao.py`
- Modify: `src/tdt/ui/app.py` (conectar badge)
- Test: `tests/test_ui_modelo_tabela.py`, `tests/test_ui_tela_revisao.py`

**Interfaces:**
- Produces:
  - `ModeloSinais.pendentes_por_sheet() -> dict[str, int]`.
  - sinal `TelaRevisao.pendentes_mudaram = Signal(int)` (total de pendentes).
  - Abas passam a guardar o nome real da sheet em `tabData` (rótulo vira
    decorado) — `_trocar_aba_sheet` lê `tabData`, não `tabText`.

- [ ] **Step 1: Write the failing tests**

Em `tests/test_ui_modelo_tabela.py`:

```python
def test_pendentes_por_sheet_conta_so_revisao(qtbot):
    st = AppState()
    st.registros = [
        _rec("SAN2:1", "M", "A"),
        _rec("SAN2:2", "M", "B"),
        _rec("TRAFO:1", "M", "C"),
    ]
    st.registros[0] = replace(st.registros[0], status="decidido")
    st.registros[1] = replace(st.registros[1], status="revisao")
    st.registros[2] = replace(st.registros[2], status="revisao")
    modelo = ModeloSinais(st)
    assert modelo.pendentes_por_sheet() == {"SAN2": 1, "TRAFO": 1}
```

(importar `replace` de `dataclasses` se ainda não importado no arquivo)

Em `tests/test_ui_tela_revisao.py`:

```python
def test_aba_mostra_contador_e_check(qtbot):
    from dataclasses import replace
    regs = [_rec_sheet("SAN2:1", "M", "A"), _rec_sheet("TRAFO:1", "M", "B")]
    regs = [replace(r, status="revisao") for r in regs]  # status explícito
    tela = _tela_carregada(qtbot, regs)
    textos = [tela.abas_sheet.tabText(i) for i in range(tela.abas_sheet.count())]
    assert any("SAN2 · 1" in t for t in textos)
    tela._modelo.definir_sigla(0, "DJF1")  # SAN2 zera pendências
    textos = [tela.abas_sheet.tabText(i) for i in range(tela.abas_sheet.count())]
    assert any("SAN2 ✓" in t for t in textos)


def test_pendentes_mudaram_emitido_ao_aprovar(qtbot):
    tela = _tela_carregada(qtbot, [_rec_sheet("SAN2:1", "M", "A")])
    valores = []
    tela.pendentes_mudaram.connect(valores.append)
    tela._modelo.definir_sigla(0, "DJF1")
    assert valores and valores[-1] == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_modelo_tabela.py tests/test_ui_tela_revisao.py -v -k "pendentes or aba_mostra"`
Expected: FAIL

- [ ] **Step 3: Implement**

1. Em `src/tdt/ui/modelo_tabela.py`, após `sheets_distintas`:

```python
    def pendentes_por_sheet(self) -> dict[str, int]:
        """Sheet -> nº de registros com status "revisao" (sheets sem pendência
        aparecem com 0, para a aba poder mostrar o check)."""
        contagem: dict[str, int] = {}
        for r in self._estado.registros:
            s = sheet_origem(r)
            if not s:
                continue
            contagem.setdefault(s, 0)
            if r.status == "revisao":
                contagem[s] += 1
        return contagem
```

2. Em `src/tdt/ui/tela_revisao.py`:
   - Adicionar `pendentes_mudaram = Signal(int)` ao lado dos outros sinais.
   - Em `_popular_abas_sheet`, ao adicionar cada aba de sheet, guardar o nome:

```python
        for sheet in self._modelo.sheets_distintas():
            i = self.abas_sheet.addTab(sheet)
            self.abas_sheet.setTabData(i, sheet)
```

   - Substituir `_trocar_aba_sheet`:

```python
    def _trocar_aba_sheet(self, indice: int) -> None:
        nome = None if indice <= 0 else self.abas_sheet.tabData(indice)
        self._proxy.set_sheet(nome)
```

   - Adicionar:

```python
    def _rotulo_aba(self, nome: str, pendentes: int) -> str:
        return f"{nome} ✓" if pendentes == 0 else f"{nome} · {pendentes}"

    def _atualizar_abas_sheet(self) -> None:
        if not hasattr(self, "_modelo"):
            return
        contagem = self._modelo.pendentes_por_sheet()
        total = sum(contagem.values())
        self.abas_sheet.setTabText(0, self._rotulo_aba("Tudo", total))
        for i in range(1, self.abas_sheet.count()):
            sheet = self.abas_sheet.tabData(i)
            self.abas_sheet.setTabText(
                i, self._rotulo_aba(sheet, contagem.get(sheet, 0)))
        self.pendentes_mudaram.emit(total)
```

   - Em `carregar()`, após `self.tabela.setModel(self._proxy)`:

```python
        self._modelo.dataChanged.connect(lambda *_: self._atualizar_abas_sheet())
        self._modelo.rowsInserted.connect(lambda *_: self._atualizar_abas_sheet())
        self._modelo.rowsRemoved.connect(lambda *_: self._atualizar_abas_sheet())
        self._atualizar_abas_sheet()
```

   - Em `refresh()` (Task 5), adicionar `self._atualizar_abas_sheet()` no fim.
3. Em `src/tdt/ui/app.py`, junto das outras conexões:

```python
        self.tela_revisao.pendentes_mudaram.connect(
            lambda n: self.sidebar.atualizar_badge("revisao", n))
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_ui_modelo_tabela.py tests/test_ui_tela_revisao.py tests/test_ui_app.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py src/tdt/ui/tela_revisao.py src/tdt/ui/app.py tests/test_ui_modelo_tabela.py tests/test_ui_tela_revisao.py
git commit -m "feat(ui): abas por sheet com contador de pendentes + badge sidebar (SP-UI-3)"
```

### Task 12: Preset de colunas, menu Colunas, splitter e persistência

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py`
- Modify: `src/tdt/ui/modelo_tabela.py` (header `✎`)
- Test: `tests/test_ui_tela_revisao.py`

**Interfaces:**
- Produces:
  - `_COLUNAS_PADRAO` (8 colunas visíveis por default) em `tela_revisao.py`.
  - Persistência em `QSettings("tdt", "ui")`: chaves `revisao_header_state` e
    `revisao_splitter_state` (salvas no `hideEvent`, restauradas no `carregar`).
  - Header das colunas editáveis com sufixo `" ✎"` (via `ModeloSinais.headerData`).
  - `TelaRevisao.splitter: QSplitter` substitui a largura fixa do painel.

- [ ] **Step 1: Write the failing tests (adicionar em `tests/test_ui_tela_revisao.py`)**

```python
from PySide6.QtCore import QSettings


def _isolar_qsettings(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "tdt.ui.tela_revisao.QSettings",
        lambda *a, **k: QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat))


def test_preset_esconde_colunas_extras(qtbot, monkeypatch, tmp_path):
    _isolar_qsettings(monkeypatch, tmp_path)
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    assert tela.tabela.isColumnHidden(ModeloSinais.COLUNAS.index("Tokens"))
    assert not tela.tabela.isColumnHidden(ModeloSinais.COLUNAS.index("Sinal"))
    assert not tela.tabela.isColumnHidden(ModeloSinais.COLUNAS.index("Motivo"))


def test_header_marca_colunas_editaveis(qtbot):
    from PySide6.QtCore import Qt
    from tdt.ui.estado import AppState
    st = AppState()
    st.registros = [_rec("1", "SE1", "A")]
    modelo = ModeloSinais(st)
    col_sinal = ModeloSinais.COLUNAS.index("Sinal")
    assert "✎" in modelo.headerData(col_sinal, Qt.Horizontal, Qt.DisplayRole)
    col_status = ModeloSinais.COLUNAS.index("Status")
    assert "✎" not in modelo.headerData(col_status, Qt.Horizontal, Qt.DisplayRole)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_revisao.py -v -k "preset or editaveis"`
Expected: FAIL

- [ ] **Step 3: Implement**

1. Em `src/tdt/ui/modelo_tabela.py`, substituir `headerData`:

```python
    def headerData(self, secao, orientacao, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientacao == Qt.Horizontal:
            nome = COLUNAS[secao]
            return f"{nome} ✎" if nome in _EDITAVEIS else nome
        return None
```

2. Em `src/tdt/ui/tela_revisao.py`:
   - Imports: `QSettings` (QtCore), `QSplitter`, `QMenu` (QtWidgets).
   - Constante no nível do módulo:

```python
_COLUNAS_PADRAO = frozenset({
    "Sinal", "Confiança", "Status", "Motivo", "Descr. bruta",
    "Descr. ADMS", "Módulo", "Endereço",
})
```

   - No `__init__`, trocar `cofre.setFixedWidth(280)` por
     `cofre.setMinimumWidth(220)` e substituir o bloco
     `corpo = QHBoxLayout(); corpo.addWidget(cofre); corpo.addWidget(self.tabela, 1)`
     + `raiz.addLayout(corpo, 1)` por:

```python
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(cofre)
        self.splitter.addWidget(self.tabela)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([280, 920])
```

     e `raiz.addWidget(self.splitter, 1)`.
   - Na `barra_filtro` (antes do `addStretch`):

```python
        self.btn_colunas = QPushButton("Colunas ▾")
        barra_filtro.addWidget(self.btn_colunas)
```

   - Em `carregar()`, no fim:

```python
        settings = QSettings("tdt", "ui")
        estado_header = settings.value("revisao_header_state")
        header = self.tabela.horizontalHeader()
        if estado_header is not None and header.count() == len(ModeloSinais.COLUNAS):
            header.restoreState(estado_header)
        else:
            for i, nome in enumerate(ModeloSinais.COLUNAS):
                self.tabela.setColumnHidden(i, nome not in _COLUNAS_PADRAO)
        estado_splitter = settings.value("revisao_splitter_state")
        if estado_splitter is not None:
            self.splitter.restoreState(estado_splitter)
        self._montar_menu_colunas()
```

   - Métodos novos:

```python
    def _montar_menu_colunas(self) -> None:
        menu = QMenu(self.btn_colunas)
        for i, nome in enumerate(ModeloSinais.COLUNAS):
            acao = menu.addAction(nome)
            acao.setCheckable(True)
            acao.setChecked(not self.tabela.isColumnHidden(i))
            acao.toggled.connect(
                lambda visivel, c=i: self.tabela.setColumnHidden(c, not visivel))
        self.btn_colunas.setMenu(menu)

    def hideEvent(self, event):
        if hasattr(self, "_proxy"):
            settings = QSettings("tdt", "ui")
            settings.setValue(
                "revisao_header_state", self.tabela.horizontalHeader().saveState())
            settings.setValue("revisao_splitter_state", self.splitter.saveState())
        super().hideEvent(event)
```

- [ ] **Step 4: Run tests + suíte completa**

Run: `python -m pytest tests/test_ui_tela_revisao.py -v` → PASS
Run: `python -m pytest tests -k "test_ui" -q` → PASS (testes que comparavam
`headerData` com o nome puro da coluna precisam aceitar o sufixo `✎` nas
colunas editáveis)

- [ ] **Step 5: Verificação visual**

Run: `python -m tdt.ui_main` → rodar um input pequeno, conferir: 8 colunas
visíveis, menu "Colunas ▾" alterna, splitter arrasta, fechar/reabrir preserva.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/tela_revisao.py src/tdt/ui/modelo_tabela.py tests/test_ui_tela_revisao.py
git commit -m "feat(ui): preset de colunas, menu Colunas, splitter e persistencia (SP-UI-3)"
```

---

## Fase 4 — SP-UI-4: Geração + Análise clicável + Config humana

### Task 13: Função pura `enderecos_duplicados`

**Files:**
- Create: `src/tdt/ui/tela_geracao.py` (só a função nesta task; a classe vem na Task 14)
- Test: `tests/test_ui_tela_geracao.py` (novo)

**Interfaces:**
- Produces: `enderecos_duplicados(registros) -> dict[tuple[str, int], list[str]]`
  — chave `("in"|"out", indice)`, valor = ids dos registros que repetem;
  só entradas com 2+ ids.

- [ ] **Step 1: Write the failing tests**

Criar `tests/test_ui_tela_geracao.py`:

```python
import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.tela_geracao import enderecos_duplicados

pytest.importorskip("PySide6")


def _rec(id_, indices=(1,), indices_saida=(), status="revisao"):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", indices, indices_saida),
        descricoes=Descricoes("d", "D"), status=status,
    )


def test_duplicata_de_input_detectada():
    regs = [_rec("a", indices=(14,)), _rec("b", indices=(14,)), _rec("c", indices=(2,))]
    assert enderecos_duplicados(regs) == {("in", 14): ["a", "b"]}


def test_input_e_output_iguais_nao_e_duplicata():
    regs = [_rec("a", indices=(14,)), _rec("b", indices=(), indices_saida=(14,))]
    assert enderecos_duplicados(regs) == {}


def test_sem_duplicatas_dict_vazio():
    assert enderecos_duplicados([_rec("a", indices=(1,))]) == {}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_geracao.py -v`
Expected: FAIL com `ModuleNotFoundError: tdt.ui.tela_geracao`

- [ ] **Step 3: Implement**

Criar `src/tdt/ui/tela_geracao.py`:

```python
"""Tela Geração (etapa 3): resumo, avisos acionáveis, gera TDT + auditoria.

ponytail: carregar() reconstrói tudo do zero a cada navegação; sem cache.
"""

from __future__ import annotations


def enderecos_duplicados(registros) -> dict[tuple[str, int], list[str]]:
    """(direcao, indice) -> ids dos registros que repetem o índice.

    "in" cobre enderecamento.indices; "out" cobre indices_saida. Direções
    não se misturam (input 14 + output 14 não é duplicata).
    """
    por_chave: dict[tuple[str, int], list[str]] = {}
    for r in registros:
        for i in r.enderecamento.indices:
            por_chave.setdefault(("in", i), []).append(r.id)
        for i in r.enderecamento.indices_saida:
            por_chave.setdefault(("out", i), []).append(r.id)
    return {k: v for k, v in por_chave.items() if len(v) > 1}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_tela_geracao.py -v`
Expected: PASS (3 testes)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tela_geracao.py tests/test_ui_tela_geracao.py
git commit -m "feat(ui): deteccao de enderecos duplicados por direcao (SP-UI-4)"
```

### Task 14: TelaGeracao completa + integração no MainWindow

**Files:**
- Modify: `src/tdt/ui/tela_geracao.py` (adicionar a classe)
- Modify: `src/tdt/ui/app.py` (trocar placeholder, conectar sinais)
- Modify: `src/tdt/ui/tela_revisao.py` (remover `_gerar` e o botão "Gerar TDT…")
- Test: `tests/test_ui_tela_geracao.py`, `tests/test_ui_app.py`

**Interfaces:**
- Consumes: `TelaRevisao.mostrar_pendentes()` (Task 8),
  `TelaRevisao.filtrar_endereco(texto)` (Task 9),
  `pipeline.gerar_tdt(registros, template, lp, subestacao=..., aliases=...)`,
  `gerar_relatorio_revisao(registros, revisao, output, diagnostico=...)`
  (assinaturas idênticas às usadas hoje em `tela_revisao._gerar`).
- Produces:
  - `TelaGeracao(estado: AppState)` com `carregar()`, sinais
    `rever_pendentes = Signal()` e `rever_duplicados = Signal(list)`.
  - `MainWindow._navegar("geracao")` chama `tela_geracao.carregar()` antes de exibir.

- [ ] **Step 1: Write the failing tests**

Adicionar em `tests/test_ui_tela_geracao.py`:

```python
from tdt.ui.estado import AppState
from tdt.ui.tela_geracao import TelaGeracao


def _tela(qtbot, registros):
    estado = AppState()
    estado.registros = registros
    estado.subestacao = "SAN2"
    tela = TelaGeracao(estado)
    qtbot.addWidget(tela)
    tela.carregar()
    return tela


def test_carregar_preenche_resumo(qtbot):
    tela = _tela(qtbot, [
        _rec("a", status="decidido"), _rec("b", indices=(2,), status="revisao"),
    ])
    assert tela._cards["total"].text() == "2"
    assert tela._cards["decididos"].text() == "1"
    assert tela._cards["pendentes"].text() == "1"
    assert "SAN2" in tela.lbl_titulo.text()


def test_gerar_com_pendentes_pergunta_e_respeita_nao(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    tela = _tela(qtbot, [_rec("a", status="revisao")])
    tela._estado.lista_padrao = object()  # truthy; não chega a ser usado
    tela._estado.paths.update({"template": "t.xlsx", "output": "out"})
    monkeypatch.setattr(
        "tdt.ui.tela_geracao.QMessageBox.question",
        lambda *a, **k: QMessageBox.StandardButton.No)
    chamado = {}
    monkeypatch.setattr(
        "tdt.ui.tela_geracao.pipeline.gerar_tdt",
        lambda *a, **k: chamado.setdefault("gerou", True))
    tela._gerar()
    assert "gerou" not in chamado


def test_aviso_pendentes_emite_rever(qtbot):
    tela = _tela(qtbot, [_rec("a", status="revisao")])
    recebido = []
    tela.rever_pendentes.connect(lambda: recebido.append(True))
    tela.rever_pendentes.emit()
    assert recebido
```

Adicionar em `tests/test_ui_app.py`:

```python
def test_navegar_para_geracao_carrega_resumo(qtbot):
    win = _win(qtbot, _estado_com_resultado())
    win._navegar("geracao")
    assert win.tela_geracao._cards["total"].text() == "2"


def test_rever_pendentes_volta_para_revisao_filtrada(qtbot):
    win = _win(qtbot, _estado_com_resultado())
    win.tela_inicial.executou.emit()
    win._navegar("geracao")
    win.tela_geracao.rever_pendentes.emit()
    assert win.stack.currentIndex() == 1
    assert win.tela_revisao._proxy._status_visivel == "revisao"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_geracao.py tests/test_ui_app.py -v`
Expected: FAIL (`TelaGeracao` não existe)

- [ ] **Step 3: Implement — adicionar a classe em `src/tdt/ui/tela_geracao.py`**

Abaixo de `enderecos_duplicados`, adicionar (com os imports novos no topo):

```python
import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from tdt import pipeline
from tdt.relatorio_revisao import gerar_relatorio_revisao
from tdt.ui.estado import AppState


class TelaGeracao(QWidget):
    rever_pendentes = Signal()
    rever_duplicados = Signal(list)

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado

        self.lbl_titulo = QLabel("Geração")

        self._cards: dict[str, QLabel] = {}
        grid = QGridLayout()
        for i, (chave, nome) in enumerate([
            ("total", "Total"), ("decididos", "Decididos"),
            ("pendentes", "Pendentes"), ("taxa", "Taxa de decisão"),
        ]):
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet("font-size: 18pt; font-weight: bold;")
            grid.addWidget(QLabel(nome), 0, i, Qt.AlignCenter)
            grid.addWidget(lbl_val, 1, i, Qt.AlignCenter)
            self._cards[chave] = lbl_val
        grupo_resumo = QGroupBox("Resumo")
        grupo_resumo.setLayout(grid)

        self._avisos_box = QVBoxLayout()
        grupo_avisos = QGroupBox("Avisos")
        grupo_avisos.setLayout(self._avisos_box)

        self.lbl_saida = QLabel("")
        self.lbl_saida.setWordWrap(True)
        btn_trocar = QPushButton("Trocar pasta…")
        btn_trocar.clicked.connect(self._trocar_saida)
        linha_saida = QHBoxLayout()
        linha_saida.addWidget(self.lbl_saida, 1)
        linha_saida.addWidget(btn_trocar)
        grupo_saida = QGroupBox("Arquivos de saída")
        grupo_saida.setLayout(linha_saida)

        self.btn_gerar = QPushButton("Gerar TDT")
        self.btn_gerar.setProperty("acao", "principal")
        self.btn_gerar.clicked.connect(self._gerar)
        self.btn_abrir_pasta = QPushButton("Abrir pasta")
        self.btn_abrir_pasta.clicked.connect(self._abrir_pasta)
        self.btn_abrir_pasta.setVisible(False)

        self.lbl_resultado = QLabel("")
        self.lbl_resultado.setProperty("nivel", "ok")
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setVisible(False)

        raiz = QVBoxLayout(self)
        raiz.addWidget(self.lbl_titulo)
        raiz.addWidget(grupo_resumo)
        raiz.addWidget(grupo_avisos)
        raiz.addWidget(grupo_saida)
        linha_gerar = QHBoxLayout()
        linha_gerar.addWidget(self.btn_gerar)
        linha_gerar.addWidget(self.btn_abrir_pasta)
        linha_gerar.addStretch()
        raiz.addLayout(linha_gerar)
        raiz.addWidget(self.lbl_resultado)
        raiz.addStretch()

    def carregar(self) -> None:
        regs = self._estado.registros
        total = len(regs)
        pendentes = sum(1 for r in regs if r.status == "revisao")
        decididos = sum(1 for r in regs if r.status == "decidido")
        taxa = f"{decididos / total * 100:.0f}%" if total else "—"
        self.lbl_titulo.setText(f"Geração — {self._estado.subestacao or '—'}")
        self._cards["total"].setText(str(total))
        self._cards["decididos"].setText(str(decididos))
        self._cards["pendentes"].setText(str(pendentes))
        self._cards["taxa"].setText(taxa)
        pend_lbl = self._cards["pendentes"]
        pend_lbl.setProperty("nivel", "aviso" if pendentes else "ok")
        pend_lbl.style().unpolish(pend_lbl)
        pend_lbl.style().polish(pend_lbl)
        self._montar_avisos(pendentes)
        out = self._estado.paths.get("output", "")
        self.lbl_saida.setText(
            f"TDT.xlsx · Auditoria_Revisao.xlsx → {out or '—'}")
        self.lbl_resultado.setVisible(False)
        self.btn_abrir_pasta.setVisible(False)

    def _montar_avisos(self, pendentes: int) -> None:
        while self._avisos_box.count():
            w = self._avisos_box.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        dups = enderecos_duplicados(self._estado.registros)
        if pendentes:
            self._avisos_box.addWidget(self._aviso(
                "aviso",
                f"{pendentes} sinais pendentes serão exportados com o melhor "
                "candidato atual",
                "Rever pendentes →", self.rever_pendentes.emit))
        if dups:
            indices = sorted({i for (_d, i) in dups})
            resumo = "; ".join(str(i) for i in indices[:5])
            self._avisos_box.addWidget(self._aviso(
                "erro",
                f"{len(dups)} endereços duplicados (índices {resumo})",
                "Rever duplicados →",
                lambda: self.rever_duplicados.emit(indices)))
        if not pendentes and not dups:
            self._avisos_box.addWidget(self._aviso(
                "ok", "Tudo pronto — sem pendências nem endereços duplicados",
                None, None))

    def _aviso(self, nivel: str, texto: str, rotulo_botao, slot) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(texto)
        lbl.setProperty("nivel", nivel)
        lbl.setWordWrap(True)
        lay.addWidget(lbl, 1)
        if rotulo_botao:
            btn = QPushButton(rotulo_botao)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
        return w

    def _trocar_saida(self) -> None:
        atual = self._estado.paths.get("output", "")
        caminho = QFileDialog.getExistingDirectory(
            self, "Pasta de saída", dir=atual)
        if caminho:
            self._estado.paths["output"] = caminho
            self.carregar()

    def _confirmar(self, titulo: str, texto: str) -> bool:
        resp = QMessageBox.question(self, titulo, texto)
        return resp == QMessageBox.StandardButton.Yes

    def _gerar(self) -> None:
        lp = self._estado.lista_padrao
        template = self._estado.paths.get("template", "")
        output = self._estado.paths.get("output", "")
        if not lp or not template or not output:
            QMessageBox.warning(
                self, "Erro", "Lista padrão, template e output são obrigatórios")
            return
        pendentes = sum(
            1 for r in self._estado.registros if r.status == "revisao")
        if pendentes and not self._confirmar(
                "Pendências", f"Gerar com {pendentes} sinais ainda pendentes?"):
            return
        out_path = Path(output) / "TDT.xlsx"
        if out_path.exists() and not self._confirmar(
                "Sobrescrever", f"{out_path} já existe. Sobrescrever?"):
            return
        try:
            wb = pipeline.gerar_tdt(
                self._estado.registros, template, lp,
                subestacao=self._estado.subestacao,
                aliases=self._estado.aliases,
            )
            wb.save(str(out_path))
            revisao = (self._estado.resultado.revisao
                       if self._estado.resultado else ())
            diag = (self._estado.resultado.diagnostico
                    if self._estado.resultado else {})
            gerar_relatorio_revisao(
                self._estado.registros, revisao, output, diagnostico=diag)
            self.lbl_resultado.setText(
                f"TDT gerado:\n{out_path}\n"
                f"{Path(output) / 'Auditoria_Revisao.xlsx'}")
            self.lbl_resultado.setVisible(True)
            self.btn_abrir_pasta.setVisible(True)
        except Exception as e:  # ponytail: erro vira dialogo; sem retry
            QMessageBox.critical(self, "Erro", f"Falha ao gerar TDT: {e}")

    def _abrir_pasta(self) -> None:
        output = self._estado.paths.get("output", "")
        if output and hasattr(os, "startfile"):
            os.startfile(output)
```

Nota: no teste `test_gerar_com_pendentes_pergunta_e_respeita_nao`, `wb.save`
nunca roda porque a recusa acontece antes.

- [ ] **Step 4: Integrar no `src/tdt/ui/app.py`**

1. Import: `from tdt.ui.tela_geracao import TelaGeracao`.
2. Trocar `self.tela_geracao = self._criar_tela_geracao()` por
   `self.tela_geracao = TelaGeracao(estado)` e **deletar** o método
   `_criar_tela_geracao` (e o import de `QLabel` se ficar sem uso).
3. Junto das outras conexões:

```python
        self.tela_geracao.rever_pendentes.connect(self._rever_pendentes)
        self.tela_geracao.rever_duplicados.connect(self._rever_duplicados)
```

4. Substituir `_navegar` e adicionar os handlers:

```python
    def _navegar(self, chave: str) -> None:
        if chave == "geracao":
            self.tela_geracao.carregar()
        self.stack.setCurrentIndex(_INDICE[chave])
        self.sidebar.definir_ativa(chave)

    def _rever_pendentes(self) -> None:
        self.tela_revisao.mostrar_pendentes()
        self._navegar("revisao")

    def _rever_duplicados(self, indices: list) -> None:
        if indices:
            self.tela_revisao.filtrar_endereco(str(indices[0]))
        self._navegar("revisao")
```

- [ ] **Step 5: Remover a geração da TelaRevisao**

Em `src/tdt/ui/tela_revisao.py`: deletar o método `_gerar`, o botão
`btn_gerar` (criação e `topo.addWidget`), e os imports que ficarem órfãos
(`from tdt import pipeline`, `from tdt.relatorio_revisao import
gerar_relatorio_revisao`). Rodar `python -m pyflakes src/tdt/ui/tela_revisao.py`
se disponível, senão conferir com o pytest.

- [ ] **Step 6: Run tests**

Run: `python -m pytest tests/test_ui_tela_geracao.py tests/test_ui_app.py tests/test_ui_tela_revisao.py -v`
Expected: PASS (remover/ajustar qualquer teste da revisão que referencie `_gerar`)

- [ ] **Step 7: Commit**

```bash
git add src/tdt/ui/tela_geracao.py src/tdt/ui/app.py src/tdt/ui/tela_revisao.py tests/test_ui_tela_geracao.py tests/test_ui_app.py tests/test_ui_tela_revisao.py
git commit -m "feat(ui): tela Geracao com resumo, avisos acionaveis e confirmacoes (SP-UI-4)"
```

### Task 15: Análise clicável + ponte para a Revisão

**Files:**
- Modify: `src/tdt/ui/tela_analise.py`
- Modify: `src/tdt/ui/tela_revisao.py` (método `selecionar_por_id`)
- Modify: `src/tdt/ui/app.py` (conectar `rever_sinal`)
- Test: `tests/test_ui_tela_analise.py`

**Interfaces:**
- Produces:
  - `_ProxyStatus.definir_filtro_motivo(motivo: str | None)` (AND com o filtro
    de status; compara com a coluna "Motivo Revisão", índice 9 de
    `modelo_analise.COLUNAS`).
  - sinal `TelaAnalise.rever_sinal = Signal(str)` (id do registro).
  - `TelaRevisao.selecionar_por_id(id_registro: str) -> bool` — limpa o filtro
    de status, seleciona e rola até a linha.

- [ ] **Step 1: Write the failing tests (adicionar em `tests/test_ui_tela_analise.py`)**

Usar os helpers existentes do arquivo para montar `ResultadoPipeline` (mesmo
padrão dos testes atuais) e adicionar:

```python
def test_clicar_card_revisao_filtra_tabela(qtbot):
    tela = _tela_carregada(qtbot)  # helper existente que chama carregar()
    tela._stats_labels["revisao"].clicado.emit()
    assert tela._combo_status.currentText() == "Revisão"


def test_chip_motivo_filtra_e_desmarca_limpa(qtbot):
    tela = _tela_carregada(qtbot)
    chips = [b for b in tela._chips_motivo if b.text().startswith("score_baixo")]
    assert chips, "chip do motivo deveria existir"
    chips[0].setChecked(True)
    chips[0].clicked.emit(True)
    assert tela._proxy._motivo == "score_baixo"
    chips[0].setChecked(False)
    chips[0].clicked.emit(False)
    assert tela._proxy._motivo is None


def test_rever_sinal_emite_id_da_linha_selecionada(qtbot):
    tela = _tela_carregada(qtbot)
    tela._table.selectRow(0)
    recebidos = []
    tela.rever_sinal.connect(recebidos.append)
    tela._btn_rever.click()
    assert len(recebidos) == 1 and isinstance(recebidos[0], str)
```

Nota: se o arquivo não tiver um helper `_tela_carregada`, criar um no padrão
dos testes existentes do arquivo (TelaAnalise + `carregar(resultado)` com ao
menos 1 registro decidido e 1 em revisão com motivo `"score_baixo"`).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_analise.py -v`
Expected: FAIL

- [ ] **Step 3: Implement em `src/tdt/ui/tela_analise.py`**

1. Label clicável (nível do módulo, após os imports):

```python
from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal


class LabelClicavel(QLabel):
    clicado = Signal()

    def __init__(self, texto="", parent=None):
        super().__init__(texto, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        self.clicado.emit()
        super().mousePressEvent(event)
```

2. No `_ProxyStatus`: `self._motivo: str | None = None` no `__init__`;

```python
    def definir_filtro_motivo(self, motivo: str | None) -> None:
        self._motivo = motivo
        self.invalidateFilter()
```

   e em `filterAcceptsRow`, após o filtro de status:

```python
        if self._motivo is not None:
            idx = modelo.index(source_row, COLUNAS.index("Motivo Revisão"),
                               source_parent)
            if modelo.data(idx) != self._motivo:
                return False
```

   (garantir `modelo = self.sourceModel()` disponível nos dois blocos)
3. Nos cards do `__init__`: trocar `label_val = QLabel("—")` por
   `label_val = LabelClicavel("—")` e, após o loop:

```python
        self._stats_labels["total"].clicado.connect(
            lambda: self._combo_status.setCurrentText("Todos"))
        self._stats_labels["decididos"].clicado.connect(
            lambda: self._combo_status.setCurrentText("Decididos"))
        self._stats_labels["revisao"].clicado.connect(
            lambda: self._combo_status.setCurrentText("Revisão"))
```

4. Chips de motivo: no `__init__`, substituir `self._motivos_label = QLabel("—")`
   (e seu `addWidget`) por:

```python
        self._chips_box = QHBoxLayout()
        self._chips_motivo: list[QPushButton] = []
        chips_container = QWidget()
        chips_container.setLayout(self._chips_box)
        stats_grid.addWidget(chips_container, 2, 1, 1, 3)
```

   e em `_atualizar_stats`, substituir o bloco que montava o texto de motivos
   por:

```python
        while self._chips_box.count():
            w = self._chips_box.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        self._chips_motivo = []
        for motivo, n in sorted(motivos.items(), key=lambda x: -x[1]):
            chip = QPushButton(f"{motivo}: {n}")
            chip.setCheckable(True)
            chip.clicked.connect(
                lambda marcado, m=motivo: self._filtrar_motivo(m, marcado))
            self._chips_box.addWidget(chip)
            self._chips_motivo.append(chip)
        self._chips_box.addStretch()
```

   com o slot:

```python
    def _filtrar_motivo(self, motivo: str, marcado: bool) -> None:
        for chip in self._chips_motivo:
            if not chip.text().startswith(f"{motivo}:"):
                chip.setChecked(False)
        self._proxy.definir_filtro_motivo(motivo if marcado else None)
```

5. Ponte: adicionar `rever_sinal = Signal(str)` à classe; na `filter_layout`
   (antes do `addStretch`):

```python
        self._btn_rever = QPushButton("Rever na Revisão →")
        self._btn_rever.clicked.connect(self._emitir_rever)
        filter_layout.addWidget(self._btn_rever)
```

   com:

```python
    def _emitir_rever(self) -> None:
        idx = self._table.selectionModel().currentIndex()
        if not idx.isValid():
            return
        id_ = self._proxy.index(idx.row(), 0).data()  # coluna 0 = "ID"
        if id_:
            self.rever_sinal.emit(str(id_))
```

   Imports extras de QtWidgets: `QWidget` (se faltar).

- [ ] **Step 4: `TelaRevisao.selecionar_por_id` (em `src/tdt/ui/tela_revisao.py`)**

```python
    def selecionar_por_id(self, id_registro: str) -> bool:
        """Seleciona e rola até o registro; limpa o filtro de status antes."""
        if not hasattr(self, "_proxy"):
            return False
        self.grupo_status.button(0).setChecked(True)
        self._filtrar_status_id(0)
        for linha, r in enumerate(self._estado.registros):
            if r.id == id_registro:
                idx_proxy = self._proxy.mapFromSource(self._modelo.index(linha, 0))
                if idx_proxy.isValid():
                    self.tabela.selectRow(idx_proxy.row())
                    self.tabela.scrollTo(idx_proxy)
                    return True
        return False
```

E em `src/tdt/ui/app.py`, junto das conexões:

```python
        self.tela_analise.rever_sinal.connect(self._rever_sinal)
```

com:

```python
    def _rever_sinal(self, id_registro: str) -> None:
        self._navegar("revisao")
        self.tela_revisao.selecionar_por_id(id_registro)
```

- [ ] **Step 5: Run tests**

Run: `python -m pytest tests/test_ui_tela_analise.py tests/test_ui_app.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/tela_analise.py src/tdt/ui/tela_revisao.py src/tdt/ui/app.py tests/test_ui_tela_analise.py
git commit -m "feat(ui): analise com cards/chips clicaveis e ponte para revisao (SP-UI-4)"
```

### Task 16: Config com labels humanos, aviso de pesos e restaurar padrões

**Files:**
- Modify: `src/tdt/ui/tela_config.py`
- Test: `tests/test_ui_tela_config.py` (novo)

**Interfaces:**
- Consumes: QSS `QLabel[tipo="tecnico"]` (Task 2), `Config()` defaults.
- Produces: mesmos atributos de widget (`spin_pct`, `spin_gap`, `spin_topn`,
  `spin_tfidf`, `spin_vet`, `spin_fuzzy`, `combo_modelo`, `spin_k`) —
  `recarregar`/`aplicar` inalterados; novos `lbl_aviso_pesos` e
  `_restaurar_padroes()`.

- [ ] **Step 1: Write the failing tests**

Criar `tests/test_ui_tela_config.py`:

```python
import pytest

from tdt.ui.estado import AppState
from tdt.ui.tela_config import TelaConfig

pytest.importorskip("PySide6")


def _tela(qtbot, tmp_path):
    tela = TelaConfig(AppState(), config_path=str(tmp_path / "config.toml"))
    qtbot.addWidget(tela)
    return tela


def test_aviso_pesos_aparece_quando_soma_diferente_de_1(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    tela.spin_tfidf.setValue(0.5)
    tela.spin_vet.setValue(0.3)
    tela.spin_fuzzy.setValue(0.1)
    assert tela.lbl_aviso_pesos.isVisibleTo(tela)
    assert "0.900" in tela.lbl_aviso_pesos.text()
    tela.spin_fuzzy.setValue(0.2)
    assert not tela.lbl_aviso_pesos.isVisibleTo(tela)


def test_restaurar_padroes_repoe_defaults_sem_salvar(qtbot, tmp_path):
    from tdt.config import Config
    tela = _tela(qtbot, tmp_path)
    tela.spin_pct.setValue(0.99)
    tela._restaurar_padroes()
    assert tela.spin_pct.value() == Config().threshold_pct


def test_labels_tem_tooltip_de_efeito(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    assert tela.spin_pct.toolTip() != ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_tela_config.py -v`
Expected: FAIL (`lbl_aviso_pesos` não existe)

- [ ] **Step 3: Implement em `src/tdt/ui/tela_config.py`**

1. Imports extras: `from PySide6.QtWidgets import QGroupBox, QWidget` (somar
   aos existentes) e `from tdt.config import Config`.
2. Tabela de textos no nível do módulo (aplicar exatamente — vem da spec):

```python
_TOOLTIPS = {
    "threshold_pct": ("Score mínimo para decidir sozinho",
                      "Candidato nº 1 precisa de pelo menos este score. "
                      "Maior = decide mais sozinho, mais risco de erro."),
    "threshold_gap": ("Vantagem mínima sobre o 2º",
                      "Diferença mínima entre 1º e 2º candidato. Maior = só "
                      "decide quando a liderança é clara."),
    "top_n_pct": ("Corte dos candidatos exibidos",
                  "Score mínimo (relativo ao 1º) para um candidato aparecer "
                  "na lista da revisão."),
    "peso_tfidf": ("Peso do TF-IDF/BM25",
                   "Peso do método lexical na mescla dos scores."),
    "peso_vetorial": ("Peso do embedding",
                      "Peso do método semântico (vetorial) na mescla."),
    "peso_fuzzy": ("Peso do fuzzy",
                   "Peso da similaridade de caracteres na mescla."),
    "modelo_embedding": ("Modelo de embedding",
                         "Modelo sentence-transformers usado no método "
                         "vetorial. Trocar exige novo download/cache."),
    "k_vizinhos": ("Candidatos por sinal (k)",
                   "Quantos vizinhos o índice vetorial devolve por sinal."),
}


def _rotulo(chave: str) -> QWidget:
    humano, tooltip = _TOOLTIPS[chave]
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    lbl = QLabel(humano)
    tec = QLabel(chave)
    tec.setProperty("tipo", "tecnico")
    v.addWidget(lbl)
    v.addWidget(tec)
    w.setToolTip(tooltip)
    return w
```

3. No `__init__`, reorganizar o form em 4 `QGroupBox` — cada grupo com um
   `QFormLayout` próprio:
   - **Caminhos padrão**: mover as 4 linhas de `_setup_paths` (método mantido,
     só passa a receber o QFormLayout do grupo).
   - **Decisão automática**: `spin_pct`, `spin_gap`, `spin_topn` com
     `form.addRow(_rotulo("threshold_pct"), self.spin_pct)` etc.
   - **Pesos do ensemble**: `spin_tfidf`, `spin_vet`, `spin_fuzzy` + no fim:

```python
        self.lbl_aviso_pesos = QLabel("")
        self.lbl_aviso_pesos.setProperty("nivel", "aviso")
        self.lbl_aviso_pesos.setVisible(False)
        form_pesos.addRow(self.lbl_aviso_pesos)
        for spin in (self.spin_tfidf, self.spin_vet, self.spin_fuzzy):
            spin.valueChanged.connect(self._atualizar_aviso_pesos)
```

   - **Modelo semântico**: `combo_modelo`, `spin_k`.
   - Para cada spin/combo, também setar o tooltip no próprio widget:
     `self.spin_pct.setToolTip(_TOOLTIPS["threshold_pct"][1])` (idem os demais).
   - Botões no rodapé: `Salvar` (principal, existente), `Restaurar padrões`
     (novo, conecta `_restaurar_padroes`), `Voltar` (existente).
4. Métodos novos:

```python
    def _atualizar_aviso_pesos(self, *_args) -> None:
        soma = (self.spin_tfidf.value() + self.spin_vet.value()
                + self.spin_fuzzy.value())
        divergente = abs(soma - 1.0) > 0.001
        if divergente:
            self.lbl_aviso_pesos.setText(
                f"Os pesos somam {soma:.3f} — o esperado é 1.0")
        self.lbl_aviso_pesos.setVisible(divergente)

    def _restaurar_padroes(self) -> None:
        c = Config()
        self.spin_pct.setValue(c.threshold_pct)
        self.spin_gap.setValue(c.threshold_gap)
        self.spin_topn.setValue(c.top_n_pct)
        self.spin_tfidf.setValue(c.peso_tfidf)
        self.spin_vet.setValue(c.peso_vetorial)
        self.spin_fuzzy.setValue(c.peso_fuzzy)
        indice = self.combo_modelo.findText(c.modelo_embedding)
        self.combo_modelo.setCurrentIndex(indice if indice >= 0 else 0)
        self.spin_k.setValue(c.k_vizinhos)
```

   (não chama `aplicar` — nada é salvo até o usuário clicar Salvar)
5. Chamar `self._atualizar_aviso_pesos()` no fim de `recarregar()`.

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_ui_tela_config.py -v`
Expected: PASS

- [ ] **Step 5: Run suíte completa + verificação visual**

Run: `python -m pytest tests -k "test_ui" -q` → PASS
Run: `python -m tdt.ui_main` → Config em 4 grupos, tooltips presentes, aviso
âmbar com pesos 0.5/0.3/0.1. Fechar.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/tela_config.py tests/test_ui_tela_config.py
git commit -m "feat(ui): config com labels humanos, aviso de pesos e restaurar padroes (SP-UI-4)"
```

---

### Task 17: DOX — atualizar `src/tdt/ui/AGENTS.md`

**Files:**
- Modify: `src/tdt/ui/AGENTS.md`

- [ ] **Step 1: Aplicar as edições**

1. Em **Ownership**, substituir a linha de `app.py` por:

```markdown
- `app.py`: `MainWindow(QMainWindow)` — Sidebar retrátil + QStackedWidget (0 Entrada, 1 Revisão, 2 Config, 3 Análise, 4 Geração); navegação por chave via `_navegar`; undo global Ctrl+Z; gating de etapas pós-execução.
```

2. Adicionar ao **Ownership** (ordem alfabética aproximada):

```markdown
- `sidebar.py`: `Sidebar(QWidget)` — navegação retrátil (48/200px, persiste em QSettings("tdt","ui")); estados por item (disponivel/bloqueada/completa), badge de pendentes, contexto no rodapé.
- `tela_geracao.py`: `TelaGeracao(QWidget)` — etapa 3: resumo, avisos acionáveis (pendentes, endereços duplicados), confirmações e geração do TDT.xlsx + Auditoria_Revisao.xlsx (movida da TelaRevisao).
```

3. Em **Local Contracts**:
   - Substituir a frase "nenhum snapshot de undo é criado (mesma lacuna do
     `definir_sigla`)" por: "snapshot de undo é criado DENTRO de
     `definir_sigla`/`_editar_nested` (lacuna fechada em SP-UI-1);
     `definir_sigla(..., snapshot=False)` existe para lotes (aprovação
     automática)."
   - Substituir a linha do `ProxyRevisao` por:

```markdown
- `ProxyRevisao` herda `QSortFilterProxyModel`; filtra por coluna (texto "contém" + valores estilo Excel, AND) com marcador " ▼*" no header; `set_status_visivel(None|"revisao"|"decidido")` substitui o antigo esconder_decididos; `filtros_ativos()`/`limpar_filtros()` alimentam o chip "limpar todos".
```

   - Substituir a linha "Navegação: ..." por:

```markdown
- Navegação: Sidebar (chaves entrada/revisao/config/analise/geracao) + QStackedWidget de 5 telas; Revisão/Geração/Análise bloqueadas até o primeiro `executou`. Preferências de UI (sidebar, colunas, splitter) em QSettings("tdt","ui").
```

- [ ] **Step 2: Commit**

```bash
git add src/tdt/ui/AGENTS.md
git commit -m "docs(ui): AGENTS.md reflete shell sidebar, TelaGeracao e contratos novos (SP-UI)"
```

---

## Verificação final (após a última task)

- [ ] `python -m pytest tests -q` — suíte inteira verde.
- [ ] `python -m tdt.ui_main` — fluxo completo manual: Entrada (cards ok →
  Executar análise) → Revisão (Enter aprova e pula; filtro por header;
  Ctrl+Z) → Geração (avisos, gerar, abrir pasta) → Análise (cards/chips) →
  Config (tooltips/aviso).

