"""Pureza das pistas lexicais → classe TYPE SEVERIDADE, medida na própria
lista padrão (descrição de cada sinal discreto vs sua classe real).

Uso: PYTHONPATH=src python bench/diag_type_severidade.py
Critério (spec SP-METADADOS §3): manter pista com pureza >= 90% e >= 5 hits.
"""
from __future__ import annotations

import unicodedata
from collections import Counter

from tdt.dados.lista_padrao import ListaPadraoADMS


def _ascii_upper(s: str) -> str:
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().upper()


# Mesmas pistas candidatas da r9 (manter em sincronia com motor_regras._PISTAS_TS)
PISTAS = {
    "PROT": {"TRIP"},
    "FALHAS FCOM/VCA/VCC": {"VCA", "VCC"},
    "FUNCOES/43/PARALELISMO": {"43"},
}


def main() -> None:
    lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v2.xlsx")
    for classe_alvo, pistas in PISTAS.items():
        for pista in sorted(pistas):
            contagem: Counter[str] = Counter()
            for s in lp.discretos:
                if not s.descricao or not s.type_severidade:
                    continue
                tokens = set(_ascii_upper(s.descricao).split())
                if pista in tokens:
                    contagem[_ascii_upper(s.type_severidade)] += 1
            total = sum(contagem.values())
            acertos = contagem.get(classe_alvo, 0)
            pureza = 100.0 * acertos / total if total else 0.0
            veredito = "MANTER" if pureza >= 90.0 and total >= 5 else "REMOVER"
            print(f"{classe_alvo:28s} {pista:14s} hits={total:3d} pureza={pureza:5.1f}% {veredito}")


if __name__ == "__main__":
    main()
