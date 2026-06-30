# SP-D — Desambiguação por qualificador (eixo 1 de matching)

**Data:** 2026-06-30
**Status:** Aguardando revisão do usuário
**Origem:** Diagnóstico dos `score_baixo` na geração da TDT GTD (V11) — comparação
`OUTPUT_TDT.xlsx` × TDT real, decomposição da análise (specs B/C/D).

> Spec **D** (eixo 1) da decomposição. A consistência **comando↔status**
> (herdada da Spec A dropada) é o **eixo 2**, deferido para uma spec/fase
> seguinte (D2). Esta spec ataca a causa dominante dos `score_baixo`.

## Problema (medido na GTD V11)

`score_baixo` é o maior motivo de revisão (590 sinais). Mas o diagnóstico
mostrou que **quase nenhum é de score baixo de fato**:

- top1 score: mediana **0,66**; **521/590** têm top1 ≥ 0,40; nenhum < 0,30.
- Vão pra revisão por **gap baixo** (`gap < threshold_gap=0,08`) — empate
  quase-perfeito entre **siglas-irmãs** que diferem só pelo **qualificador**:

```
"Proteção 81 Sub-Frequência E2 - Habilitada"  -> 81IE2@0,82  gap=0,00 (empata 81IE1)
"Proteção 50 ABC - Estágio 1 - Atuado"        -> 50F1@0,77   gap=0,03 (empata 50_2)
"Proteção Fase A - Atuado"                     -> FA@0,40     gap=0,01 (empata FB/FC)
"Proteção 67N REVERSE Temporizado (TOC)"       -> 67NT@0,86   gap=0,00
```

O matcher **acerta a família** (81, 50, 67N, fase) mas não separa o
**qualificador específico** (estágio, fase, temporização, direção) com
confiança → gap abaixo do limiar → revisão. É o "buraco de qualificadores"
já conhecido. Decidir essas siglas tira a maior fatia de `score_baixo` da
revisão sem mexer no matching de base.

## Causa-raiz (confirmada no código)

O `filtro_preciso.filtrar_especificidade` ([filtro_preciso.py:238](../../../src/tdt/filtro_preciso.py))
roda no pipeline ([pipeline.py:206](../../../src/tdt/pipeline.py)) e separa, **dentro
de uma família ANSI** (líder de 2 dígitos), os candidatos que casam mais tokens
discriminadores do texto. Não está resolvendo os empates de qualificador por
duas razões confirmadas:

1. **A canonização destrói o discriminador de fase.** `FA` tem descrição-padrão
   "FASE A", mas `canonizar("FASE A")` → **`"FASE"`** — o extrator de fase
   (`normalizador._fase_no_texto`/`extrair_contexto_estrutural`) remove o token
   da fase. `FB` → `"FASE B"` (mantém). Assimétrico e inconsistente: `FA` fica
   sem discriminador, então `FA`/`FB`/`FC` empatam. O mesmo vale para qualquer
   sigla cujo único discriminador seja a fase removida na canonização.
2. **Empates que sobrevivem à canonização** (ex. `81IE1`/`81IE2` ambos mantêm
   `E1`/`E2`) ainda não são separados — o motivo exato (empate cross-família,
   que `filtrar_especificidade` não toca; ou o índice de discriminadores não
   isola o token de estágio; ou o canonizador de texto/estágio diverge) precisa
   ser fechado no diagnóstico D1.

## Escopo

### D1 — Diagnóstico (fechar o quadro dos empates)

Para cada `score_baixo` com `gap < threshold_gap` na GTD V11, levantar:

- As siglas empatadas (top-k de score ~igual) — são **irmãs de qualificador**?
  Categorizar por tipo: **estágio** (E1/E2/E3…), **fase** (A/B/C/N/AB/BC/CA),
  **temporização** (Temporizado/TOC vs Instantâneo/IOC), **direção**
  (Reverse/Forward), **outros**. Contagem por categoria.
