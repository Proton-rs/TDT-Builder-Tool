import openpyxl

from bench.regressao import Caso, carregar_casos, checar_casos


def _tdt_fake(path, linhas):
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "DNP3_DiscreteSignals"
    for _ in range(4): ws.append([])
    for nome, addr in linhas:
        row = [None] * 32; row[0] = nome; row[31] = addr; ws.append(row)
    wb.create_sheet("DNP3_AnalogSignals"); wb.save(path)


def test_carregar_casos_le_csv(tmp_path):
    p = tmp_path / "casos.csv"
    p.write_text(
        "subestacao,endereco,sigla_esperada,origem,nota\n"
        "GTD,7,BBFC,2026-07-01 fix comando,verbo vazava\n",
        encoding="utf-8",
    )
    casos = carregar_casos(str(p))
    assert casos == [Caso("GTD", 7, "BBFC", "2026-07-01 fix comando", "verbo vazava")]


def test_checar_casos_passa_e_falha(tmp_path):
    tdt = tmp_path / "nosso.xlsx"
    _tdt_fake(tdt, [("GTD_LTGTA_52-1_BBFC", 7), ("GTD_AL_X_LIGAR", 8)])
    casos = [Caso("GTD", 7, "BBFC", "o", "n"), Caso("GTD", 8, "BBFC", "o", "n")]
    res = checar_casos(str(tdt), casos)
    passou = {c.endereco: ok for c, _, ok in res}
    assert passou == {7: True, 8: False}
