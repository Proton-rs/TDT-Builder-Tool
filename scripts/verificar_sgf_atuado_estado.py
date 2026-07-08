# scripts/verificar_sgf_atuado_estado.py
"""Task 7 (SP-G Caso 5): reprocessa LISTA 1 (GTD) e reporta o status/score do
sinal 'Proteção SGF - Atuado' (candidato correto: SGFT) para verificar o
efeito da regra R7 (estado compativel, motor_regras.r7_estado_compativel).

Uso: PYTHONPATH=src python scripts/verificar_sgf_atuado_estado.py
"""
from __future__ import annotations
import sys, warnings, logging
from pathlib import Path

warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from tdt.pipeline import executar
from tdt.config import Config
from tdt.dados.encoder import criar_encoder


def main() -> None:
    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)
    res, _ = executar(
        str(_ROOT / "docs" / "input_nao_homogeneo_1_GTA.xlsx"),
        str(_ROOT / "docs" / "dnp3_template.xlsx"),
        str(_ROOT / "docs" / "Pontos Padrao ADMS_v2.xlsx"),
        config=cfg, encoder=enc, subestacao="GTD", modo="nao-homogeneo",
    )
    decididos = list(res.lista.registros)
    revisao = list(res.revisao)
    print(f"TOTAL decididos={len(decididos)} revisao={len(revisao)}")

    print("\n=== Buscando 'Proteção SGF - Atuado' (case-insensitive contains) ===")
    achados_dec = [
        r for r in decididos
        if "sgf" in r.descricoes.bruta.lower() and "atuad" in r.descricoes.bruta.lower()
    ]
    achados_rev = [
        it for it in revisao
        if "sgf" in it.registro.descricoes.bruta.lower()
        and "atuad" in it.registro.descricoes.bruta.lower()
    ]

    print(f"total instancias DECIDIDO={len(achados_dec)} REVISAO={len(achados_rev)}")
    print(f"  ids decididos: {[r.id for r in achados_dec]}")
    print(f"  ids revisao:   {[it.registro.id for it in achados_rev]}")

    for r in achados_dec[:1]:
        print(f"\nDECIDIDO(exemplo): id={r.id} desc={r.descricoes.bruta!r} "
              f"sigla={r.sigla_sinal} justificativa={r.justificativa!r}")
        print("  candidatos:")
        for c in r.candidatos[:6]:
            print(f"    sigla={c.sigla!r} score={c.score:.4f} fonte={c.fonte}")

    for it in achados_rev[:5]:
        r = it.registro
        print(f"\nREVISAO: id={r.id} desc={r.descricoes.bruta!r} motivo={it.motivo}")
        print("  candidatos sugeridos:")
        for c in it.candidatos_sugeridos[:6]:
            print(f"    sigla={c.sigla!r} score={c.score:.4f} fonte={c.fonte}")


if __name__ == "__main__":
    main()
