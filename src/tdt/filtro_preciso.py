"""Filtro preciso de candidatos — remove siglas que contradizem pistas do texto.

Diferente do ``motor_regras`` (que ajusta scores com deltas), este módulo
**remove** candidatos que claramente não satisfazem as condições do texto.
Cada regra retorna ``bool``: ``True`` = mantém, ``False`` = remove.

Se o filtro eliminar todos os candidatos, retorna a lista original (fallback
seguro — não decidir é melhor que decidir errado).

Reusa constantes e helpers de ``motor_regras`` (nunca o chama diretamente).
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


# Registro de filtros — adicione funções aqui para crescer.
_FILTROS = (
    f_r1,
    f_r2,
    f_r3,
    f_r4,
    f_r5,
    f_equip,
    f_r6,
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
