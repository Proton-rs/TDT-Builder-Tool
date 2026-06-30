# Projeto TDT v2 — Visão Geral

Gerado em: 29/jun/2026
Último SP: SP-Pareamento-Double-Bit (commit em andamento)

---

## 1. Propósito

Pipeline que transforma planilhas Excel de pontos de subestação (discretos, analógicos, comandos) em arquivos **TDT** (Telemetry Data Template) compatíveis com o sistema **EcoStruxure ADMS** (protocolo DNP3).

O projeto implementa classificação automática de sinais por descrição textual usando três métodos independentes (TF-IDF, embeddings vetoriais, fuzzy matching), combinados por mescla ponderada e refinados por regras de domínio elétrico.

---

## 2. Stack

| Tecnologia | Versão | Uso |
|-----------|--------|-----|
| Python | 3.14.5 | Runtime |
| pytest | 9.0.3 | Testes |
| PySide6 | 6.11.1 | UI desktop |
| openpyxl | — | Leitura/escrita Excel + TDT |
| scikit-learn | — | TF-IDF vectorizer |
| sentence-transformers | — | Embeddings (MiniLM, e5) |
| faiss-cpu | — | Índice vetorial (produto interno) |
| rapidfuzz | — | Fuzzy matching (token_set_ratio) |
| tomllib | stdlib | Config persistida |

---

## 3. Arquitetura — Pipeline

```
input.xlsx
    ↓
┌─ identificador ────────────────────────┐
│ Detecta rota (homogêneo/não-homogêneo) │
│ Lista sheets de dados                  │
└────────────────────────────────────────┘
    ↓
┌─ analise_colunas ──────────────────────┐
│ Detecta colunas por CONTEÚDO:          │
│ descricao (embedding), indice (int),   │
│ tipo (vocabulário A/C/D)              │
└────────────────────────────────────────┘
    ↓
┌─ estruturador (N0) ────────────────────┐
│ Cria SignalRecords                     │
│ Extrai contexto estrutural do bruto:   │
│ equipamento, barra, fase               │
└────────────────────────────────────────┘
    ↓
┌─ pareamento_polaridade ────────────────┐
│ Par aberto/fechado mesmo equipamento   │
│ → sigla de posição (DJF1/DJA1/SEC*)   │
│ → posicao_ambigua se variante incerta  │
└────────────────────────────────────────┘
    ↓
┌─ 3 scorers paralelos ─────────────────┐
│ TF-IDF  (sklearn, coseno)  — peso 0.70│
│ FAISS   (sentence-transformers) — 0.25│
│ FUZZY   (rapidfuzz token_set) — 0.05  │
└────────────────────────────────────────┘
    ↓
┌─ mescla ────────────────────────────────┐
│ Soma ponderada por sigla candidata      │
└─────────────────────────────────────────┘
    ↓
┌─ ancoragem_sigla (ANCORAGEM) ──────────┐
│ 1. ancorar: injeta sigla literal       │
│    encontrada na descrição (score 0.85)│
│ 2. expansao_candidatos: abre família   │
│ 3. filtrar_subarvore: restringe ao     │
│    sub-ramo da âncora (67N→sem 67P/67F)│
└─────────────────────────────────────────┘
    ↓
┌─ motor_regras (R1-R6 + R_equip) ──────┐
│ 7 regras de domínio ajustam scores     │
│ R1: número proteção ANSI              │
│ R2: opostos (sobre×sub)               │
│ R3: fase                              │
│ R4: estágio                           │
│ R5: comando/status                    │
│ R_eq: equipamento (DJ×SEC)            │
│ R6: lado tensão (AT×BT)               │
└─────────────────────────────────────────┘
    ↓
┌─ roteador ───────────────────────────────┐
│ Cascata: fuzzy≥0.95 → e5≥0.95 →         │
│ consenso+gap dinâmico → quadrante       │
│ Dual-pass para categoria incerta        │
└──────────────────────────────────────────┘
    ↓
┌─ dc_pairer ─────────────────────────────┐
│ Input+Output mesmo (modulo,sigla) → RW  │
└──────────────────────────────────────────┘
    ↓
┌─ normalizador_estrutural ──────────────┐
│ Endereços consecutivos → double-bit    │
│ Endereços duplicados → revisão         │
└──────────────────────────────────────────┘
    ↓
┌─ criador_lista_homogenea ──────────────┐
│ Apenas decididos → ListaHomogenea       │
└──────────────────────────────────────────┘
    ↓
┌─ engine_tdt ────────────────────────────┐
│ Preenche template DNP3 (43+61 colunas)  │
│ DiscreteSignals + AnalogSignals         │
│ → TDT.xlsx                             │
└──────────────────────────────────────────┘
```

