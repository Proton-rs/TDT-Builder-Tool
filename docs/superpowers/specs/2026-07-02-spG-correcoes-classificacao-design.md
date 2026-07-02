# SP-G — Correções de classificação (tokenização + qualificadores) — Design

**Data:** 2026-07-02
**Fonte dos casos:** `output/LISTA 1 - GTD/Auditoria_Revisao.xlsx` (gerado 02/07/2026), lista padrão `docs/Pontos Padrao ADMS_v2.xlsx`.

## Problema

Cinco erros de classificação observados no output real da GTD. Cada caso tem
linha real de auditoria como evidência e hipótese de causa ancorada no código.

### Caso 1 — Qualificador de 79 perde para a sigla base

| Descrição bruta | Decidido | Correto | Score |
|---|---|---|---|
| `Religamento (79) - Bem Sucedido` | `79` | `79OK` (79 - RELIGAMENTO COM SUCESSO) | 1.007 |
| `Religamento (79) - Disparo` | `79` | `79_1` (79 - PARTIDA RELIGAMENTO) — confirmar no diagnóstico | 0.982 |

Observações:
- Score > 1.0 indica boost pós-fusão. **Não** é `ancoragem_sigla`: `_eh_especifica`
  exige dígito E letra — "79" (só dígitos) não ancora. O caminho real do boost
  é a primeira tarefa do plano (candidatos: `expansao_candidatos`,
  `filtro_preciso`, calibração).
- Gap de vocabulário: "BEM SUCEDIDO" não compartilha token com "COM SUCESSO"
  (nem via stemmer N6). O qualificador não pontua.

**Design:**
1. Sinônimos de qualificador no N1/vocabulário: `BEM SUCEDIDO → SUCESSO`
   (e levantamento de outros pares no diagnóstico: DISPARO→PARTIDA, etc.).
2. Regra de especificidade de qualificador: quando o vencedor é a sigla base
   de uma família (ex. `79`) e existe irmão (prefixo comum, ex. `79OK`,
   `79LO`, `79RE`) cuja descrição-padrão contém token qualificador presente
   no texto de entrada, o irmão qualificado vence (ou o caso vai para
   desempate por regras — nunca decide silenciosamente a base).

### Caso 2 — DJA1 forçado em sinais que não são posição

| Descrição bruta | Decidido | Esperado |
|---|---|---|
| `Disj. 52-1 (01Q0) - Intertravamento` | `DJA1` (0.858) | não é posição — revisão ou sigla própria |
| `Disj. 24-3 (05Q0) - Desligado` | `DJA1` (0.858) | possivelmente CORRETO (desligado = aberto) — separar no diagnóstico |

Observações:
- Score 0.858 uniforme em 96 linhas = caminho de score fixo, não scorer de texto.
- `forcar_polaridade_equipamento` exige par ligado+desligado (1×1) e
  "INTERTRAVAMENTO" não tem prefixo de posição — o caminho decisor é outro
  (whitelist de equipamento + boost? `expansao_candidatos`?). Diagnóstico
  obrigatório antes do fix.

**Design:** gate semântico — sigla de posição (`DJF1`/`DJA1`/`SEC*` de posição)
só é decidível quando o texto contém palavra de posição
(`ABERT*`/`FECHAD*`/`LIGAD*`/`DESLIGAD*`/`NA`). "Intertravamento" nunca
converge para DJ*1. Aplicar no ponto que o diagnóstico apontar como decisor.

### Caso 3 — "Secc." com ponto perde o equipamento

`'Secc. 89-2 (01Q1 Barra) - Alarme (...)'` — N0 (`extrair_contexto_estrutural`,
`normalizador.py`) roda no texto **bruto**; o token `SECC.` (com ponto final)
não casa whole-token em `_EQUIPAMENTO_PALAVRA` → `equipamento_alvo` não seta.
Adiante, N1 expande SECC→SECCIONADORA e N3 dropa como boilerplate → a
informação "seccionadora" some das duas superfícies (contexto E texto).

**Design:** no N0, comparar tokens com pontuação periférica removida
(strip de `.,;:()` nas bordas do token) em TODOS os lookups de N0
(equipamento, barra, fase). Não altera o texto remanescente além do necessário.

### Caso 4 — "Fase A" perde a letra no texto de matching

N0 `_fase_no_texto` remove a letra do texto e anota `ctx.fase`; o token `FASE`
fica órfão e o discriminador só volta via regra R3 (peso 0.10 — fraco).
Bug adicional: `tokens.remove(tok)` remove a **primeira** ocorrência — em
`"CHAVE A FASE A"` come o artigo, não a letra de fase.

**Design:**
1. Parar de remover o token de fase do texto: N0 apenas ANOTA `ctx.fase`,
   o texto segue com "FASE A" intacto (o D2.1 já protege a letra do stopword).
   Scorers passam a ver o discriminador; R3 continua como reforço.
2. Corrigir a remoção por índice onde remoção ainda ocorrer.
3. Benchmark valida (se manter o token regredir, alternativa: remover mas
   reinjetar token canônico `FASE_<X>` — decidir pelo dado).

### Caso 5 — "Proteção SGF - Atuado" não decide SGFT

Vai para revisão com `score_baixo` 0.439 e **c1=SGFT correto** (LP: SGFT =
"TRIP SGF", RelayTrip, NORMAL@ATUADO). Ranking certo, score insuficiente —
"TRIP SGF" compartilha só o token SGF com "PROTEÇÃO SGF ATUADO".

**Design:** a semântica de estados (SP-E, `semantica_estados.py`) sabe que
ATUADO ↔ estados `NORMAL@ATUADO` do candidato. Verificar por que essa
compatibilidade não contribui para o score/decisão e ligá-la como regra
positiva (estado do texto casa com estados da sigla → ajuste positivo).
Caso-limite da SP-H (resgate por regras na zona cinzenta) — implementar aqui
apenas a contribuição de estado; o mecanismo geral de resgate é da SP-H.

## Critérios de aceite

1. Os 5 casos acima classificam conforme a coluna "Correto/Esperado", cada um
   com teste unitário próprio (TDD).
2. `python -m pytest -q` verde; `PYTHONPATH=src python bench/benchmark.py`
   sem regressão de acurácia/precisão.
3. Reprocessar LISTA 1 - GTD: nº de decididos não cai; casos DJA1 separados em
   (a) corretos mantidos, (b) incorretos re-roteados.

## Fora de escopo

- Mecanismo geral de resgate por regras no roteador (SP-H).
- Pareamento comando/estado (SP-I).
- `79_EXC`/estado "Excluido" (dado ambíguo — LP tem `79` estado
  INCLUIDO/EXCLUIDO E comando `79_EXC`; mantido fora, como em SP-D2).
