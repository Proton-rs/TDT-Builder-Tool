from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Eletrico, Enderecamento, GrandezasAnalogicas,
    Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais, _EDITAVEIS, _MOTIVO_LABEL


def _rec(status="decidido", sigla="DJF1", eletrico=None):
    return SignalRecord(
        id="a:1", modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("Falha DJ 52-1", "FALHA DJ"),
        sigla_sinal=sigla, status=status,
        candidatos=(Candidato(sigla, 0.87, "mesclado"),) if sigla else (),
        diagnostico=Diagnostico({sigla: {"tfidf": 0.91, "vetorial": 0.84, "fuzzy": 0.72}}) if sigla else None,
        eletrico=eletrico if eletrico is not None else Eletrico(),
    )


def _state(rec):
    st = AppState()
    st.registros = [rec]
    st.lista_padrao = ListaPadraoADMS(
        (SinalPadrao("DJF1", "Disjuntor falha função 1", "BISI", None, None, "Discrete"),), ())
    return st


def _col(nome):
    return ModeloSinais.COLUNAS.index(nome)


def test_dimensoes_e_header(qtbot):
    m = ModeloSinais(_state(_rec()))
    assert m.rowCount() == 1
    assert m.columnCount() == len(ModeloSinais.COLUNAS)
    assert m.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Sinal ✎"


def test_sheets_distintas_deriva_do_id_e_ordena(qtbot):
    st = AppState()
    st.registros = [
        replace(_rec(), id="Discreto:0"),
        replace(_rec(), id="Analogicos:0"),
        replace(_rec(), id="Discreto:1"),
    ]
    m = ModeloSinais(st)
    assert m.sheets_distintas() == ["Analogicos", "Discreto"]


def test_sheets_distintas_ignora_id_sem_sheet(qtbot):
    st = AppState()
    st.registros = [replace(_rec(), id="manual_abc123")]
    m = ModeloSinais(st)
    assert m.sheets_distintas() == []


def test_colunas_novas_e_sem_duplicata():
    cols = ModeloSinais.COLUNAS
    assert "Descr. ADMS" in cols
    assert "Descr. normalizada" in cols
    assert "Tokens" in cols
    assert "Motivo" in cols
    assert "TKN bruto" not in cols


def test_coluna_motivo_mostra_label_amigavel():
    st = _state(_rec())
    st.resultado = type("R", (), {"revisao": (
        type("Item", (), {"registro": st.registros[0], "motivo": "score_baixo"})(),
    )})()
    m = ModeloSinais(st)
    v = m.data(m.index(0, _col("Motivo")), Qt.DisplayRole)
    assert v == "Score baixo"


def test_coluna_motivo_traco_para_decidido_sem_entrada_em_revisao():
    m = ModeloSinais(_state(_rec()))  # sem resultado/revisao -> nao tem motivo
    v = m.data(m.index(0, _col("Motivo")), Qt.DisplayRole)
    assert v == "—"


def test_descr_adms_vem_da_lista_padrao():
    m = ModeloSinais(_state(_rec()))
    v = m.data(m.index(0, _col("Descr. ADMS")), Qt.DisplayRole)
    assert v == "Disjuntor falha função 1"


def test_tokens_exibe_normalizada_tokenizada():
    m = ModeloSinais(_state(_rec()))
    v = m.data(m.index(0, _col("Tokens")), Qt.DisplayRole)
    assert v == "FALHA·DJ"


def test_score_embedding():
    m = ModeloSinais(_state(_rec()))
    v = m.data(m.index(0, _col("Score embedding")), Qt.DisplayRole)
    assert "0.84" in str(v)


def test_status_tem_cor_foreground():
    m = ModeloSinais(_state(_rec(status="revisao", sigla=None)))
    cor = m.data(m.index(0, _col("Status")), Qt.ForegroundRole)
    assert isinstance(cor, QColor)


def test_tooltip_sinal_usa_descricao_adms():
    m = ModeloSinais(_state(_rec()))
    tip = m.data(m.index(0, _col("Sinal")), Qt.ToolTipRole)
    assert "Disjuntor falha" in tip


def test_definir_sigla_atualiza():
    st = _state(_rec())
    m = ModeloSinais(st)
    m.definir_sigla(0, "DJF2")
    assert st.registros[0].sigla_sinal == "DJF2"
    assert m.data(m.index(0, _col("Sinal")), Qt.DisplayRole) == "DJF2"


