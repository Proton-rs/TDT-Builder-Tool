"""Gera o TDT DNP3 preenchendo o template (preserva fórmulas, estilos e tabelas).

Carrega ``dnp3_template.xlsx`` e escreve os dados a partir da row 5, localizando
colunas pelo **display name (row 4)** — os field names da row 3 se repetem
(seção do sinal vs. seção do remote point), então não servem de chave única.

Escopo atual: sinais discretos (DNP3_DiscreteSignals) e analógicos
(DNP3_AnalogSignals, só leitura). Pareamento D+C de comando fica para o
próximo corte.
ponytail: analógico sem unidade/escala/Measurement Type ainda; entra quando o
input fornecer a grandeza física.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.utils import get_column_letter

from tdt.contracts import ItemRevisao, ListaHomogenea, SignalRecord
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.normalizacao.normalizador import familia_do_id

SHEET_DISCRETOS = "DNP3_DiscreteSignals"
COLUNAS_ESPERADAS = 43
SHEET_ANALOGICOS = "DNP3_AnalogSignals"
COLUNAS_ESPERADAS_ANALOG = 61
SHEET_DISCRETE_ANALOG = "DNP3_DiscreteAnalog"
COLUNAS_ESPERADAS_DISCRETE_ANALOG = 48
PRIMEIRA_LINHA_DADOS = 5

_DIRECAO = {"Input": "Read", "Output": "Write", "InputOutput": "ReadWrite"}


def _mapa_colunas(ws) -> dict[str, int]:
    """display name (row 4) -> índice de coluna (1-based)."""
    return {
        ws.cell(4, c).value: c
        for c in range(1, ws.max_column + 1)
        if ws.cell(4, c).value
    }


_BARRA_SUFIXO = {"Principal": "P", "Auxiliar": "A"}


def nome_hierarquico(
    subestacao: str | None,
    modulo_nome: str | None,
    equipamento: str | None,
    barra: str | None,
    sigla: str,
) -> str:
    partes = []
    if subestacao:
        partes.append(subestacao)
    # "LT 1" → "LT1", "AL 11" → "AL11", "TR 1" → "TR1"
    modulo_fmt = modulo_nome.replace(" ", "") if modulo_nome else None
    if modulo_fmt:
        partes.append(modulo_fmt)
    if equipamento:
        partes.append(equipamento)
    elif modulo_fmt:
        partes.append(modulo_fmt)  # sem equipamento: repete o módulo
    sufixo_barra = _BARRA_SUFIXO.get(barra or "")
    if sufixo_barra:
        partes.append(sufixo_barra)
    partes.append(sigla)
    return "_".join(partes)


_nome_hierarquico = nome_hierarquico  # alias: bench/diag_cva.py e testes ainda importam o nome privado


def _eh_alimentador(modulo_nome: str | None) -> bool:
    if not modulo_nome:
        return False
    norm = modulo_nome.replace(" ", "").upper()
    return bool(re.match(r"^AL\d", norm))


def _aor_group(subestacao: str | None, alimentador: bool) -> str | None:
    if not subestacao:
        return None
    return f"{subestacao} {'Distr' if alimentador else 'Trans'}"


def _remote_unit(subestacao: str | None) -> str | None:
    return f"UTR_{subestacao}_1" if subestacao else None


# Sufixo de família do equipamento no Device Mapping (spec 2026-07-20 §A1;
# fullbase: DJ 16.866, TR 4.610, SEC 2.157 como último segmento). TC/TP da
# spec saem no ramo analógico (`<MOD>_TC`/`<MOD>_TP`) — familia_do_id não
# classifica TC/TP por ID; estender aqui se a whitelist ganhar esses IDs.
_SUFIXO_FAMILIA: dict[str, str] = {
    "Disjuntor": "DJ",
    "Seccionadora": "SEC",
    "Transformador": "TR",
}


def _dm_prot(sigla: str | None, sp) -> bool:
    """Flag do ramo PROT do device mapping (spec 2026-07-20 §B1)."""
    return bool(sp and sp.signal_type == "RelayTrip")


def _device_mapping(
    nome: str,
    sigla: str,
    dm_prot: bool,
    subestacao: str | None = None,
    modulo_nome: str | None = None,
    barra: str | None = None,
    equipamento: str | None = None,
    disjuntor: str | None = None,
) -> str:
    """Padrão RGE (spec 2026-07-20): proteção cai no módulo duplicado;
    não-proteção cai no equipamento com sufixo de família (_DJ/_SEC/_TR).
    Sem equipamento, o fallback módulo-duplicado emerge sozinho (sem sufixo).
    Base terminando em sufixo de barra fica sem sufixo de família
    (conservador — fullbase não tem exemplo com barra + sufixo).
    Exceção §A2: proteção de alimentador com disjuntor único conhecido usa o
    disjuntor (não o módulo repetido) como 2º nível — supersede a correção
    16/07 só para esse caso; demais módulos mantêm o módulo duplicado."""
    if dm_prot:
        if _eh_alimentador(modulo_nome) and disjuntor:
            # decisão 20/07 (supersede 16/07): alimentador usa o DISJUNTOR do
            # módulo (não o equipamento da linha) como 2º nível do PROT
            return nome_hierarquico(subestacao, modulo_nome, disjuntor, barra, f"PROT_{sigla}")
        return nome_hierarquico(subestacao, modulo_nome, None, barra, f"PROT_{sigla}")
    base = nome[: len(nome) - len(sigla) - 1] if nome.endswith(f"_{sigla}") else nome
    suf = _SUFIXO_FAMILIA.get(familia_do_id(equipamento) or "")
    if suf and equipamento and base.endswith(equipamento):
        return f"{base}_{suf}"
    return base


def _normal_value(sp: "SinalPadrao | None") -> int | None:
    if sp is None or not sp.estados_brutos or not sp.valores_scada:
        return None
    estados = sp.estados_brutos.split(";")
    try:
        i = estados.index("NORMAL")
    except ValueError:
        return None
    return sp.valores_scada[i] if i < len(sp.valores_scada) else None


def _alias_hoje() -> str:
    return date.today().strftime("%Y%m%d")


def _signal_alias(rec: SignalRecord, alias_v1: "dict[str, str] | None") -> str:
    """Descrição da lista padrão v1 quando a sigla está no mapa; senão a
    descrição bruta do cliente (Custom/sem sigla/mapa ausente)."""
    if alias_v1 and rec.sigla_sinal:
        desc = alias_v1.get(rec.sigla_sinal.upper())
        if desc:
            return desc
    return rec.descricoes.bruta


def _coords_comando(indices: tuple[int, ...], duplo: bool = True) -> str:
    if len(indices) == 1:
        return f"{indices[0]};{indices[0]}" if duplo else str(indices[0])
    return ";".join(str(i) for i in indices)


def _output_data_type(coords_saida: str | None) -> str | None:
    """Domínio DNP3OutputType (DMSMatchingTemplateInfo): ``SingleCoord`` quando
    o comando escreve numa coordenada só (``i;i`` ou índice único),
    ``MultiCoord`` quando escreve em duas distintas (trip;close)."""
    if not coords_saida:
        return None
    partes = coords_saida.split(";")
    return "SingleCoord" if len(set(partes)) == 1 else "MultiCoord"


_FASE_PHASECODE: dict[str, str] = {"CA": "AC"}  # interno -> PhaseCode ADMS
_PHASECODE = frozenset({"ABC", "AB", "BC", "AC", "A", "B", "C", "N"})  # DMSMatchingTemplateInfo


def _fase_saida(fase: str | None) -> str:
    """Fase para a coluna TDT ``Phases``: default ``ABC`` quando vazia, e
    fallback ``ABC`` para qualquer valor fora do domínio ``PhaseCode`` (guard
    de domínio — o ADMS rejeita fase inválida). Traduz a convenção interna de
    campo (``CA``) para o par alfabético do domínio ADMS (``AC``)."""
    fase = _FASE_PHASECODE.get(fase, fase)
    return fase if fase in _PHASECODE else "ABC"


def dm_registro(rec, subestacao, sp, disjuntor: str | None = None) -> tuple[str, str]:
    """(Signal Name, Device Mapping) do registro — derivação ÚNICA, usada por
    _valores, particionar_tipo_duplicado e pelas colunas derivadas da UI."""
    sigla = rec.sigla_sinal or "?"
    nome = nome_hierarquico(
        subestacao, rec.modulo.nome, rec.eletrico.nome_equipamento,
        rec.eletrico.barra, sigla,
    )
    dm = _device_mapping(
        nome, sigla, _dm_prot(rec.sigla_sinal, sp), subestacao,
        rec.modulo.nome, rec.eletrico.barra,
        equipamento=rec.eletrico.nome_equipamento, disjuntor=disjuntor,
    )
    return nome, dm


def _valores(rec: SignalRecord, subestacao: str | None, padrao: ListaPadraoADMS,
             alias_v1: "dict[str, str] | None" = None,
             disjuntor: "str | None" = None) -> dict:
    sp = padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
    nome, dm = dm_registro(rec, subestacao, sp, disjuntor)
    alimentador = _eh_alimentador(rec.modulo.nome)
    remote_unit = _remote_unit(subestacao)
    rp_custom = f"{nome}_{remote_unit}" if remote_unit else None
    indices = rec.enderecamento.indices
    coords = indices[0] if len(indices) == 1 else ";".join(str(i) for i in indices)
    direcao = rec.tipo_sinal.direcao
    tem_comando = direcao in ("Output", "InputOutput")
    if direcao == "Output":
        # Comando órfão (sem par de status): o próprio endereço é o de escrita,
        # não há leitura — não preencher Input Coordinates.
        coords_entrada = None
        coords_saida = _coords_comando(rec.enderecamento.indices, rec.tipo_sinal.comando_duplo)
    else:
        coords_entrada = coords
        coords_saida = (
            _coords_comando(rec.enderecamento.indices_saida, rec.tipo_sinal.comando_duplo)
            if rec.enderecamento.indices_saida else ""
        )
    return {
        "Signal Name": nome,
        "Signal Alias": _signal_alias(rec, alias_v1),
        "Measurement Type": "Status",  # ponytail: default; refinar por signal_type
        "Signal Type": sp.signal_type if sp else "Custom",
        "Side": "None",
        "Output Register": False,
        "Remote Point Type": "Status",
        "Remote Point Name": nome,
        "Phases": _fase_saida(rec.eletrico.fase),
        "Signal AOR Group": _aor_group(subestacao, alimentador),
        "Device Mapping": dm,
        "Direction": _DIRECAO.get(direcao, "Read"),
        "Message Mapping": sp.mm if sp else None,
        "Input Data Type": rec.tipo_sinal.datatype,
        "Input Coordinates": coords_entrada,
        "Output Data Type": _output_data_type(coords_saida) if tem_comando else None,
        "Output Coordinates": coords_saida if tem_comando and coords_saida else None,
        "Remote Unit": remote_unit,
        "Remote Point Custom ID": rp_custom,
        "Remote Point Alias": _alias_hoje(),
        "Normal Value": _normal_value(sp),
    }


_MEASUREMENT_TYPE_PT_EN: dict[str, str] = {
    "CORRENTE": "Current",
    "TENSÃO": "Voltage",
    "POTÊNCIA ATIVA": "ActivePower",
    "POTÊNCIA REATIVA": "ReactivePower",
    "TEMPERATURA": "Temperature",
    # auditoria 09jul (lista padrao v6) — todos confirmados no dominio
    # MeasurementType do DMSMatchingTemplateInfo:
    "COMPRIMENTO": "Unitless",      # KMDF: distancia de defeito e unitless no ADMS (decisao do usuario; o dominio tem "Length" mas usamos Unitless)
    "FREQUÊNCIA": "Frequency",
    "FATOR DE POTÊNCIA": "CosPhi",  # fator de potencia = cos(phi); o dominio usa CosPhi, NAO PowerFactor
    "POTÊNCIA APARENTE": "ApparentPower",
    "ÂNGULO DE TENSÃO": "VoltageAngle",
    "UMIDADE": "Humidity",
    "DISCRETO": "Discrete",
}


def _measurement_type(sp) -> str | None:
    if sp is None or not sp.tipo_medicao:
        return None
    return _MEASUREMENT_TYPE_PT_EN.get(sp.tipo_medicao.strip().upper())
# ponytail: tabela cobre os 12 tipos da lista padrao v6; expandir se novos tipos forem adicionados ao dominio MeasurementType do DMSMatchingTemplateInfo.


_SIGNAL_TYPE_ANALOG_PT_EN: dict[str, str] = {
    "VALOR MEDIDO": "MeasuredValue",
    "GRAVADOR DE FALHA": "FaultRecorder",
    "CONTAGEM DE OPERAÇÃO": "Custom",  # AnalogSignalType não tem OperationCount
}


def _signal_type_analog(sp) -> str:
    """Domínio AnalogSignalType (DMSMatchingTemplateInfo) a partir do tipo PT
    da lista padrão — o ADMS rejeita valor fora do domínio no import."""
    if sp is None or not sp.signal_type:
        return "Custom"
    st = sp.signal_type.strip()
    return _SIGNAL_TYPE_ANALOG_PT_EN.get(st.upper(), st)
# ponytail: cobre os 4 valores da lista padrão v2; valor novo passa reto (teste de domínio pega).


# Grandeza (Measurement Type PT da lista padrão) -> entidade do device
# mapping analógico, padrão RGE (spec 2026-07-15).
_MEDIDAS_TC = frozenset({"CORRENTE", "POTÊNCIA ATIVA", "POTÊNCIA REATIVA", "POTÊNCIA APARENTE"})
_MEDIDAS_TP = frozenset({"TENSÃO"})


def disjuntor_por_modulo(registros) -> "dict[str | None, str | None]":
    """Disjuntor único de cada módulo, usado pelo DM analógico e pelo ramo
    PROT de alimentador (spec 2026-07-20 §A2/§A3). 0 ou 2+ disjuntores
    -> None (fallback módulo-duplicado; o aviso de ambiguidade já foi emitido
    por atribuir_id_por_registro no pipeline)."""
    por_mod: dict[str | None, set[str]] = defaultdict(set)
    for rec in registros:
        ne = rec.eletrico.nome_equipamento
        if ne and familia_do_id(ne) == "Disjuntor":
            por_mod[rec.modulo.nome].add(ne)
    return {m: next(iter(ids)) if len(ids) == 1 else None for m, ids in por_mod.items()}


def _device_mapping_analog(
    subestacao: str | None,
    modulo_nome: str | None,
    tipo_medicao_pt: str | None,
    disjuntor: str | None,
) -> str:
    """Padrão RGE: corrente/potências -> <MOD>_TC; tensão -> <MOD>_TP;
    demais grandezas (KMDF, frequência, FP, temperatura...) -> disjuntor do
    módulo; sem disjuntor único -> módulo duplicado (<SUB>_<MOD>_<MOD>)."""
    modulo_fmt = modulo_nome.replace(" ", "") if modulo_nome else None
    partes = [p for p in (subestacao, modulo_fmt) if p]
    t = (tipo_medicao_pt or "").strip().upper()
    if t in _MEDIDAS_TC:
        alvo = f"{modulo_fmt}_TC" if modulo_fmt else "TC"
    elif t in _MEDIDAS_TP:
        alvo = f"{modulo_fmt}_TP" if modulo_fmt else "TP"
    else:
        alvo = disjuntor or modulo_fmt
    if alvo:
        partes.append(alvo)
    return "_".join(partes)


def _valores_analog(rec: SignalRecord, subestacao: str | None, padrao: ListaPadraoADMS,
                     alias_v1: "dict[str, str] | None" = None,
                     disjuntor: "str | None" = None) -> dict:
    sp = padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
    nome = nome_hierarquico(
        subestacao, rec.modulo.nome, rec.eletrico.nome_equipamento,
        rec.eletrico.barra, rec.sigla_sinal or "?",
    )
    indices = rec.enderecamento.indices
    coords = indices[0] if len(indices) == 1 else ";".join(str(i) for i in indices)
    alimentador = _eh_alimentador(rec.modulo.nome)
    remote_unit = _remote_unit(subestacao)
    rp_custom = f"{nome}_{remote_unit}" if remote_unit else None
    return {
        "Signal Name": nome,
        "Signal Alias": _signal_alias(rec, alias_v1),
        "Signal Type": _signal_type_analog(sp),
        "Phases": _fase_saida(rec.eletrico.fase),
        "Direction": "Read",
        "Input Coordinates": coords,
        "Side": "None",
        "Output Register": False,
        "Remote Point Type": "Analog",
        "Remote Point Name": nome,
        "Signal AOR Group": _aor_group(subestacao, alimentador),
        "Device Mapping": _device_mapping_analog(
            subestacao, rec.modulo.nome, sp.tipo_medicao if sp else None, disjuntor),
        "Remote Unit": remote_unit,
        "Remote Point Custom ID": rp_custom,
        "Remote Point Alias": _alias_hoje(),
        "Measurement Type": _measurement_type(sp),
        "Display Unit": sp.unidade_exibicao if sp and sp.unidade_exibicao not in (None, "-") else None,
    }


def _eh_discrete_analog(rec: SignalRecord, padrao: ListaPadraoADMS) -> bool:
    sp = padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
    return bool(sp and sp.categoria == "DiscreteAnalog")


def _valores_discrete_analog(rec: SignalRecord, subestacao: str | None,
                              padrao: ListaPadraoADMS,
                              alias_v1: "dict[str, str] | None" = None) -> dict:
    """TAP real (GTD DNP3_DiscreteAnalog): Measurement Type=Discrete,
    Signal Type=TapPosition, Remote Point Type=Analog, Normal Value=9,
    Device Mapping -> comando COMTAP no mesmo módulo."""
    sp = padrao.por_sigla(rec.sigla_sinal) if rec.sigla_sinal else None
    nome = nome_hierarquico(
        subestacao, rec.modulo.nome, rec.eletrico.nome_equipamento,
        rec.eletrico.barra, rec.sigla_sinal or "?",
    )
    remote_unit = _remote_unit(subestacao)
    indices = rec.enderecamento.indices
    coords = indices[0] if len(indices) == 1 else ";".join(str(i) for i in indices)
    device = nome
    ref = sp.device_mapping_ref if sp else None
    if ref and rec.sigla_sinal and nome.endswith(rec.sigla_sinal):
        device = nome[: len(nome) - len(rec.sigla_sinal)] + ref
    return {
        "Signal Name": nome,
        "Signal Alias": _signal_alias(rec, alias_v1),
        "Measurement Type": "Discrete",
        "Signal Type": (sp.signal_type if sp and sp.signal_type else "Custom"),
        "Phases": _fase_saida(rec.eletrico.fase),
        "Side": "None",
        "Direction": "Read",
        "Normal Value": sp.normal_value if sp else None,
        "Device Mapping": device,
        "Signal AOR Group": _aor_group(subestacao, _eh_alimentador(rec.modulo.nome)),
        "Input Coordinates": coords,
        "Remote Point Type": (sp.remote_point_type if sp and sp.remote_point_type else "Analog"),
        "Remote Point Name": nome,
        "Remote Unit": remote_unit,
        "Remote Point Custom ID": f"{nome}_{remote_unit}" if remote_unit else None,
        "Remote Point Alias": _alias_hoje(),
    }


def particionar_custom_id_duplicado(
    lista: ListaHomogenea,
) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]:
    """Gate de unicidade (spec 2026-07-10): o ADMS descarta remote points com
    Custom ID repetido no mesmo import. Grupos que colidem saem TODOS do TDT
    e vão para revisão — nunca saem calados no xlsx."""
    remote_unit = _remote_unit(lista.subestacao)
    por_cid: dict[str, list[SignalRecord]] = defaultdict(list)
    for rec in lista.registros:
        nome = nome_hierarquico(
            lista.subestacao, rec.modulo.nome, rec.eletrico.nome_equipamento,
            rec.eletrico.barra, rec.sigla_sinal or "?",
        )
        cid = f"{nome}_{remote_unit}" if remote_unit else nome
        por_cid[cid].append(rec)
    duplicados = {id(r) for grupo in por_cid.values() if len(grupo) > 1 for r in grupo}
    if not duplicados:
        return lista, ()
    motivo_por_id: dict[int, str] = {}
    for grupo in por_cid.values():
        if len(grupo) <= 1:
            continue
        # mesma derivação de modelo_tabela.sheet_origem
        sheets = {r.id.rsplit(":", 1)[0] if ":" in r.id else "" for r in grupo}
        motivo = "modulo_duplicado_entre_sheets" if len(sheets) > 1 else "custom_id_duplicado"
        for r in grupo:
            motivo_por_id[id(r)] = motivo
    revisao = tuple(
        ItemRevisao(replace(r, status="revisao"), motivo=motivo_por_id[id(r)])
        for r in lista.registros if id(r) in duplicados
    )
    restantes = tuple(r for r in lista.registros if id(r) not in duplicados)
    return replace(lista, registros=restantes), revisao


def particionar_endereco_duplicado(
    lista: ListaHomogenea,
) -> tuple[ListaHomogenea, tuple[ItemRevisao, ...]]:
    """Gate por módulo (SP-CVA2 E6.2): dois pontos do MESMO módulo, no MESMO
    espaço de endereçamento (categoria, in/out), com o mesmo índice, saem
    TODOS da lista e vão pra revisão. Sintoma típico: direção errada na
    origem (comando lido como Input colide com o Input real de mesmo índice
    — hipótese CVA11). Módulo entra na chave: índice local reusado entre
    módulos DISTINTOS (IEDs/linhas diferentes) é endereçamento normal, não
    colisão (achado do decision gate original, ver nota no topo da task) —
    mesmo racional de `_chave` em dc_pairer/normalizador_estrutural e do
    Custom ID em `particionar_custom_id_duplicado` (`_remote_unit` é
    constante por SUBESTAÇÃO, não desambigua módulo). MultiCoord/DoubleBit
    contribuem cada índice individualmente."""
    grupos: dict[tuple, dict[str, SignalRecord]] = defaultdict(dict)
    for rec in lista.registros:
        mod = rec.modulo.nome
        cat = rec.tipo_sinal.categoria
        espaco_in = "out" if rec.tipo_sinal.direcao == "Output" else "in"
        for idx in rec.enderecamento.indices:
            grupos[(mod, cat, espaco_in, idx)][rec.id] = rec
        for idx in rec.enderecamento.indices_saida:
            grupos[(mod, cat, "out", idx)][rec.id] = rec

    colididos: dict[str, SignalRecord] = {}
    for regs in grupos.values():
        if len(regs) > 1:
            colididos.update(regs)
    if not colididos:
        return lista, ()
    restantes = tuple(r for r in lista.registros if r.id not in colididos)
    revisao = tuple(
        ItemRevisao(r, motivo="endereco_duplicado") for r in colididos.values()
    )
    return replace(lista, registros=restantes), revisao


def gerar(
    lista: ListaHomogenea,
    template_path: str | Path,
    lista_padrao: ListaPadraoADMS,
    alias_v1: "dict[str, str] | None" = None,
) -> openpyxl.Workbook:
    wb = openpyxl.load_workbook(template_path)  # mantém fórmulas/estilos
    regs_da = [r for r in lista.registros if _eh_discrete_analog(r, lista_padrao)]
    ids_da = {id(r) for r in regs_da}
    regs_disc = [r for r in lista.registros
                 if r.tipo_sinal.categoria == "Discrete" and id(r) not in ids_da]
    regs_ana = [r for r in lista.registros
                if r.tipo_sinal.categoria == "Analog" and id(r) not in ids_da]
    disj = disjuntor_por_modulo(lista.registros)
    _escrever_sheet(
        wb[SHEET_DISCRETOS], SHEET_DISCRETOS, COLUNAS_ESPERADAS,
        regs_disc,
        lambda rec, sub, padrao: _valores(
            rec, sub, padrao, alias_v1, disj.get(rec.modulo.nome)),
        lista.subestacao, lista_padrao,
    )
    _escrever_sheet(
        wb[SHEET_ANALOGICOS], SHEET_ANALOGICOS, COLUNAS_ESPERADAS_ANALOG,
        regs_ana,
        lambda rec, sub, padrao: _valores_analog(
            rec, sub, padrao, alias_v1, disj.get(rec.modulo.nome)),
        lista.subestacao, lista_padrao,
    )
    if regs_da:
        _escrever_sheet(
            wb[SHEET_DISCRETE_ANALOG], SHEET_DISCRETE_ANALOG,
            COLUNAS_ESPERADAS_DISCRETE_ANALOG, regs_da,
            lambda rec, sub, padrao: _valores_discrete_analog(rec, sub, padrao, alias_v1),
            lista.subestacao, lista_padrao,
        )
    return wb


def _escrever_sheet(ws, sheet_nome, colunas_esperadas, registros, valores_fn, subestacao, padrao):
    if ws.max_column != colunas_esperadas:
        raise ValueError(
            f"{sheet_nome} tem {ws.max_column} colunas, esperado "
            f"{colunas_esperadas} — template desatualizado?"
        )
    colunas = _mapa_colunas(ws)
    linha = PRIMEIRA_LINHA_DADOS
    for rec in registros:
        for display, valor in valores_fn(rec, subestacao, padrao).items():
            col = colunas.get(display)
            if col and valor is not None:
                ws.cell(linha, col, valor)
        linha += 1
    ultima = linha - 1
    _expandir_tabela(ws, sheet_nome, ultima)
    if ultima >= PRIMEIRA_LINHA_DADOS:
        _expandir_cf(ws, ultima_linha=ultima)
        _expandir_dv(ws, ultima_linha=ultima)


def _expandir_tabela(ws, sheet_nome: str, ultima_linha: int) -> None:
    """Ajusta o ref do ListObject para cobrir as linhas de dados escritas."""
    if sheet_nome not in ws.tables:
        return
    ultima_col = get_column_letter(ws.max_column)
    fim = max(ultima_linha, PRIMEIRA_LINHA_DADOS)
    ws.tables[sheet_nome].ref = f"A4:{ultima_col}{fim}"


def _expandir_range_row5(sqref: str, até_linha: int) -> str:
    """Expande range(s) que começam na row 5 para até a linha dada.

    Ex: 'A5' -> 'A5:A{n}', 'AP5:AQ5' -> 'AP5:AQ{n}',
    'B5 Y5' (multi-range da TDT real) -> 'B5:B{n} Y5:Y{n}'.
    """
    return " ".join(_expandir_token_row5(t, até_linha) for t in sqref.split())


def _expandir_token_row5(token: str, até_linha: int) -> str:
    m = re.match(r'^([A-Z]+)5(?::([A-Z]+)5)?$', token)
    if not m:
        return token
    col1 = m.group(1)
    col2 = m.group(2)
    if col2:
        return f"{col1}5:{col2}{até_linha}"
    return f"{col1}5:{col1}{até_linha}"


def _expandir_cf(ws, ultima_linha: int) -> None:
    """Expande conditional formatting rules da row 5 para todo o range de dados."""
    cfl = ws.conditional_formatting
    items = []
    for cf in cfl:
        sqref = _expandir_range_row5(str(cf.sqref), ultima_linha)
        for rule in cf.rules:
            items.append((sqref, rule))
    if not items:
        return
    cfl._cf_rules.clear()
    for sqref, rule in items:
        cfl.add(sqref, rule)


def _expandir_dv(ws, ultima_linha: int) -> None:
    """Expande data validations da row 5 para todo o range de dados."""
    for dv in ws.data_validations.dataValidation:
        novo = _expandir_range_row5(str(dv.sqref), ultima_linha)
        if novo != str(dv.sqref):
            dv.sqref = novo


def salvar(wb: openpyxl.Workbook, destino: str | Path) -> None:
    wb.save(destino)
