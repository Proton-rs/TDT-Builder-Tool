# SP8 — UI: Filtros por Coluna, Tela Inicial, Status Pendente

**Data:** 2026-06-24
**Status:** Aguardando revisão do usuário
**Escopo:** Itens "FILTROS" (resto), "TELA INICIAL" e "PENDENTE" de `docs/ObservacoesProgramaTDT.txt`.

---

## 1. Filtro por coluna individual + limpar ordenação no 3º clique

**Hoje** (`src/tdt/ui/proxy_revisao.py`): só existe filtro de texto global (`setFilterKeyColumn(-1)`, busca em todas as colunas) + checkbox "esconder decididos". Ordenação por clique de cabeçalho (`tabela.setSortingEnabled(True)`) só alterna asc/desc, sem opção de "sem ordenação".

**Filtro por coluna** — `ProxyRevisao` ganha um dict de filtros por coluna, ANDado com o filtro global existente (não substitui, complementa):

```python
class ProxyRevisao(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._esconder_decididos = False
        self._filtros_coluna: dict[int, str] = {}

    def setFiltroColuna(self, col: int, texto: str) -> None:
        if texto:
            self._filtros_coluna[col] = texto.upper()
        else:
            self._filtros_coluna.pop(col, None)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._esconder_decididos:
            ...  # já existe
        for col, termo in self._filtros_coluna.items():
            idx = self.sourceModel().index(source_row, col, source_parent)
            valor = str(self.sourceModel().data(idx) or "").upper()
            if termo not in valor:
                return False
        return True
```

UI (`tela_revisao.py`): clique direito no cabeçalho da tabela abre um `QInputDialog.getText` pedindo o termo pra aquela coluna (texto vazio = remove o filtro). Sem nova classe de widget — reaproveita `QHeaderView.customContextMenuRequested`:

```python
self.tabela.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
self.tabela.horizontalHeader().customContextMenuRequested.connect(self._filtrar_coluna)

def _filtrar_coluna(self, pos):
    col = self.tabela.horizontalHeader().logicalIndexAt(pos)
    nome = ModeloSinais.COLUNAS[col]
    atual = self._proxy.filtroColuna(col)  # getter simétrico ao setter
    texto, ok = QInputDialog.getText(self, f"Filtrar '{nome}'", "Contém:", text=atual)
    if ok:
        self._proxy.setFiltroColuna(col, texto.strip())
```

**Limpar ordenação no 3º clique** — API nativa do Qt (6.5+, disponível no PySide6 6.11 já em uso):

```python
self.tabela.horizontalHeader().setSortIndicatorClearable(True)
```

Uma linha em `carregar()`. Sem código customizado de ciclo de clique.

---

## 2. Tela Inicial: limpar log + navegação em abas

**Limpar log** — botão de uma linha em `tela_inicial.py`:

```python
btn_limpar_log = QPushButton("Limpar log"); btn_limpar_log.clicked.connect(self.log.clear)
```

Colocado ao lado do label "LOG" em `col_dir`.

**Navegação em abas** — hoje (`app.py`) a troca de tela é por sinal one-way (`executou`/`abrir_config`/`voltar`), sem jeito de ir e voltar livremente entre Inicial/Revisão. Trocar o `QStackedWidget` por uma combinação de `QTabBar` fina no topo + o stack existente (mantém todo o código de cada tela intacto, só muda como a navegação é disparada):

```python
self.abas = QTabBar()
self.abas.addTab("Inicial")
self.abas.addTab("Revisão")
self.abas.currentChanged.connect(self.stack.setCurrentIndex)
```

`Config` continua fora das abas (acessada só pelo botão ⚙, como hoje — não faz sentido como aba permanente). A aba "Revisão" só fica habilitada (`setTabEnabled(1, ...)`) depois que `_ir_para_revisao()` carrega resultado pela primeira vez — antes disso não há nada pra mostrar. Trocar de aba manualmente NÃO reexecuta `tela_revisao.carregar()` (já carregado, idempotente nesse ponto).

---

## 3. Status "pendente" — classificar mesmo sem endereço + expor o motivo

