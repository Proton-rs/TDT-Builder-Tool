"""Calibração: processa um input real uma vez e varre thresholds/pesos.

Uso: PYTHONPATH=src python scripts/calibrar.py docs/input_nao_homogeneo_1.xlsx
"""
import sys, warnings, logging
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)

import faiss, numpy as np, openpyxl
from tdt.config import Config
from tdt.analise_colunas import analisar, normalizar_emb
from tdt.normalizador import canonizar
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.dados.encoder import criar_encoder
from tdt.identificador import classificar, ler_rows
from tdt.estruturador import estruturar
from tdt.scoring.tfidf import ScorerTFIDF
from tdt.contracts import Candidato
from tdt.scoring import mescla
from tdt import motor_regras

inp = sys.argv[1] if len(sys.argv) > 1 else "docs/input_nao_homogeneo_1.xlsx"
cfg = Config()
enc = criar_encoder(cfg.modelo_embedding)
lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v1.xlsx")
corpus = [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.discretos if s.descricao]
siglas = [s for s, _ in corpus]
ref = normalizar_emb(enc([d for _, d in corpus]))   # também serve de ref p/ colunas
tfidf = ScorerTFIDF.construir(corpus)
index = faiss.IndexFlatIP(ref.shape[1]); index.add(ref)

wb = openpyxl.load_workbook(inp, read_only=True, data_only=True)
rota = classificar(wb, override="nao-homogeneo")
print(f"sheets de dados: {len(rota.sheets_dados)}")

recs = []
sem_desc = 0
for sn in rota.sheets_dados:
    rows = ler_rows(wb[sn])
    mapa = analisar(rows, enc, ref)
    if "descricao" not in mapa.colunas:
        sem_desc += 1
        continue
    for r in estruturar(rows, mapa, sheet_name=sn, config=cfg):
        if r.tipo_sinal.categoria != "Analog":
            recs.append(r)
wb.close()
print(f"sheets sem coluna descrição: {sem_desc} | sinais discretos: {len(recs)}")

# batch vetorial: embeda todas as descrições de uma vez
descs = [r.descricoes.normalizada for r in recs]
q = normalizar_emb(enc(descs))
S, I = index.search(q, cfg.k_vizinhos)

def candidatos(i, rec):
    vet = [Candidato(siglas[j], max(0.0, float(s)), "vetorial") for s, j in zip(S[i], I[i]) if j != -1]
    tf = tfidf.pontuar(rec, k=cfg.k_vizinhos)
    return vet, tf

# pré-computa candidatos mesclados+regras para cada peso
def avaliar(peso_tf, peso_vet, pct, gap):
    c = Config(peso_tfidf=peso_tf, peso_vetorial=peso_vet)
    dec = rev = 0
    amostra = []
    for i, rec in enumerate(recs):
        vet, tf = candidatos(i, rec)
        fund = motor_regras.aplicar(rec, mescla.mesclar(tf, vet, c))
        fund = sorted(fund, key=lambda x: x.score, reverse=True)
        top = fund[0].score if fund else 0
        g = top - (fund[1].score if len(fund) > 1 else 0)
        if top >= pct and g >= gap:
            dec += 1
            if len(amostra) < 10:
                amostra.append((fund[0].sigla, round(top, 2), rec.descricoes.bruta[:42]))
        else:
            rev += 1
    return dec, rev, amostra

print("\n=== VARREDURA (peso_tf/peso_vet, pct, gap) ===")
for pt, pv in [(0.5, 0.5), (0.6, 0.4), (0.7, 0.3)]:
    for pct, gap in [(0.70, 0.15), (0.55, 0.10), (0.45, 0.08), (0.40, 0.05)]:
        d, r, _ = avaliar(pt, pv, pct, gap)
        print(f"  tf={pt} vet={pv} pct={pct} gap={gap}: decididos={d} revisão={r} taxa={d/(d+r):.0%}")

print("\n=== amostra decididos (tf=0.6 vet=0.4 pct=0.45 gap=0.08) ===")
_, _, amostra = avaliar(0.6, 0.4, 0.45, 0.08)
for sig, sc, desc in amostra:
    print(f"  {sig:<7} {sc}  <- {desc}")
