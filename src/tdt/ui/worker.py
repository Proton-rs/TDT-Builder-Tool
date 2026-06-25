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
from tdt.dados.encoder import criar_encoder
from tdt import pipeline


class PipelineWorker(QThread):
    log = Signal(str)
    terminado = Signal(object)
    erro = Signal(str)

    def __init__(self, paths, config: Config, modo, subestacao,
                 encoder_factory=criar_encoder, executar_fn=pipeline.executar):
        super().__init__()
        self._paths = paths
        self._config = config
        self._modo = modo
        self._subestacao = subestacao
        self._encoder_factory = encoder_factory
        self._executar_fn = executar_fn
        self._parar = threading.Event()

    def parar(self) -> None:
        self._parar.set()

    def _cancelado(self) -> bool:
        return self._parar.is_set()

    def run(self) -> None:
        try:
            self.log.emit("[INFO] pipeline: iniciando processamento…")
            aud = Auditoria(on_evento=lambda ev: self.log.emit(self._fmt(ev)))
            encoder = self._encoder_factory(self._config.modelo_embedding)
            _input = self._paths.get("input", "")
            _template = self._paths.get("template", "")
            _lista = self._paths.get("lista_padrao", "")
            resultado, _wb = self._executar_fn(
                _input, _template, _lista,
                config=self._config, encoder=encoder, modo=self._modo,
                subestacao=self._subestacao, auditoria=aud,
                diagnostico=True, cancelado=self._cancelado,
                cache_scorers_dir=Path("cache") / "scorers",
            )
            self.terminado.emit(resultado)
        except Exception:
            tb = traceback.format_exc()
            msg = f"{tb}"
            if "openpyxl does not support file format" in msg.lower():
                msg += "\n[DICA] Verifique se os arquivos abaixo existem e são .xlsx válidos:\n"
                msg += f"  input: {_input}\n  template: {_template}\n  lista_padrao: {_lista}"
            self.erro.emit(msg)

    @staticmethod
    def _fmt(ev) -> str:
        return f"[{ev.nivel}] {ev.modulo}: {ev.msg}"
