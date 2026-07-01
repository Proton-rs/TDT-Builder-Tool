import openpyxl
import pytest

from bench.gate_tdt_real import carregar_siglas_por_endereco, comparar


def _tdt_fake(path, linhas):
    """linhas = list[(signal_name, incoords)] na sheet DNP3_DiscreteSignals."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "DNP3_DiscreteSignals"
    for _ in range(4):  # rows 1-4 cabeçalho
        ws.append([])
    for nome, addr in linhas:
        row = [None] * 32
        row[0] = nome
        row[31] = addr
        ws.append(row)
    wb.create_sheet("DNP3_AnalogSignals")  # vazia mas presente
    wb.save(path)


def test_carregar_extrai_sigla_ultimo_token_e_endereco(tmp_path):
    f = tmp_path / "t.xlsx"
    _tdt_fake(f, [("GTD_AL13_52-13_CCMO", 1706), ("GTD_LTGTA_89-2_DSEC", 16)])
    d = carregar_siglas_por_endereco(str(f))
    assert d == {1706: ("GTD_AL13_52-13_CCMO", "CCMO"), 16: ("GTD_LTGTA_89-2_DSEC", "DSEC")}


def test_comparar_conta_iguais_e_lista_divergencias(tmp_path):
    real = tmp_path / "real.xlsx"; nosso = tmp_path / "nosso.xlsx"
    _tdt_fake(real, [("GTD_AL13_52-13_CCMO", 100), ("GTD_LTGTA_52-1_BBFC", 7)])
    _tdt_fake(nosso, [("GTD_AL13_52-13_CCMO", 100), ("GTD_LTGTA_52-1_LIGAR", 7)])
    r = comparar(str(nosso), str(real))
    assert r.comum == 2
    assert r.iguais == 1
    assert r.pct == pytest.approx(50.0)
    assert (7, "BBFC", "LIGAR", "GTD_LTGTA_52-1_BBFC") in r.divergencias
