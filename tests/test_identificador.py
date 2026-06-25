import openpyxl

from tdt.identificador import classificar, ler_rows


def test_detecta_sheets_de_dados_no_nao_homogeneo(docs):
    wb = openpyxl.load_workbook(docs / "input_nao_homogeneo_1.xlsx", read_only=True, data_only=True)
    rota = classificar(wb, override="nao-homogeneo")
    assert rota.homogeneo is False
    assert "01F1_GTA_P" in rota.sheets_dados
    # a capa (sem colunas de dados) não entra
    assert "Capa" not in rota.sheets_dados
    wb.close()


def test_override_respeitado(docs):
    wb = openpyxl.load_workbook(docs / "input_nao_homogeneo_1.xlsx", read_only=True, data_only=True)
    assert classificar(wb, override="homogeneo").homogeneo is True
    wb.close()


def test_ler_rows_retorna_tuplas(docs):
    wb = openpyxl.load_workbook(docs / "input_nao_homogeneo_1.xlsx", read_only=True, data_only=True)
    rows = ler_rows(wb["01F1_GTA_P"])
    assert len(rows) > 10
    assert isinstance(rows[0], tuple)
    wb.close()
