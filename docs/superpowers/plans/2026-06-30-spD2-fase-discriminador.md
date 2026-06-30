# SP-D2 — Fase como discriminador de qualificador — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Quebrar os empates `score_baixo` da GTD V11 causados por fase como
discriminador (não capturada/preservada), sem mexer em scorers de base.

**Architecture:** Três correções pequenas e independentes, cada uma num ponto
já existente do pipeline de normalização/regras — (D2.1) `normalizar`
preserva a letra de fase (A/B/C/N) quando vem logo após o token "FASE", em
vez de removê-la como stopword genérico; (D2.2) `_fase_no_texto` reconhece
também o padrão "‹líder ANSI 2-3 dígitos› ‹fase›" (ex: "50 ABC") sem a
palavra "FASE"; (D2.3) a regra `r3_fase` trata a fase genérica do candidato
(`fase_da_sigla` == `"F"`) como compatível com um alvo multi-fase do texto
(`"ABC"`/`"AB"`/`"BC"`/`"CA"`), não só igualdade estrita.

**Tech Stack:** Python 3.14, pytest 9, dataclasses frozen.

## Global Constraints

- **Não tocar scorers de base** (TF-IDF/vetorial/fuzzy/calibração) nem
  thresholds do roteador — D2 age só em canonização, extração de contexto e
  regra pós-score.
- **Sem falso positivo:** as três mudanças só ADICIONAM sinal onde hoje não
  há nenhum (token perdido, extração ausente, comparação que zera); nunca
  alteram um match/score que hoje já é correto. Divergência explícita entre
  fases específicas continua penalizando como hoje (comportamento do
  `r3_fase` fora do novo branch é preservado).
- **Benchmark como gate:** `PYTHONPATH=src python bench/benchmark.py` —
  `combo(calib-minmax)` sobe ou mantém acc@1 (69%) e decisão, **sem baixar**
  prec@dec (80%).
- **TDD obrigatório:** teste primeiro (RED→GREEN) em cada task.

---

## File Structure

- **Modify** `src/tdt/normalizacao/normalizador.py` — D2.1: helper
  `_eh_letra_fase_apos_fase` + filtro de stopwords em `normalizar()`
  (linha ~406). D2.2: `_fase_no_texto` (linhas 80-89) ganha um 3º padrão.
- **Modify** `src/tdt/motor_regras.py` — D2.3: `r3_fase` (linhas 194-212)
  ganha um branch de compatibilidade genérica×multi-fase.
- **Modify** `tests/test_normalizador.py` — testes de D2.1 e D2.2.
- **Modify** `tests/test_motor_regras.py` — testes de D2.3.

---

### Task 1: D2.1 — canonização preserva letra de fase após "FASE"

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py:397-407` (`normalizar`, +
  novo helper logo acima)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Consumes: `config.stopwords` (já existe, `STOPWORDS_PADRAO` inclui `"A"`).
- Produces: `_eh_letra_fase_apos_fase(tokens: list[str], i: int) -> bool`
  (helper interno, não exportado). `normalizar(texto, config) -> str`
  comportamento estendido (assinatura inalterada).

- [ ] **Step 1: Write the failing test**

Em `tests/test_normalizador.py`, logo após `test_remove_stopwords` (linha 43-44):

```python
def test_preserva_letra_fase_apos_fase_mesmo_sendo_stopword():
    # "A" é stopword (artigo "a"), mas aqui é discriminador de fase -- D2.1
    assert "A" in normalizar("FASE A", CFG).split()


def test_letra_a_isolada_continua_removida_como_stopword():
    # fora do contexto "FASE <letra>", "A" continua sendo o artigo -- sem regressão
    assert normalizar("DJ A BC", CFG) == "DISJUNTOR BANCO CAPACITORES"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_normalizador.py -k "preserva_letra_fase or letra_a_isolada" -v`
Expected: `test_preserva_letra_fase_apos_fase_mesmo_sendo_stopword` FAIL (`"A"`
não está em `"FASE"`); `test_letra_a_isolada_continua_removida_como_stopword`
PASSA (comportamento já existe).

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/normalizacao/normalizador.py`, adicionar o helper logo antes de
`normalizar` (depois de `_fase_no_texto`/`ContextoEstrutural`/
`extrair_contexto_estrutural`, antes da seção `# --- orquestradores ---`):

```python
def _eh_letra_fase_apos_fase(tokens: list[str], i: int) -> bool:
    """D2.1: protege a letra de fase (A/B/C/N) de ser removida como stopword
    genérico quando vem logo após o token "FASE" (ex: "FASE A" -- "A" é
    artigo em STOPWORDS_PADRAO, mas aqui é discriminador de sigla)."""
    return tokens[i] in ("A", "B", "C", "N") and i > 0 and tokens[i - 1] == "FASE"
```

