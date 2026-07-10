# Correção Import IMA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar as 343 falhas do import ADMS da lista homogênea IMA (custom ids duplicados + MMs fora do catálogo) e fazer TAP/COMTAP saírem corretos no TDT.

**Architecture:** Novo resolvedor de identidade módulo/equipamento no caminho homogêneo (alimenta `Eletrico.nome_equipamento`; a engine não muda a montagem de nome), gate de unicidade de Custom ID antes de escrever o TDT, lista padrão v8 com 2 MMs corrigidos + teste de domínio MM⊆catálogo real, COMTAP → revisão e tipo `A/D` → DiscreteAnalog.

**Tech Stack:** Python 3.14, openpyxl, pytest. Spec: `docs/superpowers/specs/2026-07-10-sp-import-ima-erros-design.md`.

## Global Constraints

- Rodar testes a partir da raiz do repo: `python -m pytest tests/... -v` (conftest resolve o path de `src/`).
- Comandos de CLI precisam de `PYTHONPATH=src` (Bash: `PYTHONPATH=src python -m tdt.cli ...`).
- NÃO editar `docs/Pontos Padrao ADMS_v7.xlsx` — a v8 é um arquivo novo gerado por script.
- Oracle de nomes: `docs/input_homogeneo_IMA.xlsx`, 1404 linhas SIM; aceite = 1400 iguais + exatamente estas 4 divergências (inconsistências do próprio cliente, viram aviso): `IMA_BP169_BP169_FGOO`, `IMA_BP269_BP269_FGOO`, `IMA_TSA_RET_NEGT`, `IMA_TSA_RET_POST`.
- MMs corrigidos na v8 (sheet DiscreteSignals, coluna MM): `43LR` → `null@null___REMOTO@LOCAL___Custom_S_TS_SS`; `81U1`..`81U5` → `null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS`.
- Commits pequenos, Conventional Commits, mensagem termina com `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Resolvedor `identidade_homogenea` (novo módulo, TDD com oracle)

**Files:**
- Create: `src/tdt/normalizacao/identidade_homogenea.py`
- Test: `tests/test_identidade_homogenea.py`

**Interfaces:**
- Consumes: nada do projeto (módulo puro; usa apenas stdlib).
- Produces (Task 2 depende):
  - `extrair_bloco(rows: list[tuple], header_idx: int) -> dict[str, str]` — bloco de cabeçalho da sheet, rótulo normalizado → valor bruto (ex. `{"MODULO": "6", "DJ AT": "52-6"}`).
  - `@dataclass(frozen=True) Identidade(modulo: str, equipamento: str | None, origem: str)` — `equipamento=None` significa "repete o módulo" (comportamento que a engine já tem).
  - `resolver(bloco: dict[str, str], sheet_name: str, modulo_col: str, equip_col: str) -> Identidade` — `modulo_col`/`equip_col` já normalizados (upper, sem acento).

- [ ] **Step 1: Escrever os testes unitários que falham**

Criar `tests/test_identidade_homogenea.py`:

```python
"""Resolvedor de identidade módulo/equipamento do caminho homogêneo
(spec 2026-07-10-sp-import-ima-erros). Oracle: coluna NOME da lista IMA."""
from pathlib import Path

import pytest

from tdt.normalizacao.identidade_homogenea import Identidade, extrair_bloco, resolver

_DOCS = Path(__file__).resolve().parent.parent / "docs"


# --- extrair_bloco -----------------------------------------------------------

def test_extrair_bloco_aceita_numero_operativo_classe_tensao_e_numero():
    rows = [
        ("MÓDULO - TRANSFORMADOR",),
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMNICO"),
        ("MÓDULO  ", "6"),
        ("DJ AT", "52-6"),
        (),
        ("EQUIPAMENTO", "CLASSE DE TENSÃO"),
        ("BP AT", "69"),
        ("EQUIPAMENTO", "NÚMERO"),
        ("RET", "1"),
        ("header",),
    ]
    bloco = extrair_bloco(rows, header_idx=9)
    assert bloco["MODULO"] == "6"
    assert bloco["DJ AT"] == "52-6"
    assert bloco["BP AT"] == "69"
    assert bloco["RET"] == "1"


def test_extrair_bloco_ausente_devolve_vazio():
    assert extrair_bloco([("qualquer",), ("coisa",)], header_idx=2) == {}


# --- resolver: módulo --------------------------------------------------------

def test_modulo_geral_concatena_numero_do_bloco():
    ident = resolver({"MODULO": "3", "DJ": "52-3"}, "LT 3", "LT", "TC")
    assert ident.modulo == "LT3"
    assert ident.equipamento is None  # TC sem mnemônico -> repete módulo


def test_modulo_ja_numerado_mantem_comportamento_atual():
    ident = resolver({"MODULO": "99"}, "LT1", "LT 1", "DJ")
    assert ident.modulo == "LT 1"  # guarda: "<letras> <número>" não concatena


def test_modulo_com_digito_interno_concatena():
    # TSA 1 real: coluna TSA_P1 + bloco MÓDULO 40 -> cliente usa TSA_P140
    ident = resolver({"MODULO": "40"}, "TSA 1", "TSA_P1", "TSA")
    assert ident.modulo == "TSA_P140"


def test_modulo_lado_at_bt_compoe_prefixo_da_sheet():
    bloco = {"MODULO": "6", "DJ AT": "52-6", "DJ BT": "52-19"}
    assert resolver(bloco, "TR 1", "AT", "TC").modulo == "TR6AT"
    assert resolver(bloco, "TR 1", "BT", "TC").modulo == "TR6BT"
    assert resolver(bloco, "TR 1", "TR", "TR").modulo == "TR6"


def test_modulo_bp_compoe_classe_de_tensao():
    bloco = {"BP AT": "69", "BP BT1": "13.8", "BP BT2": "13.8"}
    assert resolver(bloco, "BARRA", "BP", "AT").modulo == "BP69"
    assert resolver(bloco, "BARRA", "BP1", "BT").modulo == "BP113.8"
    assert resolver(bloco, "BARRA", "BP2", "BT").modulo == "BP213.8"


def test_modulo_com_entrada_propria_no_bloco():
    # RET 1 real: coluna MÓDULO = TSA, bloco TSA->1 -> módulo TSA1
    ident = resolver({"TSA": "1", "RET": "1"}, "RET 1", "TSA", "RET")
    assert ident.modulo == "TSA1"
    assert ident.equipamento == "RET1"  # valor numérico concatena ao rótulo


