# SP-DEVICE-MAPPING-RGE Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Whitelist de IDs de equipamento (mata o falso-positivo 81-x), varredura da linha inteira com colisão → revisão, registro de equipamentos por módulo (preenche ID inequívoco) e Device Mapping padrão RGE (não-proteção cai no equipamento; analógicos em TC/TP/disjuntor).

**Spec:** `docs/superpowers/specs/2026-07-15-sp-device-mapping-rge-design.md`

**Architecture:** Mudanças em 4 estágios do pipeline, cada uma no módulo dono: reconhecimento no N0 (`normalizador.py`), varredura por linha no `estruturador.py`, registro por módulo em `inferencia_topologia.py` (wired no `pipeline.py`), regras de Device Mapping no `engine_tdt.py` (único choke point, vale pros dois caminhos homogêneo/heterogêneo).

**Tech Stack:** Python 3.12, pytest, openpyxl. Sem dependência nova.

## Global Constraints

- **Remote Point Custom ID / `nome_hierarquico` NÃO mudam** — só a coluna Device Mapping (gates `particionar_custom_id_duplicado`/`particionar_endereco_duplicado` intactos).
- DiscreteAnalog (`_valores_discrete_analog`, TAP/COMTAP): **inalterado**.
- Conservação: nenhum sinal some — colisão vira revisão (`status="revisao"`), nunca descarte.
- `gate_tdt_real` ≥ baseline (medir ANTES da primeira mudança, Task 1 Step 0).
- Contratos imutáveis: enriquecer `SignalRecord`/`Eletrico` com `dataclasses.replace`, sem mutação.
- TDD: teste falhando antes de cada implementação. Commits pequenos.
- Simplificação deliberada = comentário `# ponytail:` com teto e upgrade path.
- Suite: `python -m pytest -q tests/` (rodar da raiz do repo).

---

### Task 1: Whitelist de ID de equipamento no N0 (`normalizador.py`)

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py:55-69` (vocabulários) e `:133-172` (`extrair_contexto_estrutural`)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Produces: `_ID_EQUIPAMENTO` restrito a `(52|24|29|89)-N`; `_ID_TRANSFORMADOR` (novo, `TR{n}`); `familia_do_id(nome: str | None) -> str | None` (público — Tasks 3 e 5 importam); `_EQUIPAMENTO_ANSI` com `"24": "Disjuntor"`.
- `extrair_contexto_estrutural` passa a reconhecer `TR{n}` como equipamento (alvo `"Transformador"`, ID removido do texto remanescente, mesmo tratamento do `N-N`).

- [ ] **Step 0: Medir baseline do gate**

Run: `PYTHONPATH=src python bench/gate_tdt_real.py`
Anotar o número final (baseline de referência para a Task 6). Se o script pedir argumentos, ver o topo do arquivo — mesma invocação dos SPs anteriores.

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_normalizador.py` (importar `familia_do_id` junto dos imports existentes de `tdt.normalizacao.normalizador`):

```python
def test_81_nao_e_equipamento():
    # spec 2026-07-15: 81-1 é estágio de subfrequência, não equipamento.
    base, ctx = extrair_contexto_estrutural("SUBFREQUENCIA 81-1 ATUADO")
    assert ctx.nome_equipamento is None
    assert ctx.equipamento_alvo is None
    assert "81-1" in base  # fica no texto: discrimina estágio no matching


def test_24_e_disjuntor():
    _, ctx = extrair_contexto_estrutural("DISJUNTOR 24-1 FECHADO")
    assert ctx.equipamento_alvo == "Disjuntor"
    assert ctx.nome_equipamento == "24-1"


def test_tr_e_transformador():
    base, ctx = extrair_contexto_estrutural("TEMPERATURA OLEO TR1")
    assert ctx.equipamento_alvo == "Transformador"
    assert ctx.nome_equipamento == "TR1"
    assert "TR1" not in base  # ID removido do remanescente, como o N-N


def test_tr_nao_casa_dentro_de_sigla():
    # "86TR1" não tem boundary antes do TR — não pode virar equipamento TR1
    _, ctx = extrair_contexto_estrutural("BLOQUEIO 86TR1 ATUADO")
    assert ctx.nome_equipamento is None


def test_familia_do_id():
    assert familia_do_id("52-11") == "Disjuntor"
    assert familia_do_id("24-1") == "Disjuntor"
    assert familia_do_id("89-2") == "Seccionadora"
    assert familia_do_id("29-1") == "Seccionadora"
    assert familia_do_id("TR2") == "Transformador"
    assert familia_do_id("81-1") is None
    assert familia_do_id(None) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_normalizador.py -k "81_nao or 24_e or tr_ or familia" -v`
