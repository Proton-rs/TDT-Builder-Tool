"""Reprocessa LISTA 1 - GTD do zero (pos-SP-G) e salva TDT.xlsx fresco.

Uso: PYTHONPATH=src python bench/reprocessar_lista1.py

Gera output/LISTA 1 - GTD/TDT.xlsx a partir de
docs/input_nao_homogeneo_1_GTA.xlsx, usando o pipeline real
(tdt.pipeline.executar), para servir de base a bench.gate_tdt_real.comparar
contra o TDT real (docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx).

Nao reusa nenhum TDT.xlsx pre-existente copiado no worktree.
"""
from __future__ import annotations

import warnings
import logging

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)

from pathlib import Path

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar

_INPUT = "docs/input_nao_homogeneo_1_GTA.xlsx"
_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA_PADRAO = "docs/Pontos Padrao ADMS_v2.xlsx"
_OUT_DIR = Path("output/LISTA 1 - GTD")


def main() -> None:
    cfg = Config()
    aud = Auditoria()
    resultado, wb_out = executar(
        _INPUT, _TEMPLATE, _LISTA_PADRAO,
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding), auditoria=aud,
        subestacao="GTD",
    )
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _OUT_DIR / "TDT.xlsx"
    wb_out.save(str(out_path))
    print(f"decididos={len(resultado.lista.registros)} revisao={len(resultado.revisao)}")
    print(f"salvo em: {out_path}")


if __name__ == "__main__":
    main()
