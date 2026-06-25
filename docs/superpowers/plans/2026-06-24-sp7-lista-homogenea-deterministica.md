# SP7 — Caminho Determinístico para Lista Homogênea — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sheets homogêneas com cabeçalho fixo conhecido (`docs/input_homogeneo.xlsx`) passam a ler SIGLA SINAL/MÓDULO/EQUIPAMENTO/TIPO/INDEX DNP3 direto das colunas, sem rodar `analise_colunas`/scorers, quando a sigla já existe na Lista Padrão.

**Architecture:** Novo módulo `src/tdt/estruturador_homogeneo.py` com `detectar_header()` (match literal de cabeçalho) e `estruturar_homogeneo()` (monta `SignalRecord` direto das colunas, valida sigla contra `ListaPadraoADMS`). `pipeline.executar()` tenta esse caminho por sheet quando `rota.homogeneo`; cai no caminho heurístico de hoje (`analise_colunas` + `estruturador`) como fallback.

**Tech Stack:** Python 3.14, pytest, openpyxl (já em uso). Nenhuma dependência nova.

## Global Constraints

- SRP: 1 módulo = 1 responsabilidade. Sem mudar assinatura pública de `pipeline.executar()`.
- TDD obrigatório: teste primeiro (RED→GREEN), 1 `test_*.py` por módulo novo.
- Não duplicar `_parse_indices` — reaproveitar de `estruturador.py`.
- `Utilizado? != "SIM"` nunca gera `SignalRecord`.
- Sigla vazia/não encontrada na Lista Padrão cai no caminho de scoring existente (fallback) — nunca quebra o pipeline.

---

### Task 1: `detectar_header()` — detecção do cabeçalho fixo

**Files:**
- Create: `src/tdt/estruturador_homogeneo.py`
- Test: `tests/test_estruturador_homogeneo.py`

