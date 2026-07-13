# Identificação de Módulo por Coluna (Gênero Sheet-por-Tipo) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar detecção e atribuição de módulo **por linha** no caminho não-homogêneo, para planilhas cujas sheets separam por tipo de ponto (ESTADOS/MEDIDAS/COMANDOS) e o módulo vive numa coluna dedicada.

**Architecture:** Método aditivo, gated. Uma nova detecção de coluna (`_col_modulo`, só ativa quando `config` é passado) marca a coluna; `estruturar` lê o módulo por linha sob nova origem `coluna:MODULO_POR_LINHA`; `aplicar_identidade` canoniza cada valor (reusando a lógica de `resolver_modulo`, extraída para `canonizar_modulo`) e classifica o tipo por grupo de módulo. A canonização determinística reconcilia nomes divergentes cross-sheet (`AL 11`/`AL11` → `AL11`) sem código extra.

**Tech Stack:** Python 3.14, openpyxl (leitura xlsx), pytest.

## Global Constraints

- **Nenhum comportamento existente muda.** Os caminhos homogêneo, `sheet_name` e `coluna:SIGLA` produzem saída byte-idêntica. Cada task termina com a suíte atual verde (`pytest -q`), 68 testes de baseline nos módulos tocados.
- **Tag nova obrigatória:** usar `origem_contexto="coluna:MODULO_POR_LINHA"` — NUNCA reusar `coluna:MODULO` (já é do caminho homogêneo, `identidade_homogenea.py`).
- **Sem alterar assinaturas de `aplicar_identidade`/`particionar_por_confianca`** (retorno `(sinais, str)`).
- Estilo: PEP8, nomes descritivos, funções puras onde possível. Docstrings/comentários em português como no resto do módulo.
- Commits pequenos por task.

---

## File Structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `src/tdt/identidade_modulo.py` | canonização de módulo (pura) + identidade por linha | Modificar |
| `src/tdt/analise/analise_colunas.py` | detecção de coluna de módulo por conteúdo | Modificar |
| `src/tdt/normalizacao/estruturador.py` | leitura de módulo por linha | Modificar |
| `src/tdt/pipeline.py` | wiring: passar `config` a `analisar` | Modificar (1 linha) |
| `tests/test_identidade_modulo.py` | testes de `canonizar_modulo` + identidade por linha | Modificar |
| `tests/test_analise_colunas.py` | testes de `_col_modulo` | Modificar |
| `tests/test_estruturador.py` | testes de estruturação por linha | Modificar |
| `tests/test_modulo_por_coluna_smf.py` | integração no arquivo SMF real | Criar |

---

## Task 1: Extrair `canonizar_modulo` (refactor puro, sem mudança de comportamento)

**Files:**
- Modify: `src/tdt/identidade_modulo.py:31-67`
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `Config.mapa_sheet_modulo`, `Config.mapa_prefixo_modulo`; `_tokens` (já existe).
- Produces: `canonizar_modulo(valor: str, config: Config, *, explicito: bool = False) -> ResolucaoModulo`. `resolver_modulo(sheet_name, rows, config)` passa a delegar a ela com `explicito=False`.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao fim de `tests/test_identidade_modulo.py`:

```python
from tdt.identidade_modulo import canonizar_modulo


def test_canonizar_explicito_prefixo_e_numero_com_sufixo_de_tensao():
    cfg = Config()
    assert canonizar_modulo("AL 11 - 13.8kV", cfg, explicito=True).nome == "AL11"
    assert canonizar_modulo("AL15 - 13.8kV (FUTURO)", cfg, explicito=True).nome == "AL15"
    assert canonizar_modulo("TR1", cfg, explicito=True).nome == "TR1"


def test_canonizar_explicito_sem_prefixo_usa_cru_limpo_alta():
    cfg = Config()
    r = canonizar_modulo("TIE-AT", cfg, explicito=True)
    assert r.nome == "TIE-AT"
    assert r.confianca == "alta"
    r2 = canonizar_modulo("LTSM3C1", cfg, explicito=True)
    assert r2.nome == "LTSM3C1"
    assert r2.confianca == "alta"


def test_canonizar_explicito_limpa_sufixo_futuro_sem_prefixo():
    cfg = Config()
    assert canonizar_modulo("TIE-AT (FUTURO)", cfg, explicito=True).nome == "TIE-AT"


def test_canonizar_nao_explicito_preserva_fallback_resolver_modulo():
    cfg = Config()
    r = canonizar_modulo("SLOT GERAL", cfg)  # explicito=False (default)
    assert r.nome == "SLOT GERAL"   # cru, SEM limpeza
    assert r.confianca == "baixa"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_identidade_modulo.py -q -k canonizar`
