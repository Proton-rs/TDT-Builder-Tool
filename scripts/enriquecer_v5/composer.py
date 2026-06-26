"""Enriquecimento append-only das descrições da lista padrão (build-time).

O texto da v1 é preservado verbatim no início; só se acrescenta depois. A
discriminação dentro da família (neutro/fase) vem do texto v1 preservado, então
o compositor NÃO precisa reparsear sufixos.
"""
from __future__ import annotations

import re

from ansi_ref import ANSI_C37_2, CONFLITO_V1, SINONIMOS_ANSI

_PREFIXO_ANSI = re.compile(r"^\s*(\d{2})")


def base_ansi(desc: str) -> int | None:
    m = _PREFIXO_ANSI.match(desc or "")
    return int(m.group(1)) if m else None


def enriquecer_ansi(v1: str, code: int) -> tuple[str, int | None]:
    if code in CONFLITO_V1:
        return f"{v1} — ANSI {code}", code  # referência neutra + flag, sem função
    func = ANSI_C37_2[code]
    extra = f" — ANSI {code} {func}"
    syn = SINONIMOS_ANSI.get(code, ())
    if syn:
        extra += ", " + ", ".join(syn)
    return v1 + extra, None


def enriquecer(v1: str, sheet: str) -> tuple[str, int | None]:
    """Dispatch. Nesta task só o caminho ANSI; o resto volta inalterado."""
    code = base_ansi(v1)
    if code is not None and (code in ANSI_C37_2 or code in CONFLITO_V1):
        return enriquecer_ansi(v1, code)
    return v1, None