# --- resolver: equipamento (segmento do meio) --------------------------------

def test_equipamento_mnemonico_com_hifen_usado_direto():
    bloco = {"MODULO": "3", "DJ": "52-3", "SECC": "89-16"}
    assert resolver(bloco, "LT 3", "LT", "SECC").equipamento == "89-16"
    assert resolver(bloco, "LT 3", "LT", "DJ").equipamento == "52-3"


def test_equipamento_lookup_por_lado():
    bloco = {"MODULO": "6", "DJ AT": "52-6", "DJ BT": "52-19"}
    assert resolver(bloco, "TR 1", "AT", "DJ").equipamento == "52-6"
    assert resolver(bloco, "TR 1", "BT", "DJ").equipamento == "52-19"


def test_sufixo_rele_p_a():
    bloco = {"MODULO": "3", "DJ": "52-3"}
    assert resolver(bloco, "LT 3", "LT", "DJ_P").equipamento == "52-3_P"
    assert resolver(bloco, "LT 3", "LT", "DJ_A").equipamento == "52-3_A"
    # sem mnemônico do base: sufixo vai no módulo (LT_P -> LT3_P)
    assert resolver(bloco, "LT 3", "LT", "LT_P").equipamento == "LT3_P"


def test_sem_bloco_fallback_sem_equipamento():
    ident = resolver({}, "AL 11", "AL", "DJ")
    assert ident.modulo == "AL"
    assert ident.equipamento is None


# --- oracle: coluna NOME da lista IMA (1404 linhas) ---------------------------

_EXCECOES_CLIENTE = {
    "IMA_BP169_BP169_FGOO", "IMA_BP269_BP269_FGOO",
    "IMA_TSA_RET_NEGT", "IMA_TSA_RET_POST",
}


def test_oracle_nome_cliente_ima():
    caminho = _DOCS / "input_homogeneo_IMA.xlsx"
    if not caminho.exists():
        pytest.skip("lista IMA não disponível")
    import unicodedata

    import openpyxl

    def norm(v):
        if v is None:
            return ""
        s = "".join(c for c in unicodedata.normalize("NFKD", str(v))
                    if not unicodedata.combining(c))
        return " ".join(s.upper().split())

    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    total, iguais, divergentes = 0, 0, set()
    for sh in wb.sheetnames:
        rows = [r for r in wb[sh].iter_rows(values_only=True)]
        ih = next((i for i, r in enumerate(rows[:30])
                   if {"NOME", "SIGLA SINAL"} <= {norm(c) for c in r if c}), None)
        if ih is None:
            continue
        hdr = [norm(c) for c in rows[ih]]
        ix = {n: hdr.index(n) for n in
              ("UTILIZADO?", "SUBESTACAO", "MODULO", "EQUIPAMENTO",
               "SIGLA SINAL", "NOME")}
        bloco = extrair_bloco(rows, ih)
        for r in rows[ih + 1:]:
            if norm(r[ix["UTILIZADO?"]]) != "SIM":
                continue
            sigla = str(r[ix["SIGLA SINAL"]] or "").strip()
            nome_cli = str(r[ix["NOME"]] or "").strip()
            if not sigla or not nome_cli:
                continue
            total += 1
            ident = resolver(bloco, sh, norm(r[ix["MODULO"]]),
                             norm(r[ix["EQUIPAMENTO"]]))
            se = str(r[ix["SUBESTACAO"]] or "").strip()
            mod = ident.modulo.replace(" ", "")
            calc = f"{se}_{mod}_{ident.equipamento or mod}_{sigla}"
            if calc == nome_cli:
                iguais += 1
            else:
                divergentes.add(nome_cli)
    wb.close()
    assert total == 1404
    assert divergentes == _EXCECOES_CLIENTE
    assert iguais == 1400
