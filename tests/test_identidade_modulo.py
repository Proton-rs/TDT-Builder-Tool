from tdt.contracts import Modulo, TIPOS_MODULO, TipoSinal, Enderecamento, Descricoes, SignalRecord
from tdt.config import Config


def test_modulo_tem_campo_tipo_default_none():
    m = Modulo("AL15", "sheet_name")
    assert m.tipo is None
    m2 = Modulo("AL15", "sheet_name", tipo="Alimentador")
    assert m2.tipo == "Alimentador"


def test_tipos_modulo_tem_nove_categorias():
    assert "Alimentador" in TIPOS_MODULO
    assert "Outros" in TIPOS_MODULO
    assert len(TIPOS_MODULO) == 9


def test_config_tem_tabelas_de_modulo():
    cfg = Config()
    assert cfg.mapa_prefixo_modulo["GTD"] == "AL"
    assert cfg.mapa_prefixo_modulo["FWB"] == "AL"
    assert cfg.tipo_por_prefixo["AL"] == "Alimentador"
    assert "CAPACITOR" in cfg.palavras_chave_tipo["Banco de Capacitores"]


from tdt.identidade_modulo import resolver_modulo, classificar_tipo


def test_resolver_modulo_prefixo_e_numero():
    cfg = Config()
    assert resolver_modulo("AL FWB15", [], cfg).nome == "AL15"
    assert resolver_modulo("GTD_11", [], cfg).nome == "AL11"
    assert resolver_modulo("AL FWB15", [], cfg).confianca == "alta"


def test_resolver_modulo_sem_numero_cai_em_baixa_confianca():
    cfg = Config()
    r = resolver_modulo("SLOT GERAL", [], cfg)
    assert r.confianca == "baixa"
    assert r.nome == "SLOT GERAL"  # fallback ao nome cru


def test_resolver_modulo_sinonimo_de_prefixo_nao_e_ambiguo():
    # AL e FWB sao sinonimos (ambos mapeiam para "AL") -> conjunto de prefixos
    # distintos tem tamanho 1, nao e ambiguo.
    cfg = Config()
    r = resolver_modulo("AL FWB15", [], cfg)
    assert r.nome == "AL15"
    assert r.confianca == "alta"


def test_resolver_modulo_dois_numeros_e_ambiguo():
    cfg = Config()
    for nome in ("SPS_TR1_TR2", "TR1_TR2"):
        r = resolver_modulo(nome, [], cfg)
        assert r.confianca == "baixa", f"{nome} deveria ser baixa confianca (ambiguo)"
        assert r.nome == nome  # fallback ao nome cru


def test_resolver_modulo_dois_prefixos_distintos_e_ambiguo():
    cfg = Config()
    r = resolver_modulo("LT TR 3", [], cfg)
    assert r.confianca == "baixa"
    assert r.nome == "LT TR 3"


# --- Item 1 (28-jun): prefixos expandidos a partir da medição real em
# input_nao_homogeneo_1 (GTA). TRF é módulo de Transferência, distinto de TR
# (Transformador) -- confirmado no ground-truth real (TDT exportado tem
# TRF1/TRF2/TRF03 E TR1/TR2/TR1AT/TR2BT no mesmo arquivo).


def test_resolver_modulo_trf_nao_funde_com_tr():
    cfg = Config()
    assert resolver_modulo("TRF3_P", [], cfg).nome == "TRF03"  # SP-B: TRF3 -> TRF03
    assert resolver_modulo("TRF3_P", [], cfg).confianca == "alta"
    assert resolver_modulo("TRF-1", [], cfg).nome == "TRF1"
    assert resolver_modulo("TRF-2", [], cfg).nome == "TRF2"
    # TR e TRF continuam famílias distintas -- nunca um TR* sai como TRF* nem vice-versa.
    assert resolver_modulo("TR1_P", [], cfg).nome == "TR1"


def test_resolver_modulo_alias_direto_por_sheet_bay_sem_numero():
    # 01F1_GTA_P / 01F1_KGC_P: módulo real (confirmado na coluna B do input
    # real e no ground-truth do TDT) é LT_GTA/LT_KGC -- sheet_name não tem
    # prefixo numérico decomponível (01F1 é o IED, não o módulo).
    cfg = Config()
    r = resolver_modulo("01F1_GTA_P", [], cfg)
    assert r.nome == "LTGTA"
    assert r.confianca == "alta"
    assert resolver_modulo("01F1_KGC_P", [], cfg).nome == "LTKGC"


def test_resolver_modulo_alias_direto_barra_87b():
    cfg = Config()
    assert resolver_modulo("87B_AT", [], cfg).nome == "87BAT"
    assert resolver_modulo("87B_AT", [], cfg).confianca == "alta"
    assert resolver_modulo("87B_MT1", [], cfg).nome == "87BMT1"
    assert resolver_modulo("87B_MT2", [], cfg).nome == "87BMT2"


