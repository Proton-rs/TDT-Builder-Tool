"""MainWindow: sidebar retrátil + QStackedWidget; navegação por chave.

ponytail: mapeamento chave->índice fixo em _INDICE; tela Geração é placeholder
até SP-UI-4 (Task 14 troca por TelaGeracao real).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QMainWindow, QMessageBox,
    QStackedWidget, QWidget,
)

from tdt.ui.estado import AppState
from tdt.ui.sidebar import Sidebar
from tdt.ui.tela_analise import TelaAnalise
from tdt.ui.tela_config import TelaConfig
from tdt.ui.tela_inicial import TelaInicial
from tdt.ui.tela_revisao import TelaRevisao

_TEMA = Path(__file__).resolve().parent / "tema.qss"

_INDICE = {"entrada": 0, "revisao": 1, "config": 2, "analise": 3, "geracao": 4}

_ITENS_FLUXO = [
    ("entrada", "1 · Entrada", "①"),
    ("revisao", "2 · Revisão", "②"),
    ("geracao", "3 · Geração", "③"),
]
_ITENS_FIXOS = [
    ("analise", "Análise", "▤"),
    ("config", "Configurações", "⚙"),
]


class MainWindow(QMainWindow):
    def __init__(self, estado: AppState, config_path="config.toml"):
        super().__init__()
        self._estado = estado
        self._config_path = Path(config_path)
        self.setWindowTitle("TDT — Analisador de Subestação")
        self.resize(1200, 700)

        self.stack = QStackedWidget()
        self.tela_inicial = TelaInicial(estado, config_path=config_path)
        self.tela_revisao = TelaRevisao(estado)
        self.tela_config = TelaConfig(estado, config_path=config_path)
        self.tela_analise = TelaAnalise()
        self.tela_geracao = self._criar_tela_geracao()

        self.stack.addWidget(self.tela_inicial)   # 0
        self.stack.addWidget(self.tela_revisao)   # 1
        self.stack.addWidget(self.tela_config)    # 2
        self.stack.addWidget(self.tela_analise)   # 3
        self.stack.addWidget(self.tela_geracao)   # 4

        self.sidebar = Sidebar(_ITENS_FLUXO, _ITENS_FIXOS)
        for chave in ("revisao", "geracao", "analise"):
            self.sidebar.definir_estado(chave, "bloqueada")
        self.sidebar.definir_ativa("entrada")
        self.sidebar.navegar.connect(self._navegar)

        self.tela_inicial.executou.connect(self._pos_execucao)
        self.tela_inicial.abrir_config.connect(lambda: self._navegar("config"))
        self.tela_revisao.voltar.connect(lambda: self._navegar("entrada"))
        self.tela_revisao.desfazer_pedido.connect(self._desfazer)
        self.tela_config.voltar.connect(self._voltar_config)

        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(container)

        self._atalho_undo = QShortcut(QKeySequence.Undo, self)
        self._atalho_undo.activated.connect(self._desfazer)

        if _TEMA.exists():
            with open(_TEMA, encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _criar_tela_geracao(self) -> QWidget:
        # ponytail: placeholder até SP-UI-4 (Task 14) — evita bloquear o shell.
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.addWidget(QLabel("Geração — em construção (SP-UI-4)"))
        return w

    def _navegar(self, chave: str) -> None:
        self.stack.setCurrentIndex(_INDICE[chave])
        self.sidebar.definir_ativa(chave)

    def _voltar_config(self) -> None:
        self.tela_inicial.recarregar()
        self._navegar("entrada")

    def _desfazer(self) -> None:
        if self._estado.desfazer():
            self.tela_revisao.refresh()

    def _pos_execucao(self) -> None:
        self.tela_analise.carregar(self._estado.resultado)
        self.sidebar.definir_estado("entrada", "completa")
        for chave in ("revisao", "geracao", "analise"):
            self.sidebar.definir_estado(chave, "disponivel")
        pendentes = sum(1 for r in self._estado.registros if r.status == "revisao")
        self.sidebar.atualizar_badge("revisao", pendentes)
        self.sidebar.definir_contexto(
            f"{self._estado.subestacao or '—'} · DNP3 · "
            f"{len(self._estado.registros)} sinais"
        )
        self._ir_para_revisao()

    def _ir_para_revisao(self) -> None:
        try:
            flags = self._estado.flags
            if flags.get("pular_revisao"):
                self.tela_inicial.log_msg("[INFO] UI: revisão pulada (flag ativa)")
                return
            if flags.get("aprovar_acima_threshold"):
                threshold = self._estado.config.threshold_pct
                self._estado._snapshot()  # 1 snapshot p/ o lote inteiro
                for i, r in enumerate(self._estado.registros):
                    if r.status == "revisao" and r.candidatos \
                            and r.candidatos[0].score >= threshold:
                        self._estado.definir_sigla(
                            i, r.candidatos[0].sigla, snapshot=False)
                    if i % 100 == 0:
                        QApplication.processEvents()
            self.tela_inicial.log_msg("[INFO] UI: abrindo tela de revisão…")
            QApplication.processEvents()
            self.tela_revisao.carregar()
            self._navegar("revisao")
        except Exception as e:
            self.tela_inicial.log_msg(f"[ERRO] UI: falha ao abrir revisão — {e}")
            QMessageBox.critical(
                self, "Erro", f"Não foi possível abrir a tela de revisão:\n{e}")
