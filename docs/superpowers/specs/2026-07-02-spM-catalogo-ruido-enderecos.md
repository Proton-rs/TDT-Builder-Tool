# SP-M — Catálogo de ruído na detecção de endereço DNP3 (Fase 1: Levantamento)

Data: 2026-07-03
Script: `bench/diag_enderecos.py` (log completo em `bench/resultados/diag_enderecos.log`)

## Escopo: quais arquivos foram tratados como "lista de entrada real"

Levantamento de todo `docs/*.xlsx` (via `git status`/`ls` nos dois worktrees —
este worktree `spk-h-i-j-m-l` e o worktree principal, que tinha GPR/GAU/RGE
adicionados por outra tarefa e foram copiados para cá só para este
levantamento). Critério: é lista de entrada quando é uma planilha de **pontos
supervisionados de uma UTR real** (descrição + endereço/índice por sinal),
não um artefato de outra natureza. Classificação:

| Arquivo | Tratado como lista real? | Motivo |
|---|---|---|
| `input_homogeneo_IMA.xlsx` | Sim | Lista real (SE IMA), formato homogêneo |
| `input_nao_homogeneo_1_GTD.xlsx` | Sim | Lista real (SE GTD), não-homogênea |
| `input_nao_homogeneo_2_FWB.xlsx` | Sim | Lista real (SE FWB), não-homogênea |
| `input_nao_homogeneo_3_GPR.xlsx` | Sim | Lista real (SE Guaporé), não-homogênea |
| `input_nao_homogeneo_4_GAU.xlsx` | Sim | Lista real (SE Gaurama), não-homogênea |
| `RGE GAU 2026 - Lista de Pontos v09.xlsx` | Sim | Lista real (revisão 2026 da mesma SE GAU/RGE) |
| `SAN2_LISTA_PADRONIZADA_PARA_TESTE.xlsx` | Sim | Lista real padronizada (SAN2), usada como fixture de teste |
| `Pontos Padrao ADMS_v1..v6.xlsx` | Não | É a LISTA PADRÃO ADMS de referência (vocabulário/siglas), não uma lista de ENTRADA de UTR |
| `dnp3_template.xlsx`, `iec104_template.xlsx` | Não | Templates de exportação vazios, sem sinais reais |
| `docs/TDT/exportTDT_UTR_{GTD,FWB}_*.xlsx` | Não (usado como GROUND TRUTH) | É SAÍDA do ADMS (TDT exportado), usado aqui só para cross-referência de endereço verdadeiro, não como entrada do detector |
| `mockup_treino_amostra.csv`, demais `.md`/`.json`/imagens | Não | Não são listas de sinais |

7 arquivos, 76 sheets de dados no total, cobrindo os formatos homogêneo e
não-homogêneo, RTUs Siemens/SEL/GE (protocolos DNP3 direto e IEC 60870-5-103
via concentrador COS).

## Critérios de detecção vigentes (lidos no código, não reimplementados)

### Caminho homogêneo (`src/tdt/normalizacao/estruturador_homogeneo.py`)
Sem heurística: a coluna de endereço é a que tem cabeçalho **exato**
`"INDEX DNP3"` (`_col(header, "INDEX DNP3")`, comparação normalizada
maiúscula/sem-acento, literal). Se o cabeçalho não bate em nenhuma coluna,
`detectar_header()` retorna `None` para aquela sheet e o pipeline
(`pipeline.py:562-567`) cai automaticamente no caminho não-homogêneo abaixo.
**Sem ambiguidade possível neste caminho** — é por nome, não por conteúdo.

### Caminho não-homogêneo (`src/tdt/analise/analise_colunas.py::_col_indice`,
chamado via `analisar()`)
Heurística por CONTEÚDO da coluna, sem olhar nome de cabeçalho:

```
frac = (nº células que casam ^-?\d+$) / (nº células não-vazias da coluna)
mono = (nº pares consecutivos estritamente crescentes) / (nº pares)
score = frac * (0.5 + 0.5 * mono)
```
Escolhe a coluna de maior `score`, entre TODAS as colunas da sheet. **Não há
piso mínimo de score, não há checagem de faixa de valores plausível para
endereço DNP3, não há desempate por proximidade textual ao rótulo "Endereço
DNP3"/"DNP3"/"Index"** (o único uso de rótulo/nome de coluna no pipeline é no
caminho homogêneo). Colunas candidatas incluem, na prática: números ANSI
(79/67/51N) quando aparecem soltos em coluna própria, IDs de equipamento,
contadores de linha, registradores Modbus (série 40000+), "Entrada Binária"
(terminal físico do IED), "IED Index"/"IED Obj" (índice interno do IED,
distinto do endereço DNP3 voltado à UTR/SCADA).

### `src/tdt/inferencia_topologia.py` (modelo de blocos contíguos)
**NÃO participa da detecção da coluna de endereço hoje.** É usado só depois
de o endereço já estar extraído, em `subdividir_transformador_at_bt` (C2.4),
para inferir o LADO (AT/BT) de um módulo Transformador a partir de blocos de
endereços contíguos já resolvidos — pista de reforço fraca (pista 3 de 3),
nunca decide sozinha, nunca reescreve o endereço em si. É o "modelo de
blocos" citado no design da SP-M como sinal FUTURO possível para a detecção
de coluna — hoje não é usado com esse propósito.

## Catálogo: padrão de ruído → exemplo real → lista de origem

| # | Padrão de ruído | Exemplo real (coluna/valores) | Lista/sheet de origem | Column escolhida foi a certa? |
|---|---|---|---|---|
| 1 | Registrador Modbus na faixa 40000+ concorrendo com endereço DNP3 (~centenas/milhares) | `SPS_TR1_TR2`/`TR1AT-TM1`/`TR2AT-TM1` (GTD, GPR, RGE): coluna "WORD"/"REGISTRADOR" com valores `40009-41556` vs coluna real "ENDERECO DNP3"/"BIT"/"DNP3" | GTD, GPR, RGE | **Sim** — score do registrador (0.7-0.74) sempre perde para a coluna certa; faixa de valor claramente diferente |
| 2 | "VLAN ID (DEC)" com poucos valores distintos (1-2), quase monotonia zero | `MAPA DE REDE` (IMA): coluna 12 "VLAN ID (DEC)" score=0.491 | IMA | **Sim** — nem chega a ser escolhida (sheet de infraestrutura de rede, não sinais) |
| 3 | "IED Index"/"IED Obj"/"IED Class" (índice interno do IED, não endereço SCADA) concorrendo com "UTR COS Index" (endereço real voltado à UTR) | `AL21`, `03F1 TR1 PP`, `03F2 TR1 PA` (GAU/RGE): "IED Index" score 0.84-0.94, muito perto de "UTR COS Index" | GAU, RGE | **Sim** — "UTR COS Index" é a coluna correta (valores 40,41,42... crescentes por sinal SCADA; "IED Index" é constante/quase-constante por bloco, ex. sempre 30). Confirmado lendo os dados brutos linha a linha. |
| 4 | Contador de linha ("Linha") monotônico >0.9 dentro de blocos, mas reinicia (baixa cardinalidade) — concorre com o endereço real de protocolo | `S4_LOG` (GAU e RGE, mesma sheet): coluna "Linha" (8 valores distintos em ~1140 linhas, faixa 3-90) escolhida como `indice`; coluna real "EndPt(N4)" (967 valores distintos, faixa 100-3110) descartada | **GAU, RGE** | **NÃO — CASO REAL CONFIRMADO** (ver seção final) |
| 5 | "Entrada Binária" (terminal físico do IED, reinicia por bloco Analógicos/Comandos/Digitais) concorrendo com "DNP3.0" (endereço real de protocolo, contínuo dentro do bloco Digitais) | `GPR21`, `GPR31`, `GPR33`, `GPR34`, `GPR35`, `GPR36` (SE Guaporé): coluna 3 "Entrada Binária" escolhida (score 0.84-0.87) em vez da coluna 11 "DNP3.0" (a real) | **GPR** | **NÃO — CASO REAL CONFIRMADO** (ver seção final) |
| 6 | Header verdadeiro não detectado (linha de dado tratada como header) em sheets de relé de linha via concentrador COS (protocolo IEC 60870-5-103) | `LTPCH21`/`LTKNP21`/`LTCAS21`/`LTARV21` (GPR): `_header_por_densidade` aponta linha 7 (dado) em vez da linha 4 (header real); coluna "DNP3.0" nesses relés contém códigos texto (`IDF`/`OR`), não endereço numérico — ambíguo se há endereço DNP3 numérico "verdadeiro" nessas sheets específicas (podem depender de tradução no concentrador COS, fora do escopo deste levantamento) | GPR | **Observação secundária, não contabilizada no veredito** — ground truth incerto para este subconjunto; ver limitações abaixo |
| 7 | "Coluna2..Coluna14" vazias / lixo de planilha (`Coluna2`...) | `AL21` (GAU) linha de header tem ~14 colunas "ColunaN" vazias à direita | GAU | Não afeta escolha (score 0, nunca concorre) |
| 8 | Contador de linha ("Linha") **perfeitamente** monotônico e 100% inteiro sheet-wide (sem reinício, sem gap) — vence mesmo quando a coluna real também tem score alto | Todas as 25 sheets de dados (`LOGICOS`, `SNMP`, `SPS`, `TR1`, `2414 TR1`, `TR2`, `2414 TR2`, `AL FWB11`..`AL FWB25`, `IB P1-T1`, `IB P2-T2`, `IB P1-P2`, `BC1`, `BC2`, `BARRA P1`, `BARRA P2`, `A8000`): coluna 0 "Linha" (score sempre =1.0 de facto por ser sequência pura) vs coluna 17/18 "UTR COS Index" (score 0.655-1.0, a real) | **FWB** | **NÃO — CASO REAL CONFIRMADO** (Caso C, ver seção final) — mesma família do padrão 4, mas a coluna real aqui NUNCA supera o contador de linha, mesmo com score competitivo, porque o contador é monotônico perfeito (não reinicia) |
| 9 | Contador de linha ("Linha") monotônico dentro do bloco visível, mas a coluna real ("UTR COS Index") tem cardinalidade muito baixa (`n=8`) e reinicia dentro da própria sheet (mistura linhas de cabeçalho de bloco/"-" com um sub-bloco de comandos 1..7) | `CALCULADOS` (`docs/RGE GAU 2026 - Lista de Pontos v09.xlsx`): coluna 0 "Linha" (score=1.0, sequência 1,2,3...12 quase sem gap) vs coluna 17 "UTR COS Index" (score=0.675, `frac_int=0.73 mono=0.86 faixa=[1,7] n=8`) | **RGE GAU 2026** | **NÃO — CASO REAL CONFIRMADO** (dobrado em Caso A, ver seção final) — mesma classe do padrão 4/Caso A: contador de posição vence porque a coluna real reinicia (bloco de "Pontos Calculados" tem só 8 valores numéricos válidos, o resto é `-`/vazio) |