**Interfaces:**
- Produces: `detectar_header(rows: list[tuple]) -> int | None` — índice 0-based da linha de cabeçalho, ou `None`.
- Produces: constante `_MAX_SCAN: int = 30` (linhas escaneadas antes de desistir — cabeçalho real do fixture aparece bem no início, depois do bloco de legenda).
- Produces: constante `_CABECALHO_ESPERADO: frozenset[str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_estruturador_homogeneo.py
from tdt.estruturador_homogeneo import detectar_header


def test_detectar_header_acha_linha_no_formato_fixo():
    rows = [
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMÔNICO"),
        ("DJ", "52-11"),
        (),
        ("Utilizado?", "SUBESTAÇÃO", "MÓDULO", "EQUIPAMENTO", "TIPO",
         "DESCRIÇÃO DO PONTO", "SIGLA SINAL", "NOME", "Tipo",
         "Nível Lógico 0", "Nível Lógico 1", "Escala",
         "Control Code / Qualificador", "INDEX DNP3"),
        ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
         "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70"),
    ]
    assert detectar_header(rows) == 3


def test_detectar_header_devolve_none_sem_formato_fixo():
    rows = [("DESCRIÇÃO", "ÍNDICE"), ("Disjuntor 52-2", "100")]
    assert detectar_header(rows) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_estruturador_homogeneo.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'tdt.estruturador_homogeneo'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/tdt/estruturador_homogeneo.py
"""Caminho determinístico pra sheets homogêneas: cabeçalho fixo conhecido,
sigla/módulo/equipamento/tipo já vêm em colunas dedicadas — sem heurística
de coluna nem scoring."""

from __future__ import annotations

import re

_MAX_SCAN = 30

_CABECALHO_ESPERADO: frozenset[str] = frozenset({
    "UTILIZADO?", "SUBESTACAO", "MODULO", "EQUIPAMENTO", "TIPO",
    "DESCRICAO DO PONTO", "SIGLA SINAL", "NOME", "INDEX DNP3",
})


def _sem_acentos(s: str) -> str:
    troca = str.maketrans("ÁÉÍÓÚÂÊÎÔÛÃÕÀÇ", "AEIOUAEIOUAOAC")
    return s.translate(troca)


def _normaliza_celula(v) -> str:
    if v is None:
        return ""
    return _sem_acentos(str(v)).strip().upper()


def detectar_header(rows: list[tuple]) -> int | None:
    """Devolve o índice 0-based da linha de cabeçalho, ou None se a sheet
    não seguir o formato homogêneo fixo."""
    for i, row in enumerate(rows[:_MAX_SCAN]):
        celulas = {_normaliza_celula(v) for v in row if v is not None}
        if _CABECALHO_ESPERADO <= celulas:
            return i
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_estruturador_homogeneo.py -v`
Expected: PASS (2 testes)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/estruturador_homogeneo.py tests/test_estruturador_homogeneo.py
git commit -m "feat(sp7): detecta cabecalho fixo de sheet homogenea por nome de coluna"
```

---

### Task 2: `estruturar_homogeneo()` — extração determinística por linha

**Files:**
- Modify: `src/tdt/estruturador_homogeneo.py`
- Test: `tests/test_estruturador_homogeneo.py`

**Interfaces:**
- Consumes: `tdt.contracts.SignalRecord`, `Modulo`, `TipoSinal`, `Enderecamento`, `Descricoes`, `Eletrico` (campos já existentes, ver Task 2 do contracts em SP10 — `Eletrico.nome_equipamento` já existe hoje).
- Consumes: `tdt.dados.lista_padrao.ListaPadraoADMS.por_sigla(sigla: str) -> SinalPadrao | None`.
- Consumes: `tdt.normalizador.extrair_contexto_estrutural(texto: str) -> tuple[str, ContextoEstrutural]`, `tdt.normalizador.canonizar`.
- Consumes: `tdt.estruturador._parse_indices(cell) -> tuple[int, ...]` (reaproveitado, não duplicado).
- Consumes: `tdt.config.Config`.
- Produces: `estruturar_homogeneo(rows, header_idx, sheet_name, lp, config) -> tuple[list[SignalRecord], list[SignalRecord]]` — `(decididos, pendentes_de_scoring)`.
- Produces: `CODIGOS_TIPO` de `tdt.vocabulario_tipo` é consumido para mapear coluna `TIPO` (A/C/D) — confirmar nome do módulo antes de implementar (ver Step 1 abaixo).

- [ ] **Step 1: Confirmar API de `vocabulario_tipo` antes de escrever o teste**

Run: `grep -n "CODIGOS_TIPO\|^def \|^class " src/tdt/vocabulario_tipo.py`

Use a assinatura real encontrada (provavelmente `CODIGOS_TIPO: dict[str, tuple[str, str]]` mapeando `"A"/"C"/"D"` para `(categoria, direcao)`) — se a forma for diferente, adapte o `_TIPO_PARA_CATEGORIA` do Step 3 mantendo o mesmo resultado (categoria/direção por código de 1 letra).

- [ ] **Step 2: Write the failing test**

```python
# tests/test_estruturador_homogeneo.py (acrescentar)
from tdt.config import Config
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.estruturador_homogeneo import estruturar_homogeneo


class _ListaPadraoFake:
    def __init__(self, siglas: dict[str, SinalPadrao]):
        self._siglas = siglas

    def por_sigla(self, sigla):
        return self._siglas.get(sigla.strip().upper())


def _sinal_padrao(sigla: str) -> SinalPadrao:
    return SinalPadrao(
        sigla=sigla, descricao="CORRENTE FASE A", signal_type="Current",
        direction=None, mm=None, categoria="Analog",
    )


_HEADER = (
    "Utilizado?", "SUBESTAÇÃO", "MÓDULO", "EQUIPAMENTO", "TIPO",
    "DESCRIÇÃO DO PONTO", "SIGLA SINAL", "NOME", "Tipo",
    "Nível Lógico 0", "Nível Lógico 1", "Escala",
    "Control Code / Qualificador", "INDEX DNP3",
)


