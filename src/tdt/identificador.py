"""Identifica a rota (homogêneo/não-homogêneo) e as sheets de dados.

Uma sheet é "de dados" quando a análise de colunas encontra pelo menos a
descrição e o índice de endereço — isso exclui Capa/Informações/Consistidos.
O modo pode ser forçado (override) pela UI; em "auto" usa heurística do header.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tdt.analise_colunas import _header_por_densidade, _ncols, _valores_coluna

_INT = re.compile(r"^-?\d+$")
_MAX_SCAN = 60  # linhas para amostrar a estrutura da sheet


def ler_rows(ws, max_rows: int | None = None) -> list[tuple]:
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if max_rows is not None and i >= max_rows:
            break
        rows.append(tuple(row))
    return rows


@dataclass(frozen=True)
class Rota:
    homogeneo: bool
    sheets_dados: list[str]


def _tem_coluna_inteiros(rows, inicio, ncols) -> bool:
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        if vals and sum(1 for v in vals if _INT.match(v)) / len(vals) >= 0.5:
            return True
    return False


def _tem_coluna_texto(rows, inicio, ncols) -> bool:
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        texto = [v for v in vals if len(v) >= 2 and any(ch.isalpha() for ch in v)]
        if len(texto) >= 2:
            return True
    return False


def _eh_sheet_dados(ws) -> bool:
    """Bloco estruturado (densidade) + coluna de índice (inteiros) + descrição (texto)."""
    rows = ler_rows(ws, _MAX_SCAN)
    if len(rows) < 3:
        return False
    h = _header_por_densidade(rows)
    inicio = h + 1
    ncols = _ncols(rows)
    return _tem_coluna_inteiros(rows, inicio, ncols) and _tem_coluna_texto(rows, inicio, ncols)


def classificar(workbook, override: str = "auto") -> Rota:
    sheets = [sn for sn in workbook.sheetnames if _eh_sheet_dados(workbook[sn])]

    if override == "homogeneo":
        homogeneo = True
    elif override == "nao-homogeneo":
        homogeneo = False
    else:  # auto: homogêneo se o bloco estruturado começa no topo na maioria das sheets
        topos = [_header_por_densidade(ler_rows(workbook[sn], _MAX_SCAN)) for sn in sheets]
        homogeneo = bool(topos) and (sum(1 for t in topos if t <= 1) > len(topos) / 2)

    return Rota(homogeneo=homogeneo, sheets_dados=sheets)
