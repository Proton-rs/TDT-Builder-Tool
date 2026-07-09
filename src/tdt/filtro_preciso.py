"""Filtro preciso de candidatos — remove siglas que contradizem pistas do texto.

Diferente do ``motor_regras`` (que ajusta scores com deltas), este módulo
**remove** candidatos que claramente não satisfazem as condições do texto.
Cada regra retorna ``bool``: ``True`` = mantém, ``False`` = remove.

Se o filtro eliminar todos os candidatos, retorna a lista original (fallback
seguro — não decidir é melhor que decidir errado).

Reusa constantes e helpers de ``motor_regras`` (nunca o chama diretamente).
Também reusa ``pareamento_polaridade`` (``_SIGLAS_POSICAO``,
``eh_texto_de_posicao``) para o gate de posição (Task 6, SP-G).
"""

from __future__ import annotations

from dataclasses import replace

from tdt.config import Config
from tdt.contracts import Candidato, SignalRecord
from tdt.motor_regras import (
    Contexto,
    _ESTAGIOS,
    _EQUIPAMENTO_SIGLA,
    _LADO_TEXTO,
    _MARCAS_COMANDO,
    _MARCAS_LADO,
    _NUMEROS_PROTECAO,
    _PARES_OPOSTOS,
    _TOKENS_COMANDO,
    _numero_lider,
    _numeros_no_texto,
    _tem_marca,
    equipamento_da_sigla,
    fase_da_sigla,
)
from tdt.pareamento_polaridade import _SIGLAS_POSICAO, eh_texto_de_posicao


# --- F_R1: número de proteção -----------------------------------------------


def f_r1(cand: Candidato, ctx: Contexto) -> bool:
    """Remove se texto tem número ANSI e sigla começa com número DIFERENTE."""
    numeros = _numeros_no_texto(ctx.tokens)
    if not numeros:
        return True
    lider = _numero_lider(cand.sigla.upper())
    if lider is None:
        return True
    return lider in numeros


# --- F_R2: pares opostos ----------------------------------------------------


def f_r2(cand: Candidato, ctx: Contexto) -> bool:
    """Remove se texto indica polaridade A e sigla carrega marca da polaridade B."""
    sigla = cand.sigla.upper()
    for par in _PARES_OPOSTOS:
        texto_a = any(t in ctx.tokens for t in par.tokens_a)
        texto_b = any(t in ctx.tokens for t in par.tokens_b)
        if texto_a == texto_b:
            continue
        if texto_a and _tem_marca(sigla, par.marca_b):
            return False
        if texto_b and _tem_marca(sigla, par.marca_a):
            return False
    return True


# --- F_R3: fase -------------------------------------------------------------


def f_r3(cand: Candidato, ctx: Contexto) -> bool:
    """Remove candidato cuja fase contradiz a fase do sinal (eletrico.fase).

    Lê ``ctx.eletrico.fase`` (extraída no N0, antes do colapso de separadores)
    em vez do texto — o N0 REMOVE a letra de fase da descrição, então
    "Corrente Fase B" vira "CORRENTE FASE" e o scorer não distingue IA/IB/IC.
    Filtro duro: mantém candidatos sem fase (ex: IOUT, P); remove só os de
    fase explicitamente divergente.
    """
    alvo = getattr(ctx.eletrico, "fase", None) if ctx.eletrico is not None else None
    if not alvo:
        return True
    fase_cand = fase_da_sigla(cand.sigla.upper())
    if fase_cand is None:
        return True  # sem fase → não conflita
    return fase_cand == alvo


# --- F_R4: estágio ----------------------------------------------------------


def f_r4(cand: Candidato, ctx: Contexto) -> bool:
    """Remove se texto tem estágio e sigla não termina no dígito do estágio.
    
    Agressivo: remove até candidatos sem estágio (ex: 51N quando texto
    tem E1). Upgrade: só remover se sigla explicitamente terminar em
    dígito DIFERENTE do estágio, mantendo sem-estágio.
    """
    estagios = ctx.tokens & _ESTAGIOS
    if not estagios:
        return True
    digito = next(iter(estagios))[1]
    return cand.sigla.endswith(digito)


# --- F_R5: comando × status -------------------------------------------------

# ponytail: filtro usa marcas mais restritivas que motor_regras para evitar
# FP (ex: "COM" em "FCOM" = Falha Comunicação, não Comando). "_C" e "CMD"
# são mais específicos.
_F5_MARCAS_COMANDO: tuple[str, ...] = ("CMD", "_CMD", "_C")


def _f5_eh_comando(sigla: str) -> bool:
    return any(m in sigla for m in _F5_MARCAS_COMANDO)


