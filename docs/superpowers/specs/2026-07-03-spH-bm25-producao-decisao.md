# SP-H — BM25 em produção: decisão do follow-up (Task 4)

**Data:** 2026-07-03
**Origem:** achado de follow-up em
`docs/superpowers/specs/2026-07-02-spH-resultado-experimento-pesos.md`
("BM25 como substituto do TF-IDF cru... registrado aqui como candidato a
uma Task/SP futura, não adotado nesta").

## Verificação de rigor (antes de portar)

O experimento original (`bench/exp_pesos.py`) media `bm25+vet+fuzzy` só via
`combinar_calib` — um proxy que pula filtro_preciso, semantica_estados,
whitelist, motor_regras e roteador. Para confirmar que o ganho sobrevive aos
consumidores downstream do score, criei `bench/exp_bm25_full.py`: troca só
`_Scorers.tfidf` por `ScorerBM25` (mesmos pesos 0.70/0.25/0.05, `_classificar_sinal`
real) e comparei contra os mesmos 1539 rótulos.

**Resultado (funil completo, `docs/Pontos Padrao ADMS_v1.xlsx`):**

| | acc@1 | decid | prec@dec | decididos corretos | decididos errados |
|---|---:|---:|---:|---:|---:|
| tfidf (atual) | 64.46% | 71.73% | 78.44% | 866 | 238 |
| bm25 | 64.59% | 67.32% | 82.14% | 851 | 185 |

O ganho de precisão se confirma no funil completo (+3.7pp, -53 falsos
positivos em 1539 casos), ao custo de -4.4pp em decid (~68 casos a mais em
revisão manual) e -15 decisões corretas automáticas (viram revisão, não
erro). Consistente com o achado original.

**Bug encontrado durante a verificação:** a lista padrão real tem sigla com
múltiplas linhas de descrição (variantes NA/NF, sinônimos — ex. `DJF1`/`DJA1`
com 2 linhas cada). Sem dedup, `ScorerBM25.pontuar` podia devolver a MESMA
sigla 2x no top-k (uma por linha), e `mescla.mesclar` soma por sigla —
contando o score em dobro e distorcendo a fusão o suficiente para inverter
decisões em casos de gap apertado (reproduzido em
`tests/test_pipeline.py::test_pipeline_sheet_homogenea_le_colunas_direto_sem_scoring`,
onde `DISJUNTOR ABERTO` decidia `DJA1` sem dedup e ia pra revisão com dedup
correto por causa da inflação). Corrigido em `ScorerBM25.pontuar`
(`src/tdt/scoring/bm25.py`): mantém só o melhor score por sigla antes de
truncar por `k`. A tabela acima já reflete o resultado COM a correção.
`ScorerTFIDF` tem o mesmo padrão de retorno sem dedup — não tocado aqui
(fora de escopo; não há evidência de que cause o mesmo problema em produção
hoje, já que os pesos/calibração vigentes nunca acionaram esse caso).

**Validação independente (gate real, `bench/regressao.py` — GTD):**
`comum=964 iguais=645 pct=66.9%` com BM25 vs `comum=1042 iguais=637
pct=61.1%` com TF-IDF — mesma direção (+5.8pp de correção, menos endereços
auto-decididos). Os 6 casos de `casos_travados.csv` continuam falhando
exatamente como antes (bugs de normalização/estruturação, não de scoring) —
nenhuma regressão nova.

## Decisão

**Adotado.** `_construir_scorers` (`src/tdt/pipeline.py`) e o cache de
scorers (`src/tdt/cache_scorers.py`) agora usam `ScorerBM25` no lugar de
`ScorerTFIDF` no slot `tfidf` de `_Scorers`, para as duas categorias
(Discrete/Analog, mesma função). Pesos e fusão (`combinar_calib`/`mesclar`)
não mudaram. Justificativa: o projeto já prioriza "corretude primeiro" em
todas as decisões de SP-H anteriores (preferir empurrar pra revisão manual a
arriscar falso positivo silencioso) — a troca reduz falsos positivos em
~22% relativo (238→185 em 1539) ao custo de ~4pp a mais de revisão manual,
alinhado a esse princípio.

`ScorerTFIDF` (`src/tdt/scoring/tfidf.py`) fica no repo (não removido) —
outros scripts de bench (`benchmark.py`, `exp_pesos.py`) ainda o usam para
comparação histórica.

## Arquivos

- `src/tdt/scoring/bm25.py` (novo) — `ScorerBM25`, mesma interface pública
  de `ScorerTFIDF` (`construir`/`pontuar`/`salvar`/`carregar`)
- `src/tdt/pipeline.py`, `src/tdt/cache_scorers.py` — rewiring
- `tests/test_scoring_bm25.py` (novo), `tests/test_cache_scorers.py`
  (atualizado p/ `ScorerBM25`)
- `bench/exp_bm25_full.py` (novo) — regressão do ganho medido via funil
  completo (gate: rerodar após qualquer mudança de peso/filtro/motor_regras
  e comparar com a tabela acima; não deve regredir prec@dec/FPs)
