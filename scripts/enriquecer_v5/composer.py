"""Enriquecimento append-only das descrições da lista padrão (build-time).

O texto da v1 é preservado verbatim no início; só se acrescenta depois. A
discriminação dentro da família (neutro/fase) vem do texto v1 preservado, então
o compositor NÃO precisa reparsear sufixos.
"""
from __future__ import annotations

import re

from ansi_ref import ANSI_C37_2, CONFLITO_V1, SINONIMOS_ANSI
from mapa_dominio import MAPA

_PREFIXO_ANSI = re.compile(r"^\s*(\d{2})")
_AJUSTE = re.compile(r"^\s*AJUSTE\s+PARA\s+(.+)$", re.IGNORECASE)
_CODIGOS_EMBUTIDOS = re.compile(r"\b(\d{2})[A-Z]?\b")
_SEP = re.compile(r"\s[—-]\s")

# grandeza (token inicial da descrição analógica) -> (sinônimos, unidade real|None)
# POTENCIA fica sem unidade: ativa=W, reativa=VAr, aparente=VA — ambíguo pelo
# heurístico de 1º token, então não força unidade errada.
_GRANDEZA_ANALOG: dict[str, tuple[tuple[str, ...], str | None]] = {
    "CORRENTE": (("AMPERAGEM",), "A"), "TENSAO": (("VOLTAGEM",), "V"), "TENSÃO": (("VOLTAGEM",), "V"),
    "POTENCIA": (("POTÊNCIA",), None), "POTÊNCIA": (("POTÊNCIA",), None),
    "TEMPERATURA": (("TÉRMICO",), "°C"), "FREQUENCIA": (("FREQUÊNCIA",), "HZ"), "FREQUÊNCIA": (("FREQUÊNCIA",), "HZ"),
    "ANGULO": (("FASE",), "GRAUS"), "ÂNGULO": (("FASE",), "GRAUS"),
}


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


def _enriquecer_ajuste(v1: str, alvo: str) -> str:
    return f"{v1} — AJUSTE/PARAMETRIZAÇÃO (SETTING) DA FUNÇÃO/ALIMENTADOR {alvo.strip()}"


def _enriquecer_composto(v1: str) -> str | None:
    header = _SEP.split(v1, maxsplit=1)[0]  # códigos compostos só no cabeçalho
    cods = [int(c) for c in _CODIGOS_EMBUTIDOS.findall(header) if int(c) in ANSI_C37_2]
    if len(set(cods)) < 2:   # composto = 2+ códigos ANSI distintos no cabeçalho
        return None
    vistos: list[str] = []
    for c in dict.fromkeys(cods):  # únicos, ordem
        vistos.append(f"ANSI {c} {ANSI_C37_2[c]}")
    return f"{v1} — " + "; ".join(vistos)


def _enriquecer_analogico(v1: str) -> str | None:
    tok = v1.strip().split()[0].upper() if v1.strip() else ""
    grandeza = _GRANDEZA_ANALOG.get(tok)
    if not grandeza:
        return None
    syn, unidade = grandeza
    extra = f" — MEDIÇÃO {', '.join(syn)}"
    if unidade:
        extra += f", {unidade}"
    return v1 + extra


def enriquecer(v1: str, sheet: str, sigla: str = "") -> tuple[str, int | None]:
    """Dispatch com ordem: composto (2+ códigos ANSI) -> ANSI-single -> AJUSTE -> analógico -> mapa de domínio (cauda) -> v1."""
    comp = _enriquecer_composto(v1)        # 2+ códigos ANSI distintos -> composto
    if comp is not None:
        return comp, None
    code = base_ansi(v1)
    if code is not None and (code in ANSI_C37_2 or code in CONFLITO_V1):
        return enriquecer_ansi(v1, code)
    m = _AJUSTE.match(v1 or "")
    if m:
        return _enriquecer_ajuste(v1, m.group(1)), None
    if sheet == "AnalogSignals":
        ana = _enriquecer_analogico(v1)
        if ana is not None:
            return ana, None
    termos = MAPA.get((sigla or "").strip().upper())
    if termos:
        return f"{v1} — {termos}", None
    return v1, None  # cauda idiossincrática sem entrada no mapa — preserva v1
