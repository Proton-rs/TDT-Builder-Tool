from tdt.config import Config
from tdt.contracts import ListaHomogenea, ResultadoPipeline
from tdt.auditoria import Auditoria
from tdt.ui.worker import PipelineWorker


def _resultado_vazio():
    return ResultadoPipeline(ListaHomogenea(None, "DNP3", ()), ())


def test_worker_emite_terminado(qtbot):
    def fake_exec(*a, auditoria=None, **k):
        if auditoria is not None:
            auditoria.evento("fake", "rodando", "INFO")
        return _resultado_vazio(), None

    w = PipelineWorker(
        paths={"input": "i", "output": "o", "template": "t", "lista_padrao": "lp"},
        config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: (lambda textos: None),
        executar_fn=fake_exec,
    )
    with qtbot.waitSignal(w.terminado, timeout=3000) as bloco:
        w.start()
    assert isinstance(bloco.args[0], ResultadoPipeline)
    w.wait()


def test_parar_sinaliza_cancelamento():
    w = PipelineWorker(
        paths={}, config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: None, executar_fn=lambda *a, **k: (None, None),
    )
    assert w._cancelado() is False
    w.parar()
    assert w._cancelado() is True
