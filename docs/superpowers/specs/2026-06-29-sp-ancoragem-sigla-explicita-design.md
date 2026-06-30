# SP Ancoragem — Sigla explícita na descrição como âncora de classificação

**Data:** 2026-06-29
**Status:** Proposto (diagnóstico medido em dado real — ver "Evidência" abaixo)
**Origem:** Revisão manual da lista GTD + análise de `output/Auditoria_Revisao.xlsx`. Sinais cuja descrição **contém a própria sigla** (ex.: "Proteção 67 N Temporizado (TOC)") foram decididos para uma sigla de **outra família** (`PRTF`), ignorando a evidência mais forte que existia no texto.
**Escopo:** Adicionar um estágio determinístico de **ancoragem por sigla** ao motor de classificação (`_classificar_sinal`): quando uma sigla da lista padrão aparece literalmente na descrição, ela (e sua família de filhos) entra como candidato de alta confiança; o complemento da descrição seleciona o filho correto. Cobre siglas com ou sem filhos.
**Relacionada:** [2026-06-29-sp-categoria-dual-pass-fix-design.md](2026-06-29-sp-categoria-dual-pass-fix-design.md) (barreira de domínio — composição descrita em "Integração"). Reusa o mecanismo de filhos de `expansao_candidatos.py` e a seleção por discriminadores de `filtro_preciso.filtrar_especificidade`.

---

## Diagnóstico

### Problema

O motor (`pipeline._classificar_sinal`) pontua candidatos por similaridade de **descrição** (tfidf + vetorial + fuzzy), expande filhos dos candidatos sobreviventes, filtra contraditórios e aplica deltas de regras. Em nenhum ponto ele trata a **presença literal de uma sigla no texto** como sinal de primeira classe.

Quando o redator escreveu a sigla explicitamente — "Proteção **67 N** Temporizado", "Relé de Fluxo (**63C**)", "Corrente de Desbalanço (**61N**)" — essa é a evidência mais forte e menos ambígua que existe sobre a identidade do sinal. Hoje ela é diluída em fuzzy/embedding e, na prática, **perde** para a descrição genérica de outra sigla.

### Caso que originou a spec

| ID | Descrição bruta | Decidido | Deveria ser (família) |
|---|---|---|---|
| `…GTA_P:107` | Proteção 67 N Temporizado (TOC) - Atuado | `PRTF` | `67N…` (67NT/67NTD) |
| `…GTA_P:105` | Proteção 67 N - Estágio 1 - Atuado | `PBF1` | `67N1` |
| `BC1_P1:58` | Proteção 50 N - Estágio 1 - Atuado | `PBF1` | `50N1` |
| `BC1_P1:61` | Proteção Corrente de Desbalanço (61N) - Alarme | `PRTF` | `61N` |
| `TR1_P:120` | Relé de Fluxo (63C) - Atuado | `OLFL` | `63C` |

`PRTF`/`PBF1`/`OLFL`/`RGBL` são siglas de descrição genérica ("Proteção … Atuado") que vencem por similaridade textual com a parte *não-sigla* da frase.

### Por que o motor atual não pega

1. **Os scorers não trazem a sigla certa.** Medição: em **0 dos 132** casos a família correta aparece sequer no top-3 de candidatos (ver "Evidência"). Logo um *boost* de score (como `r1_numero_protecao`) é inútil — não há candidato a reforçar. **É preciso injetar o candidato.**
2. **`r1_numero_protecao` / `f_r1` são estreitos.** Só agem sobre o conjunto hardcoded `_NUMEROS_PROTECAO` (`motor_regras.py:48`), que **não inclui 61, 62, 63** — famílias inteiras ficam sem proteção. E mesmo dentro do conjunto, só comparam o **número líder de 2 dígitos**: `PRTF`/`PBF1` não têm líder numérico, então `f_r1` os mantém em vez de removê-los.
3. **`expansao_candidatos` só expande filhos de candidatos já presentes** (`expansao_candidatos.py:71`). Se o pai (`67N`) nunca entrou como candidato, seus filhos também não entram.

