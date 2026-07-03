from tdt.config import Config
from tdt.contracts import ListaHomogenea, ResultadoPipeline
from tdt.auditoria import Auditoria
from tdt.ui.estado import AppState
from tdt.ui.worker import PipelineWorker


def _resultado_vazio():
    return ResultadoPipeline(ListaHomogenea(None, "DNP3", ()), ())


def test_worker_emite_terminado(tmp_path, qtbot):
    def fake_exec(*a, auditoria=None, **k):
        if auditoria is not None:
            auditoria.evento("fake", "rodando", "INFO")
        return _resultado_vazio(), None

    for nome in ("input.xlsx", "template.xlsx", "lista.xlsx"):
        (tmp_path / nome).write_text("x")

    w = PipelineWorker(
        paths={
            "input": str(tmp_path / "input.xlsx"), "output": "o",
            "template": str(tmp_path / "template.xlsx"),
            "lista_padrao": str(tmp_path / "lista.xlsx"),
        },
        config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: (lambda textos: None),
        executar_fn=fake_exec,
    )
    with qtbot.waitSignal(w.terminado, timeout=3000) as bloco:
        w.start()
    assert isinstance(bloco.args[0], ResultadoPipeline)
    w.wait()


def test_worker_emite_progresso_a_partir_de_evento_com_dados(tmp_path, qtbot):
    """Task 1.4: evento de Auditoria com dados={'atual','total'} vira sinal
    Qt `progresso`, e não duplica no log de texto (evita poluir o log com
    uma linha por sinal em listas grandes)."""
    def fake_exec(*a, auditoria=None, **k):
        if auditoria is not None:
            auditoria.evento("pipeline", "5/10", "INFO", dados={"atual": 5, "total": 10})
            auditoria.evento("pipeline", "feito", "INFO")
        return _resultado_vazio(), None

    for nome in ("input.xlsx", "template.xlsx", "lista.xlsx"):
        (tmp_path / nome).write_text("x")

    w = PipelineWorker(
        paths={
            "input": str(tmp_path / "input.xlsx"), "output": "o",
            "template": str(tmp_path / "template.xlsx"),
            "lista_padrao": str(tmp_path / "lista.xlsx"),
        },
        config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: (lambda textos: None),
        executar_fn=fake_exec,
    )
    logs = []
    progressos = []
    w.log.connect(logs.append)
    w.progresso.connect(lambda atual, total: progressos.append((atual, total)))
    with qtbot.waitSignal(w.terminado, timeout=3000):
        w.start()
    w.wait()
    assert progressos == [(5, 10)]
    assert not any("5/10" in linha for linha in logs)
    assert any("feito" in linha for linha in logs)


def test_parar_sinaliza_cancelamento():
    w = PipelineWorker(
        paths={}, config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: None, executar_fn=lambda *a, **k: (None, None),
    )
    assert w._cancelado() is False
    w.parar()
    assert w._cancelado() is True


def test_valida_paths_antes_de_criar_encoder(tmp_path, qtbot):
    """Paths inexistentes devem emitir erro sem nunca chamar encoder_factory
    (que carrega o modelo de embedding — lento)."""
    input_valido = tmp_path / "input.xlsx"
    input_valido.write_text("x")

    chamou_encoder = []

    def encoder_factory_espiao(nome):
        chamou_encoder.append(nome)
        return lambda textos: None

    w = PipelineWorker(
        paths={
            "input": str(input_valido),
            "template": str(tmp_path / "nao_existe_template.xlsx"),
            "lista_padrao": str(tmp_path / "nao_existe_lista.xlsx"),
        },
        config=Config(), modo="auto", subestacao=None,
        encoder_factory=encoder_factory_espiao,
        executar_fn=lambda *a, **k: (_resultado_vazio(), None),
    )
    with qtbot.waitSignal(w.erro, timeout=3000) as bloco:
        w.start()
    w.wait()
    assert "template" in bloco.args[0].lower()
    assert "não encontrado" in bloco.args[0].lower()
    assert chamou_encoder == []


def test_reusa_encoder_do_app_state_entre_execucoes(tmp_path, qtbot):
    """Com app_state informado, a 2a execução não deve recriar o encoder."""
    for nome in ("input.xlsx", "template.xlsx", "lista.xlsx"):
        (tmp_path / nome).write_text("x")

    chamadas = []

    def encoder_factory_espiao(nome):
        chamadas.append(nome)
        return lambda textos: None

    estado = AppState()
    paths = {
        "input": str(tmp_path / "input.xlsx"),
        "template": str(tmp_path / "template.xlsx"),
        "lista_padrao": str(tmp_path / "lista.xlsx"),
    }

    def fake_exec(*a, **k):
        return _resultado_vazio(), None

    w1 = PipelineWorker(
        paths=paths, config=Config(), modo="auto", subestacao=None,
        encoder_factory=encoder_factory_espiao, executar_fn=fake_exec,
        app_state=estado,
    )
    with qtbot.waitSignal(w1.terminado, timeout=3000):
        w1.start()
    w1.wait()
    assert len(chamadas) == 1
    assert estado.encoder is not None

    w2 = PipelineWorker(
        paths=paths, config=Config(), modo="auto", subestacao=None,
        encoder_factory=encoder_factory_espiao, executar_fn=fake_exec,
        app_state=estado,
    )
    with qtbot.waitSignal(w2.terminado, timeout=3000):
        w2.start()
    w2.wait()
    assert len(chamadas) == 1  # não chamou de novo


def test_worker_repassa_sheets_e_aliases_para_executar(tmp_path, qtbot):
    """Task 2 (spK): seleção de sheets e aliases (rename) coletados na tela
    inicial precisam chegar em `pipeline.executar` via PipelineWorker."""
    recebido = {}

    def fake_exec(*a, sheets=None, aliases=None, **k):
        recebido["sheets"] = sheets
        recebido["aliases"] = aliases
        return _resultado_vazio(), None

    for nome in ("input.xlsx", "template.xlsx", "lista.xlsx"):
        (tmp_path / nome).write_text("x")

    w = PipelineWorker(
        paths={
            "input": str(tmp_path / "input.xlsx"), "output": "o",
            "template": str(tmp_path / "template.xlsx"),
            "lista_padrao": str(tmp_path / "lista.xlsx"),
        },
        config=Config(), modo="auto", subestacao=None,
        encoder_factory=lambda nome: (lambda textos: None),
        executar_fn=fake_exec,
        sheets=["GTD_11"],
        aliases={"GTD_11": "MODULO_RENOMEADO"},
    )
    with qtbot.waitSignal(w.terminado, timeout=3000):
        w.start()
    w.wait()
    assert recebido["sheets"] == ["GTD_11"]
    assert recebido["aliases"] == {"GTD_11": "MODULO_RENOMEADO"}
