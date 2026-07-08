from pathlib import Path

_TEMA = Path(__file__).parent.parent / "src" / "tdt" / "ui" / "tema.qss"


def test_texto_apagado_usa_cor_com_contraste_suficiente():
    conteudo = _TEMA.read_text(encoding="utf-8")
    assert "#5f6880" not in conteudo, "cor antiga de baixo contraste ainda presente"
    assert conteudo.count("#838aa0") == 5, "esperado no comentario + 4 regras (tipo=tecnico, disabled, sidebarContexto, bloqueado)"
