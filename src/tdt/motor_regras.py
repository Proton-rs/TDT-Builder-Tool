"""Motor de regras de domínio — incrementa/decrementa scores de candidatos.

Cada regra é uma **função pura** ``regra(rec, candidato, contexto) -> AjusteRegra``
(delta + motivo). Um registro (tupla) de regras é aplicado; os deltas somam ao
score e os ``motivo``s alimentam a justificativa (rastreabilidade). Regras novas
= novas funções no registro, sem reescrever as existentes (SRP).

Os deltas base vêm de ``config.pesos_regras[<chave>]`` (calibráveis), nunca
hardcoded. Pistas vêm do texto canônico (``rec.descricoes.normalizada``) e do
contexto elétrico (``rec.eletrico``).

ponytail: regras como funções numa tupla; cresce adicionando funções, não
reescrevendo. SP2 (LLM) pluga via Avaliador, não aqui.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from tdt.config import Config
from tdt.contracts import AjusteRegra, Candidato, SignalRecord
from tdt.semantica_estados import INDEFINIDO, classe_do_mm, detectar_estado

_ZERO = AjusteRegra(0.0, "")


@dataclass(frozen=True)
class Contexto:
    """Pistas pré-extraídas da linha, compartilhadas por todas as regras.

    Evita recomputar split/regex por candidato. ``tokens`` é o conjunto de
    tokens do texto canônico; ``eletrico`` é o sub-registro elétrico.
    ``lista_padrao`` (opcional) permite a regras consultarem o Message
    Mapping de um candidato (``lista_padrao.por_sigla(sigla).mm``) — ausente
    (``None``) para chamadores que não a possuem (ex. bench/benchmark.py);
    regras que dependem dela devem ser no-op nesse caso.
    """

    tokens: frozenset[str]
    eletrico: object  # tdt.contracts.Eletrico (evita import circular de tipo)
    lista_padrao: object | None = None  # tdt.dados.lista_padrao.ListaPadraoADMS

    @classmethod
    def de(cls, rec: SignalRecord, lista_padrao: object | None = None) -> Contexto:
        return cls(
            tokens=frozenset(rec.descricoes.normalizada.upper().split()),
            eletrico=rec.eletrico,
            lista_padrao=lista_padrao,
        )


# --- R1: número de proteção -------------------------------------------------

# Funções ANSI/IEEE comuns em proteção de subestação.
_NUMEROS_PROTECAO: frozenset[str] = frozenset(
    {
        "21", "25", "27", "32", "37", "40", "46", "47", "49", "50", "51",
        "55", "59", "67", "78", "79", "81", "85", "86", "87",
    }
)


def _numero_lider(sigla: str) -> str | None:
    """Número ANSI que lidera a sigla (ex.: '67N' -> '67', 'DJ' -> None)."""
    digitos = ""
    for ch in sigla:
        if ch.isdigit():
            digitos += ch
        else:
            break
    # Aceita prefixo de 2 dígitos do catálogo (67N, 51G, 50/51 -> '50').
    return digitos[:2] if len(digitos) >= 2 else None


def _numeros_no_texto(tokens: frozenset[str]) -> set[str]:
    achados: set[str] = set()
    for tok in tokens:
        lider = _numero_lider(tok)
        if lider in _NUMEROS_PROTECAO:
            achados.add(lider)
    return achados


def r1_numero_protecao(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Número de proteção compartilhado (boost) / divergente (penalidade)."""
    numeros = _numeros_no_texto(ctx.tokens)
    if not numeros:
        return _ZERO
    lider = _numero_lider(cand.sigla.upper())
    if lider is None:
        return _ZERO
    peso = cfg.pesos_regras["numero_protecao"]
    if lider in numeros:
        return AjusteRegra(peso, f"numero_protecao: sigla {cand.sigla} casa {lider}")
    return AjusteRegra(
        -peso, f"numero_protecao: sigla {cand.sigla} diverge de {sorted(numeros)}"
    )


