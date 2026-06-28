"""Gera bench/rotulos.py a partir de duas fontes de ground-truth.

Fonte 1 — Lista Padrão ADMS v2 (docs/Pontos Padrao ADMS_v2.xlsx): cada sinal
(Discrete + Analog) vira um par (descrição canônica, sigla). Cobre todas as
~754 siglas conhecidas.

Fonte 2 — Export Full Base limpo (docs/Export_base_Full_limpo.json, gerado
por scripts/limpar_full_base.py): para cada entrada cuja sigla já é válida
(garantido pelo filtro 6 do script de limpeza), se o Signal Alias é
diferente da descrição canônica daquela sigla, adiciona como par extra —
uma variação real de como o sinal aparece em planilhas de produção.

Sinais analógicos do Export ficam fora do escopo da Fonte 2 (a sigla
canônica de analógicos segue nomenclatura ainda não validada) — só entram
os pares oriundos de DNP3_DiscreteSignals/DNP3_DiscreteAnalog. Os pares da
Fonte 1, por outro lado, incluem tanto Discrete quanto Analog da lista
padrão.

Resultado: concatena Fonte 1 + Fonte 2 e regrava bench/rotulos.py no
formato atual (lista de tuplas), preservando compatibilidade com
bench/benchmark.py (`from rotulos import ROTULOS`).

Uso: python scripts/gerar_ground_truth.py (da raiz do projeto)
Saída: bench/rotulos.py (sobrescrito; os 28 pares curados originais são
preservados em bench/rotulos_v1_curado.py)
"""
from __future__ import annotations

import json
import pathlib
import sys

_SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_ROOT / "src"))

from tdt.dados.lista_padrao import ListaPadraoADMS  # noqa: E402

LISTA_V2_PATH = _ROOT / "docs" / "Pontos Padrao ADMS_v2.xlsx"
EXPORT_LIMPO_PATH = _ROOT / "docs" / "Export_base_Full_limpo.json"
ROTULOS_PATH = _ROOT / "bench" / "rotulos.py"

# Sheets do Export cuja sigla canônica (Discrete) já foi validada contra a
# Lista Padrão v2. AnalogSignals fica fora (fora de escopo — ver spec).
SHEETS_DISCRETE = {"DNP3_DiscreteSignals", "DNP3_DiscreteAnalog"}


def _pares_fonte1() -> list[tuple[str, str]]:
    lp = ListaPadraoADMS.carregar(LISTA_V2_PATH)
    pares = [(s.descricao, s.sigla) for s in (*lp.discretos, *lp.analogicos) if s.descricao]
    # remove duplicatas exatas (descrição, sigla) preservando ordem
    vistos: set[tuple[str, str]] = set()
    unicos = []
    for p in pares:
        if p in vistos:
            continue
        vistos.add(p)
        unicos.append(p)

    # mesma regra de ambiguidade do Export (filtro 5 de limpar_full_base.py):
    # a própria Lista Padrão v2 tem ~4 descrições idênticas mapeadas para
    # siglas diferentes (ex.: "DEFEITO RELE 21" -> DR21 e DR). Sem saber
    # qual sigla é a "certa" para aquela descrição, ambos os pares são
    # ambíguos como ground-truth e precisam ser removidos.
    siglas_por_desc: dict[str, set[str]] = {}
    for desc, sigla in unicos:
        siglas_por_desc.setdefault(desc.strip().upper(), set()).add(sigla)
    descs_ambiguas = {d for d, siglas in siglas_por_desc.items() if len(siglas) > 1}
    return [p for p in unicos if p[0].strip().upper() not in descs_ambiguas]


def _descricao_canonica_por_sigla() -> dict[str, str]:
    lp = ListaPadraoADMS.carregar(LISTA_V2_PATH)
    mapa: dict[str, str] = {}
    for s in (*lp.discretos, *lp.analogicos):
        if s.descricao:
            mapa.setdefault(s.sigla.upper(), s.descricao.strip().upper())
    return mapa


