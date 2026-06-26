"""Tabela ANSI/IEEE C37.2 verificada (device number -> função em PT).

Fonte: ANSI/IEEE C37.2 (standard device function numbers). Os ambíguos/menos
comuns (26, 62, 71, 78, 85, 90, 94) foram web-verificados; 61 diverge da
convenção da v1 e é tratado como conflito (não recebe função, vai pro sidecar).
"""
from __future__ import annotations

ANSI_C37_2: dict[int, str] = {
    20: "VÁLVULA OPERADA ELETRICAMENTE (SOLENOIDE)",
    21: "RELÉ DE DISTÂNCIA (IMPEDÂNCIA)",
    24: "RELÉ VOLTS/HERTZ (PROTEÇÃO CONTRA SOBREEXCITAÇÃO / FLUXO MAGNÉTICO)",
    25: "RELÉ DE SINCRONISMO OU VERIFICAÇÃO DE SINCRONISMO",
    26: "DISPOSITIVO TÉRMICO DE EQUIPAMENTO",
    27: "RELÉ DE SUBTENSÃO",
    32: "RELÉ DIRECIONAL DE POTÊNCIA",
    43: "DISPOSITIVO DE TRANSFERÊNCIA OU SELETOR MANUAL",
    46: "RELÉ DE CORRENTE DE SEQUÊNCIA NEGATIVA / DESEQUILÍBRIO DE FASE",
    49: "RELÉ TÉRMICO (DE MÁQUINA OU TRANSFORMADOR)",
    50: "RELÉ DE SOBRECORRENTE INSTANTÂNEA",
    51: "RELÉ DE SOBRECORRENTE TEMPORIZADA (TEMPO INVERSO)",
    59: "RELÉ DE SOBRETENSÃO",
    62: "RELÉ DE TEMPORIZAÇÃO DE PARADA OU ABERTURA",
    63: "RELÉ/CHAVE DE PRESSÃO (BUCHHOLZ / SÚBITA PRESSÃO)",
    67: "RELÉ DIRECIONAL DE SOBRECORRENTE CA",
    71: "RELÉ/CHAVE DE NÍVEL DE LÍQUIDO OU GÁS",
    78: "RELÉ DE MEDIÇÃO DE ÂNGULO DE FASE / PERDA DE SINCRONISMO (OUT-OF-STEP)",
    79: "RELÉ DE RELIGAMENTO AUTOMÁTICO CA",
    81: "RELÉ DE FREQUÊNCIA (SUB/SOBREFREQUÊNCIA)",
    85: "RELÉ DE TELEPROTEÇÃO (CARRIER / FIO PILOTO)",
    86: "RELÉ DE BLOQUEIO (LOCKOUT, REARME MANUAL)",
    87: "RELÉ DE PROTEÇÃO DIFERENCIAL",
    90: "DISPOSITIVO REGULADOR (TENSÃO/POTÊNCIA/FREQUÊNCIA)",
    94: "RELÉ DE DISPARO OU DISPARO LIVRE (TRIP / TRIP-FREE)",
}

# Termos curtos de alto valor por código (acrescentados além da função).
SINONIMOS_ANSI: dict[int, tuple[str, ...]] = {
    50: ("PROTEÇÃO INSTANTÂNEA", "CURTO-CIRCUITO"),
    51: ("PROTEÇÃO TEMPORIZADA", "COORDENAÇÃO"),
    27: ("PERDA DE TENSÃO",),
    59: ("SOBRETENSÃO",),
    67: ("DIRECIONAL",),
    79: ("RELIGAMENTO", "RELIGA"),
    86: ("LOCKOUT", "BLOQUEIO"),
    87: ("PROTEÇÃO DIFERENCIAL",),
    81: ("FREQUÊNCIA",),
}

# Códigos onde a convenção da v1 diverge do padrão C37.2 -> sidecar, sem
# acrescentar função contraditória (preservar v1).
CONFLITO_V1: dict[int, str] = {
    61: ("v1 usa '(des)equilíbrio'; C37.2 define 61 como chave/sensor de densidade. "
         "Verificar convenção da concessionária antes de descrever."),
}

CODIGOS_PRESENTES: frozenset[int] = frozenset(
    {20, 21, 24, 25, 26, 27, 32, 43, 46, 49, 50, 51, 59, 61,
     62, 63, 67, 71, 78, 79, 81, 85, 86, 87, 90, 94}
)
