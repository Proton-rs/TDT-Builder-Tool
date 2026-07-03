"""Roteia um SignalRecord pelos quadrantes gap × percentual.

| gap   | %     | resultado |
|-------|-------|-----------|
| alto  | alta  | decidido  |
| baixo | alta  | revisão   |
| alto  | baixa | revisão   |
| baixo | baixa | revisão   |

Só decide quando há confiança (% >= threshold) E separação (gap >= threshold).

Com ``votos`` por método (calibrados), decide em CASCATA pelo sinal mais
confiável e grava qual método decidiu na justificativa (rastreabilidade):

  1. fuzzy altíssimo  -> grafia idêntica (match léxico forte)
  2. e5 altíssimo     -> semântica forte
  3. consenso         -> >= ``min_consenso`` métodos concordam no top-1
                         (gap exigido é DINÂMICO pela confiança dos métodos)
  4. quadrante mesclado (fallback final, comportamento legado)

Sem ``votos``, mantém só o passo 4 (retrocompat: pipeline/testes legados).

O passo 3 (consenso) tem precisão de 42% no benchmark (contra ~95% dos outros
passos da cascata) — fica desligado por padrão via ``Config.usar_consenso``
(default ``False``). Quando ``False``, a cascata pula direto do passo 2 pro 4.
"""

from __future__ import annotations

from dataclasses import replace

from tdt.config import Config
from tdt.contracts import Candidato, SignalRecord
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.normalizacao.normalizador import canonizar

# Limiares de "altíssimo" p/ a cascata — um único sinal tão forte que decide
# sozinho, sem precisar de consenso.
_FUZZY_ALTISSIMO = 0.95
_E5_ALTISSIMO = 0.95

# Gap <= este limiar é tratado como empate estrutural (mesmo critério usado
# no diagnóstico SP-H Task 1 p/ classificar "gap-zero").
_GAP_ZERO_LIMIAR = 0.005


def _resolver_empate_descricao_lp(
    rec: SignalRecord,
    candidatos: list[Candidato],
    gap: float,
    pct_ok: bool,
    config: Config,
    lista_padrao: ListaPadraoADMS | None,
) -> SignalRecord | None:
    """Quando os 2 melhores candidatos empatam (gap≈0) E suas siglas mapeiam
    para a MESMA descrição-padrão na LP, o empate é estrutural — nenhum
    texto discrimina entre eles, nem para o scorer nem para um revisor
    humano. Decide de forma determinística (sigla alfabeticamente menor) em
    vez de mandar para revisão. Devolve None se não se aplica (LP ausente,
    sigla sem cadastro, descrições diferentes — empate genuíno, ou o
    candidato top não atinge o mesmo piso de confiança (``pct_ok``) exigido
    pelo caminho normal de decisão — sem isso, dois candidatos empatados em
    score muito baixo seriam decididos só por coincidirem na LP, o que não é
    confiança suficiente).
    """
    if (
        lista_padrao is None
        or not pct_ok
        or gap > _GAP_ZERO_LIMIAR
        or len(candidatos) < 2
    ):
        return None

    c1, c2 = candidatos[0], candidatos[1]
    sp1 = lista_padrao.por_sigla(c1.sigla)
    sp2 = lista_padrao.por_sigla(c2.sigla)
    if sp1 is None or sp2 is None:
        return None

    d1 = canonizar(sp1.descricao, config)
    d2 = canonizar(sp2.descricao, config)
    if not d1 or d1 != d2:
        return None

    vencedora = min(c1.sigla, c2.sigla)
    return replace(
        rec,
        sigla_sinal=vencedora,
        status="decidido",
        justificativa=(
            f"empate_descricao_lp_duplicada: {c1.sigla}/{c2.sigla}, "
            f"escolhida {vencedora} por ordem alfabética"
        ),
    )


def _quadrante(
    rec: SignalRecord,
    config: Config,
    lista_padrao: ListaPadraoADMS | None = None,
) -> SignalRecord:
    """Decisão legada por quadrante gap × percentual sobre ``rec.candidatos``."""
    candidatos = sorted(rec.candidatos, key=lambda c: c.score, reverse=True)
    if not candidatos:
        return replace(
            rec, status="revisao", justificativa="sem candidato para o sinal"
        )

    topo = candidatos[0]
    segundo = candidatos[1].score if len(candidatos) > 1 else 0.0
    gap = topo.score - segundo
    pct_ok = topo.score >= config.threshold_pct
    gap_ok = gap >= config.threshold_gap

    if pct_ok and gap_ok:
        return replace(
            rec,
            sigla_sinal=topo.sigla,
            status="decidido",
            justificativa=f"{topo.sigla} decidido (%={topo.score:.2f}, gap={gap:.2f})",
        )

    resolvido = _resolver_empate_descricao_lp(
        rec, candidatos, gap, pct_ok, config, lista_padrao
    )
    if resolvido is not None:
        return resolvido

    return replace(
        rec,
        status="revisao",
        justificativa=f"ambíguo (%={topo.score:.2f}, gap={gap:.2f})",
    )


