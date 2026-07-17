from tdt.config import Config
from tdt.ui.config_io import carregar_config, salvar_config


def test_salvar_grava_so_deltas(tmp_path):
    p = tmp_path / "config.toml"
    salvar_config(p, Config(), {"input": "", "output": "", "template": "", "lista_padrao": ""})
    texto = p.read_text(encoding="utf-8")
    assert "peso_tfidf" not in texto          # default puro -> nada de [config]
    assert "pesos_regras" not in texto

def test_salvar_grava_override(tmp_path):
    from dataclasses import replace
    p = tmp_path / "config.toml"
    salvar_config(p, replace(Config(), threshold_pct=0.5), {"input": "", "output": "", "template": "", "lista_padrao": ""})
    texto = p.read_text(encoding="utf-8")
    assert "threshold_pct = 0.5" in texto
    assert "peso_tfidf" not in texto

def test_carregar_descarta_trio_stale(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text(
        "[config]\npeso_tfidf = 0.34\npeso_vetorial = 0.33\npeso_fuzzy = 0.33\n"
        "threshold_pct = 0.5\n", encoding="utf-8")
    cfg, _ = carregar_config(p)
    assert cfg.peso_tfidf == 0.70 and cfg.peso_vetorial == 0.25 and cfg.peso_fuzzy == 0.05
    assert cfg.threshold_pct == 0.5           # override legítimo preservado

def test_carregar_preserva_peso_intencional(tmp_path):
    p = tmp_path / "config.toml"
    p.write_text("[config]\npeso_tfidf = 0.34\n", encoding="utf-8")  # só 1 dos 3 -> não é o trio
    cfg, _ = carregar_config(p)
    assert cfg.peso_tfidf == 0.34
