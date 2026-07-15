"""Proxy de filtro/ordenação pra tela de revisão — Qt nativo, sem libs novas.

ponytail: filtro de texto usa o QSortFilterProxyModel padrão
(setFilterKeyColumn(-1) busca em todas as colunas); "esconder decididos" é
o único filtro customizado.
"""

from __future__ import annotations

from PySide6.QtCore import QSortFilterProxyModel, Qt

from tdt.ui.modelo_tabela import ModeloSinais, sheet_origem

_COL_STATUS = ModeloSinais.COLUNAS.index("Status")

# ponytail: sufixo textual no header em vez de ícone custom-painted -- menor
# diff (headerData já é sobrescrevível no proxy, sem precisar de um
# QHeaderView subclasse) e já transmite "filtro ativo" sem depender de
# assets/paint code novo.
MARCADOR_FILTRO = " ▼*"


class ProxyRevisao(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status_visivel: str | None = None
        self._filtros_coluna: dict[int, str] = {}
        self._sheet: str | None = None
        self._filtros_coluna_valores: dict[int, set[str]] = {}

    def set_status_visivel(self, status: str | None) -> None:
        """None = todos; "revisao"/"decidido" mostram só esse status."""
        self._status_visivel = status
        self.invalidateFilter()

    def set_sheet(self, nome: str | None) -> None:
        """Filtra pela sheet de origem; `None` = aba "Tudo" (sem filtro)."""
        self._sheet = nome
        self.invalidateFilter()

    def setFiltroColuna(self, col: int, texto: str) -> None:
        estava = col in self._filtros_coluna
        if texto:
            self._filtros_coluna[col] = texto.upper()
        else:
            self._filtros_coluna.pop(col, None)
        self.invalidateFilter()
        if estava != (col in self._filtros_coluna):
            self.headerDataChanged.emit(Qt.Horizontal, col, col)

    def filtroColuna(self, col: int) -> str:
        return self._filtros_coluna.get(col, "")

    def set_filtro_coluna(self, col: int, valores: set[str] | None) -> None:
        """Filtro estilo Excel: aceita a linha se o valor da célula em `col`
        estiver em `valores`. `None` remove o filtro dessa coluna.

        Independente de `setFiltroColuna` (busca "contém" de texto livre,
        legado da Task 1/2) -- as duas fontes de filtro por coluna coexistem
        e combinam em AND dentro de `filterAcceptsRow`.
        """
        estava_filtrada = col in self._filtros_coluna_valores
        if valores is None:
            self._filtros_coluna_valores.pop(col, None)
        else:
            self._filtros_coluna_valores[col] = set(valores)
        self.invalidateFilter()
        if estava_filtrada != (col in self._filtros_coluna_valores):
            # ponytail: reusa o sinal nativo headerDataChanged (em vez de
            # inventar um sinal próprio) -- é exatamente o que QHeaderView já
            # escuta pra repintar a seção, então o header atualiza sozinho.
            self.headerDataChanged.emit(Qt.Horizontal, col, col)

    def colunas_filtradas(self) -> set[int]:
        """Colunas com filtro de valores (estilo Excel) ativo no momento."""
        return set(self._filtros_coluna_valores.keys())

    def filtros_ativos(self) -> int:
        return len(set(self._filtros_coluna) | set(self._filtros_coluna_valores))

    def limpar_filtros(self) -> None:
        cols = set(self._filtros_coluna) | set(self._filtros_coluna_valores)
        self._filtros_coluna.clear()
        self._filtros_coluna_valores.clear()
        self.invalidateFilter()
        for col in cols:
            self.headerDataChanged.emit(Qt.Horizontal, col, col)

    def headerData(self, secao, orientacao, role=Qt.DisplayRole):
        valor = super().headerData(secao, orientacao, role)
        if (
            role == Qt.DisplayRole
            and orientacao == Qt.Horizontal
            and (secao in self._filtros_coluna_valores or secao in self._filtros_coluna)
        ):
            return f"{valor}{MARCADOR_FILTRO}"
        return valor

    def valores_unicos(self, col: int) -> list[str]:
        """Valores distintos presentes em `col`, na fonte inteira (não filtrada),
        ordenados. Uma passada O(n) sobre o modelo fonte -- chamada só quando o
        popup de filtro é aberto, não a cada tecla digitada na busca do popup.
        """
        modelo = self.sourceModel()
        if modelo is None:
            return []
        return sorted({
            modelo.valor_texto(row, col) for row in range(modelo.rowCount())
        })

    def filterAcceptsRow(self, source_row, source_parent) -> bool:
        modelo = self.sourceModel()
        if self._sheet is not None:
            rec = modelo._estado.registros[source_row]
            if sheet_origem(rec) != self._sheet:
                return False
        if self._status_visivel is not None:
            if modelo.valor_texto(source_row, _COL_STATUS) != self._status_visivel:
                return False
        for col, valores in self._filtros_coluna_valores.items():
            if modelo.valor_texto(source_row, col) not in valores:
                return False
        for col, termo in self._filtros_coluna.items():
            if termo not in modelo.valor_texto(source_row, col).upper():
                return False
        # busca global de texto (setFilterKeyColumn(-1), varre todas as
        # colunas) por último -- é o passo mais caro
        return super().filterAcceptsRow(source_row, source_parent)
