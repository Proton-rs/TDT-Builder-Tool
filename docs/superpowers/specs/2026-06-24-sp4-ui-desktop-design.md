# SP4 — UI Desktop (PySide6)

**Data:** 2026-06-24
**Status:** Spec aprovada para implementação
**Escopo:** Interface gráfica que envolve o pipeline determinístico do SP1.
**Goal:** operar o pipeline (configurar → executar → revisar → gerar TDT) numa
janela única, com revisão humana rica dos sinais e ajuste das configurações.

---

## 1. Objetivo

Dar uma UI desktop ao backbone do SP1. O usuário escolhe input/output, dispara o
pipeline com log ao vivo, revisa/corrige a classificação de cada sinal numa
tabela rica e gera o TDT. Uma aba de Configurações persiste pastas padrão,
thresholds, pesos e modelo.

### Em escopo
- 3 telas numa janela única: **Inicial**, **Revisão**, **Configurações**.
- Execução do pipeline em thread separada com log streaming e botão **PARAR**.
- Tabela de revisão com decididos + em revisão, colunas de diagnóstico, scroll
  H/V, edição do sinal inline **e** por painel lateral, busca da Lista Padrão ADMS.
- Persistência das configurações em `config.toml`.
- Tema visual fiel aos rascunhos (`docs/interface_inicial.jpg`,
  `docs/interface_revisão.jpg`): paleta roxo/cinza, fonte monospace.

### Fora de escopo (YAGNI por ora)
- Protocolos além de DNP3 (campo Protocolo fica fixo).
- Agentes LLM (SP2) — a UI só consome o pipeline determinístico.
- Edição em massa / atalhos avançados de revisão (decidir depois de medir uso).
- Internacionalização (UI em português).
- Empacotamento/instalador (PyInstaller fica como passo posterior, não nesta spec).

---

## 2. Stack e princípios

- **PySide6 (Qt for Python).** Mesma linguagem do pipeline; `QTableView` forte
  para a tabela; `QThread` para não travar a UI; `QSS` para o tema.
- **Lógica testável separada da widgetry.** Modelos de tabela, IO de config e o
  worker são testáveis com pytest sem abrir janela. Widgets têm smoke tests com
  `pytest-qt`. Renderização fina = verificação manual.
- **A UI não conhece o interior do pipeline** — só o contrato (`ResultadoPipeline`,
  `SignalRecord`, `ListaPadraoADMS`) e as extensões da §6.
- `# ponytail:` a UI é casca fina sobre o pipeline; nada de regra de negócio aqui.

---

## 3. Layout do projeto

```
src/tdt/ui/
  app.py            # QApplication, MainWindow (QStackedWidget), carrega tema.qss
  estado.py         # AppState: Config, paths, ResultadoPipeline atual, edições
  worker.py         # PipelineWorker(QThread): roda executar(), sinais de log/progresso/fim/erro; cancelamento
  tela_inicial.py   # Input/Output, Protocolo, Método, Flags, Subestação, Sheets, EXECUTAR/PARAR, LOG, ⚙
  tela_revisao.py   # tabela + painel de detalhe + aprovar/gerar TDT + Voltar
  tela_config.py    # pastas, thresholds, pesos, modelo — salva/carrega config.toml
  modelo_tabela.py  # ModeloSinais(QAbstractTableModel) sobre os SignalRecords
  config_io.py      # carregar/salvar config.toml <-> Config
  tema.qss
src/tdt/ui_main.py   # entry-point: python -m tdt.ui_main (ou console_script "tdt-ui")
tests/
  test_ui_modelo_tabela.py
  test_ui_config_io.py
  test_ui_worker.py
  test_ui_smoke.py     # pytest-qt: cada tela instancia e navega sem crashar
```

`app.py` é o único módulo que conhece todas as telas (análogo ao `pipeline.py`).
As telas comunicam-se via `AppState` + sinais Qt, não importando umas às outras.

---

## 4. Telas

