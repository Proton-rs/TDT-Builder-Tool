"""Testes unitários dos filtros de domínio em filtro_preciso.py (F_R1-R6,
F_equip) + integração de filtrar() + casos de borda."""

from __future__ import annotations

from dataclasses import dataclass

from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord,
    TipoSinal,
)
from tdt.filtro_preciso import f_equip, f_r1, f_r2, f_r3, f_r4, f_r5, f_r6, filtrar
from tdt.motor_regras import Contexto


def _ctx(texto: str, eletrico: Eletrico | None = None) -> Contexto:
    return Contexto(
        tokens=frozenset(texto.upper().split()),
        eletrico=eletrico if eletrico is not None else Eletrico(),
    )


def _cand(sigla: str, score: float = 0.5) -> Candidato:
    return Candidato(sigla, score, "x")


def _rec(bruta: str, normalizada: str, eletrico: Eletrico | None = None) -> SignalRecord:
    return SignalRecord(
        id="x",
        modulo=Modulo(None, "M"),
        tipo_sinal=TipoSinal("Discrete", True, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(bruta, normalizada),
        eletrico=eletrico if eletrico is not None else Eletrico(),
    )


# --- F_R1: número de proteção -----------------------------------------------


def test_f_r1_remove_numero_divergente():
    ctx = _ctx("PROTECAO 67 SOBRECORRENTE")
    assert f_r1(_cand("51"), ctx) is False


def test_f_r1_mantem_numero_igual():
    ctx = _ctx("PROTECAO 67 SOBRECORRENTE")
    assert f_r1(_cand("67N"), ctx) is True


def test_f_r1_sem_numero_no_texto_mantem():
    ctx = _ctx("DISJUNTOR ABERTO")
    assert f_r1(_cand("51"), ctx) is True


def test_f_r1_candidato_sem_numero_lider_mantem():
    ctx = _ctx("PROTECAO 67 SOBRECORRENTE")
    assert f_r1(_cand("DJ"), ctx) is True


# --- F_R2: pares opostos -----------------------------------------------------


def test_f_r2_remove_marca_oposta_sobre_sub():
    ctx = _ctx("SOBRECORRENTE FASE")
    assert f_r2(_cand("37"), ctx) is False  # 37 é marca de SUBcorrente


def test_f_r2_mantem_marca_compativel():
    ctx = _ctx("SOBRECORRENTE FASE")
    assert f_r2(_cand("50"), ctx) is True


def test_f_r2_sem_discriminador_mantem():
    ctx = _ctx("DISJUNTOR ABERTO")
    assert f_r2(_cand("50"), ctx) is True


def test_f_r2_ambos_tokens_presentes_nao_decide():
    # tokens_a e tokens_b presentes ao mesmo tempo -> ambíguo, não filtra
    ctx = _ctx("SOBRECORRENTE SUBCORRENTE")
    assert f_r2(_cand("37"), ctx) is True


# --- F_R3: fase ---------------------------------------------------------------


def test_f_r3_remove_fase_divergente():
    ctx = _ctx("CORRENTE FASE", Eletrico(fase="B"))
    assert f_r3(_cand("IA"), ctx) is False


def test_f_r3_mantem_fase_igual():
    ctx = _ctx("CORRENTE FASE", Eletrico(fase="B"))
    assert f_r3(_cand("IB"), ctx) is True


def test_f_r3_mantem_candidato_sem_fase():
    ctx = _ctx("CORRENTE FASE", Eletrico(fase="B"))
    assert f_r3(_cand("IOUT"), ctx) is True


def test_f_r3_sem_fase_no_eletrico_mantem_tudo():
    ctx = _ctx("CORRENTE", Eletrico(fase=None))
    assert f_r3(_cand("IA"), ctx) is True


# --- F_R4: estágio -------------------------------------------------------------


def test_f_r4_remove_estagio_divergente():
    ctx = _ctx("SUB FREQUENCIA E1")
    assert f_r4(_cand("81E2"), ctx) is False


def test_f_r4_mantem_estagio_igual():
    ctx = _ctx("SUB FREQUENCIA E1")
    assert f_r4(_cand("81E1"), ctx) is True


def test_f_r4_sem_estagio_no_texto_mantem():
    ctx = _ctx("SUB FREQUENCIA")
    assert f_r4(_cand("81E2"), ctx) is True


# --- F_R5: comando x status ----------------------------------------------------


def test_f_r5_remove_status_quando_texto_comanda():
    ctx = _ctx("COMANDO LIGAR DISJUNTOR")
    assert f_r5(_cand("DJST"), ctx) is False


def test_f_r5_remove_comando_quando_texto_e_status():
    ctx = _ctx("DISJUNTOR ABERTO STATUS")
    assert f_r5(_cand("DJ_CMD"), ctx) is False


def test_f_r5_mantem_comando_quando_texto_comanda():
    ctx = _ctx("COMANDO LIGAR DISJUNTOR")
    assert f_r5(_cand("DJ_CMD"), ctx) is True


def test_f_r5_fcom_nao_e_falso_positivo_de_comando():
    # FCOM (Falha Comunicação) não deve casar como comando via "COM" solto
    ctx = _ctx("DISJUNTOR ABERTO STATUS")
    assert f_r5(_cand("FCOM"), ctx) is True


# --- F_equip: equipamento -------------------------------------------------------


def test_f_equip_remove_familia_diferente_disjuntor_no_texto():
    ctx = _ctx("DISJUNTOR ABERTO")
    assert f_equip(_cand("SEC1"), ctx) is False


def test_f_equip_mantem_familia_igual():
    ctx = _ctx("DISJUNTOR ABERTO")
    assert f_equip(_cand("DJ1"), ctx) is True


def test_f_equip_sem_pista_de_equipamento_mantem():
    ctx = _ctx("STATUS GERAL")
    assert f_equip(_cand("DJ1"), ctx) is True


def test_f_equip_candidato_sem_familia_mantem():
    ctx = _ctx("DISJUNTOR ABERTO")
    assert f_equip(_cand("IA"), ctx) is True


# --- F_R6: lado / nível de tensão ------------------------------------------------


def test_f_r6_remove_lado_oposto():
    ctx = _ctx("TENSAO PRIMARIO")
    assert f_r6(_cand("V_BT"), ctx) is False


def test_f_r6_mantem_lado_igual():
    ctx = _ctx("TENSAO PRIMARIO")
    assert f_r6(_cand("V_AT"), ctx) is True


def test_f_r6_sem_pista_de_lado_mantem():
    ctx = _ctx("TENSAO GERAL")
    assert f_r6(_cand("V_BT"), ctx) is True


def test_f_r6_candidato_generico_sem_marca_mantem():
    ctx = _ctx("TENSAO PRIMARIO")
    assert f_r6(_cand("V"), ctx) is True


# --- filtrar(): integração, cascata em ordem -----------------------------------


def test_filtrar_aplica_todos_os_filtros_em_cascata():
    # Texto indica disjuntor + fase B + comando -> só DJ_CMD_B sobrevive.
    rec = _rec(
        "Comando Ligar Disjuntor Fase B",
        "COMANDO LIGAR DISJUNTOR FASE",
        Eletrico(fase="B"),
    )
    candidatos = [
        _cand("DJ_CMD_B"),  # disjuntor, comando, fase B -> mantém
        _cand("DJ_CMD_A"),  # fase divergente -> remove (f_r3)
        _cand("DJST_B"),  # status, não comando -> remove (f_r5)
        _cand("SEC_CMD_B"),  # seccionadora, não disjuntor -> remove (f_equip)
    ]
    out = filtrar(rec, candidatos, Config())
    siglas = [c.sigla for c in out]
    assert siglas == ["DJ_CMD_B"]


def test_filtrar_fallback_quando_todos_removidos_retorna_original():
    # Texto exige número de proteção 67; nenhum candidato bate -> filtro
    # eliminaria todos -> fallback preserva a lista original.
    rec = _rec("Protecao 67 Sobrecorrente", "PROTECAO 67 SOBRECORRENTE")
    candidatos = [_cand("51"), _cand("27")]
    out = filtrar(rec, candidatos, Config())
    assert [c.sigla for c in out] == ["51", "27"]


def test_filtrar_lista_vazia_retorna_vazia():
    rec = _rec("Disjuntor Aberto", "DISJUNTOR ABERTO")
    out = filtrar(rec, [], Config())
    assert out == []


def test_filtrar_nenhum_removido_quando_sem_conflitos():
    rec = _rec("Status Geral", "STATUS GERAL")
    candidatos = [_cand("DJ1"), _cand("SEC1"), _cand("IA")]
    out = filtrar(rec, candidatos, Config())
    assert [c.sigla for c in out] == ["DJ1", "SEC1", "IA"]


def test_filtrar_config_none_funciona_igual():
    rec = _rec("Disjuntor Aberto", "DISJUNTOR ABERTO")
    candidatos = [_cand("DJ1"), _cand("SEC1")]
    out = filtrar(rec, candidatos, None)
    assert [c.sigla for c in out] == ["DJ1"]
