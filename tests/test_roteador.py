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
