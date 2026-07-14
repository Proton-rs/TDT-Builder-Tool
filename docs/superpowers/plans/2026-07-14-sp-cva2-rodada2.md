# SP-CVA2 — 2ª rodada CVA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir as observações da 2ª rodada de revisão CVA (BC2: comando "Abrir/Fechar" vira DJA1 e não pareia com o status DJF1; CVA11: comandos classificados como Input) e as melhorias derivadas (spec `docs/superpowers/specs/2026-07-14-sp-cva2-rodada2-design.md`, eixos E1-E6).

**Architecture:** Correções pontuais em módulos existentes do pipeline (pareamento_polaridade, dc_pairer, estruturador, vocabulario_tipo, analise_colunas, identidade_modulo, normalizador_estrutural, engine_tdt) + 2 wirings novos no pipeline (fusão MultiCoord pré-pairer; gate de endereço duplicado no boundary). UI só na Task 11. Cada task de pipeline tem gate individual.

**Tech Stack:** Python 3.12, pytest, openpyxl, rapidfuzz, PySide6 (Task 11).

## Global Constraints

- Branch de trabalho: `feature/sp-cva2-rodada2` (criada na Task 0).
- Gate de regressão: `PYTHONPATH=src python -m bench.regressao` — `pct >= baseline` (congelado na Task 0) em TODA task que toca pipeline (Tasks 1-10), medido individualmente antes do commit.
- Suíte: `python -m pytest -q tests/` verde antes de cada commit.
- TDD: teste falhando primeiro, sempre. Atalhos deliberados marcados `# ponytail:` com teto e upgrade path.
- Nunca editar os `.xlsx` de origem (`docs/`); o input real CVA é PESSOAL (fora do repo): `C:\Users\vinic\Documents\docs importantes\RGE\CVA\CVA - Pontos Por Equipamentos DNP_V03 - COS - resumida.xlsx`.
- Convenção interna de fases continua `CA`; tradução PhaseCode só no boundary (não tocar — já implementado no SP-CVA).
- Knobs calibráveis só em `src/tdt/config.py` (nenhum novo knob é necessário neste plano).
- Commits em Conventional Commits, subject ≤ 50 chars quando possível.

---

## Fase 0 — Baseline

### Task 0: Branch + congelar baseline do gate

**Files:**
- Create: `bench/resultados/spCVA2_baseline.txt`

- [ ] **Step 1: Criar a branch**

```bash
git checkout -b feature/sp-cva2-rodada2
```

- [ ] **Step 2: Rodar o gate**

Run: `PYTHONPATH=src python -m bench.regressao`
Expected: imprime `pct` (e contagens). Anotar o valor.

- [ ] **Step 3: Registrar em `bench/resultados/spCVA2_baseline.txt`**

```
baseline spCVA2 — 2026-07-14
pct=<valor impresso>
commit=<git rev-parse --short HEAD>
```

- [ ] **Step 4: Commit**

```bash
git add bench/resultados/spCVA2_baseline.txt
git commit -m "test(gate): congela baseline spCVA2"
```

---

## Fase 1 — Pareamento de posição (E1, E2)

### Task 1: E1 — seleção do par ligado/desligado por particípio exato

Causa (spec §2 item 1): `forcar_polaridade_equipamento` seleciona candidatos ao par por PREFIXO (`ABERT`) e o token `ABERTURA` de "Supervisão Circ Abertura" infla `desligado` → `len(desligado)>1` → par nunca forçado no grupo real da BC2.

**Files:**
- Modify: `src/tdt/pareamento_polaridade.py:131-132` (seleção do par) + novos helpers no topo do módulo
- Test: `tests/test_pareamento_polaridade.py`

**Interfaces:**
- Consumes: `forcar_polaridade_equipamento(registros, config)` (existente, assinatura inalterada).
- Produces: helper interno `_polaridade_pura(rec) -> str | None` ("ligado" | "desligado" | None). `eh_texto_de_posicao` NÃO muda (continua por prefixo — outro consumidor, outro papel).

- [ ] **Step 1: Escrever o teste que falha (grupo real BC2 com ruído de supervisão)**

Adicionar em `tests/test_pareamento_polaridade.py`:

```python
def test_par_forcado_mesmo_com_ruido_de_supervisao_no_grupo():
    """SP-CVA2 E1 — grupo real BC2: 'SUPERVISAO CIRC ABERTURA' tem token
    ABERTURA que batia o prefixo ABERT e inflava `desligado` -> par nunca
    forçado -> comando ia pro scorer e virava DJA1. A seleção do PAR passa a
    exigir palavra exata de particípio (ABERTO/FECHADO/...)."""
    grupo = [
        _rec("a", "FECHADO", nome_equip="52-06", descricao="52 06 FECHADO"),
        _rec("b", "ABERTO", nome_equip="52-06", descricao="52 06 ABERTO"),
        _rec("s1", "X", nome_equip="52-06", descricao="52 06 SUPERVISAO CIRC FECHAMENTO"),
        _rec("s2", "X", nome_equip="52-06", descricao="52 06 SUPERVISAO CIRC ABERTURA"),
        _rec("s3", "X", nome_equip="52-06", descricao="52 06 SUPERVISAO CIRCUITO ABERTURA"),
        _rec("m", "X", nome_equip="52-06", descricao="52 06 MOLA DESCARREGADA"),
        _rec("c", "X", nome_equip="52-06", descricao="52 06 ABRIR FECHAR", direcao="Output"),
    ]
    by_id, rev = _parear(grupo)
    assert by_id["a"].sigla_sinal == "DJF1" and by_id["a"].status == "decidido"
    assert by_id["b"].sigla_sinal == "DJF1"
    # comando toggle do mesmo equipamento converge junto (código existente)
    assert by_id["c"].sigla_sinal == "DJF1" and by_id["c"].status == "decidido"
    # ruído não é forçado
    assert by_id["s1"].sigla_sinal is None
    assert by_id["s2"].sigla_sinal is None
    assert not rev
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_pareamento_polaridade.py::test_par_forcado_mesmo_com_ruido_de_supervisao_no_grupo`
Expected: FAIL — `by_id["a"].sigla_sinal is None` (par não forçado hoje).

- [ ] **Step 3: Implementar**

Em `src/tdt/pareamento_polaridade.py`, adicionar após `_eh_comando_toggle` (linha ~52):

```python
# Seleção do PAR ligado/desligado por PALAVRA EXATA de particípio — não por
# prefixo. 'ABERTURA' (Supervisão Circ Abertura) bate o prefixo ABERT mas não
# é estado de posição; com prefixo, o grupo real infla `desligado` e o par
# nunca é forçado (SP-CVA2 E1). Prefixos continuam em eh_texto_de_posicao
# (gate de decisão — papel diferente).
_PARTICIPIOS_LIGADO = frozenset({"LIGADO", "LIGADA", "FECHADO", "FECHADA"})
_PARTICIPIOS_DESLIGADO = frozenset({"DESLIGADO", "DESLIGADA", "ABERTO", "ABERTA"})


def _polaridade_pura(rec: SignalRecord) -> str | None:
    """"ligado"/"desligado" quando o texto tem exatamente UMA polaridade em
    palavra exata de particípio; None p/ comando (Output), toggle ou ruído."""
    if rec.tipo_sinal.direcao == "Output":
        return None
    tokens = set(rec.descricoes.normalizada.upper().split())
    lig = bool(tokens & _PARTICIPIOS_LIGADO)
    des = bool(tokens & _PARTICIPIOS_DESLIGADO)
    if lig and not des:
        return "ligado"
    if des and not lig:
        return "desligado"
    return None
```

E substituir a seleção dentro de `forcar_polaridade_equipamento` (linhas 131-132):

```python
        ligado = [r for r in grupo if _polaridade_pura(r) == "ligado"]
        desligado = [r for r in grupo if _polaridade_pura(r) == "desligado"]
```

- [ ] **Step 4: Rodar o teste novo e a suíte**

Run: `python -m pytest -q tests/test_pareamento_polaridade.py`
Expected: PASS (novo + existentes; os existentes usam textos com particípio em palavra exata — "LIGADO", "SEC CARGA ABERTO" etc.).
Se algum teste existente usar ABREVIAÇÃO real (ex. "DESL"), adicionar o token exato ao frozenset correspondente — nunca voltar a prefixo.

Run: `python -m pytest -q tests/`
Expected: PASS.

