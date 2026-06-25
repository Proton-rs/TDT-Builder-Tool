# TDT — Escopo Analógico + Completude de Campos: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trazer sinais analógicos para a classificação e geração do TDT, e preencher os campos da TDT que hoje saem vazios mas têm valor derivável.

**Architecture:** O pipeline ganha um segundo conjunto de scorers (analógico) e roteia cada sinal pelo conjunto da sua categoria; sinais de categoria estruturalmente incerta passam pelos dois (dual-pass). A engine escreve as duas sheets (`DNP3_DiscreteSignals`, `DNP3_AnalogSignals`) reusando os mesmos helpers de expansão de tabela/formatação. Campos novos são derivados de dados já no pipeline (nome do sinal, sigla decidida, módulo, subestação) ou da Lista Padrão ADMS.

**Tech Stack:** Python 3.14, openpyxl, scikit-learn (TF-IDF), faiss, rapidfuzz, pytest. UI em PySide6 (não tocada aqui).

## Global Constraints

- Contratos são `@dataclass(frozen=True)`; enriquecimento é funcional via `dataclasses.replace`, nunca mutação in-place.
- Defaults novos de `Config` preservam o comportamento atual (mesmos valores numéricos de hoje).
- Testes existentes devem permanecer verdes: a suíte inteira passa hoje com **170 passed**.
- Nomes de coluna da Lista Padrão e do template são case-insensitive por display name (row 4 no template; row 1 na Lista Padrão). Nunca por índice.
- Comando de execução da suíte: `python -m pytest -q` (a partir da raiz do projeto). Testes individuais: `python -m pytest tests/test_x.py::nome -v`.
- TDD: teste falhando antes da implementação; commits frequentes por tarefa.

---

## File Structure

| Arquivo | Responsabilidade | Mudança |
|---|---|---|
| `src/tdt/dados/lista_padrao.py` | Ler a Lista Padrão ADMS | + colunas `FUNÇÃO`/`VALOR` em `SinalPadrao` (origem do Normal Value) |
| `src/tdt/motor_regras.py` | Regras de domínio sobre scores | `_fase_da_sigla` → pública `fase_da_sigla` |
| `src/tdt/contracts.py` | Tipos compartilhados | + `TipoSinal.categoria_confiavel` |
| `src/tdt/config.py` | Knobs calibráveis | + thresholds/pesos `*_analog` |
| `src/tdt/estruturador.py` | Monta `SignalRecord` da planilha | marca `categoria_confiavel=False` sem pista |
| `src/tdt/pipeline.py` | Orquestra tudo | scorers analógicos + dual-pass + persistir fase |
| `src/tdt/engine_tdt.py` | Escreve o TDT | campos novos (`_valores`) + sheet analógica (`_valores_analog`) |

Ordem das tarefas: completude de campos primeiro (1–3, menores e independentes), depois suporte analógico (4–7), que reusa os helpers de campo da Tarefa 3.

---

### Task 1: Normal Value — Lista Padrão lê FUNÇÃO/VALOR

**Files:**
- Modify: `src/tdt/dados/lista_padrao.py`
- Test: `tests/test_lista_padrao.py`

**Interfaces:**
- Produces: `SinalPadrao` ganha dois campos: `estados_brutos: str | None` (ex. `"Transit;NORMAL;ATUADO;Error"`) e `valores_scada: tuple[int, ...]` (ex. `(0, 1, 2, 3)`). Consumido pela Tarefa 3 para derivar `Normal Value`.

- [ ] **Step 1: Write the failing test**

Adicione em `tests/test_lista_padrao.py`:

```python
def test_sinal_discreto_tem_estados_e_valores(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    # "20T" é RelayTrip com FUNÇÃO "Transit;NORMAL;ATUADO;Error" e VALOR "0;1;2;3"
    sp = lp.por_sigla("20T")
    assert sp is not None
    assert sp.estados_brutos == "Transit;NORMAL;ATUADO;Error"
    assert sp.valores_scada == (0, 1, 2, 3)


def test_analogico_sem_estados(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    in61 = lp.por_sigla("IN61")
    assert in61.estados_brutos is None
    assert in61.valores_scada == ()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_lista_padrao.py::test_sinal_discreto_tem_estados_e_valores -v`
Expected: FAIL — `TypeError` (campo inexistente) ou `AttributeError: 'SinalPadrao' object has no attribute 'estados_brutos'`.

- [ ] **Step 3: Add fields to SinalPadrao**

Em `src/tdt/dados/lista_padrao.py`, adicione os campos ao dataclass (com defaults para não quebrar construções existentes):

```python
@dataclass(frozen=True)
class SinalPadrao:
    sigla: str
    descricao: str
    signal_type: str
    direction: str | None
    mm: str | None
    categoria: str  # "Discrete" | "Analog"
    estados_brutos: str | None = None
    valores_scada: tuple[int, ...] = ()
```

- [ ] **Step 4: Parse the new columns in _ler_sheet**

Em `_ler_sheet`, dentro do loop, após calcular `def get(chave)`, adicione a derivação e passe aos campos novos:

```python
        valores_raw = get("valores")
        try:
            valores = tuple(int(p) for p in valores_raw.split(";")) if valores_raw else ()
        except ValueError:
            valores = ()  # "#N/A" ou formato inesperado

        sinais.append(
            SinalPadrao(
                sigla=sigla,
                descricao=get("descricao") or "",
                signal_type=get("signal_type") or "",
                direction=get("direction"),
                mm=get("mm"),
                categoria=categoria,
                estados_brutos=get("estados"),
                valores_scada=valores,
            )
        )
```

