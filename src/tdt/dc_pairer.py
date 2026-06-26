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


def fundir(status: SignalRecord, comando: SignalRecord) -> SignalRecord:
    """Funde um sinal Input (status) com um Output (comando) num InputOutput.

    Pública porque a UI de revisão (tela_revisao.py) reusa esta função para o
    pareamento manual D+C (Task 3.1) — evita duplicar a lógica de fusão.
    """
    return replace(
        status,
        tipo_sinal=replace(status.tipo_sinal, direcao="InputOutput"),
        enderecamento=replace(
            status.enderecamento, indices_saida=comando.enderecamento.indices
        ),
    )



def separar(fundido: SignalRecord, novo_id_saida: str) -> tuple[SignalRecord, SignalRecord]:
    """Desfaz uma fusão D+C: devolve (status Input, comando Output).

    ponytail: o registro Output original foi perdido na fusão (`fundir` só
    preserva os índices de saída, não o `id`/descrição original do comando).
    O Output recriado aqui usa `novo_id_saida` e reaproveita módulo/descrições
    do registro fundido — rastreabilidade completa do Output pré-fusão não é
    recuperável com o modelo de dados atual. Upgrade path: se isso importar,
    `Enderecamento`/`SignalRecord` precisariam guardar o id do comando
    original junto de `indices_saida`.
    """
    status = replace(
        fundido,
        tipo_sinal=replace(fundido.tipo_sinal, direcao="Input"),
        enderecamento=replace(fundido.enderecamento, indices_saida=()),
    )
    comando = replace(
        fundido,
        id=novo_id_saida,
        tipo_sinal=replace(fundido.tipo_sinal, direcao="Output"),
        enderecamento=replace(
            fundido.enderecamento,
            indices=fundido.enderecamento.indices_saida,
            indices_saida=(),
        ),
    )
    return status, comando


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
            saida.append(fundir(inputs[0], outputs[0]))
        else:  # ambíguo: não dá para confirmar o equipamento
            revisao.extend(ItemRevisao(r, motivo="pareamento_ambiguo") for r in grupo)

    return tuple(saida), tuple(revisao)
