"""Caminho determinístico pra sheets homogêneas: cabeçalho fixo conhecido,
sigla/módulo/equipamento/tipo já vêm em colunas dedicadas — sem heurística
de coluna nem scoring."""

from __future__ import annotations

from dataclasses import replace

from ..config import Config
from ..contracts import Descricoes, Eletrico, Enderecamento, ItemRevisao, Modulo, SignalRecord, TipoSinal
from ..dados.lista_padrao import ListaPadraoADMS
from .estruturador import _parse_indices
from .identidade_homogenea import extrair_bloco, resolver
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
) -> tuple[list[SignalRecord], list[SignalRecord], list[ItemRevisao], list[str]]:
    """Devolve (decididos, pendentes_de_scoring, revisao, avisos).

    revisao: siglas conhecidas sem ponto (config.siglas_sem_ponto, ex. COMTAP).
    avisos: divergência NOME do cliente x nome calculado (lint, não bloqueia).
    """
    header = rows[header_idx]
    idx = {
        "utilizado": _col(header, "UTILIZADO?"),
        "subestacao": _col(header, "SUBESTACAO"),
        "modulo": _col(header, "MODULO"),
        "equipamento": _col(header, "EQUIPAMENTO"),
        "tipo": _col(header, "TIPO"),
        "descricao": _col(header, "DESCRICAO DO PONTO"),
        "sigla": _col(header, "SIGLA SINAL"),
        "nome": _col(header, "NOME"),
        "index": _col(header, "INDEX DNP3"),
    }

    bloco = extrair_bloco(rows, header_idx)

    decididos: list[SignalRecord] = []
    pendentes: list[SignalRecord] = []
    revisao: list[ItemRevisao] = []
    avisos: list[str] = []

    for i, row in enumerate(rows[header_idx + 1:], start=header_idx + 2):
        if idx["utilizado"] is None or idx["utilizado"] >= len(row):
            continue
        if _normaliza_celula(row[idx["utilizado"]]) != "SIM":
            continue

        bruta = str(row[idx["descricao"]] or "") if idx["descricao"] is not None else ""
        remanescente, ctx = extrair_contexto_estrutural(bruta)
        cod_tipo = _normaliza_celula(row[idx["tipo"]]) if idx["tipo"] is not None else ""
        categoria, direcao = CODIGOS_TIPO.get(cod_tipo, ("Discrete", "Input"))
        modulo_col = _normaliza_celula(row[idx["modulo"]]) if idx["modulo"] is not None else ""
        equip_cod = _normaliza_celula(row[idx["equipamento"]]) if idx["equipamento"] is not None else ""
        ident = resolver(bloco, sheet_name, modulo_col, equip_cod)
        sigla_bruta = str(row[idx["sigla"]] or "").strip() if idx["sigla"] is not None else ""
        # DE->PARA só entra quando a sigla bruta NÃO já resolve na lista
        # padrão -- precedência do match direto evita que um mapeamento
        # legado desfaça uma sigla já correta (regressão bench SAN2).
        if sigla_bruta and lp.por_sigla(sigla_bruta) is None:
            sigla = lp.de_para.get(sigla_bruta.upper(), sigla_bruta)
        else:
            sigla = sigla_bruta
        if sigla != sigla_bruta:
            avisos.append(
                f"{sheet_name}:{i}: sigla '{sigla_bruta}' normalizada p/ '{sigla}' (DE->PARA)"
            )
        indices = _parse_indices(row[idx["index"]]) if idx["index"] is not None and idx["index"] < len(row) else ()
        datatype = (
            "DoubleBit"
            if len(indices) == 2 and indices[0] != indices[1]
            else "SingleBit"
        )

        rec = SignalRecord(
            id=f"{sheet_name}:{i}",
            modulo=Modulo(ident.modulo, ident.origem),
            tipo_sinal=TipoSinal(categoria, datatype=datatype, direcao=direcao,
                                 categoria_confiavel=True),
            enderecamento=Enderecamento("DNP3", indices),
            descricoes=Descricoes(bruta, canonizar(remanescente, config, None)),
            eletrico=Eletrico(
                fase=ctx.fase,
                equipamento_alvo=_EQUIPAMENTO_POR_MODULO.get(equip_cod, ctx.equipamento_alvo),
                nome_equipamento=ident.equipamento,
                barra=ctx.barra,
            ),
        )

        if sigla and sigla.upper() in config.siglas_sem_ponto:
            revisao.append(ItemRevisao(
                replace(rec, sigla_sinal=sigla.upper(), status="revisao",
                        justificativa="comando TAP não modelado no ADMS (base real: 0 sinais COMTAP)"),
                motivo="comando_tap_nao_modelado",
            ))
            continue

        # Lint NOME do cliente x regra (spec §2.4): aviso, não bloqueia.
        # Roda depois do gate acima -- linha já roteada p/ revisão não vira
        # sinal, então divergência de NOME aqui seria ruído de auditoria.
        nome_cli = str(row[idx["nome"]] or "").strip() if idx["nome"] is not None else ""
        se = str(row[idx["subestacao"]] or "").strip() if idx["subestacao"] is not None else ""
        if nome_cli and sigla and se:
            mod_fmt = ident.modulo.replace(" ", "")
            calc = f"{se}_{mod_fmt}_{ident.equipamento or mod_fmt}_{sigla}"
            if calc != nome_cli:
                avisos.append(
                    f"{sheet_name}:{i}: NOME do cliente '{nome_cli}' difere do calculado '{calc}'"
                )

        sp = lp.por_sigla(sigla) if sigla else None
        if sp is None:
            pendentes.append(rec)
        else:
            decididos.append(replace(rec, sigla_sinal=sigla, status="decidido"))

    return decididos, pendentes, revisao, avisos
