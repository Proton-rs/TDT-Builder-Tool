from tdt.auditoria import Auditoria, Evento


def test_on_evento_e_chamado():
    recebidos = []
    aud = Auditoria(on_evento=recebidos.append)
    aud.evento("mod", "oi", "INFO")
    assert len(recebidos) == 1
    assert isinstance(recebidos[0], Evento)
    assert recebidos[0].msg == "oi"


def test_sem_callback_funciona_normal():
    aud = Auditoria()
    aud.evento("mod", "oi", "INFO")
    assert aud.contagem("INFO") == 1
