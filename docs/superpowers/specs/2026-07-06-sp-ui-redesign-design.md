# SP-UI — Redesenho de UX/UI da interface desktop (design)

**Data:** 2026-07-06
**Status:** aprovado em brainstorming (usuário validou seções 1–3 + mockups)
**Escopo:** somente `src/tdt/ui/` + `tests/test_ui_*.py` + DOX. Pipeline, scoring e contratos de dados (`contracts.py`) intocados.

## Contexto e objetivo

A UI atual (PySide6, 4 telas em `QStackedWidget` + `QTabBar`) funciona, mas tem
atritos de UX mapeados em auditoria:

- Botão EXECUTAR desabilita sem explicar o motivo (tooltip fixo).
- Pré-requisitos (template, lista padrão) só são descobertos via erro ou ⚙.
- Tela de Revisão: 22 colunas sem priorização; filtros com 2 gatilhos ocultos e
  inconsistentes (clique-direito = texto livre; duplo-clique = popup Excel);
  nenhuma indicação de filtro ativo; sem atalhos de teclado; undo existe no
  `AppState` mas **nenhum widget o chama**; gerar TDT não tem preview.
- `definir_sigla` e os 7 setters de domínio **não criam snapshot** de undo
  (lacuna documentada em `src/tdt/ui/AGENTS.md` → Local Contracts).
- Config com labels técnicos crus (`threshold_pct`, `peso_tfidf`).
- Tema roxo com contraste fraco e monospace em toda a UI.

**Decisões do usuário (brainstorming):**
- Abordagem **B**: redesenho de navegação (sidebar wizard), não incremental.
- Sidebar **retrátil**: colapsada por padrão (só ícones), expande apenas por
  clique no toggle.
- Usuário-alvo: técnicos SCADA que conhecem o domínio mas não o programa —
  autoexplicativo sem tutorial.
- Tema renovado: grafite escuro + acento azul único; monospace só em dados.
- Fluxo real de revisão: por sheet + passada final geral.

## Decomposição

Cinco sub-specs, cada uma implementável e testável de forma independente por
um executor sem contexto desta conversa. Ordem obrigatória: SP-UI-0 → SP-UI-1
→ (SP-UI-2, SP-UI-3, SP-UI-4 em qualquer ordem).

| Sub-spec | Entrega | Arquivos principais |
|----------|---------|---------------------|
| SP-UI-0 | Tema grafite (tokens, QSS, cores semânticas) | `tema.qss`, `modelo_tabela.py` |
| SP-UI-1 | Shell: sidebar retrátil + undo global + tela Geração no stack | `app.py`, `sidebar.py` (novo), `estado.py`, `tela_revisao.py` (método `refresh`) |
| SP-UI-2 | Tela Entrada guiada | `tela_inicial.py` |
| SP-UI-3 | Tela Revisão: atalhos, filtro unificado, preset de colunas | `tela_revisao.py`, `proxy_revisao.py`, `modelo_tabela.py` |
| SP-UI-4 | Tela Geração (nova) + Análise clicável + Config humana | `tela_geracao.py` (novo), `tela_analise.py`, `tela_config.py` |

---

## SP-UI-0 — Fundação de tema

### Tokens (fonte de verdade; usar exatamente estes hex)

```
fundo janela      #14161d
painel            #1e2430
painel elevado    #232a38
borda             #2b3242
borda forte       #3a4356
texto primário    #e8ebf2
texto secundário  #9aa3b5
texto apagado     #5f6880
acento            #4f8cff   (hover #6ba0ff · pressed #3d74d9 · texto sobre acento #0b1526)
seleção (tabela)  #243456
ok                #35c48f   (fundo tint #173226)
aviso             #e0a83f   (fundo tint #2a2118 · texto sobre aviso #2c2005)
erro              #e0604c   (fundo tint #3a1d18)
```

### Mudanças

