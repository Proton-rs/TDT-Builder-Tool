from tdt.vocabulario_tipo import classificar


def test_classifica_palavra_completa_analogica():
    assert classificar("Analógicas Módulo AT") == ("Analog", "Input")


def test_classifica_palavra_completa_comando():
    assert classificar("Comandos Módulo AT") == ("Discrete", "Output")


def test_classifica_palavra_completa_digital():
    assert classificar("Digitais (Status)") == ("Discrete", "Input")


def test_classifica_codigo_curto_exato():
    assert classificar("A") == ("Analog", "Input")
    assert classificar("C") == ("Discrete", "Output")
    assert classificar("D") == ("Discrete", "Input")


def test_codigo_curto_nao_casa_por_substring():
    # "DISJUNTOR" não é o código "D" — igualdade exata, não substring
    assert classificar("DISJUNTOR") is None


def test_texto_sem_pista_retorna_none():
    assert classificar("ALARME GENERICO") is None
