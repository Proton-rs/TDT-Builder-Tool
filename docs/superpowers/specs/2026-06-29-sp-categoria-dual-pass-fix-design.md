# SP Categoria — Barreira de domínio no dual-pass de classificação

**Data:** 2026-06-29
**Status:** Implementado e validado no pipeline completo com dado real (ver "Resultado medido" abaixo)
**Origem:** Análise de falsos positivos em `Auditoria_Revisao.xlsx` — 213 sinais decididos com sigla de categoria incompatível (Analog vs Discrete).
**Escopo:** Corrigir o dual-pass em `pipeline._classificar_roteado` para respeitar a categoria do sinal de origem, eliminando inconsistências de domínio sem podar recall.

---

## Diagnóstico

### Problema

O pipeline constrói **dois bundles de scorers independentes**:

| Bundle | Corpus | Siglas disponíveis |
|---|---|---|
| `disc` | `lp.discretos` (692 registros) | `32`, `27BC`, `PB`, `79`, `FCMR`, ... |
| `ana` | `lp.analogicos` (62 registros) | `P`, `Q`, `VAB`, `VBC`, `VCC1`, `IN61`, ... |

Cada bundle **só conhece siglas da própria categoria**. O problema é que o pipeline não valida se a sigla decidida é compatível com a categoria do sinal de entrada.

### Fluxo que quebra

`pipeline._classificar_roteado` (linha 242) tem duas rotas:

```
if categoria_confiavel:
    → usa SÓ o bundle da própria categoria  ✅ (nunca erra domínio)

else (dual-pass, categoria_incerta):
    → roda AMBOS os bundles
    → se só um decidir, USA ELE  ❌ (pode ser da categoria errada)
    → se ambos decidirem, tenta desempatar por gap/centroide  ❌ (sem barreira de domínio)
```

O dual-pass é ativado quando `categoria_confiavel=False` — que acontece em dois momentos:

1. **`estruturador.py:75`**: quando a planilha não tem coluna "Tipo" nem marcadores de seção → `confiavel = False`
2. **`identidade_modulo.py:99`**: quando o módulo não é identificado → força `categoria_confiavel=False` **mesmo que a planilha tivesse Tipo**

### Consequências medidas

| Direção | Qtde | Exemplo típico |
|---|---|---|
| Analog/Input → sigla **Discrete** | 23 | "Potência Ativa" → `32` (direcional de potência, RelayTrip) |
| Discrete/Input → sigla **Analog** | 190 | "Proteção 81 Sub-Frequência Atuado" → `VCC1` (tensão DC) |
| **Total** | **213** | |

### Por que acontece

Sinais com descrições curtas/genéricas ("Potência Ativa", "Grupo de Ajustes 1 - Ativo", "Secc. 89-2 ... Abrir/Fechar") têm scores baixos e distribuídos. No dual-pass:

- O **bundle correto** (ex: `ana` para "Potência Ativa") encontra `P` mas com score baixo (< threshold) → não decide
- O **bundle errado** (`disc`) encontra `32` com score 0.644 (> threshold) → decide
- O pipeline aceita a decisão do bundle errado porque foi o único que decidiu

Prova de que o single-pass funciona: sheets **GTD** (onde `categoria_confiavel=True`) classificam "Potência Ativa" → `P` corretamente.

---

## Solução Proposta

### Princípio

> Um bundle só pode decidir sobre sinais da sua própria categoria.

A categoria do sinal de entrada é conhecida mesmo quando `categoria_confiavel=False` — ela está em `rec.tipo_sinal.categoria`. O dual-pass deve usar essa informação para **filtrar a saída**:

- Bundle `disc` → **só decide** se a categoria do sinal admite o domínio discreto
- Bundle `ana`  → **só decide** se a categoria do sinal admite o domínio analógico

