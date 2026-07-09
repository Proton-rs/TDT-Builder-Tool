"""Projeto TDT v2 — SP1 backbone determinístico (DNP3)."""

# Aplica o shim de compat do openpyxl (PatternFill extLst) antes de qualquer
# load_workbook — .xlsx reais de concessionária derrubam a leitura sem isso.
from tdt.dados import _openpyxl_compat as _openpyxl_compat  # noqa: F401,E402
