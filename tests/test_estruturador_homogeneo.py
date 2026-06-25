from tdt.config import Config
from tdt.dados.lista_padrao import SinalPadrao
from tdt.estruturador_homogeneo import detectar_header, estruturar_homogeneo


def test_detectar_header_acha_linha_no_formato_fixo():
    rows = [
        ("EQUIPAMENTO", "NÚMERO OPERATIVO / MNEMÔNICO"),
        ("DJ", "52-11"),
        (),
        ("Utilizado?", "SUBESTAÇÃO", "MÓDULO", "EQUIPAMENTO", "TIPO",
         "DESCRIÇÃO DO PONTO", "SIGLA SINAL", "NOME", "Tipo",
         "Nível Lógico 0", "Nível Lógico 1", "Escala",
         "Control Code / Qualificador", "INDEX DNP3"),
        ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
         "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70"),
    ]
    assert detectar_header(rows) == 3


def test_detectar_header_devolve_none_sem_formato_fixo():
    rows = [("DESCRIÇÃO", "ÍNDICE"), ("Disjuntor 52-2", "100")]
    assert detectar_header(rows) is None


class _ListaPadraoFake:
    def __init__(self, siglas: dict[str, SinalPadrao]):
        self._siglas = siglas

    def por_sigla(self, sigla):
        return self._siglas.get(sigla.strip().upper())


def _sinal_padrao(sigla: str) -> SinalPadrao:
    return SinalPadrao(
        sigla=sigla, descricao="CORRENTE FASE A", signal_type="Current",
        direction=None, mm=None, categoria="Analog",
    )


_HEADER = (
    "Utilizado?", "SUBESTAÇÃO", "MÓDULO", "EQUIPAMENTO", "TIPO",
    "DESCRIÇÃO DO PONTO", "SIGLA SINAL", "NOME", "Tipo",
    "Nível Lógico 0", "Nível Lógico 1", "Escala",
    "Control Code / Qualificador", "INDEX DNP3",
)


def test_linha_com_sigla_valida_vira_decidido_sem_scoring():
    rows = [_HEADER, ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
                       "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({"IA": _sinal_padrao("IA")})
    decididos, pendentes = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert pendentes == []
    assert len(decididos) == 1
    rec = decididos[0]
    assert rec.sigla_sinal == "IA"
    assert rec.status == "decidido"
    assert rec.modulo.nome == "AL"
    assert rec.enderecamento.indices == (70,)


def test_linha_nao_utilizada_nao_vira_sinal():
    rows = [_HEADER, ("NÃO", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "IA",
                       "IMA_AL11_AL11_IA", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({"IA": _sinal_padrao("IA")})
    decididos, pendentes = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert decididos == [] and pendentes == []


def test_sigla_inexistente_na_lista_padrao_vai_pra_pendentes():
    rows = [_HEADER, ("SIM", "IMA", "AL", "TC", "A", "CORRENTE FASE A", "XYZ",
                       "IMA_AL11_AL11_XYZ", "-", "-", "-", "1", "-", "70")]
    lp = _ListaPadraoFake({})
    decididos, pendentes = estruturar_homogeneo(rows, 0, "AL 11", lp, Config())
    assert decididos == [] and len(pendentes) == 1


def test_equipamento_disjuntor_mapeado_por_modulo_dj():
    rows = [_HEADER, ("SIM", "IMA", "DJ1", "DJ", "D", "DISJUNTOR 52-1 ABERTO", "DJF1",
                       "IMA_DJ1_DJF1", "-", "-", "-", "-", "-", "100;101")]
    lp = _ListaPadraoFake({"DJF1": _sinal_padrao("DJF1")})
    decididos, _ = estruturar_homogeneo(rows, 0, "DJ1", lp, Config())
    assert decididos[0].eletrico.equipamento_alvo == "Disjuntor"
    assert decididos[0].enderecamento.indices == (100, 101)
