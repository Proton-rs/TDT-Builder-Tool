"""Normalização pré-análise de descrições.

A normalização define o texto que TODOS os scorers consomem: lixo entra, lixo
sai. Por isso o pipeline é uma sequência de transforms SRP, cada um função pura
``str -> str`` (N0 e N2 devolvem ``(str, contexto)``), fáceis de testar isolados:

    bruto
      -> N0 extrair_contexto_estrutural (equipamento ANSI/barra/fase do texto
         BRUTO, antes do hífen e do stopword "A" serem destruídos — chamado
         por estruturador.py, não por canonizar(); ver Eletrico.*)
      -> N1 expandir_abreviacoes (whole-token, não quebra siglas)
      -> N2 separar_ids_equipamento (remove ID letra-número tipo "01Q0";
         IDs hifenados de equipamento já saíram em N0, não chegam aqui)
      -> N3 remover_boilerplate (prefixo de equipamento dilui o match)
      -> N4 corrigir_typos (fuzzy contra vocabulário de domínio, se dado)
      -> N5 normalizar_unidades (kV/A/MW canônicos)
      -> tokenizer (rejunta siglas separadas)
      -> canônico

``normalizar`` e ``canonizar`` permanecem retrocompatíveis para quem já chama
(``canonizar`` não chama N0 — quem precisa do contexto estrutural chama
``extrair_contexto_estrutural`` antes e passa o texto remanescente).

ponytail: stemming baseado na base fica para quando medir que faz diferença.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from rapidfuzz import fuzz

from ..config import Config
from .tokenizer import tokenizar

_SEPARADORES = re.compile(r"[/\-.(),;:]")
_SIGLA_ENTRE_PAREN = re.compile(r"\(([^)]+)\)")  # N0.5 — conteúdo relevante entre parênteses

# ponytail: só extrai conteúdo textual entre parênteses. Se houver casos com
# parênteses aninhados ou marcação semântica (ex: (NAO UTILIZAR)), expandir
# com filtro de exclusão por heurística.


def preservar_siglas_especiais(texto: str) -> str:
    """N0.5: extrai conteúdo de (sigla/número), remove parênteses, reinsere.

    Roda ANTES do colapso de separadores em ``normalizar()`` para que
    "(N0.5)" vire "N0.5" (com o ponto preservado), não "N0 5".
    """
    return _SIGLA_ENTRE_PAREN.sub(r" \1 ", texto)


# N0 — extração estrutural (texto bruto, antes do colapso de separadores).
_EQUIPAMENTO_ANSI: dict[str, str] = {
    "52": "Disjuntor",
    "89": "Seccionadora",
    "29": "Seccionadora",  # seccionadora de aterramento
}
_ID_EQUIPAMENTO = re.compile(r"\b(\d+)-(\d+)\b")
# Equipamento pela PALAVRA (whole-token), quando o código ANSI (52/89/29) não
# aparece. Listas reais usam IDs fora do padrão ANSI (ex: "24-1 DISJUNTOR"),
# então só o código não basta pra setar equipamento_alvo. "SEC" sozinho é
# ambíguo (SECUNDARIO) e fica de fora de propósito.
_EQUIPAMENTO_PALAVRA: dict[str, str] = {
    "DISJUNTOR": "Disjuntor", "DISJ": "Disjuntor", "DJ": "Disjuntor",
    "SECCIONADORA": "Seccionadora", "SECCION": "Seccionadora", "SECC": "Seccionadora",
}
_BARRA: dict[str, str] = {"P": "Principal", "A": "Auxiliar"}
_MARCADOR_BARRA = re.compile(r"\bBARRA\s+([A-Z])\b")
FASES: tuple[str, ...] = ("ABC", "AB", "BC", "CA", "A", "B", "C", "N")
_FASE_TOKENS: dict[str, str] = {
    "NEUTRO": "N",
    "TRIFASICO": "ABC",
    "TRIFASICA": "ABC",
}

# Pontuação periférica que pode colar em siglas/palavras em input real (ex:
# "Secc." / "Disj."). Usada só para as CHECAGENS de pertencimento a dicionário
# nos lookups por palavra (equipamento/fase) -- o token original (com a
# pontuação) continua sendo o que é removido/mantido no texto remanescente.
_PONTUACAO_BORDA = ".,;:()"


def _tok_limpo(tok: str) -> str:
    return tok.strip(_PONTUACAO_BORDA)


def _fase_no_texto(tokens: list[str]) -> tuple[str | None, str | None]:
    """Devolve (fase, token_origem) ou (None, None).

    O 2º item identifica o token que casou (histórico: já foi usado para
    remoção do texto remanescente). Desde spG/Task 3 o token NÃO é mais
    removido -- o chamador só anota ``ctx.fase`` e deixa o texto intacto,
    já que D2.1 (``_eh_letra_fase_apos_fase``) protege a letra do filtro de
    stopwords adiante. Mantido na assinatura para menor diff.
    """
    for i, tok in enumerate(tokens):
        if _tok_limpo(tok) in _FASE_TOKENS:
            return _FASE_TOKENS[_tok_limpo(tok)], tok
    tokens_limpos = [_tok_limpo(t) for t in tokens]
    if "FASE" in tokens_limpos:
        idx = tokens_limpos.index("FASE")
        if idx + 1 < len(tokens) and tokens_limpos[idx + 1] in FASES:
            return tokens_limpos[idx + 1], tokens[idx + 1]
    # D2.2: "<líder ANSI 2-3 dígitos> <fase multi-letra>" sem a palavra "FASE"
    # (ex: "50 ABC"). Restrito a multi-letra (ABC/AB/BC/CA): uma letra única
    # (A/B/C/N) sozinha após um número é ambígua demais (não é exclusivamente
    # fase) e descrições-padrão tipo "...NEUTRO..." não compartilham token com
    # a letra "N" -- extrair "N" aqui só perde sinal de texto sem ganho.
    # Só dispara se os padrões acima (prioritários) não capturaram nada.
    for i, tok in enumerate(tokens):
        tok_limpo = _tok_limpo(tok)
        if (
            tok_limpo.isdigit() and len(tok_limpo) in (2, 3)
            and i + 1 < len(tokens) and tokens_limpos[i + 1] in ("ABC", "AB", "BC", "CA")
        ):
            return tokens_limpos[i + 1], tokens[i + 1]
    return None, None


@dataclass(frozen=True)
class ContextoEstrutural:
    equipamento_alvo: str | None = None
    nome_equipamento: str | None = None  # "52-2" — ID bruto
    barra: str | None = None
    fase: str | None = None


def extrair_contexto_estrutural(texto: str) -> tuple[str, ContextoEstrutural]:
    """N0: extrai equipamento/barra/fase do texto BRUTO (antes do colapso de
    separadores em normalizar() destruir o hífen e o stopword 'A' comer a
    fase). Devolve (texto_remanescente, ContextoEstrutural)."""
    if not texto:
        return "", ContextoEstrutural()
    base = _sem_acentos(texto).upper()

    equipamento_alvo = None
    nome_equipamento = None
    m = _ID_EQUIPAMENTO.search(base)
    if m:
        equipamento_alvo = _EQUIPAMENTO_ANSI.get(m.group(1))
        nome_equipamento = f"{m.group(1)}-{m.group(2)}"
        base = (base[: m.start()] + " " + base[m.end() :]).strip()
        base = " ".join(base.split())

    if equipamento_alvo is None:
        for tok in base.split():
            tok_limpo = _tok_limpo(tok)
            if tok_limpo in _EQUIPAMENTO_PALAVRA:
                equipamento_alvo = _EQUIPAMENTO_PALAVRA[tok_limpo]
                break

    barra = None
    m_barra = _MARCADOR_BARRA.search(base)
    if m_barra and m_barra.group(1) in _BARRA:
        barra = _BARRA[m_barra.group(1)]
        inicio, fim = m_barra.span(1)
        base = (base[:inicio] + " " + base[fim:]).strip()
        base = " ".join(base.split())

    tokens = base.split()
    fase, _tok = _fase_no_texto(tokens)
    # anota apenas; o token fica no texto (discriminador para os scorers,
    # D2.1 já protege a letra do filtro de stopwords adiante)

    return base, ContextoEstrutural(
        equipamento_alvo=equipamento_alvo, nome_equipamento=nome_equipamento, barra=barra, fase=fase,
    )

# N1 — abreviações de domínio extra (mescladas com config.abreviacoes; config
# tem prioridade). Whole-token: só expandem quando o token inteiro casa, nunca
# quebram siglas. Listadas no summary para o orquestrador migrar ao config.
ABREVIACOES_EXTRA: dict[str, str] = {
    "DISJ": "DISJUNTOR",
    "SECC": "SECCIONADORA",
    "SECCION": "SECCIONADORA",
    "TRAFO": "TRANSFORMADOR",
    "TRANSF": "TRANSFORMADOR",
    "REL": "RELE",
    "CDC": "COMUTADOR DERIVACAO CARGA",
    "COMUT": "COMUTADOR",
    "TENS": "TENSAO",
    "CORR": "CORRENTE",
    "POT": "POTENCIA",
    "TEMP": "TEMPERATURA",
    "PRESS": "PRESSAO",
    "BLOQ": "BLOQUEIO",
    "SINAL": "SINALIZACAO",
    "SINALIZ": "SINALIZACAO",
    "ALARM": "ALARME",
    "DEFEITO": "DEFEITO",
    "FALHA": "FALHA",
    "OPER": "OPERACAO",
    "MAN": "MANUAL",
    "AUT": "AUTOMATICO",
    "DIFER": "DIFERENCIAL",
    "SOBREC": "SOBRECORRENTE",
    "RELIG": "RELIGADOR",
    "MEDIC": "MEDICAO",
    "SUCEDIDO": "SUCESSO",
}

# N2 — IDs de equipamento letra-número (contexto, não sinal). Calibrada para
# NÃO casar números de função de proteção (67, 87, 50N, 59, 27...).
# IDs hifenados (52-1, 89-3) NÃO entram aqui: N0 (extrair_contexto_estrutural)
# já os extrai do texto bruto, classificados por código ANSI, antes que
# normalizar() colapse o hífen em espaço — nesse ponto do pipeline (depois de
# normalizar()) o hífen já não existe mais de qualquer forma.
# ponytail: regex calibrada; ID de equipamento é contexto, não sinal.
_ID_LETRA_NUM = re.compile(r"\b\d+[A-Z]\d+\b")  # 01Q0, 12J4

# N5 — unidades equivalentes -> forma canônica (whole-token).
_UNIDADES: dict[str, str] = {
    "KV": "KV",
    "KVA": "KVA",
    "MVA": "MVA",
    "MW": "MW",
    "MVAR": "MVAR",
    "A": "A",
    "AMP": "A",
    "AMPERE": "A",
    "AMPERES": "A",
    "V": "V",
    "HZ": "HZ",
    "C": "C",
}

# N4 — siglas curtas (alfanuméricas com dígito, ou <=3 letras) nunca são
# corrigidas: 67N, SF6, DJF1, 50N, kV não devem virar palavra de domínio.
_TEM_DIGITO = re.compile(r"\d")

# N3 — termos de equipamento que, como prefixo, diluem o match (são contexto).
_TERMOS_EQUIPAMENTO: frozenset[str] = frozenset(
    {
        "DISJUNTOR",
        "SECCIONADORA",
        "TRANSFORMADOR",
        "RELIGADOR",
        "RELE",
        "CHAVE",
        "BANCO",
        "ALIMENTADOR",
        "LINHA",
    }
)


def _sem_acentos(texto: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _abreviacoes(config: Config) -> dict[str, str]:
    """Mescla ABREVIACOES_EXTRA com config.abreviacoes (config tem prioridade)."""
    merged = dict(ABREVIACOES_EXTRA)
    merged.update(config.abreviacoes)
    return merged


# --- N1 -------------------------------------------------------------------


def expandir_abreviacoes(texto: str, config: Config) -> str:
    """N1: expande abreviações whole-token; nunca quebra siglas internas."""
    if not texto:
        return ""
    abrev = _abreviacoes(config)
    saida: list[str] = []
    for tok in texto.split():
        expandido = abrev.get(tok, tok)
        saida.extend(expandido.split())
    return " ".join(saida)


# --- N2 -------------------------------------------------------------------


def separar_ids_equipamento(texto: str, config: Config) -> tuple[str, str]:
    """N2: separa IDs de equipamento letra-número (01Q0, 12J4) do texto de
    matching. IDs hifenados (52-1) já foram extraídos em N0 (texto bruto,
    antes do hífen ser colapsado por ``normalizar()``) — não chegam aqui.

    Devolve ``(texto_sem_ids, contexto)``. Números de função de proteção
    (67, 87, 50N...) são preservados — só casam padrões de ID. Gateado por
    ``config.remover_ids_equipamento``.

    ponytail: regex calibrada; ID de equipamento é contexto, não sinal.
    """
    if not texto or not config.remover_ids_equipamento:
        return texto, ""
    contexto: list[str] = []

    def _coleta(m: re.Match[str]) -> str:
        contexto.append(m.group(0))
        return " "

    texto = _ID_LETRA_NUM.sub(_coleta, texto)
    return " ".join(texto.split()), " ".join(contexto)


# --- N3 -------------------------------------------------------------------


def remover_boilerplate(texto: str, config: Config) -> str:
    """N3: descarta prefixo de equipamento que dilui o match.

    "DISJUNTOR - BAIXA PRESSAO SF6 BLOQUEIO" tem o sinal no rabo; quando há
    descrição substantiva após um separador, mantém só o núcleo semântico. O
    texto já vem com ``/-.`` colapsados por ``normalizar``, então usamos o
    primeiro separador remanescente apenas se sobrar conteúdo substantivo.
    """
    if not texto:
        return ""
    # Aqui o texto já está sem separadores (viraram espaço em normalizar). O
    # prefixo de equipamento é o termo de equipamento inicial; o núcleo é o
    # resto. Como N2 já removeu o ID, basta soltar um termo de equipamento
    # líder se houver descrição substantiva depois.
    tokens = texto.split()
    if len(tokens) <= 2:
        return texto
    if tokens[0] in _TERMOS_EQUIPAMENTO and len(tokens) > 3:
        return " ".join(tokens[1:])
    return texto


# --- N4 -------------------------------------------------------------------


def _e_sigla(token: str) -> bool:
    """Siglas curtas / alfanuméricas não são candidatas a correção de typo."""
    return bool(_TEM_DIGITO.search(token)) or len(token) <= 3


def corrigir_typos(
    texto: str,
    config: Config,
    vocab: set[str] | frozenset[str] | None,
) -> str:
    """N4: corrige tokens com ~1 edição para um termo de domínio conhecido.

    ``vocab`` é injetado pelo orquestrador (termos das descrições da lista
    padrão); sem vocab (None/vazio) a função é no-op. Gateado por
    ``config.corrigir_typos``. Threshold alto e bypass de siglas garantem que
    67N/SF6/DJF1 nunca são "corrigidos".
    """
    if not texto or not config.corrigir_typos or not vocab:
        return texto
    alvos = [v for v in vocab if not _e_sigla(v)]
    if not alvos:
        return texto
    saida: list[str] = []
    for tok in texto.split():
        if tok in vocab or _e_sigla(tok):
            saida.append(tok)
            continue
        melhor = max(alvos, key=lambda v: fuzz.ratio(tok, v))
        score = fuzz.ratio(tok, melhor)
        # ~1 edição num token de tamanho razoável -> score alto. Threshold
        # conservador para não trocar palavras genuinamente distintas.
        if score >= 85 and abs(len(tok) - len(melhor)) <= 1:
            saida.append(melhor)
        else:
            saida.append(tok)
    return " ".join(saida)


# --- N5 -------------------------------------------------------------------


def normalizar_unidades(texto: str) -> str:
    """N5: canoniza unidades equivalentes (kV/KV/Kv->KV, A/Amp->A, Mw->MW)."""
    if not texto:
        return ""
    saida: list[str] = []
    for tok in texto.split():
        saida.append(_UNIDADES.get(tok.upper(), tok))
    return " ".join(saida)


# N5.5 — "ESTAGIO 1" / "ESTAGIO1" -> "E1" (a lista padrão usa a forma compacta
# E1..E5 nos sufixos; o input costuma escrever "Estágio N"). Sem isso o token
# de estágio não casa com a descrição padrão nem com a regra de especificidade.
_ESTAGIO_RX = re.compile(r"\bESTAGIO\s*([1-5])\b")


def normalizar_estagio(texto: str) -> str:
    return _ESTAGIO_RX.sub(r"E\1", texto) if texto else ""


# --- N6 --- stemmer superficial de português -------------------------------


def _stemmar(texto: str) -> str:
    """N6: stemming superficial para sufixos comuns no domínio de subestação.

    Roda sobre texto já maiúsculo e sem acentos. Regras manuais (~30loc)
    que cobrem ~90% dos sufixos da lista padrão.
    """
    if not texto:
        return ""
    saida: list[str] = []
    for tok in texto.split():
        t = tok
        if t.endswith("COES") or t.endswith("CAO"):
            t = t[:-3] + "C"  # COMUNICACAO → COMUNICAC
        elif t.endswith("MENTOS") or t.endswith("MENTO"):
            t = t[:-5]  # RELIGAMENTO → RELIGA
        elif t.endswith("DORES"):
            t = t[:-4]  # TRANSFORMADORES → TRANSFORMA
        elif t.endswith("DOR"):
            t = t[:-3]  # TRANSFORMADOR → TRANSFORMA
        elif t.endswith("NCIAS") or t.endswith("NCIA"):
            t = t[:-4] + "NT"  # FREQUENCIA → FREQUENT
        elif t.endswith("DADES") or t.endswith("DADE"):
            t = t[:-4]  # PROPRIEDADE → PROPRIE
        elif len(t) > 5 and t[-1] == "S" and t[-2] in "AEIOU":
            t = t[:-1]  # ALARMES → ALARME, POTENCIAS → POTENCIA
        saida.append(t)
    return " ".join(saida)


# --- orquestradores -------------------------------------------------------


def _eh_letra_fase_apos_fase(tokens: list[str], i: int) -> bool:
    """D2.1: protege a letra de fase (A/B/C/N) de ser removida como stopword
    genérico quando vem logo após o token "FASE" (ex: "FASE A" -- "A" é
    artigo em STOPWORDS_PADRAO, mas aqui é discriminador de sigla)."""
    return tokens[i] in ("A", "B", "C", "N") and i > 0 and tokens[i - 1] == "FASE"


def normalizar(texto: str | None, config: Config) -> str:
    """Forma normalizada legada: maiúsculas, sem acentos, separadores, abrev,
    stopwords. Preservada para quem já chama (pipeline, benchmark)."""
    if not texto:
        return ""
    texto = _sem_acentos(texto).upper()
    texto = preservar_siglas_especiais(texto)  # N0.5: extrai (sigla) antes do colapso de separadores
    texto = _SEPARADORES.sub(" ", texto)
    tokens = texto.split()
    sem_stop = [
        t for i, t in enumerate(tokens)
        if t not in config.stopwords or _eh_letra_fase_apos_fase(tokens, i)
    ]
    return expandir_abreviacoes(" ".join(sem_stop), config)


def canonizar(
    texto: str | None,
    config: Config,
    vocab: set[str] | frozenset[str] | None = None,
) -> str:
    """Forma canônica para scoring. Orquestra N1..N5 + tokenizer de siglas.

    ``vocab`` é opcional (default None) para retrocompatibilidade; sem ele a
    correção de typos (N4) é pulada.
    """
    base = normalizar(texto, config)  # já aplica N1 internamente
    texto2, _ctx = separar_ids_equipamento(base, config)  # N2
    texto3 = remover_boilerplate(texto2, config)  # N3
    texto4 = corrigir_typos(texto3, config, vocab)  # N4
    texto5 = normalizar_unidades(texto4)  # N5
    texto5b = normalizar_estagio(texto5)  # N5.5 — "ESTAGIO 1" -> "E1"
    texto6 = _stemmar(texto5b) if config.stemming else texto5b  # N6 — gated (spF §3)
    return " ".join(tokenizar(texto6))
