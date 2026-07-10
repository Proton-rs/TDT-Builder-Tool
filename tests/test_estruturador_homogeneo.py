from tdt.config import Config
from tdt.dados.lista_padrao import SinalPadrao
from tdt.normalizacao.estruturador_homogeneo import detectar_header, estruturar_homogeneo


def test_detectar_header_acha_linha_no_formato_fixo():
    rows = [
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMÔNICO"),
        ("DJ", "52-11"),
        (),
        ("Utilizado?", "SUBESTAÇÃO", "MÓDULO", "EQUIPAMENTO", "TIPO",
         "DESCRIÇÃO DO PONTO", "SIGLA SINAL", "NOME", "Tipo",
         "Nível Lógico 0", "Nível Lógico 1", "Escala",
         "Control Code / Qualificador", "INDEX DNP3"),
        ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
         "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70"),
    ]
    assert detectar_header(rows) == 3


def test_detectar_header_devolve_none_sem_formato_fixo():
    rows = [("DESCRIÇÃO", "ÍNDICE"), ("Disjuntor 52-2", "100")]
    assert detectar_header(rows) is None


class _ListaPadraoFake:
    def __init__(self, siglas: dict[str, SinalPadrao]):
        self._siglas = siglas

    def por_sigla(self, sigla):
        return self._siglas.get(sigla.strip().upper())


def _sinal_padrao(sigla: str) -> SinalPadrao:
    return SinalPadrao(
        sigla=sigla, descricao="CORRENTE FASE A", signal_type="Current",
        direction=None, mm=None, categoria="Analog",
    )


_HEADER = (
    "Utilizado?", "SUBESTAÇÃO", "MÓDULO", "EQUIPAMENTO", "TIPO",
    "DESCRIÇÃO DO PONTO", "SIGLA SINAL", "NOME", "Tipo",
    "Nível Lógico 0", "Nível Lógico 1", "Escala",
    "Control Code / Qualificador", "INDEX DNP3",
)


