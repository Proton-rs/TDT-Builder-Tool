"""Proxy de filtro/ordenação pra tela de revisão — Qt nativo, sem libs novas.

ponytail: filtro de texto usa o QSortFilterProxyModel padrão
(setFilterKeyColumn(-1) busca em todas as colunas); "esconder decididos" é
o único filtro customizado.
"""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel

from tdt.ui.modelo_tabela import ModeloSinais

_COL_STATUS = ModeloSinais.COLUNAS.index("Status")


class ProxyRevisao(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._esconder_decididos = False
        self._filtros_coluna: dict[int, str] = {}

    def setEsconderDecididos(self, ativo: bool) -> None:
        self._esconder_decididos = ativo
        self.invalidateFilter()

    def setFiltroColuna(self, col: int, texto: str) -> None:
        if texto:
            self._filtros_coluna[col] = texto.upper()
        else:
            self._filtros_coluna.pop(col, None)
        self.invalidateFilter()

    def filtroColuna(self, col: int) -> str:
        return self._filtros_coluna.get(col, "")

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        if not super().filterAcceptsRow(source_row, source_parent):
            return False
        if self._esconder_decididos:
            idx = self.sourceModel().index(source_row, _COL_STATUS, source_parent)
            if self.sourceModel().data(idx) == "decidido":
                return False
        for col, termo in self._filtros_coluna.items():
            idx = self.sourceModel().index(source_row, col, source_parent)
            valor = str(self.sourceModel().data(idx) or "").upper()
            if termo not in valor:
                return False
        return True
