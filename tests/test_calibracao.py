import math

from tdt.scoring.calibracao import calibrar


def test_minmax_espalha_para_0_1():
    out = calibrar([0.80, 0.85, 0.90], "minmax", None)
    assert out[0] == 0.0
    assert out[2] == 1.0
    assert abs(out[1] - 0.5) < 1e-6


def test_minmax_lista_constante_nao_divide_por_zero():
    out = calibrar([0.8, 0.8, 0.8], "minmax", None)
    assert all(v == 0.0 for v in out)


def test_minmax_lista_vazia():
    assert calibrar([], "minmax", None) == []


def test_minmax_um_elemento():
    assert calibrar([0.87], "minmax", None) == [0.0]


def test_temperature_aumenta_spread():
    # e5 comprimido em ~0.8-0.9; temperature scaling alarga a separação relativa
    bruto = [0.80, 0.85, 0.90]
    spread_bruto = max(bruto) - min(bruto)
    out = calibrar(bruto, "temperature", {"T": 0.1})
    spread_out = max(out) - min(out)
    assert spread_out > spread_bruto
    # mantém ordem
    assert out == sorted(out)


def test_temperature_default_params():
    # params None -> usa T default; não explode
    out = calibrar([0.80, 0.85, 0.90], "temperature", None)
    assert len(out) == 3
    assert out == sorted(out)


def test_e5_comprimido_passa_a_ter_gap_apos_minmax():
    # critério da spec: e5 sozinho decide 0% porque scores comprimidos -> gap~0.
    # após calibrar, o top-1 ganha separação suficiente para o gap virar > 0.
    e5 = [0.91, 0.89, 0.88]
    gap_bruto = e5[0] - e5[1]
    cal = calibrar(e5, "minmax", None)
    gap_cal = cal[0] - cal[1]
    assert gap_cal > gap_bruto
    assert gap_cal > 0.0


def test_metodo_desconhecido_levanta():
    try:
        calibrar([0.1, 0.2], "inexistente", None)
        assert False, "deveria levantar"
    except ValueError:
        pass
