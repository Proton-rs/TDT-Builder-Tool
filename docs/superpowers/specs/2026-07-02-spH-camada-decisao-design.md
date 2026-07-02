# SP-H — Camada de decisão: gap, resgate por regras, pesos — Design

**Data:** 2026-07-02
**Fonte:** `output/LISTA 1 - GTD/Auditoria_Revisao.xlsx` — 793 revisões
(604 `score_baixo`), `src/tdt/roteador.py`, `src/tdt/config.py`.

## Problema

Três frentes na camada de decisão (pós-scoring, pré-revisão):

### 1. Gap 0.0 com confiança alta → revisão

Sinais com % alto vão para revisão porque `gap = topo.score - segundo` é ~0.

**Hipótese principal (verificar primeiro):** a LP contém a MESMA sigla em
variantes Read/ReadWrite com descrição idêntica (ex. `79` aparece 2×,
`SGF` 2×). Se `candidatos` carrega as duas variantes, c1 e c2 são a mesma
sigla e o gap é 0 **artificial** — a decisão está certa e é bloqueada à toa.

**Design:** dedupe de candidatos por sigla (manter o melhor score) ANTES do
cálculo de gap no roteador (`decidir_v2`/`decidir`). Se após investigação
houver outra fonte de gap-zero (ex. descrições-padrão idênticas em siglas
distintas), tratar por regra de desempate ou documentar como revisão legítima.

### 2. Gap baixo ≠ 0 → resgate pelo motor de regras

Zona cinzenta: `pct_ok` mas `gap < gap_exigido` (ex. `Proteção SGF - Atuado`,
`Secc. 89-4 - Indefinida` c1=FSEC c2=SECC). Hoje: revisão direta.

**Design:** antes de mandar para revisão, rodar `motor_regras` nos top-k
(k=3) candidatos com o contexto do sinal (estado semântico, fase, equipamento,
categoria). Se o ajuste de regras separa o topo (gap pós-regras ≥ exigido),
decide com justificativa `resgate_regras: <regras aplicadas>`; senão revisão
como hoje. Gateado por config (`resgate_por_regras: bool`, default on após
benchmark validar).

### 3. Pesos dos métodos — experimento offline

Sugestão do usuário: ↑ peso do embedding (vetorial), ↓ demais. Alternativas a
avaliar no MESMO experimento:

| Variante | O quê |
|---|---|
| Grid de pesos | varrer combinações (tfidf, vetorial, fuzzy) no benchmark |
| RRF | reciprocal rank fusion — combina por rank, elimina calibração de pesos |
| BM25 | substituir tfidf cru por BM25 (robustez a tamanho de descrição) |
| Char n-gram | tfidf de n-gramas 3-5 (robustez a abreviação sem expansão) |

**Design:** script de experimento em `bench/` que roda as variantes contra o
ground-truth e emite tabela comparativa (acurácia, precisão, taxa de decisão).
Adota-se a variante vencedora por dado; empate = manter atual. Pesos dinâmicos
/ ML de pesos: **adiado** até estático saturar.

### 4. Goal: corretude primeiro

Reorientar a métrica primária do benchmark para **corretude vs GTD real**
(TDT gerada == TDT real da GTD); taxa de decisão vira métrica secundária.
Nenhuma mudança que aumente taxa de decisão à custa de corretude é aceita.

## Critérios de aceite

1. Diagnóstico documentado: distribuição de gap dos 604 `score_baixo` da
   LISTA 1, separando gap-zero-artificial (mesma sigla) de empate real.
2. Dedupe por sigla: casos gap-0-artificial passam a decidir; teste unitário.
3. Resgate por regras: casos resgatados listados com justificativa; benchmark
   sem queda de corretude; teste unitário do fluxo (resgata / não resgata).
4. Experimento de pesos: tabela comparativa commitada em `docs/` com decisão
   registrada; config atualizado só se houver ganho medido.
5. Benchmark reporta corretude como métrica primária.

## Fora de escopo

- ML/auto-treino de pesos (adiado — registrar como possível SP futura).
- Novos scorers além de BM25/char-ngram como variantes do experimento.
- Mudanças na UI de revisão (SP-J).
