"""Monta SignalRecords a partir das linhas de uma sheet não-homogênea.

Rastreia marcadores de seção na coluna 1 (com sinônimos: Comandos/Controle,
Digitais/Sinalizações, Analógicas/Medidas) para definir categoria e direção.
A coluna 'Tipo' refina linha a linha quando presente. Módulo é constante por
sheet (do sheet_name ou de NOME derivado de sigla) no gênero tradicional, ou
lido linha a linha quando há coluna dedicada (`coluna:MODULO_POR_LINHA`).
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
from .normalizador import canonizar, equipamentos_no_texto, extrair_contexto_estrutural
from .parse_nome import (
    extrair_equipamento_do_nome,
    extrair_modulo_do_nome,
    sigla_esta_no_nome,
)
from .vocabulario_tipo import VOCAB as _VOCAB, classificar as _classificar, norm as _norm


def _eh_marcador(row: tuple, col0: int) -> bool:
    """Linha de marcador de seção: UMA célula classifica como categoria e as
    demais preenchidas são vazias ou numeração de sequência (inteiro curto) —
    o layout CVA11 tem contador na col 0 ('1'/'MEDIÇÃO', '10'/'CONTROLE'),
    que invalidava a regra antiga de "exatamente 1 célula" (SP-CVA2 E3.1).

    A célula classificadora precisa casar o VOCAB de seção (substring —
    MEDIÇÃO/CONTROLE/SINALIZAÇÃO e sinônimos), NUNCA um código curto de
    `CODIGOS_TIPO` (A/C/D/AI/AO/DI/DO) — esses são evidência POR LINHA (coluna
    Tipo, SP-CVA2 E3.2), não marcador de seção; uma linha de dados com
    descrição vazia e só a célula de código + numeração preenchidos não pode
    abrir uma seção nova e inverter a direção das linhas seguintes (achado da
    revisão final de branch, composição E3.1+E3.2 — não reproduzido no dado
    real da SE CVA, mas via de regressão latente)."""
    preenchidas = [i for i, c in enumerate(row) if _norm(c)]
    classificam = [
        i for i in preenchidas if any(k in _norm(row[i]) for k in _VOCAB)
    ]
    if len(classificam) != 1:
        return False
    outras = [i for i in preenchidas if i not in classificam]
    return all(re.fullmatch(r"\d{1,4}", _norm(row[i])) for i in outras)


def _parse_indices(cell) -> tuple[int, ...]:
    if cell is None:
        return ()
    return tuple(int(p) for p in re.findall(r"-?\d+", str(cell)))


# Grandeza elétrica contínua na própria descrição -- fallback quando não há
# coluna TIPO nem marcador de seção (ex.: CVA11: sheet só com descricao/
# indice, sinais de tensão entre fases sem nenhuma das duas evidências
# usuais). Local (não em vocabulario_tipo.VOCAB) para não afetar
# _col_tipo/_eh_marcador, que buscam evidência explícita de TIPO/seção.
_GRANDEZA_CONTINUA = ("TENSAO", "CORRENTE", "POTENCIA", "FREQUENCIA")
# Texto que COMEÇA com falta/perda descreve ausência (status discreto), não
# medição — 'Falta de Potencial', 'Falta Tensão Comando' (SP-CVA2 E3.3).
_PREFIXOS_AUSENCIA = ("FALTA", "PERDA")


def _grandeza_continua(bruta) -> tuple[str, str] | None:
    tokens = _norm(bruta).split()
    if not tokens or tokens[0] in _PREFIXOS_AUSENCIA:
        return None
    if any(t in _GRANDEZA_CONTINUA for t in tokens):
        return ("Analog", "Input")
    return None


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
    c_modulo = cols.get("modulo")
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
            # celula que classifica (nao a 1a preenchida -- pode haver
            # numeracao de sequencia antes dela, SP-CVA2 E3.1)
            idx_marc = next(
                i for i, c in enumerate(row) if _norm(c) and _classificar(c) is not None
            )
            secao = _classificar(row[idx_marc])
            secao_explicita = True
            continue

        bruta = row[c_desc] if tem_desc else row[c_sigla]
        if not _norm(bruta):
            continue

        cat_dir = _classificar(row[c_tipo]) if c_tipo is not None and c_tipo < len(row) else None
        if cat_dir is None and not secao_explicita:
            cat_dir = _grandeza_continua(bruta)
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

        # --- resolução de módulo/sigla por coluna ---
        sigla_sinal = None
        status = "pendente"
        motivo_revisao = None
        origem_modulo = "sheet_name"
        nome_mod_final = nome_mod

        if c_modulo is not None:
            # Gênero sheet-por-tipo: módulo numa coluna dedicada, por linha.
            # Precedência sobre extração do NOME (coluna explícita ganha).
            val_mod = (
                str(row[c_modulo]).strip()
                if c_modulo < len(row) and row[c_modulo] is not None
                else ""
            )
            origem_modulo = "coluna:MODULO_POR_LINHA"
            if val_mod:
                nome_mod_final = val_mod
            else:
                nome_mod_final = None
                status = "revisao"
                motivo_revisao = "modulo_indefinido"
        elif tem_sigla and siglas_set is not None:
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
        # -------------------------------------------------------------------

        # --- varredura da linha inteira por ID de equipamento (spec 15/07):
        # a descrição já foi parseada pelo N0; as demais células só
        # contribuem identidade de equipamento. Módulo (c_modulo) fica de
        # fora: é identidade de módulo, não de equipamento.
        ids_linha: dict[str, str | None] = {}
        if eletrico.nome_equipamento:
            ids_linha[eletrico.nome_equipamento] = eletrico.equipamento_alvo
        for c, cel in enumerate(row):
            if c == c_desc or c == c_modulo or cel is None:
                continue
            for alvo, nome_eq in equipamentos_no_texto(str(cel)):
                ids_linha.setdefault(nome_eq, alvo)
        if len(ids_linha) > 1 and status != "revisao":
            # 2 equipamentos distintos na mesma linha -> operador decide
            status = "revisao"
            motivo_revisao = "equipamento_conflitante"
        elif len(ids_linha) == 1 and eletrico.nome_equipamento is None:
            nome_eq, alvo = next(iter(ids_linha.items()))
            eletrico = replace(
                eletrico, nome_equipamento=nome_eq,
                # ponytail: alvo do ID só preenche quando N0 não achou nada
                # pela palavra; divergência palavra×ID não é colisão (spec
                # define colisão = 2 IDs), o ID ganha o nome e o alvo textual
                # fica. Upgrade: tratar divergência como conflito se aparecer
                # em dado real.
                equipamento_alvo=eletrico.equipamento_alvo or alvo,
            )

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