### Evidência (medida em `output/Auditoria_Revisao.xlsx`)

Detector aplicado: siglas "específicas" da lista padrão (`Pontos Padrao ADMS_v5.xlsx`) — as que têm dígito **e** letra e `len >= 3` (ex.: `67N`, `50N`, `61N`, `62BF`, `63C`) — procuradas como token na descrição, incluindo junção de tokens adjacentes (`"67" + "N"` → `67N`). Conta-se erro quando a sigla decidida **não** pertence à família detectada.

| Métrica | Valor |
|---|---|
| Casos com sigla específica embutida no texto **e** decisão de outra família | **132** |
| …todos com `status="decidido"` | 132 / 132 |
| …em que a família correta aparece no **top-3** de candidatos | **0 / 132** |
| Quebra por `motivo` de revisão | `endereco_duplicado` 85 · `categoria_ambigua` 21 · `modulo_indefinido` 12 · (nenhum/foi pra TDT) 14 |

> A coluna "motivo" mostra que muitos desses 132 caíram em revisão por **outro** gate (endereço duplicado, módulo indefinido) — mas com a sigla errada já gravada em `registro.sigla_sinal`, exatamente como em `categoria_incompativel` da spec de categoria: o rótulo enganoso contamina a auditoria e qualquer auto-aceite futuro. Os 14 sem motivo foram para o TDT com a sigla errada.

> ⚠️ **A normalização (N0) AJUDA aqui.** Verificado: `canonizar("Proteção 67 N Temporizado (TOC) - Atuado")` → `"PROTECAO 67N TEMPORIZADO TOC ATUADO"` e `"Proteção 50 N - Estágio 1"` → `"PROTECAO 50N E1"`. O canonizador **junta** "67 N"→"67N" e "50 N"→"50N", e preserva "61N"/"63C". Logo o detector pode rodar sobre `rec.descricoes.normalizada` — a sigla já vem contígua na maioria dos casos. (Exceção: "67 ABC" permanece separado; tratado no caso de borda.)

---

## Solução Proposta

### Princípio

> Uma sigla da lista padrão escrita literalmente na descrição é evidência de identidade de primeira classe. Ela deve **entrar como candidato** (com seus filhos), e o complemento da descrição seleciona o filho correto.

Um novo estágio **`ancoragem_sigla`** roda dentro de `_classificar_sinal`, **antes** de `expansao_candidatos.expandir`, compondo com o que já existe:

```
scorers (tfidf/vet/fuzzy) ─► mescla ─► [ANCORAGEM: ancorar] ─► expansão (família) ─►
  [ANCORAGEM: filtrar_subarvore] ─► filtro_preciso ─► filtro_especificidade ─► motor_regras ─► roteador
        │              │                    │                     │
        │              │                    │                     └─ r3 fase / r4 estágio pontuam o filho certo
        │              │                    └─ "Temporizado"→T, "E1"→1: descarta filhos que casam menos discriminadores
        │              └─ restringe a família ancorada ao sub-ramo da âncora (67N → remove 67F*/67P*/67_*)
        └─ injeta a sigla detectada + abre a família via expansão já existente
```

A ancoragem **não decide sozinha**: ela garante que a sigla certa e sua família entrem na disputa. A seleção do filho específico continua sendo feita pelos módulos existentes (`filtrar_especificidade` por discriminadores + `r4_estagio`/`r3_fase`), agora com candidatos para trabalhar.

### Detecção (`ancoragem_sigla.detectar`)

Roda sobre os tokens de `rec.descricoes.normalizada` e o índice de siglas da **categoria do bundle** (cada bundle só conhece as siglas da sua categoria — ver "Integração"):

