import pytest

from tdt.ui.estado import AppState
from tdt.ui.tela_config import TelaConfig

pytest.importorskip("PySide6")


def _tela(qtbot, tmp_path):
    tela = TelaConfig(AppState(), config_path=str(tmp_path / "config.toml"))
    qtbot.addWidget(tela)
    return tela


def test_aviso_pesos_aparece_quando_soma_diferente_de_1(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    tela.spin_tfidf.setValue(0.5)
    tela.spin_vet.setValue(0.3)
    tela.spin_fuzzy.setValue(0.1)
    assert tela.lbl_aviso_pesos.isVisibleTo(tela)
    assert "0.900" in tela.lbl_aviso_pesos.text()
    tela.spin_fuzzy.setValue(0.2)
    assert not tela.lbl_aviso_pesos.isVisibleTo(tela)


def test_restaurar_padroes_repoe_defaults_sem_salvar(qtbot, tmp_path):
    from tdt.config import Config
    tela = _tela(qtbot, tmp_path)
    tela.spin_pct.setValue(0.99)
    tela._restaurar_padroes()
    assert tela.spin_pct.value() == Config().threshold_pct


def test_labels_tem_tooltip_de_efeito(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    assert tela.spin_pct.toolTip() != ""
