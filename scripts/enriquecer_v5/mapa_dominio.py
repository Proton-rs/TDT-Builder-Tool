"""Termos curados a acrescentar (append-only) para siglas não-ANSI sem regra.

Fonte: sheets internas da lista (`DiscreteSignals`/`Funcionamento`, `DMS Signal
Explanation`, `Information` — docs/Pontos Padrao ADMS_v2.xlsx) + domínio
ADMS/proteção de subestação (skill especialista-ADMS).

Curadoria conservadora: só siglas cuja DESCRIÇÃO NOVA v1 é curta/críptica e cujo
significado é conhecido com confiança no domínio. A maioria da cauda não-ANSI já
tem descrição PT autoexplicativa (ex. "ALARME BATERIA", "BLOQUEIO DISJUNTOR") —
essas NÃO entram aqui, pois acrescentar termos seria ruído, não valor. Na
dúvida, deixar de fora — preservar v1 é sempre seguro (cai no `return v1`).
"""
from __future__ import annotations

MAPA: dict[str, str] = {
    # --- siglas funcionais sem regra, descrição v1 críptica (starter do brief) ---
    "TAL": "TRANSFERÊNCIA AUTOMÁTICA DE LINHA, COMUTAÇÃO DE ALIMENTAÇÃO",
    "TPPM": "TRANSFERÊNCIA COM PARALELISMO MOMENTÂNEO",
    "ABBN": "ABERTURA PELA BOBINA DE NEUTRO, COMANDO DE TRIP POR NEUTRO",
    "CMDE": "PROPRIEDADE/POSSE DO COMANDO (CONTROLE SCADA)",
    "CCIC": "CHAVE DE COMANDO ICCP (TELECONTROLE), SELEÇÃO DE QUEM DETÉM O CONTROLE DOS EQUIPAMENTOS",

    # --- grupo de ajuste / religador — confirmado por nota interna (Funcionamento) ---
    "GRPO": "GRUPO DE AJUSTE DO RELIGADOR, TROCA DE PARAMETRIZAÇÃO",
    "AJGP": "GRUPOS DE AJUSTE DE DISJUNTORES DE SUBTRANSMISSÃO",

    # --- hot line tag — bloqueio de religamento p/ trabalho em linha viva ---
    "HLT": "HOT LINE TAG, BLOQUEIO DE RELIGAMENTO AUTOMÁTICO E MANUAL PARA TRABALHO EM LINHA VIVA",

    # --- proteção de barra — função tipo 50 da barra, confirmado por nota interna ---
    "PB": "PROTEÇÃO DE BARRA, FUNÇÃO TIPO 50 DA BARRA, TEMPO PRÉ-DETERMINADO PARA SELETIVIDADE",
    "PBF": "PROTEÇÃO DE BARRA FASE, FUNÇÃO TIPO 50 DA BARRA",
    "PBF1": "PROTEÇÃO DE BARRA FASE, FUNÇÃO TIPO 50 DA BARRA, ENROLAMENTO 1",
    "PBF2": "PROTEÇÃO DE BARRA FASE, FUNÇÃO TIPO 50 DA BARRA, ENROLAMENTO 2",
    "PBN": "PROTEÇÃO DE BARRA NEUTRO, FUNÇÃO TIPO 50N DA BARRA",
    "PBN1": "PROTEÇÃO DE BARRA NEUTRO, FUNÇÃO TIPO 50N DA BARRA, ENROLAMENTO 1",
    "PBN2": "PROTEÇÃO DE BARRA NEUTRO, FUNÇÃO TIPO 50N DA BARRA, ENROLAMENTO 2",
    "PB1": "PROTEÇÃO DE BARRA, FUNÇÃO TIPO 50 DA BARRA, ENROLAMENTO 1",
    "PB2": "PROTEÇÃO DE BARRA, FUNÇÃO TIPO 50 DA BARRA, ENROLAMENTO 2",
    "PBEX": "FUNÇÃO PROTEÇÃO DE BARRA, FUNÇÃO TIPO 50 DA BARRA",

    # --- intertrip — esquema de teleproteção, disparo remoto coordenado ---
    "ITFA": "INTERTRIP FASE A, DISPARO REMOTO RECEBIDO DE TELEPROTEÇÃO",
    "ITFB": "INTERTRIP FASE B, DISPARO REMOTO RECEBIDO DE TELEPROTEÇÃO",
    "ITFC": "INTERTRIP FASE C, DISPARO REMOTO RECEBIDO DE TELEPROTEÇÃO",
    "ITGE": "INTERTRIP GERAL, DISPARO REMOTO RECEBIDO DE TELEPROTEÇÃO",

    # --- esquemas de teleproteção padrão (terminologia consolidada de proteção) ---
    "DTT": "DIRECT TRANSFER TRIP, TRANSFERÊNCIA DIRETA DE DISPARO POR TELEPROTEÇÃO",
    "DTTT": "DIRECT TRANSFER TRIP TRIFÁSICO, TRANSFERÊNCIA DIRETA DE DISPARO POR TELEPROTEÇÃO",
    "POTT": "PERMISSIVE OVERREACH TRANSFER TRIP, ESQUEMA DE TELEPROTEÇÃO POR SOBREALCANCE PERMISSIVO",
    "SOTF": "SWITCH ONTO FAULT, FECHAMENTO SOB FALTA",
    # SOTX removido: significado não confirmado (nomenclatura não-padrão, sem nota
    # interna). Preservar v1 é seguro — cai no `return v1` da cauda.

    # --- estado de contato de disjuntor — confirmado por nota interna (retificador) ---
    "DJA1": "DISJUNTOR NORMALMENTE ABERTO (CONTATO NA)",
}