def f_r5(cand: Candidato, ctx: Contexto) -> bool:
    """Remove comando se texto é status, status se texto é comando.

    Usa marcas mais restritivas (CMD, _CMD, _C) para evitar FP com
    siglas como FCOM (Falha Comunicação).
    """
    tem_comando = bool(ctx.tokens & _TOKENS_COMANDO)
    sigla = cand.sigla.upper()
    eh_comando = _f5_eh_comando(sigla)
    if tem_comando and not eh_comando:
        return False  # texto comanda, candidato é status → REMOVE
    if not tem_comando and eh_comando:
        return False  # texto é status, candidato comanda → REMOVE
    return True


# --- F_Req: equipamento -----------------------------------------------------


def f_equip(cand: Candidato, ctx: Contexto) -> bool:
    """Remove se texto indica equipamento e sigla é de família DIFERENTE."""
    equip_cand = equipamento_da_sigla(cand.sigla.upper())
    if equip_cand is None:
        return True
    # procura token de equipamento no texto
    for tok in ctx.tokens:
        if tok in ("DISJUNTOR", "DJ"):
            return equip_cand == "Disjuntor"
        if tok in ("SECCIONADORA", "SEC"):
            return equip_cand == "Seccionadora"
    return True


# --- F_R6: lado / nível de tensão -------------------------------------------


def f_r6(cand: Candidato, ctx: Contexto) -> bool:
    """Remove se texto indica AT/BT e sigla tem marca do lado OPOSTO.

    Candidatos sem marca de lado (genéricos) são mantidos — só remove
    quando há conflito explícito.
    """
    lado = None
    for tok, lvl in _LADO_TEXTO.items():
        if tok in ctx.tokens:
            lado = lvl
            break
    if not lado:
        return True
    sigla = cand.sigla.upper()
    outro = "BT" if lado == "AT" else "AT"
    if _tem_marca(sigla, _MARCAS_LADO.get(outro, ())):
        return False  # texto diz AT, candidato é BT → REMOVE
    return True


# --- F_posicao: sigla de posição exige palavra de posição no texto ---------
#
# Task 6 (SP-G, Caso 2): DJA1 decidia com score fixo 0.858 sempre que o texto
# canônico colapsava para "DISJUNTOR <algo>" — mesmo quando <algo> não era
# palavra de posição (ex. "INTERTRAVAMENTO", "INDEFINIDO"). Gate: candidato
# cuja sigla é de POSIÇÃO (_SIGLAS_POSICAO) só sobrevive ao filtro se o texto
# tiver evidência real de posição (eh_texto_de_posicao) — senão é removido
# (cai pro fallback "não decidir" se não sobrar mais ninguém).


def f_posicao(cand: Candidato, rec: SignalRecord) -> bool:
    """Remove candidato de sigla de posição sem evidência de posição no texto."""
    if cand.sigla.upper() not in _SIGLAS_POSICAO:
        return True
    return eh_texto_de_posicao(rec.descricoes.normalizada)


# --- F_sf6: SF6 alarme (baixa pressão) × bloqueio ---------------------------
#
# conhecimento_sinais item 3: com "SF6" no texto, "baixa pressão" isolada é
# alarme (família SF6); "bloqueio"/"bloqueado" é a família de bloqueio
# (SF6B/SFAB/SFFC). Remove o candidato da família errada. Lê ``ctx.tokens``
# (não existe ``ctx.texto``); "baixa pressao" é o par de tokens BAIXA+PRESSAO.
_SF6_BLOQUEIO = frozenset({"SF6B", "SFAB", "SFFC"})


def f_sf6(cand: Candidato, ctx: Contexto) -> bool:
    """Remove candidato da família SF6 errada (alarme vs bloqueio)."""
    toks = ctx.tokens
    if "SF6" not in toks:
        return True
    tem_bloqueio = "BLOQUEIO" in toks or "BLOQUEADO" in toks
    tem_alarme = ("BAIXA" in toks and "PRESSAO" in toks) and not tem_bloqueio
    sig = cand.sigla.upper()
    if sig in _SF6_BLOQUEIO and tem_alarme:
        return False  # texto é alarme isolado, candidato é bloqueio → remove
    if sig == "SF6" and tem_bloqueio:
        return False  # texto é bloqueio, candidato é alarme → remove
    return True


# --- F_79lo: lockout do religador × bloqueio geral 86 (item 6) --------------
#
# conhecimento_sinais item 6: "religamento" no texto → o conceito é o lockout
# do religador (79LO), não o bloqueio geral (86/86BF/86AT/86BT). Remove os
# 86* quando há "religamento".
_BLOQUEIO_GERAL = frozenset({"86", "86BF", "86AT", "86BT"})


def f_79lo(cand: Candidato, ctx: Contexto) -> bool:
    """Remove bloqueio geral 86* quando o texto fala de religamento."""
    if "RELIGAMENTO" not in ctx.tokens:
        return True
    return cand.sigla.upper() not in _BLOQUEIO_GERAL


