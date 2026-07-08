# SP-UI-CONTRASTE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir texto ilegível nas barras de score da tela de Revisão, restaurar a numeração de linhas sumida na mesma tela, e aumentar o contraste do texto "apagado" do tema grafite.

**Architecture:** Três correções pontuais e independentes em `src/tdt/ui/`: (1) cor de texto condicional por faixa de score em `modelo_tabela.py` + `tela_revisao.py`; (2) fallback ao `super().headerData()` em `ModeloSinais`; (3) troca de um valor de cor em `tema.qss`. Sem novas dependências, sem mudança de layout.

**Tech Stack:** Python 3, PySide6 (Qt widgets/QSS), pytest + pytest-qt (`qtbot`).

## Global Constraints

- Escopo: somente `src/tdt/ui/modelo_tabela.py`, `src/tdt/ui/tela_revisao.py`, `src/tdt/ui/tema.qss` e seus testes em `tests/`.
- Não alterar layout, tamanho de colunas, ou paleta além do valor especificado.
- Seguir padrão de testes existente: `pytest.importorskip("PySide6")` onde aplicável, fixture `qtbot` do pytest-qt.
- Rodar `pytest tests/test_ui_modelo_tabela.py tests/test_ui_tela_revisao.py -v` ao final de cada task tocando esses arquivos.

---

### Task 1: Cor de texto por faixa de score em `modelo_tabela.py`

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py:34-40` (constantes de cor) e após `cor_faixa` (linha 69)
- Test: `tests/test_ui_modelo_tabela.py`

**Interfaces:**
- Produces: `texto_faixa(score: float | None) -> QColor | None` em `tdt.ui.modelo_tabela`, mesmos limiares de `cor_faixa` (≥0.70 alto, ≥0.45 médio, resto baixo, `None` se `score is None`). Constantes `COR_ALTO_TEXTO`, `COR_MEDIO_TEXTO`, `COR_BAIXO_TEXTO` (todas `QColor`).

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_ui_modelo_tabela.py`:

```python
def test_texto_faixa_cores():
    from tdt.ui.modelo_tabela import texto_faixa
    assert texto_faixa(0.9).name() == "#0d2e21"
    assert texto_faixa(0.5).name() == "#2c2005"
    assert texto_faixa(0.1).name() == "#e8ebf2"
    assert texto_faixa(None) is None
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_ui_modelo_tabela.py::test_texto_faixa_cores -v`
Expected: FAIL com `ImportError: cannot import name 'texto_faixa'`

- [ ] **Step 3: Implementar**

Em `src/tdt/ui/modelo_tabela.py`, logo após as constantes existentes (linha 40, após `COR_REVISAO = COR_BAIXO`):

```python
# Cor de texto por faixa — necessária pq o fundo (::chunk da QProgressBar)
# muda de cor conforme a faixa, mas o texto era fixo e ficava ilegível
# sobre verde/âmbar claros.
COR_ALTO_TEXTO = QColor("#0d2e21")
COR_MEDIO_TEXTO = QColor("#2c2005")
COR_BAIXO_TEXTO = QColor("#e8ebf2")
```

E logo após a função `cor_faixa` (após a linha `return COR_BAIXO`, antes de `def _score`):

```python
def texto_faixa(score) -> QColor | None:
    if score is None:
        return None
    if score >= 0.70:
        return COR_ALTO_TEXTO
    if score >= 0.45:
        return COR_MEDIO_TEXTO
    return COR_BAIXO_TEXTO
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `pytest tests/test_ui_modelo_tabela.py::test_texto_faixa_cores -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py tests/test_ui_modelo_tabela.py
git commit -m "feat(ui): adiciona texto_faixa para cor de texto legivel por faixa de score"
```

---

### Task 2: Aplicar `texto_faixa` nas barras de score da tela de Revisão

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py:24` (import) e `:485-497` (`_atualizar_barras`)
- Test: `tests/test_ui_tela_revisao.py`

**Interfaces:**
- Consumes: `texto_faixa(score) -> QColor | None` e `cor_faixa(score) -> QColor | None` de `tdt.ui.modelo_tabela` (Task 1).

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_ui_tela_revisao.py`:

```python
from dataclasses import replace

