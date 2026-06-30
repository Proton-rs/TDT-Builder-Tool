# SP-B — Fidelidade de campo da TDT (fases + nomenclatura determinística)

**Data:** 2026-06-30
**Status:** Aguardando revisão do usuário
**Origem:** Comparação `OUTPUT_TDT.xlsx` (gerado da `GTD - Lista de Pontos V11.xlsx`)
× TDT real `exportTDT_UTR_GTD_1_20260626.xlsx`, sheets de sinais.

> Spec **B** da decomposição da análise comparativa (A pareamento/fusão D+C ·
> **B fidelidade de campo** · C política `equipamento_ambiguo` · D qualidade de
> matching). Escopo deliberadamente enxuto: corrige **campos errados nos sinais
> que o pipeline já decide**, sem mexer em cobertura, matching ou pareamento.

## Problema (medido na comparação real)

Coluna `Phases` (`MEASUREMENT_PHASE`) da `DNP3_DiscreteSignals`:

| Valor | TDT real | OUTPUT atual |
|---|--:|--:|
| `ABC` | 1346 (82%) | 0 |
| `N` | 193 | 90 |
| `A`/`B`/`C` | 30 cada | 96 / 9 / 42 |
| `None` (vazio) | 0 | **468** |
| **`F` (inválido)** | 0 | **112** |
| `Unknown` | 12 | 0 |

Dois defeitos:

1. **Valor inválido `F`** — 112 sinais saem com `Phases="F"`, que **não pertence
   ao domínio ADMS** `FASES = (ABC, AB, BC, CA, A, B, C, N)`. Risco de rejeição
   no import do ADMS.
2. **Sem default** — 468 sinais saem com `Phases` vazio; a TDT real preenche
   `ABC` na esmagadora maioria (82%).

Coluna nome de módulo (`Signal Name`, 2º segmento): a TDT real usa `TRF03`
(zero-pad) para os sinais que nosso pipeline nomeia `TRF3` (das sheets
`TRF3_P`/`TRF3_A`).

## Causa-raiz (confirmada no código)

### Fase inválida `F`

`fase_da_sigla()` ([motor_regras.py:179](../../../src/tdt/motor_regras.py)) devolve
`"F"` como **sentinela de "fase genérica"** — projetado para o scoring de
`r3_fase`, onde `"F"` deve casar com qualquer candidato A/B/C. Não é um valor de
saída.

`_com_fase()` ([pipeline.py:153](../../../src/tdt/pipeline.py)) grava o retorno de
`fase_da_sigla()` direto em `eletrico.fase`:

```python
def _com_fase(rec):
    if rec.sigla_sinal and rec.eletrico.fase is None:
        f = fase_da_sigla(rec.sigla_sinal.upper())
        if f:
            return replace(rec, eletrico=replace(rec.eletrico, fase=f))
    return rec
```

Quando a sigla decidida é uma proteção trifásica genérica (`50F1`, `67F2`,
`PRTF`, `62BF`, `MTRF`), `fase_da_sigla` extrai `"F"`, que vai pra `eletrico.fase`
e o engine emite cru. O alias real desses sinais diz literalmente
"Proteção 50 **ABC**" — ou seja, `"F"` genérico **é** trifásico → `ABC`.

`engine_tdt` ([engine_tdt.py:172,220](../../../src/tdt/engine_tdt.py)) emite
`rec.eletrico.fase` direto na coluna `Phases`, sem default nem validação contra
`FASES`.

### Nome `TRF3` vs `TRF03`

`resolver_modulo` (estratégia posicional) compõe `TRF` + `3` = `TRF3` das sheets
`TRF3_P`/`TRF3_A`. A TDT real usa `TRF03` (a GTD nomeia o 3º transformador de
transferência com zero-pad de 2 dígitos — quirk de dado, não regra geral: a
mesma TDT tem `TRF1`/`TRF2` **sem** pad).

## Escopo

### B1 — `"F"` genérico nunca chega à saída como fase

Corrigir **no limite de escrita do modelo**, não em `fase_da_sigla` (lá o `"F"`
é necessário e correto para o scoring de `r3_fase` — alterá-lo quebraria a
comparação de fase no matching).

- Em `_com_fase` ([pipeline.py:153](../../../src/tdt/pipeline.py)): mapear o
  retorno `"F"` de `fase_da_sigla` para `"ABC"` antes de gravar em
  `eletrico.fase` (proteção genérica trifásica = ABC). Demais retornos
  (A/B/C/N/AB/BC/CA/ABC) passam inalterados.

