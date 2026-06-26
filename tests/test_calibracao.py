import math

import numpy as np

from tdt.contracts import Candidato
from tdt.scoring.calibracao import (
    aplicar_calibrador_confianca,
    calibrar,
    calibrar_candidatos,
    treinar_calibrador_confianca,
)


def test_minmax_espalha_para_0_1():
    out = calibrar([0.80, 0.85, 0.90], "minmax", None)
    assert out[0] == 0.0
    assert out[2] == 1.0
    assert abs(out[1] - 0.5) < 1e-6


def test_minmax_lista_constante_nao_divide_por_zero():
    out = calibrar([0.8, 0.8, 0.8], "minmax", None)
    assert all(v == 0.0 for v in out)


def test_minmax_lista_vazia():
    assert calibrar([], "minmax", None) == []


def test_minmax_um_elemento():
    assert calibrar([0.87], "minmax", None) == [0.0]


def test_temperature_aumenta_spread():
    # e5 comprimido em ~0.8-0.9; temperature scaling alarga a separação relativa
    bruto = [0.80, 0.85, 0.90]
    spread_bruto = max(bruto) - min(bruto)
    out = calibrar(bruto, "temperature", {"T": 0.1})
    spread_out = max(out) - min(out)
    assert spread_out > spread_bruto
    # mantém ordem
    assert out == sorted(out)


def test_temperature_default_params():
    # params None -> usa T default; não explode
    out = calibrar([0.80, 0.85, 0.90], "temperature", None)
    assert len(out) == 3
    assert out == sorted(out)


def test_e5_comprimido_passa_a_ter_gap_apos_minmax():
    # critério da spec: e5 sozinho decide 0% porque scores comprimidos -> gap~0.
    # após calibrar, o top-1 ganha separação suficiente para o gap virar > 0.
    e5 = [0.91, 0.89, 0.88]
    gap_bruto = e5[0] - e5[1]
    cal = calibrar(e5, "minmax", None)
    gap_cal = cal[0] - cal[1]
    assert gap_cal > gap_bruto
    assert gap_cal > 0.0


def test_metodo_desconhecido_levanta():
    try:
        calibrar([0.1, 0.2], "inexistente", None)
        assert False, "deveria levantar"
    except ValueError:
        pass


# --- E1: Calibradores treinados ---

def test_isotonic_treinado_mapeia_monotonico():
    # params simulando IsotonicRegression fitado (1 score baixo ~0.2, 1 alto ~0.9)
    params = {"thresholds_": [0.0, 0.5, 1.0], "y_": [0.05, 0.4, 0.95]}
    out = calibrar([0.1, 0.5, 0.9], "isotonic", params)
    assert len(out) == 3
    assert all(0.0 <= v <= 1.0 for v in out)
    assert out == sorted(out)  # monotônico


def test_isotonic_clips_fora_da_faixa():
    params = {"thresholds_": [0.0, 0.5, 1.0], "y_": [0.05, 0.4, 0.95]}
    out = calibrar([-0.5, 2.0], "isotonic", params)
    assert abs(out[0] - 0.05) < 1e-6  # clipped left
    assert abs(out[1] - 0.95) < 1e-6  # clipped right


def test_isotonic_sem_params_retorna_original():
    out = calibrar([0.8, 0.9], "isotonic", None)
    assert out == [0.8, 0.9]


def test_platt_mapeia_para_0_1():
    # coef=5, intercept=-3 => score 0.0 -> 0.047, score 1.0 -> 0.88
    params = {"coef_": 5.0, "intercept_": -3.0}
    out = calibrar([0.0, 0.5, 1.0], "platt", params)
    assert len(out) == 3
    assert all(0.0 <= v <= 1.0 for v in out)
    assert out == sorted(out)
    assert out[0] < 0.1  # score 0 -> baixo
    assert out[2] > 0.8  # score 1 -> alto


def test_platt_sem_params_retorna_original():
    out = calibrar([0.8, 0.9], "platt", None)
    assert out == [0.8, 0.9]


def test_platt_lista_vazia():
    assert calibrar([], "platt", {}) == []


# --- calibrar_candidatos ---

def test_calibrar_candidatos_aplica_nos_scores():
    cands = [Candidato("DJ", 0.5, "tfidf"), Candidato("SEC", 0.9, "tfidf")]
    out = calibrar_candidatos(cands, "minmax", None)
    assert len(out) == 2
    assert out[0].sigla == "DJ"
    assert out[0].score == 0.0
    assert out[1].sigla == "SEC"
    assert out[1].score == 1.0
    assert out[1].fonte == "tfidf"


def test_calibrar_candidatos_metodo_none_retorna_original():
    cands = [Candidato("DJ", 0.5, "tfidf")]
    out = calibrar_candidatos(cands, "", None)
    assert out is cands


def test_calibrar_candidatos_vazia():
    assert calibrar_candidatos([], "minmax", None) == []


# --- E4: Calibrador de confiança (pós-mescla) --------------------------------

def test_treinar_platt_produz_params():
    scores = [0.1, 0.2, 0.8, 0.9]
    acertos = [False, False, True, True]
    params = treinar_calibrador_confianca(scores, acertos, "platt")
    assert params["metodo"] == "platt"
    assert "coef_" in params["params"]
    assert "intercept_" in params["params"]
    assert params["params"]["coef_"] > 0  # scores maiores -> mais acerto


def test_treinar_isotonic_produz_params():
    scores = [0.1, 0.2, 0.8, 0.9]
    acertos = [False, False, True, True]
    params = treinar_calibrador_confianca(scores, acertos, "isotonic")
    assert params["metodo"] == "isotonic"
    assert "thresholds_" in params["params"]
    assert "y_" in params["params"]


def test_aplicar_platt_mapeia_para_0_1():
    params = {"metodo": "platt", "params": {"coef_": 5.0, "intercept_": -3.0}}
    assert aplicar_calibrador_confianca(0.0, params) < 0.1
    assert aplicar_calibrador_confianca(1.0, params) > 0.8


def test_aplicar_platt_monotonico():
    params = {"metodo": "platt", "params": {"coef_": 4.0, "intercept_": -2.0}}
    assert aplicar_calibrador_confianca(0.3, params) < aplicar_calibrador_confianca(0.6, params)


def test_aplicar_isotonic_mapeia_para_0_1():
    params = {"metodo": "isotonic", "params": {"thresholds_": [0.0, 0.5, 1.0], "y_": [0.05, 0.4, 0.95]}}
    assert aplicar_calibrador_confianca(-0.5, params) == 0.05  # clipped left
    assert 0.3 < aplicar_calibrador_confianca(0.5, params) < 0.5
    assert aplicar_calibrador_confianca(2.0, params) == 0.95  # clipped right


def test_aplicar_metodo_desconhecido_retorna_original():
    params = {"metodo": "unknown", "params": {}}
    assert aplicar_calibrador_confianca(0.7, params) == 0.7


def test_platt_treinado_em_dados_perfeitos():
    # Dados perfeitamente separáveis: score < 0.5 -> errado, > 0.5 -> certo
    scores = [0.1, 0.2, 0.3, 0.4, 0.6, 0.7, 0.8, 0.9]
    acertos = [False, False, False, False, True, True, True, True]
    params = treinar_calibrador_confianca(scores, acertos, "platt")
    assert params["params"]["coef_"] > 0
    # Score 0.5 deve ter ~50% de chance
    p50 = aplicar_calibrador_confianca(0.5, params)
    assert 0.3 < p50 < 0.7