from tdt.contracts import Diagnostico


def test_barra_score_alto_usa_texto_escuro(qtbot):
    rec = replace(
        _rec("1", "SE1", "A"),
        sigla_sinal="DJF1",
        diagnostico=Diagnostico({"DJF1": {"vetorial": 0.9, "tfidf": 0.9, "fuzzy": 0.9}}),
    )
    tela = _tela_carregada(qtbot, [rec])
    tela.tabela.selectRow(0)
    assert "color: #0d2e21" in tela.barras[0].styleSheet()


def test_barra_score_baixo_mantem_texto_claro(qtbot):
    rec = replace(
        _rec("1", "SE1", "A"),
        sigla_sinal="DJF1",
        diagnostico=Diagnostico({"DJF1": {"vetorial": 0.1, "tfidf": 0.1, "fuzzy": 0.1}}),
    )
    tela = _tela_carregada(qtbot, [rec])
    tela.tabela.selectRow(0)
    assert "color: #e8ebf2" in tela.barras[0].styleSheet()
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_ui_tela_revisao.py::test_barra_score_alto_usa_texto_escuro -v`
Expected: FAIL — `styleSheet()` não contém `color: #0d2e21` (só tem o `background-color` do chunk)

- [ ] **Step 3: Implementar**

Em `src/tdt/ui/tela_revisao.py:24`, trocar:

```python
from tdt.ui.modelo_tabela import ModeloSinais, cor_faixa
```

por:

```python
from tdt.ui.modelo_tabela import ModeloSinais, cor_faixa, texto_faixa
```

Em `_atualizar_barras` (linhas 488-497), trocar o corpo do `for`:

```python
for (_, chave), barra in zip(_METODOS, self.barras):
    v = None
    if diag is not None and sigla is not None:
        v = diag.scores_por_metodo.get(sigla, {}).get(chave)
    pct = int(round((v or 0.0) * 100))
    barra.setValue(pct)
    barra.setFormat(f"{v:.2f}" if v is not None else "—")
    cor = cor_faixa(v)
    cor_texto = texto_faixa(v)
    if cor is not None:
        barra.setStyleSheet(
            f"QProgressBar {{ color: {cor_texto.name()}; }}"
            f"QProgressBar::chunk {{ background-color: {cor.name()}; }}"
        )
    else:
        barra.setStyleSheet("")
```

(o `else` limpa o estilo por-barra quando não há score, deixando a barra cair de volta no `QProgressBar` padrão do `tema.qss` — sem isso, uma barra que teve score numa seleção anterior manteria a cor antiga ao selecionar um registro sem score.)

- [ ] **Step 4: Rodar os testes e confirmar que passam**

Run: `pytest tests/test_ui_tela_revisao.py::test_barra_score_alto_usa_texto_escuro tests/test_ui_tela_revisao.py::test_barra_score_baixo_mantem_texto_claro -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tela_revisao.py tests/test_ui_tela_revisao.py
git commit -m "fix(ui): texto das barras de score fica legivel sobre fundo verde/ambar"
```

---

