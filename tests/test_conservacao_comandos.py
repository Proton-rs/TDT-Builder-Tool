"""SP-CVA Task 7 (Fase 5, E3): trava de regressão — todo sinal (comando E
status/analógico) que entra no pipeline aparece no TDT final OU num item de
revisão; nunca some silenciosamente.

Composição replica ``pipeline.gerar_tdt`` (normalizador_estrutural.
fundir_pares_posicao -> dc_pairer.parear -> normalizador_estrutural.corrigir
-> criador_lista_homogenea.montar -> engine_tdt.particionar_custom_id_duplicado).

Nota sobre ids: ``dc_pairer.fundir`` preserva o id do STATUS, não o do
comando (ver docstring de ``dc_pairer.separar`` — o id original do Output é
perdido na fusão). Por isso um comando fundido não pode ser rastreado pelo
seu próprio ``id`` no resultado final; ele é rastreado pelo endereço
(``enderecamento.indices`` do comando == ``indices_saida`` do registro
fundido), que sobrevive intacto por todas as etapas deste pipeline parcial.
"""

from tdt import criador_lista_homogenea, dc_pairer, engine_tdt
from tdt.config import Config
from tdt.contracts import Descricoes, Enderecamento, Modulo, SignalRecord, TipoSinal
from tdt.normalizador_estrutural import corrigir, fundir_pares_posicao


def _rec(rid, sigla, direcao, modulo, indices, desc):
    return SignalRecord(
        id=rid,
        modulo=Modulo(modulo, "sheet_name"),
        tipo_sinal=TipoSinal("Discrete", "SingleBit", direcao),
        enderecamento=Enderecamento("DNP3", tuple(indices)),
        descricoes=Descricoes(desc, desc),
        sigla_sinal=sigla,
        status="decidido",
    )


def _status(sigla, modulo, indices):
    return _rec(f"{modulo}:{indices[0]}", sigla, "Input", modulo, indices, "DISJ DESLIGADO")


def _comando(sigla, modulo, indices):
    return _rec(f"{modulo}:{indices[0]}", sigla, "Output", modulo, indices, "DISJ DESLIGAR LIGAR")


def _comandos_fundidos(entrada, *grupos_finais):
    """Ids de comando cujo endereço foi absorvido (indices_saida) por algum
    registro fundido presente em qualquer um dos grupos finais."""
    enderecos_saida_presentes = set()
    for grupo in grupos_finais:
        for rec in grupo:
            if rec.enderecamento.indices_saida:
                enderecos_saida_presentes.add(
                    (rec.modulo.nome, rec.sigla_sinal, rec.enderecamento.indices_saida)
                )
    fundidos = set()
    for r in entrada:
        if r.tipo_sinal.direcao != "Output":
            continue
        chave = (r.modulo.nome, r.sigla_sinal, r.enderecamento.indices)
        if chave in enderecos_saida_presentes:
            fundidos.add(r.id)
    return fundidos


def test_nenhum_comando_some_silenciosamente():
    # BC1: status+comando pareáveis -> funde e sobrevive no TDT final.
    # BC9: comando órfão (sem status no grupo, sigla fora da whitelist) -> revisão.
    # BC2 / "BC 2": dois pares que fundem normalmente no dc_pairer, mas cujo
    # Custom ID colide (módulo formatado igual após strip de espaço) -> ambos
    # vão para revisão em particionar_custom_id_duplicado.
    entrada = [
        _status("DJF1", "BC1", [10]), _comando("DJF1", "BC1", [100]),
        _comando("DJF1", "BC9", [200]),
        _status("DJF1", "BC2", [30]), _comando("DJF1", "BC2", [300]),
        _status("DJF1", "BC 2", [40]), _comando("DJF1", "BC 2", [400]),
    ]
    ids_comando = {r.id for r in entrada if r.tipo_sinal.direcao == "Output"}

    fundidos = fundir_pares_posicao(entrada, frozenset())
    pareados, rev1 = dc_pairer.parear(fundidos, Config())
    corrigidos, rev2 = corrigir(list(pareados), frozenset())
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao="SE1")
    lista, rev3 = engine_tdt.particionar_custom_id_duplicado(lista)

    registros_revisao = [ir.registro for ir in (*rev1, *rev2, *rev3)]
    ids_diretos = {r.id for r in lista.registros} | {r.id for r in registros_revisao}
    ids_fundidos = _comandos_fundidos(entrada, lista.registros, registros_revisao)

    sobreviventes = ids_diretos | ids_fundidos
    assert ids_comando <= sobreviventes, "comando sumiu sem TDT nem revisao"


