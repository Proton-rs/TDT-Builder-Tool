# SP-C — Promoção dos `equipamento_ambiguo` (família ambígua não bloqueia emissão)

**Data:** 2026-06-30
**Status:** Aguardando revisão do usuário
**Origem:** Comparação `OUTPUT_TDT.xlsx` × TDT real GTD; composição da revisão na
GTD V11 (`equipamento_ambiguo` = 552, 2ª maior fatia, **todos com sigla
decidida**). Decomposição da análise (specs B/C/D).

> Spec **C** da decomposição. Refina a política introduzida na **spC2** (que
> manda `equipamento_ambiguo` pra revisão). Decisão do usuário (30jun): promover
> à TDT os que **não têm comando**; os com comando ficam em revisão até o
> pareamento resolver.

## Problema (medido na GTD V11)

O pipeline manda **552 sinais** para revisão com motivo `equipamento_ambiguo`
(introduzido na spC2): sinais cujo **tipo de módulo** (Transferência, Barra,
Transformador-sem-lado, Outros) **não tem equipamento default** e cuja família
(`eletrico.equipamento_alvo`) não foi inferida. **Todos têm uma sigla decidida
com confiança** — são segurados só pela ambiguidade de família.

A TDT real **inclui** esses sinais (estão entre os 1641). E a família de
equipamento **não é necessária para emitir o sinal**:

`engine_tdt._nome_hierarquico` ([engine_tdt.py:66](../../../src/tdt/engine_tdt.py))
já trata `equipamento=None` — *"sem equipamento: repete o módulo"*:

```python
    if equipamento:
        partes.append(equipamento)
    elif modulo_fmt:
        partes.append(modulo_fmt)  # sem equipamento: repete o módulo
```

→ produz `GTD_BP1_BP1_43TC`, **exatamente a convenção da TDT real**
(`GTD_BP1_BP1_43TC`, `GTD_B69_B69_DR`, `GTD_TRF03_TRF03_50EF`). A família
(`equipamento_alvo` = Disjuntor/Seccionadora) só serve para o **scoring**
(regras `r_equipamento`/`r3_fase`, que já rodaram quando a sigla foi decidida) e
para a **fusão D+C**. Logo, o gate `equipamento_ambiguo → revisão` segura sinais
que **não precisam** da família para entrar na TDT.

## Causa-raiz (no código)

A spC2 adicionou, no laço de classificação por sheet em
`pipeline.executar` ([pipeline.py](../../../src/tdt/pipeline.py)), o branch:

```python
                elif rec.id in ids_equipamento_ambiguo:
                    revisao.append(ItemRevisao(decidido, motivo="equipamento_ambiguo",
                                               candidatos_sugeridos=decidido.candidatos[:3]))
```

Isso roda **no scoring, antes** do `dc_pairer`. Os sinais `equipamento_ambiguo`
vão pra revisão ali e **nunca chegam ao `dc_pairer`** — que é justamente quem
sabe distinguir "tem comando" de "não tem comando".

O `dc_pairer.parear` ([dc_pairer.py:70](../../../src/tdt/dc_pairer.py)) já
implementa o split desejado por grupo `(módulo, equipamento, sigla)`:

- **sem Output (comando)** ⇒ `saída` (vai pra TDT) — *promovido*.
- **1 Input + 1 Output** ⇒ `fundir` em `ReadWrite` — *promovido (fundido)*.
- **ambíguo** (N inputs/outputs) ⇒ `pareamento_ambiguo` (revisão) — *fica em
  revisão "até o pareamento resolver"*.

## Decisão (usuário, 30jun)

Promover à TDT os `equipamento_ambiguo` **sem comando**; os **com comando**
ficam em revisão até o pareamento resolver. Como o `dc_pairer` já faz exatamente
esse split, basta **deixar os sinais chegarem nele** em vez de barrá-los antes.

## Escopo

### C1 — Remover o gate de revisão `equipamento_ambiguo`

Em `pipeline.executar`:

- **Remover** o branch `elif rec.id in ids_equipamento_ambiguo: ... revisão`
  (e o cálculo de `ids_antes_sem_equip`/`ids_equipamento_ambiguo` que só servem
  a ele). Sinais com sigla decidida e família ambígua passam a entrar em
  `decididos` e seguir para o `dc_pairer`.
- **Manter** `inferir_equipamento` (preenche `equipamento_alvo`/
  `equipamento_inferido` onde a topologia determina — alimenta as regras e a
  auditoria) e `subdividir_transformador_at_bt` (spC2). **Só o gate de revisão
  sai.**
- O split comando/sem-comando passa a ser responsabilidade do `dc_pairer`
  (já existente, sem alteração): sem comando → TDT; comando que funde →
  `ReadWrite`; comando ambíguo → `pareamento_ambiguo` (o grupo inteiro, status
  incluso, como hoje).

> Supersede a parte da spC2 que rotula `equipamento_ambiguo` para revisão. O
> motivo `equipamento_ambiguo` deixa de ser emitido pelo pipeline (some da fila);
> o rótulo em `ui/modelo_tabela.py` pode permanecer inócuo (não quebra) ou ser
> removido — decisão de limpeza, não funcional.

### C2 — Validação

- `equipamento_ambiguo` na revisão da GTD V11 → **0** (motivo deixa de ser
  emitido). `decididos` sobem (em direção aos 1641 da real).
- Sinais com comando ambíguo continuam em `pareamento_ambiguo` (não promovidos),
  honrando "com comando fica em revisão até o pareamento resolver".
- Conferir contra a TDT real: os sinais promovidos saem com o **módulo repetido**
  no segmento de equipamento quando sem ID (`GTD_BP1_BP1_43TC`) — bate com a real.
- `PYTHONPATH=src python bench/benchmark.py` sem regressão (C não toca matching;
  o benchmark nem exercita o caminho de revisão por módulo/equipamento).
- `python -m pytest -q` verde — ajustar/retirar os testes da spC2 que asseguram
  `equipamento_ambiguo → revisão` (agora o comportamento é outro; documentar a
  mudança de política no commit).

## Fora de escopo

- Inferência de família em si (`inferir_equipamento`) e subdivisão AT/BT — spC2,
  mantidas. C só remove o gate de revisão.
- Pareamento/fusão D+C e a lógica do `dc_pairer` — não muda (já arbitra o split).
  A consistência comando↔status que melhora a fusão é a Spec D (eixo 2).
- `score_baixo` / desambiguação por qualificador → Spec D (eixo 1).
- Fases / nomenclatura de saída → Spec B.

## Critérios de aceite

1. O pipeline não emite mais `equipamento_ambiguo` como motivo de revisão; esses
   sinais (com sigla decidida) chegam ao `dc_pairer`.
2. Sem comando ⇒ vão para a TDT (emitidos com módulo repetido no segmento de
   equipamento quando sem ID, como a real). Com comando ambíguo ⇒ permanecem em
   `pareamento_ambiguo`.
3. `inferir_equipamento`/`subdividir_transformador_at_bt` e o metadado
   `equipamento_inferido` permanecem (só o gate de revisão é removido).
4. `decididos` sobem na GTD V11 sem novos falsos positivos de sigla (a sigla não
   muda — já estava decidida; só deixa de ser barrada).
5. `python -m pytest -q` verde (testes da spC2 do gate ajustados); benchmark sem
   regressão.
