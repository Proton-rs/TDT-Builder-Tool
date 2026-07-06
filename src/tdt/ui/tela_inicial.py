"""Tela Entrada: setup guiado com cards de estado; dispara o pipeline.

ponytail: cards são QFrame com propriedade QSS estado="ok|faltando"; a
validação vive em motivo_bloqueio (pura). Worker injetável p/ teste.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

import openpyxl
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup, QCheckBox, QComboBox, QFileDialog, QFrame, QGroupBox,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QPushButton, QRadioButton, QTextEdit, QVBoxLayout, QWidget,
)

from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT, DEFAULT_TEMPLATE
from tdt.ui.config_io import salvar_config
from tdt.ui.estado import AppState
from tdt.ui.worker import PipelineWorker

_MODOS = [("Automático (detecta pelo header)", "auto"),
          ("Homogêneo", "homogeneo"),
          ("Não homogêneo", "nao-homogeneo")]

_ROTULOS_FALTA = {
    "input": "arquivo de input",
    "template": "template DNP3",
    "lista_padrao": "lista padrão ADMS",
}

_CORES_NIVEL = {"[ERRO]": "#e0604c", "[AVISO]": "#e0a83f", "[INFO]": "#9aa3b5"}


def motivo_bloqueio(sigla: str, paths: dict) -> list[str]:
    """Pendências que impedem executar, na ordem de exibição. Vazio = pode."""
    faltas = []
    if not sigla.strip():
        faltas.append("sigla da SE")
    for chave, rotulo in _ROTULOS_FALTA.items():
        p = paths.get(chave, "")
        if not p or not Path(p).exists():
            faltas.append(rotulo)
    return faltas


def pode_executar(sigla_se: str, input_ok: bool) -> bool:
    """Mantida por compatibilidade com testes/chamadores existentes."""
    return bool(sigla_se.strip()) and input_ok


def linha_log_html(texto: str) -> str:
    """Linha de log com cor por nível, pronta para QTextEdit.append."""
    cor = "#c6ccd9"
    for prefixo, c in _CORES_NIVEL.items():
        if texto.startswith(prefixo):
            cor = c
            break
    return f'<span style="color:{cor}">{escape(texto)}</span>'


class CardArquivo(QFrame):
    """Card de pré-requisito com estado visual ok/faltando."""

    def __init__(self, titulo: str, ao_clicar):
        super().__init__()
        self._titulo = titulo
        self.lbl_titulo = QLabel(titulo)
        self.lbl_valor = QLabel("não configurado")
        self.lbl_valor.setProperty("nivel", "aviso")
        self.btn = QPushButton("Selecionar…")
        self.btn.clicked.connect(ao_clicar)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(self.lbl_titulo)
        col.addWidget(self.lbl_valor)
        lay = QHBoxLayout(self)
        lay.addLayout(col, 1)
        lay.addWidget(self.btn)
        self.definir_caminho("")

    def definir_caminho(self, caminho: str) -> None:
        ok = bool(caminho) and Path(caminho).exists()
        self.setProperty("estado", "ok" if ok else "faltando")
        if ok:
            self.lbl_titulo.setText(f"✓ {self._titulo}")
            self.lbl_valor.setText(Path(caminho).name)
            self.lbl_valor.setProperty("nivel", "")
            self.setToolTip(caminho)
            self.btn.setText("Trocar…")
        else:
            self.lbl_titulo.setText(f"! {self._titulo}")
            self.lbl_valor.setText("não configurado")
            self.lbl_valor.setProperty("nivel", "aviso")
            self.setToolTip("")
            self.btn.setText("Selecionar…")
        for w in (self, self.lbl_valor):
            w.style().unpolish(w)
            w.style().polish(w)


class TelaInicial(QWidget):
    abrir_config = Signal()
    executou = Signal()

    def __init__(self, estado: AppState, worker_factory=PipelineWorker,
                 config_path="config.toml"):
        super().__init__()
        self._estado = estado
        self._worker_factory = worker_factory
        self._worker = None
        self._config_path = config_path

        # --- coluna Arquivos: cards ---
        self.cards: dict[str, CardArquivo] = {}
        defs = [
            ("input", "Input", False, DEFAULT_LISTA),
            ("template", "Template DNP3", False, DEFAULT_TEMPLATE),
            ("lista_padrao", "Lista Padrão ADMS", False, DEFAULT_LISTA),
            ("output", "Pasta de saída", True, DEFAULT_OUTPUT),
        ]
        col_arq = QVBoxLayout()
        for chave, titulo, is_pasta, _default in defs:
            card = CardArquivo(
                titulo,
                lambda _=False, c=chave, p=is_pasta: self._escolher(c, p))
            self.cards[chave] = card
            col_arq.addWidget(card)
        self._defaults_dialogo = {c: d for c, _t, _p, d in defs}

        self.lbl_sheets = QLabel("Sheets")
        self.lista_sheets = QListWidget()
        self.lista_sheets.itemChanged.connect(self._sheet_alterada)
        col_arq.addWidget(self.lbl_sheets)
        col_arq.addWidget(self.lista_sheets, 1)

        # --- coluna Análise ---
        self.combo_sub = QComboBox()
        self.combo_sub.setEditable(True)
        self.combo_sub.lineEdit().setPlaceholderText("sigla da SE, ex.: SAN2")
        self.combo_sub.lineEdit().textChanged.connect(self._atualizar_estado_botao)

        self.combo_proto = QComboBox()
        self.combo_proto.addItem("DNP3")

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
        self.chk_aprovar.setChecked(
            estado.flags.get("aprovar_acima_threshold", True))

        col_ana = QVBoxLayout()
        col_ana.addWidget(QLabel("Subestação *"))
        col_ana.addWidget(self.combo_sub)
        col_ana.addWidget(QLabel("Protocolo"))
        col_ana.addWidget(self.combo_proto)
        col_ana.addWidget(QLabel("Método de processamento"))
        col_ana.addLayout(cx_modo)
        col_ana.addWidget(QLabel("Flags"))
        col_ana.addWidget(self.chk_pular)
        col_ana.addWidget(self.chk_aprovar)
        col_ana.addStretch()

        # --- faixa de execução ---
        self.btn_executar = QPushButton("Executar análise")
        self.btn_executar.setProperty("acao", "principal")
        self.btn_executar.clicked.connect(self._executar)
        self.btn_parar = QPushButton("Parar")
        self.btn_parar.clicked.connect(self._parar)
        self.btn_parar.setEnabled(False)
        btn_cfg = QPushButton("⚙")
        btn_cfg.setToolTip("Configurações")
        btn_cfg.clicked.connect(self.abrir_config.emit)

        self.lbl_motivo = QLabel("")
        self.lbl_motivo.setProperty("nivel", "aviso")
        self.lbl_motivo.setVisible(False)

        self.lbl_etapa = QLabel("")
        self.lbl_etapa.setVisible(False)
        self.progresso_bar = QProgressBar()
        self.progresso_bar.setVisible(False)

        self.btn_toggle_log = QPushButton("Ver log ▾")
        self.btn_toggle_log.clicked.connect(self._alternar_log)
        self.btn_limpar_log = QPushButton("Limpar log")
        self.btn_limpar_log.clicked.connect(lambda: self.log.clear())
        self.btn_limpar_log.setVisible(False)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setVisible(False)

        botoes = QHBoxLayout()
        botoes.addWidget(self.btn_executar)
        botoes.addWidget(self.btn_parar)
        botoes.addStretch()
        botoes.addWidget(self.btn_toggle_log)
        botoes.addWidget(self.btn_limpar_log)
        botoes.addWidget(btn_cfg)

        faixa_exec = QVBoxLayout()
        faixa_exec.addLayout(botoes)
        faixa_exec.addWidget(self.lbl_motivo)
        faixa_exec.addWidget(self.lbl_etapa)
        faixa_exec.addWidget(self.progresso_bar)
        faixa_exec.addWidget(self.log, 1)

        def _grupo(titulo, layout):
            g = QGroupBox(titulo)
            g.setLayout(layout)
            return g

        colunas = QHBoxLayout()
        colunas.addWidget(_grupo("Arquivos", col_arq), 1)
        colunas.addWidget(_grupo("Análise", col_ana), 1)

        raiz = QVBoxLayout(self)
        raiz.addLayout(colunas, 1)
        raiz.addLayout(faixa_exec)

        self.recarregar()

    # --- estado / validação ---
    def recarregar(self) -> None:
        p = self._estado.paths
        for chave, card in self.cards.items():
            card.definir_caminho(p.get(chave, ""))
        self._atualizar_estado_botao()

    def _atualizar_estado_botao(self) -> None:
        faltas = motivo_bloqueio(self.combo_sub.currentText(), self._estado.paths)
        self.btn_executar.setEnabled(not faltas)
        self.lbl_motivo.setText("Falta: " + ", ".join(faltas) if faltas else "")
        self.lbl_motivo.setVisible(bool(faltas))

    def _escolher(self, chave: str, is_pasta: bool) -> None:
        atual = self._estado.paths.get(chave, "") or self._defaults_dialogo[chave]
        if is_pasta:
            caminho = QFileDialog.getExistingDirectory(
                self, "Pasta de saída", dir=atual)
        else:
            caminho, _ = QFileDialog.getOpenFileName(
                self, f"Selecionar {chave}", dir=atual, filter="Excel (*.xlsx)")
        if not caminho:
            return
        self._estado.paths[chave] = caminho
        self.cards[chave].definir_caminho(caminho)
        salvar_config(self._config_path, self._estado.config, self._estado.paths)
        if chave == "input":
            self._popular_sheets(caminho)
        self._atualizar_estado_botao()

    # --- sheets (inalterado em relação à versão anterior) ---
    def _popular_sheets(self, caminho):
        self.lista_sheets.clear()
        try:
            wb = openpyxl.load_workbook(caminho, read_only=True)
            nomes = wb.sheetnames
            wb.close()
        except Exception as e:
            self.log_msg(f"[ERRO] não li sheets: {e}")
            return
        aliases = self._estado.aliases
        for nome in nomes:
            texto = aliases.get(nome, nome)
            it = QListWidgetItem(texto)
            it.setData(Qt.UserRole, nome)
            it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            it.setCheckState(Qt.Checked)
            self.lista_sheets.addItem(it)
        self._atualizar_rotulo_sheets()

    def _sheet_alterada(self, it: QListWidgetItem) -> None:
        original = it.data(Qt.UserRole)
        novo = it.text().strip()
        if novo and novo != original:
            self._estado.aliases[original] = novo
        elif original in self._estado.aliases:
            del self._estado.aliases[original]
        if it.checkState() == Qt.Unchecked:
            self._estado.sheets_excluidas.add(original)
        else:
            self._estado.sheets_excluidas.discard(original)
        self._atualizar_rotulo_sheets()

    def _atualizar_rotulo_sheets(self) -> None:
        total = self.lista_sheets.count()
        marcadas = sum(
            1 for i in range(total)
            if self.lista_sheets.item(i).checkState() == Qt.Checked)
        self.lbl_sheets.setText(
            f"Sheets · {marcadas} de {total} marcadas" if total else "Sheets")

    def _sheets_selecionadas(self) -> list[str] | None:
        if self.lista_sheets.count() == 0:
            return None
        return [
            it.data(Qt.UserRole)
            for i in range(self.lista_sheets.count())
            if (it := self.lista_sheets.item(i)).checkState() == Qt.Checked
        ]

    # --- execução ---
    def _coletar(self):
        self._estado.modo = _MODOS[self.grupo_modo.checkedId()][1]
        self._estado.flags["pular_revisao"] = self.chk_pular.isChecked()
        self._estado.flags["aprovar_acima_threshold"] = self.chk_aprovar.isChecked()
        texto = self.combo_sub.currentText().strip()
        self._estado.subestacao = None if not texto else texto

    def _executar(self):
        self._coletar()
        faltas = motivo_bloqueio(self.combo_sub.currentText(), self._estado.paths)
        if faltas:
            QMessageBox.warning(self, "Pendências",
                                "Resolva antes de executar:\n"
                                + "\n".join(f"  • {f}" for f in faltas))
            self._fim()
            return
        self.btn_executar.setEnabled(False)
        self.btn_parar.setEnabled(True)
        sheets = self._sheets_selecionadas()
        self._worker = self._worker_factory(
            paths=self._estado.paths, config=self._estado.config,
            modo=self._estado.modo, subestacao=self._estado.subestacao,
            app_state=self._estado, sheets=sheets,
            aliases=dict(self._estado.aliases),
        )
        self._worker.log.connect(self._on_log)
        self._worker.erro.connect(self._on_erro)
        self._worker.erro.connect(self._fim)
        self._worker.terminado.connect(self._terminado)
        self._worker.progresso.connect(self._atualizar_progresso)
        self._worker.start()

    # --- log / progresso ---
    def log_msg(self, texto: str) -> None:
        self.log.append(linha_log_html(texto))

    def _on_log(self, texto: str) -> None:
        self.log_msg(texto)
        if texto.startswith("[INFO]"):
            self.lbl_etapa.setText(texto[len("[INFO]"):].strip())
            self.lbl_etapa.setVisible(True)

    def _on_erro(self, msg: str) -> None:
        self.log_msg(f"[ERRO] {msg}")
        self._mostrar_log(True)

    def _alternar_log(self) -> None:
        self._mostrar_log(not self.log.isVisibleTo(self))

    def _mostrar_log(self, visivel: bool) -> None:
        self.log.setVisible(visivel)
        self.btn_limpar_log.setVisible(visivel)
        self.btn_toggle_log.setText("Ocultar log ▴" if visivel else "Ver log ▾")

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
            except Exception as e:
                self.log_msg(f"[AVISO] não carreguei lista padrão p/ UI: {e}")
        self._fim()
        self.executou.emit()

    def _parar(self):
        if self._worker is not None:
            self._worker.parar()
            self.log_msg("[AVISO] Parar solicitado")

    def _fim(self, *args):
        self._atualizar_estado_botao()
        self.btn_parar.setEnabled(False)
        self.progresso_bar.setVisible(False)
        self.lbl_etapa.setVisible(False)
