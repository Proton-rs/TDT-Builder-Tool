from tdt.tokenizer import tokenizar


def test_junta_sigla_separada():
    assert tokenizar("67 N") == ["67N"]


def test_junta_sigla_com_estagio():
    assert tokenizar("67 N 1") == ["67N1"]


def test_junta_50bf():
    assert tokenizar("50 BF") == ["50BF"]


def test_nao_junta_texto_normal():
    assert tokenizar("DJF1 ABERTO") == ["DJF1", "ABERTO"]


def test_nao_junta_numeros_de_equipamento():
    # "52 3" são dois números (52-3 vira "52 3" na normalização): não fundir
    assert tokenizar("52 3") == ["52", "3"]


def test_vazio():
    assert tokenizar("") == []
