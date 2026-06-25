import pytest
from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt import pipeline


class _ScorerFake:
    def __init__(self, fonte, scores):
        self._fonte = fonte
        self._scores = scores  # list[(sigla, score)]

    def pontuar(self, rec, k=5):
        return [Candidato(s, sc, self._fonte) for s, sc in self._scores[:k]]


class _IndiceFake:
    def __init__(self, scores):
        self._scores = scores

    def buscar(self, texto, k=5):
        return self._scores[:k]


@pytest.fixture
def rec_minimo():
    return SignalRecord(
        id="s:1",
        modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("FALHA DJ", "FALHA DJ"),
    )


@pytest.fixture
def scorers_fakes():
    tfidf = _ScorerFake("tfidf", [("DJF1", 0.9), ("DJF", 0.5)])
    fuzzy = _ScorerFake("fuzzy", [("DJF1", 0.7), ("DJF", 0.4)])
    indice = _IndiceFake([("DJF1", 0.8), ("DJF", 0.3)])
    return pipeline._Scorers(tfidf=tfidf, indice=indice, fuzzy=fuzzy, config=Config())


def test_classificar_preenche_diagnostico_quando_ligado(rec_minimo, scorers_fakes):
    out = pipeline._classificar_sinal(rec_minimo, scorers_fakes, diagnostico=True)
    assert out.diagnostico is not None
    # a sigla top tem os três métodos registrados
    top = out.candidatos[0].sigla
    assert set(out.diagnostico.scores_por_metodo[top]) == {"tfidf", "vetorial", "fuzzy"}


def test_classificar_sem_diagnostico_por_padrao(rec_minimo, scorers_fakes):
    out = pipeline._classificar_sinal(rec_minimo, scorers_fakes)
    assert out.diagnostico is None