1. **Âncora exata** — token que é uma sigla específica da LP (dígito + letra, `len >= 3`): `67N`, `50N`, `61N`, `63C`, `62BF`. Confiança alta.
2. **Âncora por junção** — par de tokens adjacentes cuja concatenação é uma sigla válida da LP: `"67" + "N"` → `67N`. Cobre o pedido explícito de *"juntar as duas siglas pra ver se viram uma só"* e os casos que o canonizador não juntou. Confiança alta.
3. **Âncora de família (fraca)** — número ANSI líder isolado (`67`, `50`) **sem** sufixo, só quando acompanhado de contexto de proteção (token "PROTECAO"/"PROTEÇÃO" ou afim). Abre a família como candidatos, mas **nunca força decisão sozinha** — deixa o complemento ("ABC"→fase, "E1"→estágio) e o roteador decidirem. Confiança baixa.

> **Guarda de precisão — números nus são perigosos.** A auditoria tem 10 falsos do tipo `"Disj. 52-21 (21Q0)"`, onde **"21" é número de disjuntor, não ANSI 21**. Por isso âncora exata/junção exige sigla **específica** (dígito+letra); número nu (passo 3) só ancora a família, com confiança baixa e exigindo contexto de proteção, e jamais decide isolado. O recorte "específica" é precisamente o que produz os 132 erros limpos da Evidência, sem capturar os 10 falsos de número de disjuntor.

### Injeção (`ancoragem_sigla.ancorar`)

Para cada âncora detectada, injeta (ou re-pontua, se já presente) um `Candidato`:

```python
Candidato(sigla=ancora.sigla, score=<score_ancora>, fonte="ancora_sigla")
```

- `score_ancora` para âncora exata/junção: alto o bastante para limpar `threshold_pct` **com gap** sobre os candidatos textuais genéricos, mas **abaixo de 1.0** para não atropelar a seleção de filho — os filhos entram via expansão com `score * fator_score` e o complemento decide entre eles. Calibrável em `config` (não hardcoded), seguindo o padrão de `pesos_regras`.
- Âncora de família (número nu): injeta o **pai** com score modesto; a expansão abre os filhos e a decisão fica a cargo de `filtrar_especificidade` + regras.

A expansão existente (`expansao_candidatos.expandir`) já transforma a âncora `67N` em `67N1, 67N2, 67NT, 67NTD, …` (todos os filhos do prefixo na LP). O `filtrar_especificidade` então mantém só os que casam o máximo de discriminadores do texto ("Temporizado"→`67NT/67NTD`, "Estágio 1"+"E1"→`67N1`), e `r4_estagio`/`r3_fase` desempatam.

### Restrição ao sub-ramo da âncora (`ancoragem_sigla.filtrar_subarvore`)

> **Regressão observada na 1ª implementação:** com a âncora `67N` injetada, o sinal *"Proteção 67 N - Estágio 2"* passou a decidir **`67P2`** (ramo de **fase**, errado), não `67N2`.

**Causa-raiz:** `expansao_candidatos.expandir` abre a família pelo **prefixo de 2 dígitos** (`67`), reintroduzindo os ramos irmãos `67F*` (fase), `67P*` (fase temporizada) e `67_*` (genérico). O problema é que as descrições-padrão discriminam por **palavra** ("NEUTRO" vs "FASE"), mas o texto de entrada traz só a sigla `67N` — a palavra "NEUTRO" nunca aparece. Assim o `filtrar_especificidade` casa apenas "E2" e **empata** `67N2`, `67F2`, `67P2`, `67_2`; após `r1`+`r4` os deltas iguais mantêm o empate e o desempate arbitrário pode eleger o irmão errado.

A informação que desfaz o empate está na **letra da própria âncora** (`N` = neutro), que o matching de palavras descarta. A correção restitui essa informação: depois da expansão, `filtrar_subarvore` mantém, **dentro de cada família ANSI ancorada**, só os candidatos cuja sigla **começa com** uma das siglas-âncora daquela família (`67N` → mantém `67N, 67N1, 67N2, 67NT, 67NT2, …`; remove `67F2, 67P2, 67_2`). Famílias sem âncora ficam intactas; nunca esvazia (fallback devolve o conjunto original). Múltiplas âncoras na mesma família (`67N` + `67F`) preservam ambos os sub-ramos.