> ⚠️ **A categoria NÃO é binária.** O contrato (`contracts.py:34`) define
> três valores: `"Discrete" | "Analog" | "DiscreteAnalog"`. Um filtro com
> `== "Discrete"` / `== "Analog"` tranca **todo** sinal `DiscreteAnalog` em
> revisão — mesmo quando um bundle decidiu certo — porque ambas as
> comparações dariam `False`. O branch `confiavel` atual (linha 252) já
> trata `DiscreteAnalog` mapeando-o para o bundle `ana`; o dual-pass precisa
> ser igualmente tolerante. Por isso a barreira é modelada como um
> **conjunto de domínios admitidos** por categoria, não como igualdade.
>
> Hoje o runtime (`vocabulario_tipo.classificar`, `estruturador`,
> `estruturador_homogeneo`) só emite `Discrete`/`Analog` — `DiscreteAnalog`
> aparece apenas na base de ground-truth (`scripts/`). Logo a falha **não
> dispara hoje**, mas é fragilidade latente: o contrato a permite e o
> default de fallback abaixo a cobre sem custo.

> ⚠️ **`rec.tipo_sinal.categoria` pode ser um placeholder sem evidência —
> não confiar nela como filtro absoluto.** `categoria_confiavel=False` tem
> duas origens bem diferentes:
>
> 1. **`identidade_modulo.py:99`**: a categoria *já era confiável* (veio de
>    uma coluna "Tipo" real); só foi forçada a `False` porque o módulo não
>    foi identificado. Aqui `categoria` é evidência real — a barreira pode
>    confiar nela.
> 2. **`estruturador.py:75`**: quando a sheet não tem coluna "Tipo" **nem**
>    marcador de seção, `categoria` cai no default hardcoded
>    (`secao = ("Discrete", "Input")`, `estruturador.py:55`). Aqui
>    `categoria == "Discrete"` não é evidência — é um placeholder arbitrário.
>
> O contrato não distingue as duas origens (mesmo booleano `categoria_confiavel`
> para ambas). Se a barreira **aceitasse automaticamente** a decisão do lado
> "permitido" sempre que o lado barrado também decidisse, ela inverteria a
> premissa do dual-pass: para sinais do caso 2 (placeholder), isso aceitaria
> sem aviso a resposta do domínio que coincide com o placeholder, mesmo
> quando o outro bundle decidiu com confiança — pior que o comportamento
> atual (que ao menos comparava via `_desempatar_ambiguo`).
>
> **Mitigação adotada:** quando a barreira bloqueia um domínio que **também**
> decidiu (conflito real, não apenas score baixo), o resultado vai para
> revisão com `motivo="categoria_ambigua"` — igual ao caso em que os dois
> domínios decidem dentro do mesmo conjunto admitido. Nunca se auto-aceita
> o lado "permitido" só porque o outro foi barrado; barrar só "ganha"
> silenciosamente quando o lado barrado é o **único** que decidiu (aí sim
> é o FP cross-categoria que esta spec quer eliminar, motivo
> `categoria_incompativel`).

### Implementação

Modificar `_classificar_roteado` em `pipeline.py` (linhas 242-277):