- [ ] **Step 5: Map the columns in carregar**

Em `ListaPadraoADMS.carregar`, no mapa do `DiscreteSignals`, adicione as duas chaves; no `AnalogSignals`, mapeie para `None` (colunas ausentes lá):

```python
            disc = _ler_sheet(
                wb["DiscreteSignals"],
                "Discrete",
                {
                    "sigla": "SINAL",
                    "descricao": "DESCRIÇÃO NOVA",
                    "signal_type": "SIGNAL TYPE",
                    "direction": "DIRECTION",
                    "mm": "MM",
                    "estados": "FUNÇÃO",
                    "valores": "VALOR",
                },
            )
            ana = _ler_sheet(
                wb["AnalogSignals"],
                "Analog",
                {
                    "sigla": "SINAL",
                    "descricao": "DESCRIÇÃO NOVA",
                    "signal_type": "SIGNAL TYPE",
                    "direction": "DIREÇÃO DO FLUXO",
                    "mm": None,
                    "estados": None,
                    "valores": None,
                },
            )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_lista_padrao.py -v`
Expected: PASS (todos, incluindo os 4 antigos).

- [ ] **Step 7: Commit**

```bash
git add src/tdt/dados/lista_padrao.py tests/test_lista_padrao.py
git commit -m "feat(lista_padrao): lê FUNÇÃO/VALOR p/ Normal Value"
```

---

### Task 2: Persistir a fase do sinal na decisão

**Files:**
- Modify: `src/tdt/motor_regras.py` (renomear `_fase_da_sigla` → `fase_da_sigla`)
- Modify: `src/tdt/pipeline.py` (helper `_com_fase` + chamada em `_classificar_sinal`)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Produces: `motor_regras.fase_da_sigla(sigla: str) -> str | None` (pública). `pipeline._com_fase(rec: SignalRecord) -> SignalRecord` grava `rec.eletrico.fase` quando há fase na sigla e o campo está vazio.

- [ ] **Step 1: Write the failing test**

Adicione em `tests/test_pipeline.py`:

```python
from dataclasses import replace as _replace

from tdt.contracts import (
    Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.pipeline import _com_fase


def _rec_min(sigla):
    return SignalRecord(
        id="s:1",
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(sigla, sigla),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_com_fase_deriva_de_sigla_neutro():
    out = _com_fase(_rec_min("51N"))
    assert out.eletrico.fase == "N"


def test_com_fase_sem_fase_mantem_none():
    out = _com_fase(_rec_min("FCOM"))
    assert out.eletrico.fase is None


def test_com_fase_nao_sobrescreve_existente():
    base = _rec_min("51N")
    base = _replace(base, eletrico=_replace(base.eletrico, fase="ABC"))
    out = _com_fase(base)
    assert out.eletrico.fase == "ABC"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py::test_com_fase_deriva_de_sigla_neutro -v`
Expected: FAIL — `ImportError: cannot import name '_com_fase'`.

- [ ] **Step 3: Make fase_da_sigla public in motor_regras**

Em `src/tdt/motor_regras.py`, renomeie a função `_fase_da_sigla` para `fase_da_sigla` (assinatura e corpo idênticos) e atualize o único chamador interno em `r3_fase`:

```python
def fase_da_sigla(sigla: str) -> str | None:
    # Remove dígito de estágio à direita (67N1 -> 67N) p/ ler a fase, não o estágio.
    base = sigla[:-1] if len(sigla) > 1 and sigla[-1] in "1234" else sigla
    if base.endswith("N"):
        return "N"
    for f in ("ABC", "AB", "BC", "CA"):
        if base.endswith(f):
            return f
    if base.endswith("F"):
        return "F"  # fase pura genérica
    if base and base[-1] in ("A", "B", "C"):
        return base[-1]
    return None
```

Em `r3_fase`, troque `fase_cand = _fase_da_sigla(cand.sigla.upper())` por `fase_cand = fase_da_sigla(cand.sigla.upper())`.

- [ ] **Step 4: Add _com_fase to pipeline**

Em `src/tdt/pipeline.py`, importe a função e adicione o helper. No topo, junto aos imports de `tdt`, acrescente:

```python
from tdt.motor_regras import fase_da_sigla
```

E defina o helper (antes de `_classificar_sinal`):

```python
def _com_fase(rec: SignalRecord) -> SignalRecord:
    """Grava a fase derivada da sigla decidida em ``eletrico.fase`` (se vazia)."""
    if rec.sigla_sinal and rec.eletrico.fase is None:
        f = fase_da_sigla(rec.sigla_sinal.upper())
        if f:
            return replace(rec, eletrico=replace(rec.eletrico, fase=f))
    return rec
```

- [ ] **Step 5: Call _com_fase on the decided path**

Em `_classificar_sinal`, no final, antes do `return decidido`, envolva a decisão:

```python
    if decidido.status == "decidido":
        decidido = _com_fase(decidido)
    return decidido
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m pytest tests/test_pipeline.py tests/test_motor_regras.py -v`
Expected: PASS (incluindo os testes legados de `motor_regras`).

- [ ] **Step 7: Commit**

```bash
git add src/tdt/motor_regras.py src/tdt/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): persiste fase derivada da sigla no registro decidido"
```

---

