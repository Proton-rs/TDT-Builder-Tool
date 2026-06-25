# SP — Revisão UI: Pareamento D+C, Equipamento, Add/Remover, Filtro Módulo, Formatação

**Data:** 2026-06-25
**Status:** Aguardando revisão do usuário
**Escopo:** 5 itens de melhoria da tela de revisão, em ordem de prioridade: (2) visualização/desvinculação de pareamento D+C; (4) colunas de equipamento + tipo editável + colunas rearrumáveis; (1) adicionar/remover sinais + edição geral; (3) filtro por módulo via checkboxes; (5) formatação visual do relatório de auditoria.

---

## 1. Estrutura de Pareamento (contrato)

Nova dataclass em `src/tdt/contracts.py`:

```python
@dataclass(frozen=True)
class Pareamento:
    id_status: str
    id_comando: str
    endereco_status: tuple[int, ...]
    endereco_comando: tuple[int, ...]
    indices_saida: tuple[int, ...]
```

`SignalRecord` ganha campo opcional:

```python
@dataclass(frozen=True)
class SignalRecord:
    ...
    pareamento: Pareamento | None = None
```

### 1.1 Mudança no DCPairer

Em `src/tdt/dc_pairer.py`, em vez de descartar os registros originais após fundir:

```python
def _fundir(status: SignalRecord, comando: SignalRecord) -> SignalRecord:
    return replace(
        status,
        tipo_sinal=replace(status.tipo_sinal, direcao="InputOutput"),
        enderecamento=replace(
            status.enderecamento, indices_saida=comando.enderecamento.indices
        ),
        pareamento=Pareamento(
            id_status=status.id,
            id_comando=comando.id,
            endereco_status=status.enderecamento.indices,
            endereco_comando=comando.enderecamento.indices,
            indices_saida=comando.enderecamento.indices,
        ),
    )
```

---

## 2. Item 2 — Pareamento D+C (prioridade 1)

### 2.1 Coluna "End. Saída"

`ModeloSinais.COLUNAS` ganha `"End. Saída"` entre `"Endereço"` e `"Score embedding"`.

`_texto()` para esta coluna:
```python
if nome == "End. Saída":
    p = rec.pareamento
    if p is None:
        return ""
    return ";".join(str(i) for i in p.indices_saida)
```

### 2.2 Pop-up de pareamento

Botão "Ver pareamento D+C…" na barra de topo da TelaRevisão, habilitado apenas quando a linha selecionada tem `pareamento is not None`.

`QDialog` com layout de duas colunas (Status × Comando):

```
┌────────────────────────────────────────────┐
│  Pareamento: {sigla}                       │
│                                            │
│  Status (Input)       Comando (Output)     │
│  ──────────────       ────────────────     │
│  ID: {id_status}      ID: {id_comando}     │
│  End.: {coord_in}     End.: {coord_out}    │
│  Dir.: Read           Dir.: Write          │
│  Tipo: {tipo}         Tipo: {tipo}         │
│  Fase: {fase}         Fase: {fase}         │
│                                            │
│  OUTCOORDS final: {N;N}                    │
│                                            │
│  [ Desvincular ]  [ Fechar ]               │
└────────────────────────────────────────────┘
```

Dados lidos de `rec.pareamento` + `rec` (status) + resgate do comando pelo id registrado no `Pareamento`.

### 2.3 Desvincular

Botão "Desvincular" no pop-up:

1. `AppState._snapshot()` — salva estado para undo
2. Cria dois `SignalRecord` a partir dos dados do `Pareamento`:
   - Status: registro original (Input), com `pareamento=None`
   - Comando: novo registro com `tipo_sinal.direcao="Output"`, endereço = `pareamento.endereco_comando`
3. Remove o registro pareado de `AppState.registros`
4. Insere os dois registros (status + comando) no mesmo lugar
5. Fecha pop-up, atualiza tabela

### 2.4 Repareamento manual

Quando 2 linhas estão selecionadas na tabela:

- Uma com `direcao == "Input"`, outra com `direcao == "Output"`
- Mesma `sigla_sinal` (não-None) e mesmo `modulo.nome`
- Botão "Parear" fica habilitado na barra

Ao clicar "Parear":
```python
def _reparar(self):
    linhas = self.tabela.selectionModel().selectedRows()
    if len(linhas) != 2:
        return
    r1 = self._estado.registros[self._proxy.mapToSource(linhas[0]).row()]
    r2 = self._estado.registros[self._proxy.mapToSource(linhas[1]).row()]
    input_r, output_r = (r1, r2) if r1.tipo_sinal.direcao == "Input" else (r2, r1)
    if output_r.tipo_sinal.direcao != "Output":
        QMessageBox.warning(self, "Erro", "Selecione um Input e um Output")
        return
    if input_r.sigla_sinal != output_r.sigla_sinal:
        QMessageBox.warning(self, "Erro", "Siglas diferentes — não é possível parear")
        return
    if input_r.modulo.nome != output_r.modulo.nome:
        QMessageBox.warning(self, "Erro", "Módulos diferentes — não é possível parear")
        return
    self._estado._snapshot()
    fundido = _fundir(input_r, output_r)
    # substitui as duas linhas pela fundida
    ...
```