---

## 4. SPs Implementados

### SP1 — Backbone Determinístico + Embeddings (23/jun)

**Fundação do pipeline.** Implementado em um `first commit` que estabeleceu:

- `pipeline.py`: orquestrador com steps encadeados
- `contracts.py`: 14 dataclasses imutáveis (SignalRecord, Candidato, etc.)
- `config.py`: Config com pesos, thresholds, caminhos
- `identificador.py`: classificação de rota + detecção de sheets
- `analise_colunas.py`: detecção de colunas por conteúdo (embedding, inteiros, vocabulário)
- `estruturador.py`: montagem de SignalRecords a partir de linhas
- `normalizador.py`: pipeline N1-N5 + canonização (em SP6 ganhou N0)
- `tokenizer.py`: reconstrução de siglas separadas ("67 N" → "67N")
- `scoring/tfidf.py`: scorer TF-IDF coseno
- `scoring/vetorial.py`: scorer FAISS (embedding coseno)
- `scoring/mescla.py`: soma ponderada com pesos configuráveis
- `roteador.py`: cascata de decisão (fuzzy ≥ 0.95 → e5 ≥ 0.95 → consenso → quadrante)
- `dc_pairer.py`: pareamento D+C → ReadWrite
- `normalizador_estrutural.py`: double-bit detection
- `criador_lista_homogenea.py`: montagem da lista final
- `engine_tdt.py`: geração do TDT a partir do template
- `auditoria.py`: coleta de eventos (log + callback)
- `dados/lista_padrao.py`: leitura da lista de pontos padrão ADMS
- `dados/indice_vetorial.py`: índice FAISS persistível
- `dados/encoder.py`: wrapper SentenceTransformer com cache
- `matchers/fuzzy_match.py`: fuzzy token_set_ratio + boost de sigla
- `cli.py`: interface CLI (`tdt gerar INPUT.xlsx --output ...`)

**Melhorias posteriores (mesmo SP1):**
- `scoring/calibracao.py`: MinMax + Temperature scaling para escalas comparáveis
- `roteador.py`: dual-pass para categoria incerta, desempate por gap + centroide
- `motor_regras.py`: 7 regras de domínio
- `normalizador.py`: N4 (correção de typos por fuzzy contra vocabulário), N5 (normalização de unidades)
- Suporte a e5 assimétrico no encoder + índice vetorial

---

### SP2 — Agentes LLM

**Em espera.** Sem spec, sem plano, sem implementação. Extensão futura para usar LLM como classificador adicional ou para revisão automatizada.

---

### SP3 — Otimização de Embeddings

**Absorvido pelo SP1.** O tuning de embeddings foi feito como parte das melhorias de análise: e5 assimétrico, afinidade por centroide, calibração.

---

### SP4 — UI Desktop + TDT (24/jun)

**Quatro entregas:**

| Componente | Arquivos | O quê |
|-----------|----------|-------|
| UI Desktop | `ui/app.py`, `ui_main.py` | MainWindow com QStackedWidget (3 telas) |
| Tela Inicial | `ui/tela_inicial.py` | Configura input/output, dispara pipeline |
| Tela Revisão | `ui/tela_revisao.py` | Tabela rica 15 colunas, painel de scores, busca ADMS |
| Tela Config | `ui/tela_config.py` | Thresholds, pesos, modelo, caminhos |
| Worker | `ui/worker.py` | QThread com cancelamento cooperativo |
| Modelo | `ui/modelo_tabela.py` | QAbstractTableModel |
| Proxy | `ui/proxy_revisao.py` | QSortFilterProxyModel (filtro + ordenação) |
| Delegate | `ui/delegate_sinal.py` | Combo editor para célula Sinal |
| Busca ADMS | `ui/busca_adms.py` | Busca linear na lista padrão |
| Config IO | `ui/config_io.py` | Persistência em TOML |
| Tema | `ui/tema.qss` | 129 linhas, roxo/monospace |

