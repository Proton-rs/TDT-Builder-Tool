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
        tipo_sinal=TipoSinal("Discrete", False, "Input"),
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
    proxy.setEsconderDecididos(True)
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
    proxy.setEsconderDecididos(False)
    assert proxy.rowCount() == 2


def test_map_to_source_aponta_pro_registro_correto_apos_filtro():
    estado = _estado_com([
        _rec("1", "decidido", "A"),
        _rec("2", "revisao", "B"),
    ])
    modelo = ModeloSinais(estado)
    proxy = ProxyRevisao()
    proxy.setSourceModel(modelo)
    proxy.setEsconderDecididos(True)
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