def _top1(cands: list[Candidato]) -> Candidato | None:
    return max(cands, key=lambda c: c.score) if cands else None


def _confianca(n_confiantes: int) -> str:
    """Mapeia nº de métodos confiantes -> chave de gap dinâmico.

    Mais métodos confiantes => exigimos MENOS gap (confiança alta). Um só
    método confiante => exigimos o gap maior (confiança baixa) p/ matar FP.
    """
    if n_confiantes >= 3:
        return "alta"
    if n_confiantes == 2:
        return "media"
    return "baixa"


def _decidir_por_votos(
    rec: SignalRecord, config: Config, votos: dict[str, list[Candidato]]
) -> SignalRecord | None:
    """Tenta decidir pela cascata sobre os votos calibrados. None se não decide."""
    tops = {m: _top1(c) for m, c in votos.items()}

    # 1. fuzzy altíssimo -> grafia
    fz = tops.get("fuzzy")
    if fz is not None and fz.score >= _FUZZY_ALTISSIMO:
        return replace(
            rec,
            sigla_sinal=fz.sigla,
            status="decidido",
            justificativa=f"{fz.sigla} decidido por fuzzy (grafia, score={fz.score:.2f})",
        )

    # 2. e5 altíssimo -> semântica
    e5 = tops.get("e5")
    if e5 is not None and e5.score >= _E5_ALTISSIMO:
        return replace(
            rec,
            sigla_sinal=e5.sigla,
            status="decidido",
            justificativa=f"{e5.sigla} decidido por e5 (semântica, score={e5.score:.2f})",
        )

    # 3. consenso + gap dinâmico: métodos cujo top-1 passa do threshold votam na
    #    sua sigla. O nº de métodos confiantes define a confiança -> e o gap
    #    exigido. Com >=1 método confiante o gap dinâmico GOVERNA a decisão
    #    (não cai pro quadrante legado, mais frouxo, que reabriria o FP).
    #    Desligado por padrão (config.usar_consenso=False) — precisão baixa (42%).
    if not config.usar_consenso:
        return None  # passo 3 desligado: deixa o quadrante mesclado decidir

    confiantes = [t for t in tops.values() if t is not None and t.score >= config.threshold_pct]
    if not confiantes:
        return None  # nenhum método confiante: deixa o quadrante mesclado decidir

    contagem: dict[str, int] = {}
    for t in confiantes:
        contagem[t.sigla] = contagem.get(t.sigla, 0) + 1
    sigla_vencedora = max(contagem, key=lambda s: contagem[s])
    n_acordo = contagem[sigla_vencedora]

    chave = _confianca(n_acordo)
    gap_exigido = config.gaps_por_confianca[chave]
    cands_ord = sorted(rec.candidatos, key=lambda c: c.score, reverse=True)
    topo = cands_ord[0].score if cands_ord else 0.0
    segundo = cands_ord[1].score if len(cands_ord) > 1 else 0.0
    gap = topo - segundo

    if n_acordo >= config.min_consenso and gap >= gap_exigido:
        return replace(
            rec,
            sigla_sinal=sigla_vencedora,
            status="decidido",
            justificativa=(
                f"{sigla_vencedora} decidido por consenso "
                f"({n_acordo} métodos, conf={chave}, gap={gap:.2f}>={gap_exigido:.2f})"
            ),
        )

    # houve método(s) confiante(s) mas sem consenso suficiente ou gap insuficiente
    # sob a confiança vigente -> revisão (não reabre via quadrante frouxo).
    return replace(
        rec,
        status="revisao",
        justificativa=(
            f"sem consenso/gap (acordo={n_acordo}, conf={chave}, "
            f"gap={gap:.2f}<{gap_exigido:.2f})"
        ),
    )


def rotear(
    rec: SignalRecord,
    config: Config,
    votos: dict[str, list[Candidato]] | None = None,
    lista_padrao: ListaPadraoADMS | None = None,
) -> SignalRecord:
    """Roteia o sinal. ``votos`` (opcional) = candidatos calibrados por método.

    Com ``votos``, aplica a cascata (fuzzy > e5 > consenso) com gap dinâmico;
    cai no quadrante mesclado se nada decidir. Sem ``votos``, só o quadrante
    (retrocompat).

    ``lista_padrao`` (opcional): quando o quadrante mesclado não decide por
    empate estrutural (gap≈0) entre os 2 melhores candidatos, e a LP tiver a
    MESMA descrição-padrão cadastrada para as duas siglas (bug de dados da
    LP, não um empate genuíno), decide deterministicamente em vez de mandar
    para revisão — ver ``_resolver_empate_descricao_lp``. Só se aplica
    quando o candidato top também atinge ``config.threshold_pct`` (mesmo
    ``pct_ok`` do caminho normal) — dois candidatos empatados em score baixo
    não são decididos só por coincidirem na LP.
    """
    if votos:
        decidido = _decidir_por_votos(rec, config, votos)
        if decidido is not None:
            return decidido
    return _quadrante(rec, config, lista_padrao)
