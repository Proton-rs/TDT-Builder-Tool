"""SP-I Task 1: relatorio de outputs (comandos DNP3) classificados em
pareado / write_legitimo / revisao(motivo) / ESCAPOU, para a LISTA 1 - GTD.

Contexto e criterios de classificacao (derivados de src/tdt/dc_pairer.py)
---------------------------------------------------------------------------
`tdt.pipeline.executar` roda `dc_pairer.parear(decididos, config)` UMA vez,
sobre a lista de registros ja DECIDIDOS (que escaparam de toda revisao
pre-pairer -- score_baixo, categoria_ambigua, sem_endereco, etc.). O pairer
agrupa por (modulo, equipamento, sigla) e, dentro de cada grupo:

  - grupo sem Output: nada a fazer, os Inputs seguem como estao.
  - grupo com Output(s) e SEM Input: cada Output cuja sigla (upper) esteja em
    `config.siglas_write_legitimo` (default apenas {"CDC"}) vira um
    SignalRecord Output "solto" (standalone) que segue para
    `resultado.lista.registros` com `tipo_sinal.direcao == "Output"` --
    **write_legitimo**. Os demais viram `ItemRevisao(o, motivo=
    "comando_sem_discreto")` -- **revisao:comando_sem_discreto**.
  - grupo com exatamente 1 Input e 1 Output E `compatibilidade_texto` (gate
    semantico SP-E/D5) aprova o par: `fundir(input, output)` produz UM
    SignalRecord com `tipo_sinal.direcao == "InputOutput"` --
    **pareado**. O Output original desaparece como registro proprio (so
    sobra via `enderecamento.indices_saida` no fundido).
  - qualquer outra combinacao (N inputs x M outputs, ou 1x1 que o gate
    semantico rejeitou) cai no catch-all `_parear_catchall`: casa Output-Input
    por similaridade de descricao (fuzzy >= `config.limiar_pareamento_
    similaridade`, default 60.0) SE `compatibilidade_texto` tambem aprovar
    aquele par especifico; o que sobra sem par vira
    `ItemRevisao(o, motivo="pareamento_ambiguo")` -- **revisao:
    pareamento_ambiguo**.

Portanto, no resultado final:
  - pareado:        rec em resultado.lista.registros com
                     tipo_sinal.direcao == "InputOutput"
  - write_legitimo:  rec em resultado.lista.registros com
                     tipo_sinal.direcao == "Output" (sobrou solto do pairer)
  - revisao:<motivo>: item em resultado.revisao cujo item.registro.tipo_sinal
                     .direcao == "Output" -- inclui os motivos do dc_pairer
                     (comando_sem_discreto, pareamento_ambiguo) E qualquer
                     motivo PRE-pairer (score_baixo, categoria_ambigua,
                     sem_endereco, modulo_indefinido, decisao_por_projeto,
                     ...) para um registro cuja direcao classificada foi
                     Output -- ou seja, um comando que nunca chegou a ser
                     visto pelo dc_pairer porque a decisao (roteador/filtros)
                     já o mandou pra revisao antes.
  - ESCAPOU:         qualquer registro Output que nao se encaixe em nenhuma
                     das categorias acima -- teoricamente nao deveria
                     acontecer (todo Output decidido cai em pareado ou
                     write_legitimo; todo Output nao-decidido cai em algum
                     item de revisao), mas o script varre TODOS os registros
                     (decididos + revisao) e sinaliza qualquer coisa fora do
                     modelo esperado (ex.: Output que nao e nem Output nem
                     InputOutput na saida final, contradizendo o proprio
                     tipo_sinal.direcao de origem) para nao assumir
                     silenciosamente que o modelo de 3 baldes esta completo.

Uso:
    PYTHONPATH=src python bench/diag_outputs_sem_par.py
"""
from __future__ import annotations

import warnings
import logging
from collections import Counter

warnings.simplefilter("ignore")
logging.disable(logging.CRITICAL)

from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.contracts import ItemRevisao, ResultadoPipeline, SignalRecord
from tdt.dados.encoder import criar_encoder
from tdt.pipeline import executar

_INPUT = "docs/input_nao_homogeneo_1_GTD.xlsx"
_TEMPLATE = "docs/dnp3_template.xlsx"
_LISTA_PADRAO = "docs/Pontos Padrao ADMS_v2.xlsx"


def classificar_decidido(rec: SignalRecord, siglas_write: frozenset[str]) -> str:
    """Classifica um registro DECIDIDO (resultado.lista.registros).

    So deveria ser chamado com rec.tipo_sinal.direcao in
    {"Output", "InputOutput"} -- ver `eh_relevante`.
    """
    direcao = rec.tipo_sinal.direcao
    if direcao == "InputOutput":
        return "pareado"
    if direcao == "Output":
        # Sobrou solto do dc_pairer: so acontece hoje se a sigla estava em
        # siglas_write_legitimo (senao teria virado ItemRevisao). Verifica
        # mesmo assim -- se a sigla NAO esta na whitelist, o registro
        # "escapou" do dc_pairer sem passar por nenhum dos 2 caminhos
        # esperados (bug de modelo, nao so de dado).
        if (rec.sigla_sinal or "").upper() in siglas_write:
            return "write_legitimo"
        return "ESCAPOU:output_solto_fora_whitelist"
    return f"ESCAPOU:direcao_inesperada={direcao}"


def eh_output_original(rec: SignalRecord) -> bool:
    """True se o registro (pre-pairer, no que sobrou em resultado.revisao)
    representa um comando (Output) -- inclui registros cujo pairer ja
    rotulou (comando_sem_discreto/pareamento_ambiguo tem sempre
    tipo_sinal.direcao == "Output": ver dc_pairer.py linhas 98-102 e 161-164)
    e registros PRE-pairer que nunca chegaram no dc_pairer (o roteador ja
    decidiu direcao a partir da estrutura da planilha antes do scoring)."""
    return rec.tipo_sinal.direcao == "Output"


def main() -> None:
    cfg = Config()
    aud = Auditoria()
    resultado, _wb_out = executar(
        _INPUT, _TEMPLATE, _LISTA_PADRAO,
        config=cfg, encoder=criar_encoder(cfg.modelo_embedding), auditoria=aud,
        subestacao="GTD",
    )
    siglas_write = cfg.siglas_write_legitimo

    cats: Counter[str] = Counter()
    escapados: list[tuple] = []

    for rec in resultado.lista.registros:
        if rec.tipo_sinal.direcao not in ("Output", "InputOutput"):
            continue
        cat = classificar_decidido(rec, siglas_write)
        cats[cat] += 1
        if cat.startswith("ESCAPOU"):
            escapados.append((cat, rec.id, rec.sigla_sinal, rec.descricoes.bruta,
                               rec.justificativa))

    for item in resultado.revisao:
        if eh_output_original(item.registro):
            cats[f"revisao:{item.motivo}"] += 1

    total_outputs = sum(v for k, v in cats.items())
    print(f"Total de registros Output/InputOutput classificados: {total_outputs}")
    print()
    for cat, n in sorted(cats.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"  {cat}: {n}")
    print()
    if escapados:
        print(f"=== {len(escapados)} caso(s) ESCAPOU (fora do modelo de 3 baldes) ===")
        for cat, rid, sigla, bruta, just in escapados:
            print(f"  [{cat}] id={rid} sigla={sigla!r} desc={bruta!r} justificativa={just!r}")
    else:
        print("Nenhum caso ESCAPOU do modelo de 3 baldes (pareado/write_legitimo/revisao).")


if __name__ == "__main__":
    main()
