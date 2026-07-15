import pytest

from tdt.ui.tela_inicial import linha_log_html, motivo_bloqueio

pytest.importorskip("PySide6")


def test_motivo_bloqueio_lista_pendencias_na_ordem(tmp_path):
    arq = tmp_path / "a.xlsx"
    arq.write_text("x")
    paths = {"input": str(arq), "template": "", "lista_padrao": str(arq)}
    assert motivo_bloqueio("", paths) == ["sigla da SE", "template DNP3"]


def test_motivo_bloqueio_vazio_quando_tudo_ok(tmp_path):
    arq = tmp_path / "a.xlsx"
    arq.write_text("x")
    paths = {"input": str(arq), "template": str(arq), "lista_padrao": str(arq)}
    assert motivo_bloqueio("SAN2", paths) == []


def test_motivo_bloqueio_path_inexistente_conta_como_falta(tmp_path):
    paths = {"input": str(tmp_path / "nao_existe.xlsx"), "template": "",
             "lista_padrao": ""}
    assert motivo_bloqueio("SAN2", paths) == [
        "arquivo de input", "template DNP3", "lista padrão ADMS"]


def test_linha_log_html_cor_por_nivel():
    assert 'color:#e0604c' in linha_log_html("[ERRO] x")
    assert 'color:#e0a83f' in linha_log_html("[AVISO] x")
    assert 'color:#9aa3b5' in linha_log_html("[INFO] x")
    assert 'color:#c6ccd9' in linha_log_html("linha sem nivel")


def test_linha_log_html_escapa_html():
    assert "<b>" not in linha_log_html("[INFO] <b>oi</b>")


from tdt.ui.estado import AppState
from tdt.ui.tela_inicial import CardArquivo, TelaInicial


class _WorkerFake:
    """Nunca inicia thread; só oferece a superfície de sinais usada pela tela."""

    def __init__(self, **kwargs):
        raise AssertionError("worker não deve ser criado nestes testes")


def _tela(qtbot, tmp_path, paths=None):
    estado = AppState()
    if paths:
        estado.paths.update(paths)
    tela = TelaInicial(estado, worker_factory=_WorkerFake,
                       config_path=str(tmp_path / "config.toml"))
    qtbot.addWidget(tela)
    return tela


def test_card_faltando_vira_ok_apos_recarregar(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    assert tela.cards["template"].property("estado") == "faltando"
    arq = tmp_path / "t.xlsx"
    arq.write_text("x")
    tela._estado.paths["template"] = str(arq)
    tela.recarregar()
    assert tela.cards["template"].property("estado") == "ok"


def test_label_motivo_lista_pendencias(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    tela._atualizar_estado_botao()
    assert not tela.btn_executar.isEnabled()
    assert "sigla da SE" in tela.lbl_motivo.text()


def test_botao_habilita_com_tudo_preenchido(qtbot, tmp_path):
    arq = tmp_path / "a.xlsx"
    arq.write_text("x")
    paths = {"input": str(arq), "template": str(arq), "lista_padrao": str(arq)}
    tela = _tela(qtbot, tmp_path, paths)
    tela.combo_sub.lineEdit().setText("SAN2")
    assert tela.btn_executar.isEnabled()
    assert not tela.lbl_motivo.isVisibleTo(tela)


def test_erro_do_worker_expande_log(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    assert not tela.log.isVisibleTo(tela)
    tela._on_erro("explodiu")
    assert tela.log.isVisibleTo(tela)
    assert "explodiu" in tela.log.toPlainText()


def test_log_msg_info_atualiza_etapa(qtbot, tmp_path):
    tela = _tela(qtbot, tmp_path)
    tela._on_log("[INFO] pipeline: normalizando descrições…")
    assert "normalizando" in tela.lbl_etapa.text()


# --- marcação em grupo (spec 2026-07-15 §1) ---
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QListWidget, QListWidgetItem

from tdt.ui.tela_inicial import definir_marcacao, inverter_marcacao


def _lista_com_itens(qtbot, n=4):
    lista = QListWidget()
    lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
    qtbot.addWidget(lista)
    for i in range(n):
        it = QListWidgetItem(f"Sheet{i}")
        it.setFlags(it.flags() | Qt.ItemIsUserCheckable)
        it.setCheckState(Qt.Checked)
        lista.addItem(it)
    return lista


def test_definir_marcacao_age_nas_selecionadas(qtbot):
    lista = _lista_com_itens(qtbot)
    lista.item(1).setSelected(True)
    lista.item(2).setSelected(True)
    definir_marcacao(lista, False)
    estados = [lista.item(i).checkState() for i in range(4)]
    assert estados == [Qt.Checked, Qt.Unchecked, Qt.Unchecked, Qt.Checked]


def test_definir_marcacao_sem_selecao_age_em_todas(qtbot):
    lista = _lista_com_itens(qtbot)
    definir_marcacao(lista, False)
    assert all(lista.item(i).checkState() == Qt.Unchecked for i in range(4))


def test_inverter_marcacao(qtbot):
    lista = _lista_com_itens(qtbot)
    lista.item(0).setCheckState(Qt.Unchecked)
    inverter_marcacao(lista)  # sem seleção -> todas
    estados = [lista.item(i).checkState() for i in range(4)]
    assert estados == [Qt.Checked, Qt.Unchecked, Qt.Unchecked, Qt.Unchecked]
