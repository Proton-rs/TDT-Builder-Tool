from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT, DEFAULT_TEMPLATE


def test_defaults_apontam_pra_pastas_do_projeto():
    assert DEFAULT_TEMPLATE.endswith("dnp3_template.xlsx")
    assert DEFAULT_LISTA.endswith("Pontos Padrao ADMS_v7.xlsx")
    assert DEFAULT_OUTPUT.endswith("output")
