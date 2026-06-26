# SP F — Análise comparativa: scores normalizados vs. brutos + correções na análise

**Data:** 2026-06-26
**Status:** Rascunho
**Origem:** análise detalhada dos outputs `norma-probabilistica/` (scores normalizados via minmax) vs `LISTA 1 - GTA/` (scores brutos, sem calibração) + 10 pontos de melhoria levantados pelo usuário.

---

## 0. Comparação: scores normalizados (minmax) vs. scores brutos

### Benchmark atual

| Configuração | acc@1 | rec@3 | decid | prec@dec |
|---|---|---|---|---|
| tfidf+vet+fuzzy (BRUTO) | 82% | 86% | 75% | **95%** |
| combo(calib-minmax) | 79% | 86% | **93%** | 85% |
| combo(calib-temp) | 82% | 89% | 71% | 95% |
| combo+regras | 82% | 86% | 75% | 95% |
| combo+consenso | 82% | — | 93% | 42% |

### Observações diretas dos outputs

**`norma-probabilistica/` (calib-minmax):** Scores em [0, 1], decid=93%. Prec@dec=85% — mais FP. Ex: `Secc. 89-8 → PB` (score=0.525, FP).

**`LISTA 1 - GTA/` (bruto):** Scores somados crus (1.029, 1.760, etc.), decid=75%, prec@dec=95%.

### Diagnóstico

O minmax comprime cada distribuição por-método para [0,1] independentemente, inflando scores de candidatos fracos. Aumenta taxa de decisão mas reduz precisão.

**Decisão:** normalizados + filtros de correção (F1-F8). Scores brutos mantidos como fallback.

---

## 1. Motor de regras como filtro + expansão de candidatos com childs (F1)

**Problema:** `81U5` não está entre os candidatos. Motor de regras não pode boostar sigla que não existe na lista.

**Solução:** expandir candidatos por prefixo (pós-scorers, pré-regras). Ex: `81` → incluir `81E1`, `81E2`, `81SU`, `81_T`, `81U1`, `81U5`. Candidatos expandidos herdam score do pai (ou 0). Motor de regras aplica boost por tokens de estágio.

Novo módulo `src/tdt/expansao_candidatos.py`.

---

## 2. Expansão de abreviações no embedding (F2)

**Problema:** Descrição na lista padrão genérica demais (`"81 - RELE DE FREQUENCIA"`). Input contém "SUB-FREQUENCIA ESTAGIO 5". Embedding não casa.

**Solução:** enriquecimento seletivo da lista padrão v6 expandir abreviações no input.

---

## 3. Stemming/lematização para português (F3)

**Problema:** "DESLIGAMENTO" vs "DESLIGAR" — tokens diferentes diluem match.

**Solução:** N6 — stemming (snowballstemmer ou RSLP). Preservar siglas. Gateado por config. Aplicar em input e lista padrão.

---

## 4. DJA1 e PB como falso positivo (F4)

**Problema:** Sinais de disjuntor (alarmes) classificados como DJA1. Seccionadoras classificadas como PB.

**Solução:**
- Se `equipamento_alvo="Disjuntor"` e texto sem posição → penalizar DJA1
- Se `equipamento_alvo="Seccionadora"` e candidato contém PB → penalidade -0.3

---

## 5. Caracteres especiais `()` `/` `-` no embedding (F5)

**Problema:** `81(U/O)` → `81 U O`, perde agrupamento.

**Solução:** N0.5 — `_preservar_siglas_especiais`. `digito(Letras/Letras)` → `digitoLetras`. Só depois colapsar separadores.

---

## 6. Bypass de módulo_indefinido (F0)

**Problema:** 1129/2417 sinais (46.7%) bloqueados sem classificação.

**Solução:** dual-pass — classificar mesmo sem módulo, com `categoria_confiavel=False`. Marcar para revisão em vez de pendente.

---

## 7. Erro de descrição (input data)

**Problema:** "desligamento local" deveria ser "religamento local".

**Solução:** corrigir na planilha de input. Pipeline não é verificador de qualidade.

---

## 8. Colunas Endereço Input/Output no TDT (F7)

**Problema:** Colunas address ausentes no TDT.

**Solução:** verificar display names no template e garantir correspondência em `_mapa_colunas`. Log de aviso se coluna não encontrada.

---

## 9. Resumo das correções prioritárias

| Prioridade | Feature | Problema |
|---|---|---|
| P0 | F7 | Colunas address ausentes no TDT |
| P0 | F0 | módulo_indefinido bloqueia 46% |
| P1 | F4a/b | DJA1 + PB falso positivo |
| P1 | F1 | Candidatos sem childs (81U5, etc.) |
| P2 | F5 | Caracteres especiais quebram match |
| P2 | F2 | Descrições enriquecidas lista padrão |
| P2 | F3 | Stemming/lematização |
| P3 | F8 | Auditoria lista padrão |
