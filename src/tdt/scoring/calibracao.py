"""Calibração de scores para [0,1] comparável antes da mescla.

tfidf-cosine, e5-cosine e fuzzy-ratio vivem em escalas diferentes (e5 comprime
em ~0.8-0.9). Mesclar scores crus dá peso enganoso ao método de escala mais
larga e mata o gap do método comprimido (e5 sozinho decide 0%). Calibrar cada
distribuição para [0,1] devolve spread e gap ao sinal comprimido.

Funções puras, sem estado. ``params`` é por método, passado pelo chamador
(dict simples ou None p/ defaults).
"""

from __future__ import annotations

import math
from typing import Any

# Temperatura default p/ temperature scaling — baixa o suficiente p/ alargar
# a faixa comprimida do e5 sem saturar.
_T_DEFAULT = 0.1


def _minmax(scores: list[float]) -> list[float]:
    lo = min(scores)
    hi = max(scores)
    faixa = hi - lo
    if faixa == 0.0:
        # ponytail: distribuição plana não tem o que espalhar; tudo vira 0.
        return [0.0 for _ in scores]
    return [(s - lo) / faixa for s in scores]


def _temperature(scores: list[float], params: Any) -> list[float]:
    t = _T_DEFAULT
    if params and "T" in params:
        t = float(params["T"])
    # softmax com temperatura: T baixo => distribuição mais picada (mais spread
    # relativo entre os scores). Estável contra overflow via shift pelo máximo.
    m = max(scores)
    exps = [math.exp((s - m) / t) for s in scores]
    soma = sum(exps)
    return [e / soma for e in exps]


def calibrar(scores: list[float], metodo: str, params: Any) -> list[float]:
    """Calibra ``scores`` para uma escala comparável.

    ``metodo``:
      - ``"minmax"``: min-max sobre a distribuição -> [0,1] com o top em 1.0.
        ``params`` ignorado.
      - ``"temperature"``: temperature scaling (softmax/T). ``params`` aceita
        ``{"T": float}``; ausente usa o default.

    Função pura. Lista vazia -> lista vazia.
    """
    if not scores:
        return []
    if metodo == "minmax":
        return _minmax(scores)
    if metodo == "temperature":
        return _temperature(scores, params)
    raise ValueError(f"método de calibração desconhecido: {metodo!r}")
