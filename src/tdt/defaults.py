"""Caminhos default do projeto (template, lista padrão, output) — usados
como diretório inicial dos diálogos de arquivo na UI, antes da primeira
seleção manual do usuário."""

from __future__ import annotations

from pathlib import Path

_DOCS = Path(__file__).resolve().parents[2] / "docs"

DEFAULT_TEMPLATE = str(_DOCS / "dnp3_template.xlsx")
DEFAULT_LISTA = str(_DOCS / "Pontos Padrao ADMS_v8.xlsx")
DEFAULT_OUTPUT = str(Path(__file__).resolve().parents[2] / "output")

# Fonte FIXA do Signal Alias na TDT gerada (spec SP-METADADOS §1): descrições
# originais da v1, independente da lista padrão carregada (v6+ tem descrições
# enriquecidas p/ matching que não devem vazar pro ALIAS).
DEFAULT_LISTA_ALIAS = str(_DOCS / "Pontos Padrao ADMS_v1.xlsx")

# Complemento do flag dm_prot (spec 2026-07-20 §B1): siglas da lista padrão
# com SIGNAL TYPE != RelayTrip que a fullbase mapeia >=90% em dispositivo
# PROT (linhas limpas, n>=20). Saída de scripts/derivar_complemento_dm_prot.py
# — regenerar se a lista padrão ou a fullbase mudarem. RelayTrip da lista
# padrão continua mandando (instrução do usuário: não mexer no documentado).
# 21: 53/55 PROT (96%)
# 25IE: 61/63 PROT (97%)
# 27: 91/94 PROT (97%)
# 27E1: 52/52 PROT (100%)
# 27E2: 39/39 PROT (100%)
# 51N: 717/717 PROT (100%)
# 59: 139/139 PROT (100%)
# 67: 107/107 PROT (100%)
# 81: 429/436 PROT (98%)
# 87: 115/115 PROT (100%)
# SGF: 361/361 PROT (100%)
# 2649: 107/140 PROT (76%, abaixo do critério) — decisão do usuário 20/07:
# dado limpo, mapeia PROT; incluído à mão.
COMPLEMENTO_DM_PROT = frozenset({
    "21", "25IE", "27", "27E1", "27E2", "51N", "59", "67", "81", "87", "SGF",
    "2649",  # decisao do usuario 20/07
})
