from tdt.contracts import (
    Descricoes,
    Enderecamento,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.normalizador_estrutural import corrigir


def _rec(rid, sigla, indices, double=False):
    return SignalRecord(
        id=rid,
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", double, "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(sigla, sigla),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_merge_double_bit_enderecos_consecutivos():
    regs = [_rec("LT3:1", "SECC", [100]), _rec("LT3:2", "SECC", [101])]
    corrigidos, erros = corrigir(regs)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (100, 101)
    assert corrigidos[0].tipo_sinal.is_double_bit is True
    assert erros == ()


def test_sem_endereco_vai_para_revisao():
    corrigidos, erros = corrigir([_rec("LT3:9", "DJ", [])])
    assert corrigidos == ()
    assert len(erros) == 1
    assert erros[0].motivo == "sem_endereco"


def test_endereco_duplicado_vai_para_revisao():
    regs = [_rec("LT3:1", "DJ", [100]), _rec("LT3:2", "DJ", [100])]
    corrigidos, erros = corrigir(regs)
    assert corrigidos == ()
    assert all(e.motivo == "endereco_duplicado" for e in erros)


def test_sinal_simples_passa_limpo():
    corrigidos, erros = corrigir([_rec("LT3:1", "DJ", [17])])
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (17,)
    assert erros == ()
