# Bugs conhecidos / causas-raiz resolvidas

**Stemmer N6 regride matching.** `_stemmar` colide RELIGADOR/RELIGAMENTO→RELIGA, singular≠plural (POTENCIA→POTENT). Gateado em `config.stemming` (default False); código mantido mas precisa reescrita das regras antes de religar.

**DJF1 não era criado:** `extrair_contexto_estrutural` só setava `equipamento_alvo` por código ANSI 52/89/29, mas listas reais usam IDs tipo `24-1`. Fix: detecção por palavra whole-token (DISJUNTOR/DJ/SECCIONADORA), SEC excluído (colide SECUNDARIO).

**Especificidade (prefixo genérico ganhava de variante):** prefixo ANSI genérico (79/81/21/25/67) ganhava por fuzzy=1.0 no nº literal em vez da variante (79LO/81E1/21Z3). Fix: `filtro_preciso.filtrar_especificidade` mantém quem casa mais tokens-discriminadores por família ANSI.

**Fase como filtro fraco:** N0 removia a letra de fase do texto, scorer não distinguia IA/IB/IC (boost soft ±0.1 insuficiente). Fix: `f_r3` lê `eletrico.fase` estruturado, remove candidatos de fase divergente.

**Fase-discriminador (SP-D2, 30jun, resolvido):** causa dominante dos empates `score_baixo` (561 na GTD V11) NÃO é estágio, é fase em 2 superfícies:
1. Canonização assimétrica: `"FASE A"`→`"FASE"` (A é stopword-artigo), `"FASE C"` sobrevive. Degrada corpus TF-IDF de FA/PB/FC.
2. Padrão `"‹líder ANSI› ABC"` não populava `eletrico.fase`; mesmo corrigido, `r3_fase` comparava por igualdade estrita e não tratava "F" genérica como compatível com multi-fase.
Fix D2.1-D2.3 implementado: score_baixo 590→520, decididos +111, zero regressão. **Restrito a multi-letra (ABC/AB/BC/CA)** — letra única piorava (ex. "67 N" — descrição-padrão usa "NEUTRO" por extenso).
Fora de escopo confirmado (ambiguidade de DADO, não bug): 81IE1/81E1 com descrição-padrão idêntica; 79_EXC/79_INC com "Excluir/Incluir" juntos na fonte.

**dc_pairer key bug:** chave inclui `sigla_sinal`, então comando (`LIGAR`) e status (`DJF1`) do mesmo equipamento não casam (siglas diferentes) → não fundem em ReadWrite. Alvo era Spec A, dropada — diagnóstico mostrou que a chave já está correta; gargalo real é resolução de sigla do comando (movido pro eixo 2 da Spec D).

**Lição geral:** previsões manuais de qual sigla específica vence não batem com o resultado real (scorer mistura tfidf+vetorial+fuzzy) — ganho só se confirma rodando benchmark/GTD, não por inspeção de código isolada.

**Gate de regressão por sinal real (2026-07-01) — countermeasure.** Investigação de "79OK não decide" e "SGF não pareia" revelou que nenhum dos dois é regressão (nunca funcionaram em nenhum audit salvo desde 24-jun); mas o batch de 30-jun mudou 337 classificações de uma vez **sem gate por-sinal** (o benchmark de 28 pares não cobre sinais reais). Causa-raiz comum: sigla catch-all/genérica atribuída a vários sub-sinais distintos colapsa o discriminador (afeta classificação E pareamento). Countermeasure: `bench/gate_tdt_real.py` compara o TDT gerado × TDT real (`docs/TDT/exportTDT_UTR_*`) por **endereço DNP3** (INCOORDS) — a descrição não existe no TDT real, só endereço é chave estável. `bench/casos_travados.csv` + `bench/regressao.py` (`PYTHONPATH=src python -m bench.regressao`) travam casos específicos; exit≠0 se algum regride. Baseline GTD medido: 664 endereços em comum, 358 iguais (53.9%). Padrões de bug sistemáticos encontrados e travados (6 casos): sigla truncada ao número líder (`50F1`→`1`, afeta toda a família `*F1/*F2`), verbo de comando vazando como sigla (`BBFC`→`LIGAR`), seccionadora mal classificada (`DSEC`→`43LR` genérico), dígito de estágio perdido (`51N1`→`51N`), prefixo de ajuste perdido (`AJG2`→`G2`), mola descarregada (`MOLA`→`MLCC`). Ver spec `docs/superpowers/specs/2026-07-01-sp-discriminador-generico-design.md`.
