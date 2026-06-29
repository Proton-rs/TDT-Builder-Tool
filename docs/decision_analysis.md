# Diagnóstico e Otimização de Thresholds do Roteador (SP-Decision)

**Data:** 2026-06-29
**Spec:** `docs/superpowers/specs/2026-06-28-sp-decision-otimizacao-thresholds-design.md`
**Script reprodutível:** `PYTHONPATH=src python scripts/sweep_thresholds.py` → `bench/resultados/sweep_thresholds.csv`

## Resumo executivo

Os thresholds atuais de produção (`threshold_pct=0.45`, `threshold_gap=0.08` para
Discrete; `threshold_pct_analog=0.35`, `threshold_gap_analog=0.05` para Analog)
foram calibrados em 2026 contra um ground-truth de 28 pares e nunca reavaliados.
Com o ground-truth expandido (SP-GT, 1539 pares — 1482 Discrete + 57 Analog) e
varredura completa de `threshold_pct × threshold_gap`, a conclusão é:

- **Os thresholds atuais de Discrete já estão na fronteira de Pareto** — nenhuma
  outra combinação testada decide mais E erra menos ao mesmo tempo. **Não foram
  alterados.**
- **Os thresholds atuais de Analog também estão muito perto do ótimo** — a
  melhora teórica encontrada (gap 0.05→0.02) depende de 1 par extra em 57 amostras
  (efeito de ruído estatístico, não sinal). **Não foram alterados.**
- **Os alvos de precisão da spec (Conservador ≥98%, Balanceado ≥95%) são
  inatingíveis para sinais Discrete** em qualquer ponto da grade varrida — o
  ponto de maior precisão alcançável é 88.4% (com taxa de decisão de só 49%).
  Isso é uma propriedade do bundle de scoring atual (`combo(calib-minmax)` =
  tfidf+vetorial(MiniLM)+fuzzy), não do roteador — ver seção "Limites do
  scoring" abaixo.

## D1 — Diagnóstico dos thresholds atuais

Medido com `bench/rotulos.py` (1539 pares) sobre o bundle de produção
`combo(calib-minmax)`, replicando a fórmula de decisão exata do roteador
(`top.score >= threshold_pct AND gap >= threshold_gap`):

| Categoria | n    | Taxa de decisão | Taxa de revisão | Precisão@decididos | Erros (FP) entre decididos |
|-----------|------|------------------|------------------|---------------------|------------------------------|
| Discrete  | 1482 | 80%              | 20%              | 80%                 | 243                          |
| Analog    | 57   | 93%              | 7%               | 98%                 | 1                            |
| **Agregado** | **1539** | **81%**      | **19%**          | **80%**             | **244**                      |

Os números agregados coincidem com o benchmark de produção
(`combo(calib-minmax)`: acc@1=69%, decid=81%, prec@dec=80%), confirmando que o
sweep replica fielmente a fórmula de decisão do roteador. Sinais analógicos já
operam numa faixa de precisão muito superior (98%) à dos discretos (80%) — a
amostra é pequena (57 pares) mas consistente com a folga maior dos thresholds
analógicos atuais.

## D2 — Varredura de thresholds

Grade: `threshold_pct ∈ {0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9}`
× `threshold_gap ∈ {0.0, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30}` (88
combinações × 3 visões = 264 linhas), sobre o mesmo bundle `combo(calib-minmax)`
usado em produção. CSV completo em `bench/resultados/sweep_thresholds.csv`
(não versionado — reproduzível via o script).

### Fronteira de Pareto — Discrete (1482 pares)

Maximizando simultaneamente taxa de decisão e precisão (cada linha domina toda
combinação com taxa e precisão piores):

