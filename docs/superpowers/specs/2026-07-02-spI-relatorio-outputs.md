# SP-I Task 1 — Relatório de outputs (comandos DNP3): pareado / write_legítimo / revisão / ESCAPOU

Data: 2026-07-02 (executado em 2026-07-03). Recipe: LISTA 1 - GTD
(`docs/input_nao_homogeneo_1_GTD.xlsx`, `docs/dnp3_template.xlsx`,
`docs/Pontos Padrao ADMS_v2.xlsx`, `Config()`, `subestacao="GTD"`, via
`tdt.pipeline.executar`). Script: `bench/diag_outputs_sem_par.py`.

## Critérios de classificação (derivados de `src/tdt/dc_pairer.py`)

`tdt.pipeline.executar` roda `dc_pairer.parear(decididos, config)` **uma
única vez**, sobre a lista de registros já **decididos** (i.e. que já
passaram por todo o funil de classificação/filtros/roteador sem cair em
revisão antes). Dentro de `parear`, os registros são agrupados por
`(modulo.nome, eletrico.nome_equipamento, sigla_sinal)` (`_chave`,
`dc_pairer.py:21-25`). Por grupo:

- **sem Output**: nada a fazer — Inputs seguem como estão.
- **Output(s) sem Input**: cada Output cuja `sigla_sinal.upper()` esteja em
  `config.siglas_write_legitimo` (default `frozenset({"CDC"})`) vira um
  `SignalRecord` com `tipo_sinal.direcao == "Output"` que sobra sozinho em
  `resultado.lista.registros` → **write_legítimo**. Os demais viram
  `ItemRevisao(o, motivo="comando_sem_discreto")` → **revisão:
  comando_sem_discreto**.
- **exatamente 1 Input + 1 Output**, e `semantica_estados.compatibilidade_texto`
  aprova o par (gate semântico SP-E/D5): `fundir()` produz UM
  `SignalRecord` com `tipo_sinal.direcao == "InputOutput"` → **pareado**. O
  registro Output original deixa de existir como item próprio (só sobra via
  `enderecamento.indices_saida` do fundido).
- **qualquer outra combinação** (N×M, ou 1×1 que o gate semântico rejeitou):
  catch-all por similaridade fuzzy (`limiar_pareamento_similaridade`,
  default 60.0) — o que casar vira `fundir()` (pareado); o Output que sobra
  vira `ItemRevisao(o, motivo="pareamento_ambiguo")` → **revisão:
  pareamento_ambiguo**.

Ou seja, no resultado final de `tdt.pipeline.executar`:

| Balde | Onde aparece | Campo distintivo |
|---|---|---|
| pareado | `resultado.lista.registros` | `tipo_sinal.direcao == "InputOutput"` |
| write_legítimo | `resultado.lista.registros` | `tipo_sinal.direcao == "Output"` (sobrevive solto) |
| revisão:comando_sem_discreto | `resultado.revisao` | `ItemRevisao.motivo == "comando_sem_discreto"` |
| revisão:pareamento_ambiguo | `resultado.revisao` | `ItemRevisao.motivo == "pareamento_ambiguo"` |
| revisão:\<outro motivo\> | `resultado.revisao` | motivo do roteador/filtros — o comando **nunca chegou** ao `dc_pairer` porque já tinha ido para revisão antes (`status_baixo`, `estado_sem_candidato`, `sem_endereco`, `fora_whitelist_equipamento`, `categoria_ambigua`, ...) |
| ESCAPOU | nenhum dos anteriores | qualquer registro Output/InputOutput fora do modelo — não deveria existir |

`ESCAPOU` no script cobre dois casos defensivos (não observados na prática
nesta lista): (a) um registro decidido com `direcao == "Output"` cuja sigla
NÃO está na whitelist `siglas_write_legitimo` (contradiria a lógica do
`dc_pairer`, que só deixa sobrar Output solto quando a sigla está na
whitelist) e (b) qualquer `direcao` decidida fora de
`{"Output","InputOutput"}` para um registro que entrou como Output no
funil.

## Contagens (LISTA 1 - GTD)

Total de registros Output/InputOutput classificados: **279**

```
pareado: 108
revisao:comando_sem_discreto: 66
revisao:score_baixo: 65
revisao:estado_sem_candidato: 20
revisao:sem_endereco: 12
revisao:fora_whitelist_equipamento: 8
```

