"""Identidade módulo/equipamento do caminho homogêneo (spec 2026-07-10).

Resolve módulo e segmento de equipamento no padrão do cliente a partir do
bloco de cabeçalho da sheet (EQUIPAMENTO | NÚMERO OPERATIVO / CLASSE DE
TENSÃO / NÚMERO). Regras validadas contra a coluna NOME da lista IMA
(1400/1404; as 4 divergências são inconsistências do próprio cliente):

- valor com "-" é mnemônico operativo -> usado direto ("DJ" -> "52-3");
- valor sem "-" concatena ao rótulo-base ("RET"+"1" -> "RET1", "LT"+"3" -> "LT3");
- coluna MÓDULO "AT"/"BT" é lado: módulo = prefixo da sheet + nº + lado
  ("TR"+"6"+"AT" -> "TR6AT") e o lookup de equipamento tenta "ROTULO LADO"
  primeiro ("DJ AT" -> "52-6");
- coluna MÓDULO "BP{n}" busca classe de tensão no rótulo "BP AT"/"BP BT{n}";
- equipamento "X_P"/"X_A" (relé principal/alternado): sufixo anexado ao meio
  ("52-3_P"); sem mnemônico do base, anexado ao módulo ("LT3_P");
- coluna MÓDULO já numerada ("LT 1") não concatena (comportamento atual).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_TITULOS_BLOCO = ("OPERATIVO", "TENSAO", "NUMERO")
_COLUNA_VALOR = 1
_LADOS = ("AT", "BT")
_JA_NUMERADO = re.compile(r"^[A-Z]+\s?\d+$")


@dataclass(frozen=True)
class Identidade:
    modulo: str
    equipamento: str | None  # None -> engine repete o módulo
    origem: str  # "coluna:MODULO" | "coluna:MODULO+header:NUMERO_OPERATIVO"


def _norm(v) -> str:
    import unicodedata
    if v is None:
        return ""
    s = "".join(c for c in unicodedata.normalize("NFKD", str(v))
                if not unicodedata.combining(c))
    return " ".join(s.upper().split())


def extrair_bloco(rows: list[tuple], header_idx: int) -> dict[str, str]:
    """Rótulo normalizado -> valor bruto. Aceita os três títulos de bloco
    reais (NÚMERO OPERATIVO / CLASSE DE TENSÃO / NÚMERO); vários blocos na
    mesma sheet são fundidos. Ausente/ilegível -> {}."""
    bloco: dict[str, str] = {}
    dentro = False
    for row in rows[:header_idx]:
        rotulo = _norm(row[0] if row else None)
        segundo = _norm(row[_COLUNA_VALOR] if len(row) > _COLUNA_VALOR else None)
        if rotulo == "EQUIPAMENTO" and any(t in segundo for t in _TITULOS_BLOCO):
            dentro = True
            continue
        if not dentro:
            continue
        if not rotulo:
            dentro = False
            continue
        valor = row[_COLUNA_VALOR] if len(row) > _COLUNA_VALOR else None
        if valor is not None and str(valor).strip():
            bloco[rotulo] = str(valor).strip()
    return bloco


def _concat(nome: str, num: str) -> str:
    nome = nome.replace(" ", "")
    return nome if nome.endswith(num) else nome + num


def _resolver_modulo(bloco: dict[str, str], sheet_name: str,
                     modulo_col: str) -> tuple[str, str]:
    num_mod = bloco.get("MODULO")
    if modulo_col in _LADOS and num_mod:
        prefixo = re.match(r"[A-Z]+", _norm(sheet_name))
        base = prefixo.group(0) if prefixo else modulo_col
        return _concat(base, num_mod) + modulo_col, "coluna:MODULO+header:NUMERO_OPERATIVO"
    if modulo_col in bloco:
        return _concat(modulo_col, bloco[modulo_col]), "coluna:MODULO+header:NUMERO_OPERATIVO"
    if modulo_col.startswith("BP"):
        sufixo = modulo_col[2:]
        rotulo = "BP AT" if not sufixo else f"BP BT{sufixo}"
        if rotulo in bloco:
            return _concat(modulo_col, bloco[rotulo]), "coluna:MODULO+header:NUMERO_OPERATIVO"
    if num_mod and not _JA_NUMERADO.match(modulo_col):
        return _concat(modulo_col, num_mod), "coluna:MODULO+header:NUMERO_OPERATIVO"
    return modulo_col, "coluna:MODULO"


def resolver(bloco: dict[str, str], sheet_name: str,
             modulo_col: str, equip_col: str) -> Identidade:
    modulo, origem = _resolver_modulo(bloco, sheet_name, modulo_col)
    base, sufixo_rele = equip_col, ""
    if equip_col.endswith(("_P", "_A")):
        base, sufixo_rele = equip_col[:-2], equip_col[-1]
    lado = modulo_col if modulo_col in _LADOS else None
    valor = None
    if lado and f"{base} {lado}" in bloco:
        valor = bloco[f"{base} {lado}"]
    elif base in bloco and base != "MODULO":
        valor = bloco[base]
    equipamento = None
    if valor is not None:
        equipamento = valor if "-" in valor else _concat(base, valor)
    if sufixo_rele:
        equipamento = f"{equipamento or modulo.replace(' ', '')}_{sufixo_rele}"
    return Identidade(modulo=modulo, equipamento=equipamento, origem=origem)
