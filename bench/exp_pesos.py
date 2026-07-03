"""Experimento de fusão: grid estático de pesos, RRF, BM25-tfidf, char n-gram.

Reusa a MESMA montagem de corpus/scorers de bench/benchmark.py (tfidf,
vetorial MiniLM, fuzzy) contra o mesmo ground-truth (ROTULOS), variando só a
estratégia de combinação. Objetivo: checar se algum grid de pesos alternativo,
RRF, ou uma variante de scorer (BM25 / char n-gram) bate a config vigente.

Métricas por variante: acc@1, recall@3, precisão@decididos, taxa de decisão
(roteação por threshold_pct/threshold_gap da Config, igual ao benchmark.py).

Uso: PYTHONPATH=src python bench/exp_pesos.py | Tee-Object bench/resultados/spH_exp_pesos.txt
"""
import sys, warnings, logging, datetime, os
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
sys.path.insert(0, "bench")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import math
import numpy as np
import faiss
from rotulos import ROTULOS
from tdt.config import Config
from tdt.normalizacao.normalizador import canonizar
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.dados.encoder import criar_encoder
from tdt.analise.analise_colunas import normalizar_emb
from tdt.scoring.tfidf import ScorerTFIDF
from tdt.scoring.calibracao import calibrar
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.contracts import Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal

LOG: list[str] = []
def log(s=""):
    print(s); LOG.append(s)

# --- MESMA montagem de bench/benchmark.py -----------------------------------
cfg = Config()
lp = ListaPadraoADMS.carregar(os.environ.get("LISTA_BENCH", "docs/Pontos Padrao ADMS_v1.xlsx"))
corpus = [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.discretos if s.descricao]
corpus += [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.analogicos if s.descricao]
siglas = [s for s, _ in corpus]
desc_por_sigla = {s: d for s, d in corpus}

def faiss_index(ref):
    ix = faiss.IndexFlatIP(ref.shape[1]); ix.add(ref); return ix

enc = criar_encoder(cfg.modelo_embedding)
ref = normalizar_emb(enc([d for _, d in corpus]))
index = faiss_index(ref)
tfidf = ScorerTFIDF.construir(corpus)
fuzzy = FuzzyMatcher.construir(corpus)

def rec(desc):
    return SignalRecord(id="x", modulo=Modulo("m", "s"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)), descricoes=Descricoes(desc, canonizar(desc, cfg)))

def vet_factory(encoder_q, ix):
    def f(r, k):
        q = normalizar_emb(encoder_q([r.descricoes.normalizada]))
        S, I = ix.search(q, k)
        return [Candidato(siglas[j], max(0.0, float(s)), "vet") for s, j in zip(S[0], I[0]) if j != -1]
    return f
vetorial = vet_factory(enc, index)

def combinar_calib(listas, pesos, metodo="minmax"):
    acc = {}
    for lst, w in zip(listas, pesos):
        if not lst: continue
        cal = calibrar([c.score for c in lst], metodo, None)
        for c, sc in zip(lst, cal):
            acc[c.sigla] = acc.get(c.sigla, 0.0) + w * sc
    return sorted((Candidato(s, v, "mix") for s, v in acc.items()), key=lambda c: c.score, reverse=True)

# --- valores vigentes na Config (conferidos, NÃO são 0.4/0.4/0.2) -----------
PESO_ATUAL = (cfg.peso_tfidf, cfg.peso_vetorial, cfg.peso_fuzzy)
log(f"pesos vigentes na Config: tfidf={PESO_ATUAL[0]} vetorial={PESO_ATUAL[1]} fuzzy={PESO_ATUAL[2]}")

# grid do brief tinha (0.4, 0.4, 0.2) como placeholder p/ "atual" — substituído
# pelo valor real da Config. Demais variantes do brief mantidas como estão.
GRIDS = [
    PESO_ATUAL,        # atual (Config real: 0.70/0.25/0.05)
    (0.3, 0.5, 0.2),
    (0.2, 0.6, 0.2),
    (0.2, 0.5, 0.3),
    (0.1, 0.7, 0.2),
]

# --- RRF (reciprocal rank fusion) --------------------------------------------
def rrf(listas, k=60):
    acc = {}
    for lst in listas:
        for rank, c in enumerate(sorted(lst, key=lambda c: c.score, reverse=True)):
            acc[c.sigla] = acc.get(c.sigla, 0.0) + 1.0 / (k + rank + 1)
    return sorted((Candidato(s, v, "rrf") for s, v in acc.items()),
                  key=lambda c: c.score, reverse=True)

