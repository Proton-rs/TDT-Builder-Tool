"""Repareamento em lote da revisão (SP-OBS-17JUL P3): reusa o pipeline puro
(fundir_pares_posicao + dc_pairer.parear) sobre um subconjunto elegível.
NUNCA desfaz par existente nem edição do usuário (CLAUDE.md fluxo de dados)."""
from dataclasses import dataclass, replace

from tdt.config import Config
from tdt.contracts import SignalRecord
from tdt.dc_pairer import parear
from tdt.normalizador_estrutural import fundir_pares_posicao


@dataclass(frozen=True)
class ResultadoReparear:
    resultantes: tuple[SignalRecord, ...]
    n_fundidos: int
    n_ambiguos: int
    n_sem_par: int


def elegivel(rec: SignalRecord) -> bool:
    if not rec.sigla_sinal:
        return False
    d = rec.tipo_sinal.direcao
    if d == "Input":
        return not rec.enderecamento.indices_saida
    return d == "Output"


def reparear(elegiveis, whitelist_posicao, config: Config) -> ResultadoReparear:
    pos = fundir_pares_posicao(list(elegiveis), whitelist_posicao)
    decididos, revisao = parear(pos, config)
    ambiguos = tuple(
        replace(ir.registro, status="revisao", justificativa=ir.motivo)
        for ir in revisao
    )
    n_fundidos = sum(1 for r in decididos if r.tipo_sinal.direcao == "InputOutput")
    n_sem_par = len(decididos) - n_fundidos
    return ResultadoReparear(
        resultantes=tuple(decididos) + ambiguos,
        n_fundidos=n_fundidos, n_ambiguos=len(ambiguos), n_sem_par=n_sem_par,
    )
