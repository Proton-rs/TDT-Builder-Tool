"""Identidade e tipo do módulo (determinístico).

Resolve o nome real do módulo a partir do nome da sheet (prefixo canônico +
número) e classifica num de TIPOS_MODULO. Funções puras; tabelas vêm de
config. Sheets slot (módulo por linha) ficam para o follow-up — `por_linha`
já existe na assinatura, sempre None aqui.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from tdt.config import Config
from tdt.contracts import ItemRevisao, SignalRecord

_TOKENS = re.compile(r"[A-Za-z]+|\d+")


def _tokens(s: str) -> list[str]:
    return _TOKENS.findall(s.upper())


@dataclass(frozen=True)
class ResolucaoModulo:
    nome: str
    confianca: str  # "alta" | "baixa"
    por_linha: dict[int, str] | None = None  # slot (follow-up); None aqui


def resolver_modulo(sheet_name: str, rows: list[tuple], config: Config) -> ResolucaoModulo:
    toks = _tokens(sheet_name)
    numeros = [t for t in toks if t.isdigit()]
    alphas = [t for t in toks if t.isalpha()]
    prefixo = next(
        (config.mapa_prefixo_modulo[a] for a in alphas if a in config.mapa_prefixo_modulo),
        None,
    )
    if prefixo and numeros:
        return ResolucaoModulo(nome=f"{prefixo}{numeros[0]}", confianca="alta")
    return ResolucaoModulo(nome=sheet_name, confianca="baixa")
