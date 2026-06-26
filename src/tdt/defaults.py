"""Caminhos default do projeto (template, lista padrão, output) — usados
como diretório inicial dos diálogos de arquivo na UI, antes da primeira
seleção manual do usuário."""

from __future__ import annotations

from pathlib import Path

_DOCS = Path(__file__).resolve().parents[2] / "docs"

DEFAULT_TEMPLATE = str(_DOCS / "dnp3_template.xlsx")
DEFAULT_LISTA = str(_DOCS / "Pontos Padrao ADMS_v4.xlsx")
DEFAULT_OUTPUT = str(Path(__file__).resolve().parents[2] / "output")
