# SP-Decision — Diagnóstico e Otimização de Thresholds do Roteador

**Data:** 2026-06-28
**Status:** Aguardando revisão do usuário
**Origem:** O pipeline decide entre "decidido" e "revisão" por um quadrante simples (gap × score percentual) com thresholds estáticos — `threshold_pct=0.45`, `threshold_gap=0.08`. Esses valores foram calibrados contra 28 pares de ground-truth (v1) e nunca reavaliados.

## Problema

1. **GT pequeno** — 28 pares não representam a distribuição real dos ~237k sinais discretos da base. Thresholds podem estar longe do ótimo real.
2. **Thresholds cegos** — não sabemos o formato da curva precisão × taxa de decisão. Talvez possamos decidir 85% com 95% de precisão, ou 80% com 97%. Sem dados, qualquer escolha é chute.
3. **Discretos × analógicos** — usam thresholds diferentes (`0.35`/`0.05` para analógicos), mas também sem validação empírica.
4. **Sem tradeoff documentado** — operador (humano ou SP2 futuro) não tem como escolher o ponto de operação: conservador (mais revisão, menos FP) ou agressivo (menos revisão, mais FP).

## Escopo

**Diagnóstico + parametrização apenas.** Nada de novo no código de decisão — só medir e ajustar números.

### D1: Curva precisão × decisão para thresholds atuais

Rodar o benchmark completo **com o GT expandido (SP-GT)** e medir, para os thresholds atuais:
- taxa de decisão geral
- precisão nos decididos
- taxa de revisão
- taxa de erro (falso positivo entre os decididos)

Separado por: `Discrete` vs `Analog`, e agregado.

### D2: Varredura de thresholds

Para `threshold_pct` em `[0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9]` e `threshold_gap` em `[0.0, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30]`, para cada combinação:

- Medir `(taxa_decisao, precisao)` no GT
- Plotar: scatter 2D com isolinhas de precisão
- Encontrar a fronteira de Pareto (melhores tradeoffs)

Separado por categoria (Discrete, Analog). Sweep roda sobre o bundle `tfidf+vet+fuzzy` com calibração minmax + regras (exatamente como a pipeline produz).

### D3: Recomendação de thresholds ótimos

Com base na fronteira de Pareto, propor 3 pontos de operação:

| Perfil | Taxa decisão alvo | Precisão mínima | Uso |
|--------|------------------|-----------------|-----|
| Conservador | mais revisão | ≥98% | Produção crítica, sem supervisão |
| Balanceado | máximo possível | ≥95% | Default (produção atual) |
| Agressivo | máximo possível | ≥90% | Pré-filtro antes de SP2/LLM |

Cada perfil mapeia para `(threshold_pct, threshold_gap)` de Discrete e Analog.

### D4: Atualizar defaults

Se os thresholds ótimos diferirem dos atuais, atualizar `config.py` com os novos valores default.

### D5: Relatório

Gerar `docs/decision_analysis.md` com:
- Curvas e tabelas da varredura
- Fronteira de Pareto
- Recomendação dos 3 perfis
- Discretos vs analógicos lado a lado

## Fora de escopo

- Mudanças na função de decisão (ex: usar calibrador Platt como gate direto, ou votação entre métodos)
- Consenso (já tratado no SP-Cleanup — desativado por padrão)
- Roteador novo (SP2 original fica para depois)
- Qualquer alteração no código de matching, scoring, regras ou filtros

## Dependências

- **SP-GT** (expansão do ground-truth) — pré-requisito. Sem GT grande, a varredura não é confiável.
- **SP-Cleanup** — desejável (remove ruído do consenso, mas a varredura usa só o quadrante simples, então não bloqueia).

## Testes

Nada de novo nos testes (é análise, não código). A verificação é:

1. Script de sweep gera tabela numérica reproduzível
2. Recomendações são auto-contidas no relatório
3. `config.py` atualizado com novos defaults (se mudar)

## Critérios de aceite

1. Varredura de thresholds executável via `PYTHONPATH=src python scripts/sweep_thresholds.py`
2. Saída: tabela CSV com todas as combinações + métricas
3. Relatório `docs/decision_analysis.md` com curvas, Pareto e recomendação
4. `config.py` atualizado com thresholds ótimos (se diferente dos atuais)
5. `python -m pytest -q` verde
