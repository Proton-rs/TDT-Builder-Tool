"""Estado compartilhado entre as telas da UI. Sem widgets, testável puro.

ponytail: dataclass mutável simples; as telas leem/escrevem aqui em vez de se
importarem entre si.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from tdt.config import Config
from tdt.contracts import ResultadoPipeline, SignalRecord
from tdt.dados.lista_padrao import ListaPadraoADMS


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
        transição de `definir_sigla` (sigla do candidato top ou já atribuída).
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
            sigla = r.candidatos[0].sigla if r.candidatos else r.sigla_sinal
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

    def definir_modulo(self, indice: int, nome: str | None) -> None:
        self._editar_nested(indice, "modulo", nome=nome)

    def definir_escala(self, indice: int, valor: float | None) -> None:
        self._editar_nested(indice, "grandezas_analogicas", escala_transmissao=valor)

    def definir_enderecos(self, indice: int, campo: str, indices: tuple[int, ...]) -> None:
        self._editar_nested(indice, "enderecamento", **{campo: indices})
