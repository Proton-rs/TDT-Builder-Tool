# SP-D — Desambiguação por qualificador (eixo 1) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps usam checkbox (`- [ ]`).

> **Plano diagnóstico-first.** A Spec D é diagnóstico-first por desenho: o mecanismo da correção (consertar discriminador na canonização vs reforçar `r3_fase` vs tratar empate cross-família) depende do que o diagnóstico **D1** medir. Este plano entrega o **D1 completo e runnable (Task 1)**; as tasks de implementação (D2) são derivadas do relatório do D1 e escritas **depois** dele — escrevê-las agora seria placeholder. A "Análise prévia" abaixo já delimita o espaço (achados confirmados) para que o D1 seja rápido e as tasks D2 saiam diretas.

**Goal:** Decidir os `score_baixo` que são empate entre siglas-IRMÃS de qualificador (família ANSI certa; estágio/fase/temporização/direção não separados), sem aumentar falso positivo.

**Architecture:** Desambiguação **pós-score** (não toca scorers de base). Estende o `filtro_preciso.filtrar_especificidade`/regras de qualificador e/ou a preservação de qualificador na canonização. Tabelas de qualificador em `config.py`.

**Tech Stack:** Python 3.14, pytest 9, dataclasses frozen, regex.

## Global Constraints

- **Sem falso positivo:** só quebra empate quando o qualificador do texto casa **inequivocamente uma** irmã; texto sem qualificador / ambíguo / múltiplas compatíveis ⇒ permanece em revisão.
- **Pós-score:** não alterar TF-IDF/vetorial/fuzzy/calibração (já explorados em SP-GT/v6/SP-Decision). D age na seleção/filtragem de candidatos, depois do score.
- **Tabelas de qualificador em `config.py`** (calibráveis), nunca hardcoded fora dela.
- **Benchmark como gate:** `PYTHONPATH=src python bench/benchmark.py` — `combo(calib-minmax)` **sobe ou mantém** acc@1 (69%) e decisão, **sem baixar** prec@dec (80%). Queda de prec ⇒ desambiguação agressiva demais.

## Análise prévia (achados confirmados — delimitam o D1)

Medido na GTD V11 (script ad-hoc, código atual):

- `score_baixo` = 590; **561** têm `gap(top1,top2) < threshold_gap (0,08)` → vão pra revisão por **empate**, não por score baixo (top1 mediana 0,66).
- Split grosseiro dos empates: **~254 mesma família ANSI** (líderes `67`×74, `81`×72, `50`×48, `79`×15, `87`×13, `86`×9, `21`/`27`/`59`/`25`...) — **irmãs de qualificador, alvo da D**; **~305 cross-família** (líderes ANSI diferentes) — ambiguidade genuína de matching, **fora do eixo 1**.
- Causa confirmada nº1: a canonização **destrói o discriminador de fase** — `canonizar("FASE A")` → `"FASE"` (perde o "A"); `"FASE B"` → `"FASE B"` (mantém). Assimétrico ⇒ `FA`/`FB`/`FC` empatam.
- `filtrar_especificidade` ([filtro_preciso.py:238](../../../src/tdt/filtro_preciso.py)) só age **intra-família** ANSI; `r3_fase` ([motor_regras.py:194](../../../src/tdt/motor_regras.py)) compara fase texto×candidato mas seu delta não está quebrando os empates de fase.

→ O D1 transforma o split grosseiro em categorização precisa (por família × tipo de qualificador × causa) que define quais correções D2 implementa e com que ganho esperado.

---

## File Structure

- **Create** `scripts/diag_qualificador.py` — D1: roda o pipeline na GTD V11, captura os `score_baixo`, categoriza os empates (família ANSI × tipo de qualificador × causa de não-separação) e imprime/grava a tabela. Não altera produção.
- *(D2 — pós-D1)* prováveis alvos: `src/tdt/filtro_preciso.py` (estender desambiguação), `src/tdt/normalizacao/normalizador.py` (preservar discriminador de fase) e/ou `src/tdt/motor_regras.py` (delta de qualificador), `src/tdt/config.py` (tabelas de qualificador), com testes em `tests/test_filtro_preciso.py` / `tests/test_normalizador.py`.

