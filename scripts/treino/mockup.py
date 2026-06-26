"""Gera dataset rotulado de descrições corrompidas em 5 níveis cumulativos.

Determinístico: a semente é uma STRING (random.Random(str) é estável entre
processos, ao contrário de hash(tuple) que é salgado por PYTHONHASHSEED).
"""
from __future__ import annotations

import random

from corrupt import (
    _abreviar, _sinonimo, _reordenar, _ruido_equip,
    _sufixo_estado, _remover_tokens, _ansi_parens, _typo,
)

# classe nova introduzida em cada nível (cumulativo)
_CLASSES = {
    2: [_abreviar, _sinonimo],
    3: [_reordenar, _ruido_equip, _sufixo_estado],
    4: [_remover_tokens, _ansi_parens, _typo],
    5: [_remover_tokens, _ruido_equip, _typo, _reordenar],  # agressivo
}


def _norm_trivial(texto: str) -> str:
    return " ".join(texto.split()).strip()


def corromper(texto: str, nivel: int, rng: random.Random) -> str:
    out = _norm_trivial(texto)
    for n in range(2, nivel + 1):
        for fn in _CLASSES.get(n, ()):
            out = fn(out, rng)
    return _norm_trivial(out)


def gerar_dataset(pares, niveis=(1, 2, 3, 4, 5), n_variantes=3, seed=0):
    ds: list[tuple[str, str, int]] = []
    for desc, sigla in pares:
        for nivel in niveis:
            for v in range(n_variantes):
                rng = random.Random(f"{sigla}|{nivel}|{v}|{seed}")
                ds.append((corromper(desc, nivel, rng), sigla, nivel))
    return ds
