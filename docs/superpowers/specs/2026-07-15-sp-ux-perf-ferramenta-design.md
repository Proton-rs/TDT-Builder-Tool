# SP-UX-PERF — Ajustes de UX e performance da ferramenta

**Status:** implementado (2026-07-15, commits e02b51a..08d0876 na branch `feature/sp-ux-perf-ferramenta`)

**Data:** 2026-07-15
**Origem:** `docs/anot.txt` ("Analise funcionamento da ferramenta") — Frente 2 da decomposição de 15/07.
A Frente 1 (device mapping RGE) tem spec/plano próprios (`2026-07-15-sp-device-mapping-rge-*`).

## Contexto / Problema

Cinco dores de uso relatadas na operação real:

1. **Seleção de sheets** (tela inicial): checkbox difícil de acertar; não dá para
   marcar/desmarcar várias sheets de uma vez.
2. **Filtro por coluna na revisão**: ao dar OK o popup parece não fechar e às vezes
   "trava" — o `invalidateFilter` roda pesado logo após o `exec()`, congelando a UI
   com o dialog ainda pintado na tela.
3. **Geração da TDT**: `_gerar()` passa `estado.registros` inteiro; não existe opção
   de gerar só alguns módulos.
4. **Campos da revisão**: a coluna Equipamento (ID, ex. `81-1`) não é editável — um
   equipamento errado decidido pelo programa não pode ser corrigido na revisão.
5. **Ações em massa**: remover ~500 sinais trava o programa —
   `modelo_tabela.remover_linhas` emite `beginRemoveRows`/`endRemoveRows` POR LINHA,
   e cada emissão dispara refiltro/repaint em cascata (O(n²) percebido).

## Escopo

Só UI (`src/tdt/ui/`): `tela_inicial.py`, `tela_revisao.py`, `tela_geracao.py`,
`proxy_revisao.py`, `modelo_tabela.py`, `delegate_sinal.py`, `estado.py`.

## Não-escopo

- Pipeline/classificação/engine: nada muda fora de `ui/`.
- Rename de sheets em lote: **descartado por decisão do usuário 15/07** (rename
  continua um a um, inline).
- Redo do undo: pertence ao redesign de 06/07 (decisão registrada, não reabrir).
- Campos derivados continuam não-editáveis: Confiança, Status, Motivo, Descr. ADMS,
  Descr. normalizada, Tokens, Scores, Justificativa, Pareado, Sheet origem.

## Design

### 1. Seleção de sheets (tela inicial — `tela_inicial.py`)

- `lista_sheets.setSelectionMode(ExtendedSelection)`: shift/ctrl seleciona várias
  linhas.
- Ações em grupo (menu de contexto): **Marcar selecionadas**,
  **Desmarcar selecionadas**, **Inverter marcação**. Agem sobre as linhas
  selecionadas; sem seleção, agem sobre todas. Atalho: tecla Espaço alterna o
  checkbox de todas as linhas selecionadas.
- Hitbox: clique em qualquer ponto da linha alterna o checkbox (hoje só o
  quadradinho alterna). Clique com modificador (shift/ctrl) só seleciona, não
  alterna — senão a seleção múltipla ficaria inusável. Duplo clique continua
  abrindo a edição inline do nome (rename um a um).

### 2. Fluidez do filtro por coluna (`tela_revisao.py`, `proxy_revisao.py`)

- `_filtrar_coluna()`: após o `dialog.exec()` retornar com accept, aplicar o filtro
  no **tick seguinte** (`QTimer.singleShot(0, ...)`) com cursor busy
  (`setOverrideCursor(WaitCursor)` / `restoreOverrideCursor`). O dialog some da
  tela antes do trabalho pesado começar — elimina o "não fechou / travou".
- Otimizar o caminho quente do proxy: `filterAcceptsRow` não pode reconstruir
  strings/estruturas por linha — valores de comparação pré-computados uma vez em
  `set_filtro_coluna` (sets prontos por coluna), lookup O(1) por linha.
- Critério: em lista de ~5.000 linhas, aplicar/limpar filtro não congela a UI de
  forma perceptível (< ~200ms de bloqueio) e o dialog fecha imediatamente ao OK.

### 3. Geração seletiva por módulo (`tela_geracao.py`)

- Lista de módulos com checkbox (mesmo padrão visual da seleção de sheets da tela
  inicial), populada em `carregar()` a partir dos módulos distintos de
  `estado.registros`. **Todos marcados por default** (comportamento atual =
  gerar tudo).
- `_gerar()` filtra `estado.registros` pelos módulos marcados antes de chamar
  `pipeline.gerar_tdt`.
