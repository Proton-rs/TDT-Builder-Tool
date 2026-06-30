# SP-B — Fidelidade de campo da TDT (fases + TRF03) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Garantir que a coluna `Phases` da TDT nunca saia inválida (`"F"`) nem vazia (default `ABC`, como a TDT real), e que as sheets `TRF3_*` saiam como módulo `TRF03`.

**Architecture:** Três correções pequenas e independentes em pontos já existentes — (B1) `pipeline._com_fase` mapeia o sentinela `"F"` de `fase_da_sigla` para `"ABC"` antes de gravar no modelo; (B2) `engine_tdt` ganha um helper puro `_fase_saida` (fallback ABC para `None` ou valor fora de `FASES`) usado nos dois pontos de emissão de `Phases`; (B3) alias literal `TRF3_*`→`TRF03` em `Config.mapa_sheet_modulo`. Nenhuma toca matching/scoring/pareamento.

**Tech Stack:** Python 3.14, pytest 9, dataclasses frozen (`dataclasses.replace`), openpyxl.

## Global Constraints

- **Não tocar `fase_da_sigla`** ([motor_regras.py:179](../../../src/tdt/motor_regras.py)) — o retorno `"F"` é o sentinela de fase genérica usado pelo scoring de `r3_fase`; alterá-lo quebra a comparação de fase no matching. A correção é só no limite de escrita do modelo/saída.
- **Default ABC é regra de saída**, não de análise — não altera `eletrico.fase` no modelo (exceto o mapeamento `"F"`→`"ABC"` de B1, que é correção de valor inválido) nem o scoring.
- **Imutabilidade:** `SignalRecord`/`Eletrico` são `@dataclass(frozen=True)` — usar `dataclasses.replace`, nunca mutação in-place.
- **Domínio de fase:** `FASES = ("ABC", "AB", "BC", "CA", "A", "B", "C", "N")` ([normalizador.py:72](../../../src/tdt/normalizacao/normalizador.py)); já importado em `engine_tdt.py:26`.
- **TDD obrigatório:** teste primeiro (RED→GREEN). **Benchmark como gate:** `PYTHONPATH=src python bench/benchmark.py` não pode regredir (B não toca matching — `combo(calib-minmax)` deve ficar 69%/80%).

---

## File Structure

- **Modify** `src/tdt/pipeline.py` (`_com_fase`, linha ~153) — B1: mapear `"F"`→`"ABC"`.
- **Modify** `src/tdt/engine_tdt.py` — B2: helper `_fase_saida` + usar nos dois `"Phases"` (linhas ~172 discreto e ~220 analógico).
- **Modify** `src/tdt/config.py` (`mapa_sheet_modulo`) — B3: `"TRF3P"`/`"TRF3A"` → `"TRF03"`.
- **Modify** `tests/test_pipeline.py` — teste de B1.
- **Modify** `tests/test_engine_tdt.py` — teste de B2 (importa `_fase_saida`).
- **Modify** `tests/test_identidade_modulo.py` — teste de B3.

---

### Task 1: B1 — `_com_fase` mapeia o `"F"` genérico para `"ABC"`

**Files:**
- Modify: `src/tdt/pipeline.py:153-159` (`_com_fase`)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `fase_da_sigla(sigla) -> str | None` (motor_regras), que devolve `"F"` para proteção genérica trifásica.
- Produces: `_com_fase(rec) -> SignalRecord` com `eletrico.fase` ∈ `FASES ∪ {None}` (nunca `"F"`).

- [ ] **Step 1: Write the failing test**

Acrescentar em `tests/test_pipeline.py` (no topo, junto dos imports já existentes, garantir `from dataclasses import replace` e os contracts; reutilizar helpers se houver — senão usar o construtor direto abaixo):

```python
from tdt.pipeline import _com_fase
from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)


def _rec_sigla(sigla: str) -> SignalRecord:
    return SignalRecord(
        id="t:1",
        modulo=Modulo("AL15", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("x", "x"),
        eletrico=Eletrico(),  # fase=None
        sigla_sinal=sigla,
    )


def test_com_fase_mapeia_F_generico_para_ABC():
    # PRTF/50F1 -> fase_da_sigla devolve "F" (genérica trifásica) -> ABC
    assert _com_fase(_rec_sigla("PRTF")).eletrico.fase == "ABC"
    assert _com_fase(_rec_sigla("50F1")).eletrico.fase == "ABC"


def test_com_fase_preserva_fase_especifica():
    assert _com_fase(_rec_sigla("51N")).eletrico.fase == "N"
    assert _com_fase(_rec_sigla("51A")).eletrico.fase == "A"
```

