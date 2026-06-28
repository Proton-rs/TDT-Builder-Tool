"""Carrega/salva as configurações da UI em config.toml <-> Config.

ponytail: TOML plano por seções; tomllib (stdlib) lê, tomli_w escreve. Sem ORM.

Portabilidade (SP-Cleanup item 6): os caminhos em ``[paths]`` são persistidos
RELATIVOS à raiz do projeto (ou à pasta apontada por ``TDT_DOCS_DIR``, se a
env var estiver definida), nunca absolutos. Isso permite versionar/compartilhar
o ``config.toml`` entre máquinas sem editar caminho manualmente. Caminhos que
não estão sob a raiz/`TDT_DOCS_DIR` (ex.: pasta de output em outro disco) são
gravados como vieram — não há como tornar relativo o que não está dentro.
"""

from __future__ import annotations

import os
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

# raiz do projeto: .../src/tdt/ui/config_io.py -> parents[3] == raiz
_RAIZ_PROJETO = Path(__file__).resolve().parents[3]


def _base_paths() -> Path:
    """Diretório-base para relativizar paths: ``TDT_DOCS_DIR`` se definida,
    senão a raiz do projeto."""
    env = os.environ.get("TDT_DOCS_DIR")
    return Path(env).resolve() if env else _RAIZ_PROJETO


def _para_relativo(valor: str, base: Path) -> str:
    """Converte caminho absoluto -> relativo a ``base``, quando possível.

    Caminhos vazios, já relativos, ou fora de ``base`` voltam como vieram
    (não força relativo onde não cabe, ex.: pasta de output em outro disco).
    """
    if not valor:
        return valor
    p = Path(valor)
    if not p.is_absolute():
        return valor
    try:
        return p.resolve().relative_to(base).as_posix()
    except ValueError:
        return valor


def _para_absoluto(valor: str, base: Path) -> str:
    """Converte caminho relativo -> absoluto a partir de ``base``.

    Caminhos vazios ou já absolutos voltam como vieram.
    """
    if not valor:
        return valor
    p = Path(valor)
    if p.is_absolute():
        return valor
    return str((base / p).resolve())


def carregar_config(path: str | Path) -> tuple[Config, dict]:
    p = Path(path)
    if not p.exists():
        return Config(), dict(_PATHS_VAZIO)
    try:
        dados = tomllib.loads(p.read_text(encoding="utf-8"))
    except (tomllib.TOMLDecodeError, OSError):
        return Config(), dict(_PATHS_VAZIO)
    paths_brutos = {**_PATHS_VAZIO, **dados.get("paths", {})}
    base = _base_paths()
    paths = {k: _para_absoluto(v, base) for k, v in paths_brutos.items()}
    knobs = {k: v for k, v in dados.get("config", {}).items() if k in _ESCALARES}
    pesos_regras = dados.get("pesos_regras")
    cfg = replace(Config(), **knobs)
    if isinstance(pesos_regras, dict):
        cfg = replace(cfg, pesos_regras={**Config().pesos_regras, **pesos_regras})
    return cfg, paths


def salvar_config(path: str | Path, config: Config, paths: dict) -> None:
    base = _base_paths()
    paths_relativos = {
        k: _para_relativo(v, base) for k, v in {**_PATHS_VAZIO, **paths}.items()
    }
    doc = {
        "paths": paths_relativos,
        "config": {k: getattr(config, k) for k in _ESCALARES},
        "pesos_regras": dict(config.pesos_regras),
    }
    Path(path).write_text(tomli_w.dumps(doc), encoding="utf-8")
