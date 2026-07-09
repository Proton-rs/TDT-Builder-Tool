from tdt.contracts import (
    Descricoes,
    Enderecamento,
    Modulo,
    Pareamento,
    SignalRecord,
    TipoSinal,
)


def _rec(tag: str) -> SignalRecord:
    return SignalRecord(
        id=f"sheet:{tag}",
        modulo=Modulo(nome=None, origem_contexto="sheet_name"),
        tipo_sinal=TipoSinal(categoria="Discrete"),
        enderecamento=Enderecamento(protocolo="DNP3", indices=(1,)),
        descricoes=Descricoes(bruta=tag, normalizada=tag),
    )


def test_pareamento_completo():
    p = Pareamento(status_rec=_rec("s"), comando_rec=_rec("c"), tipo="completo")
    assert p.comando_rec is not None
    assert p.tipo == "completo"


def test_pareamento_orfao_aceita_comando_none():
    p = Pareamento(status_rec=_rec("s"), comando_rec=None, tipo="status_orfao")
    assert p.comando_rec is None
