"""Exporta o ResultadoPipeline da tela de Análise (Parte 2) para .xlsx.

Só monta o relatório — não decide, não filtra, não toca em ModeloAnalise/
TelaAnalise (SRP). O dedupe de registros que aparecem tanto em
``lista.registros`` quanto em ``revisao`` replica o padrão usado em
``TelaAnalise.carregar`` para manter tela e relatório consistentes.
"""

from __future__ import annotations

from pathlib import Path

import openpyxl

from tdt.contracts import ResultadoPipeline, SignalRecord

_HEADERS = [
    "ID", "Descrição", "Sigla Decidida", "Status",
    "Score Final", "TF-IDF", "Vetorial", "Fuzzy",
    "Gap", "Motivo Revisão",
]

_METODOS = ("tfidf", "vetorial", "fuzzy")


def _registros_sem_duplicar(resultado: ResultadoPipeline) -> list[SignalRecord]:
    registros = list(resultado.lista.registros)
    ids_existentes = {r.id for r in registros}
    for item in resultado.revisao:
        if item.registro.id not in ids_existentes:
            registros.append(item.registro)
            ids_existentes.add(item.registro.id)
    return registros


def _gap(rec: SignalRecord) -> float | None:
    if not rec.candidatos:
        return None
    if len(rec.candidatos) < 2:
        return rec.candidatos[0].score
    return round(rec.candidatos[0].score - rec.candidatos[1].score, 4)


def _scores_metodo(rec: SignalRecord) -> dict[str, float]:
    if rec.diagnostico is None or rec.sigla_sinal is None:
        return {}
    return rec.diagnostico.scores_por_metodo.get(rec.sigla_sinal, {})


def _preencher_qualidade(ws, registros, revisao_por_id: dict[str, str]) -> None:
    ws.append(_HEADERS)
    for rec in registros:
        scores = _scores_metodo(rec)
        ws.append([
            rec.id,
            rec.descricoes.bruta,
            rec.sigla_sinal,
            rec.status,
            rec.candidatos[0].score if rec.candidatos else None,
            scores.get("tfidf"),
            scores.get("vetorial"),
            scores.get("fuzzy"),
            _gap(rec),
            revisao_por_id.get(rec.id, ""),
        ])


def _preencher_estatisticas(ws, registros, revisao) -> None:
    total = len(registros)
    decididos = sum(1 for r in registros if r.status == "decidido")
    taxa = f"{decididos / total * 100:.1f}%" if total else "—"

    ws.append(["Métrica", "Valor"])
    ws.append(["Total", total])
    ws.append(["Decididos", decididos])
    ws.append(["Revisão", len(revisao)])
    ws.append(["Taxa de Decisão", taxa])
    ws.append([])
    ws.append(["Motivo Revisão", "Contagem"])

    motivos: dict[str, int] = {}
    for item in revisao:
        motivos[item.motivo] = motivos.get(item.motivo, 0) + 1
    for motivo, contagem in sorted(motivos.items(), key=lambda kv: -kv[1]):
        ws.append([motivo, contagem])


def exportar_relatorio(resultado: ResultadoPipeline, destino: str | Path) -> None:
    """Gera um .xlsx com qualidade do matching por sinal e estatísticas gerais."""
    registros = _registros_sem_duplicar(resultado)
    revisao_por_id = {item.registro.id: item.motivo for item in resultado.revisao}

    wb = openpyxl.Workbook()
    ws_qualidade = wb.active
    ws_qualidade.title = "Qualidade por Sinal"
    _preencher_qualidade(ws_qualidade, registros, revisao_por_id)

    ws_stats = wb.create_sheet("Estatísticas")
    _preencher_estatisticas(ws_stats, registros, resultado.revisao)

    wb.save(destino)
