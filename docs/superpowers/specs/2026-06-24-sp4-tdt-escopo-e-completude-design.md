# SP4 — Escopo de Sinais Analógicos + Completude de Campos da TDT

**Data:** 2026-06-24
**Status:** Aprovado para implementação
**Escopo:** (1) trazer sinais analógicos para classificação/geração (hoje descartados); (2) preencher campos da TDT que hoje saem vazios mas têm valor previsível/derivável, segundo a análise do `Export_base_Full__27_fev_2026.xlsx`.

---

## 0. Contexto

Após a correção do `Output Coordinates` para comandos órfãos (já implementada, ver `engine_tdt.py:_valores`), restam dois problemas reportados pelo usuário:

1. **Sinais analógicos são descartados do pipeline** (`pipeline.py:148`): nunca são classificados contra a Lista Padrão ADMS, nunca aparecem na tela de revisão, nunca saem na TDT (sheet `DNP3_AnalogSignals` fica sempre vazia).
2. **A TDT discreta gerada tem colunas vazias que, no export real de produção, quase sempre têm valor** (`Side`, `Output Register`, `Remote Point Type`, `Remote Point Name`, `Phases`, `Signal AOR Group`, `Device Mapping`, `Remote Unit`, `Remote Point Custom ID`, `Normal Value`, `Remote Point Alias`). Análise de 237.726 linhas do export real confirmou padrões deriváveis para a maioria desses campos.

---

## 1. Sinais Analógicos

### 1.1 Categoria incerta — dual-pass direcionado

`estruturador.py` define a categoria (`Discrete`/`Analog`) por palavra-chave em marcador de seção ou coluna `Tipo`. Quando nenhuma pista aparece, cai num default fixo (`"Discrete","Input"`) sem nenhum sinal de alerta — um sinal analógico pode silenciosamente virar "discreto".

**Mudança em `contracts.py`:**
```python
@dataclass(frozen=True)
class TipoSinal:
    categoria: str
    is_double_bit: bool
    direcao: str
    categoria_confiavel: bool = True  # False quando nenhuma pista (marcador/Tipo) foi encontrada
```

**Mudança em `estruturador.py`:** ao montar o `SignalRecord`, se nem `cat_dir` (coluna Tipo) nem um marcador de seção específico definiram a categoria daquela linha (ou seja, `secao` ainda está no default inicial e `cat_dir is None`), seta `categoria_confiavel=False`.

**Mudança em `pipeline.executar()`:**
- Constrói **dois** conjuntos de scorers (tfidf/vetorial/fuzzy + índice vetorial), um a partir de `lp.discretos`, outro de `lp.analogicos` — mesma função `_corpus`/`ScorerTFIDF.construir`/`IndiceVetorial.construir`/`FuzzyMatcher.construir` de hoje, parametrizada pela categoria.
- Remove o bloco que descarta `categoria == "Analog"`.
- Para registros com `categoria_confiavel=True` (a maioria): roda só o scorer set da categoria já conhecida — sem mudança de custo.
- Para registros com `categoria_confiavel=False`: roda os dois scorer sets e decide:
  - **só um decide** → usa esse resultado (categoria + sigla travadas no registro).
  - **os dois decidem** → vai para revisão, `motivo="categoria_ambigua"`, com os candidatos das duas análises juntos (não decide automaticamente qual categoria é a correta).
  - **nenhum decide** → revisão normal (`motivo="score_baixo"`), candidatos mesclados das duas análises.

Roteador (`roteador.py`) e motor de regras (`motor_regras.py`) não mudam — já são agnósticos de categoria.

### 1.2 Config — thresholds/pesos separados para Analog

```python
peso_tfidf_analog: float = 0.34
peso_vetorial_analog: float = 0.33
peso_fuzzy_analog: float = 0.33
threshold_pct_analog: float = 0.45
threshold_gap_analog: float = 0.08
```
Defaults idênticos aos de hoje (não recalibra nada agora; só separa o knob). `pesos_regras`, `gaps_por_confianca`, `min_consenso` continuam compartilhados — são regras de domínio (fase, proteção, etc.) que valem igual pras duas categorias.

### 1.3 Pareamento D+C

Sinais analógicos não têm comando de saída (confirmado com o usuário) — `dc_pairer.parear` não muda e não é aplicado a registros `Analog`.

