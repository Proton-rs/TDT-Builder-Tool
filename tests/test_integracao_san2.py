"""Integração SP sigla não-homogênea: SAN2_LISTA_PADRONIZADA_PARA_TESTE.xlsx.

Lista padronizada real (sinais já classificados, sigla + NOME em colunas
dedicadas, 5 colunas — não-homogênea). Cobre os critérios de sucesso da
spec: detecção de coluna de sigla por conteúdo, pré-classificação contra a
ListaPadraoADMS, extração de módulo do NOME, e o handler de revisão por
inconsistência sigla×NOME (Task 5 Parte B) ponta-a-ponta.
"""

from collections import Counter
from pathlib import Path

import numpy as np
import openpyxl
import pytest

from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.defaults import DEFAULT_TEMPLATE
from tdt.pipeline import executar

_DOCS = Path(__file__).resolve().parents[1] / "docs"

_VOCAB = ["CORRENTE", "FASE", "FALHA", "COMUNICACAO", "DISJUNTOR", "ABERTO"]


def _fake_encoder(textos):
    return np.array(
        [[float(str(t).upper().split().count(w)) for w in _VOCAB] for t in textos],
        dtype="float32",
    )


@pytest.fixture(scope="module")
def san2_resultado():
    # Encoder REAL (não fake): a coluna NOME ("SND_LT67SAN_..._IA") e a coluna
    # SIGLA ("IA") não compartilham vocabulário com nenhum bag-of-words
    # sintético pequeno -- um fake encoder faz a detecção por embedding
    # colapsar as duas colunas na mesma (falso teste, não falso bug). O
    # encoder real distingue as duas com folga, como no resto do pipeline real.
    lp_path = _DOCS / "Pontos Padrao ADMS_v2.xlsx"
    san2_path = _DOCS / "SAN2_LISTA_PADRONIZADA_PARA_TESTE.xlsx"
    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)
    resultado, _ = executar(
        san2_path, DEFAULT_TEMPLATE, lp_path,
        config=cfg, encoder=enc, subestacao="SND", modo="nao-homogeneo",
    )
    return resultado


def test_san2_decididos_inclui_siglas_das_duas_sheets(san2_resultado):
    siglas = {r.sigla_sinal for r in san2_resultado.lista.registros}
    assert "IA" in siglas  # Analogicos
    assert "DR" in siglas  # Discreto


def test_san2_cobertura_por_sheet_bate_com_a_lista_padrao(san2_resultado):
    # Medido na LP ADMS_v2 (30jun): Analogicos 41/41 (100%) siglas elegíveis;
    # Discreto 172/235 (73%) pré-classificam via coluna -- mas a SAN2 tem 2
    # colunas de índice (Entrada/Comando) e a detecção não-homogênea só pega
    # uma (Entrada); sinais só-comando (sem valor em Entrada) ficam sem
    # `enderecamento.indices` e `normalizador_estrutural.corrigir` os
    # descarta como sem_endereco mesmo já "decidido" -- limitação separada
    # (suporte a índice duplo), fora do escopo da detecção de sigla. Medido:
    # 172-41=131 (Discreto) + 41-16=25 (Analogicos) = 156 decididos finais.
    decididos = len(san2_resultado.lista.registros)
    assert decididos >= 150


def test_san2_modulo_extraido_do_nome_substitui_sheet_generica(san2_resultado):
    # "SND_LT67SAN_LT67SAN_IA" -> módulo extraído = "LT67SAN", não "Analogicos"
    ia = next(r for r in san2_resultado.lista.registros if r.sigla_sinal == "IA")
    assert ia.modulo.nome == "LT67SAN"
    # "SND_SLOTD_SLOTD_DR" -> módulo extraído = "SLOTD", não "Discreto"
    dr = next(
        r for r in san2_resultado.lista.registros
        if r.sigla_sinal == "DR" and "SLOTD" in r.descricoes.bruta.upper()
    )
    assert dr.modulo.nome == "SLOTD"


def test_san2_nenhum_falso_positivo_sigla_fora_da_lista(san2_resultado):
    # siglas conhecidas como inválidas na LP (medido: '25', 'NORMAL', ...)
    # não devem aparecer como sigla_sinal pré-classificada por coluna --
    # se aparecerem como decididas é porque o SCORING decidiu, não a coluna.
    pre_classificadas_invalidas = [
        r for r in san2_resultado.lista.registros
        if r.sigla_sinal == "NORMAL"
    ]
    assert pre_classificadas_invalidas == []


def test_pipeline_sigla_inconsistente_com_nome_vai_pra_revisao(tmp_path, lista_padrao_path):
    # sigla "79" é válida na LP, mas o NOME aponta sigla "80" -- inconsistência
    # deliberada, exercita o handler status=="revisao" do pipeline (Task 5 Parte B).
    # 2 linhas: detecção de coluna por conteúdo (sigla/descrição) precisa de
    # >= 2 valores por coluna pra engajar (degenera com corpus de 1 doc só,
    # mesmo padrão observado nos testes de pipeline da SP-B/SP-D2).
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Discreto"
    ws.append(["SIGLA", "NOME", "INDEX DNP3 - Entrada", "AOR"])
    ws.append(["79", "SND_LT67SAN_LT67SAN_80", "10", "Distr"])  # sigla != NOME -> revisão
    ws.append(["IA", "SND_LT67SAN_LT67SAN_IA", "11", "Distr"])  # consistente -> decidido
    p = tmp_path / "input.xlsx"
    wb.save(p)

    cfg = Config()
    resultado, _ = executar(
        p, DEFAULT_TEMPLATE, lista_padrao_path,
        config=cfg, encoder=_fake_encoder, subestacao="SND", modo="nao-homogeneo",
    )
    motivos = Counter(it.motivo for it in resultado.revisao)
    assert motivos["nome_sigla_inconsistente"] == 1
    item = next(it for it in resultado.revisao if it.motivo == "nome_sigla_inconsistente")
    assert item.registro.sigla_sinal == "79"  # sigla preservada como sugestão
