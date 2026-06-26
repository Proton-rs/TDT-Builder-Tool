from tdt.contracts import Modulo, TIPOS_MODULO


def test_modulo_tem_campo_tipo_default_none():
    m = Modulo("AL15", "sheet_name")
    assert m.tipo is None
    m2 = Modulo("AL15", "sheet_name", tipo="Alimentador")
    assert m2.tipo == "Alimentador"


def test_tipos_modulo_tem_nove_categorias():
    assert "Alimentador" in TIPOS_MODULO
    assert "Outros" in TIPOS_MODULO
    assert len(TIPOS_MODULO) == 9
