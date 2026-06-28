"""Ground-truth curado (v1, histórico): descrição real (não-homogêneo) -> sigla ADMS correta.

Os 28 pares originais, curados manualmente, que serviram de ground-truth do
benchmark antes da spec SP-GT (2026-06-28). Preservados aqui por valor
histórico — não são mais usados diretamente pelo benchmark, que agora
importa de bench/rotulos.py (gerado por scripts/gerar_ground_truth.py a
partir da Lista Padrão v2 + Export Full Base limpo).

Rótulos de domínio (ver skill especialista-ADMS-TDT). Cada sigla deve
existir na lista padrão.
"""

ROTULOS_V1: list[tuple[str, str]] = [
    ("Corrente Fase A", "IA"),
    ("Corrente Fase B", "IB"),
    ("Corrente Fase C", "IC"),
    ("Corrente de Desbalanço", "IN61"),
    ("Tensão Fase A", "VA"),
    ("Tensão Fase B", "VB"),
    ("Tensão Fase C", "VC"),
    ("Potência Ativa", "P"),
    ("Potência Reativa", "Q"),
    ("Frequência", "FREQ"),
    ("Falha Comunicação IED 01F1", "FCOM"),
    ("Falha de Comunicação Relé", "FCRT"),
    ("Disj. 52-1 (01Q0) - Baixa Pressão SF6 - Bloqueio", "SF6B"),
    ("Chave 43TC Excluida", "43TC"),
    ("Chave 43LR Pos. Remoto", "43LR"),
    ("Diferencial (87) Bloqueado", "87"),
    ("Check de Sincronismo (25) - Bloquear / Desbloquear", "25IE"),
    ("CDC - Bloqueio", "CDC"),
    ("CDC - TAP Máximo", "CDC"),
    ("Religamento (79) - Bloqueado", "79"),
    ("Hot Line Tag", "HLT"),
    ("Temperatura Óleo", "TOLE"),
    ("Temperatura Enrolamento", "TENR"),
    ("Ventilação Forçada 1", "VF1"),
    ("Distância de Defeito", "KMDF"),
    ("Umidade", "UMID"),
    ("Contagem de Operações", "OPER"),
    ("Operação Indevida Seccionadora", "OI"),
]
