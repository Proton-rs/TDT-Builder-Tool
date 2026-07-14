# AGENTS.md — src/tdt (SP1 backbone + SP4 UI + SP-Ancoragem + SP-Pareamento)

## Purpose
Implementação do SP1 (pipeline) + SP4 (UI Desktop PySide6) + módulos de domínio posteriores: input `.xlsx` → ListaHomogenea → `TDT.xlsx` (DNP3), com interface gráfica para configuração, execução e revisão.

## Ownership
Pipeline: `pipeline.py` é o único orquestrador (conhece todos os módulos); os demais só conhecem `contracts.py`.
Módulos: `normalizador.py` (N0 extração estrutural + N1-N5 canonização), `tokenizer.py`, `vocabulario_tipo.py`, `defaults.py` (`DEFAULT_LISTA` = `Pontos Padrao ADMS_v8.xlsx`, corrige MM de `43LR`/`81U1`-`81U5` vs v7; `DEFAULT_LISTA_ALIAS` segue v1); entrada via `cli.py`; relatório pós-pipeline via `relatorio_revisao.py`. `estruturador_homogeneo.py` (caminho determinístico p/ sheet homogênea com cabeçalho fixo; `estruturar_homogeneo()` retorna 4-tupla `(decididos, pendentes, revisao, avisos)` — usa `normalizacao.identidade_homogenea.resolver()` p/ nome de módulo/equipamento por bloco de cabeçalho; COMTAP e demais siglas de `config.siglas_sem_ponto` roteiam pra `revisao` (motivo `comando_tap_nao_modelado`) em vez de virar sinal; tipo `A/D` → `DiscreteAnalog`/`Input`), `identidade_modulo.py` (resolução do nome real do módulo + classificação de `Modulo.tipo`; determinístico, tabelas de `config.py`; `aplicar_identidade` retorna 3-tupla `(sinais, confianca, avisos)` — `avisos` sinaliza divergência sheet×conteúdo, ex. módulo rotulado errado na origem) e `pareamento_polaridade.py` (força convergência aberto/fechado pra sigla de posição: DJF1/DJA1 para Disjuntor, SECB/SECC/SECF/SECG/SECI/SECL/SECT para Seccionadora por palavra-função; sem keyword → `posicao_ambigua`; retorna `tuple[list, list[ItemRevisao]]`) rodam antes do scoring. `ancoragem_sigla.py` (injeta sigla literal da descrição como candidato de alta confiança; `filtrar_subarvore` restringe expansão ao sub-ramo da âncora) roda dentro de `_classificar_sinal`, entre `ancorar` e `filtrar_preciso`.
UI: telas em `ui/` compartilham `AppState` mutável; `PipelineWorker` isola o pipeline em QThread.

