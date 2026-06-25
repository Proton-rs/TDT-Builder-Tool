"""Coletor de eventos do pipeline, para revisão humana.

Sem lógica de negócio: acumula eventos e serializa. O ``pipeline`` injeta uma
instância em cada módulo, que chama ``evento(...)`` para registrar o que fez.

ponytail: usa logging stdlib + lista de eventos; sem framework de log.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

_log = logging.getLogger("tdt")

NIVEIS = ("INFO", "AVISO", "ERRO")
_NIVEL_LOGGING = {"INFO": logging.INFO, "AVISO": logging.WARNING, "ERRO": logging.ERROR}


@dataclass(frozen=True)
class Evento:
    modulo: str
    msg: str
    nivel: str
    timestamp: str
    signal_id: str | None = None
    dados: dict | None = None


class Auditoria:
    def __init__(self, on_evento: "Callable[[Evento], None] | None" = None) -> None:
        self.eventos: list[Evento] = []
        self._on_evento = on_evento

    def evento(
        self,
        modulo: str,
        msg: str,
        nivel: str = "INFO",
        signal_id: str | None = None,
        dados: dict | None = None,
    ) -> None:
        if nivel not in NIVEIS:
            raise ValueError(f"nível inválido: {nivel!r} (use {NIVEIS})")
        ev = Evento(
            modulo=modulo,
            msg=msg,
            nivel=nivel,
            timestamp=datetime.now(timezone.utc).isoformat(),
            signal_id=signal_id,
            dados=dados,
        )
        self.eventos.append(ev)
        _log.log(_NIVEL_LOGGING[nivel], "%s: %s", modulo, msg)
        if self._on_evento is not None:
            self._on_evento(ev)

    def contagem(self, nivel: str) -> int:
        return sum(1 for e in self.eventos if e.nivel == nivel)

    def _linha(self, e: Evento) -> str:
        sid = f" ({e.signal_id})" if e.signal_id else ""
        extra = f" {e.dados}" if e.dados else ""
        return f"[{e.nivel}] {e.modulo}:{sid} {e.msg}{extra}"

    def salvar_log(self, destino: str | Path) -> None:
        texto = "\n".join(self._linha(e) for e in self.eventos)
        Path(destino).write_text(texto + ("\n" if texto else ""), encoding="utf-8")

    def salvar_json(self, destino: str | Path) -> None:
        payload = [asdict(e) for e in self.eventos]
        Path(destino).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
