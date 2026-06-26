"""Lê a V2, gera o mockup e grava CSV de inspeção (não usado em runtime).

Uso: PYTHONPATH=scripts/treino:scripts/enriquecer_v5:src python scripts/treino/dump_mockup.py
"""
from __future__ import annotations

import csv
import pathlib
import sys

_here = pathlib.Path(__file__).resolve().parent
_root = _here.parents[1]
for _p in (_here, _root / "src", _root / "scripts" / "enriquecer_v5"):
    sys.path.insert(0, str(_p))

from tdt.dados.lista_padrao import ListaPadraoADMS
from mockup import gerar_dataset

V2 = "docs/Pontos Padrao ADMS_v2.xlsx"
OUT = "docs/mockup_treino_amostra.csv"


def main() -> None:
    lp = ListaPadraoADMS.carregar(V2)
    pares = [(s.descricao, s.sigla) for s in (*lp.discretos, *lp.analogicos) if s.descricao]
    ds = gerar_dataset(pares, n_variantes=2, seed=0)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["texto", "sigla", "nivel"])
        w.writerows(ds)
    print(f"{len(ds)} pares de {len(pares)} sinais -> {OUT}")


if __name__ == "__main__":
    main()