```

- [ ] **Step 2: Rodar e confirmar falha por módulo inexistente**

Run: `python -m pytest tests/test_identidade_homogenea.py -x -q`
Expected: FAIL/ERROR com `ModuleNotFoundError: No module named 'tdt.normalizacao.identidade_homogenea'`

- [ ] **Step 3: Implementar o módulo**

Criar `src/tdt/normalizacao/identidade_homogenea.py`:

```python
"""Identidade módulo/equipamento do caminho homogêneo (spec 2026-07-10).

Resolve módulo e segmento de equipamento no padrão do cliente a partir do
bloco de cabeçalho da sheet (EQUIPAMENTO | NÚMERO OPERATIVO / CLASSE DE
TENSÃO / NÚMERO). Regras validadas contra a coluna NOME da lista IMA
(1400/1404; as 4 divergências são inconsistências do próprio cliente):

- valor com "-" é mnemônico operativo -> usado direto ("DJ" -> "52-3");
- valor sem "-" concatena ao rótulo-base ("RET"+"1" -> "RET1", "LT"+"3" -> "LT3");
- coluna MÓDULO "AT"/"BT" é lado: módulo = prefixo da sheet + nº + lado
  ("TR"+"6"+"AT" -> "TR6AT") e o lookup de equipamento tenta "ROTULO LADO"
  primeiro ("DJ AT" -> "52-6");
- coluna MÓDULO "BP{n}" busca classe de tensão no rótulo "BP AT"/"BP BT{n}";
- equipamento "X_P"/"X_A" (relé principal/alternado): sufixo anexado ao meio
  ("52-3_P"); sem mnemônico do base, anexado ao módulo ("LT3_P");
- coluna MÓDULO já numerada ("LT 1") não concatena (comportamento atual).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TITULOS_BLOCO = ("OPERATIVO", "TENSAO", "NUMERO")
_COLUNA_VALOR = 1
_LADOS = ("AT", "BT")
_JA_NUMERADO = re.compile(r"^[A-Z]+\s?\d+$")


@dataclass(frozen=True)
class Identidade:
    modulo: str
    equipamento: str | None  # None -> engine repete o módulo
    origem: str  # "coluna:MODULO" | "coluna:MODULO+header:NUMERO_OPERATIVO"


def _norm(v) -> str:
    import unicodedata
    if v is None:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", str(v))
                if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def extrair_bloco(rows: list[tuple], header_idx: int) -> dict[str, str]:
    """Rótulo normalizado -> valor bruto. Aceita os três títulos de bloco
    reais (NÚMERO OPERATIVO / CLASSE DE TENSÃO / NÚMERO); vários blocos na
    mesma sheet são fundidos. Ausente/ilegível -> {}."""
    bloco: dict[str, str] = {}
    dentro = False
    for row in rows[:header_idx]:
        rotulo = _norm(row[0] if row else None)
        segundo = _norm(row[_COLUNA_VALOR] if len(row) > _COLUNA_VALOR else None)
        if rotulo == "EQUIPAMENTO" and any(t in segundo for t in _TITULOS_BLOCO):
            dentro = True
            continue
        if not dentro:
            continue
        if not rotulo:
            dentro = False
            continue
        valor = row[_COLUNA_VALOR] if len(row) > _COLUNA_VALOR else None
        if valor is not None and str(valor).strip():
            bloco[rotulo] = str(valor).strip()
    return bloco


def _concat(nome: str, num: str) -> str:
    nome = nome.replace(" ", "")
    return nome if nome.endswith(num) else nome + num


def _resolver_modulo(bloco: dict[str, str], sheet_name: str,
                     modulo_col: str) -> tuple[str, str]:
    num_mod = bloco.get("MODULO")
    if modulo_col in _LADOS and num_mod:
        prefixo = re.match(r"[A-Z]+", _norm(sheet_name))
        base = prefixo.group(0) if prefixo else modulo_col
        return _concat(base, num_mod) + modulo_col, "coluna:MODULO+header:NUMERO_OPERATIVO"
    if modulo_col in bloco:
        return _concat(modulo_col, bloco[modulo_col]), "coluna:MODULO+header:NUMERO_OPERATIVO"
    if modulo_col.startswith("BP"):
        sufixo = modulo_col[2:]
        rotulo = "BP AT" if not sufixo else f"BP BT{sufixo}"
        if rotulo in bloco:
            return _concat(modulo_col, bloco[rotulo]), "coluna:MODULO+header:NUMERO_OPERATIVO"
    if num_mod and not _JA_NUMERADO.match(modulo_col):
        return _concat(modulo_col, num_mod), "coluna:MODULO+header:NUMERO_OPERATIVO"
    return modulo_col, "coluna:MODULO"


def resolver(bloco: dict[str, str], sheet_name: str,
             modulo_col: str, equip_col: str) -> Identidade:
    modulo, origem = _resolver_modulo(bloco, sheet_name, modulo_col)
    base, sufixo_rele = equip_col, ""
    if equip_col.endswith(("_P", "_A")):
        base, sufixo_rele = equip_col[:-2], equip_col[-1]
    lado = modulo_col if modulo_col in _LADOS else None
    valor = None
    if lado and f"{base} {lado}" in bloco:
        valor = bloco[f"{base} {lado}"]
    elif base in bloco and base != "MODULO":
        valor = bloco[base]
    equipamento = None
    if valor is not None:
        equipamento = valor if "-" in valor else _concat(base, valor)
    if sufixo_rele:
        equipamento = f"{equipamento or modulo.replace(' ', '')}_{sufixo_rele}"
    return Identidade(modulo=modulo, equipamento=equipamento, origem=origem)
```

- [ ] **Step 4: Rodar os testes até passar**

Run: `python -m pytest tests/test_identidade_homogenea.py -v`
Expected: todos PASS (o oracle demora alguns segundos lendo o xlsx).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/identidade_homogenea.py tests/test_identidade_homogenea.py
git commit -m "feat(homogeneo): resolvedor identidade modulo/equipamento (oracle IMA 1400/1404)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: Wiring no estruturador (nomes, COMTAP→revisão, tipo A/D, avisos)

**Files:**
- Modify: `src/tdt/normalizacao/estruturador_homogeneo.py`
- Modify: `src/tdt/normalizacao/vocabulario_tipo.py:25-29` (CODIGOS_TIPO)
- Modify: `src/tdt/config.py` (novo campo `siglas_sem_ponto`)
- Modify: `src/tdt/contracts.py:149` (comentário de motivos)
- Modify: `src/tdt/pipeline.py:593-594` (unpack 4-tupla)
- Test: `tests/test_estruturador_homogeneo.py` (novos testes + atualizar unpacks)

**Interfaces:**
- Consumes: `extrair_bloco`, `resolver`, `Identidade` (Task 1).
- Produces: `estruturar_homogeneo(rows, header_idx, sheet_name, lp, config) -> tuple[list[SignalRecord], list[SignalRecord], list[ItemRevisao], list[str]]` — (decididos, pendentes, revisao, avisos). Task 5 depende de COMTAP em revisão com motivo `comando_tap_nao_modelado`.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao fim de `tests/test_estruturador_homogeneo.py`:

```python
def _rows_lt3_43lr():
    bloco = [
        ("MÓDULO - LINHA DE TRANSMISSÃO",),
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMNICO"),
        ("MÓDULO  ", "3"),
        ("DJ", "52-3"),
        ("SECC", "89-16"),
        ("SECF", "89-14"),
        _HEADER,
    ]
    linhas = [
        ("SIM", "IMA", "LT", "SECC", "D", "43 - CHAVE LOCAL REMOTO", "43LR",
         "IMA_LT3_89-16_43LR", "-", "-", "-", "-", "-", "1"),
        ("SIM", "IMA", "LT", "SECF", "D", "43 - CHAVE LOCAL REMOTO", "43LR",
         "IMA_LT3_89-14_43LR", "-", "-", "-", "-", "-", "6"),
        ("SIM", "IMA", "LT", "DJ_P", "D", "FASE A", "FA",
         "IMA_LT3_52-3_P_FA", "-", "-", "-", "-", "-", "38"),
    ]
    return bloco + linhas


def test_nome_equipamento_resolvido_por_equipamento_da_linha():
    lp = _ListaPadraoFake({"43LR": _sinal_padrao("43LR"), "FA": _sinal_padrao("FA")})
    decididos, _, _, _ = estruturar_homogeneo(_rows_lt3_43lr(), 6, "LT 3", lp, Config())
    por_id = {d.id: d for d in decididos}
    assert por_id["LT 3:8"].eletrico.nome_equipamento == "89-16"
    assert por_id["LT 3:9"].eletrico.nome_equipamento == "89-14"
    assert por_id["LT 3:10"].eletrico.nome_equipamento == "52-3_P"
    assert all(d.modulo.nome == "LT3" for d in decididos)


def test_comtap_vai_para_revisao_sem_gerar_ponto():
    rows = [_HEADER, ("SIM", "IMA", "TR", "TR", "C", "COMANDO TAP", "COMTAP",
                      "IMA_TR6_TR6_COMTAP", "-", "-", "-", "-", "-", "30;30")]
    lp = _ListaPadraoFake({})
    decididos, pendentes, revisao, _ = estruturar_homogeneo(rows, 0, "TR 1", lp, Config())
    assert decididos == [] and pendentes == []
    assert len(revisao) == 1
    assert revisao[0].motivo == "comando_tap_nao_modelado"
    assert revisao[0].registro.sigla_sinal == "COMTAP"


def test_tipo_ad_vira_discrete_analog():
    rows = [_HEADER, ("SIM", "IMA", "TR", "TR", "A/D", "TAP", "TAP",
                      "IMA_TR6_TR6_TAP", "-", "-", "-", "-", "-", "47")]
    lp = _ListaPadraoFake({"TAP": _sinal_padrao("TAP")})
    decididos, _, _, _ = estruturar_homogeneo(rows, 0, "TR 1", lp, Config())
    assert decididos[0].tipo_sinal.categoria == "DiscreteAnalog"
    assert decididos[0].tipo_sinal.direcao == "Input"


def test_divergencia_nome_cliente_vira_aviso():
    rows = [_HEADER, ("SIM", "IMA", "AL", "DJ", "D", "DISJUNTOR NF", "DJF1",
                      "IMA_OUTRACOISA_DJF1", "-", "-", "-", "-", "-", "1")]
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    _, _, _, avisos = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert len(avisos) == 1
    assert "IMA_OUTRACOISA_DJF1" in avisos[0]
```

Atualizar TODOS os unpacks existentes de 2-tupla no arquivo (linhas 53, 67, 75, 83, 92, 119, 128, 138) de:

```python
decididos, pendentes = estruturar_homogeneo(...)
# ou: decididos, _ = estruturar_homogeneo(...)
```

para:

```python
decididos, pendentes, _, _ = estruturar_homogeneo(...)
# ou: decididos, _, _, _ = estruturar_homogeneo(...)
```

E trocar o teste `test_extrai_numeros_operativos_do_bloco` (linhas 109-113) por versão usando o novo módulo (a função antiga será removida):

```python
def test_extrai_bloco_de_numeros_operativos():
    from tdt.normalizacao.identidade_homogenea import extrair_bloco
    bloco = extrair_bloco(_rows_com_bloco(), header_idx=5)
    assert bloco["MODULO"] == "23"
    assert bloco["DJ"] == "52-23"
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/test_estruturador_homogeneo.py -x -q`
Expected: FAIL (unpack de 4 valores em função que devolve 2 / assinatura antiga).

- [ ] **Step 3: Implementar**

3a. `src/tdt/normalizacao/vocabulario_tipo.py` — adicionar `A/D` ao dict (linhas 25-29):

```python
CODIGOS_TIPO: dict[str, tuple[str, str]] = {
    "A": ("Analog", "Input"),
    "C": ("Discrete", "Output"),
    "D": ("Discrete", "Input"),
    "A/D": ("DiscreteAnalog", "Input"),  # TAP (spec 2026-07-10)
}
```

3b. `src/tdt/config.py` — adicionar campo ao dataclass `Config` (junto dos outros `field`/frozenset):

```python
    # Siglas da lista de entrada que NÃO viram ponto no ADMS (base real:
    # comando de TAP não é sinal; 0/1629 DiscreteAnalog com output).
    siglas_sem_ponto: frozenset[str] = frozenset({"COMTAP"})
```

3c. `src/tdt/contracts.py:149` — acrescentar dois motivos ao comentário do campo `motivo` de `ItemRevisao`: `"comando_tap_nao_modelado"` e `"custom_id_duplicado"` (este último é da Task 3).

3d. `src/tdt/normalizacao/estruturador_homogeneo.py` — mudanças:

Imports: adicionar `ItemRevisao` ao import de contracts e o novo módulo:

```python
from ..contracts import Descricoes, Eletrico, Enderecamento, ItemRevisao, Modulo, SignalRecord, TipoSinal
from .identidade_homogenea import extrair_bloco, resolver
```

Remover a função `extrair_numeros_operativos` e as constantes `_ROTULO_BLOCO`/`_COLUNA_NUMERO_BLOCO` (substituídas por `extrair_bloco`).

Reescrever `estruturar_homogeneo` (corpo completo — substitui o atual):

```python
def estruturar_homogeneo(
    rows: list[tuple], header_idx: int, sheet_name: str,
    lp: ListaPadraoADMS, config: Config,
) -> tuple[list[SignalRecord], list[SignalRecord], list[ItemRevisao], list[str]]:
    """Devolve (decididos, pendentes_de_scoring, revisao, avisos).

    revisao: siglas conhecidas sem ponto (config.siglas_sem_ponto, ex. COMTAP).
    avisos: divergência NOME do cliente x nome calculado (lint, não bloqueia).
    """
    header = rows[header_idx]
    idx = {
        "utilizado": _col(header, "UTILIZADO?"),
        "subestacao": _col(header, "SUBESTACAO"),
        "modulo": _col(header, "MODULO"),
        "equipamento": _col(header, "EQUIPAMENTO"),
        "tipo": _col(header, "TIPO"),
        "descricao": _col(header, "DESCRICAO DO PONTO"),
        "sigla": _col(header, "SIGLA SINAL"),
        "nome": _col(header, "NOME"),
        "index": _col(header, "INDEX DNP3"),
    }

    bloco = extrair_bloco(rows, header_idx)

    decididos: list[SignalRecord] = []
    pendentes: list[SignalRecord] = []
    revisao: list[ItemRevisao] = []
    avisos: list[str] = []

    for i, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        if idx["utilizado"] is None or idx["utilizado"] >= len(row):
            continue
        if _normaliza_celula(row[idx["utilizado"]]) != "SIM":
            continue

        bruta = str(row[idx["descricao"]] or "") if idx["descricao"] is not None else ""
        remanescente, ctx = extrair_contexto_estrutural(bruta)
        cod_tipo = _normaliza_celula(row[idx["tipo"]]) if idx["tipo"] is not None else ""
        categoria, direcao = CODIGOS_TIPO.get(cod_tipo, ("Discrete", "Input"))
        modulo_col = _normaliza_celula(row[idx["modulo"]]) if idx["modulo"] is not None else ""
        equip_cod = _normaliza_celula(row[idx["equipamento"]]) if idx["equipamento"] is not None else ""
        ident = resolver(bloco, sheet_name, modulo_col, equip_cod)
        sigla = str(row[idx["sigla"]] or "").strip() if idx["sigla"] is not None else ""
        indices = _parse_indices(row[idx["index"]]) if idx["index"] is not None and idx["index"] < len(row) else ()
        datatype = (
            "DoubleBit"
            if len(indices) == 2 and indices[0] != indices[1]
            else "SingleBit"
        )

        rec = SignalRecord(
            id=f"{sheet_name}:{i}",
            modulo=Modulo(ident.modulo, ident.origem),
            tipo_sinal=TipoSinal(categoria, datatype=datatype, direcao=direcao,
                                 categoria_confiavel=True),
            enderecamento=Enderecamento("DNP3", indices),
            descricoes=Descricoes(bruta, canonizar(remanescente, config, None)),
            eletrico=Eletrico(
                fase=ctx.fase,
                equipamento_alvo=_EQUIPAMENTO_POR_MODULO.get(equip_cod, ctx.equipamento_alvo),
                nome_equipamento=ident.equipamento,
                barra=ctx.barra,
            ),
        )

        # Lint NOME do cliente x regra (spec §2.4): aviso, não bloqueia.
        nome_cli = str(row[idx["nome"]] or "").strip() if idx["nome"] is not None else ""
        se = str(row[idx["subestacao"]] or "").strip() if idx["subestacao"] is not None else ""
        if nome_cli and sigla and se:
            mod_fmt = ident.modulo.replace(" ", "")
            calc = f"{se}_{mod_fmt}_{ident.equipamento or mod_fmt}_{sigla}"
            if calc != nome_cli:
                avisos.append(
                    f"{sheet_name}:{i}: NOME do cliente '{nome_cli}' difere do calculado '{calc}'"
                )

        if sigla and sigla.upper() in config.siglas_sem_ponto:
            revisao.append(ItemRevisao(
                replace(rec, sigla_sinal=sigla.upper(), status="revisao",
                        justificativa="comando TAP não modelado no ADMS (base real: 0 sinais COMTAP)"),
                motivo="comando_tap_nao_modelado",
            ))
            continue

        sp = lp.por_sigla(sigla) if sigla else None
        if sp is None:
            pendentes.append(rec)
        else:
            decididos.append(replace(rec, sigla_sinal=sigla, status="decidido"))

    return decididos, pendentes, revisao, avisos
```

Nota: `modulo_col` agora é normalizado (upper/sem acento) antes do resolvedor;
o teste existente `test_modulo_coluna_ja_numerada_mantem_comportamento` espera
`rec.modulo.nome == "LT 1"` — a guarda `_JA_NUMERADO` do resolvedor preserva o
valor normalizado `"LT 1"`, então o assert continua válido.

3e. `src/tdt/pipeline.py:593-594` — atualizar o caller e registrar avisos/revisão:

```python
        if header_homog is not None:
            decididos_homog, sinais, rev_homog, avisos_homog = estruturar_homogeneo(
                rows, header_homog, sn, lp, config)
            decididos.extend(decididos_homog)
            revisao.extend(rev_homog)
            for msg in avisos_homog:
                aud.evento("identidade_homogenea", msg, "AVISO")
```

- [ ] **Step 4: Rodar os testes do arquivo e a suíte de normalização**

Run: `python -m pytest tests/test_estruturador_homogeneo.py tests/test_identidade_homogenea.py -v`
Expected: todos PASS.

Run: `python -m pytest tests/ -x -q -k "estruturador or pipeline or identidade"`
Expected: PASS (nenhuma regressão nos vizinhos).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/estruturador_homogeneo.py src/tdt/normalizacao/vocabulario_tipo.py src/tdt/config.py src/tdt/contracts.py src/tdt/pipeline.py tests/test_estruturador_homogeneo.py
git commit -m "feat(homogeneo): nome por equipamento, COMTAP->revisao, tipo A/D, lint NOME

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Gate de unicidade de Remote Point Custom ID

**Files:**
- Modify: `src/tdt/engine_tdt.py` (nova função pública)
- Modify: `src/tdt/pipeline.py:525-533` (`gerar_tdt`) e `:712-720` (`executar`)
- Test: `tests/test_engine_tdt.py` (novos testes no fim do arquivo)

**Interfaces:**
- Consumes: `_nome_hierarquico`, `_remote_unit` (internos da engine), `ListaHomogenea`, `ItemRevisao`.
- Produces: `engine_tdt.particionar_custom_id_duplicado(lista: ListaHomogenea) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]` — grupos com Custom ID colidindo saem TODOS da lista e viram revisão com motivo `"custom_id_duplicado"`.

- [ ] **Step 1: Escrever o teste que falha**

Adicionar ao fim de `tests/test_engine_tdt.py`:

```python
def _rec_gate(id_, sigla, endereco, nome_equipamento=None):
    from tdt.contracts import (Descricoes, Eletrico, Enderecamento, Modulo,
                               SignalRecord, TipoSinal)
    return SignalRecord(
        id=id_,
        modulo=Modulo("LT3", "coluna:MODULO"),
        tipo_sinal=TipoSinal("Discrete"),
        enderecamento=Enderecamento("DNP3", (endereco,)),
        descricoes=Descricoes("43 - CHAVE LOCAL REMOTO", "chave local remoto"),
        eletrico=Eletrico(nome_equipamento=nome_equipamento),
        sigla_sinal=sigla, status="decidido",
    )


def test_gate_custom_id_duplicado_manda_grupo_inteiro_pra_revisao():
    from tdt.contracts import ListaHomogenea
    from tdt.engine_tdt import particionar_custom_id_duplicado
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(
        _rec_gate("LT 3:1", "43LR", 1),        # IMA_LT3_LT3_43LR
        _rec_gate("LT 3:2", "43LR", 22),       # IMA_LT3_LT3_43LR (colide)
        _rec_gate("LT 3:3", "CCFL", 2),        # único -> fica
        _rec_gate("LT 3:4", "43LR", 6, "89-14"),  # IMA_LT3_89-14_43LR -> fica
    ))
    lista_ok, rev = particionar_custom_id_duplicado(lista)
    assert [r.id for r in lista_ok.registros] == ["LT 3:3", "LT 3:4"]
    assert {it.registro.id for it in rev} == {"LT 3:1", "LT 3:2"}
    assert all(it.motivo == "custom_id_duplicado" for it in rev)


def test_gate_sem_duplicatas_nao_mexe():
    from tdt.contracts import ListaHomogenea
    from tdt.engine_tdt import particionar_custom_id_duplicado
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(
        _rec_gate("LT 3:1", "43LR", 1, "89-16"),
        _rec_gate("LT 3:2", "CCFL", 2),
    ))
    lista_ok, rev = particionar_custom_id_duplicado(lista)
    assert lista_ok == lista and rev == ()
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `python -m pytest tests/test_engine_tdt.py -x -q -k custom_id`
Expected: FAIL com `ImportError: cannot import name 'particionar_custom_id_duplicado'`

- [ ] **Step 3: Implementar**

3a. `src/tdt/engine_tdt.py` — imports: adicionar `ItemRevisao` ao import de contracts, `replace` de dataclasses e `defaultdict`:

```python
from collections import defaultdict
from dataclasses import replace

from tdt.contracts import ItemRevisao, ListaHomogenea, SignalRecord
```

Nova função (logo antes de `def gerar(`):

```python
def particionar_custom_id_duplicado(
    lista: ListaHomogenea,
) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]:
    """Gate de unicidade (spec 2026-07-10): o ADMS descarta remote points com
    Custom ID repetido no mesmo import. Grupos que colidem saem TODOS do TDT
    e vão para revisão — nunca saem calados no xlsx."""
    remote_unit = _remote_unit(lista.subestacao)
    por_cid: dict[str, list[SignalRecord]] = defaultdict(list)
    for rec in lista.registros:
        nome = _nome_hierarquico(
            lista.subestacao, rec.modulo.nome, rec.eletrico.nome_equipamento,
            rec.eletrico.barra, rec.sigla_sinal or "?",
        )
        cid = f"{nome}_{remote_unit}" if remote_unit else nome
        por_cid[cid].append(rec)
    duplicados = {id(r) for grupo in por_cid.values() if len(grupo) > 1 for r in grupo}
    if not duplicados:
        return lista, ()
    revisao = tuple(
        ItemRevisao(replace(r, status="revisao"), motivo="custom_id_duplicado")
        for r in lista.registros if id(r) in duplicados
    )
    restantes = tuple(r for r in lista.registros if id(r) not in duplicados)
    return replace(lista, registros=restantes), revisao
```

3b. `src/tdt/pipeline.py` — wiring nos dois pontos que chamam `engine_tdt.gerar`:

Em `executar` (hoje linhas ~712-720), logo após `lista = criador_lista_homogenea.montar(...)`:

```python
        lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
        lista, rev_dup = engine_tdt.particionar_custom_id_duplicado(lista)
        if rev_dup:
            aud.evento("engine", f"{len(rev_dup)} registros com Custom ID duplicado -> revisão", "AVISO")
            revisao.extend(rev_dup)
```

Em `gerar_tdt` (hoje linhas 525-533), mesma aplicação (revisão descartada como as demais deste caminho — os duplicados apenas não entram no xlsx):

```python
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    lista, _rev_dup = engine_tdt.particionar_custom_id_duplicado(lista)
    return engine_tdt.gerar(
        lista, template_path, lp, alias_v1=descricoes_por_sigla(DEFAULT_LISTA_ALIAS)
    )
```

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest tests/test_engine_tdt.py tests/test_gate_tdt_real.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py src/tdt/pipeline.py tests/test_engine_tdt.py
git commit -m "feat(engine): gate de unicidade de Remote Point Custom ID

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Lista padrão v8 + teste de domínio MM ⊆ catálogo real

**Files:**
- Create: `scripts/gerar_lista_padrao_v8.py`
- Create: `tests/fixtures/mm_catalogo_real.txt` (gerado pelo script)
- Create: `docs/Pontos Padrao ADMS_v8.xlsx` (gerado pelo script)
- Modify: `src/tdt/defaults.py:12` (`DEFAULT_LISTA` → v8)
- Modify: `src/tdt/cli.py:44` (default `--lista-padrao` → `defaults.DEFAULT_LISTA`)
- Test: `tests/test_lista_padrao_mm_dominio.py`

**Interfaces:**
- Consumes: `docs/Pontos Padrao ADMS_v7.xlsx`, `docs/Export_base_Full__27_fev_2026.xlsx`.
- Produces: v8 e fixture usados pelo teste de domínio e pela Task 5.

- [ ] **Step 1: Escrever o teste de domínio (falha: v8/fixture não existem)**

Criar `tests/test_lista_padrao_mm_dominio.py`:

```python
"""Domínio: todo MM da lista padrão deve existir no catálogo real do ADMS
(spec 2026-07-10 §2.3). Whitelist = refs quebradas conhecidas ainda não
corrigidas (spec §4 — AJ*/DSAB/VFAR, ZERO, ICC, CDCO, CCIC)."""
from pathlib import Path

import openpyxl
import pytest

from tdt.defaults import DEFAULT_LISTA

_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "mm_catalogo_real.txt"

# Pendências documentadas na spec §4 — remover daqui conforme a v8+n corrigir.
_WHITELIST = {
    "null@null___DESABILITADO@HABILITADO___Custom_S_TS_SV",   # AJ*/DSAB/VFAR
    "ZERAR@null___null@null___Custom_S_TC_SS",                # ZERO
    "RESET@null___null@null___Custom_S_TC_SS",                # ICC
    "MESTRE@INDIVIDUAL@COMANDO___MESTRE@INDIVIDUAL@COMANDO___Parallel___admsINV_D_TC",  # CDCO
    "CMD_RGE@null___RGE@CPFLT___Custom_S_TC_SS_CPFLT",        # CCIC
}


def test_mm_da_lista_padrao_existe_no_catalogo_real():
    if not Path(DEFAULT_LISTA).exists():
        pytest.fail(f"lista padrão não encontrada: {DEFAULT_LISTA}")
    catalogo = set(_FIXTURE.read_text(encoding="utf-8").splitlines())
    assert len(catalogo) > 400  # sanidade: fixture não truncada

    wb = openpyxl.load_workbook(DEFAULT_LISTA, read_only=True, data_only=True)
    ws = wb["DiscreteSignals"]
    linhas = ws.iter_rows(values_only=True)
    hdr = [str(c).strip().upper() if c else "" for c in next(linhas)]
    i_sig, i_mm = hdr.index("SINAL"), hdr.index("MM")
    fora = {}
    for r in linhas:
        sigla = str(r[i_sig]).strip() if r[i_sig] else ""
        mm = str(r[i_mm]).strip() if r[i_mm] else ""
        if sigla and mm and mm not in catalogo and mm not in _WHITELIST:
            fora.setdefault(mm, []).append(sigla)
    wb.close()
    assert fora == {}, f"MMs fora do catálogo real: {fora}"


def test_refs_corrigidas_na_v8():
    wb = openpyxl.load_workbook(DEFAULT_LISTA, read_only=True, data_only=True)
    ws = wb["DiscreteSignals"]
    linhas = ws.iter_rows(values_only=True)
    hdr = [str(c).strip().upper() if c else "" for c in next(linhas)]
    i_sig, i_mm = hdr.index("SINAL"), hdr.index("MM")
    mm = {str(r[i_sig]).strip(): str(r[i_mm]).strip() if r[i_mm] else ""
          for r in linhas if r[i_sig]}
    wb.close()
    assert mm["43LR"] == "null@null___REMOTO@LOCAL___Custom_S_TS_SS"
    for s in ("81U1", "81U2", "81U3", "81U4", "81U5"):
        assert mm[s] == "null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS"
```

Run: `python -m pytest tests/test_lista_padrao_mm_dominio.py -x -q`
Expected: FAIL (v8 e fixture ainda não existem).

- [ ] **Step 2: Escrever e rodar o script gerador**

Criar `scripts/gerar_lista_padrao_v8.py`:

```python
"""Gera docs/Pontos Padrao ADMS_v8.xlsx a partir da v7 (spec 2026-07-10 §2.3)
e extrai o catálogo real de MMs para tests/fixtures/mm_catalogo_real.txt.

