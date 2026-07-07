import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.estado import AppState
from tdt.ui.tela_geracao import TelaGeracao, enderecos_duplicados

pytest.importorskip("PySide6")


def _rec(id_, indices=(1,), indices_saida=(), status="revisao"):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", indices, indices_saida),
        descricoes=Descricoes("d", "D"), status=status,
    )


def test_duplicata_de_input_detectada():
    regs = [_rec("a", indices=(14,)), _rec("b", indices=(14,)), _rec("c", indices=(2,))]
    assert enderecos_duplicados(regs) == {("in", 14): ["a", "b"]}


def test_input_e_output_iguais_nao_e_duplicata():
    regs = [_rec("a", indices=(14,)), _rec("b", indices=(), indices_saida=(14,))]
    assert enderecos_duplicados(regs) == {}


def test_sem_duplicatas_dict_vazio():
    assert enderecos_duplicados([_rec("a", indices=(1,))]) == {}


def _tela(qtbot, registros):
    estado = AppState()
    estado.registros = registros
    estado.subestacao = "SAN2"
    tela = TelaGeracao(estado)
    qtbot.addWidget(tela)
    tela.carregar()
    return tela


def test_carregar_preenche_resumo(qtbot):
    tela = _tela(qtbot, [
        _rec("a", status="decidido"), _rec("b", indices=(2,), status="revisao"),
    ])
    assert tela._cards["total"].text() == "2"
    assert tela._cards["decididos"].text() == "1"
    assert tela._cards["pendentes"].text() == "1"
    assert "SAN2" in tela.lbl_titulo.text()


def test_gerar_com_pendentes_pergunta_e_respeita_nao(qtbot, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    tela = _tela(qtbot, [_rec("a", status="revisao")])
    tela._estado.lista_padrao = object()  # truthy; não chega a ser usado
    tela._estado.paths.update({"template": "t.xlsx", "output": "out"})
    monkeypatch.setattr(
        "tdt.ui.tela_geracao.QMessageBox.question",
        lambda *a, **k: QMessageBox.StandardButton.No)
    chamado = {}
    monkeypatch.setattr(
        "tdt.ui.tela_geracao.pipeline.gerar_tdt",
        lambda *a, **k: chamado.setdefault("gerou", True))
    tela._gerar()
    assert "gerou" not in chamado


def test_aviso_pendentes_emite_rever(qtbot):
    tela = _tela(qtbot, [_rec("a", status="revisao")])
    recebido = []
    tela.rever_pendentes.connect(lambda: recebido.append(True))
    tela.rever_pendentes.emit()
    assert recebido
