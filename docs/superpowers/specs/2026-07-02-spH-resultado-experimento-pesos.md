# SP-H — Resultado do experimento de pesos (Task 4)

**Data:** 2026-07-03
**Script:** `bench/exp_pesos.py`
**Saída bruta:** `bench/resultados/spH_exp_pesos.txt`
**Ground-truth:** `bench/rotulos.py` (`ROTULOS`), 1539 pares
**Roteação:** `pct>=0.45 gap>=0.08` (thresholds vigentes na `Config`)

## Montagem

Reusa o MESMO corpus/scorers de `bench/benchmark.py`: lista padrão
(`docs/Pontos Padrao ADMS_v1.xlsx`), canonização, `ScorerTFIDF`, encoder
MiniLM + FAISS (vetorial), `FuzzyMatcher`, `combinar_calib` (minmax) — nenhuma
montagem paralela.

**Nota sobre o grid do brief:** o placeholder `(0.4, 0.4, 0.2)` para "atual"
estava desatualizado. Os valores vigentes conferidos em `Config` são
`peso_tfidf=0.70, peso_vetorial=0.25, peso_fuzzy=0.05` — usados como baseline
real no lugar do placeholder.

## Variantes testadas

1. **Grid estático** (5 combinações, `combinar_calib` minmax): atual +
   4 alternativas do brief.
2. **RRF** (reciprocal rank fusion, k=60) sobre tfidf+vet+fuzzy.
3. **BM25** — implementado em ~35 loc sobre `CountVectorizer` (idf BM25 +
   saturação k1=1.5/b=0.75 aplicados às contagens brutas já vetorizadas; sem
   dependência nova). Testado sozinho e combinado (pesos atuais) com
   vet+fuzzy.
4. **Char n-gram (3-5)** — `ScorerTFIDF.construir` não aceita
   `analyzer`/`ngram_range` (hardcoded para tokens word-level), então a
   variante instancia `TfidfVectorizer(analyzer="char", ngram_range=(3,5))`
   localmente e reusa a classe `ScorerTFIDF` (mesma lógica de `pontuar`, sem
   duplicação). Testado sozinho e combinado com vet+fuzzy.

Nenhuma variante foi pulada — BM25 e char n-gram couberam dentro do
orçamento (~35 loc e ~10 loc respectivamente) sem dependências novas.

## Tabela comparativa

| Variante | acc@1 | rec@3 | decid | prec@dec |
|---|---:|---:|---:|---:|
| **grid(0.70, 0.25, 0.05) — atual** | 69% | 80% | 88% | 76% |
| grid(0.3, 0.5, 0.2) | 68% | 79% | 87% | 74% |
| grid(0.2, 0.6, 0.2) | 65% | 78% | 93% | 69% |
| grid(0.2, 0.5, 0.3) | 68% | 79% | 87% | 74% |
| grid(0.1, 0.7, 0.2) | 65% | 75% | 94% | 68% |
| rrf(tfidf, vet, fuzzy) | 58% | 79% | 0% | 0% |
| bm25(sozinho) | 69% | 77% | 73% | 84% |
| bm25+vet+fuzzy | 70% | 79% | 83% | 81% |
| char3-5(sozinho) | 64% | 74% | 53% | 81% |
| char3-5+vet+fuzzy | 65% | 78% | 89% | 71% |

Números exatos (n=1539): baseline atual acc@1=69.07%, rec@3=79.99%,
decid=87.78%, prec@dec=76.24%.

## Leitura dos resultados

- **Grid estático:** nenhuma das 4 alternativas do brief bate o atual em
  nenhuma métrica relevante. Todas trocam ↑vetorial/↓tfidf por queda de
  acc@1 e prec@dec (o tfidf carrega mais sinal útil que o vetorial neste
  corpus/domínio — confirma o desenho atual, não a hipótese "↑peso do
  embedding" do usuário citada no design doc).
- **RRF:** decid=0% — artefato de escala. RRF produz scores da ordem de
  `3/(k+rank)` (~0.01-0.05), incompatíveis com o threshold `pct>=0.45`
  calibrado para scores mesclados em [0,1]. Não é um veredito sobre a
  qualidade do ranking do RRF (rec@3=79%, comparável ao atual), só sobre a
  incompatibilidade de escala com a roteação vigente — exigiria recalibrar
  thresholds especificamente para RRF, fora do escopo desta Task.
- **BM25:** a variante `bm25+vet+fuzzy` (mesmos pesos 0.70/0.25/0.05, tfidf
  cru trocado por BM25) é a única que melhora acc@1 (70% vs 69%) E
  prec@dec (81% vs 76%) simultaneamente, ao custo de queda em decid (83%
  vs 88%, -5pp — mais casos empurrados para revisão manual). Em volume
  absoluto sobre os 1539 rótulos: ~1035 decisões corretas (vs ~1030 no
  atual) e ~243 decisões erradas (vs ~321) — **78 falsos positivos a
  menos**, ao custo de ~74 casos a mais em revisão manual.
- **Char n-gram:** perde do atual em todas as métricas relevantes quando
  combinado; sozinho tem prec@dec razoável (81%) mas decid baixo (53%).
  Não justifica adoção.

## Decisão

**Manter os pesos atuais (0.70 / 0.25 / 0.05) e a fusão `combinar_calib`
minmax vigente.** Nenhuma variante de **grid estático** ou **RRF** — o
escopo direto desta Task 4 (peso/fusão) — bate o atual; grid é
estritamente pior, RRF é incompatível com a roteação sem retrabalho de
threshold. Regra do plano aplicada: empate/sem-vencedor-claro no escopo
avaliado = manter atual. `src/` não foi tocado.

**Achado relevante para follow-up (fora do escopo de Task 4):** BM25 como
substituto do TF-IDF cru (variante `bm25+vet+fuzzy`) mostra ganho real e
mensurável em correção (acc@1 +1pp, prec@dec +5pp, -78 falsos positivos em
1539 casos), alinhado ao princípio "corretude primeiro" do design SP-H,
mas exige uma mudança de escopo maior que "atualizar pesos ou trocar
fusão": um novo `ScorerBM25` em produção, substituindo `ScorerTFIDF` em
`src/tdt/scoring/`, com rewiring em `pipeline.py` (`_Scorers`,
`aplicar_v2`/fluxo de scoring) e testes de regressão cobrindo os
consumidores downstream do score tfidf (filtros, `motor_regras`,
`roteador`, calibração por método). Isso é trabalho de implementação
dedicado, não um ajuste de peso — registrado aqui como candidato a uma
Task/SP futura, não adotado nesta.

## Arquivos

- `bench/exp_pesos.py` (novo) — script do experimento
- `bench/resultados/spH_exp_pesos.txt` (novo) — saída bruta da execução
- `docs/superpowers/specs/2026-07-02-spH-resultado-experimento-pesos.md`
  (este arquivo)
- `src/` — não alterado
