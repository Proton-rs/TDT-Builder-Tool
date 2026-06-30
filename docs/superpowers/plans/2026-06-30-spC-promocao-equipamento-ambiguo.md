# SP-C — Promoção dos `equipamento_ambiguo` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parar de barrar na revisão os sinais com sigla decidida cuja família de equipamento não foi inferida (`equipamento_ambiguo`); deixá-los chegar ao `dc_pairer`, que já arbitra "sem comando → TDT / comando ambíguo → revisão".

**Architecture:** Remover do laço de classificação por sheet em `pipeline.executar` o gate `equipamento_ambiguo` (introduzido na spC2) e o cálculo dos ids que só o alimentam. `inferir_equipamento`/`subdividir_transformador_at_bt` e o metadado `equipamento_inferido` permanecem — só o gate de revisão sai. O split comando/sem-comando passa a ser do `dc_pairer` (já existente, sem alteração).

**Tech Stack:** Python 3.14, pytest 9, dataclasses frozen.

## Global Constraints

- **A sigla não muda** — esses sinais já têm sigla decidida; C só deixa de barrá-los. Sem novos falsos positivos de sigla.
- **`dc_pairer` é o árbitro** do split: sem Output no grupo `(módulo, equip, sigla)` → saída/TDT; 1 in + 1 out → `ReadWrite`; ambíguo → `pareamento_ambiguo` (grupo inteiro à revisão). Não alterar `dc_pairer`.
- **Manter** `inferir_equipamento` e `subdividir_transformador_at_bt` (spC2) e o campo `Eletrico.equipamento_inferido` — só o gate de revisão `equipamento_ambiguo` é removido.
- **Benchmark como gate:** `PYTHONPATH=src python bench/benchmark.py` sem regressão (C não toca matching; o benchmark nem exercita o caminho de revisão por equipamento).

---

## File Structure

- **Modify** `src/tdt/pipeline.py` — remover o cálculo `ids_antes_sem_equip`/`ids_equipamento_ambiguo` (após `inferir_equipamento`) e o branch `elif rec.id in ids_equipamento_ambiguo` no laço de classificação.
- **Modify** `tests/test_pipeline.py` — teste novo: sinal sem comando, com sigla decidida e família não inferida, vai pra `lista.registros` (TDT), não pra revisão.
- **Modify** `tests/test_inferencia_topologia.py` — ajustar o comentário/nome do teste que referencia "revisão equipamento_ambiguo" (a função `inferir_equipamento` não muda; só o texto que cita o gate).

---

### Task 1: Remover o gate de revisão `equipamento_ambiguo`

**Files:**
- Modify: `src/tdt/pipeline.py:459-464` (cálculo dos ids) e `:507-509` (branch elif)
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `inferir_equipamento` (mantido), `dc_pairer.parear` (mantido), `ItemRevisao`.
- Produces: nenhum símbolo novo; comportamento: `equipamento_ambiguo` deixa de ser emitido como motivo; sinais decididos de família ambígua entram em `decididos`.

- [ ] **Step 1: Write the failing test**

Acrescentar em `tests/test_pipeline.py`. O teste roda o pipeline ponta-a-ponta num input sintético cujo módulo classifica como tipo sem equipamento default (ex. tipo `Outros`/`Barra`), com uma sigla que decide e **sem** linha de comando, e verifica que o sinal sai em `lista.registros` e **não** há item de revisão `equipamento_ambiguo`.

```python
def test_equipamento_ambiguo_sem_comando_vai_pra_tdt(
    tmp_path, template_dnp3_path, lista_padrao_path,
):
    """C1: sinal com sigla decidida, módulo de tipo sem equipamento default
    (família não inferida) e SEM comando -> entra na TDT (lista.registros),
    não vira revisão equipamento_ambiguo."""
    cfg = Config(peso_tfidf=1.0, peso_vetorial=0.0, threshold_pct=0.4, threshold_gap=0.05)
    inp = _input_equip_ambiguo(tmp_path)  # ver helper abaixo
    resultado, _ = executar(
        inp, template_dnp3_path, lista_padrao_path,
        config=cfg, encoder=_fake_encoder, subestacao="GTD", modo="nao-homogeneo",
    )
    motivos = {it.motivo for it in resultado.revisao}
    assert "equipamento_ambiguo" not in motivos
    assert any(r.sigla_sinal for r in resultado.lista.registros)
```

