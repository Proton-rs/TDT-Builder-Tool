"""SP-H follow-up: valida o ganho de BM25 medido em exp_pesos.py através do
FUNIL COMPLETO de produção (filtro_preciso, semantica_estados, whitelist,
motor_regras, roteador) — não só a fusão isolada de candidatos.

exp_pesos.py mediu bm25+vet+fuzzy só com `combinar_calib` (proxy). Este
script troca `_Scorers.tfidf` por `ScorerBM25` e chama a MESMA função
`tdt.pipeline._classificar_sinal` usada em produção, com os MESMOS pesos
vigentes (nenhum peso/fusão tocado) — isola só a troca de scorer e confirma
se o ganho sobrevive aos consumidores downstream do score tfidf.

Uso: PYTHONPATH=src python bench/exp_bm25_full.py
"""
import sys, warnings, logging, os
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
sys.path.insert(0, "bench")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from rotulos import ROTULOS
from tdt.config import Config
from tdt.normalizacao.normalizador import canonizar
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.dados.encoder import criar_encoder
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt import pipeline
from tdt.scoring.bm25 import ScorerBM25
from tdt.scoring.tfidf import ScorerTFIDF

cfg = Config()
lp = ListaPadraoADMS.carregar(os.environ.get("LISTA_BENCH", "docs/Pontos Padrao ADMS_v1.xlsx"))
enc = criar_encoder(cfg.modelo_embedding)

# `_construir_scorers` já usa ScorerBM25 em produção (ver pipeline.py) -- para
# a baseline REAL de TF-IDF cru, construímos o bundle e trocamos o slot
# `tfidf` explicitamente por ScorerTFIDF, não o contrário.
corpus_raw = pipeline._corpus(lp, cfg, "Discrete")
disc_bm25 = pipeline._construir_scorers(lp, cfg, enc, "Discrete", cfg)
disc_tfidf = disc_bm25._replace(tfidf=ScorerTFIDF.construir(corpus_raw))


def rec(desc):
    return SignalRecord(
        id="x", modulo=Modulo("m", "s"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(desc, canonizar(desc, cfg)),
    )


def avaliar(scorers, nome):
    acc1 = decid = corr_dec = 0
    n = len(ROTULOS)
    for desc, esp in ROTULOS:
        d = pipeline._classificar_sinal(rec(desc), scorers, lista_padrao=lp)
        cands = d.candidatos
        if cands and cands[0].sigla == esp:
            acc1 += 1
        if d.status == "decidido":
            decid += 1
            if d.sigla_sinal == esp:
                corr_dec += 1
    prec = (corr_dec / decid) if decid else 0
    print(f"{nome:<12} acc@1={acc1/n:.2%} decid={decid/n:.2%} prec@dec={prec:.2%} "
          f"(decididos_corretos={corr_dec} decididos_errados={decid - corr_dec})")


print(f"ground-truth: {len(ROTULOS)} pares | pesos vigentes tfidf={cfg.peso_tfidf} "
      f"vetorial={cfg.peso_vetorial} fuzzy={cfg.peso_fuzzy} (não alterados)\n")
avaliar(disc_tfidf, "tfidf (atual)")
avaliar(disc_bm25, "bm25")
