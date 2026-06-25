# SP5 — Correção de Classificação + Melhorias de Revisão — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir a classificação discreto/analógico (hoje quase tudo cai em "Discrete"), adicionar GPU opcional no encoder, filtros/ordenação na tela de revisão, um relatório de auditoria além da TDT, e corrigir a pasta default dos diálogos de arquivo.

**Architecture:** Mudanças cirúrgicas em módulos já existentes do pipeline SP1/SP4 (`estruturador.py`, `analise_colunas.py`, `config.py`, `pipeline.py`, `dados/indice_vetorial.py`, `dados/encoder.py`) e da UI PySide6 (`ui/tela_revisao.py`, `ui/tela_inicial.py`, `ui/tela_config.py`). Nenhuma dependência nova.

**Tech Stack:** Python, openpyxl, FAISS, sentence-transformers, PySide6, pytest.

## Global Constraints

- Spec de origem: `docs/superpowers/specs/2026-06-24-sp5-correcao-classificacao-e-revisao-design.md` — qualquer dúvida de critério de aceite, checar lá.
- Sem dependências novas (tudo já está no `pyproject`/`requirements`).
- TDD: escrever o teste falhando antes da implementação, em todas as tasks.
- Testes existentes (170+) continuam verdes — rodar a suíte completa ao final de cada Track.
- Commits pequenos e frequentes, um por task (ou por step de implementação dentro da task, quando fizer sentido).

---

## Mapa de Tracks (para dispatch paralelo)

| Track | Tasks | Independência |
|---|---|---|
| **A — Classificação** | 1, 2, 3, 4, 5, 6 | Sequencial entre si (task N depende de N-1). Independente das outras tracks. |
| **B — GPU Encoder** | 7 | Totalmente independente. |
| **C — Filtro/Ordenação Revisão** | 8 | Totalmente independente. |
| **D — Relatório de Auditoria** | 9 | Depende apenas de contratos existentes — independente das outras. |
| **E — Pasta Default File Picker** | 10 | Totalmente independente. |

As 5 tracks podem ser despachadas em paralelo (um agente por track). Dentro da Track A, as tasks são sequenciais.

---

## Track A — Classificação Discreto/Analógico

### Task 1: Vocabulário de tipo compartilhado (`vocabulario_tipo.py`)

**Files:**
- Create: `src/tdt/vocabulario_tipo.py`
- Modify: `src/tdt/estruturador.py:26-28` (remove `_ANALOG`/`_COMANDO`/`_DISCRETO` locais, importa do novo módulo)
- Modify: `src/tdt/analise_colunas.py:26-29` (idem)
- Test: `tests/test_vocabulario_tipo.py`

**Interfaces:**
- Produces: `from tdt.vocabulario_tipo import ANALOG, COMANDO, DISCRETO, CODIGOS_TIPO, classificar` — usado pelas Tasks 2 e 3.
  - `classificar(texto: str) -> tuple[str, str] | None` — mesma assinatura/comportamento do `_classificar` atual de `estruturador.py`, mais o reconhecimento de código curto (`A`/`C`/`D`) por igualdade exata.
  - `CODIGOS_TIPO: dict[str, tuple[str, str]] = {"A": ("Analog", "Input"), "C": ("Discrete", "Output"), "D": ("Discrete", "Input")}`

- [ ] **Step 1: Escrever o teste falhando**

```python
# tests/test_vocabulario_tipo.py
from tdt.vocabulario_tipo import classificar


def test_classifica_palavra_completa_analogica():
    assert classificar("Analógicas Módulo AT") == ("Analog", "Input")


def test_classifica_palavra_completa_comando():
    assert classificar("Comandos Módulo AT") == ("Discrete", "Output")


def test_classifica_palavra_completa_digital():
    assert classificar("Digitais (Controle)") == ("Discrete", "Input")


def test_classifica_codigo_curto_exato():
    assert classificar("A") == ("Analog", "Input")
    assert classificar("C") == ("Discrete", "Output")
    assert classificar("D") == ("Discrete", "Input")


def test_codigo_curto_nao_casa_por_substring():
    # "DISJUNTOR" não é o código "D" — igualdade exata, não substring
    assert classificar("DISJUNTOR") is None


def test_texto_sem_pista_retorna_none():
    assert classificar("ALARME GENERICO") is None
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_vocabulario_tipo.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tdt.vocabulario_tipo'`

- [ ] **Step 3: Implementar**

```python
# src/tdt/vocabulario_tipo.py
"""Vocabulário de classificação Discreto/Analógico/Comando, compartilhado por
`estruturador.py` (linha a linha / marcador de seção) e `analise_colunas.py`
(detecção de coluna "Tipo"). Fonte única — evita duas cópias divergentes.
"""

from __future__ import annotations

import unicodedata

ANALOG = ("ANALOGIC", "MEDIDA", "MEDICAO", "GRANDEZA")
COMANDO = ("COMANDO", "CONTROLE", "TELECOMANDO")
DISCRETO = ("DIGITAL", "DIGITAIS", "DISCRET", "SINALIZ", "STATUS", "ESTADO", "INDICAC")
VOCAB = ANALOG + COMANDO + DISCRETO

# Código curto de 1 letra usado em algumas planilhas na coluna "Tipo".
# Igualdade exata (não substring) — "D" não deve casar com "DISJUNTOR".
CODIGOS_TIPO: dict[str, tuple[str, str]] = {
    "A": ("Analog", "Input"),
    "C": ("Discrete", "Output"),
    "D": ("Discrete", "Input"),
}


def norm(v) -> str:
    if v is None:
        return ""
    s = "".join(
        c for c in unicodedata.normalize("NFKD", str(v)) if not unicodedata.combining(c)
    )
    return " ".join(s.upper().split())


def classificar(texto) -> tuple[str, str] | None:
    n = norm(texto)
    if n in CODIGOS_TIPO:
        return CODIGOS_TIPO[n]
    if any(k in n for k in ANALOG):
        return ("Analog", "Input")
    if any(k in n for k in COMANDO):
        return ("Discrete", "Output")
    if any(k in n for k in DISCRETO):
        return ("Discrete", "Input")
    return None
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_vocabulario_tipo.py -v`
Expected: 6 passed

- [ ] **Step 5: Apontar `estruturador.py` e `analise_colunas.py` pro módulo novo**

Em `src/tdt/estruturador.py`, substituir as linhas 26-28 e a função `_classificar`/`_norm` locais:
```python
from tdt.vocabulario_tipo import classificar as _classificar, norm as _norm
```
(remove as definições locais de `_ANALOG`, `_COMANDO`, `_DISCRETO`, `_norm`, `_classificar`.)

