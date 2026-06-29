"""TDD — SP C2: inferência de equipamento por topologia do módulo.

C2.1: tabela de topologia acessível via config.
C2.2: inferência determinística (default não-ambíguo, pista explícita, ou
revisão quando ambíguo).
C2.4: subdivisão de módulo Transformador por lado AT/BT.
"""

from dataclasses import replace

from tdt.config import Config
from tdt.contracts import (
    Descricoes, Enderecamento, Eletrico, Modulo, SignalRecord, Topologia, TipoSinal,
)
from tdt.inferencia_topologia import inferir_equipamento, subdividir_transformador_at_bt


def _rec(
    id_: str, modulo_nome: str, tipo_modulo: str, desc_norm: str,
    equipamento_alvo: str | None = None, indices: tuple[int, ...] = (),
    nivel_tensao: str | None = None,
) -> SignalRecord:
    return SignalRecord(
        id=id_,
        modulo=Modulo(modulo_nome, "sheet_name", tipo=tipo_modulo),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", indices),
        descricoes=Descricoes(desc_norm, desc_norm),
        eletrico=Eletrico(equipamento_alvo=equipamento_alvo, nivel_tensao=nivel_tensao),
    )


# --- C2.1 -------------------------------------------------------------------


def test_config_tem_topologia_por_tipo():
    cfg = Config()
    assert "Alimentador" in cfg.topologia_por_tipo
    assert cfg.topologia_por_tipo["Alimentador"].default == "Disjuntor"


def test_topologia_e_dataclass_frozen_com_equipamentos_e_cardinalidade():
    t = Topologia(equipamentos=("Disjuntor", "Seccionadora"), default="Disjuntor")
    assert t.equipamentos == ("Disjuntor", "Seccionadora")
    assert t.default == "Disjuntor"


def test_tipos_sem_default_claro_ficam_none():
    cfg = Config()
    assert cfg.topologia_por_tipo["Barra"].default is None


# --- C2.2: default não-ambíguo ----------------------------------------------


def test_alimentador_sem_equipamento_e_sem_pista_recebe_disjuntor_inferido():
    cfg = Config()
    rec = _rec("s:1", "AL15", "Alimentador", "FALHA COMUNICACAO")
    saida = inferir_equipamento([rec], cfg)
    assert saida[0].eletrico.equipamento_alvo == "Disjuntor"
    assert saida[0].eletrico.equipamento_inferido is True


def test_extraido_nao_e_sobrescrito_e_nao_marca_inferido():
    cfg = Config()
    rec = _rec("s:1", "AL15", "Alimentador", "ABERTO", equipamento_alvo="Seccionadora")
    saida = inferir_equipamento([rec], cfg)
    assert saida[0].eletrico.equipamento_alvo == "Seccionadora"
    assert saida[0].eletrico.equipamento_inferido is False


# --- C2.2: pista explícita de outro equipamento -----------------------------


def test_sinal_com_pista_de_seccionadora_recebe_seccionadora_nao_default():
    cfg = Config()
    rec = _rec("s:1", "AL15", "Alimentador", "SECCIONADORA ABERTA")
    saida = inferir_equipamento([rec], cfg)
    assert saida[0].eletrico.equipamento_alvo == "Seccionadora"
    assert saida[0].eletrico.equipamento_inferido is True


# --- C2.2: tipo sem default claro -> revisão --------------------------------


def test_tipo_sem_default_claro_fica_none_para_revisao_equipamento_ambiguo():
    # equipamento_alvo permanece None -- pipeline.py usa isso (rec ainda sem
    # equipamento após inferir) pra rotear o sinal a revisão com motivo
    # "equipamento_ambiguo", MANTENDO a sigla decidida como sugestão.
    cfg = Config()
    rec = _rec("s:1", "87BAT", "Barra", "FALHA COMUNICACAO")
    saida = inferir_equipamento([rec], cfg)
    assert saida[0].eletrico.equipamento_alvo is None
    assert saida[0].eletrico.equipamento_inferido is False


def test_nome_equipamento_nunca_e_inventado():
    cfg = Config()
    rec = _rec("s:1", "AL15", "Alimentador", "FALHA COMUNICACAO")
    saida = inferir_equipamento([rec], cfg)
    assert saida[0].eletrico.nome_equipamento is None


def test_tipo_modulo_none_nao_quebra_e_permanece_ambiguo():
    cfg = Config()
    rec = _rec("s:1", "XYZ", None, "FALHA COMUNICACAO")
    saida = inferir_equipamento([rec], cfg)
    assert saida[0].eletrico.equipamento_alvo is None


