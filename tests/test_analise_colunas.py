import numpy as np

from tdt.analise_colunas import analisar, normalizar_emb

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
