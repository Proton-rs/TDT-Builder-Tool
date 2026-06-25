from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.busca_adms import buscar


def _lp():
    disc = (
        SinalPadrao("DJF1", "Disjuntor falha função 1", "BISI", None, None, "Discrete"),
        SinalPadrao("DJF2", "Disjuntor falha função 2", "BISI", None, None, "Discrete"),
        SinalPadrao("51N", "Sobrecorrente de neutro", "BISI", None, None, "Discrete"),
    )
    ana = (
        SinalPadrao("IFASE", "Corrente de fase A", "AI", None, None, "Analog"),
    )
    return ListaPadraoADMS(disc, ana)


def test_match_por_sigla_vem_primeiro():
    res = buscar(_lp(), "DJF")
    assert [s.sigla for s in res[:2]] == ["DJF1", "DJF2"]


def test_match_por_texto_da_descricao():
    res = buscar(_lp(), "sobrecorrente")
    assert any(s.sigla == "51N" for s in res)


def test_busca_inclui_analogicos():
    res = buscar(_lp(), "corrente")
    siglas = {s.sigla for s in res}
    assert "IFASE" in siglas  # analógico, casa "corrente" na descrição


def test_case_e_acentos_ignorados():
    res = buscar(_lp(), "FUNCAO")
    assert any(s.sigla == "DJF1" for s in res)


def test_respeita_limite():
    res = buscar(_lp(), "", limite=2)  # termo vazio = sem filtro
    assert len(res) == 2


def test_termo_vazio_lista_tudo_ate_limite():
    res = buscar(_lp(), "")
    assert len(res) == 4
