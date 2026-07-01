"""Diagnóstico (Fase 1 / spD3): mede a frequência real do padrão "filho-vs-pai"
e testa se um embedding melhor fecha o gap semântico — SEM implementar fix.

Padrão "filho-vs-pai": a sigla real (esperada) é uma variante mais específica
de uma mesma família DE PROTEÇÃO/FUNÇÃO cuja sigla "nua" (genérica) TAMBÉM
existe como entrada própria na lista padrão — e é essa sigla nua que o
pipeline decidiu, em vez da variante específica. Ex.: real=`79OK` nosso=`79`
(79 é sigla standalone "FUNÇÃO RELIGAMENTO"). NÃO é filho-vs-pai quando a
nossa sigla é só o número líder truncado sem existir como sigla própria
(ex. real=`50F1` nosso=`1` — truncamento, já rastreado em casos_travados.csv).

Step 1: roda o gate real (bench.gate_tdt_real) e classifica cada divergência.
Step 2: para um conjunto de descrições confirmadas, compara o ranking do
filho correto sob (a) MiniLM+corpus atual == corpus_enriquecido (é o que já
roda em produção — pipeline._construir_scorers já usa _corpus_enriquecido,
não há dois paths), e (b) e5 assimétrico (intfloat/multilingual-e5-base,
dormente atrás de config.e5_prefixos).

Uso: PYTHONPATH=src python -m bench.diag_filho_vs_pai
"""
from __future__ import annotations

import sys
import warnings
import logging
from dataclasses import dataclass, replace

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from bench.gate_tdt_real import comparar
from tdt.config import Config
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.dados.encoder import criar_encoder
from tdt.dados.indice_vetorial import IndiceVetorial
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.normalizacao.normalizador import canonizar
from tdt.scoring.tfidf import ScorerTFIDF
from tdt.scoring.vetorial import pontuar as pontuar_vet
from tdt import pipeline

_NOSSO_TDT = "bench/_tdt_gerado_GTD.xlsx"
_INPUT = "docs/input_nao_homogeneo_1_GTD.xlsx"
_REAL_TDT = "docs/TDT/exportTDT_UTR_GTD_1_20260626.xlsx"
_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA = "docs/Pontos Padrao ADMS_v2.xlsx"
_E5_MODELO = "intfloat/multilingual-e5-base"  # ver .memory/decisions.md


def _gerar_nosso_tdt_se_ausente(saida: str) -> None:
    import os
    if os.path.exists(saida):
        return
    cfg = Config()
    enc = criar_encoder(cfg.modelo_embedding)
    _res, wb = pipeline.executar(_INPUT, _TEMPLATE, _LISTA, config=cfg, encoder=enc, subestacao="GTD")
    wb.save(saida)


# ---------------------------------------------------------------------------
# Step 1: frequência no GT real
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CasoFilhoPai:
    endereco: int
    real: str
    nosso: str
    nome_real: str


def classificar_divergencias(divergencias, siglas_validas: set[str]) -> tuple[list[CasoFilhoPai], list]:
    """Separa divergências no padrão filho-vs-pai das demais.

    filho-vs-pai: `nosso` é uma sigla que existe standalone na lista padrão
    E `real` começa com `nosso` (mesmo prefixo) E `real != nosso`. Isso
    exclui truncamentos onde `nosso` é só um número/fragmento que não é
    sigla própria (ex. nosso="1", "2" para 50F1/50F2/67F1/67F2 — essas são
    o padrão INVERSO, truncamento, já coberto por casos_travados.csv).
    """
    filho_pai: list[CasoFilhoPai] = []
    outros = []
    for addr, real, nosso, nome in divergencias:
        real_u, nosso_u = real.upper(), nosso.upper()
        eh_familia = (
            nosso_u in siglas_validas
            and real_u.startswith(nosso_u)
            and real_u != nosso_u
        )
        if eh_familia:
            filho_pai.append(CasoFilhoPai(addr, real, nosso, nome))
        else:
            outros.append((addr, real, nosso, nome))
    return filho_pai, outros


def agrupar_por_familia(casos: list[CasoFilhoPai]) -> dict[str, list[CasoFilhoPai]]:
    grupos: dict[str, list[CasoFilhoPai]] = {}
    for c in casos:
        grupos.setdefault(c.nosso.upper(), []).append(c)
    return grupos


# ---------------------------------------------------------------------------
# Step 2: efeito do embedding sobre casos confirmados
# ---------------------------------------------------------------------------

def _rec(desc: str, cfg: Config) -> SignalRecord:
    return SignalRecord(
        id="diag", modulo=Modulo("diag", "script"),
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(desc, canonizar(desc, cfg)),
    )


@dataclass(frozen=True)
class CasoAlvo:
    descricao: str
    filho_esperado: str
    pai_generico: str
    origem: str  # nota de onde veio (endereço/família)


