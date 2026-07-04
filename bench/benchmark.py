"""Compara métodos de matching no ground-truth rotulado. Loga em arquivo.

Métricas: acc@1 (top1 correto), recall@3, e — aplicando roteação (pct,gap) —
precisão@decididos (sem falsos positivos) e taxa de decisão.

Métodos pesados (e5, cross-encoder) ficam em try/except: se o download falhar,
são marcados indisponíveis sem quebrar o restante.

Uso: PYTHONPATH=src python bench/benchmark.py
Saída: bench/resultados/benchmark.log
"""
import sys, warnings, logging, datetime, os
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
sys.path.insert(0, "bench")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import faiss, numpy as np
from rotulos import ROTULOS
from tdt.config import Config
from tdt.normalizacao.normalizador import canonizar
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.dados.encoder import criar_encoder, criar_scorer_cross_encoder
from tdt.analise.analise_colunas import normalizar_emb
from tdt.scoring.tfidf import ScorerTFIDF
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.matchers.cross_encoder import rerank
from tdt.contracts import Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal

LOG: list[str] = []
def log(s=""):
    print(s); LOG.append(s)

cfg = Config()
lp = ListaPadraoADMS.carregar(os.environ.get("LISTA_BENCH", "docs/Pontos Padrao ADMS_v1.xlsx"))
corpus = [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.discretos if s.descricao]
corpus += [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.analogicos if s.descricao]
siglas = [s for s, _ in corpus]
desc_por_sigla = {s: d for s, d in corpus}

def faiss_index(ref):
    ix = faiss.IndexFlatIP(ref.shape[1]); ix.add(ref); return ix

# --- bi-encoder atual (MiniLM) ---
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

def combinar(listas, pesos):
    acc = {}
    for lst, w in zip(listas, pesos):
        for c in lst:
            acc[c.sigla] = acc.get(c.sigla, 0.0) + w * c.score
    return sorted((Candidato(s, v, "mix") for s, v in acc.items()), key=lambda c: c.score, reverse=True)

from tdt.scoring.calibracao import calibrar
def combinar_calib(listas, pesos, metodo="minmax"):
    acc = {}
    for lst, w in zip(listas, pesos):
        if not lst: continue
        cal = calibrar([c.score for c in lst], metodo, None)
        for c, sc in zip(lst, cal):
            acc[c.sigla] = acc.get(c.sigla, 0.0) + w * sc
    return sorted((Candidato(s, v, "mix") for s, v in acc.items()), key=lambda c: c.score, reverse=True)

METODOS = {
    "tfidf": lambda r: tfidf.pontuar(r, 5),
    "vetorial(MiniLM)": lambda r: vetorial(r, 5),
    "fuzzy": lambda r: fuzzy.pontuar(r, 5),
    "tfidf+vet+fuzzy": lambda r: combinar([tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)], [0.34, 0.33, 0.33]),
    "combo(calib-minmax)": lambda r: combinar_calib([tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)], [0.34, 0.33, 0.33], "minmax"),
    "combo(calib-temp)": lambda r: combinar_calib([tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)], [0.34, 0.33, 0.33], "temperature"),
    "combo+regras": lambda r: motor_regras.aplicar(r, combinar([tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)], [0.34, 0.33, 0.33]), cfg),
}
from tdt import motor_regras

# --- e5 (prefixos query:/passage:) ---
try:
    enc_e5_p = criar_encoder("intfloat/multilingual-e5-base", "passage: ")
    enc_e5_q = criar_encoder("intfloat/multilingual-e5-base", "query: ")
    ref_e5 = normalizar_emb(enc_e5_p([d for _, d in corpus]))
    index_e5 = faiss_index(ref_e5)
    vetorial_e5 = vet_factory(enc_e5_q, index_e5)
    METODOS["e5"] = lambda r: vetorial_e5(r, 5)
    METODOS["tfidf+e5+fuzzy"] = lambda r: combinar([tfidf.pontuar(r, 5), vetorial_e5(r, 5), fuzzy.pontuar(r, 5)], [0.34, 0.33, 0.33])
    log("e5: OK")
except Exception as e:
    log(f"e5: INDISPONÍVEL ({type(e).__name__}: {str(e)[:80]})")

# --- cross-encoder rerank sobre tfidf+vet+fuzzy ---
try:
    scorer = criar_scorer_cross_encoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")
    def combo_rerank(r):
        base = combinar([tfidf.pontuar(r, 8), vetorial(r, 8), fuzzy.pontuar(r, 8)], [0.34, 0.33, 0.33])[:8]
        return rerank(r, base, desc_por_sigla, scorer)
    METODOS["combo+rerank"] = combo_rerank
    log("reranker: OK")
except Exception as e:
    log(f"reranker: INDISPONÍVEL ({type(e).__name__}: {str(e)[:80]})")

PCT, GAP = cfg.threshold_pct, cfg.threshold_gap
log(f"\nground-truth: {len(ROTULOS)} pares | roteação: pct>={PCT} gap>={GAP}\n")

# --- métrica primária: corretude vs GTD real ---
try:
    from gate_tdt_real import comparar
    r = comparar("output/LISTA 1 - GTD/TDT.xlsx", "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx")
    log(f"[PRIMARIA] corretude vs GTD real: {r.iguais}/{r.comum} = {r.pct:.1f}%")
except FileNotFoundError:
    log("[PRIMARIA] gate TDT real: arquivos ausentes, pulado")
log("")

log(f"[SECUNDARIA] taxa de decisão e precisão:\n")
log(f"{'método':<20} {'acc@1':>6} {'rec@3':>6} {'decid':>6} {'prec@dec':>9}")
for nome, fn in METODOS.items():
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
    log(f"{nome:<20} {acc1/n:>6.0%} {rec3/n:>6.0%} {decid/n:>6.0%} {prec:>9.0%}")

# --- roteação por consenso/gap dinâmico (cascata do roteador) sobre o combo ---
# usar_consenso=True força a cascata a exercitar o passo 3 (default é False
# em produção desde SP-Cleanup item 2 — precisão baixa, ver linha abaixo).
from dataclasses import replace as _replace
from tdt import roteador
cfg_consenso = _replace(cfg, usar_consenso=True)
acc1 = decid = corr_dec = 0
for desc, esp in ROTULOS:
    r = rec(desc)
    ct, cv, cf = tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)
    combo = combinar([ct, cv, cf], [0.34, 0.33, 0.33])
    if not combo: continue
    if combo[0].sigla == esp: acc1 += 1
    votos = {"tfidf": ct, "vetorial": cv, "fuzzy": cf}
    out = roteador.rotear(_replace(r, candidatos=tuple(combo)), cfg_consenso, votos=votos)
    if out.status == "decidido":
        decid += 1
        if out.sigla_sinal == esp: corr_dec += 1
n = len(ROTULOS)
log(f"{'combo+consenso':<20} {acc1/n:>6.0%} {'':>6} {decid/n:>6.0%} {(corr_dec/decid if decid else 0):>9.0%}")

header = f"# benchmark {datetime.datetime.now():%Y-%m-%d %H:%M}\n"
open("bench/resultados/benchmark.log", "w", encoding="utf-8").write(header + "\n".join(LOG))
