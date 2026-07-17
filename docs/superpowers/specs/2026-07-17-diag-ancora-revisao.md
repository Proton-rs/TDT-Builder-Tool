# Diagnóstico: âncora de sigla → revisão + partição por classe de MM (SP-OBS-17JUL, P5 Fase-0)

**Script:** `bench/diag_ancora_revisao.py` (`PYTHONPATH=src python bench/diag_ancora_revisao.py`)
**Log completo:** `bench/resultados/diag_ancora_revisao.log`
**Listas reais rodadas:** GTD (`docs/input_nao_homogeneo_1_GTA.xlsx`), IMA
(`docs/input_homogeneo_IMA.xlsx`), FWB (`docs/input_nao_homogeneo_2_FWB.xlsx`),
GPR (`docs/input_nao_homogeneo_3_GPR.xlsx`), GAU (`docs/input_nao_homogeneo_4_GAU.xlsx`).
**Lista padrão:** `docs/Pontos Padrao ADMS_v8.xlsx` (única garantida com aba DE->PARA).

Diagnóstico puro — nenhum módulo de matching/scoring foi alterado. Nenhum gate de
bench aplicável (nada em produção mudou).

## Parte 1 — casos âncora → revisão

Total de registros com `ancoragem_sigla.detectar(...)` não-vazio E `status !=
"decidido"`, somando as 5 listas: **311**.

Distribuição por lista: GTD=68, FWB=95, IMA=148, **GPR=0, GAU=0** (nenhum
registro anchor+revisão nessas duas — não há achado a investigar ali com este
diagnóstico).

Distribuição por `motivo` (campo estrutural de `ItemRevisao`):

| motivo | GTD | FWB | IMA | total |
|---|---|---|---|---|
| score_baixo | 44 | 39 | — | 83 |
| sigla_multipla | — | 10 | — | 10 |
| custom_id_duplicado | 20 | 16 | — | 36 |
| modulo_indefinido | — | 26 | — | 26 |
| modulo_duplicado_entre_sheets | 4 | — | — | 4 |
| equipamento_conflitante | — | 4 | — | 4 |
| nome_sigla_inconsistente | — | — | 148 | 148 |

**Achado prévio à classificação H1/H2/H3:** só os motivos `score_baixo` (83) e
`sigla_multipla` (10) — 93 casos, 30% do total — passam pelo funil de scoring
do pipeline (`pipeline._classificar_roteado`, que é o único lugar que popula
`ItemRevisao.candidatos_sugeridos`). Os outros 218 casos (70%) são rejeitados
por gates ESTRUTURAIS anteriores/paralelos ao scoring — `custom_id_duplicado`
(dedupe de id customizado), `modulo_indefinido`/`modulo_duplicado_entre_sheets`
(identidade de módulo), `equipamento_conflitante`, `nome_sigla_inconsistente`
(coluna SIGLA × NOME diverge, só em listas homogêneas como IMA) — nenhum deles
constrói `ItemRevisao` com candidatos sugeridos (verificado por grep de todos
os call-sites de `ItemRevisao(...)` no código). Classificá-los como H1/H2/H3
seria vácuo (não há top-3 para avaliar) — são reportados à parte, tag
`estrutural`, e EXCLUÍDOS da contagem das hipóteses abaixo. A presença da
âncora nesses 218 casos é, na prática, irrelevante para a causa da ida a
revisão — a decisão nunca chega a comparar sigla-texto.

### Veredito por hipótese (base: 93 casos que passam pelo funil de scoring)

- **H1 (variantes da mesma família da âncora aparecem no top-3 sugerido):
  CONFIRMADA (75 casos, 81% dos 93).** Padrão dominante: âncora exata
  (`51N`, `67N`, `50N/51N`) presente no texto, mas o top-3 devolvido pelo
  roteador é só de IRMÃOS mais específicos da mesma família ANSI (`51N1`,
  `51N2`, `51NL`; `67NT`, `67NT2`, `67NT1`), todos empatados em score 1.0
  (`gap=0.00`) — a expansão por família (`expansao_candidatos`) reintroduz
  vários irmãos com a mesma pontuação e nenhum discrimina o certo por texto.
- **H2 (`score - ajuste < config.piso_decisao`, roteador `_quadrante`):
  NÃO CONFIRMADA (0 casos).** Nenhum dos 93 casos tem a justificativa
  `"confiança calibrada X < piso Y"` que `roteador._quadrante` grava quando o
  piso absoluto rejeita — todos os 93 são rejeitados pelo braço `ambíguo
  (%=.., gap=..)` (pct_ok mas gap insuficiente, ou pct/gap ambos baixos), não
  pelo piso. O piso absoluto (SP-CVA E2) não é a causa observada nesta
  amostra.
- **H3 (nenhuma sigla-âncora sobrevive no top-3 sugerido): CONFIRMADA
  (83 casos, 89% dos 93).** Em quase todos os casos H1 a âncora exata
  (`51N`) desaparece do top-3 — só sobrevivem os irmãos mais específicos
  (`51N1`/`51N2`/`51NL`); nos 18 casos H3-sem-H1 (ex. `SF6` vs
  `SFAB`/`SF6B`/`SFFC`, `87B` vs `BLDJ`/`86`/`86C`) o texto empurra o topo
  para siglas de OUTRA família, sem relação com a âncora — indício de
  expansão/scoring que não dá peso suficiente à âncora explícita frente ao
  texto genérico ao redor.
- **outra (nenhuma das 3 hipóteses): 0 casos.** Todo caso que passa pelo
  funil de scoring cai em H1 e/ou H3 (65 casos em ambas, 18 só H3, 10 só H1).

## Parte 2 — partição da lista padrão por família × `classe_do_mm` (generalização 81U1)

