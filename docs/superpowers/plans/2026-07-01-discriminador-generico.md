# Discriminador genérico + gate anti-regressão — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o gate de regressão por endereço (nosso TDT × TDT real — a countermeasure), corrigir o pareamento genérico de catch-all (SGF), e medir o caminho do fix filho-vs-pai (79OK) — tudo validado em dados reais.

**Architecture:** Fase 0 entrega o measuring stick (`bench/gate_tdt_real.py` + `bench/casos_travados.csv` + `bench/regressao.py`). Fase 2 conserta `dc_pairer` (pareamento greedy por similaridade). Fase 1 é investigação que produz um doc de decisão para um plano futuro. Spec: `docs/superpowers/specs/2026-07-01-sp-discriminador-generico-design.md`.

**Tech Stack:** Python 3.14, openpyxl, rapidfuzz (já dependências), pytest.

## Global Constraints

- **Join key = INCOORDS (col 31, 0-based) das sheets `DNP3_DiscreteSignals` e `DNP3_AnalogSignals`.** Sigla = último token após `_` do `Signal Name` (col 0). Dados de sinal começam na row 5 (1-based); rows 1-4 são cabeçalho.
- **A descrição bruta NÃO está no TDT real** (col Description vazia) — nunca casar por texto entre nosso TDT e o real; só por endereço.
- **Baseline medido (2026-07-01): GTD 348/563 = 61.8% concordância.** Qualquer fix deve subir o agregado SEM baixar os 348 que já batem.
- **Validação de fechamento é em dado real:** `input_nao_homogeneo_1_GTD.xlsx` → compara com `docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx`. Nunca fechar só em `SignalRecord` sintético.
- **`dc_pairer`: comportamento 1 input + 1 output (fusão direta) e "sem outputs"/"sem inputs" NÃO mudam.** Só o ramo ambíguo (N×M) muda.
- Princípio do projeto: método novo entra como candidato/parâmetro calibrável, sem apagar o original; medir antes de wirar.

---

## Task 1: `gate_tdt_real` — comparação por endereço (núcleo puro)

**Files:**
- Create: `bench/gate_tdt_real.py`
- Test: `tests/test_gate_tdt_real.py`

**Interfaces:**
- Produces: `carregar_siglas_por_endereco(caminho: str) -> dict[int, tuple[str, str]]` (addr → (signal_name, sigla)); `comparar(nosso: str, real: str) -> Resultado` onde `Resultado` é um `dataclass` com `comum: int, iguais: int, pct: float, divergencias: list[tuple[int,str,str,str]]` (addr, sigla_real, sigla_nossa, nome_real).

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_gate_tdt_real.py`:

```python
import openpyxl
import pytest

from bench.gate_tdt_real import carregar_siglas_por_endereco, comparar


def _tdt_fake(path, linhas):
    """linhas = list[(signal_name, incoords)] na sheet DNP3_DiscreteSignals."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DNP3_DiscreteSignals"
    for _ in range(4):  # rows 1-4 cabeçalho
        ws.append([])
    for nome, addr in linhas:
        row = [None] * 32
        row[0] = nome
        row[31] = addr
        ws.append(row)
    wb.create_sheet("DNP3_AnalogSignals")  # vazia mas presente
    wb.save(path)


def test_carregar_extrai_sigla_ultimo_token_e_endereco(tmp_path):
    f = tmp_path / "t.xlsx"
    _tdt_fake(f, [("GTD_AL13_52-13_CCMO", 1706), ("GTD_LTGTA_89-2_DSEC", 16)])
    d = carregar_siglas_por_endereco(str(f))
    assert d == {1706: ("GTD_AL13_52-13_CCMO", "CCMO"), 16: ("GTD_LTGTA_89-2_DSEC", "DSEC")}


def test_comparar_conta_iguais_e_lista_divergencias(tmp_path):
    real = tmp_path / "real.xlsx"; nosso = tmp_path / "nosso.xlsx"
    _tdt_fake(real, [("GTD_AL13_52-13_CCMO", 100), ("GTD_LTGTA_52-1_BBFC", 7)])
    _tdt_fake(nosso, [("GTD_AL13_52-13_CCMO", 100), ("GTD_LTGTA_52-1_LIGAR", 7)])
    r = comparar(str(nosso), str(real))
    assert r.comum == 2
    assert r.iguais == 1
    assert r.pct == pytest.approx(50.0)
    assert (7, "BBFC", "LIGAR", "GTD_LTGTA_52-1_BBFC") in r.divergencias
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_gate_tdt_real.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'bench.gate_tdt_real'` (ou ImportError).

- [ ] **Step 3: Implementar `bench/gate_tdt_real.py`**

```python
"""Compara o TDT gerado com o TDT real por endereço DNP3 (INCOORDS).