def test_colunas_equipamento_eletrico_existem_sem_duplicar_fase():
    cols = ModeloSinais.COLUNAS
    assert cols.count("Fase") == 1
    for nome in ("Módulo", "Equipamento", "Tipo Equip.", "Barra", "Nível Tensão"):
        assert nome in cols


def test_colunas_equipamento_eletrico_mostram_valores_populados():
    eletrico = Eletrico(
        fase="A", nivel_tensao="AT", equipamento_alvo="Disjuntor",
        nome_equipamento="52-10", barra="Principal",
    )
    m = ModeloSinais(_state(_rec(eletrico=eletrico)))
    assert m.data(m.index(0, _col("Módulo")), Qt.DisplayRole) == "M"
    assert m.data(m.index(0, _col("Equipamento")), Qt.DisplayRole) == "52-10"
    assert m.data(m.index(0, _col("Tipo Equip.")), Qt.DisplayRole) == "Disjuntor"
    assert m.data(m.index(0, _col("Barra")), Qt.DisplayRole) == "Principal"
    assert m.data(m.index(0, _col("Nível Tensão")), Qt.DisplayRole) == "AT"


def test_colunas_equipamento_eletrico_fallback_traco_quando_vazio():
    m = ModeloSinais(_state(_rec(eletrico=Eletrico())))
    assert m.data(m.index(0, _col("Equipamento")), Qt.DisplayRole) == "—"
    assert m.data(m.index(0, _col("Tipo Equip.")), Qt.DisplayRole) == "—"
    assert m.data(m.index(0, _col("Barra")), Qt.DisplayRole) == "—"
    assert m.data(m.index(0, _col("Nível Tensão")), Qt.DisplayRole) == "—"


def test_coluna_modulo_fallback_traco_quando_sem_nome():
    rec = _rec()
    rec = rec.__class__(**{**rec.__dict__, "modulo": Modulo(None, "linha")})
    st = _state(rec)
    m = ModeloSinais(st)
    assert m.data(m.index(0, _col("Módulo")), Qt.DisplayRole) == "—"


def test_adicionar_registro_aumenta_rowcount_e_anexa_no_fim():
    st = _state(_rec())
    m = ModeloSinais(st)
    novo = SignalRecord(
        id="manual_1", modulo=Modulo(None, "manual"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", ()),
        descricoes=Descricoes("", ""),
    )
    m.adicionar_registro(novo)
    assert m.rowCount() == 2
    assert st.registros[-1] is novo


def test_adicionar_registro_emite_sinais_de_insercao(qtbot):
    st = _state(_rec())
    m = ModeloSinais(st)
    novo = SignalRecord(
        id="manual_1", modulo=Modulo(None, "manual"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", ()),
        descricoes=Descricoes("", ""),
    )
    with qtbot.waitSignal(m.rowsInserted, timeout=1000):
        m.adicionar_registro(novo)


def test_remover_linhas_reduz_rowcount_e_remove_o_registro():
    rec1 = _rec()
    st = _state(rec1)
    rec2 = SignalRecord(
        id="a:2", modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (11,)),
        descricoes=Descricoes("d2", "D2"),
    )
    st.registros.append(rec2)
    m = ModeloSinais(st)
    assert m.rowCount() == 2
    m.remover_linhas([0])
    assert m.rowCount() == 1
    assert st.registros[0] is rec2


def test_remover_linhas_multiplas_indices_fora_de_ordem():
    st = _state(_rec())
    for i in range(2, 5):
        st.registros.append(SignalRecord(
            id=f"a:{i}", modulo=Modulo("M", "sheet_name"),
            tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
            enderecamento=Enderecamento("DNP3", (i,)),
            descricoes=Descricoes(f"d{i}", f"D{i}"),
        ))
    m = ModeloSinais(st)
    assert m.rowCount() == 4
    m.remover_linhas([0, 2])  # remove índices 0 e 2 (fora de ordem)
    assert m.rowCount() == 2
    ids_restantes = {r.id for r in st.registros}
    assert ids_restantes == {"a:2", "a:4"}


def test_remover_linhas_emite_sinais_de_remocao(qtbot):
    rec1 = _rec()
    st = _state(rec1)
    st.registros.append(SignalRecord(
        id="a:2", modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (11,)),
        descricoes=Descricoes("d2", "D2"),
    ))
    m = ModeloSinais(st)
    with qtbot.waitSignal(m.rowsRemoved, timeout=1000):
        m.remover_linhas([0])


