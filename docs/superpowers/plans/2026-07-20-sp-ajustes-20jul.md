# SP-AJUSTES-20JUL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar a spec [2026-07-20-sp-ajustes-dm-catalogo-revisao-design.md](../specs/2026-07-20-sp-ajustes-dm-catalogo-revisao-design.md): device mapping com sufixo de família e disjuntor no PROT de alimentador, flag `dm_prot` por sigla, avisos 43LR/43TC, gate de tipo duplicado, MultiCoord para pares de índices, colunas novas na revisão e fix do falso-positivo de endereço duplicado.

**Architecture:** Toda a derivação de Signal Name/Device Mapping converge numa função pública única `dm_registro()` em `engine_tdt.py`, consumida por `_valores`, pelo novo gate `particionar_tipo_duplicado` e pela UI (colunas derivadas). Regras de catálogo (complemento `dm_prot`) viram constante em `defaults.py` gerada por script auditável em `scripts/`. UI espelha o engine (mesma chave de duplicidade), nunca reimplementa.

**Tech Stack:** Python 3.14, openpyxl, PySide6, pytest.

## Global Constraints

- Branch: `feature/sp-ajustes-20jul` (CLAUDE.md — Implementação de features).
- Não-regressão (CLAUDE.md regra universal 2026-07-16): funcionalidade existente não pode ser desligada; diffs de DM/datatype são INTENCIONAIS e documentados no commit.
- Decisão registrada 20/07 (usuário, aprovada em spec) SUPERSEDE a correção 16/07 "proteção sempre módulo-duplicado" — somente para módulos alimentador com disjuntor único.
- `Remote Point Custom ID` deriva do `Signal Name` (não do DM) — nenhuma task pode alterá-lo.
- Testes determinísticos, sem I/O de rede; fixtures inline (padrão `_rec`/`_lista` de `tests/test_engine_tdt.py`).
- Commits pequenos, mensagem Conventional Commits, subject ≤50 chars.
- Fullbase de referência: `docs/Export_base_Full__27_fev_2026.xlsx` (não commitar cópias).
- Rodar sempre: `python -m pytest tests/<arquivo> -q` na task; suíte completa + `python -m bench.regressao` só na Task 10.

---

### Task 1: Sufixo de família no Device Mapping (spec §A1)

**Files:**
- Modify: `src/tdt/engine_tdt.py:97-117` (`_device_mapping`), `src/tdt/engine_tdt.py:174-225` (`_valores`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `familia_do_id(nome)` de `tdt.normalizacao.normalizador` (já importado no engine; retorna `"Disjuntor" | "Seccionadora" | "Transformador" | None`).
- Produces (usados pelas Tasks 2, 4, 6, 9):
  - `_SUFIXO_FAMILIA: dict[str, str]`
  - `_dm_prot(sigla: str | None, sp) -> bool` (nesta task: só RelayTrip; Task 4 adiciona complemento)
  - `_device_mapping(nome, sigla, dm_prot, subestacao=None, modulo_nome=None, barra=None, equipamento=None, disjuntor=None) -> str`
  - `dm_registro(rec, subestacao, sp, disjuntor=None) -> tuple[str, str]` — (Signal Name, Device Mapping)

- [ ] **Step 0: Criar branch**

```bash
git checkout -b feature/sp-ajustes-20jul
```

- [ ] **Step 1: Escrever testes que falham**

Adicionar em `tests/test_engine_tdt.py`, junto dos testes existentes de device mapping (~linha 408; reusar o helper `_rec` do próprio arquivo, adicionando equipamento via `replace` no campo `eletrico` conforme o padrão dos testes vizinhos):

```python
def test_dm_equipamento_disjuntor_ganha_sufixo_dj():
    # nao-protecao caindo em equipamento 52-1 -> sufixo _DJ (spec 20/07 §A1)
    dm = engine_tdt._device_mapping(
        "IMA_AL11_52-1_DJF1", "DJF1", False,
        subestacao="IMA", modulo_nome="AL11", equipamento="52-1",
    )
    assert dm == "IMA_AL11_52-1_DJ"


def test_dm_equipamento_seccionadora_ganha_sufixo_sec():
    dm = engine_tdt._device_mapping(
        "IMA_AL11_89-4_SECF", "SECF", False,
        subestacao="IMA", modulo_nome="AL11", equipamento="89-4",
    )
    assert dm == "IMA_AL11_89-4_SEC"


def test_dm_equipamento_transformador_ganha_sufixo_tr():
    dm = engine_tdt._device_mapping(
        "IMA_TR1_TR1_86", "86", False,
        subestacao="IMA", modulo_nome="TR1", equipamento="TR1",
    )
    assert dm == "IMA_TR1_TR1_TR"


def test_dm_equipamento_fora_da_whitelist_sem_sufixo():
    # familia_do_id devolve None p/ "RT1" -> comportamento atual preservado
    dm = engine_tdt._device_mapping(
        "IMA_SE_RT1_CAFL", "CAFL", False,
        subestacao="IMA", modulo_nome="SE", equipamento="RT1",
    )
    assert dm == "IMA_SE_RT1"


def test_dm_sem_equipamento_fallback_modulo_duplicado_sem_sufixo():
    dm = engine_tdt._device_mapping(
        "IMA_AL11_AL11_DJF1", "DJF1", False,
        subestacao="IMA", modulo_nome="AL11", equipamento=None,
    )
    assert dm == "IMA_AL11_AL11"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_engine_tdt.py -q -k "sufixo or fallback_modulo_duplicado_sem"`
Expected: FAIL (`TypeError: unexpected keyword argument 'equipamento'`)

- [ ] **Step 3: Implementar**

Em `src/tdt/engine_tdt.py`, acima de `_device_mapping`:

```python
# Sufixo de família do equipamento no Device Mapping (spec 2026-07-20 §A1;
# fullbase: DJ 16.866, TR 4.610, SEC 2.157 como último segmento). TC/TP da
# spec saem no ramo analógico (`<MOD>_TC`/`<MOD>_TP`) — familia_do_id não
# classifica TC/TP por ID; estender aqui se a whitelist ganhar esses IDs.
_SUFIXO_FAMILIA: dict[str, str] = {
    "Disjuntor": "DJ",
    "Seccionadora": "SEC",
    "Transformador": "TR",
}


def _dm_prot(sigla: str | None, sp) -> bool:
    """Flag do ramo PROT do device mapping (spec 2026-07-20 §B1)."""
    return bool(sp and sp.signal_type == "RelayTrip")
```

Substituir `_device_mapping` (a assinatura ganha `equipamento`/`disjuntor`; `disjuntor` só é usado na Task 2):

```python
def _device_mapping(
    nome: str,
    sigla: str,
    dm_prot: bool,
    subestacao: str | None = None,
    modulo_nome: str | None = None,
    barra: str | None = None,
    equipamento: str | None = None,
    disjuntor: str | None = None,
) -> str:
    """Padrão RGE (spec 2026-07-20): proteção cai no módulo duplicado;
    não-proteção cai no equipamento com sufixo de família (_DJ/_SEC/_TR).
    Sem equipamento, o fallback módulo-duplicado emerge sozinho (sem sufixo).
    Base terminando em sufixo de barra fica sem sufixo de família
    (conservador — fullbase não tem exemplo com barra + sufixo)."""
    if dm_prot:
        return nome_hierarquico(subestacao, modulo_nome, None, barra, f"PROT_{sigla}")
    base = nome[: len(nome) - len(sigla) - 1] if nome.endswith(f"_{sigla}") else nome
    suf = _SUFIXO_FAMILIA.get(familia_do_id(equipamento) or "")
    if suf and equipamento and base.endswith(equipamento):
        return f"{base}_{suf}"
    return base
```

Adicionar `dm_registro` logo abaixo, e usar em `_valores` (remove as linhas `nome = nome_hierarquico(...)`, `eh_prot = ...` e o valor de `"Device Mapping"`/`"Signal Name"` passa a vir daqui):

```python
def dm_registro(rec, subestacao, sp, disjuntor: str | None = None) -> tuple[str, str]:
    """(Signal Name, Device Mapping) do registro — derivação ÚNICA, usada por
    _valores, particionar_tipo_duplicado e pelas colunas derivadas da UI."""
    sigla = rec.sigla_sinal or "?"
    nome = nome_hierarquico(
        subestacao, rec.modulo.nome, rec.eletrico.nome_equipamento,
        rec.eletrico.barra, sigla,
    )
    dm = _device_mapping(
        nome, sigla, _dm_prot(rec.sigla_sinal, sp), subestacao,
        rec.modulo.nome, rec.eletrico.barra,
        equipamento=rec.eletrico.nome_equipamento, disjuntor=disjuntor,
    )
    return nome, dm
```

Em `_valores` (assinatura ganha `disjuntor: str | None = None` no fim):

```python
def _valores(rec, subestacao, padrao, alias_v1=None, disjuntor=None) -> dict:
    sp = padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
    nome, dm = dm_registro(rec, subestacao, sp, disjuntor)
    ...
    # no dict: "Signal Name": nome  /  "Device Mapping": dm
```

`particionar_custom_id_duplicado` continua com `nome_hierarquico` direto (Custom ID não muda — Global Constraints).

- [ ] **Step 4: Rodar test_engine_tdt inteiro e corrigir asserts antigos**

Run: `python -m pytest tests/test_engine_tdt.py -q`
Expected: os 5 novos PASSAM; testes antigos de DM não-proteção com equipamento 52-x/89-x/TRn FALHAM com o sufixo novo — atualizar cada assert com comentário `# sufixo de família (spec 20/07 §A1)`. Nenhuma outra falha.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine): sufixo de familia no device mapping (A1)"
```

---

### Task 2: Disjuntor no ramo PROT de alimentador (spec §A2)

**Files:**
- Modify: `src/tdt/engine_tdt.py` (`_device_mapping` ramo prot, `_disjuntor_por_modulo` → público, `gerar`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `_eh_alimentador(modulo_nome)` (engine_tdt.py:80), `dm_registro`/`_device_mapping` da Task 1.
- Produces: `disjuntor_por_modulo(registros) -> dict[str | None, str | None]` (rename público de `_disjuntor_por_modulo`; usado pela Task 6 e pela UI na Task 9). Ramo prot com `disjuntor` em alimentador.

- [ ] **Step 1: Testes que falham**

```python
def test_dm_prot_alimentador_usa_disjuntor():
    # decisao 20/07 (supersede correcao 16/07): AL com disjuntor unico ->
    # 2o modulo vira o disjuntor, SEM sufixo (fullbase CNC_AL11_52-22_PROT_51F)
    dm = engine_tdt._device_mapping(
        "CVA_AL11_52-1_CAFL", "CAFL", True,
        subestacao="CVA", modulo_nome="AL11", disjuntor="52-1",
    )
    assert dm == "CVA_AL11_52-1_PROT_CAFL"


