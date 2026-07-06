from dataclasses import replace

import pytest

from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.ui.estado import AppState
from tdt.ui.modelo_tabela import ModeloSinais
from tdt.ui.proxy_revisao import ProxyRevisao

pytest.importorskip("PySide6")


def _rec(id_, status, bruta):
    return SignalRecord(
        id=id_, modulo=Modulo("M", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (1,)),
        descricoes=Descricoes(bruta, bruta),
        status=status,
    )


def _estado_com(registros):
    e = AppState()
    e.registros = registros
    return e


def test_esconder_decididos_filtra_linhas():
    estado = _estado_com([
        _rec("1", "decidido", "A"),
        _rec("2", "revisao", "B"),
    ])
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.set_status_visivel("revisao")
    assert proxy.rowCount() == 1
    col_status = ModeloSinais.COLUNAS.index("Status")
    assert proxy.index(0, col_status).data() == "revisao"


def test_esconder_decididos_desativado_mostra_tudo():
    estado = _estado_com([
        _rec("1", "decidido", "A"),
        _rec("2", "revisao", "B"),
    ])
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.set_status_visivel(None)
    assert proxy.rowCount() == 2


def test_map_to_source_aponta_pro_registro_correto_apos_filtro():
    estado = _estado_com([
        _rec("1", "decidido", "A"),
        _rec("2", "revisao", "B"),
    ])
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.set_status_visivel("revisao")
    fonte = proxy.mapToSource(proxy.index(0, 0))
    assert fonte.row() == 1  # registro "2" é o índice 1 na fonte


def _proxy_com(registros):
    estado = _estado_com(registros)
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    return proxy


