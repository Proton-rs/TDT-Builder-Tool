"""Diagnostico SP-G (pos-review): reconcilia a contagem "96" (spec Caso 2)
com a contagem "24" observada em bench/resultados/spG_diag_decisor.txt.

Le o arquivo de auditoria de PRODUCAO original (output/LISTA 1 - GTD/
Auditoria_Revisao.xlsx) e conta, entre as linhas com Sigla Decidida == "DJA1"
e Score Final == 0.858, quantas tem Descricao Bruta contendo "Intertravamento"
(bug — nao e palavra de posicao) vs "Desligado" (possivelmente correto — E
palavra de posicao) vs outras (ex.: "Indefinido", "Ligado").

Uso: python bench/diag_spg_dja1_populacao.py
"""
from __future__ import annotations

from collections import Counter

import openpyxl

_AUDITORIA = "output/LISTA 1 - GTD/Auditoria_Revisao.xlsx"

# indices de coluna na aba "Auditoria" (ver header da planilha)
_COL_DESC_BRUTA = 1
_COL_SIGLA_DECIDIDA = 5
_COL_SCORE_FINAL = 6


def main() -> None:
    wb = openpyxl.load_workbook(_AUDITORIA, read_only=True, data_only=True)
    ws = wb["Auditoria"]
    rows = ws.iter_rows(values_only=True)
    next(rows)  # header

    scores_por_sigla: Counter[str] = Counter()
    grupo = Counter()
    outros: list[str] = []

    for row in rows:
        if row is None:
            continue
        sigla = row[_COL_SIGLA_DECIDIDA]
        score = row[_COL_SCORE_FINAL]
        desc = row[_COL_DESC_BRUTA] or ""
        if sigla != "DJA1" or score is None:
            continue
        scores_por_sigla[str(score)] += 1
        try:
            score_f = float(score)
        except (TypeError, ValueError):
            continue
        if abs(score_f - 0.858) > 1e-6:
            continue
        desc_up = desc.upper()
        if "INTERTRAVAMENTO" in desc_up:
            grupo["Intertravamento (bug — nao e palavra de posicao)"] += 1
        elif "DESLIGADO" in desc_up:
            grupo["Desligado (possivelmente correto — E palavra de posicao)"] += 1
        else:
            grupo["Outro (Indefinido/Ligado/etc. — checar caso a caso)"] += 1
            outros.append(desc)

    print(f"Distribuicao de score entre TODAS as linhas DJA1 (qualquer score): {dict(scores_por_sigla)}")
    total_858 = sum(grupo.values())
    print(f"\nTotal DJA1 @ score exato 0.858: {total_858}")
    for k, v in grupo.items():
        print(f"  - {k}: {v}")
    print("\nDescricoes do grupo 'Outro':")
    for d in outros:
        print(f"  - {d!r}")


if __name__ == "__main__":
    main()
