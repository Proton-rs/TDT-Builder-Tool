"""Calibração: E2 (pesos de mescla) + E4 (calibrador de confiança pós-mescla).

Uso: python scripts/calibrar.py (da raiz do projeto)
Saída: pesos recomendados + params do calibrador de confiança.
"""
import sys, warnings, logging, os, pathlib
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)

_script_dir = pathlib.Path(__file__).resolve().parent
_root = _script_dir.parent
for _p in (str(_root / "src"), _script_dir / "treino", _script_dir / "enriquecer_v5", str(_root / "bench")):
    sys.path.insert(0, str(_p))

import faiss, numpy as np
from tdt.config import Config
from tdt.normalizacao.normalizador import canonizar
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.dados.encoder import criar_encoder
from tdt.scoring.tfidf import ScorerTFIDF
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.scoring.calibracao import calibrar_candidatos, treinar_calibrador_confianca, aplicar_calibrador_confianca
from tdt.scoring import mescla
from tdt.contracts import Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt import motor_regras, roteador
from rotulos import ROTULOS
from mockup import gerar_dataset
from dataclasses import replace as _replace

V2 = "docs/Pontos Padrao ADMS_v2.xlsx"
cfg = Config()
enc = criar_encoder(cfg.modelo_embedding)
lp = ListaPadraoADMS.carregar(V2)
corpus = [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.discretos if s.descricao]
corpus += [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.analogicos if s.descricao]
siglas = [s for s, _ in corpus]

tfidf = ScorerTFIDF.construir(corpus)
ref = np.asarray(enc([d for _, d in corpus]), dtype="float32")
ref = ref / np.linalg.norm(ref, axis=1, keepdims=True)
index = faiss.IndexFlatIP(ref.shape[1]); index.add(ref)
fuzzy = FuzzyMatcher.construir(corpus)

pares_v2 = [(s.descricao, s.sigla) for s in (*lp.discretos, *lp.analogicos) if s.descricao]
print(f"Lista V2: {len(pares_v2)} sinais")
ds_mock = gerar_dataset(pares_v2, niveis=(1, 2, 3, 4, 5), n_variantes=2, seed=0)
print(f"Mockup: {len(ds_mock)} pares | Reais: {len(ROTULOS)} pares")

print("Pré-computando scores...")
def _sc(desc):
    d_norm = canonizar(desc, cfg)
    rec = SignalRecord(id="cal", modulo=Modulo("M", "s"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)), descricoes=Descricoes(desc, d_norm))
    ct = tfidf.pontuar(rec, k=cfg.k_vizinhos)
    q = np.asarray(enc([d_norm]), dtype="float32")
    q = q / np.linalg.norm(q)
    S, I = index.search(q, cfg.k_vizinhos)
    cv = [Candidato(siglas[j], max(0.0, float(s)), "vet") for s, j in zip(S[0], I[0]) if j != -1]
    cf = fuzzy.pontuar(rec, k=cfg.k_vizinhos)
    return ct, cv, cf

PRE = [(*_sc(desc), esp) for desc, esp, _ in ds_mock]
PRE += [(*_sc(desc), esp) for desc, esp in ROTULOS]
print(f"Total amostras: {len(PRE)}")

def _rec_vazio():
    return SignalRecord(id="cal", modulo=Modulo("M", "s"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)), descricoes=Descricoes("", ""))

def _score(ct, cv, cf, pte, pve, pfu):
    ct2 = calibrar_candidatos(ct, "minmax", None)
    cv2 = calibrar_candidatos(cv, "minmax", None)
    cf2 = calibrar_candidatos(cf, "minmax", None)
    return mescla.mesclar([(ct2, pte), (cv2, pve), (cf2, pfu)])

# --- E2: Grid search (pesos) ---
print("\n=== E2: Busca de pesos ===")
best = None; best_acc = -1
for pt in [0.05, 0.15, 0.25, 0.34, 0.50, 0.60, 0.70, 0.80, 0.90]:
    for pv in [0.05, 0.15, 0.25, 0.33, 0.50]:
        pf = round(1.0 - pt - pv, 2)
        if pf < 0.0: continue
        acertos = total = 0
        for ct, cv, cf, esp in PRE:
            total += 1
            fund = _score(ct, cv, cf, pt, pv, pf)
            if fund and fund[0].sigla == esp: acertos += 1
        acc = acertos / total * 100
        print(f"  tf={pt:.2f} vet={pv:.2f} fuzzy={pf:.2f}  acc={acc:.1f}%", end="")
        if acertos > best_acc:
            best_acc = acertos; best = (pt, pv, pf); print(" *", end="")
        print()