# --- F_50bf: start de falha de disjuntor × bloqueio consequente BF* (item 1) -
#
# conhecimento_sinais item 1: "falha de disjuntor"/"breaker failure" isolado
# (sem "bloqueio") é o START (50BF), não o bloqueio consequente (BF*/62BF).
# Remove os BF*/62BF quando o texto é só o start.
_BF_BLOQUEIO = frozenset({"BFAT", "BFBT", "BFP1", "BFP2", "BFP3", "62BF"})


def f_50bf(cand: Candidato, ctx: Contexto) -> bool:
    """Remove bloqueio BF*/62BF quando o texto é só o start de falha (sem bloqueio)."""
    toks = ctx.tokens
    falha = ("FALHA" in toks and "DISJUNTOR" in toks) or (
        "BREAKER" in toks and "FAILURE" in toks
    )
    if falha and "BLOQUEIO" not in toks:
        return cand.sigla.upper() not in _BF_BLOQUEIO
    return True


# Registro de filtros — adicione funções aqui para crescer.
_FILTROS = (
    f_r1,
    f_r2,
    f_r3,
    f_r4,
    f_r5,
    f_equip,
    f_r6,
    f_sf6,
    f_79lo,
    f_50bf,
)


def filtrar(
    rec: SignalRecord,
    candidatos: list[Candidato],
    config: Config | None = None,
) -> list[Candidato]:
    """Aplica todos os filtros. Remove candidatos que não passam em algum.

    Se o resultado for vazio, retorna a lista original (fallback — não
    decidir é melhor que decidir errado).
    """
    _ = config  # reservado para futuros gates por config
    ctx = Contexto.de(rec)
    resultado: list[Candidato] = []
    for cand in candidatos:
        manter = True
        for filtro in _FILTROS:
            if not filtro(cand, ctx):
                manter = False
                break
        if manter and not f_posicao(cand, rec):
            manter = False
        if manter:
            resultado.append(cand)
    return resultado if resultado else candidatos


# --- F_especificidade: variante específica vence o prefixo genérico ---------
#
# Dentro de uma família ANSI (mesmo nº líder de 2 dígitos), candidatos cuja
# descrição-padrão casa MAIS tokens discriminadores do texto vencem os que
# casam menos. Mata o erro "genérico (79/81/21) ganha por fuzzy=1.0 no número
# literal" sem dinâmica de pontos: só conta tokens e remove quem casa menos.
# Só remove quando há evidência estrita (alguém casa mais); empate mantém todos.

_DISC_CACHE: dict[int, dict[str, tuple[str, frozenset[str]]]] = {}
"""Cache id(lp) -> {sigla.upper(): (lider2dig, tokens_discriminadores)}."""


def _indice_discriminadores(
    lista_padrao, config: Config
) -> dict[str, tuple[str, frozenset[str]]]:
    from tdt.normalizacao.normalizador import canonizar  # import tardio: evita ciclo
    idx: dict[str, tuple[str, frozenset[str]]] = {}
    for s in (*lista_padrao.discretos, *lista_padrao.analogicos):
        sig = s.sigla.upper()
        lider = _numero_lider(sig)
        if lider is None or not s.descricao or sig in idx:
            continue
        toks = frozenset(canonizar(s.descricao, config).split()) - {lider}
        idx[sig] = (lider, toks)
    return idx


def filtrar_especificidade(
    rec: SignalRecord,
    candidatos: list[Candidato],
    lista_padrao,
    config: Config | None = None,
) -> list[Candidato]:
    """Por família ANSI, mantém os candidatos que casam o MÁXIMO de tokens
    discriminadores do texto; remove os que casam estritamente menos.

    Candidatos sem nº líder ou fora do índice não são tocados. Empate (ou
    nenhum casamento) preserva o grupo inteiro. Fallback: nunca esvazia.
    """
    if config is None or lista_padrao is None or len(candidatos) < 2:
        return candidatos
    lp_id = id(lista_padrao)
    if lp_id not in _DISC_CACHE:
        _DISC_CACHE[lp_id] = _indice_discriminadores(lista_padrao, config)
    idx = _DISC_CACHE[lp_id]
    texto = frozenset(rec.descricoes.normalizada.upper().split())

    grupos: dict[str, list[Candidato]] = {}
    soltos: list[Candidato] = []
    for c in candidatos:
        info = idx.get(c.sigla.upper())
        if info is None:
            soltos.append(c)
        else:
            grupos.setdefault(info[0], []).append(c)

    resultado: list[Candidato] = list(soltos)
    for grupo in grupos.values():
        if len(grupo) < 2:
            resultado.extend(grupo)
            continue
        casa = {c.sigla.upper(): len(idx[c.sigla.upper()][1] & texto) for c in grupo}
        mx = max(casa.values())
        if mx == 0:
            resultado.extend(grupo)  # sem evidência: não decide
        else:
            resultado.extend(c for c in grupo if casa[c.sigla.upper()] == mx)
    return resultado if resultado else candidatos
