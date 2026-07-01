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

from rapidfuzz import fuzz

from tdt.contracts import ItemRevisao, SignalRecord


def _chave(rec: SignalRecord) -> tuple:
    # Inclui o equipamento (ver normalizador_estrutural._chave): dois disjuntores
    # no mesmo módulo (52-2, 52-10), cada um com 1 status + 1 comando, pareiam
    # por equipamento em vez de virar "2 inputs + 2 outputs" (ambíguo).
    return (rec.modulo.nome, rec.eletrico.nome_equipamento, rec.sigla_sinal)


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
    config=None,
) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]:
    limiar = 60.0 if config is None else config.limiar_pareamento_similaridade
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
        else:  # N×M: desempata por similaridade de descrição (catch-all)
            saida_pares, sobra_rev = _parear_catchall(inputs, outputs, limiar)
            saida.extend(saida_pares)
            revisao.extend(sobra_rev)

    return tuple(saida), tuple(revisao)


def _parear_catchall(inputs, outputs, limiar):
    """Greedy: casa cada Output com o Input de maior similaridade de descrição
    (>= limiar). Inputs sem par -> Input standalone (saída). Outputs sem par ->
    revisão. Ver spec discriminador-genérico Fase 2.

    Empate de similaridade: `candidatos.sort(reverse=True)` desempata por
    `(oi, ii)` decrescente — entre 2 Inputs igualmente similares, vence o de
    maior índice na lista de entrada (não é ordem de dict nem estável por
    identidade do registro). A spec não prescreve desempate; não há gate real
    exercitando esse caminho hoje (catch-all real, ex. SGF, falha antes na
    classificação). Se isso importar no futuro, desempatar por outro critério
    explícito (ex. endereço) em vez de depender da ordem de enumeração.
    """
    candidatos = []
    for oi, o in enumerate(outputs):
        for ii, i in enumerate(inputs):
            sim = fuzz.token_sort_ratio(
                o.descricoes.normalizada, i.descricoes.normalizada
            )
            candidatos.append((sim, oi, ii))
    candidatos.sort(reverse=True)

    usados_o: set[int] = set()
    usados_i: set[int] = set()
    saida: list[SignalRecord] = []
    for sim, oi, ii in candidatos:
        if sim < limiar:
            break
        if oi in usados_o or ii in usados_i:
            continue
        saida.append(fundir(inputs[ii], outputs[oi]))
        usados_o.add(oi)
        usados_i.add(ii)

    for ii, inp in enumerate(inputs):
        if ii not in usados_i:
            saida.append(inp)  # standalone decidido

    revisao = [
        ItemRevisao(o, motivo="pareamento_ambiguo")
        for oi, o in enumerate(outputs) if oi not in usados_o
    ]
    return saida, revisao
