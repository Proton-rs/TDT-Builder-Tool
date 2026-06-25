# SP4 — UI Desktop (PySide6) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-window PySide6 desktop UI over the SP1 pipeline: configure → run (live log, cancel) → review/edit each signal in a rich table → generate the TDT, plus a settings tab persisted to `config.toml`.

**Architecture:** Thin UI over the existing pipeline. Three screens in a `QStackedWidget` (Inicial, Revisão, Configurações). The pipeline runs in a `QThread` worker that streams audit events and supports cooperative cancellation. The UI consumes only the data contract (`ResultadoPipeline`, `SignalRecord`, `ListaPadraoADMS`) plus four small, retrocompatible pipeline extensions. Business logic stays in the pipeline; the UI never duplicates scoring/rules.

**Tech Stack:** Python ≥3.11, PySide6 (Qt), tomllib (stdlib read) + tomli-w (write), pytest + pytest-qt. Existing: openpyxl, sentence-transformers, faiss, scikit-learn.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-06-24-sp4-ui-desktop-design.md`.
- **Not a git repository.** Ignore the `git commit` convention; each task ends with a **Checkpoint** step = run the full suite `python -m pytest -q` and confirm green. Do not run `git`.
- Pipeline extensions MUST be retrocompatible: CLI (`tdt.cli`) and `bench/benchmark.py` must keep working unchanged. New params default to off/None.
- Contracts are immutable frozen dataclasses; enrichment is functional (`dataclasses.replace`), never in-place mutation.
- Tests run from project root: `python -m pytest` (pytest config already sets `pythonpath=["src"]`).
- Code/comments in Portuguese, matching existing modules. Use `# ponytail:` to mark deliberate shortcuts.
- UI is Python-native PySide6; theme reproduces `docs/interface_inicial.jpg` / `docs/interface_revisão.jpg` (roxo/cinza, monospace).
- Headless test environment: Qt smoke tests MUST set `QT_QPA_PLATFORM=offscreen` (do it in `tests/conftest.py` so no display is needed).

---

## Task 1: Contrato `Diagnostico` + scores por método no pipeline

**Files:**
- Modify: `src/tdt/contracts.py` (add `Diagnostico`, add field to `SignalRecord`)
- Modify: `src/tdt/pipeline.py` (`_classificar_sinal`, `executar`)
- Test: `tests/test_pipeline_diagnostico.py` (create)

**Interfaces:**
- Produces:
  - `Diagnostico(scores_por_metodo: dict[str, dict[str, float]])` (frozen) — outer key = sigla candidata, inner = `{"tfidf": float, "vetorial": float, "fuzzy": float}`.
  - `SignalRecord.diagnostico: Diagnostico | None = None`.
  - `executar(..., diagnostico: bool = False)` — quando `True`, cada `SignalRecord` decidido carrega seu `Diagnostico`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline_diagnostico.py
from tdt.contracts import Diagnostico, Candidato
from tdt import pipeline


def test_classificar_preenche_diagnostico_quando_ligado(rec_minimo, scorers_fakes):
    tfidf, indice, fuzzy, config = scorers_fakes
    out = pipeline._classificar_sinal(
        rec_minimo, tfidf, indice, fuzzy, config, diagnostico=True
    )
    assert out.diagnostico is not None
    # a sigla top tem os três métodos registrados
    top = out.candidatos[0].sigla
    assert set(out.diagnostico.scores_por_metodo[top]) == {"tfidf", "vetorial", "fuzzy"}


def test_classificar_sem_diagnostico_por_padrao(rec_minimo, scorers_fakes):
    tfidf, indice, fuzzy, config = scorers_fakes
    out = pipeline._classificar_sinal(rec_minimo, tfidf, indice, fuzzy, config)
    assert out.diagnostico is None
```

Add fixtures to `tests/test_pipeline_diagnostico.py` (self-contained, fakes that return fixed candidates):

```python
import pytest
from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)


class _ScorerFake:
    def __init__(self, fonte, scores):
        self._fonte = fonte
        self._scores = scores  # list[(sigla, score)]

    def pontuar(self, rec, k=5):
        return [Candidato(s, sc, self._fonte) for s, sc in self._scores[:k]]


class _IndiceFake:
    def __init__(self, scores):
        self._scores = scores

    def buscar(self, texto, k=5):
        return self._scores[:k]


@pytest.fixture
def rec_minimo():
    return SignalRecord(
        id="s:1",
        modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("FALHA DJ", "FALHA DJ"),
    )


@pytest.fixture
def scorers_fakes():
    tfidf = _ScorerFake("tfidf", [("DJF1", 0.9), ("DJF", 0.5)])
    fuzzy = _ScorerFake("fuzzy", [("DJF1", 0.7), ("DJF", 0.4)])
    indice = _IndiceFake([("DJF1", 0.8), ("DJF", 0.3)])
    return tfidf, indice, fuzzy, Config()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline_diagnostico.py -v`
Expected: FAIL — `ImportError: cannot import name 'Diagnostico'` (and/or `_classificar_sinal` got unexpected kw `diagnostico`).

- [ ] **Step 3: Add the contract**

In `src/tdt/contracts.py`, after the `Candidato` dataclass add:

```python
@dataclass(frozen=True)
class Diagnostico:
    """Scores por método por candidato, para auditoria/UI.

    ``scores_por_metodo[sigla] = {"tfidf": .., "vetorial": .., "fuzzy": ..}``.
    """

    scores_por_metodo: dict[str, dict[str, float]]
```

In `SignalRecord`, add the field (keep it last among the optionals, after `justificativa`):

```python
    diagnostico: "Diagnostico | None" = None
```

- [ ] **Step 4: Populate it in the pipeline**

In `src/tdt/pipeline.py`, change `_classificar_sinal` to optionally build the diagnostic from the per-method lists it already computes:

```python
def _classificar_sinal(rec, tfidf, indice, fuzzy, config, diagnostico: bool = False) -> SignalRecord:
    c_tfidf = tfidf.pontuar(rec, k=config.k_vizinhos)
    c_vet = pontuar_vetorial(rec, indice, k=config.k_vizinhos)
    c_fuzzy = fuzzy.pontuar(rec, k=config.k_vizinhos)
    fundidos = mescla.mesclar(
        [
            (c_tfidf, config.peso_tfidf),
            (c_vet, config.peso_vetorial),
            (c_fuzzy, config.peso_fuzzy),
        ]
    )
    com_regras, ajustes = motor_regras.aplicar_rastreado(rec, fundidos, config)
    diag = None
    if diagnostico:
        por: dict[str, dict[str, float]] = {}
        for fonte, lst in (("tfidf", c_tfidf), ("vetorial", c_vet), ("fuzzy", c_fuzzy)):
            for c in lst:
                por.setdefault(c.sigla, {})[fonte] = c.score
        diag = Diagnostico(scores_por_metodo=por)
    rec = replace(rec, diagnostico=diag) if diag is not None else rec
    decidido = roteador.rotear(replace(rec, candidatos=tuple(com_regras)), config)
    if ajustes and decidido.status == "decidido":
        motivos = "; ".join(a.motivo for a in ajustes)
        decidido = replace(
            decidido, justificativa=f"{decidido.justificativa} | regras: {motivos}"
        )
    return decidido
