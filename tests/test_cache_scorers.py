"""Cache em disco de scorers (tfidf+fuzzy+indice vetorial) por hash do corpus.

Evita reconstruir TF-IDF/FAISS/fuzzy quando a lista padrão não mudou entre
execuções. Transparente: cache ausente ou corrompido -> reconstrói do zero.
"""

from __future__ import annotations

import numpy as np

from tdt.cache_scorers import _ScorersCacheaveis, _hash_corpus, carregar_ou_construir
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.scoring.tfidf import ScorerTFIDF

_CORPUS = [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA"), ("IA", "CORRENTE FASE A")]
_VOCAB = ["DISJUNTOR", "SECCIONADORA", "CORRENTE", "FASE", "A"]


def _fake_encoder(textos):
    vecs = []
    for t in textos:
        toks = t.upper().split()
        vecs.append([float(toks.count(w)) for w in _VOCAB])
    return np.array(vecs, dtype="float32")


# --- hash ---


def test_hash_estavel_para_mesmo_corpus():
    assert _hash_corpus(_CORPUS) == _hash_corpus(list(_CORPUS))


def test_hash_muda_com_conteudo():
    outro = _CORPUS + [("87", "DIFERENCIAL")]
    assert _hash_corpus(_CORPUS) != _hash_corpus(outro)


# --- serialização individual ---


def test_tfidf_salvar_carregar_roundtrip(tmp_path):
    scorer = ScorerTFIDF.construir(_CORPUS)
    path = tmp_path / "tfidf.pkl"
    scorer.salvar(path)
    recarregado = ScorerTFIDF.carregar(path)
    assert recarregado._siglas == scorer._siglas
    assert recarregado._matriz.shape == scorer._matriz.shape


def test_fuzzy_salvar_carregar_roundtrip(tmp_path):
    matcher = FuzzyMatcher.construir(_CORPUS)
    path = tmp_path / "fuzzy.pkl"
    matcher.salvar(path)
    recarregado = FuzzyMatcher.carregar(path)
    assert recarregado._corpus == matcher._corpus


# --- cache de alto nível ---


def _construir():
    from tdt.dados.indice_vetorial import IndiceVetorial

    return _ScorersCacheaveis(
        tfidf=ScorerTFIDF.construir(_CORPUS),
        indice=IndiceVetorial.construir(_CORPUS, _fake_encoder),
        fuzzy=FuzzyMatcher.construir(_CORPUS),
    )


def test_carregar_ou_construir_constroi_quando_cache_ausente(tmp_path):
    chamadas = {"n": 0}

    def construir():
        chamadas["n"] += 1
        return _construir()

    scorers = carregar_ou_construir(tmp_path / "cache", _CORPUS, construir, _fake_encoder)
    assert chamadas["n"] == 1
    assert scorers.tfidf.pontuar.__self__ is scorers.tfidf  # smoke: objeto usável
    assert (tmp_path / "cache").exists()


def test_carregar_ou_construir_usa_cache_na_segunda_chamada(tmp_path):
    chamadas = {"n": 0}

    def construir():
        chamadas["n"] += 1
        return _construir()

    cache_dir = tmp_path / "cache"
    carregar_ou_construir(cache_dir, _CORPUS, construir, _fake_encoder)
    scorers2 = carregar_ou_construir(cache_dir, _CORPUS, construir, _fake_encoder)
    assert chamadas["n"] == 1  # não reconstruiu na 2a chamada
    assert scorers2.fuzzy.pontuar is not None


def test_carregar_ou_construir_reconstroi_quando_corpus_muda(tmp_path):
    chamadas = {"n": 0}
    cache_dir = tmp_path / "cache"

    def construir_a():
        chamadas["n"] += 1
        return _construir()

    carregar_ou_construir(cache_dir, _CORPUS, construir_a, _fake_encoder)

    outro_corpus = _CORPUS + [("87", "DIFERENCIAL")]

    def construir_b():
        chamadas["n"] += 1
        from tdt.dados.indice_vetorial import IndiceVetorial

        return _ScorersCacheaveis(
            tfidf=ScorerTFIDF.construir(outro_corpus),
            indice=IndiceVetorial.construir(outro_corpus, _fake_encoder),
            fuzzy=FuzzyMatcher.construir(outro_corpus),
        )

    carregar_ou_construir(cache_dir, outro_corpus, construir_b, _fake_encoder)
    assert chamadas["n"] == 2  # corpus mudou -> reconstruiu


def test_carregar_ou_construir_e_transparente_a_cache_corrompido(tmp_path):
    chamadas = {"n": 0}
    cache_dir = tmp_path / "cache"

    def construir():
        chamadas["n"] += 1
        return _construir()

    scorers1 = carregar_ou_construir(cache_dir, _CORPUS, construir, _fake_encoder)
    h = _hash_corpus(_CORPUS)
    # corrompe um arquivo do cache
    alvo = next((cache_dir / h).glob("*tfidf*"))
    alvo.write_bytes(b"lixo corrompido")

    # não deve lançar excecao; deve reconstruir do zero
    scorers2 = carregar_ou_construir(cache_dir, _CORPUS, construir, _fake_encoder)
    assert chamadas["n"] == 2
    assert scorers2 is not None