- Contadores (total/pendentes/decididos) refletem a seleção corrente.
- Nenhum módulo marcado → botão Gerar desabilitado.
- Os gates de geração (`particionar_custom_id_duplicado` etc.) continuam rodando
  sobre o subconjunto filtrado — nada muda neles.

### 4. Campos editáveis novos (`modelo_tabela.py`, `delegate_sinal.py`, `estado.py`)

- **Equipamento (ID)**: entra em `_EDITAVEIS`; delegate novo `DelegateEquipamento`
  (combo editável, mesmo padrão do `DelegateModulo`): sugere os IDs de equipamento
  já presentes em registros do mesmo módulo + aceita texto livre. Vazio limpa o
  campo (`nome_equipamento=None`). `setData` → método novo
  `AppState.definir_equipamento(id_registro, valor)` com snapshot (undo igual aos
  demais campos). Caso de uso alvo: corrigir `81-1` → `52-11` na revisão.
- **Descr. bruta**: entra em `_EDITAVEIS`, edição de texto livre. Afeta o que o
  export usa como fallback de Signal Alias; **não** reprocessa matching nem
  normalização (Tokens/normalizada ficam como estavam). `setData` → método novo
  `AppState.definir_descricao_bruta(id_registro, valor)` com snapshot; valor vazio
  é rejeitado (descrição bruta é dado de origem, não pode ficar vazia).

### 5. Performance de ações em massa (`modelo_tabela.py`, `tela_revisao.py`)

- `remover_linhas(indices)`:
  - lote > 100 linhas → **um** `beginResetModel`/`endResetModel` (rebuild único,
    O(n));
  - lote ≤ 100 → `beginRemoveRows` por **range contíguo** (índices ordenados e
    agrupados), não por linha.
  - Semântica preservada: mesma remoção, mesmo snapshot único de undo ANTES da
    operação, seleção limpa ao fim.
- `_aplicar_em_lote`: `setUpdatesEnabled(False)` na view durante o loop
  (try/finally) e **um** `dataChanged` agregado no fim (linha mín..máx, todas as
  colunas), em vez de um por célula.
- Critério: remover 500 sinais em < 1s sem congelar; edição em lote de 500 células
  sem repaint por célula.

## Critérios de aceite / testes

- Testes de unidade onde há lógica pura: agrupamento de ranges contíguos,
  filtragem de registros por módulos marcados, `definir_equipamento`/
  `definir_descricao_bruta` (incl. undo restaura valor anterior; vazio rejeitado
  na descrição).
- Testes de modelo Qt já existentes (`tests/` usa o padrão dos testes de
  `modelo_tabela`): flags editáveis das colunas novas; `remover_linhas` grande e
  pequeno removem exatamente os índices pedidos.
- Fluidez (seções 2 e 5): verificação manual com lista real grande — dialog fecha
  no OK; remover ~500 sinais < 1s. Registrar o resultado no closeout.
- Nada fora de `src/tdt/ui/` e `tests/` muda.

## Resultados da verificação (closeout 15/07)

- Suite completa: `python -m pytest -q tests/` — **982 passed, 5 skipped, 2 xfailed**
  (baseline pré-SP-UX-PERF: 962 passed; +20 testes novos das 5 tasks, 0 regressão).
- Smoke test de import/construção das 3 telas alteradas (`TelaInicial`, `TelaRevisao`,
  `TelaGeracao`) sem `AppState` real — sem erro.
- Critérios de performance medidos programaticamente (`ModeloSinais` +
  `ProxyRevisao` + `QTableView` reais, 5.000 registros sintéticos, sem mock):
  - Filtro por coluna em 5.000 linhas: **21.4ms** (critério: sem congelamento
    perceptível, ~200ms).
  - Remover 500 de 5.000 linhas (com view+proxy anexados): **17.7ms** (critério:
    < 1s). Caminho sem view/proxy (só o modelo): 0.7ms.
- **Não verificado interativamente** (ambiente sem automação de GUI desktop e sem
  acesso à lista real grande da SE CVA/LVA, fora do repositório): a sensação
  subjetiva de fluidez do usuário ao clicar (shift-click em sheets, popup de
  filtro, edição de Equipamento via combo) — os números acima cobrem o
  mecanismo (sinais Qt corretos, tempo de execução), não a experiência ao vivo.
  Recomendado: um passe manual do usuário na próxima sessão com dado real antes
  de considerar a UX definitivamente resolvida.

## Decisões registradas (para o ledger no closeout)

- Rename de sheets em lote descartado (usuário 15/07); só marcação em grupo.
- Editáveis novos: Equipamento (ID) e Descr. bruta; derivados seguem travados.
- Remoção em massa: reset único acima de 100 linhas, ranges contíguos abaixo.
- Filtro aplicado pós-fechamento do dialog (tick seguinte) + caminho quente do
  proxy pré-computado.