Em `src/tdt/analise_colunas.py`, substituir as linhas 26-29:
```python
from tdt.vocabulario_tipo import VOCAB as _TIPO_VOCAB
```
(remove `_ANALOG`, `_COMANDO`, `_DISCRETO`, `_TIPO_VOCAB` locais — mantém o nome `_TIPO_VOCAB` pra não tocar no resto do arquivo agora.)

- [ ] **Step 6: Rodar toda a suíte de regressão da Track A até aqui**

Run: `pytest tests/test_estruturador.py tests/test_analise_colunas.py tests/test_vocabulario_tipo.py -v`
Expected: todos passam (nenhuma mudança de comportamento ainda — só extração)

- [ ] **Step 7: Commit**

```bash
git add src/tdt/vocabulario_tipo.py src/tdt/estruturador.py src/tdt/analise_colunas.py tests/test_vocabulario_tipo.py
git commit -m "refactor(tdt): extrai vocabulário de tipo compartilhado + reconhece código curto A/C/D"
```

---

### Task 2: `analise_colunas.py` detecta coluna "Tipo" por código curto

**Files:**
- Modify: `src/tdt/analise_colunas.py:134-144` (`_col_tipo`)
- Test: `tests/test_analise_colunas.py`

**Interfaces:**
- Consumes: `tdt.vocabulario_tipo.CODIGOS_TIPO`, `norm` (Task 1).
- Produces: `_col_tipo` continua com a mesma assinatura `(rows, inicio, ncols) -> int | None`, usado por `analisar()` já existente — nenhuma mudança de interface externa.

- [ ] **Step 1: Escrever o teste falhando**

```python
# adicionar em tests/test_analise_colunas.py

def test_tipo_por_codigo_curto():
    rows = [
        ("h0", "h1", "Descricao", "Tipo", "Addr"),
        ("01F1", "LT_GTA", "FALHA COMUNICACAO", "D", "10"),
        ("01F1", "LT_GTA", "DISJUNTOR ABERTO", "C", "11"),
        ("01F1", "LT_GTA", "CORRENTE FASE A", "A", "12"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert mapa.colunas["tipo"] == 3


def test_tipo_por_codigo_curto_nao_pega_coluna_de_fase():
    # fase trifásica A/B/C — não deve ser confundida com código de tipo
    rows = [
        ("h0", "h1", "Descricao", "Fase", "Addr"),
        ("01F1", "LT_GTA", "CORRENTE FASE A", "A", "10"),
        ("01F1", "LT_GTA", "CORRENTE FASE B", "B", "11"),
        ("01F1", "LT_GTA", "CORRENTE FASE C", "C", "12"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert "tipo" not in mapa.colunas
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_analise_colunas.py -v -k codigo_curto`
Expected: `test_tipo_por_codigo_curto` FAIL (coluna não detectada — score 0 pro vocabulário de palavra completa); `test_tipo_por_codigo_curto_nao_pega_coluna_de_fase` passa por acidente (ainda não implementamos detecção de código, então nenhuma coluna é pega) — confirmar que falha é só no primeiro.

- [ ] **Step 3: Implementar**

```python
# src/tdt/analise_colunas.py — substituir _col_tipo (linhas 134-144)
from tdt.vocabulario_tipo import CODIGOS_TIPO  # junto aos outros imports do módulo


def _col_tipo(rows, inicio, ncols) -> int | None:
    melhor, melhor_score = None, 0.0
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        if not vals:
            continue
        normalizados = [_norm(v) for v in vals]
        casam_palavra = sum(1 for n in normalizados if any(k in n for k in _TIPO_VOCAB))
        score_palavra = casam_palavra / len(vals)

        distintos = set(normalizados)
        score_codigo = 0.0
        if distintos and distintos.issubset(CODIGOS_TIPO.keys()) and len(distintos) >= 2:
            casam_codigo = sum(1 for n in normalizados if n in CODIGOS_TIPO)
            score_codigo = casam_codigo / len(vals)

        score = max(score_palavra, score_codigo if score_codigo >= 0.9 else 0.0)
        if score > melhor_score:
            melhor, melhor_score = c, score
    return melhor if melhor_score >= 0.5 else None
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_analise_colunas.py -v`
Expected: todos passam, incluindo os 2 novos e os pré-existentes (`test_tipo_por_vocabulario` etc. continuam intactos pois `score_palavra` preserva o comportamento antigo).

- [ ] **Step 5: Commit**

```bash
git add src/tdt/analise_colunas.py tests/test_analise_colunas.py
git commit -m "feat(analise_colunas): detecta coluna Tipo por código curto A/C/D sem colidir com fase A/B/C"
```

---

### Task 3: `estruturador.py` classifica por código curto linha a linha

**Files:**
- Modify: `src/tdt/estruturador.py` (já usa `classificar`/`norm` do Task 1 — sem mudança de código aqui, só teste de regressão/cobertura)
- Test: `tests/test_estruturador.py`

**Interfaces:**
- Consumes: `tdt.vocabulario_tipo.classificar` (Task 1) já injetado no Task 1/Step 5.

- [ ] **Step 1: Escrever o teste falhando**

```python
# adicionar em tests/test_estruturador.py

def test_coluna_tipo_codigo_curto_classifica_linha_a_linha():
    rows = [
        ("Descrição", "Tipo", "Endereço"),
        ("Corrente Fase A", "A", "10"),
        ("Disjuntor 52-1 Comando", "C", "11"),
        ("Disjuntor 52-1 Estado", "D", "12"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "tipo": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].tipo_sinal.categoria == "Analog"
    assert recs[0].tipo_sinal.categoria_confiavel is True
    assert recs[1].tipo_sinal.categoria == "Discrete"
    assert recs[1].tipo_sinal.direcao == "Output"
    assert recs[2].tipo_sinal.categoria == "Discrete"
    assert recs[2].tipo_sinal.direcao == "Input"
```

- [ ] **Step 2: Rodar e confirmar que já passa**

Run: `pytest tests/test_estruturador.py -v -k codigo_curto`
Expected: PASS — `_classificar` (agora importado de `vocabulario_tipo.classificar`, Task 1) já reconhece o código exato; este teste é regressão/documentação de que a integração estruturador+vocabulário funciona ponta a ponta, não exige código novo.

Se FALHAR, é sinal de que o Step 5 da Task 1 não foi aplicado corretamente — revisar o import em `estruturador.py` antes de continuar.

