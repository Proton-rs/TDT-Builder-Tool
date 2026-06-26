from tdt.config import Config
from tdt.normalizador import (
    ContextoEstrutural,
    canonizar,
    corrigir_typos,
    expandir_abreviacoes,
    extrair_contexto_estrutural,
    normalizar,
    normalizar_unidades,
    remover_boilerplate,
    separar_ids_equipamento,
)

CFG = Config()


# --- normalizar (comportamento legado preservado) -------------------------


def test_maiuscula_e_remove_acentos():
    assert normalizar("Disjuntor não operação", CFG) == "DISJUNTOR NAO OPERACAO"


def test_colapsa_espacos():
    assert normalizar("XYZ    ABC", CFG) == "XYZ ABC"


def test_separadores_viram_espaco():
    # "/-." viram espaço; depois DJ e BC expandem
    assert normalizar("DJ/BC-2", CFG) == "DISJUNTOR BANCO CAPACITORES 2"


def test_expande_abreviacao_whole_token():
    assert normalizar("DJ", CFG) == "DISJUNTOR"


def test_nao_quebra_sigla():
    # DJF1 NÃO deve expandir o "DJ" interno
    assert normalizar("DJF1", CFG) == "DJF1"
    assert normalizar("67N", CFG) == "67N"


def test_remove_stopwords():
    assert normalizar("DJ DE BC", CFG) == "DISJUNTOR BANCO CAPACITORES"


def test_vazio():
    assert normalizar("", CFG) == ""
    assert normalizar(None, CFG) == ""


# --- N1: abreviações extra ------------------------------------------------


def test_n1_abreviacoes_extra_disj():
    assert expandir_abreviacoes("DISJ", CFG) == "DISJUNTOR"


def test_n1_abreviacoes_extra_varias():
    assert expandir_abreviacoes("SECC", CFG) == "SECCIONADORA"
    assert expandir_abreviacoes("TRAFO", CFG) == "TRANSFORMADOR"
    assert expandir_abreviacoes("REL", CFG) == "RELE"


def test_n1_whole_token_nao_quebra_sigla():
    # "RELE" como substring de "RELE1" não pode expandir
    assert expandir_abreviacoes("RELE1", CFG) == "RELE1"


def test_n1_config_tem_prioridade():
    cfg = Config(abreviacoes={"DISJ": "FOO"})
    # config sobrescreve o ABREVIACOES_EXTRA
    assert expandir_abreviacoes("DISJ", cfg) == "FOO"


# --- N2: separação de IDs de equipamento ----------------------------------


def test_n2_nao_trata_id_hifenado_isso_e_job_do_n0():
    # IDs hifenados (52-1) são extraídos em N0 (extrair_contexto_estrutural),
    # sobre o texto bruto, antes do hífen virar espaço. N2 só lida com
    # IDs letra-número (01Q0) — chamado diretamente com hífen ainda intacto,
    # N2 não tem regra pra isso e não toca no texto.
    texto, ctx = separar_ids_equipamento("52-1 BAIXA PRESSAO", CFG)
    assert "52-1" in texto
    assert ctx == ""


def test_n2_remove_id_q():
    texto, ctx = separar_ids_equipamento("01Q0 ALARME", CFG)
    assert "01Q0" not in texto
    assert "01Q0" in ctx


def test_n2_preserva_funcao_protecao():
    texto, _ = separar_ids_equipamento("67 87 50N 59 27", CFG)
    for fn in ("67", "87", "50N", "59", "27"):
        assert fn in texto.split()


def test_n2_gate_desligado():
    cfg = Config(remover_ids_equipamento=False)
    texto, ctx = separar_ids_equipamento("01Q0 ALARME", cfg)
    assert texto == "01Q0 ALARME"
    assert ctx == ""


# --- N3: boilerplate ------------------------------------------------------


def test_n3_remove_prefixo_equipamento():
    bruto = "DISJUNTOR BAIXA PRESSAO SF6 BLOQUEIO"
    # prefixo de equipamento curto não some se não houver separador/descrição
    out = remover_boilerplate(bruto, CFG)
    assert "BAIXA PRESSAO SF6 BLOQUEIO" in out


def test_n3_mantem_nucleo_apos_separador():
    bruto = "DISJUNTOR - BAIXA PRESSAO SF6 BLOQUEIO"
    out = remover_boilerplate(bruto, CFG)
    assert "BAIXA" in out
    assert "SF6" in out


# --- N4: typos ------------------------------------------------------------


def test_n4_corrige_typo_uma_edicao():
    vocab = {"CORRENTE", "DESBALANCO"}
    out = corrigir_typos("CORRETNTE DESBALANCO", CFG, vocab)
    assert "CORRENTE" in out.split()


def test_n4_nao_corrige_sigla_curta():
    vocab = {"CORRENTE"}
    out = corrigir_typos("67N SF6 DJF1 50N", CFG, vocab)
    assert out.split() == ["67N", "SF6", "DJF1", "50N"]


def test_n4_gate_desligado():
    cfg = Config(corrigir_typos=False)
    vocab = {"CORRENTE"}
    assert corrigir_typos("CORRETNTE", cfg, vocab) == "CORRETNTE"


def test_n4_sem_vocab_nao_altera():
    assert corrigir_typos("CORRETNTE", CFG, None) == "CORRETNTE"
    assert corrigir_typos("CORRETNTE", CFG, set()) == "CORRETNTE"


# --- N5: unidades ---------------------------------------------------------


def test_n5_normaliza_kv():
    assert normalizar_unidades("138 KV").split() == ["138", "KV"]
    assert normalizar_unidades("138 Kv").split() == ["138", "KV"]
    assert normalizar_unidades("138 kV").split() == ["138", "KV"]