- Por que `filtrar_especificidade` não separou cada caso: (a) qualificador
  removido na canonização (como a fase); (b) empate **cross-família** (o filtro
  só age dentro da família); (c) discriminador presente mas não isolado no
  índice; (d) qualificador no texto em forma diferente da descrição-padrão
  (ex. "Estágio 2" no texto × "E2" na sigla).

Saída: tabela categoria → contagem + causa, que fixa o mecanismo de D2.

### D2 — Correção (preservar + desambiguar qualificadores)

Garantir que os qualificadores sejam **preservados de forma consistente nos dois
lados** (texto e descrição-padrão) e usados para quebrar o empate entre irmãs.
Com base em D1, provavelmente:

- **Fase:** não destruir o discriminador de fase na canonização das
  **descrições-padrão** (corrigir a assimetria `FA`→"FASE"). A fase precisa
  sobreviver como token comparável (ou ser comparada via `eletrico.fase`, que já
  é extraída — alinhar com `r3_fase`, que já compara fase candidato×texto).
- **Estágio/temporização/direção:** normalizar o qualificador a uma forma
  canônica única nos dois lados ("Estágio 2"≡"E2"≡"2"; "Temporizado"≡"TOC";
  "Instantâneo"≡"IOC"; "Reverse"≡"REV") e desambiguar a irmã correspondente —
  estendendo `filtrar_especificidade`/`f_r4` ou uma regra de qualificador
  dedicada (a escolha sai de D1; preferir estender o que já existe a criar
  caminho novo).
- A desambiguação pode ser **cross-família** quando necessário (D1.b) — hoje o
  filtro só age intra-família.

**Invariante (sem falso positivo):** só quebra o empate quando o qualificador do
texto casa **inequivocamente uma** irmã. Texto sem qualificador, qualificador
ambíguo, ou múltiplas irmãs compatíveis ⇒ permanece em revisão (`score_baixo`).
Tabelas de qualificador em `config.py` (calibráveis), nunca hardcoded fora dela.

### D3 — Validação

- `score_baixo` na GTD V11 cai (empates de qualificador passam a decidir);
  decididos sobem.
- `PYTHONPATH=src python bench/benchmark.py`: `combo(calib-minmax)` **sobe ou
  mantém** acc@1 (69%) e taxa de decisão sem **baixar** prec@dec (80%). Quebrar
  empates certos deve subir decisão e acc@1; se a precisão cair, o desempate
  está agressivo demais (apertar o invariante).
- `python -m pytest -q` verde.
- Conferir amostra contra a TDT real: estágios/fases/temporização decididos
  batem com a sigla real (ex. `81IE2`, `50_2`, `FA`).

## Fora de escopo

- **Eixo 2 — consistência comando↔status** (da Spec A dropada): comando e status
  do mesmo sinal convergirem para a mesma sigla padrão → spec/fase seguinte (D2).
- Matching de base (TF-IDF/vetorial/fuzzy/calibração) — já explorado
  (SP-GT/v6/SP-Decision); D não mexe nos scorers, só na desambiguação pós-score.
- Thresholds do roteador — fixados na SP-Decision (já na fronteira de Pareto).
- Política `equipamento_ambiguo` → Spec C.
- Fases como **campo de saída** (default ABC/`"F"`) → Spec B (distinto: B é o
  valor emitido na coluna `Phases`; D é a fase como **discriminador de sigla**).

## Critérios de aceite

1. D1 entrega tabela categoria→contagem→causa dos empates de qualificador.
2. Canonização não destrói o discriminador de fase das descrições-padrão (ou a
   fase é comparada de forma consistente nos dois lados).
3. Estágio/temporização/direção são normalizados a forma canônica única e
   desambiguam a irmã correspondente; tabelas em `config.py`.
4. Empate quebrado só com qualificador inequívoco; ambíguo/ausente ⇒ revisão.
5. `score_baixo` cai e decididos sobem na GTD V11; benchmark sem queda de
   prec@dec e sem queda de acc@1; `python -m pytest -q` verde.
6. Desambiguação aplicada pós-score (não altera scorers de base).
