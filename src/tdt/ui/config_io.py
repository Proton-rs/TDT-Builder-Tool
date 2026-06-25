"""Carrega/salva as configurações da UI em config.toml <-> Config.

ponytail: TOML plano por seções; tomllib (stdlib) lê, tomli_w escreve. Sem ORM.
"""

from __future__ import annotations

import tomllib
from dataclasses import replace
from pathlib import Path

import tomli_w

from tdt.config import Config

_PATHS_VAZIO = {"input": "", "output": "", "template": "", "lista_padrao": ""}

# campos escalares da Config que a UI edita
_ESCALARES = (
    "peso_tfidf", "peso_vetorial", "peso_fuzzy",
    "threshold_pct", "threshold_gap", "top_n_pct",
    "modelo_embedding", "k_vizinhos",
    "corrigir_typos", "remover_ids_equipamento",
)


def carregar_config(path: str | Path) -> tuple[Config, dict]:
    p = Path(path)
    if not p.exists():
        return Config(), dict(_PATHS_VAZIO)
    try:
        dados = tomllib.loads(p.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return Config(), dict(_PATHS_VAZIO)
    paths = {**_PATHS_VAZIO, **dados.get("paths", {})}
    knobs = {k: v for k, v in dados.get("config", {}).items() if k in _ESCALARES}
    pesos_regras = dados.get("pesos_regras")
    cfg = replace(Config(), **knobs)
    if isinstance(pesos_regras, dict):
        cfg = replace(cfg, pesos_regras={**Config().pesos_regras, **pesos_regras})
    return cfg, paths


def salvar_config(path: str | Path, config: Config, paths: dict) -> None:
    doc = {
        "paths": {**_PATHS_VAZIO, **paths},
        "config": {k: getattr(config, k) for k in _ESCALARES},
        "pesos_regras": dict(config.pesos_regras),
    }
    Path(path).write_text(tomli_w.dumps(doc), encoding="utf-8")