Resultado medido no input real (`docs/GTD - Lista de Pontos V11.xlsx`, `Pontos Padrao ADMS_v2`): `67 N - Estágio 1`→`67N1`, `67 N - Estágio 2`→`67N2`, `67N REVERSE`→`67NR`, `67N FOWARD`→`67N`; os ramos de fase desaparecem e os casos genuinamente ambíguos (`67NT` vs `67NT2`) vão para revisão com os candidatos certos no topo.

### Múltiplas siglas distintas

Quando a detecção acha **duas ou mais âncoras de famílias diferentes** que não se resolvem por junção:

1. **Junção primeiro.** Se forem adjacentes e concatenarem numa sigla válida, vira **uma** âncora (caso 2 acima). Sem ambiguidade.
2. **Complemento decide.** Se o complemento favorece uma delas — alguma âncora tem filho que casa discriminadores do texto e a(s) outra(s) não — ancora-se a favorecida. Cobre *"a descrição que complementa dá a entender que é um dos sinais"*.
3. **Ambíguo genuíno.** Duas âncoras válidas, sem junção, complemento não desempata → **revisão** com `motivo="sigla_multipla"`, `candidatos_sugeridos` = as âncoras ordenadas pela mais provável (maior afinidade do complemento / maior score textual). Cobre *"mandar pra revisão mostrando qual é o mais possível"*.

### Sinais sem filhos

A ancoragem **não depende de filhos**. Para uma sigla folha (sem variantes de prefixo na LP — ex.: `63C`, `OLFL`), a âncora exata injeta o próprio candidato e a expansão simplesmente não adiciona nada; o roteador decide a sigla âncora diretamente. Atende *"essa análise deve existir pra todos os sinais, que tenham filhos ou não"*.

### Integração com a barreira de domínio (spec de categoria)

`_classificar_sinal` roda **uma vez por bundle** (`disc`, `ana`). A detecção usa o índice de siglas **daquele bundle/categoria** — o bundle `disc` só ancora siglas discretas, o `ana` só analógicas. Consequência: no dual-pass de categoria incerta, o bundle da categoria errada **não acha âncora** e não produz decisão espúria — a ancoragem compõe com a barreira de domínio em vez de furá-la.

---

## Casos de borda

| Cenário | Comportamento atual (errado) | Comportamento novo |
|---|---|---|
| "Proteção 67 N Temporizado" (sigla `67N` no texto, família ausente do top-3) | decide `PRTF` (genérico) | ancora `67N`, expande filhos, complemento "Temporizado"→`67NT/67NTD` |
| "Proteção 50 N - Estágio 1" | decide `PBF1` | ancora `50N`, "E1"→`50N1` via `r4_estagio`/especificidade |
| "Relé de Fluxo (63C)" (sigla folha, sem filhos) | decide `OLFL` | ancora `63C`, decide direto |
| "61N"/"62BF" (família fora de `_NUMEROS_PROTECAO`) | decide `PRTF` | ancora a sigla específica — independe do conjunto hardcoded |
| "Disj. 52-21 (21Q0) …" ("21" = nº de disjuntor) | já vai pra revisão/decisão por outras vias | **não ancora** — número nu só com contexto de proteção; "21Q0" não é sigla específica |
| "Proteção 67 ABC - Estágio 1" (sigla escrita "67 ABC", não junta) | `67F1` surgia mas barrava por categoria | âncora de família `67` (nº nu + "PROTECAO") abre a família; "ABC"→fase ABC, "E1"→estágio 1 → `67F1` |
| "Proteção 67 - Bloqueado" (só número nu, complemento ambíguo) | decide `RGBL` | âncora de família fraca; sem filho com complemento casando, **não força** — roteador decide como hoje (fora do recorte dos 132) |
| Duas siglas distintas, junção válida (`67`+`N`) | — | vira âncora única `67N` |
| Duas siglas distintas, complemento favorece uma | — | ancora a favorecida |
| Duas siglas distintas, sem junção, complemento neutro | — | revisão `motivo="sigla_multipla"`, candidatos ordenados |
| Sigla âncora é de categoria oposta à do bundle | — | não detectada (índice por categoria) — não fura a barreira de domínio |

