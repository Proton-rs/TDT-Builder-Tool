# Decisões

**Método de matching de sinal (produção atual):** tfidf+vetorial(MiniLM)+fuzzy. Benchmark original (28 pares): acc@1 79-82%, prec@decididos 88-95% (`bench/rotulos.py` + `bench/benchmark.py`). **Escopo do benchmark:** só gateia matching/scoring — não chama `pipeline.executar`, não gateia mudanças estruturais (estruturador, identidade_modulo, pareamento, roteação). Gate real dessas é a suíte pytest completa. ⚠️ **Limitação crítica (descoberta 2026-07-01):** 28 pares NÃO cobrem sinais reais (79*, SGF, DJA1, comandos) — por isso o batch de 30-jun mudou 337 classificações reais (mix melhoria/regressão) sem nenhum gate pegar. Ver [[known-bugs]] e a countermeasure (gate de regressão por sinal real).

**Pesos atuais em `config.py` (verificado 2026-07-01):** peso_tfidf=0.70 peso_vetorial=0.25 peso_fuzzy=0.05, threshold_pct=0.45 threshold_gap=0.08. Analógicos: threshold_pct_analog=0.35/threshold_gap_analog=0.05.

**e5/BGE swap CANCELADO** (3ª rodada): tfidf+vet(MiniLM)+fuzzy = tfidf+e5+fuzzy (82/95/75), e5 não vence, modelo ~1GB mais pesado. `config.e5_prefixos=False`. Capacidade e5 dorme em `indice_vetorial`/`encoder`.

**Calibração/consenso:** `config.usar_consenso=False`. `config.calibracao_por_metodo` (minmax) e `config.confianca_calibrador` (E4 platt, `coef_=2.0403 intercept_=-0.9391`) ESTÃO ativos por default em `pipeline._classificar_sinal` (verificado 2026-07-01, não dormentes).

## Princípios de domínio da classificação (usuário, 2026-07-01)

- **Sinal com filhos → sempre expandir e classificar o filho de maior confiança.** Quando o matching identifica que o sinal pertence a uma família com variantes (ex.: `79` tem `79OK`/`79LO`/`79RE`/`79_EXC`/`79_INC`/`79TF`/`79_1`), o prefixo genérico NÃO deve vencer por default. Expande pros filhos e escolhe o de maior confiança. O pai (genérico) só vence se realmente for o mais próximo (ex.: o sinal-pai puro "Função Religamento"). Se o motor de regras não desambigua, a análise (scorers) deve decidir entre filhos ou pai. **Alvo concreto:** "Religamento (79) - Bem Sucedido" deve dar `79OK`, não `79` (hoje dá genérico porque "sucedido"≠"sucesso" não casa lexicalmente).
- **Todos os sub-sinais existentes devem ser classificados** (não deixar sub-sinal cair no genérico por falta de match lexical do discriminador).

## Countermeasure anti-regressão (usuário, 2026-07-01) — PRIORIDADE

Cada correção de classificação/pareamento vira um **caso travado documentado**: descrição real + módulo + sigla/pareamento esperado, num gate de regressão. Objetivo: quando uma correção futura quebrar algo já corrigido, o gate ACUSA — não se regride silenciosamente o que já foi resolvido. "Continuar progredindo, não ficar atacando sempre os mesmos pontos." É o pré-requisito das demais correções (construir o measuring stick antes de corrigir).

## Roadmap de specs (pós-comparação TDT real, 30jun)

Specs B/C/D (Spec A dropada, incorporada na D): **B** (pronta) fidelidade de campo; **C** (só spec) política equipamento_ambiguo; **D** (spec+plano SP-D2) matching por qualificador.
Ordem: SP-GT → SP-Cleanup → (v6 ∥ SP-Direção ∥ spC1) → spC2 → SP-Decision.

**Princípio do usuário:** criar métodos como candidatos SEM apagar os originais; benchmarkar pelo que performa antes de trocar.
