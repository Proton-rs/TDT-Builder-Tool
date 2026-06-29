"""Vocabulário de classificação Discreto/Analógico/Comando, compartilhado por
`estruturador.py` (linha a linha / marcador de seção) e `analise_colunas.py`
(detecção de coluna "Tipo"). Fonte única — evita duas cópias divergentes.
"""

from __future__ import annotations

import unicodedata

# SP-Direção / D1: diagnóstico nas planilhas reais `docs/GTD - Lista de Pontos
# V11.xlsx` (coluna "Tipo": "Comando D"/"Comando S"/"Digital Simples"/
# "Analógico"; marcadores de seção: "Comandos", "Comandos Módulos AT/MT/TR",
# "Digitais (Controle)") e `docs/Lista de Pontos FredW V13 - DNP3.xlsx`
# (coluna "Tipo": códigos de 1 letra A/C/D) mostrou que TODOS os termos de
# comando reais já casam com `COMANDO`/`CODIGOS_TIPO` abaixo — "COMANDO" é
# substring de "Comando D"/"Comandos", e "C" já mapeia para Output. Nenhum
# termo de comando ficou sem reconhecer; vocabulário não foi estendido.
ANALOG = ("ANALOGIC", "MEDIDA", "MEDICAO", "GRANDEZA")
COMANDO = ("COMANDO", "CONTROLE", "TELECOMANDO")
DISCRETO = ("DIGITAL", "DIGITAIS", "DISCRET", "SINALIZ", "STATUS", "ESTADO", "INDICAC")
VOCAB = ANALOG + COMANDO + DISCRETO

# Código curto de 1 letra usado em algumas planilhas na coluna "Tipo".
# Igualdade exata (não substring) — "D" não deve casar com "DISJUNTOR".
CODIGOS_TIPO: dict[str, tuple[str, str]] = {
    "A": ("Analog", "Input"),
    "C": ("Discrete", "Output"),
    "D": ("Discrete", "Input"),
}


def norm(v) -> str:
    if v is None:
        return ""
    s = "".join(
        c for c in unicodedata.normalize("NFKD", str(v)) if not unicodedata.combining(c)
    )
    return " ".join(s.upper().split())


def classificar(texto) -> tuple[str, str] | None:
    n = norm(texto)
    if n in CODIGOS_TIPO:
        return CODIGOS_TIPO[n]
    if any(k in n for k in ANALOG):
        return ("Analog", "Input")
    if any(k in n for k in COMANDO):
        return ("Discrete", "Output")
    if any(k in n for k in DISCRETO):
        return ("Discrete", "Input")
    return None
