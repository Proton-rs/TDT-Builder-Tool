import numpy as np

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.dados.indice_vetorial import IndiceVetorial
from tdt.scoring.vetorial import pontuar, pontuar_com_embedding

_VOCAB = ["DISJUNTOR", "SECCIONADORA", "CORRENTE"]


def _fake_encoder(textos):
    return np.array(
        [[float(t.upper().split().count(w)) for w in _VOCAB] for t in textos],
        dtype="float32",
    )


def _rec(norm):
    return SignalRecord(
        id="LT3:1",
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes("bruto", norm),
    )


def test_pontua_top_candidato_vetorial():
    idx = IndiceVetorial.construir(
        [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA")], _fake_encoder
    )
    cands = pontuar(_rec("DISJUNTOR"), idx, k=2)
    assert cands[0].sigla == "DJ"
    assert cands[0].fonte == "vetorial"
    assert 0.0 <= cands[0].score <= 1.0


def test_pontuar_com_embedding_equivale_a_pontuar():
    """pontuar_com_embedding deve produzir os mesmos resultados de pontuar()
    quando o embedding fornecido é o mesmo que pontuar() teria calculado
    internamente — só evita reencodar."""
    idx = IndiceVetorial.construir(
        [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA")], _fake_encoder
    )
    rec = _rec("DISJUNTOR")

    esperado = pontuar(rec, idx, k=2)

    embedding = _fake_encoder([rec.descricoes.normalizada])[0]
    resultado = pontuar_com_embedding(embedding, rec, idx, k=2)

    assert len(resultado) == len(esperado)
    for c_res, c_esp in zip(resultado, esperado):
        assert c_res.sigla == c_esp.sigla
        assert c_res.fonte == c_esp.fonte
        assert abs(c_res.score - c_esp.score) < 1e-6


def test_pontuar_com_embedding_usa_top_candidato_correto():
    idx = IndiceVetorial.construir(
        [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA")], _fake_encoder
    )
    rec = _rec("DISJUNTOR")
    embedding = _fake_encoder([rec.descricoes.normalizada])[0]

    cands = pontuar_com_embedding(embedding, rec, idx, k=2)

    assert cands[0].sigla == "DJ"
    assert cands[0].fonte == "vetorial"
    assert 0.0 <= cands[0].score <= 1.0