A descrição bruta não existe no TDT real (col Description vazia); a única
chave estável entre os dois é o endereço (Input Coordinates, col 31 0-based).
Sigla = último token após '_' do Signal Name (col 0). Ver spec
docs/superpowers/specs/2026-07-01-sp-discriminador-generico-design.md.
"""
from __future__ import annotations

from dataclasses import dataclass

import openpyxl

_SHEETS = ("DNP3_DiscreteSignals", "DNP3_AnalogSignals")
_COL_NOME = 0
_COL_INCOORDS = 31
_PRIMEIRA_LINHA_DADOS = 5  # 1-based; rows 1-4 são cabeçalho


def carregar_siglas_por_endereco(caminho: str) -> dict[int, tuple[str, str]]:
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    out: dict[int, tuple[str, str]] = {}
    for sn in _SHEETS:
        if sn not in wb.sheetnames:
            continue
        ws = wb[sn]
        for r in ws.iter_rows(min_row=_PRIMEIRA_LINHA_DADOS, values_only=True):
            nome = r[_COL_NOME] if len(r) > _COL_NOME else None
            addr = r[_COL_INCOORDS] if len(r) > _COL_INCOORDS else None
            if not nome or not isinstance(addr, int):
                continue
            sigla = str(nome).split("_")[-1]
            out[addr] = (str(nome), sigla)
    wb.close()
    return out


@dataclass(frozen=True)
class Resultado:
    comum: int
    iguais: int
    pct: float
    divergencias: list[tuple[int, str, str, str]]  # addr, real, nosso, nome_real


def comparar(nosso: str, real: str) -> Resultado:
    d_nosso = carregar_siglas_por_endereco(nosso)
    d_real = carregar_siglas_por_endereco(real)
    comuns = sorted(set(d_nosso) & set(d_real))
    iguais = 0
    divergencias: list[tuple[int, str, str, str]] = []
    for a in comuns:
        nome_real, sig_real = d_real[a]
        _, sig_nosso = d_nosso[a]
        if sig_real.upper() == sig_nosso.upper():
            iguais += 1
        else:
            divergencias.append((a, sig_real, sig_nosso, nome_real))
    pct = 100.0 * iguais / len(comuns) if comuns else 0.0
    return Resultado(len(comuns), iguais, pct, divergencias)
```

Criar `bench/__init__.py` vazio se não existir (para `from bench.gate_tdt_real import ...` funcionar sob pytest com rootdir na raiz).

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/test_gate_tdt_real.py -v`
Expected: PASS.

- [ ] **Step 5: Sanidade em dado real (não é teste; confirma o baseline)**

Run: `python -c "from bench.gate_tdt_real import comparar; r=comparar('output/LISTA 1 - GTD/TDT3.xlsx','docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx'); print(r.comum, r.iguais, round(r.pct,1))"`
Expected: imprime `563 348 61.8` (± se o TDT3 mudar). Registra o baseline no relatório.

- [ ] **Step 6: Commit**

```bash
git add bench/gate_tdt_real.py bench/__init__.py tests/test_gate_tdt_real.py
git commit -m "feat(bench): gate_tdt_real compara sigla por endereço (nosso TDT × real)"
```

---

## Task 2: `casos_travados.csv` + `regressao.py` (orquestrador/gate)

**Files:**
- Create: `bench/casos_travados.csv`, `bench/regressao.py`
- Test: `tests/test_regressao_gate.py`

**Interfaces:**
- Consumes: `bench.gate_tdt_real.comparar`/`carregar_siglas_por_endereco`.
- Produces: `carregar_casos(caminho: str) -> list[Caso]` (`Caso` = dataclass `subestacao,endereco:int,sigla_esperada,origem,nota`); `checar_casos(nosso_tdt: str, casos: list[Caso]) -> list[tuple[Caso,str,bool]]` (caso, sigla_obtida, passou).

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/test_regressao_gate.py`:

```python
import openpyxl

from bench.regressao import Caso, carregar_casos, checar_casos


def _tdt_fake(path, linhas):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "DNP3_DiscreteSignals"
    for _ in range(4): ws.append([])
    for nome, addr in linhas:
        row = [None] * 32; row[0] = nome; row[31] = addr; ws.append(row)
    wb.create_sheet("DNP3_AnalogSignals"); wb.save(path)


def test_carregar_casos_le_csv(tmp_path):
    p = tmp_path / "casos.csv"
    p.write_text(
        "subestacao,endereco,sigla_esperada,origem,nota\n"
        "GTD,7,BBFC,2026-07-01 fix comando,verbo vazava\n",
        encoding="utf-8",
    )
    casos = carregar_casos(str(p))
    assert casos == [Caso("GTD", 7, "BBFC", "2026-07-01 fix comando", "verbo vazava")]


def test_checar_casos_passa_e_falha(tmp_path):
    tdt = tmp_path / "nosso.xlsx"
    _tdt_fake(tdt, [("GTD_LTGTA_52-1_BBFC", 7), ("GTD_AL_X_LIGAR", 8)])
    casos = [Caso("GTD", 7, "BBFC", "o", "n"), Caso("GTD", 8, "BBFC", "o", "n")]
    res = checar_casos(str(tdt), casos)
    passou = {c.endereco: ok for c, _, ok in res}
    assert passou == {7: True, 8: False}
```

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_regressao_gate.py -v`
Expected: FAIL com ImportError de `bench.regressao`.

- [ ] **Step 3: Implementar `bench/casos_travados.csv` (semente mínima) e `bench/regressao.py`**

`bench/casos_travados.csv` (semente — só o cabeçalho + 1 exemplo comentável; os casos reais entram na Task 3 após medição):

```csv
subestacao,endereco,sigla_esperada,origem,nota
```

`bench/regressao.py`:

```python
"""Gate de regressão: gera o nosso TDT do input real, compara com o TDT real
por endereço (gate_tdt_real) e checa os casos travados. Exit != 0 se algum
caso travado falha.