### Task 3: Campos novos da TDT discreta

**Files:**
- Modify: `src/tdt/engine_tdt.py`
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `SinalPadrao.signal_type`, `.estados_brutos`, `.valores_scada` (Tarefa 1).
- Produces (helpers puros, reusados pela Tarefa 7):
  - `_eh_alimentador(modulo_nome: str | None) -> bool`
  - `_aor_group(subestacao: str | None, alimentador: bool) -> str | None`
  - `_remote_unit(subestacao: str | None) -> str | None`
  - `_device_mapping(nome: str, sigla: str, eh_protecao: bool) -> str`
  - `_normal_value(sp: SinalPadrao | None) -> int | None`
  - `_alias_hoje() -> str` (data EUA `MM/DD/YYYY`)

- [ ] **Step 1: Write the failing unit tests for helpers**

Adicione em `tests/test_engine_tdt.py` (importe os helpers no topo):

```python
import re
from datetime import date

from tdt.dados.lista_padrao import SinalPadrao
from tdt.engine_tdt import (
    _eh_alimentador, _aor_group, _remote_unit, _device_mapping,
    _normal_value, _alias_hoje,
)


def test_eh_alimentador():
    assert _eh_alimentador("AL11") is True
    assert _eh_alimentador("AL 12") is True
    assert _eh_alimentador("3") is False
    assert _eh_alimentador("TR1") is False
    assert _eh_alimentador(None) is False


def test_aor_group():
    assert _aor_group("IMA", True) == "IMA Distr"
    assert _aor_group("IMA", False) == "IMA Trans"
    assert _aor_group(None, True) is None


def test_remote_unit():
    assert _remote_unit("IMA") == "UTR_IMA_1"
    assert _remote_unit(None) is None


def test_device_mapping():
    assert _device_mapping("IMA_3_20T", "20T", True) == "IMA_3_PROT_20T"
    assert _device_mapping("IMA_3_DJ", "DJ", False) == "IMA_3_DJ"
    assert _device_mapping("BATA", "BATA", True) == "PROT_BATA"


def test_normal_value():
    sp = SinalPadrao("20T", "", "RelayTrip", None, None, "Discrete",
                     estados_brutos="Transit;NORMAL;ATUADO;Error",
                     valores_scada=(0, 1, 2, 3))
    assert _normal_value(sp) == 1
    assert _normal_value(None) is None
    sp_sem = SinalPadrao("X", "", "Custom", None, None, "Discrete")
    assert _normal_value(sp_sem) is None


def test_alias_hoje_formato_eua():
    assert re.fullmatch(r"\d{2}/\d{2}/\d{4}", _alias_hoje())
    assert _alias_hoje() == date.today().strftime("%m/%d/%Y")
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py::test_eh_alimentador -v`
Expected: FAIL — `ImportError: cannot import name '_eh_alimentador'`.

- [ ] **Step 3: Implement the helpers**

Em `src/tdt/engine_tdt.py`, adicione no topo o import de data e os helpers (após `_nome_hierarquico`):

```python
from datetime import date
```

```python
def _eh_alimentador(modulo_nome: str | None) -> bool:
    if not modulo_nome:
        return False
    norm = modulo_nome.replace(" ", "").upper()
    return bool(re.match(r"^AL\d", norm))


def _aor_group(subestacao: str | None, alimentador: bool) -> str | None:
    if not subestacao:
        return None
    return f"{subestacao} {'Distr' if alimentador else 'Trans'}"


def _remote_unit(subestacao: str | None) -> str | None:
    return f"UTR_{subestacao}_1" if subestacao else None


def _device_mapping(nome: str, sigla: str, eh_protecao: bool) -> str:
    if not eh_protecao:
        return nome
    # insere PROT_ antes da sigla final (nome termina em "..._{sigla}" ou == sigla)
    if nome.endswith(sigla):
        return nome[: len(nome) - len(sigla)] + f"PROT_{sigla}"
    return nome


def _normal_value(sp: "SinalPadrao | None") -> int | None:
    if sp is None or not sp.estados_brutos or not sp.valores_scada:
        return None
    estados = sp.estados_brutos.split(";")
    try:
        i = estados.index("NORMAL")
    except ValueError:
        return None
    return sp.valores_scada[i] if i < len(sp.valores_scada) else None


def _alias_hoje() -> str:
    return date.today().strftime("%m/%d/%Y")
```

- [ ] **Step 4: Run helper tests to verify they pass**

Run: `python -m pytest tests/test_engine_tdt.py -k "alimentador or aor_group or remote_unit or device_mapping or normal_value or alias_hoje" -v`
Expected: PASS.

- [ ] **Step 5: Write the failing integration test for the row**

Adicione em `tests/test_engine_tdt.py`:

```python
def test_campos_novos_no_output(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    # row 5 = "IMA_3_DJ" (modulo "3" não é alimentador -> Trans)
    assert ws.cell(5, col["Side"]).value == "None"
    assert ws.cell(5, col["Output Register"]).value is False
    assert ws.cell(5, col["Remote Point Type"]).value == "Status"
    assert ws.cell(5, col["Remote Point Name"]).value == "IMA_3_DJ"
    assert ws.cell(5, col["Signal AOR Group"]).value == "IMA Trans"
    assert ws.cell(5, col["Device Mapping"]).value == "IMA_3_DJ"
    assert ws.cell(5, col["Remote Unit"]).value == "UTR_IMA_1"
    assert ws.cell(5, col["Remote Point Custom ID"]).value == "IMA_3_DJ_UTR_IMA_1"
    import re as _re
    assert _re.fullmatch(r"\d{2}/\d{2}/\d{4}", ws.cell(5, col["Remote Point Alias"]).value)
```

