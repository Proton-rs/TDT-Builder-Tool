from dataclasses import replace

from tdt.config import Config
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


def _rec_dir(id_, sigla, direcao, indices, saida=()):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", indices, saida),
        descricoes=Descricoes("d", "D"), sigla_sinal=sigla, status="decidido",
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


def test_separar_par_posicao_reconstroi_duas_metades():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.registros[0] = replace(
        st.registros[0],
        tipo_sinal=TipoSinal("Discrete", "MultiCoord", "Input"),
        enderecamento=Enderecamento("DNP3", (900, 901)),
    )
    assert st.separar_par_posicao("a:1") is None
    assert len(st.registros) == 2
    a, b = st.registros
    assert a.enderecamento.indices == (900,) and b.enderecamento.indices == (901,)
    assert a.sigla_sinal is None and a.status == "revisao"
    assert a.tipo_sinal.datatype == "SingleBit"
    assert a.id != b.id
    assert st.desfazer() and len(st.registros) == 1


def test_separar_rejeita_nao_multicoord_sem_mutar():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]     # SingleBit, 1 índice
    assert st.separar_par_posicao("a:1") is not None
    assert len(st._historico) == 0                        # sem snapshot em erro


def test_separar_rejeita_inputoutput():
    st = AppState()
    st.registros = [replace(
        _rec("a:1", "DJF1", "decidido"),
        tipo_sinal=TipoSinal("Discrete", "MultiCoord", "InputOutput"),
        enderecamento=Enderecamento("DNP3", (900, 901), (950,)),
    )]
    assert "desvincule" in st.separar_par_posicao("a:1").lower()


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


def test_undo_definir_sigla_restaura_sigla_e_status():
    st = AppState()
    st.registros = [_rec("a:1", None, "revisao")]
    st.definir_sigla(0, "DJF1")
    assert st.desfazer() is True
    assert st.registros[0].sigla_sinal is None
    assert st.registros[0].status == "revisao"


def test_undo_editar_nested_restaura_campo():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_fase(0, "A")
    assert st.registros[0].eletrico.fase == "A"
    assert st.desfazer() is True
    assert st.registros[0].eletrico.fase is None


def test_definir_sigla_sem_snapshot_nao_cria_historico():
    st = AppState()
    st.registros = [_rec("a:1", None, "revisao")]
    st.definir_sigla(0, "DJF1", snapshot=False)
    assert len(st._historico) == 0


def test_definir_equipamento_e_undo():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_equipamento(0, "52-11")
    assert st.registros[0].eletrico.nome_equipamento == "52-11"
    st.definir_equipamento(0, None)  # vazio limpa
    assert st.registros[0].eletrico.nome_equipamento is None
    assert st.desfazer()
    assert st.registros[0].eletrico.nome_equipamento == "52-11"


def test_definir_descricao_bruta():
    st = AppState()
    st.registros = [_rec("a:1", "DJF1", "decidido")]
    st.definir_descricao_bruta(0, "DISJUNTOR 52-11 MOLA")
    assert st.registros[0].descricoes.bruta == "DISJUNTOR 52-11 MOLA"
    # normalizada NÃO reprocessa (spec 2026-07-15 §4)
    assert st.registros[0].descricoes.normalizada == "D"


def test_aplicar_reparear_preserva_ordem_e_um_undo():
    st = AppState()
    st.registros = [
        _rec("x:0", None, "revisao"),                       # não elegível (sem sigla)
        _rec_dir("s:1", "SECF", "Input", (100,)),
        _rec_dir("c:1", "SECF", "Output", (400,)),
    ]
    res = st.aplicar_reparear([r.id for r in st.registros], frozenset(), Config())
    assert res.n_fundidos == 1
    assert st.registros[0].id == "x:0"                      # intocado, na posição
    assert len(st.registros) == 2                           # comando absorvido
    assert st.desfazer() and len(st.registros) == 3         # 1 undo restaura tudo
