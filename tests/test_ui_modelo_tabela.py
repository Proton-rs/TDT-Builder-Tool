from dataclasses import replace

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Eletrico, Enderecamento, GrandezasAnalogicas,
    Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais


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
    assert m.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "Sinal"


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
                 "Tipo Equip.", "Módulo", "Escala"):
        flags = m.flags(m.index(0, _col(nome)))
        assert flags & Qt.ItemIsEditable, nome


def test_flags_colunas_derivadas_nao_sao_editaveis():
    m = ModeloSinais(_state(_rec()))
    for nome in ("Status", "Motivo", "Descr. ADMS", "Score tf-idf",
                 "Justificativa", "Equipamento"):
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


def test_set_data_coluna_nao_editavel_retorna_false():
    st = _state(_rec())
    m = ModeloSinais(st)
    ok = m.setData(m.index(0, _col("Status")), "decidido", Qt.EditRole)
    assert ok is False


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
