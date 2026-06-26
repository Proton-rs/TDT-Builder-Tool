import random

from mockup import corromper, gerar_dataset

PARES = [
    ("CORRENTE FASE A", "IA"),
    ("87 - PROTECAO DIFERENCIAL", "87"),
    ("DISJUNTOR FASE A", "DJF1"),
    ("TENSAO FASE B", "VB"),
]


def test_determinismo_dataset():
    a = gerar_dataset(PARES, seed=7)
    b = gerar_dataset(PARES, seed=7)
    assert a == b
    assert gerar_dataset(PARES, seed=8) != a


def test_rotulo_preservado_e_cobertura():
    ds = gerar_dataset(PARES, n_variantes=2)
    siglas = {sig for _, sig, _ in ds}
    assert siglas == {"IA", "87", "DJF1", "VB"}
    for _, sig, nivel in ds:
        assert sig in siglas and 1 <= nivel <= 5


def test_monotonicidade_sobreposicao():
    def overlap(nivel):
        tot = 0.0
        for desc, _ in PARES:
            base = set(desc.upper().split())
            c = set(corromper(desc, nivel, random.Random(1)).upper().split())
            tot += len(base & c) / max(1, len(base))
        return tot / len(PARES)

    assert overlap(1) >= overlap(5)
    assert overlap(5) < overlap(1)


def test_nivel4_degrada():
    out = corromper("87 - PROTECAO DIFERENCIAL", 4, random.Random(0))
    assert "(87)" in out or len(out.split()) < 3