def test_dm_prot_alimentador_sem_disjuntor_fallback_modulo():
    dm = engine_tdt._device_mapping(
        "CVA_AL11_AL11_CAFL", "CAFL", True,
        subestacao="CVA", modulo_nome="AL11", disjuntor=None,
    )
    assert dm == "CVA_AL11_AL11_PROT_CAFL"


def test_dm_prot_nao_alimentador_ignora_disjuntor():
    dm = engine_tdt._device_mapping(
        "CVA_TR1BT_TR1BT_CAFL", "CAFL", True,
        subestacao="CVA", modulo_nome="TR1BT", disjuntor="52-7",
    )
    assert dm == "CVA_TR1BT_TR1BT_PROT_CAFL"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_engine_tdt.py -q -k "dm_prot_alimentador or dm_prot_nao"`
Expected: FAIL no primeiro (`CVA_AL11_AL11_PROT_CAFL != CVA_AL11_52-1_PROT_CAFL`)

- [ ] **Step 3: Implementar**

No ramo prot de `_device_mapping`:

```python
    if dm_prot:
        if _eh_alimentador(modulo_nome) and disjuntor:
            # decisão 20/07 (supersede 16/07): alimentador usa o DISJUNTOR do
            # módulo (não o equipamento da linha) como 2º nível do PROT
            return nome_hierarquico(subestacao, modulo_nome, disjuntor, barra, f"PROT_{sigla}")
        return nome_hierarquico(subestacao, modulo_nome, None, barra, f"PROT_{sigla}")
```

Renomear `_disjuntor_por_modulo` → `disjuntor_por_modulo` (engine_tdt.py:276; atualizar o caller em `gerar` e usos em testes). Em `gerar`, passar o disjuntor também ao caminho discreto:

```python
    disj = disjuntor_por_modulo(lista.registros)
    _escrever_sheet(
        wb[SHEET_DISCRETOS], SHEET_DISCRETOS, COLUNAS_ESPERADAS,
        regs_disc,
        lambda rec, sub, padrao: _valores(
            rec, sub, padrao, alias_v1, disj.get(rec.modulo.nome)),
        lista.subestacao, lista_padrao,
    )
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_engine_tdt.py -q`
Expected: PASS (se algum teste antigo assertar PROT módulo-duplicado em AL com disjuntor no fixture, atualizar com comentário `# decisão 20/07`)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine): disjuntor no ramo PROT de alimentador (A2)"
```

---

### Task 3: Sufixo `_DJ` no device mapping analógico (spec §A3)

**Files:**
- Modify: `src/tdt/engine_tdt.py:288-308` (`_device_mapping_analog`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `_device_mapping_analog(subestacao, modulo_nome, tipo_medicao_pt, disjuntor)` existente.
- Produces: mesmo contrato; ramo `disjuntor` emite `<disjuntor>_DJ`.

- [ ] **Step 1: Teste que falha**

```python
def test_dm_analog_disjuntor_ganha_sufixo_dj():
    # fullbase analog: ultimo segmento DJ 4.570x (spec 20/07 §A3)
    dm = engine_tdt._device_mapping_analog("CVA", "AL11", "FREQUÊNCIA", "52-1")
    assert dm == "CVA_AL11_52-1_DJ"