def test_resolver_modulo_alias_direto_ib_ignora_numero_de_tensao():
    # IB_23kV: "23" é a tensão (23kV), não o número do módulo -- confirmado no
    # TDT real (módulo de interbarras lá é "IB", sem número).
    cfg = Config()
    r = resolver_modulo("IB_23kV", [], cfg)
    assert r.nome == "IB"
    assert r.confianca == "alta"


def test_resolver_modulo_alias_direto_psaca():
    cfg = Config()
    r = resolver_modulo("PSACA_CC", [], cfg)
    assert r.nome == "PSACA"
    assert r.confianca == "alta"


def test_resolver_modulo_sps_tr1_tr2_continua_baixa_confianca():
    # Esquema especial com 2 trafos -- ambíguo por construção, comportamento
    # já correto antes desta mudança; só confirma que não regrediu.
    cfg = Config()
    r = resolver_modulo("SPS_TR1_TR2", [], cfg)
    assert r.confianca == "baixa"
    assert r.nome == "SPS_TR1_TR2"


def test_resolver_modulo_trf3_vira_trf03():
    cfg = Config()
    assert resolver_modulo("TRF3_P", [], cfg).nome == "TRF03"
    assert resolver_modulo("TRF3_A", [], cfg).nome == "TRF03"
    assert resolver_modulo("TRF3_P", [], cfg).confianca == "alta"


def test_resolver_modulo_trf1_trf2_sem_padding():
    # quirk de dado é só do TRF3 (real tem TRF03 mas TRF1/TRF2 sem pad)
    cfg = Config()
    assert resolver_modulo("TRF-1", [], cfg).nome == "TRF1"
    assert resolver_modulo("TRF-2", [], cfg).nome == "TRF2"


def test_classificar_tipo_trf_e_transferencia():
    assert classificar_tipo("TRF3", [], Config()) == "Transferência"


def test_classificar_tipo_87b_e_ib_sao_barra():
    assert classificar_tipo("87BAT", [], Config()) == "Barra"
    assert classificar_tipo("IB", [], Config()) == "Barra"


def _rec(norm: str) -> SignalRecord:
    return SignalRecord(
        id="t:1",
        modulo=Modulo("X", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", ()),
        descricoes=Descricoes(norm, norm),
    )


def test_classificar_por_prefixo():
    assert classificar_tipo("AL15", [], Config()) == "Alimentador"


def test_classificar_por_conteudo_quando_prefixo_desconhecido():
    recs = [_rec("BANCO CAPACITOR FASE A")]
    assert classificar_tipo("XYZ9", recs, Config()) == "Banco de Capacitores"


def test_classificar_fallback_outros():
    assert classificar_tipo("ZZZ1", [_rec("SINAL GENERICO")], Config()) == "Outros"


def test_classificar_nao_faz_match_de_substring_dentro_de_outra_palavra():
    # "DESALINHADA" contem "LINHA" como substring, mas nao deve classificar
    # como Linha de Transmissao: o match precisa ser por token inteiro.
    recs = [_rec("CHAVE DESALINHADA")]
    assert classificar_tipo("ZZZ1", recs, Config()) == "Outros"


from tdt.identidade_modulo import aplicar_identidade


def test_aplicar_identidade_sobrescreve_nome_de_sheet_e_classifica():
    sinais = [_rec("DISJUNTOR LIGADO")]  # _rec usa Modulo("X","sheet_name")
    novos, conf = aplicar_identidade(sinais, "AL FWB15", [], Config())
    assert novos[0].modulo.nome == "AL15"
    assert novos[0].modulo.tipo == "Alimentador"
    assert conf == "alta"


def test_aplicar_identidade_preserva_nome_de_coluna():
    base = _rec("DISJUNTOR")
    base = base.__class__(**{**base.__dict__, "modulo": Modulo("AL11", "coluna:MODULO")})
    novos, _ = aplicar_identidade([base], "GTD_11", [], Config())
    assert novos[0].modulo.nome == "AL11"  # não sobrescreve módulo de coluna
    assert novos[0].modulo.tipo == "Alimentador"  # mas classifica o tipo


from tdt.identidade_modulo import particionar_por_confianca


def test_particionar_baixa_vai_tudo_pra_revisao():
    sinais = [_rec("SINAL A"), _rec("SINAL B")]
    segue, revisao = particionar_por_confianca(sinais, "baixa")
    assert len(segue) == 2
    assert not segue[0].tipo_sinal.categoria_confiavel
    assert not segue[1].tipo_sinal.categoria_confiavel
    assert [it.motivo for it in revisao] == ["modulo_indefinido", "modulo_indefinido"]


def test_particionar_alta_segue_adiante():
    sinais = [_rec("SINAL A")]
    segue, revisao = particionar_por_confianca(sinais, "alta")
    assert segue == sinais
    assert revisao == []
