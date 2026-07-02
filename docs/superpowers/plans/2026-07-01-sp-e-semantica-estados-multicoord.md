# SP-E — Semântica de Estados + MultiCoord + Comando×Discreto — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminar double-bits falsos (SGF+SGFT etc.), emitir MultiCoord para pares de posição fundidos, distinguir incluído/excluído/atuado via filtro semântico duro, e mandar comando órfão para revisão — conforme spec `docs/superpowers/specs/2026-07-01-semantica-estados-multicoord-design.md`.

**Architecture:** Novo módulo puro `semantica_estados.py` (detecção de classe de estado no texto + classe do par de estados do MM da lista padrão). Consumido por: pipeline (filtro duro de candidatos D2 + whitelist por equipamento D6), normalizador_estrutural (fusão restrita → MultiCoord, D3) e dc_pairer (órfão → revisão + gate semântico, D5). `TipoSinal.is_double_bit` vira `datatype` de 3 valores e ganha `comando_duplo` para OUTCOORDS `N;N` vs `N` (D4).

**Tech Stack:** Python 3.14, dataclasses frozen, openpyxl, pytest. Sem dependência nova.

## Global Constraints

- Rodar tudo da raiz do repo (`C:\Users\vinic\Documents\programing\projetoTDT v2`); scripts avulsos precisam de `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH="src"`).
- Contratos são dataclasses **frozen**; enriquecimento via `dataclasses.replace`, nunca mutação.
- Features novas gateadas por `Config` (default ON para o filtro semântico, conforme spec).
- NÃO editar a lista padrão (`docs/Pontos Padrao ADMS_v6.xlsx`) nem o template (`docs/dnp3_template.xlsx`, 43 colunas em DNP3_DiscreteSignals).
- `datatype` assume exatamente: `"SingleBit"` | `"DoubleBit"` (nativo, input já traz `N;M` com M≠N numa linha) | `"MultiCoord"` (fusão de 2 pontos single-bit).
- Novos motivos de revisão: `estado_sem_candidato`, `fora_whitelist_equipamento`, `decisao_por_projeto`, `comando_sem_discreto`, `descartado_indefinido`, `descartado_redundante`.
- Suite existente deve permanecer verde a cada task (`python -m pytest tests/ -q`).
- Commits em PT, conventional commits, pequenos (1 por task).

---

### Task 1: Módulo `semantica_estados.py` (D1)

**Files:**
- Create: `src/tdt/semantica_estados.py`
- Test: `tests/test_semantica_estados.py`

**Interfaces:**
- Consumes: `tdt.contracts.SignalRecord` (só `.descricoes.normalizada`), `tdt.dados.lista_padrao.ListaPadraoADMS` (`.por_sigla(sigla) -> SinalPadrao | None`, campo `.mm`).
- Produces (usado pelas Tasks 5, 6, 7):
  - constantes `POSICAO, FUNCAO, ATIVACAO, LOCAL_REMOTO, EVENTO, INDEFINIDO: str`
  - `EstadoDetectado(classe: str, polaridade: str | None)` (frozen dataclass)
  - `detectar_estado(texto: str | None) -> EstadoDetectado | None`
  - `classe_do_mm(mm: str | None) -> str | None`
  - `compativel(estado: EstadoDetectado | None, classe_mm: str | None) -> bool`
  - `compatibilidade_texto(a: str | None, b: str | None) -> bool`
  - `filtrar_por_estado(rec, candidatos: list, lp) -> tuple[list, bool]` (lista mantida, zerou)

- [ ] **Step 1: Write the failing test**

Criar `tests/test_semantica_estados.py`:

```python
from tdt.contracts import Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.semantica_estados import (
    ATIVACAO, EVENTO, FUNCAO, INDEFINIDO, LOCAL_REMOTO, POSICAO,
    classe_do_mm, compatibilidade_texto, compativel, detectar_estado,
    filtrar_por_estado,
)


# --- detectar_estado --------------------------------------------------------

def test_detecta_evento_atuado():
    e = detectar_estado("PROTECAO SGF ATUADO")
    assert e.classe == EVENTO


def test_detecta_funcao_excluida():
    e = detectar_estado("PROTECAO SGF EXCLUIDA")
    assert e.classe == FUNCAO


def test_detecta_funcao_verbos_comando():
    assert detectar_estado("SGF EXCLUIR INCLUIR").classe == FUNCAO


def test_detecta_posicao_com_polaridade():
    assert detectar_estado("52 DESLIGADO") == detectar_estado("DISJUNTOR DESLIGADO")
    assert detectar_estado("52 DESLIGADO").classe == POSICAO
    assert detectar_estado("52 DESLIGADO").polaridade == "B"
    assert detectar_estado("52 LIGADO").polaridade == "A"
    assert detectar_estado("SECCIONADORA ABERTA").polaridade == "B"
    assert detectar_estado("SECCIONADORA FECHADA").polaridade == "A"


def test_detecta_ativacao():
    assert detectar_estado("81 E1 HABILITAR").classe == ATIVACAO
    assert detectar_estado("ESTAGIO 1 HABILITAR DESABILITAR").classe == ATIVACAO


def test_detecta_local_remoto():
    assert detectar_estado("CHAVE 43LR POS LOCAL").classe == LOCAL_REMOTO
    assert detectar_estado("CHAVE 43LR POS REMOTO").classe == LOCAL_REMOTO


def test_indefinido_vence():
    assert detectar_estado("52 INDEFINIDO").classe == INDEFINIDO


def test_ambiguo_vira_none():
    # EVENTO (FALHA) + POSICAO (LIGAR) = ambíguo — filtro nenhum > filtro errado
    assert detectar_estado("FALHA COMANDO DE LIGAR") is None


def test_sem_evidencia_vira_none():
    assert detectar_estado("TRIP FASE A") is None
    assert detectar_estado("") is None
    assert detectar_estado(None) is None


def test_desligado_nao_casa_prefixo_ligado():
    # startswith é ancorado: DESLIGADO não pode cair na polaridade A
    assert detectar_estado("DESLIGADO").polaridade == "B"


# --- classe_do_mm -----------------------------------------------------------

def test_classe_mm_evento():
    assert classe_do_mm("null@null___NORMAL@ATUADO___RelayTrip_S_TS_SA") == EVENTO


def test_classe_mm_funcao():
    assert classe_do_mm(
        "INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled___admsINV_S_TC_SS"
    ) == FUNCAO


def test_classe_mm_posicao():
    assert classe_do_mm(
        "DESLIGAR@LIGAR___DESLIGADO@LIGADO___SwitchStatus_D_TC_SE"
    ) == POSICAO


def test_classe_mm_local_remoto_com_underscore_simples():
    # MM real da LP tem "__" (não "___") depois dos estados
    assert classe_do_mm("null@null___REMOTO@LOCAL__Local_S_TS_SS") == LOCAL_REMOTO


def test_classe_mm_sem_estados():
    assert classe_do_mm("AUMENTAR@DIMINUIR___null@null___TapIncrement_S_TC_SS") is None
    assert classe_do_mm(None) is None
    assert classe_do_mm("TapIncrement") is None


# --- compativel / compatibilidade_texto -------------------------------------

def test_atuado_incompativel_com_funcao():
    est = detectar_estado("PROTECAO SGF ATUADO")
    assert compativel(est, FUNCAO) is False
    assert compativel(est, EVENTO) is True


def test_sem_evidencia_e_compativel():
    assert compativel(None, FUNCAO) is True
    assert compativel(detectar_estado("SGF ATUADO"), None) is True


def test_compatibilidade_texto_comando_funcao_vs_trip():
    assert compatibilidade_texto("SGF EXCLUIR INCLUIR", "PROTECAO SGF ATUADO") is False
    assert compatibilidade_texto("SGF EXCLUIR INCLUIR", "PROTECAO SGF EXCLUIDA") is True
    assert compatibilidade_texto("QUALQUER COISA", "PROTECAO SGF ATUADO") is True


# --- filtrar_por_estado ------------------------------------------------------

def _lp_stub():
    return ListaPadraoADMS(
        discretos=(
            SinalPadrao("SGF", "FUNCAO SGF", "Enabled", "Read",
                        "INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled_S_TS_SS", "Discrete"),
            SinalPadrao("SGFT", "TRIP SGF", "RelayTrip", "Read",
                        "null@null___NORMAL@ATUADO___RelayTrip_S_TS_SA", "Discrete"),
        ),
        analogicos=(),
    )


def _rec(desc):
    return SignalRecord(
        id="s:1", modulo=Modulo("AL11", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete"),
        enderecamento=Enderecamento("DNP3", (1535,)),
        descricoes=Descricoes(desc, desc),
    )


def test_filtro_elimina_sigla_de_estado_incompativel():
    cands = [Candidato("SGF", 0.9, "mesclado"), Candidato("SGFT", 0.7, "mesclado")]
    mantidos, zerou = filtrar_por_estado(_rec("PROTECAO SGF ATUADO"), cands, _lp_stub())
    assert [c.sigla for c in mantidos] == ["SGFT"]
    assert zerou is False


def test_filtro_zera_vai_pra_revisao():
    cands = [Candidato("SGF", 0.9, "mesclado")]
    mantidos, zerou = filtrar_por_estado(_rec("PROTECAO SGF ATUADO"), cands, _lp_stub())
    assert zerou is True
    assert mantidos == cands  # devolve originais p/ sugestões da revisão


def test_filtro_neutro_sem_estado_detectado():
    cands = [Candidato("SGF", 0.9, "mesclado")]
    mantidos, zerou = filtrar_por_estado(_rec("TRIP FASE A"), cands, _lp_stub())
    assert mantidos == cands and zerou is False
```

