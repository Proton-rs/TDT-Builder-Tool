from tdt.config import Config
from tdt.contracts import Descricoes, Enderecamento, Modulo, TipoSinal, SignalRecord
from tdt.ui.reparear import elegivel, reparear


def _rec(id_, sigla, direcao="Input", indices=(), saida=(), desc="D"):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", indices, saida),
        descricoes=Descricoes("d", desc), sigla_sinal=sigla, status="decidido",
    )


def test_reparear_funde_par_reclassificado():
    status = _rec("s:1", "SECF", direcao="Input", indices=(100,))
    comando = _rec("c:1", "SECF", direcao="Output", indices=(400,))
    res = reparear([status, comando], frozenset(), Config())
    assert res.n_fundidos == 1
    fundido = [r for r in res.resultantes if r.tipo_sinal.direcao == "InputOutput"][0]
    assert fundido.enderecamento.indices == (100,)
    assert fundido.enderecamento.indices_saida == (400,)


def test_reparear_nao_toca_inputoutput_existente():
    ja_fundido = _rec("f:1", "SECF", direcao="InputOutput", indices=(1,), saida=(2,))
    assert elegivel(ja_fundido) is False


def test_reparear_nxm_vira_ambiguo_sem_perder_registro():
    descs_input = ("ZZZ MODULO ALFA BETA", "QQQ MODULO GAMA DELTA")
    recs = [
        _rec(f"s:{i}", "SECF", direcao="Input", indices=(i,), desc=d)
        for i, d in zip((1, 2), descs_input)
    ]
    recs += [_rec("c:9", "SECF", direcao="Output", indices=(9,),
                   desc="XPTO COMANDO GERAL SISTEMA REDE")]
    res = reparear(recs, frozenset(), Config())
    total_indices = sum(len(r.enderecamento.indices) + len(r.enderecamento.indices_saida)
                        for r in res.resultantes)
    assert total_indices == 3
    assert res.n_ambiguos >= 1
