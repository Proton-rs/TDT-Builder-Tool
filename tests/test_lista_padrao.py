from tdt.defaults import DEFAULT_LISTA
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.dados.lista_padrao import descricoes_por_sigla


def test_default_lista_aponta_para_v2_com_djf1_enriquecido():
    assert "v2" in DEFAULT_LISTA
    lp = ListaPadraoADMS.carregar(DEFAULT_LISTA)
    sp = lp.por_sigla("DJF1")
    assert sp is not None
    assert "LIGADO" in sp.descricao.upper()
    assert "DESLIGADO" in sp.descricao.upper()


def test_carrega_discretos_e_analogicos(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    assert len(lp.discretos) > 100
    assert len(lp.analogicos) > 10


def test_sinal_discreto_conhecido(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    cmde = lp.por_sigla("CMDE")
    assert cmde is not None
    assert cmde.categoria == "Discrete"
    assert cmde.signal_type == "Custom"
    assert cmde.direction == "ReadWrite"
    assert cmde.mm.startswith("CMD_CEEE@CMD_RGE")


def test_sinal_analogico_conhecido(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    in61 = lp.por_sigla("IN61")
    assert in61.categoria == "Analog"
    assert in61.signal_type == "Valor Medido"


def test_siglas_inclui_discretos_e_analogicos(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    siglas = lp.siglas
    assert isinstance(siglas, frozenset)
    assert "CMDE" in siglas  # discreto
    assert "IN61" in siglas  # analógico
    assert len(siglas) == len({s.sigla for s in (*lp.discretos, *lp.analogicos)})


def test_siglas_normaliza_maiusculas(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    assert all(s == s.upper() for s in lp.siglas)


def test_ignora_linhas_invalidas(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    # nenhuma sigla vazia ou "#N/A" deve entrar
    siglas = {s.sigla for s in lp.discretos}
    assert "" not in siglas
    assert "#N/A" not in siglas
    assert None not in siglas


def test_sinal_discreto_tem_estados_e_valores(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    # Na v2, a sheet DiscreteSignals não tem nenhuma linha com FUNÇÃO/VALOR
    # preenchidos (colunas existem no header, mas vazias em produção) — ao
    # contrário da v1, onde "20T" trazia
    # "Transit;NORMAL;ATUADO;Error" / "0;1;2;3". Mantém a leitura validada
    # (campo None / tupla vazia quando a fonte não traz dado), sem inventar
    # valor que a v2 não tem.
    sp = lp.por_sigla("20T")
    assert sp is not None
    assert sp.estados_brutos is None
    assert sp.valores_scada == ()


def test_analogico_sem_estados(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    in61 = lp.por_sigla("IN61")
    assert in61.estados_brutos is None
    assert in61.valores_scada == ()


def test_le_tipo_medicao_e_unidade_exibicao_de_analog_signals(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    in61 = lp.por_sigla("IN61")
    assert in61.tipo_medicao == "Corrente"
    assert in61.unidade_exibicao == "A"


def test_le_type_severidade_dos_discretos(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    assert lp.por_sigla("TEA").type_severidade == "PROT"
    assert lp.por_sigla("DJF1").type_severidade == "DJ"
    assert lp.por_sigla("CMDE").type_severidade == "ALARMES PREDIAIS/VF/GRUPO"


def test_analogico_sem_type_severidade(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    assert lp.por_sigla("IN61").type_severidade is None


def test_descricoes_por_sigla_le_v1(docs):
    m = descricoes_por_sigla(str(docs / "Pontos Padrao ADMS_v1.xlsx"))
    assert m["TEA"] == "49 - ALARME TEMPERATURA ENROLAMENTO"
    assert "IN61" in m  # analógicos também entram


def test_descricoes_por_sigla_arquivo_ausente_devolve_vazio(tmp_path):
    assert descricoes_por_sigla(str(tmp_path / "nao_existe.xlsx")) == {}
