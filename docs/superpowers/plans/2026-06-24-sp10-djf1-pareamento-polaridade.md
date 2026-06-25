# SP10 — DJF1 e Pareamento de Polaridade (Ligado/Desligado) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Disjuntor com duas linhas de input ("...Desligado"/"...Ligado") converge pra sigla de posição `DJF1` mesmo quando a descrição padrão da Lista Padrão é genérica demais pro scorer de texto — via (1) Lista Padrão v2 com descrição enriquecida e (2) regra de pareamento por polaridade configurável.

**Architecture:** Dois fixes independentes — dado (`docs/Pontos Padrao ADMS_v2.xlsx`) e código (`src/tdt/pareamento_polaridade.py`, novo módulo SRP, chamado em `pipeline.executar()` antes do loop de classificação).

**Tech Stack:** openpyxl, nenhuma dependência nova.

## Global Constraints

- Não editar `Pontos Padrao ADMS_v1.xlsx` (lista oficial compartilhada) — só copiar pra v2.
- `parear_polaridade_equipamento=False` → comportamento idêntico a hoje (regressão zero).
- Pareamento só dispara em par exato (1 ligado + 1 desligado do mesmo módulo+equipamento) — ambiguidade cai no scoring normal.
- `_SIGLA_POSICAO` fica pequena de propósito (só `Disjuntor`→`DJF1` confirmado) — não generalizar pra Seccionadora sem evidência real.

---

### Task 1: Lista Padrão v2 com descrição de DJF1 enriquecida

**Files:**
- Create: `docs/Pontos Padrao ADMS_v2.xlsx` (cópia de `docs/Pontos Padrao ADMS_v1.xlsx`)
- Modify: `src/tdt/defaults.py`
- Test: `tests/test_lista_padrao.py`

**Interfaces:**
- Produces: `defaults.DEFAULT_LISTA` apontando pra v2.

- [ ] **Step 1: Criar a cópia e editar a descrição de DJF1**

Run (PowerShell, já que o ambiente é Windows):
```powershell
Copy-Item "docs/Pontos Padrao ADMS_v1.xlsx" "docs/Pontos Padrao ADMS_v2.xlsx"
```

Abrir `docs/Pontos Padrao ADMS_v2.xlsx` com um script Python único (não editar via UI do Excel, pra preservar formatação/estrutura — usar openpyxl preservando o resto do arquivo):

```python
# script descartável, rodar uma vez e apagar — não faz parte do código do projeto
import openpyxl

wb = openpyxl.load_workbook("docs/Pontos Padrao ADMS_v2.xlsx")
ws = wb["DiscreteSignals"]
header = next(ws.iter_rows(min_row=1, max_row=1, values_only=True))
col_sigla = header.index("SINAL") + 1
col_desc = header.index("DESCRIÇÃO NOVA") + 1  # confirmar nome exato da coluna antes de rodar
for row in ws.iter_rows(min_row=2):
    if row[col_sigla - 1].value == "DJF1":
        row[col_desc - 1].value = "DISJUNTOR NF (LIGADO/DESLIGADO/ABERTO/FECHADO)"
        break
wb.save("docs/Pontos Padrao ADMS_v2.xlsx")
```

Confirme o nome exato da coluna de descrição rodando antes:
Run: `python -c "import openpyxl; wb=openpyxl.load_workbook('docs/Pontos Padrao ADMS_v1.xlsx'); print(next(wb['DiscreteSignals'].iter_rows(min_row=1,max_row=1,values_only=True)))"`

- [ ] **Step 2: Write the failing test**

```python
# tests/test_lista_padrao.py (acrescentar)
from tdt.defaults import DEFAULT_LISTA
from tdt.dados.lista_padrao import ListaPadraoADMS


def test_default_lista_aponta_para_v2_com_djf1_enriquecido():
    assert "v2" in DEFAULT_LISTA
    lp = ListaPadraoADMS.carregar(DEFAULT_LISTA)
    sp = lp.por_sigla("DJF1")
    assert sp is not None
    assert "LIGADO" in sp.descricao.upper()
    assert "DESLIGADO" in sp.descricao.upper()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_lista_padrao.py -k v2 -v`
Expected: FAIL — `DEFAULT_LISTA` ainda aponta pra v1.

- [ ] **Step 4: Apply the fix**

```python
# src/tdt/defaults.py
DEFAULT_LISTA = str(_DOCS / "Pontos Padrao ADMS_v2.xlsx")
```

