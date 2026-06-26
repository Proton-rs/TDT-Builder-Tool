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


def test_ajuste_family_append():
    v1 = "AJUSTE PARA AL15"
    out, c = enriquecer(v1, "DiscreteSignals")
    assert out.startswith(v1)
    assert "PARAMETR" in out.upper() or "SETTING" in out.upper()
    assert "AL15" in out


def test_composto_expande_codigos_embutidos():
    v1 = "20C 20T 63T - ALARME VALVULA OU BUCHHOLZ"
    out, c = enriquecer(v1, "DiscreteSignals")
    assert out.startswith(v1)
    # acrescenta a expansão de pelo menos um código embutido
    assert "VÁLVULA" in out.upper() or "VALVULA" in out.upper() or "PRESS" in out.upper()


def test_analogico_grandeza_unidade():
    out, c = enriquecer("CORRENTE NEUTRO", "AnalogSignals")
    assert out.startswith("CORRENTE NEUTRO")
    assert ", A" in out.upper()  # unidade real (Amperagem), não só sinônimo


def test_composto_nao_escaneia_corpo_apos_separador():
    # "90" aparece no corpo (BARRA 90), não no cabeçalho de códigos -> não é composto
    v1 = "27 - SUBTENSAO BARRA 90"
    out, c = enriquecer(v1, "DiscreteSignals")
    assert out.startswith(v1)
    assert "ANSI 27" in out
    assert "ANSI 90" not in out


def test_dispatch_preserva_nao_ansi_nesta_task():
    v1 = "PROPRIEDADE DO COMANDO"
    out, conflito = enriquecer(v1, "DiscreteSignals")
    assert out.startswith(v1)              # append-only, cai na cauda inalterado
    assert conflito is None