Expected: FAIL com `ImportError: cannot import name 'canonizar_modulo'`.

- [ ] **Step 3: Implementar `canonizar_modulo` e delegar `resolver_modulo`**

Em `src/tdt/identidade_modulo.py`, adicionar acima de `resolver_modulo` (após a definição de `_tokens`/`ResolucaoModulo`):

```python
_SUFIXO_RUIDO = re.compile(
    r"\s*-\s*\d+(?:[.,]\d+)?\s*KV\b|\s*\((?:FUTURO|RESERVA)\)",
    re.IGNORECASE,
)


def _limpar_modulo(valor: str) -> str:
    """Remove sufixos de ruído (classe de tensão, (FUTURO)/(RESERVA)) e
    colapsa espaços. Usado só no ramo explícito (coluna de módulo)."""
    return " ".join(_SUFIXO_RUIDO.sub("", valor).split())


def canonizar_modulo(valor: str, config: Config, *, explicito: bool = False) -> ResolucaoModulo:
    """Canoniza um NOME de módulo (de sheet_name OU de célula da coluna Módulo).

    Estratégia 1: alias direto por nome inteiro normalizado (mapa_sheet_modulo).
    Estratégia 2: prefixo mapeado seguido do número do módulo.
    Sem canonização:
      - explicito=False (sheet_name): valor CRU, confiança BAIXA  [inalterado]
      - explicito=True  (coluna):     valor cru LIMPO, confiança ALTA
    """
    toks = _tokens(valor)
    chave = "".join(toks)
    if chave in config.mapa_sheet_modulo:
        return ResolucaoModulo(nome=config.mapa_sheet_modulo[chave], confianca="alta")
    ocorr = [
        (i, config.mapa_prefixo_modulo[t])
        for i, t in enumerate(toks)
        if t.isalpha() and t in config.mapa_prefixo_modulo
    ]
    canonicos = {c for _, c in ocorr}
    if len(canonicos) == 1:
        nums = {
            toks[i + 1] for i, _ in ocorr
            if i + 1 < len(toks) and toks[i + 1].isdigit()
        }
        if len(nums) == 1:
            (prefixo,) = canonicos
            (num,) = nums
            return ResolucaoModulo(nome=f"{prefixo}{num}", confianca="alta")
    if explicito:
        return ResolucaoModulo(nome=_limpar_modulo(valor), confianca="alta")
    return ResolucaoModulo(nome=valor, confianca="baixa")
```

Substituir o CORPO de `resolver_modulo` (linhas 32-67, tudo depois da docstring) por:

```python
    return canonizar_modulo(sheet_name, config)
```

Manter a assinatura `def resolver_modulo(sheet_name: str, rows: list[tuple], config: Config) -> ResolucaoModulo:` e sua docstring; `rows` continua sem uso (como hoje).

- [ ] **Step 4: Rodar e ver passar (novos + regressão)**

Run: `python -m pytest tests/test_identidade_modulo.py -q`
Expected: PASS (todos os `test_resolver_modulo_*` seguem verdes — canonização idêntica; `TRF3_P`→`TRF03` via mapa_sheet_modulo `"TRF3P"`).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/identidade_modulo.py tests/test_identidade_modulo.py
git commit -m "refactor: extrai canonizar_modulo de resolver_modulo (flag explicito)"
```

---

## Task 2: Detecção `_col_modulo` + parâmetro `config` em `analisar`

**Files:**
- Modify: `src/tdt/analise/analise_colunas.py`
- Test: `tests/test_analise_colunas.py`

**Interfaces:**
- Consumes: `Config.mapa_prefixo_modulo`; helpers `_valores_coluna`, `_norm`, `_ncols`, `_header_por_densidade` (já existem).
- Produces: `_col_modulo(rows, inicio, ncols, config, reservadas) -> int | None`; `analisar(rows, encoder, ref_emb, siglas_set=None, config=None)` passa a incluir chave `"modulo"` em `MapaColunas.colunas` quando `config` é dado e a coluna é detectada.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao fim de `tests/test_analise_colunas.py`:

```python
from tdt.config import Config