Nota: `TipoSinal("Discrete")` já usa a assinatura NOVA (Task 3). Como a Task 3 vem depois, neste momento use `TipoSinal("Discrete", False, "Input")` nos dois construtores acima e troque na Task 3 (o grep da Task 3 pega).

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_semantica_estados.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'tdt.semantica_estados'`

- [ ] **Step 3: Write the implementation**

Criar `src/tdt/semantica_estados.py`:

```python
"""Semântica de estados (SP-E D1) — classifica o par-de-estado que uma
descrição de sinal descreve e o compara com o par de estados do Message
Mapping da lista padrão. Base do filtro duro (D2), da fusão restrita (D3)
e do gate semântico do pareamento D+C (D5).

Classes derivadas dos pares reais do Export Base Full (237k sinais DNP3):
NORMAL@ATUADO (108k) e NORMAL@FALHA/DEFEITO/FALTA compartilham semântica de
"evento/alarme" — trips Custom existem (79_1, FCSF), então trip e alarme
ficam numa classe só (EVENTO); a distinção que importa é contra FUNCAO/
POSICAO/ATIVACAO/LOCAL_REMOTO.
"""

from __future__ import annotations

from dataclasses import dataclass

POSICAO = "posicao"          # aberto/fechado, ligado/desligado (SwitchStatus)
FUNCAO = "funcao"            # incluído/excluído (Enabled/ReclosingEnabled/Local)
ATIVACAO = "ativacao"        # ativado/desativado, habilitado/desabilitado
LOCAL_REMOTO = "local_remoto"
EVENTO = "evento"            # atuado, falha, defeito, falta, bloqueio
INDEFINIDO = "indefinido"    # transit de posição — nunca vira ponto (D3)


@dataclass(frozen=True)
class EstadoDetectado:
    classe: str
    # POSICAO: "A" = fechado/ligado, "B" = aberto/desligado. Demais: None.
    polaridade: str | None = None


# prefixo de token (texto upper, sem acentos — descrição normalizada) ->
# (classe, polaridade). Prefixos ancorados no INÍCIO do token, então
# "DESLIGADO".startswith("LIGA") é False — sem colisão LIGA/DESLIGA.
_LEXICO: tuple[tuple[str, str, str | None], ...] = (
    ("FECHA", POSICAO, "A"), ("LIGA", POSICAO, "A"),
    ("ABERT", POSICAO, "B"), ("ABRIR", POSICAO, "B"), ("DESLIGA", POSICAO, "B"),
    ("INCLUI", FUNCAO, None), ("EXCLUI", FUNCAO, None),
    ("ATIVA", ATIVACAO, None), ("DESATIVA", ATIVACAO, None),
    ("HABILITA", ATIVACAO, None), ("DESABILITA", ATIVACAO, None),
    ("LOCAL", LOCAL_REMOTO, None), ("REMOT", LOCAL_REMOTO, None),
    ("ATUAD", EVENTO, None), ("FALHA", EVENTO, None),
    ("DEFEITO", EVENTO, None), ("FALTA", EVENTO, None),
    ("BLOQUE", EVENTO, None), ("LIBERA", EVENTO, None),
    ("INDEFINID", INDEFINIDO, None),
)


def _classificar_token(tok: str) -> tuple[str, str | None] | None:
    for prefixo, classe, pol in _LEXICO:
        if tok.startswith(prefixo):
            return classe, pol
    return None


def detectar_estado(texto: str | None) -> EstadoDetectado | None:
    """Classe de estado da descrição, ou None (sem evidência OU ambígua).

    Mais de uma classe distinta no texto (ex. "FALHA COMANDO DE LIGAR" tem
    EVENTO+POSICAO) = ambíguo -> None: filtro nenhum é melhor que errado.
    INDEFINIDO vence qualquer outra (marcador estrutural, não par de estado).
    """
    if not texto:
        return None
    achados = [r for tok in texto.upper().split() if (r := _classificar_token(tok))]
    if not achados:
        return None
    classes = {c for c, _ in achados}
    if INDEFINIDO in classes:
        return EstadoDetectado(INDEFINIDO)
    if len(classes) > 1:
        return None
    pols = {p for _, p in achados if p is not None}
    pol = pols.pop() if len(pols) == 1 else None
    return EstadoDetectado(classes.pop(), pol)


def classe_do_mm(mm: str | None) -> str | None:
    """Classe do par de estados de um MM da lista padrão.

    Formato: "{CMD0@CMD1}___{EST0@EST1}___{Type}_{flags}". Alguns MMs reais
    usam "__" simples após os estados (ex. "...REMOTO@LOCAL__Local_S_TS_SS"),
    então o segmento de estados é cortado no primeiro "__" interno.
    """
    if not mm:
        return None
    partes = mm.split("___")
    if len(partes) < 2:
        return None
    estados = partes[1].split("__")[0]
    classes: set[str] = set()
    for est in estados.split("@"):
        r = _classificar_token(est.strip().upper())
        if r:
            classes.add(r[0])
    return classes.pop() if len(classes) == 1 else None


