"""Varredura de thresholds do roteador (SP-Decision, D1+D2).

Mede, para cada combinação ``(threshold_pct, threshold_gap)``, a taxa de
decisão e a precisão nos decididos sobre o ground-truth (``bench/rotulos.py``),
separado por categoria (``Discrete``/``Analog``) e agregado.

Reaproduz EXATAMENTE a fórmula de decisão do quadrante simples usada em
``bench/benchmark.py`` (linha ~118-135) e em ``tdt.roteador._quadrante``:

    gap = top.score - segundo.score
    decidido = top.score >= threshold_pct AND gap >= threshold_gap

O scorer usado é o bundle de produção ``combo(calib-minmax)`` — tfidf +
vetorial (MiniLM) + fuzzy, mesclados com pesos iguais e calibração minmax por
método (mesma construção de ``bench/benchmark.py``; este script reimporta as
peças, não duplica a lógica de calibração/scoring).

Custo caro (encoder, tfidf, fuzzy) é pago uma vez por par do GT; a varredura
em si é barata (decisão é uma comparação de 2 números por combinação).

Uso: PYTHONPATH=src python scripts/sweep_thresholds.py
Saída: bench/resultados/sweep_thresholds.csv
"""
from __future__ import annotations

import csv
import os
import sys
import warnings
import logging

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)

sys.path.insert(0, "bench")

import faiss
import numpy as np

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

# Grades da spec (D2) — fixas, não calibráveis via CLI (script de diagnóstico).
GRADE_PCT: list[float] = [0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9]
GRADE_GAP: list[float] = [0.0, 0.02, 0.05, 0.08, 0.10, 0.15, 0.20, 0.30]

CSV_PATH = "bench/resultados/sweep_thresholds.csv"


def _montar_lista_padrao() -> ListaPadraoADMS:
    return ListaPadraoADMS.carregar(os.environ.get("LISTA_BENCH", "docs/Pontos Padrao ADMS_v1.xlsx"))


def _mapa_categoria(lp: ListaPadraoADMS) -> dict[str, str]:
    """sigla -> "Discrete" | "Analog", a partir da sheet de origem na lista padrão."""
    mapa: dict[str, str] = {}
    for s in lp.discretos:
        mapa[s.sigla] = "Discrete"
    for s in lp.analogicos:
        mapa[s.sigla] = "Analog"
    return mapa


