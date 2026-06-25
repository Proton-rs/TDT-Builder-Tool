"""Tokenização com regras regex para reconstruir siglas separadas.

Ex.: "67 N" -> "67N", "67 N 1" -> "67N1", "50 BF" -> "50BF". Evita fundir
números soltos de equipamento (ex.: "52 3" permanece "52", "3").
"""

from __future__ import annotations

import re

# número (2-3 dígitos) + 1-2 letras separados por espaço -> junta
_NUM_LETRA = re.compile(r"\b(\d{2,3})\s+([A-Z]{1,2})\b")
# sigla (num+letras) + dígito de estágio separado -> junta
_SIGLA_DIGITO = re.compile(r"\b(\d{2,3}[A-Z]{1,2})\s+(\d)\b")


def tokenizar(descricao: str) -> list[str]:
    if not descricao:
        return []
    texto = _NUM_LETRA.sub(r"\1\2", descricao)
    texto = _SIGLA_DIGITO.sub(r"\1\2", texto)
    return texto.split()