# --- R2: pares opostos (hard/soft negatives) --------------------------------


@dataclass(frozen=True)
class ParOposto:
    """Par confusável + tokens discriminadores por polaridade.

    Quando ``token_a`` está no texto, candidatos com marca da polaridade B são
    penalizados (e vice-versa). ``marca_a``/``marca_b`` identificam a polaridade
    do candidato na sigla; ``tokens_a``/``tokens_b`` são as pistas no texto.
    """

    nome: str
    tokens_a: tuple[str, ...]
    tokens_b: tuple[str, ...]
    marca_a: tuple[str, ...]
    marca_b: tuple[str, ...]


# Catálogo modelado como dado — cresce adicionando linhas, não código.
_PARES_OPOSTOS: tuple[ParOposto, ...] = (
    ParOposto(
        nome="sobrecorrente_x_subcorrente",
        tokens_a=("SOBRECORRENTE", "SOBRE"),
        tokens_b=("SUBCORRENTE", "SUB"),
        marca_a=("50", "51", "67", "37SOBRE"),
        marca_b=("37",),
    ),
    ParOposto(
        nome="sobretensao_x_subtensao",
        tokens_a=("SOBRETENSAO", "59"),
        tokens_b=("SUBTENSAO", "27"),
        marca_a=("59",),
        marca_b=("27",),
    ),
    ParOposto(
        nome="tap_max_x_min",
        tokens_a=("MAX", "MAXIMO"),
        tokens_b=("MIN", "MINIMO"),
        marca_a=("MAX",),
        marca_b=("MIN",),
    ),
    ParOposto(
        nome="ligado_x_desligado",
        tokens_a=("LIGADO", "LIGAR"),
        tokens_b=("DESLIGADO", "DESLIGAR"),
        marca_a=("LIGADO", "LIGAR", "LIG"),
        marca_b=("DESLIGADO", "DESLIGAR", "DESLIG"),
    ),
    ParOposto(
        nome="barra_x_linha",
        tokens_a=("BARRA",),
        tokens_b=("LINHA",),
        marca_a=("_B", "BARRA"),
        marca_b=("_L", "LINHA"),
    ),
)


def _tem_marca(sigla: str, marcas: tuple[str, ...]) -> bool:
    return any(m in sigla for m in marcas)


