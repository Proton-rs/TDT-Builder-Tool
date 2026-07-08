"""Lê a lista padrão ADMS (``Pontos Padrao ADMS_v1.xlsx``).

É o gabarito de respostas: o que os scorers comparam contra. Colunas
localizadas pelo nome (row 1), nunca por índice. Linhas inválidas (sigla
vazia / ``#N/A``) são ignoradas.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import openpyxl

_INVALIDOS = {None, "", "#N/A", "NONE", "NULL"}


@dataclass(frozen=True)
class SinalPadrao:
    sigla: str
    descricao: str
    signal_type: str
    direction: str | None
    mm: str | None
    categoria: str  # "Discrete" | "Analog"
    estados_brutos: str | None = None
    valores_scada: tuple[int, ...] = ()
    tipo_medicao: str | None = None  # "Corrente", "Tensão", ... (lista padrão, PT)
    unidade_exibicao: str | None = None  # "A", "kV", "Grau", "-", ...
    type_severidade: str | None = None  # "PROT", "FALHAS FCOM/VCA/VCC", ... (só discretos)


def _val(v) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    return None if s.upper() in _INVALIDOS else s


def _coluna(header: tuple, nome: str) -> int | None:
    alvo = nome.strip().upper()
    for i, h in enumerate(header):
        if h is not None and str(h).strip().upper() == alvo:
            return i
    return None


def _ler_sheet(ws, categoria: str, mapa: dict[str, str]) -> list[SinalPadrao]:
    linhas = ws.iter_rows(values_only=True)
    header = next(linhas)
    idx = {
        chave: (_coluna(header, col) if col is not None else None)
        for chave, col in mapa.items()
    }
    if idx["sigla"] is None:
        raise ValueError(f"coluna SINAL ausente em {ws.title}")

    sinais: list[SinalPadrao] = []
    for row in linhas:
        sigla = _val(row[idx["sigla"]])
        if sigla is None:
            continue

        def get(chave):
            i = idx[chave]
            return _val(row[i]) if i is not None and i < len(row) else None

        valores_raw = get("valores")
        try:
            valores = tuple(int(p) for p in valores_raw.split(";")) if valores_raw else ()
        except ValueError:
            valores = ()  # "#N/A" ou formato inesperado

        sinais.append(
            SinalPadrao(
                sigla=sigla,
                descricao=get("descricao") or "",
                signal_type=get("signal_type") or "",
                direction=get("direction"),
                mm=get("mm"),
                categoria=categoria,
                estados_brutos=get("estados"),
                valores_scada=valores,
                tipo_medicao=get("tipo_medicao"),
                unidade_exibicao=get("unidade_exibicao"),
                type_severidade=get("type_severidade"),
            )
        )
    return sinais


@dataclass(frozen=True)
class ListaPadraoADMS:
    discretos: tuple[SinalPadrao, ...]
    analogicos: tuple[SinalPadrao, ...]

    @classmethod
    def carregar(cls, path: str | Path) -> "ListaPadraoADMS":
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        try:
            disc = _ler_sheet(
                wb["DiscreteSignals"],
                "Discrete",
                {
                    "sigla": "SINAL",
                    "descricao": "DESCRIÇÃO NOVA",
                    "signal_type": "SIGNAL TYPE",
                    "direction": "DIRECTION",
                    "mm": "MM",
                    "estados": "FUNÇÃO",
                    "valores": "VALOR",
                    "tipo_medicao": None,
                    "unidade_exibicao": None,
                    "type_severidade": "TYPE SEVERIDADE",
                },
            )
            ana = _ler_sheet(
                wb["AnalogSignals"],
                "Analog",
                {
                    "sigla": "SINAL",
                    "descricao": "DESCRIÇÃO NOVA",
                    "signal_type": "SIGNAL TYPE",
                    "direction": "DIREÇÃO DO FLUXO",
                    "mm": None,
                    "estados": None,
                    "valores": None,
                    "tipo_medicao": "TIPO DE MEDIÇÃO",
                    "unidade_exibicao": "UNIDADE DE EXIBIÇÃO",
                    "type_severidade": None,
                },
            )
        finally:
            wb.close()
        return cls(tuple(disc), tuple(ana))

    def por_sigla(self, sigla: str) -> SinalPadrao | None:
        alvo = sigla.strip().upper()
        for s in (*self.discretos, *self.analogicos):
            if s.sigla.upper() == alvo:
                return s
        return None

    @property
    def siglas(self) -> frozenset[str]:
        """Todas as siglas (discretos + analógicos), normalizadas maiúsculas —
        usado pela detecção de coluna de sigla em listas não-homogêneas."""
        return frozenset(s.sigla.upper() for s in (*self.discretos, *self.analogicos))
