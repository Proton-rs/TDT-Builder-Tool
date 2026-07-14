from tdt.config import Config
from tdt.contracts import (
    Descricoes,
    Eletrico,
    Enderecamento,
    Modulo,
    SignalRecord,
    TipoSinal,
)
from tdt import dc_pairer
from tdt.dc_pairer import fundir, parear, separar


def _rec(rid, sigla, direcao, indices, desc=None):
    desc = sigla if desc is None else desc
    return SignalRecord(
        id=rid,
        modulo=Modulo("LT_GTA", "coluna:modulo"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(sigla, desc),
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


def test_comando_orfao_fora_da_whitelist_vai_para_revisao():
    # Fase D5: comando órfão só passa direto como Write se a sigla estiver na
    # whitelist de write legítimo (ex. CDC); "DJ" órfão sem status vira revisão.
    regs = [_rec("s:1", "DJ", "Output", [0])]
    pareados, revisao = parear(regs)
    assert pareados == ()
    assert [r.motivo for r in revisao] == ["comando_sem_discreto"]


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


def test_comando_orfao_vai_para_revisao():
    comando = _rec("s:1", "81U1", "Output", [1504])
    saida, revisao = parear([comando], Config())
    assert saida == ()
    assert [r.motivo for r in revisao] == ["comando_sem_discreto"]


def test_cdc_orfao_continua_write():
    comando = _rec("s:1", "CDC", "Output", [700, 701])
    saida, revisao = parear([comando], Config())
    assert len(saida) == 1
    assert revisao == ()


def test_catchall_nao_casa_classes_de_estado_diferentes():
    # comando de função (excluir/incluir) não pode casar status de EVENTO (atuado)
    status_trip = _rec("s:1", "SGF", "Input", [1535], desc="PROTECAO SGF ATUADO")
    comando = _rec("s:2", "SGF", "Output", [1502], desc="SGF EXCLUIR INCLUIR")
    saida, revisao = parear([status_trip, comando], Config())
    # não funde: status segue standalone, comando vira revisão
    assert any(r.tipo_sinal.direcao == "Input" for r in saida)
    assert [r.motivo for r in revisao] == ["pareamento_ambiguo"]


def test_autc_orfao_e_write_legitimo():
    # SP-I Task 2, causa D: "Rearme 86 Automatismo" (PSACA_CC:22 real) é um
    # comando tipo pulso/reset sem status de retorno por natureza — precisa
    # entrar na whitelist junto de CDC (config.siglas_write_legitimo).
    comando = _rec("s:1", "AUTC", "Output", [10, 11])
    saida, revisao = parear([comando], Config())
    assert len(saida) == 1
    assert saida[0].tipo_sinal.direcao == "Output"
    assert revisao == ()


def test_pb_orfao_e_write_legitimo():
    # SP-I Task 2, causa D: "Seleção de Barra Preferencial" (PSACA_CC:21
    # real) não tem status correspondente em lugar nenhum do input.
    comando = _rec("s:1", "PB", "Output", [12, 13])
    saida, revisao = parear([comando], Config())
    assert len(saida) == 1
    assert saida[0].tipo_sinal.direcao == "Output"
    assert revisao == ()


def test_cmd_orfao_no_modulo_psaca_e_write_legitimo():
    # SP-I Task 2, causa D: "Comando Iluminação Pátio" (PSACA_CC:20 real)
    # decide sigla CMD (genérica), mas nesse módulo/grupo específico não há
    # NENHUM Input com essa sigla — write legítimo. Nota: CMD é usada em
    # dezenas de outros módulos como Input ("Falha Comando de
    # Desligar/Ligar"); a whitelist só morde quando o grupo
    # (módulo, equipamento, sigla) não tem nenhum Input, então não afeta
    # esses outros grupos (ver investigação da task: nenhum módulo fora de
    # PSACA tem grupo CMD com Output e zero Input).
    comando = _rec("s:1", "CMD", "Output", [14, 15])
    saida, revisao = parear([comando], Config())
    assert len(saida) == 1
    assert saida[0].tipo_sinal.direcao == "Output"
    assert revisao == ()


def test_cmd_orfao_nao_afeta_grupo_cmd_com_input_em_outro_modulo():
    # Confirma que whitelistar CMD não quebra o caso real onde CMD já tem
    # Input no mesmo grupo (ex. módulo AL11: "Falha Comando de
    # Desligar/Ligar") — esse grupo nunca cai no ramo `elif not inputs`,
    # então segue indo para o catch-all/pareamento normal, intocado.
    status = _rec("s:1", "CMD", "Input", [20], desc="Falha Comando de Desligar")
    saida, revisao = parear([status], Config())
    assert len(saida) == 1
    assert saida[0].tipo_sinal.direcao == "Input"
    assert revisao == ()


def test_secg_terra_status_sem_comando_nao_vira_gap():
    # item 4: SECG (seccionadora de terra) é um STATUS — no TDT real está em
    # DNP3_DiscreteSignals (MM _terra, doublebit "28;29"), sem par de comando,
    # porque o intertravamento de segurança impede operação remota. Status
    # sozinho já cai no ramo `if not outputs` -> saída; nunca é marcado como
    # comando_sem_discreto (esse ramo só morde Output órfão). Trava o não-gap.
    status = _rec("s:1", "SECG", "Input", [28, 29])
    saida, revisao = parear([status], Config())
    assert revisao == ()
    assert saida[0].sigla_sinal == "SECG"


def test_fundir_propaga_comando_duplo():
    from dataclasses import replace
    status = _rec("s:1", "81U1", "Input", [1539])
    comando = _rec("s:2", "81U1", "Output", [1504])
    comando = replace(comando, tipo_sinal=replace(comando.tipo_sinal, comando_duplo=False))
    fundido = fundir(status, comando)
    assert fundido.tipo_sinal.comando_duplo is False
    assert fundido.enderecamento.indices_saida == (1504,)


def _rec_pos(rid, sigla, direcao, indices, desc, equip="52-06", modulo="BC1"):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        eletrico=Eletrico(equipamento_alvo="Disjuntor", nome_equipamento=equip),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_reconcilia_comando_toggle_com_sigla_do_status_de_posicao():
    """SP-CVA2 E2: comando 'ABRIR FECHAR' decidido DJA1 pelo scorer, status do
    mesmo equipamento decidido DJF1 -> re-chaveia o comando pra DJF1 (status
    único e inequívoco)."""
    status = _rec_pos("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    comando = _rec_pos("BC2:14", "DJA1", "Output", [90], "52 06 ABRIR FECHAR")
    novos, rev = dc_pairer._reconciliar_posicao([status, comando])
    by_id = {r.id: r for r in novos}
    assert by_id["BC2:14"].sigla_sinal == "DJF1"
    assert not rev


def test_posicao_divergente_vai_pra_revisao_quando_status_ambiguo():
    """Dois status de posição com siglas DIFERENTES no mesmo equipamento:
    não re-chaveia — revisão `posicao_divergente`."""
    s1 = _rec_pos("X:1", "DJF1", "Input", [10], "52 06 ABERTO")
    s2 = _rec_pos("X:2", "DJA1", "Input", [11], "52 06 FECHADO NA")
    comando = _rec_pos("X:3", "SECC", "Output", [90], "52 06 ABRIR FECHAR")
    novos, rev = dc_pairer._reconciliar_posicao([s1, s2, comando])
    assert [it.motivo for it in rev] == ["posicao_divergente"]
    assert all(r.id != "X:3" for r in novos)


def test_reconciliacao_nao_toca_comando_nao_toggle_nem_sigla_fora_do_catalogo():
    status = _rec_pos("Y:1", "DJF1", "Input", [10], "52 06 ABERTO")
    cmd_nao_toggle = _rec_pos("Y:2", "CDC", "Output", [20], "COMANDO SUBIR DESCER")
    novos, rev = dc_pairer._reconciliar_posicao([status, cmd_nao_toggle])
    by_id = {r.id: r for r in novos}
    assert by_id["Y:2"].sigla_sinal == "CDC"
    assert not rev


def test_parear_funde_apos_reconciliacao():
    """Fim-a-fim no parear: comando DJA1 + status DJF1 do mesmo equipamento
    fundem (antes: comando_sem_discreto)."""
    status = _rec_pos("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    comando = _rec_pos("BC2:14", "DJA1", "Output", [90], "52 06 ABRIR FECHAR")
    pareados, rev = dc_pairer.parear([status, comando], Config())
    assert not any(it.motivo == "comando_sem_discreto" for it in rev)
    rw = [r for r in pareados if r.tipo_sinal.direcao == "InputOutput"]
    assert len(rw) == 1 and rw[0].enderecamento.indices_saida == (90,)