- [ ] **Step 6: Run to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py::test_campos_novos_no_output -v`
Expected: FAIL — `assert None == 'None'` (campos ainda vazios).

- [ ] **Step 7: Wire the fields into _valores**

Em `_valores`, antes do `return`, calcule os derivados e adicione as chaves ao dict. Insira após a linha `nome = _nome_hierarquico(...)`:

```python
    alimentador = _eh_alimentador(rec.modulo.nome)
    eh_prot = bool(sp and sp.signal_type == "RelayTrip")
    remote_unit = _remote_unit(subestacao)
    rp_custom = f"{nome}_{remote_unit}" if remote_unit else None
```

E no dict retornado, adicione (mantendo as chaves já existentes):

```python
        "Side": "None",
        "Output Register": False,
        "Remote Point Type": "Status",
        "Remote Point Name": nome,
        "Phases": rec.eletrico.fase,
        "Signal AOR Group": _aor_group(subestacao, alimentador),
        "Device Mapping": _device_mapping(nome, rec.sigla_sinal or "?", eh_prot),
        "Remote Unit": remote_unit,
        "Remote Point Custom ID": rp_custom,
        "Remote Point Alias": _alias_hoje(),
        "Normal Value": _normal_value(sp),
```

(A chave `"Phases"` já existe no dict atual — substitua a linha existente, não duplique.)

- [ ] **Step 8: Run the full engine suite**

Run: `python -m pytest tests/test_engine_tdt.py -v`
Expected: PASS (novos + 17 existentes).

- [ ] **Step 9: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine_tdt): preenche campos derivados (Side, AOR, Device Mapping, Remote Unit/Point, Normal Value, Alias)"
```

---

### Task 4: `categoria_confiavel` no contrato e no estruturador

**Files:**
- Modify: `src/tdt/contracts.py`
- Modify: `src/tdt/estruturador.py`
- Test: `tests/test_estruturador.py`

**Interfaces:**
- Produces: `TipoSinal.categoria_confiavel: bool = True`. O estruturador marca `False` quando a categoria daquela linha veio do default (nem coluna `Tipo`, nem marcador de seção encontrado).

- [ ] **Step 1: Write the failing test**

Adicione em `tests/test_estruturador.py` (use o estilo de chamada já presente no arquivo — verifique a assinatura de `estruturar` e os fixtures existentes no arquivo antes de escrever; o teste abaixo monta `rows`/`MapaColunas` diretamente):

```python
from tdt.config import Config
from tdt.contracts import MapaColunas
from tdt.estruturador import estruturar


def test_categoria_incerta_sem_pista():
    # header na row 1; uma linha de dados sem marcador de seção e sem coluna Tipo
    rows = [
        ("Descrição", "Endereço"),
        ("ALARME GENERICO", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert len(recs) == 1
    assert recs[0].tipo_sinal.categoria_confiavel is False


def test_categoria_confiavel_com_marcador():
    rows = [
        ("Descrição", "Endereço"),
        ("Analógicas", ""),          # marcador de seção -> categoria confiável
        ("CORRENTE FASE A", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].tipo_sinal.categoria == "Analog"
    assert recs[0].tipo_sinal.categoria_confiavel is True
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_estruturador.py::test_categoria_incerta_sem_pista -v`
Expected: FAIL — `AttributeError: 'TipoSinal' object has no attribute 'categoria_confiavel'`.

- [ ] **Step 3: Add the field to TipoSinal**

Em `src/tdt/contracts.py`:

```python
@dataclass(frozen=True)
class TipoSinal:
    categoria: str  # "Discrete" | "Analog" | "DiscreteAnalog"
    is_double_bit: bool
    direcao: str  # "Input" | "Output" | "InputOutput"
    categoria_confiavel: bool = True
```

- [ ] **Step 4: Track whether a hint was seen, in estruturador**

Em `src/tdt/estruturador.py`, dentro de `estruturar`, rastreie se a seção atual veio de um marcador. Inicialize ao lado de `secao`:

```python
    secao: tuple[str, str] = ("Discrete", "Input")  # default
    secao_explicita = False  # virou True quando um marcador de seção foi lido
```

No bloco do marcador, marque a flag:

```python
        if _eh_marcador(row, col0):
            secao = _classificar(row[col0])
            secao_explicita = True
            continue
```

Ao montar o registro, calcule a confiança (confiável se a coluna Tipo classificou OU houve marcador de seção):

```python
        cat_dir = _classificar(row[c_tipo]) if c_tipo is not None and c_tipo < len(row) else None
        categoria, direcao = cat_dir or secao
        confiavel = cat_dir is not None or secao_explicita
```

E passe ao `TipoSinal`:

```python
                tipo_sinal=TipoSinal(categoria, is_double_bit=False, direcao=direcao,
                                     categoria_confiavel=confiavel),
```

- [ ] **Step 5: Run to verify it passes**

Run: `python -m pytest tests/test_estruturador.py -v`
Expected: PASS (novos + existentes).

- [ ] **Step 6: Commit**

```bash
git add src/tdt/contracts.py src/tdt/estruturador.py tests/test_estruturador.py
git commit -m "feat(estruturador): marca categoria_confiavel=False sem pista de categoria"
```

