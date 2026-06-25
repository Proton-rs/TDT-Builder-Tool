"""TelaAnalise (Parte 2): tabela de qualidade do matching + cards de estatísticas.

Lê o ResultadoPipeline completo (decididos + revisão) via ModeloAnalise, com um
QSortFilterProxyModel para ordenação por coluna e filtro de status (Todos /
Decididos / Revisão). Não decide nada, não edita registros — somente leitura,
consistente com ModeloAnalise (SRP).
"""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QMessageBox, QPushButton, QTableView, QVBoxLayout, QWidget,
)

from tdt.contracts import ResultadoPipeline
from tdt.ui.modelo_analise import COLUNAS, ModeloAnalise

_COL_STATUS = COLUNAS.index("Status")


class _ProxyStatus(QSortFilterProxyModel):
    """Proxy com filtro por status exato (coluna "Status").

    ponytail: filtro simples baseado num atributo `_status_filtro` (None =
    sem filtro). QSortFilterProxyModel.setFilterFixedString não dá pra usar
    aqui porque "decidido" e "revisao" não são substrings exclusivas entre si
    nem das outras colunas — por isso o filterAcceptsRow dedicado.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_filtro: str | None = None

    def definir_filtro_status(self, status: str | None) -> None:
        self._status_filtro = status
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        if self._status_filtro is None:
            return True
        modelo = self.sourceModel()
        idx = modelo.index(source_row, _COL_STATUS, source_parent)
        return modelo.data(idx) == self._status_filtro


class TelaAnalise(QWidget):
    """Tela de análise de qualidade do matching (Parte 2)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._resultado: ResultadoPipeline | None = None
        layout = QVBoxLayout(self)

        self._stats_group = QGroupBox("Estatísticas")
        stats_grid = QGridLayout()
        self._stats_labels: dict[str, QLabel] = {}
        for i, (nome, chave) in enumerate([
            ("Total", "total"), ("Decididos", "decididos"),
            ("Revisão", "revisao"), ("Taxa de Decisão", "taxa"),
        ]):
            label_val = QLabel("—")
            label_val.setStyleSheet("font-size: 18pt; font-weight: bold;")
            stats_grid.addWidget(QLabel(nome), 0, i, Qt.AlignCenter)
            stats_grid.addWidget(label_val, 1, i, Qt.AlignCenter)
            self._stats_labels[chave] = label_val

        stats_grid.addWidget(QLabel("Motivos de Revisão:"), 2, 0, 1, 1)
        self._motivos_label = QLabel("—")
        stats_grid.addWidget(self._motivos_label, 2, 1, 1, 3)
        self._stats_group.setLayout(stats_grid)
        layout.addWidget(self._stats_group)

        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filtrar:"))
        self._combo_status = QComboBox()
        self._combo_status.addItems(["Todos", "Decididos", "Revisão"])
        self._combo_status.currentTextChanged.connect(self._filtrar)
        filter_layout.addWidget(self._combo_status)
        filter_layout.addStretch()
        self._btn_exportar = QPushButton("Exportar Relatório")
        self._btn_exportar.clicked.connect(self._exportar)
        filter_layout.addWidget(self._btn_exportar)
        layout.addLayout(filter_layout)

        self._table = QTableView()
        self._table.setSortingEnabled(True)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self._modelo: ModeloAnalise | None = None
        self._proxy = _ProxyStatus()
        self._table.setModel(self._proxy)
        layout.addWidget(self._table)

    def carregar(self, resultado: ResultadoPipeline) -> None:
        self._resultado = resultado
        revisao_por_id = {ir.registro.id: ir.motivo for ir in resultado.revisao}

        registros = list(resultado.lista.registros)
        ids_existentes = {r.id for r in registros}
        for ir in resultado.revisao:
            if ir.registro.id not in ids_existentes:
                registros.append(ir.registro)
                ids_existentes.add(ir.registro.id)

        self._modelo = ModeloAnalise(registros, revisao_por_id)
        self._proxy.setSourceModel(self._modelo)
        self._combo_status.setCurrentIndex(0)
        self._proxy.definir_filtro_status(None)
        self._atualizar_stats(registros, resultado.revisao)

    def _atualizar_stats(self, registros, revisao) -> None:
        total = len(registros)
        decididos = sum(1 for r in registros if r.status == "decidido")
        n_revisao = len(revisao)
        taxa = f"{decididos / total * 100:.1f}%" if total else "—"

        self._stats_labels["total"].setText(str(total))
        self._stats_labels["decididos"].setText(str(decididos))
        self._stats_labels["revisao"].setText(str(n_revisao))
        self._stats_labels["taxa"].setText(taxa)

        motivos: dict[str, int] = {}
        for ir in revisao:
            motivos[ir.motivo] = motivos.get(ir.motivo, 0) + 1
        if motivos:
            texto = ", ".join(
                f"{k}: {v}" for k, v in sorted(motivos.items(), key=lambda x: -x[1])
            )
        else:
            texto = "—"
        self._motivos_label.setText(texto)

    def _filtrar(self, texto: str) -> None:
        if texto == "Decididos":
            self._proxy.definir_filtro_status("decidido")
        elif texto == "Revisão":
            self._proxy.definir_filtro_status("revisao")
        else:
            self._proxy.definir_filtro_status(None)

    def _exportar(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório", "", "Excel (*.xlsx)")
        if not path:
            return
        try:
            from tdt.ui.exportar_analise import exportar_relatorio
        except ImportError:
            QMessageBox.warning(
                self, "Exportação indisponível",
                "A exportação de relatório ainda não está implementada nesta versão.",
            )
            return
        exportar_relatorio(self._resultado, path)