def _ranking_vetorial_isolado(rec, indice: IndiceVetorial, k: int = 10):
    return pontuar_vet(rec, indice, k=k)


def _ranking_pipeline_completo(rec, scorers: "pipeline._Scorers", lp: ListaPadraoADMS, k: int = 8):
    d = pipeline._classificar_sinal(rec, scorers, diagnostico=False, lista_padrao=lp)
    return list(d.candidatos[:k])


def _posicao(siglas_rank: list[str], alvo: str) -> "int | None":
    return siglas_rank.index(alvo) + 1 if alvo in siglas_rank else None


def _fmt_top(cands, n=6) -> str:
    return ", ".join(f"{c.sigla}={c.score:.3f}" for c in cands[:n])


def rodar_step2(casos: list[CasoAlvo]) -> None:
    print("\n" + "=" * 78)
    print("STEP 2 — embedding fecha o gap semântico?")
    print("=" * 78)

    cfg_minilm = Config()
    lp = ListaPadraoADMS.carregar(_LISTA)

    # --- MiniLM (== produção hoje: pipeline._construir_scorers já usa
    # _corpus_enriquecido; não existe um segundo path "corpus simples" em uso) ---
    enc_minilm = criar_encoder(cfg_minilm.modelo_embedding)
    scorers_minilm = pipeline._construir_scorers(lp, cfg_minilm, enc_minilm, "Discrete", cfg_minilm)
    corpus_enr = pipeline._corpus_enriquecido(lp, cfg_minilm, "Discrete")
    idx_minilm_isolado = IndiceVetorial.construir(corpus_enr, enc_minilm)

    # --- e5 assimétrico (dormente, config.e5_prefixos=False por padrão) ---
    cfg_e5 = replace(cfg_minilm, modelo_embedding=_E5_MODELO, e5_prefixos=True)
    enc_e5_p = criar_encoder(_E5_MODELO, "passage: ")
    enc_e5_q = criar_encoder(_E5_MODELO, "query: ")
    corpus_raw = pipeline._corpus(lp, cfg_e5, "Discrete")
    scorers_e5 = pipeline._Scorers(
        tfidf=ScorerTFIDF.construir(corpus_raw),
        indice=IndiceVetorial.construir(corpus_enr, enc_e5_p, enc_e5_q),
        fuzzy=FuzzyMatcher.construir(corpus_raw),
        config=cfg_e5,
    )
    idx_e5_isolado = IndiceVetorial.construir(corpus_enr, enc_e5_p, enc_e5_q)

    resumo = []
    for caso in casos:
        print(f"\n--- '{caso.descricao}' ---")
        print(f"    esperado(filho)={caso.filho_esperado}  pai_generico={caso.pai_generico}  origem={caso.origem}")

        rec_minilm = _rec(caso.descricao, cfg_minilm)
        rec_e5 = _rec(caso.descricao, cfg_e5)

        # (i) MiniLM — vetorial isolado
        rank_vet_minilm = [c.sigla for c in _ranking_vetorial_isolado(rec_minilm, idx_minilm_isolado)]
        pf_v_mini = _posicao(rank_vet_minilm, caso.filho_esperado)
        pp_v_mini = _posicao(rank_vet_minilm, caso.pai_generico)
        print(f"    [MiniLM vetorial isolado]     pos_filho={pf_v_mini} pos_pai={pp_v_mini} "
              f"| top6: {_fmt_top(_ranking_vetorial_isolado(rec_minilm, idx_minilm_isolado))}")

        # (ii) MiniLM — pipeline completo (tfidf+vetorial+fuzzy+regras, como roda hoje)
        rank_full_minilm = [c.sigla for c in _ranking_pipeline_completo(rec_minilm, scorers_minilm, lp)]
        pf_f_mini = _posicao(rank_full_minilm, caso.filho_esperado)
        pp_f_mini = _posicao(rank_full_minilm, caso.pai_generico)
        print(f"    [MiniLM pipeline completo]    pos_filho={pf_f_mini} pos_pai={pp_f_mini} "
              f"| top6: {_fmt_top(_ranking_pipeline_completo(rec_minilm, scorers_minilm, lp))}")

        # (iii) e5 — vetorial isolado
        rank_vet_e5 = [c.sigla for c in _ranking_vetorial_isolado(rec_e5, idx_e5_isolado)]
        pf_v_e5 = _posicao(rank_vet_e5, caso.filho_esperado)
        pp_v_e5 = _posicao(rank_vet_e5, caso.pai_generico)
        print(f"    [e5 vetorial isolado]         pos_filho={pf_v_e5} pos_pai={pp_v_e5} "
              f"| top6: {_fmt_top(_ranking_vetorial_isolado(rec_e5, idx_e5_isolado))}")

        # (iv) e5 — pipeline completo
        rank_full_e5 = [c.sigla for c in _ranking_pipeline_completo(rec_e5, scorers_e5, lp)]
        pf_f_e5 = _posicao(rank_full_e5, caso.filho_esperado)
        pp_f_e5 = _posicao(rank_full_e5, caso.pai_generico)
        print(f"    [e5 pipeline completo]        pos_filho={pf_f_e5} pos_pai={pp_f_e5} "
              f"| top6: {_fmt_top(_ranking_pipeline_completo(rec_e5, scorers_e5, lp))}")

        filho_vence_vet_minilm = pf_v_mini is not None and pp_v_mini is not None and pf_v_mini < pp_v_mini
        filho_vence_full_minilm = pf_f_mini is not None and (pp_f_mini is None or pf_f_mini < pp_f_mini)
        filho_vence_vet_e5 = pf_v_e5 is not None and pp_v_e5 is not None and pf_v_e5 < pp_v_e5
        filho_vence_full_e5 = pf_f_e5 is not None and (pp_f_e5 is None or pf_f_e5 < pp_f_e5)
        resumo.append((caso, filho_vence_vet_minilm, filho_vence_full_minilm, filho_vence_vet_e5, filho_vence_full_e5))

    print("\n" + "-" * 78)
    print("RESUMO — filho ranqueia ACIMA do pai genérico?")
    print(f"{'descrição':<45} {'vet-MiniLM':>11} {'full-MiniLM':>12} {'vet-e5':>8} {'full-e5':>8}")
    for caso, fv_mini, ff_mini, fv_e5, ff_e5 in resumo:
        d = caso.descricao if len(caso.descricao) <= 43 else caso.descricao[:40] + "..."
        print(f"{d:<45} {str(fv_mini):>11} {str(ff_mini):>12} {str(fv_e5):>8} {str(ff_e5):>8}")


