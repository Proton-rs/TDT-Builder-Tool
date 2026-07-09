"""Boot da UI nao pode importar sentence_transformers/transformers (custa ~16s).
Regressao do lazy-load do encoder (SP-Pendencias-09jul Task 9)."""
import subprocess
import sys


def test_importar_ui_app_nao_puxa_transformers():
    code = (
        "import sys; import tdt.ui.app; "
        "pesados = sorted(m for m in sys.modules "
        "if m in ('transformers', 'sentence_transformers', 'sklearn')); "
        "assert not pesados, pesados"
    )
    r = subprocess.run(
        [sys.executable, "-c", code],
        cwd="src", capture_output=True, text=True,
    )
    assert r.returncode == 0, f"boot puxou modulos pesados:\nSTDOUT={r.stdout}\nSTDERR={r.stderr}"
