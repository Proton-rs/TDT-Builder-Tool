from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.matchers.fuzzy_match import FuzzyMatcher

CORPUS = [
    ("87", "DIFERENCIAL 87"),
    ("FCOM", "FALHA COMUNICACAO"),
    ("IA", "CORRENTE FASE A"),
    ("SF6B", "DISJUNTOR BAIXA PRESSAO SF6 BLOQUEIO"),
]


def _rec(norm):
    return SignalRecord(
        id="x", modulo=Modulo("m", "s"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(norm, norm),
    )


def test_fuzzy_casa_descricao():
    m = FuzzyMatcher.construir(CORPUS)
    cands = m.pontuar(_rec("FALHA COMUNICACAO IED 01F1"), k=3)
    assert cands[0].sigla == "FCOM"
    assert cands[0].fonte == "fuzzy"


def test_boost_sigla_token_exata():
    m = FuzzyMatcher.construir(CORPUS)
    # "87" aparece literal na descrição -> boost para o sigla 87
    cands = m.pontuar(_rec("DIFERENCIAL 87 BLOQUEADO"), k=3)
    assert cands[0].sigla == "87"


def test_scores_normalizados_0_1():
    m = FuzzyMatcher.construir(CORPUS)
    for c in m.pontuar(_rec("DISJUNTOR BAIXA PRESSAO SF6"), k=4):
        assert 0.0 <= c.score <= 1.0