1. **Reescrever `tema.qss`** com os tokens acima. Manter o cabeçalho-comentário
   listando os tokens (padrão atual do arquivo). Regras:
   - `QMainWindow, QWidget`: fundo `#14161d`, texto `#e8ebf2`,
     `font-family: "Segoe UI", sans-serif; font-size: 13px`. **Monospace sai do
     default global.**
   - `QPlainTextEdit, QTextEdit` (log): `font-family: Consolas, monospace`,
     fundo `#1e2430`, texto `#c6ccd9`.
   - `QGroupBox` e `#painelDetalhe`: fundo `#1e2430`, borda `#2b3242`,
     radius 10px.
   - `QPushButton`: fundo `#232a38`, borda `#2b3242`, texto `#e8ebf2`;
     hover `#2b3446`; pressed `#1a1f29`; disabled fundo `#1e2430` texto
     `#5f6880`.
   - `QPushButton[acao="principal"]`: fundo `#4f8cff`, texto `#0b1526`,
     bold; hover `#6ba0ff`; pressed `#3d74d9`. (Propriedade já usada hoje —
     manter o nome.)
   - Inputs (`QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox`): fundo
     `#1a1f29`, texto `#e8ebf2`, borda `#2b3242`;
     `:focus { border: 1px solid #4f8cff; }` — **estado de foco visível é
     requisito**, não opcional.
   - `QTableView`: fundo `#1a1f29`, alternate `#1e2430`, texto `#c6ccd9`,
     gridline `#232a38`, seleção `#243456` com texto `#e8ebf2`.
   - `QHeaderView::section`: fundo `#191d26`, texto `#9aa3b5`.
   - `QTabBar::tab`: texto `#9aa3b5`; `:selected` texto `#e8ebf2` +
     `border-bottom: 2px solid #4f8cff`.
   - `QProgressBar`: trilho `#232a38`; chunk `#4f8cff`.
   - `QListWidget`: fundo `#1a1f29`, item selecionado `#243456`.
   - Scrollbars finas (10px) com handle `#3a4356`.
2. **`modelo_tabela.py`** — atualizar constantes de cor:
   `COR_ALTO = COR_DECIDIDO = QColor("#35c48f")`,
   `COR_MEDIO = QColor("#e0a83f")`, `COR_BAIXO = COR_REVISAO = QColor("#e0604c")`.
   Faixas de `cor_faixa` (0.70/0.45) não mudam.
3. **Fonte monospace por coluna** — em `ModeloSinais.data()`, responder
   `Qt.FontRole` com Consolas para as colunas `Sinal`, `Endereço`,
   `Endereço Output`, `Tokens`, `Score embedding`, `Score tf-idf`,
   `Score fuzzy`. Demais colunas: fonte default.
4. **Barras de score da Revisão** (`tela_revisao._atualizar_barras`): já usam
   `cor_faixa` — nenhuma mudança além das constantes.

### Regras

- Estilo **só em `tema.qss`** (Work Guidance do AGENTS.md: não colocar style
  inline). Exceção existente: cor dinâmica do chunk das barras de score, que
  já é setada via `setStyleSheet` por valor — manter.
- Nenhuma dependência nova.

### Critérios de aceite

- App abre com tema grafite; nenhum widget com fundo roxo remanescente.
- Foco de teclado visível em qualquer input (borda azul).
- Status "decidido" verde `#35c48f` e "revisao" vermelho `#e0604c` na tabela.
- Testes existentes de UI continuam verdes.

### Testes

- `test_cor_faixa_novas_cores`: `cor_faixa(0.9).name() == "#35c48f"`,
  `cor_faixa(0.5).name() == "#e0a83f"`, `cor_faixa(0.1).name() == "#e0604c"`.
- `test_font_role_monospace`: `data(index_coluna_sinal, Qt.FontRole)` retorna
  fonte com família contendo "Consolas"; coluna "Status" retorna None.

---

## SP-UI-1 — Shell: sidebar retrátil + undo global

### Novo arquivo `src/tdt/ui/sidebar.py`

`Sidebar(QWidget)` — coluna vertical fixa à esquerda do `MainWindow`.

**Dois estados persistidos** (padrão: colapsada):

