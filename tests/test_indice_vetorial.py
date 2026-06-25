import numpy as np

from tdt.dados.indice_vetorial import IndiceVetorial

# encoder falso determinístico: bag-of-words sobre vocab fixo (cosine = match exato no topo)
_VOCAB = ["DISJUNTOR", "SECCIONADORA", "CORRENTE", "FASE", "A"]


def _fake_encoder(textos):
    vecs = []
    for t in textos:
        toks = t.upper().split()
        vecs.append([float(toks.count(w)) for w in _VOCAB])
    return np.array(vecs, dtype="float32")


_SINAIS = [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA"), ("IA", "CORRENTE FASE A")]


def test_busca_retorna_sigla_mais_proxima():
    idx = IndiceVetorial.construir(_SINAIS, _fake_encoder)
    res = idx.buscar("DISJUNTOR", k=1)
    assert res[0][0] == "DJ"
    assert res[0][1] > 0.9


def test_busca_retorna_k_ordenado():
    idx = IndiceVetorial.construir(_SINAIS, _fake_encoder)
    res = idx.buscar("CORRENTE FASE A", k=3)
    assert len(res) == 3
    assert res[0][0] == "IA"
    scores = [s for _, s in res]
    assert scores == sorted(scores, reverse=True)


def test_persistencia_roundtrip(tmp_path):
    idx = IndiceVetorial.construir(_SINAIS, _fake_encoder)
    idx.salvar(tmp_path)
    recarregado = IndiceVetorial.carregar(tmp_path, _fake_encoder)
    assert recarregado.buscar("SECCIONADORA", k=1)[0][0] == "SECC"


# --- e5 assimétrico: prefixo de passagem != consulta ---

_VOCAB_E5 = ["PASSAGE", "QUERY", "DISJUNTOR", "SECCIONADORA"]


def _enc_prefixado(prefixo):
    # fake e5: concatena o prefixo ao texto; o token de prefixo entra no vetor,
    # então passage-vec e query-vec do mesmo texto diferem.
    def encode(textos):
        vecs = []
        for t in textos:
            toks = (prefixo + " " + t).upper().split()
            vecs.append([float(toks.count(w)) for w in _VOCAB_E5])
        return np.array(vecs, dtype="float32")

    return encode


def test_e5_assimetrico_vetores_distintos_por_prefixo():
    enc_passagem = _enc_prefixado("passage")
    enc_consulta = _enc_prefixado("query")
    vp = enc_passagem(["DISJUNTOR"])
    vq = enc_consulta(["DISJUNTOR"])
    # mesmo texto, prefixos distintos -> vetores distintos
    assert not np.array_equal(vp, vq)


def test_e5_assimetrico_busca_funciona():
    enc_passagem = _enc_prefixado("passage")
    enc_consulta = _enc_prefixado("query")
    sinais = [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA")]
    idx = IndiceVetorial.construir(sinais, enc_passagem, encoder_consulta=enc_consulta)
    # a busca usa o encoder de consulta; ainda assim acha a passagem certa
    res = idx.buscar("DISJUNTOR", k=1)
    assert res[0][0] == "DJ"


def test_afinidade_centroide_favorece_corpus_mais_similar():
    disjuntores = [("DJ1", "DISJUNTOR ABERTO"), ("DJ2", "DISJUNTOR FECHADO")]
    correntes = [("IA", "CORRENTE FASE A"), ("IB", "CORRENTE FASE B")]
    idx_disc = IndiceVetorial.construir(disjuntores, _fake_encoder)
    idx_ana = IndiceVetorial.construir(correntes, _fake_encoder)
    afin_disc = idx_disc.afinidade_centroide("DISJUNTOR FECHADO")
    afin_ana = idx_ana.afinidade_centroide("DISJUNTOR FECHADO")
    assert afin_disc > afin_ana


def test_afinidade_centroide_persiste_no_roundtrip(tmp_path):
    sinais = [("DJ", "DISJUNTOR"), ("SECC", "SECCIONADORA")]
    idx = IndiceVetorial.construir(sinais, _fake_encoder)
    idx.salvar(tmp_path)
    recarregado = IndiceVetorial.carregar(tmp_path, _fake_encoder)
    assert recarregado.afinidade_centroide("DISJUNTOR") == idx.afinidade_centroide("DISJUNTOR")