def test_linha_com_sigla_valida_vira_decidido_sem_scoring():
    rows = [_HEADER, ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
                       "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({"IA": _sinal_padrao("IA")})
    decididos, pendentes = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert pendentes == []
    assert len(decididos) == 1
    rec = decididos[0]
    assert rec.sigla_sinal == "IA"
    assert rec.modulo.nome == "AL"
    assert rec.eletrico.equipamento_alvo == "Disjuntor" or rec.eletrico.equipamento_alvo is None
    assert rec.enderecamento.indices == (70,)


def test_linha_nao_utilizada_nao_vira_sinal():
    rows = [_HEADER, ("NÃO", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
                       "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({"IA": _sinal_padrao("IA")})
    decididos, pendentes = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert decididos == [] and pendentes == []


def test_sigla_inexistente_na_lista_padrao_vai_pra_pendentes():
    rows = [_HEADER, ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "XYZ",
                       "IMA_AL11_AL11_XYZ", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({})
    decididos, pendentes = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert decididos == [] and len(pendentes) == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_estruturador_homogeneo.py -v`
Expected: FAIL com `ImportError: cannot import name 'estruturar_homogeneo'`

- [ ] **Step 4: Write minimal implementation**

```python
# src/tdt/estruturador_homogeneo.py (acrescentar ao final)
from tdt.config import Config
from tdt.contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.estruturador import _parse_indices
from tdt.normalizador import canonizar, extrair_contexto_estrutural
from tdt.vocabulario_tipo import CODIGOS_TIPO  # ajustar import conforme Step 1 da Task 2

_EQUIPAMENTO_POR_MODULO: dict[str, str] = {
    "DJ": "Disjuntor",
    "SECC": "Seccionadora", "SECF": "Seccionadora",
    "SECT": "Seccionadora", "SECG": "Seccionadora",
}


def _col(header: tuple, nome: str) -> int | None:
    for i, v in enumerate(header):
        if _normaliza_celula(v) == nome:
            return i
    return None


def estruturar_homogeneo(
    rows: list[tuple], header_idx: int, sheet_name: str,
    lp: ListaPadraoADMS, config: Config,
) -> tuple[list[SignalRecord], list[SignalRecord]]:
    header = rows[header_idx]
    idx = {
        "utilizado": _col(header, "UTILIZADO?"),
        "modulo": _col(header, "MODULO"),
        "equipamento": _col(header, "EQUIPAMENTO"),
        "tipo": _col(header, "TIPO"),
        "descricao": _col(header, "DESCRICAO DO PONTO"),
        "sigla": _col(header, "SIGLA SINAL"),
        "index": _col(header, "INDEX DNP3"),
    }

    decididos: list[SignalRecord] = []
    pendentes: list[SignalRecord] = []

    for i, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        if idx["utilizado"] is None or idx["utilizado"] >= len(row):
            continue
        if _normaliza_celula(row[idx["utilizado"]]) != "SIM":
            continue

        bruta = str(row[idx["descricao"]] or "") if idx["descricao"] is not None else ""
        remanescente, ctx = extrair_contexto_estrutural(bruta)
        cod_tipo = _normaliza_celula(row[idx["tipo"]]) if idx["tipo"] is not None else ""
        categoria, direcao = CODIGOS_TIPO.get(cod_tipo, ("Discrete", "Input"))
        modulo_nome = str(row[idx["modulo"]]) if idx["modulo"] is not None and row[idx["modulo"]] else None
        equip_cod = _normaliza_celula(row[idx["equipamento"]]) if idx["equipamento"] is not None else ""
        sigla = str(row[idx["sigla"]] or "").strip() if idx["sigla"] is not None else ""
        indices = _parse_indices(row[idx["index"]]) if idx["index"] is not None and idx["index"] < len(row) else ()

        rec = SignalRecord(
            id=f"{sheet_name}:{i}",
            modulo=Modulo(modulo_nome, "coluna:MODULO"),
            tipo_sinal=TipoSinal(categoria, is_double_bit=False, direcao=direcao, categoria_confiavel=True),
            enderecamento=Enderecamento("DNP3", indices),
            descricoes=Descricoes(bruta, canonizar(remanescente, config, None)),
            eletrico=Eletrico(
                fase=ctx.fase,
                equipamento_alvo=_EQUIPAMENTO_POR_MODULO.get(equip_cod, ctx.equipamento_alvo),
                barra=ctx.barra,
            ),
        )

        sp = lp.por_sigla(sigla) if sigla else None
        if sp is None:
            pendentes.append(rec)
        else:
            decididos.append(replace_sigla(rec, sigla))

    return decididos, pendentes


def replace_sigla(rec: SignalRecord, sigla: str) -> SignalRecord:
    from dataclasses import replace as _replace
    return _replace(rec, sigla_sinal=sigla, status="decidido")
```

Nota: se `CODIGOS_TIPO` não existir com essa assinatura exata, adapte `_col`/lookup pra API real confirmada no Step 1 — o teste de aceite é o comportamento (`categoria`/`direcao` corretos pro código `A`/`C`/`D`), não o nome interno da função.

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_estruturador_homogeneo.py -v`
Expected: PASS (5 testes)

- [ ] **Step 6: Commit**

```bash
git add src/tdt/estruturador_homogeneo.py tests/test_estruturador_homogeneo.py
git commit -m "feat(sp7): extrai SignalRecord direto das colunas da sheet homogenea"
```

---

### Task 3: Integrar no `pipeline.executar()`

**Files:**
- Modify: `src/tdt/pipeline.py:222-242` (loop de sheets, dentro de `executar()`)
- Test: `tests/test_pipeline_homogeneo.py`

**Interfaces:**
- Consumes: `tdt.estruturador_homogeneo.detectar_header`, `estruturar_homogeneo` (Tasks 1-2).
- Consumes: `rota.homogeneo: bool` (já existe em `Rota`, `identificador.py:30`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline_homogeneo.py
from pathlib import Path

import openpyxl
import pytest

from tdt.config import Config
from tdt.pipeline import executar

_DOCS = Path(__file__).resolve().parents[1] / "docs"


@pytest.fixture
def encoder_fake():
    import numpy as np

    def _enc(textos):
        return np.zeros((len(textos), 8), dtype="float32")

    return _enc


def test_sheet_homogenea_usa_caminho_deterministico(encoder_fake):
    resultado, _wb = executar(
        _DOCS / "input_homogeneo.xlsx",
        _DOCS / "dnp3_template.xlsx",
        _DOCS / "Pontos Padrao ADMS_v1.xlsx",
        config=Config(),
        encoder=encoder_fake,
        modo="homogeneo",
    )
    decididos_sem_diagnostico = [r for r in resultado.lista.registros if r.diagnostico is None]
    assert len(decididos_sem_diagnostico) > 0  # sigla validada direto da coluna, sem rodar scorers
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_pipeline_homogeneo.py -v`
Expected: FAIL ou comportamento diferente do esperado (todos os registros vêm com `diagnostico` populado pelo caminho heurístico, já que o atalho ainda não existe) — confirme lendo a saída antes de prosseguir.

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/pipeline.py`, adicionar import e alterar o loop:

```python
from tdt.estruturador_homogeneo import detectar_header, estruturar_homogeneo
```

Substituir o trecho (linhas atuais ~222-225):

```python
        rows = ler_rows(wb_in[sn])
        mapa = analisar(rows, encoder, ref_emb)
        sinais = list(estruturar(rows, mapa, sheet_name=sn, config=config, vocab=vocab))
```

por:

```python
        rows = ler_rows(wb_in[sn])
        header_homog = detectar_header(rows) if rota.homogeneo else None
        if header_homog is not None:
            decididos_homog, sinais = estruturar_homogeneo(rows, header_homog, sn, lp, config)
            decididos.extend(decididos_homog)
        else:
            mapa = analisar(rows, encoder, ref_emb)
            sinais = list(estruturar(rows, mapa, sheet_name=sn, config=config, vocab=vocab))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_pipeline_homogeneo.py -v`
Expected: PASS

- [ ] **Step 5: Run full suite to check no regression**

Run: `python -m pytest -q`
Expected: todos os testes existentes continuam verdes.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline_homogeneo.py
git commit -m "feat(sp7): pipeline usa caminho deterministico p/ sheet homogenea com cabecalho fixo"
```

---

## Self-Review Notes

- Cobertura: detecção de cabeçalho (1), extração por linha incl. `Utilizado?=NÃO` e sigla ausente/inválida (2), integração no pipeline com fallback (3). Critério de aceite 6 (sheet homogênea fora do formato cai no heurístico) é cobertura automática do `if header_homog is not None` — `header_homog is None` preserva o caminho de hoje, sem teste extra necessário além do já existente em `test_estruturador_homogeneo.py::test_detectar_header_devolve_none_sem_formato_fixo`.
- Risco principal: nome exato da API de `vocabulario_tipo.CODIGOS_TIPO` — Task 2 Step 1 manda confirmar antes de codificar, em vez de assumir.
