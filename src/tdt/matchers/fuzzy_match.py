"""Matcher fuzzy: rapidfuzz token_set_ratio sobre as descrições ADMS, com boost
quando a sigla aparece literal na descrição (códigos SCADA costumam aparecer
no texto: "Diferencial (87)", "Chave 43TC", "SF6").

Mira precisão sem modelo. fonte="fuzzy".
"""

from __future__ import annotations

import pickle
from pathlib import Path

from rapidfuzz import fuzz

from tdt.contracts import Candidato, SignalRecord

_BOOST_SIGLA = 0.25


class FuzzyMatcher:
    def __init__(self, corpus: list[tuple[str, str]]):
        self._corpus = corpus  # (sigla, descricao_canonizada)

    @classmethod
    def construir(cls, corpus: list[tuple[str, str]]) -> "FuzzyMatcher":
        return cls(list(corpus))

    def pontuar(self, rec: SignalRecord, k: int = 5) -> list[Candidato]:
        texto = rec.descricoes.normalizada
        tokens = set(texto.split())
        cands = []
        for sigla, desc in self._corpus:
            base = fuzz.token_set_ratio(texto, desc) / 100.0
            boost = _BOOST_SIGLA if sigla.upper() in tokens else 0.0
            cands.append(Candidato(sigla, min(1.0, base + boost), "fuzzy"))
        cands.sort(key=lambda c: c.score, reverse=True)
        return cands[:k]

    def salvar(self, path: str | Path) -> None:
        """Serializa o corpus (não há fit custoso aqui; só evita reler/reconstruir a lista)."""
        Path(path).write_bytes(pickle.dumps(self._corpus))

    @classmethod
    def carregar(cls, path: str | Path) -> "FuzzyMatcher":
        corpus = pickle.loads(Path(path).read_bytes())
        return cls.construir(corpus)