Se validação falhar, exibe `QMessageBox.warning` com o motivo específico.

### 2.5 Contador de seleção

Label na barra inferior (ou no canto da barra de filtros):
```
Sinais: 42 total · 3 selecionados
```

Atualizado via:
```python
self.tabela.selectionModel().selectionChanged.connect(self._atualizar_contador)
```

Usa `len(self.tabela.selectionModel().selectedRows())`.

### 2.6 Undo/Redo

`AppState` ganha:

```python
@dataclass
class AppState:
    ...
    _historico: list[dict] = field(default_factory=list)  # snapshots serializados
    _indice_historico: int = -1

    def _snapshot(self) -> None:
        import copy
        if self._indice_historico < len(self._historico) - 1:
            self._historico = self._historico[:self._indice_historico + 1]
        self._historico.append({
            "registros": copy.deepcopy(self.registros),
            "resultado": self.resultado,
        })
        self._indice_historico += 1

    def desfazer(self) -> bool:
        if self._indice_historico <= 0:
            return False
        self._indice_historico -= 1
        snap = self._historico[self._indice_historico]
        self.registros = copy.deepcopy(snap["registros"])
        self.resultado = snap["resultado"]
        return True

    def refazer(self) -> bool:
        if self._indice_historico >= len(self._historico) - 1:
            return False
        self._indice_historico += 1
        snap = self._historico[self._indice_historico]
        self.registros = copy.deepcopy(snap["registros"])
        self.resultado = snap["resultado"]
        return True
```

Botões "← Desfazer" e "Refazer →" na barra de topo, desabilitados quando `desfazer()/refazer()` retorna False.

`_snapshot()` é chamado ANTES de qualquer ação que modifique `registros`: editar sigla, remover, adicionar, desvincular, parear, mudar tipo.

---

## 3. Item 4 — Colunas de equipamento + tipo editável (prioridade 2)

### 3.1 Novas colunas

`ModeloSinais.COLUNAS` atualizada:

```python
COLUNAS = [
    "Sinal", "Confiança", "Status", "Motivo", "Módulo", "Equipamento",
    "Barra", "Nível Tensão", "Fase", "Tipo", "Endereço", "End. Saída",
    "Descr. ADMS", "Descr. bruta", "Descr. normalizada",
    "Score embedding", "Score tf-idf", "Score fuzzy", "Justificativa",
]
```

`_texto()` para as novas:

```python
if nome == "Módulo":
    return rec.modulo.nome or ""
if nome == "Equipamento":
    return rec.eletrico.nome_equipamento or ""
if nome == "Barra":
    return rec.eletrico.barra or ""
if nome == "Nível Tensão":
    return rec.eletrico.nivel_tensao or ""
```

### 3.2 Tipo editável

`ModeloSinais.flags()` retorna `Qt.ItemIsEditable` para a coluna "Tipo".

Editor: `QComboBox` com opções: `Discrete/Input`, `Discrete/Output`, `Discrete/InputOutput`, `Analog/Input`.

Novo `DelegateTipo` (ou reuso do padrão em `delegate_sinal.py`):

```python
class DelegateTipo(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(["Discrete/Input", "Discrete/Output",
                        "Discrete/InputOutput", "Analog/Input"])
        return combo

    def setModelData(self, editor, model, index):
        texto = editor.currentText()
        cat, direcao = texto.split("/")
        fonte = self._proxy.mapToSource(index)
        rec = self._estado.registros[fonte.row()]
        self._estado._snapshot()
        novo = replace(rec, tipo_sinal=replace(
            rec.tipo_sinal, categoria=cat, direcao=direcao))
        self._estado.registros[fonte.row()] = novo
```

### 3.3 Colunas rearrumáveis

```python
self.tabela.horizontalHeader().setSectionsMovable(True)
```

Uma linha em `carregar()`. Persistência da ordem entre sessões (QSettings) fica como melhoria futura (`ponytail: persistir ordem de colunas via QSettings se houver demanda`).

---

## 4. Item 1 — Adicionar/Remover sinais + edição geral (prioridade 3)

### 4.1 Remover