`write_legitimo`: **0** (nenhum comando sobrou solto do `dc_pairer` marcado
como write legítimo nesta lista — não há ocorrência de `CDC`, a única sigla
em `config.siglas_write_legitimo`, entre os comandos desta planilha).

`ESCAPOU` (fora do modelo de 3 baldes): **0 casos.** Todo registro
Output/InputOutput do processamento caiu limpo em `pareado` ou em algum
motivo de `revisao`; não há nenhum "buraco" de contrato entre `dc_pairer` e
`pipeline.executar` nesta lista — nenhum comando desaparece silenciosamente
sem aparecer nem em `resultado.lista.registros` nem em `resultado.revisao`.

**Ressalva importante:** o modelo estrito de 3 baldes do brief
(pareado / write_legítimo / revisão) não tem nenhum "buraco de contrato" —
mas o pedido original do usuário ("comandos escapam de todos os baldes")
não se refere a um bug estrutural de contrato, e sim ao fato de que **171
dos 279 outputs (61%)** acabam em revisão manual ao invés de pareados —
sendo que boa parte desses tinha, em algum lugar, um par de status
legítimo que só não foi decidido a tempo do `dc_pairer` ver os dois juntos.
Do ponto de vista do usuário/operador, um comando que devia estar pareado
mas está preso em `score_baixo`/`estado_sem_candidato` **é** um "escapou" —
só não é um escapou do *contrato de dados* do `dc_pairer`, e sim do
*objetivo de domínio* ("comando = output = mesmo sinal"). A investigação de
causa raiz abaixo cobre esse sentido mais amplo, por ser o que interessa
para as tasks de correção subsequentes (Task 2..N).

## Investigação de causa raiz — revisao:comando_sem_discreto (66 casos)

Distribuição por sigla decidida do comando:

```
81U1: 12   81U2: 12   81U3: 12   81U4: 12   81U5: 12   (=60, 91%)
87BL: 2
CMD:  2
PB:   1
AUTC: 1
```

### Padrão A — status nunca decidido (60/66, sigla 81U1..81U5)

