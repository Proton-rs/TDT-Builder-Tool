# SP-K — Tela inicial: seleção de sheets + sigla SE — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development ou superpowers:executing-plans. Bug fix = systematic-debugging (reproduzir ANTES de editar). Steps com checkbox.

**Goal:** seleção/rename de sheets funcionando de ponta a ponta e execução bloqueada sem sigla da SE (spec `2026-07-02-spK-tela-inicial-design.md`).

**Architecture:** contrato UI→pipeline: a tela inicial produz a lista de sheets selecionadas (com nomes possivelmente renomeados) e o pipeline só processa essas. O gate de sigla é validação de estado na própria tela.

**Tech Stack:** Python 3.14, PySide6/PyQt, pytest.

## Global Constraints

- Fix na causa raiz, não no sintoma — localizar ONDE a seleção se perde antes de editar.
- `python -m pytest -q` verde por task.

---

### Task 1: Reproduzir e localizar o bug da seleção de sheets

**Files:**
- Read: `src/tdt/ui/tela_inicial.py`, `src/tdt/ui/estado.py`, `src/tdt/ui/worker.py`, chamada de `executar` (pipeline)

- [ ] Step 1: mapear o fluxo: onde a UI guarda a seleção de sheets? o `estado`/config passa isso ao `executar`? o `executar` tem parâmetro para subconjunto de sheets ou processa todas?
- [ ] Step 2: reproduzir com input multi-sheet: desmarcar uma sheet, executar, verificar se ela aparece no output. Repetir com rename.
- [ ] Step 3: anotar a causa raiz no plano (ex.: seleção nunca sai da UI / parâmetro ignorado no pipeline / rename só muda o label). NÃO editar ainda.

---

### Task 2: Fix seleção + rename (TDD no contrato)

**Files:**
- Modify: conforme causa da Task 1 (UI e/ou `src/tdt/pipeline.py`)
- Test: `tests/test_pipeline.py` (contrato de sheets) e/ou teste do estado da UI

- [ ] Step 1: teste RED do contrato — o pipeline aceita/respeita a seleção:

```python
def test_pipeline_processa_apenas_sheets_selecionadas(tmp_path):
    entrada = _xlsx_com_sheets(tmp_path, ["Discreto", "Analogicos", "Ignorar"])
    resultado, _ = executar(entrada, TEMPLATE, LP, config=cfg, encoder=enc,
                            sheets=["Discreto", "Analogicos"])   # param conforme Task 1
    sheets_no_resultado = {r.modulo.nome_sheet for r in resultado.lista.registros}
    assert "Ignorar" not in sheets_no_resultado
```

(assinatura/atributos exatos conforme o mapeamento da Task 1 — se o pipeline já tem o parâmetro e a UI que não envia, o teste RED vai no lado da UI/estado.)

- [ ] Step 2: teste RED do rename: sheet renomeada na UI chega ao estruturador com o nome novo (nome de módulo).
- [ ] Step 3: fix mínimo na causa raiz; testes PASS.
- [ ] Step 4: smoke manual: desmarcar + renomear + executar → output correto.
- [ ] Step 5: commit `fix(spK): selecao e rename de sheets respeitados pelo pipeline`

---

### Task 3: Sigla da SE obrigatória

**Files:**
- Modify: `src/tdt/ui/tela_inicial.py`
- Test: `tests/test_tela_inicial.py` (ou teste de estado, se widgets não forem testáveis no CI)

- [ ] Step 1: teste RED — gate de validação (função pura, testável sem Qt):

```python
def test_pode_executar_exige_sigla():
    assert not pode_executar(sigla_se="", input_ok=True)
    assert not pode_executar(sigla_se="   ", input_ok=True)
    assert pode_executar(sigla_se="SND", input_ok=True)
```

- [ ] Step 2: implementar `pode_executar` (função módulo-level em `tela_inicial.py`) e ligar: botão Executar `setEnabled(pode_executar(...))` em cada mudança do campo; tooltip "Informe a sigla da SE" quando desabilitado; validação repetida no handler de execução (estado carregado de config antiga pode burlar o botão).
- [ ] Step 3: testes PASS; smoke manual.
- [ ] Step 4: commit `feat(spK): execucao bloqueada sem sigla da SE`