> Confirme os nomes dos campos de `SignalRecord`/`Eletrico` lendo `src/tdt/contracts.py` antes de rodar — se `SignalRecord` exigir outros campos obrigatórios, ajuste o construtor do helper. `sigla_sinal` é o campo que `_com_fase` lê.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_pipeline.py -k com_fase -v`
Expected: FAIL — `test_com_fase_mapeia_F_generico_para_ABC` quebra com `eletrico.fase == "F"` (≠ `"ABC"`). O teste de fase específica já passa.

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/pipeline.py`, alterar `_com_fase`:

```python
def _com_fase(rec: SignalRecord) -> SignalRecord:
    """Grava a fase derivada da sigla decidida em ``eletrico.fase`` (se vazia).

    ``fase_da_sigla`` devolve ``"F"`` como sentinela de fase genérica (usado no
    scoring de ``r3_fase``); proteção genérica trifásica = ``ABC`` na saída.
    """
    if rec.sigla_sinal and rec.eletrico.fase is None:
        f = fase_da_sigla(rec.sigla_sinal.upper())
        if f == "F":
            f = "ABC"
        if f:
            return replace(rec, eletrico=replace(rec.eletrico, fase=f))
    return rec
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_pipeline.py -k com_fase -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline.py
git commit -m "fix(pipeline): _com_fase mapeia F genérico para ABC (SP-B)"
```

---

### Task 2: B2 — `_fase_saida` no engine (default ABC + guard de domínio)

**Files:**
- Modify: `src/tdt/engine_tdt.py` (novo helper + duas linhas `"Phases"`: ~172 e ~220)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `FASES` (já importado em `engine_tdt.py:26`).
- Produces: `_fase_saida(fase: str | None) -> str` — devolve `fase` se ∈ `FASES`, senão `"ABC"`.

- [ ] **Step 1: Write the failing test**

Acrescentar em `tests/test_engine_tdt.py` (adicionar `_fase_saida` à lista de imports `from tdt.engine_tdt import (...)`):

```python
def test_fase_saida_default_abc_para_none():
    assert _fase_saida(None) == "ABC"


def test_fase_saida_fallback_abc_para_valor_invalido():
    assert _fase_saida("F") == "ABC"
    assert _fase_saida("XYZ") == "ABC"


def test_fase_saida_preserva_fase_valida():
    assert _fase_saida("A") == "A"
    assert _fase_saida("ABC") == "ABC"
    assert _fase_saida("N") == "N"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_engine_tdt.py -k fase_saida -v`
Expected: FAIL — `ImportError: cannot import name '_fase_saida'`.

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/engine_tdt.py`, adicionar o helper (perto do topo, após os imports / junto dos outros `_helpers`):

```python
def _fase_saida(fase: str | None) -> str:
    """Fase para a coluna TDT ``Phases``: default ``ABC`` quando vazia, e
    fallback ``ABC`` para qualquer valor fora do domínio ``FASES`` (guard de
    domínio — o ADMS rejeita fase inválida)."""
    return fase if fase in FASES else "ABC"
```

E trocar, **nos dois** pontos de emissão, `"Phases": rec.eletrico.fase` por:

```python
        "Phases": _fase_saida(rec.eletrico.fase),
```

(uma ocorrência em `_valores_discreto` ~linha 172, outra em `_valores_analog` ~linha 220 — `grep -n '"Phases": rec.eletrico.fase' src/tdt/engine_tdt.py` lista as duas).

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_engine_tdt.py -k fase_saida -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "fix(engine_tdt): _fase_saida default ABC + guard de domínio (SP-B)"
```

---

### Task 3: B3 — alias `TRF3_*` → `TRF03`

**Files:**
- Modify: `src/tdt/config.py` (`mapa_sheet_modulo`)
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `resolver_modulo(sheet_name, rows, config)` (estratégia 1 = alias por `"".join(_tokens(sheet_name))` em `config.mapa_sheet_modulo`).
- Produces: `mapa_sheet_modulo["TRF3P"] == "TRF03"`, `["TRF3A"] == "TRF03"`.

- [ ] **Step 1: Write the failing test**

Acrescentar em `tests/test_identidade_modulo.py` (junto dos demais testes de `resolver_modulo`):

```python
def test_resolver_modulo_trf3_vira_trf03():
    cfg = Config()
    assert resolver_modulo("TRF3_P", [], cfg).nome == "TRF03"
    assert resolver_modulo("TRF3_A", [], cfg).nome == "TRF03"
    assert resolver_modulo("TRF3_P", [], cfg).confianca == "alta"


def test_resolver_modulo_trf1_trf2_sem_padding():
    # quirk de dado é só do TRF3 (real tem TRF03 mas TRF1/TRF2 sem pad)
    cfg = Config()
    assert resolver_modulo("TRF-1", [], cfg).nome == "TRF1"
    assert resolver_modulo("TRF-2", [], cfg).nome == "TRF2"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k trf -v`
