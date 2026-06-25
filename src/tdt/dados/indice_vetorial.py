"""Índice vetorial FAISS sobre as descrições da lista padrão.

Encoder injetado (``list[str] -> ndarray``) para testabilidade — em produção é
um SentenceTransformer; em teste, um fake determinístico. Vetores são
L2-normalizados e indexados com produto interno (= cosseno). Persistível em
disco; rebuild só quando o conteúdo muda (hash das siglas+descrições).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable

import faiss
import numpy as np

Encoder = Callable[[list[str]], np.ndarray]

_ARQ_INDEX = "indice.faiss"
_ARQ_META = "meta.json"


def _normalizar(m: np.ndarray) -> np.ndarray:
    m = np.ascontiguousarray(m, dtype="float32")
    faiss.normalize_L2(m)
    return m


def _hash(sinais: list[tuple[str, str]]) -> str:
    h = hashlib.sha256()
    for sigla, desc in sinais:
        h.update(f"{sigla}\x1f{desc}\x1e".encode("utf-8"))
    return h.hexdigest()


class IndiceVetorial:
    def __init__(
        self,
        index,
        siglas: list[str],
        encoder: Encoder,
        hash_: str,
        encoder_consulta: Encoder | None = None,
        centroide: np.ndarray | None = None,
    ):
        # ``encoder`` indexa o corpus (passagem). ``encoder_consulta`` codifica
        # a query — distinto p/ modelos e5 assimétricos ("passage:" vs "query:").
        # Ausente => simétrico: a busca usa o mesmo encoder do corpus.
        self._index = index
        self._siglas = siglas
        self._encoder = encoder
        self._encoder_consulta = encoder_consulta or encoder
        self.hash = hash_
        self._centroide = centroide

    @classmethod
    def construir(
        cls,
        sinais: list[tuple[str, str]],
        encoder: Encoder,
        encoder_consulta: Encoder | None = None,
    ) -> "IndiceVetorial":
        """Constrói o índice. ``encoder`` codifica as passagens (corpus).

        Passe ``encoder_consulta`` p/ e5 assimétrico (prefixo "query:" distinto
        do "passage:" do corpus). Omitido => simétrico (retrocompat).
        """
        siglas = [s for s, _ in sinais]
        descricoes = [d for _, d in sinais]
        vecs = _normalizar(encoder(descricoes))
        index = faiss.IndexFlatIP(vecs.shape[1])
        index.add(vecs)
        centroide = _normalizar(vecs.mean(axis=0, keepdims=True))
        return cls(index, siglas, encoder, _hash(sinais), encoder_consulta, centroide)

    def vetores(self) -> np.ndarray:
        """Embeddings do corpus já indexado (evita re-encodar o mesmo texto)."""
        return self._index.reconstruct_n(0, self._index.ntotal)

    def buscar(self, texto: str, k: int = 5) -> list[tuple[str, float]]:
        q = _normalizar(self._encoder_consulta([texto]))
        k = min(k, len(self._siglas))
        scores, idxs = self._index.search(q, k)
        return [(self._siglas[i], float(s)) for s, i in zip(scores[0], idxs[0]) if i != -1]

    def afinidade_centroide(self, texto: str) -> float:
        q = _normalizar(self._encoder_consulta([texto]))
        return float((q @ self._centroide.T)[0, 0])

    def salvar(self, diretorio: str | Path) -> None:
        d = Path(diretorio)
        d.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(d / _ARQ_INDEX))
        (d / _ARQ_META).write_text(
            json.dumps(
                {
                    "siglas": self._siglas,
                    "hash": self.hash,
                    "centroide": self._centroide.tolist(),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    @classmethod
    def carregar(
        cls,
        diretorio: str | Path,
        encoder: Encoder,
        encoder_consulta: Encoder | None = None,
    ) -> "IndiceVetorial":
        d = Path(diretorio)
        index = faiss.read_index(str(d / _ARQ_INDEX))
        meta = json.loads((d / _ARQ_META).read_text(encoding="utf-8"))
        centroide = np.asarray(meta["centroide"], dtype="float32")
        return cls(index, meta["siglas"], encoder, meta["hash"], encoder_consulta, centroide)
