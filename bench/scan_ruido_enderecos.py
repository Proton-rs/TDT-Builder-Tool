"""SP-M -- varredura sistematica do log `bench/resultados/diag_enderecos.log`.

Objetivo: substituir a inspecao manual (linha-a-linha, sheet por sheet) que
ja deixou passar 2 casos reais em 2 rodadas de revisao anteriores (S4_LOG/GPR
na Fase 1 original, depois FWB, depois CALCULADOS -- sempre achado pelo
revisor, nunca pela varredura manual do implementador).

Este script NAO reimplementa a deteccao de endereco -- ele so faz PARSING
do log ja gerado por `bench/diag_enderecos.py` (que roda o detector real do
pipeline, `analisar()`/`_col_indice`) e sinaliza, de forma exaustiva e
determinística, toda sheet onde:

  1. a coluna ESCOLHIDA como `col_indice` tem rotulo (header) que bate um
     termo de "contador de posicao/linha" (linha, line, seq, row, item,
     n°/no./num...), E
  2. existe pelo menos uma coluna CONCORRENTE logada (>=50% inteiros, ver
     `_colunas_numericas_confundiveis` em diag_enderecos.py) cujo rotulo bate
     um termo de "endereco de protocolo real" (dnp3, index, endereco, addr,
     entrada binaria, utr cos, bit, word, registrador, coordinate, endpt...).

Uso:
    python bench/scan_ruido_enderecos.py
    (le bench/resultados/diag_enderecos.log; rode bench/diag_enderecos.py antes
    se precisar regenerar o log.)
"""
from __future__ import annotations

import re
from pathlib import Path

LOG = Path("bench/resultados/diag_enderecos.log")


def _norm(s: str) -> str:
    s = s.lower().strip()
    for a, b in (
        ("á", "a"), ("à", "a"), ("ã", "a"), ("â", "a"),
        ("é", "e"), ("ê", "e"),
        ("í", "i"),
        ("ó", "o"), ("õ", "o"), ("ô", "o"),
        ("ú", "u"),
        ("ç", "c"),
    ):
        s = s.replace(a, b)
    return s


def is_row_counter_label(label: str) -> bool:
    l = _norm(label)
    if not l:
        return False
    for term in ("linha", "line", "seq", "row", "item"):
        if term in l:
            return True
    if re.search(r"\bn[o°]?\b", l) and len(l) <= 4:
        return True
    if re.search(r"\bnum\b", l):
        return True
    return False


def is_addr_label(label: str) -> bool:
    l = _norm(label)
    if not l:
        return False
    for term in (
        "dnp3", "index", "endereco", "addr", "entrada binaria", "utr cos",
        "bit", "word", "registrador", "coordinate", "endpt", "n4", "n3",
    ):
        if term in l:
            return True
    return False


_FILE_RE = re.compile(r"^## (.+)$")
_SHEET_RE = re.compile(
    r"^\s*\[(.+?)\] rota=NAO-HOMOGENEO header_row=(\S+) col_indice=(\S+) label=(.+?) cols="
)
_CONC_RE = re.compile(
    r"^\s*concorrente col=(\S+) label=(.+?) score=(\S+) frac_int=(\S+) "
    r"mono=(\S+) faixa=\[(-?\d+),(-?\d+)\] n=(\d+)"
)


def scan(log_path: Path = LOG):
    """Retorna lista de dicts: cada um é uma sheet flagada (coluna escolhida
    parece contador de posicao E ha >=1 concorrente com cara de endereco
    real), com todos os concorrentes que bateram o criterio de endereco."""
    lines = log_path.read_text(encoding="utf-8").splitlines()

    flagged = []
    current_file = current_sheet = current_label = current_col = None
    pending = []

    def flush():
        nonlocal pending
        if current_sheet is not None and is_row_counter_label(current_label):
            addr_competitors = [c for c in pending if is_addr_label(c["label"])]
            if addr_competitors:
                flagged.append({
                    "file": current_file,
                    "sheet": current_sheet,
                    "chosen_label": current_label,
                    "chosen_col": current_col,
                    "competitors": addr_competitors,
                })
        pending = []

    for raw in lines:
        fm = _FILE_RE.match(raw)
        if fm:
            flush()
            current_file = fm.group(1)
            current_sheet = None
            continue
        sm = _SHEET_RE.match(raw)
        if sm:
            flush()
            current_sheet = sm.group(1)
            current_col = sm.group(3)
            current_label = sm.group(4).strip().strip("'\"")
            continue
        cm = _CONC_RE.match(raw)
        if cm:
            pending.append({
                "col": cm.group(1),
                "label": cm.group(2).strip().strip("'\""),
                "score": float(cm.group(3)),
                "frac_int": float(cm.group(4)),
                "mono": float(cm.group(5)),
                "min": int(cm.group(6)),
                "max": int(cm.group(7)),
                "n": int(cm.group(8)),
            })
            continue
    flush()
    return flagged


def main():
    flagged = scan()
    print(
        f"Total de sheets flagadas (col_indice=contador de posicao E "
        f">=1 concorrente com cara de endereco real): {len(flagged)}\n"
    )
    for f in flagged:
        print(f"FILE={f['file']}")
        print(f"  SHEET={f['sheet']!r}  escolhida='{f['chosen_label']}' (col={f['chosen_col']})")
        for c in f["competitors"]:
            print(
                f"    concorrente: label='{c['label']}' col={c['col']} "
                f"score={c['score']} frac_int={c['frac_int']} mono={c['mono']} "
                f"faixa=[{c['min']},{c['max']}] n={c['n']}"
            )
        print()


if __name__ == "__main__":
    main()
