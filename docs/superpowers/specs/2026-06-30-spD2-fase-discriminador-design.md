# SP-D2 — Fase como discriminador de qualificador (eixo 1, escopo fase)

**Data:** 2026-06-30
**Status:** Implementado e validado (com ajuste de escopo pós-implementação)
**Origem:** D1 (`scripts/diag_qualificador.py`, commit `788a745`) — diagnóstico dos
561 empates `score_baixo` na GTD V11. Refinamento pós-D1 (brainstorming):
~254 empates mesma-família ANSI; investigação manual mostrou que boa parte do
que o D1 rotulou cruamente como "estágio" é, na causa raiz, o mesmo problema
de **fase** manifestado em duas superfícies textuais diferentes. Esta spec
ataca só o eixo fase (a fatia mais coesa, mecanicamente bem entendida e
self-contained do achado da D1).

## Resultado real (pós-implementação, 30jun)

A previsão original do critério de aceite 4 (siglas específicas como `FA`,
`50F1` vencendo literalmente) **não se confirmou point-a-point** — o sistema
real mistura TF-IDF+vetorial+fuzzy (não só TF-IDF, usado na validação manual
do design) e mudanças no texto de entrada cascateiam de formas não-óbvias por
análise manual. Em compensação, a validação na GTD V11 revelou e corrigiu um
**efeito colateral real**: o padrão D2.2 original ("‹líder ANSI› ‹fase›")
capturava também letra única (ex: "67 N"), o que **piorava** esses casos —
removia o token "N" do texto sem ganho compensador (a descrição-padrão usa a
palavra "NEUTRO", não a letra solta, então tirar "N" só perde sinal de
embedding que o bônus fixo de regra (+0.10) não cobre). Corrigido restringindo
D2.2 a multi-letra (`ABC`/`AB`/`BC`/`CA`) — único, coeso, sem essa ambiguidade.

**Métricas finais na GTD V11** (após a correção de escopo):
`score_baixo` 590→**520** (-70); `decididos` 1029→**1140** (+111); nenhuma
outra categoria de revisão regrediu (totais batem: 2228=2228). Benchmark
`combo(calib-minmax)`: acc@1 69% (igual), `decid` 81%→**82%**, prec@dec 80%
(igual, sem queda).

## Problema (causa raiz confirmada no código, dois mecanismos independentes)

### Mecanismo 1 — canonização assimétrica destrói o discriminador de fase

`canonizar("FASE A", cfg)` → `"FASE"` (a letra "A" some). `canonizar("FASE C", cfg)`
→ `"FASE C"` (mantém). Causa: `"A"` está em `STOPWORDS_PADRAO`
([normalizador.py:26-28](../../../src/tdt/normalizacao/normalizador.py)) — é o
artigo "a" do português, removido genericamente sem saber que aqui é uma letra
de fase. `"B"`/`"C"`/`"N"` não são stopwords, então sobrevivem — daí a
assimetria.

Isso degrada o **corpus TF-IDF** da lista padrão: a descrição-padrão de `FA`
é literalmente `"FASE A"`; depois de canonizada vira `"FASE"`, indistinguível
de qualquer outra entrada genérica de proteção. Medido na GTD V11:
`"Proteção Fase A - Atuado"` empata `FA` (score 0.40) com `PROT` — sigla
genérica de "Proteção Bloqueada" (score 0.39), por um gap de 0.01.

Confirmado que a regra `r3_fase` ([motor_regras.py:194](../../../src/tdt/motor_regras.py))
**já** dá bônus correto pra esse caso — texto extrai `eletrico.fase="A"`
(via `extrair_contexto_estrutural`, que roda **antes** da canonização e
**não** sofre o bug de stopword), `fase_da_sigla("FA")` retorna `"A"`, bate
exato, bônus `+peso["fase"]` (0.10) aplicado. Mas o bônus não é suficiente
pra superar o déficit de TF-IDF causado pela perda do token "A" no corpus —
a fonte do problema é o corpus, não a regra.

