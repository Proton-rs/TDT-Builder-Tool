# Lista Padrão ADMS v6 — enriquecimento por auditoria (variantes reais) — Design

**Data:** 2026-06-26
**Status:** spec (brainstorming completo) — pronto para virar plano de implementação

## Objetivo

Produzir `docs/Pontos Padrao ADMS_v6.xlsx`: a lista padrão com as descrições
(`DESCRIÇÃO NOVA`) **enriquecidas com variantes terminológicas reais** mineradas
dos arquivos de auditoria do pipeline (`Auditoria_Revisao*.xlsx`), para **melhorar
o matching sem regredir a discriminação** entre siglas.

A v6 **substitui a v2 como lista default de matching** (benchmark v6 >= v2).

## Contexto e diagnóstico

### O que aprendemos com a v5

A v5 enriqueceu descrições com texto ANSI C37.2 oficial + domínio ADMS —
**compartilhado entre siglas da mesma família** (ex: todo `50*` recebeu o mesmo
append "ANSI 50 SOBRECORRENTE INSTANTÂNEA"). Isso **diluiu a discriminação TF-IDF**
porque tokens comuns a múltiplas siglas perdem poder separador:

| Métrica | v2 (baseline) | v5 (ANSI) |
|---------|:-:|:-:|
| acc@1 | 82% | 68% |
| prec@dec | 95% | 68% |

Regressão confirmada. Conclusão: **texto compartilhado entre siglas canibaliza
matching**. O enriquecimento precisa ser **específico por sigla**, não por família.

### Oportunidade: Auditoria_Revisao.xlsx

O pipeline já gera `output/*/Auditoria_Revisao*.xlsx` com **2.371+ sinais reais**
processados, contendo por linha:

| Coluna | O que contém |
|--------|-------------|
| `Descrição Bruta` | Texto original da planilha de entrada (ex: `"Tensão Barra Fases AB"`) |
| `Sigla Decidida` | Sigla v2 que o pipeline escolheu (ex: `VAB`) |
| `Status` | `decidido` ou `revisao` |
| `Score Final` | Score mesclado do melhor candidato |
| `Candidato 1..3` | Top 3 candidatos + scores TF-IDF/vetorial/fuzzy |

Isso nos dá **pares reais `descrição → sigla_v2` já classificados**, sem
precisar classificar manualmente.

### Por que isso resolve o problema da v5

Cada sigla v2 ganha variantes **que só aparecem no contexto daquela sigla**:

```
VAB (v2="TENSAO FASE AB")
  ├─ "Tensão Barra Fases AB"      → variante: Barra, Fases
  ├─ "Tensão de Fase AB"          → variante: de
  └─ "VAB - Tensão Fase AB"       → variante: VAB (sigla na descrição)

FCOM (v2="FALHA COMUNICACAO IED")
  └─ "Falha GOOSE (Falha Recepção IED Adjacente)"
                                   → variante: GOOSE, Recepção, Adjacente
```

Como os termos são **extraídos das descrições reais que mapearam para aquela
sigla**, eles são naturalmente discriminativos — um termo que aparece em
descrições mapeadas para `VAB` dificilmente aparece nas mapeadas para `VBC`.

## Decisões travadas (do brainstorming)

- **Objetivo:** melhorar matching (não só documentação). Validar no benchmark.
- **Fonte:** `output/*/Auditoria_Revisao*.xlsx` (não classificar manualmente).
- **Inclui sinais decididos E em revisão** (revisão com Candidato 1 >= score 0.30
  como hipótese de trabalho; marcados para curadoria posterior).
- **Recipe:** **append-only** sobre descrição v2 verbatim + variantes reais
  específicas da sigla (separador ` — {variante_1}, {variante_2}...`).
- **Critério de inclusão:** só termos que adicionem **sentido semântico novo**
  em relação à descrição v2 (critério inclusivo — nuance pequena também entra).
- **Exclusões obrigatórias:** infinitivos (desligar, ligar, abrir, fechar...);
  IDs de equipamento (`01Q0`, `52-1`); endereços (`1.3/1.1`); mera variação de
  grafia/maiúscula/acento.
- **Contra-checagem:** não adicionar termo que já exista em desc_v2 de **outra**
  sigla (evita canibalização entre siglas).
