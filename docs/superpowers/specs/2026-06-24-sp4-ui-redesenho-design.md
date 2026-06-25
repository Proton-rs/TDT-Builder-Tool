# SP4.1 — Redesenho da UI (bonita, limpa e funcional)

**Data:** 2026-06-24
**Status:** Spec aprovada para implementação
**Base:** SP4 (UI PySide6 já implementada em `src/tdt/ui/`).
**Goal:** deixar a UI **mais bonita e limpa** (refino visual nas 3 telas, fiel ao
rascunho roxo/monospace) e **mais funcional** na revisão — onde hoje os
candidatos não aparecem e não dá para comparar descrições da Lista Padrão ADMS.

---

## 1. Objetivo e contexto

A UI atual funciona, mas (a) tem bugs na tela de revisão que escondem os
candidatos e a comparação de descrições, e (b) o visual está "flat" demais
frente ao rascunho. Este sub-projeto **refina** a UI existente — não reescreve a
arquitetura (`estado`/`modelo_tabela`/`worker`/telas/`config_io`/`app`, que está
bem estruturada). Escopo: as **3 telas** ganham tratamento visual; a **Revisão**
ganha também as correções funcionais.

### Princípios
- Mantém a arquitetura e a separação de responsabilidades atuais.
- Mantém a identidade **roxo + monospace** do rascunho, com muito melhor
  espaçamento, hierarquia, contraste e agrupamento (densidade **confortável**).
- Lógica testável (modelo, busca) separada de widget; smoke com `pytest-qt`.
- `# ponytail:` para atalhos deliberados; nada de over-engineering.

---

## 2. Correções de bug (Revisão) — pré-requisito

Estas entram primeiro porque destravam a funcionalidade que o operador relatou.

### B1. `QListWidgetItem` não importado
`src/tdt/ui/tela_revisao.py` usa `QListWidgetItem` (montagem dos candidatos) mas
não o importa → `NameError` ao selecionar uma linha → **a lista de candidatos
nunca aparece**. Adicionar ao import de `PySide6.QtWidgets`.

### B2. f-string do painel engole o texto inteiro
Em `_atualizar_painel`, o `... if r.candidatos else ""` cobre o f-string inteiro:
sinais **em revisão sem candidato** mostram o painel em branco (sem Sinal,
Status, Tipo...). Reescrever montando os campos sempre, e a Confiança só quando
há candidato.

### B3. Busca ADMS pobre
`_aplicar_busca` auto-escolhe o 1º match exato/prefixo e sai; não lista
resultados, não mostra descrições, ignora `analogicos`. Substituída pela busca
da §4.3.

### B4. Coluna duplicada
`modelo_tabela.COLUNAS` tem "Justificativa" e "Motivo" devolvendo o mesmo
`rec.justificativa`. Remover "Motivo" (ver §4.4).

---

## 3. Identidade visual (`tema.qss` reescrito)

Folha única, cores/medidas no topo para ajuste fácil. Paleta roxa do rascunho,
densidade confortável, cantos arredondados.

| Token | Valor | Uso |
|---|---|---|
| `--fundo` | `#7d7796` | fundo das telas |
| `--painel` | `#6c6688` | cards/grupos, header de tabela |
| `--painel-2` | `#544f6e` | inputs, itens, bordas internas |
| `--borda` | `#46415f` | bordas |
| `--acento` | `#8a7fe0` | **roxo vibrante** — ações principais |
| `--acento-texto` | `#1c1733` | texto sobre o acento |
| `--texto` | `#f3f1f7` | texto sobre roxo |
| `--tab-fundo` | `#e7e5ef` / `#cfccd9` | linhas da tabela (zebra leve) |
| `--ok` | `#0f6e56` (texto) / `#5dcaa5` (barra) | decidido / score alto |
| `--medio` | `#854f0b` (texto) / `#efb14a` (barra) | score médio |
| `--baixo` | `#993c1d` (texto) / `#e0613f` (barra) | revisão / score baixo |

Regras-chave:
- Fonte monospace (Consolas/Courier New), `font-size` base 13px; títulos de
  seção em maiúsculas com leve `letter-spacing`.
- `QPushButton` padrão neutro; **classe de acento** (via `setProperty("acao",
  "principal")` + seletor `QPushButton[acao="principal"]`) para EXECUTAR,
  "aprovar / gerar TDT", Salvar — fundo `--acento`, sem borda, cantos 10px.
- Inputs/combos/spins: fundo claro, cantos 8px, padding confortável.
- `QTableView`: zebra leve, `gridline` discreto, header `--painel` com padding
  9–11px e borda inferior de 2px; seleção de linha com `outline`/realce do acento.
