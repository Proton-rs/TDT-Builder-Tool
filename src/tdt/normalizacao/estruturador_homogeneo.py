"""Caminho determinístico pra sheets homogêneas: cabeçalho fixo conhecido,
sigla/módulo/equipamento/tipo já vêm em colunas dedicadas — sem heurística
de coluna nem scoring."""

from __future__ import annotations

from dataclasses import replace

from ..config import Config
from ..contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from ..dados.lista_padrao import ListaPadraoADMS
from .estruturador import _parse_indices
from .normalizador import canonizar, extrair_contexto_estrutural
from .vocabulario_tipo import CODIGOS_TIPO

_MAX_SCAN = 30

_CABECALHO_ESPERADO: frozenset[str] = frozenset({
    "UTILIZADO?", "SUBESTACAO", "MODULO", "EQUIPAMENTO", "TIPO",
    "DESCRICAO DO PONTO", "SIGLA SINAL", "NOME", "INDEX DNP3",
})

_EQUIPAMENTO_POR_MODULO: dict[str, str] = {
    "DJ": "Disjuntor",
    "SECC": "Seccionadora", "SECF": "Seccionadora",
    "SECT": "Seccionadora", "SECG": "Seccionadora",
}


def _sem_acentos(s: str) -> str:
    troca = str.maketrans("ÁÉÍÓÚÂÊÎÔÛÃÕÀÇ", "AEIOUAEIOUAOAC")
    return s.translate(troca)


def _normaliza_celula(v) -> str:
    if v is None:
        return ""
    return _sem_acentos(str(v)).strip().upper()


def detectar_header(rows: list[tuple]) -> int | None:
    """Devolve o índice 0-based da linha de cabeçalho, ou None se a sheet
    não seguir o formato homogêneo fixo."""
    for i, row in enumerate(rows[:_MAX_SCAN]):
        celulas = {_normaliza_celula(v) for v in row if v is not None}
        if _CABECALHO_ESPERADO <= celulas:
            return i
    return None


def _col(header: tuple, nome: str) -> int | None:
    for i, v in enumerate(header):
        if _normaliza_celula(v) == nome:
            return i
    return None


_ROTULO_BLOCO = "EQUIPAMENTO"
_COLUNA_NUMERO_BLOCO = 1  # "NÚMERO OPERATIVO / MNEMNICO"


def extrair_numeros_operativos(rows: list[tuple], header_idx: int) -> dict[str, str]:
    """Bloco acima do cabeçalho: EQUIPAMENTO | NÚMERO OPERATIVO / MNEMNICO.

    Devolve rótulo normalizado -> número ("MODULO" -> "23", "DJ" -> "52-23").
    Bloco ausente/ilegível -> {} (chamador não inventa número).
    """
    nums: dict[str, str] = {}
    dentro = False
    for row in rows[:header_idx]:
        rotulo = _normaliza_celula(row[0] if row else None)
        segundo = _normaliza_celula(
            row[_COLUNA_NUMERO_BLOCO] if len(row) > _COLUNA_NUMERO_BLOCO else None)
        if rotulo == _ROTULO_BLOCO and "OPERATIVO" in segundo:
            dentro = True
            continue
        if not dentro:
            continue
        if not rotulo:
            dentro = False
            continue
        valor = row[_COLUNA_NUMERO_BLOCO] if len(row) > _COLUNA_NUMERO_BLOCO else None
        if valor is not None and str(valor).strip():
            nums[rotulo] = str(valor).strip()
    return nums


def estruturar_homogeneo(
    rows: list[tuple], header_idx: int, sheet_name: str,
    lp: ListaPadraoADMS, config: Config,
) -> tuple[list[SignalRecord], list[SignalRecord]]:
    """Devolve (decididos, pendentes_de_scoring)."""
    header = rows[header_idx]
    idx = {
        "utilizado": _col(header, "UTILIZADO?"),
        "modulo": _col(header, "MODULO"),
        "equipamento": _col(header, "EQUIPAMENTO"),
        "tipo": _col(header, "TIPO"),
        "descricao": _col(header, "DESCRICAO DO PONTO"),
        "sigla": _col(header, "SIGLA SINAL"),
        "index": _col(header, "INDEX DNP3"),
    }

    numeros = extrair_numeros_operativos(rows, header_idx)
    numero_modulo = numeros.get("MODULO")

    decididos: list[SignalRecord] = []
    pendentes: list[SignalRecord] = []

    for i, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        if idx["utilizado"] is None or idx["utilizado"] >= len(row):
            continue
        if _normaliza_celula(row[idx["utilizado"]]) != "SIM":
            continue

        bruta = str(row[idx["descricao"]] or "") if idx["descricao"] is not None else ""
        remanescente, ctx = extrair_contexto_estrutural(bruta)
        cod_tipo = _normaliza_celula(row[idx["tipo"]]) if idx["tipo"] is not None else ""
        categoria, direcao = CODIGOS_TIPO.get(cod_tipo, ("Discrete", "Input"))
        modulo_nome = str(row[idx["modulo"]]) if idx["modulo"] is not None and row[idx["modulo"]] else None
        origem_modulo = "coluna:MODULO"
        if (modulo_nome and numero_modulo
                and not any(ch.isdigit() for ch in modulo_nome)):
            modulo_nome = f"{modulo_nome.strip()}{numero_modulo}"
            origem_modulo = "coluna:MODULO+header:NUMERO_OPERATIVO"
        equip_cod = _normaliza_celula(row[idx["equipamento"]]) if idx["equipamento"] is not None else ""
        sigla = str(row[idx["sigla"]] or "").strip() if idx["sigla"] is not None else ""
        indices = _parse_indices(row[idx["index"]]) if idx["index"] is not None and idx["index"] < len(row) else ()
        datatype = (
            "DoubleBit"
            if len(indices) == 2 and indices[0] != indices[1]
            else "SingleBit"
        )

        rec = SignalRecord(
            id=f"{sheet_name}:{i}",
            modulo=Modulo(modulo_nome, origem_modulo),
            tipo_sinal=TipoSinal(categoria, datatype=datatype, direcao=direcao,
                                 categoria_confiavel=True),
            enderecamento=Enderecamento("DNP3", indices),
            descricoes=Descricoes(bruta, canonizar(remanescente, config, None)),
            eletrico=Eletrico(
                fase=ctx.fase,
                equipamento_alvo=_EQUIPAMENTO_POR_MODULO.get(equip_cod, ctx.equipamento_alvo),
                nome_equipamento=ctx.nome_equipamento,
                barra=ctx.barra,
            ),
        )

        sp = lp.por_sigla(sigla) if sigla else None
        if sp is None:
            pendentes.append(rec)
        else:
            decididos.append(replace(rec, sigla_sinal=sigla, status="decidido"))

    return decididos, pendentes
