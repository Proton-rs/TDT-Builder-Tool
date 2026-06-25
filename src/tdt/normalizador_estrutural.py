"""Corrige a estrutura dos sinais classificados.

- Duplicatas do mesmo (módulo, sigla) com endereços consecutivos (100, 101)
  viram um único sinal double-bit (indices = (100, 101)).
- Duplicatas com mesmo endereço -> revisão.
- Sinais sem endereço -> revisão.

Casos sem fix automático saem como ItemRevisao; o resto segue corrigido.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.contracts import Enderecamento, ItemRevisao, SignalRecord, TipoSinal


def _chave(rec: SignalRecord) -> tuple:
    return (rec.modulo.nome, rec.sigla_sinal)


def corrigir(
    registros: list[SignalRecord],
) -> tuple[tuple[SignalRecord, ...], tuple[ItemRevisao, ...]]:
    corrigidos: list[SignalRecord] = []
    erros: list[ItemRevisao] = []

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        if not rec.enderecamento.indices:
            erros.append(ItemRevisao(rec, motivo="sem_endereco"))
            continue
        grupos[_chave(rec)].append(rec)

    for grupo in grupos.values():
        if len(grupo) == 1:
            corrigidos.append(grupo[0])
            continue

        indices = sorted(idx for rec in grupo for idx in rec.enderecamento.indices)
        consecutivos = len(grupo) == 2 and indices == list(
            range(indices[0], indices[0] + len(indices))
        ) and len(set(indices)) == len(indices)

        if consecutivos:
            base = grupo[0]
            corrigidos.append(
                replace(
                    base,
                    enderecamento=Enderecamento(base.enderecamento.protocolo, tuple(indices)),
                    tipo_sinal=replace(base.tipo_sinal, is_double_bit=True),
                )
            )
        else:
            for rec in grupo:
                erros.append(ItemRevisao(rec, motivo="endereco_duplicado"))

    return tuple(corrigidos), tuple(erros)
