"""Worker em thread: roda o pipeline sem travar a UI; streaming de log e PARAR.

ponytail: cancelamento cooperativo por flag; nada de QThread.terminate (corrompe
estado). executar_fn é injetável para teste.
"""

from __future__ import annotations

import threading
import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from tdt.auditoria import Auditoria
from tdt.config import Config


class PipelineWorker(QThread):
    log = Signal(str)
    terminado = Signal(object)
    erro = Signal(str)
    progresso = Signal(int, int)  # (atual, total)

    def __init__(self, paths, config: Config, modo, subestacao,
                 encoder_factory=None, executar_fn=None,
                 app_state=None, sheets=None, aliases=None):
        super().__init__()
        self._paths = paths
        self._config = config
        self._modo = modo
        self._subestacao = subestacao
        self._encoder_factory = encoder_factory
        self._executar_fn = executar_fn
        self._app_state = app_state
        self._sheets = sheets
        self._aliases = aliases
        self._parar = threading.Event()

    def parar(self) -> None:
        self._parar.set()

    def _cancelado(self) -> bool:
        return self._parar.is_set()

    def run(self) -> None:
        _input = self._paths.get("input", "")
        _template = self._paths.get("template", "")
        _lista = self._paths.get("lista_padrao", "")
        try:
            for nome, p in (("input", _input), ("template", _template),
                             ("lista padrão", _lista)):
                if not Path(p).exists():
                    self.erro.emit(f"Arquivo {nome} não encontrado: {p}")
                    return
            self.log.emit("[INFO] pipeline: iniciando processamento…")
            aud = Auditoria(on_evento=self._on_evento)
            # ponytail: reusa encoder via AppState (evita reload do modelo de
            # embeddings, lento) — sem contagem de referências, ver estado.py.
            if self._app_state is not None and self._app_state.encoder is not None:
                encoder = self._app_state.encoder
            else:
                factory = self._encoder_factory
                if factory is None:
                    from tdt.dados.encoder import criar_encoder
                    factory = criar_encoder
                encoder = factory(self._config.modelo_embedding)
                if self._app_state is not None:
                    self._app_state.encoder = encoder
            executar = self._executar_fn
            if executar is None:
                from tdt import pipeline
                executar = pipeline.executar
            resultado, _wb = executar(
                _input, _template, _lista,
                config=self._config, encoder=encoder, modo=self._modo,
                subestacao=self._subestacao, auditoria=aud,
                diagnostico=True, cancelado=self._cancelado,
                cache_scorers_dir=Path("cache") / "scorers",
                sheets=self._sheets, aliases=self._aliases,
            )
            self.terminado.emit(resultado)
        except Exception:
            tb = traceback.format_exc()
            msg = f"{tb}"
            if "openpyxl does not support file format" in msg.lower():
                msg += "\n[DICA] Verifique se os arquivos abaixo existem e são .xlsx válidos:\n"
                msg += f"  input: {_input}\n  template: {_template}\n  lista_padrao: {_lista}"
            self.erro.emit(msg)

    def _on_evento(self, ev) -> None:
        # ponytail: evento de progresso é um evento normal (nivel="INFO") com
        # dados={"atual","total"} — evita estender Auditoria.NIVEIS só para
        # isso. Vai pra barra, não pro log de texto (1 linha/sheet já basta
        # como rastro textual; duplicar viraria spam em listas grandes).
        if ev.dados and "atual" in ev.dados and "total" in ev.dados:
            self.progresso.emit(ev.dados["atual"], ev.dados["total"])
            return
        self.log.emit(self._fmt(ev))

    @staticmethod
    def _fmt(ev) -> str:
        return f"[{ev.nivel}] {ev.modulo}: {ev.msg}"
