"""Tela Geração (etapa 3): resumo, avisos acionáveis, gera TDT + auditoria.

ponytail: carregar() reconstrói tudo do zero a cada navegação; sem cache.
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QMessageBox,
    QPushButton, QVBoxLayout, QWidget,
)

from tdt.auditoria import Auditoria
from tdt.contracts import ItemRevisao
from tdt.nomes_saida import nome_saida
from tdt.relatorio_revisao import gerar_relatorio_revisao
from tdt.ui.estado import AppState


def enderecos_duplicados(registros) -> dict[tuple[str, int], list[str]]:
    """(direcao, indice) -> ids dos registros que repetem o índice.

    "in" cobre enderecamento.indices; "out" cobre indices_saida. Direções
    não se misturam (input 14 + output 14 não é duplicata).
    """
    por_chave: dict[tuple[str, int], list[str]] = {}
    for r in registros:
        for i in r.enderecamento.indices:
            por_chave.setdefault(("in", i), []).append(r.id)
        for i in r.enderecamento.indices_saida:
            por_chave.setdefault(("out", i), []).append(r.id)
    return {k: v for k, v in por_chave.items() if len(v) > 1}


class TelaGeracao(QWidget):
    rever_pendentes = Signal()
    rever_duplicados = Signal(list)

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado

        self.lbl_titulo = QLabel("Geração")

        self._cards: dict[str, QLabel] = {}
        grid = QGridLayout()
        for i, (chave, nome) in enumerate([
            ("total", "Total"), ("decididos", "Decididos"),
            ("pendentes", "Pendentes"), ("taxa", "Taxa de decisão"),
        ]):
            lbl_val = QLabel("—")
            lbl_val.setStyleSheet("font-size: 18pt; font-weight: bold;")
            grid.addWidget(QLabel(nome), 0, i, Qt.AlignCenter)
            grid.addWidget(lbl_val, 1, i, Qt.AlignCenter)
            self._cards[chave] = lbl_val
        grupo_resumo = QGroupBox("Resumo")
        grupo_resumo.setLayout(grid)

        self._avisos_box = QVBoxLayout()
        grupo_avisos = QGroupBox("Avisos")
        grupo_avisos.setLayout(self._avisos_box)

        self.lbl_saida = QLabel("")
        self.lbl_saida.setWordWrap(True)
        btn_trocar = QPushButton("Trocar pasta…")
        btn_trocar.clicked.connect(self._trocar_saida)
        linha_saida = QHBoxLayout()
        linha_saida.addWidget(self.lbl_saida, 1)
        linha_saida.addWidget(btn_trocar)
        grupo_saida = QGroupBox("Arquivos de saída")
        grupo_saida.setLayout(linha_saida)

        self.btn_gerar = QPushButton("Gerar TDT")
        self.btn_gerar.setProperty("acao", "principal")
        self.btn_gerar.clicked.connect(self._gerar)
        self.btn_abrir_pasta = QPushButton("Abrir pasta")
        self.btn_abrir_pasta.clicked.connect(self._abrir_pasta)
        self.btn_abrir_pasta.setVisible(False)

        self.lbl_resultado = QLabel("")
        self.lbl_resultado.setProperty("nivel", "ok")
        self.lbl_resultado.setWordWrap(True)
        self.lbl_resultado.setVisible(False)

        raiz = QVBoxLayout(self)
        raiz.addWidget(self.lbl_titulo)
        raiz.addWidget(grupo_resumo)
        raiz.addWidget(grupo_avisos)
        raiz.addWidget(grupo_saida)
        linha_gerar = QHBoxLayout()
        linha_gerar.addWidget(self.btn_gerar)
        linha_gerar.addWidget(self.btn_abrir_pasta)
        linha_gerar.addStretch()
        raiz.addLayout(linha_gerar)
        raiz.addWidget(self.lbl_resultado)
        raiz.addStretch()

    def carregar(self) -> None:
        regs = self._estado.registros
        total = len(regs)
        pendentes = sum(1 for r in regs if r.status == "revisao")
        decididos = sum(1 for r in regs if r.status == "decidido")
        taxa = f"{decididos / total * 100:.0f}%" if total else "—"
        self.lbl_titulo.setText(f"Geração — {self._estado.subestacao or '—'}")
        self._cards["total"].setText(str(total))
        self._cards["decididos"].setText(str(decididos))
        self._cards["pendentes"].setText(str(pendentes))
        self._cards["taxa"].setText(taxa)
        pend_lbl = self._cards["pendentes"]
        pend_lbl.setProperty("nivel", "aviso" if pendentes else "ok")
        pend_lbl.style().unpolish(pend_lbl)
        pend_lbl.style().polish(pend_lbl)
        self._montar_avisos(pendentes)
        out = self._estado.paths.get("output", "")
        self.lbl_saida.setText(f"TDT + Auditoria → {out or '—'}")
        self.lbl_resultado.setVisible(False)
        self.btn_abrir_pasta.setVisible(False)

    def _montar_avisos(self, pendentes: int) -> None:
        while self._avisos_box.count():
            w = self._avisos_box.takeAt(0).widget()
            if w is not None:
                w.deleteLater()
        dups = enderecos_duplicados(self._estado.registros)
        if pendentes:
            self._avisos_box.addWidget(self._aviso(
                "aviso",
                f"{pendentes} sinais pendentes serão exportados com o melhor "
                "candidato atual",
                "Rever pendentes →", self.rever_pendentes.emit))
        if dups:
            indices = sorted({i for (_d, i) in dups})
            resumo = "; ".join(str(i) for i in indices[:5])
            self._avisos_box.addWidget(self._aviso(
                "erro",
                f"{len(dups)} endereços duplicados (índices {resumo})",
                "Rever duplicados →",
                lambda: self.rever_duplicados.emit(indices)))
        if not pendentes and not dups:
            self._avisos_box.addWidget(self._aviso(
                "ok", "Tudo pronto — sem pendências nem endereços duplicados",
                None, None))

    def _aviso(self, nivel: str, texto: str, rotulo_botao, slot) -> QWidget:
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(texto)
        lbl.setProperty("nivel", nivel)
        lbl.setWordWrap(True)
        lay.addWidget(lbl, 1)
        if rotulo_botao:
            btn = QPushButton(rotulo_botao)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
        return w

    def _trocar_saida(self) -> None:
        atual = self._estado.paths.get("output", "")
        caminho = QFileDialog.getExistingDirectory(
            self, "Pasta de saída", dir=atual)
        if caminho:
            self._estado.paths["output"] = caminho
            self.carregar()

    def _confirmar(self, titulo: str, texto: str) -> bool:
        resp = QMessageBox.question(self, titulo, texto)
        return resp == QMessageBox.StandardButton.Yes

    def _gerar(self) -> None:
        lp = self._estado.lista_padrao
        template = self._estado.paths.get("template", "")
        output = self._estado.paths.get("output", "")
        if not lp or not template or not output:
            QMessageBox.warning(
                self, "Erro", "Lista padrão, template e output são obrigatórios")
            return
        pendentes = sum(
            1 for r in self._estado.registros if r.status == "revisao")
        if pendentes and not self._confirmar(
                "Pendências", f"Gerar com {pendentes} sinais ainda pendentes?"):
            return
        out_path = nome_saida("TDT", self._estado.subestacao, output)
        if out_path.exists() and not self._confirmar(
                "Sobrescrever", f"{out_path} já existe. Sobrescrever?"):
            return
        try:
            from tdt import pipeline
            aud = Auditoria()
            wb = pipeline.gerar_tdt(
                self._estado.registros, template, lp,
                subestacao=self._estado.subestacao,
                aliases=self._estado.aliases,
                auditoria=aud,
            )
            wb.save(str(out_path))
            revisao = list(self._estado.resultado.revisao
                           if self._estado.resultado else ())
            diag = (self._estado.resultado.diagnostico
                    if self._estado.resultado else {})
            # ponytail: só gerar_tdt() emite AVISO com dados["ids"] hoje (gate de
            # Custom ID duplicado); se outro evento futuro reusar essa chave com
            # motivo diferente, isto precisa distinguir por `ev.modulo`/msg.
            por_id = {r.id: r for r in self._estado.registros}
            for ev in aud.eventos:
                dup_ids = (ev.dados or {}).get("ids", ()) if ev.nivel == "AVISO" else ()
                revisao.extend(
                    ItemRevisao(por_id[i], motivo="custom_id_duplicado")
                    for i in dup_ids if i in por_id)
            aud_path = gerar_relatorio_revisao(
                self._estado.registros, revisao, output, diagnostico=diag,
                subestacao=self._estado.subestacao)
            self.lbl_resultado.setText(
                f"TDT gerado:\n{out_path}\n{aud_path}")
            self.lbl_resultado.setVisible(True)
            self.btn_abrir_pasta.setVisible(True)
        except Exception as e:  # ponytail: erro vira dialogo; sem retry
            QMessageBox.critical(self, "Erro", f"Falha ao gerar TDT: {e}")

    def _abrir_pasta(self) -> None:
        output = self._estado.paths.get("output", "")
        if output and hasattr(os, "startfile"):
            os.startfile(output)
