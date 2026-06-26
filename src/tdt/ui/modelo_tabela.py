"""Modelo de tabela sobre os SignalRecords (decididos + revisão).

ponytail: model fino que lê do AppState; sem cache, relê o registro a cada data().
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from tdt.contracts import SignalRecord
from tdt.ui.estado import AppState

COLUNAS = [
    "Sinal", "Confiança", "Status", "Motivo", "Descr. ADMS", "Descr. bruta",
    "Descr. normalizada", "Tokens", "Tipo", "Escala", "Fase", "Endereço",
    "Endereço Output",
    "Score embedding", "Score tf-idf", "Score fuzzy", "Justificativa",
    "Módulo", "Equipamento", "Tipo Equip.", "Barra", "Nível Tensão",
]

_MOTIVO_LABEL = {
    "sem_endereco": "Futuro (sem endereço)",
    "score_baixo": "Score baixo",
    "categoria_ambigua": "Categoria ambígua",
    "endereco_duplicado": "Endereço duplicado",
    "sem_fix": "Sem correção automática",
}

# Cores por faixa de confiança (texto). ponytail: faixas fixas; threshold de
# decisão é outra coisa (config).
COR_ALTO = QColor("#1d9e75")
COR_MEDIO = QColor("#b07410")
COR_BAIXO = QColor("#c0492a")
COR_DECIDIDO = QColor("#1d9e75")
COR_REVISAO = QColor("#c0492a")


def cor_faixa(score) -> QColor | None:
    if score is None:
        return None
    if score >= 0.70:
        return COR_ALTO
    if score >= 0.45:
        return COR_MEDIO
    return COR_BAIXO


def _score(rec, sigla, metodo):
    diag = rec.diagnostico
    if diag is None or sigla is None:
        return ""
    v = diag.scores_por_metodo.get(sigla, {}).get(metodo)
    return f"{v:.2f}" if v is not None else ""


class ModeloSinais(QAbstractTableModel):
    COLUNAS = COLUNAS

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._estado.registros)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUNAS)

    def headerData(self, secao, orientacao, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientacao == Qt.Horizontal:
            return COLUNAS[secao]
        return None

    def flags(self, index):
        base = super().flags(index)
        if COLUNAS[index.column()] == "Sinal":
            return base | Qt.ItemIsEditable
        return base

    def _adms(self, rec):
        lp = self._estado.lista_padrao
        if lp is None or not rec.sigla_sinal:
            return ""
        sp = lp.por_sigla(rec.sigla_sinal)
        return sp.descricao if sp else ""

    def _texto(self, rec, col):
        sigla = rec.sigla_sinal
        topo = rec.candidatos[0].score if rec.candidatos else None
        nome = COLUNAS[col]
        if nome == "Sinal":
            return sigla or "—"
        if nome == "Confiança":
            return f"{topo:.2f}" if topo is not None else ""
        if nome == "Status":
            return rec.status
        if nome == "Motivo":
            motivo = self._estado.motivo_por_id().get(rec.id)
            return _MOTIVO_LABEL.get(motivo, "—") if motivo else "—"
        # ponytail: motivo_por_id() reconstroi o dict a cada chamada de _texto
        # -- ok pro tamanho de lista atual (centenas de linhas); cachear no
        # AppState se a tabela ficar lenta com listas grandes.
        if nome == "Descr. ADMS":
            return self._adms(rec) or "—"
        if nome == "Descr. bruta":
            return rec.descricoes.bruta
        if nome == "Descr. normalizada":
            return rec.descricoes.normalizada
        if nome == "Tokens":
            return "·".join(rec.descricoes.normalizada.split())
        if nome == "Tipo":
            t = rec.tipo_sinal
            return f"{t.categoria}/{t.direcao}"
        if nome == "Escala":
            e = rec.grandezas_analogicas.escala_transmissao
            return "" if e is None else str(e)
        if nome == "Fase":
            return rec.eletrico.fase or "—"
        if nome == "Endereço":
            return ";".join(str(i) for i in rec.enderecamento.indices)
        if nome == "Endereço Output":
            return ";".join(str(i) for i in rec.enderecamento.indices_saida) or "—"
        if nome == "Score embedding":
            return _score(rec, sigla, "vetorial")
        if nome == "Score tf-idf":
            return _score(rec, sigla, "tfidf")
        if nome == "Score fuzzy":
            return _score(rec, sigla, "fuzzy")
        if nome == "Justificativa":
            return rec.justificativa or ""
        if nome == "Módulo":
            return (rec.modulo.nome if rec.modulo else None) or "—"
        if nome == "Equipamento":
            return rec.eletrico.nome_equipamento or "—"
        if nome == "Tipo Equip.":
            return rec.eletrico.equipamento_alvo or "—"
        if nome == "Barra":
            return rec.eletrico.barra or "—"
        if nome == "Nível Tensão":
            return rec.eletrico.nivel_tensao or "—"
        return ""

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self._estado.registros[index.row()]
        nome = COLUNAS[index.column()]
        if role == Qt.DisplayRole:
            return self._texto(rec, index.column())
        if role == Qt.ForegroundRole:
            if nome == "Status":
                return COR_DECIDIDO if rec.status == "decidido" else COR_REVISAO
            if nome == "Confiança":
                return cor_faixa(rec.candidatos[0].score if rec.candidatos else None)
        if role == Qt.ToolTipRole and nome in ("Sinal", "Descr. ADMS"):
            return self._adms(rec) or None
        return None

    def definir_sigla(self, linha: int, sigla: str) -> None:
        self._estado.definir_sigla(linha, sigla)
        topo = self.index(linha, 0)
        fim = self.index(linha, len(COLUNAS) - 1)
        self.dataChanged.emit(topo, fim)

    def adicionar_registro(self, registro: SignalRecord) -> None:
        """Anexa um registro ao final, notificando a view via Qt (insertRows).

        Quem chama é responsável por `self._estado._snapshot()` antes, se
        quiser permitir desfazer (mesmo padrão de `remover_linhas`).
        """
        n = len(self._estado.registros)
        self.beginInsertRows(QModelIndex(), n, n)
        self._estado.registros.append(registro)
        self.endInsertRows()

    def remover_linhas(self, indices: list[int]) -> None:
        """Remove as linhas (índices da fonte, 0-based) da lista subjacente.

        Notifica a view linha a linha via begin/endRemoveRows -- exigido pelo
        Qt antes/depois da mutação real, para não desincronizar view/modelo.
        """
        for linha in sorted(set(indices), reverse=True):
            if not (0 <= linha < len(self._estado.registros)):
                continue
            self.beginRemoveRows(QModelIndex(), linha, linha)
            self._estado.registros.pop(linha)
            self.endRemoveRows()
