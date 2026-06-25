from tdt.config import Config
from tdt.ui.config_io import carregar_config, salvar_config


def test_round_trip(tmp_path):
    p = tmp_path / "config.toml"
    cfg = Config(threshold_pct=0.5, peso_tfidf=0.4, peso_vetorial=0.3, peso_fuzzy=0.3)
    paths = {"input": "C:/in", "output": "C:/out", "template": "t.xlsx", "lista_padrao": "lp.xlsx"}
    salvar_config(p, cfg, paths)
    cfg2, paths2 = carregar_config(p)
    assert cfg2.threshold_pct == 0.5
    assert cfg2.peso_tfidf == 0.4
    assert paths2["output"] == "C:/out"


def test_arquivo_ausente_cai_nos_defaults(tmp_path):
    cfg, paths = carregar_config(tmp_path / "nao_existe.toml")
    assert cfg == Config()
    assert paths == {"input": "", "output": "", "template": "", "lista_padrao": ""}
