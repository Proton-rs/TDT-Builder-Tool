"""Testes da tela inicial."""

import pytest

from tdt.ui.tela_inicial import pode_executar


def test_pode_executar_exige_sigla():
    """Execução deve ser bloqueada sem sigla válida da SE."""
    assert not pode_executar(sigla_se="", input_ok=True)
    assert not pode_executar(sigla_se="   ", input_ok=True)
    assert pode_executar(sigla_se="SND", input_ok=True)


def test_pode_executar_com_input_invalido():
    """Execução deve ser bloqueada com input_ok=False."""
    assert not pode_executar(sigla_se="SND", input_ok=False)
    assert not pode_executar(sigla_se="", input_ok=False)


def test_pode_executar_valido():
    """Execução deve ser permitida com sigla válida e input_ok=True."""
    assert pode_executar(sigla_se="ABC", input_ok=True)
    assert pode_executar(sigla_se="XYZ123", input_ok=True)
