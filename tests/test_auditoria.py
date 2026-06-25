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