def _sinais_absorvidos(entrada, *grupos_finais):
    """Inputs cujo endereço foi absorvido por um MultiCoord fundido
    (fundir_pares_posicao) — rastreados por (modulo, sigla, endereço ∈ indices),
    análogo ao rastreio de comandos por indices_saida."""
    presentes = [
        (rec.modulo.nome, rec.sigla_sinal, set(rec.enderecamento.indices))
        for grupo in grupos_finais
        for rec in grupo
    ]
    absorvidos = set()
    for r in entrada:
        if r.tipo_sinal.direcao != "Input" or not r.enderecamento.indices:
            continue
        alvo = r.enderecamento.indices[0]
        for mod, sig, idxs in presentes:
            if mod == r.modulo.nome and sig == r.sigla_sinal and alvo in idxs:
                absorvidos.add(r.id)
                break
    return absorvidos


def test_nenhum_sinal_some_silenciosamente():
    """SP-CVA2 E6.1: conservação TOTAL — todo sinal da entrada (qualquer
    direção) termina no TDT final OU na revisão. Requisito do usuário
    (anot.txt 14jul): 'mesmo com módulo errado, deve ter todos os sinais
    para que a revisão possa ser feita'."""
    entrada = [
        # par de posição fundível (E4) + comando toggle do mesmo grupo
        _rec("BC2:21", "DJF1", "Input", "BC2", [320], "52 06 ABERTO"),
        _rec("BC2:22", "DJF1", "Input", "BC2", [321], "52 06 FECHADO"),
        _rec("BC2:14", "DJF1", "Output", "BC2", [90], "52 06 ABRIR FECHAR"),
        # input comum
        _rec("BC2:32", "MOLA", "Input", "BC2", [326], "MOLA DESCARREGADA"),
        # comando órfão -> revisão comando_sem_discreto
        _rec("BC9:1", "DJF1", "Output", "BC9", [200], "DISJ DESLIGAR LIGAR"),
        # sem endereço -> revisão sem_endereco (corrigir)
        _rec("BC2:52", "COM1", "Input", "BC2", [], "SAUDE COMUNICACAO"),
        # duplicata de endereço no mesmo grupo -> revisão endereco_duplicado
        _rec("BC3:5", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
        _rec("BC3:6", "VAB", "Input", "BC3", [50], "TENSAO BARRA AB"),
    ]
    ids_entrada = {r.id for r in entrada}

    fundidos = fundir_pares_posicao(entrada, frozenset({"DJF1"}))
    pareados, rev1 = dc_pairer.parear(fundidos, Config())
    corrigidos, rev2 = corrigir(list(pareados), frozenset({"DJF1"}))
    lista = criador_lista_homogenea.montar(list(corrigidos), subestacao="SE1")
    lista, rev3 = engine_tdt.particionar_custom_id_duplicado(lista)

    registros_revisao = [ir.registro for ir in (*rev1, *rev2, *rev3)]
    ids_diretos = {r.id for r in lista.registros} | {r.id for r in registros_revisao}
    ids_fundidos = _comandos_fundidos(entrada, lista.registros, registros_revisao)
    ids_absorvidos = _sinais_absorvidos(entrada, lista.registros, registros_revisao)

    sobreviventes = ids_diretos | ids_fundidos | ids_absorvidos
    assert ids_entrada <= sobreviventes, f"sumiram: {ids_entrada - sobreviventes}"
