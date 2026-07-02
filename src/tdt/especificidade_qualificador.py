"""Pós-decisão: sigla base de família não engole qualificador presente no texto.

Contexto (SP-G, Task 4): ``motor_regras.aplicar_rastreado`` soma um delta não
limitado APÓS a calibração Platt, então uma sigla genérica (``79``) pode
pontuar mais que uma irmã mais específica (``79OK``, ``79LO``, ``79RE``...)
mesmo quando o texto do sinal contém a palavra que qualifica a irmã (ex.:
"Bem Sucedido" -> deveria ser ``79OK``, não ``79``). Esse módulo não mexe na
calibração/regras (fora de escopo aqui) — atua como camada de correção
PÓS-decisão: se o decidido é a sigla RAIZ (bare) de uma família ANSI — ou seja
``sigla == numero_lider(sigla)`` (ex.: ``79``, ``25``, ``21``; NÃO ``25VT``,
``20T``, ``81E1``, que já são específicas) — e a descrição-padrão de
exatamente UM irmão tem token distintivo presente no texto canônico do sinal,
o irmão vence. Vários irmãos casando ao mesmo tempo -> ambíguo, vai para
revisão (motivo ``qualificador_ambiguo``).

Guarda ``sigla == numero_lider(sigla)`` é essencial: só re-arbitra quando o
decidido é o rótulo genérico puro da família (o cenário do bug — calibração
deixa o genérico vencer por score). Sem essa guarda, o módulo re-litigaria
decisões que JÁ elegeram um irmão específico (ex.: base ``25VT`` "TRIP
DIFERENCA TENSAO" vs irmão ``25ER`` "FALHA SINCRONISMO") — nesses casos a
palavra "SINCRONISMO"/"FALHA" é vocabulário comum da família ANSI-25 inteira,
não um qualificador discriminante, e sinalizaria falso-positivo de
ambiguidade (visto em dados reais: ``docs/input_nao_homogeneo_1_GTD.xlsx``,
casos "Sincronismo (25) - Falha por Diferença de Tensão/Ângulo").

Família de irmãos identificada via ``motor_regras._numero_lider`` (mesmo
critério usado por ``filtro_preciso.filtrar_especificidade``), não por
``sigla.startswith(base)`` ingênuo: siglas "combo" como ``2759`` (27+59) ou
``8750`` (87+50) compartilham prefixo textual com bases de 2 dígitos mas são
de família ANSI diferente (``_numero_lider("2759") == "27"``, não ``"75"`` ou
``"59"``) — usar apenas startswith geraria falso-positivo nesses casos.

Token distintivo de um irmão = presente na descrição do irmão, ausente da
descrição da base E exclusivo desse irmão dentro da família (não repetido em
nenhuma outra descrição do grupo) — evita que vocabulário compartilhado por
vários irmãos (ex.: "SINCRONISMO" na família 25) seja tratado como
qualificador de um único irmão.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import SignalRecord
from tdt.motor_regras import _numero_lider
from tdt.normalizacao.normalizador import canonizar


def preferir_irmao_qualificado(
    rec: SignalRecord, lp, config: Config | None = None
) -> SignalRecord:
    """Troca a sigla decidida por um irmão mais específico quando o texto do
    sinal contém a palavra que o distingue da base. Múltiplos irmãos casando
    -> ``status="revisao"``, motivo ``qualificador_ambiguo``.
    """
    if rec.status != "decidido" or not rec.sigla_sinal or lp is None:
        return rec
    if config is None:
        config = Config()

    base = rec.sigla_sinal.upper()
    lider_base = _numero_lider(base)
    if lider_base is None or base != lider_base:
        # Só re-arbitra quando o decidido é a raiz genérica da família (ex.
        # "79", "25"); sigla já específica (25VT, 81E1, 20T...) não é
        # re-litigada por este módulo (ver docstring).
        return rec

    texto = frozenset(rec.descricoes.normalizada.upper().split())

    todos = (*lp.discretos, *lp.analogicos)
    desc_base = next(
        (s.descricao for s in todos if s.sigla.upper() == base), ""
    )
    tokens_base = frozenset(canonizar(desc_base, config).split()) if desc_base else frozenset()

    irmaos: list[tuple[str, frozenset[str]]] = []
    for s in todos:
        sig = s.sigla.upper()
        if sig == base or _numero_lider(sig) != lider_base or not s.descricao:
            continue
        irmaos.append((s.sigla, frozenset(canonizar(s.descricao, config).split())))

    # Token só conta como qualificador se for exclusivo de UM irmão dentro da
    # família (não aparece na base nem em outro irmão) — vocabulário comum a
    # vários irmãos (ex. "SINCRONISMO" na família 25) não decide nada.
    contagem: Counter[str] = Counter()
    for _, toks in irmaos:
        for t in toks - tokens_base:
            contagem[t] += 1

    casando: list[str] = []
    for sig, toks in irmaos:
        distintivos = frozenset(t for t in (toks - tokens_base) if contagem[t] == 1)
        if distintivos and (distintivos & texto):
            casando.append(sig)

    if len(casando) == 1:
        irmao = casando[0]
        justificativa = f"{irmao} por qualificador (base {rec.sigla_sinal})"
        if rec.justificativa:
            justificativa = f"{rec.justificativa} | {justificativa}"
        return replace(rec, sigla_sinal=irmao, justificativa=justificativa)

    if len(casando) > 1:
        # justificativa é o motivo literal ("qualificador_ambiguo"), no mesmo
        # padrão de "estado_sem_candidato"/"fora_whitelist_equipamento" —
        # pipeline._classificar_um (linha ~341) faz match exato de
        # d.justificativa contra a lista de motivos conhecidos para propagar
        # ao ItemRevisao; texto livre aqui seria silenciosamente reclassificado
        # como "score_baixo"/"sigla_multipla".
        return replace(rec, status="revisao", justificativa="qualificador_ambiguo")

    return rec