def test_dm_analog_corrente_continua_mod_tc():
    dm = engine_tdt._device_mapping_analog("CVA", "AL11", "CORRENTE", "52-1")
    assert dm == "CVA_AL11_AL11_TC"


def test_dm_analog_sem_disjuntor_fallback_modulo():
    dm = engine_tdt._device_mapping_analog("CVA", "AL11", "FREQUÊNCIA", None)
    assert dm == "CVA_AL11_AL11"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_engine_tdt.py -q -k dm_analog`
Expected: FAIL no primeiro (`CVA_AL11_52-1 != CVA_AL11_52-1_DJ`)

- [ ] **Step 3: Implementar**

Em `_device_mapping_analog`, trocar o `else` final:

```python
    else:
        alvo = f"{disjuntor}_DJ" if disjuntor else modulo_fmt
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_engine_tdt.py -q`
Expected: PASS (atualizar asserts antigos do ramo disjuntor analógico com `# sufixo _DJ (spec 20/07 §A3)`)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine): sufixo _DJ no DM analogico (A3)"
```

---

### Task 4: Complemento `dm_prot` por sigla (spec §B1)

**Files:**
- Create: `scripts/derivar_complemento_dm_prot.py`
- Modify: `src/tdt/defaults.py`, `src/tdt/engine_tdt.py` (`_dm_prot`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `_dm_prot(sigla, sp)` da Task 1; `docs/Export_base_Full__27_fev_2026.xlsx`; `docs/Pontos Padrao ADMS_v8.xlsx`.
- Produces: `COMPLEMENTO_DM_PROT: frozenset[str]` em `tdt.defaults` (consumida por `_dm_prot`).

- [ ] **Step 1: Criar o script**

`scripts/derivar_complemento_dm_prot.py` (completo):

```python
"""Deriva COMPLEMENTO_DM_PROT (spec 2026-07-20 §B1): siglas da lista padrão
com SIGNAL TYPE != RelayTrip que a fullbase mapeia consistentemente em
dispositivo PROT. Critério: nomes estilo-SE, linhas limpas (prefixo SE do
sinal == prefixo SE do DM), >=90% PROT, n>=20. Rodar e colar a saída em
tdt/defaults.py quando a lista padrão ou a fullbase mudarem."""
import re
from collections import defaultdict
from pathlib import Path

from openpyxl import load_workbook

DOCS = Path(__file__).resolve().parents[1] / "docs"
FULLBASE = DOCS / "Export_base_Full__27_fev_2026.xlsx"
LISTA = DOCS / "Pontos Padrao ADMS_v8.xlsx"
RE_SE = re.compile(r"^([A-Z]{2,5})_")

# siglas nao-RelayTrip da lista padrao
wb = load_workbook(LISTA, read_only=True, data_only=True)
ws = wb["DiscreteSignals"]
rows = ws.iter_rows(values_only=True)
hdr = [str(h).strip() if h else "" for h in next(rows)]
i_s, i_st = hdr.index("SINAL"), hdr.index("SIGNAL TYPE")
nao_relaytrip = {
    str(r[i_s]).strip().upper()
    for r in rows
    if r[i_s] is not None and str(r[i_st] or "").strip() != "RelayTrip"
}

# %PROT por sigla na fullbase (linhas limpas)
wb = load_workbook(FULLBASE, read_only=True, data_only=True)
ws = wb["DNP3_DiscreteSignals"]
hdr = [str(h).strip() if h else "" for h in
       next(ws.iter_rows(min_row=4, max_row=4, values_only=True))]
i_sn, i_dm = hdr.index("Signal Name"), hdr.index("Device Mapping")
stats: dict[str, list[int]] = defaultdict(lambda: [0, 0])  # sigla -> [tot, prot]
for row in ws.iter_rows(min_row=5, values_only=True):
    sn = row[i_sn]
    if sn is None:
        continue
    sn, dm = str(sn), str(row[i_dm] or "").strip()
    m_sn, m_dm = RE_SE.match(sn), RE_SE.match(dm)
    if not m_sn or not m_dm or m_sn.group(1) != m_dm.group(1):
        continue  # religador numerico ou linha suja (SE trocada)
    sigla = sn.rsplit("_", 1)[-1].upper()
    stats[sigla][0] += 1
    if "PROT" in dm.upper():
        stats[sigla][1] += 1

aprovadas = sorted(
    s for s, (tot, prot) in stats.items()
    if s in nao_relaytrip and tot >= 20 and prot / tot >= 0.90
)
for s in aprovadas:
    tot, prot = stats[s]
    print(f"# {s}: {prot}/{tot} PROT ({100 * prot / tot:.0f}%)")
print("COMPLEMENTO_DM_PROT = frozenset({")
print("    " + ", ".join(f'"{s}"' for s in aprovadas))
print("})")
```

- [ ] **Step 2: Rodar o script e revisar a saída**

Run: `python scripts/derivar_complemento_dm_prot.py`
Expected: lista contendo `2649` (decisão do usuário 20/07 — dado limpo → PROT) e provável `27`, `59`, `61`. Se `2649` NÃO sair (dado limpo abaixo do critério), adicioná-lo à mão com comentário `# decisão do usuário 20/07`. Se sair sigla claramente não-proteção (conferir contra a spec §Diagnóstico item 3 — família 79, 43*, 86, 63*, 71*, 81U* NÃO podem entrar), investigar antes de seguir.

- [ ] **Step 3: Colar a constante em `src/tdt/defaults.py`**

Ao final do arquivo:

```python
# Complemento do flag dm_prot (spec 2026-07-20 §B1): siglas da lista padrão
# com SIGNAL TYPE != RelayTrip que a fullbase mapeia >=90% em dispositivo
# PROT (linhas limpas, n>=20). Saída de scripts/derivar_complemento_dm_prot.py
# — regenerar se a lista padrão ou a fullbase mudarem. RelayTrip da lista
# padrão continua mandando (instrução do usuário: não mexer no documentado).
COMPLEMENTO_DM_PROT = frozenset({
    # <colar a saída do script aqui, com o comentário de % por sigla>
})
```

