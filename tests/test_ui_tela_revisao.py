from PySide6.QtCore import QItemSelectionModel, QPoint
from PySide6.QtWidgets import QDialog

import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.delegate_sinal import DelegateCombo, DelegateModulo
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
from tdt.ui.tela_revisao import FiltroColunaDialog, TelaRevisao, decidir_acao_pareamento

pytest.importorskip("PySide6")


def _rec_sheet(id_com_sheet, modulo_nome, bruta, direcao="Input", indices=(1,)):
    """Como `_rec`, mas o `id` carrega a sheet de origem (f"{sheet}:{linha}")."""
    return SignalRecord(
        id=id_com_sheet, modulo=Modulo(modulo_nome, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", indices, ()),
        descricoes=Descricoes(bruta, bruta),
    )


def _rec(id_, modulo_nome, bruta, direcao="Input", indices=(1,), indices_saida=()):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo_nome, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
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


# --- abas por sheet (SP-J Task 2: substitui o filtro de texto global) ---

def test_abas_sheet_tem_tudo_primeiro_mais_uma_por_sheet_distinta(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec_sheet("Discreto:0", "SE1", "A"),
        _rec_sheet("Analogicos:0", "SE1", "B"),
        _rec_sheet("Discreto:1", "SE1", "C"),
    ])
    textos = [tela.abas_sheet.tabText(i) for i in range(tela.abas_sheet.count())]
    assert textos == ["Tudo", "Analogicos", "Discreto"]
    assert tela.abas_sheet.currentIndex() == 0
    assert tela._proxy.rowCount() == 3


def test_selecionar_aba_sheet_filtra_a_tabela(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec_sheet("Discreto:0", "SE1", "A"),
        _rec_sheet("Analogicos:0", "SE1", "B"),
    ])
    idx_discreto = next(
        i for i in range(tela.abas_sheet.count())
        if tela.abas_sheet.tabText(i) == "Discreto"
    )
    tela.abas_sheet.setCurrentIndex(idx_discreto)
    assert tela._proxy.rowCount() == 1
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    assert tela._proxy.index(0, col_desc).data() == "A"


def test_voltar_para_aba_tudo_remove_o_filtro_de_sheet(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec_sheet("Discreto:0", "SE1", "A"),
        _rec_sheet("Analogicos:0", "SE1", "B"),
    ])
    idx_discreto = next(
        i for i in range(tela.abas_sheet.count())
        if tela.abas_sheet.tabText(i) == "Discreto"
    )
    tela.abas_sheet.setCurrentIndex(idx_discreto)
    assert tela._proxy.rowCount() == 1
    tela.abas_sheet.setCurrentIndex(0)
    assert tela._proxy.rowCount() == 2


def test_filtro_global_de_texto_foi_removido(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A")])
    assert not hasattr(tela, "ed_filtro")
    assert not hasattr(tela, "_filtrar_texto")


# --- popup estilo Excel por coluna (SP-J Task 3) ---

def test_duplo_clique_no_header_abre_popup_excel(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")

    chamado = {}

    class _DialogFalso:
        def __init__(self, *a, **k):
            chamado["criado"] = True

        def exec(self):
            return QDialog.Accepted

        def valores_selecionados(self):
            return {"DISJUNTOR"}

        def texto_contem(self):
            return ""

    monkeypatch.setattr("tdt.ui.tela_revisao.FiltroColunaDialog", _DialogFalso)
    monkeypatch.setattr(
        tela.tabela.horizontalHeader(), "logicalIndexAt", lambda pos: col_desc)
    tela._filtrar_coluna(QPoint(0, 0))
    assert chamado.get("criado") is True
    assert tela._proxy.colunas_filtradas() == {col_desc}
    assert tela._proxy.rowCount() == 1


def test_popup_excel_cancelado_nao_altera_filtro(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")

    class _DialogCancelado:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.Rejected

    monkeypatch.setattr("tdt.ui.tela_revisao.FiltroColunaDialog", _DialogCancelado)
    monkeypatch.setattr(
        tela.tabela.horizontalHeader(), "logicalIndexAt", lambda pos: col_desc)
    tela._filtrar_coluna(QPoint(0, 0))
    assert tela._proxy.colunas_filtradas() == set()
    assert tela._proxy.rowCount() == 2


def test_popup_excel_limpar_remove_filtro_da_coluna(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    tela._proxy.set_filtro_coluna(col_desc, {"DISJUNTOR"})
    assert tela._proxy.rowCount() == 1

    class _DialogLimpar:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return QDialog.Accepted

        def valores_selecionados(self):
            return None

        def texto_contem(self):
            return ""

    monkeypatch.setattr("tdt.ui.tela_revisao.FiltroColunaDialog", _DialogLimpar)
    monkeypatch.setattr(
        tela.tabela.horizontalHeader(), "logicalIndexAt", lambda pos: col_desc)
    tela._filtrar_coluna(QPoint(0, 0))
    assert tela._proxy.colunas_filtradas() == set()
    assert tela._proxy.rowCount() == 2


def test_construir_popup_excel_real_lista_valores_distintos_da_coluna(qtbot):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
        _rec("3", "SE1", "DISJUNTOR"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    dialog = FiltroColunaDialog(
        "Descr. bruta", tela._proxy.valores_unicos(col_desc), None, tela,
    )
    qtbot.addWidget(dialog)
    textos = {dialog.lista.item(i).text() for i in range(dialog.lista.count())}
    assert textos == {"DISJUNTOR", "SECCIONADORA"}
    assert dialog.valores_selecionados() is None  # tudo marcado por padrão = sem filtro


def test_popup_unificado_aplica_contem_e_valores(qtbot, monkeypatch):
    tela = _tela_carregada(qtbot, [
        _rec("1", "SE1", "DISJUNTOR"),
        _rec("2", "SE2", "SECCIONADORA"),
    ])
    col = ModeloSinais.COLUNAS.index("Descr. bruta")

    class _DialogFake:
        def __init__(self, *a, **k):
            pass
        def exec(self):
            return QDialog.Accepted
        def valores_selecionados(self):
            return None
        def texto_contem(self):
            return "DISJ"

    monkeypatch.setattr("tdt.ui.tela_revisao.FiltroColunaDialog", _DialogFake)
    monkeypatch.setattr(
        tela.tabela.horizontalHeader(), "logicalIndexAt", lambda pos: col)
    tela._filtrar_coluna(QPoint(0, 0))
    assert tela._proxy.filtroColuna(col) == "DISJ"
    assert tela._proxy.rowCount() == 1
    assert tela.btn_limpar_filtros.isVisibleTo(tela)


def test_limpar_todos_zera_filtros(qtbot):
    tela = _tela_carregada(qtbot, [_rec("1", "SE1", "A"), _rec("2", "SE2", "B")])
    col = ModeloSinais.COLUNAS.index("Módulo")
    tela._proxy.setFiltroColuna(col, "SE1")
    tela._atualizar_chip_filtros()
    tela._limpar_filtros()
    assert tela._proxy.filtros_ativos() == 0
    assert tela._proxy.rowCount() == 2
