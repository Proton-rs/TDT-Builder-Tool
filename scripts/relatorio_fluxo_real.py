"""Relatório de fluxo/conservação para listas reais (gate de closeout).

Roda o pipeline completo numa lista e imprime: TDT × revisão (por motivo) e
eventos de identidade (sobrescritas INFO / perdas AVISO do módulo
fluxo_dados). Perda > 0 = bug de fluxo (regra 2 do CLAUDE.md).

Uso (listas reais ficam fora do repo — passe o path):
    PYTHONPATH=src python scripts/relatorio_fluxo_real.py \
        "C:/Users/vinic/Documents/docs importantes/RGE/LVA/Lista de pontos LVA.xlsx" \
        --subestacao LVA
"""

import argparse
import sys
from collections import Counter

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("input", help="planilha de entrada (.xlsx)")
    p.add_argument("--lista-padrao", default="docs/Pontos Padrao ADMS_v8.xlsx")
    p.add_argument("--template", default="docs/dnp3_template.xlsx")
    p.add_argument("--subestacao", default=None)
    args = p.parse_args()

    cfg = Config()
    aud = Auditoria()
    res, _wb = executar(
        args.input, args.template, args.lista_padrao,
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding),
        subestacao=args.subestacao, auditoria=aud,
    )

    print(f"\nTDT: {len(res.lista.registros)} | revisão: {len(res.revisao)}")
    print("revisão por motivo:")
    for motivo, n in Counter(ir.motivo for ir in res.revisao).most_common():
        print(f"  {motivo}: {n}")

    fluxo = [e for e in aud.eventos if e.modulo == "fluxo_dados"]
    perdas = [e for e in fluxo if e.dados and e.dados.get("tipo") == "perda"]
    print(f"\neventos de identidade: {len(fluxo)} ({len(perdas)} PERDAS)")
    for e in perdas:
        print(f"  PERDA {e.signal_id}: {e.msg}")
    return 1 if perdas else 0


if __name__ == "__main__":
    sys.exit(main())