| threshold_pct | threshold_gap | Taxa decisão | Precisão | Decididos/Total |
|---------------|----------------|---------------|----------|-------------------|
| 0.00 | 0.00 | 100.0% | 67.5% | 1482/1482 |
| 0.40 | 0.00 | 90.6%  | 73.6% | 1343/1482 |
| 0.45 | 0.00 | 90.1%  | 73.9% | 1335/1482 |
| 0.50 | 0.00 | 89.3%  | 74.5% | 1323/1482 |
| 0.00 | 0.02 | 87.5%  | 74.9% | 1297/1482 |
| 0.40 | 0.05 | 83.8%  | 77.5% | 1242/1482 |
| **0.45** | **0.08** | **80.3%** | **79.6%** | **1190/1482** |
| 0.50 | 0.10 | 78.9%  | 80.5% | 1169/1482 |
| 0.60 | 0.15 | 75.0%  | 82.2% | 1112/1482 |
| 0.00 | 0.30 | 61.5%  | 83.4% | 911/1482  |
| 0.70 | 0.05 | 55.9%  | 84.3% | 828/1482  |
| 0.80 | 0.08 | 53.8%  | 86.1% | 797/1482  |
| 0.90 | 0.10 | 52.0%  | 87.8% | 770/1482  |
| 0.90 | 0.20 | 49.3%  | **88.4% (máximo)** | 731/1482 |

A linha em destaque (**0.45 / 0.08**) é o default atual de produção — está
exatamente sobre a fronteira (nenhuma outra combinação da grade decide mais E
erra menos ao mesmo tempo). O teto de precisão alcançável para Discrete em
toda a grade é **88.4%**, e só com taxa de decisão de 49%.

### Fronteira de Pareto — Analog (57 pares)

| threshold_pct | threshold_gap | Taxa decisão | Precisão | Decididos/Total |
|---------------|----------------|---------------|----------|-------------------|
| qualquer ≤0.6 | 0.00 | 100.0% | 96.5% | 57/57 |
| qualquer ≤0.6 | 0.02 | 96.5%  | 98.2% | 55/57 |
| **0.35\*** | **0.05 (atual)** | **94.7%** | **98.2%** | 54/57 |
| qualquer ≤0.6 | 0.20 | 84.2%  | 100.0% | 48/57 |

\* `threshold_pct_analog` não afeta o resultado em toda a faixa `[0.0, 0.6]`
varrida — os scores top-1 de Analog nesta amostra estão sempre acima de 0.6,
então só `threshold_gap_analog` governa a decisão. Amostra pequena (n=57);
movimentos de 1 par mudam a métrica em ~2pp, então a curva é mais ruído do que
sinal fino — mas a faixa geral (94-98% de precisão) é robusta nos pontos
testados.

### Discreto × Analógico, lado a lado (ponto atual de cada um)

| | Discrete (0.45, 0.08) | Analog (0.35, 0.05) |
|---|---|---|
| Taxa de decisão | 80.3% | 94.7% |
| Precisão@decididos | 79.6% | 98.2% |
| Revisão | 19.7% | 5.3% |
| Erros (FP) | 243 | 1 |

Sinais analógicos são muito mais fáceis de decidir corretamente com o bundle
atual — descrições de grandezas (tensão, corrente, potência) têm vocabulário
mais restrito e menos siglas ambíguas do que comandos/status discretos.

## D3 — Recomendação de perfis de operação

| Perfil | Alvo de precisão | Discrete: (pct, gap) | Discrete: taxa/prec | Analog: (pct, gap) | Analog: taxa/prec |
|--------|-------------------|------------------------|------------------------|----------------------|------------------------|
| Conservador | ≥98% | **INATINGÍVEL** — melhor ponto da grade: (0.90, 0.20) | 49.3% / 88.4% | (0.35, 0.02) | 96.5% / 98.2% |
| Balanceado | ≥95% | **INATINGÍVEL** — melhor ponto da grade: (0.90, 0.20) | 49.3% / 88.4% | (0.35, 0.00) | 100.0% / 96.5% |
| Agressivo | ≥90% | **INATINGÍVEL** — melhor ponto da grade: (0.90, 0.20) | 49.3% / 88.4% | (0.35, 0.00) | 100.0% / 96.5% |

