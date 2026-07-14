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
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
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
    novos, conf, _ = aplicar_identidade(sinais, "AL FWB15", [], Config())
    assert novos[0].modulo.nome == "AL15"
    assert novos[0].modulo.tipo == "Alimentador"
    assert conf == "alta"


def test_aplicar_identidade_preserva_nome_de_coluna():
    base = _rec("DISJUNTOR")
    base = base.__class__(**{**base.__dict__, "modulo": Modulo("AL11", "coluna:MODULO")})
    novos, _, _ = aplicar_identidade([base], "GTD_11", [], Config())
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


from tdt.identidade_modulo import canonizar_modulo


def test_canonizar_explicito_prefixo_e_numero_com_sufixo_de_tensao():
    cfg = Config()
    assert canonizar_modulo("AL 11 - 13.8kV", cfg, explicito=True).nome == "AL11"
    assert canonizar_modulo("AL15 - 13.8kV (FUTURO)", cfg, explicito=True).nome == "AL15"
    assert canonizar_modulo("TR1", cfg, explicito=True).nome == "TR1"


def test_canonizar_explicito_sem_prefixo_usa_cru_limpo_alta():
    cfg = Config()
    r = canonizar_modulo("TIE-AT", cfg, explicito=True)
    assert r.nome == "TIE-AT"
    assert r.confianca == "alta"
    r2 = canonizar_modulo("LTSM3C1", cfg, explicito=True)
    assert r2.nome == "LTSM3C1"
    assert r2.confianca == "alta"


def test_canonizar_explicito_limpa_sufixo_futuro_sem_prefixo():
    cfg = Config()
    assert canonizar_modulo("TIE-AT (FUTURO)", cfg, explicito=True).nome == "TIE-AT"


def test_canonizar_nao_explicito_preserva_fallback_resolver_modulo():
    cfg = Config()
    r = canonizar_modulo("SLOT GERAL", cfg)  # explicito=False (default)
    assert r.nome == "SLOT GERAL"   # cru, SEM limpeza
    assert r.confianca == "baixa"


def test_canonizar_explicito_sufixo_tensao_com_prefixo_nao_mapeado():
    # XYZ não está em mapa_prefixo_modulo, então não é capturado por Estratégia 2.
    # Com explicito=True, a regex de _limpar_modulo (sufixo de tensão) deve remover
    # " - 13.8kV" e retornar o valor limpo com confiança alta.
    cfg = Config()
    r = canonizar_modulo("XYZ - 13.8kV", cfg, explicito=True)
    assert r.nome == "XYZ"
    assert r.confianca == "alta"


def _rec_mod(norm: str, nome_mod: str) -> SignalRecord:
    return SignalRecord(
        id="t:1",
        modulo=Modulo(nome_mod, "coluna:MODULO_POR_LINHA"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", ()),
        descricoes=Descricoes(norm, norm),
    )


def _sinal_coluna(rid, nome_mod):
    return SignalRecord(
        id=rid,
        modulo=Modulo(nome_mod, "coluna:MODULO_POR_LINHA"),
        tipo_sinal=TipoSinal("Discrete"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("x", "X"),
    )


def test_canonizar_modulo_marca_canonico():
    cfg = Config()
    assert canonizar_modulo("BC1_DJ_ABERTO", cfg, explicito=True).canonico
    # dois prefixos conhecidos (BC + IB) -> ambíguo -> fallback cru, não-canônico
    res = canonizar_modulo("BC1_CORRENTE_IB", cfg, explicito=True)
    assert not res.canonico and res.nome == "BC1_CORRENTE_IB"


def test_identidade_por_linha_sanea_lixo_pro_modulo_dominante():
    """SP-CVA2 E5.1 — célula fora do padrão herda o módulo dominante da sheet
    (com aviso) em vez de virar nome de módulo lixo."""
    sinais = [
        _sinal_coluna("BC2:5", "BC1_VAB"),
        _sinal_coluna("BC2:9", "BC1_CORRENTE_IB"),
        _sinal_coluna("BC2:21", "BC1_DJ_ABERTO"),
        _sinal_coluna("BC2:26", "(LogicaInterna!)"),
    ]
    novos, conf, avisos = aplicar_identidade(sinais, "BC2", [], Config())
    assert {s.modulo.nome for s in novos} == {"BC1"}
    assert len(avisos) == 2  # BC2:9 e BC2:26
    assert any("BC2:9" in a for a in avisos)


def test_aplicar_identidade_por_linha_canoniza_e_classifica_por_grupo():
    sinais = [
        _rec_mod("DISJUNTOR", "AL 11 - 13.8kV"),
        _rec_mod("CORRENTE", "TR1"),
    ]
    novos, conf, _ = aplicar_identidade(sinais, "ESTADOS", [], Config())
    assert novos[0].modulo.nome == "AL11"
    assert novos[0].modulo.tipo == "Alimentador"
    assert novos[1].modulo.nome == "TR1"
    assert novos[1].modulo.tipo == "Transformador"
    assert conf == "alta"


def test_aplicar_identidade_por_linha_reconcilia_variantes():
    # 'AL 11' e 'AL11' (variantes cross-sheet) canonizam para o mesmo nome
    sinais = [_rec_mod("SINAL A", "AL 11 - 13.8kV"), _rec_mod("SINAL B", "AL11 - 13.8kV")]
    novos, _, _ = aplicar_identidade(sinais, "MEDIDAS", [], Config())
    assert novos[0].modulo.nome == novos[1].modulo.nome == "AL11"


def test_aplicar_identidade_por_linha_canonizacao_vazia_vai_pra_revisao():
    # Célula de módulo é só sufixo de classe de tensão ("- 13.8kV"): não
    # vazia na origem, mas canoniza (explicito=True) para "" -- equivale a
    # módulo ausente e não pode seguir pro scoring em silêncio.
    sinais = [_rec_mod("DISJUNTOR", "- 13.8kV")]
    novos, _, _ = aplicar_identidade(sinais, "ESTADOS", [], Config())
    assert novos[0].status == "revisao"
    assert novos[0].justificativa == "modulo_indefinido"


from tdt.identidade_modulo import aviso_divergencia_sheet


def test_aviso_divergencia_sheet_bc2_rotulada_bc1():
    """SP-CVA2 E5.2 — sheet BC2 com conteúdo (módulo por linha) dominante BC1:
    aviso explícito; o sistema NÃO corrige (dado do cliente)."""
    sinais, _, _ = aplicar_identidade(
        [_sinal_coluna(f"BC2:{i}", "BC1_VAB") for i in range(4)], "BC2", [], Config()
    )
    aviso = aviso_divergencia_sheet("BC2", sinais, Config())
    assert aviso is not None and "BC1" in aviso and "BC2" in aviso


def test_aviso_divergencia_none_quando_coerente_ou_sem_evidencia():
    cfg = Config()
    sinais, _, _ = aplicar_identidade(
        [_sinal_coluna(f"BC1:{i}", "BC1_VAB") for i in range(4)], "BC1", [], cfg
    )
    assert aviso_divergencia_sheet("BC1", sinais, cfg) is None  # coerente
    assert aviso_divergencia_sheet("BC2", [], cfg) is None      # sem módulo por coluna
