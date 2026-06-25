from tdt.defaults import DEFAULT_LISTA
from tdt.dados.lista_padrao import ListaPadraoADMS


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


def test_ignora_linhas_invalidas(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    # nenhuma sigla vazia ou "#N/A" deve entrar
    siglas = {s.sigla for s in lp.discretos}
    assert "" not in siglas
    assert "#N/A" not in siglas
    assert None not in siglas


def test_sinal_discreto_tem_estados_e_valores(lista_padrao_path):
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    # "20T" é RelayTrip com FUNÇÃO "Transit;NORMAL;ATUADO;Error" e VALOR "0;1;2;3"
    sp = lp.por_sigla("20T")
    assert sp is not None
    assert sp.estados_brutos == "Transit;NORMAL;ATUADO;Error"
    assert sp.valores_scada == (0, 1, 2, 3)


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
