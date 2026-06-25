# SP6 — Normalização Estrutural (Equipamento/Barra/Fase) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir a ordem do pipeline de normalização (hífen/pontuação é destruído antes de qualquer extração estrutural rodar), extraindo equipamento (Disjuntor/Seccionadora), barra (Principal/Auxiliar) e fase explicitamente do texto bruto, e usar essa informação no motor de regras pra descartar candidatos de equipamento errado.

**Architecture:** Novo passo N0 (`extrair_contexto_estrutural`) em `normalizador.py`, chamado por `estruturador.py` antes de `canonizar()`. Populamento de `Eletrico.fase/equipamento_alvo/barra` na normalização (não só pós-decisão). Nova regra `r_equipamento` em `motor_regras.py`.

**Tech Stack:** Python, regex, dataclasses — sem dependências novas.

## Global Constraints

- Spec de origem: `docs/superpowers/specs/2026-06-24-sp6-normalizacao-estrutural-equipamento-design.md`.
- Tabela de equipamento fica pequena de propósito: `{"52": "Disjuntor", "89": "Seccionadora", "29": "Seccionadora"}` — não adicionar mais códigos agora (YAGNI confirmado com o usuário).
- `canonizar()` mantém a assinatura atual (`texto, config, vocab=None -> str`) — outros chamadores (`pipeline._corpus()` pra lista padrão) não devem ser afetados.
- TDD em todas as tasks; suíte completa (`pytest -v`) verde ao final.
- Commits pequenos, um por task.

---

### Task 1: `ContextoEstrutural` + extração de equipamento (N0, parte 1)

**Files:**
- Modify: `src/tdt/normalizador.py`
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Produces: `ContextoEstrutural` (dataclass frozen, campos `equipamento_alvo: str | None`, `barra: str | None`, `fase: str | None`, todos default `None`); `extrair_contexto_estrutural(texto: str) -> tuple[str, ContextoEstrutural]` — usado pelas Tasks 2, 3 e 5 (vão estender o corpo da função) e pela Task 4 (`estruturador.py`).

- [ ] **Step 1: Escrever o teste falhando**

```python
# adicionar em tests/test_normalizador.py
from tdt.normalizador import ContextoEstrutural, extrair_contexto_estrutural


def test_extrai_equipamento_disjuntor():
    texto, ctx = extrair_contexto_estrutural("DISJUNTOR 52-1 ABERTO")
    assert ctx.equipamento_alvo == "Disjuntor"
    assert "52-1" not in texto
    assert "52" not in texto.split()
    assert "1" not in texto.split()


def test_extrai_equipamento_seccionadora():
    texto, ctx = extrair_contexto_estrutural("SECCIONADORA 89-3 FECHADA")
    assert ctx.equipamento_alvo == "Seccionadora"
    assert "89" not in texto.split()


def test_codigo_fora_da_tabela_remove_mas_nao_classifica():
    texto, ctx = extrair_contexto_estrutural("RELE 67-1 ATUADO")
    assert ctx.equipamento_alvo is None
    assert "67" not in texto.split()


def test_sem_id_de_equipamento_nao_extrai_nada():
    texto, ctx = extrair_contexto_estrutural("FALHA COMUNICACAO")
    assert ctx == ContextoEstrutural()
    assert texto == "FALHA COMUNICACAO"
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_normalizador.py -v -k extrai_equipamento`
Expected: FAIL — `ImportError: cannot import name 'ContextoEstrutural'`

- [ ] **Step 3: Implementar**

