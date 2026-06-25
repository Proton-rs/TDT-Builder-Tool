from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, ItemRevisao, ListaHomogenea, Modulo,
    ResultadoPipeline, SignalRecord, TipoSinal,
)
from tdt.ui.tela_analise import TelaAnalise


def _sr(id_, sigla, status, candidatos=()):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"),
        sigla_sinal=sigla, status=status, candidatos=candidatos,
    )


def _resultado_basico():
    decididos = (
        _sr("a:1", "DJF1", "decidido", (Candidato("DJF1", 0.9, "mesclado"),)),
        _sr("a:2", "DJF2", "decidido", (Candidato("DJF2", 0.8, "mesclado"),)),
    )
    em_revisao = _sr("a:3", None, "revisao", ())
    revisao = (ItemRevisao(em_revisao, "score_baixo"),)
    lista = ListaHomogenea("SE1", "DNP3", decididos)
    return ResultadoPipeline(lista, revisao)


def test_tela_analise_instancia(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    assert tela._table is not None
    assert tela._combo_status.count() == 3


def test_carregar_popula_tabela_sem_duplicar_ids(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    tela.carregar(_resultado_basico())
    assert tela._proxy.rowCount() == 3  # 2 decididos + 1 revisão, sem duplicar


def test_carregar_inclui_registro_que_so_esta_em_revisao(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    res = _resultado_basico()
    tela.carregar(res)
    ids = set()
    for row in range(tela._proxy.rowCount()):
        idx = tela._proxy.index(row, 0)
        ids.add(tela._proxy.data(idx))
    assert "a:3" in ids
    assert ids == {"a:1", "a:2", "a:3"}


def test_estatisticas_calculadas_corretamente(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    tela.carregar(_resultado_basico())
    assert tela._stats_labels["total"].text() == "3"
    assert tela._stats_labels["decididos"].text() == "2"
    assert tela._stats_labels["revisao"].text() == "1"
    assert "66.7%" in tela._stats_labels["taxa"].text()


def test_estatisticas_motivos_agregados(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    res = ResultadoPipeline(
        ListaHomogenea("SE1", "DNP3", ()),
        (
            ItemRevisao(_sr("a:1", None, "revisao"), "score_baixo"),
            ItemRevisao(_sr("a:2", None, "revisao"), "score_baixo"),
            ItemRevisao(_sr("a:3", None, "revisao"), "sem_endereco"),
        ),
    )
    tela.carregar(res)
    texto = tela._motivos_label.text()
    assert "score_baixo: 2" in texto
    assert "sem_endereco: 1" in texto


def test_estatisticas_sem_registros(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    res = ResultadoPipeline(ListaHomogenea(None, "DNP3", ()), ())
    tela.carregar(res)
    assert tela._stats_labels["total"].text() == "0"
    assert tela._stats_labels["taxa"].text() == "—"


def test_filtro_todos_mostra_tudo(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    tela.carregar(_resultado_basico())
    tela._combo_status.setCurrentText("Todos")
    assert tela._proxy.rowCount() == 3


def test_filtro_decididos_mostra_so_decididos(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    tela.carregar(_resultado_basico())
    tela._combo_status.setCurrentText("Decididos")
    assert tela._proxy.rowCount() == 2


def test_filtro_revisao_mostra_so_revisao(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    tela.carregar(_resultado_basico())
    tela._combo_status.setCurrentText("Revisão")
    assert tela._proxy.rowCount() == 1
    idx = tela._proxy.index(0, 0)
    assert tela._proxy.data(idx) == "a:3"


def test_filtro_volta_a_todos_apos_revisao(qtbot):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    tela.carregar(_resultado_basico())
    tela._combo_status.setCurrentText("Revisão")
    assert tela._proxy.rowCount() == 1
    tela._combo_status.setCurrentText("Todos")
    assert tela._proxy.rowCount() == 3


def test_exportar_sem_resultado_nao_lanca(qtbot, monkeypatch):
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    # Sem path selecionado (usuário cancelou) — não deve tentar importar nada.
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName", lambda *a, **k: ("", "")
    )
    tela._exportar()  # não deve lançar


def test_exportar_gera_arquivo_xlsx(qtbot, monkeypatch, tmp_path):
    """Task 2.3 implementou exportar_analise — o botão agora gera o .xlsx de fato."""
    tela = TelaAnalise()
    qtbot.addWidget(tela)
    tela.carregar(_resultado_basico())
    destino = tmp_path / "saida.xlsx"
    monkeypatch.setattr(
        "PySide6.QtWidgets.QFileDialog.getSaveFileName", lambda *a, **k: (str(destino), "")
    )
    avisos = []
    monkeypatch.setattr(
        "PySide6.QtWidgets.QMessageBox.warning",
        lambda *a, **k: avisos.append(a),
    )
    tela._exportar()  # não deve lançar nem avisar — exportação real
    assert destino.exists()
    assert avisos == []
