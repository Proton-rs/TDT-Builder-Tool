"""Cache em disco dos scorers (tfidf+fuzzy+índice vetorial) por hash do corpus.

Construir os scorers (fit TF-IDF, indexar FAISS, montar o fuzzy) é custoso e
hoje roda em toda execução do pipeline, mesmo quando a lista padrão ADMS não
mudou. Aqui cacheamos o resultado em disco, indexado pelo hash do corpus
(siglas+descrições) + identificador do modelo de embedding: mesma lista
padrão e mesmo modelo -> reusa o cache sem nunca chamar `construir`; lista ou
modelo mudou (ou cache ausente/corrompido) -> reconstrói do zero e grava o
novo cache.

Transparente por design: qualquer falha ao ler o cache (arquivo ausente,
corrompido, versão incompatível) cai no caminho de reconstrução normal — o
cache nunca pode quebrar o pipeline.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable, NamedTuple

from tdt.dados.indice_vetorial import IndiceVetorial
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.scoring.bm25 import ScorerBM25

_ARQ_TFIDF = "tfidf.pkl"
_ARQ_FUZZY = "fuzzy.pkl"


def _hash_corpus(corpus: list[tuple[str, str]], modelo_embedding: str) -> str:
    """Hash do corpus + identificador do modelo de embedding.

    Incluir `modelo_embedding` é essencial: o índice FAISS cacheado contém
    vetores gerados por um encoder específico. Se o usuário troca de modelo
    mas o corpus (siglas+descrições) não muda, o hash precisa mudar mesmo
    assim — senão um cache hit devolveria vetores do encoder ANTIGO para uso
    com o encoder NOVO, produzindo scores vetoriais incoerentes sem erro.
    """
    h = hashlib.sha256()
    h.update(f"{modelo_embedding}\x1d".encode("utf-8"))
    for sigla, desc in corpus:
        h.update(f"{sigla}\x1f{desc}\x1e".encode("utf-8"))
    return h.hexdigest()


def _tentar_carregar(base: Path, encoder):
    """Tenta montar tfidf/fuzzy/indice a partir do cache em `base`.

    None se algo faltar ou corromper — sinaliza ao chamador para reconstruir.
    """
    try:
        tfidf = ScorerBM25.carregar(base / _ARQ_TFIDF)
        fuzzy = FuzzyMatcher.carregar(base / _ARQ_FUZZY)
        indice = IndiceVetorial.carregar(base, encoder)
    except Exception:
        # ponytail: catch-all deliberado — qualquer corrupção de cache (pickle
        # truncado, faiss ausente, json inválido) deve cair para reconstrução,
        # nunca propagar. Upgrade path: logar a exceção via Auditoria se algum
        # dia precisarmos diagnosticar caches corrompidos com frequência.
        return None
    return tfidf, fuzzy, indice


class _ScorersCacheaveis(NamedTuple):
    """Subconjunto cacheável de `pipeline._Scorers` (sem `config`, que é runtime)."""

    tfidf: object
    fuzzy: object
    indice: object


def carregar_ou_construir(
    diretorio: str | Path,
    corpus: list[tuple[str, str]],
    construir: Callable[[], _ScorersCacheaveis],
    encoder,
    modelo_embedding: str,
) -> _ScorersCacheaveis:
    """Devolve tfidf/fuzzy/indice do cache em `diretorio` se o hash do corpus casar.

    Em cache hit, `construir()` nunca é chamado — esse é o ponto da função:
    pular o fit do TF-IDF, o índice FAISS e o fuzzy quando o corpus
    (siglas+descrições da lista padrão) não mudou desde a última execução.
    Em cache miss (ou cache corrompido), chama `construir()` e grava o
    resultado em disco para a próxima execução.

    `modelo_embedding` entra no hash junto com o corpus: trocar de modelo de
    sentence-transformer invalida o cache automaticamente (cai num diretório
    diferente), mesmo que o corpus permaneça idêntico.
    """
    h = _hash_corpus(corpus, modelo_embedding)
    base = Path(diretorio) / h

    if base.exists():
        carregado = _tentar_carregar(base, encoder)
        if carregado is not None:
            tfidf, fuzzy, indice = carregado
            return _ScorersCacheaveis(tfidf=tfidf, fuzzy=fuzzy, indice=indice)

    scorers = construir()
    base.mkdir(parents=True, exist_ok=True)
    try:
        scorers.tfidf.salvar(base / _ARQ_TFIDF)
        scorers.fuzzy.salvar(base / _ARQ_FUZZY)
        scorers.indice.salvar(base)
    except Exception:
        # ponytail: falha ao gravar cache (disco cheio, permissão) não deve
        # derrubar o pipeline — os scorers já construídos seguem válidos em
        # memória, só não persistem para a próxima execução.
        pass
    return scorers
