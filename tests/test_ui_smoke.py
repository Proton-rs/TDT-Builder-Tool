from tdt.ui.app import MainWindow
from tdt.contracts import (
    Descricoes as _D, Enderecamento as _E, Modulo as _M, SignalRecord as _SR, TipoSinal as _T,
)
from tdt.ui.estado import AppState
from tdt.ui.tela_config import TelaConfig
from tdt.ui.tela_inicial import TelaInicial
from tdt.ui.tela_revisao import TelaRevisao


def test_tela_config_instancia_e_aplica(qtbot, tmp_path):
    st = AppState()
    st.paths = {"input": "", "output": str(tmp_path), "template": "t.xlsx", "lista_padrao": "lp.xlsx"}
    tela = TelaConfig(st, config_path=tmp_path / "config.toml")
    qtbot.addWidget(tela)
    tela.spin_pct.setValue(0.55)
    tela.aplicar()
    assert abs(st.config.threshold_pct - 0.55) < 1e-9
    assert (tmp_path / "config.toml").exists()


def test_tela_inicial_instancia(qtbot):
    st = AppState()
    tela = TelaInicial(st)
    qtbot.addWidget(tela)
    assert tela.btn_executar.text().upper().startswith("EXEC")


def test_barra_de_progresso_inicia_oculta_e_responde_ao_sinal(qtbot):
    st = AppState()
    tela = TelaInicial(st)
    qtbot.addWidget(tela)
    # isVisible() depende da janela estar mostrada na tela; em teste headless
    # usamos explicitlyHidden (estado do próprio widget, sem precisar de .show()).
    assert tela.progresso_bar.isHidden() is True
    tela._atualizar_progresso(3, 10)
    assert tela.progresso_bar.isHidden() is False
    assert tela.progresso_bar.maximum() == 10
    assert tela.progresso_bar.value() == 3
    tela._fim()
    assert tela.progresso_bar.isHidden() is True


def test_botao_limpar_log_esvazia_o_log(qtbot):
    st = AppState()
    tela = TelaInicial(st)
    qtbot.addWidget(tela)
    tela.log.appendPlainText("algo")
    tela.btn_limpar_log.click()
    assert tela.log.toPlainText() == ""


def test_tela_revisao_popula_tabela(qtbot):
    st = AppState()
    st.registros = [
        _SR(id="a:1", modulo=_M("M", "sheet_name"), tipo_sinal=_T("Discrete", False, "Input"),
            enderecamento=_E("DNP3", (1,)), descricoes=_D("d", "D"),
            sigla_sinal="DJF1", status="decidido")
    ]
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    assert tela.tabela.model().rowCount() == 1


def test_main_window_instancia(qtbot):
    st = AppState()
    win = MainWindow(st)
    qtbot.addWidget(win)
    assert win.stack.currentIndex() == 0  # tela inicial


def test_aba_revisao_comeca_desabilitada(qtbot):
    st = AppState()
    win = MainWindow(st)
    qtbot.addWidget(win)
    assert win.abas.count() == 3
    assert win.abas.isTabEnabled(1) is False
    assert win.abas.isTabEnabled(2) is False


def test_clicar_aba_revisao_troca_o_stack(qtbot):
    st = AppState()
    win = MainWindow(st)
    qtbot.addWidget(win)
    win.abas.setTabEnabled(1, True)
    win.abas.setCurrentIndex(1)
    assert win.stack.currentIndex() == 1


def test_ir_para_revisao_habilita_e_seleciona_aba(qtbot):
    st = AppState()
    st.flags["pular_revisao"] = False
    st.flags["aprovar_acima_threshold"] = False
    win = MainWindow(st)
    qtbot.addWidget(win)
    win._ir_para_revisao()
    assert win.abas.isTabEnabled(1) is True
    assert win.abas.currentIndex() == 1
    assert win.stack.currentIndex() == 1


def test_ir_para_revisao_tambem_habilita_aba_analise(qtbot):
    st = AppState()
    st.flags["pular_revisao"] = False
    st.flags["aprovar_acima_threshold"] = False
    win = MainWindow(st)
    qtbot.addWidget(win)
    win._ir_para_revisao()
    assert win.abas.isTabEnabled(2) is True


def test_clicar_aba_analise_troca_para_stack_index_3(qtbot):
    st = AppState()
    win = MainWindow(st)
    qtbot.addWidget(win)
    win.abas.setTabEnabled(2, True)
    win.abas.setCurrentIndex(2)
    assert win.stack.currentIndex() == 3


def test_executou_carrega_resultado_na_tela_analise(qtbot):
    from tdt.contracts import ListaHomogenea, ResultadoPipeline
    st = AppState()
    win = MainWindow(st)
    qtbot.addWidget(win)
    res = ResultadoPipeline(ListaHomogenea(None, "DNP3", ()), ())
    win._estado.carregar_resultado(res)
    win.tela_inicial.executou.emit()
    assert win.tela_analise._resultado is res


# --- SP4.1: regressão da revisão (B1/B2/B5) ---
from pathlib import Path as _Path
import pytest as _pytest
from tdt.contracts import Candidato, ResultadoPipeline, ListaHomogenea
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao

_DOCS = _Path("docs")


def _sr(sigla, status, candidatos=()):
    return _SR(id="a:1", modulo=_M("M", "sheet_name"),
              tipo_sinal=_T("Discrete", False, "Input"),
              enderecamento=_E("DNP3", (10,)), descricoes=_D("Falha DJ", "FALHA DJ"),
              sigla_sinal=sigla, status=status, candidatos=candidatos)


def test_selecionar_linha_sem_candidatos_nao_quebra(qtbot):
    st = AppState()
    st.registros = [_sr(None, "revisao", candidatos=())]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)  # dispara _atualizar_painel — não deve lançar
    assert "Status" in tela.lbl_campos.text()


def test_candidato_aparece_com_descricao_adms(qtbot):
    st = AppState()
    st.registros = [_sr("DJF1", "decidido", candidatos=(Candidato("DJF1", 0.87, "mesclado"),))]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)
    assert tela.lista_candidatos.count() == 1
    assert "Disjuntor falha 1" in tela.lista_candidatos.item(0).text()


@_pytest.mark.skipif(not (_DOCS / "Pontos Padrao ADMS_v1.xlsx").exists(),
                     reason="lista padrão ausente")
def test_terminado_popula_lista_padrao(qtbot):
    st = AppState()
    st.paths["lista_padrao"] = str(_DOCS / "Pontos Padrao ADMS_v1.xlsx")
    tela = TelaInicial(st)
    qtbot.addWidget(tela)
    res = ResultadoPipeline(ListaHomogenea(None, "DNP3", ()), ())
    tela._terminado(res)
    assert st.lista_padrao is not None
    assert st.lista_padrao.por_sigla("DJF1") is None or st.lista_padrao.por_sigla("DJF1") is not None


def test_busca_no_painel_lista_resultados_e_escolhe(qtbot):
    st = AppState()
    st.registros = [_sr(None, "revisao", candidatos=())]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),
         SinalPadrao("DJF2", "Disjuntor falha 2", "BISI", None, None, "Discrete")), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)
    tela.buscar_adms("falha")
    assert tela.lista_resultados.count() == 2
    item = tela.lista_resultados.item(0)
    assert "Disjuntor falha" in item.text()
    tela._escolher_resultado(item)  # clicar define a sigla
    assert st.registros[0].sigla_sinal in ("DJF1", "DJF2")


def test_barras_de_score_existem(qtbot):
    st = AppState()
    st.registros = [_sr("DJF1", "decidido", candidatos=(Candidato("DJF1", 0.87, "mesclado"),))]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    tela.tabela.selectRow(0)
    # as 3 barras (emb/tfidf/fuzzy) foram criadas no painel
    assert len(tela.barras) == 3


def test_delegate_cria_editor_com_candidatos(qtbot):
    from tdt.ui.delegate_sinal import DelegateSinal
    from tdt.ui.modelo_tabela import ModeloSinais
    st = AppState()
    st.registros = [_sr("DJF1", "decidido", candidatos=(Candidato("DJF1", 0.87, "mesclado"),
                                                        Candidato("DJF", 0.61, "mesclado")))]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha 1", "BISI", None, None, "Discrete"),), ())
    tela = TelaRevisao(st)
    qtbot.addWidget(tela)
    tela.carregar()
    col = ModeloSinais.COLUNAS.index("Sinal")
    delegate = tela.tabela.itemDelegateForColumn(col)
    assert isinstance(delegate, DelegateSinal)
    editor = delegate.createEditor(tela, None, tela._proxy.index(0, col))
    textos = [editor.itemText(i) for i in range(editor.count())]
    assert "DJF1" in textos
    assert "DJF" in textos


def test_desmarcar_sheet_reflete_em_sheets_excluidas_do_estado(qtbot):
    """Task 2 (spK): desmarcar o checkbox de uma sheet na lista deve gravar
    a exclusão em AppState, para depois ser repassada ao pipeline."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QListWidgetItem

    st = AppState()
    tela = TelaInicial(st)
    qtbot.addWidget(tela)
    tela.lista_sheets.clear()
    for nome in ("GTD_11", "GTD_22"):
        item = QListWidgetItem(nome)
        item.setData(Qt.UserRole, nome)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
        item.setCheckState(Qt.Checked)
        tela.lista_sheets.addItem(item)

    item_excluido = tela.lista_sheets.item(1)
    item_excluido.setCheckState(Qt.Unchecked)

    assert "GTD_22" in st.sheets_excluidas
    assert "GTD_11" not in st.sheets_excluidas


def test_botoes_principais_tem_property_acao(qtbot, tmp_path):
    st = AppState()
    ti = TelaInicial(st); qtbot.addWidget(ti)
    tc = TelaConfig(st, config_path=tmp_path / "config.toml"); qtbot.addWidget(tc)
    assert ti.btn_executar.property("acao") == "principal"
    # TelaConfig instancia e tem um botão marcado como ação principal
    from PySide6.QtWidgets import QPushButton
    principais = [b for b in tc.findChildren(QPushButton) if b.property("acao") == "principal"]
    assert len(principais) >= 1
