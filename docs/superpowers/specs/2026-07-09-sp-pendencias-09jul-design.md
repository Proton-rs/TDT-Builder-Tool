# SP-Pendencias-09jul — Design

**Data:** 2026-07-09
**Status:** aprovado (design validado com usuário em sessão)
**Escopo:** spec unificada, 5 fases, 9 pendências levantadas em uso real (input homogêneo IMA + GAU v09).

---

## Contexto

Pendências observadas em uso real do gerador de TDT. Evidências ancoradas no dado real:
`docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx` (GTD) e `docs/TDT/exportTDT_UTR_FWB_1_20260626.xlsx` (FWB).

Decisões do usuário (registradas em sessão):
- Nome de arquivo: **SUB + data + sequência** (`TDT_GAU_20260709.xlsx`, `_v2` se existir).
- Auto-tuning de pesos: **grid search offline** contra `gate_tdt_real`.
- Escopo: **spec unificada com fases**.
- Itens "conferir" (startup, revisão homogênea): **diagnóstico com fix condicional** — se a causa for óbvia, corrige na mesma task.

---

## Fase 1 — Fixes rápidos

### 1.1 Remote Point Alias em YYYYMMDD
`_alias_hoje()` em `src/tdt/engine_tdt.py:110` usa `strftime("%m%d%Y")` (padrão EUA, ex. `07092026`).
**Fix:** `%Y%m%d` (→ `20260709`).
**Evidência:** TDT real GTD usa alias `20260204`/`20260210` (YYYYMMDD) na aba DNP3_DiscreteAnalog.

### 1.2 KMDF → Unitless (+ auditoria de tipos sem tradução)
`_MEASUREMENT_TYPE_PT_EN` (`engine_tdt.py:198`) tem só 5 entradas. KMDF tem
`TIPO DE MEDIÇÃO = "Comprimento"` na lista padrão → sem tradução → Measurement Type vazio.
**Fix:** mapear `"COMPRIMENTO" → "Unitless"` (decisão do usuário: KMDF é unitless no ADMS).
**Auditoria:** a lista padrão v6 tem mais 6 tipos sem tradução — Ângulo de Tensão, Discreto,
Fator de Potência, Frequência, Potência Aparente, Umidade. Mapear cada um para o domínio
`MeasurementType` do `DMSMatchingTemplateInfo` (template) quando houver equivalente
(ex. Frequency, PowerFactor, ApparentPower); sem equivalente → documentar e deixar vazio
(nunca inventar valor fora do domínio — ADMS rejeita no import).

### 1.3 Nome dos arquivos gerados com subestação + data + sequência
Hoje: `TDT.xlsx` fixo (`src/tdt/ui/tela_geracao.py:186`) e `Auditoria_Revisao.xlsx` fixo
(`src/tdt/relatorio_revisao.py:133`).
**Fix:** `TDT_<SUB>_<YYYYMMDD>.xlsx` e `Auditoria_<SUB>_<YYYYMMDD>.xlsx`; se já existir,
sufixo `_v2`, `_v3`, ... A sigla vem de `estado.subestacao` (já disponível na tela de geração);
sem sigla → omite o segmento (`TDT_20260709.xlsx`), nunca quebra a geração.
Helper único de nomeação (mesma regra pros dois arquivos), usado pela tela e pelo relatório.
O diálogo "Sobrescrever?" continua valendo só quando o nome final colide (com sequência,
colisão só ocorre em corrida).

---

## Fase 2 — Path homogêneo

### 2.1 Device mapping: número do módulo vem do bloco de header
No input homogêneo real (IMA), cada sheet tem acima do cabeçalho de dados um bloco:

```
EQUIPAMENTO | NÚMERO OPERATIVO / MNEMNICO
MÓDULO      | 23
DJ          | 52-23
SECC        | 29-62
...
```

A coluna `MÓDULO` das linhas de dados traz **só o tipo** (`AL`, `LT`, `TR`, `TRF`, `BC`, ...).
Hoje `estruturador_homogeneo.py:87` usa a célula da coluna direto → módulo vira `AL` (sem número)
→ Signal Name / Device Mapping errados.

