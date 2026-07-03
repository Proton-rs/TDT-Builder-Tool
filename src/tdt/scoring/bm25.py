"""Scorer BM25 contra as descrições da lista padrão (alternativa ao TF-IDF cru).

Mesma interface pública de `ScorerTFIDF` (`construir`/`pontuar`/`salvar`/
`carregar`) — drop-in em `_Scorers.tfidf`. Usa `CountVectorizer` (contagens
brutas) + idf BM25 e saturação de frequência de termo (k1, b), em vez de
similaridade de cosseno sobre TF-IDF. Ganho medido em
`docs/superpowers/specs/2026-07-02-spH-resultado-experimento-pesos.md` e
confirmado através do funil completo em `bench/exp_bm25_full.py`.

ponytail: score BM25 não é normalizado para [0, 1] (ao contrário do cosseno
do TF-IDF) — mas todo consumidor em produção calibra via `calibrar_candidatos`
(minmax, `Config.calibracao_por_metodo["tfidf"]`) antes de fundir, então a
escala bruta não vaza para o roteador. Upgrade path: normalizar no próprio
`pontuar` se algum consumidor futuro usar o score sem calibração.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import CountVectorizer

from tdt.contracts import Candidato, SignalRecord

_TOKEN = r"(?u)\b\w+\b"


class ScorerBM25:
    def __init__(self, vectorizer, contagens, siglas: list[str], k1: float = 1.5, b: float = 0.75):
        self._vectorizer = vectorizer
        self._siglas = siglas
        self._k1, self._b = k1, b
        self._contagens = contagens.tocsc()
        self._doc_len = np.asarray(contagens.sum(axis=1)).ravel()
        self._avgdl = float(self._doc_len.mean()) if len(self._doc_len) else 1.0
        df = np.asarray((contagens > 0).sum(axis=0)).ravel()
        n_docs = contagens.shape[0]
        self._idf = np.log(1 + (n_docs - df + 0.5) / (df + 0.5))

    @classmethod
    def construir(cls, sinais: list[tuple[str, str]]) -> "ScorerBM25":
        siglas = [s for s, _ in sinais]
        descricoes = [d for _, d in sinais]
        vec = CountVectorizer(token_pattern=_TOKEN, lowercase=True)
        contagens = vec.fit_transform(descricoes)
        return cls(vec, contagens, siglas)

    def pontuar(self, rec: SignalRecord, k: int = 5) -> list[Candidato]:
        q_counts = self._vectorizer.transform([rec.descricoes.normalizada])
        termos = q_counts.nonzero()[1]
        if len(termos) == 0:
            return []
        k1, b = self._k1, self._b
        scores = np.zeros(len(self._siglas))
        for t in termos:
            col = self._contagens[:, t].toarray().ravel()
            num = col * (k1 + 1)
            den = col + k1 * (1 - b + b * self._doc_len / self._avgdl)
            scores += self._idf[t] * np.divide(num, den, out=np.zeros_like(num, dtype=float), where=den != 0)
        # A lista padrão tem sigla com múltiplas linhas de descrição (variantes
        # NA/NF, sinônimos) -- sem isso, a mesma sigla apareceria 2x no topo
        # (uma por linha) e `mescla.mesclar` soma por sigla, contando a mesma
        # sigla em dobro e distorcendo a fusão. Mantém só o melhor score por sigla.
        melhor: dict[str, float] = {}
        for i, sigla in enumerate(self._siglas):
            if scores[i] > 0 and scores[i] > melhor.get(sigla, 0.0):
                melhor[sigla] = float(scores[i])
        ordenados = sorted(melhor.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [Candidato(sigla, score, "bm25") for sigla, score in ordenados]

    def salvar(self, path: str | Path) -> None:
        """Serializa vetorizador + contagens fitadas (cache em disco)."""
        data = {
            "vectorizer": self._vectorizer, "contagens": self._contagens,
            "siglas": self._siglas, "k1": self._k1, "b": self._b,
        }
        Path(path).write_bytes(pickle.dumps(data))

    @classmethod
    def carregar(cls, path: str | Path) -> "ScorerBM25":
        data = pickle.loads(Path(path).read_bytes())
        return cls(data["vectorizer"], data["contagens"], data["siglas"], data["k1"], data["b"])