def main() -> None:
    _gerar_nosso_tdt_se_ausente(_NOSSO_TDT)

    print("=" * 78)
    print("STEP 1 — frequência do padrão filho-vs-pai no GT real (GTD)")
    print("=" * 78)
    r = comparar(_NOSSO_TDT, _REAL_TDT)
    print(f"comum={r.comum} iguais={r.iguais} pct={r.pct:.1f}% divergências={len(r.divergencias)}")

    lp = ListaPadraoADMS.carregar(_LISTA)
    siglas_validas = {s.sigla.upper() for s in lp.discretos} | {s.sigla.upper() for s in lp.analogicos}

    filho_pai, outros = classificar_divergencias(r.divergencias, siglas_validas)
    print(f"\nfilho-vs-pai: {len(filho_pai)} / {len(r.divergencias)} divergências totais")
    print(f"outros padrões (truncamento, equip. errado, etc — fora de escopo): {len(outros)}")

    grupos = agrupar_por_familia(filho_pai)
    print(f"\nAgrupado por família (nossa sigla genérica -> N ocorrências):")
    for pai, casos in sorted(grupos.items(), key=lambda kv: -len(kv[1])):
        reais = sorted({c.real for c in casos})
        enderecos = [c.endereco for c in casos]
        print(f"  {pai:<8} n={len(casos):<3} variantes_reais={reais} enderecos={enderecos}")

    print("\nCasos individuais:")
    for c in filho_pai:
        print(f"  addr={c.endereco:<6} real={c.real:<8} nosso={c.nosso:<8} nome={c.nome_real}")

    # --- Step 2: casos-alvo confirmados ---
    # "Religamento (79) - Bem Sucedido" é o caso motivador original (não está
    # no GT real do GTD — não há ponto 79OK nesse conjunto — mas é o repro
    # canônico do problema, citado no brief da task). Os demais vêm
    # diretamente do Step 1 acima, com a descrição bruta original recuperada
    # via pipeline.executar (auditável: ver bloco abaixo).
    casos_alvo = [
        CasoAlvo("Religamento (79) - Bem Sucedido", "79OK", "79",
                 "repro motivador (sintético — não presente no GT real do GTD)"),
        CasoAlvo("Proteção 51 N - Atuado", "51N1", "51N",
                 "GT real GTD addr=67 (e réplicas 267/459/709/730/2135/2235/2332/3035/3135)"),
        CasoAlvo("Relé Buchholz (63T) - Desligamento", "63TD", "63T",
                 "GT real GTD addr=667 (e réplica 967)"),
        CasoAlvo("Válvula de Alivio de Pressão (20T) - Atuada", "20TD", "20T",
                 "GT real GTD addr=670 (e réplica 970)"),
        CasoAlvo("Proteção 67N FOWARD - Atuado (Frente P1 para P2)", "67ND", "67N",
                 "GT real GTD addr=2335"),
    ]
    rodar_step2(casos_alvo)


if __name__ == "__main__":
    main()
