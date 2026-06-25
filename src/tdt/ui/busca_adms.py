"""Busca na Lista Padrão ADMS por sigla e por texto da descrição.

ponytail: varredura linear sobre a lista (alguns milhares de itens); sem índice.
"""

from __future__ import annotations

import unicodedata

from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao


def _norm(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto or "")
    sem_acento = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sem_acento.upper()


def buscar(lp: ListaPadraoADMS, termo: str, limite: int = 30) -> list[SinalPadrao]:
    alvo = _norm(termo).strip()
    todos = list(lp.discretos) + list(lp.analogicos)
    if not alvo:
        return todos[:limite]
    por_sigla: list[SinalPadrao] = []
    por_desc: list[SinalPadrao] = []
    for s in todos:
        if alvo in _norm(s.sigla):
            por_sigla.append(s)
        elif alvo in _norm(s.descricao):
            por_desc.append(s)
    return (por_sigla + por_desc)[:limite]
