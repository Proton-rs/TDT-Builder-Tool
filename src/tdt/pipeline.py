"""Orquestrador do SP1 — o único módulo que conhece todos os outros.

input.xlsx -> ListaHomogenea -> TDT.xlsx, coletando os sinais que foram para
revisão. Embeddings/scorers são construídos uma vez a partir da lista padrão.

Discretos e analógicos têm bundles de scorers próprios (mesmo código,
config derivada por categoria). Sinais com categoria estruturalmente
incerta (`categoria_confiavel=False`) passam pelos dois bundles num
dual-pass; usa-se o único que decidir, ou vão para revisão.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Callable, NamedTuple

import openpyxl

from tdt import criador_lista_homogenea, dc_pairer, engine_tdt, motor_regras, roteador
from tdt.motor_regras import fase_da_sigla
from tdt.analise_colunas import analisar
from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.contracts import Diagnostico, ItemRevisao, ResultadoPipeline, SignalRecord
from tdt.dados.indice_vetorial import IndiceVetorial
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.estruturador import estruturar
from tdt.estruturador_homogeneo import detectar_header, estruturar_homogeneo
from tdt.identificador import classificar, ler_rows
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.normalizador import canonizar
from tdt.normalizador_estrutural import corrigir
from tdt.pareamento_polaridade import forcar_polaridade_equipamento
from tdt.scoring import mescla
from tdt.scoring.tfidf import ScorerTFIDF
from tdt.scoring.vetorial import pontuar as pontuar_vetorial
from tdt.scoring.vetorial import pontuar_com_embedding


def _corpus(lp: ListaPadraoADMS, config: Config, categoria: str = "Discrete") -> list[tuple[str, str]]:
    fonte = lp.discretos if categoria == "Discrete" else lp.analogicos
    return [
        (s.sigla, canonizar(s.descricao, config))
        for s in fonte
        if s.descricao
    ]


class _Scorers(NamedTuple):
    tfidf: object
    indice: object
    fuzzy: object
    config: Config


def _construir_scorers(lp, config, encoder, categoria, cfg_efetivo) -> _Scorers:
    corpus = _corpus(lp, config, categoria)
    return _Scorers(
        tfidf=ScorerTFIDF.construir(corpus),
        indice=IndiceVetorial.construir(corpus, encoder),
        fuzzy=FuzzyMatcher.construir(corpus),
        config=cfg_efetivo,
    )


def _vocab_dominio(corpus: list[tuple[str, str]]) -> frozenset[str]:
    """Vocabulário de termos da lista padrão p/ correção de typos (N4).

    O corpus já vem canonizado; seus tokens são os termos de domínio válidos.
    """
    return frozenset(tok for _, desc in corpus for tok in desc.split())


def _com_fase(rec: SignalRecord) -> SignalRecord:
    """Grava a fase derivada da sigla decidida em ``eletrico.fase`` (se vazia)."""
    if rec.sigla_sinal and rec.eletrico.fase is None:
        f = fase_da_sigla(rec.sigla_sinal.upper())
        if f:
            return replace(rec, eletrico=replace(rec.eletrico, fase=f))
    return rec


def _classificar_sinal(
    rec, scorers: "_Scorers", diagnostico: bool = False, embedding_vet=None
) -> SignalRecord:
    config = scorers.config
    c_tfidf = scorers.tfidf.pontuar(rec, k=config.k_vizinhos)
    if embedding_vet is not None:
        c_vet = pontuar_com_embedding(embedding_vet, rec, scorers.indice, k=config.k_vizinhos)
    else:
        c_vet = pontuar_vetorial(rec, scorers.indice, k=config.k_vizinhos)
    c_fuzzy = scorers.fuzzy.pontuar(rec, k=config.k_vizinhos)
    fundidos = mescla.mesclar(
        [
            (c_tfidf, config.peso_tfidf),
            (c_vet, config.peso_vetorial),
            (c_fuzzy, config.peso_fuzzy),
        ]
    )
    com_regras, ajustes = motor_regras.aplicar_rastreado(rec, fundidos, config)
    diag = None
    if diagnostico:
        por: dict[str, dict[str, float]] = {}
        for fonte, lst in (("tfidf", c_tfidf), ("vetorial", c_vet), ("fuzzy", c_fuzzy)):
            for c in lst:
                por.setdefault(c.sigla, {})[fonte] = c.score
        diag = Diagnostico(scores_por_metodo=por)
    rec = replace(rec, diagnostico=diag) if diag is not None else rec
    decidido = roteador.rotear(replace(rec, candidatos=tuple(com_regras)), config)
    if ajustes and decidido.status == "decidido":
        motivos = "; ".join(a.motivo for a in ajustes)
        decidido = replace(
            decidido, justificativa=f"{decidido.justificativa} | regras: {motivos}"
        )
    if decidido.status == "decidido":
        decidido = _com_fase(decidido)
    return decidido


_MARGEM_DESEMPATE = 0.03


def _gap(rec: SignalRecord) -> float:
    cs = rec.candidatos
    if not cs:
        return 0.0
    if len(cs) == 1:
        return cs[0].score
    return cs[0].score - cs[1].score


def _desempatar_ambiguo(d_disc, d_ana, disc: "_Scorers", ana: "_Scorers", descricao: str):
    """Quando os dois bundles decidem, tenta resolver por gap (mais confiante)
    e, se os gaps forem próximos, pelo centroide do corpus (a quem a
    descrição se aproxima mais). Devolve o vencedor ou None (permanece
    ambíguo -> revisão manual)."""
    gap_disc, gap_ana = _gap(d_disc), _gap(d_ana)
    if abs(gap_disc - gap_ana) > _MARGEM_DESEMPATE:
        return d_disc if gap_disc > gap_ana else d_ana
    afin_disc = disc.indice.afinidade_centroide(descricao)
    afin_ana = ana.indice.afinidade_centroide(descricao)
    if afin_disc == afin_ana:
        return None
    return d_disc if afin_disc > afin_ana else d_ana


def _classificar_roteado(rec, disc: "_Scorers", ana: "_Scorers", diagnostico: bool, embedding_vet=None):
    """Devolve (decidido_ou_None, item_revisao_ou_None).

    Confiável: usa o bundle da própria categoria.
    Incerto: roda os dois; usa o único que decidir; se ambos decidirem,
    tenta desempatar (gap, depois centroide); só vai pra revisão se também
    o desempate for inconclusivo.
    """
    if rec.tipo_sinal.categoria_confiavel:
        bundle = disc if rec.tipo_sinal.categoria == "Discrete" else ana
        d = _classificar_sinal(rec, bundle, diagnostico=diagnostico, embedding_vet=embedding_vet)
        if d.status == "decidido":
            return d, None
        return None, ItemRevisao(d, motivo="score_baixo", candidatos_sugeridos=d.candidatos[:3])

    d_disc = _classificar_sinal(rec, disc, diagnostico=diagnostico, embedding_vet=embedding_vet)
    d_ana = _classificar_sinal(rec, ana, diagnostico=diagnostico, embedding_vet=embedding_vet)
    ok_disc = d_disc.status == "decidido"
    ok_ana = d_ana.status == "decidido"

    if ok_disc and ok_ana:
        vencedor = _desempatar_ambiguo(d_disc, d_ana, disc, ana, rec.descricoes.normalizada)
        if vencedor is not None:
            return vencedor, None
        cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
        return None, ItemRevisao(d_disc, motivo="categoria_ambigua", candidatos_sugeridos=cands)
    if ok_disc and not ok_ana:
        return d_disc, None
    if ok_ana and not ok_disc:
        return d_ana, None
    cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
    return None, ItemRevisao(d_disc, motivo="score_baixo", candidatos_sugeridos=cands)


def _aplicar_aliases(registros: list, aliases: dict[str, str] | None) -> list:
    if not aliases:
        return registros
    novos = []
    for r in registros:
        original = r.modulo.nome
        alias = aliases.get(original) if original else None
        if alias and alias != original:
            novo_id = r.id.replace(f"{original}:", f"{alias}:", 1)
            novo_mod = replace(r.modulo, nome=alias)
            r = replace(r, id=novo_id, modulo=novo_mod)
        novos.append(r)
    return novos


def gerar_tdt(registros, template_path, lp, subestacao=None, aliases=None):
    """Gera o workbook TDT a partir de uma lista (já decidida/editada) de registros."""
    lst = _aplicar_aliases(list(registros), aliases)
    pareados, _rev = dc_pairer.parear(lst)
    corrigidos, _rev2 = corrigir(list(pareados))
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    return engine_tdt.gerar(lista, template_path, lp)


def executar(
    input_path: str | Path,
    template_path: str | Path,
    lista_padrao_path: str | Path,
    *,
    config: Config,
    encoder,
    subestacao: str | None = None,
    modo: str = "auto",
    auditoria: Auditoria | None = None,
    diagnostico: bool = False,
    cancelado: "Callable[[], bool] | None" = None,
) -> tuple[ResultadoPipeline, openpyxl.Workbook]:
    aud = auditoria or Auditoria()
    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    cfg_analog = replace(
        config,
        peso_tfidf=config.peso_tfidf_analog,
        peso_vetorial=config.peso_vetorial_analog,
        peso_fuzzy=config.peso_fuzzy_analog,
        threshold_pct=config.threshold_pct_analog,
        threshold_gap=config.threshold_gap_analog,
    )
    disc = _construir_scorers(lp, config, encoder, "Discrete", config)
    ana = _construir_scorers(lp, config, encoder, "Analog", cfg_analog)
    corpus = _corpus(lp, config, "Discrete")  # ainda usado p/ vocab abaixo
    vocab = _vocab_dominio(corpus) if config.corrigir_typos else None
    ref_emb = disc.indice.vetores()  # já codificado em _construir_scorers; evita reencodar
    aud.evento("pipeline", f"lista padrão: {len(corpus)} sinais discretos", "INFO")

    wb_in = openpyxl.load_workbook(input_path, read_only=True, data_only=True)
    rota = classificar(wb_in, override=modo)
    aud.evento("identificador", f"homogêneo={rota.homogeneo}, {len(rota.sheets_dados)} sheets", "INFO")

    decididos: list[SignalRecord] = []
    revisao: list[ItemRevisao] = []

    for sn in rota.sheets_dados:
        if cancelado is not None and cancelado():
            aud.evento("pipeline", "cancelado pelo usuário", "AVISO")
            break
        rows = ler_rows(wb_in[sn])
        header_homog = detectar_header(rows) if rota.homogeneo else None
        if header_homog is not None:
            decididos_homog, sinais = estruturar_homogeneo(rows, header_homog, sn, lp, config)
            decididos.extend(decididos_homog)
        else:
            mapa = analisar(rows, encoder, ref_emb)
            sinais = list(estruturar(rows, mapa, sheet_name=sn, config=config, vocab=vocab))
        sinais = forcar_polaridade_equipamento(sinais, config)
        total = len(sinais)
        aud.evento("identificador", f"Sheet {sn}: {total} sinais lidos", "INFO")
        # Batch encode das descrições da sheet inteira — evita uma chamada ao
        # encoder por sinal (cada chamada individual ao sentence-transformer
        # tem overhead fixo significativo).
        if sinais:
            descricoes_lote = [r.descricoes.normalizada for r in sinais]
            emb_lote = encoder(descricoes_lote)
        else:
            emb_lote = []
        for j, rec in enumerate(sinais, 1):
            if cancelado is not None and cancelado():
                aud.evento("pipeline", "cancelado pelo usuário", "AVISO")
                break
            embedding_vet = emb_lote[j - 1] if len(emb_lote) else None
            if rec.status == "decidido":  # já resolvido pelo pareamento de polaridade
                decididos.append(rec)
                continue
            if not rec.enderecamento.indices:
                aud.evento("pipeline", f"{rec.id}: sem endereço — classificando sem decidir", "AVISO")
                decidido_tmp, item_tmp = _classificar_roteado(
                    rec, disc, ana, diagnostico, embedding_vet=embedding_vet
                )
                if decidido_tmp is not None:
                    rec_avaliado = decidido_tmp
                    candidatos_sugeridos = decidido_tmp.candidatos[:3]
                else:
                    rec_avaliado = item_tmp.registro
                    candidatos_sugeridos = item_tmp.candidatos_sugeridos
                revisao.append(ItemRevisao(
                    rec_avaliado, motivo="sem_endereco", candidatos_sugeridos=candidatos_sugeridos,
                ))
                continue
            decidido, item = _classificar_roteado(
                rec, disc, ana, diagnostico, embedding_vet=embedding_vet
            )
            if decidido is not None:
                decididos.append(decidido)
            else:
                revisao.append(item)
            if j % 50 == 0 or j == total:
                aud.evento("pipeline", f"Sheet {sn}: {j}/{total} sinais processados", "INFO")
        if cancelado is not None and cancelado():
            break
    wb_in.close()

    pareados, rev_pair = dc_pairer.parear(decididos)
    corrigidos, rev_estrut = corrigir(list(pareados))
    revisao.extend(rev_pair)
    revisao.extend(rev_estrut)

    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    wb_out = engine_tdt.gerar(lista, template_path, lp)

    aud.evento(
        "pipeline",
        f"decididos={len(lista.registros)} revisão={len(revisao)}",
        "INFO",
    )
    return ResultadoPipeline(lista=lista, revisao=tuple(revisao)), wb_out
