"""Entry-point: python -m tdt.ui_main  (ou console_script 'tdt-ui').

Carrega config.toml, monta AppState, abre a janela.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from tdt.config import Config
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.defaults import DEFAULT_LISTA as _DEFAULT_LISTA
from tdt.defaults import DEFAULT_OUTPUT as _DEFAULT_OUTPUT
from tdt.defaults import DEFAULT_TEMPLATE as _DEFAULT_TEMPLATE
from tdt.ui.app import MainWindow
from tdt.ui.config_io import carregar_config
from tdt.ui.estado import AppState

_CONFIG_PATH = Path("config.toml")


def main():
    app = QApplication(sys.argv)

    cfg, paths = carregar_config(_CONFIG_PATH)
    paths.setdefault("template", _DEFAULT_TEMPLATE)
    paths.setdefault("lista_padrao", _DEFAULT_LISTA)
    paths.setdefault("output", _DEFAULT_OUTPUT)
    estado = AppState(config=cfg, paths=paths)

    # Carrega a lista padrão (síncrono; barato — o encoder pesado só carrega
    # quando roda análise)
    lp_path = paths.get("lista_padrao", "")
    if lp_path and Path(lp_path).exists():
        try:
            estado.lista_padrao = ListaPadraoADMS.carregar(lp_path)
        except Exception:
            pass

    win = MainWindow(estado, config_path=_CONFIG_PATH)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