Só altera a coluna MM de 43LR e 81U1-5 na sheet DiscreteSignals; o resto do
arquivo (todas as sheets, formatação) é preservado pelo openpyxl.
"""
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
V7 = RAIZ / "docs" / "Pontos Padrao ADMS_v7.xlsx"
V8 = RAIZ / "docs" / "Pontos Padrao ADMS_v8.xlsx"
EXPORT = RAIZ / "docs" / "Export_base_Full__27_fev_2026.xlsx"
FIXTURE = RAIZ / "tests" / "fixtures" / "mm_catalogo_real.txt"

CORRECOES = {
    "43LR": "null@null___REMOTO@LOCAL___Custom_S_TS_SS",
    "81U1": "null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS",
    "81U2": "null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS",
    "81U3": "null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS",
    "81U4": "null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS",
    "81U5": "null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS",
}


def gerar_v8() -> None:
    wb = openpyxl.load_workbook(V7)
    ws = wb["DiscreteSignals"]
    hdr = {str(c.value).strip().upper(): c.column for c in ws[1] if c.value}
    col_sig, col_mm = hdr["SINAL"], hdr["MM"]
    alteradas = 0
    for row in range(2, ws.max_row + 1):
        sigla = str(ws.cell(row, col_sig).value or "").strip()
        if sigla in CORRECOES:
            ws.cell(row, col_mm).value = CORRECOES[sigla]
            alteradas += 1
    assert alteradas == len(CORRECOES), f"esperava {len(CORRECOES)} siglas, alterou {alteradas}"
    wb.save(V8)
    print(f"v8 salva: {V8} ({alteradas} MMs corrigidos)")


def extrair_catalogo() -> None:
    wb = openpyxl.load_workbook(EXPORT, read_only=True, data_only=True)
    ws = wb["MessageMappings"]
    refs = sorted({
        str(r[0]).strip() for r in ws.iter_rows(values_only=True)
        if r[0] and isinstance(r[0], str) and "@" in r[0]
    })
    wb.close()
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text("\n".join(refs) + "\n", encoding="utf-8")
    print(f"catálogo: {FIXTURE} ({len(refs)} refs)")


if __name__ == "__main__":
    gerar_v8()
    extrair_catalogo()
```

Run: `PYTHONPATH=src python scripts/gerar_lista_padrao_v8.py`
Expected: `v8 salva: ... (6 MMs corrigidos)` e `catálogo: ... (484 refs)`.

- [ ] **Step 3: Apontar o app para a v8**

`src/tdt/defaults.py:12`:

```python
DEFAULT_LISTA = str(_DOCS / "Pontos Padrao ADMS_v8.xlsx")
```

`src/tdt/cli.py` — trocar o default hardcoded (linha 44) para usar defaults:

```python
from tdt.defaults import DEFAULT_LISTA
...
    g.add_argument("--lista-padrao", default=DEFAULT_LISTA)
```

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest tests/test_lista_padrao_mm_dominio.py tests/test_lista_padrao.py -v`
Expected: PASS (domínio + loader).

- [ ] **Step 5: Commit**

```bash
git add scripts/gerar_lista_padrao_v8.py "docs/Pontos Padrao ADMS_v8.xlsx" tests/fixtures/mm_catalogo_real.txt tests/test_lista_padrao_mm_dominio.py src/tdt/defaults.py src/tdt/cli.py
git commit -m "feat(lista-padrao): v8 corrige MM de 43LR e 81U1-5 + teste de dominio MM

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Regen do TDT IMA + verificação de aceite

**Files:**
- Create: `scripts/verificar_aceite_ima.py`
- Output: `output/TDT_IMA_v2.xlsx` (+ `.revisao.json`, `.log.txt`, `.auditoria.json`)

**Interfaces:**
- Consumes: tudo das Tasks 1-4 (pipeline completo + v8).
- Produces: evidência de aceite da spec §3 (não entra código de produção).

- [ ] **Step 1: Regenerar o TDT da IMA**

Run (demora minutos — carrega o modelo de embeddings):

```bash
PYTHONPATH=src python -m tdt.cli gerar docs/input_homogeneo_IMA.xlsx \
  --output output/TDT_IMA_v2.xlsx --modo homogeneo --subestacao IMA \
  --lista-padrao "docs/Pontos Padrao ADMS_v8.xlsx"
```

Expected: termina com `TDT: output/TDT_IMA_v2.xlsx | decididos=... revisão=...`.

- [ ] **Step 2: Escrever e rodar o script de aceite**

Criar `scripts/verificar_aceite_ima.py`:

```python
"""Aceite da spec 2026-07-10 §3 sobre o TDT regenerado da IMA:
1. zero Remote Point Custom ID duplicado;
2. todo MM preenchido existe no catálogo real (fixture);
3. DNP3_DiscreteAnalog contém IMA_TR6_TR6_TAP e IMA_TR7_TR7_TAP;
4. nenhum sinal espúrio *_CMD;
5. revisao.json contém COMTAP com motivo comando_tap_nao_modelado.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import openpyxl

