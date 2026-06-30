# scripts/diag_qualificador.py
"""D1 (SP-D): categoriza os empates de score_baixo na GTD V11 por família ANSI,
tipo de qualificador e causa de não-separação. Diagnóstico — não toca produção.

Uso: PYTHONPATH=src python scripts/diag_qualificador.py
"""
from __future__ import annotations
import csv, re, sys, warnings, logging
from collections import Counter
from pathlib import Path

warnings.simplefilter("ignore"); logging.disable(logging.CRITICAL)
_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))

from tdt.pipeline import executar
from tdt.config import Config
from tdt.defaults import DEFAULT_TEMPLATE
from tdt.dados.encoder import criar_encoder
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.normalizacao.normalizador import canonizar

LIDER = re.compile(r"(\d{2,3})")
QUALIF = {
    "estagio": re.compile(r"\bE?\d\b|\bEST[AÁ]GIO\b", re.I),
    "fase": re.compile(r"\bFASE\b|\b[ABCN]$"),
    "temporizacao": re.compile(r"\bTEMPORIZAD|INSTANT|\bTOC\b|\bIOC\b", re.I),
    "direcao": re.compile(r"\bREVERSE|\bFORWARD|\bDIRECION", re.I),
}

def lider(s: str) -> str | None:
    m = LIDER.match(s); return m.group(1) if m else None

def tipos_no_texto(txt: str) -> set[str]:
    return {k for k, rx in QUALIF.items() if rx.search(txt)}

def main() -> None:
    cfg = Config(); enc = criar_encoder(cfg.modelo_embedding)
    lp = ListaPadraoADMS.carregar("docs/Pontos Padrao ADMS_v2.xlsx")
    desc_por_sigla = {s.sigla.upper(): s.descricao for s in (*lp.discretos, *lp.analogicos)}
    res, _ = executar("docs/GTD - Lista de Pontos V11.xlsx", DEFAULT_TEMPLATE,
                      "docs/Pontos Padrao ADMS_v2.xlsx", config=cfg, encoder=enc,
                      subestacao="GTD", modo="nao-homogeneo")
    sb = [it for it in res.revisao if it.motivo == "score_baixo"]
    linhas = []
    cat = Counter()
    for it in sb:
        c = it.candidatos_sugeridos
        if len(c) < 2 or (c[0].score - c[1].score) >= cfg.threshold_gap:
            continue
        s1, s2 = c[0].sigla.upper(), c[1].sigla.upper()
        mesma_fam = lider(s1) is not None and lider(s1) == lider(s2)
        txt = canonizar(it.registro.descricoes.bruta, cfg)
        # qualificadores presentes no texto e nas descrições-padrão das 2 siglas
        qt = tipos_no_texto(txt)
        q1 = tipos_no_texto(desc_por_sigla.get(s1, ""))
        q2 = tipos_no_texto(desc_por_sigla.get(s2, ""))
        # tipo que DISTINGUE: presente no texto e que separa s1 de s2
        distingue = sorted((qt & (q1 ^ q2)))
        categoria = (
            "cross_familia" if not mesma_fam
            else (",".join(distingue) if distingue else "mesma_fam_sem_qualif_distinto")
        )
        cat[categoria] += 1
        linhas.append((it.registro.descricoes.bruta, s1, f"{c[0].score:.2f}",
                       s2, f"{c[1].score:.2f}", lider(s1) or "", categoria))
    out = _ROOT / "bench" / "resultados" / "diag_qualificador.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["desc_bruta", "top1", "score1", "top2", "score2", "lider_ansi", "categoria"])
        w.writerows(linhas)
    print(f"score_baixo: {len(sb)} | empates analisados: {len(linhas)}")
    print("categorias:", dict(cat.most_common()))
    print(f"detalhe em {out.relative_to(_ROOT)}")

if __name__ == "__main__":
    main()
