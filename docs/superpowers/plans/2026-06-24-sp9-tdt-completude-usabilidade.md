# SP9 — TDT: Output Coordinates, Dropdowns, Measurement Type/Display Unit — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** TDT gerada (1) nunca duplica índice único de comando simples nas Output Coordinates, (2) ganha dropdowns (Data Validation) nas colunas Phases/Direction/Remote Point Type, (3) preenche Measurement Type/Display Unit pra sinais analógicos com essa info na Lista Padrão.

**Architecture:** Tudo em `src/tdt/engine_tdt.py` (mesma família de funções `_valores`/`_valores_analog`/geração de sheet) + 2 campos novos em `src/tdt/dados/lista_padrao.py`.

**Tech Stack:** openpyxl (`DataValidation` já disponível, sem dependência nova).

## Global Constraints

- Não inventar domínio de dropdown sem grounding (ex. `Side` fica de fora — só `"None"` confirmado).
- Sem entrada na tabela PT→EN de Measurement Type: fica `None` (comportamento de hoje, sem regressão).
- Double-bit real (2 índices) não pode ser afetado pela duplicação de comando simples.

---

### Task 1: Output Coordinates não duplica comando simples

**Files:**
- Modify: `src/tdt/engine_tdt.py` (função `_valores()`, trecho de `coords_saida`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Produces: `_coords_comando(indices: tuple[int, ...]) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine_tdt.py (acrescentar)
from tdt.engine_tdt import _coords_comando


def test_coords_comando_duplica_indice_unico():
    assert _coords_comando((1500,)) == "1500;1500"


def test_coords_comando_preserva_multiplos_indices():
    assert _coords_comando((1500, 1501)) == "1500;1501"
```

E um teste de integração (ajustar pro helper de fixture de `SignalRecord` já usado neste arquivo):

```python
def test_valores_comando_orfao_duplica_coordenada_unica(...):
    # rec com tipo_sinal.direcao="Output", enderecamento.indices=(1500,)
    valores = _valores(rec, subestacao=None, padrao=padrao_fake)
    assert valores["Output Coordinates"] == "1500;1500"


def test_valores_double_bit_nao_duplica(...):
    # rec com tipo_sinal.is_double_bit=True, enderecamento.indices=(100, 101), direcao="Input"
    valores = _valores(rec, subestacao=None, padrao=padrao_fake)
    assert valores["Output Coordinates"] is None  # não é comando, não tem coords_saida
```

Reaproveite os helpers de `SignalRecord`/`SinalPadrao` fake já existentes em `tests/test_engine_tdt.py` (leia o arquivo antes — não recrie dataclasses de teste).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py -k coords_comando -v`
Expected: FAIL com `ImportError: cannot import name '_coords_comando'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/engine_tdt.py — função nova, perto de _valores()
def _coords_comando(indices: tuple[int, ...]) -> str:
    if len(indices) == 1:
        return f"{indices[0]};{indices[0]}"
    return ";".join(str(i) for i in indices)
```

Em `_valores()`, trocar:

```python
    if direcao == "Output":
        coords_entrada = None
        coords_saida = coords
    else:
        coords_entrada = coords
        coords_saida = ";".join(str(i) for i in rec.enderecamento.indices_saida)
```

por:

```python
    if direcao == "Output":
        coords_entrada = None
        coords_saida = _coords_comando(rec.enderecamento.indices)
    else:
        coords_entrada = coords
        coords_saida = _coords_comando(rec.enderecamento.indices_saida) if rec.enderecamento.indices_saida else ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_engine_tdt.py -k coords -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "fix(tdt): Output Coordinates duplica indice unico de comando simples (N;N)"
```

---

### Task 2: Dropdowns (Data Validation) em Phases/Direction/Remote Point Type

**Files:**
- Modify: `src/tdt/normalizador.py` (expor `FASES` público em vez de `_FASES`)
- Modify: `src/tdt/engine_tdt.py` (`_escrever_sheet()`, função nova `_adicionar_dv_lista`)
- Test: `tests/test_normalizador.py`, `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `tdt.normalizador.FASES: tuple[str, ...]` (renomeado de `_FASES`).
- Consumes: `engine_tdt._DIRECAO: dict[str, str]` (já existe).
- Produces: `_adicionar_dv_lista(ws, colunas: dict[str, int], ultima_linha: int) -> None`.

- [ ] **Step 1: Renomear `_FASES` para `FASES` (público)**

Run: `grep -rn "_FASES" src/ tests/` — listar todos os usos antes de renomear.

Renomear a constante em `src/tdt/normalizador.py` de `_FASES` para `FASES` e atualizar todos os usos internos do mesmo arquivo. Rodar a suíte completa pra confirmar que nenhum outro módulo dependia do nome privado:

Run: `python -m pytest -q`
Expected: todos os testes continuam verdes (renome interno, sem mudança de comportamento).

- [ ] **Step 2: Write the failing test pro dropdown**

```python
# tests/test_engine_tdt.py (acrescentar)
from openpyxl import Workbook
from tdt.engine_tdt import _adicionar_dv_lista


def test_adicionar_dv_lista_cria_data_validation_nas_colunas_esperadas():
    wb = Workbook()
    ws = wb.active
    colunas = {"Phases": 1, "Direction": 2, "Remote Point Type": 3, "Outra": 4}
    _adicionar_dv_lista(ws, colunas, ultima_linha=10)
    dvs = list(ws.data_validations.dataValidation)
    assert len(dvs) == 3
    alvos = {str(dv.sqref) for dv in dvs}
    assert any("A5:A10" in a for a in alvos)  # Phases na coluna A, linha 5 (PRIMEIRA_LINHA_DADOS) até 10
    formulas = {dv.formula1 for dv in dvs}
    assert any("Read" in f and "Write" in f for f in formulas)
```

Confirme o valor real de `PRIMEIRA_LINHA_DADOS` em `engine_tdt.py` antes de fixar `"A5"` no teste — ajuste pro valor real se for diferente de 5.

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py -k dv_lista -v`
Expected: FAIL com `ImportError: cannot import name '_adicionar_dv_lista'`

- [ ] **Step 4: Write minimal implementation**

```python
# src/tdt/engine_tdt.py
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from tdt.normalizador import FASES

_DV_LISTAS: dict[str, tuple[str, ...]] = {
    "Phases": FASES,
    "Direction": tuple(_DIRECAO.values()),
    "Remote Point Type": ("Status", "Analog"),
}


def _adicionar_dv_lista(ws, colunas: dict[str, int], ultima_linha: int) -> None:
    for display, valores in _DV_LISTAS.items():
        col = colunas.get(display)
        if col is None:
            continue
        letra = get_column_letter(col)
        dv = DataValidation(type="list", formula1=f'"{",".join(valores)}"', allow_blank=True)
        dv.add(f"{letra}{PRIMEIRA_LINHA_DADOS}:{letra}{ultima_linha}")
        ws.add_data_validation(dv)
```

Em `_escrever_sheet()`, depois da chamada existente a `_expandir_dv(ws, ultima_linha=ultima)`:

```python
    if ultima >= PRIMEIRA_LINHA_DADOS:
        _expandir_cf(ws, ultima_linha=ultima)
        _expandir_dv(ws, ultima_linha=ultima)
        _adicionar_dv_lista(ws, colunas, ultima_linha=ultima)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_engine_tdt.py -v && python -m pytest tests/test_normalizador.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tdt/normalizador.py src/tdt/engine_tdt.py tests/test_engine_tdt.py tests/test_normalizador.py
git commit -m "feat(tdt): dropdowns (Data Validation) nas colunas Phases/Direction/Remote Point Type"
```

---

### Task 3: `SinalPadrao.tipo_medicao`/`unidade_exibicao` lidos da Lista Padrão

**Files:**
- Modify: `src/tdt/dados/lista_padrao.py` (dataclass `SinalPadrao`, chamada de `_ler_sheet` pra `AnalogSignals`)
- Test: `tests/test_lista_padrao.py`

**Interfaces:**
- Produces: `SinalPadrao.tipo_medicao: str | None`, `SinalPadrao.unidade_exibicao: str | None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_lista_padrao.py (acrescentar — reaproveitar helper de workbook fake já existente no arquivo)
def test_le_tipo_medicao_e_unidade_exibicao_de_analog_signals(tmp_path):
    # montar workbook fake com sheet "AnalogSignals" contendo colunas
    # "SINAL", "DESCRIÇÃO NOVA", "SIGNAL TYPE", "DIREÇÃO DO FLUXO",
    # "TIPO DE MEDIÇÃO", "UNIDADE DE EXIBIÇÃO" — reaproveitar o padrão de
    # fixture já usado pelos outros testes deste arquivo pra AnalogSignals.
    lp = ListaPadraoADMS.carregar(caminho_fake)
    sp = lp.por_sigla("IA")
    assert sp.tipo_medicao == "CORRENTE"
    assert sp.unidade_exibicao == "A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_lista_padrao.py -k tipo_medicao -v`
Expected: FAIL com `AttributeError: 'SinalPadrao' object has no attribute 'tipo_medicao'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/dados/lista_padrao.py
@dataclass(frozen=True)
class SinalPadrao:
    sigla: str
    descricao: str
    signal_type: str
    direction: str | None
    mm: str | None
    categoria: str
    estados_brutos: str | None = None
    valores_scada: tuple[int, ...] = ()
    tipo_medicao: str | None = None
    unidade_exibicao: str | None = None
```

No ponto onde `_ler_sheet` é chamado para `AnalogSignals` (mesmo bloco que hoje passa `"mm": None, "estados": None, "valores": None`), adicionar:

```python
ana = _ler_sheet(
    wb["AnalogSignals"], "Analog",
    {
        "sigla": "SINAL", "descricao": "DESCRIÇÃO NOVA", "signal_type": "SIGNAL TYPE",
        "direction": "DIREÇÃO DO FLUXO", "mm": None, "estados": None, "valores": None,
        "tipo_medicao": "TIPO DE MEDIÇÃO", "unidade_exibicao": "UNIDADE DE EXIBIÇÃO",
    },
)
```

E em `_ler_sheet()`, no `SinalPadrao(...)` construído por linha, adicionar:

```python
                tipo_medicao=get("tipo_medicao"),
                unidade_exibicao=get("unidade_exibicao"),
```

(`get()` já trata chave ausente no `idx` retornando `None` — sem mudança na função `get` interna.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_lista_padrao.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/dados/lista_padrao.py tests/test_lista_padrao.py
git commit -m "feat(lista-padrao): le TIPO DE MEDICAO/UNIDADE DE EXIBICAO de AnalogSignals"
```

---

### Task 4: `_valores_analog()` preenche Measurement Type / Display Unit

**Files:**
- Modify: `src/tdt/engine_tdt.py` (função `_valores_analog()`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `SinalPadrao.tipo_medicao`, `SinalPadrao.unidade_exibicao` (Task 3).
- Produces: `_measurement_type(sp: "SinalPadrao | None") -> str | None`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_engine_tdt.py
from tdt.engine_tdt import _measurement_type


def test_measurement_type_traduz_pt_para_en():
    sp = SinalPadrao(sigla="IA", descricao="", signal_type="Current", direction=None,
                      mm=None, categoria="Analog", tipo_medicao="CORRENTE", unidade_exibicao="A")
    assert _measurement_type(sp) == "Current"


def test_measurement_type_none_sem_tipo_medicao():
    sp = SinalPadrao(sigla="IA", descricao="", signal_type="Current", direction=None,
                      mm=None, categoria="Analog")
    assert _measurement_type(sp) is None


def test_valores_analog_preenche_measurement_type_e_display_unit(...):
    # rec com sigla_sinal="IA", padrao_fake.por_sigla("IA") devolve sp com
    # tipo_medicao="CORRENTE", unidade_exibicao="A"
    valores = _valores_analog(rec, subestacao=None, padrao=padrao_fake)
    assert valores["Measurement Type"] == "Current"
    assert valores["Display Unit"] == "A"


def test_valores_analog_sem_tipo_medicao_fica_none(...):
    valores = _valores_analog(rec_sem_info, subestacao=None, padrao=padrao_fake)
    assert valores.get("Measurement Type") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py -k measurement -v`
Expected: FAIL com `ImportError: cannot import name '_measurement_type'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/engine_tdt.py
_MEASUREMENT_TYPE_PT_EN: dict[str, str] = {
    "CORRENTE": "Current",
    "TENSÃO": "Voltage",
    "POTÊNCIA ATIVA": "ActivePower",
    "POTÊNCIA REATIVA": "ReactivePower",
    "TEMPERATURA": "Temperature",
}


def _measurement_type(sp) -> str | None:
    if sp is None or not sp.tipo_medicao:
        return None
    return _MEASUREMENT_TYPE_PT_EN.get(sp.tipo_medicao.strip().upper())
# ponytail: tabela cobre os 5 tipos confirmados no export real; ampliar quando aparecer outro tipo de medicao real nos dados.
```

Em `_valores_analog()`, adicionar ao dict de retorno (depois de `"Remote Point Type": "Analog",`):

```python
        "Measurement Type": _measurement_type(sp),
        "Display Unit": sp.unidade_exibicao if sp and sp.unidade_exibicao not in (None, "-") else None,
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_engine_tdt.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite to check no regression**

Run: `python -m pytest -q`

- [ ] **Step 6: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(tdt): Measurement Type/Display Unit em sinais analogicos (PT->EN)"
```

---

## Self-Review Notes

- Cobertura: Output Coordinates (1), dropdowns (2), leitura de Lista Padrão (3), escrita Measurement Type/Display Unit (4). Todos os 5 critérios de aceite do spec têm task correspondente.
- Risco: valor real de `PRIMEIRA_LINHA_DADOS` em `engine_tdt.py` precisa ser confirmado antes de fixar no teste da Task 2 (assumido como 5 no spec original, mas Step 2 manda verificar).