Expected: FAIL — `test_resolver_modulo_trf3_vira_trf03` dá `"TRF3"` (≠ `"TRF03"`). O teste TRF1/TRF2 já passa.

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/config.py`, dentro do `default_factory` de `mapa_sheet_modulo`, acrescentar as duas entradas (o comentário do bloco já existe; só somar as chaves):

```python
            "01F1GTAP": "LTGTA", "01F1GTAA": "LTGTA",
            "01F1KGCP": "LTKGC", "01F1KGCA": "LTKGC",
            "87BAT": "87BAT",
            "87BMT1": "87BMT1",
            "87BMT2": "87BMT2",
            "IB23KV": "IB",
            "PSACACC": "PSACA",
            "TRF3P": "TRF03", "TRF3A": "TRF03",
        }
```

> Copie as chaves já existentes verbatim e some apenas a última linha — confirme lendo `src/tdt/config.py` para não duplicar nem perder entradas.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_identidade_modulo.py -k trf -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/config.py tests/test_identidade_modulo.py
git commit -m "feat(config): alias TRF3_* -> TRF03 em mapa_sheet_modulo (SP-B)"
```

---

### Task 4: Validação integrada — suite, benchmark e TDT real

**Files:** nenhum (verificação).

- [ ] **Step 1: Suite completa**

Run: `PYTHONPATH=src python -m pytest -q`
Expected: PASS (todos os testes existentes + os 7 novos). Se algum teste antigo fixava `Phases` esperando `None`/`"F"`, ajustar o teste para o novo comportamento (ABC) e anotar no commit.

- [ ] **Step 2: Benchmark (gate)**

Run: `PYTHONPATH=src python bench/benchmark.py`
Expected: `combo(calib-minmax)` em `acc@1=69% prec@dec=80%` — inalterado (B não toca matching).

- [ ] **Step 3: Conferir contra a TDT real (re-gerar a GTD)**

Run:
```bash
PYTHONPATH=src python -m tdt.cli "docs/GTD - Lista de Pontos V11.xlsx" \
  --output output/OUTPUT_TDT.xlsx --lista-padrao "docs/Pontos Padrao ADMS_v2.xlsx" \
  --subestacao GTD --modo nao-homogeneo
```
Depois, inspecionar `output/OUTPUT_TDT.xlsx`, sheet `DNP3_DiscreteSignals` (4 linhas de header, dados a partir da 5ª, coluna 15 = `Phases`, coluna 0 = `Signal Name`):

```python
import openpyxl
wb = openpyxl.load_workbook("output/OUTPUT_TDT.xlsx", read_only=True, data_only=True)
ws = wb["DNP3_DiscreteSignals"]
rows = [r for r in list(ws.iter_rows(values_only=True))[4:] if r[0] is not None]
from collections import Counter
print("Phases:", dict(Counter(r[15] for r in rows)))
print("F:", sum(1 for r in rows if r[15] == "F"))        # esperado 0
print("vazio:", sum(1 for r in rows if not r[15]))        # esperado 0
print("TRF03:", sum(1 for r in rows if "_TRF03_" in str(r[0])))  # > 0
wb.close()
```
Expected: `F: 0`, `vazio: 0`, `ABC` dominante, `TRF03 > 0`.

- [ ] **Step 4: Commit (se a re-geração da TDT for versionada)**

```bash
git add output/OUTPUT_TDT.xlsx
git commit -m "chore: re-gera OUTPUT_TDT da GTD com fidelidade de fase (SP-B)"
```

> Se `output/` for git-ignored, pular este commit — a verificação do Step 3 basta.

---

## Self-Review (preenchido)

- **Cobertura do spec:** B1 (Task 1) ✓; B2 helper+guard+default (Task 2) ✓; B3 TRF03 (Task 3) ✓; validação contra TDT real + benchmark (Task 4) ✓. Critérios de aceite 1-6 cobertos.
- **`fase_da_sigla` intacta** (critério 3): nenhuma task a modifica — só `_com_fase` e o engine. ✓
- **Placeholders:** nenhum — todo passo traz código real e comando com saída esperada.
- **Consistência de tipos:** `_com_fase(rec)->SignalRecord`; `_fase_saida(str|None)->str`; `resolver_modulo(...).nome:str`. Nomes batem entre tasks e com o código atual.
- **Escopo deferido (consistente com a spec):** nomenclatura `BP/TSA/SE` fora; sem plumbing de auditoria no guard (guard puro).