```python
# src/tdt/normalizador.py — adicionar após os imports existentes, antes de "# --- N1 ---"
from dataclasses import dataclass

_EQUIPAMENTO_ANSI: dict[str, str] = {
    "52": "Disjuntor",
    "89": "Seccionadora",
    "29": "Seccionadora",  # seccionadora de aterramento
}
_ID_EQUIPAMENTO = re.compile(r"\b(\d+)-(\d+)\b")


@dataclass(frozen=True)
class ContextoEstrutural:
    equipamento_alvo: str | None = None
    barra: str | None = None
    fase: str | None = None


def extrair_contexto_estrutural(texto: str) -> tuple[str, ContextoEstrutural]:
    """N0: extrai equipamento/barra/fase do texto BRUTO (antes do colapso de
    separadores em normalizar() destruir o hífen e o stopword 'A' comer a
    fase). Devolve (texto_remanescente, ContextoEstrutural)."""
    if not texto:
        return "", ContextoEstrutural()
    base = _sem_acentos(texto).upper()

    equipamento_alvo = None
    m = _ID_EQUIPAMENTO.search(base)
    if m:
        equipamento_alvo = _EQUIPAMENTO_ANSI.get(m.group(1))
        base = (base[: m.start()] + " " + base[m.end() :]).strip()
        base = " ".join(base.split())

    return base, ContextoEstrutural(equipamento_alvo=equipamento_alvo)
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_normalizador.py -v -k extrai_equipamento`
Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizador.py tests/test_normalizador.py
git commit -m "feat(normalizador): N0 extrai código de equipamento (52->Disjuntor, 89/29->Seccionadora) antes do colapso de hífen"
```

---

### Task 2: Extração de barra (N0, parte 2)

**Files:**
- Modify: `src/tdt/normalizador.py` (`extrair_contexto_estrutural`)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Consumes/extends: `ContextoEstrutural` e `extrair_contexto_estrutural` (Task 1).

- [ ] **Step 1: Escrever o teste falhando**

```python
def test_extrai_barra_principal():
    texto, ctx = extrair_contexto_estrutural("TENSAO BARRA P FASES AB")
    assert ctx.barra == "Principal"
    assert "P" not in texto.split()


def test_extrai_barra_auxiliar():
    texto, ctx = extrair_contexto_estrutural("TENSAO BARRA A")
    assert ctx.barra == "Auxiliar"


def test_letra_p_sem_marcador_barra_nao_e_barra():
    # "P" sozinho, sem "BARRA" antes, não deve ser tratado como barra
    texto, ctx = extrair_contexto_estrutural("POTENCIA P TOTAL")
    assert ctx.barra is None
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_normalizador.py -v -k extrai_barra`
Expected: FAIL — `ctx.barra` sempre `None` (campo ainda não é populado)

- [ ] **Step 3: Implementar**

```python
# src/tdt/normalizador.py — dentro de extrair_contexto_estrutural, depois do bloco de equipamento
_BARRA: dict[str, str] = {"P": "Principal", "A": "Auxiliar"}
_MARCADOR_BARRA = re.compile(r"\bBARRA\s+([A-Z])\b")
```

```python
    barra = None
    m_barra = _MARCADOR_BARRA.search(base)
    if m_barra and m_barra.group(1) in _BARRA:
        barra = _BARRA[m_barra.group(1)]
        inicio, fim = m_barra.span(1)
        base = (base[:inicio] + " " + base[fim:]).strip()
        base = " ".join(base.split())
```

(adicionar `_BARRA`/`_MARCADOR_BARRA` como constantes de módulo, junto de `_EQUIPAMENTO_ANSI`/`_ID_EQUIPAMENTO`; o bloco de barra entra no corpo de `extrair_contexto_estrutural` depois do bloco de equipamento, atualizando `base` antes de devolver. Ajustar o `return` final para `ContextoEstrutural(equipamento_alvo=equipamento_alvo, barra=barra)`.)

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_normalizador.py -v -k "extrai_barra or extrai_equipamento or letra_p"`
Expected: 7 passed (4 da Task 1 + 3 novos)

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizador.py tests/test_normalizador.py
git commit -m "feat(normalizador): N0 extrai barra Principal/Auxiliar (BARRA P/A) do texto bruto"
```

---

### Task 3: Extração de fase (N0, parte 3) — move `_fase_no_texto` de `motor_regras.py`

**Files:**
- Modify: `src/tdt/normalizador.py` (`extrair_contexto_estrutural`)
- Modify: `src/tdt/motor_regras.py` (`r3_fase`, remove `_fase_no_texto`/`_FASES`/`_FASE_TOKENS` locais)
- Test: `tests/test_normalizador.py`, `tests/test_motor_regras.py`

**Interfaces:**
- Produces: `ContextoEstrutural.fase` populado.
- Consumes (movido): a lógica hoje em `motor_regras._fase_no_texto` — vira parte de `extrair_contexto_estrutural`, em `normalizador.py`.

- [ ] **Step 1: Escrever o teste falhando**

```python
# tests/test_normalizador.py
def test_extrai_fase_letra_unica():
    texto, ctx = extrair_contexto_estrutural("CORRENTE FASE A")
    assert ctx.fase == "A"
    assert "A" not in texto.split()


