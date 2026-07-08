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
    ancoragem_sigla,
    criador_lista_homogenea, dc_pairer, engine_tdt, especificidade_qualificador,
    expansao_candidatos, filtro_preciso,
    motor_regras, roteador, semantica_estados,
)
from tdt.motor_regras import fase_da_sigla
from tdt.analise.analise_colunas import analisar
from tdt.auditoria import Auditoria
from tdt.cache_scorers import carregar_ou_construir
from tdt.config import Config
from tdt.contracts import Diagnostico, ItemRevisao, ResultadoPipeline, SignalRecord
from tdt.dados.indice_vetorial import IndiceVetorial
from tdt.dados.lista_padrao import ListaPadraoADMS, descricoes_por_sigla
from tdt.defaults import DEFAULT_LISTA_ALIAS
from tdt.normalizacao.estruturador import estruturar
from tdt.normalizacao.estruturador_homogeneo import detectar_header, estruturar_homogeneo
from tdt.identidade_modulo import aplicar_identidade, particionar_por_confianca
from tdt.analise.identificador import classificar, ler_rows
from tdt.inferencia_topologia import (
    derivar_secao_por_linha, inferir_equipamento, subdividir_transformador_at_bt,
)
from tdt.matchers.fuzzy_match import FuzzyMatcher
from tdt.normalizacao.normalizador import canonizar, normalizar
from tdt.normalizador_estrutural import corrigir
from tdt.pareamento_polaridade import forcar_polaridade_equipamento
from tdt.scoring import mescla
from tdt.scoring.calibracao import aplicar_calibrador_confianca, calibrar_candidatos
from tdt.scoring.bm25 import ScorerBM25
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
        tfidf=ScorerBM25.construir(corpus_raw),
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


def _whitelist_posicao(lp: ListaPadraoADMS, config: Config | None = None) -> frozenset[str]:
    """Siglas fundíveis em MultiCoord (D3): SwitchStatus da lista padrão +
    extras de config."""
    wl = frozenset(
        s.sigla.upper() for s in lp.discretos if s.signal_type == "SwitchStatus"
    )
    extra = config.siglas_fundiveis_extra if config is not None else frozenset()
    return wl | extra


def _com_fase(rec: SignalRecord) -> SignalRecord:
    """Grava a fase derivada da sigla decidida em ``eletrico.fase`` (se vazia).

    ``fase_da_sigla`` devolve ``"F"`` como sentinela de fase genérica (usado no
    scoring de ``r3_fase``); proteção genérica trifásica = ``ABC`` na saída.
    """
    if rec.sigla_sinal and rec.eletrico.fase is None:
        f = fase_da_sigla(rec.sigla_sinal.upper())
        if f == "F":
            f = "ABC"
        if f:
            return replace(rec, eletrico=replace(rec.eletrico, fase=f))
    return rec


def _etapa_decisora(rec: SignalRecord) -> str:
    """Deriva a etapa do pipeline que decidiu a sigla a partir do prefixo de
    ``justificativa`` -- os módulos de decisão (roteador, resgate por
    regras, qualificador) já escrevem um texto distinto por caminho; não
    duplica essa informação num enum novo, só a rotula p/ auditoria."""
    if rec.status != "decidido":
        return ""
    j = rec.justificativa or ""
    if "por qualificador" in j:
        return "qualificador_irmao"
    if "por resgate_regras" in j:
        return "resgate_regras"
    if "por fuzzy" in j:
        return "cascata_fuzzy"
    if "por e5" in j:
        return "cascata_e5"
    if "por consenso" in j:
        return "cascata_consenso"
    if "empate_descricao_lp_duplicada" in j:
        return "empate_descricao_lp"
    if j.startswith("decidido") or " decidido (" in j:
        return "quadrante"
    return "pre_scoring"  # pareamento de polaridade / sigla pré-classificada por coluna


