"""SP-FLUXO-DADOS Task 3: o pipeline emite eventos fluxo_dados quando uma
etapa muda identidade — aqui, a fusão MultiCoord do par de posição muda
`indices` do registro sobrevivente (320,) -> (320, 321)."""

from dataclasses import replace

from tdt import pipeline
from tdt.auditoria import Auditoria
from tdt.config import Config
from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.dados.lista_padrao import ListaPadraoADMS

LISTA_PADRAO = "docs/Pontos Padrao ADMS_v8.xlsx"
TEMPLATE = "docs/dnp3_template.xlsx"


def _rec(rid, sigla, indices, desc):
    return SignalRecord(
        id=rid, modulo=Modulo("BC2", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(nome_equipamento="52-6"),
        sigla_sinal=sigla, status="decidido",
    )


def test_gerar_tdt_audita_sobrescrita_de_indices_na_fusao():
    lp = ListaPadraoADMS.carregar(LISTA_PADRAO)
    aud = Auditoria()
    cfg = replace(Config(), siglas_fundiveis_extra=frozenset({"DJF1"}))
    regs = [
        _rec("BC2:21", "DJF1", (320,), "52 06 ABERTO"),
        _rec("BC2:22", "DJF1", (321,), "52 06 FECHADO"),
    ]
    pipeline.gerar_tdt(regs, TEMPLATE, lp, subestacao="SE1",
                       config=cfg, auditoria=aud)
    evs = [e for e in aud.eventos if e.modulo == "fluxo_dados"]
    assert any(
        e.dados["campo"] == "indices"
        and e.dados["etapa"] == "fundir_pares_posicao"
        and e.signal_id == "BC2:21"
        for e in evs
    ), f"nenhum evento de fusão: {evs}"
