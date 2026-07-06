"""Tela Geração (etapa 3): resumo, avisos acionáveis, gera TDT + auditoria.

ponytail: carregar() reconstrói tudo do zero a cada navegação; sem cache.
"""

from __future__ import annotations


def enderecos_duplicados(registros) -> dict[tuple[str, int], list[str]]:
    """(direcao, indice) -> ids dos registros que repetem o índice.

    "in" cobre enderecamento.indices; "out" cobre indices_saida. Direções
    não se misturam (input 14 + output 14 não é duplicata).
    """
    por_chave: dict[tuple[str, int], list[str]] = {}
    for r in registros:
        for i in r.enderecamento.indices:
            por_chave.setdefault(("in", i), []).append(r.id)
        for i in r.enderecamento.indices_saida:
            por_chave.setdefault(("out", i), []).append(r.id)
    return {k: v for k, v in por_chave.items() if len(v) > 1}