- [ ] **Step 4: Testes que falham**

```python
def test_dm_prot_complemento_2649():
    # 2649 e Enabled na lista padrao mas mapeia PROT (decisao 20/07)
    sp = SinalPadrao(sigla="2649", descricao="X", signal_type="Enabled",
                     direction=None, mm=None, categoria="Discrete")
    assert engine_tdt._dm_prot("2649", sp) is True


def test_dm_prot_79_fica_fora():
    sp = SinalPadrao(sigla="79", descricao="X", signal_type="ReclosingEnabled",
                     direction=None, mm=None, categoria="Discrete")
    assert engine_tdt._dm_prot("79", sp) is False


def test_dm_prot_relaytrip_preservado():
    sp = SinalPadrao(sigla="TRIP", descricao="X", signal_type="RelayTrip",
                     direction=None, mm=None, categoria="Discrete")
    assert engine_tdt._dm_prot("TRIP", sp) is True
```

Run: `python -m pytest tests/test_engine_tdt.py -q -k dm_prot_`
Expected: FAIL em `test_dm_prot_complemento_2649` (complemento ainda não consultado)

- [ ] **Step 5: Implementar**

Em `engine_tdt.py` (import no topo: `from tdt.defaults import COMPLEMENTO_DM_PROT`):

```python
def _dm_prot(sigla: str | None, sp) -> bool:
    """Flag do ramo PROT do device mapping (spec 2026-07-20 §B1): RelayTrip
    da lista padrão manda; o complemento cobre siglas não-RelayTrip que a
    fullbase mapeia consistentemente em PROT (ex. 2649). NÃO é o conceito
    ANSI de função de proteção (79 é função e mesmo assim cai no DJ)."""
    if sp is not None and sp.signal_type == "RelayTrip":
        return True
    return (sigla or "").strip().upper() in COMPLEMENTO_DM_PROT
```

- [ ] **Step 6: Rodar e ver passar**

Run: `python -m pytest tests/test_engine_tdt.py tests/test_ui_defaults.py -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add scripts/derivar_complemento_dm_prot.py src/tdt/defaults.py src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine): dm_prot por sigla com complemento da fullbase (B1)"
```

---

### Task 5: Aviso 43LR sem 43TC (spec §B2)

**Files:**
- Modify: `src/tdt/engine_tdt.py`, `src/tdt/pipeline.py:544-570` (`gerar_tdt`), `src/tdt/ui/tela_geracao.py:166-189` (`_montar_avisos`)
- Test: `tests/test_engine_tdt.py`, `tests/test_ui_tela_geracao.py`

**Interfaces:**
- Consumes: `SignalRecord` (campos `sigla_sinal`, `modulo.nome`, `eletrico.nome_equipamento`).
- Produces: `dispositivos_43lr_sem_43tc(registros) -> tuple[str, ...]` em `engine_tdt` (labels `"MOD/EQUIP"`, ordenados).

- [ ] **Step 1: Testes que falham** (engine)

Helper `_rec_equip` (definir uma vez em `tests/test_engine_tdt.py`, junto do `_rec` existente; reusado nas Tasks 6 e 9 — se o arquivo já tiver helper equivalente com equipamento, reusar):

```python
def _rec_equip(rid, sigla, equipamento, modulo="AL11", indices=(10,), direcao="Input"):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(f"{sigla} BRUTO", sigla),
        sigla_sinal=sigla,
        status="decidido",
        eletrico=Eletrico(fase=None, equipamento_alvo=None,
                          nome_equipamento=equipamento, barra=None),
    )
```

(Conferir a ordem/nomes dos campos de `Eletrico` em `src/tdt/contracts.py` antes de usar — o teste `test_estruturador_homogeneo.py` constrói `Eletrico` com `fase/equipamento_alvo/nome_equipamento/barra`.)

```python
def test_43lr_sem_43tc_avisa():
    regs = (
        _rec_equip("AL11:1", "43LR", "52-1"),
    )
    assert engine_tdt.dispositivos_43lr_sem_43tc(regs) == ("AL11/52-1",)


def test_43lr_com_43tc_nao_avisa():
    regs = (
        _rec_equip("AL11:1", "43LR", "52-1"),
        _rec_equip("AL11:2", "43TC", "52-1"),
    )
    assert engine_tdt.dispositivos_43lr_sem_43tc(regs) == ()


def test_43tc_sozinho_nao_avisa():
    regs = (_rec_equip("AL11:1", "43TC", "52-1"),)
    assert engine_tdt.dispositivos_43lr_sem_43tc(regs) == ()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_engine_tdt.py -q -k 43lr`
Expected: FAIL (`AttributeError: dispositivos_43lr_sem_43tc`)

- [ ] **Step 3: Implementar no engine**

```python
def dispositivos_43lr_sem_43tc(registros) -> tuple[str, ...]:
    """Dispositivos (módulo, equipamento) com 43LR e sem 43TC — precisa haver
    um sinal Local (43TC) no dispositivo (spec 2026-07-20 §B2; catálogo v8:
    43LR=Custom, 43TC=Local)."""
    lr: set[tuple[str, str]] = set()
    tc: set[tuple[str, str]] = set()
    for rec in registros:
        sigla = (rec.sigla_sinal or "").strip().upper()
        if sigla not in ("43LR", "43TC"):
            continue
        chave = (rec.modulo.nome or "?", rec.eletrico.nome_equipamento or "?")
        (lr if sigla == "43LR" else tc).add(chave)
    return tuple(f"{m}/{e}" for m, e in sorted(lr - tc))
```

- [ ] **Step 4: Wiring pipeline + UI**

Em `pipeline.gerar_tdt`, após o bloco de `particionar_endereco_duplicado`:

```python
    sem_local = engine_tdt.dispositivos_43lr_sem_43tc(lista.registros)
    if sem_local:
        aud.evento(
            "engine",
            f"{len(sem_local)} dispositivos com 43LR sem 43TC (falta sinal Local)",
            "AVISO", dados={"dispositivos": sem_local},
        )
```

Em `tela_geracao.py` (import: `from tdt.engine_tdt import dispositivos_43lr_sem_43tc`), dentro de `_montar_avisos`, após o bloco `if dups:`:

```python
        sem_local = dispositivos_43lr_sem_43tc(regs)
        if sem_local:
            resumo = "; ".join(sem_local[:3])
            self._avisos_box.addWidget(self._aviso(
                "aviso",
                f"{len(sem_local)} dispositivos com 43LR sem 43TC "
                f"(falta sinal Local): {resumo}",
                None, None))
```