```python
# Domínios que cada categoria de sinal admite. DiscreteAnalog (e qualquer
# categoria não mapeada, via .get default) admite os dois — equivale ao
# dual-pass livre de antes nesse caso.
_DOMINIOS_POR_CATEGORIA: dict[str, frozenset[str]] = {
    "Discrete": frozenset({"Discrete"}),
    "Analog": frozenset({"Analog"}),
    "DiscreteAnalog": frozenset({"Discrete", "Analog"}),
}


def _classificar_roteado(rec, disc, ana, ...):
    if rec.tipo_sinal.categoria_confiavel:
        # Rota atual: single-pass com bundle da própria categoria
        bundle = disc if rec.tipo_sinal.categoria == "Discrete" else ana
        d = _classificar_sinal(rec, bundle, ...)
        ...
        return d, None if decidido else (None, ItemRevisao(...))

    # ─── Dual-pass com barreira de domínio ───
    d_disc = _classificar_sinal(rec, disc, ...)
    d_ana  = _classificar_sinal(rec, ana, ...)
    decidiu_disc = d_disc.status == "decidido"
    decidiu_ana  = d_ana.status == "decidido"

    # Barreira de domínio: cada bundle só conta como "ok" se a categoria do
    # sinal admite aquele domínio (não-binário — cobre DiscreteAnalog/default).
    dominios = _DOMINIOS_POR_CATEGORIA.get(
        rec.tipo_sinal.categoria, frozenset({"Discrete", "Analog"})
    )
    permite_disc = "Discrete" in dominios
    permite_ana = "Analog" in dominios
    ok_disc = decidiu_disc and permite_disc
    ok_ana  = decidiu_ana  and permite_ana

    if ok_disc and ok_ana:
        # Ambos decidiram E ambos no domínio admitido → desempate normal
        vencedor = _desempatar_ambiguo(d_disc, d_ana, disc, ana, ...)
        if vencedor is not None:
            return vencedor, None
        cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
        return None, ItemRevisao(d_disc, motivo="categoria_ambigua", ...)

    if decidiu_disc and decidiu_ana:
        # Ambos decidiram, mas a barreira bloqueia ao menos um → conflito
        # real entre domínios. NÃO auto-aceita o lado "permitido": categoria
        # pode ser placeholder sem evidência (ver nota acima). Vai pra
        # revisão igual ao caso "ambos no mesmo domínio e inconclusivo".
        cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
        base = d_disc if permite_disc else d_ana
        return None, ItemRevisao(base, motivo="categoria_ambigua", candidatos_sugeridos=cands)

    if ok_disc:
        return d_disc, None       # ✅ só Discrete decidiu, categoria admite — sem conflito
    if ok_ana:
        return d_ana, None        # ✅ só Analog decidiu, categoria admite — sem conflito

    # Nenhum bundle decidiu DENTRO do domínio admitido. Distingue dois motivos:
    #  - nenhum bundle decidiu em lugar nenhum → "score_baixo"
    #  - só o bundle do domínio BARRADO decidiu (FP cross-categoria evitado,
    #    sem conflito porque o lado admitido nem tentou) → "categoria_incompativel"
    decidiu_fora = decidiu_disc or decidiu_ana
    base = d_disc if permite_disc else (d_ana if permite_ana else d_disc)
    motivo = "categoria_incompativel" if decidiu_fora else "score_baixo"
    cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
    return None, ItemRevisao(base, motivo=motivo, candidatos_sugeridos=cands)
```

> **Por que `motivo` distinto.** Esta spec nasceu de *analisar a auditoria*.
> Reusar `score_baixo` para o caso de domínio (bundle errado decidiu, certo
> não) cega a próxima análise: não dá para separar "sinal genuinamente fraco"
> de "FP cross-categoria barrado". O valor novo `categoria_incompativel`
> precisa ser adicionado ao docstring de `ItemRevisao.motivo` em
> `contracts.py:134`.

### Casos de borda

| Cenário | Comportamento atual (errado) | Comportamento novo (correto) | `motivo` |
|---|---|---|---|
| Sinal Analog, só Discrete decide (ana não decide) | `32` é aceito (FP) | Revisão — base = `d_ana` | `categoria_incompativel` |
| Sinal Discrete, só Analog decide (disc não decide) | `VCC1` é aceito (FP) | Revisão — base = `d_disc` | `categoria_incompativel` |
| Sinal Analog, nenhum bundle decide | Revisão | Revisão — base = `d_ana` | `score_baixo` |
| Sinal Analog, **ambos** decidem (disc E ana) | Auto-aceita o vencedor do desempate, podendo escolher `32` (FP) | Revisão — conflito real, não auto-aceita o lado "permitido" mesmo descartando o barrado | `categoria_ambigua` |
| Sinal `DiscreteAnalog`, ambos decidem (só ground-truth hoje) | — | Ambos os domínios são admitidos → desempate normal (gap/centroide), igual ao dual-pass livre de antes | — / `categoria_ambigua` se desempate inconclusivo |
| Sinal `DiscreteAnalog`, só um decide | — | Aceita — sem conflito, domínio admite | — |
| Categoria nova/vazia (default) | — | Mantém dual-pass livre (`.get(..., {"Discrete","Analog"})`) | — |
| Sinal Analog, só bundle ana decide (sem conflito) | Funciona igual (correto) | Funciona igual | — |

### Efeito esperado (confirmado — ver "Resultado medido" abaixo)

