"""Corpus adversarial anti-FP.

Entradas reais que já causaram falso-positivo ou perda/troca de token,
cristalizadas como travas de não-regressão no nível determinístico da
normalização (rápido, sem modelo). Fonte: docs/anot.txt "Erros observados"
e memórias do projeto.

Os FP de sigla decidida por endereço (79, DJA1, DSEC, MOLA) já têm gate real
em bench/casos_travados.csv (comparação por endereço no TDT real); aqui ficam
só os invariantes de normalização que o gate não isola. Casos ainda quebrados
entram em CASOS_XFAIL_SIGLA (dívida conhecida, marcada xfail, não falha a suíte).
"""

# (id, texto, token que DEVE sobreviver a canonizar)
CASOS_TOKEN_PRESERVADO = [
    ("religamento_preserva", "religamento local", "RELIGAMENTO"),
    ("sgf_atuado_preserva_sgf", "protecao sensivel terra sgf atuado", "SGF"),
    ("sgf_atuado_preserva_atuado", "protecao sensivel terra sgf atuado", "ATUADO"),
    ("mola_vira_bobina", "mola carregada", "BOBINA"),  # item 2 (Task 6)
]

# (id, texto, token que canonizar NÃO pode produzir — troca indevida)
CASOS_TOKEN_PROIBIDO = [
    ("religamento_nao_desligamento", "religamento local", "DESLIGAMENTO"),
]

# (id, texto, fase esperada) — "Fase A" não pode ser perdida (vai p/ eletrico.fase)
CASOS_FASE = [
    ("fase_a_preservada", "Disjuntor 52-1 Fase A Aberto", "A"),
]

# Dívida conhecida (docs/anot.txt): sigla de proteção com padrão \d+[A-Z]\d+
# (50F1, 51N1) é removida por _ID_LETRA_NUM como se fosse ID de equipamento,
# truncando o discriminador de estágio. Gate real: bench/casos_travados.csv
# (addr 62=50F1, addr 67=51N1). xfail até a correção — quando passar, alerta.
CASOS_XFAIL_SIGLA = [
    ("50F1_preservada", "50F1 sobrecorrente instantanea", "50F1"),
    ("51N1_preservada", "51N1 neutro", "51N1"),
]
