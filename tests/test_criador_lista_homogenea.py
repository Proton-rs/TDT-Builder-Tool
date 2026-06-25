from dataclasses import replace

import pytest

from tdt.contracts import (
    Descricoes,
    Enderecamento,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.criador_lista_homogenea import montar


def _rec(rid, status):
    return SignalRecord(
        id=rid,
        modulo=Modulo("LT_GTA", "coluna:modulo"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (5,)),
        descricoes=Descricoes("DJ", "DISJUNTOR"),
        sigla_sinal="DJ",
        status=status,
    )


def test_monta_lista_so_com_decididos():
    regs = [_rec("s:1", "decidido"), _rec("s:2", "revisao"), _rec("s:3", "decidido")]
    lista = montar(regs, subestacao="IMA")
    assert lista.subestacao == "IMA"
    assert lista.protocolo == "DNP3"
    assert len(lista.registros) == 2
    assert all(r.status == "decidido" for r in lista.registros)


def test_monta_sem_subestacao_com_registros_levanta_erro():
    regs = [_rec("s:1", "decidido")]
    with pytest.raises(ValueError, match="Subestação"):
        montar(regs, subestacao=None)


def test_monta_sem_subestacao_sem_registros_decididos_nao_levanta():
    regs = [_rec("s:1", "revisao")]
    lista = montar(regs, subestacao=None)
    assert lista.registros == ()
