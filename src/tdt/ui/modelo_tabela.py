"""Modelo de tabela sobre os SignalRecords (decididos + revisão).

ponytail: model fino que lê do AppState; sem cache, relê o registro a cada data().
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor, QFont

from tdt.contracts import SignalRecord
from tdt.ui.estado import AppState

COLUNAS = [
    "Sinal", "Confiança", "Status", "Motivo", "Descr. ADMS", "Descr. bruta",
    "Descr. normalizada", "Tokens", "Tipo", "Escala", "Fase", "Endereço",
    "Endereço Output",
    "Score embedding", "Score tf-idf", "Score fuzzy", "Justificativa",
    "Módulo", "Equipamento", "Tipo Equip.", "Barra", "Nível Tensão",
    "Pareado", "Sheet origem",
]

_MOTIVO_LABEL = {
    "sem_endereco": "Sem endereço",
    "score_baixo": "Score baixo",
    "categoria_ambigua": "Categoria ambígua",
    "categoria_incompativel": "Categoria incompatível",
    "endereco_duplicado": "Endereço duplicado",
    "sem_fix": "Sem correção automática",
    "modulo_indefinido": "Módulo indefinido",
    "equipamento_ambiguo": "Equipamento ambíguo",
    "nome_sigla_inconsistente": "Sigla ≠ NOME",
    "qualificador_ambiguo": "Qualificador ambíguo",
    "pareamento_ambiguo": "Comando sem par claro",
    "comando_sem_discreto": "Comando sem status",
    "custom_id_duplicado": "Custom ID duplicado",
    "equipamento_conflitante": "Equipamentos conflitantes na linha",
    "modulo_duplicado_entre_sheets": "Módulo duplicado entre sheets",
    "posicao_ambigua": "Posição sem palavra-chave",
    "estado_sem_candidato": "Estado sem candidato",
    "comando_tap_nao_modelado": "Comando de TAP (não vira ponto)",
    "decisao_por_projeto": "Decisão por projeto",
    "descartado_indefinido": "Descartado (indefinido)",
    "descartado_redundante": "Descartado (redundante)",
    "posicao_divergente": "Posição diverge do status",
}

_MOTIVO_TOOLTIP = {
    "sem_endereco": "Sinal sem endereço mapeado. Confirme o endereço ou descarte a linha.",
    "score_baixo": "Nenhum candidato bateu confiança mínima. Revise a descrição ou escolha a sigla manualmente.",
    "categoria_ambigua": "Sinal decidiu tanto como Discrete quanto Analog. Escolha a categoria correta.",
    "categoria_incompativel": "Só decidiu fora da categoria admitida pra esse tipo de sinal. Revise o tipo ou a sigla.",
    "endereco_duplicado": "Mesmo endereço usado por mais de um sinal. Corrija o endereçamento.",
    "sem_fix": "Não há correção automática aplicável. Ajuste manualmente.",
    "modulo_indefinido": "Sinal sem módulo identificado. Informe o módulo.",
    "equipamento_ambiguo": "Mais de um equipamento candidato pro sinal. Escolha o equipamento correto.",
    "nome_sigla_inconsistente": "Sigla da coluna diverge do NOME do sinal. Confirme qual prevalece.",
    "qualificador_ambiguo": "Qualificador (fase/estado/etc.) não ficou claro na descrição. Complete manualmente.",
    "pareamento_ambiguo": "Comando sem discreto correspondente claro pro par D+C. Revise o pareamento.",
    "comando_sem_discreto": "Comando identificado sem status (discreto) associado. Verifique se falta o par.",
    "custom_id_duplicado": "Custom ID já usado por outro sinal. Corrija a duplicidade.",
    "equipamento_conflitante": "A linha de origem cita dois equipamentos distintos (ex. 52-11 e 89-1). Confirme a qual equipamento o sinal pertence e ajuste.",
    "modulo_duplicado_entre_sheets": "Sinais idênticos vieram de sheets de origem distintas — o módulo pode estar nomeado errado na planilha de origem. Verifique/corrija o módulo.",
    "posicao_ambigua": "Não achou palavra-chave de posição (aberto/fechado) na descrição. Informe manualmente.",
    "estado_sem_candidato": "Nenhum candidato de estado bateu com a descrição. Escolha manualmente.",
    "comando_tap_nao_modelado": "Comando de TAP não vira ponto no modelo atual. Nenhuma ação necessária, apenas ciente.",
    "decisao_por_projeto": "Sigla marcada como revisão obrigatória por decisão de projeto.",
    "descartado_indefinido": "Linha descartada por falta de dados suficientes pra decidir.",
    "descartado_redundante": "Linha descartada por ser redundante com outra já processada.",
    "posicao_divergente": "Comando de posição com sigla diferente do status do mesmo equipamento, e o status é ambíguo (mais de uma sigla de posição). Escolha a sigla correta e paree manualmente.",
}

# Cores por faixa de confiança (texto). ponytail: faixas fixas; threshold de
# decisão é outra coisa (config).
COR_ALTO = QColor("#35c48f")
COR_MEDIO = QColor("#e0a83f")
COR_BAIXO = QColor("#e0604c")
COR_DECIDIDO = COR_ALTO
COR_REVISAO = COR_BAIXO

# Cor de texto por faixa — necessária pq o fundo (::chunk da QProgressBar)
# muda de cor conforme a faixa, mas o texto era fixo e ficava ilegível
# sobre verde/âmbar claros.
COR_ALTO_TEXTO = QColor("#0d2e21")
COR_MEDIO_TEXTO = QColor("#2c2005")
COR_BAIXO_TEXTO = QColor("#e8ebf2")

_EDITAVEIS = frozenset({
    "Sinal", "Tipo", "Fase", "Nível Tensão", "Barra", "Tipo Equip.",
    "Módulo", "Escala", "Endereço", "Endereço Output",
})

_COLUNAS_MONO = frozenset({
    "Sinal", "Endereço", "Endereço Output", "Tokens",
    "Score embedding", "Score tf-idf", "Score fuzzy",
})


def sheet_origem(rec: SignalRecord) -> str:
    """Sheet de origem, extraída do ``id`` estável (``f"{sheet}:{linha}"``).

    Mesma derivação de `relatorio_revisao._sheet_origem` — `id` já carrega
    essa informação (contrato existente), sem precisar propagar campo novo.
    """
    return rec.id.rsplit(":", 1)[0] if ":" in rec.id else ""


def cor_faixa(score) -> QColor | None:
    if score is None:
        return None
    if score >= 0.70:
        return COR_ALTO
    if score >= 0.45:
        return COR_MEDIO
    return COR_BAIXO


def texto_faixa(score) -> QColor | None:
    if score is None:
        return None
    if score >= 0.70:
        return COR_ALTO_TEXTO
    if score >= 0.45:
        return COR_MEDIO_TEXTO
    return COR_BAIXO_TEXTO


def _score(rec, sigla, metodo):
    diag = rec.diagnostico
    if diag is None or sigla is None:
        return ""
    v = diag.scores_por_metodo.get(sigla, {}).get(metodo)
    return f"{v:.2f}" if v is not None else ""


class ModeloSinais(QAbstractTableModel):
    COLUNAS = COLUNAS

    def __init__(self, estado: AppState):
        super().__init__()
        self._estado = estado
        self.ultima_edicao: tuple[str, object] | None = None

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._estado.registros)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(COLUNAS)

    def headerData(self, secao, orientacao, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientacao == Qt.Horizontal:
            nome = COLUNAS[secao]
            return f"{nome} ✎" if nome in _EDITAVEIS else nome
        return super().headerData(secao, orientacao, role)

    def flags(self, index):
        base = super().flags(index)
        if COLUNAS[index.column()] in _EDITAVEIS:
            return base | Qt.ItemIsEditable
        return base

    def _adms(self, rec):
        lp = self._estado.lista_padrao
        if lp is None or not rec.sigla_sinal:
            return ""
        sp = lp.por_sigla(rec.sigla_sinal)
        return sp.descricao if sp else ""

    def _texto(self, rec, col):
        sigla = rec.sigla_sinal
        topo = rec.candidatos[0].score if rec.candidatos else None
        nome = COLUNAS[col]
        if nome == "Sinal":
            return sigla or "—"
        if nome == "Confiança":
            if topo is not None:
                return f"{topo:.2f}"
            if rec.status == "decidido":
                return "1.00 (regra)"
            return ""
        if nome == "Status":
            return rec.status
        if nome == "Motivo":
            motivo = self._estado.motivo_por_id().get(rec.id)
            return _MOTIVO_LABEL.get(motivo, motivo) if motivo else "—"
        # ponytail: motivo_por_id() reconstroi o dict a cada chamada de _texto
        # -- ok pro tamanho de lista atual (centenas de linhas); cachear no
        # AppState se a tabela ficar lenta com listas grandes.
        if nome == "Descr. ADMS":
            return self._adms(rec) or "—"
        if nome == "Descr. bruta":
            return rec.descricoes.bruta
        if nome == "Descr. normalizada":
            return rec.descricoes.normalizada
        if nome == "Tokens":
            return "·".join(rec.descricoes.normalizada.split())
        if nome == "Tipo":
            t = rec.tipo_sinal
            return f"{t.categoria}/{t.direcao}"
        if nome == "Escala":
            e = rec.grandezas_analogicas.escala_transmissao
            return "" if e is None else str(e)
        if nome == "Fase":
            return rec.eletrico.fase or "—"
        if nome == "Endereço":
            return ";".join(str(i) for i in rec.enderecamento.indices)
        if nome == "Endereço Output":
            return ";".join(str(i) for i in rec.enderecamento.indices_saida) or "—"
        if nome == "Score embedding":
            return _score(rec, sigla, "vetorial")
        if nome == "Score tf-idf":
            return _score(rec, sigla, "tfidf")
        if nome == "Score fuzzy":
            return _score(rec, sigla, "fuzzy")
        if nome == "Justificativa":
            return rec.justificativa or ""
        if nome == "Módulo":
            return (rec.modulo.nome if rec.modulo else None) or "—"
        if nome == "Equipamento":
            return rec.eletrico.nome_equipamento or "—"
        if nome == "Tipo Equip.":
            return rec.eletrico.equipamento_alvo or "—"
        if nome == "Barra":
            return rec.eletrico.barra or "—"
        if nome == "Nível Tensão":
            return rec.eletrico.nivel_tensao or "—"
        if nome == "Pareado":
            direcao = rec.tipo_sinal.direcao
            if direcao == "InputOutput":
                return "Sim"
            if direcao == "Output":
                # comando ainda sem par: rótulo próprio p/ o operador ACHAR o
                # comando na revisão (SP-CVA2 E6.3 — antes renderizava "—")
                return "Comando (sem par)" if rec.enderecamento.indices else "Órfão"
            return "—"
        if nome == "Sheet origem":
            return sheet_origem(rec)
        return ""

    def _valor_edicao(self, rec, col):
        """Valor cru p/ Qt.EditRole -- sem sentinela "—" nem sufixos de
        exibição (evita o round-trip DisplayRole->setData corromper o dado
        quando o editor reabre a célula pra edição).
        """
        nome = COLUNAS[col]
        if nome == "Fase":
            return rec.eletrico.fase or ""
        if nome == "Nível Tensão":
            return rec.eletrico.nivel_tensao or ""
        if nome == "Barra":
            return rec.eletrico.barra or ""
        if nome == "Tipo Equip.":
            return rec.eletrico.equipamento_alvo or ""
        if nome == "Módulo":
            return (rec.modulo.nome if rec.modulo else None) or ""
        if nome == "Endereço Output":
            return ";".join(str(i) for i in rec.enderecamento.indices_saida)
        if nome == "Sinal":
            return rec.sigla_sinal or ""
        return self._texto(rec, col)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self._estado.registros[index.row()]
        nome = COLUNAS[index.column()]
        if role == Qt.DisplayRole:
            return self._texto(rec, index.column())
        if role == Qt.EditRole:
            return self._valor_edicao(rec, index.column())
        if role == Qt.ForegroundRole:
            if nome == "Status":
                return COR_DECIDIDO if rec.status == "decidido" else COR_REVISAO
            if nome == "Confiança":
                if rec.candidatos:
                    return cor_faixa(rec.candidatos[0].score)
                if rec.status == "decidido":
                    return cor_faixa(1.0)
                return cor_faixa(None)
        if role == Qt.ToolTipRole and nome in ("Sinal", "Descr. ADMS"):
            return self._adms(rec) or None
        if role == Qt.ToolTipRole and nome == "Motivo":
            motivo = self._estado.motivo_por_id().get(rec.id)
            return _MOTIVO_TOOLTIP.get(motivo, "") if motivo else None
        if role == Qt.FontRole and nome in _COLUNAS_MONO:
            return QFont("Consolas")
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role != Qt.EditRole or not index.isValid():
            return False
        nome = COLUNAS[index.column()]
        linha = index.row()
        texto = str(value).strip()
        if nome == "Tipo":
            if "/" not in texto:
                return False
            categoria, direcao = texto.split("/", 1)
            self._estado.definir_tipo(linha, categoria, direcao)
        elif nome == "Fase":
            self._estado.definir_fase(linha, texto or None)
        elif nome == "Nível Tensão":
            self._estado.definir_nivel_tensao(linha, texto or None)
        elif nome == "Barra":
            self._estado.definir_barra(linha, texto or None)
        elif nome == "Tipo Equip.":
            self._estado.definir_tipo_equip(linha, texto or None)
        elif nome == "Módulo":
            self._estado.definir_modulo(linha, texto or None)
        elif nome == "Escala":
            try:
                valor = float(texto.replace(",", ".")) if texto else None
            except ValueError:
                return False
            self._estado.definir_escala(linha, valor)
        elif nome in ("Endereço", "Endereço Output"):
            try:
                indices = tuple(int(p) for p in texto.split(";")) if texto else ()
            except ValueError:
                return False
            if not all(0 <= v <= 65535 for v in indices):
                return False
            campo = "indices" if nome == "Endereço" else "indices_saida"
            self._estado.definir_enderecos(linha, campo, indices)
        else:
            return False
        self.ultima_edicao = (nome, value)
        topo = self.index(linha, 0)
        fim = self.index(linha, len(COLUNAS) - 1)
        self.dataChanged.emit(topo, fim)
        return True

    def aplicar_valor_em_lote(self, ids: list[str], coluna: str, valor) -> int:
        """Propaga `valor` na `coluna` para todos os registros com `ids`.

        Reusa `setData` (mesma validação/transição da edição individual). Um
        único snapshot para o lote inteiro (padrão de `AppState.aprovar_ids`):
        suprime os snapshots internos de cada `setData` e faz só um antes do
        loop, para que 1 `desfazer()` reverta o lote inteiro.
        """
        if coluna not in _EDITAVEIS:
            return 0
        col = COLUNAS.index(coluna)
        indice_por_id = {r.id: i for i, r in enumerate(self._estado.registros)}
        linhas = [indice_por_id[id_] for id_ in ids if id_ in indice_por_id]
        if not linhas:
            return 0
        self._estado._snapshot()
        snapshot_original = self._estado._snapshot
        self._estado._snapshot = lambda: None
        aplicados = 0
        try:
            for linha in linhas:
                if self.setData(self.index(linha, col), valor, Qt.EditRole):
                    aplicados += 1
        finally:
            self._estado._snapshot = snapshot_original
        return aplicados

    def definir_sigla(self, linha: int, sigla: str) -> None:
        self._estado.definir_sigla(linha, sigla)
        topo = self.index(linha, 0)
        fim = self.index(linha, len(COLUNAS) - 1)
        self.dataChanged.emit(topo, fim)

    def adicionar_registro(self, registro: SignalRecord) -> None:
        """Anexa um registro ao final, notificando a view via Qt (insertRows).

        Quem chama é responsável por `self._estado._snapshot()` antes, se
        quiser permitir desfazer (mesmo padrão de `remover_linhas`).
        """
        n = len(self._estado.registros)
        self.beginInsertRows(QModelIndex(), n, n)
        self._estado.registros.append(registro)
        self.endInsertRows()

    def sheets_distintas(self) -> list[str]:
        """Nomes de sheet distintos presentes nos registros, ordenados.

        Usado pela tela de revisão pra montar as abas (uma por sheet + "Tudo").
        """
        return sorted({sheet_origem(r) for r in self._estado.registros if sheet_origem(r)})

    def contagem_por_sheet(self) -> dict[str, tuple[int, int]]:
        """Sheet -> (nº de registros com status "revisao", nº total de
        registros da sheet). Sheets sem pendência aparecem com (0, total)."""
        contagem: dict[str, tuple[int, int]] = {}
        for r in self._estado.registros:
            s = sheet_origem(r)
            if not s:
                continue
            pendentes, total = contagem.get(s, (0, 0))
            total += 1
            if r.status == "revisao":
                pendentes += 1
            contagem[s] = (pendentes, total)
        return contagem

    def pendentes_por_sheet(self) -> dict[str, int]:
        """Sheet -> nº de registros com status "revisao" (sheets sem pendência
        aparecem com 0, para a aba poder mostrar o check)."""
        return {s: pendentes for s, (pendentes, _total) in self.contagem_por_sheet().items()}

    def remover_linhas(self, indices: list[int]) -> None:
        """Remove as linhas (índices da fonte, 0-based) da lista subjacente.

        Notifica a view linha a linha via begin/endRemoveRows -- exigido pelo
        Qt antes/depois da mutação real, para não desincronizar view/modelo.
        """
        for linha in sorted(set(indices), reverse=True):
            if not (0 <= linha < len(self._estado.registros)):
                continue
            self.beginRemoveRows(QModelIndex(), linha, linha)
            self._estado.registros.pop(linha)
            self.endRemoveRows()
