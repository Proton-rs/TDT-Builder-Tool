"""Orquestrador do SP1 — o único módulo que conhece todos os outros.

input.xlsx -> ListaHomogenea -> TDT.xlsx, coletando os sinais que foram para
revisão. Embeddings/scorers são construídos uma vez a partir da lista padrão.

Discretos e analógicos têm bundles de scorers próprios (mesmo código,
config derivada por categoria). Sinais com categoria estruturalmente
incerta (`categoria_confiavel=False`) passam pelos dois bundles num
dual-pass; usa-se o único que decidir, ou vão para revisão.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
from typing import Callable, NamedTuple

import openpyxl

from tdt import (
    criador_lista_homogenea, dc_pairer, engine_tdt, expansao_candidatos, filtro_preciso,
    motor_regras, roteador,
)
from tdt.motor_regras import fase_da_sigla
from tdt.analise.analise_colunas import analisar
from tdt.auditoria import Auditoria
from tdt.cache_scorers import carregar_ou_construir
from tdt.config import Config
from tdt.contracts import Diagnostico, ItemRevisao, ResultadoPipeline, SignalRecord
from tdt.dados.indice_vetorial import IndiceVetorial
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.normalizacao.estruturador import estruturar
from tdt.normalizacao.estruturador_homogeneo import detectar_header, estruturar_homogeneo
from tdt.identidade_modulo import aplicar_identidade, particionar_por_confianca
from tdt.analise.identificador import classificar, ler_rows
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.normalizacao.normalizador import canonizar
from tdt.normalizador_estrutural import corrigir
from tdt.pareamento_polaridade import forcar_polaridade_equipamento
from tdt.scoring import mescla
from tdt.scoring.calibracao import aplicar_calibrador_confianca, calibrar_candidatos
from tdt.scoring.tfidf import ScorerTFIDF
from tdt.scoring.vetorial import pontuar as pontuar_vetorial
from tdt.scoring.vetorial import pontuar_com_embedding


@contextmanager
def _timer(nome: str, aud: Auditoria):
    """Mede o tempo de uma etapa e registra um evento "perf" na auditoria.

    Não suprime exceções: se a etapa falhar, o tempo até a falha ainda é
    registrado e a exceção propaga normalmente (nenhum mascaramento de erro).
    """
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = time.perf_counter() - t0
        aud.evento("perf", f"{nome}: {dt:.2f}s")


def _corpus(lp: ListaPadraoADMS, config: Config, categoria: str = "Discrete") -> list[tuple[str, str]]:
    """Corpus base: descrição canônica (para TF-IDF e fuzzy)."""
    fonte = lp.discretos if categoria == "Discrete" else lp.analogicos
    return [
        (s.sigla, canonizar(s.descricao, config))
        for s in fonte
        if s.descricao
    ]


def _corpus_enriquecido(lp: ListaPadraoADMS, config: Config, categoria: str = "Discrete") -> list[tuple[str, str]]:
    """Corpus com descrição enriquecida: sigla + descrição + metadados (para embeddings).
    
    A adição da sigla e metadados fornece mais contexto semântico para o
    embedding, melhorando matches onde a descrição isolada é ambígua.
    """
    fonte = lp.discretos if categoria == "Discrete" else lp.analogicos
    saida: list[tuple[str, str]] = []
    for s in fonte:
        if not s.descricao:
            continue
        partes = [s.sigla, s.descricao]
        if s.tipo_medicao:
            partes.append(s.tipo_medicao)
        if s.unidade_exibicao and s.unidade_exibicao not in ("-", ""):
            partes.append(s.unidade_exibicao)
        if s.direction:
            partes.append(s.direction)
        saida.append((s.sigla, canonizar(" ".join(partes), config)))
    return saida


class _Scorers(NamedTuple):
    tfidf: object
    indice: object
    fuzzy: object
    config: Config


def _construir_scorers(lp, config, encoder, categoria, cfg_efetivo) -> _Scorers:
    corpus_raw = _corpus(lp, config, categoria)
    corpus_vec = _corpus_enriquecido(lp, config, categoria)
    return _Scorers(
        tfidf=ScorerTFIDF.construir(corpus_raw),
        indice=IndiceVetorial.construir(corpus_vec, encoder),
        fuzzy=FuzzyMatcher.construir(corpus_raw),
        config=cfg_efetivo,
    )


def _construir_scorers_cacheado(
    lp, config, encoder, categoria, cfg_efetivo, cache_dir: "str | Path | None"
) -> _Scorers:
    """Como `_construir_scorers`, mas reaproveita tfidf/fuzzy/indice de um cache
    em disco quando o corpus (siglas+descrições da lista padrão) não mudou.

    `cache_dir=None` desliga o cache (usado em testes, para não tocar disco
    fora de `tmp_path` e manter o comportamento anterior intacto).
    """
    if cache_dir is None:
        return _construir_scorers(lp, config, encoder, categoria, cfg_efetivo)
    corpus_vec = _corpus_enriquecido(lp, config, categoria)
    cacheaveis = carregar_ou_construir(
        cache_dir,
        corpus_vec,  # chave de cache usa corpus enriquecido (superset)
        lambda: _construir_scorers(lp, config, encoder, categoria, cfg_efetivo),
        encoder,
        config.modelo_embedding,
    )
    return _Scorers(
        tfidf=cacheaveis.tfidf,
        indice=cacheaveis.indice,
        fuzzy=cacheaveis.fuzzy,
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
    rec, scorers: "_Scorers", diagnostico: bool = False, embedding_vet=None,
    lista_padrao: "ListaPadraoADMS | None" = None,
) -> SignalRecord:
    config = scorers.config
    c_tfidf = scorers.tfidf.pontuar(rec, k=config.k_vizinhos)
    if embedding_vet is not None:
        c_vet = pontuar_com_embedding(embedding_vet, rec, scorers.indice, k=config.k_vizinhos)
    else:
        c_vet = pontuar_vetorial(rec, scorers.indice, k=config.k_vizinhos)
    c_fuzzy = scorers.fuzzy.pontuar(rec, k=config.k_vizinhos)
    cal_metodo = config.calibracao_por_metodo
    def _cal(metodo_cfg):
        if not metodo_cfg:
            return "none", None
        return metodo_cfg.get("metodo", "none"), metodo_cfg.get("params")
    c_tfidf = calibrar_candidatos(c_tfidf, *_cal(cal_metodo.get("tfidf")))
    c_vet = calibrar_candidatos(c_vet, *_cal(cal_metodo.get("vetorial")))
    c_fuzzy = calibrar_candidatos(c_fuzzy, *_cal(cal_metodo.get("fuzzy")))
    fundidos = mescla.mesclar(
        [
            (c_tfidf, config.peso_tfidf),
            (c_vet, config.peso_vetorial),
            (c_fuzzy, config.peso_fuzzy),
        ]
    )
    if config.confianca_calibrador.get("metodo") not in (None, "none"):
        ca = config.confianca_calibrador
        fundidos = [
            replace(c, score=aplicar_calibrador_confianca(c.score, ca))
            for c in fundidos
        ]
    # F1 + Filtro Preciso: expande candidatos e remove contraditórios
    if lista_padrao is not None:
        fundidos = expansao_candidatos.expandir(fundidos, lista_padrao)
        fundidos = filtro_preciso.filtrar(rec, fundidos, config)
        fundidos = filtro_preciso.filtrar_especificidade(rec, fundidos, lista_padrao, config)
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


def _classificar_roteado(rec, disc: "_Scorers", ana: "_Scorers", diagnostico: bool,
                         embedding_vet=None, lista_padrao: "ListaPadraoADMS | None" = None):
    """Devolve (decidido_ou_None, item_revisao_ou_None).

    Confiável: usa o bundle da própria categoria.
    Incerto: roda os dois; usa o único que decidir; se ambos decidirem,
    tenta desempatar (gap, depois centroide); só vai pra revisão se também
    o desempate for inconclusivo.
    """
    if rec.tipo_sinal.categoria_confiavel:
        bundle = disc if rec.tipo_sinal.categoria == "Discrete" else ana
        d = _classificar_sinal(rec, bundle, diagnostico=diagnostico, embedding_vet=embedding_vet,
                               lista_padrao=lista_padrao)
        if d.status == "decidido":
            return d, None
        return None, ItemRevisao(d, motivo="score_baixo", candidatos_sugeridos=d.candidatos[:3])

    d_disc = _classificar_sinal(rec, disc, diagnostico=diagnostico, embedding_vet=embedding_vet,
                                lista_padrao=lista_padrao)
    d_ana = _classificar_sinal(rec, ana, diagnostico=diagnostico, embedding_vet=embedding_vet,
                               lista_padrao=lista_padrao)
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
    cache_scorers_dir: "str | Path | None" = None,
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
    with _timer("construir scorers disc", aud):
        disc = _construir_scorers_cacheado(lp, config, encoder, "Discrete", config, cache_scorers_dir)
    with _timer("construir scorers ana", aud):
        ana = _construir_scorers_cacheado(lp, config, encoder, "Analog", cfg_analog, cache_scorers_dir)
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
        sinais, conf_mod = aplicar_identidade(sinais, sn, rows, config)
        sinais, rev_modulo = particionar_por_confianca(sinais, conf_mod)
        ids_indefinidos: set[str] = set()
        if rev_modulo:
            aud.evento("identidade_modulo",
                       f"Sheet {sn}: módulo indefinido — {len(rev_modulo)} sinais p/ revisão",
                       "AVISO")
            ids_indefinidos = {ir.registro.id for ir in rev_modulo}
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
                    rec, disc, ana, diagnostico, embedding_vet=embedding_vet,
                    lista_padrao=lp,
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
                rec, disc, ana, diagnostico, embedding_vet=embedding_vet,
                lista_padrao=lp,
            )
            if decidido is not None:
                if rec.id in ids_indefinidos:
                    revisao.append(ItemRevisao(decidido, motivo="modulo_indefinido",
                                               candidatos_sugeridos=decidido.candidatos[:3]))
                else:
                    decididos.append(decidido)
            else:
                revisao.append(item)
            if j % 50 == 0 or j == total:
                aud.evento(
                    "pipeline", f"Sheet {sn}: {j}/{total} sinais processados", "INFO",
                    dados={"atual": j, "total": total},
                )
        if cancelado is not None and cancelado():
            break
    wb_in.close()

    with _timer("dc_pairer + corrigir + montar + tdt", aud):
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