```

Add `Diagnostico` to the contracts import at the top of `pipeline.py`:

```python
from tdt.contracts import Diagnostico, ItemRevisao, ResultadoPipeline, SignalRecord
```

Thread the flag through `executar`: add `diagnostico: bool = False` to its signature and pass it at the call site:

```python
            decidido = _classificar_sinal(rec, tfidf, indice, fuzzy, config, diagnostico=diagnostico)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline_diagnostico.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all prior tests still pass (120) + 2 new = 122 passed. Confirms CLI/benchmark contracts unbroken.

---

## Task 2: Cancelamento cooperativo em `executar`

**Files:**
- Modify: `src/tdt/pipeline.py` (`executar` loop)
- Test: `tests/test_pipeline_cancelamento.py` (create)

**Interfaces:**
- Produces: `executar(..., cancelado: Callable[[], bool] | None = None)` — quando `cancelado()` retorna `True`, o loop de classificação para e devolve um `ResultadoPipeline` parcial; registra evento `AVISO` "cancelado pelo usuário".

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline_cancelamento.py
from pathlib import Path
import pytest
from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt import pipeline

DOCS = Path("docs")


@pytest.mark.skipif(
    not (DOCS / "input_nao_homogeneo_1.xlsx").exists(),
    reason="fixture de input ausente",
)
def test_cancelamento_para_cedo():
    aud = Auditoria()
    resultado, _wb = pipeline.executar(
        DOCS / "input_nao_homogeneo_1.xlsx",
        DOCS / "dnp3_template.xlsx",
        DOCS / "Pontos Padrao ADMS_v1.xlsx",
        config=Config(),
        encoder=criar_encoder(Config().modelo_embedding),
        cancelado=lambda: True,  # cancela imediatamente
        auditoria=aud,
    )
    assert len(resultado.lista.registros) == 0
    assert any("cancelado" in e.msg.lower() for e in aud.eventos)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline_cancelamento.py -v`
Expected: FAIL — `executar()` got an unexpected keyword argument `cancelado`.

- [ ] **Step 3: Implement cooperative cancellation**

In `src/tdt/pipeline.py`, add `cancelado: "Callable[[], bool] | None" = None` to `executar`'s keyword-only params, add the import `from typing import Callable` at the top, and guard the per-record loop. Replace the inner loop body start:

```python
    for sn in rota.sheets_dados:
        if cancelado is not None and cancelado():
            aud.evento("pipeline", "cancelado pelo usuário", "AVISO")
            break
        rows = ler_rows(wb_in[sn])
        mapa = analisar(rows, encoder, ref_emb)
        for rec in estruturar(rows, mapa, sheet_name=sn, config=config, vocab=vocab):
            if cancelado is not None and cancelado():
                aud.evento("pipeline", "cancelado pelo usuário", "AVISO")
                break
            if rec.tipo_sinal.categoria == "Analog":
                analogicos += 1
                continue
            decidido = _classificar_sinal(rec, tfidf, indice, fuzzy, config, diagnostico=diagnostico)
            ...
```

(Keep the rest of the loop unchanged. The outer `break` after the inner `break` is acceptable — the next outer-iteration guard also catches it; to be explicit you may add `if cancelado is not None and cancelado(): break` right after the inner `for`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline_cancelamento.py -v`
Expected: PASS (or SKIP if the input fixture is absent — acceptable; note it).

- [ ] **Step 5: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 3: `Auditoria.on_evento` (log streaming) + `pipeline.gerar_tdt`

**Files:**
- Modify: `src/tdt/auditoria.py` (`__init__`, `evento`)
- Modify: `src/tdt/pipeline.py` (add `gerar_tdt`)
- Test: `tests/test_auditoria_callback.py` (create), `tests/test_pipeline_gerar_tdt.py` (create)

**Interfaces:**
- Produces:
  - `Auditoria(on_evento: Callable[[Evento], None] | None = None)` — `evento(...)` chama `on_evento(ev)` após acumular.
  - `pipeline.gerar_tdt(registros: list[SignalRecord], template_path, lp, subestacao=None) -> openpyxl.Workbook` — monta a `ListaHomogenea` e gera o workbook (mesma rota do fim de `executar`), para a UI usar no "aprovar/gerar TDT".

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_auditoria_callback.py
from tdt.auditoria import Auditoria, Evento


def test_on_evento_e_chamado():
    recebidos = []
    aud = Auditoria(on_evento=recebidos.append)
    aud.evento("mod", "oi", "INFO")
    assert len(recebidos) == 1
    assert isinstance(recebidos[0], Evento)
    assert recebidos[0].msg == "oi"


def test_sem_callback_funciona_normal():
    aud = Auditoria()
    aud.evento("mod", "oi", "INFO")
    assert aud.contagem("INFO") == 1
```

```python
# tests/test_pipeline_gerar_tdt.py
from pathlib import Path
import pytest
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt import pipeline

DOCS = Path("docs")


@pytest.mark.skipif(
    not (DOCS / "dnp3_template.xlsx").exists(), reason="template ausente"
)
def test_gerar_tdt_de_lista_vazia_nao_quebra():
    lp = ListaPadraoADMS.carregar(DOCS / "Pontos Padrao ADMS_v1.xlsx")
    wb = pipeline.gerar_tdt([], DOCS / "dnp3_template.xlsx", lp, subestacao=None)
    assert wb is not None  # workbook estruturalmente válido, sem registros
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auditoria_callback.py tests/test_pipeline_gerar_tdt.py -v`
Expected: FAIL — `Auditoria.__init__` got unexpected `on_evento`; `module 'tdt.pipeline' has no attribute 'gerar_tdt'`.

- [ ] **Step 3: Implement the callback**

In `src/tdt/auditoria.py`, update `__init__` and `evento`:

```python
    def __init__(self, on_evento: "Callable[[Evento], None] | None" = None) -> None:
        self.eventos: list[Evento] = []
        self._on_evento = on_evento
```

At the end of `evento(...)`, after `self.eventos.append(ev)` and the `_log.log(...)` line:

```python
        if self._on_evento is not None:
            self._on_evento(ev)
```

Add the import at the top of `auditoria.py`:

```python
from typing import Callable
```

- [ ] **Step 4: Implement `gerar_tdt`**

In `src/tdt/pipeline.py`, add a thin helper that reuses the existing final steps of `executar`:

```python
def gerar_tdt(registros, template_path, lp, subestacao=None):
    """Gera o workbook TDT a partir de uma lista (já decidida/editada) de registros."""
    pareados, _rev = dc_pairer.parear(list(registros))
    corrigidos, _rev2 = corrigir(list(pareados))
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    return engine_tdt.gerar(lista, template_path, lp)
```

(All of `dc_pairer`, `corrigir`, `criador_lista_homogenea`, `engine_tdt` are already imported in `pipeline.py`.)

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_auditoria_callback.py tests/test_pipeline_gerar_tdt.py -v`
Expected: PASS (gerar_tdt may SKIP if template absent — acceptable).

- [ ] **Step 6: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green. Pipeline extensions (§6 of the spec) complete.