E a condição final vira `if not pendentes and not dups and not sem_local:`.

Teste UI em `tests/test_ui_tela_geracao.py` (seguir o padrão dos testes existentes do arquivo p/ montar registros e chamar `_montar_avisos`): registro 43LR sem 43TC → box contém aviso com "43LR sem 43TC".

- [ ] **Step 5: Rodar e ver passar**

Run: `python -m pytest tests/test_engine_tdt.py tests/test_ui_tela_geracao.py tests/test_pipeline_gerar_tdt.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/tdt/engine_tdt.py src/tdt/pipeline.py src/tdt/ui/tela_geracao.py tests/test_engine_tdt.py tests/test_ui_tela_geracao.py
git commit -m "feat(engine): aviso 43LR sem 43TC por dispositivo (B2)"
```

---

### Task 6: Gate `particionar_tipo_duplicado` (spec §B3)

**Files:**
- Modify: `src/tdt/engine_tdt.py`, `src/tdt/pipeline.py` (`gerar_tdt`), `src/tdt/ui/modelo_tabela.py:23-72` (`_MOTIVO_LABEL`/`_MOTIVO_TOOLTIP`)
- Test: `tests/test_engine_tdt.py`, `tests/test_pipeline_gerar_tdt.py`

**Interfaces:**
- Consumes: `dm_registro`, `_dm_prot`, `disjuntor_por_modulo` (Tasks 1-2-4); `ListaPadraoADMS.por_sigla`.
- Produces: `particionar_tipo_duplicado(lista: ListaHomogenea, lista_padrao) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]`; motivo `"tipo_duplicado_dispositivo"`.

**Refinamento da spec (palavras do usuário, 20/07):** sinais que caem DENTRO do dispositivo PROT ficam ISENTOS do gate — "se ele for cair dentro de um dispositivo de proteção, aí sim, você pode ter o repetido" (a fullbase tem 16 Enabled legítimos num mesmo PROT). O gate só cobre sinais diretos no equipamento.

- [ ] **Step 1: Testes que falham**

```python
def _lp_fake(siglas_tipos: dict[str, str]):
    class _LP:
        def por_sigla(self, sigla):
            st = siglas_tipos.get(sigla)
            if st is None:
                return None
            return SinalPadrao(sigla=sigla, descricao="X", signal_type=st,
                               direction=None, mm=None, categoria="Discrete")
    return _LP()


def test_tipo_duplicado_mesmo_dispositivo_vai_para_revisao():
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(
        _rec_equip("AL11:1", "43TC", "52-1"),   # Local
        _rec_equip("AL11:2", "43XY", "52-1"),   # Local tambem -> conflito
    ))
    lp = _lp_fake({"43TC": "Local", "43XY": "Local"})
    restante, revisao = engine_tdt.particionar_tipo_duplicado(lista, lp)
    assert len(restante.registros) == 0
    assert {it.motivo for it in revisao} == {"tipo_duplicado_dispositivo"}


def test_tipo_duplicado_custom_isento():
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(
        _rec_equip("AL11:1", "CAB1", "52-1"),
        _rec_equip("AL11:2", "CAB2", "52-1"),
    ))
    lp = _lp_fake({"CAB1": "Custom", "CAB2": "Custom"})
    restante, revisao = engine_tdt.particionar_tipo_duplicado(lista, lp)
    assert len(restante.registros) == 2 and revisao == ()


def test_tipo_duplicado_prot_isento():
    # dois RelayTrip no mesmo modulo: caem no PROT -> repetido e valido
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(
        _rec_equip("AL11:1", "51F", "52-1"),
        _rec_equip("AL11:2", "50F1", "52-1"),
    ))
    lp = _lp_fake({"51F": "RelayTrip", "50F1": "RelayTrip"})
    restante, revisao = engine_tdt.particionar_tipo_duplicado(lista, lp)
    assert len(restante.registros) == 2 and revisao == ()


def test_tipo_duplicado_dispositivos_distintos_isento():
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(
        _rec_equip("AL11:1", "43TC", "52-1"),
        _rec_equip("AL11:2", "43TC", "89-4"),   # outro equipamento
    ))
    lp = _lp_fake({"43TC": "Local"})
    restante, revisao = engine_tdt.particionar_tipo_duplicado(lista, lp)
    assert len(restante.registros) == 2 and revisao == ()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_engine_tdt.py -q -k tipo_duplicado`
Expected: FAIL (`AttributeError: particionar_tipo_duplicado`)

- [ ] **Step 3: Implementar**

Em `engine_tdt.py`, após `particionar_endereco_duplicado`:

```python
def particionar_tipo_duplicado(
    lista: ListaHomogenea,
    lista_padrao,
) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]:
    """Gate (spec 2026-07-20 §B3): dois sinais não-Custom com o MESMO Signal
    Type caindo DIRETO no mesmo dispositivo (DM final) conflitam no ADMS —
    o grupo inteiro sai do TDT e vai pra revisão (padrão custom_id: nunca
    sai calado no xlsx). Sinais do ramo PROT ficam de fora — dentro de
    proteção o repetido é válido (decisão do usuário 20/07)."""
    disj = disjuntor_por_modulo(lista.registros)
    grupos: dict[tuple[str, str], list[SignalRecord]] = defaultdict(list)
    for rec in lista.registros:
        sp = lista_padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
        st = (sp.signal_type if sp else "Custom") or "Custom"
        if st == "Custom" or _dm_prot(rec.sigla_sinal, sp):
            continue
        _, dm = dm_registro(rec, lista.subestacao, sp, disj.get(rec.modulo.nome))
        grupos[(dm, st)].append(rec)
    colididos = {r.id for regs in grupos.values() if len(regs) > 1 for r in regs}
    if not colididos:
        return lista, ()
    revisao = tuple(
        ItemRevisao(replace(r, status="revisao"), motivo="tipo_duplicado_dispositivo")
        for r in lista.registros if r.id in colididos
    )
    restantes = tuple(r for r in lista.registros if r.id not in colididos)
    return replace(lista, registros=restantes), revisao
```

Wiring em `pipeline.gerar_tdt`, após o bloco de endereço duplicado (o gate usa o DM FINAL — precisa das Tasks 1-3 já aplicadas):

```python
    lista, rev_tipo = engine_tdt.particionar_tipo_duplicado(lista, lp)
    if rev_tipo:
        aud.evento(
            "engine",
            f"{len(rev_tipo)} registros com Signal Type duplicado no dispositivo -> revisão",
            "AVISO", dados={"ids": tuple(it.registro.id for it in rev_tipo)},
        )
```

Em `modelo_tabela.py`:

```python
# _MOTIVO_LABEL
"tipo_duplicado_dispositivo": "Signal Type duplicado no dispositivo",
# _MOTIVO_TOOLTIP
"tipo_duplicado_dispositivo": "Dois sinais não-Custom com o mesmo Signal Type "
    "caindo direto no mesmo dispositivo — o ADMS conflita. Troque a sigla de "
    "um deles (ou o Signal Type no catálogo) e regenere.",
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_engine_tdt.py tests/test_pipeline_gerar_tdt.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py src/tdt/pipeline.py src/tdt/ui/modelo_tabela.py tests/test_engine_tdt.py tests/test_pipeline_gerar_tdt.py
git commit -m "feat(engine): gate Signal Type duplicado por dispositivo (B3)"
```

---

### Task 7: Par de índices → MultiCoord (spec §C)

**Files:**
- Modify: `src/tdt/normalizacao/estruturador.py:141-146`, `src/tdt/normalizacao/estruturador_homogeneo.py:114-118`
- Test: `tests/test_estruturador.py`, `tests/test_estruturador_homogeneo.py`

**Interfaces:**
- Consumes: `TipoSinal.datatype` (contracts.py:35).
- Produces: estruturadores emitem `"MultiCoord"` p/ 2 índices distintos; `"DoubleBit"` fica reservado (nenhuma origem o produz mais).

- [ ] **Step 1: Mapear consumidores de "DoubleBit" (pré-requisito de não-regressão)**

Run: `grep -rn "DoubleBit" src/ tests/`
Expected: ocorrências em `contracts.py` (domínio — fica), `estruturador.py`/`estruturador_homogeneo.py` (mudam), `engine_tdt.py:436` (comentário — trata índices individualmente, indiferente), testes. `normalizador_estrutural`, `dc_pairer` e `ui/estado.py` já operam com `MultiCoord` — nenhum ramo condicional em `"DoubleBit"` fora dos estruturadores. Se aparecer consumidor novo, PARAR e reavaliar.

- [ ] **Step 2: Atualizar testes (que passam hoje com DoubleBit) para MultiCoord**

Em `tests/test_estruturador_homogeneo.py` e `tests/test_estruturador.py`, trocar os asserts `datatype == "DoubleBit"` por `datatype == "MultiCoord"` com comentário:

```python
    # spec 20/07 §C: par de indices e MultiCoord (fullbase: DoubleBit nunca
    # tem ';' nas coordenadas; DoubleBit = ponto nativo de 1 endereco)
    assert decididos[0].tipo_sinal.datatype == "MultiCoord"
```

Run: `python -m pytest tests/test_estruturador.py tests/test_estruturador_homogeneo.py -q`
Expected: FAIL (código ainda emite DoubleBit)

- [ ] **Step 3: Implementar**

Nos DOIS estruturadores, o bloco vira:

```python
        # spec 2026-07-20 §C: dois índices = dois pontos = MultiCoord.
        # "DoubleBit" (ponto nativo de 1 endereço) fica reservado — nenhuma
        # lista de origem o marca hoje.
        datatype = (
            "MultiCoord"
            if len(indices) == 2 and indices[0] != indices[1]
            else "SingleBit"
        )
```

- [ ] **Step 4: Rodar suíte de conservação e ver passar**

Run: `python -m pytest tests/test_estruturador.py tests/test_estruturador_homogeneo.py tests/test_normalizador_estrutural.py tests/test_dc_pairer.py tests/test_conservacao_comandos.py tests/test_conservacao_identidade.py tests/test_fluxo_dados.py tests/test_engine_tdt.py -q`
Expected: PASS (se um teste de engine assertar `Input Data Type == "DoubleBit"`, atualizar p/ `"MultiCoord"` com o mesmo comentário)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/estruturador.py src/tdt/normalizacao/estruturador_homogeneo.py tests/
git commit -m "fix(estruturador): par de indices vira MultiCoord, nao DoubleBit (C)"
```

---

### Task 8: Fix falso-positivo do aviso de endereço duplicado (spec §D2)

**Files:**
- Modify: `src/tdt/ui/tela_geracao.py:24-36` (`enderecos_duplicados`), `src/tdt/ui/tela_geracao.py:166-189` (`_montar_avisos`)
- Test: `tests/test_ui_tela_geracao.py`

**Interfaces:**
- Consumes: `SignalRecord` (`modulo.nome`, `tipo_sinal.categoria`, `tipo_sinal.direcao`, `enderecamento`).
- Produces: `enderecos_duplicados(registros) -> dict[tuple[str, str, str, int], list[str]]` — chave `(espaco, modulo, categoria, indice)`.

**Raiz (confirmada por leitura, hipóteses da spec):** a versão da UI diverge do gate do engine em DOIS pontos — (1) não tem módulo na chave (índice local reusado entre módulos DISTINTOS é endereçamento normal, mas a UI avisa); (2) registro `direcao == "Output"` guarda o endereço de ESCRITA em `enderecamento.indices`, e a UI o joga no espaço "in", colidindo com Inputs reais de mesmo índice — exatamente a comparação input×output que o usuário suspeitou. O engine (`particionar_endereco_duplicado`, engine_tdt.py:438-446) já faz certo; a UI passa a espelhar a mesma chave.

- [ ] **Step 1: Testes-repro que falham**

Em `tests/test_ui_tela_geracao.py` — se o arquivo já tiver helper de registro, reusar; senão definir:

```python
def _rec_mod(rid, modulo, indices, direcao="Input", indices_saida=()):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices), tuple(indices_saida)),
        descricoes=Descricoes("BRUTO", "norm"),
        sigla_sinal="DJF1",
        status="decidido",
    )
```

```python
def test_mesmo_indice_em_modulos_distintos_nao_e_duplicata():
    regs = [
        _rec_mod("AL11:1", modulo="AL11", indices=(14,)),
        _rec_mod("AL12:1", modulo="AL12", indices=(14,)),
    ]
    assert enderecos_duplicados(regs) == {}


def test_indice_de_comando_nao_colide_com_input():
    regs = [
        _rec_mod("AL11:1", modulo="AL11", indices=(14,), direcao="Input"),
        _rec_mod("AL11:2", modulo="AL11", indices=(14,), direcao="Output"),
    ]
    assert enderecos_duplicados(regs) == {}


def test_mesmo_indice_mesmo_modulo_mesma_direcao_e_duplicata():
    regs = [
        _rec_mod("AL11:1", modulo="AL11", indices=(14,)),
        _rec_mod("AL11:2", modulo="AL11", indices=(14,)),
    ]
    dups = enderecos_duplicados(regs)
    assert list(dups.values()) == [["AL11:1", "AL11:2"]]