Botão "Remover" + atalho `Delete` na TelaRevisão:
```python
def _remover(self):
    linhas = sorted(
        (self._proxy.mapToSource(idx).row() for idx in self.tabela.selectionModel().selectedRows()),
        reverse=True,
    )
    if not linhas:
        return
    if len(linhas) > 1:
        resp = QMessageBox.question(self, "Remover", f"Remover {len(linhas)} sinais?")
        if resp != QMessageBox.Yes:
            return
    self._estado._snapshot()
    for linha in linhas:
        del self._estado.registros[linha]
    self._modelo.layoutChanged.emit()
```

### 4.2 Adicionar

Botão "Adicionar sinal" → `_adicionar()`:
```python
def _adicionar(self):
    self._estado._snapshot()
    from tdt.contracts import SignalRecord, Modulo, TipoSinal, Enderecamento, Descricoes
    import uuid
    novo = SignalRecord(
        id=f"manual:{uuid.uuid4().hex[:8]}",
        modulo=Modulo(nome="", origem_contexto="manual"),
        tipo_sinal=TipoSinal("Discrete", False, "Input", True),
        enderecamento=Enderecamento("DNP3", ()),
        descricoes=Descricoes("", ""),
        status="pendente",
    )
    self._estado.registros.append(novo)
    self._modelo.layoutChanged.emit()
```

### 4.3 Edição de campos

`ModeloSinais.flags()` expandido:

```python
def flags(self, index):
    base = super().flags(index)
    nome = COLUNAS[index.column()]
    editaveis = {"Sinal", "Tipo", "Endereço", "End. Saída", "Módulo",
                 "Equipamento", "Fase", "Descr. bruta", "Barra", "Nível Tensão"}
    if nome in editaveis:
        return base | Qt.ItemIsEditable
    return base
```

`ModeloSinais.setData()`:

```python
def setData(self, index, value, role=Qt.EditRole):
    if role != Qt.EditRole or not index.isValid():
        return False
    rec = self._estado.registros[index.row()]
    nome = COLUNAS[index.column()]
    self._estado._snapshot()
    if nome == "Sinal":
        self._estado.definir_sigla(index.row(), str(value))
    elif nome == "Endereço":
        partes = tuple(int(x) for x in str(value).split(";") if x.strip())
        novo = replace(rec, enderecamento=replace(rec.enderecamento, indices=partes))
        self._estado.registros[index.row()] = novo
    elif nome == "Módulo":
        novo = replace(rec, modulo=replace(rec.modulo, nome=str(value)))
        self._estado.registros[index.row()] = novo
    elif nome == "Fase":
        novo = replace(rec, eletrico=replace(rec.eletrico, fase=str(value) or None))
        self._estado.registros[index.row()] = novo
    elif nome == "Descr. bruta":
        novo = replace(rec, descricoes=replace(rec.descricoes, bruta=str(value)))
        self._estado.registros[index.row()] = novo
    # etc.
    self.dataChanged.emit(index, index)
    return True
```

Delegates específicos por coluna (quando `setData` e `QLineEdit` padrão não são suficientes) reusam o padrão do `DelegateSinal`.

---

## 5. Item 3 — Filtro por módulo via checkboxes (prioridade 4)

### 5.1 ProxyRevisao

```python
class ProxyRevisao(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._modulos_visiveis: set[str] | None = None  # None = todos

    def setModulosVisiveis(self, modulos: set[str]) -> None:
        self._modulos_visiveis = modulos
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._modulos_visiveis is not None:
            rec = self.sourceModel()._estado.registros[source_row]
            if rec.modulo.nome not in self._modulos_visiveis:
                return False
        return True
```

### 5.2 Menu de checkboxes

No clique do cabeçalho da coluna "Módulo" (reusa `customContextMenuRequested`):

```python
def _abrir_menu_modulos(self, pos):
    col = self.tabela.horizontalHeader().logicalIndexAt(pos)
    if col < 0 or ModeloSinais.COLUNAS[col] != "Módulo":
        return
    modulos = sorted({r.modulo.nome for r in self._estado.registros if r.modulo.nome})
    menu = QMenu(self)
    todos = menu.addAction("Selecionar todos")
    todos.setCheckable(True)
    menu.addSeparator()
    for m in modulos:
        acao = menu.addAction(m)
        acao.setCheckable(True)
        acao.setChecked(m in (self._proxy._modulos_visiveis if self._proxy._modulos_visiveis else modulos))
    menu.triggered.connect(lambda acao: self._aplicar_filtro_modulos(menu, modulos))
    menu.exec(self.tabela.horizontalHeader().viewport().mapToGlobal(pos))

def _aplicar_filtro_modulos(self, menu, modulos):
    ativos = {a.text() for a in menu.actions() if a.isChecked() and a.text() in modulos}
    self._proxy.setModulosVisiveis(ativos if ativos and len(ativos) < len(modulos) else None)
```

---

