import pytest

from tdt.contracts import (
    Descricoes, Enderecamento, ItemRevisao, ListaHomogenea, Modulo,
    ResultadoPipeline, SignalRecord, TipoSinal,
)
from tdt.ui.app import MainWindow
from tdt.ui.estado import AppState

pytest.importorskip("PySide6")


def _rec(id_, sigla, status):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"), sigla_sinal=sigla, status=status,
    )


def _estado_com_resultado():
    rev = _rec("s:2", None, "revisao")
    estado = AppState()
    estado.resultado = ResultadoPipeline(
        lista=ListaHomogenea(None, "DNP3", (_rec("s:1", "DJF1", "decidido"),)),
        revisao=(ItemRevisao(rev, "score_baixo", ()),),
    )
    estado.registros = [_rec("s:1", "DJF1", "decidido"), rev]
    estado.flags["aprovar_acima_threshold"] = False
    return estado


def _win(qtbot, estado):
    win = MainWindow(estado, config_path="config_inexistente.toml")
    qtbot.addWidget(win)
    return win


def test_comeca_com_etapas_bloqueadas(qtbot):
    win = _win(qtbot, AppState())
    assert win.sidebar._estados["revisao"] == "bloqueada"
    assert win.sidebar._estados["geracao"] == "bloqueada"
    assert win.sidebar._estados["config"] == "disponivel"


def test_executou_desbloqueia_e_vai_para_revisao(qtbot):
    win = _win(qtbot, _estado_com_resultado())
    win.tela_inicial.executou.emit()
    assert win.sidebar._estados["revisao"] == "disponivel"
    assert win.sidebar._estados["entrada"] == "completa"
    assert win.stack.currentIndex() == 1


def test_navegar_por_chave(qtbot):
    win = _win(qtbot, AppState())
    win._navegar("config")
    assert win.stack.currentIndex() == 2


def test_undo_global_restaura_e_refresca(qtbot):
    estado = _estado_com_resultado()
    win = _win(qtbot, estado)
    win.tela_inicial.executou.emit()
    estado.definir_sigla(1, "DJA1")
    assert estado.registros[1].status == "decidido"
    win._desfazer()
    assert estado.registros[1].status == "revisao"


def test_navegar_para_geracao_carrega_resumo(qtbot):
    win = _win(qtbot, _estado_com_resultado())
    win._navegar("geracao")
    assert win.tela_geracao._cards["total"].text() == "2"


def test_rever_pendentes_volta_para_revisao_filtrada(qtbot):
    win = _win(qtbot, _estado_com_resultado())
    win.tela_inicial.executou.emit()
    win._navegar("geracao")
    win.tela_geracao.rever_pendentes.emit()
    assert win.stack.currentIndex() == 1
    assert win.tela_revisao._proxy._status_visivel == "revisao"