**Discretos: nenhum dos 3 alvos de precisão da spec (98%/95%/90%) é
atingível** em qualquer combinação da grade varrida. O teto é 88.4% de
precisão, e só com taxa de decisão de 49% (metade dos sinais ficaria em
revisão). Isso é consistente com o baseline medido pelo usuário (prec@dec=80%
no default atual) — o gargalo é a capacidade discriminativa do bundle de
scoring (tfidf+vetorial(MiniLM)+fuzzy) sobre descrições reais de produção, não
o roteador. Ver "Limites do scoring" abaixo. Para uso prático, a recomendação
é tratar a fronteira Discrete como o teto real de operação:

- **Operação "mais decisão" (atual, recomendado p/ produção):** (0.45, 0.08) → 80%/80%.
- **Operação "mais precisão" (se algum consumidor downstream tolerar 50%
  de revisão em troca de erro baixo):** (0.90, 0.20) → 49%/88%.

**Analógicos: os 3 alvos são atingíveis** com folga, porque a amostra (n=57)
já decide quase tudo com alta precisão. Os pontos recomendados (acima) são
muito próximos do default atual — a diferença entre eles é 1 par em 57
amostras, dentro da margem de ruído da amostra.

## D4 — Atualização de defaults

**Decisão: manter os defaults atuais em `src/tdt/config.py`, sem alterações.**

- **Discrete** `(threshold_pct=0.45, threshold_gap=0.08)`: está exatamente
  sobre a fronteira de Pareto medida (nenhuma combinação da grade domina este
  ponto — toda combinação com taxa de decisão maior tem precisão pior, e
  vice-versa). Não há ponto estritamente melhor para substituir.
- **Analog** `(threshold_pct_analog=0.35, threshold_gap_analog=0.05)`: muito
  próximo do ótimo (94.7% decisão / 98.2% precisão). Existe um ponto que
  domina estritamente em 1 amostra (`gap=0.02` → 96.5%/98.2%, +1 decidido
  correto sobre 57), mas o ganho é ruído estatístico (n=57; 1 par de
  diferença) — trocar o default por essa margem não é uma decisão
  defensável com esta amostra. Mantido por cautela.

Como não houve mudança em `config.py`, o benchmark (`bench/benchmark.py`) não
muda — os números de produção continuam: `combo(calib-minmax)` acc@1=69%,
decid=81%, prec@dec=80% (medido neste mesmo ground-truth de 1539 pares).

## Limites do scoring (fora de escopo desta spec, registrado para futuro)

A varredura mostra que **nenhum threshold resolve o teto de precisão de
Discretos** — em 1482 pares, mesmo exigindo score top-1 ≥0.90 E gap ≥0.20
(quase nunca decide: 49% de taxa), a precisão não passa de 88.4%. Ou seja,
há ~11-12% dos casos "muito confiantes" que ainda assim erram o top-1. Isso é
uma limitação do bundle de scoring (tfidf+vetorial(MiniLM)+fuzzy com
calibração minmax) em discriminar siglas Discrete parecidas — não do
roteador (que está corretamente exposto à fronteira real, não a esconde).
Investigar isso é trabalho de scoring/matching, explicitamente fora de escopo
desta spec (SP-Decision é parametrização, não mudança de lógica de matching).

## Apêndice — fórmula de decisão replicada

```python
gap = top.score - segundo.score
decidido = top.score >= threshold_pct and gap >= threshold_gap
```

Idêntica à usada em `bench/benchmark.py` (linhas ~129-131) e
`tdt.roteador._quadrante` (linhas ~49-53). O sweep (`scripts/sweep_thresholds.py`)
monta o mesmo bundle `combo(calib-minmax)` (tfidf + vetorial MiniLM + fuzzy,
mescla com pesos iguais `[0.34, 0.33, 0.33]` e calibração minmax por método)
usado em `bench/benchmark.py`, calcula `(top.score, gap, categoria, correto)`
uma única vez por par do ground-truth (parte cara: encoder/tfidf/fuzzy), e
reusa esse cache para todas as 88 combinações de threshold (parte barata:
2 comparações numéricas).