**Fix:** ao detectar o header (`detectar_header`), escanear as linhas acima
(`rows[:header_idx]`) pelo par (`MÓDULO`, `<número>`) do bloco `EQUIPAMENTO / NÚMERO OPERATIVO`;
compor `modulo_nome = <tipo da coluna> + <número do bloco>` (ex. `AL` + `23` → `AL23`).
- Fallback 1: coluna já traz número (`LT 1`) → comportamento atual (só normaliza espaço).
- Fallback 2: bloco ausente/ilegível → comportamento atual + registro em diagnóstico
  (não inventa número).
- `origem_contexto` do `Modulo` passa a indicar a fonte (`coluna:MODULO` vs
  `coluna:MODULO+header:NUMERO_OPERATIVO`) para auditoria.

O bloco também traz números operativos por equipamento (`DJ | 52-23`) — fora de escopo usar
agora; o parser deve devolver o dict completo para uso futuro (custo zero, já está lendo).

### 2.2 Sinais não decididos na revisão (diagnóstico + fix condicional)
Comportamento correto que fica: pontos futuros (`Utilizado? = NÃO`, sheets `(FUTURO)`) não
entram. O problema: alguns sinais com `Utilizado? = SIM` caem em `pendentes`
(`estruturador_homogeneo.py:114`) porque `lp.por_sigla(sigla)` não acha a sigla.

**Task de diagnóstico:** rodar o input homogêneo real e listar as siglas que caem em
pendentes, com contagem e descrição. Classificar cada uma:
- (a) sigla legítima faltando na lista padrão → adicionar na lista padrão (vira parte da v7
  da Fase 3);
- (b) variação de grafia/normalização (acento, espaço, sufixo) → fix no lookup
  (`por_sigla` já normaliza upper/strip; cobrir o gap encontrado);
- (c) sigla realmente desconhecida/ambígua → fica em revisão (correto), documentar.

---

## Fase 3 — DiscreteAnalog / TAP

### 3.1 Nova aba `DiscreteAnalog` na lista padrão (v7)
Gerar `docs/Pontos Padrao ADMS_v7.xlsx` = v6 + aba nova `DiscreteAnalog`, colunas no mesmo
padrão das abas existentes (SINAL, DESCRIÇÃO NOVA, SIGNAL TYPE, ...) + campos que a categoria
exige, preenchidos a partir da linha real de TAP na GTD/FWB:

| Campo | Valor (TAP) | Fonte |
|---|---|---|
| SINAL | TAP | — |
| DESCRIÇÃO NOVA | Posição do TAP (a confirmar na DE->PARA/GTD) | lista padrão |
| SIGNAL TYPE | TapPosition | GTD real |
| MEASUREMENT TYPE | Discrete | GTD real |
| FASES | ABC | GTD real |
| DIRECTION | Read | GTD real |
| NORMAL VALUE | 9 | GTD real |
| REMOTE POINT TYPE | Analog | GTD real |
| OUTPUT DATA TYPE (deadband) | Float | GTD real (APROCESSING_DEADBANDTYPE) |
| DEVICE MAPPING | ref. comando COMTAP (`<nome>_COMTAP`) | GTD real |
| APLICABILIDADE | TRANSFORMADOR | domínio (só TR tem TAP) |

Uma linha (TAP é hoje a única exceção dessa categoria), estrutura pronta pra crescer.

### 3.2 Pipeline reconhece e gera DiscreteAnalog
- `src/tdt/dados/lista_padrao.py`: ler a aba nova → `SinalPadrao` com
  `categoria="DiscreteAnalog"`; aba ausente (listas v6 e anteriores) → tupla vazia,
  retrocompatível.
- `src/tdt/engine_tdt.py`: constante `SHEET_DISCRETE_ANALOG = "DNP3_DiscreteAnalog"`;
  registro com sigla de categoria DiscreteAnalog vai pra essa sheet do template, com as
  colunas conforme o dado real (Remote Point Type=Analog, Signal Type=TapPosition,
  Normal Value, Device Mapping → COMTAP quando o comando existir no mesmo módulo).
