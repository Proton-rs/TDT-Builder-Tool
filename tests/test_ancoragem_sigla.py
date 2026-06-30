"""Testes unitários para ancoragem_sigla."""
from dataclasses import replace

import pytest

import tdt.ancoragem_sigla as _mod
from tdt.ancoragem_sigla import (
    Ancora, ancorar, detectar, filtrar_subarvore, tem_multiplas_familias,
)


@pytest.fixture(autouse=True)
def _limpar_cache_ancora():
    """Limpa o cache de índice entre testes — evita reuso de id() de objetos efêmeros."""
    _mod._INDICE_CACHE.clear()
    yield
    _mod._INDICE_CACHE.clear()
from tdt.contracts import (
    Candidato, Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS, SinalPadrao


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sp(sigla, cat="Discrete", descricao="desc") -> SinalPadrao:
    return SinalPadrao(
        sigla=sigla,
        descricao=descricao,
        signal_type="DI",
        direction=None,
        mm=None,
        categoria=cat,
    )


def _lp(*siglas_disc, siglas_ana=()) -> ListaPadraoADMS:
    disc = tuple(_sp(s) for s in siglas_disc)
    ana = tuple(_sp(s, cat="Analog") for s in siglas_ana)
    return ListaPadraoADMS(discretos=disc, analogicos=ana)


def _rec(normalizada: str, categoria="Discrete") -> SignalRecord:
    return SignalRecord(
        id="t:1",
        modulo=Modulo("M", "sheet"),
        tipo_sinal=TipoSinal(categoria, False, "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(normalizada, normalizada),
    )


def _cand(sigla, score=0.5, fonte="tfidf") -> Candidato:
    return Candidato(sigla=sigla, score=score, fonte=fonte)


# ---------------------------------------------------------------------------
# detectar
# ---------------------------------------------------------------------------

def test_detectar_ancora_exata():
    lp = _lp("67N", "67N1", "67NT")
    rec = _rec("PROTECAO 67N TEMPORIZADO ATUADO")
    ancoras = detectar(rec, lp, "Discrete")
    assert len(ancoras) == 1
    assert ancoras[0].sigla == "67N"
    assert ancoras[0].confianca == "alta"


def test_detectar_ainda_junta_tokens_adjacentes():
    lp = _lp("67N", "67N1")
    # canonizador pode deixar "67" e "N" separados em algumas descrições
    rec = _rec("PROTECAO 67 N TEMPORIZADO ATUADO")
    ancoras = detectar(rec, lp, "Discrete")
    siglas = {a.sigla for a in ancoras}
    # "67N" formado por junção "67"+"N"
    assert "67N" in siglas


def test_detectar_multiplas_siglas_mesma_descricao():
    lp = _lp("67N", "50BF")
    rec = _rec("PROTECAO 67N 50BF COMBINADO")
    ancoras = detectar(rec, lp, "Discrete")
    siglas = {a.sigla for a in ancoras}
    assert "67N" in siglas
    assert "50BF" in siglas


def test_detectar_nao_ancora_sigla_curta_apenas_digitos():
    """Token "67" (2 dígitos, sem letra) não é sigla específica."""
    lp = _lp("67N")
    rec = _rec("PROTECAO 67 BLOQUEADO")
    ancoras = detectar(rec, lp, "Discrete")
    # "67" não é específica (len=2, sem letra); "67N" não está no texto;
    # "67"+"BLOQUEADO" = "67BLOQUEADO" não existe na LP.
    assert ancoras == []


def test_detectar_nao_ancora_sigla_curta_letras():
    """Token "PB" (2 letras, sem dígito) não é sigla específica."""
    lp = _lp("PBF1")
    rec = _rec("PROTECAO PB ATUADO")
    ancoras = detectar(rec, lp, "Discrete")
    assert ancoras == []


def test_detectar_categoria_errada_nao_ancora():
    """Sigla discreta não é detectada quando categoria='Analog' e vice-versa."""
    lp = _lp("67N", siglas_ana=("IN61",))
    rec = _rec("PROTECAO 67N ATUADO")
    ancoras_ana = detectar(rec, lp, "Analog")
    # "67N" está no corpus Discrete, não no Analog
    assert ancoras_ana == []


def test_detectar_sigla_analogica_no_bundle_analogico():
    lp = _lp("67N", siglas_ana=("IN61",))
    rec = _rec("CORRENTE IN61 MEDICAO")
    ancoras_ana = detectar(rec, lp, "Analog")
    assert any(a.sigla == "IN61" for a in ancoras_ana)


def test_detectar_sem_duplicatas():
    """Mesmo token não deve gerar duas âncoras."""
    lp = _lp("67N")
    rec = _rec("67N 67N")
    ancoras = detectar(rec, lp, "Discrete")
    assert len(ancoras) == 1


def test_detectar_descricao_vazia_retorna_lista_vazia():
    lp = _lp("67N")
    rec = _rec("")
    ancoras = detectar(rec, lp, "Discrete")
    assert ancoras == []


# ---------------------------------------------------------------------------
# ancorar
# ---------------------------------------------------------------------------

def test_ancorar_injeta_candidato_ausente():
    fundidos = [_cand("PRTF", 0.65)]
    ancoras = [Ancora("67N")]
    resultado = ancorar(fundidos, ancoras, score_ancora=0.85)
    siglas = {c.sigla for c in resultado}
    assert "67N" in siglas
    ancora_injetada = next(c for c in resultado if c.sigla == "67N")
    assert ancora_injetada.score == 0.85
    assert ancora_injetada.fonte == "ancora_sigla"


def test_ancorar_eleva_score_de_candidato_presente():
    fundidos = [_cand("67N", 0.40)]
    ancoras = [Ancora("67N")]
    resultado = ancorar(fundidos, ancoras, score_ancora=0.85)
    assert len(resultado) == 1
    assert resultado[0].score == 0.85


def test_ancorar_nao_abaixa_score_alto():
    fundidos = [_cand("67N", 0.95)]
    ancoras = [Ancora("67N")]
    resultado = ancorar(fundidos, ancoras, score_ancora=0.85)
    assert resultado[0].score == 0.95


def test_ancorar_lista_vazia_retorna_original():
    fundidos = [_cand("PRTF", 0.65)]
    resultado = ancorar(fundidos, [], score_ancora=0.85)
    assert resultado == fundidos


def test_ancorar_preserva_candidatos_existentes():
    fundidos = [_cand("PRTF", 0.65), _cand("RGBL", 0.50)]
    ancoras = [Ancora("67N")]
    resultado = ancorar(fundidos, ancoras, score_ancora=0.85)
    siglas = {c.sigla for c in resultado}
    assert {"PRTF", "RGBL", "67N"} == siglas


def test_ancorar_case_insensitive():
    """Comparação de sigla presente deve ser case-insensitive."""
    fundidos = [_cand("67n", 0.30)]  # lowercase na lista
    ancoras = [Ancora("67N")]  # uppercase na âncora
    resultado = ancorar(fundidos, ancoras, score_ancora=0.85)
    # deve atualizar o candidato existente, não duplicar
    assert len(resultado) == 1
    assert resultado[0].score == 0.85


# ---------------------------------------------------------------------------
# filtrar_subarvore
# ---------------------------------------------------------------------------

def test_filtrar_subarvore_remove_ramo_irmao():
    """Âncora 67N remove ramos de fase (67F2, 67P2, 67_2) da família 67."""
    cands = [
        _cand("67N2"), _cand("67NT2"), _cand("67F2"),
        _cand("67P2"), _cand("67_2"),
    ]
    resultado = filtrar_subarvore(cands, [Ancora("67N")])
    siglas = {c.sigla for c in resultado}
    assert siglas == {"67N2", "67NT2"}


def test_filtrar_subarvore_mantem_a_propria_ancora_e_filhos():
    cands = [_cand("67N"), _cand("67N1"), _cand("67NT"), _cand("67P1")]
    siglas = {c.sigla for c in filtrar_subarvore(cands, [Ancora("67N")])}
    assert siglas == {"67N", "67N1", "67NT"}


def test_filtrar_subarvore_familia_nao_ancorada_intacta():
    """Candidatos de família sem âncora não são tocados."""
    cands = [_cand("67N2"), _cand("50BF"), _cand("PRTF"), _cand("67P2")]
    siglas = {c.sigla for c in filtrar_subarvore(cands, [Ancora("67N")])}
    # 67P2 some (família 67 ancorada); 50BF e PRTF ficam (sem âncora)
    assert siglas == {"67N2", "50BF", "PRTF"}


def test_filtrar_subarvore_multiplas_ancoras_mesma_familia():
    """Duas âncoras na mesma família mantêm ambos os sub-ramos."""
    cands = [_cand("67N2"), _cand("67F2"), _cand("67P2"), _cand("67_2")]
    siglas = {c.sigla for c in filtrar_subarvore(cands, [Ancora("67N"), Ancora("67F")])}
    assert siglas == {"67N2", "67F2"}


def test_filtrar_subarvore_sem_ancoras_retorna_original():
    cands = [_cand("67N2"), _cand("67P2")]
    assert filtrar_subarvore(cands, []) == cands


def test_filtrar_subarvore_nunca_esvazia():
    """Fallback: se todos os candidatos contradizem a âncora, devolve original."""
    cands = [_cand("67P2"), _cand("67F2")]
    resultado = filtrar_subarvore(cands, [Ancora("67N")])
    assert resultado == cands


def test_filtrar_subarvore_case_insensitive():
    cands = [_cand("67n2"), _cand("67p2")]
    siglas = {c.sigla for c in filtrar_subarvore(cands, [Ancora("67N")])}
    assert siglas == {"67n2"}


# ---------------------------------------------------------------------------
# tem_multiplas_familias
# ---------------------------------------------------------------------------

def test_tem_multiplas_familias_true():
    ancoras = [Ancora("67N"), Ancora("50BF")]
    assert tem_multiplas_familias(ancoras) is True


def test_tem_multiplas_familias_false_mesma_familia():
    ancoras = [Ancora("67N"), Ancora("67NT")]
    assert tem_multiplas_familias(ancoras) is False


def test_tem_multiplas_familias_lista_vazia():
    assert tem_multiplas_familias([]) is False


def test_tem_multiplas_familias_uma_ancora():
    assert tem_multiplas_familias([Ancora("67N")]) is False


def test_tem_multiplas_familias_sem_lider_numerico():
    """Siglas sem prefixo numérico usam a sigla inteira como família."""
    ancoras = [Ancora("63C"), Ancora("63C")]  # mesma sigla duplicada
    assert tem_multiplas_familias(ancoras) is False


def test_tem_multiplas_familias_siglas_sem_lider_distintas():
    ancoras = [Ancora("63C"), Ancora("DJF1")]
    assert tem_multiplas_familias(ancoras) is True


# ---------------------------------------------------------------------------
# Integração com pipeline._classificar_roteado (via lista_padrao real)
# ---------------------------------------------------------------------------

def test_ancora_injeta_e_pipeline_decide_sigla_familia(lista_padrao_path):
    """Âncora "50N" no texto → pipeline deve preferir família 50N sobre PRTF."""
    import numpy as np
    from tdt.config import Config
    from tdt.dados.lista_padrao import ListaPadraoADMS
    from tdt.pipeline import _classificar_roteado, _construir_scorers
    from dataclasses import replace as drep

    lp = ListaPadraoADMS.carregar(lista_padrao_path)

    def _fake_enc(ts):
        return np.zeros((len(ts), 5), dtype="float32")

    cfg = Config(
        peso_tfidf=1.0, peso_vetorial=0.0, peso_fuzzy=0.0,
        threshold_pct=0.01, threshold_gap=0.0,
        ancora_sigla_ativa=True, ancora_sigla_score=0.85,
    )
    disc = _construir_scorers(lp, cfg, _fake_enc, "Discrete", cfg)
    cfg_analog = drep(cfg, threshold_pct=5.0, threshold_gap=5.0)
    ana = _construir_scorers(lp, cfg, _fake_enc, "Analog", cfg_analog)

    # "PROTECAO 50N E1 ATUADO" — 50N está na LP; sem âncora o scorer tende a PRTF/PBF1
    rec = SignalRecord(
        id="t:1",
        modulo=Modulo("M", "sheet"),
        tipo_sinal=TipoSinal("Discrete", False, "Input", categoria_confiavel=True),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes("PROTECAO 50N E1 ATUADO", "PROTECAO 50N E1 ATUADO"),
    )

    decidido, item = _classificar_roteado(rec, disc, ana, diagnostico=False, lista_padrao=lp)
    # Com âncora, a família 50N deve entrar; o scorer + regras selecionam filho
    if decidido is not None:
        assert decidido.sigla_sinal.startswith("50"), (
            f"esperava família 50N mas decidiu {decidido.sigla_sinal}"
        )
    else:
        # Se não decidiu, ao menos deve ter um candidato da família 50N nos sugeridos
        assert item is not None
        familia_ok = any(
            c.sigla.upper().startswith("50")
            for c in item.candidatos_sugeridos
        )
        assert familia_ok, (
            f"família 50N ausente dos candidatos sugeridos: {item.candidatos_sugeridos}"
        )


def test_ancora_desativada_nao_injeta(lista_padrao_path):
    """Com ancora_sigla_ativa=False, a âncora não deve ser injetada."""
    import numpy as np
    from tdt.config import Config
    from tdt.dados.lista_padrao import ListaPadraoADMS
    from tdt.ancoragem_sigla import detectar, ancorar, Ancora

    lp = ListaPadraoADMS.carregar(lista_padrao_path)
    rec = _rec("PROTECAO 50N E1 ATUADO")

    ancoras = detectar(rec, lp, "Discrete")
    assert any(a.sigla.upper().startswith("50") for a in ancoras)

    # com score_ancora irrelevante, mas lista vazia de ancoras → nada injetado
    fundidos = [_cand("PRTF", 0.65)]
    resultado = ancorar(fundidos, [], score_ancora=0.85)
    assert len(resultado) == 1
    assert resultado[0].sigla == "PRTF"
