"""Tela de Revisão: tabela rica + painel de detalhe; aprova e gera o TDT.

ponytail: painel reflete a linha selecionada; edição vai pro AppState via modelo.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QSettings, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QMessageBox, QProgressBar,
    QPushButton, QSizePolicy, QSplitter, QTableView, QTabBar, QVBoxLayout, QWidget,
)

from tdt import pipeline
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.dc_pairer import fundir, separar
from tdt.ui.busca_adms import buscar
from tdt.ui.delegate_sinal import DelegateCombo, DelegateModulo, DelegateSinal
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais, cor_faixa
from tdt.relatorio_revisao import gerar_relatorio_revisao
from tdt.ui.proxy_revisao import ProxyRevisao

_METODOS = (("emb", "vetorial"), ("tfidf", "tfidf"), ("fuzzy", "fuzzy"))

_COLUNAS_PADRAO = frozenset({
    "Sinal", "Confiança", "Status", "Motivo", "Descr. bruta",
    "Descr. ADMS", "Módulo", "Endereço",
})

_OPCOES_COMBO = {
    "Tipo": ["Discrete/Input", "Discrete/Output", "Discrete/InputOutput",
             "Analog/Input", "Analog/Output"],
    "Fase": ["", "A", "B", "C", "N", "AB", "BC", "CA", "ABC"],
    "Nível Tensão": ["", "AT", "BT"],
    "Barra": ["", "Principal", "Auxiliar"],
    "Tipo Equip.": ["", "Disjuntor", "Seccionadora"],
}


def decidir_acao_pareamento(registros: list[SignalRecord]):
    """Decide, a partir da seleção atual, qual ação de pareamento é possível.

    Função pura (sem Qt) para ser testável sem abrir diálogos. Retorna uma
    tupla ``(acao, dados)``:
    - ``("parear", (status, comando))`` — exatamente 1 Input + 1 Output.
    - ``("desvincular", fundido)`` — exatamente 1 registro já InputOutput.
    - ``("erro", mensagem)`` — seleção inválida (mostrar aviso amigável).
    """
    if len(registros) == 1:
        rec = registros[0]
        if rec.tipo_sinal.direcao == "InputOutput":
            return ("desvincular", rec)
        return (
            "erro",
            "Selecione 1 sinal já pareado (Input/Output) para desvincular, "
            "ou 2 sinais (1 status + 1 comando) para parear.",
        )
    if len(registros) == 2:
        inputs = [r for r in registros if r.tipo_sinal.direcao == "Input"]
        outputs = [r for r in registros if r.tipo_sinal.direcao == "Output"]
        if len(inputs) == 1 and len(outputs) == 1:
            return ("parear", (inputs[0], outputs[0]))
        return (
            "erro",
            "Para parear, selecione exatamente 1 sinal Input (status) e "
            "1 sinal Output (comando).",
        )
    return (
        "erro",
        "Selecione 1 sinal pareado (desvincular) ou 2 sinais — 1 status e "
        "1 comando (parear).",
    )


class FiltroColunaDialog(QDialog):
    """Popup estilo Excel: busca + lista checkable de valores distintos.

    ponytail: só wiring -- toda a lógica de filtro (quais linhas passam,
    valores distintos) vive no ProxyRevisao (`valores_unicos`,
    `set_filtro_coluna`). Este diálogo apenas coleta o que o usuário marcou
    e repassa; não sabe nada sobre SignalRecord nem sobre o modelo fonte.
    """

    def __init__(self, nome_coluna: str, valores: list[str], selecionados: set[str] | None, contem_inicial: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Filtrar '{nome_coluna}'")
        self._valores = valores
        marcar_tudo = selecionados is None

        self.ed_contem = QLineEdit(contem_inicial)
        self.ed_contem.setPlaceholderText("contém… (texto livre)")

        self.busca = QLineEdit()
        self.busca.setPlaceholderText("buscar...")
        self.busca.textChanged.connect(self._filtrar_lista)

        self.chk_todos = QCheckBox("Selecionar tudo")
        self.chk_todos.setTristate(False)
        self.chk_todos.toggled.connect(self._alternar_tudo)

        self.lista = QListWidget()
        for v in valores:
            item = QListWidgetItem(v)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            marcado = marcar_tudo or v in selecionados
            item.setCheckState(Qt.Checked if marcado else Qt.Unchecked)
            self.lista.addItem(item)
        self.chk_todos.setChecked(all(
            self.lista.item(i).checkState() == Qt.Checked for i in range(self.lista.count())
        ) if self.lista.count() else True)

        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        btn_limpar = QPushButton("Limpar Filtro")
        btn_limpar.clicked.connect(self._limpar)
        botoes.addButton(btn_limpar, QDialogButtonBox.ResetRole)

        layout = QVBoxLayout(self)
        layout.addWidget(self.ed_contem)
        layout.addWidget(self.busca)
        layout.addWidget(self.chk_todos)
        layout.addWidget(self.lista)
        layout.addWidget(botoes)

        self._limpo = False

    def _filtrar_lista(self, termo: str) -> None:
        termo = termo.strip().upper()
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            item.setHidden(bool(termo) and termo not in item.text().upper())

    def _alternar_tudo(self, marcado: bool) -> None:
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if not item.isHidden():
                item.setCheckState(Qt.Checked if marcado else Qt.Unchecked)

    def _limpar(self) -> None:
        self._limpo = True
        self.accept()

    def valores_selecionados(self) -> set[str] | None:
        """`None` = sem filtro (limpar ou tudo marcado); senão o conjunto marcado."""
        if self._limpo:
            return None
        marcados = {
            self.lista.item(i).text()
            for i in range(self.lista.count())
            if self.lista.item(i).checkState() == Qt.Checked
        }
        if len(marcados) == len(self._valores):
            return None
        return marcados

    def texto_contem(self) -> str:
        return "" if self._limpo else self.ed_contem.text().strip()


class PareamentoDialog(QDialog):
    """Confirmação simples: mostra os sinais selecionados e a ação proposta."""

    def __init__(self, acao: str, descricao: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pareamento D+C")
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(descricao))
        rotulo_botao = "Parear" if acao == "parear" else "Desvincular"
        botoes = QDialogButtonBox(QDialogButtonBox.Cancel)
        botoes.addButton(rotulo_botao, QDialogButtonBox.AcceptRole)
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)


class TelaRevisao(QWidget):
    voltar = Signal()
    desfazer_pedido = Signal()
    pendentes_mudaram = Signal(int)

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado
        self._linha = -1
        self._selecao_filtro_coluna: dict[int, set[str]] = {}

        btn_voltar = QPushButton("← Voltar"); btn_voltar.clicked.connect(self.voltar.emit)
        btn_desfazer = QPushButton("↶ Desfazer (Ctrl+Z)")
        btn_desfazer.clicked.connect(self.desfazer_pedido.emit)
        btn_remover = QPushButton("Remover Sinal"); btn_remover.clicked.connect(self._remover_sinais)
        btn_adicionar = QPushButton("Adicionar Sinal"); btn_adicionar.clicked.connect(self._adicionar_sinal)
        btn_parear = QPushButton("Parear D+C"); btn_parear.clicked.connect(self._parear_sinais)
        btn_gerar = QPushButton("Gerar TDT…")
        btn_gerar.clicked.connect(self._gerar)
        self.btn_aprovar = QPushButton("Aprovar e ir ao próximo (Enter)")
        self.btn_aprovar.setProperty("acao", "principal")
        self.btn_aprovar.clicked.connect(lambda: self._aprovar_e_proximo())

        topo = QHBoxLayout()
        topo.addWidget(btn_voltar)
        topo.insertWidget(1, btn_desfazer)
        topo.addStretch()
        topo.addWidget(btn_remover)
        topo.addWidget(btn_adicionar)
        topo.addWidget(btn_parear)
        topo.addWidget(self.btn_aprovar)
        topo.addWidget(btn_gerar)

        # --- painel de detalhe ---
        self.lbl_campos = QLabel("Selecione um sinal"); self.lbl_campos.setWordWrap(True)

        self.barras: list[QProgressBar] = []
        cx_scores = QVBoxLayout()
        for rotulo, _chave in _METODOS:
            linha = QHBoxLayout()
            linha.addWidget(QLabel(rotulo))
            barra = QProgressBar(); barra.setRange(0, 100); barra.setTextVisible(True)
            barra.setFixedHeight(14)
            self.barras.append(barra)
            linha.addWidget(barra, 1)
            cx_scores.addLayout(linha)

        self.lista_candidatos = QListWidget()
        self.lista_candidatos.itemClicked.connect(self._escolher_candidato)

        self.busca = QLineEdit(); self.busca.setPlaceholderText("buscar na Lista Padrão ADMS…")
        self.busca.textChanged.connect(self.buscar_adms)
        self.lista_resultados = QListWidget()
        self.lista_resultados.itemClicked.connect(self._escolher_resultado)

        painel = QVBoxLayout()
        painel.addWidget(QLabel("DETALHE DO SINAL"))
        painel.addWidget(self.lbl_campos)
        painel.addWidget(QLabel("Scores por método"))
        painel.addLayout(cx_scores)
        painel.addWidget(QLabel("Candidatos"))
        painel.addWidget(self.lista_candidatos)
        painel.addWidget(QLabel("Buscar na Lista Padrão ADMS"))
        painel.addWidget(self.busca)
        painel.addWidget(self.lista_resultados)
        cofre = QWidget(); cofre.setObjectName("painelDetalhe")
        cofre.setLayout(painel); cofre.setMinimumWidth(220)

        # --- tabela ---
        self.tabela = QTableView()
        self.tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabela.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.tabela.setSelectionBehavior(QTableView.SelectRows)
        self.tabela.setAlternatingRowColors(True)

        self.grupo_status = QButtonGroup(self)
        self._status_por_id = {0: None, 1: "revisao", 2: "decidido"}
        botoes_status = QHBoxLayout()
        for i, rotulo in enumerate(("Todos", "Pendentes", "Decididos")):
            b = QPushButton(rotulo)
            b.setCheckable(True)
            if i == 0:
                b.setChecked(True)
            self.grupo_status.addButton(b, i)
            botoes_status.addWidget(b)
        self.grupo_status.idClicked.connect(self._filtrar_status_id)
        self.lbl_selecao = QLabel("0 selecionados")
        barra_filtro = QHBoxLayout()
        barra_filtro.addLayout(botoes_status)
        barra_filtro.addStretch()
        self.btn_colunas = QPushButton("Colunas ▾")
        barra_filtro.addWidget(self.btn_colunas)
        self.btn_limpar_filtros = QPushButton("")
        self.btn_limpar_filtros.setVisible(False)
        self.btn_limpar_filtros.clicked.connect(self._limpar_filtros)
        barra_filtro.addWidget(self.btn_limpar_filtros)
        barra_filtro.addWidget(self.lbl_selecao)

        self.abas_sheet = QTabBar()
        self.abas_sheet.addTab("Tudo")
        self.abas_sheet.currentChanged.connect(self._trocar_aba_sheet)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(cofre)
        self.splitter.addWidget(self.tabela)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([280, 920])
        raiz = QVBoxLayout(self)
        raiz.addLayout(topo)
        raiz.addWidget(self.abas_sheet)
        raiz.addLayout(barra_filtro)
        raiz.addWidget(self.splitter, 1)

        # Atalhos de teclado
        for tecla in (Qt.Key_Return, Qt.Key_Enter):
            atalho = QShortcut(QKeySequence(tecla), self.tabela)
            atalho.setContext(Qt.WidgetShortcut)
            atalho.activated.connect(lambda: self._aprovar_e_proximo())
        for n in range(1, 6):
            atalho = QShortcut(QKeySequence(str(n)), self.tabela)
            atalho.setContext(Qt.WidgetShortcut)
            atalho.activated.connect(
                lambda n=n: self._aprovar_e_proximo(n - 1))
        atalho_busca = QShortcut(QKeySequence.Find, self)
        atalho_busca.activated.connect(self.busca.setFocus)

    def _rotulo_aba(self, nome: str, pendentes: int) -> str:
        return f"{nome} ✓" if pendentes == 0 else f"{nome} · {pendentes}"

    def _atualizar_abas_sheet(self) -> None:
        if not hasattr(self, "_modelo"):
            return
        contagem = self._modelo.pendentes_por_sheet()
        total = sum(contagem.values())
        self.abas_sheet.setTabText(0, self._rotulo_aba("Tudo", total))
        for i in range(1, self.abas_sheet.count()):
            sheet = self.abas_sheet.tabData(i)
            self.abas_sheet.setTabText(
                i, self._rotulo_aba(sheet, contagem.get(sheet, 0)))
        self.pendentes_mudaram.emit(total)

    def carregar(self) -> None:
        self._modelo = ModeloSinais(self._estado)
        self._proxy = ProxyRevisao(self)
        self._proxy.setSourceModel(self._modelo)
        self._popular_abas_sheet()
        self.tabela.setModel(self._proxy)
        self.tabela.setSortingEnabled(True)
        self.tabela.horizontalHeader().setSortIndicatorClearable(True)
        self.tabela.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabela.horizontalHeader().customContextMenuRequested.connect(self._filtrar_coluna)
        self.tabela.setEditTriggers(QTableView.DoubleClicked)
        self.tabela.horizontalHeader().setSectionsMovable(True)  # arrastar colunas
        col_sinal = ModeloSinais.COLUNAS.index("Sinal")
        self.tabela.setItemDelegateForColumn(
            col_sinal, DelegateSinal(self._estado, self._modelo, self._proxy, self.tabela))
        for nome, opcoes in _OPCOES_COMBO.items():
            col = ModeloSinais.COLUNAS.index(nome)
            self.tabela.setItemDelegateForColumn(col, DelegateCombo(opcoes, self.tabela))
        col_modulo = ModeloSinais.COLUNAS.index("Módulo")
        self.tabela.setItemDelegateForColumn(col_modulo, DelegateModulo(self._estado, self.tabela))
        self.tabela.selectionModel().currentRowChanged.connect(self._linha_mudou)
        self.tabela.selectionModel().selectionChanged.connect(self._atualizar_selecao)
        self._modelo.dataChanged.connect(lambda *_: self._atualizar_abas_sheet())
        self._modelo.rowsInserted.connect(lambda *_: self._atualizar_abas_sheet())
        self._modelo.rowsRemoved.connect(lambda *_: self._atualizar_abas_sheet())
        self._atualizar_abas_sheet()
        self._atualizar_chip_filtros()
        settings = QSettings("tdt", "ui")
        estado_header = settings.value("revisao_header_state")
        header = self.tabela.horizontalHeader()
        if estado_header is not None and header.count() == len(ModeloSinais.COLUNAS):
            header.restoreState(estado_header)
        else:
            for i, nome in enumerate(ModeloSinais.COLUNAS):
                self.tabela.setColumnHidden(i, nome not in _COLUNAS_PADRAO)
        estado_splitter = settings.value("revisao_splitter_state")
        if estado_splitter is not None:
            self.splitter.restoreState(estado_splitter)
        self._montar_menu_colunas()

    def refresh(self) -> None:
        """Re-sincroniza a view após mutação externa de registros (ex.: undo)."""
        if not hasattr(self, "_modelo"):
            return
        self._modelo.beginResetModel()
        self._modelo.endResetModel()
        self._atualizar_painel()
        self._atualizar_abas_sheet()

    def _atualizar_selecao(self, *_args) -> None:
        n = len(self.tabela.selectionModel().selectedRows())
        self.lbl_selecao.setText(f"{n} selecionado" + ("" if n == 1 else "s"))

    def _linha_mudou(self, atual, _anterior):
        fonte = self._proxy.mapToSource(atual)
        self._linha = fonte.row()
        self._atualizar_painel()

    def _filtrar_status_id(self, id_botao: int) -> None:
        if hasattr(self, "_proxy"):
            self._proxy.set_status_visivel(self._status_por_id[id_botao])

    def mostrar_pendentes(self) -> None:
        """Ativa o filtro Pendentes (usado pela tela de Geração)."""
        self.grupo_status.button(1).setChecked(True)
        self._filtrar_status_id(1)

    def _popular_abas_sheet(self) -> None:
        """Uma aba por sheet distinta presente nos registros + "Tudo" (primeira).

        ponytail: reconstrói o QTabBar do zero a cada carregar() -- não há
        recarga incremental de sheets nesta tela, então não vale a pena
        diffar contra o estado anterior.
        """
        self.abas_sheet.blockSignals(True)
        while self.abas_sheet.count() > 0:
            self.abas_sheet.removeTab(0)
        self.abas_sheet.addTab("Tudo")
        for sheet in self._modelo.sheets_distintas():
            i = self.abas_sheet.addTab(sheet)
            self.abas_sheet.setTabData(i, sheet)
        self.abas_sheet.blockSignals(False)
        self.abas_sheet.setCurrentIndex(0)
        self._proxy.set_sheet(None)

    def _trocar_aba_sheet(self, indice: int) -> None:
        nome = None if indice <= 0 else self.abas_sheet.tabData(indice)
        self._proxy.set_sheet(nome)

    def _filtrar_coluna(self, pos) -> None:
        col = self.tabela.horizontalHeader().logicalIndexAt(pos)
        if col < 0:
            return
        nome = ModeloSinais.COLUNAS[col]
        valores = self._proxy.valores_unicos(col)
        atuais = self._selecao_filtro_coluna.get(col)
        dialog = FiltroColunaDialog(
            nome, valores, atuais,
            contem_inicial=self._proxy.filtroColuna(col), parent=self)
        if dialog.exec() != QDialog.Accepted:
            return
        novos = dialog.valores_selecionados()
        self._proxy.set_filtro_coluna(col, novos)
        self._proxy.setFiltroColuna(col, dialog.texto_contem())
        if novos is None:
            self._selecao_filtro_coluna.pop(col, None)
        else:
            self._selecao_filtro_coluna[col] = novos
        self._atualizar_chip_filtros()


    def _atualizar_chip_filtros(self) -> None:
        n = self._proxy.filtros_ativos()
        self.btn_limpar_filtros.setText(f"Filtros ativos: {n} — limpar todos")
        self.btn_limpar_filtros.setVisible(n > 0)

    def _limpar_filtros(self) -> None:
        self._proxy.limpar_filtros()
        self._selecao_filtro_coluna.clear()
        self._atualizar_chip_filtros()

    def filtrar_endereco(self, texto: str) -> None:
        """Filtro "contém" na coluna Endereço (usado pela tela de Geração)."""
        col = ModeloSinais.COLUNAS.index("Endereço")
        self._proxy.setFiltroColuna(col, texto)
        self._atualizar_chip_filtros()

    def _registro(self):
        if 0 <= self._linha < len(self._estado.registros):
            return self._estado.registros[self._linha]
        return None

    def _atualizar_painel(self):
        r = self._registro()
        if r is None:
            return
        conf = f"{r.candidatos[0].score:.2f}" if r.candidatos else "—"
        end_in = ";".join(str(i) for i in r.enderecamento.indices) or "—"
        end_out = ";".join(str(i) for i in r.enderecamento.indices_saida) or "—"
        self.lbl_campos.setText(
            f"Sinal: {r.sigla_sinal or '—'}\n"
            f"Status: {r.status}\n"
            f"Confiança: {conf}\n"
            f"Tipo: {r.tipo_sinal.categoria}/{r.tipo_sinal.direcao}\n"
            f"Fase: {r.eletrico.fase or '—'}\n"
            f"Endereço Input: {end_in}\n"
            f"Endereço Output: {end_out}\n"
            f"Descrição: {r.descricoes.bruta}"
        )
        self._atualizar_barras(r)
        self._atualizar_candidatos(r)

    def _atualizar_barras(self, r):
        diag = r.diagnostico
        sigla = r.sigla_sinal
        for (_, chave), barra in zip(_METODOS, self.barras):
            v = None
            if diag is not None and sigla is not None:
                v = diag.scores_por_metodo.get(sigla, {}).get(chave)
            pct = int(round((v or 0.0) * 100))
            barra.setValue(pct)
            barra.setFormat(f"{v:.2f}" if v is not None else "—")
            cor = cor_faixa(v)
            if cor is not None:
                barra.setStyleSheet(f"QProgressBar::chunk {{ background-color: {cor.name()}; }}")

    def _atualizar_candidatos(self, r):
        self.lista_candidatos.clear()
        lp = self._estado.lista_padrao
        if not r.candidatos:
            it = QListWidgetItem("sem candidatos — use a busca")
            it.setFlags(Qt.NoItemFlags)
            self.lista_candidatos.addItem(it)
            return
        for c in r.candidatos:
            sp = lp.por_sigla(c.sigla) if lp else None
            desc = f" — {sp.descricao}" if sp else ""
            it = QListWidgetItem(f"{c.sigla} ({c.score:.3f}){desc}")
            it.setData(Qt.UserRole, c.sigla)
            if sp:
                it.setToolTip(sp.descricao)
            self.lista_candidatos.addItem(it)

    def buscar_adms(self, termo: str):
        self.lista_resultados.clear()
        lp = self._estado.lista_padrao
        if lp is None or not termo.strip():
            return
        for sp in buscar(lp, termo, limite=30):
            it = QListWidgetItem(f"{sp.sigla}  ·  {sp.categoria}  —  {sp.descricao}")
            it.setData(Qt.UserRole, sp.sigla)
            it.setToolTip(sp.descricao)
            self.lista_resultados.addItem(it)

    def _escolher_candidato(self, item):
        sigla = item.data(Qt.UserRole)
        if self._linha >= 0 and sigla:
            self._modelo.definir_sigla(self._linha, sigla)
            self._atualizar_painel()

    def _escolher_resultado(self, item):
        sigla = item.data(Qt.UserRole)
        if self._linha >= 0 and sigla:
            self._modelo.definir_sigla(self._linha, sigla)
            self._atualizar_painel()

    def _gerar(self):
        lp = self._estado.lista_padrao
        template = self._estado.paths.get("template", "")
        output = self._estado.paths.get("output", "")
        if not lp or not template or not output:
            QMessageBox.warning(self, "Erro", "Lista padrão, template e output são obrigatórios")
            return
        try:
            wb = pipeline.gerar_tdt(
                self._estado.registros, template, lp,
                subestacao=self._estado.subestacao, aliases=self._estado.aliases,
            )
            out_path = Path(output) / "TDT.xlsx"
            wb.save(str(out_path))
            revisao = self._estado.resultado.revisao if self._estado.resultado else ()
            diag = self._estado.resultado.diagnostico if self._estado.resultado else {}
            gerar_relatorio_revisao(self._estado.registros, revisao, output, diagnostico=diag)
            QMessageBox.information(
                self, "Sucesso",
                f"TDT gerado: {out_path}\nAuditoria: {Path(output) / 'Auditoria_Revisao.xlsx'}",
            )
        except Exception as e:  # ponytail: erro vira dialogo; sem retry
            QMessageBox.critical(self, "Erro", f"Falha ao gerar TDT: {e}")

    def _remover_sinais(self):
        selecionadas = self.tabela.selectionModel().selectedRows()
        if not selecionadas:
            return
        indices = [self._proxy.mapToSource(idx).row() for idx in selecionadas]
        self._estado._snapshot()
        self._modelo.remover_linhas(indices)

    def _adicionar_sinal(self):
        self._estado._snapshot()
        registro = SignalRecord(
            id=f"manual_{uuid.uuid4().hex[:8]}",
            modulo=Modulo(None, "manual"),
            tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
            enderecamento=Enderecamento("DNP3", ()),
            descricoes=Descricoes("", ""),
        )
        self._modelo.adicionar_registro(registro)

    def _linhas_selecionadas(self) -> list[int]:
        selecionadas = self.tabela.selectionModel().selectedRows()
        return [self._proxy.mapToSource(idx).row() for idx in selecionadas]

    def _parear_sinais(self):
        indices = self._linhas_selecionadas()
        if not indices:
            return
        registros = [self._estado.registros[i] for i in indices]
        acao, dados = decidir_acao_pareamento(registros)
        if acao == "erro":
            QMessageBox.warning(self, "Pareamento D+C", dados)
            return
        descricao = self._descricao_confirmacao(acao, dados)
        if not self._confirmar_dialogo(acao, descricao):
            return
        self._estado._snapshot()
        if acao == "parear":
            status, comando = dados
            fundido_rec = fundir(status, comando)
            self._modelo.remover_linhas(indices)
            self._modelo.adicionar_registro(fundido_rec)
        else:  # desvincular
            # ponytail: id sintético com sufixo aleatório — evita colisão se o
            # mesmo registro for desvinculado mais de uma vez (ex.: desfazer +
            # refazer manual) sem remover o comando recriado anteriormente.
            novo_id_saida = f"{dados.id}_saida_{uuid.uuid4().hex[:6]}"
            status_rec, comando_rec = separar(dados, novo_id_saida)
            self._modelo.remover_linhas(indices)
            self._modelo.adicionar_registro(status_rec)
            self._modelo.adicionar_registro(comando_rec)

    def _descricao_confirmacao(self, acao: str, dados) -> str:
        if acao == "parear":
            status, comando = dados
            return (
                f"Parear status {status.sigla_sinal or status.id} "
                f"(Input, end. {status.enderecamento.indices}) com comando "
                f"{comando.sigla_sinal or comando.id} (Output, end. "
                f"{comando.enderecamento.indices})?"
            )
        end_in = ";".join(str(i) for i in dados.enderecamento.indices)
        end_out = ";".join(str(i) for i in dados.enderecamento.indices_saida)
        return (
            f"Desvincular {dados.sigla_sinal or dados.id} (InputOutput, "
            f"end. Input: {end_in} / end. Output: {end_out}) "
            f"em Input + Output separados?"
        )

    def _confirmar_dialogo(self, acao: str, descricao: str) -> bool:
        """Exibe o diálogo de confirmação. Isolado em método próprio para que
        os testes substituam só esta camada (sem tocar QDialog.exec nativo).
        """
        dialog = PareamentoDialog(acao, descricao, self)
        return dialog.exec() == QDialog.Accepted

    def _proximo_pendente(self, apos_linha_proxy: int) -> int:
        """Próxima linha visível no proxy com status "revisao" (com wrap)."""
        total = self._proxy.rowCount()
        if total == 0:
            return -1
        col_status = ModeloSinais.COLUNAS.index("Status")
        for delta in range(1, total + 1):
            linha = (apos_linha_proxy + delta) % total
            if self._proxy.index(linha, col_status).data() == "revisao":
                return linha
        return -1

    def _aprovar_e_proximo(self, indice_candidato: int | None = None) -> None:
        if not hasattr(self, "_proxy"):
            return
        r = self._registro()
        if r is None:
            return
        if indice_candidato is not None:
            if indice_candidato >= len(r.candidatos):
                QApplication.beep()
                return
            sigla = r.candidatos[indice_candidato].sigla
        else:
            item = self.lista_candidatos.currentItem()
            sigla = item.data(Qt.UserRole) if item else None
            if not sigla and r.candidatos:
                sigla = r.candidatos[0].sigla
        if not sigla:
            QApplication.beep()
            return
        atual = self.tabela.selectionModel().currentIndex()
        linha_proxy = atual.row() if atual.isValid() else -1
        self._modelo.definir_sigla(self._linha, sigla)
        proxima = self._proximo_pendente(linha_proxy)
        if proxima >= 0:
            self.tabela.selectRow(proxima)
        else:
            self._atualizar_painel()

    def _montar_menu_colunas(self) -> None:
        menu = QMenu(self.btn_colunas)
        for i, nome in enumerate(ModeloSinais.COLUNAS):
            acao = menu.addAction(nome)
            acao.setCheckable(True)
            acao.setChecked(not self.tabela.isColumnHidden(i))
            acao.toggled.connect(
                lambda visivel, c=i: self.tabela.setColumnHidden(c, not visivel))
        self.btn_colunas.setMenu(menu)

    def hideEvent(self, event):
        if hasattr(self, "_proxy"):
            settings = QSettings("tdt", "ui")
            settings.setValue(
                "revisao_header_state", self.tabela.horizontalHeader().saveState())
            settings.setValue("revisao_splitter_state", self.splitter.saveState())
        super().hideEvent(event)
