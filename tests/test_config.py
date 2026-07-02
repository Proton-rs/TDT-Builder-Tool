from tdt.config import Config


def test_defaults_analog_pesos_iguais_aos_discretos():
    c = Config()
    assert c.peso_tfidf_analog == c.peso_tfidf
    assert c.peso_vetorial_analog == c.peso_vetorial
    assert c.peso_fuzzy_analog == c.peso_fuzzy


def test_thresholds_analogicos_mais_frouxos_que_discretos():
    c = Config()
    assert c.threshold_pct_analog == 0.35
    assert c.threshold_gap_analog == 0.05
    assert c.threshold_pct_analog < c.threshold_pct
    assert c.threshold_gap_analog < c.threshold_gap


def test_config_spe_defaults():
    from tdt.config import Config
    cfg = Config()
    assert cfg.filtro_semantica_estados is True
    assert "LIBM" in cfg.siglas_revisao_projeto
    assert "CDC" in cfg.siglas_write_legitimo
    assert cfg.siglas_fundiveis_extra == frozenset()
    secc = cfg.siglas_por_equipamento["Seccionadora"]
    assert {"SECC", "SECG", "DSEC", "43LR", "LIBM"} <= secc
