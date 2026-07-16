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

    def sobrescritas(self, etapa: str, antes, depois) -> int:
        """I3 (spec fluxo-dados): emite 1 evento por mudança de identidade
        entre dois estágios do pipeline. "sobrescrita" (valor -> outro
        valor) é INFO — legítima, mas visível; "perda" (valor -> vazio) é
        AVISO — nunca deve acontecer silenciosamente. Devolve o total."""
        diffs = diff_identidade(antes, depois)
        for d in diffs:
            self.evento(
                "fluxo_dados",
                f"{etapa}: {d.campo} {d.antes!r} -> {d.depois!r}",
                "AVISO" if d.tipo == "perda" else "INFO",
                signal_id=d.signal_id,
                dados={"etapa": etapa, "campo": d.campo, "antes": d.antes,
                       "depois": d.depois, "tipo": d.tipo},
            )
        return len(diffs)

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


@dataclass(frozen=True)
class Sobrescrita:
    signal_id: str
    campo: str
    antes: object
    depois: object
    tipo: str  # "sobrescrita" (valor -> outro valor) | "perda" (valor -> vazio)


def _identidade(rec) -> dict:
    return {
        "sigla_sinal": rec.sigla_sinal,
        "modulo": rec.modulo.nome,
        "equipamento": rec.eletrico.nome_equipamento,
        "indices": rec.enderecamento.indices,
    }


def diff_identidade(antes, depois) -> "list[Sobrescrita]":
    """Mudanças de campos de identidade entre dois estágios, por id.

    Ids presentes só num dos lados ficam de fora (fusão/particionamento —
    cobertos pelos testes de conservação por contagem); vazio -> valor é
    enriquecimento, não mudança. Vazio = None ou tupla ().
    """
    por_id = {r.id: r for r in antes}
    out: list[Sobrescrita] = []
    for rec in depois:
        r_antes = por_id.get(rec.id)
        if r_antes is None:
            continue
        ia, id_ = _identidade(r_antes), _identidade(rec)
        for campo, v_antes in ia.items():
            v_depois = id_[campo]
            if v_antes in (None, ()) or v_depois == v_antes:
                continue
            tipo = "perda" if v_depois in (None, ()) else "sobrescrita"
            out.append(Sobrescrita(rec.id, campo, v_antes, v_depois, tipo))
    return out
