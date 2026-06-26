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


def classificar_tipo(modulo_nome: str, registros: list[SignalRecord], config: Config) -> str:
    # 1. por prefixo do nome do módulo
    for tok in _tokens(modulo_nome):
        if tok in config.tipo_por_prefixo:
            return config.tipo_por_prefixo[tok]
    # 2. por conteúdo (palavras-chave nas descrições normalizadas)
    texto = " ".join(r.descricoes.normalizada for r in registros).upper()
    for tipo, palavras in config.palavras_chave_tipo.items():
        if any(p in texto for p in palavras):
            return tipo
    # 3. fallback
    return "Outros"


def aplicar_identidade(
    sinais: list[SignalRecord], sheet_name: str, rows: list[tuple], config: Config
) -> tuple[list[SignalRecord], str]:
    res = resolver_modulo(sheet_name, rows, config)
    # nome: resolve só onde veio do nome da sheet; preserva módulo de coluna.
    com_nome = [
        replace(s, modulo=replace(s.modulo, nome=res.nome))
        if s.modulo.origem_contexto == "sheet_name"
        else s
        for s in sinais
    ]
    nome_ref = com_nome[0].modulo.nome if com_nome else res.nome
    tipo = classificar_tipo(nome_ref or "", com_nome, config)
    com_tipo = [replace(s, modulo=replace(s.modulo, tipo=tipo)) for s in com_nome]
    # confiança só importa quando o nome veio da sheet (caminho não-homogêneo).
    veio_de_sheet = any(s.modulo.origem_contexto == "sheet_name" for s in sinais)
    return com_tipo, (res.confianca if veio_de_sheet else "alta")


def particionar_por_confianca(
    sinais: list[SignalRecord], confianca: str
) -> tuple[list[SignalRecord], list[ItemRevisao]]:
    if confianca == "baixa":
        return [], [ItemRevisao(s, motivo="modulo_indefinido") for s in sinais]
    return sinais, []