def test_linha_com_sigla_valida_vira_decidido_sem_scoring():
    rows = [_HEADER, ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
                       "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({"IA": _sinal_padrao("IA")})
    decididos, pendentes, _, _ = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert pendentes == []
    assert len(decididos) == 1
    rec = decididos[0]
    assert rec.sigla_sinal == "IA"
    assert rec.status == "decidido"
    assert rec.modulo.nome == "AL"
    assert rec.enderecamento.indices == (70,)


def test_linha_nao_utilizada_nao_vira_sinal():
    rows = [_HEADER, ("NÃO", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
                       "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({"IA": _sinal_padrao("IA")})
    decididos, pendentes, _, _ = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert decididos == [] and pendentes == []


def test_sigla_inexistente_na_lista_padrao_vai_pra_pendentes():
    rows = [_HEADER, ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "XYZ",
                       "IMA_AL11_AL11_XYZ", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({})
    decididos, pendentes, _, _ = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert decididos == [] and len(pendentes) == 1


def test_equipamento_disjuntor_mapeado_por_modulo_dj():
    rows = [_HEADER, ("SIM", "IMA", "DJ1", "DJ", "D", "DISJUNTOR 52-1 ABERTO", "DJF1",
                       "IMA_DJ1_DJF1", "-", "-", "-", "-", "-", "100;101")]
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    decididos, _, _, _ = estruturar_homogeneo(rows, 0, "DJ1", lp, Config())
    assert decididos[0].eletrico.equipamento_alvo == "Disjuntor"
    assert decididos[0].enderecamento.indices == (100, 101)


def test_indice_duplo_nativo_vira_doublebit():
    rows = [_HEADER, ("SIM", "IMA", "DJ1", "DJ", "D", "DISJUNTOR 52-1 ABERTO", "DJF1",
                       "IMA_DJ1_DJF1", "-", "-", "-", "-", "-", "1100;1101")]
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    decididos, _, _, _ = estruturar_homogeneo(rows, 0, "DJ1", lp, Config())
    assert decididos[0].tipo_sinal.datatype == "DoubleBit"


def _rows_com_bloco(modulo_col="AL", numero="23"):
    return [
        ("MÓDULO - ALIMENTADOR",),
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMNICO"),
        ("MÓDULO  ", numero),
        ("DJ", "52-23"),
        ("SECC", "29-62"),
        _HEADER,
        ("SIM", "IMA", modulo_col, "DJ", "C", "DISJUNTOR NF", "DJF1",
         "IMA_AL23_52-23_DJF1", "-", "-", "-", "-", "-", "1"),
    ]


def test_extrai_bloco_de_numeros_operativos():
    from tdt.normalizacao.identidade_homogenea import extrair_bloco
    bloco = extrair_bloco(_rows_com_bloco(), header_idx=5)
    assert bloco["MODULO"] == "23"
    assert bloco["DJ"] == "52-23"


def test_modulo_compoe_tipo_da_coluna_com_numero_do_bloco():
    rows = _rows_com_bloco(modulo_col="AL", numero="23")
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    decididos, pendentes, _, _ = estruturar_homogeneo(rows, 5, "AL23", lp, Config())
    rec = (decididos + pendentes)[0]
    assert rec.modulo.nome == "AL23"
    assert "header:NUMERO_OPERATIVO" in rec.modulo.origem_contexto


def test_modulo_coluna_ja_numerada_mantem_comportamento():
    rows = _rows_com_bloco(modulo_col="LT 1", numero="99")
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    decididos, pendentes, _, _ = estruturar_homogeneo(rows, 5, "LT1", lp, Config())
    rec = (decididos + pendentes)[0]
    assert rec.modulo.nome == "LT 1"
    assert rec.modulo.origem_contexto == "coluna:MODULO"


def test_bloco_ausente_mantem_comportamento():
    rows = [_HEADER, ("SIM", "IMA", "AL", "DJ", "C", "DISJUNTOR NF", "DJF1",
                      "IMA_AL_DJF1", "-", "-", "-", "-", "-", "1")]
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    decididos, pendentes, _, _ = estruturar_homogeneo(rows, 0, "AL", lp, Config())
    rec = (decididos + pendentes)[0]
    assert rec.modulo.nome == "AL"
    assert rec.modulo.origem_contexto == "coluna:MODULO"


def _rows_lt3_43lr():
    bloco = [
        ("MÓDULO - LINHA DE TRANSMISSÃO",),
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMNICO"),
        ("MÓDULO  ", "3"),
        ("DJ", "52-3"),
        ("SECC", "89-16"),
        ("SECF", "89-14"),
        _HEADER,
    ]
    linhas = [
        ("SIM", "IMA", "LT", "SECC", "D", "43 - CHAVE LOCAL REMOTO", "43LR",
         "IMA_LT3_89-16_43LR", "-", "-", "-", "-", "-", "1"),
        ("SIM", "IMA", "LT", "SECF", "D", "43 - CHAVE LOCAL REMOTO", "43LR",
         "IMA_LT3_89-14_43LR", "-", "-", "-", "-", "-", "6"),
        ("SIM", "IMA", "LT", "DJ_P", "D", "FASE A", "FA",
         "IMA_LT3_52-3_P_FA", "-", "-", "-", "-", "-", "38"),
    ]
    return bloco + linhas


def test_nome_equipamento_resolvido_por_equipamento_da_linha():
    lp = _ListaPadraoFake({"43LR": _sinal_padrao("43LR"), "FA": _sinal_padrao("FA")})
    decididos, _, _, _ = estruturar_homogeneo(_rows_lt3_43lr(), 6, "LT 3", lp, Config())
    por_id = {d.id: d for d in decididos}
    assert por_id["LT 3:8"].eletrico.nome_equipamento == "89-16"
    assert por_id["LT 3:9"].eletrico.nome_equipamento == "89-14"
    assert por_id["LT 3:10"].eletrico.nome_equipamento == "52-3_P"
    assert all(d.modulo.nome == "LT3" for d in decididos)


def test_comtap_vai_para_revisao_sem_gerar_ponto():
    rows = [_HEADER, ("SIM", "IMA", "TR", "TR", "C", "COMANDO TAP", "COMTAP",
                      "IMA_TR6_TR6_COMTAP", "-", "-", "-", "-", "-", "30;30")]
    lp = _ListaPadraoFake({})
    decididos, pendentes, revisao, _ = estruturar_homogeneo(rows, 0, "TR 1", lp, Config())
    assert decididos == [] and pendentes == []
    assert len(revisao) == 1
    assert revisao[0].motivo == "comando_tap_nao_modelado"
    assert revisao[0].registro.sigla_sinal == "COMTAP"


def test_tipo_ad_vira_discrete_analog():
    rows = [_HEADER, ("SIM", "IMA", "TR", "TR", "A/D", "TAP", "TAP",
                      "IMA_TR6_TR6_TAP", "-", "-", "-", "-", "-", "47")]
    lp = _ListaPadraoFake({"TAP": _sinal_padrao("TAP")})
    decididos, _, _, _ = estruturar_homogeneo(rows, 0, "TR 1", lp, Config())
    assert decididos[0].tipo_sinal.categoria == "DiscreteAnalog"
    assert decididos[0].tipo_sinal.direcao == "Input"


def test_divergencia_nome_cliente_vira_aviso():
    rows = [_HEADER, ("SIM", "IMA", "AL", "DJ", "D", "DISJUNTOR NF", "DJF1",
                      "IMA_OUTRACOISA_DJF1", "-", "-", "-", "-", "-", "1")]
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    _, _, _, avisos = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert len(avisos) == 1
    assert "IMA_OUTRACOISA_DJF1" in avisos[0]
