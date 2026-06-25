from tdt.config import Config
from tdt.contracts import MapaColunas
from tdt.estruturador import estruturar

CFG = Config()

ROWS = [
    ("", "", "SUBESTAÇÃO RGE", "", ""),
    ("IED", "Módulo", "Descrição do Ponto", "Tipo", "Endereço DNP3"),
    ("Analógicas", "", "", "", ""),
    ("01F1", "LT_GTA", "Corrente Fase A", "Analógico", "0"),
    ("01F1", "LT_GTA", "Corrente Fase B", "Analógico", "1"),
    ("Controle", "", "", "", ""),  # sinônimo de "Comandos"
    ("01F1", "LT_GTA", "Disjuntor 52-1 Comando", "Comando D", "0"),
    ("Digitais", "", "", "", ""),
    ("01F1", "LT_GTA", "Disjuntor 52-1 Estado", "Digital", "5"),
    ("", "", "", "", ""),  # linha vazia ignorada
]
# header na row 2 (1-based); descricao=2, tipo=3, indice=4
MAPA = MapaColunas(header_row=2, colunas={"descricao": 2, "tipo": 3, "indice": 4})


def _estruturar():
    return estruturar(ROWS, MAPA, sheet_name="01F1_GTA", config=CFG, modulo="LT_GTA")


def test_ignora_metadados_marcadores_e_vazias():
    recs = _estruturar()
    # 2 analógicos + 1 comando + 1 digital = 4
    assert len(recs) == 4


def test_secao_analogica_define_categoria():
    recs = _estruturar()
    assert recs[0].tipo_sinal.categoria == "Analog"
    assert recs[0].descricoes.bruta == "Corrente Fase A"
    assert recs[0].descricoes.normalizada  # normalizada preenchida


def test_secao_controle_sinonimo_vira_comando_output():
    recs = _estruturar()
    cmd = [r for r in recs if "COMANDO" in r.descricoes.bruta.upper()][0]
    assert cmd.tipo_sinal.categoria == "Discrete"
    assert cmd.tipo_sinal.direcao == "Output"


def test_secao_digital_vira_discreto_input():
    recs = _estruturar()
    est = [r for r in recs if "ESTADO" in r.descricoes.bruta.upper()][0]
    assert est.tipo_sinal.categoria == "Discrete"
    assert est.tipo_sinal.direcao == "Input"


def test_parseia_indice_e_modulo():
    recs = _estruturar()
    assert recs[0].enderecamento.indices == (0,)
    assert recs[0].modulo.nome == "LT_GTA"
    assert recs[0].id == "01F1_GTA:4"  # row 4 (1-based) é o 1º dado


def test_categoria_incerta_sem_pista():
    # header na row 1; uma linha de dados sem marcador de seção e sem coluna Tipo
    rows = [
        ("Descrição", "Endereço"),
        ("ALARME GENERICO", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert len(recs) == 1
    assert recs[0].tipo_sinal.categoria_confiavel is False


def test_categoria_confiavel_com_marcador():
    rows = [
        ("Descrição", "Endereço"),
        ("Analógicas", ""),          # marcador de seção -> categoria confiável
        ("CORRENTE FASE A", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].tipo_sinal.categoria == "Analog"
    assert recs[0].tipo_sinal.categoria_confiavel is True


def test_eletrico_populado_a_partir_da_descricao():
    rows = [
        ("Descrição", "Endereço"),
        ("Disjuntor 52-1 Fase A Barra P Aberto", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].eletrico.equipamento_alvo == "Disjuntor"
    assert recs[0].eletrico.fase == "A"
    assert recs[0].eletrico.barra == "Principal"
    assert "52" not in recs[0].descricoes.normalizada.split()


def test_coluna_tipo_codigo_curto_classifica_linha_a_linha():
    rows = [
        ("Descrição", "Tipo", "Endereço"),
        ("Corrente Fase A", "A", "10"),
        ("Disjuntor 52-1 Comando", "C", "11"),
        ("Disjuntor 52-1 Estado", "D", "12"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "tipo": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].tipo_sinal.categoria == "Analog"
    assert recs[0].tipo_sinal.categoria_confiavel is True
    assert recs[1].tipo_sinal.categoria == "Discrete"
    assert recs[1].tipo_sinal.direcao == "Output"
    assert recs[2].tipo_sinal.categoria == "Discrete"
    assert recs[2].tipo_sinal.direcao == "Input"
