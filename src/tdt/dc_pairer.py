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
from tdt.pareamento_polaridade import SIGLAS_POSICAO, eh_comando_toggle
from tdt.semantica_estados import compatibilidade_texto


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
        tipo_sinal=replace(
            status.tipo_sinal, direcao="InputOutput",
            comando_duplo=comando.tipo_sinal.comando_duplo,
        ),
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


def _reconciliar_posicao(
    registros: list[SignalRecord],
) -> tuple[list[SignalRecord], list[ItemRevisao]]:
    """Comando toggle ('Abrir/Fechar') com sigla de POSIÇÃO divergente do
    status de posição do MESMO (módulo, equipamento) re-chaveia pra sigla do
    status — rede de segurança quando o scorer divergiu (SP-CVA2 E2). Só
    quando o status é único e inequívoco; status ambíguo (2 siglas de posição
    distintas) manda o comando pra revisão `posicao_divergente`. Determinístico,
    restrito ao catálogo SIGLAS_POSICAO; nunca mexe em score."""
    por_equip: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for r in registros:
        if r.eletrico.nome_equipamento:
            por_equip[(r.modulo.nome, r.eletrico.nome_equipamento)].append(r)

    troca: dict[str, str] = {}
    divergentes: set[str] = set()
    for grupo in por_equip.values():
        siglas_status = {
            (r.sigla_sinal or "").upper()
            for r in grupo
            if r.tipo_sinal.direcao == "Input"
            and (r.sigla_sinal or "").upper() in SIGLAS_POSICAO
        }
        cmds = [
            r for r in grupo
            if r.tipo_sinal.direcao == "Output"
            and (r.sigla_sinal or "").upper() in SIGLAS_POSICAO
            and (r.sigla_sinal or "").upper() not in siglas_status
            and eh_comando_toggle(r.descricoes.normalizada.split())
        ]
        if not cmds or not siglas_status:
            continue
        if len(siglas_status) == 1:
            (alvo,) = siglas_status
            for c in cmds:
                troca[c.id] = alvo
        else:
            divergentes.update(c.id for c in cmds)

    revisao = [
        ItemRevisao(r, motivo="posicao_divergente")
        for r in registros
        if r.id in divergentes
    ]
    novos = [
        replace(
            r,
            sigla_sinal=troca[r.id],
            justificativa="posicao reconciliada com status do equipamento",
        )
        if r.id in troca
        else r
        for r in registros
        if r.id not in divergentes
    ]
    return novos, revisao


def parear(
    registros: list[SignalRecord],
    config=None,
) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]:
    limiar = 60.0 if config is None else config.limiar_pareamento_similaridade
    siglas_write = (
        config.siglas_write_legitimo if config is not None else frozenset({"CDC"})
    )
    registros, revisao_reconc = _reconciliar_posicao(registros)
    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        grupos[_chave(rec)].append(rec)

    saida: list[SignalRecord] = []
    revisao: list[ItemRevisao] = list(revisao_reconc)

    for grupo in grupos.values():
        inputs = [r for r in grupo if r.tipo_sinal.direcao == "Input"]
        outputs = [r for r in grupo if r.tipo_sinal.direcao == "Output"]

        if not outputs:  # sem comando: nada a parear
            saida.extend(grupo)
        elif not inputs:  # comando(s) sem status
            for o in outputs:
                if (o.sigla_sinal or "").upper() in siglas_write:
                    saida.append(o)  # Write legítimo (ex. CDC raise/lower)
                else:
                    revisao.append(ItemRevisao(o, motivo="comando_sem_discreto"))
        # Gate semântico (D5): só *morde* quando AMBOS os textos carregam
        # evidência de estado — comando com texto sem verbo de estado (só sigla
        # após N3) passa (compatibilidade_texto devolve True). "Filtro nenhum >
        # filtro errado": não bloqueia pareamento legítimo por falta de sinal.
        elif len(inputs) == 1 and len(outputs) == 1 and compatibilidade_texto(
            outputs[0].descricoes.normalizada, inputs[0].descricoes.normalizada
        ):
            saida.append(fundir(inputs[0], outputs[0]))
        else:  # N×M ou 1×1 incompatível: desempata por similaridade (catch-all)
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
            if not compatibilidade_texto(
                o.descricoes.normalizada, i.descricoes.normalizada
            ):
                continue
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