(`v1.xlsx` permanece no repo intocado, como histórico.)

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_lista_padrao.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add "docs/Pontos Padrao ADMS_v2.xlsx" src/tdt/defaults.py tests/test_lista_padrao.py
git commit -m "feat(dados): Lista Padrao v2 com descricao DJF1 enriquecida (polaridade); default aponta pra v2"
```

---

### Task 2: `Config.parear_polaridade_equipamento` + `ContextoEstrutural.nome_equipamento`

**Files:**
- Modify: `src/tdt/config.py` (dataclass `Config`)
- Modify: `src/tdt/normalizador.py` (dataclass `ContextoEstrutural`, função `extrair_contexto_estrutural`)
- Modify: `src/tdt/estruturador.py` (montagem de `Eletrico(...)` em `estruturar()`)
- Test: `tests/test_normalizador.py`, `tests/test_config.py` (se existir, senão pular teste de Config — campo trivial com default)

**Interfaces:**
- Produces: `Config.parear_polaridade_equipamento: bool = True`.
- Produces: `ContextoEstrutural.nome_equipamento: str | None`.
- Nota: `Eletrico.nome_equipamento` **já existe** em `contracts.py` e já é lido por `engine_tdt._nome_hierarquico` — só falta ser escrito. Não recriar o campo, só populá-lo.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_normalizador.py (acrescentar)
from tdt.normalizador import extrair_contexto_estrutural


def test_extrai_nome_equipamento_bruto():
    _, ctx = extrair_contexto_estrutural("DISJUNTOR 52-2 DESLIGADO")
    assert ctx.nome_equipamento == "52-2"


def test_nome_equipamento_none_sem_id():
    _, ctx = extrair_contexto_estrutural("CORRENTE FASE A")
    assert ctx.nome_equipamento is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_normalizador.py -k nome_equipamento -v`
Expected: FAIL com `AttributeError: 'ContextoEstrutural' object has no attribute 'nome_equipamento'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/normalizador.py
@dataclass(frozen=True)
class ContextoEstrutural:
    equipamento_alvo: str | None = None
    nome_equipamento: str | None = None  # "52-2" — ID bruto
    barra: str | None = None
    fase: str | None = None


def extrair_contexto_estrutural(texto: str) -> tuple[str, ContextoEstrutural]:
    if not texto:
        return "", ContextoEstrutural()
    base = _sem_acentos(texto).upper()

    equipamento_alvo = None
    nome_equipamento = None
    m = _ID_EQUIPAMENTO.search(base)
    if m:
        equipamento_alvo = _EQUIPAMENTO_ANSI.get(m.group(1))
        nome_equipamento = f"{m.group(1)}-{m.group(2)}"
        base = (base[: m.start()] + " " + base[m.end() :]).strip()
        base = " ".join(base.split())

    barra = None
    m_barra = _MARCADOR_BARRA.search(base)
    if m_barra and m_barra.group(1) in _BARRA:
        barra = _BARRA[m_barra.group(1)]
        inicio, fim = m_barra.span(1)
        base = (base[:inicio] + " " + base[fim:]).strip()
        base = " ".join(base.split())

    fase = None
    tokens = base.split()
    fase_val, tok_remover = _fase_no_texto(tokens)
    if tok_remover is not None:
        tokens.remove(tok_remover)
        base = " ".join(tokens)
        fase = fase_val

    return base, ContextoEstrutural(
        equipamento_alvo=equipamento_alvo, nome_equipamento=nome_equipamento,
        barra=barra, fase=fase,
    )
```

Em `src/tdt/estruturador.py`, no bloco que monta `Eletrico(...)` dentro de `estruturar()`:

```python
        eletrico = Eletrico(
            fase=ctx_estrutural.fase,
            equipamento_alvo=ctx_estrutural.equipamento_alvo,
            nome_equipamento=ctx_estrutural.nome_equipamento,
            barra=ctx_estrutural.barra,
        )
```

Em `src/tdt/config.py`, adicionar ao final da dataclass `Config`:

