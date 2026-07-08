"""SP-H Task 1: diagnostico da distribuicao do gap (score c1 - score c2) nas
revisoes score_baixo da LISTA 1 - GTD.

Hipotese a validar: muitas revisoes score_baixo tem gap ~ 0 nao por empate
genuino, mas porque a LP (docs/Pontos Padrao ADMS_v2.xlsx) contem a MESMA
sigla duas vezes (ex.: "79" como variante Read e ReadWrite, mesma descricao),
entao candidato 1 e candidato 2 da auditoria sao literalmente a mesma sigla
-- um gap-zero artificial.

Por que este script nao le Auditoria_Revisao.xlsx diretamente
----------------------------------------------------------------
O brief original assumia colunas "Score tfidf/vetorial/fuzzy N" preenchidas
por candidato, para computar gap = max(scores c1) - max(scores c2). Na
Auditoria_Revisao.xlsx real essas colunas ficam SEMPRE vazias para revisoes
score_baixo: `tdt.pipeline.executar` so popula `SignalRecord.diagnostico`
quando chamado com `diagnostico=True`, e `bench/reprocessar_lista1.py` (o
script que gerou a auditoria em uso) nao passa essa flag. Alem disso,
`relatorio_revisao.gerar_relatorio_revisao` so escreve "Score Final" para o
candidato 1 (rec.candidatos[0].score) -- nao ha coluna com o score
mesclado do candidato 2 nem do candidato 3 no xlsx.

Por isso este script reprocessa a LISTA 1 - GTD em memoria, com a MESMA
receita de bench/reprocessar_lista1.py, e le o gap diretamente dos
`Candidato` (sigla, score mesclado) anexados a cada `ItemRevisao.registro`
-- sem alterar nenhum modulo em src/. O resultado e equivalente ao que a
auditoria representaria se tivesse uma coluna de score mesclado por
candidato.

Segunda descoberta (por que "mesma_sigla" == c1.sigla == c2.sigla nunca
acontece): `tdt.scoring.mescla.mesclar` acumula os candidatos de cada
metodo (tfidf/vetorial/fuzzy) num dict chaveado por `Candidato.sigla`
(src/tdt/scoring/mescla.py:14). Se a LP tem "79" cadastrado duas vezes
(variante Read + variante ReadWrite, mesma sigla-texto), as duas linhas
IGUALMENTE colapsam na MESMA chave do dict antes mesmo de a lista de
candidatos ser montada -- portanto e estruturalmente impossivel que
`rec.candidatos[0].sigla == rec.candidatos[1].sigla` na saida do pipeline
atual. A hipotese original (candidato 1 e 2 sendo o MESMO texto de sigla)
nao pode se manifestar nesse dado.

Por isso este script tambem cruza cada par gap-zero com a DESCRICAO da LP
(coluna "DESCRIÇÃO NOVA" de DiscreteSignals/AnalogSignals) por sigla: pares
onde sigla(c1) != sigla(c2) mas description(c1) == description(c2) sao a
manifestacao real do bug de duplicacao da LP -- duas siglas DIFERENTES
(tipicamente por variante Read/ReadWrite de uma mesma funcao) mas com o
mesmo texto descritivo, entao tfidf/vetorial/fuzzy dao o MESMO score aos
dois. Pares com descricoes diferentes sao candidatos a empate genuino
(nao sao bug de LP).

Uso: python bench/diag_gap_revisao.py
(nao recebe argumento de arquivo -- reprocessa via pipeline real, pois a
xlsx gerada nao carrega os dados numericos necessarios; veja nota acima)
"""
from __future__ import annotations

import warnings
import logging
from collections import Counter

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)

import openpyxl

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar

_INPUT = "docs/input_nao_homogeneo_1_GTA.xlsx"
_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA_PADRAO = "docs/Pontos Padrao ADMS_v2.xlsx"
_GAP_ZERO_LIMIAR = 0.005


