from pathlib import Path

from tdt.config import Config
from tdt.ui import config_io
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


# --- Portabilidade (SP-Cleanup item 6): paths relativos -----------------------


def test_salvar_grava_caminho_relativo_quando_dentro_da_raiz(tmp_path):
    p = tmp_path / "config.toml"
    raiz = config_io._RAIZ_PROJETO
    absoluto = str(raiz / "docs" / "exemplo.xlsx")
    salvar_config(p, Config(), {"input": "", "output": "", "template": absoluto, "lista_padrao": ""})
    texto = p.read_text(encoding="utf-8")
    assert str(raiz).replace("\\", "/") not in texto
    assert "docs/exemplo.xlsx" in texto


def test_carregar_resolve_caminho_relativo_para_absoluto(tmp_path):
    p = tmp_path / "config.toml"
    raiz = config_io._RAIZ_PROJETO
    absoluto = str(raiz / "docs" / "exemplo.xlsx")
    salvar_config(p, Config(), {"input": "", "output": "", "template": absoluto, "lista_padrao": ""})
    _, paths = carregar_config(p)
    assert Path(paths["template"]).resolve() == (raiz / "docs" / "exemplo.xlsx").resolve()


def test_caminho_fora_da_raiz_permanece_absoluto(tmp_path):
    p = tmp_path / "config.toml"
    fora = "D:/outro_disco/saida" if Path("D:/").drive else "/outro/disco/saida"
    salvar_config(p, Config(), {"input": "", "output": fora, "template": "", "lista_padrao": ""})
    _, paths = carregar_config(p)
    assert paths["output"] == fora


def test_tdt_docs_dir_sobrepoe_raiz_do_projeto(tmp_path, monkeypatch):
    docs_dir = tmp_path / "outra_maquina" / "docs"
    docs_dir.mkdir(parents=True)
    monkeypatch.setenv("TDT_DOCS_DIR", str(docs_dir))
    p = tmp_path / "config.toml"
    absoluto = str(docs_dir / "lista.xlsx")
    salvar_config(p, Config(), {"input": "", "output": "", "template": "", "lista_padrao": absoluto})
    texto = p.read_text(encoding="utf-8")
    assert "lista.xlsx" in texto
    assert str(docs_dir).replace("\\", "/") not in texto
    _, paths = carregar_config(p)
    assert Path(paths["lista_padrao"]).resolve() == (docs_dir / "lista.xlsx").resolve()
