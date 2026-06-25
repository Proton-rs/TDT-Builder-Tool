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
    resultado: ResultadoPipeline | None = None
    registros: list[SignalRecord] = field(default_factory=list)
    lista_padrao: ListaPadraoADMS | None = None

    def carregar_resultado(self, res: ResultadoPipeline) -> None:
        self.resultado = res
        self.registros = list(res.lista.registros) + [it.registro for it in res.revisao]

    def motivo_por_id(self) -> dict[str, str]:
        if self.resultado is None:
            return {}
        return {item.registro.id: item.motivo for item in self.resultado.revisao}

    def definir_sigla(self, indice: int, sigla: str) -> None:
        r = self.registros[indice]
        self.registros[indice] = replace(
            r, sigla_sinal=sigla, status="decidido",
            justificativa="editado manualmente",
        )
