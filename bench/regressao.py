"""Gate de regressão: gera o nosso TDT do input real, compara com o TDT real
por endereço (gate_tdt_real) e checa os casos travados. Exit != 0 se algum
caso travado falha.

⚠️ Estado inicial: os casos em `casos_travados.csv` documentam bugs
CONHECIDOS AINDA NÃO CORRIGIDOS — por design, começam FALHANDO (GATE FALHOU
é esperado até as fases de fix corrigirem cada um). O sinal que importa é
"nenhum caso que passava passou a falhar" (regressão), não "tudo verde".
Ao corrigir um caso, ele deve virar PASS; se um caso que já era PASS virar
FAIL, isso sim é regressão real.

Uso: PYTHONPATH=src python -m bench.regressao
"""
from __future__ import annotations

import csv
import sys
from dataclasses import dataclass

from bench.gate_tdt_real import carregar_siglas_por_endereco, comparar


@dataclass(frozen=True)
class Caso:
    subestacao: str
    endereco: int
    sigla_esperada: str
    origem: str
    nota: str


def carregar_casos(caminho: str) -> list[Caso]:
    casos: list[Caso] = []
    with open(caminho, encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            casos.append(Caso(
                row["subestacao"], int(row["endereco"]),
                row["sigla_esperada"], row["origem"], row["nota"],
            ))
    return casos


def checar_casos(nosso_tdt: str, casos: list[Caso]) -> list[tuple[Caso, str, bool]]:
    por_addr = carregar_siglas_por_endereco(nosso_tdt)
    out: list[tuple[Caso, str, bool]] = []
    for c in casos:
        obtida = por_addr.get(c.endereco, (None, ""))[1]
        out.append((c, obtida, obtida.upper() == c.sigla_esperada.upper()))
    return out


# Pares (input real, TDT real) — a fonte de verdade da validação de fechamento.
_PARES = [
    ("GTD", "docs/input_nao_homogeneo_1_GTD.xlsx",
     "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx"),
]
_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA = "docs/Pontos Padrao ADMS_v2.xlsx"


def _gerar_nosso_tdt(input_path: str, saida: str, subestacao: str) -> None:
    """Roda o pipeline real e salva o TDT gerado em `saida`."""
    import warnings, logging
    warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
    from tdt.config import Config
    from tdt.dados.encoder import criar_encoder
    from tdt import pipeline
    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)
    _res, wb = pipeline.executar(
        input_path, _TEMPLATE, _LISTA, config=cfg, encoder=enc, subestacao=subestacao
    )
    wb.save(saida)


def main() -> int:
    casos = carregar_casos("bench/casos_travados.csv")
    falhas = 0
    for se, inp, real in _PARES:
        saida = f"bench/_tdt_gerado_{se}.xlsx"
        _gerar_nosso_tdt(inp, saida, se)
        r = comparar(saida, real)
        print(f"[{se}] comum={r.comum} iguais={r.iguais} pct={r.pct:.1f}%")
        for c, obtida, ok in checar_casos(saida, [x for x in casos if x.subestacao == se]):
            print(f"   {'PASS' if ok else 'FAIL'} addr={c.endereco} "
                  f"esperado={c.sigla_esperada} obtido={obtida or '—'} ({c.nota})")
            if not ok:
                falhas += 1
    print(f"\n{'GATE OK' if falhas == 0 else f'GATE FALHOU: {falhas} caso(s)'}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