def test_filtro_coluna_isola_linhas():
    proxy = _proxy_com([
        _rec("1", "decidido", "DISJUNTOR ABERTO"),
        _rec("2", "revisao", "SECCIONADORA FECHADA"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    proxy.setFiltroColuna(col_desc, "DISJUNTOR")
    assert proxy.rowCount() == 1
    assert proxy.index(0, col_desc).data() == "DISJUNTOR ABERTO"


def test_filtros_multiplas_colunas_combinam_em_and():
    proxy = _proxy_com([
        _rec("1", "decidido", "DISJUNTOR ABERTO"),
        _rec("2", "revisao", "DISJUNTOR FECHADO"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    col_status = ModeloSinais.COLUNAS.index("Status")
    proxy.setFiltroColuna(col_desc, "DISJUNTOR")
    proxy.setFiltroColuna(col_status, "revisao")
    assert proxy.rowCount() == 1
    assert proxy.index(0, col_desc).data() == "DISJUNTOR FECHADO"


def test_filtro_coluna_vazio_remove_filtro():
    proxy = _proxy_com([
        _rec("1", "decidido", "DISJUNTOR ABERTO"),
        _rec("2", "revisao", "SECCIONADORA FECHADA"),
    ])
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    proxy.setFiltroColuna(col_desc, "DISJUNTOR")
    assert proxy.filtroColuna(col_desc) == "DISJUNTOR"
    proxy.setFiltroColuna(col_desc, "")
    assert proxy.filtroColuna(col_desc) == ""
    assert proxy.rowCount() == 2


# --- set_sheet (SP-J Task 2: abas por sheet no lugar do filtro global) ---

def _modelo_com_itens(itens):
    """itens: lista de (sigla, sheet) -> registros com id f"{sheet}:{i}"."""
    registros = [
        _rec(f"{sheet}:{i}", "revisao", sigla)
        for i, (sigla, sheet) in enumerate(itens)
    ]
    estado = _estado_com(registros)
    return ModeloSinais(estado)


def test_filtro_por_sheet(qapp):
    modelo = _modelo_com_itens([("sig1", "Discreto"), ("sig2", "Analogicos")])
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.set_sheet("Discreto")
    assert proxy.rowCount() == 1
    proxy.set_sheet(None)
    assert proxy.rowCount() == 2


# --- filtro estilo Excel por coluna (SP-J Task 3: multi-valor, combina AND
# com o filtro de texto legado, com set_sheet da Task 2 e entre colunas) ---

_COL_MOTIVO = ModeloSinais.COLUNAS.index("Motivo")
_COL_STATUS = ModeloSinais.COLUNAS.index("Status")


def _motivo(proxy, linha):
    return proxy.index(linha, _COL_MOTIVO).data()


def _proxy_padrao():
    return _proxy_com([
        _rec("Discreto:1", "revisao", "DISJUNTOR ABERTO"),
        _rec("Discreto:2", "decidido", "SECCIONADORA FECHADA"),
        _rec("Analogicos:3", "revisao", "TENSAO BARRA"),
    ])


def test_filtro_coluna_combina_and(qapp):
    proxy = _proxy_padrao()
    proxy.set_filtro_coluna(_COL_STATUS, {"revisao"})
    proxy.set_filtro_coluna(_COL_MOTIVO, {"—"})
    # ambos os filtros já isolam o mesmo conjunto (registros sem motivo
    # calculado exibem "—"); a asserção real é que o AND não derruba tudo.
    assert proxy.rowCount() >= 1
    assert all(_motivo(proxy, i) == "—" for i in range(proxy.rowCount()))


def test_filtro_coluna_combina_and_com_sheet(qapp):
    proxy = _proxy_padrao()
    proxy.set_filtro_coluna(_COL_STATUS, {"revisao"})
    proxy.set_sheet("Discreto")
    assert proxy.rowCount() == 1
    col_desc = ModeloSinais.COLUNAS.index("Descr. bruta")
    assert proxy.index(0, col_desc).data() == "DISJUNTOR ABERTO"


def test_limpar_filtro(qapp):
    proxy = _proxy_padrao()
    proxy.set_filtro_coluna(_COL_MOTIVO, {"score_baixo"})
    assert _COL_MOTIVO in proxy.colunas_filtradas()
    proxy.set_filtro_coluna(_COL_MOTIVO, None)
    assert _COL_MOTIVO not in proxy.colunas_filtradas()
    assert proxy.rowCount() == 3


def test_valores_unicos_retorna_valores_distintos_ordenados(qapp):
    proxy = _proxy_padrao()
    assert proxy.valores_unicos(_COL_STATUS) == ["decidido", "revisao"]


def test_set_filtro_coluna_none_nao_aparece_em_colunas_filtradas(qapp):
    proxy = _proxy_padrao()
    assert proxy.colunas_filtradas() == set()
    proxy.set_filtro_coluna(_COL_STATUS, {"revisao"})
    assert proxy.colunas_filtradas() == {_COL_STATUS}


# --- indicador de filtro ativo no header (SP-J Task 4) ---

def test_header_data_marca_coluna_filtrada(qapp):
    from PySide6.QtCore import Qt

    proxy = _proxy_padrao()
    rotulo_base = proxy.headerData(_COL_STATUS, Qt.Horizontal)
    proxy.set_filtro_coluna(_COL_STATUS, {"revisao"})
    assert proxy.headerData(_COL_STATUS, Qt.Horizontal) == f"{rotulo_base} ▼*"


def test_header_data_volta_ao_normal_apos_limpar_filtro(qapp):
    from PySide6.QtCore import Qt

    proxy = _proxy_padrao()
    rotulo_base = proxy.headerData(_COL_STATUS, Qt.Horizontal)
    proxy.set_filtro_coluna(_COL_STATUS, {"revisao"})
    proxy.set_filtro_coluna(_COL_STATUS, None)
    assert proxy.headerData(_COL_STATUS, Qt.Horizontal) == rotulo_base


def test_set_filtro_coluna_emite_header_data_changed_so_quando_muda(qapp):
    from PySide6.QtCore import Qt

    proxy = _proxy_padrao()
    emissoes = []
    proxy.headerDataChanged.connect(
        lambda orientacao, first, last: emissoes.append((orientacao, first, last))
    )

    proxy.set_filtro_coluna(_COL_STATUS, {"revisao"})
    assert emissoes == [(Qt.Horizontal, _COL_STATUS, _COL_STATUS)]

    # reaplicar valores diferentes na mesma coluna já filtrada não muda o
    # conjunto de "colunas filtradas" -- não deve reemitir.
    proxy.set_filtro_coluna(_COL_STATUS, {"decidido"})
    assert emissoes == [(Qt.Horizontal, _COL_STATUS, _COL_STATUS)]

    proxy.set_filtro_coluna(_COL_STATUS, None)
    assert emissoes == [
        (Qt.Horizontal, _COL_STATUS, _COL_STATUS),
        (Qt.Horizontal, _COL_STATUS, _COL_STATUS),
    ]


def test_set_status_visivel_revisao_esconde_decididos():
    proxy = _proxy_com([_rec("a:1", "decidido", "DJF1"), _rec("a:2", "revisao", None)])
    proxy.set_status_visivel("revisao")
    assert proxy.rowCount() == 1


def test_set_status_visivel_none_mostra_tudo():
    proxy = _proxy_com([_rec("a:1", "decidido", "DJF1"), _rec("a:2", "revisao", None)])
    proxy.set_status_visivel("decidido")
    proxy.set_status_visivel(None)
    assert proxy.rowCount() == 2


def test_filtros_ativos_conta_texto_e_valores(qtbot):
    proxy = _proxy_com([_rec("a:1", "DJF1", "decidido")])
    assert proxy.filtros_ativos() == 0
    proxy.setFiltroColuna(0, "DJ")
    proxy.set_filtro_coluna(2, {"decidido"})
    assert proxy.filtros_ativos() == 2
    proxy.limpar_filtros()
    assert proxy.filtros_ativos() == 0


def test_marcador_header_para_filtro_texto(qtbot):
    from PySide6.QtCore import Qt
    proxy = _proxy_com([_rec("a:1", "DJF1", "decidido")])
    proxy.setFiltroColuna(0, "DJ")
    assert "▼" in proxy.headerData(0, Qt.Horizontal, Qt.DisplayRole)
