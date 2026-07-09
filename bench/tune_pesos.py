"""Tuning dos pesos de mescla em 2 estagios.

Estagio 1 (barato): grid simplex passo 0.05 (231 combos) sobre candidatos
cacheados por metodo (tfidf/vetorial/fuzzy sao independentes dos pesos —
computa 1x, mescla N vezes). Metrica: prec@decididos + acc@1 no ROTULOS,
roteacao por threshold_pct/threshold_gap da Config (igual exp_pesos.py).

Estagio 2 (caro): top-3 combos do estagio 1 + o peso atual rodam o pipeline
real (bench/reprocessar_lista1.py via env TDT_PESOS) e comparam no gate_tdt_real
contra o TDT real GTD. So RECOMENDA atualizar a Config se o melhor combo superar
o atual NO GATE (estagio 2), nunca so pelo estagio 1.

Uso: PYTHONPATH=src python bench/tune_pesos.py
Saida: bench/resultados/tune_pesos.txt
"""
import sys, warnings, logging, datetime, os, subprocess
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
sys.path.insert(0, "bench")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

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

# --- SETUP: copiado verbatim de bench/exp_pesos.py --------------------------
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

PESO_ATUAL = (cfg.peso_tfidf, cfg.peso_vetorial, cfg.peso_fuzzy)
# --- fim do setup copiado ----------------------------------------------------

PCT, GAP = cfg.threshold_pct, cfg.threshold_gap
ATUAL = PESO_ATUAL

# Estagio 1: cache dos candidatos por metodo (pesos nao afetam os scores)
cache = [(tfidf.pontuar(rec(d), 5), vetorial(rec(d), 5), fuzzy.pontuar(rec(d), 5), esp)
         for d, esp in ROTULOS]

def simplex(passo=0.05):
    n = round(1 / passo)
    for i in range(n + 1):
        for j in range(n + 1 - i):
            yield (round(i * passo, 2), round(j * passo, 2), round(1 - (i + j) * passo, 2))

def avaliar(pesos):
    acc1 = decid = corr = 0
    for t_c, v_c, f_c, esp in cache:
        cands = combinar_calib([t_c, v_c, f_c], pesos, "minmax")
        if not cands:
            continue
        top = cands[0]
        if top.sigla == esp:
            acc1 += 1
        gap = top.score - (cands[1].score if len(cands) > 1 else 0)
        if top.score >= PCT and gap >= GAP:
            decid += 1
            if top.sigla == esp:
                corr += 1
    n = len(ROTULOS)
    prec = corr / decid if decid else 0.0
    return (prec, acc1 / n, decid / n)

log(f"# tune_pesos {datetime.datetime.now():%Y-%m-%d %H:%M}")
log(f"pesos atuais: {ATUAL} | roteacao pct>={PCT} gap>={GAP} | ROTULOS={len(ROTULOS)}\n")

resultados = []
for pesos in simplex():
    prec, acc1, decid = avaliar(pesos)
    resultados.append((prec, acc1, decid, pesos))
resultados.sort(reverse=True)

log(f"{'#':>3} {'prec@dec':>9} {'acc@1':>7} {'decid':>7}  pesos")
for i, (prec, acc1, decid, pesos) in enumerate(resultados[:10], 1):
    log(f"{i:>3} {prec:>9.2%} {acc1:>7.2%} {decid:>7.2%}  {pesos}")
prec_at, acc_at, dec_at = avaliar(ATUAL)
log(f"\natual {ATUAL}: prec@dec={prec_at:.2%} acc@1={acc_at:.2%} decid={dec_at:.2%}")

# Estagio 2: top-3 distintos + atual, valida no GATE real
from gate_tdt_real import comparar
REAL = "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx"
NOSSO = "output/LISTA 1 - GTD/TDT.xlsx"
candidatos = []
for _, _, _, pesos in resultados:
    if pesos not in candidatos:
        candidatos.append(pesos)
    if len(candidatos) >= 3:
        break
if ATUAL not in candidatos:
    candidatos.append(ATUAL)

log("\n=== ESTAGIO 2: gate real (reprocessa pipeline por combo) ===")
gate = {}
for pesos in candidatos:
    env = dict(os.environ, TDT_PESOS=",".join(str(p) for p in pesos), PYTHONPATH="src")
    subprocess.run([sys.executable, "bench/reprocessar_lista1.py"], env=env, check=True,
                   stdout=subprocess.DEVNULL)
    r = comparar(NOSSO, REAL)
    gate[pesos] = (r.comum, r.iguais, r.pct)
    tag = " (ATUAL)" if pesos == ATUAL else ""
    log(f"gate pesos={pesos}{tag}: comum={r.comum} iguais={r.iguais} pct={r.pct:.2f}")

melhor = max(candidatos, key=lambda p: gate[p][1])  # mais 'iguais' no gate
log(f"\nMELHOR no gate: {melhor} -> iguais={gate[melhor][1]} pct={gate[melhor][2]:.2f}")
if gate[melhor][1] > gate[ATUAL][1]:
    log(f"RECOMENDA atualizar Config: {ATUAL} -> {melhor} (gate {gate[ATUAL][2]:.2f}% -> {gate[melhor][2]:.2f}%)")
else:
    log(f"MANTER atual: nenhum combo supera {ATUAL} no gate (atual iguais={gate[ATUAL][1]}).")

os.makedirs("bench/resultados", exist_ok=True)
open("bench/resultados/tune_pesos.txt", "w", encoding="utf-8").write("\n".join(LOG))
