"""Funde candidatos de N métodos de scoring (TF-IDF, vetorial, fuzzy...).

Soma ponderada por sigla (faltante = 0), complementando os pontos fortes de
cada método. Resultado ordenado desc, fonte="mesclado".
"""

from __future__ import annotations

from tdt.contracts import Candidato


def mesclar(fontes: list[tuple[list[Candidato], float]]) -> list[Candidato]:
    """``fontes`` = lista de (candidatos, peso)."""
    acc: dict[str, float] = {}
    for candidatos, peso in fontes:
        for c in candidatos:
            acc[c.sigla] = acc.get(c.sigla, 0.0) + peso * c.score
    fundidos = [Candidato(s, v, "mesclado") for s, v in acc.items()]
    return sorted(fundidos, key=lambda c: c.score, reverse=True)
