from tdt.config import Config
from tdt.contracts import MapaColunas
from tdt.normalizacao.estruturador import _eh_marcador, _grandeza_continua, estruturar

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


def test_grandeza_continua_sem_coluna_tipo_infere_analog():
    # CVA11: sem coluna TIPO, sem marcador de seção, descrição indica
    # grandeza elétrica contínua (tensão) -> Analog/Input, nunca Discrete.
    rows = [
        ("Descrição", "Endereço"),
        ("Tensão Barra AB", "10"),
        ("Tensão Barra BC", "11"),
        ("Tensão Barra CA", "12"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="CVA11", config=Config())
    assert len(recs) == 3
    for r in recs:
        assert r.tipo_sinal.categoria == "Analog"
        assert r.tipo_sinal.direcao == "Input"
        assert r.tipo_sinal.categoria_confiavel is True


def test_grandeza_continua_por_token_exato():
    """SP-CVA2 E3.3: 'POTENCIAL' não é 'POTENCIA'; 'SUBTENSAO' não é 'TENSAO'."""
    assert _grandeza_continua("Falta de Potencial") is None
    assert _grandeza_continua("Proteção Subtensão (27) - Excluida") is None
    assert _grandeza_continua("Tensão Barra AB") == ("Analog", "Input")
    assert _grandeza_continua("Potência Reativa") == ("Analog", "Input")
    assert _grandeza_continua("Corrente de Desbalanço (IBX)") == ("Analog", "Input")


def test_grandeza_continua_guarda_falta_perda():
    assert _grandeza_continua("Falta Tensão Comando") is None
    assert _grandeza_continua("Perda de Corrente TC") is None


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


def test_marcador_em_coluna_d_nao_vira_sinal_fantasma():
    """GAU: marcadores MEDIÇÃO/CONTROLE/SINALIZAÇÃO na coluna D (descrição).
    Antes viravam sinais fantasmas porque _eh_marcador só olhava col 0."""
    rows = [
        ("MODULO", "IED", "TIPO", "DESCRICAO DO PONTO", "INDEX"),
        ("", "", "", "MEDIÇÃO", ""),
        ("AL21", "UPC1", "A", "Corrente Fase A", "40"),
        ("AL21", "UPC1", "A", "Corrente Fase B", "41"),
        ("", "", "", "CONTROLE", ""),
        ("AL21", "UPC1", "C", "Disj. 52-21 Abrir/Fechar", "30"),
        ("", "", "", "SINALIZAÇÃO", ""),
        ("AL21", "UPC1", "D", "Disj. 52-21 Desligado", "130"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 3, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="AL21", config=Config())
    assert len(recs) == 4
    assert recs[0].descricoes.bruta == "Corrente Fase A"
    assert recs[0].tipo_sinal.categoria == "Analog"
    assert recs[1].descricoes.bruta == "Corrente Fase B"
    assert recs[1].tipo_sinal.categoria == "Analog"
    assert recs[2].descricoes.bruta == "Disj. 52-21 Abrir/Fechar"
    assert recs[2].tipo_sinal.categoria == "Discrete"
    assert recs[2].tipo_sinal.direcao == "Output"
    assert recs[3].descricoes.bruta == "Disj. 52-21 Desligado"
    assert recs[3].tipo_sinal.categoria == "Discrete"
    assert recs[3].tipo_sinal.direcao == "Input"


# --- coluna de sigla (lista não-homogênea com sigla pronta) -----------------

_SIGLAS_LP = frozenset({"79", "IA"})


def test_sem_coluna_sigla_comportamento_atual():
    rows = [
        ("SIGLA", "NOME", "TIPO", "IDX"),
        ("79", "SND_LT67SAN_LT67SAN_79", "Digital", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="LT67SAN", config=Config())
    assert len(recs) == 1
    assert recs[0].status == "pendente"
    assert recs[0].sigla_sinal is None


def test_sigla_valida_e_nome_consistente_pre_classifica():
    rows = [
        ("SIGLA", "NOME", "TIPO", "IDX"),
        ("79", "SND_LT67SAN_LT67SAN_79", "Digital", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"sigla": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="LT67SAN", config=Config(), siglas_set=_SIGLAS_LP)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.status == "decidido"
    assert rec.sigla_sinal == "79"
    assert rec.modulo.nome == "LT67SAN"
    assert rec.modulo.origem_contexto == "coluna:SIGLA"


def test_sigla_pre_classificada_popula_nome_equipamento_do_nome():
    # mesma sigla/módulo, instâncias de equipamento DIFERENTES (3º token do
    # NOME) -- sem isso, normalizador_estrutural._chave (modulo,
    # nome_equipamento, sigla) trata como duplicata de endereço e descarta
    # 3 dos 4 sinais (achado real na integração com SAN2).
    rows = [
        ("SIGLA", "NOME", "TIPO", "IDX"),
        ("DR", "SND_SLOTD_SLOTD_DR", "Digital", "69"),
        ("DR", "SND_SLOTD_SLOTD-2_DR", "Digital", "161"),
    ]
    siglas = frozenset({"DR"})
    mapa = MapaColunas(header_row=1, colunas={"sigla": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="SLOTD", config=Config(), siglas_set=siglas)
    assert len(recs) == 2
    assert recs[0].eletrico.nome_equipamento == "SLOTD"
    assert recs[1].eletrico.nome_equipamento == "SLOTD-2"


def test_sigla_valida_mas_nome_inconsistente_vai_pra_revisao():
    rows = [
        ("SIGLA", "NOME", "TIPO", "IDX"),
        ("79", "SND_LT67SAN_LT67SAN_80", "Digital", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"sigla": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="LT67SAN", config=Config(), siglas_set=_SIGLAS_LP)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.status == "revisao"
    assert rec.justificativa == "nome_sigla_inconsistente"


def test_sigla_valida_sem_coluna_descricao_pre_classifica_pelo_modulo_da_sheet():
    # lista só com sigla (Caso de Uso #3) -- sem coluna "descricao" detectada
    rows = [
        ("SIGLA", "IDX"),
        ("79", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"sigla": 0, "indice": 1})
    recs = estruturar(rows, mapa, sheet_name="LT67SAN", config=Config(), siglas_set=_SIGLAS_LP)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.status == "decidido"
    assert rec.sigla_sinal == "79"
    assert rec.modulo.nome == "LT67SAN"  # módulo da sheet, sem NOME pra extrair


def test_sigla_invalida_recai_no_scoring():
    rows = [
        ("SIGLA", "NOME", "TIPO", "IDX"),
        ("INVENTADO", "SND_LT67SAN_INVENTADO", "Digital", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"sigla": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="LT67SAN", config=Config(), siglas_set=_SIGLAS_LP)
    assert len(recs) == 1
    rec = recs[0]
    assert rec.status == "pendente"
    assert rec.sigla_sinal is None


def test_sigla_de_entrada_normalizada_por_de_para():
    rows = [
        ("SIGLA", "NOME", "TIPO", "IDX"),
        ("90", "SND_LT67SAN_LT67SAN_R90", "Digital", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"sigla": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="LT67SAN", config=Config(),
                       siglas_set=frozenset({"R90"}), de_para={"90": "R90"})
    assert len(recs) == 1
    rec = recs[0]
    assert rec.sigla_sinal == "R90"
    assert rec.status == "decidido"


def test_sigla_fora_do_de_para_comportamento_inalterado():
    rows = [
        ("SIGLA", "NOME", "TIPO", "IDX"),
        ("79", "SND_LT67SAN_LT67SAN_79", "Digital", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"sigla": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="LT67SAN", config=Config(),
                       siglas_set=_SIGLAS_LP, de_para={"90": "R90"})
    assert len(recs) == 1
    rec = recs[0]
    assert rec.sigla_sinal == "79"
    assert rec.status == "decidido"


# --- datatype (DoubleBit nativo) + comando_duplo (SP-E / Task 3) -----------


def _estruturar_rows(rows):
    mapa = MapaColunas(header_row=1, colunas={"descricao": 0, "indice": 1, "tipo": 2})
    return estruturar(rows, mapa, sheet_name="S1", config=Config())


def test_input_com_endereco_duplo_nativo_vira_doublebit():
    rows = [("desc", "idx", "tipo"),
            ("Secc. 89-16 Aberta/Fechada", "1100;1101", "D")]
    regs = _estruturar_rows(rows)
    assert regs[0].tipo_sinal.datatype == "DoubleBit"


def test_comando_nn_continua_singlebit():
    rows = [("desc", "idx", "tipo"),
            ("CMD Secc. 89-16", "3;3", "C")]
    regs = _estruturar_rows(rows)
    assert regs[0].tipo_sinal.datatype == "SingleBit"
    assert regs[0].tipo_sinal.comando_duplo is True


def test_comando_s_marca_comando_nao_duplo():
    rows = [("desc", "idx", "tipo"),
            ("CMD RMT.009 81 E1 Habilitar", "1504", "Comando S"),
            ("CMD RMT.002 SGF Excluir/Incluir", "1502", "Comando D")]
    regs = _estruturar_rows(rows)
    assert regs[0].tipo_sinal.direcao == "Output"
    assert regs[0].tipo_sinal.comando_duplo is False
    assert regs[1].tipo_sinal.comando_duplo is True


# --- módulo por linha (coluna MODULO_POR_LINHA, Task 3) -----


def test_estruturar_modulo_por_linha_muda_entre_blocos():
    rows = [
        ("Modulo", "Descricao", "Tipo", "Addr"),
        ("LTSM3C1", "DISJUNTOR ABERTO", "Ponto Simples", "1"),
        ("LTSM3C1", "DISJUNTOR FECHADO", "Ponto Simples", "2"),
        ("TR1", "TEMPERATURA OLEO", "Ponto Simples", "3"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"modulo": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="ESTADOS", config=Config())
    assert [r.modulo.nome for r in recs] == ["LTSM3C1", "LTSM3C1", "TR1"]
    assert all(r.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" for r in recs)


def test_estruturar_modulo_vazio_vai_para_revisao():
    rows = [
        ("Modulo", "Descricao", "Tipo", "Addr"),
        ("TR1", "TEMPERATURA OLEO", "Ponto Simples", "1"),
        ("", "SINAL SEM MODULO", "Ponto Simples", "2"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"modulo": 0, "descricao": 1, "tipo": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="ESTADOS", config=Config())
    assert recs[0].status == "pendente"
    assert recs[1].status == "revisao"
    assert recs[1].justificativa == "modulo_indefinido"
    assert recs[1].modulo.nome is None


def test_modulo_por_linha_nao_engole_coluna_sigla():
    """Regressão LVA AL21 (b9b0118): módulo por coluna e sigla por coluna são
    independentes — sheet com as DUAS colunas precisa aplicar as duas. O
    ``elif`` tornava a resolução mutuamente exclusiva e a sheet inteira
    perdia a pré-classificação por sigla."""
    rows = [
        ("TOPOLOGIA", "DESCRIÇÃO", "TIPO", "MÓDULO", "EQUIP", "SIGLA", "IDX"),
        ("LVA\\AL 21", "P", "A", "AL21", "TC", "P", "10"),
        ("LVA\\AL 21", "Q", "A", "AL22", "TC", "Q", "11"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "descricao": 1, "tipo": 2, "modulo": 3, "sigla": 5, "indice": 6})
    recs = estruturar(rows, mapa, sheet_name="AL21", config=Config(),
                      siglas_set=frozenset({"P", "Q"}))
    assert [r.modulo.nome for r in recs] == ["AL21", "AL22"]
    assert all(r.modulo.origem_contexto == "coluna:MODULO_POR_LINHA" for r in recs)
    assert [r.sigla_sinal for r in recs] == ["P", "Q"]
    assert all(r.status == "decidido" for r in recs)


def test_modulo_vazio_preserva_sigla_da_coluna():
    # módulo indefinido continua mandando pra revisão, mas a sigla lida da
    # coluna não pode ser descartada no caminho
    rows = [
        ("Modulo", "Descricao", "Tipo", "SIGLA", "Addr"),
        ("", "P", "A", "P", "1"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "modulo": 0, "descricao": 1, "tipo": 2, "sigla": 3, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="ESTADOS", config=Config(),
                      siglas_set=frozenset({"P"}))
    assert recs[0].status == "revisao"
    assert recs[0].justificativa == "modulo_indefinido"
    assert recs[0].sigla_sinal == "P"


def test_coluna_modulo_ganha_da_extracao_do_nome():
    # com coluna MODULO explícita, o módulo extraído do NOME não sobrescreve
    rows = [
        ("Modulo", "NOME", "Tipo", "SIGLA", "Addr"),
        ("AL21", "SND_LT67SAN_LT67SAN_79", "Digital", "79", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "modulo": 0, "descricao": 1, "tipo": 2, "sigla": 3, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config(),
                      siglas_set=_SIGLAS_LP)
    rec = recs[0]
    assert rec.status == "decidido"
    assert rec.sigla_sinal == "79"
    assert rec.modulo.nome == "AL21"
    assert rec.modulo.origem_contexto == "coluna:MODULO_POR_LINHA"


# --- independência de identidades (SP-FLUXO-DADOS Task 5, invariante I2) ---
# Cada fonte de identidade presente na linha resolve a SUA identidade;
# nenhuma desliga a outra (módulo×sigla coberto em
# test_modulo_por_linha_nao_engole_coluna_sigla).


def test_sigla_coluna_e_equipamento_na_linha_resolvem_juntos():
    rows = [
        ("DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "SIGLA", "IDX"),
        ("MOLA", "D", "52-11", "MOLA", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "descricao": 0, "tipo": 1, "sigla": 3, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config(),
                      siglas_set=frozenset({"MOLA"}))
    assert recs[0].sigla_sinal == "MOLA"           # coluna SIGLA
    assert recs[0].eletrico.nome_equipamento == "52-11"  # varredura da linha
    assert recs[0].status == "decidido"


def test_modulo_coluna_e_equipamento_na_linha_resolvem_juntos():
    rows = [
        ("MODULO", "DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "IDX"),
        ("AL21", "Disj. aberto", "D", "52-11", "10"),
        ("AL22", "Disj. fechado", "D", "52-12", "11"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "modulo": 0, "descricao": 1, "tipo": 2, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert [r.modulo.nome for r in recs] == ["AL21", "AL22"]
    assert [r.eletrico.nome_equipamento for r in recs] == ["52-11", "52-12"]


def test_modulo_sigla_e_equipamento_simultaneos_resolvem_os_tres():
    """Critério de sucesso da spec: as TRÊS identidades na mesma linha
    (layout LVA AL11/AL21 completo) resolvem juntas."""
    rows = [
        ("MODULO", "DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "SIGLA", "IDX"),
        ("AL21", "MOLA", "D", "52-11", "MOLA", "10"),
        ("AL22", "MOLA", "D", "52-12", "MOLA", "11"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "modulo": 0, "descricao": 1, "tipo": 2, "sigla": 4, "indice": 5})
    recs = estruturar(rows, mapa, sheet_name="AL21", config=Config(),
                      siglas_set=frozenset({"MOLA"}))
    assert [r.modulo.nome for r in recs] == ["AL21", "AL22"]
    assert [r.sigla_sinal for r in recs] == ["MOLA", "MOLA"]
    assert [r.eletrico.nome_equipamento for r in recs] == ["52-11", "52-12"]
    assert [r.status for r in recs] == ["decidido", "decidido"]


def test_coluna_equipamento_dedicada_preenche_sem_afetar_sigla_e_modulo():
    """Task 19 (2F) — coluna EQUIPAMENTO dedicada é identidade INDEPENDENTE
    de sigla/módulo (I2): as três resolvem juntas na mesma linha."""
    rows = [
        ("MODULO", "DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "SIGLA", "IDX"),
        ("AL21", "MOLA", "D", "52-1", "MOLA", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "modulo": 0, "descricao": 1, "tipo": 2, "equipamento": 3, "sigla": 4, "indice": 5})
    recs = estruturar(rows, mapa, sheet_name="AL21", config=Config(),
                      siglas_set=frozenset({"MOLA"}))
    assert recs[0].eletrico.nome_equipamento == "52-1"  # coluna EQUIPAMENTO
    assert recs[0].sigla_sinal == "MOLA"                # coluna SIGLA (não afetada)
    assert recs[0].modulo.nome == "AL21"                # coluna MODULO (não afetada)
    assert recs[0].status == "decidido"


def test_coluna_equipamento_nao_sobrescreve_equipamento_ja_resolvido_pelo_n0():
    # descrição já traz o ID (N0 extrai "52-11"); coluna EQUIPAMENTO com valor
    # diferente NÃO sobrescreve (política de nunca sobrescrever)
    rows = [
        ("DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "IDX"),
        ("Disj. 52-11 aberto", "D", "89-2", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "descricao": 0, "tipo": 1, "equipamento": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].eletrico.nome_equipamento == "52-11"  # N0 (descrição) ganha


def test_coluna_equipamento_x_varredura_linha_gera_equipamento_conflitante():
    # coluna EQUIPAMENTO diz "52-1"; outra célula da linha menciona um ID
    # divergente ("89-2") -- conflito roteado pelo motivo já existente
    rows = [
        ("DESCRIÇÃO", "TIPO", "EQUIPAMENTO", "OBS", "IDX"),
        ("Disj. aberto", "D", "52-1", "Ref. secc. 89-2", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "descricao": 0, "tipo": 1, "equipamento": 2, "indice": 4})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].status == "revisao"
    assert recs[0].justificativa == "equipamento_conflitante"


def test_coluna_equipamento_decorada_nao_conflita_consigo_mesma():
    """Revisão Task 19 (17/07) — a própria célula da coluna EQUIPAMENTO,
    quando fora da forma canônica NN-N (ex.: "52-1 (novo)"), não pode ser
    re-varrida como se fosse OUTRA célula: c_equip fica de fora da
    varredura de linha inteira, igual a c_modulo. Só uma fonte de
    identidade nessa linha -- não é conflito."""
    rows = [
        ("DESCRICAO", "TIPO", "EQUIPAMENTO", "IDX"),
        ("Disj. aberto", "D", "52-1 (novo)", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={
        "descricao": 0, "tipo": 1, "equipamento": 2, "indice": 3})
    recs = estruturar(rows, mapa, sheet_name="S1", config=Config())
    assert recs[0].eletrico.nome_equipamento == "52-1 (novo)"
    assert recs[0].justificativa != "equipamento_conflitante"


# --- marcador tolerante a numeracao (SP-CVA2 E3.1) --------------------------


def test_marcador_com_numeracao_na_col0():
    """SP-CVA2 E3.1 — layout CVA11: marcador tem nº de sequência na col 0."""
    assert _eh_marcador(("1", None, None, None, "MEDIÇÃO", None), 0)
    assert _eh_marcador(("10", None, None, None, "CONTROLE", None), 0)
    assert _eh_marcador(("16", None, None, None, "SINALIZAÇÃO", None), 0)


def test_marcador_uma_celula_continua_valendo():
    assert _eh_marcador((None, None, None, None, "CONTROLE", None), 0)


def test_linha_de_dados_nao_e_marcador():
    # linha real CVA11 (descrição + código DI + nome): não é marcador
    assert not _eh_marcador(
        ("17", "CVA11", "PP", "N", "Disj. 52-11 (11Q0) - Sup Circ", "DI"), 0
    )


def test_codigo_curto_de_tipo_sozinho_nao_e_marcador():
    """Revisão final de branch (SP-CVA2): composição E3.1 (marcador tolera
    numeração) + E3.2 (códigos AI/AO/DI/DO no vocabulário) pode fazer uma
    linha com descrição vazia, só o código de tipo e numeração de índice
    passar como marcador de seção (categoria via CODIGOS_TIPO, não VOCAB) —
    abriria seção nova e inverteria a direção das linhas seguintes. Célula
    classificadora de marcador só pode casar VOCAB (MEDIÇÃO/CONTROLE/
    SINALIZAÇÃO...), nunca um código curto por-linha."""
    assert not _eh_marcador(("17", None, None, None, None, "DI"), 0)
    assert not _eh_marcador(("17", None, None, None, None, "A"), 0)
    assert not _eh_marcador(("17", None, None, None, None, "C"), 0)


def test_marcador_de_secao_define_direcao_e_nao_vira_registro():
    """Fim-a-fim no estruturar: seção CONTROLE dá Output às linhas seguintes e
    a linha do marcador não vira SignalRecord (E6.4)."""
    rows = [
        ("", "", "", "", "DESCRIÇÃO", "", "", "", "", "INDEX"),      # header (row 1)
        ("10", None, None, None, "CONTROLE", None, None, None, None, None),
        ("11", "CVA11", "PP", "C", "Disjuntor 52-11 - Abrir/Fechar", None, None, None, None, "0"),
        ("16", None, None, None, "SINALIZAÇÃO", None, None, None, None, None),
        ("17", "CVA11", "PP", "N", "Disjuntor 52-11 - Aberto", None, None, None, None, "1"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 4, "indice": 9})
    sinais = estruturar(rows, mapa, sheet_name="CVA11", config=Config())
    por_id = {r.id: r for r in sinais}
    assert "CVA11:2" not in por_id and "CVA11:4" not in por_id  # marcadores
    assert por_id["CVA11:3"].tipo_sinal.direcao == "Output"
    assert por_id["CVA11:3"].tipo_sinal.categoria == "Discrete"
    assert por_id["CVA11:5"].tipo_sinal.direcao == "Input"


def test_equipamento_vem_de_outra_coluna_da_linha():
    # spec 2026-07-15: busca de equipamento varre a linha inteira, não só a
    # descrição (AL11 tem coluna própria de equipamento).
    rows = [
        ("Equipamento", "Descrição", "Endereço"),
        ("52-11", "MOLA CARREGADA", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config())
    assert recs[0].eletrico.nome_equipamento == "52-11"
    assert recs[0].eletrico.equipamento_alvo == "Disjuntor"
    assert recs[0].status != "revisao"


def test_dois_equipamentos_distintos_na_linha_vao_pra_revisao():
    rows = [
        ("Equipamento", "Descrição", "Endereço"),
        ("89-1", "DISJUNTOR 52-11 FECHADO", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config())
    assert recs[0].status == "revisao"
    assert recs[0].justificativa == "equipamento_conflitante"


def test_mesmo_equipamento_repetido_na_linha_nao_conflita():
    rows = [
        ("Equipamento", "Descrição", "Endereço"),
        ("52-11", "DISJUNTOR 52-11 FECHADO", "10"),
    ]
    mapa = MapaColunas(header_row=1, colunas={"descricao": 1, "indice": 2})
    recs = estruturar(rows, mapa, sheet_name="AL11", config=Config())
    assert recs[0].status != "revisao"
    assert recs[0].eletrico.nome_equipamento == "52-11"
