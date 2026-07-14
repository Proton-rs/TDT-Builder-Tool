"""Identidade e tipo do módulo (determinístico).

Resolve o nome real do módulo a partir do nome da sheet (prefixo canônico +
número) e classifica num de TIPOS_MODULO. Funções puras; tabelas vêm de
config. Sheets slot (módulo por linha, tag `coluna:MODULO_POR_LINHA`) são
tratadas por `_identidade_por_linha`, que canoniza e classifica por grupo de
módulo. O campo `ResolucaoModulo.por_linha` em si continua sem uso — essa
atribuição por linha acontece em `estruturar()`, não por esse campo.
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
    canonico: bool = False  # True só quando saiu das estratégias 1/2 (SP-CVA2 E5.1)


_SUFIXO_RUIDO = re.compile(
    r"\s*-\s*\d+(?:[.,]\d+)?\s*KV\b|\s*\((?:FUTURO|RESERVA)\)",
    re.IGNORECASE,
)


def _limpar_modulo(valor: str) -> str:
    """Remove sufixos de ruído (classe de tensão, (FUTURO)/(RESERVA)) e
    colapsa espaços. Usado só no ramo explícito (coluna de módulo)."""
    return " ".join(_SUFIXO_RUIDO.sub("", valor).split())


def canonizar_modulo(valor: str, config: Config, *, explicito: bool = False) -> ResolucaoModulo:
    """Canoniza um NOME de módulo (de sheet_name OU de célula da coluna Módulo).

    Estratégia 1: alias direto por nome inteiro normalizado (mapa_sheet_modulo).
    Estratégia 2: prefixo mapeado seguido do número do módulo.
    Sem canonização:
      - explicito=False (sheet_name): valor CRU, confiança BAIXA  [inalterado]
      - explicito=True  (coluna):     valor cru LIMPO, confiança ALTA
    """
    toks = _tokens(valor)
    chave = "".join(toks)
    if chave in config.mapa_sheet_modulo:
        return ResolucaoModulo(nome=config.mapa_sheet_modulo[chave], confianca="alta", canonico=True)
    ocorr = [
        (i, config.mapa_prefixo_modulo[t])
        for i, t in enumerate(toks)
        if t.isalpha() and t in config.mapa_prefixo_modulo
    ]
    canonicos = {c for _, c in ocorr}
    if len(canonicos) == 1:
        nums = {
            toks[i + 1] for i, _ in ocorr
            if i + 1 < len(toks) and toks[i + 1].isdigit()
        }
        if len(nums) == 1:
            (prefixo,) = canonicos
            (num,) = nums
            return ResolucaoModulo(nome=f"{prefixo}{num}", confianca="alta", canonico=True)
    if explicito:
        return ResolucaoModulo(nome=_limpar_modulo(valor), confianca="alta")
    return ResolucaoModulo(nome=valor, confianca="baixa")


def resolver_modulo(sheet_name: str, rows: list[tuple], config: Config) -> ResolucaoModulo:
    """Resolve o nome real do módulo a partir do nome da sheet."""
    return canonizar_modulo(sheet_name, config)


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


def _identidade_por_linha(
    sinais: list[SignalRecord], config: Config
) -> tuple[list[SignalRecord], list[str]]:
    """Gênero módulo-por-coluna: canoniza cada nome (explícito), SANEIA os que
    não canonizam pro módulo dominante da sheet (SP-CVA2 E5.1 — evita módulo
    lixo tipo 'BC1_CORRENTE_IB') e classifica o tipo POR GRUPO de módulo."""
    resolvidos: list[tuple[SignalRecord, ResolucaoModulo | None]] = []
    for s in sinais:
        if s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" and s.modulo.nome:
            resolvidos.append((s, canonizar_modulo(s.modulo.nome, config, explicito=True)))
        else:
            resolvidos.append((s, None))

    canonicos = [r.nome for _, r in resolvidos if r is not None and r.canonico and r.nome]
    dominante = max(set(canonicos), key=canonicos.count) if canonicos else None

    avisos: list[str] = []
    canon: list[SignalRecord] = []
    for s, res in resolvidos:
        if res is None:
            canon.append(s)
            continue
        nome = res.nome
        if not res.canonico and dominante is not None:
            avisos.append(
                f"{s.id}: módulo {s.modulo.nome!r} fora do padrão — saneado para {dominante!r}"
            )
            nome = dominante
        s = replace(s, modulo=replace(s.modulo, nome=nome))
        if not nome:
            # Canonizou para vazio (ex.: célula era só sufixo de classe de
            # tensão) -- equivale a módulo ausente, mesma trilha de revisão
            # do caminho de célula vazia em estruturador.py.
            s = replace(s, status="revisao", justificativa="modulo_indefinido")
        canon.append(s)

    grupos: dict[str, list[SignalRecord]] = {}
    for s in canon:
        grupos.setdefault(s.modulo.nome or "", []).append(s)
    tipo_de = {nome: classificar_tipo(nome, regs, config) for nome, regs in grupos.items()}
    return [
        replace(s, modulo=replace(s.modulo, tipo=tipo_de[s.modulo.nome or ""]))
        for s in canon
    ], avisos


def aplicar_identidade(
    sinais: list[SignalRecord], sheet_name: str, rows: list[tuple], config: Config
) -> tuple[list[SignalRecord], str, list[str]]:
    if any(s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" for s in sinais):
        novos, avisos = _identidade_por_linha(sinais, config)
        return novos, "alta", avisos
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
    return com_tipo, (res.confianca if veio_de_sheet else "alta"), []


def aviso_divergencia_sheet(
    sheet_name: str, sinais: list[SignalRecord], config: Config
) -> str | None:
    """Aviso quando o módulo dominante do CONTEÚDO (coluna por linha) diverge
    do nome canônico da sheet — caso real BC2 rotulada BC1 na origem
    (SP-CVA2 E5.2). Não corrige: o operador decide (renomear em lote)."""
    res_sheet = canonizar_modulo(sheet_name, config)
    if not res_sheet.canonico:
        return None
    nomes = [
        s.modulo.nome for s in sinais
        if s.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" and s.modulo.nome
    ]
    if not nomes:
        return None
    dominante = max(set(nomes), key=nomes.count)
    if dominante == res_sheet.nome or nomes.count(dominante) / len(nomes) < 0.5:
        return None
    return (
        f"Sheet {sheet_name}: conteúdo rotulado {dominante!r} diverge do nome da "
        f"sheet ({res_sheet.nome!r}) — verificar módulo na planilha de origem"
    )


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
