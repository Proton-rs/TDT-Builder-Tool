from tdt.normalizacao.parse_nome import (
    extrair_equipamento_do_nome,
    extrair_modulo_do_nome,
    extrair_se_do_nome,
    sigla_esta_no_nome,
    validar_consistencia_modulo,
)


def test_extrair_modulo_do_nome_3_tokens():
    assert extrair_modulo_do_nome("SND_LT67SAN_LT67SAN_79") == "LT67SAN"


def test_extrair_modulo_do_nome_token_composto():
    assert extrair_modulo_do_nome("SND_SLOTD_SLOTD-2_DR") == "SLOTD"


def test_extrair_modulo_do_nome_sem_underscore_suficiente():
    assert extrair_modulo_do_nome("INVALIDO") is None


def test_extrair_modulo_do_nome_vazio():
    assert extrair_modulo_do_nome("") is None


def test_extrair_equipamento_do_nome_distingue_instancias():
    # Mesmo módulo (token 2), instâncias de equipamento diferentes (token 3)
    # -- é o que distingue "SND_SLOTD_SLOTD-2_DR" de "SND_SLOTD_SLOTD-3_DR"
    # na chave de dedup (modulo, nome_equipamento, sigla) do normalizador_estrutural.
    assert extrair_equipamento_do_nome("SND_SLOTD_SLOTD-2_DR") == "SLOTD-2"
    assert extrair_equipamento_do_nome("SND_SLOTD_SLOTD-3_DR") == "SLOTD-3"
    assert extrair_equipamento_do_nome("SND_LT67SAN_LT67SAN_79") == "LT67SAN"


def test_extrair_equipamento_do_nome_sem_tokens_suficientes():
    assert extrair_equipamento_do_nome("SND_LT67SAN") is None
    assert extrair_equipamento_do_nome("") is None


def test_extrair_se_do_nome():
    assert extrair_se_do_nome("SND_LT67SAN_LT67SAN_79") == "SND"


def test_sigla_esta_no_nome_sufixo_simples():
    assert sigla_esta_no_nome("SND_LT67SAN_LT67SAN_79", "79") is True


def test_sigla_esta_no_nome_sufixo_composto():
    assert sigla_esta_no_nome("SND_LT67TPJ2_89-20_DSEC", "89-20_DSEC") is True


def test_sigla_esta_no_nome_nao_bate():
    assert sigla_esta_no_nome("SND_LT67SAN_LT67SAN_79", "80") is False


def test_sigla_esta_no_nome_sigla_vazia():
    assert sigla_esta_no_nome("SND_LT67SAN_LT67SAN_79", "") is False


def test_sigla_esta_no_nome_letra_unica_nao_casa_no_meio():
    # "P" não deve casar como sufixo se não for o token final
    assert sigla_esta_no_nome("SND_LT67SAN_P_79", "P") is False


def test_sigla_esta_no_nome_letra_unica_no_final():
    assert sigla_esta_no_nome("SND_LT67SAN_LT67SAN_P", "P") is True


def test_validar_consistencia_modulo_ok():
    assert validar_consistencia_modulo("LT67SAN", "LT67SAN") is None


def test_validar_consistencia_modulo_diverge():
    motivo = validar_consistencia_modulo("LT67SAN", "TRANSFER67")
    assert motivo is not None
    assert "LT67SAN" in motivo and "TRANSFER67" in motivo


def test_validar_consistencia_modulo_uma_fonte_ausente():
    assert validar_consistencia_modulo("LT67SAN", None) is None
    assert validar_consistencia_modulo(None, "LT67SAN") is None
