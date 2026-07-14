"""Corrige a estrutura dos sinais classificados (SP-E D3).

- Par de POSIÇÃO do mesmo equipamento (sigla na whitelist SwitchStatus,
  estados opostos aberto/fechado ou ligado/desligado, endereços consecutivos)
  vira UM sinal ``MultiCoord`` — nunca ``DoubleBit`` (reservado ao nativo N;M).
- Estado "Indefinido" (transit de posição) nunca vira ponto -> descartado.
- Par complementar LOCAL/REMOTO: fica o bit LOCAL (regra GTD real 43LR).
- Duplicata de MESMO endereço -> revisão; sem endereço -> revisão.
- Todo o resto segue como single-bit independente.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.contracts import Enderecamento, ItemRevisao, SignalRecord
from tdt.semantica_estados import INDEFINIDO, LOCAL_REMOTO, POSICAO, detectar_estado


def _chave(rec: SignalRecord) -> tuple:
    # Inclui o equipamento: a TDT nomeia o ponto como {SE}_{modulo}_{equip}_{sigla},
    # então mesma (modulo, sigla) com equipamentos distintos NÃO são duplicatas.
    return (rec.modulo.nome, rec.eletrico.nome_equipamento, rec.sigla_sinal)


def _estado(rec: SignalRecord):
    return detectar_estado(rec.descricoes.normalizada)


def _par_posicao_oposta(a: SignalRecord, b: SignalRecord) -> bool:
    ea, eb = _estado(a), _estado(b)
    return (
        ea is not None and eb is not None
        and ea.classe == POSICAO and eb.classe == POSICAO
        and ea.polaridade is not None and eb.polaridade is not None
        and ea.polaridade != eb.polaridade
    )


def _fundir_multicoord(a: SignalRecord, b: SignalRecord) -> SignalRecord:
    return replace(
        a,
        enderecamento=Enderecamento(
            a.enderecamento.protocolo,
            a.enderecamento.indices + b.enderecamento.indices,
        ),
        tipo_sinal=replace(a.tipo_sinal, datatype="MultiCoord"),
    )


def fundir_pares_posicao(
    registros: list[SignalRecord],
    whitelist_posicao: frozenset[str],
) -> list[SignalRecord]:
    """Funde pares de POSIÇÃO (2 Inputs de 1 índice, sigla na whitelist
    SwitchStatus, polaridade oposta, endereços consecutivos) num único
    MultiCoord ANTES do dc_pairer — o comando pareia com o par inteiro
    (1 input x 1 output) em vez de cair no catch-all N x M (SP-CVA2 E4).
    Mesmo predicado `fundivel` de `corrigir`; puro, não emite revisão."""
    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    saida: list[SignalRecord] = []
    for rec in registros:
        if (
            rec.tipo_sinal.direcao == "Input"
            and len(rec.enderecamento.indices) == 1
            and (rec.sigla_sinal or "").upper() in whitelist_posicao
        ):
            grupos[_chave(rec)].append(rec)
        else:
            saida.append(rec)
    for grupo in grupos.values():
        ordenados = sorted(grupo, key=lambda r: r.enderecamento.indices[0])
        i = 0
        while i < len(ordenados):
            a = ordenados[i]
            b = ordenados[i + 1] if i + 1 < len(ordenados) else None
            if (
                b is not None
                and b.enderecamento.indices[0] == a.enderecamento.indices[0] + 1
                and _par_posicao_oposta(a, b)
            ):
                saida.append(_fundir_multicoord(a, b))
                i += 2
            else:
                saida.append(a)
                i += 1
    return saida


def corrigir(
    registros: list[SignalRecord],
    whitelist_posicao: frozenset[str] = frozenset(),
) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]:
    corrigidos: list[SignalRecord] = []
    erros: list[ItemRevisao] = []

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        if not rec.enderecamento.indices:
            erros.append(ItemRevisao(rec, motivo="sem_endereco"))
            continue
        est = _estado(rec)
        if est is not None and est.classe == INDEFINIDO:
            erros.append(ItemRevisao(rec, motivo="descartado_indefinido"))
            continue
        grupos[_chave(rec)].append(rec)

    for grupo in grupos.values():
        if len(grupo) == 1:
            corrigidos.append(grupo[0])
            continue

        # Par complementar LOCAL/REMOTO: fica só o bit LOCAL (GTD real: 43LR
        # usa 1504 REMOTO@LOCAL; 1505 é redundante).
        if len(grupo) == 2:
            estados = [_estado(r) for r in grupo]
            if all(e is not None and e.classe == LOCAL_REMOTO for e in estados):
                com_local = [
                    r for r in grupo
                    if "LOCAL" in r.descricoes.normalizada.upper().split()
                ]
                if len(com_local) == 1:
                    corrigidos.append(com_local[0])
                    outro = grupo[0] if grupo[1] is com_local[0] else grupo[1]
                    erros.append(ItemRevisao(outro, motivo="descartado_redundante"))
                    continue

        ordenados = sorted(grupo, key=lambda r: r.enderecamento.indices[0])
        usados: set[int] = set()
        i = 0
        while i < len(ordenados) - 1:
            a, b = ordenados[i], ordenados[i + 1]
            fundivel = (
                a.tipo_sinal.direcao == "Input"
                and b.tipo_sinal.direcao == "Input"
                and len(a.enderecamento.indices) == 1
                and len(b.enderecamento.indices) == 1
                and b.enderecamento.indices[0] == a.enderecamento.indices[0] + 1
                and (a.sigla_sinal or "").upper() in whitelist_posicao
                and _par_posicao_oposta(a, b)
            )
            duplicata = a.enderecamento.indices == b.enderecamento.indices
            if fundivel:
                corrigidos.append(_fundir_multicoord(a, b))
                usados.update((i, i + 1))
                i += 2
            elif duplicata:
                erros.append(ItemRevisao(a, motivo="endereco_duplicado"))
                erros.append(ItemRevisao(b, motivo="endereco_duplicado"))
                usados.update((i, i + 1))
                i += 2
            else:
                i += 1
        # Não fundidos e sem duplicata: single-bit independentes. Colisão de
        # nome na saída é responsabilidade do diag_estrutura (Task 8).
        corrigidos.extend(
            ordenados[j] for j in range(len(ordenados)) if j not in usados
        )

    return tuple(corrigidos), tuple(erros)