---

### Task 1: D1 — diagnóstico preciso dos empates de qualificador

**Files:**
- Create: `scripts/diag_qualificador.py`

**Interfaces:**
- Consumes: `tdt.pipeline.executar`, `tdt.config.Config`, `tdt.dados.lista_padrao.ListaPadraoADMS` (para a família/qualificador da sigla via descrição-padrão).
- Produces: relatório (stdout + `bench/resultados/diag_qualificador.csv`) com, por empate `score_baixo` (gap<threshold): família ANSI do top1, tipo de qualificador que difere (estágio/fase/temporização/direção/outro), se top2 é mesma família, e a causa provável (qualificador removido na canonização / ausente do índice de discriminadores / forma divergente texto×padrão / cross-família).

- [ ] **Step 1: Escrever o script**

```python
# scripts/diag_qualificador.py
"""D1 (SP-D): categoriza os empates de score_baixo na GTD V11 por família ANSI,
tipo de qualificador e causa de não-separação. Diagnóstico — não toca produção.

Uso: PYTHONPATH=src python scripts/diag_qualificador.py
"""
from __future__ import annotations
import csv, re, sys, warnings, logging
from collections import Counter
from pathlib import Path

warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from tdt.pipeline import executar
from tdt.config import Config
from tdt.defaults import DEFAULT_TEMPLATE
from tdt.dados.encoder import criar_encoder
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.normalizacao.normalizador import canonizar

LIDER = re.compile(r"(\d{2,3})")
QUALIF = {
    "estagio": re.compile(r"\bE?\d\b|\bEST[AÁ]GIO\b", re.I),
    "fase": re.compile(r"\bFASE\b|\b[ABCN]$"),
    "temporizacao": re.compile(r"\bTEMPORIZAD|INSTANT|\bTOC\b|\bIOC\b", re.I),
    "direcao": re.compile(r"\bREVERSE|\bFORWARD|\bDIRECION", re.I),
}

def lider(s: str) -> str | None:
    m = LIDER.match(s); return m.group(1) if m else None

def tipos_no_texto(txt: str) -> set[str]:
    return {k for k, rx in QUALIF.items() if rx.search(txt)}

def main() -> None:
    cfg = Config(); enc = criar_encoder(cfg.modelo_embedding)
    lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v2.xlsx")
    desc_por_sigla = {s.sigla.upper(): s.descricao for s in (*lp.discretos, *lp.analogicos)}
    res, _ = executar("docs/GTD - Lista de Pontos V11.xlsx", DEFAULT_TEMPLATE,
                      "docs/Pontos Padrao ADMS_v2.xlsx", config=cfg, encoder=enc,
                      subestacao="GTD", modo="nao-homogeneo")
    sb = [it for it in res.revisao if it.motivo == "score_baixo"]
    linhas = []
    cat = Counter()
    for it in sb:
        c = it.candidatos_sugeridos
        if len(c) < 2 or (c[0].score - c[1].score) >= cfg.threshold_gap:
            continue
        s1, s2 = c[0].sigla.upper(), c[1].sigla.upper()
        mesma_fam = lider(s1) is not None and lider(s1) == lider(s2)
        txt = canonizar(it.registro.descricoes.bruta, cfg)
        # qualificadores presentes no texto e nas descrições-padrão das 2 siglas
        qt = tipos_no_texto(txt)
        q1 = tipos_no_texto(desc_por_sigla.get(s1, ""))
        q2 = tipos_no_texto(desc_por_sigla.get(s2, ""))
        # tipo que DISTINGUE: presente no texto e que separa s1 de s2
        distingue = sorted((qt & (q1 ^ q2)))
        categoria = (
            "cross_familia" if not mesma_fam
            else (",".join(distingue) if distingue else "mesma_fam_sem_qualif_distinto")
        )
        cat[categoria] += 1
        linhas.append((it.registro.descricoes.bruta, s1, f"{c[0].score:.2f}",
                       s2, f"{c[1].score:.2f}", lider(s1) or "", categoria))
    out = _ROOT / "bench" / "resultados" / "diag_qualificador.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["desc_bruta", "top1", "score1", "top2", "score2", "lider_ansi", "categoria"])
        w.writerows(linhas)
    print(f"score_baixo: {len(sb)} | empates analisados: {len(linhas)}")
    print("categorias:", dict(cat.most_common()))
    print(f"detalhe em {out.relative_to(_ROOT)}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar o diagnóstico**

Run: `PYTHONPATH=src python scripts/diag_qualificador.py`
Expected: imprime `score_baixo`, nº de empates e o dict de categorias (ex. `estagio`, `fase`, `temporizacao`, `direcao`, `mesma_fam_sem_qualif_distinto`, `cross_familia`); grava `bench/resultados/diag_qualificador.csv`. **Ler o CSV** — ele define, por família ANSI e tipo de qualificador, quantos empates são desambiguáveis (qualificador distingue) vs não (cross-família / sem qualificador distinto), e a causa.

- [ ] **Step 3: Commit do diagnóstico**

```bash
git add scripts/diag_qualificador.py
git commit -m "diag(SP-D): D1 categoriza empates de qualificador no score_baixo"
```

- [ ] **Step 4: Autorar as tasks D2 a partir do relatório**

Com o CSV/contagens em mãos, escrever as tasks D2 concretas (RED→GREEN), seguindo o que o D1 mostrar. Candidatos de correção já delimitados pela Análise prévia, a confirmar/dimensionar pelo D1:

1. **Discriminador de fase na canonização** — se `fase` for fatia relevante e a causa for o "FASE A"→"FASE": preservar a fase como token comparável nas descrições-padrão (ou comparar via `eletrico.fase`/`r3_fase` com delta suficiente). Teste: `FA`/`FB`/`FC` deixam de empatar dado texto "Fase A/B/C".
2. **Tabela de qualificador + desambiguação intra-família** — normalizar estágio/temporização/direção a forma canônica única (texto×padrão) em `config.py` e estender `filtrar_especificidade`/`f_r4` para reter a irmã cujo qualificador casa o texto. Teste por família dominante do D1 (ex. `67`, `81`, `50`).
3. **Empate cross-família** — fora do eixo 1 (vai pra revisão); confirmar no D1 que continuam em revisão (não regredir) e registrar para eventual spec futura.

Cada task D2 traz teste primeiro, implementação mínima, e roda o gate (suite + benchmark). O ganho esperado é a soma das categorias desambiguáveis do D1 (não os 590).

---

## Validação (D3 — após D2)

- `score_baixo` na GTD V11 cai pela fatia desambiguável medida no D1; decididos sobem.
- `PYTHONPATH=src python bench/benchmark.py`: acc@1 ≥ 69% e decisão ≥ atual, **sem** baixar prec@dec (80%).
- `python -m pytest -q` verde.
- Spot-check contra a TDT real: `81IE2`, `50_2`, `FA` etc. decididos batem com a sigla real.

## Self-Review (preenchido)

- **Cobertura do spec:** D1 (Task 1) ✓ entrega a tabela categoria→causa exigida pelo critério 1. D2/D3 são derivadas do D1 (Task 4) — intencional para spec diagnóstico-first; a Análise prévia + os candidatos de correção delimitam o trabalho sem fixar código que dependeria de dados ainda não medidos.
- **Placeholders:** Task 1 é script completo e runnable; Task 4 é explicitamente "autorar pós-D1", não um passo de implementação mascarado.
- **Sem falso positivo / pós-score / config:** refletidos nas Global Constraints e nos candidatos D2.
- **Nota:** se o D1 mostrar que a fatia desambiguável é pequena (muitos cross-família), reavaliar o valor da D antes de implementar D2 — como aconteceu com a Spec A.
