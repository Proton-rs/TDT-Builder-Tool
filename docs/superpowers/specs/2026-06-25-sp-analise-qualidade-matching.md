# SP-ANALISE: Análise de Qualidade do Matching

## 1. Visão Geral

Adicionar uma tela de **Análise** na UI (4ª tela, acessível via QTabBar junto com Inicial/Revisão) que exibe:

- Tabela de qualidade por sinal (score breakdown por método)
- Painel de estatísticas agregadas
- Botão de exportar relatório (.xlsx)

## 2. Pré-requisito: Diagnostico Disponível

O `Diagnostico` já é coletado quando `diagnostico=True` (worker.py:55). Cada `SignalRecord.diagnostico` contém:

```python
@dataclass
class Diagnostico:
    scores_por_metodo: dict[str, dict[str, float]]
    # ex: {"DJF1": {"tfidf": 0.82, "vetorial": 0.79, "fuzzy": 0.88, "final": 0.83}}
```

O gap (diferença entre 1º e 2º candidato) é calculável `_gap()` em pipeline.py.

## 3. Tabela de Qualidade (por sinal)

Nova aba "Análise" com `QTableView` exibindo:

| Coluna | Fonte |
|--------|-------|
| Sinal ID | `rec.id` |
| Descrição | `rec.descricoes.bruta` |
| Sigla Decidida | `rec.sigla_sinal` |
| Status | `rec.status` ("decidido", "revisão") |
| Score TF-IDF | `diag.scores_por_metodo[sigla]["tfidf"]` |
| Score Vetorial | `diag.scores_por_metodo[sigla]["vetorial"]` |
| Score Fuzzy | `diag.scores_por_metodo[sigla]["fuzzy"]"` |
| Score Final | `rec.candidatos[0].score` (se houver) |
| Gap | `_gap(rec)` |
| Motivo Revisão | `ItemRevisao.motivo` ou vazio |
| Consenso | qtd métodos que concordam no top-1 |

### Implementação
- `modelo_analise.py`: `QAbstractTableModel` sobre `list[SignalRecord]` + `dict[str, ItemRevisao]`
- `proxy_analise.py`: `QSortFilterProxyModel` ordenável por coluna
- `tela_analise.py`: `QWidget` com `QTableView` + filtro de status (combo: "Todos", "Decididos", "Revisão")

## 4. Painel de Estatísticas

Acima da tabela, cards informativos:

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│  Total       │  Decididos   │  Revisão     │  Taxa Decisão │
│  554         │  415         │  139         │  74.9%        │
├──────────────┼──────────────┼──────────────┼──────────────┤
│  Score Médio │  Gap Médio   │  SEM ENDEREÇO│  CATEGORIA AMB│
│  0.81        │  0.12        │  23          │  5            │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

### Motivos de revisão (gráfico de barras simples ou lista numerada)
Usar `QGroupBox` com `QLabel`s para cada motivo + contagem.

## 5. Relatório Exportável

Botão "Exportar Relatório" → salva `.xlsx` (baseado em template ou openpyxl direto) com:

**Sheet 1 — Qualidade por Sinal**: mesma estrutura da tabela, com todas as colunas
**Sheet 2 — Estatísticas Agregadas**: contagens, médias, distribuição de status

Diferente da TDT (que segue template ADMS), este relatório é livre — só openpyxl direto, sem template.

## 6. Integração na UI

- `app.py`: adicionar `TelaAnalise` ao `QStackedWidget`
- `QTabBar` passa a mostrar: Inicial | Revisão | Análise
- Estado compartilhado via `AppState`: `AppState.resultado` contém `ResultadoPipeline` com `lista` + `revisao`
- Ao final do pipeline, `terminado` signal popula a tela de análise automaticamente

## 7. Não Fazer

- Gráficos interativos (matplotlib/QtCharts) — só labels numéricos por ora
- Drill-down por sinal na análise (clica no sinal e vai pra revisão) — pode ser adicionado depois
- Cache de análise entre execuções — sempre recalcula do resultado atual