RAIZ = Path(__file__).resolve().parent.parent
TDT = RAIZ / "output" / "TDT_IMA_v2.xlsx"
REVISAO = RAIZ / "output" / "TDT_IMA_v2.revisao.json"
CATALOGO = set((RAIZ / "tests" / "fixtures" / "mm_catalogo_real.txt")
               .read_text(encoding="utf-8").splitlines())

falhas: list[str] = []
wb = openpyxl.load_workbook(TDT, read_only=True, data_only=True)
nomes_da: set[str] = set()
for sheet in ("DNP3_DiscreteSignals", "DNP3_AnalogSignals", "DNP3_DiscreteAnalog"):
    if sheet not in wb.sheetnames:
        falhas.append(f"{sheet}: sheet ausente")
        continue
    linhas = wb[sheet].iter_rows(values_only=True)
    for _ in range(3):
        next(linhas)
    hdr = [str(c) if c else "" for c in next(linhas)]
    i_cid = next((i for i, c in enumerate(hdr) if "remote point custom" in c.lower()), None)
    i_mm = next((i for i, c in enumerate(hdr) if c == "Message Mapping"), None)
    cids: Counter[str] = Counter()
    for r in linhas:
        nome = r[0]
        if not nome:
            continue
        if str(nome).endswith("_CMD"):
            falhas.append(f"{sheet}: sinal espúrio {nome}")
        if sheet == "DNP3_DiscreteAnalog":
            nomes_da.add(str(nome))
        if i_cid is not None and r[i_cid]:
            cids[str(r[i_cid])] += 1
        if i_mm is not None and r[i_mm] and str(r[i_mm]).strip() not in CATALOGO:
            falhas.append(f"{sheet}: {nome}: MM fora do catálogo: {r[i_mm]}")
    dups = {k: v for k, v in cids.items() if v > 1}
    if dups:
        falhas.append(f"{sheet}: Custom IDs duplicados: {dups}")
