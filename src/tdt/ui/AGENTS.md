# AGENTS.md — src/tdt/ui (SP4 UI Desktop)

## Purpose
Interface gráfica PySide6 para configurar, executar e revisar o pipeline SP1. Input `.xlsx` → revisão interativa → `TDT.xlsx`.

## Ownership
- `app.py`: `MainWindow(QMainWindow)` — empacota QStackedWidget + QTabBar; navega Inicial (tab 0), Revisão (tab 1); Config abre via botão ⚙ (não é tab).
- `tela_inicial.py`: `TelaInicial(QWidget)` — seleção de arquivos (input, template, lista, output), botão executar, barra de progresso.
- `tela_revisao.py`: `TelaRevisao(QWidget)` — tabela de revisão com `ProxyRevisao` + `DelegateSinal` + `ModeloSinais`; filtro global + filtro por coluna; menu de módulo.
- `tela_config.py`: `TelaConfig(QWidget)` — knobs de configuração do pipeline (Config paths).
- `tela_analise.py`: `TelaAnalise(QWidget)` — análise de qualidade do matching pós-pipeline.
- `estado.py`: `AppState` — estado mutável compartilhado entre telas (Config, ResultadoPipeline, ListaPadraoADMS, motivo revisão).
- `worker.py`: `PipelineWorker(QThread)` — isola o pipeline em QThread; cancelamento cooperativo via flag.
- `modelo_tabela.py`: `ModeloSinais(QAbstractTableModel)` — tabela de revisão (colunas: Módulo, End., Sigla, Decisão, etc.).
- `modelo_analise.py`: `ModeloAnalise(QAbstractTableModel)` — tabela de análise de qualidade.
- `proxy_revisao.py`: `ProxyRevisao(QSortFilterProxyModel)` — filtra por coluna individual (AND com filtro global) + esconder decididos.
- `delegate_sinal.py`: `DelegateSinal(QStyledItemDelegate)` — custom rendering (cores por score, checkbox, busca ADMS).
- `busca_adms.py`: busca textual na lista padrão ADMS.
- `exportar_analise.py`: exporta relatório de análise para `.xlsx`.
- `config_io.py`: carrega/salva configuração do pipeline (JSON+paths).
- `tema.qss`: folha de estilos.
- `app.py` + `ui_main.py`: entry-point da UI.

## Local Contracts
- AppState é mutável e compartilhado entre telas via referência. `motivo_por_id()` devolve motivo de revisão por id do SignalRecord.
- PipelineWorker usa `pyqtSignal` para progresso (int), log (str), resultado (ResultadoPipeline) e erro (str). Cancela via `_cancelado` flag com cooperativa.
- `ProxyRevisao` herda `QSortFilterProxyModel`; filtra por coluna individual (`set_filtro_coluna(col_index, texto)`) em AND com filtro global; `esconder_decididos` remove linhas com `decisao!="revisar"`.
- Navegação: QStackedWidget com QTabBar (2 abas: Inicial, Revisão); Config é popup/QWidget avulso, não tab.

## Work Guidance
- Testes com pytest-qt. Fake/pipeline mock injectado via AppState. Não precisa de modelo real.
- Tema QSS em `tema.qss` — não colocar style inline.

## Verification
`PYTHONPATH=src python -m pytest -q tests/test_ui_*.py`; `PYTHONPATH=src python -m tdt.ui_main` (abre a janela).
