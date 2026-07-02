# SP-H — Camada de decisão (gap, resgate, pesos) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ou superpowers:executing-plans. TDD. Steps com checkbox.

**Goal:** eliminar gap 0.0 artificial, resgatar zona cinzenta via regras já rastreadas, decidir pesos por experimento, e tornar corretude vs GTD real a métrica primária.

**Architecture:** dedupe por sigla no `roteador._quadrante`; resgate usa os `ajustes` que `motor_regras.aplicar_rastreado` (pipeline.py:243) JÁ produz — passados ao `rotear` como parâmetro opcional; experimento de pesos como script standalone em `bench/` reusando os módulos de scoring.

**Tech Stack:** Python 3.14, pytest, numpy/faiss (bench).

## Global Constraints

- `python -m pytest -q` verde por task; benchmark sem queda de corretude.
- Nenhuma mudança que suba taxa de decisão às custas de corretude (spec §4).
- Ordem: Task 1 (diagnóstico) antes das demais — o dedupe (Task 2) só se o diagnóstico confirmar a hipótese.

---

### Task 1: Diagnóstico do gap nas revisões da LISTA 1

**Files:**
- Create: `bench/diag_gap_revisao.py`
- Create: `bench/resultados/spH_diag_gap.txt` (gerado, commitado)

- [ ] Step 1: script que lê a auditoria real e histograma o gap:

```python
"""Distribui o gap (c1-c2) das revisões score_baixo; conta gap-zero com
candidatos de MESMA sigla (duplicata da LP) vs siglas distintas.
Uso: python bench/diag_gap_revisao.py "output/LISTA 1 - GTD/Auditoria_Revisao.xlsx"
"""
import sys
from collections import Counter
import openpyxl

wb = openpyxl.load_workbook(sys.argv[1], read_only=True)
ws = wb["Auditoria"]
rows = list(ws.iter_rows(values_only=True))
hdr = {h: i for i, h in enumerate(rows[0])}
hist, mesma_sigla, distintas = Counter(), 0, 0
for r in rows[1:]:
    if r[hdr["Status"]] != "revisao" or r[hdr["Motivo Revisão"]] != "score_baixo":
        continue
    c1, c2 = r[hdr["Candidato 1"]], r[hdr["Candidato 2"]]
    s1 = max(x for x in (r[hdr["Score tfidf 1"]], r[hdr["Score vetorial 1"]], r[hdr["Score fuzzy 1"]]) if x is not None)
    s2 = max((x for x in (r[hdr["Score tfidf 2"]], r[hdr["Score vetorial 2"]], r[hdr["Score fuzzy 2"]]) if x is not None), default=0.0)
    gap = round(s1 - s2, 2)
    hist[gap] += 1
    if c1 and c2 and str(c1).upper() == str(c2).upper():
        mesma_sigla += 1
    else:
        distintas += 1
print("mesma_sigla(c1==c2):", mesma_sigla, "| distintas:", distintas)
for g, n in sorted(hist.items()):
    print(f"gap={g}: {n}")
```

(os scores por método na auditoria são proxy do gap mesclado; se a auditoria estendida da SP-J já existir com a coluna gap, usar direto.)

- [ ] Step 2: rodar, salvar em `bench/resultados/spH_diag_gap.txt`, anotar conclusão no fim: hipótese mesma-sigla confirmada? outras fontes de gap-zero?
- [ ] Step 3: commit `test(spH): diagnostico distribuicao de gap nas revisoes`

---

### Task 2: Dedupe de candidatos por sigla antes do gap

**Files:**
- Modify: `src/tdt/roteador.py` (`_quadrante`, e o cálculo de gap do passo consenso)
- Test: `tests/test_roteador.py`

**Interfaces:**
- Produces: `_dedupe_por_sigla(cands: list[Candidato]) -> list[Candidato]` — mantém o melhor score de cada sigla, ordem por score desc.

- [ ] Step 1: teste RED

```python
def test_gap_ignora_duplicata_da_mesma_sigla(config):
    rec = _rec_com_candidatos([("79", 0.90), ("79", 0.89), ("79OK", 0.50)])
    out = rotear(rec, config)
    assert out.status == "decidido"      # gap real = 0.90-0.50, não 0.90-0.89
    assert out.sigla_sinal == "79"
```

(usar os helpers de construção de SignalRecord já existentes em `tests/test_roteador.py`.)

- [ ] Step 2: rodar → FAIL
- [ ] Step 3: implementar

```python
def _dedupe_por_sigla(cands: list[Candidato]) -> list[Candidato]:
    melhor: dict[str, Candidato] = {}
    for c in cands:
        k = c.sigla.upper()
        if k not in melhor or c.score > melhor[k].score:
            melhor[k] = c
    return sorted(melhor.values(), key=lambda c: c.score, reverse=True)
```

Usar em `_quadrante` (`candidatos = _dedupe_por_sigla(rec.candidatos)`) e no bloco de gap do consenso (`cands_ord`).

- [ ] Step 4: `python -m pytest -q` → PASS; benchmark sem queda
- [ ] Step 5: reprocessar LISTA 1: contar quantas revisões `score_baixo` viraram decisão; conferir amostra de 10 manualmente (corretude, não só contagem)
- [ ] Step 6: commit `fix(spH): gap entre siglas distintas (dedupe de variantes da LP)`

---

### Task 3: Resgate por regras na zona cinzenta

**Files:**
- Modify: `src/tdt/roteador.py` (`rotear`, `_quadrante`), `src/tdt/pipeline.py:243` (passar ajustes), `src/tdt/config.py` (`resgate_por_regras: bool = True`)
- Test: `tests/test_roteador.py`

