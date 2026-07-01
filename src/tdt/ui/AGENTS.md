# AGENTS.md — src/tdt/ui (SP4 UI Desktop)

## Purpose
Interface gráfica PySide6 para configurar, executar e revisar o pipeline SP1. Input `.xlsx` → revisão interativa → `TDT.xlsx`.

## Ownership
- `app.py`: `MainWindow(QMainWindow)` — empacota QStackedWidget + QTabBar; navega Inicial (tab 0), Revisão (tab 1); Config abre via botão ⚙ (não é tab).
- `tela_inicial.py`: `TelaInicial(QWidget)` — seleção de arquivos (input, template, lista, output), botão executar, barra de progresso.
- `tela_revisao.py`: `TelaRevisao(QWidget)` — tabela de revisão com `ProxyRevisao` + `DelegateSinal` + `ModeloSinais`; filtro global + filtro por coluna; menu de módulo.
- `tela_config.py`: `TelaConfig(QWidget)` — knobs de configuração do pipeline (Config paths).
- `tela_analise.py`: `TelaAnalise(QWidget)` — análise de qualidade do matching pós-pipeline.
- `estado.py`: `AppState` — estado mutável compartilhado entre telas (Config, ResultadoPipeline, ListaPadraoADMS, motivo revisão). `_editar_nested` + 7 setters (`definir_tipo/fase/nivel_tensao/barra/tipo_equip/modulo/escala`) editam campos aninhados de `SignalRecord` via `dataclasses.replace`.
- `worker.py`: `PipelineWorker(QThread)` — isola o pipeline em QThread; cancelamento cooperativo via flag.
- `modelo_tabela.py`: `ModeloSinais(QAbstractTableModel)` — tabela de revisão (colunas: Módulo, End., Sigla, Decisão, etc.). `flags()`/`setData()` habilitam edição em 8 colunas (Sinal + 7 campos de domínio), dispatchando pros setters do `AppState`.
- `modelo_analise.py`: `ModeloAnalise(QAbstractTableModel)` — tabela de análise de qualidade.
- `proxy_revisao.py`: `ProxyRevisao(QSortFilterProxyModel)` — filtra por coluna individual (AND com filtro global) + esconder decididos.
- `delegate_sinal.py`: `DelegateSinal(QStyledItemDelegate)` — editor combo da coluna Sinal (candidatos + busca ADMS). `DelegateCombo` — combo de opções fixas p/ colunas de domínio fechado (Tipo/Fase/Nível Tensão/Barra/Tipo Equip.). `DelegateModulo` — combo editável p/ Módulo, sugere nomes já presentes nos registros. Os 3 implementam `setEditorData` (pré-seleciona o valor atual da célula ao abrir; `_preselecionar` mapeia o sentinela de exibição "—" pra opção vazia "").
- `busca_adms.py`: busca textual na lista padrão ADMS.
- `exportar_analise.py`: exporta relatório de análise para `.xlsx`.
- `config_io.py`: carrega/salva configuração do pipeline (JSON+paths).
- `tema.qss`: folha de estilos.
- `app.py` + `ui_main.py`: entry-point da UI.

## Local Contracts
- AppState é mutável e compartilhado entre telas via referência. `motivo_por_id()` devolve motivo de revisão por id do SignalRecord.
- Campos editáveis na tabela de revisão: Sinal, Tipo, Fase, Nível Tensão, Barra, Tipo Equip., Módulo, Escala. Editar qualquer um dos 7 campos de domínio NÃO promove `status` pra `"decidido"` (só editar Sinal promove); nenhum snapshot de undo é criado (mesma lacuna do `definir_sigla`). Editar Tipo Equip. grava `equipamento_inferido=False`; editar Tipo grava `categoria_confiavel=True`. Domínio fechado de Tipo exclui `DiscreteAnalog` (placeholder de incerteza do dual-pass, não é estado-alvo de edição manual). Ver spec `docs/superpowers/specs/2026-07-01-sp-campos-editaveis-revisao-design.md`.
- PipelineWorker usa `pyqtSignal` para progresso (int), log (str), resultado (ResultadoPipeline) e erro (str). Cancela via `_cancelado` flag com cooperativa.
- `ProxyRevisao` herda `QSortFilterProxyModel`; filtra por coluna individual (`set_filtro_coluna(col_index, texto)`) em AND com filtro global; `esconder_decididos` remove linhas com `decisao!="revisar"`.
- Navegação: QStackedWidget com QTabBar (2 abas: Inicial, Revisão); Config é popup/QWidget avulso, não tab.

## Work Guidance
- Testes com pytest-qt. Fake/pipeline mock injectado via AppState. Não precisa de modelo real.
- Tema QSS em `tema.qss` — não colocar style inline.

## Verification
`PYTHONPATH=src python -m pytest -q tests/test_ui_*.py`; `PYTHONPATH=src python -m tdt.ui_main` (abre a janela).
