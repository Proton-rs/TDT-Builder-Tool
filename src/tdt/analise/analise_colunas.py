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

from tdt.config import Config
from tdt.contracts import MapaColunas
from tdt.normalizacao.vocabulario_tipo import CODIGOS_TIPO, VOCAB as _TIPO_VOCAB

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

    ponytail: amostra por coluna limitada a _AMOSTRA_MAX (não 200) — o custo
    dominante é a inferência do modelo BERT, proporcional ao volume de texto
    codificado, não lógica Python. Medido em sheets reais (até 1238 linhas,
    236 colunas): cap 200→20 não muda a coluna detectada; 40 dá ~2-4x menos
    texto codificado com folga de segurança sobre o mínimo observado (20).
    Se um caso real divergir, subir _AMOSTRA_MAX antes de reverter o batch.
    """
    import math

    _AMOSTRA_MAX = 40
    candidatos: list[tuple[int, list[str]]] = []
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        textos = [v for v in vals if any(ch.isalpha() for ch in v)]
        if len(textos) < 2:
            continue
        candidatos.append((c, textos[:_AMOSTRA_MAX]))

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


_ROTULO_CONTADOR_POSICAO = ("LINHA", "LINE", "SEQ", "ROW", "ITEM")
_ROTULO_ENDERECO = ("DNP3", "INDEX", "ENDERECO", "ADDRESS", "ADDR", "ENDPT")
_BONUS_ENDERECO = 0.10  # tie-break: header com cara de endereço soma 10% ao score bruto


def _rotulo_bate(rotulo: str, termos: tuple[str, ...]) -> bool:
    return any(t in rotulo for t in termos)


def _e_contador_de_posicao(rows: list[tuple], c: int, inicio: int) -> bool:
    """Detecta coluna "contador de posição": o valor numérico da célula é a
    própria posição da linha na sheet (a menos de um deslocamento constante),
    quase sem exceção. Isso é diferente de "monotônico"/"sequencial" -- uma
    coluna de ENDEREÇO real também pode ser 1,2,3.../2100,2101,2102... (ver
    caso SNMP/FWB, onde "UTR COS Index" é sequencial e genuíno); o que
    identifica um contador de posição especificamente é que ele rastreia a
    ENUMERAÇÃO DA PRÓPRIA LINHA da planilha (deslocamento fixo = número da
    linha em que aparece, sempre o mesmo em quase toda a coluna), não um
    valor de domínio (endereço de protocolo) que por coincidência também é
    sequencial.
    """
    deslocamentos: list[int] = []
    for i, r in enumerate(rows[inicio:], start=inicio):
        if c < len(r) and r[c] is not None:
            v = str(r[c]).strip()
            if v and _INT.match(v):
                deslocamentos.append(int(v) - i)
    if len(deslocamentos) < 2:
        return False
    mais_comum = max(set(deslocamentos), key=deslocamentos.count)
    razao = sum(1 for d in deslocamentos if d == mais_comum) / len(deslocamentos)
    return razao >= 0.95


def _col_indice(rows, inicio, ncols) -> int | None:
    header_row = inicio - 1
    header = rows[header_row] if 0 <= header_row < len(rows) else ()

    candidatos: list[tuple[int, float]] = []
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        if not vals:
            continue
        ints = [int(v) for v in vals if _INT.match(v)]
        frac = len(ints) / len(vals)
        crescente = sum(1 for a, b in zip(ints, ints[1:]) if b > a)
        mono = (crescente / (len(ints) - 1)) if len(ints) > 1 else 0.0
        score = frac * (0.5 + 0.5 * mono)
        if score <= 0.0:
            continue
        candidatos.append((c, score))

    if not candidatos:
        return None

    rotulo_de = {c: _norm(header[c]) if c < len(header) else "" for c, _ in candidatos}

    # Veto: coluna com rótulo de "contador de posição" (Linha/Seq/Item/...) E
    # cujos valores de fato rastreiam a posição da linha na sheet -- nunca é
    # um endereço DNP3 (é a identidade da linha, não o protocolo). Só afeta
    # candidatos que casam AMBOS os critérios (rótulo E forma), preservando
    # colunas de endereço real que também são sequenciais (ex. SNMP/FWB).
    sobreviventes = [
        (c, score) for c, score in candidatos
        if not (_rotulo_bate(rotulo_de[c], _ROTULO_CONTADOR_POSICAO) and _e_contador_de_posicao(rows, c, inicio))
    ]
    if not sobreviventes:
        sobreviventes = candidatos  # todos vetados (improvável) -- não fica sem índice

    # Desempate: rótulo com cara de endereço de protocolo ganha um bônus
    # multiplicativo -- decide entre concorrentes de score próximo (ex.
    # "Entrada Binária" vs "DNP3.0") sem inverter diferenças de score grandes.
    melhor, melhor_ajustado = None, -1.0
    for c, score in sobreviventes:
        ajustado = score * (1 + _BONUS_ENDERECO) if _rotulo_bate(rotulo_de[c], _ROTULO_ENDERECO) else score
        if ajustado > melhor_ajustado:
            melhor, melhor_ajustado = c, ajustado
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
        if len(distintos & set(CODIGOS_TIPO)) >= 2:
            casam_codigo = sum(1 for n in normalizados if n in CODIGOS_TIPO)
            score_codigo = casam_codigo / len(vals)

        score = max(score_palavra, score_codigo if score_codigo >= 0.9 else 0.0)
        if score > melhor_score:
            melhor, melhor_score = c, score
    return melhor if melhor_score >= 0.5 else None


_SIGLA_THRESHOLD = 0.3


_MODULO_ROTULO = ("MODULO", "BAY", "VAO")
_MODULO_BONUS = 0.10
_MODULO_CANON_MIN = 0.3   # fração mín. de valores distintos com prefixo de módulo
_MODULO_BLOCO_MIN = 0.5   # estrutura de bloco: 1 - transicoes/(n-1)
_SO_ALFA = re.compile(r"[A-Za-z]+")


def _col_sigla(rows, inicio, ncols, siglas_set: frozenset[str]) -> int | None:
    """Coluna cujos valores são majoritariamente siglas conhecidas da lista
    padrão ADMS (``siglas_set``). Exclui colunas predominantemente numéricas
    (são índice, não sigla) e colunas de baixa diversidade (ex: "IED" repete
    a mesma tag de relé em várias linhas -- se essa tag coincidir com uma
    sigla válida por acaso, teria score 100% sem ser uma coluna de sigla por
    linha; exige pelo menos 2 siglas válidas DISTINTAS, como a SAN2 real)."""
    melhor, melhor_score = None, 0.0
    for c in range(ncols):
        vals = _valores_coluna(rows, c, inicio)
        if len(vals) < 2:
            continue
        norm = [unicodedata.normalize("NFKD", v).strip().upper() for v in vals]
        digitais = sum(1 for v in norm if v.isdigit())
        if digitais / len(norm) > 0.8:
            continue
        validas = {v for v in norm if v in siglas_set}
        if len(validas) < 2:
            continue
        acertos = sum(1 for v in norm if v in siglas_set)
        score = acertos / len(norm)
        if score >= _SIGLA_THRESHOLD and score > melhor_score:
            melhor, melhor_score = c, score
    return melhor


def _col_modulo(rows, inicio, ncols, config: Config, reservadas: set[int]) -> int | None:
    """Coluna de módulo por linha: valores em BLOCOS contíguos + alta taxa de
    canonização por prefixo de módulo. Header 'Módulo' soma bônus de desempate.

    - Estrutura de bloco separa {módulo, IED} de {descrição, índice}.
    - Taxa de canonização (1º token alfabético ∈ mapa_prefixo_modulo) separa
      módulo de IED (SEL-411L não bate prefixo).
    - Exclui colunas já reivindicadas (descricao/indice/tipo/sigla), numéricas
      e de baixa diversidade (< 2 distintos).
    """
    prefixos = set(config.mapa_prefixo_modulo)
    header_row = inicio - 1
    header = rows[header_row] if 0 <= header_row < len(rows) else ()
    melhor, melhor_score = None, 0.0
    for c in range(ncols):
        if c in reservadas:
            continue
        vals = _valores_coluna(rows, c, inicio)
        if len(vals) < 2:
            continue
        norm = [_norm(v) for v in vals]
        if len(set(norm)) < 2:
            continue
        if sum(1 for v in norm if v.replace("-", "").isdigit()) / len(norm) > 0.5:
            continue
        # Calcular transições baseado em prefixos (blocos de mesmo prefixo)
        prefixos_vals = []
        for v in norm:
            m = _SO_ALFA.findall(v)
            if m:
                prefixos_vals.append(m[0])
            else:
                prefixos_vals.append(v)
        transicoes = sum(1 for a, b in zip(prefixos_vals, prefixos_vals[1:]) if a != b)
        bloco = 1.0 - transicoes / max(len(prefixos_vals) - 1, 1)
        if bloco < _MODULO_BLOCO_MIN:
            continue
        distintos = set(norm)
        com_prefixo = sum(
            1 for v in distintos
            if (m := _SO_ALFA.findall(v)) and m[0] in prefixos
        )
        canon = com_prefixo / len(distintos)
        if canon < _MODULO_CANON_MIN:
            continue
        score = canon * bloco
        rotulo = _norm(header[c]) if c < len(header) else ""
        if any(t in rotulo for t in _MODULO_ROTULO):
            score *= 1 + _MODULO_BONUS
        if score > melhor_score:
            melhor, melhor_score = c, score
    return melhor


def analisar(
    rows: list[tuple], encoder, ref_emb: np.ndarray,
    siglas_set: frozenset[str] | None = None,
    config: Config | None = None,
) -> MapaColunas:
    ncols = _ncols(rows)
    h = _header_por_densidade(rows)
    inicio = h + 1

    c_desc = _col_descricao(rows, inicio, ncols, encoder, ref_emb)
    c_idx = _col_indice(rows, inicio, ncols)
    c_tipo = _col_tipo(rows, inicio, ncols)
    c_sig = _col_sigla(rows, inicio, ncols, siglas_set) if siglas_set is not None else None
    c_mod = None
    if config is not None:
        reservadas = {c for c in (c_desc, c_idx, c_tipo, c_sig) if c is not None}
        c_mod = _col_modulo(rows, inicio, ncols, config, reservadas)

    colunas = {
        k: v
        for k, v in (
            ("descricao", c_desc),
            ("indice", c_idx),
            ("tipo", c_tipo),
            ("sigla", c_sig),
            ("modulo", c_mod),
        )
        if v is not None
    }
    return MapaColunas(header_row=h + 1, colunas=colunas)
