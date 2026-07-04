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