def compativel(estado: EstadoDetectado | None, classe_mm: str | None) -> bool:
    """Filtro duro D2: sem evidência de um dos lados = compatível."""
    if estado is None or classe_mm is None:
        return True
    if estado.classe == INDEFINIDO:
        return True  # tratado estruturalmente (D3), não pelo matching
    return estado.classe == classe_mm


def compatibilidade_texto(a: str | None, b: str | None) -> bool:
    """Dois textos podem descrever o mesmo ponto? (gate do pareamento D+C)."""
    ea, eb = detectar_estado(a), detectar_estado(b)
    if ea is None or eb is None:
        return True
    if INDEFINIDO in (ea.classe, eb.classe):
        return True
    return ea.classe == eb.classe


def filtrar_por_estado(rec, candidatos, lp):
    """(mantidos, zerou). zerou=True: havia candidatos e o filtro eliminou
    todos — o chamador manda para revisão com os ORIGINAIS como sugestão."""
    est = detectar_estado(rec.descricoes.normalizada)
    if est is None or est.classe == INDEFINIDO or not candidatos:
        return candidatos, False
    mantidos = []
    for c in candidatos:
        sp = lp.por_sigla(c.sigla)
        if compativel(est, classe_do_mm(sp.mm if sp else None)):
            mantidos.append(c)
    if not mantidos:
        return candidatos, True
    return mantidos, False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_semantica_estados.py -q`
Expected: PASS (todos)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/semantica_estados.py tests/test_semantica_estados.py
git commit -m "feat(spE): modulo semantica_estados — classes de estado + compatibilidade com MM"
```

---

### Task 2: Knobs de Config (suporte a D2/D5/D6)

**Files:**
- Modify: `src/tdt/config.py` (fim da dataclass `Config`)
- Test: `tests/test_config.py` (acrescentar 1 teste)

**Interfaces:**
- Produces (usado pelas Tasks 5, 6, 7): campos de `Config`:
  - `filtro_semantica_estados: bool = True`
  - `siglas_revisao_projeto: frozenset[str] = frozenset({"LIBM"})`
  - `siglas_write_legitimo: frozenset[str] = frozenset({"CDC"})`
  - `siglas_fundiveis_extra: frozenset[str] = frozenset()`
  - `siglas_por_equipamento: dict[str, frozenset[str]]` com chave `"Seccionadora"`

- [ ] **Step 1: Write the failing test**

Acrescentar em `tests/test_config.py`:

```python
def test_config_spe_defaults():
    from tdt.config import Config
    cfg = Config()
    assert cfg.filtro_semantica_estados is True
    assert "LIBM" in cfg.siglas_revisao_projeto
    assert "CDC" in cfg.siglas_write_legitimo
    assert cfg.siglas_fundiveis_extra == frozenset()
    secc = cfg.siglas_por_equipamento["Seccionadora"]
    assert {"SECC", "SECG", "DSEC", "43LR", "LIBM"} <= secc
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_config.py::test_config_spe_defaults -q`
Expected: FAIL — `AttributeError: ... 'filtro_semantica_estados'`

- [ ] **Step 3: Write the implementation**

Acrescentar ao final da dataclass `Config` em `src/tdt/config.py`:

```python
    # --- SP-E: semântica de estados e políticas por projeto ------------------
    # D2: filtro duro estado-detectado × par de estados do MM da lista padrão.
    filtro_semantica_estados: bool = True
    # Sigla decidida que cada projeto escolhe incluir ou não (real GTD
    # descartou LIBM; base full tem 36) -> rebaixa para revisão.
    siglas_revisao_projeto: frozenset[str] = frozenset({"LIBM"})
    # D5: comandos que são Write legítimo (sem discreto de status).
    siglas_write_legitimo: frozenset[str] = frozenset({"CDC"})
    # D3: siglas fundíveis além das SwitchStatus da lista padrão.
    siglas_fundiveis_extra: frozenset[str] = frozenset()
    # D6: whitelist de siglas por equipamento_alvo (semente = medição no
    # Export Base Full 27fev2026, sinais com equip 89-*/29-* no nome; 2103
    # sinais). Estender por medição quando aparecer sigla nova real.
    siglas_por_equipamento: dict[str, frozenset[str]] = field(
        default_factory=lambda: {
            "Seccionadora": frozenset({
                "SECF", "DSEC", "SECC", "43LR", "SECG", "SECB", "SECT",
                "CCCO", "CCFL", "CCMO", "FSEC", "OI", "LIBM", "CCCM",
                "CCAL", "BSEC", "MANI", "MDCM", "FLFC", "BBFC", "BBAB",
                "FLAB", "FALH", "PROT", "CCLO", "VMTC", "BBA2", "SOBC",
                "BATA", "MINC",
            }),
        }
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_config.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/config.py tests/test_config.py
git commit -m "feat(spE): knobs de config — filtro semantico, whitelists e politicas por projeto"
```

---

### Task 3: `TipoSinal.datatype` + `comando_duplo` (D4 — contrato e estruturadores)

**Files:**
- Modify: `src/tdt/contracts.py:32-37`
- Modify: `src/tdt/normalizacao/estruturador.py` (linhas ~86-90 e ~134)
- Modify: `src/tdt/normalizacao/estruturador_homogeneo.py:90-95`
- Modify: `src/tdt/normalizador_estrutural.py:67` (migração mecânica; regra nova é a Task 5)
- Modify: `src/tdt/engine_tdt.py:184` (migração mecânica; OUTCOORDS é a Task 4)
- Modify: todo call-site de `TipoSinal(` / `is_double_bit` (grep — inclui `tests/` e `bench/`)
- Test: `tests/test_estruturador.py`, `tests/test_estruturador_homogeneo.py` (novos casos)

**Interfaces:**
- Produces (usado pelas Tasks 4, 5):

```python
@dataclass(frozen=True)
class TipoSinal:
    categoria: str  # "Discrete" | "Analog" | "DiscreteAnalog"
    datatype: str = "SingleBit"  # "SingleBit" | "DoubleBit" (nativo) | "MultiCoord" (fusão D3)
    direcao: str = "Input"  # "Input" | "Output" | "InputOutput"
    categoria_confiavel: bool = True
    comando_duplo: bool = True  # Comando D (OUTCOORDS "N;N") vs Comando S ("N")
```

- [ ] **Step 1: Write the failing tests**

Acrescentar em `tests/test_estruturador.py` (usar os helpers/formato de rows já existentes no arquivo como referência; construir rows mínimas):

```python
from tdt.config import Config
from tdt.contracts import MapaColunas
from tdt.normalizacao.estruturador import estruturar


def _estruturar_rows(rows):
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1, "tipo": 2})
    return estruturar(rows, mapa, sheet_name="S1", config=Config())


def test_input_com_endereco_duplo_nativo_vira_doublebit():
    rows = [("desc", "idx", "tipo"),
            ("Secc. 89-16 Aberta/Fechada", "1100;1101", "D")]
    regs = _estruturar_rows(rows)
    assert regs[0].tipo_sinal.datatype == "DoubleBit"


def test_comando_nn_continua_singlebit():
    rows = [("desc", "idx", "tipo"),
            ("CMD Secc. 89-16", "3;3", "C")]
    regs = _estruturar_rows(rows)
    assert regs[0].tipo_sinal.datatype == "SingleBit"
    assert regs[0].tipo_sinal.comando_duplo is True


def test_comando_s_marca_comando_nao_duplo():
    rows = [("desc", "idx", "tipo"),
            ("CMD RMT.009 81 E1 Habilitar", "1504", "Comando S"),
            ("CMD RMT.002 SGF Excluir/Incluir", "1502", "Comando D")]
    regs = _estruturar_rows(rows)
    assert regs[0].tipo_sinal.direcao == "Output"
    assert regs[0].tipo_sinal.comando_duplo is False
    assert regs[1].tipo_sinal.comando_duplo is True
```

