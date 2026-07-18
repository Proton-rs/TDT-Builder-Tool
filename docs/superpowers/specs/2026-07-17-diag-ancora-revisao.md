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

## Refresh pós-C1/C4 (residual p/ C3) — 2026-07-18

Rerun do mesmo script (`bench/diag_ancora_revisao.py`) contra o HEAD atual,
pós Task 12 (C1 — `desambiguar_variante`/motivo `variante_ambigua`) e Task 14
(C4 — `_desambiguar_por_classe_estado`). Motivação: o classificador original
(Fase-0, acima) não reconhecia `variante_ambigua` como motivo de funil — caso
não corrigido, os casos que o C1 relabelou de `score_baixo`→`variante_ambigua`
cairiam vacuamente no balde `estrutural`, subcontando o residual real.

**Mudanças no script** (diagnóstico puro, nenhum módulo de produção tocado):

1. `_MOTIVOS_FUNIL` ganhou `"variante_ambigua"` — esses casos voltam a ser
   classificados H1/H2/H3 normalmente.
2. Novo campo `resolucao_c1c4` por caso, derivado do `motivo` (não é medição
   nova, é rótulo sobre o que a máquina C1/C4 já tentou — ver
   `pipeline.py:447-464` e `ancoragem_sigla.desambiguar_variante`):
   - `c1_c4_tentado_ainda_ambiguo` (motivo `variante_ambigua`): C1 e C4
     RODARAM (âncora exata, família única) e nenhum dos dois resolveu
     sozinho — ambiguidade genuína, residual real do C1/C4 já entregue.
   - `c1_pulado_multiplas_familias` (motivo `sigla_multipla`): gate
     `not _multiplas` pula C1/C4 de propósito (dual-família, ex. `50N/51N`
     no mesmo texto) — fora do escopo por design, não é falha do C1/C4.
   - `fora_escopo_c1_c4` (demais motivos do funil, ex. `score_baixo`,
     `categoria_incompativel`): vêm do braço de categoria INCERTA
     (`_classificar_roteado` linhas 466-518), que nunca chama
     `desambiguar_variante` — C1/C4 estruturalmente não se aplicam ali.
3. Nova tag `"H3-familia-ausente"`: quando NENHUM candidato do top-3 é da
   família da âncora (zero sobreviventes) — diferente de H1 (>=2 irmãos
   competem, falha de desempate) e da tag nova `"H3-familia-parcial"` (1
   único irmão sobrevive, âncora ainda ausente — visibilidade parcial).
   `H3-familia-ausente` é o alvo real do C3: candidate generation/ranking
   derrubou a família inteira, não é só desempate entre irmãos.

**Rerun (mesmas 5 listas reais: GTD/IMA/FWB/GPR/GAU).** Nota: os inputs
`docs/input_nao_homogeneo_3_GPR.xlsx` e `..._4_GAU.xlsx` não existiam neste
worktree (untracked, presentes só no worktree principal) — copiados de lá
para rodar o diagnóstico completo; nenhum arquivo de produção alterado.

Total bruto (âncora + status != decidido, 5 listas): **409** (vs 311 na
Fase-0 — GPR/GAU agora contribuem porque os inputs estavam ausentes na
Fase-0 original deste worktree, não por regressão). Total do funil de scoring
(inclui `variante_ambigua` agora): **152** casos.

### (1) Total residual funil pós-C1/C4: 152

Por `resolucao_c1c4`: `c1_c4_tentado_ainda_ambiguo`=82,
`c1_pulado_multiplas_familias`=10, `fora_escopo_c1_c4`=60.

### (2) Ainda H1 (irmãos da família competem no top-3): 102/152

Nem todo H1 residual é "falha do C1/C4" — decompondo por `resolucao_c1c4`:

| motivo | contagem H1 | explicação |
|---|---|---|
| `variante_ambigua` | 66 | C1+C4 RODARAM, não resolveram — empate genuíno (`gap=0.00`, todos os irmãos score 1.0, sem discriminador textual nem de MM). Ex.: `51N` → top3 `51NL/51N2/51N1` (todos 1.0); `67N` → `67NT2/67NT/67NT1`. |
| `categoria_incompativel` | 26 | fora do escopo do C1/C4 por construção (braço categoria incerta nunca chama `desambiguar_variante`) — todos em GPR. Ex.: `51N` (Grupo de Ajustes B) → top3 `51N/51NL/51N2`. |
| `sigla_multipla` | 10 | C1 pula de propósito (`not _multiplas`) — dual-família no mesmo texto (`50N/51N` em FWB `AL FWBxx:47`), C1 não decide entre âncoras de famílias diferentes. Esperado, não é bug. |

**Veredito:** C1 resolveu o que se propôs (variante-pai exata quando 1
candidato bate a âncora); os 66 `variante_ambigua`+H1 são casos em que NENHUM
candidato bate a âncora exata dentre os 3 finais (todos irmãos mais
específicos, âncora "crua" nem aparece) — fora do alcance de C1 por design
(exige `sigla == âncora` em `desambiguar_variante`), e C4 não resolveu porque
`classe_do_mm` empata ou não discrimina esses casos específicos (`51N`,
`67N`). Os 10 `sigla_multipla` são o dual-família explicitamente fora de
escopo mencionado no achado. Os 26 `categoria_incompativel` são de outro
braço do pipeline (categoria incerta) — nunca passam por C1/C4.

### (3) H3-familia-ausente (família inteira sumiu do top-3 — alvo real do C3): 34/152

Por `resolucao_c1c4`: `c1_c4_tentado_ainda_ambiguo`=16,
`categoria_incompativel` (`fora_escopo_c1_c4`)=12, `score_baixo`
(`fora_escopo_c1_c4`)=6.

Exemplos (score/família zero no top-3 final):

- `[FWB] BARRA P1:31 / BARRA P2:31` — desc=`"CMD BLOQ 87B"`, âncora exata
  `87B` família `87`, top3=`[('BLDJ',0.59,'mesclado'), ('86',0.537,'mesclado'),
  ('86C',0.47,'expandido')]` — **caso de referência do usuário**, confirmado
  intacto pós-C1/C4 (motivo `score_baixo`, fora do escopo do C1/C4 porque a
  âncora `87B` nunca chega nos candidatos roteados pra começo de conversa —
  não é ambiguidade de variante, é ausência total de candidato).
- `[FWB] AL FWB11:35 / AL FWB12:35 / AL FWB13:35` — desc=`"Disj. 11Q0 (52) -
  BP SF6 (Estág.2) - Bloqueio"`, âncora exata `SF6` família `SF6`,
  top3=`[('SFAB',0.843,'mesclado'), ('SF6B',0.803,'mesclado'),
  ('SFFC',0.794,'mesclado')]` — motivo `variante_ambigua`
  (`c1_c4_tentado_ainda_ambiguo`): C1/C4 RODARAM (âncora exata `SF6`), mas o
  top-3 final populado por `_classificar_roteado` não contém `SF6` nem
  nenhum candidato de família `SF6` — o scoring/expansão já descartou a
  família antes de C1 examinar `rec.candidatos[:3]`.
- `[GPR] SLOT D:9 / SLOT D:29` — desc=`"VF2 - Defeito"`, âncora exata `VF2`
  família `VF2`, top3=`[('FVF2',0.465,'mesclado'), ('DFDJ',0.431,'mesclado'),
  ('DMOT',0.431,'mesclado')]` — motivo `categoria_incompativel`
  (`fora_escopo_c1_c4`, braço categoria incerta).
- `[GPR] LTPCH67:40` — desc=`"DJ - SF6 - Bloqueio"`, âncora exata `SF6`,
  top3=`[('SFAB',0.881,'mesclado'), ('SFFC',0.83,'mesclado'),
  ('SF6B',0.664,'mesclado')]` — mesmo padrão de família `SF6` ausente,
  agora via `categoria_incompativel`.

