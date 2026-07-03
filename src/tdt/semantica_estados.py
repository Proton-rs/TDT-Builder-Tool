"""Semântica de estados (SP-E D1) — classifica o par-de-estado que uma
descrição de sinal descreve e o compara com o par de estados do Message
Mapping da lista padrão. Base do filtro duro (D2), da fusão restrita (D3)
e do gate semântico do pareamento D+C (D5).

Classes derivadas dos pares reais do Export Base Full (237k sinais DNP3):
NORMAL@ATUADO (108k) e NORMAL@FALHA/DEFEITO/FALTA compartilham semântica de
"evento/alarme" — trips Custom existem (79_1, FCSF), então trip e alarme
ficam numa classe só (EVENTO); a distinção que importa é contra FUNCAO/
POSICAO/ATIVACAO/LOCAL_REMOTO.
"""

from __future__ import annotations

from dataclasses import dataclass

POSICAO = "posicao"          # aberto/fechado, ligado/desligado (SwitchStatus)
FUNCAO = "funcao"            # incluído/excluído (Enabled/ReclosingEnabled/Local)
ATIVACAO = "ativacao"        # ativado/desativado, habilitado/desabilitado
LOCAL_REMOTO = "local_remoto"
EVENTO = "evento"            # atuado, falha, defeito, falta, bloqueio
INDEFINIDO = "indefinido"    # transit de posição — nunca vira ponto (D3)


@dataclass(frozen=True)
class EstadoDetectado:
    classe: str
    # POSICAO: "A" = fechado/ligado, "B" = aberto/desligado. Demais: None.
    polaridade: str | None = None


# prefixo de token (texto upper, sem acentos — descrição normalizada) ->
# (classe, polaridade). Prefixos ancorados no INÍCIO do token, então
# "DESLIGADO".startswith("LIGA") é False — sem colisão LIGA/DESLIGA.
_LEXICO: tuple[tuple[str, str, str | None], ...] = (
    ("FECHA", POSICAO, "A"), ("LIGA", POSICAO, "A"),
    ("ABERT", POSICAO, "B"), ("ABRIR", POSICAO, "B"), ("DESLIGA", POSICAO, "B"),
    ("INCLUI", FUNCAO, None), ("EXCLUI", FUNCAO, None),
    ("ATIVA", ATIVACAO, None), ("DESATIVA", ATIVACAO, None),
    ("HABILITA", ATIVACAO, None), ("DESABILITA", ATIVACAO, None),
    ("REMOT", LOCAL_REMOTO, None),
    ("ATUAD", EVENTO, None), ("FALHA", EVENTO, None),
    ("DEFEITO", EVENTO, None), ("FALTA", EVENTO, None),
    ("BLOQUE", EVENTO, None), ("LIBERA", EVENTO, None),
    ("INDEFINID", INDEFINIDO, None),
)

# "LOCAL" é palavra completa (não radical) — prefixo colide com LOCALIZADOR
# (ANSI 21D, classe real EVENTO). Token exato em vez de startswith.
_TOKENS_EXATOS: dict[str, tuple[str, str | None]] = {
    "LOCAL": (LOCAL_REMOTO, None),
}


def _classificar_token(tok: str) -> tuple[str, str | None] | None:
    if tok in _TOKENS_EXATOS:
        return _TOKENS_EXATOS[tok]
    for prefixo, classe, pol in _LEXICO:
        if tok.startswith(prefixo):
            return classe, pol
    return None


def detectar_estado(texto: str | None) -> EstadoDetectado | None:
    """Classe de estado da descrição, ou None (sem evidência OU ambígua).

    Mais de uma classe distinta no texto (ex. "FALHA COMANDO DE LIGAR" tem
    EVENTO+POSICAO) = ambíguo -> None: filtro nenhum é melhor que errado.
    INDEFINIDO vence qualquer outra (marcador estrutural, não par de estado).
    """
    if not texto:
        return None
    achados = [r for tok in texto.upper().split() if (r := _classificar_token(tok))]
    if not achados:
        return None
    classes = {c for c, _ in achados}
    if INDEFINIDO in classes:
        return EstadoDetectado(INDEFINIDO)
    if len(classes) > 1:
        return None
    pols = {p for _, p in achados if p is not None}
    pol = pols.pop() if len(pols) == 1 else None
    return EstadoDetectado(classes.pop(), pol)


def classe_do_mm(mm: str | None) -> str | None:
    """Classe do par de estados de um MM da lista padrão.

    Formato: "{CMD0@CMD1}___{EST0@EST1}___{Type}_{flags}". Alguns MMs reais
    usam "__" simples após os estados (ex. "...REMOTO@LOCAL__Local_S_TS_SS"),
    então o segmento de estados é cortado no primeiro "__" interno.
    """
    if not mm:
        return None
    partes = mm.split("___")
    if len(partes) < 2:
        return None
    estados = partes[1].split("__")[0]
    classes: set[str] = set()
    for est in estados.split("@"):
        r = _classificar_token(est.strip().upper())
        if r:
            classes.add(r[0])
    return classes.pop() if len(classes) == 1 else None


def compativel(estado: EstadoDetectado | None, classe_mm: str | None) -> bool:
    """Filtro duro D2: sem evidência de um dos lados = compatível."""
    if estado is None or classe_mm is None:
        return True
    if estado.classe == INDEFINIDO:
        return True  # tratado estruturalmente (D3), não pelo matching
    return estado.classe == classe_mm


def compatibilidade_texto(a: str | None, b: str | None) -> bool:
    """Dois textos podem descrever o mesmo ponto? (gate do pareamento D+C)."""
    ea, eb = detectar_estado(a), detectar_estado(b)
    if ea is None or eb is None:
        return True
    if INDEFINIDO in (ea.classe, eb.classe):
        return True
    return ea.classe == eb.classe


def filtrar_por_estado(rec, candidatos, lp):
    """(mantidos, zerou). zerou=True: havia candidatos e o filtro eliminou
    todos — o chamador manda para revisão com os ORIGINAIS como sugestão."""
    est = detectar_estado(rec.descricoes.normalizada)
    if est is None or est.classe == INDEFINIDO or not candidatos:
        return candidatos, False
    mantidos = []
    for c in candidatos:
        sp = lp.por_sigla(c.sigla)
        if compativel(est, classe_do_mm(sp.mm if sp else None)):
            mantidos.append(c)
    if not mantidos:
        return candidatos, True
    return mantidos, False
