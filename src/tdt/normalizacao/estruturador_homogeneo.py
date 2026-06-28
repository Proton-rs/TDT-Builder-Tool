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
        equip_cod = _normaliza_celula(row[idx["equipamento"]]) if idx["equipamento"] is not None else ""
        sigla = str(row[idx["sigla"]] or "").strip() if idx["sigla"] is not None else ""
        indices = _parse_indices(row[idx["index"]]) if idx["index"] is not None and idx["index"] < len(row) else ()

        rec = SignalRecord(
            id=f"{sheet_name}:{i}",
            modulo=Modulo(modulo_nome, "coluna:MODULO"),
            tipo_sinal=TipoSinal(categoria, is_double_bit=False, direcao=direcao, categoria_confiavel=True),
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