**Leitura:** `87B`/`SF6`/`VF1`/`VF2` compartilham o mesmo padrão — a âncora
exata está no texto, mas o candidato-gerador (`expansao_candidatos`/scoring
mesclado) nunca reintroduz NENHUM membro da família correta no top-3; o
score vencedor vai para famílias vizinhas por similaridade textual genérica
(`BLDJ`, `86`, `SFAB`, `DFDJ`). Isso é diferente do padrão H1 (`51N`/`67N`),
onde a família correta domina o top-3 mas o desempate entre irmãos falha.
**Este é o alvo de design do C3**, conforme a hipótese original do gate de
decisão do plano.

### (4) H3-familia-parcial (1 irmão presente, âncora ausente — visibilidade parcial): 2/152

Ambos em GPR, motivo `categoria_incompativel`:

- `[GPR] GPR21:43` — desc=`"Proteção 50 N - Estágio 1 - Atuado"`, âncora
  `50N`, top3=`[('50N1',1.0,'expandido'), ('PBF1',0.87,'mesclado'),
  ('PBN1',0.575,'mesclado')]` — só `50N1` (1 irmão) sobrevive; o resto do
  top-3 é de outra família.
- `[GPR] GPR21:44` — desc=`"Proteção 50 N - Estágio 2 - Atuado"`, âncora
  `50N`, top3=`[('PBF2',0.87,'mesclado'), ('50N2',0.661,'mesclado'),
  ('PB2',0.531,'mesclado')]` — só `50N2` sobrevive (posição 2, não 1).

**Leitura:** padrão distinto de "família ausente" — aqui a expansão TROUXE 1
variante certa (a do estágio certo, coincidentemente), mas não junto da
âncora crua nem de outros irmãos, e o texto genérico ("Proteção... Estágio
N... Atuado") empurra candidatos de família alheia pro topo. Amostra pequena
(2 casos, mesma família `50`/mesma lista GPR) — não dá pra generalizar sem
mais dado real, mas é sinal de que a falha de visibilidade parcial existe e é
mecanicamente diferente da ausência total.

### Achado extra: bucket `outra` (14 casos, não pedido mas relevante p/ C3)

Motivo `categoria_incompativel`/`score_baixo`, `fora_escopo_c1_c4`, SEM tag
H1/H2/H3 — a âncora exata está no top-3 (às vezes até top-1, score 1.0/0.85),
mas o registro vai pra revisão por CONFLITO DE CATEGORIA (braço incerto,
`_classificar_roteado` linhas 489-502/509-518), não por falha de
candidato/desempate. Ex.: `[GPR] GPR21:33` desc=`"Telecomando (43TC) -
Excluído"`, top3=`[('43TC',1.0,'mesclado'), ...]` — âncora no topo, mas
revisão por `categoria_ambigua`/`categoria_incompativel`. Fora do escopo do
C3 (não é problema de candidate generation/ranking) — mencionado só para não
confundir com H3-familia-ausente ao ler o log bruto.

### Resumo para o design do C3

| bucket | contagem | é alvo do C3? |
|---|---|---|
| H1 residual (`variante_ambigua`, empate genuíno) | 66 | Não — falha de desempate entre irmãos já visíveis, não de candidate generation |
| H1 residual (`sigla_multipla`, C1 pula) | 10 | Não — fora de escopo por design (dual-família) |
| H1 residual (`categoria_incompativel`) | 26 | Não — outro braço do pipeline (categoria incerta), C1/C4 nem se aplicam |
| **H3-familia-ausente** | **34** | **Sim — família inteira não sobrevive ao candidate generation/ranking, é o alvo real** |
| H3-familia-parcial | 2 | Talvez — amostra pequena, mecanicamente distinto da ausência total, merece nota mas não dado suficiente pra dimensionar |
| `outra` (conflito de categoria, âncora no top-3) | 14 | Não — problema de categoria, não de candidato |

C3 deve mirar os **34 casos H3-familia-ausente** (16 já sobreviveram
C1/C4 sem resolver, 18 nem chegam a passar por C1/C4) — candidate
generation/ranking (`expansao_candidatos`/scoring `mesclado`) descarta a
família inteira da âncora quando o texto ao redor favorece outra família por
similaridade genérica, mesmo com a sigla exata presente no texto bruto.
