import pytest
from PySide6.QtCore import QSettings

from tdt.ui.sidebar import LARGURA_COLAPSADA, LARGURA_EXPANDIDA, Sidebar

pytest.importorskip("PySide6")

_FLUXO = [("entrada", "1 · Entrada", "①"), ("revisao", "2 · Revisão", "②")]
_FIXOS = [("config", "Configurações", "⚙")]


def _settings(tmp_path):
    return QSettings(str(tmp_path / "ui.ini"), QSettings.IniFormat)


def _sidebar(qtbot, tmp_path):
    sb = Sidebar(_FLUXO, _FIXOS, settings=_settings(tmp_path))
    qtbot.addWidget(sb)
    return sb


def test_item_bloqueado_nao_navega(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    sb.definir_estado("revisao", "bloqueada")
    chamadas = []
    sb.navegar.connect(chamadas.append)
    sb._botoes["revisao"].click()
    assert chamadas == []


def test_item_disponivel_emite_chave(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    chamadas = []
    sb.navegar.connect(chamadas.append)
    sb._botoes["entrada"].click()
    assert chamadas == ["entrada"]


def test_comeca_colapsada_e_toggle_expande_persistindo(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    assert sb.width() == LARGURA_COLAPSADA or sb.minimumWidth() == LARGURA_COLAPSADA
    sb._btn_toggle.click()
    assert sb.minimumWidth() == LARGURA_EXPANDIDA
    sb2 = Sidebar(_FLUXO, _FIXOS, settings=_settings(tmp_path))
    qtbot.addWidget(sb2)
    assert sb2.minimumWidth() == LARGURA_EXPANDIDA


def test_badge_aparece_no_texto_e_some_com_zero(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    sb._btn_toggle.click()  # expande p/ ver rótulo completo
    sb.atualizar_badge("revisao", 37)
    assert "37" in sb._botoes["revisao"].text()
    sb.atualizar_badge("revisao", 0)
    assert "37" not in sb._botoes["revisao"].text()


def test_estado_completa_troca_glifo(qtbot, tmp_path):
    sb = _sidebar(qtbot, tmp_path)
    sb.definir_estado("entrada", "completa")
    assert "✓" in sb._botoes["entrada"].text()