- **FPs cross-categoria eliminados na raiz** — sem precisar de regras manuais por padrão de descrição (240 medidos no dataset real, mesma ordem de grandeza dos 213 da auditoria original)
- **Recall não caiu**: `decididos` na lista final ficou idêntico (510→510) — esses sinais nunca chegavam ao TDT mesmo antes (módulo indefinido sempre vai pra revisão), então não havia recall real a perder; o que existia era um rótulo/candidato enganoso dentro da própria revisão
- Sinais que **já** estavam indo para o bundle correto continuam funcionando sem mudança

---

## Estratégia de Rollout

1. ~~Implementar a mudança~~ ✅ feito em `pipeline._classificar_roteado` (barreira de domínio + `_DOMINIOS_POR_CATEGORIA` + motivo distinto)
2. ~~Rodar o benchmark~~ ⏭️ **pulado, deliberadamente.** `bench/benchmark.py` mede precisão/recall de matching (tfidf/vetorial/fuzzy/consenso) contra `ROTULOS`, chamando `roteador.rotear` direto — nunca passa por `pipeline._classificar_roteado`. A barreira de domínio desta spec vive inteiramente na orquestração do dual-pass, fora do código que o benchmark exercita. Rodá-lo não teria mostrado nenhuma diferença (confirmado: é o que já estava documentado em "Artefatos" antes mesmo de rodar).
3. ~~Rodar pipeline completo~~ ✅ feito — `docs/GTD - Lista de Pontos V11.xlsx`, comparando a árvore de trabalho antes/depois da mudança via `git stash` (script em `run_pipeline_real.py`, descartável)
4. ~~Comparar auditoria~~ ✅ feito — ver "Resultado medido" abaixo
5. **Recall não caiu** (decididos finais idênticos: 510 antes e depois) — não foi preciso ajustar thresholds do bundle analógico

### Resultado medido

Rodando `pipeline.executar()` no input real (`docs/GTD - Lista de Pontos V11.xlsx`,
config default, sem subestação detectável automaticamente → `subestacao="X"`),
comparando a árvore de trabalho **antes** (`git stash`) e **depois** do fix:

| Métrica | Antes | Depois | Δ |
|---|---|---|---|
| `decididos` (lista final/TDT) | 510 | 510 | 0 |
| `revisão` (total) | 1824 | 1824 | 0 |
| FPs cross-categoria na lista final | 0 | 0 | 0 |
| **FPs cross-categoria em itens de revisão com `status="decidido"`** | **240** | **0** | **-240** |

A 3ª linha já estava em 0 nos dois — confirma que `identidade_modulo.py`'s
`ids_indefinidos` já impedia esses sinais de entrar no TDT final, antes e
depois do fix (achado da revisão de design: módulo indefinido sempre vai
pra revisão, nunca é auto-aceito). A 4ª linha é a métrica real do problema
original: `gerar_relatorio_revisao` (`Auditoria_Revisao.xlsx`) escreve
`registro.status` e `registro.sigla_sinal` **mesmo para itens de revisão**
— então um sinal roteado pra revisão por `modulo_indefinido` mas com
`status="decidido"` aparecia na planilha com uma sigla cross-categoria
"decidida" (ex.: `'Potência Ativa' → sigla '32', categoria 'Analog'` —
exatamente o exemplo citado no Diagnóstico), mesmo nunca tendo entrado no
TDT. Essa é a origem real dos "213 sinais decididos com sigla incompatível"
da auditoria — a métrica desta rodada (240) confirma o fenômeno na mesma
ordem de grandeza, no dataset atual. O fix zera essa contagem sem mover
`decididos` nem o total de `revisão` — é puramente uma correção de rótulo
e candidato dentro do que já ia para revisão (breakdown de motivo migrou:
`modulo_indefinido` 758→206, com os 552 restantes reclassificados em
`categoria_incompativel` 147 + `categoria_ambigua` 405).

---

## Artefatos

