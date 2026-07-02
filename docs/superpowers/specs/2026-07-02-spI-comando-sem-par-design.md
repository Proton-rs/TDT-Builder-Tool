# SP-I — Comando (output) sem par — Design

**Data:** 2026-07-02
**Contexto:** SP-A (fusão D+C) e SP-E (gate semântico 1×1 no `dc_pairer`,
comando órfão → revisão exceto write legítimo) já mexeram neste domínio.
Usuário reporta que ainda há sinais de comando (output) sem par no output.

## Problema

Comandos (outputs DNP3) deveriam (a) fundir com o discreto correspondente
(comando = output = mesmo sinal, regra de domínio registrada), (b) ser write
legítimo sem par (ex. `79_EXC`, `79_INC`), ou (c) ir para revisão com motivo.
Há comandos escapando dessas três saídas — quantificar e classificar antes de
mexer no `dc_pairer` de novo.

## Design

**Fase 1 — Diagnóstico (obrigatória, antes de qualquer fix):**
script/teste que processa LISTA 1 - GTD e emite relatório de TODOS os
outputs: pareado (com quem) / write sem par (por quê legítimo) / revisão
(motivo) / **escapou** (nenhum dos três). Para cada "escapou", registrar a
causa raiz:
- falha de chave no pareamento (endereço/módulo/equipamento divergem)?
- gate semântico 1×1 rígido demais (estados não casam por vocabulário)?
- comando decidido isoladamente pelo scoring antes do pairer ver?

**Fase 2 — Fix por causa:** cada categoria de causa vira um ajuste pontual no
`dc_pairer`/pipeline, com teste de regressão. Sem redesenho especulativo do
pairer — só o que o diagnóstico provar.

## Critérios de aceite

1. Relatório da Fase 1 commitado em `docs/` (contagens por categoria + exemplos).
2. Pós-fix: zero outputs "escapou" na LISTA 1 — todo comando ou pareado, ou
   write legítimo, ou em revisão com motivo (`comando_sem_discreto` etc.).
3. `diag_estrutura_gtd` (gate estrutural gerado × real) sem regressão.
4. Testes unitários para cada causa corrigida.

## Fora de escopo

- Semântica de estados nova (usa a de SP-E).
- Comandos analógicos (regra de domínio: não existem).
