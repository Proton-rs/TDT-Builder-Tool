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
"""

from __future__ import annotations

from dataclasses import replace

from tdt.config import Config
from tdt.contracts import Candidato, SignalRecord

# Limiares de "altíssimo" p/ a cascata — um único sinal tão forte que decide
# sozinho, sem precisar de consenso.
_FUZZY_ALTISSIMO = 0.95
_E5_ALTISSIMO = 0.95


def _quadrante(rec: SignalRecord, config: Config) -> SignalRecord:
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
) -> SignalRecord:
    """Roteia o sinal. ``votos`` (opcional) = candidatos calibrados por método.

    Com ``votos``, aplica a cascata (fuzzy > e5 > consenso) com gap dinâmico;
    cai no quadrante mesclado se nada decidir. Sem ``votos``, só o quadrante
    (retrocompat).
    """
    if votos:
        decidido = _decidir_por_votos(rec, config, votos)
        if decidido is not None:
            return decidido
    return _quadrante(rec, config)
