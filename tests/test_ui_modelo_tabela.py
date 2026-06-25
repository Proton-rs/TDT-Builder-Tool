from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais


def _rec(status="decidido", sigla="DJF1"):
    return SignalRecord(
        id="a:1", modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("Falha DJ 52-1", "FALHA DJ"),
        sigla_sinal=sigla, status=status,
        candidatos=(Candidato(sigla, 0.87, "mesclado"),) if sigla else (),
        diagnostico=Diagnostico({sigla: {"tfidf": 0.91, "vetorial": 0.84, "fuzzy": 0.72}}) if sigla else None,
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
