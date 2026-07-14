from dataclasses import replace

from tdt.config import Config
from tdt.contracts import (
    Candidato,
    Descricoes,
    Enderecamento,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao
from tdt.roteador import rotear

CFG = Config()  # threshold_pct=0.70, threshold_gap=0.15
# Passo de consenso é desligado por padrão (usar_consenso=False) — os testes
# que exercitam especificamente a cascata de consenso ligam a flag.
CFG_CONSENSO = replace(CFG, usar_consenso=True)


def _rec(candidatos):
    return SignalRecord(
        id="LT3:4",
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes("DJ", "DISJUNTOR"),
        candidatos=tuple(candidatos),
    )


def test_gap_alto_pct_alta_decide():
    r = rotear(_rec([Candidato("DJ", 0.91, "mesclado"), Candidato("SEC", 0.40, "mesclado")]), CFG)
    assert r.status == "decidido"
    assert r.sigla_sinal == "DJ"
    assert r.justificativa


def test_gap_baixo_pct_alta_revisao():
    # ambíguo: dois candidatos fortes e próximos
    r = rotear(_rec([Candidato("DJ", 0.91, "mesclado"), Candidato("DJE1", 0.88, "mesclado")]), CFG)
    assert r.status == "revisao"
    assert r.sigla_sinal is None


def test_pct_baixa_revisao():
    # abaixo do threshold_pct calibrado (0.45)
    r = rotear(_rec([Candidato("DJ", 0.30, "mesclado")]), CFG)
    assert r.status == "revisao"


def test_sem_candidatos_revisao():
    r = rotear(_rec([]), CFG)
    assert r.status == "revisao"
    assert "sem candidato" in r.justificativa.lower()


def test_candidato_unico_forte_decide():
    r = rotear(_rec([Candidato("DJ", 0.95, "mesclado")]), CFG)
    assert r.status == "decidido"
    assert r.sigla_sinal == "DJ"


# --- consenso + gap dinâmico + cascata rastreada (parâmetro votos) ---


def test_consenso_dois_metodos_decide():
    # 2 métodos concordam no top-1 acima do threshold -> decide (min_consenso=2)
    votos = {
        "tfidf": [Candidato("DJ", 0.80, "tfidf"), Candidato("SEC", 0.30, "tfidf")],
        "e5": [Candidato("DJ", 0.75, "e5"), Candidato("SEC", 0.40, "e5")],
    }
    r = rotear(_rec([Candidato("DJ", 0.90, "mesclado")]), CFG_CONSENSO, votos=votos)
    assert r.status == "decidido"
    assert r.sigla_sinal == "DJ"
    assert "consenso" in r.justificativa.lower()


def test_consenso_desligado_por_padrao_pula_para_quadrante():
    # Mesmo cenário de test_consenso_dois_metodos_decide, mas com a config
    # default (usar_consenso=False): decide pelo quadrante mesclado (gap=0.90
    # do único candidato), não pela justificativa de consenso.
    votos = {
        "tfidf": [Candidato("DJ", 0.80, "tfidf"), Candidato("SEC", 0.30, "tfidf")],
        "e5": [Candidato("DJ", 0.75, "e5"), Candidato("SEC", 0.40, "e5")],
    }
    r = rotear(_rec([Candidato("DJ", 0.90, "mesclado")]), CFG, votos=votos)
    assert r.status == "decidido"
    assert r.sigla_sinal == "DJ"
    assert "consenso" not in r.justificativa.lower()


def test_sem_consenso_vai_revisao():
    # cada método aponta sigla diferente -> nenhum consenso, gap mesclado também não salva
    votos = {
        "tfidf": [Candidato("DJ", 0.60, "tfidf"), Candidato("SEC", 0.55, "tfidf")],
        "e5": [Candidato("SEC", 0.62, "e5"), Candidato("DJ", 0.58, "e5")],
    }
    r = rotear(_rec([Candidato("DJ", 0.50, "mesclado"), Candidato("SEC", 0.49, "mesclado")]), CFG, votos=votos)
    assert r.status == "revisao"


def test_gap_dinamico_um_metodo_exige_gap_maior():
    # só 1 método confiante -> confiança "baixa" -> gap exigido = 0.15 (maior).
    # gap mesclado de 0.10 NÃO basta sob confiança baixa.
    votos = {
        "tfidf": [Candidato("DJ", 0.80, "tfidf"), Candidato("SEC", 0.20, "tfidf")],
        "e5": [Candidato("DJ", 0.30, "e5"), Candidato("SEC", 0.25, "e5")],
    }
    rec = _rec([Candidato("DJ", 0.60, "mesclado"), Candidato("SEC", 0.50, "mesclado")])
    r = rotear(rec, CFG_CONSENSO, votos=votos)
    assert r.status == "revisao"


def test_cascata_fuzzy_altissimo_decide_por_grafia():
    # fuzzy muito alto domina: decide por grafia e registra o método na justificativa
    votos = {
        "fuzzy": [Candidato("DJ", 0.99, "fuzzy")],
        "e5": [Candidato("DJ", 0.50, "e5")],
    }
    r = rotear(_rec([Candidato("DJ", 0.70, "mesclado")]), CFG, votos=votos)
    assert r.status == "decidido"
    assert r.sigla_sinal == "DJ"
    assert "fuzzy" in r.justificativa.lower()


def test_cascata_e5_altissimo_decide_por_semantica():
    votos = {
        "e5": [Candidato("DJ", 0.97, "e5")],
        "tfidf": [Candidato("DJ", 0.40, "tfidf")],
    }
    r = rotear(_rec([Candidato("DJ", 0.70, "mesclado")]), CFG, votos=votos)
    assert r.status == "decidido"
    assert "e5" in r.justificativa.lower()


# --- empate por descrição LP duplicada (SP-H Task 2) ---
#
# Causa raiz confirmada: a LP tem pares de siglas DIFERENTES com a mesma
# descrição-padrão (texto idêntico) -- ex. 81IE1/81E1. Como o scoring
# compara contra a descrição da LP, esses pares SEMPRE empatam (gap=0)
# para qualquer sinal de entrada -- um humano revisor também não teria
# como discriminar só pelo texto/metadados da LP. O roteador deve
# resolver isso deterministicamente (sigla alfabeticamente menor) em vez
# de mandar para revisão, mas só quando a descrição-padrão bate IGUAL
# (não é heurística de similaridade).


def _lp(pares: list[tuple[str, str]]) -> ListaPadraoADMS:
    """Constrói uma LP mínima: cada par (sigla, descricao)."""
    discretos = tuple(
        SinalPadrao(
            sigla=sigla, descricao=descricao, signal_type="SingleBit",
            direction="Input", mm="MM1", categoria="Discrete",
        )
        for sigla, descricao in pares
    )
    return ListaPadraoADMS(discretos=discretos, analogicos=())


def test_empate_descricao_lp_duplicada_decide_por_ordem_alfabetica():
    # 81IE1 e 81E1 têm a MESMA descrição-padrão na LP -> empate estrutural,
    # nunca discriminável por texto. Roteador decide pela sigla
    # alfabeticamente menor (81E1 < 81IE1) em vez de ir para revisão.
    lp = _lp([
        ("81IE1", "81 - TRIP SUB/SOBRE FREQUENCIA E1"),
        ("81E1", "81 - TRIP SUB/SOBRE FREQUENCIA E1"),
    ])
    rec = _rec([Candidato("81IE1", 0.60, "mesclado"), Candidato("81E1", 0.60, "mesclado")])
    r = rotear(rec, CFG, lista_padrao=lp)
    assert r.status == "decidido"
    assert r.sigla_sinal == "81E1"
    assert "empate_descricao_lp_duplicada" in r.justificativa


def test_empate_genuino_descricoes_diferentes_continua_revisao():
    # 51N2 e 51NL têm descrições DIFERENTES na LP -- empate genuíno, não é
    # bug de LP. Deve continuar indo para revisão como hoje (não regride).
    lp = _lp([
        ("51N2", "51 - SOBRECORRENTE TEMPORIZADA NEUTRO E2"),
        ("51NL", "51 - SOBRECORRENTE TEMPORIZADA LOCAL"),
    ])
    rec = _rec([Candidato("51N2", 0.60, "mesclado"), Candidato("51NL", 0.60, "mesclado")])
    r = rotear(rec, CFG, lista_padrao=lp)
    assert r.status == "revisao"
    assert r.sigla_sinal is None


def test_empate_descricao_lp_duplicada_mas_score_baixo_continua_revisao():
    # Mesmo par 81IE1/81E1 com descrição-padrão IDÊNTICA, mas os candidatos
    # empatam num score BAIXO (0.10 << threshold_pct=0.45) -- nenhum dos dois
    # atinge o piso de confiança mínimo exigido pelo caminho normal
    # (`pct_ok`). Empate estrutural na LP não deve bypassar essa checagem:
    # sem confiança mínima, mesmo tendo a MESMA descrição-padrão, o sinal
    # deve continuar em revisão (achado da revisão de código: faltava o
    # guard de `pct_ok` nesse caminho).
    lp = _lp([
        ("81IE1", "81 - TRIP SUB/SOBRE FREQUENCIA E1"),
        ("81E1", "81 - TRIP SUB/SOBRE FREQUENCIA E1"),
    ])
    rec = _rec([Candidato("81IE1", 0.10, "mesclado"), Candidato("81E1", 0.10, "mesclado")])
    r = rotear(rec, CFG, lista_padrao=lp)
    assert r.status == "revisao"
    assert r.sigla_sinal is None


# --- resgate por regras na zona cinzenta (SP-H Task 3) ---
#
# Zona cinzenta: pct_ok (candidato top passa do threshold_pct) mas gap
# insuficiente (< threshold_gap) -- hoje vai para revisão mesmo quando o
# motor de regras de domínio (numero de protecao, fase, opostos, etc.) já
# apontou exclusivamente para o topo (ajuste positivo) e não para o
# segundo colocado (ajuste zero ou negativo). ``ajustes`` é o mapa
# sigla->delta total aplicado pelas regras (calculado no pipeline a partir
# de ``motor_regras.aplicar_rastreado``, que devolve uma lista plana de
# ``AjusteRegra`` sem sigla -- o pipeline agrega por sigla antes de montar
# esse mapa).

_CANDS_ZONA_CINZENTA = [Candidato("SGFT", 0.62, "mesclado"), Candidato("SGT2", 0.58, "mesclado")]
# pct_ok: 0.62 >= threshold_pct(0.45); gap=0.04 < threshold_gap(0.08) -> gap_ok False


def test_resgate_por_regras_decide():
    rec = _rec(_CANDS_ZONA_CINZENTA)
    out = rotear(rec, CFG, ajustes={"SGFT": 0.15, "SGT2": 0.0})
    assert out.status == "decidido" and out.sigla_sinal == "SGFT"
    assert "resgate_regras" in out.justificativa


def test_sem_regra_exclusiva_vai_revisao():
    rec = _rec(_CANDS_ZONA_CINZENTA)
    out = rotear(rec, CFG, ajustes={"SGFT": 0.15, "SGT2": 0.15})
    assert out.status == "revisao"
    assert out.sigla_sinal is None


def test_resgate_desligado_por_config():
    cfg = replace(CFG, resgate_por_regras=False)
    rec = _rec(_CANDS_ZONA_CINZENTA)
    out = rotear(rec, cfg, ajustes={"SGFT": 0.15})
    assert out.status == "revisao"


# --- piso absoluto de confiança calibrada (SP-CVA E2) ---
#
# gap grande não deve decidir sozinho quando a confiança calibrada real do
# top-1 (score pós-mescla/calibração, ANTES do ajuste do motor de regras --
# esse é unbounded, spB-B2 pendente) é baixa. Ex. real: BC2 51F/51F1 -> FC87
# decidia hoje só pelo gap, mesmo com confiança calibrada ridícula.

_CANDS_PISO = [Candidato("FC87", 0.55, "mesclado"), Candidato("51F", 0.10, "mesclado")]
# pct_ok (0.55>=0.45) e gap_ok (0.45>=0.08) só por causa do ajuste de regra
# (+0.43); confiança calibrada real = 0.55-0.43 = 0.12.


def test_top1_abaixo_do_piso_calibrado_vai_para_revisao():
    rec = _rec(_CANDS_PISO)
    cfg = replace(CFG, piso_decisao=0.20)
    out = rotear(rec, cfg, ajustes={"FC87": 0.43, "51F": 0.0})
    assert out.status == "revisao"
    assert "score_baixo" in out.justificativa
    assert out.sigla_sinal is None


def test_piso_zero_preserva_comportamento_atual():
    rec = _rec(_CANDS_PISO)
    cfg = replace(CFG, piso_decisao=0.0)
    out = rotear(rec, cfg, ajustes={"FC87": 0.43, "51F": 0.0})
    assert out.status == "decidido"
    assert out.sigla_sinal == "FC87"
