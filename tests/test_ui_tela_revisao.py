from PySide6.QtCore import QPoint

import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
from tdt.ui.tela_revisao import TelaRevisao

pytest.importorskip("PySide6")


def _rec(id_, modulo_nome, bruta):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo_nome, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(bruta, bruta),
    )


def _tela_carregada(qtbot, registros):
    estado = AppState()
    estado.registros = registros
    tela = TelaRevisao(estado)
    qtbot.addWidget(tela)
    tela.carregar()
    return tela


def test_menu_filtro_modulo_lista_valores_distintos(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "A"),
        _rec("2", "SE2", "B"),
        _rec("3", "SE1", "C"),
    ])
    col_modulo = ModeloSinais.COLUNAS.index("Módulo")
    menu = tela._construir_menu_coluna(col_modulo, QPoint(0, 0))
    textos = {a.text() for a in menu.actions() if a.isCheckable()}
    assert textos == {"SE1", "SE2"}


def test_selecionar_modulo_no_menu_aplica_filtro_via_proxy(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "A"),
        _rec("2", "SE2", "B"),
    ])
    col_modulo = ModeloSinais.COLUNAS.index("Módulo")
    menu = tela._construir_menu_coluna(col_modulo, QPoint(0, 0))
    acao_se2 = next(a for a in menu.actions() if a.text() == "SE2")
    acao_se2.trigger()
    assert tela._proxy.filtroColuna(col_modulo) == "SE2"
    assert tela._proxy.rowCount() == 1


def test_outras_colunas_continuam_usando_dialogo_texto_livre(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    monkeypatch.setattr(
        tela.tabela.horizontalHeader(), "logicalIndexAt", lambda pos: col_desc
    )

    chamado = {}

    def _fake_get_text(parent, titulo, label, text=""):
        chamado["ok"] = True
        return "DISJUNTOR", True

    monkeypatch.setattr("tdt.ui.tela_revisao.QInputDialog.getText", _fake_get_text)
    tela._filtrar_coluna(QPoint(0, 0))
    assert chamado.get("ok") is True
    assert tela._proxy.filtroColuna(col_desc) == "DISJUNTOR"


def test_coluna_modulo_nao_usa_dialogo_texto_livre(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
    ])
    col_modulo = ModeloSinais.COLUNAS.index("Módulo")
    monkeypatch.setattr(
        tela.tabela.horizontalHeader(), "logicalIndexAt", lambda pos: col_modulo
    )

    def _fail_get_text(*args, **kwargs):
        raise AssertionError("não deveria abrir QInputDialog para coluna Módulo")

    monkeypatch.setattr("tdt.ui.tela_revisao.QInputDialog.getText", _fail_get_text)

    chamado = {}

    class _MenuFalso:
        def exec(self, *args, **kwargs):
            chamado["exec_chamado"] = True

    monkeypatch.setattr(
        tela, "_construir_menu_coluna", lambda col, pos: _MenuFalso()
    )
    tela._filtrar_coluna(QPoint(0, 0))
    assert chamado.get("exec_chamado") is True


def test_adicionar_sinal_faz_snapshot_antes_e_aumenta_linhas(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    assert len(tela._estado._historico) == 0
    tela._adicionar_sinal()
    assert len(tela._estado._historico) == 1
    assert len(tela._estado.registros) == 2
    assert tela._modelo.rowCount() == 2


def test_adicionar_sinal_cria_registro_em_branco_com_id_unico(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    tela._adicionar_sinal()
    tela._adicionar_sinal()
    novo1, novo2 = tela._estado.registros[1], tela._estado.registros[2]
    assert novo1.id != novo2.id
    assert novo1.descricoes.bruta == ""
    assert novo1.modulo.nome is None


def test_remover_sinais_sem_selecao_nao_faz_nada(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    tela._remover_sinais()
    assert len(tela._estado._historico) == 0
    assert len(tela._estado.registros) == 1


def test_remover_sinais_faz_snapshot_antes_e_remove_linha_selecionada(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "A"),
        _rec("2", "SE2", "B"),
    ])
    tela.tabela.selectRow(0)
    tela._remover_sinais()
    assert len(tela._estado._historico) == 1
    assert tela._estado._historico[0][0].id == "1"
    assert len(tela._estado.registros) == 1
    assert tela._estado.registros[0].id == "2"