## Veredito final: há casos reais de endereço errado no output atual do pipeline?

**SIM — 3 padrões distintos confirmados (Caso A, Caso B, Caso C), cada um
afetando múltiplas sheets/sinais reais. Uma varredura sistemática do log
(ver seção "Varredura sistemática" abaixo) confirmou que o escopo está
fechado: 28 sheets no total têm um contador de posição vencendo um
concorrente com cara de endereço real; 27 já eram Caso A/C, 1 nova
(`CALCULADOS`) foi dobrada em Caso A nesta revisão; nenhuma sheet adicional
não documentada foi encontrada.**

### Caso A — sheet `S4_LOG` (arquivos `docs/input_nao_homogeneo_4_GAU.xlsx` e
`docs/RGE GAU 2026 - Lista de Pontos v09.xlsx`, mesma sheet nos dois) **e**
sheet `CALCULADOS` (`docs/RGE GAU 2026 - Lista de Pontos v09.xlsx`)

`analisar()` escolhe a coluna **"Linha"** (posição/contador, reinicia por
bloco — só 88 valores distintos em 1144 linhas) como coluna de endereço DNP3,
em vez de **"EndPt(N4)"** (967 valores distintos, faixa 100-3110 — o
endereço real do protocolo). Rodando `estruturar()` com o mapa real
produzido pelo pipeline:

```
S4_LOG:2  desc='SE' ... ADDR=(7,)    # real seria 3110 (EndPt N4)
S4_LOG:3  desc='SE' ... ADDR=(8,)    # real seria 1605
S4_LOG:4  desc='SE' ... ADDR=(9,)    # real seria 1606
...
```

Todo sinal desta sheet (1139 registros estruturados) recebe como endereço um
número de linha/posição, não o endereço DNP3 real. (Nota: a coluna de
`descricao` também sai errada nesta sheet — pega "Modulo" em vez de um campo
textual — sinal de que `S4_LOG` é, na origem, uma planilha de log/mapeamento
técnico do conversor de protocolo (S4), não uma lista de pontos no formato
esperado pelo pipeline; ainda assim ela passa pelo filtro `_eh_sheet_dados`
e não está em `config.sheets_excluidas`, então é processada e teria saída
poluída se essa sheet chegasse a produção.)

**Mesma classe de falha, achada pela varredura sistemática da Task 1
(revisão), em sheet e arquivo diferentes: `CALCULADOS`
(`docs/RGE GAU 2026 - Lista de Pontos v09.xlsx`, log linhas 426-427).**
`analisar()` escolhe a coluna 0 **"Linha"** (score=1.0, sequência 1,2,...,12
quase sem gap ao longo da sheet) em vez da coluna 17 **"UTR COS Index"**
(score=0.675, `frac_int=0.73 mono=0.86 faixa=[1,7] n=8`). Verificação nos
dados brutos (`docs/RGE GAU 2026 - Lista de Pontos v09.xlsx`, sheet
`CALCULADOS`, linhas 3-16):

```
Linha=1   UTR COS Index=None   (linha de bloco "Pontos Calculados", sem sinal)
Linha=2   UTR COS Index='-'    (placeholder, tipo='A' — ainda sem valor DNP3)
Linha=3   UTR COS Index='-'
Linha=4   UTR COS Index='-'
Linha=5   UTR COS Index=None   desc='COMANDO CENTRAL DE ALARMES' (cabeçalho de bloco)
Linha=6   UTR COS Index=1      desc='CA_Comando Sirene'
Linha=6   UTR COS Index=1      desc='CA_SENSOR_DEFEITO'   # reinicia dentro da mesma sheet
Linha=7   UTR COS Index=2      desc='CA_Sensor de Fumaça'
Linha=8   UTR COS Index=3      desc='CA_central Armada'
Linha=9   UTR COS Index=4      desc='CA_Sensor Invasão Externa'
Linha=10  UTR COS Index=5      desc='CA_Sensor Invasão Interna'
Linha=11  UTR COS Index=6      desc='CA Sirene Disparada'
Linha=12  UTR COS Index=7      desc='CA VCC_Presente'
```

"Linha" é o contador de posição/exibição da planilha (cresce quase sem
interrupção, 1..12); "UTR COS Index" é o endereço real do protocolo, mas
tem só 8 valores numéricos válidos na sheet inteira (o resto é `-`/vazio de
linhas de cabeçalho/placeholder) e reinicia a contagem (1,2,3...) dentro do
próprio bloco "Pontos Calculados" — exatamente o mesmo mecanismo de falha
do `S4_LOG`: um contador de linha que aparenta ser "mais monotônico e mais
denso" vence uma coluna de endereço real que é genuína, porém esparsa/
reiniciante. Rodando `estruturar()`, os 7 sinais do bloco de comandos desta
sheet receberiam ADDR=(6,), (6,), (7,), (8,), (9,), (10,), (11,), (12,) —
números de linha, não os endereços DNP3 reais 1,1,2,3,4,5,6,7.

### Caso B — sheets de relé `GPR21`/`GPR31`/`GPR33`/`GPR34`/`GPR35`/`GPR36`
(`docs/input_nao_homogeneo_3_GPR.xlsx`, SE Guaporé)

`analisar()` escolhe a coluna **"Entrada Binária"** (terminal físico do IED,
reinicia a numeração a cada bloco Analógicos/Comandos/Digitais) em vez de
**"DNP3.0"** (endereço real, contínuo dentro do bloco Digitais). Rodando
`estruturar()` com o mapa real do pipeline para `GPR21`:

```
GPR21:27  "TRIP de desligamento p/26/49 TR3 - Atuado"  ADDR=(16,)
          # DNP3.0 real nesta linha = '-' (não numérico) -- endereço FABRICADO
          # a partir de uma coluna errada, não um endereço genuíno perdido
GPR21:33  "Telecomando (43TC) - Excluído"               ADDR=()
          # DNP3.0 real = 8 -- endereço genuíno PERDIDO (fica vazio)
GPR21:40  "Proteção 50BF - Atuado"                       ADDR=()
          # DNP3.0 real = 15 -- PERDIDO
GPR21:55  "Proteção 27 - Atuada"                          ADDR=()
          # DNP3.0 real = 30 -- PERDIDO
GPR21:56  "Proteção 59 - Atuada"                          ADDR=()
          # DNP3.0 real = 31 -- PERDIDO
```

25 sinais de proteção reais em `GPR21` (religamento 79, proteções ANSI
50/51/59/27, sequência negativa, sub/sobrefrequência, terra sensitiva etc.)
ficam **sem endereço** no output atual porque a coluna escolhida
("Entrada Binária") está vazia para eles, enquanto a coluna certa ("DNP3.0")
tem o valor numérico correto ali. O mesmo padrão estrutural (mesmo layout de
cabeçalho) se repete idêntico em `GPR31`, `GPR33`, `GPR34`, `GPR35`, `GPR36`
— 6 sheets no total, cada uma com dezenas de sinais de proteção afetados.

### Caso C — 25 sheets de `docs/input_nao_homogeneo_2_FWB.xlsx` (SE FWB, todas
as sheets de dados do arquivo: `LOGICOS`, `SNMP`, `SPS`, `TR1`, `2414 TR1`,
`TR2`, `2414 TR2`, `AL FWB11`..`AL FWB25`, `IB P1-T1`, `IB P2-T2`, `IB P1-P2`,
`BC1`, `BC2`, `BARRA P1`, `BARRA P2`, `A8000`)