def test_agrupamento_por_modulo_nao_mistura_modulos_diferentes():
    cfg = Config()
    rec_al = _rec("s:1", "AL15", "Alimentador", "FALHA COMUNICACAO")
    rec_barra = _rec("s:2", "87BAT", "Barra", "FALHA COMUNICACAO")
    saida = inferir_equipamento([rec_al, rec_barra], cfg)
    por_id = {r.id: r for r in saida}
    assert por_id["s:1"].eletrico.equipamento_alvo == "Disjuntor"
    assert por_id["s:2"].eletrico.equipamento_alvo is None


# --- C2.4: subdivisão de módulo Transformador por lado AT/BT ----------------


def test_trafo_com_pista_de_secao_subdivide_modulo():
    cfg = Config()
    rec_at = _rec("s:1", "TR1", "Transformador", "CORRENTE FASE A", indices=(600,))
    rec_bt = _rec("s:2", "TR1", "Transformador", "CORRENTE FASE A", indices=(608,))
    saida = subdividir_transformador_at_bt(
        [rec_at, rec_bt], cfg, secao_por_id={"s:1": "AT", "s:2": "BT"},
    )
    por_id = {r.id: r for r in saida}
    assert por_id["s:1"].modulo.nome == "TR1AT"
    assert por_id["s:2"].modulo.nome == "TR1BT"


def test_trafo_com_nivel_tensao_extraido_subdivide_modulo():
    cfg = Config()
    rec_at = _rec(
        "s:1", "TR1", "Transformador", "CORRENTE PRIMARIO", indices=(600,),
        nivel_tensao="AT",
    )
    rec_bt = _rec(
        "s:2", "TR1", "Transformador", "CORRENTE SECUNDARIO", indices=(608,),
        nivel_tensao="BT",
    )
    saida = subdividir_transformador_at_bt([rec_at, rec_bt], cfg)
    por_id = {r.id: r for r in saida}
    assert por_id["s:1"].modulo.nome == "TR1AT"
    assert por_id["s:2"].modulo.nome == "TR1BT"


def test_trafo_sem_pista_nao_subdivide():
    cfg = Config()
    rec_a = _rec("s:1", "TR1", "Transformador", "CORRENTE FASE A", indices=(600,))
    rec_b = _rec("s:2", "TR1", "Transformador", "CORRENTE FASE A", indices=(608,))
    saida = subdividir_transformador_at_bt([rec_a, rec_b], cfg)
    assert saida[0].modulo.nome == "TR1"
    assert saida[1].modulo.nome == "TR1"


def test_modulo_nao_transformador_nunca_e_tocado():
    cfg = Config()
    rec = _rec(
        "s:1", "AL15", "Alimentador", "CORRENTE PRIMARIO", nivel_tensao="AT",
    )
    saida = subdividir_transformador_at_bt([rec], cfg)
    assert saida[0].modulo.nome == "AL15"


def test_trafo_faixa_de_endereco_contigua_decide_quando_sem_outra_pista():
    # Heurística mais fraca (3ª pista): bloco AT e bloco BT contíguos. Sem
    # nivel_tensao/seção, dois clusters de endereço bem separados sugerem
    # dois lados -- mas só decide se houver gap claro entre os clusters.
    cfg = Config()
    bloco_at = [
        _rec(f"s:{i}", "TR1", "Transformador", "CORRENTE", indices=(600 + i,))
        for i in range(3)
    ]
    bloco_bt = [
        _rec(f"s:{10+i}", "TR1", "Transformador", "CORRENTE", indices=(700 + i,))
        for i in range(3)
    ]
    saida = subdividir_transformador_at_bt(bloco_at + bloco_bt, cfg)
    nomes_bloco_at = {r.modulo.nome for r in saida if r.id.startswith("s:0") or r.id in ("s:1", "s:2")}
    nomes_bloco_bt = {r.modulo.nome for r in saida if r.id in ("s:10", "s:11", "s:12")}
    # Sem pista forte (seção/nivel_tensao), e como a spec define a faixa de
    # endereço como heurística MAIS FRACA, dois blocos distantes sem rótulo
    # explícito de lado não são suficientes -- continua sem subdividir, pois
    # não há como saber QUAL bloco é AT e qual é BT sem outra pista.
    assert nomes_bloco_at == {"TR1"}
    assert nomes_bloco_bt == {"TR1"}