---

## Task 4: Dependências de UI + `config_io` (config.toml ↔ Config)

**Files:**
- Modify: `pyproject.toml` (optional-deps `ui`, dev `pytest-qt`/`tomli-w`)
- Create: `src/tdt/ui/__init__.py`
- Create: `src/tdt/ui/config_io.py`
- Test: `tests/test_ui_config_io.py`

**Interfaces:**
- Produces:
  - `carregar_config(path: str | Path) -> tuple[Config, dict]` — devolve a `Config` e um dict de paths (`{"input", "output", "template", "lista_padrao"}`). Arquivo ausente/corrompido → defaults + paths vazios.
  - `salvar_config(path, config: Config, paths: dict) -> None` — escreve TOML legível.

- [ ] **Step 1: Add dependencies**

In `pyproject.toml`, under `[project.optional-dependencies]`:

```toml
ui = ["PySide6>=6.6", "tomli-w>=1.0"]
dev = ["pytest>=8", "pytest-qt>=4.4", "tomli-w>=1.0"]
```

Then install: `python -m pip install -e ".[ui,dev,vetorial]"`
Expected: PySide6, pytest-qt, tomli-w installed.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_ui_config_io.py
from tdt.config import Config
from tdt.ui.config_io import carregar_config, salvar_config


def test_round_trip(tmp_path):
    p = tmp_path / "config.toml"
    cfg = Config(threshold_pct=0.5, peso_tfidf=0.4, peso_vetorial=0.3, peso_fuzzy=0.3)
    paths = {"input": "C:/in", "output": "C:/out", "template": "t.xlsx", "lista_padrao": "lp.xlsx"}
    salvar_config(p, cfg, paths)
    cfg2, paths2 = carregar_config(p)
    assert cfg2.threshold_pct == 0.5
    assert cfg2.peso_tfidf == 0.4
    assert paths2["output"] == "C:/out"


def test_arquivo_ausente_cai_nos_defaults(tmp_path):
    cfg, paths = carregar_config(tmp_path / "nao_existe.toml")
    assert cfg == Config()
    assert paths == {"input": "", "output": "", "template": "", "lista_padrao": ""}
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_config_io.py -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.config_io`.

- [ ] **Step 4: Implement**

Create `src/tdt/ui/__init__.py` (empty).

Create `src/tdt/ui/config_io.py`:

```python
"""Carrega/salva as configurações da UI em config.toml <-> Config.

ponytail: TOML plano por seções; tomllib (stdlib) lê, tomli_w escreve. Sem ORM.
"""

from __future__ import annotations

import tomllib
from dataclasses import replace
from pathlib import Path

import tomli_w

from tdt.config import Config

_PATHS_VAZIO = {"input": "", "output": "", "template": "", "lista_padrao": ""}

# campos escalares da Config que a UI edita
_ESCALARES = (
    "peso_tfidf", "peso_vetorial", "peso_fuzzy",
    "threshold_pct", "threshold_gap", "top_n_pct",
    "modelo_embedding", "k_vizinhos",
    "corrigir_typos", "remover_ids_equipamento",
)


