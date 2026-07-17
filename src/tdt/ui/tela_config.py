"""Tela de Configurações: pastas, thresholds, pesos, modelo. Persiste em TOML.

ponytail: form direto com widgets nomeados; sem binding genérico.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout,
    QLabel, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)
from PySide6.QtCore import Signal

from tdt.config import Config
from tdt.defaults import DEFAULT_LISTA, DEFAULT_OUTPUT, DEFAULT_TEMPLATE
from tdt.ui.config_io import salvar_config
from tdt.ui.estado import AppState

_MODELOS = [
    "paraphrase-multilingual-MiniLM-L12-v2",
    "intfloat/multilingual-e5-base",
]

_TOOLTIPS = {
    "threshold_pct": ("Score mínimo para decidir sozinho",
                      "Candidato nº 1 precisa de pelo menos este score. "
                      "Maior = decide mais sozinho, mais risco de erro."),
    "threshold_gap": ("Vantagem mínima sobre o 2º",
                      "Diferença mínima entre 1º e 2º candidato. Maior = só "
                      "decide quando a liderança é clara."),
    "top_n_pct": ("Corte dos candidatos exibidos",
                  "Score mínimo (relativo ao 1º) para um candidato aparecer "
                  "na lista da revisão."),
    "peso_tfidf": ("Peso do TF-IDF/BM25",
                   "Peso do método lexical na mescla dos scores."),
    "peso_vetorial": ("Peso do embedding",
                      "Peso do método semântico (vetorial) na mescla."),
    "peso_fuzzy": ("Peso do fuzzy",
                   "Peso da similaridade de caracteres na mescla."),
    "modelo_embedding": ("Modelo de embedding",
                         "Modelo sentence-transformers usado no método "
                         "vetorial. Trocar exige novo download/cache."),
    "k_vizinhos": ("Candidatos por sinal (k)",
                   "Quantos vizinhos o índice vetorial devolve por sinal."),
}


def _rotulo(chave: str) -> QWidget:
    humano, tooltip = _TOOLTIPS[chave]
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    lbl = QLabel(humano)
    tec = QLabel(chave)
    tec.setProperty("tipo", "tecnico")
    v.addWidget(lbl)
    v.addWidget(tec)
    w.setToolTip(tooltip)
    return w


def _spin(maximo=1.0, passo=0.01):
    s = QDoubleSpinBox()
    s.setRange(0.0, maximo)
    s.setSingleStep(passo)
    s.setDecimals(3)
    s.setFixedWidth(120)
    return s


_KNOBS_UI = (
    ("threshold_pct", "spin_pct"), ("threshold_gap", "spin_gap"),
    ("top_n_pct", "spin_topn"), ("peso_tfidf", "spin_tfidf"),
    ("peso_vetorial", "spin_vet"), ("peso_fuzzy", "spin_fuzzy"),
)


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

        layout = QVBoxLayout(self)

        # Grupo 1: Caminhos padrão
        group_caminhos = QGroupBox("Caminhos padrão")
        form_caminhos = QFormLayout(group_caminhos)
        form_caminhos.setVerticalSpacing(6)
        self._setup_paths(form_caminhos)
        layout.addWidget(group_caminhos)

        # Grupo 2: Decisão automática
        group_decisao = QGroupBox("Decisão automática")
        form_decisao = QFormLayout(group_decisao)
        form_decisao.setVerticalSpacing(6)
        self.spin_pct = _spin()
        self.spin_pct.setToolTip(_TOOLTIPS["threshold_pct"][1])
        self.spin_gap = _spin()
        self.spin_gap.setToolTip(_TOOLTIPS["threshold_gap"][1])
        self.spin_topn = _spin()
        self.spin_topn.setToolTip(_TOOLTIPS["top_n_pct"][1])
        form_decisao.addRow(_rotulo("threshold_pct"), self.spin_pct)
        form_decisao.addRow(_rotulo("threshold_gap"), self.spin_gap)
        form_decisao.addRow(_rotulo("top_n_pct"), self.spin_topn)
        layout.addWidget(group_decisao)

        # Grupo 3: Pesos do ensemble
        group_pesos = QGroupBox("Pesos do ensemble")
        form_pesos = QFormLayout(group_pesos)
        form_pesos.setVerticalSpacing(6)
        self.spin_tfidf = _spin()
        self.spin_tfidf.setToolTip(_TOOLTIPS["peso_tfidf"][1])
        self.spin_vet = _spin()
        self.spin_vet.setToolTip(_TOOLTIPS["peso_vetorial"][1])
        self.spin_fuzzy = _spin()
        self.spin_fuzzy.setToolTip(_TOOLTIPS["peso_fuzzy"][1])
        form_pesos.addRow(_rotulo("peso_tfidf"), self.spin_tfidf)
        form_pesos.addRow(_rotulo("peso_vetorial"), self.spin_vet)
        form_pesos.addRow(_rotulo("peso_fuzzy"), self.spin_fuzzy)
        self.lbl_aviso_pesos = QLabel("")
        self.lbl_aviso_pesos.setProperty("nivel", "aviso")
        self.lbl_aviso_pesos.setVisible(False)
        form_pesos.addRow(self.lbl_aviso_pesos)
        for spin in (self.spin_tfidf, self.spin_vet, self.spin_fuzzy):
            spin.valueChanged.connect(self._atualizar_aviso_pesos)
        layout.addWidget(group_pesos)

        self.lbl_overrides = QLabel("")
        self.lbl_overrides.setProperty("nivel", "aviso")
        layout.addWidget(self.lbl_overrides)
        for _campo, _nome_spin in _KNOBS_UI:
            getattr(self, _nome_spin).valueChanged.connect(self._atualizar_overrides)

        # Grupo 4: Modelo semântico
        group_modelo = QGroupBox("Modelo semântico")
        form_modelo = QFormLayout(group_modelo)
        form_modelo.setVerticalSpacing(6)
        self.combo_modelo = QComboBox()
        self.combo_modelo.addItems(_MODELOS)
        self.combo_modelo.setToolTip(_TOOLTIPS["modelo_embedding"][1])
        self.spin_k = QSpinBox()
        self.spin_k.setRange(1, 50)
        self.spin_k.setFixedWidth(120)
        self.spin_k.setToolTip(_TOOLTIPS["k_vizinhos"][1])
        form_modelo.addRow(_rotulo("modelo_embedding"), self.combo_modelo)
        form_modelo.addRow(_rotulo("k_vizinhos"), self.spin_k)
        layout.addWidget(group_modelo)

        # Botões
        btn_salvar = QPushButton("Salvar")
        btn_salvar.setProperty("acao", "principal")
        btn_salvar.clicked.connect(self.aplicar)
        btn_restaurar = QPushButton("Restaurar padrões")
        btn_restaurar.clicked.connect(self._restaurar_padroes)
        btn_voltar = QPushButton("Voltar")
        btn_voltar.clicked.connect(self.voltar.emit)

        h_botoes = QHBoxLayout()
        h_botoes.addWidget(btn_salvar)
        h_botoes.addWidget(btn_restaurar)
        h_botoes.addWidget(btn_voltar)
        layout.addLayout(h_botoes)

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
            salvar_config(self._config_path, self._estado.config, self._estado.paths)  # persiste path, sem revalidar pesos

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
        self._atualizar_aviso_pesos()
        self._atualizar_overrides()

    def _atualizar_aviso_pesos(self, *_args) -> None:
        soma = (self.spin_tfidf.value() + self.spin_vet.value()
                + self.spin_fuzzy.value())
        divergente = abs(soma - 1.0) > 0.001
        if divergente:
            self.lbl_aviso_pesos.setText(
                f"Os pesos somam {soma:.3f} — o esperado é 1.0")
        self.lbl_aviso_pesos.setVisible(divergente)

    def _atualizar_overrides(self, *_args) -> None:
        default = Config()
        difs = [
            f"{campo} ({getattr(self, spin).value():g} ≠ padrão {getattr(default, campo):g})"
            for campo, spin in _KNOBS_UI
            if abs(getattr(self, spin).value() - getattr(default, campo)) > 1e-9
        ]
        self.lbl_overrides.setText(
            "Valores diferentes do padrão calibrado: " + "; ".join(difs) if difs else "")
        self.lbl_overrides.setVisible(bool(difs))

    def _restaurar_padroes(self) -> None:
        c = Config()
        self.spin_pct.setValue(c.threshold_pct)
        self.spin_gap.setValue(c.threshold_gap)
        self.spin_topn.setValue(c.top_n_pct)
        self.spin_tfidf.setValue(c.peso_tfidf)
        self.spin_vet.setValue(c.peso_vetorial)
        self.spin_fuzzy.setValue(c.peso_fuzzy)
        indice = self.combo_modelo.findText(c.modelo_embedding)
        self.combo_modelo.setCurrentIndex(indice if indice >= 0 else 0)
        self.spin_k.setValue(c.k_vizinhos)

    def aplicar(self) -> None:
        soma = self.spin_tfidf.value() + self.spin_vet.value() + self.spin_fuzzy.value()
        if abs(soma - 1.0) > 0.001:
            QMessageBox.warning(self, "Pesos do ensemble",
                                 f"Os pesos somam {soma:.3f} — ajuste para 1.0 antes de salvar.")
            return
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
