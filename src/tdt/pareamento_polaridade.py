"""Forca convergencia de pares ligado/desligado do mesmo equipamento pra
sigla de posicao (ex. DJF1), quando a descricao padrao da sigla e generica
demais pro scorer de texto reconhecer as duas linhas do input (ver SP10).
Roda antes do scoring; e' rede de seguranca, desligavel via Config."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import SignalRecord

_SIGLA_POSICAO: dict[str, str] = {"Disjuntor": "DJF1"}
# Prefixo (não palavra exata): corrigir_typos pode mudar a concordância de
# gênero ("DESLIGADO" -> "DESLIGADA") sem o vocabulário de domínio ter a
# palavra; comparar por prefixo é robusto a essa variação.
_LIGADO_PREFIXOS = ("LIGAD", "FECHAD")
_DESLIGADO_PREFIXOS = ("DESLIGAD", "ABERT")


def _tem_prefixo(tokens: list[str], prefixos: tuple[str, ...]) -> bool:
    return any(tok.startswith(p) for tok in tokens for p in prefixos)


def _chave(rec: SignalRecord) -> tuple | None:
    eq = rec.eletrico.equipamento_alvo
    if eq not in _SIGLA_POSICAO or not rec.eletrico.nome_equipamento:
        return None
    return (rec.modulo.nome, eq, rec.eletrico.nome_equipamento)


def forcar_polaridade_equipamento(
    registros: list[SignalRecord], config: Config,
) -> list[SignalRecord]:
    """Antes do scoring: duas linhas do mesmo equipamento com polaridade
    oposta (ligado/desligado, aberto/fechado) convergem direto pra sigla de
    posicao do equipamento (ex. DJF1), sem depender do scorer de texto."""
    if not config.parear_polaridade_equipamento:
        return registros

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        chave = _chave(rec)
        if chave is not None:
            grupos[chave].append(rec)

    forcados: dict[str, str] = {}
    for chave, grupo in grupos.items():
        ligado = [r for r in grupo if _tem_prefixo(r.descricoes.normalizada.split(), _LIGADO_PREFIXOS)]
        desligado = [r for r in grupo if _tem_prefixo(r.descricoes.normalizada.split(), _DESLIGADO_PREFIXOS)]
        if len(ligado) == 1 and len(desligado) == 1 and ligado[0] is not desligado[0]:
            sigla = _SIGLA_POSICAO[chave[1]]
            forcados[ligado[0].id] = sigla
            forcados[desligado[0].id] = sigla

    if not forcados:
        return registros
    return [
        replace(rec, sigla_sinal=forcados[rec.id], status="decidido") if rec.id in forcados else rec
        for rec in registros
    ]