> Reuse os helpers já existentes em `tests/test_pipeline.py` (`_fake_encoder`, `template_dnp3_path`, `lista_padrao_path`, e o construtor de input sintético usado pelos testes de pipeline). Crie `_input_equip_ambiguo` a partir do helper de input já presente no arquivo, montando uma sheet não-homogênea cujo nome classifique como tipo sem default (ex. um módulo `Barra`/`Outros`) com uma descrição que case uma sigla da lista padrão e **sem** linha sob seção "Comandos". Se o arquivo já tiver um helper de input sintético, parametrize-o; não duplique a montagem de workbook.

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src python -m pytest tests/test_pipeline.py -k equipamento_ambiguo_sem_comando -v`
Expected: FAIL — hoje o sinal vira `ItemRevisao(motivo="equipamento_ambiguo")`, então `"equipamento_ambiguo" in motivos` (assert falha).

- [ ] **Step 3: Write minimal implementation**

Em `src/tdt/pipeline.py`, **remover** o cálculo dos ids (manter só a chamada a `inferir_equipamento`):

```python
        # C2.2/C2.3 (spC2): infere equipamento_alvo pela topologia do tipo de
        # módulo p/ alimentar r_equipamento/r3_fase no scoring. Família não
        # inferida NÃO bloqueia: o sinal com sigla decidida segue para o
        # dc_pairer, que arbitra sem-comando -> TDT / comando ambíguo ->
        # pareamento_ambiguo (Spec C, supersede o gate equipamento_ambiguo).
        sinais = inferir_equipamento(sinais, config)
        total = len(sinais)
```

(apaga as linhas `ids_antes_sem_equip = ...`, `ids_equipamento_ambiguo = {...}` e o comentário antigo sobre revisão.)

E no laço, **remover** o branch `elif`:

```python
            if decidido is not None:
                if rec.id in ids_indefinidos:
                    revisao.append(ItemRevisao(decidido, motivo="modulo_indefinido",
                                               candidatos_sugeridos=decidido.candidatos[:3]))
                else:
                    decididos.append(decidido)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src python -m pytest tests/test_pipeline.py -k equipamento_ambiguo_sem_comando -v`
Expected: PASS.

- [ ] **Step 5: Ajustar o teste da spC2 que cita o gate**

Em `tests/test_inferencia_topologia.py`, o teste `test_tipo_sem_default_claro_fica_none_para_revisao_equipamento_ambiguo` continua válido na asserção (`inferir_equipamento` deixa `equipamento_alvo=None`, `equipamento_inferido=False`), mas o nome/comentário citam o gate removido. Renomear para `test_tipo_sem_default_claro_fica_none` e ajustar o comentário para: "permanece None; o pipeline NÃO bloqueia por isso (Spec C) — o dc_pairer arbitra".

Run: `PYTHONPATH=src python -m pytest tests/test_inferencia_topologia.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/tdt/pipeline.py tests/test_pipeline.py tests/test_inferencia_topologia.py
git commit -m "feat(pipeline): equipamento_ambiguo não bloqueia emissão; dc_pairer arbitra (SP-C)"
```

---

### Task 2: Validação integrada (suite, benchmark, TDT real)

**Files:** nenhum (verificação).

- [ ] **Step 1: Suite completa**

Run: `PYTHONPATH=src python -m pytest -q`
Expected: PASS. Nenhum teste deve asserir `equipamento_ambiguo` em revisão (só o de topologia, já ajustado na Task 1).

- [ ] **Step 2: Benchmark (gate)**

Run: `PYTHONPATH=src python bench/benchmark.py`
Expected: `combo(calib-minmax)` em `acc@1=69% prec@dec=80%` — inalterado.

- [ ] **Step 3: Conferir na GTD V11 (cobertura sobe, sem equipamento_ambiguo)**

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
cfg=Config(); enc=criar_encoder(cfg.modelo_embedding)
r,_=executar("docs/GTD - Lista de Pontos V11.xlsx", DEFAULT_TEMPLATE,
    "docs/Pontos Padrao ADMS_v2.xlsx", config=cfg, encoder=enc, subestacao="GTD", modo="nao-homogeneo")
print("decididos:", len(r.lista.registros))
print("revisao:", dict(Counter(it.motivo for it in r.revisao)))
PY
```
Expected: `equipamento_ambiguo` **ausente** do dict de revisão; `decididos` sobe (baseline ~694 → maior, em direção aos 1641 da real); sinais com comando ambíguo aparecem em `pareamento_ambiguo` (não promovidos). Spot-check: algum sinal promovido de módulo Barra/Transferência sai com nome `GTD_<MOD>_<MOD>_<SIGLA>` (módulo repetido), como a real.

- [ ] **Step 4: (sem commit — verificação)**

Se quiser versionar o `OUTPUT_TDT.xlsx` regenerado, fazê-lo no fechamento das specs B/C/D juntas, não aqui.

---

## Self-Review (preenchido)

- **Cobertura do spec:** C1 remover gate (Task 1) ✓; C2 validação (Task 2) ✓. Critérios 1-5 cobertos.
- **`inferir_equipamento`/`subdividir_transformador_at_bt`/`equipamento_inferido` intactos** (critério 3): nenhuma task os toca. ✓
- **Placeholders:** o helper `_input_equip_ambiguo` referencia os helpers já existentes do arquivo de teste (não é placeholder de lógica — é reuso do padrão de input sintético do próprio `test_pipeline.py`); o restante traz código e comando com saída esperada.
- **Consistência:** a remoção das linhas 459-464 elimina os símbolos `ids_antes_sem_equip`/`ids_equipamento_ambiguo`; o branch que os usava (507-509) é removido na mesma task — sem referência órfã.
