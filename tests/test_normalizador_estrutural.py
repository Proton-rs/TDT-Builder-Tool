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
        tipo_sinal=TipoSinal("Discrete", "DoubleBit" if double else "SingleBit", "Input"),
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
    assert corrigidos[0].tipo_sinal.datatype == "DoubleBit"
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


def test_salva_par_consecutivo_e_manda_sobra_pra_revisao():
    # 3 sinais na mesma chave: 100/101 são o double-bit; 105 é distinto (colapsou
    # na mesma sigla) -> par funde, sobra vai pra revisão (não some, não corrompe).
    regs = [_rec("LT3:1", "SECC", [100]), _rec("LT3:2", "SECC", [101]),
            _rec("LT3:3", "SECC", [105])]
    corrigidos, erros = corrigir(regs)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (100, 101)
    assert corrigidos[0].tipo_sinal.datatype == "DoubleBit"
    assert [e.registro.id for e in erros] == ["LT3:3"]


def test_nao_funde_nao_consecutivos():
    # Dois sinais não-consecutivos NÃO são double-bit (a TDT real não tem lacuna).
    regs = [_rec("LT3:1", "DJA1", [100]), _rec("LT3:2", "DJA1", [108])]
    corrigidos, erros = corrigir(regs)
    assert corrigidos == ()
    assert all(e.motivo == "endereco_duplicado" for e in erros)


def test_sinal_simples_passa_limpo():
    corrigidos, erros = corrigir([_rec("LT3:1", "DJ", [17])])
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (17,)
    assert erros == ()
