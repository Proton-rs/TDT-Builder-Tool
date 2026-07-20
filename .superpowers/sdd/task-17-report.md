# Task 17 report — diag_manut_lp (2E, condicional)

**Status:** done, diagnostic-only (no matching/scoring/production code touched).
**Commit:** `a4a947e` — `docs(diag): mede aproveitamento das sheets MANUT (2E)`

## Files touched
- `bench/diag_manut_lp.py` (new)
- `bench/resultados/spOBS_2E.txt` (new, force-added — dir is gitignored)

## What the script does
1. `carregar_manut()` reads `MANUT_DiscreteSignals` + `Manut_AnalogSignals`
   from `docs/Pontos Padrao ADMS_v8.xlsx` via openpyxl (same manual-open
   pattern as `ListaPadraoADMS.carregar`, but by column *position* 0/1
   instead of header name — the header cells in these two sheets are
   mojibake-corrupted (`DESCRI��O NOVA`), so name-lookup via `_coluna()`
   wouldn't match; position is stable and verified against both sheets).
   Loaded **31** sigla+descrição rows (20 discrete + 11 analog with a
   non-empty sigla) — brief said "~33"; close enough, not exact (some
   analog rows have sigla but empty descrição, some have neither).
2. Runs the real pipeline (`tdt.pipeline.executar`) on the same 5 real
   lists used by Task 11/21's `diag_ancora_revisao.py` (GTD/IMA/FWB/GPR/GAU).
3. For every record ending in revisão (`status != "decidido"`) **or**
   looking like a false positive (decided but best candidate score < 0.6,
   a heuristic — there's no production FP flag to reuse), checks whether
   any MANUT sigla anchors exactly (whole-token match) in the record's
   normalized text, or any MANUT descrição fuzzy-matches (rapidfuzz
   `token_sort_ratio` > 90) the record's raw description.
4. Prints every matching case and applies the plan's decision rule.

## Result

**23 real cases** found (≥ 5 threshold) across GTD(8)/IMA(11)/GPR(3)/FWB(0)/GAU(0):
- 17/23 driven by `VCA` (Falta VCA / Falta Vca Painel / VCA Aquecimento —
  exact-anchor match, motivos: `score_baixo`, `custom_id_duplicado`,
  `nome_sigla_inconsistente`, `categoria_incompativel`)
- 4/23 driven by `FUGA` (Fuga a Terra / Fuga Terra — exact anchor)
- 2/23 driven by `VCC1`/`VCC2` (fuzzy 96.0 on "Tensao Corrente Continua")

**Conclusion: ≥5 → recommend opening a 4th-catalog-source task** (flag
`origem="manut"`, individual gate, same structure as Task 7), out of this
plan's scope — **not implemented here**, per explicit dispatch instruction.
Count written to `bench/resultados/spOBS_2E.txt`.

## Concern
The 23 cases are concentrated in essentially 3 distinct MANUT siglas (VCA,
FUGA, VCC1/VCC2) out of 31 loaded — not broad coverage across the sheet.
The plan's own dilution lesson (v5: "more candidates = diluição") applies
to the follow-up task too: whoever picks it up should scope inclusion
narrowly (maybe just these 3 confirmed-useful siglas with a gate) rather
than dumping all 31 MANUT rows into the catalog blindly, echoing the
brief's own "não incluir às cegas" instruction.

I did **not** add the follow-up task to the plan file
(`docs/superpowers/plans/...`) — the brief text (step 2) says to add it
"na hora, com a mesma estrutura da Task 7", but the dispatch message
explicitly said "do NOT implement it now, just recommend" for the ≥5
branch. I followed the dispatch instruction (narrower/more conservative)
and left plan-file editing to the architect/parent agent.

## Correção pós-revisão (2026-07-20)

**Bug metodológico encontrado na revisão:** `carregar_manut()`/`_bate_manut()`
contavam "match" para qualquer sigla MANUT presente num registro real, SEM
excluir siglas MANUT que já existem no catálogo primário
(`DiscreteSignals`/`AnalogSignals`). Cross-referência das 31 siglas MANUT
carregadas contra o catálogo primário: **7 sobrepostas**
(`50CD, MTRF, CMDE, VCA, VCC1, VCC2, FUGA`) e **24 exclusivas do MANUT**.

Todos os 23 "casos reais" originalmente reportados vêm de apenas 4 das 7
siglas sobrepostas (VCA=17, FUGA=4, VCC1/VCC2=2) — siglas que já são
válidas e já pontuadas hoje via catálogo primário; um duplicado vindo do
MANUT não ajudaria em nada (motivo de revisão é rejeição de gate num
candidato JÁ encontrado, não "sigla desconhecida"). **Zero das 24 siglas
exclusivas do MANUT bateram em qualquer registro** — a pergunta real do
diagnóstico ("MANUT como 4ª fonte encontraria candidatos NOVOS?") só é
respondida corretamente pela contagem de siglas exclusivas, que é 0.

Nota lateral confirmada: a sobreposição "FUGA" é o mesmo sinal real que a
Task 8 (já landed) encontrou e excluiu da canonização DE→PARA por
precedência (FUGA já resolve direto no catálogo primário) — mesmo sinal
subjacente, não coincidência; generaliza para VCA/VCC1/VCC2 também.

**Fix:** `carregar_manut()` permanece igual; adicionado filtro em `main()`
que carrega `ListaPadraoADMS.carregar(_LISTA_PADRAO).siglas` (catálogo
primário, mesmo padrão de `descricoes_por_sigla`/`lista_padrao.py`) e
remove do conjunto MANUT qualquer sigla já presente ali, antes de contar
matches.

**Re-execução (mesmas 5 listas reais GTD/IMA/FWB/GPR/GAU):**
```
MANUT: 31 sinais carregados; 7 ja presentes no catalogo primario
(excluidas); 24 exclusivas restantes
casos onde uma sigla/descrição MANUT bateria: 0
2E: 0 casos reais (<5) -> medida, NAO incluida (licao v5: mais
candidatos = diluicao).
```

**Conclusão corrigida: 0 casos (<5) → "2E medida, não incluída".**
`bench/resultados/spOBS_2E.txt` reescrito com a contagem corrigida.
**Reverto a recomendação anterior** de abrir task de inclusão MANUT como
4ª fonte — a análise original estava contaminada por siglas já resolvidas
via catálogo primário; corrigida, não há evidência de ganho.
