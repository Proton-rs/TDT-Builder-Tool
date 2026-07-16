import json

from tdt.auditoria import Auditoria


def test_acumula_eventos_por_nivel():
    aud = Auditoria()
    aud.evento("roteador", "DJF1 decidido", nivel="INFO", signal_id="LT3:4")
    aud.evento("engine_tdt", "coluna ausente", nivel="ERRO")
    assert len(aud.eventos) == 2
    assert aud.contagem("ERRO") == 1
    assert aud.contagem("INFO") == 1


def test_salva_log_legivel(tmp_path):
    aud = Auditoria()
    aud.evento("roteador", "DJF1 decidido", nivel="INFO", dados={"gap": 0.31})
    destino = tmp_path / "out.log.txt"
    aud.salvar_log(destino)
    texto = destino.read_text(encoding="utf-8")
    assert "[INFO]" in texto
    assert "roteador" in texto
    assert "DJF1 decidido" in texto


def test_salva_json_com_signal_id(tmp_path):
    aud = Auditoria()
    aud.evento("normalizador_estrutural", "sem endereco", nivel="AVISO", signal_id="LT3:9")
    destino = tmp_path / "out.auditoria.json"
    aud.salvar_json(destino)
    dados = json.loads(destino.read_text(encoding="utf-8"))
    assert dados[0]["signal_id"] == "LT3:9"
    assert dados[0]["nivel"] == "AVISO"
    assert dados[0]["modulo"] == "normalizador_estrutural"


# --- diff_identidade / sobrescritas (SP-FLUXO-DADOS Task 2) -----------------

from dataclasses import replace

from tdt.auditoria import diff_identidade
from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)


def _rec_id(id_, sigla="DJF1", modulo="BC1", equip="52-1", indices=(10,)):
    return SignalRecord(
        id=id_, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes("d", "D"),
        eletrico=Eletrico(nome_equipamento=equip),
        sigla_sinal=sigla, status="decidido",
    )


def test_diff_identidade_detecta_sobrescrita_e_perda():
    antes = [_rec_id("a:1"), _rec_id("a:2")]
    depois = [
        replace(antes[0], sigla_sinal="DJA1"),
        replace(antes[1], sigla_sinal=None),
    ]
    diffs = diff_identidade(antes, depois)
    assert [(d.signal_id, d.campo, d.tipo) for d in diffs] == [
        ("a:1", "sigla_sinal", "sobrescrita"),
        ("a:2", "sigla_sinal", "perda"),
    ]


def test_diff_identidade_ignora_preenchimento_e_ids_novos():
    # None -> valor é ENRIQUECIMENTO (permitido); id só de um lado é fusão/
    # particionamento (coberto pelos testes de conservação por contagem)
    antes = [_rec_id("a:1", sigla=None)]
    depois = [replace(antes[0], sigla_sinal="DJF1"), _rec_id("a:9")]
    assert diff_identidade(antes, depois) == []


def test_sobrescritas_emite_eventos_com_nivel_por_tipo():
    aud = Auditoria()
    antes = [_rec_id("a:1"), _rec_id("a:2")]
    depois = [
        replace(antes[0], modulo=Modulo("BC1AT", "sheet_name")),
        replace(antes[1], eletrico=Eletrico(nome_equipamento=None)),
    ]
    n = aud.sobrescritas("subdividir_at_bt", antes, depois)
    assert n == 2
    ev_info, ev_aviso = aud.eventos
    assert ev_info.nivel == "INFO"
    assert ev_info.signal_id == "a:1"
    assert ev_info.dados == {
        "etapa": "subdividir_at_bt", "campo": "modulo",
        "antes": "BC1", "depois": "BC1AT", "tipo": "sobrescrita",
    }
    assert ev_aviso.nivel == "AVISO"
    assert ev_aviso.signal_id == "a:2"
    assert ev_aviso.dados["tipo"] == "perda"
    assert ev_aviso.dados["campo"] == "equipamento"
