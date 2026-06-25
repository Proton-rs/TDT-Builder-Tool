from tdt.contracts import (
    Descricoes,
    Enderecamento,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.dc_pairer import parear


def _rec(rid, sigla, direcao, indices):
    return SignalRecord(
        id=rid,
        modulo=Modulo("LT_GTA", "coluna:modulo"),
        tipo_sinal=TipoSinal("Discrete", False, direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(sigla, sigla),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_pareia_input_e_output_vira_readwrite():
    regs = [_rec("s:1", "DJ", "Input", [5]), _rec("s:2", "DJ", "Output", [0])]
    pareados, revisao = parear(regs)
    assert len(pareados) == 1
    assert revisao == ()
    rw = pareados[0]
    assert rw.tipo_sinal.direcao == "InputOutput"
    assert rw.enderecamento.indices == (5,)
    assert rw.enderecamento.indices_saida == (0,)


def test_status_sozinho_passa():
    regs = [_rec("s:1", "DJ", "Input", [5])]
    pareados, revisao = parear(regs)
    assert pareados[0].tipo_sinal.direcao == "Input"
    assert revisao == ()


def test_comando_orfao_passa_como_write():
    regs = [_rec("s:1", "DJ", "Output", [0])]
    pareados, revisao = parear(regs)
    assert pareados[0].tipo_sinal.direcao == "Output"
    assert revisao == ()


def test_ambiguo_vai_para_revisao():
    regs = [
        _rec("s:1", "DJ", "Input", [5]),
        _rec("s:2", "DJ", "Input", [6]),
        _rec("s:3", "DJ", "Output", [0]),
    ]
    pareados, revisao = parear(regs)
    assert pareados == ()
    assert len(revisao) == 3
    assert all(it.motivo == "pareamento_ambiguo" for it in revisao)


def test_grupos_mesma_direcao_nao_sao_tocados():
    # dois inputs sem comando: dc_pairer não mexe (double-bit é do normalizador estrutural)
    regs = [_rec("s:1", "DJ", "Input", [100]), _rec("s:2", "DJ", "Input", [101])]
    pareados, revisao = parear(regs)
    assert len(pareados) == 2
    assert revisao == ()
