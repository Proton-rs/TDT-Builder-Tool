# Spec — Correção dos erros de importação ADMS da lista homogênea IMA

**Data:** 2026-07-10
**Status:** aprovada (design validado com usuário nesta data)
**Evidência:** `docs/erros.csv` (log de import do ADMS), `docs/input_homogeneo_IMA.xlsx`,
`output/TDT_IMA_20260709.xlsx`, `docs/Export_base_Full__27_fev_2026.xlsx` (modelo real),
`docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (TDT aceito), `docs/Pontos Padrao ADMS_v7.xlsx`.

## 1. Diagnóstico

`erros.csv`: 6797 linhas, 343 `Falhou` (resto `Informação`). Três classes:

| Classe | Msgs | Causa raiz |
|---|---|---|
| 1. Remote point duplicado | 133 (121 ids) | Nome gerado colapsa equipamentos distintos do mesmo módulo |
| 2. Message Mapping inexistente | 105 (91 elems) | Refs da lista padrão v7 não existem no modelo real |
| 3. Cascata (elemento DNP3 órfão) | 105 | Consequência direta da classe 2 — sem ação própria |

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
Auditoria completa das 692 siglas com MM da v7 contra o catálogo real
(`MessageMappings` do Export Base Full, 484 refs): **6 refs quebradas, ~35 siglas**.
A IMA só bateu em 2; as demais quebram o próximo import que usar as siglas
(GAU tem lista na fila).

Ground truth (TDT GTD aceito no ADMS):

| Sigla | Ref quebrada (v7) | Correção (v8) |
|---|---|---|
| 43LR | `null@null___REMOTO@LOCAL__Local_S_TS_SS` | `null@null___REMOTO@LOCAL___Custom_S_TS_SS` (19x GTD, 833x base) |
| 81U1–81U5 | `null@null___DESABILITADO@HABILITADO___Custom_S_TS_SV` | `null@ATIVAR___DESATIVADO@ATIVADO___Custom_S_TC_SS` (70x GTD) |

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

- `docs/Pontos Padrao ADMS_v8.xlsx`: corrige as 2 refs da tabela acima
  (43LR + 81U1–81U5, sheet DiscreteSignals, coluna MM). Nada mais muda.
- Teste de domínio novo: toda ref da coluna MM da lista padrão deve existir no
  catálogo `MessageMappings` do Export Base Full, com whitelist explícita das
  4 pendências da seção 4 (o teste falha se surgir ref quebrada nova).

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
- Regressão: regen `TDT_IMA` + re-run `gate_tdt_real`/bench.
- Critério de aceite do conjunto: no TDT regenerado, zero `Remote Point Custom ID`
  duplicado e zero MM fora do catálogo real → as 343 falhas do `erros.csv`
  não se reproduzem.

## 4. Pendências (validar com domínio antes do import GAU)

Refs quebradas restantes da v7 — candidatos do modelo real, decisão de domínio
pendente:

| Siglas | Ref quebrada | Evidência / candidato |
|---|---|---|
| AJ1..AJ31 (30) | `null@null___DESABILITADO@HABILITADO___Custom_S_TS_SV` | Uso real misto: `..._DESATIVADO@ATIVADO___Custom_S_TS_SVx` / `_S_TS_SV` / `_S_TC_SV` (1–2 usos cada) |
| ZERO | `ZERAR@null___null@null___Custom_S_TC_SS` | Candidato forte: `DI_null@ZERAR___NORMAL@ZERADO___Custom_admsINV_S_TC` (406 usos) |
| ICC | `RESET@null___null@null___Custom_S_TC_SS` | Zero uso na base; variantes `DI_RESETAR@null___...` existem |
| CDCO | `MESTRE@INDIVIDUAL@COMANDO___..._Parallel___admsINV_D_TC` | 3 variantes reais D_TC/D_TS `Custom___admsINV`/`Custom___INV` |
| CCIC | `CMD_RGE@null___RGE@CPFLT___Custom_S_TC_SS_CPFLT` | `CPFLT` não existe no catálogo; sem uso na base |

## 5. Fora de escopo

- Caminho não homogêneo (GAU/GPR usam outra spec).
- Classe 3 (cascata) — desaparece com a classe 2.
- Scoring/matching de siglas.
- Módulos de sheets futuras com blocos de cabeçalho diferentes dos 4 padrões
  mapeados (TR/BARRA/RET/TSA + padrão geral) — fallback + revisão cobre.
