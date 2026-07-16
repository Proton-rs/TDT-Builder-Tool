# SP-DEVICE-MAPPING-RGE — Identidade de equipamento + Device Mapping padrão RGE

**Data:** 2026-07-15
**Status:** implementado (6 tasks, branch `feature/sp-device-mapping-rge`; gate `bench.regressao` pct 72.1%→72.3%, `comum` 954→952 — queda esperada: 5 sinais com equipamento conflitante passam a ir pra revisão em vez de gerar endereço; suite 962→985 testes, todos verdes). Whole-branch review (opus): ready to merge, achado Important sobre precisão do invariante de Custom ID corrigido no §Não-escopo abaixo (não era regressão).
**Origem:** `docs/anot.txt` (análise da lista LVA, sheet AL11) — Frente 1 da decomposição de 15/07.
A Frente 2 (ajustes de UX/perf da ferramenta) fica para spec própria, fora deste escopo.

## Contexto / Problema

Análise da lista LVA (sheet AL11) revelou dois defeitos encadeados:

1. **Equipamento falso-positivo:** `_ID_EQUIPAMENTO` (`normalizador.py`) casa qualquer
   padrão `N-N`, então sinais `81-1`, `81-2` (estágios de subfrequência) viraram
   `nome_equipamento="81-1"` — não existe equipamento 81. Equipamentos reais em módulo
   de subestação: 52, 24, 29, 89 (disjuntor/seccionadora) e transformadores `TR{n}`.
   Além disso a busca só olha a coluna de descrição — a AL11 tem coluna própria de
   equipamento que o caminho heterogêneo ignora.
2. **Device Mapping fora do padrão RGE:** hoje todo sinal gera Device Mapping com a
   sigla no fim (`LVA_AL11_52-11_CAFL`). No padrão RGE só proteção leva sufixo
   (`PROT_<SIGLA>`); não-proteção cai direto no equipamento (`LVA_AL11_52-11`);
   analógicos caem no TC/TP ou no disjuntor conforme a grandeza.

## Escopo

- Reconhecimento de ID de equipamento (whitelist) no N0.
- Varredura da linha inteira no caminho heterogêneo + colisão → revisão.
- Registro de equipamentos por módulo (extensão da `inferencia_topologia`/spC2):
  preencher o **ID** quando inequívoco.
- Regras RGE de Device Mapping no `engine_tdt` (só a coluna Device Mapping).

## Não-escopo

- Remote Point Custom ID / nome hierárquico: as regras de Device Mapping (§4,
  `_device_mapping`/`_device_mapping_analog`) **não tocam** neles — só a coluna
  Device Mapping muda. **Precisão (achado no whole-branch review, 15/07):** a
  identidade de equipamento em si (Tasks 1/3) pode legitimamente mudar
  Custom ID/nome_hierárquico quando corrige um `nome_equipamento` errado
  (81-1 deixa de ser equipamento) ou preenche um que faltava (registro por
  módulo) — é o efeito pretendido da correção de identidade, não uma
  violação. Verificado: no dado real GTA, o backfill da Task 3 não introduziu
  nenhum `custom_id_duplicado` novo (374 pós-branch vs 375 baseline — caiu,
  não subiu); os gates `particionar_custom_id_duplicado`/
  `particionar_endereco_duplicado` continuam intactos como mecanismo.
- DiscreteAnalog (TAP/COMTAP): inalterado — não citado na anotação.
- Ajustes de UI/perf (Frente 2, spec própria).
- Matching/scoring: nenhum knob de score muda; `81-1` permanecer na descrição é
  efeito colateral desejado (estágio ajuda o matching).

## Design

### 1. Reconhecimento de equipamento (N0 — `normalizacao/normalizador.py`)

- `_ID_EQUIPAMENTO` deixa de casar `\b(\d+)-(\d+)\b` genérico; passa a whitelist:
  `\b(52|24|29|89)-(\d+)\b`.
- Padrão novo: `TR{n}` (ex. `TR1`, `TR2`) reconhecido como equipamento.
- Mapa de tipos (`_EQUIPAMENTO_ANSI`): `52 → Disjuntor`, `24 → Disjuntor`,
  `29 → Seccionadora`, `89 → Seccionadora`, `TR → Transformador`.
- Vocabulário por palavra (`_EQUIPAMENTO_PALAVRA`) permanece como está.
- Consequência: `81-1` não vira mais `nome_equipamento` e fica no texto normalizado.

### 2. Varredura da linha inteira + colisão (`normalizacao/estruturador.py`)