Metodologia: agrupa `lp.discretos + lp.analogicos` por família ANSI
(`ancoragem_sigla._familia`); a raiz nua da família (sigla == família, ex.
`"81"`, `"87"`) é EXCLUÍDA da partição — ela é sempre isolada trivialmente
pela classe FUNCAO (INCLUI/EXCLUI) e não é o caso de ambiguidade que o C4
mira (irmãos qualificados que competem entre si).

- Famílias com >= 2 variantes (fora a raiz): **20** de 469 famílias totais.
- Famílias onde **classe_do_mm produz >= 2 grupos não-triviais** (a classe
  discrimina, ainda que não isole a exatamente 1 sigla): **7** —
  `25, 26, 43, 51, 67, 81, 90`.
- Famílias onde alguma classe isola **exatamente 1 sigla** (discriminação
  total, sem precisar de discriminador adicional): **8 ocorrências em 6
  famílias** — `25` (FUNCAO→`25IE`, LOCAL_REMOTO→`25LR`), `26`
  (EVENTO→`263A`, FUNCAO→`2649`), `51` (FUNCAO→`51N`), `67`
  (FUNCAO→`67NX`), `90` (LOCAL_REMOTO→`90LR`, FUNCAO→`90VF`).

### Caso 81 (o caso de estudo original) — confirmado, com ressalva

Família `81`: `ATIVACAO` isola o grupo `{81U1..81U5}` (5 siglas) DISTINTO do
grupo `EVENTO` (`81E1..81E5`, `81IE1/2`, `81O1/2`, `81SU`, `81SO`, `81_T`, 12
siglas) — confirma o padrão esperado pelo usuário/spec ("81 → ATIVACAO isola
81U*"). **Mas, na leitura estrita de "isola exatamente 1 variante", isso NÃO
se confirma**: `ATIVACAO` isola um GRUPO de 5, não uma sigla única — reduz a
ambiguidade de 12→5 candidatos possíveis dentro do grupo compatível, não
resolve sozinho. Fechar em `81U1` exige um discriminador ADICIONAL de
estágio (sufixo numérico `E1`↔`U1`), que este diagnóstico NÃO mede (fora de
escopo — é o mecanismo do C4 descrito na spec, não uma medição). **Contra-
exemplo 87 confirmado**: depois de excluída a raiz nua, os 27 irmãos
restantes de `87` (`87B`, `8750`, `87U1`, `87TT`, ...) são TODOS classe
`EVENTO` (`classe_do_mm` não produz nenhum segundo grupo) — `classe_do_mm`
não discrimina nada dentro da família 87, exatamente como o usuário previu.

## Parte 3 — falso-positivo do léxico (`semantica_estados`)

Corpus: todas as `descricoes.normalizada` (maiúsculas, sem acento) de
registros DECIDIDOS + EM REVISÃO das 5 listas reais, tokenizadas.

**Resultado: nenhum falso-positivo encontrado.** Todos os tokens que casam
por prefixo de `_LEXICO` no corpus real são inflexões legítimas da palavra
pretendida (`ABERTURA`/`ABERTA`←ABERT, `ATUADO`/`ATUADA`←ATUAD,
`BLOQUEIO`/`BLOQUEADO`/`BLOQUEAR`/`BLOQUEADA`←BLOQUE, `DESLIGADO`/
`DESLIGAR`←DESLIGA, `EXCLUIDA`/`EXCLUIDO`/`EXCLUIR`/... ←EXCLUI,
`FECHADO`/`FECHAR`/`FECHAMENTO`←FECHA, `HABILITADA`/`HABILITAR`←HABILITA,
`INCLUIDO`/`INCLUIR`/`INCLUIDA`←INCLUI, `INDEFINIDO`/`INDEFINIDA`←INDEFINID,
`LIGAR`/`LIGADA`/`LIGADO`←LIGA, `REMOTO`←REMOT). A palavra `LOCALIZADOR`
(o bug histórico documentado em `especificidade_qualificador.py:71-90`, onde
o prefixo `"LOCAL"` colidia com ela) **não aparece nenhuma vez** no corpus
real das 5 listas — e o fix já aplicado (`"LOCAL"` como token exato em
`semantica_estados._TOKENS_EXATOS`, não mais radical/prefixo) impediria a
colisão mesmo se aparecesse.

**Veredito: hipótese de FP de léxico NÃO CONFIRMADA nas 5 listas reais
disponíveis neste repo.** Não há evidência, no dado real testável, de que o
léxico atual gera falsos positivos por colisão de prefixo.

## Resumo de veredito (para decisão de Tasks 12–14)

| Hipótese | Veredito | Contagem |
|---|---|---|
| H1 (irmãos da família no top-3) | **CONFIRMADA** | 75/93 casos do funil (81%) |
| H2 (`score - ajuste < piso`) | **NÃO CONFIRMADA** | 0/93 |
| H3 (âncora fora do top-3 final) | **CONFIRMADA** | 83/93 casos do funil (89%) |
| C4 — partição por `classe_do_mm` discrimina | **CONFIRMADA** (parcial) | 7 famílias (`25,26,43,51,67,81,90`); 6 delas isolam 1 sigla direto, `81` isola um grupo de 5 que precisa de discriminador extra (estágio) |
| FP do léxico (`_LEXICO` prefixo) | **NÃO CONFIRMADA** | 0 tokens suspeitos no corpus real |

Casos estruturais (motivo fora do funil de scoring: `custom_id_duplicado`,
`modulo_indefinido`, `modulo_duplicado_entre_sheets`, `equipamento_conflitante`,
`nome_sigla_inconsistente` — 218/311, 70% do total) não avaliam H1/H2/H3 (sem
top-3 populado) — a âncora ali é coincidência textual, não causa da ida a
revisão.
