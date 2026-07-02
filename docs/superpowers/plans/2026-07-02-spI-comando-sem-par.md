# SP-I — Comando (output) sem par — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ou superpowers:executing-plans. TDD. Steps com checkbox.

**Goal:** todo output ou pareado, ou write legítimo, ou em revisão com motivo — zero "escapados" (spec `2026-07-02-spI-comando-sem-par-design.md`).

**Architecture:** Fase 1 = relatório determinístico da situação de cada output no `dc_pairer`/pipeline; Fase 2 = fixes pontuais por causa provada, com teste de regressão cada.

**Tech Stack:** Python 3.14, pytest, openpyxl.

## Global Constraints

- `python -m pytest -q` verde por task.
- `bench/gate_tdt_real.py` e `diag_estrutura_gtd` sem regressão.
- NÃO redesenhar o `dc_pairer` — só ajustes dirigidos pelo diagnóstico (SP-A/SP-E acabaram de mexer aqui).

---

### Task 1: Relatório de outputs (Fase 1)

**Files:**
- Create: `bench/diag_outputs_sem_par.py`
- Create: `docs/superpowers/specs/2026-07-02-spI-relatorio-outputs.md` (resultado)

**Interfaces:**
- Consumes: `tdt.pipeline.executar` + auditoria; ler antes `src/tdt/dc_pairer.py` para mapear como pares/órfãos são marcados no record (campos/justificativa).

- [ ] Step 1: ler `dc_pairer.py` e anotar no script: como identificar no resultado (a) output pareado e com quem, (b) write sem par aceito, (c) revisão `comando_sem_discreto`/afins.
- [ ] Step 2: script:

```python
"""Classifica TODOS os outputs do processamento em: pareado / write_legitimo /
revisao(motivo) / ESCAPOU. Uso:
PYTHONPATH=src python bench/diag_outputs_sem_par.py <input_lista1.xlsx>
"""
import sys
from collections import Counter
from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar

def main(input_path: str) -> None:
    cfg = Config(); aud = Auditoria()
    resultado, _ = executar(input_path, "docs/dnp3_template.xlsx",
        "docs/Pontos Padrao ADMS_v2.xlsx", config=cfg,
        encoder=criar_encoder(cfg.modelo_embedding), auditoria=aud)
    cats = Counter(); escapados = []
    # critérios concretos preenchidos no Step 1 (campos do record marcados pelo dc_pairer)
    for rec in resultado.lista.registros:
        if rec.tipo_sinal.direcao != "Output":       # conferir nome exato do campo no contracts
            continue
        cat = classificar(rec)                       # pareado|write_legitimo|ESCAPOU
        cats[cat] += 1
        if cat == "ESCAPOU":
            escapados.append((rec.descricoes.bruta, rec.sigla_sinal, rec.justificativa))
    for it in resultado.revisao:
        if eh_output(it.registro):
            cats[f"revisao:{it.motivo}"] += 1
    print(cats)
    for e in escapados:
        print("ESCAPOU:", e)

if __name__ == "__main__":
    main(sys.argv[1])
```

(`classificar`/`eh_output` são definidos NESTE script com os critérios do Step 1 — deliverable da task inclui essas funções concretas.)

- [ ] Step 3: rodar com o input da LISTA 1; escrever o relatório md: contagens, cada ESCAPOU com causa raiz investigada (chave divergente? gate semântico? decisão isolada pré-pairer?).
- [ ] Step 4: commit `test(spI): relatorio outputs pareado/legitimo/revisao/escapou`

---

### Task 2..N: Fix por causa (uma task por categoria de causa)

> Instanciar após a Task 1 — uma task por causa com >0 ocorrências. Modelo:

**Files:**
- Modify: `src/tdt/dc_pairer.py` (ou pipeline, conforme causa)
- Test: `tests/test_dc_pairer.py`

- [ ] Step 1: teste RED reproduzindo o caso real do relatório (descrição bruta real do ESCAPOU)
- [ ] Step 2: fix mínimo na causa (ex.: normalizar chave de módulo antes do casamento; afrouxar gate semântico só no padrão provado; mover pairer antes da decisão isolada)
- [ ] Step 3: testes PASS; `diag_estrutura_gtd` e gate real sem regressão
- [ ] Step 4: commit `fix(spI): <causa>`

---

### Task final: Validação

- [ ] Step 1: re-rodar `bench/diag_outputs_sem_par.py` → `ESCAPOU == 0`
- [ ] Step 2: atualizar o relatório md com o antes/depois; commit `docs(spI): antes/depois outputs sem par`
