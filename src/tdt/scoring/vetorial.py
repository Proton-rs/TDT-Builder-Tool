"""Scorer vetorial: busca a descrição normalizada no índice FAISS da lista padrão.

Devolve candidatos com score = similaridade de cosseno (clampada em [0, 1]).
"""

from __future__ import annotations

import numpy as np

from tdt.contracts import Candidato, SignalRecord
from tdt.dados.indice_vetorial import IndiceVetorial, _normalizar


def pontuar(rec: SignalRecord, indice: IndiceVetorial, k: int = 5) -> list[Candidato]:
    hits = indice.buscar(rec.descricoes.normalizada, k)
    return [Candidato(sigla, max(0.0, score), "vetorial") for sigla, score in hits]


def pontuar_com_embedding(
    embedding: np.ndarray,
    rec: SignalRecord,
    indice: IndiceVetorial,
    k: int = 5,
) -> list[Candidato]:
    """Igual a ``pontuar``, mas usa um embedding já calculado (batch encode)
    em vez de reencodar a descrição — evita uma chamada ao encoder por sinal.
    """
    # ponytail: assume encoder simétrico (embedding já no espaço certo); se
    # encoder_consulta assimétrico for introduzido em IndiceVetorial, esta
    # função precisa aceitar/usar encoder_consulta também — ver IndiceVetorial.buscar()
    q = _normalizar(np.asarray(embedding).reshape(1, -1))
    k = min(k, len(indice._siglas))
    scores, idxs = indice._index.search(q, k)
    hits = [(indice._siglas[i], float(s)) for s, i in zip(scores[0], idxs[0]) if i != -1]
    return [Candidato(sigla, max(0.0, score), "vetorial") for sigla, score in hits]