| | Colapsada | Expandida |
|---|---|---|
| Largura fixa | 48px | 200px |
| Item | só glifo + badge | glifo + rótulo + badge |
| Tooltip | rótulo completo | — |
| Rodapé de contexto | oculto | "SE · protocolo · N sinais" |

- Toggle: botão no topo (glifo `☰`), alterna estado e emite nada (só layout).
  Estado salvo em `QSettings("tdt", "ui")`, chave `sidebar_expandida` (bool),
  restaurado no construtor.
- **Itens de fluxo** (topo, nesta ordem): `1 · Entrada`, `2 · Revisão`,
  `3 · Geração`. **Itens fixos** (rodapé): `Análise`, `Configurações`.
- Glifos unicode, sem dependência de ícones: etapas usam `①②③` (ou o número
  simples), status usa `✓` (completa, verde) e `🔒` (bloqueada, texto apagado);
  Análise `▤`; Configurações `⚙` (já usado hoje).
- **Estados por item de fluxo**: `bloqueada` (texto `#5f6880`, não clicável),
  `ativa` (fundo `#243456`, texto `#e8ebf2`), `completa` (glifo `✓` verde,
  clicável), `disponivel` (texto `#9aa3b5`, clicável).
- **Badge de pendentes** no item Revisão: contagem de registros com
  `status == "revisao"`; pill âmbar (`#e0a83f` fundo, texto `#2c2005`).
  Método público `atualizar_badge(pendentes: int)` — some quando 0.
- API: `Sidebar(itens: list[tuple[chave, rotulo, glifo]])`;
  sinal `navegar = Signal(str)` (chave do item); métodos
  `definir_estado(chave, estado: str)`, `definir_ativa(chave)`,
  `atualizar_badge(int)`, `definir_contexto(texto: str)`.
- Implementação: QPushButtons flat empilhados em QVBoxLayout; propriedade QSS
  `item="ativo|bloqueado|normal"` + regras novas no `tema.qss`
  (`QPushButton[item="ativo"]` etc.). Sem QListWidget, sem model.

### `app.py` — MainWindow

1. Remover `QTabBar` e `_ABA_PARA_STACK`. Layout novo: `QHBoxLayout` raiz =
   `Sidebar` + `QStackedWidget`.
2. Stack: `0 TelaInicial · 1 TelaRevisao · 2 TelaConfig · 3 TelaAnalise ·
   4 TelaGeracao` (nova; até SP-UI-4 existir, usar placeholder
   `QWidget` com QLabel "Geração — em construção" para não bloquear esta
   sub-spec).
3. Mapeamento chave→índice: `{"entrada": 0, "revisao": 1, "config": 2,
   "analise": 3, "geracao": 4}`.
4. **Gating** (mesma semântica de hoje): na abertura, `revisao`, `geracao` e
   `analise` ficam `bloqueada`; após `tela_inicial.executou`, viram
   `disponivel`, `entrada` vira `completa`, e navega para `revisao`
   (respeitando as flags `pular_revisao` / `aprovar_acima_threshold` —
   lógica atual de `_ir_para_revisao` intocada). `config` sempre disponível.
5. `tela_inicial.abrir_config` e `tela_config.voltar` continuam funcionando
   (voltar navega para `entrada` e chama `tela_inicial.recarregar()`).
6. Badge: conectar ao fim de `_ir_para_revisao` e a `TelaRevisao` (ver hook em
   SP-UI-3; até lá, atualizar só no `executou`).
7. Contexto do rodapé: após `executou`, `sidebar.definir_contexto(
   f"{subestacao} · DNP3 · {len(registros)} sinais")`.

### Undo global (corrige a lacuna na raiz)

1. **`estado.py`**: `definir_sigla()` e `_editar_nested()` chamam
   `self._snapshot()` como primeira linha. Isso cobre **todos** os callers
   (delegates, painel de candidatos, busca ADMS, edição de célula) sem tocar
   em cada um. Remover das chamadas externas os `_snapshot()` que ficarem
   duplicados em sequência imediata? **Não** — snapshots duplicados são
   inofensivos (undo extra vazio) e os pontos atuais
   (`_remover_sinais`/`_adicionar_sinal`/`_parear_sinais`) protegem mutações
   que NÃO passam pelos setters. Manter.
