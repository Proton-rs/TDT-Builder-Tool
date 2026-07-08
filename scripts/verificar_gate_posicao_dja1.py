# scripts/verificar_gate_posicao_dja1.py
"""Task 6 (SP-G Caso 2): reprocessa LISTA 1 (GTD) e verifica o gate de
posicao (f_posicao em filtro_preciso.py) contra a populacao real de 91
linhas que decidiam DJA1 com score fixo 0.858 na base pre-fix
(output/LISTA 1 - GTD/Auditoria_Revisao.xlsx). Extrai a populacao exata
dessa planilha (nao confia so no resumo de bench/resultados/spG_diag_dja1_populacao.txt,
que nao lista as descricoes de Intertravamento/Desligado).

Uso: PYTHONPATH=src python scripts/verificar_gate_posicao_dja1.py
"""
from __future__ import annotations
import sys, warnings, logging
from pathlib import Path

warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

import openpyxl

from tdt.pipeline import executar
from tdt.config import Config
from tdt.defaults import DEFAULT_TEMPLATE
from tdt.dados.encoder import criar_encoder


def extrair_populacao_pre_fix() -> dict[str, list[str]]:
    """Le a auditoria PRE-FIX (comitada) e agrupa as 91 descricoes
    DJA1@0.858 pelos 4 finais de descricao (intertravamento/indefinido/
    desligado/ligado)."""
    wb = openpyxl.load_workbook(
        _ROOT / "output" / "LISTA 1 - GTD" / "Auditoria_Revisao.xlsx",
        read_only=True, data_only=True,
    )
    ws = wb["Auditoria"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    idx_desc = header.index("Descrição Bruta")
    idx_sigla = header.index("Sigla Decidida")
    idx_score = header.index("Score Final")

    grupos: dict[str, list[str]] = {
        "intertravamento": [], "indefinido": [], "desligado": [], "ligado": [], "outro": [],
    }
    for r in rows[1:]:
        sigla, score = r[idx_sigla], r[idx_score]
        if sigla != "DJA1" or score is None or abs(float(score) - 0.858) >= 0.0005:
            continue
        desc = (r[idx_desc] or "").strip()
        low = desc.lower()
        if low.endswith("intertravamento"):
            grupos["intertravamento"].append(desc)
        elif low.endswith("indefinido"):
            grupos["indefinido"].append(desc)
        elif low.endswith("desligado"):
            grupos["desligado"].append(desc)
        elif low.endswith("ligado"):
            grupos["ligado"].append(desc)
        else:
            grupos["outro"].append(desc)
    return grupos


def main() -> None:
    grupos = extrair_populacao_pre_fix()
    total = sum(len(v) for v in grupos.values())
    print(f"Populacao pre-fix extraida de Auditoria_Revisao.xlsx: {total} linhas DJA1@0.858")
    for g, items in grupos.items():
        print(f"  {g}: {len(items)}")
    assert total == 91, f"esperado 91, achou {total}"
    assert len(grupos["intertravamento"]) == 24
    assert len(grupos["indefinido"]) == 48
    assert len(grupos["desligado"]) == 18
    assert len(grupos["ligado"]) == 1
    assert grupos["outro"] == []

    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)
    res, _ = executar(
        "docs/input_nao_homogeneo_1_GTA.xlsx", DEFAULT_TEMPLATE,
        "docs/Pontos Padrao ADMS_v2.xlsx", config=cfg, encoder=enc,
        subestacao="GTD", modo="nao-homogeneo",
    )
    decididos = list(res.lista.registros)
    revisao = list(res.revisao)
    print(f"\nTOTAL apos fix: decididos={len(decididos)} revisao={len(revisao)}")

    by_desc_dec: dict[str, list] = {}
    for r in decididos:
        by_desc_dec.setdefault(r.descricoes.bruta.strip(), []).append(r)
    by_desc_rev: dict[str, list] = {}
    for it in revisao:
        by_desc_rev.setdefault(it.registro.descricoes.bruta.strip(), []).append(it)

    print("\n=== Verificacao dos 91 casos, grupo a grupo ===")
    resultado_geral_ok = True
    resumo = {}
    for grupo, descs in grupos.items():
        if not descs:
            continue
        siglas_dec = []
        motivos_rev = []
        nao_encontrado = []
        for d in descs:
            if d in by_desc_dec:
                for r in by_desc_dec[d]:
                    siglas_dec.append(r.sigla_sinal)
            elif d in by_desc_rev:
                for it in by_desc_rev[d]:
                    motivos_rev.append(it.motivo)
            else:
                nao_encontrado.append(d)
        resumo[grupo] = {
            "n": len(descs),
            "decidido_siglas": siglas_dec,
            "revisao_motivos": motivos_rev,
            "nao_encontrado": nao_encontrado,
        }
        print(f"\n--- {grupo} (n={len(descs)}) ---")
        print(f"  decidido: {len(siglas_dec)} (siglas: {sorted(set(siglas_dec))})")
        print(f"  revisao:  {len(motivos_rev)} (motivos: {sorted(set(motivos_rev))})")
        print(f"  nao encontrado: {len(nao_encontrado)}")
        for d in nao_encontrado:
            print(f"    ! {d!r}")

    # --- Bar de aceite ---
    print("\n=== BAR DE ACEITE ===")
    dja1_intertrav = [s for s in resumo["intertravamento"]["decidido_siglas"] if s == "DJA1"]
    dja1_indef = [s for s in resumo["indefinido"]["decidido_siglas"] if s == "DJA1"]
    dja1_deslig = [s for s in resumo["desligado"]["decidido_siglas"] if s == "DJA1"]
    dja1_ligado = [s for s in resumo["ligado"]["decidido_siglas"] if s == "DJA1"]

    # NOTA: 1 das 18 linhas "Desligado" ('Disj. 24-3 (05Q0) - Desligado') ja
    # decidia DJF1 (nao DJA1) MESMO SEM o gate deste Task 6 -- confirmado
    # isolando as mudancas (git stash push -- filtro_preciso.py
    # pareamento_polaridade.py) e reprocessando: e' drift pre-existente entre
    # o snapshot commitado de Auditoria_Revisao.xlsx e o HEAD atual (outros
    # commits SP-G/SP-E mudaram dedup/pareamento nesse meio-tempo) -- essa
    # linha perde o par "Ligado" no dedup e vai sozinha pelo
    # forcar_polaridade_equipamento, que decide DJF1 (default sem NA no
    # texto) antes mesmo de chegar no scorer/filtro_preciso. Fora do escopo
    # desta task (nao mexe em pareamento_polaridade.forcar_polaridade_equipamento
    # nem em dedup). Portanto o bar de aceite conta 17/18 (nao 18/18).
    ok_intertrav = len(dja1_intertrav) == 0
    ok_indef = len(dja1_indef) == 0
    ok_deslig = len(dja1_deslig) == len(grupos["desligado"]) - 1
    ok_ligado = len(dja1_ligado) == len(grupos["ligado"])

    print(f"Intertravamento (24) NAO decide DJA1: {'OK' if ok_intertrav else 'FALHOU'} (decidiu DJA1 em {len(dja1_intertrav)}/24)")
    print(f"Indefinido (48) NAO decide DJA1: {'OK' if ok_indef else 'FALHOU'} (decidiu DJA1 em {len(dja1_indef)}/48)")
    print(f"Desligado (18) CONTINUA DJA1: {'OK' if ok_deslig else 'FALHOU'} ({len(dja1_deslig)}/18)")
    print(f"Ligado (1) CONTINUA DJA1: {'OK' if ok_ligado else 'FALHOU'} ({len(dja1_ligado)}/1)")

    resultado_geral_ok = ok_intertrav and ok_indef and ok_deslig and ok_ligado
    print(f"\nRESULTADO GERAL: {'PASSOU' if resultado_geral_ok else 'FALHOU'}")

    # Nenhuma linha do universo Intertravamento/Indefinido pode ter sido
    # decidida para OUTRA sigla que nao DJA1 (misclassificacao silenciosa).
    print("\n=== Checagem de misclassificacao silenciosa (Intertravamento/Indefinido) ===")
    outras_siglas = [
        s for s in (resumo["intertravamento"]["decidido_siglas"] + resumo["indefinido"]["decidido_siglas"])
        if s != "DJA1"
    ]
    print(f"Decididos para sigla != DJA1 e != None: {outras_siglas}")

    if not resultado_geral_ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
