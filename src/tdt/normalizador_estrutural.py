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
    # Inclui o equipamento: a TDT nomeia o ponto como {SE}_{modulo}_{equip}_{sigla},
    # então mesma (modulo, sigla) com equipamentos distintos (52-2 vs 52-10, ou
    # 8 seccionadoras 89-1..89-8) NÃO são duplicatas — só colidem se equip e
    # sigla coincidem. Equip None só colide com equip None (mesmo nome de saída).
    return (rec.modulo.nome, rec.eletrico.nome_equipamento, rec.sigla_sinal)


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

        # Status double-bit = par de endereços CONSECUTIVOS (ground-truth da TDT:
        # DJF1 INCOORDS=2500;2501, SECC=623;624). Salvamos cada par consecutivo —
        # mesmo num grupo maior — e só o que sobra (sinal distinto colapsado na
        # mesma sigla, ex: 3º SECC) vai pra revisão. NÃO fundimos não-consecutivos:
        # a TDT real não tem double-bit com lacuna, fundir corromperia os COORDS.
        ordenados = sorted(grupo, key=lambda r: r.enderecamento.indices[0])
        usados: set[int] = set()
        i = 0
        while i < len(ordenados) - 1:
            a, b = ordenados[i], ordenados[i + 1]
            if (
                len(a.enderecamento.indices) == 1
                and len(b.enderecamento.indices) == 1
                and b.enderecamento.indices[0] == a.enderecamento.indices[0] + 1
            ):
                corrigidos.append(
                    replace(
                        a,
                        enderecamento=Enderecamento(
                            a.enderecamento.protocolo,
                            a.enderecamento.indices + b.enderecamento.indices,
                        ),
                        tipo_sinal=replace(a.tipo_sinal, is_double_bit=True),
                    )
                )
                usados.update((i, i + 1))
                i += 2
            else:
                i += 1
        sobra = [ordenados[j] for j in range(len(ordenados)) if j not in usados]
        # Se nada foi pareado, é duplicata pura (mesmo endereço ou não-consecutivos).
        for rec in sobra:
            erros.append(ItemRevisao(rec, motivo="endereco_duplicado"))

    return tuple(corrigidos), tuple(erros)
