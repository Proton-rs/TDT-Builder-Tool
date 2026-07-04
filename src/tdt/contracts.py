"""Contrato de dados compartilhado por todos os módulos do SP1.

Tipos imutáveis. Enriquecimento é funcional (dataclasses.replace), sem mutação
in-place. Nenhum módulo conhece o interior de outro — só estes tipos.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Modulo:
    nome: str | None
    origem_contexto: str  # "sheet_name" | "linha" | "coluna:<x>"
    tipo: str | None = None  # um de TIPOS_MODULO, ou None até classificar


TIPOS_MODULO: tuple[str, ...] = (
    "Alimentador",
    "Linha de Transmissão",
    "Banco de Capacitores",
    "Alta do Transformador",
    "Baixa do Transformador",
    "Transformador",
    "Barra",
    "Transferência",
    "Outros",
)


@dataclass(frozen=True)
class TipoSinal:
    categoria: str  # "Discrete" | "Analog" | "DiscreteAnalog"
    datatype: str = "SingleBit"  # "SingleBit" | "DoubleBit" (nativo) | "MultiCoord" (fusão D3)
    direcao: str = "Input"  # "Input" | "Output" | "InputOutput"
    categoria_confiavel: bool = True
    comando_duplo: bool = True  # Comando D (OUTCOORDS "N;N") vs Comando S ("N")


@dataclass(frozen=True)
class Enderecamento:
    protocolo: str  # "DNP3"
    indices: tuple[int, ...]  # (1100, 1101) DoubleBit nativo/MultiCoord | (17,) | () sem endereço
    indices_saida: tuple[int, ...] = ()  # OUTCOORDS do comando (após pareamento D+C)


@dataclass(frozen=True)
class Descricoes:
    bruta: str
    normalizada: str


@dataclass(frozen=True)
class Eletrico:
    fase: str | None = None
    nivel_tensao: str | None = None  # "AT" | "BT"
    equipamento_alvo: str | None = None
    nome_equipamento: str | None = None  # "52-10"
    barra: str | None = None  # "Principal" | "Auxiliar"
    equipamento_inferido: bool = False  # True quando equipamento_alvo veio de
    # inferência por topologia (C2.2), não extração explícita do texto —
    # distingue "inferido" de "extraído" para a auditoria.


@dataclass(frozen=True)
class GrandezasAnalogicas:
    unidade_medida: str | None = None
    escala_transmissao: float | None = None
    tipo_medicao: str | None = None


@dataclass(frozen=True)
class MapeamentoEstados:
    estados_brutos: str | None = None  # "Transit;LIGADO;DESLIGADO;Error"
    valores_scada: tuple[int, ...] = ()  # (0, 1, 2, 3)


@dataclass(frozen=True)
class Candidato:
    sigla: str
    score: float
    fonte: str  # "tfidf" | "vetorial" | "mesclado" | "expandido" | "ancora_sigla"


@dataclass(frozen=True)
class Diagnostico:
    """Scores por método por candidato, para auditoria/UI.

    ``scores_por_metodo[sigla] = {"tfidf": .., "vetorial": .., "fuzzy": ..}``.
    """

    scores_por_metodo: dict[str, dict[str, float]]


@dataclass(frozen=True)
class AjusteRegra:
    """Resultado de uma regra de domínio sobre um candidato.

    ``delta`` soma ao score; ``motivo`` alimenta a justificativa (rastreabilidade).
    """

    delta: float
    motivo: str


@dataclass(frozen=True)
class SignalRecord:
    id: str  # estável: f"{sheet}:{linha}"
    modulo: Modulo
    tipo_sinal: TipoSinal
    enderecamento: Enderecamento
    descricoes: Descricoes
    eletrico: Eletrico = field(default_factory=lambda: Eletrico())
    grandezas_analogicas: GrandezasAnalogicas = field(
        default_factory=lambda: GrandezasAnalogicas()
    )
    mapeamento_estados: MapeamentoEstados = field(
        default_factory=lambda: MapeamentoEstados()
    )
    sigla_sinal: str | None = None  # None até o Roteador decidir
    candidatos: tuple[Candidato, ...] = ()
    status: str = "pendente"  # "pendente" | "decidido" | "revisao"
    justificativa: str | None = None
    diagnostico: "Diagnostico | None" = None


@dataclass(frozen=True)
class ListaHomogenea:
    subestacao: str | None
    protocolo: str  # "DNP3"
    registros: tuple[SignalRecord, ...]  # todos com status="decidido"


@dataclass(frozen=True)
class ItemRevisao:
    registro: SignalRecord
    motivo: str  # "score_baixo"|"endereco_duplicado"|"sem_endereco"|"sem_fix"|"categoria_ambigua"|"categoria_incompativel"|"modulo_indefinido"|"sigla_multipla"|"posicao_ambigua"|"pareamento_ambiguo"|"nome_sigla_inconsistente"|"descartado_indefinido"|"descartado_redundante"|"comando_sem_discreto"|"estado_sem_candidato"|"fora_whitelist_equipamento"|"decisao_por_projeto"|"qualificador_ambiguo"
    candidatos_sugeridos: tuple[Candidato, ...] = ()


@dataclass(frozen=True)
class ResultadoPipeline:
    lista: ListaHomogenea
    revisao: tuple[ItemRevisao, ...]
    # id -> {"desc_normalizada", "regras_aplicadas", "gap", "gap_exigido",
    # "etapa_decisora", "endereco_bruto"}: contexto de decisão p/ auditoria
    # estendida (SP-J), fora do SignalRecord p/ não acoplar contrato central
    # a um caso de uso (exportação). Vazio p/ ids sem decisão rastreada
    # (ex. dual-pass de categoria incerta) -- nunca fabricado.
    diagnostico: dict[str, dict] = field(default_factory=dict)


@dataclass(frozen=True)
class Topologia:
    """Composição típica de equipamentos de um tipo de módulo (C2.1).

    ``default`` é o equipamento ao qual um sinal sem equipamento explícito é
    atribuído quando a topologia tem um principal não-ambíguo (ex.:
    alimentador -> 1 disjuntor). ``None`` quando o tipo não tem principal
    claro (ex.: barra com vários elementos) — nesse caso a inferência não
    chuta: o sinal vai para revisão (C2.2).
    """

    equipamentos: tuple[str, ...]
    default: str | None = None
    cardinalidade: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class MapaColunas:
    """Resultado da análise de colunas de uma sheet não-homogênea.

    ``header_row`` é 1-based; ``colunas`` mapeia campo lógico -> índice 0-based.
    Campos lógicos: descricao, modulo, indice, tipo, ied, variavel, sigla.
    """

    header_row: int
    colunas: dict[str, int]