def _rec(desc: str, cfg: Config) -> SignalRecord:
    return SignalRecord(
        id="x",
        modulo=Modulo("m", "s"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(desc, canonizar(desc, cfg)),
    )


def _combinar_calib(listas, pesos, metodo="minmax") -> list[Candidato]:
    """Mescla calibrada — idêntica a ``bench/benchmark.py:combinar_calib``."""
    acc: dict[str, float] = {}
    for lst, w in zip(listas, pesos):
        if not lst:
            continue
        cal = calibrar([c.score for c in lst], metodo, None)
        for c, sc in zip(lst, cal):
            acc[c.sigla] = acc.get(c.sigla, 0.0) + w * sc
    return sorted((Candidato(s, v, "mix") for s, v in acc.items()), key=lambda c: c.score, reverse=True)


def _construir_scorers(cfg: Config, lp: ListaPadraoADMS):
    """Monta tfidf/vetorial(MiniLM)/fuzzy sobre o corpus da lista padrão.

    Mesma construção de ``bench/benchmark.py`` (corpus = discretos + analógicos
    com descrição, embeddings normalizados em índice FAISS flat-IP).
    """
    corpus = [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.discretos if s.descricao]
    corpus += [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.analogicos if s.descricao]
    siglas = [s for s, _ in corpus]

    enc = criar_encoder(cfg.modelo_embedding)
    ref = normalizar_emb(enc([d for _, d in corpus]))
    index = faiss.IndexFlatIP(ref.shape[1])
    index.add(ref)

    tfidf = ScorerTFIDF.construir(corpus)
    fuzzy = FuzzyMatcher.construir(corpus)

    def vetorial(r: SignalRecord, k: int) -> list[Candidato]:
        q = normalizar_emb(enc([r.descricoes.normalizada]))
        S, I = index.search(q, k)
        return [Candidato(siglas[j], max(0.0, float(s)), "vet") for s, j in zip(S[0], I[0]) if j != -1]

    return tfidf, vetorial, fuzzy


def calcular_top_gap(cfg: Config, lp: ListaPadraoADMS) -> list[tuple[str, str, float, float]]:
    """Para cada par do GT, calcula (sigla_esperada, categoria, top_score, gap) UMA VEZ.

    A decisão de qualquer combinação de thresholds é função só de
    ``(top_score, gap)`` — calcular o bundle combo(calib-minmax) por par é a
    parte cara (encoder/tfidf/fuzzy); a varredura em si reusa este cache.
    """
    cat_por_sigla = _mapa_categoria(lp)
    tfidf, vetorial, fuzzy = _construir_scorers(cfg, lp)

    linhas: list[tuple[str, str, float, float]] = []
    for desc, esperado in ROTULOS:
        r = _rec(desc, cfg)
        cands = _combinar_calib(
            [tfidf.pontuar(r, 5), vetorial(r, 5), fuzzy.pontuar(r, 5)],
            [0.34, 0.33, 0.33],
            "minmax",
        )
        if not cands:
            continue
        top = cands[0]
        segundo = cands[1].score if len(cands) > 1 else 0.0
        gap = top.score - segundo
        categoria = cat_por_sigla.get(esperado, "Discrete")
        correto = top.sigla == esperado
        linhas.append((esperado, categoria, top.score, gap, correto))
    return linhas


def _metricas(linhas, pct: float, gap_min: float) -> tuple[int, int, int]:
    """(n_total, n_decididos, n_corretos_entre_decididos) para um subconjunto de linhas."""
    n = len(linhas)
    decid = corr = 0
    for _, _, top_score, gap, correto in linhas:
        if top_score >= pct and gap >= gap_min:
            decid += 1
            if correto:
                corr += 1
    return n, decid, corr


def main() -> None:
    cfg = Config()
    lp = _montar_lista_padrao()

    print("calculando scores combo(calib-minmax) para todo o GT (uma vez)...")
    linhas_todas = calcular_top_gap(cfg, lp)
    linhas_disc = [l for l in linhas_todas if l[1] == "Discrete"]
    linhas_ana = [l for l in linhas_todas if l[1] == "Analog"]
    print(f"GT: {len(linhas_todas)} pares ({len(linhas_disc)} Discrete, {len(linhas_ana)} Analog)")

    os.makedirs("bench/resultados", exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "categoria", "threshold_pct", "threshold_gap",
            "n", "n_decididos", "n_corretos", "taxa_decisao", "precisao",
        ])
        for pct in GRADE_PCT:
            for gmin in GRADE_GAP:
                for categoria, linhas in (
                    ("Discrete", linhas_disc),
                    ("Analog", linhas_ana),
                    ("Agregado", linhas_todas),
                ):
                    n, decid, corr = _metricas(linhas, pct, gmin)
                    taxa = decid / n if n else 0.0
                    prec = corr / decid if decid else 0.0
                    w.writerow([categoria, pct, gmin, n, decid, corr, f"{taxa:.4f}", f"{prec:.4f}"])

    print(f"sweep gravado em {CSV_PATH}")

    # D1 — diagnóstico dos thresholds atuais (linha de referência, sem sweep)
    print(f"\n--- D1: thresholds atuais (pct={cfg.threshold_pct}, gap={cfg.threshold_gap}) ---")
    for categoria, linhas in (
        ("Discrete", linhas_disc),
        ("Analog", linhas_ana),
        ("Agregado", linhas_todas),
    ):
        n, decid, corr = _metricas(linhas, cfg.threshold_pct, cfg.threshold_gap)
        taxa = decid / n if n else 0.0
        prec = corr / decid if decid else 0.0
        taxa_rev = 1 - taxa
        erro = decid - corr
        print(
            f"{categoria:<10} n={n:<5} decisao={taxa:.0%} revisao={taxa_rev:.0%} "
            f"precisao={prec:.0%} erros(FP)={erro}"
        )


if __name__ == "__main__":
    main()