Em TODOS os 12 módulos afetados (AL11-AL15, AL21-AL25, TR1_A/TR1_MT,
TR2_A/TR2_MT, TRF-1, TRF-2), o comando `81U<n>` ("Proteção de
SubFrequência Estágio N — Habilitar/Desabilitar") tem, no MESMO módulo do
input original, uma linha de status correspondente ("Proteção 81
Sub-Frequência E\<n\> — Habilitada"). Exemplo concreto — sheet `GTD_11`:

- linha 22: comando `81U1` → decide com candidato único
  `('81U1', score=1.2)` → `comando_sem_discreto`.
- linha 76: status "Proteção 81 Sub-Frequência E1 - Habilitada" → NUNCA
  decide. Vai para `revisao:estado_sem_candidato` com candidatos
  `[('DR81', 0.288), ('81IE1', 0.62), ('81E1', 0.62)]` — nenhum candidato
  suficientemente forte, e o gate `semantica_estados.filtrar_por_estado`
  (SP-E D2) zera os candidatos por incompatibilidade de vocabulário de
  estado (`justificativa="estado_sem_candidato"`).

Ou seja: o par existe nos dados de origem, mas o lado **Input nunca chega
ao `dc_pairer`** porque é descartado ANTES, no funil de
classificação/filtro (`_classificar_roteado` → `estado_sem_candidato`,
`src/tdt/pipeline.py:236-240`). Do ponto de vista do `dc_pairer`, o grupo
`(módulo, equipamento, "81U1")` literalmente não tem nenhum Input — a regra
"sem Input → comando_sem_discreto/write_legítimo" está correta dado o que
ela recebe; o problema é anterior (Padrão A = decisão isolada pré-pairer,
igual ao terceiro cenário levantado no brief). Não é um mismatch de chave
nem um gate do pairer excessivamente estrito — o Input simplesmente não
sobrevive para participar do agrupamento.

Nota: a sigla candidata para o status também não é obviamente `81U1` — os
candidatos vistos (`81IE1`, `81E1`, `DR81`) sugerem que a Lista Padrão pode
não ter uma sigla "Habilitada" dedicada por estágio com boa
correspondência textual a "Sub-Frequência Ex — Habilitada", ou que o filtro
semântico de estado é conservador demais para esse vocabulário
("Habilitada" vs. os estados esperados do MM da sigla candidata). Task de
correção subsequente precisa decidir se é caso de ajustar sigla candidata
na LP, o filtro semântico, ou aceitar que esses ficam em revisão manual
como legítimo (comando existe, mas a LP pode não modelar status "Habilitado
por estágio" granular).

### Padrão B — status decide, mas score baixo/sigla errada (2/66, sigla 87BL)

Módulos `TR1`/`TR2` — TR1_P:31 (comando "Diferencial (87) — Bloqueio /
Desbloqueio", decide `87BL` com candidato único score 0.894). O par de
status existe no MESMO módulo `TR1`: linhas 146 ("Proteção - Diferencial
(87) Bloqueado") e 147 ("... Atuado"). Nenhuma das duas decide como Input:

- linha 146 → `score_baixo`, candidatos top
  `[('87_T',0.876),('87U2',0.813),('8751',0.813),('87Q1',0.813),('87R2',0.813)]`
  — `87BL` (ou uma variante "87 Bloqueado") não aparece nem entre os
  top-5; o texto "Diferencial (87) Bloqueado" não converge para a mesma
  família de sigla do comando.
- linha 147 → `score_baixo`, candidatos top todos ~0.89, também sem
  variante "87 Bloqueado"/"87BL".

Causa raiz: nem chave (módulo bate) nem gate semântico do pairer — de novo
é decisão isolada pré-pairer, mas aqui adicionalmente há um sinal de que a
Lista Padrão pode não ter (ou tem mal rankeada) uma sigla de status
"Diferencial Bloqueado" com boa correspondência textual — os candidatos
retornados são genericamente "87\*" (relé diferencial em geral), não a
variante Bloqueado/Desbloqueado. Mesma família de problema do Padrão A
(perda pré-pairer), causa textual/LP diferente.

### Padrão C — sigla do par diverge entre comando e status (2/66, sigla CMD)

`PSACA_CC:19` — comando "Comando Automatismo PSACA", decide sigla `CMD`
(score 0.607). O status correspondente EXISTE e decide normalmente:
`PSACA_CC:27` ("Painel Serviço Auxiliar CA - Automatismo Incluído") decide
como **Input, sigla `AUTO`**, no MESMO módulo `PSACA`.

Aqui o Input **chega decidido** ao `dc_pairer` — mas com sigla `AUTO`,
enquanto o comando decide `CMD`. A chave de agrupamento
`(modulo, equipamento, sigla_sinal)` usa a sigla LITERAL — `("PSACA", None,
"CMD")` ≠ `("PSACA", None, "AUTO")` — logo caem em grupos DIFERENTES e o
`dc_pairer` nunca os vê juntos. Este é o único caso, dos 66, que é
genuinamente um **mismatch de chave de pareamento** (não perda pré-pairer):
os dois lados decidem, mas com siglas diferentes, e a chave do pairer exige
sigla idêntica. É candidato natural a uma correção futura (ex.: mapa
sigla-comando → sigla-status quando a LP modela os dois lados com nomes
distintos, tipo `CDC`/`CMD` vs. o nome do status).

`PSACA_CC:20` (comando "Comando Iluminação Pátio", sigla `CMD`, score 0.973)
não tem NENHUMA linha de status correspondente em lugar nenhum do input
(varredura por "iluminação"/"pátio" só encontra alarmes de falta de
tensão CA, não um status de iluminação ligada/desligada) — este é
**legítimo comando_sem_discreto por ausência real de dado**, não bug.

### Padrão D — sem contrapartida nos dados de origem (2/66, siglas PB e AUTC)

- `PSACA_CC:21` (comando "Seleção de Barra Preferencial", sigla `PB`) — sem
  status correspondente em lugar nenhum do input (varredura por "barra
  b"/"barra a"/"preferenc" não encontra nada além do próprio comando).
  Legítimo `comando_sem_discreto`.
- `PSACA_CC:22` (comando "Rearme 86 Automatismo", sigla `AUTC`) — comando
  de pulso tipo "reset", sem status de retorno esperado por natureza
  (semelhante a `CDC`, que já está na whitelist de write legítimo). Este é
  o caso mais forte de candidato a ENTRAR em
  `config.siglas_write_legitimo` (hoje só tem `CDC`) — não é uma falha do
  pipeline, é uma sigla de write legítimo não cadastrada na whitelist.

## Investigação de causa raiz — outros motivos de revisão (Output nunca chega ao pairer)

Estes 105 registros (`score_baixo`=65, `estado_sem_candidato`=20,
`sem_endereco`=12, `fora_whitelist_equipamento`=8) são comandos cuja
própria sigla nunca foi decidida — **o roteador/filtro decidiu isoladamente
antes do `dc_pairer` sequer rodar**, então nem chegam a ser avaliados para
pareamento (nem por chave, nem pelo gate semântico). Amostra representativa:

- `01F1_GTA_P:18` "Disj. 52-1 (01Q0) - Desligar / Ligar" → `score_baixo`,
  `justificativa="ambíguo (%=0.81, gap=0.06)"`, candidatos top
  `[('DESLIGAR',0.812),('LIGAR',0.747),('DJA1',0.669)]` — siglas genéricas
  "DESLIGAR"/"LIGAR" (prováveis entradas verbo-genéricas da LP) pontuam
  acima da sigla correta de equipamento `DJA1`. Não é problema de
  pareamento — é problema de scoring/ranking anterior (mesma classe de
  achado já documentado em specs SP-H sobre gap/score_baixo).
- `01F1_GTA_P:22` "Religamento Automático (79) - Excluir / Incluir" →
  `score_baixo`, candidatos `[('79_EXC',0.85),('79_INC',0.83)]` — ambíguo
  entre duas siglas de exceção já documentadas (`79_EXC`/`79_INC`, as
  próprias exceções mencionadas no brief como write legítimo esperado);
  aqui ficam empatadas e vão para revisão em vez de decidir uma.
- `01F1_GTA_P:19` "Secc. 89-2 (01Q1 Barra) - Abrir / Fechar" →
  `estado_sem_candidato`, candidatos `[('PB',0.644),...]` — o gate
  semântico de estado (SP-E D2) zera os candidatos porque o vocabulário
  "Abrir/Fechar" não casa com os estados esperados do MM de `PB`.
- `GTD_11:29` "Recomposição Alimentadores - Comando ligar via PAS" →
  `sem_endereco` — a linha não tem endereço de saída na planilha de
  origem (`Saída Binária` vazia), então nem entra no funil de
  classificação normal (vai direto para revisão com
  `motivo="sem_endereco"`, antes mesmo do roteador).
- `01F1_GTA_P:20` "Secc. 89-4 (01Q2 Linha) - Abrir/Fechar" →
  `fora_whitelist_equipamento` — o equipamento extraído (`01Q2`/Linha) não
  está na whitelist de siglas por equipamento (`config.
  siglas_por_equipamento`, SP-E D6) para os candidatos que sobraram.

Esses 105 casos são, em conjunto, o volume dominante de "comandos que
deveriam estar pareados mas não estão" — mas a causa raiz é
**anterior e externa ao `dc_pairer`**: filtros/scorer de SP-E/SP-G/SP-H já
descartam a decisão antes que o pareamento tenha qualquer chance de atuar.
Corrigir o `dc_pairer` (chave, gate semântico, whitelist de write) não
resolve nenhum desses — são falhas de classificação em outro estágio do
funil, fora do escopo desta task (mas relevantes para priorizar Task 2..N).

## Resumo de causas raiz distintas (para dimensionar Task 2..N)

1. **Perda pré-pairer por filtro/score no lado Input** (Padrão A, 60 casos
   comando_sem_discreto + a maioria dos 20 estado_sem_candidato Output) —
   status nunca decide (gate semântico de estado ou score baixo), então o
   grupo do `dc_pairer` nunca tem Input para casar. Fix candidato: revisar
   candidatos/threshold da LP para siglas "Habilitada"/estado por estágio,
   ou o filtro semântico SP-E D2 para esse vocabulário.
2. **Perda pré-pairer por scoring genérico no lado Output** (Padrão B, 2
   casos 87BL + os 65 score_baixo + 8 fora_whitelist_equipamento + 12
   sem_endereco) — o próprio comando (ou seu par textualmente esperado)
   não decide isoladamente; fora do escopo do `dc_pairer`.
3. **Mismatch de chave sigla-comando × sigla-status** (Padrão C parcial, 1
   caso confirmado: CMD×AUTO em PSACA) — os dois lados decidem mas com
   siglas diferentes; a chave `(modulo, equipamento, sigla_sinal)` do
   `dc_pairer` não casa. Fix candidato: mapa de siglas correlatas
   comando→status quando a LP nomeia os dois lados diferente.
4. **Write legítimo sem contrapartida real nos dados + sigla fora da
   whitelist** (Padrão C/D parcial: AUTC, PB, CMD/Iluminação — 4 casos) —
   comandos de fato standalone (pulso/reset/seleção sem retorno modelado);
   `AUTC` é o caso mais forte de entrar em `config.siglas_write_legitimo`.

Total: **4 causas raiz distintas** identificadas nos 66 casos de
`comando_sem_discreto`, mais uma quinta categoria mais ampla (filtros
upstream do roteador/scorer, motivos `score_baixo`/`estado_sem_candidato`/
`sem_endereco`/`fora_whitelist_equipamento`) que impede 105 outros
comandos de sequer chegar ao `dc_pairer` — essa categoria não é nova (já é
objeto de outras specs SP-G/SP-H sobre score_baixo/gap), mas é responsável
pela maior fatia numérica dos comandos "sem par" nesta lista.

## Sanidade

`python -m pytest -q` executado como checagem — nenhuma alteração em
`src/` feita nesta task (apenas `bench/diag_outputs_sem_par.py` novo).

## Validação final — antes/depois (Task 2, commit 97697bf)

Causas C (parcial) e D corrigidas: `AUTC`/`PB`/`CMD` adicionadas a
`config.siglas_write_legitimo` (antes só `CDC`). Causa C completa
(mismatch de chave `CMD`×`AUTO` em `PSACA_CC:19/27`) foi deliberadamente
**deferida** — caso isolado (1 ocorrência confirmada em ambos os datasets
reais do repo), correção genérica (mapa de correlação de siglas) julgada
de risco desproporcional ao ganho (`CMD` significa Input/status em 27
outros módulos; ver `.superpowers/sdd/spI-task-2-report.md` para a
investigação completa). `PSACA_CC:19` acabou beneficiado como efeito
colateral do fix de `CMD` na whitelist (mesmo grupo que `PSACA_CC:20`),
saindo de `comando_sem_discreto` para `write_legítimo` — não é o
resultado ideal (idealmente fundiria com `PSACA_CC:27`), mas é uma
melhora líquida sobre o estado anterior (revisão obrigatória).

Reexecução de `bench/diag_outputs_sem_par.py` em 2026-07-03 (pós Task 2):

```
                                antes   depois
pareado                          108      108
write_legitimo                     0        4
revisao:comando_sem_discreto      66       62
revisao:score_baixo               65       65
revisao:estado_sem_candidato      20       20
revisao:sem_endereco              12       12
revisao:fora_whitelist_equip.      8        8
ESCAPOU                            0        0
```

`ESCAPOU` permanece 0 nos dois momentos — critério de aceite #2 do design
("zero outputs escapou") já estava satisfeito mesmo antes de qualquer fix
de código, pois o modelo de 3 baldes do `dc_pairer` nunca teve buraco de
contrato nesta lista; o trabalho real da Task 2 foi mover 4 casos
genuinamente mal classificados (`comando_sem_discreto` → `write_legítimo`)
dentro do modelo já correto.

Gate de corretude (`bench/gate_tdt_real.py`, LISTA 1 - GTD vs TDT real):
inalterado em `comum=1042 iguais=637 (61.1%)` antes e depois — esperado,
já que a correção só reclassifica o BALDE de destino (write_legítimo em
vez de revisão), não altera qual sigla é decidida para nenhum registro.

As causas A/B (62 casos) e a categoria mais ampla de 105 registros que
nunca chegam ao `dc_pairer` permanecem **fora de escopo desta SP**
(pertencem a SP-E/SP-G/SP-H — filtros de scoring/semântica de estado
upstream) e foram registradas como follow-up.

**SP-I concluída**: 3/3 tasks (diagnóstico, fix causas C/D, validação).

## Follow-up — causas A/B investigadas (não é bug do `dc_pairer`/D2)

Investigação solicitada: causas A (60 casos, `81U1..81U5`) e B (2 casos,
`87BL`) são (1) LP sem sigla dedicada bem rankeada, ou (2) gate semântico
SP-E D2 conservador demais? Rodado `tdt.pipeline.executar(...,
diagnostico=True)` na LISTA 1 - GTD para capturar os candidatos reais
(pré-D2) e os scores por método (`tfidf`/`vetorial`/`fuzzy`) de cada sigla
envolvida. Resposta: **nenhuma das duas** — é (3), ranking/scoring upstream
(mesma categoria já registrada como fora de escopo).

**Causa A (`GTD_11:76`, "Proteção 81 Sub-Frequência E1 - Habilitada",
`estado_sem_candidato`):** a sigla `81U1` (LP: `AJUSTE PARA 81 E1`,
MM `DESABILITADO@HABILITADO`, classe ATIVACAO — a correta) **nunca aparece
nos candidatos finais** que chegam ao gate D2; o gate recebe só `DR81
(0.288)`, `81IE1 (0.62)`, `81E1 (0.62)` (todos `fonte=mesclado`, i.e.
scorados diretamente, não expandidos por família) e zera os 3 por serem
classe EVENTO (TRIP/DEFEITO) incompatível com ATIVACAO — o D2 está correto
dado o que recebe. O comando irmão (`GTD_11:22`, "...Habilitar/Desabilitar
(81-U1)") decide `81U1` com `tfidf=1.0` só porque o texto **cita a sigla
literalmente** (`"81-U1"`); a linha de status não cita nenhuma sigla, só
descreve o estado ("Habilitada"), e a descrição da LP para `81U1`
("AJUSTE PARA 81 E1") não compartilha vocabulário suficiente com "Proteção
Sub-Frequência ... Habilitada" para pontuar alto em TF-IDF/fuzzy — logo
`81U1` nunca chega a ser candidato viável para o lado Input. Isso é
upstream do `dc_pairer` e do D2 (candidato nem existe na lista que os dois
recebem).

**Causa B (`TR1_P:146/147`, "Diferencial (87) Bloqueado"/"Atuado",
`score_baixo`):** aqui `87BL` (LP: `87 - DIFERENCIAL BLOQUEIO`, MM
`NORMAL@ATUADO`) **aparece nos candidatos**, mas com score baixo (`tfidf
0.068` na linha ":146", `0.489` na ":147") — muito atrás de `87_T` ("87 -
TRIP DIFERENCIAL", `tfidf=1.0`) e de ~20 siglas genéricas da família `87*`
adicionadas por `expansao_candidatos.expandir` (score `0.813`/`0.89`,
`fonte=expandido`, herdado de `87_T` como pai). Confirmado que **não é
questão de classe semântica**: `87BL`, `87_T` e todos os `87*` expandidos
têm o MESMO MM (`NORMAL@ATUADO`, classe EVENTO) — o D2 nem discrimina entre
eles, porque são todos semanticamente compatíveis. A causa é 100%
scoring/ranking (TF-IDF favorece `87_T` por semelhança textual mais forte
+ inundação de candidatos genéricos por expansão de família), decidido
ANTES do `dc_pairer` (`score_baixo` no roteador).

**Conclusão:** causas A e B confirmam — com evidência real, não só
hipótese — a mesma categoria já registrada acima ("perda pré-pairer por
filtro/score", causas #1 e #2 do resumo): scorer (TF-IDF/fuzzy/vetorial) +
expansão de família por prefixo, não o `dc_pairer` nem o gate D2. Fix
aqui seria (a) enriquecer a descrição/sinônimos da LP para `81U*` e `87BL`
com o vocabulário real de campo ("Sub-Frequência", "Bloqueado"), e/ou (b)
penalizar candidatos `fonte=expandido` no desempate de `score_baixo` — as
duas são mudanças de **scorer/dados da LP**, não do `dc_pairer`/`filtro_
preciso`/`semantica_estados`. Continuam **fora do escopo desta SP**
(pertencem a SP-G/SP-H); nenhuma alteração de código feita nesta
investigação — nenhuma hipótese de bug no `dc_pairer` ou no D2 se
confirmou.
