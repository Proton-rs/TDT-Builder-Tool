from PySide6.QtCore import QItemSelectionModel, QPoint

import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.delegate_sinal import DelegateCombo, DelegateModulo
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
from tdt.ui.tela_revisao import TelaRevisao, decidir_acao_pareamento

pytest.importorskip("PySide6")


def _rec(id_, modulo_nome, bruta, direcao="Input", indices=(1,), indices_saida=()):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo_nome, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, direcao),
        enderecamento=Enderecamento("DNP3", indices, indices_saida),
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


# --- decidir_acao_pareamento (função pura, sem Qt) ---

def test_decidir_acao_pareamento_um_input_um_output_parear():
    status = _rec("1", "SE1", "A", direcao="Input", indices=(5,))
    comando = _rec("2", "SE1", "A", direcao="Output", indices=(0,))
    acao, dados = decidir_acao_pareamento([status, comando])
    assert acao == "parear"
    assert dados == (status, comando)


def test_decidir_acao_pareamento_dois_inputs_erro():
    r1 = _rec("1", "SE1", "A", direcao="Input")
    r2 = _rec("2", "SE1", "B", direcao="Input")
    acao, msg = decidir_acao_pareamento([r1, r2])
    assert acao == "erro"
    assert isinstance(msg, str) and msg


def test_decidir_acao_pareamento_um_inputoutput_desvincular():
    fundido = _rec("1", "SE1", "A", direcao="InputOutput", indices=(5,), indices_saida=(0,))
    acao, dados = decidir_acao_pareamento([fundido])
    assert acao == "desvincular"
    assert dados is fundido


def test_decidir_acao_pareamento_um_input_sozinho_erro():
    r1 = _rec("1", "SE1", "A", direcao="Input")
    acao, msg = decidir_acao_pareamento([r1])
    assert acao == "erro"
    assert isinstance(msg, str) and msg


def test_decidir_acao_pareamento_tres_selecionados_erro():
    regs = [
        _rec("1", "SE1", "A", direcao="Input"),
        _rec("2", "SE1", "B", direcao="Output"),
        _rec("3", "SE1", "C", direcao="Input"),
    ]
    acao, msg = decidir_acao_pareamento(regs)
    assert acao == "erro"
    assert isinstance(msg, str) and msg


def test_decidir_acao_pareamento_sem_selecao_erro():
    acao, msg = decidir_acao_pareamento([])
    assert acao == "erro"


# --- _parear_sinais (handler da tela) ---

def test_parear_sinais_sem_selecao_nao_faz_nada(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    tela._parear_sinais()
    assert len(tela._estado._historico) == 0
    assert len(tela._estado.registros) == 1


def test_parear_sinais_selecao_invalida_mostra_aviso_sem_mutar(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "A", direcao="Input"),
        _rec("2", "SE2", "B", direcao="Input"),
    ])
    avisos = []
    monkeypatch.setattr(
        "tdt.ui.tela_revisao.QMessageBox.warning",
        lambda *a, **k: avisos.append(a),
    )
    tela.tabela.selectRow(0)
    tela.tabela.selectionModel().select(
        tela._proxy.index(1, 0),
        QItemSelectionModel.Select | QItemSelectionModel.Rows,
    )
    tela._parear_sinais()
    assert len(avisos) == 1
    assert len(tela._estado._historico) == 0
    assert len(tela._estado.registros) == 2


def test_parear_sinais_confirmado_funde_input_e_output(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "A", direcao="Input", indices=(5,)),
        _rec("2", "SE1", "A", direcao="Output", indices=(0,)),
    ])
    monkeypatch.setattr(tela, "_confirmar_dialogo", lambda acao, descricao: True)
    tela.tabela.selectAll()
    tela._parear_sinais()
    assert len(tela._estado._historico) == 1
    assert len(tela._estado.registros) == 1
    fundido = tela._estado.registros[0]
    assert fundido.tipo_sinal.direcao == "InputOutput"
    assert fundido.enderecamento.indices == (5,)
    assert fundido.enderecamento.indices_saida == (0,)


def test_parear_sinais_cancelado_no_dialogo_nao_muta(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "A", direcao="Input", indices=(5,)),
        _rec("2", "SE1", "A", direcao="Output", indices=(0,)),
    ])
    monkeypatch.setattr(tela, "_confirmar_dialogo", lambda acao, descricao: False)
    tela.tabela.selectAll()
    tela._parear_sinais()
    assert len(tela._estado._historico) == 0
    assert len(tela._estado.registros) == 2


def test_parear_sinais_desvincular_confirmado_separa_em_dois(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "A", direcao="InputOutput", indices=(5,), indices_saida=(0,)),
    ])
    monkeypatch.setattr(tela, "_confirmar_dialogo", lambda acao, descricao: True)
    tela.tabela.selectRow(0)
    tela._parear_sinais()
    assert len(tela._estado._historico) == 1
    assert len(tela._estado.registros) == 2
    direcoes = {r.tipo_sinal.direcao for r in tela._estado.registros}
    assert direcoes == {"Input", "Output"}
    status_rec = next(r for r in tela._estado.registros if r.tipo_sinal.direcao == "Input")
    comando_rec = next(r for r in tela._estado.registros if r.tipo_sinal.direcao == "Output")
    assert status_rec.enderecamento.indices == (5,)
    assert comando_rec.enderecamento.indices == (0,)
    assert comando_rec.id.startswith("1_saida_")
    assert comando_rec.id != status_rec.id


def test_carregar_registra_delegate_combo_nas_colunas_de_dominio(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    for nome in ("Tipo", "Fase", "Nível Tensão", "Barra", "Tipo Equip."):
        col = ModeloSinais.COLUNAS.index(nome)
        delegate = tela.tabela.itemDelegateForColumn(col)
        assert isinstance(delegate, DelegateCombo), nome


def test_carregar_registra_delegate_modulo_na_coluna_modulo(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    col = ModeloSinais.COLUNAS.index("Módulo")
    delegate = tela.tabela.itemDelegateForColumn(col)
    assert isinstance(delegate, DelegateModulo)
