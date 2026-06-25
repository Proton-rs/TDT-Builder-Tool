"""Gera Auditoria_Revisao.xlsx: uma linha por sinal com status, sigla
decidida, scores por método e os candidatos descartados — para cruzar com
a TDT na auditoria pós-classificação."""

from __future__ import annotations

from pathlib import Path

import openpyxl

from tdt.contracts import ItemRevisao, SignalRecord

CABECALHO = [
    "ID Sinal", "Descrição Bruta", "Tipo", "Endereço", "Status",
    "Sigla Decidida", "Score Final", "Motivo Revisão",
    "Candidato 1", "Score tfidf 1", "Score vetorial 1", "Score fuzzy 1",
    "Candidato 2", "Score tfidf 2", "Score vetorial 2", "Score fuzzy 2",
    "Candidato 3", "Score tfidf 3", "Score vetorial 3", "Score fuzzy 3",
]


def _scores_metodo(rec: SignalRecord, sigla: str | None) -> tuple[str, str, str]:
    if rec.diagnostico is None or sigla is None:
        return ("", "", "")
    por = rec.diagnostico.scores_por_metodo.get(sigla, {})
    return tuple(
        f"{por[m]:.3f}" if m in por else "" for m in ("tfidf", "vetorial", "fuzzy")
    )


def gerar_relatorio_revisao(
    registros: list[SignalRecord],
    revisao: tuple[ItemRevisao, ...],
    destino: str | Path,
) -> Path:
    motivo_por_id = {it.registro.id: it.motivo for it in revisao}
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Auditoria"
    ws.append(CABECALHO)
    for rec in registros:
        linha = [
            rec.id,
            rec.descricoes.bruta,
            f"{rec.tipo_sinal.categoria}/{rec.tipo_sinal.direcao}",
            ";".join(str(i) for i in rec.enderecamento.indices),
            rec.status,
            rec.sigla_sinal or "",
            f"{rec.candidatos[0].score:.3f}" if rec.candidatos else "",
            motivo_por_id.get(rec.id, ""),
        ]
        for c in rec.candidatos[:3]:
            linha.append(c.sigla)
            linha.extend(_scores_metodo(rec, c.sigla))
        linha += [""] * (len(CABECALHO) - len(linha))
        ws.append(linha)
    saida = Path(destino) / "Auditoria_Revisao.xlsx"
    wb.save(str(saida))
    return saida
