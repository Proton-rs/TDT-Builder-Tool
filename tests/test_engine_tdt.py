import re
from datetime import date

import openpyxl

from tdt.contracts import (
    Descricoes,
    Enderecamento,
    ListaHomogenea,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.engine_tdt import (
    gerar,
    salvar,
    _nome_hierarquico,
    _expandir_range_row5,
    _eh_alimentador,
    _aor_group,
    _remote_unit,
    _device_mapping,
    _normal_value,
    _alias_hoje,
    _coords_comando,
    _adicionar_dv_lista,
    _measurement_type,
)


def test_adicionar_dv_lista_cria_data_validation_nas_colunas_esperadas():
    wb = openpyxl.Workbook()
    ws = wb.active
    colunas = {"Phases": 1, "Direction": 2, "Remote Point Type": 3, "Outra": 4}
    _adicionar_dv_lista(ws, colunas, ultima_linha=10)
    dvs = list(ws.data_validations.dataValidation)
    assert len(dvs) == 3
    alvos = {str(dv.sqref) for dv in dvs}
    assert any("A5:A10" in a for a in alvos)
    formulas = {dv.formula1 for dv in dvs}
    assert any("Read" in f and "Write" in f for f in formulas)


def test_coords_comando_duplica_indice_unico():
    assert _coords_comando((1500,)) == "1500;1500"


def test_coords_comando_preserva_multiplos_indices():
    assert _coords_comando((1500, 1501)) == "1500;1501"


def _rec(rid, sigla, indices, direcao="Input", double=False, fase="ABC"):
    return SignalRecord(
        id=rid,
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", double, direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(f"{sigla} BRUTO", sigla),
        sigla_sinal=sigla,
        status="decidido",
    )


def _lista():
    return ListaHomogenea(
        subestacao="IMA",
        protocolo="DNP3",
        registros=(
            _rec("LT3:1", "DJ", [17], direcao="Input"),
            _rec("LT3:2", "SECC", [100, 101], double=True),
        ),
    )


def test_preserva_43_colunas_e_tabela(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    out = tmp_path / "tdt.xlsx"
    salvar(wb, out)
    rb = openpyxl.load_workbook(out)
    ws = rb["DNP3_DiscreteSignals"]
    assert ws.max_column == 43
    # field names (row 3) e display (row 4) preservados
    assert ws.cell(3, 1).value == "IDOBJ_NAME"
    assert ws.cell(4, 1).value == "Signal Name"
    # ListObject preservado
    assert "DNP3_DiscreteSignals" in ws.tables


def test_escreve_registro_single_bit(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    # primeira linha de dados = row 5
    # hierarchical: subestacao + modulo.nome("3") + módulo repetido (sem equip) + sigla
    assert ws.cell(5, col["Signal Name"]).value == "IMA_3_3_DJ"
    assert ws.cell(5, col["Input Data Type"]).value == "SingleBit"
    assert ws.cell(5, col["Input Coordinates"]).value == "17"
    assert ws.cell(5, col["Direction"]).value == "Read"


def test_readwrite_escreve_output_coords(template_dnp3_path, lista_padrao_path, tmp_path):
    from dataclasses import replace

    base = _rec("LT3:1", "DJ", [5], direcao="InputOutput")
    rw = replace(base, enderecamento=replace(base.enderecamento, indices_saida=(0,)))
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(rw,))
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    ws = gerar(lista, template_dnp3_path, lp)["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(5, col["Direction"]).value == "ReadWrite"
    assert ws.cell(5, col["Output Coordinates"]).value == "0;0"  # comando simples duplica o indice
    assert ws.cell(5, col["Output Data Type"]).value == "SingleBit"


def test_output_orfao_escreve_output_coords_nao_input(template_dnp3_path, lista_padrao_path, tmp_path):
    """Comando Output sem par (órfão): endereço próprio vai para Output Coordinates,
    não para Input Coordinates (sinal não tem leitura, só escrita)."""
    cmd = _rec("LT3:3", "ABRIR", [42], direcao="Output")
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(cmd,))
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    ws = gerar(lista, template_dnp3_path, lp)["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(5, col["Direction"]).value == "Write"
    assert ws.cell(5, col["Output Coordinates"]).value == "42;42"  # comando simples duplica o indice
    assert ws.cell(5, col["Input Coordinates"]).value is None


def test_output_orfao_multiplos_indices_nao_duplica(template_dnp3_path, lista_padrao_path, tmp_path):
    cmd = _rec("LT3:4", "ABRIR2", [42, 43], direcao="Output")
    lista = ListaHomogenea(subestacao="IMA", protocolo="DNP3", registros=(cmd,))
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    ws = gerar(lista, template_dnp3_path, lp)["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(5, col["Output Coordinates"]).value == "42;43"


def test_double_bit_preserva_dois_indices(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(6, col["Input Data Type"]).value == "DoubleBit"
    assert ws.cell(6, col["Input Coordinates"]).value == "100;101"


# ── Tarefa 1: table ref ──────────────────────────────────────────────────────

def test_table_ref_comeca_em_a4(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    ref = ws.tables["DNP3_DiscreteSignals"].ref
    assert ref.startswith("A4:"), f"Esperado A4:..., obteve {ref}"
    assert ref.endswith("6"), f"Esperado A4:AQ6, obteve {ref}"
    assert ref == "A4:AQ6", f"ref inesperado: {ref}"


# ── Tarefa 2: conditional formatting ─────────────────────────────────────────

def test_cf_expandido_para_todas_linhas(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    ranges = [str(cf.sqref) for cf in ws.conditional_formatting]
    assert len(ranges) == 13
    for r in ranges:
        assert "6" in r, f"CF range {r} não cobre row 6"
        assert r.endswith("6"), f"CF range {r} não termina em 6"


# ── Tarefa 3: data validations ──────────────────────────────────────────────

def test_dv_expandido_para_todas_linhas(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    sqrefs = [str(dv.sqref) for dv in ws.data_validations.dataValidation]
    assert len(sqrefs) == 7  # 4 numericas pre-existentes + 3 de lista (Phases/Direction/Remote Point Type)
    for sq in sqrefs:
        assert "6" in sq, f"DV sqref {sq} não cobre row 6"
    # AP5:AQ5 → AP5:AQ6
    assert any(sq == "AP5:AQ6" for sq in sqrefs), f"Nenhum DV com AP5:AQ6: {sqrefs}"


# ── Tarefa 4: nome hierárquico ──────────────────────────────────────────────

def test_nome_hierarquico_4_partes():
    nome = _nome_hierarquico("GTA", "AL 11", "52-22", None, "43TC")
    assert nome == "GTA_AL11_52-22_43TC"


def test_nome_hierarquico_2_partes_fallback():
    nome = _nome_hierarquico("GTA", None, None, None, "BATA")
    assert nome == "GTA_BATA"


def test_nome_hierarquico_sem_subestacao():
    nome = _nome_hierarquico(None, "LT 1", "52-10", None, "DJ")
    assert nome == "LT1_52-10_DJ"


def test_nome_hierarquico_sigla_only():
    nome = _nome_hierarquico(None, None, None, None, "BATA")
    assert nome == "BATA"


def test_nome_hierarquico_modulo_sem_equip():
    # sem equipamento: repete o módulo
    nome = _nome_hierarquico("SE", "TR 1", None, None, "FA")
    assert nome == "SE_TR1_TR1_FA"


def test_nome_hierarquico_barra_principal_auxiliar():
    nome_p = _nome_hierarquico("GTA", "LT 1", "52-10", "Principal", "DJ")
    assert nome_p == "GTA_LT1_52-10_P_DJ"
    nome_a = _nome_hierarquico("GTA", "LT 1", "52-10", "Auxiliar", "DJ")
    assert nome_a == "GTA_LT1_52-10_A_DJ"


def test_signal_name_hierarquico_no_output(template_dnp3_path, lista_padrao_path, tmp_path):
    """Verifica que o Signal Name no output segue o formato hierárquico."""
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    # _lista() tem subestacao="IMA", modulo.nome="3", sem equipamento -> repete módulo
    assert ws.cell(5, col["Signal Name"]).value == "IMA_3_3_DJ"
    assert ws.cell(6, col["Signal Name"]).value == "IMA_3_3_SECC"


# ── _expandir_range_row5 ────────────────────────────────────────────────────

def test_expandir_range_single():
    assert _expandir_range_row5("A5", 10) == "A5:A10"


def test_expandir_range_range():
    assert _expandir_range_row5("AP5:AQ5", 10) == "AP5:AQ10"


def test_expandir_range_nao_row5():
    assert _expandir_range_row5("A1", 10) == "A1"  # sem mudança


# ── Tarefa 3: campos derivados ──────────────────────────────────────────────

def test_eh_alimentador():
    assert _eh_alimentador("AL11") is True
    assert _eh_alimentador("AL 12") is True
    assert _eh_alimentador("3") is False
    assert _eh_alimentador("TR1") is False
    assert _eh_alimentador(None) is False


def test_aor_group():
    assert _aor_group("IMA", True) == "IMA Distr"
    assert _aor_group("IMA", False) == "IMA Trans"
    assert _aor_group(None, True) is None


def test_remote_unit():
    assert _remote_unit("IMA") == "UTR_IMA_1"
    assert _remote_unit(None) is None


def test_device_mapping():
    assert _device_mapping("IMA_3_20T", "20T", True) == "IMA_3_PROT_20T"
    assert _device_mapping("IMA_3_DJ", "DJ", False) == "IMA_3_DJ"
    assert _device_mapping("BATA", "BATA", True) == "PROT_BATA"


def test_normal_value():
    sp = SinalPadrao("20T", "", "RelayTrip", None, None, "Discrete",
                     estados_brutos="Transit;NORMAL;ATUADO;Error",
                     valores_scada=(0, 1, 2, 3))
    assert _normal_value(sp) == 1
    assert _normal_value(None) is None
    sp_sem = SinalPadrao("X", "", "Custom", None, None, "Discrete")
    assert _normal_value(sp_sem) is None


def test_alias_hoje_formato_eua_sem_barras():
    assert re.fullmatch(r"\d{8}", _alias_hoje())
    assert _alias_hoje() == date.today().strftime("%m%d%Y")


def _rec_analog(rid, sigla, indices):
    return SignalRecord(
        id=rid,
        modulo=Modulo("AL11", "sheet_name"),
        tipo_sinal=TipoSinal("Analog", False, "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(f"{sigla} BRUTO", sigla),
        sigla_sinal=sigla,
        status="decidido",
    )


def _lista_analog():
    return ListaHomogenea(
        subestacao="IMA", protocolo="DNP3",
        registros=(_rec_analog("A:1", "IN61", [20]),),
    )


def test_measurement_type_traduz_pt_para_en():
    sp = SinalPadrao(sigla="IA", descricao="", signal_type="Current", direction=None,
                      mm=None, categoria="Analog", tipo_medicao="Corrente", unidade_exibicao="A")
    assert _measurement_type(sp) == "Current"


def test_measurement_type_none_sem_tipo_medicao():
    sp = SinalPadrao(sigla="IA", descricao="", signal_type="Current", direction=None,
                      mm=None, categoria="Analog")
    assert _measurement_type(sp) is None


def test_escreve_sheet_analogica(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista_analog(), template_dnp3_path, lp)
    ws = wb["DNP3_AnalogSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    assert ws.cell(5, col["Signal Name"]).value == "IMA_AL11_AL11_IN61"
    assert ws.cell(5, col["Input Coordinates"]).value == "20"
    assert ws.cell(5, col["Direction"]).value == "Read"
    assert ws.cell(5, col["Remote Point Type"]).value == "Analog"
    assert ws.cell(5, col["Side"]).value == "None"
    assert ws.cell(5, col["Signal AOR Group"]).value == "IMA Distr"  # AL11 = alimentador
    assert ws.cell(5, col["Remote Point Name"]).value == "IMA_AL11_AL11_IN61"
    # IN61 = "Corrente"/"A" na Lista Padrao -> Measurement Type/Display Unit
    assert ws.cell(5, col["Measurement Type"]).value == "Current"
    assert ws.cell(5, col["Display Unit"]).value == "A"
    # table ref começa em A4
    assert ws.tables["DNP3_AnalogSignals"].ref.startswith("A4:")


def test_discreto_intacto_com_analog(template_dnp3_path, lista_padrao_path, tmp_path):
    """Gerar com registros das duas categorias preenche as duas sheets."""
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    lista = ListaHomogenea(
        subestacao="IMA", protocolo="DNP3",
        registros=_lista().registros + _lista_analog().registros,
    )
    wb = gerar(lista, template_dnp3_path, lp)
    wsd = wb["DNP3_DiscreteSignals"]
    wsa = wb["DNP3_AnalogSignals"]
    cold = {wsd.cell(4, c).value: c for c in range(1, wsd.max_column + 1)}
    cola = {wsa.cell(4, c).value: c for c in range(1, wsa.max_column + 1)}
    assert wsd.cell(5, cold["Signal Name"]).value == "IMA_3_3_DJ"
    assert wsa.cell(5, cola["Signal Name"]).value == "IMA_AL11_AL11_IN61"


def test_campos_novos_no_output(template_dnp3_path, lista_padrao_path, tmp_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    wb = gerar(_lista(), template_dnp3_path, lp)
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    # row 5 = "IMA_3_3_DJ" (modulo "3" não é alimentador -> Trans, sem equip repete módulo)
    assert ws.cell(5, col["Side"]).value == "None"
    assert ws.cell(5, col["Output Register"]).value is False
    assert ws.cell(5, col["Remote Point Type"]).value == "Status"
    assert ws.cell(5, col["Remote Point Name"]).value == "IMA_3_3_DJ"
    assert ws.cell(5, col["Signal AOR Group"]).value == "IMA Trans"
    assert ws.cell(5, col["Device Mapping"]).value == "IMA_3_3_DJ"
    assert ws.cell(5, col["Remote Unit"]).value == "UTR_IMA_1"
    assert ws.cell(5, col["Remote Point Custom ID"]).value == "IMA_3_3_DJ_UTR_IMA_1"
    import re as _re
    assert _re.fullmatch(r"\d{8}", ws.cell(5, col["Remote Point Alias"]).value)