Mesmo padrão estrutural do Caso A (contador de linha vence a coluna de
endereço real), mas em arquivo diferente e com escopo bem maior: **todas as
25 sheets não-vazias** do arquivo. `analisar()` escolhe a coluna 0
("Linha", contador de linha puro: 1, 2, 3...) em vez da coluna 17/18 ("UTR
COS Index", o endereço DNP3/protocolo real). Log (`bench/resultados/
diag_enderecos.log`, linhas 112-211): em nenhuma das 25 sheets a coluna
"Linha" perde — mesmo quando "UTR COS Index" tem `score` alto (até 1.0,
`mono=1.0`), o contador de linha vence porque tem `frac_int=1.0` e também
`mono=1.0` (sequência 1,2,3... é estritamente crescente sheet-wide, tanto
quanto — ou mais estável que — a coluna real).

**Verificação independente contra o ground truth** (`docs/TDT/
exportTDT_UTR_FWB_1_20260626.xlsx`, sheets `DNP3_AnalogSignals`/
`DNP3_DiscreteSignals`, coluna "Input Coordinates"), cruzando por
descrição/nome de sinal em 3 sheets:

- `AL FWB12`: linha 1 "Corrente Fase A" → "UTR COS Index"=21; linha 2
  "Corrente Fase B"→22; linha 3 "Corrente Fase C"→23. Ground truth:
  `FWB_AL12_52-12_IA` coord=21, `..._IB` coord=22, `..._IC` coord=23 —
  **bate exatamente**.
- `AL FWB13`: "Corrente Fase A"→41, "Corrente Fase B"→42, "Corrente Fase
  C"→43, "Corrente Neutro"→44, "Tensão Barra Fase AB"→45, "...BC"→46.
  Ground truth: `FWB_AL13_52-13_IA`=41, `_IB`=42, `_IC`=43, `_IN`=44,
  `_VAB`=45, `_VBC`=46 — **bate exatamente**, todos os 6 sinais
  conferidos.
- `SNMP`: linha 1 "SW1 - Falha Porta 01"→2100, linha 2 "...02"→2101, linha
  3 "...03"→2102 — sequência coerente com a faixa 2100+ observada em
  outras sheets do mesmo arquivo (ex. `A8000` faixa=[420,2364]); a coluna
  "Linha" para as mesmas 3 células vale 1, 2, 3 — claramente um contador,
  não um endereço de protocolo.

Rodando `estruturar()` com o mapa real produzido pelo pipeline (mesmo
caminho não-homogêneo que Caso A/B):

```
AL FWB12:1  desc='Corrente Fase A' ADDR=(1,)   # real seria 21 (UTR COS Index)
AL FWB12:2  desc='Corrente Fase B' ADDR=(2,)   # real seria 22
AL FWB12:3  desc='Corrente Fase C' ADDR=(3,)   # real seria 23
```

Todo sinal das 25 sheets recebe como endereço um número de linha/posição
sequencial, não o endereço DNP3 real — mesmo efeito do Caso A (S4_LOG),
porém em superfície muito maior (25 sheets vs. 1) e em arquivo distinto
(FWB, não GAU/RGE).

**Implicação para o design da correção (Task 2):** o Caso A e o Caso C são
a mesma classe de falha, não dois bugs independentes — um contador de
linha puramente sequencial (1,2,3...) é **monotônico perfeito
sheet-wide** (`mono=1.0`) e frequentemente **100% inteiro**
(`frac_int=1.0`), então ele bate ou supera o score de qualquer coluna de
endereço real que não seja ela mesma estritamente crescente do início ao
fim da sheet (a coluna real cai quando reinicia por bloco, tem gaps, ou
não é perfeitamente sequencial). A correção da Task 2 não pode ser um
patch pontual para "Linha" ou para uma sheet específica — precisa de um
critério que penalize (ou desempate contra) uma coluna cujo padrão é
"contador de posição" (ex.: sequência 1..N sem gaps, idêntica ao índice de
linha da própria tabela) e/ou favoreça sinais de "endereço de protocolo
real" (nome de header, faixa de valores fora de [1, nº de linhas], ou
proximidade a rótulos como "DNP3"/"Index"/"Endereço").

## Varredura sistemática (revisão pós-Caso-C): fechando o escopo do Caso A/C

Duas rodadas de revisão manual encontraram, cada uma, mais **uma** ocorrência
do mesmo padrão (contador de linha vencendo endereço real) que a passada
anterior não tinha surfaced no catálogo — primeiro `S4_LOG`/GPR na Fase 1
original, depois as 25 sheets de FWB, depois `CALCULADOS`. Isso indica que a
leitura manual do log não é confiável para provar exaustividade. Para fechar
esta questão de vez, foi escrito um script de parsing determinístico do log
(`bench/scan_ruido_enderecos.py`, reusável, não reimplementa a heurística de
detecção — só faz parsing estrutural do output já gerado por
`bench/diag_enderecos.py`).

**Critério da varredura:** flag toda sheet onde (1) a coluna **escolhida**
como `col_indice` tem rótulo batendo um termo de "contador de posição"
(`linha`, `line`, `seq`, `row`, `item`, `n°`/`num`, comparação
case-insensitive e sem acento) **e** (2) existe pelo menos uma coluna
**concorrente** logada (>=50% inteiros) cujo rótulo bate um termo de
"endereço de protocolo real" (`dnp3`, `index`, `endereco`, `addr`, `entrada
binaria`, `utr cos`, `bit`, `word`, `registrador`, `coordinate`, `endpt`,
`n3`/`n4`).

**Resultado (rodado sobre as 462 linhas do log atual, 134 sheets
processadas no total pelas 7 listas reais — corrigido de "141" numa revisão
anterior deste documento; 134 é a contagem verificada por soma de
`sheets_dados` por arquivo e por contagem de linhas `col_indice=` no log,
ambas concordando):**

**Limitação conhecida do log-fonte:** `bench/diag_enderecos.py` trunca a
lista de colunas concorrentes logadas a `concorrentes[:5]` por sheet — as
28 sheets acima têm no máximo 3 concorrentes cada (não truncadas), então
isso não afeta o veredito acima, mas 18 outras sheets do log (majoritariamente
GPR: `GPR21/31/32/33/34/35/36`, `IB23`, `BC1`, `TR3DIF`, `TR2DIF`, `TR1AT`,
`TR1BT`, `LTKNP67`, `COMANDOS`, `DIGITAIS`, `ANALOGICOS`, `SACA - MMD`) têm
exatamente 5 concorrentes listados — um 6º concorrente mais fraco poderia
existir sem aparecer no log. Relevante para qualquer varredura futura
baseada neste log (ex. um scan do padrão do Caso B); não invalida o veredito
desta varredura (que não depende de concorrentes além do 1º/2º lugar).

```
Total de sheets flagadas: 28

docs/input_nao_homogeneo_2_FWB.xlsx
  LOGICOS, SNMP, SPS, TR1, 2414 TR1, TR2, 2414 TR2,
  AL FWB11..AL FWB15, AL FWB21..AL FWB25,
  IB P1-T1, IB P2-T2, IB P1-P2, BC1, BC2, BARRA P1, BARRA P2, A8000
  (25 sheets — todas já documentadas como Caso C)

docs/input_nao_homogeneo_4_GAU.xlsx
  S4_LOG  (já documentada como Caso A)

docs/RGE GAU 2026 - Lista de Pontos v09.xlsx
  CALCULADOS  (NOVA — não estava no catálogo antes desta revisão)
  S4_LOG      (já documentada como Caso A, segunda cópia do arquivo)
```

**Checagem de completude adicional:** um `grep` bruto de todo rótulo já
escolhido como `col_indice` em qualquer sheet do log (`col_indice=... label='...'`)
mostra apenas **um** rótulo que bate o padrão "contador de posição" em toda a
base: `LINHA` (28 ocorrências). Não há nenhuma sheet no log onde `col_indice`
tenha rótulo `SEQ`, `ITEM`, `N°`, `ROW` ou similar — ou seja, o universo de
"contador de posição escolhido como endereço" já está 100% coberto pelas
28 ocorrências de `LINHA` acima, e todas as 28 foram flagadas pela varredura
(nenhuma sheet com `LINHA` escolhida ficou de fora por não ter concorrente
"parecido com endereço real" — em todas as 28, "UTR COS Index" ou
"EndPt(N4)"/"N3" apareceu como concorrente no log).

**Veredito da varredura sistemática:** das 28 sheets flagadas, **27 já
estavam documentadas** (25 FWB = Caso C, 2×S4_LOG [GAU e RGE] = Caso A) e
**1 é nova**: `CALCULADOS` (RGE GAU 2026), confirmada como bug genuíno (ver
verificação de dados brutos no Caso A acima) e agora dobrada em Caso A.
**Nenhuma outra sheet não documentada foi encontrada.** O padrão "Entrada
Binária" vs "DNP3.0" (Caso B, GPR) é uma classe de falha diferente — não é
um contador de posição, é o terminal físico do IED (reinicia por bloco mas
não é uma sequência 1..N pura) vencendo por proximidade de score, não por
"parecer" um contador — por isso não aparece nesta varredura (que busca
especificamente rótulos tipo "linha/seq/item"), o que é o comportamento
esperado, não uma lacuna: Caso B já está documentado separadamente e seu
critério de busca é outro (coberto pela Task 1 original, não pelo escopo
desta varredura adicional).

### Casos investigados e descartados (NÃO são bugs)

- `AL21`/`03F1 TR1 PP`/`03F2 TR1 PA` (GAU/RGE): "UTR COS Index" vs "IED
  Index" tinham score próximo (0.84-0.94), mas conferência linha-a-linha
  confirma que "UTR COS Index" é a coluna certa (valores crescentes por
  sinal: 40,41,42...) e foi a escolhida — sem bug.
- `SPS_TR1_TR2`/`TR1AT-TM1` (GTD/GPR/RGE): registrador Modbus (40000+) tinha
  score 0.7-0.74 mas nunca supera a coluna certa (score maior, faixa
  claramente diferente) — sem bug.
- `SAN2_LISTA_PADRONIZADA_PARA_TESTE.xlsx`: "INDEX DNP3 - COMANDO" tinha
  score 0.5 mas com `n=1` (1 valor só) — não chega a competir com "INDEX
  DNP3 - ENTRADA" (a correta, `n` muito maior) — sem bug.
- `LTPCH21`/`LTKNP21`/`LTCAS21`/`LTARV21` (GPR): header mal detectado (linha
  de dado em vez de header real) é uma observação real, mas o "endereço
  verdadeiro" destes relés IEC 60870-5-103/COS específicos não pôde ser
  determinado com confiança neste levantamento (coluna "DNP3.0" tem códigos
  texto, não número, nestas sheets) — **não contabilizado como caso
  confirmado**, fica registrado como limitação/candidato a investigação
  futura, não como parte do veredito.

## Limitações deste levantamento

- Cross-referência direta com TDT exportado (`docs/TDT/exportTDT_UTR_GTD_1_
  20260626.xlsx`) só está disponível para GTD e FWB; para GPR/GAU/RGE/SAN2/
  IMA a verificação de "certo vs errado" foi feita por inspeção direta dos
  dados brutos da própria planilha de entrada (cardinalidade, faixa,
  continuidade dentro de blocos, e o rótulo do cabeçalho real quando
  localizável), não por comparação com uma saída SCADA já confirmada.
- A inspeção manual linha-a-linha (a etapa que efetivamente pega bugs como
  o Caso A/B/C, distinta de só ler o `score` do log) não foi aplicada de
  forma uniforme a todas as sheets levantadas na Fase 1 original — o Caso C
  (FWB, 25 sheets) já estava nos dados do log desde a primeira rodada, mas
  só foi confirmado como caso real numa passada de revisão posterior, e o
  mesmo se repetiu com `CALCULADOS` (achado só na segunda revisão). **Esta
  lacuna foi fechada** para o padrão específico "contador de posição vence
  endereço real" pela varredura sistemática (`bench/scan_ruido_enderecos.py`,
  ver seção "Varredura sistemática" acima), que processa 100% das sheets do
  log de forma determinística em vez de depender de leitura manual —
  resultado: 28/28 ocorrências do padrão já cobertas pelo catálogo (Caso
  A/C). Para os OUTROS padrões (Caso B e os "descartados"), a verificação
  segue sendo por inspeção direta dos dados brutos (não há uma varredura
  automatizada equivalente para "IED Index"/"Entrada Binária" etc. — se uma
  lista nova aparecer, recomenda-se rodar uma varredura análoga para esses
  padrões antes de declarar "sem bug").
- `docs/RGE GAU 2026 - Lista de Pontos v09.xlsx` tem um `<extLst>` em
  `xl/styles.xml` que o openpyxl 3.1.5 (Python 3.14) não desserializa
  (`PatternFill.__init__() got an unexpected keyword argument 'extLst'` —
  risco de ambiente já registrado na memória do projeto). O script contorna
  isso removendo os blocos `<extLst>` de uma cópia temporária do arquivo
  antes de abrir (não altera dado/valor de célula) — não é uma correção de
  produto, só destrava a leitura para este levantamento.
- O padrão 6 (header mal detectado nos relés de linha via COS) não foi
  aprofundado por não ter ground truth numérico claro — pode merecer
  levantamento próprio se aparecer de novo em lista nova.

## Commit

`test(spM): catalogo de ruido de enderecos em todas as listas`
`docs(spM): adiciona caso C (FWB) ao catalogo de ruido de enderecos`
`docs(spM): varredura sistematica confirma escopo completo do catalogo`

## Próximo passo

Conforme o Global Constraint da SP-M: como HÁ casos reais confirmados
(Caso A, Caso B e Caso C — Caso A agora cobrindo também `CALCULADOS`), a
Fase 1 **não encerra** a SP — a Task 2 (correção) seria o próximo passo,
tratada como tarefa separada com sua própria revisão (fora do escopo desta
Task 1, que é só levantamento). O Caso C reforça que a correção não deve
ser um patch pontual por sheet/arquivo: precisa endereçar a classe geral
"contador de posição sheet-wide vence coluna de endereço real quando esta
não é 100% monotônica do início ao fim" (ver nota de implicação de design
no Caso C acima), sob pena de resolver A/B/C e deixar a mesma falha
estrutural aberta para a próxima lista real que aparecer. A varredura
sistemática confirma que, para ESTE padrão específico, o escopo do
levantamento está fechado (28/28 ocorrências documentadas) — a correção da
Task 2 pode ser projetada com confiança de que não há mais instâncias
escondidas do mesmo padrão nas 7 listas reais analisadas.
