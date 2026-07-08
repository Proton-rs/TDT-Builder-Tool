from pathlib import Path
import pytest
from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.dados.encoder import criar_encoder
from tdt import pipeline

DOCS = Path("docs")


@pytest.mark.skipif(
    not (DOCS / "input_nao_homogeneo_1_GTA.xlsx").exists(),
    reason="fixture de input ausente",
)
def test_cancelamento_para_cedo():
    aud = Auditoria()
    resultado, _wb = pipeline.executar(
        DOCS / "input_nao_homogeneo_1_GTA.xlsx",
        DOCS / "dnp3_template.xlsx",
        DOCS / "Pontos Padrao ADMS_v1.xlsx",
        config=Config(),
        encoder=criar_encoder(Config().modelo_embedding),
        cancelado=lambda: True,  # cancela imediatamente
        auditoria=aud,
    )
    assert len(resultado.lista.registros) == 0
    assert any("cancelado" in e.msg.lower() for e in aud.eventos)
