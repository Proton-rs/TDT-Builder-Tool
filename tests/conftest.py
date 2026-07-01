import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

DOCS = Path(__file__).resolve().parents[1] / "docs"


@pytest.fixture
def docs():
    return DOCS


@pytest.fixture
def lista_padrao_path():
    return DOCS / "Pontos Padrao ADMS_v2.xlsx"


@pytest.fixture
def template_dnp3_path():
    return DOCS / "dnp3_template.xlsx"


@pytest.fixture
def input_homogeneo_path():
    return DOCS / "input_homogeneo_IMA.xlsx"