---

### Task 5: Knobs de Config para analógicos

**Files:**
- Modify: `src/tdt/config.py`
- Test: `tests/test_calibracao.py` (ou crie `tests/test_config.py` se preferir isolar)

**Interfaces:**
- Produces: `Config` ganha `peso_tfidf_analog`, `peso_vetorial_analog`, `peso_fuzzy_analog`, `threshold_pct_analog`, `threshold_gap_analog`, com os mesmos defaults dos discretos. Consumido pela Tarefa 6.

- [ ] **Step 1: Write the failing test**

Crie `tests/test_config.py`:

```python
from tdt.config import Config


def test_defaults_analog_iguais_aos_discretos():
    c = Config()
    assert c.peso_tfidf_analog == c.peso_tfidf
    assert c.peso_vetorial_analog == c.peso_vetorial
    assert c.peso_fuzzy_analog == c.peso_fuzzy
    assert c.threshold_pct_analog == c.threshold_pct
    assert c.threshold_gap_analog == c.threshold_gap
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `AttributeError: 'Config' object has no attribute 'peso_tfidf_analog'`.

- [ ] **Step 3: Add the fields**

Em `src/tdt/config.py`, dentro do dataclass `Config`, após a seção de mescla/roteador dos discretos:

```python
    # Analógicos — mesmos defaults dos discretos até calibrar separadamente
    peso_tfidf_analog: float = 0.34
    peso_vetorial_analog: float = 0.33
    peso_fuzzy_analog: float = 0.33
    threshold_pct_analog: float = 0.45
    threshold_gap_analog: float = 0.08
```

- [ ] **Step 4: Run to verify it passes**

Run: `python -m pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/config.py tests/test_config.py
git commit -m "feat(config): knobs de peso/threshold separados p/ analógicos"
```

---

### Task 6: Pipeline — scorers analógicos + dual-pass

**Files:**
- Modify: `src/tdt/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `Config.*_analog` (Tarefa 5), `TipoSinal.categoria_confiavel` (Tarefa 4), `SinalPadrao` analógicos (já existem em `lp.analogicos`).
- Produces: `executar(...)` passa a classificar analógicos e a aplicar dual-pass em sinais com `categoria_confiavel=False`. `_corpus(lp, config, categoria="Discrete")` ganha o parâmetro de categoria.

- [ ] **Step 1: Write the failing test (analógico decidido chega ao output)**

Em `tests/test_pipeline.py`, estenda o vocab fake e o input sintético para incluir um analógico, e asserte que ele é decidido. Adicione:

```python
def _input_com_analogico(tmp_path):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "01F1_GTA_P"
    ws.append(["", "", "SUBESTAÇÃO X", "", ""])
    ws.append(["IED", "Módulo", "Descrição do Ponto", "Tipo", "Endereço DNP3"])
    ws.append(["Digitais", "", "", "", ""])
    ws.append(["01F1", "LT_GTA", "FALHA COMUNICACAO", "Digital", "10"])
    ws.append(["Analógicas", "", "", "", ""])
    ws.append(["01F1", "LT_GTA", "CORRENTE FASE A", "Analógico", "20"])
    p = tmp_path / "input_ana.xlsx"
    wb.save(p)
    return p


def test_pipeline_classifica_analogico(tmp_path, template_dnp3_path, lista_padrao_path):
    cfg = Config(peso_tfidf=1.0, peso_vetorial=0.0,
                 peso_tfidf_analog=1.0, peso_vetorial_analog=0.0,
                 threshold_pct=0.3, threshold_gap=0.01,
                 threshold_pct_analog=0.3, threshold_gap_analog=0.01)
    inp = _input_com_analogico(tmp_path)
    resultado, wb = executar(
        inp, template_dnp3_path, lista_padrao_path,
        config=cfg, encoder=_fake_encoder, subestacao="X", modo="nao-homogeneo",
    )
    analog = [r for r in resultado.lista.registros if r.tipo_sinal.categoria == "Analog"]
    assert len(analog) >= 1
    # saiu na sheet analógica do TDT
    ws = wb["DNP3_AnalogSignals"]
    nomes = [ws.cell(r, 1).value for r in range(5, 5 + len(analog))]
    assert any(n for n in nomes)
```

(O `_fake_encoder` e `_VOCAB` já existem no arquivo; `CORRENTE`/`FASE` já estão no vocab.)

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_pipeline.py::test_pipeline_classifica_analogico -v`
Expected: FAIL — hoje `analog` é vazio (analógicos descartados em `pipeline.py`) e a sheet `DNP3_AnalogSignals` sai vazia. A asserção `len(analog) >= 1` falha.

- [ ] **Step 3: Parametrize _corpus by category**

Em `src/tdt/pipeline.py`, troque `_corpus` para aceitar a categoria:

```python
def _corpus(lp: ListaPadraoADMS, config: Config, categoria: str = "Discrete") -> list[tuple[str, str]]:
    fonte = lp.discretos if categoria == "Discrete" else lp.analogicos
    return [
        (s.sigla, canonizar(s.descricao, config))
        for s in fonte
        if s.descricao
    ]
```

- [ ] **Step 4: Build a scorer bundle and an analog config**

Em `pipeline.py`, adicione um pequeno agregador de scorers (logo após os imports) e o helper que constrói os dois bundles. Use `NamedTuple` para clareza:

```python
from typing import NamedTuple


