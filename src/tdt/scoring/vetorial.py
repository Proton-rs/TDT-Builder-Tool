"""Scorer vetorial: busca a descrição normalizada no índice FAISS da lista padrão.

Devolve candidatos com score = similaridade de cosseno (clampada em [0, 1]).
"""

from __future__ import annotations

from tdt.contracts import Candidato, SignalRecord
from tdt.dados.indice_vetorial import IndiceVetorial


def pontuar(rec: SignalRecord, indice: IndiceVetorial, k: int = 5) -> list[Candidato]:
    hits = indice.buscar(rec.descricoes.normalizada, k)
    return [Candidato(sigla, max(0.0, score), "vetorial") for sigla, score in hits]
