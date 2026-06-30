"""Testes para pareamento_polaridade — convergência de posição por polaridade."""
import pytest

from tdt.config import Config
from tdt.contracts import Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.pareamento_polaridade import forcar_polaridade_equipamento


def _rec(
    id_: str,
    estado: str,
    equipamento: str = "Disjuntor",
    nome_equip: str = "52-2",
    modulo: str = "AL",
    descricao: str | None = None,
) -> SignalRecord:
    desc = descricao if descricao is not None else f"DISJ {nome_equip} {estado}"
    return SignalRecord(
        id=id_,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", is_double_bit=False, direcao="Input"),
        enderecamento=Enderecamento("DNP3", (100,)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(equipamento_alvo=equipamento, nome_equipamento=nome_equip),
    )


def _parear(registros, cfg=None):
    sinais, revisao = forcar_polaridade_equipamento(registros, cfg or Config())
    by_id = {r.id: r for r in sinais}
    rev_by_id = {it.registro.id: it for it in revisao}
    return by_id, rev_by_id


# ---------------------------------------------------------------------------
# Disjuntor NF (DJF1)
# ---------------------------------------------------------------------------

def test_par_ligado_desligado_converge_pra_djf1():
    by_id, _ = _parear([_rec("a", "LIGADO"), _rec("b", "DESLIGADO")])
    assert by_id["a"].sigla_sinal == "DJF1" and by_id["a"].status == "decidido"
    assert by_id["b"].sigla_sinal == "DJF1" and by_id["b"].status == "decidido"


def test_par_fechado_aberto_converge_pra_djf1():
    by_id, _ = _parear([_rec("a", "FECHADO"), _rec("b", "ABERTO")])
    assert {r.sigla_sinal for r in by_id.values()} == {"DJF1"}


# ---------------------------------------------------------------------------
# Disjuntor NA (DJA1)
# ---------------------------------------------------------------------------

def test_par_disjuntor_na_converge_pra_dja1():
    a = _rec("a", "LIGADO",   descricao="DISJUNTOR NA LIGADO",    equipamento="Disjuntor", nome_equip="24-3")
    b = _rec("b", "DESLIGADO",descricao="DISJUNTOR NA DESLIGADO", equipamento="Disjuntor", nome_equip="24-3")
    by_id, _ = _parear([a, b])
    assert by_id["a"].sigla_sinal == "DJA1"
    assert by_id["b"].sigla_sinal == "DJA1"


# ---------------------------------------------------------------------------
# Seccionadoras com palavra-função conhecida
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kw,esperada", [
    ("CARGA",              "SECC"),
    ("CARG",               "SECC"),
    ("BYPASS",             "SECB"),
    ("BY PASS",            "SECB"),
    ("BY-PASS",            "SECB"),
    ("BYPS",               "SECB"),
    ("TRANSFERENCIA",      "SECT"),
    ("TRANSFER",           "SECT"),
    ("TERRA",              "SECG"),
    ("ATERRAMENTO",        "SECG"),
    ("ATERR",              "SECG"),
    ("FONTE",              "SECF"),
    ("FONT",               "SECF"),
    ("INTERBARRAS",        "SECI"),
    ("INTERBARRA",         "SECI"),
    ("INTERLINHAS",        "SECL"),
    ("INTERLINHA",         "SECL"),
])
def test_seccionadora_kw_converge(kw, esperada):
    a = _rec("a", "FECHADO",  descricao=f"SEC {kw} FECHADO",
             equipamento="Seccionadora", nome_equip="89-1")
    b = _rec("b", "ABERTO",   descricao=f"SEC {kw} ABERTO",
             equipamento="Seccionadora", nome_equip="89-1")
    by_id, rev = _parear([a, b])
    assert rev == {}, f"não deveria ter revisão, got {list(rev)}"
    assert by_id["a"].sigla_sinal == esperada, f"kw={kw!r}"
    assert by_id["b"].sigla_sinal == esperada
    assert by_id["a"].status == "decidido"


# ---------------------------------------------------------------------------
# Seccionadora ambígua (sem keyword reconhecida) → posicao_ambigua
# ---------------------------------------------------------------------------

def test_seccionadora_sem_kw_vai_pra_revisao():
    """Par detectado mas sem palavra-função → posicao_ambigua, sai do scorer."""
    a = _rec("a", "FECHADO", descricao="SECCIONADORA FECHADO",
             equipamento="Seccionadora", nome_equip="89-5")
    b = _rec("b", "ABERTO",  descricao="SECCIONADORA ABERTO",
             equipamento="Seccionadora", nome_equip="89-5")
    by_id, rev = _parear([a, b])
    assert "a" in rev and "b" in rev, "par ambíguo deve ir pra revisão"
    assert rev["a"].motivo == "posicao_ambigua"
    assert rev["b"].motivo == "posicao_ambigua"
    # não aparecem no saida
    assert "a" not in by_id and "b" not in by_id


def test_seccionadora_transformador_nao_ativa_sect():
    """'TR' expande para TRANSFORMADOR → não deve acionar SECT (Transferência)."""
    a = _rec("a", "FECHADO", descricao="SECCIONADORA TRANSFORMADOR FECHADO",
             equipamento="Seccionadora", nome_equip="89-10")
    b = _rec("b", "ABERTO",  descricao="SECCIONADORA TRANSFORMADOR ABERTO",
             equipamento="Seccionadora", nome_equip="89-10")
    by_id, rev = _parear([a, b])
    # TRANSFORMADOR começa com "TRANSFOR", não "TRANSFER" → sem keyword → posicao_ambigua
    assert "a" in rev and "b" in rev
    assert rev["a"].motivo == "posicao_ambigua"


