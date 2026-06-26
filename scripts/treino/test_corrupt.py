import random

from corrupt import (
    _abreviar, _sinonimo, _reordenar, _ruido_equip,
    _sufixo_estado, _remover_tokens, _ansi_parens, _typo,
)


def _rng():
    return random.Random(42)


def test_abreviar_encurta_token_conhecido():
    out = _abreviar("DISJUNTOR FASE A", _rng())
    assert "DISJ" in out.upper() and "FASE" in out.upper()


def test_reordenar_preserva_tokens():
    out = _reordenar("CORRENTE FASE A", _rng())
    assert sorted(out.split()) == sorted("CORRENTE FASE A".split())


def test_ruido_equip_insere_id():
    out = _ruido_equip("CORRENTE FASE A", _rng())
    assert len(out) > len("CORRENTE FASE A")


def test_sufixo_estado_anexa():
    out = _sufixo_estado("CORRENTE", _rng())
    assert out.startswith("CORRENTE") and "-" in out


def test_remover_tokens_encurta():
    out = _remover_tokens("CORRENTE FASE A B C", _rng())
    assert len(out.split()) < 5


def test_ansi_parens_substitui_funcao_por_codigo():
    out = _ansi_parens("87 - PROTECAO DIFERENCIAL", _rng())
    assert "(87)" in out


def test_typo_muda_um_caractere():
    base = "CORRENTE"
    out = _typo(base, _rng())
    assert out != base and abs(len(out) - len(base)) <= 1


def test_determinismo_transform():
    assert _ruido_equip("X", random.Random(1)) == _ruido_equip("X", random.Random(1))