```python
    # Pareamento de polaridade (SP10) — rede de segurança quando a descrição
    # padrão da sigla de posição é genérica demais pro scorer de texto.
    parear_polaridade_equipamento: bool = True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_normalizador.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite to check no regression**

Run: `python -m pytest -q`
Expected: nenhuma regressão (campo novo com default, dataclasses frozen continuam compatíveis).

- [ ] **Step 6: Commit**

```bash
git add src/tdt/config.py src/tdt/normalizador.py src/tdt/estruturador.py tests/test_normalizador.py
git commit -m "feat(sp10): config.parear_polaridade_equipamento + ContextoEstrutural.nome_equipamento"
```

---

### Task 3: Novo módulo `pareamento_polaridade.py`

**Files:**
- Create: `src/tdt/pareamento_polaridade.py`
- Test: `tests/test_pareamento_polaridade.py`

**Interfaces:**
- Consumes: `tdt.contracts.SignalRecord` (campos `eletrico.equipamento_alvo`, `eletrico.nome_equipamento`, `modulo.nome`, `descricoes.normalizada`, `id`).
- Consumes: `tdt.config.Config.parear_polaridade_equipamento` (Task 2).
- Produces: `forcar_polaridade_equipamento(registros: list[SignalRecord], config: Config) -> list[SignalRecord]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pareamento_polaridade.py
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.pareamento_polaridade import forcar_polaridade_equipamento


def _rec(id_, estado: str, equipamento="Disjuntor", nome_equip="52-2", modulo="AL"):
    return SignalRecord(
        id=id_,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", is_double_bit=False, direcao="Input"),
        enderecamento=Enderecamento("DNP3", (100,)),
        descricoes=Descricoes(f"DISJ {nome_equip} {estado}", estado),
        eletrico=Eletrico(equipamento_alvo=equipamento, nome_equipamento=nome_equip),
    )


def test_par_ligado_desligado_converge_pra_djf1():
    ligado = _rec("a", "LIGADO")
    desligado = _rec("b", "DESLIGADO")
    saida = forcar_polaridade_equipamento([ligado, desligado], Config())
    by_id = {r.id: r for r in saida}
    assert by_id["a"].sigla_sinal == "DJF1" and by_id["a"].status == "decidido"
    assert by_id["b"].sigla_sinal == "DJF1" and by_id["b"].status == "decidido"


def test_sem_par_completo_nao_forca():
    ligado = _rec("a", "LIGADO")
    saida = forcar_polaridade_equipamento([ligado], Config())
    assert saida[0].sigla_sinal is None


def test_flag_desligada_e_no_op():
    ligado = _rec("a", "LIGADO")
    desligado = _rec("b", "DESLIGADO")
    cfg = Config(parear_polaridade_equipamento=False)
    saida = forcar_polaridade_equipamento([ligado, desligado], cfg)
    assert saida[0].sigla_sinal is None and saida[1].sigla_sinal is None


def test_equipamento_fora_da_tabela_e_no_op():
    ligado = _rec("a", "LIGADO", equipamento="Seccionadora", nome_equip="89-1")
    desligado = _rec("b", "DESLIGADO", equipamento="Seccionadora", nome_equip="89-1")
    saida = forcar_polaridade_equipamento([ligado, desligado], Config())
    assert saida[0].sigla_sinal is None and saida[1].sigla_sinal is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pareamento_polaridade.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'tdt.pareamento_polaridade'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/pareamento_polaridade.py