E alterar o filtro de stopwords em `normalizar`:

```python
def normalizar(texto: str | None, config: Config) -> str:
    """Forma normalizada legada: maiúsculas, sem acentos, separadores, abrev,
    stopwords. Preservada para quem já chama (pipeline, benchmark)."""
    if not texto:
        return ""
    texto = _sem_acentos(texto).upper()
    texto = preservar_siglas_especiais(texto)  # N0.5: extrai (sigla) antes do colapso de separadores
    texto = _SEPARADORES.sub(" ", texto)
    tokens = texto.split()
    sem_stop = [
        t for i, t in enumerate(tokens)
        if t not in config.stopwords or _eh_letra_fase_apos_fase(tokens, i)
    ]
    return expandir_abreviacoes(" ".join(sem_stop), config)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_normalizador.py -k "preserva_letra_fase or letra_a_isolada" -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Run full normalizador suite (regressão)**

Run: `PYTHONPATH=src python -m pytest tests/test_normalizador.py -v`
Expected: PASS — nenhum teste existente fixava `"FASE A"` → `"FASE"` (não há
regressão; `canonizar("FASE C", cfg)` continua `"FASE C"` por já ser o
comportamento atual).

- [ ] **Step 6: Commit**

```bash
git add src/tdt/normalizacao/normalizador.py tests/test_normalizador.py
git commit -m "fix(normalizador): preserva letra de fase apos 'FASE' na canonizacao (SP-D2.1)"
```

---

### Task 2: D2.2 — extração reconhece "‹líder ANSI› ‹fase›" sem a palavra "FASE"

**Files:**
- Modify: `src/tdt/normalizacao/normalizador.py:80-89` (`_fase_no_texto`)
- Test: `tests/test_normalizador.py`

**Interfaces:**
- Consumes: `FASES` (já existe, linha 72).
- Produces: `_fase_no_texto(tokens: list[str]) -> tuple[str | None, str | None]`
  (assinatura inalterada, comportamento estendido). Usado por
  `extrair_contexto_estrutural`, que continua devolvendo
  `(texto_remanescente: str, ContextoEstrutural)` com `.fase` populado.

- [ ] **Step 1: Write the failing test**

Em `tests/test_normalizador.py`, logo após `test_extrai_fase_trifasico`
(linha 288-290), antes de `test_sem_fase_no_texto`:

```python
def test_extrai_fase_apos_lider_ansi_sem_palavra_fase():
    texto, ctx = extrair_contexto_estrutural("PROTECAO 50 ABC ESTAGIO 1 ATUADO")
    assert ctx.fase == "ABC"
    assert "ABC" not in texto.split()
    assert "50" in texto.split()  # número ANSI preservado, só a fase é removida


def test_extrai_fase_apos_lider_ansi_letra_unica():
    texto, ctx = extrair_contexto_estrutural("PROTECAO 67 N TEMPORIZADO")
    assert ctx.fase == "N"


def test_fase_explicita_tem_prioridade_sobre_padrao_lider_ansi():
    # "FASE <letra>" (padrão já existente) continua tendo prioridade
    texto, ctx = extrair_contexto_estrutural("PROTECAO FASE A 50 ATUADO")
    assert ctx.fase == "A"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_normalizador.py -k "lider_ansi" -v`
Expected: `test_extrai_fase_apos_lider_ansi_sem_palavra_fase` e
`test_extrai_fase_apos_lider_ansi_letra_unica` FALHAM (`ctx.fase is None`);
`test_fase_explicita_tem_prioridade_sobre_padrao_lider_ansi` PASSA (padrão
já existente).

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/normalizacao/normalizador.py`, alterar `_fase_no_texto`:

```python
def _fase_no_texto(tokens: list[str]) -> tuple[str | None, str | None]:
    """Devolve (fase, token_a_remover) ou (None, None)."""
    for i, tok in enumerate(tokens):
        if tok in _FASE_TOKENS:
            return _FASE_TOKENS[tok], tok
    if "FASE" in tokens:
        idx = tokens.index("FASE")
        if idx + 1 < len(tokens) and tokens[idx + 1] in FASES:
            return tokens[idx + 1], tokens[idx + 1]
    # D2.2: "<líder ANSI 2-3 dígitos> <fase>" sem a palavra "FASE" (ex: "50 ABC").
    # Só dispara se os padrões acima (prioritários) não capturaram nada.
    for i, tok in enumerate(tokens):
        if tok.isdigit() and len(tok) in (2, 3) and i + 1 < len(tokens) and tokens[i + 1] in FASES:
            return tokens[i + 1], tokens[i + 1]
    return None, None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_normalizador.py -k "lider_ansi" -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Run full normalizador suite (regressão)**

Run: `PYTHONPATH=src python -m pytest tests/test_normalizador.py -v`
Expected: PASS — todos os testes de `extrair_contexto_estrutural` existentes
continuam passando (ex.: `test_extrai_barra_principal`,
`test_sem_id_de_equipamento_nao_extrai_nada`).

- [ ] **Step 6: Commit**

```bash
git add src/tdt/normalizacao/normalizador.py tests/test_normalizador.py
git commit -m "feat(normalizador): reconhece fase apos lider ANSI sem palavra FASE (SP-D2.2)"
```

---

### Task 3: D2.3 — `r3_fase` trata fase genérica como compatível com multi-fase

**Files:**
- Modify: `src/tdt/motor_regras.py:194-212` (`r3_fase`)
- Test: `tests/test_motor_regras.py`

**Interfaces:**
- Consumes: `fase_da_sigla(sigla) -> str | None` (inalterada, devolve `"F"`
  pra fase pura genérica). `Contexto.de(rec)` (inalterado).
- Produces: `r3_fase(rec, cand, ctx, cfg) -> AjusteRegra` (assinatura
  inalterada, comportamento estendido).

- [ ] **Step 1: Write the failing test**

Em `tests/test_motor_regras.py`, logo após `test_r3_neutro_favorece_n_penaliza_fase_pura`
(linha 87-91), antes do comentário `# --- R4: estágio ---`:

```python
def test_r3_fase_generica_compativel_com_multifase_do_texto():
    # "50 ABC" extrai fase="ABC" (D2.2); 50F1 (genérica) compatível com ABC,
    # 50_1 (sem fase) não recebe bônus -- desempata na direção certa.
    rec = _rec("PROTECAO 50 ABC ESTAGIO 1", eletrico=Eletrico(fase="ABC"))
    cands = [Candidato("50_1", 0.74, "mesclado"), Candidato("50F1", 0.74, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "50F1"


def test_r3_fase_especifica_explicita_vence_variante_generica():
    # alvo de fase específica (ex "A") -- candidato genérico (F) NÃO ganha o
    # novo bônus (só multi-fase); comportamento pré-D2.3 preservado.
    rec = _rec("PROTECAO FASE A", eletrico=Eletrico(fase="A"))
    cands = [Candidato("FA", 0.70, "mesclado"), Candidato("50F1", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "FA"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_motor_regras.py -k "fase_generica or fase_especifica_explicita" -v`
Expected: `test_r3_fase_generica_compativel_com_multifase_do_texto` FALHA
(`50_1` e `50F1` empatam em 0.74, ordem indefinida/estável não garante
`50F1` primeiro); `test_r3_fase_especifica_explicita_vence_variante_generica`
PASSA (comportamento já existente, `"F" != "A"` já penaliza).

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/motor_regras.py`, alterar `r3_fase`:

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
    if fase_cand == "F" and alvo in ("ABC", "AB", "BC", "CA"):
        # D2.3: sigla de fase pura genérica (ex: 50F1) é compatível com um
        # alvo multi-fase do texto (ex: "50 ABC") -- não é divergência, é a
        # mesma generalidade. Não estende a fase específica única (A/B/C/N):
        # a sigla com letra explícita já compara exato e deve prevalecer.
        return AjusteRegra(peso, f"fase: candidato genérico compatível com {alvo}")
    if fase_cand == alvo:
        return AjusteRegra(peso, f"fase: candidato e texto em {alvo}")
    return AjusteRegra(-peso, f"fase: candidato {fase_cand} diverge de {alvo}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_motor_regras.py -k "fase_generica or fase_especifica_explicita" -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Run full motor_regras suite (regressão)**

Run: `PYTHONPATH=src python -m pytest tests/test_motor_regras.py -v`
Expected: PASS — todos os testes de R1-R6/equipamento existentes continuam
passando (`test_r3_neutro_favorece_n_penaliza_fase_pura` inclusive, já que o
novo branch só dispara quando `fase_cand == "F"`, e `"51F"` nesse teste tem
`fase_da_sigla("51F")` — conferir que não conflita).

- [ ] **Step 6: Commit**

```bash
git add src/tdt/motor_regras.py tests/test_motor_regras.py
git commit -m "feat(motor_regras): r3_fase trata fase generica compativel com multi-fase (SP-D2.3)"
```

---

### Task 4: Validação integrada — suite, benchmark e TDT real

**Files:** nenhum (verificação).

- [ ] **Step 1: Suite completa**

Run: `PYTHONPATH=src python -m pytest -q`
Expected: PASS (todos os testes existentes + os 7 novos desta spec).

- [ ] **Step 2: Benchmark (gate)**

Run: `PYTHONPATH=src python bench/benchmark.py`
Expected: `combo(calib-minmax)` com acc@1 ≥ 69% e prec@dec ≥ 80% (sobe ou
mantém — D2 só adiciona sinal de desempate, nunca remove).

- [ ] **Step 3: Conferir na GTD V11 — empates de fase decidem, ambiguidade real continua em revisão**

Run:
```bash
PYTHONPATH=src python - <<'PY'
import warnings, logging
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
from collections import Counter
from tdt.pipeline import executar
from tdt.config import Config
from tdt.defaults import DEFAULT_TEMPLATE
from tdt.dados.encoder import criar_encoder
cfg = Config(); enc = criar_encoder(cfg.modelo_embedding)
r, _ = executar("docs/GTD - Lista de Pontos V11.xlsx", DEFAULT_TEMPLATE,
    "docs/Pontos Padrao ADMS_v2.xlsx", config=cfg, encoder=enc, subestacao="GTD", modo="nao-homogeneo")