- [ ] **Step 3: Rodar toda a suíte do arquivo**

Run: `pytest tests/test_estruturador.py -v`
Expected: todos passam (nenhuma regressão nos testes pré-existentes de marcador de seção).

- [ ] **Step 4: Commit**

```bash
git add tests/test_estruturador.py
git commit -m "test(estruturador): cobre classificação por código curto Tipo (A/C/D) linha a linha"
```

---

### Task 4: Thresholds analógicos calibrados separadamente

**Files:**
- Modify: `src/tdt/config.py:47-48`
- Test: `tests/test_config.py` (criar se não existir)

**Interfaces:**
- Produces: `Config.threshold_pct_analog`, `Config.threshold_gap_analog` com novos defaults — consumido por `pipeline.executar()` (já existente, sem mudança de assinatura).

- [ ] **Step 1: Escrever o teste falhando**

```python
# tests/test_config.py
from tdt.config import Config


def test_thresholds_analogicos_mais_frouxos_que_discretos():
    c = Config()
    assert c.threshold_pct_analog == 0.35
    assert c.threshold_gap_analog == 0.05
    assert c.threshold_pct_analog < c.threshold_pct
    assert c.threshold_gap_analog < c.threshold_gap
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_config.py -v`
Expected: FAIL — `assert 0.45 == 0.35`

- [ ] **Step 3: Implementar**

```python
# src/tdt/config.py — linhas 47-48
    threshold_pct_analog: float = 0.35
    threshold_gap_analog: float = 0.05
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_config.py -v`
Expected: 1 passed

- [ ] **Step 5: Rodar a suíte de pipeline pra checar regressão de calibração**

Run: `pytest tests/test_pipeline.py -v`
Expected: todos passam — os testes existentes de dual-pass fixam thresholds explícitos via `Config(...)`, não dependem do default; se algum falhar, é o teste `test_pipeline_classifica_analogico` (que pode usar `Config()` default) — inspecionar e ajustar a asserção pro novo threshold, documentando por quê no commit.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/config.py tests/test_config.py
git commit -m "fix(config): afrouxa thresholds analógicos (corpus padrão analógico é ~10x menor que o discreto)"
```

---

### Task 5: Centroide de embeddings em `IndiceVetorial`

**Files:**
- Modify: `src/tdt/dados/indice_vetorial.py`
- Test: `tests/test_indice_vetorial.py`

**Interfaces:**
- Produces: `IndiceVetorial.afinidade_centroide(texto: str) -> float` — usado pela Task 6.

- [ ] **Step 1: Escrever o teste falhando**

```python
# adicionar em tests/test_indice_vetorial.py

def test_afinidade_centroide_favorece_corpus_mais_similar():
    disjuntores = [("DJ1", "DISJUNTOR ABERTO"), ("DJ2", "DISJUNTOR FECHADO")]
    correntes = [("IA", "CORRENTE FASE A"), ("IB", "CORRENTE FASE B")]
    idx_disc = IndiceVetorial.construir(disjuntores, _fake_encoder)
    idx_ana = IndiceVetorial.construir(correntes, _fake_encoder)
    afin_disc = idx_disc.afinidade_centroide("DISJUNTOR FECHADO")
    afin_ana = idx_ana.afinidade_centroide("DISJUNTOR FECHADO")
    assert afin_disc > afin_ana