### Mecanismo 2 — padrão "‹líder ANSI› ‹fase›" não é reconhecido como menção de fase

Texto `"Proteção 50 ABC - Estágio 1 - Atuado"` nunca popula `eletrico.fase`.
`_fase_no_texto` ([normalizador.py:80-89](../../../src/tdt/normalizacao/normalizador.py))
só reconhece o padrão literal `"FASE <letra>"`; o padrão comum na GTD
`"<número ANSI 2-3 dígitos> ABC"` (ou `"67 N"`, etc. — número seguido direto
por um membro de `FASES`, sem a palavra "FASE") não é capturado. Confirmado
por teste direto: `extrair_contexto_estrutural("Proteção 50 ABC - Estágio 1")`
devolve `ctx.fase=None`.

Mesmo que a extração capturasse esse padrão, a regra `r3_fase` compara por
**igualdade estrita** (`fase_cand == alvo`). `fase_da_sigla("50F1")`
([motor_regras.py:179-191](../../../src/tdt/motor_regras.py)) devolve
`"F"` — o sentinela de "fase pura genérica" (mesmo sentinela que a SP-B
mapeia para `"ABC"` na saída). `"F" != "ABC"` na comparação direta, então
mesmo com a extração corrigida o bônus não dispara.

Esse é o mecanismo dominante: `50F1` (descrição "...FASE E1") vs `50_1`
(descrição "...E1", sem "FASE") empatam porque o texto de entrada nunca
contém literalmente a palavra "FASE" (usa "ABC") nem a regra `r3_fase` sabe
conectar fase_da_sigla="F" com um alvo multi-fase extraído do texto.

## Design

Três correções pequenas, cada uma num ponto já existente, sem tocar
scorers de base (TF-IDF/vetorial/fuzzy/calibração) nem thresholds.

### D2.1 — Canonização preserva letra de fase após "FASE"

Em `normalizar`/remoção de stopwords ([normalizador.py](../../../src/tdt/normalizacao/normalizador.py)):
não remover um token de 1 letra que seja membro de `("A","B","C","N")` quando
o token imediatamente anterior (na sequência pré-stopword) for `"FASE"`.
Aplica-se uniformemente — tanto às descrições-padrão da lista (corpus) quanto
a qualquer texto de entrada que ainda não tenha passado por
`extrair_contexto_estrutural`.

### D2.2 — Extração reconhece "‹líder ANSI› ‹fase›" sem a palavra "FASE"

Em `_fase_no_texto` ([normalizador.py:80-89](../../../src/tdt/normalizacao/normalizador.py)):
adicionar um terceiro padrão — token numérico de 2-3 dígitos (líder ANSI)
imediatamente seguido por um membro de `FASES` (ex: `"50 ABC"`, `"67 N"`,
`"81 A"`) — devolve esse membro como fase e remove só o token de fase do
texto (preserva o número ANSI, que já é tratado por outras regras). Não
confundir com o padrão de `_BARRA`/`_ID_EQUIPAMENTO`, que já rodam antes na
mesma função (`extrair_contexto_estrutural`) e têm prioridade — esse novo
padrão só dispara se os anteriores não capturaram nada para aquele token.

### D2.3 — `r3_fase` trata "F" (genérica) como compatível com multi-fase

Em `r3_fase` ([motor_regras.py:194-212](../../../src/tdt/motor_regras.py)):
quando `fase_da_sigla(candidato) == "F"` (fase pura genérica — sigla não tem
letra específica, ex: `50F1`, `PRTF`), tratar como compatível (bônus, não
zero/penalidade) quando `alvo` (a fase extraída do texto) for um valor
multi-fase: `"ABC"`, `"AB"`, `"BC"`, `"CA"`. Não estender a compatibilidade
pra fase específica única (`"A"`/`"B"`/`"C"`/`"N"`) — sigla com letra
explícita (`FA`, `51N`) já tem sua própria comparação exata e deve ser
preferida sobre a variante genérica quando o texto aponta uma fase única.