def _registrar_diagnostico(
    diag_extra: "dict[str, dict] | None",
    rec: SignalRecord,
    decidido: SignalRecord,
    ajustes: "list",
    gap: float,
    gap_exigido: float,
    config: Config,
) -> None:
    """Grava o contexto de decisão de ``rec`` em ``diag_extra`` (mapa
    id->dict, dono é o pipeline/chamador -- não é estado global, só um
    acumulador local passado explicitamente, no mesmo espírito de
    ``Auditoria``). No-op quando ``diag_extra`` é None (chamadores que não
    pedem auditoria estendida, ex. testes legados)."""
    if diag_extra is None:
        return
    entrada = diag_extra.setdefault(rec.id, {})  # preserva "endereco_bruto" já gravado
    entrada.update({
        "desc_normalizada": normalizar(rec.descricoes.bruta, config),
        "regras_aplicadas": "; ".join(a.motivo for a in ajustes) if ajustes else "",
        "gap": gap,
        "gap_exigido": gap_exigido,
        "etapa_decisora": _etapa_decisora(decidido),
    })


def _classificar_sinal(
    rec, scorers: "_Scorers", diagnostico: bool = False, embedding_vet=None,
    lista_padrao: "ListaPadraoADMS | None" = None,
    ancoras: "list | None" = None,
    diag_extra: "dict[str, dict] | None" = None,
) -> SignalRecord:
    # Ordem do funil de decisão (mapa p/ "onde entra minha nova regra?"):
    # filtros (filtro_preciso, semantica_estados, whitelist) removem
    # candidatos POR CAUSA -> motor_regras ajusta scores dos que sobraram ->
    # roteador escolhe o topo -> correções pós-decisão (fase,
    # especificidade_qualificador) podem sobrescrever a escolha do roteador,
    # mas só dentro de um escopo estreito e específico (não re-filtram nem
    # re-pontuam candidatos).
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
        if ancoras:
            fundidos = ancoragem_sigla.ancorar(fundidos, ancoras, config.ancora_sigla_score)
        fundidos = expansao_candidatos.expandir(fundidos, lista_padrao)
        if ancoras:
            # A expansão por prefixo de 2 dígitos reintroduz ramos irmãos
            # (67F*/67P*) que a sigla âncora explícita (67N) exclui. Restringe
            # cada família ancorada ao sub-ramo da âncora antes dos filtros.
            fundidos = ancoragem_sigla.filtrar_subarvore(fundidos, ancoras)
        fundidos = filtro_preciso.filtrar(rec, fundidos, config)
        fundidos = filtro_preciso.filtrar_especificidade(rec, fundidos, lista_padrao, config)
        # SP-E D2: filtro duro estado-detectado × par de estados do MM.
        if config.filtro_semantica_estados:
            fundidos, zerou = semantica_estados.filtrar_por_estado(
                rec, fundidos, lista_padrao
            )
            if zerou:
                return replace(
                    rec, candidatos=tuple(fundidos[:3]), status="revisao",
                    justificativa="estado_sem_candidato",
                )
        # SP-E D6: whitelist de siglas por equipamento (só extração explícita).
        wl_equip = config.siglas_por_equipamento.get(rec.eletrico.equipamento_alvo or "")
        if wl_equip and not rec.eletrico.equipamento_inferido:
            dentro = [c for c in fundidos if c.sigla.upper() in wl_equip]
            if fundidos and not dentro:
                return replace(
                    rec, candidatos=tuple(fundidos[:3]), status="revisao",
                    justificativa="fora_whitelist_equipamento",
                )
            fundidos = dentro
    com_regras, ajustes = motor_regras.aplicar_rastreado(
        rec, fundidos, config, lista_padrao=lista_padrao
    )
    # Mapa sigla->delta total das regras, para o resgate na zona cinzenta do
    # roteador (SP-H Task 3). `aplicar_rastreado` devolve só a lista plana de
    # AjusteRegra (delta+motivo, sem sigla) para a justificativa -- o delta
    # por sigla é recomputado aqui comparando o score antes/depois das
    # regras (casado por sigla; `aplicar_rastreado` só re-pontua e reordena
    # candidatos existentes, não renomeia siglas nem duplica).
    scores_antes = {c.sigla: c.score for c in fundidos}
    ajustes_por_sigla: dict[str, float] = {
        c.sigla: c.score - scores_antes.get(c.sigla, c.score) for c in com_regras
    }
    diag = None
    if diagnostico:
        por: dict[str, dict[str, float]] = {}
        for fonte, lst in (("tfidf", c_tfidf), ("vetorial", c_vet), ("fuzzy", c_fuzzy)):
            for c in lst:
                por.setdefault(c.sigla, {})[fonte] = c.score
        diag = Diagnostico(scores_por_metodo=por)
    rec = replace(rec, diagnostico=diag) if diag is not None else rec
    decidido = roteador.rotear(
        replace(rec, candidatos=tuple(com_regras)), config,
        lista_padrao=lista_padrao, ajustes=ajustes_por_sigla,
    )
    if ajustes and decidido.status == "decidido":
        motivos = "; ".join(a.motivo for a in ajustes)
        decidido = replace(
            decidido, justificativa=f"{decidido.justificativa} | regras: {motivos}"
        )
    if decidido.status == "decidido":
        decidido = _com_fase(decidido)
    if lista_padrao is not None:
        decidido = especificidade_qualificador.preferir_irmao_qualificado(
            decidido, lista_padrao, config
        )
    _registrar_diagnostico(
        diag_extra, rec, decidido, ajustes, _gap(decidido), config.threshold_gap, config,
    )
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