wb.close()

for esperado in ("IMA_TR6_TR6_TAP", "IMA_TR7_TR7_TAP"):
    if esperado not in nomes_da:
        falhas.append(f"DNP3_DiscreteAnalog: {esperado} ausente")

itens = json.loads(REVISAO.read_text(encoding="utf-8"))
if not any(i["motivo"] == "comando_tap_nao_modelado" for i in itens):
    falhas.append("revisao.json: COMTAP não está em revisão com motivo comando_tap_nao_modelado")

if falhas:
    print("ACEITE FALHOU:")
    for f in falhas:
        print(" -", f)
    sys.exit(1)
print("ACEITE OK: TDT IMA sem duplicatas, MMs no catálogo, TAP presente, COMTAP em revisão.")
```

Run: `PYTHONPATH=src python scripts/verificar_aceite_ima.py`
Expected: `ACEITE OK: ...` (exit 0). Se falhar, corrigir a causa nas Tasks 1-4 antes de seguir (as falhas listadas apontam a task dona: nomes/dup → Task 1-3; MM → Task 4; TAP/COMTAP → Task 2).

- [ ] **Step 3: Regressão completa**

Run: `python -m pytest tests/ -q`
Expected: suíte inteira PASS (inclui `test_gate_tdt_real`).

- [ ] **Step 4: Commit**

```bash
git add scripts/verificar_aceite_ima.py
git commit -m "test(aceite): verificacao do TDT IMA regenerado (spec 2026-07-10)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