**Invariante (sem falso positivo):** as três mudanças só **adicionam**
sinal onde hoje não há nenhum (corpus token perdido, extração ausente,
comparação que retorna zero) — nunca alteram um match/score que hoje já é
correto. `r3_fase` continua simétrico: divergência explícita (`fase_cand`
específica ≠ `alvo` específica) continua penalizando como hoje.

## Fora de escopo (confirmado não-corrigível por código, validado no D1 refinado)

- **`81IE1` vs `81E1`** — descrição-padrão idêntica byte-a-byte na lista
  ("81 - TRIP SUB/SOBRE FREQUENCIA E1" pros dois). Ambiguidade de **dado**
  da lista padrão, não de matching — fica em `score_baixo` corretamente.
- **`79_EXC` vs `79_INC`** — o texto-fonte da GTD contém literalmente
  "Excluir / Incluir" na mesma descrição (um único ponto descrevendo as duas
  ações). Ambiguidade da **fonte**, não corrigível por desambiguação de
  qualificador.
- **Heurística "texto sem qualificador prefere candidato sem sufixo"**
  (ex: `67NT` vs `67NT2`) — mecanismo diferente (penaliza excesso, não
  premia match positivo), mais risco de falso positivo. Descartado pelo
  usuário nesta spec.
- Tabela de normalização de estágio/temporização (`E1`≡`F1`≡`_1`, `T`≡`TOC`)
  — após a investigação, a maior parte do que parecia "estágio" é fase
  (mecanismo 2 acima); o resíduo genuíno de estágio/temporização não foi
  quantificado isoladamente e fica para uma spec futura se o ganho desta D2
  não for suficiente.
- Empates cross-família (307/561) — fora do eixo 1 desde a spec D original.
- Matching de base / thresholds do roteador — inalterados.

## Critérios de aceite

1. `canonizar("FASE A", cfg)` preserva o token de fase (não vira só `"FASE"`);
   `"FASE B"`/`"FASE C"` continuam preservadas (sem regressão).
2. `extrair_contexto_estrutural("... 50 ABC ...")` popula `eletrico.fase="ABC"`;
   padrões já cobertos (`"FASE A"`, `"NEUTRO"`, `"TRIFASICO"`) continuam
   funcionando.
3. `r3_fase` dá bônus quando candidato tem fase genérica (`"F"`) e o texto
   aponta fase multi-letra (`"ABC"`/`"AB"`/`"BC"`/`"CA"`); continua penalizando
   divergência explícita entre fases específicas como hoje.
4. Na GTD V11: os empates `50F1`/`50_1` (e análogos `67_1`/`67F1`, `67_2`/
   `67F2`) deixam de empatar sob o gap (um dos dois decide — qual deles
   depende da combinação real tfidf+vetorial+fuzzy, não previsível por
   inspeção manual); `score_baixo` cai (medido: -70), `decididos` sobe
   (medido: +111), sem regressão em nenhuma outra categoria de revisão.
   `81IE1`/`81E1` e `79_EXC`/`79_INC` continuam em revisão (confirma que o
   fix é cirúrgico, não força decisão onde a ambiguidade é real). **Nota
   pós-implementação:** padrão letra-única ("67 N") removido do escopo de
   D2.2 — piorava esses casos (ver "Resultado real" acima); `FA`/`PB`/`FC`
   vs `PROT` (mecanismo D2.1) não decidiram na validação final — o ganho
   medido veio majoritariamente de D2.2+D2.3 (padrão multi-fase).
5. `PYTHONPATH=src python bench/benchmark.py`: `combo(calib-minmax)` sobe ou
   mantém acc@1 (69%) e decisão, sem baixar prec@dec (80%).
6. `python -m pytest -q` verde.
