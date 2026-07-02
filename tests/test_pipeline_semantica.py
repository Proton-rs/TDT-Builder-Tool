from dataclasses import replace

from tdt import pipeline
from tdt.config import Config
from tdt.contracts import (
    Candidato, Descricoes, Eletrico, Enderecamento, ItemRevisao, Modulo,
    SignalRecord, TipoSinal,
)


def _rec(desc, equip_alvo=None, inferido=False):
    return SignalRecord(
        id="s:1", modulo=Modulo("AL11", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete"),
        enderecamento=Enderecamento("DNP3", (10,)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(equipamento_alvo=equip_alvo, equipamento_inferido=inferido),
    )


def test_roteado_mapeia_justificativa_para_motivo(monkeypatch):
    rec = _rec("PROTECAO SGF ATUADO")
    rev = replace(rec, status="revisao", justificativa="estado_sem_candidato",
                  candidatos=(Candidato("SGF", 0.9, "mesclado"),))
    monkeypatch.setattr(pipeline, "_classificar_sinal", lambda *a, **k: rev)
    monkeypatch.setattr(pipeline.ancoragem_sigla, "detectar", lambda *a, **k: [])
    scorers = pipeline._Scorers(None, None, None, Config())
    decidido, item = pipeline._classificar_roteado(
        rec, scorers, scorers, diagnostico=False, lista_padrao=object(),
    )
    assert decidido is None
    assert item.motivo == "estado_sem_candidato"
    assert item.candidatos_sugeridos == rev.candidatos[:3]


def test_roteado_mapeia_fora_whitelist(monkeypatch):
    rec = _rec("TERRA LIBERA MANOBRA", equip_alvo="Seccionadora")
    rev = replace(rec, status="revisao", justificativa="fora_whitelist_equipamento")
    monkeypatch.setattr(pipeline, "_classificar_sinal", lambda *a, **k: rev)
    monkeypatch.setattr(pipeline.ancoragem_sigla, "detectar", lambda *a, **k: [])
    scorers = pipeline._Scorers(None, None, None, Config())
    decidido, item = pipeline._classificar_roteado(
        rec, scorers, scorers, diagnostico=False, lista_padrao=object(),
    )
    assert item.motivo == "fora_whitelist_equipamento"