def test_col_modulo_detecta_coluna_de_bloco_com_prefixo():
    # col 0 = módulo (blocos, prefixos AL/TR); col 1 = IED (SEL, sem prefixo);
    # col 2 = descrição; col 3 = índice
    rows = [
        ("Modulo", "Origem", "Descricao", "Addr"),
        ("AL 11 - 13.8kV", "SEL-411L", "FALHA COMUNICACAO", "1"),
        ("AL 11 - 13.8kV", "SEL-411L", "DISJUNTOR ABERTO", "2"),
        ("TR1", "SEL-3530", "CORRENTE FASE", "3"),
        ("TR1", "SEL-3530", "CORRENTE FASE B", "4"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF, config=Config())
    assert mapa.colunas["modulo"] == 0


def test_col_modulo_nao_confunde_com_ied():
    rows = [
        ("Modulo", "Origem", "Descricao", "Addr"),
        ("AL11", "SEL-411L", "FALHA COMUNICACAO", "1"),
        ("AL12", "SEL-411L", "DISJUNTOR ABERTO", "2"),
        ("TR1", "SEL-3530", "CORRENTE FASE", "3"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF, config=Config())
    assert mapa.colunas["modulo"] == 0  # não a coluna IED (1)


def test_col_modulo_ausente_quando_sem_config():
    # sem config, _col_modulo não roda -> comportamento atual preservado
    rows = [
        ("Modulo", "Origem", "Descricao", "Addr"),
        ("AL11", "SEL-411L", "FALHA COMUNICACAO", "1"),
        ("AL12", "SEL-411L", "DISJUNTOR ABERTO", "2"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)  # sem config
    assert "modulo" not in mapa.colunas


def test_col_modulo_none_sem_coluna_de_modulo():
    # nenhuma coluna canoniza em bloco -> None (não inventa módulo)
    rows = [
        ("Sigla", "Descricao", "Addr"),
        ("79", "RELIGAMENTO", "1"),
        ("SF6", "PRESSAO BAIXA", "2"),
        ("DR", "DEFEITO RELE", "3"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF, config=Config())
    assert "modulo" not in mapa.colunas
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_analise_colunas.py -q -k col_modulo`
Expected: FAIL (`analisar() got an unexpected keyword argument 'config'`).

- [ ] **Step 3: Implementar `_col_modulo` e estender `analisar`**

Em `src/tdt/analise/analise_colunas.py`, adicionar o import no topo (após os imports existentes):

```python
from tdt.config import Config
```

Adicionar antes de `def analisar(`:

```python
_MODULO_ROTULO = ("MODULO", "BAY", "VAO")
_MODULO_BONUS = 0.10
_MODULO_CANON_MIN = 0.3   # fração mín. de valores distintos com prefixo de módulo
_MODULO_BLOCO_MIN = 0.5   # estrutura de bloco: 1 - transicoes/(n-1)
_SO_ALFA = re.compile(r"[A-Za-z]+")


def _col_modulo(rows, inicio, ncols, config: Config, reservadas: set[int]) -> int | None:
    """Coluna de módulo por linha: valores em BLOCOS contíguos + alta taxa de
    canonização por prefixo de módulo. Header 'Módulo' soma bônus de desempate.

    - Estrutura de bloco separa {módulo, IED} de {descrição, índice}.
    - Taxa de canonização (1º token alfabético ∈ mapa_prefixo_modulo) separa
      módulo de IED (SEL-411L não bate prefixo).
    - Exclui colunas já reivindicadas (descricao/indice/tipo/sigla), numéricas
      e de baixa diversidade (< 2 distintos).
    """
    prefixos = set(config.mapa_prefixo_modulo)
    header_row = inicio - 1
    header = rows[header_row] if 0 <= header_row < len(rows) else ()
    melhor, melhor_score = None, 0.0
    for c in range(ncols):
        if c in reservadas:
            continue
        vals = _valores_coluna(rows, c, inicio)
        if len(vals) < 2:
            continue
        norm = [_norm(v) for v in vals]
        if len(set(norm)) < 2:
            continue
        if sum(1 for v in norm if v.replace("-", "").isdigit()) / len(norm) > 0.5:
            continue
        transicoes = sum(1 for a, b in zip(norm, norm[1:]) if a != b)
        bloco = 1.0 - transicoes / max(len(norm) - 1, 1)
        if bloco < _MODULO_BLOCO_MIN:
            continue
        distintos = set(norm)
        com_prefixo = sum(
            1 for v in distintos
            if (m := _SO_ALFA.findall(v)) and m[0] in prefixos
        )
        canon = com_prefixo / len(distintos)
        if canon < _MODULO_CANON_MIN:
            continue
        score = canon * bloco
        rotulo = _norm(header[c]) if c < len(header) else ""
        if any(t in rotulo for t in _MODULO_ROTULO):
            score *= 1 + _MODULO_BONUS
        if score > melhor_score:
            melhor, melhor_score = c, score
    return melhor
```

Substituir a função `analisar` (linhas 268-286) por:

```python
def analisar(
    rows: list[tuple], encoder, ref_emb: np.ndarray,
    siglas_set: frozenset[str] | None = None,
    config: Config | None = None,
) -> MapaColunas:
    ncols = _ncols(rows)
    h = _header_por_densidade(rows)
    inicio = h + 1

    c_desc = _col_descricao(rows, inicio, ncols, encoder, ref_emb)
    c_idx = _col_indice(rows, inicio, ncols)
    c_tipo = _col_tipo(rows, inicio, ncols)
    c_sig = _col_sigla(rows, inicio, ncols, siglas_set) if siglas_set is not None else None
    c_mod = None
    if config is not None:
        reservadas = {c for c in (c_desc, c_idx, c_tipo, c_sig) if c is not None}
        c_mod = _col_modulo(rows, inicio, ncols, config, reservadas)

    colunas = {
        k: v
        for k, v in (
            ("descricao", c_desc),
            ("indice", c_idx),
            ("tipo", c_tipo),
            ("sigla", c_sig),
            ("modulo", c_mod),
        )
        if v is not None
    }
    return MapaColunas(header_row=h + 1, colunas=colunas)
```

- [ ] **Step 4: Rodar e ver passar (novos + regressão)**

Run: `python -m pytest tests/test_analise_colunas.py -q`
Expected: PASS. Em especial `test_modulo_nao_e_detectado_por_coluna` (chama `analisar` sem `config`) segue verde.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/analise/analise_colunas.py tests/test_analise_colunas.py
git commit -m "feat: _col_modulo detecta coluna de modulo por linha (gated em config)"
```

---

## Task 3: `estruturar` — módulo por linha + célula vazia p/ revisão

**Files:**
- Modify: `src/tdt/normalizacao/estruturador.py:110-138`
- Test: `tests/test_estruturador.py`

**Interfaces:**
- Consumes: chave `"modulo"` em `mapa.colunas` (Task 2).
- Produces: `SignalRecord.modulo` com `origem_contexto="coluna:MODULO_POR_LINHA"` e `nome` = valor cru da célula (ou `None` + `status="revisao"`/`justificativa="modulo_indefinido"` se vazia).

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao fim de `tests/test_estruturador.py`:

```python
def test_estruturar_modulo_por_linha_muda_entre_blocos():
    rows = [
        ("Modulo", "Descricao", "Tipo", "Addr"),
        ("LTSM3C1", "DISJUNTOR ABERTO", "Ponto Simples", "1"),
        ("LTSM3C1", "DISJUNTOR FECHADO", "Ponto Simples", "2"),
        ("TR1", "TEMPERATURA OLEO", "Ponto Simples", "3"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"modulo": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="ESTADOS", config=Config())
    assert [r.modulo.nome for r in recs] == ["LTSM3C1", "LTSM3C1", "TR1"]
    assert all(r.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" for r in recs)


def test_estruturar_modulo_vazio_vai_para_revisao():
    rows = [
        ("Modulo", "Descricao", "Tipo", "Addr"),
        ("TR1", "TEMPERATURA OLEO", "Ponto Simples", "1"),
        ("", "SINAL SEM MODULO", "Ponto Simples", "2"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"modulo": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="ESTADOS", config=Config())
    assert recs[0].status == "pendente"
    assert recs[1].status == "revisao"
    assert recs[1].justificativa == "modulo_indefinido"
    assert recs[1].modulo.nome is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_estruturador.py -q -k modulo_por_linha`
Expected: FAIL (módulo vem de `sheet_name`, origem errada / status errado).

- [ ] **Step 3: Implementar o ramo de coluna de módulo**

Em `src/tdt/normalizacao/estruturador.py`, no início de `estruturar` (após `c_sigla = cols.get("sigla")`, ~linha 60) adicionar:

```python
    c_modulo = cols.get("modulo")
```

Substituir o bloco de pré-classificação (linhas 110-138, do comentário `# --- pré-classificação...` até a linha de fechamento `# ---...`) por:

```python
        # --- resolução de módulo/sigla por coluna ---
        sigla_sinal = None
        status = "pendente"
        motivo_revisao = None
        origem_modulo = "sheet_name"
        nome_mod_final = nome_mod

        if c_modulo is not None:
            # Gênero sheet-por-tipo: módulo numa coluna dedicada, por linha.
            # Precedência sobre extração do NOME (coluna explícita ganha).
            val_mod = (
                str(row[c_modulo]).strip()
                if c_modulo < len(row) and row[c_modulo] is not None
                else ""
            )
            origem_modulo = "coluna:MODULO_POR_LINHA"
            if val_mod:
                nome_mod_final = val_mod
            else:
                nome_mod_final = None
                status = "revisao"
                motivo_revisao = "modulo_indefinido"
        elif tem_sigla and siglas_set is not None:
            sv = str(row[c_sigla] or "").strip().upper()
            if sv and sv in siglas_set:
                sigla_sinal = sv
                nome_str = str(row[c_desc]) if tem_desc else ""
                if nome_str and not sigla_esta_no_nome(nome_str, sv):
                    status = "revisao"
                    motivo_revisao = "nome_sigla_inconsistente"
                else:
                    status = "decidido"
                    mod_extraido = extrair_modulo_do_nome(nome_str) if nome_str else None
                    if mod_extraido:
                        nome_mod_final, origem_modulo = mod_extraido, "coluna:SIGLA"
                        equip_extraido = extrair_equipamento_do_nome(nome_str)
                        if equip_extraido:
                            eletrico = replace(eletrico, nome_equipamento=equip_extraido)
            # sv não-vazia mas fora da LP -> status fica "pendente": recai no scoring
        # ---------------------------------------------------------------------
```

(O ramo `elif` é o bloco de sigla ORIGINAL, movido sob `elif`; nada nele muda — quando há coluna de módulo, `c_modulo is not None` e o ramo de sigla não roda; quando não há, `c_modulo is None` e o `elif` roda idêntico ao atual.)

- [ ] **Step 4: Rodar e ver passar (novos + regressão)**

Run: `python -m pytest tests/test_estruturador.py -q`
Expected: PASS (testes de sigla `coluna:SIGLA` e todos os demais seguem verdes — `c_modulo is None` nesses casos).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizacao/estruturador.py tests/test_estruturador.py
git commit -m "feat: estruturar le modulo por linha (coluna:MODULO_POR_LINHA); vazio->revisao"
```

---

## Task 4: `aplicar_identidade` — canoniza por linha + tipo por grupo + wiring do pipeline

**Files:**
- Modify: `src/tdt/identidade_modulo.py:93-109`
- Modify: `src/tdt/pipeline.py:601`
- Test: `tests/test_identidade_modulo.py`

**Interfaces:**
- Consumes: `origem_contexto="coluna:MODULO_POR_LINHA"` (Task 3); `canonizar_modulo` (Task 1); `classificar_tipo` (existente).
- Produces: `aplicar_identidade` retorna `(sinais, "alta")` para o gênero por linha, com `modulo.nome` canonizado e `modulo.tipo` classificado por grupo. Assinatura inalterada.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao fim de `tests/test_identidade_modulo.py`:

```python
def _rec_mod(norm: str, nome_mod: str) -> SignalRecord:
    return SignalRecord(
        id="t:1",
        modulo=Modulo(nome_mod, "coluna:MODULO_POR_LINHA"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", ()),
        descricoes=Descricoes(norm, norm),
    )


def test_aplicar_identidade_por_linha_canoniza_e_classifica_por_grupo():
    sinais = [
        _rec_mod("DISJUNTOR", "AL 11 - 13.8kV"),
        _rec_mod("CORRENTE", "TR1"),
    ]
    novos, conf = aplicar_identidade(sinais, "ESTADOS", [], Config())
    assert novos[0].modulo.nome == "AL11"
    assert novos[0].modulo.tipo == "Alimentador"
    assert novos[1].modulo.nome == "TR1"
    assert novos[1].modulo.tipo == "Transformador"
    assert conf == "alta"


def test_aplicar_identidade_por_linha_reconcilia_variantes():
    # 'AL 11' e 'AL11' (variantes cross-sheet) canonizam para o mesmo nome
    sinais = [_rec_mod("SINAL A", "AL 11 - 13.8kV"), _rec_mod("SINAL B", "AL11 - 13.8kV")]
    novos, _ = aplicar_identidade(sinais, "MEDIDAS", [], Config())
    assert novos[0].modulo.nome == novos[1].modulo.nome == "AL11"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `python -m pytest tests/test_identidade_modulo.py -q -k por_linha`
Expected: FAIL (nome não canonizado: `AL 11 - 13.8kV` preservado; tipo único da sheet, não por grupo).

- [ ] **Step 3: Implementar o ramo por linha em `aplicar_identidade`**

Em `src/tdt/identidade_modulo.py`, adicionar antes de `aplicar_identidade`:

```python
def _identidade_por_linha(
    sinais: list[SignalRecord], config: Config
) -> list[SignalRecord]:
    """Gênero módulo-por-coluna: canoniza cada nome de módulo (explícito) e
    classifica o tipo POR GRUPO de módulo canônico (não 1 tipo/sheet)."""
    canon: list[SignalRecord] = []
    for s in sinais:
        if s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" and s.modulo.nome:
            res = canonizar_modulo(s.modulo.nome, config, explicito=True)
            s = replace(s, modulo=replace(s.modulo, nome=res.nome))
        canon.append(s)
    grupos: dict[str, list[SignalRecord]] = {}
    for s in canon:
        grupos.setdefault(s.modulo.nome or "", []).append(s)
    tipo_de = {nome: classificar_tipo(nome, regs, config) for nome, regs in grupos.items()}
    return [
        replace(s, modulo=replace(s.modulo, tipo=tipo_de[s.modulo.nome or ""]))
        for s in canon
    ]
```

Substituir o corpo de `aplicar_identidade` (linhas 96-109, tudo após a docstring/assinatura) por:

```python
    if any(s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" for s in sinais):
        return _identidade_por_linha(sinais, config), "alta"
    res = resolver_modulo(sheet_name, rows, config)
    # nome: resolve só onde veio do nome da sheet; preserva módulo de coluna.
    com_nome = [
        replace(s, modulo=replace(s.modulo, nome=res.nome))
        if s.modulo.origem_contexto == "sheet_name"
        else s
        for s in sinais
    ]
    nome_ref = com_nome[0].modulo.nome if com_nome else res.nome
    tipo = classificar_tipo(nome_ref or "", com_nome, config)
    com_tipo = [replace(s, modulo=replace(s.modulo, tipo=tipo)) for s in com_nome]
    # confiança só importa quando o nome veio da sheet (caminho não-homogêneo).
    veio_de_sheet = any(s.modulo.origem_contexto == "sheet_name" for s in sinais)
    return com_tipo, (res.confianca if veio_de_sheet else "alta")
```

- [ ] **Step 4: Rodar e ver passar**

Run: `python -m pytest tests/test_identidade_modulo.py -q`
Expected: PASS (novos + `test_aplicar_identidade_preserva_nome_de_coluna` com `coluna:MODULO` homogêneo NÃO entra no ramo novo).

- [ ] **Step 5: Wiring do pipeline — passar `config` a `analisar`**

Em `src/tdt/pipeline.py:601`, trocar:

```python
            mapa = analisar(rows, encoder, ref_emb, siglas_set=lp.siglas)
```

por:

```python
            mapa = analisar(rows, encoder, ref_emb, siglas_set=lp.siglas, config=config)
```

- [ ] **Step 6: Rodar a suíte inteira**

Run: `python -m pytest -q`
Expected: PASS (nenhuma regressão em todo o projeto).

- [ ] **Step 7: Commit**

```bash
git add src/tdt/identidade_modulo.py src/tdt/pipeline.py tests/test_identidade_modulo.py
git commit -m "feat: aplicar_identidade canoniza modulo por linha + tipo por grupo; wire pipeline"
```

---

## Task 5: Integração no arquivo SMF real

**Files:**
- Create: `tests/test_modulo_por_coluna_smf.py`

**Interfaces:**
- Consumes: `_col_modulo`, `canonizar_modulo`, `estruturar`, `aplicar_identidade` (Tasks 1-4); openpyxl para ler o arquivo.

- [ ] **Step 1: Escrever o teste de integração (deve passar com Tasks 1-4 prontas)**

Criar `tests/test_modulo_por_coluna_smf.py`:

```python
"""Integração: gênero sheet-por-tipo (SMF) — módulo por coluna, cross-sheet.

Determinístico, sem modelo ST: exercita _col_modulo + canonizar_modulo +
estruturar + aplicar_identidade nas linhas reais do arquivo. Guarda contra
regressão da detecção e da reconciliação cross-sheet.
"""
from pathlib import Path

import openpyxl
import pytest

from tdt.analise.analise_colunas import _col_modulo, _header_por_densidade, _ncols
from tdt.config import Config
from tdt.identidade_modulo import canonizar_modulo

_ARQ = Path(__file__).resolve().parents[1] / "docs" / "input_não_homogeneo_5_SMF.xlsx"


def _rows(sheet: str) -> list[tuple]:
    wb = openpyxl.load_workbook(_ARQ, data_only=True, read_only=True)
    return [tuple(r) for r in wb[sheet].iter_rows(values_only=True)]


@pytest.mark.skipif(not _ARQ.exists(), reason="arquivo SMF não disponível")
@pytest.mark.parametrize("sheet", ["ESTADOS", "MEDIDAS", "COMANDOS"])
def test_col_modulo_e_a_coluna_A_no_smf(sheet):
    rows = _rows(sheet)
    inicio = _header_por_densidade(rows) + 1
    ncols = _ncols(rows)
    assert _col_modulo(rows, inicio, ncols, Config(), reservadas=set()) == 0


@pytest.mark.skipif(not _ARQ.exists(), reason="arquivo SMF não disponível")
def test_reconciliacao_cross_sheet_al11():
    cfg = Config()
    # 'AL 11 - 13.8kV' (ESTADOS) e 'AL11 - 13.8kV' (MEDIDAS) -> mesmo canônico
    a = canonizar_modulo("AL 11 - 13.8kV", cfg, explicito=True).nome
    b = canonizar_modulo("AL11 - 13.8kV", cfg, explicito=True).nome
    assert a == b == "AL11"
```

- [ ] **Step 2: Rodar e ver passar**

Run: `python -m pytest tests/test_modulo_por_coluna_smf.py -q`
Expected: PASS (3 sheets → coluna 0; AL 11/AL11 → AL11).

- [ ] **Step 3: Verificação manual end-to-end (opcional, requer modelo ST)**

Rodar o pipeline completo no arquivo pela UI/CLI e conferir no resultado:
- módulos por linha corretos (não "ESTADOS"/"MEDIDAS"/"COMANDOS");
- módulos `AL11`, `TR1`, `LTSM3C1` etc. unificados entre os 3 tipos de ponto.
Registrar observação em `docs/observações_pendentes.txt` se algum módulo cair em revisão inesperadamente.

- [ ] **Step 4: Commit**

```bash
git add tests/test_modulo_por_coluna_smf.py
git commit -m "test: integracao modulo por coluna no arquivo SMF (deteccao + reconciliacao)"
```

---

## Self-Review (feito)

**Spec coverage:**
- Detecção híbrida `_col_modulo` (conteúdo + header desempate) → Task 2. ✓
- `canonizar_modulo` com `explicito` preservando `resolver_modulo` → Task 1. ✓
- Módulo por linha em `estruturar` + célula vazia→revisão → Task 3. ✓
- Tipo por grupo + tag nova em `aplicar_identidade` → Task 4. ✓
- Reconciliação cross-sheet automática → Task 4 (canonização) + Task 5 (guard). ✓
- Preservação de comportamento (gating por config, tag distinta, fallback inalterado, assinaturas) → constraints + Tasks 1-4 rodando suíte a cada passo. ✓

**Placeholder scan:** sem TBD/TODO; todo passo com código e comando concretos. ✓

**Type consistency:** `canonizar_modulo(valor, config, *, explicito=False) -> ResolucaoModulo`, `_col_modulo(rows, inicio, ncols, config, reservadas) -> int|None`, `origem_contexto="coluna:MODULO_POR_LINHA"`, `justificativa="modulo_indefinido"` — usados de forma idêntica entre tasks. ✓
