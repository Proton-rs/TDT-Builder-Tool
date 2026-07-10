# Spec — Correção dos erros de importação ADMS da lista homogênea IMA

**Data:** 2026-07-10 (rev. 2: pesquisa MM por sigla + TAP/DiscreteAnalog)
**Status:** aprovada (design validado com usuário nesta data)
**Evidência:** `docs/erros.csv` (log de import do ADMS), `docs/input_homogeneo_IMA.xlsx`,
`output/TDT_IMA_20260709.xlsx`, `output/Auditoria_IMA_20260709.xlsx`,
`docs/Export_base_Full__27_fev_2026.xlsx` (modelo real),
`docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (TDT aceito), `docs/Pontos Padrao ADMS_v7.xlsx`,
`output/pesquisa_mm_quebrados.txt` (contagens completas da pesquisa MM).

## 1. Diagnóstico

`erros.csv`: 6797 linhas, 343 `Falhou` (resto `Informação`). Três classes:

| Classe | Msgs | Causa raiz |
|---|---|---|
| 1. Remote point duplicado | 133 (121 ids) | Nome gerado colapsa equipamentos distintos do mesmo módulo |
| 2. Message Mapping inexistente | 105 (91 elems) | Refs da lista padrão v7 não existem no modelo real |
| 3. Cascata (elemento DNP3 órfão) | 105 | Consequência direta da classe 2 — sem ação própria |

Fora do `erros.csv`, mais dois defeitos confirmados no mesmo run (seção 5):
TAP não identificado (foi pra revisão) e COMTAP decidido errado como `CMD`.

### Classe 1 — duplicados

A lista homogênea distingue pontos pela coluna EQUIPAMENTO (`SECC`, `SECF`, `SECT`,
`DJ`, `DJ_P`, `DJ_A`, ...), cada um com mnemônico no bloco de cabeçalho da sheet
(`DJ→52-3`, `SECC→89-16`...). O pipeline monta o nome só com (SE, módulo, sigla)
em `engine_tdt._nome_hierarquico` — `Eletrico.nome_equipamento` chega vazio do
caminho homogêneo (`estruturador_homogeneo.py` lê EQUIPAMENTO apenas para
`equipamento_alvo`). Resultado: os 4 `43LR` da LT3 (89-14, 89-16, 89-18, 52-3)
viram todos `IMA_LT3_LT3_43LR` → mesmo `Remote Point Custom ID`
(`{nome}_{remote_unit}`) → ADMS descarta a 2ª+ ocorrência.

Regra de domínio (usuário, 2026-07-10): equipamento no nome só para sinais
diretos do equipamento (`SE_MOD_EQUIP_SIGLA`); proteções seguem
`SE_MOD_MOD_SIGLA` (com qualificador `_P`/`_A` de relé principal/alternado).
A regra geral **mnemônico do equipamento-base se existir no bloco, senão módulo,
+ sufixo `_P`/`_A`** reproduz a convenção do cliente incluindo os casos
`DJ_P→52-3_P` e `LT_P→LT3_P`, sem exceção codificada.

Validação contra a coluna NOME do cliente (1404 linhas SIM): 1067 batem com a
regra de equipamento; os 337 restantes são todos **resolução de módulo**
(decisão do usuário: corrigir junto):

- Sheet TR: coluna MÓDULO = `AT`/`BT`/`TR`, bloco `MÓDULO→6`; cliente usa
  `TR6AT`/`TR6BT`/`TR6`. Mnemônicos por lado no bloco (`DJ AT→52-6`, `DJ BT→52-19`).
- Sheet BARRA: bloco `EQUIPAMENTO | CLASSE DE TENSÃO` (`BP AT→69`, `BP BT1→13.8`);
  coluna MÓDULO `BP`/`BP1`/`BP2`; cliente usa `BP69`, `BP113.8`, `BP213.8`.
- Sheets RET: bloco `TSA→1`, `RET→1`; coluna MÓDULO `TSA`; cliente usa módulo
  `TSA1`/`TSA2` e equipamento `RET1`/`RET2`.
- Sheets TSA: bloco `MÓDULO→40`; cliente usa `TSA40`, `TSA_P140` (concatena o
  número mesmo quando o rótulo da coluna já contém dígito — a guarda atual
  `not any(ch.isdigit())` impede).

### Classe 2 — Message Mappings

MM sai literal da coluna MM da lista padrão (`engine_tdt.py:188`, `sp.mm`).
Contexto (usuário, 2026-07-10): a lista padrão foi criada por engenheiros da
RGE para padronizar os MMs — pegaram o mais usado por sinal, mas erraram alguns.

Auditoria completa das 692 siglas com MM da v7 contra o catálogo real
(`MessageMappings` do Export Base Full, 484 refs): **6 refs quebradas, 35 siglas**
(`43LR`, `81U1-5`, `AJ*` ×23, `DSAB`, `VFAR`, `ZERO`, `ICC`, `CDCO`, `CCIC`).
A IMA só bateu em 43LR/81U*; as demais quebram o próximo import que usar as
siglas (GAU tem lista na fila). A pesquisa da seção 4 refaz o "mais usado por
sinal" direto do Export Base Full para todas elas.

## 2. Solução

### 2.1 Resolvedor de identidade módulo/equipamento (Classe 1)

Novo `src/tdt/normalizacao/identidade_homogenea.py`, chamado por
`estruturador_homogeneo`:

- Parseia o bloco de cabeçalho da sheet (generalização de
  `extrair_numeros_operativos`): número operativo/mnemônico, classe de tensão
  (BARRA), número (RET/TSA).
- Resolve **módulo** no padrão do cliente: `AT`/`BT` em sheet TR → `TR{n}AT`/`TR{n}BT`;
  `BP{x}` + classe → `BP{x}{classe}` (`BP1`+`13.8`→`BP113.8`); `TSA` + número → `TSA{n}`;
  demais mantêm a regra atual (`LT`+`3`→`LT3`), inclusive concatenação quando o
  rótulo já tem dígito (`TSA_P1`+`40`→`TSA_P140`).
- Resolve **equipamento (segmento do meio)**: mnemônico do equipamento-base no
  bloco, com lado quando o rótulo do bloco tem lado (`DJ` em linha do lado AT →
  `52-6`); sem mnemônico → repete o módulo resolvido. Sufixo de relé embutido no
  próprio valor: `DJ_P` → `52-3_P`, `TR_A` (lado BT) → `TR6BT_A`.
- Preenche `Modulo.nome` e `Eletrico.nome_equipamento`; **`engine_tdt._nome_hierarquico`
  não muda** (já concatena equipamento quando presente).
- Fallback: sheet sem bloco ou rótulo desconhecido → comportamento atual
  (módulo repetido) + registro marcado para revisão.

### 2.2 Gate de unicidade de Custom ID

Pós-geração, antes de escrever o TDT: `Remote Point Custom ID` duplicado →
linhas conflitantes vão para Auditoria/Revisão; nunca saem caladas no xlsx.
(Duplicatas legítimas de par complementar já foram fundidas pelo
`normalizador_estrutural` antes desse ponto.)

### 2.3 Lista padrão v7 → v8 (Classe 2)

- `docs/Pontos Padrao ADMS_v8.xlsx`: corrige as 2 refs que quebraram a IMA
  (43LR + 81U1–81U5, sheet DiscreteSignals, coluna MM) conforme seção 4.
  As demais correções da seção 4 são aplicadas na mesma edição da v8 quando o
  usuário validar as recomendações (ICC/CCIC ficam pendentes — sem evidência).
- Teste de domínio novo: toda ref da coluna MM da lista padrão deve existir no
  catálogo `MessageMappings` do Export Base Full, com whitelist explícita do
  que ainda não foi corrigido (o teste falha se surgir ref quebrada nova).

### 2.4 Verificação NOME×regra (auditoria)

Quando a lista de entrada tiver coluna NOME preenchida, comparar com o nome
calculado; divergência vira aviso de auditoria (não bloqueia). Detecta drift da
convenção em listas futuras.

## 3. Testes

- **Oracle NOME:** as 1404 linhas SIM da IMA (coluna NOME do cliente) viram
  fixture; nome calculado deve bater 100%. TDD: escrever o teste antes do
  resolvedor.
- Teste de domínio MM ⊆ catálogo real (seção 2.3).
- Gate de unicidade: teste com dup sintético → vai pra revisão, não pro xlsx.
- TAP (seção 5): regen IMA → sheet `DNP3_DiscreteAnalog` com `IMA_TR6_TR6_TAP`
  e `IMA_TR7_TR7_TAP` (perfil TapPosition/Discrete/Read/Analog/NV 9, sem MM);
  COMTAP em revisão; nenhum `CMD` espúrio gerado.
- Regressão: regen `TDT_IMA` + re-run `gate_tdt_real`/bench.
- Critério de aceite do conjunto: no TDT regenerado, zero `Remote Point Custom ID`
  duplicado e zero MM fora do catálogo real → as 343 falhas do `erros.csv`
  não se reproduzem.

## 4. Pesquisa MM — mais usado por sigla no Export Base Full

Método: contagem de MM por sigla (sufixo `_SIGLA` do Signal Name) em
`DNP3_DiscreteSignals` (237k sinais); todos os candidatos recomendados foram
verificados presentes no catálogo `MessageMappings`. Contagens completas em
`output/pesquisa_mm_quebrados.txt`. Ressalva ao método "mais usado": o MM tem
que ser compatível com o tipo do ponto — single vs double (`S_`/`D_`, prefixo
`DI_`) e sinalização vs comando (`TS`/`TC`). O mais usado global pode ser da
variante errada (ex.: 43LR global é `DI_..._DS`, double).

| Sigla(s) | Ref quebrada (v7) | Recomendação v8 | Evidência |
|---|---|---|---|
| 43LR | `null@null___REMOTO@LOCAL__Local_S_TS_SS` | `null@null___REMOTO@LOCAL___Custom_S_TS_SS` | mais usado single-bit (833x; GTD aceito 19x). Top global `DI_null@null___REMOTO@LOCAL___Local___INV_S_TS_DS` (5165x) é double |
| 81U1–81U5 | `null@null___DESABILITADO@HABILITADO___Custom_S_TS_SV` | ponto com comando: `null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS` (GTD aceito 70x); só sinalização: `null@null___DESABILITADO@HABILITADO___Custom_S_TS` (mais usado, ~58%) | IMA tem comando (Discrete Output) → variante TC |
| AJ1..AJ34 (23) | idem 81U | `null@null___DESATIVADO@ATIVADO___Custom_S_TS_SV` (com comando: `null@ATIV_DES___DESATIVADO@ATIVADO___Custom_S_TC_SV`) | família uniforme na base: par é DESATIVADO@ATIVADO, nunca DESABILITADO@HABILITADO; variantes SV/SVx 1–2 usos cada |
| DSAB | idem 81U | `null@null___HABILITADO@DESABILITADO___Custom_S_TS_SA` | único uso real (1x) |
| VFAR | idem 81U | `DESLIGAR@LIGAR___DESLIGADO@LIGADO___Custom_S_TC_SV` | único uso real (2x) |
| ZERO | `ZERAR@null___null@null___Custom_S_TC_SS` | `DI_null@ZERAR___NORMAL@ZERADO___Custom_admsINV_S_TC` | 406x, 100% dos usos |
| CDCO | `MESTRE@INDIVIDUAL@COMANDO___..._Parallel___admsINV_D_TC` | `MESTRE@INDIVIDUAL@COMANDADO___MESTRE@INDIVIDUAL@COMANDADO___Custom___INV___D_TS_SS` | mais usado (7x, 41%); ponto double |
| ICC | `RESET@null___null@null___Custom_S_TC_SS` | **pendente** — zero uso na base; variantes `DI_RESETAR@null___...` existem no catálogo | decisão de engenharia RGE |
| CCIC | `CMD_RGE@null___RGE@CPFLT___Custom_S_TC_SS_CPFLT` | **pendente** — zero uso; `CPFLT` não existe no catálogo | decisão de engenharia RGE |

## 5. TAP / DiscreteAnalog

### Diagnóstico

Run de 09/07 (TDT 17:16): TAP e COMTAP do input (TR 1/TR 2: `TAP` tipo `A/D`
idx 47/69; `COMTAP` tipo `C` idx `30;30`) **não saíram no TDT**. Auditoria:
`TAP` → revisão `score_baixo` (0.462, candidato 90DP); `COMTAP` → **decidido
errado como `CMD`** (0.643) — falso positivo que gera comando espúrio.

Estado do código (HEAD): suporte DiscreteAnalog existe e funciona — loader lê a
aba (`baee2f9`, 09/07 13:51), engine roteia por `sp.categoria` e escreve a sheet
`DNP3_DiscreteAnalog` (`b8d36c7`, 09/07 15:08), `por_sigla("TAP")` resolve na
v7. O run das 17:16 falhou na identificação — processo/UI com código ou lista
padrão anteriores. Gaps reais restantes:

1. **Tipo `A/D` não mapeado**: `CODIGOS_TIPO` só tem A/C/D; `A/D` cai no default
   `("Discrete","Input")` — categoria errada no registro, na auditoria e na
   barreira de domínio do dual-pass (caminho não homogêneo).
2. **COMTAP sem tratamento**: sigla não existe na lista padrão nem como sinal na
   base real (0 sinais `_COMTAP`; 0 de 1629 linhas DiscreteAnalog nos 3
   protocolos têm Output Coordinates/Direction≠Read). COMTAP real só existe como
   alvo de Device Mapping da linha TAP. Sem tratamento, o scoring decide `CMD`.

Perfil TAP real (1516 linhas DNP3, 100% uniforme): `Signal Type=TapPosition`,
`Measurement Type=Discrete`, `Direction=Read`, `Remote Point Type=Analog`,
`Normal Value=9`, **MM vazio** (DiscreteAnalog não usa Message Mapping — não há
MM de TAP a corrigir na lista padrão; a v7 já traz o perfil completo e o builder
`_valores_discrete_analog` já o reproduz).

### Correções

- `CODIGOS_TIPO["A/D"] = ("DiscreteAnalog", "Input")` em `vocabulario_tipo.py`
  (contrato `contracts.py` e `_DOMINIOS_POR_CATEGORIA` já suportam a categoria).
- **COMTAP → revisão, sem gerar sinal** (decisão usuário 2026-07-10): sigla
  conhecida que não vira ponto; sai do scoring (elimina o falso positivo `CMD`)
  e cai na auditoria com motivo "comando TAP não modelado no ADMS".
- Critério de aceite na seção 3.

## 6. Fora de escopo

- Caminho não homogêneo (GAU/GPR usam outra spec) — exceto o efeito colateral
  benigno de `CODIGOS_TIPO["A/D"]`.
- Classe 3 (cascata) — desaparece com a classe 2.
- Scoring/matching de siglas.
- Módulos de sheets futuras com blocos de cabeçalho diferentes dos 4 padrões
  mapeados (TR/BARRA/RET/TSA + padrão geral) — fallback + revisão cobre.
- Edição em si da v8 para AJ*/DSAB/VFAR/ZERO/CDCO — recomendações prontas na
  seção 4, aplicar após validação do usuário; ICC/CCIC dependem de engenharia RGE.