Expected: FAIL (`ImportError: familia_do_id` e asserts de 81-1/TR).

- [ ] **Step 3: Implementar**

Em `src/tdt/normalizacao/normalizador.py`, substituir o bloco das linhas 55-69 por:

```python
# N0 — extração estrutural (texto bruto, antes do colapso de separadores).
# Whitelist RGE (spec 2026-07-15): só 52/24/29/89 são IDs N-N de equipamento;
# qualquer outro N-N (ex. 81-1 = estágio de subfrequência) fica no texto.
_EQUIPAMENTO_ANSI: dict[str, str] = {
    "52": "Disjuntor",
    "24": "Disjuntor",     # convenção RGE (decisão do usuário 15/07)
    "89": "Seccionadora",
    "29": "Seccionadora",  # seccionadora de aterramento
}
_ID_EQUIPAMENTO = re.compile(r"\b(52|24|29|89)-(\d+)\b")
_ID_TRANSFORMADOR = re.compile(r"\bTR(\d+)\b")
# Equipamento pela PALAVRA (whole-token), quando nenhum ID da whitelist
# aparece. "SEC" sozinho é ambíguo (SECUNDARIO) e fica de fora de propósito.
_EQUIPAMENTO_PALAVRA: dict[str, str] = {
    "DISJUNTOR": "Disjuntor", "DISJ": "Disjuntor", "DJ": "Disjuntor",
    "SECCIONADORA": "Seccionadora", "SECCION": "Seccionadora", "SECC": "Seccionadora",
}


def familia_do_id(nome: str | None) -> str | None:
    """Família de equipamento a partir do ID: "52-11"→Disjuntor, "TR1"→
    Transformador, fora da whitelist→None. Consumido por
    inferencia_topologia (registro por módulo) e engine_tdt (DM analógico)."""
    if not nome:
        return None
    if _ID_TRANSFORMADOR.fullmatch(nome):
        return "Transformador"
    return _EQUIPAMENTO_ANSI.get(nome.split("-", 1)[0])
```

Em `extrair_contexto_estrutural`, logo APÓS o bloco do `_ID_EQUIPAMENTO` (linhas 143-148) e ANTES do fallback por palavra (`if equipamento_alvo is None:` da linha 150), inserir:

```python
    if nome_equipamento is None:
        m_tr = _ID_TRANSFORMADOR.search(base)
        if m_tr:
            equipamento_alvo = "Transformador"
            nome_equipamento = m_tr.group(0)
            base = (base[: m_tr.start()] + " " + base[m_tr.end():]).strip()
            base = " ".join(base.split())
```

- [ ] **Step 4: Rodar a suite inteira**

Run: `python -m pytest -q tests/`
Expected: novos testes PASS. Se algum teste existente falhar por assumir `N-N` genérico virando equipamento (fora da whitelist), esse teste codifica o bug — atualizar o teste citando a spec no comentário. Falha por outro motivo = investigar antes de tocar.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/normalizador.py tests/test_normalizador.py
git commit -m "feat(normalizador): whitelist de ID de equipamento (52/24/29/89, TRn)"
```

---

### Task 2: Varredura da linha inteira + colisão → revisão (`estruturador.py`)

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py` (helper novo `equipamentos_no_texto`)
- Modify: `src/tdt/normalizacao/estruturador.py:196-215` (fim do loop de `estruturar`)
- Modify: `src/tdt/ui/modelo_tabela.py:36,60` (label + tooltip do motivo novo)
- Test: `tests/test_estruturador.py`