Acrescentar em `tests/test_estruturador_homogeneo.py` um caso análogo ao nativo (linha com `INDEX DNP3 = "1100;1101"` e tipo `D` → `datatype == "DoubleBit"`), seguindo o formato de rows homogêneas que os testes existentes do arquivo já usam (header com "UTILIZADO?", "MODULO", "TIPO", "DESCRICAO DO PONTO", "SIGLA SINAL", "INDEX DNP3").

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_estruturador.py tests/test_estruturador_homogeneo.py -q`
Expected: FAIL — `TypeError`/`AttributeError` (assinatura antiga)

- [ ] **Step 3: Migrar o contrato**

Em `src/tdt/contracts.py`, substituir a classe `TipoSinal` inteira pelo bloco da seção **Interfaces** acima. Atualizar também o comentário da linha 43 de `Enderecamento` para: `# (1100, 1101) DoubleBit nativo/MultiCoord | (17,) | () sem endereço`.

- [ ] **Step 4: Migrar todos os call-sites (mecânico)**

Run: `grep -rn "is_double_bit\|TipoSinal(" src tests bench scripts`

Para cada ocorrência:
- `TipoSinal(categoria, is_double_bit=False, direcao=d, categoria_confiavel=c)` → `TipoSinal(categoria, direcao=d, categoria_confiavel=c)` (datatype default) — **exceto** nos estruturadores (Step 5, regra nativa).
- `TipoSinal("Discrete", double, "Input")` (posicional, testes) → `TipoSinal("Discrete", "DoubleBit" if double else "SingleBit", "Input")`.
- `replace(x.tipo_sinal, is_double_bit=True)` (normalizador_estrutural.py:67) → `replace(x.tipo_sinal, datatype="DoubleBit")` (comportamento preservado; a Task 5 muda para MultiCoord).
- `rec.tipo_sinal.is_double_bit` (engine_tdt.py:184) → linha inteira vira:
  `"Input Data Type": rec.tipo_sinal.datatype,`
- Asserts de teste `tipo_sinal.is_double_bit is True` → `tipo_sinal.datatype == "DoubleBit"`.
- `bench/benchmark.py` e demais: mesmo padrão mecânico.

- [ ] **Step 5: Regra de datatype nativo + Comando S nos estruturadores**

Em `src/tdt/normalizacao/estruturador.py`, dentro do loop (hoje linhas 86-90), depois de `categoria, direcao = cat_dir or secao`:

```python
        tipo_norm = (
            _norm(row[c_tipo]) if c_tipo is not None and c_tipo < len(row) else ""
        )
        comando_duplo = not (direcao == "Output" and tipo_norm == "COMANDO S")
```

e depois de `indices = _parse_indices(...)`:

```python
        datatype = (
            "DoubleBit"
            if len(indices) == 2 and indices[0] != indices[1]
            else "SingleBit"
        )
```

No construtor (linha ~134):

```python
                tipo_sinal=TipoSinal(categoria, datatype=datatype, direcao=direcao,
                                     categoria_confiavel=confiavel,
                                     comando_duplo=comando_duplo),
```

Em `src/tdt/normalizacao/estruturador_homogeneo.py` (linha ~90), depois de `indices = _parse_indices(...)`:

```python
        datatype = (
            "DoubleBit"
            if len(indices) == 2 and indices[0] != indices[1]
            else "SingleBit"
        )
```

e na linha 95:

```python
            tipo_sinal=TipoSinal(categoria, datatype=datatype, direcao=direcao,
                                 categoria_confiavel=True),
```

Obs.: comando com endereço `N;N` (índices iguais) fica SingleBit — a condição `indices[0] != indices[1]` já cobre.

- [ ] **Step 6: Run FULL suite**

Run: `python -m pytest tests/ -q`
Expected: PASS (suite inteira — a migração é mecânica; falha aqui = call-site esquecido, repetir grep)

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor(spE): TipoSinal.datatype (Single/Double/MultiCoord) + comando_duplo; DoubleBit nativo N;M"
```

---

### Task 4: Engine — Input Data Type + OUTCOORDS `N;N` vs `N` (D4)

**Files:**
- Modify: `src/tdt/engine_tdt.py:132-135` (`_coords_comando`) e `:159-169` (chamadas)
- Modify: `src/tdt/dc_pairer.py:27-39` (`fundir` propaga `comando_duplo`)
- Test: `tests/test_engine_tdt.py`, `tests/test_dc_pairer.py`

**Interfaces:**
- Consumes: `TipoSinal.datatype`, `TipoSinal.comando_duplo` (Task 3).
- Produces: coluna TDT "Input Data Type" = datatype literal; "Output Coordinates" = `"N;N"` quando `comando_duplo=True` e 1 índice, `"N"` quando `False`.

- [ ] **Step 1: Write the failing tests**

Em `tests/test_dc_pairer.py` (seguir helper `_rec` local do arquivo, adicionando `comando_duplo` no comando):

```python
def test_fundir_propaga_comando_duplo():
    from dataclasses import replace
    from tdt.dc_pairer import fundir
    status = _sinal("AL11:1", "81U1", "Input", [1539])   # usar o helper local do arquivo
    comando = _sinal("AL11:2", "81U1", "Output", [1504])
    comando = replace(comando, tipo_sinal=replace(comando.tipo_sinal, comando_duplo=False))
    fundido = fundir(status, comando)
    assert fundido.tipo_sinal.comando_duplo is False
    assert fundido.enderecamento.indices_saida == (1504,)
```

Em `tests/test_engine_tdt.py` (seguir o padrão dos testes existentes que geram workbook e leem células):

```python
def test_outcoords_comando_s_sem_duplicar():
    # registro InputOutput com comando_duplo=False -> Output Coordinates "1504"
    # registro InputOutput com comando_duplo=True  -> Output Coordinates "1502;1502"
    # registro MultiCoord -> Input Data Type "MultiCoord"
    ...  # construir 3 SignalRecords no padrão dos testes existentes do arquivo,
         # gerar com engine_tdt.gerar e assertar as 3 células.
```

(Escrever o teste completo copiando o setup de template/leitura de célula já usado em `tests/test_engine_tdt.py` — o arquivo já tem fixture/helper para isso; assertar: `Output Coordinates == "1504"`, `== "1502;1502"`, `Input Data Type == "MultiCoord"`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dc_pairer.py tests/test_engine_tdt.py -q`
Expected: FAIL (comando_duplo não propagado; OUTCOORDS sempre duplica)

- [ ] **Step 3: Write the implementation**

`src/tdt/dc_pairer.py` — em `fundir`:

```python
    return replace(
        status,
        tipo_sinal=replace(
            status.tipo_sinal, direcao="InputOutput",
            comando_duplo=comando.tipo_sinal.comando_duplo,
        ),
        enderecamento=replace(
            status.enderecamento, indices_saida=comando.enderecamento.indices
        ),
    )
```

`src/tdt/engine_tdt.py`:

```python
def _coords_comando(indices: tuple[int, ...], duplo: bool = True) -> str:
    if len(indices) == 1:
        return f"{indices[0]};{indices[0]}" if duplo else str(indices[0])
    return ";".join(str(i) for i in indices)
```

e nas duas chamadas em `_valores` passar `rec.tipo_sinal.comando_duplo`:

```python
        coords_saida = _coords_comando(rec.enderecamento.indices, rec.tipo_sinal.comando_duplo)
```
```python
        coords_saida = (
            _coords_comando(rec.enderecamento.indices_saida, rec.tipo_sinal.comando_duplo)
            if rec.enderecamento.indices_saida else ""
        )
```

("Input Data Type" já emite `rec.tipo_sinal.datatype` desde a Task 3.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_dc_pairer.py tests/test_engine_tdt.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py src/tdt/dc_pairer.py tests/test_engine_tdt.py tests/test_dc_pairer.py
git commit -m "feat(spE): OUTCOORDS N;N (cmd D) vs N (cmd S) + emissao de MultiCoord no TDT"
```

---

### Task 5: Fusão restrita → MultiCoord + descartes (D3)

**Files:**
- Modify: `src/tdt/normalizador_estrutural.py` (reescrita de `corrigir`)
- Modify: `src/tdt/pipeline.py:383` (`gerar_tdt`) e `:527` (`executar`) — passar whitelist
- Modify: `src/tdt/contracts.py:137` (docstring de motivos de `ItemRevisao`)
- Test: `tests/test_normalizador_estrutural.py` (reescrever/estender)

**Interfaces:**
- Consumes: `semantica_estados.{detectar_estado, POSICAO, LOCAL_REMOTO, INDEFINIDO}` (Task 1); `TipoSinal.datatype` (Task 3); `Config.siglas_fundiveis_extra` (Task 2).
- Produces: `corrigir(registros, whitelist_posicao: frozenset[str] = frozenset()) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]` — nova assinatura usada pelo pipeline; helper `_whitelist_posicao(lp, config)` em `pipeline.py`.

- [ ] **Step 1: Rewrite the tests**

Substituir o conteúdo de `tests/test_normalizador_estrutural.py` por:

```python
from tdt.contracts import (
    Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.normalizador_estrutural import corrigir

WL = frozenset({"SECC", "DJF1", "SECG"})


def _rec(rid, sigla, indices, desc=None, datatype="SingleBit"):
    d = desc if desc is not None else sigla
    return SignalRecord(
        id=rid,
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", datatype, "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(d, d),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_par_posicao_whitelist_vira_multicoord():
    regs = [_rec("LT3:1", "SECC", [100], "SECCIONADORA ABERTA"),
            _rec("LT3:2", "SECC", [101], "SECCIONADORA FECHADA")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (100, 101)
    assert corrigidos[0].tipo_sinal.datatype == "MultiCoord"
    assert erros == ()


def test_nao_funde_fora_da_whitelist():
    # SGF Excluída + SGF Atuado consecutivos: NUNCA funde (bug histórico 1534;1535)
    regs = [_rec("AL11:1", "SGF", [1534], "PROTECAO SGF EXCLUIDA"),
            _rec("AL11:2", "SGF", [1535], "PROTECAO SGF ATUADO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2
    assert all(c.tipo_sinal.datatype == "SingleBit" for c in corrigidos)
    assert erros == ()


def test_nao_funde_sem_estados_opostos():
    # mesma sigla whitelisted mas estados iguais -> não é par de posição
    regs = [_rec("LT3:1", "SECC", [100], "SECCIONADORA ABERTA"),
            _rec("LT3:2", "SECC", [101], "SECCIONADORA ABERTA")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2


def test_doublebit_nativo_passa_intacto():
    regs = [_rec("IMA:1", "SECC", [1100, 1101], "SECC 89-16", datatype="DoubleBit")]
    corrigidos, erros = corrigir(regs, WL)
    assert corrigidos[0].tipo_sinal.datatype == "DoubleBit"
    assert corrigidos[0].enderecamento.indices == (1100, 1101)


def test_indefinido_descartado_com_registro():
    regs = [_rec("AL11:1", "DJF1", [1500], "52 DESLIGADO"),
            _rec("AL11:2", "DJF1", [1501], "52 LIGADO"),
            _rec("AL11:3", "DJF1", [1502], "52 INDEFINIDO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].tipo_sinal.datatype == "MultiCoord"
    assert [e.motivo for e in erros] == ["descartado_indefinido"]


def test_local_remoto_fica_so_o_bit_local():
    regs = [_rec("AL11:1", "43LR", [1504], "CHAVE 43LR POS LOCAL"),
            _rec("AL11:2", "43LR", [1505], "CHAVE 43LR POS REMOTO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (1504,)
    assert [e.motivo for e in erros] == ["descartado_redundante"]


def test_endereco_duplicado_continua_revisao():
    regs = [_rec("LT3:1", "DJ", [100]), _rec("LT3:2", "DJ", [100])]
    corrigidos, erros = corrigir(regs, WL)
    assert corrigidos == ()
    assert all(e.motivo == "endereco_duplicado" for e in erros)


def test_sem_endereco_vai_para_revisao():
    corrigidos, erros = corrigir([_rec("LT3:9", "DJ", [])], WL)
    assert erros[0].motivo == "sem_endereco"


def test_nao_consecutivos_seguem_independentes():
    regs = [_rec("LT3:1", "DJA1", [100], "DISJUNTOR ABERTO"),
            _rec("LT3:2", "DJA1", [108], "DISJUNTOR FECHADO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2
    assert erros == ()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_normalizador_estrutural.py -q`
Expected: FAIL (assinatura/regra antiga)

- [ ] **Step 3: Rewrite `corrigir`**

Substituir `src/tdt/normalizador_estrutural.py` por:

```python
"""Corrige a estrutura dos sinais classificados (SP-E D3).

- Par de POSIÇÃO do mesmo equipamento (sigla na whitelist SwitchStatus,
  estados opostos aberto/fechado ou ligado/desligado, endereços consecutivos)
  vira UM sinal ``MultiCoord`` — nunca ``DoubleBit`` (reservado ao nativo N;M).
- Estado "Indefinido" (transit de posição) nunca vira ponto -> descartado.
- Par complementar LOCAL/REMOTO: fica o bit LOCAL (regra GTD real 43LR).
- Duplicata de MESMO endereço -> revisão; sem endereço -> revisão.
- Todo o resto segue como single-bit independente.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.contracts import Enderecamento, ItemRevisao, SignalRecord
from tdt.semantica_estados import INDEFINIDO, LOCAL_REMOTO, POSICAO, detectar_estado


def _chave(rec: SignalRecord) -> tuple:
    # Inclui o equipamento: a TDT nomeia o ponto como {SE}_{modulo}_{equip}_{sigla},
    # então mesma (modulo, sigla) com equipamentos distintos NÃO são duplicatas.
    return (rec.modulo.nome, rec.eletrico.nome_equipamento, rec.sigla_sinal)


def _estado(rec: SignalRecord):
    return detectar_estado(rec.descricoes.normalizada)


def _par_posicao_oposta(a: SignalRecord, b: SignalRecord) -> bool:
    ea, eb = _estado(a), _estado(b)
    return (
        ea is not None and eb is not None
        and ea.classe == POSICAO and eb.classe == POSICAO
        and ea.polaridade is not None and eb.polaridade is not None
        and ea.polaridade != eb.polaridade
    )


def _fundir_multicoord(a: SignalRecord, b: SignalRecord) -> SignalRecord:
    return replace(
        a,
        enderecamento=Enderecamento(
            a.enderecamento.protocolo,
            a.enderecamento.indices + b.enderecamento.indices,
        ),
        tipo_sinal=replace(a.tipo_sinal, datatype="MultiCoord"),
    )


def corrigir(
    registros: list[SignalRecord],
    whitelist_posicao: frozenset[str] = frozenset(),
) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]:
    corrigidos: list[SignalRecord] = []
    erros: list[ItemRevisao] = []

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        if not rec.enderecamento.indices:
            erros.append(ItemRevisao(rec, motivo="sem_endereco"))
            continue
        est = _estado(rec)
        if est is not None and est.classe == INDEFINIDO:
            erros.append(ItemRevisao(rec, motivo="descartado_indefinido"))
            continue
        grupos[_chave(rec)].append(rec)

    for grupo in grupos.values():
        if len(grupo) == 1:
            corrigidos.append(grupo[0])
            continue

        # Par complementar LOCAL/REMOTO: fica só o bit LOCAL (GTD real: 43LR
        # usa 1504 REMOTO@LOCAL; 1505 é redundante).
        if len(grupo) == 2:
            estados = [_estado(r) for r in grupo]
            if all(e is not None and e.classe == LOCAL_REMOTO for e in estados):
                com_local = [
                    r for r in grupo
                    if "LOCAL" in r.descricoes.normalizada.upper().split()
                ]
                if len(com_local) == 1:
                    corrigidos.append(com_local[0])
                    outro = grupo[0] if grupo[1] is com_local[0] else grupo[1]
                    erros.append(ItemRevisao(outro, motivo="descartado_redundante"))
                    continue

        ordenados = sorted(grupo, key=lambda r: r.enderecamento.indices[0])
        usados: set[int] = set()
        i = 0
        while i < len(ordenados) - 1:
            a, b = ordenados[i], ordenados[i + 1]
            fundivel = (
                len(a.enderecamento.indices) == 1
                and len(b.enderecamento.indices) == 1
                and b.enderecamento.indices[0] == a.enderecamento.indices[0] + 1
                and (a.sigla_sinal or "").upper() in whitelist_posicao
                and _par_posicao_oposta(a, b)
            )
            duplicata = a.enderecamento.indices == b.enderecamento.indices
            if fundivel:
                corrigidos.append(_fundir_multicoord(a, b))
                usados.update((i, i + 1))
                i += 2
            elif duplicata:
                erros.append(ItemRevisao(a, motivo="endereco_duplicado"))
                erros.append(ItemRevisao(b, motivo="endereco_duplicado"))
                usados.update((i, i + 1))
                i += 2
            else:
                i += 1
        # Não fundidos e sem duplicata: single-bit independentes. Colisão de
        # nome na saída é responsabilidade do diag_estrutura (Task 8).
        corrigidos.extend(
            ordenados[j] for j in range(len(ordenados)) if j not in usados
        )

    return tuple(corrigidos), tuple(erros)
```

- [ ] **Step 4: Wire no pipeline**

Em `src/tdt/pipeline.py`, adicionar helper (perto de `_vocab_dominio`):

```python
def _whitelist_posicao(lp: ListaPadraoADMS, config: Config | None = None) -> frozenset[str]:
    """Siglas fundíveis em MultiCoord (D3): SwitchStatus da lista padrão +
    extras de config."""
    wl = frozenset(
        s.sigla.upper() for s in lp.discretos if s.signal_type == "SwitchStatus"
    )
    extra = config.siglas_fundiveis_extra if config is not None else frozenset()
    return wl | extra
```

Atualizar as 2 chamadas de `corrigir`:

```python
def gerar_tdt(registros, template_path, lp, subestacao=None, aliases=None, config=None):
    """Gera o workbook TDT a partir de uma lista (já decidida/editada) de registros."""
    lst = _aplicar_aliases(list(registros), aliases)
    pareados, _rev = dc_pairer.parear(lst, config)
    corrigidos, _rev2 = corrigir(list(pareados), _whitelist_posicao(lp, config))
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    return engine_tdt.gerar(lista, template_path, lp)
```

e em `executar` (linha ~527):

```python
        pareados, rev_pair = dc_pairer.parear(decididos, config)
        corrigidos, rev_estrut = corrigir(list(pareados), _whitelist_posicao(lp, config))
```

Run: `grep -rn "gerar_tdt(" src tests` — atualizar chamadores (UI `worker.py`/`tela_revisao.py` se passarem posicionais) para a nova assinatura (config é opcional; chamadas existentes continuam válidas se usarem keywords).

Atualizar docstring de `ItemRevisao.motivo` em `src/tdt/contracts.py:137` acrescentando: `|"descartado_indefinido"|"descartado_redundante"|"comando_sem_discreto"|"estado_sem_candidato"|"fora_whitelist_equipamento"|"decisao_por_projeto"`.

- [ ] **Step 5: Run tests + full suite**

Run: `python -m pytest tests/test_normalizador_estrutural.py -q` → PASS
Run: `python -m pytest tests/ -q` → PASS (testes de pipeline que chamam corrigir com assinatura antiga: atualizar mecanicamente)

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat(spE): fusao restrita a posicao -> MultiCoord; descarta Indefinido e bit remoto redundante"
```

---

### Task 6: Filtro duro no matching + whitelist por equipamento + LIBM (D2/D6)

**Files:**
- Modify: `src/tdt/pipeline.py` (`_classificar_sinal` após linha ~212; `_classificar_roteado` ramo confiável ~linha 302; loop de `executar` ~linha 508; import)
- Test: `tests/test_pipeline_semantica.py` (novo)

**Interfaces:**
- Consumes: `semantica_estados.filtrar_por_estado` (Task 1); `Config.{filtro_semantica_estados, siglas_por_equipamento, siglas_revisao_projeto}` (Task 2).
- Produces: registros com `status="revisao"` e `justificativa` ∈ {`estado_sem_candidato`, `fora_whitelist_equipamento`} saindo de `_classificar_sinal`; `ItemRevisao` com esses motivos e com `decisao_por_projeto`.

- [ ] **Step 1: Write the failing tests**

Criar `tests/test_pipeline_semantica.py`:

```python
from dataclasses import replace

from tdt import pipeline
from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Eletrico, Enderecamento, ItemRevisao, Modulo,
    SignalRecord, TipoSinal,
)


def _rec(desc, equip_alvo=None, inferido=False):
    return SignalRecord(
        id="s:1", modulo=Modulo("AL11", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(equipamento_alvo=equip_alvo, equipamento_inferido=inferido),
    )


def test_roteado_mapeia_justificativa_para_motivo(monkeypatch):
    rec = _rec("PROTECAO SGF ATUADO")
    rev = replace(rec, status="revisao", justificativa="estado_sem_candidato",
                  candidatos=(Candidato("SGF", 0.9, "mesclado"),))
    monkeypatch.setattr(pipeline, "_classificar_sinal", lambda *a, **k: rev)
    scorers = pipeline._Scorers(None, None, None, Config())
    decidido, item = pipeline._classificar_roteado(
        rec, scorers, scorers, diagnostico=False, lista_padrao=object(),
    )
    assert decidido is None
    assert item.motivo == "estado_sem_candidato"
    assert item.candidatos_sugeridos == rev.candidatos[:3]


def test_roteado_mapeia_fora_whitelist(monkeypatch):
    rec = _rec("TERRA LIBERA MANOBRA", equip_alvo="Seccionadora")
    rev = replace(rec, status="revisao", justificativa="fora_whitelist_equipamento")
    monkeypatch.setattr(pipeline, "_classificar_sinal", lambda *a, **k: rev)
    scorers = pipeline._Scorers(None, None, None, Config())
    decidido, item = pipeline._classificar_roteado(
        rec, scorers, scorers, diagnostico=False, lista_padrao=object(),
    )
    assert item.motivo == "fora_whitelist_equipamento"
```

Obs.: `ancoragem_sigla.detectar` roda antes de `_classificar_sinal` no ramo confiável — se precisar, monkeypatchar `pipeline.ancoragem_sigla.detectar` para `lambda *a, **k: []`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_pipeline_semantica.py -q`
Expected: FAIL (motivo cai em `score_baixo`)

- [ ] **Step 3: Write the implementation**

Em `src/tdt/pipeline.py`:

1. Import: acrescentar `semantica_estados` ao bloco `from tdt import (...)`.

2. Em `_classificar_sinal`, logo após `fundidos = filtro_preciso.filtrar_especificidade(rec, fundidos, lista_padrao, config)` (dentro do `if lista_padrao is not None:`):

```python
        # SP-E D2: filtro duro estado-detectado × par de estados do MM.
        if config.filtro_semantica_estados:
            fundidos, zerou = semantica_estados.filtrar_por_estado(
                rec, fundidos, lista_padrao
            )
            if zerou:
                return replace(
                    rec, candidatos=tuple(fundidos[:3]), status="revisao",
                    justificativa="estado_sem_candidato",
                )
        # SP-E D6: whitelist de siglas por equipamento (só extração explícita).
        wl_equip = config.siglas_por_equipamento.get(rec.eletrico.equipamento_alvo or "")
        if wl_equip and not rec.eletrico.equipamento_inferido:
            dentro = [c for c in fundidos if c.sigla.upper() in wl_equip]
            if fundidos and not dentro:
                return replace(
                    rec, candidatos=tuple(fundidos[:3]), status="revisao",
                    justificativa="fora_whitelist_equipamento",
                )
            fundidos = dentro
```

3. Em `_classificar_roteado`, ramo confiável, logo após `d = _classificar_sinal(...)`:

```python
        if d.status == "revisao" and d.justificativa in (
            "estado_sem_candidato", "fora_whitelist_equipamento",
        ):
            return None, ItemRevisao(
                d, motivo=d.justificativa, candidatos_sugeridos=d.candidatos[:3]
            )
```

(No dual-pass — categoria não confiável — o registro em revisão conta como "não decidiu" e cai no fluxo existente de `score_baixo`; aceitável, GTD tem categoria confiável na quase totalidade.)

4. No loop de `executar` (~linha 508), antes do `if rec.id in ids_indefinidos:`:

```python
            if decidido is not None:
                if (decidido.sigla_sinal or "").upper() in config.siglas_revisao_projeto:
                    revisao.append(ItemRevisao(
                        decidido, motivo="decisao_por_projeto",
                        candidatos_sugeridos=decidido.candidatos[:3],
                    ))
                elif rec.id in ids_indefinidos:
```

(reindentar o bloco existente para o `elif`/`else` seguinte.)

- [ ] **Step 4: Run tests + full suite**

Run: `python -m pytest tests/test_pipeline_semantica.py -q` → PASS
Run: `python -m pytest tests/ -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline_semantica.py
git commit -m "feat(spE): filtro duro estado->MM no matching + whitelist por equipamento + LIBM p/ revisao"
```

---

### Task 7: dc_pairer — comando órfão em revisão + gate semântico (D5)

**Files:**
- Modify: `src/tdt/dc_pairer.py` (`parear` e `_parear_catchall`)
- Test: `tests/test_dc_pairer.py`

**Interfaces:**
- Consumes: `semantica_estados.compatibilidade_texto` (Task 1); `Config.siglas_write_legitimo` (Task 2).
- Produces: `ItemRevisao(motivo="comando_sem_discreto")` para Output órfão fora da whitelist; catch-all N×M não casa textos de classes de estado diferentes.

- [ ] **Step 1: Write the failing tests**

Acrescentar em `tests/test_dc_pairer.py` (usar o helper de construção de sinais já existente no arquivo; `desc` controla `descricoes.normalizada`):

```python
def test_comando_orfao_vai_para_revisao():
    comando = _sinal("AL11:1", "81U1", "Output", [1504])
    saida, revisao = parear([comando], Config())
    assert saida == ()
    assert [r.motivo for r in revisao] == ["comando_sem_discreto"]


def test_cdc_orfao_continua_write():
    comando = _sinal("TR1:1", "CDC", "Output", [700, 701])
    saida, revisao = parear([comando], Config())
    assert len(saida) == 1
    assert revisao == ()


def test_catchall_nao_casa_classes_de_estado_diferentes():
    # comando de função (excluir/incluir) não pode casar status de EVENTO (atuado)
    status_trip = _sinal("AL11:1", "SGF", "Input", [1535], desc="PROTECAO SGF ATUADO")
    comando = _sinal("AL11:2", "SGF", "Output", [1502], desc="SGF EXCLUIR INCLUIR")
    saida, revisao = parear([status_trip, comando], Config())
    # não funde: status segue standalone, comando vira revisão
    assert any(r.tipo_sinal.direcao == "Input" for r in saida)
    assert [r.motivo for r in revisao] == ["pareamento_ambiguo"]
```

Se o helper existente do arquivo não aceitar `desc`, estender o helper local (parâmetro opcional `desc=None` usando a sigla como default — mesmo padrão da Task 5).

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dc_pairer.py -q`
Expected: FAIL (órfão hoje sai Write; catch-all casa por similaridade)

- [ ] **Step 3: Write the implementation**

Em `src/tdt/dc_pairer.py`:

1. Import: `from tdt.semantica_estados import compatibilidade_texto`.

2. Em `parear`, no topo:

```python
    siglas_write = (
        config.siglas_write_legitimo if config is not None else frozenset({"CDC"})
    )
```

3. Substituir o ramo órfão:

```python
        elif not inputs:  # comando(s) sem status
            for o in outputs:
                if (o.sigla_sinal or "").upper() in siglas_write:
                    saida.append(o)  # Write legítimo (ex. CDC raise/lower)
                else:
                    revisao.append(ItemRevisao(o, motivo="comando_sem_discreto"))
```

4. Em `_parear_catchall`, dentro do loop duplo, antes de calcular `sim`:

```python
            if not compatibilidade_texto(
                o.descricoes.normalizada, i.descricoes.normalizada
            ):
                continue
```

5. Caso 1×1 (`len(inputs) == 1 and len(outputs) == 1`): também respeitar o gate —
substituir por:

```python
        elif len(inputs) == 1 and len(outputs) == 1 and compatibilidade_texto(
            outputs[0].descricoes.normalizada, inputs[0].descricoes.normalizada
        ):
            saida.append(fundir(inputs[0], outputs[0]))
        else:  # N×M ou 1×1 incompatível: desempata por similaridade (catch-all)
```

- [ ] **Step 4: Run tests + full suite**

Run: `python -m pytest tests/test_dc_pairer.py -q` → PASS
Run: `python -m pytest tests/ -q` → PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/dc_pairer.py tests/test_dc_pairer.py
git commit -m "feat(spE): comando orfao -> revisao (exceto write legitimo) + gate semantico no pareamento D+C"
```

---

### Task 8: Diagnóstico estrutural + validação E2E GTD + benchmark

**Files:**
- Create: `scripts/diag_estrutura_gtd.py`
- Test: validação manual E2E (metas da spec §4) + suite + benchmark

**Interfaces:**
- Consumes: TDT gerado e TDT real (xlsx); nenhuma API interna nova.

- [ ] **Step 1: Write the diagnostic script**

Criar `scripts/diag_estrutura_gtd.py`:

```python
"""Diagnóstico estrutural SP-E: TDT gerado × TDT real (DNP3_DiscreteSignals).

Uso: PYTHONPATH=src python scripts/diag_estrutura_gtd.py GERADO.xlsx REAL.xlsx

Metas (spec 2026-07-01-semantica-estados-multicoord §4):
- 0 double-bit falso (DoubleBit no gerado onde o real tem 2 sinais)
- MultiCoord nos pares de posição (real GTD: 44)
- 0 Write não-legitimado (real GTD: 2, só CDC)
- 0 Signal Name duplicado
"""
import sys
from collections import Counter, defaultdict

import openpyxl


def carregar(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["DNP3_DiscreteSignals"]
    rows = ws.iter_rows(values_only=True)
    next(rows); next(rows)
    fields = [str(c) if c is not None else "" for c in next(rows)]
    next(rows)
    idx = {f: i for i, f in enumerate(fields)}

    def col(parte):
        return next((i for f, i in idx.items() if parte in f), None)

    c = {"name": col("IDOBJ_NAME"), "dt": col("DINPUTDNP3_DATATYPE"),
         "dir": col("SIGNAL_DIRECTION"), "inc": col("INCOORDS")}
    sinais = []
    for row in rows:
        if c["name"] is None or not row[c["name"]]:
            continue
        sinais.append({k: (str(row[i]) if i is not None and row[i] is not None else "")
                       for k, i in c.items()})
    return sinais


def main():
    gen = carregar(sys.argv[1])
    real = carregar(sys.argv[2])

    dt_gen = Counter(s["dt"] for s in gen)
    dt_real = Counter(s["dt"] for s in real)
    dir_gen = Counter(s["dir"] for s in gen)
    dir_real = Counter(s["dir"] for s in real)
    print(f"gerado: {len(gen)} sinais | datatypes={dict(dt_gen)} | dir={dict(dir_gen)}")
    print(f"real:   {len(real)} sinais | datatypes={dict(dt_real)} | dir={dict(dir_real)}")

    # falsos double/multi: 2º endereço do gerado existe como sinal próprio no real
    por_addr = defaultdict(list)
    for s in real:
        if s["inc"]:
            por_addr[s["inc"].split(";")[0].strip()].append(s["name"])
    falsos = []
    for s in gen:
        partes = [p.strip() for p in s["inc"].split(";") if p.strip()]
        if s["dt"] in ("DoubleBit", "MultiCoord") and len(partes) == 2:
            a, b = partes
            real_a_par = [n for n in por_addr.get(a, [])
                          if any(r["name"] == n and r["dt"] in ("DoubleBit", "MultiCoord")
                                 for r in real)]
            if por_addr.get(b) and not real_a_par:
                falsos.append((s["name"], s["inc"], por_addr[a], por_addr[b]))
    print(f"\nfusões falsas (real tem 2 sinais separados): {len(falsos)}")
    for nome, inc, ra, rb in falsos[:20]:
        print(f"  {nome} inc={inc} | real@a={ra} | real@b={rb}")

    dups = [n for n, c in Counter(s["name"] for s in gen).items() if c > 1]
    print(f"\nSignal Names duplicados no gerado: {len(dups)}")
    for n in dups[:20]:
        print(f"  {n}")

    writes = [s["name"] for s in gen if s["dir"] == "Write"]
    print(f"\nWrite no gerado: {len(writes)}")
    for n in writes[:20]:
        print(f"  {n}")

    tem_sgft = any(n.endswith("_SGFT") for n in (s["name"] for s in gen))
    print(f"\nSGFT presente no gerado: {tem_sgft}")

    ok = not falsos and not dups and tem_sgft
    print(f"\n{'PASS' if ok else 'FAIL'} (metas spec SP-E §4)")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Regerar o TDT da GTD**

```powershell
$env:PYTHONPATH="src"
python -m tdt.cli gerar "docs/input_nao_homogeneo_1_GTD.xlsx" --output "output/LISTA 1 - GTD/TDT_spE.xlsx" --lista-padrao "docs/Pontos Padrao ADMS_v6.xlsx" --template "docs/dnp3_template.xlsx" --subestacao GTD
```

Expected: termina com `TDT: ... decididos=... revisão=...` sem exceção. (Primeira execução baixa/carrega o sentence-transformer — pode demorar minutos.)

- [ ] **Step 3: Rodar o diagnóstico**

```powershell
python scripts/diag_estrutura_gtd.py "output/LISTA 1 - GTD/TDT_spE.xlsx" "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx"
```

Expected (metas):
- `fusões falsas: 0` (era 39)
- `MultiCoord` > 0 no gerado (real: 44; o gerado só atinge 44 nos vãos cobertos pelo matching)
- `Write` ≈ 0 fora de `siglas_write_legitimo` (era 73)
- `SGFT presente no gerado: True`
- `Signal Names duplicados: 0`
- Veredito `PASS`

Se `FAIL`: investigar caso a caso ANTES de relaxar qualquer regra (systematic-debugging); os 20 exemplos impressos dão o ponto de partida.

- [ ] **Step 4: Suite + benchmark de regressão**

```powershell
python -m pytest tests/ -q
$env:PYTHONPATH="src"
python bench/benchmark.py
```

Expected: suite PASS; no log do benchmark (`bench/resultados/benchmark.log`), o método combo calib-minmax com decididos ≥ 82%, acc@1 ≥ 69%, prec@dec ≥ 80% (valores pós-SP-D2 — sem regressão).

- [ ] **Step 5: Commit**

```bash
git add scripts/diag_estrutura_gtd.py
git commit -m "feat(spE): diag_estrutura_gtd — gate estrutural gerado x real (metas spec §4)"
```

---

## Self-Review (executada na escrita)

- **Cobertura da spec:** D1→Task 1; D2→Task 6; D3→Task 5; D4→Tasks 3+4; D5→Task 7; D6→Task 6; regra Comando D/S→Tasks 3+4; Indefinido/43LR→Task 5; LIBM→Task 6; CDC Write→Task 7; validação §4→Task 8. Sem gap.
- **Placeholders:** o teste de engine (Task 4 Step 1) delega o setup ao padrão já existente em `tests/test_engine_tdt.py` — intencional (o arquivo tem helper de template próprio; copiá-lo aqui dessincronizaria). Todo o resto tem código completo.
- **Consistência de tipos:** `datatype`/`comando_duplo` (Task 3) usados por Tasks 4/5/8; `filtrar_por_estado` (Task 1) usado por Task 6; `compatibilidade_texto` (Task 1) por Task 7; `corrigir(registros, whitelist_posicao)` (Task 5) casada com as chamadas do pipeline.