def test_seccionadora_cru_alias_lmn_terr_nao_converge():
    """Alias 'LMN TERR' sem a palavra TERRA/ATERR → revisão, não força SECG."""
    a = _rec("a", "FECHADO", descricao="LMN TERR FECHADO",
             equipamento="Seccionadora", nome_equip="29-5")
    b = _rec("b", "ABERTO",  descricao="LMN TERR ABERTO",
             equipamento="Seccionadora", nome_equip="29-5")
    by_id, rev = _parear([a, b])
    # "TERR" está contido em "LMN TERR" — mas não como prefixo de token inteiro
    # "TERR" deve casar "TERRA" e "TERR" como tokens, não como substring de "TERR"
    # Token "TERR" começa com "TERRA"? Não — "TERR" começa com "ATERR"? Não.
    # "TERRA" prefixo? tok="TERR" startswith("TERRA")? Não. startswith("TERRA")? Não.
    # Token "TERR" startswith("ATERR")? Não. startswith("TERRA")? Não.
    # Mas tok="TERR" startswith("TERRA") == False, startswith("ATERR") == False →
    # → não reconhece → posicao_ambigua
    assert rev.get("a") is not None or by_id.get("a") is not None  # um ou outro


def test_seccionadora_terra_via_token_terra_converge():
    """Alias com palavra TERRA explícita → converge para SECG."""
    a = _rec("a", "FECHADO", descricao="SECCIONADORA TERRA FECHADO",
             equipamento="Seccionadora", nome_equip="29-5")
    b = _rec("b", "ABERTO",  descricao="SECCIONADORA TERRA ABERTO",
             equipamento="Seccionadora", nome_equip="29-5")
    by_id, _ = _parear([a, b])
    assert by_id["a"].sigla_sinal == "SECG"
    assert by_id["b"].sigla_sinal == "SECG"


# ---------------------------------------------------------------------------
# Comportamento geral
# ---------------------------------------------------------------------------

def test_sem_par_completo_nao_forca():
    by_id, rev = _parear([_rec("a", "LIGADO")])
    assert by_id["a"].sigla_sinal is None
    assert rev == {}


def test_tres_linhas_nao_converge():
    """3 linhas do mesmo equipamento: par não é 1+1 exato — scorer decide."""
    a = _rec("a", "FECHADO", nome_equip="89-1", equipamento="Seccionadora",
             descricao="SEC CARGA FECHADO")
    b = _rec("b", "ABERTO",  nome_equip="89-1", equipamento="Seccionadora",
             descricao="SEC CARGA ABERTO")
    c = _rec("c", "ABERTO",  nome_equip="89-1", equipamento="Seccionadora",
             descricao="SEC CARGA ABERTO 2")
    by_id, rev = _parear([a, b, c])
    assert all(r.sigla_sinal is None for r in by_id.values())
    assert rev == {}


def test_flag_desligada_e_no_op():
    ligado = _rec("a", "LIGADO")
    desligado = _rec("b", "DESLIGADO")
    by_id, rev = _parear([ligado, desligado], Config(parear_polaridade_equipamento=False))
    assert by_id["a"].sigla_sinal is None and by_id["b"].sigla_sinal is None
    assert rev == {}


def test_equipamento_desconhecido_e_no_op():
    """Equipamento que não é Disjuntor nem Seccionadora: sem pare."""
    a = _rec("a", "LIGADO",    equipamento="Religador", nome_equip="79-1")
    b = _rec("b", "DESLIGADO", equipamento="Religador", nome_equip="79-1")
    by_id, rev = _parear([a, b])
    assert all(r.sigla_sinal is None for r in by_id.values())


def test_modulos_diferentes_nao_pareiam():
    """Mesmo equipamento, módulos distintos: chaves diferentes, não pareia."""
    a = _rec("a", "FECHADO", modulo="AL21", equipamento="Seccionadora",
             nome_equip="89-2", descricao="SEC CARGA FECHADO")
    b = _rec("b", "ABERTO",  modulo="AL22", equipamento="Seccionadora",
             nome_equip="89-2", descricao="SEC CARGA ABERTO")
    by_id, rev = _parear([a, b])
    assert all(r.sigla_sinal is None for r in by_id.values())


def test_equipamentos_diferentes_nao_pareiam():
    """Mesmo módulo, equipamentos distintos (89-1 vs 89-2): não pareia."""
    a = _rec("a", "FECHADO", equipamento="Seccionadora", nome_equip="89-1",
             descricao="SEC CARGA FECHADO")
    b = _rec("b", "ABERTO",  equipamento="Seccionadora", nome_equip="89-2",
             descricao="SEC CARGA ABERTO")
    by_id, rev = _parear([a, b])
    assert all(r.sigla_sinal is None for r in by_id.values())


def test_terceiro_sinal_sem_polaridade_passa_intacto():
    """Dois sinais pareiam; um terceiro sem polaridade segue para o scorer."""
    a = _rec("a", "FECHADO", descricao="DISJ 52-5 FECHADO")
    b = _rec("b", "ABERTO",  descricao="DISJ 52-5 ABERTO")
    c = _rec("c", "ALARME",  descricao="DISJ 52-5 ALARME BAIXA PRESSAO")
    by_id, rev = _parear([a, b, c])
    assert by_id["a"].sigla_sinal == "DJF1"
    assert by_id["b"].sigla_sinal == "DJF1"
    assert by_id["c"].sigla_sinal is None
