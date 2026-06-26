from ansi_ref import ANSI_C37_2, SINONIMOS_ANSI, CONFLITO_V1, CODIGOS_PRESENTES


def test_cobre_os_26_codigos_presentes():
    presentes = {20, 21, 24, 25, 26, 27, 32, 43, 46, 49, 50, 51, 59, 61,
                 62, 63, 67, 71, 78, 79, 81, 85, 86, 87, 90, 94}
    assert CODIGOS_PRESENTES == presentes
    # todo código presente tem função, exceto os explicitamente em conflito
    for c in presentes:
        assert c in ANSI_C37_2 or c in CONFLITO_V1


def test_ancoras_corretas_anti_v3():
    # os erros que a v3 cometeu — aqui têm que estar certos
    assert "VOLTS" in ANSI_C37_2[24].upper()        # 24 = Volts/Hz (v3 errou p/ sobrecorrente)
    assert "VÁLVULA" in ANSI_C37_2[20].upper() or "VALVULA" in ANSI_C37_2[20].upper()  # 20 = válvula (v3 errou p/ diferencial)
    assert "INSTANT" in ANSI_C37_2[50].upper()      # 50 instantânea
    assert "INVERSO" in ANSI_C37_2[51].upper() or "TEMPO" in ANSI_C37_2[51].upper()
    assert "SUBTENS" in ANSI_C37_2[27].upper()
    assert "SOBRETENS" in ANSI_C37_2[59].upper()
    assert "DIFERENCIAL" in ANSI_C37_2[87].upper()
    assert "FREQU" in ANSI_C37_2[81].upper()


def test_61_marcado_como_conflito_v1():
    # C37.2 define 61 como chave/sensor de densidade, mas a v1 usa "desequilíbrio".
    # Não inventar: 61 vai pro sidecar, não recebe função contraditória.
    assert 61 in CONFLITO_V1
    assert 61 not in ANSI_C37_2
