"""Modelo de tabela para a tela de Análise (Parte 2).

Lê SignalRecord (já processados pelo pipeline) e o mapa id->motivo de revisão,
expondo colunas de auditoria: scores por método, gap entre 1º/2º candidato e
consenso entre métodos. Não toca em pipeline nem na tela de revisão (SRP).

ponytail: model fino e somente leitura, sem cache — relê o registro a cada
data(). Se a tabela crescer (milhares de linhas) e isso ficar lento, trocar
por cache de coluna computada no __init__.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from tdt.contracts import SignalRecord

COLUNAS = [
    "ID", "Descrição", "Sigla Decidida", "Status",
    "Score Final", "Score TF-IDF", "Score Vetorial", "Score Fuzzy",
    "Gap", "Motivo Revisão", "Consenso",
]

_METODOS = ("tfidf", "vetorial", "fuzzy")


def _scores_metodo(rec: SignalRecord) -> dict[str, float] | None:
    if rec.diagnostico is None or rec.sigla_sinal is None:
        return None
    return rec.diagnostico.scores_por_metodo.get(rec.sigla_sinal)


class ModeloAnalise(QAbstractTableModel):
    """Tabela somente-leitura para a tela de Análise."""

    COLUNAS = COLUNAS

    def __init__(self, registros: list[SignalRecord], revisao_por_id: dict[str, str]):
        super().__init__()
        self._rows = registros
        self._revisao = revisao_por_id  # id -> motivo

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(COLUNAS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return COLUNAS[section]
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        rec = self._rows[index.row()]
        col = index.column()

        if col == 0:
            return rec.id
        if col == 1:
            return rec.descricoes.bruta
        if col == 2:
            return rec.sigla_sinal
        if col == 3:
            return rec.status
        if col == 4:
            return rec.candidatos[0].score if rec.candidatos else None
        if col in (5, 6, 7):
            scores = _scores_metodo(rec)
            if scores is None:
                return None
            return scores.get(_METODOS[col - 5])
        if col == 8:
            return self._gap(rec)
        if col == 9:
            return self._revisao.get(rec.id, "")
        if col == 10:
            return self._consenso(rec)
        return None

    @staticmethod
    def _gap(rec: SignalRecord) -> float | None:
        if not rec.candidatos:
            return None
        if len(rec.candidatos) < 2:
            return rec.candidatos[0].score
        return round(rec.candidatos[0].score - rec.candidatos[1].score, 4)

    @staticmethod
    def _consenso(rec: SignalRecord) -> int:
        scores = _scores_metodo(rec)
        if not scores:
            return 0
        return sum(1 for v in scores.values() if v is not None)