**Redesenho (SP4.1):** Correções B1/B2/B5, tema refinado, tabela com cores/tooltip, painel de scores, delegate inline editing, busca ADMS ao vivo.

**Correção Output TDT:** Formatação correta (table ref, CF, data validation), padrão hierarchical naming para signal names, coordenadas de saída para comandos órfãos.

**Escopo Analógico:** Dual-pass pipeline para sinais analógicos, sheet DNP3_AnalogSignals (61 colunas), campos derivados (Side, AOR, DeviceMapping, RemoteUnit/RemotePoint, NormalValue, Alias).

---

### SP5 — Correção de Classificação + Revisão (24/jun)

**5 tracks paralelas:**

| Track | O quê | Evidência |
|-------|-------|-----------|
| A | Códigos A/C/D na coluna Tipo, centroide desempate, thresholds analógicos frouxos | `analise_colunas.py`, `vocabulario_tipo.py` |
| B | GPU opcional no encoder | `dados/encoder.py` |
| C | Filtros + ordenação na tela de revisão | `ui/proxy_revisao.py` |
| D | Relatório de auditoria (Auditoria_Revisao.xlsx) | `relatorio_revisao.py` |
| E | Pasta default no file picker | `ui/config_io.py`, `defaults.py` |

---

### SP6 — Normalização Estrutural (24/jun)

| Task | Componente | O quê |
|------|-----------|-------|
| 1 | `normalizador.py` | `ContextoEstrutural` + extração de equipamento via `\b(\d+)-(\d+)\b` → `_EQUIPAMENTO_ANSI` |
| 2 | `normalizador.py` | Extração de barra (`BARRA P`→Principal, `BARRA A`→Auxiliar) |
| 3 | `normalizador.py` | `_fase_no_texto` migrada de `motor_regras` → `normalizador`; `r3_fase` simplificado |
| 4 | `estruturador.py` + `contracts.py` | Wiring N0 → `SignalRecord`, campo `Eletrico.barra` |
| 5 | `normalizador.py` | `_SEPARADORES` expandido para `(),;:` |
| 6 | `motor_regras.py` + `config.py` | `r_equipamento` + `equipamento_da_sigla` + peso 0.12 |

**Lógica central:** extrair equipamento/barra/fase do texto **bruto** (antes da normalização N1-N5), porque o colapso de hífens, pontos e stopwords (ex: "A") destruiria a informação estrutural.

---

### SP-Categoria — Barreira de domínio no dual-pass (29/jun)

**Problema:** 213 sinais analógicos classificados como discretos (e vice-versa) porque o dual-pass não respeitava a categoria do bundle durante a expansão de candidatos.

**Solução:** ancoragem de categoria por bundle — cada bundle (disc/ana) expande candidatos e aplica filtro de especificidade **só dentro do seu domínio**; candidatos do domínio oposto não entram na disputa do bundle. Se ambos os bundles decidem siglas de categoria diferente, o sinal vai para revisão com `motivo="categoria_incompativel"`.

Spec: `docs/superpowers/specs/2026-06-29-sp-categoria-dual-pass-fix-design.md`

---

### SP-Ancoragem — Sigla explícita na descrição (29/jun)

**Problema diagnosticado:** 132 sinais com a própria sigla escrita na descrição sendo decididos para famílias erradas (ex.: `"Proteção 67 N Temporizado"` → `PRTF`), porque a sigla `67N` nunca entrava como candidato.

**Solução:** novo módulo `ancoragem_sigla.py` com três etapas dentro de `_classificar_sinal`:

1. **`detectar`** — encontra siglas da LP embutidas nos tokens da descrição (âncora exata + junção de tokens adjacentes "67"+"N"→"67N").
2. **`ancorar`** — injeta a sigla detectada como candidato com `score=0.85` (ou re-pontua se já presente).
3. **`filtrar_subarvore`** — após `expansao_candidatos` abrir toda a família pelo prefixo de 2 dígitos, restringe cada família ancorada ao sub-ramo da âncora (`67N` → mantém `67N*`, remove `67F*/67P*/67_*`). Isso evita empate entre ramos irmãos causado pela expansão ampla.