```

Run: `python -m pytest tests/test_ui_tela_geracao.py -q -k "indice or duplicata"`
Expected: os dois primeiros FALHAM (repro do falso-positivo)

- [ ] **Step 2: Implementar**

```python
def enderecos_duplicados(registros) -> dict[tuple[str, str, str, int], list[str]]:
    """(espaco, modulo, categoria, indice) -> ids que repetem o índice.

    Mesma chave do gate `engine_tdt.particionar_endereco_duplicado` (fix
    falso-positivo 20/07): módulo na chave (índice local reusado entre
    módulos distintos é endereçamento normal) e registro Output contribui
    seus `indices` no espaço "out" (é endereço de ESCRITA, não de leitura).
    """
    por_chave: dict[tuple[str, str, str, int], list[str]] = {}
    for r in registros:
        mod = (r.modulo.nome if r.modulo else None) or "?"
        cat = r.tipo_sinal.categoria
        espaco = "out" if r.tipo_sinal.direcao == "Output" else "in"
        for i in r.enderecamento.indices:
            por_chave.setdefault((espaco, mod, cat, i), []).append(r.id)
        for i in r.enderecamento.indices_saida:
            por_chave.setdefault(("out", mod, cat, i), []).append(r.id)
    return {k: v for k, v in por_chave.items() if len(v) > 1}
```

Em `_montar_avisos`, ajustar a extração de índices:

```python
        indices = sorted({i for (_esp, _mod, _cat, i) in dups})
```

- [ ] **Step 3: Rodar e ver passar**

Run: `python -m pytest tests/test_ui_tela_geracao.py -q`
Expected: PASS (atualizar testes antigos que asssertavam a chave `(dir, idx)` de 2 elementos)

- [ ] **Step 4: Commit**

```bash
git add src/tdt/ui/tela_geracao.py tests/test_ui_tela_geracao.py
git commit -m "fix(ui): aviso de endereco duplicado espelha chave do engine (D2)"
```

---

### Task 9: Colunas da tabela de revisão (spec §D1)

**Files:**
- Modify: `src/tdt/ui/modelo_tabela.py` (COLUNAS, `_EDITAVEIS`, `_COLUNAS_MONO`, `_texto`, `_valor_edicao`, `data`), `src/tdt/ui/tela_revisao.py:34-37` (`_COLUNAS_PADRAO`) e `:350` (`index("Sinal")`)
- Test: `tests/test_ui_modelo_tabela.py`, `tests/test_ui_tela_revisao.py`

**Interfaces:**
- Consumes: `dm_registro(rec, subestacao, sp, disjuntor)` e `disjuntor_por_modulo(registros)` de `tdt.engine_tdt` (Tasks 1-2); `AppState.subestacao` (ui/estado.py:23); `AppState.lista_padrao`.
- Produces: `COLUNAS` novo (26 nomes, abaixo); colunas derivadas read-only `Signal Name` / `Device Mapping` / `Signal Type`.

- [ ] **Step 1: Varredura de referências aos nomes antigos**

Run: `grep -rn "\"Sinal\"\|Descr\. ADMS\|\"Tokens\"\|Descr\. normalizada" src/tdt/ tests/`
Expected: `modelo_tabela.py` (15, 90, 96, 200, 216, 220, 222, 299, 329), `tela_revisao.py` (35-36, 350) e testes. TODAS entram no diff desta task — nenhuma referência ao nome antigo pode sobrar em `src/`.

- [ ] **Step 2: Testes que falham**

Em `tests/test_ui_modelo_tabela.py` — seguir o padrão de construção de modelo/estado do próprio arquivo; se não houver helper, definir (`_rec_equip` igual ao da Task 5):

```python
def _modelo_com(rec, subestacao=None):
    estado = AppState()          # conferir construção do AppState no arquivo
    estado.registros = [rec]
    estado.subestacao = subestacao
    return ModeloSinais(estado)
```

```python
def test_colunas_renomeadas_e_derivadas():
    assert "Sigla" in COLUNAS and "Sinal" not in COLUNAS
    assert "Descr. lista padrão" in COLUNAS and "Descr. ADMS" not in COLUNAS
    assert "Tokens" not in COLUNAS and "Descr. normalizada" not in COLUNAS
    for nova in ("Signal Name", "Device Mapping", "Signal Type"):
        assert nova in COLUNAS


def test_coluna_device_mapping_deriva_do_engine():
    # registro com equipamento disjuntor: DM termina _DJ (Task 1)
    modelo = _modelo_com(_rec_equip("AL11:1", "DJF1", "52-1"), subestacao="IMA")
    col = COLUNAS.index("Device Mapping")
    assert modelo._texto(modelo._estado.registros[0], col) == "IMA_AL11_52-1_DJ"


def test_coluna_signal_type_custom_sem_catalogo():
    modelo = _modelo_com(_rec_equip("AL11:1", "ZZZZ", "52-1"), subestacao="IMA")
    col = COLUNAS.index("Signal Type")
    assert modelo._texto(modelo._estado.registros[0], col) == "Custom"
```

Run: `python -m pytest tests/test_ui_modelo_tabela.py -q -k "renomeadas or deriva or signal_type"`
Expected: FAIL

- [ ] **Step 3: Implementar em `modelo_tabela.py`**

Imports: `from tdt.engine_tdt import dm_registro, disjuntor_por_modulo`.

```python
COLUNAS = [
    "Sigla", "Confiança", "Status", "Motivo",
    "Signal Name", "Device Mapping", "Signal Type",
    "Descr. lista padrão", "Descr. bruta",
    "Tipo", "Escala", "Fase", "Endereço Input", "Endereço Output",
    "Score embedding", "Score tf-idf", "Score fuzzy", "Justificativa",
    "Módulo", "Equipamento", "Tipo Equip.", "Barra", "Nível Tensão",
    "Pareado", "Sheet origem", "Severidade",
]

_EDITAVEIS = frozenset({
    "Sigla", "Tipo", "Fase", "Nível Tensão", "Barra", "Tipo Equip.",
    "Módulo", "Escala", "Endereço Input", "Endereço Output",
    "Equipamento", "Descr. bruta",
})

_COLUNAS_MONO = frozenset({
    "Sigla", "Signal Name", "Device Mapping", "Endereço Input",
    "Endereço Output", "Score embedding", "Score tf-idf", "Score fuzzy",
})
```

Helper + branches novos em `_texto` (remover os branches `"Descr. normalizada"` e `"Tokens"`; renomear `"Sinal"`→`"Sigla"` e `"Descr. ADMS"`→`"Descr. lista padrão"` nos branches e no tooltip de `data()`; em `_valor_edicao` idem):

```python
    def _sp(self, rec):
        lp = self._estado.lista_padrao
        if lp is None or not rec.sigla_sinal:
            return None
        return lp.por_sigla(rec.sigla_sinal)

    def _nome_dm(self, rec):
        # ponytail: disjuntor_por_modulo é O(n) por célula — mesmo teto do
        # motivo_por_id() acima; cachear no AppState se a tabela ficar lenta.
        disj = disjuntor_por_modulo(self._estado.registros)
        return dm_registro(
            rec, self._estado.subestacao, self._sp(rec),
            disj.get(rec.modulo.nome if rec.modulo else None),
        )
