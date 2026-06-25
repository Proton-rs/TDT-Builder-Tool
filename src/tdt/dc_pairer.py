"""Pareamento D+C — após a classificação.

Agrupa sinais decididos por (módulo, sigla). Quando um grupo tem exatamente um
status (Input) e um comando (Output), funde num sinal ReadWrite (INCOORDS do
status, OUTCOORDS do comando). Combinações ambíguas (vários inputs e um output,
etc.) vão para revisão. Grupos de mesma direção não são tocados — double-bit é
responsabilidade do normalizador estrutural.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.contracts import ItemRevisao, SignalRecord


def _chave(rec: SignalRecord) -> tuple:
    return (rec.modulo.nome, rec.sigla_sinal)


def _fundir(status: SignalRecord, comando: SignalRecord) -> SignalRecord:
    return replace(
        status,
        tipo_sinal=replace(status.tipo_sinal, direcao="InputOutput"),
        enderecamento=replace(
            status.enderecamento, indices_saida=comando.enderecamento.indices
        ),
    )


def parear(
    registros: list[SignalRecord],
) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]:
    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        grupos[_chave(rec)].append(rec)

    saida: list[SignalRecord] = []
    revisao: list[ItemRevisao] = []

    for grupo in grupos.values():
        inputs = [r for r in grupo if r.tipo_sinal.direcao == "Input"]
        outputs = [r for r in grupo if r.tipo_sinal.direcao == "Output"]

        if not outputs:  # sem comando: nada a parear
            saida.extend(grupo)
        elif not inputs:  # comando(s) órfão(s): Write-only
            saida.extend(grupo)
        elif len(inputs) == 1 and len(outputs) == 1:
            saida.append(_fundir(inputs[0], outputs[0]))
        else:  # ambíguo: não dá para confirmar o equipamento
            revisao.extend(ItemRevisao(r, motivo="pareamento_ambiguo") for r in grupo)

    return tuple(saida), tuple(revisao)