### B2 — Default `ABC` + guard de domínio no engine

No `engine_tdt`, no ponto único de emissão da coluna `Phases` (discreto e
analógico):

- Helper puro `_fase_saida(fase) -> str`: devolve `fase` se estiver em `FASES`,
  senão `"ABC"`. Cobre num só ponto o `None`/vazio (⇒ ABC default, alinhado com
  os 82% da real) **e** qualquer valor fora do domínio (⇒ ABC). Defesa-em-
  profundidade: garante que o ADMS nunca receba fase inválida, mesmo que uma
  nova origem de fase apareça no futuro. Sem plumbing de auditoria — as funções
  de emissão (`_valores_discreto`/`_valores_analog`) são construtoras puras de
  dict e B1 já elimina a única origem conhecida de `"F"`.
- Fase válida detectada (A/B/C/N/AB/BC/CA/ABC) é preservada como está.

> O default ABC é uma regra de **saída** (preenchimento do campo TDT), não de
> análise — não altera `eletrico.fase` no modelo nem o scoring.

### B3 — Alias `TRF3` → `TRF03` (determinístico)

Adicionar entradas literais em `Config.mapa_sheet_modulo` (spC1):
`"TRF3P": "TRF03"`, `"TRF3A": "TRF03"`. É um alias de dado específico da GTD
(como os demais em `mapa_sheet_modulo`), não uma regra de zero-pad geral —
`TRF1`/`TRF2` continuam sem pad, batendo com a real.

## Fora de escopo (deferido)

- **Nomenclatura GTD-específica** `87B_*`→`BP1/BP2/B69`, `PSACA`→`TSA/TSA1/TSA2/TRSA`,
  e o módulo `SE` (bateria/retificador, que vem das sheets `Consistidos/CTR/UCCD1`
  **excluídas de propósito** no spC1). São convenção por-subestação, não
  generalizáveis, e nome de módulo errado **não perde sinal** (entra na TDT com
  outro label, o revisor renomeia). Vira spec futura de "tabela de alias de
  módulo por subestação" + decisão sobre sinais nível-SE.
- Cobertura, fusão D+C, matching — specs A/C/D.
- Coluna `Side` — já correta (`None`, como a real; o lado AT/BT vive no nome do
  módulo, via spC2).

## Testes (TDD)

| Item | Teste | Asserção |
|---|---|---|
| B1 | `tests/test_pipeline.py` (estende) | sigla com fase genérica (`PRTF`/`50F1`) ⇒ `eletrico.fase == "ABC"`, nunca `"F"` |
| B1 | idem | sigla com fase específica (`51A`→A, `IN61`→N) ⇒ fase preservada |
| B2 | `tests/test_engine_tdt.py` (estende) | `_fase_saida(None) == "ABC"` |
| B2 | idem | `_fase_saida("F")` (ou qualquer fora de `FASES`) `== "ABC"` |
| B2 | idem | `_fase_saida("A") == "A"` (preservado) |
| B3 | `tests/test_identidade_modulo.py` (estende) | `resolver_modulo("TRF3_P")` ⇒ `"TRF03"`; `resolver_modulo("TRF-1")` ⇒ `"TRF1"` (sem pad, inalterado) |

**Gate:** `python -m pytest -q` verde; `PYTHONPATH=src python bench/benchmark.py`
sem regressão (B não toca matching — números do `combo(calib-minmax)` iguais).

## Validação contra a TDT real

Após implementar, re-gerar a TDT da GTD V11 e conferir na `DNP3_DiscreteSignals`:

- `Phases="F"`: **0** (era 112).
- `Phases` vazio: **0** (era 468) — tudo com fase válida.
- Distribuição de `Phases` mais próxima da real (ABC dominante).
- Sinais das sheets `TRF3_*` saem como módulo `TRF03`.

## Critérios de aceite

1. Nenhum sinal sai com `Phases` fora de `FASES` (zero `"F"`, zero vazio).
2. `_com_fase` mapeia o `"F"` genérico para `"ABC"`; fases específicas preservadas.
3. `fase_da_sigla` **inalterada** (scoring de `r3_fase` intacto).
4. Engine aplica default `ABC` + guard de domínio (`_fase_saida`, fallback ABC).
5. Sheets `TRF3_*` ⇒ módulo `TRF03`; `TRF-1`/`TRF-2` inalterados.
6. `python -m pytest -q` verde; benchmark sem regressão.