### 4.1 Tela Inicial (`tela_inicial.py`)
Fiel ao rascunho. Componentes:
- **Input** — botão de pasta/arquivo `.xlsx`; ao escolher, lê os nomes das sheets
  e popula a lista de **Sheets** detectadas. Default vem do `config.toml`.
- **Output** — pasta de saída (default do config).
- **Protocolo** — combo fixo em `DNP3` (único valor por ora).
- **Método de processamento** — rádio: Automático (detecta pelo header) /
  Homogêneo / Não-homogêneo. Mapeia para `modo` do `executar` (`auto`/`homogeneo`/`nao-homogeneo`).
- **Flags** — checkboxes: "Pular revisão manual" e "Aprovar auto. acima do
  threshold". Ver §4.4 para o efeito.
- **Subestação** — combo "Auto detect" + edição manual (vira `subestacao`).
- **Sheets** — lista das sheets do input com checkbox por sheet (quais processar);
  default = todas as de dados.
- **EXECUTAR / PARAR** — dispara/cancela o `PipelineWorker`.
- **LOG** — painel read-only que recebe os eventos da `Auditoria` ao vivo (§6.3).
- **⚙** (topo, direita) — abre a tela de Configurações.

Ao terminar com sucesso, a UI troca para a tela de Revisão. Erro → mensagem no
LOG + diálogo; permanece na Inicial.

### 4.2 Tela de Revisão (`tela_revisao.py`)
Layout em duas colunas que ocupam a altura da janela:
- **Esquerda — Painel de detalhe** (largura fixa ~240–280px): campos do sinal
  selecionado empilhados verticalmente — Sinal (editável), Confiança, Status,
  Tipo, Escala, Fase, Endereço, Descrição bruta, TKN norm., barras de score por
  método (emb/tfidf/fuzzy), lista de **Candidatos** clicáveis (cada um com sigla,
  score fundido e descrição ADMS no tooltip), e um campo de **busca** para
  escolher qualquer sigla da Lista Padrão ADMS. Botão **aprovar / gerar TDT**.
  Botão **Voltar** (volta à Inicial).
- **Direita — Tabela** (`QTableView` + `ModeloSinais`): ocupa o resto da largura
  **e estica verticalmente** para preencher a altura disponível (máximo de linhas
  visíveis). Scroll horizontal e vertical. Mostra **decididos + em revisão**.

**Colunas da tabela** (todas com scroll H quando não cabem):
Sinal · Confiança · Status · Descrição bruta · TKN bruto · TKN norm. · Tipo ·
Escala · Fase · Endereço · Score embedding · Score tf-idf · Score fuzzy ·
Justificativa · Motivo.
- Status colorido: `decidido` (verde), `revisao` (laranja/coral).
- Tooltip na célula Sinal e nos candidatos = descrição da Lista Padrão ADMS.

**Edição do Sinal** (inline e pelo painel, sincronizados):
- Inline: a célula "Sinal" abre um editor (delegate) com os `candidatos_sugeridos`
  + campo de busca da lista ADMS completa.
- Painel: clicar num candidato OU buscar/escolher uma sigla ADMS define o sinal
  da linha selecionada.
- Editar uma linha atualiza `sigla_sinal` e marca o registro como editado
  (status → `decidido`, justificativa registra "editado manualmente").

**aprovar / gerar TDT:** roda `engine_tdt.gerar` (via `criador_lista_homogenea`)
sobre a lista atual com as edições aplicadas → grava o `TDT.xlsx` na pasta de
output; salva também `OUT.revisao.json`/`.log.txt`/`.auditoria.json` como a CLI.
Confirma sucesso/erro em diálogo.

### 4.3 Tela de Configurações (`tela_config.py`)
Formulário agrupado, com **Salvar** (escreve `config.toml`) e **Restaurar
padrões**. Volta via Voltar/⚙. Grupos:
- **Pastas/arquivos:** input padrão, output padrão, caminho do template DNP3,
  caminho da Lista Padrão ADMS (`.xlsx`). Validação: caminho existe.
