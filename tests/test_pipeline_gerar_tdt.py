from pathlib import Path
import pytest
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt import pipeline

DOCS = Path("docs")


@pytest.mark.skipif(
    not (DOCS / "dnp3_template.xlsx").exists(), reason="template ausente"
)
def test_gerar_tdt_de_lista_vazia_nao_quebra():
    lp = ListaPadraoADMS.carregar(DOCS / "Pontos Padrao ADMS_v1.xlsx")
    wb = pipeline.gerar_tdt([], DOCS / "dnp3_template.xlsx", lp, subestacao=None)
    assert wb is not None
