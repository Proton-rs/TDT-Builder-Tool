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