- [ ] **Step 5: Gate**

Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline` (Task 0). Se cair, investigar antes de commitar (parar e reportar).

- [ ] **Step 6: Commit**

```bash
git add src/tdt/pareamento_polaridade.py tests/test_pareamento_polaridade.py
git commit -m "fix(pareamento): par de posicao por participio exato (ruido ABERTURA)"
```

### Task 2: E2 — reconciliação comando↔status de posição no dc_pairer

Rede de segurança quando o par NÃO foi forçado e o scorer divergiu (comando DJA1 × status DJF1): re-chavear o comando toggle pra sigla de posição do status do MESMO equipamento — só quando inequívoco; senão revisão `posicao_divergente`.

**Files:**
- Modify: `src/tdt/pareamento_polaridade.py` (exports públicos no fim do módulo)
- Modify: `src/tdt/dc_pairer.py` (novo `_reconciliar_posicao`, chamado no topo de `parear`)
- Modify: `src/tdt/contracts.py:149` (docstring de motivo — adicionar `posicao_divergente`)
- Test: `tests/test_dc_pairer.py`

**Interfaces:**
- Consumes: `pareamento_polaridade._SIGLAS_POSICAO`, `_eh_comando_toggle` — expostos como `SIGLAS_POSICAO` e `eh_comando_toggle` (aliases públicos).
- Produces: `dc_pairer._reconciliar_posicao(registros) -> tuple[list[SignalRecord], list[ItemRevisao]]`; `parear` passa a emitir motivo novo `"posicao_divergente"`.

- [ ] **Step 1: Expor aliases públicos em `pareamento_polaridade.py`** (fim do módulo)

```python
# Consumidos por dc_pairer (SP-CVA2 E2) — aliases públicos, mesma referência.
SIGLAS_POSICAO = _SIGLAS_POSICAO
eh_comando_toggle = _eh_comando_toggle
```

- [ ] **Step 2: Escrever os testes que falham**

Adicionar em `tests/test_dc_pairer.py` (usar/reaproveitar o helper `_rec` local do arquivo se existir; senão este, autocontido):

```python
from tdt.config import Config
from tdt.contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt import dc_pairer