- **Thresholds:** `threshold_pct`, `threshold_gap`, `top_n_pct` (sliders/spin,
  faixa [0,1]).
- **Pesos dos métodos:** `peso_tfidf`, `peso_vetorial`, `peso_fuzzy` e
  `pesos_regras` (por regra). Aviso visual se os três pesos de mescla não somam ~1.
- **Modelo:** `modelo_embedding` (combo MiniLM/e5), `k_vizinhos`, flags
  `corrigir_typos` e `remover_ids_equipamento`.

As mudanças entram em vigor no próximo EXECUTAR (a `Config` é relida do
`config.toml` ao montar o worker).

### 4.4 Efeito das Flags (Inicial)
- **Pular revisão manual:** após executar, vai direto ao "gerar TDT" sem abrir a
  tela de Revisão (usa as decisões automáticas; itens em revisão ficam de fora,
  como hoje). Mostra resumo decididos/revisão no LOG.
- **Aprovar auto. acima do threshold:** ao abrir a Revisão, pré-aprova (marca
  como decididos) os sinais cuja confiança ≥ `threshold_pct`, deixando para
  revisão manual só os abaixo. Default ligado, espelhando o rascunho.

---

## 5. Fluxo de dados

```
config.toml ──carregar──▶ Config ──┐
                                    ▼
TelaInicial (paths, modo, flags) ──▶ PipelineWorker(QThread) ──executar()──▶ ResultadoPipeline
        ▲                                  │ sinais: log/progresso                  │
        └──────────── PARAR ───────────────┘                                        ▼
                                                                       AppState.resultado
                                                                                    │
                                                            TelaRevisao ◀───────────┘
                                  (edições nos SignalRecords) ──aprovar──▶ engine_tdt ──▶ TDT.xlsx
```

`AppState` guarda a `Config` corrente, os paths, o `ResultadoPipeline` e as
edições do usuário (lista mutável de `SignalRecord` derivada do resultado; o
contrato segue imutável — edição = `replace`).

---

## 6. Extensões no pipeline (contrato — mínimas)

A UI exige um pouco mais do SP1. Tudo opcional/retrocompatível: CLI e benchmark
seguem inalterados.

### 6.1 Diagnóstico de scoring por sinal (Abordagem A)
Hoje `_classificar_sinal` funde os scores e descarta o detalhe por método. Para a
tabela mostrar emb/tfidf/fuzzy por candidato:
- Novo dataclass em `contracts.py`:
  ```python
  @dataclass(frozen=True)
  class Diagnostico:
      # por sigla candidata -> {"tfidf": float, "vetorial": float, "fuzzy": float}
      scores_por_metodo: dict[str, dict[str, float]]
  ```
- `SignalRecord` ganha `diagnostico: Diagnostico | None = None` (default None).
- `executar(..., diagnostico: bool = False)`: quando `True`, `_classificar_sinal`
  preenche o `Diagnostico` antes de fundir. A UI sempre chama com `diagnostico=True`.
- CLI/benchmark não passam o flag → campo fica `None`, custo zero.

### 6.2 Cancelamento (PARAR)
- `executar(..., cancelado: Callable[[], bool] | None = None)`: checado no loop de
  sheets/registros; se `cancelado()` retorna `True`, interrompe e devolve um
  `ResultadoPipeline` parcial + evento de auditoria "cancelado pelo usuário".
- O `PipelineWorker` expõe `parar()` que liga a flag lida por `cancelado`.

### 6.3 Log streaming
- `Auditoria` ganha callback opcional `on_evento: Callable[[Evento], None] | None`.
  `evento(...)` chama o callback além de acumular. O worker conecta o callback a
  um sinal Qt → painel LOG ao vivo. Sem callback, comportamento atual.

### 6.4 Acesso à Lista Padrão ADMS
- A UI carrega `ListaPadraoADMS` (já existe) para: descrições/tooltips por sigla,
  metadados (tipo, escala) e o seletor "qualquer sinal ADMS". Exposição via um
  método de conveniência `descricao_de(sigla) -> str | None` se ainda não houver.

