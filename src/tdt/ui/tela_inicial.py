"""Tela Inicial: configura e dispara o pipeline; LOG ao vivo; PARAR.

ponytail: lê sheets com openpyxl read_only; worker injetável p/ teste.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QGroupBox, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit,
    QProgressBar, QPushButton, QRadioButton, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Qt

from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT
from tdt.ui.estado import AppState
from tdt.ui.worker import PipelineWorker

_MODOS = [("Automático (detecta pelo header)", "auto"),
          ("Homogêneo", "homogeneo"),
          ("Não homogêneo", "nao-homogeneo")]


class TelaInicial(QWidget):
    abrir_config = Signal()
    executou = Signal()

    def __init__(self, estado: AppState, worker_factory=PipelineWorker):
        super().__init__()
        self._estado = estado
        self._worker_factory = worker_factory
        self._worker = None

        self.ed_input = QLineEdit()
        self.ed_input.setReadOnly(True)
        self.ed_input.setPlaceholderText("Nenhum arquivo de entrada selecionado")
        btn_in = QPushButton("Input…"); btn_in.clicked.connect(self._escolher_input)

        self.ed_output = QLineEdit()
        self.ed_output.setReadOnly(True)
        self.ed_output.setPlaceholderText("Nenhuma pasta de saída selecionada")
        btn_out = QPushButton("Output…"); btn_out.clicked.connect(self._escolher_output)

        self.combo_proto = QComboBox(); self.combo_proto.addItem("DNP3")
        self.grupo_modo = QButtonGroup(self)
        cx_modo = QVBoxLayout()
        for i, (rotulo, _val) in enumerate(_MODOS):
            rb = QRadioButton(rotulo)
            if i == 0:
                rb.setChecked(True)
            self.grupo_modo.addButton(rb, i)
            cx_modo.addWidget(rb)

        self.chk_pular = QCheckBox("Pular revisão manual")
        self.chk_aprovar = QCheckBox("Aprovar auto. acima do threshold")
        self.chk_aprovar.setChecked(estado.flags.get("aprovar_acima_threshold", True))

        self.combo_sub = QComboBox(); self.combo_sub.setEditable(True)
        self.combo_sub.lineEdit().setPlaceholderText("Obrigatório — sigla da subestação")

        self.lista_sheets = QListWidget()
        self.lista_sheets.itemChanged.connect(self._sheet_renomeada)

        self.btn_executar = QPushButton("EXECUTAR"); self.btn_executar.clicked.connect(self._executar)
        self.btn_executar.setProperty("acao", "principal")
        self.btn_parar = QPushButton("PARAR"); self.btn_parar.clicked.connect(self._parar)
        self.btn_parar.setEnabled(False)
        btn_cfg = QPushButton("⚙"); btn_cfg.clicked.connect(self.abrir_config.emit)

        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.btn_limpar_log = QPushButton("Limpar log")
        self.btn_limpar_log.clicked.connect(self.log.clear)

        self.progresso_bar = QProgressBar()
        self.progresso_bar.setVisible(False)

        col_esq = QVBoxLayout()
        for w in (QLabel("Input:"), self.ed_input, btn_in,
                  QLabel("Output:"), self.ed_output, btn_out,
                  QLabel("Protocolo:"), self.combo_proto,
                  QLabel("Método de processamento:")):
            col_esq.addWidget(w)
        col_esq.addLayout(cx_modo)
        col_esq.addWidget(QLabel("Flags:")); col_esq.addWidget(self.chk_pular); col_esq.addWidget(self.chk_aprovar)

        col_meio = QVBoxLayout()
        col_meio.addWidget(QLabel("Subestação")); col_meio.addWidget(self.combo_sub)
        col_meio.addWidget(QLabel("Sheets")); col_meio.addWidget(self.lista_sheets)

        col_dir = QVBoxLayout()
        topo = QHBoxLayout(); topo.addStretch(); topo.addWidget(btn_cfg)
        botoes = QHBoxLayout(); botoes.addWidget(self.btn_executar); botoes.addWidget(self.btn_parar)
        col_dir.addLayout(topo); col_dir.addLayout(botoes)
        log_header = QHBoxLayout()
        log_header.addWidget(QLabel("LOG"))
        log_header.addStretch()
        log_header.addWidget(self.btn_limpar_log)
        col_dir.addLayout(log_header)
        col_dir.addWidget(self.log)
        col_dir.addWidget(self.progresso_bar)

        def _grupo(titulo, layout):
            g = QGroupBox(titulo); g.setLayout(layout); return g

        raiz = QHBoxLayout(self)
        raiz.addWidget(_grupo("Entrada / Processamento", col_esq))
        raiz.addWidget(_grupo("Subestação / Sheets", col_meio))
        raiz.addWidget(_grupo("Execução", col_dir), 1)

    def recarregar(self) -> None:
        p = self._estado.paths
        self.ed_input.setText(p.get("input", ""))
        self.ed_output.setText(p.get("output", ""))

    def _escolher_input(self):
        atual = self._estado.paths.get("input", "") or DEFAULT_LISTA
        caminho, _ = QFileDialog.getOpenFileName(
            self, "Input .xlsx", dir=atual, filter="Excel (*.xlsx)")
        if not caminho:
            return
        self._estado.paths["input"] = caminho
        self.ed_input.setText(caminho)
        self._popular_sheets(caminho)

    def _escolher_output(self):
        atual = self._estado.paths.get("output", "") or DEFAULT_OUTPUT
        caminho = QFileDialog.getExistingDirectory(self, "Pasta de output", dir=atual)
        if caminho:
            self._estado.paths["output"] = caminho
            self.ed_output.setText(caminho)

    def _popular_sheets(self, caminho):
        self.lista_sheets.clear()
        try:
            wb = openpyxl.load_workbook(caminho, read_only=True)
            nomes = wb.sheetnames
            wb.close()
        except Exception as e:
            self.log.appendPlainText(f"[ERRO] não li sheets: {e}")
            return
        aliases = self._estado.aliases
        for nome in nomes:
            texto = aliases.get(nome, nome)
            it = QListWidgetItem(texto)
            it.setData(Qt.UserRole, nome)  # nome original da sheet
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            it.setCheckState(Qt.Checked)
            self.lista_sheets.addItem(it)

    def _sheet_renomeada(self, it: QListWidgetItem) -> None:
        original = it.data(Qt.UserRole)
        novo = it.text().strip()
        if novo and novo != original:
            self._estado.aliases[original] = novo
        elif original in self._estado.aliases:
            del self._estado.aliases[original]

    def _coletar(self):
        self._estado.modo = _MODOS[self.grupo_modo.checkedId()][1]
        self._estado.flags["pular_revisao"] = self.chk_pular.isChecked()
        self._estado.flags["aprovar_acima_threshold"] = self.chk_aprovar.isChecked()
        texto = self.combo_sub.currentText().strip()
        self._estado.subestacao = None if not texto else texto

    def _executar(self):
        self._coletar()
        p = self._estado.paths
        faltando = [k for k in ("input", "template", "lista_padrao")
                    if not p.get(k) or not Path(p[k]).exists()]
        if faltando:
            QMessageBox.warning(self, "Arquivos ausentes",
                                "Configure os caminhos abaixo em ⚙:\n"
                                + "\n".join(f"  • {k}" for k in faltando))
            self._fim()
            return
        self.btn_executar.setEnabled(False); self.btn_parar.setEnabled(True)
        self._worker = self._worker_factory(
            paths=self._estado.paths, config=self._estado.config,
            modo=self._estado.modo, subestacao=self._estado.subestacao,
            app_state=self._estado,
        )
        self._worker.log.connect(self.log.appendPlainText)
        self._worker.erro.connect(lambda m: self.log.appendPlainText(f"[ERRO] {m}"))
        self._worker.erro.connect(self._fim)
        self._worker.terminado.connect(self._terminado)
        self._worker.progresso.connect(self._atualizar_progresso)
        self._worker.start()

    def _atualizar_progresso(self, atual: int, total: int) -> None:
        self.progresso_bar.setVisible(True)
        self.progresso_bar.setMaximum(total)
        self.progresso_bar.setValue(atual)

    def _terminado(self, resultado):
        self._estado.carregar_resultado(resultado)
        caminho_lp = self._estado.paths.get("lista_padrao", "")
        if caminho_lp:
            try:
                self._estado.lista_padrao = ListaPadraoADMS.carregar(caminho_lp)
            except Exception as e:  # ponytail: lista ruim só desliga ADMS na UI + loga
                self.log.appendPlainText(f"[AVISO] não carreguei lista padrão p/ UI: {e}")
        self._fim()
        self.executou.emit()

    def _parar(self):
        if self._worker is not None:
            self._worker.parar()
            self.log.appendPlainText("[AVISO] PARAR solicitado")

    def _fim(self, *args):
        self.btn_executar.setEnabled(True); self.btn_parar.setEnabled(False)
        self.progresso_bar.setVisible(False)