**Interfaces:**
- Consumes: `ajustes` de `motor_regras.aplicar_rastreado` — mapa sigla→delta aplicado (conferir estrutura exata em `motor_regras.py` antes de codar).
- Produces: `rotear(rec, config, votos=None, ajustes=None)`; decisão extra: `pct_ok and not gap_ok` E topo com ajuste positivo exclusivo (topo>0, segundo<=0) → decide com justificativa `resgate_regras`.

- [ ] Step 1: testes RED

```python
def test_resgate_por_regras_decide(config):
    rec = _rec_com_candidatos([("SGFT", 0.62), ("SGT2", 0.58)])
    out = rotear(rec, config, ajustes={"SGFT": +0.15, "SGT2": 0.0})
    assert out.status == "decidido" and out.sigla_sinal == "SGFT"
    assert "resgate_regras" in out.justificativa

def test_sem_regra_exclusiva_vai_revisao(config):
    rec = _rec_com_candidatos([("SGFT", 0.62), ("SGT2", 0.58)])
    out = rotear(rec, config, ajustes={"SGFT": +0.15, "SGT2": +0.15})
    assert out.status == "revisao"

def test_resgate_desligado_por_config(config):
    cfg = replace(config, resgate_por_regras=False)
    rec = _rec_com_candidatos([("SGFT", 0.62), ("SGT2", 0.58)])
    assert rotear(rec, cfg, ajustes={"SGFT": +0.15}).status == "revisao"
```

- [ ] Step 2: rodar → FAIL
- [ ] Step 3: implementar no `_quadrante` (novo braço entre decidido e revisão):

```python
    if pct_ok and not gap_ok and config.resgate_por_regras and ajustes:
        aj_topo = ajustes.get(topo.sigla, 0.0)
        aj_seg = ajustes.get(candidatos[1].sigla, 0.0) if len(candidatos) > 1 else 0.0
        if aj_topo > 0 and aj_seg <= 0:
            return replace(rec, sigla_sinal=topo.sigla, status="decidido",
                justificativa=f"{topo.sigla} por resgate_regras "
                              f"(%={topo.score:.2f}, gap={gap:.2f}, regra=+{aj_topo:.2f})")
```

Propagar `ajustes` de `pipeline.py:243` até a chamada de `rotear`.

- [ ] Step 4: testes PASS; benchmark: corretude NÃO cai (taxa de decisão pode subir)
- [ ] Step 5: reprocessar LISTA 1; listar resgatados no txt de resultados; conferir amostra manual
- [ ] Step 6: commit `feat(spH): resgate por regra discriminante na zona cinzenta`

---

### Task 4: Experimento de pesos (grid + RRF + BM25 + char n-gram)

**Files:**
- Create: `bench/exp_pesos.py`
- Create: `docs/superpowers/specs/2026-07-02-spH-resultado-experimento-pesos.md` (relatório)

- [ ] Step 1: script — reusar a MESMA montagem do `bench/benchmark.py` (corpus, ROTULOS, scorers tfidf/vetorial/fuzzy e `combinar_calib`); variantes:

```python
GRIDS = [
    (0.4, 0.4, 0.2),   # atual (conferir valores vigentes na Config)
    (0.3, 0.5, 0.2),
    (0.2, 0.6, 0.2),
    (0.2, 0.5, 0.3),
    (0.1, 0.7, 0.2),
]

def rrf(listas, k=60):
    acc = {}
    for lst in listas:
        for rank, c in enumerate(sorted(lst, key=lambda c: c.score, reverse=True)):
            acc[c.sigla] = acc.get(c.sigla, 0.0) + 1.0 / (k + rank + 1)
    return sorted((Candidato(s, v, "rrf") for s, v in acc.items()),
                  key=lambda c: c.score, reverse=True)
```

- BM25: variante do ScorerTFIDF (rank-bm25 NÃO entra como dependência nova — implementar idf/saturação em cima da matriz existente OU pular com nota se custo > 30 loc);
- char n-gram: `ScorerTFIDF.construir` com analisador char 3-5 se o construtor permitir; senão variante local no script.
- Para cada variante: acc@1, recall@3, precisão@decididos, taxa de decisão nos ROTULOS.

- [ ] Step 2: rodar `PYTHONPATH=src python bench/exp_pesos.py | Tee-Object bench/resultados/spH_exp_pesos.txt`
- [ ] Step 3: escrever o relatório (tabela + decisão: adotar X / manter atual). Empate técnico = manter atual.
- [ ] Step 4: SE houver vencedor: atualizar pesos na `Config` (ou trocar fusão por RRF) com teste de regressão do benchmark; SENÃO: registrar e encerrar.
- [ ] Step 5: commit `bench(spH): experimento de pesos + decisao registrada`

---

### Task 5: Corretude como métrica primária

**Files:**
- Modify: `bench/benchmark.py` (bloco final de relatório) e/ou `bench/regressao.py`

- [ ] Step 1: adicionar ao fim do benchmark a chamada do gate real (quando os dois arquivos existem):

```python
try:
    sys.path.insert(0, "bench"); from gate_tdt_real import comparar
    r = comparar("output/LISTA 1 - GTD/TDT.xlsx", "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx")
    log(f"[PRIMARIA] corretude vs GTD real: {r.iguais}/{r.comum} = {r.pct:.1f}%")
except FileNotFoundError:
    log("[PRIMARIA] gate TDT real: arquivos ausentes, pulado")
```

Reordenar o log: corretude primeiro, taxa de decisão por último com rótulo `[secundária]`.

- [ ] Step 2: rodar benchmark, conferir saída; commit `bench(spH): corretude vs GTD real como metrica primaria`
