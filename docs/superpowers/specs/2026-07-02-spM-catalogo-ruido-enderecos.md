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

## Veredito final: há casos reais de endereço errado no output atual do pipeline?

**SIM — 2 padrões distintos confirmados, cada um afetando múltiplas
sheets/sinais reais.**

### Caso A — sheet `S4_LOG` (arquivos `docs/input_nao_homogeneo_4_GAU.xlsx` e
`docs/RGE GAU 2026 - Lista de Pontos v09.xlsx`, mesma sheet nos dois)

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

## Próximo passo

Conforme o Global Constraint da SP-M: como HÁ casos reais confirmados
(Caso A e Caso B), a Fase 1 **não encerra** a SP — a Task 2 (correção) seria
o próximo passo, tratada como tarefa separada com sua própria revisão (fora
do escopo desta Task 1, que é só levantamento).