---

## Efeito esperado

- Os **132 erros medidos** passam a ancorar a família correta. Quantos viram decisão certa depende de o complemento selecionar o filho — meta: zerar a decisão de **família errada** (sigla de outra família), reduzindo os "rótulos enganosos" que contaminam a auditoria, análogo ao efeito da spec de categoria.
- **Sem regressão de precisão fora do recorte:** o gate de número nu exige contexto de proteção e nunca decide sozinho; siglas específicas têm colisão desprezível com identificadores de equipamento (validado contra os 10 falsos de número de disjuntor).
- A seleção fina (filho) reusa `filtrar_especificidade` + `r4`/`r3` — nada de lógica nova de desempate.

---

## Estratégia de Rollout

1. Implementar `src/tdt/ancoragem_sigla.py` (índice por categoria cacheado por `id(lp)`, `detectar`, `ancorar`).
2. Plugar em `_classificar_sinal` antes de `expansao_candidatos.expandir`; propagar a info de "múltiplas siglas" até `_classificar_roteado` para virar `ItemRevisao(motivo="sigla_multipla")`.
3. Config: flag `ancora_sigla_ativa` (default `True`) + `ancora_sigla_score` (ou entrada em `pesos_regras`), calibráveis.
4. Contratos: novo valor `"ancora_sigla"` para `Candidato.fonte` e `"sigla_multipla"` para `ItemRevisao.motivo` (docstring em `contracts.py:79` e `:134`).
5. Testes unitários (ver "Artefatos").
6. Rodar `pipeline.executar()` no input real (`docs/GTD - Lista de Pontos V11.xlsx`), comparar a auditoria antes/depois — métrica primária: nº de sinais com sigla específica no texto decididos para outra família (132 → meta 0), sem mover o total de `decididos`/`revisão` para pior.
7. `bench/benchmark.py` não exercita `_classificar_sinal` (chama `roteador.rotear` direto) — a ancoragem não aparece ali; medir pela auditoria do pipeline completo, como na spec de categoria.

---

## Artefatos

- Novo módulo `src/tdt/ancoragem_sigla.py` (`detectar`, `ancorar`, `filtrar_subarvore`, `tem_multiplas_familias`).
- Hook em `src/tdt/pipeline.py` (`_classificar_sinal`: `ancorar` antes de `expansao_candidatos.expandir`, `filtrar_subarvore` logo depois; propagação de ambiguidade em `_classificar_roteado`).
- Novos campos de config em `src/tdt/config.py` (`ancora_sigla_ativa`, `ancora_sigla_score`).
- Novos valores em `src/tdt/contracts.py`: `Candidato.fonte="ancora_sigla"`, `ItemRevisao.motivo="sigla_multipla"`.
- Testes em `tests/test_ancoragem_sigla.py` cobrindo: âncora exata injeta candidato ausente; junção `67`+`N`→`67N`; complemento seleciona filho (`67NT` vs `67N1`); sigla folha sem filhos (`63C`); número nu de disjuntor **não** ancora; duas siglas → `sigla_multipla`; âncora de categoria oposta não detectada no bundle; `filtrar_subarvore` remove ramo irmão (`67P2`/`67F2` sob âncora `67N`), preserva família não ancorada, trata múltiplas âncoras na mesma família e nunca esvazia.

---

## Não escopo

- **Não substitui** os scorers nem o roteador — ancoragem é um estágio aditivo de candidatos; a decisão final continua no `roteador`.
- **Não amplia** `_NUMEROS_PROTECAO` nem mexe em `r1`/`f_r1` — a correção é injeção de candidato, não ajuste de delta (o boost de `r1` é irrelevante quando não há candidato; ver Diagnóstico §1). Consolidar `r1`/`f_r1` é a melhoria **M-A** da spec de categoria, separada.
- **Não trata** descrição sem sigla escrita (caso genérico "Potência Ativa") — esse é o gate de abstenção competitivo **M-C** da spec de categoria.
- **Não altera** a barreira de domínio — apenas compõe com ela (ancoragem por categoria do bundle).
