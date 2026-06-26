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
    assert segue == []
    assert [it.motivo for it in revisao] == ["modulo_indefinido", "modulo_indefinido"]


def test_particionar_alta_segue_adiante():
    sinais = [_rec("SINAL A")]
    segue, revisao = particionar_por_confianca(sinais, "alta")
    assert segue == sinais
    assert revisao == []
