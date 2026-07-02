"""Pós-decisão: sigla base de família (79) não engole qualificador presente
no texto (79OK/79LO/79RE/... quando o texto tem a palavra distintiva)."""

from __future__ import annotations

from dataclasses import dataclass

from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.especificidade_qualificador import preferir_irmao_qualificado
from tdt.normalizacao.normalizador import canonizar


@dataclass(frozen=True)
class _SP:
    sigla: str
    descricao: str


class _LP:
    """Lista padrão mínima (só o que preferir_irmao_qualificado lê)."""
    def __init__(self, sinais):
        self.discretos = sinais
        self.analogicos = []


_SINAIS = [
    _SP("79", "79 - FUNCAO RELIGAMENTO"),
    _SP("79_1", "79 - PARTIDA RELIGAMENTO"),
    _SP("79LO", "79 - RELIGAMENTO BLOQUEADO"),
    _SP("79OK", "79 - RELIGAMENTO COM SUCESSO"),
    _SP("79_EXC", "79 - EXCLUIR RELIGAMENTO"),
    _SP("79_INC", "79 - INCLUIR RELIGAMENTO"),
    _SP("79RE", "79 - RELIGAMENTO PRONTO"),
    _SP("79TF", "79 - RELIGAMENTO TRANSFERIDO"),
]


def _config() -> Config:
    return Config()


def _lp() -> _LP:
    return _LP(_SINAIS)


def _rec_decidido(bruta: str, sigla: str, cfg: Config) -> SignalRecord:
    return SignalRecord(
        id="x",
        modulo=Modulo(None, "M"),
        tipo_sinal=TipoSinal("Discrete", "DoubleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(bruta, canonizar(bruta, cfg)),
        sigla_sinal=sigla,
        candidatos=(Candidato(sigla, 0.9, "mesclado"),),
        status="decidido",
    )


def test_bem_sucedido_prefere_79ok():
    cfg = _config()
    lp = _lp()
    rec = _rec_decidido("Religamento (79) - Bem Sucedido", sigla="79", cfg=cfg)
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79OK"
    assert out.status == "decidido"


def test_sem_qualificador_mantem_base():
    cfg = _config()
    lp = _lp()
    rec = _rec_decidido("Religamento (79)", sigla="79", cfg=cfg)
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79"
    assert out.status == "decidido"


def test_dois_irmaos_casando_vai_revisao():
    cfg = _config()
    lp = _lp()
    # "Bloqueado" -> 79LO, "Pronto" -> 79RE: dois irmãos distintos casam -> ambíguo
    rec = _rec_decidido("Religamento (79) Bloqueado Pronto", sigla="79", cfg=cfg)
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.status == "revisao"
    assert out.justificativa is not None and "qualificador" in out.justificativa.lower()


def test_base_ja_especifica_nao_e_relitigada():
    # Caso real (LISTA 1 GTD): decidido já é 25VT (específico, não a raiz "25").
    # "SINCRONISMO"/"FALHA" são vocabulário comum da família inteira -- não
    # devem disparar re-arbitragem contra o irmão 25ER ("FALHA SINCRONISMO").
    cfg = _config()
    lp = _LP([
        _SP("25", "25 - FUNCAO SINCRONISMO"),
        _SP("25ER", "25 - FALHA SINCRONISMO"),
        _SP("25VT", "25 - TRIP DIFERENCA TENSAO"),
        _SP("25AT", "25 - TRIP DIFERENCA DE ANGULO"),
    ])
    rec = _rec_decidido(
        "Sincronismo (25) - Falha por Diferença de Tensão", sigla="25VT", cfg=cfg
    )
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "25VT"
    assert out.status == "decidido"


def test_raiz_generica_com_vocabulario_comum_ainda_prefere_irmao_unico():
    # Se o decidido É a raiz genérica ("25") e só um irmão tem token
    # exclusivo presente no texto, a correção ainda deve valer.
    cfg = _config()
    lp = _LP([
        _SP("25", "25 - FUNCAO SINCRONISMO"),
        _SP("25ER", "25 - FALHA SINCRONISMO"),
        _SP("25VT", "25 - TRIP DIFERENCA TENSAO"),
        _SP("25AT", "25 - TRIP DIFERENCA DE ANGULO"),
    ])
    rec = _rec_decidido(
        "Sincronismo (25) - Diferença de Tensão", sigla="25", cfg=cfg
    )
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "25VT"
