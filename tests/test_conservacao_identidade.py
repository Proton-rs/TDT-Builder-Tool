"""SP-FLUXO-DADOS Task 4: nenhum campo de identidade preenchido na entrada
(sigla, módulo, equipamento, endereço) é PERDIDO (valor -> vazio) até o fim
da cadeia parcial de geração. Sobrescrita (valor -> outro valor) é permitida
— e auditada em produção via Auditoria.sobrescritas (Task 3). Fixture espelha
tests/test_conservacao_comandos.py (conservação por CONTAGEM); aqui é
conservação por CONTEÚDO."""

from tdt import criador_lista_homogenea, dc_pairer, engine_tdt
from tdt.auditoria import diff_identidade
from tdt.config import Config
from tdt.contracts import (
    Descricoes, Eletrico, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.normalizador_estrutural import corrigir, fundir_pares_posicao


def _rec(rid, sigla, direcao, modulo, indices, desc, equip="52-1"):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(nome_equipamento=equip),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_nenhuma_perda_de_identidade_na_cadeia_de_geracao():
    entrada = [
        # par de posição fundível (vira MultiCoord no id BC2:21)
        _rec("BC2:21", "DJF1", "Input", "BC2", [320], "52 06 ABERTO"),
        _rec("BC2:22", "DJF1", "Input", "BC2", [321], "52 06 FECHADO"),
        # comando toggle do mesmo grupo (funde no dc_pairer)
        _rec("BC2:14", "DJF1", "Output", "BC2", [90], "52 06 ABRIR FECHAR"),
        # input comum com equipamento
        _rec("BC2:32", "MOLA", "Input", "BC2", [326], "MOLA DESCARREGADA"),
        # comando órfão -> revisão comando_sem_discreto
        _rec("BC9:1", "DJF1", "Output", "BC9", [200], "DISJ DESLIGAR LIGAR"),
        # duplicata de endereço no mesmo grupo -> revisão endereco_duplicado
        _rec("BC3:5", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
        _rec("BC3:6", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
    ]
    wl = frozenset({"DJF1"})
    fundidos = fundir_pares_posicao(entrada, wl)
    pareados, rev1 = dc_pairer.parear(fundidos, Config())
    corrigidos, rev2 = corrigir(list(pareados), wl)
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao="SE1")
    lista, rev3 = engine_tdt.particionar_custom_id_duplicado(lista)
    lista, rev4 = engine_tdt.particionar_endereco_duplicado(lista)

    finais = list(lista.registros) + [
        ir.registro for ir in (*rev1, *rev2, *rev3, *rev4)
    ]
    perdas = [d for d in diff_identidade(entrada, finais) if d.tipo == "perda"]
    assert perdas == [], f"identidade perdida no caminho: {perdas}"
