"""Nomeação dos arquivos gerados: <prefixo>_<SUB>_<YYYYMMDD>[_vN].ext.

Sem subestação o segmento é omitido — a geração nunca quebra por falta de sigla.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path


def nome_saida(prefixo: str, subestacao: str | None,
               pasta: str | Path, ext: str = ".xlsx") -> Path:
    base = "_".join(p for p in (prefixo, subestacao, date.today().strftime("%Y%m%d")) if p)
    caminho = Path(pasta) / f"{base}{ext}"
    v = 2
    while caminho.exists():
        caminho = Path(pasta) / f"{base}_v{v}{ext}"
        v += 1
    return caminho