- Scrollbars custom; indicadores de `QCheckBox`/`QRadioButton` visíveis
  (preencher com o acento quando marcados).
- `QListWidget` de candidatos/busca: itens como "cards" com padding e cantos.

`# ponytail:` QSS não suporta variáveis nativas — declarar as cores como
comentário-legenda no topo e usar os hex diretamente; um bloco por widget.

---

## 4. Tela de Revisão (funcional + visual)

Layout: **painel de detalhe à esquerda** (largura fixa ~268px) + **tabela à
direita** esticando (vertical e horizontal). Botões: "← Voltar" (topo-esq) e
"aprovar / gerar TDT" (acento, topo-dir).

### 4.1 Painel de detalhe (campos empilhados)
Para o sinal selecionado:
- **Sinal escolhido** (dropdown editável — espelha a edição inline da célula).
- Campos: Status (com bolinha colorida), Tipo (`categoria/direcao`), Fase,
  Endereço (`;`.join índices), Escala (se analógico).
- **Scores por método**: `emb`, `tfidf`, `fuzzy` como **barra proporcional +
  número + cor por faixa** (alto/médio/baixo). Lê de `rec.diagnostico`
  (sigla escolhida).
- **Candidatos**: lista (de `rec.candidatos`), cada item card com sigla, score
  fundido e **descrição ADMS** (de `lista_padrao.por_sigla(sigla).descricao`).
  Clicar define a sigla da linha. Tooltip com a descrição completa.
- **Busca ADMS** (§4.3).

Sem candidatos: o painel ainda mostra os campos do sinal; a área de candidatos
exibe "sem candidatos — use a busca".

### 4.2 Comparação de descrições
A comparação bruta × ADMS acontece **na tabela** (colunas Descr. ADMS, Descr.
bruta, Descr. normalizada, Tokens — §4.4) e **nos candidatos/busca** (cada um
mostra sua descrição ADMS). O painel não precisa de um bloco dedicado de
comparação.

### 4.3 Busca na Lista Padrão ADMS
Nova função pura, testável, em um módulo de apoio `src/tdt/ui/busca_adms.py`:
```python
def buscar(lp: ListaPadraoADMS, termo: str, limite: int = 30) -> list[SinalPadrao]
```
- Casa o `termo` (case-insensitive, sem acento) contra a **sigla** *e* contra o
  **texto da descrição** (substring por token). Ex.: "falha" acha DJF1/DJF2;
  "sobrecorrente" acha 51/67.
- Busca em **discretos + analógicos**.
- Ordena: matches de sigla primeiro, depois de descrição; corta em `limite`.
- `# ponytail:` varredura linear sobre a lista (alguns milhares de itens); sem índice.

Na UI: campo de texto → lista de resultados (sigla · tag discreto/analógico ·
descrição ADMS) → clicar escolhe a sigla para a linha selecionada. Atualiza ao
digitar (com `limite` para não travar).

### 4.4 Colunas da tabela (`modelo_tabela.COLUNAS`)
Conjunto enxuto e útil:
`Sinal · Confiança · Status · Descr. ADMS · Descr. bruta · Descr. normalizada ·
Tokens · Tipo · Escala · Fase · Endereço · Score embedding · Score tf-idf ·
Score fuzzy · Justificativa`.
- **Descr. ADMS** (novo): `lista_padrao.por_sigla(sigla_sinal).descricao` ou "—".
- **Descr. bruta**: `descricoes.bruta`.
- **Descr. normalizada**: `descricoes.normalizada` (forma canônica).
- **Tokens**: `descricoes.normalizada.split()` exibido com separador visível
  (ex.: `tok·tok·tok`).
- Remove "Motivo" (duplicava "Justificativa"); remove o antigo "TKN bruto"
  (duplicava "Descr. bruta").
- `data()` com `BackgroundRole`/cor para **Status** (verde/coral) e **Confiança**
  (verde/âmbar/vermelho por faixa via `threshold_pct`); `ToolTipRole` na célula
  Sinal e Descr. ADMS com a descrição ADMS completa.

### 4.5 Edição (painel + célula, sincronizados)
- **Célula "Sinal"**: editável via `QStyledItemDelegate` (`EditTriggers` =
  duplo-clique) que abre um combo com **candidatos** + **busca ADMS**; ao
  confirmar, chama `modelo.definir_sigla(linha, sigla)`.
- **Painel**: clicar candidato / escolher resultado de busca chama o mesmo
  `definir_sigla`. `dataChanged` re-renderiza a linha; o painel reflete a célula
  selecionada. Editar marca `status="decidido"`, justificativa "editado
  manualmente" (comportamento atual de `AppState.definir_sigla`).

