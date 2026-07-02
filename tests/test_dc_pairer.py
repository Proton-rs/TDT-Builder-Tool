from tdt.contracts import (
    Descricoes,
    Enderecamento,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt.dc_pairer import fundir, parear, separar


def _rec(rid, sigla, direcao, indices):
    return SignalRecord(
        id=rid,
        modulo=Modulo("LT_GTA", "coluna:modulo"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(sigla, sigla),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_pareia_input_e_output_vira_readwrite():
    regs = [_rec("s:1", "DJ", "Input", [5]), _rec("s:2", "DJ", "Output", [0])]
    pareados, revisao = parear(regs)
    assert len(pareados) == 1
    assert revisao == ()
    rw = pareados[0]
    assert rw.tipo_sinal.direcao == "InputOutput"
    assert rw.enderecamento.indices == (5,)
    assert rw.enderecamento.indices_saida == (0,)


def test_status_sozinho_passa():
    regs = [_rec("s:1", "DJ", "Input", [5])]
    pareados, revisao = parear(regs)
    assert pareados[0].tipo_sinal.direcao == "Input"
    assert revisao == ()


def test_comando_orfao_passa_como_write():
    regs = [_rec("s:1", "DJ", "Output", [0])]
    pareados, revisao = parear(regs)
    assert pareados[0].tipo_sinal.direcao == "Output"
    assert revisao == ()


def test_ambiguo_com_descricoes_empatadas_greedy_escolhe_um_e_outro_fica_standalone():
    # _rec usa Descricoes(sigla, sigla): os 2 inputs têm descrição idêntica
    # ("DJ"), empatando a 100 de similaridade com o único output. Fase 2
    # (greedy catch-all) resolve o empate deterministicamente: 1 funde,
    # o outro sobra como Input standalone — nenhum vai pra revisão, pois o
    # output não fica órfão. Nome/expectativa anteriores (tudo pra revisão)
    # eram do comportamento pré-Fase-2; ver spec discriminador-genérico Fase 2.
    regs = [
        _rec("s:1", "DJ", "Input", [5]),
        _rec("s:2", "DJ", "Input", [6]),
        _rec("s:3", "DJ", "Output", [0]),
    ]
    pareados, revisao = parear(regs)
    assert len(pareados) == 2
    dirs = sorted(r.tipo_sinal.direcao for r in pareados)
    assert dirs == ["Input", "InputOutput"]
    assert revisao == ()
    # Trava o desempate atual (maior índice de enumeração vence): s:2 funde,
    # s:1 fica standalone. Se o critério de desempate mudar deliberadamente,
    # este teste deve ser atualizado junto (não é um comportamento prescrito
    # pela spec, só o efeito observável do sort atual).
    por_id = {r.id: r for r in pareados}
    assert por_id["s:2"].tipo_sinal.direcao == "InputOutput"
    assert por_id["s:1"].tipo_sinal.direcao == "Input"


def test_grupos_mesma_direcao_nao_sao_tocados():
    # dois inputs sem comando: dc_pairer não mexe (double-bit é do normalizador estrutural)
    regs = [_rec("s:1", "DJ", "Input", [100]), _rec("s:2", "DJ", "Input", [101])]
    pareados, revisao = parear(regs)
    assert len(pareados) == 2
    assert revisao == ()


def test_fundir_publico_e_equivalente_ao_usado_internamente():
    status = _rec("s:1", "DJ", "Input", [5])
    comando = _rec("s:2", "DJ", "Output", [0])
    rw = fundir(status, comando)
    assert rw.tipo_sinal.direcao == "InputOutput"
    assert rw.enderecamento.indices == (5,)
    assert rw.enderecamento.indices_saida == (0,)


def test_separar_desfaz_fusao_em_input_e_output():
    status = _rec("s:1", "DJ", "Input", [5])
    comando = _rec("s:2", "DJ", "Output", [0])
    fundido = fundir(status, comando)

    novo_status, novo_comando = separar(fundido, "s:1_saida")

    assert novo_status.tipo_sinal.direcao == "Input"
    assert novo_status.enderecamento.indices == (5,)
    assert novo_status.enderecamento.indices_saida == ()
    assert novo_status.id == fundido.id

    assert novo_comando.tipo_sinal.direcao == "Output"
    assert novo_comando.enderecamento.indices == (0,)
    assert novo_comando.enderecamento.indices_saida == ()
    assert novo_comando.id == "s:1_saida"


def test_separar_e_fundir_sao_inversos_para_enderecos():
    status = _rec("s:1", "DJ", "Input", [5])
    comando = _rec("s:2", "DJ", "Output", [0])
    fundido = fundir(status, comando)
    novo_status, novo_comando = separar(fundido, "novo_id")
    refundido = fundir(novo_status, novo_comando)
    assert refundido.enderecamento.indices == fundido.enderecamento.indices
    assert refundido.enderecamento.indices_saida == fundido.enderecamento.indices_saida


def _rec_desc(rid, sigla, direcao, desc, modulo, indices):
    from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
    return SignalRecord(
        id=rid, modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc), sigla_sinal=sigla, status="decidido",
    )


def test_catchall_pareia_por_similaridade_e_deixa_sem_par_standalone():
    # 1 output "Excluir" + 2 inputs "Excluida"/"Atuado", todos sigla SGF, mesmo modulo.
    out = _rec_desc("o", "SGF", "Output", "PROTECAO SENSIVEL TERRA SGF EXCLUIR", "GTD_11", (20,))
    in_exc = _rec_desc("i1", "SGF", "Input", "PROTECAO SGF EXCLUIDA", "GTD_11", (71,))
    in_atu = _rec_desc("i2", "SGF", "Input", "PROTECAO SGF ATUADO", "GTD_11", (72,))
    saida, revisao = parear([out, in_exc, in_atu])
    dirs = sorted(r.tipo_sinal.direcao for r in saida)
    # Excluir+Excluida fundem (InputOutput); Atuado sobra como Input standalone.
    assert "InputOutput" in dirs
    assert "Input" in dirs           # Atuado standalone, decidido
    assert revisao == ()             # nada vai pra revisao


def test_catchall_output_orfao_vai_revisao():
    # 2 outputs, 1 input; o 2o output nao casa nada -> sobra -> revisao.
    out1 = _rec_desc("o1", "SGF", "Output", "PROTECAO SGF EXCLUIR", "GTD_11", (20,))
    out2 = _rec_desc("o2", "SGF", "Output", "ZZZ QQQ WWW NADA A VER", "GTD_11", (21,))
    inp = _rec_desc("i1", "SGF", "Input", "PROTECAO SGF EXCLUIDA", "GTD_11", (71,))
    saida, revisao = parear([out1, out2, inp])
    assert any(r.tipo_sinal.direcao == "InputOutput" for r in saida)
    assert len(revisao) == 1
    assert revisao[0].motivo == "pareamento_ambiguo"


def test_um_input_um_output_ainda_funde_direto():
    out = _rec_desc("o", "DJF1", "Output", "DISJ DESLIGAR LIGAR", "GTD_11", (18,))
    inp = _rec_desc("i", "DJF1", "Input", "DISJ DESLIGADO", "GTD_11", (35,))
    saida, revisao = parear([out, inp])
    assert len(saida) == 1 and saida[0].tipo_sinal.direcao == "InputOutput"
    assert revisao == ()


def test_fundir_propaga_comando_duplo():
    from dataclasses import replace
    status = _rec("s:1", "81U1", "Input", [1539])
    comando = _rec("s:2", "81U1", "Output", [1504])
    comando = replace(comando, tipo_sinal=replace(comando.tipo_sinal, comando_duplo=False))
    fundido = fundir(status, comando)
    assert fundido.tipo_sinal.comando_duplo is False
    assert fundido.enderecamento.indices_saida == (1504,)