```

```python
        if nome == "Signal Name":
            return self._nome_dm(rec)[0]
        if nome == "Device Mapping":
            return self._nome_dm(rec)[1]
        if nome == "Signal Type":
            sp = self._sp(rec)
            return sp.signal_type if sp else "Custom"
```

(`_adms` pode reusar `_sp`.) As derivadas não entram em `_EDITAVEIS` — recalculam sozinhas porque o modelo relê o registro a cada `data()`.

Em `tela_revisao.py`:

```python
_COLUNAS_PADRAO = frozenset({
    "Sigla", "Confiança", "Status", "Motivo", "Descr. bruta",
    "Descr. lista padrão", "Signal Name", "Device Mapping", "Signal Type",
    "Módulo", "Endereço Input", "Pareado", "Sheet origem",
})
```

E na linha 350: `ModeloSinais.COLUNAS.index("Sigla")`.

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_ui_modelo_tabela.py tests/test_ui_tela_revisao.py tests/test_ui_proxy_revisao.py tests/test_ui_delegate_sinal.py tests/test_ui_estado.py tests/test_estado_lote.py -q`
Expected: PASS (testes que citem "Sinal"/"Descr. ADMS"/"Tokens" pelos nomes antigos são atualizados nesta task; visibilidade de coluna salva com nome antigo simplesmente não casa mais → coluna volta ao default, aceito)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/ui/modelo_tabela.py src/tdt/ui/tela_revisao.py tests/
git commit -m "feat(ui): colunas Signal Name/DM/Signal Type na revisao (D1)"
```

---

### Task 11: Signal Name usa disjuntor no PROT de alimentador (fix pós-Task 2, decisão 20/07 tarde)

**Origem:** usuário reportou, após Task 8, que apesar do Device Mapping de alimentador PROT já usar o disjuntor (Task 2), o Signal Name continuava `MODULO_MODULO` (fallback antigo, sem disjuntor).

**Conflito com Global Constraints (linha 16 deste plano):** "`Remote Point Custom ID` deriva do `Signal Name` — nenhuma task pode alterá-lo". Corrigir o Signal Name necessariamente muda o Custom ID desses registros.

**Investigação (fullbase real, `docs/Export_base_Full__27_fev_2026.xlsx`):** confirmado que a produção real usa o disjuntor tanto no Signal Name quanto no Device Mapping quanto no Remote Point Custom ID:
- Signal Name: `CNC_AL11_52-22_51F` (não `CNC_AL11_AL11_51F`)
- Device Mapping: `CNC_AL11_52-22_PROT_51F` (Task 2)
- Remote Point Custom ID: `CNCAL11522251F_UTR_CNC_DNP3_1` — deriva do Signal Name corrigido, não do antigo.

**Decisão do usuário (20/07, tarde):** corrigir Signal Name E Custom ID juntos (não desacoplar). `particionar_custom_id_duplicado` também precisa da mesma derivação disjuntor-aware para não validar unicidade contra um nome que diverge do que realmente sai no xlsx.

**Files:**
- Modify: `src/tdt/engine_tdt.py` (`dm_registro`, `particionar_custom_id_duplicado`), `src/tdt/pipeline.py` (2 call sites: `gerar_tdt`, `executar`)
- Test: `tests/test_engine_tdt.py`

**Escopo do fallback:** só quando `_dm_prot(sigla, sp)` é True E `_eh_alimentador(modulo_nome)` E disjuntor é conhecido E o registro não já tem `eletrico.nome_equipamento` explícito — mesma condição da Task 2, aplicada também ao Signal Name. PROT não-alimentador, alimentador sem disjuntor, e não-PROT ficam inalterados (mesmo comportamento de antes).

`particionar_custom_id_duplicado` ganha parâmetro opcional `lista_padrao=None` — quando `None` (compat retroativa, testes existentes), mantém o comportamento antigo (nome_hierarquico puro, sem disjuntor); quando informado (os 2 call sites de produção em `pipeline.py`), usa `dm_registro` para casar exatamente com o nome que `_valores`/`gerar` vão escrever.

- [ ] **Step 1: Commit**

```bash
git commit -m "fix(engine): signal name usa disjuntor no PROT alimentador"
```

---

### Task 10: Verificação de closeout (gate da spec)

**Files:**
- Modify: `docs/AGENTS.md` (ledger), `src/tdt/AGENTS.md` (tabela de papéis — funções públicas novas `dm_registro`, `disjuntor_por_modulo`, `particionar_tipo_duplicado`, `dispositivos_43lr_sem_43tc`)

- [ ] **Step 1: Suíte completa**

Run: `python -m pytest tests/ -q`
Expected: 0 failed

- [ ] **Step 2: Gate real**

Run: `python -m bench.regressao`
Expected: sem regressão NOVA vs baseline (casos_travados.csv com FAIL>0 é esperado — memória do projeto); diffs de Device Mapping (sufixos, PROT-AL) e Input Data Type (MultiCoord) são os ÚNICOS campos alterados. Comparar contra as listas reais suportadas (SAN2, CVA, LVA, GAU, GTD) e registrar no commit de closeout a contagem de DMs alterados por SE.

- [ ] **Step 3: Conferir invariante do Custom ID**

Run: `grep -n "nome_hierarquico" src/tdt/engine_tdt.py`
Expected: `particionar_custom_id_duplicado` segue usando `nome_hierarquico` puro (sem sufixo de família) — Custom IDs idênticos aos de antes.

- [ ] **Step 4: DOX pass + ledger**

Reler a cadeia `AGENTS.md` (raiz → docs → src/tdt) antes de editar (regra do projeto). Registrar SP-AJUSTES-20JUL no ledger (`docs/AGENTS.md`) com os 4 blocos e as decisões: 2649→PROT, 79 fica fora do dm_prot, PROT-AL supersede 16/07, gate B3 isenta ramo PROT. Atualizar a tabela de papéis (`src/tdt/AGENTS.md`) com as funções públicas novas.

- [ ] **Step 5: Commit de closeout**

```bash
git add docs/AGENTS.md src/tdt/AGENTS.md
git commit -m "docs(ledger): closeout SP-AJUSTES-20JUL"
```

- [ ] **Step 6: Finalizar branch**

Invocar a skill `superpowers:finishing-a-development-branch` para decidir merge/PR com o usuário.
