"""Encoder de produção — wrapper fino do SentenceTransformer.

ponytail: wrapper de biblioteca; testado pelo uso real, não por unit test
(carregar o modelo é lento e baixa ~120MB). Os módulos que consomem usam
encoder injetado, então são testados com fake. Import de
sentence_transformers no topo do módulo (não mais lazy-load) — necessário
pro unittest.mock.patch do teste de device funcionar; o lru_cache já evita
reinstanciar o modelo, então o custo de import antecipado é desprezível
comparado ao load do modelo em si.
"""

from __future__ import annotations

import os
from functools import lru_cache

# ponytail: HF Hub faz round-trip online a cada SentenceTransformer(...) p/
# checar versão, mesmo com o modelo já em cache local (~85s medidos vs <1s
# offline). setdefault permite religar online (HF_HUB_OFFLINE=0) p/ baixar
# modelo novo.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer


@lru_cache(maxsize=2)
def _modelo(nome: str, device: str | None):
    return SentenceTransformer(nome, device=device)


def criar_encoder(modelo: str, prefixo: str = "", device: str | None = None):
    """Devolve um callable ``list[str] -> ndarray(float32)``.

    ``prefixo`` para modelos e5/instruct (ex.: "query: " / "passage: ").
    ``device`` força "cpu"/"cuda"; ``None`` deixa o sentence-transformers
    autodetectar (usa GPU se disponível, sem regressão em máquina sem GPU).
    """

    def encode(textos: list[str]) -> np.ndarray:
        ts = [prefixo + t for t in textos] if prefixo else textos
        return np.asarray(_modelo(modelo, device).encode(ts), dtype="float32")

    return encode


@lru_cache(maxsize=2)
def _cross_encoder(nome: str):
    return CrossEncoder(nome)


def criar_scorer_cross_encoder(modelo: str):
    """Devolve um scorer ``list[(query, doc)] -> list[float]`` para o reranker."""

    def scorer(pares: list[tuple[str, str]]) -> list[float]:
        return [float(s) for s in _cross_encoder(modelo).predict(pares)]

    return scorer
