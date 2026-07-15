import pytest

pytest.importorskip("PySide6")

from tdt.contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.delegate_sinal import DelegateCombo, DelegateEquipamento, DelegateModulo
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
from tdt.ui.proxy_revisao import ProxyRevisao


def _rec(id_, modulo_nome, eletrico=None):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo_nome, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"),
        eletrico=eletrico if eletrico is not None else Eletrico(),
    )


def _col(nome):
    return ModeloSinais.COLUNAS.index(nome)


def test_delegate_modulo_sugere_nomes_distintos_ordenados_sem_none(qtbot):
    st = AppState()
    st.registros = [
        _rec("a:1", "AL22"), _rec("a:2", "AL21"), _rec("a:3", "AL21"),
        _rec("a:4", None),
    ]
    delegate = DelegateModulo(st)
    combo = delegate.createEditor(None, None, None)
    qtbot.addWidget(combo)
    assert combo.isEditable() is True
    assert [combo.itemText(i) for i in range(combo.count())] == ["AL21", "AL22"]


def test_delegate_combo_set_editor_data_preseleciona_valor_atual(qtbot):
    st = AppState()
    st.registros = [_rec("a:1", "M", eletrico=Eletrico(fase="B"))]
    m = ModeloSinais(st)
    delegate = DelegateCombo(["", "A", "B", "C"])
    combo = delegate.createEditor(None, None, None)
    qtbot.addWidget(combo)
    delegate.setEditorData(combo, m.index(0, _col("Fase")))
    assert combo.currentText() == "B"


def test_delegate_combo_set_editor_data_mapeia_traco_para_opcao_vazia(qtbot):
    st = AppState()
    st.registros = [_rec("a:1", "M")]  # Eletrico() default -> Fase exibe "—"
    m = ModeloSinais(st)
    delegate = DelegateCombo(["", "A", "B", "C"])
    combo = delegate.createEditor(None, None, None)
    qtbot.addWidget(combo)
    delegate.setEditorData(combo, m.index(0, _col("Fase")))
    assert combo.currentText() == ""


def test_delegate_modulo_set_editor_data_preseleciona_modulo_atual(qtbot):
    st = AppState()
    st.registros = [_rec("a:1", "AL21"), _rec("a:2", "AL22")]
    m = ModeloSinais(st)
    delegate = DelegateModulo(st)
    combo = delegate.createEditor(None, None, None)
    qtbot.addWidget(combo)
    delegate.setEditorData(combo, m.index(0, _col("Módulo")))
    assert combo.currentText() == "AL21"


def _proxy_index(modelo, proxy, row, col):
    return proxy.mapFromSource(modelo.index(row, col))


def test_delegate_equipamento_sugere_so_ids_do_mesmo_modulo(qtbot):
    """Caso alvo: corrigir 81-1 -> 52-11 na revisão -- as sugestões precisam
    vir só do MESMO módulo da linha editada, não da lista inteira."""
    st = AppState()
    st.registros = [
        _rec("a:1", "AL21", eletrico=Eletrico(nome_equipamento="52-10")),
        _rec("a:2", "AL21", eletrico=Eletrico(nome_equipamento="52-11")),
        _rec("a:3", "AL22", eletrico=Eletrico(nome_equipamento="89-1")),
        _rec("a:4", "AL21"),  # mesmo módulo, sem equipamento -> não entra
    ]
    m = ModeloSinais(st)
    proxy = ProxyRevisao()
    proxy.setSourceModel(m)
    delegate = DelegateEquipamento(st, proxy)
    idx = _proxy_index(m, proxy, 0, _col("Equipamento"))  # linha do módulo AL21
    combo = delegate.createEditor(None, None, idx)
    qtbot.addWidget(combo)
    assert [combo.itemText(i) for i in range(combo.count())] == ["", "52-10", "52-11"]


def test_delegate_equipamento_set_editor_data_preseleciona_valor_atual(qtbot):
    st = AppState()
    st.registros = [_rec("a:1", "AL21", eletrico=Eletrico(nome_equipamento="52-10"))]
    m = ModeloSinais(st)
    proxy = ProxyRevisao()
    proxy.setSourceModel(m)
    delegate = DelegateEquipamento(st, proxy)
    idx = _proxy_index(m, proxy, 0, _col("Equipamento"))
    combo = delegate.createEditor(None, None, idx)
    qtbot.addWidget(combo)
    delegate.setEditorData(combo, idx)
    assert combo.currentText() == "52-10"