class _Scorers(NamedTuple):
    tfidf: object
    indice: object
    fuzzy: object
    config: Config
```

E uma função para construir um bundle a partir de uma categoria:

```python
def _construir_scorers(lp, config, encoder, categoria, cfg_efetivo) -> _Scorers:
    corpus = _corpus(lp, config, categoria)
    return _Scorers(
        tfidf=ScorerTFIDF.construir(corpus),
        indice=IndiceVetorial.construir(corpus, encoder),
        fuzzy=FuzzyMatcher.construir(corpus),
        config=cfg_efetivo,
    )
```

- [ ] **Step 5: Refactor _classificar_sinal to take a _Scorers bundle**

Mude a assinatura de `_classificar_sinal` para receber um `_Scorers` em vez dos quatro argumentos soltos, usando `scorers.config` onde hoje usa `config`:

```python
def _classificar_sinal(rec, scorers: "_Scorers", diagnostico: bool = False) -> SignalRecord:
    config = scorers.config
    c_tfidf = scorers.tfidf.pontuar(rec, k=config.k_vizinhos)
    c_vet = pontuar_vetorial(rec, scorers.indice, k=config.k_vizinhos)
    c_fuzzy = scorers.fuzzy.pontuar(rec, k=config.k_vizinhos)
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
    if decidido.status == "decidido":
        decidido = _com_fase(decidido)
    return decidido
```

- [ ] **Step 6: Add the dual-pass router helper**

Adicione um helper que decide qual resultado usar conforme `categoria_confiavel`:

```python
def _classificar_roteado(rec, disc: "_Scorers", ana: "_Scorers", diagnostico: bool):
    """Devolve (decidido_ou_None, item_revisao_ou_None).

    Confiável: usa o bundle da própria categoria.
    Incerto: roda os dois; usa o único que decidir, ou manda p/ revisão.
    """
    if rec.tipo_sinal.categoria_confiavel:
        bundle = disc if rec.tipo_sinal.categoria == "Discrete" else ana
        d = _classificar_sinal(rec, bundle, diagnostico=diagnostico)
        if d.status == "decidido":
            return d, None
        return None, ItemRevisao(d, motivo="score_baixo", candidatos_sugeridos=d.candidatos[:3])

    d_disc = _classificar_sinal(rec, disc, diagnostico=diagnostico)
    d_ana = _classificar_sinal(rec, ana, diagnostico=diagnostico)
    ok_disc = d_disc.status == "decidido"
    ok_ana = d_ana.status == "decidido"
    if ok_disc and not ok_ana:
        return d_disc, None
    if ok_ana and not ok_disc:
        return d_ana, None
    cands = (d_disc.candidatos[:3] + d_ana.candidatos[:3])
    motivo = "categoria_ambigua" if (ok_disc and ok_ana) else "score_baixo"
    return None, ItemRevisao(d_disc, motivo=motivo, candidatos_sugeridos=cands)
```

- [ ] **Step 7: Rewire executar() to build both bundles and route**

Em `executar`, substitua a construção dos scorers e o loop de classificação. Onde hoje há a construção única (`tfidf = ...; indice = ...; fuzzy = ...`), troque por:

```python
    from dataclasses import replace as _replace
    cfg_analog = _replace(
        config,
        peso_tfidf=config.peso_tfidf_analog,
        peso_vetorial=config.peso_vetorial_analog,
        peso_fuzzy=config.peso_fuzzy_analog,
        threshold_pct=config.threshold_pct_analog,
        threshold_gap=config.threshold_gap_analog,
    )
    disc = _construir_scorers(lp, config, encoder, "Discrete", config)
    ana = _construir_scorers(lp, config, encoder, "Analog", cfg_analog)
    corpus = _corpus(lp, config, "Discrete")  # ainda usado p/ vocab/ref_emb abaixo
```

Mantenha as linhas existentes que derivam `vocab`, `ref_emb` e o `aud.evento` do corpus (elas continuam baseadas no corpus discreto). Remova o bloco antigo que pulava analógicos:

```python
            if rec.tipo_sinal.categoria == "Analog":
                analogicos += 1
                continue
```

E troque a chamada de classificação dentro do loop por:

```python
            decidido, item = _classificar_roteado(rec, disc, ana, diagnostico)
            if decidido is not None:
                decididos.append(decidido)
            else:
                revisao.append(item)
```

Remova o contador `analogicos` e o `aud.evento` que loga "analógicos pulados" (ou ajuste a mensagem final para `analogicos_pulados=0`). Mantenha o restante (`dc_pairer`, `corrigir`, `montar`, `engine_tdt.gerar`) inalterado — `dc_pairer` naturalmente não funde analógicos (não têm `Output`).

- [ ] **Step 8: Run the pipeline suite**

Run: `python -m pytest tests/test_pipeline.py tests/test_pipeline_diagnostico.py tests/test_pipeline_cancelamento.py tests/test_pipeline_gerar_tdt.py -v`
Expected: PASS. Se algum teste legado referenciava `_classificar_sinal` com a assinatura antiga, atualize-o para passar um `_Scorers` (improvável — é função privada).

- [ ] **Step 9: Run the FULL suite (catch regressions in engine/analog write)**

Run: `python -m pytest -q`
Expected: a sheet analógica passa a ser escrita pela engine. **Se `test_engine_tdt`/`test_pipeline_gerar_tdt` falharem por falta da função `_valores_analog`, isso é esperado — será resolvido na Tarefa 7.** Se falharem por outro motivo, corrija antes de prosseguir.

> Nota: a escrita da sheet analógica em `engine_tdt.gerar` só existe após a Tarefa 7. Até lá, `executar` ainda gera o TDT só com a sheet discreta; o `test_pipeline_classifica_analogico` assert sobre `DNP3_AnalogSignals` **vai falhar no Step 2 e só passa após a Tarefa 7**. Por isso, neste ponto, rode o teste sem a asserção da sheet (comente as 3 últimas linhas) ou aceite-o como vermelho até a Tarefa 7. Marque a asserção da sheet para reativar no final da Tarefa 7.

- [ ] **Step 10: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): classifica analógicos (scorers próprios) + dual-pass p/ categoria incerta"
```

