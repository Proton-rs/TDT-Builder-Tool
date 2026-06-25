"""Diagnóstico de detecção de colunas/header por sheet. Loga em arquivo.

Uso: PYTHONPATH=src python bench/diag_colunas.py [input.xlsx]
Saída: bench/resultados/diag_colunas.log
"""
import sys, warnings, logging, datetime
warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)

import openpyxl
from tdt.config import Config
from tdt.analise_colunas import analisar, normalizar_emb, _norm
from tdt.normalizador import canonizar
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.dados.encoder import criar_encoder
from tdt.identificador import classificar, ler_rows

inp = sys.argv[1] if len(sys.argv) > 1 else "docs/input_nao_homogeneo_1.xlsx"
HEADERISH = ("DESCRICAO", "DESCRICAO DO PONTO", "DESCRICAO PONTO")

cfg = Config(); enc = criar_encoder(cfg.modelo_embedding)
lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v1.xlsx")
corpus = [(s.sigla, canonizar(s.descricao, cfg)) for s in lp.discretos if s.descricao]
ref = normalizar_emb(enc([d for _, d in corpus]))

wb = openpyxl.load_workbook(inp, read_only=True, data_only=True)
rota = classificar(wb, override="nao-homogeneo")

linhas = [f"# diag_colunas {datetime.datetime.now():%Y-%m-%d %H:%M} | {inp}",
          f"# sheets de dados: {len(rota.sheets_dados)}", ""]
vazamentos = 0
for sn in rota.sheets_dados:
    rows = ler_rows(wb[sn]); mapa = analisar(rows, enc, ref)
    cd = mapa.colunas.get("descricao")
    label = _norm(rows[mapa.header_row - 1][cd]) if cd is not None and mapa.header_row - 1 < len(rows) and cd < len(rows[mapa.header_row - 1]) else "?"
    linhas.append(f"[{sn}] header_row={mapa.header_row} desc_col={cd} label={label!r} cols={mapa.colunas}")
    # rows abaixo do header com valor de descrição igual a rótulo de header
    for i in range(mapa.header_row, len(rows)):
        if cd is None or cd >= len(rows[i]):
            continue
        val = _norm(rows[i][cd])
        if val in HEADERISH:
            linhas.append(f"    !! VAZAMENTO row {i+1}: desc={rows[i][cd]!r}")
            vazamentos += 1
wb.close()

linhas.append("")
linhas.append(f"# vazamentos de header como dado: {vazamentos}")
open("bench/resultados/diag_colunas.log", "w", encoding="utf-8").write("\n".join(linhas))
print(f"vazamentos={vazamentos} | log em bench/resultados/diag_colunas.log")
