"""Integração: gênero sheet-por-tipo (SMF) — módulo por coluna, cross-sheet.

Determinístico, sem modelo ST: valida, contra os dados reais do arquivo, o
que _col_modulo/_header_por_densidade/_ncols detectam e o que
canonizar_modulo resolve -- não invoca estruturar/aplicar_identidade. Guarda
contra regressão da detecção e da reconciliação cross-sheet.
"""
from pathlib import Path

import openpyxl
import pytest

from tdt.analise.analise_colunas import _col_modulo, _header_por_densidade, _ncols
from tdt.config import Config
from tdt.identidade_modulo import canonizar_modulo

_ARQ = Path(__file__).resolve().parents[1] / "docs" / "input_não_homogeneo_5_SMF.xlsx"


def _rows(sheet: str) -> list[tuple]:
    wb = openpyxl.load_workbook(_ARQ, data_only=True, read_only=True)
    return [tuple(r) for r in wb[sheet].iter_rows(values_only=True)]


@pytest.mark.skipif(not _ARQ.exists(), reason="arquivo SMF não disponível")
@pytest.mark.parametrize("sheet", ["ESTADOS", "MEDIDAS", "COMANDOS"])
def test_col_modulo_e_a_coluna_A_no_smf(sheet):
    rows = _rows(sheet)
    inicio = _header_por_densidade(rows) + 1
    ncols = _ncols(rows)
    assert _col_modulo(rows, inicio, ncols, Config(), reservadas=set()) == 0


@pytest.mark.skipif(not _ARQ.exists(), reason="arquivo SMF não disponível")
def test_reconciliacao_cross_sheet_al11():
    cfg = Config()
    # 'AL 11 - 13.8kV' (ESTADOS) e 'AL11 - 13.8kV' (MEDIDAS) -> mesmo canônico
    a = canonizar_modulo("AL 11 - 13.8kV", cfg, explicito=True).nome
    b = canonizar_modulo("AL11 - 13.8kV", cfg, explicito=True).nome
    assert a == b == "AL11"
