from composer import base_ansi, enriquecer_ansi, enriquecer


def test_base_ansi_extrai_codigo():
    assert base_ansi("50 - SOBRECORRENTE INSTANTANEA NEUTRO") == 50
    assert base_ansi("50F2 - ...") == 50
    assert base_ansi("CORRENTE NEUTRO") is None
    assert base_ansi("20C 20T 63T - ALARME VALVULA OU BUCHHOLZ") == 20  # 1º código embutido


def test_enriquecer_ansi_append_only_e_funcao():
    v1 = "50 - SOBRECORRENTE INSTANTANEA NEUTRO"
    out, conflito = enriquecer_ansi(v1, 50)
    assert out.startswith(v1)            # append-only
    assert "ANSI 50" in out
    assert "INSTANT" in out.upper()
    assert conflito is None
    assert len(out) > len(v1)            # acrescentou algo


def test_enriquecer_ansi_conflito_nao_acrescenta_funcao():
    v1 = "61 - DESEQUILIBRIO TEMPORIZADO"
    out, conflito = enriquecer_ansi(v1, 61)
    assert out.startswith(v1)
    assert conflito == 61                 # flagado
    # não acrescenta texto contraditório (densidade); no máximo a referência neutra
    assert "DENSIDADE" not in out.upper()


def test_dispatch_preserva_nao_ansi_nesta_task():
    v1 = "CORRENTE NEUTRO"
    out, conflito = enriquecer(v1, "AnalogSignals")
    assert out == v1                      # ainda não tratado (Task 3)
    assert conflito is None