pte, pve, pfu = best
print(f"\nMelhores pesos: tf={pte:.2f} vet={pve:.2f} fuzzy={pfu:.2f}  acc={best_acc}/{total} ({best_acc/total*100:.1f}%)")

# --- E4: Treinar calibrador de confiança ---
print("\n=== E4: Treinar calibrador de confiança (Platt) ===")
scores_merged = []
acertos = []
for ct, cv, cf, esp in PRE:
    fund = _score(ct, cv, cf, pte, pve, pfu)
    if fund:
        scores_merged.append(fund[0].score)
        acertos.append(fund[0].sigla == esp)

params = treinar_calibrador_confianca(scores_merged, acertos, "platt")
coef = params["params"]["coef_"]
intercept = params["params"]["intercept_"]
print(f"  Platt: coef_={coef:.4f}  intercept_={intercept:.4f}")

# Evaluar calibração: binned confidence vs accuracy
from collections import Counter
bins = np.linspace(0, 1, 11)
correct_counts = Counter()
total_counts = Counter()
for s, a in zip(scores_merged, acertos):
    bi = min(int(s * 10), 9)
    total_counts[bi] += 1
    if a: correct_counts[bi] += 1

print(f"\n  {'score':<8} {'n':>5} {'acc_real':>8} {'conf_calib':>10}")
for bi in range(10):
    lo, hi = bins[bi], bins[bi+1]
    n = total_counts.get(bi, 0)
    if n < 10: continue
    acc_real = correct_counts.get(bi, 0) / n
    mid = (lo + hi) / 2
    conf_calib = aplicar_calibrador_confianca(mid, params)
    print(f"  [{lo:.1f}-{hi:.1f}) {n:>5} {acc_real:>8.3f} {conf_calib:>10.3f}")

# ECE
ece = sum(abs(correct_counts.get(bi,0)/(total_counts.get(bi,1)) - aplicar_calibrador_confianca((bins[bi]+bins[bi+1])/2, params)) * total_counts.get(bi,0) for bi in range(10)) / sum(total_counts.values())
print(f"\n  ECE (Expected Calibration Error): {ece:.4f}")
print(f"\n  Sem calibrador: score médio correto={np.mean([s for s,a in zip(scores_merged, acertos) if a]):.3f}  score médio errado={np.mean([s for s,a in zip(scores_merged, acertos) if not a]):.3f}")
print(f"  Com calibrador: conf média correta={np.mean([aplicar_calibrador_confianca(s, params) for s,a in zip(scores_merged, acertos) if a]):.3f}  conf média errada={np.mean([aplicar_calibrador_confianca(s, params) for s,a in zip(scores_merged, acertos) if not a]):.3f}")

# Efeito no roteador: amostra calibrada vs raw
print(f"\n=== E4: Impacto no roteador ===")
for nome, usar_calib in [("sem calibrador", False), ("com calibrador", True)]:
    cfg_test = Config(peso_tfidf=pte, peso_vetorial=pve, peso_fuzzy=pfu,
        confianca_calibrador= params if usar_calib else cfg.confianca_calibrador)
    a = d = c = fp = 0
    for ct, cv, cf, esp in PRE:
        fund = _score(ct, cv, cf, pte, pve, pfu)
        if usar_calib:
            fund = [_replace(c, score=aplicar_calibrador_confianca(c.score, params)) for c in fund]
        rec = _rec_vazio()
        com_regras = motor_regras.aplicar(rec, fund, cfg_test)
        rec2 = _replace(rec, candidatos=tuple(com_regras))
        out = roteador.rotear(rec2, cfg_test)
        if out.status == "decidido":
            d += 1
            if out.sigla_sinal == esp: c += 1; a += 1
            else: fp += 1
        elif com_regras and com_regras[0].sigla == esp: a += 1
    n = len(PRE)
    print(f"  {nome:<20}  acc={a/n*100:.1f}% decid={d/n*100:.1f}% fp={fp}")

print(f"\nCONFIG RECOMENDADA:")
print(f"  peso_tfidf={pte:.2f}, peso_vetorial={pve:.2f}, peso_fuzzy={pfu:.2f}")
import json
print(f"  confianca_calibrador={json.dumps(params)}")