- **Default:** v6 vira default **após** benchmark confirmar acc@1 >= 82% e
  prec@dec >= 95% (não regredir vs v2).

## Superfície do trabalho

### Arquivos de entrada

| Arquivo | Descrição |
|---------|-----------|
| `output/LISTA 1 - GTA/Auditoria_Revisao2.xlsx` | 2.371 sinais (Gravataí) |
| `output/LISTA 1 - GTA/GTA - Auditoria_Revisao.xlsx` | Lote anterior (Gravataí) |
| `output/HOMOGENEA/HOMOGENEA - Auditoria_Revisao.xlsx` | Sinais de lista homogênea |
| `docs/Pontos Padrao ADMS_v2.xlsx` | Lista base a copiar |
| Outros `*Auditoria_Revisao*.xlsx` em `output/` se existirem | |

### Estimativa de pares úteis

- ~2.000+ linhas decididas (score > 0, sigla confirmada) → **pares diretos**
- ~200-300 linhas em revisão com Candidato 1 >= 0.30 → **pares hipotéticos**
- Cada par gera 1..N variantes (média estimada: 1-3 termos por descrição)
- Após filtragem/deduplicação: **~100-300 siglas enriquecidas**
  (as mais frequentes nos inputs)

### Exemplos concretos (do auditoria real)

| Desc. Bruta | Sigla | v2 | Variantes candidatas | Inclui? |
|---|---|---|---|---|
| `Tensão Barra Fases AB` | VAB | `TENSAO FASE AB` | `Barra`, `Fases` | Sim |
| `Distancia da Última Falta` | KMDF | `DISTANCIA DEFEITO` | `Última` | Sim (inclusivo) |
| `Temp.Óleo - Alarme` | TOLE | `TEMPERATURA OLEO` | `Temp.Óleo` (grafia), `Alarme` | Grafia não; Alarme sim |
| `Falha GOOSE (Falha Recepção IED Adjacente)` | FCOM | `FALHA COMUNICACAO IED` | `GOOSE`, `Recepção`, `Adjacente` | Sim (conceitos novos) |
| `Disj. 52-1 (01Q0) - Desligado` | DJF1 | `DJ` | `Disj.` (grafia), `Desligado` (infinitivo), `52-1` (ID), `01Q0` (ID) | Nenhum |
| `Chave 43TC Excluida` | 43TC | `43TC` | `Excluida` (infinitivo) | Não |
| `Potência Reativa` | Q | `POTENCIA REATIVA` | (nenhuma — já cobre) | — |

## Recipe de enriquecimento

Formato por linha, **append-only**:

```
<desc_v2 EXATA> — <variante_1>, <variante_2>[, ...]
```

Onde `<variante_N>` são tokens (palavras ou bigramas) extraídos das descrições
reais que:
1. **Não estão presentes** na desc_v2 (após tokenização + lowercase)
2. **Adicionam sentido semântico novo** (critério inclusivo)
3. **Não são infinitivos** (desligar, ligar, abrir, fechar, bloquear, desbloquear,
   incluir, excluir, atuar, disparar, resetar, etc.)
4. **Não são IDs de equipamento** (padrão `[A-Z0-9]{2,4}\d*`, ex: `01Q0`, `52-1`)
5. **Não são endereços** (padrão `\d+[./]\d+`, ex: `1.3`, `3/1`)
6. **Não são mera variação de grafia/maiúscula/acento** da desc_v2
   (ex: `OLEO` vs `Óleo` — mesma semântica)
7. **Não aparecem na desc_v2 de nenhuma outra sigla** (contra-checagem
   para evitar canibalização)

### Termos de estado (exceção)

Termos como `Alarme`, `Bloqueio`, `Ativo`, `Aberto`, `Fechado`, `Desligado`,
`Ligado`, `Trip`, `Energizado`, `Desenergizado` — **são incluídos** se não
estiverem na desc_v2, pois indicam contexto semântico (o sinal não é só a
grandeza, é a grandeza em estado de alarme/bloqueio).

**Exceção da exceção:** formas infinitivas (`Alarmar`, `Bloquear`, `Ativar`)
são excluídas como infinitivos.

## Pipeline de processamento (script único)

