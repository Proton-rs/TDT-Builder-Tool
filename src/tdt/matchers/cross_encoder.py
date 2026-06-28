"""DEPRECATED — não usar em produção.

Benchmark mostrou que o reranker mmarco piora o matching (acc@1: 82% → 36%).
Mantido apenas para referência histórica; o pipeline de produção não chama
este módulo.

Reranker cross-encoder: reordena os top-k candidatos pontuando o par
(descrição do sinal, descrição ADMS do candidato) conjuntamente.

Padrão retrieve-then-rerank: o bi-encoder/tfidf/fuzzy recupera candidatos, o
cross-encoder dá a precisão final. ``scorer`` é injetável (callable que recebe
pares (query, doc) e devolve scores) — produção usa um CrossEncoder; testes um
fake. Scores passam por sigmoide para cair em [0, 1].
"""

from __future__ import annotations

import math
from typing import Callable

from tdt.contracts import Candidato, SignalRecord

Scorer = Callable[[list[tuple[str, str]]], list[float]]


def _sigmoide(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def rerank(
    rec: SignalRecord,
    candidatos: list[Candidato],
    descricao_por_sigla: dict[str, str],
    scorer: Scorer,
) -> list[Candidato]:
    if not candidatos:
        return []
    query = rec.descricoes.normalizada
    pares = [(query, descricao_por_sigla.get(c.sigla, "")) for c in candidatos]
    scores = scorer(pares)
    rerankeados = [
        Candidato(c.sigla, _sigmoide(float(s)), "rerank")
        for c, s in zip(candidatos, scores)
    ]
    return sorted(rerankeados, key=lambda c: c.score, reverse=True)
