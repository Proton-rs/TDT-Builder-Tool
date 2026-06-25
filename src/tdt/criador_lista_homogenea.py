"""Monta a ListaHomogenea (representação intermediária única antes da EngineTDT).

Só sinais decididos entram. Enriquecimento determinístico adicional (AT/BT,
proteção, AOR) é um hook para o futuro — a versão LLM é o SP2.

ponytail: por ora só assembla; enriquecimento entra quando houver regra/dado.
"""

from __future__ import annotations

from tdt.contracts import ListaHomogenea, SignalRecord


def montar(
    registros: list[SignalRecord], subestacao: str | None, protocolo: str = "DNP3"
) -> ListaHomogenea:
    decididos = tuple(r for r in registros if r.status == "decidido")
    if decididos and not subestacao:
        raise ValueError(
            "Subestação não informada. Não há detecção automática da sigla da "
            "subestação — informe-a para continuar a geração do TDT."
        )
    return ListaHomogenea(subestacao=subestacao, protocolo=protocolo, registros=decididos)