---

### Task 7: Engine — geração da sheet `DNP3_AnalogSignals`

**Files:**
- Modify: `src/tdt/engine_tdt.py`
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: helpers de campo da Tarefa 3, `_nome_hierarquico`.
- Produces: `_valores_analog(rec, subestacao, padrao) -> dict`; `gerar()` escreve as duas sheets. `_expandir_tabela(ws, sheet_nome, ultima_linha)` ganha o parâmetro de nome da sheet.

- [ ] **Step 1: Write the failing test**

Adicione em `tests/test_engine_tdt.py`:

```python
def _rec_analog(rid, sigla, indices):
    return SignalRecord(
        id=rid,
        modulo=Modulo("AL11", "sheet_name"),
        tipo_sinal=TipoSinal("Analog", False, "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(f"{sigla} BRUTO", sigla),
        sigla_sinal=sigla,
        status="decidido",
    )


def _lista_analog():
    return ListaHomogenea(
        subestacao="IMA", protocolo="DNP3",
        registros=(_rec_analog("A:1", "IN61", [20]),),
    )


def test_escreve_sheet_analogica(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista_analog(), template_dnp3_path, lp)
    ws = wb["DNP3_AnalogSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(5, col["Signal Name"]).value == "IMA_AL11_IN61"
    assert ws.cell(5, col["Input Coordinates"]).value == "20"
    assert ws.cell(5, col["Direction"]).value == "Read"
    assert ws.cell(5, col["Remote Point Type"]).value == "Analog"
    assert ws.cell(5, col["Side"]).value == "None"
    assert ws.cell(5, col["Signal AOR Group"]).value == "IMA Distr"  # AL11 = alimentador
    assert ws.cell(5, col["Remote Point Name"]).value == "IMA_AL11_IN61"
    # table ref começa em A4
    assert ws.tables["DNP3_AnalogSignals"].ref.startswith("A4:")


def test_discreto_intacto_com_analog(template_dnp3_path, lista_padrao_path, tmp_path):
    """Gerar com registros das duas categorias preenche as duas sheets."""
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    lista = ListaHomogenea(
        subestacao="IMA", protocolo="DNP3",
        registros=_lista().registros + _lista_analog().registros,
    )
    wb = gerar(lista, template_dnp3_path, lp)
    wsd = wb["DNP3_DiscreteSignals"]
    wsa = wb["DNP3_AnalogSignals"]
    cold = {wsd.cell(4, c).value: c for c in range(1, wsd.max_column + 1)}
    cola = {wsa.cell(4, c).value: c for c in range(1, wsa.max_column + 1)}
    assert wsd.cell(5, cold["Signal Name"]).value == "IMA_3_DJ"
    assert wsa.cell(5, cola["Signal Name"]).value == "IMA_AL11_IN61"
```

- [ ] **Step 2: Run to verify it fails**

Run: `python -m pytest tests/test_engine_tdt.py::test_escreve_sheet_analogica -v`
Expected: FAIL — sheet analógica está vazia (cell vazia / `AttributeError` se `_valores_analog` não existe).

- [ ] **Step 3: Add analog constants and generalize _expandir_tabela**

Em `src/tdt/engine_tdt.py`, adicione as constantes da sheet analógica junto às existentes:

```python
SHEET_ANALOGICOS = "DNP3_AnalogSignals"
COLUNAS_ESPERADAS_ANALOG = 61
```

Generalize `_expandir_tabela` para receber o nome da sheet (a coluna final passa a vir do `max_column` da própria ws, já que analógicos têm 61 colunas):

```python
def _expandir_tabela(ws, sheet_nome: str, ultima_linha: int) -> None:
    """Ajusta o ref do ListObject para cobrir as linhas de dados escritas."""
    if sheet_nome not in ws.tables:
        return
    ultima_col = get_column_letter(ws.max_column)
    fim = max(ultima_linha, PRIMEIRA_LINHA_DADOS)
    ws.tables[sheet_nome].ref = f"A4:{ultima_col}{fim}"
```

- [ ] **Step 4: Add _valores_analog**

