from tdt.config import Config
from tdt.contracts import (
    Candidato,
    Descricoes,
    Eletrico,
    Enderecamento,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.motor_regras import (
    Contexto,
    aplicar,
    aplicar_rastreado,
    equipamento_da_sigla,
    r7_estado_compativel,
    r_equipamento,
)

_CFG = Config()


def _lp():
    return ListaPadraoADMS(
        discretos=(
            SinalPadrao("SGF", "FUNCAO SGF", "Enabled", "Read",
                        "INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled_S_TS_SS", "Discrete"),
            SinalPadrao("SGFT", "TRIP SGF", "RelayTrip", "Read",
                        "null@null___NORMAL@ATUADO___RelayTrip_S_TS_SA", "Discrete"),
            SinalPadrao("79_EXC", "79 - EXCLUIR RELIGAMENTO", "Custom", "Write",
                        "null@EXCLUIR___null@null___ReclosingEnabled___admsINV_D_TC_SS",
                        "Discrete"),
        ),
        analogicos=(),
    )


def _rec(desc_norm, eletrico=None):
    return SignalRecord(
        id="LT3:4",
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes(desc_norm, desc_norm),
        eletrico=eletrico or Eletrico(),
    )


# --- retrocompat (pipeline chama com 2 args) --------------------------------


def test_neutro_desconsidera_candidatos_de_fase():
    rec = _rec("PROTECAO", eletrico=Eletrico(fase="N"))
    cands = [Candidato("67F", 0.70, "mesclado"), Candidato("67N", 0.70, "mesclado")]
    out = aplicar(rec, cands)
    assert out[0].sigla == "67N"


def test_estagio_e1_favorece_sigla_com_1():
    rec = _rec("PROTECAO E1 NEUTRO")
    cands = [Candidato("67N", 0.60, "mesclado"), Candidato("67N1", 0.60, "mesclado")]
    out = aplicar(rec, cands)
    assert out[0].sigla == "67N1"


def test_sem_pistas_mantem_ordem():
    rec = _rec("DISJUNTOR")
    cands = [Candidato("DJ", 0.9, "mesclado"), Candidato("SEC", 0.5, "mesclado")]
    out = aplicar(rec, cands)
    assert [c.sigla for c in out] == ["DJ", "SEC"]


# --- R1: número de proteção -------------------------------------------------


def test_r1_numero_protecao_boost_e_penaliza_divergente():
    rec = _rec("67N SOBRECORRENTE NEUTRO DIRECIONAL")
    cands = [Candidato("87T", 0.70, "mesclado"), Candidato("67N", 0.65, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "67N"  # boost 67 + penalidade 87


# --- R2: pares opostos ------------------------------------------------------


def test_r2_sobrecorrente_nao_decide_subcorrente():
    rec = _rec("PROTECAO SOBRECORRENTE FASE")
    cands = [Candidato("37", 0.72, "mesclado"), Candidato("51", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "51"  # 37 (subcorrente) penalizado pelo discriminador SOBRE


def test_r2_sobretensao_vs_subtensao_pelo_discriminador():
    rec = _rec("ALARME SOBRETENSAO BARRA")
    cands = [Candidato("27", 0.71, "mesclado"), Candidato("59", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "59"  # 27 (subtensão) penalizado por SOBRETENSAO/59


# --- R3: fase ---------------------------------------------------------------


def test_r3_neutro_favorece_n_penaliza_fase_pura():
    rec = _rec("PROTECAO SOBRECORRENTE", eletrico=Eletrico(fase="N"))
    cands = [Candidato("51F", 0.70, "mesclado"), Candidato("51N", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "51N"


def test_r3_fase_generica_compativel_com_multifase_do_texto():
    # "50 ABC" extrai fase="ABC" (D2.2); 50F1 (genérica) compatível com ABC,
    # 50_1 (sem fase) não recebe bônus -- desempata na direção certa.
    rec = _rec("PROTECAO 50 ABC ESTAGIO 1", eletrico=Eletrico(fase="ABC"))
    cands = [Candidato("50_1", 0.74, "mesclado"), Candidato("50F1", 0.74, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "50F1"


def test_r3_fase_especifica_explicita_vence_variante_generica():
    # alvo de fase específica (ex "A") -- candidato genérico (F) NÃO ganha o
    # novo bônus (só multi-fase); comportamento pré-D2.3 preservado.
    rec = _rec("PROTECAO FASE A", eletrico=Eletrico(fase="A"))
    cands = [Candidato("FA", 0.70, "mesclado"), Candidato("50F1", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "FA"


# --- R4: estágio ------------------------------------------------------------


def test_r4_estagio_e2_favorece_sigla_terminada_em_2():
    rec = _rec("SOBRECORRENTE E2")
    cands = [Candidato("51N1", 0.60, "mesclado"), Candidato("51N2", 0.60, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "51N2"


# --- R5: comando × status ---------------------------------------------------


def test_r5_comando_favorece_candidato_de_comando():
    rec = _rec("DISJUNTOR COMANDO LIGAR")
    cands = [Candidato("52STATUS", 0.70, "mesclado"), Candidato("52CMD", 0.68, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "52CMD"


# --- R6: lado / nível de tensão ---------------------------------------------


def test_r6_lado_primario_favorece_at():
    rec = _rec("CORRENTE PRIMARIO TRANSFORMADOR")
    cands = [Candidato("IBT", 0.70, "mesclado"), Candidato("IAT", 0.69, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "IAT"


def test_r6_usa_contexto_eletrico_quando_texto_silencia():
    rec = _rec("CORRENTE TRANSFORMADOR", eletrico=Eletrico(nivel_tensao="BT"))
    cands = [Candidato("IAT", 0.70, "mesclado"), Candidato("IBT", 0.69, "mesclado")]
    out = aplicar(rec, cands, _CFG)
    assert out[0].sigla == "IBT"


# --- rastreamento -----------------------------------------------------------


def test_aplicar_rastreado_retorna_motivos_legiveis():
    rec = _rec("67N SOBRECORRENTE NEUTRO E1", eletrico=Eletrico(fase="N"))
    cands = [Candidato("67N1", 0.60, "mesclado"), Candidato("87T", 0.60, "mesclado")]
    out, ajustes = aplicar_rastreado(rec, cands, _CFG)
    assert out[0].sigla == "67N1"
    assert ajustes  # houve regras atuando
    motivos = " | ".join(a.motivo for a in ajustes)
    assert "numero_protecao" in motivos
    assert "fase" in motivos
    assert "estagio" in motivos


# --- R_equip: equipamento ----------------------------------------------------


def test_equipamento_da_sigla_disjuntor():
    assert equipamento_da_sigla("DJ") == "Disjuntor"
    assert equipamento_da_sigla("DJE1") == "Disjuntor"


def test_equipamento_da_sigla_seccionadora():
    assert equipamento_da_sigla("SECC") == "Seccionadora"
    assert equipamento_da_sigla("SECB") == "Seccionadora"


def test_equipamento_da_sigla_sem_match():
    assert equipamento_da_sigla("BATA") is None


def test_r_equipamento_penaliza_familia_errada():
    ctx = Contexto(tokens=frozenset(), eletrico=Eletrico(equipamento_alvo="Disjuntor"))
    cand = Candidato("SECC", 0.8, "tfidf")
    cfg = Config()
    ajuste = r_equipamento(None, cand, ctx, cfg)
    assert ajuste.delta < 0


def test_r_equipamento_neutro_sem_alvo():
    ctx = Contexto(tokens=frozenset(), eletrico=Eletrico())
    cand = Candidato("SECC", 0.8, "tfidf")
    cfg = Config()
    ajuste = r_equipamento(None, cand, ctx, cfg)
    assert ajuste.delta == 0.0


# --- R7: estado compatível (SP-G Task 7) -------------------------------------
#
# NOTA sobre o candidato "incompatível" usado no teste: a brief original sugeria
# '79_EXC' (sigla só-comando, Write) como exemplo de incompatibilidade. Verificado
# contra a LP real (docs/Pontos Padrao ADMS_v2.xlsx): o MM de 79_EXC é
# "null@EXCLUIR___null@null___..." -- o segmento de ESTADOS (2a posição) é
# "null@null", que classe_do_mm() classifica como None (sem par de estado --
# é comando puro). A própria brief instrui: "If classe_mm is None: return _ZERO
# (candidate's MM has no clear state-class, e.g. a Write-only command with no
# read state pair)" -- ou seja, 79_EXC é o exemplo CANÔNICO de _ZERO, não de
# incompatibilidade. Usamos 'SGF' (classe FUNCAO via INCLUIR@EXCLUIDO) como o
# candidato realmente incompatível com o texto ATUADO (classe EVENTO) -- mesmo
# par já usado em test_semantica_estados.test_filtro_elimina_sigla_de_estado_incompativel.


def test_regra_estado_compativel_pontua(lp=_lp()):
    # 'PROTECAO SGF ATUADO': estado ATUADO (EVENTO) casa com NORMAL@ATUADO de SGFT
    rec = _rec("Proteção SGF - Atuado")
    ajuste = r7_estado_compativel(rec, Candidato("SGFT", 0.5, "mesclado"), Contexto.de(rec, lp), _CFG)
    assert ajuste.delta > 0


def test_regra_estado_incompativel_penaliza(lp=_lp()):
    # SGF (classe FUNCAO: INCLUIR/EXCLUIR) nao casa com o texto de estado ATUADO (EVENTO)
    rec = _rec("Proteção SGF - Atuado")
    ajuste = r7_estado_compativel(rec, Candidato("SGF", 0.5, "mesclado"), Contexto.de(rec, lp), _CFG)
    assert ajuste.delta < 0


def test_regra_estado_sem_classe_mm_e_neutra(lp=_lp()):
    # 79_EXC: MM so-comando (estados = "null@null") -> classe_do_mm None -> _ZERO
    rec = _rec("Proteção SGF - Atuado")
    ajuste = r7_estado_compativel(
        rec, Candidato("79_EXC", 0.5, "mesclado"), Contexto.de(rec, lp), _CFG
    )
    assert ajuste.delta == 0.0


def test_regra_estado_sem_lista_padrao_e_neutra():
    # Contexto sem lista_padrao (retrocompat, ex. bench/benchmark.py) -> no-op seguro
    rec = _rec("Proteção SGF - Atuado")
    ajuste = r7_estado_compativel(rec, Candidato("SGFT", 0.5, "mesclado"), Contexto.de(rec), _CFG)
    assert ajuste.delta == 0.0


def test_regra_estado_sem_evidencia_no_texto_e_neutra(lp=_lp()):
    rec = _rec("DISJUNTOR ABERTO")  # classe POSICAO, nao EVENTO -- sem conflito p/ SGF
    ajuste = r7_estado_compativel(rec, Candidato("SGF", 0.5, "mesclado"), Contexto.de(rec, lp), _CFG)
    # POSICAO detectado, SGF e FUNCAO -> incompativel tambem penaliza (nao e "sem evidencia")
    assert ajuste.delta < 0


def test_aplicar_rastreado_thread_lista_padrao_para_sgft():
    lp = _lp()
    rec = _rec("Proteção SGF - Atuado")
    cands = [Candidato("SGF", 0.6, "mesclado"), Candidato("SGFT", 0.5, "mesclado")]
    out, ajustes = aplicar_rastreado(rec, cands, _CFG, lista_padrao=lp)
    assert out[0].sigla == "SGFT"
    motivos = " | ".join(a.motivo for a in ajustes)
    assert "estado" in motivos


def _rec_dir(desc_norm, direcao):
    return SignalRecord(
        id="LT3:9",
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes(desc_norm, desc_norm),
    )


def _lp_dir():
    return ListaPadraoADMS(
        discretos=(
            SinalPadrao("AUTC", "REARME AUTOMATISMO", "Custom", "ReadWrite",
                        None, "Discrete"),
            SinalPadrao("AUTA", "REARME AUTOMATISMO ALARME", "Custom", "Read",
                        None, "Discrete"),
        ),
        analogicos=(),
    )


# --- R8: direção -------------------------------------------------------------


def test_r8_comando_favorece_candidato_de_escrita():
    rec = _rec_dir("REARME AUTOMATISMO", "Output")
    cands = [Candidato("AUTA", 0.70, "mesclado"), Candidato("AUTC", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG, lista_padrao=_lp_dir())
    assert out[0].sigla == "AUTC"  # ReadWrite boost; AUTA (Read) penalizado


def test_r8_input_puro_e_noop():
    rec = _rec_dir("REARME AUTOMATISMO", "Input")
    cands = [Candidato("AUTA", 0.70, "mesclado"), Candidato("AUTC", 0.70, "mesclado")]
    out = aplicar(rec, cands, _CFG, lista_padrao=_lp_dir())
    # sem comando no input, r8 não mexe — ordem original preservada
    assert out[0].sigla == "AUTA"


def test_r8_sem_lista_padrao_e_noop():
    rec = _rec_dir("REARME AUTOMATISMO", "Output")
    cands = [Candidato("AUTA", 0.70, "mesclado"), Candidato("AUTC", 0.69, "mesclado")]
    out = aplicar(rec, cands, _CFG)  # sem lista_padrao
    assert out[0].sigla == "AUTA"
