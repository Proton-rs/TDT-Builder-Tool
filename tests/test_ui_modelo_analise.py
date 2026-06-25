from PySide6.QtCore import QModelIndex, Qt

from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.ui.modelo_analise import COLUNAS, ModeloAnalise


def _rec(id_="s1", sigla="DJF1", candidatos=None, diagnostico=None, status="decidido"):
    return SignalRecord(
        id=id_,
        modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("DJ 52 FALHA", "DJ 52 FALHA"),
        sigla_sinal=sigla,
        status=status,
        candidatos=candidatos if candidatos is not None else (
            (Candidato(sigla, 0.85, "mesclado"),) if sigla else ()
        ),
        diagnostico=diagnostico,
        justificativa="ok",
    )


def test_columns_pelo_menos_oito():
    m = ModeloAnalise([_rec()], {})
    assert m.columnCount(QModelIndex()) >= 8
    assert m.columnCount(QModelIndex()) == len(COLUNAS)


def test_row_count():
    regs = [_rec("s1"), _rec("s2")]
    m = ModeloAnalise(regs, {})
    assert m.rowCount(QModelIndex()) == 2


def test_score_final_com_candidato():
    m = ModeloAnalise([_rec()], {})
    idx = m.index(0, COLUNAS.index("Score Final"))
    assert m.data(idx) == 0.85


def test_score_final_sem_candidato_eh_none():
    rec = _rec(sigla=None, candidatos=())
    m = ModeloAnalise([rec], {})
    idx = m.index(0, COLUNAS.index("Score Final"))
    assert m.data(idx) is None


def test_scores_por_metodo():
    diag = Diagnostico({"DJF1": {"tfidf": 0.9, "vetorial": 0.8, "fuzzy": 0.7}})
    rec = _rec(diagnostico=diag)
    m = ModeloAnalise([rec], {})
    assert m.data(m.index(0, COLUNAS.index("Score TF-IDF"))) == 0.9
    assert m.data(m.index(0, COLUNAS.index("Score Vetorial"))) == 0.8
    assert m.data(m.index(0, COLUNAS.index("Score Fuzzy"))) == 0.7


def test_scores_por_metodo_sem_diagnostico_eh_none():
    rec = _rec(diagnostico=None)
    m = ModeloAnalise([rec], {})
    assert m.data(m.index(0, COLUNAS.index("Score TF-IDF"))) is None
    assert m.data(m.index(0, COLUNAS.index("Score Vetorial"))) is None
    assert m.data(m.index(0, COLUNAS.index("Score Fuzzy"))) is None


def test_gap_dois_candidatos():
    cands = (Candidato("DJF1", 0.85, "mesclado"), Candidato("DJF2", 0.60, "mesclado"))
    rec = _rec(candidatos=cands)
    m = ModeloAnalise([rec], {})
    gap = m.data(m.index(0, COLUNAS.index("Gap")))
    assert gap == round(0.85 - 0.60, 4)


def test_gap_um_candidato_eh_score_do_primeiro():
    rec = _rec(candidatos=(Candidato("DJF1", 0.85, "mesclado"),))
    m = ModeloAnalise([rec], {})
    gap = m.data(m.index(0, COLUNAS.index("Gap")))
    assert gap == 0.85


def test_gap_sem_candidato_eh_none():
    rec = _rec(sigla=None, candidatos=())
    m = ModeloAnalise([rec], {})
    gap = m.data(m.index(0, COLUNAS.index("Gap")))
    assert gap is None


def test_motivo_revisao_via_dict_id():
    rec = _rec(id_="s1")
    m = ModeloAnalise([rec], {"s1": "score_baixo"})
    v = m.data(m.index(0, COLUNAS.index("Motivo Revisão")))
    assert v == "score_baixo"


def test_motivo_revisao_vazio_quando_nao_presente():
    rec = _rec(id_="s1")
    m = ModeloAnalise([rec], {})
    v = m.data(m.index(0, COLUNAS.index("Motivo Revisão")))
    assert v == ""


def test_consenso_conta_metodos_com_score_nao_nulo():
    diag = Diagnostico({"DJF1": {"tfidf": 0.9, "vetorial": 0.0, "fuzzy": 0.7}})
    rec = _rec(diagnostico=diag)
    m = ModeloAnalise([rec], {})
    consenso = m.data(m.index(0, COLUNAS.index("Consenso")))
    # vetorial=0.0 não é None mas é falsy; contamos por "não-nulo" (is not None)
    assert consenso == 3


def test_consenso_sem_diagnostico_eh_zero():
    rec = _rec(diagnostico=None)
    m = ModeloAnalise([rec], {})
    consenso = m.data(m.index(0, COLUNAS.index("Consenso")))
    assert consenso == 0


def test_header_data():
    m = ModeloAnalise([_rec()], {})
    assert m.headerData(0, Qt.Horizontal, Qt.DisplayRole) == "ID"


def test_id_descricao_sigla_status():
    m = ModeloAnalise([_rec(id_="s1", sigla="DJF1", status="decidido")], {})
    assert m.data(m.index(0, COLUNAS.index("ID"))) == "s1"
    assert m.data(m.index(0, COLUNAS.index("Descrição"))) == "DJ 52 FALHA"
    assert m.data(m.index(0, COLUNAS.index("Sigla Decidida"))) == "DJF1"
    assert m.data(m.index(0, COLUNAS.index("Status"))) == "decidido"


def test_data_role_diferente_de_display_retorna_none():
    m = ModeloAnalise([_rec()], {})
    assert m.data(m.index(0, 0), Qt.ToolTipRole) is None
