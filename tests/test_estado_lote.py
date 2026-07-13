from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.ui.estado import AppState


def _rec(id_):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"), sigla_sinal=None, status="revisao",
        candidatos=(Candidato(f"SIG{id_}", 0.9, "tfidf"),),
    )


def _estado_com(n):
    st = AppState()
    st.registros = [_rec(f"a:{i}") for i in range(n)]
    return st


def _aprovado(r):
    return r.status == "decidido" and r.sigla_sinal is not None


def test_aprovar_ids_aprova_todos_com_um_snapshot():
    estado = _estado_com(3)
    n = estado.aprovar_ids([r.id for r in estado.registros])
    assert n == 3 and all(_aprovado(r) for r in estado.registros)
    estado.desfazer()
    assert not any(_aprovado(r) for r in estado.registros)  # 1 undo desfaz o lote


def test_aprovar_ids_um_snapshot_para_lote_inteiro():
    estado = _estado_com(3)
    estado.aprovar_ids([r.id for r in estado.registros])
    assert len(estado._historico) == 1


def test_aprovar_ids_ignora_ids_inexistentes():
    estado = _estado_com(2)
    n = estado.aprovar_ids(["nao_existe"])
    assert n == 0


def test_aprovar_ids_ignora_sem_candidato_e_sem_sigla():
    estado = _estado_com(1)
    estado.registros = [
        SignalRecord(
            id="x:1", modulo=Modulo("M", "sheet_name"),
            tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
            enderecamento=Enderecamento("DNP3", (1,)),
            descricoes=Descricoes("d", "D"), sigla_sinal=None, status="revisao",
        ),
    ]
    n = estado.aprovar_ids(["x:1"])
    assert n == 0
    assert estado.registros[0].status == "revisao"


def test_aprovar_ids_retorna_quantidade_aprovada_parcial():
    estado = _estado_com(2)
    n = estado.aprovar_ids([estado.registros[0].id])
    assert n == 1
    assert _aprovado(estado.registros[0])
    assert not _aprovado(estado.registros[1])