### 1.4 Geração — sheet `DNP3_AnalogSignals`

`engine_tdt.py`:
- Generaliza `_expandir_tabela`/`_expandir_cf`/`_expandir_dv` para receber o nome da sheet (hoje hardcoded em `SHEET_DISCRETOS`).
- Nova `SHEET_ANALOGICOS = "DNP3_AnalogSignals"`, `COLUNAS_ESPERADAS_ANALOG = 61`.
- Nova `_valores_analog(rec, subestacao, padrao)` — campos mínimos: `Signal Name` (mesmo `_nome_hierarquico`), `Signal Alias`, `Signal Type` (da Lista Padrão), `Phases`, `Direction` (sempre `Read`, sem output), `Input Coordinates`, `Remote Point Type = "Analog"` (constante; no export real 99% é "Analog"), além dos campos derivados compartilhados com discretos (seção 2.2: `Side`, `Output Register`, `Remote Point Name`, `Signal AOR Group`, `Device Mapping`, `Remote Unit`, `Remote Point Custom ID`, `Remote Point Alias`). `Message Mapping` e `Normal Value` ficam vazios (não existem na sheet/Lista Padrão para analógicos). **`Measurement Type` fica em branco** — no export real varia por grandeza física (Current/Voltage/Unitless/…), não derivável sem a unidade de medida; entra junto com `GrandezasAnalogicas` quando o input fornecer unidade/escala. `GrandezasAnalogicas` (unidade/escala) não é preenchida ainda — campo já existe no contrato.
- `gerar()` escreve nas duas sheets do mesmo workbook: discretos filtra `categoria=="Discrete"`, a nova função filtra `categoria=="Analog"`.

### 1.5 Testes

- `tests/test_pipeline.py`: sinal analógico chega a `decididos` (hoje só testa o skip); cenário de `categoria_confiavel=False` com dual-pass (só um decide / ambos decidem / nenhum decide).
- `tests/test_engine_tdt.py`: bloco novo para `DNP3_AnalogSignals` (table ref, nome hierárquico, Input Coordinates).
- `tests/test_estruturador.py`: `categoria_confiavel=False` quando não há pista nenhuma na sheet.

---

## 2. Completude de Campos da TDT

Baseado na análise coluna-a-coluna do `Export_base_Full__27_fev_2026.xlsx` (237.726 linhas, sheet `DNP3_DiscreteSignals`) comparado ao `output/TDT.xlsx` atual.

### 2.1 Constantes (sem variação observada no export real)

| Campo | Valor | Observação |
|---|---|---|
| `Side` | `"None"` (string literal) | 237.725/237.726 no export real |
| `Output Register` | `False` | 237.726/237.726 |
| `Remote Point Type` | `"Status"` | 237.726/237.726, mesmo em Write/ReadWrite |

### 2.2 Deriváveis de dados já existentes no pipeline

| Campo | Regra |
|---|---|
| `Remote Point Name` | = `Signal Name` (99,6% idênticos no export real) |
| `Phases` | persistido em `eletrico.fase` no momento da decisão, reusando `motor_regras._fase_da_sigla(sigla)` — hoje essa função só é usada de forma descartável dentro da regra de scoring `r3_fase`; o resultado nunca é gravado no registro final. |
| `Signal AOR Group` | `f"{subestacao} {'Distr' if alimentador else 'Trans'}"`; `alimentador` = `modulo.nome` normalizado (sem espaço) começa com `AL` seguido de dígito (ex. `AL11`). Vazio se `subestacao` for `None`. |
| `Device Mapping` | = `Signal Name`, exceto quando `sp.signal_type == "RelayTrip"` (Lista Padrão) → insere `_PROT_` antes da sigla no nome (ex. `GTA_AL11_52-22_43TC` → `GTA_AL11_52-22_PROT_43TC`). |
| `Remote Unit` | `f"UTR_{subestacao}_1"`. Vazio se `subestacao` for `None`. Número fixo em `1` (não há outra fonte de numeração de UTR no pipeline). |
| `Remote Point Custom ID` | `f"{signal_name}_{remote_unit}"`. Vazio se `remote_unit` vazio. |
| `Remote Point Alias` | data de hoje, formato EUA `MM/DD/YYYY` — gerada uma vez no momento do build, igual para todas as linhas (não é dado por sinal). |
| `Normal Value` | Lista Padrão ADMS ganha leitura de duas colunas hoje ignoradas: `FUNÇÃO` (ex. `"Transit;NORMAL;ATUADO;Error"`) e `VALOR` (ex. `"0;1;2;3"`). `Normal Value` = valor de `VALOR` na posição do estado `NORMAL` dentro de `FUNÇÃO` (sempre índice 1 nos dados observados — formato fixo `Transit;<normal>;<anormal>;Error`). Alimenta `MapeamentoEstados` (`estados_brutos`, `valores_scada`), hoje nunca populado em lugar nenhum do pipeline. |

