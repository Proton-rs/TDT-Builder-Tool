from dataclasses import replace

from tdt.contracts import (
    Candidato, Descricoes, Eletrico, Enderecamento, ItemRevisao, ListaHomogenea,
    Modulo, ResultadoPipeline, SignalRecord, TipoSinal,
)
from tdt.ui.estado import AppState


def _rec(id_, sigla, status):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
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


def test_definir_fase_atualiza_eletrico():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_fase(0, "B")
    assert st.registros[0].eletrico.fase == "B"


def test_definir_nivel_tensao_atualiza_eletrico():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_nivel_tensao(0, "AT")
    assert st.registros[0].eletrico.nivel_tensao == "AT"


def test_definir_barra_atualiza_eletrico():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_barra(0, "Auxiliar")
    assert st.registros[0].eletrico.barra == "Auxiliar"


def test_definir_tipo_equip_atualiza_e_zera_inferido():
    st = AppState()
    rec = _rec("a:1", "DJF1", "decidido")
    rec = replace(rec, eletrico=Eletrico(equipamento_alvo="Disjuntor", equipamento_inferido=True))
    st.registros = [rec]
    st.definir_tipo_equip(0, "Seccionadora")
    assert st.registros[0].eletrico.equipamento_alvo == "Seccionadora"
    assert st.registros[0].eletrico.equipamento_inferido is False


def test_definir_modulo_atualiza_nome():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_modulo(0, "AL21")
    assert st.registros[0].modulo.nome == "AL21"


def test_definir_escala_atualiza_grandezas_analogicas():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_escala(0, 1.5)
    assert st.registros[0].grandezas_analogicas.escala_transmissao == 1.5


def test_definir_tipo_atualiza_categoria_direcao_e_marca_confiavel():
    st = AppState()
    rec = _rec("a:1", "DJF1", "decidido")
    rec = replace(rec, tipo_sinal=TipoSinal("DiscreteAnalog", "SingleBit", "Input", categoria_confiavel=False))
    st.registros = [rec]
    st.definir_tipo(0, "Analog", "Output")
    assert st.registros[0].tipo_sinal.categoria == "Analog"
    assert st.registros[0].tipo_sinal.direcao == "Output"
    assert st.registros[0].tipo_sinal.categoria_confiavel is True


def test_editar_campo_nao_muda_status_nem_justificativa():
    st = AppState()
    st.registros = [_rec("a:1", None, "revisao")]
    st.definir_fase(0, "A")
    assert st.registros[0].status == "revisao"
    assert st.registros[0].justificativa is None