def _pares_fonte2(desc_canonica: dict[str, str]) -> list[tuple[str, str]]:
    entradas = json.loads(EXPORT_LIMPO_PATH.read_text(encoding="utf-8"))
    pares: list[tuple[str, str]] = []
    vistos: set[tuple[str, str]] = set()
    for e in entradas:
        if e["sheet"] not in SHEETS_DISCRETE:  # analógicos do Export fora de escopo
            continue
        sigla = e["signal_name"].rsplit("_", 1)[-1]
        alias = e["signal_alias"].strip()
        canonica = desc_canonica.get(sigla.upper())
        if canonica is not None and alias.upper() == canonica:
            continue  # idêntico à descrição canônica -> já cobertO pela Fonte 1
        par = (alias, sigla)
        if par in vistos:
            continue
        vistos.add(par)
        pares.append(par)
    return pares


_CABECALHO = '''"""Ground-truth: descrição real (não-homogêneo) -> sigla ADMS correta.

Gerado automaticamente por scripts/gerar_ground_truth.py (spec SP-GT,
docs/superpowers/specs/2026-06-28-sp-gt-ground-truth-automatico-design.md).
Combina duas fontes:

  Fonte 1 — Lista Padrão ADMS v2 (docs/Pontos Padrao ADMS_v2.xlsx): par
            (descrição canônica, sigla) para cada sinal Discrete/Analog.
  Fonte 2 — Export Full Base limpo (docs/Export_base_Full_limpo.json):
            variações reais de planilhas de produção (Signal Alias) cuja
            sigla já existe na Lista Padrão v2 e cuja descrição difere da
            canônica.

Os 28 pares curados manualmente da versão anterior (rotulos.py v1) foram
preservados em bench/rotulos_v1_curado.py — não foram perdidos, apenas
substituídos como fonte primária do benchmark por este conjunto maior.

Para regerar: python scripts/gerar_ground_truth.py (da raiz do projeto).
Rótulos de domínio (ver skill especialista-ADMS-TDT). Usado para medir
precisão (sem falsos positivos) e taxa de decisão dos métodos de matching.
Cada sigla deve existir na lista padrão.
"""

ROTULOS: list[tuple[str, str]] = [
'''


def gerar() -> list[tuple[str, str]]:
    fonte1 = _pares_fonte1()
    desc_canonica = _descricao_canonica_por_sigla()
    fonte2 = _pares_fonte2(desc_canonica)

    todos = fonte1 + fonte2
    # dedup final (defensivo: pode haver coincidências entre fontes)
    vistos: set[tuple[str, str]] = set()
    sem_dup = []
    for p in todos:
        if p in vistos:
            continue
        vistos.add(p)
        sem_dup.append(p)

    # checagem final de ambiguidade (defensivo: Fonte 2 pode introduzir uma
    # descrição que colide com a de outra sigla vinda da Fonte 1)
    siglas_por_desc: dict[str, set[str]] = {}
    for desc, sigla in sem_dup:
        siglas_por_desc.setdefault(desc.strip().upper(), set()).add(sigla)
    descs_ambiguas = {d for d, siglas in siglas_por_desc.items() if len(siglas) > 1}
    return [p for p in sem_dup if p[0].strip().upper() not in descs_ambiguas]


def escrever(pares: list[tuple[str, str]]) -> None:
    linhas = [_CABECALHO]
    for desc, sigla in pares:
        linhas.append(f"    ({desc!r}, {sigla!r}),\n")
    linhas.append("]\n")
    ROTULOS_PATH.write_text("".join(linhas), encoding="utf-8")


def main() -> None:
    pares = gerar()
    escrever(pares)
    print(f"bench/rotulos.py gerado com {len(pares)} pares.")


if __name__ == "__main__":
    main()
