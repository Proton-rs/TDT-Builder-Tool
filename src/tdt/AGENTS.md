# AGENTS.md — src/tdt (SP1 backbone + SP4 UI + SP-Ancoragem + SP-Pareamento)

## Purpose
Implementação do SP1 (pipeline) + SP4 (UI Desktop PySide6) + módulos de domínio posteriores: input `.xlsx` → ListaHomogenea → `TDT.xlsx` (DNP3), com interface gráfica para configuração, execução e revisão.

## Ownership
Pipeline: `pipeline.py` é o único orquestrador (conhece todos os módulos); os demais só conhecem `contracts.py`.
Módulos: `normalizador.py` (N0 extração estrutural + N1-N5 canonização), `tokenizer.py`, `vocabulario_tipo.py`, `defaults.py`; entrada via `cli.py`; relatório pós-pipeline via `relatorio_revisao.py`. `estruturador_homogeneo.py` (caminho determinístico p/ sheet homogênea com cabeçalho fixo), `identidade_modulo.py` (resolução do nome real do módulo + classificação de `Modulo.tipo`; determinístico, tabelas de `config.py`) e `pareamento_polaridade.py` (força convergência aberto/fechado pra sigla de posição: DJF1/DJA1 para Disjuntor, SECB/SECC/SECF/SECG/SECI/SECL/SECT para Seccionadora por palavra-função; sem keyword → `posicao_ambigua`; retorna `tuple[list, list[ItemRevisao]]`) rodam antes do scoring. `ancoragem_sigla.py` (injeta sigla literal da descrição como candidato de alta confiança; `filtrar_subarvore` restringe expansão ao sub-ramo da âncora) roda dentro de `_classificar_sinal`, entre `ancorar` e `filtrar_preciso`.
UI: telas em `ui/` compartilham `AppState` mutável; `PipelineWorker` isola o pipeline em QThread.

## Local Contracts
- Tipos compartilhados em `contracts.py` (imutáveis; enriquecer com `dataclasses.replace`, sem mutação).
- Knobs calibráveis só em `config.py`.
- Fluxo pipeline: `identificador → [se rota.homogeneo e cabeçalho fixo bate: estruturador_homogeneo (lê SIGLA SINAL/MÓDULO/EQUIPAMENTO/TIPO/INDEX DNP3 direto das colunas, valida sigla na Lista Padrão, decide sem scoring; sigla vazia/inválida cai no caminho de baixo) senão: analise_colunas → estruturador] (extrair_contexto_estrutural/N0 → Eletrico.{fase,equipamento_alvo,nome_equipamento,barra}; canonizar/N1-N5 p/ normalizar descrições) → identidade_modulo → pareamento_polaridade (par aberto/fechado → sigla posição DJF1/DJA1/SEC*; sem keyword → posicao_ambigua; retorna sinais+revisão) → [_classificar_sinal: tfidf+vetorial+fuzzy → mescla → ancoragem_sigla.ancorar → expansao_candidatos → ancoragem_sigla.filtrar_subarvore → filtro_preciso → motor_regras] → roteador → dc_pairer → normalizador_estrutural → criador_lista_homogenea → engine_tdt`. Sinal sem endereço é classificado (sigla sugerida) mas nunca decidido/auto-aprovado — vai pra revisão com `motivo="sem_endereco"`. `auditoria` injetada para logs de revisão e streaming para UI. `normalizador.py` (N0 + N1..N5 + tokenizer) consumido por `estruturador`/`estruturador_homogeneo` (N0+canonizar) e scorers (só canonizar, lista padrão não tem ID de equipamento embutido). `normalizador.FASES` é público (consumido também por `engine_tdt` pros dropdowns de Phases).
- `pipeline.executar` aceita `sheets: list[str] | None` (whitelist de sheets a processar, filtrando `rota.sheets_dados`; `None` = todas as sheets que a heurística de `identificador.classificar` decidir) e `aliases: dict[str, str] | None` (sheet original → apelido, mesma chave que `AppState.aliases`; aplicado dentro do loop por sheet logo após `identidade_modulo.aplicar_identidade`, sobrescrevendo `modulo.nome` de todo sinal com `origem_contexto == "sheet_name"` — `SignalRecord.id` não muda, continua estável como `sheet:linha`). Isso é distinto de `_aplicar_aliases`/`gerar_tdt` (chamado só pelo export da tela de Revisão), que casa `aliases` contra o `modulo.nome` já resolvido, não o nome bruto da sheet — os dois caminhos coexistem e não devem ser confundidos.
- `engine_tdt`: carrega o template e escreve nele (preserva fórmulas/estilos/tabelas/validações); colunas por display name (row 4); valida 43 colunas. Output Coordinates de comando simples (1 índice) sempre duplica (`N;N`) — double-bit real (2 índices) não passa por esse caminho. Dropdowns (Data Validation) criados em código pra Phases/Direction/Remote Point Type (`_DV_LISTAS`); `Side` fica de fora (sem domínio confirmado).
- `analise_colunas`: detecção por CONTEÚDO (header por densidade-do-topo; descrição por embedding×diversidade×comprimento; índice sequencial; tipo por vocabulário). Módulo NÃO é detectado por coluna (vem do nome da sheet) — só no caminho heurístico; `estruturador_homogeneo` lê módulo/equipamento/tipo das colunas quando o cabeçalho fixo bate.
- UI: QStackedWidget (Inicial/Revisão/Config) navegado também por `QTabBar` (Inicial/Revisão; Config só pelo botão ⚙). AppState mutável compartilhado, incl. `motivo_por_id()` (id→motivo de revisão, exibido na coluna "Motivo" da tabela). PipelineWorker em QThread com cancelamento cooperativo. Tema QSS em `ui/tema.qss`. `ProxyRevisao` filtra por coluna individual (AND com filtro global) além de "esconder decididos".

## Work Guidance
- TDD sempre (ver `tests/`). Marcar simplificações com `# ponytail:` e o teto/upgrade.
- Mudança de método de matching: adicionar candidato, não apagar original; validar em `bench/`.

## Verification
`python -m pytest -q tests/` (raiz); `PYTHONPATH=src python -c "import tdt.pipeline"`; UI: `PYTHONPATH=src python -m tdt.ui_main`.

## Child DOX Index
- `normalizacao/AGENTS.md` — normalização N0..N5, tokenizer, vocabulário, estruturadores.
- `analise/AGENTS.md` — análise de colunas por conteúdo, identificação de rota.
- `scoring/AGENTS.md` — scorers (tfidf, vetorial, mescla).
- `matchers/AGENTS.md` — métodos alternativos benchmarkáveis (fuzzy, cross_encoder).
- `dados/AGENTS.md` — serviços de dados (lista padrão, índice vetorial, encoder).
- `ui/AGENTS.md` — telas PySide6 (TelaInicial, TelaConfig, TelaRevisao, TelaAnalise), AppState, PipelineWorker, modelos, proxy, delegate.