2. **`app.py`**: `QShortcut(QKeySequence.Undo, self)` →
   `self._desfazer()`: chama `estado.desfazer()`; se `True` e a tela de
   revisão já foi carregada, chama `tela_revisao.refresh()` (novo método:
   `self._modelo.beginResetModel(); self._modelo.endResetModel()` +
   `_atualizar_painel()`; em SP-UI-3 também atualiza contadores).
3. Botão "↶ Desfazer (Ctrl+Z)" no topo da Revisão (SP-UI-3 posiciona;
   nesta sub-spec basta o atalho global funcionar).

### Critérios de aceite

- App abre com sidebar colapsada de 48px; clique no toggle expande para 200px;
  reabrir o app preserva o último estado.
- Etapas 2 e 3 bloqueadas antes de executar; desbloqueiam após pipeline.
- Ctrl+Z após escolher um candidato na Revisão restaura a sigla anterior.
- Navegação por clique funciona em todos os itens desbloqueados.

### Testes (pytest-qt)

- `test_sidebar_estados`: item bloqueado não emite `navegar` ao clicar; item
  disponível emite com a chave certa.
- `test_sidebar_toggle_persiste`: toggle muda largura; QSettings gravado.
- `test_undo_definir_sigla`: `AppState.definir_sigla` seguido de `desfazer()`
  restaura sigla e status anteriores (teste puro, sem Qt).
- `test_undo_editar_nested`: idem para `definir_fase`.
- `test_gating_pos_executou`: emitir `executou` desbloqueia revisão/geração.

---

## SP-UI-2 — Tela Entrada guiada

Refactor de `tela_inicial.py`. Worker, sheets checkable com alias, radios de
modo, flags e PARAR **mantidos como estão** — muda apresentação e feedback.

### Cards de arquivo com estado

Substituir os pares `QLabel` + `QLineEdit` readonly + botão por 4 cards
(input, template DNP3, lista padrão ADMS, pasta de saída). Card = `QFrame`
com propriedade QSS `estado="ok|faltando"`:

- `ok`: borda `#2b3242`, glifo `✓` verde, nome do arquivo (basename) em texto
  primário + caminho completo no tooltip, link-botão "trocar".
- `faltando`: borda `#e0a83f`, glifo `!` âmbar, texto "não configurado(a)",
  botão âmbar "Selecionar…" **no próprio card** (elimina a ida obrigatória ao
  ⚙ na primeira execução).
- Template/lista/output usam os mesmos file dialogs de hoje
  (`TelaConfig._escolher` é referência); ao selecionar, gravar em
  `estado.paths` **e persistir via `salvar_config`** (mesmo efeito colateral
  da TelaConfig, para a escolha valer na próxima sessão).
- `recarregar()` reavalia os 4 estados (já é chamado ao voltar da Config).

### Botão executar que se explica

- Novo método puro `motivo_bloqueio(sigla: str, paths: dict) -> list[str]`
  (testável sem Qt): devolve lista de pendências, na ordem: `"sigla da SE"`,
  `"arquivo de input"`, `"template DNP3"`, `"lista padrão ADMS"` (checa
  existência do path como `_input_valido` faz hoje).
- QLabel âmbar logo abaixo do botão: `"Falta: " + ", ".join(motivos)`;
  oculto quando vazio. Atualizado nos mesmos gatilhos de
  `_atualizar_estado_botao` (que passa a usar `motivo_bloqueio`).
  `pode_executar` atual pode ser mantido como wrapper ou absorvido.
- Botão renomeado: `EXECUTAR` → `Executar análise` (sentence case).

### Progresso com etapa nomeada

- Barra de progresso atual mantida (sinal `progresso(atual, total)`).
- QLabel de etapa acima da barra: mostra a **última linha recebida no sinal
  `log`** com nível `[INFO]`, elidida (`Qt.ElideRight`, largura do painel).
  Zero mudança no pipeline/worker — o rastro textual já existe.
- Durante execução: label + barra + "Parar" visíveis; ao terminar/erro, some.

### Log colapsável com níveis coloridos