def test_afinidade_centroide_persiste_no_roundtrip(tmp_path):
    sinais = [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA")]
    idx = IndiceVetorial.construir(sinais, _fake_encoder)
    idx.salvar(tmp_path)
    recarregado = IndiceVetorial.carregar(tmp_path, _fake_encoder)
    assert recarregado.afinidade_centroide("DISJUNTOR") == idx.afinidade_centroide("DISJUNTOR")
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_indice_vetorial.py -v -k centroide`
Expected: FAIL — `AttributeError: 'IndiceVetorial' object has no attribute 'afinidade_centroide'`

- [ ] **Step 3: Implementar**

```python
# src/tdt/dados/indice_vetorial.py

class IndiceVetorial:
    def __init__(
        self,
        index,
        siglas: list[str],
        encoder: Encoder,
        hash_: str,
        encoder_consulta: Encoder | None = None,
        centroide: np.ndarray | None = None,
    ):
        self._index = index
        self._siglas = siglas
        self._encoder = encoder
        self._encoder_consulta = encoder_consulta or encoder
        self.hash = hash_
        self._centroide = centroide

    @classmethod
    def construir(cls, sinais, encoder, encoder_consulta=None) -> "IndiceVetorial":
        siglas = [s for s, _ in sinais]
        descricoes = [d for _, d in sinais]
        vecs = _normalizar(encoder(descricoes))
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
        centroide = _normalizar(vecs.mean(axis=0, keepdims=True))
        return cls(index, siglas, encoder, _hash(sinais), encoder_consulta, centroide)

    def afinidade_centroide(self, texto: str) -> float:
        q = _normalizar(self._encoder_consulta([texto]))
        return float((q @ self._centroide.T)[0, 0])

    def salvar(self, diretorio: str | Path) -> None:
        d = Path(diretorio)
        d.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(d / _ARQ_INDEX))
        (d / _ARQ_META).write_text(
            json.dumps(
                {"siglas": self._siglas, "hash": self.hash,
                 "centroide": self._centroide.tolist()},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    @classmethod
    def carregar(cls, diretorio, encoder, encoder_consulta=None) -> "IndiceVetorial":
        d = Path(diretorio)
        index = faiss.read_index(str(d / _ARQ_INDEX))
        meta = json.loads((d / _ARQ_META).read_text(encoding="utf-8"))
        centroide = np.asarray(meta["centroide"], dtype="float32")
        return cls(index, meta["siglas"], encoder, meta["hash"], encoder_consulta, centroide)
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_indice_vetorial.py -v`
Expected: todos passam, incluindo os 2 novos e os 5 pré-existentes.

- [ ] **Step 5: Commit**

```bash
git add src/tdt/dados/indice_vetorial.py tests/test_indice_vetorial.py
git commit -m "feat(indice_vetorial): adiciona centroide do corpus + afinidade_centroide(texto)"
```

---

### Task 6: Desempate gap+centroide no dual-pass

**Files:**
- Modify: `src/tdt/pipeline.py:113-136` (`_classificar_roteado`, nova função `_desempatar_ambiguo`)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `_Scorers.indice.afinidade_centroide(str) -> float` (Task 5); `SignalRecord.candidatos: tuple[Candidato, ...]` (já existente).
- Produces: `_classificar_roteado` mantém a assinatura `(rec, disc, ana, diagnostico) -> tuple[SignalRecord | None, ItemRevisao | None]` — sem mudança de interface externa, só de comportamento interno.

- [ ] **Step 1: Escrever os testes falhando — desempate puro (sem corpus pesado)**

```python
# adicionar em tests/test_pipeline.py
from tdt.contracts import Candidato
from tdt.pipeline import _desempatar_ambiguo, _gap


class _IndiceFake:
    def __init__(self, afinidade):
        self._afinidade = afinidade

    def afinidade_centroide(self, _texto):
        return self._afinidade


class _ScorersFake:
    def __init__(self, afinidade):
        self.indice = _IndiceFake(afinidade)


def _rec_com_candidatos(*scores):
    cands = tuple(Candidato(f"S{i}", s, "tfidf") for i, s in enumerate(scores))
    rec = _rec_incerto()
    return _replace(rec, candidatos=cands, status="decidido", sigla_sinal=cands[0].sigla)


def test_gap_decide_quando_diferenca_e_grande():
    d_disc = _rec_com_candidatos(0.90, 0.40)  # gap 0.50
    d_ana = _rec_com_candidatos(0.55, 0.50)   # gap 0.05
    vencedor = _desempatar_ambiguo(d_disc, d_ana, _ScorersFake(0.0), _ScorersFake(0.0), "x")
    assert vencedor is d_disc


def test_centroide_decide_quando_gap_empata():
    d_disc = _rec_com_candidatos(0.60, 0.55)  # gap 0.05
    d_ana = _rec_com_candidatos(0.62, 0.58)   # gap 0.04 — dentro da margem (0.03)
    vencedor = _desempatar_ambiguo(
        d_disc, d_ana, _ScorersFake(afinidade=0.2), _ScorersFake(afinidade=0.8), "x"
    )
    assert vencedor is d_ana


def test_permanece_ambiguo_quando_gap_e_centroide_empatam():
    d_disc = _rec_com_candidatos(0.60, 0.55)
    d_ana = _rec_com_candidatos(0.62, 0.58)
    vencedor = _desempatar_ambiguo(
        d_disc, d_ana, _ScorersFake(afinidade=0.5), _ScorersFake(afinidade=0.5), "x"
    )
    assert vencedor is None


def test_gap_de_candidato_unico_e_o_proprio_score():
    rec = _rec_com_candidatos(0.90)
    assert _gap(rec) == 0.90
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_pipeline.py -v -k "gap_decide or centroide_decide or permanece_ambiguo or gap_de_candidato"`
Expected: FAIL — `ImportError: cannot import name '_desempatar_ambiguo'`

- [ ] **Step 3: Implementar**

```python
# src/tdt/pipeline.py — adicionar antes de _classificar_roteado, e substituir o corpo dela

_MARGEM_DESEMPATE = 0.03


def _gap(rec: SignalRecord) -> float:
    cs = rec.candidatos
    if not cs:
        return 0.0
    if len(cs) == 1:
        return cs[0].score
    return cs[0].score - cs[1].score


def _desempatar_ambiguo(d_disc, d_ana, disc: "_Scorers", ana: "_Scorers", descricao: str):
    """Quando os dois bundles decidem, tenta resolver por gap (mais confiante)
    e, se os gaps forem próximos, pelo centroide do corpus (a quem a
    descrição se aproxima mais). Devolve o vencedor ou None (permanece
    ambíguo -> revisão manual)."""
    gap_disc, gap_ana = _gap(d_disc), _gap(d_ana)
    if abs(gap_disc - gap_ana) > _MARGEM_DESEMPATE:
        return d_disc if gap_disc > gap_ana else d_ana
    afin_disc = disc.indice.afinidade_centroide(descricao)
    afin_ana = ana.indice.afinidade_centroide(descricao)
    if afin_disc == afin_ana:
        return None
    return d_disc if afin_disc > afin_ana else d_ana


def _classificar_roteado(rec, disc: "_Scorers", ana: "_Scorers", diagnostico: bool):
    """Devolve (decidido_ou_None, item_revisao_ou_None).

    Confiável: usa o bundle da própria categoria.
    Incerto: roda os dois; usa o único que decidir; se ambos decidirem,
    tenta desempatar (gap, depois centroide); só vai pra revisão se também
    o desempate for inconclusivo.
    """
    if rec.tipo_sinal.categoria_confiavel:
        bundle = disc if rec.tipo_sinal.categoria == "Discrete" else ana
        d = _classificar_sinal(rec, bundle, diagnostico=diagnostico)
        if d.status == "decidido":
            return d, None
        return None, ItemRevisao(d, motivo="score_baixo", candidatos_sugeridos=d.candidatos[:3])

    d_disc = _classificar_sinal(rec, disc, diagnostico=diagnostico)
    d_ana = _classificar_sinal(rec, ana, diagnostico=diagnostico)
    ok_disc = d_disc.status == "decidido"
    ok_ana = d_ana.status == "decidido"

    if ok_disc and ok_ana:
        vencedor = _desempatar_ambiguo(d_disc, d_ana, disc, ana, rec.descricoes.normalizada)
        if vencedor is not None:
            return vencedor, None
        cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
        return None, ItemRevisao(d_disc, motivo="categoria_ambigua", candidatos_sugeridos=cands)
    if ok_disc and not ok_ana:
        return d_disc, None
    if ok_ana and not ok_disc:
        return d_ana, None
    cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
    return None, ItemRevisao(d_disc, motivo="score_baixo", candidatos_sugeridos=cands)
```

- [ ] **Step 4: Rodar e confirmar sucesso dos testes novos**

Run: `pytest tests/test_pipeline.py -v -k "gap_decide or centroide_decide or permanece_ambiguo or gap_de_candidato"`
Expected: 4 passed

- [ ] **Step 5: Rodar a suíte completa de `test_pipeline.py` e ajustar o teste de integração ambíguo se necessário**

Run: `pytest tests/test_pipeline.py -v`

`test_classificar_roteado_categoria_incerta_ambos_decidem_categoria_ambigua` (linha ~179) agora passa pelo desempate real com corpus de verdade. Duas saídas possíveis:

- **Continua ambíguo** (gaps próximos e centroides empatados/próximos pro texto "CORRENTE FASE A" nessa fixture específica): nenhuma mudança necessária.
- **Resolve automaticamente** (`decidido is not None`): é o comportamento pretendido pelo SP5 (menos revisão manual). Trocar a asserção:
  ```python
  decidido, item = _classificar_roteado(rec, disc, ana, diagnostico=False)
  assert decidido is not None
  assert item is None
  # categoria resolvida pelo desempate (gap ou centroide) — ver _desempatar_ambiguo
  assert decidido.tipo_sinal.categoria in ("Discrete", "Analog")
  ```
  Documentar no commit qual dos dois caminhos foi observado.

Se algum outro teste de `test_pipeline.py` quebrar (ex. `test_pipeline_classifica_analogico`, que roda `executar()` ponta-a-ponta), inspecionar a saída e confirmar que a mudança é uma melhora esperada (sinal que antes ia pra revisão agora decide) antes de ajustar a asserção — não silenciar falha sem entender a causa.

- [ ] **Step 6: Rodar a suíte completa do projeto**

Run: `pytest -v`
Expected: todos passam.

- [ ] **Step 7: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline.py
git commit -m "feat(pipeline): desempate gap+centroide quando os dois bundles decidem no dual-pass"
```

---

## Track B — GPU no Encoder

### Task 7: `device` opcional no `SentenceTransformer`

**Files:**
- Modify: `src/tdt/dados/encoder.py`
- Test: `tests/test_encoder.py` (criar se não existir)

**Interfaces:**
- Produces: `criar_encoder(modelo, prefixo="", device=None)` — chamadores existentes (`pipeline.py`, `ui/worker.py`, `cli.py`) continuam funcionando sem passar `device` (default `None` preserva comportamento atual).

- [ ] **Step 1: Escrever o teste falhando**

```python
# tests/test_encoder.py
from unittest.mock import patch

from tdt.dados.encoder import criar_encoder


def test_criar_encoder_aceita_device_none_sem_quebrar():
    with patch("tdt.dados.encoder.SentenceTransformer") as MockST:
        MockST.return_value.encode.return_value = [[0.1, 0.2]]
        encode = criar_encoder("modelo-fake", device=None)
        encode(["texto"])
        MockST.assert_called_once_with("modelo-fake", device=None)


def test_criar_encoder_propaga_device_explicito():
    with patch("tdt.dados.encoder.SentenceTransformer") as MockST:
        MockST.return_value.encode.return_value = [[0.1, 0.2]]
        encode = criar_encoder("modelo-fake", device="cuda")
        encode(["texto"])
        MockST.assert_called_once_with("modelo-fake", device="cuda")
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_encoder.py -v`
Expected: FAIL — `_modelo()` hoje não aceita `device`, e `SentenceTransformer` é importado dentro da função (não no módulo), então `patch("tdt.dados.encoder.SentenceTransformer")` falha com `AttributeError` até o import ser movido pro topo do módulo.

- [ ] **Step 3: Implementar**

```python
# src/tdt/dados/encoder.py
from __future__ import annotations

from functools import lru_cache

import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer


@lru_cache(maxsize=2)
def _modelo(nome: str, device: str | None):
    return SentenceTransformer(nome, device=device)


def criar_encoder(modelo: str, prefixo: str = "", device: str | None = None):
    """Devolve um callable ``list[str] -> ndarray(float32)``.

    ``prefixo`` para modelos e5/instruct (ex.: "query: " / "passage: ").
    ``device`` força "cpu"/"cuda"; ``None`` deixa o sentence-transformers
    autodetectar (usa GPU se disponível, sem regressão em máquina sem GPU).
    """

    def encode(textos: list[str]) -> np.ndarray:
        ts = [prefixo + t for t in textos] if prefixo else textos
        return np.asarray(_modelo(modelo, device).encode(ts), dtype="float32")

    return encode


@lru_cache(maxsize=2)
def _cross_encoder(nome: str):
    return CrossEncoder(nome)


def criar_scorer_cross_encoder(modelo: str):
    """Devolve um scorer ``list[(query, doc)] -> list[float]`` para o reranker."""

    def scorer(pares: list[tuple[str, str]]) -> list[float]:
        return [float(s) for s in _cross_encoder(modelo).predict(pares)]

    return scorer
```

Mover os imports de `sentence_transformers` pro topo do módulo é necessário pro `patch()` do teste funcionar (`unittest.mock.patch` precisa que o nome esteja no namespace do módulo no momento do patch) — isso muda o comentário do ponytail original ("lazy-load"), mas o `lru_cache` já evita reinstanciar o modelo, então o custo de import antecipado é desprezível comparado ao load do modelo em si.

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_encoder.py -v`
Expected: 2 passed

- [ ] **Step 5: Rodar a suíte completa pra checar quem mais usa `criar_encoder`**

Run: `pytest -v -k "encoder or pipeline or cross_encoder"`
Expected: todos passam — nenhum chamador existente passa `device` hoje, então o default `None` preserva 100% do comportamento atual.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/dados/encoder.py tests/test_encoder.py
git commit -m "feat(encoder): expõe device opcional no SentenceTransformer (usa GPU automaticamente se disponível)"
```

---

## Track C — Filtro e Ordenação na Tela de Revisão

### Task 8: `ProxyRevisao` (QSortFilterProxyModel) + wiring

**Files:**
- Create: `src/tdt/ui/proxy_revisao.py`
- Modify: `src/tdt/ui/tela_revisao.py` (`carregar`, `_linha_mudou`, `__init__`)
- Modify: `src/tdt/ui/delegate_sinal.py` (recebe o proxy, mapeia índice)
- Test: `tests/test_ui_proxy_revisao.py`

**Interfaces:**
- Consumes: `ModeloSinais.COLUNAS` (já existente, `ui/modelo_tabela.py`).
- Produces: `ProxyRevisao.setEsconderDecididos(bool)`, herda `setFilterFixedString`/`setFilterKeyColumn` de `QSortFilterProxyModel` (Qt nativo) — consumido por `tela_revisao.py` e indiretamente por `delegate_sinal.py` via `mapToSource`.

- [ ] **Step 1: Escrever o teste falhando**

```python
# tests/test_ui_proxy_revisao.py
from dataclasses import replace

import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
from tdt.ui.proxy_revisao import ProxyRevisao

pytest.importorskip("PySide6")


def _rec(id_, status, bruta):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(bruta, bruta),
        status=status,
    )


def _estado_com(registros):
    e = AppState()
    e.registros = registros
    return e


def test_esconder_decididos_filtra_linhas():
    estado = _estado_com([
        _rec("1", "decidido", "A"),
        _rec("2", "revisao", "B"),
    ])
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.setEsconderDecididos(True)
    assert proxy.rowCount() == 1
    col_status = ModeloSinais.COLUNAS.index("Status")
    assert proxy.index(0, col_status).data() == "revisao"


def test_esconder_decididos_desativado_mostra_tudo():
    estado = _estado_com([
        _rec("1", "decidido", "A"),
        _rec("2", "revisao", "B"),
    ])
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.setEsconderDecididos(False)
    assert proxy.rowCount() == 2


def test_map_to_source_aponta_pro_registro_correto_apos_filtro():
    estado = _estado_com([
        _rec("1", "decidido", "A"),
        _rec("2", "revisao", "B"),
    ])
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.setEsconderDecididos(True)
    fonte = proxy.mapToSource(proxy.index(0, 0))
    assert fonte.row() == 1  # registro "2" é o índice 1 na fonte
```

(`pytest.importorskip("PySide6")` segue o padrão já usado pelos outros testes de UI do projeto — checar `tests/test_ui_modelo_tabela.py` antes de implementar pra confirmar se já existe um fixture/marker equivalente e reusar.)

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_ui_proxy_revisao.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tdt.ui.proxy_revisao'`

- [ ] **Step 3: Implementar `ProxyRevisao`**

```python
# src/tdt/ui/proxy_revisao.py
"""Proxy de filtro/ordenação pra tela de revisão — Qt nativo, sem libs novas.

ponytail: filtro de texto usa o QSortFilterProxyModel padrão
(setFilterKeyColumn(-1) busca em todas as colunas); "esconder decididos" é
o único filtro customizado.
"""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel

from tdt.ui.modelo_tabela import ModeloSinais

_COL_STATUS = ModeloSinais.COLUNAS.index("Status")


class ProxyRevisao(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._esconder_decididos = False

    def setEsconderDecididos(self, ativo: bool) -> None:
        self._esconder_decididos = ativo
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._esconder_decididos:
            idx = self.sourceModel().index(source_row, _COL_STATUS, source_parent)
            if self.sourceModel().data(idx) == "decidido":
                return False
        return True
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_ui_proxy_revisao.py -v`
Expected: 3 passed

- [ ] **Step 5: Conectar o proxy em `delegate_sinal.py`**

```python
# src/tdt/ui/delegate_sinal.py — substituir a classe inteira
from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QStyledItemDelegate

from tdt.ui.busca_adms import buscar
from tdt.ui.estado import AppState


class DelegateSinal(QStyledItemDelegate):
    def __init__(self, estado: AppState, modelo, proxy, parent=None):
        super().__init__(parent)
        self._estado = estado
        self._modelo = modelo
        self._proxy = proxy

    def createEditor(self, parent, option, index):
        fonte = self._proxy.mapToSource(index)
        combo = QComboBox(parent)
        combo.setEditable(True)
        siglas: list[str] = []
        rec = self._estado.registros[fonte.row()] if fonte.isValid() else None
        if rec is not None:
            siglas.extend(c.sigla for c in rec.candidatos)
        lp = self._estado.lista_padrao
        if lp is not None:
            for sp in buscar(lp, "", limite=500):
                if sp.sigla not in siglas:
                    siglas.append(sp.sigla)
        combo.addItems(siglas)
        return combo

    def setModelData(self, editor, model, index):
        fonte = self._proxy.mapToSource(index)
        sigla = editor.currentText().strip()
        if sigla:
            self._modelo.definir_sigla(fonte.row(), sigla)
```

- [ ] **Step 6: Conectar o proxy em `tela_revisao.py`**

No `__init__`, adicionar (junto da barra `topo`, antes de `corpo`):
```python
from PySide6.QtWidgets import QCheckBox  # junto dos outros imports de widgets

# ... dentro de __init__, após criar self.tabela:
self.chk_so_revisao = QCheckBox("Mostrar apenas revisão")
self.chk_so_revisao.toggled.connect(self._filtrar_status)
self.ed_filtro = QLineEdit()
self.ed_filtro.setPlaceholderText("Filtrar (todas as colunas)…")
self.ed_filtro.textChanged.connect(self._filtrar_texto)
barra_filtro = QHBoxLayout()
barra_filtro.addWidget(self.chk_so_revisao)
barra_filtro.addWidget(self.ed_filtro, 1)

# ... no layout final:
raiz.addLayout(topo)
raiz.addLayout(barra_filtro)
raiz.addLayout(corpo, 1)
```

Substituir `carregar()` e `_linha_mudou`, e adicionar os dois novos métodos:
```python
def carregar(self) -> None:
    self._modelo = ModeloSinais(self._estado)
    self._proxy = ProxyRevisao(self)
    self._proxy.setSourceModel(self._modelo)
    self._proxy.setFilterKeyColumn(-1)
    self.tabela.setModel(self._proxy)
    self.tabela.setSortingEnabled(True)
    self.tabela.setEditTriggers(QTableView.DoubleClicked)
    col_sinal = ModeloSinais.COLUNAS.index("Sinal")
    self.tabela.setItemDelegateForColumn(
        col_sinal, DelegateSinal(self._estado, self._modelo, self._proxy, self.tabela))
    self.tabela.selectionModel().currentRowChanged.connect(self._linha_mudou)

def _linha_mudou(self, atual, _anterior):
    fonte = self._proxy.mapToSource(atual)
    self._linha = fonte.row()
    self._atualizar_painel()

def _filtrar_status(self, ativo: bool) -> None:
    self._proxy.setEsconderDecididos(ativo)

def _filtrar_texto(self, termo: str) -> None:
    self._proxy.setFilterFixedString(termo)
```

E o import no topo do arquivo:
```python
from tdt.ui.proxy_revisao import ProxyRevisao
```

- [ ] **Step 7: Rodar a suíte de UI**

Run: `pytest tests/test_ui_smoke.py tests/test_ui_modelo_tabela.py tests/test_ui_proxy_revisao.py -v`
Expected: todos passam. Se `test_ui_smoke.py` instanciar `DelegateSinal` diretamente com a assinatura antiga (2 args + parent), ajustar a chamada pra incluir o `proxy` — checar o arquivo antes de assumir.

- [ ] **Step 8: Teste manual obrigatório (não automatizável em CI sem display)**

Rodar a aplicação (`python -m tdt.ui_main` ou o entrypoint usado pelo projeto), carregar um resultado com sinais decididos e em revisão, e confirmar manualmente:
1. Marcar "Mostrar apenas revisão" esconde os decididos.
2. Clicar no cabeçalho de qualquer coluna ordena a tabela.
3. Com a tabela ordenada e/ou filtrada, dar duplo-clique numa célula "Sinal" e trocar a sigla — confirmar que o registro correto (pela descrição bruta exibida) foi editado, não outro.

Esse passo é o que valida o risco principal apontado no design (índice errado após filtro/ordenação) — não pular.

- [ ] **Step 9: Commit**

```bash
git add src/tdt/ui/proxy_revisao.py src/tdt/ui/tela_revisao.py src/tdt/ui/delegate_sinal.py tests/test_ui_proxy_revisao.py
git commit -m "feat(ui): filtro 'esconder decididos' + filtro de texto + ordenação por coluna na tela de revisão"
```

---

## Track D — Relatório de Auditoria

### Task 9: `relatorio_revisao.py` + botão "Gerar TDT" também exporta auditoria

**Files:**
- Create: `src/tdt/relatorio_revisao.py`
- Modify: `src/tdt/ui/tela_revisao.py:_gerar` (linhas ~176-192)
- Test: `tests/test_relatorio_revisao.py`

**Interfaces:**
- Consumes: `SignalRecord`, `ItemRevisao` (já existentes, `contracts.py`).
- Produces: `gerar_relatorio_revisao(registros, revisao, destino) -> Path` — consumido por `tela_revisao.py`.

- [ ] **Step 1: Escrever o teste falhando**

```python
# tests/test_relatorio_revisao.py
import openpyxl

from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Enderecamento, ItemRevisao, Modulo,
    SignalRecord, TipoSinal,
)
from tdt.relatorio_revisao import gerar_relatorio_revisao


def _rec(id_, sigla=None, candidatos=(), diagnostico=None, status="decidido"):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("Disjuntor Aberto", "disjuntor aberto"),
        sigla_sinal=sigla, candidatos=candidatos, status=status,
        diagnostico=diagnostico,
    )


def test_gera_planilha_com_uma_linha_por_sinal(tmp_path):
    cands = (Candidato("DJ", 0.91, "mesclado"), Candidato("SC", 0.40, "mesclado"))
    diag = Diagnostico(scores_por_metodo={"DJ": {"tfidf": 0.9, "vetorial": 0.92, "fuzzy": 0.88}})
    registros = [_rec("S1:1", sigla="DJ", candidatos=cands, diagnostico=diag)]
    revisao = ()

    caminho = gerar_relatorio_revisao(registros, revisao, tmp_path)

    assert caminho.exists()
    wb = openpyxl.load_workbook(caminho)
    ws = wb["Auditoria"]
    assert ws.cell(1, 1).value == "ID Sinal"
    assert ws.cell(2, 1).value == "S1:1"
    assert ws.cell(2, 6).value == "DJ"  # Sigla Decidida
    assert ws.cell(2, 9).value == "DJ"  # Candidato 1


def test_sinal_sem_candidatos_nao_quebra(tmp_path):
    registros = [_rec("S1:2", sigla=None, candidatos=(), status="revisao")]
    revisao = (ItemRevisao(registros[0], motivo="score_baixo"),)

    caminho = gerar_relatorio_revisao(registros, revisao, tmp_path)

    wb = openpyxl.load_workbook(caminho)
    ws = wb["Auditoria"]
    assert ws.cell(2, 8).value == "score_baixo"  # Motivo Revisão
    assert ws.cell(2, 9).value in (None, "")  # sem candidato 1
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_relatorio_revisao.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tdt.relatorio_revisao'`

- [ ] **Step 3: Implementar**

```python
# src/tdt/relatorio_revisao.py
"""Gera Auditoria_Revisao.xlsx: uma linha por sinal com status, sigla
decidida, scores por método e os candidatos descartados — para cruzar com
a TDT na auditoria pós-classificação."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from tdt.contracts import ItemRevisao, SignalRecord

CABECALHO = [
    "ID Sinal", "Descrição Bruta", "Tipo", "Endereço", "Status",
    "Sigla Decidida", "Score Final", "Motivo Revisão",
    "Candidato 1", "Score tfidf 1", "Score vetorial 1", "Score fuzzy 1",
    "Candidato 2", "Score tfidf 2", "Score vetorial 2", "Score fuzzy 2",
    "Candidato 3", "Score tfidf 3", "Score vetorial 3", "Score fuzzy 3",
]


def _scores_metodo(rec: SignalRecord, sigla: str | None) -> tuple[str, str, str]:
    if rec.diagnostico is None or sigla is None:
        return ("", "", "")
    por = rec.diagnostico.scores_por_metodo.get(sigla, {})
    return tuple(
        f"{por[m]:.3f}" if m in por else "" for m in ("tfidf", "vetorial", "fuzzy")
    )


def gerar_relatorio_revisao(
    registros: list[SignalRecord],
    revisao: tuple[ItemRevisao, ...],
    destino: str | Path,
) -> Path:
    motivo_por_id = {it.registro.id: it.motivo for it in revisao}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Auditoria"
    ws.append(CABECALHO)
    for rec in registros:
        linha = [
            rec.id,
            rec.descricoes.bruta,
            f"{rec.tipo_sinal.categoria}/{rec.tipo_sinal.direcao}",
            ";".join(str(i) for i in rec.enderecamento.indices),
            rec.status,
            rec.sigla_sinal or "",
            f"{rec.candidatos[0].score:.3f}" if rec.candidatos else "",
            motivo_por_id.get(rec.id, ""),
        ]
        for c in rec.candidatos[:3]:
            linha.append(c.sigla)
            linha.extend(_scores_metodo(rec, c.sigla))
        linha += [""] * (len(CABECALHO) - len(linha))
        ws.append(linha)
    saida = Path(destino) / "Auditoria_Revisao.xlsx"
    wb.save(str(saida))
    return saida
```

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_relatorio_revisao.py -v`
Expected: 2 passed

- [ ] **Step 5: Conectar ao botão "Gerar TDT"**

```python
# src/tdt/ui/tela_revisao.py — método _gerar, dentro do try, depois de wb.save(...)
from tdt.relatorio_revisao import gerar_relatorio_revisao  # junto dos outros imports

# ... dentro de _gerar(), após `wb.save(str(out_path))`:
revisao = self._estado.resultado.revisao if self._estado.resultado else ()
gerar_relatorio_revisao(self._estado.registros, revisao, output)
QMessageBox.information(self, "Sucesso", f"TDT gerado: {out_path}\nAuditoria: {Path(output) / 'Auditoria_Revisao.xlsx'}")
```

(Essa linha substitui a chamada antiga a `QMessageBox.information` que só mencionava a TDT — não duplicar as duas.)

- [ ] **Step 6: Rodar a suíte de UI**

Run: `pytest tests/test_ui_smoke.py -v`
Expected: passa — se houver um teste que mocka `pipeline.gerar_tdt` e verifica a mensagem exibida, ajustar a string esperada.

- [ ] **Step 7: Commit**

```bash
git add src/tdt/relatorio_revisao.py src/tdt/ui/tela_revisao.py tests/test_relatorio_revisao.py
git commit -m "feat(relatorio): gera Auditoria_Revisao.xlsx junto com a TDT (status, scores e candidatos descartados)"
```

---

## Track E — Pasta Default no File Picker

### Task 10: Defaults compartilhados + fallback nos diálogos

**Files:**
- Create: `src/tdt/defaults.py`
- Modify: `src/tdt/ui/tela_config.py:20-23` (importa de `defaults.py` em vez de definir local; usa fallback nos próprios diálogos da tela de config também — linhas 126-138 tinham o mesmo gap)
- Modify: `src/tdt/ui/tela_inicial.py:108-123`
- Test: `tests/test_ui_defaults.py`

**Interfaces:**
- Produces: `tdt.defaults.DEFAULT_TEMPLATE`, `DEFAULT_LISTA`, `DEFAULT_OUTPUT` (strings de caminho) — consumidos por `tela_inicial.py` e `tela_config.py`.

- [ ] **Step 1: Escrever o teste falhando**

```python
# tests/test_ui_defaults.py
from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT, DEFAULT_TEMPLATE


def test_defaults_apontam_pra_pastas_do_projeto():
    assert DEFAULT_TEMPLATE.endswith("dnp3_template.xlsx")
    assert DEFAULT_LISTA.endswith("Pontos Padrao ADMS_v1.xlsx")
    assert DEFAULT_OUTPUT.endswith("output")
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/test_ui_defaults.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tdt.defaults'`

- [ ] **Step 3: Implementar `defaults.py`**

```python
# src/tdt/defaults.py
"""Caminhos default do projeto (template, lista padrão, output) — usados
como diretório inicial dos diálogos de arquivo na UI, antes da primeira
seleção manual do usuário."""

from __future__ import annotations

from pathlib import Path

_DOCS = Path(__file__).resolve().parents[2] / "docs"

DEFAULT_TEMPLATE = str(_DOCS / "dnp3_template.xlsx")
DEFAULT_LISTA = str(_DOCS / "Pontos Padrao ADMS_v1.xlsx")
DEFAULT_OUTPUT = str(Path(__file__).resolve().parents[2] / "output")
```

Atenção ao número de `.parents[N]`: `tela_config.py` está em `src/tdt/ui/tela_config.py` e usava `parents[3]` a partir desse arquivo. `defaults.py` fica em `src/tdt/defaults.py` — um nível mais raso — então o índice correto é `parents[2]` (confirmar rodando o Step 4 antes de seguir; se o path não resolver pra pasta `docs/` real do projeto, ajustar o índice).

- [ ] **Step 4: Rodar e confirmar sucesso**

Run: `pytest tests/test_ui_defaults.py -v`
Expected: 1 passed

- [ ] **Step 5: Usar os defaults em `tela_inicial.py`**

```python
# src/tdt/ui/tela_inicial.py — adicionar import
from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT

# substituir _escolher_input (linhas 108-116)
def _escolher_input(self):
    atual = self._estado.paths.get("input", "") or DEFAULT_LISTA
    caminho, _ = QFileDialog.getOpenFileName(
        self, "Input .xlsx", dir=atual, filter="Excel (*.xlsx)")
    if not caminho:
        return
    self._estado.paths["input"] = caminho
    self.ed_input.setText(caminho)
    self._popular_sheets(caminho)

# substituir _escolher_output (linhas 118-123)
def _escolher_output(self):
    atual = self._estado.paths.get("output", "") or DEFAULT_OUTPUT
    caminho = QFileDialog.getExistingDirectory(self, "Pasta de output", dir=atual)
    if caminho:
        self._estado.paths["output"] = caminho
        self.ed_output.setText(caminho)
```

- [ ] **Step 6: Usar os defaults em `tela_config.py`**

```python
# src/tdt/ui/tela_config.py — remover as 3 linhas locais (20-23):
#   _DEFAULT_TEMPLATE = ...
#   _DEFAULT_LISTA = ...
#   _DEFAULT_OUTPUT = ...
# substituir pelo import:
from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT, DEFAULT_TEMPLATE

# substituir _escolher (linhas 126-134)
def _escolher(self, chave, is_pasta):
    atual = self._estado.paths.get(chave, "")
    default = {
        "template": DEFAULT_TEMPLATE, "lista_padrao": DEFAULT_LISTA, "output": DEFAULT_OUTPUT,
    }.get(chave, "")
    inicial = atual or default
    if is_pasta:
        caminho = QFileDialog.getExistingDirectory(self, f"Selecionar pasta {chave}", dir=inicial)
    else:
        caminho, _ = QFileDialog.getOpenFileName(
            self, f"Selecionar {chave}", dir=inicial,
            filter="Excel (*.xlsx);;Todos (*)",
        )
    if caminho:
        self._estado.paths[chave] = caminho
        self._atualizar_label(chave)
        self.aplicar()  # persiste imediatamente
```

(`chave == "input"` não tem default próprio — cai em `""`, igual a hoje; só `template`/`lista_padrao`/`output` têm default conhecido.)

- [ ] **Step 7: Rodar a suíte de UI**

Run: `pytest tests/test_ui_smoke.py tests/test_ui_estado.py -v`
Expected: todos passam.

- [ ] **Step 8: Teste manual obrigatório**

Abrir a tela inicial e a tela de configuração numa instância nova (sem `config.toml` prévio) e confirmar que os diálogos de Input/Output/Template/Lista Padrão abrem dentro de `docs/` ou `output/` do projeto, não em outro lugar do Windows.

- [ ] **Step 9: Commit**

```bash
git add src/tdt/defaults.py src/tdt/ui/tela_inicial.py src/tdt/ui/tela_config.py tests/test_ui_defaults.py
git commit -m "fix(ui): diálogos de arquivo abrem na pasta default do projeto quando nada foi selecionado ainda"
```

---

## Fechamento

- [ ] **Rodar a suíte completa do projeto**

Run: `pytest -v`
Expected: 100% dos testes passam (pré-existentes + todos os novos das 10 tasks).

- [ ] **Revisar critérios de aceite da spec (seção 6) um a um**, confirmando que cada item tem uma task correspondente já implementada e testada.