def carregar_config(path: str | Path) -> tuple[Config, dict]:
    p = Path(path)
    if not p.exists():
        return Config(), dict(_PATHS_VAZIO)
    try:
        dados = tomllib.loads(p.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return Config(), dict(_PATHS_VAZIO)
    paths = {**_PATHS_VAZIO, **dados.get("paths", {})}
    knobs = {k: v for k, v in dados.get("config", {}).items() if k in _ESCALARES}
    pesos_regras = dados.get("pesos_regras")
    cfg = replace(Config(), **knobs)
    if isinstance(pesos_regras, dict):
        cfg = replace(cfg, pesos_regras={**Config().pesos_regras, **pesos_regras})
    return cfg, paths


def salvar_config(path: str | Path, config: Config, paths: dict) -> None:
    doc = {
        "paths": {**_PATHS_VAZIO, **paths},
        "config": {k: getattr(config, k) for k in _ESCALARES},
        "pesos_regras": dict(config.pesos_regras),
    }
    Path(path).write_text(tomli_w.dumps(doc), encoding="utf-8")
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_config_io.py -v`
Expected: PASS (both).

- [ ] **Step 6: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 5: `AppState` (estado compartilhado da UI)

**Files:**
- Create: `src/tdt/ui/estado.py`
- Test: `tests/test_ui_estado.py`

**Interfaces:**
- Produces: `AppState` com atributos mutáveis: `config: Config`, `paths: dict`, `modo: str`, `subestacao: str | None`, `flags: dict`, `resultado: ResultadoPipeline | None`, `registros: list[SignalRecord]` (cópia editável da lista decididos+revisão), `lista_padrao: ListaPadraoADMS | None`.
  - `AppState.carregar_resultado(res: ResultadoPipeline) -> None` — popula `registros` com decididos + registros dos itens de revisão.
  - `AppState.definir_sigla(indice: int, sigla: str) -> None` — `replace` o registro: `sigla_sinal=sigla`, `status="decidido"`, justificativa "editado manualmente".

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_estado.py
from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, ItemRevisao, ListaHomogenea,
    Modulo, ResultadoPipeline, SignalRecord, TipoSinal,
)
from tdt.ui.estado import AppState


def _rec(id_, sigla, status):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"), sigla_sinal=sigla, status=status,
    )


def test_carregar_resultado_junta_decididos_e_revisao():
    dec = _rec("a:1", "DJF1", "decidido")
    rev = _rec("a:2", None, "revisao")
    res = ResultadoPipeline(
        lista=ListaHomogenea(None, "DNP3", (dec,)),
        revisao=(ItemRevisao(rev, "score_baixo", ()),),
    )
    st = AppState()
    st.carregar_resultado(res)
    assert len(st.registros) == 2


def test_definir_sigla_marca_editado():
    st = AppState()
    st.registros = [_rec("a:2", None, "revisao")]
    st.definir_sigla(0, "DJF1")
    assert st.registros[0].sigla_sinal == "DJF1"
    assert st.registros[0].status == "decidido"
    assert "editado" in (st.registros[0].justificativa or "").lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_estado.py -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.estado`.

- [ ] **Step 3: Implement**

Create `src/tdt/ui/estado.py`:

```python
"""Estado compartilhado entre as telas da UI. Sem widgets, testável puro.

ponytail: dataclass mutável simples; as telas leem/escrevem aqui em vez de se
importarem entre si.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from tdt.config import Config
from tdt.contracts import ResultadoPipeline, SignalRecord
from tdt.dados.lista_padrao import ListaPadraoADMS


@dataclass
class AppState:
    config: Config = field(default_factory=Config)
    paths: dict = field(default_factory=lambda: {"input": "", "output": "", "template": "", "lista_padrao": ""})
    modo: str = "auto"
    subestacao: str | None = None
    flags: dict = field(default_factory=lambda: {"pular_revisao": False, "aprovar_acima_threshold": True})
    resultado: ResultadoPipeline | None = None
    registros: list[SignalRecord] = field(default_factory=list)
    lista_padrao: ListaPadraoADMS | None = None

    def carregar_resultado(self, res: ResultadoPipeline) -> None:
        self.resultado = res
        self.registros = list(res.lista.registros) + [it.registro for it in res.revisao]

    def definir_sigla(self, indice: int, sigla: str) -> None:
        r = self.registros[indice]
        self.registros[indice] = replace(
            r, sigla_sinal=sigla, status="decidido",
            justificativa="editado manualmente",
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_estado.py -v`
Expected: PASS (both).

- [ ] **Step 5: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 6: `ModeloSinais` (QAbstractTableModel)

**Files:**
- Create: `src/tdt/ui/modelo_tabela.py`
- Create: `tests/conftest.py` (offscreen Qt) — if absent
- Test: `tests/test_ui_modelo_tabela.py`

**Interfaces:**
- Consumes: `AppState` (registros, lista_padrao, diagnostico nos registros).
- Produces: `ModeloSinais(QAbstractTableModel)`:
  - `COLUNAS: list[str]` na ordem da spec §4.2.
  - `data(index, role)` para `DisplayRole` e `ToolTipRole` (tooltip na coluna Sinal = descrição ADMS via `lista_padrao.por_sigla`).
  - `definir_sigla(linha: int, sigla: str)` → delega a `AppState.definir_sigla` e emite `dataChanged`.

- [ ] **Step 1: Add offscreen Qt to conftest**

Create (or prepend to) `tests/conftest.py`:

```python
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_ui_modelo_tabela.py
from PySide6.QtCore import Qt
from tdt.contracts import (
    Descricoes, Diagnostico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais


def _rec():
    return SignalRecord(
        id="a:1", modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("Falha DJ", "FALHA DJ"),
        sigla_sinal="DJF1", status="decidido",
        diagnostico=Diagnostico({"DJF1": {"tfidf": 0.91, "vetorial": 0.84, "fuzzy": 0.72}}),
    )


def _state():
    st = AppState()
    st.registros = [_rec()]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha função 1", "BISI", None, None, "Discrete"),), ()
    )
    return st


def test_dimensoes_e_header(qtbot):
    m = ModeloSinais(_state())
    assert m.rowCount() == 1
    assert m.columnCount() == len(ModeloSinais.COLUNAS)
    assert m.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Sinal"


def test_sinal_e_score_aparecem():
    m = ModeloSinais(_state())
    sinal = m.data(m.index(0, 0), Qt.DisplayRole)
    assert sinal == "DJF1"
    col_emb = ModeloSinais.COLUNAS.index("Score embedding")
    assert "0.84" in str(m.data(m.index(0, col_emb), Qt.DisplayRole))


def test_tooltip_sinal_usa_descricao_adms():
    m = ModeloSinais(_state())
    tip = m.data(m.index(0, 0), Qt.ToolTipRole)
    assert "Disjuntor falha" in tip


def test_definir_sigla_atualiza_registro():
    st = _state()
    m = ModeloSinais(st)
    m.definir_sigla(0, "DJF2")
    assert st.registros[0].sigla_sinal == "DJF2"
    assert m.data(m.index(0, 0), Qt.DisplayRole) == "DJF2"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.modelo_tabela`.

- [ ] **Step 4: Implement**

Create `src/tdt/ui/modelo_tabela.py`:

```python
"""Modelo de tabela sobre os SignalRecords (decididos + revisão).

ponytail: um QAbstractTableModel fino que lê do AppState; sem cache, relê o
registro a cada data().
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from tdt.ui.estado import AppState

COLUNAS = [
    "Sinal", "Confiança", "Status", "Descrição bruta", "TKN bruto", "TKN norm.",
    "Tipo", "Escala", "Fase", "Endereço",
    "Score embedding", "Score tf-idf", "Score fuzzy", "Justificativa", "Motivo",
]


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
        if nome == "Descrição bruta":
            return rec.descricoes.bruta
        if nome == "TKN bruto":
            return rec.descricoes.bruta
        if nome == "TKN norm.":
            return rec.descricoes.normalizada
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
        if nome == "Motivo":
            return rec.justificativa or ""
        return ""

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self._estado.registros[index.row()]
        if role == Qt.DisplayRole:
            return self._texto(rec, index.column())
        if role == Qt.ToolTipRole and COLUNAS[index.column()] == "Sinal":
            lp = self._estado.lista_padrao
            if lp is not None and rec.sigla_sinal:
                sp = lp.por_sigla(rec.sigla_sinal)
                return sp.descricao if sp else None
        return None

    def definir_sigla(self, linha: int, sigla: str) -> None:
        self._estado.definir_sigla(linha, sigla)
        topo = self.index(linha, 0)
        fim = self.index(linha, len(COLUNAS) - 1)
        self.dataChanged.emit(topo, fim)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_modelo_tabela.py -v`
Expected: PASS (all four).

- [ ] **Step 6: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 7: `PipelineWorker` (QThread)

**Files:**
- Create: `src/tdt/ui/worker.py`
- Test: `tests/test_ui_worker.py`

**Interfaces:**
- Consumes: paths, `Config`, `modo`, `subestacao`, encoder factory, `pipeline.executar`.
- Produces: `PipelineWorker(QThread)` com sinais `log = Signal(str)`, `terminado = Signal(object)` (ResultadoPipeline), `erro = Signal(str)`; método `parar()` (cancelamento cooperativo). `run()` chama `executar(..., diagnostico=True, cancelado=self._cancelado, auditoria=Auditoria(on_evento=...))`.
- A função de execução é injetável (`executar_fn`) para testar sem rodar o pipeline real.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ui_worker.py
from tdt.config import Config
from tdt.contracts import ListaHomogenea, ResultadoPipeline
from tdt.auditoria import Auditoria
from tdt.ui.worker import PipelineWorker


def _resultado_vazio():
    return ResultadoPipeline(ListaHomogenea(None, "DNP3", ()), ())


def test_worker_emite_terminado(qtbot):
    def fake_exec(*a, auditoria=None, **k):
        if auditoria is not None:
            auditoria.evento("fake", "rodando", "INFO")
        return _resultado_vazio(), None

    w = PipelineWorker(
        paths={"input": "i", "output": "o", "template": "t", "lista_padrao": "lp"},
        config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: (lambda textos: None),
        executar_fn=fake_exec,
    )
    with qtbot.waitSignal(w.terminado, timeout=3000) as bloco:
        w.start()
    assert isinstance(bloco.args[0], ResultadoPipeline)
    w.wait()


def test_parar_sinaliza_cancelamento():
    w = PipelineWorker(
        paths={}, config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: None, executar_fn=lambda *a, **k: (None, None),
    )
    assert w._cancelado() is False
    w.parar()
    assert w._cancelado() is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_worker.py -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.worker`.

- [ ] **Step 3: Implement**

Create `src/tdt/ui/worker.py`:

```python
"""Worker em thread: roda o pipeline sem travar a UI; streaming de log e PARAR.

ponytail: cancelamento cooperativo por flag; nada de QThread.terminate (corrompe
estado). executar_fn é injetável para teste.
"""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt import pipeline


class PipelineWorker(QThread):
    log = Signal(str)
    terminado = Signal(object)
    erro = Signal(str)

    def __init__(self, paths, config: Config, modo, subestacao,
                 encoder_factory=criar_encoder, executar_fn=pipeline.executar):
        super().__init__()
        self._paths = paths
        self._config = config
        self._modo = modo
        self._subestacao = subestacao
        self._encoder_factory = encoder_factory
        self._executar_fn = executar_fn
        self._parar = threading.Event()

    def parar(self) -> None:
        self._parar.set()

    def _cancelado(self) -> bool:
        return self._parar.is_set()

    def run(self) -> None:
        try:
            aud = Auditoria(on_evento=lambda ev: self.log.emit(self._fmt(ev)))
            encoder = self._encoder_factory(self._config.modelo_embedding)
            resultado, _wb = self._executar_fn(
                self._paths["input"], self._paths["template"], self._paths["lista_padrao"],
                config=self._config, encoder=encoder, modo=self._modo,
                subestacao=self._subestacao, auditoria=aud,
                diagnostico=True, cancelado=self._cancelado,
            )
            self.terminado.emit(resultado)
        except Exception as e:  # ponytail: erro vira sinal; UI mostra e segue
            self.erro.emit(f"{type(e).__name__}: {e}")

    @staticmethod
    def _fmt(ev) -> str:
        return f"[{ev.nivel}] {ev.modulo}: {ev.msg}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_ui_worker.py -v`
Expected: PASS (both).

- [ ] **Step 5: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 8: Tela de Configurações (`tela_config.py`)

**Files:**
- Create: `src/tdt/ui/tela_config.py`
- Test: `tests/test_ui_smoke.py` (create; grows in Tasks 9–11)

**Interfaces:**
- Consumes: `AppState`, `config_io.salvar_config/carregar_config`.
- Produces: `TelaConfig(QWidget)` com sinal `voltar = Signal()`. Campos para paths, thresholds, pesos, modelo. `aplicar()` lê os widgets → `AppState.config`/`paths` e salva o `config.toml`. `recarregar()` repõe os widgets a partir do `AppState`.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/test_ui_smoke.py
from tdt.ui.estado import AppState
from tdt.ui.tela_config import TelaConfig


def test_tela_config_instancia_e_aplica(qtbot, tmp_path):
    st = AppState()
    st.paths = {"input": "", "output": str(tmp_path), "template": "t.xlsx", "lista_padrao": "lp.xlsx"}
    tela = TelaConfig(st, config_path=tmp_path / "config.toml")
    qtbot.addWidget(tela)
    tela.spin_pct.setValue(0.55)
    tela.aplicar()
    assert abs(st.config.threshold_pct - 0.55) < 1e-9
    assert (tmp_path / "config.toml").exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.tela_config`.

- [ ] **Step 3: Implement**

Create `src/tdt/ui/tela_config.py`:

```python
"""Tela de Configurações: pastas, thresholds, pesos, modelo. Persiste em TOML.

ponytail: form direto com widgets nomeados; sem binding genérico.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFormLayout, QLineEdit, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Signal

from tdt.ui.config_io import salvar_config
from tdt.ui.estado import AppState

_MODELOS = [
    "paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-base",
]


def _spin(maximo=1.0, passo=0.01):
    s = QDoubleSpinBox()
    s.setRange(0.0, maximo)
    s.setSingleStep(passo)
    s.setDecimals(3)
    return s


class TelaConfig(QWidget):
    voltar = Signal()

    def __init__(self, estado: AppState, config_path="config.toml"):
        super().__init__()
        self._estado = estado
        self._config_path = Path(config_path)
        form = QFormLayout()

        self.ed_input = QLineEdit()
        self.ed_output = QLineEdit()
        self.ed_template = QLineEdit()
        self.ed_lista = QLineEdit()
        form.addRow("Input padrão", self.ed_input)
        form.addRow("Output padrão", self.ed_output)
        form.addRow("Template DNP3", self.ed_template)
        form.addRow("Lista Padrão ADMS", self.ed_lista)

        self.spin_pct = _spin()
        self.spin_gap = _spin()
        self.spin_topn = _spin()
        form.addRow("threshold_pct", self.spin_pct)
        form.addRow("threshold_gap", self.spin_gap)
        form.addRow("top_n_pct", self.spin_topn)

        self.spin_tfidf = _spin()
        self.spin_vet = _spin()
        self.spin_fuzzy = _spin()
        form.addRow("peso_tfidf", self.spin_tfidf)
        form.addRow("peso_vetorial", self.spin_vet)
        form.addRow("peso_fuzzy", self.spin_fuzzy)

        self.combo_modelo = QComboBox()
        self.combo_modelo.addItems(_MODELOS)
        self.spin_k = QSpinBox()
        self.spin_k.setRange(1, 50)
        form.addRow("modelo_embedding", self.combo_modelo)
        form.addRow("k_vizinhos", self.spin_k)

        btn_salvar = QPushButton("Salvar")
        btn_salvar.clicked.connect(self.aplicar)
        btn_voltar = QPushButton("Voltar")
        btn_voltar.clicked.connect(self.voltar.emit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btn_salvar)
        layout.addWidget(btn_voltar)
        self.recarregar()

    def recarregar(self) -> None:
        c, p = self._estado.config, self._estado.paths
        self.ed_input.setText(p.get("input", ""))
        self.ed_output.setText(p.get("output", ""))
        self.ed_template.setText(p.get("template", ""))
        self.ed_lista.setText(p.get("lista_padrao", ""))
        self.spin_pct.setValue(c.threshold_pct)
        self.spin_gap.setValue(c.threshold_gap)
        self.spin_topn.setValue(c.top_n_pct)
        self.spin_tfidf.setValue(c.peso_tfidf)
        self.spin_vet.setValue(c.peso_vetorial)
        self.spin_fuzzy.setValue(c.peso_fuzzy)
        i = self.combo_modelo.findText(c.modelo_embedding)
        self.combo_modelo.setCurrentIndex(i if i >= 0 else 0)
        self.spin_k.setValue(c.k_vizinhos)

    def aplicar(self) -> None:
        self._estado.paths = {
            "input": self.ed_input.text(), "output": self.ed_output.text(),
            "template": self.ed_template.text(), "lista_padrao": self.ed_lista.text(),
        }
        self._estado.config = replace(
            self._estado.config,
            threshold_pct=self.spin_pct.value(),
            threshold_gap=self.spin_gap.value(),
            top_n_pct=self.spin_topn.value(),
            peso_tfidf=self.spin_tfidf.value(),
            peso_vetorial=self.spin_vet.value(),
            peso_fuzzy=self.spin_fuzzy.value(),
            modelo_embedding=self.combo_modelo.currentText(),
            k_vizinhos=self.spin_k.value(),
        )
        salvar_config(self._config_path, self._estado.config, self._estado.paths)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_smoke.py -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 9: Tela Inicial (`tela_inicial.py`)

**Files:**
- Create: `src/tdt/ui/tela_inicial.py`
- Test: append to `tests/test_ui_smoke.py`

**Interfaces:**
- Consumes: `AppState`, `PipelineWorker`.
- Produces: `TelaInicial(QWidget)` com sinais `abrir_config = Signal()`, `executou = Signal()` (emitido quando o worker termina, antes de trocar para Revisão). Botões EXECUTAR/PARAR; lê paths/modo/flags/subestação para o `AppState`; ao escolher input, popula a lista de sheets; recebe `log` do worker no painel LOG.
- O worker é injetável (`worker_factory`) para teste sem rodar o pipeline.

- [ ] **Step 1: Write the failing smoke test (append)**

```python
# append to tests/test_ui_smoke.py
from tdt.contracts import ListaHomogenea, ResultadoPipeline
from tdt.ui.tela_inicial import TelaInicial


class _WorkerFake:
    def __init__(self, *a, **k):
        from PySide6.QtCore import Signal, QObject
    # substituído abaixo por implementação real de sinais


def test_tela_inicial_instancia(qtbot):
    st = AppState()
    tela = TelaInicial(st)
    qtbot.addWidget(tela)
    assert tela.btn_executar.text().upper().startswith("EXEC")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py::test_tela_inicial_instancia -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.tela_inicial`.

- [ ] **Step 3: Implement**

Create `src/tdt/ui/tela_inicial.py`:

```python
"""Tela Inicial: configura e dispara o pipeline; LOG ao vivo; PARAR.

ponytail: lê sheets com openpyxl read_only; worker injetável p/ teste.
"""

from __future__ import annotations

import openpyxl
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton, QRadioButton,
    QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from tdt.ui.estado import AppState
from tdt.ui.worker import PipelineWorker

_MODOS = [("Automático (detecta pelo header)", "auto"),
          ("Homogêneo", "homogeneo"),
          ("Não homogêneo", "nao-homogeneo")]


class TelaInicial(QWidget):
    abrir_config = Signal()
    executou = Signal()

    def __init__(self, estado: AppState, worker_factory=PipelineWorker):
        super().__init__()
        self._estado = estado
        self._worker_factory = worker_factory
        self._worker = None

        self.ed_input = QLabel(estado.paths.get("input", "") or "Input: —")
        self.ed_output = QLabel("Output: " + (estado.paths.get("output", "") or "—"))
        btn_in = QPushButton("Input…"); btn_in.clicked.connect(self._escolher_input)
        btn_out = QPushButton("Output…"); btn_out.clicked.connect(self._escolher_output)

        self.combo_proto = QComboBox(); self.combo_proto.addItem("DNP3")
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
        self.chk_aprovar.setChecked(estado.flags.get("aprovar_acima_threshold", True))

        self.combo_sub = QComboBox(); self.combo_sub.setEditable(True)
        self.combo_sub.addItem("Auto detect")

        self.lista_sheets = QListWidget()

        self.btn_executar = QPushButton("EXECUTAR"); self.btn_executar.clicked.connect(self._executar)
        self.btn_parar = QPushButton("PARAR"); self.btn_parar.clicked.connect(self._parar)
        self.btn_parar.setEnabled(False)
        btn_cfg = QPushButton("⚙"); btn_cfg.clicked.connect(self.abrir_config.emit)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True)

        col_esq = QVBoxLayout()
        for w in (self.ed_input, btn_in, self.ed_output, btn_out, QLabel("Protocolo:"),
                  self.combo_proto, QLabel("Método de processamento:")):
            col_esq.addWidget(w)
        col_esq.addLayout(cx_modo)
        col_esq.addWidget(QLabel("Flags:")); col_esq.addWidget(self.chk_pular); col_esq.addWidget(self.chk_aprovar)

        col_meio = QVBoxLayout()
        col_meio.addWidget(QLabel("Subestação")); col_meio.addWidget(self.combo_sub)
        col_meio.addWidget(QLabel("Sheets")); col_meio.addWidget(self.lista_sheets)

        col_dir = QVBoxLayout()
        topo = QHBoxLayout(); topo.addStretch(); topo.addWidget(btn_cfg)
        botoes = QHBoxLayout(); botoes.addWidget(self.btn_executar); botoes.addWidget(self.btn_parar)
        col_dir.addLayout(topo); col_dir.addLayout(botoes)
        col_dir.addWidget(QLabel("LOG")); col_dir.addWidget(self.log)

        raiz = QHBoxLayout(self)
        raiz.addLayout(col_esq); raiz.addLayout(col_meio); raiz.addLayout(col_dir)

    def _escolher_input(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Input .xlsx", filter="Excel (*.xlsx)")
        if not caminho:
            return
        self._estado.paths["input"] = caminho
        self.ed_input.setText("Input: " + caminho)
        self._popular_sheets(caminho)

    def _escolher_output(self):
        caminho = QFileDialog.getExistingDirectory(self, "Pasta de output")
        if caminho:
            self._estado.paths["output"] = caminho
            self.ed_output.setText("Output: " + caminho)

    def _popular_sheets(self, caminho):
        self.lista_sheets.clear()
        try:
            wb = openpyxl.load_workbook(caminho, read_only=True)
            nomes = wb.sheetnames
            wb.close()
        except Exception as e:  # ponytail: input ruim só esvazia a lista + loga
            self.log.appendPlainText(f"[ERRO] não li sheets: {e}")
            return
        for nome in nomes:
            it = QListWidgetItem(nome)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
            it.setCheckState(Qt.Checked)
            self.lista_sheets.addItem(it)

    def _coletar(self):
        self._estado.modo = _MODOS[self.grupo_modo.checkedId()][1]
        self._estado.flags["pular_revisao"] = self.chk_pular.isChecked()
        self._estado.flags["aprovar_acima_threshold"] = self.chk_aprovar.isChecked()
        sub = self.combo_sub.currentText()
        self._estado.subestacao = None if sub == "Auto detect" else sub

    def _executar(self):
        self._coletar()
        self.btn_executar.setEnabled(False); self.btn_parar.setEnabled(True)
        self._worker = self._worker_factory(
            paths=self._estado.paths, config=self._estado.config,
            modo=self._estado.modo, subestacao=self._estado.subestacao,
        )
        self._worker.log.connect(self.log.appendPlainText)
        self._worker.erro.connect(lambda m: self.log.appendPlainText(f"[ERRO] {m}"))
        self._worker.erro.connect(self._fim)
        self._worker.terminado.connect(self._terminado)
        self._worker.start()

    def _terminado(self, resultado):
        self._estado.carregar_resultado(resultado)
        self._fim()
        self.executou.emit()

    def _parar(self):
        if self._worker is not None:
            self._worker.parar()
            self.log.appendPlainText("[AVISO] PARAR solicitado")

    def _fim(self, *args):
        self.btn_executar.setEnabled(True); self.btn_parar.setEnabled(False)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_smoke.py::test_tela_inicial_instancia -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 10: Tela de Revisão (`tela_revisao.py`)

**Files:**
- Create: `src/tdt/ui/tela_revisao.py`
- Test: append to `tests/test_ui_smoke.py`

**Interfaces:**
- Consumes: `AppState`, `ModeloSinais`, `pipeline.gerar_tdt`.
- Produces: `TelaRevisao(QWidget)` com sinal `voltar = Signal()`. À esquerda o painel de detalhe (campos empilhados + lista de candidatos clicável + busca ADMS); à direita a `QTableView` com o `ModeloSinais`, esticando na vertical (`setSizePolicy` Expanding, `horizontalHeader().setStretchLastSection(False)`, `setHorizontalScrollMode(ScrollPerPixel)`). Selecionar linha atualiza o painel; clicar candidato/escolher sigla chama `modelo.definir_sigla`. Botão "aprovar / gerar TDT" chama `pipeline.gerar_tdt` e salva na pasta de output.
- `carregar()` (re)cria o modelo a partir do `AppState` e dá `reset` na view.

- [ ] **Step 1: Write the failing smoke test (append)**

```python
# append to tests/test_ui_smoke.py
from tdt.contracts import (
    Descricoes as _D, Enderecamento as _E, Modulo as _M, SignalRecord as _SR, TipoSinal as _T,
)
from tdt.ui.tela_revisao import TelaRevisao


def test_tela_revisao_popula_tabela(qtbot):
    st = AppState()
    st.registros = [
        _SR(id="a:1", modulo=_M("M", "sheet_name"), tipo_sinal=_T("Discrete", False, "Input"),
            enderecamento=_E("DNP3", (1,)), descricoes=_D("d", "D"),
            sigla_sinal="DJF1", status="decidido")
    ]
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    assert tela.tabela.model().rowCount() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py::test_tela_revisao_popula_tabela -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.tela_revisao`.

- [ ] **Step 3: Implement**

Create `src/tdt/ui/tela_revisao.py`:

```python
"""Tela de Revisão: tabela rica + painel de detalhe; aprova e gera o TDT.

ponytail: painel reflete a linha selecionada; edição vai pro AppState via modelo.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QMessageBox, QPushButton,
    QSizePolicy, QTableView, QVBoxLayout, QWidget,
)