Uso: PYTHONPATH=src python bench/regressao.py
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass

from bench.gate_tdt_real import carregar_siglas_por_endereco, comparar


@dataclass(frozen=True)
class Caso:
    subestacao: str
    endereco: int
    sigla_esperada: str
    origem: str
    nota: str


def carregar_casos(caminho: str) -> list[Caso]:
    casos: list[Caso] = []
    with open(caminho, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            casos.append(Caso(
                row["subestacao"], int(row["endereco"]),
                row["sigla_esperada"], row["origem"], row["nota"],
            ))
    return casos


def checar_casos(nosso_tdt: str, casos: list[Caso]) -> list[tuple[Caso, str, bool]]:
    por_addr = carregar_siglas_por_endereco(nosso_tdt)
    out: list[tuple[Caso, str, bool]] = []
    for c in casos:
        obtida = por_addr.get(c.endereco, (None, ""))[1]
        out.append((c, obtida, obtida.upper() == c.sigla_esperada.upper()))
    return out


# Pares (input real, TDT real) — a fonte de verdade da validação de fechamento.
_PARES = [
    ("GTD", "docs/input_nao_homogeneo_1_GTD.xlsx",
     "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx"),
]
_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA = "docs/Pontos Padrao ADMS_v2.xlsx"


def _gerar_nosso_tdt(input_path: str, saida: str) -> None:
    """Roda o pipeline real e salva o TDT gerado em `saida`."""
    import warnings, logging
    warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
    from tdt.config import Config
    from tdt.dados.encoder import criar_encoder
    from tdt import pipeline
    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)
    _res, wb = pipeline.executar(input_path, _TEMPLATE, _LISTA, config=cfg, encoder=enc)
    wb.save(saida)


