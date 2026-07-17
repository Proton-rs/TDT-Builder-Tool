"""Ancoragem por sigla explícita na descrição.

Quando a descrição de um sinal contém literalmente uma sigla da lista padrão,
essa é evidência de identidade de primeira classe — mais forte do que a
similaridade textual genérica. Este módulo detecta essas âncoras e as injeta
como candidatos de alta confiança, permitindo que a expansão de filhos
(expansao_candidatos) e o filtro de especificidade (filtro_preciso) selecionem
a variante correta (ex.: "Proteção 67 N Temporizado" → ancora 67N → filhos
67NT/67NTD → complemento decide).

Somente siglas "específicas" (len >= 3, tem dígito e letra) são ancoradas —
guarda que evita falsos positivos com números de identificação de equipamento
(ex: "52-21 (21Q0)").
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from tdt.contracts import Candidato
from tdt.motor_regras import _numero_lider

if TYPE_CHECKING:
    from tdt.contracts import SignalRecord
    from tdt.dados.lista_padrao import ListaPadraoADMS


def _eh_especifica(sigla: str) -> bool:
    """Sigla "específica": len >= 3, tem dígito e letra.

    Exclui siglas curtas como "21", "67" (apenas dígitos) e "PB", "IN"
    (apenas letras, len <= 2). Guarda contra números de identificação de
    equipamento (52-21, 21Q0) e tokens genéricos.
    """
    return len(sigla) >= 3 and any(c.isdigit() for c in sigla) and any(c.isalpha() for c in sigla)


def _familia(sigla: str) -> str:
    """Família ANSI da sigla: 2 dígitos líder, ou a sigla inteira se não numérica."""
    lider = _numero_lider(sigla.upper())
    return lider if lider is not None else sigla.upper()


@dataclass(frozen=True)
class Ancora:
    sigla: str  # sigla original da lista padrão (case-preservado)
    confianca: str = "alta"  # "alta" = âncora exata ou por junção
    exata: bool = True  # True = token exato na descrição; False = junção de tokens


_INDICE_CACHE: dict[tuple, dict[str, str]] = {}
"""Cache (id(lp), categoria) → {SIGLA_UPPER: sigla_original} para siglas específicas."""


def _indice(lp: "ListaPadraoADMS", categoria: str) -> dict[str, str]:
    key = (id(lp), categoria)
    if key not in _INDICE_CACHE:
        fonte = lp.discretos if categoria == "Discrete" else lp.analogicos
        _INDICE_CACHE[key] = {
            s.sigla.upper(): s.sigla
            for s in fonte
            if _eh_especifica(s.sigla)
        }
    return _INDICE_CACHE[key]


def detectar(
    rec: "SignalRecord",
    lp: "ListaPadraoADMS",
    categoria: str,
) -> list[Ancora]:
    """Detecta siglas da LP embutidas em ``rec.descricoes.normalizada``.

    Procura:
    - Âncora exata: token que é uma sigla específica da LP.
    - Âncora por junção: par de tokens adjacentes cuja concatenação é uma sigla.

    O índice é construído apenas com siglas da categoria informada — assim
    cada bundle só ancora siglas do seu próprio domínio, compondo com a
    barreira de categoria do dual-pass.
    """
    idx = _indice(lp, categoria)
    tokens = rec.descricoes.normalizada.upper().split()
    encontradas: list[Ancora] = []
    ja_vistas: set[str] = set()

    for i, tok in enumerate(tokens):
        # Âncora exata
        if tok in idx and tok not in ja_vistas:
            encontradas.append(Ancora(sigla=idx[tok]))
            ja_vistas.add(tok)
        # Âncora por junção de tokens adjacentes
        if i + 1 < len(tokens):
            juncao = tok + tokens[i + 1]
            if juncao in idx and juncao not in ja_vistas:
                encontradas.append(Ancora(sigla=idx[juncao], exata=False))
                ja_vistas.add(juncao)

    return encontradas


def tem_multiplas_familias(ancoras: list[Ancora]) -> bool:
    """True se as âncoras pertencem a >= 2 famílias ANSI distintas."""
    return len({_familia(a.sigla) for a in ancoras}) >= 2


def filtrar_subarvore(
    candidatos: list[Candidato],
    ancoras: list[Ancora],
) -> list[Candidato]:
    """Restringe cada família ancorada ao sub-ramo da âncora.

    A sigla âncora carrega informação (ex.: a letra "N" de "67N" = neutro) que
    o matching de palavras perde — a descrição-padrão usa "NEUTRO"/"FASE", mas o
    texto de entrada traz só a sigla. A expansão por prefixo de 2 dígitos
    (``expansao_candidatos``) reintroduz ramos irmãos (67F*, 67P*) que o "N"
    explícito exclui. Esta função remove, dentro de uma família ANSI ancorada,
    os candidatos que **não** começam com nenhuma das siglas âncora daquela
    família — deixando a expansão/regras escolherem o filho certo só entre os
    do ramo correto.

    Famílias sem âncora ficam intactas. Fallback: nunca esvazia.
    """
    if not ancoras:
        return candidatos

    prefixos_por_familia: dict[str, set[str]] = {}
    for a in ancoras:
        prefixos_por_familia.setdefault(_familia(a.sigla), set()).add(a.sigla.upper())

    resultado: list[Candidato] = []
    for c in candidatos:
        fam = _familia(c.sigla)
        prefixos = prefixos_por_familia.get(fam)
        if prefixos is None:
            resultado.append(c)  # família não ancorada — intacta
        elif any(c.sigla.upper().startswith(p) for p in prefixos):
            resultado.append(c)  # do sub-ramo da âncora — mantém
        # else: contradiz o ramo explícito (ex.: 67P2 quando âncora é 67N) — remove

    return resultado if resultado else candidatos


def desambiguar_variante(
    rec: "SignalRecord",
    ancoras: list[Ancora],
    config,
) -> "SignalRecord | None":
    """Decide entre variantes-irmãs de uma família exatamente ancorada (C1).

    Quando o roteador manda ``rec`` para revisão (score_baixo) porque os
    candidatos do topo (top-3) são todos irmãos de uma mesma família ANSI
    ancorada por sigla exata no texto (ex.: "79") e um deles é a própria
    sigla âncora, o gap≈0 entre variantes é falso empate: a âncora exata É
    a evidência textual mais forte, decide por ela (spec §9.3).

    Só considera âncoras ``exata=True`` — âncora por junção de tokens é
    inferência mais fraca e não decide sozinha (salvaguarda da spec).
    Devolve ``None`` quando não se aplica (sem âncora exata, top-3 sai da
    família ancorada, ou nenhum candidato bate a sigla da âncora).
    """
    ancoras_exatas = [a for a in ancoras if a.exata]
    if not ancoras_exatas:
        return None

    familias_ancoradas = {_familia(a.sigla) for a in ancoras_exatas}
    candidatos_finais = rec.candidatos[:3]
    if not candidatos_finais:
        return None
    if not all(_familia(c.sigla) in familias_ancoradas for c in candidatos_finais):
        return None

    siglas_ancora = {a.sigla.upper(): a.sigla for a in ancoras_exatas}
    for c in candidatos_finais:
        if c.sigla.upper() in siglas_ancora:
            return replace(
                rec,
                sigla_sinal=siglas_ancora[c.sigla.upper()],
                status="decidido",
                justificativa="variante-pai exata da âncora (C1)",
            )
    return None


def ancorar(
    fundidos: list[Candidato],
    ancoras: list[Ancora],
    score_ancora: float,
) -> list[Candidato]:
    """Injeta âncoras detectadas em ``fundidos`` como candidatos de alta confiança.

    - Candidatos ausentes são inseridos com ``fonte="ancora_sigla"`` e
      ``score=score_ancora``.
    - Candidatos já presentes têm o score elevado para
      ``max(existente, score_ancora)`` — nunca abaixa um score já alto.
    """
    if not ancoras:
        return fundidos

    por_sigla: dict[str, int] = {c.sigla.upper(): i for i, c in enumerate(fundidos)}
    resultado = list(fundidos)

    for ancora in ancoras:
        key = ancora.sigla.upper()
        if key in por_sigla:
            idx = por_sigla[key]
            if resultado[idx].score < score_ancora:
                resultado[idx] = replace(resultado[idx], score=score_ancora)
        else:
            resultado.append(
                Candidato(sigla=ancora.sigla, score=score_ancora, fonte="ancora_sigla")
            )
            por_sigla[key] = len(resultado) - 1

    return resultado