### 2.3 Fora de escopo (sem dado confiável para derivar)

| Campo | Motivo |
|---|---|
| `Signal Custom ID` | Formato inconsistente no export real (UUID, `SCID_<id>`, string livre) — parece gerado pelo próprio ADMS na importação. Fica em branco. |
| `Device`, `Bank`, `Bay`, `Feeder`, `Feeder Object`, `Description`, `Annual Schedule`, `DOM Catalog` | Sempre vazios também no export real de produção — não preencher. |

### 2.4 Mudanças de código

- `lista_padrao.py`: `SinalPadrao` ganha `estados_brutos: str | None` e `valores_scada: tuple[int, ...]`; `_ler_sheet` para `DiscreteSignals` passa a mapear `"FUNÇÃO"` e `"VALOR"`. Sheet `AnalogSignals` não tem essas colunas — fica `None`/`()`.
- `motor_regras.py`: `_fase_da_sigla` é exportada (sem underscore, ou módulo dedicado) para reuso fora do motor de regras.
- `pipeline.py` (`_classificar_sinal`): após `roteador.rotear` decidir, se `decidido.status == "decidido"` e `decidido.eletrico.fase is None`, deriva a fase a partir da sigla decidida e grava em `decidido.eletrico.fase` (via `dataclasses.replace`).
- `engine_tdt.py` (`_valores`): adiciona os campos novos. Helpers: `_eh_alimentador(modulo_nome) -> bool`, `_eh_protecao(sp) -> bool`, `_device_mapping(nome, sp) -> str`, `_aor_group(subestacao, alimentador) -> str | None`, `_remote_unit(subestacao) -> str | None`. Mesmas regras aplicadas em `_valores_analog` onde os campos existirem na sheet de analógicos (`Side`, `Output Register`, `Remote Point Type`, `Remote Point Name`, `Signal AOR Group`, `Device Mapping`, `Remote Unit`, `Remote Point Custom ID`, `Remote Point Alias` também existem na sheet `DNP3_AnalogSignals`).

### 2.5 Testes

- `tests/test_lista_padrao.py`: leitura de `FUNÇÃO`/`VALOR`, `Normal Value` derivado corretamente (índice 1).
- `tests/test_engine_tdt.py`: um teste por campo novo (constantes, `Remote Point Name`, `Signal AOR Group` com/sem alimentador, `Device Mapping` com/sem proteção, `Remote Unit`, `Remote Point Custom ID`, `Remote Point Alias` no formato `MM/DD/YYYY`).
- `tests/test_motor_regras.py` ou novo teste de pipeline: `eletrico.fase` populado após decisão, a partir da sigla.

---

## 3. Critérios de Aceite

1. Sinal analógico de entrada aparece na tela de revisão, é comparado contra a Lista Padrão ADMS (separadamente dos discretos) e sai na sheet `DNP3_AnalogSignals` do TDT.
2. Sinal com categoria estruturalmente incerta passa pelas duas análises; resultado ambíguo vai para revisão com candidatos das duas, sem decisão automática.
3. Output TDT (discreta e analógica) preenche: `Side`, `Output Register`, `Remote Point Type`, `Remote Point Name`, `Phases`, `Signal AOR Group`, `Device Mapping`, `Remote Unit`, `Remote Point Custom ID`, `Remote Point Alias`, `Normal Value` — segundo as regras da seção 2.
4. `Signal Custom ID` e os campos da seção 2.3 continuam vazios (sem fabricar dado).
5. Testes existentes continuam verdes (170/170); novos testes cobrem cada regra nova.
