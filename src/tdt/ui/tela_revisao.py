"""Tela de Revisão: tabela rica + painel de detalhe; aprova e gera o TDT.

ponytail: painel reflete a linha selecionada; edição vai pro AppState via modelo.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QProgressBar, QPushButton,
    QSizePolicy, QTableView, QVBoxLayout, QWidget,
)

from tdt import pipeline
from tdt.ui.busca_adms import buscar
from tdt.ui.delegate_sinal import DelegateSinal
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais, cor_faixa
from tdt.relatorio_revisao import gerar_relatorio_revisao
from tdt.ui.proxy_revisao import ProxyRevisao

_METODOS = (("emb", "vetorial"), ("tfidf", "tfidf"), ("fuzzy", "fuzzy"))


class TelaRevisao(QWidget):
    voltar = Signal()

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado
        self._linha = -1

        btn_voltar = QPushButton("← Voltar"); btn_voltar.clicked.connect(self.voltar.emit)
        btn_gerar = QPushButton("aprovar / gerar TDT")
        btn_gerar.setProperty("acao", "principal")
        btn_gerar.clicked.connect(self._gerar)

        topo = QHBoxLayout(); topo.addWidget(btn_voltar); topo.addStretch(); topo.addWidget(btn_gerar)

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
        cofre.setLayout(painel); cofre.setFixedWidth(280)

        # --- tabela ---
        self.tabela = QTableView()
        self.tabela.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.tabela.setHorizontalScrollMode(QTableView.ScrollPerPixel)
        self.tabela.setSelectionBehavior(QTableView.SelectRows)
        self.tabela.setAlternatingRowColors(True)

        self.chk_so_revisao = QCheckBox("Mostrar apenas revisão")
        self.chk_so_revisao.toggled.connect(self._filtrar_status)
        self.ed_filtro = QLineEdit()
        self.ed_filtro.setPlaceholderText("Filtrar (todas as colunas)…")
        self.ed_filtro.textChanged.connect(self._filtrar_texto)
        barra_filtro = QHBoxLayout()
        barra_filtro.addWidget(self.chk_so_revisao)
        barra_filtro.addWidget(self.ed_filtro, 1)

        corpo = QHBoxLayout(); corpo.addWidget(cofre); corpo.addWidget(self.tabela, 1)
        raiz = QVBoxLayout(self)
        raiz.addLayout(topo)
        raiz.addLayout(barra_filtro)
        raiz.addLayout(corpo, 1)

    def carregar(self) -> None:
        self._modelo = ModeloSinais(self._estado)
        self._proxy = ProxyRevisao(self)
        self._proxy.setSourceModel(self._modelo)
        self._proxy.setFilterKeyColumn(-1)
        self.tabela.setModel(self._proxy)
        self.tabela.setSortingEnabled(True)
        self.tabela.horizontalHeader().setSortIndicatorClearable(True)
        self.tabela.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.tabela.horizontalHeader().customContextMenuRequested.connect(self._filtrar_coluna)
        self.tabela.setEditTriggers(QTableView.DoubleClicked)
        col_sinal = ModeloSinais.COLUNAS.index("Sinal")
        self.tabela.setItemDelegateForColumn(
            col_sinal, DelegateSinal(self._estado, self._modelo, self._proxy, self.tabela))
        self.tabela.selectionModel().currentRowChanged.connect(self._linha_mudou)

    def _linha_mudou(self, atual, _anterior):
        fonte = self._proxy.mapToSource(atual)
        self._linha = fonte.row()
        self._atualizar_painel()

    def _filtrar_status(self, ativo: bool) -> None:
        self._proxy.setEsconderDecididos(ativo)

    def _filtrar_texto(self, termo: str) -> None:
        self._proxy.setFilterFixedString(termo)

    def _filtrar_coluna(self, pos) -> None:
        col = self.tabela.horizontalHeader().logicalIndexAt(pos)
        if col < 0:
            return
        if self._eh_coluna_modulo(col):
            menu = self._construir_menu_coluna(col, pos)
            menu.exec(self.tabela.horizontalHeader().viewport().mapToGlobal(pos))
            return
        nome = ModeloSinais.COLUNAS[col]
        atual = self._proxy.filtroColuna(col)
        texto, ok = QInputDialog.getText(self, f"Filtrar '{nome}'", "Contém:", text=atual)
        if ok:
            self._proxy.setFiltroColuna(col, texto.strip())

    def _eh_coluna_modulo(self, col: int) -> bool:
        return col == ModeloSinais.COLUNAS.index("Módulo")

    def _construir_menu_coluna(self, col: int, _pos) -> QMenu:
        """Menu de checkboxes com os módulos distintos presentes nos registros.

        ponytail: single-select (cada clique substitui o filtro anterior via
        setFiltroColuna). Multi-select exigiria estender ProxyRevisao pra
        aceitar uma lista de valores aceitos por coluna — não fazemos isso
        agora porque o caso de uso atual (isolar um módulo por vez) não pede.
        """
        menu = QMenu(self)
        modulos = sorted({
            r.modulo.nome for r in self._estado.registros
            if r.modulo and r.modulo.nome
        })
        filtro_atual = self._proxy.filtroColuna(col)
        for mod in modulos:
            acao = menu.addAction(mod)
            acao.setCheckable(True)
            acao.setChecked(mod.upper() == filtro_atual.upper())
            acao.triggered.connect(lambda _checked=False, m=mod: self._proxy.setFiltroColuna(col, m))
        menu.addSeparator()
        acao_limpar = menu.addAction("Limpar Filtro")
        acao_limpar.triggered.connect(lambda: self._proxy.setFiltroColuna(col, ""))
        return menu

    def _registro(self):
        if 0 <= self._linha < len(self._estado.registros):
            return self._estado.registros[self._linha]
        return None

    def _atualizar_painel(self):
        r = self._registro()
        if r is None:
            return
        conf = f"{r.candidatos[0].score:.2f}" if r.candidatos else "—"
        self.lbl_campos.setText(
            f"Sinal: {r.sigla_sinal or '—'}\n"
            f"Status: {r.status}\n"
            f"Confiança: {conf}\n"
            f"Tipo: {r.tipo_sinal.categoria}/{r.tipo_sinal.direcao}\n"
            f"Fase: {r.eletrico.fase or '—'}\n"
            f"Endereço: {';'.join(str(i) for i in r.enderecamento.indices)}\n"
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
            gerar_relatorio_revisao(self._estado.registros, revisao, output)
            QMessageBox.information(
                self, "Sucesso",
                f"TDT gerado: {out_path}\nAuditoria: {Path(output) / 'Auditoria_Revisao.xlsx'}",
            )
        except Exception as e:  # ponytail: erro vira dialogo; sem retry
            QMessageBox.critical(self, "Erro", f"Falha ao gerar TDT: {e}")
