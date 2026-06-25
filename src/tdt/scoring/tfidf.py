"""Scorer TF-IDF contra as descrições da lista padrão (o gabarito de respostas).

Vetoriza a lista padrão e compara a descrição normalizada do sinal por cosseno.

ponytail: por ora só a análise contra a lista padrão. As análises global e por
sheet do diagrama (ponderar siglas raras / comuns) entram quando medirmos que
melhoram a decisão — não antes.
"""

from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from tdt.contracts import Candidato, SignalRecord

# mantém siglas alfanuméricas curtas como "67N", "DJ"
_TOKEN = r"(?u)\b\w+\b"


class ScorerTFIDF:
    def __init__(self, vectorizer, matriz, siglas: list[str]):
        self._vectorizer = vectorizer
        self._matriz = matriz
        self._siglas = siglas

    @classmethod
    def construir(cls, sinais: list[tuple[str, str]]) -> "ScorerTFIDF":
        siglas = [s for s, _ in sinais]
        descricoes = [d for _, d in sinais]
        vec = TfidfVectorizer(token_pattern=_TOKEN, lowercase=True)
        matriz = vec.fit_transform(descricoes)
        return cls(vec, matriz, siglas)

    def pontuar(self, rec: SignalRecord, k: int = 5) -> list[Candidato]:
        q = self._vectorizer.transform([rec.descricoes.normalizada])
        sims = cosine_similarity(q, self._matriz)[0]
        ordem = sims.argsort()[::-1][:k]
        return [Candidato(self._siglas[i], float(sims[i]), "tfidf") for i in ordem]