def test_extrai_fase_dupla():
    texto, ctx = extrair_contexto_estrutural("TENSAO FASE AB")
    assert ctx.fase == "AB"


def test_extrai_fase_neutro():
    texto, ctx = extrair_contexto_estrutural("CORRENTE NEUTRO")
    assert ctx.fase == "N"


def test_extrai_fase_trifasico():
    texto, ctx = extrair_contexto_estrutural("TENSAO TRIFASICA")
    assert ctx.fase == "ABC"


def test_sem_fase_no_texto():
    texto, ctx = extrair_contexto_estrutural("FALHA COMUNICACAO")
    assert ctx.fase is None
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_normalizador.py -v -k extrai_fase`
Expected: FAIL — `ctx.fase` sempre `None`

- [ ] **Step 3: Implementar — mover a lógica de `motor_regras.py` pra `normalizador.py`**

```python
# src/tdt/normalizador.py — constantes de módulo (junto das outras de N0)
_FASES: tuple[str, ...] = ("ABC", "AB", "BC", "CA", "A", "B", "C", "N")
_FASE_TOKENS: dict[str, str] = {
    "NEUTRO": "N",
    "TRIFASICO": "ABC",
    "TRIFASICA": "ABC",
}


def _fase_no_texto(tokens: list[str]) -> tuple[str | None, str | None]:
    """Devolve (fase, token_a_remover) ou (None, None)."""
    for i, tok in enumerate(tokens):
        if tok in _FASE_TOKENS:
            return _FASE_TOKENS[tok], tok
    if "FASE" in tokens:
        idx = tokens.index("FASE")
        if idx + 1 < len(tokens) and tokens[idx + 1] in _FASES:
            return tokens[idx + 1], tokens[idx + 1]
    return None, None
```

Dentro de `extrair_contexto_estrutural`, depois do bloco de barra:
```python
    fase = None
    tokens = base.split()
    fase, tok_remover = _fase_no_texto(tokens)
    if tok_remover is not None:
        tokens.remove(tok_remover)
        base = " ".join(tokens)

    return base, ContextoEstrutural(equipamento_alvo=equipamento_alvo, barra=barra, fase=fase)
