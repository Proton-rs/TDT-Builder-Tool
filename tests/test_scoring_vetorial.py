import numpy as np

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.dados.indice_vetorial import IndiceVetorial
from tdt.scoring.vetorial import pontuar

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
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
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
