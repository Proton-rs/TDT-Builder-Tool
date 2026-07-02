# SP-M — Robustez na aquisição de endereços DNP3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ou superpowers:executing-plans. Fase 1 decide se a Fase 2 existe. Steps com checkbox.

**Goal:** blindar a aquisição de endereços contra números que não são endereço, dirigido por casos reais (spec `2026-07-02-spM-robustez-endereco-dnp3-design.md`).

**Architecture:** Fase 1 = varredura de todas as listas + catálogo de ruído; Fase 2 (condicional) = endurecimento no detector de coluna/leitura de endereço, por padrão provado.

**Tech Stack:** Python 3.14, pytest, openpyxl.

## Global Constraints

- Se a Fase 1 não achar caso real de endereço errado, a SP ENCERRA na Fase 1 (registrar e parar — YAGNI).
- `python -m pytest -q` verde; benchmark/pipeline sem regressão nas listas que já funcionam.

---

### Task 1: Varredura das listas (Fase 1)

**Files:**
- Create: `bench/diag_enderecos.py`
- Create: `docs/superpowers/specs/2026-07-02-spM-catalogo-ruido-enderecos.md`

- [ ] Step 1: ler `src/tdt/analise/analise_colunas.py` (como a coluna de endereço é detectada hoje) e `src/tdt/inferencia_topologia.py` (modelo de blocos) — anotar no script os critérios vigentes.
- [ ] Step 2: script:

```python
"""Para cada lista/sheet: coluna de endereço detectada + números 'confundíveis'
(células numéricas fora da coluna de endereço em faixa plausível de endereço).
Compara endereço lido pelo pipeline com a coluna verdadeira (inspeção manual
das listas conhecidas). Uso:
PYTHONPATH=src python bench/diag_enderecos.py docs/*.xlsx
"""
import glob, sys
import openpyxl
# para cada arquivo/sheet: header + primeiras 30 linhas;
# marca colunas majoritariamente numéricas, faixa, monotonicidade, duplicatas;
# imprime a coluna que o detector atual escolheria e as concorrentes.
```

(corpo concreto: reusar a função de detecção real importada de `analise_colunas` — a MESMA que o pipeline usa, nada paralelo.)

- [ ] Step 3: rodar contra TODAS as listas do repo (GTD, GPR, GAU, RGE, SAN2, homogêneas de `docs/`); escrever o catálogo: tabela padrão de ruído → exemplo real → lista de origem; seção final: **casos reais de endereço errado no output atual** (sim/não).
- [ ] Step 4: commit `test(spM): catalogo de ruido de enderecos em todas as listas`

**GATE:** sem caso real de endereço errado → registrar no catálogo "nenhum caso real; endurecimento adiado (YAGNI)", commit e ENCERRAR a SP.

---

### Task 2 (condicional): Endurecimento do detector/leitura

**Files:**
- Modify: `src/tdt/analise/analise_colunas.py` e/ou `src/tdt/normalizacao/estruturador.py` (onde o endereço é lido por linha)
- Test: `tests/test_analise_colunas.py`

- [ ] Step 1: para CADA padrão de ruído com caso real: teste RED reproduzindo a lista sintética mínima com aquele ruído (endereço na coluna certa, ruído na errada) — o detector deve escolher a coluna certa e a leitura deve rejeitar o valor incompatível (revisão `sem_endereco`/`endereco_duplicado`).
- [ ] Step 2: implementar por padrão: pontuação de coluna por consistência (fração de valores em blocos contíguos/monotônicos — reusar lógica de blocos de `inferencia_topologia`), rejeição por faixa/duplicata na leitura. Nunca extrair endereço de descrição.
- [ ] Step 3: testes PASS; reprocessar as listas do catálogo: zero endereços incorretos; listas boas inalteradas (diff de output).
- [ ] Step 4: commit `fix(spM): detector de endereco por consistencia de coluna`
