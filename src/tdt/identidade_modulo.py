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
    # Estratégia 1: alias direto por sheet_name inteiro normalizado (mais
    # específica — checa primeiro). Cobre sheet_names que não decompõem em
    # prefixo+número de forma confiável: bay/vão sem número de módulo
    # ("01F1_GTA_P" -> "LTGTA"), número embutido que NÃO é o nº do módulo
    # ("IB_23kV": 23 é a tensão, não o módulo -> "IB"), siglas próprias
    # ("87B_AT" -> "87BAT"). Exato/literal por sheet_name — sem ambiguidade,
    # confirmado contra os dados reais (coluna de módulo + ground-truth TDT
    # exportado). Tabela em config.mapa_sheet_modulo.
    chave = "".join(toks)
    if chave in config.mapa_sheet_modulo:
        return ResolucaoModulo(nome=config.mapa_sheet_modulo[chave], confianca="alta")
    # Estratégia 2: posicional — prefixo mapeado seguido do número do módulo.
    # Sufixos de barra/proteção (_P1, _P2) adicionam números que NÃO são o nº
    # do módulo — por isso usamos o número imediatamente após o prefixo, não
    # "exatamente um número global".
    ocorr = [
        (i, config.mapa_prefixo_modulo[t])
        for i, t in enumerate(toks)
        if t.isalpha() and t in config.mapa_prefixo_modulo
    ]
    canonicos = {c for _, c in ocorr}
    # alta confiança só sem ambiguidade: uma única família canônica (sinônimos
    # contam como uma) e um único nº DEPOIS de um prefixo mapeado. Assim "AL
    # FWB15"->AL15 (sinônimo), "BC1_P1"->BC1 (sufixo de barra ignorado, só o nº
    # após BC conta) e "SPS_TR1_TR2"->baixa (TR seguido de 1 e de 2, ambíguo).
    if len(canonicos) == 1:
        nums = {
            toks[i + 1] for i, _ in ocorr
            if i + 1 < len(toks) and toks[i + 1].isdigit()
        }
        if len(nums) == 1:
            (prefixo,) = canonicos
            (num,) = nums
            return ResolucaoModulo(nome=f"{prefixo}{num}", confianca="alta")
    return ResolucaoModulo(nome=sheet_name, confianca="baixa")


def classificar_tipo(modulo_nome: str, registros: list[SignalRecord], config: Config) -> str:
    # 1. por nome completo (ex.: "87BAT") ou por prefixo/token do nome do
    # módulo. Nome completo primeiro: alguns módulos (87B_AT -> "87BAT") não
    # tokenizam num prefixo alfabético isolado (87 e BAT ficam juntos), então
    # tipo_por_prefixo também aceita o nome inteiro como chave.
    nome_norm = "".join(_tokens(modulo_nome))
    if nome_norm in config.tipo_por_prefixo:
        return config.tipo_por_prefixo[nome_norm]
    for tok in _tokens(modulo_nome):
        if tok in config.tipo_por_prefixo:
            return config.tipo_por_prefixo[tok]
    # 2. por conteúdo (palavras-chave nas descrições normalizadas) — match por
    # token inteiro, não substring (evita "LINHA" casar em "DESALINHADA").
    tokens_texto = set()
    for r in registros:
        tokens_texto.update(_tokens(r.descricoes.normalizada))
    for tipo, palavras in config.palavras_chave_tipo.items():
        if any(p in tokens_texto for p in palavras):
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
        novos = [
            replace(s, tipo_sinal=replace(s.tipo_sinal, categoria_confiavel=False))
            for s in sinais
        ]
        return novos, [ItemRevisao(s, motivo="modulo_indefinido") for s in novos]
    return sinais, []
