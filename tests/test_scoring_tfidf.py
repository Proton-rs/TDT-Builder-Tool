from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.scoring.tfidf import ScorerTFIDF


def _rec(norm):
    return SignalRecord(
        id="LT3:1",
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes("bruto", norm),
    )


_SINAIS = [
    ("DJ", "DISJUNTOR FORA OPERACAO"),
    ("SECC", "SECCIONADORA FECHADA"),
    ("67N", "RELE SOBRECORRENTE NEUTRO"),
]


def test_pontua_top_candidato_tfidf():
    scorer = ScorerTFIDF.construir(_SINAIS)
    cands = scorer.pontuar(_rec("DISJUNTOR FORA OPERACAO"), k=3)
    assert cands[0].sigla == "DJ"
    assert cands[0].fonte == "tfidf"
    assert cands[0].score > 0.5


def test_ordena_desc_e_limita_k():
    scorer = ScorerTFIDF.construir(_SINAIS)
    cands = scorer.pontuar(_rec("SECCIONADORA FECHADA"), k=2)
    assert len(cands) == 2
    assert cands[0].sigla == "SECC"
    assert [c.score for c in cands] == sorted([c.score for c in cands], reverse=True)


def test_nao_repete_sigla_com_multiplas_linhas_de_descricao():
    # Lista padrão real tem sigla com >1 linha (variantes NA/NF) -- sem
    # dedup, a mesma sigla apareceria 2x no topo e a fusão (mescla.mesclar,
    # que soma por sigla) contaria o score em dobro.
    sinais = _SINAIS + [("DJ", "DISJUNTOR ABERTO OPERACAO")]
    scorer = ScorerTFIDF.construir(sinais)
    cands = scorer.pontuar(_rec("DISJUNTOR FORA OPERACAO"), k=5)
    siglas = [c.sigla for c in cands]
    assert siglas.count("DJ") == 1
