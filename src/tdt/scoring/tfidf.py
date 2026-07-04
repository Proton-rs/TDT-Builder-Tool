"""Scorer TF-IDF contra as descrições da lista padrão (o gabarito de respostas).

Vetoriza a lista padrão e compara a descrição normalizada do sinal por cosseno.

ponytail: por ora só a análise contra a lista padrão. As análises global e por
sheet do diagrama (ponderar siglas raras / comuns) entram quando medirmos que
melhoram a decisão — não antes.
"""

from __future__ import annotations

import pickle
from pathlib import Path

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
        # Lista padrão tem sigla com múltiplas linhas de descrição (variantes
        # NA/NF, sinônimos) -- sem isso, a mesma sigla apareceria 2x no topo
        # (uma por linha) e `mescla.mesclar` soma por sigla, contando a mesma
        # sigla em dobro e distorcendo a fusão. Mantém só o melhor score por sigla.
        melhor: dict[str, float] = {}
        for i, sigla in enumerate(self._siglas):
            if float(sims[i]) > melhor.get(sigla, float("-inf")):
                melhor[sigla] = float(sims[i])
        ordenados = sorted(melhor.items(), key=lambda kv: kv[1], reverse=True)[:k]
        return [Candidato(sigla, score, "tfidf") for sigla, score in ordenados]

    def salvar(self, path: str | Path) -> None:
        """Serializa vetorizador + matriz fitados (cache em disco)."""
        data = {"vectorizer": self._vectorizer, "matriz": self._matriz, "siglas": self._siglas}
        Path(path).write_bytes(pickle.dumps(data))

    @classmethod
    def carregar(cls, path: str | Path) -> "ScorerTFIDF":
        data = pickle.loads(Path(path).read_bytes())
        return cls(data["vectorizer"], data["matriz"], data["siglas"])
