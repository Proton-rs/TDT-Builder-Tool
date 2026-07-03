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
from tdt.semantica_estados import filtrar_por_estado


@dataclass(frozen=True)
class _SP:
    sigla: str
    descricao: str
    mm: str | None = None


class _LP:
    """Lista padrão mínima (só o que preferir_irmao_qualificado lê)."""
    def __init__(self, sinais):
        self.discretos = sinais
        self.analogicos = []

    def por_sigla(self, sigla):
        alvo = sigla.strip().upper()
        for s in (*self.discretos, *self.analogicos):
            if s.sigla.upper() == alvo:
                return s
        return None


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


def test_promocao_atualiza_candidatos_para_nao_ficar_obsoleto():
    # Achado 2 (revisão final de branch SP-G): candidatos[0] precisa refletir
    # a sigla DECIDIDA (79OK), não a base descartada (79) — senão a
    # auditoria mostra o score de "79" ao lado do rótulo "79OK".
    cfg = _config()
    lp = _lp()
    rec = _rec_decidido("Religamento (79) - Bem Sucedido", sigla="79", cfg=cfg)
    assert rec.candidatos[0].sigla == "79"
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79OK"
    assert out.candidatos[0].sigla == "79OK"
    assert out.candidatos[0].score == rec.candidatos[0].score
    assert out.candidatos[0].fonte == "qualificador"
    # o candidato antigo (base) continua presente, só não é mais o topo
    assert any(c.sigla == "79" for c in out.candidatos[1:])


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


def test_irmao_promovido_apesar_de_filtro_estado_hard_documented():
    """Achado 1 (revisão final de branch SP-G): pinagem de comportamento
    aceito, não uma correção.

    ``preferir_irmao_qualificado`` busca o irmão qualificado em TODA a lista
    padrão (``lp.discretos``/``lp.analogicos``), não em ``rec.candidatos``
    (sobreviventes pós-filtros). Isso significa que um irmão eliminado por
    ``semantica_estados.filtrar_por_estado`` — por a classe de estado do MM
    dele conflitar com o estado detectado no texto — ainda pode ser
    promovido aqui, se tiver token exclusivo casando no texto.

    Este teste CONSTRÓI esse cenário sinteticamente (família ANSI fictícia
    "79" com um irmão "79EXC" cujo MM é classe FUNCAO, mas cujo token
    distintivo aparece num texto cuja classe detectada é EVENTO) para provar
    que o mecanismo é ALCANÇÁVEL em tese.

    Investigação na lista padrão REAL (docs/Pontos Padrao ADMS_v2.xlsx, 26
    famílias ANSI, 12 com classes de MM mistas entre irmãos) não encontrou
    NENHUM caso onde isso ocorre de fato — o vocabulário distintivo de um
    irmão tende a ser o mesmo vocabulário que evidencia a classe de estado
    do MM dele (mesma fonte: a descrição padrão do próprio irmão). Por isso
    o risco foi aceito como estreito na prática (ver docstring do módulo).

    Se algum dia a lista padrão real introduzir essa colisão, ou se este
    teste passar a falhar porque o comportamento mudou, isso deve forçar
    uma reavaliação consciente — não um "conserto silencioso".
    """
    cfg = _config()
    lp = _LP([
        _SP("79", "79 - FUNCAO RELIGAMENTO", mm=None),
        _SP(
            "79LO", "79 - RELIGAMENTO BLOQUEADO",
            mm="null@null___NORMAL@ATUADO___RecloserLockout_S_TS_SA",  # EVENTO
        ),
        _SP(
            "79EXC", "79 - EXCLUSAO AUTOMATICA",
            mm="INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled_S_TS_SS",  # FUNCAO
        ),
    ])
    texto_bruto = "Religamento (79) Bloqueio por Exclusao Automatica na Falha"
    rec = _rec_decidido(texto_bruto, sigla="79", cfg=cfg)

    # Passo 1: prova que filtrar_por_estado (SP-E D2), rodando ANTES do
    # roteador no pipeline real, teria eliminado 79EXC por causa (conflito
    # de classe de estado: texto é EVENTO, MM de 79EXC é FUNCAO).
    candidatos_com_79exc = (
        Candidato("79", 0.9, "mesclado"),
        Candidato("79EXC", 0.85, "mesclado"),
    )
    mantidos, zerou = filtrar_por_estado(rec, candidatos_com_79exc, lp)
    assert [c.sigla for c in mantidos] == ["79"]
    assert zerou is False

    # Passo 2: preferir_irmao_qualificado roda DEPOIS, ignorando o que
    # filtrar_por_estado já decidiu, e promove 79EXC mesmo assim —
    # comportamento aceito (ver docstring do módulo), pinado aqui.
    out = preferir_irmao_qualificado(rec, lp, cfg)
    assert out.sigla_sinal == "79EXC"
    assert out.status == "decidido"
