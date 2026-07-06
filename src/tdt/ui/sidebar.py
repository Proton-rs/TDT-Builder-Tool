"""Sidebar retrátil: etapas do fluxo (topo) + itens fixos (rodapé).

ponytail: QPushButtons flat num QVBoxLayout, sem model. Expansão persiste em
QSettings("tdt", "ui") — injetável nos testes via parâmetro `settings`.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

LARGURA_COLAPSADA = 48
LARGURA_EXPANDIDA = 200

_GLIFO_COMPLETA = "✓"
_GLIFO_BLOQUEADA = "🔒"


class Sidebar(QWidget):
    navegar = Signal(str)

    def __init__(self, itens_fluxo, itens_fixos, settings: QSettings | None = None,
                 parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self._settings = settings if settings is not None else QSettings("tdt", "ui")
        self._expandida = self._settings.value("sidebar_expandida", False, type=bool)
        self._botoes: dict[str, QPushButton] = {}
        self._glifos: dict[str, str] = {}
        self._rotulos: dict[str, str] = {}
        self._estados: dict[str, str] = {}
        self._badges: dict[str, int] = {}
        self._ativa: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 8, 6, 8)
        layout.setSpacing(2)

        self._btn_toggle = QPushButton("☰")
        self._btn_toggle.setProperty("item", "normal")
        self._btn_toggle.setToolTip("Expandir/recolher menu")
        self._btn_toggle.clicked.connect(self._alternar)
        layout.addWidget(self._btn_toggle)

        for chave, rotulo, glifo in itens_fluxo:
            layout.addWidget(self._criar_botao(chave, rotulo, glifo))
        layout.addStretch()
        for chave, rotulo, glifo in itens_fixos:
            layout.addWidget(self._criar_botao(chave, rotulo, glifo))

        self._contexto = QLabel("")
        self._contexto.setObjectName("sidebarContexto")
        self._contexto.setWordWrap(True)
        layout.addWidget(self._contexto)

        self._aplicar_largura()

    def _criar_botao(self, chave: str, rotulo: str, glifo: str) -> QPushButton:
        btn = QPushButton()
        btn.setProperty("item", "normal")
        btn.clicked.connect(lambda _=False, c=chave: self._clicado(c))
        self._botoes[chave] = btn
        self._glifos[chave] = glifo
        self._rotulos[chave] = rotulo
        self._estados[chave] = "disponivel"
        self._badges[chave] = 0
        self._atualizar_botao(chave)
        return btn

    def _clicado(self, chave: str) -> None:
        if self._estados[chave] == "bloqueada":
            return
        self.navegar.emit(chave)

    def _alternar(self) -> None:
        self._expandida = not self._expandida
        self._settings.setValue("sidebar_expandida", self._expandida)
        self._aplicar_largura()

    def _aplicar_largura(self) -> None:
        self.setFixedWidth(LARGURA_EXPANDIDA if self._expandida else LARGURA_COLAPSADA)
        for chave in self._botoes:
            self._atualizar_botao(chave)
        self._contexto.setVisible(self._expandida and bool(self._contexto.text()))

    def _atualizar_botao(self, chave: str) -> None:
        btn = self._botoes[chave]
        estado = self._estados[chave]
        glifo = self._glifos[chave]
        if estado == "completa":
            glifo = _GLIFO_COMPLETA
        elif estado == "bloqueada":
            glifo = _GLIFO_BLOQUEADA
        badge = self._badges[chave]
        sufixo = f" ({badge})" if badge else ""
        if self._expandida:
            btn.setText(f"{glifo}  {self._rotulos[chave]}{sufixo}")
            btn.setToolTip("")
        else:
            btn.setText(f"{glifo}{sufixo}" if badge else glifo)
            btn.setToolTip(self._rotulos[chave] + sufixo)
        if chave == self._ativa:
            item = "ativo"
        elif estado == "bloqueada":
            item = "bloqueado"
        else:
            item = "normal"
        btn.setProperty("item", item)
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def definir_estado(self, chave: str, estado: str) -> None:
        self._estados[chave] = estado
        self._atualizar_botao(chave)

    def definir_ativa(self, chave: str) -> None:
        anterior, self._ativa = self._ativa, chave
        if anterior in self._botoes:
            self._atualizar_botao(anterior)
        self._atualizar_botao(chave)

    def atualizar_badge(self, chave: str, n: int) -> None:
        self._badges[chave] = n
        self._atualizar_botao(chave)

    def definir_contexto(self, texto: str) -> None:
        self._contexto.setText(texto)
        self._contexto.setVisible(self._expandida and bool(texto))