"""Forca convergencia de pares ligado/desligado do mesmo equipamento pra
sigla de posicao (ex. DJF1), quando a descricao padrao da sigla e generica
demais pro scorer de texto reconhecer as duas linhas do input (ver SP10).
Roda antes do scoring; e' rede de seguranca, desligavel via Config."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import SignalRecord

_SIGLA_POSICAO: dict[str, str] = {"Disjuntor": "DJF1"}
_LIGADO = frozenset({"LIGADO", "FECHADO"})
_DESLIGADO = frozenset({"DESLIGADO", "ABERTO"})


def _chave(rec: SignalRecord) -> tuple | None:
    eq = rec.eletrico.equipamento_alvo
    if eq not in _SIGLA_POSICAO or not rec.eletrico.nome_equipamento:
        return None
    return (rec.modulo.nome, eq, rec.eletrico.nome_equipamento)


def forcar_polaridade_equipamento(
    registros: list[SignalRecord], config: Config,
) -> list[SignalRecord]:
    if not config.parear_polaridade_equipamento:
        return registros

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        chave = _chave(rec)
        if chave is not None:
            grupos[chave].append(rec)

    forcados: dict[str, str] = {}
    for chave, grupo in grupos.items():
        ligado = [r for r in grupo if _LIGADO & set(r.descricoes.normalizada.split())]
        desligado = [r for r in grupo if _DESLIGADO & set(r.descricoes.normalizada.split())]
        if len(ligado) == 1 and len(desligado) == 1 and ligado[0] is not desligado[0]:
            sigla = _SIGLA_POSICAO[chave[1]]
            forcados[ligado[0].id] = sigla
            forcados[desligado[0].id] = sigla

    if not forcados:
        return registros
    return [
        replace(rec, sigla_sinal=forcados[rec.id], status="decidido") if rec.id in forcados else rec
        for rec in registros
    ]
```

Nota: o teste usa `descricoes.normalizada` igual ao `estado` (`"LIGADO"`/`"DESLIGADO"`) direto, sem passar por `canonizar()` — confirma o comportamento da função isoladamente. No pipeline real (Task 4), `descricoes.normalizada` já vem canonizada por `estruturador.estruturar()`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pareamento_polaridade.py -v`
Expected: PASS (4 testes)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/pareamento_polaridade.py tests/test_pareamento_polaridade.py
git commit -m "feat(sp10): pareamento_polaridade.forcar_polaridade_equipamento (DJF1, configuravel)"
```

---

### Task 4: Integrar no `pipeline.executar()`

**Files:**
- Modify: `src/tdt/pipeline.py` (loop de sheets, depois de montar `sinais`)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `tdt.pareamento_polaridade.forcar_polaridade_equipamento` (Task 3).

**Nota de ordem com SP7:** se o Task 3 do plano SP7 já foi aplicado, o trecho de leitura de sheet já tem o `if header_homog is not None: ... else: sinais = list(estruturar(...))`. Esta task adiciona a chamada de `forcar_polaridade_equipamento` **depois** desse bloco, afetando os dois ramos (sinais do caminho heurístico e os `pendentes` do caminho homogêneo que ainda vão pro scoring) — sem reabrir o `if`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline.py (acrescentar)
def test_djf1_par_ligado_desligado_converge_para_double_bit(...):
    # ponta a ponta com docs/input_nao_homogeneo_1.xlsx (fixture real citado no spec)
    resultado, _wb = executar(
        DOCS / "input_nao_homogeneo_1.xlsx", DOCS / "dnp3_template.xlsx",
        DOCS / "Pontos Padrao ADMS_v2.xlsx", config=Config(), encoder=encoder_fake,
    )
    djf1 = [r for r in resultado.lista.registros if r.sigla_sinal == "DJF1"]
    assert len(djf1) == 1
    assert djf1[0].tipo_sinal.is_double_bit
```

Reaproveite o padrão de `encoder_fake`/fixtures já usado em outros testes ponta a ponta deste arquivo.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline.py -k djf1 -v`
Expected: FAIL (ou inconclusivo — confirme primeiro lendo a saída atual, já que sem o pareamento o scorer pode decidir errado ou jogar pra revisão).

- [ ] **Step 3: Write minimal implementation**

```python
from tdt.pareamento_polaridade import forcar_polaridade_equipamento
```

No loop de `executar()`, logo após a linha que monta `sinais` (em ambos os ramos do `if`/`else` da Task 3 do SP7, ou na linha única se SP7 ainda não foi aplicado):

```python
        sinais = forcar_polaridade_equipamento(sinais, config)
        total = len(sinais)
        aud.evento("identificador", f"Sheet {sn}: {total} sinais lidos", "INFO")
        for j, rec in enumerate(sinais, 1):
            ...
            if rec.status == "decidido":  # já resolvido pelo pareamento de polaridade
                decididos.append(rec)
                continue
            if not rec.enderecamento.indices:
                ...
```

(Inserir o `if rec.status == "decidido": decididos.append(rec); continue` como primeira checagem dentro do loop `for j, rec in enumerate(sinais, 1):`, antes do `if not rec.enderecamento.indices:` existente.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline.py -k djf1 -v`
Expected: PASS

- [ ] **Step 5: Run full suite + benchmark de regressão**

Run: `python -m pytest -q`
Run: `PYTHONPATH=src python bench/benchmark.py` (gate de regressão de matching — confirmar que não piora taxa de decisão/falsos positivos)

- [ ] **Step 6: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline.py
git commit -m "feat(sp10): pipeline aplica pareamento de polaridade antes do scoring (DJF1)"
```

---

## Self-Review Notes

- Cobertura: dado v2 (1), config+contrato (2), módulo isolado (3), integração pipeline (4). Todos os 5 critérios de aceite do spec têm task correspondente.
- Risco principal: nome exato da coluna de descrição em `DiscreteSignals` (Task 1, Step 1) — confirmar antes de editar a planilha, não assumir `"DESCRIÇÃO NOVA"` sem checar.
- Dependência de ordem: Task 4 deste plano assume que o loop de `pipeline.executar()` já foi tocado pelo SP7 (ou não) — instrução explícita pra não reabrir/duplicar o `if` de detecção homogênea.
