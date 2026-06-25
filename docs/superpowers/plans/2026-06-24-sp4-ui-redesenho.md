# SP4.1 — Redesenho da UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deixar a UI PySide6 mais bonita/limpa (3 telas) e corrigir a revisão, onde candidatos e descrições ADMS não aparecem e a busca/geração de TDT estão quebradas.

**Architecture:** Refino da UI existente (`src/tdt/ui/`), sem reescrever a arquitetura. Correções de bug primeiro (destravam a revisão), depois uma função de busca pura, o modelo de tabela enriquecido, o painel de revisão, o editor inline de célula, e por fim o tema + cards. Lógica testável separada de widget; smoke com pytest-qt.

**Tech Stack:** Python ≥3.11, PySide6 (Qt), pytest + pytest-qt. Existente: openpyxl, sentence-transformers, faiss.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-24-sp4-ui-redesenho-design.md`.
- **É um repositório git** na branch `sp4-ui-desktop`. Cada task termina com um commit.
- Identidade visual: **roxo + monospace**, densidade **confortável**, cantos arredondados, **acento roxo vibrante** (`#8a7fe0`) nas ações principais. Paleta da spec §3 (copiar os hex verbatim).
- Não quebrar a suíte existente: rodar `python -m pytest -q` (config já tem `pythonpath=["src"]` e `tests/conftest.py` com `QT_QPA_PLATFORM=offscreen`).
- Código/comentários em português; `# ponytail:` para atalhos deliberados.
- Não mexer no pipeline/contratos além do que a spec pede (nada além da UI).
- Manter a arquitetura: `estado`/`modelo_tabela`/`worker`/telas/`config_io`/`app`.

---

## Task 1: Correções de bug que destravam a revisão (B1, B2, B5)

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py` (import; `_atualizar_painel`)
- Modify: `src/tdt/ui/tela_inicial.py` (`_terminado` popula `lista_padrao`)
- Test: `tests/test_ui_smoke.py` (estende)

**Interfaces:**
- Consumes: `AppState.lista_padrao`, `ListaPadraoADMS.carregar`, `ListaPadraoADMS.por_sigla`.
- Produces: ao terminar o worker, `AppState.lista_padrao` fica populado; selecionar uma linha na revisão não lança erro e o painel mostra os campos mesmo sem candidatos.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_ui_smoke.py
from pathlib import Path
import pytest
from tdt.contracts import (
    Candidato, Descricoes as _D, Enderecamento as _E, ListaHomogenea,
    Modulo as _M, ResultadoPipeline, SignalRecord as _SR, TipoSinal as _T,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.estado import AppState
from tdt.ui.tela_revisao import TelaRevisao
from tdt.ui.tela_inicial import TelaInicial

_DOCS = Path("docs")


def _sr(sigla, status, candidatos=()):
    return _SR(id="a:1", modulo=_M("M", "sheet_name"),
              tipo_sinal=_T("Discrete", False, "Input"),
              enderecamento=_E("DNP3", (10,)), descricoes=_D("Falha DJ", "FALHA DJ"),
              sigla_sinal=sigla, status=status, candidatos=candidatos)


def test_selecionar_linha_sem_candidatos_nao_quebra(qtbot):
    st = AppState()
    st.registros = [_sr(None, "revisao", candidatos=())]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)  # dispara _atualizar_painel — não deve lançar
    assert "Status" in tela.lbl_campos.text()


def test_candidato_aparece_com_descricao_adms(qtbot):
    st = AppState()
    st.registros = [_sr("DJF1", "decidido", candidatos=(Candidato("DJF1", 0.87, "mesclado"),))]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)
    assert tela.lista_candidatos.count() == 1
    assert "Disjuntor falha 1" in tela.lista_candidatos.item(0).text()


@pytest.mark.skipif(not (_DOCS / "Pontos Padrao ADMS_v1.xlsx").exists(),
                    reason="lista padrão ausente")
def test_terminado_popula_lista_padrao(qtbot):
    st = AppState()
    st.paths["lista_padrao"] = str(_DOCS / "Pontos Padrao ADMS_v1.xlsx")
    tela = TelaInicial(st)
    qtbot.addWidget(tela)
    res = ResultadoPipeline(ListaHomogenea(None, "DNP3", ()), ())
    tela._terminado(res)
    assert st.lista_padrao is not None
    assert st.lista_padrao.por_sigla is not None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_ui_smoke.py -k "sem_candidatos or descricao_adms or popula_lista" -v`
Expected: FAIL — `NameError: QListWidgetItem` (B1) ao selecionar linha; e `st.lista_padrao is None` no terceiro (B5).

- [ ] **Step 3: Fix B1 — importar `QListWidgetItem`**

In `src/tdt/ui/tela_revisao.py`, the `from PySide6.QtWidgets import (...)` block must include `QListWidgetItem`:

```python
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QPushButton, QSizePolicy, QTableView, QVBoxLayout, QWidget,
)
```

- [ ] **Step 4: Fix B2 — `_atualizar_painel` monta os campos sempre**

Replace the body of `_atualizar_painel` in `src/tdt/ui/tela_revisao.py`:

```python
    def _atualizar_painel(self):
        if self._linha < 0:
            return
        r = self._estado.registros[self._linha]
        conf = f"{r.candidatos[0].score:.2f}" if r.candidatos else "—"
        self.lbl_campos.setText(
            f"Sinal: {r.sigla_sinal or '—'}\n"
            f"Status: {r.status}\n"
            f"Confiança: {conf}\n"
            f"Tipo: {r.tipo_sinal.categoria}/{r.tipo_sinal.direcao}\n"
            f"Fase: {r.eletrico.fase or '—'}\n"
            f"Endereço: {';'.join(str(i) for i in r.enderecamento.indices)}\n"
            f"Descrição: {r.descricoes.bruta}"
        )
        self.lista_candidatos.clear()
        lp = self._estado.lista_padrao
        for c in (r.candidatos or ()):
            sp = lp.por_sigla(c.sigla) if lp else None
            desc = f" — {sp.descricao}" if sp else ""
            it = QListWidgetItem(f"{c.sigla} ({c.score:.3f}){desc}")
            it.setData(Qt.UserRole, c.sigla)
            self.lista_candidatos.addItem(it)
```

- [ ] **Step 5: Fix B5 — popular `lista_padrao` ao terminar o worker**

In `src/tdt/ui/tela_inicial.py`, add the import at the top (with the other `tdt` imports):

```python
from tdt.dados.lista_padrao import ListaPadraoADMS
```

Replace `_terminado`:

```python
    def _terminado(self, resultado):
        self._estado.carregar_resultado(resultado)
        caminho_lp = self._estado.paths.get("lista_padrao", "")
        if caminho_lp:
            try:
                self._estado.lista_padrao = ListaPadraoADMS.carregar(caminho_lp)
            except Exception as e:  # ponytail: lista ruim só desliga ADMS na UI + loga
                self.log.appendPlainText(f"[AVISO] não carreguei lista padrão p/ UI: {e}")
        self._fim()
        self.executou.emit()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_smoke.py -k "sem_candidatos or descricao_adms or popula_lista" -v`
Expected: PASS (3 passed; `popula_lista` PASS, ou SKIP se a lista não existir — aceitável).

- [ ] **Step 7: Commit**

```bash
git add src/tdt/ui/tela_revisao.py src/tdt/ui/tela_inicial.py tests/test_ui_smoke.py
git commit -m "fix(ui): destrava revisão — importa QListWidgetItem, painel sem candidato, popula lista_padrao"
```

Run before committing: `python -m pytest -q` → suíte verde.

---

## Task 2: Função de busca na Lista Padrão ADMS (`busca_adms.py`)

**Files:**
- Create: `src/tdt/ui/busca_adms.py`
- Test: `tests/test_ui_busca_adms.py`

**Interfaces:**
- Consumes: `ListaPadraoADMS` (`.discretos`, `.analogicos` → tuplas de `SinalPadrao` com `.sigla`, `.descricao`, `.categoria`).
- Produces: `buscar(lp: ListaPadraoADMS, termo: str, limite: int = 30) -> list[SinalPadrao]` — casa por sigla **e** por texto da descrição (case-insensitive, sem acento), em discretos + analógicos; matches de sigla primeiro; corta em `limite`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_busca_adms.py
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.busca_adms import buscar


def _lp():
    disc = (
        SinalPadrao("DJF1", "Disjuntor falha função 1", "BISI", None, None, "Discrete"),
        SinalPadrao("DJF2", "Disjuntor falha função 2", "BISI", None, None, "Discrete"),
        SinalPadrao("51N", "Sobrecorrente de neutro", "BISI", None, None, "Discrete"),
    )
    ana = (
        SinalPadrao("IFASE", "Corrente de fase A", "AI", None, None, "Analog"),
    )
    return ListaPadraoADMS(disc, ana)


def test_match_por_sigla_vem_primeiro():
    res = buscar(_lp(), "DJF")
    assert [s.sigla for s in res[:2]] == ["DJF1", "DJF2"]


def test_match_por_texto_da_descricao():
    res = buscar(_lp(), "sobrecorrente")
    assert any(s.sigla == "51N" for s in res)


def test_busca_inclui_analogicos():
    res = buscar(_lp(), "corrente")
    siglas = {s.sigla for s in res}
    assert "IFASE" in siglas  # analógico, casa "corrente" na descrição


def test_case_e_acentos_ignorados():
    res = buscar(_lp(), "FUNCAO")
    assert any(s.sigla == "DJF1" for s in res)


def test_respeita_limite():
    res = buscar(_lp(), "", limite=2)  # termo vazio = sem filtro
    assert len(res) == 2


def test_termo_vazio_lista_tudo_ate_limite():
    res = buscar(_lp(), "")
    assert len(res) == 4
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_busca_adms.py -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.busca_adms`.

- [ ] **Step 3: Implement**

Create `src/tdt/ui/busca_adms.py`:

```python
"""Busca na Lista Padrão ADMS por sigla e por texto da descrição.

ponytail: varredura linear sobre a lista (alguns milhares de itens); sem índice.
"""

from __future__ import annotations

import unicodedata

from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao


def _norm(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.upper()


def buscar(lp: ListaPadraoADMS, termo: str, limite: int = 30) -> list[SinalPadrao]:
    alvo = _norm(termo).strip()
    todos = list(lp.discretos) + list(lp.analogicos)
    if not alvo:
        return todos[:limite]
    por_sigla: list[SinalPadrao] = []
    por_desc: list[SinalPadrao] = []
    for s in todos:
        if alvo in _norm(s.sigla):
            por_sigla.append(s)
        elif alvo in _norm(s.descricao):
            por_desc.append(s)
    return (por_sigla + por_desc)[:limite]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_busca_adms.py -v`
Expected: PASS (6 passed).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/busca_adms.py tests/test_ui_busca_adms.py
git commit -m "feat(ui): busca ADMS por sigla e texto (discretos+analógicos)"
```

Run before committing: `python -m pytest -q` → verde.

---

## Task 3: Modelo de tabela enriquecido (colunas, cores, tooltips)

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py`
- Test: `tests/test_ui_modelo_tabela.py` (estende/atualiza)

**Interfaces:**
- Consumes: `AppState.registros`, `AppState.lista_padrao` (`por_sigla`), `SignalRecord.diagnostico`.
- Produces: `ModeloSinais.COLUNAS` na ordem nova; `data()` com `DisplayRole`, `ForegroundRole` (cor de Status/Confiança), `ToolTipRole` (descrição ADMS em Sinal e Descr. ADMS); helpers `cor_faixa(score) -> QColor` e constantes de cor exportados para reuso pelo painel.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_modelo_tabela.py  (substitui o conteúdo antigo equivalente)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais


def _rec(status="decidido", sigla="DJF1"):
    return SignalRecord(
        id="a:1", modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("Falha DJ 52-1", "FALHA DJ"),
        sigla_sinal=sigla, status=status,
        candidatos=(Candidato(sigla, 0.87, "mesclado"),) if sigla else (),
        diagnostico=Diagnostico({sigla: {"tfidf": 0.91, "vetorial": 0.84, "fuzzy": 0.72}}) if sigla else None,
    )


def _state(rec):
    st = AppState()
    st.registros = [rec]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha função 1", "BISI", None, None, "Discrete"),), ())
    return st


def _col(nome):
    return ModeloSinais.COLUNAS.index(nome)


def test_colunas_novas_e_sem_duplicata():
    cols = ModeloSinais.COLUNAS
    assert "Descr. ADMS" in cols
    assert "Descr. normalizada" in cols
    assert "Tokens" in cols
    assert "Motivo" not in cols
    assert "TKN bruto" not in cols


def test_descr_adms_vem_da_lista_padrao():
    m = ModeloSinais(_state(_rec()))
    v = m.data(m.index(0, _col("Descr. ADMS")), Qt.DisplayRole)
    assert v == "Disjuntor falha função 1"


def test_tokens_exibe_normalizada_tokenizada():
    m = ModeloSinais(_state(_rec()))
    v = m.data(m.index(0, _col("Tokens")), Qt.DisplayRole)
    assert v == "FALHA·DJ"


def test_score_embedding():
    m = ModeloSinais(_state(_rec()))
    v = m.data(m.index(0, _col("Score embedding")), Qt.DisplayRole)
    assert "0.84" in str(v)


def test_status_tem_cor_foreground():
    m = ModeloSinais(_state(_rec(status="revisao", sigla=None)))
    cor = m.data(m.index(0, _col("Status")), Qt.ForegroundRole)
    assert isinstance(cor, QColor)


def test_tooltip_sinal_usa_descricao_adms():
    m = ModeloSinais(_state(_rec()))
    tip = m.data(m.index(0, _col("Sinal")), Qt.ToolTipRole)
    assert "Disjuntor falha" in tip


def test_definir_sigla_atualiza():
    st = _state(_rec())
    m = ModeloSinais(st)
    m.definir_sigla(0, "DJF2")
    assert st.registros[0].sigla_sinal == "DJF2"
    assert m.data(m.index(0, _col("Sinal")), Qt.DisplayRole) == "DJF2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v`
Expected: FAIL — colunas/keys ausentes (`ValueError: 'Descr. ADMS' is not in list`), e `ForegroundRole` retorna `None`.

- [ ] **Step 3: Implement**

Replace `src/tdt/ui/modelo_tabela.py` with:

```python
"""Modelo de tabela sobre os SignalRecords (decididos + revisão).

ponytail: model fino que lê do AppState; sem cache, relê o registro a cada data().
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from tdt.ui.estado import AppState

COLUNAS = [
    "Sinal", "Confiança", "Status", "Descr. ADMS", "Descr. bruta",
    "Descr. normalizada", "Tokens", "Tipo", "Escala", "Fase", "Endereço",
    "Score embedding", "Score tf-idf", "Score fuzzy", "Justificativa",
]

# Cores por faixa de confiança (texto). ponytail: faixas fixas; threshold de
# decisão é outra coisa (config).
COR_ALTO = QColor("#1d9e75")
COR_MEDIO = QColor("#b07410")
COR_BAIXO = QColor("#c0492a")
COR_DECIDIDO = QColor("#1d9e75")
COR_REVISAO = QColor("#c0492a")


def cor_faixa(score) -> QColor | None:
    if score is None:
        return None
    if score >= 0.70:
        return COR_ALTO
    if score >= 0.45:
        return COR_MEDIO
    return COR_BAIXO


def _score(rec, sigla, metodo):
    diag = rec.diagnostico
    if diag is None or sigla is None:
        return ""
    v = diag.scores_por_metodo.get(sigla, {}).get(metodo)
    return f"{v:.2f}" if v is not None else ""


class ModeloSinais(QAbstractTableModel):
    COLUNAS = COLUNAS

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._estado.registros)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUNAS)

    def headerData(self, secao, orientacao, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientacao == Qt.Horizontal:
            return COLUNAS[secao]
        return None

    def _adms(self, rec):
        lp = self._estado.lista_padrao
        if lp is None or not rec.sigla_sinal:
            return ""
        sp = lp.por_sigla(rec.sigla_sinal)
        return sp.descricao if sp else ""

    def _texto(self, rec, col):
        sigla = rec.sigla_sinal
        topo = rec.candidatos[0].score if rec.candidatos else None
        nome = COLUNAS[col]
        if nome == "Sinal":
            return sigla or "—"
        if nome == "Confiança":
            return f"{topo:.2f}" if topo is not None else ""
        if nome == "Status":
            return rec.status
        if nome == "Descr. ADMS":
            return self._adms(rec) or "—"
        if nome == "Descr. bruta":
            return rec.descricoes.bruta
        if nome == "Descr. normalizada":
            return rec.descricoes.normalizada
        if nome == "Tokens":
            return "·".join(rec.descricoes.normalizada.split())
        if nome == "Tipo":
            t = rec.tipo_sinal
            return f"{t.categoria}/{t.direcao}"
        if nome == "Escala":
            e = rec.grandezas_analogicas.escala_transmissao
            return "" if e is None else str(e)
        if nome == "Fase":
            return rec.eletrico.fase or "—"
        if nome == "Endereço":
            return ";".join(str(i) for i in rec.enderecamento.indices)
        if nome == "Score embedding":
            return _score(rec, sigla, "vetorial")
        if nome == "Score tf-idf":
            return _score(rec, sigla, "tfidf")
        if nome == "Score fuzzy":
            return _score(rec, sigla, "fuzzy")
        if nome == "Justificativa":
            return rec.justificativa or ""
        return ""

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self._estado.registros[index.row()]
        nome = COLUNAS[index.column()]
        if role == Qt.DisplayRole:
            return self._texto(rec, index.column())
        if role == Qt.ForegroundRole:
            if nome == "Status":
                return COR_DECIDIDO if rec.status == "decidido" else COR_REVISAO
            if nome == "Confiança":
                return cor_faixa(rec.candidatos[0].score if rec.candidatos else None)
        if role == Qt.ToolTipRole and nome in ("Sinal", "Descr. ADMS"):
            return self._adms(rec) or None
        return None

    def definir_sigla(self, linha: int, sigla: str) -> None:
        self._estado.definir_sigla(linha, sigla)
        topo = self.index(linha, 0)
        fim = self.index(linha, len(COLUNAS) - 1)
        self.dataChanged.emit(topo, fim)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v`
Expected: PASS (todos).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py tests/test_ui_modelo_tabela.py
git commit -m "feat(ui): tabela com Descr. ADMS/normalizada/Tokens, cores de status/confiança, tooltip ADMS"
```

Run before committing: `python -m pytest -q` → verde.

---

## Task 4: Painel de revisão — candidatos com descrição, barras de score, busca integrada

**Files:**
- Modify: `src/tdt/ui/tela_revisao.py`
- Test: `tests/test_ui_smoke.py` (estende)

**Interfaces:**
- Consumes: `busca_adms.buscar` (Task 2), `modelo_tabela.cor_faixa`/cores (Task 3), `AppState.lista_padrao`, `SignalRecord.diagnostico`.
- Produces: painel com barras de score por método (cor por faixa), candidatos com descrição ADMS, e busca ao vivo que lista resultados (sigla · categoria · descrição) e ao clicar define a sigla. `TelaRevisao.buscar_adms(termo)` popula `self.lista_resultados`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_ui_smoke.py
from tdt.contracts import Diagnostico


def test_busca_no_painel_lista_resultados_e_escolhe(qtbot):
    st = AppState()
    st.registros = [_sr(None, "revisao", candidatos=())]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),
         SinalPadrao("DJF2", "Disjuntor falha 2", "BISI", None, None, "Discrete")), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)
    tela.buscar_adms("falha")
    assert tela.lista_resultados.count() == 2
    item = tela.lista_resultados.item(0)
    assert "Disjuntor falha" in item.text()
    tela._escolher_resultado(item)  # clicar define a sigla
    assert st.registros[0].sigla_sinal in ("DJF1", "DJF2")


def test_barras_de_score_existem(qtbot):
    st = AppState()
    st.registros = [_sr("DJF1", "decidido", candidatos=(Candidato("DJF1", 0.87, "mesclado"),))]
    st.registros[0] = st.registros[0].__class__(
        **{**st.registros[0].__dict__,
           "diagnostico": Diagnostico({"DJF1": {"tfidf": 0.91, "vetorial": 0.84, "fuzzy": 0.72}})}
    ) if False else st.registros[0]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)
    # as 3 barras (emb/tfidf/fuzzy) foram criadas no painel
    assert len(tela.barras) == 3
```

(Nota: o `replace` de `diagnostico` em SignalRecord é feito no fixture `_rec` do Task 3; aqui o registro pode não ter diagnóstico e as barras devem aparecer zeradas/vazias sem quebrar.)

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py -k "busca_no_painel or barras_de_score" -v`
Expected: FAIL — `AttributeError: 'TelaRevisao' object has no attribute 'buscar_adms'` / `lista_resultados` / `barras`.

- [ ] **Step 3: Implement the panel**

Rewrite `src/tdt/ui/tela_revisao.py` (mantém `_gerar`, `voltar`, a tabela; reescreve o painel). Use this full file:

```python
"""Tela de Revisão: tabela rica + painel de detalhe; aprova e gera o TDT.

ponytail: painel reflete a linha selecionada; edição vai pro AppState via modelo.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QPushButton, QSizePolicy, QTableView, QVBoxLayout, QWidget,
)

from tdt import pipeline
from tdt.ui.busca_adms import buscar
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais, cor_faixa

_METODOS = (("emb", "vetorial"), ("tfidf", "tfidf"), ("fuzzy", "fuzzy"))


class TelaRevisao(QWidget):
    voltar = Signal()

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado
        self._linha = -1

        btn_voltar = QPushButton("← Voltar"); btn_voltar.clicked.connect(self.voltar.emit)
        btn_gerar = QPushButton("aprovar / gerar TDT")
        btn_gerar.setProperty("acao", "principal")
        btn_gerar.clicked.connect(self._gerar)

        topo = QHBoxLayout(); topo.addWidget(btn_voltar); topo.addStretch(); topo.addWidget(btn_gerar)

        # --- painel de detalhe ---
        self.lbl_campos = QLabel("Selecione um sinal"); self.lbl_campos.setWordWrap(True)

        self.barras: list[QProgressBar] = []
        cx_scores = QVBoxLayout()
        for rotulo, _chave in _METODOS:
            linha = QHBoxLayout()
            linha.addWidget(QLabel(rotulo))
            barra = QProgressBar(); barra.setRange(0, 100); barra.setTextVisible(True)
            barra.setFixedHeight(14)
            self.barras.append(barra)
            linha.addWidget(barra, 1)
            cx_scores.addLayout(linha)

        self.lista_candidatos = QListWidget()
        self.lista_candidatos.itemClicked.connect(self._escolher_candidato)

        self.busca = QLineEdit(); self.busca.setPlaceholderText("buscar na Lista Padrão ADMS…")
        self.busca.textChanged.connect(self.buscar_adms)
        self.lista_resultados = QListWidget()
        self.lista_resultados.itemClicked.connect(self._escolher_resultado)

        painel = QVBoxLayout()
        painel.addWidget(QLabel("DETALHE DO SINAL"))
        painel.addWidget(self.lbl_campos)
        painel.addWidget(QLabel("Scores por método"))
        painel.addLayout(cx_scores)
        painel.addWidget(QLabel("Candidatos"))
        painel.addWidget(self.lista_candidatos)
        painel.addWidget(QLabel("Buscar na Lista Padrão ADMS"))
        painel.addWidget(self.busca)
        painel.addWidget(self.lista_resultados)
        cofre = QWidget(); cofre.setObjectName("painelDetalhe")
        cofre.setLayout(painel); cofre.setFixedWidth(280)

        # --- tabela ---
        self.tabela = QTableView()
        self.tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabela.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.tabela.setSelectionBehavior(QTableView.SelectRows)
        self.tabela.setAlternatingRowColors(True)

        corpo = QHBoxLayout(); corpo.addWidget(cofre); corpo.addWidget(self.tabela, 1)
        raiz = QVBoxLayout(self)
        raiz.addLayout(topo)
        raiz.addLayout(corpo, 1)

    def carregar(self) -> None:
        self._modelo = ModeloSinais(self._estado)
        self.tabela.setModel(self._modelo)
        self.tabela.selectionModel().currentRowChanged.connect(self._linha_mudou)

    def _linha_mudou(self, atual, _anterior):
        self._linha = atual.row()
        self._atualizar_painel()

    def _registro(self):
        if 0 <= self._linha < len(self._estado.registros):
            return self._estado.registros[self._linha]
        return None

    def _atualizar_painel(self):
        r = self._registro()
        if r is None:
            return
        conf = f"{r.candidatos[0].score:.2f}" if r.candidatos else "—"
        self.lbl_campos.setText(
            f"Sinal: {r.sigla_sinal or '—'}\n"
            f"Status: {r.status}\n"
            f"Confiança: {conf}\n"
            f"Tipo: {r.tipo_sinal.categoria}/{r.tipo_sinal.direcao}\n"
            f"Fase: {r.eletrico.fase or '—'}\n"
            f"Endereço: {';'.join(str(i) for i in r.enderecamento.indices)}\n"
            f"Descrição: {r.descricoes.bruta}"
        )
        self._atualizar_barras(r)
        self._atualizar_candidatos(r)

    def _atualizar_barras(self, r):
        diag = r.diagnostico
        sigla = r.sigla_sinal
        for (_, chave), barra in zip(_METODOS, self.barras):
            v = None
            if diag is not None and sigla is not None:
                v = diag.scores_por_metodo.get(sigla, {}).get(chave)
            pct = int(round((v or 0.0) * 100))
            barra.setValue(pct)
            barra.setFormat(f"{v:.2f}" if v is not None else "—")
            cor = cor_faixa(v)
            if cor is not None:
                barra.setStyleSheet(f"QProgressBar::chunk {{ background-color: {cor.name()}; }}")

    def _atualizar_candidatos(self, r):
        self.lista_candidatos.clear()
        lp = self._estado.lista_padrao
        if not r.candidatos:
            it = QListWidgetItem("sem candidatos — use a busca")
            it.setFlags(Qt.NoItemFlags)
            self.lista_candidatos.addItem(it)
            return
        for c in r.candidatos:
            sp = lp.por_sigla(c.sigla) if lp else None
            desc = f" — {sp.descricao}" if sp else ""
            it = QListWidgetItem(f"{c.sigla} ({c.score:.3f}){desc}")
            it.setData(Qt.UserRole, c.sigla)
            if sp:
                it.setToolTip(sp.descricao)
            self.lista_candidatos.addItem(it)

    def buscar_adms(self, termo: str):
        self.lista_resultados.clear()
        lp = self._estado.lista_padrao
        if lp is None or not termo.strip():
            return
        for sp in buscar(lp, termo, limite=30):
            it = QListWidgetItem(f"{sp.sigla}  ·  {sp.categoria}  —  {sp.descricao}")
            it.setData(Qt.UserRole, sp.sigla)
            it.setToolTip(sp.descricao)
            self.lista_resultados.addItem(it)

    def _escolher_candidato(self, item):
        sigla = item.data(Qt.UserRole)
        if self._linha >= 0 and sigla:
            self._modelo.definir_sigla(self._linha, sigla)
            self._atualizar_painel()

    def _escolher_resultado(self, item):
        sigla = item.data(Qt.UserRole)
        if self._linha >= 0 and sigla:
            self._modelo.definir_sigla(self._linha, sigla)
            self._atualizar_painel()

    def _gerar(self):
        lp = self._estado.lista_padrao
        template = self._estado.paths.get("template", "")
        output = self._estado.paths.get("output", "")
        if not lp or not template or not output:
            QMessageBox.warning(self, "Erro", "Lista padrão, template e output são obrigatórios")
            return
        try:
            wb = pipeline.gerar_tdt(
                self._estado.registros, template, lp,
                subestacao=self._estado.subestacao, aliases=self._estado.aliases,
            )
            out_path = Path(output) / "TDT.xlsx"
            wb.save(str(out_path))
            QMessageBox.information(self, "Sucesso", f"TDT gerado: {out_path}")
        except Exception as e:  # ponytail: erro vira dialogo; sem retry
            QMessageBox.critical(self, "Erro", f"Falha ao gerar TDT: {e}")
```

(Verifique a assinatura de `pipeline.gerar_tdt` no código atual; mantenha exatamente os argumentos que o arquivo original já passava — incluindo `aliases`.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_smoke.py -k "busca_no_painel or barras_de_score or sem_candidatos or descricao_adms" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/tela_revisao.py tests/test_ui_smoke.py
git commit -m "feat(ui): painel de revisão com barras de score, candidatos com descrição ADMS e busca ao vivo"
```

Run before committing: `python -m pytest -q` → verde.

---

## Task 5: Edição inline da célula "Sinal" (delegate)

**Files:**
- Create: `src/tdt/ui/delegate_sinal.py`
- Modify: `src/tdt/ui/tela_revisao.py` (instala o delegate na coluna Sinal)
- Test: `tests/test_ui_smoke.py` (estende)

**Interfaces:**
- Consumes: `ModeloSinais.COLUNAS`, `ModeloSinais.definir_sigla`, `AppState.registros`, `busca_adms.buscar`.
- Produces: `DelegateSinal(QStyledItemDelegate)` — `createEditor` devolve um `QComboBox` editável com os candidatos da linha + as siglas ADMS (via busca); `setModelData` chama `modelo.definir_sigla`. Instalado em `TelaRevisao` na coluna "Sinal" com `EditTriggers = DoubleClicked`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/test_ui_smoke.py
from tdt.ui.delegate_sinal import DelegateSinal


def test_delegate_cria_editor_com_candidatos(qtbot):
    st = AppState()
    st.registros = [_sr("DJF1", "decidido", candidatos=(Candidato("DJF1", 0.87, "mesclado"),
                                                        Candidato("DJF", 0.61, "mesclado")))]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    delegate = tela.tabela.itemDelegateForColumn(ModeloSinais.COLUNAS.index("Sinal"))
    assert isinstance(delegate, DelegateSinal)
    editor = delegate.createEditor(tela, None, tela._modelo.index(0, 0))
    textos = [editor.itemText(i) for i in range(editor.count())]
    assert any("DJF1" in t for t in textos)
    assert any("DJF" == t or "DJF" in t for t in textos)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py -k "delegate_cria_editor" -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.delegate_sinal`.

- [ ] **Step 3: Implement the delegate**

Create `src/tdt/ui/delegate_sinal.py`:

```python
"""Editor inline da célula 'Sinal': combo com candidatos + busca ADMS.

ponytail: combo editável; itens = candidatos da linha + siglas ADMS. setModelData
delega ao ModeloSinais.definir_sigla (mesma rota do painel).
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QStyledItemDelegate

from tdt.ui.busca_adms import buscar
from tdt.ui.estado import AppState


class DelegateSinal(QStyledItemDelegate):
    def __init__(self, estado: AppState, modelo, parent=None):
        super().__init__(parent)
        self._estado = estado
        self._modelo = modelo

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        siglas: list[str] = []
        rec = self._estado.registros[index.row()] if index.isValid() else None
        if rec is not None:
            siglas.extend(c.sigla for c in rec.candidatos)
        lp = self._estado.lista_padrao
        if lp is not None:
            for sp in buscar(lp, "", limite=500):
                if sp.sigla not in siglas:
                    siglas.append(sp.sigla)
        combo.addItems(siglas)
        return combo

    def setModelData(self, editor, model, index):
        sigla = editor.currentText().strip()
        if sigla:
            self._modelo.definir_sigla(index.row(), sigla)
```

- [ ] **Step 4: Install the delegate in TelaRevisao**

In `src/tdt/ui/tela_revisao.py`, add the import:

```python
from tdt.ui.delegate_sinal import DelegateSinal
```

In `carregar`, after setting the model, install the delegate and enable double-click editing:

```python
    def carregar(self) -> None:
        self._modelo = ModeloSinais(self._estado)
        self.tabela.setModel(self._modelo)
        self.tabela.setEditTriggers(QTableView.DoubleClicked)
        col_sinal = ModeloSinais.COLUNAS.index("Sinal")
        self.tabela.setItemDelegateForColumn(col_sinal, DelegateSinal(self._estado, self._modelo, self.tabela))
        self.tabela.selectionModel().currentRowChanged.connect(self._linha_mudou)
```

Also, make the "Sinal" column editable in the model: in `src/tdt/ui/modelo_tabela.py`, add a `flags` method to `ModeloSinais`:

```python
    def flags(self, index):
        base = super().flags(index)
        if COLUNAS[index.column()] == "Sinal":
            return base | Qt.ItemIsEditable
        return base
```

(Add `Qt` is already imported in modelo_tabela.py.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_smoke.py -k "delegate_cria_editor" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/ui/delegate_sinal.py src/tdt/ui/tela_revisao.py src/tdt/ui/modelo_tabela.py tests/test_ui_smoke.py
git commit -m "feat(ui): edição inline da célula Sinal via delegate (candidatos + busca ADMS)"
```

Run before committing: `python -m pytest -q` → verde.

---

## Task 6: Tema refinado + cards/acento nas telas Inicial e Config

**Files:**
- Modify: `src/tdt/ui/tema.qss` (reescrito)
- Modify: `src/tdt/ui/tela_inicial.py` (agrupar em cards; acento no EXECUTAR)
- Modify: `src/tdt/ui/tela_config.py` (agrupar em cards; acento no Salvar)
- Test: `tests/test_ui_smoke.py` (estende — telas instanciam sem erro)

**Interfaces:**
- Consumes: as telas existentes.
- Produces: `tema.qss` refinado; botões principais com `setProperty("acao","principal")`; campos agrupados em `QGroupBox` com título. Sem mudança de comportamento.

- [ ] **Step 1: Write the failing/guard test**

```python
# append to tests/test_ui_smoke.py
from tdt.ui.tela_config import TelaConfig


def test_botoes_principais_tem_property_acao(qtbot, tmp_path):
    st = AppState()
    ti = TelaInicial(st); qtbot.addWidget(ti)
    tc = TelaConfig(st, config_path=tmp_path / "config.toml"); qtbot.addWidget(tc)
    # EXECUTAR e Salvar marcados como ação principal
    assert ti.btn_executar.property("acao") == "principal"
    assert tc.findChild(type(ti.btn_executar)) is not None  # instancia sem erro
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py -k "botoes_principais" -v`
Expected: FAIL — `property("acao")` é `None` (ainda não marcado).

- [ ] **Step 3: Mark accent buttons + group into cards (TelaInicial)**

In `src/tdt/ui/tela_inicial.py`:
- Add `from PySide6.QtWidgets import QGroupBox` to the imports.
- After creating `self.btn_executar`, mark it: `self.btn_executar.setProperty("acao", "principal")`.
- Wrap the existing column layouts in `QGroupBox`es with titles. Replace the final assembly (`col_esq`/`col_meio`/`col_dir` raw layouts) so each column's content sits inside a titled group. Minimal change — wrap each `QVBoxLayout` in a `QGroupBox`:

```python
        def _grupo(titulo, layout):
            g = QGroupBox(titulo); g.setLayout(layout); return g

        raiz = QHBoxLayout(self)
        raiz.addWidget(_grupo("Entrada / Processamento", col_esq))
        raiz.addWidget(_grupo("Subestação / Sheets", col_meio))
        raiz.addWidget(_grupo("Execução", col_dir), 1)
```

(Keep all widget creation and signal wiring exactly as-is; only the final assembly changes.)

- [ ] **Step 4: Mark accent + group into cards (TelaConfig)**

In `src/tdt/ui/tela_config.py`:
- After creating `btn_salvar`, mark it: `btn_salvar.setProperty("acao", "principal")`.
- (Cards opcional aqui: o `QFormLayout` já agrupa; manter como está é aceitável. Apenas o acento é obrigatório neste passo.)

- [ ] **Step 5: Rewrite the theme**

Replace `src/tdt/ui/tema.qss` with the refined theme (paleta da spec §3; densidade confortável; acento; cards; tabela; barras):

```css
/* SP4.1 UI — tema roxo/monospace refinado.
   fundo #7d7796 · painel #6c6688 · painel-2 #544f6e · borda #46415f
   acento #8a7fe0 (texto #1c1733) · texto #f3f1f7
   ok #1d9e75 · medio #b07410 · baixo #c0492a */

QMainWindow, QWidget {
    background-color: #7d7796;
    color: #f3f1f7;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 13px;
}

QGroupBox {
    background-color: #6c6688;
    border: 1px solid #46415f;
    border-radius: 12px;
    margin-top: 14px;
    padding: 12px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #d8d3ee;
    letter-spacing: 1px;
}

#painelDetalhe {
    background-color: #6c6688;
    border: 1px solid #46415f;
    border-radius: 12px;
    padding: 8px;
}

QLabel { color: #e8e6f2; }

QPushButton {
    background-color: #544f6e;
    border: 1px solid #46415f;
    border-radius: 10px;
    padding: 8px 14px;
    color: #f3f1f7;
}
QPushButton:hover { background-color: #615b80; }
QPushButton:pressed { background-color: #46415f; }
QPushButton:disabled { background-color: #5a5578; color: #a59fc0; }

QPushButton[acao="principal"] {
    background-color: #8a7fe0;
    color: #1c1733;
    border: none;
    font-weight: bold;
    padding: 10px 18px;
}
QPushButton[acao="principal"]:hover { background-color: #9a90ea; }
QPushButton[acao="principal"]:pressed { background-color: #776ccb; }

QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit {
    background-color: #f1eff7;
    color: #2c2a36;
    border: 1px solid #46415f;
    border-radius: 8px;
    padding: 6px 8px;
    selection-background-color: #8a7fe0;
}

QPlainTextEdit { font-size: 12px; }

QTableView {
    background-color: #e7e5ef;
    alternate-background-color: #ddd9e8;
    color: #2c2a36;
    gridline-color: #c4c0d4;
    border: 1px solid #46415f;
    border-radius: 12px;
    selection-background-color: #bdb2db;
    selection-color: #1c1733;
}
QTableView::item { padding: 6px 9px; }

QHeaderView::section {
    background-color: #6c6688;
    color: #f3f1f7;
    padding: 9px 11px;
    border: none;
    border-bottom: 2px solid #46415f;
    font-weight: bold;
}

QListWidget {
    background-color: #efedf6;
    color: #2c2a36;
    border: 1px solid #46415f;
    border-radius: 8px;
    padding: 2px;
}
QListWidget::item { padding: 6px 8px; border-radius: 6px; }
QListWidget::item:selected { background-color: #bdb2db; color: #1c1733; }

QProgressBar {
    background-color: #46415f;
    border: none;
    border-radius: 7px;
    text-align: center;
    color: #f3f1f7;
}
QProgressBar::chunk { background-color: #8a7fe0; border-radius: 7px; }

QScrollBar:vertical { background: #6c6688; width: 11px; margin: 0; }
QScrollBar::handle:vertical { background: #46415f; border-radius: 5px; min-height: 24px; }
QScrollBar:horizontal { background: #6c6688; height: 11px; margin: 0; }
QScrollBar::handle:horizontal { background: #46415f; border-radius: 5px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }

QCheckBox, QRadioButton { color: #e8e6f2; spacing: 7px; }
QCheckBox::indicator, QRadioButton::indicator {
    width: 15px; height: 15px;
    border: 2px solid #46415f;
    background: #f1eff7;
}
QCheckBox::indicator { border-radius: 4px; }
QRadioButton::indicator { border-radius: 8px; }
QCheckBox::indicator:checked, QRadioButton::indicator:checked {
    background: #8a7fe0;
    border: 2px solid #776ccb;
}

QSpinBox::up-button, QDoubleSpinBox::up-button { width: 18px; subcontrol-position: top right; }
QSpinBox::down-button, QDoubleSpinBox::down-button { width: 18px; subcontrol-position: bottom right; }
```

- [ ] **Step 6: Run tests + manual check**

Run: `python -m pytest tests/test_ui_smoke.py -k "botoes_principais" -v`
Expected: PASS.
Run full suite: `python -m pytest -q` → verde.
Manual: `python -m tdt.ui_main` — confirmar visual das 3 telas (cards, acento roxo vibrante, tabela colorida, painel com barras), e que a revisão mostra candidatos + busca com descrições.

- [ ] **Step 7: Commit**

```bash
git add src/tdt/ui/tema.qss src/tdt/ui/tela_inicial.py src/tdt/ui/tela_config.py tests/test_ui_smoke.py
git commit -m "feat(ui): tema refinado (cards, acento, tabela/barras) + agrupamento das telas"
```

---

## Self-Review (vs spec)

**Spec coverage:**
- §2 B1 (import) → Task 1 Step 3. ✓
- §2 B2 (f-string painel) → Task 1 Step 4. ✓
- §2 B3 (busca pobre) → Task 2 + Task 4 (busca ao vivo). ✓
- §2 B4 (coluna duplicada) → Task 3 (remove Motivo/TKN bruto). ✓
- §7 B5 (lista_padrao nunca populado) → Task 1 Step 5. ✓
- §3 tema.qss → Task 6. ✓
- §4.1 painel (campos, barras score+cor, candidatos+ADMS) → Task 4. ✓
- §4.2 comparação (tabela ADMS/bruta/normalizada/tokens; candidatos/busca com ADMS) → Task 3 (colunas) + Task 4 (candidatos/busca). ✓
- §4.3 busca (sigla+texto, discretos+analógicos, com descrição) → Task 2 + Task 4. ✓
- §4.4 colunas + cores + tooltip → Task 3. ✓
- §4.5 edição painel + célula (delegate) → Task 4 (painel) + Task 5 (delegate). ✓
- §5 cards/acento Inicial+Config → Task 6. ✓
- §8 testes (busca, modelo, smoke) → Tasks 2/3/1/4/5/6. ✓

**Placeholder scan:** sem TBD/TODO; todo passo de código tem o código. O teste `test_barras_de_score_existem` (Task 4) tem um trecho `if False else` redundante — **simplificar ao escrever**: o registro já é criado por `_sr` sem diagnóstico; basta afirmar `len(tela.barras) == 3` (as barras existem independentemente de diagnóstico). Remover a expressão `if False`.

**Type consistency:** `definir_sigla(linha/indice, sigla)` consistente (AppState/ModeloSinais); `buscar(lp, termo, limite)` igual nas Tasks 2/4/5; `cor_faixa(score)` e cores exportadas na Task 3 e usadas na Task 4; `COLUNAS.index("Sinal")` usado nas Tasks 5; `pipeline.gerar_tdt(registros, template, lp, subestacao=, aliases=)` mantido como no arquivo atual (Task 4 preserva a chamada existente).
