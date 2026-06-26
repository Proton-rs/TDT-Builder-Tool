# SP C3 — Mineração da Full Base (catálogo de sinais + Measurement Type)

**Data:** 2026-06-26
**Status:** Aguardando revisão do usuário
**Origem:** `docs/observacoes26062026.md` §5.1 (quais sinais existem por tipo de módulo/equipamento → enriquecer o motor de regras), §5.3 (como o KMDF referencia o Measurement Type).
**Escopo:** minerar **offline** a `Export_base_Full` para produzir dois artefatos compactos versionados — (1) catálogo de sinais esperados por tipo de módulo/equipamento; (2) mapa sigla→Measurement Type — consumidos em runtime pelo motor de regras e pelo `engine_tdt`. **Nunca** ler a base de 97MB em runtime.

> Sub-spec da decomposição **C**. Independente de C1/C2 para rodar (mineração é offline), mas o artefato (1) pode **popular** a tabela de topologia da C2 e a classificação de tipo da C1. Alimenta o motor de regras (spec B usa as regras).

---

## Estrutura confirmada da Full Base

`docs/Export_base_Full__27_fev_2026.xlsx` é um export ADMS completo. Sheets relevantes:

- **`DNP3_DiscreteSignals`** (≈237k linhas, 43 cols) e **`DNP3_AnalogSignals`** (≈133k). Colunas-chave (row 4 = display names): `Signal Alias` (descrição humana, ex. "BATERIA - FALHA"), `Measurement Type`, `Substation`, `Feeder`, `Feeder Object`, `Bank`, `Bay`, `Device`, `Device Mapping`, `Description`, `Signal Type`, `Phases`, `Side`, `Direction`. **As colunas Feeder/Bank/Bay/Device dão a topologia/módulo/equipamento explícitos.**
- **`DMSMatchingTemplateInfo`**: enums oficiais. Coluna `MeasurementType` = vocabulário válido: `Unitless, Voltage, Current, ActivePower, ReactivePower, CosPhi, Frequency, Temperature, ActiveEnergy, ReactiveEnergy, ApparentPower, Status, SwitchStatus, …`. Outros enums úteis: `DiscreteSignalType`, `SignalDirection`, `PhaseCode`, `AnalogSignalType`.

`Measurement Type` já vem **preenchido por linha** nas sheets de sinais (ex.: AnalogSignals → `Current`, `Voltage`; DiscreteSignals → `Status`, `SwitchStatus`). Isso responde §5.3 diretamente: o KMDF referencia o Measurement Type pelo enum de `DMSMatchingTemplateInfo`, e cada sinal carrega o seu.

---

## C3.1 — Script de mineração offline

Novo `scripts/minerar_full_base.py` (CLI, fora do pipeline de runtime). Lê a base em **streaming** (`openpyxl load_workbook(read_only=True, data_only=True)` + `iter_rows`) — nunca materializa a planilha inteira.

### Artefato 1 — Catálogo de sinais por contexto (§5.1)

Agrega, varrendo Discrete+Analog:

- chave de contexto = `(tipo_modulo_normalizado, familia_equipamento)` derivada de `Feeder`/`Bank`/`Bay` (tipo de módulo) + `Device`/`Signal Type` (equipamento);
- valor = contagem de cada **sigla canônica** observada (derivada de `Signal Alias`/`Description` via a mesma normalização do pipeline, `normalizador.canonizar`, para alinhar com as siglas da Lista Padrão).

Saída: `docs/conhecimento_base/catalogo_sinais.json` (compacto: por contexto, lista de `(sigla, frequência)`), versionado no repo.

### Artefato 2 — Mapa sigla → Measurement Type (§5.3)

Agrega `Signal Alias` (→ sigla canônica) → `Measurement Type` mais frequente, validado contra o enum de `DMSMatchingTemplateInfo`. Saída: `docs/conhecimento_base/measurement_type.json`.