**Interfaces:**
- Consumes: `_ID_EQUIPAMENTO`, `_ID_TRANSFORMADOR`, `_EQUIPAMENTO_ANSI` (Task 1).
- Produces: `equipamentos_no_texto(texto: str) -> list[tuple[str | None, str]]` (público em `normalizador.py`); motivo de revisão `"equipamento_conflitante"` (string usada por pipeline/UI).

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_estruturador.py`:

```python
def test_equipamento_vem_de_outra_coluna_da_linha():
    # spec 2026-07-15: busca de equipamento varre a linha inteira, não só a
    # descrição (AL11 tem coluna própria de equipamento).
    rows = [
        ("Equipamento", "Descrição", "Endereço"),
        ("52-11", "MOLA CARREGADA", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config())
    assert recs[0].eletrico.nome_equipamento == "52-11"
    assert recs[0].eletrico.equipamento_alvo == "Disjuntor"
    assert recs[0].status != "revisao"


def test_dois_equipamentos_distintos_na_linha_vao_pra_revisao():
    rows = [
        ("Equipamento", "Descrição", "Endereço"),
        ("89-1", "DISJUNTOR 52-11 FECHADO", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config())
    assert recs[0].status == "revisao"
    assert recs[0].justificativa == "equipamento_conflitante"


def test_mesmo_equipamento_repetido_na_linha_nao_conflita():
    rows = [
        ("Equipamento", "Descrição", "Endereço"),
        ("52-11", "DISJUNTOR 52-11 FECHADO", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config())
    assert recs[0].status != "revisao"
    assert recs[0].eletrico.nome_equipamento == "52-11"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_estruturador.py -k "linha" -v`
Expected: FAIL — `nome_equipamento` None no 1º teste, status não-revisao no 2º.

- [ ] **Step 3: Implementar**

(a) Em `src/tdt/normalizacao/normalizador.py`, adicionar após `familia_do_id`:

```python
def equipamentos_no_texto(texto: str) -> list[tuple[str | None, str]]:
    """Todos os IDs de equipamento no texto: [(família, id), ...]. Usado pela
    varredura de linha inteira do estruturador (spec 2026-07-15)."""
    if not texto:
        return []
    base = _sem_acentos(str(texto)).upper()
    achados = [
        (_EQUIPAMENTO_ANSI.get(m.group(1)), f"{m.group(1)}-{m.group(2)}")
        for m in _ID_EQUIPAMENTO.finditer(base)
    ]
    achados += [("Transformador", m.group(0)) for m in _ID_TRANSFORMADOR.finditer(base)]
    return achados
```

(b) Em `src/tdt/normalizacao/estruturador.py`: incluir `equipamentos_no_texto` no import de `.normalizador` (linha 25) e, dentro de `estruturar`, logo APÓS o bloco de resolução de módulo/sigla (após a linha `# ---------------...` ~198) e ANTES do `registros.append(...)`, inserir:

```python
        # --- varredura da linha inteira por ID de equipamento (spec 15/07):
        # a descrição já foi parseada pelo N0; as demais células só
        # contribuem identidade de equipamento. Módulo (c_modulo) fica de
        # fora: é identidade de módulo, não de equipamento.
        ids_linha: dict[str, str | None] = {}
        if eletrico.nome_equipamento:
            ids_linha[eletrico.nome_equipamento] = eletrico.equipamento_alvo
        for c, cel in enumerate(row):
            if c == c_desc or c == c_modulo or cel is None:
                continue
            for alvo, nome_eq in equipamentos_no_texto(str(cel)):
                ids_linha.setdefault(nome_eq, alvo)
        if len(ids_linha) > 1 and status != "revisao":
            # 2 equipamentos distintos na mesma linha -> operador decide
            status = "revisao"
            motivo_revisao = "equipamento_conflitante"
        elif len(ids_linha) == 1 and eletrico.nome_equipamento is None:
            nome_eq, alvo = next(iter(ids_linha.items()))
            eletrico = replace(
                eletrico, nome_equipamento=nome_eq,
                # ponytail: alvo do ID só preenche quando N0 não achou nada
                # pela palavra; divergência palavra×ID não é colisão (spec
                # define colisão = 2 IDs), o ID ganha o nome e o alvo textual
                # fica. Upgrade: tratar divergência como conflito se aparecer
                # em dado real.
                equipamento_alvo=eletrico.equipamento_alvo or alvo,
            )
```

(c) Em `src/tdt/ui/modelo_tabela.py`, adicionar nos dois dicts de motivo (procurar `"custom_id_duplicado"`, linhas ~36 e ~60):

```python
    "equipamento_conflitante": "Equipamentos conflitantes na linha",
```

```python
    "equipamento_conflitante": "A linha de origem cita dois equipamentos distintos (ex. 52-11 e 89-1). Confirme a qual equipamento o sinal pertence e ajuste.",
```

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest -q tests/test_estruturador.py tests/test_normalizador.py`
Expected: PASS. Depois a suite inteira: `python -m pytest -q tests/` — o roteamento do motivo já existe no pipeline (`rec.status == "revisao"` → `ItemRevisao(rec, motivo=rec.justificativa...)`, `pipeline.py:679`), não precisa de mudança lá.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/normalizador.py src/tdt/normalizacao/estruturador.py src/tdt/ui/modelo_tabela.py tests/test_estruturador.py
git commit -m "feat(estruturador): equipamento na linha inteira; colisao -> equipamento_conflitante"
```

---

### Task 3: Registro de equipamentos por módulo (`inferencia_topologia.py` + wiring)

**Files:**
- Modify: `src/tdt/inferencia_topologia.py` (função nova)
- Modify: `src/tdt/pipeline.py:41-43` (import) e `:652` (wiring pós-`inferir_equipamento`)
- Test: `tests/test_inferencia_topologia.py`

**Interfaces:**
- Consumes: `familia_do_id` (Task 1).
- Produces: `atribuir_id_por_registro(registros: list[SignalRecord]) -> tuple[list[SignalRecord], list[str]]` — 2ª posição são avisos (strings) pro canal `aud.evento(..., "AVISO")`.

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_inferencia_topologia.py` (completar imports existentes com `Eletrico`, `Descricoes`, `Enderecamento`, `TipoSinal`, `Modulo`, `SignalRecord` de `tdt.contracts` e `atribuir_id_por_registro` de `tdt.inferencia_topologia`, se ainda não presentes):

```python
def _rec_reg(rid, modulo, alvo=None, nome_eq=None):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("X", "X"),
        eletrico=Eletrico(equipamento_alvo=alvo, nome_equipamento=nome_eq),
    )


def test_registro_atribui_id_unico_da_familia():
    # AL11 tem 1 disjuntor (52-11); sinal de disjuntor sem ID ganha o ID.
    recs = [
        _rec_reg("s:1", "AL11", alvo="Disjuntor", nome_eq="52-11"),
        _rec_reg("s:2", "AL11", alvo="Disjuntor"),
    ]
    saida, avisos = atribuir_id_por_registro(recs)
    assert saida[1].eletrico.nome_equipamento == "52-11"
    assert avisos == []


def test_registro_dois_disjuntores_avisa_e_nao_atribui():
    recs = [
        _rec_reg("s:1", "AL11", alvo="Disjuntor", nome_eq="52-11"),
        _rec_reg("s:2", "AL11", alvo="Disjuntor", nome_eq="52-12"),
        _rec_reg("s:3", "AL11", alvo="Disjuntor"),
    ]
    saida, avisos = atribuir_id_por_registro(recs)
    assert saida[2].eletrico.nome_equipamento is None
    assert len(avisos) == 1
    assert "AL11" in avisos[0] and "52-11" in avisos[0] and "52-12" in avisos[0]


def test_registro_nao_sobrescreve_id_existente():
    recs = [
        _rec_reg("s:1", "AL11", alvo="Seccionadora", nome_eq="89-1"),
        _rec_reg("s:2", "AL11", alvo="Seccionadora", nome_eq="89-2"),
    ]
    saida, avisos = atribuir_id_por_registro(recs)
    assert saida[0].eletrico.nome_equipamento == "89-1"
    assert saida[1].eletrico.nome_equipamento == "89-2"
    assert avisos == []  # ninguém precisou de atribuição -> sem aviso


def test_registro_familia_sem_ocorrencia_fica_sem_id():
    recs = [_rec_reg("s:1", "AL11", alvo="Transformador")]
    saida, avisos = atribuir_id_por_registro(recs)
    assert saida[0].eletrico.nome_equipamento is None
    assert avisos == []


def test_registro_modulos_nao_se_misturam():
    recs = [
        _rec_reg("s:1", "AL11", alvo="Disjuntor", nome_eq="52-11"),
        _rec_reg("s:2", "AL12", alvo="Disjuntor"),
    ]
    saida, _ = atribuir_id_por_registro(recs)
    assert saida[1].eletrico.nome_equipamento is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_inferencia_topologia.py -k registro -v`
Expected: FAIL com `ImportError: atribuir_id_por_registro`.

- [ ] **Step 3: Implementar**

Em `src/tdt/inferencia_topologia.py`, adicionar import (`from tdt.normalizacao.normalizador import _EQUIPAMENTO_PALAVRA, familia_do_id` — a linha 29 já importa `_EQUIPAMENTO_PALAVRA`) e a função:

```python
def atribuir_id_por_registro(
    registros: list[SignalRecord],
) -> tuple[list[SignalRecord], list[str]]:
    """Preenche ``eletrico.nome_equipamento`` a partir dos equipamentos REAIS
    achados na sheet (spec 2026-07-15): por módulo, se existe exatamente 1
    equipamento da família do sinal, atribui o ID. 2+ da mesma família ->
    aviso (1 por módulo+família) e o ID fica vazio (o fallback do device
    mapping em engine_tdt resolve). Nunca inventa ID — só reusa o que outra
    linha do mesmo módulo declarou. Complementa ``inferir_equipamento`` (C2),
    que preenche só a FAMÍLIA; roda depois dele no pipeline.
    """
    registro: dict[str | None, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for rec in registros:
        ne = rec.eletrico.nome_equipamento
        fam = familia_do_id(ne)
        if ne and fam:
            registro[rec.modulo.nome][fam].add(ne)

    avisos: list[str] = []
    avisados: set[tuple[str | None, str]] = set()
    saida = list(registros)
    for i, rec in enumerate(saida):
        fam = rec.eletrico.equipamento_alvo
        if fam is None or rec.eletrico.nome_equipamento is not None:
            continue
        ids = registro[rec.modulo.nome].get(fam, set())
        if len(ids) == 1:
            (unico,) = ids
            saida[i] = replace(
                rec, eletrico=replace(rec.eletrico, nome_equipamento=unico),
            )
        elif len(ids) > 1 and (rec.modulo.nome, fam) not in avisados:
            avisados.add((rec.modulo.nome, fam))
            avisos.append(
                f"módulo {rec.modulo.nome}: {len(ids)} equipamentos da família "
                f"{fam} na sheet ({', '.join(sorted(ids))}) — ID não atribuído "
                f"aos sinais sem equipamento explícito"
            )
    return saida, avisos
```

Em `src/tdt/pipeline.py`: adicionar `atribuir_id_por_registro` ao import das linhas 41-43 e, logo após `sinais = inferir_equipamento(sinais, config)` (linha 652):

```python
        sinais, avisos_reg = atribuir_id_por_registro(sinais)
        for msg in avisos_reg:
            aud.evento("registro_equipamentos", msg, "AVISO")
```

(O registro é por sheet — mesmo escopo do loop; módulo vive dentro da sheet, e módulo repetido entre sheets já é anomalia coberta pelo gate `modulo_duplicado_entre_sheets`.)

- [ ] **Step 4: Rodar os testes**

Run: `python -m pytest -q tests/test_inferencia_topologia.py` e depois `python -m pytest -q tests/`
Expected: PASS. Atenção a testes de pipeline que contem eventos de auditoria — o evento novo `registro_equipamentos` pode alterar contagens; ajustar só contagens, nunca silenciar o evento.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/inferencia_topologia.py src/tdt/pipeline.py tests/test_inferencia_topologia.py
git commit -m "feat(inferencia): registro de equipamentos por modulo preenche ID inequivoco"
```

---

### Task 4: Device Mapping discreto padrão RGE (`engine_tdt.py`)

**Files:**
- Modify: `src/tdt/engine_tdt.py:96-102` (`_device_mapping`)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: nada novo.
- Produces: `_device_mapping(nome, sigla, eh_protecao)` — mesma assinatura, comportamento novo p/ `eh_protecao=False` (Tasks nenhuma dependem; `_valores` já chama).

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_engine_tdt.py` (o import de `_device_mapping` já existe na linha 25):

```python
def test_device_mapping_protecao_mantem_prot():
    assert _device_mapping("LVA_AL11_52-11_CAFL", "CAFL", True) == "LVA_AL11_52-11_PROT_CAFL"


def test_device_mapping_nao_protecao_cai_no_equipamento():
    # spec 2026-07-15: não-proteção cai direto no equipamento, sem sigla.
    assert _device_mapping("LVA_AL11_52-11_CAFL", "CAFL", False) == "LVA_AL11_52-11"


def test_device_mapping_nao_protecao_seccionadora():
    assert _device_mapping("LVA_AL11_89-1_SECC", "SECC", False) == "LVA_AL11_89-1"


def test_device_mapping_nao_protecao_sem_equipamento_cai_no_modulo():
    # nome_hierarquico repete o módulo quando não há equipamento
    assert _device_mapping("LVA_AL11_AL11_MOLA", "MOLA", False) == "LVA_AL11_AL11"


def test_device_mapping_nome_igual_sigla_nao_quebra():
    assert _device_mapping("CAFL", "CAFL", False) == "CAFL"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_engine_tdt.py -k device_mapping -v`
Expected: FAIL nos casos `nao_protecao` (hoje devolvem o nome inteiro com sigla).

- [ ] **Step 3: Implementar**

Substituir `_device_mapping` (engine_tdt.py:96-102) por:

```python
def _device_mapping(nome: str, sigla: str, eh_protecao: bool) -> str:
    """Padrão RGE (spec 2026-07-15): proteção mantém o sufixo PROT_<SIGLA>;
    não-proteção cai direto no equipamento — o nome hierárquico SEM a sigla
    final (sem equipamento o nome já repete o módulo, então o fallback
    módulo-duplicado emerge sozinho)."""
    if eh_protecao:
        # insere PROT_ antes da sigla final (nome termina em "..._{sigla}" ou == sigla)
        if nome.endswith(sigla):
            return nome[: len(nome) - len(sigla)] + f"PROT_{sigla}"
        return nome
    if nome.endswith(f"_{sigla}"):
        return nome[: len(nome) - len(sigla) - 1]
    return nome
```

- [ ] **Step 4: Rodar a suite**

Run: `python -m pytest -q tests/`
Expected: novos testes PASS. Testes existentes que asserem Device Mapping antigo de não-proteção (nome completo com sigla) codificam o comportamento pré-RGE — atualizar o valor esperado citando a spec. `Remote Point Custom ID`/`Signal Name`/`Remote Point Name` NÃO podem ter mudado em nenhum teste.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine_tdt): DM discreto nao-protecao cai direto no equipamento (RGE)"
```

---

### Task 5: Device Mapping analógico TC/TP/disjuntor (`engine_tdt.py`)

**Files:**
- Modify: `src/tdt/engine_tdt.py` (`_valores_analog:252-283`, `gerar:401-433`, helpers novos)
- Test: `tests/test_engine_tdt.py`

**Interfaces:**
- Consumes: `familia_do_id` (Task 1; adicionar ao import de `tdt.normalizacao.normalizador` que já traz `FASES`).
- Produces: `_device_mapping_analog(subestacao, modulo_nome, tipo_medicao_pt, disjuntor) -> str`; `_disjuntor_por_modulo(registros) -> dict[str | None, str | None]`; `_valores_analog(..., disjuntor: str | None = None)` (parâmetro novo, default retrocompat).

- [ ] **Step 1: Escrever os testes falhando**

Adicionar em `tests/test_engine_tdt.py` (importar `_device_mapping_analog`, `_disjuntor_por_modulo` e `Eletrico` de `tdt.contracts`):

```python
def test_dm_analog_corrente_e_potencias_caem_no_tc():
    assert _device_mapping_analog("LVA", "AL 11", "Corrente", "52-11") == "LVA_AL11_AL11_TC"
    assert _device_mapping_analog("LVA", "AL11", "Potência Ativa", None) == "LVA_AL11_AL11_TC"
    assert _device_mapping_analog("LVA", "AL11", "POTÊNCIA REATIVA", None) == "LVA_AL11_AL11_TC"
    assert _device_mapping_analog("LVA", "AL11", "Potência Aparente", None) == "LVA_AL11_AL11_TC"


def test_dm_analog_tensao_cai_no_tp():
    assert _device_mapping_analog("LVA", "AL11", "Tensão", "52-11") == "LVA_AL11_AL11_TP"


def test_dm_analog_resto_cai_no_disjuntor():
    # KMDF (Comprimento), frequência, FP, temperatura... -> disjuntor do módulo
    assert _device_mapping_analog("LVA", "AL11", "Comprimento", "52-11") == "LVA_AL11_52-11"
    assert _device_mapping_analog("LVA", "AL11", "Frequência", "52-11") == "LVA_AL11_52-11"
    assert _device_mapping_analog("LVA", "AL11", None, "52-11") == "LVA_AL11_52-11"


def test_dm_analog_sem_disjuntor_cai_no_modulo_duplicado():
    assert _device_mapping_analog("LVA", "AL11", "Comprimento", None) == "LVA_AL11_AL11"


def _rec_eq(rid, modulo, nome_eq):
    return replace(
        _rec(rid, "DJ", [1]),
        modulo=Modulo(modulo, "sheet_name"),
        eletrico=Eletrico(nome_equipamento=nome_eq),
    )


def test_disjuntor_por_modulo():
    regs = [
        _rec_eq("a:1", "AL11", "52-11"),
        _rec_eq("a:2", "AL11", "89-1"),   # seccionadora não conta
        _rec_eq("a:3", "AL12", "52-12"),
        _rec_eq("a:4", "AL12", "24-1"),   # 2 disjuntores -> ambíguo
        _rec_eq("a:5", "AL13", None),
    ]
    disj = _disjuntor_por_modulo(regs)
    assert disj["AL11"] == "52-11"
    assert disj["AL12"] is None
    assert disj.get("AL13") is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest -q tests/test_engine_tdt.py -k "dm_analog or disjuntor_por" -v`
Expected: FAIL com `ImportError`.

- [ ] **Step 3: Implementar**

Em `src/tdt/engine_tdt.py`, adicionar `familia_do_id` ao import existente de `tdt.normalizacao.normalizador` (o que traz `FASES`). Antes de `_valores_analog`, adicionar:

```python
# Grandeza (Measurement Type PT da lista padrão) -> entidade do device
# mapping analógico, padrão RGE (spec 2026-07-15).
_MEDIDAS_TC = frozenset({"CORRENTE", "POTÊNCIA ATIVA", "POTÊNCIA REATIVA", "POTÊNCIA APARENTE"})
_MEDIDAS_TP = frozenset({"TENSÃO"})


def _disjuntor_por_modulo(registros) -> "dict[str | None, str | None]":
    """Disjuntor único de cada módulo, p/ o DM analógico. 0 ou 2+ disjuntores
    -> None (fallback módulo-duplicado; o aviso de ambiguidade já foi emitido
    por atribuir_id_por_registro no pipeline)."""
    por_mod: dict[str | None, set[str]] = defaultdict(set)
    for rec in registros:
        ne = rec.eletrico.nome_equipamento
        if ne and familia_do_id(ne) == "Disjuntor":
            por_mod[rec.modulo.nome].add(ne)
    return {m: next(iter(ids)) if len(ids) == 1 else None for m, ids in por_mod.items()}


def _device_mapping_analog(
    subestacao: str | None,
    modulo_nome: str | None,
    tipo_medicao_pt: str | None,
    disjuntor: str | None,
) -> str:
    """Padrão RGE: corrente/potências -> <MOD>_TC; tensão -> <MOD>_TP;
    demais grandezas (KMDF, frequência, FP, temperatura...) -> disjuntor do
    módulo; sem disjuntor único -> módulo duplicado (<SUB>_<MOD>_<MOD>)."""
    modulo_fmt = modulo_nome.replace(" ", "") if modulo_nome else None
    partes = [p for p in (subestacao, modulo_fmt) if p]
    t = (tipo_medicao_pt or "").strip().upper()
    if t in _MEDIDAS_TC:
        alvo = f"{modulo_fmt}_TC" if modulo_fmt else "TC"
    elif t in _MEDIDAS_TP:
        alvo = f"{modulo_fmt}_TP" if modulo_fmt else "TP"
    else:
        alvo = disjuntor or modulo_fmt
    if alvo:
        partes.append(alvo)
    return "_".join(partes)
```

Em `_valores_analog`: adicionar parâmetro `disjuntor: "str | None" = None` ao fim da assinatura; remover a linha `eh_prot = bool(sp and sp.signal_type == "RelayTrip")` (só o DM usava); trocar a linha do Device Mapping por:

```python
        "Device Mapping": _device_mapping_analog(
            subestacao, rec.modulo.nome, sp.tipo_medicao if sp else None, disjuntor),
```

Em `gerar()`: antes dos `_escrever_sheet`, computar `disj = _disjuntor_por_modulo(lista.registros)` e trocar a lambda dos analógicos por:

```python
        lambda rec, sub, padrao: _valores_analog(
            rec, sub, padrao, alias_v1, disj.get(rec.modulo.nome)),
```

- [ ] **Step 4: Rodar a suite**

Run: `python -m pytest -q tests/`
Expected: PASS. Testes de analógico existentes que asserem o DM antigo (com sigla) — atualizar valor esperado citando a spec. Colunas analógicas restantes (Measurement Type, Display Unit, Custom ID) intocadas.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/engine_tdt.py tests/test_engine_tdt.py
git commit -m "feat(engine_tdt): DM analogico TC/TP/disjuntor padrao RGE"
```

---

### Task 6: Gate, conservação e closeout DOX

**Files:**
- Modify: `docs/AGENTS.md` (ledger), `src/tdt/AGENTS.md` (fluxo/papéis), `docs/superpowers/specs/2026-07-15-sp-device-mapping-rge-design.md` (status)

- [ ] **Step 1: Gate**

Run: `PYTHONPATH=src python bench/gate_tdt_real.py`
Expected: resultado ≥ baseline do Task 1 Step 0. Regressão → parar, diagnosticar (provável interação da whitelist com extração antiga), não seguir pro closeout com gate abaixo do baseline.

- [ ] **Step 2: Suite completa + import**

Run: `python -m pytest -q tests/` e `PYTHONPATH=src python -c "import tdt.pipeline"`
Expected: tudo PASS.

- [ ] **Step 3: DOX pass**

- `docs/AGENTS.md`: linha nova na lista de specs + linhas no ledger:
  - Whitelist equipamento `(52|24|29|89)-N` + `TR{n}`, 24=Disjuntor — implementado
  - Varredura linha inteira + motivo `equipamento_conflitante` — implementado
  - Registro por módulo (`atribuir_id_por_registro`) preenche ID inequívoco; 2+ → aviso — implementado
  - DM RGE: não-proteção sem sigla; analógico TC/TP/disjuntor; fallback módulo duplicado — implementado
- `src/tdt/AGENTS.md`: atualizar a descrição do fluxo (linha 14: inserir `atribuir_id_por_registro` após `inferir_equipamento`... a menção está na seção de pipeline) e a linha do `engine_tdt` (DM RGE).
- Spec: marcar como **implementado** no cabeçalho.

- [ ] **Step 4: Commit final**

```bash
git add docs/AGENTS.md src/tdt/AGENTS.md docs/superpowers/specs/2026-07-15-sp-device-mapping-rge-design.md
git commit -m "docs: closeout SP-DEVICE-MAPPING-RGE (ledger + DOX + status spec)"
```
