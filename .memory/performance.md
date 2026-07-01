# Performance

**Encoder batch fix (commits d3f00de + b7ce9f3):** `analise_colunas._col_descricao()` chamava o encoder 1x por coluna → corrigido p/ 1 chamada batch por sheet. Profiling (cProfile) mostrou que a hipótese "gargalo em Python puro" estava ERRADA — só 0.7s de 62.9s era Python; 95%+ é inferência BERT proporcional ao volume de texto. Fix real: reduzir amostra por coluna de 200→40 textos. Resultado: `input_nao_homogeneo_3.xlsx` (~47 sheets) de ~3-4min → ~70-80s (~3x), sem divergência de coluna detectada.

**Lição:** medir com profiler antes de assumir onde está o custo.