## 6. Item 5 — Formatação do relatório (prioridade 5)

### 6.1 Mudanças em `relatorio_revisao.py`

Após escrever os dados e antes de salvar:

```python
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

_THIN = Side(style="thin")
_BORDA = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_FILL_CAB = PatternFill("solid", fgColor="2F5496")
_FONT_CAB = Font(bold=True, color="FFFFFF", size=10)
_FILL_VERDE = PatternFill("solid", fgColor="E8F5E9")
_FILL_VERMELHO = PatternFill("solid", fgColor="FFEBEE")
_FILL_BANDA = PatternFill("solid", fgColor="F5F5F5")


def _formatar(ws, num_cols, num_linhas, status_por_linha: dict[int, str]) -> None:
    # Cabeçalho
    for c in range(1, num_cols + 1):
        cel = ws.cell(1, c)
        cel.font = _FONT_CAB
        cel.fill = _FILL_CAB
        cel.alignment = Alignment(horizontal="center")
        cel.border = _BORDA
    # Dados
    for r in range(2, num_linhas + 1):
        status = status_por_linha.get(r)
        fill = None
        if status == "decidido":
            fill = _FILL_VERDE
        elif status == "revisao":
            fill = _FILL_VERMELHO
        elif r % 2 == 0:
            fill = _FILL_BANDA
        for c in range(1, num_cols + 1):
            cel = ws.cell(r, c)
            cel.border = _BORDA
            if fill:
                cel.fill = fill
    # Largura automática
    for c in range(1, num_cols + 1):
        max_len = max((len(str(ws.cell(r, c).value or "")) for r in range(1, num_linhas + 1)), default=8)
        ws.column_dimensions[get_column_letter(c)].width = min(max_len + 2, 60)
```

Chamado no final de `gerar_relatorio_revisao()`. `status_por_linha` mapeia número da linha (Excel) para `"decidido"` ou `"revisao"` baseado no `rec.status`.

---

## 7. Aprovação automática vs manual (alinhamento com comportamento existente)

Nenhuma mudança: sinais sem endereço continuam classificados (sigla sugerida) mas nunca auto-aprovados (`motivo="sem_endereco"`). A edição manual de sigla/tipo/endereço chama `_snapshot()` e atualiza o registro in-place.

---

## 8. Testes

| Item | Teste |
|------|-------|
| 2 | `test_dc_pairer.py`: pareamento salva `Pareamento` com ids/endereços corretos |
| 2 | `test_ui_popup_pareamento.py`: pop-up exibe dados do status + comando; "Desvincular" cria 2 registros |
| 2 | `test_ui_reparar.py`: selecionar Input+Output com mesma sigla/módulo funde; seleção inválida mostra aviso |
| 2 | `test_ui_contador.py`: contador de seleção reflete linhas selecionadas |
| 2 | `test_appstate_undo.py`: desfazer/refazer restaura registros; `_snapshot` antes de cada ação |
| 4 | `test_ui_modelo_tabela.py`: novas colunas (Módulo, Equipamento, Barra, Nível Tensão) exibem dados corretos |
| 4 | `test_ui_delegate_tipo.py`: editar tipo via combo persiste no `registro` |
| 1 | `test_ui_add_remove.py`: remover remove do AppState; adicionar cria linha vazia; undo restaura |
| 3 | `test_ui_proxy_revisao.py`: filtro por módulo esconde linhas de outros módulos; "Selecionar todos" mostra tudo |
| 5 | `test_relatorio_revisao.py`: formatação (cores, bordas, largura) aplicada corretamente |

## 9. Critérios de Aceite

1. Sinal pareado (D+C) exibe pop-up com status e comando lado a lado; "Desvincular" separa de volta.
2. Selecionar Input + Output com mesma sigla/módulo → botão "Parear" os funde; seleção inválida → aviso específico.
3. Contador mostra "N total · M selecionados" e atualiza em tempo real.
4. ← Desfazer / Refazer → restaura estado anterior em qualquer edição (sigla, tipo, adicionar, remover, desvincular, parear).
5. Colunas Módulo, Equipamento, Barra, Nível Tensão aparecem na tabela com dados de cada sinal.
6. Coluna "Tipo" é editável via combo com 4 opções; mudança persiste no registro.
7. Cabeçalhos de coluna podem ser arrastados para reordenar (setSectionsMovable).
8. Botão "Remover" apaga linha(s) selecionada(s); botão "Adicionar sinal" insere registro vazio editável.
9. Filtro por checkboxes no cabeçalho da coluna "Módulo" oculta sinais de módulos desmarcados (AND com filtros existentes).
10. `Auditoria_Revisao.xlsx` gerado com cabeçalho estilizado, cores por status, bordas e largura ajustada.
11. Testes existentes continuam verdes.
