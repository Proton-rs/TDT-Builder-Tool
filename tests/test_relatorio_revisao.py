import openpyxl

from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Enderecamento, ItemRevisao, Modulo,
    SignalRecord, TipoSinal,
)
from tdt.relatorio_revisao import gerar_relatorio_revisao


def _rec(id_, sigla=None, candidatos=(), diagnostico=None, status="decidido"):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes("Disjuntor Aberto", "disjuntor aberto"),
        sigla_sinal=sigla, candidatos=candidatos, status=status,
        diagnostico=diagnostico,
    )


def test_gera_planilha_com_uma_linha_por_sinal(tmp_path):
    cands = (Candidato("DJ", 0.91, "mesclado"), Candidato("SC", 0.40, "mesclado"))
    diag = Diagnostico(scores_por_metodo={"DJ": {"tfidf": 0.9, "vetorial": 0.92, "fuzzy": 0.88}})
    registros = [_rec("S1:1", sigla="DJ", candidatos=cands, diagnostico=diag)]
    revisao = ()

    caminho = gerar_relatorio_revisao(registros, revisao, tmp_path)

    assert caminho.exists()
    wb = openpyxl.load_workbook(caminho)
    ws = wb["Auditoria"]
    assert ws.cell(1, 1).value == "ID Sinal"
    assert ws.cell(2, 1).value == "S1:1"
    assert ws.cell(2, 6).value == "DJ"  # Sigla Decidida
    assert ws.cell(2, 9).value == "DJ"  # Candidato 1


def test_sinal_sem_candidatos_nao_quebra(tmp_path):
    registros = [_rec("S1:2", sigla=None, candidatos=(), status="revisao")]
    revisao = (ItemRevisao(registros[0], motivo="score_baixo"),)

    caminho = gerar_relatorio_revisao(registros, revisao, tmp_path)

    wb = openpyxl.load_workbook(caminho)
    ws = wb["Auditoria"]
    assert ws.cell(2, 8).value == "score_baixo"  # Motivo Revisão
    assert ws.cell(2, 9).value in (None, "")  # sem candidato 1