def test_n5_normaliza_amp():
    assert "A" in normalizar_unidades("CORRENTE AMP").split()


def test_n5_normaliza_mw():
    assert "MW" in normalizar_unidades("100 Mw").split()


# --- canonizar (ponta a ponta) --------------------------------------------


def test_canonizar_retrocompativel_sem_vocab():
    # quem já chama canonizar(texto, cfg) continua funcionando (assinatura)
    out = canonizar("ALARME DISJUNTOR DJ", CFG)
    assert isinstance(out, str)
    assert "DISJUNTOR" in out.split()


def test_canonizar_boilerplate_ponta_a_ponta():
    bruto = "Disj. 52-1 (01Q0) - Baixa Pressão SF6 - Bloqueio"
    out = canonizar(bruto, CFG)
    assert "52-1" not in out
    assert "01Q0" not in out
    assert "SF6" in out.split()
    assert "BAIXA" in out.split()
    assert "PRESSAO" in out.split()
    assert "BLOQUEIO" in out.split()


def test_canonizar_typo_com_vocab():
    vocab = {"CORRENTE", "DESBALANCO"}
    out = canonizar("Corretnte de Desbalanço", CFG, vocab=vocab)
    assert "CORRENTE" in out.split()


def test_canonizar_siglas_nunca_quebradas():
    bruto = "67N DJF1 SF6 50N 67 N 1"
    out = canonizar(bruto, CFG).split()
    for sigla in ("67N", "DJF1", "SF6", "50N", "67N1"):
        assert sigla in out


# --- N0: extração estrutural (SP6) -----------------------------------------


def test_extrai_equipamento_disjuntor():
    texto, ctx = extrair_contexto_estrutural("DISJUNTOR 52-1 ABERTO")
    assert ctx.equipamento_alvo == "Disjuntor"
    assert "52-1" not in texto
    assert "52" not in texto.split()
    assert "1" not in texto.split()


def test_extrai_equipamento_seccionadora():
    texto, ctx = extrair_contexto_estrutural("SECCIONADORA 89-3 FECHADA")
    assert ctx.equipamento_alvo == "Seccionadora"
    assert "89" not in texto.split()


def test_codigo_fora_da_tabela_remove_mas_nao_classifica():
    texto, ctx = extrair_contexto_estrutural("RELE 67-1 ATUADO")
    assert ctx.equipamento_alvo is None
    assert "67" not in texto.split()


def test_extrai_nome_equipamento_bruto():
    _, ctx = extrair_contexto_estrutural("DISJUNTOR 52-2 DESLIGADO")
    assert ctx.nome_equipamento == "52-2"


def test_nome_equipamento_none_sem_id():
    _, ctx = extrair_contexto_estrutural("CORRENTE FASE A")
    assert ctx.nome_equipamento is None


def test_equipamento_pela_palavra_quando_id_nao_e_ansi():
    # "24-1" não é código ANSI (só 52/89/29), mas a palavra DISJUNTOR resolve.
    # Sem isso, o forçamento DJF1 (pareamento_polaridade) não dispara.
    _, ctx = extrair_contexto_estrutural("24-1 DISJUNTOR FECHADO")
    assert ctx.equipamento_alvo == "Disjuntor"
    assert ctx.nome_equipamento == "24-1"
    _, ctx2 = extrair_contexto_estrutural("DJ 24-1 ABERTO")
    assert ctx2.equipamento_alvo == "Disjuntor"


def test_sec_sozinho_nao_confunde_secundario():
    _, ctx = extrair_contexto_estrutural("TENSAO SECUNDARIO BARRA")
    assert ctx.equipamento_alvo is None


def test_sem_id_de_equipamento_nao_extrai_nada():
    texto, ctx = extrair_contexto_estrutural("FALHA COMUNICACAO")
    assert ctx == ContextoEstrutural()
    assert texto == "FALHA COMUNICACAO"


def test_extrai_barra_principal():
    texto, ctx = extrair_contexto_estrutural("TENSAO BARRA P FASES AB")
    assert ctx.barra == "Principal"
    assert "P" not in texto.split()


def test_extrai_barra_auxiliar():
    texto, ctx = extrair_contexto_estrutural("TENSAO BARRA A")
    assert ctx.barra == "Auxiliar"


def test_letra_p_sem_marcador_barra_nao_e_barra():
    texto, ctx = extrair_contexto_estrutural("POTENCIA P TOTAL")
    assert ctx.barra is None


def test_extrai_fase_letra_unica():
    texto, ctx = extrair_contexto_estrutural("CORRENTE FASE A")
    assert ctx.fase == "A"
    assert "A" not in texto.split()


def test_extrai_fase_dupla():
    texto, ctx = extrair_contexto_estrutural("TENSAO FASE AB")
    assert ctx.fase == "AB"


def test_extrai_fase_neutro():
    texto, ctx = extrair_contexto_estrutural("CORRENTE NEUTRO")
    assert ctx.fase == "N"


def test_extrai_fase_trifasico():
    texto, ctx = extrair_contexto_estrutural("TENSAO TRIFASICA")
    assert ctx.fase == "ABC"


def test_sem_fase_no_texto():
    texto, ctx = extrair_contexto_estrutural("FALHA COMUNICACAO")
    assert ctx.fase is None


def test_parenteses_e_pontuacao_extra_virram_espaco():
    cfg = Config()
    assert normalizar("DISJUNTOR (52-1) ABERTO, FECHADO; TESTE: OK", cfg) == \
        "DISJUNTOR 52 1 ABERTO FECHADO TESTE OK"
