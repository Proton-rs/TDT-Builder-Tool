"""Forca convergencia de pares aberto/fechado do mesmo equipamento pra
sigla de posicao (ex. DJF1, SECC), quando a descricao padrao da sigla e generica
demais pro scorer de texto reconhecer as duas linhas do input (ver SP10).
Roda antes do scoring; e' rede de seguranca, desligavel via Config."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import ItemRevisao, SignalRecord

# Prefixo (não palavra exata): robusto a "FECHADO"/"FECHADA", "DESLIGADO"/"DESLIGADA"
# e a variações que corrigir_typos possa introduzir.
_LIGADO_PREFIXOS = ("LIGAD", "FECHAD")
_DESLIGADO_PREFIXOS = ("DESLIGAD", "ABERT")

# Seccionadora: keyword (prefixo de token) → sigla de posição.
# Ordenada por especificidade decrescente — "BYPASS" antes de "BY" para
# que "BY PASS" não caia no genérico "BY" antes do check de prefixo.
# Robustez: "BYPS", "BY-PASS", "BY PASS" todos começam com "BY".
_SECC_KEYWORDS: list[tuple[str, str]] = [
    ("BYPASS",    "SECB"),
    ("BY",        "SECB"),   # BY PASS / BY-PASS / BYPS
    ("CARG",      "SECC"),   # CARGA / CARG
    ("TRANSFER",  "SECT"),   # TRANSFERENCIA / TRANSFER (NÃO "TRANSF": exclui TRANSFORMADOR)
    ("ATERR",     "SECG"),   # ATERRAMENTO
    ("TERRA",     "SECG"),
    ("FONT",      "SECF"),   # FONTE / FONT
    ("INTERBAR",  "SECI"),   # INTERBARRAS / INTERBARRA
    ("INTERLINHA","SECL"),
]


def _tem_prefixo(tokens: list[str], prefixos: tuple[str, ...]) -> bool:
    return any(tok.startswith(p) for tok in tokens for p in prefixos)


# Comando de 1 linha só ("Abrir/Fechar", "Ligar/Desligar" — verbo infinitivo,
# as DUAS polaridades no mesmo texto) — não bate _LIGADO_PREFIXOS/
# _DESLIGADO_PREFIXOS (particípio), então precisa de prefixos próprios pra
# ser reconhecido como comando-par (Task 8.1 SP-CVA, achado item 1b).
_ABERTURA_PREFIXOS = ("ABRIR", "ABERT", "DESLIGA")
_FECHAMENTO_PREFIXOS = ("FECHA", "LIGA")


def _eh_comando_toggle(tokens: list[str]) -> bool:
    """True se o texto carrega evidência das DUAS polaridades juntas (comando
    de uma linha só que alterna o equipamento, ex. 'Abrir/Fechar')."""
    return _tem_prefixo(tokens, _ABERTURA_PREFIXOS) and _tem_prefixo(tokens, _FECHAMENTO_PREFIXOS)


# Seleção do PAR ligado/desligado por PALAVRA EXATA de particípio — não por
# prefixo. 'ABERTURA' (Supervisão Circ Abertura) bate o prefixo ABERT mas não
# é estado de posição; com prefixo, o grupo real infla `desligado` e o par
# nunca é forçado (SP-CVA2 E1). Prefixos continuam em eh_texto_de_posicao
# (gate de decisão — papel diferente).
_PARTICIPIOS_LIGADO = frozenset({"LIGADO", "LIGADA", "FECHADO", "FECHADA"})
_PARTICIPIOS_DESLIGADO = frozenset({"DESLIGADO", "DESLIGADA", "ABERTO", "ABERTA"})


def _polaridade_pura(rec: SignalRecord) -> str | None:
    """"ligado"/"desligado" quando o texto tem exatamente UMA polaridade em
    palavra exata de particípio; None p/ comando (Output), toggle ou ruído."""
    if rec.tipo_sinal.direcao == "Output":
        return None
    tokens = set(rec.descricoes.normalizada.upper().split())
    lig = bool(tokens & _PARTICIPIOS_LIGADO)
    des = bool(tokens & _PARTICIPIOS_DESLIGADO)
    if lig and not des:
        return "ligado"
    if des and not lig:
        return "desligado"
    return None


# Siglas que representam POSIÇÃO de equipamento (aberto/fechado, ligado/
# desligado) — só podem decidir um sinal se o texto tiver evidência real de
# posição (ver eh_texto_de_posicao). Task 6 / SP-G: gate contra decisão "por
# default" quando o texto residual é genérico demais (ex. "DISJUNTOR
# INTERTRAVAMENTO", "... INDEFINIDO") e não descreve estado algum.
_SIGLAS_POSICAO: frozenset[str] = frozenset(
    {"DJF1", "DJA1", "SECC", "SECB", "SECT", "SECG", "SECF", "SECI", "SECL"}
)


def eh_texto_de_posicao(texto_normalizado: str) -> bool:
    """True se o texto contém evidência de estado de posição (aberto/fechado,
    ligado/desligado, ou o token "NA" — normalmente aberto).

    Reusa ``_LIGADO_PREFIXOS``/``_DESLIGADO_PREFIXOS`` (mesmas listas do
    pareamento de par ligado/desligado) — genérico por construção: qualquer
    texto que já ativaria o pareamento de par também passa aqui. Textos como
    "INTERTRAVAMENTO" ou "INDEFINIDO" não têm nenhum desses prefixos/token e
    portanto não contam como evidência de posição.
    """
    tokens = texto_normalizado.upper().split()
    return (
        "NA" in tokens
        or _tem_prefixo(tokens, _LIGADO_PREFIXOS)
        or _tem_prefixo(tokens, _DESLIGADO_PREFIXOS)
    )


def _chave(rec: SignalRecord) -> tuple | None:
    eq = rec.eletrico.equipamento_alvo
    if eq not in ("Disjuntor", "Seccionadora") or not rec.eletrico.nome_equipamento:
        return None
    return (rec.modulo.nome, eq, rec.eletrico.nome_equipamento)


def _sigla_disjuntor(tokens_combined: list[str]) -> str:
    """DJA1 se algum token for exatamente "NA" (normalmente aberto), DJF1 default."""
    if "NA" in tokens_combined:
        return "DJA1"
    return "DJF1"


def _sigla_seccionadora(desc_combinada: str) -> str | None:
    """Resolve a variante SEC* pela palavra-função. None se ambíguo."""
    tokens = desc_combinada.upper().split()
    for kw, sigla in _SECC_KEYWORDS:
        if any(tok.startswith(kw) for tok in tokens):
            return sigla
    return None


def forcar_polaridade_equipamento(
    registros: list[SignalRecord], config: Config,
) -> tuple[list[SignalRecord], list[ItemRevisao]]:
    """Antes do scoring: duas linhas do mesmo equipamento com polaridade
    oposta (fechado/aberto, ligado/desligado) convergem para a sigla de
    posição do equipamento (ex. DJF1, SECC), sem depender do scorer de texto.

    Retorna (sinais_restantes, itens_revisao):
    - sinais forçados: status="decidido", sigla_sinal=<sigla>
    - par detectado mas variante ambígua (Seccionadora sem keyword): revisão "posicao_ambigua"
    - sem par completo ou flag desligada: passam intactos para o scorer
    """
    if not config.parear_polaridade_equipamento:
        return registros, []

    grupos: dict[tuple, list[SignalRecord]] = defaultdict(list)
    for rec in registros:
        chave = _chave(rec)
        if chave is not None:
            grupos[chave].append(rec)

    forcados: dict[str, str] = {}
    ambiguos: set[str] = set()

    for chave, grupo in grupos.items():
        eq = chave[1]  # "Disjuntor" | "Seccionadora"
        ligado = [r for r in grupo if _polaridade_pura(r) == "ligado"]
        desligado = [r for r in grupo if _polaridade_pura(r) == "desligado"]
        if not (len(ligado) == 1 and len(desligado) == 1 and ligado[0] is not desligado[0]):
            continue  # par incompleto ou múltiplo — scorer decide

        par = (ligado[0], desligado[0])
        desc_comb = " ".join(r.descricoes.normalizada.upper() for r in par)

        if eq == "Disjuntor":
            sigla = _sigla_disjuntor(desc_comb.split())
            for r in par:
                forcados[r.id] = sigla
        else:  # Seccionadora
            sigla = _sigla_seccionadora(desc_comb)
            if sigla is not None:
                for r in par:
                    forcados[r.id] = sigla
            else:
                # par detectado mas variante não reconhecida — revisão explícita
                for r in par:
                    ambiguos.add(r.id)

        if sigla is not None:
            # comando de uma linha só ("Abrir/Fechar") do MESMO equipamento —
            # converge pra sigla já forçada do par de status, senão o scorer
            # semântico desempata pra sigla errada (ex. DJA1 em vez de DJF1).
            for outro in grupo:
                if outro is ligado[0] or outro is desligado[0]:
                    continue
                if outro.tipo_sinal.direcao == "Output" and _eh_comando_toggle(
                    outro.descricoes.normalizada.split()
                ):
                    forcados[outro.id] = sigla

    revisao = [
        ItemRevisao(rec, motivo="posicao_ambigua")
        for rec in registros
        if rec.id in ambiguos
    ]
    saida = [
        replace(rec, sigla_sinal=forcados[rec.id], status="decidido")
        if rec.id in forcados
        else rec
        for rec in registros
        if rec.id not in ambiguos
    ]
    return saida, revisao


# Consumidos por dc_pairer (SP-CVA2 E2) — aliases públicos, mesma referência.
SIGLAS_POSICAO = _SIGLAS_POSICAO
eh_comando_toggle = _eh_comando_toggle