# Domínios que cada categoria de sinal admite no dual-pass. DiscreteAnalog (e
# qualquer categoria não mapeada, via .get default) admite os dois — equivale
# ao dual-pass livre de antes nesse caso.
_DOMINIOS_POR_CATEGORIA: dict[str, frozenset[str]] = {
    "Discrete": frozenset({"Discrete"}),
    "Analog": frozenset({"Analog"}),
    "DiscreteAnalog": frozenset({"Discrete", "Analog"}),
}


def _classificar_roteado(rec, disc: "_Scorers", ana: "_Scorers", diagnostico: bool,
                         embedding_vet=None, lista_padrao: "ListaPadraoADMS | None" = None,
                         diag_extra: "dict[str, dict] | None" = None):
    """Devolve (decidido_ou_None, item_revisao_ou_None).

    Confiável: usa o bundle da própria categoria.

    Incerto (categoria_confiavel=False): roda os dois bundles, mas só aceita
    a decisão de um bundle cujo domínio seja admitido por
    ``rec.tipo_sinal.categoria`` (barreira de domínio — ver
    docs/superpowers/specs/2026-06-29-sp-categoria-dual-pass-fix-design.md).

    ``rec.tipo_sinal.categoria`` pode ser um placeholder sem evidência real
    quando a sheet não tinha coluna Tipo nem marcador de seção (estruturador
    cai no default "Discrete"). Por isso, quando o domínio barrado TAMBÉM
    decidiu (conflito real, não só score baixo), não se auto-aceita o lado
    "permitido" — vai para revisão (categoria_ambigua), igual ao caso em que
    os dois bundles decidem dentro do mesmo domínio admitido. Barrar só
    "vence" silenciosamente quando o lado barrado é o único que decidiu
    (motivo categoria_incompativel) — aí sim é o FP cross-categoria que esta
    barreira existe para eliminar.
    """
    _cfg = disc.config
    _ancora_ativa = _cfg.ancora_sigla_ativa and lista_padrao is not None

    if rec.tipo_sinal.categoria_confiavel:
        bundle = disc if rec.tipo_sinal.categoria == "Discrete" else ana
        categoria_bundle = "Discrete" if rec.tipo_sinal.categoria == "Discrete" else "Analog"
        _ancoras = (
            ancoragem_sigla.detectar(rec, lista_padrao, categoria_bundle)
            if _ancora_ativa else []
        )
        _multiplas = ancoragem_sigla.tem_multiplas_familias(_ancoras)
        d = _classificar_sinal(rec, bundle, diagnostico=diagnostico, embedding_vet=embedding_vet,
                               lista_padrao=lista_padrao, ancoras=_ancoras, diag_extra=diag_extra)
        if d.status == "decidido":
            return d, None
        if d.status == "revisao" and d.justificativa in (
            "estado_sem_candidato", "fora_whitelist_equipamento", "qualificador_ambiguo",
        ):
            return None, ItemRevisao(
                d, motivo=d.justificativa, candidatos_sugeridos=d.candidatos[:3]
            )
        motivo_conf = "sigla_multipla" if _multiplas else "score_baixo"
        return None, ItemRevisao(d, motivo=motivo_conf, candidatos_sugeridos=d.candidatos[:3])

    _ancoras_disc = (
        ancoragem_sigla.detectar(rec, lista_padrao, "Discrete")
        if _ancora_ativa else []
    )
    _ancoras_ana = (
        ancoragem_sigla.detectar(rec, lista_padrao, "Analog")
        if _ancora_ativa else []
    )
    d_disc = _classificar_sinal(rec, disc, diagnostico=diagnostico, embedding_vet=embedding_vet,
                                lista_padrao=lista_padrao, ancoras=_ancoras_disc)
    d_ana = _classificar_sinal(rec, ana, diagnostico=diagnostico, embedding_vet=embedding_vet,
                               lista_padrao=lista_padrao, ancoras=_ancoras_ana)
    decidiu_disc = d_disc.status == "decidido"
    decidiu_ana = d_ana.status == "decidido"

    dominios = _DOMINIOS_POR_CATEGORIA.get(
        rec.tipo_sinal.categoria, frozenset({"Discrete", "Analog"})
    )
    permite_disc = "Discrete" in dominios
    permite_ana = "Analog" in dominios
    ok_disc = decidiu_disc and permite_disc
    ok_ana = decidiu_ana and permite_ana

    if ok_disc and ok_ana:
        vencedor = _desempatar_ambiguo(d_disc, d_ana, disc, ana, rec.descricoes.normalizada)
        if vencedor is not None:
            return vencedor, None
        cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
        return None, ItemRevisao(d_disc, motivo="categoria_ambigua", candidatos_sugeridos=cands)

    if decidiu_disc and decidiu_ana:
        # Ambos decidiram, mas a barreira bloqueia ao menos um -> conflito
        # real entre domínios. Categoria pode ser placeholder sem evidência
        # (ver docstring) — não auto-aceita o lado "permitido".
        cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
        base = d_disc if permite_disc else d_ana
        return None, ItemRevisao(base, motivo="categoria_ambigua", candidatos_sugeridos=cands)

    if ok_disc:
        return d_disc, None
    if ok_ana:
        return d_ana, None

    # Nenhum bundle decidiu DENTRO do domínio admitido.
    decidiu_fora = decidiu_disc or decidiu_ana
    base = d_disc if permite_disc else (d_ana if permite_ana else d_disc)
    motivo = "categoria_incompativel" if decidiu_fora else "score_baixo"
    if motivo == "score_baixo" and ancoragem_sigla.tem_multiplas_familias(
        _ancoras_disc + _ancoras_ana
    ):
        motivo = "sigla_multipla"
    cands = d_disc.candidatos[:3] + d_ana.candidatos[:3]
    return None, ItemRevisao(base, motivo=motivo, candidatos_sugeridos=cands)


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