### Fase 1 — Minerar pares dos auditoria

`scripts/enriquecer_v6/gerar_v6.py`

```
Entrada: output/*/Auditoria_Revisao*.xlsx
         docs/Pontos Padrao ADMS_v2.xlsx

1. Ler todos os *Auditoria_Revisao*.xlsx
   - Para cada linha:
     - Se Status == "decidido" AND Score Final > 0:
         → par_confiavel[sigla].append(desc_bruta)
     - Se Status == "revisao" AND Candidato 1.score >= 0.30:
         → par_hipotetico[sigla_hipotese].append(desc_bruta)

2. Carregar docs/Pontos Padrao ADMS_v2.xlsx
   - Mapa sigla → desc_v2 (normalizada, lowercase)
   - Mapa sigla → {termos_v2} (conjunto de tokens)

Saída intermediária (para curadoria):
  - dict[sigla → [desc_bruta]]  (confiáveis)
  - dict[sigla → [desc_bruta]]  (hipotéticos)
```

### Fase 2 — Extrair e filtrar variantes

```
3. Para cada sigla com descrições (confiáveis + hipotéticos):
   a) Tokenizar cada desc_bruta (split em espaços/pontuação)
   b) Subtrair tokens já presentes em termos_v2
   c) Aplicar filtros (infinitivo, ID, endereço, grafia-only)
   d) Contra-checagem: token não está em termos_v2 de outra sigla
   e) Reter termos únicos + frequência de ocorrência
   f) Marcar se veio de par_hipotetico (confiança baixa)

Saída intermediária:
  - relatorio_variantes.csv (sigla, desc_v2, termos_propostos,
    freq, confianca_alta)
```

### Fase 3 — Gerar v6

```
4. Copiar docs/Pontos Padrao ADMS_v2.xlsx → v6.xlsx
5. Para cada sigla com termos aprovados:
   - Ordenar termos por frequência (decrescente)
   - desc_v6 = f"{desc_v2} — {', '.join(termos)}"
   - Atualizar célula DESCRIÇÃO NOVA
6. Preservar sheet estrutura, formatação, outras colunas (idêntico à v2)
```

### Fase 4 — Relatório de curadoria

```
7. Gerar docs/v6_variantes_propostas.csv
   Colunas: sigla, desc_v2, desc_v6, termos_novos, freq,
            origem (decidido/revisao), benchmark_impact
```

## Validação

### Benchmark (gate de regressão)

```powershell
$env:LISTA_BENCH="docs/Pontos Padrao ADMS_v6.xlsx"
$env:PYTHONPATH="src"
python bench/benchmark.py
```

**Critérios de aceitação:**
- acc@1 >= 82% (v2 baseline)
- prec@dec >= 95% (v2 baseline)
- Se um dos dois cair, rejeitar v6 e revisar as variantes adicionadas

### Validação complementar (se benchmark OK)

Rodar pipeline completo com v6 nos mesmos inputs dos auditoria e medir:

```
Queda esperada em revisão: ~5-15% (sinais que iam pra revisão por
falta de termo na descrição v2 passam a ser decididos)
```

### Revisão humana

O `v6_variantes_propostas.csv` permite revisão rápida:
- Filtrar por `confianca=baixa` (pares hipotéticos) para decisão caso a caso
- Filtrar por siglas com muitas variantes (possível ruído)
- Verificar se alguma variante aparece em múltiplas siglas (contra-checagem
  falhou — remover manualmente)

## Switch de default (só após validação)

Trocar para v6 em:
- `src/tdt/defaults.py` (`DEFAULT_LISTA`)
- `src/tdt/cli.py` (`--lista-padrao` default)
- `tests/test_ui_defaults.py`
- `docs/AGENTS.md` (linha de fontes de verdade)

## Não-objetivos

- **Não mexer em siglas, linhas, outras colunas, ou outras sheets.**
- **Não editar v1/v2/v3/v4/v5** (histórico).
- **Não ampliar ground-truth do benchmark** (esforço separado).
- **Não mexer no canonizador/scorers/config.**
- **Não resolver infinitivos como variantes** (later fix, problema separado).
- **Não incluir contexto de equipamento** (só variantes diretas por sigla).

## Riscos

