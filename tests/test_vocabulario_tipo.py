from tdt.normalizacao.vocabulario_tipo import classificar


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


def test_classifica_termos_de_comando_reais_gtd_v11():
    """D1 (spec SP-Direção): valores literais da coluna 'Tipo' e dos
    marcadores de seção observados em `docs/GTD - Lista de Pontos V11.xlsx`
    (38 sheets varridas via `analise_colunas.analisar` real). Trava o
    comportamento já correto — nenhuma extensão de vocabulário foi necessária.
    """
    assert classificar("Comando D") == ("Discrete", "Output")
    assert classificar("Comando S") == ("Discrete", "Output")
    assert classificar("Comandos") == ("Discrete", "Output")
    assert classificar("Comandos Módulos AT") == ("Discrete", "Output")
    assert classificar("Digitais (Controle)") == ("Discrete", "Output")
    assert classificar("Digital Simples") == ("Discrete", "Input")


def test_classifica_codigos_curtos_reais_fredw_v13():
    """D1: a coluna 'Tipo' de `docs/Lista de Pontos FredW V13 - DNP3.xlsx`
    usa exclusivamente os códigos de 1 letra A/C/D (1019xD, 249xA, 226xC nas
    sheets reais) — já cobertos por `CODIGOS_TIPO`."""
    assert classificar("A") == ("Analog", "Input")
    assert classificar("C") == ("Discrete", "Output")
    assert classificar("D") == ("Discrete", "Input")
