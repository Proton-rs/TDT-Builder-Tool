from tdt.config import Config
from tdt import dc_pairer
from tdt.contracts import (
    Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal,
)
from tdt.normalizador_estrutural import corrigir, fundir_pares_posicao

WL = frozenset({"SECC", "DJF1", "SECG"})


def _rec(rid, sigla, indices, desc=None, datatype="SingleBit"):
    d = desc if desc is not None else sigla
    return SignalRecord(
        id=rid,
        modulo=Modulo("3", "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", datatype, "Input"),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(d, d),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_par_posicao_whitelist_vira_multicoord():
    regs = [_rec("LT3:1", "SECC", [100], "SECCIONADORA ABERTA"),
            _rec("LT3:2", "SECC", [101], "SECCIONADORA FECHADA")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (100, 101)
    assert corrigidos[0].tipo_sinal.datatype == "MultiCoord"
    assert erros == ()


def test_nao_funde_fora_da_whitelist():
    # SGF Excluída + SGF Atuado consecutivos: NUNCA funde (bug histórico 1534;1535)
    regs = [_rec("AL11:1", "SGF", [1534], "PROTECAO SGF EXCLUIDA"),
            _rec("AL11:2", "SGF", [1535], "PROTECAO SGF ATUADO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2
    assert all(c.tipo_sinal.datatype == "SingleBit" for c in corrigidos)
    assert erros == ()


def test_nao_funde_sem_estados_opostos():
    # mesma sigla whitelisted mas estados iguais -> não é par de posição
    regs = [_rec("LT3:1", "SECC", [100], "SECCIONADORA ABERTA"),
            _rec("LT3:2", "SECC", [101], "SECCIONADORA ABERTA")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2


def test_doublebit_nativo_passa_intacto():
    regs = [_rec("IMA:1", "SECC", [1100, 1101], "SECC 89-16", datatype="DoubleBit")]
    corrigidos, erros = corrigir(regs, WL)
    assert corrigidos[0].tipo_sinal.datatype == "DoubleBit"
    assert corrigidos[0].enderecamento.indices == (1100, 1101)


def test_indefinido_descartado_com_registro():
    regs = [_rec("AL11:1", "DJF1", [1500], "52 DESLIGADO"),
            _rec("AL11:2", "DJF1", [1501], "52 LIGADO"),
            _rec("AL11:3", "DJF1", [1502], "52 INDEFINIDO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].tipo_sinal.datatype == "MultiCoord"
    assert [e.motivo for e in erros] == ["descartado_indefinido"]


def test_local_remoto_fica_so_o_bit_local():
    regs = [_rec("AL11:1", "43LR", [1504], "CHAVE 43LR POS LOCAL"),
            _rec("AL11:2", "43LR", [1505], "CHAVE 43LR POS REMOTO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 1
    assert corrigidos[0].enderecamento.indices == (1504,)
    assert [e.motivo for e in erros] == ["descartado_redundante"]


def test_endereco_duplicado_continua_revisao():
    regs = [_rec("LT3:1", "DJ", [100]), _rec("LT3:2", "DJ", [100])]
    corrigidos, erros = corrigir(regs, WL)
    assert corrigidos == ()
    assert all(e.motivo == "endereco_duplicado" for e in erros)


def test_sem_endereco_vai_para_revisao():
    corrigidos, erros = corrigir([_rec("LT3:9", "DJ", [])], WL)
    assert erros[0].motivo == "sem_endereco"


def test_nao_consecutivos_seguem_independentes():
    regs = [_rec("LT3:1", "DJA1", [100], "DISJUNTOR ABERTO"),
            _rec("LT3:2", "DJA1", [108], "DISJUNTOR FECHADO")]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2
    assert erros == ()


def test_nao_funde_input_com_output_mesmo_par_posicao():
    # Guarda de direção: fundir_pares_posicao já exige direcao=="Input";
    # corrigir() não tinha essa checagem. Hoje é inerte porque comando de
    # verbo duplo ("ABRIR FECHAR") vira polaridade None e nunca casa, mas um
    # comando de verbo único (ex. só "ABRIR") resolveria para 1 polaridade e,
    # sem a guarda, fundiria Input+Output num "MultiCoord" (semanticamente
    # errado — MultiCoord é reservado a 2 INPUTS de status).
    regs = [
        SignalRecord(
            id="LT3:1", modulo=Modulo("3", "sheet_name"),
            tipo_sinal=TipoSinal("Discrete", "SingleBit", "Input"),
            enderecamento=Enderecamento("DNP3", (100,)),
            descricoes=Descricoes("SECC FECHADO", "SECC FECHADO"),
            sigla_sinal="SECC", status="decidido",
        ),
        SignalRecord(
            id="LT3:2", modulo=Modulo("3", "sheet_name"),
            tipo_sinal=TipoSinal("Discrete", "SingleBit", "Output"),
            enderecamento=Enderecamento("DNP3", (101,)),
            descricoes=Descricoes("ABRIR", "ABRIR"),
            sigla_sinal="SECC", status="decidido",
        ),
    ]
    corrigidos, erros = corrigir(regs, WL)
    assert len(corrigidos) == 2
    assert all(c.tipo_sinal.datatype == "SingleBit" for c in corrigidos)
    assert erros == ()


def _rec_fp(rid, sigla, direcao, indices, desc, modulo="BC2"):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        sigla_sinal=sigla,
        status="decidido",
    )


def test_fundir_pares_posicao_forma_multicoord():
    """SP-CVA2 E4: par ABERTO/FECHADO (mesma sigla de posição, endereços
    consecutivos) vira UM MultiCoord ANTES do dc_pairer."""
    aberto = _rec_fp("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    fechado = _rec_fp("BC2:22", "DJF1", "Input", [321], "52 06 FECHADO")
    comando = _rec_fp("BC2:14", "DJF1", "Output", [90], "52 06 ABRIR FECHAR")
    saida = fundir_pares_posicao([aberto, fechado, comando], frozenset({"DJF1"}))
    inputs = [r for r in saida if r.tipo_sinal.direcao == "Input"]
    assert len(inputs) == 1
    assert inputs[0].enderecamento.indices == (320, 321)
    assert inputs[0].tipo_sinal.datatype == "MultiCoord"
    assert len(saida) == 2  # MultiCoord + comando


def test_fundir_pares_posicao_readwrite_completo_no_pairer():
    """Encadeado com dc_pairer: 1 MultiCoord x 1 comando -> InputOutput com
    INCOORDS do par e OUTCOORDS do comando (antes: catch-all N x M)."""
    aberto = _rec_fp("BC2:21", "DJF1", "Input", [320], "52 06 ABERTO")
    fechado = _rec_fp("BC2:22", "DJF1", "Input", [321], "52 06 FECHADO")
    comando = _rec_fp("BC2:14", "DJF1", "Output", [90], "52 06 ABRIR FECHAR")
    fundidos = fundir_pares_posicao([aberto, fechado, comando], frozenset({"DJF1"}))
    pareados, rev = dc_pairer.parear(fundidos, Config())
    rw = [r for r in pareados if r.tipo_sinal.direcao == "InputOutput"]
    assert len(rw) == 1
    assert rw[0].enderecamento.indices == (320, 321)
    assert rw[0].enderecamento.indices_saida == (90,)
    assert not rev


def test_fundir_pares_posicao_ignora_fora_da_whitelist_e_nao_consecutivos():
    a = _rec_fp("Z:1", "MOLA", "Input", [10], "MOLA CARREGADA")
    b = _rec_fp("Z:2", "MOLA", "Input", [11], "MOLA DESCARREGADA")
    c = _rec_fp("Z:3", "DJF1", "Input", [20], "52 06 ABERTO")
    d = _rec_fp("Z:4", "DJF1", "Input", [22], "52 06 FECHADO")  # gap: 20->22
    saida = fundir_pares_posicao([a, b, c, d], frozenset({"DJF1"}))
    assert len(saida) == 4  # nada fundido