- Trocar `QPlainTextEdit` por `QTextEdit` readonly.
- Novo helper puro `linha_log_html(texto: str) -> str`: envolve a linha em
  `<span style="color:...">` por prefixo — `[ERRO]` `#e0604c`, `[AVISO]`
  `#e0a83f`, `[INFO]` `#9aa3b5`, sem prefixo `#c6ccd9`. Conectar
  `worker.log` → `self.log.append(linha_log_html(m))`.
- Log **colapsado por padrão**: botão-toggle "Ver log ▾ / Ocultar log ▴".
  Erro do worker expande automaticamente (erro nunca fica invisível).
- "Limpar log" mantido (visível só quando expandido).

### Layout

Duas colunas em QGroupBox ("Arquivos" | "Análise") + faixa inferior de
execução (botão, motivo, etapa, barra, log). A coluna "Análise" agrupa:
subestação (obrigatória, com `*` no label), protocolo, método, flags, sheets.

### Critérios de aceite

- Primeira execução do zero é possível sem abrir a tela Config.
- Com lista padrão ausente: card âmbar + "Falta: lista padrão ADMS" sob o
  botão desabilitado; após selecionar, card fica ok e botão habilita (com
  sigla preenchida).
- Durante execução, label mostra a última etapa logada.
- `[ERRO]` aparece vermelho e o log se expande sozinho.

### Testes

- `test_motivo_bloqueio_ordena_pendencias` (puro): sem sigla e sem template →
  `["sigla da SE", "template DNP3"]`.
- `test_linha_log_html_niveis` (puro): cor certa por prefixo.
- `test_card_faltando_para_ok` (pytest-qt): setar path válido em
  `estado.paths` + `recarregar()` muda propriedade `estado` do card.
- `test_erro_expande_log` (pytest-qt): emitir `erro` do worker fake torna o
  log visível.

---

## SP-UI-3 — Tela Revisão: fluxo de teclado, filtro unificado, colunas

### Fluxo "aprovar e ir ao próximo"

- Botão principal na barra inferior: `Aprovar e ir ao próximo (Enter)`
  (`acao="principal"`). O botão "aprovar / gerar TDT" **permanece** nesta
  sub-spec (vira secundário, rótulo `Gerar TDT…`); quem o remove é a
  SP-UI-4, ao mover a geração para a etapa 3 — assim o app nunca fica sem
  caminho de geração, independente da ordem de implementação.
- Ação: na linha corrente, aplicar a sigla do candidato selecionado no painel
  (se nenhum selecionado, o top-1 de `r.candidatos`; se não há candidatos,
  no-op com beep) via `definir_sigla`; depois mover a seleção para a
  **próxima linha visível no proxy** com `status == "revisao"` (wrap: se não
  há próxima abaixo, procura do topo; se nenhuma, permanece e atualiza).
- `QShortcut(Qt.Key_Return, tabela)` dispara o mesmo slot (não interferir com
  edição de célula: atalho com `Qt.WidgetShortcut` na tabela; durante edição o
  editor consome o Enter).
- Atalhos `1`–`5`: aplicar o candidato N da lista do painel + ir ao próximo
  (mesmo slot com índice). `Ctrl+F`: foca `self.busca` (busca ADMS).
- Botão `↶ Desfazer` no topo (chama o mesmo `_desfazer` do MainWindow via
  sinal `desfazer_pedido = Signal()` ou referência ao estado + refresh local).

### Filtro unificado (um só gatilho)

- **Remover**: `_filtrar_coluna` (clique-direito, texto livre),
  `_construir_menu_coluna` (menu de módulos) e o gatilho de duplo-clique.
- **Único gatilho**: clique-direito no header abre `FiltroColunaDialog`
  (o popup estilo Excel existente) **estendido com campo "contém"** no topo
  (reaproveita `setFiltroColuna` texto, que já combina em AND com o filtro
  multi-valor no `ProxyRevisao` — nenhuma mudança de lógica de filtragem).
