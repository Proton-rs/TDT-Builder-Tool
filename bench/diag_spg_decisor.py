"""Diagnostico SP-G: de onde vem as decisoes 79 (score>1) e DJA1 (0.858).

Uso: PYTHONPATH=src python bench/diag_spg_decisor.py <input_lista1.xlsx>

Consome tdt.pipeline.executar(...) e imprime, para cada sinal cujo texto
bruto contenha um dos ALVOS, a sigla decidida, a justificativa (identifica o
DECISOR: fuzzy/e5/consenso/quadrante/regras) e os top-4 candidatos com
(sigla, score, fonte) — fonte identifica a ORIGEM do candidato (tfidf /
vetorial / mesclado / expandido / ancora_sigla).
"""
from __future__ import annotations

import sys
import warnings
import logging

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar

ALVOS = ("BEM SUCEDIDO", "INTERTRAVAMENTO", "RELIGAMENTO (79)", "DESLIGADO")

_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA_PADRAO = "docs/Pontos Padrao ADMS_v2.xlsx"


def main(input_path: str) -> None:
    cfg = Config()
    aud = Auditoria()
    resultado, _wb = executar(
        input_path, _TEMPLATE, _LISTA_PADRAO,
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding), auditoria=aud,
        subestacao="GTD",
    )
    aud.salvar_json("bench/resultados/spG_diag_decisor_aud.json")

    print("=== registros DECIDIDOS (resultado.lista.registros) ===")
    n_dec = 0
    for r in resultado.lista.registros:
        d = r.descricoes.bruta.upper()
        if any(a in d for a in ALVOS):
            n_dec += 1
            cands = [(c.sigla, round(c.score, 3), c.fonte) for c in (r.candidatos or [])[:4]]
            print(f"{r.descricoes.bruta!r} -> {r.sigla_sinal} | just={r.justificativa} | cands={cands}")
    print(f"--- total decididos correspondentes aos ALVOS: {n_dec} ---\n")

    print("=== itens em REVISAO (resultado.revisao) que tambem batem ALVOS ===")
    n_rev = 0
    for item in resultado.revisao:
        r = item.registro
        d = r.descricoes.bruta.upper()
        if any(a in d for a in ALVOS):
            n_rev += 1
            cands = [(c.sigla, round(c.score, 3), c.fonte) for c in (r.candidatos or [])[:4]]
            sugeridos = [(c.sigla, round(c.score, 3), c.fonte) for c in (item.candidatos_sugeridos or [])[:4]]
            print(f"{r.descricoes.bruta!r} -> motivo={item.motivo} | sigla_sinal={r.sigla_sinal} "
                  f"| just={r.justificativa} | cands={cands} | sugeridos={sugeridos}")
    print(f"--- total em revisao correspondentes aos ALVOS: {n_rev} ---")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/input_nao_homogeneo_1_GTA.xlsx")