**Guard de precisão:** apenas siglas "específicas" (len ≥ 3, tem dígito E letra) são ancoradas — exclui números de identificação de equipamento (`52-21`, `21Q0`). Múltiplas famílias → `motivo="sigla_multipla"` na revisão.

**Resultado no input real:** `67 N - Estágio 2` → `67N2` ✓; `67N REVERSE` → `67NR` ✓; `63C` → `63C` ✓.

Spec: `docs/superpowers/specs/2026-06-29-sp-ancoragem-sigla-explicita-design.md`

---

### SP-Pareamento-Double-Bit — Seccionadora aberta/fechada (29/jun)

**Problema:** pares aberto/fechado de **seccionadora** não eram pareados pelo módulo de polaridade — `pareamento_polaridade.py` só cobria Disjuntor (`DJF1`). Seccionadoras divergiam para o scorer e se separavam.

**Catálogo auditado** (`Export_base_Full_limpo.json`): 12 siglas double-bit na LP; 9 são posição de chave:
- Disjuntor: `DJF1` (NF), `DJA1` (NA)
- Seccionadora: `SECB` (bypass), `SECC` (carga), `SECF` (fonte), `SECG` (terra/aterramento), `SECI` (interbarras), `SECL` (interlinhas), `SECT` (transferência)

**Solução:** resolução por **palavra-função** na descrição combinada do par:
- `CARG*` → SECC · `BYPASS/BY/BYPS*` → SECB · `TRANSFER*` → SECT · `TERRA/ATERR*` → SECG · `FONT*` → SECF · `INTERBAR*` → SECI · `INTERLINHA*` → SECL
- Disjuntor NA detectado pelo token exato "NA" → `DJA1`
- Sem keyword reconhecida → `ItemRevisao(motivo="posicao_ambigua")` (nunca chuta)

**Guard TRANSF vs TRANSFORMADOR:** keyword usa `"TRANSFER"` (8 chars); `"TRANSFORMADOR"` começa com `"TRANSFOR"`, não `"TRANSFER"` — evita falso positivo de seccionadora de transformador sendo classificada como transferência.

**Retorno:** `forcar_polaridade_equipamento` agora retorna `tuple[list[SignalRecord], list[ItemRevisao]]`; pipeline desempacota e coleta revisões.

Spec: `docs/superpowers/specs/2026-06-29-sp-pareamento-double-bit-posicao-design.md`

---

## 5. Motor de Regras — Detalhamento

| # | Função | O que faz | Delta | Gatilho |
|---|--------|-----------|-------|---------|
| R1 | `r1_numero_protecao` | Boost se número ANSI casa com descrição; penalidade se diverge | ±0.10 | Qualquer sinal com número |
| R2 | `r2_opostos` | Penaliza polaridade oposta (sobrecorrente vs subcorrente, sobretensão vs subtensão) | −0.15 | Pares opostos detectados |
| R3 | `r3_fase` | Favorece candidato com mesma fase (A/B/C/N/AB/BC/CA/ABC) | ±0.10 | Fase detectada |
| R4 | `r4_estagio` | Boost se sigla termina no dígito do estágio (E1-E4) | +0.10 | Estágio na descrição |
| R5 | `r5_comando_status` | "Comando" no texto favorece candidatos CMD | +0.08 | Token comando |
| Req | `r_equipamento` | Penaliza se família diverge (DJ vs SEC) | −0.12 | `equipamento_alvo` presente |
| R6 | `r6_lado_tensao` | "AT" favorece candidatos de alta tensão | ±0.08 | Lado detectado |

---

## 6. Normalização — Pipeline N0-N5

```
Texto bruto
  ↓ N0 — extrair_contexto_estrutural()
  Remove padrão de equipamento (52-1 → equipamento_alvo=Disjuntor)
  Remove BARRA X → barra
  Remove FASE X / NEUTRO / TRIFASICO → fase
  Retorna ContextoEstrutural + texto limpo
  ↓ N1 — expandir_abreviacoes()
  Whole-token: DISJ→DISJUNTOR, TRAFO→TRANSFORMADOR, etc.
  ↓ N2 — separar_ids_equipamento()
  Remove 52-1, 01Q0 (preserva 67, 87 como números ANSI)
  ↓ N3 — remover_boilerplate()
  Descarta prefixo de equipamento que dilui o match
  ↓ N4 — corrigir_typos()
  Fuzzy contra vocabulário (threshold 85, ~1 edição)
  ↓ N5 — normalizar_unidades()
  KV→KV, Amp→A, Hz→HZ, MW→MW, MVAr→MVAR
  ↓ Tokenizer
  "67 N" → "67N", "50 BF" → "50BF"
  ↓ Texto canônico
```

