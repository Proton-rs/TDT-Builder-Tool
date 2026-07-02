"""Monta SignalRecords a partir das linhas de uma sheet não-homogênea.

Rastreia marcadores de seção na coluna 1 (com sinônimos: Comandos/Controle,
Digitais/Sinalizações, Analógicas/Medidas) para definir categoria e direção.
A coluna 'Tipo' refina linha a linha quando presente. Módulo é constante por
sheet (vem da coluna Módulo).
"""

from __future__ import annotations

import re
from dataclasses import replace

from ..config import Config
from ..contracts import (
    Descricoes,
    Eletrico,
    Enderecamento,
    MapaColunas,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from .normalizador import canonizar, extrair_contexto_estrutural
from .parse_nome import (
    extrair_equipamento_do_nome,
    extrair_modulo_do_nome,
    sigla_esta_no_nome,
)
from .vocabulario_tipo import classificar as _classificar, norm as _norm


def _eh_marcador(row: tuple, col0: int) -> bool:
    """Uma única célula tem categoria (em qq coluna) e o resto está vazio."""
    preenchidas = [i for i, c in enumerate(row) if _norm(c)]
    if len(preenchidas) != 1:
        return False
    return _classificar(row[preenchidas[0]]) is not None


def _parse_indices(cell) -> tuple[int, ...]:
    if cell is None:
        return ()
    return tuple(int(p) for p in re.findall(r"-?\d+", str(cell)))


def estruturar(
    rows: list[tuple],
    mapa: MapaColunas,
    sheet_name: str,
    config: Config,
    modulo: str | None = None,
    vocab: set[str] | frozenset[str] | None = None,
    siglas_set: frozenset[str] | None = None,
) -> list[SignalRecord]:
    cols = mapa.colunas
    c_desc = cols.get("descricao")
    c_idx = cols.get("indice")
    c_tipo = cols.get("tipo")
    c_sigla = cols.get("sigla")
    nome_mod = modulo if modulo is not None else sheet_name
    col0 = 0  # marcadores de seção ficam na 1ª coluna

    registros: list[SignalRecord] = []
    secao: tuple[str, str] = ("Discrete", "Input")  # default
    secao_explicita = False  # virou True quando um marcador de seção foi lido

    for i, row in enumerate(rows):
        if i + 1 <= mapa.header_row:  # pula header e metadados acima
            continue
        tem_desc = c_desc is not None and c_desc < len(row)
        tem_sigla = c_sigla is not None and c_sigla < len(row)
        if not tem_desc and not tem_sigla:
            continue

        if _eh_marcador(row, col0):
            idx_marc = [i for i, c in enumerate(row) if _norm(c)][0]
            secao = _classificar(row[idx_marc])
            secao_explicita = True
            continue

        bruta = row[c_desc] if tem_desc else row[c_sigla]
        if not _norm(bruta):
            continue

        cat_dir = _classificar(row[c_tipo]) if c_tipo is not None and c_tipo < len(row) else None
        categoria, direcao = cat_dir or secao
        confiavel = cat_dir is not None or secao_explicita

        tipo_norm = (
            _norm(row[c_tipo]) if c_tipo is not None and c_tipo < len(row) else ""
        )
        comando_duplo = not (direcao == "Output" and tipo_norm == "COMANDO S")

        indices = _parse_indices(row[c_idx]) if c_idx is not None and c_idx < len(row) else ()
        datatype = (
            "DoubleBit"
            if len(indices) == 2 and indices[0] != indices[1]
            else "SingleBit"
        )

        remanescente, ctx_estrutural = extrair_contexto_estrutural(str(bruta))
        eletrico = Eletrico(
            fase=ctx_estrutural.fase,
            equipamento_alvo=ctx_estrutural.equipamento_alvo,
            nome_equipamento=ctx_estrutural.nome_equipamento,
            barra=ctx_estrutural.barra,
        )

        # --- pré-classificação por coluna de sigla (sigla não-homogênea) ---
        sigla_sinal = None
        status = "pendente"
        motivo_revisao = None
        origem_modulo = "sheet_name"
        nome_mod_final = nome_mod
        if tem_sigla and siglas_set is not None:
            sv = str(row[c_sigla] or "").strip().upper()
            if sv and sv in siglas_set:
                sigla_sinal = sv
                nome_str = str(row[c_desc]) if tem_desc else ""
                if nome_str and not sigla_esta_no_nome(nome_str, sv):
                    status = "revisao"
                    motivo_revisao = "nome_sigla_inconsistente"
                else:
                    status = "decidido"
                    mod_extraido = extrair_modulo_do_nome(nome_str) if nome_str else None
                    if mod_extraido:
                        nome_mod_final, origem_modulo = mod_extraido, "coluna:SIGLA"
                        # 3º token do NOME (equipamento/instância) -- sem isso,
                        # múltiplas instâncias do mesmo módulo+sigla (ex:
                        # "SLOTD" vs "SLOTD-2") colidem na chave de dedup de
                        # normalizador_estrutural (modulo, nome_equipamento,
                        # sigla) e são descartadas como endereco_duplicado.
                        equip_extraido = extrair_equipamento_do_nome(nome_str)
                        if equip_extraido:
                            eletrico = replace(eletrico, nome_equipamento=equip_extraido)
            # sv não-vazia mas fora da LP -> status fica "pendente": recai no scoring
        # ---------------------------------------------------------------------

        registros.append(
            SignalRecord(
                id=f"{sheet_name}:{i + 1}",
                modulo=Modulo(nome_mod_final, origem_modulo),
                tipo_sinal=TipoSinal(categoria, datatype=datatype, direcao=direcao,
                                     categoria_confiavel=confiavel,
                                     comando_duplo=comando_duplo),
                enderecamento=Enderecamento("DNP3", indices),
                descricoes=Descricoes(str(bruta), canonizar(remanescente, config, vocab)),
                eletrico=eletrico,
                sigla_sinal=sigla_sinal,
                status=status,
                justificativa=motivo_revisao,
            )
        )
    return registros