def _carregar_descricao_por_sigla(caminho_lp: str) -> dict[str, str]:
    """sigla (upper) -> descricao (upper) a partir das abas Discrete/Analog
    da LP, para detectar entradas duplicadas (mesma descricao, sigla
    diferente -- ex.: variante Read vs ReadWrite)."""
    wb = openpyxl.load_workbook(caminho_lp, read_only=True)
    desc_por_sigla: dict[str, str] = {}
    for sheet in ("DiscreteSignals", "AnalogSignals"):
        ws = wb[sheet]
        rows = ws.iter_rows(values_only=True)
        next(rows)  # cabecalho
        for r in rows:
            if r and r[0]:
                desc_por_sigla[str(r[0]).strip().upper()] = str(r[1] or "").strip().upper()
    return desc_por_sigla


def main() -> None:
    cfg = Config()
    aud = Auditoria()
    resultado, _wb_out = executar(
        _INPUT, _TEMPLATE, _LISTA_PADRAO,
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding), auditoria=aud,
        subestacao="GTD",
    )
    desc_por_sigla = _carregar_descricao_por_sigla(_LISTA_PADRAO)

    hist: Counter[float] = Counter()
    mesma_sigla = 0  # estruturalmente sempre 0 -- ver nota no docstring
    mesma_descricao_lp = 0  # bug de LP: siglas distintas, descricao identica
    empate_genuino = 0  # siglas e descricoes distintas -- nao e bug de LP
    sem_c2 = 0
    total_score_baixo = 0
    exemplos_mesma_descricao: list[tuple[str, str, str, str]] = []
    exemplos_empate_genuino: list[tuple[str, str, str, str]] = []

    for item in resultado.revisao:
        if item.motivo != "score_baixo":
            continue
        total_score_baixo += 1
        rec = item.registro
        cands = rec.candidatos
        if len(cands) < 2:
            sem_c2 += 1
            continue
        c1, c2 = cands[0], cands[1]
        gap = round(c1.score - c2.score, 3)
        hist[gap] += 1

        if gap <= _GAP_ZERO_LIMIAR:
            if c1.sigla.upper() == c2.sigla.upper():
                mesma_sigla += 1
                continue
            d1 = desc_por_sigla.get(c1.sigla.upper(), "?")
            d2 = desc_por_sigla.get(c2.sigla.upper(), "?")
            if d1 == d2 and d1 != "?":
                mesma_descricao_lp += 1
                if len(exemplos_mesma_descricao) < 15:
                    exemplos_mesma_descricao.append((rec.id, c1.sigla, c2.sigla, d1))
            else:
                empate_genuino += 1
                if len(exemplos_empate_genuino) < 15:
                    exemplos_empate_genuino.append((rec.id, c1.sigla, c2.sigla, f"{d1} || {d2}"))

    print(f"total revisoes score_baixo: {total_score_baixo}")
    print(f"sem candidato 2 (gap indefinido, excluido do histograma): {sem_c2}")
    print()
    gap_zero_total = mesma_sigla + mesma_descricao_lp + empate_genuino
    print(f"gap<={_GAP_ZERO_LIMIAR} (considerado gap-zero): {gap_zero_total}")
    print(f"  mesma_sigla (c1.sigla == c2.sigla, estruturalmente impossivel -- ver docstring): {mesma_sigla}")
    print(f"  mesma_descricao_lp (siglas distintas, descricao LP identica -- bug de LP): {mesma_descricao_lp}")
    print(f"  empate_genuino (siglas e descricoes distintas -- nao e bug de LP): {empate_genuino}")
    if gap_zero_total:
        pct_dup = 100.0 * (mesma_sigla + mesma_descricao_lp) / gap_zero_total
        print(f"  fracao atribuivel a duplicacao de LP (mesma_sigla + mesma_descricao_lp) / gap-zero total: {pct_dup:.1f}%")
    print()
    print("histograma gap (score c1 - score c2), arredondado a 3 casas:")
    for g, n in sorted(hist.items()):
        print(f"  gap={g:+.3f}: {n}")
    print()
    print("exemplos gap-zero MESMA DESCRICAO LP (id, sigla_c1, sigla_c2, descricao_comum):")
    for ex in exemplos_mesma_descricao:
        print(f"  {ex}")
    print()
    print("exemplos gap-zero EMPATE GENUINO (id, sigla_c1, sigla_c2, descricao_c1 || descricao_c2):")
    for ex in exemplos_empate_genuino:
        print(f"  {ex}")


if __name__ == "__main__":
    main()