```python
def _valores_analog(rec: SignalRecord, subestacao: str | None, padrao: ListaPadraoADMS) -> dict:
    sp = padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
    nome = _nome_hierarquico(
        subestacao, rec.modulo.nome, rec.eletrico.nome_equipamento, rec.sigla_sinal or "?"
    )
    coords = ";".join(str(i) for i in rec.enderecamento.indices)
    alimentador = _eh_alimentador(rec.modulo.nome)
    eh_prot = bool(sp and sp.signal_type == "RelayTrip")
    remote_unit = _remote_unit(subestacao)
    rp_custom = f"{nome}_{remote_unit}" if remote_unit else None
    return {
        "Signal Name": nome,
        "Signal Alias": rec.descricoes.bruta,
        "Signal Type": sp.signal_type if sp else "Custom",
        "Phases": rec.eletrico.fase,
        "Direction": "Read",
        "Input Coordinates": coords,
        "Side": "None",
        "Output Register": False,
        "Remote Point Type": "Analog",
        "Remote Point Name": nome,
        "Signal AOR Group": _aor_group(subestacao, alimentador),
        "Device Mapping": _device_mapping(nome, rec.sigla_sinal or "?", eh_prot),
        "Remote Unit": remote_unit,
        "Remote Point Custom ID": rp_custom,
        "Remote Point Alias": _alias_hoje(),
    }
```

- [ ] **Step 5: Extract a per-sheet writer and update gerar()**

Substitua o corpo de `gerar` para escrever as duas sheets via um helper comum:

```python
def gerar(
    lista: ListaHomogenea, template_path: str | Path, lista_padrao: ListaPadraoADMS
) -> openpyxl.Workbook:
    wb = openpyxl.load_workbook(template_path)  # mantém fórmulas/estilos
    _escrever_sheet(
        wb[SHEET_DISCRETOS], SHEET_DISCRETOS, COLUNAS_ESPERADAS,
        [r for r in lista.registros if r.tipo_sinal.categoria == "Discrete"],
        _valores, lista.subestacao, lista_padrao,
    )
    _escrever_sheet(
        wb[SHEET_ANALOGICOS], SHEET_ANALOGICOS, COLUNAS_ESPERADAS_ANALOG,
        [r for r in lista.registros if r.tipo_sinal.categoria == "Analog"],
        _valores_analog, lista.subestacao, lista_padrao,
    )
    return wb


def _escrever_sheet(ws, sheet_nome, colunas_esperadas, registros, valores_fn, subestacao, padrao):
    if ws.max_column != colunas_esperadas:
        raise ValueError(
            f"{sheet_nome} tem {ws.max_column} colunas, esperado "
            f"{colunas_esperadas} — template desatualizado?"
        )
    colunas = _mapa_colunas(ws)
    linha = PRIMEIRA_LINHA_DADOS
    for rec in registros:
        for display, valor in valores_fn(rec, subestacao, padrao).items():
            col = colunas.get(display)
            if col and valor is not None:
                ws.cell(linha, col, valor)
        linha += 1
    ultima = linha - 1
    _expandir_tabela(ws, sheet_nome, ultima)
    if ultima >= PRIMEIRA_LINHA_DADOS:
        _expandir_cf(ws, ultima_linha=ultima)
        _expandir_dv(ws, ultima_linha=ultima)
```

Remova a antiga função-corpo de `gerar` (o loop discreto inline e a chamada antiga a `_expandir_tabela(ws, ultima_linha=ultima)`).

- [ ] **Step 6: Fix the existing discrete table-ref test call site**

`_expandir_tabela` agora exige `sheet_nome`. O teste `test_table_ref_comeca_em_a4` chama `gerar` (não a função direto), então não muda. Confirme que nenhum teste chama `_expandir_tabela` diretamente:

Run: `python -m pytest tests/test_engine_tdt.py -v`
Expected: PASS — incluindo `test_table_ref_comeca_em_a4` (discreto ainda `A4:AQ6`) e os novos analógicos.

- [ ] **Step 7: Reactivate the analog-sheet assertion from Task 6**

Reative as 3 últimas linhas de `test_pipeline_classifica_analogico` (a asserção sobre `DNP3_AnalogSignals`) caso tenham sido comentadas no Step 9 da Tarefa 6.

Run: `python -m pytest tests/test_pipeline.py::test_pipeline_classifica_analogico -v`
Expected: PASS.

- [ ] **Step 8: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (todos). Reporte a contagem final.

- [ ] **Step 9: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine_tdt): gera sheet DNP3_AnalogSignals (campos mínimos + derivados)"
```

---

## Self-Review (executada na escrita do plano)

- **Cobertura da spec:** §1.1 categoria incerta → Tarefas 4+6; §1.2 Config analog → Tarefa 5; §1.3 sem pareamento → coberto (dc_pairer não toca analógico, nota na Tarefa 6 Step 7); §1.4 sheet analógica → Tarefa 7; §2.1 constantes → Tarefa 3; §2.2 deriváveis (incl. Phases/Normal Value) → Tarefas 1,2,3; §2.3 fora de escopo → não implementado por design (sem tarefa, correto); §2.4/§2.5 mudanças+testes → distribuídas. **Sem lacunas.**
- **Placeholders:** nenhum "TODO"/"TBD"; todo passo de código mostra o código.
- **Consistência de tipos:** `_Scorers`, `_construir_scorers`, `_classificar_sinal(rec, scorers)`, `_classificar_roteado(rec, disc, ana, diagnostico)`, `_valores_analog`, `_expandir_tabela(ws, sheet_nome, ultima_linha)`, `fase_da_sigla`, helpers `_eh_alimentador/_aor_group/_remote_unit/_device_mapping/_normal_value/_alias_hoje` — nomes e assinaturas batem entre tarefas produtoras e consumidoras.
- **Risco conhecido:** a ordem cria uma janela onde `test_pipeline_classifica_analogico` fica vermelho entre Tarefa 6 e 7 (documentado explicitamente nos Steps 9/7). Aceitável em execução sequencial.