---

## 5. Telas Inicial e Configurações (visual)

Sem mudança funcional relevante; reorganização visual:
- **Agrupar** campos relacionados em **cards com título** (ex.: Inicial →
  "Entrada/Saída", "Processamento", "Flags", "Sheets", "Execução/LOG"; Config →
  "Pastas", "Thresholds", "Pesos", "Modelo").
- Espaçamento confortável, cantos arredondados, alinhamento consistente.
- Botões principais (EXECUTAR, Salvar) com a classe de **acento**.
- Inicial: ⚙ no topo-direito; LOG ocupando a coluna direita inteira; lista de
  Sheets com altura adequada.
- Manter os ajustes já feitos (indicadores radio/checkbox, sheets editáveis,
  placeholders, largura dos spins).

---

## 6. Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `src/tdt/ui/tela_revisao.py` | import `QListWidgetItem`; painel reescrito (campos sempre; barras de score; candidatos com descrição ADMS); busca via `busca_adms`; delegate de edição inline |
| `src/tdt/ui/busca_adms.py` (novo) | `buscar(lp, termo, limite)` — função pura |
| `src/tdt/ui/modelo_tabela.py` | colunas novas (Descr. ADMS/normalizada/Tokens), remove duplicatas; cores via `BackgroundRole`; tooltips |
| `src/tdt/ui/delegate_sinal.py` (novo) | `QStyledItemDelegate` com combo candidatos + busca |
| `src/tdt/ui/tela_inicial.py` | agrupamento em cards; classe de acento nos botões |
| `src/tdt/ui/tela_config.py` | agrupamento em cards; classe de acento |
| `src/tdt/ui/tema.qss` | reescrito (§3) |

`AppState`, `worker`, `config_io`, `app` permanecem (no máximo o `app` ganha
ajuste se a navegação mudar — não está previsto).

---

## 7. Dados / dependências

- Scores por método: já em `SignalRecord.diagnostico` (UI já roda com
  `diagnostico=True`).
- Descrição ADMS: `ListaPadraoADMS.por_sigla(sigla)` (existe).
- **B5 (causa raiz adicional): `AppState.lista_padrao` nunca é populado.** É lido
  em `modelo_tabela.py:91` e `tela_revisao.py` (3×) mas não é atribuído em lugar
  nenhum → sempre `None`. Por isso hoje **nenhuma** descrição ADMS aparece, os
  tooltips e a busca não funcionam, e o **"aprovar/gerar TDT" falha sempre**
  (`tela_revisao._gerar` aborta com `if not lp`). **Correção:** ao terminar o
  worker, em `TelaInicial._terminado`, popular
  `estado.lista_padrao = ListaPadraoADMS.carregar(estado.paths["lista_padrao"])`
  antes de `executou.emit()`. (Uma carga extra leve do .xlsx no lado da UI;
  `# ponytail:` recarrega em vez de fazer o worker devolver a lista.) Esta é a
  única integração nova fora das telas.
- Sem novas dependências de terceiros.

---

## 8. Abordagem TDD

| Teste | Garante |
|---|---|
| `test_ui_busca_adms.py` | `buscar` casa por sigla e por texto da descrição; discretos+analógicos; ordena sigla-first; respeita `limite`; case/acentos |
| `test_ui_modelo_tabela.py` (estende) | colunas novas (Descr. ADMS via `por_sigla`, normalizada, Tokens); duplicatas removidas; cor de Status/Confiança por `BackgroundRole`; tooltip ADMS |
| `test_ui_smoke.py` (estende) | selecionar linha popula o painel **sem erro** (regressão do B1/B2); candidatos aparecem com descrição; busca filtra e escolher define a sigla; delegate instancia |

Renderização fina do `tema.qss` = verificação manual (abrir `python -m
tdt.ui_main`).

---

## 9. Critérios de sucesso

1. Selecionar uma linha na revisão **mostra os candidatos** com sigla, score e
   descrição ADMS (bug B1/B2 corrigidos).
2. Buscar por "falha"/"sobrecorrente" lista sinais ADMS (sigla+descrição) de
   discretos e analógicos; clicar define a sigla.
3. Tabela mostra Descr. ADMS + bruta + normalizada + Tokens; Status e Confiança
   coloridos; sem coluna duplicada.
4. Editar o Sinal funciona pela célula (duplo-clique) e pelo painel,
   sincronizados.
5. As 3 telas com visual refinado (cards, espaçamento, acento roxo vibrante),
   fiéis à identidade do rascunho.
6. Testes da §8 verdes; suíte total continua passando.