```

**Em `motor_regras.py`:** remover `_FASES`, `_FASE_TOKENS`, `_fase_no_texto` (linhas 178-198) e simplificar `r3_fase`:

```python
def r3_fase(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Fase (A/B/C/N/AB/BC/CA/ABC): favorece mesma fase, penaliza divergente.

    ``ctx.eletrico.fase`` já vem preenchido pela normalização (N0,
    ``normalizador.extrair_contexto_estrutural``) — esta regra não re-deriva
    do texto, só lê o que já foi extraído.
    """
    alvo = getattr(ctx.eletrico, "fase", None) if ctx.eletrico is not None else None
    if not alvo:
        return _ZERO
    fase_cand = fase_da_sigla(cand.sigla.upper())
    if fase_cand is None:
        return _ZERO
    peso = cfg.pesos_regras["fase"]
    if fase_cand == alvo:
        return AjusteRegra(peso, f"fase: candidato e texto em {alvo}")
    return AjusteRegra(-peso, f"fase: candidato {fase_cand} diverge de {alvo}")
```

- [ ] **Step 4: Rodar e confirmar sucesso, e ajustar testes de `r3_fase` que dependiam do texto**

Run: `pytest tests/test_normalizador.py tests/test_motor_regras.py -v`

`tests/test_motor_regras.py` provavelmente tem testes de `r3_fase` que constroem um `Contexto` com `tokens` contendo "FASE A" e `eletrico=Eletrico()` (sem fase) — esses testes vão falhar porque `r3_fase` não lê mais `ctx.tokens`. Ajustar esses testes pra construir o `Contexto` com `eletrico=Eletrico(fase="A")` em vez de depender de tokens — é a forma correta de testar a regra isoladamente agora (a extração de fase do texto já tem seus próprios testes em `test_normalizador.py`, Step 1 desta task).

Expected ao final: todos passam.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/normalizador.py src/tdt/motor_regras.py tests/test_normalizador.py tests/test_motor_regras.py
git commit -m "refactor(normalizador): move extração de fase pra N0 (texto bruto, antes do stopword 'A' comer a fase); r3_fase só lê ctx.eletrico.fase"
```

---

### Task 4: Campo `Eletrico.barra` + wiring de N0 em `estruturador.py`

**Files:**
- Modify: `src/tdt/contracts.py` (`Eletrico`)
- Modify: `src/tdt/estruturador.py`
- Test: `tests/test_estruturador.py`

**Interfaces:**
- Consumes: `extrair_contexto_estrutural` (Tasks 1-3), `canonizar` (já existente).
- Produces: `SignalRecord.eletrico.{fase,equipamento_alvo,barra}` populados a partir da descrição de entrada, antes de qualquer classificação.

- [ ] **Step 1: Escrever o teste falhando**

```python
# adicionar em tests/test_estruturador.py
def test_eletrico_populado_a_partir_da_descricao():
    rows = [
        ("Descrição", "Endereço"),
        ("Disjuntor 52-1 Fase A Barra P Aberto", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].eletrico.equipamento_alvo == "Disjuntor"
    assert recs[0].eletrico.fase == "A"
    assert recs[0].eletrico.barra == "Principal"
    # texto canônico não tem mais os tokens extraídos como ruído
    assert "52" not in recs[0].descricoes.normalizada.split()
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_estruturador.py -v -k eletrico_populado`
Expected: FAIL — `eletrico.equipamento_alvo is None` (ainda não existe wiring)

- [ ] **Step 3: Implementar**

`src/tdt/contracts.py` — adicionar campo em `Eletrico` (depois de `fase`, antes de `nivel_tensao`, mantendo a ordem alfabética/lógica não importa, só não quebrar posicionais — é dataclass com kwargs, sem risco):
```python
@dataclass(frozen=True)
class Eletrico:
    fase: str | None = None
    nivel_tensao: str | None = None  # "AT" | "BT"
    equipamento_alvo: str | None = None
    nome_equipamento: str | None = None  # "52-10"
    barra: str | None = None  # "Principal" | "Auxiliar"
```

`src/tdt/estruturador.py` — import e uso:
```python
from tdt.normalizador import canonizar, extrair_contexto_estrutural
from tdt.contracts import Eletrico  # junto dos outros imports de contracts
```

No corpo do loop de `estruturar()`, onde hoje é:
```python
        bruta = row[c_desc]
        if not _norm(bruta):
            continue
```
... (mantém igual até a montagem do `SignalRecord`). Trocar a montagem da descrição/registro:
```python
        remanescente, ctx_estrutural = extrair_contexto_estrutural(str(bruta))
        eletrico = Eletrico(
            fase=ctx_estrutural.fase,
            equipamento_alvo=ctx_estrutural.equipamento_alvo,
            barra=ctx_estrutural.barra,
        )
        ...
        registros.append(
            SignalRecord(
                id=f"{sheet_name}:{i + 1}",
                modulo=Modulo(nome_mod, "sheet_name"),
                tipo_sinal=TipoSinal(categoria, is_double_bit=False, direcao=direcao,
                                     categoria_confiavel=confiavel),
                enderecamento=Enderecamento("DNP3", indices),
                descricoes=Descricoes(str(bruta), canonizar(remanescente, config, vocab)),
                eletrico=eletrico,
            )
        )
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_estruturador.py -v`
Expected: todos passam, incluindo o novo.

- [ ] **Step 5: Rodar a suíte de pipeline pra checar regressão**

Run: `pytest tests/test_pipeline.py tests/test_pipeline_diagnostico.py -v`
Expected: todos passam — `_com_fase()` em `pipeline.py` só sobrescreve `eletrico.fase` quando ele está `None` (`if rec.sigla_sinal and rec.eletrico.fase is None`), então não há conflito com o valor já populado por N0; ele só preenche o que N0 não conseguiu extrair do texto.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/contracts.py src/tdt/estruturador.py tests/test_estruturador.py
git commit -m "feat(estruturador): popula eletrico.{fase,equipamento_alvo,barra} a partir da descrição de entrada via N0, antes da decisão"
```

---

### Task 5: Pontuação residual (parênteses, vírgula, ponto-e-vírgula, dois-pontos)

**Files:**
- Modify: `src/tdt/normalizador.py` (`_SEPARADORES`)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Nenhuma interface nova — só estende a constante `_SEPARADORES` já consumida por `normalizar()`.

- [ ] **Step 1: Escrever o teste falhando**

```python
def test_parenteses_e_pontuacao_extra_virram_espaco():
    cfg = Config()
    assert normalizar("DISJUNTOR (52-1) ABERTO, FECHADO; TESTE: OK", cfg) == \
        "DISJUNTOR 52 1 ABERTO FECHADO TESTE OK"
```

(usa `from tdt.normalizador import normalizar` — já deve estar importado no arquivo de teste; se não, adicionar.)

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_normalizador.py -v -k parenteses_e_pontuacao`
Expected: FAIL — parênteses/vírgula/`;`/`:` continuam no texto, ex. `"DISJUNTOR (52"` não vira `"DISJUNTOR 52"`.

- [ ] **Step 3: Implementar**

```python
# src/tdt/normalizador.py — linha 31
_SEPARADORES = re.compile(r"[/\-.(),;:]")
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_normalizador.py -v`
Expected: todos passam (incluindo os testes pré-existentes de `_SEPARADORES` com `/`, `-`, `.` — comportamento preservado, só estendido).

- [ ] **Step 5: Rodar a suíte completa de normalização/estruturador/pipeline**

Run: `pytest tests/test_normalizador.py tests/test_estruturador.py tests/test_pipeline.py tests/test_tokenizer.py -v`
Expected: todos passam. Atenção especial ao tokenizer (`tdt/tokenizer.py`, "rejunta siglas separadas") — se algum teste dele depender de um parêntese sobrevivendo até o tokenizer, vai quebrar; nesse caso, o teste do tokenizer está testando um cenário que não deveria mais ocorrer (parêntese já é removido antes) — ajustar o teste, não a regra nova.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/normalizador.py tests/test_normalizador.py
git commit -m "fix(normalizador): parênteses e pontuação extra (,;:) virram espaço no pré-processamento, igual / - ."
```

---

### Task 6: Regra `r_equipamento` no motor de regras

**Files:**
- Modify: `src/tdt/motor_regras.py`
- Modify: `src/tdt/config.py` (`pesos_regras`)
- Test: `tests/test_motor_regras.py`

**Interfaces:**
- Consumes: `ctx.eletrico.equipamento_alvo` (populado pela Task 4).
- Produces: `equipamento_da_sigla(sigla: str) -> str | None`, `r_equipamento(rec, cand, ctx, cfg) -> AjusteRegra` — adicionada ao registro de regras aplicado por `aplicar_rastreado`/`aplicar`.

- [ ] **Step 1: Escrever o teste falhando**

```python
# adicionar em tests/test_motor_regras.py
from tdt.contracts import Eletrico
from tdt.motor_regras import equipamento_da_sigla, r_equipamento


def test_equipamento_da_sigla_disjuntor():
    assert equipamento_da_sigla("DJ") == "Disjuntor"
    assert equipamento_da_sigla("DJE1") == "Disjuntor"


def test_equipamento_da_sigla_seccionadora():
    assert equipamento_da_sigla("SECC") == "Seccionadora"
    assert equipamento_da_sigla("SECB") == "Seccionadora"


def test_equipamento_da_sigla_sem_match():
    assert equipamento_da_sigla("BATA") is None


def test_r_equipamento_penaliza_familia_errada():
    ctx = Contexto(tokens=frozenset(), eletrico=Eletrico(equipamento_alvo="Disjuntor"))
    cand = Candidato("SECC", 0.8, "tfidf")
    cfg = Config()
    ajuste = r_equipamento(None, cand, ctx, cfg)
    assert ajuste.delta < 0


def test_r_equipamento_neutro_sem_alvo():
    ctx = Contexto(tokens=frozenset(), eletrico=Eletrico())
    cand = Candidato("SECC", 0.8, "tfidf")
    cfg = Config()
    ajuste = r_equipamento(None, cand, ctx, cfg)
    assert ajuste.delta == 0.0
```

(verificar imports já presentes no topo de `tests/test_motor_regras.py` — `Contexto`, `Candidato`, `Config`; adicionar o que faltar.)

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_motor_regras.py -v -k "equipamento"`
Expected: FAIL — `ImportError: cannot import name 'equipamento_da_sigla'`

- [ ] **Step 3: Implementar**

```python
# src/tdt/motor_regras.py — nova seção, após "# --- R3: fase ---" (ou antes de aplicar_rastreado)

# --- R_equip: equipamento -----------------------------------------------

_EQUIPAMENTO_SIGLA: tuple[tuple[str, str], ...] = (
    ("DJ", "Disjuntor"),
    ("SEC", "Seccionadora"),
)


def equipamento_da_sigla(sigla: str) -> str | None:
    for prefixo, nome in _EQUIPAMENTO_SIGLA:
        if sigla.startswith(prefixo):
            return nome
    return None


def r_equipamento(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Penaliza candidato de família de equipamento diferente da detectada
    na descrição (Disjuntor vs Seccionadora) — ctx.eletrico.equipamento_alvo
    vem da extração estrutural (N0) em normalizador.py."""
    alvo = getattr(ctx.eletrico, "equipamento_alvo", None) if ctx.eletrico is not None else None
    if not alvo:
        return _ZERO
    equip_cand = equipamento_da_sigla(cand.sigla.upper())
    if equip_cand is None or equip_cand == alvo:
        return _ZERO
    peso = cfg.pesos_regras["equipamento"]
    return AjusteRegra(-peso, f"equipamento: candidato e {equip_cand}, descricao indica {alvo}")
```

`src/tdt/config.py` — adicionar chave em `pesos_regras` (dentro do `field(default_factory=lambda: {...})`):
```python
            "lado_tensao": 0.08,
            "equipamento": 0.12,
```

Registrar `r_equipamento` no mesmo lugar onde `r3_fase` e as outras regras já estão registradas (a tupla/lista usada por `aplicar_rastreado`/`aplicar` — procurar onde `r3_fase` aparece referenciada fora da própria definição, é nesse registro que `r_equipamento` entra).

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_motor_regras.py -v`
Expected: todos passam.

- [ ] **Step 5: Rodar a suíte completa**

Run: `pytest -v`
Expected: todos passam — nova regra só age quando `equipamento_alvo` está preenchido (default `None`), então registros sem essa informação (maioria dos testes/fixtures existentes) não são afetados.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/motor_regras.py src/tdt/config.py tests/test_motor_regras.py
git commit -m "feat(motor_regras): nova regra r_equipamento penaliza candidato Disjuntor/Seccionadora trocado"
```

---

## Fechamento

- [ ] **Rodar a suíte completa do projeto**

Run: `pytest -v`
Expected: 100% dos testes passam (pré-existentes + os 6 grupos novos).

- [ ] **Revisar os critérios de aceite da spec (seção 5)** um a um, confirmando que cada item tem uma task correspondente já implementada e testada.