from tdt import pipeline
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais


class TelaRevisao(QWidget):
    voltar = Signal()

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado
        self._linha = -1

        btn_voltar = QPushButton("← Voltar"); btn_voltar.clicked.connect(self.voltar.emit)
        btn_gerar = QPushButton("aprovar / gerar TDT"); btn_gerar.clicked.connect(self._gerar)

        # painel de detalhe
        self.lbl_campos = QLabel("Selecione um sinal"); self.lbl_campos.setWordWrap(True)
        self.lista_candidatos = QListWidget()
        self.lista_candidatos.itemClicked.connect(self._escolher_candidato)
        self.busca = QLineEdit(); self.busca.setPlaceholderText("buscar qualquer sinal ADMS…")
        self.busca.returnPressed.connect(self._aplicar_busca)
        painel = QVBoxLayout()
        painel.addWidget(QLabel("Detalhe")); painel.addWidget(self.lbl_campos)
        painel.addWidget(QLabel("Candidatos")); painel.addWidget(self.lista_candidatos)
        painel.addWidget(self.busca); painel.addWidget(btn_gerar)
        cofre = QWidget(); cofre.setLayout(painel); cofre.setFixedWidth(260)

        # tabela
        self.tabela = QTableView()
        self.tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabela.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.tabela.setSelectionBehavior(QTableView.SelectRows)

        corpo = QHBoxLayout(); corpo.addWidget(cofre); corpo.addWidget(self.tabela, 1)
        raiz = QVBoxLayout(self)
        raiz.addWidget(btn_voltar)
        raiz.addLayout(corpo, 1)

    def carregar(self) -> None:
        self._modelo = ModeloSinais(self._estado)
        self.tabela.setModel(self._modelo)
        self.tabela.selectionModel().currentRowChanged.connect(self._linha_mudou)

    def _linha_mudou(self, atual, _anterior):
        self._linha = atual.row()
        self._atualizar_painel()

    def _atualizar_painel(self):
        if self._linha < 0:
            return
        r = self._estado.registros[self._linha]
        self.lbl_campos.setText(
            f"Sinal: {r.sigla_sinal or '—'}\nStatus: {r.status}\n"
            f"Tipo: {r.tipo_sinal.categoria}/{r.tipo_sinal.direcao}\n"
            f"Fase: {r.eletrico.fase or '—'}\n"
            f"Endereço: {';'.join(str(i) for i in r.enderecamento.indices)}\n"
            f"Descrição: {r.descricoes.bruta}"
        )
        self.lista_candidatos.clear()
        for c in r.candidatos:
            self.lista_candidatos.addItem(f"{c.sigla}  ({c.score:.2f})")

    def _escolher_candidato(self, item):
        if self._linha < 0:
            return
        sigla = item.text().split()[0]
        self._modelo.definir_sigla(self._linha, sigla)
        self._atualizar_painel()

    def _aplicar_busca(self):
        if self._linha < 0:
            return
        sigla = self.busca.text().strip().upper()
        lp = self._estado.lista_padrao
        if lp is not None and lp.por_sigla(sigla) is None:
            QMessageBox.warning(self, "Sigla", f"{sigla} não está na Lista Padrão ADMS")
            return
        self._modelo.definir_sigla(self._linha, sigla)
        self._atualizar_painel()

    def _gerar(self):
        out = Path(self._estado.paths.get("output") or ".")
        try:
            wb = pipeline.gerar_tdt(
                self._estado.registros, self._estado.paths["template"],
                self._estado.lista_padrao, subestacao=self._estado.subestacao,
            )
            destino = out / "TDT.xlsx"
            wb.save(destino)
        except Exception as e:  # ponytail: erro de geração vira diálogo, não crash
            QMessageBox.critical(self, "Erro ao gerar", f"{type(e).__name__}: {e}")
            return
        QMessageBox.information(self, "TDT", f"Gerado: {destino}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_smoke.py::test_tela_revisao_popula_tabela -v`
Expected: PASS.

- [ ] **Step 5: Checkpoint — full suite green**

Run: `python -m pytest -q`
Expected: all green.

---

## Task 11: `MainWindow` + `ui_main` + tema + navegação

**Files:**
- Create: `src/tdt/ui/app.py`
- Create: `src/tdt/ui/tema.qss`
- Create: `src/tdt/ui_main.py`
- Modify: `pyproject.toml` (console script `tdt-ui`)
- Test: append to `tests/test_ui_smoke.py`

**Interfaces:**
- Consumes: todas as telas, `AppState`, `config_io.carregar_config`.
- Produces: `MainWindow(QMainWindow)` com `QStackedWidget` (Inicial/Revisão/Config) e navegação por sinais; `criar_app()` monta tudo; `tdt.ui_main.main()` é o entry-point.

- [ ] **Step 1: Write the failing smoke test (append)**

```python
# append to tests/test_ui_smoke.py
from tdt.ui.app import MainWindow


def test_mainwindow_navega(qtbot, tmp_path):
    st = AppState()
    janela = MainWindow(st, config_path=tmp_path / "config.toml")
    qtbot.addWidget(janela)
    # começa na Inicial
    assert janela.stack.currentWidget() is janela.tela_inicial
    # abrir config e voltar
    janela.tela_inicial.abrir_config.emit()
    assert janela.stack.currentWidget() is janela.tela_config
    janela.tela_config.voltar.emit()
    assert janela.stack.currentWidget() is janela.tela_inicial
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ui_smoke.py::test_mainwindow_navega -v`
Expected: FAIL — `ModuleNotFoundError: tdt.ui.app`.

- [ ] **Step 3: Implement the window**

Create `src/tdt/ui/app.py`:

```python
"""Janela principal: QStackedWidget com as três telas e a navegação.

ponytail: o único módulo que conhece todas as telas (como o pipeline.py).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget

from tdt.ui.config_io import carregar_config
from tdt.ui.estado import AppState
from tdt.ui.tela_config import TelaConfig
from tdt.ui.tela_inicial import TelaInicial
from tdt.ui.tela_revisao import TelaRevisao

_TEMA = Path(__file__).with_name("tema.qss")


class MainWindow(QMainWindow):
    def __init__(self, estado: AppState, config_path="config.toml"):
        super().__init__()
        self.setWindowTitle("Projeto TDT")
        self._estado = estado
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.tela_inicial = TelaInicial(estado)
        self.tela_revisao = TelaRevisao(estado)
        self.tela_config = TelaConfig(estado, config_path=config_path)
        for t in (self.tela_inicial, self.tela_revisao, self.tela_config):
            self.stack.addWidget(t)

        self.tela_inicial.abrir_config.connect(lambda: self.stack.setCurrentWidget(self.tela_config))
        self.tela_inicial.executou.connect(self._mostrar_revisao)
        self.tela_revisao.voltar.connect(lambda: self.stack.setCurrentWidget(self.tela_inicial))
        self.tela_config.voltar.connect(lambda: self.stack.setCurrentWidget(self.tela_inicial))
        self.stack.setCurrentWidget(self.tela_inicial)

    def _mostrar_revisao(self):
        self.tela_revisao.carregar()
        self.stack.setCurrentWidget(self.tela_revisao)


def criar_app(config_path="config.toml"):
    app = QApplication.instance() or QApplication([])
    if _TEMA.exists():
        app.setStyleSheet(_TEMA.read_text(encoding="utf-8"))
    estado = AppState()
    estado.config, estado.paths = carregar_config(config_path)
    janela = MainWindow(estado, config_path=config_path)
    return app, janela
```

- [ ] **Step 4: Create the theme**

Create `src/tdt/ui/tema.qss` (starter; cores no topo, ajuste fino é verificação manual):

```css
QWidget { background: #7d7796; color: #f3f1f7; font-family: "Consolas","Courier New",monospace; font-size: 13px; }
QPushButton { background: #5a5475; border: 1px solid #46415f; border-radius: 8px; padding: 6px 12px; }
QPushButton:hover { background: #6c6688; }
QPushButton:disabled { color: #b5b1c4; }
QLineEdit, QComboBox, QPlainTextEdit, QListWidget, QDoubleSpinBox, QSpinBox {
  background: #544f6e; border: 1px solid #46415f; border-radius: 6px; padding: 4px; color: #f3f1f7;
}
QTableView { background: #b8b4c4; color: #2c2a36; gridline-color: #9c98ab; }
QHeaderView::section { background: #e6e3ee; color: #2c2a36; padding: 4px; border: 1px solid #9c98ab; }
QScrollBar:vertical, QScrollBar:horizontal { background: #6c6688; border-radius: 6px; }
QScrollBar::handle { background: #46415f; border-radius: 6px; }
```

- [ ] **Step 5: Create the entry-point and console script**

Create `src/tdt/ui_main.py`:

```python
"""Entry-point da UI: python -m tdt.ui_main (ou console_script tdt-ui)."""

from __future__ import annotations

import sys

from tdt.ui.app import criar_app


def main() -> int:
    app, janela = criar_app()
    janela.resize(1100, 650)
    janela.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

In `pyproject.toml`, under `[project.scripts]`:

```toml
tdt = "tdt.cli:main"
tdt-ui = "tdt.ui_main:main"
```

- [ ] **Step 6: Run test to verify it passes**

Run: `python -m pytest tests/test_ui_smoke.py::test_mainwindow_navega -v`
Expected: PASS.

- [ ] **Step 7: Checkpoint — full suite green + manual launch**

Run: `python -m pytest -q`
Expected: all green (122 + UI tests).
Manual: `python -m tdt.ui_main` opens the window; verify the three screens, theme, and that EXECUTAR with a real input runs and lands on Revisão. (Visual fine-tuning of `tema.qss` is manual.)

---

## Self-Review (vs spec)

**Spec coverage:**
- §2 stack PySide6 → Tasks 4–11. ✓
- §3 layout/módulos → cada arquivo tem sua task. ✓
- §4.1 Tela Inicial (input/output/protocolo/método/flags/subestação/sheets/EXECUTAR-PARAR/LOG/⚙) → Task 9. ✓
- §4.2 Tela Revisão (tabela rica, colunas, scroll, estica vertical, edição inline+painel, busca ADMS, tooltip, aprovar/gerar) → Tasks 6 + 10. ✓
- §4.3 Configurações (pastas/thresholds/pesos/modelo + salvar) → Task 8. ✓
- §4.4 Flags (efeito) → coletadas em Task 9; *nota:* o efeito "pular revisão" (gerar direto) e "aprovar acima do threshold" (pré-aprovar) são lidos para o AppState mas o branch de aplicá-los na navegação fica no MainWindow — **adicionado abaixo como ajuste**.
- §5 fluxo de dados → AppState (Task 5) + worker (Task 7) + app (Task 11). ✓
- §6 extensões pipeline (Diagnostico, cancelado, on_evento, gerar_tdt; por_sigla já existia) → Tasks 1–3. ✓
- §7 worker → Task 7. ✓
- §8 tema → Task 11. ✓
- §9 erros → diálogos/sinais nas Tasks 9–10; checagens do SP1 reusadas. ✓
- §10 testes → cada task TDD; smoke em conftest offscreen. ✓

**Ajuste (efeito das flags, §4.4) — fold no Task 11, Step 3 `_mostrar_revisao`:**

```python
    def _mostrar_revisao(self):
        if self._estado.flags.get("pular_revisao"):
            self.tela_revisao.carregar()
            self.tela_revisao._gerar()   # gera direto, sem revisar
            return
        if self._estado.flags.get("aprovar_acima_threshold"):
            pct = self._estado.config.threshold_pct
            from dataclasses import replace
            self._estado.registros = [
                replace(r, status="decidido") if (r.candidatos and r.candidatos[0].score >= pct) else r
                for r in self._estado.registros
            ]
        self.tela_revisao.carregar()
        self.stack.setCurrentWidget(self.tela_revisao)
```

(Implemente este corpo no lugar do `_mostrar_revisao` simples do Step 3.)

**Placeholder scan:** sem TBD/TODO; o `_WorkerFake` esboçado no Task 9 Step 1 não é usado (o teste real instancia a tela sem rodar worker) — **remover esse trecho morto ao escrever o teste**; manter só `test_tela_inicial_instancia`.

**Type consistency:** `definir_sigla(indice/linha, sigla)` consistente entre `AppState` e `ModeloSinais`; `executar(..., diagnostico=, cancelado=)` igual nas Tasks 1–2 e no worker (Task 7); `gerar_tdt(registros, template, lp, subestacao)` igual na Task 3 e Task 10; `por_sigla` (existente) usado em Tasks 6 e 10.