**Causa raiz confirmada:** `SignalRecord.status` default é `"pendente"` (`contracts.py:105`), mas nenhum sinal real chega a ter esse valor de propósito — sinais sem endereço (`pipeline.py:248-251`) vão direto pra `ItemRevisao(motivo="sem_endereco")` **sem rodar os scorers**, então não têm candidato sugerido nenhum. Na UI, esse caso e um "score baixo" aparecem com a mesma cor/coluna Status — o único diferenciador real (`ItemRevisao.motivo`) não é exibido em lugar nenhum.

**Mudança 1 — classificar mesmo sem endereço** (`pipeline.py`, dentro do loop de `sinais`):

```python
if not rec.enderecamento.indices:
    decidido_tmp, item_tmp = _classificar_roteado(rec, disc, ana, diagnostico)
    rec_avaliado = decidido_tmp if decidido_tmp is not None else item_tmp.registro
    revisao.append(ItemRevisao(rec_avaliado, motivo="sem_endereco"))
    continue
```

Reaproveita `_classificar_roteado` (já existe, sem scoring novo) só pra preencher `candidatos`/`sigla_sinal` sugeridos — o resultado **sempre** vai pra `revisao` (nunca pra `decididos`), porque sem endereço não há o que escrever na TDT de qualquer forma. Isso atende literalmente "classificar o sinal mesmo que seja futuro": o usuário vê a sigla sugerida na tela de revisão antes mesmo do endereço existir, só não pode aprovar até o endereço ser alocado (aprovar sem endereço não tem como gerar uma linha de TDT válida — fica fora de escopo).

**Mudança 2 — coluna "Motivo" na tabela.** `AppState` (`ui/estado.py`) ganha um método que mapeia `id do registro -> motivo`, construído uma vez a partir de `self.resultado.revisao`:

```python
def motivo_por_id(self) -> dict[str, str]:
    if self.resultado is None:
        return {}
    return {item.registro.id: item.motivo for item in self.resultado.revisao}
```

`ModeloSinais.COLUNAS` ganha "Motivo" (depois de "Status"); `_texto()`:

```python
_MOTIVO_LABEL = {
    "sem_endereco": "Futuro (sem endereço)",
    "score_baixo": "Score baixo",
    "categoria_ambigua": "Categoria ambígua",
    "endereco_duplicado": "Endereço duplicado",
    "sem_fix": "Sem correção automática",
}

if nome == "Motivo":
    motivo = self._estado.motivo_por_id().get(rec.id)
    return _MOTIVO_LABEL.get(motivo, "—") if motivo else "—"
```

`# ponytail: motivo_por_id() reconstrói o dict a cada chamada — ok pro tamanho de lista atual (centenas de linhas); cachear se a tabela ficar lenta com listas grandes.`

---

## Testes

- `tests/test_ui_proxy_revisao.py`: filtro por coluna isola linhas; múltiplos filtros simultâneos (colunas diferentes) combinam em AND; filtro global + filtro por coluna juntos.
- `tests/test_pipeline.py`: sinal sem endereço aparece em `revisao` com `motivo="sem_endereco"` e `candidatos` não-vazio quando há candidato plausível (hoje seria vazio).
- `tests/test_ui_modelo_tabela.py` (ou onde existir): coluna "Motivo" mostra o label amigável certo por `ItemRevisao.motivo`; registro decidido (sem entrada em `resultado.revisao`) mostra "—".

## Critérios de Aceite

1. Filtrar 2+ colunas simultaneamente restringe a tabela pela interseção (AND).
2. 3º clique no cabeçalho de uma coluna ordenada remove a ordenação (volta à ordem original).
3. Botão "Limpar log" esvazia o `QPlainTextEdit` da Tela Inicial.
4. Usuário navega Inicial ↔ Revisão clicando nas abas, sem precisar dos botões "← Voltar"/fluxo de execução (que continuam funcionando também).
5. Sinal sem endereço aparece na tela de revisão com sigla sugerida (quando o scorer encontrar candidato plausível) e nunca é auto-aprovado.
6. Coluna "Motivo" mostra o motivo amigável pra qualquer item de revisão; "—" para decididos.
7. Testes existentes continuam verdes.