- Duplo-clique no header deixa de ter função (ordenar já é o clique simples).
- **Indicação de filtro ativo**: colunas filtradas exibem `▼` no header
  (via `headerData` do `ModeloSinais` consultando um set de colunas filtradas
  exposto pelo proxy — `ProxyRevisao.colunas_filtradas() -> set[int]`) e a
  barra de filtro ganha chip `Filtros ativos: N — Limpar todos` (QPushButton
  visível só com N>0; limpa texto + multi-valor de todas as colunas).

### Segmented de status

- Substituir o checkbox "Mostrar apenas revisão" por 3 botões checkable
  autoexclusivos: `Todos · Pendentes · Decididos`.
- `ProxyRevisao`: trocar `setEsconderDecididos(bool)` por
  `set_status_visivel(status: str | None)` (`None`=todos, `"revisao"`,
  `"decidido"`). Atualizar chamada em `_filtrar_status` e teste existente.

### Abas por sheet com progresso

- Texto da aba: `"{sheet} · {pendentes}"`; quando pendentes==0: `"{sheet} ✓"`.
  Aba "Tudo": `"Tudo · {total_pendentes}"`.
- Novo método `ModeloSinais.pendentes_por_sheet() -> dict[str, int]`
  (usa `sheet_origem`). `TelaRevisao._atualizar_abas_sheet()` re-rotula (sem
  reconstruir) e é chamado: no `carregar()`, em `dataChanged` do modelo, e
  após remover/adicionar/parear/undo.
- Badge da sidebar: emitir sinal `pendentes_mudaram = Signal(int)` no mesmo
  ponto; MainWindow conecta em `sidebar.atualizar_badge`.

### Preset de colunas + persistência

- Padrão visível: `Sinal, Confiança, Status, Motivo, Descr. bruta,
  Descr. ADMS, Módulo, Endereço`. Demais 14 ocultas via
  `tabela.setColumnHidden`.
- Botão `Colunas ▾` na barra de filtro: menu checkable com as 22 colunas
  (toggle de visibilidade).
- Persistência: `QSettings("tdt", "ui")` — `revisao_header_state`
  (`header.saveState()` no `hideEvent`/antes de gerar; `restoreState()` no
  `carregar()` se existir; senão aplica o preset padrão). saveState já
  captura visibilidade, largura e ordem arrastada.
- Colunas editáveis: sufixo `" ✎"` no `headerData` (`Sinal ✎`, `Tipo ✎`…) —
  fonte: `_EDITAVEIS` de `modelo_tabela.py`.

### Painel de detalhe

- `cofre.setFixedWidth(280)` → `QSplitter(Qt.Horizontal)` entre painel e
  tabela; largura inicial 280, mínimo 220; posição persistida no mesmo
  QSettings (`revisao_splitter_state`).

### Critérios de aceite

- Revisar uma sheet inteira só com teclado (Enter/1–5) é possível; a seleção
  pula automaticamente para o próximo pendente visível.
- Filtrar coluna por valores + "contém" num único popup; header mostra `▼`;
  "Limpar todos" zera tudo.
- Aba mostra contagem e vira `✓` quando a sheet zera pendências.
- Fechar e reabrir o app preserva colunas visíveis/larguras/ordem e splitter.
- Ctrl+Z reverte a última aprovação e os contadores atualizam.

### Testes

- `test_proximo_pendente_wrap` (puro ou qt): dado proxy com pendentes nas
  linhas visíveis 2 e 5, corrente=5 → próximo=2.
- `test_set_status_visivel`: `"decidido"` esconde pendentes; `None` mostra tudo.
- `test_colunas_filtradas_indicador`: aplicar filtro → header com `▼`;
  limpar → sem `▼`.
- `test_pendentes_por_sheet`: contagem correta com registros de 2 sheets.
- `test_aprovar_e_proximo_define_sigla`: Enter aplica top-1 e move seleção.

---

## SP-UI-4 — Tela Geração + Análise clicável + Config humana

### Novo arquivo `src/tdt/ui/tela_geracao.py`

`TelaGeracao(QWidget)` — etapa 3. Recebe `AppState`; método `carregar()`
recalcula tudo (chamado ao navegar para a tela).

