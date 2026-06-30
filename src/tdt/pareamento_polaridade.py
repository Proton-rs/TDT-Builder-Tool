"""Forca convergencia de pares aberto/fechado do mesmo equipamento pra
sigla de posicao (ex. DJF1, SECC), quando a descricao padrao da sigla e generica
demais pro scorer de texto reconhecer as duas linhas do input (ver SP10).
Roda antes do scoring; e' rede de seguranca, desligavel via Config."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import ItemRevisao, SignalRecord

# Prefixo (não palavra exata): robusto a "FECHADO"/"FECHADA", "DESLIGADO"/"DESLIGADA"
# e a variações que corrigir_typos possa introduzir.
_LIGADO_PREFIXOS = ("LIGAD", "FECHAD")
_DESLIGADO_PREFIXOS = ("DESLIGAD", "ABERT")

# Seccionadora: keyword (prefixo de token) → sigla de posição.
# Ordenada por especificidade decrescente — "BYPASS" antes de "BY" para
# que "BY PASS" não caia no genérico "BY" antes do check de prefixo.
# Robustez: "BYPS", "BY-PASS", "BY PASS" todos começam com "BY".
_SECC_KEYWORDS: list[tuple[str, str]] = [
    ("BYPASS",    "SECB"),
    ("BY",        "SECB"),   # BY PASS / BY-PASS / BYPS
    ("CARG",      "SECC"),   # CARGA / CARG
    ("TRANSFER",  "SECT"),   # TRANSFERENCIA / TRANSFER (NÃO "TRANSF": exclui TRANSFORMADOR)
    ("ATERR",     "SECG"),   # ATERRAMENTO
    ("TERRA",     "SECG"),
    ("FONT",      "SECF"),   # FONTE / FONT
    ("INTERBAR",  "SECI"),   # INTERBARRAS / INTERBARRA
    ("INTERLINHA","SECL"),
]


def _tem_prefixo(tokens: list[str], prefixos: tuple[str, ...]) -> bool:
    return any(tok.startswith(p) for tok in tokens for p in prefixos)


def _chave(rec: SignalRecord) -> tuple | None:
    eq = rec.eletrico.equipamento_alvo
    if eq not in ("Disjuntor", "Seccionadora") or not rec.eletrico.nome_equipamento:
        return None
    return (rec.modulo.nome, eq, rec.eletrico.nome_equipamento)


def _sigla_disjuntor(tokens_combined: list[str]) -> str:
    """DJA1 se algum token for exatamente "NA" (normalmente aberto), DJF1 default."""
    if "NA" in tokens_combined:
        return "DJA1"
    return "DJF1"


def _sigla_seccionadora(desc_combinada: str) -> str | None:
    """Resolve a variante SEC* pela palavra-função. None se ambíguo."""
    tokens = desc_combinada.upper().split()
    for kw, sigla in _SECC_KEYWORDS:
        if any(tok.startswith(kw) for tok in tokens):
            return sigla
    return None


def forcar_polaridade_equipamento(
    registros: list[SignalRecord], config: Config,
) -> tuple[list[SignalRecord], list[ItemRevisao]]:
    """Antes do scoring: duas linhas do mesmo equipamento com polaridade
    oposta (fechado/aberto, ligado/desligado) convergem para a sigla de
    posição do equipamento (ex. DJF1, SECC), sem depender do scorer de texto.

    Retorna (sinais_restantes, itens_revisao):
    - sinais forçados: status="decidido", sigla_sinal=<sigla>
    - par detectado mas variante ambígua (Seccionadora sem keyword): revisão "posicao_ambigua"
    - sem par completo ou flag desligada: passam intactos para o scorer
    """
    if not config.parear_polaridade_equipamento:
        return registros, []

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        chave = _chave(rec)
        if chave is not None:
            grupos[chave].append(rec)

    forcados: dict[str, str] = {}
    ambiguos: set[str] = set()

    for chave, grupo in grupos.items():
        eq = chave[1]  # "Disjuntor" | "Seccionadora"
        ligado = [r for r in grupo if _tem_prefixo(r.descricoes.normalizada.split(), _LIGADO_PREFIXOS)]
        desligado = [r for r in grupo if _tem_prefixo(r.descricoes.normalizada.split(), _DESLIGADO_PREFIXOS)]
        if not (len(ligado) == 1 and len(desligado) == 1 and ligado[0] is not desligado[0]):
            continue  # par incompleto ou múltiplo — scorer decide

        par = (ligado[0], desligado[0])
        desc_comb = " ".join(r.descricoes.normalizada.upper() for r in par)

        if eq == "Disjuntor":
            sigla = _sigla_disjuntor(desc_comb.split())
            for r in par:
                forcados[r.id] = sigla
        else:  # Seccionadora
            sigla = _sigla_seccionadora(desc_comb)
            if sigla is not None:
                for r in par:
                    forcados[r.id] = sigla
            else:
                # par detectado mas variante não reconhecida — revisão explícita
                for r in par:
                    ambiguos.add(r.id)

    revisao = [
        ItemRevisao(rec, motivo="posicao_ambigua")
        for rec in registros
        if rec.id in ambiguos
    ]
    saida = [
        replace(rec, sigla_sinal=forcados[rec.id], status="decidido")
        if rec.id in forcados
        else rec
        for rec in registros
        if rec.id not in ambiguos
    ]
    return saida, revisao
