"""Localiza colunas-chave de uma sheet por CONTEÚDO, não por nome de cabeçalho.

As listas não-homogêneas nomeiam colunas de formas diferentes (e às vezes nem
têm os mesmos campos). Então:

- **descrição**: coluna cujos valores têm maior similaridade média de embedding
  com as descrições da lista padrão ADMS (``ref_emb``). É a ideia central.
- **índice**: coluna com padrão de inteiros (quase) sequenciais — determinístico.
- **tipo**: coluna cujos valores casam o vocabulário {Analógico, Comando, Digital}.

O módulo NÃO é detectado por coluna (ambíguo com IED) — é constante por sheet e
vem do nome da sheet (responsabilidade do chamador). O header é detectado por
densidade (início do bloco estruturado), sem keywords.
"""

from __future__ import annotations

import re
import unicodedata

import faiss
import numpy as np

from tdt.contracts import MapaColunas
from tdt.vocabulario_tipo import CODIGOS_TIPO, VOCAB as _TIPO_VOCAB

_INT = re.compile(r"^-?\d+$")


def normalizar_emb(m: np.ndarray) -> np.ndarray:
    m = np.ascontiguousarray(m, dtype="float32")
    faiss.normalize_L2(m)
    return m


def _norm(v) -> str:
    if v is None:
        return ""
    s = "".join(
        c for c in unicodedata.normalize("NFKD", str(v)) if not unicodedata.combining(c)
    )
    return " ".join(s.upper().split())


_JANELA_HEADER = 20  # o header fica perto do topo


def _header_por_densidade(rows: list[tuple]) -> int:
    """Header = primeira linha que atinge ~80% da densidade máxima do topo.

    Robusto a dois casos: sheet densa (header e dados cheios — o header vem
    antes, então "primeiro" o pega) e sheet esparsa (dados preenchem poucas
    colunas — o header de rótulos é a linha mais densa). Metadados no topo
    ficam abaixo do limiar.
    """
    if not rows:
        return 0
    janela = rows[:_JANELA_HEADER]
    contagem = [sum(1 for c in r if _norm(c)) for r in janela]
    mx = max(contagem)
    if mx == 0:
        return 0
    alvo = 0.8 * mx
    for i, c in enumerate(contagem):
        if c >= alvo:
            return i
    return 0


def _valores_coluna(rows: list[tuple], c: int, inicio: int) -> list[str]:
    out = []
    for r in rows[inicio:]:
        if c < len(r):
            v = "" if r[c] is None else str(r[c]).strip()
            if v:
                out.append(v)
    return out


def _ncols(rows: list[tuple]) -> int:
    return max((len(r) for r in rows), default=0)


def _col_descricao(rows, inicio, ncols, encoder, ref_emb) -> int | None:
    """Coluna cujos valores casam a lista ADMS, ponderada pela DIVERSIDADE.

    Descrições são quase únicas por linha; colunas de metadado (Lógica/Origem)
    repetem poucos valores. A média de similaridade sozinha premia colunas de
    valores idênticos — por isso multiplicamos por sqrt(distintos/total).

    Batch: uma única chamada ao encoder para as amostras de TODAS as colunas
    candidatas, em vez de uma chamada por coluna — sheets com 200+ colunas
    (comuns em listas não-homogêneas largas) levavam minutos só nesta etapa.
    """
    import math

    candidatos: list[tuple[int, list[str]]] = []
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        textos = [v for v in vals if any(ch.isalpha() for ch in v)]
        if len(textos) < 2:
            continue
        candidatos.append((c, textos[:200]))

    if not candidatos:
        return None

    # canonizar (sem config aqui: normalização leve) alinha com ref ADMS
    todos_textos = [_norm(v) for _, amostra in candidatos for v in amostra]
    todos_emb = normalizar_emb(encoder(todos_textos))

    melhor, melhor_score = None, -1.0
    offset = 0
    for c, amostra in candidatos:
        n = len(amostra)
        emb = todos_emb[offset:offset + n]
        offset += n
        sims = emb @ ref_emb.T
        sim_media = float(sims.max(axis=1).mean()) if sims.size else 0.0
        diversidade = len(set(amostra)) / len(amostra)
        # descrições são linguagem natural (multi-palavra); códigos/flags têm 1 token
        avg_palavras = sum(len(v.split()) for v in amostra) / len(amostra)
        score = sim_media * (diversidade ** 0.5) * math.log1p(avg_palavras)
        if score > melhor_score:
            melhor, melhor_score = c, score
    return melhor


def _col_indice(rows, inicio, ncols) -> int | None:
    melhor, melhor_score = None, 0.0
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        if not vals:
            continue
        ints = [int(v) for v in vals if _INT.match(v)]
        frac = len(ints) / len(vals)
        crescente = sum(1 for a, b in zip(ints, ints[1:]) if b > a)
        mono = (crescente / (len(ints) - 1)) if len(ints) > 1 else 0.0
        score = frac * (0.5 + 0.5 * mono)
        if score > melhor_score:
            melhor, melhor_score = c, score
    return melhor


def _col_tipo(rows, inicio, ncols) -> int | None:
    melhor, melhor_score = None, 0.0
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        if not vals:
            continue
        normalizados = [_norm(v) for v in vals]
        casam_palavra = sum(1 for n in normalizados if any(k in n for k in _TIPO_VOCAB))
        score_palavra = casam_palavra / len(vals)

        distintos = set(normalizados)
        score_codigo = 0.0
        if distintos and distintos.issubset(CODIGOS_TIPO.keys()) and len(distintos) >= 2:
            casam_codigo = sum(1 for n in normalizados if n in CODIGOS_TIPO)
            score_codigo = casam_codigo / len(vals)

        score = max(score_palavra, score_codigo if score_codigo >= 0.9 else 0.0)
        if score > melhor_score:
            melhor, melhor_score = c, score
    return melhor if melhor_score >= 0.5 else None


def analisar(rows: list[tuple], encoder, ref_emb: np.ndarray) -> MapaColunas:
    ncols = _ncols(rows)
    h = _header_por_densidade(rows)
    inicio = h + 1

    colunas = {
        k: v
        for k, v in (
            ("descricao", _col_descricao(rows, inicio, ncols, encoder, ref_emb)),
            ("indice", _col_indice(rows, inicio, ncols)),
            ("tipo", _col_tipo(rows, inicio, ncols)),
        )
        if v is not None
    }
    return MapaColunas(header_row=h + 1, colunas=colunas)