def _rec_pos(rid, sigla, direcao, indices, desc, equip="52-06", modulo="BC1"):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(equipamento_alvo="Disjuntor", nome_equipamento=equip),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_reconcilia_comando_toggle_com_sigla_do_status_de_posicao():
    """SP-CVA2 E2: comando 'ABRIR FECHAR' decidido DJA1 pelo scorer, status do
    mesmo equipamento decidido DJF1 -> re-chaveia o comando pra DJF1 (status
    único e inequívoco)."""
    status = _rec_pos("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    comando = _rec_pos("BC2:14", "DJA1", "Output", [90], "52 06 ABRIR FECHAR")
    novos, rev = dc_pairer._reconciliar_posicao([status, comando])
    by_id = {r.id: r for r in novos}
    assert by_id["BC2:14"].sigla_sinal == "DJF1"
    assert not rev


def test_posicao_divergente_vai_pra_revisao_quando_status_ambiguo():
    """Dois status de posição com siglas DIFERENTES no mesmo equipamento:
    não re-chaveia — revisão `posicao_divergente`."""
    s1 = _rec_pos("X:1", "DJF1", "Input", [10], "52 06 ABERTO")
    s2 = _rec_pos("X:2", "DJA1", "Input", [11], "52 06 FECHADO NA")
    comando = _rec_pos("X:3", "SECC", "Output", [90], "52 06 ABRIR FECHAR")
    novos, rev = dc_pairer._reconciliar_posicao([s1, s2, comando])
    assert [it.motivo for it in rev] == ["posicao_divergente"]
    assert all(r.id != "X:3" for r in novos)


def test_reconciliacao_nao_toca_comando_nao_toggle_nem_sigla_fora_do_catalogo():
    status = _rec_pos("Y:1", "DJF1", "Input", [10], "52 06 ABERTO")
    cmd_nao_toggle = _rec_pos("Y:2", "CDC", "Output", [20], "COMANDO SUBIR DESCER")
    novos, rev = dc_pairer._reconciliar_posicao([status, cmd_nao_toggle])
    by_id = {r.id: r for r in novos}
    assert by_id["Y:2"].sigla_sinal == "CDC"
    assert not rev


def test_parear_funde_apos_reconciliacao():
    """Fim-a-fim no parear: comando DJA1 + status DJF1 do mesmo equipamento
    fundem (antes: comando_sem_discreto)."""
    status = _rec_pos("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    comando = _rec_pos("BC2:14", "DJA1", "Output", [90], "52 06 ABRIR FECHAR")
    pareados, rev = dc_pairer.parear([status, comando], Config())
    assert not any(it.motivo == "comando_sem_discreto" for it in rev)
    rw = [r for r in pareados if r.tipo_sinal.direcao == "InputOutput"]
    assert len(rw) == 1 and rw[0].enderecamento.indices_saida == (90,)
```

- [ ] **Step 3: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_dc_pairer.py -k "reconcilia or divergente"`
Expected: FAIL — `AttributeError: module 'tdt.dc_pairer' has no attribute '_reconciliar_posicao'`.

- [ ] **Step 4: Implementar em `dc_pairer.py`**

Imports no topo (junto dos existentes):

```python
from tdt.pareamento_polaridade import SIGLAS_POSICAO, eh_comando_toggle
```

Nova função antes de `parear`:

```python
def _reconciliar_posicao(
    registros: list[SignalRecord],
) -> tuple[list[SignalRecord], list[ItemRevisao]]:
    """Comando toggle ('Abrir/Fechar') com sigla de POSIÇÃO divergente do
    status de posição do MESMO (módulo, equipamento) re-chaveia pra sigla do
    status — rede de segurança quando o scorer divergiu (SP-CVA2 E2). Só
    quando o status é único e inequívoco; status ambíguo (2 siglas de posição
    distintas) manda o comando pra revisão `posicao_divergente`. Determinístico,
    restrito ao catálogo SIGLAS_POSICAO; nunca mexe em score."""
    por_equip: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for r in registros:
        if r.eletrico.nome_equipamento:
            por_equip[(r.modulo.nome, r.eletrico.nome_equipamento)].append(r)

    troca: dict[str, str] = {}
    divergentes: set[str] = set()
    for grupo in por_equip.values():
        siglas_status = {
            (r.sigla_sinal or "").upper()
            for r in grupo
            if r.tipo_sinal.direcao == "Input"
            and (r.sigla_sinal or "").upper() in SIGLAS_POSICAO
        }
        cmds = [
            r for r in grupo
            if r.tipo_sinal.direcao == "Output"
            and (r.sigla_sinal or "").upper() in SIGLAS_POSICAO
            and (r.sigla_sinal or "").upper() not in siglas_status
            and eh_comando_toggle(r.descricoes.normalizada.split())
        ]
        if not cmds or not siglas_status:
            continue
        if len(siglas_status) == 1:
            (alvo,) = siglas_status
            for c in cmds:
                troca[c.id] = alvo
        else:
            divergentes.update(c.id for c in cmds)

    revisao = [
        ItemRevisao(r, motivo="posicao_divergente")
        for r in registros
        if r.id in divergentes
    ]
    novos = [
        replace(
            r,
            sigla_sinal=troca[r.id],
            justificativa="posicao reconciliada com status do equipamento",
        )
        if r.id in troca
        else r
        for r in registros
        if r.id not in divergentes
    ]
    return novos, revisao
```

Em `parear`, logo após resolver `limiar`/`siglas_write` (linha ~83):

```python
    registros, revisao_reconc = _reconciliar_posicao(registros)
```

E inicializar `revisao: list[ItemRevisao] = list(revisao_reconc)` (em vez de lista vazia).

- [ ] **Step 5: Atualizar docstring de motivo em `contracts.py:149`**

Adicionar `"posicao_divergente"` à enumeração do comentário de `ItemRevisao.motivo`.

- [ ] **Step 6: Rodar testes + suíte + gate**

Run: `python -m pytest -q tests/test_dc_pairer.py && python -m pytest -q tests/`
Expected: PASS.
Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline`.

- [ ] **Step 7: Commit**

```bash
git add src/tdt/dc_pairer.py src/tdt/pareamento_polaridade.py src/tdt/contracts.py tests/test_dc_pairer.py
git commit -m "feat(dc_pairer): reconcilia comando toggle com sigla do status de posicao"
```

---

## Fase 2 — Estruturação: tipo e direção (E3)

### Task 3: E3.1 — `_eh_marcador` tolerante a célula de numeração

Causa (spec §2 item 5): linhas de marcador do CVA11 têm nº de sequência na col 0 (`('1','MEDIÇÃO')`, `('10','CONTROLE')`, `('16','SINALIZAÇÃO')`) → 2 células preenchidas → `_eh_marcador` exige exatamente 1 → marcador nunca reconhecido. Também fecha E6.4 (linha de marcador não vira registro).

**Files:**
- Modify: `src/tdt/normalizacao/estruturador.py:34-39` (`_eh_marcador`)
- Test: `tests/test_estruturador.py`

**Interfaces:**
- Consumes: `vocabulario_tipo.classificar`/`norm` (inalterados nesta task).
- Produces: `_eh_marcador(row, col0) -> bool` (assinatura inalterada, aceita numeração).

- [ ] **Step 1: Testes que falham**

Adicionar em `tests/test_estruturador.py`:

```python
from tdt.normalizacao.estruturador import _eh_marcador


def test_marcador_com_numeracao_na_col0():
    """SP-CVA2 E3.1 — layout CVA11: marcador tem nº de sequência na col 0."""
    assert _eh_marcador(("1", None, None, None, "MEDIÇÃO", None), 0)
    assert _eh_marcador(("10", None, None, None, "CONTROLE", None), 0)
    assert _eh_marcador(("16", None, None, None, "SINALIZAÇÃO", None), 0)


def test_marcador_uma_celula_continua_valendo():
    assert _eh_marcador((None, None, None, None, "CONTROLE", None), 0)


def test_linha_de_dados_nao_e_marcador():
    # linha real CVA11 (descrição + código DI + nome): não é marcador
    assert not _eh_marcador(
        ("17", "CVA11", "PP", "N", "Disj. 52-11 (11Q0) - Sup Circ", "DI"), 0
    )


def test_marcador_de_secao_define_direcao_e_nao_vira_registro():
    """Fim-a-fim no estruturar: seção CONTROLE dá Output às linhas seguintes e
    a linha do marcador não vira SignalRecord (E6.4)."""
    from tdt.config import Config
    from tdt.contracts import MapaColunas
    from tdt.normalizacao.estruturador import estruturar

    rows = [
        ("", "", "", "", "DESCRIÇÃO", "", "", "", "", "INDEX"),      # header (row 1)
        ("10", None, None, None, "CONTROLE", None, None, None, None, None),
        ("11", "CVA11", "PP", "C", "Disjuntor 52-11 - Abrir/Fechar", None, None, None, None, "0"),
        ("16", None, None, None, "SINALIZAÇÃO", None, None, None, None, None),
        ("17", "CVA11", "PP", "N", "Disjuntor 52-11 - Aberto", None, None, None, None, "1"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 4, "indice": 9})
    sinais = estruturar(rows, mapa, sheet_name="CVA11", config=Config())
    por_id = {r.id: r for r in sinais}
    assert "CVA11:2" not in por_id and "CVA11:4" not in por_id  # marcadores
    assert por_id["CVA11:3"].tipo_sinal.direcao == "Output"
    assert por_id["CVA11:3"].tipo_sinal.categoria == "Discrete"
    assert por_id["CVA11:5"].tipo_sinal.direcao == "Input"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_estruturador.py -k marcador`
Expected: FAIL nos 2 primeiros (numeração) e no fim-a-fim (direção Input hoje).

- [ ] **Step 3: Implementar**

Substituir `_eh_marcador` em `estruturador.py:34-39`:

```python
def _eh_marcador(row: tuple, col0: int) -> bool:
    """Linha de marcador de seção: UMA célula classifica como categoria e as
    demais preenchidas são vazias ou numeração de sequência (inteiro curto) —
    o layout CVA11 tem contador na col 0 ('1'/'MEDIÇÃO', '10'/'CONTROLE'),
    que invalidava a regra antiga de "exatamente 1 célula" (SP-CVA2 E3.1)."""
    preenchidas = [i for i, c in enumerate(row) if _norm(c)]
    classificam = [i for i in preenchidas if _classificar(row[i]) is not None]
    if len(classificam) != 1:
        return False
    outras = [i for i in preenchidas if i not in classificam]
    return all(re.fullmatch(r"\d{1,4}", _norm(row[i])) for i in outras)
```

(`re` já é importado no módulo.)

- [ ] **Step 4: Rodar testes + suíte + gate**

Run: `python -m pytest -q tests/test_estruturador.py && python -m pytest -q tests/`
Expected: PASS.
Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline`.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/estruturador.py tests/test_estruturador.py
git commit -m "fix(estruturador): marcador de secao tolera celula de numeracao (CVA11)"
```

### Task 4: E3.2 — códigos AI/AO/DI/DO no vocabulário + `_col_tipo` sem issubset

Achado bônus (spec §2 item 6): BC2 e CVA11 têm coluna de códigos `AI`/`DI`/`DO` (col 5) que `_col_tipo` não reconhece. Evidência por-linha mais forte que marcador (precedência coluna>seção já existe em `estruturador.py:101-104`).

**Files:**
- Modify: `src/tdt/normalizacao/vocabulario_tipo.py:25-30` (`CODIGOS_TIPO`)
- Modify: `src/tdt/analise/analise_colunas.py:228-232` (`_col_tipo`, relaxar issubset)
- Test: `tests/test_vocabulario_tipo.py`, `tests/test_analise_colunas.py`

**Interfaces:**
- Consumes: `CODIGOS_TIPO` (dict código exato → (categoria, direção)).
- Produces: códigos novos `AI/AO/DI/DO`; `_col_tipo` aceita coluna de códigos com ≤10% de ruído (antes: issubset estrito).

- [ ] **Step 1: Testes que falham**

Em `tests/test_vocabulario_tipo.py`:

```python
import pytest
from tdt.normalizacao.vocabulario_tipo import classificar


@pytest.mark.parametrize("codigo,esperado", [
    ("AI", ("Analog", "Input")),
    ("AO", ("Analog", "Output")),
    ("DI", ("Discrete", "Input")),
    ("DO", ("Discrete", "Output")),
    ("di", ("Discrete", "Input")),   # norm() upper
])
def test_codigos_dois_chars_ai_ao_di_do(codigo, esperado):
    """SP-CVA2 E3.2 — listas RGE (BC2/CVA11) usam códigos de 2 letras na
    coluna de tipo. Match por célula EXATA (não substring)."""
    assert classificar(codigo) == esperado


def test_codigo_nao_casa_por_substring():
    assert classificar("DIREITA") != ("Discrete", "Input")
```

Em `tests/test_analise_colunas.py` (seguir o padrão de construção de rows do arquivo; teste direto de `_col_tipo`):

```python
from tdt.analise.analise_colunas import _col_tipo


def test_col_tipo_codigos_dois_chars_com_ruido_tolerado():
    """SP-CVA2 E3.2 — coluna de códigos AI/DI/DO com <=10% de ruído ('-')
    é detectada (antes o issubset estrito zerava com 1 célula fora)."""
    rows = [("DESC", "TIPO")]
    codigos = ["AI", "AI", "DO", "DI", "DI", "DI", "DO", "AI", "DI", "DI",
               "DO", "DI", "AI", "DI", "DI", "DO", "DI", "AI", "DI", "-"]
    rows += [(f"sinal {i}", c) for i, c in enumerate(codigos)]
    assert _col_tipo(rows, 1, 2) == 1


def test_col_tipo_nao_pega_coluna_com_muito_ruido():
    rows = [("DESC", "TIPO")]
    codigos = ["AI", "DI", "N", "N", "N", "N", "N", "N", "N", "N"]
    rows += [(f"sinal {i}", c) for i, c in enumerate(codigos)]
    assert _col_tipo(rows, 1, 2) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_vocabulario_tipo.py tests/test_analise_colunas.py -k "codigo or dois_chars"`
Expected: FAIL (`classificar("AI")` devolve None hoje; `_col_tipo` devolve None p/ coluna com '-').

- [ ] **Step 3: Implementar**

`vocabulario_tipo.py` — estender `CODIGOS_TIPO`:

```python
CODIGOS_TIPO: dict[str, tuple[str, str]] = {
    "A": ("Analog", "Input"),
    "C": ("Discrete", "Output"),
    "D": ("Discrete", "Input"),
    "A/D": ("DiscreteAnalog", "Input"),  # TAP (spec 2026-07-10)
    # Códigos de 2 letras das listas RGE (BC2/CVA11, SP-CVA2 E3.2) — célula
    # exata, nunca substring.
    "AI": ("Analog", "Input"),
    "AO": ("Analog", "Output"),
    "DI": ("Discrete", "Input"),
    "DO": ("Discrete", "Output"),
}
```

`analise_colunas.py` `_col_tipo` — substituir o bloco do `score_codigo` (linhas 228-232):

```python
        distintos = set(normalizados)
        score_codigo = 0.0
        if len(distintos & set(CODIGOS_TIPO)) >= 2:
            casam_codigo = sum(1 for n in normalizados if n in CODIGOS_TIPO)
            score_codigo = casam_codigo / len(vals)
```

(o `score = max(score_palavra, score_codigo if score_codigo >= 0.9 else 0.0)` existente fica como está — o corte de 90% é quem tolera o ruído, o issubset estrito era redundante e zerava com 1 célula '-').

- [ ] **Step 4: Rodar testes + suíte + gate**

Run: `python -m pytest -q tests/test_vocabulario_tipo.py tests/test_analise_colunas.py && python -m pytest -q tests/`
Expected: PASS.
Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline`. (Esta task muda detecção de colunas — se o gate cair, olhar QUAL sheet ganhou coluna de tipo nova antes de decidir.)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/vocabulario_tipo.py src/tdt/analise/analise_colunas.py tests/test_vocabulario_tipo.py tests/test_analise_colunas.py
git commit -m "feat(analise): codigos de tipo AI/AO/DI/DO por celula exata"
```

### Task 5: E3.3 — `_grandeza_continua` por token exato + guarda FALTA/PERDA

Causa (spec §2 item 7): `'Falta de Potencial'` vira Analog por substring `POTENCIA`. Match por token exato + não disparar quando o texto começa com FALTA/PERDA (status de ausência).

**Files:**
- Modify: `src/tdt/normalizacao/estruturador.py:56-58` (`_grandeza_continua`)
- Test: `tests/test_estruturador.py`

**Interfaces:**
- Produces: `_grandeza_continua(bruta) -> tuple[str, str] | None` (assinatura inalterada).

- [ ] **Step 1: Testes que falham**

Em `tests/test_estruturador.py`:

```python
from tdt.normalizacao.estruturador import _grandeza_continua


def test_grandeza_continua_por_token_exato():
    """SP-CVA2 E3.3: 'POTENCIAL' não é 'POTENCIA'; 'SUBTENSAO' não é 'TENSAO'."""
    assert _grandeza_continua("Falta de Potencial") is None
    assert _grandeza_continua("Proteção Subtensão (27) - Excluida") is None
    assert _grandeza_continua("Tensão Barra AB") == ("Analog", "Input")
    assert _grandeza_continua("Potência Reativa") == ("Analog", "Input")
    assert _grandeza_continua("Corrente de Desbalanço (IBX)") == ("Analog", "Input")


def test_grandeza_continua_guarda_falta_perda():
    assert _grandeza_continua("Falta Tensão Comando") is None
    assert _grandeza_continua("Perda de Corrente TC") is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_estruturador.py -k grandeza`
Expected: FAIL — `'Falta de Potencial'` devolve `("Analog","Input")` hoje (substring `POTENCIA`).

- [ ] **Step 3: Implementar**

Substituir em `estruturador.py:53-58`:

```python
_GRANDEZA_CONTINUA = ("TENSAO", "CORRENTE", "POTENCIA", "FREQUENCIA")
# Texto que COMEÇA com falta/perda descreve ausência (status discreto), não
# medição — 'Falta de Potencial', 'Falta Tensão Comando' (SP-CVA2 E3.3).
_PREFIXOS_AUSENCIA = ("FALTA", "PERDA")


def _grandeza_continua(bruta) -> tuple[str, str] | None:
    tokens = _norm(bruta).split()
    if not tokens or tokens[0] in _PREFIXOS_AUSENCIA:
        return None
    if any(t in _GRANDEZA_CONTINUA for t in tokens):
        return ("Analog", "Input")
    return None
```

- [ ] **Step 4: Rodar testes + suíte + gate**

Run: `python -m pytest -q tests/test_estruturador.py && python -m pytest -q tests/`
Expected: PASS.
Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline`.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/estruturador.py tests/test_estruturador.py
git commit -m "fix(estruturador): grandeza continua por token exato + guarda FALTA/PERDA"
```

---

## Fase 3 — Fusão do par de posição antes do dc_pairer (E4)

### Task 6: `fundir_pares_posicao` + wiring nos 2 call sites

Hoje o double-bit funde só em `normalizador_estrutural.corrigir`, que roda DEPOIS do `dc_pairer` — o grupo DJF1 chega ao pairer como 2 inputs + 1 output e cai no catch-all. Fundir o par ANTES: 1 input MultiCoord × 1 output → ReadWrite limpo. Resolve de brinde os itens 1 e 13 de `observações_pendentes.txt`.

**Files:**
- Modify: `src/tdt/normalizador_estrutural.py` (nova função pública `fundir_pares_posicao`)
- Modify: `src/tdt/pipeline.py:530-531` (`gerar_tdt`) e `:715-717` (`executar`)
- Modify: `tests/test_conservacao_comandos.py` (composição espelha o pipeline)
- Test: `tests/test_normalizador_estrutural.py`

**Interfaces:**
- Consumes: `_chave`, `_par_posicao_oposta`, `_fundir_multicoord` (privados existentes do próprio módulo); `pipeline._whitelist_posicao(lp, config)`.
- Produces: `fundir_pares_posicao(registros: list[SignalRecord], whitelist_posicao: frozenset[str]) -> list[SignalRecord]` — puro, sem revisão (quem descarta/roteia continua sendo `corrigir`).

- [ ] **Step 1: Testes que falham**

Em `tests/test_normalizador_estrutural.py` (usar o helper de construção de registro local do arquivo se existir; senão este):

```python
from tdt.config import Config
from tdt import dc_pairer
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.normalizador_estrutural import fundir_pares_posicao


def _rec_fp(rid, sigla, direcao, indices, desc, modulo="BC2"):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_fundir_pares_posicao_forma_multicoord():
    """SP-CVA2 E4: par ABERTO/FECHADO (mesma sigla de posição, endereços
    consecutivos) vira UM MultiCoord ANTES do dc_pairer."""
    aberto = _rec_fp("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    fechado = _rec_fp("BC2:22", "DJF1", "Input", [321], "52 06 FECHADO")
    comando = _rec_fp("BC2:14", "DJF1", "Output", [90], "52 06 ABRIR FECHAR")
    saida = fundir_pares_posicao([aberto, fechado, comando], frozenset({"DJF1"}))
    inputs = [r for r in saida if r.tipo_sinal.direcao == "Input"]
    assert len(inputs) == 1
    assert inputs[0].enderecamento.indices == (320, 321)
    assert inputs[0].tipo_sinal.datatype == "MultiCoord"
    assert len(saida) == 2  # MultiCoord + comando


def test_fundir_pares_posicao_readwrite_completo_no_pairer():
    """Encadeado com dc_pairer: 1 MultiCoord x 1 comando -> InputOutput com
    INCOORDS do par e OUTCOORDS do comando (antes: catch-all N x M)."""
    aberto = _rec_fp("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    fechado = _rec_fp("BC2:22", "DJF1", "Input", [321], "52 06 FECHADO")
    comando = _rec_fp("BC2:14", "DJF1", "Output", [90], "52 06 ABRIR FECHAR")
    fundidos = fundir_pares_posicao([aberto, fechado, comando], frozenset({"DJF1"}))
    pareados, rev = dc_pairer.parear(fundidos, Config())
    rw = [r for r in pareados if r.tipo_sinal.direcao == "InputOutput"]
    assert len(rw) == 1
    assert rw[0].enderecamento.indices == (320, 321)
    assert rw[0].enderecamento.indices_saida == (90,)
    assert not rev


def test_fundir_pares_posicao_ignora_fora_da_whitelist_e_nao_consecutivos():
    a = _rec_fp("Z:1", "MOLA", "Input", [10], "MOLA CARREGADA")
    b = _rec_fp("Z:2", "MOLA", "Input", [11], "MOLA DESCARREGADA")
    c = _rec_fp("Z:3", "DJF1", "Input", [20], "52 06 ABERTO")
    d = _rec_fp("Z:4", "DJF1", "Input", [22], "52 06 FECHADO")  # gap: 20->22
    saida = fundir_pares_posicao([a, b, c, d], frozenset({"DJF1"}))
    assert len(saida) == 4  # nada fundido
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_normalizador_estrutural.py -k fundir_pares`
Expected: FAIL — `ImportError: cannot import name 'fundir_pares_posicao'`.

- [ ] **Step 3: Implementar em `normalizador_estrutural.py`** (após `_fundir_multicoord`)

```python
def fundir_pares_posicao(
    registros: list[SignalRecord],
    whitelist_posicao: frozenset[str],
) -> list[SignalRecord]:
    """Funde pares de POSIÇÃO (2 Inputs de 1 índice, sigla na whitelist
    SwitchStatus, polaridade oposta, endereços consecutivos) num único
    MultiCoord ANTES do dc_pairer — o comando pareia com o par inteiro
    (1 input x 1 output) em vez de cair no catch-all N x M (SP-CVA2 E4).
    Mesmo predicado `fundivel` de `corrigir`; puro, não emite revisão."""
    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    saida: list[SignalRecord] = []
    for rec in registros:
        if (
            rec.tipo_sinal.direcao == "Input"
            and len(rec.enderecamento.indices) == 1
            and (rec.sigla_sinal or "").upper() in whitelist_posicao
        ):
            grupos[_chave(rec)].append(rec)
        else:
            saida.append(rec)
    for grupo in grupos.values():
        ordenados = sorted(grupo, key=lambda r: r.enderecamento.indices[0])
        i = 0
        while i < len(ordenados):
            a = ordenados[i]
            b = ordenados[i + 1] if i + 1 < len(ordenados) else None
            if (
                b is not None
                and b.enderecamento.indices[0] == a.enderecamento.indices[0] + 1
                and _par_posicao_oposta(a, b)
            ):
                saida.append(_fundir_multicoord(a, b))
                i += 2
            else:
                saida.append(a)
                i += 1
    return saida
```

- [ ] **Step 4: Wiring no pipeline**

`pipeline.py` — import (junto do `corrigir` existente):

```python
from tdt.normalizador_estrutural import corrigir, fundir_pares_posicao
```

`gerar_tdt` (linhas 529-531) vira:

```python
    lst = _aplicar_aliases(list(registros), aliases)
    wl_pos = _whitelist_posicao(lp, config)
    lst = fundir_pares_posicao(lst, wl_pos)
    pareados, _rev = dc_pairer.parear(lst, config)
    corrigidos, _rev2 = corrigir(list(pareados), wl_pos)
```

`executar` (linhas 715-717) vira:

```python
    with _timer("dc_pairer + corrigir + montar + tdt", aud):
        wl_pos = _whitelist_posicao(lp, config)
        decididos = fundir_pares_posicao(decididos, wl_pos)
        pareados, rev_pair = dc_pairer.parear(decididos, config)
        corrigidos, rev_estrut = corrigir(list(pareados), wl_pos)
```

- [ ] **Step 5: Espelhar a composição em `tests/test_conservacao_comandos.py`**

No teste existente `test_nenhum_comando_some_silenciosamente`, atualizar a cadeia (e o comentário de composição do docstring do módulo) para:

```python
    fundidos = fundir_pares_posicao(entrada, frozenset())
    pareados, rev1 = dc_pairer.parear(fundidos, Config())
```

com o import `from tdt.normalizador_estrutural import corrigir, fundir_pares_posicao`.

- [ ] **Step 6: Rodar testes + suíte + gate**

Run: `python -m pytest -q tests/test_normalizador_estrutural.py tests/test_conservacao_comandos.py tests/test_pipeline_gerar_tdt.py && python -m pytest -q tests/`
Expected: PASS.
Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline`. (Mudança de ordem no pipeline — se cair, parar e reportar com o diff de casos do gate.)

- [ ] **Step 7: Commit**

```bash
git add src/tdt/normalizador_estrutural.py src/tdt/pipeline.py tests/test_normalizador_estrutural.py tests/test_conservacao_comandos.py
git commit -m "feat(pipeline): funde par de posicao em MultiCoord antes do dc_pairer"
```

---

## Fase 4 — Módulo por linha (E5)

### Task 7: E5.1 — sanitização do módulo por linha (dominante da sheet)

Achado (spec §2 item 4): células com 2 prefixos conhecidos (`BC1_CORRENTE_IB` → {BC, IB}) ou lixo (`(LógicainternadeIntertravamento!)`) passam crus como nome de módulo com confiança alta.

**Files:**
- Modify: `src/tdt/identidade_modulo.py` (`ResolucaoModulo.canonico`, `canonizar_modulo`, `_identidade_por_linha`, `aplicar_identidade` → 3-tupla)
- Modify: `src/tdt/pipeline.py:610` (desempacotar 3-tupla + logar avisos)
- Modify: `tests/test_identidade_modulo.py` (call sites existentes de `aplicar_identidade` — linhas ~185/194/275/283+, desempacotar 3 valores)
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `canonizar_modulo(valor, config, explicito=True)` (existente).
- Produces: `ResolucaoModulo` ganha `canonico: bool = False` (True só nas estratégias 1/2); `aplicar_identidade(...) -> tuple[list[SignalRecord], str, list[str]]` (3º item: avisos legíveis p/ auditoria).

- [ ] **Step 1: Testes que falham**

Em `tests/test_identidade_modulo.py`:

```python
def test_canonizar_modulo_marca_canonico():
    cfg = Config()
    assert canonizar_modulo("BC1_DJ_ABERTO", cfg, explicito=True).canonico
    # dois prefixos conhecidos (BC + IB) -> ambíguo -> fallback cru, não-canônico
    res = canonizar_modulo("BC1_CORRENTE_IB", cfg, explicito=True)
    assert not res.canonico and res.nome == "BC1_CORRENTE_IB"


def test_identidade_por_linha_sanea_lixo_pro_modulo_dominante():
    """SP-CVA2 E5.1 — célula fora do padrão herda o módulo dominante da sheet
    (com aviso) em vez de virar nome de módulo lixo."""
    sinais = [
        _sinal_coluna("BC2:5", "BC1_VAB"),
        _sinal_coluna("BC2:9", "BC1_CORRENTE_IB"),
        _sinal_coluna("BC2:21", "BC1_DJ_ABERTO"),
        _sinal_coluna("BC2:26", "(LogicaInterna!)"),
    ]
    novos, conf, avisos = aplicar_identidade(sinais, "BC2", [], Config())
    assert {s.modulo.nome for s in novos} == {"BC1"}
    assert len(avisos) == 2  # BC2:9 e BC2:26
    assert any("BC2:9" in a for a in avisos)
```

Com o helper (adicionar junto dos helpers existentes do arquivo, mesmo estilo):

```python
def _sinal_coluna(rid, nome_mod):
    return SignalRecord(
        id=rid,
        modulo=Modulo(nome_mod, "coluna:MODULO_POR_LINHA"),
        tipo_sinal=TipoSinal("Discrete"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("x", "X"),
    )
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_identidade_modulo.py -k "canonico or sanea"`
Expected: FAIL — `ResolucaoModulo` não tem `canonico`; `aplicar_identidade` devolve 2-tupla.

- [ ] **Step 3: Implementar em `identidade_modulo.py`**

`ResolucaoModulo` ganha o campo:

```python
@dataclass(frozen=True)
class ResolucaoModulo:
    nome: str
    confianca: str  # "alta" | "baixa"
    por_linha: dict[int, str] | None = None  # slot (follow-up); None aqui
    canonico: bool = False  # True só quando saiu das estratégias 1/2 (SP-CVA2 E5.1)
```

`canonizar_modulo`: os dois `return` das estratégias 1 e 2 ganham `canonico=True`; os fallbacks ficam `canonico=False` (default).

`_identidade_por_linha` vira (substitui a função inteira):

```python
def _identidade_por_linha(
    sinais: list[SignalRecord], config: Config
) -> tuple[list[SignalRecord], list[str]]:
    """Gênero módulo-por-coluna: canoniza cada nome (explícito), SANEIA os que
    não canonizam pro módulo dominante da sheet (SP-CVA2 E5.1 — evita módulo
    lixo tipo 'BC1_CORRENTE_IB') e classifica o tipo POR GRUPO de módulo."""
    resolvidos: list[tuple[SignalRecord, ResolucaoModulo | None]] = []
    for s in sinais:
        if s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" and s.modulo.nome:
            resolvidos.append((s, canonizar_modulo(s.modulo.nome, config, explicito=True)))
        else:
            resolvidos.append((s, None))

    canonicos = [r.nome for _, r in resolvidos if r is not None and r.canonico and r.nome]
    dominante = max(set(canonicos), key=canonicos.count) if canonicos else None

    avisos: list[str] = []
    canon: list[SignalRecord] = []
    for s, res in resolvidos:
        if res is None:
            canon.append(s)
            continue
        nome = res.nome
        if not res.canonico and dominante is not None:
            avisos.append(
                f"{s.id}: módulo {s.modulo.nome!r} fora do padrão — saneado para {dominante!r}"
            )
            nome = dominante
        s = replace(s, modulo=replace(s.modulo, nome=nome))
        if not nome:
            s = replace(s, status="revisao", justificativa="modulo_indefinido")
        canon.append(s)

    grupos: dict[str, list[SignalRecord]] = {}
    for s in canon:
        grupos.setdefault(s.modulo.nome or "", []).append(s)
    tipo_de = {nome: classificar_tipo(nome, regs, config) for nome, regs in grupos.items()}
    return [
        replace(s, modulo=replace(s.modulo, tipo=tipo_de[s.modulo.nome or ""]))
        for s in canon
    ], avisos
```

`aplicar_identidade` passa a devolver 3-tupla:

```python
def aplicar_identidade(
    sinais: list[SignalRecord], sheet_name: str, rows: list[tuple], config: Config
) -> tuple[list[SignalRecord], str, list[str]]:
    if any(s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" for s in sinais):
        novos, avisos = _identidade_por_linha(sinais, config)
        return novos, "alta", avisos
    ...  # caminho de sheet inalterado, retornar (com_tipo, <confianca>, [])
```

- [ ] **Step 4: Atualizar call sites**

Run: `grep -rn "aplicar_identidade" src tests bench` — atualizar TODOS:
- `src/tdt/pipeline.py:610`:

```python
        sinais, conf_mod, avisos_mod = aplicar_identidade(sinais, sn, rows, config)
        for msg in avisos_mod:
            aud.evento("identidade_modulo", msg, "AVISO")
```

- `tests/test_identidade_modulo.py` (linhas ~185, ~194, ~275, ~283 e demais): desempacotar `novos, conf, _ = ...` (ou `novos, _, _`).
- `bench/diag_cva.py`: o monkeypatch de captura repassa o retorno cru — nenhuma mudança.

- [ ] **Step 5: Rodar testes + suíte + gate**

Run: `python -m pytest -q tests/test_identidade_modulo.py tests/test_pipeline.py && python -m pytest -q tests/`
Expected: PASS.
Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline`.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/identidade_modulo.py src/tdt/pipeline.py tests/test_identidade_modulo.py
git commit -m "feat(identidade): sanea modulo por linha fora do padrao (dominante da sheet)"
```

### Task 8: E5.2 — aviso de divergência sheet × conteúdo (BC2 rotulada BC1)

**Files:**
- Modify: `src/tdt/identidade_modulo.py` (novo helper puro `aviso_divergencia_sheet`)
- Modify: `src/tdt/pipeline.py` (wiring após `aplicar_identidade`)
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `canonizar_modulo` (com `canonico`, Task 7); `aplicar_identidade` 3-tupla (Task 7).
- Produces: `aviso_divergencia_sheet(sheet_name: str, sinais: list[SignalRecord], config: Config) -> str | None`.

- [ ] **Step 1: Testes que falham**

```python
def test_aviso_divergencia_sheet_bc2_rotulada_bc1():
    """SP-CVA2 E5.2 — sheet BC2 com conteúdo (módulo por linha) dominante BC1:
    aviso explícito; o sistema NÃO corrige (dado do cliente)."""
    sinais, _, _ = aplicar_identidade(
        [_sinal_coluna(f"BC2:{i}", "BC1_VAB") for i in range(4)], "BC2", [], Config()
    )
    aviso = aviso_divergencia_sheet("BC2", sinais, Config())
    assert aviso is not None and "BC1" in aviso and "BC2" in aviso


def test_aviso_divergencia_none_quando_coerente_ou_sem_evidencia():
    cfg = Config()
    sinais, _, _ = aplicar_identidade(
        [_sinal_coluna(f"BC1:{i}", "BC1_VAB") for i in range(4)], "BC1", [], cfg
    )
    assert aviso_divergencia_sheet("BC1", sinais, cfg) is None  # coerente
    assert aviso_divergencia_sheet("BC2", [], cfg) is None      # sem módulo por coluna
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_identidade_modulo.py -k divergencia`
Expected: FAIL — `ImportError` (função não existe).

- [ ] **Step 3: Implementar em `identidade_modulo.py`**

```python
def aviso_divergencia_sheet(
    sheet_name: str, sinais: list[SignalRecord], config: Config
) -> str | None:
    """Aviso quando o módulo dominante do CONTEÚDO (coluna por linha) diverge
    do nome canônico da sheet — caso real BC2 rotulada BC1 na origem
    (SP-CVA2 E5.2). Não corrige: o operador decide (renomear em lote)."""
    res_sheet = canonizar_modulo(sheet_name, config)
    if not res_sheet.canonico:
        return None
    nomes = [
        s.modulo.nome for s in sinais
        if s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" and s.modulo.nome
    ]
    if not nomes:
        return None
    dominante = max(set(nomes), key=nomes.count)
    if dominante == res_sheet.nome or nomes.count(dominante) / len(nomes) < 0.5:
        return None
    return (
        f"Sheet {sheet_name}: conteúdo rotulado {dominante!r} diverge do nome da "
        f"sheet ({res_sheet.nome!r}) — verificar módulo na planilha de origem"
    )
```

- [ ] **Step 4: Wiring em `pipeline.py`** (logo após o bloco de avisos da Task 7)

Import: adicionar `aviso_divergencia_sheet` ao import de `tdt.identidade_modulo` (linha 39).

```python
        aviso_div = aviso_divergencia_sheet(sn, sinais, config)
        if aviso_div:
            aud.evento("identidade_modulo", aviso_div, "AVISO")
```

- [ ] **Step 5: Rodar testes + suíte + gate; commit**

Run: `python -m pytest -q tests/test_identidade_modulo.py && python -m pytest -q tests/`
Run: `PYTHONPATH=src python -m bench.regressao` → `pct >= baseline` (só logging, não deve mexer).

```bash
git add src/tdt/identidade_modulo.py src/tdt/pipeline.py tests/test_identidade_modulo.py
git commit -m "feat(identidade): aviso quando conteudo da sheet diverge do nome (BC2/BC1)"
```

---

## Fase 5 — Invariantes e boundary (E6.1, E6.2)

### Task 9: E6.1 — invariante de conservação TOTAL

**Files:**
- Modify: `tests/test_conservacao_comandos.py` (novo teste + helper; docstring do módulo)

**Interfaces:**
- Consumes: `fundir_pares_posicao` (Task 6), cadeia `parear → corrigir → montar → particionar_custom_id_duplicado`.
- Produces: só teste (trava de regressão).

- [ ] **Step 1: Escrever o teste**

Adicionar em `tests/test_conservacao_comandos.py`:

```python
def _sinais_absorvidos(entrada, *grupos_finais):
    """Inputs cujo endereço foi absorvido por um MultiCoord fundido
    (fundir_pares_posicao) — rastreados por (modulo, sigla, endereço ∈ indices),
    análogo ao rastreio de comandos por indices_saida."""
    presentes = [
        (rec.modulo.nome, rec.sigla_sinal, set(rec.enderecamento.indices))
        for grupo in grupos_finais
        for rec in grupo
    ]
    absorvidos = set()
    for r in entrada:
        if r.tipo_sinal.direcao != "Input" or not r.enderecamento.indices:
            continue
        alvo = r.enderecamento.indices[0]
        for mod, sig, idxs in presentes:
            if mod == r.modulo.nome and sig == r.sigla_sinal and alvo in idxs:
                absorvidos.add(r.id)
                break
    return absorvidos


def test_nenhum_sinal_some_silenciosamente():
    """SP-CVA2 E6.1: conservação TOTAL — todo sinal da entrada (qualquer
    direção) termina no TDT final OU na revisão. Requisito do usuário
    (anot.txt 14jul): 'mesmo com módulo errado, deve ter todos os sinais
    para que a revisão possa ser feita'."""
    entrada = [
        # par de posição fundível (E4) + comando toggle do mesmo grupo
        _rec("BC2:21", "DJF1", "Input", "BC2", [320], "52 06 ABERTO"),
        _rec("BC2:22", "DJF1", "Input", "BC2", [321], "52 06 FECHADO"),
        _rec("BC2:14", "DJF1", "Output", "BC2", [90], "52 06 ABRIR FECHAR"),
        # input comum
        _rec("BC2:32", "MOLA", "Input", "BC2", [326], "MOLA DESCARREGADA"),
        # comando órfão -> revisão comando_sem_discreto
        _rec("BC9:1", "DJF1", "Output", "BC9", [200], "DISJ DESLIGAR LIGAR"),
        # sem endereço -> revisão sem_endereco (corrigir)
        _rec("BC2:52", "COM1", "Input", "BC2", [], "SAUDE COMUNICACAO"),
        # duplicata de endereço no mesmo grupo -> revisão endereco_duplicado
        _rec("BC3:5", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
        _rec("BC3:6", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
    ]
    ids_entrada = {r.id for r in entrada}

    fundidos = fundir_pares_posicao(entrada, frozenset({"DJF1"}))
    pareados, rev1 = dc_pairer.parear(fundidos, Config())
    corrigidos, rev2 = corrigir(list(pareados), frozenset({"DJF1"}))
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao="SE1")
    lista, rev3 = engine_tdt.particionar_custom_id_duplicado(lista)

    registros_revisao = [ir.registro for ir in (*rev1, *rev2, *rev3)]
    ids_diretos = {r.id for r in lista.registros} | {r.id for r in registros_revisao}
    ids_fundidos = _comandos_fundidos(entrada, lista.registros, registros_revisao)
    ids_absorvidos = _sinais_absorvidos(entrada, lista.registros, registros_revisao)

    sobreviventes = ids_diretos | ids_fundidos | ids_absorvidos
    assert ids_entrada <= sobreviventes, f"sumiram: {ids_entrada - sobreviventes}"
```

Atualizar o docstring do módulo: "todo sinal de comando" → "todo sinal (comando E status/analógico)".

- [ ] **Step 2: Rodar**

Run: `python -m pytest -q tests/test_conservacao_comandos.py -v`
Expected: PASS (é trava — se falhar, achou bug real; parar e reportar).

- [ ] **Step 3: Commit**

```bash
git add tests/test_conservacao_comandos.py
git commit -m "test(conservacao): invariante total - nenhum sinal some do TDT+revisao"
```

### Task 10: E6.2 — gate `endereco_duplicado` por módulo

**Correção pós-execução (14jul, achado pelo decision gate do Step 4 original — ver `.superpowers/sdd/task-10-report.md`):** a 1ª versão desta task chaveava só por `(categoria, in/out, índice)`, workbook-wide. Rodado contra o dado real da SE CVA deu 0 colisões (autorizava ligar o wiring), mas ligar o wiring quebrou 2 testes existentes (`test_pipeline_aplica_aliases_ao_nome_do_modulo`, `test_san2_cobertura_por_sheet_bate_com_a_lista_padrao`): módulos DISTINTOS (linhas de transmissão/IEDs diferentes) legitimamente reusam o mesmo índice local — é o mesmo motivo pelo qual `_chave` em `dc_pairer.py`/`normalizador_estrutural.py` e o Custom ID em `particionar_custom_id_duplicado` SEMPRE incluem `módulo` (e `_remote_unit` é constante por SUBESTAÇÃO inteira, não por módulo — não serve pra desambiguar). A correção: escopar a chave por módulo também, consistente com o resto do codebase. Isso ainda cobre o caso CVA11 (a colisão daquela hipótese é DENTRO do mesmo módulo/sheet).

Detector genérico do sintoma da hipótese do usuário (CVA11): direção errada → dois pontos no mesmo módulo, no mesmo espaço de endereçamento, com o mesmo índice. Medir no dado real ANTES de ligar.

**Files:**
- Modify: `src/tdt/engine_tdt.py` (nova `particionar_endereco_duplicado`, ao lado de `particionar_custom_id_duplicado`)
- Modify: `src/tdt/pipeline.py` (wiring nos 2 call sites, após `particionar_custom_id_duplicado`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `ListaHomogenea`, `ItemRevisao` (motivo REUSADO: `"endereco_duplicado"` — já tem label/tooltip na UI).
- Produces: `particionar_endereco_duplicado(lista: ListaHomogenea) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]`. Espaço de endereçamento: `(módulo, categoria, "in"|"out", índice)` — Input/InputOutput usam `indices` no espaço "in"; Output usa `indices` no "out"; `indices_saida` sempre "out". Módulo faz parte da chave: índice local reusado entre módulos distintos NÃO é colisão.

- [ ] **Step 1: Testes que falham**

Em `tests/test_engine_tdt.py` — adicionar helper autocontido (se o arquivo já tiver um construtor equivalente com nome `_rec`, usar `_rec_end` pra não colidir):

```python
from dataclasses import replace

from tdt import criador_lista_homogenea, engine_tdt
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal


def _rec_end(rid, sigla, direcao, modulo, indices, desc):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_particionar_endereco_duplicado_mesmo_modulo_colide():
    """SP-CVA2 E6.2: dois Inputs Discrete do MESMO módulo com o mesmo índice
    -> grupo inteiro pra revisão (sintoma de direção errada na origem)."""
    a = _rec_end("S1:1", "27", "Input", "M1", [10], "PROT 27 ATUADO")
    b = _rec_end("S1:2", "50BF", "Input", "M1", [10], "ATUADO 50 BF")
    lista = criador_lista_homogenea.montar([a, b], subestacao="SE1")
    lista2, rev = engine_tdt.particionar_endereco_duplicado(lista)
    assert len(lista2.registros) == 0
    assert sorted(it.registro.id for it in rev) == ["S1:1", "S1:2"]
    assert {it.motivo for it in rev} == {"endereco_duplicado"}


def test_particionar_endereco_duplicado_modulos_distintos_nao_colidem():
    """Achado do decision gate (14jul): índice local reusado entre módulos
    (IEDs/linhas) DISTINTOS é endereçamento normal, não colisão — mesmo
    padrão de `_chave` em dc_pairer/normalizador_estrutural."""
    a = _rec_end("S1:1", "FCOM", "Input", "M1", [10], "FALHA COMUNICACAO")
    b = _rec_end("S2:1", "FCOM", "Input", "M2", [10], "FALHA COMUNICACAO")
    lista = criador_lista_homogenea.montar([a, b], subestacao="SE1")
    lista2, rev = engine_tdt.particionar_endereco_duplicado(lista)
    assert not rev and len(lista2.registros) == 2


def test_particionar_endereco_duplicado_espacos_distintos_nao_colidem():
    """Analog@0 e Discrete@0 são espaços distintos; Input@5 e Output@5 idem
    (mesmo módulo em todos os casos)."""
    recs = [
        _rec_end("S1:1", "VAB", "Input", "M1", [0], "TENSAO BARRA AB"),
        _rec_end("S1:2", "27", "Input", "M1", [0], "PROT 27 ATUADO"),
        _rec_end("S1:3", "DJF1", "Output", "M1", [5], "DISJ ABRIR FECHAR"),
        _rec_end("S1:4", "MOLA", "Input", "M1", [5], "MOLA DESCARREGADA"),
    ]
    # VAB precisa ser Analog: ajustar helper/replace da categoria
    recs[0] = replace(recs[0], tipo_sinal=replace(recs[0].tipo_sinal, categoria="Analog"))
    lista = criador_lista_homogenea.montar(recs, subestacao="SE1")
    lista2, rev = engine_tdt.particionar_endereco_duplicado(lista)
    assert not rev and len(lista2.registros) == 4


def test_particionar_endereco_duplicado_indices_saida_no_espaco_out():
    fundido = _rec_end("S1:1", "DJF1", "InputOutput", "M1", [10], "DISJ ABERTO")
    fundido = replace(
        fundido, enderecamento=replace(fundido.enderecamento, indices_saida=(90,))
    )
    outro_cmd = _rec_end("S1:2", "SECC", "Output", "M1", [90], "SEC CARGA ABRIR FECHAR")
    lista = criador_lista_homogenea.montar([fundido, outro_cmd], subestacao="SE1")
    lista2, rev = engine_tdt.particionar_endereco_duplicado(lista)
    assert sorted(it.registro.id for it in rev) == ["S1:1", "S1:2"]
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_engine_tdt.py -k endereco_duplicado`
Expected: FAIL — função não existe.

- [ ] **Step 3: Implementar em `engine_tdt.py`** (após `particionar_custom_id_duplicado`)

```python
def particionar_endereco_duplicado(
    lista: ListaHomogenea,
) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]:
    """Gate por módulo (SP-CVA2 E6.2): dois pontos do MESMO módulo, no MESMO
    espaço de endereçamento (categoria, in/out), com o mesmo índice, saem
    TODOS da lista e vão pra revisão. Sintoma típico: direção errada na
    origem (comando lido como Input colide com o Input real de mesmo índice
    — hipótese CVA11). Módulo entra na chave: índice local reusado entre
    módulos DISTINTOS (IEDs/linhas diferentes) é endereçamento normal, não
    colisão (achado do decision gate original, ver nota no topo da task) —
    mesmo racional de `_chave` em dc_pairer/normalizador_estrutural e do
    Custom ID em `particionar_custom_id_duplicado` (`_remote_unit` é
    constante por SUBESTAÇÃO, não desambigua módulo). MultiCoord/DoubleBit
    contribuem cada índice individualmente."""
    grupos: dict[tuple, dict[str, SignalRecord]] = defaultdict(dict)
    for rec in lista.registros:
        mod = rec.modulo.nome
        cat = rec.tipo_sinal.categoria
        espaco_in = "out" if rec.tipo_sinal.direcao == "Output" else "in"
        for idx in rec.enderecamento.indices:
            grupos[(mod, cat, espaco_in, idx)][rec.id] = rec
        for idx in rec.enderecamento.indices_saida:
            grupos[(mod, cat, "out", idx)][rec.id] = rec

    colididos: dict[str, SignalRecord] = {}
    for regs in grupos.values():
        if len(regs) > 1:
            colididos.update(regs)
    if not colididos:
        return lista, ()
    restantes = tuple(r for r in lista.registros if r.id not in colididos)
    revisao = tuple(
        ItemRevisao(r, motivo="endereco_duplicado") for r in colididos.values()
    )
    return replace(lista, registros=restantes), revisao
```

(Conferir se `engine_tdt.py` já importa `replace` e `defaultdict`; senão adicionar.)

- [ ] **Step 4: MEDIR no dado real antes de ligar (decision gate)**

Rodar no repo (não commitar o snippet):

```bash
PYTHONPATH=src python - <<'EOF'
import warnings; warnings.simplefilter("ignore")
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar
from tdt import engine_tdt
cfg = Config()
res, _ = executar(
    r"C:\Users\vinic\Documents\docs importantes\RGE\CVA\CVA - Pontos Por Equipamentos DNP_V03 - COS - resumida.xlsx",
    "docs/dnp3_template.xlsx", "docs/Pontos Padrao ADMS_v8.xlsx",
    config=cfg, encoder=criar_encoder(cfg.modelo_embedding), subestacao="CVA",
)
lista2, rev = engine_tdt.particionar_endereco_duplicado(res.lista)
print(f"colisoes reais: {len(rev)}")
for it in rev:
    print(" ", it.registro.id, it.registro.sigla_sinal, it.registro.enderecamento)
EOF
```

Expected: `colisoes reais: 0` (pós Tasks 3-5 a direção do CVA11 está certa). **Se > 0 com casos LEGÍTIMOS (não erro de direção/origem): PARAR e reportar ao usuário antes de ligar o wiring** — o keying pode precisar de refinamento (ex. incluir remote unit).

- [ ] **Step 5: Wiring nos 2 call sites de `pipeline.py`** (após `particionar_custom_id_duplicado`)

Em `executar`:

```python
        lista, rev_end = engine_tdt.particionar_endereco_duplicado(lista)
        if rev_end:
            aud.evento("engine", f"{len(rev_end)} registros com endereço duplicado -> revisão", "AVISO")
            revisao.extend(rev_end)
```

Em `gerar_tdt` (espelho, com `aud.evento` análogo ao bloco `rev_dup` existente):

```python
    lista, rev_end = engine_tdt.particionar_endereco_duplicado(lista)
    if rev_end:
        aud.evento("engine", f"{len(rev_end)} registros com endereço duplicado -> revisão", "AVISO",
                   dados={"ids": tuple(it.registro.id for it in rev_end)})
```

- [ ] **Step 6: Rodar testes + suíte + gate**

Run: `python -m pytest -q tests/test_engine_tdt.py tests/test_pipeline_gerar_tdt.py tests/test_pipeline.py tests/test_integracao_san2.py && python -m pytest -q tests/`
Expected: PASS — em particular `test_pipeline_aplica_aliases_ao_nome_do_modulo` e `test_san2_cobertura_por_sheet_bate_com_a_lista_padrao` (os 2 casos que quebraram na 1ª tentativa, chave sem módulo) devem passar agora.
Run: `PYTHONPATH=src python -m bench.regressao`
Expected: `pct >= baseline` E nenhum registro novo removido do TDT do gate (se o gate cair, é colisão legítima DENTRO do mesmo módulo no fixture — voltar ao Step 4/decision gate, não afrouxar a chave de novo).

- [ ] **Step 7: Commit**

```bash
git add src/tdt/engine_tdt.py src/tdt/pipeline.py tests/test_engine_tdt.py
git commit -m "feat(engine): gate de endereco duplicado por modulo"
```

---

## Fase 6 — UI (E6.3)

### Task 11: coluna Pareado "Comando (sem par)" + label/tooltip `posicao_divergente`

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py:23-67` (`_MOTIVO_LABEL`, `_MOTIVO_TOOLTIP`) e `:223-229` (Pareado)
- Test: `tests/test_ui_modelo_tabela.py`

**Interfaces:**
- Consumes: motivo `posicao_divergente` (Task 2); padrão de teste existente do arquivo (`_rec`/`_state`/`_col`).
- Produces: Pareado → "Comando (sem par)" para Output COM endereço; "Órfão" continua só para Output SEM endereço.

- [ ] **Step 1: Testes que falham**

Em `tests/test_ui_modelo_tabela.py`:

```python
# (o arquivo já importa Enderecamento e TipoSinal de tdt.contracts, e replace)


def test_pareado_comando_sem_par_e_endereco_visiveis(qtbot):
    """SP-CVA2 E6.3 (fato 3 do anot.txt): comando sem par precisa ser
    LOCALIZÁVEL na revisão — rótulo próprio + endereço na coluna Endereço."""
    rec = replace(
        _rec(status="revisao", sigla="DJA1"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Output"),
        enderecamento=Enderecamento("DNP3", (90,)),
    )
    m = ModeloSinais(_state(rec))
    assert m.data(m.index(0, _col("Pareado"))) == "Comando (sem par)"
    assert m.data(m.index(0, _col("Endereço"))) == "90"


def test_pareado_orfao_continua_para_output_sem_endereco(qtbot):
    rec = replace(
        _rec(),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Output"),
        enderecamento=Enderecamento("DNP3", ()),
    )
    m = ModeloSinais(_state(rec))
    assert m.data(m.index(0, _col("Pareado"))) == "Órfão"


def test_motivo_posicao_divergente_tem_label_e_tooltip(qtbot):
    from tdt.ui.modelo_tabela import _MOTIVO_TOOLTIP
    assert _MOTIVO_LABEL["posicao_divergente"] == "Posição diverge do status"
    assert "status" in _MOTIVO_TOOLTIP["posicao_divergente"].lower()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_ui_modelo_tabela.py -k "pareado or divergente"`
Expected: FAIL — Pareado devolve "—" p/ Output com endereço; label ausente.

- [ ] **Step 3: Implementar**

Bloco Pareado em `modelo_tabela.py:223-229`:

```python
        if nome == "Pareado":
            direcao = rec.tipo_sinal.direcao
            if direcao == "InputOutput":
                return "Sim"
            if direcao == "Output":
                # comando ainda sem par: rótulo próprio p/ o operador ACHAR o
                # comando na revisão (SP-CVA2 E6.3 — antes renderizava "—")
                return "Comando (sem par)" if rec.enderecamento.indices else "Órfão"
            return "—"
```

`_MOTIVO_LABEL` — adicionar:

```python
    "posicao_divergente": "Posição diverge do status",
```

`_MOTIVO_TOOLTIP` — adicionar:

```python
    "posicao_divergente": "Comando de posição com sigla diferente do status do mesmo equipamento, e o status é ambíguo (mais de uma sigla de posição). Escolha a sigla correta e paree manualmente.",
```

- [ ] **Step 4: Rodar testes + suíte**

Run: `python -m pytest -q tests/test_ui_modelo_tabela.py && python -m pytest -q tests/`
Expected: PASS. (Sem gate — task só de UI.)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py tests/test_ui_modelo_tabela.py
git commit -m "feat(ui): Pareado rotula comando sem par; label posicao_divergente"
```

---

## Fase 7 — Validação no dado real + closeout

### Task 12: diag rodada 3 — validar os casos do anot.txt fim-a-fim

**Files:**
- Create: `bench/resultados/diag_cva_rodada3.log` (saída do script existente)
- Modify (se necessário p/ aceitação): nenhum — task de MEDIÇÃO; qualquer falha = parar e reportar.

- [ ] **Step 1: Rodar o diagnóstico existente sobre o input real**

Run: `PYTHONPATH=src python bench/diag_cva.py > bench/resultados/diag_cva_rodada3.log 2>&1`
Expected: exit 0.

- [ ] **Step 2: Conferir critérios de aceite (spec §6) no log**

1. BC1 linha 14 (end. 80), BC2 linha 14 (end. 90), BC5_6 linhas 8/10 (end. 100/102): destino `TDT ReadWrite (fundido ...)` OU `revisão: modulo_duplicado_entre_sheets (fundido ...)` — **NUNCA** `comando_sem_discreto` nem sigla DJA1.
2. CVA11: `>= 5 comando(s) detectado(s) na entrada` (linhas 14-18 com direção Output vindas da seção CONTROLE/códigos DO) e **nenhum** `AUSENTE (perda silenciosa)`.
3. Seção 2 (CVA11 VAB): linhas de tensão continuam Analog; nenhuma linha `MEDIÇÃO`/`CONTROLE`/`SINALIZAÇÃO` aparece como sinal.
4. `AUSENTE (perda silenciosa): 0` no total.

- [ ] **Step 3: Parar e reportar**

Apresentar ao usuário o resumo do log (antes × depois por caso). Se algum critério falhar: **não seguir para a Task 13** — abrir investigação com o caso exato do log.

- [ ] **Step 4: Commit do log**

```bash
git add bench/resultados/diag_cva_rodada3.log
git commit -m "docs(diag): rodada 3 CVA - casos do anot.txt validados no dado real"
```

### Task 13: Closeout — ledger, DOX, memória

**Files:**
- Modify: `docs/AGENTS.md` (ledger de decisões — 1 linha por eixo E1-E6 com status)
- Modify: `src/tdt/AGENTS.md` (fluxo do pipeline: `fundir_pares_posicao` antes do `dc_pairer`; `particionar_endereco_duplicado` no boundary; `aplicar_identidade` 3-tupla)
- Modify: `docs/superpowers/specs/2026-07-14-sp-cva2-rodada2-design.md` (marcar implementado no topo, se for o padrão vigente do repo — conferir specs anteriores)

- [ ] **Step 1: Ledger em `docs/AGENTS.md`**

Adicionar linhas à tabela (formato das existentes), uma por decisão:

```
| Par de posição por particípio exato (ruído ABERTURA) | SP-CVA2 E1 14jul | implementado — pareamento_polaridade._polaridade_pura; prefixos seguem só em eh_texto_de_posicao |
| Reconciliação comando↔status de posição no dc_pairer | SP-CVA2 E2 14jul | implementado — _reconciliar_posicao; motivo novo posicao_divergente |
| Marcador de seção tolera numeração + códigos AI/AO/DI/DO + grandeza por token | SP-CVA2 E3 14jul | implementado — CVA11 comandos viram Output por evidência ESTRUTURAL (coerente com ledger "direção por texto bloqueada") |
| Fusão MultiCoord do par de posição ANTES do dc_pairer | SP-CVA2 E4 14jul | implementado — fundir_pares_posicao nos 2 call sites; fecha itens 1/13 de observações_pendentes |
| Sanitização módulo-por-linha + aviso divergência sheet×conteúdo | SP-CVA2 E5 14jul | implementado — dominante da sheet; sistema avisa, não corrige dado do cliente |
| Conservação total + gate endereço duplicado workbook-wide | SP-CVA2 E6 14jul | implementado — test_conservacao (todas as direções); particionar_endereco_duplicado (medido: 0 colisões no CVA real) |
```

- [ ] **Step 2: DOX pass em `src/tdt/AGENTS.md`**

Atualizar a linha do fluxo do pipeline (§Local Contracts): inserir `normalizador_estrutural.fundir_pares_posicao` entre `roteador` e `dc_pairer`, e `engine_tdt.particionar_endereco_duplicado` após `particionar_custom_id_duplicado`. Registrar `aplicar_identidade -> (sinais, confianca, avisos)`.

- [ ] **Step 3: Suíte completa + gate final**

Run: `python -m pytest -q tests/ && PYTHONPATH=src python -m bench.regressao`
Expected: PASS, `pct >= baseline`.

- [ ] **Step 4: Commit**

```bash
git add docs/AGENTS.md src/tdt/AGENTS.md docs/superpowers/specs/2026-07-14-sp-cva2-rodada2-design.md
git commit -m "docs: closeout SP-CVA2 (ledger, DOX)"
```

---

## Notas de execução

- **Ordem importa:** Tasks 1-2 (pareamento) e 3-5 (estruturação) são independentes entre si, mas a Task 6 (E4) assume 1-2 prontas e a Task 12 assume TUDO pronto. Executar na ordem numerada.
- **Gate cai em qualquer task:** parar, comparar o diff de casos do gate com o baseline, reportar ao usuário. Não "compensar" numa task seguinte.
- **Task 10 tem decision gate próprio** (medição no dado real antes do wiring) — respeitar o stop-and-report.
- Fixture nova de teste NUNCA copia dado do cliente (só textos curtos representativos, como os já usados).
