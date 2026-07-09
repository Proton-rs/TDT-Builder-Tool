"""Trava de não-regressão do corpus adversarial (spD).

Não muda produção: exercita a normalização determinística em cada caso
conhecido de FP/perda de token e asserta o não-FP. Casos ainda quebrados são
xfail documentado (dívida), não falham a suíte.
"""

import pytest

from tdt.config import Config
from tdt.normalizacao.normalizador import canonizar, extrair_contexto_estrutural
from tests.corpus_adversarial import (
    CASOS_FASE,
    CASOS_TOKEN_PRESERVADO,
    CASOS_TOKEN_PROIBIDO,
    CASOS_XFAIL_SIGLA,
)

CFG = Config()


@pytest.mark.parametrize(
    "cid,texto,token", CASOS_TOKEN_PRESERVADO, ids=[c[0] for c in CASOS_TOKEN_PRESERVADO]
)
def test_token_preservado(cid, texto, token):
    assert token in canonizar(texto, CFG).split()


@pytest.mark.parametrize(
    "cid,texto,token", CASOS_TOKEN_PROIBIDO, ids=[c[0] for c in CASOS_TOKEN_PROIBIDO]
)
def test_token_proibido(cid, texto, token):
    assert token not in canonizar(texto, CFG).split()


@pytest.mark.parametrize(
    "cid,texto,fase", CASOS_FASE, ids=[c[0] for c in CASOS_FASE]
)
def test_fase_preservada(cid, texto, fase):
    _rem, ctx = extrair_contexto_estrutural(texto)
    assert ctx.fase == fase


@pytest.mark.xfail(
    reason="sigla de protecao \\d+[A-Z]\\d+ removida como ID (anot.txt); "
    "gate real: bench/casos_travados.csv",
    strict=False,
)
@pytest.mark.parametrize(
    "cid,texto,token", CASOS_XFAIL_SIGLA, ids=[c[0] for c in CASOS_XFAIL_SIGLA]
)
def test_sigla_protecao_nao_truncada(cid, texto, token):
    assert token in canonizar(texto, CFG).split()
