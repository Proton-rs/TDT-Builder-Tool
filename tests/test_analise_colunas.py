import numpy as np

from tdt.analise.analise_colunas import analisar, normalizar_emb

# vocab compartilhado entre valores das colunas e a referência ADMS
_VOCAB = ["FALHA", "COMUNICACAO", "DISJUNTOR", "ABERTO", "CORRENTE", "FASE",
          "LT", "GTA", "DIGITAL", "ANALOGICO"]


def _fake_encoder(textos):
    return np.array(
        [[float(str(t).upper().split().count(w)) for w in _VOCAB] for t in textos],
        dtype="float32",
    )


# referência: descrições "ADMS" (limpas), embebidas e normalizadas
_REF = normalizar_emb(_fake_encoder(["FALHA COMUNICACAO", "DISJUNTOR ABERTO", "CORRENTE FASE"]))

# colunas com perfis distintos: 0=IED/seção, 1=módulo(const), 2=descrição, 3=tipo, 4=índice
ROWS = [
    ("", "", "SUBESTAÇÃO X", "", ""),
    ("Cab", "Modulo", "Coluna Qualquer", "T", "Addr"),  # header com nomes inúteis
    ("01F1", "LT_GTA", "FALHA COMUNICACAO IED 01F1", "Digital", "10"),
    ("01F1", "LT_GTA", "DISJUNTOR ABERTO 52-1", "Digital", "11"),
    ("01F1", "LT_GTA", "CORRENTE FASE A", "Analogico", "12"),
]


def _mapa():
    return analisar(ROWS, encoder=_fake_encoder, ref_emb=_REF)


def test_descricao_por_embedding_ignora_nome_da_coluna():
    # mesmo o header sendo "Coluna Qualquer", o conteúdo casa a lista ADMS
    assert _mapa().colunas["descricao"] == 2


def test_indice_por_padrao_sequencial():
    assert _mapa().colunas["indice"] == 4


def test_tipo_por_vocabulario():
    assert _mapa().colunas["tipo"] == 3


def test_modulo_nao_e_detectado_por_coluna():
    # módulo vem do nome da sheet (constante), não de coluna ambígua
    assert "modulo" not in _mapa().colunas


