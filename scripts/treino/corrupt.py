"""Transforms determinísticos de corrupção de descrição (build-time, tooling de treino)."""
from __future__ import annotations

import random

from tdt.config import ABREVIACOES_PADRAO
from ansi_ref import ANSI_C37_2

# reverso: palavra inteira -> abreviação (1ª que expande p/ ela)
_REV_ABREV: dict[str, str] = {}
for _ab, _full in ABREVIACOES_PADRAO.items():
    _REV_ABREV.setdefault(_full, _ab)

SINONIMOS: dict[str, str] = {
    "DESEQUILIBRIO": "DESBALANCO", "CORRENTE": "CORR", "TENSAO": "TENS",
    "TEMPERATURA": "TEMP", "RELIGAMENTO": "RELIGA", "BLOQUEIO": "BLOQ",
}
IDS_EQUIP: tuple[str, ...] = ("52-1", "01Q0", "01F1", "43TC", "52-2", "IED 01F1")
SUFIXOS_ESTADO: tuple[str, ...] = ("BLOQUEIO", "ABERTO", "FECHADO", "POS. REMOTO", "TRIP")


def _toks(s: str) -> list[str]:
    return s.split()


def _abreviar(texto: str, rng: random.Random) -> str:
    out = []
    for t in _toks(texto):
        u = t.upper()
        if u in _REV_ABREV and rng.random() < 0.7:
            out.append(_REV_ABREV[u])
        elif u in SINONIMOS and rng.random() < 0.5:
            out.append(SINONIMOS[u])
        else:
            out.append(t)
    return " ".join(out)


def _sinonimo(texto: str, rng: random.Random) -> str:
    return " ".join(
        SINONIMOS.get(t.upper(), t) if rng.random() < 0.6 else t for t in _toks(texto)
    )


def _reordenar(texto: str, rng: random.Random) -> str:
    ts = _toks(texto)
    rng.shuffle(ts)
    return " ".join(ts)


def _ruido_equip(texto: str, rng: random.Random) -> str:
    return f"{texto} {rng.choice(IDS_EQUIP)}"


def _sufixo_estado(texto: str, rng: random.Random) -> str:
    return f"{texto} - {rng.choice(SUFIXOS_ESTADO)}"


def _remover_tokens(texto: str, rng: random.Random) -> str:
    ts = _toks(texto)
    if len(ts) <= 2:
        return texto
    n = rng.randint(1, max(1, len(ts) // 3))
    idx = set(rng.sample(range(len(ts)), min(n, len(ts) - 1)))
    return " ".join(t for i, t in enumerate(ts) if i not in idx)


def _ansi_parens(texto: str, rng: random.Random) -> str:
    ts = _toks(texto)
    if ts and ts[0].isdigit() and int(ts[0]) in ANSI_C37_2:
        cod = ts[0]
        resto = [t for t in ts[1:] if t != "-"]
        return (" ".join(resto) + f" ({cod})").strip()
    return texto


def _typo(texto: str, rng: random.Random) -> str:
    if not texto:
        return texto
    i = rng.randrange(len(texto))
    c = texto[i]
    op = rng.choice(("drop", "dup", "swap"))
    if op == "drop" and len(texto) > 1:
        return texto[:i] + texto[i + 1:]
    if op == "dup":
        return texto[:i] + c + texto[i:]
    j = min(i + 1, len(texto) - 1)
    return texto[:i] + texto[j] + texto[i + 1:j] + c + texto[j + 1:]
