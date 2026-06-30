"""Extrai informações estruturadas do nome padronizado de sinal ADMS.

Formato esperado: {SE}_{MODULO}_{EQUIPAMENTO}_{SIGLA}
Ex: SND_LT67SAN_LT67SAN_79 → SE=SND, MODULO=LT67SAN, SIGLA=79
Ex: SND_LT67TPJ2_LT67TPJ2_89-20_DSEC → SE=SND, MODULO=LT67TPJ2, SIGLA=89-20_DSEC
"""

from __future__ import annotations


def extrair_modulo_do_nome(nome: str) -> str | None:
    """2º token após split por '_', se existir."""
    partes = str(nome).strip().split("_")
    return partes[1] if len(partes) >= 3 else None


def extrair_se_do_nome(nome: str) -> str | None:
    """1º token após split por '_', se existir."""
    partes = str(nome).strip().split("_")
    return partes[0] if partes else None


def extrair_equipamento_do_nome(nome: str) -> str | None:
    """3º token (EQUIPAMENTO) após split por '_', se existir.

    Distingue instâncias do mesmo módulo (ex: "SLOTD" vs "SLOTD-2" vs
    "SLOTD-3") -- necessário pra alimentar ``eletrico.nome_equipamento``,
    que é o que a chave de dedup de `normalizador_estrutural._chave`
    (modulo, nome_equipamento, sigla) usa pra não tratar instâncias
    diferentes como duplicata de endereço.
    """
    partes = str(nome).strip().split("_")
    return partes[2] if len(partes) >= 4 else None


def sigla_esta_no_nome(nome: str, sigla: str) -> bool:
    """A sigla aparece como TOKEN FINAL do nome (case-insensitive).

    O nome padronizado é {SE}_{MODULO}_{EQUIP}_{SIGLA}; a sigla é o sufixo
    após o último '_' (possivelmente composto, ex. "89-20_DSEC"). Comparamos
    por SUFIXO precedido de '_' (ou igualdade total) -- não por substring
    solta -- para não cair na fragilidade de siglas de 1 char: substring
    "P" in "..._P_..." casaria mesmo se "P" não for o token final.
    """
    if not nome or not sigla:
        return False
    n = nome.strip().upper()
    s = sigla.strip().upper()
    return n == s or n.endswith("_" + s)


def validar_consistencia_modulo(
    mod_nome: str | None,
    mod_sheet: str | None,
) -> str | None:
    """Valida consistência entre módulo extraído do NOME e da sheet.

    Retorna None se OK, string com motivo se divergir.
    """
    if mod_nome is None or mod_sheet is None:
        return None  # uma das fontes não está disponível — não há conflito
    if mod_nome.upper() == mod_sheet.upper():
        return None
    return f"modulo_nome={mod_nome} != modulo_sheet={mod_sheet}"
