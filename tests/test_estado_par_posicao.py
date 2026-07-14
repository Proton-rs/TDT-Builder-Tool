from tdt.contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.estado import AppState


def _rec(id_, mod="M1", equip="52-10", ind=(900,), sigla=None, datatype="SingleBit"):
    return SignalRecord(
        id=id_, modulo=Modulo(mod, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", datatype, "Input"),
        enderecamento=Enderecamento("DNP3", tuple(ind)),
        descricoes=Descricoes("d", "D"),
        eletrico=Eletrico(nome_equipamento=equip),
        sigla_sinal=sigla, status="revisao",
    )


def _rec_multicoord(sigla, ind, mod="M1", equip="52-10"):
    return SignalRecord(
        id="s:1", modulo=Modulo(mod, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "MultiCoord", "Input"),
        enderecamento=Enderecamento("DNP3", tuple(ind)),
        descricoes=Descricoes("d", "D"),
        eletrico=Eletrico(nome_equipamento=equip),
        sigla_sinal=sigla, status="decidido",
    )


def _estado_com_regs(regs):
    st = AppState()
    st.registros = list(regs)
    return st


def test_formar_par_posicao_funde_multicoord():
    estado = _estado_com_regs([_rec("s:1", ind=(900,)), _rec("s:2", ind=(901,))])
    erro = estado.formar_par_posicao("s:1", "s:2", "DJF1")
    assert erro is None
    (r,) = estado.registros
    assert r.tipo_sinal.datatype == "MultiCoord"
    assert r.enderecamento.indices == (900, 901)
    assert r.sigla_sinal == "DJF1"


def test_formar_par_posicao_um_snapshot():
    estado = _estado_com_regs([_rec("s:1", ind=(900,)), _rec("s:2", ind=(901,))])
    estado.formar_par_posicao("s:1", "s:2", "DJF1")
    assert len(estado._historico) == 1
    estado.desfazer()
    assert len(estado.registros) == 2


def test_formar_par_recusa_modulos_diferentes():
    estado = _estado_com_regs([_rec("s:1", mod="BC1"), _rec("s:2", mod="BC2")])
    erro = estado.formar_par_posicao("s:1", "s:2", "DJF1")
    assert erro is not None
    assert len(estado.registros) == 2


def test_formar_par_recusa_equipamentos_diferentes():
    estado = _estado_com_regs([_rec("s:1", equip="52-10"), _rec("s:2", equip="52-11")])
    erro = estado.formar_par_posicao("s:1", "s:2", "DJF1")
    assert erro is not None
    assert len(estado.registros) == 2


def test_formar_par_recusa_mais_de_um_endereco():
    estado = _estado_com_regs([_rec("s:1", ind=(900, 901)), _rec("s:2", ind=(902,))])
    erro = estado.formar_par_posicao("s:1", "s:2", "DJF1")
    assert erro is not None
    assert len(estado.registros) == 2


def test_formar_par_recusa_id_inexistente():
    estado = _estado_com_regs([_rec("s:1", ind=(900,))])
    erro = estado.formar_par_posicao("s:1", "nao_existe", "DJF1")
    assert erro is not None
    assert len(estado.registros) == 1


def test_trocar_sigla_par_preserva_enderecos():
    estado = _estado_com_regs([_rec_multicoord("DJA1", ind=(900, 901))])
    estado.trocar_sigla_par("s:1", "DJF1")
    (r,) = estado.registros
    assert r.sigla_sinal == "DJF1"
    assert r.enderecamento.indices == (900, 901)
    assert r.tipo_sinal.datatype == "MultiCoord"


def test_trocar_sigla_par_um_snapshot():
    estado = _estado_com_regs([_rec_multicoord("DJA1", ind=(900, 901))])
    estado.trocar_sigla_par("s:1", "DJF1")
    assert len(estado._historico) == 1


def test_trocar_sigla_par_recusa_sigla_fora_do_catalogo():
    estado = _estado_com_regs([_rec_multicoord("DJA1", ind=(900, 901))])
    estado.trocar_sigla_par("s:1", "XYZ")
    (r,) = estado.registros
    assert r.sigla_sinal == "DJA1"
