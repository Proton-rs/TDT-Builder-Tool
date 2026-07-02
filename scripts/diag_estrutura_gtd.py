"""Diagnóstico estrutural SP-E: TDT gerado × TDT real (DNP3_DiscreteSignals).

Uso: PYTHONPATH=src python scripts/diag_estrutura_gtd.py GERADO.xlsx REAL.xlsx

Metas ESTRUTURAIS do SP-E (spec 2026-07-01-semantica-estados-multicoord §4) —
determinam o veredito PASS/FAIL:
- 0 double-bit falso (fusão de 2 sinais que o real mantém separados)
- MultiCoord emitido nos pares de posição (real GTD: 44; o gerado só cobre os
  vãos que o matching resolveu, então < 44 é esperado, não uma falha do SP-E)
- SGFT presente (prova de que o filtro estado→tipo separa SGF de SGFT)
- 0 Write não-legitimado (só CDC é Write; comando órfão vai a revisão)

Nomes duplicados são reportados como DIAGNÓSTICO informativo, NÃO entram no
veredito: sua causa é matching de sigla-irmã de qualificador (SF6A/SF6B,
67NT1×67NT2 — spec D eixo 1) e proteção principal/alternada P_/A_ dos módulos
LT — ambos fora do escopo do SP-E (confirmado com o usuário)."""
import sys
from collections import Counter, defaultdict

import openpyxl


def carregar(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb["DNP3_DiscreteSignals"]
    rows = ws.iter_rows(values_only=True)
    next(rows); next(rows)
    fields = [str(c) if c is not None else "" for c in next(rows)]
    next(rows)
    idx = {f: i for i, f in enumerate(fields)}

    def col(parte):
        return next((i for f, i in idx.items() if parte in f), None)

    c = {"name": col("IDOBJ_NAME"), "dt": col("DINPUTDNP3_DATATYPE"),
         "dir": col("SIGNAL_DIRECTION"), "inc": col("INCOORDS")}
    sinais = []
    for row in rows:
        if c["name"] is None or not row[c["name"]]:
            continue
        sinais.append({k: (str(row[i]) if i is not None and row[i] is not None else "")
                       for k, i in c.items()})
    return sinais


def main():
    gen = carregar(sys.argv[1])
    real = carregar(sys.argv[2])

    dt_gen = Counter(s["dt"] for s in gen)
    dt_real = Counter(s["dt"] for s in real)
    dir_gen = Counter(s["dir"] for s in gen)
    dir_real = Counter(s["dir"] for s in real)
    print(f"gerado: {len(gen)} sinais | datatypes={dict(dt_gen)} | dir={dict(dir_gen)}")
    print(f"real:   {len(real)} sinais | datatypes={dict(dt_real)} | dir={dict(dir_real)}")

    # falsos double/multi: 2º endereço do gerado existe como sinal próprio no real
    por_addr = defaultdict(list)
    for s in real:
        if s["inc"]:
            por_addr[s["inc"].split(";")[0].strip()].append(s["name"])
    falsos = []
    for s in gen:
        partes = [p.strip() for p in s["inc"].split(";") if p.strip()]
        if s["dt"] in ("DoubleBit", "MultiCoord") and len(partes) == 2:
            a, b = partes
            real_a_par = [n for n in por_addr.get(a, [])
                          if any(r["name"] == n and r["dt"] in ("DoubleBit", "MultiCoord")
                                 for r in real)]
            if por_addr.get(b) and not real_a_par:
                falsos.append((s["name"], s["inc"], por_addr[a], por_addr[b]))
    print(f"\nfusões falsas (real tem 2 sinais separados): {len(falsos)}")
    for nome, inc, ra, rb in falsos[:20]:
        print(f"  {nome} inc={inc} | real@a={ra} | real@b={rb}")

    mc = dt_gen.get("MultiCoord", 0)
    print(f"\nMultiCoord emitido no gerado: {mc} (real: {dt_real.get('MultiCoord', 0)})")

    writes = [s["name"] for s in gen if s["dir"] == "Write"]
    # Write legítimo = só CDC (comutador de tap raise/lower, sem input).
    writes_ilegit = [n for n in writes if n.rsplit("_", 1)[-1].upper() != "CDC"]
    print(f"\nWrite no gerado: {len(writes)} (não-CDC: {len(writes_ilegit)})")
    for n in writes_ilegit[:20]:
        print(f"  {n}")

    tem_sgft = any(n.endswith("_SGFT") for n in (s["name"] for s in gen))
    print(f"\nSGFT presente no gerado: {tem_sgft}")

    # Diagnóstico informativo (fora do veredito) — ver docstring.
    dups = [n for n, c in Counter(s["name"] for s in gen).items() if c > 1]
    print(f"\n[diagnóstico] Signal Names duplicados: {len(dups)} "
          f"(causa fora de escopo SP-E: qualificador spec D + prefixo P_/A_)")
    for n in dups[:20]:
        print(f"  {n}")

    ok = not falsos and tem_sgft and not writes_ilegit and mc > 0
    print(f"\n{'PASS' if ok else 'FAIL'} (metas estruturais SP-E §4: "
          f"falsos={len(falsos)}, SGFT={tem_sgft}, Write_ilegit={len(writes_ilegit)}, MultiCoord={mc})")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
