# AGENTS.md — src/tdt (SP1 backbone + SP4 UI)

## Purpose
Implementação do SP1 (pipeline) + SP4 (UI Desktop PySide6): input `.xlsx` → ListaHomogenea → `TDT.xlsx` (DNP3), com interface gráfica para configuração, execução e revisão.

## Ownership
Pipeline: `pipeline.py` é o único orquestrador (conhece todos os módulos); os demais só conhecem `contracts.py`.
Módulos: `normalizador.py` (N0 extração estrutural + N1-N5 canonização), `tokenizer.py`, `vocabulario_tipo.py`, `defaults.py`; entrada via `cli.py`; relatório pós-pipeline via `relatorio_revisao.py`. `estruturador_homogeneo.py` (caminho determinístico p/ sheet homogênea com cabeçalho fixo) e `pareamento_polaridade.py` (força convergência ligado/desligado pra sigla de posição, ex. DJF1) rodam antes do scoring — ambos com fallback/flag pro caminho heurístico de hoje.
UI: telas em `ui/` compartilham `AppState` mutável; `PipelineWorker` isola o pipeline em QThread.

## Local Contracts
- Tipos compartilhados em `contracts.py` (imutáveis; enriquecer com `dataclasses.replace`, sem mutação).
- Knobs calibráveis só em `config.py`.
- Fluxo pipeline: `identificador → [se rota.homogeneo e cabeçalho fixo bate: estruturador_homogeneo (lê SIGLA SINAL/MÓDULO/EQUIPAMENTO/TIPO/INDEX DNP3 direto das colunas, valida sigla na Lista Padrão, decide sem scoring; sigla vazia/inválida cai no caminho de baixo) senão: analise_colunas → estruturador] (extrair_contexto_estrutural/N0 → Eletrico.{fase,equipamento_alvo,nome_equipamento,barra}; canonizar/N1-N5 p/ normalizar descrições) → pareamento_polaridade (força par ligado/desligado pra sigla de posição, ex. DJF1, antes do scoring; configurável via `Config.parear_polaridade_equipamento`) → (tfidf+vetorial+fuzzy → mescla → motor_regras → roteador) → dc_pairer → normalizador_estrutural → criador_lista_homogenea → engine_tdt`. Sinal sem endereço é classificado (sigla sugerida) mas nunca decidido/auto-aprovado — vai pra revisão com `motivo="sem_endereco"`. `auditoria` injetada para logs de revisão e streaming para UI. `normalizador.py` (N0 + N1..N5 + tokenizer) consumido por `estruturador`/`estruturador_homogeneo` (N0+canonizar) e scorers (só canonizar, lista padrão não tem ID de equipamento embutido). `normalizador.FASES` é público (consumido também por `engine_tdt` pros dropdowns de Phases).
- `pipeline.executar` aceita `aliases: dict[str, str] | None` para renomear módulos por sheet.
- `engine_tdt`: carrega o template e escreve nele (preserva fórmulas/estilos/tabelas/validações); colunas por display name (row 4); valida 43 colunas. Output Coordinates de comando simples (1 índice) sempre duplica (`N;N`) — double-bit real (2 índices) não passa por esse caminho. Dropdowns (Data Validation) criados em código pra Phases/Direction/Remote Point Type (`_DV_LISTAS`); `Side` fica de fora (sem domínio confirmado).
- `analise_colunas`: detecção por CONTEÚDO (header por densidade-do-topo; descrição por embedding×diversidade×comprimento; índice sequencial; tipo por vocabulário). Módulo NÃO é detectado por coluna (vem do nome da sheet) — só no caminho heurístico; `estruturador_homogeneo` lê módulo/equipamento/tipo das colunas quando o cabeçalho fixo bate.
- UI: QStackedWidget (Inicial/Revisão/Config) navegado também por `QTabBar` (Inicial/Revisão; Config só pelo botão ⚙). AppState mutável compartilhado, incl. `motivo_por_id()` (id→motivo de revisão, exibido na coluna "Motivo" da tabela). PipelineWorker em QThread com cancelamento cooperativo. Tema QSS em `ui/tema.qss`. `ProxyRevisao` filtra por coluna individual (AND com filtro global) além de "esconder decididos".

## Work Guidance
- TDD sempre (ver `tests/`). Marcar simplificações com `# ponytail:` e o teto/upgrade.
- Mudança de método de matching: adicionar candidato, não apagar original; validar em `bench/`.

## Verification
`python -m pytest -q tests/` (raiz); `PYTHONPATH=src python -c "import tdt.pipeline"`; UI: `PYTHONPATH=src python -m tdt.ui_main`.

## Child DOX Index
- `scoring/AGENTS.md` — scorers (tfidf, vetorial, mescla).
- `matchers/AGENTS.md` — métodos alternativos benchmarkáveis (fuzzy, cross_encoder).
- `dados/AGENTS.md` — serviços de dados (lista padrão, índice vetorial, encoder).
- `ui/` — telas PySide6 (TelaInicial, TelaConfig, TelaRevisao), AppState, PipelineWorker, ModeloSinais, config_io, tema.qss, app.py e ui_main.py.