| Risco | Mitigação |
|-------|-----------|
| **Overfitting nos inputs de auditoria**: v6 melhora nesses inputs mas regride em outros | Benchmark contra ground-truth curado (28 pares) pega regressão. Se passar, confiável. |
| **Termos muito específicos de uma SE**: `GOOSE` pode ser específico de Gravataí | Incluir mesmo assim (é termo de protocolo, não de SE). Monitorar em futuros inputs. |
| **Contra-checagem muito agressiva**: termo novo que existe em outra desc_v2 é barrado, mesmo sendo útil | Relatório de curadoria permite revisão manual dos casos barrados. |
| **Pares hipotéticos (revisão) contaminam**: Candidato 1 pode estar errado | Marcar como confiança baixa, segregar no relatório, revisão humana obrigatória. |
| **Benchmark fraco (28 pares)**: pega regressão grosseira, não melhoria fina | Assumido. A melhoria fina se verifica na queda de revisão ao rodar pipeline completo. |

## Artefatos de saída

- `docs/Pontos Padrao ADMS_v6.xlsx` — cópia da v2 com `DESCRIÇÃO NOVA`
  enriquecida (append-only). Todo o resto idêntico à v2.
- `docs/v6_variantes_propostas.csv` — diff antes/depois + termos adicionados
  para curadoria.
- `scripts/enriquecer_v6/gerar_v6.py` — script único que faz tudo (minerar,
  filtrar, gerar, relatório).

## Decomposição em tarefas (para o plano)

1. **Script `gerar_v6.py`** — leitura dos auditoria, extração de pares,
   diff contra v2, filtros, contra-checagem, geração v6.xlsx, relatório CSV.
2. **Benchmark v6 vs v2** — validar não regressão.
3. **Curadoria** — revisar `v6_variantes_propostas.csv`, ajustar se necessário.
4. **Pipeline completo** — rodar com v6, medir queda em revisão.
5. **Switch de default** (se validado).

---

## Atualização 2026-06-28 (após melhorias do motor de regras)

Fecha a spec com o aprendizado de rodar o pipeline corrigido na
`input_nao_homogeneo_1` (GTA, 2.372 sinais) + decisão do brainstorm.

### Decisão travada — fonte (revisa "Decisões travadas")

- **Fonte = auditoria existente, SÓ sinais `decidido`.** Descartar os pares
  hipotéticos (status `revisao`, Candidato 1 ≥ 0.30) nesta primeira iteração —
  o ruído de herdar sigla errada supera o ganho. Reavaliar depois.
- Os `output/*/Auditoria_Revisao*.xlsx` vieram do pipeline **antigo** (decidia
  genérico `79` onde hoje é `79LO`, `DJA1` falso). Como usamos só `decidido` e
  só **adicionamos termos à descrição da sigla já escolhida**, herdar a sigla é
  aceitável — mas curadoria deve excluir siglas espúrias (ex.: `DJA1`, que não
  existe na TDT real da GTD).

### Foco redefinido — v6 ataca o "catch-all"

O motor de regras já resolve a especificidade de **famílias ANSI numeradas**
(`filtro_preciso.filtrar_especificidade`: `79 Bloqueado`→`79LO`, `81 Estágio 1`
→`81E1`). A v6 **não** precisa mirar esses casos.

O alvo da v6 são as **siglas catch-all NÃO-numeradas** (`PRTF`, `FCMR`, `MTRF`,
`SECC`, `CMD`) que absorvem muitos sinais distintos no mesmo módulo — causa
dominante de `endereco_duplicado` e `pareamento_ambiguo` na medição real. A
descrição v2 dessas siglas é genérica demais; a v6 dá os termos discriminadores
reais (por-sigla, sem canibalizar) para o scorer **surfar a sigla específica
certa**, complementando o motor de regras (que só reordena o que foi surfado).

### Validação — usar o GT da SP-GT

A `SP-GT` (~756 + variações reais) é a régua correta para o gate da v6.
**Dependência nova:** validar contra o GT expandido, não os 28 pares. Gate
inalterado: acc@1 ≥ 82%, prec@dec ≥ 95%.

### Ordem recomendada

SP-GT (régua) → v6 (enriquecimento) → SP-Decision (re-tunar thresholds).
