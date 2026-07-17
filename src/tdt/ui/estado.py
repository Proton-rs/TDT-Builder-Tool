"""Estado compartilhado entre as telas da UI. Sem widgets, testável puro.

ponytail: dataclass mutável simples; as telas leem/escrevem aqui em vez de se
importarem entre si.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace

from tdt.config import Config
from tdt.contracts import Enderecamento, ResultadoPipeline, SignalRecord
from tdt.dados.lista_padrao import ListaPadraoADMS
from tdt.pareamento_polaridade import _SIGLAS_POSICAO


@dataclass
class AppState:
    config: Config = field(default_factory=Config)
    paths: dict = field(default_factory=lambda: {"input": "", "output": "", "template": "", "lista_padrao": ""})
    modo: str = "auto"
    subestacao: str | None = None
    flags: dict = field(default_factory=lambda: {"pular_revisao": False, "aprovar_acima_threshold": True})
    aliases: dict[str, str] = field(default_factory=dict)  # sheet original → apelido
    sheets_excluidas: set[str] = field(default_factory=set)  # sheets (nome original) desmarcadas na tela inicial
    resultado: ResultadoPipeline | None = None
    registros: list[SignalRecord] = field(default_factory=list)
    lista_padrao: ListaPadraoADMS | None = None
    # ponytail: encoder guardado sem contagem de referências — só há um
    # PipelineWorker ativo por vez (UI dispara um por execução, sequencial).
    # Se isso mudar (workers concorrentes), revisitar com keep-alive/refs.
    encoder: object | None = None
    # ponytail: histórico é só uma pilha de undo (lista de snapshots de
    # `registros`, sem ponteiro/redo). A UI hoje não tem botão "Refazer" —
    # implementar índice + redo completo agora seria especular sobre um
    # requisito que não existe. Upgrade path: se um botão "Refazer" for
    # pedido, trocar a pilha por (_historico, _indice_historico) e avançar/
    # voltar o índice em vez de pop().
    _historico: list[list[SignalRecord]] = field(default_factory=list, repr=False)

    def _snapshot(self) -> None:
        """Salva o estado atual de `registros` antes de uma mutação destrutiva.

        Cópia superficial basta: SignalRecord é frozen, então os elementos
        nunca mudam in-place — só a lista é substituída/tem itens add/removidos.
        """
        self._historico.append(list(self.registros))

    def desfazer(self) -> bool:
        """Volta para o snapshot anterior. Retorna False se não há histórico."""
        if not self._historico:
            return False
        self.registros = self._historico.pop()
        return True

    def carregar_resultado(self, res: ResultadoPipeline) -> None:
        # sem dedupe: o pipeline garante que cada registro cai em só um dos
        # dois grupos (lista OU revisao). TelaAnalise/exportar_analise dedupam
        # por id mesmo assim, defensivamente — não há divergência hoje.
        self.resultado = res
        self.registros = list(res.lista.registros) + [it.registro for it in res.revisao]

    def motivo_por_id(self) -> dict[str, str]:
        if self.resultado is None:
            return {}
        return {item.registro.id: item.motivo for item in self.resultado.revisao}

    def aprovar_ids(self, ids: list[str]) -> int:
        """Aprova em lote os registros com os `ids` dados, usando a mesma
        transição de `definir_sigla`. A sigla JÁ ATRIBUÍDA tem precedência
        sobre o candidato top — aprovar confirma o que o usuário vê/editou,
        nunca reverte uma reclassificação manual (bug crítico 16/07).
        Um único snapshot para o lote inteiro: 1 `desfazer()` reverte tudo.
        """
        self._snapshot()
        indice_por_id = {r.id: i for i, r in enumerate(self.registros)}
        aprovados = 0
        for id_ in ids:
            indice = indice_por_id.get(id_)
            if indice is None:
                continue
            r = self.registros[indice]
            sigla = r.sigla_sinal or (r.candidatos[0].sigla if r.candidatos else None)
            if not sigla:
                continue
            self.definir_sigla(indice, sigla, snapshot=False)
            aprovados += 1
        return aprovados

    def definir_sigla(self, indice: int, sigla: str, *, snapshot: bool = True) -> None:
        if snapshot:
            self._snapshot()
        r = self.registros[indice]
        self.registros[indice] = replace(
            r, sigla_sinal=sigla, status="decidido",
            justificativa="editado manualmente",
        )

    def _editar_nested(self, indice: int, campo: str, **kwargs) -> None:
        """Substitui atributos de um campo aninhado (Eletrico/TipoSinal/
        Modulo/GrandezasAnalogicas) via replace, sem tocar status/justificativa.
        """
        self._snapshot()
        r = self.registros[indice]
        novo = replace(getattr(r, campo), **kwargs)
        self.registros[indice] = replace(r, **{campo: novo})

    def definir_tipo(self, indice: int, categoria: str, direcao: str) -> None:
        self._editar_nested(indice, "tipo_sinal", categoria=categoria,
                             direcao=direcao, categoria_confiavel=True)

    def definir_fase(self, indice: int, fase: str | None) -> None:
        self._editar_nested(indice, "eletrico", fase=fase)

    def definir_nivel_tensao(self, indice: int, nivel: str | None) -> None:
        self._editar_nested(indice, "eletrico", nivel_tensao=nivel)

    def definir_barra(self, indice: int, barra: str | None) -> None:
        self._editar_nested(indice, "eletrico", barra=barra)

    def definir_tipo_equip(self, indice: int, equip: str | None) -> None:
        self._editar_nested(indice, "eletrico", equipamento_alvo=equip,
                             equipamento_inferido=False)

    def definir_equipamento(self, indice: int, nome: str | None) -> None:
        """ID do equipamento (ex. corrigir "81-1" -> "52-11"); None limpa."""
        self._editar_nested(indice, "eletrico", nome_equipamento=nome)

    def definir_descricao_bruta(self, indice: int, texto: str) -> None:
        """Só o texto bruto (afeta fallback de Signal Alias no export);
        normalizada/tokens NÃO reprocessam (spec 2026-07-15 §4)."""
        self._editar_nested(indice, "descricoes", bruta=texto)

    def definir_modulo(self, indice: int, nome: str | None) -> None:
        self._editar_nested(indice, "modulo", nome=nome)

    def definir_escala(self, indice: int, valor: float | None) -> None:
        self._editar_nested(indice, "grandezas_analogicas", escala_transmissao=valor)

    def definir_enderecos(self, indice: int, campo: str, indices: tuple[int, ...]) -> None:
        self._editar_nested(indice, "enderecamento", **{campo: indices})

    def formar_par_posicao(self, id_a: str, id_b: str, sigla: str) -> str | None:
        """Funde 2 registros num único MultiCoord (mesmo formato de
        `normalizador_estrutural.corrigir`), com a `sigla` escolhida pelo
        operador (ex. corrigir DJA1 -> DJF1 quando o pareamento automático
        errou a polaridade). Valida mesmo módulo + mesmo equipamento + 1
        endereço cada; devolve mensagem de erro sem mutar nada se inválido.
        """
        indice_por_id = {r.id: i for i, r in enumerate(self.registros)}
        ia = indice_por_id.get(id_a)
        ib = indice_por_id.get(id_b)
        if ia is None or ib is None:
            return "Registro não encontrado."
        a, b = self.registros[ia], self.registros[ib]
        if a.modulo.nome != b.modulo.nome:
            return "Os dois sinais precisam ser do mesmo módulo."
        if a.eletrico.nome_equipamento != b.eletrico.nome_equipamento:
            return "Os dois sinais precisam ser do mesmo equipamento."
        if len(a.enderecamento.indices) != 1 or len(b.enderecamento.indices) != 1:
            return "Cada sinal precisa ter exatamente 1 endereço."
        self._snapshot()
        primeiro, segundo = (
            (a, b) if a.enderecamento.indices[0] <= b.enderecamento.indices[0] else (b, a)
        )
        fundido = replace(
            primeiro,
            enderecamento=Enderecamento(
                primeiro.enderecamento.protocolo,
                primeiro.enderecamento.indices + segundo.enderecamento.indices,
            ),
            tipo_sinal=replace(primeiro.tipo_sinal, datatype="MultiCoord"),
            sigla_sinal=sigla, status="decidido",
            justificativa="par de posição formado manualmente",
        )
        novos = [r for i, r in enumerate(self.registros) if i not in (ia, ib)]
        novos.insert(min(ia, ib), fundido)
        self.registros = novos
        return None

    def aplicar_reparear(self, ids, whitelist_posicao, config) -> "ResultadoReparear":
        """Reparea os registros elegíveis dentre `ids` (P3). 1 snapshot: 1
        desfazer reverte o lote. Ordem preservada; comando absorvido pela
        fusão sai da lista (endereço vive no par — conservação auditada)."""
        from tdt.ui.reparear import ResultadoReparear, elegivel, reparear
        alvo = set(ids)
        elegiveis = [r for r in self.registros if r.id in alvo and elegivel(r)]
        if not elegiveis:
            return ResultadoReparear((), 0, 0, 0)
        self._snapshot()
        res = reparear(elegiveis, whitelist_posicao, config)
        ids_eleg = {r.id for r in elegiveis}
        novos_por_id = {r.id: r for r in res.resultantes}
        saida = []
        for r in self.registros:
            if r.id in ids_eleg:
                novo = novos_por_id.get(r.id)
                if novo is not None:
                    saida.append(novo)
            else:
                saida.append(r)
        self.registros = saida
        return res

    def trocar_sigla_par(self, id_: str, nova_sigla: str) -> None:
        """Troca a sigla de um par de posição já fundido (ex. DJA1 <-> DJF1),
        preservando `enderecamento`/`tipo_sinal` intactos. No-op se
        `nova_sigla` não estiver no catálogo de siglas de posição.
        """
        if (nova_sigla or "").upper() not in _SIGLAS_POSICAO:
            return
        indice_por_id = {r.id: i for i, r in enumerate(self.registros)}
        indice = indice_por_id.get(id_)
        if indice is None:
            return
        self._snapshot()
        r = self.registros[indice]
        self.registros[indice] = replace(
            r, sigla_sinal=nova_sigla, status="decidido",
            justificativa="sigla de par trocada manualmente",
        )

    def separar_par_posicao(self, id_: str) -> str | None:
        """Inverso de formar_par_posicao (P3b). RECONSTRÓI (a descrição do
        registro absorvido não existe mais — limitação documentada na spec):
        2 Inputs de 1 índice, sigla limpa, revisão `posicao_ambigua`."""
        indice_por_id = {r.id: i for i, r in enumerate(self.registros)}
        i = indice_por_id.get(id_)
        if i is None:
            return "Registro não encontrado."
        r = self.registros[i]
        if r.tipo_sinal.direcao == "InputOutput":
            return "O par tem comando pareado: desvincule (Parear D+C) antes de separar."
        if (r.tipo_sinal.direcao != "Input"
                or r.tipo_sinal.datatype != "MultiCoord"
                or len(r.enderecamento.indices) != 2):
            return "Selecione um par de posição (Input MultiCoord com 2 endereços)."
        if (r.sigla_sinal or "").upper() not in _SIGLAS_POSICAO:
            return "A sigla do registro não é de posição."
        self._snapshot()
        base = replace(
            r,
            tipo_sinal=replace(r.tipo_sinal, datatype="SingleBit"),
            sigla_sinal=None, status="revisao",
            justificativa="posicao_ambigua",   # par separado manualmente — redecidir
        )
        met_a = replace(base, enderecamento=Enderecamento(
            r.enderecamento.protocolo, (r.enderecamento.indices[0],)))
        met_b = replace(base, id=f"{r.id}_pos_{uuid.uuid4().hex[:6]}",
                        enderecamento=Enderecamento(
                            r.enderecamento.protocolo, (r.enderecamento.indices[1],)))
        novos = list(self.registros)
        novos[i] = met_a
        novos.insert(i + 1, met_b)
        self.registros = novos
        return None
