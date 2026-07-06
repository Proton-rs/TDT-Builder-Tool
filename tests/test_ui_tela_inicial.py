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
