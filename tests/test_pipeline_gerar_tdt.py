from pathlib import Path
import pytest
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt import pipeline
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal

DOCS = Path("docs")


@pytest.mark.skipif(
    not (DOCS / "dnp3_template.xlsx").exists(), reason="template ausente"
)
def test_gerar_tdt_de_lista_vazia_nao_quebra():
    lp = ListaPadraoADMS.carregar(DOCS / "Pontos Padrao ADMS_v1.xlsx")
    wb = pipeline.gerar_tdt([], DOCS / "dnp3_template.xlsx", lp, subestacao=None)
    assert wb is not None


@pytest.mark.skipif(
    not (DOCS / "dnp3_template.xlsx").exists(), reason="template ausente"
)
def test_gerar_tdt_signal_alias_vem_da_v1():
    lp = ListaPadraoADMS.carregar(DOCS / "Pontos Padrao ADMS_v2.xlsx")
    rec = SignalRecord(
        id="LT3:1",
        modulo=Modulo("3", "sheet"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", (17,)),
        descricoes=Descricoes("ALARME TEMP ENROLAMENTO DO CLIENTE", "ALARME TEMP"),
        sigla_sinal="TEA",
        status="decidido",
    )
    wb = pipeline.gerar_tdt([rec], DOCS / "dnp3_template.xlsx", lp, subestacao="IMA")
    ws = wb["DNP3_DiscreteSignals"]
    col = {ws.cell(4, c).value: c for c in range(1, ws.max_column + 1)}
    # descrição original da v1, não a do cliente
    assert ws.cell(5, col["Signal Alias"]).value == "49 - ALARME TEMPERATURA ENROLAMENTO"
