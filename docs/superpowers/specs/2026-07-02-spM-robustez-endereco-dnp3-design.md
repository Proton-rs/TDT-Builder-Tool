# SP-M — Robustez na aquisição de endereços DNP3 — Design

**Data:** 2026-07-02

## Problema

A aquisição de endereços DNP3 pode confundir números que não são endereço
(índices de linha, IDs de equipamento 52-1/01Q0, números ANSI 79/67, contagens)
com o endereço do ponto. Blindar contra ruído usando todas as listas
disponíveis como corpus de teste.

## Design

### Fase 1 — Levantamento (dado primeiro)

Script que varre TODAS as listas do repo (`docs/*.xlsx` de input: GTD, GPR,
GAU, RGE, SAN2…) e reporta, por lista/sheet:
- coluna(s) candidatas a endereço detectadas hoje e por quê;
- números fora da coluna de endereço que PODERIAM ser confundidos (mesma faixa,
  posicionados em colunas vizinhas);
- casos reais de endereço errado no output atual (se houver).

Catálogo de padrões de ruído commitado em `docs/` (tabela: padrão, exemplo,
lista de origem).

### Fase 2 — Endurecimento do parser

Conforme o catálogo, na detecção/leitura de endereço:
- identificação da coluna por CONSISTÊNCIA da coluna inteira (blocos
  monotônicos/contíguos — `inferencia_topologia` já modela blocos), não por
  célula individual;
- rejeição de valores incompatíveis com a coluna decidida (faixa, duplicata
  inesperada) → revisão `sem_endereco`/`endereco_duplicado` como hoje;
- nunca extrair endereço de texto de descrição.

Fix mínimo dirigido pelos casos reais da Fase 1 — sem heurística especulativa.

## Critérios de aceite

1. Catálogo da Fase 1 commitado com ≥ 1 exemplo real por padrão de ruído (ou
   registro explícito de que não há caso real — aí a SP encerra na Fase 1).
2. Zero endereços incorretos nas listas de teste após Fase 2; testes unitários
   por padrão de ruído corrigido.
3. Benchmark/pipeline sem regressão nas listas que já funcionavam.

## Fora de escopo

- Suporte a novos formatos de lista.
- UI (indicação de endereço suspeito na revisão pode virar item da SP-J se a
  Fase 1 mostrar necessidade).
