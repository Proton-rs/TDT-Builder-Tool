import openpyxl

from tdt.contracts import (
    Candidato, Descricoes, Diagnostico, Enderecamento, ItemRevisao, Modulo,
    SignalRecord, TipoSinal,
)
from tdt.relatorio_revisao import descricao_para_exibicao, gerar_relatorio_revisao


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


def test_descricao_para_exibicao_usa_sigla_quando_bruta_e_codigo():
    assert descricao_para_exibicao("SND_LT67SAN_LT67SAN_79", "79") == "79"


def test_descricao_para_exibicao_mantem_descricao_real():
    assert descricao_para_exibicao("Disjuntor Aberto", "DJ") == "Disjuntor Aberto"


def test_descricao_para_exibicao_sem_sigla_mantem_bruta():
    assert descricao_para_exibicao("SND_LT67SAN_LT67SAN_79", None) == "SND_LT67SAN_LT67SAN_79"


def test_relatorio_usa_sigla_como_descricao_quando_bruta_e_codigo(tmp_path):
    from dataclasses import replace
    rec = replace(_rec("S1:3", sigla="79"), descricoes=Descricoes("SND_LT67SAN_LT67SAN_79", "x"))
    registros = [rec]

    caminho = gerar_relatorio_revisao(registros, (), tmp_path)

    wb = openpyxl.load_workbook(caminho)
    ws = wb["Auditoria"]
    assert ws.cell(2, 2).value == "79"  # Descrição Bruta -- sigla, não o código


def test_cabecalho_tem_formatacao_visual(tmp_path):
    cands = (Candidato("DJ", 0.91, "mesclado"),)
    registros = [_rec("S1:1", sigla="DJ", candidatos=cands)]

    caminho = gerar_relatorio_revisao(registros, (), tmp_path)

    wb = openpyxl.load_workbook(caminho)
    ws = wb["Auditoria"]
    for col in range(1, len(ws[1]) + 1):
        cell = ws.cell(1, col)
        assert cell.fill.patternType == "solid"
        assert cell.fill.fgColor.rgb == "004472C4"
        assert cell.font.bold is True
        assert cell.font.color.rgb == "00FFFFFF"
        assert cell.border.left.style == "thin"
        assert cell.border.right.style == "thin"
        assert cell.border.top.style == "thin"
        assert cell.border.bottom.style == "thin"
        assert cell.alignment.horizontal == "center"


def test_largura_colunas_ajustada_pelo_conteudo(tmp_path):
    descricao_longa = "x" * 60
    registros = [
        SignalRecord(
            id="S1:1", modulo=Modulo("M", "sheet_name"),
            tipo_sinal=TipoSinal("Discrete", False, "Input"),
            enderecamento=Enderecamento("DNP3", (10,)),
            descricoes=Descricoes(descricao_longa, "x"),
            sigla_sinal=None, candidatos=(), status="decidido",
            diagnostico=None,
        )
    ]

    caminho = gerar_relatorio_revisao(registros, (), tmp_path)

    wb = openpyxl.load_workbook(caminho)
    ws = wb["Auditoria"]
    # coluna "Descrição Bruta" (B) deve ter largura ajustada e capada em 40
    largura_b = ws.column_dimensions["B"].width
    assert largura_b is not None
    assert largura_b == 40  # capado: 60 chars + 2 > 40
    # nenhuma coluna deve ficar no default do openpyxl (None ou 8.43)
    for col_letra in ("A", "B", "C", "D", "E", "F", "G", "H"):
        largura = ws.column_dimensions[col_letra].width
        assert largura is not None
        assert largura != 8.43
