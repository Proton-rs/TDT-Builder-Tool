from tdt.contracts import Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.matchers.cross_encoder import rerank


def _rec(norm):
    return SignalRecord(
        id="x", modulo=Modulo("m", "s"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)), descricoes=Descricoes(norm, norm),
    )


DESC = {"DJ": "DISJUNTOR ABERTO", "SEC": "SECCIONADORA FECHADA"}


def test_rerank_reordena_pelo_cross_encoder():
    rec = _rec("DISJUNTOR ABERTO")
    cands = [Candidato("SEC", 0.9, "mesclado"), Candidato("DJ", 0.5, "mesclado")]
    # fake scorer: pontua alto quando query == doc
    def scorer(pares):
        return [5.0 if q == d else -5.0 for q, d in pares]
    out = rerank(rec, cands, DESC, scorer)
    assert out[0].sigla == "DJ"  # reranker corrige a ordem
    assert out[0].fonte == "rerank"


def test_scores_em_0_1():
    rec = _rec("DISJUNTOR ABERTO")
    cands = [Candidato("DJ", 0.5, "x")]
    out = rerank(rec, cands, DESC, lambda p: [0.0])
    assert 0.0 <= out[0].score <= 1.0


def test_sem_candidatos():
    assert rerank(_rec("x"), [], DESC, lambda p: []) == []