- TAP é **opcional** dentro de transformadores: presente no input → gera; ausente → nada
  (sem obrigatoriedade, sem warning).
- `bench/gate_tdt_real.py`: incluir `DNP3_DiscreteAnalog` em `_SHEETS` para a comparação
  contra GTD/FWB medir a categoria nova.

---

## Fase 4 — Startup lento (diagnóstico + fix condicional)

Suspeito nº 1 já identificado: `src/tdt/ui_main.py:12` importa `criar_encoder`
(`tdt.dados.encoder`) no topo **e não usa** — se esse import puxa
sentence-transformers/torch, é segundos de boot desperdiçados antes da janela abrir.
O comentário "carrega em background" (linha 33) mente: `ListaPadraoADMS.carregar` é síncrono.

**Task:** medir boot com timestamps por etapa (imports, carregar_config, lista padrão,
criação da janela). Fix condicional:
- import morto → remover (fix imediato);
- import pesado legítimo em outro módulo da cadeia → lazy import (dentro da função que usa);
- lista padrão síncrona custando >0.5s → mover pra thread/pós-show.
Critério de aceite: janela visível em <2s em máquina de dev (medido, não estimado).

---

## Fase 5 — Auto-tuning dos pesos de mescla

`Config.peso_tfidf/vetorial/fuzzy` (hoje 0.70/0.25/0.05, calibrado manualmente;
`bench/benchmark.py` usa 0.34/0.33/0.33 — inconsistência a resolver de brinde).

**Design:** script `bench/tune_pesos.py`, **estendendo a montagem já existente de
`bench/exp_pesos.py`** (mesmos scorers/corpus/ground-truth — não duplicar), em 2 estágios:
1. **Grid barato:** varre o simplex completo (passo 0.05, soma = 1.0, 231 combinações)
   com os candidatos por método computados **uma vez** (cache — pesos só entram na mescla);
   métrica: precisão@decididos e acc@1 no ground-truth `ROTULOS` (roteação da Config).
2. **Validação cara:** top-3 combos rodam o pipeline real (`bench/reprocessar_lista1.py`
   parametrizado por pesos) e comparam com `gate_tdt_real.comparar()` contra GTD.
- Saída: tabela completa + top-10 em `bench/resultados/tune_pesos.txt`;
- Só atualiza os defaults em `src/tdt/config.py` se o melhor combo **superar o atual no
  gate** (estágio 2), nunca só pelo estágio 1; registrar antes/depois no ledger;
- determinístico, sem dependência nova, respeita o roteador atual (thresholds fixos —
  tuning de threshold fica fora de escopo).

---

## Testes

- Unit: alias YYYYMMDD; mapa PT→EN (KMDF→Unitless + novos); helper de nome de arquivo
  (com/sem sub, sequência); parser do bloco NÚMERO OPERATIVO (com bloco, sem bloco,
  coluna já numerada); leitura da aba DiscreteAnalog (presente/ausente); roteamento de
  TAP pra sheet nova.
- Regressão global: `bench/gate_tdt_real.py` antes/depois de cada fase (não pode regredir).
- Testes existentes (`tests/test_estruturador_homogeneo.py`, `test_pipeline.py`, suite SAN2)
  continuam verdes.

## Riscos / observações

- `docs/RGE GAU 2026 - Lista de Pontos v09.xlsx` quebra o openpyxl atual
  (`PatternFill ... extLst`, py3.14): se a UI abrir esse arquivo, crasha antes de qualquer
  análise. Não é uma das 9 pendências, mas foi confirmado nesta sessão — tratar como task
  extra da Fase 4 (guard/patch de leitura) ou registrar follow-up.
- Fase 3 muda a lista padrão (v6→v7): scripts que apontam pra versão fixa precisam do
  path novo (`tdt.defaults.DEFAULT_LISTA`).
- Fase 5 só ajusta pesos de mescla; qualquer regressão no gate bloqueia a atualização
  do default.

## Fora de escopo

- Usar os números operativos por equipamento (DJ 52-23) no naming — parser devolve, ninguém
  consome ainda.
- Tuning de thresholds do roteador (gap/pct).
- Sinais DiscreteAnalog além do TAP.