def main() -> int:
    casos = carregar_casos("bench/casos_travados.csv")
    falhas = 0
    for se, inp, real in _PARES:
        saida = f"bench/_tdt_gerado_{se}.xlsx"
        _gerar_nosso_tdt(inp, saida)
        r = comparar(saida, real)
        print(f"[{se}] comum={r.comum} iguais={r.iguais} pct={r.pct:.1f}%")
        for c, obtida, ok in checar_casos(saida, [x for x in casos if x.subestacao == se]):
            print(f"   {'PASS' if ok else 'FAIL'} addr={c.endereco} "
                  f"esperado={c.sigla_esperada} obtido={obtida or '—'} ({c.nota})")
            if not ok:
                falhas += 1
    print(f"\n{'GATE OK' if falhas == 0 else f'GATE FALHOU: {falhas} caso(s)'}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `python -m pytest tests/test_regressao_gate.py -v`
Expected: PASS (testa `carregar_casos`/`checar_casos`; NÃO roda o pipeline pesado).

- [ ] **Step 5: Commit**

```bash
git add bench/casos_travados.csv bench/regressao.py tests/test_regressao_gate.py
git commit -m "feat(bench): regressao.py — gate de casos travados sobre TDT real"
```

---

## Task 3: Semear casos travados + baseline + documentar no DOX

**Files:**
- Modify: `bench/casos_travados.csv`, `AGENTS.md` (root, seção Verification)
- Modify: `.memory/known-bugs.md`

**Interfaces:** nenhuma nova — usa Task 1/2.

- [ ] **Step 1: Rodar o gate completo em dado real e capturar divergências**

Run: `PYTHONPATH=src python bench/regressao.py`
Expected: imprime `[GTD] comum=... iguais=... pct=...` (~61.8%) e `GATE OK` (casos vazio ainda). Anota o pct baseline.

Depois, listar as divergências candidatas a caso travado:
Run: `python -c "from bench.gate_tdt_real import comparar; [print(d) for d in comparar('bench/_tdt_gerado_GTD.xlsx','docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx').divergencias[:40]]"`

- [ ] **Step 2: Semear `bench/casos_travados.csv`**

Adicionar linhas para as divergências reais confirmadas como bugs (endereços do output do Step 1; siglas esperadas = as do TDT real). Exemplo do formato (usar os endereços reais medidos):

```csv
subestacao,endereco,sigla_esperada,origem,nota
GTD,7,BBFC,2026-07-01 baseline,verbo LIGAR vazava como sigla
GTD,62,50F1,2026-07-01 baseline,sigla truncada ao digito de estagio
GTD,16,DSEC,2026-07-01 baseline,seccionadora classificada como 43LR
GTD,67,51N1,2026-07-01 baseline,estagio perdido (51N em vez de 51N1)
```

Estes começam FALHANDO (são os bugs). O gate documenta o estado atual; as Fases 1-3 os viram PASS. **Um caso que já passa também entra** quando for corrigido, pra travar contra regressão futura.

- [ ] **Step 3: Documentar o gate no `AGENTS.md` raiz**

Na seção `## Verification` do `AGENTS.md` raiz, adicionar:

```markdown
- Gate de regressão por sinal real: `PYTHONPATH=src python bench/regressao.py`
  compara o TDT gerado do input real com o TDT real por endereço e checa
  `bench/casos_travados.csv`. Rodar no closeout de mudança de matching/estrutura.
  Ao corrigir um sinal, adicionar seu caso ao CSV (trava contra regressão).
```

- [ ] **Step 4: Registrar em `.memory/known-bugs.md`**

Adicionar entrada resumindo: baseline 61.8% GTD, os 4 padrões de bug (comando→sigla, truncamento de estágio, seccionadora, estágio perdido), e que o gate `bench/regressao.py` + `casos_travados.csv` é a countermeasure.

- [ ] **Step 5: Commit**

```bash
git add bench/casos_travados.csv AGENTS.md .memory/known-bugs.md
git commit -m "docs(bench): semeia casos travados + baseline 61.8% + doc do gate no DOX"
```

---

## Task 4: Fase 2 — pareamento genérico de catch-all no `dc_pairer`

**Files:**
- Modify: `src/tdt/dc_pairer.py` (só o ramo ambíguo de `parear`), `src/tdt/config.py` (novo knob)
- Test: `tests/test_dc_pairer.py` (adicionar casos)

**Interfaces:**
- Consumes: `config.Config.limiar_pareamento_similaridade` (novo).
- Produces: `parear(registros, config=None)` — assinatura estendida com `config` opcional (retrocompat: `None` usa default).

- [ ] **Step 1: Escrever os testes que falham**

O helper `_rec` existente em `tests/test_dc_pairer.py` é `_rec(rid, sigla, direcao, indices)` e usa `Descricoes(sigla, sigla)` — inútil para testar similaridade de descrição (todo SGF teria descrição "SGF"). Adicionar um helper novo `_rec_desc` (descrição e módulo explícitos) e os testes:

```python
def _rec_desc(rid, sigla, direcao, desc, modulo, indices):
    from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
    return SignalRecord(
        id=rid, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc), sigla_sinal=sigla, status="decidido",
    )


def test_catchall_pareia_por_similaridade_e_deixa_sem_par_standalone():
    # 1 output "Excluir" + 2 inputs "Excluida"/"Atuado", todos sigla SGF, mesmo modulo.
    out = _rec_desc("o", "SGF", "Output", "PROTECAO SENSIVEL TERRA SGF EXCLUIR", "GTD_11", (20,))
    in_exc = _rec_desc("i1", "SGF", "Input", "PROTECAO SGF EXCLUIDA", "GTD_11", (71,))
    in_atu = _rec_desc("i2", "SGF", "Input", "PROTECAO SGF ATUADO", "GTD_11", (72,))
    saida, revisao = parear([out, in_exc, in_atu])
    dirs = sorted(r.tipo_sinal.direcao for r in saida)
    # Excluir+Excluida fundem (InputOutput); Atuado sobra como Input standalone.
    assert "InputOutput" in dirs
    assert "Input" in dirs           # Atuado standalone, decidido
    assert revisao == ()             # nada vai pra revisao


def test_catchall_output_orfao_vai_revisao():
    # 2 outputs, 1 input; o 2o output nao casa nada -> sobra -> revisao.
    out1 = _rec_desc("o1", "SGF", "Output", "PROTECAO SGF EXCLUIR", "GTD_11", (20,))
    out2 = _rec_desc("o2", "SGF", "Output", "ZZZ QQQ WWW NADA A VER", "GTD_11", (21,))
    inp = _rec_desc("i1", "SGF", "Input", "PROTECAO SGF EXCLUIDA", "GTD_11", (71,))
    saida, revisao = parear([out1, out2, inp])
    assert any(r.tipo_sinal.direcao == "InputOutput" for r in saida)
    assert len(revisao) == 1
    assert revisao[0].motivo == "pareamento_ambiguo"


def test_um_input_um_output_ainda_funde_direto():
    out = _rec_desc("o", "DJF1", "Output", "DISJ DESLIGAR LIGAR", "GTD_11", (18,))
    inp = _rec_desc("i", "DJF1", "Input", "DISJ DESLIGADO", "GTD_11", (35,))
    saida, revisao = parear([out, inp])
    assert len(saida) == 1 and saida[0].tipo_sinal.direcao == "InputOutput"
    assert revisao == ()
```

Nota: o `_chave` do `dc_pairer` inclui `nome_equipamento` (aqui `None` em todos) → os 3 SGF caem no mesmo grupo. Confirmar que os testes 1:1 pré-existentes (que usam `_rec` e módulo `LT_GTA`) continuam passando.

- [ ] **Step 2: Rodar e confirmar que falha**

Run: `python -m pytest tests/test_dc_pairer.py -v -k "catchall or funde_direto"`
Expected: FAIL — hoje o ramo N×M manda tudo pra `pareamento_ambiguo`, então `test_catchall_pareia...` falha (revisao não vazia, sem InputOutput).

- [ ] **Step 3: Adicionar o knob em `config.py`**

Em `src/tdt/config.py`, dentro de `class Config`, adicionar (perto dos outros thresholds):

```python
    # Pareamento D+C de catch-all: similaridade mínima (rapidfuzz token_sort_ratio,
    # 0-100) para casar 1 Output com 1 Input quando N inputs/M outputs compartilham
    # a mesma sigla no módulo. Abaixo disso, output órfão vai pra revisão.
    limiar_pareamento_similaridade: float = 60.0
```

- [ ] **Step 4: Implementar o ramo greedy em `dc_pairer.parear`**

Em `src/tdt/dc_pairer.py`, trocar a assinatura e o ramo ambíguo:

```python
from rapidfuzz import fuzz
```

```python
def parear(
    registros: list[SignalRecord],
    config=None,
) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]:
    limiar = 60.0 if config is None else config.limiar_pareamento_similaridade
    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        grupos[_chave(rec)].append(rec)

    saida: list[SignalRecord] = []
    revisao: list[ItemRevisao] = []

    for grupo in grupos.values():
        inputs = [r for r in grupo if r.tipo_sinal.direcao == "Input"]
        outputs = [r for r in grupo if r.tipo_sinal.direcao == "Output"]

        if not outputs:
            saida.extend(grupo)
        elif not inputs:
            saida.extend(grupo)
        elif len(inputs) == 1 and len(outputs) == 1:
            saida.append(fundir(inputs[0], outputs[0]))
        else:
            saida_pares, sobra_rev = _parear_catchall(inputs, outputs, limiar)
            saida.extend(saida_pares)
            revisao.extend(sobra_rev)

    return tuple(saida), tuple(revisao)


def _parear_catchall(inputs, outputs, limiar):
    """Greedy: casa cada Output com o Input de maior similaridade de descrição
    (>= limiar). Inputs sem par -> Input standalone (saída). Outputs sem par ->
    revisão. Ver spec discriminador-genérico Fase 2.
    """
    candidatos = []
    for oi, o in enumerate(outputs):
        for ii, i in enumerate(inputs):
            sim = fuzz.token_sort_ratio(
                o.descricoes.normalizada, i.descricoes.normalizada
            )
            candidatos.append((sim, oi, ii))
    candidatos.sort(reverse=True)

    usados_o: set[int] = set()
    usados_i: set[int] = set()
    saida: list[SignalRecord] = []
    for sim, oi, ii in candidatos:
        if sim < limiar:
            break
        if oi in usados_o or ii in usados_i:
            continue
        saida.append(fundir(inputs[ii], outputs[oi]))
        usados_o.add(oi)
        usados_i.add(ii)

    for ii, inp in enumerate(inputs):
        if ii not in usados_i:
            saida.append(inp)  # standalone decidido

    revisao = [
        ItemRevisao(o, motivo="pareamento_ambiguo")
        for oi, o in enumerate(outputs) if oi not in usados_o
    ]
    return saida, revisao
```

- [ ] **Step 5: Rodar e confirmar que passa; suíte de dc_pairer inteira**

Run: `python -m pytest tests/test_dc_pairer.py -v`
Expected: PASS (novos + os pré-existentes — confirmar que nenhum caso 1:1 ou "sem output" regrediu).

- [ ] **Step 6: Verificar que o chamador (`pipeline`) ainda funciona sem passar config, e opcionalmente passá-lo**

`pipeline.executar` chama `dc_pairer.parear(decididos)` (sem config) — retrocompat mantida pelo default. Opcional: passar `config` na chamada de `pipeline` para o knob valer. Localizar as 2 chamadas (`pipeline.gerar_tdt` e `pipeline.executar`) e passar `config`/`cfg` se disponível no escopo. Rodar a suíte de pipeline:

Run: `python -m pytest tests/test_pipeline*.py -q`
Expected: PASS.

- [ ] **Step 7: Validar em dado real + travar caso SGF**

Run: `PYTHONPATH=src python bench/regressao.py`
Confirmar que o pct agregado NÃO baixou e que sinais SGF antes em `pareamento_ambiguo` agora pareiam/standalone. Adicionar um caso SGF a `bench/casos_travados.csv` (endereço de um SGF "Excluída" que agora resolve) e re-rodar: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/tdt/dc_pairer.py src/tdt/config.py tests/test_dc_pairer.py bench/casos_travados.csv
git commit -m "feat(dc_pairer): pareamento greedy de catch-all por similaridade (Fase 2)"
```

---

## Task 5: Fase 1 — investigação filho-vs-pai (produz doc de decisão)

**Files:**
- Create: `bench/diag_filho_vs_pai.py` (script de medição), `docs/superpowers/specs/2026-07-01-spD3-filho-vs-pai-achados.md` (findings)

**Interfaces:** usa `pipeline._construir_scorers`/`_classificar_sinal` (como o repro já feito) + `gate_tdt_real` para o universo real.

Esta task **não implementa o fix** — mede para escolher o mecanismo (a spec exige "medir antes de wirar"). O fix filho-vs-pai vira um plano próprio escrito a partir deste doc.

- [ ] **Step 1: Medir a frequência do problema no GT real**

Escrever `bench/diag_filho_vs_pai.py` que: para cada divergência do gate onde a sigla real é uma variante (tem discriminador) e a nossa é o prefixo genérico da mesma família (ex. real=`50F1` nosso=`1` ou `50`; real=`79OK` nosso=`79`), conta e agrupa por família. Rodar e registrar quantas das ~215 divergências GTD são desse padrão.

Run: `PYTHONPATH=src python bench/diag_filho_vs_pai.py`

- [ ] **Step 2: Medir se embedding melhor fecha o gap semântico**

Estender o script para, num conjunto de descrições-alvo (ex. "Religamento (79) - Bem Sucedido"), imprimir o ranking do filho correto (79OK) com: (a) MiniLM + corpus atual, (b) MiniLM + `_corpus_enriquecido`, (c) e5 (`config.modelo_embedding` trocado para o e5 dormente). Registrar se algum ranqueia o filho certo acima do pai **genericamente** (sem hardcode).

- [ ] **Step 3: Escrever o doc de achados**

`docs/superpowers/specs/2026-07-01-spD3-filho-vs-pai-achados.md`: frequência do padrão no GT real, resultado da comparação de embeddings, e a **recomendação de mecanismo** (regra estrutural pai-nu + melhor embedding medido; ou, se nenhum embedding fecha, o escopo mínimo de sinônimo medido). Este doc é a entrada do plano de implementação da Fase 1.

- [ ] **Step 4: Commit**

```bash
git add bench/diag_filho_vs_pai.py docs/superpowers/specs/2026-07-01-spD3-filho-vs-pai-achados.md
git commit -m "diag(spD3): mede frequência filho-vs-pai + efeito de embedding (Fase 1 investigação)"
```

---

## Fora deste plano (planos seguintes, escritos a partir dos achados)

- **Fase 1 impl:** o fix filho-vs-pai, com o mecanismo escolhido na Task 5. Gate: benchmark 28 pares sem regressão + GT real sobe + casos 79* viram PASS.
- **Fase 3:** varredura das regressões do batch 30-jun (comando→sigla, truncamento de estágio, seccionadora), priorizada pela lista de divergências do gate; cada correção trava seu caso.
