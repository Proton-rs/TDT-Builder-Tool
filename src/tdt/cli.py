"""Ponto de entrada CLI do SP1.

    tdt gerar INPUT.xlsx --output OUT.xlsx [--template ...] [--lista-padrao ...]
        [--modo auto|homogeneo|nao-homogeneo] [--subestacao X]

Salva OUT.xlsx, OUT.revisao.json, OUT.log.txt e OUT.auditoria.json.
"""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict
from pathlib import Path

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.defaults import DEFAULT_LISTA
from tdt.pipeline import executar


def _salvar_revisao(resultado, destino: Path) -> None:
    itens = [
        {
            "id": it.registro.id,
            "motivo": it.motivo,
            "descricao": it.registro.descricoes.bruta,
            "candidatos": [{"sigla": c.sigla, "score": round(c.score, 3)} for c in it.candidatos_sugeridos],
        }
        for it in resultado.revisao
    ]
    destino.write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    p = argparse.ArgumentParser(prog="tdt")
    sub = p.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gerar", help="gera um TDT a partir de uma planilha")
    g.add_argument("input")
    g.add_argument("--output", required=True)
    g.add_argument("--template", default="docs/dnp3_template.xlsx")
    g.add_argument("--lista-padrao", default=DEFAULT_LISTA)
    g.add_argument("--modo", default="auto", choices=["auto", "homogeneo", "nao-homogeneo"])
    g.add_argument("--subestacao", default=None)
    args = p.parse_args(argv)

    cfg = Config()
    aud = Auditoria()
    resultado, wb = executar(
        args.input, args.template, args.lista_padrao,
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding),
        subestacao=args.subestacao, modo=args.modo, auditoria=aud,
    )

    out = Path(args.output)
    wb.save(out)
    _salvar_revisao(resultado, out.with_suffix(".revisao.json"))
    aud.salvar_log(out.with_suffix(".log.txt"))
    aud.salvar_json(out.with_suffix(".auditoria.json"))
    print(f"TDT: {out} | decididos={len(resultado.lista.registros)} revisão={len(resultado.revisao)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