## Local Contracts
- Tipos compartilhados em `contracts.py` (imutáveis; enriquecer com `dataclasses.replace`, sem mutação).
- Knobs calibráveis só em `config.py`.
- Fluxo pipeline: `identificador → [se rota.homogeneo e cabeçalho fixo bate: estruturador_homogeneo (lê SIGLA SINAL/MÓDULO/EQUIPAMENTO/TIPO/INDEX DNP3 direto das colunas, valida sigla na Lista Padrão, decide sem scoring; sigla vazia/inválida cai no caminho de baixo) senão: analise_colunas → estruturador] (extrair_contexto_estrutural/N0 → Eletrico.{fase,equipamento_alvo,nome_equipamento,barra}; canonizar/N1-N5 p/ normalizar descrições) → identidade_modulo → pareamento_polaridade (par aberto/fechado → sigla posição DJF1/DJA1/SEC*; sem keyword → posicao_ambigua; retorna sinais+revisão) → [_classificar_sinal: tfidf+vetorial+fuzzy → mescla → ancoragem_sigla.ancorar → expansao_candidatos → ancoragem_sigla.filtrar_subarvore → filtro_preciso → motor_regras] → roteador → normalizador_estrutural.fundir_pares_posicao (funde par de posição em MultiCoord ANTES do dc_pairer, resolve caso "par + comando") → dc_pairer → normalizador_estrutural → criador_lista_homogenea → engine_tdt.particionar_custom_id_duplicado (gate: grupos de registros com o mesmo Remote Point Custom ID — nome hierárquico + remote unit — saem TODOS da lista e vão pra `revisao` com motivo `custom_id_duplicado`; nunca saem calados no xlsx) → engine_tdt.particionar_endereco_duplicado (gate: grupos com endereço duplicado ESCOPADO POR MÓDULO, não workbook-wide, saem pra `revisao`) → engine_tdt.gerar`. Sinal sem endereço é classificado (sigla sugerida) mas nunca decidido/auto-aprovado — vai pra revisão com `motivo="sem_endereco"`. `auditoria` injetada para logs de revisão e streaming para UI. `normalizador.py` (N0 + N1..N5 + tokenizer) consumido por `estruturador`/`estruturador_homogeneo` (N0+canonizar) e scorers (só canonizar, lista padrão não tem ID de equipamento embutido). `normalizador.FASES` é público (consumido também por `engine_tdt` como guard de domínio da coluna Phases).
- `pipeline.executar` aceita `sheets: list[str] | None` (whitelist de sheets a processar, filtrando `rota.sheets_dados`; `None` = todas as sheets que a heurística de `identificador.classificar` decidir) e `aliases: dict[str, str] | None` (sheet original → apelido, mesma chave que `AppState.aliases`; aplicado dentro do loop por sheet logo após `identidade_modulo.aplicar_identidade`, sobrescrevendo `modulo.nome` de todo sinal com `origem_contexto == "sheet_name"` — `SignalRecord.id` não muda, continua estável como `sheet:linha`). Isso é distinto de `_aplicar_aliases`/`gerar_tdt` (chamado só pelo export da tela de Revisão), que casa `aliases` contra o `modulo.nome` já resolvido, não o nome bruto da sheet — os dois caminhos coexistem e não devem ser confundidos.
- `engine_tdt`: carrega o template e escreve nele (preserva fórmulas/estilos/tabelas/validações); colunas por display name (row 4); valida contagem de colunas por sheet (DiscreteSignals=43, AnalogSignals=61, DiscreteAnalog=48). Roteamento 3-vias em `gerar()`: sinais cuja sigla decidida tem `SinalPadrao.categoria=="DiscreteAnalog"` (hoje só TAP) vão pra sheet `DNP3_DiscreteAnalog` via `_valores_discrete_analog` (Measurement Type=`Discrete`, Signal Type=`TapPosition`, Remote Point Type=`Analog`, Normal Value da lista, Device Mapping → comando `COMTAP`) e são excluídos de Discrete/Analog por `id()`; a sheet só é escrita quando há registros DiscreteAnalog. `Remote Point Alias` = data de hoje em `%Y%m%d` (`_alias_hoje`, padrão do TDT real). Output Coordinates de comando simples (1 índice) sempre duplica (`N;N`) — double-bit real (2 índices) não passa por esse caminho. `Output Data Type` deriva das coords de saída (iguais → `SingleCoord`, distintas → `MultiCoord`; domínio DNP3OutputType — `SingleBit` é só de Input). Dropdowns vêm das Data Validations do template (row 5, referenciam a sheet oculta `DMSMatchingTemplateInfo` com os domínios de valores por coluna/protocolo); `_expandir_dv` expande pro range de dados, incl. sqref multi-range (`B5 Y5`). Template restaurado por `scripts/restaurar_dvs_template_dnp3.py` (copia sheet oculta + DVs da TDT real exportada). Signal Type analógico traduz PT→EN (`_SIGNAL_TYPE_ANALOG_PT_EN`, ex. "Valor Medido"→`MeasuredValue`). `gerar(..., alias_v1: dict[str,str]|None=None)` — coluna `Signal Alias` usa `alias_v1[sigla]` (descrição da lista padrão **v1**, fixa, via `lista_padrao.descricoes_por_sigla`) quando a sigla decidida está no mapa; senão mantém `rec.descricoes.bruta` (fallback, nunca quebra a geração). `alias_v1=None` = comportamento antigo (retrocompat). Threadeado por `pipeline.gerar_tdt`/`pipeline.executar`.
- Cadeia de scoring — papel de cada módulo (REMOVE candidato vs RE-PONTUA vs DECIDE; conferir aqui antes de afirmar wiring):

  | Módulo | Papel | Escala do score |
  |---|---|---|
  | `scoring/calibracao.calibrar_candidatos` | re-escala por método (minmax/temp/isotonic/platt) | [0,1] |
  | `scoring/mescla.mesclar` | soma ponderada dos 3 métodos | pode passar de 1 se Σpesos>1 |
  | `calibracao.aplicar_calibrador_confianca` (E4) | score mesclado → P(correto) | [0,1] |
  | `ancoragem_sigla` | injeta candidato âncora + `filtrar_subarvore` REMOVE fora do ramo | âncora = `config.ancora_sigla_score` |
  | `expansao_candidatos` | ADICIONA irmãos de família | `pai.score × fator` |
  | `filtro_preciso` | REMOVE contraditórios (fallback: se zerar, devolve original) | não mexe em score |
  | `semantica_estados` / whitelist equipamento | REMOVE (gates duros) | não mexe em score |
  | `motor_regras` (r1..r9) | RE-PONTUA (soma deltas, unbounded) e reordena; **nunca remove** | pode sair de [0,1] |
  | `roteador` | DECIDE por pct/gap sobre o score cru pós-regras | — |
  | `pipeline._limitar_confianca` | clamp [0,1] SÓ na saída (exibição); roteamento usa cru | [0,1] |

  Decisão spB-B2 ("motor de regras como filtro bounded + renormaliza") está **pendente** — spec aguardando revisão, nunca implementada (ver ledger em `docs/AGENTS.md`).
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