def test_flags_colunas_dominio_sao_editaveis():
    m = ModeloSinais(_state(_rec()))
    for nome in ("Sinal", "Tipo", "Fase", "Nível Tensão", "Barra",
                 "Tipo Equip.", "Módulo", "Escala", "Endereço", "Endereço Output",
                 "Equipamento", "Descr. bruta"):
        flags = m.flags(m.index(0, _col(nome)))
        assert flags & Qt.ItemIsEditable, nome


def test_flags_colunas_derivadas_nao_sao_editaveis():
    m = ModeloSinais(_state(_rec()))
    for nome in ("Status", "Motivo", "Descr. ADMS", "Score tf-idf",
                 "Justificativa", "Descr. normalizada", "Tokens", "Confiança",
                 "Pareado", "Sheet origem"):
        flags = m.flags(m.index(0, _col(nome)))
        assert not (flags & Qt.ItemIsEditable), nome


def test_set_data_fase_atualiza_estado_e_emite_data_changed(qtbot):
    st = _state(_rec())
    m = ModeloSinais(st)
    idx = m.index(0, _col("Fase"))
    with qtbot.waitSignal(m.dataChanged, timeout=1000):
        ok = m.setData(idx, "B", Qt.EditRole)
    assert ok is True
    assert st.registros[0].eletrico.fase == "B"


def test_set_data_tipo_faz_split_categoria_direcao():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Tipo")), "Analog/Output", Qt.EditRole)
    assert ok is True
    assert st.registros[0].tipo_sinal.categoria == "Analog"
    assert st.registros[0].tipo_sinal.direcao == "Output"


def test_set_data_tipo_sem_barra_retorna_false():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Tipo")), "Discrete", Qt.EditRole)
    assert ok is False


def test_set_data_escala_converte_texto_com_virgula_para_float():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Escala")), "1,5", Qt.EditRole)
    assert ok is True
    assert st.registros[0].grandezas_analogicas.escala_transmissao == 1.5


def test_set_data_escala_vazio_limpa_valor():
    st = _state(_rec())
    st.registros[0] = replace(
        st.registros[0],
        grandezas_analogicas=GrandezasAnalogicas(escala_transmissao=3.0),
    )
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Escala")), "", Qt.EditRole)
    assert ok is True
    assert st.registros[0].grandezas_analogicas.escala_transmissao is None


def test_set_data_escala_invalida_retorna_false_sem_mutar():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Escala")), "abc", Qt.EditRole)
    assert ok is False
    assert st.registros[0].grandezas_analogicas.escala_transmissao is None


def test_set_data_endereco_grava_indices():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Endereço")), "900;901", Qt.EditRole)
    assert ok is True
    assert st.registros[0].enderecamento.indices == (900, 901)


def test_set_data_endereco_output_grava_indices():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Endereço Output")), "902", Qt.EditRole)
    assert ok is True
    assert st.registros[0].enderecamento.indices_saida == (902,)


def test_set_data_endereco_invalido_retorna_false_sem_mutar():
    st = _state(_rec())
    m = ModeloSinais(st)
    antes = st.registros[0].enderecamento.indices
    ok = m.setData(m.index(0, _col("Endereço")), "abc", Qt.EditRole)
    assert ok is False
    assert st.registros[0].enderecamento.indices == antes
    ok = m.setData(m.index(0, _col("Endereço")), "70000", Qt.EditRole)
    assert ok is False
    assert st.registros[0].enderecamento.indices == antes


def test_set_data_coluna_nao_editavel_retorna_false():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Status")), "decidido", Qt.EditRole)
    assert ok is False


def test_equipamento_e_descr_bruta_editaveis():
    assert "Equipamento" in _EDITAVEIS
    assert "Descr. bruta" in _EDITAVEIS


