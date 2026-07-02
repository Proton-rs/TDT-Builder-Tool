"""F_especificidade: variante específica vence o prefixo genérico por
casamento de tokens discriminadores, sem decidir quando não há evidência."""

from __future__ import annotations

from dataclasses import dataclass

from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.filtro_preciso import _DISC_CACHE, filtrar_especificidade
from tdt.normalizacao.normalizador import canonizar, normalizar_estagio


@dataclass(frozen=True)
class _SP:
    sigla: str
    descricao: str


class _LP:
    """Lista padrão mínima (só o que o índice de discriminadores lê)."""
    def __init__(self, sinais):
        self.discretos = sinais
        self.analogicos = []


_SINAIS = [
    _SP("79", "79 - FUNCAO RELIGAMENTO"),
    _SP("79LO", "79 - RELIGAMENTO BLOQUEADO"),
    _SP("79RE", "79 - RELIGAMENTO PRONTO"),
    _SP("79OK", "79 - RELIGAMENTO COM SUCESSO"),
    _SP("81", "81 - FUNCAO SUB/SOB FREQUENCIA"),
    _SP("81SU", "81 - TRIP SUB FREQUENCIA"),
    _SP("81E1", "81 - TRIP SUB/SOBRE FREQUENCIA E1"),
    _SP("81E2", "81 - TRIP SUB/SOBRE FREQUENCIA E2"),
]


def _rec(bruta: str, cfg: Config) -> SignalRecord:
    return SignalRecord(
        id="x", modulo=Modulo(None, "M"),
        tipo_sinal=TipoSinal("Discrete", "DoubleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(bruta, canonizar(bruta, cfg)),
    )


def _cand(*siglas):
    return [Candidato(s, 0.5, "x") for s in siglas]


def _siglas(out):
    return [c.sigla for c in out]


def _lp_e_cfg():
    _DISC_CACHE.clear()  # evita cache cruzado entre testes (id reciclado)
    return _LP(_SINAIS), Config()


def test_especifico_vence_generico_por_discriminador():
    lp, cfg = _lp_e_cfg()
    out = filtrar_especificidade(_rec("Religamento Bloqueado", cfg),
                                 _cand("79", "79LO", "79RE", "79OK"), lp, cfg)
    assert _siglas(out) == ["79LO"]


def test_estagio_normalizado_seleciona_variante():
    lp, cfg = _lp_e_cfg()
    out = filtrar_especificidade(_rec("Protecao 81 Sub Frequencia Estagio 1", cfg),
                                 _cand("81", "81SU", "81E1", "81E2"), lp, cfg)
    assert _siglas(out) == ["81E1"]


def test_generico_vence_quando_seu_discriminador_casa():
    # "Funcao" é o discriminador do genérico; nenhum específico o tem -> 79 vence.
    lp, cfg = _lp_e_cfg()
    out = filtrar_especificidade(_rec("Funcao 79 Religamento", cfg),
                                 _cand("79", "79LO", "79OK"), lp, cfg)
    assert _siglas(out) == ["79"]


def test_sem_evidencia_mantem_grupo():
    # Só o token compartilhado (RELIGAMENTO) casa -> empate, não decide.
    lp, cfg = _lp_e_cfg()
    out = filtrar_especificidade(_rec("Religamento", cfg),
                                 _cand("79", "79LO", "79OK"), lp, cfg)
    assert set(_siglas(out)) == {"79", "79LO", "79OK"}


def test_nunca_esvazia_e_ignora_fora_da_familia():
    lp, cfg = _lp_e_cfg()
    cands = _cand("79LO", "DJF1")  # DJF1 não tem nº líder -> intocado
    out = filtrar_especificidade(_rec("Religamento Bloqueado", cfg), cands, lp, cfg)
    assert "DJF1" in _siglas(out) and "79LO" in _siglas(out)


def test_fase_filtro_duro_usa_eletrico_fase():
    # N0 tira a letra de fase do texto; o filtro tem de ler eletrico.fase,
    # senão IA/IB/IC ficam indistinguíveis (texto vira "CORRENTE FASE").
    from tdt.contracts import Eletrico
    from tdt.filtro_preciso import filtrar
    cfg = Config()
    rec = SignalRecord(
        id="x", modulo=Modulo(None, "M"),
        tipo_sinal=TipoSinal("Analog", "DoubleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("Corrente Fase B", "CORRENTE FASE"),
        eletrico=Eletrico(fase="B"),
    )
    out = filtrar(rec, _cand("IA", "IB", "IC", "IOUT"), cfg)
    siglas = _siglas(out)
    assert "IB" in siglas and "IOUT" in siglas  # fase B e sem-fase mantidos
    assert "IA" not in siglas and "IC" not in siglas  # fases divergentes removidas


def test_normalizar_estagio():
    assert normalizar_estagio("SUB FREQUENCIA ESTAGIO 1") == "SUB FREQUENCIA E1"
    assert normalizar_estagio("ESTAGIO2 ATUADO") == "E2 ATUADO"
    assert normalizar_estagio("SEM ESTAGIO AQUI") == "SEM ESTAGIO AQUI"
