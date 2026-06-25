from tdt.config import Config
from tdt.contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.pareamento_polaridade import forcar_polaridade_equipamento


def _rec(id_, estado: str, equipamento="Disjuntor", nome_equip="52-2", modulo="AL"):
    return SignalRecord(
        id=id_,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", is_double_bit=False, direcao="Input"),
        enderecamento=Enderecamento("DNP3", (100,)),
        descricoes=Descricoes(f"DISJ {nome_equip} {estado}", estado),
        eletrico=Eletrico(equipamento_alvo=equipamento, nome_equipamento=nome_equip),
    )


def test_par_ligado_desligado_converge_pra_djf1():
    ligado = _rec("a", "LIGADO")
    desligado = _rec("b", "DESLIGADO")
    saida = forcar_polaridade_equipamento([ligado, desligado], Config())
    by_id = {r.id: r for r in saida}
    assert by_id["a"].sigla_sinal == "DJF1" and by_id["a"].status == "decidido"
    assert by_id["b"].sigla_sinal == "DJF1" and by_id["b"].status == "decidido"


def test_par_aberto_fechado_tambem_converge():
    fechado = _rec("a", "FECHADO")
    aberto = _rec("b", "ABERTO")
    saida = forcar_polaridade_equipamento([fechado, aberto], Config())
    assert {r.sigla_sinal for r in saida} == {"DJF1"}


def test_sem_par_completo_nao_forca():
    ligado = _rec("a", "LIGADO")
    saida = forcar_polaridade_equipamento([ligado], Config())
    assert saida[0].sigla_sinal is None


def test_flag_desligada_e_no_op():
    ligado = _rec("a", "LIGADO")
    desligado = _rec("b", "DESLIGADO")
    cfg = Config(parear_polaridade_equipamento=False)
    saida = forcar_polaridade_equipamento([ligado, desligado], cfg)
    assert saida[0].sigla_sinal is None and saida[1].sigla_sinal is None


def test_equipamento_fora_da_tabela_e_no_op():
    ligado = _rec("a", "LIGADO", equipamento="Seccionadora", nome_equip="89-1")
    desligado = _rec("b", "DESLIGADO", equipamento="Seccionadora", nome_equip="89-1")
    saida = forcar_polaridade_equipamento([ligado, desligado], Config())
    assert saida[0].sigla_sinal is None and saida[1].sigla_sinal is None