# --- BM25 em cima da matriz tfidf existente (idf + saturação) ---------------
# Reusa o CountVectorizer implícito no vectorizer do ScorerTFIDF (vocabulário
# e contagens brutas), aplica idf BM25 e saturação term-frequency (k1, b) em
# vez de cosine puro. ~25 loc, sem dependência nova (sem rank-bm25).
class ScorerBM25:
    def __init__(self, vectorizer, contagens, siglas, k1=1.5, b=0.75):
        self._vectorizer = vectorizer
        self._siglas = siglas
        self._k1, self._b = k1, b
        self._doc_len = np.asarray(contagens.sum(axis=1)).ravel()
        self._avgdl = float(self._doc_len.mean()) if len(self._doc_len) else 1.0
        self._contagens = contagens.tocsc()
        df = np.asarray((contagens > 0).sum(axis=0)).ravel()
        n_docs = contagens.shape[0]
        self._idf = np.log(1 + (n_docs - df + 0.5) / (df + 0.5))

    @classmethod
    def construir(cls, sinais):
        from sklearn.feature_extraction.text import CountVectorizer
        siglas = [s for s, _ in sinais]
        descricoes = [d for _, d in sinais]
        vec = CountVectorizer(token_pattern=r"(?u)\b\w+\b", lowercase=True)
        contagens = vec.fit_transform(descricoes)
        return cls(vec, contagens, siglas)

    def pontuar(self, rec, k=5):
        q_counts = self._vectorizer.transform([rec.descricoes.normalizada])
        termos = q_counts.nonzero()[1]
        if len(termos) == 0:
            return []
        scores = np.zeros(len(self._siglas))
        k1, b = self._k1, self._b
        for t in termos:
            col = self._contagens[:, t].toarray().ravel()
            idf = self._idf[t]
            num = col * (k1 + 1)
            den = col + k1 * (1 - b + b * self._doc_len / self._avgdl)
            scores += idf * np.divide(num, den, out=np.zeros_like(num, dtype=float), where=den != 0)
        ordem = scores.argsort()[::-1][:k]
        return [Candidato(self._siglas[i], float(scores[i]), "bm25") for i in ordem if scores[i] > 0]

bm25 = ScorerBM25.construir(corpus)

# --- char n-gram tfidf (3-5) via ScorerTFIDF.construir -----------------------
# ScorerTFIDF.construir não aceita analyzer/ngram_range (hardcoded token
# pattern word-level) — variante local reaproveitando a MESMA classe via
# monkey-patch do vectorizer, sem duplicar a lógica de pontuar().
def construir_tfidf_char(sinais, ngram_range=(3, 5)):
    from sklearn.feature_extraction.text import TfidfVectorizer
    siglas = [s for s, _ in sinais]
    descricoes = [d for _, d in sinais]
    vec = TfidfVectorizer(analyzer="char", ngram_range=ngram_range, lowercase=True)
    matriz = vec.fit_transform(descricoes)
    return ScorerTFIDF(vec, matriz, siglas)

tfidf_char = construir_tfidf_char(corpus)

# --- variantes a comparar -----------------------------------------------------
VARIANTES = {}
for pesos in GRIDS:
    nome = f"grid{pesos}"
    def make(pesos=pesos):
        return lambda r: combinar_calib([tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)], pesos, "minmax")
    VARIANTES[nome] = make()

VARIANTES["rrf(tfidf,vet,fuzzy)"] = lambda r: rrf([tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)])
VARIANTES["bm25(sozinho)"] = lambda r: bm25.pontuar(r, 5)
VARIANTES["bm25+vet+fuzzy"] = lambda r: combinar_calib([bm25.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)], PESO_ATUAL, "minmax")
VARIANTES["char3-5(sozinho)"] = lambda r: tfidf_char.pontuar(r, 5)
VARIANTES["char3-5+vet+fuzzy"] = lambda r: combinar_calib([tfidf_char.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)], PESO_ATUAL, "minmax")

# --- avaliação -----------------------------------------------------------------
PCT, GAP = cfg.threshold_pct, cfg.threshold_gap
log(f"\nground-truth: {len(ROTULOS)} pares | roteação: pct>={PCT} gap>={GAP}\n")
log(f"{'variante':<24} {'acc@1':>6} {'rec@3':>6} {'decid':>6} {'prec@dec':>9}")

resultados = {}
for nome, fn in VARIANTES.items():
    acc1 = rec3 = decid = corr_dec = 0
    for desc, esp in ROTULOS:
        cands = fn(rec(desc))
        if not cands: continue
        top = cands[0]
        if top.sigla == esp: acc1 += 1
        if esp in [c.sigla for c in cands[:3]]: rec3 += 1
        gap = top.score - (cands[1].score if len(cands) > 1 else 0)
        if top.score >= PCT and gap >= GAP:
            decid += 1
            if top.sigla == esp: corr_dec += 1
    n = len(ROTULOS)
    prec = (corr_dec / decid) if decid else 0
    resultados[nome] = dict(acc1=acc1/n, rec3=rec3/n, decid=decid/n, prec=prec)
    log(f"{nome:<24} {acc1/n:>6.0%} {rec3/n:>6.0%} {decid/n:>6.0%} {prec:>9.0%}")

# --- comparação vs. atual -------------------------------------------------------
atual = resultados[f"grid{PESO_ATUAL}"]
log(f"\nbaseline (atual): acc@1={atual['acc1']:.2%} rec@3={atual['rec3']:.2%} decid={atual['decid']:.2%} prec@dec={atual['prec']:.2%}")
melhor_nome, melhor = max(resultados.items(), key=lambda kv: (kv[1]['prec'], kv[1]['acc1']))
log(f"melhor por (prec@dec, acc@1): {melhor_nome} -> prec={melhor['prec']:.2%} acc@1={melhor['acc1']:.2%}")

header = f"# exp_pesos {datetime.datetime.now():%Y-%m-%d %H:%M}\n"
open("bench/resultados/spH_exp_pesos.txt", "w", encoding="utf-8").write(header + "\n".join(LOG))