def test_setdata_equipamento():
    st = _state(_rec())
    m = ModeloSinais(st)
    assert m.setData(m.index(0, _col("Equipamento")), "52-11", Qt.EditRole)
    assert st.registros[0].eletrico.nome_equipamento == "52-11"
    assert m.setData(m.index(0, _col("Equipamento")), "", Qt.EditRole)
    assert st.registros[0].eletrico.nome_equipamento is None


def test_setdata_descr_bruta_rejeita_vazio():
    st = _state(_rec())
    m = ModeloSinais(st)
    assert not m.setData(m.index(0, _col("Descr. bruta")), "  ", Qt.EditRole)
    assert m.setData(m.index(0, _col("Descr. bruta")), "NOVA DESC", Qt.EditRole)
    assert st.registros[0].descricoes.bruta == "NOVA DESC"


def test_valor_edicao_equipamento_nao_usa_sentinela_traco():
    """EditRole não pode devolver "—" (sentinela de exibição p/ vazio) --
    senão o round-trip abrir/fechar o editor sem mudar nada grava "—" como
    valor literal em vez de manter None (mesmo bug já evitado p/ Fase/Barra/
    Tipo Equip./Módulo em `_valor_edicao`)."""
    m = ModeloSinais(_state(_rec(eletrico=Eletrico())))
    assert m.data(m.index(0, _col("Equipamento")), Qt.DisplayRole) == "—"
    assert m.data(m.index(0, _col("Equipamento")), Qt.EditRole) == ""


def test_cor_faixa_novas_cores():
    from tdt.ui.modelo_tabela import cor_faixa
    assert cor_faixa(0.9).name() == "#35c48f"
    assert cor_faixa(0.5).name() == "#e0a83f"
    assert cor_faixa(0.1).name() == "#e0604c"


def test_font_role_monospace_so_em_colunas_de_dados(qtbot):
    from PySide6.QtGui import QFont
    st = _state(_rec())
    m = ModeloSinais(st)
    col_sinal = ModeloSinais.COLUNAS.index("Sinal")
    fonte = m.data(m.index(0, col_sinal), Qt.FontRole)
    assert fonte is not None and "Consolas" in fonte.family()
    col_status = ModeloSinais.COLUNAS.index("Status")
    assert m.data(m.index(0, col_status), Qt.FontRole) is None


def test_pendentes_por_sheet_conta_so_revisao(qtbot):
    st = AppState()
    st.registros = [
        replace(_rec("decidido", sigla="DJF1"), id="SAN2:1"),
        replace(_rec("revisao", sigla="DJF2"), id="SAN2:2"),
        replace(_rec("revisao", sigla="DJA1"), id="TRAFO:1"),
    ]
    modelo = ModeloSinais(st)
    assert modelo.pendentes_por_sheet() == {"SAN2": 1, "TRAFO": 1}


def test_contagem_por_sheet_pendentes_e_total(qtbot):
    st = AppState()
    st.registros = [
        replace(_rec("decidido", sigla="DJF1"), id="SAN2:1"),
        replace(_rec("revisao", sigla="DJF2"), id="SAN2:2"),
        replace(_rec("revisao", sigla="DJA1"), id="TRAFO:1"),
    ]
    modelo = ModeloSinais(st)
    assert modelo.contagem_por_sheet() == {"SAN2": (1, 2), "TRAFO": (1, 1)}


def test_texto_faixa_cores():
    from tdt.ui.modelo_tabela import texto_faixa
    assert texto_faixa(0.9).name() == "#0d2e21"
    assert texto_faixa(0.5).name() == "#2c2005"
    assert texto_faixa(0.1).name() == "#e8ebf2"
    assert texto_faixa(None) is None


def test_header_data_vertical_mostra_numero_da_linha(qtbot):
    m = ModeloSinais(_state(_rec()))
    assert m.headerData(0, Qt.Vertical, Qt.DisplayRole) == 1


def test_motivo_sem_label_exibe_motivo_cru():
    assert _MOTIVO_LABEL.get("motivo_futuro_desconhecido", "motivo_futuro_desconhecido") != "—"


def test_coluna_pareado():
    st = _state(_rec())
    m = ModeloSinais(st)
    st.registros[0] = replace(
        st.registros[0], tipo_sinal=TipoSinal("Discrete", "SingleBit", "InputOutput"))
    assert m.data(m.index(0, _col("Pareado")), Qt.DisplayRole) == "Sim"


