"""MainWindow: empilha as 4 telas num QStackedWidget; navegação por sinal.

ponytail: QStackedWidget index 0/1/2/3 = Inicial/Revisão/Config/Análise; sem
roteador. Análise fica em índice 3 (não 2, ocupado por Config) porque Config
não tem aba própria — é acessada via link separado da tela inicial.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QStackedWidget, QTabBar, QVBoxLayout, QWidget,
)

from tdt.ui.estado import AppState
from tdt.ui.tela_analise import TelaAnalise
from tdt.ui.tela_config import TelaConfig
from tdt.ui.tela_inicial import TelaInicial
from tdt.ui.tela_revisao import TelaRevisao

_TEMA = Path(__file__).resolve().parent / "tema.qss"


class MainWindow(QMainWindow):
    def __init__(self, estado: AppState, config_path="config.toml"):
        super().__init__()
        self._estado = estado
        self._config_path = Path(config_path)
        self.setWindowTitle("TDT — Analisador de Subestação")
        self.resize(1200, 700)

        self.stack = QStackedWidget()
        self.tela_inicial = TelaInicial(estado)
        self.tela_revisao = TelaRevisao(estado)
        self.tela_config = TelaConfig(estado, config_path=config_path)
        self.tela_analise = TelaAnalise()

        self.stack.addWidget(self.tela_inicial)   # 0
        self.stack.addWidget(self.tela_revisao)    # 1
        self.stack.addWidget(self.tela_config)     # 2
        self.stack.addWidget(self.tela_analise)    # 3

        self.abas = QTabBar()
        self.abas.addTab("Inicial")
        self.abas.addTab("Revisão")
        self.abas.addTab("Análise")
        self.abas.setTabEnabled(1, False)
        self.abas.setTabEnabled(2, False)
        self.abas.currentChanged.connect(self._mudar_aba)

        self.tela_inicial.executou.connect(self._ir_para_revisao)
        self.tela_inicial.executou.connect(
            lambda: self.tela_analise.carregar(self._estado.resultado)
        )
        self.tela_inicial.abrir_config.connect(lambda: self.stack.setCurrentIndex(2))
        self.tela_revisao.voltar.connect(lambda: self.abas.setCurrentIndex(0))
        self.tela_config.voltar.connect(lambda: self._voltar_config())

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.abas)
        layout.addWidget(self.stack)
        self.setCentralWidget(container)

        tema = _TEMA
        if tema.exists():
            with open(tema, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    # ponytail: mapa fixo aba->stack porque a TelaConfig ocupa o índice 2 do
    # stack sem ter aba própria (acesso via link na tela inicial). Se mais
    # telas sem aba forem adicionadas, trocar por uma lista de índices.
    _ABA_PARA_STACK = {0: 0, 1: 1, 2: 3}

    def _mudar_aba(self, indice_aba: int) -> None:
        self.stack.setCurrentIndex(self._ABA_PARA_STACK[indice_aba])

    def _voltar_config(self) -> None:
        self.tela_inicial.recarregar()
        self.abas.setCurrentIndex(0)
        self.stack.setCurrentIndex(0)

    def _ir_para_revisao(self) -> None:
        try:
            flags = self._estado.flags
            if flags.get("pular_revisao"):
                self.tela_inicial.log.appendPlainText("[INFO] UI: revisão pulada (flag ativa)")
                return
            if flags.get("aprovar_acima_threshold"):
                threshold = self._estado.config.threshold_pct
                total = len(self._estado.registros)
                for i, r in enumerate(self._estado.registros):
                    if r.status == "revisao" and r.candidatos and r.candidatos[0].score >= threshold:
                        self._estado.definir_sigla(i, r.candidatos[0].sigla)
                    if i % 100 == 0:
                        QApplication.processEvents()
            self.tela_inicial.log.appendPlainText("[INFO] UI: abrindo tela de revisão…")
            QApplication.processEvents()
            self.tela_revisao.carregar()
            self.abas.setTabEnabled(1, True)
            self.abas.setTabEnabled(2, True)
            self.abas.setCurrentIndex(1)
            self.stack.setCurrentIndex(1)
        except Exception as e:
            self.tela_inicial.log.appendPlainText(f"[ERRO] UI: falha ao abrir revisão — {e}")
            QMessageBox.critical(self, "Erro", f"Não foi possível abrir a tela de revisão:\n{e}")
