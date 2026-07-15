"""Inferência de equipamento por topologia do módulo (SP C2).

Quando a linha não informa o equipamento explicitamente (``eletrico.
equipamento_alvo is None``), infere a família (Disjuntor/Seccionadora/...) a
partir da topologia típica do tipo de módulo (C1) — determinístico, com
fallback a revisão sob ambiguidade. ``nome_equipamento`` (o ID, ex. "52-2")
NUNCA é inventado aqui — só a família.

C2.4: subdivide o módulo Transformador por lado (AT/BT) quando há pista
confiável — necessário porque o mesmo módulo (ex. TR1) recebe duas vezes a
mesma grandeza (uma por lado), colidindo na chave de dedup (módulo, equip,
sigla) usada por ``normalizador_estrutural``/``dc_pairer``.

Módulo puro: conhece só ``contracts`` + ``config``. ``pipeline.py`` integra.

ponytail: inferência só do default quando a topologia tem 1 principal; o
resto vai pra revisão. Subdivisão AT/BT só quando o lado é determinável;
senão revisão (sem falso positivo).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace

from tdt.config import Config
from tdt.contracts import SignalRecord
from tdt.normalizacao.normalizador import _EQUIPAMENTO_PALAVRA, familia_do_id

_TOKENS = re.compile(r"[A-Za-z]+")


def _tokens(texto: str) -> set[str]:
    return set(_TOKENS.findall(texto.upper()))


def _equipamento_explicito_no_texto(rec: SignalRecord, topologia_equipamentos: tuple[str, ...]) -> str | None:
    """Casa token whole-word de equipamento da topologia na descrição.

    Reusa o vocabulário de ``normalizador._EQUIPAMENTO_PALAVRA`` (DISJUNTOR/
    DISJ/DJ, SECCIONADORA/SECCION/SECC) — mesma fonte que N0 usa pra extrair
    do texto bruto; aqui casamos no texto já canônico/normalizado.
    """
    tokens = _tokens(rec.descricoes.normalizada)
    for tok in tokens:
        equip = _EQUIPAMENTO_PALAVRA.get(tok)
        if equip is not None and equip in topologia_equipamentos:
            return equip
    return None


def inferir_equipamento(registros: list[SignalRecord], config: Config) -> list[SignalRecord]:
    """Infere ``eletrico.equipamento_alvo`` pela topologia do tipo de módulo.

    Por módulo (agrupado por ``modulo.nome``), pra cada registro com
    ``equipamento_alvo is None``:
    1. Pista explícita de outro equipamento da topologia no texto -> atribui
       esse (marcado inferido, ``equipamento_inferido=True``).
    2. Senão, default não-ambíguo da topologia do tipo -> atribui o default
       (marcado inferido).
    3. Senão -> permanece ``equipamento_alvo=None`` (ambíguo). O CHAMADOR
       (``pipeline.py``) decide o que fazer com isso — aqui não setamos
       ``status``/``justificativa`` porque o scoring (``roteador.rotear``)
       sempre os sobrescreve depois; quem precisa saber que ficou ambíguo
       lê ``eletrico.equipamento_alvo is None`` no resultado.

    Registros que já têm ``equipamento_alvo`` (extraído em N0) não são
    tocados -- nem ``nome_equipamento`` (o ID) é inventado em nenhum caso.
    """
    saida = list(registros)
    for i, rec in enumerate(saida):
        if rec.eletrico.equipamento_alvo is not None:
            continue  # já extraído (N0) -- não sobrescreve

        tipo = rec.modulo.tipo
        topologia = config.topologia_por_tipo.get(tipo) if tipo else None
        if topologia is None:
            continue  # tipo sem topologia conhecida -- permanece ambíguo

        explicito = _equipamento_explicito_no_texto(rec, topologia.equipamentos)
        if explicito is not None:
            saida[i] = replace(
                rec,
                eletrico=replace(rec.eletrico, equipamento_alvo=explicito, equipamento_inferido=True),
            )
            continue

        if topologia.default is not None:
            saida[i] = replace(
                rec,
                eletrico=replace(
                    rec.eletrico, equipamento_alvo=topologia.default, equipamento_inferido=True,
                ),
            )
            # senão: permanece None -- ambíguo, sem default claro.

    return saida


# --- C2.4: subdivisão de módulo Transformador por lado AT/BT ----------------

_GAP_MINIMO_BLOCO = 5  # endereços a mais de 5 do bloco contam como outro bloco


def _normaliza_celula(v) -> str:
    if v is None:
        return ""
    return str(v).strip().upper()


def derivar_secao_por_linha(
    rows: list[tuple], sheet_name: str, coluna_modulo_nome: str = "MÓDULO",
) -> dict[str, str]:
    """Lê a coluna "Módulo" (marcador de seção por linha, ex. "TR1_AT"/
    "TR1_MT") do layout não-homogêneo e devolve ``{id: valor_da_celula}``,
    ``id`` no formato estável ``f"{sheet}:{linha 1-based}"`` (mesmo formato
    usado por ``estruturador.estruturar``). Quem decide AT/BT a partir do
    valor cru é ``_lado_de_secao`` (chamado por
    ``subdividir_transformador_at_bt``); aqui só localizamos e lemos a coluna.

    Sem coluna "Módulo" identificável -> dict vazio (pista 1 simplesmente não
    contribui; pistas 2/3 continuam disponíveis).
    """
    nomes_aceitos = {coluna_modulo_nome.upper(), "MODULO"}  # com/sem acento
    col_idx: int | None = None
    header_linha: int | None = None
    for i, row in enumerate(rows[:30]):
        for c, v in enumerate(row):
            if _normaliza_celula(v).replace("Ó", "O") in nomes_aceitos:
                col_idx, header_linha = c, i
                break
        if col_idx is not None:
            break
    if col_idx is None or header_linha is None:
        return {}

    saida: dict[str, str] = {}
    for i, row in enumerate(rows[header_linha + 1:], start=header_linha + 2):
        if col_idx < len(row) and row[col_idx] is not None:
            saida[f"{sheet_name}:{i}"] = str(row[col_idx])
    return saida


def _lado_de_secao(valor: str | None) -> str | None:
    if not valor:
        return None
    v = valor.upper()
    if "AT" in v or "PRIM" in v or "ALTA" in v:
        return "AT"
    if "BT" in v or "MT" in v or "SEC" in v or "BAIXA" in v:
        return "BT"
    return None


def _agrupar_blocos_contiguos(indices_ordenados: list[tuple[int, int]]) -> list[list[int]]:
    """Agrupa (endereco, idx_original) ordenados por endereço em blocos
    contíguos (gap <= _GAP_MINIMO_BLOCO mantém no mesmo bloco)."""
    blocos: list[list[int]] = []
    atual: list[int] = []
    anterior: int | None = None
    for endereco, idx in indices_ordenados:
        if anterior is not None and endereco - anterior > _GAP_MINIMO_BLOCO:
            blocos.append(atual)
            atual = []
        atual.append(idx)
        anterior = endereco
    if atual:
        blocos.append(atual)
    return blocos


def subdividir_transformador_at_bt(
    registros: list[SignalRecord],
    config: Config,
    secao_por_id: dict[str, str] | None = None,
) -> list[SignalRecord]:
    """Subdivide módulos de tipo Transformador em ``<nome>AT``/``<nome>BT``.

    Pistas de lado, em ordem (a primeira que decidir vence, por registro):
    1. ``secao_por_id[rec.id]`` — seção/sheet/marcador interno (injetado pelo
       chamador; aqui chega já como string livre, ex. "AT"/"TR1_MT"/"BT").
    2. ``eletrico.nivel_tensao`` já extraído (PRIMARIO/ALTA->AT,
       SECUNDARIO/BAIXA->BT, via ``r6_lado_tensao``/``normalizador``).
    3. Faixa de endereço contígua: registros sem pista 1/2 que caem no MESMO
       bloco contíguo de outro registro do mesmo módulo que JÁ tem lado
       resolvido (pistas 1/2) herdam esse lado — heurística mais fraca,
       nunca decide por si só qual bloco é AT/qual é BT sem uma âncora.

    Sem nenhuma pista -> não subdivide (mantém o nome original; o caso
    permanece sujeito a ``endereco_duplicado`` em revisão downstream).
    """
    secao_por_id = secao_por_id or {}
    por_modulo: dict[str | None, list[int]] = defaultdict(list)
    for i, rec in enumerate(registros):
        if rec.modulo.tipo == "Transformador":
            por_modulo[rec.modulo.nome].append(i)

    saida = list(registros)
    for modulo_nome, idxs in por_modulo.items():
        lado_por_idx: dict[int, str] = {}
        for i in idxs:
            rec = saida[i]
            lado = _lado_de_secao(secao_por_id.get(rec.id)) or _lado_de_secao(rec.eletrico.nivel_tensao)
            if lado is not None:
                lado_por_idx[i] = lado

        # Pista 3: propaga lado resolvido (1/2) para vizinhos contíguos sem
        # pista, dentro do mesmo módulo -- só quando há endereço.
        com_endereco = [
            (saida[i].enderecamento.indices[0], i)
            for i in idxs
            if saida[i].enderecamento.indices
        ]
        if com_endereco:
            com_endereco.sort()
            for bloco in _agrupar_blocos_contiguos(com_endereco):
                lados_no_bloco = {lado_por_idx[i] for i in bloco if i in lado_por_idx}
                if len(lados_no_bloco) == 1:
                    (lado_ancora,) = lados_no_bloco
                    for i in bloco:
                        lado_por_idx.setdefault(i, lado_ancora)
                # len == 0 (nenhuma âncora) -> não decide; len > 1 (bloco
                # misto) -> ambíguo, não propaga (evita falso positivo).

        if not lado_por_idx:
            continue  # nenhuma pista pra nenhum sinal do módulo -- não subdivide

        for i, lado in lado_por_idx.items():
            rec = saida[i]
            saida[i] = replace(rec, modulo=replace(rec.modulo, nome=f"{modulo_nome}{lado}"))

    return saida


# --- registro de equipamentos por módulo (SP-DEVICE-MAPPING-RGE, task 3) ----


def atribuir_id_por_registro(
    registros: list[SignalRecord],
) -> tuple[list[SignalRecord], list[str]]:
    """Preenche ``eletrico.nome_equipamento`` a partir dos equipamentos REAIS
    achados na sheet (spec 2026-07-15): por módulo, se existe exatamente 1
    equipamento da família do sinal, atribui o ID. 2+ da mesma família ->
    aviso (1 por módulo+família) e o ID fica vazio (o fallback do device
    mapping em engine_tdt resolve). Nunca inventa ID — só reusa o que outra
    linha do mesmo módulo declarou. Complementa ``inferir_equipamento`` (C2),
    que preenche só a FAMÍLIA; roda depois dele no pipeline.
    """
    registro: dict[str | None, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for rec in registros:
        ne = rec.eletrico.nome_equipamento
        fam = familia_do_id(ne)
        if ne and fam:
            registro[rec.modulo.nome][fam].add(ne)

    avisos: list[str] = []
    avisados: set[tuple[str | None, str]] = set()
    saida = list(registros)
    for i, rec in enumerate(saida):
        fam = rec.eletrico.equipamento_alvo
        if fam is None or rec.eletrico.nome_equipamento is not None:
            continue
        ids = registro[rec.modulo.nome].get(fam, set())
        if len(ids) == 1:
            (unico,) = ids
            saida[i] = replace(
                rec, eletrico=replace(rec.eletrico, nome_equipamento=unico),
            )
        elif len(ids) > 1 and (rec.modulo.nome, fam) not in avisados:
            avisados.add((rec.modulo.nome, fam))
            avisos.append(
                f"módulo {rec.modulo.nome}: {len(ids)} equipamentos da família "
                f"{fam} na sheet ({', '.join(sorted(ids))}) — ID não atribuído "
                f"aos sinais sem equipamento explícito"
            )
    return saida, avisos