### Task 3: Restaurar numeração de linhas na tela de Revisão

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py:93-97`
- Test: `tests/test_ui_modelo_tabela.py`

**Interfaces:**
- Nenhuma nova; corrige comportamento de `ModeloSinais.headerData` (já usado pela `tela_revisao.py`).

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao final de `tests/test_ui_modelo_tabela.py`:

```python
def test_header_data_vertical_mostra_numero_da_linha(qtbot):
    m = ModeloSinais(_state(_rec()))
    assert m.headerData(0, Qt.Vertical, Qt.DisplayRole) == 1
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_ui_modelo_tabela.py::test_header_data_vertical_mostra_numero_da_linha -v`
Expected: FAIL — retorna `None` em vez de `1` (Qt retorna int, não string, no fallback padrão)

- [ ] **Step 3: Implementar**

Em `src/tdt/ui/modelo_tabela.py:93-97`, trocar:

```python
    def headerData(self, secao, orientacao, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientacao == Qt.Horizontal:
            nome = COLUNAS[secao]
            return f"{nome} ✎" if nome in _EDITAVEIS else nome
        return None
```

por:

```python
    def headerData(self, secao, orientacao, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientacao == Qt.Horizontal:
            nome = COLUNAS[secao]
            return f"{nome} ✎" if nome in _EDITAVEIS else nome
        return super().headerData(secao, orientacao, role)
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `pytest tests/test_ui_modelo_tabela.py::test_header_data_vertical_mostra_numero_da_linha -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py tests/test_ui_modelo_tabela.py
git commit -m "fix(ui): numeracao de linha volta a aparecer na tela de Revisao"
```

---

### Task 4: Aumentar contraste do texto "apagado" no tema

**Files:**
- Modify: `src/tdt/ui/tema.qss:1-5,34,45,61,72`
- Test: `tests/test_ui_tema.py` (novo arquivo)

**Interfaces:** Nenhuma — mudança de valor de cor em stylesheet, sem API.

**Justificativa numérica (WCAG 2.1, contraste texto normal ≥ 4.5:1):** `#5f6880` sobre o fundo mais claro em que aparece (`#1e2430`) dá razão de contraste ≈ 2.8:1 (falha). `#838aa0` sobre os mesmos fundos (`#14161d`, `#191d26`, `#1e2430`) dá ≈ 4.5–5.3:1 (passa). As demais cores do tema (`#9aa3b5` sobre os painéis, ≈ 5.7–6.6:1) já passam e não são alteradas — mudança fica restrita ao único valor que falhava.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_ui_tema.py`:

```python
from pathlib import Path

_TEMA = Path(__file__).parent.parent / "src" / "tdt" / "ui" / "tema.qss"


def test_texto_apagado_usa_cor_com_contraste_suficiente():
    conteudo = _TEMA.read_text(encoding="utf-8")
    assert "#5f6880" not in conteudo, "cor antiga de baixo contraste ainda presente"
    assert conteudo.count("#838aa0") == 5, "esperado no comentario + 4 regras (tipo=tecnico, disabled, sidebarContexto, bloqueado)"
```

- [ ] **Step 2: Rodar o teste e confirmar que falha**

Run: `pytest tests/test_ui_tema.py -v`
Expected: FAIL — `#5f6880` ainda presente no arquivo

- [ ] **Step 3: Implementar**

Em `src/tdt/ui/tema.qss`, substituir todas as 4 ocorrências de `#5f6880` por `#838aa0`:

Linha 3 (comentário de paleta):
```
   texto #e8ebf2 · secundário #9aa3b5 · apagado #838aa0
```

Linha 34:
```
QLabel[tipo="tecnico"] { color: #838aa0; font-size: 11px; }
```

Linha 45:
```
QPushButton:disabled { background-color: #1e2430; color: #838aa0; }
```

Linha 61:
```
#sidebarContexto { color: #838aa0; font-family: Consolas, monospace; font-size: 11px; }
```

Linha 72:
```
QPushButton[item="bloqueado"] { color: #838aa0; }
```

- [ ] **Step 4: Rodar o teste e confirmar que passa**

Run: `pytest tests/test_ui_tema.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tema.qss tests/test_ui_tema.py
git commit -m "fix(ui): aumenta contraste do texto apagado no tema grafite (WCAG AA)"
```

---

### Task 5: Verificação manual final

**Files:** Nenhum (só execução).

- [ ] **Step 1: Rodar a suíte completa de UI**

Run: `pytest tests/test_ui_modelo_tabela.py tests/test_ui_tela_revisao.py tests/test_ui_tema.py -v`
Expected: todos PASS

- [ ] **Step 2: Abrir a tela de Revisão manualmente e checar**

Run: `python -m tdt.ui.app` (ou o entrypoint atual da aplicação), navegar até a tela de Revisão, selecionar um sinal com score alto/médio/baixo em cada método:
- Confirmar que a coluna de números de linha (à esquerda da tabela) mostra 1, 2, 3...
- Confirmar que o texto dentro das barras de score (verde e âmbar) fica legível.

Não há passo de commit — task de verificação apenas.
