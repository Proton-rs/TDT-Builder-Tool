from datetime import date

from tdt.nomes_saida import nome_saida

HOJE = date.today().strftime("%Y%m%d")


def test_nome_com_subestacao(tmp_path):
    assert nome_saida("TDT", "GAU", tmp_path).name == f"TDT_GAU_{HOJE}.xlsx"


def test_nome_sem_subestacao(tmp_path):
    assert nome_saida("TDT", None, tmp_path).name == f"TDT_{HOJE}.xlsx"


def test_sequencia_quando_existe(tmp_path):
    (tmp_path / f"TDT_GAU_{HOJE}.xlsx").touch()
    assert nome_saida("TDT", "GAU", tmp_path).name == f"TDT_GAU_{HOJE}_v2.xlsx"
    (tmp_path / f"TDT_GAU_{HOJE}_v2.xlsx").touch()
    assert nome_saida("TDT", "GAU", tmp_path).name == f"TDT_GAU_{HOJE}_v3.xlsx"