def r2_opostos(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Desambiguação de pares opostos: penaliza candidato de polaridade contrária."""
    sigla = cand.sigla.upper()
    peso = cfg.pesos_regras["opostos"]
    for par in _PARES_OPOSTOS:
        texto_a = any(t in ctx.tokens for t in par.tokens_a)
        texto_b = any(t in ctx.tokens for t in par.tokens_b)
        if texto_a == texto_b:
            continue  # nenhum discriminador, ou ambos (ambíguo) -> não decide
        if texto_a and _tem_marca(sigla, par.marca_b):
            return AjusteRegra(-peso, f"opostos[{par.nome}]: contraria polaridade A")
        if texto_b and _tem_marca(sigla, par.marca_a):
            return AjusteRegra(-peso, f"opostos[{par.nome}]: contraria polaridade B")
    return _ZERO


# --- R3: fase ---------------------------------------------------------------


def fase_da_sigla(sigla: str) -> str | None:
    # Remove dígito de estágio à direita (67N1 -> 67N) p/ ler a fase, não o estágio.
    base = sigla[:-1] if len(sigla) > 1 and sigla[-1] in "1234" else sigla
    if base.endswith("N"):
        return "N"
    for f in ("ABC", "AB", "BC", "CA"):
        if base.endswith(f):
            return f
    if base.endswith("F"):
        return "F"  # fase pura genérica
    if base and base[-1] in ("A", "B", "C"):
        return base[-1]
    return None


def r3_fase(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Fase (A/B/C/N/AB/BC/CA/ABC): favorece mesma fase, penaliza divergente.

    ``ctx.eletrico.fase`` já vem preenchido pela normalização (N0,
    ``normalizador.extrair_contexto_estrutural``) — esta regra não re-deriva
    do texto, só lê o que já foi extraído.
    """
    alvo = getattr(ctx.eletrico, "fase", None) if ctx.eletrico is not None else None
    if not alvo:
        return _ZERO
    fase_cand = fase_da_sigla(cand.sigla.upper())
    if fase_cand is None:
        return _ZERO
    peso = cfg.pesos_regras["fase"]
    if fase_cand == "F" and alvo in ("ABC", "AB", "BC", "CA"):
        # D2.3: sigla de fase pura genérica (ex: 50F1) é compatível com um
        # alvo multi-fase do texto (ex: "50 ABC") -- não é divergência, é a
        # mesma generalidade. Não estende a fase específica única (A/B/C/N):
        # a sigla com letra explícita já compara exato e deve prevalecer.
        return AjusteRegra(peso, f"fase: candidato genérico compatível com {alvo}")
    if fase_cand == alvo:
        return AjusteRegra(peso, f"fase: candidato e texto em {alvo}")
    return AjusteRegra(-peso, f"fase: candidato {fase_cand} diverge de {alvo}")


# --- R4: estágio ------------------------------------------------------------

_ESTAGIOS: frozenset[str] = frozenset({"E1", "E2", "E3", "E4"})


def r4_estagio(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Estágio (E1–E4): favorece sigla terminando no dígito do estágio."""
    estagios = ctx.tokens & _ESTAGIOS
    if not estagios:
        return _ZERO
    digito = next(iter(estagios))[1]
    if cand.sigla.endswith(digito):
        peso = cfg.pesos_regras["estagio"]
        return AjusteRegra(peso, f"estagio: sigla termina em E{digito}")
    return _ZERO


def estagio_texto(texto_tokens: set[str]) -> str | None:
    """Dígito de estágio (E1–E4) presente nos tokens do texto, ou None."""
    estagios = texto_tokens & _ESTAGIOS
    if not estagios:
        return None
    return next(iter(estagios))[1]


def estagio_da_sigla(sigla: str) -> str | None:
    """Dígito final da sigla, ou None se o último caractere não é dígito."""
    if sigla and sigla[-1].isdigit():
        return sigla[-1]
    return None


# --- R5: comando × status ---------------------------------------------------

_TOKENS_COMANDO: frozenset[str] = frozenset(
    {"LIGAR", "DESLIGAR", "COMANDO", "CONTROLE", "ABRIR", "FECHAR", "CMD"}
)
_MARCAS_COMANDO: tuple[str, ...] = ("CMD", "_CMD", "COM", "_C")


def r5_comando_status(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Comando × status: comando no texto favorece candidato com direção de comando."""
    if not (ctx.tokens & _TOKENS_COMANDO):
        return _ZERO
    sigla = cand.sigla.upper()
    peso = cfg.pesos_regras["comando_status"]
    if _tem_marca(sigla, _MARCAS_COMANDO):
        return AjusteRegra(peso, "comando_status: candidato de comando")
    return AjusteRegra(-peso, "comando_status: candidato de status sob contexto comando")


# --- R_equip: equipamento -----------------------------------------------

_EQUIPAMENTO_SIGLA: tuple[tuple[str, str], ...] = (
    ("DJ", "Disjuntor"),
    ("SEC", "Seccionadora"),
)


def equipamento_da_sigla(sigla: str) -> str | None:
    for prefixo, nome in _EQUIPAMENTO_SIGLA:
        if sigla.startswith(prefixo):
            return nome
    return None


def r_equipamento(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Penaliza candidato de família de equipamento diferente da detectada
    na descrição (Disjuntor vs Seccionadora) — ctx.eletrico.equipamento_alvo
    vem da extração estrutural (N0) em normalizador.py."""
    alvo = getattr(ctx.eletrico, "equipamento_alvo", None) if ctx.eletrico is not None else None
    if not alvo:
        return _ZERO
    equip_cand = equipamento_da_sigla(cand.sigla.upper())
    if equip_cand is None or equip_cand == alvo:
        return _ZERO
    peso = cfg.pesos_regras["equipamento"]
    return AjusteRegra(-peso, f"equipamento: candidato e {equip_cand}, descricao indica {alvo}")


# --- R6: lado / nível de tensão ---------------------------------------------

_LADO_TEXTO: dict[str, str] = {
    "PRIMARIO": "AT",
    "PRIMARIA": "AT",
    "ALTA": "AT",
    "AT": "AT",
    "SECUNDARIO": "BT",
    "SECUNDARIA": "BT",
    "BAIXA": "BT",
    "BT": "BT",
}
_MARCAS_LADO: dict[str, tuple[str, ...]] = {
    "AT": ("AT", "_AT", "PRIM"),
    "BT": ("BT", "_BT", "SEC"),
}


def r6_lado_tensao(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Lado/nível de tensão (AT/BT, primário/secundário): favorece candidato do lado."""
    lado = None
    for tok, lvl in _LADO_TEXTO.items():
        if tok in ctx.tokens:
            lado = lvl
            break
    if lado is None and ctx.eletrico is not None:
        lado = getattr(ctx.eletrico, "nivel_tensao", None)
    if not lado:
        return _ZERO
    sigla = cand.sigla.upper()
    peso = cfg.pesos_regras["lado_tensao"]
    if _tem_marca(sigla, _MARCAS_LADO.get(lado, ())):
        return AjusteRegra(peso, f"lado_tensao: candidato em {lado}")
    outro = "BT" if lado == "AT" else "AT"
    if _tem_marca(sigla, _MARCAS_LADO.get(outro, ())):
        return AjusteRegra(-peso, f"lado_tensao: candidato em {outro}, texto em {lado}")
    return _ZERO


# --- R7: estado compatível (SP-G Task 7) -------------------------------------


def r7_estado_compativel(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Estado do texto (evento/posição/função/...) × classe do MM do candidato.

    Casa (ex.: texto "ATUADO" = EVENTO, e MM do candidato também é EVENTO):
    boost. Diverge (ex.: texto EVENTO, MM é FUNCAO): penalidade. Não reimplementa
    extração/comparação de estados — usa ``semantica_estados`` (SP-E) tal qual.
    Requer ``ctx.lista_padrao`` para consultar o MM do candidato; ausente
    (chamador não a threadeou, ex. bench/benchmark.py) = no-op seguro.
    """
    if ctx.lista_padrao is None:
        return _ZERO
    est = detectar_estado(rec.descricoes.normalizada)
    if est is None or est.classe == INDEFINIDO:
        return _ZERO
    sp = ctx.lista_padrao.por_sigla(cand.sigla)
    classe_mm = classe_do_mm(sp.mm if sp else None)
    if classe_mm is None:
        return _ZERO
    peso = cfg.pesos_regras["estado"]
    if classe_mm == est.classe:
        return AjusteRegra(peso, f"estado: candidato e texto em {est.classe}")
    return AjusteRegra(
        -peso, f"estado: candidato em {classe_mm} diverge de {est.classe}"
    )


# --- R8: direção (comando exige escrita) --------------------------------------


def r8_direcao(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """Input com comando (Output/InputOutput) favorece candidato ReadWrite/Write
    e penaliza Read puro. ASSIMÉTRICA de propósito: input só-leitura é no-op —
    status de equipamento manobrável (DJ) casa sigla ReadWrite legitimamente
    (par comando+status resolvido pelo dc_pairer); penalizar quebraria esse
    caminho. Requer ctx.lista_padrao (ausente = no-op, contrato da r7)."""
    if ctx.lista_padrao is None:
        return _ZERO
    if rec.tipo_sinal.direcao not in ("Output", "InputOutput"):
        return _ZERO
    sp = ctx.lista_padrao.por_sigla(cand.sigla)
    if sp is None or not sp.direction:
        return _ZERO
    peso = cfg.pesos_regras["direcao"]
    if sp.direction in ("ReadWrite", "Write"):
        return AjusteRegra(peso, f"direcao: comando casa candidato {sp.direction}")
    return AjusteRegra(-peso, "direcao: comando mas candidato so-leitura (Read)")


# --- R10: fase estruturada da LP (AnalogSignals, 2B) -------------------------

_FASES_LP: dict[str, str] = {"L1": "A", "L2": "B", "L3": "C"}


def _fases_da_lp(valor: str) -> str:
    """Traduz FASES da LP ('L1 L2 L3', 'L2', 'N', ...) p/ letras A/B/C (mantém N)."""
    letras = sorted({_FASES_LP.get(t, t) for t in valor.upper().split()})
    return "".join(letras)


def r10_fase_lp(
    rec: SignalRecord, cand: Candidato, ctx: Contexto, cfg: Config
) -> AjusteRegra:
    """FASES estruturada da AnalogSignals × fase extraída do texto (2B).

    Requer ctx.lista_padrao (ausente = no-op, contrato da r7/r8); só atua
    sobre candidatos analógicos cuja LP traz FASES preenchida.
    """
    if ctx.lista_padrao is None or ctx.eletrico is None or not ctx.eletrico.fase:
        return _ZERO
    sp = ctx.lista_padrao.por_sigla(cand.sigla)
    if sp is None or sp.categoria != "Analog" or not sp.fases:
        return _ZERO
    peso = cfg.pesos_regras["fase"]
    lp_fases = _fases_da_lp(sp.fases)
    if ctx.eletrico.fase in lp_fases or lp_fases == "ABC":
        return AjusteRegra(peso, f"fase LP: {sp.fases} compatível com {ctx.eletrico.fase}")
    return AjusteRegra(-peso, f"fase LP: {sp.fases} diverge de {ctx.eletrico.fase}")


# Registro de regras — adicione funções aqui para crescer (SRP, sem reescrita).
_REGRAS = (
    r1_numero_protecao,
    r2_opostos,
    r3_fase,
    r4_estagio,
    r5_comando_status,
    r_equipamento,
    r6_lado_tensao,
    r7_estado_compativel,
    r8_direcao,
    r10_fase_lp,
)


def aplicar_rastreado(
    rec: SignalRecord,
    candidatos: list[Candidato],
    config: Config | None = None,
    lista_padrao: object | None = None,  # tdt.dados.lista_padrao.ListaPadraoADMS
) -> tuple[list[Candidato], list[AjusteRegra]]:
    """Aplica o registro de regras, reordena e devolve os ajustes que atuaram.

    Retorna ``(candidatos_reordenados, ajustes)``; ``ajustes`` traz só os
    ``AjusteRegra`` com delta != 0 (motivos legíveis para a justificativa).
    ``lista_padrao`` é opcional (retrocompat: chamadores existentes que não a
    passam mantêm o comportamento antigo — regras que dependem dela, ex.
    ``r7_estado_compativel``, são no-op nesse caso).
    """
    cfg = config or Config()
    ctx = Contexto.de(rec, lista_padrao)
    ajustados: list[Candidato] = []
    atuantes: list[AjusteRegra] = []
    for cand in candidatos:
        delta_total = 0.0
        for regra in _REGRAS:
            ajuste = regra(rec, cand, ctx, cfg)
            if ajuste.delta:
                delta_total += ajuste.delta
                atuantes.append(ajuste)
        ajustados.append(replace(cand, score=cand.score + delta_total))
    ajustados.sort(key=lambda c: c.score, reverse=True)
    return ajustados, atuantes


def aplicar(
    rec: SignalRecord,
    candidatos: list[Candidato],
    config: Config | None = None,
    lista_padrao: object | None = None,  # tdt.dados.lista_padrao.ListaPadraoADMS
) -> list[Candidato]:
    """Soma deltas das regras aos scores e reordena (desc). Retrocompat: 2 args."""
    ajustados, _ = aplicar_rastreado(rec, candidatos, config, lista_padrao)
    return ajustados
