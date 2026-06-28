"""Monta SignalRecords a partir das linhas de uma sheet não-homogênea.

Rastreia marcadores de seção na coluna 1 (com sinônimos: Comandos/Controle,
Digitais/Sinalizações, Analógicas/Medidas) para definir categoria e direção.
A coluna 'Tipo' refina linha a linha quando presente. Módulo é constante por
sheet (vem da coluna Módulo).
"""

from __future__ import annotations

import re

from tdt.config import Config
from tdt.contracts import (
    Descricoes,
    Eletrico,
    Enderecamento,
    MapaColunas,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.normalizador import canonizar, extrair_contexto_estrutural
from tdt.vocabulario_tipo import classificar as _classificar, norm as _norm


def _eh_marcador(row: tuple, col0: int) -> bool:
    """col0 tem categoria e o resto da linha está vazio."""
    preenchidas = [i for i, c in enumerate(row) if _norm(c)]
    return preenchidas == [col0] and _classificar(row[col0]) is not None


def _parse_indices(cell) -> tuple[int, ...]:
    if cell is None:
        return ()
    return tuple(int(p) for p in re.findall(r"-?\d+", str(cell)))


def estruturar(
    rows: list[tuple],
    mapa: MapaColunas,
    sheet_name: str,
    config: Config,
    modulo: str | None = None,
    vocab: set[str] | frozenset[str] | None = None,
) -> list[SignalRecord]:
    cols = mapa.colunas
    c_desc = cols.get("descricao")
    c_idx = cols.get("indice")
    c_tipo = cols.get("tipo")
    nome_mod = modulo if modulo is not None else sheet_name
    col0 = 0  # marcadores de seção ficam na 1ª coluna

    registros: list[SignalRecord] = []
    secao: tuple[str, str] = ("Discrete", "Input")  # default
    secao_explicita = False  # virou True quando um marcador de seção foi lido

    for i, row in enumerate(rows):
        if i + 1 <= mapa.header_row:  # pula header e metadados acima
            continue
        if c_desc is None or c_desc >= len(row):
            continue

        if _eh_marcador(row, col0):
            secao = _classificar(row[col0])
            secao_explicita = True
            continue

        bruta = row[c_desc]
        if not _norm(bruta):
            continue

        cat_dir = _classificar(row[c_tipo]) if c_tipo is not None and c_tipo < len(row) else None
        categoria, direcao = cat_dir or secao
        confiavel = cat_dir is not None or secao_explicita

        indices = _parse_indices(row[c_idx]) if c_idx is not None and c_idx < len(row) else ()

        remanescente, ctx_estrutural = extrair_contexto_estrutural(str(bruta))
        eletrico = Eletrico(
            fase=ctx_estrutural.fase,
            equipamento_alvo=ctx_estrutural.equipamento_alvo,
            nome_equipamento=ctx_estrutural.nome_equipamento,
            barra=ctx_estrutural.barra,
        )

        registros.append(
            SignalRecord(
                id=f"{sheet_name}:{i + 1}",
                modulo=Modulo(nome_mod, "sheet_name"),
                tipo_sinal=TipoSinal(categoria, is_double_bit=False, direcao=direcao,
                                     categoria_confiavel=confiavel),
                enderecamento=Enderecamento("DNP3", indices),
                descricoes=Descricoes(str(bruta), canonizar(remanescente, config, vocab)),
                eletrico=eletrico,
            )
        )
    return registros