**Conteúdo (de cima para baixo):**

1. Título `Geração — {subestacao}`.
2. 4 cards de resumo: Total, Decididos (verde), Pendentes (âmbar quando >0),
   Taxa de decisão. Reutilizar o padrão visual da TelaAnalise (QLabel 18pt).
3. **Avisos acionáveis** (lista vertical; cada um só aparece se aplicável):
   - Pendentes>0 — âmbar: "N sinais pendentes serão exportados com o melhor
     candidato atual" + botão `Rever pendentes →` (sinal
     `rever_pendentes = Signal()`; MainWindow navega p/ Revisão e ativa o
     segmented "Pendentes" — se SP-UI-3 ainda não estiver implementada,
     usar `setEsconderDecididos(True)` atual como fallback).
   - Endereços duplicados — vermelho: função pura
     `enderecos_duplicados(registros) -> dict[int, list[str]]` (índice DNP3 →
     ids dos registros que o repetem; considerar `indices` e `indices_saida`
     separadamente por direção). Botão `Rever duplicados →` (sinal
     `rever_duplicados = Signal(list)` com os índices; MainWindow navega e
     aplica filtro "contém" na coluna Endereço com o primeiro índice — simples
     e suficiente para localizar).
   - Verde informativo quando tudo ok: "Template e lista padrão validados".
4. Card "Arquivos de saída": nomes `TDT.xlsx` e `Auditoria_Revisao.xlsx`,
   pasta destino (elidida) + link "trocar" (dialog de pasta; grava em
   `estado.paths["output"]`).
5. Botão `Gerar TDT` (`acao="principal"`) + nota "sobrescreve TDT.xlsx
   existente".

**Comportamento do gerar** (lógica movida de `TelaRevisao._gerar`, que é
removida):

- Pré-checagens iguais (lista padrão, template, output — se faltar,
  QMessageBox como hoje).
- Se pendentes>0: QMessageBox de confirmação "Gerar com N pendentes?".
- Se `output/TDT.xlsx` já existe: QMessageBox "Sobrescrever TDT.xlsx?".
- Sucesso: **sem dialog** — painel de resultado na própria tela (verde):
  caminhos completos dos 2 arquivos + botão `Abrir pasta`
  (`os.startfile(output)` — Windows; guard `hasattr(os, "startfile")`).
- Erro: QMessageBox.critical (como hoje).

### `tela_analise.py`

1. **Cards clicáveis**: clicar em "Decididos"/"Revisão"/"Total" seta o combo
   de filtro correspondente (Total→"Todos"). Implementação: envolver cada
   card num QWidget com `mousePressEvent` ou instalar eventFilter; cursor
   `PointingHandCursor`.
2. **Motivos clicáveis**: substituir o QLabel único `_motivos_label` por uma
   linha de QPushButtons-chip (`"{label}: {n}"`, checkable). Chip ativo
   filtra a tabela pelo motivo: `_ProxyStatus` ganha
   `definir_filtro_motivo(motivo_label: str | None)` (AND com o filtro de
   status; coluna "Motivo" de `ModeloAnalise`).
3. **Ponte Análise→Revisão**: botão `Rever na Revisão →` habilitado com linha
   selecionada; emite `rever_sinal = Signal(str)` (id do registro).
   MainWindow: navega para Revisão, limpa filtros de status, localiza a linha
   pelo id (`estado.registros`) e seleciona/rola até ela via proxy.

### `tela_config.py`

1. Reagrupar o form em 4 `QGroupBox`: `Caminhos padrão`, `Decisão automática`,
   `Pesos do ensemble`, `Modelo semântico`.