(Os artefatos `output/TDT_IMA_v2.*` não são commitados — `output/` é artefato local.)

---

### Task 6: DOX — ledger e tabelas de papéis

**Files:**
- Modify: `docs/AGENTS.md` (ledger de decisões)
- Modify: `src/tdt/AGENTS.md` (tabela de papéis, se listar módulos de normalização/engine)
- Modify: `src/tdt/normalizacao/AGENTS.md` (novo módulo `identidade_homogenea.py`)

**Interfaces:** documentação apenas; nenhum código.

- [ ] **Step 1: Ler a cadeia AGENTS.md antes de editar**

Ler `docs/AGENTS.md`, `src/tdt/AGENTS.md` e `src/tdt/normalizacao/AGENTS.md` e seguir o formato existente (regra do projeto: conferir ledger + tabela de papéis antes de afirmar wiring).

- [ ] **Step 2: Registrar**

- `src/tdt/normalizacao/AGENTS.md`: uma linha para `identidade_homogenea.py` no formato das existentes, ex.:
  `- \`identidade_homogenea.py\`: resolve módulo/equipamento do caminho homogêneo pelo bloco de cabeçalho (spec 2026-07-10). Exporta \`extrair_bloco()\`, \`resolver()\`, \`Identidade\`.`
- `src/tdt/AGENTS.md`: se a tabela de papéis citar `estruturador_homogeneo`/`engine_tdt`, atualizar: retorno 4-tupla do estruturador; gate `particionar_custom_id_duplicado` na engine; `DEFAULT_LISTA` = v8.
- `docs/AGENTS.md` (ledger): entrada datada 2026-07-10 resumindo: nomes por equipamento no homogêneo, gate custom id, v8 (43LR/81U*), COMTAP→revisão, `A/D`→DiscreteAnalog.

- [ ] **Step 3: Commit**

```bash
git add docs/AGENTS.md src/tdt/AGENTS.md src/tdt/normalizacao/AGENTS.md
git commit -m "docs(dox): ledger + papeis - identidade homogenea, gate custom id, v8

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```
