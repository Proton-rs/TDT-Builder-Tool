from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.scoring.bm25 import ScorerBM25


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


def test_pontua_top_candidato_bm25():
    scorer = ScorerBM25.construir(_SINAIS)
    cands = scorer.pontuar(_rec("DISJUNTOR FORA OPERACAO"), k=3)
    assert cands[0].sigla == "DJ"
    assert cands[0].fonte == "bm25"
    assert cands[0].score > 0


def test_ordena_desc_e_limita_k():
    # DJ2/DJ3 também citam "DISJUNTOR" p/ exercitar o truncamento por k de
    # verdade (sem eles, só DJ teria termo em comum e k não seria exercitado).
    sinais = _SINAIS + [("DJ2", "DISJUNTOR FALHA"), ("DJ3", "DISJUNTOR BLOQUEADO")]
    scorer = ScorerBM25.construir(sinais)
    cands = scorer.pontuar(_rec("DISJUNTOR FORA OPERACAO"), k=2)
    assert len(cands) == 2
    assert cands[0].sigla == "DJ"
    assert [c.score for c in cands] == sorted([c.score for c in cands], reverse=True)


def test_nao_repete_sigla_com_multiplas_linhas_de_descricao():
    # Lista padrão real tem sigla com >1 linha (variantes NA/NF) -- sem
    # dedup, a mesma sigla apareceria 2x no topo e a fusão (mescla.mesclar,
    # que soma por sigla) contaria o score em dobro.
    sinais = _SINAIS + [("DJ", "DISJUNTOR ABERTO OPERACAO")]
    scorer = ScorerBM25.construir(sinais)
    cands = scorer.pontuar(_rec("DISJUNTOR FORA OPERACAO"), k=5)
    siglas = [c.sigla for c in cands]
    assert siglas.count("DJ") == 1


def test_sem_termos_conhecidos_devolve_vazio():
    scorer = ScorerBM25.construir(_SINAIS)
    assert scorer.pontuar(_rec("xyzabc inexistente"), k=3) == []


def test_salvar_carregar_roundtrip(tmp_path):
    scorer = ScorerBM25.construir(_SINAIS)
    path = tmp_path / "bm25.pkl"
    scorer.salvar(path)
    recarregado = ScorerBM25.carregar(path)
    assert recarregado._siglas == scorer._siglas
    cands = recarregado.pontuar(_rec("DISJUNTOR FORA OPERACAO"), k=3)
    assert cands[0].sigla == "DJ"