> **Passo 0 (exploração):** o join entre as colunas de topologia da base (Feeder/Bank/Bay/Device) e os nossos `TIPOS_MODULO`/famílias de equipamento, e entre `Signal Alias` e as siglas da Lista Padrão, **não é 1:1** — exige uma passada de normalização/mapeamento a confirmar com amostras reais da base. A caracterização (quais valores distintos aparecem nessas colunas) é a primeira tarefa do plano. As tabelas de mapeamento vivem em `config.py`.

---

## C3.2 — Consumo em runtime (artefatos, não a base)

### Nova regra no motor de regras (§5.1)

`motor_regras` ganha `r_catalogo_base(rec, cand, ctx, cfg)`: usando o `catalogo_sinais.json` carregado uma vez, **boost** ao candidato cuja sigla é esperada para o `(tipo_modulo, equipamento)` do registro; **penalidade leve** à sigla nunca/raramente vista naquele contexto. Peso em `config.pesos_regras["catalogo_base"]`. Segue o padrão de função pura do registro de regras (cresce sem reescrever).

Após a reordenação da **spec B** (regras como filtro pós-normalização), `r_catalogo_base` opera como as demais: ajuste bounded sobre candidatos normalizados.

### Measurement Type mais preciso (§5.3)

`engine_tdt._measurement_type` hoje traduz PT→EN com default `"Status"` ([engine_tdt.py:197](../../../src/tdt/engine_tdt.py)). Passa a consultar `measurement_type.json` (sigla → enum) como fonte primária, caindo na tradução atual quando a sigla não está no mapa. Valores sempre dentro do enum oficial.

---

## C3.3 — Carregamento dos artefatos

Serviço de dados em `src/tdt/dados/conhecimento_base.py` (no padrão de `lista_padrao.py`): carrega os dois JSON uma vez, expõe `siglas_esperadas(tipo_modulo, equipamento)` e `measurement_type(sigla)`. Sem acesso a disco dentro de scorers/regras (o serviço injeta os dados, como já é a convenção em `scoring/AGENTS.md`).

---

## Testes (TDD)

| Item | Teste | Asserção mínima |
|------|-------|-----------------|
| C3.1 | `test_minerar_full_base.py` | sobre um **fixture pequeno** (não a base real), agrega contagem por contexto e mapa sigla→MeasurementType; valida contra enum |
| C3.2 | `test_motor_regras.py` (estende) | `r_catalogo_base` dá boost à sigla esperada e penaliza a inesperada no contexto |
| C3.2 | `test_engine_tdt.py` (estende) | Measurement Type vem do mapa quando presente; cai no fallback PT→EN quando ausente; sempre no enum |
| C3.3 | `test_conhecimento_base.py` | carrega JSON, `siglas_esperadas`/`measurement_type` respondem |

A mineração **não** roda nos testes (base de 97MB) — os testes usam fixtures sintéticos; o script real é executado manualmente para gerar os artefatos versionados.

**Gate:** `bench/benchmark.py` — `r_catalogo_base` **deve** subir a taxa de decisão sem aumentar FP (é exatamente o tipo de pista que a obs quer). Peso calibrável; começa conservador.

---

## Critérios de Aceite

1. `scripts/minerar_full_base.py` lê a base em streaming e gera `catalogo_sinais.json` + `measurement_type.json` compactos, versionados em `docs/conhecimento_base/`.
2. O catálogo mapeia `(tipo de módulo, equipamento) → siglas esperadas com frequência`; o mapa de Measurement Type respeita o enum oficial.
3. Runtime consome só os artefatos (nunca os 97MB); `r_catalogo_base` enriquece o ranqueamento; `engine_tdt` preenche Measurement Type pelo mapa com fallback.
4. Benchmark: taxa de decisão sobe sem aumentar FP.
5. Testes verdes com fixtures (sem rodar a mineração real).

---

## Fora de escopo

- Identificar módulo/tipo e inferir equipamento no input do usuário → C1/C2 (C3 só fornece o conhecimento de fundo).
- Re-treinar embeddings com a base → fora; é trabalho de calibração/encoder (memória do projeto).
- Outras sheets da base (Alarmes, MessageMappings, ICCP…) → fora; só DNP3 Discrete/Analog + enums por ora.