### 6.5 Geração a partir da lista editada
- Reusar `criador_lista_homogenea.montar` + `engine_tdt.gerar`. Expor em
  `pipeline.py` uma função fina `gerar_tdt(registros, template, lp, subestacao)`
  que a UI chama no "aprovar/gerar TDT" (mesma rota do final de `executar`).

---

## 7. Worker (threading)

`PipelineWorker(QThread)`:
- Entrada: paths, `Config`, `modo`, `subestacao`, flags.
- `run()`: monta o `encoder` (`criar_encoder`), chama `executar(..., encoder=...,
  diagnostico=True, cancelado=self._cancelado, auditoria=Auditoria(on_evento=...))`.
- Sinais: `log(str)`, `progresso(int|str)`, `terminado(ResultadoPipeline)`,
  `erro(str)`.
- `parar()`: seta a flag de cancelamento (cooperativo; sem matar a thread).
- `# ponytail:` cancelamento cooperativo por flag; sem QThread.terminate (corrompe estado).

---

## 8. Tema (`tema.qss`)

- Paleta dos rascunhos: fundo roxo acinzentado (~`#7d7796`), painéis mais escuros
  (`#6c6688`/`#544f6e`), texto claro; tabela com fundo claro e header destacado.
- Fonte monospace; botões arredondados; scrollbars custom; ícones de pasta.
- Status na tabela: verde (decidido) / coral (revisão).
- Uma folha única aplicada na `QApplication`. Cores/medidas centralizadas no topo
  do arquivo para ajuste fácil.

---

## 9. Tratamento de erros

- **Input inválido / sem sheets de dados:** mensagem clara, permanece na Inicial.
- **Lista padrão / template ausente ou desatualizado:** erro explícito antes de
  executar/gerar (reusa as checagens do SP1, ex.: nº de colunas do template).
- **Falha no worker:** sinal `erro` → diálogo + LOG; UI volta ao estado ocioso.
- **PARAR:** resultado parcial coerente; nada é gravado até "aprovar/gerar TDT".
- **config.toml corrompido:** cai nos defaults da `Config` + avisa no LOG.

---

## 10. Abordagem TDD

Test-first onde a lógica é testável sem janela; smoke onde é widget.

| Teste | Garante |
|---|---|
| `test_ui_config_io.py` | round-trip `Config` → `config.toml` → `Config` preserva valores; arquivo ausente/corrompido cai nos defaults |
| `test_ui_modelo_tabela.py` | `ModeloSinais` expõe as colunas certas, dados por linha, edição do Sinal atualiza o registro (`replace`) e marca editado; tooltip = descrição ADMS |
| `test_ui_worker.py` | worker emite log/terminado; `parar()` cancela cooperativamente (com `executar` fake/curto) |
| `test_ui_smoke.py` (pytest-qt) | cada tela instancia, navega Inicial↔Revisão↔Config sem crashar; carregar um `ResultadoPipeline` fixo popula a tabela |

Extensões do pipeline (§6) ganham teste no SP1: `Diagnostico` populado quando
`diagnostico=True`; `cancelado` interrompe o loop; `on_evento` recebe os eventos.

---

## 11. Critérios de sucesso

1. Abrir input `.xlsx` lista as sheets; EXECUTAR roda sem travar a UI, com log ao
   vivo e PARAR funcional.
2. Tela de Revisão mostra decididos + em revisão com as colunas de diagnóstico;
   tabela estica na vertical; scroll H/V; status colorido.
3. Editar o Sinal (inline e pelo painel) entre candidatos ou qualquer sigla ADMS,
   com sincronização tabela↔painel; tooltip mostra a descrição ADMS.
4. "aprovar/gerar TDT" produz um `TDT.xlsx` estruturalmente válido a partir das
   edições.
5. Configurações persistem em `config.toml` e afetam o próximo run.
6. Testes da §10 verdes; CLI e `bench/benchmark.py` seguem inalterados (extensões
   retrocompatíveis).
