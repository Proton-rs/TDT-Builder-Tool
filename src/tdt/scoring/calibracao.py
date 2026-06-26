"""Calibração de scores para [0,1] comparável antes da mescla + calibrador de confiança pós-mescla.

tfidf-cosine, e5-cosine e fuzzy-ratio vivem em escalas diferentes (e5 comprime
em ~0.8-0.9). Mesclar scores crus dá peso enganoso ao método de escala mais
larga e mata o gap do método comprimido (e5 sozinho decide 0%). Calibrar cada
distribuição para [0,1] devolve spread e gap ao sinal comprimido.

Inclui calibradores não-supervisionados (minmax, temperature) e treinados
(isotonic, platt). Calibradores treinados são serializados como dict de
parâmetros e aplicados via ``{thresholds_, y_}`` (isotonic) ou
``{coef_, intercept_}`` (platt).

O calibrador de confiança (E4) treina Platt/Isotonic no score mesclado (pós-mescla,
pré-regras) para mapear score → P(correto). O roteador usa a probabilidade calibrada
nos thresholds pct/gap.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from tdt.contracts import Candidato

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


def _isotonic(scores: list[float], params: Any) -> list[float]:
    """Isotonic regression treinado: mapeia score bruto -> prob calibrada.

    ``params`` = ``{"thresholds_": list[float], "y_": list[float]}``
    do sklearn.isotonic.IsotonicRegression fitado.
    """
    if params is None or "thresholds_" not in params:
        return scores
    thresholds = np.array(params["thresholds_"], dtype=float)
    y_vals = np.array(params["y_"], dtype=float)
    # interpolação linear, clipping out-of-bounds
    return [float(np.interp(s, thresholds, y_vals, left=y_vals[0], right=y_vals[-1])) for s in scores]


def _platt(scores: list[float], params: Any) -> list[float]:
    """Platt scaling (regressão logística 1D): 1/(1+exp(-(coef*x+intercept))).

    ``params`` = ``{"coef_": float, "intercept_": float}``
    do sklearn.linear_model.LogisticRegression fitado.
    """
    if params is None or "coef_" not in params:
        return scores
    coef = float(params["coef_"])
    intercept = float(params["intercept_"])
    return [1.0 / (1.0 + math.exp(-(coef * s + intercept))) for s in scores]


def calibrar(scores: list[float], metodo: str, params: Any) -> list[float]:
    """Calibra ``scores`` para uma escala comparável.

    ``metodo``:
      - ``"minmax"``: min-max sobre a distribuição -> [0,1] com o top em 1.0.
        ``params`` ignorado.
      - ``"temperature"``: temperature scaling (softmax/T). ``params`` aceita
        ``{"T": float}``; ausente usa o default (T=0.1).
      - ``"isotonic"``: isotonic regression treinado. ``params`` = ``{"thresholds_": [...], "y_": [...]}``.
      - ``"platt"``: Platt scaling. ``params`` = ``{"coef_": float, "intercept_": float}``.

    Função pura. Lista vazia -> lista vazia.
    """
    if not scores:
        return []
    if metodo == "minmax":
        return _minmax(scores)
    if metodo == "temperature":
        return _temperature(scores, params)
    if metodo == "isotonic":
        return _isotonic(scores, params)
    if metodo == "platt":
        return _platt(scores, params)
    raise ValueError(f"método de calibração desconhecido: {metodo!r}")


def calibrar_candidatos(
    candidatos: list[Candidato], metodo: str, params: Any
) -> list[Candidato]:
    """Aplica ``calibrar`` aos scores de uma lista de Candidatos.

    ``metodo`` vazio ou ``"none"`` retorna os candidatos inalterados.
    """
    if not candidatos or not metodo or metodo == "none":
        return candidatos
    scores = [c.score for c in candidatos]
    calibrados = calibrar(scores, metodo, params)
    return [Candidato(c.sigla, s, c.fonte) for c, s in zip(candidatos, calibrados)]


# --- E4: Calibrador de Confiança (pós-mescla) ---------------------------------

def treinar_calibrador_confianca(
    scores: list[float],
    acertos: list[bool],
    metodo: str = "platt",
) -> dict[str, Any]:
    """Treina calibrador de confiança no score mesclado.

    ``scores`` = merged top-1 scores (pós-mescla, pré-regras).
    ``acertos`` = True se o top-1 é a sigla correta.

    Retorna params serializáveis: ``{metodo: ..., params: {coef_, intercept_}}``
    (Platt) ou ``{metodo: ..., params: {thresholds_, y_}}`` (Isotonic).
    """
    X = np.asarray(scores, dtype=float).reshape(-1, 1)
    y = np.asarray(acertos, dtype=float)
    if metodo == "platt":
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression(C=1e10, solver="lbfgs")
        lr.fit(X, y)
        return {
            "metodo": "platt",
            "params": {"coef_": float(lr.coef_[0][0]), "intercept_": float(lr.intercept_[0])},
        }
    elif metodo == "isotonic":
        from sklearn.isotonic import IsotonicRegression
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(scores, y)
        return {
            "metodo": "isotonic",
            "params": {
                "thresholds_": iso.X_thresholds_.tolist(),
                    "y_": iso.y_thresholds_.tolist(),
            },
        }
    else:
        raise ValueError(f"metodo desconhecido: {metodo}")


def aplicar_calibrador_confianca(
    score: float,
    params: dict[str, Any],
) -> float:
    """Aplica calibrador de confiança treinado a um score mesclado."""
    metodo = params.get("metodo", "platt")
    p = params.get("params", {})
    if metodo == "platt":
        coef = float(p.get("coef_", 1.0))
        intercept = float(p.get("intercept_", 0.0))
        return 1.0 / (1.0 + math.exp(-(coef * score + intercept)))
    elif metodo == "isotonic":
        thresh = np.array(p.get("thresholds_", [0.0, 1.0]), dtype=float)
        yv = np.array(p.get("y_", [0.0, 1.0]), dtype=float)
        return float(np.interp(score, thresh, yv, left=yv[0], right=yv[-1]))
    return score
