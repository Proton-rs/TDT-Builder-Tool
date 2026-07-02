from tdt.contracts import Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.semantica_estados import (
    ATIVACAO, EVENTO, FUNCAO, INDEFINIDO, LOCAL_REMOTO, POSICAO,
    classe_do_mm, compatibilidade_texto, compativel, detectar_estado,
    filtrar_por_estado,
)


# --- detectar_estado --------------------------------------------------------

def test_detecta_evento_atuado():
    e = detectar_estado("PROTECAO SGF ATUADO")
    assert e.classe == EVENTO


def test_detecta_funcao_excluida():
    e = detectar_estado("PROTECAO SGF EXCLUIDA")
    assert e.classe == FUNCAO


def test_detecta_funcao_verbos_comando():
    assert detectar_estado("SGF EXCLUIR INCLUIR").classe == FUNCAO


def test_detecta_posicao_com_polaridade():
    assert detectar_estado("52 DESLIGADO") == detectar_estado("DISJUNTOR DESLIGADO")
    assert detectar_estado("52 DESLIGADO").classe == POSICAO
    assert detectar_estado("52 DESLIGADO").polaridade == "B"
    assert detectar_estado("52 LIGADO").polaridade == "A"
    assert detectar_estado("SECCIONADORA ABERTA").polaridade == "B"
    assert detectar_estado("SECCIONADORA FECHADA").polaridade == "A"


def test_detecta_ativacao():
    assert detectar_estado("81 E1 HABILITAR").classe == ATIVACAO
    assert detectar_estado("ESTAGIO 1 HABILITAR DESABILITAR").classe == ATIVACAO


def test_detecta_local_remoto():
    assert detectar_estado("CHAVE 43LR POS LOCAL").classe == LOCAL_REMOTO
    assert detectar_estado("CHAVE 43LR POS REMOTO").classe == LOCAL_REMOTO


def test_indefinido_vence():
    assert detectar_estado("52 INDEFINIDO").classe == INDEFINIDO


def test_ambiguo_vira_none():
    # EVENTO (FALHA) + POSICAO (LIGAR) = ambíguo — filtro nenhum > filtro errado
    assert detectar_estado("FALHA COMANDO DE LIGAR") is None


def test_sem_evidencia_vira_none():
    assert detectar_estado("TRIP FASE A") is None
    assert detectar_estado("") is None
    assert detectar_estado(None) is None


def test_desligado_nao_casa_prefixo_ligado():
    # startswith é ancorado: DESLIGADO não pode cair na polaridade A
    assert detectar_estado("DESLIGADO").polaridade == "B"


# --- classe_do_mm -----------------------------------------------------------

def test_classe_mm_evento():
    assert classe_do_mm("null@null___NORMAL@ATUADO___RelayTrip_S_TS_SA") == EVENTO


def test_classe_mm_funcao():
    assert classe_do_mm(
        "INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled___admsINV_S_TC_SS"
    ) == FUNCAO


def test_classe_mm_posicao():
    assert classe_do_mm(
        "DESLIGAR@LIGAR___DESLIGADO@LIGADO___SwitchStatus_D_TC_SE"
    ) == POSICAO


def test_classe_mm_local_remoto_com_underscore_simples():
    # MM real da LP tem "__" (não "___") depois dos estados
    assert classe_do_mm("null@null___REMOTO@LOCAL__Local_S_TS_SS") == LOCAL_REMOTO


def test_classe_mm_sem_estados():
    assert classe_do_mm("AUMENTAR@DIMINUIR___null@null___TapIncrement_S_TC_SS") is None
    assert classe_do_mm(None) is None
    assert classe_do_mm("TapIncrement") is None


# --- compativel / compatibilidade_texto -------------------------------------

def test_atuado_incompativel_com_funcao():
    est = detectar_estado("PROTECAO SGF ATUADO")
    assert compativel(est, FUNCAO) is False
    assert compativel(est, EVENTO) is True


def test_sem_evidencia_e_compativel():
    assert compativel(None, FUNCAO) is True
    assert compativel(detectar_estado("SGF ATUADO"), None) is True


def test_compatibilidade_texto_comando_funcao_vs_trip():
    assert compatibilidade_texto("SGF EXCLUIR INCLUIR", "PROTECAO SGF ATUADO") is False
    assert compatibilidade_texto("SGF EXCLUIR INCLUIR", "PROTECAO SGF EXCLUIDA") is True
    assert compatibilidade_texto("QUALQUER COISA", "PROTECAO SGF ATUADO") is True


# --- filtrar_por_estado ------------------------------------------------------

def _lp_stub():
    return ListaPadraoADMS(
        discretos=(
            SinalPadrao("SGF", "FUNCAO SGF", "Enabled", "Read",
                        "INCLUIR@EXCLUIR___INCLUIDO@EXCLUIDO___Enabled_S_TS_SS", "Discrete"),
            SinalPadrao("SGFT", "TRIP SGF", "RelayTrip", "Read",
                        "null@null___NORMAL@ATUADO___RelayTrip_S_TS_SA", "Discrete"),
        ),
        analogicos=(),
    )


def _rec(desc):
    return SignalRecord(
        id="s:1", modulo=Modulo("AL11", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1535,)),
        descricoes=Descricoes(desc, desc),
    )


def test_filtro_elimina_sigla_de_estado_incompativel():
    cands = [Candidato("SGF", 0.9, "mesclado"), Candidato("SGFT", 0.7, "mesclado")]
    mantidos, zerou = filtrar_por_estado(_rec("PROTECAO SGF ATUADO"), cands, _lp_stub())
    assert [c.sigla for c in mantidos] == ["SGFT"]
    assert zerou is False


def test_filtro_zera_vai_pra_revisao():
    cands = [Candidato("SGF", 0.9, "mesclado")]
    mantidos, zerou = filtrar_por_estado(_rec("PROTECAO SGF ATUADO"), cands, _lp_stub())
    assert zerou is True
    assert mantidos == cands  # devolve originais p/ sugestões da revisão


def test_filtro_neutro_sem_estado_detectado():
    cands = [Candidato("SGF", 0.9, "mesclado")]
    mantidos, zerou = filtrar_por_estado(_rec("TRIP FASE A"), cands, _lp_stub())
    assert mantidos == cands and zerou is False
