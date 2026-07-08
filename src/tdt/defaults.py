"""Caminhos default do projeto (template, lista padrão, output) — usados
como diretório inicial dos diálogos de arquivo na UI, antes da primeira
seleção manual do usuário."""

from __future__ import annotations

from pathlib import Path

_DOCS = Path(__file__).resolve().parents[2] / "docs"

DEFAULT_TEMPLATE = str(_DOCS / "dnp3_template.xlsx")
DEFAULT_LISTA = str(_DOCS / "Pontos Padrao ADMS_v2.xlsx")
DEFAULT_OUTPUT = str(Path(__file__).resolve().parents[2] / "output")

# Fonte FIXA do Signal Alias na TDT gerada (spec SP-METADADOS §1): descrições
# originais da v1, independente da lista padrão carregada (v6+ tem descrições
# enriquecidas p/ matching que não devem vazar pro ALIAS).
DEFAULT_LISTA_ALIAS = str(_DOCS / "Pontos Padrao ADMS_v1.xlsx")