---

## 7. Calibração e Decisão (Roteador)

### Cascata do roteador (`roteador.rotear()`):

1. **Fuzzy ≥ 0.95** → grafia idêntica ou quase → aceita direto
2. **E5 ≥ 0.95** → semântica muito forte → aceita direto
3. **Consenso (≥ min_consenso métodos)** + gap dinâmico:
   - *Decidido* se gap > threshold_gap (discreto 0.08, analógico 0.05)
   - *Ambíguo* se gap ≤ threshold_gap
4. **Sem consenso** → quadrante (percentual × gap) — fallback legado

### Dual-pass para categoria incerta (`_classificar_roteado()`):
- Passa como Discreto **e** como Analógico
- Escolhe o que tiver maior gap entre 1º e 2º colocado
- Se gap e centroide empatarem → Ambíguo (vai para revisão)

---

## 8. Testes

**511 testes, 0 falhas** (29/jun/2026).

Arquivos de teste em `tests/`. Fixtures globais em `conftest.py`:
- `docs/dnp3_template.xlsx`
- `docs/Pontos Padrao ADMS_v2.xlsx` (`lista_padrao_path`)
- `docs/input_homogeneo.xlsx`

TDD obrigatório: todo módulo tem seu `test_<modulo>.py`.

---

## 9. Dados Reais

Base de 27/fev/2026 (`docs/Export_base_Full__27_fev_2026.xlsx`):
- 7.397 RTUs DNP3
- 237.727 sinais discretos
- 70 RTUs IEC 104, 27.130 discretos, 4.886 analógicos
- 14 RTUs IEC 101, 1 ICCP (ONS)
- 258 grupos de varredura DNP3

> IEC 104 e IEC 101 estão fora de escopo. O pipeline atual só gera TDT DNP3.

---

## 10. Commits (60 no total)

Evolução cronológica resumida:

```
SP1:  first commit → backbone, contratos, pipeline, 3 scorers, engine_tdt
      Melhorias: calibração, e5, motor_regras 6 regras, normalizador N4-N5
SP4:  UI PySide6 → 3 telas, worker, modelo, proxy, delegate, tema
      Redesenho, correção output TDT, escopo analógico
SP5:  5 tracks paralelas → classificação A/C/D, GPU, filtros, relatório, pasta default
SP6:  Normalização estrutural → N0, equipamento/barra/fase, r_equipamento
SP7-SP10, spA-spF: lista homogênea determinística, filtros UI, completude TDT,
      pareamento D+C (DJF1), identidade módulo, melhorias de análise e scoring
SP-Categoria (29/jun): barreira de domínio dual-pass → elimina 213 FPs categoria
SP-Ancoragem (29/jun): ancoragem_sigla.py → injeta sigla explícita como candidato;
      filtrar_subarvore limita expansão ao sub-ramo da âncora (67N→sem 67P/67F)
SP-Pareamento-Double-Bit (29/jun): pareamento_polaridade generalizado para SEC*
      (7 variantes por palavra-função + DJA1 + posicao_ambigua); retorno com revisão
```

---

## 11. Como Usar

### CLI
```bash
python -m tdt.cli gerar input.xlsx --output output/meu_tdt.xlsx
```

### UI
```bash
python -m tdt.ui_main
```

### Testes
```bash
pytest -v
```

---

## 12. Próximos Passos Possíveis

- **SP2** — Agentes LLM para classificação auxiliar ou revisão automatizada
- **SP7+** — Suporte a IEC 104, IEC 101, ICCP
- **SP7+** — Benchmark formal com dados reais (precisão, recall, F1)
- **SP7+** — Pipeline de CI/CD (GitHub Actions)
- **SP7+** — Otimização de performance (batch processing, GPU full pipeline)
