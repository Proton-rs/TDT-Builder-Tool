"""Tela de Configurações: pastas, thresholds, pesos, modelo. Persiste em TOML.

ponytail: form direto com widgets nomeados; sem binding genérico.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout,
    QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Signal

from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT, DEFAULT_TEMPLATE
from tdt.ui.config_io import salvar_config
from tdt.ui.estado import AppState

_MODELOS = [
    "paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-base",
]


def _spin(maximo=1.0, passo=0.01):
    s = QDoubleSpinBox()
    s.setRange(0.0, maximo)
    s.setSingleStep(passo)
    s.setDecimals(3)
    s.setFixedWidth(120)
    return s


def _linha_caminho(rotulo: str, valor: str, seletor: str, is_pasta: bool = False) -> tuple:
    """Cria linha com label + label do caminho + botão de explorar."""
    lbl_valor = QLabel(valor or "—")
    lbl_valor.setWordWrap(True)
    if is_pasta:
        btn = QPushButton("Pasta…")
    else:
        btn = QPushButton("Arquivo…")
    linha = QHBoxLayout()
    linha.addWidget(lbl_valor, 1)
    linha.addWidget(btn)
    return lbl_valor, btn, linha


class TelaConfig(QWidget):
    voltar = Signal()

    def __init__(self, estado: AppState, config_path="config.toml"):
        super().__init__()
        self._estado = estado
        self._config_path = Path(config_path)
        form = QFormLayout()
        form.setVerticalSpacing(6)

        self._setup_paths(form)

        self.spin_pct = _spin()
        self.spin_gap = _spin()
        self.spin_topn = _spin()
        form.addRow("threshold_pct", self.spin_pct)
        form.addRow("threshold_gap", self.spin_gap)
        form.addRow("top_n_pct", self.spin_topn)

        self.spin_tfidf = _spin()
        self.spin_vet = _spin()
        self.spin_fuzzy = _spin()
        form.addRow("peso_tfidf", self.spin_tfidf)
        form.addRow("peso_vetorial", self.spin_vet)
        form.addRow("peso_fuzzy", self.spin_fuzzy)

        self.combo_modelo = QComboBox()
        self.combo_modelo.addItems(_MODELOS)
        self.spin_k = QSpinBox()
        self.spin_k.setRange(1, 50)
        self.spin_k.setFixedWidth(120)
        form.addRow("modelo_embedding", self.combo_modelo)
        form.addRow("k_vizinhos", self.spin_k)

        btn_salvar = QPushButton("Salvar")
        btn_salvar.setProperty("acao", "principal")
        btn_salvar.clicked.connect(self.aplicar)
        btn_voltar = QPushButton("Voltar")
        btn_voltar.clicked.connect(self.voltar.emit)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(btn_salvar)
        layout.addWidget(btn_voltar)
        self.recarregar()

    def _setup_paths(self, form):
        self.lbl_input = QLabel("—")
        self.lbl_input.setWordWrap(True)
        btn_input = QPushButton("Arquivo…")
        btn_input.clicked.connect(lambda: self._escolher("input", False))
        h = QHBoxLayout(); h.addWidget(self.lbl_input, 1); h.addWidget(btn_input)
        form.addRow("Input padrão", h)

        self.lbl_output = QLabel("—")
        btn_output = QPushButton("Pasta…")
        btn_output.clicked.connect(lambda: self._escolher("output", True))
        h = QHBoxLayout(); h.addWidget(self.lbl_output, 1); h.addWidget(btn_output)
        form.addRow("Output padrão", h)

        self.lbl_template = QLabel("—")
        btn_template = QPushButton("Arquivo…")
        btn_template.clicked.connect(lambda: self._escolher("template", False))
        h = QHBoxLayout(); h.addWidget(self.lbl_template, 1); h.addWidget(btn_template)
        form.addRow("Template DNP3", h)

        self.lbl_lista = QLabel("—")
        btn_lista = QPushButton("Arquivo…")
        btn_lista.clicked.connect(lambda: self._escolher("lista_padrao", False))
        h = QHBoxLayout(); h.addWidget(self.lbl_lista, 1); h.addWidget(btn_lista)
        form.addRow("Lista Padrão ADMS", h)

    def _escolher(self, chave, is_pasta):
        atual = self._estado.paths.get(chave, "")
        default = {
            "template": DEFAULT_TEMPLATE, "lista_padrao": DEFAULT_LISTA, "output": DEFAULT_OUTPUT,
        }.get(chave, "")
        inicial = atual or default
        if is_pasta:
            caminho = QFileDialog.getExistingDirectory(self, f"Selecionar pasta {chave}", dir=inicial)
        else:
            caminho, _ = QFileDialog.getOpenFileName(
                self, f"Selecionar {chave}", dir=inicial,
                filter="Excel (*.xlsx);;Todos (*)",
            )
        if caminho:
            self._estado.paths[chave] = caminho
            self._atualizar_label(chave)
            self.aplicar()  # persiste imediatamente

    def _atualizar_label(self, chave):
        v = self._estado.paths.get(chave, "")
        lbl = {"input": self.lbl_input, "output": self.lbl_output,
               "template": self.lbl_template, "lista_padrao": self.lbl_lista}.get(chave)
        if lbl:
            lbl.setText(v or "—")

    def recarregar(self) -> None:
        c, p = self._estado.config, self._estado.paths
        self._atualizar_label("input")
        self._atualizar_label("output")
        self._atualizar_label("template")
        self._atualizar_label("lista_padrao")
        self.spin_pct.setValue(c.threshold_pct)
        self.spin_gap.setValue(c.threshold_gap)
        self.spin_topn.setValue(c.top_n_pct)
        self.spin_tfidf.setValue(c.peso_tfidf)
        self.spin_vet.setValue(c.peso_vetorial)
        self.spin_fuzzy.setValue(c.peso_fuzzy)
        i = self.combo_modelo.findText(c.modelo_embedding)
        self.combo_modelo.setCurrentIndex(i if i >= 0 else 0)
        self.spin_k.setValue(c.k_vizinhos)

    def aplicar(self) -> None:
        self._estado.config = replace(
            self._estado.config,
            threshold_pct=self.spin_pct.value(),
            threshold_gap=self.spin_gap.value(),
            top_n_pct=self.spin_topn.value(),
            peso_tfidf=self.spin_tfidf.value(),
            peso_vetorial=self.spin_vet.value(),
            peso_fuzzy=self.spin_fuzzy.value(),
            modelo_embedding=self.combo_modelo.currentText(),
            k_vizinhos=self.spin_k.value(),
        )
        salvar_config(self._config_path, self._estado.config, self._estado.paths)
