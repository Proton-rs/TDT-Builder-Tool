import pytest

from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.ui.estado import AppState
from tdt.ui.tela_geracao import TelaGeracao, enderecos_duplicados, filtrar_por_modulos

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


def _rec_mod(rid, modulo):
    return SignalRecord(
        id=rid, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("X", "X"), status="decidido",
    )


def test_filtrar_por_modulos():
    regs = [_rec_mod("a:1", "AL11"), _rec_mod("a:2", "AL12"), _rec_mod("a:3", None)]
    assert [r.id for r in filtrar_por_modulos(regs, {"AL11"})] == ["a:1"]
    assert [r.id for r in filtrar_por_modulos(regs, {"AL11", "AL12", None})] == [
        "a:1", "a:2", "a:3"]
    assert filtrar_por_modulos(regs, set()) == []


def test_filtrar_por_modulos_none_e_o_sem_modulo():
    regs = [_rec_mod("a:1", None)]
    assert [r.id for r in filtrar_por_modulos(regs, {None})] == ["a:1"]


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
        "tdt.pipeline.gerar_tdt",
        lambda *a, **k: chamado.setdefault("gerou", True))
    tela._gerar()
    assert "gerou" not in chamado


def test_aviso_pendentes_emite_rever(qtbot):
    tela = _tela(qtbot, [_rec("a", status="revisao")])
    recebido = []
    tela.rever_pendentes.connect(lambda: recebido.append(True))
    tela.rever_pendentes.emit()
    assert recebido


def test_custom_id_duplicado_vai_para_relatorio_de_revisao(qtbot, monkeypatch, tmp_path):
    tela = _tela(qtbot, [_rec("a", status="decidido")])
    tela._estado.lista_padrao = object()
    tela._estado.paths.update({"template": "t.xlsx", "output": str(tmp_path)})

    class _FakeWb:
        def save(self, path):
            pass

    def fake_gerar_tdt(registros, template, lp, subestacao=None, aliases=None, auditoria=None):
        auditoria.evento(
            "engine", "1 registros com Custom ID duplicado -> revisão", "AVISO",
            dados={"ids": ("a",)})
        return _FakeWb()

    monkeypatch.setattr("tdt.pipeline.gerar_tdt", fake_gerar_tdt)

    capturado = {}

    def fake_relatorio(registros, revisao, destino, diagnostico=None, subestacao=None):
        capturado["revisao"] = revisao
        return tmp_path / "Auditoria_x.xlsx"

    monkeypatch.setattr("tdt.ui.tela_geracao.gerar_relatorio_revisao", fake_relatorio)

    tela._gerar()

    motivos = {it.registro.id: it.motivo for it in capturado["revisao"]}
    assert motivos.get("a") == "custom_id_duplicado"


def _rec_sigla(rid, sigla, equipamento, modulo="AL11"):
    return SignalRecord(
        id=rid, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(f"{sigla} BRUTO", sigla),
        sigla_sinal=sigla, status="decidido",
        eletrico=Eletrico(nome_equipamento=equipamento),
    )


def test_aviso_43lr_sem_43tc(qtbot):
    tela = _tela(qtbot, [_rec_sigla("a:1", "43LR", "52-1")])
    textos = [
        tela._avisos_box.itemAt(i).widget().layout().itemAt(0).widget().text()
        for i in range(tela._avisos_box.count())
    ]
    assert any("43LR sem 43TC" in t for t in textos)
