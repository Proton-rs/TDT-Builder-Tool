from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, ItemRevisao, ListaHomogenea,
    Modulo, ResultadoPipeline, SignalRecord, TipoSinal,
)
from tdt.ui.estado import AppState


def _rec(id_, sigla, status):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"), sigla_sinal=sigla, status=status,
    )


def test_carregar_resultado_junta_decididos_e_revisao():
    dec = _rec("a:1", "DJF1", "decidido")
    rev = _rec("a:2", None, "revisao")
    res = ResultadoPipeline(
        lista=ListaHomogenea(None, "DNP3", (dec,)),
        revisao=(ItemRevisao(rev, "score_baixo", ()),),
    )
    st = AppState()
    st.carregar_resultado(res)
    assert len(st.registros) == 2


def test_definir_sigla_marca_editado():
    st = AppState()
    st.registros = [_rec("a:2", None, "revisao")]
    st.definir_sigla(0, "DJF1")
    assert st.registros[0].sigla_sinal == "DJF1"
    assert st.registros[0].status == "decidido"
    assert "editado" in (st.registros[0].justificativa or "").lower()


def test_motivo_por_id_mapeia_id_para_motivo():
    dec = _rec("a:1", "DJF1", "decidido")
    rev = _rec("a:2", None, "revisao")
    res = ResultadoPipeline(
        lista=ListaHomogenea(None, "DNP3", (dec,)),
        revisao=(ItemRevisao(rev, "score_baixo", ()),),
    )
    st = AppState()
    st.carregar_resultado(res)
    mapa = st.motivo_por_id()
    assert mapa == {"a:2": "score_baixo"}


def test_motivo_por_id_vazio_sem_resultado():
    st = AppState()
    assert st.motivo_por_id() == {}


def test_snapshot_guarda_estado_atual_no_historico():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st._snapshot()
    assert len(st._historico) == 1
    assert st._historico[0] == st.registros
    # cópia, não a mesma lista
    assert st._historico[0] is not st.registros


def test_desfazer_restaura_snapshot_anterior():
    st = AppState()
    original = [_rec("a:1", "DJF1", "decidido")]
    st.registros = original
    st._snapshot()
    st.registros = [_rec("a:2", None, "revisao")]
    ok = st.desfazer()
    assert ok is True
    assert st.registros == original


def test_desfazer_sem_historico_retorna_false():
    st = AppState()
    assert st.desfazer() is False