siglas = {rec.sigla_sinal for rec in r.lista.registros}
print("decididos:", len(r.lista.registros))
print("revisao:", dict(Counter(it.motivo for it in r.revisao)))
print("score_baixo:", sum(1 for it in r.revisao if it.motivo == "score_baixo"))
print("\n-- siglas alvo do fix (esperado: decidida) --")
for s in ("FA", "PB", "FC", "50F1", "50_1", "67F1", "67_1", "67F2", "67_2"):
    print(f"  {s}: {'decidida' if s in siglas else 'AINDA EM REVISAO'}")
print("\n-- ambiguidade de dado, fora de escopo (esperado: continua em revisao) --")
for s in ("81IE1", "81E1", "79_EXC", "79_INC"):
    print(f"  {s}: {'decidida (inesperado!)' if s in siglas else 'continua em revisao (esperado)'}")
PY
```
Expected: `score_baixo` cai em relação ao baseline pré-D2 (590); `decididos`
sobe em relação ao baseline pós-SP-C (1029). As siglas-alvo (`FA`, `PB`,
`FC`, `50F1`, `50_1`, `67F1`, `67_1`, etc.) aparecem `"decidida"`. As siglas
de ambiguidade real de dado (`81IE1`, `81E1`, `79_EXC`, `79_INC`) continuam
`"continua em revisao (esperado)"` — confirma que o fix é cirúrgico e não
força decisão onde a ambiguidade é genuína.

- [ ] **Step 4: (sem commit — verificação)**

Se quiser versionar o `OUTPUT_TDT.xlsx` regenerado, fazer no fechamento
conjunto de B/C/D, não aqui.

---

## Self-Review (preenchido)

- **Cobertura do spec:** D2.1 (Task 1) ✓; D2.2 (Task 2) ✓; D2.3 (Task 3) ✓;
  validação contra TDT real + benchmark (Task 4) ✓. Critérios de aceite 1-6
  cobertos.
- **`fase_da_sigla` intacta** (consistente com a Global Constraint de não
  tocar scorers/regras-base fora do escopo): só `r3_fase` é alterada, e só
  no branch novo — o resto da função (incluindo o caso `fase_cand is None`
  e a divergência específica) é preservado byte a byte.
- **Placeholders:** nenhum — todo passo traz código real, teste real e
  comando com saída esperada.
- **Consistência de tipos:** `_eh_letra_fase_apos_fase(list[str], int) -> bool`;
  `_fase_no_texto(list[str]) -> tuple[str | None, str | None]` (assinatura
  inalterada); `r3_fase(rec, cand, ctx, cfg) -> AjusteRegra` (assinatura
  inalterada). Nomes batem entre tasks e com o código atual (conferidos por
  leitura direta do arquivo antes de escrever cada task).
- **Ordem de prioridade preservada:** D2.2 só dispara como 3º fallback em
  `_fase_no_texto` (depois de `_FASE_TOKENS` e do padrão `"FASE <letra>"`),
  testado explicitamente (`test_fase_explicita_tem_prioridade_sobre_padrao_lider_ansi`).
  D2.3 só dispara pra `fase_cand == "F"` e `alvo` multi-fase, testado
  explicitamente que fase específica não é afetada
  (`test_r3_fase_especifica_explicita_vence_variante_generica`).
- **Escopo deferido (consistente com a spec):** tabela de estágio/
  temporização, heurística "sem qualificador prefere sem sufixo",
  `81IE1`/`81E1` e `79_EXC`/`79_INC` (ambiguidade de dado/fonte) — nenhuma
  task tenta resolvê-los; Task 4 Step 3 confirma explicitamente que
  continuam em revisão.