def gerar_tdt(registros, template_path, lp, subestacao=None, aliases=None, config=None):
    """Gera o workbook TDT a partir de uma lista (já decidida/editada) de registros."""
    lst = _aplicar_aliases(list(registros), aliases)
    pareados, _rev = dc_pairer.parear(lst, config)
    corrigidos, _rev2 = corrigir(list(pareados), _whitelist_posicao(lp, config))
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
    return engine_tdt.gerar(
        lista, template_path, lp, alias_v1=descricoes_por_sigla(DEFAULT_LISTA_ALIAS)
    )


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
    sheets: "list[str] | None" = None,
    aliases: "dict[str, str] | None" = None,
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
    rota = classificar(wb_in, override=modo, config=config)
    sheets_dados = rota.sheets_dados
    if sheets is not None:
        selecionadas = set(sheets)
        sheets_dados = [sn for sn in sheets_dados if sn in selecionadas]
    aud.evento("identificador", f"homogêneo={rota.homogeneo}, {len(sheets_dados)} sheets", "INFO")

    decididos: list[SignalRecord] = []
    revisao: list[ItemRevisao] = []
    # id -> dict de contexto de decisão p/ auditoria estendida (SP-J Task 1).
    # Acumulador local do pipeline (não é estado global -- vive só durante
    # esta chamada de `executar`, devolvido em `ResultadoPipeline.diagnostico`).
    diag_extra: dict[str, dict] = {}

    for sn in sheets_dados:
        if cancelado is not None and cancelado():
            aud.evento("pipeline", "cancelado pelo usuário", "AVISO")
            break
        rows = ler_rows(wb_in[sn])
        header_homog = detectar_header(rows) if rota.homogeneo else None
        if header_homog is not None:
            decididos_homog, sinais = estruturar_homogeneo(rows, header_homog, sn, lp, config)
            decididos.extend(decididos_homog)
        else:
            mapa = analisar(rows, encoder, ref_emb, siglas_set=lp.siglas)
            sinais = list(estruturar(rows, mapa, sheet_name=sn, config=config, vocab=vocab,
                                     siglas_set=lp.siglas))
        sinais, conf_mod = aplicar_identidade(sinais, sn, rows, config)
        alias_sheet = aliases.get(sn) if aliases else None
        if alias_sheet:
            sinais = [
                replace(s, modulo=replace(s.modulo, nome=alias_sheet))
                if s.modulo.origem_contexto == "sheet_name"
                else s
                for s in sinais
            ]
        sinais, rev_modulo = particionar_por_confianca(sinais, conf_mod)
        ids_indefinidos: set[str] = set()
        if rev_modulo:
            aud.evento("identidade_modulo",
                       f"Sheet {sn}: módulo indefinido — {len(rev_modulo)} sinais p/ revisão",
                       "AVISO")
            ids_indefinidos = {ir.registro.id for ir in rev_modulo}
        sinais, rev_polaridade = forcar_polaridade_equipamento(sinais, config)
        revisao.extend(rev_polaridade)
        # C2.4 (antes de C2.2): subdivide módulo Transformador por lado AT/BT
        # quando há pista — precisa decidir o nome do módulo ANTES da
        # inferência de equipamento (Transformador não tem default
        # não-ambíguo sem o lado) e antes do scoring/dc_pairer agrupar por
        # módulo (correntes/tensões do AT e do BT colidiriam na chave de
        # dedup sem isso).
        secao_por_linha = derivar_secao_por_linha(rows, sn)
        sinais = subdividir_transformador_at_bt(sinais, config, secao_por_linha)
        # C2.2/C2.3 (spC2): infere equipamento_alvo pela topologia do tipo de
        # módulo p/ alimentar r_equipamento/r3_fase no scoring. Família não
        # inferida NÃO bloqueia: o sinal com sigla decidida segue para o
        # dc_pairer, que arbitra sem-comando -> TDT / comando ambíguo ->
        # pareamento_ambiguo (Spec C, supersede o gate equipamento_ambiguo).
        sinais = inferir_equipamento(sinais, config)
        # Endereço bruto, capturado ANTES do dc_pairer (que reatribui
        # `indices` a partir de `indices_saida` ao fundir pares D+C -- ver
        # `dc_pairer.py:69`) -- p/ a auditoria mostrar o endereço como lido,
        # não o resultado do pareamento.
        for r in sinais:
            diag_extra.setdefault(r.id, {})["endereco_bruto"] = (
                ";".join(str(i) for i in r.enderecamento.indices)
            )
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
            if rec.status == "revisao":  # sigla de coluna inconsistente com NOME
                revisao.append(ItemRevisao(
                    rec, motivo=rec.justificativa or "sigla_inconsistente",
                ))
                continue
            if not rec.enderecamento.indices:
                aud.evento("pipeline", f"{rec.id}: sem endereço — classificando sem decidir", "AVISO")
                decidido_tmp, item_tmp = _classificar_roteado(
                    rec, disc, ana, diagnostico, embedding_vet=embedding_vet,
                    lista_padrao=lp, diag_extra=diag_extra,
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
                lista_padrao=lp, diag_extra=diag_extra,
            )
            if decidido is not None:
                if (decidido.sigla_sinal or "").upper() in config.siglas_revisao_projeto:
                    revisao.append(ItemRevisao(
                        decidido, motivo="decisao_por_projeto",
                        candidatos_sugeridos=decidido.candidatos[:3],
                    ))
                elif rec.id in ids_indefinidos:
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
        pareados, rev_pair = dc_pairer.parear(decididos, config)
        corrigidos, rev_estrut = corrigir(list(pareados), _whitelist_posicao(lp, config))
        revisao.extend(rev_pair)
        revisao.extend(rev_estrut)

        lista = criador_lista_homogenea.montar(list(corrigidos), subestacao=subestacao)
        alias_v1 = descricoes_por_sigla(DEFAULT_LISTA_ALIAS)
        if not alias_v1:
            aud.evento(
                "pipeline",
                f"lista v1 ausente ({DEFAULT_LISTA_ALIAS}): Signal Alias usa descrição do cliente",
                "WARN",
            )
        wb_out = engine_tdt.gerar(lista, template_path, lp, alias_v1=alias_v1)

    aud.evento(
        "pipeline",
        f"decididos={len(lista.registros)} revisão={len(revisao)}",
        "INFO",
    )
    return (
        ResultadoPipeline(lista=lista, revisao=tuple(revisao), diagnostico=diag_extra),
        wb_out,
    )
