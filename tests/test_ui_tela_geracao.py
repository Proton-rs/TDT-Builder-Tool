import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.tela_geracao import enderecos_duplicados

pytest.importorskip("PySide6")


def _rec(id_, indices=(1,), indices_saida=(), status="revisao"):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", indices, indices_saida),
        descricoes=Descricoes("d", "D"), status=status,
    )


def test_duplicata_de_input_detectada():
    regs = [_rec("a", indices=(14,)), _rec("b", indices=(14,)), _rec("c", indices=(2,))]
    assert enderecos_duplicados(regs) == {("in", 14): ["a", "b"]}


def test_input_e_output_iguais_nao_e_duplicata():
    regs = [_rec("a", indices=(14,)), _rec("b", indices=(), indices_saida=(14,))]
    assert enderecos_duplicados(regs) == {}


def test_sem_duplicatas_dict_vazio():
    assert enderecos_duplicados([_rec("a", indices=(1,))]) == {}
