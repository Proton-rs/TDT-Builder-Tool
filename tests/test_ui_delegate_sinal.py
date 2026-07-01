import pytest

pytest.importorskip("PySide6")

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.delegate_sinal import DelegateModulo
from tdt.ui.estado import AppState


def _rec(id_, modulo_nome):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo_nome, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("d", "D"),
    )


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