2. Labels humanos com o nome técnico como sublabel discreto e tooltip de
   efeito (aplicar exatamente):

   | Campo | Label | Tooltip |
   |---|---|---|
   | threshold_pct | Score mínimo para decidir sozinho | Candidato nº 1 precisa de pelo menos este score. Maior = decide mais sozinho, mais risco de erro. |
   | threshold_gap | Vantagem mínima sobre o 2º | Diferença mínima entre 1º e 2º candidato. Maior = só decide quando a liderança é clara. |
   | top_n_pct | Corte dos candidatos exibidos | Score mínimo (relativo ao 1º) para um candidato aparecer na lista da revisão. |
   | peso_tfidf | Peso do TF-IDF/BM25 | Peso do método lexical na mescla dos scores. |
   | peso_vetorial | Peso do embedding | Peso do método semântico (vetorial) na mescla. |
   | peso_fuzzy | Peso do fuzzy | Peso da similaridade de caracteres na mescla. |
   | modelo_embedding | Modelo de embedding | Modelo sentence-transformers usado no método vetorial. Trocar exige novo download/cache. |
   | k_vizinhos | Candidatos por sinal (k) | Quantos vizinhos o índice vetorial devolve por sinal. |

3. **Validação dos pesos**: QLabel âmbar sob o grupo, visível quando
   `abs(peso_tfidf + peso_vetorial + peso_fuzzy − 1.0) > 0.001`:
   "Os pesos somam {soma:.3f} — o esperado é 1.0". Não bloqueia salvar
   (a mescla normaliza), só informa.
4. Botão `Restaurar padrões`: repõe `Config()` default nos widgets (não salva
   até clicar Salvar).

### Critérios de aceite

- Fluxo completo: Entrada → Revisão → Geração gera os mesmos arquivos que o
  botão antigo gerava (TDT.xlsx + Auditoria_Revisao.xlsx, mesmos callers).
- "Rever pendentes →" cai na Revisão já filtrada em Pendentes.
- Gerar com pendências e com TDT.xlsx existente pede confirmação; sucesso
  mostra caminhos e abre a pasta.
- Clicar no card "Revisão" da Análise filtra a tabela; chip de motivo filtra;
  "Rever na Revisão →" seleciona o sinal certo.
- Config mostra labels humanos; pesos somando ≠1.0 exibem o aviso.

### Testes

- `test_enderecos_duplicados` (puro): 2 registros com índice 14 → dict com
  ids; direções não se misturam (input 14 + output 14 ≠ duplicata).
- `test_gerar_confirma_pendentes` (qt, monkeypatch QMessageBox): pendentes>0
  pergunta antes; recusa não gera.
- `test_filtro_motivo_proxy` (qt): chip filtra linhas pelo motivo.
- `test_config_aviso_pesos` (qt): 0.5/0.3/0.1 mostra aviso; 0.5/0.3/0.2 esconde.
- `test_rever_sinal_seleciona` (qt): sinal com id conhecido → linha corrente
  na Revisão aponta para ele.

---

## Fora de escopo (não fazer)

- Pipeline, scoring, contratos, worker (exceto zero mudanças confirmadas acima).
- Redo (Ctrl+Y) — pilha de undo permanece sem ponteiro (upgrade path já
  documentado em `estado.py`).
- Novas dependências (ícones = glifos unicode; persistência = QSettings).
- Novo protocolo além de DNP3; i18n; modo claro.
- Wizard modal/forçado — a sidebar guia, não tranca (usuário técnico).

## DOX (obrigatório no closeout de cada sub-spec)

Atualizar `src/tdt/ui/AGENTS.md`:

- Ownership: `sidebar.py`, `tela_geracao.py`, renomeações de responsabilidade
  (geração sai da TelaRevisao).
- Local Contracts: snapshot agora é interno aos setters do AppState (lacuna
  fechada); `ProxyRevisao.set_status_visivel` substitui `esconder_decididos`;
  navegação = Sidebar + QStackedWidget (5 telas), não mais QTabBar.
- Verification: comandos inalterados.

## Riscos

- `QShortcut` Enter vs edição de célula: mitigado com `Qt.WidgetShortcut` e
  teste manual; se conflitar, mover para `keyPressEvent` da tabela.
- `restoreState` de header com colunas novas no futuro: se o número de colunas
  mudar, o estado salvo é descartado (checar `header.count()` antes).
- Emojis/glifos (`🔒`, `✎`, `▼`) dependem da fonte do Windows — todos existem
  em Segoe UI/Segoe UI Symbol; fallback aceitável é o glifo vazio, sem crash.
