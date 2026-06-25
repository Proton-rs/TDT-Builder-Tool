from tdt.contracts import Candidato
from tdt.scoring.mescla import mesclar


def test_pondera_scores_da_mesma_sigla():
    tfidf = [Candidato("DJ", 0.8, "tfidf")]
    vet = [Candidato("DJ", 0.6, "vetorial")]
    out = mesclar([(tfidf, 0.5), (vet, 0.5)])
    assert out[0].sigla == "DJ"
    assert abs(out[0].score - 0.7) < 1e-9
    assert out[0].fonte == "mesclado"


def test_uniao_de_siglas_distintas():
    tfidf = [Candidato("DJ", 1.0, "tfidf")]
    vet = [Candidato("SEC", 1.0, "vetorial")]
    siglas = {c.sigla for c in mesclar([(tfidf, 0.5), (vet, 0.5)])}
    assert siglas == {"DJ", "SEC"}


def test_tres_fontes():
    a = [Candidato("X", 1.0, "tfidf")]
    b = [Candidato("X", 1.0, "vet")]
    c = [Candidato("X", 1.0, "fuzzy")]
    out = mesclar([(a, 0.34), (b, 0.33), (c, 0.33)])
    assert abs(out[0].score - 1.0) < 1e-9


def test_ordena_desc():
    tfidf = [Candidato("DJ", 0.2, "tfidf"), Candidato("SEC", 0.9, "tfidf")]
    out = mesclar([(tfidf, 1.0)])
    assert [c.sigla for c in out] == ["SEC", "DJ"]