- No caminho heterogêneo, a busca de ID de equipamento passa a varrer **todas as
  células da linha** (não só a descrição). A descrição continua sendo a fonte do
  texto do sinal; as demais células só contribuem para identidade de equipamento.
- Dois IDs de equipamento **distintos** na mesma linha → sinal vai para revisão com
  motivo novo `equipamento_conflitante` (mesmo canal `ItemRevisao` dos demais
  motivos). Mesmo ID repetido em células diferentes → ok, sem conflito.
- Caminho homogêneo não muda (coluna EQUIPAMENTO já é autoritativa via
  `identidade_homogenea.resolver`).

### 3. Registro de equipamentos por módulo (`inferencia_topologia.py`)

- Novo passo: coletar, por módulo, os equipamentos reais achados na sheet —
  `AL11 → {Disjuntor: {52-11}, Seccionadora: {89-1, 89-2}, Transformador: {TR1}}`.
- Sinal com `equipamento_alvo` (família) resolvido mas `nome_equipamento=None`:
  se o registro do módulo tem **exatamente 1** equipamento daquela família →
  atribui o ID (marcado `equipamento_inferido=True`). Hoje a spC2 só infere
  família; o ID atribuído aqui vem do que foi **achado na sheet**, nunca inventado.
- 2+ equipamentos da mesma família no módulo (ex. dois disjuntores) → **aviso**
  (canal `avisos` existente), exibido na revisão e na geração da TDT; sinais sem
  ID daquela família permanecem sem ID (caem no fallback do §4).

### 4. Device Mapping padrão RGE (`engine_tdt.py`)

Regras aplicadas **somente à coluna Device Mapping**, nos dois caminhos
(homogêneo e heterogêneo), num único choke point (`_device_mapping`):

| Sinal | Device Mapping | Exemplo |
|---|---|---|
| Proteção (`signal_type == "RelayTrip"`) | inalterado (`..._PROT_<SIGLA>`) | `LVA_AL11_52-11_PROT_CAFL` |
| Discreto não-proteção | equipamento da linha/registro, **sem sigla** | `LVA_AL11_52-11` |
| Analógico: corrente, potência ativa/reativa/aparente | TC do módulo | `LVA_AL11_AL11_TC` |
| Analógico: tensão | TP do módulo | `LVA_AL11_AL11_TP` |
| Analógico: demais grandezas (KMDF, frequência, fator de potência, temperatura...) | disjuntor do módulo | `LVA_AL11_52-11` |
| Fallback (sem equipamento/disjuntor identificado ou ambíguo) | módulo duplicado | `LVA_AL11_AL11` |

- Generalização aprovada: "não-proteção cai no disjuntor" = cai no **equipamento
  da linha** — sinal de seccionadora com `89-1` identificado gera `LVA_AL11_89-1`,
  não o disjuntor. Disjuntor é o caso dominante, não regra exclusiva.
- TC/TP são entidades nomeadas por módulo: `<SUB>_<MOD>_<MOD>_TC` / `..._TP`.
- A grandeza do analógico vem do Measurement Type PT já extraído (mesma fonte de
  `_MEASUREMENT_TYPE_PT_EN`), decidida **antes** da tradução PT→EN.
- Módulo com aviso de disjuntor duplicado (§3): sinais que dependeriam do
  disjuntor usam o fallback módulo duplicado.

### 5. Testes / critério de aceite

- TDD: fixtures sintéticas no padrão LVA/AL11 (coluna de equipamento separada,
  sinais 81-x, analógicos de corrente/tensão/potência/KMDF).
- Casos mínimos: 81-x não vira equipamento; colisão → `equipamento_conflitante`;
  registro atribui ID único; 2 disjuntores → aviso + fallback; cada linha da
  tabela do §4; proteção inalterada; Custom ID inalterado.
- `gate_tdt_real` ≥ baseline (mudança não pode regredir o gate).
- Conservação: nenhum sinal some — colisão vai para revisão, nunca é descartada.

## Decisões registradas (para o ledger no closeout)

- Whitelist de equipamento `(52|24|29|89)-N` + `TR{n}`; 24 = Disjuntor (decisão do usuário 15/07).
- Analógico sem regra específica cai no **disjuntor** do módulo (decisão do usuário 15/07).
- Fallback universal de Device Mapping: módulo duplicado (`<SUB>_<MOD>_<MOD>`).
- Registro por módulo atribui ID real achado na sheet; nunca inventa ID (mantém princípio da spC2).