def test_coluna_pareado_orfao_output_sem_indices():
    st = _state(_rec())
    m = ModeloSinais(st)
    st.registros[0] = replace(
        st.registros[0],
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Output"),
        enderecamento=Enderecamento("DNP3", ()))
    assert m.data(m.index(0, _col("Pareado")), Qt.DisplayRole) == "Órfão"


def test_coluna_pareado_input_puro():
    m = ModeloSinais(_state(_rec()))
    assert m.data(m.index(0, _col("Pareado")), Qt.DisplayRole) == "—"


def test_coluna_sheet_origem():
    st = _state(replace(_rec(), id="BC2:12"))
    m = ModeloSinais(st)
    assert m.data(m.index(0, _col("Sheet origem")), Qt.DisplayRole) == "BC2"


def test_todos_motivos_emitidos_tem_label():
    emitidos = {
        "sem_endereco", "score_baixo", "categoria_ambigua", "endereco_duplicado",
        "sem_fix", "modulo_indefinido", "nome_sigla_inconsistente",
        "qualificador_ambiguo", "pareamento_ambiguo", "comando_sem_discreto",
        "custom_id_duplicado", "posicao_ambigua", "comando_tap_nao_modelado",
        "decisao_por_projeto", "descartado_indefinido", "descartado_redundante",
    }
    assert emitidos <= set(_MOTIVO_LABEL)


def test_sem_endereco_nao_diz_futuro():
    assert "futuro" not in _MOTIVO_LABEL["sem_endereco"].lower()


def test_motivo_desconhecido_mostra_motivo_cru_na_coluna():
    st = _state(_rec())
    st.resultado = type("R", (), {"revisao": (
        type("Item", (), {"registro": st.registros[0], "motivo": "motivo_futuro_desconhecido"})(),
    )})()
    m = ModeloSinais(st)
    v = m.data(m.index(0, _col("Motivo")), Qt.DisplayRole)
    assert v == "motivo_futuro_desconhecido"


def test_roundtrip_edicao_nao_altera_valor():
    """Ler via EditRole e regravar o mesmo valor não pode mudar o dado
    exibido (reprodução headless do bug "double-click quebra formatação")."""
    st = _state(_rec())
    m = ModeloSinais(st)
    for nome in sorted(_EDITAVEIS - {"Sinal"}):
        idx = m.index(0, _col(nome))
        antes_display = m.data(idx, Qt.DisplayRole)
        antes_edit = m.data(idx, Qt.EditRole)
        m.setData(idx, antes_edit, Qt.EditRole)
        assert m.data(idx, Qt.DisplayRole) == antes_display, nome


def test_tooltip_motivo_traz_texto_explicativo():
    st = _state(_rec())
    st.resultado = type("R", (), {"revisao": (
        type("Item", (), {"registro": st.registros[0], "motivo": "score_baixo"})(),
    )})()
    m = ModeloSinais(st)
    tip = m.data(m.index(0, _col("Motivo")), Qt.ToolTipRole)
    assert tip and "confiança" in tip.lower()


def test_pareado_comando_sem_par_e_endereco_visiveis(qtbot):
    """SP-CVA2 E6.3 (fato 3 do anot.txt): comando sem par precisa ser
    LOCALIZÁVEL na revisão — rótulo próprio + endereço na coluna Endereço."""
    rec = replace(
        _rec(status="revisao", sigla="DJA1"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Output"),
        enderecamento=Enderecamento("DNP3", (90,)),
    )
    m = ModeloSinais(_state(rec))
    assert m.data(m.index(0, _col("Pareado"))) == "Comando (sem par)"
    assert m.data(m.index(0, _col("Endereço"))) == "90"


def test_pareado_orfao_continua_para_output_sem_endereco(qtbot):
    rec = replace(
        _rec(),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Output"),
        enderecamento=Enderecamento("DNP3", ()),
    )
    m = ModeloSinais(_state(rec))
    assert m.data(m.index(0, _col("Pareado"))) == "Órfão"


def test_motivo_posicao_divergente_tem_label_e_tooltip(qtbot):
    from tdt.ui.modelo_tabela import _MOTIVO_TOOLTIP
    assert _MOTIVO_LABEL["posicao_divergente"] == "Posição diverge do status"
    assert "status" in _MOTIVO_TOOLTIP["posicao_divergente"].lower()