def test_descricao_prefere_multipalavra_sobre_codigo():
    # col 2 = descrições multi-palavra; col 3 = códigos de 1 token (mesma similaridade/diversidade)
    rows = [
        ("h0", "h1", "Descricao", "Codigo", "Addr"),
        ("01F1", "LT_GTA", "FALHA COMUNICACAO", "FALHA", "10"),
        ("01F2", "LT_GTA", "DISJUNTOR ABERTO", "DISJUNTOR", "11"),
        ("02F1", "LT_GTA", "CORRENTE FASE", "CORRENTE", "12"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert mapa.colunas["descricao"] == 2


def test_header_em_sheet_esparsa():
    # dados MUITO esparsos (só IED+descrição preenchidos) -> poucas colunas
    # passam de 30% de densidade; header é a linha mais densa, não o fallback.
    rows = [
        ("#VALUE", "", "SUBESTACAO X", "", "", ""),
        ("", "", "Lista de Pontos", "", "", ""),
        ("", "", "Protocolo", "", "", ""),
        ("IED", "Modulo", "Descricao", "Variavel", "Tipo", "Addr"),
        ("01F1", "", "FALHA COMUNICACAO", "", "", ""),
        ("34F1", "", "DISJUNTOR ABERTO", "", "", ""),
        ("02F1", "", "CORRENTE FASE", "", "", ""),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert mapa.header_row == 4  # 1-based
    assert mapa.colunas["descricao"] == 2


def test_tipo_por_codigo_curto():
    rows = [
        ("h0", "h1", "Descricao", "Tipo", "Addr"),
        ("01F1", "LT_GTA", "FALHA COMUNICACAO", "D", "10"),
        ("01F1", "LT_GTA", "DISJUNTOR ABERTO", "C", "11"),
        ("01F1", "LT_GTA", "CORRENTE FASE A", "A", "12"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert mapa.colunas["tipo"] == 3


def test_tipo_por_codigo_curto_nao_pega_coluna_de_fase():
    # fase trifásica A/B/C — não deve ser confundida com código de tipo
    rows = [
        ("h0", "h1", "Descricao", "Fase", "Addr"),
        ("01F1", "LT_GTA", "CORRENTE FASE A", "A", "10"),
        ("01F1", "LT_GTA", "CORRENTE FASE B", "B", "11"),
        ("01F1", "LT_GTA", "CORRENTE FASE C", "C", "12"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert "tipo" not in mapa.colunas


def test_header_descricao_boost_seleciona_coluna_com_descricao_no_titulo():
    # colunas com conteúdo idêntico: a que tem "DESCRICAO" no header ganha
    rows = [
        ("", "", "", ""),
        ("", "DESCRICAO DO PONTO", "OUTRO TITULO", ""),
        ("001", "FALHA COMUNICACAO IED 01F1", "FALHA COMUNICACAO IED 01F1", "10"),
        ("001", "DISJUNTOR ABERTO 52-1", "DISJUNTOR ABERTO 52-1", "11"),
        ("001", "CORRENTE FASE A", "CORRENTE FASE A", "12"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert mapa.colunas["descricao"] == 1


def test_header_descricao_nao_seleciona_coluna_vazia_mesmo_com_titulo():
    # header com "DESCRICAO" mas coluna vazia → não ganha (não entra nos
    # candidatos)
    rows = [
        ("", "", "", "", ""),
        ("IED", "DESCRICAO", "MELHOR TITULO", "TIPO", "ADDR"),
        ("01F1", "", "FALHA COMUNICACAO", "Digital", "10"),
        ("01F1", "", "DISJUNTOR ABERTO", "Digital", "11"),
        ("01F1", "", "CORRENTE FASE", "Analogico", "12"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert mapa.colunas["descricao"] == 2  # conteúdo vence, não header


def test_header_ignora_metadado_espalhado():
    # linha de metadado com 4 células de texto ESPALHADAS não é o header;
    # o header real preenche a maioria das colunas de dados (contíguas).
    rows = [
        ("", "", "Relé Siemens", "", "", "Falha Aqui", "IP 10.3", "", "Concentradora", ""),
        ("IED", "Modulo", "Descricao", "Variavel", "Tipo", "Origem", "Logica", "Addr", "N2", "N3"),
        ("Digitais", "", "", "", "", "", "", "", "", ""),
        ("01F1", "LT_GTA", "FALHA COMUNICACAO", "x", "Digital", "UCCD1", "Direto", "10", "", ""),
        ("01F1", "LT_GTA", "DISJUNTOR ABERTO", "y", "Digital", "UCCD1", "Direto", "11", "", ""),
        ("01F1", "LT_GTA", "CORRENTE FASE", "z", "Digital", "UCCD1", "Direto", "12", "", ""),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert mapa.header_row == 2  # 1-based: a row "IED|Modulo|..."
    assert mapa.colunas["descricao"] == 2  # não a coluna "Logica" (Direto)


def test_descricao_chama_encoder_uma_vez_independente_do_numero_de_colunas():
    # perf: analisar() não deve chamar o encoder 1x por coluna candidata —
    # isso é o que torna sheets largas (200+ colunas) lentas. O encoder deve
    # ser chamado uma única vez (batch) com todas as amostras de texto.
    chamadas = []

    def _encoder_contador(textos):
        chamadas.append(len(textos))
        return _fake_encoder(textos)

    rows = [
        ("Cab", "Modulo", "Coluna A", "Coluna B", "Coluna C"),
        ("01F1", "LT_GTA", "FALHA COMUNICACAO IED 01F1", "metadado x", "Digital"),
        ("01F1", "LT_GTA", "DISJUNTOR ABERTO 52-1", "metadado y", "Digital"),
        ("01F1", "LT_GTA", "CORRENTE FASE A", "metadado z", "Analogico"),
    ]
    mapa = analisar(rows, encoder=_encoder_contador, ref_emb=_REF)
    assert mapa.colunas["descricao"] == 2
    assert len(chamadas) == 1


def test_descricao_limita_amostra_por_coluna_para_nao_codificar_tudo():
    # perf: colunas com muitos valores (sheets de centenas/milhares de linhas)
    # não devem mandar TODOS os valores pro encoder — uma amostra já basta
    # pra estimar similaridade/diversidade, e reduz o volume de texto
    # codificado (custo dominante é o modelo BERT, não Python).
    chamadas = []

    def _encoder_contador(textos):
        chamadas.append(len(textos))
        return _fake_encoder(textos)

    rows = [("Cab", "Modulo", "Coluna A")]
    descricoes = ["FALHA COMUNICACAO IED 001", "DISJUNTOR ABERTO 52-1", "CORRENTE FASE A"]
    rows += [("001", "LT_GTA", descricoes[i % len(descricoes)]) for i in range(500)]

    mapa = analisar(rows, encoder=_encoder_contador, ref_emb=_REF)
    assert mapa.colunas["descricao"] == 2
    # 2 colunas candidatas (Modulo, Coluna A — "001" não tem letra, não conta)
    assert chamadas[0] <= 80  # amostra pequena já é suficiente (medido: sem
    # divergência de coluna detectada com cap 200→20 em sheets reais de até
    # 1238 linhas; cap=40 dá ~2-4x menos texto codificado sem mudar resultado)


# --- _col_sigla() / siglas_set (sigla em lista não-homogênea) ---------------

_SIGLAS = frozenset({"IA", "IB", "IC", "P", "Q", "FREQ", "79"})


def test_col_sigla_detectada_quando_maioria_e_sigla_conhecida():
    rows = [
        ("SIGLA", "NOME", "DESCRICAO", "TIPO", "IDX"),
        ("IA", "SND_LT_IA", "CORRENTE FASE A", "Analogico", "1"),
        ("IB", "SND_LT_IB", "CORRENTE FASE B", "Analogico", "2"),
        ("IC", "SND_LT_IC", "CORRENTE FASE C", "Analogico", "3"),
        ("P", "SND_LT_P", "FALHA COMUNICACAO", "Analogico", "4"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF, siglas_set=_SIGLAS)
    assert mapa.colunas["sigla"] == 0


def test_col_sigla_nao_detecta_coluna_de_nome_padronizado():
    # coluna NOME (códigos tipo SND_LT_IA) não tem nenhum valor em siglas_set
    rows = [
        ("NOME", "DESCRICAO", "TIPO", "IDX"),
        ("SND_LT_IA", "CORRENTE FASE A", "Analogico", "1"),
        ("SND_LT_IB", "CORRENTE FASE B", "Analogico", "2"),
        ("SND_LT_IC", "CORRENTE FASE C", "Analogico", "3"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF, siglas_set=_SIGLAS)
    assert "sigla" not in mapa.colunas


def test_col_sigla_exclui_coluna_puramente_numerica():
    # mesmo que os dígitos "coincidam" com siglas_set, coluna >80% dígitos é índice
    siglas_com_numeros = _SIGLAS | {"1", "2", "3", "4"}
    rows = [
        ("IDX", "DESCRICAO", "TIPO", "ADDR"),
        ("1", "CORRENTE FASE A", "Analogico", "10"),
        ("2", "CORRENTE FASE B", "Analogico", "11"),
        ("3", "CORRENTE FASE C", "Analogico", "12"),
        ("4", "FALHA COMUNICACAO", "Analogico", "13"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF, siglas_set=siglas_com_numeros)
    assert "sigla" not in mapa.colunas


def test_col_sigla_threshold_30_porcento():
    # 2 de 5 valores (40%) são siglas conhecidas -> detecta (>= 0.3)
    rows = [
        ("COL", "DESCRICAO", "TIPO", "IDX"),
        ("79", "PROTECAO ATUADA", "Digital", "1"),
        ("SINAL_79", "OUTRO PONTO", "Digital", "2"),
        ("LX_80", "MAIS UM PONTO", "Digital", "3"),
        ("P", "FALHA COMUNICACAO", "Digital", "4"),
        ("ZZ_INVALIDO", "CORRENTE FASE A", "Digital", "5"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF, siglas_set=_SIGLAS)
    assert mapa.colunas["sigla"] == 0


def test_sem_siglas_set_nao_detecta_sigla():
    # comportamento atual preservado quando siglas_set não é passado
    rows = [
        ("SIGLA", "DESCRICAO", "TIPO", "IDX"),
        ("IA", "CORRENTE FASE A", "Analogico", "1"),
        ("IB", "CORRENTE FASE B", "Analogico", "2"),
    ]
    mapa = analisar(rows, encoder=_fake_encoder, ref_emb=_REF)
    assert "sigla" not in mapa.colunas
