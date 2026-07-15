"""Editor inline da célula 'Sinal': combo com candidatos + busca ADMS.

ponytail: combo editável; itens = candidatos da linha + siglas ADMS. setModelData
delega ao ModeloSinais.definir_sigla (mesma rota do painel).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QStyledItemDelegate

from tdt.ui.busca_adms import buscar
from tdt.ui.estado import AppState


def _preselecionar(editor: QComboBox, valor) -> None:
    """Sincroniza o combo com o valor atual da célula ao abrir o editor.

    "—" é o sentinela de exibição p/ campo vazio (ver modelo_tabela._texto);
    mapeia p/ a opção vazia "". Em combo não-editável (DelegateCombo),
    setCurrentText só muda a seleção se o texto for uma opção existente —
    sem match, o Qt não altera a seleção (comportamento padrão do widget).
    """
    texto = "" if valor in (None, "—") else str(valor)
    editor.setCurrentText(texto)


class DelegateSinal(QStyledItemDelegate):
    def __init__(self, estado: AppState, modelo, proxy, parent=None):
        super().__init__(parent)
        self._estado = estado
        self._modelo = modelo
        self._proxy = proxy

    def createEditor(self, parent, option, index):
        fonte = self._proxy.mapToSource(index)
        combo = QComboBox(parent)
        combo.setEditable(True)
        siglas: list[str] = []
        rec = self._estado.registros[fonte.row()] if fonte.isValid() else None
        if rec is not None:
            siglas.extend(c.sigla for c in rec.candidatos)
        lp = self._estado.lista_padrao
        if lp is not None:
            for sp in buscar(lp, "", limite=500):
                if sp.sigla not in siglas:
                    siglas.append(sp.sigla)
        combo.addItems(siglas)
        return combo

    def setModelData(self, editor, model, index):
        fonte = self._proxy.mapToSource(index)
        sigla = editor.currentText().strip()
        if sigla:
            self._modelo.definir_sigla(fonte.row(), sigla)


class DelegateCombo(QStyledItemDelegate):
    """Editor combo p/ colunas de domínio fechado (Tipo/Fase/Nível Tensão/
    Barra/Tipo Equip.). Sempre não-editável — só os valores fixos passados.
    """

    def __init__(self, opcoes: list[str], parent=None):
        super().__init__(parent)
        self._opcoes = opcoes

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItems(self._opcoes)
        return combo

    def setEditorData(self, editor, index):
        _preselecionar(editor, index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)


class DelegateModulo(QStyledItemDelegate):
    """Editor combo editável p/ Módulo: sugere nomes já presentes nos
    registros, aceita texto livre (módulo novo).
    """

    def __init__(self, estado: AppState, parent=None):
        super().__init__(parent)
        self._estado = estado

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        modulos = sorted({
            r.modulo.nome for r in self._estado.registros
            if r.modulo and r.modulo.nome
        })
        combo.addItems(modulos)
        return combo

    def setEditorData(self, editor, index):
        _preselecionar(editor, index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)


class DelegateEquipamento(QStyledItemDelegate):
    """Editor combo editável p/ Equipamento (ID): sugere os IDs já presentes
    em registros do MESMO módulo, aceita texto livre; opção vazia limpa
    (spec 2026-07-15 §4). Caso alvo: corrigir 81-1 -> 52-11 na revisão.
    """

    def __init__(self, estado: AppState, proxy, parent=None):
        super().__init__(parent)
        self._estado = estado
        self._proxy = proxy

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(True)
        fonte = self._proxy.mapToSource(index)
        modulo = None
        if fonte.isValid():
            rec = self._estado.registros[fonte.row()]
            modulo = rec.modulo.nome if rec.modulo else None
        ids = sorted({
            r.eletrico.nome_equipamento for r in self._estado.registros
            if r.eletrico.nome_equipamento
            and (r.modulo.nome if r.modulo else None) == modulo
        })
        combo.addItems([""] + ids)
        return combo

    def setEditorData(self, editor, index):
        _preselecionar(editor, index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText().strip(), Qt.EditRole)
