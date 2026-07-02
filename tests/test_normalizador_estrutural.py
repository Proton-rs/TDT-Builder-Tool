from tdt.contracts import (
    Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.normalizador_estrutural import corrigir

WL = frozenset({"SECC", "DJF1", "SECG"})


def _rec(rid, sigla, indices, desc=None, datatype="SingleBit"):
    d = desc if desc is not None else sigla
    return SignalRecord(
        id=rid,
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", datatype, "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(d, d),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_par_posicao_whitelist_vira_multicoord():
    regs = [_rec("LT3:1", "SECC", [100], "SECCIONADORA ABERTA"),
            _rec("LT3:2", "SECC", [101], "SECCIONADORA FECHADA")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (100, 101)
    assert corrigidos[0].tipo_sinal.datatype == "MultiCoord"
    assert erros == ()


def test_nao_funde_fora_da_whitelist():
    # SGF Excluída + SGF Atuado consecutivos: NUNCA funde (bug histórico 1534;1535)
    regs = [_rec("AL11:1", "SGF", [1534], "PROTECAO SGF EXCLUIDA"),
            _rec("AL11:2", "SGF", [1535], "PROTECAO SGF ATUADO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2
    assert all(c.tipo_sinal.datatype == "SingleBit" for c in corrigidos)
    assert erros == ()


def test_nao_funde_sem_estados_opostos():
    # mesma sigla whitelisted mas estados iguais -> não é par de posição
    regs = [_rec("LT3:1", "SECC", [100], "SECCIONADORA ABERTA"),
            _rec("LT3:2", "SECC", [101], "SECCIONADORA ABERTA")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2


def test_doublebit_nativo_passa_intacto():
    regs = [_rec("IMA:1", "SECC", [1100, 1101], "SECC 89-16", datatype="DoubleBit")]
    corrigidos, erros = corrigir(regs, WL)
    assert corrigidos[0].tipo_sinal.datatype == "DoubleBit"
    assert corrigidos[0].enderecamento.indices == (1100, 1101)


def test_indefinido_descartado_com_registro():
    regs = [_rec("AL11:1", "DJF1", [1500], "52 DESLIGADO"),
            _rec("AL11:2", "DJF1", [1501], "52 LIGADO"),
            _rec("AL11:3", "DJF1", [1502], "52 INDEFINIDO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].tipo_sinal.datatype == "MultiCoord"
    assert [e.motivo for e in erros] == ["descartado_indefinido"]


def test_local_remoto_fica_so_o_bit_local():
    regs = [_rec("AL11:1", "43LR", [1504], "CHAVE 43LR POS LOCAL"),
            _rec("AL11:2", "43LR", [1505], "CHAVE 43LR POS REMOTO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (1504,)
    assert [e.motivo for e in erros] == ["descartado_redundante"]


def test_endereco_duplicado_continua_revisao():
    regs = [_rec("LT3:1", "DJ", [100]), _rec("LT3:2", "DJ", [100])]
    corrigidos, erros = corrigir(regs, WL)
    assert corrigidos == ()
    assert all(e.motivo == "endereco_duplicado" for e in erros)


def test_sem_endereco_vai_para_revisao():
    corrigidos, erros = corrigir([_rec("LT3:9", "DJ", [])], WL)
    assert erros[0].motivo == "sem_endereco"


def test_nao_consecutivos_seguem_independentes():
    regs = [_rec("LT3:1", "DJA1", [100], "DISJUNTOR ABERTO"),
            _rec("LT3:2", "DJA1", [108], "DISJUNTOR FECHADO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2
    assert erros == ()
