"""Expansão de candidatos com variantes de estágio/sufixo (childs).

Exemplo: se ``81`` está entre os candidatos, expande para incluir
``81E1``, ``81E2``, ``81SU``, ``81_T``, ``81U1``, ``81U5``, etc.
(desde que existam na lista padrão).

A expansão permite que o motor de regras / filtro escolha a variante
correta com base nos tokens do texto (ESTAGIO 1 → 81E1, etc.).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from tdt.contracts import Candidato

if TYPE_CHECKING:
    from tdt.dados.lista_padrao import ListaPadraoADMS


def _extrair_prefixo(sigla: str) -> str | None:
    """Extrai prefixo numérico de uma sigla (ex: '67N1' → '67', '81_T' → '81')."""
    digitos = ""
    for ch in sigla:
        if ch.isdigit():
            digitos += ch
        else:
            break
    if len(digitos) < 2:
        return None
    return digitos[:2]  # os 2 primeiros dígitos definem o grupo


def _indice_prefixo(lp: "ListaPadraoADMS") -> dict[str, set[str]]:
    """Constrói índice {prefixo: {sigla1, sigla2, ...}} da lista padrão."""
    idx: dict[str, set[str]] = {}
    for s in (*lp.discretos, *lp.analogicos):
        p = _extrair_prefixo(s.sigla)
        if p is not None:
            idx.setdefault(p, set()).add(s.sigla.upper())
    return idx


_INDICE_CACHE: dict[int, dict[str, set[str]]] = {}
"""Cache do índice por id(lp) — evita reconstruir a cada chamada."""


def expandir(
    candidatos: list[Candidato],
    lista_padrao: "ListaPadraoADMS",
    fator_score: float = 0.9,
) -> list[Candidato]:
    """Expande candidatos com variantes da mesma família de prefixo.

    Candidatos expandidos recebem ``fonte="expandido"`` e score reduzido
    (``score * fator_score`` do pai, ou ``0.0`` se adicionados independentes).
    """
    if not candidatos:
        return candidatos

    lp_id = id(lista_padrao)
    if lp_id not in _INDICE_CACHE:
        _INDICE_CACHE[lp_id] = _indice_prefixo(lista_padrao)
    idx = _INDICE_CACHE[lp_id]

    siglas_existentes: set[str] = {c.sigla.upper() for c in candidatos}
    adicoes: list[Candidato] = []
    pai_por_sigla: dict[str, Candidato] = {}  # pai de maior score p/ cada child

    for cand in candidatos:
        p = _extrair_prefixo(cand.sigla)
        if p is None or p not in idx:
            continue
        for child in idx[p]:
            if child in siglas_existentes:
                continue
            antigo = pai_por_sigla.get(child)
            if antigo is None or cand.score > antigo.score:
                pai_por_sigla[child] = cand

    for child, pai in pai_por_sigla.items():
        adicoes.append(replace(pai, sigla=child, score=pai.score * fator_score, fonte="expandido"))

    return candidatos + adicoes