- Mudança localizada em `src/tdt/pipeline.py:242-277` + constante `_DOMINIOS_POR_CATEGORIA`
- Novo valor `categoria_incompativel` no docstring de `ItemRevisao.motivo` (`contracts.py:134`)
- Teste existente **atualizado** em `tests/test_pipeline.py`:
  `test_classificar_roteado_categoria_incerta_ambos_decidem_categoria_ambigua`
  — antes esperava `decidido is not None` (auto-aceitava o desempate livre);
  agora, com `categoria="Discrete"` fixo na fixture, o domínio `Analog` é
  barrado e os dois bundles decidem → conflito real → `decidido is None`,
  `item.motivo == "categoria_ambigua"` (não mais o desempate por gap/centroide,
  que só roda quando os dois domínios decididos são admitidos)
- Testes novos em `tests/test_pipeline.py`, cobrindo os quadrantes da tabela de borda:
  - `test_dual_pass_barra_dominio_so_bundle_errado_decide` (categoria Analog, só disc decide) → revisão `categoria_incompativel`, base `d_ana`
  - `test_dual_pass_score_baixo_nos_dois` → revisão `score_baixo` (já existia, sem mudança)
  - `test_dual_pass_discreteanalog_ambos_decidem_aceita_desempate` → categoria `DiscreteAnalog`, ambos decidem → desempate normal (não vira `categoria_ambigua` automaticamente)
  - `test_dual_pass_discreteanalog_so_um_decide_aceita` → categoria `DiscreteAnalog`, só um decide → aceita sem conflito
- Benchmark em `bench/benchmark.py` não muda (já mede precisão)

---

## Não escopo

- Não altera `categoria_confiavel` — quem define isso continua sendo `estruturador` e `identidade_modulo`
- Não altera o `_desempatar_ambiguo` — só muda quais candidatos chegam lá
- Não adiciona regras no `motor_regras.py` — a correção é estrutural, não cosmética. A barreira de domínio **tem** que viver na orquestração (`_classificar_roteado`): cada bundle só enxerga siglas da própria categoria, então `filtro_preciso` (que roda dentro de um único bundle) jamais veria o conflito cross-categoria.

---

## Apêndice — Melhorias adjacentes no motor de regras (specs separadas)

Levantadas na revisão desta spec. **Fora do escopo do fix de categoria** —
cada uma vira sua própria spec/PR. Listadas aqui para não se perderem.

### M-A · Ramo de penalidade morto em `r1_numero_protecao`

Em `_classificar_sinal`, `filtro_preciso.filtrar` roda **antes** de
`motor_regras.aplicar_rastreado` (`pipeline.py:193` vs `:195`). `f_r1` já
*remove* candidatos com número ANSI líder divergente, então o ramo
`-peso ... diverge` de `r1_numero_protecao` quase nunca encontra candidato
sobrevivente para penalizar — é código morto no caminho normal. O boost
positivo continua válido. Mesma redundância parcial existe entre
`r2`/`f_r2` e `r6`/`f_r6`. **Ação:** consolidar ou documentar a divisão de
trabalho (filtro = hard negative, motor = soft positive).

### M-B · Deltas das regras sem saturação/clamp

`aplicar_rastreado` soma deltas ilimitadamente (`r1`+`r3`+`r6` empilham) e
reordena por cima dos scores **já calibrados** da fusão. Como o score
alimenta o threshold/gap do `roteador`, um empilhamento positivo pode
empurrar um candidato marginal acima do threshold → o mesmo tipo de decisão
falsa que esta spec combate, só que **dentro** do domínio. **Ação:** clampar
`delta_total` a uma faixa bounded (ex.: `±2·max(pesos_regras)`) antes de
somar ao score.

### M-C · Gate de abstenção competitivo

Toda regra pontua candidato isoladamente; nenhuma observa o conjunto. A
barreira de categoria desta spec é um caso particular de "abster quando o
vencedor não tem evidência estrutural a favor". **Generalização:** se o top
candidato vence apenas por fuzzy/embedding e **nenhuma** regra disparou
delta positivo sobre ele, mandar para revisão em vez de decidir. Pegaria os
FPs de descrição genérica ("Potência Ativa", "Grupo de Ajustes 1") *além*
do recorte cross-categoria — atacando a mesma causa raiz descrita em "Por
que acontece".
